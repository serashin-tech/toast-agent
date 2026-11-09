"""소스 어댑터 공통: 호출, 페이지 넘김, 오류 분류, 호출 예산, 값 변환.

소스별 모듈은 요청 주소, 파라미터, 필드 이름 대응표(FIELDS), 항목 변환만 가진다.
"""
import json
import re
import xml.etree.ElementTree as ET
from datetime import date
from urllib.parse import unquote


class SourceError(Exception):
    def __init__(self, kind, message):
        super().__init__(message)
        self.kind = kind
        self.message = message


class LimitNear(Exception):
    pass


class Budget:
    def __init__(self, used, limit):
        self.used, self.limit = used, limit

    def take(self):
        if self.used >= self.limit:
            raise LimitNear()
        self.used += 1


def scrub(text, key):
    """오류 메시지와 결과에서 인증키(원문과 인코딩 변형)를 지운다."""
    if not key:
        return text
    from urllib.parse import quote
    for k in {key, unquote(key), quote(unquote(key), safe=""), quote(unquote(key))}:
        if k:
            text = text.replace(k, "***")
    return text


# data.go.kr 공통 오류 문자열과 코드
_TEXT_KINDS = [("LIMITED_NUMBER_OF_SERVICE_REQUESTS", "rate_limit"),
               ("SERVICE_ACCESS_DENIED", "pending_approval"),
               ("SERVICE_KEY_IS_NOT_REGISTERED", "auth"), ("DEADLINE_HAS_EXPIRED", "auth"),
               ("UNREGISTERED_IP", "auth"), ("INVALID_REQUEST_PARAMETER", "format")]
_CODE_KINDS = {"20": "pending_approval", "22": "rate_limit", "30": "auth", "31": "auth",
               "32": "auth", "33": "auth", "10": "format"}


def _raise_http(status):
    if status in (401, 403):
        raise SourceError("auth", f"HTTP {status}: 인증 또는 접근 거부")
    if status == 429:
        raise SourceError("rate_limit", "HTTP 429: 호출 한도 초과")
    if status >= 500:
        raise SourceError("network", f"HTTP {status}: 서버 오류")
    if status >= 400:
        raise SourceError("format", f"HTTP {status}: 요청 오류")


def _raise_kind(code, msg, status):
    up = f"{code} {msg}".upper()
    for needle, kind in _TEXT_KINDS:
        if needle in up:
            raise SourceError(kind, f"API 오류: {needle}")
    if code in _CODE_KINDS:
        raise SourceError(_CODE_KINDS[code], f"API 오류 코드 {code}: {msg}"[:200])
    _raise_http(status)
    raise SourceError("format", f"API 오류 응답 {code}: {msg}"[:200])


def _walk(data, path):
    for p in path:
        if not isinstance(data, dict) or p not in data:
            return None
        data = data[p]
    return data


def parse_response(status, body, src):
    """(항목 목록, 전체 건수 또는 None). 오류는 SourceError."""
    text = (body or "").strip()
    if text.startswith("<"):  # 게이트웨이 오류는 XML로 오는 경우가 많다
        try:
            root = ET.fromstring(text)
        except ET.ParseError:
            _raise_http(status)
            raise SourceError("format", "XML 응답을 해석하지 못함")
        tags = {e.tag.split("}")[-1]: (e.text or "").strip() for e in root.iter()}
        _raise_kind(tags.get("returnReasonCode", ""), tags.get("returnAuthMsg") or tags.get("errMsg", ""), status)
    try:
        data = json.loads(text)
    except ValueError:
        _raise_http(status)
        raise SourceError("format", "응답이 JSON이 아님")
    header = _walk(data, src.HEADER_PATH) or {}
    code, msg = str(header.get("resultCode", "00")), str(header.get("resultMsg", ""))
    if code not in ("00", "0", "000"):
        if code == "03":  # 자료 없음
            return [], 0
        _raise_kind(code, msg, status)
    _raise_http(status)
    parent = _walk(data, src.ITEMS_PATH[:-1])
    if not isinstance(parent, dict):
        raise SourceError("format", "응답에 항목 영역이 없음")
    items = parent.get(src.ITEMS_PATH[-1])
    if items in (None, ""):
        items = []
    if isinstance(items, dict):
        items = items["item"] if "item" in items else [items]
        if isinstance(items, dict):
            items = [items]
    if not isinstance(items, list) or not all(isinstance(i, dict) for i in items):
        raise SourceError("format", "항목 형식이 예상과 다름")
    total = _walk(data, src.TOTAL_PATH)
    return items, int(total) if str(total).isdigit() else None


def collect(src, transport, key, budget, since, now, env):
    """페이지를 넘기며 원본 항목을 하나씩 낸다. 호출마다 예산을 센다."""
    url = src.url(env)
    if not url:
        raise SourceError("format", f"{src.LABEL}: 요청 주소가 설정되지 않음({src.URL_ENV})")
    page, got = 1, 0
    while True:
        budget.take()
        params = {"serviceKey": unquote(key), "pageNo": page, "numOfRows": src.PAGE_SIZE,
                  **src.build_params(since, now)}
        try:
            status, body = transport(url, params)
        except Exception as e:  # 네트워크 계층의 모든 실패
            raise SourceError("network", scrub(f"네트워크 오류: {type(e).__name__}: {e}", key)[:200])
        items, total = parse_response(status, body, src)
        yield from items
        got += len(items)
        if not items or len(items) < src.PAGE_SIZE or (total is not None and got >= total):
            return
        page += 1


# 값 변환
def pick(raw, field):
    v = raw.get(field) if field else None
    v = "" if v is None else str(v).strip()
    return v or None


def to_int(v):
    v = re.sub(r"[^\d]", "", (v or "").split(".")[0])
    return int(v) if v else None


def to_float(v):
    try:
        return float((v or "").replace(",", "").replace("%", ""))
    except ValueError:
        return None


_DATE = re.compile(r"(\d{4})[-./]?(\d{2})[-./]?(\d{2})")


def all_dates(v):
    out = []
    for y, m, d in _DATE.findall(v or ""):
        try:
            out.append(date(int(y), int(m), int(d)))
        except ValueError:
            pass
    return out


def to_date(v):
    d = all_dates(v)
    return d[0] if d else None

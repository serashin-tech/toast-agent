"""수집 이력 시트 연결(D14, D19): 시트에 붙인 Apps Script 웹 앱 하나에 JSON을 POST한다.

요청 종류: upsert(행 추가·갱신), rows(마감 전 행 읽기), mail(대표에게 메일 발송).
주소와 토큰은 작업 폴더 .env의 SHEET_APP_URL, SHEET_APP_TOKEN에서만 읽고 출력하지 않는다.
ponytail: 시트에는 그날 처음 보여 주는 항목만 보낸다. 이미 보여 준 항목의 내용 변경은 시트에 다시 쓰지 않으며,
필요하면 로컬 원장에 행 필드를 더해 upsert 대상으로 넓힌다.
"""
import json
import pathlib
import urllib.request
from datetime import timedelta

from .inputs import parse_date

NO_DEADLINE_DAYS = 30  # 마감일이 없는 행은 등록일로부터 30일까지만 둔다(D29)


def read_env(path):
    env = {}
    try:
        lines = pathlib.Path(path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return env
    for line in lines:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip("'\"")
    return env


def http_transport(url, payload):
    """실제 네트워크 계층. Apps Script는 응답을 다른 주소로 넘기므로 urllib의 리다이렉트 처리에 맡긴다."""
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def _open(item, run_date):
    d = parse_date(item.get("deadline")) if item.get("deadline") else None
    if d is not None:
        return d >= run_date
    posted = parse_date(item.get("posted_on")) if item.get("posted_on") else None
    return posted is None or posted >= run_date - timedelta(days=NO_DEADLINE_DAYS)


def build_rows(results_dir, run_date):
    """그날 결과 파일의 항목을 시트 행으로 바꾼다. 마감 지난 행은 넣지 않는다. 대표 메모 열은 다루지 않는다."""
    rows = []
    for p in sorted(pathlib.Path(results_dir).glob(f"*_{run_date.isoformat()}.json")):
        if p.name.startswith("shown_"):
            continue
        try:
            items = json.loads(p.read_text(encoding="utf-8")).get("items") or []
        except (OSError, ValueError, AttributeError):
            continue
        for it in items:
            if not it.get("is_new") or not _open(it, run_date):
                continue
            x = it.get("extra") or {}
            keys = it.get("keys") or [f"{it.get('source')}:{it.get('id')}"]
            rows.append({"key": keys[0], "alt_keys": keys[1:], "source": it.get("source"), "kind": it.get("kind"),
                         "title": it.get("title"), "agency": x.get("agency") or x.get("poster") or "",
                         "price": x.get("est_price"), "deadline": it.get("deadline"),
                         "registered": it.get("posted_on"), "url": it.get("url"),
                         "matched": ", ".join(it.get("matched_keywords") or []), "status": "신규"})
    return rows


def call(env, payload, transport):
    """(성공 여부, 응답 또는 실패 사유). 토큰과 주소는 사유에 넣지 않는다."""
    url, token = env.get("SHEET_APP_URL"), env.get("SHEET_APP_TOKEN")
    if not url or not token:
        return False, "SHEET_APP_URL, SHEET_APP_TOKEN이 .env에 없습니다"
    try:
        reply = transport(url, {**payload, "token": token})
    except Exception as e:  # 네트워크·응답 형식 오류를 모두 실패로 남긴다
        return False, type(e).__name__
    if not isinstance(reply, dict) or not reply.get("ok"):
        return False, "웹 앱이 거절함" + (f"({reply.get('error')})" if isinstance(reply, dict) and reply.get("error") else "")
    return True, reply

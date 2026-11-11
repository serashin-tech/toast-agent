"""수집 이력 시트 연결(D14, D19): 시트에 붙인 Apps Script 웹 앱 하나에 JSON을 POST한다.

요청 종류: upsert(행 추가·갱신), rows(마감 전 행 읽기), status(상태 칸 변경), mail(대표에게 메일 발송).
주소와 토큰은 작업 폴더 .env의 SHEET_APP_URL, SHEET_APP_TOKEN에서만 읽고 출력하지 않는다.
시트 행은 로컬 원장(gov-agent의 state/ledger.json)의 마감 전 행 전체다. 매 실행 전부 다시 보내므로,
기록에 실패한 날의 행과 이미 보여 준 항목의 내용 변경도 다음 실행에서 시트에 들어간다(티켓 21).
ponytail: 마감 전 행 전체를 매일 보낸다. 행이 수천 개로 늘면 바뀐 행만 보내도록 원장에 보낸 날을 둔다.
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


ROW_FIELDS = ("source", "kind", "title", "agency", "price", "deadline", "registered", "url", "matched")


def _still_open(entry, run_date):
    """마감일이 오늘 이후(당일 포함)이거나, 마감일이 없고 등록 30일 이내인 행(D29)."""
    d = parse_date(entry.get("deadline")) if entry.get("deadline") else None
    if d is not None:
        return d >= run_date
    reg = parse_date(entry.get("registered")) if entry.get("registered") else None
    return reg is None or reg >= run_date - timedelta(days=NO_DEADLINE_DAYS)


def build_rows(state_dir, run_date):
    """로컬 원장의 마감 전 행을 시트 행으로 바꾼다. 같은 사업의 다른 출처 키는 대표 행의 alt_keys로 붙인다.

    행 필드가 없는 옛 원장 항목은 건너뛴다. 대표 메모 열은 다루지 않고, 상태는 새 행에만 '신규'로 쓰인다.
    """
    try:
        ledger = json.loads((pathlib.Path(state_dir) / "ledger.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    aliases = {}
    for k, e in ledger.items():
        if e.get("alias_of"):
            aliases.setdefault(e["alias_of"], []).append(k)
    return [{"key": k, "alt_keys": sorted(aliases.get(k, [])), **{f: e.get(f) for f in ROW_FIELDS}, "status": "신규"}
            for k, e in sorted(ledger.items())
            if e.get("title") and not e.get("alias_of") and _still_open(e, run_date)]


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

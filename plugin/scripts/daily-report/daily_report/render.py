"""메일과 현황판이 함께 쓰는 표시 도우미. 모든 입력 문자열은 esc()를 거쳐 넣는다.

예전에는 보고서 HTML 한 장을 만들었으나 D35(2026-11-11)로 그 기능을 신규 알림 메일로 옮기고 지웠다.
"""
import html as _html
import re

from .inputs import parse_date, parse_dt

AGENT_LABEL = {"gov": "정부사업", "market": "시장 정보"}
REASON = {
    "auth": "인증 오류", "pending_approval": "승인 대기", "rate_limit": "호출 한도 초과",
    "network": "네트워크 오류", "format": "형식 오류", "missing": "결과 없음", "limit_near": "한도 임박으로 중단",
}
SOON_DAYS = 7
# 절 구성: (id, 제목, 이 절에 데이터를 주는 소스 id들). 시장 정보 절은 market-agent spec에서 정한다.
SECTIONS = (
    ("bid", "입찰공고", ("bid",)),
    ("grant", "지원사업", ("grant_kocca", "grant_bizinfo")),
    ("outsource", "민간 외주", ("outsource_cglink",)),
)


def esc(v):
    return _html.escape("" if v is None else str(v), quote=True)


def fmt_dt(v):
    d = parse_dt(v) if v else None
    return d.strftime("%Y-%m-%d %H:%M") if d else "기록 없음"


_KEY_PARAM = re.compile(r"([?&])(?:service[_-]?key|api[_-]?key|auth[_-]?key|crtfc[_-]?key|key)=[^&#\s]*&?", re.I)


def safe_url(u):
    """http/https만 링크로 쓴다. 주소에 섞인 인증키 모양의 매개변수는 지운다. 안전하지 않으면 None."""
    u = _KEY_PARAM.sub(r"\1", "" if u is None else str(u).strip()).rstrip("?&")
    return u if re.match(r"https?://", u, re.I) else None


def link(label, url):
    u = safe_url(url)
    if u:
        return f'<a href="{esc(u)}" rel="noopener noreferrer">{esc(label)}</a>'
    return f'{esc(label)} <span class="nolink">(링크 없음: 안전하지 않은 주소)</span>'


def won(v):
    return f"{v:,}원" if isinstance(v, int) and not isinstance(v, bool) else "미기재"


def days_left(it, run_date):
    d = parse_date(it["deadline"]) if it["deadline"] else None
    return (d - run_date).days if d else None


def dday(n):
    return "마감 지남" if n < 0 else "D-day" if n == 0 else f"D-{n}"


def failures(agents):
    """실패한 에이전트와 소스를 [(라벨, 사유, 마지막 정상 수집, 소스 id)]로 모은다. 에이전트 전체 실패는 소스 id가 None이다."""
    out = []
    for a in agents:
        if not a["ok"]:
            out.append((AGENT_LABEL.get(a["agent"], a["agent"]) + " 에이전트 전체", REASON[a["error"]], "확인 불가", None))
            continue
        for s in a["sources"]:
            if s["status"] == "ok":
                continue
            kind = (s["error"] or {}).get("kind")
            reason = REASON["limit_near"] if s["status"] == "limit_near" else REASON.get(kind, "원인 미상")
            out.append((s["label"] or s["id"], reason, fmt_dt(s["last_success_at"]), s["id"]))
    return out

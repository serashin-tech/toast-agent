"""입력 읽기: 결과 파일(docs/result-format.md)과 설정 md의 변경 이력.

계약 문서의 목록에 있는 필드만 골라 읽고, 나머지는 버린다. 인증키가 어디에 섞여 있어도
보고서와 실행 기록으로 새어 나가지 않게 하기 위해서다.
"""
import json
import pathlib
import re
from datetime import date, datetime

# 기대하는 에이전트 목록. 시장 정보 에이전트를 붙일 때 "market"을 여기에 추가한다.
EXPECTED_AGENTS = ("gov",)
FORMAT_VERSION = "1"

_SOURCE_KEYS = ("id", "label", "status", "fetched", "included", "excluded", "new_count", "changed_shown_count",
                "error", "last_success_at")
_ITEM_KEYS = ("source", "kind", "id", "title", "posted_on", "deadline", "url", "matched_keywords", "summary", "is_new",
              "renotify")
_EXTRA_KEYS = {
    "bid": ("agency", "demand_agency", "est_price"),  # attachments는 보고서에 싣지 않으므로 읽지 않는다
    "grant": ("agency", "period_start", "period_end", "dday", "category", "target", "contact", "origins"),
    "outsource": ("poster",),
}
_ELIG_KEYS = ("bid_id", "overall", "reason", "disclaimer", "unreadable_files", "requirements")
_REQ_KEYS = ("category", "text", "verdict", "profile_item", "evidence")
_REQUIRED = ("format_version", "agent", "run_date", "sources", "items", "eligibility")


def parse_date(value):
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def parse_dt(value):
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _pick(d, keys):
    if not isinstance(d, dict):
        raise ValueError("객체가 아님")
    return {k: d.get(k) for k in keys}


def _list(v):
    if not isinstance(v, list):
        raise ValueError("배열이 아님")
    return v


def _normalize(raw, agent, run_date):
    if not isinstance(raw, dict) or any(k not in raw for k in _REQUIRED):
        raise ValueError("필수 필드 없음")
    if raw["format_version"] != FORMAT_VERSION or raw["agent"] != agent or str(raw["run_date"]) != run_date.isoformat():
        raise ValueError("버전, 에이전트, 기준일 불일치")
    sources = []
    for s in _list(raw["sources"]):
        s = _pick(s, _SOURCE_KEYS)
        s["error"] = _pick(s["error"], ("kind",)) if isinstance(s["error"], dict) else None  # message는 읽지 않는다
        sources.append(s)
    items = []
    for it in _list(raw["items"]):
        base = _pick(it, _ITEM_KEYS)
        if base["kind"] not in _EXTRA_KEYS:
            continue
        base["extra"] = _pick(it.get("extra") or {}, _EXTRA_KEYS[base["kind"]])
        kw = base["matched_keywords"]
        base["matched_keywords"] = [str(k) for k in kw] if isinstance(kw, list) else []
        base["is_new"] = base["is_new"] is True
        base["renotify"] = base["renotify"] is True
        items.append(base)
    elig = []
    for e in _list(raw["eligibility"]):
        e = _pick(e, _ELIG_KEYS)
        e["requirements"] = [_pick(r, _REQ_KEYS) for r in _list(e["requirements"] or [])]
        e["unreadable_files"] = [_pick(f, ("name", "url")) for f in _list(e["unreadable_files"] or [])]
        elig.append(e)
    return {"agent": agent, "ok": True, "error": None, "sources": sources, "items": items, "eligibility": elig}


def load_agent(results_dir, agent, run_date):
    """에이전트 하루치 결과를 읽는다. 어제 파일로 대체하지 않는다."""
    path = pathlib.Path(results_dir) / f"{agent}_{run_date.isoformat()}.json"
    fail = {"agent": agent, "ok": False, "sources": [], "items": [], "eligibility": []}
    if not path.is_file():
        return {**fail, "error": "missing"}
    try:
        return _normalize(json.loads(path.read_text(encoding="utf-8")), agent, run_date)
    except (OSError, ValueError, TypeError, AttributeError):  # JSONDecodeError, UnicodeDecodeError는 ValueError의 하위
        return {**fail, "error": "format"}


_HISTORY_COLS = ["일자", "항목", "변경 전", "변경 후", "사유", "변경자"]


def recent_changes(settings_dir, today, days=7):
    """설정 md의 '## 변경 이력' 표에서 기준일 기준 최근 days일 이내 행을 읽는다. 형식이 다르면 건너뛴다."""
    rows = []
    if not settings_dir:
        return rows
    for md in sorted(pathlib.Path(settings_dir).glob("*.md")):
        try:
            text = md.read_text(encoding="utf-8")
        except (OSError, ValueError):
            continue
        m = re.search(r"^##\s*변경 이력\s*$", text, re.M)
        if not m:
            continue
        table = []
        for line in text[m.end():].splitlines():
            if line.startswith("## "):
                break
            if line.strip().startswith("|"):
                table.append([c.strip() for c in line.strip().strip("|").split("|")])
        if len(table) < 2 or table[0] != _HISTORY_COLS:
            continue
        for cells in table[2:]:  # table[1]은 구분선
            if len(cells) != 6:
                continue
            d = parse_date(cells[0])
            if d and 0 <= (today - d).days <= days:
                rows.append(dict(zip(_HISTORY_COLS, cells), d=d))
    return sorted(rows, key=lambda r: r["d"])

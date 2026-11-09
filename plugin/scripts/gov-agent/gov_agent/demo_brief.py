"""2차 검토(시연 판정): Claude가 추출한 시연 신호를 결정적으로 판정해 시연 브리프를 만든다.

신호 추출(공고문·제안요청서 읽기)은 Claude가 하고, 이 코드는 근거가 확인된 신호만 '필요'로 센다.
형식은 docs/demo-brief-input.md.
"""
from pathlib import Path

from .settings import SettingsError, read_table

DISCLAIMER = "AI가 만든 1차 판정과 브리프입니다. 시연 데모 제작 여부와 최종 판단은 대표가 합니다."
DEFAULT_WORDS = ["시안", "시연", "샘플", "견본", "데모", "시제품", "프로토타입", "캐릭터 디자인", "캐릭터 개발",
                 "콘셉트", "키비주얼", "스토리보드", "디자인 제안"]
PASS = {"recommend", "conditional", "extract_only"}  # 제안 조건 검토에서 넘어올 수 있는 종합 의견


def load_words(path):
    """(신호 단어 목록, 설정 메모). 설정을 읽지 못하거나 비어 있으면 기본 단어를 쓴다."""
    try:
        header, rows = read_table(path)
        got = {r.get("항목"): r.get("값", "") for r in rows}
        if "시연 신호 단어" not in got:
            raise SettingsError("필수 행 없음(시연 신호 단어)")
        words = [w.strip() for w in got["시연 신호 단어"].split(",") if w.strip()]
        if words:
            return words, None
        return DEFAULT_WORDS, "시연 신호 단어가 비어 있어 기본 신호 단어를 썼습니다."
    except SettingsError as e:
        return DEFAULT_WORDS, f"demo-criteria.md를 읽지 못해({e}) 기본 신호 단어를 썼습니다."


def _verdict(signal, words):
    ev = signal.get("evidence") or {}
    quote, location = ev.get("quote") or "", ev.get("location") or ""
    return "confirmed" if quote and location and any(w in quote for w in words) else "needs_check"


def build_brief(extraction, eligibility, criteria_path):
    """시연 신호 JSON과 제안 조건 검토 결과(없으면 None)로 시연 브리프 하나를 만든다."""
    words, note = load_words(Path(criteria_path))
    signals = []
    for s in extraction.get("signals") or []:
        ev = s.get("evidence") or {}
        signals.append({"text": s.get("text"), "deliverable": s.get("deliverable"), "verdict": _verdict(s, words),
                        "evidence": {"quote": ev.get("quote") or None, "location": ev.get("location") or None}})
    unreadable = list(extraction.get("unreadable_files") or [])

    overall = (eligibility or {}).get("overall")
    passed = overall is None or overall in PASS
    confirmed = [s for s in signals if s["verdict"] == "confirmed"]
    if not passed:
        needed, reason = "no", f"제안 조건 검토 결과가 {overall}이라 시연 데모를 만들지 않습니다."
    elif confirmed:
        needed, reason = "yes", f"공고가 시연·시안을 요구합니다(근거 확인 {len(confirmed)}건)."
    elif signals or unreadable:
        needed = "needs_check"
        reason = "근거가 확인되지 않은 신호가 있거나 읽지 못한 첨부가 있어 대표 확인이 필요합니다."
    else:
        needed, reason = "no", "공고문과 첨부에서 시연·시안 요구를 찾지 못했습니다."
    if overall is None and passed:
        reason += " 제안 조건 검토 결과 없이 판정했습니다."

    kinds = {s["deliverable"] for s in confirmed}
    if needed != "yes":
        deliverable = "none"
    elif {"character", "screen"} <= kinds:
        deliverable = "both"
    else:
        deliverable = next((k for k in ("character", "screen") if k in kinds), "unspecified")

    return {"bid_id": extraction.get("bid_id"), "title": extraction.get("title"),
            "gate": {"eligibility": overall, "passed": passed},
            "demo_needed": needed, "reason": reason, "deliverable": deliverable, "signals": signals,
            "scoring": list(extraction.get("scoring") or []), "constraints": dict(extraction.get("constraints") or {}),
            "ai_use_notes": list(extraction.get("ai_use_notes") or []), "style_refs": list(extraction.get("style_refs") or []),
            "unreadable_files": unreadable,
            "settings_note": note, "disclaimer": DISCLAIMER}

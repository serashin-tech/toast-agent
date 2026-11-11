"""인용 대조: Claude가 추출한 근거 문장이 첨부 원문에 실제로 있는지 본다(H9).

공백과 줄바꿈 차이, 마크다운 굵은 글씨 표시(**, __)는 무시한다(한글 문서를 텍스트로 바꾸면 줄이 임의로 끊기고,
kordoc은 굵은 글씨를 **로 남긴다).
ponytail: 글자 그대로 포함되는지만 본다. 따옴표·괄호 모양이 달라도 못 찾으며, 그때는 확인필요로 내려가 안전한 쪽이다.
"""
import re
from pathlib import Path

_WS = re.compile(r"\s+|\*\*|__")


def _norm(text):
    return _WS.sub("", text or "")


def load_source(folder):
    """원문 폴더의 .md·.txt를 모두 이어 붙인다."""
    files = sorted(p for p in Path(folder).rglob("*") if p.suffix.lower() in (".md", ".txt") and p.is_file())
    return _norm("".join(p.read_text(encoding="utf-8", errors="replace") for p in files))


def mark(extraction, source):
    """requirements·signals의 evidence에 quote_found를 붙인다. source는 load_source의 결과."""
    for key in ("requirements", "signals"):
        for item in extraction.get(key) or []:
            ev = item.setdefault("evidence", {}) or {}
            quote = _norm(ev.get("quote"))
            ev["quote_found"] = bool(quote) and quote in source
            item["evidence"] = ev
    return extraction


def evidence_of(ev):
    """판정 결과에 싣는 근거 모양. 인용 대조를 했으면 quote_found도 함께 싣는다(eligibility·brief가 함께 쓴다)."""
    out = {"quote": ev.get("quote") or None, "location": ev.get("location") or None}
    if "quote_found" in ev:
        out["quote_found"] = ev["quote_found"]
    return out

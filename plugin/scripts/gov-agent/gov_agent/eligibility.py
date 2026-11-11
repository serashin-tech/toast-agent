"""제안 가능성 검토: 추출된 요건과 회사 프로필 설정을 결정적으로 대조한다.

요건 추출(Claude)은 이 코드의 입력이다. 확인되지 않은 값은 절대 충족으로 처리하지 않는다.
"""
import re
from pathlib import Path

from .quotes import evidence_of
from .settings import SettingsError, load_profile

DISCLAIMER = "최종 판단은 대표가 합니다. 이 의견은 확인된 프로필 값과 공고문 근거 문장만으로 만든 참고 자료이며 낙찰 가능성을 보증하지 않습니다."
CONFIRMED = "확인됨"

# 요건 kind -> 회사 프로필 항목 이름
PROFILE_ITEM = {"업종등록": "등록한 업종(나라장터)", "직접생산확인": "직접생산확인", "중소기업확인": "중소기업 확인",
                "소기업소상공인확인": "소기업·소상공인 확인", "벤처확인": "벤처기업 확인", "부설연구소": "기업부설연구소",
                "소재지": "소재지", "실적": "수행 실적", "인력": "보유 인력(직무별 인원, 경력 연수)"}
YES = {"보유", "있음", "예", "확인", "해당", "y", "o"}
NO = {"미보유", "없음", "아니오", "아니요", "해당없음", "해당 없음", "n", "x"}
_UNIT = {"억": 10**8, "천만": 10**7, "백만": 10**6, "만": 10**4, "천": 10**3, "": 1}
_AMOUNT = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(억|천만|백만|만|천)?\s*원")


def _amount(text):
    m = _AMOUNT.search(text or "")
    return int(float(m.group(1).replace(",", "")) * _UNIT[m.group(2) or ""]) if m else None


def _flag(entry, req):
    v = entry["value"].strip().lower()
    if v in NO:
        return "unmet"
    if v in YES:
        return "met"
    return "needs_check"


def _license_key(text):
    """업종코드 표기 "(6490)"와 공백을 지워 비교한다(애니메이션 제작업(6490) == 애니메이션제작업)."""
    return re.sub(r"\(\d+\)|\s", "", text)


def _license(entry, req):
    """공고의 "A 또는 B" 업종 제한은 하나라도 등록돼 있으면 충족이다."""
    want = (req["params"].get("업종") or "").strip()
    if not want or not entry["value"].strip():
        return "needs_check"
    have = _license_key(entry["value"])
    alts = [k for k in (_license_key(a) for a in want.split("또는")) if k]
    if not alts:
        return "needs_check"
    return "met" if any(k in have for k in alts) else "unmet"


# 광역 지자체: 줄임 이름 -> 공식 이름과 옛 이름. 표기 차이로 틀린 미충족이 나오지 않게 한다.
_PROVINCES = {"서울": ["서울특별시"], "부산": ["부산광역시"], "대구": ["대구광역시"], "인천": ["인천광역시"],
              "광주": ["광주광역시"], "대전": ["대전광역시"], "울산": ["울산광역시"], "세종": ["세종특별자치시"],
              "경기": ["경기도"], "강원": ["강원특별자치도", "강원도"], "충북": ["충청북도"], "충남": ["충청남도"],
              "전북": ["전북특별자치도", "전라북도"], "전남": ["전라남도"], "경북": ["경상북도"], "경남": ["경상남도"],
              "제주": ["제주특별자치도", "제주도"]}


def _short_region(text):
    """공식 이름과 옛 이름을 줄임 이름으로 바꾼다(전북특별자치도 -> 전북)."""
    for short, longs in _PROVINCES.items():
        for name in longs:
            text = text.replace(name, short)
    return text


def _province(text):
    """문자열에서 광역 지자체(줄임 이름) 하나를 찾는다. 하나로 정해지지 않으면 None."""
    found = {short for short in _PROVINCES if short in text}
    return found.pop() if len(found) == 1 else None


def _location(entry, req):
    want = (req["params"].get("지역") or "").strip()
    if not want or not entry["value"].strip():
        return "needs_check"
    want, have = _short_region(want), _short_region(entry["value"])
    if want in have:
        return "met"
    # 서로 다른 광역 지자체로 확인될 때만 미충족이다. 시·군만 적힌 요건처럼 판단할 수 없으면 확인필요이다.
    pw, ph = _province(want), _province(have)
    return "unmet" if pw and ph and pw != ph else "needs_check"


def _personnel(entry, req):
    role, need = req["params"].get("role"), req["params"].get("min_count")
    counts = {}
    for seg in entry["value"].split(","):
        m = re.match(r"^\s*(.*?)\s*[:=]?\s*(\d+)\s*명?\s*$", seg)
        if m and m.group(1):
            counts[m.group(1)] = int(m.group(2))
    if not role or need is None or not counts:
        return "needs_check"
    have = sum(n for k, n in counts.items() if role in k)
    return "met" if have >= need else "unmet"


_EVAL = {"업종등록": _license, "소재지": _location, "인력": _personnel}


def _records(profile, req):
    rows = [e for k, e in profile.items() if k.startswith("수행 실적")]
    need, min_amount = req["params"].get("min_count", 1), req["params"].get("min_amount")
    if not rows:
        return "needs_check"
    sure = maybe = 0
    for e in rows:
        if e["status"] != CONFIRMED:
            maybe += 1
            continue
        if min_amount is None:
            sure += 1
            continue
        a = _amount(e["value"])
        if a is None:
            maybe += 1
        elif a >= min_amount:
            sure += 1
    return "met" if sure >= need else "needs_check" if sure + maybe >= need else "unmet"


def _judge(req, profile):
    """(verdict, profile_item)."""
    kind = req.get("kind")
    item = PROFILE_ITEM.get(kind)
    ev = req.get("evidence") or {}
    if not (ev.get("quote") and ev.get("location")) or ev.get("quote_found") is False or item is None:
        return "needs_check", item
    if kind == "실적":
        return _records(profile, req), item
    entry = profile.get(item)
    if not entry or entry["status"] != CONFIRMED:
        return "needs_check", item
    return _EVAL.get(kind, _flag)(entry, req), item


def build_eligibility(extraction, profile_path):
    """요건 JSON(docs/eligibility-input.md)과 회사 프로필 설정으로 eligibility 항목 하나를 만든다."""
    try:
        profile = load_profile(Path(profile_path)) if profile_path else None
    except SettingsError:
        profile = None
    out = []
    for r in extraction.get("requirements", []):
        r = {**r, "params": r.get("params") or {}}
        verdict, item = ("extract_only", None) if profile is None else _judge(r, profile)
        out.append({"category": r.get("category"), "text": r.get("text"), "verdict": verdict, "profile_item": item,
                    "evidence": evidence_of(r.get("evidence") or {})})
    v = [x["verdict"] for x in out]
    n = {k: v.count(k) for k in ("met", "unmet", "needs_check")}
    count = f"충족 {n['met']}건, 미충족 {n['unmet']}건, 확인필요 {n['needs_check']}건"
    if profile is None:
        overall, reason = "extract_only", f"회사 프로필이 없거나 읽지 못해 요건 {len(out)}건만 추출했습니다. 대조는 하지 않았습니다."
    elif n["unmet"]:
        overall, reason = "not_recommend", f"미충족 요건이 있습니다({count})."
    elif n["needs_check"] or not out:
        overall = "conditional"
        reason = f"확인이 필요한 요건이 있습니다({count})." if out else "추출된 요건이 없어 충족 여부를 판단하지 못했습니다."
    else:
        overall, reason = "recommend", f"확인된 요건이 모두 충족입니다({count})."
    return {"bid_id": extraction.get("bid_id"), "overall": overall, "reason": reason, "disclaimer": DISCLAIMER,
            "unreadable_files": list(extraction.get("unreadable_files") or []), "requirements": out}

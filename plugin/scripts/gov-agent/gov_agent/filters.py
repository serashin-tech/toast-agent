"""필터, 지원사업 병합. 모두 결정적인 규칙이다."""
import re


def _hits(text, words):
    t = (text or "").lower()
    return [w for w in words if w.lower() in t]


def filter_bid(it, cfg, run_date):
    """(통과 여부, 일치한 포함 키워드)."""
    matched = _hits(it["title"], cfg["include"])
    if cfg["include"] and not matched:
        return False, []
    if _hits(it["title"], cfg["exclude"]):
        return False, []
    price = it["est_price"]
    if price is not None:
        if cfg["price_min"] is not None and price < cfg["price_min"]:
            return False, []
        if cfg["price_max"] is not None and price > cfg["price_max"]:
            return False, []
    if cfg["min_days"] is not None and it["deadline"] and (it["deadline"] - run_date).days < cfg["min_days"]:
        return False, []
    if it.get("agency_type") and _hits(it["agency_type"], cfg["exclude_types"]):
        return False, []
    return True, matched


def filter_grant(it, cfg):
    """관심 기관, 사업 분야, 키워드 중 하나라도 맞으면 통과(전부 비어 있으면 모두 통과). 제외 키워드는 항상 이긴다."""
    text = f"{it['title']} {it.get('summary') or ''}"
    if _hits(text, cfg["exclude"]):
        return False, []
    matched = _hits(text, cfg["keywords"])
    if not (cfg["keywords"] or cfg["fields"] or cfg["agencies"]):
        return True, []
    ok = bool(matched) or bool(_hits(it.get("category"), cfg["fields"])) or bool(_hits(it.get("agency"), cfg["agencies"]))
    return ok, matched


def merge_grants(kocca, bizinfo):
    """같은 사업을 한 건으로 합친다. 대표는 bizinfo, 빈 필드는 kocca로 채운다.

    가정(사용자 확인 전): 정규화한 제목(한글, 영문, 숫자만 남김)과 접수 마감일이 같으면 같은 사업이다.
    반환: [(합친 항목, 출처 목록, 구성원 [(소스, 항목)])]
    """
    key = lambda it: (re.sub(r"[^0-9a-z가-힣]", "", it["title"].lower()), it["deadline"])
    groups = {}
    for src, items in (("grant_bizinfo", bizinfo), ("grant_kocca", kocca)):
        for it in items:
            groups.setdefault(key(it), {}).setdefault(src, it)
    out = []
    for g in groups.values():
        origins = list(g)
        main = dict(g.get("grant_bizinfo") or g["grant_kocca"])
        other = g.get("grant_kocca")
        if "grant_bizinfo" in g and other:
            for k, v in other.items():
                if main.get(k) in (None, ""):
                    main[k] = v
        out.append((main, origins, [(s, g[s]) for s in origins]))
    return out

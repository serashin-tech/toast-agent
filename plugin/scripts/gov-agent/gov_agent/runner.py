"""수집 실행: 소스별 수집(서로 격리), 필터, 증분, 병합, 결과 파일 작성."""
import hashlib
import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from . import settings as st
from .filters import filter_bid, filter_grant, merge_grants
from .sources import ALL
from .sources import _common as c

KST = timezone(timedelta(hours=9))
FORMAT_VERSION = "1"
FIRST_RUN_DAYS = 1  # 처음 실행(상태 없음)에는 하루 전부터 조회한다


def _fp(item):
    return hashlib.sha1(json.dumps(item, sort_keys=True, default=str, ensure_ascii=False).encode()).hexdigest()


def _iso(d):
    return d.isoformat() if d else None


def _load_state(path):
    try:
        s = json.loads(Path(path).read_text(encoding="utf-8"))
        return {"sources": s.get("sources", {}), "seen": s.get("seen", {}), "calls": s.get("calls", {})}
    except (OSError, ValueError):
        return {"sources": {}, "seen": {}, "calls": {}}


def _fetch(src, transport, key, state, env, now, run_date_s, call_budget):
    """한 소스를 수집한다. 어떤 실패도 이 함수 밖으로 새지 않는다."""
    budget = c.Budget(state["calls"].get(run_date_s, {}).get(src.ID, 0), call_budget)
    since_s = state["sources"].get(src.ID, {}).get("last_success_at")
    since = datetime.fromisoformat(since_s) if since_s else None
    raws, status, error = [], "ok", None
    try:
        if hasattr(src, "fetch"):  # 인증키가 필요 없는 공개 소스(RSS)
            raws = src.fetch(transport, env, budget)
        elif not key:
            raise c.SourceError("auth", "인증키(DATA_GO_KR_SERVICE_KEY)가 설정되지 않음")
        else:
            window_start = since or now - timedelta(days=FIRST_RUN_DAYS)
            for raw in c.collect(src, transport, key, budget, window_start if src.KIND != "grant" else since, now, env):
                raws.append(raw)
    except c.SourceError as e:
        status, error = "failed", {"kind": e.kind, "message": c.scrub(e.message, key)}
    except c.LimitNear:
        status = "limit_near"
        error = {"kind": "rate_limit", "message": f"하루 호출 예산 {call_budget}회에 도달해 중단함"}
    state["calls"].setdefault(run_date_s, {})[src.ID] = budget.used
    cands = {}
    for raw in raws:
        it = src.normalize(raw)
        if it:
            cands[it["id"]] = it  # 공고번호 기준 중복 제거
    cands = list(cands.values())
    floor = since or (now - timedelta(days=src.FIRST_RUN_DAYS) if hasattr(src, "FIRST_RUN_DAYS") else None)
    if getattr(src, "LOCAL_INCREMENT", False) and floor:
        cands = [i for i in cands if not i["posted_on"] or i["posted_on"] >= floor.date()]
    return {"src": src, "status": status, "error": error, "fetched": len(raws), "cands": cands,
            "since": since_s, "excluded": 0, "included": 0, "new": 0}


def run(run_date, out_dir, settings_dir, state_dir, transport, env=None, now=None, call_budget=900):
    run_date_d = date.fromisoformat(run_date) if isinstance(run_date, str) else run_date
    run_date_s = run_date_d.isoformat()
    now = now or datetime.now(KST)
    env = dict(os.environ if env is None else env)
    key = (env.get("DATA_GO_KR_SERVICE_KEY") or "").strip()
    state_dir = Path(state_dir)
    state = _load_state(state_dir / "state.json")
    state["calls"] = {run_date_s: state["calls"].get(run_date_s, {})}  # 지난 날짜의 호출 수는 버린다

    cfg, problems, files = st.load_all(settings_dir, state_dir / "last_good_settings")
    res = {s.ID: _fetch(s, transport, key, state, env, now, run_date_s, call_budget) for s in ALL}
    seen = dict(state["seen"])
    new_seen, items = {}, []

    def fresh(source_id, it):
        k = f"{source_id}:{it['id']}"
        new_seen[k] = _fp(it)
        return seen.get(k) != new_seen[k], k not in seen

    r = res["bid"]
    for it in r["cands"]:
        ok, matched = filter_bid(it, cfg["bid"], run_date_d)
        if not ok:
            r["excluded"] += 1
            continue
        is_changed, is_new = fresh("bid", it)
        if not is_changed:
            continue
        r["included"] += 1
        r["new"] += is_new
        items.append(_item("bid", "bid", it, matched, is_new, {
            "agency": it["agency"], "demand_agency": it["demand_agency"], "est_price": it["est_price"],
            "attachments": it["attachments"]}))

    r = res["outsource_cglink"]
    for it in r["cands"]:  # 한 달에 몇 건뿐이라 필터 없이 새 글을 모두 싣는다
        is_changed, is_new = fresh("outsource_cglink", it)
        if not is_changed:
            continue
        r["included"] += 1
        r["new"] += is_new
        items.append(_item("outsource_cglink", "outsource", it, [], is_new, {"poster": it["poster"]}))

    passed = {}
    for sid in ("grant_kocca", "grant_bizinfo"):
        r = res[sid]
        passed[sid] = []
        for it in r["cands"]:
            ok, matched = filter_grant(it, cfg["grant"])
            if ok:
                passed[sid].append({**it, "_matched": matched})
            else:
                r["excluded"] += 1
    for main, origins, members in merge_grants(passed["grant_kocca"], passed["grant_bizinfo"]):
        flags = [fresh(s, m) for s, m in members]
        if not any(f[0] for f in flags):
            continue
        is_new = all(f[1] for f in flags)
        for s in origins:
            res[s]["included"] += 1
            res[s]["new"] += is_new
        matched = sorted({w for _, m in members for w in m["_matched"]}, key=main["title"].lower().find)
        dday = (main["deadline"] - run_date_d).days if main["deadline"] else None
        items.append(_item(origins[0] if len(origins) == 1 else "grant", "grant", main, matched, is_new, {
            "agency": main["agency"], "period_start": _iso(main["period_start"]),
            "period_end": _iso(main["deadline"]), "dday": dday, "category": main["category"],
            "target": main["target"], "contact": main["contact"], "origins": origins}))

    sources = []
    for s in ALL:
        r = res[s.ID]
        ok = r["status"] == "ok"
        if ok:
            state["sources"][s.ID] = {"last_success_at": now.isoformat()}
            state["seen"].update({k: v for k, v in new_seen.items() if k.startswith(s.ID + ":")})
        sources.append({"id": s.ID, "label": s.LABEL, "status": r["status"], "fetched": r["fetched"],
                        "included": r["included"], "excluded": r["excluded"], "new_count": r["new"],
                        "error": r["error"],
                        "last_success_at": state["sources"].get(s.ID, {}).get("last_success_at")})

    result = {"format_version": FORMAT_VERSION, "agent": "gov", "run_date": run_date_s,
              "generated_at": now.isoformat(), "sources": sources, "items": items, "eligibility": [],
              "settings": {"fallback_used": bool(problems), "fallback_reason": "; ".join(problems) or None,
                           "files": files}}
    text = c.scrub(json.dumps(result, ensure_ascii=False, indent=2), key)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"gov_{run_date_s}.json"
    path.write_text(text, encoding="utf-8")
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "state.json").write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    if not problems:
        st.save_good(settings_dir, state_dir / "last_good_settings")
    return path


def _item(source, kind, it, matched, is_new, extra):
    return {"source": source, "kind": kind, "id": it["id"], "title": it["title"],
            "posted_on": _iso(it["posted_on"]), "deadline": _iso(it["deadline"]), "url": it["url"],
            "matched_keywords": matched, "summary": None, "is_new": is_new, "extra": extra}

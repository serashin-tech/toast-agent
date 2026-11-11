"""수집 실행: 소스별 수집(서로 격리), 필터, 증분, 병합, 결과 파일 작성."""
import hashlib
import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from . import settings as st
from .filters import filter_bid, filter_grant, grant_key, merge_grants
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
        return {"sources": s.get("sources", {}), "calls": s.get("calls", {})}
    except (OSError, ValueError):
        return {"sources": {}, "calls": {}}


def _load_ledger(state_dir, out_dir):
    """로컬 원장(IM-09)을 읽고, 결과 폴더의 노출 기록(shown_*.json)으로 첫 노출일을 채운다.

    이미 채운 첫 노출일은 바꾸지 않으므로 같은 노출 기록을 여러 번 읽어도 결과가 같다. 원장에 없는 키는 무시한다.
    """
    try:
        ledger = json.loads((state_dir / "ledger.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        ledger = {}
    for p in sorted(Path(out_dir).glob("shown_*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for k in data.get("keys") or []:
            if k in ledger and not ledger[k].get("first_shown"):
                ledger[k]["first_shown"] = data.get("date")
    return ledger


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
            "since": since_s, "excluded": 0, "included": 0, "new": 0, "changed_shown": 0}


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
    ledger = _load_ledger(state_dir, out_dir)
    touched, items = {}, []

    # 지원사업은 한콘진·중소기업 두 출처에 따로 올라와 날짜가 어긋날 수 있으므로, 같은 사업의 열쇠로도 노출을 본다.
    shown_groups = {e["group"] for e in ledger.values() if e.get("group") and e.get("first_shown")}

    def check(source_id, it, row, group=None, alias_of=None):
        """(이미 보여 줬는가, 보여 준 뒤 내용이 바뀌었는가). 노출 판정의 정본은 로컬 원장이다(D13).

        실행 끝에 원장에 반영할 값(지문, 시트 행 필드, 같은 사업 열쇠, 대표 행 키)도 함께 적어 둔다.
        """
        k = f"{source_id}:{it['id']}"
        fp = _fp(it)
        touched[k] = (source_id, fp, group, row, alias_of)
        e = ledger.get(k) or {}
        was_shown = bool(e.get("first_shown")) or (group is not None and group in shown_groups)
        return was_shown, was_shown and e.get("fp") not in (None, fp)

    def row_of(kind, source, it, agency, price, matched):
        """시트 '수집 이력'의 코드가 쓰는 열(티켓 21). 상태와 대표 메모는 시트가 가진다."""
        return {"kind": kind, "source": source, "title": it["title"], "agency": agency or "", "price": price,
                "deadline": _iso(it["deadline"]), "registered": _iso(it["posted_on"]), "url": it["url"],
                "matched": ", ".join(matched)}

    r = res["bid"]
    for it in r["cands"]:
        ok, matched = filter_bid(it, cfg["bid"], run_date_d)
        if not ok:
            r["excluded"] += 1
            continue
        was_shown, changed = check("bid", it, row_of("bid", "bid", it, it["agency"], it["est_price"], matched))
        if was_shown:
            r["changed_shown"] += changed
            continue
        r["included"] += 1
        r["new"] += 1
        items.append(_item("bid", "bid", it, matched, [f"bid:{it['id']}"], {
            "agency": it["agency"], "demand_agency": it["demand_agency"], "est_price": it["est_price"],
            "attachments": it["attachments"]}))

    r = res["outsource_cglink"]
    for it in r["cands"]:  # 한 달에 몇 건뿐이라 필터 없이 새 글을 모두 싣는다
        was_shown, changed = check("outsource_cglink", it,
                                   row_of("outsource", "outsource_cglink", it, it["poster"], None, []))
        if was_shown:
            r["changed_shown"] += changed
            continue
        r["included"] += 1
        r["new"] += 1
        items.append(_item("outsource_cglink", "outsource", it, [], [f"outsource_cglink:{it['id']}"],
                           {"poster": it["poster"]}))

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
        group = "|".join(str(x) for x in grant_key(main))
        matched = sorted({w for _, m in members for w in m["_matched"]}, key=main["title"].lower().find)
        keys = [f"{s}:{m['id']}" for s, m in members]  # 첫 키가 대표 행(중소기업 쪽이 있으면 그쪽)
        row = row_of("grant", origins[0] if len(origins) == 1 else "grant", main, main["agency"], None, matched)
        flags = [check(s, m, row, group, None if i == 0 else keys[0]) for i, (s, m) in enumerate(members)]
        if any(f[0] for f in flags):  # 출처 하나라도 보여 줬으면 보여 준 것으로 본다
            for s in origins:
                res[s]["changed_shown"] += any(f[1] for f in flags)
            continue
        for s in origins:
            res[s]["included"] += 1
            res[s]["new"] += 1
        dday = (main["deadline"] - run_date_d).days if main["deadline"] else None
        items.append(_item(origins[0] if len(origins) == 1 else "grant", "grant", main, matched, keys, {
            "agency": main["agency"], "period_start": _iso(main["period_start"]),
            "period_end": _iso(main["deadline"]), "dday": dday, "category": main["category"],
            "target": main["target"], "contact": main["contact"], "origins": origins}))

    sources = []
    for s in ALL:
        r = res[s.ID]
        ok = r["status"] == "ok"
        if ok:
            state["sources"][s.ID] = {"last_success_at": now.isoformat()}
        sources.append({"id": s.ID, "label": s.LABEL, "status": r["status"], "fetched": r["fetched"],
                        "included": r["included"], "excluded": r["excluded"], "new_count": r["new"],
                        "changed_shown_count": r["changed_shown"], "error": r["error"],
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
    for k, (sid, fp, group, row, alias_of) in touched.items():  # 정상 수집한 소스의 항목만 원장에 반영한다
        if res[sid]["status"] != "ok":
            continue
        e = ledger.setdefault(k, {"first_seen": run_date_s, "last_changed": None, "first_shown": None, "fp": fp})
        e.update(row)
        e.pop("alias_of", None)
        if alias_of:
            e["alias_of"] = alias_of
        if group:
            e["group"] = group
        if e["fp"] != fp:
            e["fp"], e["last_changed"] = fp, run_date_s
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "state.json").write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    (state_dir / "ledger.json").write_text(json.dumps(ledger, ensure_ascii=False, indent=1), encoding="utf-8")
    if not problems:
        st.save_good(settings_dir, state_dir / "last_good_settings")
    return path


def _item(source, kind, it, matched, keys, extra):
    """결과 파일의 항목 하나. 아직 보여 주지 않은 항목만 싣으므로 is_new는 늘 참이다(D13)."""
    return {"source": source, "kind": kind, "id": it["id"], "title": it["title"],
            "posted_on": _iso(it["posted_on"]), "deadline": _iso(it["deadline"]), "url": it["url"],
            "matched_keywords": matched, "summary": None, "is_new": True, "keys": keys, "extra": extra}

"""실행 기록(runs.jsonl)과 11시 도착률. 날짜마다 한 줄이 기본이고, 같은 날 다시 실행하면 줄이 더 붙는다."""
import json
import pathlib
from datetime import date, datetime, time, timedelta, timezone

KST = timezone(timedelta(hours=9))
DEADLINE = "11:00"  # 도착 기준 시각. 루틴 10:00 시작, 보고 마감 10:50(D5)


def _file(runs_dir):
    return pathlib.Path(runs_dir) / "runs.jsonl"


def load_runs(runs_dir):
    p = _file(runs_dir)
    if not p.is_file():
        return []
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def _save(runs_dir, records):
    pathlib.Path(runs_dir).mkdir(parents=True, exist_ok=True)
    _file(runs_dir).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")


def source_status(agents):
    """소스별 성공 여부와 사유 종류만 남긴다(오류 메시지는 기록하지 않는다)."""
    out = {}
    for a in agents:
        if not a["ok"]:
            out[a["agent"]] = {"ok": False, "reason": a["error"]}
            continue
        for s in a["sources"]:
            ok = s["status"] == "ok"
            reason = None if ok else ("limit_near" if s["status"] == "limit_near" else (s["error"] or {}).get("kind"))
            out[s["id"]] = {"ok": ok, "reason": reason}
    return out


def append_run(runs_dir, record):
    _save(runs_dir, load_runs(runs_dir) + [record])


def _on_time(run_date, published_at, deadline):
    at = datetime.fromisoformat(published_at)
    return at <= datetime.combine(run_date, time.fromisoformat(deadline), tzinfo=at.tzinfo)


def write_shown(results_dir, date_s):
    """그날 결과 파일에 실린 항목의 원장 키를 노출 기록(shown_<날짜>.json)으로 쓴다. 반환: 키 개수.

    병합한 지원사업은 출처 키 둘을 모두 담는다(gov가 항목의 keys에 넣어 둔다). keys가 없는 옛 파일은 source:id를 쓴다.
    """
    results_dir = pathlib.Path(results_dir)
    keys = []
    for p in sorted(results_dir.glob(f"*_{date_s}.json")):
        if p.name.startswith("shown_"):
            continue
        try:
            items = json.loads(p.read_text(encoding="utf-8")).get("items") or []
        except (OSError, ValueError, AttributeError):
            continue
        for it in items:
            keys += it.get("keys") or [f"{it.get('source')}:{it.get('id')}"]
    (results_dir / f"shown_{date_s}.json").write_text(json.dumps({"date": date_s, "keys": keys}, ensure_ascii=False),
                                                      encoding="utf-8")
    return len(keys)


def record_publish(runs_dir, date_s, at_iso, ok, deadline=DEADLINE, results_dir=None):
    """그날 daily 루틴의 마지막 줄에 전달(신규 알림 메일 발송) 결과를 기록한다(D31). 줄이 없으면 새로 만든다.

    review 루틴의 줄에는 붙이지 않는다. 성공했고 results_dir가 있으면 노출 기록도 쓴다.
    """
    records = load_runs(runs_dir)
    idx = max((i for i, r in enumerate(records)
               if r.get("date") == date_s and r.get("routine", "daily") == "daily"), default=None)
    if idx is None:
        records.append({"date": date_s, "routine": "daily", "report_ok": None})
        idx = len(records) - 1
    late = not _on_time(date.fromisoformat(date_s), at_iso, deadline)
    records[idx].update(published_ok=ok, published_at=at_iso, publish_late=late)
    if ok and results_dir:
        records[idx]["shown_count"] = write_shown(results_dir, date_s)
    _save(runs_dir, records)


def _d(v):
    return v if isinstance(v, date) else date.fromisoformat(str(v))


def arrival_rate(runs, start, end, deadline=DEADLINE):
    """기간(양끝 포함)의 모든 날짜가 분모다. 기록이 없는 날은 미실행이며, 마감 시각까지 게시에 성공한 날만 분자다."""
    start, end = _d(start), _d(end)
    by_day = {}
    for r in runs:
        by_day.setdefault(r.get("date"), []).append(r)
    days = (end - start).days + 1
    arrived = not_run = 0
    for n in range(days):
        day = start + timedelta(days=n)
        recs = by_day.get(day.isoformat())
        if not recs:
            not_run += 1
        elif any(r.get("published_ok") is True and r.get("published_at")
                 and _on_time(day, r["published_at"], deadline) for r in recs):
            arrived += 1
    return {"days": days, "arrived": arrived, "not_run": not_run,
            "late_or_failed": days - arrived - not_run, "rate": arrived / days if days else 0.0}

"""명령줄 진입점: build, record-publish, arrival-rate.

이 코드는 호출된 시점에 있는 결과 파일만으로 보고서를 만든다. 10:50 시간 상자는 호출하는 루틴의 일이고,
게시(artifact)도 이 코드의 일이 아니다. 네트워크에 접근하지 않는다.
"""
import argparse
import pathlib
from datetime import datetime, timedelta

from . import inputs, render, runs


def count_delta(today, prev):
    """오늘과 전날 모두 수집에 성공한 소스만 비교해 포함·제외 건수를 합한다. 비교할 소스가 없으면 None."""
    prev_by = {a["agent"]: {s["id"]: s for s in a["sources"] if s["status"] == "ok"} for a in prev if a["ok"]}
    t_inc = t_exc = p_inc = p_exc = n = 0
    for a in today:
        if not a["ok"]:
            continue
        for s in a["sources"]:
            p = prev_by.get(a["agent"], {}).get(s["id"])
            if s["status"] == "ok" and p:
                t_inc += s["included"] or 0
                t_exc += s["excluded"] or 0
                p_inc += p["included"] or 0
                p_exc += p["excluded"] or 0
                n += 1
    return {"included": (t_inc, p_inc), "excluded": (t_exc, p_exc)} if n else None


def _build(args, now):
    started = now()
    run_date = inputs.parse_date(args.date)
    agents = [inputs.load_agent(args.results, a, run_date) for a in inputs.EXPECTED_AGENTS]
    changes = inputs.recent_changes(args.settings, run_date)
    counts = None
    if changes:  # 전날 파일은 건수 비교에만 쓴다. 오늘 결과를 대신하지 않는다.
        prev = [inputs.load_agent(args.results, a, run_date - timedelta(days=1)) for a in inputs.EXPECTED_AGENTS]
        counts = count_delta(agents, prev)
    html = render.render(run_date, agents, changes, counts)
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"report-{args.date}.html").write_text(html, encoding="utf-8")
    if args.runs:
        runs.append_run(args.runs, {
            "date": args.date, "routine": args.routine, "started_at": started.isoformat(timespec="seconds"),
            "finished_at": now().isoformat(timespec="seconds"), "sources": runs.source_status(agents),
            "report_ok": True, "published_ok": None,
        })
    return 0


def main(argv=None, now=None):
    now = now or (lambda: datetime.now(runs.KST))
    p = argparse.ArgumentParser(prog="daily_report")
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="보고서 HTML 한 장과 실행 기록을 만든다")
    b.add_argument("--date", required=True)
    b.add_argument("--results", required=True)
    b.add_argument("--out", required=True)
    b.add_argument("--settings")
    b.add_argument("--runs")
    b.add_argument("--routine", choices=["daily", "review"], default="daily", help="실행 기록에 남길 루틴 종류")
    r = sub.add_parser("record-publish", help="전달(신규 알림 메일 발송) 결과를 실행 기록에 적는다(D31)")
    r.add_argument("--runs", required=True)
    r.add_argument("--date", required=True)
    r.add_argument("--at", required=True, help="발송 일시(ISO 8601)")
    r.add_argument("--ok", required=True, choices=["true", "false"])
    r.add_argument("--results", help="결과 폴더. 주면 성공한 날 노출 기록(shown_<날짜>.json)을 쓴다")
    a = sub.add_parser("arrival-rate", help="기간의 11시 도착률을 계산한다")
    a.add_argument("--runs", required=True)
    a.add_argument("--from", dest="start", required=True)
    a.add_argument("--to", dest="end", required=True)
    a.add_argument("--deadline", default=runs.DEADLINE)
    args = p.parse_args(argv)
    if args.cmd == "build":
        return _build(args, now)
    if args.cmd == "record-publish":
        runs.record_publish(args.runs, args.date, args.at, args.ok == "true", results_dir=args.results)
        return 0
    x = runs.arrival_rate(runs.load_runs(args.runs), args.start, args.end, args.deadline)
    print(f"도착 {x['arrived']}/{x['days']}일 ({x['rate']:.1%}), 미실행 {x['not_run']}일, 지연 또는 실패 {x['late_or_failed']}일")
    return 0

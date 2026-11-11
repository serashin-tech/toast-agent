"""명령줄 진입점: build, mail, board, record-publish, arrival-rate.

이 코드는 호출된 시점에 있는 결과 파일만으로 전달물을 만든다. 10:50 시간 상자, 메일 발송(Apps Script),
artifact 게시는 호출하는 루틴의 일이다. 네트워크에 접근하지 않는다.
"""
import argparse
import json
import pathlib
from datetime import datetime, timedelta

from . import deliver, inputs, render, runs, sheet


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


def _sheet(args, transport):
    """시트 웹 앱 요청 네 가지. 실패는 한 줄로 알리고 1을 돌려준다(다음 단계는 루틴이 이어 간다)."""
    env = sheet.read_env(args.env_file)
    if args.cmd == "sheet-push":
        rows = sheet.build_rows(args.state, inputs.parse_date(args.date))
        if rows is None:
            print("시트 기록 실패: 로컬 원장(state/ledger.json)을 읽지 못했습니다")
            return 1
        ok, reply = sheet.call(env, {"action": "upsert", "rows": rows}, transport)
        print(f"시트 기록 {len(rows)}행" if ok else f"시트 기록 실패: {reply}")
    elif args.cmd == "sheet-pull":
        ok, reply = sheet.call(env, {"action": "rows"}, transport)
        if ok:
            out = pathlib.Path(args.out)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps({"rows": reply.get("rows") or []}, ensure_ascii=False), encoding="utf-8")
        print(f"시트 읽기 {len(reply.get('rows') or [])}행" if ok else f"시트 읽기 실패: {reply}")
    elif args.cmd == "sheet-status":
        ok, reply = sheet.call(env, {"action": "status", "key": args.key, "status": args.status}, transport)
        print(f"상태 변경 {args.key} → {args.status}" if ok else f"상태 변경 실패: {reply}")
    else:
        mail = json.loads(pathlib.Path(args.mail).read_text(encoding="utf-8"))
        ok, reply = sheet.call(env, {"action": "mail", "subject": mail["subject"], "html": mail["html"]}, transport)
        print("메일 발송 성공" if ok else f"메일 발송 실패: {reply}")
    return 0 if ok else 1


def main(argv=None, now=None, transport=None):
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
    m = sub.add_parser("mail", help="신규 알림 메일 본문(JSON: subject, html, count)을 만든다(D30)")
    m.add_argument("--date", required=True)
    m.add_argument("--results", required=True)
    m.add_argument("--out", required=True)
    m.add_argument("--board-url")
    m.add_argument("--sheet-url", help="없으면 --env-file의 SHEET_URL을 쓴다")
    m.add_argument("--env-file", default=".env")
    bd = sub.add_parser("board", help="시트 응답 JSON으로 입찰 현황판 HTML을 만든다(D28)")
    bd.add_argument("--date", required=True)
    bd.add_argument("--sheet", required=True, help="Apps Script GET 응답을 저장한 JSON 파일({rows: [...]})")
    bd.add_argument("--out", required=True)
    st = sub.add_parser("record-step", help="메일 밖 단계(sheet, board 등)의 성패를 그날 daily 줄에 남긴다(티켓 22)")
    st.add_argument("--runs", required=True)
    st.add_argument("--date", required=True)
    st.add_argument("--step", required=True)
    st.add_argument("--ok", required=True, choices=["true", "false"])
    sp = sub.add_parser("sheet-push", help="로컬 원장의 마감 전 행을 수집 이력 시트에 보낸다(티켓 21, D29)")
    sp.add_argument("--date", required=True)
    sp.add_argument("--state", default="state", help="gov-agent의 상태 폴더(ledger.json이 있는 곳)")
    sl = sub.add_parser("sheet-pull", help="시트의 마감 전 행을 받아 JSON으로 저장한다(현황판 입력)")
    sl.add_argument("--out", required=True)
    sm = sub.add_parser("send-mail", help="mail 명령이 만든 본문을 Apps Script로 보낸다")
    sm.add_argument("--mail", required=True)
    ss = sub.add_parser("sheet-status", help="시트 행의 상태 칸을 바꾼다(D26)")
    ss.add_argument("--key", required=True)
    ss.add_argument("--status", required=True)
    for x in (sp, sl, sm, ss):
        x.add_argument("--env-file", default=".env")
    a = sub.add_parser("arrival-rate", help="기간의 11시 도착률을 계산한다")
    a.add_argument("--runs", required=True)
    a.add_argument("--from", dest="start", required=True)
    a.add_argument("--to", dest="end", required=True)
    a.add_argument("--deadline", default=runs.DEADLINE)
    args = p.parse_args(argv)
    if args.cmd == "build":
        return _build(args, now)
    if args.cmd in ("sheet-push", "sheet-pull", "send-mail", "sheet-status"):
        return _sheet(args, transport or sheet.http_transport)
    if args.cmd in ("mail", "board"):
        run_date = inputs.parse_date(args.date)
        if args.cmd == "mail":
            agents = [inputs.load_agent(args.results, a, run_date) for a in inputs.EXPECTED_AGENTS]
            sheet_url = args.sheet_url or sheet.read_env(args.env_file).get("SHEET_URL")
            text = json.dumps(deliver.render_mail(run_date, agents, args.board_url, sheet_url), ensure_ascii=False)
        else:
            rows = json.loads(pathlib.Path(args.sheet).read_text(encoding="utf-8")).get("rows") or []
            text = deliver.render_board(run_date, rows)
        out = pathlib.Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        return 0
    if args.cmd == "record-step":
        runs.record_step(args.runs, args.date, args.step, args.ok == "true")
        return 0
    if args.cmd == "record-publish":
        runs.record_publish(args.runs, args.date, args.at, args.ok == "true", results_dir=args.results)
        return 0
    x = runs.arrival_rate(runs.load_runs(args.runs), args.start, args.end, args.deadline)
    print(f"도착 {x['arrived']}/{x['days']}일 ({x['rate']:.1%}), 미실행 {x['not_run']}일, 지연 또는 실패 {x['late_or_failed']}일")
    return 0

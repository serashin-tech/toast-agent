"""실행 기록과 11시 도착률 (경계: CLI와 공개 함수 arrival_rate). 루틴 10:00 시작, 기본 도착 기준 11:00(D5)."""
import contextlib
import io
import json
from datetime import date, datetime, timedelta, timezone

from daily_report import arrival_rate
from daily_report.cli import main
from helpers import ReportCase

KST = timezone(timedelta(hours=9))


def clock(*times):
    it = iter(times)
    return lambda: next(it)


def at(h, m, day=5):
    return datetime(2026, 11, day, h, m, tzinfo=KST)


class RunLog(ReportCase):
    def setUp(self):
        super().setUp()
        self.runs = self.tmp / "runs"

    def lines(self):
        return [json.loads(x) for x in (self.runs / "runs.jsonl").read_text(encoding="utf-8").splitlines()]

    def test_one_line_per_run_with_required_fields(self):
        self.put_today()
        self.build(runs=self.runs, now=clock(at(9, 50), at(9, 50, 5)))
        (rec,) = self.lines()
        self.assertEqual(rec["date"], "2026-11-05")
        self.assertEqual(rec["started_at"], "2026-11-05T09:50:00+09:00")
        self.assertEqual(rec["finished_at"], "2026-11-05T09:50:00+09:00")
        self.assertEqual(rec["sources"]["bid"], {"ok": True, "reason": None})
        self.assertEqual(rec["sources"]["grant_kocca"], {"ok": False, "reason": "rate_limit"})
        self.assertIs(rec["report_ok"], True)
        self.assertIsNone(rec["published_ok"])

    def test_missing_result_file_is_recorded_per_agent(self):
        self.build(runs=self.runs, now=clock(at(9, 50), at(9, 51)))
        (rec,) = self.lines()
        self.assertEqual(rec["sources"], {"gov": {"ok": False, "reason": "missing"}})
        self.assertIs(rec["report_ok"], True)  # 보고서는 실패 소스를 표시한 채로 만들어진다

    def test_each_run_appends_a_line_and_log_has_no_secrets(self):
        self.put_today()
        self.build(runs=self.runs, now=clock(at(9, 50), at(9, 51)))
        self.build(runs=self.runs, now=clock(at(9, 55), at(9, 56)))
        self.assertEqual(len(self.lines()), 2)
        self.assertNotIn("SECRETKEY", (self.runs / "runs.jsonl").read_text(encoding="utf-8"))

    def record_publish(self, at_iso, ok):
        with contextlib.redirect_stdout(io.StringIO()):
            return main(["record-publish", "--runs", str(self.runs), "--date", "2026-11-05", "--at", at_iso, "--ok", ok])

    def test_record_publish_updates_the_same_date_line(self):
        self.put_today()
        self.build(date="2026-11-05", runs=self.runs, now=clock(at(9, 50), at(9, 51)))
        self.assertEqual(self.record_publish("2026-11-05T10:58:00+09:00", "true"), 0)
        (rec,) = self.lines()
        self.assertIs(rec["published_ok"], True)
        self.assertEqual(rec["published_at"], "2026-11-05T10:58:00+09:00")
        self.assertIs(rec["publish_late"], False)

    def test_late_or_failed_publish_is_recorded(self):
        self.put_today()
        self.build(runs=self.runs, now=clock(at(9, 50), at(9, 51)))
        self.record_publish("2026-11-05T11:20:00+09:00", "true")
        self.assertIs(self.lines()[0]["publish_late"], True)
        self.record_publish("2026-11-05T09:59:00+09:00", "false")
        self.assertIs(self.lines()[0]["published_ok"], False)


class ShownRecordAndRoutines(ReportCase):
    """D31: 메일 발송에 성공한 날에만 노출 기록을 남긴다. 검토 #5: 도착 결과는 그날의 daily 줄에만 붙인다."""

    def setUp(self):
        super().setUp()
        self.runs = self.tmp / "runs"

    def lines(self):
        return [json.loads(x) for x in (self.runs / "runs.jsonl").read_text(encoding="utf-8").splitlines()]

    def publish(self, ok, results=True):
        argv = ["record-publish", "--runs", str(self.runs), "--date", "2026-11-05",
                "--at", "2026-11-05T10:58:00+09:00", "--ok", ok]
        if results:
            argv += ["--results", str(self.results)]
        with contextlib.redirect_stdout(io.StringIO()):
            return main(argv)

    def test_successful_send_writes_shown_keys(self):
        def mutate(d):
            d["items"][0]["keys"] = ["grant_kocca:K1", "grant_bizinfo:P1"]
        data = self.put_today(mutate)
        self.build(runs=self.runs, now=clock(at(10, 40), at(10, 41)))
        self.assertEqual(self.publish("true"), 0)
        shown = json.loads((self.results / "shown_2026-11-05.json").read_text(encoding="utf-8"))
        expected = ["grant_kocca:K1", "grant_bizinfo:P1"] + [f"{i['source']}:{i['id']}" for i in data["items"][1:]]
        self.assertEqual(shown["date"], "2026-11-05")
        self.assertEqual(sorted(shown["keys"]), sorted(expected))
        self.assertEqual(self.lines()[0]["shown_count"], len(expected))

    def test_failed_send_writes_no_shown_record(self):
        self.put_today()
        self.build(runs=self.runs, now=clock(at(10, 40), at(10, 41)))
        self.publish("false")
        self.assertFalse((self.results / "shown_2026-11-05.json").exists())

    def test_arrival_attaches_to_the_daily_line_not_a_later_review_line(self):
        self.put_today()
        self.build(runs=self.runs, now=clock(at(10, 0), at(10, 1)))
        argv = ["build", "--date", "2026-11-05", "--results", str(self.results), "--out", str(self.out),
                "--runs", str(self.runs), "--routine", "review"]
        with contextlib.redirect_stdout(io.StringIO()):
            main(argv, now=clock(at(10, 30), at(10, 31)))
        self.publish("true")
        daily, review = self.lines()
        self.assertEqual((daily["routine"], review["routine"]), ("daily", "review"))
        self.assertIs(daily["published_ok"], True)
        self.assertNotIn("published_ok", {k: v for k, v in review.items() if v is not None})


class ArrivalRate(ReportCase):
    def rec(self, day, published_at=None, ok=True):
        return {"date": f"2026-11-0{day}", "report_ok": True, "published_ok": ok if published_at else None,
                "published_at": published_at}

    def runs(self):
        return [
            self.rec(2, "2026-11-02T10:55:00+09:00"),
            self.rec(3, "2026-11-03T11:05:00+09:00"),   # 11시 이후라 지연
            # 11-04는 기록 없음: 미실행
            self.rec(5, "2026-11-05T10:30:00+09:00", ok=False),  # 게시 실패
            self.rec(6, "2026-11-06T11:00:00+09:00"),   # 11:00 정각은 도착
        ]

    def test_every_date_in_range_is_in_the_denominator_and_unrun_days_are_counted(self):
        r = arrival_rate(self.runs(), "2026-11-02", "2026-11-06")
        self.assertEqual((r["days"], r["arrived"], r["not_run"], r["late_or_failed"]), (5, 2, 1, 2))
        self.assertAlmostEqual(r["rate"], 0.4)

    def test_review_lines_do_not_count_as_a_daily_run(self):  # 검토 #c2: 도착은 daily 줄로만 센다
        runs = [{"date": "2026-11-02", "routine": "review", "report_ok": True, "published_ok": None}]
        r = arrival_rate(runs, "2026-11-02", "2026-11-02")
        self.assertEqual((r["not_run"], r["late_or_failed"]), (1, 0))

    def test_deadline_is_adjustable_and_dates_outside_range_are_ignored(self):
        r = arrival_rate(self.runs(), date(2026, 11, 2), date(2026, 11, 3), deadline="11:30")
        self.assertEqual((r["days"], r["arrived"]), (2, 2))

    def test_cli_prints_the_rate_from_runs_jsonl(self):
        d = self.tmp / "runs"
        d.mkdir()
        (d / "runs.jsonl").write_text("\n".join(json.dumps(x) for x in self.runs()), encoding="utf-8")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = main(["arrival-rate", "--runs", str(d), "--from", "2026-11-02", "--to", "2026-11-06"])
        self.assertEqual(code, 0)
        self.assertIn("도착 2/5일 (40.0%)", buf.getvalue())
        self.assertIn("미실행 1일", buf.getvalue())

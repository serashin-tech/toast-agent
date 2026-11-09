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

"""시트 연결 경계(D14, D19, D29, D32): 명령줄 -> Apps Script 웹 앱 요청. 네트워크 계층만 가짜로 바꾼다."""
import contextlib
import io
import json

from daily_report.cli import main
from helpers import ReportCase

URL, TOKEN = "https://script.google.test/exec", "tok-123"


class FakeApp:
    def __init__(self, reply=None, fail=False):
        self.calls, self.reply, self.fail = [], reply or {"ok": True}, fail

    def __call__(self, url, payload):
        self.calls.append((url, payload))
        if self.fail:
            raise OSError("network down")
        return self.reply


class SheetSync(ReportCase):
    def setUp(self):
        super().setUp()
        self.env = self.tmp / ".env"
        self.env.write_text(f"SHEET_APP_URL={URL}\nSHEET_APP_TOKEN={TOKEN}\n", encoding="utf-8")

    def cli(self, argv, app):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = main([*argv, "--env-file", str(self.env)], transport=app)
        return code, buf.getvalue()

    def ledger(self):
        """gov-agent가 쓰는 로컬 원장 모양(티켓 21). 시트 행은 원장의 마감 전 행 전체다."""
        row = {"kind": "bid", "source": "bid", "agency": "전주시", "price": 1, "registered": "2026-11-01",
               "url": "https://g2b.test/x", "matched": "애니메이션", "first_shown": "2026-11-04", "fp": "f"}
        state = self.tmp / "state"
        state.mkdir()
        (state / "ledger.json").write_text(json.dumps({
            "bid:OPEN": {**row, "title": "열린 공고", "deadline": "2026-11-20"},
            "bid:TODAY": {**row, "title": "오늘 마감", "deadline": "2026-11-05"},
            "bid:PAST": {**row, "title": "지난 공고", "deadline": "2026-11-04"},
            "grant_bizinfo:P1": {**row, "kind": "grant", "title": "지원사업", "deadline": "2026-12-01"},
            "grant_kocca:K1": {**row, "kind": "grant", "title": "지원사업", "deadline": "2026-12-01",
                               "alias_of": "grant_bizinfo:P1"},
            "outsource_cglink:OLD": {**row, "kind": "outsource", "title": "오래된 글", "deadline": None,
                                     "registered": "2026-09-01"},
            "bid:LEGACY": {"first_seen": "2026-11-01", "first_shown": None, "fp": "f"},  # 행 필드 없는 옛 항목
        }, ensure_ascii=False), encoding="utf-8")
        return state

    def push(self, app):
        return self.cli(["sheet-push", "--date", "2026-11-05", "--state", str(self.ledger())], app)

    def test_push_sends_every_open_ledger_row_without_memo(self):
        app = FakeApp()
        code, _ = self.push(app)
        self.assertEqual(code, 0)
        (url, payload), = app.calls
        self.assertEqual((url, payload["action"], payload["token"]), (URL, "upsert", TOKEN))
        rows = {r["key"]: r for r in payload["rows"]}
        self.assertEqual(sorted(rows), ["bid:OPEN", "bid:TODAY", "grant_bizinfo:P1"])  # 마감 지남·30일 지난 글·별칭 제외
        self.assertEqual(rows["grant_bizinfo:P1"]["alt_keys"], ["grant_kocca:K1"])
        self.assertEqual((rows["bid:OPEN"]["status"], rows["bid:OPEN"]["registered"]), ("신규", "2026-11-01"))
        self.assertNotIn("memo", rows["bid:OPEN"])  # 대표 메모 열은 건드리지 않는다

    def test_push_failure_is_reported_and_the_rows_go_again_next_time(self):
        code, out = self.push(FakeApp(fail=True))
        self.assertEqual(code, 1)
        self.assertIn("시트 기록 실패", out)
        self.assertNotIn(TOKEN, out)
        import shutil
        shutil.rmtree(self.tmp / "state")
        app = FakeApp()
        self.push(app)  # 원장이 정본이므로 다음 실행이 같은 행을 다시 보낸다
        self.assertIn("bid:OPEN", [r["key"] for r in app.calls[0][1]["rows"]])

    def test_unreadable_ledger_fails_instead_of_sending_nothing(self):  # 티켓 22
        state = self.tmp / "state"
        state.mkdir()
        (state / "ledger.json").write_text("{broken", encoding="utf-8")
        app = FakeApp()
        code, out = self.cli(["sheet-push", "--date", "2026-11-05", "--state", str(state)], app)
        self.assertEqual((code, app.calls), (1, []))
        self.assertIn("원장", out)

    def test_pull_saves_rows_for_the_board(self):
        rows = [{"key": "bid:R1", "kind": "bid", "title": "t", "status": "2차 검토 중"}]
        out_file = self.tmp / "sheet.json"
        code, _ = self.cli(["sheet-pull", "--out", str(out_file)], FakeApp(reply={"ok": True, "rows": rows}))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out_file.read_text(encoding="utf-8"))["rows"], rows)

    def test_send_mail_posts_subject_and_html(self):
        mail = self.tmp / "mail.json"
        mail.write_text(json.dumps({"subject": "s", "html": "<p>h</p>", "count": 1}), encoding="utf-8")
        app = FakeApp()
        code, _ = self.cli(["send-mail", "--mail", str(mail)], app)
        self.assertEqual(code, 0)
        self.assertEqual({k: app.calls[0][1][k] for k in ("action", "subject", "html")},
                         {"action": "mail", "subject": "s", "html": "<p>h</p>"})

    def test_status_change_posts_key_and_value(self):
        app = FakeApp()
        code, _ = self.cli(["sheet-status", "--key", "bid:R1", "--status", "2차 검토 중"], app)
        self.assertEqual(code, 0)
        self.assertEqual({k: app.calls[0][1][k] for k in ("action", "key", "status")},
                         {"action": "status", "key": "bid:R1", "status": "2차 검토 중"})

    def test_missing_settings_fail_cleanly(self):
        self.env.write_text("", encoding="utf-8")
        code, out = self.cli(["sheet-pull", "--out", str(self.tmp / "x.json")], FakeApp())
        self.assertEqual(code, 1)
        self.assertIn("SHEET_APP_URL", out)

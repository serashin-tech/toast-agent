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

    def test_push_sends_new_open_rows_without_memo_and_with_registered_date(self):
        def mutate(d):
            d["items"][0]["deadline"] = "2026-11-04"  # 마감 지남: 보내지 않는다(D29)
        data = self.put_today(mutate)
        app = FakeApp()
        code, _ = self.cli(["sheet-push", "--date", "2026-11-05", "--results", str(self.results)], app)
        self.assertEqual(code, 0)
        (url, payload), = app.calls
        self.assertEqual((url, payload["action"], payload["token"]), (URL, "upsert", TOKEN))
        keys = [r["key"] for r in payload["rows"]]
        self.assertNotIn(f"{data['items'][0]['source']}:{data['items'][0]['id']}", keys)
        row = payload["rows"][0]
        self.assertEqual(row["status"], "신규")
        self.assertIn("registered", row)  # 등록일 열(D32)
        self.assertNotIn("memo", row)  # 대표 메모 열은 건드리지 않는다

    def test_push_failure_is_reported_not_raised(self):
        self.put_today()
        code, out = self.cli(["sheet-push", "--date", "2026-11-05", "--results", str(self.results)], FakeApp(fail=True))
        self.assertEqual(code, 1)
        self.assertIn("시트 기록 실패", out)
        self.assertNotIn(TOKEN, out)

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

    def test_missing_settings_fail_cleanly(self):
        self.env.write_text("", encoding="utf-8")
        code, out = self.cli(["sheet-pull", "--out", str(self.tmp / "x.json")], FakeApp())
        self.assertEqual(code, 1)
        self.assertIn("SHEET_APP_URL", out)

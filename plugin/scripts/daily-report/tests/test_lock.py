"""루틴 잠금(티켓 23, 검토 #5): daily와 review가 같은 잠금 파일 하나로 동시에 쓰지 않는다."""
import contextlib
import io
from datetime import datetime, timedelta, timezone

from daily_report.cli import main
from helpers import ReportCase

KST = timezone(timedelta(hours=9))


class RoutineLock(ReportCase):
    def lock(self, action, owner, minute=0):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = main(["lock", action, "--runs", str(self.tmp / "runs"), "--owner", owner],
                        now=lambda: datetime(2026, 11, 11, 10, minute, tzinfo=KST))
        return code, buf.getvalue()

    def test_second_routine_waits_while_the_first_holds_the_lock(self):
        self.assertEqual(self.lock("acquire", "daily")[0], 0)
        code, out = self.lock("acquire", "review", minute=30)
        self.assertEqual(code, 1)
        self.assertIn("daily", out)

    def test_release_lets_the_other_routine_in(self):
        self.lock("acquire", "daily")
        self.assertEqual(self.lock("release", "daily")[0], 0)
        self.assertEqual(self.lock("acquire", "review", minute=30)[0], 0)

    def test_stale_lock_older_than_an_hour_is_taken_over(self):
        self.lock("acquire", "review", minute=0)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = main(["lock", "acquire", "--runs", str(self.tmp / "runs"), "--owner", "daily"],
                        now=lambda: datetime(2026, 11, 11, 11, 5, tzinfo=KST))
        self.assertEqual(code, 0)
        self.assertIn("오래된 잠금", buf.getvalue())

    def test_release_by_another_owner_keeps_the_lock(self):
        self.lock("acquire", "daily")
        self.lock("release", "review")
        self.assertEqual(self.lock("acquire", "review", minute=30)[0], 1)

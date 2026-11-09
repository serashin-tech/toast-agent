"""민간 외주(CGLink 외주발주 게시판 RSS) 수집."""
import json

from helpers import Base, FakeTransport, ok_routes
import fixtures as fx


class Outsource(Base):
    def run_with(self, posts, date="2026-11-05", **kw):
        return self.run_day(FakeTransport(ok_routes(cglinks=posts)), date=date, **kw)

    def test_post_becomes_outsource_item_without_body_text(self):
        r = self.run_with([fx.cglink("5112927", "게임 3D 그래픽 외주 업체를 찾습니다.",
                                     "Thu, 05 Nov 2026 10:21:00 +0900", "INDIGO3D")])
        [it] = self.items(r, "outsource")
        self.assertEqual((it["source"], it["id"], it["url"], it["posted_on"], it["deadline"], it["is_new"]),
                         ("outsource_cglink", "5112927", "https://cglink.com/5112927", "2026-11-05", None, True))
        self.assertEqual(it["extra"], {"poster": "INDIGO3D"})
        self.assertNotIn("010-0000-0000", json.dumps(r, ensure_ascii=False))  # 본문(연락처가 섞일 수 있음)은 싣지 않는다
        s = self.src(r, "outsource_cglink")
        self.assertEqual((s["status"], s["fetched"], s["included"], s["new_count"]), ("ok", 1, 1, 1))

    def test_first_run_keeps_last_14_days_then_only_new_posts(self):
        old = fx.cglink("1", "오래된 글", "Mon, 19 Oct 2026 10:00:00 +0900")
        recent = fx.cglink("2", "최근 글", "Wed, 28 Oct 2026 10:00:00 +0900")
        r1 = self.run_with([recent, old])
        self.assertEqual([i["id"] for i in self.items(r1, "outsource")], ["2"])
        newer = fx.cglink("3", "새 글", "Thu, 05 Nov 2026 15:00:00 +0900")
        r2 = self.run_with([newer, recent, old], date="2026-11-06")
        self.assertEqual([(i["id"], i["is_new"]) for i in self.items(r2, "outsource")], [("3", True)])

    def test_runs_without_data_go_kr_key(self):
        r = self.run_with([fx.cglink("9", "글", "Thu, 05 Nov 2026 08:00:00 +0900")], env={})
        self.assertEqual(self.src(r, "outsource_cglink")["status"], "ok")
        self.assertEqual(len(self.items(r, "outsource")), 1)

    def test_broken_feed_fails_only_this_source(self):
        for bad, kind in [((200, "<html>점검 중"), "format"), ((503, ""), "network"), (OSError("down"), "network")]:
            with self.subTest(kind=kind, bad=str(bad)):
                self.setUp()
                routes = ok_routes()
                routes["cglink.com"] = bad
                r = self.run_day(FakeTransport(routes))
                s = self.src(r, "outsource_cglink")
                self.assertEqual((s["status"], s["error"]["kind"]), ("failed", kind))
                self.assertEqual(self.src(r, "bid")["status"], "ok")

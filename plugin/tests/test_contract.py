"""결과 계약 경계: gov-agent가 쓴 결과 파일을 daily-report가 형식 오류 없이 모두 읽는다(docs/result-format.md, H10)."""
import json
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

import common  # noqa: F401  경로 설정

import fixtures as fx
from daily_report.inputs import load_agent
from gov_agent.runner import run
from helpers import ENV, KST, FakeTransport, bid_filter_md, grant_md, ok_routes


class ResultContract(unittest.TestCase):
    def test_every_item_gov_writes_is_read_by_daily_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "settings").mkdir()
            (root / "settings" / "bid-filter.md").write_text(bid_filter_md(), encoding="utf-8")
            (root / "settings" / "grant-criteria.md").write_text(grant_md(), encoding="utf-8")
            t = FakeTransport(ok_routes(
                bids=[fx.bid("B1", "홍보 애니메이션 제작")],
                koccas=[fx.kocca("K1", "애니메이션 제작 지원")],
                bizinfos=[fx.bizinfo("P1", "콘텐츠 제작 지원사업")],
                cglinks=[fx.cglink("7", "3D 캐릭터 외주", "Wed, 04 Nov 2026 10:00:00 +0900")]))
            run("2026-11-05", root / "results", root / "settings", root / "state", t, env=ENV,
                now=datetime(2026, 11, 5, 10, tzinfo=KST))
            written = json.loads((root / "results" / "gov_2026-11-05.json").read_text(encoding="utf-8"))
            read = load_agent(root / "results", "gov", date(2026, 11, 5))
        self.assertTrue(read["ok"], read.get("error"))
        self.assertEqual({i["kind"] for i in written["items"]}, {"bid", "grant", "outsource"})
        self.assertEqual(sorted(i["id"] for i in read["items"]), sorted(i["id"] for i in written["items"]))
        self.assertEqual({s["id"] for s in read["sources"]}, {s["id"] for s in written["sources"]})


class StatusNames(unittest.TestCase):
    """시트 상태 이름(D26)은 두 패키지에 따로 있다. 한쪽만 바뀌면 재알림과 현황판 순서가 어긋나므로 기계로 맞춘다(티켓 24)."""

    def test_review_status_lists_match(self):
        from daily_report.deliver import REVIEWING
        from gov_agent.runner import REQUESTED
        self.assertEqual(tuple(REQUESTED), tuple(REVIEWING))

    def test_apps_script_knows_the_initial_status(self):
        code = (common.PLUGIN.parent / "apps-script" / "Code.gs").read_text(encoding="utf-8")
        self.assertIn("'신규'", code)


if __name__ == "__main__":
    unittest.main()

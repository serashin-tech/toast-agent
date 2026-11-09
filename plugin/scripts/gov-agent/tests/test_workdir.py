"""작업 폴더 경계: 코드가 어디에 있든 현재 폴더(대표 PC의 작업 폴더)의 settings/, state/, .env를 쓴다(H11, H12)."""
import contextlib
import io
import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from gov_agent.cli import main
from helpers import KEY, KST, FakeTransport, bid_filter_md, grant_md, ok_routes

import fixtures as fx


class WorkFolderDefaults(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.work = Path(self._tmp.name)
        (self.work / "settings").mkdir()
        (self.work / "settings" / "bid-filter.md").write_text(bid_filter_md(include="애니메이션"), encoding="utf-8")
        (self.work / "settings" / "grant-criteria.md").write_text(grant_md(), encoding="utf-8")
        (self.work / ".env").write_text(f"DATA_GO_KR_SERVICE_KEY={KEY}\nKOCCA_API_URL=https://kocca.test/api\n",
                                        encoding="utf-8")
        here = os.getcwd()
        os.chdir(self.work)
        self.addCleanup(os.chdir, here)

    def test_run_without_paths_uses_the_current_work_folder(self):
        t = FakeTransport(ok_routes(bids=[fx.bid("B1", "홍보 애니메이션 제작"), fx.bid("B2", "청사 청소 용역")]))
        with contextlib.redirect_stdout(io.StringIO()):
            code = main(["run", "--date", "2026-11-05", "--out", "results"], transport=t, environ={},
                        now=datetime(2026, 11, 5, 10, tzinfo=KST))
        self.assertEqual(code, 0)
        r = json.loads((self.work / "results" / "gov_2026-11-05.json").read_text(encoding="utf-8"))
        bid = next(s for s in r["sources"] if s["id"] == "bid")
        self.assertEqual(bid["status"], "ok")  # 키를 작업 폴더의 .env에서 읽었다
        self.assertEqual([i["id"] for i in r["items"] if i["kind"] == "bid"], ["B1"])  # 작업 폴더의 필터를 썼다
        self.assertTrue((self.work / "state").is_dir())


if __name__ == "__main__":
    unittest.main()

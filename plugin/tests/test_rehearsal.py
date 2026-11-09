"""루틴 전체 리허설 경계(가장 높은 경계): 가짜 응답으로 daily-routine의 코드 단계를 모두 돌린다(H10)."""
import json
import tempfile
import unittest
from pathlib import Path

import common  # noqa: F401  경로 설정

from rehearse import rehearse


class Rehearsal(unittest.TestCase):
    def test_full_routine_produces_run_log_shown_record_mail_and_board(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = rehearse(tmp)
            work = Path(tmp)
            self.assertEqual([code for _, code in r["steps"]], [0] * len(r["steps"]), r["steps"])
            (line,) = [json.loads(x) for x in (work / "runs" / "runs.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual((line["routine"], line["published_ok"], line["publish_late"]), ("daily", True, False))
            shown = json.loads((work / "results" / "shown_2026-11-11.json").read_text(encoding="utf-8"))
            self.assertIn("bid:R26BK999", shown["keys"])
            self.assertEqual(len(r["mails"]), 1)
            board = (work / "reports" / "board.html").read_text(encoding="utf-8")
            self.assertIn("어린이 교통안전 홍보 애니메이션 제작", board)
            for f in work.rglob("*"):  # 키와 토큰은 어떤 산출물에도 남지 않는다(.env 제외)
                if f.is_file() and f.name != ".env":
                    text = f.read_text(encoding="utf-8", errors="replace")
                    self.assertNotIn("SECRETKEY", text, f.name)
                    self.assertNotIn("rehearsal\"", text, f.name)


if __name__ == "__main__":
    unittest.main()

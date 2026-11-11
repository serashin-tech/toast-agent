"""관련도 한 줄 요약 합치기(D33, 티켓 18): Claude가 쓴 {공고번호: 요약}을 결과 파일의 입찰공고 summary에 넣는다."""
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from gov_agent.cli import main


def item(kind, iid):
    return {"source": kind, "kind": kind, "id": iid, "title": "t", "summary": None, "is_new": True}


class Summarize(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        self.result = self.dir / "gov_2026-11-11.json"
        self.result.write_text(json.dumps({"format_version": "1", "items": [
            item("bid", "B1"), item("bid", "B2"), item("outsource", "O1")]}), encoding="utf-8")

    def summarize(self, data):
        src = self.dir / "summaries.json"
        src.write_text(data if isinstance(data, str) else json.dumps(data, ensure_ascii=False), encoding="utf-8")
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["summarize", "--result", str(self.result), "--input", str(src)])
        return code, buf.getvalue(), json.loads(self.result.read_text(encoding="utf-8"))

    def test_summaries_go_to_bids_only_and_are_trimmed(self):
        code, out, r = self.summarize({"B1": "  홍보 애니메이션, 회사 실적과 맞음  ", "O1": "외주", "X9": "없는 공고",
                                       "B2": "가" * 300})
        self.assertEqual(code, 0)
        s = {i["id"]: i["summary"] for i in r["items"]}
        self.assertEqual(s["B1"], "홍보 애니메이션, 회사 실적과 맞음")
        self.assertIsNone(s["O1"])  # 관련도 판정은 입찰공고만(D33)
        self.assertEqual(len(s["B2"]), 120)
        self.assertIn("X9", out)  # 결과에 없는 공고번호는 건너뛰고 알린다

    def test_bad_input_changes_nothing(self):
        before = self.result.read_text(encoding="utf-8")
        code, _, _ = self.summarize("{broken")
        self.assertEqual(code, 1)
        self.assertEqual(self.result.read_text(encoding="utf-8"), before)


if __name__ == "__main__":
    unittest.main()

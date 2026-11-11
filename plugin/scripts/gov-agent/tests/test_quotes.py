"""인용 대조(경계 B의 명령줄 면): 원문 폴더를 주면, 원문에서 찾을 수 없는 근거 문장은 확인필요로 내린다(H9)."""
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from gov_agent.cli import main
from test_eligibility_merge import PROFILE, extraction

CRITERIA = "# 시연 판정 기준\n\n| 항목 | 값 | 비고 |\n|---|---|---|\n| 시연 신호 단어 | 시안 | |\n\n## 변경 이력\n"
SIGNALS = {"bid_id": "R1", "unreadable_files": [], "signals": [
    {"text": "캐릭터 시안 2종 제출", "deliverable": "character",
     "evidence": {"quote": "캐릭터 시안 2종을 제출", "location": "제안요청서 12쪽"}}]}


class QuoteCheck(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        (self.dir / "settings").mkdir()
        (self.dir / "settings" / "company-profile.md").write_text(PROFILE, encoding="utf-8")
        (self.dir / "settings" / "demo-criteria.md").write_text(CRITERIA, encoding="utf-8")
        self.text = self.dir / "text"
        self.text.mkdir()

    def call(self, cmd, data, source=True):
        src = self.dir / "input.json"
        src.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        argv = [cmd, "--input", str(src), "--settings", str(self.dir / "settings")]
        if source:
            argv += ["--source-text", str(self.text)]
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(main(argv), 0)
        return json.loads(buf.getvalue())

    def test_quote_found_in_source_keeps_the_verdict(self):
        (self.text / "공고문.md").write_text("참가자격: 전북\n소재  업체에 한함", encoding="utf-8")  # 줄바꿈·공백 차이는 무시
        out = self.call("eligibility", extraction("R1", "전북"))
        self.assertEqual(out["requirements"][0]["verdict"], "met")
        self.assertIs(out["requirements"][0]["evidence"]["quote_found"], True)

    def test_markdown_emphasis_in_source_is_ignored(self):  # kordoc은 굵은 글씨를 **로 남긴다
        (self.text / "공고문.md").write_text("참가자격: **전북\n소재** 업체에 __한함__", encoding="utf-8")
        out = self.call("eligibility", extraction("R1", "전북"))
        self.assertIs(out["requirements"][0]["evidence"]["quote_found"], True)

    def test_quote_missing_from_source_becomes_needs_check(self):
        (self.text / "공고문.md").write_text("참가자격: 제한 없음", encoding="utf-8")
        out = self.call("eligibility", extraction("R1", "전북"))
        self.assertEqual(out["requirements"][0]["verdict"], "needs_check")
        self.assertIs(out["requirements"][0]["evidence"]["quote_found"], False)
        self.assertEqual(out["overall"], "conditional")

    def test_without_source_text_nothing_changes(self):
        out = self.call("eligibility", extraction("R1", "전북"), source=False)
        self.assertEqual(out["requirements"][0]["verdict"], "met")
        self.assertNotIn("quote_found", out["requirements"][0]["evidence"])

    def test_brief_signal_missing_from_source_is_not_confirmed(self):
        (self.text / "제안요청서.txt").write_text("평가 항목: 사업 이해도", encoding="utf-8")
        out = self.call("brief", SIGNALS)
        self.assertEqual(out["signals"][0]["verdict"], "needs_check")
        (self.text / "제안요청서.txt").write_text("캐릭터 시안 2종을 제출하여야 한다", encoding="utf-8")
        self.assertEqual(self.call("brief", SIGNALS)["signals"][0]["verdict"], "confirmed")


if __name__ == "__main__":
    unittest.main()

"""제안 가능성 검토 결과를 하루치 결과 파일에 합치는 동작(경계 B의 명령줄 면)."""
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from gov_agent.cli import main

PROFILE = """# 회사 프로필

| 항목 | 값 | 확인 상태 | 출처 |
|---|---|---|---|
| 소재지 | 전북 전주시 | 확인됨 | 시험 |

## 변경 이력

| 일자 | 항목 | 변경 전 | 변경 후 | 사유 | 변경자 |
|---|---|---|---|---|---|
"""


def extraction(bid_id, region):
    return {"bid_id": bid_id, "unreadable_files": [], "requirements": [
        {"category": "참가자격", "text": f"{region} 소재 업체", "kind": "소재지", "params": {"지역": region},
         "evidence": {"quote": f"{region} 소재 업체", "location": "3쪽"}}]}


class MergeIntoResult(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        (self.dir / "settings").mkdir()
        (self.dir / "settings" / "company-profile.md").write_text(PROFILE, encoding="utf-8")
        self.result = self.dir / "gov_2026-11-11.json"
        self.result.write_text(json.dumps({"format_version": "1", "agent": "gov", "items": [], "eligibility": []},
                                          ensure_ascii=False), encoding="utf-8")

    def merge(self, data):
        src = self.dir / "input.json"
        src.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        with redirect_stdout(io.StringIO()):
            code = main(["eligibility", "--input", str(src), "--settings", str(self.dir / "settings"),
                         "--merge-into", str(self.result)])
        self.assertEqual(code, 0)
        return json.loads(self.result.read_text(encoding="utf-8"))

    def test_new_bid_is_appended_and_other_fields_are_kept(self):
        out = self.merge(extraction("R1", "전북"))
        self.assertEqual([e["bid_id"] for e in out["eligibility"]], ["R1"])
        self.assertEqual(out["eligibility"][0]["overall"], "recommend")
        self.assertEqual((out["format_version"], out["agent"]), ("1", "gov"))

    def test_same_bid_is_replaced_not_duplicated(self):
        self.merge(extraction("R1", "전북"))
        self.merge(extraction("R2", "전북"))
        out = self.merge(extraction("R1", "서울"))
        self.assertEqual(sorted(e["bid_id"] for e in out["eligibility"]), ["R1", "R2"])
        r1 = next(e for e in out["eligibility"] if e["bid_id"] == "R1")
        self.assertEqual(r1["overall"], "not_recommend")


if __name__ == "__main__":
    unittest.main()

"""2차 검토(시연 판정): 추출된 시연 신호를 결정적으로 판정해 시연 브리프를 만든다."""
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from gov_agent.cli import main
from gov_agent.demo_brief import DEFAULT_WORDS, build_brief

CRITERIA = """# 설정: 시연 판정 기준

## 값

| 항목 | 값 | 비고 |
|---|---|---|
| 시연 신호 단어 | {words} | |

## 변경 이력

| 일자 | 항목 | 변경 전 | 변경 후 | 사유 | 변경자 |
|---|---|---|---|---|---|
"""


def sig(quote="캐릭터 시안 2종을 제출하여야 한다", location="제안요청서 12쪽", deliverable="character"):
    return {"text": "캐릭터 시안 2종 제출", "deliverable": deliverable,
            "evidence": {"quote": quote, "location": location}}


class DemoBrief(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "demo-criteria.md"
        self.path.write_text(CRITERIA.format(words="시안, 시연, 키비주얼"), encoding="utf-8")

    def brief(self, *signals, eligibility="recommend", unreadable=None, **extra):
        data = {"bid_id": "R26BK001", "title": "홍보 애니메이션 제작", "signals": list(signals),
                "unreadable_files": unreadable or [], **extra}
        elig = None if eligibility is None else {"bid_id": "R26BK001", "overall": eligibility}
        return build_brief(data, elig, self.path)

    def test_grounded_signal_means_demo_needed(self):
        out = self.brief(sig())
        self.assertEqual(out["demo_needed"], "yes")
        self.assertEqual(out["deliverable"], "character")
        self.assertEqual(out["signals"][0]["verdict"], "confirmed")
        self.assertTrue(out["gate"]["passed"])
        self.assertIn("대표", out["disclaimer"])

    def test_signal_without_evidence_or_signal_word_needs_check(self):
        # 근거 위치가 없거나, 근거 문장에 설정의 신호 단어가 없으면 확인되지 않은 신호다.
        out = self.brief(sig(location=""), sig(quote="과업 내용은 협의하여 정한다"))
        self.assertEqual([s["verdict"] for s in out["signals"]], ["needs_check", "needs_check"])
        self.assertEqual(out["demo_needed"], "needs_check")
        self.assertEqual(out["deliverable"], "none")

    def test_no_signals_means_no_demo_but_unreadable_files_need_check(self):
        self.assertEqual(self.brief()["demo_needed"], "no")
        out = self.brief(unreadable=[{"name": "제안요청서.hwp", "url": "https://x"}])
        self.assertEqual(out["demo_needed"], "needs_check")  # 읽지 못한 첨부에 요구가 있을 수 있다

    def test_not_recommended_bid_stops_at_gate(self):
        out = self.brief(sig(), eligibility="not_recommend")
        self.assertFalse(out["gate"]["passed"])
        self.assertEqual(out["demo_needed"], "no")
        self.assertEqual(out["deliverable"], "none")
        # 판정 정보는 남겨서 대표가 직접 뒤집을 수 있게 한다
        self.assertEqual(out["signals"][0]["verdict"], "confirmed")

    def test_missing_eligibility_passes_gate_with_note(self):
        out = self.brief(sig(), eligibility=None)
        self.assertTrue(out["gate"]["passed"])
        self.assertIsNone(out["gate"]["eligibility"])
        self.assertEqual(out["demo_needed"], "yes")

    def test_deliverable_combines_confirmed_signals_only(self):
        out = self.brief(sig(), sig(quote="키비주얼 1종을 제시한다", deliverable="screen"),
                         sig(quote="협의한다", deliverable="screen"))
        self.assertEqual(out["deliverable"], "both")
        out = self.brief(sig(deliverable=None))
        self.assertEqual(out["deliverable"], "unspecified")

    def test_settings_error_falls_back_to_default_words(self):
        self.path.write_text("표가 없는 파일", encoding="utf-8")
        out = self.brief(sig(quote="시제품을 시연한다"))
        self.assertIn("시제품", DEFAULT_WORDS)
        self.assertEqual(out["demo_needed"], "yes")
        self.assertIn("기본 신호 단어", out["settings_note"])

    def test_passthrough_fields(self):
        out = self.brief(sig(), scoring=[{"item": "디자인 제안", "points": 20}],
                         constraints={"format": "PNG", "count": 2}, ai_use_notes=[{"text": "생성형 AI 사용 시 명시"}])
        self.assertEqual(out["scoring"][0]["points"], 20)
        self.assertEqual(out["constraints"]["count"], 2)
        self.assertEqual(out["ai_use_notes"][0]["text"], "생성형 AI 사용 시 명시")
        self.assertEqual(out["title"], "홍보 애니메이션 제작")


class BriefCommand(unittest.TestCase):
    def test_cli_reads_eligibility_and_writes_brief(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "settings").mkdir()
            (d / "settings" / "demo-criteria.md").write_text(CRITERIA.format(words="시안"), encoding="utf-8")
            (d / "in.json").write_text(json.dumps({"bid_id": "B1", "signals": [sig()]}, ensure_ascii=False),
                                       encoding="utf-8")
            (d / "elig.json").write_text(json.dumps({"bid_id": "B1", "overall": "conditional"}), encoding="utf-8")
            out = d / "drafts" / "B1" / "brief.json"
            with redirect_stdout(io.StringIO()):
                code = main(["brief", "--input", str(d / "in.json"), "--eligibility", str(d / "elig.json"),
                             "--settings", str(d / "settings"), "--out", str(out)])
            self.assertEqual(code, 0)
            brief = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(brief["gate"]["eligibility"], "conditional")
            self.assertEqual(brief["demo_needed"], "yes")


if __name__ == "__main__":
    unittest.main()

"""신규 알림 메일의 수집 실패 표시와 실패 처리 (D30, D35)."""
import shutil

from helpers import FIX, ReportCase, fixture, section

FAIL_BOX = "오늘 수집하지 못한 소스"


class FailureBox(ReportCase):
    def test_failed_source_box_is_at_top_with_reason_and_last_success(self):
        self.put_today()
        html = self.html()
        box = html.index(FAIL_BOX)
        self.assertLess(box, html.index(">입찰공고 "))
        self.assertIn("한콘진", html[box:html.index(">입찰공고 ")])
        self.assertIn("호출 한도 초과", html)
        self.assertIn("마지막 정상 수집 2026-11-04 09:03", html)

    def test_no_box_when_all_sources_ok(self):
        def mutate(d):
            d["sources"] = [s for s in d["sources"] if s["status"] == "ok"]
        self.put_today(mutate)
        self.assertNotIn(FAIL_BOX, self.html())

    def test_missing_result_file_is_failure_not_empty_day(self):
        html = self.html()  # 결과 파일 없음
        self.assertIn(FAIL_BOX, html)
        self.assertIn("결과 없음", html)
        self.assertNotIn("오늘은 새 공고가 없습니다", html)

    def test_unknown_format_version_is_format_error(self):
        self.put_today(lambda d: d.update(format_version="2"))
        html = self.html()
        self.assertIn("형식 오류", html[html.index(FAIL_BOX):html.index(">입찰공고 ")])
        self.assertNotIn("AI 기반 3D 애니메이션 제작 용역", html)

    def test_broken_json_is_format_error(self):
        self.put("gov_2026-11-05.json", "{ not json")
        self.assertIn("형식 오류", self.html())

    def test_missing_required_field_is_format_error(self):
        self.put_today(lambda d: d.pop("items"))
        self.assertIn("형식 오류", self.html())

    def test_yesterday_file_is_never_used_instead_of_today(self):
        shutil.copy(FIX / "results" / "gov_2026-11-05.json", self.results / "gov_2026-11-04.json")
        html = self.html()  # 오늘 파일 없음, 어제 파일만 있음
        self.assertIn("결과 없음", html)
        self.assertNotIn("AI 기반 3D 애니메이션 제작 용역", html)

    def test_failed_source_section_differs_from_no_new_items(self):
        self.put_today()  # 지원사업의 한콘진은 실패, 민간 외주는 성공했으나 새 항목 없음
        html = self.html()
        outsource = section(html, "민간 외주")
        grant = section(html, "지원사업", "민간 외주")
        self.assertIn("새 항목이 없습니다", outsource)
        self.assertNotIn("수집 실패", outsource)
        self.assertIn("수집 실패", grant)
        self.assertNotIn("새 항목이 없습니다", grant)


class EmptyDay(ReportCase):
    def test_day_with_no_items_says_no_new_notices(self):
        def mutate(d):
            d["items"] = []
            d["eligibility"] = []
            d["sources"] = [s for s in d["sources"] if s["status"] == "ok"]
            for s in d["sources"]:
                s["new_count"] = 0
        self.put_today(mutate)
        html = self.html()
        self.assertIn("오늘은 새 공고가 없습니다", html)
        self.assertNotIn(FAIL_BOX, html)
        self.assertEqual(fixture("gov_2026-11-05.json")["run_date"], "2026-11-05")

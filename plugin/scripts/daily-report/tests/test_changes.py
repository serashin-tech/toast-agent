"""최근 설정 변경 표시와 전날 대비 건수 변화 (경계 C)."""
import shutil

from helpers import FIX, ReportCase

SETTINGS = FIX / "settings"


class RecentSettingChanges(ReportCase):
    def setUp(self):
        super().setUp()
        self.put_today()

    def test_changes_within_7_days_shown_as_one_line_and_older_rows_are_not(self):
        html = self.html(settings=SETTINGS)
        self.assertIn("최근 설정 변경", html)
        self.assertIn("포함 키워드", html)
        self.assertIn("애니메이션 → 애니메이션, AI", html)
        self.assertNotIn("추정가격 하한", html)  # 2026-10-20은 16일 전

    def test_initial_row_is_shown_when_within_7_days(self):
        self.assertIn("최초 작성", self.html(settings=SETTINGS))

    def test_boundary_is_7_days_inclusive(self):
        d = self.tmp / "settings"
        d.mkdir()
        head = "## 변경 이력\n\n| 일자 | 항목 | 변경 전 | 변경 후 | 사유 | 변경자 |\n|---|---|---|---|---|---|\n"
        (d / "a.md").write_text(head + "| 2026-10-29 | 일곱째날항목 | 가 | 나 | 사유 | 대표 |\n"
                                "| 2026-10-28 | 여덟째날항목 | 가 | 나 | 사유 | 대표 |\n", encoding="utf-8")
        html = self.html(settings=d)
        self.assertIn("일곱째날항목", html)
        self.assertNotIn("여덟째날항목", html)

    def test_no_recent_change_means_no_line_and_no_count_delta(self):
        d = self.tmp / "settings"
        d.mkdir()
        shutil.copy(SETTINGS / "bid_filter.md", d / "bid_filter.md")
        text = (d / "bid_filter.md").read_text(encoding="utf-8").replace("2026-11-04", "2026-10-01")
        (d / "bid_filter.md").write_text(text, encoding="utf-8")
        shutil.copy(FIX / "results" / "gov_2026-11-04.json", self.results / "gov_2026-11-04.json")
        html = self.html(settings=d)
        self.assertNotIn("최근 설정 변경", html)
        self.assertNotIn("전날 대비", html)

    def test_malformed_or_empty_history_is_ignored_without_error(self):
        d = self.tmp / "settings"
        d.mkdir()
        shutil.copy(SETTINGS / "broken.md", d / "broken.md")
        (d / "wrongcols.md").write_text("## 변경 이력\n\n| 날짜 | 내용 |\n|---|---|\n| 2026-11-05 | 가짜 |\n", encoding="utf-8")
        (d / "empty.md").write_text("## 변경 이력\n\n| 일자 | 항목 | 변경 전 | 변경 후 | 사유 | 변경자 |\n|---|---|---|---|---|---|\n", encoding="utf-8")
        (d / "nohistory.md").write_text("# 값만 있는 파일\n", encoding="utf-8")
        html = self.html(settings=d)
        self.assertNotIn("최근 설정 변경", html)
        self.assertNotIn("가짜", html)


class CountDelta(ReportCase):
    def setUp(self):
        super().setUp()
        self.put_today()

    def test_inclusion_and_exclusion_change_vs_yesterday_for_sources_ok_on_both_days(self):
        shutil.copy(FIX / "results" / "gov_2026-11-04.json", self.results / "gov_2026-11-04.json")
        html = self.html(settings=SETTINGS)
        self.assertIn("포함 9건 (전날 7건, +2건)", html)
        self.assertIn("제외 48건 (전날 40건, +8건)", html)
        self.assertIn("수집에 성공한 소스만 비교", html)

    def test_count_delta_is_omitted_when_yesterday_file_is_absent(self):
        html = self.html(settings=SETTINGS)
        self.assertIn("최근 설정 변경", html)
        self.assertNotIn("전날", html)

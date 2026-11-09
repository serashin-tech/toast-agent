"""보기 위젯과 화면 규칙 (경계 C: 출력 HTML의 외부에서 보이는 성질)."""
import re

from helpers import ReportCase


class ViewWidget(ReportCase):
    def setUp(self):
        super().setUp()
        self.put_today()
        self.html_ = self.html()

    def test_sort_options_soon_only_and_collapse_controls_exist(self):
        h = self.html_
        self.assertIn('<select id="sort"', h)
        self.assertIn("마감순", h)
        self.assertIn("등록일순", h)
        self.assertIn('<input type="checkbox" id="soon-only"', h)
        self.assertIn("마감 임박만 보기", h)
        self.assertIn("모두 접기", h)
        self.assertIn("모두 펼치기", h)
        self.assertIn('<button type="button"', h)  # 키보드와 터치로 조작되는 기본 컨트롤

    def test_controls_appear_only_when_script_runs(self):
        self.assertIn('id="viewbar" class="toolbar" hidden', self.html_)

    def test_report_is_fully_readable_without_script(self):
        h = self.html_
        self.assertNotRegex(h, r'<article[^>]* hidden')
        self.assertIn('<details class="srcsec" open>', h)
        self.assertIn("<summary>", h)

    def test_nothing_is_stored_and_no_runtime_features_are_used(self):
        for banned in ("window.claude", "localStorage", "sessionStorage", "indexedDB", "document.cookie",
                       "fetch(", "XMLHttpRequest", "navigator.", "download", "Blob(", "createObjectURL"):
            self.assertNotIn(banned, self.html_, banned)

    def test_everything_is_inline_with_no_external_resources(self):
        h = self.html_
        self.assertNotRegex(h, r"<script[^>]*\ssrc=")
        self.assertNotIn("<link", h)
        self.assertNotIn("@import", h)
        self.assertNotRegex(h, r"url\(")
        self.assertEqual(h.count("<style>"), 1)
        self.assertEqual(h.count("<script>"), 1)


class ScreenRules(ReportCase):
    def setUp(self):
        super().setUp()
        self.put_today()
        self.html_ = self.html()

    def test_korean_wraps_by_word(self):
        self.assertIn("word-break:keep-all", self.html_)
        self.assertIn("overflow-wrap:break-word", self.html_)
        self.assertIn('<html lang="ko">', self.html_)

    def test_phone_viewport_and_both_color_schemes(self):
        self.assertIn('<meta name="viewport" content="width=device-width, initial-scale=1">', self.html_)
        self.assertIn("prefers-color-scheme:dark", self.html_)
        self.assertIn("color-scheme:light dark", self.html_)

    def test_reading_width_is_set_by_one_container_only(self):
        selectors = [s.strip() for s in re.findall(r"([^{}]+)\{[^}]*max-width", self.html_)]
        self.assertEqual(selectors, [".page"])

    def test_no_fixed_widths_that_could_scroll_a_375px_screen(self):
        css = self.html_[self.html_.index("<style>"):self.html_.index("</style>")]
        for px in re.findall(r"(?<![-\w])(?:min-)?width:(\d+)px", css):
            self.assertLessEqual(int(px), 320)

"""신규 알림 메일의 절·정렬·마감 임박·항목 표시 (D30, D35). 예전 보고서 HTML 시험에서 옮겼다."""
import re

from helpers import ReportCase, fixture, section

B1, B2, B3, B4 = "20261100001-00", "20261100002-00", "20261100003-00", "20261100004-00"
SOON = "마감 임박"


def entry(html, url):
    """항목 하나(<li>…</li>)를 원문 링크로 찾는다."""
    a = html.rindex("<li", 0, html.index(f'href="{url}"'))
    return html[a:html.index("</li>", a)]


def urls(chunk):
    return re.findall(r'href="(https://example\.go\.kr/[^"]+)"', chunk)


def url_of(item_id):
    return next(i["url"] for i in fixture("gov_2026-11-05.json")["items"] if i["id"] == item_id)


class Order(ReportCase):
    def setUp(self):
        super().setUp()
        self.put_today()
        self.h = self.html()

    def test_sections_in_order_with_counts(self):
        h = self.h
        self.assertLess(h.index(">입찰공고 3건"), h.index(">지원사업 2건"))
        self.assertLess(h.index(">지원사업 2건"), h.index(">민간 외주 0건"))
        self.assertNotIn("낙찰", h)

    def test_items_sorted_by_nearest_deadline_and_no_deadline_last(self):
        self.assertEqual(urls(section(self.h, "입찰공고", "지원사업")), [url_of(B1), url_of(B2), url_of(B3)])
        self.assertEqual(urls(section(self.h, "지원사업", "민간 외주")), [url_of("GR-1"), url_of("GR-2")])

    def test_shown_items_never_appear(self):  # is_new=false는 메일에 싣지 않는다
        for old in (B4, "GR-3"):
            self.assertNotIn(url_of(old), self.h)

    def test_no_today_three_section_and_no_report_widgets(self):
        for gone in ("오늘 볼 3건", "보기 설정", "<script", "<select"):
            self.assertNotIn(gone, self.h)


class DeadlineSoon(ReportCase):
    def mail_with_deadlines(self, deadlines):
        def mutate(d):
            base = d["items"][1]
            d["items"] = [{**base, "id": f"T{n}", "deadline": dl, "is_new": True, "url": f"https://example.go.kr/t{n}"}
                          for n, dl in enumerate(deadlines)]
        self.put_today(mutate)
        return self.html()

    def test_soon_mark_for_0_to_7_days_only(self):  # 기준일 2026-11-05
        h = self.mail_with_deadlines(["2026-11-05", "2026-11-12", "2026-11-13", None])
        self.assertIn(SOON, entry(h, "https://example.go.kr/t0"))   # D-day
        self.assertIn(SOON, entry(h, "https://example.go.kr/t1"))   # D-7
        self.assertNotIn(SOON, entry(h, "https://example.go.kr/t2"))  # D-8
        self.assertNotIn(SOON, entry(h, "https://example.go.kr/t3"))  # 마감 없음

    def test_fixture_marks_bid_and_grant_due_this_week(self):
        self.put_today()
        h = self.html()
        self.assertIn(SOON, entry(h, url_of(B1)))      # 2026-11-09, D-4
        self.assertIn(SOON, entry(h, url_of("GR-1")))  # 2026-11-07, D-2
        self.assertNotIn(SOON, entry(h, url_of(B2)))


class ItemFields(ReportCase):
    def setUp(self):
        super().setUp()
        self.put_today()
        self.h = self.html()

    def test_every_new_item_has_its_source_link(self):
        for it in fixture("gov_2026-11-05.json")["items"]:
            if it["is_new"]:
                self.assertIn(f'href="{it["url"]}"', self.h, it["id"])

    def test_bid_fields(self):
        e = entry(self.h, url_of(B1))
        for text in ("AI 기반 3D 애니메이션 제작 용역", "한국콘텐츠진흥원", "150,000,000원", "2026-11-09", "D-4"):
            self.assertIn(text, e)
        self.assertIn("미기재", entry(self.h, url_of(B3)))  # 추정가격 없음

    def test_grant_fields(self):
        e = entry(self.h, url_of("GR-1"))
        for text in ("한국콘텐츠진흥원", "2026-11-07", "D-2"):
            self.assertIn(text, e)

    def test_outsource_poster_and_link(self):
        def mutate(d):
            d["items"].append({"source": "outsource_cglink", "kind": "outsource", "id": "CG-1",
                               "title": "신규 TV시리즈 3D 애니메이션 프리랜서 및 팀 구인", "posted_on": "2026-11-04",
                               "deadline": None, "url": "https://cglink.com/5099468", "matched_keywords": [],
                               "summary": None, "is_new": True, "extra": {"poster": "N-GEO"}})
        self.put_today(mutate)
        h = self.html()
        e = entry(h, "https://cglink.com/5099468")
        self.assertIn("N-GEO", e)
        self.assertIn(">민간 외주 1건", h)

    def test_summary_is_labelled_only_where_present(self):
        self.assertIn("AI 요약: AI 활용 3D 애니메이션 제작 용역 공고입니다.", entry(self.h, url_of(B1)))
        self.assertNotIn("AI 요약", entry(self.h, url_of(B2)))

    def test_korean_wraps_by_word(self):
        self.assertIn("word-break:keep-all", self.h)


class BuildMakesNoReport(ReportCase):
    def test_build_only_starts_the_run_log(self):  # D35
        self.put_today()
        runs = self.tmp / "runs"
        code, report_exists = self.build(runs=runs)
        self.assertEqual(code, 0)
        self.assertFalse(report_exists)
        self.assertTrue((runs / "runs.jsonl").exists())

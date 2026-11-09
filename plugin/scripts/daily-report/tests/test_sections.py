"""오늘 볼 3건, 마감 임박, 소스별 절, 항목 표시 (경계 C)."""
import re

from helpers import ReportCase, fixture

B1, B2, B3, B4 = "20261100001-00", "20261100002-00", "20261100003-00", "20261100004-00"


def region(html, start_id, end_id=None):
    a = html.index(f'id="{start_id}"')
    return html[a:html.index(f'id="{end_id}"')] if end_id else html[a:]


def article(html, item_id):
    a = html.index(f'data-id="{item_id}"')
    return html[a:html.index("</article>", a)]


def data_ids(chunk):
    return re.findall(r'data-id="([^"]+)"', chunk)


class TodayAndSoon(ReportCase):
    def setUp(self):
        super().setUp()
        self.put_today()
        self.html_ = self.html()

    def test_today_three_picks_nearest_deadline_among_new_bid_and_grant(self):
        self.assertEqual(data_ids(region(self.html_, "today", "soon")), ["GR-1", B1, "GR-2"])

    def test_today_explains_selection_rule_in_one_line(self):
        self.assertIn("마감이 가까운 순", region(self.html_, "today", "soon"))

    def test_soon_lists_deadline_within_7_days_including_not_new(self):
        self.assertEqual(sorted(data_ids(region(self.html_, "soon", "sec-bid"))), sorted(["GR-3", "GR-1", B4, B1]))

    def test_tie_on_deadline_prefers_more_matched_keywords_and_no_deadline_goes_last(self):
        def mutate(d):
            base = d["items"][1]
            d["items"] = []
            for n, (iid, kws, dl) in enumerate([
                ("T1", ["a"], "2026-11-10"), ("T2", ["a", "b", "c"], "2026-11-10"),
                ("T3", ["a", "b"], "2026-11-10"), ("T4", ["a", "b", "c", "d"], None)]):
                d["items"].append({**base, "id": iid, "kind": "bid", "source": "bid", "matched_keywords": kws,
                                   "deadline": dl, "is_new": True, "url": "https://example.go.kr/" + iid})
        self.put_today(mutate)
        self.assertEqual(data_ids(region(self.html(), "today", "soon")), ["T2", "T3", "T1"])

    def test_fewer_than_three_new_items_shows_only_what_exists(self):
        def mutate(d):
            d["items"] = [i for i in d["items"] if i["id"] in ("GR-1", "CG-OLD")]
        self.put_today(mutate)
        self.assertEqual(data_ids(region(self.html(), "today", "soon")), ["GR-1"])


class Sections(ReportCase):
    def setUp(self):
        super().setUp()
        self.put_today()
        self.html_ = self.html()

    def test_section_order_and_titles(self):
        h = self.html_
        self.assertLess(h.index('id="sec-bid"'), h.index('id="sec-grant"'))
        self.assertLess(h.index('id="sec-grant"'), h.index('id="sec-outsource"'))
        for title in ("입찰공고", "지원사업", "민간 외주"):
            self.assertIn(f"<h2>{title}</h2>", h)
        self.assertNotIn("낙찰", h)

    def test_items_not_in_top_are_inside_collapsed_details(self):
        sec = region(self.html_, "sec-bid", "sec-grant")
        self.assertNotIn(f'data-id="{B1}"', sec)   # 상단에 올라간 항목은 절에서 중복하지 않는다
        self.assertEqual(sorted(data_ids(sec)), sorted([B2, B3]))
        rest = sec[sec.index('<details class="rest"'):]
        self.assertIn(f'data-id="{B2}"', rest)
        self.assertNotIn("<details class=\"rest\" open", sec)

    def test_source_without_new_items_says_so(self):
        self.assertIn("새 항목 없음", region(self.html_, "sec-outsource"))
        self.assertNotIn("새 항목 없음", region(self.html_, "sec-bid", "sec-grant"))

    def test_every_item_has_its_source_link(self):
        for it in fixture("gov_2026-11-05.json")["items"]:
            self.assertIn(f'href="{it["url"]}"', article(self.html_, it["id"]), it["id"])

    def test_bid_fields(self):
        a = article(self.html_, B1)
        for text in ("AI 기반 3D 애니메이션 제작 용역", "한국콘텐츠진흥원", "150,000,000원", "2026-11-09", "애니메이션"):
            self.assertIn(text, a)
        self.assertIn("미기재", article(self.html_, B3))  # 추정가격 없음

    def test_grant_fields(self):
        a = article(self.html_, "GR-1")
        for text in ("2026-10-20 ~ 2026-11-07", "D-2", "중소기업 지원사업", "한콘진"):
            self.assertIn(text, a)

    def test_agent_summary_is_labelled_and_absent_when_none(self):
        a = article(self.html_, B1)
        self.assertLess(a.index("에이전트 요약"), a.index("AI 활용 3D 애니메이션 제작 용역 공고입니다."))
        self.assertNotIn("에이전트 요약", article(self.html_, B2))


class Eligibility(ReportCase):
    def setUp(self):
        super().setUp()
        self.put_today()
        self.html_ = self.html()

    def test_verdicts_evidence_reason_and_disclaimer_under_the_bid(self):
        a = article(self.html_, B1)
        self.assertIn('<details class="elig"', a)
        for text in ("충족", "미충족", "확인필요", "조건부", "영상물 제작업 등록업체일 것", "공고문 3쪽 2항",
                     "참가자격은 충족하나 평가방식 확인이 필요합니다.", "최종 판단은 대표가 합니다."):
            self.assertIn(text, a)

    def test_extract_only_states_no_profile_comparison(self):
        self.assertIn("요건만 추출했고 회사 정보와 대조하지 않았습니다", article(self.html_, B2))

    def test_bid_without_review_has_no_review_block(self):
        self.assertNotIn("elig", article(self.html_, B4))


class Outsource(ReportCase):
    def test_outsource_section_comes_last_with_poster_and_link(self):
        def mutate(d):
            d["sources"] = [s for s in d["sources"] if s["id"] != "outsource_cglink"]
            d["sources"].append({"id": "outsource_cglink", "label": "민간 외주(CGLink)", "status": "ok", "fetched": 1,
                                 "included": 1, "excluded": 0, "new_count": 1, "error": None,
                                 "last_success_at": "2026-11-05T09:00:00+09:00"})
            d["items"].append({"source": "outsource_cglink", "kind": "outsource", "id": "CG-1",
                               "title": "신규 TV시리즈 3D 애니메이션 프리랜서 및 팀 구인", "posted_on": "2026-11-04",
                               "deadline": None, "url": "https://cglink.com/5099468", "matched_keywords": [],
                               "summary": None, "is_new": True, "extra": {"poster": "N-GEO"}})
        self.put_today(mutate)
        h = self.html()
        self.assertLess(h.index('id="sec-grant"'), h.index('id="sec-outsource"'))
        self.assertIn("<h2>민간 외주</h2>", h)
        a = article(h, "CG-1")
        for text in ("N-GEO", "2026-11-04", "CGLink", 'href="https://cglink.com/5099468"'):
            self.assertIn(text, a)
        self.assertNotIn('data-id="CG-1"', region(h, "today", "soon"))  # 오늘 볼 3건은 입찰공고와 지원사업에서만 고른다

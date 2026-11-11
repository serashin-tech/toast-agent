from helpers import Base, FakeTransport, ok_routes, bid_filter_md
import fixtures as fx


class BidCollection(Base):
    def test_first_run_writes_contract_fields_for_bid(self):
        t = FakeTransport(ok_routes(bids=[fx.bid("R26BK001", "AI 애니메이션 제작 용역",
                                                 attach=[("공고문.hwp", "https://g2b.test/a.hwp")])]))
        r = self.run_day(t)
        self.assertEqual((r["format_version"], r["agent"], r["run_date"]), ("1", "gov", "2026-11-05"))
        (it,) = self.items(r, "bid")
        self.assertEqual((it["source"], it["id"], it["is_new"]), ("bid", "R26BK001", True))
        self.assertEqual(it["posted_on"], "2026-11-04")
        self.assertEqual(it["deadline"], "2026-11-30")
        self.assertTrue(it["url"].startswith("https://"))
        self.assertEqual(it["extra"]["est_price"], 100000000)
        self.assertEqual(it["extra"]["agency"], "전북특별자치도교육청")
        self.assertEqual(it["extra"]["attachments"], [{"name": "공고문.hwp", "url": "https://g2b.test/a.hwp"}])
        self.assertEqual(r["eligibility"], [])
        self.assertFalse(r["settings"]["fallback_used"])

    def test_shown_items_are_not_listed_again_even_when_changed(self):
        # 2026-11-09 규칙 변경(D13, IM-09): 보여 준 항목은 내용이 바뀌어도 다시 싣지 않고 건수만 센다.
        import json
        a, b = fx.bid("A1", "애니메이션 제작"), fx.bid("B1", "홍보영상 제작")
        self.run_day(FakeTransport(ok_routes(bids=[a, b])))
        self.out.joinpath("shown_2026-11-05.json").write_text(
            json.dumps({"date": "2026-11-05", "keys": ["bid:A1", "bid:B1"]}), encoding="utf-8")
        b2 = fx.bid("B1", "홍보영상 제작", price=90000000)  # 변경
        c = fx.bid("C1", "콘텐츠 제작")  # 신규
        r = self.run_day(FakeTransport(ok_routes(bids=[a, b2, c])), date="2026-11-06")
        got = {i["id"]: i["is_new"] for i in self.items(r, "bid")}
        self.assertEqual(got, {"C1": True})
        self.assertEqual((self.src(r, "bid")["new_count"], self.src(r, "bid")["changed_shown_count"]), (1, 1))

    def test_duplicate_bid_numbers_appear_once(self):
        r = self.run_day(FakeTransport(ok_routes(bids=[fx.bid("A1", "x"), fx.bid("A1", "x")])))
        self.assertEqual([i["id"] for i in self.items(r, "bid")], ["A1"])

    def test_request_window_starts_at_last_success(self):
        self.run_day(FakeTransport(ok_routes()), date="2026-11-05")
        t2 = FakeTransport(ok_routes())
        self.run_day(t2, date="2026-11-06")
        p = t2.calls_to("BidPublicInfoService02")[0]
        self.assertEqual(p["inqryBgnDt"], "202611050900")
        self.assertEqual((p["inqryEndDt"], p["type"]), ("202611060900", "json"))

    def test_uses_the_services_list_operation_confirmed_on_2026_11_11(self):  # 실제 응답 확인(`…Servc02`)
        t = FakeTransport(ok_routes())
        self.run_day(t)
        self.assertTrue(t.calls_to("/getBidPblancListInfoServc02"))

    def test_request_window_is_capped_at_7_days(self):  # 2026-11-10부터 조회 기간 최대 7일(공공데이터포털 공지)
        self.run_day(FakeTransport(ok_routes()), date="2026-11-01")
        t2 = FakeTransport(ok_routes())
        self.run_day(t2, date="2026-11-10")
        self.assertEqual(t2.calls_to("BidPublicInfoService02")[0]["inqryBgnDt"], "202611030900")


class BidFilter(Base):
    def collect(self, bids, **filter_args):
        self.set_settings(bid=bid_filter_md(**filter_args))
        return self.items(self.run_day(FakeTransport(ok_routes(bids=bids))), "bid")

    def test_include_keywords_filter_and_are_recorded(self):
        got = self.collect([fx.bid("A", "AI 애니메이션 및 홍보영상"), fx.bid("B", "청사 청소 용역")],
                           include="애니메이션, 홍보영상")
        self.assertEqual([(i["id"], i["matched_keywords"]) for i in got], [("A", ["애니메이션", "홍보영상"])])

    def test_exclude_keywords(self):
        got = self.collect([fx.bid("A", "애니메이션 제작"), fx.bid("B", "애니메이션 장비 유지보수")],
                           include="애니메이션", exclude="유지보수")
        self.assertEqual([i["id"] for i in got], ["A"])

    def test_price_range(self):
        bids = [fx.bid("LOW", "x", price=1000), fx.bid("MID", "x", price=50000), fx.bid("HIGH", "x", price=999999)]
        got = self.collect(bids, pmin="10,000", pmax="100000")
        self.assertEqual([i["id"] for i in got], ["MID"])

    def test_minimum_days_until_deadline(self):
        bids = [fx.bid("SOON", "x", deadline="2026-11-07 10:00"), fx.bid("LATER", "x", deadline="2026-11-30 10:00")]
        got = self.collect(bids, days="7")
        self.assertEqual([i["id"] for i in got], ["LATER"])

    def test_excluded_agency_type(self):
        got = self.collect([fx.bid("A", "x", agency_type="민간"), fx.bid("B", "x", agency_type="교육기관")], types="민간")
        self.assertEqual([i["id"] for i in got], ["B"])

    def test_empty_include_keywords_pass_everything(self):
        got = self.collect([fx.bid("A", "아무 공고"), fx.bid("B", "다른 공고")])
        self.assertEqual([i["id"] for i in got], ["A", "B"])
        self.assertTrue(all(i["matched_keywords"] == [] for i in got))

    def test_counts(self):
        self.set_settings(bid=bid_filter_md(include="애니"))
        r = self.run_day(FakeTransport(ok_routes(bids=[fx.bid("A", "애니"), fx.bid("B", "청소")])))
        s = self.src(r, "bid")
        self.assertEqual((s["fetched"], s["included"], s["excluded"], s["status"]), (2, 1, 1, "ok"))

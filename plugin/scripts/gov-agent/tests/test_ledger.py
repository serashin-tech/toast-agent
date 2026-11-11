"""보여 준 항목 제외(IM-09, D13): 로컬 원장이 정본이고, 노출 기록(shown_<날짜>.json)에 있는 항목만 다시 싣지 않는다."""
import json

import fixtures as fx
from helpers import Base, FakeTransport, ok_routes


def shown(out, day, keys):
    out.mkdir(parents=True, exist_ok=True)
    (out / f"shown_{day}.json").write_text(json.dumps({"date": day, "keys": keys}), encoding="utf-8")


class Ledger(Base):
    def day(self, date, bids=(), koccas=(), bizinfos=()):
        return self.run_day(FakeTransport(ok_routes(bids=bids, koccas=koccas, bizinfos=bizinfos)), date=date)

    def ids(self, r):
        return [i["id"] for i in r["items"]]

    def test_items_carry_their_ledger_keys(self):
        r = self.day("2026-11-05", bids=[fx.bid("B1", "홍보 애니메이션")])
        self.assertEqual(r["items"][0]["keys"], ["bid:B1"])

    def test_shown_item_does_not_come_back(self):
        self.day("2026-11-05", bids=[fx.bid("B1", "홍보 애니메이션")])
        shown(self.out, "2026-11-05", ["bid:B1"])
        r = self.day("2026-11-06", bids=[fx.bid("B1", "홍보 애니메이션")])
        self.assertEqual(self.ids(r), [])

    def test_item_not_shown_yesterday_comes_back_as_new(self):  # 전달에 실패한 날의 항목
        self.day("2026-11-05", bids=[fx.bid("B1", "홍보 애니메이션")])
        r = self.day("2026-11-06", bids=[fx.bid("B1", "홍보 애니메이션")])
        self.assertEqual(self.ids(r), ["B1"])
        self.assertIs(r["items"][0]["is_new"], True)

    def test_changed_shown_item_is_counted_not_listed(self):
        self.day("2026-11-05", bids=[fx.bid("B1", "홍보 애니메이션")])
        shown(self.out, "2026-11-05", ["bid:B1"])
        r = self.day("2026-11-06", bids=[fx.bid("B1", "홍보 애니메이션", deadline="2026-12-05 18:00")])
        self.assertEqual(self.ids(r), [])
        self.assertEqual(self.src(r, "bid")["changed_shown_count"], 1)

    def test_merged_grant_shown_by_one_origin_does_not_come_back(self):
        k = fx.kocca("K1", "애니메이션 제작 지원", end="2026-12-10")
        b = fx.bizinfo("P1", "애니메이션 제작 지원", end="20261210")
        r = self.day("2026-11-05", koccas=[k], bizinfos=[b])
        self.assertEqual(sorted(r["items"][0]["keys"]), ["grant_bizinfo:P1", "grant_kocca:K1"])
        shown(self.out, "2026-11-05", ["grant_kocca:K1"])
        self.assertEqual(self.ids(self.day("2026-11-06", koccas=[k], bizinfos=[b])), [])

    def requested(self, keys_status):
        p = self.out.parent / "sheet.json"
        p.write_text(json.dumps({"rows": [{"key": k, "status": s} for k, s in keys_status]}, ensure_ascii=False),
                     encoding="utf-8")
        return p

    def test_changed_item_under_review_is_listed_again(self):  # 티켓 20, D18
        self.day("2026-11-05", bids=[fx.bid("B1", "홍보 애니메이션"), fx.bid("B2", "캐릭터 애니메이션")])
        shown(self.out, "2026-11-05", ["bid:B1", "bid:B2"])
        sheet = self.requested([("bid:B1", "2차 검토 중"), ("bid:B2", "보류")])
        bids = [fx.bid("B1", "홍보 애니메이션", deadline="2026-12-05 18:00"),
                fx.bid("B2", "캐릭터 애니메이션", deadline="2026-12-05 18:00")]
        r = self.run_day(FakeTransport(ok_routes(bids=bids)), date="2026-11-06", sheet_rows=sheet)
        self.assertEqual(self.ids(r), ["B1"])
        self.assertIs(r["items"][0]["renotify"], True)
        self.assertEqual(self.src(r, "bid")["changed_shown_count"], 1)  # B2는 지금처럼 건수만

    def test_renotify_survives_a_failed_send_until_it_is_shown(self):  # 재리뷰 (c)2
        self.day("2026-11-05", bids=[fx.bid("B1", "홍보 애니메이션")])
        shown(self.out, "2026-11-05", ["bid:B1"])
        sheet = self.requested([("bid:B1", "2차 검토 중")])
        changed = [fx.bid("B1", "홍보 애니메이션", deadline="2026-12-05 18:00")]
        self.run_day(FakeTransport(ok_routes(bids=changed)), date="2026-11-06", sheet_rows=sheet)
        # 11-06 메일 발송 실패: 노출 기록 없음 -> 11-07에도 다시 나와야 한다
        r = self.run_day(FakeTransport(ok_routes(bids=changed)), date="2026-11-07", sheet_rows=sheet)
        self.assertEqual(self.ids(r), ["B1"])
        shown(self.out, "2026-11-07", ["bid:B1"])
        r = self.run_day(FakeTransport(ok_routes(bids=changed)), date="2026-11-08", sheet_rows=sheet)
        self.assertEqual(self.ids(r), [])

    def test_unreadable_sheet_rows_are_warned(self):  # 재리뷰 (a)2: 재알림 입력의 실패를 숨기지 않는다
        bad = self.out.parent / "sheet.json"
        bad.write_text("{broken", encoding="utf-8")
        r = self.run_day(FakeTransport(ok_routes(bids=[fx.bid("B1", "홍보 애니메이션")])), sheet_rows=bad)
        self.assertTrue(any("시트" in w for w in r["warnings"]))

    def test_alias_stays_when_one_origin_is_collected_alone(self):  # 재리뷰 (c)3
        k = fx.kocca("K1", "애니메이션 제작 지원", end="2026-12-10")
        b = fx.bizinfo("P1", "애니메이션 제작 지원", end="20261210")
        self.day("2026-11-05", koccas=[k], bizinfos=[b])
        self.day("2026-11-06", koccas=[fx.kocca("K1", "애니메이션 제작 지원", end="2026-12-10", posted="2026-11-06")])
        ledger = json.loads((self.state / "ledger.json").read_text(encoding="utf-8"))
        self.assertEqual(ledger["grant_kocca:K1"]["alias_of"], "grant_bizinfo:P1")

    def test_unchanged_item_under_review_is_not_listed_again(self):
        self.day("2026-11-05", bids=[fx.bid("B1", "홍보 애니메이션")])
        shown(self.out, "2026-11-05", ["bid:B1"])
        sheet = self.requested([("bid:B1", "2차 검토 요청")])
        r = self.run_day(FakeTransport(ok_routes(bids=[fx.bid("B1", "홍보 애니메이션")])), date="2026-11-06",
                         sheet_rows=sheet)
        self.assertEqual(self.ids(r), [])

    def test_broken_ledger_is_kept_aside_and_reported(self):  # 티켓 22, 불변 규칙 9
        self.state.mkdir(parents=True, exist_ok=True)
        (self.state / "ledger.json").write_text("{broken", encoding="utf-8")
        r = self.day("2026-11-05", bids=[fx.bid("B1", "홍보 애니메이션")])
        self.assertTrue(any("ledger.json" in w for w in r["warnings"]))
        kept = list(self.state.glob("ledger.broken-*.json"))
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0].read_text(encoding="utf-8"), "{broken")

    def test_ledger_keeps_sheet_row_fields(self):  # 티켓 21: 시트는 원장 기준으로 쓴다
        self.day("2026-11-05", bids=[fx.bid("B1", "홍보 애니메이션", price=50000000, deadline="2026-11-30 18:00")])
        e = json.loads((self.state / "ledger.json").read_text(encoding="utf-8"))["bid:B1"]
        self.assertEqual({k: e[k] for k in ("kind", "source", "title", "price", "deadline")},
                         {"kind": "bid", "source": "bid", "title": "홍보 애니메이션", "price": 50000000,
                          "deadline": "2026-11-30"})
        for k in ("agency", "registered", "url", "matched"):
            self.assertIn(k, e)

    def test_merged_grant_member_points_to_the_primary_row(self):
        k = fx.kocca("K1", "애니메이션 제작 지원", end="2026-12-10")
        b = fx.bizinfo("P1", "애니메이션 제작 지원", end="20261210")
        self.day("2026-11-05", koccas=[k], bizinfos=[b])
        ledger = json.loads((self.state / "ledger.json").read_text(encoding="utf-8"))
        self.assertEqual(ledger["grant_kocca:K1"]["alias_of"], "grant_bizinfo:P1")
        self.assertNotIn("alias_of", ledger["grant_bizinfo:P1"])

    def test_first_shown_date_is_not_overwritten(self):
        self.day("2026-11-05", bids=[fx.bid("B1", "홍보 애니메이션")])
        shown(self.out, "2026-11-05", ["bid:B1", "bid:UNKNOWN"])
        self.day("2026-11-06", bids=[fx.bid("B1", "홍보 애니메이션")])
        shown(self.out, "2026-11-06", ["bid:B1"])
        self.day("2026-11-07", bids=[fx.bid("B1", "홍보 애니메이션")])
        ledger = json.loads((self.state / "ledger.json").read_text(encoding="utf-8"))
        self.assertEqual(ledger["bid:B1"]["first_shown"], "2026-11-05")
        self.assertNotIn("bid:UNKNOWN", ledger)

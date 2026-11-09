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

    def test_first_shown_date_is_not_overwritten(self):
        self.day("2026-11-05", bids=[fx.bid("B1", "홍보 애니메이션")])
        shown(self.out, "2026-11-05", ["bid:B1", "bid:UNKNOWN"])
        self.day("2026-11-06", bids=[fx.bid("B1", "홍보 애니메이션")])
        shown(self.out, "2026-11-06", ["bid:B1"])
        self.day("2026-11-07", bids=[fx.bid("B1", "홍보 애니메이션")])
        ledger = json.loads((self.state / "ledger.json").read_text(encoding="utf-8"))
        self.assertEqual(ledger["bid:B1"]["first_shown"], "2026-11-05")
        self.assertNotIn("bid:UNKNOWN", ledger)

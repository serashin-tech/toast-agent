import contextlib
import io
import json

from helpers import Base, FakeTransport, ok_routes, bid_filter_md, ENV, KEY
import fixtures as fx
import gov_agent.cli as cli

XML_ERR = ('<OpenAPI_ServiceResponse><cmmMsgHeader><errMsg>SERVICE ERROR</errMsg>'
           '<returnAuthMsg>{}</returnAuthMsg><returnReasonCode>{}</returnReasonCode></cmmMsgHeader>'
           '</OpenAPI_ServiceResponse>')


class SourceIsolation(Base):
    def test_one_source_failure_does_not_stop_others_and_is_classified(self):
        cases = {"pending_approval": (200, XML_ERR.format("SERVICE_ACCESS_DENIED_ERROR", "20")),
                 "auth": (200, XML_ERR.format("SERVICE_KEY_IS_NOT_REGISTERED_ERROR", "30")),
                 "rate_limit": (200, XML_ERR.format("LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR", "22")),
                 "network": OSError("연결 끊김"),
                 "format": (200, "이건 JSON이 아님")}
        for kind, bad in cases.items():
            with self.subTest(kind=kind):
                routes = ok_routes(koccas=[fx.kocca("K1", "사업")])
                routes["BidPublicInfoService02"] = bad
                self.setUp()
                r = self.run_day(FakeTransport(routes))
                b = self.src(r, "bid")
                self.assertEqual((b["status"], b["error"]["kind"]), ("failed", kind))
                self.assertEqual(self.src(r, "grant_kocca")["status"], "ok")
                self.assertEqual(len(self.items(r, "grant")), 1)

    def test_http_errors_are_classified(self):
        for code, kind in [(401, "auth"), (429, "rate_limit"), (500, "network")]:
            with self.subTest(code=code):
                routes = ok_routes()
                routes["1421000/bizinfo"] = (code, "")
                self.setUp()
                self.assertEqual(self.src(self.run_day(FakeTransport(routes)), "grant_bizinfo")["error"]["kind"], kind)

    def test_failed_day_does_not_advance_incremental_baseline(self):
        self.run_day(FakeTransport(ok_routes()), date="2026-11-05")
        bad = ok_routes()
        bad["BidPublicInfoService02"] = OSError("down")
        r = self.run_day(FakeTransport(bad), date="2026-11-06")
        self.assertEqual(self.src(r, "bid")["last_success_at"], "2026-11-05T09:00:00+09:00")
        self.assertTrue(self.src(r, "grant_bizinfo")["last_success_at"].startswith("2026-11-06"))
        t = FakeTransport(ok_routes())
        self.run_day(t, date="2026-11-07")
        self.assertEqual(t.calls_to("BidPublicInfoService02")[0]["inqryBgnDt"], "202611050900")

    def test_failed_day_items_are_still_new_next_time(self):
        bad = ok_routes(bids=[fx.bid("A1", "x")])
        bad["BidPublicInfoService02"] = (500, "")
        self.run_day(FakeTransport(bad))
        r = self.run_day(FakeTransport(ok_routes(bids=[fx.bid("A1", "x")])), date="2026-11-06")
        self.assertEqual([(i["id"], i["is_new"]) for i in self.items(r, "bid")], [("A1", True)])


class CallBudget(Base):
    def test_source_stops_at_budget_and_is_marked_limit_near(self):
        page = lambda p: (200, fx.envelope([fx.bid(f"A{p['pageNo']}-{i}", "x") for i in range(100)], total=9999))
        routes = ok_routes()
        routes["BidPublicInfoService02"] = page
        t = FakeTransport(routes)
        r = self.run_day(t, call_budget=2)
        b = self.src(r, "bid")
        self.assertEqual(len(t.calls_to("BidPublicInfoService02")), 2)
        self.assertEqual((b["status"], b["error"]["kind"], b["fetched"]), ("limit_near", "rate_limit", 200))
        self.assertIsNone(b["last_success_at"])
        self.assertEqual(self.src(r, "grant_bizinfo")["status"], "ok")

    def test_budget_is_counted_per_day_across_runs(self):
        self.run_day(FakeTransport(ok_routes()), call_budget=1)
        t = FakeTransport(ok_routes())
        r = self.run_day(t, call_budget=1)  # 같은 날 두 번째 실행
        self.assertEqual(self.src(r, "bid")["status"], "limit_near")
        self.assertEqual(t.calls, [])


class KeySafety(Base):
    def test_key_never_reaches_result_or_state(self):
        routes = ok_routes()
        routes["BidPublicInfoService02"] = OSError(f"실패 https://x?serviceKey={KEY} 호출")
        routes["1421000/bizinfo"] = OSError("serviceKey=SECRETKEY+abc123 실패")
        self.run_day(FakeTransport(routes))
        for f in [*self.out.rglob("*.json"), *self.state.rglob("*")]:
            if f.is_file():
                txt = f.read_text(encoding="utf-8")
                self.assertNotIn("SECRETKEY", txt)
                self.assertNotIn("abc123", txt)

    def test_missing_key_fails_data_go_kr_sources_as_auth_without_calling_them(self):
        t = FakeTransport(ok_routes())
        r = self.run_day(t, env={})
        kinds = {s["id"]: (s["error"] or {}).get("kind") for s in r["sources"]}
        self.assertEqual(kinds, {"bid": "auth", "grant_kocca": "auth", "grant_bizinfo": "auth",
                                 "outsource_cglink": None})  # CGLink RSS는 인증키가 필요 없다
        self.assertTrue(all("cglink.com" in u for u, _ in t.calls))

    def test_missing_kocca_url_fails_only_that_source_as_format(self):
        r = self.run_day(FakeTransport(ok_routes()), env={"DATA_GO_KR_SERVICE_KEY": KEY})
        self.assertEqual(self.src(r, "grant_kocca")["error"]["kind"], "format")
        self.assertEqual(self.src(r, "bid")["status"], "ok")

    def test_key_is_read_from_env_file_and_environment_wins(self):
        envfile = self.settings.parent / ".env"
        envfile.write_text("# 주석\nDATA_GO_KR_SERVICE_KEY=FILEKEY\nKOCCA_API_URL='https://kocca.test/api'\n", encoding="utf-8")
        t = FakeTransport(ok_routes())
        argv = ["run", "--date", "2026-11-05", "--out", str(self.out), "--settings", str(self.settings),
                "--state", str(self.state), "--env-file", str(envfile)]
        with contextlib.redirect_stdout(io.StringIO()):
            cli.main(argv, transport=t, environ={})
        self.assertEqual(t.calls_to("BidPublicInfoService02")[0]["serviceKey"], "FILEKEY")
        t2 = FakeTransport(ok_routes())
        with contextlib.redirect_stdout(io.StringIO()):
            cli.main(argv, transport=t2, environ={"DATA_GO_KR_SERVICE_KEY": "ENVKEY"})
        self.assertEqual(t2.calls_to("BidPublicInfoService02")[0]["serviceKey"], "ENVKEY")


class SettingsBehaviour(Base):
    def bids(self):
        return [fx.bid("A", "애니메이션 제작"), fx.bid("B", "청소 용역")]

    def test_value_changed_in_md_applies_on_next_run(self):
        self.set_settings(bid=bid_filter_md(include="애니메이션"))
        r1 = self.run_day(FakeTransport(ok_routes(bids=self.bids())))
        self.assertEqual([i["id"] for i in self.items(r1, "bid")], ["A"])
        self.set_settings(bid=bid_filter_md(include="청소"))
        r2 = self.run_day(FakeTransport(ok_routes(bids=self.bids())), date="2026-11-06")
        self.assertEqual([i["id"] for i in self.items(r2, "bid")], ["B"])

    def test_history_section_is_not_read_as_values(self):
        text = bid_filter_md(include="애니메이션") + "| 2026-11-05 | 제외 키워드 | | 애니메이션 | 시험 | 관리자 |\n"
        text += "\n## 값 같은 표\n\n| 항목 | 값 | 비고 |\n|---|---|---|\n| 포함 키워드 | 청소 | |\n"
        self.set_settings(bid=text)
        r = self.run_day(FakeTransport(ok_routes(bids=self.bids())))
        self.assertEqual([i["id"] for i in self.items(r, "bid")], ["A"])
        self.assertFalse(r["settings"]["fallback_used"])

    def test_broken_settings_fall_back_to_last_good(self):
        self.set_settings(bid=bid_filter_md(include="애니메이션"))
        self.run_day(FakeTransport(ok_routes()))
        broken = {"표 없음": "# 설정\n표가 없다\n",
                  "필수 행 없음": "| 항목 | 값 | 비고 |\n|---|---|---|\n| 포함 키워드 | 청소 | |\n",
                  "숫자 아님": bid_filter_md(pmin="비싸게")}
        for why, text in broken.items():
            with self.subTest(why):
                self.set_settings(bid=text)
                r = self.run_day(FakeTransport(ok_routes(bids=self.bids())), date="2026-11-06")
                self.assertEqual([i["id"] for i in self.items(r, "bid")], ["A"])  # 직전 정상 설정의 키워드
                self.assertTrue(r["settings"]["fallback_used"])
                self.assertIn("bid-filter.md", r["settings"]["fallback_reason"])
                (self.state / "state.json").unlink()  # 다음 하위 시험이 새로 판정하도록 증분 상태를 비운다

    def test_last_good_settings_are_not_overwritten_by_broken_ones(self):
        self.set_settings(bid=bid_filter_md(include="애니메이션"))
        self.run_day(FakeTransport(ok_routes()))
        self.set_settings(bid="깨짐")
        self.run_day(FakeTransport(ok_routes()), date="2026-11-06")
        r = self.run_day(FakeTransport(ok_routes(bids=self.bids())), date="2026-11-07")
        self.assertEqual([i["id"] for i in self.items(r, "bid")], ["A"])

    def test_broken_settings_without_last_good_run_with_defaults(self):
        self.set_settings(bid="깨짐")
        r = self.run_day(FakeTransport(ok_routes(bids=self.bids())))
        self.assertEqual(len(self.items(r, "bid")), 2)
        self.assertTrue(r["settings"]["fallback_used"])
        self.assertIn("기본값", r["settings"]["fallback_reason"])

    def test_shipped_settings_are_valid(self):
        # 저장소에는 실제 설정 대신 템플릿만 둔다(H12). 템플릿이 오류 없이 읽히는지만 본다.
        from pathlib import Path
        shipped = Path(__file__).resolve().parents[2] / "settings-template"
        from gov_agent.runner import run
        from helpers import KST
        from datetime import datetime
        t = FakeTransport(ok_routes(bids=self.bids(), koccas=[fx.kocca("K1", "무엇이든")]))
        run("2026-11-05", self.out, shipped, self.state, t, env=ENV, now=datetime(2026, 11, 5, 9, tzinfo=KST))
        r = json.loads((self.out / "gov_2026-11-05.json").read_text(encoding="utf-8"))
        self.assertFalse(r["settings"]["fallback_used"])

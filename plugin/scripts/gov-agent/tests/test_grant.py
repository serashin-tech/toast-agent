from helpers import Base, FakeTransport, ok_routes, grant_md
import fixtures as fx


class GrantCollection(Base):
    def run_grants(self, koccas=(), bizinfos=(), **kw):
        return self.run_day(FakeTransport(ok_routes(koccas=koccas, bizinfos=bizinfos)), **kw)

    def test_same_program_is_merged_with_both_origins_and_dday(self):
        k = fx.kocca("K1", "2027 애니메이션 제작지원 사업", end="2026-12-10")
        b = fx.bizinfo("B1", "2027 애니메이션 제작지원  사업", end="20261210", target=None)
        r = self.run_grants([k], [b])
        (g,) = self.items(r, "grant")
        self.assertEqual(g["source"], "grant")
        self.assertEqual(g["extra"]["origins"], ["grant_bizinfo", "grant_kocca"])
        self.assertEqual(g["id"], "B1")  # 대표는 중소기업 지원사업 API
        self.assertTrue(g["url"].startswith("https://www.bizinfo.go.kr"))
        self.assertEqual(g["extra"]["dday"], 35)  # 2026-11-05 -> 2026-12-10
        self.assertEqual((g["extra"]["period_start"], g["extra"]["period_end"], g["deadline"]),
                         ("2026-12-01", "2026-12-10", "2026-12-10"))
        self.assertEqual(self.src(r, "grant_kocca")["included"], 1)
        self.assertEqual(self.src(r, "grant_bizinfo")["included"], 1)

    def test_bizinfo_calls_the_list_operation_without_a_date_filter(self):  # 실제 응답 확인(2026-11-11)
        self.run_grants(date="2026-11-05")
        t = FakeTransport(ok_routes())
        self.run_day(t, date="2026-11-06")
        (p,) = t.calls_to("1421000/bizinfo/pblancBsnsService")
        self.assertNotIn("updtPnttm", p)  # 그날 하루만 맞추는 필터라 증분에 쓸 수 없다. 전체를 받고 원장으로 가린다

    def test_empty_fields_of_main_are_filled_from_kocca(self):
        k = fx.kocca("K1", "같은 사업", category="콘텐츠제작지원")
        b = fx.bizinfo("B1", "같은 사업", field="")
        (g,) = self.items(self.run_grants([k], [b]), "grant")
        self.assertEqual(g["extra"]["category"], "콘텐츠제작지원")

    def test_different_deadline_is_not_merged(self):
        r = self.run_grants([fx.kocca("K1", "같은 사업", end="2026-12-10")],
                            [fx.bizinfo("B1", "같은 사업", end="20261220")])
        self.assertEqual(len(self.items(r, "grant")), 2)

    def test_single_origin_keeps_its_source_and_negative_dday(self):
        (g,) = self.items(self.run_grants([fx.kocca("K1", "지난 사업", end="2026-11-01")]), "grant")
        self.assertEqual((g["source"], g["extra"]["origins"], g["extra"]["dday"]), ("grant_kocca", ["grant_kocca"], -4))

    def test_grant_criteria_keywords_and_exclusion(self):
        self.set_settings(grant=grant_md(keywords="애니메이션", exclude="해외"))
        ks = [fx.kocca("K1", "애니메이션 제작 지원"), fx.kocca("K2", "게임 지원"), fx.kocca("K3", "해외 애니메이션 전시")]
        r = self.run_grants(ks)
        self.assertEqual([(i["id"], i["matched_keywords"]) for i in self.items(r, "grant")],
                         [("K1", ["애니메이션"])])

    def test_kocca_incremental_is_decided_locally_by_registration_date(self):
        old, new = fx.kocca("K1", "옛 공고", posted="2026-10-01"), fx.kocca("K2", "새 공고", posted="2026-11-06")
        self.run_grants([old], date="2026-11-05")
        r = self.run_grants([fx.kocca("K0", "더 옛 공고", posted="2026-09-01"), old, new], date="2026-11-06")
        self.assertEqual([i["id"] for i in self.items(r, "grant")], ["K2"])

    def test_unchanged_grants_are_skipped_on_next_run(self):
        k = fx.kocca("K1", "사업")
        self.run_grants([k])
        self.assertEqual(self.items(self.run_grants([k], date="2026-11-06"), "grant"), [])

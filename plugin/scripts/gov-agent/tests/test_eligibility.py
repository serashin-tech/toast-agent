import tempfile
import unittest
from pathlib import Path

from gov_agent.eligibility import build_eligibility

HEAD = "# 설정: 회사 프로필\n\n## 값\n\n| 항목 | 값 | 확인 상태 | 출처 |\n|---|---|---|---|\n"
TAIL = "\n## 변경 이력\n\n| 일자 | 항목 | 변경 전 | 변경 후 | 사유 | 변경자 |\n|---|---|---|---|---|---|\n"
EV = {"quote": "공고문 3쪽 문장", "location": "3쪽 2항"}


def req(kind, params=None, evidence=EV, category="참가자격", text="요건"):
    return {"category": category, "text": text, "kind": kind, "params": params or {}, "evidence": evidence}


class Eligibility(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "company-profile.md"

    def profile(self, rows):
        self.path.write_text(HEAD + "".join(f"| {a} | {b} | {c} | 시험 |\n" for a, b, c in rows) + TAIL, encoding="utf-8")

    def review(self, *reqs, unreadable=None, path=None):
        data = {"bid_id": "R26BK001", "requirements": list(reqs), "unreadable_files": unreadable or []}
        return build_eligibility(data, path if path is not None else self.path)

    def verdicts(self, out):
        return [r["verdict"] for r in out["requirements"]]

    def test_confirmed_values_give_met_or_unmet(self):
        self.profile([("소재지", "전북 전주시 덕진구", "확인됨"), ("중소기업 확인", "보유", "확인됨"),
                      ("직접생산확인", "미보유", "확인됨")])
        out = self.review(req("소재지", {"지역": "전북"}), req("소재지", {"지역": "서울"}),
                          req("중소기업확인"), req("직접생산확인"))
        self.assertEqual(self.verdicts(out), ["met", "unmet", "met", "unmet"])
        self.assertEqual(out["requirements"][0]["profile_item"], "소재지")
        self.assertEqual(out["requirements"][0]["evidence"], EV)
        self.assertEqual(out["bid_id"], "R26BK001")

    def test_region_names_are_normalized_and_ambiguous_regions_need_check(self):
        # 광역 지자체의 공식 이름과 줄임 이름은 같은 곳으로 본다. 틀린 미충족이 비권고로 이어지지 않게
        # 서로 다른 광역 지자체로 확인될 때만 unmet이고, 판단할 수 없는 지역은 needs_check이다.
        self.profile([("소재지", "전북 전주시 덕진구", "확인됨")])
        out = self.review(req("소재지", {"지역": "전북특별자치도"}), req("소재지", {"지역": "전라북도"}),
                          req("소재지", {"지역": "전주시"}), req("소재지", {"지역": "서울특별시"}),
                          req("소재지", {"지역": "익산시"}))
        self.assertEqual(self.verdicts(out), ["met", "met", "met", "unmet", "needs_check"])

    def test_unconfirmed_profile_values_need_check(self):
        self.profile([("중소기업 확인", "보유", "대표 확인 필요"), ("벤처기업 확인", "보유", "일부 확인"),
                      ("직접생산확인", "", "대표 확인 필요")])
        out = self.review(req("중소기업확인"), req("벤처확인"), req("직접생산확인"), req("부설연구소"))
        self.assertEqual(self.verdicts(out), ["needs_check"] * 4)  # 마지막은 프로필에 항목이 없음
        self.assertEqual(out["overall"], "conditional")

    def test_other_kind_is_reference_and_missing_evidence_needs_check(self):  # D36
        self.profile([("소재지", "전북 전주시", "확인됨")])
        out = self.review(req("기타"), req("소재지", {"지역": "전북"}, evidence=None),
                          req("소재지", {"지역": "전북"}, evidence={"quote": "문장", "location": ""}),
                          req("소재지", {"지역": "전북"}, evidence={"quote": "", "location": "1쪽"}))
        self.assertEqual(self.verdicts(out), ["reference"] + ["needs_check"] * 3)
        self.assertEqual(out["requirements"][1]["evidence"], {"quote": None, "location": None})

    def test_record_requirement_counts_only_confirmed_rows(self):
        self.profile([("수행 실적 1", "A사업, 2025, 5천만원", "확인됨"), ("수행 실적 2", "B사업, 2024, 3억원", "확인됨"),
                      ("수행 실적 3", "C사업, 금액 미확인", "일부 확인")])
        met = self.review(req("실적", {"min_count": 2, "min_amount": 50000000}))
        self.assertEqual(self.verdicts(met), ["met"])
        # 확인됨 행만으로는 3건에 못 미치지만 확인되지 않은 행까지 보면 가능 -> 확인필요
        self.assertEqual(self.verdicts(self.review(req("실적", {"min_count": 3}))), ["needs_check"])
        # 모든 행을 합쳐도 4건에 못 미침 -> 미충족
        self.assertEqual(self.verdicts(self.review(req("실적", {"min_count": 4}))), ["unmet"])
        # 금액 조건: 확인됨 행 중 1억 이상은 B 하나뿐이고 C는 금액 미확인 -> 2건 가능성은 확인필요
        self.assertEqual(self.verdicts(self.review(req("실적", {"min_count": 2, "min_amount": 100000000}))), ["needs_check"])

    def test_record_requirement_with_only_unconfirmed_rows_needs_check(self):
        self.profile([("수행 실적 1", "A사업, 5천만원", "일부 확인")])
        self.assertEqual(self.verdicts(self.review(req("실적", {"min_count": 1}))), ["needs_check"])

    def test_license_alternatives_codes_and_spacing(self):
        # 나라장터 공고의 업종 제한은 "A(코드) 또는 B(코드)" 형태가 많다. 하나라도 등록돼 있으면 충족이다.
        # 업종코드 표기와 띄어쓰기 차이로 틀린 미충족이 나오면 참가할 수 있는 공고가 비권고로 빠진다.
        self.profile([("등록한 업종(나라장터)", "애니메이션 제작업, 비디오물제작업, "
                       "소프트웨어사업자(디지털콘텐츠개발서비스사업)", "확인됨")])
        out = self.review(req("업종등록", {"업종": "비디오물제작업(3244) 또는 방송영상독립제작자(3230)"}),
                          req("업종등록", {"업종": "애니메이션 제작업(6490)"}),
                          req("업종등록", {"업종": "애니메이션제작업"}),
                          req("업종등록", {"업종": "소프트웨어사업자(디지털콘텐츠개발서비스사업)(1469)"}),
                          req("업종등록", {"업종": "방송영상독립제작자(3230) 또는 실내건축공사업(4990)"}),
                          req("업종등록", {"업종": "소프트웨어사업자(컴퓨터관련서비스사업)(1468)"}))
        self.assertEqual(self.verdicts(out), ["met", "met", "met", "met", "unmet", "unmet"])

    def test_personnel_requirement(self):
        self.profile([("보유 인력(직무별 인원, 경력 연수)", "애니메이터 3명, 디자이너 1명", "확인됨")])
        out = self.review(req("인력", {"role": "애니메이터", "min_count": 2}),
                          req("인력", {"role": "디자이너", "min_count": 2}),
                          req("인력", {"role": "PD", "min_count": 1}))
        self.assertEqual(self.verdicts(out), ["met", "unmet", "unmet"])

    def test_overall_rules(self):
        self.profile([("소재지", "전북 전주시", "확인됨")])
        met, unmet = req("소재지", {"지역": "전북"}), req("소재지", {"지역": "서울"})
        check = req("소재지", {"지역": "전북"}, evidence=None)
        self.assertEqual(self.review(met)["overall"], "recommend")
        self.assertEqual(self.review(met, check)["overall"], "conditional")
        self.assertEqual(self.review(met, check, unmet)["overall"], "not_recommend")
        self.assertEqual(self.review(unmet)["overall"], "not_recommend")

    def test_reference_conditions_do_not_change_the_overall_but_are_named(self):  # D36
        self.profile([("소재지", "전북 전주시", "확인됨")])
        out = self.review(req("소재지", {"지역": "전북"}), req("기타", text="청렴계약 이행서약서 제출"), req("기타"))
        self.assertEqual(out["overall"], "recommend")
        self.assertIn("참고 조건 2건", out["reason"])
        self.assertIn("대표", out["reason"])  # 참고 조건은 대표가 확인한다

    def test_only_reference_conditions_is_conditional(self):  # 대조할 요건이 없으면 권고하지 않는다
        self.profile([("소재지", "전북", "확인됨")])
        out = self.review(req("기타"), req("기타"))
        self.assertEqual(out["overall"], "conditional")
        self.assertIn("대조할 수 있는 요건이 없", out["reason"])

    def test_any_unmet_never_recommends(self):
        self.profile([("소재지", "전북 전주시", "확인됨"), ("중소기업 확인", "미보유", "확인됨")])
        for others in ([], [req("소재지", {"지역": "전북"})], [req("기타")]):
            out = self.review(req("중소기업확인"), *others)
            self.assertNotEqual(out["overall"], "recommend")

    def test_no_requirements_is_not_recommended(self):
        self.profile([("소재지", "전북", "확인됨")])
        self.assertEqual(self.review()["overall"], "conditional")

    def test_missing_or_unreadable_profile_extracts_only(self):
        reqs = [req("소재지", {"지역": "전북"}), req("기타")]
        for path in (Path(self._tmp.name) / "없음.md", self.path):
            with self.subTest(path=path.name):
                if path is self.path:
                    self.path.write_text("표가 없는 파일", encoding="utf-8")
                out = self.review(*reqs, path=path)
                self.assertEqual(out["overall"], "extract_only")
                self.assertEqual(self.verdicts(out), ["extract_only"] * 2)
                self.assertTrue(all(r["profile_item"] is None for r in out["requirements"]))
        self.assertEqual(self.review(*reqs, path=None)["overall"], "extract_only")

    def test_disclaimer_and_unreadable_files_always_present(self):
        files = [{"name": "과업지시서.hwp", "url": "https://g2b.test/x.hwp"}]
        for profile in (True, False):
            if profile:
                self.profile([("소재지", "전북", "확인됨")])
            out = self.review(req("소재지", {"지역": "전북"}), unreadable=files, path=self.path if profile else None)
            self.assertIn("최종 판단은 대표가 합니다", out["disclaimer"])
            self.assertEqual(out["unreadable_files"], files)
            self.assertTrue(out["reason"])

    def test_history_rows_of_profile_are_not_values(self):
        self.profile([("소재지", "전북", "확인됨")])
        self.path.write_text(self.path.read_text(encoding="utf-8") + "| 2026-11-06 | 소재지 | 전북 | 서울 | 시험 | 관리자 |\n",
                             encoding="utf-8")
        self.assertEqual(self.verdicts(self.review(req("소재지", {"지역": "전북"}))), ["met"])


if __name__ == "__main__":
    unittest.main()

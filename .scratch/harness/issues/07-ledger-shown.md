# 07: 보여 준 항목 제외: 로컬 원장과 노출 기록 (IM-09)

**What to build:** 어제 보여 준 항목은 다시 나오지 않고, 전달에 실패한 날의 항목은 다음 날 다시 나온다.

**Blocked by:** 03

**Status:** resolved (2026-11-10)

- [x] `state/ledger.json`이 노출 판정의 정본
- [x] 보여 준 항목의 내용 변경은 `changed_shown_count`로만 셈
- [x] 병합 지원사업은 출처가 어긋나도 같은 사업으로 봄
- [x] 메일 발송 성공 때만 `shown_<날짜>.json`(D31)

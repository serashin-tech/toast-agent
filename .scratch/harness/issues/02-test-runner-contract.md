# 02: 통합 시험 실행기와 결과 계약 시험

**What to build:** 명령 하나로 모든 시험 묶음이 돌고, gov-agent 결과 형식이 깨지면 daily-report 쪽 시험이 실패한다.

**Blocked by:** 01

**Status:** resolved (2026-11-10)

- [x] `run_tests.py`가 세 묶음을 각자 폴더에서 실행
- [x] gov 결과 파일을 daily-report가 형식 오류 없이 모두 읽는 시험

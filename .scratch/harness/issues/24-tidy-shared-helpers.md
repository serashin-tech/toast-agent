# 24: 공용 도우미 정리 (리뷰 냄새)

**What to build:** 결과 파일 순회, evidence 조립, .env 읽기, 시트 상태 이름이 한 곳에 있다.

**Blocked by:** None (can start immediately)

**Status:** resolved (2026-11-11)

출처: 2026-11-10 코드 리뷰(표준·명세 두 축)

- [x] write_shown과 build_rows의 결과 파일 순회를 한 함수로(티켓 21에서 build_rows가 원장을 읽게 되어 중복이 사라짐)
- [x] eligibility·brief의 evidence 조립을 quotes 모듈로
- [x] 상태 이름 목록 한 곳(Code.gs는 주석으로 같은 목록을 가리킴)
- [x] rehearse.py가 시험 도우미 대신 고정 자료 모듈을 씀

남긴 것(2026-11-11 재리뷰): `.env` 읽기는 두 패키지(gov_agent, daily_report)가 서로 의존하지 않게 하려고 각자 둔다. 상태 이름 목록도 두 패키지에 하나씩 두고 계약 시험이 같은지 강제한다. 정본은 decisions.md D26이다.

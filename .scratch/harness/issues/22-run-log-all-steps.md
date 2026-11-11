# 22: 실행 기록에 시트·현황판 결과와 숨은 실패 남기기

**What to build:** 시트 기록, 현황판 게시, 원장·결과 파일 읽기 실패가 실행 기록에 남는다(불변 규칙 9, D31).

**Blocked by:** 08

**Status:** resolved (2026-11-11)

출처: 2026-11-10 코드 리뷰(표준·명세 두 축)

- [x] record-publish 외에 단계 결과를 남기는 명령 또는 인자
- [x] 깨진 ledger.json을 덮어쓰지 않고 보관·보고
- [x] build_rows·write_shown이 읽지 못한 파일 수를 알림

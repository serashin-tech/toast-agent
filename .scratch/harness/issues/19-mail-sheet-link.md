# 19: 신규 알림 메일의 시트 링크 (D30)

**What to build:** 메일에 수집 이력 시트 링크가 들어간다. 스킬은 `.env`를 읽지 않으므로 코드가 `.env`의 `SHEET_URL`을 읽는다.

**Blocked by:** 10

**Status:** resolved (2026-11-10)

- [x] `mail` 명령이 `--sheet-url`이 없으면 `.env`의 `SHEET_URL`을 씀
- [x] 시험 추가

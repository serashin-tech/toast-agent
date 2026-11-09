# 04: 플러그인 골격, 불변 규칙 주입 훅, 구조 검사

**What to build:** `--plugin-dir`로 띄우면 세션 시작 때 불변 규칙이 들어오고, 구조 검사가 시험에 포함된다.

**Blocked by:** 01

**Status:** resolved (2026-11-10)

- [x] SessionStart 훅이 invariants.md를 그대로 넣음
- [x] `claude plugin validate --strict` 통과
- [x] bin/ 없음, 플러그인 경로 참조가 모두 존재

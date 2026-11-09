# 토스트 애니메이션 스튜디오: 구현 폴더

정부사업·시장 정보 에이전트(공공데이터포털 API 직접 연동, artifact 게시)의 구현 작업 폴더다.
상위 PRD는 `../05_PRD/`에 있다.

## 폴더 구조

- `gov-agent/`: 정부사업 에이전트(공공데이터포털 API 3종과 CGLink 외주 RSS 수집, 필터, 제안 가능성 검토, 시연 판정)
- `market-agent/`: 시장 정보 에이전트(유튜브 수집, 제목·설명문 요약. 자막은 쓰지 않음)
- `daily-report/`: 두 에이전트의 결과를 합치는 통합 보고서와 artifact 게시(공통)
- `.env`: API 키(루트 한 곳, 보고서와 로그에 쓰지 않는다)
- 폴더 지도와 실행 흐름: `ARCHITECTURE.md`(먼저 읽는다)
- 결정·요구사항·리스크(구현 PRD에서 옮김, 번호 유지): `docs/decisions.md`
- AI 시안 파이프라인(공고 검토 → 2차 검토 → Adobe 커넥터로 1차 시연 데모) 명세: `.scratch/ai-draft-pipeline/spec.md`
- `DEMO.md`: 공고 1건을 제안 조건 검토, 2차 검토, 1차 시연 데모까지 처리하는 대화형 절차(무인 루틴에서 실행하지 않음)
- `demo-sample/`: 리허설용 가상 공고 R26BK999와 추출 결과 예시
- `drafts/<공고번호>/`: 공고별 산출물(requirements, eligibility, signals, brief, prompt, outputs)

## Agent skills

### Issue tracker

이슈는 이 폴더의 `.scratch/` 아래 로컬 마크다운으로 관리한다. See `docs/agents/issue-tracker.md`.

### Triage labels

기본 라벨 5종(needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix)을 그대로 쓴다. See `docs/agents/triage-labels.md`.

### Domain docs

단일 컨텍스트(CONTEXT.md와 docs/adr/는 이 폴더 루트). See `docs/agents/domain.md`.

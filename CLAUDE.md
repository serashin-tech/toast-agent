# toast-agent

토스트 애니메이션 스튜디오의 정부사업·시장 정보 에이전트 저장소다. 저장소 루트가 마켓플레이스(`toast-agent`)이고 `plugin/`이 플러그인 `toast-agent`(토스트 에이전트)다. 토스트 에이전트 안에 정부사업 에이전트(`plugin/scripts/gov-agent/`)와 시장 정보 에이전트(`plugin/scripts/market-agent/`)가 있다. 이 파일은 저장소를 **고치는 사람**을 위한 목차다. 승인용 상위 PRD는 고객 폴더의 `05_PRD/`에 있다.

## 먼저 읽을 것

- 구조와 실행 흐름: `ARCHITECTURE.md`
- 결정(D1~D34)·요구사항·리스크: `docs/decisions.md`. 하네스 결정(H1~H18): `.scratch/harness/map.md`
- 용어: `CONTEXT.md`. 이 용어로 이름을 짓는다
- 되돌리기 어려운 결정의 근거: `docs/adr/`
- 명세와 이슈: `.scratch/<기능>/spec.md`, `.scratch/<기능>/issues/NN-*.md` (규칙은 `docs/agents/issue-tracker.md`, 라벨은 `docs/agents/triage-labels.md`)
- 결과 파일 계약: `docs/result-format.md`

## 구조

- `plugin/hooks/`: 세션 시작 때 불변 규칙 주입, 설정 파일 변경 이력 검사
- `plugin/rules/invariants.md`: 불변 규칙 원본(플러그인은 CLAUDE.md를 실을 수 없어 훅이 넣는다)
- `plugin/skills/`, `plugin/agents/`: 운영 절차(daily-routine 등)와 추출 에이전트
- `plugin/scripts/`: `gov.py`, `report.py`(진입점), `gov-agent/`, `daily-report/`, `market-agent/`, `settings-template/`, `fixtures/`
- `plugin/tests/`: 훅, 결과 계약, 리허설 시험
- `apps-script/`: 시트에 붙일 Apps Script 원본(시트 기록, 메일 발송, 마감 지난 행 정리)

## 지킬 것

- 운영 데이터(`.env`, `settings/`, `results/`, `reports/`, `runs/`, `state/`, `drafts/`)는 대표 PC 작업 폴더에만 둔다. 저장소에 넣지 않는다.
- 코드의 기본 경로는 현재 폴더(작업 폴더) 기준이다. 코드 위치에서 경로를 계산하지 않는다.
- 판정은 코드가 하고 Claude는 추출만 한다. 근거 문장이 없으면 확인필요다.
- 스킬·에이전트 본문의 경로는 `${CLAUDE_PLUGIN_ROOT}/…`로 적는다.

## 고치는 방법

- 커밋 전에 `python -X utf8 plugin/scripts/run_tests.py`를 돌려 모두 통과시킨다. 새 시험은 각 묶음의 `tests/test_*.py`에 둔다.
- 코드는 TDD로 고친다(시험 먼저). 시험은 밖에서 보이는 동작만 본다.
- 매니페스트를 고치면 `claude plugin validate .`과 `claude plugin validate plugin`을 돌린다.
- 대표에게 내보낼 변경은 `plugin/.claude-plugin/plugin.json`의 `version`을 올린다.
- 결정이 바뀌면 `docs/decisions.md`(또는 `map.md`)를 먼저 고치고, 되돌리기 어려운 결정은 ADR을 더한다.

## Agent skills

이슈 트래커는 `.scratch/` 아래 로컬 마크다운이다. 라벨은 기본 5종(needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix)을 쓴다. 도메인 문서는 단일 컨텍스트(`CONTEXT.md`, `docs/adr/`)다.

# 아키텍처: 토스트 정부사업·시장 정보 에이전트

이 문서는 구현 폴더(`07_Implementation`)의 지도다. 무엇이 어디에 있고, 무엇이 무엇에 기대며, 어느 파일이 정본인지를 적는다. 결정의 이유는 `docs/decisions.md`, 용어는 `CONTEXT.md`, 하네스 구성 논의는 `.scratch/harness/map.md`에 있다.

마지막 정리: 2026-11-09 (아래 '정리 기록')

## 1. 시스템이 하는 일

대표 한 사람이 매일 오전 10시에 시작하는 루틴으로 새 입찰공고, 지원사업 공고, 민간 외주 글, 시장 동향을 한 번에 받는다. 수집한 정보는 Google Sheet '수집 이력'에 쌓이고, 그날 처음 보는 항목은 **신규 알림 메일**로, 마감 전 입찰공고의 검토 상태는 **입찰 현황판**(artifact)으로 본다(D28·D30). 마감이 지난 행은 시트에서 매일 자동으로 빠진다(D29). 대표가 공고 하나를 고르면 참가자격과 시연 필요 여부를 근거와 함께 검토하고, 필요하면 1차 시연 데모를 만든다.

원칙: **수집·중복 제거·필터·판정 규칙은 결정적인 코드가 맡고, 문서를 읽고 추출하는 일만 Claude가 맡는다.** Claude 단계가 실패해도 목록은 도착한다.

## 2. 폴더 지도 (2026-11-09 기준)

```
07_Implementation/
├── CLAUDE.md              에이전트가 처음 읽는 목차
├── ARCHITECTURE.md        이 문서
├── CONTEXT.md             용어집 (수집 이력, 지난 공고, 신규 알림 메일, 입찰 현황판)
├── ROUTINE.md             매일 10:00 예약 작업에 붙여 넣는 지침 (D28~D30 반영 전, §7)
├── DEMO.md                공고 1건 검토 → 1차 시연 데모 대화형 절차
├── .env / .env.example    인증키 (루트 한 곳, 코드만 읽는다)
├── docs/
│   ├── decisions.md       결정 D1~D30, 요구사항 IM-01~09, 열린 리스크·질문 (구현 PRD에서 옮김)
│   ├── result-format.md   gov-agent → daily-report 결과 파일 계약 (format_version 1)
│   └── agents/            이슈 트래커·라벨·도메인 문서 규칙
├── .scratch/              명세와 이슈 (로컬 이슈 트래커)
│   ├── gov-agent/spec.md
│   ├── daily-report/spec.md
│   ├── ai-draft-pipeline/spec.md
│   ├── market-agent/issues/01~04
│   └── harness/           map.md(하네스 결정 H1~H16), spec.md(하네스 명세)
├── gov-agent/             정부사업 에이전트 (파이썬, 표준 라이브러리만)
│   ├── gov_agent/         cli, runner, sources/(S1·S3·S4·S5), filters, settings, eligibility, demo_brief, converter
│   ├── settings/          설정 4종: bid-filter, grant-criteria, company-profile, demo-criteria
│   ├── docs/              eligibility-input, demo-brief-input (Claude가 쓰는 JSON 입력 형식)
│   └── tests/             경계 A(수집)·경계 B(검토) 시험
├── daily-report/          결과 파일을 합쳐 보고서 HTML과 실행 기록을 만든다
├── market-agent/          유튜브 후보 수집(collect.py, keywords.json, data/)
├── demo-sample/           리허설용 가상 공고 R26BK999와 추출 예시
└── drafts/<공고번호>/      공고별 검토·데모 산출물 (현재 R26BK999 리허설 결과만)
```

실행 중에 생기는 폴더: `results/`(결과 JSON), `reports/`(보고서 HTML), `runs/runs.jsonl`(실행 기록), `gov-agent/state/`(증분 상태·직전 정상 설정). **2026-11-09 현재 네 폴더 모두 없다.** 루틴을 실제로 돌린 적이 없고, 시험은 가짜 응답으로만 했다.

## 3. 실행 흐름

### 3-1. 매일 10:00 무인 루틴 (IM-01~06, D5)

목표 흐름(D28~D30). 표시가 없는 단계는 구현되어 있다.

```
Cowork 예약 작업 (대표 PC, 폴더 연결, 10:00)
  │
  ├─ gov-agent run ──▶ results/gov_<날짜>.json        S1·S3·S4·S5 수집 → 필터 → 병합
  │     읽음: gov-agent/settings/*.md, gov-agent/state/(증분 상태 seen), .env
  │     노출 기록 results/shown_*.json 읽기와 로컬 원장                        [미구현, IM-09]
  │
  ├─ 시트 동기화 ──▶ Apps Script 웹 앱 ──▶ '수집 이력' 행 추가·갱신       [미구현, D14·D19]
  │     마감 지난 행은 보내지 않음(D29). '대표 메모' 열은 건드리지 않음
  │
  ├─ 신규 알림 메일 ──▶ 대표 이메일 (입찰공고·지원사업·외주 글 절, 현황판 링크) [미구현, D30]
  │
  ├─ 입찰 현황판 ──▶ 시트 읽기 → HTML → artifact 같은 주소에 재게시          [미구현, D28]
  │     마감 전 입찰공고를 상태별로, 검토 중을 맨 위. capabilities 선언 없음
  │
  └─ 기록 ──▶ runs/runs.jsonl(전달 결과), shown_<날짜>.json(노출 기록)        [노출 기록 미구현, IM-09]
```

현행 코드는 `daily-report build`가 결과 파일로 보고서 HTML 한 장(`reports/report-<날짜>.html`)을 만들고, `ROUTINE.md`가 그 HTML을 artifact로 게시한다. 목표 흐름에서 이 HTML의 역할은 신규 알림 메일과 입찰 현황판으로 나뉜다.

- 한 소스가 실패해도 결과 파일은 항상 써진다. 실패 사유는 `sources[].error.kind`(auth, pending_approval, rate_limit, network, format)에 남는다.
- 10:50(보고 마감)까지 끝나지 않는 단계는 기다리지 않는다(시간 상자는 예약 작업의 일). 11:00까지 전달에 성공한 날이 '도착'이다(D5, 코드 기본값 `daily_report/runs.py`의 `DEADLINE`).
- 대표 PC가 가장 확실하게 켜져 있는 시각이 오전 10시여서 루틴을 10:00에 시작한다(D5, 2026-11-09 정정).
- 루틴은 설정 파일을 고치지 않고, 제안 가능성 검토를 자동으로 하지 않는다.

### 3-2. 2차 검토 (D20·D21·D25, 미구현)

목표: 대표가 시트에서 '2차 검토 요청'을 체크하면 업무 시간 30분 간격 예약 작업이 이어서 처리하고 결과를 메일로 보낸다. 같은 작업이 상태 칸을 갱신하고 입찰 현황판을 다시 게시한다(D28). 시트 연결(D19)이 없어서, 지금은 `DEMO.md` 1~3단계를 대화로 실행한다.

```
첨부 읽기(D27) ─▶ Claude 추출 ─▶ drafts/<공고번호>/requirements.json
                                     └▶ drafts/<공고번호>/signals.json
gov-agent eligibility ─▶ eligibility.json   (회사 프로필 대조: 충족·미충족·확인필요)
gov-agent brief       ─▶ brief.json         (시연 판정: demo-criteria.md)
```

첨부 읽기 규칙(D27): hwp·hwpx는 kordoc 스킬, 그 밖의 파일(pdf, docx, pptx, xlsx 등)은 markitdown으로 읽는다. 읽지 못한 첨부는 이름과 링크를 '읽지 못함'으로 남긴다. 읽기는 Claude 세션이 하며, `gov_agent/converter.py`는 '읽지 못함' 처리 자리만 있다.

### 3-3. 1차 시연 데모 (D23, 대화형)

대표가 요청할 때만 `DEMO.md` 5단계로 Adobe for creativity 커넥터를 써서 만든다. 산출물은 `drafts/<공고번호>/prompt.md`, `outputs.md`다. 코드프레소 Claude 조직에서는 이 커넥터 추가가 막혀 있어 대표 계정에서만 실행한다(2026-11-09 확인).

### 3-4. 시트 정리 (D29, Apps Script 시간 트리거, 미구현)

대표 PC와 무관하게 Google 쪽에서 매일 한 번 돈다. 10:00 루틴보다 먼저 돌도록 새벽 시각에 둔다(시각은 구현 때 정함).

| 행 | 기준 | 처리 |
|---|---|---|
| 입찰공고·지원사업 | 마감일(접수 마감일)이 오늘보다 이전 | 검토 기록이 있으면 '지난 공고' 탭으로 옮기고, 없으면 지운다 |
| 마감일이 없는 행(CGLink 외주 글 등) | 등록일로부터 30일이 지남 | 위와 같음 |
| 마감일 당일 | | 남긴다 |

검토 기록이 있는 행: 상태가 '신규'가 아니거나 '대표 메모'가 비어 있지 않은 행. 로컬 원장과 `drafts/<공고번호>/`는 지우지 않는다.

### 3-5. 시장 정보 (market-agent)

`collect.py search`가 언어별 키워드로 이번 주 유튜브 후보를 `data/candidates_<날짜>.json`에 모으고, 관련도 판정·요약은 호출한 Claude가 한다. daily-report의 결과 파일 계약(`agent: "market"`)에는 아직 연결되지 않았다.

## 4. 의존 방향과 경계

```
settings/*.md ─┐
.env ──────────┼─▶ sources/(S1·S3·S4·S5) ─▶ filters ─▶ 병합·증분 상태(state/) ─▶ 결과 JSON ─▶ daily-report ─▶ 전달
state/ ────────┘                                                         (계약: docs/result-format.md)

첨부 텍스트 ─▶ Claude 추출(JSON, 근거 quote·location 필수) ─▶ eligibility / brief (코드 판정) ─▶ drafts/
```

- gov-agent와 daily-report는 서로 모른다. 둘 사이의 유일한 계약은 `docs/result-format.md`다. 형식을 바꾸면 `format_version`을 올린다.
- Claude가 쓰는 JSON 입력의 형식은 `gov-agent/docs/eligibility-input.md`, `demo-brief-input.md`가 정한다. 판정(충족 여부, 권고, 시연 필요)은 코드가 한다. 근거 문장이 없으면 확인필요(`needs_check`)다.
- 설정은 값 영역(`## 변경 이력` 앞의 표)만 코드가 읽는다. 수집용 설정 2종(bid-filter, grant-criteria)에 오류가 있으면 `state/last_good_settings/`로 실행한다. 회사 프로필 오류는 요건 추출만(`extract_only`), 시연 판정 기준 오류는 기본 단어로 처리한다.
- 시험 경계: 경계 A(설정 + 고정 응답 → 결과 JSON), 경계 B(추출 JSON + 프로필 → 요건별 분류), 경계 C(결과 파일 → 보고 HTML·실행 기록). 네트워크와 Claude 단계만 가짜로 바꾼다. 하네스 구축 때 루틴 전체 리허설과 훅 경계를 더한다(`.scratch/harness/spec.md`).

## 5. 정본 표

| 무엇 | 정본 | 사본·파생 |
|---|---|---|
| 결정·요구사항·리스크 | `docs/decisions.md` | 상위 PRD(`../05_PRD/`)는 고객 승인용 |
| 기능 명세 | `.scratch/<기능>/spec.md` | |
| 용어 | `CONTEXT.md` | |
| 설정 값과 변경 이력 | `gov-agent/settings/*.md` | `state/last_good_settings/`(수집용 2종만) |
| 보여 준 항목(노출 판정) | 로컬 원장 `gov-agent/state/`(IM-09) | Google Sheet '수집 이력'(D14, 마감 전 행만) |
| 공고별 처리 기록 | 시트 상태 칸·대표 메모 + `drafts/<공고번호>/`(D24) | 마감 뒤에는 '지난 공고' 탭(D29). Claude 세션은 기록이 아님 |
| 검토 상태 화면 | 시트 '수집 이력' | 입찰 현황판 artifact(D28, 최대 30분 늦음) |
| 실행·도착 기록 | `runs/runs.jsonl` | |
| 인증키·시트 비밀값 | `.env` | 어디에도 쓰지 않음 |
| 대표 메일 주소 | Apps Script 스크립트 속성(D30) | 문서·코드에 적지 않음 |

## 6. 외부 수집원과 실행 환경

| # | 수집원 | 접근 | 확인 상태 |
|---|---|---|---|
| S1 | 입찰공고정보서비스(15129394) `apis.data.go.kr/1230000/ad/BidPublicInfoService02` | data.go.kr 인증키 | 오퍼레이션명·부분 일치·한도 미확인 |
| S3 | 한콘진 지원사업공고(15134251) | 요청 주소 미확인, `KOCCA_API_URL` | 주소·파라미터·한도 미확인 |
| S4 | 중소기업 지원사업 공고(15157820) `apis.data.go.kr/1421000/bizinfo` | data.go.kr 인증키 | 증분 파라미터 가정, 한도 미확인 |
| S5 | CGLink 외주발주 RSS `cglink.com/jobsOffer/rss` | 인증 없음 | 2026-11-09 실제 RSS로 형식 확인, 약관 미확인 |

낙찰정보(S2)와 사전규격은 수집하지 않는다(D1, D15). 공공데이터포털 3종의 응답 필드 이름은 모두 가정이며, 가정 목록은 `gov-agent/README.md`에 있다.

실행 환경(Cowork) 전제:

- 폴더를 연결한 예약 작업은 대표 PC에서 로컬로만 실행된다. 대표 PC가 켜져 있고 Claude 데스크톱이 실행 중이어야 한다(Cowork 문서, 2026-11-04 확인).
- 예약 작업의 각 실행은 별도 세션이며, 일반 Cowork 작업처럼 연결된 도구·스킬·설치된 플러그인을 쓴다(Cowork 문서).
- 플러그인의 훅과 서브에이전트는 Cowork와 Claude Code에서 실행된다(지원 문서 13837440, 2026-11-09 확인). `bin/` 디렉터리가 있는 플러그인은 Cowork가 설치하지 않는다(Claude Code 플러그인 문서).
- 첨부 읽기 도구(D27): kordoc 스킬(플러그인)과 markitdown(파이썬 패키지)이 대표 PC에 있어야 한다. 코드프레소 PC에는 markitdown 0.1.7과 pdf·docx·pptx·xlsx 변환 패키지가 있다(2026-11-09 확인). 대표 PC는 확인 전이다.
- 확인하지 못한 것: `apis.data.go.kr` 송신 허용, `.env`가 모델 컨텍스트에 노출되지 않는지, 무인 실행 중 권한 확인 창, 놓친 실행의 처리, 예약 작업에서 플러그인 훅이 도는지, 개인 계정의 비공개 GitHub 마켓플레이스 지원.

## 7. 알려진 어긋남 (고칠 대상)

| 문서 | 어긋난 내용 | 기준 |
|---|---|---|
| `ROUTINE.md` 2~3단계와 상태 줄 | 보고서 HTML을 artifact로 게시. 시트 동기화·신규 알림 메일·입찰 현황판 단계가 없음. 상태 줄이 2026-11-05 기준 | D28~D30. 하네스의 daily-routine 스킬로 대체 예정(H8) |
| `CLAUDE.md` 머리말과 폴더 구조, `daily-report/README.md` | 통합 보고서를 artifact로 게시 | D28~D30 |
| `.scratch/daily-report/spec.md` 본문 | 보고서 한 장을 artifact로 게시 | 맨 위 변경 상자(D28~D30)가 우선 |

## 8. 목표 구조: 하네스 (결정 H1~H16, 2026-11-09)

결정 내용은 `.scratch/harness/map.md`에 있고, 아직 만들지 않았다. 이 절은 목표이며 현재 상태가 아니다.

- 대상: 운영(대표 PC의 루틴·2차 검토·데모)과 개발(코드 작성 에이전트) 둘 다(H1).
- 형태: Claude 플러그인. 파이썬 코드도 플러그인 `scripts/`로 옮기고(H5), 대표 계정에는 비공개 GitHub 저장소 마켓플레이스로 설치한다(H6). 플러그인은 `CLAUDE.md`와 rules를 실을 수 없으므로 불변 규칙은 세션 시작 훅이 넣는다(H2).
- 저장소: `D:\98_MyCode` 아래 새 저장소(H12), 토스트 명의 GitHub 비공개 저장소에 코드프레소 협업자(H13). 이 문서와 `CLAUDE.md`, `CONTEXT.md`, `docs/`, `.scratch/`도 그 저장소로 옮긴다.
- 작업 폴더(`07_Implementation`)는 운영 데이터 폴더가 된다: `settings/`(루트로 옮김, H11), `.env`, `results/`, `reports/`, `runs/`, `state/`, `drafts/`.
- 대안: 비공개 마켓플레이스가 안 되면 플러그인 파일 업로드(H14), 예약 작업에서 플러그인 `scripts/`를 못 돌리면 코드는 작업 폴더로 되돌림(H15).
- 일정: 11/12 시연 전에는 PRD·Spec만 갱신하고, 구축은 11/13부터(H16).

```
<D:\98_MyCode\새 저장소>/             (이름 미정)
├── .claude-plugin/plugin.json
├── hooks/hooks.json                 세션 시작 불변 규칙 주입, 설정 수정 시 변경 이력 검사 (H7)
├── rules/invariants.md
├── skills/                          daily-routine, review-requests, make-demo, change-setting, garden (H8)
├── agents/                          추출 에이전트 1개 (인용 대조는 코드, H9)
├── scripts/                         gov_agent, daily_report, market collect, 시험 (H5)
└── evals/ 또는 tests/                통합 시험 실행기, 결과 계약 시험, 가짜 응답 리허설, 플러그인 구조 검사 (H10)
```

## 9. 정리 기록

**2026-11-09** (sera.shin 요청): 낡은 자료 8개를 지웠다. 저장소가 git이 아니므로 영구 삭제 대신 Windows 휴지통으로 보냈다.

| 지운 파일 | 남은 내용이 간 곳 |
|---|---|
| `PRD_토스트애니메이션스튜디오_API직접연동Artifact_V261104.md` (구현 PRD 1.3) | `docs/decisions.md`(D·IM·R·Q 번호 유지), 수집원 표는 이 문서 §6 |
| `리서치_Cowork루틴_API호출가능성_V261104.md` | 이 문서 §6 실행 환경 전제 |
| `리서치_위젯설정변경_가능성_V261105.md` | 없음(D16으로 artifact 위젯을 쓰지 않음) |
| `리서치_회사프로필_토스트애니메이션스튜디오_V261105.md` | 값은 `gov-agent/settings/company-profile.md`의 출처 칸 |
| `리서치_검토대상필터항목_토스트애니메이션스튜디오_V261109.md` | 값은 `bid-filter.md`, `grant-criteria.md` |
| `요청양식_대표자료_V261104.md`, `요청양식_대표자료_V261109.md`, `요청양식_Adobe시연자료_V261109.md` | 대표 확인 대기 항목은 `docs/decisions.md` 열린 질문 |

지운 파일을 가리키던 곳(`CLAUDE.md`, `DEMO.md`, 설정 3종의 머리말, `.scratch`의 두 문서)은 함께 고쳤다.

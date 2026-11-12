# 아키텍처: 토스트 에이전트

이 문서는 `toast-agent` 저장소와 대표 PC 작업 폴더의 지도다. 무엇이 어디에 있고, 무엇이 무엇에 기대며, 어느 파일이 정본인지를 적는다. 결정의 이유는 `docs/decisions.md`(D)와 `.scratch/harness/map.md`(H), 용어는 `CONTEXT.md`에 있다. 실행 절차의 정본은 각 스킬 본문이며, 이 문서는 절차를 다시 적지 않는다.

마지막 정리: 2026-11-11 (아래 '정리 기록')

## 1. 시스템이 하는 일

토스트 에이전트는 Claude 플러그인 `toast-agent`이고, 안에 정부사업 에이전트(gov-agent)와 시장 정보 에이전트(market-agent, 미연결)가 있다(H17). 매일 오전 10시 루틴이 새 입찰공고, 지원사업 공고, 민간 외주 글을 모아 1차 필터링하고, Google Sheet '수집 이력'에 쌓은 뒤, 그날 처음 보는 항목을 **신규 알림 메일**로 보내고 마감 전 입찰공고의 상태를 **사업 현황판**(artifact)으로 다시 게시한다(D28·D30). 마감이 지난 행은 시트에서 매일 자동으로 빠진다(D29). 대표가 시트에서 '2차 검토 요청'을 고르면 30분 간격 루틴이 참가자격과 시연 필요 여부를 근거와 함께 검토하고(2차 검토), 대표가 요청하면 1차 시연 데모를 만든다.

원칙: **수집·중복 제거·필터·판정 규칙은 결정적인 코드가 맡고, 문서를 읽고 추출하는 일만 Claude가 맡는다.** Claude 단계가 실패해도 목록은 도착한다.

## 2. 지도

### 2-1. 저장소 (`D:\98_MyCode\toast-agent`, GitHub `serashin-tech/toast-agent` 비공개)

```
toast-agent/                          저장소 루트 = 마켓플레이스 `toast-agent`
├── .claude-plugin/marketplace.json
├── CLAUDE.md                         저장소를 고치는 사람의 목차
├── ARCHITECTURE.md                   이 문서
├── CONTEXT.md                        용어집
├── README.md                         설치 절차(대표 PC)
├── .env.example                      작업 폴더 .env의 항목
├── apps-script/                      시트에 붙이는 Code.gs와 설치·확인 절차
├── installer/                        대표 PC 설치: install.bat(작업 폴더·.env 생성), README_install.md, settings/(초기값, D37)
├── docs/
│   ├── decisions.md                  결정 D1~D37, 요구사항 IM, 리스크 R, 질문 Q
│   ├── result-format.md              gov-agent → daily-report 결과 파일 계약
│   ├── adr/0001~0003                 되돌리기 어려운 결정
│   ├── agents/                       이슈 트래커·라벨·도메인 문서 규칙
│   └── manual/                       대표용 설명서(artifact 정본, H18)
├── .scratch/<기능>/                  명세(spec.md)와 티켓(issues/NN-*.md)
└── plugin/                           플러그인 `toast-agent`
    ├── .claude-plugin/plugin.json    버전(대표에게 내보낼 때 올림)
    ├── rules/invariants.md           불변 규칙 원본
    ├── hooks/                        세션 시작 때 불변 규칙 주입, 설정 파일 변경 이력 검사(H7)
    ├── skills/                       daily-routine, review-requests, make-demo, change-setting, garden(H8)
    ├── agents/requirement-extractor.md  2차 검토의 요건·시연 신호 추출(H9)
    ├── scripts/
    │   ├── gov.py, report.py         진입점(gov-agent, daily-report)
    │   ├── gov-agent/                수집·필터·원장·판정(파이썬 표준 라이브러리), docs/에 추출 JSON 형식
    │   ├── daily-report/             메일·현황판·시트 연동·실행 기록·잠금
    │   ├── market-agent/             유튜브 후보 수집(collect.py, 미연결)
    │   ├── settings-template/        설정 4종의 첫 값
    │   ├── fixtures/demo-sample/     리허설용 가상 공고 R26BK999
    │   ├── rehearse.py               가짜 응답 전체 리허설
    │   └── run_tests.py              통합 시험 실행기
    └── tests/                        훅, 결과 계약, 리허설, 플러그인 구조 시험
```

### 2-2. 작업 폴더 (대표 PC, Cowork에 연결)

```
<작업 폴더>/                          코드는 이 폴더를 현재 폴더로 보고 경로를 정한다
├── settings/                         설정 4종: bid-filter, grant-criteria, company-profile, demo-criteria(H11)
├── .env                              인증키·시트 웹 앱 주소·토큰(코드만 읽음)
├── state/                            로컬 원장(ledger.json), 증분 상태, last_good_settings/
├── results/                          gov_<날짜>.json(결과), shown_<날짜>.json(노출 기록)
├── reports/                          메일 본문, 현황판 HTML, 시트 스냅샷
├── runs/                             runs.jsonl(실행 기록), routine.lock(잠금)
└── drafts/<공고번호>/                 첨부, 텍스트, 추출 JSON, eligibility·brief, 데모 산출물
```

`settings/`와 `.env`는 `installer/install.bat`이 만들고(D37), 나머지는 첫 실행 때 코드가 만든다. 운영 데이터는 저장소에 넣지 않는다. 예외인 `installer/settings/`는 설치 때만 쓰는 초기값이며, 설치 뒤 정본은 작업 폴더의 `settings/`다. 고객 폴더 `07_Implementation`은 11/12 시연 뒤 이 구조로 정리한다(H16-1).

## 3. 실행 흐름

| 흐름 | 언제 | 정본 절차 | 요약 |
|---|---|---|---|
| 매일 루틴 | 평일 10:00 예약 작업 | `daily-routine` 스킬 | 잠금 → 시트 상태 받기 → 수집·1차 필터링·관련도 요약 → 시트 기록 → 신규 알림 메일 → 실행 기록 → 현황판 재게시 → 잠금 해제 |
| 2차 검토 | 09~18시 30분마다(10:00~10:50 제외) | `review-requests` 스킬 | '2차 검토 요청' 행 → 첨부 읽기 → 추출 에이전트 → eligibility·brief(코드 판정, 인용 대조) → 상태 갱신 → 결과 메일 → 현황판 재게시 |
| 1차 시연 데모 | 대표가 요청할 때(대화) | `make-demo` 스킬 | brief 확인 → 커넥터 지시문 → Adobe for creativity로 생성 → 산출물 기록 → '데모 완료'(대표 계정에서만) |
| 설정 변경 | 대표·관리자가 말로 요청 | `change-setting` 스킬 | 전후 표시 → 확인 → 파일 전체 다시 쓰기 + 변경 이력 한 줄(D11) |
| 주간 점검 | 월요일 또는 요청 | `garden` 스킬 | 도착률, 실패 소스, 설정 대체 실행, 노출 기록 빈 날, 오래된 가정 보고(고치지 않음) |
| 시트 정리 | 매일 06:00(Apps Script 트리거) | `apps-script/Code.gs` | 아래 표 |

- 시간: 10:00 시작, 10:50까지 끝나지 않는 단계는 기다리지 않음, 11:00까지 메일 발송에 성공한 날이 '도착'(D5, D31). PC가 꺼져 있던 날은 '미실행'으로 센다.
- 한 소스가 실패해도 결과 파일은 항상 써진다. 실패 사유는 `sources[].error.kind`(auth, pending_approval, rate_limit, network, format)에 남는다.
- 첨부 읽기(D27): hwp·hwpx는 kordoc 스킬, 그 밖의 파일은 markitdown. 읽지 못한 첨부는 이름과 링크를 남긴다.
- 무인 루틴은 설정 파일을 고치지 않는다(불변 규칙 3).

시트 정리 기준(D29):

| 행 | 기준 | 처리 |
|---|---|---|
| 입찰공고·지원사업 | 마감일이 오늘보다 이전 | 검토 기록이 있으면 '지난 공고' 탭으로 옮기고, 없으면 지운다 |
| 마감일이 없는 행(CGLink 외주 글 등) | 등록일로부터 30일이 지남 | 위와 같음 |

검토 기록이 있는 행은 상태가 '신규'가 아니거나 '대표 메모'가 비어 있지 않은 행이다. 로컬 원장과 `drafts/`는 지우지 않는다.

## 4. 의존 방향과 경계

```
settings/*.md ─┐
.env ──────────┼─▶ sources(S1·S3·S4·S5) ─▶ filters ─▶ 병합·원장(state/) ─▶ 결과 JSON ─▶ daily-report ─▶ 시트·메일·현황판
state/ ────────┘                                              (계약: docs/result-format.md)

첨부 텍스트 ─▶ 추출 에이전트(JSON, 근거 quote·location 필수) ─▶ eligibility / brief(코드 판정, 인용 대조) ─▶ drafts/
```

- gov-agent와 daily-report는 서로 모른다. 둘 사이의 유일한 계약은 `docs/result-format.md`다. 형식을 바꾸면 `format_version`을 올린다.
- Claude가 쓰는 JSON 입력 형식은 `plugin/scripts/gov-agent/docs/`의 두 문서가 정한다. 판정(충족 여부, 권고, 시연 필요)은 코드가 하며, 근거 문장이 없거나 원문에서 찾지 못한 인용은 확인필요(`needs_check`)다.
- 설정은 값 영역(`## 변경 이력` 앞의 표)만 코드가 읽는다. 수집용 2종에 오류가 있으면 `state/last_good_settings/`로 실행하고, 회사 프로필 오류는 요건 추출만, 시연 판정 기준 오류는 기본 단어로 처리한다.
- 스킬·에이전트는 코드를 `${CLAUDE_PLUGIN_ROOT}/scripts/`로 부르고, 코드는 작업 폴더 기준 상대 경로를 쓴다.
- 시험 경계: 수집(설정 + 고정 응답 → 결과 JSON), 검토(추출 JSON + 프로필 → 판정), 보고(결과 파일 → 메일·현황판·실행 기록), 루틴 전체 리허설, 훅, 플러그인 구조. 네트워크와 Claude 단계만 가짜로 바꾼다.

## 5. 정본 표

| 무엇 | 정본 | 사본·파생 |
|---|---|---|
| 결정·요구사항·리스크 | `docs/decisions.md`, 하네스는 `.scratch/harness/map.md` | 상위 PRD(고객 폴더 `05_PRD/`)는 고객 승인용 |
| 기능 명세 | `.scratch/<기능>/spec.md` | |
| 운영 절차 | `plugin/skills/*/SKILL.md` | 대표용 설명서 `plugin/scripts/daily-report/daily_report/manual.html`(사업 현황판 탭 포함) |
| 불변 규칙 | `plugin/rules/invariants.md` | 세션 시작 훅이 대화에 넣음 |
| 용어 | `CONTEXT.md` | |
| 설정 값과 변경 이력 | 작업 폴더 `settings/*.md` | `state/last_good_settings/`(수집용 2종), 설명서의 관리자 설정 탭(게시 시점 스냅샷), `installer/settings/`(설치 초기값, D37) |
| 보여 준 항목(노출 판정) | 로컬 원장 `state/` | 시트 '수집 이력'(마감 전 행만) |
| 공고별 처리 기록 | 시트 상태 칸·대표 메모 + `drafts/<공고번호>/`(D24) | 마감 뒤에는 '지난 공고' 탭(D29). Claude 세션은 기록이 아님 |
| 검토 상태 화면 | 시트 '수집 이력' | 사업 현황판 artifact(최대 30분 늦음) |
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

낙찰정보(S2)와 사전규격은 수집하지 않는다(D1, D15). 공공데이터포털 3종의 응답 필드 이름은 모두 가정이며, 가정 목록은 `plugin/scripts/gov-agent/README.md`에 있다.

실행 환경(Cowork) 전제:

- 폴더를 연결한 예약 작업은 대표 PC에서 로컬로만 실행된다. 대표 PC가 켜져 있고 Claude 데스크톱이 실행 중이어야 한다.
- 예약 작업의 각 실행은 별도 세션이며, 설치된 플러그인의 스킬·훅·에이전트를 쓴다. `bin/` 디렉터리가 있는 플러그인은 Cowork가 설치하지 않는다.
- 첨부 읽기 도구: kordoc 스킬과 markitdown이 대표 PC에 있어야 한다(대표 PC는 확인 전).

## 7. 확인하지 못한 것

| 무엇 | 확인할 곳 |
|---|---|
| 개인 계정 Cowork가 비공개 저장소 마켓플레이스를 받는지, 예약 작업에서 플러그인 `scripts/`의 파이썬과 훅이 도는지, 무인 실행 중 권한 확인 창, 현황판 재게시 승인 창 | 티켓 05(H14·H15 대안 포함) |
| `apis.data.go.kr` 송신 허용, 공공데이터포털 실제 응답 | 티켓 05, `gov-agent/README.md` 가정 목록 |
| Apps Script 실제 설치, 메일 발송, 정리 트리거 | 티켓 09·10·12, `apps-script/README.md` 확인 절차 |
| Adobe 커넥터 도구 이름과 결과 저장 방식 | 티켓 16 확인 기록 |
| market-agent를 결과 파일 계약에 연결할지 | PRD Q9 |

## 8. 정리 기록

**2026-11-11** (sera.shin 요청): 이 문서를 고객 폴더(`07_Implementation`) 기준에서 저장소 기준으로 다시 썼다. 저장소의 `ROUTINE.md`와 `DEMO.md`를 지웠다(git 기록에 남음). 둘 다 11/10에 고객 폴더에서 복사해 온 사본이고, 절차는 daily-routine·make-demo 스킬이 대체했다.

| 지운 파일 | 남은 내용이 간 곳 |
|---|---|
| `ROUTINE.md` | 절차는 `daily-routine` 스킬. 처음 설정(지금 실행으로 권한 허용, 휴대폰 확인, 절전 방지)은 `README.md` 설치 절. 놓친 실행은 코드가 '미실행'으로 셈 |
| `DEMO.md` | 1~3단계는 `review-requests` 스킬과 추출 에이전트, 4~5단계는 `make-demo` 스킬. 커넥터 연결과 리허설은 `make-demo`, 확인 기록은 하네스 티켓 16 |

고객 폴더의 `ROUTINE.md`·`DEMO.md`·`ARCHITECTURE.md`는 그대로 있다. `ROUTINE.md`는 예약 작업을 스킬로 바꾼 뒤 지우고(티켓 08), `DEMO.md`는 Agent 평가 계획(`.scratch/agent-eval/plan.md`)이 평가 대상 지침으로 쓰므로 평가 담당자와 협의한 뒤 지운다.

**2026-11-09** (sera.shin 요청): 고객 폴더의 낡은 자료 8개(구현 PRD 1.3, 리서치 4종, 요청양식 3종)를 지웠다. 남은 내용은 `docs/decisions.md`, 이 문서의 수집원 표, 설정 파일의 출처 칸, `docs/decisions.md` 열린 질문으로 옮겼다.

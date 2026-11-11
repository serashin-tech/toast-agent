# 결과 파일 계약 (format_version 1)

gov-agent가 쓰고 daily-report가 읽는 날짜별 JSON 파일의 형식이다. 두 폴더는 이 문서만 보고 서로 모르게 개발한다. 형식을 바꾸면 `format_version`을 올린다.

- 파일 이름: `<agent>_<YYYY-MM-DD>.json` (예: `gov_2026-11-11.json`). 파일 하나가 에이전트 하나의 하루치이다.
- 인코딩은 UTF-8, 날짜는 `YYYY-MM-DD`, 일시는 ISO 8601(+09:00)이다.
- 이 문서에 없는 필드는 읽는 쪽이 무시한다. 있어야 하는 필드가 없으면 읽는 쪽은 그 에이전트를 `format` 오류로 실패 처리한다.

## 최상위

| 필드 | 형식 | 설명 |
|---|---|---|
| `format_version` | 문자열 | `"1"` |
| `agent` | 문자열 | `"gov"` (이후 `"market"`) |
| `run_date` | 날짜 | 실행 기준일 |
| `generated_at` | 일시 | 파일을 쓴 시각 |
| `sources` | 배열 | 소스별 실행 상태(아래) |
| `items` | 배열 | 공통 항목(아래) |
| `eligibility` | 배열 | 제안 가능성 검토 결과(없으면 빈 배열) |
| `settings` | 객체 | 설정 사용 정보(아래) |
| `warnings` | 문자열 배열 | 결과에 영향을 준 문제(원장·노출 기록·시트 상태 파일을 읽지 못함 등). 없으면 빈 배열(2026-11-11 추가) |

## sources[]

| 필드 | 형식 | 설명 |
|---|---|---|
| `id` | 문자열 | `bid`(입찰공고), `grant_kocca`(한콘진), `grant_bizinfo`(중소기업 지원사업), `outsource_cglink`(CGLink 외주발주 게시판) |
| `label` | 문자열 | 화면에 보이는 이름 |
| `status` | 문자열 | `ok` 또는 `failed` 또는 `limit_near`(한도 임박으로 중단) |
| `fetched` | 정수 | API에서 받은 건수 |
| `included` | 정수 | 필터를 통과해 `items`에 들어간 건수 |
| `excluded` | 정수 | 필터에서 제외된 건수 |
| `new_count` | 정수 | `included` 중 아직 보여 주지 않은 건수. 재알림 항목(`renotify`)만큼 `included`보다 작을 수 있다(D13, D18) |
| `changed_shown_count` | 정수 | 이미 보여 준 항목 가운데 오늘 내용이 바뀐 건수. 이 항목은 `items`에 싣지 않는다(2026-11-10 추가, IM-09) |
| `error` | 객체 또는 null | 실패일 때 `{"kind": ..., "message": ...}`. `kind`는 `auth`, `pending_approval`, `rate_limit`, `network`, `format` 중 하나. `message`에는 인증키를 넣지 않는다 |
| `last_success_at` | 일시 또는 null | 이 소스가 마지막으로 성공한 시각 |

## items[] (공통 항목)

| 필드 | 형식 | 설명 |
|---|---|---|
| `source` | 문자열 | `sources[].id` 중 하나(지원사업은 병합된 한 건에 `grant`) |
| `kind` | 문자열 | `bid`, `grant`, `outsource` |
| `id` | 문자열 | 항목 식별자(공고번호, 지원사업 식별자, 외주 글 번호) |
| `title` | 문자열 | 제목 |
| `posted_on` | 날짜 또는 null | 등록일(공고일) |
| `deadline` | 날짜 또는 null | 마감일(지원사업은 접수 마감일, 외주 글은 null) |
| `url` | 문자열 | 원문 링크. 모든 항목에 있어야 하고 `http` 또는 `https`로 시작한다 |
| `matched_keywords` | 문자열 배열 | 필터를 통과시킨 포함 키워드. 필터 미설정이면 빈 배열 |
| `summary` | 문자열 또는 null | 에이전트가 쓴 한 줄 요약. 원문 인용이 아니다 |
| `is_new` | 불리언 | 메일에 실을 항목인지. 2026-11-10부터 gov가 싣는 항목은 늘 참이다(D13). 이미 보여 줬지만 다시 알리는 항목은 `renotify`로 구분한다. 옛 파일에는 거짓인 항목이 있을 수 있다 |
| `renotify` | 불리언, 없을 수 있음 | 이미 보여 줬지만 대표가 시트에서 검토를 요청한 뒤 내용이 바뀌어 다시 싣는 입찰공고에만 참으로 붙는다(D18, `run --sheet-rows`) |
| `keys` | 문자열 배열 | 로컬 원장 키(`소스:식별자`). 병합한 지원사업은 출처 키 둘을 모두 담는다. 노출 기록(`shown_<날짜>.json`)이 이 키를 쓴다(2026-11-10 추가, IM-09) |
| `extra` | 객체 | 종류별 고유 값(아래) |

### extra: `kind` = `bid`

| 필드 | 설명 |
|---|---|
| `agency` | 공고기관 |
| `demand_agency` | 수요기관(없으면 null) |
| `est_price` | 추정가격(정수 원, 없으면 null) |
| `attachments` | `[{"name": ..., "url": ...}]` |

### extra: `kind` = `grant`

| 필드 | 설명 |
|---|---|
| `agency` | 소관 또는 수행 기관 |
| `period_start` | 접수 시작일 또는 null |
| `period_end` | 접수 마감일 또는 null (`deadline`과 같은 값) |
| `dday` | 실행 기준일 대비 마감까지 남은 일수(마감이 지났으면 음수, 모르면 null) |
| `category` | 분류 또는 null |
| `target` | 지원 대상 또는 null |
| `contact` | 문의처(기관 문의처만, 개인 연락처 아님) 또는 null |
| `origins` | 출처 목록. 예: `["grant_bizinfo", "grant_kocca"]`. 대표 정보는 `grant_bizinfo`를 쓴다(D9) |

### extra: `kind` = `outsource`

| 필드 | 설명 |
|---|---|
| `poster` | 게시자 닉네임(없으면 null). 게시 글 본문과 연락처는 담지 않는다 |

`outsource` 항목의 `deadline`은 null, `matched_keywords`는 빈 배열이다.

## eligibility[] (제안 가능성 검토)

| 필드 | 설명 |
|---|---|
| `bid_id` | 검토한 공고번호(`items`의 bid `id`) |
| `overall` | `recommend`(참여 권고), `conditional`(조건부), `not_recommend`(비권고), `extract_only`(프로필 없이 요건만 추출) |
| `reason` | 종합 의견의 이유 |
| `disclaimer` | 최종 판단은 대표가 한다는 문구(항상 포함) |
| `unreadable_files` | 변환하지 못한 첨부 `[{"name": ..., "url": ...}]` |
| `requirements` | 요건 목록(아래) |

requirements[]: `category`(참가자격, 계약방식, 평가방식, 예산, 제출마감 등), `text`(요건 내용), `verdict`(`met`, `unmet`, `needs_check`, `extract_only`), `profile_item`(대조한 프로필 항목 또는 null), `evidence`(`{"quote": 공고문 근거 문장, "location": 위치}`)

## settings

| 필드 | 설명 |
|---|---|
| `fallback_used` | 설정 오류로 직전 정상 설정을 썼는지 |
| `fallback_reason` | 썼다면 이유(없으면 null) |
| `files` | 이번 실행에 읽은 설정 파일 이름 목록 |

## 구현에서 정한 규칙 (2026-11-05)

구현 중 계약에 비어 있던 부분을 다음과 같이 정했다.

- **낙찰 항목 삭제(2026-11-09)**: 낙찰 수집과 경쟁사 대조를 기능에서 뺐다(구현 PRD D15). 결과 파일에 `award` 소스와 항목이 더는 나오지 않는다. 항목 종류가 줄기만 한 변경이므로 `format_version`은 올리지 않았다.
- **지원사업의 `source`**: 두 소스가 병합된 사업은 `grant`, 한 소스에만 있는 사업은 그 소스 `id`(`grant_kocca` 또는 `grant_bizinfo`)이다. 읽는 쪽은 `kind`로 종류를 구분한다.
- **`limit_near`의 `error`**: `kind`는 `rate_limit`으로 채운다.
- **`keys`, `changed_shown_count` 추가와 `is_new` 뜻 변경(2026-11-10)**: 읽는 쪽은 모르는 필드를 무시하므로 `format_version`을 올리지 않았다. `is_new`의 뜻이 '오늘 처음 수집'에서 '아직 보여 주지 않음'으로 바뀌었다.
- **`warnings` 추가(2026-11-11, 최상위 문자열 배열)**: gov가 원장이나 노출 기록을 읽지 못하는 등 결과에 영향을 준 문제를 적는다. 신규 알림 메일 맨 위 '확인이 필요한 점'에 그대로 나온다. 없으면 빈 배열이다.
- **노출 기록 `shown_<날짜>.json`(2026-11-10)**: 결과 폴더에 `{"date": 날짜, "keys": [원장 키…]}`로 둔다. `daily_report record-publish --ok true --results <결과 폴더>`가 신규 알림 메일 발송에 성공한 날에만 쓰고(D31), gov는 다음 실행을 시작할 때 이 파일들로 원장의 첫 노출일을 채운다.
- **`outsource` 추가(2026-11-09)**: 읽는 쪽은 모르는 `kind`를 건너뛰므로 덧붙이기만 한 이 변경은 `format_version`을 올리지 않았다. 옛 daily-report는 이 항목을 보이지 않을 뿐 실패하지 않는다.
- **`eligibility`**: 수집 실행(`run`)은 빈 배열을 쓴다. 제안 가능성 검토는 별도 명령(`eligibility`)이 같은 계약의 항목을 만들고, 그 결과를 결과 파일에 합칠 때는 `eligibility --merge-into <결과 파일>`을 쓴다. 같은 공고번호의 항목은 바꾸고, 새 공고는 `eligibility` 배열에 더한다.

## 설정 md 형식

`gov-agent/settings/*.md`의 공통 형식이다. 값 영역은 `## 변경 이력` 절 앞에 있는 표이고, 코드는 이 영역만 읽는다. 변경 이력 절은 `일자 | 항목 | 변경 전 | 변경 후 | 사유 | 변경자` 열의 표이며 코드는 값으로 해석하지 않는다. daily-report는 변경 이력 표만 읽어 "최근 설정 변경"을 신규 알림 메일에 표시한다(D35).

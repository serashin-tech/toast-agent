---
name: daily-routine
description: 토스트 정부사업 에이전트의 매일 10:00 무인 루틴. 공고를 수집하고, 수집 이력 시트에 쌓고, 신규 알림 메일을 보내고, 입찰 현황판을 다시 게시하고, 실행 기록을 남긴다. Cowork 예약 작업(평일 10:00)이 부르거나 대표가 "오늘 루틴 다시 돌려 줘"라고 할 때 쓴다.
---

작업 폴더(Cowork에 연결한 폴더)에서 아래 순서대로 실행한다. 오늘 날짜(한국 시간, YYYY-MM-DD)를 TODAY라고 부른다. 한 단계가 실패해도 다음 단계로 이어 가고, **10:50까지 끝나지 않는 단계는 기다리지 않는다**(D5). 명령 앞부분은 `python -X utf8 "${CLAUDE_PLUGIN_ROOT}/scripts/gov.py"`(GOV), `python -X utf8 "${CLAUDE_PLUGIN_ROOT}/scripts/report.py"`(REPORT)로 줄여 적는다.

0. 잠금: `REPORT lock acquire --runs runs --owner daily`. 검토 루틴이 잡고 있으면(종료 코드 1) 1분 간격으로 다시 시도하되 10:20이 지나면 잠금 없이 이어 간다. 끝(7번)에서 `REPORT lock release --runs runs --owner daily`를 꼭 실행한다.
1. 수집
   - 먼저 시트 상태를 받는다: `REPORT sheet-pull --out reports/sheet-before-TODAY.json`. 실패해도 이어 간다.
   - `GOV run --date TODAY --out results --sheet-rows reports/sheet-before-TODAY.json` (시트를 못 받았으면 `--sheet-rows`를 뺀다). 검토를 요청한 입찰공고의 내용이 바뀌었으면 다시 실린다(D18).
   - 인증키는 코드가 `.env`에서 읽는다. `.env`를 열거나 출력하지 않는다.
   - 관련도 한 줄 요약(D33): `results/gov_TODAY.json`의 입찰공고(kind가 bid)마다 제목과 기관을 `settings/company-profile.md`의 주요 사업 분야·수행 실적과 견주어 "왜 볼 만한지(또는 아닌지)"를 한 줄(120자 안)로 쓴다. 근거가 없는 평가나 낙찰 가능성은 쓰지 않는다. `{"공고번호": "요약"}` 모양으로 `reports/summaries-TODAY.json`에 쓰고 `GOV summarize --result results/gov_TODAY.json --input reports/summaries-TODAY.json`을 실행한다. 실패하면 요약 없이 이어 간다.
2. 실행 기록 시작: `REPORT build --date TODAY --results results --out reports --settings settings --runs runs`
3. 시트 기록: `REPORT sheet-push --date TODAY --state state` (로컬 원장의 마감 전 행 전체를 보내므로, 어제 실패한 행도 오늘 다시 들어간다). 종료 코드로 `REPORT record-step --runs runs --date TODAY --step sheet --ok true|false`를 남긴다.
4. 신규 알림 메일
   - `reports/artifact-url.txt`가 있으면 그 주소를 BOARD로 쓴다.
   - `REPORT mail --date TODAY --results results --out reports/mail-TODAY.json --board-url BOARD`
   - `REPORT send-mail --mail reports/mail-TODAY.json` 의 종료 코드로 성공 여부를 정한다. 지금 한국 시각(ISO 8601)을 AT라고 부른다.
5. 실행 기록 마감: `REPORT record-publish --runs runs --date TODAY --at AT --ok true|false --results results`
   - 메일 발송에 성공했을 때만 `--ok true`다. 성공한 날에만 노출 기록이 남고, 11시 도착은 이것으로 센다(D31).
6. 입찰 현황판
   - `REPORT sheet-pull --out reports/sheet-TODAY.json` 후 `REPORT board --date TODAY --sheet reports/sheet-TODAY.json --out reports/board.html`
   - Artifact 도구로 `reports/board.html`을 게시한다. **capabilities는 선언하지 않는다.** `reports/artifact-url.txt`가 있으면 그 주소를 url로 넘겨 같은 주소에 다시 게시하고, 없으면 새로 게시한 뒤(icon은 board) 받은 주소를 그 파일에 한 줄로 저장한다.
   - 게시 결과를 `REPORT record-step --runs runs --date TODAY --step board --ok true|false`로 남긴다. 현황판 결과는 11시 도착 판정에 쓰지 않는다(D31).
7. 끝. 한 줄로 보고한다: 성공한 소스와 실패한 소스(사유 종류), 시트 기록, 메일 발송, 현황판 게시 결과.

하지 않는 일: `settings/`를 고치지 않는다(읽기만 한다). 2차 검토와 데모는 이 루틴에서 하지 않는다.

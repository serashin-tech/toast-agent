---
name: daily-routine
description: 토스트 정부사업 에이전트의 매일 10:00 무인 루틴. 공고를 수집하고, 수집 이력 시트에 쌓고, 신규 알림 메일을 보내고, 입찰 현황판을 다시 게시하고, 실행 기록을 남긴다. Cowork 예약 작업(평일 10:00)이 부르거나 대표가 "오늘 루틴 다시 돌려 줘"라고 할 때 쓴다.
---

작업 폴더(Cowork에 연결한 폴더)에서 아래 순서대로 실행한다. 오늘 날짜(한국 시간, YYYY-MM-DD)를 TODAY라고 부른다. 한 단계가 실패해도 다음 단계로 이어 가고, **10:50까지 끝나지 않는 단계는 기다리지 않는다**(D5). 명령 앞부분은 `python -X utf8 "${CLAUDE_PLUGIN_ROOT}/scripts/gov.py"`(GOV), `python -X utf8 "${CLAUDE_PLUGIN_ROOT}/scripts/report.py"`(REPORT)로 줄여 적는다.

1. 수집: `GOV run --date TODAY --out results`
   - 인증키는 코드가 `.env`에서 읽는다. `.env`를 열거나 출력하지 않는다.
2. 실행 기록 시작: `REPORT build --date TODAY --results results --out reports --settings settings --runs runs`
3. 시트 기록: `REPORT sheet-push --date TODAY --results results`
4. 신규 알림 메일
   - `reports/artifact-url.txt`가 있으면 그 주소를 BOARD로 쓴다.
   - `REPORT mail --date TODAY --results results --out reports/mail-TODAY.json --board-url BOARD`
   - `REPORT send-mail --mail reports/mail-TODAY.json` 의 종료 코드로 성공 여부를 정한다. 지금 한국 시각(ISO 8601)을 AT라고 부른다.
5. 실행 기록 마감: `REPORT record-publish --runs runs --date TODAY --at AT --ok true|false --results results`
   - 메일 발송에 성공했을 때만 `--ok true`다. 성공한 날에만 노출 기록이 남고, 11시 도착은 이것으로 센다(D31).
6. 입찰 현황판
   - `REPORT sheet-pull --out reports/sheet-TODAY.json` 후 `REPORT board --date TODAY --sheet reports/sheet-TODAY.json --out reports/board.html`
   - Artifact 도구로 `reports/board.html`을 게시한다. **capabilities는 선언하지 않는다.** `reports/artifact-url.txt`가 있으면 그 주소를 url로 넘겨 같은 주소에 다시 게시하고, 없으면 새로 게시한 뒤(icon은 board) 받은 주소를 그 파일에 한 줄로 저장한다.
7. 끝. 한 줄로 보고한다: 성공한 소스와 실패한 소스(사유 종류), 시트 기록, 메일 발송, 현황판 게시 결과.

하지 않는 일: `settings/`를 고치지 않는다. 2차 검토와 데모는 이 루틴에서 하지 않는다. 관련도 한 줄 요약(D33)은 아직 코드가 없어 건너뛴다(티켓 18).

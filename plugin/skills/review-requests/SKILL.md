---
name: review-requests
description: 수집 이력 시트에서 상태가 '2차 검토 요청'인 입찰공고를 찾아 참가자격 대조와 시연 판정(2차 검토)을 하고, 결과를 메일로 보내고 사업 현황판을 다시 게시한다. Cowork 예약 작업(09~18시, 30분 간격)이 부르거나 대표가 "검토 요청 처리"라고 할 때 쓴다.
---

작업 폴더에서 실행한다. GOV, REPORT는 daily-routine 스킬과 같은 명령이다(`${CLAUDE_PLUGIN_ROOT}/scripts/gov.py`, `${CLAUDE_PLUGIN_ROOT}/scripts/report.py`).

## 먼저 확인

- 지금 한국 시각이 10:00~10:50이면 아무것도 하지 않고 끝낸다(10:00 루틴과 겹치지 않게 한다).
- `REPORT lock acquire --runs runs --owner review`가 1을 돌려주면(다른 루틴 실행 중) 아무것도 하지 않고 끝낸다. 잡았으면 끝날 때(실패해도) `REPORT lock release --runs runs --owner review`를 실행한다. 잠금 파일은 daily 루틴과 같은 `runs/routine.lock` 하나이며, 60분이 지난 잠금은 코드가 넘겨받는다.

## 순서

1. `REPORT sheet-pull --out reports/sheet-now.json`. 행 가운데 `status`가 '2차 검토 요청'이고 `kind`가 bid인 것만 고른다(D21, D32). 없으면 잠금을 풀고 끝낸다.
2. 공고마다(키 KEY, 공고번호 ID):
   1. `REPORT sheet-status --key KEY --status "2차 검토 중"`
   2. `results/gov_*.json`에서 같은 키(`keys`)를 가진 항목을 찾아 첨부 목록(`extra.attachments`)을 얻는다.
   3. 첨부를 `drafts/ID/attachments/`에 내려받고 텍스트로 바꿔 `drafts/ID/text/`에 둔다. hwp·hwpx는 kordoc 스킬, 그 밖은 markitdown으로 읽는다(D27). 읽지 못한 첨부는 이름과 링크를 남긴다.
   4. requirement-extractor 에이전트에게 공고번호, 작업 폴더, `drafts/ID/text/`, 읽지 못한 첨부를 넘겨 `requirements.json`과 `signals.json`을 받는다.
   5. `GOV eligibility --input drafts/ID/requirements.json --source-text drafts/ID/text --out drafts/ID/eligibility.json`
   6. `GOV brief --input drafts/ID/signals.json --eligibility drafts/ID/eligibility.json --source-text drafts/ID/text --out drafts/ID/brief.json`
   7. 결과에 따라 상태를 '2차 완료(권고)', '2차 완료(조건부)', '2차 완료(비권고)' 가운데 하나로 바꾼다.
   8. 결과 메일: `reports/review-ID.json`에 `{"subject": "[토스트] 2차 검토 ID: 권고|조건부|비권고", "html": ...}`를 쓴다. html에는 종합 의견과 이유, 요건별 판정(verdict가 `reference`인 기타 요건은 판정 표에 섞지 않고 아래 '참고 조건' 표로 따로 모은다, D36)과 근거 문장·위치, 시연 필요 여부와 이유, 읽지 못한 첨부, "최종 판단은 대표가 합니다" 문구를 표로 넣는다. `REPORT send-mail --mail reports/review-ID.json`
3. 사업 현황판을 daily-routine 6단계와 같은 방법으로 다시 게시한다. 결과는 4번 build 뒤에 `REPORT record-step --runs runs --date TODAY --step board --ok true|false --routine review`로 남긴다.
4. 실행 기록: `REPORT build --date TODAY --results results --runs runs --routine review`
5. 잠금을 풀고 한 줄로 보고한다: 처리한 공고 수와 결과.

실패하면 그 공고의 상태를 '2차 검토 요청'으로 되돌리고 다음 공고로 넘어간다.

# daily-report

에이전트가 남긴 날짜별 결과 파일(`docs/result-format.md`, format_version 1)과 수집 이력 시트를 읽어, 대표에게 가는 신규 알림 메일 본문과 입찰 현황판 HTML을 만들고, 시트 연동과 실행 기록을 맡습니다. Python 3.13과 표준 라이브러리만 씁니다. 네트워크는 시트 웹 앱(Apps Script)을 부르는 명령만 씁니다. 명세는 `.scratch/daily-report/spec.md`입니다.

## 실행 방법

진입점은 플러그인의 `scripts/report.py`이며, 모든 경로는 작업 폴더 기준입니다. 명령의 정본 순서는 `daily-routine`·`review-requests` 스킬에 있습니다.

```
report.py build --date 2026-11-05 --results results --runs runs [--routine daily|review]
report.py mail --date 2026-11-05 --results results --out reports/mail.json [--board-url <현황판 주소>] [--settings settings]
report.py send-mail --mail reports/mail.json
report.py record-publish --runs runs --date 2026-11-05 --at 2026-11-05T10:58:00+09:00 --ok true --results results
report.py board --date 2026-11-05 --sheet reports/sheet.json --out reports/board.html
report.py sheet-push --date 2026-11-05 --state state / sheet-pull --out <파일> / sheet-status --key <키> --status <상태>
report.py record-step --runs runs --date 2026-11-05 --step sheet --ok true
report.py lock acquire|release --runs runs --owner daily|review
report.py arrival-rate --runs runs --from 2026-11-02 --to 2026-11-06 [--deadline 11:00]
```

- `build`는 그날 실행 기록 줄을 시작합니다. 보고서 HTML은 만들지 않습니다(D35, 2026-11-11).
- 시험: 저장소 루트에서 `python -X utf8 plugin/scripts/run_tests.py`

## 역할의 경계

- 이 코드는 **호출된 시점에 있는 결과 파일만으로** 전달물을 만듭니다. 10:50 시간 상자는 호출하는 예약 작업의 일이며, 그때 없는 결과 파일은 '결과 없음'으로 표시됩니다.
- 메일 발송은 Apps Script가, 현황판 게시는 스킬이 Artifact 도구로 합니다. 결과는 `record-publish`(메일, 도착 판정 D31)와 `record-step`(그 밖의 단계)으로 남깁니다.
- 기대하는 에이전트 목록은 `daily_report/inputs.py`의 `EXPECTED_AGENTS`입니다. 시장 정보 에이전트는 여기에 `"market"`을 더하면 읽고, 메일 절은 `render.py`의 `SECTIONS`에 더합니다.

## 동작 요약

- 파일이 없으면 '결과 없음', 읽을 수 없거나 형식 버전이 `"1"`이 아니거나 필수 필드가 없거나 `run_date`가 다르면 '형식 오류'입니다. 어제 파일로 대체하지 않습니다(전날 파일은 설정 변경 건수 비교에만 씁니다).
- 계약 문서의 목록에 있는 필드만 읽습니다. 링크의 인증키 매개변수(`serviceKey=` 등)는 지우고, `http`와 `https`가 아닌 주소는 링크로 만들지 않습니다.
- 메일: 실패 소스 → 확인이 필요한 점 → 최근 설정 변경 → 이미 본 공고 변경 건수 → 입찰공고·지원사업·민간 외주 절 → 현황판·시트 링크. 절 안은 마감이 가까운 순(마감 없음은 뒤)이고, 소스가 실패한 절에는 '수집 실패'를, 성공했지만 새 항목이 없는 절에는 '새 항목이 없습니다'를 씁니다. 메일 앱이 스크립트와 외부 CSS를 지우므로 인라인 스타일만 씁니다.
- 현황판: 마감 전 입찰공고를 상태별로 묶고 검토 중을 맨 위에 둡니다. 대표 메모와 시트 주소는 싣지 않습니다.
- 도착률: 기간의 모든 날짜가 분모이고, 기록이 없는 날은 미실행입니다. 마감 시각(기본 11:00, `runs.py`의 `DEADLINE`)까지 메일 발송에 성공한 날만 분자입니다. `review` 줄은 세지 않습니다.

## 가정 목록 (대표가 정한 것이 아니므로 확인이 필요합니다)

1. 마감 임박: 마감까지 0~7일인 항목. D-day는 `deadline`과 `--date`로 계산하며 결과 파일의 `dday`는 읽지 않습니다.
2. 최근 설정 변경: 수집 설정 2종(회사 프로필·시연 판정 기준은 건수에 영향이 없어 뺌), 기준일 기준 0~7일 이내(7일 전 포함, 미래 일자 제외). 값에 쉼표가 있으면 목록으로 보고 더하고 뺀 것만 적습니다.
3. 전날 대비 건수: 오늘과 전날 모두 수집에 성공한 소스의 `included`와 `excluded`만 합산합니다. 실패 소스를 넣으면 0건이 변화로 보이기 때문입니다.
4. 수집에 실패한 날은 "오늘은 새 공고가 없습니다"를 쓰지 않습니다. 성공한 소스가 있으면 "수집에 성공한 소스에는 오늘 새 항목이 없습니다", 하나도 없으면 "오늘 결과 파일을 확인하지 못했습니다"를 씁니다.
5. 에이전트 전체가 실패하면 마지막 정상 수집 시각을 알 수 없어 '확인 불가'로 표시하고, 모든 절에 '수집 실패'를 씁니다.

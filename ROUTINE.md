# Cowork 예약 작업 프롬프트 (매일 10:00, 로컬 실행)

이 문서는 Claude Cowork 예약 작업에 붙여 넣는 지침이다. 작업 폴더는 `07_Implementation`을 연결해서 쓴다(D3). 대표 PC가 켜져 있고 Claude 데스크톱 앱이 실행 중이어야 한다.

> 상태(2026-11-05): 코드는 가짜 응답으로만 시험했다. 인증키 승인과 실제 응답 확인(11/6), Cowork 시험 1~4(네트워크 송신, 무인 실행, `.env` 읽기, 휴대폰 앱 열람)가 끝나기 전에는 이 작업을 켜지 않는다.

## 예약 작업에 붙여 넣을 지침

```
너는 토스트 애니메이션 스튜디오 대표를 위한 일일 보고서를 만든다. 연결된 작업 폴더는 07_Implementation이다.
오늘 날짜(한국 시간, YYYY-MM-DD)를 TODAY라고 부른다. 아래 순서를 지키고, 한 단계가 실패해도 다음 단계로 이어간다.

1. 수집
   cd gov-agent
   python -X utf8 -m gov_agent run --date TODAY --out ../results
   - 인증키는 코드가 작업 폴더의 .env에서 직접 읽는다. .env 파일을 열어 보거나 내용을 출력하지 않는다.
   - 10:50까지 끝나지 않으면 기다리지 말고 2단계로 넘어간다.
2. 보고서 만들기
   cd ../daily-report
   python -X utf8 -m daily_report build --date TODAY --results ../results --out ../reports --settings ../gov-agent/settings --runs ../runs
   - 이 명령은 reports/report-TODAY.html과 runs/runs.jsonl의 한 줄을 만든다. HTML을 직접 고치지 않는다.
3. 게시
   - Artifact 도구로 reports/report-TODAY.html을 게시한다. capabilities는 절대 선언하지 않는다(승인 프롬프트가 떠서 무인 실행이 멈춘다).
   - reports/artifact-url.txt가 있으면 그 주소를 url로 넘겨 같은 주소에 다시 게시한다. 없으면 새로 게시하고(icon은 report), 받은 주소를 reports/artifact-url.txt에 한 줄로 저장한다.
4. 기록
   cd ../daily-report
   python -X utf8 -m daily_report record-publish --runs ../runs --date TODAY --at <지금 한국 시각 ISO 8601> --ok true
   - 게시에 실패했으면 --ok false로 기록한다.
5. 끝. 한 줄로 결과만 보고한다: 성공한 소스, 실패한 소스와 사유 종류, 게시 성공 여부.

금지: 인증키나 .env 내용을 출력하거나 기록하지 않는다. gov-agent/settings 아래 설정 파일을 고치지 않는다. 제안 가능성 검토는 이 작업에서 자동으로 하지 않는다.
```

## 처음 설정할 때 (한 번만)

1. 작업 폴더로 `07_Implementation`을 연결하고, 작업 폴더 루트에 `.env`를 만든다(`.env.example` 참고, 키는 대표가 직접 입력).
2. 위 지침으로 예약 작업을 만들고 빈도는 **평일 10:00**(또는 매일)으로 한다. 대표 PC가 가장 확실하게 켜져 있는 시각이다(D5).
3. **지금 실행**으로 한 번 돌려 권한 프롬프트를 확인하고, 뜨는 도구마다 "항상 허용"을 선택한다. 이후 실행은 같은 도구를 자동 승인한다.
4. 보고서가 게시되면 주소를 휴대폰 Claude 앱에서 열어 확인한다.
5. 컴퓨터의 절전을 막는다(설정의 절전 방지 항목). 노트북이면 덮개를 닫지 않는다.

## 확인하지 못한 것

- 예약 작업이 폴더를 연결한 상태에서 `python`을 실행하고 Artifact 도구로 무인 게시할 수 있는지는 문서로 확인되지 않았다. 11/5 시험의 결과에 따른다.
- 같은 주소로 다시 게시할 때 승인 프롬프트가 뜨지 않는 조건(내 소유, 공개 공유 아님, capability 선언 없음 등)은 문서 기준이며 실제 동작은 시험으로 확인한다.
- 놓친 실행(PC가 꺼져 있던 날)의 처리는 Cowork 문서에 없다. 그런 날은 실행 기록이 없으므로 도착률에서 '미실행'으로 센다.

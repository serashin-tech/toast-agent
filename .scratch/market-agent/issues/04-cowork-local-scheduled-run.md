Status: ready-for-human
Type: prototype
Blocked by: 01
작성일: 2026-11-05
근거: 상위 PRD V1.5 US-06, R-6, Cowork 루틴 리서치 문서(2026-11-09 정리 때 지움, 남은 사실은 `ARCHITECTURE.md` 실행 환경 절)

# Cowork 예약 작업을 로컬 폴더 연결로 무인 실행하는 시험

## 질문

로컬 폴더(`market-agent/`)를 연결한 Cowork 예약 작업이 대표 PC에서 실행되고, 사람이 없는 상태로 Agent Reach 명령을 끝까지 실행하는가?

## 확인 항목

- [ ] 폴더를 연결한 예약 작업이 클라우드가 아니라 로컬에서 실행되는지 확인한다(실행 기록, 외부 IP 비교)
- [ ] 셸 명령 실행 중 권한 확인 창이 떠서 멈추는지 확인한다. 멈추면 "승인 모드" 설정으로 해결되는지 본다
- [ ] PC가 잠자기이거나 앱이 닫혀 있을 때의 동작을 기록한다(R-6)
- [ ] 결과 JSON이 daily-report가 읽는 위치에 저장되는지 확인한다

## 완료 기준

Cowork 앱에서 사람이 직접 설정해야 하므로 ready-for-human으로 둔다. 결과와 설정 화면 캡처 위치를 Answer에 남긴다.

## Comments
- 2026-11-05: 대표 PC 대신 코드프레소 PC(sera.shin)에서 먼저 시험한다. Cowork 대신 Claude 데스크톱 앱의 예약 작업(로컬 실행, 앱이 열려 있을 때 실행)을 쓴다.
  - Agent Reach 1.6.1을 uv tool로 설치했다(`C:\Users\user\.local\bin\agent-reach.exe`, yt-dlp는 `uv tool dir`\agent-reach\Scripts).
  - `market-agent/collect.py search`를 수동 실행: YouTube 요청 6회, 2분 5초, 후보 15~30건씩 정상. 키워드는 시험용(`keywords.json`).
  - 예약 작업 `toast-market-agent-youtube`(수동 실행형, Auto 모드로 저장)를 만들었다. 프롬프트: 검색 → 관련도 판정 → 언어별 상위 3건 read → `data/market_YYYYMMDD.json` → commit.
  - 무인 실행은 사람이 앱 사이드바 Scheduled에서 "Run now"를 눌러 시작해야 한다(에이전트의 실행 요청은 권한 분류기가 거부함). 결과 대기 중.

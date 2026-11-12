# toast-agent

토스트 애니메이션 스튜디오 대표를 위한 **토스트 에이전트**입니다. 안에 정부사업 에이전트(gov-agent)와 시장 정보 에이전트(market-agent)가 있고, Claude 플러그인 `toast-agent`로 배포합니다. 매일 10:00에 나라장터 용역 입찰공고, 지원사업 공고, CGLink 민간 외주 글을 모아 신규 알림 메일로 보내고, 검토 중인 입찰공고의 상태를 사업 현황판으로 보여 줍니다. 대표가 시트에서 2차 검토를 요청하면 참가자격과 시연 필요 여부를 근거와 함께 검토합니다.

## 설치 (대표 PC)

대표가 직접 설치합니다. 절차의 정본은 `installer/README_install.md`입니다. 저장소를 ZIP으로 받아 `installer/install.bat`을 실행하면 작업 폴더(기본 `D:\toast-work`)와 `settings/`, `.env`가 만들어지고, 이후 Claude 허용 도메인, 플러그인 설치, 예약 작업, PC 절전 설정을 안내서대로 진행합니다(D37).

- 플러그인은 Cowork의 Customize > Plugins > Add marketplace로 이 저장소(비공개)를 추가해 설치합니다. 비공개 저장소를 받지 못하면 `plugin/` 폴더를 플러그인 파일로 업로드합니다(H14).
- 예약 작업은 PC가 켜져 있고 Claude 데스크톱이 실행 중일 때만 돌고, PC가 꺼져 있던 날은 도착률에서 '미실행'으로 셉니다.

대표용 설명서는 `plugin/scripts/daily-report/daily_report/manual.html`이며, artifact로 게시해 전달합니다(`.scratch/manual/spec.md`).

## 개발

`CLAUDE.md`를 먼저 읽습니다. 시험은 `python -X utf8 plugin/scripts/run_tests.py`입니다.

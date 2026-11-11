# toast-agent

토스트 애니메이션 스튜디오 대표를 위한 **토스트 에이전트**입니다. 안에 정부사업 에이전트(gov-agent)와 시장 정보 에이전트(market-agent)가 있고, Claude 플러그인 `toast-agent`로 배포합니다. 매일 10:00에 나라장터 용역 입찰공고, 지원사업 공고, CGLink 민간 외주 글을 모아 신규 알림 메일로 보내고, 검토 중인 입찰공고의 상태를 입찰 현황판으로 보여 줍니다. 대표가 시트에서 2차 검토를 요청하면 참가자격과 시연 필요 여부를 근거와 함께 검토합니다.

## 설치 (대표 PC)

1. Claude 데스크톱의 Cowork에서 Customize > Plugins > Add marketplace로 이 저장소(`serashin-tech/toast-agent`, 비공개)를 추가하고 `toast-agent` 플러그인을 설치합니다. 비공개 저장소를 받지 못하면 저장소를 clone한 뒤 `plugin/` 폴더를 플러그인 파일로 업로드합니다(H14).
2. 작업 폴더(예: `07_Implementation`)를 Cowork에 연결하고, 그 폴더에 `settings/`(플러그인의 `scripts/settings-template/`을 복사해 채움)와 `.env`(`.env.example` 참고)를 둡니다.
3. 예약 작업을 만듭니다: 평일 10:00에 `daily-routine`, 09~18시 30분마다 `review-requests`.

## 개발

`CLAUDE.md`를 먼저 읽습니다. 시험은 `python -X utf8 plugin/scripts/run_tests.py`입니다.

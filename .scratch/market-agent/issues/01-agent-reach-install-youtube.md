Status: resolved
Type: prototype
작성일: 2026-11-05
근거: 상위 PRD V1.5 US-06, NFR-007, §7-6

# Agent Reach를 Windows에 설치하고 YouTube 검색·자막 수집 시험

## 질문

대표 PC와 같은 Windows 11 환경에서 Agent Reach가 설치되고, 키워드 검색과 자막 수집이 API 키 없이 동작하는가?

## 확인 항목

- [ ] 설치 절차와 필요 런타임(Python 버전, ffmpeg 필요 여부)을 기록한다. 버전은 고정한다(NFR-004)
- [ ] 한국어 키워드 1개로 최근 7일 영상을 검색하고, 제목·채널·게시일·조회수·링크가 나오는지 확인한다
- [ ] 자동 생성 자막이 있는 영상 1건의 자막을 받는다
- [ ] 자막 원문을 요약 뒤에 지우는 흐름이 가능한지 확인한다(파일로 남는 위치 확인)
- [ ] 실패 시 출력되는 오류 형태를 기록한다(FR-011 실패 표시에 사용)

## 완료 기준

위 항목의 명령, 출력 예시, 소요 시간을 아래 Answer에 남긴다.

## Comments

## Answer (1차 시험, 2026-11-05, 코드프레소 PC·Windows 11·사무실 회선)

### 설치: 성공
- PyPI의 `agent-reach`는 다른 프로젝트이므로 쓰지 않는다. 공식 설치는 GitHub Release zip을 uv로 설치하는 방식이다.
  `uv tool install https://github.com/Panniantong/Agent-Reach/releases/latest/download/agent-reach.zip`
- 설치 버전: Agent Reach 1.6.1 (MIT), yt-dlp 2026.8.19, yt-dlp-ejs 0.8.0. 소요 9초. Python 3.10 이상과 uv가 필요하다. ffmpeg는 이번 시험에서 쓰지 않았다.
- 시험에서는 `UV_TOOL_DIR`·`UV_TOOL_BIN_DIR`를 임시 폴더로 지정해 격리 설치했다. `agent-reach setup`(스킬 설치)은 실행하지 않았다.
- 고정할 버전은 `agent-reach version`으로 확인한다(NFR-004). 롤백은 `uv tool install --force .../archive/refs/tags/v<버전>.zip`이다.

### 검색 (`agent-reach youtube search "<키워드>" --limit 10`): 성공, 단 한계 있음
- 7초에 10건. 출력은 JSON이며 `items[].title/author/url`과 `raw.view_count/duration/channel_id`가 나온다.
- 한계 1: `published_at`이 비어 있다. 게시일을 알려면 영상마다 `youtube read`를 따로 호출해야 한다.
- 한계 2: 기간 필터와 정렬 옵션이 없다. 관련도 순 결과만 나오므로 "최근 7일"은 결과를 받은 뒤 걸러야 한다. 검색 결과 10건 중 최근 7일 영상이 적을 수 있다.
- 한계 3: 검색 결과의 제목·채널명이 번역된 표시명으로 나오기도 한다(예: 검색에서는 "찍봇", read에서는 "ZZIK BOT"). 중복 판정은 영상 ID로 해야 한다.

### 영상 정보 (`agent-reach youtube read <url>`): 성공
- 23초 소요. 제목, 채널, 게시일(`published_at`), 조회수, 좋아요, 태그, 카테고리가 나온다. 일평균 조회수 계산에 필요한 값은 모두 있다.

### 자막 (`agent-reach youtube subtitle <id> --lang ko`): 실패
- 첫 요청(기본 언어 목록에 ko 추가)에서 `RATE_LIMITED`(HTTP 429 Too Many Requests)가 났다. 이 시점까지 YouTube 요청은 검색 1회, read 1회뿐이었다.
- 오류 후 Agent Reach가 YouTube 채널을 약 1시간 동안 스스로 멈춘다. 3분 뒤 재시도에서 "Wait 3383 seconds before retrying this channel."가 나왔다. 백엔드를 바꾸지 말라는 안내도 나온다.
- 자막 원문이 파일로 남는지는 확인하지 못했다(작업 폴더에는 JSON 출력 외 파일이 생기지 않았다).

### 실패 출력 형태 (FR-011에 사용)
- `{"ok": false, "error": {"code": "RATE_LIMITED", "message": ..., "hint": "Wait N seconds ..."}}`. 종료 코드는 1이다. `ok`와 `error.code`로 실패를 판별할 수 있다.

### 남은 확인
- 1시간 쿨다운이 끝난 뒤 자막 재시험 1회. 같은 결과면 이 회선에서는 자막 수집이 막힌 것으로 본다.
- 하루 수집량 추정: 4개 언어 × 검색 1회 + 후보 영상마다 read 1회 + 상위 12건 자막 = 하루 50회 안팎의 요청. 첫 자막 요청에서 429가 난 점을 보면 이 양은 위험하다.

### 결론 (2026-11-05, 상위 PRD V1.6에 반영)
- 자막 재시험은 하지 않는다. 자막은 수집 대상에서 뺐다(요약은 제목·설명문·태그). Gemini 영상 분석과 음성 변환은 비용 문제로 쓰지 않는다.
- 날짜 필터 문제는 yt-dlp를 직접 호출해 YouTube 검색의 "업로드 날짜: 이번 주" 필터로 푼다. 시험 결과 1회 요청에 30건(조회수·설명문 포함, 49초)이 나왔고, 표본 2건의 게시일(11/4, 11/2)이 이번 주였다. 명령:
  `yt-dlp --flat-playlist -J "https://www.youtube.com/results?search_query=<키워드>&sp=EgIIAw%253D%253D" --playlist-end 30`
- 다른 언어와 키워드 OR 묶음 검색은 02에서 확인한다.

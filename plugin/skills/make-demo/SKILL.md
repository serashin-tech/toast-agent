---
name: make-demo
description: 2차 검토에서 시연이 필요하다고 나온 입찰공고의 1차 시연 데모(캐릭터·화면 초안)를 Adobe for creativity 커넥터로 만든다. 대표가 시트 상태를 '데모 요청'으로 바꾼 뒤 "데모 만들어 줘"라고 할 때만 쓴다. 무인으로 돌리지 않는다(D23).
---

작업 폴더에서 대화로 실행한다. 대표 계정에서만 쓴다(코드프레소 Claude 조직은 이 커넥터 추가가 막혀 있다).

## 처음 한 번 (커넥터 연결)

1. 대표 계정의 Claude 앱 커넥터 목록에서 **Adobe for creativity**를 연결한다. Adobe 계정 없이도 연결은 되며, 로그인하면 한도와 도구가 늘어난다고 알려져 있다(미확인).
2. 새 대화에서 "Adobe 커넥터에서 쓸 수 있는 도구 목록을 보여 줘"라고 요청해 이미지 생성 도구 이름, 결과를 로컬 파일로 받는지 링크만 받는지를 확인하고, 코드프레소 담당자에게 알린다(확인 기록은 저장소 하네스 티켓 16).

## 리허설 (가상 공고, 커넥터 없이)

`${CLAUDE_PLUGIN_ROOT}/scripts/fixtures/demo-sample/`의 가상 공고 R26BK999와 미리 추출한 입력으로 1~2단계를 시험할 수 있다. 결과는 작업 폴더 `settings/company-profile.md` 값에 따라 달라진다.

```
python -X utf8 "${CLAUDE_PLUGIN_ROOT}/scripts/gov.py" eligibility --input "${CLAUDE_PLUGIN_ROOT}/scripts/fixtures/demo-sample/requirements.json" --out drafts/R26BK999/eligibility.json
python -X utf8 "${CLAUDE_PLUGIN_ROOT}/scripts/gov.py" brief --input "${CLAUDE_PLUGIN_ROOT}/scripts/fixtures/demo-sample/signals.json" --eligibility drafts/R26BK999/eligibility.json --out drafts/R26BK999/brief.json
```

## 순서

1. 공고번호 ID를 확인하고 `drafts/ID/brief.json`을 읽는다. 없거나 `demo_needed`가 yes가 아니면 이유를 알리고 멈춘다. 대표가 needs_check를 yes로 정하면 이어 간다.
2. `brief.json`을 표로 요약해 보여 준다: 관문(제안 조건 검토), 시연 필요 여부와 이유, 만들 것, 근거 문장과 위치, 관련 배점, 제약, 생성형 AI 관련 문구. 대표가 "데모 만들어"라고 답해야 다음으로 간다.
3. `drafts/ID/prompt.md`에 커넥터에 줄 지시를 쓴다. 지시는 `brief.json`의 constraints(format, count, size, due, audience)와 style_refs만으로 만든다.
   - 캐릭터: 같은 세계관의 주인공 2~3안, 각 안은 정면 전신 한 장. 단순한 형태, 대상 연령에 맞는 색감.
   - 화면: 1안 캐릭터가 나오는 키비주얼 1장(가로 16:9).
4. 커넥터의 이미지 생성 도구로 만든다. 한 번에 최대 4장이며, 더 필요하면 대표에게 묻는다.
5. `drafts/ID/outputs.md` 맨 위에 "AI가 만든 1차 초안입니다. 제출 전 디자이너 검수와 생성형 AI 활용 명시가 필요합니다."를 적고, 안 번호·도구·결과 경로나 링크·생성 시각을 적는다. 결과를 로컬로 받을 수 있으면 같은 폴더에 저장한다.
6. `python -X utf8 "${CLAUDE_PLUGIN_ROOT}/scripts/report.py" sheet-status --key KEY --status "데모 완료"`

금지: 실존 캐릭터, 타사 IP, 유명 작가의 화풍을 따라 하라는 지시를 쓰지 않는다. 발주기관 로고나 공식 상징물을 만들지 않는다. 대표가 허락하지 않은 회사 자료를 커넥터에 올리지 않는다.

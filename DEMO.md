# 공고 1건 검토부터 1차 시연 데모까지 (대화형 절차)

이 문서는 Claude 데스크톱(Code 탭 또는 Cowork)에 붙여 넣는 지침입니다. 대표가 시트에서 '데모 확인'을 표시한 공고를 Claude 데스크톱에 한 줄로 요청할 때 실행합니다(D23). 매일 10:00 무인 루틴(`ROUTINE.md`)에서는 실행하지 않습니다.

> 상태(2026-11-09): 2단계(제안 조건 검토)와 3단계(2차 검토)는 코드와 시험이 있습니다. 4단계(Adobe 커넥터)는 커넥터를 연결해 실제로 돌려 보기 전이며, 도구 이름과 결과 저장 방식을 확인하지 못했습니다.

## 처음 한 번만

1. 작업 폴더로 `07_Implementation`을 연결합니다.
2. Claude 앱의 커넥터 목록에서 **Adobe for creativity**를 찾아 연결합니다. **코드프레소 Claude 조직에서는 이 커넥터 추가가 막혀 있으므로(2026-11-09 확인), 4단계는 토스트 대표님의 Claude 계정에서만 실행합니다.** 1~3단계는 어느 계정에서나 됩니다. Adobe 계정 없이도 연결은 되지만, 계정으로 로그인하면 사용 한도와 도구가 늘어난다고 알려져 있습니다(제3자 기사 기준, 미확인). 토스트 계정 정보는 대표에게 받습니다.
3. 연결한 뒤 새 대화에서 "Adobe 커넥터에서 쓸 수 있는 도구 목록을 보여 줘"라고 요청해 도구 이름을 확인하고, 아래 "확인 기록"에 적습니다.

## 붙여 넣을 지침

`<공고번호>`와 `<공고 자료>`(첨부 파일 경로 또는 원문 링크)를 바꿔서 씁니다.

```
공고 <공고번호>를 검토하고 필요하면 1차 시연 데모까지 만든다. 공고 자료: <공고 자료>
작업 폴더는 07_Implementation이고, 모든 산출물은 drafts/<공고번호>/ 에 쓴다.

1. 첨부 읽기
   - hwp·hwpx는 kordoc 스킬로 읽는다. 그 밖의 파일(pdf, docx, pptx, xlsx 등)은 markitdown으로 읽는다(예: markitdown <파일> -o <파일>.md). 읽지 못한 첨부는 이름과 링크를 기록한다(D27).
2. 제안 조건 검토(참가자격)
   - gov-agent/docs/eligibility-input.md 형식으로 drafts/<공고번호>/requirements.json 을 쓴다. 근거 문장과 위치를 반드시 넣는다.
   - cd gov-agent
     python -X utf8 -m gov_agent eligibility --input ../drafts/<공고번호>/requirements.json --out ../drafts/<공고번호>/eligibility.json
3. 2차 검토(시연 판정)
   - 과업 내용, 제안서 작성 요령, 평가표, 기타 조건을 읽고 gov-agent/docs/demo-brief-input.md 형식으로 drafts/<공고번호>/signals.json 을 쓴다.
     시연·시안·샘플 요구 문장은 signals에, 평가 배점은 scoring에, 형식·수량·마감·대상은 constraints에, 생성형 AI 관련 문구는 ai_use_notes에 넣는다.
   - python -X utf8 -m gov_agent brief --input ../drafts/<공고번호>/signals.json --eligibility ../drafts/<공고번호>/eligibility.json --out ../drafts/<공고번호>/brief.json
4. 대표 확인 (여기서 멈춘다)
   - brief.json을 표로 요약해 보여 준다: 관문(제안 조건 검토 결과), 시연 필요 여부와 이유, 만들 것(캐릭터·화면), 근거 문장과 위치, 관련 배점, 제약, 생성형 AI 관련 문구.
   - demo_needed가 yes이거나 대표가 needs_check를 yes로 정했을 때만, 대표가 "데모 만들어"라고 답한 뒤 5단계로 간다. no이면 여기서 끝낸다.
5. 1차 시연 데모 제작 (Adobe for creativity 커넥터)
   - 먼저 drafts/<공고번호>/prompt.md 에 커넥터에 줄 지시를 쓴다. 지시는 brief.json의 constraints(형식 format, 수량 count, 규격 size, 마감 due, 대상 audience)와 style_refs만으로 만든다.
     캐릭터(character): 같은 세계관의 주인공 캐릭터 2~3안. 각 안은 정면 전신 한 장. 단순한 형태, 대상 연령에 맞는 색감.
     화면(screen): 1안 캐릭터가 등장하는 키비주얼 1장(가로 16:9).
   - 커넥터의 이미지 생성 도구로 만든다. 한 번에 최대 4장까지만 만들고, 더 필요하면 대표에게 묻는다.
   - 결과를 drafts/<공고번호>/outputs.md 에 적는다: 안 번호, 사용한 도구, 결과 파일 경로 또는 Adobe 링크, 생성 시각. 로컬로 받을 수 있으면 같은 폴더에 저장한다.
   - outputs.md 맨 위에 "AI가 만든 1차 초안입니다. 제출 전 디자이너 검수와 생성형 AI 활용 명시가 필요합니다."를 적는다.
6. 끝. 한 줄로 보고한다: 관문 결과, 시연 판정, 만든 안의 수, 결과 위치.

금지:
- 실존 캐릭터, 타사 IP, 유명 작가의 화풍을 따라 하라는 지시를 쓰지 않는다. 발주기관 로고나 공식 상징물을 만들지 않는다.
- 대표가 허락하지 않은 회사 자료(기존 캐릭터 이미지 등)를 커넥터에 올리지 않는다.
- gov-agent/settings 아래 설정 파일을 고치지 않는다. 인증키나 .env 내용을 출력하지 않는다.
```

## 리허설(가상 공고)

`demo-sample/`에 가상 공고 R26BK999와 미리 추출해 둔 `requirements.json`, `signals.json`이 있습니다. 1~3단계를 Claude 없이 코드만으로 확인하려면 아래를 실행합니다.

```
cd gov-agent
python -X utf8 -m gov_agent eligibility --input ../demo-sample/requirements.json --out ../drafts/R26BK999/eligibility.json
python -X utf8 -m gov_agent brief --input ../demo-sample/signals.json --eligibility ../drafts/R26BK999/eligibility.json --out ../drafts/R26BK999/brief.json
```

2026-11-09 회사 프로필 기준으로 다시 돌린 결과는 제안 조건 검토 `recommend`(권고, 충족 3건: 등록 업종, 소재지, 중소기업 확인)와 시연 필요 `yes`(만들 것 `both`)입니다. 11/9에 등록 업종과 중소기업 확인이 공공 기록으로 '확인됨'이 되었기 때문입니다. 프로필 값이 바뀌면 결과도 바뀌므로, 시연 전에 이 두 명령을 다시 돌려 `drafts/R26BK999/`를 갱신합니다.

## 확인 기록 (커넥터 연결 후 채움)

| 항목 | 결과 | 확인일 |
|---|---|---|
| 커넥터 도구 목록(이미지 생성에 쓴 도구 이름) | | |
| 결과를 로컬 파일로 받을 수 있는가, 링크만 받는가 | | |
| Adobe 계정 없이 생성되는가, 한도는 | | |
| 같은 캐릭터를 여러 장에서 일관되게 그리는가 | | |
| 4장 생성에 걸린 시간 | | |

# 2차 검토(시연 판정) 입력 형식

시연 신호 추출은 Claude가 하고, 코드는 근거가 확인된 신호만 '필요'로 셉니다. 이 문서는 코드가 받는 입력 JSON의 형식입니다.

실행: `python -X utf8 -m gov_agent brief --input 신호.json [--eligibility 검토결과.json] [--settings 설정폴더] [--out drafts/<공고번호>/brief.json]`

`--eligibility`에는 같은 공고에 대해 `eligibility` 명령이 낸 결과 파일을 넣습니다. 종합 의견이 `not_recommend`이면 시연 데모를 만들지 않습니다(관문). 넣지 않으면 관문 없이 판정하고 이유에 그 사실을 적습니다.

## 입력

```json
{
  "bid_id": "R26BK999",
  "title": "OO시 어린이 교통안전 홍보 애니메이션 제작",
  "unreadable_files": [{"name": "과업지시서.hwp", "url": "https://..."}],
  "signals": [
    {
      "text": "캐릭터 시안 2종 제출",
      "deliverable": "character",
      "evidence": {"quote": "제안사는 주인공 캐릭터 시안 2종 이상을 제안서에 포함하여야 한다", "location": "제안요청서 8쪽 3항"}
    }
  ],
  "scoring": [{"item": "캐릭터·디자인 제안의 창의성", "points": 15, "evidence": {"quote": "...", "location": "제안요청서 12쪽 평가표"}}],
  "constraints": {"format": "PNG 또는 PDF", "count": 2, "size": null, "due": "2026-12-01", "audience": "초등 저학년"},
  "ai_use_notes": [{"text": "생성형 AI 활용 시 활용 범위를 명시", "evidence": {"quote": "...", "location": "..."}}],
  "style_refs": ["토스트 '키키와 친구들' 캐릭터 톤"]
}
```

- `signals`: 공고가 시연·시안·샘플·데모를 요구하는 문장입니다. 요구가 없으면 빈 배열입니다.
- `deliverable`: `character`(캐릭터), `screen`(키비주얼·포스터·화면·스토리보드 컷), 모르면 `null`입니다.
- `evidence`: `quote`와 `location`이 **둘 다** 있고, `quote`에 설정 `demo-criteria.md`의 신호 단어가 들어 있어야 `confirmed`입니다. 그렇지 않으면 `needs_check`입니다.
- `scoring`, `constraints`, `ai_use_notes`, `style_refs`: 판정에 쓰지 않고 브리프에 그대로 옮깁니다. 데모 제작 지시에 씁니다. `style_refs`는 대표가 허락한 회사 자료만 적습니다.

## 판정 규칙

1. 제안 조건 검토 종합 의견이 `not_recommend`이면 `demo_needed=no`, `deliverable=none`입니다. 신호 판정은 남겨서 대표가 직접 뒤집을 수 있게 합니다.
2. 확인된(`confirmed`) 신호가 하나라도 있으면 `demo_needed=yes`입니다.
3. 확인된 신호는 없지만 확인되지 않은 신호나 읽지 못한 첨부가 있으면 `needs_check`입니다. 읽지 못한 첨부에 요구가 있을 수 있기 때문입니다.
4. 그 밖에는 `no`입니다.
5. `deliverable`: 확인된 신호에 캐릭터와 화면이 모두 있으면 `both`, 하나만 있으면 그것, 둘 다 없으면 `unspecified`입니다. `demo_needed`가 `yes`가 아니면 `none`입니다.
6. `disclaimer`에는 항상 "최종 판단은 대표가 합니다."가 들어갑니다.

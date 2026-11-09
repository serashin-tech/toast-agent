"""한국콘텐츠진흥원 지원사업공고(S3) 어댑터.

미확인 가정: 요청 주소(환경 설정 KOCCA_API_URL로만 지정), 요청 파라미터, 증분 파라미터 없음,
아래 FIELDS의 모든 필드 이름. 증분 파라미터가 없다고 가정하므로 전체를 받아 등록일로 로컬에서 거른다
(LOCAL_INCREMENT).
"""
from . import _common as c

ID, LABEL, KIND = "grant_kocca", "지원사업(한국콘텐츠진흥원)", "grant"
PORTAL = "https://www.kocca.kr"
URL_ENV = "KOCCA_API_URL"
PAGE_SIZE = 100
LOCAL_INCREMENT = True
HEADER_PATH = ("response", "header")
ITEMS_PATH = ("response", "body", "items")
TOTAL_PATH = ("response", "body", "totalCount")

FIELDS = {"id": "bizNo", "title": "title", "category": "category", "posted_on": "regDate", "url": "link",
          "period_start": "rcptBgnDe", "period_end": "rcptEndDe", "agency": "agencyNm"}


def url(env):
    return env.get(URL_ENV) or ""


def build_params(since, now):
    return {"type": "json"}  # 가정: 증분 파라미터 없음


def normalize(raw):
    p = lambda k: c.pick(raw, FIELDS[k])
    if not p("id") or not p("title"):
        return None
    end = c.to_date(p("period_end"))
    return {"id": p("id"), "title": p("title"), "posted_on": c.to_date(p("posted_on")), "deadline": end,
            "url": p("url") or PORTAL, "agency": p("agency"), "period_start": c.to_date(p("period_start")),
            "category": p("category"), "target": None, "contact": None, "summary": None}

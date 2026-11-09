"""중소기업 지원사업 공고 조회 서비스(S4) 어댑터.

미확인 가정: 응답 JSON 구조(response.body.items), 아래 FIELDS의 모든 필드 이름,
updtPnttm 의 값 형식(12자리 일시로 가정), 신청기간 한 문자열("시작 ~ 종료")의 모양.
"""
from . import _common as c

ID, LABEL, KIND = "grant_bizinfo", "지원사업(중소기업 지원사업 공고)", "grant"
PORTAL = "https://www.bizinfo.go.kr"
URL_BASE = "https://apis.data.go.kr/1421000/bizinfo"
URL_ENV = "BIZINFO_API_URL"
PAGE_SIZE = 100
LOCAL_INCREMENT = False
HEADER_PATH = ("response", "header")
ITEMS_PATH = ("response", "body", "items")
TOTAL_PATH = ("response", "body", "totalCount")

FIELDS = {"id": "pblancId", "title": "pblancNm", "url": "pblancUrl", "agency": "jrsdInsttNm",
          "executor": "excInsttNm", "summary": "bsnsSumryCn", "category": "pldirSportRealmLclasCodeNm",
          "period": "reqstBeginEndDe", "target": "trgetNm", "contact": "refrncNm", "posted_on": "creatPnttm"}


def url(env):
    return env.get(URL_ENV) or URL_BASE


def build_params(since, now):
    p = {"dataType": "json"}
    if since:
        p["updtPnttm"] = since.strftime("%Y%m%d%H%M")
    return p


def normalize(raw):
    p = lambda k: c.pick(raw, FIELDS[k])
    if not p("id") or not p("title"):
        return None
    dates = c.all_dates(p("period"))
    return {"id": p("id"), "title": p("title"), "posted_on": c.to_date(p("posted_on")),
            "deadline": dates[-1] if dates else None, "url": p("url") or PORTAL,
            "agency": p("agency") or p("executor"), "period_start": dates[0] if dates else None,
            "category": p("category"), "target": p("target"), "contact": p("contact"), "summary": p("summary")}

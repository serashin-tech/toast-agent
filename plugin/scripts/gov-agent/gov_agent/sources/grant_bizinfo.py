"""중소기업 지원사업 공고 조회 서비스(S4) 어댑터.

2026-11-11 실제 응답으로 확인: 오퍼레이션 `/pblancBsnsService`, dataType=json, JSON 구조(response.body.items.item),
FIELDS의 필드 이름, 신청기간 문자열("2026-11-09 ~ 2026-11-16" 또는 "상시 접수").
updtPnttm 필터는 8자리 날짜 하루만 맞추므로 증분에 쓰지 않는다. 당해 공고 전체(약 1,400건, 100건씩 15회 안팎)를
매일 받고, 이미 보여 준 공고는 원장이 가린다.
"""
from . import _common as c

ID, LABEL, KIND = "grant_bizinfo", "지원사업(중소기업 지원사업 공고)", "grant"
PORTAL = "https://www.bizinfo.go.kr"
URL_BASE = "https://apis.data.go.kr/1421000/bizinfo/pblancBsnsService"
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
    return {"dataType": "json"}


def normalize(raw):
    p = lambda k: c.pick(raw, FIELDS[k])
    if not p("id") or not p("title"):
        return None
    dates = c.all_dates(p("period"))
    return {"id": p("id"), "title": p("title"), "posted_on": c.to_date(p("posted_on")),
            "deadline": dates[-1] if dates else None, "url": p("url") or PORTAL,
            "agency": p("agency") or p("executor"), "period_start": dates[0] if dates else None,
            "category": p("category"), "target": p("target"), "contact": p("contact"), "summary": p("summary")}

"""입찰공고정보서비스(S1) 어댑터: 용역 입찰공고 목록.

2026-11-11 실제 응답으로 확인: 오퍼레이션 `getBidPblancListInfoServc02`, inqryDiv=1과 12자리 조회 기간,
JSON 구조(response.body.items), FIELDS의 필드 이름. 2026-11-10부터 조회 기간은 최대 7일이다(공공데이터포털 공지).
"""
from datetime import timedelta

from . import _common as c

ID, LABEL, KIND = "bid", "입찰공고(나라장터 용역)", "bid"
PORTAL = "https://www.g2b.go.kr"
URL_BASE = "https://apis.data.go.kr/1230000/ad/BidPublicInfoService02"
OPERATION = "getBidPblancListInfoServc02"
MAX_WINDOW = timedelta(days=7)
URL_ENV = "BID_API_URL"
PAGE_SIZE = 100
HEADER_PATH = ("response", "header")
ITEMS_PATH = ("response", "body", "items")
TOTAL_PATH = ("response", "body", "totalCount")

# 표준 이름 -> 응답 필드 이름(가정)
FIELDS = {"id": "bidNtceNo", "title": "bidNtceNm", "agency": "ntceInsttNm", "demand_agency": "dminsttNm",
          "agency_type": "insttDivNm", "est_price": "presmptPrce", "deadline": "bidClseDt",
          "posted_on": "bidNtceDt", "url": "bidNtceUrl"}
ATTACHMENTS = [(f"ntceSpecFileNm{i}", f"ntceSpecDocUrl{i}") for i in range(1, 11)]  # (이름, 주소) 쌍


def url(env):
    return env.get(URL_ENV) or f"{URL_BASE}/{OPERATION}"


def build_params(since, now):
    # ponytail: 7일보다 오래 쉬었으면 그 앞의 공고는 받지 않는다. 필요하면 7일 단위로 나눠 여러 번 부른다.
    since = max(since, now - MAX_WINDOW)
    return {"inqryDiv": "1", "inqryBgnDt": since.strftime("%Y%m%d%H%M"),
            "inqryEndDt": now.strftime("%Y%m%d%H%M"), "type": "json"}


def normalize(raw):
    p = lambda k: c.pick(raw, FIELDS[k])
    if not p("id") or not p("title"):
        return None
    atts = [{"name": c.pick(raw, n) or "", "url": c.pick(raw, u)} for n, u in ATTACHMENTS if c.pick(raw, u)]
    return {"id": p("id"), "title": p("title"), "posted_on": c.to_date(p("posted_on")),
            "deadline": c.to_date(p("deadline")), "url": p("url") or PORTAL,
            "agency": p("agency"), "demand_agency": p("demand_agency"), "agency_type": p("agency_type"),
            "est_price": c.to_int(p("est_price")), "attachments": atts}

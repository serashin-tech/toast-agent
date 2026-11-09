"""입찰공고정보서비스(S1) 어댑터: 용역 입찰공고 목록.

미확인 가정: 오퍼레이션 이름, inqryDiv 값, 조회 기간 형식(12자리), 아래 FIELDS의 모든 필드 이름.
승인된 키로 실제 응답을 받은 뒤 이 파일의 대응표만 고치면 된다.
"""
from . import _common as c

ID, LABEL, KIND = "bid", "입찰공고(나라장터 용역)", "bid"
PORTAL = "https://www.g2b.go.kr"
URL_BASE = "https://apis.data.go.kr/1230000/ad/BidPublicInfoService02"
OPERATION = "getBidPblancListInfoServc"  # 가정
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

# 주의: 이 파일의 JSON 필드 이름은 모두 가정이다.
# 4개 API의 실제 응답 필드 이름은 아직 확인하지 못했다. 승인된 키로 실제 응답을
# 한 번 받아 키를 지운 뒤, 아래 값과 gov_agent/sources/*.py 의 FIELDS 표를 함께 교체해야 한다.
# 이 고정 응답은 실제 응답이 아니라 시험용으로 만든 가짜 응답이다.
import json


def envelope(items, total=None):
    """data.go.kr 공통 응답 모양(가정)으로 감싼다."""
    return json.dumps({"response": {
        "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE."},
        "body": {"items": items, "totalCount": len(items) if total is None else total}}},
        ensure_ascii=False)


def bid(no, title, price=100000000, deadline="2026-11-30 18:00", agency="전북특별자치도교육청",
        agency_type="교육기관", posted="2026-11-04 09:00", attach=None):
    d = {"bidNtceNo": no, "bidNtceNm": title, "ntceInsttNm": agency, "dminsttNm": agency,
         "insttDivNm": agency_type, "presmptPrce": str(price), "bidClseDt": deadline,
         "bidNtceDt": posted, "bidNtceUrl": f"https://www.g2b.go.kr/notice/{no}"}
    for i, (n, u) in enumerate(attach or [], 1):
        d[f"ntceSpecFileNm{i}"] = n
        d[f"ntceSpecDocUrl{i}"] = u
    return d


def kocca(no, title, end="2026-12-10", start="2026-11-20", posted="2026-11-04", category="콘텐츠제작지원"):
    return {"bizNo": no, "title": title, "category": category, "regDate": posted,
            "link": f"https://www.kocca.kr/notice/{no}", "rcptBgnDe": start, "rcptEndDe": end,
            "agencyNm": "한국콘텐츠진흥원"}


def bizinfo(pid, title, end="20261210", start="20261201", posted="20261104", field="문화", target=None):
    return {"pblancId": pid, "pblancNm": title, "pblancUrl": f"https://www.bizinfo.go.kr/{pid}",
            "jrsdInsttNm": "문화체육관광부", "excInsttNm": "한국콘텐츠진흥원",
            "bsnsSumryCn": "애니메이션 제작 지원", "pldirSportRealmLclasCodeNm": field,
            "reqstBeginEndDe": f"{start} ~ {end}", "trgetNm": target, "refrncNm": "02-000-0000",
            "creatPnttm": posted}


# CGLink 외주발주 게시판 RSS. 2026-11-09에 받은 실제 응답(https://cglink.com/jobsOffer/rss)의 모양을 따랐다.
def cglink(no, title, pub, creator="게시자", body="본문 연락처 010-0000-0000"):
    return (f"<item><title><![CDATA[{title}]]></title><dc:creator><![CDATA[{creator}]]></dc:creator>"
            f"<link>https://cglink.com/{no}</link><guid isPermaLink=\"true\">https://cglink.com/{no}</guid>"
            f"<description><![CDATA[{body}]]></description><pubDate>{pub}</pubDate></item>")


def rss(items):
    return ('<?xml version="1.0" encoding="UTF-8" ?><rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/">'
            "<channel><title><![CDATA[프리랜서 구인, 외주발주]]></title><link>https://cglink.com/jobsOffer</link>"
            + "".join(items) + "</channel></rss>")

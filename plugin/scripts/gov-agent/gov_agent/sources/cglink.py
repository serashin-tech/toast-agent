"""CGLink 외주발주 게시판(S5) 어댑터: 민간 애니메이션·CG 외주 의뢰 글.

공개 RSS(인증키 불필요)를 한 번 받아 읽는다. 응답 모양은 2026-11-09에 받은 실제 RSS로 확인했다.
본문(description)은 읽지 않는다. 연락처가 섞일 수 있고, 보고서에는 제목과 원문 링크면 충분하다.
RSS는 최근 글만 주므로 등록일로 로컬에서 증분을 거른다(LOCAL_INCREMENT).
"""
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

from . import _common as c

ID, LABEL, KIND = "outsource_cglink", "민간 외주(CGLink)", "outsource"
URL = "https://cglink.com/jobsOffer/rss"
LOCAL_INCREMENT = True
FIRST_RUN_DAYS = 14  # 한 달에 몇 건뿐인 게시판이라 처음 실행에는 2주치를 보여 준다
_DC = "{http://purl.org/dc/elements/1.1/}"


def fetch(transport, env, budget):
    """원본 항목 목록. 실패는 SourceError."""
    budget.take()
    try:
        status, body = transport(URL, {})
    except Exception as e:  # 네트워크 계층의 모든 실패
        raise c.SourceError("network", f"네트워크 오류: {type(e).__name__}: {e}"[:200])
    c._raise_http(status)
    try:
        channel = ET.fromstring(body or "").find("channel")
    except ET.ParseError:
        raise c.SourceError("format", "RSS를 해석하지 못함")
    if channel is None:
        raise c.SourceError("format", "RSS에 channel이 없음")
    return [{"title": i.findtext("title"), "link": i.findtext("link"), "creator": i.findtext(_DC + "creator"),
             "pubDate": i.findtext("pubDate")} for i in channel.iter("item")]


def normalize(raw):
    title, link = c.pick(raw, "title"), c.pick(raw, "link")
    if not title or not link or not link.startswith(("http://", "https://")):
        return None
    try:
        posted = parsedate_to_datetime(c.pick(raw, "pubDate") or "").date()
    except (TypeError, ValueError):
        posted = None
    return {"id": link.rstrip("/").rsplit("/", 1)[-1], "title": title, "posted_on": posted, "deadline": None,
            "url": link, "poster": c.pick(raw, "creator")}

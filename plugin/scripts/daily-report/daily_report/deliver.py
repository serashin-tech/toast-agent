"""전달물 두 가지: 신규 알림 메일 본문(D30)과 입찰 현황판 HTML(D28). 모든 입력 문자열은 esc()를 거친다.

메일은 메일 앱이 스크립트와 외부 CSS를 지우므로 인라인 스타일만 쓴다. 현황판은 공유될 수 있으므로
대표 메모와 시트 주소를 싣지 않는다.
"""
from .inputs import parse_date
from .render import SECTIONS, days_left, dday, esc, failures, link, won

REVIEWING = ("2차 검토 요청", "2차 검토 중", "2차 완료", "데모 요청", "데모 완료")  # 맨 위에 둘 상태(D26)
LATER = ("신규", "보류", "관련 없음")
FONT = '"Pretendard","Malgun Gothic","맑은 고딕",sans-serif'


def _meta(it, run_date):
    x, parts = it.get("extra") or {}, []
    if x.get("agency"):
        parts.append(esc(x["agency"]))
    if it["kind"] == "bid":
        parts.append(won(x.get("est_price")))
    if x.get("poster"):
        parts.append("작성자 " + esc(x["poster"]))
    n = days_left(it, run_date)
    if n is not None:
        parts.append(f"마감 {esc(it['deadline'])} ({dday(n)})")
    return " · ".join(parts)


def render_mail(run_date, agents, board_url=None, sheet_url=None):
    """반환: {"subject", "html", "count"}."""
    items = [it for a in agents if a["ok"] for it in a["items"] if it["is_new"]]
    p = f'<p style="margin:0 0 12px">'
    out = [f'<div style="font-family:{FONT};word-break:keep-all;line-height:1.6;max-width:640px">']
    fails = failures(agents)
    if fails:
        lis = "".join(f"<li>{esc(label)}: {esc(reason)} (마지막 정상 수집 {esc(last)})</li>"
                      for label, reason, last, _ in fails)
        out.append(f'<div style="border:1px solid #c62828;padding:8px 12px;margin:0 0 16px">'
                   f"<strong>오늘 수집하지 못한 소스</strong><ul>{lis}</ul>"
                   "이 소스에 새 공고가 없다는 뜻이 아닙니다.</div>")
    if not any(a["ok"] for a in agents):
        out.append(p + "오늘 결과 파일을 확인하지 못했습니다. 실행 기록을 확인해 주십시오.</p>")
    changed = sum(s.get("changed_shown_count") or 0 for a in agents if a["ok"] for s in a["sources"])
    if changed:
        out.append(p + f"이미 보신 공고 {changed}건의 내용이 바뀌었습니다(시트에서 확인).</p>")
    for sid, title, source_ids in SECTIONS:
        its = [it for it in items if it["source"] in source_ids or (sid == "grant" and it["kind"] == "grant")]
        body = "".join(f'<li style="margin:0 0 8px">'
                       + ("<strong>[다시 알림: 검토를 요청하신 공고의 내용이 바뀌었습니다]</strong> " if it.get("renotify") else "")
                       + f'{link(it["title"], it["url"])}<br>'
                       f'<span style="color:#5f6672">{_meta(it, run_date)}</span></li>' for it in its)
        out.append(f'<h2 style="font-size:16px;margin:16px 0 8px">{esc(title)} {len(its)}건</h2>'
                   + (f"<ul>{body}</ul>" if its else p + "새 항목이 없습니다.</p>"))
    links = [link("입찰 현황판 열기", board_url) if board_url else "", link("수집 이력 시트 열기", sheet_url) if sheet_url else ""]
    if any(links):
        out.append(p + " · ".join(x for x in links if x) + "</p>")
    out.append("</div>")
    return {"subject": f"[토스트] {run_date.isoformat()} 새 정보 {len(items)}건", "html": "".join(out), "count": len(items)}


def _rank(status):
    s = status or "신규"
    for i, name in enumerate(REVIEWING + LATER):
        if s.startswith(name):
            return i
    return len(REVIEWING)  # 모르는 값은 검토 중 바로 뒤에 둔다


BOARD_CSS = """:root{color-scheme:light dark;--bg:#fff;--ink:#16181d;--muted:#5f6672;--line:#d4d8df;--link:#1a56c4}
@media (prefers-color-scheme:dark){:root{--bg:#14161a;--ink:#f1f2f4;--muted:#a3aab6;--line:#3a3f48;--link:#8ab4ff}}
body{margin:0;background:var(--bg);color:var(--ink);font-family:%s;line-height:1.6;word-break:keep-all;overflow-wrap:break-word}
main{max-width:640px;margin:0 auto;padding:16px}h1{font-size:20px}h2{font-size:16px;border-bottom:1px solid var(--line);padding-bottom:4px}
ul{padding-left:18px}li{margin:0 0 10px}a{color:var(--link)}.m{color:var(--muted);font-size:14px}""" % FONT


def render_board(run_date, rows):
    """시트 행(Apps Script GET 응답의 rows)으로 입찰 현황판 HTML을 만든다. 마감 전 입찰공고만 싣는다."""
    open_bids = []
    for r in rows or []:
        d = parse_date(r.get("deadline")) if r.get("deadline") else None
        if r.get("kind") == "bid" and (d is None or d >= run_date):
            open_bids.append({**r, "_d": d})
    groups = {}
    for r in sorted(open_bids, key=lambda r: (_rank(r.get("status")), r["_d"] or run_date.max)):
        groups.setdefault(r.get("status") or "신규", []).append(r)
    parts = [f"<h1>입찰 현황판</h1><p class=\"m\">{run_date.isoformat()} 기준 · 마감 전 입찰공고 {len(open_bids)}건</p>"]
    if not open_bids:
        parts.append("<p>마감 전인 입찰공고가 없습니다.</p>")
    for status, rs in groups.items():
        lis = "".join(
            f"<li>{link(r.get('title'), r.get('url'))}<br><span class=\"m\">{esc(r.get('agency') or '')}"
            + (f" · 마감 {esc(r['deadline'])} ({dday((r['_d'] - run_date).days)})" if r["_d"] else "")
            + "</span></li>" for r in rs)
        parts.append(f"<section><h2>{esc(status)} {len(rs)}건</h2><ul>{lis}</ul></section>")
    return ("<!doctype html><html lang=\"ko\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>입찰 현황판</title>"
            f"<style>{BOARD_CSS}</style></head><body><main>{''.join(parts)}</main></body></html>")

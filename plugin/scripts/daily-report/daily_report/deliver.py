"""전달물 두 가지: 신규 알림 메일 본문(D30)과 입찰 현황판 HTML(D28). 모든 입력 문자열은 esc()를 거친다.

메일은 메일 앱이 스크립트와 외부 CSS를 지우므로 인라인 스타일만 쓴다. 현황판은 공유될 수 있으므로
대표 메모와 시트 주소를 싣지 않는다.
"""
from .inputs import parse_date
from .render import SECTIONS, SOON_DAYS, days_left, dday, esc, failures, link, won

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


_EMPTY = ("", "(빈 값)", "(없음)", "없음")


def _what_changed(before, after):
    """쉼표 목록 값(키워드 등)은 더하고 뺀 것만, 그 밖의 값은 '전 → 후'로 적는다(D35, US 14)."""
    before, after = (before or "").strip(), (after or "").strip()
    if "," not in before + after:
        return f"{esc(before)} → {esc(after)}"
    old, new = ([] if v in _EMPTY else [x.strip() for x in v.split(",") if x.strip()] for v in (before, after))
    added, removed = [x for x in new if x not in old], [x for x in old if x not in new]
    parts = (["+" + esc(", ".join(added))] if added else []) + (["−" + esc(", ".join(removed))] if removed else [])
    return " ".join(parts) or "순서만 바뀜"


def _changes(changes, counts):
    """최근 설정 변경 한 줄과 전날 대비 건수(D35). 변경이 없으면 빈 문자열."""
    if not changes:
        return ""

    lines = "; ".join(f'{esc(c["일자"])} {esc(c["항목"])}: {_what_changed(c["변경 전"], c["변경 후"])} ({esc(c["사유"])})'
                      for c in changes)
    html = f'<div style="background:#fff6dc;padding:8px 12px;margin:0 0 16px"><strong>최근 설정 변경</strong> {lines}'
    if counts:
        (ti, pi), (te, pe) = counts["included"], counts["excluded"]
        html += (f"<br><strong>전날 대비</strong> 포함 {ti}건 (전날 {pi}건, {ti - pi:+d}건), 제외 {te}건 (전날 {pe}건, {te - pe:+d}건). "
                 "수집에 성공한 소스만 비교합니다.")
    return html + "</div>"


def _sort_key(run_date):
    def key(it):  # 마감이 가까운 순, 마감 없음은 뒤(D35)
        n = days_left(it, run_date)
        return (n is None, n or 0)
    return key


def _soon(it, run_date):
    n = days_left(it, run_date)
    return n is not None and 0 <= n <= SOON_DAYS


def render_mail(run_date, agents, board_url=None, sheet_url=None, changes=None, counts=None):
    """반환: {"subject", "html", "count"}. changes·counts는 최근 설정 변경 줄(D35)의 입력이다."""
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
    warns = [w for a in agents if a["ok"] for w in a.get("warnings") or []]
    if warns:
        out.append('<div style="border:1px solid #b26a00;padding:8px 12px;margin:0 0 16px"><strong>확인이 필요한 점</strong>'
                   f"<ul>{''.join(f'<li>{esc(w)}</li>' for w in warns)}</ul></div>")
    out.append(_changes(changes, counts))
    if not any(a["ok"] for a in agents):
        out.append(p + "오늘 결과 파일을 확인하지 못했습니다. 실행 기록을 확인해 주십시오.</p>")
    elif not items:
        out.append(p + ("오늘은 새 공고가 없습니다.</p>" if not fails else "수집에 성공한 소스에는 오늘 새 항목이 없습니다.</p>"))
    changed = sum(s.get("changed_shown_count") or 0 for a in agents if a["ok"] for s in a["sources"])
    if changed:
        out.append(p + f"이미 보신 공고 {changed}건의 내용이 바뀌었습니다(시트에서 확인).</p>")
    for sid, title, source_ids in SECTIONS:
        its = sorted((it for it in items if it["source"] in source_ids or (sid == "grant" and it["kind"] == "grant")),
                     key=_sort_key(run_date))
        broken = [f for f in fails if f[3] is None or f[3] in source_ids]  # 에이전트 전체 실패는 모든 절에 걸린다
        note = (p + "수집 실패: " + ", ".join(f"{esc(f[0])}({esc(f[1])})" for f in broken) + "</p>") if broken else ""
        body = "".join(f'<li style="margin:0 0 8px">'
                       + ("<strong>[다시 알림: 검토를 요청하신 공고의 내용이 바뀌었습니다]</strong> " if it.get("renotify") else "")
                       + ('<strong style="color:#b26a00">[마감 임박]</strong> ' if _soon(it, run_date) else "")
                       + f'{link(it["title"], it["url"])}<br>'
                       + (f'<span>AI 요약: {esc(it["summary"])}</span><br>' if it.get("summary") else "")
                       + f'<span style="color:#5f6672">{_meta(it, run_date)}</span></li>' for it in its)
        empty = "" if broken else p + "새 항목이 없습니다.</p>"
        out.append(f'<h2 style="font-size:16px;margin:16px 0 8px">{esc(title)} {len(its)}건</h2>'
                   + note + (f"<ul>{body}</ul>" if its else empty))
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

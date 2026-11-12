"""전달물 두 가지: 신규 알림 메일 본문(D30)과 사업 현황판(D28, 설명서의 첫 탭). 모든 입력 문자열은 esc()를 거친다.

메일은 메일 앱이 스크립트와 외부 CSS를 지우므로 인라인 스타일만 쓴다. 현황판은 공유될 수 있으므로
대표 메모를 싣지 않는다. 시트 주소는 싣는다(시트 권한이 있는 계정만 열 수 있음, 2026-11-12 sera.shin 지시).
"""
import pathlib
import re

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
    links = [link("사업 현황판 열기", board_url) if board_url else "", link("수집 이력 시트 열기", sheet_url) if sheet_url else ""]
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


# 사업 현황판은 설명서(manual.html)의 첫 탭이다. 루틴이 시트 행으로 탭 내용을 채운 설명서 전체를 게시한다(D28 개정).
MANUAL = pathlib.Path(__file__).with_name("manual.html")
BOARD_MARK = "<!--BOARD-->"


def _open_rows(rows, kind, run_date):
    out = []
    for r in rows or []:
        d = parse_date(r.get("deadline")) if r.get("deadline") else None
        if r.get("kind") == kind and (d is None or d >= run_date):
            out.append({**r, "_d": d})
    return out


def _due(r, run_date):
    return f"{esc(r['deadline'])} ({dday((r['_d'] - run_date).days)})" if r["_d"] else "마감일 없음"


PICK = ("신규", "2차 검토 요청", "데모 요청", "보류", "관련 없음")  # 대표가 고르는 상태(D26·D32·D34). 나머지는 에이전트가 쓴다
KIND = {"bid": "입찰", "grant": "지원"}


def _pick(r, run_date):
    """상태 선택 목록(D38). 설명서의 스크립트가 보는 사람의 Google Sheets 커넥터를 확인한 뒤에 켜고,
    고르면 시트의 상태 칸에 바로 저장한다. 에이전트가 쓴 값('2차 완료(권고)' 등)은 그대로 선택돼 보인다."""
    s = r.get("status") or "신규"
    opts = "".join(f'<option value="{esc(o)}"{" selected" if o == s else ""}>{esc(o)}</option>'
                   for o in (PICK if s in PICK else (s,) + PICK))
    return (f'<select class="inp bstatus" data-key="{esc(r.get("key") or "")}" data-memo="{"1" if _watched_memo(r) else ""}" '
            f'data-deadline="{esc(r["_d"] or "")}" data-due="{_due(r, run_date)}" data-kind="{KIND.get(r.get("kind"), "")}" '
            f'data-agency="{esc(r.get("agency") or "")}" aria-label="상태: {esc(r.get("title") or "")}" disabled>{opts}</select>')


def _bid_tab(bids, run_date):
    """입찰공고를 상태별로 묶는다. 검토 중인 상태가 맨 위, 같은 상태 안에서는 마감이 가까운 순."""
    if not bids:
        return "<p>마감 전인 입찰공고가 없습니다.</p>"
    groups = {}
    for r in sorted(bids, key=lambda r: (_rank(r.get("status")), r["_d"] or run_date.max)):
        groups.setdefault(r.get("status") or "신규", []).append(r)
    return "".join(
        f"<h3>{esc(status)} {len(rs)}건</h3><ul>"
        + "".join(f'<li>{_pick(r, run_date)} {link(r.get("title"), r.get("url"))}<br><span class="m">{esc(r.get("agency") or "")}'
                  f" · 마감 {_due(r, run_date)}</span></li>" for r in rs)
        + "</ul>" for status, rs in groups.items())


def _grant_tab(grants, run_date):
    """지원사업 표. 날짜 기준(마감일·등록일)과 기간, 상태, 기관으로 거르고 등록일·마감일 머리를 눌러 정렬한다.
    거르기와 정렬은 설명서의 스크립트가 움직인다. 처음 순서는 마감일 오름차순이다."""
    if not grants:
        return "<p>마감 전인 지원사업이 없습니다.</p>"
    statuses = sorted({r.get("status") or "신규" for r in grants}, key=_rank)
    opts = "".join(f'<option value="{esc(s)}">{esc(s)}</option>' for s in statuses)
    agencies = sorted({r.get("agency") for r in grants if r.get("agency")})
    agency_opts = "".join(f'<option value="{esc(a)}">{esc(a)}</option>' for a in agencies)
    trs = []
    for r in sorted(grants, key=lambda r: (r["_d"] is None, r["_d"] or run_date)):
        reg = parse_date(r.get("registered")) if r.get("registered") else None
        trs.append(f'<tr data-deadline="{esc(r["_d"] or "")}" data-registered="{esc(reg or "")}" data-status="{esc(r.get("status") or "신규")}" '
                   f'data-agency="{esc(r.get("agency") or "")}"><td>{_pick(r, run_date)}</td><td>{link(r.get("title"), r.get("url"))}</td>'
                   f'<td>{esc(r.get("agency") or "")}</td><td>{esc(reg or "")}</td><td>{_due(r, run_date)}</td></tr>')
    sort_th = lambda key, name, order: (f'<th aria-sort="{order}"><button class="sortbtn" type="button" data-sort="{key}">'
                                        f'{name}<span class="si" aria-hidden="true"></span></button></th>')
    return ('<div class="bfilter">'
            '<label>날짜 기준<select class="inp" id="bf-basis"><option value="deadline">마감일</option><option value="registered">등록일</option></select></label>'
            '<label>시작<input class="inp" type="date" id="bf-from"></label>'
            '<label>끝<input class="inp" type="date" id="bf-to"></label>'
            f'<label>상태<select class="inp" id="bf-status"><option value="">전체</option>{opts}</select></label>'
            f'<label>기관<select class="inp" id="bf-agency"><option value="">전체</option>{agency_opts}</select></label>'
            '<button class="ebtn" type="button" id="bf-reset">초기화</button>'
            f'<span class="small" id="bf-count" aria-live="polite">{len(grants)}건 표시</span></div>'
            '<div class="scroll"><table class="tbl grant-tbl"><thead><tr><th>상태</th><th>사업명</th><th>기관</th>'
            + sort_th("registered", "등록일", "none") + sort_th("deadline", "마감일", "ascending") + "</tr></thead>"
            f'<tbody>{"".join(trs)}<tr class="bf-none" hidden><td colspan="5">조건에 맞는 지원사업이 없습니다.</td></tr></tbody></table></div>')


def _watched(r):
    """관심사업: 대표가 상태를 바꿨거나(체크) 메모를 남긴 행. '관련 없음'은 관심이 없다는 뜻이라 뺀다(2026-11-12 sera.shin 지시)."""
    status = r.get("status") or "신규"
    return status != "관련 없음" and (status != "신규" or _watched_memo(r))


def _watch_tab(rows, run_date):
    """마감 전 관심사업(입찰·지원) 표. 마감이 가까운 순. 메모는 있는지만 보이고 내용은 싣지 않는다.
    표는 비어 있어도 둔다: 현황판에서 상태를 고르면 스크립트가 이 표에 행을 넣고 뺀다(D38)."""
    trs = "".join(
        f'<tr data-key="{esc(r.get("key") or "")}"><td>{_pick(r, run_date)}</td><td>{_due(r, run_date)}</td><td>{link(r.get("title"), r.get("url"))}</td>'
        f'<td>{KIND[r["kind"]]}</td><td>{esc(r.get("agency") or "")}</td><td>{"메모 있음" if _watched_memo(r) else ""}</td></tr>'
        for r in sorted(rows, key=lambda r: (r["_d"] is None, r["_d"] or run_date)))
    none = ('<tr class="bf-none"' + (" hidden" if rows else "") + '><td colspan="6">마감 전인 관심사업이 없습니다. '
            "상태를 바꾸거나 메모를 남긴 사업이 여기에 모입니다.</td></tr>")
    return ('<p class="small" style="padding:12px 18px 0;margin:0">상태를 바꾸거나 메모를 남긴 마감 전 사업. 메모 내용은 시트에서 확인.</p>'
            '<div class="scroll"><table class="tbl board-tbl"><thead><tr><th>상태</th><th>마감일</th><th>사업명</th><th>종류</th><th>기관</th><th>메모</th></tr></thead>'
            f"<tbody>{trs}{none}</tbody></table></div>")


def _watched_memo(r):
    return r.get("has_memo") is True or str(r.get("has_memo")).lower() == "true"


def render_board(run_date, rows, sheet_url=None):
    """시트 행(Apps Script 응답의 rows)으로 사업 현황판 탭을 채운 설명서 HTML을 만든다. 민간 외주 글은 싣지 않는다."""
    bids, grants = _open_rows(rows, "bid", run_date), _open_rows(rows, "grant", run_date)
    watch = [r for r in bids + grants if _watched(r)]
    sheet = (f"수집 이력 시트: {link('시트 열기', sheet_url)} (권한이 있는 Google 계정으로만 열림). "
             "마감이 지난 기존 기록은 시트의 '지난 공고' 탭에서 확인." if sheet_url
             else "수집 이력 시트 주소가 설정되지 않았습니다(작업 폴더 .env의 SHEET_URL).")
    m = re.search(r"/spreadsheets/d/([^/?#]+)", sheet_url or "")
    sheet_id = f' data-sheet-id="{esc(m.group(1))}"' if m else ""  # 시트 주소에 이미 보이는 값이고 토큰이 아니다(D30)
    tab = lambda k, name, n, on: (f'<button class="subtab" role="tab" type="button" id="bt-{k}" aria-controls="bp-{k}" '
                                  f'aria-selected="{"true" if on else "false"}">{name} <span class="n">{n}</span></button>')
    panel = ("<!--board-start--><section><h2>사업 현황판</h2>"
             f'<p class="sub">{run_date.isoformat()} 기준 · 마감 전 입찰사업 {len(bids)}건 · 지원사업 {len(grants)}건 · 관심사업 {len(watch)}건. '
             "10시 루틴과 30분 검토 루틴이 시트를 읽어 다시 게시함(시트에서 바꾼 상태는 최대 30분 늦게 보임). "
             "상태 칸에서 고르면 시트에 바로 저장되고, '신규'·'관련 없음'이 아니면 관심사업에 들어감(Google Sheets 커넥터 필요).</p>"
             f'<p class="sub">{sheet}</p><p class="sub" id="bsave" role="status" aria-live="polite"></p></section>'
             f'<section class="subwrap"{sheet_id}><div class="subtabs" role="tablist" aria-label="사업 종류">'
             + tab("bid", "입찰사업", len(bids), True) + tab("grant", "지원사업", len(grants), False)
             + tab("watch", "관심사업", len(watch), False) + "</div>"
             f'<div class="setcard blist" role="tabpanel" id="bp-bid" aria-labelledby="bt-bid">{_bid_tab(bids, run_date)}</div><!--bp-bid-->'
             f'<div class="setcard" role="tabpanel" id="bp-grant" aria-labelledby="bt-grant" hidden>{_grant_tab(grants, run_date)}</div><!--bp-grant-->'
             f'<div class="setcard" role="tabpanel" id="bp-watch" aria-labelledby="bt-watch" hidden>{_watch_tab(watch, run_date)}</div><!--bp-watch-->'
             "</section><!--board-end-->")
    manual = MANUAL.read_text(encoding="utf-8")
    if BOARD_MARK not in manual:
        raise ValueError("manual.html에 사업 현황판 자리(<!--BOARD-->)가 없습니다")
    return manual.replace(BOARD_MARK, panel, 1)

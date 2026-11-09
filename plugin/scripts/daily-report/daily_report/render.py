"""보고서 HTML 한 장 만들기. 모든 입력 문자열은 esc()를 거쳐 넣는다."""
import html as _html
import re

from .inputs import parse_date, parse_dt

AGENT_LABEL = {"gov": "정부사업", "market": "시장 정보"}
REASON = {
    "auth": "인증 오류", "pending_approval": "승인 대기", "rate_limit": "호출 한도 초과",
    "network": "네트워크 오류", "format": "형식 오류", "missing": "결과 없음", "limit_near": "한도 임박으로 중단",
}
GRANT_ORIGIN = {"grant_bizinfo": "중소기업 지원사업", "grant_kocca": "한콘진"}
OVERALL = {"recommend": "참여 권고", "conditional": "조건부", "not_recommend": "비권고", "extract_only": "요건만 추출"}
VERDICT = {"met": "충족", "unmet": "미충족", "needs_check": "확인필요", "extract_only": "요건 추출"}
SOON_DAYS = 7
# 절 구성: (id, 제목, 이 절에 데이터를 주는 소스 id들). 시장 정보 절은 market-agent spec에서 정한다.
SECTIONS = (
    ("bid", "입찰공고", ("bid",)),
    ("grant", "지원사업", ("grant_kocca", "grant_bizinfo")),
    ("outsource", "민간 외주", ("outsource_cglink",)),
)

# 모든 CSS는 한 파일 안에 둔다. 외부 글꼴은 불러오지 않고 시스템에 있는 글꼴로 대체한다.
CSS = """
:root{color-scheme:light dark;--bg:#fff;--ink:#16181d;--body:#3d424c;--muted:#5f6672;--line:#d4d8df;--soft:#f5f6f8;--link:#1a56c4;
--warn-bg:#fdecec;--warn-line:#c62828;--note-bg:#fff6dc;--chip:#e8ebf0;--measure:640px}
@media (prefers-color-scheme:dark){:root{--bg:#14161a;--ink:#f1f2f4;--body:#c9cdd4;--muted:#a3aab6;--line:#3a3f48;--soft:#1e2127;--link:#8ab4ff;
--warn-bg:#3a1b1b;--warn-line:#ff8a80;--note-bg:#33290f;--chip:#2a2e36}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--body);font-family:"Pretendard",-apple-system,BlinkMacSystemFont,"Malgun Gothic","맑은 고딕","Segoe UI",sans-serif;
font-size:15px;line-height:1.65;word-break:keep-all;overflow-wrap:break-word;line-break:strict;text-wrap:pretty}
.page{max-width:var(--measure);margin:0 auto;padding:16px}
h1,h2,h3{color:var(--ink);line-height:1.3;text-wrap:balance;margin:0}
h1{font-size:24px;margin:8px 0 16px}h2{font-size:19px}h3{font-size:16px}
section{margin:0 0 24px}
a{color:var(--link)}
a:focus-visible,summary:focus-visible,button:focus-visible,select:focus-visible,input:focus-visible{outline:3px solid var(--link);outline-offset:2px}
.banner{border:2px solid var(--warn-line);background:var(--warn-bg);border-radius:8px;padding:12px 16px}
.banner h2{margin-bottom:4px}.banner ul{margin:8px 0 0;padding-left:20px}
.fail{border-left:4px solid var(--warn-line);background:var(--warn-bg);padding:8px 12px;margin:8px 0}
.empty{color:var(--muted);margin:8px 0}
.empty-day{font-size:18px;font-weight:700;color:var(--ink);border:1px dashed var(--line);border-radius:8px;padding:16px;text-align:center}
.rule{color:var(--muted);font-size:14px;margin:4px 0 12px}
.changes{background:var(--note-bg);border-radius:8px;padding:8px 12px;margin:0 0 16px}
.item{border:1px solid var(--line);background:var(--soft);border-radius:8px;padding:12px;margin:0 0 12px}
.item[hidden]{display:none}
.meta{display:grid;grid-template-columns:max-content minmax(0,1fr);gap:2px 12px;margin:8px 0 0}
.meta dt{color:var(--muted)}.meta dd{margin:0;min-width:0;overflow-wrap:anywhere}
.tag{display:inline-block;font-size:12px;line-height:1.5;border:1px solid var(--line);border-radius:4px;padding:0 6px;background:var(--chip);color:var(--ink)}
.summary,.src{margin:8px 0 0}
summary{cursor:pointer;min-height:44px;display:flex;align-items:center}
summary h2{display:inline}
details.elig{margin-top:8px;border-top:1px solid var(--line)}
.reqs{padding-left:20px;margin:8px 0}.reqs li{margin:0 0 8px}
blockquote{margin:4px 0 0;padding:4px 12px;border-left:3px solid var(--line)}
cite{color:var(--muted);font-style:normal}
.disclaimer{font-weight:600;color:var(--ink)}
.toolbar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 16px}
.toolbar[hidden]{display:none}
.toolbar select,.toolbar button,.toolbar label{min-height:44px;font:inherit;display:inline-flex;align-items:center;gap:6px}
.toolbar select,.toolbar button{padding:0 12px;border:1px solid var(--line);border-radius:8px;background:var(--soft);color:var(--ink)}
.foot{color:var(--muted);font-size:13px}
"""


TOOLBAR = (
    '<div id="viewbar" class="toolbar" hidden role="group" aria-label="보기 설정">'
    '<label>정렬 <select id="sort"><option value="default">보고서 순서</option>'
    '<option value="deadline">마감순</option><option value="posted">등록일순</option></select></label>'
    '<label><input type="checkbox" id="soon-only"> 마감 임박만 보기</label>'
    '<button type="button" id="fold-all">모두 접기</button><button type="button" id="unfold-all">모두 펼치기</button></div>'
)

# 보기 위젯: 화면 안에서만 바뀐다. 아무것도 저장하거나 내려받거나 불러오지 않는다.
# 스크립트가 꺼져 있으면 도구 모음은 숨겨진 채로 남고, 보고서는 details만으로 읽힌다.
SCRIPT = """
(function () {
  var bar = document.getElementById('viewbar');
  if (!bar) return;
  bar.hidden = false;
  var sort = document.getElementById('sort'), soonOnly = document.getElementById('soon-only');
  var boxes = [].slice.call(document.querySelectorAll('.items'));
  boxes.forEach(function (box) {
    [].forEach.call(box.children, function (el, i) { el.setAttribute('data-order', i); });
  });
  function cmp(mode) {
    return function (a, b) {
      var k = mode === 'posted' ? 'data-posted' : 'data-deadline', x = a.getAttribute(k), y = b.getAttribute(k);
      if (mode !== 'default' && x !== y) {
        if (!x) return 1;
        if (!y) return -1;
        return mode === 'posted' ? (x < y ? 1 : -1) : (x < y ? -1 : 1);
      }
      return a.getAttribute('data-order') - b.getAttribute('data-order');
    };
  }
  function apply() {
    boxes.forEach(function (box) {
      var els = [].slice.call(box.children).filter(function (e) { return e.classList.contains('item'); });
      els.sort(cmp(sort.value)).forEach(function (e) { box.appendChild(e); });
    });
    [].forEach.call(document.querySelectorAll('.item'), function (e) {
      e.hidden = soonOnly.checked && e.getAttribute('data-soon') !== '1';
    });
  }
  function fold(open) {
    [].forEach.call(document.querySelectorAll('details.srcsec'), function (d) { d.open = open; });
  }
  sort.addEventListener('change', apply);
  soonOnly.addEventListener('change', apply);
  document.getElementById('fold-all').addEventListener('click', function () { fold(false); });
  document.getElementById('unfold-all').addEventListener('click', function () { fold(true); });
})();
"""


def esc(v):
    return _html.escape("" if v is None else str(v), quote=True)


def fmt_dt(v):
    d = parse_dt(v) if v else None
    return d.strftime("%Y-%m-%d %H:%M") if d else "기록 없음"


_KEY_PARAM = re.compile(r"([?&])(?:service[_-]?key|api[_-]?key|auth[_-]?key|crtfc[_-]?key|key)=[^&#\s]*&?", re.I)


def safe_url(u):
    """http/https만 링크로 쓴다. 주소에 섞인 인증키 모양의 매개변수는 지운다. 안전하지 않으면 None."""
    u = _KEY_PARAM.sub(r"\1", "" if u is None else str(u).strip()).rstrip("?&")
    return u if re.match(r"https?://", u, re.I) else None


def link(label, url):
    u = safe_url(url)
    if u:
        return f'<a href="{esc(u)}" rel="noopener noreferrer">{esc(label)}</a>'
    return f'{esc(label)} <span class="nolink">(링크 없음: 안전하지 않은 주소)</span>'


def won(v):
    return f"{v:,}원" if isinstance(v, int) and not isinstance(v, bool) else "미기재"


def days_left(it, run_date):
    d = parse_date(it["deadline"]) if it["deadline"] else None
    return (d - run_date).days if d else None


def dday(n):
    return "마감 지남" if n < 0 else "D-day" if n == 0 else f"D-{n}"


def failures(agents):
    """실패한 에이전트와 소스를 [(라벨, 사유, 마지막 정상 수집, 소스 id)]로 모은다. 에이전트 전체 실패는 소스 id가 None이다."""
    out = []
    for a in agents:
        if not a["ok"]:
            out.append((AGENT_LABEL.get(a["agent"], a["agent"]) + " 에이전트 전체", REASON[a["error"]], "확인 불가", None))
            continue
        for s in a["sources"]:
            if s["status"] == "ok":
                continue
            kind = (s["error"] or {}).get("kind")
            reason = REASON["limit_near"] if s["status"] == "limit_near" else REASON.get(kind, "원인 미상")
            out.append((s["label"] or s["id"], reason, fmt_dt(s["last_success_at"]), s["id"]))
    return out


def _banner(fails):
    if not fails:
        return ""
    lis = "".join(
        f"<li><strong>{esc(label)}</strong> · {esc(reason)} · 마지막 정상 수집 {esc(last)}</li>"
        for label, reason, last, _ in fails
    )
    return (
        '<section id="failures" class="banner" role="alert"><h2>수집 실패 소스</h2>'
        "<p>아래 소스는 오늘 수집하지 못했습니다. 이 소스에 새 공고가 없다는 뜻이 아닙니다.</p>"
        f"<ul>{lis}</ul></section>"
    )


def _row(label, value_html):
    return f"<dt>{esc(label)}</dt><dd>{value_html}</dd>"


def _meta(it, run_date):
    x, n = it["extra"], days_left(it, run_date)
    deadline = (esc(it["deadline"]) + (f" ({dday(n)})" if n is not None else "")) if it["deadline"] else "미기재"
    if it["kind"] == "bid":
        kws = "".join(f'<span class="tag">{esc(k)}</span> ' for k in it["matched_keywords"]) or "없음"
        rows = [_row("기관", esc(x["agency"] or "미기재")), _row("추정가격", won(x["est_price"])),
                _row("마감일", deadline), _row("일치 키워드", kws)]
    elif it["kind"] == "outsource":
        rows = [_row("게시일", esc(it["posted_on"] or "미기재")), _row("게시자", esc(x["poster"] or "미기재")),
                _row("출처", "CGLink 외주발주 게시판")]
    else:
        period = f"{esc(x['period_start'] or '?')} ~ {esc(x['period_end'] or it['deadline'] or '?')}"
        origins = x["origins"] if isinstance(x["origins"], list) else []
        rows = [_row("접수 기간", period), _row("마감", dday(n) if n is not None else "미기재"),
                _row("기관", esc(x["agency"] or "미기재")),
                _row("출처", ", ".join(esc(GRANT_ORIGIN.get(o, o)) for o in origins) or "미기재")]
    return f'<dl class="meta">{"".join(rows)}</dl>'


def _eligibility(e):
    reqs = ""
    for r in e["requirements"]:
        ev = r["evidence"] if isinstance(r["evidence"], dict) else {}
        quote = ""
        if ev.get("quote"):
            quote = (f'<blockquote><span class="tag">공고문 근거</span> {esc(ev["quote"])}'
                     f' <cite>{esc(ev.get("location"))}</cite></blockquote>')
        reqs += (f'<li><span class="tag v-{esc(r["verdict"])}">{esc(VERDICT.get(r["verdict"], r["verdict"]))}</span> '
                 f'<strong>{esc(r["category"])}</strong> {esc(r["text"])}{quote}</li>')
    note = ""
    if e["overall"] == "extract_only":
        note = '<p class="note">요건만 추출했고 회사 정보와 대조하지 않았습니다.</p>'
    files = ""
    if e["unreadable_files"]:
        files = "<p>변환하지 못한 첨부: " + ", ".join(link(f["name"] or "첨부", f["url"]) for f in e["unreadable_files"]) + "</p>"
    return (f'<details class="elig"><summary>제안 가능성 검토 · {esc(OVERALL.get(e["overall"], e["overall"]))}</summary>'
            f'{note}<p>{esc(e["reason"])}</p><ul class="reqs">{reqs}</ul>{files}'
            f'<p class="disclaimer">{esc(e["disclaimer"] or "최종 판단은 대표가 합니다.")}</p></details>')


def card(it, run_date, elig):
    n = days_left(it, run_date)
    summary = ""
    if it["summary"]:
        summary = f'<p class="summary"><span class="tag">에이전트 요약</span> {esc(it["summary"])}</p>'
    review = _eligibility(elig[it["id"]]) if it["kind"] == "bid" and it["id"] in elig else ""
    return (
        f'<article class="item" data-id="{esc(it["id"])}" data-kind="{esc(it["kind"])}" '
        f'data-deadline="{esc(it["deadline"] or "")}" data-posted="{esc(it["posted_on"] or "")}" '
        f'data-soon="{int(n is not None and 0 <= n <= SOON_DAYS)}" data-new="{int(it["is_new"])}">'
        f'<h3 class="t">{esc(it["title"])}</h3>{_meta(it, run_date)}{summary}'
        f'<p class="src">{link("원문 보기", it["url"])}</p>{review}</article>'
    )


def pick_top(items, run_date, limit=3):
    # 가정(대표가 정한 기준이 아님): 오늘 볼 3건 = 새 입찰공고와 지원사업 중 마감이 가까운 순(마감 없음은 뒤),
    # 같으면 일치 키워드가 많은 순. 이미 마감이 지난 항목은 고르지 않는다.
    cand = [i for i in items if i["kind"] in ("bid", "grant") and i["is_new"]
            and (days_left(i, run_date) is None or days_left(i, run_date) >= 0)]

    def key(i):
        n = days_left(i, run_date)
        return (n is None, n or 0, -len(i["matched_keywords"]))
    return sorted(cand, key=key)[:limit]


def pick_soon(items, run_date):
    # 가정(대표가 정한 기준이 아님): 마감 임박 = 마감까지 0~7일인 입찰공고와 지원사업.
    cand = [i for i in items if i["kind"] in ("bid", "grant") and days_left(i, run_date) is not None
            and 0 <= days_left(i, run_date) <= SOON_DAYS]
    return sorted(cand, key=lambda i: days_left(i, run_date))


def _section(sid, title, source_ids, items, fails, run_date, top_keys, elig):
    broken = [f for f in fails if f[3] is None or f[3] in source_ids]
    mine = [i for i in items if i["kind"] == sid]
    body = ""
    if broken:
        names = ", ".join(f"{esc(f[0])}({esc(f[1])})" for f in broken)
        body += f'<p class="fail">수집 실패: {names}</p>'
    elif not any(i["is_new"] for i in mine):
        body += '<p class="empty">새 항목 없음</p>'
    rest = [i for i in mine if (i["kind"], i["id"]) not in top_keys]
    rest.sort(key=lambda i: (not i["is_new"], days_left(i, run_date) is None, days_left(i, run_date) or 0))
    if rest:
        cards = "".join(card(i, run_date, elig) for i in rest)
        body += (f'<details class="rest"><summary>나머지 {len(rest)}건 보기 (새 항목 {sum(i["is_new"] for i in rest)}건)</summary>'
                 f'<div class="items">{cards}</div></details>')
    return (f'<section id="sec-{sid}" class="sec"><details class="srcsec" open><summary><h2>{esc(title)}</h2></summary>'
            f"{body}</details></section>")


def _changes(changes, counts):
    if not changes:
        return ""
    lines = "; ".join(
        f'{esc(c["일자"])} {esc(c["항목"])}: {esc(c["변경 전"])} → {esc(c["변경 후"])} ({esc(c["사유"])})' for c in changes
    )
    html = f'<section id="changes" class="changes"><p><strong>최근 설정 변경</strong> {lines}</p>'
    if counts:
        (ti, pi), (te, pe) = counts["included"], counts["excluded"]
        html += (f"<p><strong>전날 대비</strong> 포함 {ti}건 (전날 {pi}건, {ti - pi:+d}건), 제외 {te}건 (전날 {pe}건, {te - pe:+d}건). "
                 "수집에 성공한 소스만 비교합니다.</p>")
    return html + "</section>"


def render(run_date, agents, changes=None, counts=None):
    fails = failures(agents)
    items = [i for a in agents for i in a["items"]]
    elig = {e["bid_id"]: e for a in agents for e in a["eligibility"]}
    top, soon = pick_top(items, run_date), pick_soon(items, run_date)
    top_keys = {(i["kind"], i["id"]) for i in top + soon}
    if any(i["is_new"] for i in items):
        status = ""
    elif not fails:
        status = '<p id="status" class="empty-day">오늘은 새 공고가 없습니다.</p>'
    elif any(a["ok"] for a in agents):
        status = '<p id="status" class="empty-day">수집에 성공한 소스에는 오늘 새 항목이 없습니다.</p>'
    else:
        status = '<p id="status" class="empty-day">오늘 결과 파일을 확인하지 못했습니다.</p>'

    def cards(lst):
        return "".join(card(i, run_date, elig) for i in lst) or '<p class="empty">해당 항목이 없습니다.</p>'
    today = ('<section id="today"><h2>오늘 볼 3건</h2><p class="rule">선정 기준: 오늘 새로 들어온 입찰공고와 지원사업 중 '
             "마감이 가까운 순(마감 없음은 뒤)으로 고르고, 마감이 같으면 일치 키워드가 많은 순입니다.</p>"
             f'<div class="items">{cards(top)}</div></section>')
    soon_html = ('<section id="soon"><h2>마감 임박</h2><p class="rule">마감까지 7일 이내인 입찰공고와 지원사업입니다.</p>'
                 f'<div class="items">{cards(soon)}</div></section>')
    sections = "".join(_section(sid, t, ids, items, fails, run_date, top_keys, elig) for sid, t, ids in SECTIONS)
    return (
        '<!doctype html><html lang="ko"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>일일 보고서 {esc(run_date.isoformat())}</title><style>{CSS}</style></head><body>"
        f'<main class="page"><h1>일일 보고서 {esc(run_date.isoformat())}</h1>'
        f"{_banner(fails)}{_changes(changes, counts)}{status}{TOOLBAR}{today}{soon_html}{sections}"
        '<p class="foot">보기 설정은 이 화면에서만 바뀌며 저장되지 않습니다. 에이전트 요약 표시가 없는 문장은 원문 인용입니다.</p>'
        f"</main><script>{SCRIPT}</script></body></html>"
    )

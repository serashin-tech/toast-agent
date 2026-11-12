"""신규 알림 메일(D30)과 사업 현황판(D28)의 경계: 명령줄 입력 -> 메일 JSON, 현황판 HTML."""
import contextlib
import io
import json

from daily_report.cli import main
from helpers import ReportCase

BOARD = "https://claude.ai/artifact/board-1"
SHEET = "https://docs.google.com/spreadsheets/d/sheet-1"


class NewItemsMail(ReportCase):
    def mail(self, *extra):
        out = self.tmp / "mail.json"
        argv = ["mail", "--date", "2026-11-05", "--results", str(self.results), "--out", str(out), *extra]
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(argv), 0)
        return json.loads(out.read_text(encoding="utf-8"))

    def test_sections_links_and_subject(self):
        data = self.put_today()
        m = self.mail("--board-url", BOARD, "--sheet-url", SHEET)
        new = [it for it in data["items"] if it["is_new"]]  # 고정 자료에는 옛 형식의 is_new=false 항목도 있다
        n = len(new)
        self.assertIn("2026-11-05", m["subject"])
        self.assertIn(f"{n}건", m["subject"])
        for title in ("입찰공고", "지원사업", "민간 외주"):
            self.assertIn(title, m["html"])
        for it in new:
            self.assertIn(it["title"], m["html"])
        self.assertIn(BOARD, m["html"])
        self.assertIn(SHEET, m["html"])
        self.assertEqual(m["count"], n)

    def test_failed_source_is_shown_first_and_secrets_never_appear(self):
        self.put_today()
        html = self.mail()["html"]
        self.assertIn("수집하지 못한 소스", html)  # 고정 자료의 한콘진은 rate_limit 실패
        self.assertLess(html.index("수집하지 못한 소스"), html.index("입찰공고"))
        self.assertNotIn("SECRETKEY", html)

    def test_result_warnings_are_shown_at_the_top(self):  # 티켓 22: 숨은 실패를 대표에게도 보인다
        def mutate(d):
            d["warnings"] = ["ledger.json을 읽지 못해 원장을 새로 시작했습니다"]
        self.put_today(mutate)
        html = self.mail()["html"]
        self.assertIn("ledger.json을 읽지 못해", html)
        self.assertLess(html.index("ledger.json"), html.index("입찰공고"))

    def test_summary_is_labelled_as_ai_written(self):  # D33, US-08: 요약과 원문을 구분한다
        def mutate(d):
            d["items"][0]["summary"] = "홍보 애니메이션 <실적과 맞음>"
        self.put_today(mutate)
        html = self.mail()["html"]
        self.assertIn("AI 요약: 홍보 애니메이션 &lt;실적과 맞음&gt;", html)

    def test_renotified_bid_is_marked(self):  # D18
        def mutate(d):
            d["items"][0]["renotify"] = True
        self.put_today(mutate)
        self.assertEqual(self.mail()["html"].count("다시 알림"), 1)

    def test_changed_shown_count_is_one_line(self):
        def mutate(d):
            d["sources"][0]["changed_shown_count"] = 2
        self.put_today(mutate)
        self.assertIn("이미 보신 공고 2건의 내용이 바뀌었습니다", self.mail()["html"])

    def test_sheet_link_comes_from_env_when_not_given(self):  # 스킬은 .env를 읽지 않으므로 코드가 읽는다(D30)
        self.put_today()
        env = self.tmp / ".env"
        env.write_text(f"SHEET_URL={SHEET}\nSHEET_APP_TOKEN=tok\n", encoding="utf-8")
        html = self.mail("--env-file", str(env))["html"]
        self.assertIn(SHEET, html)
        self.assertNotIn("tok", html)

    def test_missing_result_file_says_so_instead_of_no_news(self):
        m = self.mail()
        self.assertEqual(m["count"], 0)
        self.assertIn("결과 파일을 확인하지 못했습니다", m["html"])


ROWS = [
    {"key": "bid:R1", "kind": "bid", "title": "홍보 애니메이션 <제작>", "agency": "전주시", "deadline": "2026-11-20",
     "url": "https://g2b.test/R1", "status": "2차 검토 중", "memo": "대표 메모 비공개"},
    {"key": "bid:R2", "kind": "bid", "title": "캐릭터 개발", "agency": "익산시", "deadline": "2026-11-05",
     "url": "https://g2b.test/R2", "status": "신규", "memo": ""},
    {"key": "bid:R3", "kind": "bid", "title": "마감 지난 공고", "agency": "군산시", "deadline": "2026-11-04",
     "url": "https://g2b.test/R3", "status": "보류", "memo": ""},
    {"key": "grant_kocca:K1", "kind": "grant", "title": "지원사업 행", "agency": "한콘진", "deadline": "2026-12-01",
     "url": "https://kocca.test/K1", "status": "신규", "memo": ""},
    {"key": "bid:R4", "kind": "bid", "title": "데모 요청 공고", "agency": "전북교육청", "deadline": "2026-11-30",
     "url": "https://g2b.test/R4", "status": "데모 요청", "memo": ""},
    {"key": "grant_bizinfo:B1", "kind": "grant", "title": "보류한 지원사업", "agency": "인천광역시", "deadline": "2026-11-25",
     "url": "https://bizinfo.test/B1", "status": "보류", "memo": ""},
    {"key": "grant_bizinfo:B2", "kind": "grant", "title": "마감 지난 지원사업", "agency": "충청북도", "deadline": "2026-11-01",
     "url": "https://bizinfo.test/B2", "status": "신규", "memo": ""},
    {"key": "grant_bizinfo:B3", "kind": "grant", "title": "메모 남긴 지원사업", "agency": "부산광역시", "deadline": "2026-11-28",
     "url": "https://bizinfo.test/B3", "status": "신규", "has_memo": True},
    {"key": "grant_bizinfo:B4", "kind": "grant", "title": "마감 지난 메모 사업", "agency": "대구광역시", "deadline": "2026-11-01",
     "url": "https://bizinfo.test/B4", "status": "신규", "has_memo": True},
    {"key": "bid:R5", "kind": "bid", "title": "관련 없다고 한 공고", "agency": "남원시", "deadline": "2026-11-30",
     "url": "https://g2b.test/R5", "status": "관련 없음", "has_memo": True},
    {"key": "outsource_cglink:C1", "kind": "outsource", "title": "외주 게시글 C1", "agency": "", "deadline": "",
     "url": "https://cglink.test/C1", "status": "신규", "memo": ""},
]


class BusinessBoard(ReportCase):
    """사업 현황판(D28 개정): 설명서의 첫 탭에 입찰사업·지원사업 세부 탭을 채운 설명서 한 장."""

    def board(self, rows=ROWS, env=None):
        sheet = self.tmp / "sheet.json"
        sheet.write_text(json.dumps({"rows": rows}, ensure_ascii=False), encoding="utf-8")
        env_file = self.tmp / "board.env"
        env_file.write_text(env if env is not None else f"SHEET_URL={SHEET}\nSHEET_APP_TOKEN=tok-secret-123\n", encoding="utf-8")
        out = self.tmp / "board.html"
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["board", "--date", "2026-11-05", "--sheet", str(sheet), "--out", str(out),
                                   "--env-file", str(env_file)]), 0)
        return out.read_text(encoding="utf-8")

    @staticmethod
    def part(html, start, end):
        return html[html.index(start):html.index(end, html.index(start))]

    def panel(self, html):
        return self.part(html, "<!--board-start-->", "<!--board-end-->")

    def test_board_is_the_first_tab_of_the_manual(self):
        html = self.board()
        self.assertNotIn("<!--BOARD-->", html)
        self.assertIn('id="architecture"', html)  # 설명서의 다른 탭은 그대로 있다
        self.assertLess(html.index('aria-controls="board"'), html.index('aria-controls="architecture"'))
        self.assertIn("2026-11-05", self.panel(html))

    def test_bid_tab_groups_open_bids_with_reviews_first(self):
        bid = self.part(self.board(), 'id="bp-bid"', "</div><!--bp-bid-->")
        self.assertIn("캐릭터 개발", bid)  # 마감일 당일은 남는다
        self.assertNotIn("마감 지난 공고", bid)
        self.assertNotIn("지원사업 행", bid)
        self.assertLess(bid.index("<h3>2차 검토 중"), bid.index("<h3>신규"))  # 묶음 제목 순서(선택 목록의 값과 구분)
        self.assertLess(bid.index("<h3>데모 요청"), bid.index("<h3>신규"))

    def test_grant_tab_is_a_date_filterable_table(self):
        grant = self.part(self.board(), 'id="bp-grant"', "</div><!--bp-grant-->")
        self.assertIn("<table", grant)
        self.assertIn('type="date"', grant)  # 날짜 필터
        self.assertIn('data-deadline="2026-12-01"', grant)
        self.assertIn("지원사업 행", grant)
        self.assertIn("보류한 지원사업", grant)
        self.assertNotIn("마감 지난 지원사업", grant)
        self.assertNotIn("캐릭터 개발", grant)
        self.assertLess(grant.index("보류한 지원사업"), grant.index("지원사업 행"))  # 표는 마감이 가까운 순

    def test_grant_table_filters_by_agency_and_sorts_by_dates(self):  # 2026-11-12 sera.shin 지시
        grant = self.part(self.board(), 'id="bp-grant"', "</div><!--bp-grant-->")
        agency = self.part(grant, 'id="bf-agency"', "</select>")
        self.assertIn('<option value="인천광역시">', agency)
        self.assertIn('<option value="한콘진">', agency)
        self.assertIn('data-agency="인천광역시"', grant)
        head = self.part(grant, "<thead>", "</thead>")
        self.assertLess(head.index("기관"), head.index("등록일"))
        self.assertLess(head.index("등록일"), head.index("마감일"))  # 마감일은 등록일 바로 옆
        self.assertIn('data-sort="registered"', head)
        self.assertIn('data-sort="deadline"', head)
        self.assertIn('aria-sort="ascending"', head)  # 처음에는 마감일 오름차순

    def test_watch_tab_lists_open_rows_the_ceo_marked_or_memoed(self):  # 관심사업(2026-11-12 sera.shin 지시)
        html = self.board()
        self.assertLess(html.index('id="bt-grant"'), html.index('id="bt-watch"'))
        watch = self.part(html, 'id="bp-watch"', "</div><!--bp-watch-->")
        for title in ("홍보 애니메이션 &lt;제작&gt;", "데모 요청 공고", "보류한 지원사업", "메모 남긴 지원사업"):
            self.assertIn(title, watch)
        for title in ("캐릭터 개발", "지원사업 행", "마감 지난 메모 사업", "관련 없다고 한 공고", "마감 지난 공고"):
            self.assertNotIn(title, watch)
        self.assertIn("메모 있음", watch)
        self.assertLess(watch.index("홍보 애니메이션"), watch.index("보류한 지원사업"))  # 마감이 가까운 순

    def test_empty_watch_tab_says_so(self):
        self.assertIn("마감 전인 관심사업이 없습니다", self.panel(self.board(rows=[])))

    def test_outsource_posts_are_not_on_the_board(self):
        self.assertNotIn("외주 게시글 C1", self.board())

    def test_sheet_link_and_past_records_are_shown_but_secrets_are_not(self):
        html = self.board()
        panel = self.panel(html)
        self.assertIn(SHEET, panel)
        self.assertIn("지난 공고", panel)
        self.assertNotIn("tok-secret-123", html)

    def test_missing_sheet_url_says_so(self):
        self.assertIn("시트 주소가 설정되지 않았습니다", self.panel(self.board(env="")))

    def test_title_is_escaped_and_memo_is_never_published(self):
        html = self.board()
        self.assertIn("홍보 애니메이션 &lt;제작&gt;", html)
        self.assertNotIn("대표 메모 비공개", html)

    def test_status_is_a_picklist_keyed_to_the_sheet_row(self):  # 현황판에서 상태 저장(2026-11-12 sera.shin 지시, D38)
        html = self.board()
        grant = self.part(html, 'id="bp-grant"', "</div><!--bp-grant-->")
        pick = self.part(grant, 'data-key="grant_bizinfo:B1"', "</select>")
        for status in ("신규", "2차 검토 요청", "데모 요청", "보류", "관련 없음"):
            self.assertIn(f'<option value="{status}"', pick)
        self.assertIn('<option value="보류" selected>', pick)
        bid = self.part(html, 'id="bp-bid"', "</div><!--bp-bid-->")
        self.assertIn('<option value="2차 검토 중" selected>', self.part(bid, 'data-key="bid:R1"', "</select>"))
        watch = self.part(html, 'id="bp-watch"', "</div><!--bp-watch-->")
        self.assertIn('data-key="bid:R4"', watch)

    def test_board_names_the_sheet_to_save_to_but_not_the_token(self):
        panel = self.panel(self.board())
        self.assertIn('data-sheet-id="sheet-1"', panel)
        self.assertNotIn("data-sheet-id", self.panel(self.board(env="")))  # 시트가 없으면 저장하지 않는다

    def test_unknown_status_stays_selected(self):  # '2차 완료(권고)'처럼 에이전트가 쓴 값은 그대로 보인다
        rows = [{"key": "bid:R9", "kind": "bid", "title": "권고 공고", "agency": "전주시", "deadline": "2026-11-20",
                 "url": "https://g2b.test/R9", "status": "2차 완료(권고)"}]
        self.assertIn('<option value="2차 완료(권고)" selected>', self.panel(self.board(rows=rows)))

    def test_empty_board_says_no_open_bids_or_grants(self):
        panel = self.panel(self.board(rows=[]))
        self.assertIn("마감 전인 입찰공고가 없습니다", panel)
        self.assertIn("마감 전인 지원사업이 없습니다", panel)

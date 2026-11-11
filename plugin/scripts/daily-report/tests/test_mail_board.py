"""신규 알림 메일(D30)과 입찰 현황판(D28)의 경계: 명령줄 입력 -> 메일 JSON, 현황판 HTML."""
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
]


class BidBoard(ReportCase):
    def board(self, rows=ROWS):
        sheet = self.tmp / "sheet.json"
        sheet.write_text(json.dumps({"rows": rows}, ensure_ascii=False), encoding="utf-8")
        out = self.tmp / "board.html"
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["board", "--date", "2026-11-05", "--sheet", str(sheet), "--out", str(out)]), 0)
        return out.read_text(encoding="utf-8")

    def test_only_open_bids_grouped_with_reviews_first(self):
        html = self.board()
        self.assertNotIn("마감 지난 공고", html)
        self.assertNotIn("지원사업 행", html)
        self.assertIn("캐릭터 개발", html)  # 마감일 당일은 남는다
        self.assertLess(html.index("2차 검토 중"), html.index("신규"))
        self.assertLess(html.index("데모 요청"), html.index("신규"))

    def test_title_is_escaped_and_memo_is_never_published(self):
        html = self.board()
        self.assertIn("홍보 애니메이션 &lt;제작&gt;", html)
        self.assertNotIn("대표 메모 비공개", html)
        self.assertNotIn("docs.google.com", html)

    def test_empty_board_says_no_open_bids(self):
        self.assertIn("마감 전인 입찰공고가 없습니다", self.board(rows=[]))

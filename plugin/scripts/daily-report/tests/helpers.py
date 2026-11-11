"""시험 보조: 고정한 결과 파일을 임시 폴더에 놓고 CLI(경계 C)를 호출한다."""
import contextlib
import copy
import io
import json
import pathlib
import tempfile
import unittest

from daily_report.cli import main

FIX = pathlib.Path(__file__).parent / "fixtures"
TODAY = "2026-11-05"


def section(html, title, next_title=None):
    """메일에서 절 하나('<제목> N건' 머리부터 다음 절 머리 앞까지)를 잘라 낸다."""
    a = html.index(f">{title} ")
    return html[a:html.index(f">{next_title} ", a)] if next_title else html[a:]


def fixture(name):
    return json.loads((FIX / "results" / name).read_text(encoding="utf-8"))


class ReportCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = pathlib.Path(self._tmp.name)
        self.results = self.tmp / "results"
        self.results.mkdir()

    def put(self, name, data):
        text = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
        (self.results / name).write_text(text, encoding="utf-8")

    def put_today(self, mutate=None):
        data = copy.deepcopy(fixture("gov_2026-11-05.json"))
        if mutate:
            mutate(data)
        self.put("gov_2026-11-05.json", data)
        return data

    def build(self, date=TODAY, runs=None, now=None):
        """실행 기록 줄을 시작한다(D35: 보고서 HTML은 만들지 않는다). (종료 코드, 보고서 파일이 생겼는지)를 돌려준다."""
        argv = ["build", "--date", date, "--results", str(self.results)]
        if runs:
            argv += ["--runs", str(runs)]
        with contextlib.redirect_stdout(io.StringIO()):
            code = main(argv, now=now)
        return code, any(self.tmp.rglob("report-*.html"))

    def mail(self, *extra, date=TODAY, settings=None):
        out = self.tmp / "mail.json"
        argv = ["mail", "--date", date, "--results", str(self.results), "--out", str(out), *extra]
        if settings:
            argv += ["--settings", str(settings)]
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(argv), 0)
        return json.loads(out.read_text(encoding="utf-8"))

    def html(self, settings=None, **kw):
        """신규 알림 메일 본문 HTML(D35 뒤 대표가 받는 유일한 일일 전달물)."""
        return self.mail(settings=settings, **kw)["html"]

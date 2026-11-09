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


def fixture(name):
    return json.loads((FIX / "results" / name).read_text(encoding="utf-8"))


class ReportCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = pathlib.Path(self._tmp.name)
        self.results = self.tmp / "results"
        self.results.mkdir()
        self.out = self.tmp / "out"

    def put(self, name, data):
        text = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
        (self.results / name).write_text(text, encoding="utf-8")

    def put_today(self, mutate=None):
        data = copy.deepcopy(fixture("gov_2026-11-05.json"))
        if mutate:
            mutate(data)
        self.put("gov_2026-11-05.json", data)
        return data

    def build(self, date=TODAY, settings=None, runs=None, now=None):
        argv = ["build", "--date", date, "--results", str(self.results), "--out", str(self.out)]
        if settings:
            argv += ["--settings", str(settings)]
        if runs:
            argv += ["--runs", str(runs)]
        with contextlib.redirect_stdout(io.StringIO()):
            code = main(argv, now=now)
        path = self.out / f"report-{date}.html"
        return code, (path.read_text(encoding="utf-8") if path.exists() else None)

    def html(self, **kw):
        code, html = self.build(**kw)
        self.assertEqual(code, 0)
        return html

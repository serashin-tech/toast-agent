"""시험 보조: 가짜 네트워크 계층과 임시 설정 폴더. 외부로 나가는 호출은 없다."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from gov_agent.fakes import FakeTransport, ok_routes  # noqa: F401  시험들이 helpers에서 가져다 쓴다
from gov_agent.runner import run

KST = timezone(timedelta(hours=9))
KEY = "SECRETKEY%2Babc123"
ENV = {"DATA_GO_KR_SERVICE_KEY": KEY, "KOCCA_API_URL": "https://kocca.test/api"}
HISTORY = "\n## 변경 이력\n\n| 일자 | 항목 | 변경 전 | 변경 후 | 사유 | 변경자 |\n|---|---|---|---|---|---|\n"


def md(title, header, rows):
    t = f"# 설정: {title}\n\n## 값\n\n| {' | '.join(header)} |\n|{'---|' * len(header)}\n"
    return t + "".join(f"| {' | '.join(r)} |\n" for r in rows) + HISTORY


def bid_filter_md(include="", exclude="", pmin="", pmax="", days="", types=""):
    return md("입찰공고 필터", ["항목", "값", "비고"], [
        ["포함 키워드", include, ""], ["제외 키워드", exclude, ""], ["추정가격 최소", pmin, ""],
        ["추정가격 최대", pmax, ""], ["마감까지 최소 남은 일수", days, ""], ["제외할 기관 유형", types, ""]])


def grant_md(agency="", field="", keywords="", exclude=""):
    return md("지원사업 검색 조건", ["항목", "값"], [
        ["관심 기관", agency], ["사업 분야", field], ["지원사업 키워드", keywords], ["제외 키워드", exclude]])


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.settings, self.state, self.out = root / "settings", root / "state", root / "out"
        self.settings.mkdir()
        self.set_settings()

    def set_settings(self, bid=None, grant=None):
        (self.settings / "bid-filter.md").write_text(bid or bid_filter_md(), encoding="utf-8")
        (self.settings / "grant-criteria.md").write_text(grant or grant_md(), encoding="utf-8")

    def run_day(self, transport, date="2026-11-05", env=ENV, hour=9, **kw):
        y, m, d = map(int, date.split("-"))
        run(date, self.out, self.settings, self.state, transport, env=env,
            now=datetime(y, m, d, hour, 0, tzinfo=KST), **kw)
        return json.loads((self.out / f"gov_{date}.json").read_text(encoding="utf-8"))

    @staticmethod
    def src(result, sid):
        return next(s for s in result["sources"] if s["id"] == sid)

    @staticmethod
    def items(result, kind):
        return [i for i in result["items"] if i["kind"] == kind]

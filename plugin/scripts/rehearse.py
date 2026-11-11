"""가짜 응답 리허설(H10): 실제 키와 시트 없이 daily-routine의 코드 단계를 한 번 돌린다.

수집 → 결과 파일 → 시트 기록 → 신규 알림 메일 본문 → 메일 발송 → 시트 읽기 → 사업 현황판 → 실행 기록·노출 기록.
네트워크(공공데이터포털, CGLink, Apps Script)만 가짜로 바꾼다. 결과로 runs/runs.jsonl이 실제로 생긴다.
사용: python -X utf8 plugin/scripts/rehearse.py [작업 폴더]   (없으면 임시 폴더)
"""
import contextlib
import io
import os
import shutil
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
for p in (HERE / "gov-agent", HERE / "daily-report"):
    sys.path.insert(0, str(p))

from daily_report.cli import main as report  # noqa: E402
from gov_agent import fakes as fx  # noqa: E402  시험과 같은 가짜 응답
from gov_agent.cli import main as gov  # noqa: E402
from gov_agent.fakes import FakeTransport, ok_routes  # noqa: E402

DATE = "2026-11-11"
KST = timezone(timedelta(hours=9))
KEY = "SECRETKEY%2Brehearsal"  # 가짜 키. 어떤 산출물에도 남지 않아야 한다


class FakeSheetApp:
    """Apps Script 웹 앱 흉내: 행을 기억하고, 상태·메모를 덮어쓰지 않고, 메일은 보낸 것으로 기록한다."""

    def __init__(self):
        self.rows, self.mails = {}, []

    def __call__(self, url, payload):
        act = payload["action"]
        if act == "upsert":
            for r in payload["rows"]:
                keep = self.rows.get(r["key"], {})
                self.rows[r["key"]] = {**r, "status": keep.get("status", r["status"])}
        elif act == "mail":
            self.mails.append(payload["subject"])
        elif act == "status":
            self.rows[payload["key"]]["status"] = payload["status"]
        return {"ok": True, "rows": list(self.rows.values())}


def rehearse(work):
    work = Path(work)
    (work / "settings").mkdir(parents=True, exist_ok=True)
    for f in (HERE / "settings-template").glob("*.md"):
        shutil.copy(f, work / "settings" / f.name)
    (work / ".env").write_text(f"DATA_GO_KR_SERVICE_KEY={KEY}\nKOCCA_API_URL=https://kocca.test/api\n"
                               "SHEET_APP_URL=https://script.google.test/exec\nSHEET_APP_TOKEN=rehearsal\n",
                               encoding="utf-8")
    net = FakeTransport(ok_routes(
        bids=[fx.bid("R26BK999", "어린이 교통안전 홍보 애니메이션 제작", deadline="2026-12-01 10:00")],
        koccas=[fx.kocca("K1", "애니메이션 제작 지원사업")],
        cglinks=[fx.cglink("9", "3D 캐릭터 모델링 외주", "Tue, 10 Nov 2026 10:00:00 +0900")]))
    app = FakeSheetApp()
    log = io.StringIO()
    here = Path.cwd()
    try:
        os.chdir(work)
        with contextlib.redirect_stdout(log):
            steps = [
                ("수집", gov(["run", "--date", DATE, "--out", "results"], transport=net, environ={},
                            now=datetime(2026, 11, 11, 10, tzinfo=KST))),
                ("시트 기록", report(["sheet-push", "--date", DATE, "--state", "state"], transport=app)),
                ("메일 본문", report(["mail", "--date", DATE, "--results", "results", "--out", "reports/mail.json",
                                      "--board-url", "https://claude.ai/artifact/rehearsal", "--settings", "settings"])),
                ("메일 발송", report(["send-mail", "--mail", "reports/mail.json"], transport=app)),
                ("시트 읽기", report(["sheet-pull", "--out", "reports/sheet.json"], transport=app)),
                ("현황판", report(["board", "--date", DATE, "--sheet", "reports/sheet.json",
                                   "--out", "reports/board.html"])),
                ("실행 기록", report(["build", "--date", DATE, "--results", "results", "--runs", "runs"], now=lambda: datetime(2026, 11, 11, 10, 40, tzinfo=KST))),
                ("노출 기록", report(["record-publish", "--runs", "runs", "--date", DATE,
                                      "--at", "2026-11-11T10:45:00+09:00", "--ok", "true", "--results", "results"])),
            ]
    finally:
        os.chdir(here)
    return {"steps": steps, "mails": app.mails, "rows": len(app.rows), "work": str(work)}


def main():
    work = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp(prefix="toast-rehearsal-"))
    r = rehearse(work)
    for name, code in r["steps"]:
        print(f"[{'통과' if code == 0 else '실패'}] {name}")
    print(f"시트 행 {r['rows']}개, 보낸 메일 {len(r['mails'])}통, 작업 폴더 {r['work']}")
    return 0 if all(code == 0 for _, code in r["steps"]) else 1


if __name__ == "__main__":
    sys.exit(main())

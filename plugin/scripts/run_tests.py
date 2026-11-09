"""통합 시험 실행기: 모든 시험 묶음을 각자 폴더에서 따로 돌린다(H10).

묶음마다 시험 보조 모듈 이름(helpers 등)이 겹치므로 한 프로세스에 섞지 않는다.
사용: python -X utf8 plugin/scripts/run_tests.py
"""
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
SUITES = [PLUGIN / "scripts" / "gov-agent", PLUGIN / "scripts" / "daily-report", PLUGIN]


def main():
    failed = []
    for d in SUITES:
        p = subprocess.run([sys.executable, "-X", "utf8", "-m", "unittest", "discover", "-s", "tests"],
                           cwd=d, capture_output=True, text=True, encoding="utf-8")
        tail = (p.stderr.strip().splitlines() or ["(출력 없음)"])
        print(f"[{'통과' if p.returncode == 0 else '실패'}] {d.name}: {' / '.join(tail[-3:])}")
        if p.returncode:
            failed.append(d.name)
            print(p.stderr)
    print("모두 통과" if not failed else f"실패한 묶음: {', '.join(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

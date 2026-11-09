"""하네스 시험 보조: 두 코드 묶음과 gov-agent의 가짜 응답을 한 프로세스에서 쓴다."""
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN / "scripts"
for p in (SCRIPTS, SCRIPTS / "gov-agent", SCRIPTS / "gov-agent" / "tests", SCRIPTS / "daily-report"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

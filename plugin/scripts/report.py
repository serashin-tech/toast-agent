"""보고 진입점(daily_report). 작업 폴더에서 `python -X utf8 <플러그인>/scripts/report.py build ...`으로 부른다."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "daily-report"))
from daily_report.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())

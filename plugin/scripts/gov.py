"""정부사업 에이전트 진입점. 작업 폴더에서 `python -X utf8 <플러그인>/scripts/gov.py run ...`으로 부른다."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "gov-agent"))
from gov_agent.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())

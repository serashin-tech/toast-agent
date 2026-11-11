"""SessionStart 훅: 불변 규칙(rules/invariants.md)을 대화에 그대로 넣는다(H2, H7).

플러그인은 CLAUDE.md나 .claude/rules를 실을 수 없으므로, 늘 지킬 규칙은 이 훅이 넣는다.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INVARIANTS = ROOT / "rules" / "invariants.md"


def main():
    rules = INVARIANTS.read_text(encoding="utf-8").replace("${CLAUDE_PLUGIN_ROOT}", str(ROOT))
    context = f"toast-agent 플러그인(토스트 에이전트, {ROOT})의 불변 규칙이다.\n\n{rules}"
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context}}))


if __name__ == "__main__":
    main()

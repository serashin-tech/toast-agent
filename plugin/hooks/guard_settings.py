"""PreToolUse 훅: 설정 파일(settings/*.md)의 값을 바꾸면서 변경 이력 줄을 남기지 않는 호출을 막는다(D11, H7).

호출 전 파일 내용과 호출을 적용한 뒤의 내용을 비교한다. 값 영역(`## 변경 이력` 앞)이 바뀌었는데 변경 이력 표의
줄이 늘지 않았으면 막는다. 입력을 읽지 못하거나 대상이 아니면 아무것도 출력하지 않는다(허용).
ponytail: Bash·PowerShell로 고치면 이 훅을 거치지 않는다. 불변 규칙 3이 그 길을 금지한다.
"""
import json
import sys
from pathlib import Path

MARK = "## 변경 이력"


def split(text):
    head, _, hist = text.partition(MARK)
    rows = [ln for ln in hist.splitlines() if ln.strip().startswith("|")]
    return head, len(rows)


def apply(tool, inp, before):
    if tool == "Write":
        return inp.get("content", "")
    edits = inp.get("edits") if tool == "MultiEdit" else [inp]
    after = before
    for e in edits or []:
        old, new = e.get("old_string", ""), e.get("new_string", "")
        after = after.replace(old, new) if e.get("replace_all") else after.replace(old, new, 1)
    return after


def check(payload):
    tool, inp = payload.get("tool_name"), payload.get("tool_input") or {}
    if tool not in ("Write", "Edit", "MultiEdit"):
        return None
    path = Path(inp.get("file_path", ""))
    if path.suffix != ".md" or path.parent.name != "settings" or not path.is_file():
        return None
    before = path.read_text(encoding="utf-8")
    after = apply(tool, inp, before)
    (head_b, rows_b), (head_a, rows_a) = split(before), split(after)
    if head_a.split() == head_b.split() or rows_a > rows_b:
        return None
    return (f"{path.name}의 값을 바꾸려면 같은 호출에서 '{MARK}' 표에 한 줄을 더해야 합니다"
            "(일자, 항목, 변경 전, 변경 후, 사유, 변경자). 값 표와 변경 이력 표는 떨어져 있으므로 "
            "Edit를 두 번으로 나누지 말고, 파일 전체를 Write로 한 번에 다시 쓰십시오(change-setting 스킬).")


def main():
    try:
        reason = check(json.loads(sys.stdin.read() or "{}"))
    except Exception:  # 훅이 고장 나도 작업을 막지 않는다
        return
    if reason:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                                 "permissionDecision": "deny",
                                                 "permissionDecisionReason": reason}}))


if __name__ == "__main__":
    main()

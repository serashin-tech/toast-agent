"""훅 경계: 도구 호출 입력(JSON) -> 허용(출력 없음) 또는 차단(JSON). 훅 스크립트를 실제 프로세스로 돌린다."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
GUARD = PLUGIN / "hooks" / "guard_settings.py"
START = PLUGIN / "hooks" / "session_start.py"

SETTING = """# 설정: 입찰공고 필터

## 값

| 항목 | 값 | 비고 |
|---|---|---|
| 포함 키워드 | 애니메이션 | |

## 변경 이력

| 일자 | 항목 | 변경 전 | 변경 후 | 사유 | 변경자 |
|---|---|---|---|---|---|
| 2026-11-09 | 포함 키워드 | (없음) | 애니메이션 | 초안 | claude |
"""
ROW = "| 2026-11-10 | 포함 키워드 | 애니메이션 | 애니메이션, 홍보영상 | 대표 요청 | sera.shin |\n"


def run(script, payload):
    p = subprocess.run([sys.executable, "-I", str(script)], input=json.dumps(payload), capture_output=True,
                       text=True, encoding="utf-8")
    return p.returncode, p.stdout.strip()


def denied(out):
    return bool(out) and json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"


class GuardSettings(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name) / "settings"
        self.dir.mkdir()
        self.file = self.dir / "bid-filter.md"
        self.file.write_text(SETTING, encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def edit(self, old, new, path=None):
        return run(GUARD, {"tool_name": "Edit", "cwd": str(self.dir.parent),
                           "tool_input": {"file_path": str(path or self.file), "old_string": old, "new_string": new}})

    def write(self, content, path=None):
        return run(GUARD, {"tool_name": "Write", "cwd": str(self.dir.parent),
                           "tool_input": {"file_path": str(path or self.file), "content": content}})

    def test_value_change_without_history_row_is_denied_with_guidance(self):
        code, out = self.edit("| 애니메이션 | |", "| 애니메이션, 홍보영상 | |")
        self.assertEqual(code, 0)
        self.assertTrue(denied(out))
        reason = json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertIn("변경 이력", reason)
        self.assertIn("Write", reason)

    def test_write_with_value_and_history_row_is_allowed(self):
        new = SETTING.replace("| 애니메이션 | |", "| 애니메이션, 홍보영상 | |") + ROW
        self.assertEqual(self.write(new), (0, ""))

    def test_history_only_edit_is_allowed(self):
        last = SETTING.splitlines(keepends=True)[-1]
        self.assertEqual(self.edit(last, last + ROW), (0, ""))

    def test_files_outside_settings_are_not_checked(self):
        other = Path(self._tmp.name) / "notes.md"
        other.write_text(SETTING, encoding="utf-8")
        self.assertEqual(self.edit("| 애니메이션 | |", "| 다른 값 | |", path=other), (0, ""))

    def test_new_settings_file_is_allowed(self):
        self.assertEqual(self.write(SETTING, path=self.dir / "grant-criteria.md"), (0, ""))

    def test_multiedit_value_and_history_together_is_allowed(self):
        last = SETTING.splitlines(keepends=True)[-1]
        payload = {"tool_name": "MultiEdit", "cwd": str(self.dir.parent),
                   "tool_input": {"file_path": str(self.file), "edits": [
                       {"old_string": "| 애니메이션 | |", "new_string": "| 애니메이션, 홍보영상 | |"},
                       {"old_string": last, "new_string": last + ROW}]}}
        self.assertEqual(run(GUARD, payload), (0, ""))

    def test_bad_input_never_blocks(self):
        p = subprocess.run([sys.executable, "-I", str(GUARD)], input="not json", capture_output=True, text=True)
        self.assertEqual((p.returncode, p.stdout.strip()), (0, ""))


class SessionStart(unittest.TestCase):
    def test_injects_invariants_verbatim(self):
        code, out = run(START, {"hook_event_name": "SessionStart"})
        self.assertEqual(code, 0)
        ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        rules = (PLUGIN / "rules" / "invariants.md").read_text(encoding="utf-8")
        self.assertIn(rules.strip(), ctx)


if __name__ == "__main__":
    unittest.main()

"""플러그인 구조 경계: Cowork에 설치할 수 있는 모양인지, 운영 데이터가 저장소에 섞이지 않았는지 본다(H10)."""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
REPO = PLUGIN.parent
REF = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([^\s`\"')]+)")


def texts():
    for d in ("skills", "agents"):
        for p in (PLUGIN / d).rglob("*.md") if (PLUGIN / d).is_dir() else []:
            yield p, p.read_text(encoding="utf-8")
    yield PLUGIN / "hooks" / "hooks.json", (PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8")


class PluginStructure(unittest.TestCase):
    def test_no_bin_directory(self):  # Cowork는 bin/이 있는 플러그인을 설치하지 않는다
        self.assertFalse((PLUGIN / "bin").exists())

    def test_every_plugin_root_reference_exists(self):
        for path, text in texts():
            for rel in REF.findall(text):
                rel = rel.rstrip(".,:;")
                self.assertTrue((PLUGIN / rel).exists(), f"{path.name}: {rel}")

    def test_skills_do_not_use_repo_relative_script_paths(self):
        for path, text in texts():
            self.assertNotRegex(text, r"(?<![}/])\bplugin/scripts/", f"{path.name}: 경로는 ${{CLAUDE_PLUGIN_ROOT}}로 적는다")

    def test_each_skill_has_name_and_description(self):
        for skill in (PLUGIN / "skills").glob("*/SKILL.md"):
            head = skill.read_text(encoding="utf-8").split("---")[1]
            self.assertIn("name:", head, skill)
            self.assertIn("description:", head, skill)

    def test_manifests_are_valid_json_with_version(self):
        manifest = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertRegex(manifest["version"], r"^\d+\.\d+\.\d+$")
        json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))

    def test_no_operational_data_in_repo(self):
        for name in (".env", "settings", "results", "reports", "runs", "state", "drafts"):
            self.assertFalse((REPO / name).exists(), name)
            self.assertFalse((PLUGIN / name).exists(), name)

    @unittest.skipUnless(shutil.which("claude"), "claude CLI 없음")
    def test_claude_validate_strict(self):
        for target in (REPO, PLUGIN):
            p = subprocess.run([shutil.which("claude"), "plugin", "validate", "--strict", str(target)],
                               capture_output=True, text=True, encoding="utf-8")  # Windows에서는 claude.cmd 경로가 필요
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)


if __name__ == "__main__":
    unittest.main()

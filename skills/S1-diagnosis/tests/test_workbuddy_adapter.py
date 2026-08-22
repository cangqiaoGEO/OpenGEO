import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile


class WorkBuddyAdapterBuildTests(unittest.TestCase):
    """Verify that the repository can reproduce a safe WorkBuddy expert package."""

    def setUp(self):
        self.module_root = Path(__file__).resolve().parents[1]
        self.build_script = (
            self.module_root / "adapters" / "workbuddy" / "scripts" / "build_expert.py"
        )

    def test_build_assembles_current_core_without_local_secrets(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            output_dir = Path(temporary_dir)
            subprocess.run(
                [sys.executable, str(self.build_script), "--output-dir", str(output_dir)],
                check=True,
                capture_output=True,
                text=True,
            )
            expert_dir = output_dir / "geo-diagnostic-expert"
            archive_path = output_dir / "geo-diagnostic-expert.zip"
            packaged_core = expert_dir / "skills" / "brand-geo-audit"

            self.assertEqual(
                (self.module_root / "SKILL.md").read_bytes(),
                (packaged_core / "SKILL.md").read_bytes(),
            )
            self.assertFalse((packaged_core / ".env").exists())
            self.assertTrue((packaged_core / ".env.example").is_file())
            self.assertFalse((packaged_core / "work").exists())
            self.assertFalse((packaged_core / "tests").exists())
            self.assertFalse((packaged_core / "node_modules").exists())
            self.assertFalse((packaged_core / "adapters").exists())

            manifest = json.loads(
                (expert_dir / ".codebuddy-plugin" / "plugin.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(manifest["version"], "0.3.0")
            self.assertIn("./skills/geo-browser-runtime", manifest["skills"])

            with zipfile.ZipFile(archive_path) as archive:
                names = set(archive.namelist())
            self.assertIn(
                "geo-diagnostic-expert/skills/brand-geo-audit/SKILL.md", names
            )
            self.assertIn(
                "geo-diagnostic-expert/skills/geo-browser-runtime/SKILL.md", names
            )


if __name__ == "__main__":
    unittest.main()

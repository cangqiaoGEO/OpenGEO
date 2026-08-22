"""Secret-safe module-local environment loading tests"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from api_collect import load_local_env  # noqa: E402


class ApiCollectEnvironmentTest(unittest.TestCase):
    """Verify local credentials are allowlisted and never override explicit env"""

    def test_loads_only_allowlisted_keys_without_shell_evaluation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text(
                "DASHSCOPE_API_KEY='local-value'\nUNRELATED_KEY=blocked\nBAD_LINE\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {}, clear=True):
                load_local_env(env_path)
                self.assertEqual(os.environ["DASHSCOPE_API_KEY"], "local-value")
                self.assertNotIn("UNRELATED_KEY", os.environ)

    def test_explicit_process_environment_has_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text("DEEPSEEK_API_KEY=local-value\n", encoding="utf-8")
            with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "process-value"}, clear=True):
                load_local_env(env_path)
                self.assertEqual(os.environ["DEEPSEEK_API_KEY"], "process-value")


if __name__ == "__main__":
    unittest.main()

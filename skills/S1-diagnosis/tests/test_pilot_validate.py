"""R2 controlled-pilot plan and completion tests"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from pilot_validate import validate_pilot_study  # noqa: E402


def load_pilot() -> dict:
    """Load the synthetic pilot without sharing mutable state"""

    with (ROOT / "examples" / "pilot_study_standard.json").open(encoding="utf-8") as file:
        return json.load(file)


class PilotValidateTest(unittest.TestCase):
    """Verify R2 portfolio coverage and evidence-completion gates"""

    def test_frozen_three_case_portfolio_is_valid(self) -> None:
        result = validate_pilot_study(load_pilot())
        self.assertTrue(result["valid"], result)
        self.assertEqual(result["assessment"], "ready")
        self.assertTrue(result["warnings"])

    def test_missing_coverage_class_is_rejected(self) -> None:
        pilot = load_pilot()
        pilot["cases"][0]["coverage"].remove("entity_complexity")
        result = validate_pilot_study(pilot)
        self.assertFalse(result["valid"])
        self.assertTrue(any("does not cover" in error["message"] for error in result["errors"]))

    def test_local_case_requires_explicit_geography(self) -> None:
        pilot = load_pilot()
        pilot["observation_policy"]["location_state"] = "unknown"
        result = validate_pilot_study(pilot)
        self.assertFalse(result["valid"])
        self.assertTrue(any("geography explicit" in error["message"] for error in result["errors"]))

    def test_api_only_case_is_rejected(self) -> None:
        pilot = load_pilot()
        pilot["cases"][1]["data_access"] = ["official_api"]
        result = validate_pilot_study(pilot)
        self.assertFalse(result["valid"])
        self.assertTrue(any("consumer App evidence" in error["message"] for error in result["errors"]))

    def test_completed_pilot_requires_artifacts_and_exact_repetitions(self) -> None:
        pilot = load_pilot()
        pilot["status"] = "completed"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for case in pilot["cases"]:
                case["status"] = "completed"
                case["review_status"] = "completed"
                case_root = Path("work") / case["case_id"]
                case["research_package_path"] = str(case_root / "research.json")
                case["diagnostic_package_path"] = str(case_root / "diagnostic.json")
                case["handoff_path"] = str(case_root / "handoff.json")
                case["app_request_paths"] = [str(case_root / f"request-{index}.json") for index in range(1, 4)]
                case["app_response_paths"] = [str(case_root / f"response-{index}.json") for index in range(1, 4)]
                for value in [case["research_package_path"], case["diagnostic_package_path"], case["handoff_path"], *case["app_request_paths"], *case["app_response_paths"]]:
                    path = root / value
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text("{}", encoding="utf-8")
            result = validate_pilot_study(pilot, project_root=root)
        self.assertTrue(result["valid"], result)
        self.assertEqual(result["assessment"], "completed")

    def test_completed_pilot_rejects_missing_response(self) -> None:
        pilot = copy.deepcopy(load_pilot())
        pilot["status"] = "completed"
        for case in pilot["cases"]:
            case["status"] = "completed"
            case["review_status"] = "completed"
            case["handoff_path"] = "work/handoff.json"
            case["app_request_paths"] = ["work/request-1.json", "work/request-2.json", "work/request-3.json"]
            case["app_response_paths"] = ["work/response-1.json", "work/response-2.json"]
        result = validate_pilot_study(pilot)
        self.assertFalse(result["valid"])
        self.assertTrue(any("exactly 3" in error["message"] for error in result["errors"]))

    def test_cli_accepts_standard_plan(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(SCRIPTS / "pilot_validate.py"), str(ROOT / "examples" / "pilot_study_standard.json")],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertTrue(json.loads(completed.stdout)["valid"])


if __name__ == "__main__":
    unittest.main()

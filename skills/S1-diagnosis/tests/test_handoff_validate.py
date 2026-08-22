"""Diagnostic handoff contract tests"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from handoff_validate import validate_handoff_package  # noqa: E402


def load_example() -> dict:
    return json.loads((ROOT / "examples" / "diagnostic_handoff_standard.json").read_text(encoding="utf-8"))


class HandoffValidationTest(unittest.TestCase):
    """Protect evidence lineage and the diagnostic-to-planning boundary"""

    def test_standard_example_is_ready_for_planning(self) -> None:
        result = validate_handoff_package(load_example())
        self.assertTrue(result["valid"], result)
        self.assertEqual(result["assessment"], "ready_for_planning")

    def test_observed_finding_requires_evidence_lineage(self) -> None:
        handoff = load_example()
        handoff["findings"][0]["artifact_ref_ids"] = []
        result = validate_handoff_package(handoff)
        self.assertFalse(result["valid"])
        self.assertIn("observed findings require evidence lineage", str(result["errors"]))

    def test_unknown_finding_cannot_claim_confidence(self) -> None:
        handoff = load_example()
        handoff["findings"][0].update({"epistemic_status": "unknown", "confidence": "high", "artifact_ref_ids": []})
        result = validate_handoff_package(handoff)
        self.assertFalse(result["valid"])
        self.assertIn("unknown findings require unknown confidence", str(result["errors"]))

    def test_other_entity_only_requires_explicit_matched_term(self) -> None:
        handoff = load_example()
        observation = handoff["entity_observations"][0]
        observation.update({"match_status": "other_entity_only", "matched_terms": []})
        result = validate_handoff_package(handoff)
        self.assertFalse(result["valid"])
        self.assertIn("requires at least one matched term", str(result["errors"]))

    def test_absent_entity_cannot_keep_matched_terms(self) -> None:
        handoff = load_example()
        handoff["entity_observations"][0]["match_status"] = "absent"
        result = validate_handoff_package(handoff)
        self.assertFalse(result["valid"])
        self.assertIn("absent cannot assert matched terms", str(result["errors"]))

    def test_planning_question_must_reference_a_finding(self) -> None:
        handoff = load_example()
        handoff["planning_questions"][0]["related_finding_ids"] = ["finding-missing"]
        result = validate_handoff_package(handoff)
        self.assertFalse(result["valid"])
        self.assertIn("unresolved reference", str(result["errors"]))

    def test_project_root_checks_artifact_existence_and_path_escape(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            handoff = copy.deepcopy(load_example())
            handoff["artifact_refs"][0]["path"] = "../outside.json"
            handoff["artifact_refs"][1]["path"] = "missing.json"
            result = validate_handoff_package(handoff, project_root=root)
        self.assertFalse(result["valid"])
        self.assertIn("safe project-relative path", str(result["errors"]))
        self.assertIn("artifact does not exist", str(result["errors"]))

    def test_action_fields_are_rejected(self) -> None:
        handoff = load_example()
        handoff["findings"][0]["recommended_action"] = "发布内容"
        result = validate_handoff_package(handoff)
        self.assertFalse(result["valid"])
        self.assertIn("field is not allowed", str(result["errors"]))


if __name__ == "__main__":
    unittest.main()

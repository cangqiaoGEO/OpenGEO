"""Evidence-driven recommendation validation tests for Batch C"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from geo_score import compute  # noqa: E402
from quality_audit import audit_quality  # noqa: E402
from recommendation_validate import validate_recommendations  # noqa: E402


def load_json(name: str) -> dict:
    """Load one isolated example fixture"""

    with (ROOT / "examples" / name).open(encoding="utf-8") as file:
        return json.load(file)


def errors(result: dict) -> str:
    """Flatten validation errors for assertions"""

    return "\n".join(f"{item['path']}: {item['message']}" for item in result["errors"])


class RecommendationValidationTest(unittest.TestCase):
    """Verify evidence binding, weak-dimension coverage, and insufficient-data behavior"""

    def setUp(self) -> None:
        self.research = load_json("research_package_standard.json")
        self.evidence = load_json("evidence_package_measured.json")
        self.score = compute(self.research, self.evidence)
        self.audit = audit_quality(self.research, self.evidence, self.score)
        self.package = load_json("recommendations_measured.json")

    def validate(self) -> dict:
        return validate_recommendations(self.research, self.evidence, self.score, self.audit, self.package)

    def test_measured_recommendations_are_valid(self) -> None:
        result = self.validate()
        self.assertTrue(result["valid"], errors(result))

    def test_recommendation_requires_resolved_evidence(self) -> None:
        self.package["recommendations"][0]["source_ids"] = ["src-missing"]
        result = self.validate()
        self.assertFalse(result["valid"])
        self.assertIn("unresolved reference", errors(result))

    def test_recommendation_cannot_be_generic_and_evidence_free(self) -> None:
        item = self.package["recommendations"][0]
        item["source_ids"] = []
        item["observation_ids"] = []
        result = self.validate()
        self.assertFalse(result["valid"])
        self.assertIn("must cite at least one", errors(result))

    def test_dimension_must_be_measured_as_weak(self) -> None:
        self.package["recommendations"][0]["dimension"] = "visibility"
        result = self.validate()
        self.assertFalse(result["valid"])
        self.assertIn("not a measured weak dimension", errors(result))

    def test_dimension_below_forty_requires_two_recommendations(self) -> None:
        self.package["recommendations"] = [
            item for item in self.package["recommendations"] if item["dimension"] != "citation_quality" or item["recommendation_id"] == "rec-citation-official"
        ]
        result = self.validate()
        self.assertFalse(result["valid"])
        self.assertIn("requires at least 2", errors(result))

    def test_low_confidence_cannot_be_p0(self) -> None:
        self.package["recommendations"][0]["confidence"] = "low"
        result = self.validate()
        self.assertFalse(result["valid"])
        self.assertIn("P0 recommendations cannot use low confidence", errors(result))

    def test_insufficient_data_allows_empty_package_but_not_improvement_claims(self) -> None:
        self.evidence["observations"] = []
        self.score = compute(self.research, self.evidence)
        self.audit = audit_quality(self.research, self.evidence, self.score)
        self.package["audit_id"] = self.audit["audit_id"]
        self.package["recommendations"] = []
        result = self.validate()
        self.assertTrue(result["valid"], errors(result))
        self.assertTrue(result["warnings"])


if __name__ == "__main__":
    unittest.main()

"""Evidence contract and sample-sufficiency tests for Batch B"""

from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    """Load a script module without making scripts a production package"""

    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALIDATOR = load_module("evidence_validate", ROOT / "scripts" / "evidence_validate.py")


def load_json(name: str) -> dict:
    """Load one isolated example fixture"""

    with (ROOT / "examples" / name).open(encoding="utf-8") as file:
        return json.load(file)


def error_text(result: dict) -> str:
    """Flatten validation messages for readable assertions"""

    return "\n".join(f"{item['path']}: {item['message']}" for item in result["errors"])


class EvidenceValidationTest(unittest.TestCase):
    """Verify evidence identity, state, source, and sample gates"""

    def setUp(self) -> None:
        self.research = load_json("research_package_standard.json")
        self.evidence = load_json("evidence_package_measured.json")

    def test_measured_example_is_valid(self) -> None:
        result = VALIDATOR.validate_evidence_package(self.research, self.evidence)
        self.assertTrue(result["valid"], error_text(result))
        self.assertEqual(result["assessment"]["status"], "measured")
        self.assertEqual(result["assessment"]["observed_count"], 12)

    def test_web_proxy_cannot_masquerade_as_engine_observation(self) -> None:
        self.evidence["observations"][0]["source_type"] = "web_ecosystem_proxy"
        result = VALIDATOR.validate_evidence_package(self.research, self.evidence)
        self.assertFalse(result["valid"])
        self.assertIn("web_ecosystem_proxy", error_text(result))

    def test_unknown_position_is_rejected_before_scoring(self) -> None:
        self.evidence["observations"][0]["position"] = "bogus"
        result = VALIDATOR.validate_evidence_package(self.research, self.evidence)
        self.assertFalse(result["valid"])
        self.assertIn("evidence.observations[0].position", error_text(result))

    def test_absent_brand_requires_zero_evidence_state(self) -> None:
        absent = self.evidence["observations"][5]
        absent["coverage"]["intro"] = None
        absent["recommendation"] = "neutral"
        result = VALIDATOR.validate_evidence_package(self.research, self.evidence)
        self.assertFalse(result["valid"])
        text = error_text(result)
        self.assertIn("must be null when the brand is absent", text)
        self.assertIn("all six coverage fields must be false", text)

    def test_unobserved_is_distinct_from_absent(self) -> None:
        observation = self.evidence["observations"][0]
        observation["status"] = "unobserved"
        for field in ("observed_at", "raw_response", "position", "recommendation", "citations", "sentiment", "coverage", "fact_errors"):
            observation[field] = None
        result = VALIDATOR.validate_evidence_package(self.research, self.evidence)
        self.assertTrue(result["valid"], error_text(result))
        self.assertEqual(result["assessment"]["status"], "partially_measured")

    def test_unobserved_cannot_carry_answer_values(self) -> None:
        self.evidence["observations"][0]["status"] = "unobserved"
        result = VALIDATOR.validate_evidence_package(self.research, self.evidence)
        self.assertFalse(result["valid"])
        self.assertIn("must be null when status is 'unobserved'", error_text(result))

    def test_duplicate_query_engine_pair_is_rejected(self) -> None:
        duplicate = copy.deepcopy(self.evidence["observations"][0])
        duplicate["observation_id"] = "obs-duplicate"
        self.evidence["observations"].append(duplicate)
        result = VALIDATOR.validate_evidence_package(self.research, self.evidence)
        self.assertFalse(result["valid"])
        self.assertIn("duplicate query-engine observation", error_text(result))

    def test_query_must_come_from_frozen_protocol(self) -> None:
        self.evidence["observations"][0]["query_id"] = "q-invented"
        result = VALIDATOR.validate_evidence_package(self.research, self.evidence)
        self.assertFalse(result["valid"])
        self.assertIn("does not exist in the frozen protocol", error_text(result))

    def test_known_foundation_value_requires_source(self) -> None:
        self.evidence["foundation"]["wiki"]["evidence_ids"] = []
        result = VALIDATOR.validate_evidence_package(self.research, self.evidence)
        self.assertFalse(result["valid"])
        self.assertIn("observed foundation values require at least one source", error_text(result))

    def test_unknown_foundation_value_cannot_claim_support(self) -> None:
        self.evidence["foundation"]["knowledge_graph"]["evidence_ids"] = ["src-official-home"]
        result = VALIDATOR.validate_evidence_package(self.research, self.evidence)
        self.assertFalse(result["valid"])
        self.assertIn("unknown foundation values cannot cite evidence", error_text(result))

    def test_no_observations_is_valid_but_insufficient(self) -> None:
        self.evidence["observations"] = []
        result = VALIDATOR.validate_evidence_package(self.research, self.evidence)
        self.assertTrue(result["valid"], error_text(result))
        self.assertEqual(result["assessment"]["status"], "insufficient_data")
        self.assertEqual(result["assessment"]["observed_count"], 0)


if __name__ == "__main__":
    unittest.main()

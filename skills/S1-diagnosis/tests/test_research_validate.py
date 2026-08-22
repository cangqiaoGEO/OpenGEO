"""Contract and readiness tests for Batch A research objects"""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_PATH = ROOT / "examples" / "research_package_standard.json"
VALIDATOR_PATH = ROOT / "scripts" / "research_validate.py"
SPEC = importlib.util.spec_from_file_location("research_validate", VALIDATOR_PATH)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def load_example() -> dict:
    """Return an isolated copy of the valid standard research package"""

    with EXAMPLE_PATH.open(encoding="utf-8") as file:
        return json.load(file)


def messages(result: dict) -> str:
    """Flatten validation errors for readable assertions"""

    return "\n".join(f"{item['path']}: {item['message']}" for item in result["errors"])


class SchemaAssetTest(unittest.TestCase):
    """Verify formal Schema assets are parseable and identify the v2 contract"""

    def test_all_schema_files_are_valid_json_and_versioned(self) -> None:
        schema_paths = sorted((ROOT / "schemas").glob("*.schema.json"))
        self.assertEqual(
            {path.name for path in schema_paths},
            {
                "brand-entity-profile.schema.json",
                "content-foundation-protocol.schema.json",
                "diagnostic-package.schema.json",
                "diagnostic-handoff.schema.json",
                "diagnostic-run.schema.json",
                "domain-context.schema.json",
                "industry-profile.schema.json",
                "measurement-plan.schema.json",
                "observation-evidence.schema.json",
                "pilot-study.schema.json",
                "platform-request.schema.json",
                "quality-audit.schema.json",
                "query-protocol.schema.json",
                "raw-platform-response.schema.json",
                "recommendations.schema.json",
                "repeated-observation-experiment.schema.json",
                "research-scope.schema.json",
                "score-result.schema.json",
            },
        )
        for path in schema_paths:
            with self.subTest(path=path.name), path.open(encoding="utf-8") as file:
                schema = json.load(file)
                self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
                self.assertIn("schema_version", schema["properties"])


class ResearchPackageValidationTest(unittest.TestCase):
    """Verify cross-object evidence, reference, and readiness gates"""

    def test_standard_example_is_ready(self) -> None:
        result = VALIDATOR.validate_research_package(load_example())
        self.assertTrue(result["valid"], messages(result))
        self.assertEqual(result["assessment"], "ready")

    def test_cli_accepts_standard_example(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(VALIDATOR_PATH), str(EXAMPLE_PATH)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertTrue(json.loads(completed.stdout)["valid"])

    def test_draft_scope_exposes_unknown_context_and_blocks_frozen_protocol(self) -> None:
        data = load_example()
        data["scope"].update({"status": "draft", "domain": None, "market": None, "language": None, "audiences": []})
        result = VALIDATOR.validate_research_package(data)
        self.assertFalse(result["valid"])
        self.assertIn("cannot be 'ready' while scope.status is not 'ready'", messages(result))
        self.assertIn("cannot be 'frozen'", messages(result))
        self.assertGreaterEqual(len(result["warnings"]), 4)

    def test_ready_scope_requires_business_context(self) -> None:
        data = load_example()
        data["scope"]["domain"] = None
        result = VALIDATOR.validate_research_package(data)
        self.assertFalse(result["valid"])
        self.assertIn("scope.domain", messages(result))

    def test_fact_requires_verified_evidence(self) -> None:
        data = load_example()
        data["domain_context"]["brand_positioning"]["claim"]["evidence_ids"] = []
        result = VALIDATOR.validate_research_package(data)
        self.assertFalse(result["valid"])
        self.assertIn("fact claims require at least one source", messages(result))

    def test_unresolved_evidence_reference_is_rejected(self) -> None:
        data = load_example()
        data["domain_context"]["brand_positioning"]["claim"]["evidence_ids"] = ["src-missing"]
        result = VALIDATOR.validate_research_package(data)
        self.assertFalse(result["valid"])
        self.assertIn("unresolved reference 'src-missing'", messages(result))

    def test_unknown_claim_cannot_masquerade_as_supported_fact(self) -> None:
        data = load_example()
        claim = data["domain_context"]["brand_positioning"]["claim"]
        claim.update({"status": "unknown", "confidence": "high"})
        result = VALIDATOR.validate_research_package(data)
        self.assertFalse(result["valid"])
        error_text = messages(result)
        self.assertIn("unknown claims cannot cite evidence", error_text)
        self.assertIn("unknown claims must use confidence 'unknown'", error_text)

    def test_cross_object_customer_reference_must_resolve(self) -> None:
        data = load_example()
        data["query_protocol"]["queries"][0]["audience_ids"] = ["customer-missing"]
        result = VALIDATOR.validate_research_package(data)
        self.assertFalse(result["valid"])
        self.assertIn("unresolved reference 'customer-missing'", messages(result))

    def test_frozen_protocol_requires_all_four_core_query_types(self) -> None:
        data = load_example()
        data["query_protocol"]["queries"][3]["query_type"] = "risk"
        result = VALIDATOR.validate_research_package(data)
        self.assertFalse(result["valid"])
        self.assertIn("brand_comparison", messages(result))

    def test_brand_comparison_requires_a_known_competitor(self) -> None:
        data = load_example()
        del data["query_protocol"]["queries"][3]["competitor_ids"]
        result = VALIDATOR.validate_research_package(data)
        self.assertFalse(result["valid"])
        self.assertIn("brand_comparison queries require at least one competitor", messages(result))

    def test_frozen_queries_require_a_comparable_engine_set(self) -> None:
        data = load_example()
        data["query_protocol"]["queries"][0]["engines"] = ["ChatGPT", "DeepSeek", "Kimi"]
        result = VALIDATOR.validate_research_package(data)
        self.assertFalse(result["valid"])
        self.assertIn("same engine set", messages(result))

    def test_deep_scope_requires_five_engines(self) -> None:
        data = load_example()
        data["scope"]["depth"] = "deep"
        result = VALIDATOR.validate_research_package(data)
        self.assertFalse(result["valid"])
        self.assertIn("requires at least 5 engines", messages(result))

    def test_ready_context_requires_four_high_value_questions(self) -> None:
        data = load_example()
        data["domain_context"]["high_value_questions"] = data["domain_context"]["high_value_questions"][:3]
        data["query_protocol"]["queries"] = data["query_protocol"]["queries"][:3]
        result = VALIDATOR.validate_research_package(data)
        self.assertFalse(result["valid"])
        self.assertIn("must contain at least four questions", messages(result))

    def test_timestamp_requires_timezone(self) -> None:
        data = load_example()
        data["query_protocol"]["created_at"] = "2026-08-20T15:10:00"
        result = VALIDATOR.validate_research_package(data)
        self.assertFalse(result["valid"])
        self.assertIn("with timezone", messages(result))

    def test_runtime_rejects_fields_forbidden_by_schema(self) -> None:
        data = load_example()
        data["scope"]["unexpected"] = "must not pass silently"
        result = VALIDATOR.validate_research_package(data)
        self.assertFalse(result["valid"])
        self.assertIn("field is not allowed by the v2 contract", messages(result))

    def test_runtime_rejects_invalid_source_enum(self) -> None:
        data = load_example()
        data["domain_context"]["sources"][0]["source_type"] = "random_blog"
        result = VALIDATOR.validate_research_package(data)
        self.assertFalse(result["valid"])
        self.assertIn("domain_context.sources[0].source_type", messages(result))

    def test_user_provided_source_can_use_controlled_artifact_path(self) -> None:
        data = load_example()
        source = data["domain_context"]["sources"][0]
        source["source_type"] = "user_provided"
        source["url"] = None
        source["artifact_path"] = "work/intake/brand-identity.png"
        result = VALIDATOR.validate_research_package(data)
        self.assertTrue(result["valid"], result)

    def test_user_provided_source_rejects_missing_or_unsafe_artifact_path(self) -> None:
        data = load_example()
        source = data["domain_context"]["sources"][0]
        source["source_type"] = "user_provided"
        source["url"] = None
        result = VALIDATOR.validate_research_package(data)
        self.assertFalse(result["valid"])
        self.assertIn("domain_context.sources[0].artifact_path", messages(result))
        source["artifact_path"] = "../outside.png"
        result = VALIDATOR.validate_research_package(data)
        self.assertFalse(result["valid"])
        self.assertIn("safe project-relative artifact path", messages(result))

    def test_ready_context_represents_every_scope_audience(self) -> None:
        data = load_example()
        data["scope"]["audiences"].append("企业培训负责人")
        result = VALIDATOR.validate_research_package(data)
        self.assertFalse(result["valid"])
        self.assertIn("does not represent scope audiences", messages(result))

    def test_validation_is_pure_for_callers(self) -> None:
        data = load_example()
        original = copy.deepcopy(data)
        VALIDATOR.validate_research_package(data)
        self.assertEqual(data, original)


if __name__ == "__main__":
    unittest.main()

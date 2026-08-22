"""R1 diagnostic manifest, entity, industry, plan, and content protocol tests"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from diagnostic_contracts import validate_diagnostic_package  # noqa: E402


def load_json(name: str) -> dict:
    """Load one example without sharing mutable state across tests"""

    with (ROOT / "examples" / name).open(encoding="utf-8") as file:
        return json.load(file)


class DiagnosticContractsTest(unittest.TestCase):
    """Verify R1 cross-object references and small-business-safe semantics"""

    def setUp(self) -> None:
        self.research = load_json("research_package_standard.json")
        self.package = load_json("diagnostic_package_standard.json")

    def test_standard_diagnostic_package_is_ready(self) -> None:
        result = validate_diagnostic_package(self.research, self.package)
        self.assertTrue(result["valid"], result)
        self.assertEqual(result["assessment"], "ready")

    def test_scope_brand_can_resolve_through_verified_store_alias(self) -> None:
        self.research["scope"]["brand"] = "示例影音门店"
        profile = self.package["brand_entity_profile"]
        profile["canonical_name"] = "示例影音"
        profile["entity_type"] = "store"
        profile["match_terms"] = [
            {
                "term_id": "term-canonical-store",
                "term": "示例影音",
                "term_type": "canonical",
                "verification_status": "verified",
                "evidence_ids": ["src-official-home"],
            },
            {
                "term_id": "term-local-store",
                "term": "示例影音门店",
                "term_type": "store_name",
                "verification_status": "verified",
                "evidence_ids": ["src-official-home"],
            },
        ]
        profile["locations"] = [
            {
                "location_id": "location-example-store",
                "name": "示例影音门店",
                "market": "杭州",
                "address": "示例路 1 号",
                "service_area": ["杭州"],
                "evidence_ids": ["src-official-home"],
            }
        ]
        industry = self.package["industry_profile"]
        industry["operating_scope"] = "local"
        industry["service_modes"] = ["in_store"]
        industry["market_characteristics"] = ["location_sensitive", "in_person_experience"]
        content = self.package["content_foundation_protocol"]
        content["probes"].extend(
            [
                {
                    "probe_id": "probe-local-listing",
                    "probe_type": "local_listing",
                    "applicability": "required",
                    "target_terms": ["示例影音门店", "杭州影音体验店"],
                    "decision_factor_ids": ["factor-delivery-proof"],
                    "expected_evidence": ["location_accuracy", "identity_match"],
                    "rationale": "核验门店位置和名称是否一致",
                },
                {
                    "probe_id": "probe-business-identity",
                    "probe_type": "business_identity",
                    "applicability": "required",
                    "target_terms": ["示例影音", "示例影音门店"],
                    "decision_factor_ids": ["factor-delivery-proof"],
                    "expected_evidence": ["identity_match"],
                    "rationale": "核验品牌、门店和经营主体关系",
                },
            ]
        )
        for mapping in self.package["measurement_plan"]["query_mappings"]:
            if mapping["query_id"] == "q-category-recommendation":
                mapping["location_ids"] = ["location-example-store"]
        result = validate_diagnostic_package(self.research, self.package)
        self.assertTrue(result["valid"], result)
        self.assertFalse(result["warnings"], result)

    def test_unverified_alias_cannot_define_measured_brand(self) -> None:
        self.research["scope"]["brand"] = "未经确认的门店别名"
        self.package["brand_entity_profile"]["match_terms"].append(
            {
                "term_id": "term-unverified-store",
                "term": "未经确认的门店别名",
                "term_type": "store_name",
                "verification_status": "unverified",
                "evidence_ids": [],
            }
        )
        result = validate_diagnostic_package(self.research, self.package)
        self.assertFalse(result["valid"])
        self.assertTrue(any("scope brand must resolve" in error["message"] for error in result["errors"]))

    def test_location_sensitive_profile_exposes_missing_local_probes(self) -> None:
        self.package["industry_profile"]["operating_scope"] = "local"
        self.package["industry_profile"]["market_characteristics"] = ["location_sensitive"]
        result = validate_diagnostic_package(self.research, self.package)
        messages = [warning["message"] for warning in result["warnings"]]
        self.assertTrue(any("local_listing" in message for message in messages))
        self.assertTrue(any("business_identity" in message for message in messages))

    def test_frozen_plan_must_map_every_query_without_cross_segment_offset(self) -> None:
        self.package["measurement_plan"]["query_mappings"].pop()
        self.package["measurement_plan"]["aggregation_policy"]["allow_cross_segment_offset"] = True
        result = validate_diagnostic_package(self.research, self.package)
        messages = [error["message"] for error in result["errors"]]
        self.assertIn("frozen measurement plan must map every frozen query exactly once", messages)
        self.assertIn("must be false", messages)

    def test_cli_accepts_standard_package(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "diagnostic_contracts.py"),
                str(ROOT / "examples" / "research_package_standard.json"),
                str(ROOT / "examples" / "diagnostic_package_standard.json"),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertTrue(json.loads(completed.stdout)["valid"])


if __name__ == "__main__":
    unittest.main()

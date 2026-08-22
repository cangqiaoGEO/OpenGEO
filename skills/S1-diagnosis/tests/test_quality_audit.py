"""Deterministic quality-audit tests for Batch C"""

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


def load_json(name: str) -> dict:
    """Load one isolated example fixture"""

    with (ROOT / "examples" / name).open(encoding="utf-8") as file:
        return json.load(file)


class QualityAuditTest(unittest.TestCase):
    """Verify quality status, gaps, counterevidence, freshness, and traceability"""

    def setUp(self) -> None:
        self.research = load_json("research_package_standard.json")
        self.evidence = load_json("evidence_package_measured.json")
        self.score = compute(self.research, self.evidence)

    def test_measured_example_passes_with_explicit_warnings(self) -> None:
        audit = audit_quality(self.research, self.evidence, self.score)
        self.assertEqual(audit["status"], "passed_with_warnings")
        self.assertEqual(audit["confidence"], "medium")
        self.assertEqual(set(audit["checks"]), {
            "boundary_completeness",
            "sample_sufficiency",
            "source_reliability",
            "coverage_completeness",
            "cross_validation",
            "counterexample_review",
            "data_freshness",
            "traceability",
        })
        self.assertGreaterEqual(len(audit["gaps"]), 3)

    def test_observed_absence_and_fact_error_become_counterevidence(self) -> None:
        audit = audit_quality(self.research, self.evidence, self.score)
        descriptions = "\n".join(item["description"] for item in audit["counterevidence"])
        self.assertIn("品牌未出现", descriptions)
        self.assertIn("过时产品信息", descriptions)

    def test_score_mismatch_fails_traceability(self) -> None:
        self.score["total"] = 99.0
        audit = audit_quality(self.research, self.evidence, self.score)
        self.assertEqual(audit["status"], "failed")
        self.assertEqual(audit["checks"]["traceability"]["status"], "fail")
        self.assertIn("无法复算", "\n".join(gap["description"] for gap in audit["gaps"]))

    def test_stale_sources_are_exposed(self) -> None:
        self.research["domain_context"]["sources"][0]["retrieved_at"] = "2025-01-01T00:00:00+08:00"
        self.score = compute(self.research, self.evidence)
        audit = audit_quality(self.research, self.evidence, self.score)
        self.assertEqual(audit["checks"]["data_freshness"]["status"], "warning")
        self.assertIn("gap-stale-evidence", {gap["gap_id"] for gap in audit["gaps"]})

    def test_empty_observations_produce_insufficient_data_audit(self) -> None:
        self.evidence["observations"] = []
        self.score = compute(self.research, self.evidence)
        audit = audit_quality(self.research, self.evidence, self.score)
        self.assertEqual(audit["status"], "insufficient_data")
        self.assertEqual(audit["confidence"], "low")
        self.assertEqual(audit["checks"]["sample_sufficiency"]["status"], "fail")


if __name__ == "__main__":
    unittest.main()

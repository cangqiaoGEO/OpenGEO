"""Deterministic answer, engine, and overall scoring tests for Batch B"""

from __future__ import annotations

import importlib.util
import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("geo_score_v2", SCRIPTS / "geo_score.py")
assert SPEC and SPEC.loader
SCORE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCORE)


def load_json(name: str) -> dict:
    """Load one isolated JSON fixture"""

    with (ROOT / "examples" / name).open(encoding="utf-8") as file:
        return json.load(file)


class ObservationScoringTest(unittest.TestCase):
    """Verify the repaired v2 meanings of missing, absent, and observed data"""

    def test_absent_brand_has_zero_coverage_and_no_sentiment(self) -> None:
        evidence = load_json("evidence_package_measured.json")
        result = SCORE.score_observation(evidence["observations"][5])
        self.assertEqual(result["scores"]["visibility"], 0.0)
        self.assertEqual(result["scores"]["recommendation"], 0.0)
        self.assertEqual(result["scores"]["coverage"], 0.0)
        self.assertIsNone(result["scores"]["sentiment"])

    def test_unobserved_answer_produces_only_unknown_scores(self) -> None:
        observation = load_json("evidence_package_measured.json")["observations"][0]
        observation.update({
            "status": "unobserved",
            "observed_at": None,
            "raw_response": None,
            "position": None,
            "recommendation": None,
            "citations": None,
            "sentiment": None,
            "coverage": None,
            "fact_errors": None,
        })
        result = SCORE.score_observation(observation)
        self.assertTrue(all(value is None for value in result["scores"].values()))

    def test_unknown_coverage_items_do_not_default_to_true(self) -> None:
        coverage = {name: None for name in SCORE.COVERAGE_ITEMS}
        self.assertIsNone(SCORE.score_coverage(coverage, []))
        coverage["intro"] = False
        self.assertEqual(SCORE.score_coverage(coverage, []), 0.0)

    def test_citation_scoring_is_per_answer_and_domain_aware(self) -> None:
        citations = [
            {"url": "https://official.example/a", "domain": "official.example", "source_type": "official", "brand_owned": True, "verification_status": "verified"},
            {"url": "https://report.example/b", "domain": "report.example", "source_type": "authoritative", "brand_owned": False, "verification_status": "verified"},
            {"url": "https://review.example/c", "domain": "review.example", "source_type": "review", "brand_owned": False, "verification_status": "verified"},
        ]
        diverse = SCORE.score_citations(citations)
        same_domain = SCORE.score_citations([{**item, "domain": "same.example"} for item in citations])
        self.assertIsNotNone(diverse)
        self.assertGreater(diverse, same_domain)


class AggregateScoringTest(unittest.TestCase):
    """Verify formal grading, matrix completeness, and equal-engine aggregation"""

    def setUp(self) -> None:
        self.research = load_json("research_package_standard.json")
        self.evidence = load_json("evidence_package_measured.json")

    def test_measured_example_has_stable_result(self) -> None:
        result = SCORE.compute(self.research, self.evidence)
        self.assertEqual(result["assessment"]["status"], "measured")
        self.assertEqual(result["total"], 63.0)
        self.assertEqual(result["grade"], "A")
        self.assertEqual(result["weak_dimensions"], ["citation_quality", "foundation"])

    def test_engine_matrix_contains_all_five_answer_dimensions(self) -> None:
        result = SCORE.compute(self.research, self.evidence)
        required = {"visibility", "recommendation", "citation_quality", "coverage", "sentiment"}
        for engine in result["engines"].values():
            self.assertTrue(required <= set(engine))

    def test_empty_observations_do_not_produce_score_or_grade(self) -> None:
        self.evidence["observations"] = []
        result = SCORE.compute(self.research, self.evidence)
        self.assertEqual(result["assessment"]["status"], "insufficient_data")
        self.assertIsNone(result["total"])
        self.assertIsNone(result["grade"])

    def test_partial_observations_do_not_produce_formal_grade(self) -> None:
        self.evidence["observations"] = self.evidence["observations"][:4]
        result = SCORE.compute(self.research, self.evidence)
        self.assertEqual(result["assessment"]["status"], "partially_measured")
        self.assertIsNone(result["total"])

    def test_overall_metric_weights_engines_equally(self) -> None:
        engines = {
            "many": {"coverage": {"score": 100.0, "sample_count": 100, "unknown_count": 0}},
            "few": {"coverage": {"score": 0.0, "sample_count": 1, "unknown_count": 0}},
        }
        metric = SCORE._equal_engine_metric(engines, "coverage")
        self.assertEqual(metric["score"], 50.0)
        self.assertEqual(metric["sample_count"], 101)

    def test_repeated_run_does_not_change_query_weight(self) -> None:
        observations = [
            SCORE.score_observation(item)
            for item in self.evidence["observations"]
            if item["engine"]["name"] == "ChatGPT"
        ]
        original = SCORE.aggregate_engine(observations)
        repeated = copy.deepcopy(observations[0])
        repeated["observation_id"] = "obs-chatgpt-brand-direct-repeat-2"
        result = SCORE.aggregate_engine([*observations, repeated])
        self.assertEqual(result["queries"], 4)
        self.assertEqual(result["run_count"], 5)
        self.assertEqual(result["visibility"], original["visibility"])

    def test_grade_boundaries(self) -> None:
        expected = [(19.9, "D"), (20.0, "C"), (39.9, "C"), (40.0, "B"), (59.9, "B"), (60.0, "A"), (79.9, "A"), (80.0, "S")]
        for score, grade in expected:
            with self.subTest(score=score):
                self.assertEqual(SCORE.grade_for(score)[0], grade)

    def test_cli_produces_v2_result(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "geo_score.py"),
                str(ROOT / "examples" / "research_package_standard.json"),
                str(ROOT / "examples" / "evidence_package_measured.json"),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["schema_version"], "2.0.0")
        self.assertEqual(result["assessment"]["status"], "measured")



if __name__ == "__main__":
    unittest.main()

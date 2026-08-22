#!/usr/bin/env python3
"""Compute deterministic v2 GEO scores from validated observation evidence

Usage: python3 geo_score.py <research_package.json> <evidence_package.json>

The Agent produces structured observations, evidence_validate.py enforces their
contract, and this module performs answer-, engine-, and overall aggregation
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from evidence_validate import validate_evidence_package  # noqa: E402


SCHEMA_VERSION = "2.0.0"
WEIGHTS = {
    "visibility": 0.30,
    "recommendation": 0.20,
    "citation_quality": 0.15,
    "coverage": 0.15,
    "sentiment": 0.10,
    "foundation": 0.10,
}
POSITION_SCORES = {"top1": 100.0, "top1_tied": 85.0, "top3": 70.0, "top5": 50.0, "mention": 30.0, "absent": 0.0}
RECOMMENDATION_SCORES = {"explicit": 100.0, "tied": 70.0, "neutral": 40.0, "negative": 0.0}
CITATION_TYPE_SCORES = {"official": 90.0, "wiki": 80.0, "authoritative": 75.0, "review": 65.0, "social": 45.0, "low_quality": 20.0}
CITATION_VERIFICATION_FACTORS = {"verified": 1.0, "partially_verified": 0.75, "unverified": 0.0}
SENTIMENT_SCORES = {"positive": 100.0, "neutral": 50.0, "negative": 0.0}
COVERAGE_ITEMS = ("intro", "selling_points", "products", "pricing", "reputation", "news")
FOUNDATION_MAX_POINTS = {"wiki": 25.0, "official_site_structured": 20.0, "third_party_count": 20.0, "knowledge_graph": 15.0, "content_active": 20.0}
GRADES = (
    (80.0, "S", "优秀，GEO 领先者"),
    (60.0, "A", "良好，有竞争力"),
    (40.0, "B", "中等，需要改进"),
    (20.0, "C", "较弱，明显落后"),
    (0.0, "D", "缺失，几乎不可见"),
)
ANSWER_DIMENSIONS = ("recommendation", "citation_quality", "coverage", "sentiment")


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    """Clamp a numeric score to the public 0-100 range"""

    return max(low, min(high, value))


def _round(value: float | None) -> float | None:
    """Round known scores to one decimal while preserving unknown"""

    return None if value is None else round(clamp(value), 1)


def grade_for(score: float) -> tuple[str, str]:
    """Return the stable letter and label for a formal total score"""

    for threshold, letter, label in GRADES:
        if score >= threshold:
            return letter, label
    return GRADES[-1][1], GRADES[-1][2]


def score_citations(citations: list[dict[str, Any]] | None) -> float | None:
    """Score citations within one answer using unique URLs and domain diversity

    None means collection was unavailable and does not enter an average, while
    an empty list means collection was performed and found no citations
    """

    if citations is None:
        return None
    if not citations:
        return 0.0
    unique_citations = list({item["url"]: item for item in citations}.values())
    authority_mean = sum(
        CITATION_TYPE_SCORES[item["source_type"]] * CITATION_VERIFICATION_FACTORS[item["verification_status"]]
        for item in unique_citations
    ) / len(unique_citations)
    quantity_factor = min(1.0, len(unique_citations) / 3.0)
    domain_diversity = len({item["domain"].lower() for item in unique_citations}) / len(unique_citations)
    score = authority_mean * quantity_factor * (0.7 + 0.3 * domain_diversity)
    if any(item["brand_owned"] and item["verification_status"] != "unverified" for item in unique_citations):
        score += 10.0
    independent_types = {"wiki", "authoritative", "review"}
    if any(
        not item["brand_owned"]
        and item["source_type"] in independent_types
        and item["verification_status"] != "unverified"
        for item in unique_citations
    ):
        score += 5.0
    return _round(score)


def score_coverage(coverage: dict[str, bool | None] | None, fact_errors: list[dict[str, Any]] | None) -> float | None:
    """Score known coverage items and subtract explicit factual-error penalties"""

    if coverage is None:
        return None
    known = [coverage[item] for item in COVERAGE_ITEMS if coverage[item] is not None]
    if not known:
        return None
    score = sum(value is True for value in known) / len(known) * 100.0
    if fact_errors is not None:
        for error in fact_errors:
            score -= 20.0 if error["severity"] == "major" else 10.0
    return _round(score)


def score_observation(observation: dict[str, Any]) -> dict[str, Any]:
    """Convert one validated observation into independently reviewable scores"""

    base = {
        "observation_id": observation["observation_id"],
        "query_id": observation["query_id"],
        "engine": observation["engine"]["name"],
        "status": observation["status"],
        "position": observation["position"],
    }
    if observation["status"] == "unobserved":
        return {**base, "scores": {name: None for name in ("visibility", *ANSWER_DIMENSIONS)}}
    position = observation["position"]
    if position == "absent":
        scores = {"visibility": 0.0, "recommendation": 0.0, "citation_quality": 0.0, "coverage": 0.0, "sentiment": None}
    else:
        scores = {
            "visibility": POSITION_SCORES[position],
            "recommendation": None if observation["recommendation"] is None else RECOMMENDATION_SCORES[observation["recommendation"]],
            "citation_quality": score_citations(observation["citations"]),
            "coverage": score_coverage(observation["coverage"], observation["fact_errors"]),
            "sentiment": None if observation["sentiment"] is None else SENTIMENT_SCORES[observation["sentiment"]],
        }
    return {**base, "scores": {name: _round(value) for name, value in scores.items()}}


def _metric(values: list[float | None]) -> dict[str, float | int | None]:
    """Aggregate known values and expose both sample and unknown counts"""

    known = [value for value in values if value is not None]
    return {"score": _round(sum(known) / len(known)) if known else None, "sample_count": len(known), "unknown_count": len(values) - len(known)}


def _visibility_metric(scores: list[dict[str, Any]]) -> dict[str, float | int | None]:
    """Combine appearance rate and mean position according to GEO metrics"""

    observed = [item for item in scores if item["scores"]["visibility"] is not None]
    if not observed:
        return {"score": None, "sample_count": 0, "unknown_count": len(scores)}
    appearance_rate = sum(item["position"] != "absent" for item in observed) / len(observed) * 100.0
    position_mean = sum(item["scores"]["visibility"] for item in observed) / len(observed)
    return {"score": _round(0.5 * appearance_rate + 0.5 * position_mean), "sample_count": len(observed), "unknown_count": len(scores) - len(observed)}


def aggregate_engine(observation_scores: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate one engine with equal weight per query wording

    Repeated runs remain available at observation level, but they are first
    averaged within the same query id so a stability experiment cannot change
    the business-query weighting of the formal score
    """

    by_query: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in observation_scores:
        by_query[item["query_id"]].append(item)

    query_visibility: list[float | None] = []
    query_dimensions: dict[str, list[float | None]] = {name: [] for name in ANSWER_DIMENSIONS}
    observed_queries = 0
    for items in by_query.values():
        if any(item["status"] == "observed" for item in items):
            observed_queries += 1
        query_visibility.append(_visibility_metric(items)["score"])
        for dimension in ANSWER_DIMENSIONS:
            query_dimensions[dimension].append(_metric([item["scores"][dimension] for item in items])["score"])

    result: dict[str, Any] = {
        "queries": len(by_query),
        "observed_queries": observed_queries,
        "run_count": len(observation_scores),
        "visibility": _metric(query_visibility),
    }
    for dimension in ANSWER_DIMENSIONS:
        result[dimension] = _metric(query_dimensions[dimension])
    return result


def score_foundation(foundation: dict[str, dict[str, Any]]) -> dict[str, float | int | None]:
    """Score known content-foundation checks without treating null as false"""

    earned = possible = 0.0
    known_count = unknown_count = 0
    for name, max_points in FOUNDATION_MAX_POINTS.items():
        value = foundation[name]["value"]
        if value is None:
            unknown_count += 1
            continue
        known_count += 1
        possible += max_points
        if name == "third_party_count":
            if value >= 5:
                earned += max_points
            elif value >= 2:
                earned += max_points * 0.5
            elif value >= 1:
                earned += max_points * 0.25
        elif value:
            earned += max_points
    return {"score": _round(earned / possible * 100.0) if possible else None, "sample_count": known_count, "unknown_count": unknown_count}


def _equal_engine_metric(engines: dict[str, dict[str, Any]], dimension: str) -> dict[str, float | int | None]:
    """Average engine scores equally so query volume cannot alter engine weight"""

    values = [engine[dimension]["score"] for engine in engines.values()]
    known = [value for value in values if value is not None]
    return {
        "score": _round(sum(known) / len(known)) if known else None,
        "sample_count": sum(engine[dimension]["sample_count"] for engine in engines.values()),
        "unknown_count": sum(engine[dimension]["unknown_count"] for engine in engines.values()),
    }


def compute(research: dict[str, Any], evidence: dict[str, Any], validation: dict[str, Any] | None = None) -> dict[str, Any]:
    """Compute v2 scores from a contract-valid research and evidence package"""

    validation = validation or validate_evidence_package(research, evidence)
    if not validation["valid"]:
        raise ValueError("evidence package must pass validation before scoring")
    observation_scores = [score_observation(item) for item in evidence["observations"]]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in observation_scores:
        grouped[item["engine"]].append(item)
    engines = {engine: aggregate_engine(items) for engine, items in sorted(grouped.items())}
    dimensions = {name: _equal_engine_metric(engines, name) for name in ("visibility", *ANSWER_DIMENSIONS)}
    dimensions["foundation"] = score_foundation(evidence["foundation"])
    assessment = validation["assessment"]
    can_grade = assessment["status"] == "measured" and all(dimensions[name]["score"] is not None for name in WEIGHTS)
    if can_grade:
        total = _round(sum(dimensions[name]["score"] * WEIGHTS[name] for name in WEIGHTS))
        assert total is not None
        grade, grade_label = grade_for(total)
        weak_dimensions = [name for name in WEIGHTS if dimensions[name]["score"] < 60.0]
    else:
        total = grade = grade_label = None
        weak_dimensions = []
        if assessment["status"] == "measured":
            missing = [name for name in WEIGHTS if dimensions[name]["score"] is None]
            assessment = {**assessment, "status": "partially_measured", "limitations": [*assessment["limitations"], f"formal grading requires known scores for dimensions: {', '.join(missing)}"]}
    return {
        "schema_version": SCHEMA_VERSION,
        "brand": evidence["brand"],
        "protocol_id": evidence["protocol_id"],
        "assessment": assessment,
        "observation_scores": observation_scores,
        "dimensions": dimensions,
        "weights": WEIGHTS,
        "total": total,
        "grade": grade,
        "grade_label": grade_label,
        "weak_dimensions": weak_dimensions,
        "engines": engines,
    }


def _load_json(path: str) -> Any:
    """Load one UTF-8 JSON file"""

    with Path(path).open(encoding="utf-8") as file:
        return json.load(file)


def main() -> int:
    """Validate inputs, compute scores, and print stable v2 result JSON"""

    parser = argparse.ArgumentParser(description="Compute Brand GEO v2 scores")
    parser.add_argument("research_path")
    parser.add_argument("evidence_path")
    args = parser.parse_args()
    try:
        research = _load_json(args.research_path)
        evidence = _load_json(args.evidence_path)
    except (OSError, json.JSONDecodeError) as error:
        print(json.dumps({"valid": False, "errors": [{"path": "$", "message": str(error)}]}, ensure_ascii=False, indent=2))
        return 2
    validation = validate_evidence_package(research, evidence)
    if not validation["valid"]:
        print(json.dumps(validation, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(compute(research, evidence, validation), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

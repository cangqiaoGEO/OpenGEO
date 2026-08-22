#!/usr/bin/env python3
"""Validate evidence-driven recommendations against v2 research outputs"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "2.0.0"
DIMENSIONS = {"visibility", "recommendation", "citation_quality", "coverage", "sentiment", "foundation"}
PRIORITIES = {"P0", "P1", "P2"}
CONFIDENCE = {"high", "medium", "low"}


class RecommendationReport:
    """Collect deterministic recommendation contract errors"""

    def __init__(self) -> None:
        self.errors: list[dict[str, str]] = []
        self.warnings: list[dict[str, str]] = []

    def error(self, path: str, message: str) -> None:
        """Record one blocking recommendation problem"""

        self.errors.append({"path": path, "message": message})

    def warning(self, path: str, message: str) -> None:
        """Record one non-blocking recommendation limitation"""

        self.warnings.append({"path": path, "message": message})


def _is_string(value: Any) -> bool:
    """Return whether a value is a non-empty string"""

    return isinstance(value, str) and bool(value.strip())


def _fields(obj: Any, required: set[str], allowed: set[str], path: str, report: RecommendationReport) -> dict[str, Any]:
    """Validate an object plus its required and additional fields"""

    if not isinstance(obj, dict):
        report.error(path, f"expected object, got {type(obj).__name__}")
        return {}
    for field in sorted(required - set(obj)):
        report.error(f"{path}.{field}", "required field is missing")
    for field in sorted(set(obj) - allowed):
        report.error(f"{path}.{field}", "field is not allowed by the v2 contract")
    return obj


def _references(value: Any, allowed: set[str], path: str, report: RecommendationReport) -> list[str]:
    """Validate unique references to known source or observation ids"""

    if not isinstance(value, list):
        report.error(path, f"expected array, got {type(value).__name__}")
        return []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not _is_string(item):
            report.error(f"{path}[{index}]", "expected non-empty reference")
        elif item in seen:
            report.error(f"{path}[{index}]", f"duplicate reference {item!r}")
        elif item not in allowed:
            report.error(f"{path}[{index}]", f"unresolved reference {item!r}")
        seen.add(item)
    return [item for item in value if isinstance(item, str)]


def validate_recommendations(
    research: Any,
    evidence: Any,
    score_result: Any,
    audit: Any,
    package: Any,
) -> dict[str, Any]:
    """Validate recommendation traceability, coverage, and priority discipline"""

    report = RecommendationReport()
    research = research if isinstance(research, dict) else {}
    evidence = evidence if isinstance(evidence, dict) else {}
    score_result = score_result if isinstance(score_result, dict) else {}
    audit = audit if isinstance(audit, dict) else {}
    top_fields = {"schema_version", "recommendation_package_id", "protocol_id", "audit_id", "recommendations"}
    package = _fields(package, top_fields, top_fields, "recommendations", report)
    if package.get("schema_version") != SCHEMA_VERSION:
        report.error("recommendations.schema_version", f"expected {SCHEMA_VERSION!r}, got {package.get('schema_version')!r}")
    if package.get("protocol_id") != score_result.get("protocol_id") or package.get("protocol_id") != audit.get("protocol_id"):
        report.error("recommendations.protocol_id", "must match score result and quality audit")
    if package.get("audit_id") != audit.get("audit_id"):
        report.error("recommendations.audit_id", "must match quality audit")
    can_recommend = (
        audit.get("status") in {"passed", "passed_with_warnings"}
        and score_result.get("assessment", {}).get("status") == "measured"
    )

    source_ids = {
        item.get("source_id")
        for item in research.get("domain_context", {}).get("sources", [])
        if isinstance(item, dict) and isinstance(item.get("source_id"), str)
    }
    observation_ids = {
        item.get("observation_id")
        for item in evidence.get("observations", [])
        if isinstance(item, dict) and isinstance(item.get("observation_id"), str)
    }
    weak_dimensions = set(score_result.get("weak_dimensions", []))
    recommendations = package.get("recommendations")
    if not isinstance(recommendations, list):
        report.error("recommendations.recommendations", "expected array")
        recommendations = []
    if not can_recommend and recommendations:
        report.error("recommendations.recommendations", "improvement recommendations require a measured score and passed quality audit")
    if not can_recommend and not recommendations:
        report.warning("recommendations.recommendations", "no improvement recommendations generated because evidence is insufficient")
    ids: set[str] = set()
    counts: dict[str, int] = {dimension: 0 for dimension in weak_dimensions}
    fields = {
        "recommendation_id",
        "priority",
        "dimension",
        "business_context",
        "finding",
        "source_ids",
        "observation_ids",
        "hypothesis",
        "action",
        "expected_effect",
        "measure",
        "confidence",
    }
    for index, item in enumerate(recommendations):
        path = f"recommendations.recommendations[{index}]"
        item = _fields(item, fields, fields, path, report)
        recommendation_id = item.get("recommendation_id")
        if not _is_string(recommendation_id):
            report.error(f"{path}.recommendation_id", "expected non-empty recommendation id")
        elif recommendation_id in ids:
            report.error(f"{path}.recommendation_id", f"duplicate recommendation id {recommendation_id!r}")
        ids.add(recommendation_id)
        if item.get("priority") not in PRIORITIES:
            report.error(f"{path}.priority", f"expected one of {sorted(PRIORITIES)}, got {item.get('priority')!r}")
        dimension = item.get("dimension")
        if dimension not in DIMENSIONS:
            report.error(f"{path}.dimension", f"expected one of {sorted(DIMENSIONS)}, got {dimension!r}")
        elif dimension not in weak_dimensions:
            report.error(f"{path}.dimension", f"dimension {dimension!r} is not a measured weak dimension")
        else:
            counts[dimension] = counts.get(dimension, 0) + 1
        for field in ("business_context", "finding", "hypothesis", "action", "expected_effect", "measure"):
            if not _is_string(item.get(field)):
                report.error(f"{path}.{field}", "expected non-empty string")
        if item.get("confidence") not in CONFIDENCE:
            report.error(f"{path}.confidence", f"expected one of {sorted(CONFIDENCE)}, got {item.get('confidence')!r}")
        source_refs = _references(item.get("source_ids"), source_ids, f"{path}.source_ids", report)
        observation_refs = _references(item.get("observation_ids"), observation_ids, f"{path}.observation_ids", report)
        if not source_refs and not observation_refs:
            report.error(path, "recommendation must cite at least one source or observation")
        if item.get("priority") == "P0" and item.get("confidence") == "low":
            report.error(f"{path}.confidence", "P0 recommendations cannot use low confidence")

    dimensions = score_result.get("dimensions", {})
    for dimension in sorted(weak_dimensions if can_recommend else set()):
        score = dimensions.get(dimension, {}).get("score")
        required_count = 2 if score is not None and score < 40 else 1
        if counts.get(dimension, 0) < required_count:
            report.error(
                "recommendations.recommendations",
                f"weak dimension {dimension!r} with score {score!r} requires at least {required_count} recommendation(s)",
            )
    return {"valid": not report.errors, "errors": report.errors, "warnings": report.warnings}


def _load(path: str) -> Any:
    """Load UTF-8 JSON"""

    with Path(path).open(encoding="utf-8") as file:
        return json.load(file)


def main() -> int:
    """Validate one recommendation package against all upstream objects"""

    parser = argparse.ArgumentParser(description="Validate Brand GEO v2 recommendations")
    parser.add_argument("research_path")
    parser.add_argument("evidence_path")
    parser.add_argument("score_path")
    parser.add_argument("audit_path")
    parser.add_argument("recommendations_path")
    args = parser.parse_args()
    try:
        result = validate_recommendations(
            _load(args.research_path),
            _load(args.evidence_path),
            _load(args.score_path),
            _load(args.audit_path),
            _load(args.recommendations_path),
        )
    except (OSError, json.JSONDecodeError) as error:
        print(json.dumps({"valid": False, "errors": [{"path": "$", "message": str(error)}]}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

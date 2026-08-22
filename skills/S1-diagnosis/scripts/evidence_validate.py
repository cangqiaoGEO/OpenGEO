#!/usr/bin/env python3
"""Validate v2 GEO observations against a frozen Batch A research package"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from research_validate import REQUIRED_QUERY_TYPES, SCHEMA_VERSION, validate_research_package  # noqa: E402


POSITION_VALUES = {"top1", "top1_tied", "top3", "top5", "mention", "absent"}
RECOMMENDATION_VALUES = {"explicit", "tied", "neutral", "negative"}
SENTIMENT_VALUES = {"positive", "neutral", "negative"}
COVERAGE_ITEMS = {"intro", "selling_points", "products", "pricing", "reputation", "news"}
SOURCE_TYPES = {"direct_engine_observation", "user_provided_observation"}
CITATION_TYPES = {"official", "wiki", "authoritative", "review", "social", "low_quality"}
VERIFICATION_STATUSES = {"verified", "partially_verified", "unverified"}
FOUNDATION_FIELDS = {"wiki", "official_site_structured", "third_party_count", "knowledge_graph", "content_active"}
DEPTH_REQUIRED_ENGINES = {"quick": 3, "standard": 3, "deep": 5}


class EvidenceReport:
    """Collect evidence contract errors and non-blocking sample warnings"""

    def __init__(self) -> None:
        self.errors: list[dict[str, str]] = []
        self.warnings: list[dict[str, str]] = []

    def error(self, path: str, message: str) -> None:
        """Record a blocking evidence contract violation"""

        self.errors.append({"path": path, "message": message})

    def warning(self, path: str, message: str) -> None:
        """Record a non-blocking completeness limitation"""

        self.warnings.append({"path": path, "message": message})


def _is_string(value: Any) -> bool:
    """Return whether a value is a non-empty string"""

    return isinstance(value, str) and bool(value.strip())


def _object(value: Any, path: str, report: EvidenceReport) -> dict[str, Any]:
    """Return an object or record a type error"""

    if not isinstance(value, dict):
        report.error(path, f"expected object, got {type(value).__name__}")
        return {}
    return value


def _array(value: Any, path: str, report: EvidenceReport) -> list[Any]:
    """Return an array or record a type error"""

    if not isinstance(value, list):
        report.error(path, f"expected array, got {type(value).__name__}")
        return []
    return value


def _fields(
    obj: dict[str, Any],
    required: set[str],
    allowed: set[str],
    path: str,
    report: EvidenceReport,
) -> None:
    """Validate required and additional object fields"""

    for field in sorted(required - set(obj)):
        report.error(f"{path}.{field}", "required field is missing")
    for field in sorted(set(obj) - allowed):
        report.error(f"{path}.{field}", "field is not allowed by the v2 contract")


def _iso_datetime(value: Any, path: str, report: EvidenceReport) -> None:
    """Validate an ISO timestamp with explicit timezone"""

    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            raise ValueError("timezone missing")
    except (TypeError, ValueError):
        report.error(path, f"expected ISO date-time with timezone, got {value!r}")


def _reference_ids(value: Any, allowed: set[str], path: str, report: EvidenceReport) -> list[str]:
    """Validate unique references to established DomainContext sources"""

    values = _array(value, path, report)
    seen: set[str] = set()
    for index, item in enumerate(values):
        if not _is_string(item):
            report.error(f"{path}[{index}]", "expected non-empty source id")
        elif item in seen:
            report.error(f"{path}[{index}]", f"duplicate source reference {item!r}")
        elif item not in allowed:
            report.error(f"{path}[{index}]", f"unresolved source reference {item!r}")
        seen.add(item)
    return [item for item in values if isinstance(item, str)]


def _validate_foundation(foundation: Any, source_ids: set[str], report: EvidenceReport) -> None:
    """Validate content-foundation values without converting unknowns into negatives"""

    foundation = _object(foundation, "evidence.foundation", report)
    _fields(foundation, FOUNDATION_FIELDS, FOUNDATION_FIELDS, "evidence.foundation", report)
    for name in sorted(FOUNDATION_FIELDS):
        item_path = f"evidence.foundation.{name}"
        item = _object(foundation.get(name), item_path, report)
        item_fields = {"value", "evidence_ids"}
        _fields(item, item_fields, item_fields, item_path, report)
        value = item.get("value")
        if name == "third_party_count":
            if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 0):
                report.error(f"{item_path}.value", f"expected non-negative integer or null, got {value!r}")
        elif value is not None and not isinstance(value, bool):
            report.error(f"{item_path}.value", f"expected boolean or null, got {value!r}")
        evidence_ids = _reference_ids(item.get("evidence_ids"), source_ids, f"{item_path}.evidence_ids", report)
        if value is None and evidence_ids:
            report.error(f"{item_path}.evidence_ids", "unknown foundation values cannot cite evidence as established support")
        if value is not None and not evidence_ids:
            report.error(f"{item_path}.evidence_ids", "observed foundation values require at least one source")


def _validate_engine(engine: Any, allowed_engines: set[str], path: str, report: EvidenceReport) -> str | None:
    """Validate engine identity and ensure it belongs to the frozen protocol"""

    engine = _object(engine, path, report)
    fields = {"name", "model", "web_enabled"}
    _fields(engine, fields, fields, path, report)
    name = engine.get("name")
    if not _is_string(name):
        report.error(f"{path}.name", "expected non-empty engine name")
        return None
    if name not in allowed_engines:
        report.error(f"{path}.name", f"engine {name!r} is not assigned to this query in the frozen protocol")
    if engine.get("model") is not None and not _is_string(engine.get("model")):
        report.error(f"{path}.model", "expected non-empty model string or null")
    if engine.get("web_enabled") is not None and not isinstance(engine.get("web_enabled"), bool):
        report.error(f"{path}.web_enabled", "expected boolean or null")
    return name


def _validate_citations(citations: Any, path: str, report: EvidenceReport) -> None:
    """Validate brand-related citations and reject duplicate URLs within one answer"""

    if citations is None:
        return
    citations = _array(citations, path, report)
    urls: set[str] = set()
    for index, citation in enumerate(citations):
        item_path = f"{path}[{index}]"
        citation = _object(citation, item_path, report)
        fields = {"url", "domain", "source_type", "brand_owned", "verification_status"}
        _fields(citation, fields, fields, item_path, report)
        url = citation.get("url")
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            report.error(f"{item_path}.url", f"expected HTTP(S) URL, got {url!r}")
        elif url in urls:
            report.error(f"{item_path}.url", f"duplicate citation URL {url!r}")
        urls.add(url)
        if not _is_string(citation.get("domain")):
            report.error(f"{item_path}.domain", "expected non-empty domain")
        if citation.get("source_type") not in CITATION_TYPES:
            report.error(f"{item_path}.source_type", f"unsupported citation type {citation.get('source_type')!r}")
        if not isinstance(citation.get("brand_owned"), bool):
            report.error(f"{item_path}.brand_owned", "expected boolean")
        if citation.get("verification_status") not in VERIFICATION_STATUSES:
            report.error(f"{item_path}.verification_status", f"unsupported verification status {citation.get('verification_status')!r}")


def _validate_coverage(coverage: Any, path: str, report: EvidenceReport) -> None:
    """Validate all six coverage fields while preserving null as unknown"""

    coverage = _object(coverage, path, report)
    _fields(coverage, COVERAGE_ITEMS, COVERAGE_ITEMS, path, report)
    for name in COVERAGE_ITEMS:
        value = coverage.get(name)
        if value is not None and not isinstance(value, bool):
            report.error(f"{path}.{name}", f"expected boolean or null, got {value!r}")


def _validate_fact_errors(errors: Any, path: str, report: EvidenceReport) -> None:
    """Validate explicit factual errors without treating null as an empty review"""

    if errors is None:
        return
    errors = _array(errors, path, report)
    ids: set[str] = set()
    for index, error in enumerate(errors):
        item_path = f"{path}[{index}]"
        error = _object(error, item_path, report)
        fields = {"error_id", "description", "severity"}
        _fields(error, fields, fields, item_path, report)
        error_id = error.get("error_id")
        if not _is_string(error_id):
            report.error(f"{item_path}.error_id", "expected non-empty error id")
        elif error_id in ids:
            report.error(f"{item_path}.error_id", f"duplicate fact error id {error_id!r}")
        ids.add(error_id)
        if not _is_string(error.get("description")):
            report.error(f"{item_path}.description", "expected non-empty error description")
        if error.get("severity") not in {"minor", "major"}:
            report.error(f"{item_path}.severity", "expected 'minor' or 'major'")


def _validate_observation_state(observation: dict[str, Any], path: str, report: EvidenceReport) -> None:
    """Enforce the distinct meanings of unobserved, absent, false, and null"""

    status = observation.get("status")
    if status not in {"observed", "unobserved"}:
        report.error(f"{path}.status", f"expected 'observed' or 'unobserved', got {status!r}")
        return
    if status == "unobserved":
        for field in ("observed_at", "raw_response", "position", "recommendation", "citations", "sentiment", "coverage", "fact_errors"):
            if observation.get(field) is not None:
                report.error(f"{path}.{field}", "must be null when status is 'unobserved'")
        return

    _iso_datetime(observation.get("observed_at"), f"{path}.observed_at", report)
    if not _is_string(observation.get("raw_response")):
        report.error(f"{path}.raw_response", "observed answers require the raw response")
    position = observation.get("position")
    if position not in POSITION_VALUES:
        report.error(f"{path}.position", f"expected one of {sorted(POSITION_VALUES)}, got {position!r}")
        return
    if position == "absent":
        if observation.get("recommendation") is not None:
            report.error(f"{path}.recommendation", "must be null when the brand is absent")
        if observation.get("sentiment") is not None:
            report.error(f"{path}.sentiment", "must be null when the brand is absent")
        if observation.get("citations") != []:
            report.error(f"{path}.citations", "must be an empty array when the brand is absent")
        coverage = observation.get("coverage")
        if not isinstance(coverage, dict) or set(coverage) != COVERAGE_ITEMS or any(value is not False for value in coverage.values()):
            report.error(f"{path}.coverage", "all six coverage fields must be false when the brand is absent")
        if observation.get("fact_errors") != []:
            report.error(f"{path}.fact_errors", "must be an empty array when the brand is absent")
        return

    recommendation = observation.get("recommendation")
    if recommendation is not None and recommendation not in RECOMMENDATION_VALUES:
        report.error(f"{path}.recommendation", f"expected one of {sorted(RECOMMENDATION_VALUES)} or null, got {recommendation!r}")
    sentiment = observation.get("sentiment")
    if sentiment is not None and sentiment not in SENTIMENT_VALUES:
        report.error(f"{path}.sentiment", f"expected one of {sorted(SENTIMENT_VALUES)} or null, got {sentiment!r}")
    _validate_citations(observation.get("citations"), f"{path}.citations", report)
    if observation.get("coverage") is not None:
        _validate_coverage(observation.get("coverage"), f"{path}.coverage", report)
    _validate_fact_errors(observation.get("fact_errors"), f"{path}.fact_errors", report)


def assess_samples(research: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    """Assess whether observed core queries support a formal cross-engine grade"""

    scope = research["scope"]
    queries = research["query_protocol"]["queries"]
    query_by_id = {query["query_id"]: query for query in queries}
    expected_pairs = {
        (query["query_id"], engine)
        for query in queries
        for engine in query["engines"]
    }
    observed_pairs = {
        (item["query_id"], item["engine"]["name"])
        for item in evidence.get("observations", [])
        if isinstance(item, dict)
        and item.get("status") == "observed"
        and isinstance(item.get("engine"), dict)
        and item.get("query_id") in query_by_id
    }
    core_types_by_engine: dict[str, set[str]] = {}
    for query_id, engine in observed_pairs:
        query_type = query_by_id[query_id]["query_type"]
        core_types_by_engine.setdefault(engine, set()).add(query_type)
    measured_engines = sorted(
        engine
        for engine, query_types in core_types_by_engine.items()
        if REQUIRED_QUERY_TYPES <= query_types
    )
    required_engines = DEPTH_REQUIRED_ENGINES.get(scope.get("depth"), 3)
    if len(measured_engines) >= required_engines:
        status = "measured"
    elif observed_pairs:
        status = "partially_measured"
    else:
        status = "insufficient_data"
    limitations: list[str] = []
    missing_pairs = expected_pairs - observed_pairs
    if missing_pairs:
        limitations.append(f"{len(missing_pairs)} expected query-engine observations are missing or unobserved")
    incomplete_engines = sorted(set(core_types_by_engine) - set(measured_engines))
    if incomplete_engines:
        limitations.append(f"core query types are incomplete for engines: {', '.join(incomplete_engines)}")
    if len(measured_engines) < required_engines:
        limitations.append(f"formal grading requires {required_engines} engines with all four core query types")
    return {
        "status": status,
        "expected_observations": len(expected_pairs),
        "observed_count": len(observed_pairs),
        "unobserved_count": len(expected_pairs - observed_pairs),
        "measured_engines": len(measured_engines),
        "required_engines": required_engines,
        "limitations": limitations,
    }


def validate_evidence_package(research: Any, evidence: Any) -> dict[str, Any]:
    """Validate Batch A plus evidence contracts and return sample sufficiency"""

    report = EvidenceReport()
    research_result = validate_research_package(research)
    for error in research_result["errors"]:
        report.error(f"research.{error['path']}", error["message"])
    for warning in research_result["warnings"]:
        report.warning(f"research.{warning['path']}", warning["message"])
    if not isinstance(research, dict):
        research = {}
    evidence = _object(evidence, "evidence", report)
    fields = {"schema_version", "evidence_package_id", "scope_id", "context_id", "protocol_id", "brand", "foundation", "observations"}
    _fields(evidence, fields, fields, "evidence", report)
    if evidence.get("schema_version") != SCHEMA_VERSION:
        report.error("evidence.schema_version", f"expected {SCHEMA_VERSION!r}, got {evidence.get('schema_version')!r}")

    scope = research.get("scope", {}) if isinstance(research.get("scope"), dict) else {}
    context = research.get("domain_context", {}) if isinstance(research.get("domain_context"), dict) else {}
    protocol = research.get("query_protocol", {}) if isinstance(research.get("query_protocol"), dict) else {}
    expected_links = {
        "scope_id": scope.get("scope_id"),
        "context_id": context.get("context_id"),
        "protocol_id": protocol.get("protocol_id"),
        "brand": scope.get("brand"),
    }
    for field, expected in expected_links.items():
        if evidence.get(field) != expected:
            report.error(f"evidence.{field}", f"must match research package value {expected!r}")
    if protocol.get("status") != "frozen":
        report.error("research.query_protocol.status", "evidence scoring requires a frozen query protocol")

    source_ids = {
        item.get("source_id")
        for item in context.get("sources", [])
        if isinstance(item, dict) and isinstance(item.get("source_id"), str)
    }
    _validate_foundation(evidence.get("foundation"), source_ids, report)
    query_by_id = {
        query.get("query_id"): query
        for query in protocol.get("queries", [])
        if isinstance(query, dict) and isinstance(query.get("query_id"), str)
    }
    observations = _array(evidence.get("observations"), "evidence.observations", report)
    observation_ids: set[str] = set()
    query_engine_observed_at: dict[tuple[str, str], set[Any]] = {}
    observation_fields = {
        "observation_id",
        "query_id",
        "source_type",
        "status",
        "engine",
        "observed_at",
        "raw_response",
        "position",
        "recommendation",
        "citations",
        "sentiment",
        "coverage",
        "fact_errors",
    }
    for index, observation in enumerate(observations):
        path = f"evidence.observations[{index}]"
        observation = _object(observation, path, report)
        _fields(observation, observation_fields, observation_fields, path, report)
        observation_id = observation.get("observation_id")
        if not _is_string(observation_id):
            report.error(f"{path}.observation_id", "expected non-empty observation id")
        elif observation_id in observation_ids:
            report.error(f"{path}.observation_id", f"duplicate observation id {observation_id!r}")
        observation_ids.add(observation_id)
        query_id = observation.get("query_id")
        query = query_by_id.get(query_id)
        if query is None:
            report.error(f"{path}.query_id", f"query {query_id!r} does not exist in the frozen protocol")
            allowed_engines: set[str] = set()
        else:
            allowed_engines = set(query.get("engines", []))
        engine_name = _validate_engine(observation.get("engine"), allowed_engines, f"{path}.engine", report)
        if engine_name is not None:
            pair = (query_id, engine_name)
            observed_at = observation.get("observed_at")
            pair_times = query_engine_observed_at.setdefault(pair, set())
            if observed_at in pair_times:
                report.error(path, f"duplicate query-engine observation {pair!r} at {observed_at!r}")
            pair_times.add(observed_at)
        if observation.get("source_type") not in SOURCE_TYPES:
            report.error(f"{path}.source_type", f"expected one of {sorted(SOURCE_TYPES)}, got {observation.get('source_type')!r}")
        _validate_observation_state(observation, path, report)

    if report.errors:
        assessment = {
            "status": "insufficient_data",
            "expected_observations": 0,
            "observed_count": 0,
            "unobserved_count": 0,
            "measured_engines": 0,
            "required_engines": DEPTH_REQUIRED_ENGINES.get(scope.get("depth"), 3),
            "limitations": ["sample sufficiency was not assessed because contract validation failed"],
        }
    else:
        assessment = assess_samples(research, evidence)
        for limitation in assessment["limitations"]:
            report.warning("evidence.observations", limitation)
    return {
        "valid": not report.errors,
        "errors": report.errors,
        "warnings": report.warnings,
        "assessment": assessment,
    }


def _load_json(path: str) -> Any:
    """Load UTF-8 JSON from a path or stdin marker"""

    if path == "-":
        return json.load(sys.stdin)
    with Path(path).open(encoding="utf-8") as file:
        return json.load(file)


def main() -> int:
    """Validate a research and evidence package pair"""

    parser = argparse.ArgumentParser(description="Validate Brand GEO v2 observation evidence")
    parser.add_argument("research_path")
    parser.add_argument("evidence_path")
    args = parser.parse_args()
    try:
        research = _load_json(args.research_path)
        evidence = _load_json(args.evidence_path)
    except (OSError, json.JSONDecodeError) as error:
        print(json.dumps({"valid": False, "errors": [{"path": "$", "message": str(error)}]}, ensure_ascii=False, indent=2))
        return 2
    result = validate_evidence_package(research, evidence)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

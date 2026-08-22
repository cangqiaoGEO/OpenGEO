#!/usr/bin/env python3
"""Validate Batch A research objects before GEO evidence collection

The JSON Schema files document the transport contract while this module enforces
cross-object business rules that JSON Schema cannot express clearly, including
reference integrity, evidence semantics, readiness gates, and query coverage
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "2.0.0"
DEPTH_MINIMUM_ENGINES = {"quick": 3, "standard": 3, "deep": 5}
REQUIRED_QUERY_TYPES = {
    "brand_direct",
    "category_recommendation",
    "solution",
    "brand_comparison",
}
ALLOWED_QUERY_TYPES = REQUIRED_QUERY_TYPES | {
    "customer_problem",
    "alternative",
    "risk",
    "fact_check",
}
ALLOWED_CLAIM_STATUSES = {"fact", "inference", "opinion", "unknown"}
ALLOWED_CONFIDENCE = {"high", "medium", "low", "unknown"}
ALLOWED_DEPTHS = set(DEPTH_MINIMUM_ENGINES)
ALLOWED_EXPECTED_EVIDENCE = {
    "position",
    "recommendation",
    "citations",
    "coverage",
    "sentiment",
    "fact_accuracy",
}
ALLOWED_SOURCE_TYPES = {
    "official",
    "institutional",
    "authoritative_media",
    "industry_report",
    "third_party",
    "community",
    "user_provided",
    "audit_artifact",
}
ALLOWED_VERIFICATION_STATUSES = {"verified", "partially_verified", "unverified"}
ALLOWED_COMMERCIAL_RELEVANCE = {"high", "medium", "low"}
ALLOWED_COMPETITOR_RELATIONSHIPS = {"direct", "alternative", "adjacent"}
ID_PATTERNS = {
    "scope": re.compile(r"^scope-[a-z0-9][a-z0-9-]*$"),
    "context": re.compile(r"^context-[a-z0-9][a-z0-9-]*$"),
    "protocol": re.compile(r"^protocol-[a-z0-9][a-z0-9-]*$"),
    "source": re.compile(r"^src-[a-z0-9][a-z0-9-]*$"),
    "query": re.compile(r"^q-[a-z0-9][a-z0-9-]*$"),
}


class ValidationReport:
    """Collect deterministic validation errors and non-blocking warnings"""

    def __init__(self) -> None:
        self.errors: list[dict[str, str]] = []
        self.warnings: list[dict[str, str]] = []

    def error(self, path: str, message: str) -> None:
        """Record a blocking contract or readiness violation"""

        self.errors.append({"path": path, "message": message})

    def warning(self, path: str, message: str) -> None:
        """Record a non-blocking research gap that should remain visible"""

        self.warnings.append({"path": path, "message": message})

    def as_dict(self) -> dict[str, Any]:
        """Return the stable CLI and test representation of the report"""

        return {
            "valid": not self.errors,
            "assessment": "ready" if not self.errors else "invalid",
            "errors": self.errors,
            "warnings": self.warnings,
        }


def _is_non_empty_string(value: Any) -> bool:
    """Return whether a value is a non-empty human-readable string"""

    return isinstance(value, str) and bool(value.strip())


def _require_object(value: Any, path: str, report: ValidationReport) -> dict[str, Any]:
    """Return an object value or record a type error and return an empty object"""

    if not isinstance(value, dict):
        report.error(path, f"expected object, got {type(value).__name__}")
        return {}
    return value


def _require_list(value: Any, path: str, report: ValidationReport) -> list[Any]:
    """Return a list value or record a type error and return an empty list"""

    if not isinstance(value, list):
        report.error(path, f"expected array, got {type(value).__name__}")
        return []
    return value


def _require_fields(obj: dict[str, Any], fields: set[str], path: str, report: ValidationReport) -> None:
    """Record every missing required field instead of failing at the first one"""

    for field in sorted(fields):
        if field not in obj:
            report.error(f"{path}.{field}", "required field is missing")


def _reject_extra_fields(obj: dict[str, Any], fields: set[str], path: str, report: ValidationReport) -> None:
    """Reject undeclared fields so runtime validation matches additionalProperties=false"""

    for field in sorted(set(obj) - fields):
        report.error(f"{path}.{field}", "field is not allowed by the v2 contract")


def _validate_string_list(value: Any, path: str, report: ValidationReport) -> list[str]:
    """Validate a list of unique non-empty strings without resolving references"""

    entries = _require_list(value, path, report)
    seen: set[str] = set()
    for index, entry in enumerate(entries):
        item_path = f"{path}[{index}]"
        if not _is_non_empty_string(entry):
            report.error(item_path, "expected non-empty string")
        elif entry in seen:
            report.error(item_path, f"duplicate value {entry!r}")
        seen.add(entry)
    return [entry for entry in entries if isinstance(entry, str) and entry.strip()]


def _validate_id(value: Any, kind: str, path: str, report: ValidationReport) -> None:
    """Validate a stable identifier against its domain prefix"""

    pattern = ID_PATTERNS[kind]
    if not isinstance(value, str) or not pattern.fullmatch(value):
        report.error(path, f"expected {kind} id matching {pattern.pattern!r}, got {value!r}")


def _validate_iso_date(value: Any, path: str, report: ValidationReport) -> None:
    """Validate an ISO 8601 calendar date"""

    try:
        date.fromisoformat(value)
    except (TypeError, ValueError):
        report.error(path, f"expected ISO date YYYY-MM-DD, got {value!r}")


def _validate_iso_datetime(value: Any, path: str, report: ValidationReport) -> None:
    """Validate an ISO 8601 timestamp and require an explicit timezone"""

    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            raise ValueError("timezone missing")
    except (TypeError, ValueError):
        report.error(path, f"expected ISO date-time with timezone, got {value!r}")


def _validate_unique_ids(items: list[Any], id_field: str, path: str, report: ValidationReport) -> set[str]:
    """Return unique ids while reporting malformed entries and duplicates"""

    found: set[str] = set()
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            report.error(f"{path}[{index}]", "expected object")
            continue
        item_id = item.get(id_field)
        if not _is_non_empty_string(item_id):
            report.error(f"{path}[{index}].{id_field}", "expected non-empty string")
        elif item_id in found:
            report.error(f"{path}[{index}].{id_field}", f"duplicate id {item_id!r}")
        else:
            found.add(item_id)
    return found


def _validate_reference_list(
    values: Any,
    allowed: set[str],
    path: str,
    report: ValidationReport,
    *,
    minimum: int = 0,
) -> list[str]:
    """Validate a unique string list whose values must resolve to known ids"""

    entries = _require_list(values, path, report)
    if len(entries) < minimum:
        report.error(path, f"expected at least {minimum} item(s), got {len(entries)}")
    seen: set[str] = set()
    for index, value in enumerate(entries):
        item_path = f"{path}[{index}]"
        if not _is_non_empty_string(value):
            report.error(item_path, "expected non-empty string reference")
        elif value in seen:
            report.error(item_path, f"duplicate reference {value!r}")
        elif value not in allowed:
            report.error(item_path, f"unresolved reference {value!r}")
        seen.add(value)
    return [value for value in entries if isinstance(value, str)]


def validate_scope(scope: Any, report: ValidationReport) -> dict[str, Any]:
    """Validate ResearchScope structure and readiness semantics"""

    scope = _require_object(scope, "scope", report)
    required = {
        "schema_version",
        "scope_id",
        "status",
        "brand",
        "domain",
        "market",
        "language",
        "audiences",
        "competitors",
        "depth",
        "as_of",
        "exclusions",
    }
    _require_fields(scope, required, "scope", report)
    _reject_extra_fields(scope, required, "scope", report)
    if scope.get("schema_version") != SCHEMA_VERSION:
        report.error("scope.schema_version", f"expected {SCHEMA_VERSION!r}, got {scope.get('schema_version')!r}")
    _validate_id(scope.get("scope_id"), "scope", "scope.scope_id", report)
    if scope.get("status") not in {"draft", "ready"}:
        report.error("scope.status", f"expected 'draft' or 'ready', got {scope.get('status')!r}")
    if not _is_non_empty_string(scope.get("brand")):
        report.error("scope.brand", "expected non-empty brand")
    depth = scope.get("depth")
    if depth not in ALLOWED_DEPTHS:
        report.error("scope.depth", f"expected one of {sorted(ALLOWED_DEPTHS)}, got {depth!r}")
    _validate_iso_date(scope.get("as_of"), "scope.as_of", report)
    audiences = _validate_string_list(scope.get("audiences"), "scope.audiences", report)
    _validate_string_list(scope.get("competitors"), "scope.competitors", report)
    _validate_string_list(scope.get("exclusions"), "scope.exclusions", report)

    missing_context = [
        field
        for field in ("domain", "market", "language")
        if not _is_non_empty_string(scope.get(field))
    ]
    if scope.get("status") == "ready":
        for field in missing_context:
            report.error(f"scope.{field}", "must be known when scope.status is 'ready'")
        if not audiences:
            report.error("scope.audiences", "must contain at least one audience when scope.status is 'ready'")
    else:
        for field in missing_context:
            report.warning(f"scope.{field}", "research context is still unknown")
        if not audiences:
            report.warning("scope.audiences", "target audiences are still unknown")
    return scope


def _validate_claim(
    claim: Any,
    path: str,
    source_ids: set[str],
    verified_source_ids: set[str],
    report: ValidationReport,
) -> None:
    """Validate fact, inference, opinion, and unknown evidence semantics"""

    claim = _require_object(claim, path, report)
    fields = {"status", "confidence", "evidence_ids"}
    _require_fields(claim, fields, path, report)
    _reject_extra_fields(claim, fields, path, report)
    status = claim.get("status")
    confidence = claim.get("confidence")
    if status not in ALLOWED_CLAIM_STATUSES:
        report.error(f"{path}.status", f"expected one of {sorted(ALLOWED_CLAIM_STATUSES)}, got {status!r}")
    if confidence not in ALLOWED_CONFIDENCE:
        report.error(f"{path}.confidence", f"expected one of {sorted(ALLOWED_CONFIDENCE)}, got {confidence!r}")
    evidence_ids = _validate_reference_list(claim.get("evidence_ids"), source_ids, f"{path}.evidence_ids", report)
    if status in {"fact", "inference"} and not evidence_ids:
        report.error(f"{path}.evidence_ids", f"{status} claims require at least one source")
    if status == "fact" and evidence_ids and not any(source_id in verified_source_ids for source_id in evidence_ids):
        report.error(f"{path}.evidence_ids", "fact claims require at least one verified or partially verified source")
    if status == "unknown":
        if evidence_ids:
            report.error(f"{path}.evidence_ids", "unknown claims cannot cite evidence as established support")
        if confidence != "unknown":
            report.error(f"{path}.confidence", "unknown claims must use confidence 'unknown'")


def validate_context(
    context: Any,
    scope: dict[str, Any],
    report: ValidationReport,
) -> dict[str, Any]:
    """Validate DomainContext evidence, references, and minimum ready-state model"""

    context = _require_object(context, "domain_context", report)
    required = {
        "schema_version",
        "context_id",
        "scope_id",
        "status",
        "sources",
        "brand_positioning",
        "target_customers",
        "customer_problems",
        "products",
        "business_scenarios",
        "competitors",
        "high_value_questions",
        "unknowns",
    }
    _require_fields(context, required, "domain_context", report)
    _reject_extra_fields(context, required, "domain_context", report)
    if context.get("schema_version") != SCHEMA_VERSION:
        report.error("domain_context.schema_version", f"expected {SCHEMA_VERSION!r}, got {context.get('schema_version')!r}")
    _validate_id(context.get("context_id"), "context", "domain_context.context_id", report)
    if context.get("scope_id") != scope.get("scope_id"):
        report.error("domain_context.scope_id", "must reference scope.scope_id")
    if context.get("status") not in {"draft", "ready"}:
        report.error("domain_context.status", f"expected 'draft' or 'ready', got {context.get('status')!r}")

    sources = _require_list(context.get("sources"), "domain_context.sources", report)
    source_ids = _validate_unique_ids(sources, "source_id", "domain_context.sources", report)
    verified_source_ids: set[str] = set()
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            continue
        source_path = f"domain_context.sources[{index}]"
        required_source_fields = {"source_id", "source_type", "title", "url", "verification_status", "retrieved_at"}
        source_fields = required_source_fields | {"artifact_path"}
        _require_fields(source, required_source_fields, source_path, report)
        _reject_extra_fields(source, source_fields, source_path, report)
        _validate_id(source.get("source_id"), "source", f"{source_path}.source_id", report)
        if source.get("source_type") not in ALLOWED_SOURCE_TYPES:
            report.error(f"{source_path}.source_type", f"expected one of {sorted(ALLOWED_SOURCE_TYPES)}, got {source.get('source_type')!r}")
        if not _is_non_empty_string(source.get("title")):
            report.error(f"{source_path}.title", "expected non-empty source title")
        if source.get("verification_status") not in ALLOWED_VERIFICATION_STATUSES:
            report.error(f"{source_path}.verification_status", f"expected one of {sorted(ALLOWED_VERIFICATION_STATUSES)}, got {source.get('verification_status')!r}")
        if source.get("verification_status") in {"verified", "partially_verified"}:
            verified_source_ids.add(source.get("source_id"))
        if source.get("source_type") in {"user_provided", "audit_artifact"}:
            if source.get("url") is not None:
                report.error(f"{source_path}.url", "controlled artifacts must use null URL")
            artifact_path = source.get("artifact_path")
            if not _is_non_empty_string(artifact_path):
                report.error(f"{source_path}.artifact_path", "controlled artifact source requires a project-relative path")
            elif Path(artifact_path).is_absolute() or ".." in Path(artifact_path).parts:
                report.error(f"{source_path}.artifact_path", "expected a safe project-relative artifact path")
        elif not isinstance(source.get("url"), str) or not source["url"].startswith(("http://", "https://")):
            report.error(f"{source_path}.url", f"expected HTTP(S) URL, got {source.get('url')!r}")
        _validate_iso_datetime(source.get("retrieved_at"), f"{source_path}.retrieved_at", report)

    positioning = _require_object(context.get("brand_positioning"), "domain_context.brand_positioning", report)
    positioning_fields = {"value", "claim"}
    _require_fields(positioning, positioning_fields, "domain_context.brand_positioning", report)
    _reject_extra_fields(positioning, positioning_fields, "domain_context.brand_positioning", report)
    _validate_claim(positioning.get("claim"), "domain_context.brand_positioning.claim", source_ids, verified_source_ids, report)

    collections = {
        "target_customers": "id",
        "customer_problems": "id",
        "products": "id",
        "business_scenarios": "id",
        "competitors": "id",
        "high_value_questions": "id",
        "unknowns": "id",
    }
    collection_values: dict[str, list[Any]] = {}
    collection_ids: dict[str, set[str]] = {}
    for name, id_field in collections.items():
        values = _require_list(context.get(name), f"domain_context.{name}", report)
        collection_values[name] = values
        collection_ids[name] = _validate_unique_ids(values, id_field, f"domain_context.{name}", report)

    for name in ("target_customers", "products", "business_scenarios", "competitors"):
        for index, item in enumerate(collection_values[name]):
            if isinstance(item, dict):
                path = f"domain_context.{name}[{index}]"
                fields = {"id", "name", "claim"}
                if name == "competitors":
                    fields.add("relationship")
                _require_fields(item, fields, path, report)
                _reject_extra_fields(item, fields, path, report)
                if not _is_non_empty_string(item.get("name")):
                    report.error(f"{path}.name", "expected non-empty name")
                if name == "competitors" and item.get("relationship") not in ALLOWED_COMPETITOR_RELATIONSHIPS:
                    report.error(f"{path}.relationship", f"expected one of {sorted(ALLOWED_COMPETITOR_RELATIONSHIPS)}, got {item.get('relationship')!r}")
                _validate_claim(item.get("claim"), f"domain_context.{name}[{index}].claim", source_ids, verified_source_ids, report)

    for index, problem in enumerate(collection_values["customer_problems"]):
        if not isinstance(problem, dict):
            continue
        path = f"domain_context.customer_problems[{index}]"
        problem_fields = {"id", "description", "customer_ids", "claim"}
        _require_fields(problem, problem_fields, path, report)
        _reject_extra_fields(problem, problem_fields, path, report)
        if not _is_non_empty_string(problem.get("description")):
            report.error(f"{path}.description", "expected non-empty problem description")
        _validate_reference_list(problem.get("customer_ids"), collection_ids["target_customers"], f"{path}.customer_ids", report, minimum=1)
        _validate_claim(problem.get("claim"), f"{path}.claim", source_ids, verified_source_ids, report)

    for index, question in enumerate(collection_values["high_value_questions"]):
        if not isinstance(question, dict):
            continue
        path = f"domain_context.high_value_questions[{index}]"
        question_fields = {"id", "question", "customer_ids", "problem_ids", "scenario_ids", "commercial_relevance", "evidence_ids"}
        _require_fields(question, question_fields, path, report)
        _reject_extra_fields(question, question_fields, path, report)
        if not _is_non_empty_string(question.get("question")):
            report.error(f"{path}.question", "expected non-empty high-value question")
        if question.get("commercial_relevance") not in ALLOWED_COMMERCIAL_RELEVANCE:
            report.error(f"{path}.commercial_relevance", f"expected one of {sorted(ALLOWED_COMMERCIAL_RELEVANCE)}, got {question.get('commercial_relevance')!r}")
        _validate_reference_list(question.get("customer_ids"), collection_ids["target_customers"], f"{path}.customer_ids", report, minimum=1)
        _validate_reference_list(question.get("problem_ids"), collection_ids["customer_problems"], f"{path}.problem_ids", report, minimum=1)
        _validate_reference_list(question.get("scenario_ids"), collection_ids["business_scenarios"], f"{path}.scenario_ids", report)
        _validate_reference_list(question.get("evidence_ids"), source_ids, f"{path}.evidence_ids", report, minimum=1)

    for index, unknown in enumerate(collection_values["unknowns"]):
        if not isinstance(unknown, dict):
            continue
        path = f"domain_context.unknowns[{index}]"
        fields = {"id", "question", "impact"}
        _require_fields(unknown, fields, path, report)
        _reject_extra_fields(unknown, fields, path, report)
        for field in ("question", "impact"):
            if not _is_non_empty_string(unknown.get(field)):
                report.error(f"{path}.{field}", "expected non-empty string")

    if context.get("status") == "ready":
        if scope.get("status") != "ready":
            report.error("domain_context.status", "cannot be 'ready' while scope.status is not 'ready'")
        readiness_collections = ("target_customers", "customer_problems", "products", "business_scenarios")
        for name in readiness_collections:
            if not collection_values[name]:
                report.error(f"domain_context.{name}", "must contain at least one item when domain_context.status is 'ready'")
        if not _is_non_empty_string(positioning.get("value")):
            report.error("domain_context.brand_positioning.value", "must be known when domain_context.status is 'ready'")
        if len(collection_values["high_value_questions"]) < 4:
            report.error("domain_context.high_value_questions", "must contain at least four questions when domain_context.status is 'ready'")
        scope_audiences = set(scope.get("audiences", []))
        represented_audiences = {
            item.get("name") for item in collection_values["target_customers"] if isinstance(item, dict)
        }
        missing_audiences = sorted(scope_audiences - represented_audiences)
        if missing_audiences:
            report.error("domain_context.target_customers", f"does not represent scope audiences: {', '.join(missing_audiences)}")
    return context


def validate_protocol(
    protocol: Any,
    scope: dict[str, Any],
    context: dict[str, Any],
    report: ValidationReport,
) -> dict[str, Any]:
    """Validate QueryProtocol traceability, frozen gates, and coverage"""

    protocol = _require_object(protocol, "query_protocol", report)
    required = {"schema_version", "protocol_id", "scope_id", "context_id", "status", "created_at", "queries"}
    _require_fields(protocol, required, "query_protocol", report)
    _reject_extra_fields(protocol, required, "query_protocol", report)
    if protocol.get("schema_version") != SCHEMA_VERSION:
        report.error("query_protocol.schema_version", f"expected {SCHEMA_VERSION!r}, got {protocol.get('schema_version')!r}")
    _validate_id(protocol.get("protocol_id"), "protocol", "query_protocol.protocol_id", report)
    if protocol.get("scope_id") != scope.get("scope_id"):
        report.error("query_protocol.scope_id", "must reference scope.scope_id")
    if protocol.get("context_id") != context.get("context_id"):
        report.error("query_protocol.context_id", "must reference domain_context.context_id")
    if protocol.get("status") not in {"draft", "frozen"}:
        report.error("query_protocol.status", f"expected 'draft' or 'frozen', got {protocol.get('status')!r}")
    _validate_iso_datetime(protocol.get("created_at"), "query_protocol.created_at", report)

    queries = _require_list(protocol.get("queries"), "query_protocol.queries", report)
    _validate_unique_ids(queries, "query_id", "query_protocol.queries", report)
    customer_ids = _validate_unique_ids(context.get("target_customers", []), "id", "domain_context.target_customers", ValidationReport())
    problem_ids = _validate_unique_ids(context.get("customer_problems", []), "id", "domain_context.customer_problems", ValidationReport())
    hvq_ids = _validate_unique_ids(context.get("high_value_questions", []), "id", "domain_context.high_value_questions", ValidationReport())
    competitor_ids = _validate_unique_ids(context.get("competitors", []), "id", "domain_context.competitors", ValidationReport())
    observed_types: set[str] = set()
    engine_sets: list[set[str]] = []
    minimum_engines = DEPTH_MINIMUM_ENGINES.get(scope.get("depth"), 3)

    for index, query in enumerate(queries):
        if not isinstance(query, dict):
            continue
        path = f"query_protocol.queries[{index}]"
        query_fields = {
            "query_id",
            "query_type",
            "query",
            "audience_ids",
            "problem_ids",
            "high_value_question_ids",
            "business_rationale",
            "commercial_relevance",
            "expected_evidence",
            "engines",
            "competitor_ids",
        }
        required_query_fields = query_fields - {"competitor_ids"}
        _require_fields(query, required_query_fields, path, report)
        _reject_extra_fields(query, query_fields, path, report)
        _validate_id(query.get("query_id"), "query", f"{path}.query_id", report)
        query_type = query.get("query_type")
        if query_type not in ALLOWED_QUERY_TYPES:
            report.error(f"{path}.query_type", f"expected one of {sorted(ALLOWED_QUERY_TYPES)}, got {query_type!r}")
        else:
            observed_types.add(query_type)
        if not _is_non_empty_string(query.get("query")):
            report.error(f"{path}.query", "expected non-empty query text")
        if not _is_non_empty_string(query.get("business_rationale")):
            report.error(f"{path}.business_rationale", "must explain why this query matters to the business")
        if query.get("commercial_relevance") not in ALLOWED_COMMERCIAL_RELEVANCE:
            report.error(f"{path}.commercial_relevance", f"expected one of {sorted(ALLOWED_COMMERCIAL_RELEVANCE)}, got {query.get('commercial_relevance')!r}")
        _validate_reference_list(query.get("audience_ids"), customer_ids, f"{path}.audience_ids", report, minimum=1)
        _validate_reference_list(query.get("problem_ids"), problem_ids, f"{path}.problem_ids", report, minimum=1)
        _validate_reference_list(query.get("high_value_question_ids"), hvq_ids, f"{path}.high_value_question_ids", report, minimum=1)
        competitor_refs = _validate_reference_list(query.get("competitor_ids", []), competitor_ids, f"{path}.competitor_ids", report)
        if query_type == "brand_comparison" and not competitor_refs:
            report.error(f"{path}.competitor_ids", "brand_comparison queries require at least one competitor")

        expected_evidence = _require_list(query.get("expected_evidence"), f"{path}.expected_evidence", report)
        seen_evidence: set[str] = set()
        for evidence_index, value in enumerate(expected_evidence):
            if value not in ALLOWED_EXPECTED_EVIDENCE:
                report.error(f"{path}.expected_evidence[{evidence_index}]", f"unsupported evidence type {value!r}")
            elif value in seen_evidence:
                report.error(f"{path}.expected_evidence[{evidence_index}]", f"duplicate evidence type {value!r}")
            seen_evidence.add(value)
        engines = _require_list(query.get("engines"), f"{path}.engines", report)
        engine_set = {value for value in engines if _is_non_empty_string(value)}
        if len(engine_set) != len(engines):
            report.error(f"{path}.engines", "engine names must be non-empty and unique")
        if len(engine_set) < minimum_engines:
            report.error(f"{path}.engines", f"depth {scope.get('depth')!r} requires at least {minimum_engines} engines")
        engine_sets.append(engine_set)

    if protocol.get("status") == "frozen":
        if scope.get("status") != "ready" or context.get("status") != "ready":
            report.error("query_protocol.status", "cannot be 'frozen' until scope and domain_context are both 'ready'")
        missing_types = sorted(REQUIRED_QUERY_TYPES - observed_types)
        if missing_types:
            report.error("query_protocol.queries", f"frozen protocol is missing required query types: {', '.join(missing_types)}")
        if len(queries) < 4:
            report.error("query_protocol.queries", "frozen protocol requires at least four queries")
        if engine_sets and any(engine_set != engine_sets[0] for engine_set in engine_sets[1:]):
            report.error("query_protocol.queries", "all frozen queries must use the same engine set for comparable observations")
    return protocol


def validate_research_package(data: Any) -> dict[str, Any]:
    """Validate the full Batch A package and return a serializable report"""

    report = ValidationReport()
    package = _require_object(data, "$", report)
    fields = {"scope", "domain_context", "query_protocol"}
    _require_fields(package, fields, "$", report)
    _reject_extra_fields(package, fields, "$", report)
    scope = validate_scope(package.get("scope"), report)
    context = validate_context(package.get("domain_context"), scope, report)
    validate_protocol(package.get("query_protocol"), scope, context, report)
    return report.as_dict()


def main() -> int:
    """Read a research package, print validation JSON, and expose failure by exit code"""

    parser = argparse.ArgumentParser(description="Validate Brand GEO Batch A research objects")
    parser.add_argument("path", help="research package JSON path, or - for stdin")
    args = parser.parse_args()
    try:
        if args.path == "-":
            data = json.load(sys.stdin)
        else:
            with Path(args.path).open(encoding="utf-8") as file:
                data = json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        print(json.dumps({"valid": False, "errors": [{"path": "$", "message": str(error)}]}, ensure_ascii=False, indent=2))
        return 2
    result = validate_research_package(data)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

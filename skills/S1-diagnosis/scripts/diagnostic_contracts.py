#!/usr/bin/env python3
"""Validate R1 diagnostic MVP objects against one existing v2 research package"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from research_validate import validate_research_package  # noqa: E402


NEW_SCHEMA_VERSION = "1.0.0"
PACKAGE_FIELDS = {
    "schema_version",
    "diagnostic_run",
    "brand_entity_profile",
    "industry_profile",
    "measurement_plan",
    "content_foundation_protocol",
}
REPORT_MODES = {"exploratory", "diagnostic", "experimental_score"}
READY_RUN_STATES = {"ready", "collecting", "analyzing", "completed"}
STAGE_STATES = {"pending", "in_progress", "completed", "blocked", "not_applicable"}
RUN_ID = re.compile(r"^run-[a-z0-9][a-z0-9-]*$")


class DiagnosticReport:
    """Collect deterministic R1 contract errors and non-blocking gaps"""

    def __init__(self) -> None:
        self.errors: list[dict[str, str]] = []
        self.warnings: list[dict[str, str]] = []

    def error(self, path: str, message: str) -> None:
        """Record a blocking contract violation"""

        self.errors.append({"path": path, "message": message})

    def warning(self, path: str, message: str) -> None:
        """Record a visible but non-blocking diagnostic limitation"""

        self.warnings.append({"path": path, "message": message})

    def as_dict(self) -> dict[str, Any]:
        """Return the stable CLI representation"""

        return {
            "valid": not self.errors,
            "assessment": "ready" if not self.errors else "invalid",
            "errors": self.errors,
            "warnings": self.warnings,
        }


def _object(value: Any, path: str, report: DiagnosticReport) -> dict[str, Any]:
    """Return an object or report its type error"""

    if not isinstance(value, dict):
        report.error(path, f"expected object, got {type(value).__name__}")
        return {}
    return value


def _array(value: Any, path: str, report: DiagnosticReport) -> list[Any]:
    """Return an array or report its type error"""

    if not isinstance(value, list):
        report.error(path, f"expected array, got {type(value).__name__}")
        return []
    return value


def _fields(obj: dict[str, Any], required: set[str], allowed: set[str], path: str, report: DiagnosticReport) -> None:
    """Enforce required and additional-properties semantics"""

    for field in sorted(required - set(obj)):
        report.error(f"{path}.{field}", "required field is missing")
    for field in sorted(set(obj) - allowed):
        report.error(f"{path}.{field}", "field is not allowed by the R1 contract")


def _string(value: Any, path: str, report: DiagnosticReport) -> bool:
    """Validate one non-empty string"""

    valid = isinstance(value, str) and bool(value.strip())
    if not valid:
        report.error(path, "expected non-empty string")
    return valid


def _datetime(value: Any, path: str, report: DiagnosticReport) -> None:
    """Validate an ISO timestamp with an explicit timezone"""

    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            raise ValueError("timezone missing")
    except (TypeError, ValueError):
        report.error(path, "expected ISO date-time with timezone")


def _date(value: Any, path: str, report: DiagnosticReport) -> None:
    """Validate an ISO date"""

    try:
        date.fromisoformat(value)
    except (TypeError, ValueError):
        report.error(path, "expected ISO date YYYY-MM-DD")


def _unique_ids(items: list[Any], field: str, path: str, report: DiagnosticReport) -> set[str]:
    """Collect unique identifiers from an object array"""

    result: set[str] = set()
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            report.error(f"{path}[{index}]", "expected object")
            continue
        value = item.get(field)
        if not _string(value, f"{path}[{index}].{field}", report):
            continue
        if value in result:
            report.error(f"{path}[{index}].{field}", f"duplicate id {value!r}")
        result.add(value)
    return result


def _references(values: Any, allowed: set[str], path: str, report: DiagnosticReport, *, minimum: int = 0) -> list[str]:
    """Validate a unique list of resolvable string references"""

    entries = _array(values, path, report)
    if len(entries) < minimum:
        report.error(path, f"expected at least {minimum} item(s)")
    seen: set[str] = set()
    result: list[str] = []
    for index, value in enumerate(entries):
        item_path = f"{path}[{index}]"
        if not _string(value, item_path, report):
            continue
        if value in seen:
            report.error(item_path, f"duplicate reference {value!r}")
        elif value not in allowed:
            report.error(item_path, f"unresolved reference {value!r}")
        seen.add(value)
        result.append(value)
    return result


def _version(obj: dict[str, Any], path: str, report: DiagnosticReport) -> None:
    """Require the shared R1 object version"""

    if obj.get("schema_version") != NEW_SCHEMA_VERSION:
        report.error(f"{path}.schema_version", f"expected {NEW_SCHEMA_VERSION!r}")


def _validate_run(run: Any, research: dict[str, Any], report: DiagnosticReport) -> dict[str, Any]:
    """Validate the root run manifest and its references to existing v2 objects"""

    path = "diagnostic_run"
    run = _object(run, path, report)
    fields = {"schema_version", "run_id", "status", "report_mode", "created_at", "as_of", "object_refs", "stage_status", "limitations"}
    _fields(run, fields, fields, path, report)
    _version(run, path, report)
    if not isinstance(run.get("run_id"), str) or not RUN_ID.fullmatch(run["run_id"]):
        report.error(f"{path}.run_id", "expected run id matching '^run-[a-z0-9][a-z0-9-]*$'")
    if run.get("status") not in {"planning", "ready", "collecting", "analyzing", "completed", "blocked"}:
        report.error(f"{path}.status", "unsupported run status")
    if run.get("report_mode") not in REPORT_MODES:
        report.error(f"{path}.report_mode", f"expected one of {sorted(REPORT_MODES)}")
    _datetime(run.get("created_at"), f"{path}.created_at", report)
    _date(run.get("as_of"), f"{path}.as_of", report)
    refs = _object(run.get("object_refs"), f"{path}.object_refs", report)
    ref_fields = {"scope_id", "context_id", "protocol_id", "brand_profile_id", "industry_profile_id", "measurement_plan_id", "content_protocol_id"}
    _fields(refs, ref_fields, ref_fields, f"{path}.object_refs", report)
    expected = {
        "scope_id": research.get("scope", {}).get("scope_id"),
        "context_id": research.get("domain_context", {}).get("context_id"),
        "protocol_id": research.get("query_protocol", {}).get("protocol_id"),
    }
    for field, value in expected.items():
        if refs.get(field) != value:
            report.error(f"{path}.object_refs.{field}", f"must reference research package {field}")
    stages = _object(run.get("stage_status"), f"{path}.stage_status", report)
    stage_fields = {"research", "entity_resolution", "industry_adaptation", "query_design", "content_foundation", "collection", "annotation", "audit", "reporting"}
    _fields(stages, stage_fields, stage_fields, f"{path}.stage_status", report)
    for name in stage_fields:
        if stages.get(name) not in STAGE_STATES:
            report.error(f"{path}.stage_status.{name}", f"expected one of {sorted(STAGE_STATES)}")
    limitations = _array(run.get("limitations"), f"{path}.limitations", report)
    for index, value in enumerate(limitations):
        _string(value, f"{path}.limitations[{index}]", report)
    return run


def _validate_brand(profile: Any, run: dict[str, Any], research: dict[str, Any], source_ids: set[str], report: DiagnosticReport) -> tuple[dict[str, Any], set[str]]:
    """Validate entity aliases, locations, channels, and relation evidence"""

    path = "brand_entity_profile"
    profile = _object(profile, path, report)
    fields = {"schema_version", "brand_profile_id", "run_id", "status", "canonical_name", "entity_type", "match_terms", "locations", "official_channels", "relations", "unknowns"}
    _fields(profile, fields, fields, path, report)
    _version(profile, path, report)
    if profile.get("run_id") != run.get("run_id"):
        report.error(f"{path}.run_id", "must reference diagnostic_run.run_id")
    if profile.get("status") not in {"draft", "ready"}:
        report.error(f"{path}.status", "expected 'draft' or 'ready'")
    _string(profile.get("canonical_name"), f"{path}.canonical_name", report)
    if profile.get("entity_type") not in {"brand", "company", "store", "product_line", "service_brand", "mixed"}:
        report.error(f"{path}.entity_type", "unsupported entity type")

    terms = _array(profile.get("match_terms"), f"{path}.match_terms", report)
    _unique_ids(terms, "term_id", f"{path}.match_terms", report)
    verified_terms: set[str] = set()
    for index, item in enumerate(terms):
        if not isinstance(item, dict):
            continue
        item_path = f"{path}.match_terms[{index}]"
        item_fields = {"term_id", "term", "term_type", "verification_status", "evidence_ids"}
        _fields(item, item_fields, item_fields, item_path, report)
        if _string(item.get("term"), f"{item_path}.term", report) and item.get("verification_status") in {"verified", "partially_verified"}:
            verified_terms.add(item["term"])
        if item.get("term_type") not in {"canonical", "brand_alias", "legal_name", "store_name", "former_name", "transliteration", "colloquial"}:
            report.error(f"{item_path}.term_type", "unsupported match term type")
        if item.get("verification_status") not in {"verified", "partially_verified", "unverified"}:
            report.error(f"{item_path}.verification_status", "unsupported verification status")
        evidence_ids = _references(item.get("evidence_ids"), source_ids, f"{item_path}.evidence_ids", report)
        if item.get("verification_status") != "unverified" and not evidence_ids:
            report.error(f"{item_path}.evidence_ids", "verified match terms require source evidence")
    scope_brand = research.get("scope", {}).get("brand")
    if scope_brand not in verified_terms:
        report.error(f"{path}.match_terms", "scope brand must resolve to a verified canonical name or alias")
    if profile.get("canonical_name") not in {item.get("term") for item in terms if isinstance(item, dict) and item.get("term_type") == "canonical"}:
        report.error(f"{path}.match_terms", "canonical_name requires a canonical match term")

    locations = _array(profile.get("locations"), f"{path}.locations", report)
    location_ids = _unique_ids(locations, "location_id", f"{path}.locations", report)
    for index, item in enumerate(locations):
        if not isinstance(item, dict):
            continue
        item_path = f"{path}.locations[{index}]"
        item_fields = {"location_id", "name", "market", "address", "service_area", "evidence_ids"}
        _fields(item, item_fields, item_fields, item_path, report)
        _string(item.get("name"), f"{item_path}.name", report)
        _string(item.get("market"), f"{item_path}.market", report)
        _references(item.get("evidence_ids"), source_ids, f"{item_path}.evidence_ids", report)
        service_area = _array(item.get("service_area"), f"{item_path}.service_area", report)
        for value_index, value in enumerate(service_area):
            _string(value, f"{item_path}.service_area[{value_index}]", report)

    for collection_name, id_field, allowed_fields in (
        ("official_channels", "channel_id", {"channel_id", "channel_type", "url", "verification_status", "evidence_ids"}),
        ("relations", "relation_id", {"relation_id", "subject", "relation_type", "object", "verification_status", "evidence_ids"}),
    ):
        entries = _array(profile.get(collection_name), f"{path}.{collection_name}", report)
        _unique_ids(entries, id_field, f"{path}.{collection_name}", report)
        for index, item in enumerate(entries):
            if not isinstance(item, dict):
                continue
            item_path = f"{path}.{collection_name}[{index}]"
            _fields(item, allowed_fields, allowed_fields, item_path, report)
            _references(item.get("evidence_ids"), source_ids, f"{item_path}.evidence_ids", report)
    _array(profile.get("unknowns"), f"{path}.unknowns", report)
    if profile.get("status") == "ready" and not verified_terms:
        report.error(f"{path}.match_terms", "ready entity profile requires at least one verified match term")
    return profile, location_ids


def _validate_industry(profile: Any, run: dict[str, Any], source_ids: set[str], report: DiagnosticReport) -> tuple[dict[str, Any], set[str]]:
    """Validate industry decision factors without imposing one industry's inventory"""

    path = "industry_profile"
    profile = _object(profile, path, report)
    fields = {"schema_version", "industry_profile_id", "run_id", "status", "industry", "operating_scope", "service_modes", "market_characteristics", "decision_factors", "unknowns"}
    _fields(profile, fields, fields, path, report)
    _version(profile, path, report)
    if profile.get("run_id") != run.get("run_id"):
        report.error(f"{path}.run_id", "must reference diagnostic_run.run_id")
    if profile.get("status") not in {"draft", "ready"}:
        report.error(f"{path}.status", "expected 'draft' or 'ready'")
    _string(profile.get("industry"), f"{path}.industry", report)
    if profile.get("operating_scope") not in {"local", "regional", "national", "global", "mixed"}:
        report.error(f"{path}.operating_scope", "unsupported operating scope")
    modes = _array(profile.get("service_modes"), f"{path}.service_modes", report)
    allowed_modes = {"in_store", "on_site", "remote", "online_only", "hybrid"}
    for index, value in enumerate(modes):
        if value not in allowed_modes:
            report.error(f"{path}.service_modes[{index}]", f"expected one of {sorted(allowed_modes)}")
    characteristics = _array(profile.get("market_characteristics"), f"{path}.market_characteristics", report)
    allowed_characteristics = {"location_sensitive", "appointment_based", "in_person_experience", "authorized_reseller", "high_consideration", "project_delivery", "recurring_service", "regulated", "digital_self_service"}
    for index, value in enumerate(characteristics):
        if value not in allowed_characteristics:
            report.error(f"{path}.market_characteristics[{index}]", f"expected one of {sorted(allowed_characteristics)}")
    factors = _array(profile.get("decision_factors"), f"{path}.decision_factors", report)
    factor_ids = _unique_ids(factors, "factor_id", f"{path}.decision_factors", report)
    required_factors = 0
    for index, item in enumerate(factors):
        if not isinstance(item, dict):
            continue
        item_path = f"{path}.decision_factors[{index}]"
        item_fields = {"factor_id", "name", "description", "importance", "applicability", "evidence_ids"}
        _fields(item, item_fields, item_fields, item_path, report)
        _string(item.get("name"), f"{item_path}.name", report)
        _string(item.get("description"), f"{item_path}.description", report)
        evidence_ids = _references(item.get("evidence_ids"), source_ids, f"{item_path}.evidence_ids", report)
        if item.get("applicability") == "required":
            required_factors += 1
            if profile.get("status") == "ready" and not evidence_ids:
                report.error(f"{item_path}.evidence_ids", "required factors need evidence when industry profile is ready")
    if profile.get("status") == "ready" and required_factors == 0:
        report.error(f"{path}.decision_factors", "ready industry profile requires at least one required decision factor")
    _array(profile.get("unknowns"), f"{path}.unknowns", report)
    return profile, factor_ids


def _validate_content(protocol: Any, run: dict[str, Any], brand: dict[str, Any], industry: dict[str, Any], factor_ids: set[str], report: DiagnosticReport) -> tuple[dict[str, Any], set[str]]:
    """Validate independent content probes and local-business coverage warnings"""

    path = "content_foundation_protocol"
    protocol = _object(protocol, path, report)
    fields = {"schema_version", "content_protocol_id", "run_id", "brand_profile_id", "industry_profile_id", "status", "created_at", "probes"}
    _fields(protocol, fields, fields, path, report)
    _version(protocol, path, report)
    if protocol.get("run_id") != run.get("run_id"):
        report.error(f"{path}.run_id", "must reference diagnostic_run.run_id")
    if protocol.get("brand_profile_id") != brand.get("brand_profile_id"):
        report.error(f"{path}.brand_profile_id", "must reference brand_entity_profile.brand_profile_id")
    if protocol.get("industry_profile_id") != industry.get("industry_profile_id"):
        report.error(f"{path}.industry_profile_id", "must reference industry_profile.industry_profile_id")
    if protocol.get("status") not in {"draft", "frozen"}:
        report.error(f"{path}.status", "expected 'draft' or 'frozen'")
    _datetime(protocol.get("created_at"), f"{path}.created_at", report)
    probes = _array(protocol.get("probes"), f"{path}.probes", report)
    probe_ids = _unique_ids(probes, "probe_id", f"{path}.probes", report)
    active_types: set[str] = set()
    for index, item in enumerate(probes):
        if not isinstance(item, dict):
            continue
        item_path = f"{path}.probes[{index}]"
        item_fields = {"probe_id", "probe_type", "applicability", "target_terms", "decision_factor_ids", "expected_evidence", "rationale"}
        _fields(item, item_fields, item_fields, item_path, report)
        if item.get("applicability") != "not_applicable":
            active_types.add(item.get("probe_type"))
        _references(item.get("decision_factor_ids"), factor_ids, f"{item_path}.decision_factor_ids", report)
        terms = _array(item.get("target_terms"), f"{item_path}.target_terms", report)
        if not terms:
            report.error(f"{item_path}.target_terms", "probe requires at least one target term")
        _string(item.get("rationale"), f"{item_path}.rationale", report)
    characteristics = set(industry.get("market_characteristics", []))
    if "location_sensitive" in characteristics:
        for required_type in {"local_listing", "business_identity"}:
            if required_type not in active_types:
                report.warning(f"{path}.probes", f"location-sensitive diagnostics should include an active {required_type} probe")
    if "authorized_reseller" in characteristics and "authorized_relationship" not in active_types:
        report.warning(f"{path}.probes", "authorized-reseller diagnostics should include an active authorized_relationship probe")
    return protocol, probe_ids


def _validate_plan(plan: Any, run: dict[str, Any], research: dict[str, Any], content: dict[str, Any], factor_ids: set[str], location_ids: set[str], report: DiagnosticReport) -> dict[str, Any]:
    """Validate query-to-business mappings and anti-dilution invariants"""

    path = "measurement_plan"
    plan = _object(plan, path, report)
    fields = {"schema_version", "measurement_plan_id", "run_id", "status", "query_protocol_id", "content_protocol_id", "critical_query_ids", "query_mappings", "aggregation_policy"}
    _fields(plan, fields, fields, path, report)
    _version(plan, path, report)
    if plan.get("run_id") != run.get("run_id"):
        report.error(f"{path}.run_id", "must reference diagnostic_run.run_id")
    protocol = research.get("query_protocol", {})
    if plan.get("query_protocol_id") != protocol.get("protocol_id"):
        report.error(f"{path}.query_protocol_id", "must reference query_protocol.protocol_id")
    if plan.get("content_protocol_id") != content.get("content_protocol_id"):
        report.error(f"{path}.content_protocol_id", "must reference content_foundation_protocol.content_protocol_id")
    if plan.get("status") not in {"draft", "frozen"}:
        report.error(f"{path}.status", "expected 'draft' or 'frozen'")
    queries = {item.get("query_id"): item for item in protocol.get("queries", []) if isinstance(item, dict)}
    query_ids = set(queries)
    critical = _references(plan.get("critical_query_ids"), query_ids, f"{path}.critical_query_ids", report, minimum=1)
    for query_id in critical:
        if queries.get(query_id, {}).get("commercial_relevance") != "high":
            report.error(f"{path}.critical_query_ids", f"critical query {query_id!r} must have high commercial relevance")
    mappings = _array(plan.get("query_mappings"), f"{path}.query_mappings", report)
    mapped_query_ids: set[str] = set()
    for index, item in enumerate(mappings):
        if not isinstance(item, dict):
            continue
        item_path = f"{path}.query_mappings[{index}]"
        item_fields = {"query_id", "decision_factor_ids", "location_ids", "commercial_relevance"}
        _fields(item, item_fields, item_fields, item_path, report)
        query_id = item.get("query_id")
        if query_id not in query_ids:
            report.error(f"{item_path}.query_id", f"unresolved query reference {query_id!r}")
        elif query_id in mapped_query_ids:
            report.error(f"{item_path}.query_id", f"duplicate query mapping {query_id!r}")
        mapped_query_ids.add(query_id)
        _references(item.get("decision_factor_ids"), factor_ids, f"{item_path}.decision_factor_ids", report, minimum=1)
        _references(item.get("location_ids"), location_ids, f"{item_path}.location_ids", report)
        if query_id in queries and item.get("commercial_relevance") != queries[query_id].get("commercial_relevance"):
            report.error(f"{item_path}.commercial_relevance", "must match QueryProtocol commercial_relevance")
    if plan.get("status") == "frozen" and mapped_query_ids != query_ids:
        report.error(f"{path}.query_mappings", "frozen measurement plan must map every frozen query exactly once")
    policy = _object(plan.get("aggregation_policy"), f"{path}.aggregation_policy", report)
    policy_fields = {"preserve_query_level_results", "preserve_channel_separation", "allow_cross_segment_offset"}
    _fields(policy, policy_fields, policy_fields, f"{path}.aggregation_policy", report)
    if policy.get("preserve_query_level_results") is not True:
        report.error(f"{path}.aggregation_policy.preserve_query_level_results", "must be true")
    if policy.get("preserve_channel_separation") is not True:
        report.error(f"{path}.aggregation_policy.preserve_channel_separation", "must be true")
    if policy.get("allow_cross_segment_offset") is not False:
        report.error(f"{path}.aggregation_policy.allow_cross_segment_offset", "must be false")
    return plan


def validate_diagnostic_package(research: Any, package: Any) -> dict[str, Any]:
    """Validate one compatible v2 research package plus all R1 diagnostic objects"""

    report = DiagnosticReport()
    research_result = validate_research_package(research)
    for error in research_result["errors"]:
        report.error(f"research.{error['path']}", error["message"])
    for warning in research_result["warnings"]:
        report.warning(f"research.{warning['path']}", warning["message"])
    if not isinstance(research, dict):
        return report.as_dict()
    package = _object(package, "diagnostic_package", report)
    _fields(package, PACKAGE_FIELDS, PACKAGE_FIELDS, "diagnostic_package", report)
    _version(package, "diagnostic_package", report)
    sources = research.get("domain_context", {}).get("sources", [])
    source_ids = {item.get("source_id") for item in sources if isinstance(item, dict) and isinstance(item.get("source_id"), str)}

    run = _validate_run(package.get("diagnostic_run"), research, report)
    brand, location_ids = _validate_brand(package.get("brand_entity_profile"), run, research, source_ids, report)
    industry, factor_ids = _validate_industry(package.get("industry_profile"), run, source_ids, report)
    content, _ = _validate_content(package.get("content_foundation_protocol"), run, brand, industry, factor_ids, report)
    plan = _validate_plan(package.get("measurement_plan"), run, research, content, factor_ids, location_ids, report)

    refs = run.get("object_refs", {})
    for field, actual in {
        "brand_profile_id": brand.get("brand_profile_id"),
        "industry_profile_id": industry.get("industry_profile_id"),
        "measurement_plan_id": plan.get("measurement_plan_id"),
        "content_protocol_id": content.get("content_protocol_id"),
    }.items():
        if refs.get(field) != actual:
            report.error(f"diagnostic_run.object_refs.{field}", f"must reference the package {field}")

    if run.get("status") in READY_RUN_STATES:
        readiness = {
            "research.scope.status": research.get("scope", {}).get("status") == "ready",
            "research.domain_context.status": research.get("domain_context", {}).get("status") == "ready",
            "research.query_protocol.status": research.get("query_protocol", {}).get("status") == "frozen",
            "brand_entity_profile.status": brand.get("status") == "ready",
            "industry_profile.status": industry.get("status") == "ready",
            "measurement_plan.status": plan.get("status") == "frozen",
            "content_foundation_protocol.status": content.get("status") == "frozen",
        }
        for path, ready in readiness.items():
            if not ready:
                report.error(path, "must be ready or frozen before diagnostic run leaves planning")
    if run.get("report_mode") == "exploratory" and run.get("status") == "completed":
        report.warning("diagnostic_run.report_mode", "completed exploratory runs remain non-scoring scope studies")
    return report.as_dict()


def _load(path: str) -> Any:
    """Load one UTF-8 JSON object"""

    with Path(path).open(encoding="utf-8") as file:
        return json.load(file)


def main() -> int:
    """Validate one research package and its R1 diagnostic extension package"""

    parser = argparse.ArgumentParser(description="Validate Brand GEO R1 diagnostic contracts")
    parser.add_argument("research_path")
    parser.add_argument("diagnostic_package_path")
    args = parser.parse_args()
    try:
        result = validate_diagnostic_package(_load(args.research_path), _load(args.diagnostic_package_path))
    except (OSError, json.JSONDecodeError) as error:
        print(json.dumps({"valid": False, "errors": [{"path": "$", "message": str(error)}]}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate a diagnostic-only handoff package for a downstream planning role"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.0.0"
ID_PATTERNS = {
    "handoff_id": re.compile(r"^handoff-[a-z0-9][a-z0-9-]*$"),
    "run_id": re.compile(r"^run-[a-z0-9][a-z0-9-]*$"),
    "artifact_id": re.compile(r"^artifact-[a-z0-9][a-z0-9-]*$"),
    "entity_observation_id": re.compile(r"^entity-obs-[a-z0-9][a-z0-9-]*$"),
    "finding_id": re.compile(r"^finding-[a-z0-9][a-z0-9-]*$"),
    "gap_id": re.compile(r"^gap-[a-z0-9][a-z0-9-]*$"),
    "planning_question_id": re.compile(r"^planning-q-[a-z0-9][a-z0-9-]*$"),
}
ARTIFACT_TYPES = {
    "research_package", "diagnostic_package", "raw_request", "raw_response",
    "screenshot", "stability_result", "user_material",
}
MATCH_STATUSES = {
    "exact_canonical", "verified_alias", "verified_related_entity",
    "other_entity_only", "ambiguous", "absent", "unreviewed",
}
EPISTEMIC_STATUSES = {"observed", "inferred", "unknown", "contradicted"}
CONFIDENCES = {"high", "medium", "low", "unknown"}
CHANNELS = {"official_app_browser", "official_api", "public_web", "user_provided"}


class HandoffReport:
    """Collect blocking handoff contract errors and visible limitations"""

    def __init__(self) -> None:
        self.errors: list[dict[str, str]] = []
        self.warnings: list[dict[str, str]] = []

    def error(self, path: str, message: str) -> None:
        self.errors.append({"path": path, "message": message})

    def warning(self, path: str, message: str) -> None:
        self.warnings.append({"path": path, "message": message})

    def as_dict(self) -> dict[str, Any]:
        return {
            "valid": not self.errors,
            "assessment": "ready_for_planning" if not self.errors else "invalid",
            "errors": self.errors,
            "warnings": self.warnings,
        }


def _object(value: Any, path: str, report: HandoffReport) -> dict[str, Any]:
    if not isinstance(value, dict):
        report.error(path, f"expected object, got {type(value).__name__}")
        return {}
    return value


def _array(value: Any, path: str, report: HandoffReport) -> list[Any]:
    if not isinstance(value, list):
        report.error(path, f"expected array, got {type(value).__name__}")
        return []
    return value


def _fields(obj: dict[str, Any], expected: set[str], path: str, report: HandoffReport) -> None:
    for field in sorted(expected - set(obj)):
        report.error(f"{path}.{field}", "required field is missing")
    for field in sorted(set(obj) - expected):
        report.error(f"{path}.{field}", "field is not allowed by the diagnostic handoff contract")


def _string(value: Any, path: str, report: HandoffReport) -> bool:
    valid = isinstance(value, str) and bool(value.strip())
    if not valid:
        report.error(path, "expected non-empty string")
    return valid


def _id(value: Any, kind: str, path: str, report: HandoffReport) -> bool:
    valid = isinstance(value, str) and bool(ID_PATTERNS[kind].fullmatch(value))
    if not valid:
        report.error(path, f"invalid {kind}")
    return valid


def _unique_strings(value: Any, path: str, report: HandoffReport, *, minimum: int = 0) -> list[str]:
    items = _array(value, path, report)
    if len(items) < minimum:
        report.error(path, f"expected at least {minimum} item(s)")
    result: list[str] = []
    for index, item in enumerate(items):
        if _string(item, f"{path}[{index}]", report):
            if item in result:
                report.error(f"{path}[{index}]", f"duplicate value {item!r}")
            result.append(item)
    return result


def _refs(value: Any, allowed: set[str], path: str, report: HandoffReport, *, minimum: int = 0) -> list[str]:
    refs = _unique_strings(value, path, report, minimum=minimum)
    for index, ref in enumerate(refs):
        if ref not in allowed:
            report.error(f"{path}[{index}]", f"unresolved reference {ref!r}")
    return refs


def _safe_artifact_path(value: Any, path: str, project_root: Path | None, report: HandoffReport) -> None:
    if not _string(value, path, report):
        return
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts:
        report.error(path, "expected a safe project-relative path")
    elif project_root is not None and not (project_root / candidate).is_file():
        report.error(path, f"artifact does not exist: {value}")


def validate_handoff_package(handoff: Any, *, project_root: Path | None = None) -> dict[str, Any]:
    """Validate evidence lineage, epistemic separation, and diagnostic role boundaries"""

    report = HandoffReport()
    handoff = _object(handoff, "handoff", report)
    fields = {
        "schema_version", "handoff_id", "run_id", "report_mode", "generated_at",
        "brand", "scope", "artifact_refs", "entity_observations", "findings",
        "evidence_gaps", "planning_questions", "limitations",
    }
    _fields(handoff, fields, "handoff", report)
    if handoff.get("schema_version") != SCHEMA_VERSION:
        report.error("handoff.schema_version", f"expected {SCHEMA_VERSION!r}")
    _id(handoff.get("handoff_id"), "handoff_id", "handoff.handoff_id", report)
    _id(handoff.get("run_id"), "run_id", "handoff.run_id", report)
    if handoff.get("report_mode") != "diagnostic":
        report.error("handoff.report_mode", "planning handoff must use diagnostic mode")
    try:
        generated_at = datetime.fromisoformat(handoff.get("generated_at"))
        if generated_at.tzinfo is None:
            raise ValueError("timezone missing")
    except (TypeError, ValueError):
        report.error("handoff.generated_at", "expected ISO date-time with timezone")
    _string(handoff.get("brand"), "handoff.brand", report)

    scope = _object(handoff.get("scope"), "handoff.scope", report)
    _fields(scope, {"market", "critical_query_ids", "channels"}, "handoff.scope", report)
    _string(scope.get("market"), "handoff.scope.market", report)
    _unique_strings(scope.get("critical_query_ids"), "handoff.scope.critical_query_ids", report, minimum=1)
    channels = _unique_strings(scope.get("channels"), "handoff.scope.channels", report, minimum=1)
    for index, channel in enumerate(channels):
        if channel not in CHANNELS:
            report.error(f"handoff.scope.channels[{index}]", f"unsupported channel {channel!r}")

    artifacts = _array(handoff.get("artifact_refs"), "handoff.artifact_refs", report)
    artifact_ids: set[str] = set()
    for index, item in enumerate(artifacts):
        path = f"handoff.artifact_refs[{index}]"
        item = _object(item, path, report)
        _fields(item, {"artifact_id", "artifact_type", "path"}, path, report)
        artifact_id = item.get("artifact_id")
        if _id(artifact_id, "artifact_id", f"{path}.artifact_id", report):
            if artifact_id in artifact_ids:
                report.error(f"{path}.artifact_id", f"duplicate artifact id {artifact_id!r}")
            artifact_ids.add(artifact_id)
        if item.get("artifact_type") not in ARTIFACT_TYPES:
            report.error(f"{path}.artifact_type", "unsupported artifact type")
        _safe_artifact_path(item.get("path"), f"{path}.path", project_root, report)
    if not artifacts:
        report.error("handoff.artifact_refs", "at least one source artifact is required")

    entity_observations = _array(handoff.get("entity_observations"), "handoff.entity_observations", report)
    entity_ids: set[str] = set()
    for index, item in enumerate(entity_observations):
        path = f"handoff.entity_observations[{index}]"
        item = _object(item, path, report)
        fields = {"entity_observation_id", "query_id", "artifact_ref_ids", "match_status", "matched_terms", "rationale"}
        _fields(item, fields, path, report)
        value = item.get("entity_observation_id")
        if _id(value, "entity_observation_id", f"{path}.entity_observation_id", report):
            if value in entity_ids:
                report.error(f"{path}.entity_observation_id", f"duplicate entity observation id {value!r}")
            entity_ids.add(value)
        _string(item.get("query_id"), f"{path}.query_id", report)
        _refs(item.get("artifact_ref_ids"), artifact_ids, f"{path}.artifact_ref_ids", report, minimum=1)
        match_status = item.get("match_status")
        if match_status not in MATCH_STATUSES:
            report.error(f"{path}.match_status", "unsupported entity match status")
        terms = _unique_strings(item.get("matched_terms"), f"{path}.matched_terms", report)
        if match_status in {"exact_canonical", "verified_alias", "verified_related_entity", "other_entity_only", "ambiguous"} and not terms:
            report.error(f"{path}.matched_terms", f"{match_status} requires at least one matched term")
        if match_status in {"absent", "unreviewed"} and terms:
            report.error(f"{path}.matched_terms", f"{match_status} cannot assert matched terms")
        _string(item.get("rationale"), f"{path}.rationale", report)

    findings = _array(handoff.get("findings"), "handoff.findings", report)
    finding_ids: set[str] = set()
    for index, item in enumerate(findings):
        path = f"handoff.findings[{index}]"
        item = _object(item, path, report)
        fields = {"finding_id", "statement", "epistemic_status", "confidence", "artifact_ref_ids", "counterevidence_ref_ids", "business_impact"}
        _fields(item, fields, path, report)
        finding_id = item.get("finding_id")
        if _id(finding_id, "finding_id", f"{path}.finding_id", report):
            if finding_id in finding_ids:
                report.error(f"{path}.finding_id", f"duplicate finding id {finding_id!r}")
            finding_ids.add(finding_id)
        _string(item.get("statement"), f"{path}.statement", report)
        status = item.get("epistemic_status")
        if status not in EPISTEMIC_STATUSES:
            report.error(f"{path}.epistemic_status", "unsupported epistemic status")
        confidence = item.get("confidence")
        if confidence not in CONFIDENCES:
            report.error(f"{path}.confidence", "unsupported confidence")
        evidence_refs = _refs(item.get("artifact_ref_ids"), artifact_ids, f"{path}.artifact_ref_ids", report)
        _refs(item.get("counterevidence_ref_ids"), artifact_ids, f"{path}.counterevidence_ref_ids", report)
        if status in {"observed", "inferred", "contradicted"} and not evidence_refs:
            report.error(f"{path}.artifact_ref_ids", f"{status} findings require evidence lineage")
        if status == "unknown" and confidence != "unknown":
            report.error(f"{path}.confidence", "unknown findings require unknown confidence")
        _string(item.get("business_impact"), f"{path}.business_impact", report)
    if not findings:
        report.error("handoff.findings", "at least one diagnostic finding is required")

    gaps = _array(handoff.get("evidence_gaps"), "handoff.evidence_gaps", report)
    gap_ids: set[str] = set()
    for index, item in enumerate(gaps):
        path = f"handoff.evidence_gaps[{index}]"
        item = _object(item, path, report)
        _fields(item, {"gap_id", "statement", "impact", "required_evidence"}, path, report)
        gap_id = item.get("gap_id")
        if _id(gap_id, "gap_id", f"{path}.gap_id", report):
            if gap_id in gap_ids:
                report.error(f"{path}.gap_id", f"duplicate gap id {gap_id!r}")
            gap_ids.add(gap_id)
        _string(item.get("statement"), f"{path}.statement", report)
        _string(item.get("impact"), f"{path}.impact", report)
        _unique_strings(item.get("required_evidence"), f"{path}.required_evidence", report, minimum=1)

    questions = _array(handoff.get("planning_questions"), "handoff.planning_questions", report)
    question_ids: set[str] = set()
    for index, item in enumerate(questions):
        path = f"handoff.planning_questions[{index}]"
        item = _object(item, path, report)
        _fields(item, {"planning_question_id", "question", "related_finding_ids", "validation_metric"}, path, report)
        value = item.get("planning_question_id")
        if _id(value, "planning_question_id", f"{path}.planning_question_id", report):
            if value in question_ids:
                report.error(f"{path}.planning_question_id", f"duplicate planning question id {value!r}")
            question_ids.add(value)
        _string(item.get("question"), f"{path}.question", report)
        _refs(item.get("related_finding_ids"), finding_ids, f"{path}.related_finding_ids", report, minimum=1)
        _string(item.get("validation_metric"), f"{path}.validation_metric", report)
    if not questions:
        report.error("handoff.planning_questions", "at least one planning question is required")

    limitations = _unique_strings(handoff.get("limitations"), "handoff.limitations", report)
    if "official_app_browser" in channels and not any(item.get("artifact_type") == "stability_result" for item in artifacts if isinstance(item, dict)):
        report.warning("handoff.artifact_refs", "consumer App evidence has no repeated-run stability artifact")
    if not limitations:
        report.warning("handoff.limitations", "a real diagnostic should state its known limitations")
    return report.as_dict()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("handoff", type=Path)
    parser.add_argument("--project-root", type=Path)
    args = parser.parse_args()
    try:
        handoff = json.loads(args.handoff.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(json.dumps({"valid": False, "assessment": "invalid", "errors": [{"path": str(args.handoff), "message": str(error)}], "warnings": []}, ensure_ascii=False, indent=2))
        return 2
    result = validate_handoff_package(handoff, project_root=args.project_root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

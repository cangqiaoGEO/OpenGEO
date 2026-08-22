#!/usr/bin/env python3
"""Validate a controlled R2 pilot plan and its completion evidence"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.0.0"
ALL_COVERAGE = {
    "high_consideration_b2b",
    "consumer_brand",
    "regional_service",
    "local_sme_or_micro",
    "entity_complexity",
}
PILOT_ID = re.compile(r"^pilot-[a-z0-9][a-z0-9-]*$")
CASE_ID = re.compile(r"^case-[a-z0-9][a-z0-9-]*$")
ACTIVE_STATES = {"frozen", "collecting", "completed"}


class PilotReport:
    """Collect blocking errors and visible R2 limitations"""

    def __init__(self) -> None:
        self.errors: list[dict[str, str]] = []
        self.warnings: list[dict[str, str]] = []

    def error(self, path: str, message: str) -> None:
        """Record one blocking contract violation"""

        self.errors.append({"path": path, "message": message})

    def warning(self, path: str, message: str) -> None:
        """Record one non-blocking pilot limitation"""

        self.warnings.append({"path": path, "message": message})

    def as_dict(self, status: Any) -> dict[str, Any]:
        """Return the stable command-line representation"""

        assessment = "invalid" if self.errors else ("completed" if status == "completed" else "ready")
        return {
            "valid": not self.errors,
            "assessment": assessment,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def _object(value: Any, path: str, report: PilotReport) -> dict[str, Any]:
    """Return an object or report its type error"""

    if not isinstance(value, dict):
        report.error(path, f"expected object, got {type(value).__name__}")
        return {}
    return value


def _array(value: Any, path: str, report: PilotReport) -> list[Any]:
    """Return an array or report its type error"""

    if not isinstance(value, list):
        report.error(path, f"expected array, got {type(value).__name__}")
        return []
    return value


def _fields(obj: dict[str, Any], required: set[str], path: str, report: PilotReport) -> None:
    """Apply required and additional-property checks"""

    for field in sorted(required - set(obj)):
        report.error(f"{path}.{field}", "required field is missing")
    for field in sorted(set(obj) - required):
        report.error(f"{path}.{field}", "field is not allowed by the pilot contract")


def _string(value: Any, path: str, report: PilotReport) -> bool:
    """Validate one non-empty string"""

    valid = isinstance(value, str) and bool(value.strip())
    if not valid:
        report.error(path, "expected non-empty string")
    return valid


def _datetime(value: Any, path: str, report: PilotReport) -> None:
    """Validate an ISO timestamp with timezone"""

    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            raise ValueError("timezone missing")
    except (TypeError, ValueError):
        report.error(path, "expected ISO date-time with timezone")


def _date(value: Any, path: str, report: PilotReport) -> None:
    """Validate an ISO date"""

    try:
        date.fromisoformat(value)
    except (TypeError, ValueError):
        report.error(path, "expected ISO date YYYY-MM-DD")


def _unique_strings(values: Any, path: str, report: PilotReport) -> list[str]:
    """Validate a unique array of non-empty strings"""

    entries = _array(values, path, report)
    seen: set[str] = set()
    result: list[str] = []
    for index, value in enumerate(entries):
        if not _string(value, f"{path}[{index}]", report):
            continue
        if value in seen:
            report.error(f"{path}[{index}]", f"duplicate value {value!r}")
        seen.add(value)
        result.append(value)
    return result


def _path_exists(value: Any, path: str, root: Path, report: PilotReport) -> None:
    """Require one project-relative artifact path to exist"""

    if not _string(value, path, report):
        return
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts:
        report.error(path, "expected a safe project-relative path")
    elif not (root / candidate).is_file():
        report.error(path, f"artifact does not exist: {value}")


def validate_pilot_study(pilot: Any, *, project_root: Path | None = None) -> dict[str, Any]:
    """Validate one R2 pilot from frozen design through completion"""

    report = PilotReport()
    pilot = _object(pilot, "pilot", report)
    fields = {
        "schema_version", "pilot_id", "status", "purpose", "created_at", "as_of",
        "required_coverage", "observation_policy", "review_policy", "handoff_policy", "cases",
    }
    _fields(pilot, fields, "pilot", report)
    if pilot.get("schema_version") != SCHEMA_VERSION:
        report.error("pilot.schema_version", f"expected {SCHEMA_VERSION!r}")
    if not isinstance(pilot.get("pilot_id"), str) or not PILOT_ID.fullmatch(pilot["pilot_id"]):
        report.error("pilot.pilot_id", "expected id matching '^pilot-[a-z0-9][a-z0-9-]*$'")
    status = pilot.get("status")
    if status not in {"draft", "frozen", "collecting", "completed", "blocked"}:
        report.error("pilot.status", "unsupported pilot status")
    if pilot.get("purpose") != "workflow_validation":
        report.error("pilot.purpose", "R2 pilots validate workflow, not scoring calibration")
    _datetime(pilot.get("created_at"), "pilot.created_at", report)
    _date(pilot.get("as_of"), "pilot.as_of", report)

    required_coverage = set(_unique_strings(pilot.get("required_coverage"), "pilot.required_coverage", report))
    if status in ACTIVE_STATES and required_coverage != ALL_COVERAGE:
        report.error("pilot.required_coverage", "active R2 pilot must freeze all five roadmap coverage classes")

    observation = _object(pilot.get("observation_policy"), "pilot.observation_policy", report)
    observation_fields = {
        "primary_channel", "consumer_product", "target_repetitions", "time_window_hours",
        "market_context", "location_state", "search_required", "preserve_query_level_results",
        "preserve_channel_separation",
    }
    _fields(observation, observation_fields, "pilot.observation_policy", report)
    if observation.get("primary_channel") != "official_app_browser":
        report.error("pilot.observation_policy.primary_channel", "consumer App browser must remain the R2 primary channel")
    if observation.get("consumer_product") not in {"doubao", "qwen", "deepseek", "yuanbao"}:
        report.error("pilot.observation_policy.consumer_product", "unsupported consumer product")
    repetitions = observation.get("target_repetitions")
    if not isinstance(repetitions, int) or repetitions < 2:
        report.error("pilot.observation_policy.target_repetitions", "expected integer >= 2")
        repetitions = 2
    window = observation.get("time_window_hours")
    if not isinstance(window, int) or window < 1:
        report.error("pilot.observation_policy.time_window_hours", "expected integer >= 1")
    _string(observation.get("market_context"), "pilot.observation_policy.market_context", report)
    if observation.get("location_state") not in {"explicit_in_query", "account_or_device_context", "unknown"}:
        report.error("pilot.observation_policy.location_state", "unsupported location state")
    for field in ("search_required", "preserve_query_level_results", "preserve_channel_separation"):
        if observation.get(field) is not True:
            report.error(f"pilot.observation_policy.{field}", "must be true")

    review = _object(pilot.get("review_policy"), "pilot.review_policy", report)
    review_fields = {"entity_resolution_owner", "industry_factor_owner", "annotation_owner", "review_method"}
    _fields(review, review_fields, "pilot.review_policy", report)
    for field in ("entity_resolution_owner", "industry_factor_owner", "annotation_owner"):
        _string(review.get(field), f"pilot.review_policy.{field}", report)
    if review.get("review_method") not in {"single_operator_review", "independent_second_review"}:
        report.error("pilot.review_policy.review_method", "unsupported review method")
    if review.get("review_method") == "single_operator_review":
        report.warning("pilot.review_policy.review_method", "R2 can test executability, but agreement remains untested until R3")

    handoff = _object(pilot.get("handoff_policy"), "pilot.handoff_policy", report)
    handoff_fields = {"delivery_mode", "artifact_root", "workbuddy_binding_status", "planning_handoff_required"}
    _fields(handoff, handoff_fields, "pilot.handoff_policy", report)
    if handoff.get("delivery_mode") not in {"controlled_files", "workbuddy_tool", "mixed"}:
        report.error("pilot.handoff_policy.delivery_mode", "unsupported delivery mode")
    _string(handoff.get("artifact_root"), "pilot.handoff_policy.artifact_root", report)
    if handoff.get("workbuddy_binding_status") not in {"unavailable", "planned", "verified"}:
        report.error("pilot.handoff_policy.workbuddy_binding_status", "unsupported WorkBuddy binding status")
    if handoff.get("planning_handoff_required") is not True:
        report.error("pilot.handoff_policy.planning_handoff_required", "must be true")
    if handoff.get("workbuddy_binding_status") != "verified":
        report.warning("pilot.handoff_policy.workbuddy_binding_status", "pilot does not prove WorkBuddy runtime integration")

    cases = _array(pilot.get("cases"), "pilot.cases", report)
    if status in ACTIVE_STATES and not 3 <= len(cases) <= 5:
        report.error("pilot.cases", "active R2 pilot requires 3-5 cases")
    seen_case_ids: set[str] = set()
    covered: set[str] = set()
    case_fields = {
        "case_id", "status", "coverage", "data_access", "research_package_path",
        "diagnostic_package_path", "critical_query_ids", "app_request_paths",
        "app_response_paths", "review_status", "handoff_path", "limitations",
    }
    for index, item in enumerate(cases):
        path = f"pilot.cases[{index}]"
        case = _object(item, path, report)
        _fields(case, case_fields, path, report)
        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not CASE_ID.fullmatch(case_id):
            report.error(f"{path}.case_id", "expected id matching '^case-[a-z0-9][a-z0-9-]*$'")
        elif case_id in seen_case_ids:
            report.error(f"{path}.case_id", f"duplicate case id {case_id!r}")
        seen_case_ids.add(case_id)
        if case.get("status") not in {"planned", "ready", "collecting", "reviewed", "completed", "blocked"}:
            report.error(f"{path}.status", "unsupported case status")
        coverage = set(_unique_strings(case.get("coverage"), f"{path}.coverage", report))
        covered.update(coverage)
        access = set(_unique_strings(case.get("data_access"), f"{path}.data_access", report))
        if "official_app_browser" not in access:
            report.error(f"{path}.data_access", "each R2 case requires consumer App evidence access")
        if coverage & {"regional_service", "local_sme_or_micro"} and observation.get("location_state") != "explicit_in_query":
            report.error("pilot.observation_policy.location_state", "regional and local cases require geography explicit in the frozen query")
        critical_ids = _unique_strings(case.get("critical_query_ids"), f"{path}.critical_query_ids", report)
        if not critical_ids:
            report.error(f"{path}.critical_query_ids", "each case requires at least one critical query")
        request_paths = _unique_strings(case.get("app_request_paths"), f"{path}.app_request_paths", report)
        response_paths = _unique_strings(case.get("app_response_paths"), f"{path}.app_response_paths", report)
        _array(case.get("limitations"), f"{path}.limitations", report)
        if case.get("status") == "completed" or status == "completed":
            if len(request_paths) != repetitions or len(response_paths) != repetitions:
                report.error(path, f"completed case requires exactly {repetitions} App requests and responses")
            if case.get("review_status") != "completed":
                report.error(f"{path}.review_status", "completed case requires completed review")
            if case.get("handoff_path") is None:
                report.error(f"{path}.handoff_path", "completed case requires a planning handoff artifact")
            if project_root is not None:
                for field in ("research_package_path", "diagnostic_package_path", "handoff_path"):
                    _path_exists(case.get(field), f"{path}.{field}", project_root, report)
                for field, paths in (("app_request_paths", request_paths), ("app_response_paths", response_paths)):
                    for item_index, value in enumerate(paths):
                        _path_exists(value, f"{path}.{field}[{item_index}]", project_root, report)
    if status in ACTIVE_STATES and not required_coverage.issubset(covered):
        missing = sorted(required_coverage - covered)
        report.error("pilot.cases", f"case portfolio does not cover {missing}")
    if status == "completed" and any(case.get("status") != "completed" for case in cases if isinstance(case, dict)):
        report.error("pilot.status", "completed pilot requires every case to be completed")
    return report.as_dict(status)


def main() -> int:
    """Run the R2 pilot validator as a CLI"""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pilot", type=Path)
    parser.add_argument("--project-root", type=Path)
    args = parser.parse_args()
    try:
        with args.pilot.open(encoding="utf-8") as file:
            pilot = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "assessment": "invalid", "errors": [{"path": str(args.pilot), "message": str(exc)}], "warnings": []}, ensure_ascii=False, indent=2))
        return 2
    result = validate_pilot_study(pilot, project_root=args.project_root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

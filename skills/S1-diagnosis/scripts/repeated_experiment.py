#!/usr/bin/env python3
"""Validate repeated browser observations and calculate stability metrics"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from statistics import fmean, pstdev
from typing import Any

from collection_contracts import validate_raw_response

EXPERIMENT_SCHEMA_VERSION = "1.0.0"
PRODUCTS = {"doubao", "qwen", "deepseek", "yuanbao"}
EXPERIMENT_ID_PATTERN = re.compile(r"^experiment-[a-z0-9][a-z0-9-]*$")
RUN_ID_PATTERN = re.compile(r"^run-[a-z0-9][a-z0-9-]*$")


def _error(errors: list[dict[str, str]], path: str, message: str) -> None:
    """Append one stable validation error"""

    errors.append({"path": path, "message": message})


def _load_json(root: Path, relative_path: Any, path: str, errors: list[dict[str, str]]) -> dict[str, Any]:
    """Load a project-relative JSON object without allowing path escape"""

    if not isinstance(relative_path, str) or not relative_path:
        _error(errors, path, "expected non-empty project-relative path")
        return {}
    target = (root / relative_path).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError:
        _error(errors, path, "path must stay inside project root")
        return {}
    try:
        value = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        _error(errors, path, str(error))
        return {}
    if not isinstance(value, dict):
        _error(errors, path, "expected JSON object")
        return {}
    return value


def _unique_strings(value: Any, path: str, errors: list[dict[str, str]]) -> list[str]:
    """Validate a unique list of non-empty annotation strings"""

    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        _error(errors, path, "expected array of non-empty strings")
        return []
    if len(value) != len(set(value)):
        _error(errors, path, "items must be unique")
    return value


def validate_experiment(experiment: Any, project_root: Path) -> dict[str, Any]:
    """Validate repeated runs, referenced raw artifacts, and semantic annotations"""

    errors: list[dict[str, str]] = []
    if not isinstance(experiment, dict):
        return {"valid": False, "errors": [{"path": "$", "message": "expected object"}], "resolved_runs": []}
    expected_fields = {"schema_version", "experiment_id", "protocol_id", "query_id", "query_text", "purpose", "target_repetitions", "platforms"}
    for field in sorted(expected_fields - set(experiment)):
        _error(errors, f"experiment.{field}", "required field is missing")
    for field in sorted(set(experiment) - expected_fields):
        _error(errors, f"experiment.{field}", "field is not allowed")
    if experiment.get("schema_version") != EXPERIMENT_SCHEMA_VERSION:
        _error(errors, "experiment.schema_version", f"expected {EXPERIMENT_SCHEMA_VERSION!r}")
    if not isinstance(experiment.get("experiment_id"), str) or not EXPERIMENT_ID_PATTERN.fullmatch(experiment.get("experiment_id", "")):
        _error(errors, "experiment.experiment_id", "expected experiment id using lowercase letters, numbers, and hyphens")
    if experiment.get("purpose") != "collection_stability":
        _error(errors, "experiment.purpose", "expected 'collection_stability'")
    target = experiment.get("target_repetitions")
    if isinstance(target, bool) or not isinstance(target, int) or target < 2:
        _error(errors, "experiment.target_repetitions", "expected integer >= 2")
        target = 0
    query_text = experiment.get("query_text")
    if not isinstance(query_text, str) or not query_text.strip():
        _error(errors, "experiment.query_text", "expected non-empty string")
    for field in ("protocol_id", "query_id"):
        if not isinstance(experiment.get(field), str) or not experiment.get(field, "").strip():
            _error(errors, f"experiment.{field}", "expected non-empty string")

    platforms = experiment.get("platforms")
    if not isinstance(platforms, list) or not platforms:
        _error(errors, "experiment.platforms", "expected non-empty array")
        platforms = []
    seen_products: set[str] = set()
    resolved_runs: list[dict[str, Any]] = []
    for platform_index, platform in enumerate(platforms):
        platform_path = f"experiment.platforms[{platform_index}]"
        if not isinstance(platform, dict):
            _error(errors, platform_path, "expected object")
            continue
        expected_platform_fields = {"consumer_product", "channel", "mode_policy", "runs"}
        if set(platform) != expected_platform_fields:
            _error(errors, platform_path, "expected exactly consumer_product, channel, mode_policy, and runs")
        product = platform.get("consumer_product")
        if product not in PRODUCTS:
            _error(errors, f"{platform_path}.consumer_product", "unsupported product")
        elif product in seen_products:
            _error(errors, f"{platform_path}.consumer_product", "product must be unique")
        else:
            seen_products.add(product)
        channel = platform.get("channel")
        if channel not in {"official_app_browser", "official_api"}:
            _error(errors, f"{platform_path}.channel", "unsupported repeated experiment channel")
        policy = platform.get("mode_policy")
        policy_fields = {"mode_label", "thinking_mode", "search_mode", "search_required"}
        if not isinstance(policy, dict) or set(policy) != policy_fields:
            _error(errors, f"{platform_path}.mode_policy", "mode policy has an invalid shape")
            policy = {}
        if not isinstance(policy.get("mode_label"), str) or not policy.get("mode_label", "").strip():
            _error(errors, f"{platform_path}.mode_policy.mode_label", "expected non-empty string")
        if policy.get("thinking_mode") not in {"disabled", "platform_default"}:
            _error(errors, f"{platform_path}.mode_policy.thinking_mode", "unsupported thinking mode")
        if policy.get("search_mode") not in {"native", "none"} or not isinstance(policy.get("search_required"), bool):
            _error(errors, f"{platform_path}.mode_policy", "supported search mode and boolean search_required are required")
        if policy.get("search_mode") == "none" and policy.get("search_required") is not False:
            _error(errors, f"{platform_path}.mode_policy.search_required", "search_required must be false when search_mode is none")

        runs = platform.get("runs")
        if not isinstance(runs, list):
            _error(errors, f"{platform_path}.runs", "expected array")
            continue
        if len(runs) != target:
            _error(errors, f"{platform_path}.runs", f"expected exactly {target} runs")
        indexes: list[int] = []
        for run_index, run in enumerate(runs):
            run_path = f"{platform_path}.runs[{run_index}]"
            if not isinstance(run, dict) or set(run) != {"run_id", "repetition_index", "request_path", "response_path", "annotation"}:
                _error(errors, run_path, "run has an invalid shape")
                continue
            if not isinstance(run.get("run_id"), str) or not RUN_ID_PATTERN.fullmatch(run.get("run_id", "")):
                _error(errors, f"{run_path}.run_id", "expected run id using lowercase letters, numbers, and hyphens")
            repetition_index = run.get("repetition_index")
            if isinstance(repetition_index, bool) or not isinstance(repetition_index, int):
                _error(errors, f"{run_path}.repetition_index", "expected integer")
            else:
                indexes.append(repetition_index)
            request = _load_json(project_root, run.get("request_path"), f"{run_path}.request_path", errors)
            response = _load_json(project_root, run.get("response_path"), f"{run_path}.response_path", errors)
            if request and response:
                pair_result = validate_raw_response(request, response)
                for pair_error in pair_result["errors"]:
                    _error(errors, f"{run_path}.{pair_error['path']}", pair_error["message"])
                if response.get("status") != "completed":
                    _error(errors, f"{run_path}.response.status", "repeated stability statistics require a completed response")
                if channel == "official_app_browser":
                    screenshot_value = response.get("screenshot_path")
                    screenshot = Path(screenshot_value) if isinstance(screenshot_value, str) else None
                    if screenshot is not None and not screenshot.is_absolute():
                        screenshot = project_root / screenshot
                    if screenshot is None or not screenshot.is_file() or screenshot.stat().st_size == 0:
                        _error(errors, f"{run_path}.response.screenshot_path", "referenced screenshot must exist and be non-empty")
                expected_values = {
                    "protocol_id": experiment.get("protocol_id"),
                    "query_id": experiment.get("query_id"),
                    "query": query_text,
                    "consumer_product": product,
                    "channel": channel,
                }
                for field, expected in expected_values.items():
                    if request.get(field) != expected:
                        _error(errors, f"{run_path}.request.{field}", f"expected {expected!r}")
                configuration = request.get("configuration", {})
                for field in ("thinking_mode", "search_mode", "search_required"):
                    if configuration.get(field) != policy.get(field):
                        _error(errors, f"{run_path}.request.configuration.{field}", f"must match mode policy {policy.get(field)!r}")
            annotation = run.get("annotation")
            annotation_fields = {"entities_mentioned", "entities_recommended", "first_entity", "recommendation_present", "selection_criteria", "caveats"}
            if not isinstance(annotation, dict) or set(annotation) != annotation_fields:
                _error(errors, f"{run_path}.annotation", "annotation has an invalid shape")
                annotation = {}
            mentioned = _unique_strings(annotation.get("entities_mentioned"), f"{run_path}.annotation.entities_mentioned", errors)
            recommended = _unique_strings(annotation.get("entities_recommended"), f"{run_path}.annotation.entities_recommended", errors)
            _unique_strings(annotation.get("selection_criteria"), f"{run_path}.annotation.selection_criteria", errors)
            _unique_strings(annotation.get("caveats"), f"{run_path}.annotation.caveats", errors)
            first_entity = annotation.get("first_entity")
            if first_entity is not None and (not isinstance(first_entity, str) or not first_entity.strip()):
                _error(errors, f"{run_path}.annotation.first_entity", "expected non-empty string or null")
            if first_entity is not None and first_entity not in mentioned:
                _error(errors, f"{run_path}.annotation.first_entity", "must be null or one of entities_mentioned")
            if any(item not in mentioned for item in recommended):
                _error(errors, f"{run_path}.annotation.entities_recommended", "recommended entities must also be mentioned")
            if not isinstance(annotation.get("recommendation_present"), bool):
                _error(errors, f"{run_path}.annotation.recommendation_present", "expected boolean")
            elif annotation.get("recommendation_present") != bool(recommended):
                _error(errors, f"{run_path}.annotation.recommendation_present", "must match whether entities_recommended is non-empty")
            resolved_runs.append({"product": product, "run": run, "request": request, "response": response, "annotation": annotation})
        if sorted(indexes) != list(range(1, target + 1)):
            _error(errors, f"{platform_path}.runs", f"repetition indexes must be 1..{target}")
    return {"valid": not errors, "errors": errors, "resolved_runs": resolved_runs}


def _mean_pairwise_jaccard(values: list[set[str]]) -> float | None:
    """Return mean pairwise Jaccard similarity, treating two empty sets as equal"""

    scores: list[float] = []
    for left_index, left in enumerate(values):
        for right in values[left_index + 1:]:
            scores.append(1.0 if not left and not right else len(left & right) / len(left | right))
    return round(fmean(scores), 4) if scores else None


def calculate_stability(experiment: dict[str, Any], project_root: Path) -> dict[str, Any]:
    """Calculate transparent, non-scoring repeatability statistics"""

    validation = validate_experiment(experiment, project_root)
    if not validation["valid"]:
        return {"valid": False, "errors": validation["errors"]}
    grouped: dict[str, list[dict[str, Any]]] = {platform["consumer_product"]: [] for platform in experiment["platforms"]}
    for item in validation["resolved_runs"]:
        grouped[item["product"]].append(item)
    results: list[dict[str, Any]] = []
    for product, items in grouped.items():
        lengths = [len(item["response"]["raw_text"]) for item in items]
        hashes = [hashlib.sha256(item["response"]["raw_text"].encode("utf-8")).hexdigest() for item in items]
        citations = [{citation["url"] for citation in item["response"]["citations"]} for item in items]
        mentioned = [set(item["annotation"]["entities_mentioned"]) for item in items]
        recommended = [set(item["annotation"]["entities_recommended"]) for item in items]
        first_entities = [item["annotation"]["first_entity"] for item in items]
        first_counts = Counter(first_entities)
        mean_length = fmean(lengths)
        results.append({
            "consumer_product": product,
            "completed_runs": len(items),
            "search_execution_rate": (
                round(sum(item["response"]["search_executed"] is True for item in items) / len(items), 4)
                if any(item["response"]["search_requested"] for item in items)
                else None
            ),
            "unique_answer_rate": round(len(set(hashes)) / len(hashes), 4),
            "answer_chars": {
                "min": min(lengths),
                "max": max(lengths),
                "mean": round(mean_length, 2),
                "coefficient_of_variation": round(pstdev(lengths) / mean_length, 4) if mean_length else None,
            },
            "mentioned_entity_jaccard": _mean_pairwise_jaccard(mentioned),
            "recommended_entity_jaccard": _mean_pairwise_jaccard(recommended),
            "first_entity_agreement": round(max(first_counts.values()) / len(first_entities), 4),
            "citation_url_jaccard": _mean_pairwise_jaccard(citations) if any(citations) else None,
        })
    return {
        "valid": True,
        "schema_version": EXPERIMENT_SCHEMA_VERSION,
        "experiment_id": experiment["experiment_id"],
        "purpose": "collection_stability",
        "platforms": results,
        "interpretation": "repeatability metrics only; not a GEO score or factual-accuracy judgment",
    }


def main() -> int:
    """Validate an experiment and optionally emit its stability statistics"""

    parser = argparse.ArgumentParser(description="Validate and summarize repeated browser observations")
    parser.add_argument("experiment_path")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("-o", "--output", type=Path, help="write the result JSON to this path")
    args = parser.parse_args()
    try:
        experiment = json.loads(Path(args.experiment_path).read_text(encoding="utf-8"))
        result = validate_experiment(experiment, Path(args.project_root)) if args.validate_only else calculate_stability(experiment, Path(args.project_root))
        result.pop("resolved_runs", None)
    except (OSError, json.JSONDecodeError) as error:
        result = {"valid": False, "errors": [{"path": "$", "message": str(error)}]}
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Compare repeated official API and consumer browser experiments by dimension"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from statistics import fmean
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from repeated_experiment import validate_experiment  # noqa: E402


def _jaccard(left: set[str], right: set[str]) -> float | None:
    """Return Jaccard similarity or null when neither side has observations"""

    return round(len(left & right) / len(left | right), 4) if left or right else None


def _mode(values: list[str | None]) -> dict[str, Any]:
    """Return the dominant value and its agreement rate"""

    counts = Counter(values)
    value, count = counts.most_common(1)[0]
    return {"value": value, "agreement": round(count / len(values), 4)}


def summarize_experiment(experiment: dict[str, Any], project_root: Path, product: str | None = None) -> dict[str, Any]:
    """Summarize one valid single-platform repeated experiment"""

    validation = validate_experiment(experiment, project_root)
    if not validation["valid"]:
        return {"valid": False, "errors": validation["errors"]}
    platforms = [platform for platform in experiment["platforms"] if product is None or platform["consumer_product"] == product]
    if len(platforms) != 1:
        return {"valid": False, "errors": [{"path": "experiment.platforms", "message": "channel comparison requires exactly one matching platform"}]}
    selected_product = platforms[0]["consumer_product"]
    runs = [item for item in validation["resolved_runs"] if item["product"] == selected_product]
    mentioned_sets = [set(item["annotation"]["entities_mentioned"]) for item in runs]
    recommended_sets = [set(item["annotation"]["entities_recommended"]) for item in runs]
    mentioned_union = set().union(*mentioned_sets)
    recommended_union = set().union(*recommended_sets)
    mentioned_core = set.intersection(*mentioned_sets)
    recommended_core = set.intersection(*recommended_sets)
    responses = [item["response"] for item in runs]
    search_requested = [response["search_requested"] for response in responses]
    platform = platforms[0]
    return {
        "valid": True,
        "experiment_id": experiment["experiment_id"],
        "protocol_id": experiment["protocol_id"],
        "query_id": experiment["query_id"],
        "query_text": experiment["query_text"],
        "consumer_product": platform["consumer_product"],
        "channel": platform["channel"],
        "mode_policy": platform["mode_policy"],
        "runs": len(runs),
        "answer_chars_mean": round(fmean(len(response["raw_text"]) for response in responses), 2),
        "citation_count_mean": round(fmean(len(response["citations"]) for response in responses), 2),
        "search_requested_rate": round(sum(search_requested) / len(responses), 4),
        "search_execution_rate": (
            round(sum(response["search_executed"] is True for response in responses) / len(responses), 4)
            if any(search_requested)
            else None
        ),
        "recommendation_present_rate": round(sum(item["annotation"]["recommendation_present"] for item in runs) / len(runs), 4),
        "mentioned_entity_union": sorted(mentioned_union),
        "mentioned_entity_core": sorted(mentioned_core),
        "recommended_entity_union": sorted(recommended_union),
        "recommended_entity_core": sorted(recommended_core),
        "first_entity_mode": _mode([item["annotation"]["first_entity"] for item in runs]),
    }


def compare_channels(browser: dict[str, Any], api: dict[str, Any], project_root: Path) -> dict[str, Any]:
    """Compare two repeated experiments without claiming model equivalence"""

    api_summary = summarize_experiment(api, project_root)
    browser_summary = (
        summarize_experiment(browser, project_root, api_summary["consumer_product"])
        if api_summary.get("valid")
        else {"valid": False, "errors": []}
    )
    errors = []
    for label, summary in (("browser", browser_summary), ("api", api_summary)):
        for error in summary.get("errors", []):
            errors.append({"path": f"{label}.{error['path']}", "message": error["message"]})
    if errors:
        return {"valid": False, "errors": errors}
    expected_channels = {browser_summary["channel"], api_summary["channel"]}
    if expected_channels != {"official_app_browser", "official_api"}:
        errors.append({"path": "channels", "message": "expected one official_app_browser and one official_api experiment"})
    for field in ("protocol_id", "query_id", "query_text", "consumer_product"):
        if browser_summary[field] != api_summary[field]:
            errors.append({"path": field, "message": "browser and API experiments must match"})
    if errors:
        return {"valid": False, "errors": errors}

    browser_mentioned = set(browser_summary["mentioned_entity_union"])
    api_mentioned = set(api_summary["mentioned_entity_union"])
    browser_mentioned_core = set(browser_summary["mentioned_entity_core"])
    api_mentioned_core = set(api_summary["mentioned_entity_core"])
    browser_recommended = set(browser_summary["recommended_entity_union"])
    api_recommended = set(api_summary["recommended_entity_union"])
    browser_length = browser_summary["answer_chars_mean"]
    api_length = api_summary["answer_chars_mean"]
    return {
        "valid": True,
        "schema_version": "1.0.0",
        "consumer_product": browser_summary["consumer_product"],
        "protocol_id": browser_summary["protocol_id"],
        "query_id": browser_summary["query_id"],
        "browser": browser_summary,
        "api": api_summary,
        "differences": {
            "answer_chars_delta_api_minus_browser": round(api_length - browser_length, 2),
            "answer_length_ratio_api_to_browser": round(api_length / browser_length, 4) if browser_length else None,
            "citation_count_delta_api_minus_browser": round(api_summary["citation_count_mean"] - browser_summary["citation_count_mean"], 2),
            "mentioned_entity_union_jaccard": _jaccard(browser_mentioned, api_mentioned),
            "mentioned_entity_core_jaccard": _jaccard(browser_mentioned_core, api_mentioned_core),
            "recommended_entity_union_jaccard": _jaccard(browser_recommended, api_recommended),
            "first_entity_mode_same": browser_summary["first_entity_mode"]["value"] == api_summary["first_entity_mode"]["value"],
            "search_capability_same": (
                browser_summary["search_requested_rate"] == api_summary["search_requested_rate"]
                and browser_summary["search_execution_rate"] == api_summary["search_execution_rate"]
            ),
        },
        "comparability": {
            "same_query": True,
            "same_consumer_product_label": True,
            "same_channel": False,
            "same_verified_model": False,
            "same_search_capability": False,
            "formal_equivalence": False,
        },
        "interpretation": "dimension-level paired difference only; API and consumer App are not equivalent products",
    }


def main() -> int:
    """Compare browser and API experiment JSON files"""

    parser = argparse.ArgumentParser(description="Compare repeated browser and official API experiments")
    parser.add_argument("browser_experiment_path")
    parser.add_argument("api_experiment_path")
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()
    try:
        browser = json.loads(Path(args.browser_experiment_path).read_text(encoding="utf-8"))
        api = json.loads(Path(args.api_experiment_path).read_text(encoding="utf-8"))
        result = compare_channels(browser, api, Path(args.project_root))
    except (OSError, json.JSONDecodeError) as error:
        result = {"valid": False, "errors": [{"path": "$", "message": str(error)}]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

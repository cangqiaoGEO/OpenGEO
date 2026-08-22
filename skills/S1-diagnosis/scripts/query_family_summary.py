#!/usr/bin/env python3
"""Summarize Brand GEO observations by business query family and wording variant"""

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


SCHEMA_VERSION = "1.0.0"
REQUIRED_FAMILIES = (
    "brand_direct",
    "category_recommendation",
    "solution",
    "brand_comparison",
)
FAMILY_LABELS = {
    "brand_direct": "品牌认知",
    "category_recommendation": "品类推荐",
    "solution": "需求解决",
    "brand_comparison": "品牌比较",
    "customer_problem": "客户问题",
    "alternative": "替代选择",
    "risk": "风险核验",
    "fact_check": "事实核验",
}
STATE_LABELS = {
    "consistently_visible": "稳定可见",
    "consistently_absent": "稳定缺席",
    "wording_sensitive": "对问法敏感",
    "partially_observed": "观测不完整",
    "unobserved": "尚未观测",
}
REPEAT_STATE_LABELS = {
    "not_repeated": "未做重复观测",
    "stable_visible": "重复观测均出现",
    "stable_absent": "重复观测均缺席",
    "unstable": "重复结果不稳定",
}


def _round(value: float | None) -> float | None:
    """Round a public ratio consistently"""

    return None if value is None else round(value + 1e-12, 1)


def _platform_state(expected: int, observations_by_variant: list[list[dict[str, Any]]]) -> str:
    """Classify one platform-family cell without hiding missing variants"""

    observed_by_variant = [
        [item for item in observations if item.get("status") == "observed"]
        for observations in observations_by_variant
    ]
    observed_by_variant = [items for items in observed_by_variant if items]
    if not observed_by_variant:
        return "unobserved"
    if expected < 2 or len(observed_by_variant) < expected:
        return "partially_observed"
    present = [
        any(item["position"] != "absent" for item in items)
        for items in observed_by_variant
    ]
    if all(present):
        return "consistently_visible"
    if not any(present):
        return "consistently_absent"
    return "wording_sensitive"


def _repeat_state(observations_by_variant: list[list[dict[str, Any]]]) -> str:
    """Classify repeatability without confusing repeated runs with wording variants"""

    repeated = [
        [item for item in observations if item.get("status") == "observed"]
        for observations in observations_by_variant
        if len([item for item in observations if item.get("status") == "observed"]) >= 2
    ]
    if not repeated:
        return "not_repeated"
    directions = [
        {item["position"] != "absent" for item in observations}
        for observations in repeated
    ]
    if any(len(items) > 1 for items in directions):
        return "unstable"
    if all(items == {True} for items in directions):
        return "stable_visible"
    if all(items == {False} for items in directions):
        return "stable_absent"
    return "unstable"


def _cross_platform_state(platforms: list[dict[str, Any]]) -> str:
    """Describe whether complete platform cells tell the same directional story"""

    states = {
        item["state"]
        for item in platforms
        if item["state"] not in {"unobserved", "partially_observed"}
    }
    if not states:
        return "insufficient_data"
    if states == {"consistently_visible"}:
        return "consistent_strength"
    if states == {"consistently_absent"}:
        return "consistent_gap"
    return "mixed_by_platform_or_wording"


def summarize(research: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    """Build a deterministic family-level summary from contract-valid v2 inputs"""

    validation = validate_evidence_package(research, evidence)
    if not validation["valid"]:
        messages = "; ".join(f"{item['path']}: {item['message']}" for item in validation["errors"])
        raise ValueError(f"research and evidence must pass validation: {messages}")

    queries = research["query_protocol"]["queries"]
    queries_by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for query in queries:
        queries_by_family[query["query_type"]].append(query)

    observations_by_pair: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for observation in evidence["observations"]:
        observations_by_pair[(observation["query_id"], observation["engine"]["name"])].append(observation)

    family_results: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    expected_cells = observed_cells = 0

    family_order = [*REQUIRED_FAMILIES, *sorted(set(queries_by_family) - set(REQUIRED_FAMILIES))]
    for family_id in family_order:
        variants = queries_by_family.get(family_id, [])
        if not variants:
            gaps.append({
                "gap_type": "missing_family",
                "family_id": family_id,
                "message": f"缺少{FAMILY_LABELS.get(family_id, family_id)}查询族",
            })
            continue

        engines = sorted({engine for query in variants for engine in query["engines"]})
        platform_results: list[dict[str, Any]] = []
        for engine in engines:
            expected_query_ids = [query["query_id"] for query in variants if engine in query["engines"]]
            required_variant_count = max(
                len(expected_query_ids),
                2 if family_id in REQUIRED_FAMILIES else len(expected_query_ids),
            )
            observations_by_variant = [
                observations_by_pair.get((query_id, engine), [])
                for query_id in expected_query_ids
            ]
            observed = [
                item
                for observations in observations_by_variant
                for item in observations
                if item["status"] == "observed"
            ]
            repeated_observations = [
                items
                for observations in observations_by_variant
                if len(items := [item for item in observations if item["status"] == "observed"]) >= 2
            ]
            repeated_runs = [item for items in repeated_observations for item in items]
            repeated_present = [item for item in repeated_runs if item["position"] != "absent"]
            observed_variant_count = sum(
                any(item["status"] == "observed" for item in observations)
                for observations in observations_by_variant
            )
            present = [item for item in observed if item["position"] != "absent"]
            top1 = [item for item in observed if item["position"] in {"top1", "top1_tied"}]
            recommended = [item for item in observed if item.get("recommendation") in {"explicit", "tied"}]
            negative = [item for item in observed if item.get("recommendation") == "negative"]
            major_fact_error_observations = [
                item
                for item in observed
                if any(error.get("severity") == "major" for error in (item.get("fact_errors") or []))
            ]
            major_fact_errors = [
                error
                for item in major_fact_error_observations
                for error in (item.get("fact_errors") or [])
                if error.get("severity") == "major"
            ]
            state = _platform_state(required_variant_count, observations_by_variant)
            repeat_state = _repeat_state(observations_by_variant)
            expected_cells += required_variant_count
            observed_cells += observed_variant_count
            result = {
                "platform": engine,
                "expected_variants": required_variant_count,
                "protocol_variants": len(expected_query_ids),
                "observed_variants": observed_variant_count,
                "observed_runs": len(observed),
                "presence_rate": _round(len(present) / len(observed) * 100) if observed else None,
                "top1_rate": _round(len(top1) / len(observed) * 100) if observed else None,
                "recommendation_rate": _round(len(recommended) / len(observed) * 100) if observed else None,
                "negative_recommendation_count": len(negative),
                "major_fact_error_count": len(major_fact_errors),
                "state": state,
                "state_label": STATE_LABELS[state],
                "repeat_state": repeat_state,
                "repeat_state_label": REPEAT_STATE_LABELS[repeat_state],
                "observation_ids": [item["observation_id"] for item in observed],
            }
            platform_results.append(result)

            if major_fact_errors:
                findings.append({
                    "finding_type": "major_fact_error",
                    "family_id": family_id,
                    "platform": engine,
                    "statement": (
                        f"{engine} 在{FAMILY_LABELS.get(family_id, family_id)}回答中出现 "
                        f"{len(major_fact_errors)} 项重大事实或实体错误"
                    ),
                    "observation_ids": [item["observation_id"] for item in major_fact_error_observations],
                })

            if negative:
                findings.append({
                    "finding_type": "negative_recommendation",
                    "family_id": family_id,
                    "platform": engine,
                    "statement": (
                        f"{engine} 在{FAMILY_LABELS.get(family_id, family_id)}的 "
                        f"{len(negative)} 次回答中对目标品牌给出负向或不推荐判断"
                    ),
                    "observation_ids": [item["observation_id"] for item in negative],
                })

            if repeat_state == "unstable":
                findings.append({
                    "finding_type": "repeat_unstable",
                    "family_id": family_id,
                    "platform": engine,
                    "statement": (
                        f"{engine} 在{FAMILY_LABELS.get(family_id, family_id)}同一问法的 {len(repeated_runs)} 次重复中"
                        f"有 {len(repeated_present)} 次出现、{len(repeated_runs) - len(repeated_present)} 次缺席，结果不稳定"
                    ),
                    "observation_ids": [item["observation_id"] for item in repeated_runs],
                })

            if state in {"consistently_visible", "consistently_absent", "wording_sensitive"}:
                statement = {
                    "consistently_visible": f"{engine} 在{FAMILY_LABELS.get(family_id, family_id)}的不同问法中均能发现品牌",
                    "consistently_absent": f"{engine} 在{FAMILY_LABELS.get(family_id, family_id)}的不同问法中均未发现品牌",
                    "wording_sensitive": f"{engine} 的{FAMILY_LABELS.get(family_id, family_id)}结果随问法发生变化",
                }[state]
                findings.append({
                    "finding_type": state,
                    "family_id": family_id,
                    "platform": engine,
                    "statement": statement,
                    "observation_ids": result["observation_ids"],
                })

        if len(variants) < 2:
            gaps.append({
                "gap_type": "insufficient_variants",
                "family_id": family_id,
                "message": f"{FAMILY_LABELS.get(family_id, family_id)}只有 {len(variants)} 种问法，无法判断措辞敏感性",
            })

        for platform in platform_results:
            if platform["observed_variants"] < platform["expected_variants"]:
                gaps.append({
                    "gap_type": "missing_observations",
                    "family_id": family_id,
                    "platform": platform["platform"],
                    "message": f"{platform['platform']} 的{FAMILY_LABELS.get(family_id, family_id)}缺少 {platform['expected_variants'] - platform['observed_variants']} 种问法观测",
                })

        family_results.append({
            "family_id": family_id,
            "label": FAMILY_LABELS.get(family_id, family_id),
            "variant_count": len(variants),
            "variants": [
                {
                    "query_id": query["query_id"],
                    "query": query["query"],
                    "commercial_relevance": query["commercial_relevance"],
                }
                for query in variants
            ],
            "platforms": platform_results,
            "cross_platform_state": _cross_platform_state(platform_results),
        })

    required_ready = all(len(queries_by_family.get(family_id, [])) >= 2 for family_id in REQUIRED_FAMILIES)
    if required_ready and expected_cells > 0 and observed_cells == expected_cells:
        status = "complete"
    elif observed_cells:
        status = "partial"
    else:
        status = "insufficient_data"

    return {
        "schema_version": SCHEMA_VERSION,
        "method_status": "candidate_mvp",
        "brand": evidence["brand"],
        "protocol_id": evidence["protocol_id"],
        "assessment": {
            "status": status,
            "required_families": len(REQUIRED_FAMILIES),
            "required_variants_per_family": 2,
            "expected_observations": expected_cells,
            "observed_count": observed_cells,
            "coverage_rate": _round(observed_cells / expected_cells * 100) if expected_cells else 0.0,
            "limitations": [item["message"] for item in gaps],
        },
        "families": family_results,
        "key_findings": findings,
        "evidence_gaps": gaps,
    }


def _load_json(path: str) -> Any:
    """Load a UTF-8 JSON file"""

    with Path(path).open(encoding="utf-8") as file:
        return json.load(file)


def main() -> int:
    """Validate inputs and print one family-level JSON summary"""

    parser = argparse.ArgumentParser(description="Summarize Brand GEO evidence by query family")
    parser.add_argument("research_path")
    parser.add_argument("evidence_path")
    parser.add_argument("-o", "--output")
    args = parser.parse_args()
    try:
        result = summarize(_load_json(args.research_path), _load_json(args.evidence_path))
        rendered = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            Path(args.output).write_text(rendered + "\n", encoding="utf-8")
        else:
            print(rendered)
        return 0
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"查询族汇总失败: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

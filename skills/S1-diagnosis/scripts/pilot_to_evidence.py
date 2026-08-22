#!/usr/bin/env python3
"""Convert one repeated consumer-App pilot into the v2 evidence package"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


PRODUCT_LABELS = {
    "qwen": "千问",
    "doubao": "豆包",
    "deepseek": "DeepSeek",
    "yuanbao": "腾讯元宝",
}


def _load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def _safe_id(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def convert(research: dict[str, Any], experiment: dict[str, Any], root: Path) -> dict[str, Any]:
    """Preserve run-level evidence while deriving only explicit entity observations"""

    brand = research["scope"]["brand"]
    observations: list[dict[str, Any]] = []
    for platform in experiment["platforms"]:
        product = platform["consumer_product"]
        engine_name = PRODUCT_LABELS.get(product, product)
        for run in platform["runs"]:
            response = _load(root / run["response_path"])
            annotation = run["annotation"]
            mentioned = brand in annotation.get("entities_mentioned", [])
            recommended = brand in annotation.get("entities_recommended", [])
            first = annotation.get("first_entity") == brand
            observed = response.get("status") == "completed"
            coverage = {
                "intro": None,
                "selling_points": None,
                "products": None,
                "pricing": None,
                "reputation": None,
                "news": None,
            }
            if not mentioned:
                coverage = {name: False for name in coverage}
            observations.append({
                "observation_id": f'obs-{_safe_id(run["run_id"])}',
                "query_id": experiment["query_id"],
                "source_type": "direct_engine_observation",
                "status": "observed" if observed else "unobserved",
                "engine": {
                    "name": engine_name,
                    "model": response.get("model_reported"),
                    "web_enabled": response.get("search_executed"),
                },
                "observed_at": response.get("collected_at") if observed else None,
                "raw_response": response.get("raw_text") if observed else None,
                "position": ("top1" if first else ("mention" if mentioned else "absent")) if observed else None,
                "recommendation": ("explicit" if recommended else None) if observed else None,
                "citations": [] if observed else None,
                "sentiment": ("positive" if recommended else None) if observed else None,
                "coverage": coverage if observed else None,
                "fact_errors": [] if observed else None,
            })

    return {
        "schema_version": "2.0.0",
        "evidence_package_id": f'evidence-{_safe_id(experiment["experiment_id"])}',
        "scope_id": research["scope"]["scope_id"],
        "context_id": research["domain_context"]["context_id"],
        "protocol_id": research["query_protocol"]["protocol_id"],
        "brand": brand,
        "foundation": {
            "wiki": {"value": None, "evidence_ids": []},
            "official_site_structured": {"value": None, "evidence_ids": []},
            "third_party_count": {"value": None, "evidence_ids": []},
            "knowledge_graph": {"value": None, "evidence_ids": []},
            "content_active": {"value": None, "evidence_ids": []},
        },
        "observations": observations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert repeated pilot artifacts to v2 evidence")
    parser.add_argument("research_path")
    parser.add_argument("experiment_path")
    parser.add_argument("-o", "--output", required=True)
    args = parser.parse_args()
    research_path = Path(args.research_path).resolve()
    experiment_path = Path(args.experiment_path).resolve()
    root = next(
        parent
        for parent in experiment_path.parents
        if (parent / "brand-geo-audit").is_dir()
    )
    result = convert(_load(research_path), _load(experiment_path), root)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"证据包已生成: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Normalize consumer-App browser captures and build an evidence package"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from collection_contracts import canonical_fingerprint  # noqa: E402


PRODUCT_LABELS = {
    "qwen": "千问",
    "doubao": "豆包",
    "deepseek": "DeepSeek",
    "yuanbao": "腾讯元宝",
}


def _load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _safe_id(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _relative(path: Path, repo_root: Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def _source_count(capture: dict[str, Any]) -> int | None:
    explicit = capture.get("source_count")
    if isinstance(explicit, int):
        return explicit
    text = capture.get("raw_text") or ""
    match = re.search(r"(?:参考|已阅读)\s*(\d+)\s*(?:篇资料|个网页)", text)
    return int(match.group(1)) if match else None


def _citation_mode(citations: list[dict[str, Any]], source_count: int | None) -> str:
    if citations:
        return "structured"
    if source_count is not None:
        return "inline_only"
    return "unknown"


def _source_type(url: str) -> str:
    host = urlparse(url).hostname or ""
    if host.endswith(("dynaudio.cn", "sonystyle.com.cn")):
        return "official"
    if host.endswith("baike.baidu.com"):
        return "wiki"
    if host.endswith(("hdavchina.com", "av-china.com")):
        return "authoritative"
    if host.endswith(("zhihu.com", "smzdm.com", "xiaohongshu.com", "douyin.com")):
        return "social"
    return "low_quality"


def _evidence_citations(
    citations: list[dict[str, Any]],
    verified_sources: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in citations:
        url = item.get("url")
        if not isinstance(url, str) or not url.startswith(("http://", "https://")) or url in seen:
            continue
        seen.add(url)
        verified = verified_sources.get(url.rstrip("/"), {})
        result.append({
            "url": url,
            "domain": urlparse(url).hostname or "unknown",
            "source_type": verified.get("source_type", _source_type(url)),
            "brand_owned": False,
            "verification_status": verified.get("verification_status", "unverified"),
        })
    return result


def _coverage(position: str | None) -> dict[str, bool | None]:
    fields = ("intro", "selling_points", "products", "pricing", "reputation", "news")
    if position == "absent":
        return {field: False for field in fields}
    return {field: None for field in fields}


def _request(
    protocol_id: str,
    product: str,
    query: dict[str, Any],
    requested_at: str,
    suffix: str = "",
) -> dict[str, Any]:
    identifier = f"mvp4-{product}-{_safe_id(query['query_id'])}{suffix}"
    return {
        "schema_version": "1.0.0",
        "request_id": f"request-{identifier}",
        "protocol_id": protocol_id,
        "query_id": query["query_id"],
        "consumer_product": product,
        "provider": "consumer_web",
        "channel": "official_app_browser",
        "query": query["query"],
        "requested_at": requested_at,
        "configuration": {
            "model_requested": None,
            "search_mode": "native",
            "search_required": False,
            "thinking_mode": "platform_default",
            "temperature": None,
            "max_output_tokens": None,
            "region": "cn-mainland",
            "language": "zh-CN",
        },
    }


def _response(
    request: dict[str, Any],
    capture: dict[str, Any],
    screenshot_path: str,
    suffix: str = "",
) -> dict[str, Any]:
    source_count = _source_count(capture)
    citations = [
        {"url": item["url"], "title": item.get("title") or None}
        for item in capture.get("citations", [])
        if isinstance(item, dict) and isinstance(item.get("url"), str) and item["url"].startswith(("http://", "https://"))
    ]
    identifier = f"mvp4-{request['consumer_product']}-{_safe_id(request['query_id'])}{suffix}"
    page_url = capture.get("page_url")
    platform_request_id = page_url.rstrip("/").split("/")[-1] if isinstance(page_url, str) and "/chat/" in page_url else None
    return {
        "schema_version": "1.0.0",
        "response_id": f"response-{identifier}",
        "request_id": request["request_id"],
        "protocol_id": request["protocol_id"],
        "query_id": request["query_id"],
        "consumer_product": request["consumer_product"],
        "provider": request["provider"],
        "channel": request["channel"],
        "status": "completed",
        "collected_at": capture["collected_at"],
        "model_requested": None,
        "model_reported": capture.get("model_reported"),
        "search_requested": True,
        "search_executed": True if source_count is not None or citations else None,
        "citation_mode": _citation_mode(citations, source_count),
        "raw_text": capture["raw_text"],
        "citations": citations,
        "raw_payload": {
            "page_url": page_url,
            "page_title": capture.get("page_title"),
            "mode_label": capture.get("mode_label"),
            "reported_source_count": source_count,
            "capture_scope": "visible answer and explicit source indicators",
        },
        "request_fingerprint": canonical_fingerprint(request),
        "platform_request_id": platform_request_id,
        "screenshot_path": screenshot_path,
        "error": None,
    }


def _observation(
    response: dict[str, Any],
    annotation: dict[str, Any],
    verified_sources: dict[str, dict[str, Any]],
    suffix: str = "",
) -> dict[str, Any]:
    product = response["consumer_product"]
    position = annotation["position"]
    citations = _evidence_citations(response["citations"], verified_sources)
    if position == "absent":
        citations = []
    elif response["citation_mode"] != "structured":
        citations = None
    return {
        "observation_id": f"obs-mvp4-{product}-{_safe_id(response['query_id'])}{suffix}",
        "query_id": response["query_id"],
        "source_type": "direct_engine_observation",
        "status": "observed",
        "engine": {
            "name": PRODUCT_LABELS[product],
            "model": response.get("model_reported"),
            "web_enabled": response.get("search_executed"),
        },
        "observed_at": response["collected_at"],
        "raw_response": response["raw_text"],
        "position": position,
        "recommendation": annotation.get("recommendation"),
        "citations": citations,
        "sentiment": annotation.get("sentiment"),
        "coverage": _coverage(position),
        "fact_errors": annotation.get("fact_errors", []),
    }


def _normalize_captures(
    research: dict[str, Any],
    capture_root: Path,
    output_root: Path,
    repo_root: Path,
    annotations: dict[str, Any],
    verified_sources: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    protocol = research["query_protocol"]
    queries = {item["query_id"]: item for item in protocol["queries"]}
    observations: list[dict[str, Any]] = []
    for capture_path in sorted(capture_root.glob("*/*.capture.json")):
        product = capture_path.parent.name
        query_id = capture_path.name.removesuffix(".capture.json")
        key = f"{product}/{query_id}"
        if key not in annotations:
            raise ValueError(f"missing semantic annotation for {key}")
        capture = _load(capture_path)
        request = _request(protocol["protocol_id"], product, queries[query_id], capture["collected_at"])
        screenshot = capture_path.with_suffix("").with_suffix(".png")
        response = _response(request, capture, _relative(screenshot, repo_root))
        directory = output_root / product
        _write(directory / f"{query_id}-request.json", request)
        _write(directory / f"{query_id}-response.json", response)
        observations.append(_observation(response, annotations[key], verified_sources))
    return observations


def _legacy_qwen_runs(
    research: dict[str, Any],
    experiment_path: Path,
    output_root: Path,
    repo_root: Path,
    verified_sources: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    experiment = _load(experiment_path)
    query = next(item for item in research["query_protocol"]["queries"] if item["query_id"] == experiment["query_id"])
    observations: list[dict[str, Any]] = []
    for run in experiment["platforms"][0]["runs"]:
        index = run["repetition_index"]
        original = _load(repo_root / run["response_path"])
        capture = {
            "collected_at": original["collected_at"],
            "model_reported": original.get("model_reported"),
            "raw_text": original["raw_text"],
            "citations": original.get("citations", []),
            "source_count": (original.get("raw_payload") or {}).get("reported_source_count"),
            "page_url": (original.get("raw_payload") or {}).get("page_url"),
            "page_title": (original.get("raw_payload") or {}).get("page_title"),
            "mode_label": (original.get("raw_payload") or {}).get("mode_label"),
        }
        suffix = f"-repeat-{index}"
        request = _request(research["query_protocol"]["protocol_id"], "qwen", query, original["collected_at"], suffix)
        response = _response(request, capture, run["response_path"].replace("-response.json", ".png"), suffix)
        directory = output_root / "qwen"
        _write(directory / f"{query['query_id']}{suffix}-request.json", request)
        _write(directory / f"{query['query_id']}{suffix}-response.json", response)
        annotation = run["annotation"]
        target = research["scope"]["brand"]
        observations.append(_observation(response, {
            "position": "top1" if annotation.get("first_entity") == target else ("mention" if target in annotation.get("entities_mentioned", []) else "absent"),
            "recommendation": "explicit" if target in annotation.get("entities_recommended", []) else None,
            "sentiment": "positive" if target in annotation.get("entities_recommended", []) else None,
            "fact_errors": [],
        }, verified_sources, suffix))
    return observations


def build_package(
    research_path: Path,
    capture_root: Path,
    annotations_path: Path,
    output_root: Path,
    repo_root: Path,
    legacy_experiment: Path | None,
) -> dict[str, Any]:
    research = _load(research_path)
    annotation_package = _load(annotations_path)
    annotations = annotation_package["annotations"]
    source_type_map = {"official": "official", "authoritative_media": "authoritative", "user_provided": "low_quality", "audit_artifact": "low_quality"}
    verified_sources = {
        item["url"].rstrip("/"): {
            "source_type": source_type_map.get(item["source_type"], "low_quality"),
            "verification_status": item["verification_status"],
        }
        for item in research["domain_context"].get("sources", [])
        if item.get("url")
    }
    observations = _normalize_captures(research, capture_root, output_root, repo_root, annotations, verified_sources)
    if legacy_experiment:
        observations.extend(_legacy_qwen_runs(research, legacy_experiment, output_root, repo_root, verified_sources))
    return {
        "schema_version": "2.0.0",
        "evidence_package_id": "evidence-dongting-audio-mvp4",
        "scope_id": research["scope"]["scope_id"],
        "context_id": research["domain_context"]["context_id"],
        "protocol_id": research["query_protocol"]["protocol_id"],
        "brand": research["scope"]["brand"],
        "foundation": annotation_package.get("foundation", {
            "wiki": {"value": None, "evidence_ids": []},
            "official_site_structured": {"value": None, "evidence_ids": []},
            "third_party_count": {"value": None, "evidence_ids": []},
            "knowledge_graph": {"value": None, "evidence_ids": []},
            "content_active": {"value": None, "evidence_ids": []},
        }),
        "observations": observations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize browser captures into Brand GEO contracts")
    parser.add_argument("research_path")
    parser.add_argument("capture_root")
    parser.add_argument("annotations_path")
    parser.add_argument("--normalized-output", required=True)
    parser.add_argument("--evidence-output", required=True)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--legacy-experiment")
    args = parser.parse_args()
    try:
        package = build_package(
            Path(args.research_path).resolve(),
            Path(args.capture_root).resolve(),
            Path(args.annotations_path).resolve(),
            Path(args.normalized_output).resolve(),
            Path(args.repo_root).resolve(),
            Path(args.legacy_experiment).resolve() if args.legacy_experiment else None,
        )
        _write(Path(args.evidence_output), package)
        print(f"浏览器证据包已生成: {args.evidence_output} ({len(package['observations'])} 条观测)")
        return 0
    except (OSError, json.JSONDecodeError, KeyError, ValueError) as error:
        print(f"浏览器证据包生成失败: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

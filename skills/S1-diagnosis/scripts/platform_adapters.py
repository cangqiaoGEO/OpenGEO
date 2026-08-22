#!/usr/bin/env python3
"""Build provider requests and normalize raw API responses without credentials"""

from __future__ import annotations

from typing import Any


def build_provider_request(request: dict[str, Any]) -> dict[str, Any]:
    """Build a credential-free HTTP request description for one official provider"""

    product = request["consumer_product"]
    config = request["configuration"]
    query = request["query"]
    if product == "doubao":
        if request["provider"] == "volcengine_agent_plan":
            return {
                "url": "https://ark.cn-beijing.volces.com/api/plan/v1/messages",
                "credential_env": "ARK_AGENT_PLAN_API_KEY",
                "headers": {"Anthropic-Version": "2023-06-01"},
                "body": {
                    "model": config["model_requested"],
                    "messages": [{"role": "user", "content": query}],
                    "temperature": config["temperature"],
                    "max_tokens": config["max_output_tokens"],
                },
            }
        if request["provider"] == "volcengine_coding_plan":
            body = {
                "model": config["model_requested"],
                "messages": [{"role": "user", "content": query}],
                "thinking": {"type": config["thinking_mode"]} if config["thinking_mode"] in {"enabled", "disabled"} else None,
                "temperature": config["temperature"],
                "max_tokens": config["max_output_tokens"],
            }
            return {
                "url": "https://ark.cn-beijing.volces.com/api/coding/v3/chat/completions",
                "credential_env": "ARK_API_KEY",
                "body": {key: value for key, value in body.items() if value is not None},
            }
        body: dict[str, Any] = {
            "model": config["model_requested"],
            "input": query,
            "thinking": {"type": config["thinking_mode"]} if config["thinking_mode"] in {"enabled", "disabled"} else None,
            "max_output_tokens": config["max_output_tokens"],
        }
        if config["search_mode"] == "native":
            body["tools"] = [{"type": "web_search"}]
        return {
            "url": "https://ark.cn-beijing.volces.com/api/v3/responses",
            "credential_env": "ARK_API_KEY",
            "body": {key: value for key, value in body.items() if value is not None},
        }
    if product == "qwen":
        if request["provider"] == "dashscope_token_plan":
            body = {
                "model": config["model_requested"],
                "input": query,
                "enable_thinking": config["thinking_mode"] == "enabled" if config["thinking_mode"] in {"enabled", "disabled"} else None,
                "max_output_tokens": config["max_output_tokens"],
            }
            if config["search_mode"] == "native":
                body["tools"] = [{"type": "web_search"}]
            return {
                "url": "https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1/responses",
                "credential_env": "DASHSCOPE_API_KEY",
                "body": {key: value for key, value in body.items() if value is not None},
            }
        return {
            "url": "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
            "credential_env": "DASHSCOPE_API_KEY",
            "body": {
                "model": config["model_requested"],
                "input": {"messages": [{"role": "user", "content": query}]},
                "parameters": {
                    "enable_search": config["search_mode"] == "native",
                    "search_options": {
                        "forced_search": config["search_required"],
                        "enable_source": True,
                        "enable_citation": True,
                        "citation_format": "[ref_<number>]",
                    },
                    "temperature": config["temperature"],
                    "max_tokens": config["max_output_tokens"],
                    "result_format": "message",
                },
            },
        }
    if product == "deepseek":
        return {
            "url": "https://api.deepseek.com/chat/completions",
            "credential_env": "DEEPSEEK_API_KEY",
            "body": {
                "model": config["model_requested"],
                "messages": [{"role": "user", "content": query}],
                "thinking": {"type": config["thinking_mode"]} if config["thinking_mode"] in {"enabled", "disabled"} else None,
                "temperature": config["temperature"],
                "max_tokens": config["max_output_tokens"],
            },
        }
    if product == "yuanbao":
        body = {
            "model": config["model_requested"],
            "messages": [{"role": "user", "content": query}],
            "reasoning_effort": (
                "low" if config["thinking_mode"] == "enabled"
                else "no_think" if config["thinking_mode"] == "disabled"
                else None
            ),
            "temperature": config["temperature"],
            "max_tokens": config["max_output_tokens"],
            "stream": False,
        }
        if config["search_mode"] == "native":
            body["web_search_options"] = {"enable": True}
        return {
            "url": "https://tokenhub.tencentmaas.com/v1/chat/completions",
            "credential_env": "TENCENT_TOKENHUB_API_KEY",
            "body": {key: value for key, value in body.items() if value is not None},
        }
    raise ValueError(f"unsupported consumer product {product!r}")


def extract_text(product: str, payload: dict[str, Any]) -> str | None:
    """Extract final answer text while preserving the full payload separately"""

    if product == "doubao":
        anthropic_parts = [
            item.get("text", "")
            for item in payload.get("content", [])
            if item.get("type") == "text"
        ]
        if anthropic_parts:
            return "\n".join(part for part in anthropic_parts if part) or None
        parts = []
        for item in payload.get("output", []):
            if item.get("type") == "message":
                parts.extend(content.get("text", "") for content in item.get("content", []) if content.get("type") == "output_text")
        if parts:
            return "\n".join(part for part in parts if part) or None
        choices = payload.get("choices", [])
        return choices[0].get("message", {}).get("content") if choices else None
    if product == "qwen":
        if isinstance(payload.get("output"), list):
            parts = []
            for item in payload["output"]:
                if item.get("type") == "message":
                    parts.extend(content.get("text", "") for content in item.get("content", []) if content.get("type") == "output_text")
            return "\n".join(part for part in parts if part) or None
        choices = payload.get("output", {}).get("choices", [])
        if choices:
            content = choices[0].get("message", {}).get("content")
            return content if isinstance(content, str) else None
        return payload.get("output", {}).get("text")
    if product in {"deepseek", "yuanbao"}:
        choices = payload.get("choices", [])
        return choices[0].get("message", {}).get("content") if choices else None
    return None


def extract_citations(product: str, payload: dict[str, Any]) -> list[dict[str, str | None]]:
    """Extract only explicit structured citations, never infer URLs from prose"""

    candidates: list[dict[str, Any]] = []
    if product == "qwen":
        if isinstance(payload.get("output"), list):
            for item in payload["output"]:
                if item.get("type") == "web_search_call":
                    candidates.extend(item.get("action", {}).get("sources", []))
        else:
            candidates = payload.get("output", {}).get("search_info", {}).get("search_results", [])
    elif product == "doubao":
        for item in payload.get("output", []):
            if item.get("type") in {"web_search_result", "web_search_call"}:
                candidates.extend(item.get("results", []))
    elif product == "yuanbao":
        choices = payload.get("choices", [])
        if choices:
            candidates.extend(choices[0].get("message", {}).get("search_results", []))
        search_info = payload.get("search_info")
        if isinstance(search_info, dict):
            candidates.extend(search_info.get("search_results", []))
    citations = []
    for item in candidates:
        url = item.get("url")
        if isinstance(url, str) and url.startswith(("http://", "https://")):
            title = item.get("title") if isinstance(item.get("title"), str) else item.get("name")
            citations.append({"url": url, "title": title if isinstance(title, str) else None})
    return citations

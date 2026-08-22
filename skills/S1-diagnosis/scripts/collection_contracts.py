#!/usr/bin/env python3
"""Validate and protect Brand GEO platform collection contracts"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

COLLECTION_SCHEMA_VERSION = "1.0.0"
PRODUCT_PROVIDERS = {
    "doubao": {"official_api": {"volcengine", "volcengine_coding_plan", "volcengine_agent_plan"}, "official_app_browser": {"consumer_web"}},
    "qwen": {"official_api": {"dashscope", "dashscope_token_plan"}, "official_app_browser": {"consumer_web"}},
    "deepseek": {"official_api": {"deepseek"}, "official_app_browser": {"consumer_web"}},
    "yuanbao": {"official_api": {"tencent_tokenhub"}, "official_app_browser": {"consumer_web"}},
}
SECRET_FIELD_PATTERN = re.compile(r"authorization|api[_-]?key|access[_-]?token|secret", re.IGNORECASE)
SECRET_VALUE_PATTERNS = (
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE),
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"),
)


def canonical_fingerprint(request: dict[str, Any]) -> str:
    """Return a deterministic SHA-256 fingerprint for a platform request"""

    payload = json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def redact_secrets(value: Any) -> Any:
    """Return a recursively redacted copy suitable for persisted diagnostics"""

    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if SECRET_FIELD_PATTERN.search(str(key)) else redact_secrets(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    if isinstance(value, str):
        redacted = value
        for pattern in SECRET_VALUE_PATTERNS:
            redacted = pattern.sub("[REDACTED]", redacted)
        return redacted
    return value


def _timestamp(value: Any) -> bool:
    """Return whether a value is an ISO timestamp with an explicit timezone"""

    try:
        return isinstance(value, str) and datetime.fromisoformat(value).tzinfo is not None
    except ValueError:
        return False


def _required(obj: Any, fields: set[str], path: str, errors: list[dict[str, str]]) -> dict[str, Any]:
    """Validate an exact object shape and return a safe object value"""

    if not isinstance(obj, dict):
        errors.append({"path": path, "message": f"expected object, got {type(obj).__name__}"})
        return {}
    for field in sorted(fields - set(obj)):
        errors.append({"path": f"{path}.{field}", "message": "required field is missing"})
    for field in sorted(set(obj) - fields):
        errors.append({"path": f"{path}.{field}", "message": "field is not allowed"})
    return obj


def validate_platform_request(request: Any) -> dict[str, Any]:
    """Validate a platform request and cross-field collection semantics"""

    errors: list[dict[str, str]] = []
    fields = {"schema_version", "request_id", "protocol_id", "query_id", "consumer_product", "provider", "channel", "query", "requested_at", "configuration"}
    request = _required(request, fields, "request", errors)
    if request.get("schema_version") != COLLECTION_SCHEMA_VERSION:
        errors.append({"path": "request.schema_version", "message": f"expected {COLLECTION_SCHEMA_VERSION!r}"})
    product = request.get("consumer_product")
    channel = request.get("channel")
    expected_providers = PRODUCT_PROVIDERS.get(product, {}).get(channel)
    if expected_providers is None:
        errors.append({"path": "request.channel", "message": f"unsupported product-channel combination {product!r}/{channel!r}"})
    elif request.get("provider") not in expected_providers:
        errors.append({"path": "request.provider", "message": f"expected one of {sorted(expected_providers)!r} for {product!r}/{channel!r}"})
    if not isinstance(request.get("query"), str) or not request.get("query", "").strip():
        errors.append({"path": "request.query", "message": "expected non-empty query"})
    if not _timestamp(request.get("requested_at")):
        errors.append({"path": "request.requested_at", "message": "expected ISO date-time with timezone"})

    config_fields = {"model_requested", "search_mode", "search_required", "thinking_mode", "temperature", "max_output_tokens", "region", "language"}
    config = _required(request.get("configuration"), config_fields, "request.configuration", errors)
    if config.get("search_mode") not in {"native", "none"}:
        errors.append({"path": "request.configuration.search_mode", "message": "expected 'native' or 'none'"})
    if not isinstance(config.get("search_required"), bool):
        errors.append({"path": "request.configuration.search_required", "message": "expected boolean"})
    if config.get("search_required") and config.get("search_mode") != "native":
        errors.append({"path": "request.configuration.search_required", "message": "search can only be required in native mode"})
    if product == "deepseek" and channel == "official_api" and config.get("search_mode") != "none":
        errors.append({"path": "request.configuration.search_mode", "message": "DeepSeek official API has no verified native web-search contract"})
    if product == "yuanbao" and channel == "official_api" and config.get("model_requested") != "hy3":
        errors.append({"path": "request.configuration.model_requested", "message": "Tencent TokenHub comparison channel is fixed to model 'hy3'"})
    if channel == "official_app_browser" and config.get("model_requested") is not None:
        errors.append({"path": "request.configuration.model_requested", "message": "browser collection cannot claim an unverified model id"})
    if channel == "official_api" and not isinstance(config.get("model_requested"), str):
        errors.append({"path": "request.configuration.model_requested", "message": "official API collection requires an explicit model id"})
    temperature = config.get("temperature")
    if temperature is not None and (isinstance(temperature, bool) or not isinstance(temperature, (int, float)) or not 0 <= temperature <= 2):
        errors.append({"path": "request.configuration.temperature", "message": "expected number from 0 to 2 or null"})
    return {"valid": not errors, "errors": errors, "fingerprint": canonical_fingerprint(request) if not errors else None}


def validate_raw_response(request: Any, response: Any) -> dict[str, Any]:
    """Validate a raw response against its exact originating request"""

    request_result = validate_platform_request(request)
    errors = list(request_result["errors"])
    fields = {"schema_version", "response_id", "request_id", "protocol_id", "query_id", "consumer_product", "provider", "channel", "status", "collected_at", "model_requested", "model_reported", "search_requested", "search_executed", "citation_mode", "raw_text", "citations", "raw_payload", "request_fingerprint", "platform_request_id", "screenshot_path", "error"}
    response = _required(response, fields, "response", errors)
    if response.get("schema_version") != COLLECTION_SCHEMA_VERSION:
        errors.append({"path": "response.schema_version", "message": f"expected {COLLECTION_SCHEMA_VERSION!r}"})
    for field in ("request_id", "protocol_id", "query_id", "consumer_product", "provider", "channel"):
        if response.get(field) != request.get(field):
            errors.append({"path": f"response.{field}", "message": f"must match request value {request.get(field)!r}"})
    config = request.get("configuration", {}) if isinstance(request.get("configuration"), dict) else {}
    expected = {
        "model_requested": config.get("model_requested"),
        "search_requested": config.get("search_mode") == "native",
        "request_fingerprint": request_result.get("fingerprint"),
    }
    for field, value in expected.items():
        if response.get(field) != value:
            errors.append({"path": f"response.{field}", "message": f"expected {value!r}"})
    if not _timestamp(response.get("collected_at")):
        errors.append({"path": "response.collected_at", "message": "expected ISO date-time with timezone"})
    status = response.get("status")
    if status not in {"completed", "failed", "blocked_auth"}:
        errors.append({"path": "response.status", "message": "unsupported response status"})
    if status == "completed":
        if not isinstance(response.get("raw_text"), str) or not response.get("raw_text", "").strip():
            errors.append({"path": "response.raw_text", "message": "completed response requires non-empty text"})
        if response.get("error") is not None:
            errors.append({"path": "response.error", "message": "completed response cannot contain an error"})
        if config.get("search_required") and response.get("search_executed") is not True:
            errors.append({"path": "response.search_executed", "message": "required search was not proven to execute"})
    elif not isinstance(response.get("error"), str) or not response.get("error", "").strip():
        errors.append({"path": "response.error", "message": "non-completed response requires a sanitized error"})
    if response.get("channel") == "official_app_browser" and not response.get("screenshot_path"):
        errors.append({"path": "response.screenshot_path", "message": "browser evidence requires a screenshot path"})
    if redact_secrets(response) != response:
        errors.append({"path": "response", "message": "response contains credential-like material and must be redacted"})
    return {"valid": not errors, "errors": errors}


def _load(path: str) -> Any:
    """Load a UTF-8 JSON document"""

    with Path(path).open(encoding="utf-8") as file:
        return json.load(file)


def main() -> int:
    """Validate one request or a request-response pair"""

    parser = argparse.ArgumentParser(description="Validate Brand GEO platform collection contracts")
    parser.add_argument("request_path")
    parser.add_argument("response_path", nargs="?")
    args = parser.parse_args()
    try:
        request = _load(args.request_path)
        result = validate_raw_response(request, _load(args.response_path)) if args.response_path else validate_platform_request(request)
    except (OSError, json.JSONDecodeError) as error:
        result = {"valid": False, "errors": [{"path": "$", "message": str(error)}]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

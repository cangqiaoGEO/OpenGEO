#!/usr/bin/env python3
"""Collect one official API response with bounded retries and secret-safe persistence"""

from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from collection_contracts import canonical_fingerprint, redact_secrets, validate_platform_request, validate_raw_response  # noqa: E402
from platform_adapters import build_provider_request, extract_citations, extract_text  # noqa: E402


MODULE_ROOT = SCRIPT_DIR.parent
ALLOWED_LOCAL_ENV_KEYS = {
    "ARK_API_KEY",
    "ARK_AGENT_PLAN_API_KEY",
    "DASHSCOPE_API_KEY",
    "DEEPSEEK_API_KEY",
    "TENCENT_TOKENHUB_API_KEY",
}


def load_local_env(path: Path | None = None) -> None:
    """Load allowlisted module-local credentials without shell evaluation or overwrite"""

    env_path = path or MODULE_ROOT / ".env"
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key not in ALLOWED_LOCAL_ENV_KEYS:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if value:
            os.environ.setdefault(key, value)


def _load(path: str) -> dict[str, Any]:
    """Load one UTF-8 request document"""

    with Path(path).open(encoding="utf-8") as file:
        return json.load(file)


def _tls_context() -> ssl.SSLContext:
    """Build a verified TLS context with portable CA bundle fallbacks"""

    defaults = ssl.get_default_verify_paths()
    candidates = (
        os.environ.get("SSL_CERT_FILE"),
        defaults.cafile,
        defaults.openssl_cafile,
        "/etc/ssl/cert.pem",
        "/opt/homebrew/etc/ca-certificates/cert.pem",
    )
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return ssl.create_default_context(cafile=candidate)
    return ssl.create_default_context()


def _post_json(
    url: str,
    body: dict[str, Any],
    api_key: str,
    timeout: float,
    extra_headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """POST JSON using a bearer credential without exposing it to diagnostics"""

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    headers.update(extra_headers or {})
    request = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout, context=_tls_context()) as response:
        return json.loads(response.read().decode("utf-8"))


def _search_executed(product: str, payload: dict[str, Any], citations: list[dict[str, Any]]) -> bool:
    """Return true only when structured response evidence proves a search occurred"""

    if citations:
        return True
    if product == "doubao":
        return any(item.get("type") in {"web_search_call", "web_search_result"} for item in payload.get("output", []))
    if product == "qwen":
        output = payload.get("output")
        if isinstance(output, list):
            return any(item.get("type") == "web_search_call" for item in output)
        search_info = output.get("search_info") if isinstance(output, dict) else None
        return isinstance(search_info, dict) and bool(search_info)
    if product == "yuanbao":
        usage = payload.get("usage", {})
        tool_usage = usage.get("tool_usage", {}) if isinstance(usage, dict) else {}
        return isinstance(tool_usage, dict) and tool_usage.get("web_search_call", 0) > 0
    return False


def _response(request: dict[str, Any], payload: dict[str, Any], status: str, error: str | None) -> dict[str, Any]:
    """Normalize a provider payload without interpreting brand semantics"""

    product = request["consumer_product"]
    config = request["configuration"]
    citations = extract_citations(product, payload) if status == "completed" else []
    raw_text = extract_text(product, payload) if status == "completed" else None
    search_executed = _search_executed(product, payload, citations) if config["search_mode"] == "native" else False
    platform_request_id = payload.get("id") or payload.get("request_id")
    model_reported = payload.get("model")
    return {
        "schema_version": "1.0.0",
        "response_id": f"response-{request['request_id'].removeprefix('request-')}",
        "request_id": request["request_id"],
        "protocol_id": request["protocol_id"],
        "query_id": request["query_id"],
        "consumer_product": product,
        "provider": request["provider"],
        "channel": request["channel"],
        "status": status,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "model_requested": config["model_requested"],
        "model_reported": model_reported if isinstance(model_reported, str) else None,
        "search_requested": config["search_mode"] == "native",
        "search_executed": search_executed,
        "citation_mode": "structured" if citations else "none",
        "raw_text": raw_text,
        "citations": citations,
        "raw_payload": redact_secrets(payload),
        "request_fingerprint": canonical_fingerprint(request),
        "platform_request_id": str(platform_request_id) if platform_request_id is not None else None,
        "screenshot_path": None,
        "error": error,
    }


def collect(request: dict[str, Any], timeout: float, retries: int) -> dict[str, Any]:
    """Execute one official API request with bounded retry on transient failures"""

    load_local_env()
    descriptor = build_provider_request(request)
    credential_name = descriptor["credential_env"]
    api_key = os.environ.get(credential_name)
    if not api_key:
        return _response(request, {}, "blocked_auth", f"missing required environment variable {credential_name}")
    for attempt in range(retries + 1):
        try:
            payload = _post_json(
                descriptor["url"],
                descriptor["body"],
                api_key,
                timeout,
                descriptor.get("headers"),
            )
            response = _response(request, payload, "completed", None)
            if not response["raw_text"]:
                return _response(request, payload, "failed", "provider response did not contain extractable answer text")
            return response
        except urllib.error.HTTPError as error:
            retryable = error.code == 429 or 500 <= error.code < 600
            message = f"provider HTTP {error.code}"
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            retryable = True
            message = f"provider transport error: {type(error).__name__}"
        if not retryable or attempt == retries:
            return _response(request, {}, "failed", message)
        time.sleep(2**attempt)
    return _response(request, {}, "failed", "unreachable retry state")


def main() -> int:
    """Dry-run or execute one platform request"""

    parser = argparse.ArgumentParser(description="Collect one Brand GEO official API response")
    parser.add_argument("request_path")
    parser.add_argument("-o", "--output")
    parser.add_argument("--execute", action="store_true", help="perform the external API call")
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--retries", type=int, default=2)
    args = parser.parse_args()
    try:
        request = _load(args.request_path)
    except (OSError, json.JSONDecodeError) as error:
        print(json.dumps({"valid": False, "errors": [{"path": "$", "message": str(error)}]}, ensure_ascii=False, indent=2))
        return 2
    validation = validate_platform_request(request)
    if not validation["valid"]:
        print(json.dumps(validation, ensure_ascii=False, indent=2))
        return 1
    if not args.execute:
        print(json.dumps({"valid": True, "fingerprint": validation["fingerprint"], "request": build_provider_request(request)}, ensure_ascii=False, indent=2))
        return 0
    response = collect(request, args.timeout, max(0, args.retries))
    validation = validate_raw_response(request, response)
    output = json.dumps(response, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(f"{output}\n", encoding="utf-8")
        summary = {
            **validation,
            "response_status": response["status"],
            "error": response["error"],
            "output_path": args.output,
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(output)
    if not validation["valid"]:
        return 1
    return 0 if response["status"] == "completed" else 3


if __name__ == "__main__":
    raise SystemExit(main())

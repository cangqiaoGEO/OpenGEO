"""Collection contract, adapter, and credential-safety tests for Batch D2"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from api_collect import _tls_context  # noqa: E402
from collection_contracts import canonical_fingerprint, redact_secrets, validate_platform_request, validate_raw_response  # noqa: E402
from platform_adapters import build_provider_request, extract_citations, extract_text  # noqa: E402


def load_example(name: str) -> dict:
    """Load one collection example fixture"""

    return json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))


class CollectionContractTest(unittest.TestCase):
    """Protect channel identity, search semantics, and traceability"""

    def setUp(self) -> None:
        self.request = load_example("platform_request_doubao.json")
        self.response = load_example("raw_platform_response_doubao.json")

    def test_example_pair_is_valid_and_fingerprint_is_stable(self) -> None:
        request_result = validate_platform_request(self.request)
        self.assertTrue(request_result["valid"], request_result)
        self.assertEqual(request_result["fingerprint"], self.response["request_fingerprint"])
        self.assertTrue(validate_raw_response(self.request, self.response)["valid"])

    def test_provider_must_match_product_and_channel(self) -> None:
        self.request["provider"] = "deepseek"
        result = validate_platform_request(self.request)
        self.assertFalse(result["valid"])
        self.assertIn("volcengine_coding_plan", str(result["errors"]))

    def test_deepseek_official_api_cannot_claim_native_search(self) -> None:
        self.request["consumer_product"] = "deepseek"
        self.request["provider"] = "deepseek"
        result = validate_platform_request(self.request)
        self.assertFalse(result["valid"])
        self.assertIn("no verified native web-search", str(result["errors"]))

    def test_tencent_api_is_fixed_to_hy3(self) -> None:
        self.request.update({"consumer_product": "yuanbao", "provider": "tencent_tokenhub"})
        self.request["configuration"]["model_requested"] = "hy3-preview"
        result = validate_platform_request(self.request)
        self.assertFalse(result["valid"])
        self.assertIn("fixed to model 'hy3'", str(result["errors"]))

    def test_required_search_must_be_proven(self) -> None:
        self.response["search_executed"] = None
        result = validate_raw_response(self.request, self.response)
        self.assertFalse(result["valid"])
        self.assertIn("required search was not proven", str(result["errors"]))

    def test_browser_channel_requires_screenshot_and_unknown_model(self) -> None:
        request = copy.deepcopy(self.request)
        request.update({"provider": "consumer_web", "channel": "official_app_browser"})
        request["configuration"]["model_requested"] = None
        request["configuration"]["search_required"] = False
        response = copy.deepcopy(self.response)
        for field in ("request_id", "protocol_id", "query_id", "consumer_product", "provider", "channel"):
            response[field] = request[field]
        response.update({
            "model_requested": None,
            "model_reported": None,
            "search_requested": True,
            "search_executed": None,
            "request_fingerprint": canonical_fingerprint(request),
            "screenshot_path": None,
        })
        result = validate_raw_response(request, response)
        self.assertFalse(result["valid"])
        self.assertIn("browser evidence requires a screenshot", str(result["errors"]))

    def test_yuanbao_browser_request_keeps_model_unknown(self) -> None:
        request = load_example("platform_request_yuanbao_browser.json")
        result = validate_platform_request(request)
        self.assertTrue(result["valid"], result)
        self.assertIsNone(request["configuration"]["model_requested"])

    def test_credentials_are_redacted_and_rejected_from_persistence(self) -> None:
        unsafe = {"Authorization": "Bearer " + "secret-value", "nested": {"api_key": "sk-" + "1234567890"}}
        self.assertEqual(redact_secrets(unsafe)["Authorization"], "[REDACTED]")
        self.response["raw_payload"] = unsafe
        result = validate_raw_response(self.request, self.response)
        self.assertFalse(result["valid"])
        self.assertIn("credential-like material", str(result["errors"]))


class PlatformAdapterTest(unittest.TestCase):
    """Verify provider-specific requests preserve platform differences"""

    def setUp(self) -> None:
        self.request = load_example("platform_request_doubao.json")

    def test_doubao_uses_responses_web_search(self) -> None:
        descriptor = build_provider_request(self.request)
        self.assertEqual(descriptor["credential_env"], "ARK_API_KEY")
        self.assertEqual(descriptor["body"]["tools"], [{"type": "web_search"}])

    def test_qwen_uses_source_and_citation_capable_parameters(self) -> None:
        request = copy.deepcopy(self.request)
        request.update({"consumer_product": "qwen", "provider": "dashscope"})
        descriptor = build_provider_request(request)
        options = descriptor["body"]["parameters"]["search_options"]
        self.assertTrue(options["forced_search"])
        self.assertTrue(options["enable_source"])
        self.assertTrue(options["enable_citation"])

    def test_qwen_token_plan_uses_responses_harness(self) -> None:
        request = copy.deepcopy(self.request)
        request.update({"consumer_product": "qwen", "provider": "dashscope_token_plan"})
        request["configuration"].update({"model_requested": "qwen3.8-max", "thinking_mode": "enabled"})
        descriptor = build_provider_request(request)
        self.assertEqual(descriptor["url"], "https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1/responses")
        self.assertEqual(descriptor["body"]["tools"], [{"type": "web_search"}])

    def test_doubao_coding_plan_uses_plan_chat_endpoint(self) -> None:
        request = copy.deepcopy(self.request)
        request.update({"provider": "volcengine_coding_plan"})
        request["configuration"].update({"model_requested": "doubao-seed-2.0-lite", "search_mode": "none", "search_required": False})
        descriptor = build_provider_request(request)
        self.assertEqual(descriptor["url"], "https://ark.cn-beijing.volces.com/api/coding/v3/chat/completions")
        self.assertEqual(descriptor["body"]["model"], "doubao-seed-2.0-lite")

    def test_doubao_agent_plan_uses_anthropic_messages_endpoint(self) -> None:
        request = copy.deepcopy(self.request)
        request.update({"provider": "volcengine_agent_plan"})
        request["configuration"].update({"model_requested": "ark-code-latest", "search_mode": "none", "search_required": False})
        descriptor = build_provider_request(request)
        self.assertEqual(descriptor["url"], "https://ark.cn-beijing.volces.com/api/plan/v1/messages")
        self.assertEqual(descriptor["credential_env"], "ARK_AGENT_PLAN_API_KEY")
        self.assertEqual(descriptor["headers"], {"Anthropic-Version": "2023-06-01"})

    def test_doubao_agent_plan_extracts_anthropic_text(self) -> None:
        payload = {"content": [{"type": "thinking", "thinking": "hidden"}, {"type": "text", "text": "answer"}]}
        self.assertEqual(extract_text("doubao", payload), "answer")

    def test_deepseek_request_has_no_search_tool(self) -> None:
        request = copy.deepcopy(self.request)
        request.update({"consumer_product": "deepseek", "provider": "deepseek"})
        request["configuration"].update({"search_mode": "none", "search_required": False})
        descriptor = build_provider_request(request)
        self.assertNotIn("tools", descriptor["body"])
        self.assertEqual(descriptor["credential_env"], "DEEPSEEK_API_KEY")

    def test_tencent_tokenhub_hy3_uses_native_search(self) -> None:
        request = copy.deepcopy(self.request)
        request.update({"consumer_product": "yuanbao", "provider": "tencent_tokenhub"})
        request["configuration"].update({"model_requested": "hy3", "thinking_mode": "disabled"})
        descriptor = build_provider_request(request)
        self.assertEqual(descriptor["url"], "https://tokenhub.tencentmaas.com/v1/chat/completions")
        self.assertEqual(descriptor["credential_env"], "TENCENT_TOKENHUB_API_KEY")
        self.assertEqual(descriptor["body"]["model"], "hy3")
        self.assertEqual(descriptor["body"]["web_search_options"], {"enable": True})
        self.assertEqual(descriptor["body"]["reasoning_effort"], "no_think")

    def test_tencent_extracts_explicit_search_results(self) -> None:
        payload = {
            "choices": [{"message": {
                "content": "回答[1]",
                "search_results": [{"url": "https://example.com/source", "name": "来源标题"}],
            }}],
        }
        self.assertEqual(extract_text("yuanbao", payload), "回答[1]")
        self.assertEqual(
            extract_citations("yuanbao", payload),
            [{"url": "https://example.com/source", "title": "来源标题"}],
        )

    def test_extractors_do_not_infer_citations_from_prose(self) -> None:
        payload = {"choices": [{"message": {"content": "参考 https://example.com"}}]}
        self.assertEqual(extract_text("deepseek", payload), "参考 https://example.com")
        self.assertEqual(extract_citations("deepseek", payload), [])

    def test_cli_defaults_to_credential_free_dry_run(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(SCRIPTS / "api_collect.py"), str(ROOT / "examples" / "platform_request_doubao.json")],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertTrue(result["valid"])
        self.assertNotIn("Authorization", completed.stdout)

    def test_tls_context_keeps_certificate_verification_enabled(self) -> None:
        context = _tls_context()
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode.name, "CERT_REQUIRED")


if __name__ == "__main__":
    unittest.main()

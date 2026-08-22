"""Repeated browser experiment contract and stability tests for Batch D4"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from collection_contracts import canonical_fingerprint  # noqa: E402
from repeated_experiment import calculate_stability, validate_experiment  # noqa: E402


class RepeatedExperimentTest(unittest.TestCase):
    """Protect repetition completeness, mode consistency, and transparent metrics"""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temporary.name)
        request_template = json.loads((ROOT / "examples" / "platform_request_doubao_browser.json").read_text(encoding="utf-8"))
        annotations = [
            {
                "entities_mentioned": ["供应商甲", "供应商乙"],
                "entities_recommended": ["供应商甲"],
                "first_entity": "供应商甲",
                "recommendation_present": True,
                "selection_criteria": ["课程匹配"],
                "caveats": ["需现场验证"],
            },
            {
                "entities_mentioned": ["供应商甲", "供应商丙"],
                "entities_recommended": ["供应商甲"],
                "first_entity": "供应商甲",
                "recommendation_present": True,
                "selection_criteria": ["课程匹配", "师资服务"],
                "caveats": [],
            },
            {
                "entities_mentioned": ["供应商甲", "供应商乙"],
                "entities_recommended": ["供应商乙"],
                "first_entity": "供应商乙",
                "recommendation_present": True,
                "selection_criteria": ["师资服务"],
                "caveats": [],
            },
        ]
        runs = []
        for index in range(1, 4):
            request = copy.deepcopy(request_template)
            request["request_id"] = f"request-doubao-browser-repeat-{index:03d}"
            request_path = f"artifacts/request-{index}.json"
            response_path = f"artifacts/response-{index}.json"
            response = {
                "schema_version": "1.0.0",
                "response_id": f"response-doubao-browser-repeat-{index:03d}",
                "request_id": request["request_id"],
                "protocol_id": request["protocol_id"],
                "query_id": request["query_id"],
                "consumer_product": "doubao",
                "provider": "consumer_web",
                "channel": "official_app_browser",
                "status": "completed",
                "collected_at": f"2026-08-20T18:0{index}:00+08:00",
                "model_requested": None,
                "model_reported": None,
                "search_requested": True,
                "search_executed": True,
                "citation_mode": "structured",
                "raw_text": "甲方案" + "说明" * index,
                "citations": [{"url": f"https://example.com/{index}", "title": "示例"}],
                "raw_payload": {"fixture": True},
                "request_fingerprint": canonical_fingerprint(request),
                "platform_request_id": None,
                "screenshot_path": f"artifacts/screenshot-{index}.png",
                "error": None,
            }
            (self.project_root / "artifacts").mkdir(exist_ok=True)
            (self.project_root / request_path).write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")
            (self.project_root / response_path).write_text(json.dumps(response, ensure_ascii=False), encoding="utf-8")
            (self.project_root / f"artifacts/screenshot-{index}.png").write_bytes(b"fixture-image")
            runs.append({
                "run_id": f"run-doubao-repeat-{index:03d}",
                "repetition_index": index,
                "request_path": request_path,
                "response_path": response_path,
                "annotation": annotations[index - 1],
            })
        self.experiment = {
            "schema_version": "1.0.0",
            "experiment_id": "experiment-browser-repeatability",
            "protocol_id": request_template["protocol_id"],
            "query_id": request_template["query_id"],
            "query_text": request_template["query"],
            "purpose": "collection_stability",
            "target_repetitions": 3,
            "platforms": [{
                "consumer_product": "doubao",
                "channel": "official_app_browser",
                "mode_policy": {
                    "mode_label": "快速、自动搜索",
                    "thinking_mode": "platform_default",
                    "search_mode": "native",
                    "search_required": False,
                },
                "runs": runs,
            }],
        }

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_valid_experiment_resolves_all_runs(self) -> None:
        result = validate_experiment(self.experiment, self.project_root)
        self.assertTrue(result["valid"], result)
        self.assertEqual(len(result["resolved_runs"]), 3)

    def test_repetition_indexes_must_be_complete(self) -> None:
        self.experiment["platforms"][0]["runs"][2]["repetition_index"] = 2
        result = validate_experiment(self.experiment, self.project_root)
        self.assertFalse(result["valid"])
        self.assertIn("repetition indexes must be 1..3", str(result["errors"]))

    def test_request_mode_must_match_frozen_policy(self) -> None:
        request_path = self.project_root / self.experiment["platforms"][0]["runs"][0]["request_path"]
        request = json.loads(request_path.read_text(encoding="utf-8"))
        request["configuration"]["thinking_mode"] = "disabled"
        request_path.write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")
        result = validate_experiment(self.experiment, self.project_root)
        self.assertFalse(result["valid"])
        self.assertIn("must match mode policy", str(result["errors"]))

    def test_recommended_entity_must_also_be_mentioned(self) -> None:
        annotation = self.experiment["platforms"][0]["runs"][0]["annotation"]
        annotation["entities_recommended"] = ["未提及供应商"]
        result = validate_experiment(self.experiment, self.project_root)
        self.assertFalse(result["valid"])
        self.assertIn("recommended entities must also be mentioned", str(result["errors"]))

    def test_missing_screenshot_is_rejected(self) -> None:
        screenshot = self.project_root / "artifacts/screenshot-1.png"
        screenshot.unlink()
        result = validate_experiment(self.experiment, self.project_root)
        self.assertFalse(result["valid"])
        self.assertIn("referenced screenshot must exist", str(result["errors"]))

    def test_official_api_runs_allow_no_search_and_no_screenshot(self) -> None:
        platform = self.experiment["platforms"][0]
        platform["consumer_product"] = "deepseek"
        platform["channel"] = "official_api"
        platform["mode_policy"].update({
            "mode_label": "deepseek-v4-flash、非思考、无原生搜索",
            "thinking_mode": "disabled",
            "search_mode": "none",
            "search_required": False,
        })
        for run in platform["runs"]:
            request_path = self.project_root / run["request_path"]
            response_path = self.project_root / run["response_path"]
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request.update({"consumer_product": "deepseek", "provider": "deepseek", "channel": "official_api"})
            request["configuration"].update({
                "model_requested": "deepseek-v4-flash",
                "search_mode": "none",
                "search_required": False,
                "thinking_mode": "disabled",
            })
            response = json.loads(response_path.read_text(encoding="utf-8"))
            response.update({
                "consumer_product": "deepseek",
                "provider": "deepseek",
                "channel": "official_api",
                "model_requested": "deepseek-v4-flash",
                "model_reported": "deepseek-v4-flash",
                "search_requested": False,
                "search_executed": False,
                "citation_mode": "none",
                "citations": [],
                "screenshot_path": None,
                "request_fingerprint": canonical_fingerprint(request),
            })
            request_path.write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")
            response_path.write_text(json.dumps(response, ensure_ascii=False), encoding="utf-8")
        result = calculate_stability(self.experiment, self.project_root)
        self.assertTrue(result["valid"], result)
        self.assertIsNone(result["platforms"][0]["search_execution_rate"])
        self.assertIsNone(result["platforms"][0]["citation_url_jaccard"])

    def test_stability_metrics_are_descriptive_not_a_geo_score(self) -> None:
        result = calculate_stability(self.experiment, self.project_root)
        self.assertTrue(result["valid"], result)
        platform = result["platforms"][0]
        self.assertEqual(platform["completed_runs"], 3)
        self.assertEqual(platform["search_execution_rate"], 1.0)
        self.assertEqual(platform["unique_answer_rate"], 1.0)
        self.assertEqual(platform["first_entity_agreement"], 0.6667)
        self.assertNotIn("score", platform)
        self.assertIn("not a GEO score", result["interpretation"])

    def test_cli_can_persist_stability_result(self) -> None:
        experiment_path = self.project_root / "experiment.json"
        output_path = self.project_root / "results" / "stability.json"
        experiment_path.write_text(json.dumps(self.experiment, ensure_ascii=False), encoding="utf-8")
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "repeated_experiment.py"),
                str(experiment_path),
                "--project-root",
                str(self.project_root),
                "--output",
                str(output_path),
            ],
            capture_output=True,
            check=False,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        persisted = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertTrue(persisted["valid"])
        self.assertEqual(persisted, json.loads(completed.stdout))


if __name__ == "__main__":
    unittest.main()

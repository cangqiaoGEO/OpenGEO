"""End-to-end tests for query-family aggregation and the concise MVP report"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from mvp_report import build_report  # noqa: E402
from query_family_summary import summarize  # noqa: E402


def load_json(name: str) -> dict:
    """Load one public synthetic example"""

    with (ROOT / "examples" / name).open(encoding="utf-8") as file:
        return json.load(file)


def family_fixture() -> tuple[dict, dict]:
    """Expand the v2 example to two independently addressable variants per family"""

    research = load_json("research_package_standard.json")
    evidence = load_json("evidence_package_measured.json")
    new_queries = []
    id_map: dict[str, str] = {}
    for query in research["query_protocol"]["queries"]:
        variant = copy.deepcopy(query)
        variant["query_id"] = f'{query["query_id"]}-variant-b'
        variant["query"] = f'{query["query"]} 请换一种日常表达回答'
        id_map[query["query_id"]] = variant["query_id"]
        new_queries.append(variant)
    research["query_protocol"]["queries"].extend(new_queries)

    new_observations = []
    for observation in evidence["observations"]:
        variant = copy.deepcopy(observation)
        variant["observation_id"] = f'{observation["observation_id"]}-variant-b'
        variant["query_id"] = id_map[observation["query_id"]]
        if observation["engine"]["name"] == "DeepSeek" and observation["query_id"] == "q-solution":
            variant.update(
                position="absent",
                recommendation=None,
                citations=[],
                sentiment=None,
                coverage={
                    "intro": False,
                    "selling_points": False,
                    "products": False,
                    "pricing": False,
                    "reputation": False,
                    "news": False,
                },
                fact_errors=[],
            )
        new_observations.append(variant)
    evidence["observations"].extend(new_observations)
    return research, evidence


class StructureParser(HTMLParser):
    """Collect rendered tags for security assertions"""

    def __init__(self) -> None:
        super().__init__()
        self.tags: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        self.tags.append(tag)


class QueryFamilyMvpTest(unittest.TestCase):
    """Verify the MVP separates business needs, wording variants, and platforms"""

    def test_complete_portfolio_detects_stability_and_wording_sensitivity(self) -> None:
        research, evidence = family_fixture()
        result = summarize(research, evidence)
        self.assertEqual(result["assessment"]["status"], "complete")
        self.assertEqual(result["assessment"]["coverage_rate"], 100.0)

        category = next(item for item in result["families"] if item["family_id"] == "category_recommendation")
        deepseek_category = next(item for item in category["platforms"] if item["platform"] == "DeepSeek")
        self.assertEqual(deepseek_category["state"], "consistently_absent")

        solution = next(item for item in result["families"] if item["family_id"] == "solution")
        deepseek_solution = next(item for item in solution["platforms"] if item["platform"] == "DeepSeek")
        self.assertEqual(deepseek_solution["state"], "wording_sensitive")

    def test_single_wording_per_family_is_only_partial(self) -> None:
        research = load_json("research_package_standard.json")
        evidence = load_json("evidence_package_measured.json")
        result = summarize(research, evidence)
        self.assertEqual(result["assessment"]["status"], "partial")
        self.assertEqual(result["assessment"]["expected_observations"], 24)
        self.assertEqual(result["assessment"]["coverage_rate"], 50.0)
        self.assertEqual(
            sum(item["gap_type"] == "insufficient_variants" for item in result["evidence_gaps"]),
            4,
        )
        self.assertEqual(result["key_findings"], [])
        self.assertTrue(
            all(
                platform["state"] == "partially_observed"
                for family in result["families"]
                for platform in family["platforms"]
            )
        )

    def test_repeated_runs_are_not_counted_as_wording_variants(self) -> None:
        research = load_json("research_package_standard.json")
        evidence = load_json("evidence_package_measured.json")
        original = next(
            item
            for item in evidence["observations"]
            if item["query_id"] == "q-category-recommendation" and item["engine"]["name"] == "ChatGPT"
        )
        absent = copy.deepcopy(original)
        absent["observation_id"] = "obs-chatgpt-category-repeat-2"
        absent["observed_at"] = "2026-08-20T16:01:30+08:00"
        absent.update(
            position="absent",
            recommendation=None,
            sentiment=None,
            citations=[],
            coverage={
                "intro": False,
                "selling_points": False,
                "products": False,
                "pricing": False,
                "reputation": False,
                "news": False,
            },
            fact_errors=[],
        )
        evidence["observations"].append(absent)

        result = summarize(research, evidence)
        category = next(item for item in result["families"] if item["family_id"] == "category_recommendation")
        platform = next(item for item in category["platforms"] if item["platform"] == "ChatGPT")
        self.assertEqual(platform["observed_variants"], 1)
        self.assertEqual(platform["observed_runs"], 2)
        self.assertEqual(platform["repeat_state"], "unstable")
        self.assertEqual(platform["state"], "partially_observed")
        repeat_finding = next(item for item in result["key_findings"] if item["finding_type"] == "repeat_unstable")
        self.assertIn("2 次重复", repeat_finding["statement"])

    def test_report_leads_with_findings_and_contains_complete_diagnostic_layers(self) -> None:
        research, evidence = family_fixture()
        rendered = build_report(research, evidence)
        self.assertIn("结论先行", rendered)
        self.assertIn("优先动作", rendered)
        self.assertIn("不同问法下的实际表现", rendered)
        self.assertIn("对问法敏感", rendered)
        self.assertIn("研究范围与业务语境", rendered)
        self.assertIn("六维得分", rendered)
        self.assertIn("六维雷达", rendered)
        self.assertIn("引擎对比矩阵", rendered)
        self.assertIn("质量审计", rendered)
        self.assertIn("实验性综合指数", rendered)
        parser = StructureParser()
        parser.feed(rendered)
        self.assertIn("main", parser.tags)
        self.assertNotIn("script", parser.tags)

    def test_report_escapes_untrusted_query_text(self) -> None:
        research, evidence = family_fixture()
        attack = '<script>alert("x")</script>'
        research["query_protocol"]["queries"][0]["query"] = attack
        rendered = build_report(research, evidence)
        self.assertNotIn(attack, rendered)
        self.assertIn("&lt;script&gt;", rendered)

    def test_cli_writes_html_and_machine_summary(self) -> None:
        research, evidence = family_fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            research_path = root / "research.json"
            evidence_path = root / "evidence.json"
            report_path = root / "report.html"
            summary_path = root / "summary.json"
            research_path.write_text(json.dumps(research, ensure_ascii=False), encoding="utf-8")
            evidence_path.write_text(json.dumps(evidence, ensure_ascii=False), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "mvp_report.py"),
                    str(research_path),
                    str(evidence_path),
                    "-o",
                    str(report_path),
                    "--summary-output",
                    str(summary_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue(report_path.exists())
            self.assertEqual(json.loads(summary_path.read_text(encoding="utf-8"))["assessment"]["status"], "complete")


if __name__ == "__main__":
    unittest.main()

"""Security, consistency, and end-to-end tests for the v2 HTML report"""

from __future__ import annotations

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

from geo_report import build_report, validate_inputs  # noqa: E402
from geo_score import compute  # noqa: E402
from quality_audit import audit_quality  # noqa: E402


def load_json(name: str) -> dict:
    """Load one isolated example fixture"""

    with (ROOT / "examples" / name).open(encoding="utf-8") as file:
        return json.load(file)


class StructureParser(HTMLParser):
    """Collect basic structural signals from generated HTML"""

    def __init__(self) -> None:
        super().__init__()
        self.tags: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        self.tags.append(tag)


class GeoReportV2Test(unittest.TestCase):
    """Verify complete rendering, escaping, and upstream consistency checks"""

    def setUp(self) -> None:
        self.research = load_json("research_package_standard.json")
        self.evidence = load_json("evidence_package_measured.json")
        self.score = compute(self.research, self.evidence)
        self.audit = audit_quality(self.research, self.evidence, self.score)
        self.recommendations = load_json("recommendations_measured.json")

    def test_complete_report_contains_all_decision_sections(self) -> None:
        rendered = build_report(self.research, self.evidence, self.score, self.audit, self.recommendations, "experimental_score")
        for heading in (
            "研究范围与业务语境",
            "六维得分",
            "引擎对比矩阵",
            "质量审计",
            "逐条观测与回答级得分",
            "证据缺口",
            "反例与反向证据",
            "证据驱动建议",
            "方法与局限",
        ):
            self.assertIn(heading, rendered)
        parser = StructureParser()
        parser.feed(rendered)
        self.assertIn("main", parser.tags)
        self.assertIn("svg", parser.tags)
        self.assertNotIn("script", parser.tags)
        self.assertIn("experimental M1", rendered)
        self.assertIn("不构成 GEO 行业标准", rendered)

    def test_all_untrusted_text_is_html_escaped(self) -> None:
        attack = '<script>alert("x")</script><img src=x onerror=alert(1)>'
        self.research["scope"]["brand"] = attack
        self.evidence["brand"] = attack
        self.research["query_protocol"]["queries"][0]["query"] = attack
        self.evidence["observations"][0]["raw_response"] = attack
        self.recommendations["recommendations"][0]["action"] = attack
        self.score = compute(self.research, self.evidence)
        self.audit = audit_quality(self.research, self.evidence, self.score)
        rendered = build_report(self.research, self.evidence, self.score, self.audit, self.recommendations, "experimental_score")
        self.assertNotIn(attack, rendered)
        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)
        parser = StructureParser()
        parser.feed(rendered)
        self.assertNotIn("script", parser.tags)
        self.assertNotIn("img", parser.tags)

    def test_report_rejects_stale_score_and_audit(self) -> None:
        self.score["total"] = 99.0
        errors = validate_inputs(self.research, self.evidence, self.score, self.audit, self.recommendations)
        self.assertIn("score result does not match deterministic recomputation", errors)

    def test_insufficient_data_report_has_no_fake_grade_or_recommendations(self) -> None:
        self.evidence["observations"] = []
        self.score = compute(self.research, self.evidence)
        self.audit = audit_quality(self.research, self.evidence, self.score)
        self.recommendations["audit_id"] = self.audit["audit_id"]
        self.recommendations["recommendations"] = []
        self.assertEqual(validate_inputs(self.research, self.evidence, self.score, self.audit, self.recommendations), [])
        rendered = build_report(self.research, self.evidence, self.score, self.audit, self.recommendations)
        self.assertIn("证据不足", rendered)
        self.assertIn("当前报告只交付观测、证据、缺口和待验证问题", rendered)
        self.assertNotIn("等级 A", rendered)

    def test_diagnostic_mode_hides_experimental_total_and_actions(self) -> None:
        rendered = build_report(self.research, self.evidence, self.score, self.audit, self.recommendations)
        self.assertIn("当前模式不发布综合分", rendered)
        self.assertIn("诊断模式", rendered)
        self.assertIn("规划交接边界", rendered)
        self.assertNotIn("证据驱动建议", rendered)

    def test_experimental_mode_discloses_score_status(self) -> None:
        rendered = build_report(
            self.research,
            self.evidence,
            self.score,
            self.audit,
            self.recommendations,
            "experimental_score",
        )
        self.assertIn("实验性综合得分 / 100", rendered)
        self.assertIn("证据驱动建议", rendered)

    def test_cli_generates_self_contained_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            score_path = directory_path / "score.json"
            audit_path = directory_path / "audit.json"
            output_path = directory_path / "report.html"
            score_path.write_text(json.dumps(self.score, ensure_ascii=False), encoding="utf-8")
            audit_path.write_text(json.dumps(self.audit, ensure_ascii=False), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "geo_report.py"),
                    str(ROOT / "examples" / "research_package_standard.json"),
                    str(ROOT / "examples" / "evidence_package_measured.json"),
                    str(score_path),
                    str(audit_path),
                    str(ROOT / "examples" / "recommendations_measured.json"),
                    "-o",
                    str(output_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            rendered = output_path.read_text(encoding="utf-8")
            self.assertIn("<!DOCTYPE html>", rendered)
            self.assertNotIn("<script", rendered.lower())
            self.assertNotIn("src=\"http", rendered.lower())
            self.assertIn("当前模式不发布综合分", rendered)

    def test_cli_uses_diagnostic_package_report_mode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            score_path = directory_path / "score.json"
            audit_path = directory_path / "audit.json"
            output_path = directory_path / "report.html"
            score_path.write_text(json.dumps(self.score, ensure_ascii=False), encoding="utf-8")
            audit_path.write_text(json.dumps(self.audit, ensure_ascii=False), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "geo_report.py"),
                    str(ROOT / "examples" / "research_package_standard.json"),
                    str(ROOT / "examples" / "evidence_package_measured.json"),
                    str(score_path),
                    str(audit_path),
                    "--diagnostic-package",
                    str(ROOT / "examples" / "diagnostic_package_standard.json"),
                    "-o",
                    str(output_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("当前模式不发布综合分", output_path.read_text(encoding="utf-8"))

    def test_experimental_cli_requires_recommendations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            score_path = directory_path / "score.json"
            audit_path = directory_path / "audit.json"
            score_path.write_text(json.dumps(self.score, ensure_ascii=False), encoding="utf-8")
            audit_path.write_text(json.dumps(self.audit, ensure_ascii=False), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "geo_report.py"),
                    str(ROOT / "examples" / "research_package_standard.json"),
                    str(ROOT / "examples" / "evidence_package_measured.json"),
                    str(score_path),
                    str(audit_path),
                    "--report-mode",
                    "experimental_score",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 1)
            self.assertIn("requires recommendations_path", completed.stderr)


if __name__ == "__main__":
    unittest.main()

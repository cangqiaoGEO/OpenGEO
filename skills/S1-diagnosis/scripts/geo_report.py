#!/usr/bin/env python3
"""Generate a safe, self-contained v2 Brand GEO HTML report

Usage:
    python3 geo_report.py <research.json> <evidence.json> <score.json>
        <audit.json> <recommendations.json> [-o report.html]
"""

from __future__ import annotations

import argparse
import html
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from evidence_validate import validate_evidence_package  # noqa: E402
from geo_score import compute  # noqa: E402
from quality_audit import audit_quality  # noqa: E402
from recommendation_validate import validate_recommendations  # noqa: E402
from diagnostic_contracts import REPORT_MODES, validate_diagnostic_package  # noqa: E402


DIMENSION_LABELS = {
    "visibility": "可见度",
    "recommendation": "推荐度",
    "citation_quality": "引用源质量",
    "coverage": "信息覆盖度",
    "sentiment": "情感倾向",
    "foundation": "内容基础",
}
POSITION_LABELS = {"top1": "首位唯一推荐", "top1_tied": "首位并列", "top3": "前 3 提及", "top5": "前 5 提及", "mention": "附带提及", "absent": "未出现"}
RECOMMENDATION_LABELS = {"explicit": "明确推荐", "tied": "并列推荐", "neutral": "客观描述", "negative": "负面/劝阻"}
SENTIMENT_LABELS = {"positive": "正面", "neutral": "中立", "negative": "负面"}
AUDIT_LABELS = {"passed": "通过", "passed_with_warnings": "通过但有警告", "insufficient_data": "证据不足", "failed": "失败"}
ASSESSMENT_LABELS = {"measured": "正式测量", "partially_measured": "部分测量", "insufficient_data": "证据不足"}
CHECK_LABELS = {
    "boundary_completeness": "边界完整性",
    "sample_sufficiency": "样本充分性",
    "source_reliability": "来源可靠性",
    "coverage_completeness": "数据完整性",
    "cross_validation": "交叉验证",
    "counterexample_review": "反例检查",
    "data_freshness": "复核与观测时效性",
    "traceability": "结果可追溯性",
}
PRIORITY_META = {"P0": ("#b42318", "1–2 周"), "P1": ("#b54708", "1–2 月"), "P2": ("#175cd3", "持续")}
GRADE_META = {"S": ("#067647", "优秀"), "A": ("#3f6212", "良好"), "B": ("#b54708", "中等"), "C": ("#b42318", "较弱"), "D": ("#7a271a", "缺失")}

CSS = """
:root{color-scheme:light;--ink:#17202a;--muted:#667085;--line:#e4e7ec;--panel:#fff;--bg:#f5f7fa;--blue:#175cd3;--green:#067647;--amber:#b54708;--red:#b42318}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;line-height:1.58}
.wrap{max-width:1120px;margin:0 auto;padding:28px 18px 56px}.hero{background:linear-gradient(135deg,#102a43,#175cd3);color:#fff;border-radius:18px;padding:30px;margin-bottom:20px}
.eyebrow{font-size:12px;letter-spacing:.08em;text-transform:uppercase;opacity:.76}.hero h1{font-size:29px;margin:6px 0}.hero-grid{display:grid;grid-template-columns:180px 1fr;gap:26px;align-items:center;margin-top:20px}
.big-score{font-size:58px;font-weight:800;line-height:1}.subtle{font-size:13px;opacity:.78}.hero-summary{background:rgba(255,255,255,.12);border-radius:12px;padding:14px 16px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:18px}.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:22px;margin-bottom:18px;box-shadow:0 1px 3px rgba(16,24,40,.04)}
.card h2{font-size:18px;margin:0 0 15px}.card h3{font-size:15px;margin:16px 0 8px}.meta-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.meta{background:#f8fafc;border-radius:10px;padding:11px}.meta b{display:block;font-size:12px;color:var(--muted);margin-bottom:3px}
.badge{display:inline-block;border-radius:999px;padding:3px 9px;font-size:12px;font-weight:700}.pass{background:#ecfdf3;color:var(--green)}.warning{background:#fffaeb;color:var(--amber)}.fail{background:#fef3f2;color:var(--red)}.neutral{background:#eff4ff;color:var(--blue)}
.dim{display:grid;grid-template-columns:108px 1fr 64px;gap:10px;align-items:center;margin:12px 0}.bar{height:11px;background:#eef2f6;border-radius:9px;overflow:hidden}.fill{height:100%;border-radius:9px}.metric-note{grid-column:2/4;color:var(--muted);font-size:11px;margin-top:-7px}
table{width:100%;border-collapse:collapse;font-size:13px}th,td{border-bottom:1px solid var(--line);padding:9px 8px;text-align:left;vertical-align:top}th{background:#f8fafc;color:#475467;white-space:nowrap}.scroll{overflow-x:auto}
.item{border:1px solid var(--line);border-radius:11px;padding:13px;margin:9px 0}.item-title{font-weight:700}.item-meta{font-size:12px;color:var(--muted);margin-top:5px}.raw{white-space:pre-wrap;background:#f8fafc;border-radius:8px;padding:10px;margin-top:8px;font-size:12px;max-height:180px;overflow:auto}
.recommendation{display:grid;grid-template-columns:62px 1fr;gap:13px}.priority{height:52px;border-radius:10px;color:#fff;display:flex;align-items:center;justify-content:center;font-weight:800}.empty{color:var(--muted);font-size:13px}.foot{color:#98a2b3;font-size:12px;text-align:center;margin-top:20px}.svg-wrap{display:flex;justify-content:center}
@media(max-width:760px){.grid2,.hero-grid,.meta-grid{grid-template-columns:1fr}.hero-grid{gap:14px}.dim{grid-template-columns:90px 1fr 54px}.wrap{padding:14px 10px 40px}.card,.hero{padding:17px}}
"""


def esc(value: Any) -> str:
    """Escape all externally sourced values before inserting them into HTML"""

    if value is None:
        return "—"
    return html.escape(str(value), quote=True)


def safe_filename(value: str) -> str:
    """Create a filesystem-safe default report name from an untrusted brand"""

    normalized = re.sub(r"[^\w\u4e00-\u9fff.-]+", "_", value, flags=re.UNICODE).strip("._")
    return normalized or "brand"


def metric_text(metric: dict[str, Any]) -> str:
    """Format one v2 metric with its sample state"""

    score = metric.get("score")
    return "—" if score is None else f"{score:.1f}"


def score_color(score: float | None) -> str:
    """Return a controlled color for one score"""

    if score is None:
        return "#98a2b3"
    if score >= 80:
        return "#067647"
    if score >= 60:
        return "#3f6212"
    if score >= 40:
        return "#b54708"
    return "#b42318"


def radar_svg(dimensions: dict[str, dict[str, Any]]) -> str:
    """Render a fixed-label radar chart only when all six scores are known"""

    if any(dimensions[name]["score"] is None for name in DIMENSION_LABELS):
        return '<div class="empty">部分维度未知，暂不绘制雷达图</div>'
    names = list(DIMENSION_LABELS)
    cx, cy, radius = 190, 170, 118

    def point(index: int, value: float) -> tuple[float, float]:
        angle = -math.pi / 2 + 2 * math.pi * index / len(names)
        scaled = radius * value / 100
        return cx + scaled * math.cos(angle), cy + scaled * math.sin(angle)

    parts = ['<svg viewBox="0 0 380 330" width="100%" style="max-width:430px" role="img" aria-label="六维得分雷达图">']
    for step in (25, 50, 75, 100):
        points = " ".join(f"{point(index, step)[0]:.1f},{point(index, step)[1]:.1f}" for index in range(len(names)))
        parts.append(f'<polygon points="{points}" fill="none" stroke="#d0d5dd" stroke-width="1"/>')
    for index in range(len(names)):
        x, y = point(index, 100)
        parts.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="#d0d5dd"/>')
    values = [dimensions[name]["score"] for name in names]
    points = " ".join(f"{point(index, value)[0]:.1f},{point(index, value)[1]:.1f}" for index, value in enumerate(values))
    parts.append(f'<polygon points="{points}" fill="rgba(23,92,211,.2)" stroke="#175cd3" stroke-width="2.5"/>')
    for index, name in enumerate(names):
        x, y = point(index, 112)
        anchor = "middle" if index in {0, 3} else ("start" if index in {1, 2} else "end")
        marker = "*" if dimensions[name].get("unknown_count", 0) else ""
        parts.append(f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-size="12" fill="#344054">{esc(DIMENSION_LABELS[name])}{marker} {values[index]:.0f}</text>')
    parts.append("</svg>")
    return "".join(parts)


def dimensions_html(result: dict[str, Any]) -> str:
    """Render six dimensions with sample and unknown counts"""

    rows: list[str] = []
    for name, label in DIMENSION_LABELS.items():
        metric = result["dimensions"][name]
        score = metric["score"]
        width = 0 if score is None else max(0, min(100, round(score)))
        total_samples = metric["sample_count"] + metric["unknown_count"]
        known_rate = 0 if not total_samples else metric["sample_count"] / total_samples * 100
        marker = "*" if metric["unknown_count"] else ""
        rows.append(
            f'<div class="dim"><b>{esc(label)}</b><div class="bar"><div class="fill" style="width:{width}%;background:{score_color(score)}"></div></div>'
            f'<strong style="color:{score_color(score)}">{metric_text(metric)}{marker}</strong>'
            f'<div class="metric-note">有效样本 {metric["sample_count"]} · 未知 {metric["unknown_count"]} · 已知覆盖 {known_rate:.0f}% · 权重 {result["weights"][name] * 100:.0f}%</div></div>'
        )
    return "".join(rows)


def engine_matrix_html(result: dict[str, Any]) -> str:
    """Render the complete five-dimension engine matrix"""

    rows: list[str] = []
    for engine_name, engine in result.get("engines", {}).items():
        cells = []
        for dimension in ("visibility", "recommendation", "citation_quality", "coverage", "sentiment"):
            metric = engine[dimension]
            cells.append(f'<td>{metric_text(metric)}<div class="subtle">n={metric["sample_count"]} / ?={metric["unknown_count"]}</div></td>')
        repeat_note = "" if engine.get("run_count", engine["queries"]) == engine["queries"] else f'<div class="subtle">{engine["run_count"]} 次运行</div>'
        rows.append(f'<tr><td><b>{esc(engine_name)}</b></td><td>{engine["observed_queries"]}/{engine["queries"]}{repeat_note}</td>{"".join(cells)}</tr>')
    if not rows:
        return '<tr><td colspan="7" class="empty">没有可展示的引擎观测</td></tr>'
    return "".join(rows)


def scope_html(research: dict[str, Any]) -> str:
    """Render declared research boundaries and minimum business context"""

    scope = research["scope"]
    context = research["domain_context"]
    fields = [
        ("品牌", scope["brand"]),
        ("领域", scope["domain"]),
        ("市场", scope["market"]),
        ("语言", scope["language"]),
        ("截止日期", scope["as_of"]),
        ("调研深度", scope["depth"]),
        ("目标受众", "、".join(scope["audiences"])),
        ("品牌定位", context["brand_positioning"]["value"]),
    ]
    return "".join(f'<div class="meta"><b>{esc(label)}</b>{esc(value)}</div>' for label, value in fields)


def audit_checks_html(audit: dict[str, Any]) -> str:
    """Render all deterministic quality checks"""

    rows = []
    for name, check in audit["checks"].items():
        css_class = "pass" if check["status"] == "pass" else ("warning" if check["status"] == "warning" else "fail")
        findings = "；".join(check["findings"]) or "—"
        rows.append(f'<tr><td>{esc(CHECK_LABELS.get(name, name))}</td><td><span class="badge {css_class}">{esc(check["status"])}</span></td><td>{esc(findings)}</td></tr>')
    return "".join(rows)


def foundation_html(evidence: dict[str, Any], research: dict[str, Any] | None = None) -> str:
    """Render content foundation while preserving unknown values"""

    labels = {"wiki": "百科条目", "official_site_structured": "官网结构化内容", "third_party_count": "可核验外部内容数", "knowledge_graph": "知识实体识别", "content_active": "近期内容活跃"}
    source_map = {
        item["source_id"]: item
        for item in (research or {}).get("domain_context", {}).get("sources", [])
        if isinstance(item, dict) and item.get("source_id")
    }
    rows = []
    for name, item in evidence["foundation"].items():
        value = item["value"]
        if value is None:
            shown = "未知"
        elif value is True:
            shown = "窗口内已发现" if name == "content_active" else "已发现"
        elif value is False:
            shown = "本次探针未发现"
        else:
            shown = str(value)
        evidence_labels: list[str] = []
        for source_id in item["evidence_ids"]:
            source = source_map.get(source_id)
            if not source:
                evidence_labels.append(esc(source_id))
                continue
            title = esc(source.get("title", source_id))
            url = source.get("url")
            label = f'<a href="{esc(url)}" target="_blank" rel="noreferrer">{title}</a>' if url else title
            evidence_labels.append(f'{label}<div class="subtle">{esc(source_id)}</div>')
        rows.append(f'<tr><td>{esc(labels[name])}</td><td>{esc(shown)}</td><td>{"<br>".join(evidence_labels) or "—"}</td></tr>')
    return "".join(rows)


def observations_html(research: dict[str, Any], evidence: dict[str, Any], result: dict[str, Any]) -> str:
    """Join protocol, raw evidence, and answer-level scores for traceability"""

    query_by_id = {item["query_id"]: item for item in research["query_protocol"]["queries"]}
    score_by_id = {item["observation_id"]: item for item in result["observation_scores"]}
    blocks: list[str] = []
    for observation in evidence["observations"]:
        query = query_by_id[observation["query_id"]]
        score = score_by_id[observation["observation_id"]]
        metric_summary = " · ".join(f'{DIMENSION_LABELS[name]} {"—" if value is None else f"{value:.1f}"}' for name, value in score["scores"].items())
        raw = observation["raw_response"] if observation["raw_response"] is not None else "未取得回答"
        citations = observation["citations"]
        citation_state = "未采集" if citations is None else f"{len(citations)} 条"
        blocks.append(
            f'<div class="item"><div class="item-title">{esc(observation["engine"]["name"])} · {esc(query["query"])}</div>'
            f'<div class="item-meta">{esc(observation["observation_id"])} · {esc(POSITION_LABELS.get(observation["position"], observation["position"]))} · 引用 {esc(citation_state)}</div>'
            f'<div class="item-meta">{esc(metric_summary)}</div><div class="raw">{esc(raw)}</div></div>'
        )
    return "".join(blocks) or '<div class="empty">没有观测数据</div>'


def gaps_html(audit: dict[str, Any]) -> str:
    """Render evidence gaps and next validation actions"""

    blocks = []
    for gap in audit["gaps"]:
        blocks.append(f'<div class="item"><div class="item-title">{esc(gap["description"])}</div><div>{esc(gap["impact"])}</div><div class="item-meta">下一步：{esc(gap["next_action"])}</div></div>')
    return "".join(blocks) or '<div class="empty">没有记录到证据缺口</div>'


def counterevidence_html(audit: dict[str, Any]) -> str:
    """Render counterexamples separately from positive findings"""

    blocks = []
    for item in audit["counterevidence"]:
        blocks.append(f'<div class="item"><div class="item-title">{esc(item["description"])}</div><div>{esc(item["implication"])}</div><div class="item-meta">观测：{esc("、".join(item["observation_ids"]) or "—")}</div></div>')
    return "".join(blocks) or '<div class="empty">未记录反例，需要人工确认是否完成反例检查</div>'


def recommendations_html(package: dict[str, Any]) -> str:
    """Render evidence-driven recommendations with fact and hypothesis separated"""

    blocks = []
    for item in package["recommendations"]:
        color, timeline = PRIORITY_META[item["priority"]]
        refs = [*item["source_ids"], *item["observation_ids"]]
        blocks.append(
            f'<div class="item recommendation"><div class="priority" style="background:{color}">{esc(item["priority"])}</div><div>'
            f'<div class="item-title">{esc(item["action"])}</div><div class="item-meta">{esc(DIMENSION_LABELS[item["dimension"]])} · {esc(item["business_context"])} · {esc(timeline)}</div>'
            f'<h3>观察事实</h3><div>{esc(item["finding"])}</div><h3>原因假设</h3><div>{esc(item["hypothesis"])}</div>'
            f'<h3>预期与验证</h3><div>{esc(item["expected_effect"])}</div><div class="item-meta">衡量：{esc(item["measure"])}</div>'
            f'<div class="item-meta">证据：{esc("、".join(refs))} · 置信度 {esc(item["confidence"])}</div></div></div>'
        )
    return "".join(blocks) or '<div class="empty">没有可交付的改进建议</div>'


def build_report(
    research: dict[str, Any],
    evidence: dict[str, Any],
    result: dict[str, Any],
    audit: dict[str, Any],
    recommendations: dict[str, Any] | None,
    report_mode: str = "diagnostic",
) -> str:
    """Build one complete escaped report under an explicit R1 delivery mode"""

    if report_mode not in REPORT_MODES:
        raise ValueError(f"unsupported report mode {report_mode!r}")
    brand = research["scope"]["brand"]
    total = result["total"]
    grade = result["grade"]
    assessment = result["assessment"]
    publish_experimental_score = report_mode == "experimental_score"
    if not publish_experimental_score:
        score_display = "—"
        grade_display = "诊断模式" if report_mode == "diagnostic" else "探索模式"
        grade_color = "#667085"
        score_caption = "当前模式不发布综合分"
    elif total is None:
        score_display = "—"
        grade_display = ASSESSMENT_LABELS[assessment["status"]]
        grade_color = "#667085"
        score_caption = "实验性综合得分 / 100"
    else:
        score_display = f"{total:.1f}"
        grade_color, grade_short = GRADE_META[grade]
        grade_display = f"{grade} · {grade_short}"
        score_caption = "实验性综合得分 / 100"
    if publish_experimental_score:
        if recommendations is None:
            raise ValueError("experimental_score mode requires a validated recommendations package")
        recommendation_section = f'<section class="card"><h2>十、证据驱动建议</h2>{recommendations_html(recommendations)}</section>'
    else:
        recommendation_section = (
            '<section class="card"><h2>十、规划交接边界</h2>'
            '<div class="empty">当前报告只交付观测、证据、缺口和待验证问题，不发布行动方案；'
            '改进路径由下游规划角色结合诊断结果确定</div></section>'
        )
    limitations = assessment["limitations"] or ["无样本门槛限制"]
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{esc(brand)} GEO 诊断报告</title><style>{CSS}</style></head><body><main class="wrap">
<section class="hero"><div class="eyebrow">Brand GEO Audit · v2</div><h1>{esc(brand)} GEO 诊断报告</h1>
	<div class="hero-grid"><div><div class="big-score">{score_display}</div><div class="subtle">{esc(score_caption)}</div><div style="margin-top:9px"><span class="badge" style="background:{grade_color};color:#fff">{esc(grade_display)}</span></div></div>
<div class="hero-summary">样本状态：{esc(ASSESSMENT_LABELS[assessment["status"]])}<br>质量审计：{esc(AUDIT_LABELS[audit["status"]])} · 置信度 {esc(audit["confidence"])}<br>有效观测 {assessment["observed_count"]}/{assessment["expected_observations"]} · 正式引擎 {assessment["measured_engines"]}/{assessment["required_engines"]}</div></div></section>
<section class="card"><h2>一、研究范围与业务语境</h2><div class="meta-grid">{scope_html(research)}</div></section>
<section class="grid2"><div class="card"><h2>二、六维得分（实验性量尺）</h2>{dimensions_html(result)}</div><div class="card"><h2>三、六维雷达（实验性量尺）</h2><div class="svg-wrap">{radar_svg(result["dimensions"])}</div></div></section>
<section class="card"><h2>四、引擎对比矩阵</h2><div class="scroll"><table><tr><th>引擎</th><th>观测</th><th>可见度</th><th>推荐度</th><th>引用质量</th><th>覆盖度</th><th>情感</th></tr>{engine_matrix_html(result)}</table></div></section>
<section class="grid2"><div class="card"><h2>五、内容基础</h2><table><tr><th>检查项</th><th>状态</th><th>证据</th></tr>{foundation_html(evidence, research)}</table></div>
<div class="card"><h2>六、质量审计</h2><div class="scroll"><table><tr><th>检查</th><th>状态</th><th>发现</th></tr>{audit_checks_html(audit)}</table></div></div></section>
<section class="card"><h2>七、逐条观测与回答级得分</h2>{observations_html(research, evidence, result)}</section>
<section class="grid2"><div class="card"><h2>八、证据缺口</h2>{gaps_html(audit)}</div><div class="card"><h2>九、反例与反向证据</h2>{counterevidence_html(audit)}</div></section>
		{recommendation_section}
		<section class="card"><h2>十一、方法与局限</h2><div class="item"><div class="item-title">样本局限</div><div>{esc("；".join(limitations))}</div></div>
		<div class="item"><div class="item-title">报告模式</div><div>{esc(report_mode)}；只有 experimental_score 模式允许展示当前实验性总分和等级</div></div>
	<div class="item"><div class="item-title">方法学状态</div><div>当前 v2 为 experimental M1 工程测量框架；权重、阈值与等级尚未完成多行业校准和外部验证，不构成 GEO 行业标准</div></div>
	<div class="item"><div class="item-title">证据边界</div><div>Web 内容生态只用于内容基础和引用潜力，不等同于真实 AI 引擎表现</div></div>
<div class="item"><div class="item-title">复查原则</div><div>使用相同查询协议、引擎集合、市场、语言和采集条件进行复查</div></div></section>
<div class="foot">审计日期 {esc(audit["audit_date"])} · 协议 {esc(result["protocol_id"])} · 本报告仅供诊断参考，不构成商业决策依据</div>
</main></body></html>"""


def validate_inputs(
    research: dict[str, Any],
    evidence: dict[str, Any],
    result: dict[str, Any],
    audit: dict[str, Any],
    recommendations: dict[str, Any] | None,
) -> list[str]:
    """Reject stale or inconsistent upstream artifacts before rendering"""

    errors: list[str] = []
    evidence_validation = validate_evidence_package(research, evidence)
    if not evidence_validation["valid"]:
        errors.append("research or evidence validation failed")
    else:
        if compute(research, evidence, evidence_validation) != result:
            errors.append("score result does not match deterministic recomputation")
        if audit_quality(research, evidence, result) != audit:
            errors.append("quality audit does not match deterministic recomputation")
    if recommendations is not None:
        recommendation_validation = validate_recommendations(research, evidence, result, audit, recommendations)
        if not recommendation_validation["valid"]:
            errors.extend(item["message"] for item in recommendation_validation["errors"])
    return errors


def _load(path: str) -> Any:
    """Load UTF-8 JSON"""

    with Path(path).open(encoding="utf-8") as file:
        return json.load(file)


def main() -> int:
    """Validate all artifacts and write one self-contained HTML report"""

    parser = argparse.ArgumentParser(description="Generate Brand GEO v2 HTML report")
    parser.add_argument("research_path")
    parser.add_argument("evidence_path")
    parser.add_argument("score_path")
    parser.add_argument("audit_path")
    parser.add_argument("recommendations_path", nargs="?")
    parser.add_argument("-o", "--output")
    parser.add_argument("--report-mode", choices=sorted(REPORT_MODES))
    parser.add_argument("--diagnostic-package", help="optional R1 diagnostic package whose run controls report mode")
    args = parser.parse_args()
    try:
        research, evidence, result, audit = (
            _load(args.research_path),
            _load(args.evidence_path),
            _load(args.score_path),
            _load(args.audit_path),
        )
        recommendations = _load(args.recommendations_path) if args.recommendations_path else None
        errors = validate_inputs(research, evidence, result, audit, recommendations)
        report_mode = args.report_mode or "diagnostic"
        if args.diagnostic_package:
            diagnostic_package = _load(args.diagnostic_package)
            diagnostic_validation = validate_diagnostic_package(research, diagnostic_package)
            if not diagnostic_validation["valid"]:
                errors.append("diagnostic package validation failed")
            package_mode = diagnostic_package.get("diagnostic_run", {}).get("report_mode")
            if args.report_mode and args.report_mode != package_mode:
                errors.append("explicit report mode conflicts with diagnostic run")
            report_mode = package_mode or report_mode
        if report_mode == "experimental_score" and recommendations is None:
            errors.append("experimental_score mode requires recommendations_path")
        if errors:
            print("错误：" + "；".join(errors), file=sys.stderr)
            return 1
        output = Path(args.output) if args.output else Path(f"{safe_filename(research['scope']['brand'])}_geo_audit_report.html")
        output.write_text(build_report(research, evidence, result, audit, recommendations, report_mode), encoding="utf-8")
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        print(f"错误：{error}", file=sys.stderr)
        return 2
    print(f"报告已生成: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

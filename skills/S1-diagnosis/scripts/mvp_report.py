#!/usr/bin/env python3
"""Generate a concise, self-contained customer report for the Brand GEO MVP"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from geo_report import (  # noqa: E402
    ASSESSMENT_LABELS,
    AUDIT_LABELS,
    CSS as DIAGNOSTIC_CSS,
    audit_checks_html,
    counterevidence_html,
    dimensions_html,
    engine_matrix_html,
    foundation_html,
    gaps_html,
    observations_html,
    radar_svg,
    scope_html,
)
from geo_score import compute  # noqa: E402
from quality_audit import audit_quality  # noqa: E402
from query_family_summary import summarize  # noqa: E402


STATUS_LABELS = {"complete": "完整观测", "partial": "部分观测", "insufficient_data": "证据不足"}
STATUS_CLASSES = {"complete": "good", "partial": "warn", "insufficient_data": "bad"}
STATE_CLASSES = {
    "consistently_visible": "good",
    "consistently_absent": "bad",
    "wording_sensitive": "warn",
    "partially_observed": "muted",
    "unobserved": "muted",
}

CSS = DIAGNOSTIC_CSS + """
.good{background:#ecfdf3;color:var(--green)}.warn{background:#fffaeb;color:var(--amber)}.bad{background:#fef3f2;color:var(--red)}.muted{background:#f2f4f7;color:var(--muted)}
.finding{border-left:4px solid var(--line);padding:9px 12px;margin:9px 0;background:#f8fafc;border-radius:0 9px 9px 0}.finding.good{border-color:var(--green)}.finding.warn{border-color:var(--amber)}.finding.bad{border-color:var(--red)}
.query{border:1px solid var(--line);border-radius:9px;padding:10px;margin:7px 0}.query b{display:block;font-size:12px;color:var(--muted);margin-bottom:3px}.note{color:var(--muted);font-size:13px}
.summary-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:14px}.summary-stat{background:#f8fafc;border:1px solid var(--line);border-radius:10px;padding:12px}.summary-stat b{display:block;font-size:22px}.summary-stat span{font-size:12px;color:var(--muted)}
details summary{cursor:pointer;font-weight:700;padding:4px 0}@media(max-width:760px){.summary-grid{grid-template-columns:1fr}}
"""


def esc(value: Any) -> str:
    """Escape untrusted text before HTML interpolation"""

    return html.escape("—" if value is None else str(value), quote=True)


def _finding_class(finding_type: str) -> str:
    """Map deterministic findings to a restrained visual priority"""

    if finding_type == "consistently_visible":
        return "good"
    if finding_type in {"consistently_absent", "major_fact_error"}:
        return "bad"
    return "warn"


def _matrix_rows(summary: dict[str, Any]) -> str:
    """Render platform-family cells without averaging platforms together"""

    rows: list[str] = []
    for family in summary["families"]:
        for index, platform in enumerate(family["platforms"]):
            family_cell = f'<td rowspan="{len(family["platforms"])}"><b>{esc(family["label"])}</b><div class="note">{family["variant_count"]} 种问法</div></td>' if index == 0 else ""
            rate = "—" if platform["presence_rate"] is None else f'{platform["presence_rate"]:.0f}%'
            top1_rate = "—" if platform.get("top1_rate") is None else f'{platform["top1_rate"]:.0f}%'
            rows.append(
                f'<tr>{family_cell}<td>{esc(platform["platform"])}</td><td><span class="badge {STATE_CLASSES[platform["state"]]}">{esc(platform["state_label"])}</span></td>'
                f'<td>{esc(rate)}</td><td>{esc(top1_rate)}</td><td>{platform["observed_variants"]}/{platform["expected_variants"]}</td>'
                f'<td>{platform.get("observed_runs", platform["observed_variants"])} 次 · {esc(platform.get("repeat_state_label", "未做重复观测"))}</td>'
                f'<td>{"重大事实错误 " + str(platform["major_fact_error_count"]) + " 次" if platform.get("major_fact_error_count") else ("负向判断 " + str(platform["negative_recommendation_count"]) + " 次" if platform.get("negative_recommendation_count") else "未标出重大错误")}</td></tr>'
            )
    return "".join(rows) or '<tr><td colspan="8" class="empty">没有查询族观测</td></tr>'


def _findings(summary: dict[str, Any]) -> str:
    """Render only the most decision-relevant deterministic findings"""

    priority = {"major_fact_error": 0, "consistently_absent": 1, "negative_recommendation": 2, "repeat_unstable": 3, "wording_sensitive": 4, "consistently_visible": 5}
    findings = sorted(summary["key_findings"], key=lambda item: priority.get(item["finding_type"], 9))[:6]
    if not findings:
        return '<div class="empty">当前证据不足以形成跨问法结论</div>'
    return "".join(
        f'<div class="finding {_finding_class(item["finding_type"])}">{esc(item["statement"])}</div>'
        for item in findings
    )


def _gaps(summary: dict[str, Any]) -> str:
    """Render a compact deduplicated gap list"""

    seen: set[str] = set()
    rows: list[str] = []
    for gap in summary["evidence_gaps"]:
        message = gap["message"]
        if message not in seen:
            seen.add(message)
            rows.append(f"<li>{esc(message)}</li>")
    return "<ul>" + "".join(rows[:8]) + "</ul>" if rows else '<div class="empty">没有阻塞本次解释的采集缺口</div>'


def _actions(summary: dict[str, Any]) -> str:
    """Derive a short action list from observed risks without inventing a score"""

    findings = summary["key_findings"]
    actions: list[str] = []
    if any(item["finding_type"] == "major_fact_error" for item in findings):
        actions.append("优先统一品牌名、门店名、经营主体、地址和业务边界的公开表述，降低近似名称导致的实体混淆")
    if any(item["finding_type"] == "consistently_absent" for item in findings):
        actions.append("补齐用户按品类或需求搜索时可检索的本地场景内容，并用可核验来源说明门店能力与适用人群")
    if any(item["finding_type"] in {"wording_sensitive", "repeat_unstable"} for item in findings):
        actions.append("围绕同一需求覆盖不同自然问法，完成内容调整后用冻结查询集重复观测，确认结果是否真正改善")
    if not actions:
        actions.append("保持当前可见场景，并按固定查询集定期复测，监控平台回答和引用来源变化")
    return "<ol>" + "".join(f"<li>{esc(item)}</li>" for item in actions[:3]) + "</ol>"


def _query_appendix(summary: dict[str, Any]) -> str:
    """Keep exact queries available for audit without crowding the conclusion"""

    sections: list[str] = []
    for family in summary["families"]:
        variants = "".join(
            f'<div class="query"><b>{esc(item["query_id"])}</b>{esc(item["query"])}</div>'
            for item in family["variants"]
        )
        sections.append(f'<h3>{esc(family["label"])}</h3>{variants}')
    return "".join(sections)


def _repeat_design_note(summary: dict[str, Any]) -> str:
    """Describe repeated observations from actual data instead of one case name"""

    repeated: list[str] = []
    for family in summary["families"]:
        for platform in family["platforms"]:
            runs = platform.get("observed_runs", platform["observed_variants"])
            variants = platform["observed_variants"]
            if runs > variants:
                repeated.append(f'{platform["platform"]}“{family["label"]}”共 {runs} 次运行、覆盖 {variants} 种问法')
    if not repeated:
        return "本轮没有同一问法的重复运行，稳定性仅按不同问法观察"
    return "；".join(repeated) + "；正式分项先在同一查询内平均，再按查询等权汇总"


def build_report(
    research: dict[str, Any],
    evidence: dict[str, Any],
    summary: dict[str, Any] | None = None,
    score_result: dict[str, Any] | None = None,
    audit: dict[str, Any] | None = None,
) -> str:
    """Build a layered final MVP report from one validated evidence package"""

    summary = summary or summarize(research, evidence)
    score_result = score_result or compute(research, evidence)
    audit = audit or audit_quality(research, evidence, score_result)
    family_assessment = summary["assessment"]
    score_assessment = score_result["assessment"]
    family_cells = [platform for family in summary["families"] for platform in family["platforms"]]
    strength_count = sum(item["state"] == "consistently_visible" for item in family_cells)
    risk_count = sum(
        item["state"] in {"consistently_absent", "wording_sensitive"}
        or item.get("repeat_state") == "unstable"
        or item.get("major_fact_error_count", 0) > 0
        or item.get("negative_recommendation_count", 0) > 0
        for item in family_cells
    )
    scope = research["scope"]
    total = score_result["total"]
    has_unknown_samples = any(metric.get("unknown_count", 0) for metric in score_result["dimensions"].values())
    score_display = "—" if total is None else f'{total:.1f}{"*" if has_unknown_samples else ""}'
    score_caption = "实验性综合指数暂不可计算" if total is None else ("实验性综合指数 / 100 · 含未知样本" if has_unknown_samples else "实验性综合指数 / 100")
    score_state = ASSESSMENT_LABELS[score_assessment["status"]]
    audit_state = f'{AUDIT_LABELS[audit["status"]]} · 置信度 {audit["confidence"]}'
    query_count = len(research["query_protocol"]["queries"])
    engine_count = len({engine for query in research["query_protocol"]["queries"] for engine in query["engines"]})
    run_count = len(evidence["observations"])
    limitations = score_assessment["limitations"] or ["当前冻结协议下没有缺失观测"]
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(summary["brand"])} GEO 诊断报告</title><style>{CSS}</style></head><body><main class="wrap">
<section class="hero"><div class="eyebrow">BRAND GEO AUDIT · MVP · M1</div><h1>{esc(summary["brand"])} GEO 诊断报告</h1>
<div class="hero-grid"><div><div class="big-score">{esc(score_display)}</div><div class="subtle">{esc(score_caption)}</div><div style="margin-top:9px"><span class="badge" style="background:#667085;color:#fff">{esc(score_state)}</span></div></div>
<div class="hero-summary">观测覆盖：{family_assessment["observed_count"]}/{family_assessment["expected_observations"]}（{family_assessment["coverage_rate"]:.0f}%）<br>质量审计：{esc(audit_state)}<br>{esc(scope["market"])} · {esc(scope["domain"])} · 截止 {esc(scope["as_of"])}</div></div></section>
<section class="card"><h2>一、结论先行与优先动作</h2>{_findings(summary)}<h3>优先动作</h3>{_actions(summary)}<p class="note">结论来自冻结查询集的消费者 App 实测；行动项是待验证假设，不是效果承诺</p></section>
<section class="card"><h2>二、研究范围与业务语境</h2><div class="meta-grid">{scope_html(research)}</div></section>
<section class="card"><h2>三、测量设计</h2><div class="summary-grid"><div class="summary-stat"><b>{query_count}</b><span>四查询族、每族两种问法</span></div><div class="summary-stat"><b>{engine_count}</b><span>国内消费者 AI 平台</span></div><div class="summary-stat"><b>{run_count}</b><span>回答级运行，含重复稳定性样本</span></div></div><p class="note">渠道为官方消费者 App 浏览器实测；API 结果不混入本报告。{esc(_repeat_design_note(summary))}</p></section>
<section class="grid2"><div class="card"><h2>四、六维得分（实验性量尺）</h2>{dimensions_html(score_result)}<p class="note">* 表示该维度仍有未知样本；分项可用于发现问题，但当前权重和阈值尚未完成多行业校准</p></div><div class="card"><h2>五、六维雷达</h2><div class="svg-wrap">{radar_svg(score_result["dimensions"])}</div><p class="note">* 表示该维度含未知样本；任一维度完全未知时不绘制雷达，避免用零分伪装缺失数据</p></div></section>
<section class="card"><h2>六、引擎对比矩阵</h2><div class="scroll"><table><thead><tr><th>引擎</th><th>查询观测</th><th>可见度</th><th>推荐度</th><th>引用质量</th><th>覆盖度</th><th>情感</th></tr></thead><tbody>{engine_matrix_html(score_result)}</tbody></table></div></section>
<section class="card"><h2>七、不同问法下的实际表现</h2><h3>查询族、问法敏感性与重复稳定性</h3><div class="scroll"><table><thead><tr><th>用户需求</th><th>平台</th><th>问法覆盖状态</th><th>品牌出现率</th><th>首位率</th><th>已观测/计划问法</th><th>同问法重复结果</th><th>结果质量</th></tr></thead><tbody>{_matrix_rows(summary)}</tbody></table></div><p class="note">“稳定”只表示本次查询、时间和平台条件下结果一致，不代表所有用户问法都会得到相同回答</p></section>
<section class="grid2"><div class="card"><h2>八、内容基础</h2><table><thead><tr><th>检查项</th><th>状态</th><th>证据</th></tr></thead><tbody>{foundation_html(evidence, research)}</tbody></table><p class="note">“本次探针未发现”只描述冻结检索范围和时间点，不等于客观不存在；近期活跃采用十二个月窗口</p></div><div class="card"><h2>九、质量审计</h2><div class="scroll"><table><thead><tr><th>检查</th><th>状态</th><th>发现</th></tr></thead><tbody>{audit_checks_html(audit)}</tbody></table></div></div></section>
<section class="grid2"><div class="card"><h2>十、证据缺口</h2>{gaps_html(audit)}{_gaps(summary)}</div><div class="card"><h2>十一、反例与反向证据</h2>{counterevidence_html(audit)}</div></section>
<section class="card"><h2>十二、逐条观测与回答级得分</h2><details><summary>展开 {run_count} 条回答级证据</summary>{observations_html(research, evidence, score_result)}</details></section>
<section class="card"><h2>十三、查询协议与方法局限</h2><details><summary>查看冻结测试问题</summary>{_query_appendix(summary)}</details><h3>方法学状态</h3><p>当前为待验证的 M1 工程测量框架，可发布实验性分项，不构成 GEO 行业标准</p><h3>当前限制</h3><p>{esc("；".join(limitations))}</p><h3>证据边界</h3><p>真实 AI 回答用于衡量生成式可见性；Web 内容基础只衡量可检索与可引用潜力，两者不互相替代</p><div class="note">协议 {esc(summary["protocol_id"])} · 方法状态 candidate_mvp · 报告可由研究包、证据包、评分器和质量审计确定性复算</div></section>
<div class="foot">审计日期 {esc(scope["as_of"])} · 本报告用于诊断和后续验证，不构成商业效果承诺</div>
</main></body></html>"""


def _load_json(path: str) -> Any:
    """Load one UTF-8 JSON file"""

    with Path(path).open(encoding="utf-8") as file:
        return json.load(file)


def main() -> int:
    """Generate both machine-readable summary and customer-facing HTML"""

    parser = argparse.ArgumentParser(description="Generate the Brand GEO query-family MVP report")
    parser.add_argument("research_path")
    parser.add_argument("evidence_path")
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("--summary-output")
    parser.add_argument("--score-output")
    parser.add_argument("--audit-output")
    args = parser.parse_args()
    try:
        research = _load_json(args.research_path)
        evidence = _load_json(args.evidence_path)
        summary = summarize(research, evidence)
        score_result = compute(research, evidence)
        audit = audit_quality(research, evidence, score_result)
        Path(args.output).write_text(build_report(research, evidence, summary, score_result, audit), encoding="utf-8")
        if args.summary_output:
            Path(args.summary_output).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if args.score_output:
            Path(args.score_output).write_text(json.dumps(score_result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if args.audit_output:
            Path(args.audit_output).write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"MVP 报告已生成: {args.output}")
        return 0
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"MVP 报告生成失败: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

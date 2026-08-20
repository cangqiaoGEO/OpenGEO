#!/usr/bin/env python3
"""
GEO 品牌诊断报告生成器

基于 geo_score.py 的评分结果与原始查询数据，生成单文件 HTML 诊断报告
（浅色主题、中文、内联 CSS/SVG，无外部依赖）。

用法：
    python3 geo_report.py <data.json> <result.json> [-o report.html]

- <data.json>   : 原始查询明细（结构同 geo_score.py 的输入，可含 "suggestions" 列表）
- <result.json> : geo_score.py 的输出
- 默认输出 <brand>_geo_audit_report.html 到当前目录

suggestions 结构（可选）：
{
  "suggestions": [
    {"priority": "P0", "dimension": "visibility", "action": "…",
     "effect": "…", "measure": "…"}
  ]
}
"""

import json
import math
import sys

DIMENSION_LABELS = {
    "visibility": "可见度",
    "recommendation": "推荐度",
    "citation_quality": "引用源质量",
    "coverage": "信息覆盖度",
    "sentiment": "情感倾向",
    "foundation": "内容基础",
}

POSITION_LABELS = {
    "top1": "首位唯一推荐",
    "top1_tied": "首位并列",
    "top3": "前3提及",
    "top5": "前5提及",
    "mention": "附带提及",
    "absent": "未出现",
}

RECOMMENDATION_LABELS = {
    "explicit": "明确推荐",
    "tied": "并列推荐",
    "neutral": "客观描述",
    "negative": "负面/劝阻",
}

SENTIMENT_LABELS = {
    "positive": "正面",
    "neutral": "中立",
    "negative": "负面",
}

CITATION_LABELS = {
    "official": "官网/官方",
    "wiki": "百科/知识图谱",
    "authoritative": "权威媒体/报告",
    "review": "第三方评测/KOL",
    "social": "社媒/论坛",
    "low_quality": "低质聚合站",
}

PRIORITY_META = {
    "P0": ("#b3261e", "1-2 周内"),
    "P1": ("#e8710a", "1-2 个月内"),
    "P2": ("#0b57d0", "持续进行"),
}

GRADE_META = {
    "S": ("#0b8043", "优秀，GEO 领先者"),
    "A": ("#6f8f00", "良好，有竞争力"),
    "B": ("#e8710a", "中等，需要改进"),
    "C": ("#c5221f", "较弱，明显落后"),
    "D": ("#7f1d1d", "缺失，几乎不可见"),
}

CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;background:#f4f6f9;color:#1f2937;line-height:1.6;padding:32px 16px}
.wrap{max-width:960px;margin:0 auto}
.header{background:linear-gradient(135deg,#0f2a43,#1d4ed8);color:#fff;border-radius:16px;padding:32px;margin-bottom:24px}
.header h1{font-size:28px;margin-bottom:6px}
.header .sub{opacity:.85;font-size:14px}
.score-row{display:flex;align-items:center;gap:24px;margin-top:20px;flex-wrap:wrap}
.big-score{font-size:56px;font-weight:800;line-height:1}
.grade-badge{display:inline-block;padding:8px 18px;border-radius:999px;font-weight:700;font-size:16px;color:#fff}
.summary{margin-top:16px;font-size:15px;background:rgba(255,255,255,.12);border-radius:10px;padding:12px 16px}
.card{background:#fff;border-radius:14px;padding:24px;margin-bottom:20px;box-shadow:0 1px 4px rgba(16,24,40,.08)}
.card h2{font-size:18px;margin-bottom:16px;color:#0f2a43;border-left:4px solid #1d4ed8;padding-left:10px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:20px}
@media(max-width:720px){.grid2{grid-template-columns:1fr}}
.dim{display:flex;align-items:center;gap:12px;margin-bottom:14px}
.dim-name{width:92px;font-size:14px;font-weight:600;flex-shrink:0}
.dim-bar{flex:1;height:12px;background:#eef1f5;border-radius:6px;overflow:hidden}
.dim-fill{height:100%;border-radius:6px}
.dim-score{width:52px;text-align:right;font-weight:700;font-size:14px}
.dim-note{font-size:12px;color:#6b7280;margin:-8px 0 14px 104px}
table{width:100%;border-collapse:collapse;font-size:13.5px}
th,td{padding:9px 10px;text-align:left;border-bottom:1px solid #eef1f5}
th{background:#f8fafc;color:#475569;font-weight:600}
tr:hover td{background:#f8fafc}
.tag{display:inline-block;padding:2px 10px;border-radius:999px;font-size:12px;font-weight:600;color:#fff}
.pill{display:inline-block;padding:2px 10px;border-radius:999px;font-size:12px;background:#eef2ff;color:#3730a3;margin:2px}
.sug{border:1px solid #eef1f5;border-radius:12px;padding:16px;margin-bottom:12px;display:flex;gap:14px}
.sug-prio{flex-shrink:0;width:52px;height:52px;border-radius:12px;color:#fff;display:flex;flex-direction:column;align-items:center;justify-content:center;font-weight:800;font-size:16px}
.sug-prio span{font-size:9px;font-weight:500;opacity:.9}
.sug-body{flex:1}
.sug-body .act{font-weight:600;font-size:14.5px;margin-bottom:4px}
.sug-body .meta{font-size:12.5px;color:#6b7280}
.sug-body .meta b{color:#374151}
.foot{font-size:12px;color:#9ca3af;text-align:center;margin-top:8px}
.legend{font-size:12px;color:#6b7280;margin-top:8px}
.svg-wrap{display:flex;justify-content:center}
"""


def radar_svg(scores):
    """生成六维雷达图 SVG，返回 SVG 字符串。"""
    dims = list(DIMENSION_LABELS.keys())
    n = len(dims)
    cx, cy, R = 190, 170, 120
    steps = [0, 25, 50, 75, 100]

    def point(i, value):
        angle = -math.pi / 2 + 2 * math.pi * i / n
        r = R * value / 100
        return (cx + r * math.cos(angle), cy + r * math.sin(angle))

    def text_anchor(angle):
        a = (angle + math.pi / 2) % (2 * math.pi)
        if a < math.pi / 6 or a > 11 * math.pi / 6:
            return "middle"
        if a < math.pi:
            return "start"
        return "end"

    parts = []
    parts.append('<svg viewBox="0 0 380 330" width="100%" style="max-width:420px" xmlns="http://www.w3.org/2000/svg">')
    for s in steps:
        pts = " ".join(f"{point(i, s)[0]:.1f},{point(i, s)[1]:.1f}" for i in range(n))
        parts.append(f'<polygon points="{pts}" fill="none" stroke="#e2e8f0" stroke-width="1"/>')
    for i, dim in enumerate(dims):
        x1, y1 = point(i, 100)
        parts.append(f'<line x1="{cx}" y1="{cy}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="#e2e8f0" stroke-width="1"/>')
    for s in steps[1:]:
        for i in range(n):
            x, y = point(i, s)
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.8" fill="#cbd5e1"/>')
    pts = " ".join(f"{point(i, scores[dim])[0]:.1f},{point(i, scores[dim])[1]:.1f}" for i, dim in enumerate(dims))
    parts.append(f'<polygon points="{pts}" fill="rgba(29,78,216,.25)" stroke="#1d4ed8" stroke-width="2.5"/>')
    for i, dim in enumerate(dims):
        x, y = point(i, scores[dim])
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#1d4ed8"/>')
    for i, dim in enumerate(dims):
        x, y = point(i, 108)
        angle = -math.pi / 2 + 2 * math.pi * i / n
        anchor = text_anchor(angle)
        label = f"{DIMENSION_LABELS[dim]} {scores[dim]:.0f}"
        dy = 4 if i != 0 else -6
        parts.append(
            f'<text x="{x:.1f}" y="{y:.1f}" dy="{dy}" text-anchor="{anchor}" '
            f'font-size="12.5" fill="#374151" font-weight="600">{label}</text>'
        )
    parts.append('</svg>')
    return "".join(parts)


def dim_bar_html(scores, weights):
    rows = []
    for dim in DIMENSION_LABELS:
        score = scores[dim]
        pct = int(round(score))
        color = "#0b8043" if score >= 80 else ("#6f8f00" if score >= 60 else ("#e8710a" if score >= 40 else "#c5221f"))
        note = "达标" if score >= 60 else "薄弱，需改进"
        rows.append(
            f'<div class="dim"><div class="dim-name">{DIMENSION_LABELS[dim]}<div style="font-size:10.5px;color:#9ca3af;font-weight:400">权重 {int(weights[dim]*100)}%</div></div>'
            f'<div class="dim-bar"><div class="dim-fill" style="width:{pct}%;background:{color}"></div></div>'
            f'<div class="dim-score" style="color:{color}">{score:.1f}</div></div>'
            f'<div class="dim-note">{"✓ " + note if score >= 60 else "⚠ " + note}</div>'
        )
    return "".join(rows)


def engine_matrix_html(engines):
    rows = []
    for engine, e in engines.items():
        vis_color = "#0b8043" if e["visibility"] >= 60 else "#c5221f"
        rows.append(
            f'<tr><td><b>{engine}</b></td><td>{e["queries"]}</td>'
            f'<td style="color:{vis_color};font-weight:700">{e["visibility"]:.1f}</td>'
            f'<td>{e["recommendation"]:.1f}</td><td>{e["sentiment"]:.1f}</td></tr>'
        )
    return "".join(rows)


def detail_rows(data):
    rows = []
    for q in data.get("queries", []):
        cov = q.get("coverage", {})
        covered = sum(1 for k in ("intro", "selling_points", "products", "pricing", "reputation", "news") if cov.get(k, True))
        citations = "、".join(CITATION_LABELS.get(c.get("type", "low_quality"), c.get("type")) for c in q.get("citations", [])) or "—"
        rows.append(
            f'<tr><td>{q.get("engine", "—")}</td><td style="max-width:220px">{q.get("query", "")}</td>'
            f'<td><span class="pill">{POSITION_LABELS.get(q.get("position", "absent"), q.get("position"))}</span></td>'
            f'<td><span class="pill">{RECOMMENDATION_LABELS.get(q.get("recommendation", "neutral"), q.get("recommendation"))}</span></td>'
            f'<td>{citations}</td>'
            f'<td><span class="pill">{SENTIMENT_LABELS.get(q.get("sentiment", "neutral"), q.get("sentiment"))}</span></td>'
            f'<td>{covered}/6</td><td>{q.get("errors", 0)}</td></tr>'
        )
    return "".join(rows)


def suggestions_html(data):
    sugs = data.get("suggestions", [])
    if not sugs:
        return '<div style="font-size:13.5px;color:#6b7280">未提供建议数据（本次运行未生成建议）。</div>'
    blocks = []
    for s in sugs:
        color, timeline = PRIORITY_META.get(s.get("priority", "P1"), ("#e8710a", "近期"))
        dim_label = DIMENSION_LABELS.get(s.get("dimension", ""), s.get("dimension", ""))
        blocks.append(
            f'<div class="sug"><div class="sug-prio" style="background:{color}">{s.get("priority", "P1")}<span>{timeline}</span></div>'
            f'<div class="sug-body"><div class="act">{s.get("action", "")}</div>'
            f'<div class="meta"><b>目标维度：</b>{dim_label} · <b>预期效果：</b>{s.get("effect", "")}</div>'
            f'<div class="meta"><b>衡量方式：</b>{s.get("measure", "")}</div></div></div>'
        )
    return "".join(blocks)


def build_report(data, result):
    brand = result.get("brand") or data.get("brand", "品牌")
    total = result["total"]
    grade = result["grade"]
    grade_color, grade_label = GRADE_META.get(grade, ("#6b7280", ""))
    dims = result["dimensions"]
    weak = result.get("weak_dimensions", [])
    weak_text = "、".join(DIMENSION_LABELS.get(w, w) for w in weak) if weak else "无（全部维度达标）"

    best = max(dims, key=dims.get)
    worst = min(dims, key=dims.get)

    summary = (
        f"综合 GEO 得分 <b>{total:.1f}</b>（{grade_label}）。最强维度为"
        f"「{DIMENSION_LABELS[best]}」（{dims[best]:.1f}），最弱维度为「{DIMENSION_LABELS[worst]}」（{dims[worst]:.1f}）。"
        f"薄弱维度：{weak_text}。"
    )

    source_note = data.get("source_note", "数据来源：未注明（请人工核对）。")

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{brand} GEO 诊断报告</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <h1>{brand} · GEO 诊断报告</h1>
    <div class="sub">生成式引擎优化（Generative Engine Optimization）诊断 · 生成日期 {data.get("date", "—")}</div>
    <div class="score-row">
      <div class="big-score">{total:.1f}</div>
      <div><div style="opacity:.75;font-size:13px">综合得分（满分 100）</div>
      <div style="margin-top:8px"><span class="grade-badge" style="background:{grade_color}">等级 {grade} · {grade_label}</span></div></div>
    </div>
    <div class="summary">{summary}</div>
  </div>

  <div class="card">
    <h2>六维得分雷达</h2>
    <div class="svg-wrap">{radar_svg(dims)}</div>
    <div class="legend">维度得分 0-100，越靠近外圈表现越好。综合得分 = 各维度得分 × 权重 之和。</div>
  </div>

  <div class="card">
    <h2>维度得分明细</h2>
    {dim_bar_html(dims, result.get("weights", {}))}
  </div>

  <div class="grid2">
    <div class="card">
      <h2>引擎对比矩阵</h2>
      <table>
        <tr><th>引擎</th><th>查询数</th><th>可见度</th><th>推荐度</th><th>情感</th></tr>
        {engine_matrix_html(result.get("engines", {}))}
      </table>
    </div>
    <div class="card">
      <h2>内容基础评估</h2>
      {foundation_html(data.get("foundation", {}))}
    </div>
  </div>

  <div class="card">
    <h2>逐条查询明细</h2>
    <table>
      <tr><th>引擎</th><th>测试查询</th><th>品牌位置</th><th>推荐状态</th><th>引用源</th><th>情感</th><th>覆盖</th><th>事实错误</th></tr>
      {detail_rows(data)}
    </table>
  </div>

  <div class="card">
    <h2>改进建议（按优先级）</h2>
    {suggestions_html(data)}
  </div>

  <div class="foot">
    {source_note}<br>
    本报告由 brand-geo-audit 技能生成，仅供参考，不构成商业决策依据。
  </div>
</div>
</body>
</html>"""
    return html


def foundation_html(f):
    if not f:
        return '<div style="font-size:13.5px;color:#6b7280">未提供内容基础数据。</div>'
    rows = [
        ("百科条目且内容正面", f.get("wiki", False)),
        ("官网可检索且含 FAQ/结构化标记", f.get("official_site_structured", False)),
        ("权威第三方内容 ≥5 篇", f.get("third_party_count", 0) >= 5),
        ("实体被知识图谱识别", f.get("knowledge_graph", False)),
        ("近 3-6 个月内容生态活跃", f.get("content_active", False)),
    ]
    items = "".join(
        f'<div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #eef1f5;font-size:13.5px">'
        f'<span>{label}</span><span style="font-weight:600;color:{"#0b8043" if ok else "#c5221f"}">{"✓ 是" if ok else "✗ 否"}</span></div>'
        for label, ok in rows
    )
    return f'<div>权威第三方内容数量：<b>{f.get("third_party_count", 0)}</b> 篇</div>{items}'


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    data_path, result_path = sys.argv[1], sys.argv[2]
    out = sys.argv[sys.argv.index("-o") + 1] if "-o" in sys.argv else None
    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)
    with open(result_path, encoding="utf-8") as f:
        result = json.load(f)
    html = build_report(data, result)
    if not out:
        brand = result.get("brand") or data.get("brand", "brand")
        out = f"{brand}_geo_audit_report.html"
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ 报告已生成: {out}")


if __name__ == "__main__":
    main()

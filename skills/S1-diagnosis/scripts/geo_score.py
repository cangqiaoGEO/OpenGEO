#!/usr/bin/env python3
"""
GEO 品牌诊断评分计算器

从"查询明细 JSON"确定性计算品牌在生成式 AI 引擎（GEO）中的各维度得分、
综合得分、等级与薄弱维度。评分标准见 references/geo-metrics.md。

用法：
    python3 geo_score.py <data.json>
    cat data.json | python3 geo_score.py -

输入 JSON 结构（详见文件底部 __doc_example）：

{
  "brand": "示例品牌",
  "queries": [
    {
      "query": "最好用的XX是什么",
      "engine": "ChatGPT",
      "position": "top3",              // top1 | top1_tied | top3 | top5 | mention | absent
      "recommendation": "explicit",    // explicit | tied | neutral | negative
      "citations": [                   // 每项为 {"type": "...", "brand_owned": bool}
        {"type": "official", "brand_owned": true}
      ],
      "sentiment": "positive",         // positive | neutral | negative
      "coverage": {                    // 6 个检查项（可缺省，缺省视为 true）
        "intro": true, "selling_points": true, "products": true,
        "pricing": false, "reputation": true, "news": false
      },
      "errors": 0                      // 答案中的事实错误数量
    }
  ],
  "foundation": {
    "wiki": true,                      // 百科条目且正面
    "official_site_structured": true,  // 官网可检索且含 FAQ/结构化标记
    "third_party_count": 8,            // 权威第三方内容数量
    "knowledge_graph": true,           // 实体被知识图谱识别
    "content_active": true             // 近 3-6 个月内容生态活跃
  }
}

输出 JSON：各维度得分、综合得分、等级、薄弱维度、每引擎明细。
"""

import json
import sys

WEIGHTS = {
    "visibility": 0.30,
    "recommendation": 0.20,
    "citation_quality": 0.15,
    "coverage": 0.15,
    "sentiment": 0.10,
    "foundation": 0.10,
}

POSITION_SCORES = {
    "top1": 100,
    "top1_tied": 85,
    "top3": 70,
    "top5": 50,
    "mention": 30,
    "absent": 0,
}

RECOMMENDATION_SCORES = {
    "explicit": 100,
    "tied": 70,
    "neutral": 40,
    "negative": 0,
}

CITATION_TYPE_SCORES = {
    "official": 90,
    "wiki": 80,
    "authoritative": 75,
    "review": 65,
    "social": 45,
    "low_quality": 20,
}

SENTIMENT_SCORES = {
    "positive": 1.0,
    "neutral": 0.0,
    "negative": -1.0,
}

COVERAGE_ITEMS = ["intro", "selling_points", "products", "pricing", "reputation", "news"]

GRADES = [
    (80, "S", "优秀，GEO 领先者"),
    (60, "A", "良好，有竞争力"),
    (40, "B", "中等，需要改进"),
    (20, "C", "较弱，明显落后"),
    (0, "D", "缺失，几乎不可见"),
]

FOUNDATION_SCORES = {
    "wiki": 25,
    "official_site_structured": 20,
    "third_party_count": 20,
    "knowledge_graph": 15,
    "content_active": 20,
}


def clamp(value, low=0.0, high=100.0):
    return max(low, min(high, value))


def grade_for(score):
    for threshold, letter, label in GRADES:
        if score >= threshold:
            return letter, label
    return GRADES[-1][1], GRADES[-1][2]


def calc_visibility(queries):
    total = len(queries)
    if total == 0:
        return 0.0
    mention_rate = sum(1 for q in queries if q.get("position") != "absent") / total * 100
    position_mean = sum(POSITION_SCORES.get(q.get("position", "absent"), 0) for q in queries) / total
    return round(clamp(0.5 * mention_rate + 0.5 * position_mean), 1)


def calc_recommendation(queries):
    total = len(queries)
    if total == 0:
        return 0.0
    return round(sum(RECOMMENDATION_SCORES.get(q.get("recommendation", "neutral"), 40) for q in queries) / total, 1)


def calc_citation_quality(queries):
    all_citations = []
    brand_owned_cited = False
    for q in queries:
        for c in q.get("citations", []):
            all_citations.append(c)
            if c.get("brand_owned"):
                brand_owned_cited = True
    if not all_citations:
        return 0.0
    mean = sum(CITATION_TYPE_SCORES.get(c.get("type", "low_quality"), 20) for c in all_citations) / len(all_citations)
    diversity_factor = min(1.0, len(all_citations) / 3.0)
    score = mean * diversity_factor
    if brand_owned_cited:
        score += 10
    return round(clamp(score), 1)


def calc_coverage(queries):
    if not queries:
        return 0.0
    covered_items = 0
    total_items = 0
    errors = 0
    for q in queries:
        cov = q.get("coverage", {})
        for item in COVERAGE_ITEMS:
            total_items += 1
            if cov.get(item, True):
                covered_items += 1
        errors += q.get("errors", 0)
    score = covered_items / total_items * 100 if total_items else 0
    score -= 10 * errors
    return round(clamp(score), 1)


def calc_sentiment(queries):
    total = len(queries)
    if total == 0:
        return 50.0
    s = sum(SENTIMENT_SCORES.get(q.get("sentiment", "neutral"), 0.0) for q in queries) / total
    return round((s + 1.0) / 2.0 * 100, 1)


def calc_foundation(foundation):
    if not foundation:
        return 0.0
    score = 0.0
    for key, max_score in FOUNDATION_SCORES.items():
        if key == "third_party_count":
            count = foundation.get("third_party_count", 0)
            if count >= 5:
                score += max_score
            elif count >= 2:
                score += max_score * 0.5
            elif count >= 1:
                score += max_score * 0.25
        elif foundation.get(key):
            score += max_score
    return round(clamp(score), 1)


def compute(data):
    queries = data.get("queries", [])
    foundation = data.get("foundation", {})
    dimensions = {
        "visibility": calc_visibility(queries),
        "recommendation": calc_recommendation(queries),
        "citation_quality": calc_citation_quality(queries),
        "coverage": calc_coverage(queries),
        "sentiment": calc_sentiment(queries),
        "foundation": calc_foundation(foundation),
    }
    total = round(sum(dimensions[k] * WEIGHTS[k] for k in WEIGHTS), 1)
    grade, grade_label = grade_for(total)
    weak = [k for k in WEIGHTS if dimensions[k] < 60]
    return {
        "brand": data.get("brand", ""),
        "dimensions": dimensions,
        "weights": WEIGHTS,
        "total": total,
        "grade": grade,
        "grade_label": grade_label,
        "weak_dimensions": weak,
        "engines": engine_detail(queries),
    }


def engine_detail(queries):
    by_engine = {}
    for q in queries:
        engine = q.get("engine", "unknown")
        by_engine.setdefault(engine, []).append(q)
    result = {}
    for engine, qs in by_engine.items():
        result[engine] = {
            "queries": len(qs),
            "visibility": calc_visibility(qs),
            "recommendation": calc_recommendation(qs),
            "sentiment": calc_sentiment(qs),
        }
    return result


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    path = sys.argv[1]
    if path == "-":
        data = json.load(sys.stdin)
    else:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    result = compute(data)
    print(json.dumps(result, ensure_ascii=False, indent=2))


__doc_example = {
    "brand": "示例品牌",
    "queries": [
        {
            "query": "最好用的XX是什么",
            "engine": "ChatGPT",
            "position": "top1",
            "recommendation": "explicit",
            "citations": [{"type": "official", "brand_owned": True}, {"type": "wiki", "brand_owned": False}],
            "sentiment": "positive",
            "coverage": {"intro": True, "selling_points": True, "products": True, "pricing": True, "reputation": True, "news": False},
            "errors": 0,
        }
    ],
    "foundation": {
        "wiki": True,
        "official_site_structured": True,
        "third_party_count": 8,
        "knowledge_graph": True,
        "content_active": True,
    },
}

if __name__ == "__main__":
    main()

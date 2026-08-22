#!/usr/bin/env python3
"""Produce a deterministic quality audit for v2 GEO research and scores"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from evidence_validate import validate_evidence_package  # noqa: E402
from geo_score import compute  # noqa: E402


SCHEMA_VERSION = "2.0.0"
MAX_SOURCE_AGE_DAYS = 180
UNKNOWN_RATIO_WARNING = 0.20
CHECK_NAMES = (
    "boundary_completeness",
    "sample_sufficiency",
    "source_reliability",
    "coverage_completeness",
    "cross_validation",
    "counterexample_review",
    "data_freshness",
    "traceability",
)


def _check(status: str, *findings: str) -> dict[str, Any]:
    """Build one stable audit check"""

    return {"status": status, "findings": list(findings)}


def _gap(
    gap_id: str,
    category: str,
    description: str,
    impact: str,
    next_action: str,
    *,
    source_ids: list[str] | None = None,
    observation_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Build one actionable evidence gap"""

    return {
        "gap_id": gap_id,
        "category": category,
        "description": description,
        "impact": impact,
        "source_ids": source_ids or [],
        "observation_ids": observation_ids or [],
        "next_action": next_action,
    }


def _collect_claims(context: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Collect every explicit claim from the minimum business model"""

    claims: list[tuple[str, dict[str, Any]]] = []
    positioning = context.get("brand_positioning", {})
    if isinstance(positioning, dict) and isinstance(positioning.get("claim"), dict):
        claims.append(("brand_positioning", positioning["claim"]))
    for collection_name in ("target_customers", "customer_problems", "products", "business_scenarios", "competitors"):
        for index, item in enumerate(context.get(collection_name, [])):
            if isinstance(item, dict) and isinstance(item.get("claim"), dict):
                claims.append((f"{collection_name}[{index}]", item["claim"]))
    return claims


def _source_check(context: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Audit source verification state and return any source gaps"""

    sources = context.get("sources", [])
    unverified = [item for item in sources if item.get("verification_status") == "unverified"]
    if not sources:
        return _check("fail", "领域模型没有来源"), [
            _gap("gap-no-sources", "source", "领域模型没有来源", "业务语境无法独立核验", "补充并验证官方或权威来源")
        ]
    if unverified:
        ids = [item["source_id"] for item in unverified]
        return _check("warning", f"{len(unverified)} 个来源尚未验证"), [
            _gap("gap-unverified-sources", "source", "存在未验证来源", "相关结论的可靠性受限", "验证来源主体、页面内容和可访问性", source_ids=ids)
        ]
    return _check("pass", f"{len(sources)} 个领域来源均已验证或部分验证"), []


def _coverage_check(score_result: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Audit unknown ratios in every score dimension"""

    warnings: list[str] = []
    gaps: list[dict[str, Any]] = []
    for dimension, metric in score_result.get("dimensions", {}).items():
        total = metric.get("sample_count", 0) + metric.get("unknown_count", 0)
        ratio = metric.get("unknown_count", 0) / total if total else 1.0
        if ratio > UNKNOWN_RATIO_WARNING:
            warnings.append(f"{dimension} 未知比例为 {ratio:.0%}")
            gaps.append(
                _gap(
                    f"gap-unknown-{dimension.replace('_', '-')}",
                    "coverage",
                    f"{dimension} 的未知数据比例为 {ratio:.0%}",
                    "该维度分数可能依赖有限样本",
                    f"补齐 {dimension} 的缺失观测后使用同一查询协议复查",
                )
            )
    if warnings:
        return _check("warning", *warnings), gaps
    return _check("pass", "所有维度未知比例均在允许范围内"), []


def _cross_validation_check(context: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Identify facts and inferences that rely on only one source"""

    single_source = [path for path, claim in _collect_claims(context) if claim.get("status") in {"fact", "inference"} and len(claim.get("evidence_ids", [])) == 1]
    if not single_source:
        return _check("pass", "事实和推断均具有多源支持或不需要交叉验证"), []
    return _check("warning", f"{len(single_source)} 项事实或推断只有单一来源"), [
        _gap(
            "gap-single-source-claims",
            "cross_validation",
            f"{len(single_source)} 项事实或推断只有单一来源",
            "单一来源错误可能传导到查询设计和建议",
            "为高影响事实补充独立来源并重新运行研究包校验",
        )
    ]


def _freshness_check(scope: dict[str, Any], context: dict[str, Any], evidence: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Audit source-review and observation-collection recency, not publication age"""

    as_of = date.fromisoformat(scope["as_of"])
    stale_sources: list[str] = []
    for source in context.get("sources", []):
        retrieved = datetime.fromisoformat(source["retrieved_at"]).date()
        if (as_of - retrieved).days > MAX_SOURCE_AGE_DAYS:
            stale_sources.append(source["source_id"])
    stale_observations: list[str] = []
    for observation in evidence.get("observations", []):
        if observation.get("status") != "observed":
            continue
        observed = datetime.fromisoformat(observation["observed_at"]).date()
        if (as_of - observed).days > MAX_SOURCE_AGE_DAYS:
            stale_observations.append(observation["observation_id"])
    if stale_sources or stale_observations:
        return _check("warning", f"{len(stale_sources)} 个来源复核时间和 {len(stale_observations)} 个观测采集时间超过 {MAX_SOURCE_AGE_DAYS} 天"), [
            _gap(
                "gap-stale-evidence",
                "freshness",
                "部分来源复核或 AI 观测超过时效窗口",
                "当前结果可能不能代表截止日期时的产品和内容状态",
                "重新采集过期来源和 AI 引擎回答",
                source_ids=stale_sources,
                observation_ids=stale_observations,
            )
        ]
    return _check("pass", f"来源复核时间和观测采集时间均在 {MAX_SOURCE_AGE_DAYS} 天窗口内"), []


def _counterevidence(evidence: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Extract observed absences, negative answers, and factual errors as counterevidence"""

    items: list[dict[str, Any]] = []
    for observation in evidence.get("observations", []):
        if observation.get("status") != "observed":
            continue
        observation_id = observation["observation_id"]
        suffix = observation_id.removeprefix("obs-")
        if observation.get("position") == "absent":
            items.append({
                "counterevidence_id": f"counter-absent-{suffix}",
                "description": f"{observation['engine']['name']} 的查询 {observation['query_id']} 中品牌未出现",
                "source_ids": [],
                "observation_ids": [observation_id],
                "implication": "品牌可见度并非在所有核心查询中稳定成立",
            })
        if observation.get("recommendation") == "negative" or observation.get("sentiment") == "negative":
            items.append({
                "counterevidence_id": f"counter-negative-{suffix}",
                "description": f"{observation['engine']['name']} 的回答包含负面推荐或情感",
                "source_ids": [],
                "observation_ids": [observation_id],
                "implication": "正面品牌判断存在反例，需要检查原因和来源",
            })
        for error in observation.get("fact_errors") or []:
            items.append({
                "counterevidence_id": f"counter-error-{suffix}-{error['error_id'].removeprefix('error-')}",
                "description": error["description"],
                "source_ids": [],
                "observation_ids": [observation_id],
                "implication": "回答中的品牌事实并非完全准确",
            })
    if items:
        return _check("pass", f"已记录 {len(items)} 条反例或反向证据"), items
    return _check("warning", "未发现或未记录反例，需人工确认是否执行过反例检查"), []


def audit_quality(research: dict[str, Any], evidence: dict[str, Any], score_result: dict[str, Any]) -> dict[str, Any]:
    """Audit boundaries, evidence, samples, counterexamples, and traceability"""

    validation = validate_evidence_package(research, evidence)
    scope = research.get("scope", {})
    context = research.get("domain_context", {})
    protocol = research.get("query_protocol", {})
    checks: dict[str, dict[str, Any]] = {}
    gaps: list[dict[str, Any]] = []
    warnings: list[str] = []

    if validation["valid"] and scope.get("status") == "ready" and context.get("status") == "ready" and protocol.get("status") == "frozen":
        checks["boundary_completeness"] = _check("pass", "研究范围、业务语境和查询协议均已冻结")
    else:
        checks["boundary_completeness"] = _check("fail", "研究基础或证据契约未通过校验")
        gaps.append(_gap("gap-invalid-boundary", "boundary", "研究基础或证据契约无效", "结果不能进入正式审计", "先修复所有校验错误"))

    sample_status = validation["assessment"]["status"]
    if sample_status == "measured":
        checks["sample_sufficiency"] = _check("pass", f"{validation['assessment']['measured_engines']} 个引擎完成四类核心查询")
    else:
        level = "fail" if sample_status == "insufficient_data" else "warning"
        checks["sample_sufficiency"] = _check(level, *validation["assessment"]["limitations"])
        gaps.append(_gap("gap-sample-sufficiency", "sample", "样本未达到正式测量门槛", "不能形成完整正式结论", "按冻结查询协议补齐缺失引擎观测"))

    source_check, source_gaps = _source_check(context)
    checks["source_reliability"] = source_check
    gaps.extend(source_gaps)
    coverage_check, coverage_gaps = _coverage_check(score_result)
    checks["coverage_completeness"] = coverage_check
    gaps.extend(coverage_gaps)
    cross_check, cross_gaps = _cross_validation_check(context)
    checks["cross_validation"] = cross_check
    gaps.extend(cross_gaps)
    counter_check, counterevidence = _counterevidence(evidence)
    checks["counterexample_review"] = counter_check
    freshness_check, freshness_gaps = _freshness_check(scope, context, evidence)
    checks["data_freshness"] = freshness_check
    gaps.extend(freshness_gaps)

    for unknown in context.get("unknowns", []):
        gaps.append(_gap(
            f"gap-business-{unknown['id'].removeprefix('unknown-')}",
            "business_unknown",
            unknown["question"],
            unknown["impact"],
            "完成业务访谈或补充权威资料后更新 DomainContext",
        ))

    if validation["valid"]:
        expected_score = compute(research, evidence, validation)
        if expected_score == score_result:
            checks["traceability"] = _check("pass", "评分结果可由研究包和证据包确定性复算")
        else:
            checks["traceability"] = _check("fail", "提供的评分结果与确定性复算结果不一致")
            gaps.append(_gap("gap-score-mismatch", "traceability", "评分结果无法复算", "报告可能展示被修改或过期的分数", "重新运行 geo_score.py 并替换结果文件"))
    else:
        checks["traceability"] = _check("fail", "输入无效，无法执行评分复算")

    for name in CHECK_NAMES:
        check = checks[name]
        if check["status"] != "pass":
            warnings.extend(f"{name}: {finding}" for finding in check["findings"])
    if any(check["status"] == "fail" for check in checks.values()):
        status = "failed" if sample_status != "insufficient_data" else "insufficient_data"
        confidence = "unknown" if status == "failed" else "low"
    elif sample_status == "insufficient_data":
        status, confidence = "insufficient_data", "low"
    elif warnings or gaps:
        status = "passed_with_warnings"
        confidence = "medium" if sample_status == "measured" else "low"
    else:
        status, confidence = "passed", "high"
    next_actions = list(dict.fromkeys(gap["next_action"] for gap in gaps))
    return {
        "schema_version": SCHEMA_VERSION,
        "audit_id": f"audit-{protocol.get('protocol_id', 'unknown').removeprefix('protocol-')}",
        "protocol_id": protocol.get("protocol_id", ""),
        "audit_date": scope.get("as_of", ""),
        "status": status,
        "confidence": confidence,
        "checks": checks,
        "gaps": gaps,
        "counterevidence": counterevidence,
        "warnings": warnings,
        "next_validation_actions": next_actions,
    }


def _load(path: str) -> Any:
    """Load UTF-8 JSON"""

    with Path(path).open(encoding="utf-8") as file:
        return json.load(file)


def main() -> int:
    """Generate quality-audit JSON from research, evidence, and score files"""

    parser = argparse.ArgumentParser(description="Audit Brand GEO v2 research quality")
    parser.add_argument("research_path")
    parser.add_argument("evidence_path")
    parser.add_argument("score_path")
    args = parser.parse_args()
    try:
        result = audit_quality(_load(args.research_path), _load(args.evidence_path), _load(args.score_path))
    except (OSError, json.JSONDecodeError, KeyError, ValueError) as error:
        print(json.dumps({"status": "failed", "error": str(error)}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] not in {"failed"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

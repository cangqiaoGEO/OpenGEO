#!/usr/bin/env python3
"""Validate and map the existing OpenGEO materials before topic generation."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class Material:
    kind: str
    path: str
    purpose: str
    fact: bool = False
    required: bool = True
    alternatives: tuple[str, ...] = ()


MATERIALS = (
    Material("品牌事实", "brand-facts/examples/cangqiao/identity.md", "公司主体与名称", True),
    Material("品牌事实", "brand-facts/examples/cangqiao/audience.md", "受众与三层决策问题", True),
    Material("意图词", "brand-facts/examples/cangqiao/intent-words.md", "攻略/对比/口碑选题", True),
    Material("品牌边界", "brand-facts/examples/cangqiao/boundaries.md", "承诺与合规红线", True),
    Material("转化入口", "brand-facts/examples/cangqiao/channels.md", "CTA", True),
    Material("FAQ", "brand-facts/examples/cangqiao/faq.md", "真实用户问题", True),
    Material("产品", "brand-facts/examples/cangqiao/products/geo-course.md", "课程能力与交付物", True),
    Material("产品", "brand-facts/examples/cangqiao/products/geo-operations.md", "代运营能力与边界", True),
    Material("诊断", "brand-facts/examples/cangqiao/diagnosis/2026-08-21-baseline.md", "公开基线与P0选题", True),
    Material("定位候选", "brand-facts/examples/cangqiao/positioning.md", "仅stable时可用", True, False),
    Material("S1", "skills/S1-diagnosis/SKILL.md", "六维诊断与分级"),
    Material(
        "S2",
        "skills/geo-intent-words/SKILL.md",
        "三层意图选题",
        alternatives=("skills/S2-intent-words.md",),
    ),
    Material("S3", "skills/S3-content.md", "核心答案/方法/证据/CTA/FAQ"),
    Material(
        "S4",
        "skills/geo-short-video-expert/SKILL.md",
        "算法+GEO双满足",
        alternatives=("skills/S4-short-video.md",),
    ),
    Material(
        "S7",
        "skills/geo-weekly-monitor/SKILL.md",
        "复测过程选题",
        alternatives=("skills/S7-monitoring.md",),
    ),
    Material("课程方法", "coursebook/docs/ch05.md", "四步法与AI友好七特征"),
    Material("矩阵方法", "coursebook/docs/ch06.md", "AI员工与短视频矩阵"),
    Material("案例方法", "coursebook/docs/ch07.md", "案例结构，不转写为自身业绩"),
    Material("系统架构", "system/architecture.md", "一库一脑七技一环"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check required OpenGEO source materials.")
    parser.add_argument("--repo", required=True, type=Path, help="OpenGEO repository root")
    parser.add_argument("--output", required=True, type=Path, help="Markdown material map")
    parser.add_argument("--today", type=date.fromisoformat, default=date.today())
    return parser.parse_args()


def frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    match = re.match(r"^---\s*\r?\n(.*?)\r?\n---", text, flags=re.DOTALL)
    if not match:
        return {}
    values: dict[str, str] = {}
    for line in match.group(1).splitlines():
        item = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*?)\s*$", line)
        if item:
            values[item.group(1)] = item.group(2).strip('"\'')
    return values


def assess(material: Material, root: Path, today: date) -> tuple[str, str, str, str]:
    resolved_path = next(
        (candidate for candidate in (material.path, *material.alternatives) if (root / candidate).is_file()),
        material.path,
    )
    path = root / resolved_path
    if not path.is_file():
        return resolved_path, "MISSING", "-", "文件不存在"
    if not material.fact:
        return resolved_path, "SPEC", "-", "可用"

    metadata = frontmatter(path.read_text(encoding="utf-8-sig"))
    status = metadata.get("status", "UNKNOWN")
    stale_after = metadata.get("stale_after", "-")
    if status != "stable":
        return resolved_path, status.upper(), stale_after, "不进入正式脚本"
    if stale_after != "-":
        try:
            if date.fromisoformat(stale_after) < today:
                return resolved_path, "EXPIRED", stale_after, "需负责人重新确认"
        except ValueError:
            return resolved_path, "INVALID_DATE", stale_after, "stale_after格式错误"
    return resolved_path, "STABLE", stale_after, "可用于正式脚本"


def main() -> None:
    args = parse_args()
    root = args.repo.resolve()
    if not root.is_dir():
        print(f"OpenGEO目录不存在：{root}", file=sys.stderr)
        raise SystemExit(2)

    rows: list[tuple[Material, str, str, str, str]] = []
    blockers: list[str] = []
    for material in MATERIALS:
        resolved_path, status, stale_after, note = assess(material, root, args.today)
        rows.append((material, resolved_path, status, stale_after, note))
        if material.required and status not in {"STABLE", "SPEC"}:
            blockers.append(f"{resolved_path}: {status}")

    lines = [
        "# GEO原有材料映射",
        "",
        f"- 生成时间：{datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"- OpenGEO目录：`{root}`",
        f"- 检查日期：{args.today.isoformat()}",
        f"- 结论：{'BLOCKED' if blockers else 'READY'}",
        "",
        "| 类型 | 原有材料路径 | 状态 | 有效期 | 本片用途 | 处理 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for material, resolved_path, status, stale_after, note in rows:
        lines.append(
            f"| {material.kind} | `{resolved_path}` | {status} | {stale_after} | {material.purpose} | {note} |"
        )
    lines.extend(["", "## 阻断项", ""])
    lines.extend([f"- {item}" for item in blockers] or ["- 无"])
    lines.extend(
        [
            "",
            "## 使用规则",
            "",
            "- 选题时从 READY/STABLE/SPEC 材料中选择实际引用项。",
            "- 定位候选不是必需项；其状态非 STABLE 时必须排除。",
            "- 外部案例与示例视频只提供方法或形式参考，不能变成仓桥智能事实。",
        ]
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"material_map={args.output.resolve()}")
    print(f"status={'BLOCKED' if blockers else 'READY'}")
    if blockers:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

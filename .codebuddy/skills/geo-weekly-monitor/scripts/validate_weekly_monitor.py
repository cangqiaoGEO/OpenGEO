#!/usr/bin/env python3
"""Dependency-free validation for OpenGEO S7 fixed-question monitoring."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path


CONCEPTS = ("positioning.md", "audience.md", "identity.md")
LAYERS = {"品类推荐": 10, "品牌直达": 5, "对比验证": 5}
YES_NO = {"是", "否", "无法验证"}
ACCURACY = {"正确", "部分正确", "不正确", "无法验证"}
FIELDS = ("问题 ID", "层级", "平台", "提及", "推荐", "引用源", "准确性", "证据", "备注")


def frontmatter(path: Path) -> tuple[dict[str, str], str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"{path.name}：缺少 YAML frontmatter")
    end = next((i for i, line in enumerate(lines[1:], 1) if line.strip() == "---"), None)
    if end is None:
        raise ValueError(f"{path.name}：YAML frontmatter 未闭合")
    data: dict[str, str] = {}
    for line in lines[1:end]:
        found = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", line)
        if found:
            data[found.group(1)] = found.group(2).strip().strip('"\'')
    return data, "\n".join(lines[end + 1 :])


def expired(data: dict[str, str], as_of: date) -> bool:
    value = data.get("stale_after")
    if not value:
        return False
    matched = re.match(r"^(\d{4}-\d{2}-\d{2})", value)
    if not matched:
        return True
    return date.fromisoformat(matched.group(1)) < as_of


def table_cells(line: str) -> list[str]:
    return [value.strip() for value in line.strip().strip("|").split("|")]


def is_rule(row: list[str]) -> bool:
    return bool(row) and all(re.fullmatch(r":?-{3,}:?", item.replace(" ", "")) for item in row)


def questions(body: str) -> list[dict[str, str]]:
    active = False
    result: list[dict[str, str]] = []
    for line in body.splitlines():
        if line.startswith("# "):
            active = line.strip().startswith("# 问题集")
            continue
        if not active or not line.lstrip().startswith("|"):
            continue
        row = table_cells(line)
        if not row or is_rule(row) or row[0] in {"#", "序号"} or len(row) < 3:
            continue
        result.append({"id": row[0], "question": row[1], "layer": row[2]})
    return result


def inspect(facts_dir: Path, monitor: Path, as_of: date) -> dict[str, object]:
    errors: list[str] = []
    eligible: list[dict[str, str]] = []
    for name in CONCEPTS:
        path = facts_dir / name
        if not path.exists():
            errors.append(f"缺少必需概念：{name}")
            continue
        try:
            data, _ = frontmatter(path)
            if data.get("status") != "stable":
                errors.append(f"{name}：status 必须为 stable")
            elif expired(data, as_of):
                errors.append(f"{name}：stale_after 已过期或格式无效")
            else:
                eligible.append({"path": name, "title": data.get("title", "")})
        except (OSError, ValueError) as exc:
            errors.append(str(exc))

    fixed: list[dict[str, str]] = []
    if not monitor.exists():
        errors.append(f"缺少固定问题集：{monitor}")
    else:
        try:
            data, body = frontmatter(monitor)
            if data.get("status") != "stable":
                errors.append(f"{monitor.name}：status 必须为 stable")
            elif expired(data, as_of):
                errors.append(f"{monitor.name}：stale_after 已过期或格式无效")
            fixed = questions(body)
            if len(fixed) != 20:
                errors.append(f"{monitor.name}：固定问题必须恰好 20 条，当前为 {len(fixed)} 条")
            if len({item['id'] for item in fixed}) != len(fixed):
                errors.append(f"{monitor.name}：问题 ID 不得重复")
            if Counter(item["layer"] for item in fixed) != LAYERS:
                errors.append(f"{monitor.name}：层级必须为品类推荐 10、品牌直达 5、对比验证 5")
            for item in fixed:
                if not item["question"] or "[" in item["question"]:
                    errors.append(f"{monitor.name}：问题 {item['id']} 仍是占位内容")
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
    return {"facts_dir": str(facts_dir), "monitor_file": str(monitor), "as_of": as_of.isoformat(), "eligible_required_files": eligible, "question_count": len(fixed), "questions": fixed, "errors": errors}


def run_rows(path: Path) -> tuple[dict[str, str], list[dict[str, str]]]:
    data, body = frontmatter(path)
    header: list[str] | None = None
    records: list[dict[str, str]] = []
    for line in body.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        row = table_cells(line)
        if "问题 ID" in row:
            header = row
        elif header and not is_rule(row) and len(row) == len(header):
            record = dict(zip(header, row))
            if record.get("问题 ID"):
                records.append(record)
    return data, records


def validate(facts: dict[str, object], run: Path, named_platforms: list[str]) -> dict[str, object]:
    errors = list(facts["errors"])
    try:
        data, records = run_rows(run)
    except (OSError, ValueError) as exc:
        return {"run": str(run), "errors": errors + [str(exc)]}
    if data.get("type") != "Monitor Run":
        errors.append(f"{run.name}：type 必须为 Monitor Run")
    if data.get("status") != "draft":
        errors.append(f"{run.name}：新复测记录 status 必须为 draft")
    platforms = named_platforms or sorted({row.get("平台", "") for row in records if row.get("平台")})
    if not platforms:
        errors.append(f"{run.name}：至少需要一个实际可访问的平台")
    expected = {(item["id"], item["layer"]) for item in facts.get("questions", [])}
    seen = Counter((row.get("问题 ID", ""), row.get("层级", ""), row.get("平台", "")) for row in records)
    for index, row in enumerate(records, 1):
        missing = [field for field in FIELDS if not row.get(field)]
        if missing:
            errors.append(f"{run.name}：第 {index} 条缺少 {', '.join(missing)}")
        if row.get("提及") not in YES_NO or row.get("推荐") not in YES_NO:
            errors.append(f"{run.name}：第 {index} 条提及/推荐值无效")
        if row.get("准确性") not in ACCURACY:
            errors.append(f"{run.name}：第 {index} 条准确性值无效")
        if (row.get("问题 ID"), row.get("层级")) not in expected:
            errors.append(f"{run.name}：第 {index} 条不属于固定问题集")
    for question_id, layer in expected:
        for platform in platforms:
            if seen[(question_id, layer, platform)] != 1:
                errors.append(f"{run.name}：问题 {question_id} / {layer} / {platform} 应恰好出现 1 次")
    return {"run": str(run), "platforms": platforms, "row_count": len(records), "expected_row_count": len(expected) * len(platforms), "errors": errors}


def aggregate(records: list[dict[str, str]]) -> dict[str, dict[str, int]]:
    stats: dict[str, dict[str, int]] = {}
    for row in records:
        scope = f"{row.get('平台')} / {row.get('层级')}"
        item = stats.setdefault(scope, {"rows": 0, "mentioned": 0, "recommended": 0, "correct": 0, "partly_correct": 0, "unverifiable": 0})
        item["rows"] += 1
        item["mentioned"] += int(row.get("提及") == "是")
        item["recommended"] += int(row.get("推荐") == "是")
        item["correct"] += int(row.get("准确性") == "正确")
        item["partly_correct"] += int(row.get("准确性") == "部分正确")
        item["unverifiable"] += int(row.get("准确性") == "无法验证")
    return stats


def compare(baseline: Path, current: Path) -> dict[str, object]:
    _, before_rows = run_rows(baseline)
    _, now_rows = run_rows(current)
    before, now = aggregate(before_rows), aggregate(now_rows)
    rows: list[dict[str, object]] = []
    for scope in sorted(set(before) | set(now)):
        if scope not in before or scope not in now:
            rows.append({"scope": scope, "comparable": False, "reason": "基线或本次缺少同口径记录"})
        else:
            delta = {key: now[scope][key] - before[scope][key] for key in ("mentioned", "recommended", "correct", "partly_correct", "unverifiable")}
            rows.append({"scope": scope, "comparable": True, "baseline": before[scope], "current": now[scope], "delta": delta})
    return {"baseline": str(baseline), "current": str(current), "comparisons": rows}


def resolve(path: str, facts_dir: Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else facts_dir / value


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate OpenGEO S7 weekly monitor files.")
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("inspect", "validate"):
        sub = commands.add_parser(command)
        sub.add_argument("--facts-dir", required=True)
        sub.add_argument("--monitor-file", default="monitors/weekly.md")
        sub.add_argument("--as-of", default=date.today().isoformat())
        if command == "validate":
            sub.add_argument("--run", required=True)
            sub.add_argument("--platform", action="append", default=[])
    sub = commands.add_parser("compare")
    sub.add_argument("--baseline", required=True)
    sub.add_argument("--current", required=True)
    args = parser.parse_args()
    try:
        if args.command == "compare":
            result = compare(Path(args.baseline), Path(args.current))
        else:
            facts_dir = Path(args.facts_dir)
            facts = inspect(facts_dir, resolve(args.monitor_file, facts_dir), date.fromisoformat(args.as_of))
            result = facts if args.command == "inspect" else validate(facts, resolve(args.run, facts_dir), args.platform)
    except (OSError, ValueError) as exc:
        result = {"errors": [str(exc)]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result.get("errors") else 0


if __name__ == "__main__":
    sys.exit(main())

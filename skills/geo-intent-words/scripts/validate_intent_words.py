#!/usr/bin/env python3
"""Validate S2 GEO intent-word inputs and output structure without dependencies."""

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path


REQUIRED_FACTS = ("positioning.md", "audience.md")
LAYERS = ("场景攻略层", "品牌对比层", "口碑验证层")
VALID_COVERAGE = {"已覆盖", "部分覆盖", "未覆盖"}


def read_frontmatter(path):
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---(?:\n|$)", text, re.DOTALL)
    if not match:
        return {}, text
    frontmatter = {}
    for line in match.group(1).splitlines():
        field = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*?)\s*(?:#.*)?$", line)
        if field:
            frontmatter[field.group(1)] = field.group(2).strip().strip("'\"")
    return frontmatter, text


def parse_date(value):
    match = re.search(r"\d{4}-\d{2}-\d{2}", value or "")
    if not match:
        return None
    return datetime.strptime(match.group(0), "%Y-%m-%d").date()


def eligible(path, as_of):
    frontmatter, _ = read_frontmatter(path)
    errors = []
    if frontmatter.get("status") != "stable":
        errors.append("status 必须为 stable")
    stale_after = frontmatter.get("stale_after")
    if stale_after:
        expiry = parse_date(stale_after)
        if expiry is None:
            errors.append("stale_after 不是 YYYY-MM-DD 日期")
        elif expiry < as_of:
            errors.append("stale_after 已过期")
    return frontmatter, errors


def inspect_facts(facts_dir, as_of):
    errors = []
    eligible_files = []
    for filename in REQUIRED_FACTS:
        path = facts_dir / filename
        if not path.is_file():
            errors.append(f"缺少必需文件：{filename}")
            continue
        frontmatter, problems = eligible(path, as_of)
        if problems:
            errors.append(f"{filename}：{'；'.join(problems)}")
        else:
            eligible_files.append({"path": filename, "title": frontmatter.get("title", "")})

    identity = facts_dir / "identity.md"
    if identity.is_file():
        frontmatter, problems = eligible(identity, as_of)
        if not problems:
            eligible_files.append({"path": "identity.md", "title": frontmatter.get("title", "")})

    return {
        "facts_dir": str(facts_dir),
        "as_of": as_of.isoformat(),
        "eligible_required_files": eligible_files,
        "errors": errors,
    }


def section_text(text, heading):
    pattern = re.compile(
        rf"^##\s+{re.escape(heading)}\s*$\n(.*?)(?=^##\s+|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    return match.group(1) if match else None


def table_rows(section):
    rows = []
    for line in section.splitlines():
        if re.match(r"^\|\s*\d+\s*\|", line):
            rows.append([part.strip() for part in line.strip().strip("|").split("|")])
    return rows


def validate_output(facts_dir, output, as_of):
    report = inspect_facts(facts_dir, as_of)
    errors = list(report["errors"])
    if not output.is_file():
        errors.append(f"找不到输出文件：{output}")
        return errors

    frontmatter, text = read_frontmatter(output)
    if frontmatter.get("status") != "draft":
        errors.append("输出文件必须以 status: draft 写入，待人工审核后再稳定化")

    for layer in LAYERS:
        section = section_text(text, layer)
        if section is None:
            errors.append(f"缺少章节：{layer}")
            continue
        rows = table_rows(section)
        if not 20 <= len(rows) <= 30:
            errors.append(f"{layer} 必须有 20–30 条问题，当前 {len(rows)} 条")
        for row_number, row in enumerate(rows, start=1):
            if len(row) < 4:
                errors.append(f"{layer} 第 {row_number} 行必须有 4 列")
                continue
            if not row[1].rstrip().endswith(("?", "？")):
                errors.append(f"{layer} 第 {row_number} 行不是以问号结尾的用户问题")
            if row[2] not in VALID_COVERAGE:
                errors.append(f"{layer} 第 {row_number} 行覆盖状态无效：{row[2]}")
            if row[2] in {"已覆盖", "部分覆盖"} and row[3] in {"", "—", "-"}:
                errors.append(f"{layer} 第 {row_number} 行缺少覆盖证据路径或缺口说明")

    citations = section_text(text, "引用概念文件")
    if citations is None:
        errors.append("缺少“引用概念文件”章节")
    else:
        for filename in REQUIRED_FACTS:
            if filename not in citations:
                errors.append(f"引用概念文件中缺少 {filename}")

    checklist = section_text(text, "AI 友好七特征自检")
    if checklist is None:
        errors.append("缺少“AI 友好七特征自检”章节")
    else:
        items = re.findall(r"^\s*-\s*\[([ xX])\]", checklist, re.MULTILINE)
        if len(items) != 7:
            errors.append(f"七特征自检必须列出 7 项，当前 {len(items)} 项")
        elif sum(item.lower() == "x" for item in items) < 5:
            errors.append("AI 友好七特征自检少于 5 项达标")
    return errors


def main():
    parser = argparse.ArgumentParser(description="Validate OpenGEO S2 intent-word inputs and output.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect", help="Validate required fact files.")
    inspect_parser.add_argument("--facts-dir", required=True, type=Path)
    inspect_parser.add_argument("--as-of", default=date.today().isoformat())

    validate_parser = subparsers.add_parser("validate", help="Validate a generated intent-word list.")
    validate_parser.add_argument("--facts-dir", required=True, type=Path)
    validate_parser.add_argument("--output", required=True, type=Path)
    validate_parser.add_argument("--as-of", default=date.today().isoformat())

    args = parser.parse_args()
    try:
        as_of = datetime.strptime(args.as_of, "%Y-%m-%d").date()
    except ValueError:
        parser.error("--as-of 必须是 YYYY-MM-DD")

    facts_dir = args.facts_dir.resolve()
    if not facts_dir.is_dir():
        parser.error(f"--facts-dir 不是目录：{facts_dir}")

    if args.command == "inspect":
        report = inspect_facts(facts_dir, as_of)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        sys.exit(0 if not report["errors"] else 2)

    errors = validate_output(facts_dir, args.output.resolve(), as_of)
    if errors:
        print("验证失败：", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        sys.exit(2)
    print(f"验证通过：{args.output.resolve()}")


if __name__ == "__main__":
    main()

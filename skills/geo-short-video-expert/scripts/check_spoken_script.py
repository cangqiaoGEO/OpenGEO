#!/usr/bin/env python3
"""Validate a plain-text Chinese spoken script against a target duration."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


UNIT_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fffA-Za-z0-9]")
SENTENCE_RE = re.compile(r"[^。！？!?\n]+[。！？!?]?")
INSTRUCTION_RE = re.compile(r"(^|\n)\s*(#{1,6}\s|[-*]\s|\d+[.)]\s|\|)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check a teleprompter script for duration, required terms, and plain-text format."
    )
    parser.add_argument("--input", required=True, help="UTF-8 teleprompter text file")
    parser.add_argument("--target-seconds", type=float, required=True)
    parser.add_argument("--tolerance", type=float, default=0.10)
    parser.add_argument(
        "--units-per-second",
        type=float,
        default=4.0,
        help="Estimated Chinese/alphanumeric delivery rate (default: 4.0)",
    )
    parser.add_argument("--required-term", action="append", default=[])
    parser.add_argument("--output", help="Optional JSON output path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    if not input_path.is_file():
        raise SystemExit(f"Input file not found: {input_path}")
    if args.target_seconds <= 0 or args.units_per_second <= 0:
        raise SystemExit("Target seconds and units per second must be positive")
    if not 0 <= args.tolerance < 1:
        raise SystemExit("Tolerance must be between 0 and 1")

    text = input_path.read_text(encoding="utf-8-sig").strip()
    units = len(UNIT_RE.findall(text))
    estimated_seconds = units / args.units_per_second
    minimum = args.target_seconds * (1 - args.tolerance)
    maximum = args.target_seconds * (1 + args.tolerance)
    missing_terms = [term for term in args.required_term if term not in text]
    sentences = [item.strip() for item in SENTENCE_RE.findall(text) if item.strip()]
    long_sentences = [item for item in sentences if len(UNIT_RE.findall(item)) > 42]
    has_instructions = bool(INSTRUCTION_RE.search(text))

    failures: list[str] = []
    warnings: list[str] = []
    if not text:
        failures.append("口播稿为空")
    if not minimum <= estimated_seconds <= maximum:
        failures.append(
            f"估算时长 {estimated_seconds:.1f}s 不在 {minimum:.1f}s–{maximum:.1f}s 范围内"
        )
    if missing_terms:
        failures.append("缺少必含词：" + "、".join(missing_terms))
    if has_instructions:
        failures.append("提词器混入 Markdown 列表、标题或表格指令")
    if long_sentences:
        warnings.append(f"有 {len(long_sentences)} 个句子超过 42 个口播单位，建议拆句")

    report = {
        "status": "PASS" if not failures else "FAIL",
        "input": str(input_path),
        "unit_count": units,
        "units_per_second": args.units_per_second,
        "estimated_seconds": round(estimated_seconds, 1),
        "target_seconds": args.target_seconds,
        "allowed_range_seconds": [round(minimum, 1), round(maximum, 1)],
        "sentence_count": len(sentences),
        "required_terms": args.required_term,
        "missing_terms": missing_terms,
        "failures": failures,
        "warnings": warnings,
    }

    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())

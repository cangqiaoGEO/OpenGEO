#!/usr/bin/env python3
"""Validate an OpenGEO single-file site before it enters human review."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from typing import Any


PLACEHOLDERS = {
    "示例品牌": "仍包含模板品牌名",
    "【": "仍包含中文占位括号",
    "】": "仍包含中文占位括号",
    "※": "仍包含模板占位标记",
    "example.com": "仍包含示例域名",
    "000-000": "仍包含示例联系方式",
}
REQUIRED_SCHEMA_TYPES = {"Organization", "WebSite", "FAQPage"}


class SiteParser(HTMLParser):
    """Collect structural signals, visible text, metadata, and JSON-LD."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.h1_count = 0
        self.semantic_tags: set[str] = set()
        self.meta_description = ""
        self.title_parts: list[str] = []
        self.visible_parts: list[str] = []
        self.json_ld_parts: list[list[str]] = []
        self._hidden_depth = 0
        self._in_title = False
        self._in_json_ld = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "h1":
            self.h1_count += 1
        if tag in {"header", "main", "footer"}:
            self.semantic_tags.add(tag)
        if tag == "meta" and values.get("name", "").lower() == "description":
            self.meta_description = (values.get("content") or "").strip()
        if tag == "title":
            self._in_title = True
        if tag in {"style", "script"}:
            self._hidden_depth += 1
        if tag == "script" and values.get("type", "").lower() == "application/ld+json":
            self._in_json_ld = True
            self.json_ld_parts.append([])

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        if tag == "script" and self._in_json_ld:
            self._in_json_ld = False
        if tag in {"style", "script"}:
            self._hidden_depth = max(0, self._hidden_depth - 1)

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_parts.append(data)
        if self._in_json_ld and self.json_ld_parts:
            self.json_ld_parts[-1].append(data)
        if self._hidden_depth == 0:
            value = re.sub(r"\s+", " ", data).strip()
            if value:
                self.visible_parts.append(value)


def schema_nodes(value: Any) -> list[dict[str, Any]]:
    """Flatten top-level JSON-LD objects and @graph nodes."""

    if isinstance(value, list):
        result: list[dict[str, Any]] = []
        for item in value:
            result.extend(schema_nodes(item))
        return result
    if not isinstance(value, dict):
        return []
    result = [value]
    graph = value.get("@graph")
    if isinstance(graph, list):
        result.extend(item for item in graph if isinstance(item, dict))
    return result


def type_names(value: Any) -> set[str]:
    """Normalize a JSON-LD @type value."""

    if isinstance(value, str):
        return {value}
    if isinstance(value, list):
        return {item for item in value if isinstance(item, str)}
    return set()


def validate(path: Path) -> dict[str, Any]:
    """Return blocking errors and useful structural facts."""

    source = path.read_text(encoding="utf-8")
    parser = SiteParser()
    parser.feed(source)
    parser.close()

    errors: list[str] = []
    for marker, message in PLACEHOLDERS.items():
        if marker in source:
            errors.append(f"{message}: {marker}")

    title = re.sub(r"\s+", " ", "".join(parser.title_parts)).strip()
    if not title:
        errors.append("缺少非空 <title>")
    if not parser.meta_description:
        errors.append("缺少非空 meta description")
    if parser.h1_count != 1:
        errors.append(f"H1 必须恰好一个，当前 {parser.h1_count} 个")
    missing_semantic = {"header", "main", "footer"} - parser.semantic_tags
    if missing_semantic:
        errors.append("缺少语义标签: " + ", ".join(sorted(missing_semantic)))

    nodes: list[dict[str, Any]] = []
    for index, parts in enumerate(parser.json_ld_parts, start=1):
        raw = "".join(parts).strip()
        try:
            nodes.extend(schema_nodes(json.loads(raw)))
        except json.JSONDecodeError as exc:
            errors.append(f"第 {index} 个 JSON-LD 无效: {exc.msg}")

    present_types: set[str] = set()
    for node in nodes:
        present_types.update(type_names(node.get("@type")))
    missing_types = REQUIRED_SCHEMA_TYPES - present_types
    if missing_types:
        errors.append("缺少 JSON-LD 类型: " + ", ".join(sorted(missing_types)))

    visible = re.sub(r"\s+", "", " ".join(parser.visible_parts))
    faq_nodes = [node for node in nodes if "FAQPage" in type_names(node.get("@type"))]
    for faq in faq_nodes:
        entities = faq.get("mainEntity")
        if not isinstance(entities, list) or not entities:
            errors.append("FAQPage.mainEntity 必须为非空数组")
            continue
        for index, entity in enumerate(entities, start=1):
            if not isinstance(entity, dict):
                errors.append(f"FAQPage 第 {index} 项不是对象")
                continue
            question = entity.get("name")
            answer = entity.get("acceptedAnswer")
            answer_text = answer.get("text") if isinstance(answer, dict) else None
            if not isinstance(question, str) or not question.strip():
                errors.append(f"FAQPage 第 {index} 项缺少问题")
            elif re.sub(r"\s+", "", question) not in visible:
                errors.append(f"FAQPage 问题未出现在可见正文: {question}")
            if not isinstance(answer_text, str) or not answer_text.strip():
                errors.append(f"FAQPage 第 {index} 项缺少答案")
            elif re.sub(r"\s+", "", answer_text) not in visible:
                errors.append(f"FAQPage 答案未出现在可见正文: {question}")

    return {
        "valid": not errors,
        "path": str(path),
        "title": title,
        "h1_count": parser.h1_count,
        "schema_types": sorted(present_types),
        "errors": errors,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html", type=Path, help="待审单文件 HTML")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    path = args.html.expanduser().resolve()
    if not path.is_file():
        print(json.dumps({"valid": False, "errors": [f"找不到文件: {path}"]}, ensure_ascii=False, indent=2))
        return 2
    result = validate(path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

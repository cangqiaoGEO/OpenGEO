#!/usr/bin/env python3
"""Build the WorkBuddy GEO expert from repository-owned source files."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile
import zipfile


EXPERT_NAME = "geo-diagnostic-expert"
CORE_FILES = (
    "SKILL.md",
    "README.md",
    ".env.example",
    ".gitignore",
    "package.json",
    "package-lock.json",
)
CORE_DIRECTORIES = ("docs", "examples", "references", "schemas", "scripts")
TEXT_SUFFIXES = {"", ".json", ".md", ".mjs", ".ps1", ".py", ".sh", ".txt", ".yaml", ".yml"}
TOKEN_PATTERNS = (
    re.compile(r"ark-[A-Za-z0-9][A-Za-z0-9._-]{20,}"),
    re.compile(r"sk-sp-[A-Za-z0-9][A-Za-z0-9._-]{20,}"),
    re.compile(r"(?<![A-Za-z0-9])sk-[A-Za-z0-9][A-Za-z0-9._-]{20,}"),
)
ENV_ASSIGNMENT_PATTERN = re.compile(
    r"(?:export\s+)?(?:ARK_API_KEY|ARK_AGENT_PLAN_API_KEY|DASHSCOPE_API_KEY|"
    r"DEEPSEEK_API_KEY|TENCENT_TOKENHUB_API_KEY)[ \t]*=[ \t]*(?P<value>[^\s#]*)"
)
ALLOWED_PLACEHOLDER_VALUES = {"", "...", '"..."', "'...'"}


def get_module_root() -> Path:
    """Return the repository-owned brand-geo-audit module root."""

    return Path(__file__).resolve().parents[3]


def copy_tree_without_caches(source: Path, destination: Path) -> None:
    """Copy a runtime directory while excluding generated Python caches."""

    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
    )


def validate_template(template_root: Path) -> dict:
    """Validate the repository-owned expert template before assembly."""

    manifest_path = template_root / ".codebuddy-plugin" / "plugin.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("name") != EXPERT_NAME:
        raise ValueError(f"unexpected expert name: {manifest.get('name')!r}")
    expected_skills = {"./skills/brand-geo-audit", "./skills/geo-browser-runtime"}
    if set(manifest.get("skills", [])) != expected_skills:
        raise ValueError("plugin.json must declare the core and WorkBuddy runtime skills")
    for relative_path in manifest.get("agents", []):
        if not (template_root / relative_path).is_file():
            raise FileNotFoundError(f"missing agent source: {relative_path}")
    if not (template_root / "avatars" / "expert.png").is_file():
        raise FileNotFoundError("missing repository-owned expert avatar")
    return manifest


def copy_core_runtime(module_root: Path, expert_root: Path) -> Path:
    """Copy only publishable core runtime files into the assembled expert."""

    skill_root = expert_root / "skills" / "brand-geo-audit"
    skill_root.mkdir(parents=True, exist_ok=True)
    for name in CORE_FILES:
        shutil.copy2(module_root / name, skill_root / name)
    for name in CORE_DIRECTORIES:
        copy_tree_without_caches(module_root / name, skill_root / name)
    return skill_root


def find_secret_violations(expert_root: Path) -> list[str]:
    """Return publishable files containing likely real credentials."""

    violations: list[str] = []
    for path in sorted(expert_root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if any(pattern.search(text) for pattern in TOKEN_PATTERNS):
            violations.append(str(path.relative_to(expert_root)))
            continue
        for match in ENV_ASSIGNMENT_PATTERN.finditer(text):
            value = match.group("value").strip()
            if value not in ALLOWED_PLACEHOLDER_VALUES:
                violations.append(str(path.relative_to(expert_root)))
                break
    return violations


def validate_assembled_expert(expert_root: Path) -> None:
    """Check required package paths and reject credential leakage."""

    manifest = json.loads(
        (expert_root / ".codebuddy-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    for relative_path in (*manifest["agents"], *manifest["skills"]):
        path = expert_root / relative_path
        if not path.exists():
            raise FileNotFoundError(f"assembled expert is missing {relative_path}")
    for skill_path in manifest["skills"]:
        if not (expert_root / skill_path / "SKILL.md").is_file():
            raise FileNotFoundError(f"assembled skill has no SKILL.md: {skill_path}")
    violations = find_secret_violations(expert_root)
    if violations:
        joined = ", ".join(violations)
        raise ValueError(f"credential-like values found in assembled expert: {joined}")


def write_deterministic_zip(expert_root: Path, archive_path: Path) -> None:
    """Write a stable ZIP whose root directory is the expert name."""

    fixed_time = (2026, 1, 1, 0, 0, 0)
    temporary_archive = archive_path.with_suffix(".zip.tmp")
    with zipfile.ZipFile(temporary_archive, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(expert_root.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(expert_root)
            info = zipfile.ZipInfo(f"{EXPERT_NAME}/{relative.as_posix()}", fixed_time)
            info.compress_type = zipfile.ZIP_DEFLATED
            mode = path.stat().st_mode & 0o777
            info.external_attr = (stat.S_IFREG | mode) << 16
            archive.writestr(info, path.read_bytes())
    os.replace(temporary_archive, archive_path)


def build_expert(output_dir: Path) -> tuple[Path, Path]:
    """Assemble the expert directory and ZIP under a generated output path."""

    module_root = get_module_root()
    template_root = module_root / "adapters" / "workbuddy" / "expert"
    validate_template(template_root)
    output_dir.mkdir(parents=True, exist_ok=True)

    temporary_root = Path(tempfile.mkdtemp(prefix=f".{EXPERT_NAME}-", dir=output_dir))
    temporary_expert = temporary_root / EXPERT_NAME
    target_expert = output_dir / EXPERT_NAME
    target_archive = output_dir / f"{EXPERT_NAME}.zip"
    try:
        copy_tree_without_caches(template_root, temporary_expert)
        copy_core_runtime(module_root, temporary_expert)
        for script in (
            temporary_expert / "scripts" / "setup.sh",
            temporary_expert
            / "skills"
            / "geo-browser-runtime"
            / "scripts"
            / "ensure_runtime.sh",
        ):
            script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        validate_assembled_expert(temporary_expert)
        if target_expert.exists():
            shutil.rmtree(target_expert)
        os.replace(temporary_expert, target_expert)
        write_deterministic_zip(target_expert, target_archive)
    finally:
        shutil.rmtree(temporary_root, ignore_errors=True)
    return target_expert, target_archive


def parse_args() -> argparse.Namespace:
    """Parse build CLI arguments."""

    module_root = get_module_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=module_root / "work" / "mvp-release",
        help="Generated expert directory and ZIP destination",
    )
    return parser.parse_args()


def main() -> int:
    """Build and report the generated WorkBuddy expert artifacts."""

    args = parse_args()
    expert_dir, archive_path = build_expert(args.output_dir.expanduser().resolve())
    print(f"Built expert directory: {expert_dir}")
    print(f"Built expert archive: {archive_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

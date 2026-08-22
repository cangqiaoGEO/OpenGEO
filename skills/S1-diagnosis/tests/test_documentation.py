from pathlib import Path
import re
import unittest


MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


class DocumentationLinkTests(unittest.TestCase):
    """Verify that repository-local Markdown links resolve from their source files."""

    def test_local_markdown_links_resolve(self):
        module_root = Path(__file__).resolve().parents[1]
        broken_links = []
        for document in sorted(module_root.rglob("*.md")):
            if "node_modules" in document.parts or "work" in document.parts:
                continue
            text = document.read_text(encoding="utf-8")
            for target in MARKDOWN_LINK_PATTERN.findall(text):
                if target.startswith(("http://", "https://", "#")):
                    continue
                local_target = target.split("#", 1)[0]
                if not local_target:
                    continue
                resolved = (document.parent / local_target).resolve()
                if not resolved.exists():
                    broken_links.append(f"{document.relative_to(module_root)} -> {target}")
        self.assertEqual([], broken_links)


if __name__ == "__main__":
    unittest.main()

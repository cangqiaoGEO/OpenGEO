from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from validate_site import validate  # noqa: E402


VALID_SITE = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>云帆科技 - 数据治理服务</title>
  <meta name="description" content="云帆科技提供数据治理服务。">
  <script type="application/ld+json">
  {"@context":"https://schema.org","@graph":[
    {"@type":"Organization","name":"云帆科技"},
    {"@type":"WebSite","name":"云帆科技官网","url":"https://yunfan.invalid"},
    {"@type":"FAQPage","mainEntity":[{"@type":"Question","name":"提供什么服务？","acceptedAnswer":{"@type":"Answer","text":"提供数据治理服务。"}}]}
  ]}
  </script>
</head>
<body>
  <header>云帆科技</header>
  <main><h1>数据治理服务</h1><section><h2>常见问题</h2><h3>提供什么服务？</h3><p>提供数据治理服务。</p></section></main>
  <footer>联系我们</footer>
</body>
</html>"""


class ValidateSiteTest(unittest.TestCase):
    def write(self, content: str) -> Path:
        temporary = tempfile.NamedTemporaryFile("w", suffix=".html", encoding="utf-8", delete=False)
        self.addCleanup(lambda: Path(temporary.name).unlink(missing_ok=True))
        with temporary:
            temporary.write(content)
        return Path(temporary.name)

    def test_valid_site_passes(self) -> None:
        result = validate(self.write(VALID_SITE))
        self.assertTrue(result["valid"], result)
        self.assertEqual(1, result["h1_count"])
        self.assertEqual({"FAQPage", "Organization", "WebSite"}, set(result["schema_types"]))

    def test_template_placeholders_and_structure_errors_fail(self) -> None:
        broken = VALID_SITE.replace("云帆科技", "示例品牌").replace("<h1>", "<h1>重复</h1><h1>", 1)
        result = validate(self.write(broken))
        self.assertFalse(result["valid"])
        self.assertIn("仍包含模板品牌名", " ".join(result["errors"]))
        self.assertIn("H1 必须恰好一个", " ".join(result["errors"]))

    def test_faq_json_ld_must_match_visible_copy(self) -> None:
        broken = VALID_SITE.replace("提供数据治理服务。</p>", "提供数据分析服务。</p>")
        result = validate(self.write(broken))
        self.assertFalse(result["valid"])
        self.assertIn("FAQPage 答案未出现在可见正文", " ".join(result["errors"]))


if __name__ == "__main__":
    unittest.main()

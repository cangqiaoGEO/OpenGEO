#!/usr/bin/env python3
"""内部链接检查：校验仓库内 markdown 相对链接指向存在的文件。

只查相对路径链接（跳过 http(s)/mailto/锚点/绝对路径），零依赖。
用法：python3 tools/check_links.py [根目录，默认当前目录]
退出码：0 = 通过；1 = 存在断链（逐条列出）。
"""
import os
import re
import sys
import urllib.parse

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "dist", "build"}


def main(root: str) -> int:
    broken = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if not name.endswith(".md"):
                continue
            path = os.path.join(dirpath, name)
            try:
                text = open(path, encoding="utf-8").read()
            except OSError:
                continue
            # 跳过围栏代码块，避免把示例代码里的伪链接当真
            text = re.sub(r"```.*?```", "", text, flags=re.S)
            for m in LINK_RE.finditer(text):
                target = m.group(1)
                if target.startswith(("http://", "https://", "mailto:", "#", "/", "tel:")):
                    continue
                target = urllib.parse.unquote(target.split("#", 1)[0])
                if not target:
                    continue
                resolved = os.path.normpath(os.path.join(dirpath, target))
                if not os.path.exists(resolved):
                    rel = os.path.relpath(path, root)
                    broken.append(f"{rel}: ({m.group(1)}) -> {os.path.relpath(resolved, root)}")
    if broken:
        print(f"断链 {len(broken)} 条：")
        for line in broken:
            print("  " + line)
        return 1
    print("内部链接检查通过")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "."))

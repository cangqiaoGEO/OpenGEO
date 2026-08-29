# CLAUDE.md — OpenGEO 门户仓

本仓是 OpenGEO 组织门户：课程 + 治理 + 术层教学。不放代码实现（在层仓库），不放技能副本（D2 决议：迁出不留副本，对照 MIGRATION.md）。

## 研发流程

按 [docs/ai-native-sdlc.md](docs/ai-native-sdlc.md) 执行：任务先写 intent（目标/约束/影响/待确认）；指标、schema、引擎、IF 接口变更走 RFC。对外发布（公众号/官网/客户交付）是 L3 动作，放行人为课程运营。

## 目录

- `coursebook/` 详解版课程（mkdocs 源码，8 章 + 附录 + SVG 图解）；`textbook/` 单文件学员教材；`teambook/` 内部图解教材（mkdocs）
- `guides/` 避坑指南 + 选型评分卡；`docs/` 已构建站点 + 权威文档（six-repo-plan / dual-engine-architecture / ai-native-sdlc / positioning）
- `GOVERNANCE.md` 治理宪章（口径宪章、RFC 流程、open-core 边界、L3 放行人、账号基建分层立场）

## 命令

```bash
# mkdocs 本地预览（venv 在 scratchpad/.venv，易被清，重建即可）
python3 -m venv .venv && .venv/bin/pip install mkdocs-material
.venv/bin/mkdocs serve -f teambook/mkdocs.yml
# 内部断链检查（CI 同款）
python3 tools/check_links.py
```

## 约定

- 全仓中文写作；文档许可 CC BY-SA 4.0（LICENSE-docs.md），代码 MIT
- 口径红线：三不承诺（不承诺排名第一/不承诺被所有 AI 推荐/不承诺统一见效天数）；任何「保排名」语义的文案拒收
- 永不发布服务商推荐榜单（中立性条款）；服务商评估只指向 guides/geo-vendor-scorecard.md
- 课程内容引用事实须给出处；效果数据若来自销售口径必须标注

## 常见错误

- 不要把技能/规范写回本仓——去 opengeo-skills / opengeo-spec（同错已犯过，见 restructure v2）
- teambook/coursebook 是 mkdocs 站点源码：站内相对链接按构建后 URL 解析，跨站引用用完整 GitHub URL
- 引用六层仓库术语时对齐口径：可见度/竞对份额/检索扩散(fan-out)/引用来源/机会点

## 验证

改动后跑 `python3 tools/check_links.py`（CI 强制）；治理/宪章文案变更须维护者批准后合并。

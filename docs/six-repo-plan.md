# OpenGEO 组织六仓并行建设方案（V1.1 · 2026-08-23 评审通过）

> 前提：团队 9 人，前期全部由仓桥智能投入，按评审决议先建 L0 / L1 / L3；组织 github.com/cangqiaoGEO 已按六层建好 6 个仓库 + 组织资料页，OpenGEO 主仓改为「组织门户 + 课程 + 治理」。
> 评审结论：D1 先 L0/L1/L3；D2 主仓不保留副本（已删除）；D3 匿名哈希默认、可选实名；D4 Cloud 不进开源（open-core）；D5 双周 release note 同步公众号/知乎。以下分工与里程碑已按结论调整。

## 一、组织仓库架构（已落地）

| 层 | 仓库 | 已迁入资产 | 新建内容 |
| --- | --- | --- | --- |
| 门户 | **OpenGEO** | 初衷 README、口径宪章、详解教程（coursebook/docs）、避坑指南、官网 docs/ | GOVERNANCE.md、仓库地图、贡献入口 |
| L0 | **opengeo-spec** | brand-facts（SPEC-L1、模板、仓桥 bundle） | README、lint 路线图 |
| L1 | **opengeo-audit** | brand-geo-audit 技能（指标+评分+报告脚本）、geo-weekly-monitor、S7 规格 | 自动采集器路线图 |
| L2 | **opengeo-insights** | geo-intent-words 技能、S2/S6 规格 | 地基体检脚本、内容差距、爬虫观测路线图 |
| L3 | **opengeo-skills** | S3/S4/S5、orchestrator、automation、architecture、WorkBuddy 实现 | 平台实现贡献规范 |
| L4 | **opengeo-agentready** | 仓桥官网 JSON-LD 示例 | 生成器规划（llms.txt / JSON-LD / FAQ / AI 轻量页 / 公众号适配） |
| L5 | **opengeo-index** | 仓桥基线记录 | 数据 schema v0.1、聚合与基准页路线图 |
| — | **.github** | 组织资料页 | 六层仓库地图 + 口径宪章 |

依赖方向：spec → audit / insights / skills / agentready → index；audit 的复测结果回写 spec（verified 事件）——这是「复测闭环」在仓库层面的体现。

## 二、9 人分工（第一批 L0 / L1 / L3 + 门户，L2 / L4 / L5 为第二批）

| 角色 | 人数 | 仓库 | 本月交付（可验收） |
| --- | --- | --- | --- |
| 统筹 / 维护者 | 1 | 全部 + OpenGEO | GOVERNANCE/RFC 已落地；周例会；跨仓 issue 看板；双周 release note（GitHub + 公众号 + 知乎） |
| 规范 L0 | 1 | opengeo-spec | lint v0.2（过期 / draft 积压 / 断链 / 口径冲突）；3 个行业 type 词表；仓桥 bundle 转 stable |
| 测量 L1 | 3 | opengeo-audit | **自动采集器 v0.3**（豆包 / 元宝 / DeepSeek 自有账号低频采集，20 问一键出报告）；竞品对标表；仓桥每周一复测；为第二批 index 预留 30 品牌采集 |
| 执行 L3 | 3 | opengeo-skills | WorkBuddy 七技全部实测通关并回写提示词；Claude Code 实现；飞书待审区审批流模板；交付侧生产使用 |
| 课程 / 运营 | 1 | OpenGEO 门户 | 课程站维护、避坑指南更新、公开课承接、社群运营、release note 配图与分发 |

> 第二批（L2 insights / L4 agentready / L5 index）：仅保留 README 与路线图、接受社区 issue；第一批 W6 里程碑达成后，从 L1 / L3 各抽 1 人启动。

## 三、里程碑（12 周）

| 周 | 里程碑 | 验收 |
| --- | --- | --- |
| W1–2 | 三仓 issue 模板 / CI 骨架 / good-first-issue；仓桥 bundle stable 化；主仓门户化完成（已完成） | 各仓 ≥5 个 issue，组织页上线 |
| W3–6 | audit 采集器跑通 3 引擎；skills WorkBuddy 七技通关；spec lint 跑在 CI | 仓桥复测用采集器自动出报告；周报自动生成 |
| W7–10 | 第二批启动：agentready 两个生成器、insights 地基脚本、index 首批 30 品牌（匿名哈希） | 基准表可查；Claude Code 实现发布 |
| W11–12 | OpenGEO Cloud MVP（仓桥商业产品，不进组织）；组织 v0.5；首份《杭州 AI 可见度基准》 | 对外发布 + 课程第二期用基准数据 |

## 四、验收口径（对齐口径宪章）

- 每个仓库 README 必须回答：对标谁、中国差异在哪、输入输出是什么、下一版做什么；
- 任何指标变更走 RFC（spec / audit）；任何「保排名」语义的功能或文案拒收；
- 采集器合规：仅自有账号、低频、遵守平台条款、不绕过验证；采集失败宁可人工。

## 五、评审决策点

| # | 决策 | 建议 |
| --- | --- | --- |
| D1 | 六仓并行还是先 L0/L1/L3 | ✅ **先 L0/L1/L3**，L2/L4/L5 第二批 |
| D2 | 主仓是否保留 skills/brand-facts 副本 | ✅ **不保留**（已删除，链接全部指向层仓库） |
| D3 | Index 数据实名策略 | ✅ 默认匿名哈希，品牌方可选实名（已写入 index README/SCHEMA） |
| D4 | Cloud 托管版是否进开源组织 | ✅ 不进，open-core（已写入 GOVERNANCE） |
| D5 | 对外发布节奏 | ✅ 双周 release note，GitHub Releases + 公众号 + 知乎（已写入 GOVERNANCE） |

## 六、执行进度（2026-08-23）

**W1–2 骨架：已完成。**
- 三仓 CI 全绿：spec `okf-lint`（pytest + 示例 bundle lint）、audit `tests`（131 passed）、skills `validate-skills`
- issue / PR 模板、三阶段里程碑、19 个首批 issue（含 good-first-issue）
- 仓桥 bundle 通过 lint v0.3（0 errors / 0 warnings）：verified 规范化、无依据的 stable 回退 draft、孤页入 index

**W3–6 已提前落地（可离线部分）：**
- spec：lint v0.3（W105 index 覆盖率、价格/时长冲突、`--format json`）、RFC-0001 verified 前缀枚举、evidence sources 示例、行业词表 ×3
- audit：`run_audit.py` 一键流水线（回写 bundle diagnosis/，experimental_score 强制带改进清单）、`brand_compare.py` 对标表、`docs/SCHEMAS.md` 自动生成、周测 cron 脚本与文档
- skills：事实引用门禁（只引用 stable + human: verified）、S2/S7 指引页、Claude Code 安装脚本、飞书审批流模板、automation lint 门禁

**待人工 / 自有账号的事项（不可由 Agent 代做）：**
| 仓库 | issue | 需要谁 |
| --- | --- | --- |
| spec | #1 channels / intent-words 转 stable | 老板核对 |
| spec | #2 RFC-0001 批准 | ≥2 维护者 |
| audit | #1–#3 豆包 / 元宝 / DeepSeek 采集器实测 | 测量层（自有账号、可见浏览器） |
| skills | #1 WorkBuddy 七技通关、#2 Claude Code 实测 S3 | 执行层 |

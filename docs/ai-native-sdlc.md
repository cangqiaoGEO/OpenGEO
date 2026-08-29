# OpenGEO AI 原生研发流程（v1 · 2026-08-29 拍板）

> 把 Anthropic《The AI-Native SDLC Playbook》落进 OpenGEO 组织（9 人 · 8 仓 · [双引擎架构](dual-engine-architecture.md)）。
> 原则：**对齐补缺，不推倒重来**——OpenGEO 已是 markdown 产物链组织（Bundle 单向环流 ≈ artifact chain、RFC ≈ spec、lint/validate/pytest ≈ evals、S7 周测 ≈ Maintain 闭环），本流程把既有实践升格为六阶段闭环 + 三层控制面，重心是**把控制面从提醒升格为门禁**。
>
> 依据：Anthropic《AI-Native SDLC Playbook》（2026-08-21）与《How Anthropic secures its AI-native SDLC》（2026-07-21）、OpenAI《Building an AI-native engineering team》、Addy Osmani《Agentic Code Review》（2026-06-16）。

## 拍板决议（2026-08-29）

1. **L3 放行人指名**：生产部署 → **统筹/维护者**；对外发布（公众号/官网/客户交付）→ **课程运营**；灰度账号操作 → **服务实体负责人**。
2. **双试点链**：pandasofa 内容链（intent→内容→发布→归因）+ opengeo-matrix 中文 provider 开发链（工程线）。
3. **本文档对外可见**，作为组织研发流程的权威记录；变更走 PR + 维护者批准。

---

## 一、六阶段（代码线与内容线统一适用）

OpenGEO 的「生产」有两种：**代码生产**（8 仓功能开发）与**内容生产**（客户 Bundle 的诊断-内容-发布-归因）。六阶段对两条线统一适用，产物不同而已。每阶段给下游留一份能读、能追、算数的产物。

### 1. Plan —— 意图先行（产物：intent.md）

凡要动手的任务先有 intent：**目标 / 约束 / 影响范围 / 待确认**四段，两百字即可。代码线放 `<repo>/intents/` 或 issue 模板；客户口头需求整理成 intent 进 Bundle（接 BUNDLE 环流最上游）。**待确认没关掉不开工。**

- Delegate：Claude 从口头需求/群聊整理 intent 草稿、对照仓库标影响面
- Review：提出人确认四段完整、待确认项指了 Owner
- Own：优先级与要不要做——统筹

### 2. Design —— 轻重分流（产物：spec 段 / RFC）

沿用现行 RFC 分界并扩展到 matrix：指标、schema、引擎适配、IF-A~D 接口变更必须走 RFC（≥2 维护者批准，已是制度）；普通功能在 intent 里追加 spec 段（方案 + 取舍 + 验证方式）即可。

- Delegate：Claude 读代码/历史 RFC 给候选方案与依赖图
- Review：层 Owner 查完整性与风险
- Own：口径语义、迁移风险、长期取舍——层 Owner（RFC 时 + 2 维护者）

### 3. Build —— Plan Mode 默认 + 八仓工作手册（产物：plan + diff + tests）

工程任务一律 Plan Mode 起步（带 intent + spec），计划批准后才切执行。八仓各一份 CLAUDE.md（构建命令 / 约定 / 常见错误 / 验证步骤四节起步；matrix 在 postiz 上游版之上叠 OpenGEO 层：AGPL 边界、IF-D 契约、术语表）。**Claude 同一个错犯第二次，当天进 CLAUDE.md。**

- Delegate：找链路 / 改代码 / 补测试 / 跑检查 / 写 PR 说明
- Review：工程师审计划与 diff，不逐行手写
- Own：新抽象、跨仓变更、含糊需求——工程师

### 4. Test —— 评测门禁全仓覆盖（产物：CI 绿 + eval 套件）

既有门禁脚本全部升 CI（spec `okf_lint`、skills `validate_skills` 已在；OpenGEO / agentready / index / bundle 仓补最小 CI：链接检查 + schema 校验 + lint）。**修 bug 先写会失败的测试；agent 不得修改测试文件迁就实现**（测试与实现分会话生成）。CLAUDE.md / SKILL.md / 宪章文案变更必须跑对应 eval——宪章回归样本制度（同输入应复现同分数）落进 CI 触发。

- Delegate：Claude 生成测试初稿、自迭代到绿
- Review：工程师**重点读测试变更**（agent 会改断言迁就坏行为——比读实现更仔细）
- Own：覆盖率与边界案例对齐——各层 Owner

### 5. Review / Deploy —— 风险分层放行（产物：带发现的 PR + 审批痕迹）

每仓一份 `REVIEW.md` 定义 AI 评审 pass（正确性 / 安全 / 口径合规 / AGPL 供应链）；branch protection 全仓（main 必须 PR + Owner 批准）。按出错代价四层放行：

| 层 | 覆盖 | 放行方式 |
| --- | --- | --- |
| L0 | 格式 / lint / schema / 断链 | 确定性工具，CI 自动 |
| L1 | 常规代码与内容改动 | AI 初审给 severity，人看 Important 以上、抽样其余 |
| L2 | stable 事实变更、指标口径、RFC、六维权重、客户报告 | 层 Owner 深审 |
| L3 | 生产部署 / 对外发布 / 灰度账号操作 | **指名放行人**（见拍板决议），hook 强制 |

新引入的 AI Reviewer 先 **Shadow Mode 两周**（只评论不拦截），统计误报漏报再放权。**谁点合并谁负责。**

### 6. Maintain —— 周测即监控，跌分即工单（产物：事故记录 → 新 intent + eval）

OpenGEO 的「生产监控」= S7 周测与 matrix 运行态。闭环自动化：**客户可见度跌出预设区间 / 归因判决连续 ❌ / matrix 账号授权失效或发布失败** → 确定性脚本聚合日志与变更（不过模型）→ Claude 起草诊断型 intent.md → 进 triage 队列 → 按 Plan 阶段重新入链。**每次事故收尾必加一条 eval 防复发。**

- Delegate：诊断 agent 只读——读日志 / 关联提交 / 给根因假设
- Review：人核对诊断、决定回滚或修复
- Own：敏感生产操作与最终放行——指名放行人

---

## 二、控制面三层（本流程的重心）

| 层 | 落点 | 说明 |
| --- | --- | --- |
| **CLAUDE.md** | 8 仓各一份 | 每日工作手册：命令 / 约定 / 常见错误 / 验证步骤；同错二犯进手册 |
| **Skills（政策即代码）** | `.claude/skills/` 组织技能包 `opengeo-policy` | 口径宪章、白帽红线、事实引用门禁 5 条、对客表述红线、发布前三查、AGPL 供应链检查——从提示词收进版本控制的技能，变更须层 Owner sign-off |
| **Hooks（不可绕过的门禁）** | `.claude/settings.json` | ① **stable 事实保护**：`facts/` 中 `status: stable` 文件被 agent 编辑 → 询问/阻断，须 Owner 确认（对应 RFC-0001 `human:` 前缀）；② **生产与发布 gate**：L3 动作走指名放行人；③ **测试文件保护**：修 bug 会话禁改 `tests/`；④ **灰度隔离**：matrix 仓阻断任何账号自动化路径写入 |

## 三、Agent 身份与权限（委派不提权）

| Agent | 可以 | 不可以 |
| --- | --- | --- |
| 总控/团长（orchestrator） | 读 Bundle 全树、派活七技、写周报四段式 | 直接改 stable 事实、直接发布、合并 PR |
| 诊断/采集（S1/S7、collectors） | 跑采集、算分、写 `reports/` | 改内容与事实；对外发送任何东西 |
| 内容生产（S2–S5、matrix AI 创作台） | 写 `content/drafts/`、起草发布包 | 写 `approved/`（须人审）、触发实际发布 |
| 发布执行（matrix 发布中心） | 发 approved 内容到已授权账号、回写 publish_record | 发未 approved 内容；账号授权之外的平台操作 |

**委派规则**：agent 请求另一个 agent 做自己无权做的事，按**发起方**的权限与审批等级执行——委派不提权，跨 agent 动作过人审 gate（飞书审批流）。所有自动批准留决策理由、可追溯，每月抽样复审。

## 四、9 人角色（Delegate / Review / Own）

| 角色 | Delegate 给 agent | Review | Own |
| --- | --- | --- | --- |
| 统筹/维护者 ×1 | 周报聚合、跨仓 issue、release note 初稿 | triage 队列、RFC 终审 | 优先级、治理、**生产放行** |
| 规范 L0 ×1 | lint 规则草稿、schema 迁移 diff | IF-A~D 与 RFC 完整性 | 口径语义、字段取舍 |
| 测量 ×3 | 采集器适配、报表、诊断初稿 | 算分正确性、双引擎归因联表 | 指标宪章执行、回归样本 |
| 执行 ×3 | 内容初稿、provider 适配、测试初稿 | 测试变更、发布包三查 | provider 架构、八要素口径 |
| 课程/运营 ×1 | 课件、公众号排版、社群 FAQ | 对外文案合规 | **对外发布放行** |

共同纪律：不逐行读全部 diff（按四层看）；谁点合并谁负责；每人每周至少送一条「Claude 二犯错误」进 CLAUDE.md。

## 五、度量（不数 AI 写了多少，数链条顺不顺）

| 阶段 | 前导 | 滞后 |
| --- | --- | --- |
| Plan/Design | 口头需求→intent 提交时长（目标当天） | 开工后需求返工次数 |
| Build/Test | agent PR 的 CI 首次通过率 | 每 PR 返工轮次、plan 漂移 |
| Review | PR 首评时长（目标分钟级） | 逃逸缺陷 vs 拦下缺陷之比 |
| Maintain | 跌分/事故→intent 进 triage 时长 | **同类事故复发率**（应趋降） |
| 内容线 | intent→首篇 approved 时长 | 归因判决 ✅ 占比 |

## 六、30 / 60 / 90（双试点链：pandasofa 内容链 + matrix provider 链）

- **D0–30 补基建 + 试点跑通**：8 仓 CLAUDE.md 补齐/改造；4 裸仓最小 CI；hook ①③ 落地；pandasofa 链按六阶段完整走一遍，记录卡点。
- **D31–60 评审与政策上线**：REVIEW.md + claude-code-action 推广 spec/skills/matrix（Shadow 两周后放权 L1）；branch protection 全仓；`opengeo-policy` 技能包成形；agent 权限进治理 + 飞书 gate 接通发布动作。
- **D61–90 闭环 + 看板**：跌分→intent 的 headless 链路上线；每事故一 eval 成验收项；度量进统筹周会看板；复盘双试点链，决定扩大范围。

三条纪律自第一天生效：① L3 动作最后开放；② 新 AI 能力一律 Shadow 先行；③ 自动批准留理由、月度抽样复审。

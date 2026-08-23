# OpenGEO 团队内部调研报告：从小米类比到六层架构（全员学习手册）

> 受众：仓桥智能全体 9 人 ｜ 用途：内部宣讲（40 分钟）+ 自学手册（1 周） ｜ 版本：V1.0 · 2026-08-23
> 配套：简明图解教程 https://cangqiaogeo.github.io/OpenGEO/learn/ ；评审稿《六仓并行建设方案 V1.1》；GOVERNANCE.md
> 一句话：**我们不是在做一家 GEO 服务商，我们是在给一个正在「华强北化」的市场建一把尺子——尺子归开源组织，手艺归仓桥。**

---

## 第一部分｜宣讲：为什么是现在，为什么是我们（15 分钟）

### 1.1 历史不重复，结构会重复

| 移动互联网 | Agent 时代 | 我们在哪一格 |
| --- | --- | --- |
| 2007 初代 iPhone：范式出现 | 2022-11 ChatGPT：范式出现 | — |
| 2010-06 iPhone 4 + Android 2.2：体验成熟 | 2025 Claude Code / WorkBuddy / 开源 Agent：体验成熟 | — |
| 2011–2013 千元机普及，移动互联网成默认 | 2026 Agent 进入办公场景（判断，非事实） | **现在** |
| 2011 安兔兔上线：智能机有了「可比较」 | 2026 OpenGEO Index：品牌 AI 可见度有了「可比较」 | **我们要做的** |

结构性的五步：**新入口出现 → 渗透拐点 → 攒机/攒课零门槛 → 信息差横行 → 度量工具出现，市场重新定价。** 2010 年的华强北和 2026 年的 GEO 市场都走到了第四步，第五步就是我们的位置。

### 1.2 GEO 市场 = 2010 年的华强北（证据在我们自己手里）

- 真需求：AI 用户 6.02 亿、渗透 53%（对外引用时补来源）；企业获客入口正在迁移；
- 攒课零门槛：「N 小时讲透」满街都是（竞品分析 2026-08）；
- 参数虚标：「保排名」「保推荐位」——AI 推荐机制下不可承诺；
- 无售后：交付即结束，不复测；
- **我们自己的基线实测**：搜「杭州 GEO 哪家好」，结果全是服务商自荐软文——这就是华强北的柜台。

### 1.3 山寨机是怎么死的，我们要复制哪一条

| 死因 | 小米/行业做了什么 | 我们的对应（按六层架构） |
| --- | --- | --- |
| 信息差被打穿 | 公开 BOM 逻辑定价 | **L0 品牌事实库**：每条卖点答得出谁写的、谁核的、过没过期 + 口径宪章 |
| 不可比较 → 可比较 | 安兔兔跑分 | **L1 诊断 + L5 OpenGEO Index**：单品牌六维分数 + 行业 × 城市 × 引擎公开榜 |
| 正规军降维打击 | MIUI 先行、铁人三项 | **L3/L4 开源执行层**是给全行业的 MIUI；**培训 × 交付 × Cloud** 是仓桥自己的铁人三项 |

最重要的一条：**山寨机不是被「更便宜」杀死的，是被「可比较」杀死的。** 所以我们的核心资产不是某个 Skill，而是「让市场可度量」的整套开源层。

### 1.4 宣讲稿里没讲的另一半：安兔兔的教训

1. 安兔兔被视为「小米系」，长期背负「偏向小米」的质疑——**选手持股的裁判，分数会被折价**；
2. 2013、2018 年多家大厂被曝跑分作弊——**度量一旦成为权力，就会被优化到失真**；
3. 单一总分的权威后来被多元指标分流——**分数的心智红利有有效期**。

我们对应的三道防线（都已经写进仓库，不是口号）：

- 裁判进开源组织：测量（L1）与基准（L5）归 OpenGEO，仓桥只做交付与 Cloud（GOVERNANCE「商业边界」）；指标权重变更走 RFC、≥2 维护者批准；
- 防作弊：题集双轨（公开 20 问做纵向复测、隐藏题集做横向基准）、引用源质量维度对低质信源打折、采集只用自有账号可见浏览器、index 数据异常波动标记；
- 不迷信总分：brand-geo-audit 默认 `diagnostic` 模式不发布总分；`experimental_score` 必须附经验证的改进清单并标注「experimental M1，不构成行业标准」。

### 1.5 两个主语，别混

| 主语 | 打的牌 | 赚不赚钱 |
| --- | --- | --- |
| **OpenGEO（组织）** | 规范 L0 · 测量 L1 · 洞察 L2 · 执行层 L3 · 站点 L4 · 基准 L5 | 不赚钱，赚采用率与话语权 |
| **仓桥（公司）** | 培训 · 代运营交付 · OpenGEO Cloud 托管（open-core） | 赚钱，靠开源层降低获客与交付成本 |

对外说话时：讲标准用「OpenGEO」，讲服务用「仓桥」。**行业基准对外名称统一为 OpenGEO Index / OpenGEO 可见度指数**（「及兔兔」只做内部代号）。

### 1.6 宣讲结尾的三句话（修订版）

1. 雷军进手机业时也不是手机人——跨界者带着成熟武器进场，恰恰是清场者的标准画像；
2. 山寨死于跑分，割韭菜死于复测——我们先测了自己、先亮了 18 分；
3. 别人卖信息差，我们卖确定性——**2026 年，轮到一个可度量的标准了。**

---

## 第二部分｜OpenGEO 架构深度解析（15 分钟宣讲 + 自学）

### 2.1 一张图

```
                 ┌──────────────────────── 门户 OpenGEO ────────────────────────┐
                 │   初衷 · 口径宪章 · GOVERNANCE/RFC · 详解教程 · 避坑指南 · 官网    │
                 └──────────────────────────────────────────────────────────────┘
  L0 规范  opengeo-spec        品牌事实库 OKF（唯一事实源）＋ okf_lint ＋ 行业词表
        │  依赖方向 ↓（所有层只准引用 spec 里 stable + human: verified 的事实）
  L1 测量  opengeo-audit       brand-geo-audit 六维诊断 · run_audit 流水线 · 周测 ──┐
  L2 洞察  opengeo-insights    意图词 · 内容差距 · 竞品对标 · 官网地基体检            │ 复测结果
  L3 执行  opengeo-skills      七技规格 · 总控 Agent · 自动化 · WorkBuddy/Claude Code │ 回写 spec
  L4 站点  opengeo-agentready  llms.txt / JSON-LD / FAQ / AI 可读页面生成            │ diagnosis/
  L5 基准  opengeo-index       OpenGEO Index：行业 × 城市 × 引擎公开基准 ◄───────────┘
```

**闭环**：spec 定口径 → insights 出题与差距 → skills 生产 → agentready 上站 → audit 复测 → 结果回写 spec（`verified: tool:`）→ index 聚合成行业基准。与市面「GEO Agent」的区别一句话：别人止于生成方案，我们闭环到复测分数。

### 2.2 逐层解析（做什么 / 输入输出 / 现状 / 对标 / 谁负责）

#### L0 · opengeo-spec（规范层）— 第一批
- **做什么**：品牌事实库 OKF L1 规范（六个字段：type/title/description/status/generated/verified + sources）、模板、真实示例（仓桥 bundle）、行业词表 ×3、lint 工具。
- **输入/输出**：输入公司资料与老板确认；输出一棵 markdown 目录树，每个文件 frontmatter 标明状态与信任级。
- **关键概念**：`status`（draft 未审不得引用 / stable / deprecated）；`verified.by` 三级信任 `human:`（人确认）> `tool:`（确定性脚本）> `machine:`（自动核验）（RFC-0001）。
- **现状**：lint v0.3（10 条规则，`--format json`），CI 每次 push 对示例 bundle 跑 lint，当前 0 errors / 0 warnings；RFC-0001 待批准。
- **对标**：无直接对标，这是我们独创的层；海外五家都没有「事实源」概念，这是中国市场（口径混乱、多平台）逼出来的。
- **负责**：规范 1 人。

#### L1 · opengeo-audit（测量层）— 第一批
- **做什么**：六维诊断（可见度 30 / 推荐度 20 / 引用源 15 / 覆盖度 15 / 情感 10 / 内容基础 10）× 多引擎；周测；一键流水线；多品牌对标。
- **链路**：research package（冻结题集与范围）→ 采集（browser_collect / api_collect，自有账号）→ evidence package（evidence_validate 校验）→ geo_score（确定性）→ quality_audit → recommendations → geo_report（HTML）→ `run_audit.py` 回写 bundle `diagnosis/`。
- **现状**：131 个测试；18 个 JSON Schema（docs/SCHEMAS.md）；方法学成熟度 experimental M1；**自动采集器三引擎待实测**（issue #1–#3）。
- **对标**：Profound Monitor / Peec。差异：中国引擎无 API、必须自有账号低频采集；我们开源评分脚本，他们闭源。
- **负责**：测量 3 人。

#### L2 · opengeo-insights（洞察层）— 第二批
- **做什么**：三层意图词（场景攻略 50 / 品牌对比 30 / 口碑验证 20）、内容差距（audit 引用源 vs bundle 覆盖）、竞品对标、官网地基 7 条体检（可访问 / 可抓取 / 不锁图 / sitemap / 统一名 / FAQ 页 / 联系入口）。
- **现状**：geo-intent-words 与 S6-website-foundation 两个完整技能已迁入；自动化脚本待第二批。
- **对标**：Scrunch Insights。

#### L3 · opengeo-skills（执行层）— 第一批
- **做什么**：七技规格（S1–S7）、总控 Agent（orchestrator）、自动化模板（daily-content / weekly-audit / 飞书审批流）、平台实现（WorkBuddy v1 参考实现，Claude Code 安装脚本）。
- **硬规则**：事实引用门禁——只读 stable 且 human: verified 的事实；引用附来源；未确认信息只能进「待确认」段；执行前先跑 lint。
- **现状**：S3/S4/S5 在本仓，S1/S7 指向 audit，S2/S6 指向 insights；CI 校验 SKILL.md frontmatter、断链、违宪文案。
- **对标**：Profound Agents / Frase。差异：我们是平台无关的提示词规格 + 开源。
- **负责**：执行 3 人。

#### L4 · opengeo-agentready（站点层）— 第二批
- **做什么**：从 bundle 生成 llms.txt、JSON-LD（Organization / FAQPage）、FAQ 页、AI 轻量页；公众号适配。
- **现状**：仓桥官网 JSON-LD 示例；生成器规划中。
- **对标**：Scrunch AXP。

#### L5 · opengeo-index（基准层）— 第二批
- **做什么**：**OpenGEO Index（可见度指数）**：行业 × 城市 × 引擎的公开可见度基准；默认匿名哈希，品牌方可 PR 实名认领。
- **现状**：schema v0.1、仓桥基线一条记录；首批 30 品牌待 audit 采集器就绪后启动。
- **对标**：Profound Index。

#### 门户 · OpenGEO
- README（初衷 + 口径宪章 + 仓库地图）、GOVERNANCE（不可协商条款、角色、RFC、建设顺序、商业边界、隐私、发布节奏）、MIGRATION、课程站、避坑指南、官网。

### 2.3 治理要点（每个人都要会背）

- **三不承诺**：不承诺排名第一 / 不承诺被所有 AI 推荐 / 不承诺统一见效天数；**三只承诺**：诊断分数 / 改进清单 / 复测对比；六条白帽红线。
- **RFC 触发**：spec 字段、audit 指标权重、新引擎适配、index schema —— 四类变更先提 `rfcs/`。
- **建设顺序**：先 L0/L1/L3，第二批 L2/L4/L5；**主仓不保留副本**，技能改动去层仓库。
- **发布**：每两周组织级 release note（GitHub Releases + 公众号 + 知乎）。
- **采集合规**：仅自有账号、低频（≥30s）、不绕过验证、失败即停人工接管、不伪造数据。

### 2.4 与海外五家的位置关系

| 他们 | 卖什么 | 我们对应层 | 我们的差异 |
| --- | --- | --- | --- |
| Profound | Monitor / Agents / Index，399 美元/月起 | L1 / L3 / L5 | 开源、中国引擎、事实源先行 |
| Scrunch | Insights / AXP（站点可读性） | L2 / L4 | 同上 |
| Peec | 轻量监测 | L1 | 同上 |
| Frase / Native AI | 内容生成与优化 | L3 | 我们绑定事实库门禁，不做无源内容 |

定位一句话：**GEO 的开放标准与开源工具层——闭源 SaaS 把「看见」卖 399 美元/月，OpenGEO 把「看见」变成公共品。**

---

## 第三部分｜全员学习路径（1 周）

### 3.1 所有人必修（第 1–2 天，约 3 小时）

| 步骤 | 做什么 | 验收 |
| --- | --- | --- |
| 1 | 读门户 README + GOVERNANCE | 能背出三不三只、四类 RFC 触发 |
| 2 | 看简明图解教程 learn/（8 页，30 分钟） | 能用一句话讲清每一层 |
| 3 | 本地克隆 opengeo-spec，对仓桥 bundle 跑 `python tools/okf_lint.py examples/cangqiao` | 看到 0 errors；故意把一个 stable 的 verified 删掉，看到 E004 |
| 4 | 本地克隆 opengeo-audit，跑 `python -m pytest -q` 与 `python scripts/run_audit.py examples/research_package_standard.json examples/evidence_package_measured.json --recommendations examples/recommendations_measured.json -o /tmp/a --report-mode experimental_score` | 打开生成的 HTML 报告，能指出六个维度 |
| 5 | 读《避坑指南》与课程站第三篇（AI 怎么选商家） | 能向客户解释「为什么不能保排名」 |

### 3.2 分角色进阶（第 3–5 天）

| 角色 | 必读 | 动手 | 验收 |
| --- | --- | --- | --- |
| 规范（L0） | SPEC-L1、RFC-0001、lint 源码 | 给一个虚构行业写一份 bundle 并通过 `--strict` | PR：行业词表补一个行业 |
| 测量（L1） | docs/ARCHITECTURE、SPEC、RUNBOOK、scoring-calibration | 用自有账号跑通 browser_collect 5 问 | issue #1 贴出 evidence 并通过 evidence_validate |
| 执行（L3） | orchestrator、三个 SKILL.md、fact-library-contract | `tools/install_claude_code.sh` 装到一个项目，用 S3 对仓桥 bundle 生成 1 篇 draft | draft 带来源标注，lint 通过 |
| 课程/运营 | 课程站全文、评审稿、本手册 | 写第一期 release note 草稿 | 双周发布 |
| 统筹 | 全部 + 六仓 issue | 建跨仓看板 | 周例会纪要 |

### 3.3 团队共同练习（第 5 天，1 小时）

「一个客户从 0 到复测」桌面推演：选一家本地生活品牌 → 按行业词表建 bundle（draft）→ 老板审核转 stable → 出 20 问 → 诊断基线 → S3 产 3 篇 → 上站 JSON-LD → 28 天后复测回写 → 进入 OpenGEO Index。每个人讲自己那一层的输入输出与门禁。

### 3.4 学习验收题（10 题，答对 8 题过关）

1. 一条事实能被总控 Agent 引用的两个条件是？
2. `verified.by` 三个前缀分别代表什么信任级？
3. 六维权重各是多少？哪一维对投毒最敏感？
4. 为什么 experimental_score 模式必须附改进清单？
5. 采集为什么不能跑在 GitHub Actions？
6. 哪四类变更必须走 RFC？
7. 主仓 OpenGEO 里现在还有没有 skills/ 目录？为什么？
8. OpenGEO Cloud 属于谁？它和开源层的关系是什么？
9. 安兔兔的两个教训分别对应我们哪两道防线？
10. 对外讲标准时用哪个名字？讲服务时用哪个名字？

---

## 附录 A｜术语速查

| 术语 | 一句话 |
| --- | --- |
| GEO | 生成式引擎优化：让 AI 看见、相信并推荐你 |
| OKF bundle | 品牌事实库：一棵带 frontmatter 的 markdown 目录树，唯一事实源 |
| stable / draft | 已审可引用 / 未审不得引用 |
| verified human: / tool: / machine: | 人确认 / 确定性脚本产出 / 自动核验 |
| 六维 | 可见度·推荐度·引用源·覆盖度·情感·内容基础 |
| diagnostic / experimental_score | 不发总分的诊断模式 / 带总分但必须附改进清单的研究模式 |
| 20 问 | 固定题集：品类推荐 10 / 品牌直达 5 / 对比验证 5 |
| OpenGEO Index | 行业 × 城市 × 引擎的可见度指数（对外名） |
| open-core | 开源层公共品 + 仓桥 Cloud 商业层 |
| RFC | 规范/指标/引擎/schema 变更的提案流程 |

## 附录 B｜仓库与链接

- 组织：https://github.com/cangqiaoGEO ｜ 门户：https://github.com/cangqiaoGEO/OpenGEO
- 课程站：https://cangqiaogeo.github.io/OpenGEO/course/ ｜ 图解教程：https://cangqiaogeo.github.io/OpenGEO/learn/
- 层仓库：opengeo-spec · opengeo-audit · opengeo-insights · opengeo-skills · opengeo-agentready · opengeo-index
- 治理：OpenGEO/GOVERNANCE.md ｜ 评审稿：OpenGEO/docs/six-repo-plan.md

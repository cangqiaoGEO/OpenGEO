---
name: brand-geo-audit
description: 诊断品牌在生成式 AI 引擎答案和公开内容生态中的表现。当用户希望了解品牌的 AI 可见度、推荐、引用、信息覆盖、情感与内容基础时使用。先建立业务语境和冻结查询协议，再校验真实观测证据；样本充分时可输出实验性分项与评分，样本不足时只输出缺口，不制造正式结论。当前自动采集适配豆包、千问、DeepSeek 和腾讯元宝，其他平台可接收用户提供的真实回答。触发词：GEO诊断、品牌诊断、AI搜索可见度、生成式引擎优化、品牌在AI中的表现、brand GEO audit。
metadata:
  version: 0.6.0
  agent_created: true
  display_name: 品牌 GEO 诊断
  description_zh: 用多类业务问题和不同问法实测品牌在生成式 AI 中的可见性，并输出证据化精简报告
---

# Brand GEO Audit（品牌 GEO 诊断）

对给定品牌执行一次完整的生成式引擎优化（GEO）诊断：先确认品牌实体、业务场景与高价值问题，再观测品牌在主流 AI 引擎答案中的表现，输出可追溯的分项诊断。

## Module Boundary

`OpenGEO` 是多 Skill 容器，本 Skill 的唯一产品边界是 `skills/S1-diagnosis/`

- 本 Skill 只维护该目录下的指令、契约、脚本、文档、测试、示例和本地运行配置
- 不得根据 GEO 模块需求改写仓库根目录、其他 Skill 或共享配置
- 若未来确需仓库级集成，必须将其作为独立变更由仓库所有者明确确认
- 当前规格、产品目标和渐进路线分别见 `docs/SPEC.md`、`docs/PRODUCT_TARGET.md` 和 `docs/ROADMAP.md`

## Overview

GEO 指优化品牌在生成式 AI 引擎答案中的可见度与推荐概率。本技能先建立最小业务
领域模型并冻结查询协议，再通过消费者产品浏览器、官方 API 和 WebSearch 内容生态调查
三条通道收集数据，按统一指标体系（见 `references/methodology/geo-metrics.md`）计算得分，产出 HTML
诊断报告。Web 内容生态调查只用于判断内容基础与引用潜力，不能冒充真实 AI 引擎观测。

当前 v2 指标配置属于 `experimental M1` 工程测量框架，不是已经获得外部验证的 GEO 行业标准
正式运行前读取 `references/methodology/methodology-evidence.md`，不得把外部论文、标准或平台文档表述为对
本技能权重、阈值和等级的认证。目标三层领域模型、双协议结构和迁移边界见
`references/architecture/measurement-architecture.md`，科学校准和发布门槛见 `references/methodology/scoring-calibration.md`。

WorkBuddy MVP 默认交付物：
1. 一份机器可读的查询族汇总，区分稳定可见、稳定缺席、问法敏感和证据不足
2. 一份结论优先的单文件 HTML 客户报告，详细查询和方法边界放在附录

当前查询族和每族两种问法属于待验证的 MVP 采样策略，用于上线取数和反向校准，不得表述为行业标准

## OpenGEO 事实库衔接

- 调用方提供 OpenGEO 品牌事实库时，只用 `status: stable` 且未过 `stale_after` 的 `identity.md`、`positioning.md`、`audience.md`、`products/` 与 `boundaries.md` 建立品牌实体和业务语境。
- 消费者 AI 回答、官方 API 响应和公开网页属于本次诊断的**观测证据**，不是可直接回写的品牌事实；它们必须按通道、时间和来源保存。
- 诊断发现、评分、建议与报告不得自动修改品牌事实库的状态、正文或 `verified` 字段。需要纳入事实库的材料必须另走 ingest 与人工审核。
- 事实库与平台回答冲突时，同时保留事实口径和冲突证据，标为待人工复核；不得为了提高分数改写事实库。

## Workflow Decision Tree

- 用户只给了品牌关键词 → 先完成研究基础门槛，再执行完整诊断流程
- 用户给了品牌关键词 + 某个/多个 AI 引擎的问答文本 → 按该引擎填充分数，跳过对应数据收集
- 用户要求跟踪/复查（此前诊断过）→ 复用同版本查询协议和采集条件执行可比较复查；当前没有独立快速模式契约
- 用户仅问概念（"什么是 GEO"）→ 不执行诊断，直接解释概念

## Step 1: 建立研究基础并冻结查询协议

正式采集前必须读取 `references/methodology/methodology-evidence.md` 与 `references/methodology/research-foundation.md`，依次建立：

1. `ResearchScope`：品牌、业务领域、地域、语言、受众、截止日期、深度与排除范围。
2. `DomainContext`：品牌定位、目标客户、客户问题、产品、业务场景、竞品、替代方案、
   高价值问题、未知项与来源证据。
3. `QueryProtocol`：从高价值问题推导测试查询，关联客户、问题、商业价值、预期证据和引擎。
4. R1 诊断包：建立 `DiagnosticRun`、`BrandEntityProfile`、`IndustryProfile`、`MeasurementPlan` 和 `ContentFoundationProtocol`。

`BrandEntityProfile` 必须显式记录正式名、品牌别名、公司名、门店名和地点；只有已验证或部分验证的匹配词才能用于判断品牌是否在 AI 答案中出现。

`IndustryProfile` 不按品牌规模设置门槛。对地域敏感、到店体验或授权经销业务，必须把地域查询、门店实体、本地列表、经营主体和授权关系列为适用的测量内容，不能用缺少百科或全国媒体覆盖推导 AI 不可见。

事实、推断、观点和未知必须显式区分；事实和推断必须引用来源。候选来源需检查页面存活、
主体匹配和内容相关性，无法确认时标记 `unverified`，不能作为已成立事实的唯一证据。

冻结查询集至少覆盖 4 个业务查询族：

- 品类推荐型："最好的{品类}是什么？"
- 品牌对比型："{品牌}和{竞品}哪个好？"
- 解决方案型："{客户}应该如何解决{业务问题}？"
- 品牌直达型："{品牌}怎么样？{品牌}值得选择吗？"

WorkBuddy MVP 中，每个查询族至少设计两条独立问法。两条问法必须表达同一业务信息需求，但使用真实用户可能采用的不同措辞；优先来自客户原话、咨询记录或搜索词，没有真实语料时允许专家设计并明确其来源。不得仅追加“换个说法回答”等无效尾缀制造伪变体

`query_type` 作为当前查询族标识，同类型的不同 `query_id` 作为表达变体。四族与两变体只是首版运行参数，后续依据真实数据调整，不固化为权威门槛

默认使用 3-5 个引擎。竞品比较属于查询协议的必要校准项，但不自动扩大为完整竞品研究报告。

将三个对象保存为工作目录 `geo_research_<brand>.json`，结构参考
`examples/research_package_standard.json`，然后运行：

```bash
python3 <skill_dir>/scripts/research_validate.py geo_research_<brand>.json
```

只有校验结果 `valid=true` 且 `QueryProtocol.status=frozen` 时才能进入 Step 2。若范围或业务语境
仍不明确，保持 `draft`，列出研究缺口，不生成看似正式的查询协议。

将 R1 对象保存为 `geo_diagnostic_<brand>.json`，结构参考 `examples/diagnostic_package_standard.json`，然后运行：

```bash
python3 <skill_dir>/scripts/diagnostic_contracts.py \
  geo_research_<brand>.json geo_diagnostic_<brand>.json
```

只有 `DiagnosticRun` 离开 `planning` 时，研究、品牌实体和行业适配必须 `ready`，查询、测量计划和内容协议必须 `frozen`。

需要执行真实品牌受控试点时，读取 `docs/R2_PILOT_PROTOCOL.md`，用 `PilotStudy` 冻结案例组合、采集模式、重复次数、复核责任和交接要求。真实案例只能保存在 Git 忽略的 `work/` 目录。

## Step 2: 数据收集（三通道）

正式采集需先读取 `references/runtime/domestic-platform-capabilities.md` 和 `references/runtime/collection-runtime.md`
消费者网页采集必须由当前宿主提供满足 `references/runtime/host-runtime-contract.md` 的适配器
当前可发布实现只有 WorkBuddy，构建后的专家会预加载独立的 `geo-browser-runtime` Skill；核心 Skill 不直接绑定浏览器工具名、安装目录或宿主配置
每条冻结查询先生成 `PlatformRequest`，采集器输出 `RawPlatformResponse`，再由人工或受控标注
转换为 `ObservationEvidence`。原始采集器不得自行猜测品牌位置、推荐、情感、覆盖和事实错误。

### 通道 A：消费者产品浏览器实测（正式诊断主证据）

通过当前宿主的浏览器适配器，以可见窗口执行低频、受控采集
可见窗口是正式采集的硬性要求，不得静默降级为后台无头模式；窗口必须保持可见，以便用户在身份或授权节点接管
适配器负责打开豆包、千问、DeepSeek 和腾讯元宝并识别页面状态，核心 Skill 只接收标准 `PlatformRequest` 和 `RawPlatformResponse`
登录、账号选择、验证码、OAuth、权限和安全验证仍必须由用户本人完成，专家到达该节点后暂停平台操作并明确交还用户

没有宿主浏览器适配器时，才使用本 Skill 自带的 Playwright 半自动采集器作为本地兼容方案
也可以向用户提供标准查询话术，请其将各引擎回答和截图交回：

> 请在以下引擎中逐一提问并复制回答：
> 1. {查询 1}  2. {查询 2}  3. ...
> 引擎：用户实际使用且能够提供真实回答的生成式 AI 产品

若用户已提供文本，跳过对应回答采集。浏览器结果标记为 `official_app_browser`，必须保存采集
时间、页面状态和截图；不得绕过验证码、规避风控或高并发抓取。

### 通道 B：官方 API 自动采集（辅助与周期监测）

豆包使用火山方舟，千问使用阿里云百炼，DeepSeek 使用官方 API，腾讯元宝使用腾讯 TokenHub 的 Hy3 作为 API 对照通道。Key 只允许通过环境变量读取。
API 结果标记为 `official_api`，与消费者产品结果分别聚合，不能混合平均。DeepSeek 官方 API
没有已核验的原生联网搜索契约，必须记录 `search_mode=none`。

腾讯元宝消费者网页不得预设模型 ID；只有 TokenHub API 请求可以明确记录 `model_requested=hy3`，该 API 对照通道固定使用普通 TokenHub，不接受其他模型或套餐端点。

### 通道 C：WebSearch 内容生态调查（自动执行）

用 WebSearch 对每条测试查询 + 品牌词执行检索，评估品牌在可索引内容生态中的表现，
并作为引用潜力的代理证据。该通道不得直接产生 AI 引擎可见度、推荐度或情感观测。
每条查询至少 1 次搜索，检查：
- 品牌官网 / 官方内容是否出现且排位
- 百科、权威媒体、评测、社媒内容的有无与数量
- 品牌核心信息（简介、卖点、产品线、价格、口碑、动态）在搜索结果中的覆盖
- 竞品相关内容量对比

同时用 WebFetch 抽查品牌官网与百科条目，确认结构化内容（FAQ、schema.org）与信息准确性。

### 数据落盘

先按 `references/runtime/collection-runtime.md` 校验 `PlatformRequest` 与 `RawPlatformResponse`，再将真实
AI 回答与内容基础证据整理为 `ObservationEvidence` JSON，保存到工作目录
`geo_evidence_<brand>.json`，结构参考 `examples/evidence_package_measured.json`。

执行证据校验：

```bash
python3 <skill_dir>/scripts/evidence_validate.py \
  geo_research_<brand>.json geo_evidence_<brand>.json
```

`unobserved`、`absent`、`null` 和 `false` 含义不同，必须按 `references/methodology/geo-metrics.md`
记录，不得使用缺失字段代替状态。

关键消费者 App 查询需要检查重复运行时，使用 `RepeatedObservationExperiment` 保留每次独立回答和人工标注，再运行：

```bash
python3 <skill_dir>/scripts/repeated_experiment.py \
  repeated-observation-experiment.json \
  --project-root <project_root> \
  --output stability.json
```

稳定性指标不是 GEO 得分。每次回答还必须区分规范名、已核验别名、已核验关联实体、同品类其他实体、歧义和缺席，不能用名称相似建立品牌关系。

## Step 3: 计算指标

运行评分脚本（须使用托管 Python）：

```bash
python3 <skill_dir>/scripts/geo_score.py \
  geo_research_<brand>.json geo_evidence_<brand>.json > geo_result_<brand>.json
```

脚本依次执行回答级、引擎级和总体级计算，输出完整五维引擎矩阵及内容基础分。
每个维度同时包含 `score`、`sample_count` 和 `unknown_count`。

得分与等级解读规则：
- 只有 `assessment.status=measured` 时才允许解释综合得分和等级。
- `partially_measured` 或 `insufficient_data` 的 `total` 与 `grade` 为 `null`。
- 正式结果中综合得分 ≥60 为合格，维度得分 <60 进入 `weak_dimensions`。
- 当前权重、60 分阈值和字母等级必须标记为实验性解释，不得表述为外部验证标准。

## Step 4: 执行质量审计

对研究边界、样本充分性、来源可靠性、覆盖完整性、交叉验证、反证审查、数据新鲜度和
可追溯性执行确定性审计：

```bash
python3 <skill_dir>/scripts/quality_audit.py \
  geo_research_<brand>.json geo_evidence_<brand>.json geo_result_<brand>.json \
  > geo_audit_<brand>.json
```

审计输出 `QualityAudit`，包括状态、置信度、逐项检查、证据缺口、反证、警告和下一步验证动作。
只有 `passed` 或 `passed_with_warnings` 且评分状态为 `measured` 时，才允许生成改进建议。

## Step 5: 按报告模式处理改进建议

`diagnostic` 和 `exploratory` 模式跳过改进建议生成，只交付证据缺口、待验证问题和规划交接边界。

`diagnostic` 模式完成后生成 `DiagnosticHandoff`，结构参考 `examples/diagnostic_handoff_standard.json`，并运行：

```bash
python3 <skill_dir>/scripts/handoff_validate.py \
  geo_handoff_<brand>.json \
  --project-root <project_root>
```

交接包必须分离已观察事实、推断、未知和反证，并引用原始证据；它可以提出待规划问题和验证指标，但不能替规划角色选择或执行行动。

只有 `experimental_score` 模式执行以下兼容链路：

按 `references/methodology/geo-metrics.md` 第 5 节生成 `geo_recommendations_<brand>.json`，结构参考
`examples/recommendations_measured.json`。每条建议必须区分发现、假设、行动、预期效果、
衡量方式和置信度，并引用真实的来源或观测 ID。

```bash
python3 <skill_dir>/scripts/recommendation_validate.py \
  geo_research_<brand>.json geo_evidence_<brand>.json geo_result_<brand>.json \
  geo_audit_<brand>.json geo_recommendations_<brand>.json
```

校验器会重新计算评分与审计，拒绝过期结果、无证据建议、未覆盖薄弱维度、低置信度 P0
以及样本不足时产生的改进建议。样本不足时建议数组必须为空，只交付证据缺口和验证动作。

## Step 6: 生成并交付 WorkBuddy MVP 报告

### 6.1 生成查询族汇总和客户报告

默认运行精简报告脚本：

```bash
python3 <skill_dir>/scripts/mvp_report.py \
  geo_research_<brand>.json geo_evidence_<brand>.json \
  --summary-output <brand>_geo_summary.json \
  -o <brand>_geo_report.html
```

脚本先验证研究与证据契约，再按平台和查询族汇总不同问法。客户报告首页只展示观测覆盖率、跨问法稳定结论和风险场景，不展示未经校准的综合分；精确查询与机器摘要保留在附录

`geo_report.py` 继续作为内部实验与兼容报告器保留，不作为 WorkBuddy MVP 默认客户交付

默认 `diagnostic` 模式不发布实验性总分、字母等级或行动方案；只有显式的 `experimental_score` 模式才展示现有实验性总分和建议。

### 6.2 交付

- 使用当前运行环境可用的文件交付能力展示 HTML 报告
- 在对话中给出摘要：本次观测范围、跨问法稳定结论、问法敏感场景、稳定缺席场景和关键证据缺口

## 通用规则与注意事项

- 当前自动采集覆盖豆包、千问、DeepSeek 和腾讯元宝；其他平台仅在用户提供真实回答或未来增加适配器后进入观测。
- 通道 C 属于内容生态代理评估，报告中必须注明局限，不能将其包装为 AI 引擎实测。
- 情感、覆盖度等存在主观性的判断，在明细表中标注判断依据，供用户复核。
- 查询协议必须包含至少一条同口径竞品校准查询；完整竞品报告仅在用户要求时进行。
- 报告的浅色主题与汉字编码需在生成时保证（避免乱码）。
- 诊断输出仅作为参考，不构成任何投资或商业决策依据。
- 真实品牌运行只是可替换、可删除的测试或交付案例，不得反向定义通用 Schema、指标、权重、阈值和默认建议。
- 每个高商业价值查询必须保留独立观测，不得用其他地域、场景或通道的聚合分掩盖该查询的真实命中或缺失。

## Resources

- `README.md` 与 `docs/ARCHITECTURE.md` — 开发入口，以及核心、宿主契约、WorkBuddy 适配和生成产物的责任关系
- `docs/SPEC.md`、`docs/PRODUCT_TARGET.md` 与 `docs/ROADMAP.md` — 当前实现、WorkBuddy 产品边界和渐进路线。
- `docs/R2_PILOT_PROTOCOL.md` — 真实案例的组合、冻结、采集、实体复核、重复性和交接验收协议。
- `references/methodology/geo-metrics.md` — 当前 v2 指标计算口径的实现级来源（6 维度权重、
  0-100 评分表、等级划分、引擎矩阵要求、建议生成规则与通用建议库）。计算前必须读取。
- `references/methodology/methodology-evidence.md` — 外部理论来源、支持边界、自定义指标证据等级和实验性参数登记。
- `references/architecture/measurement-architecture.md` — 通用业务层、行业适配层、品牌实体层、双协议和候选对象链。
- `references/methodology/scoring-calibration.md` — 内容效度、标注信度、重复性、不确定性、权重校准和外部验证路线。
- `references/methodology/research-foundation.md` — 正式采集前的研究范围、业务领域模型、查询协议、
  证据语义与冻结门槛。
- `references/runtime/domestic-platform-capabilities.md` — 豆包、千问、DeepSeek 和腾讯元宝官方能力快照及 App/API 边界。
- `references/runtime/collection-runtime.md` — 浏览器与 API 两条平台通道的采集运行、凭证、交接与验收规则。
- `references/runtime/host-runtime-contract.md` — 浏览器、身份交接、密钥读取和产物写入的宿主适配契约
- `references/studies/` — 仅在复核历史实验、重复性和 App/API 差异时读取，不承担当前运行规范。
- `schemas/*.schema.json` — 研究、证据、评分、质量审计与建议对象的稳定 JSON 契约。
- `scripts/research_validate.py` — 批次 A 研究包校验器：结构检查、证据语义、跨对象引用、
  查询覆盖和冻结门槛，无第三方依赖。
- `scripts/diagnostic_contracts.py` — R1 诊断运行、品牌实体、行业适配、测量计划和内容协议的跨对象校验器。
- `examples/diagnostic_package_standard.json` — 可与标准研究包组合校验的 R1 合成示例。
- `examples/diagnostic_handoff_standard.json` — 不含真实品牌的诊断到规划交接示例。
- `examples/research_package_standard.json` — 可直接通过校验的标准档示例研究包。
- `examples/evidence_package_measured.json` — 覆盖 3 个引擎与 4 类核心查询的正式测量示例。
- `scripts/evidence_validate.py` — v2 证据、状态一致性、查询引用和样本充分性校验器。
- `scripts/collection_contracts.py` — 平台请求、原始响应、指纹和凭证泄露校验器。
- `scripts/repeated_experiment.py` — 多次消费者网页运行校验与描述性稳定性统计器。
- `scripts/pilot_validate.py` — R2 案例组合、重复采集、复核和完成状态校验器。
- `scripts/handoff_validate.py` — 诊断事实、实体状态、证据缺口和规划问题交接校验器。
- `scripts/channel_compare.py` — 同题消费者网页与官方 API 的分维度通道比较器。
- `scripts/api_collect.py` 与 `scripts/platform_adapters.py` — 四个平台的 Dry Run 和官方 API 采集适配层。
- `scripts/browser_collect.mjs` — 无宿主浏览器适配器时使用的 Playwright 可见浏览器兼容采集器，身份与授权操作由用户完成
- `scripts/geo_score.py` — v2 确定性评分器：研究包 + 观测证据 → 回答级、引擎级与总体级结果。
  纯标准库，无第三方依赖。
- `scripts/quality_audit.py` — v2 确定性质量审计器：输出检查、缺口、反证、置信度和验证动作。
- `scripts/recommendation_validate.py` — v2 建议校验器：检查可追溯性、覆盖门槛、优先级与结果新鲜度。
- `examples/recommendations_measured.json` — 可通过校验的证据驱动建议示例。
- `scripts/geo_report.py` — v2 安全报告生成器：五个契约对象 → 无脚本、无外部资源的单文件 HTML 报告。
- `scripts/query_family_summary.py` — 按业务查询族、表达变体和平台生成确定性汇总
- `scripts/mvp_report.py` — WorkBuddy 默认的结论优先客户报告与机器摘要生成器

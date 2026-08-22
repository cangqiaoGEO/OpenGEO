## Brand GEO Audit 当前 v2 + R2 模块规格

### 一、规格边界

本文只描述 `skills/S1-diagnosis/` 模块中已经实现并可验证的 v2 链路、R1 诊断契约和 R2 受控试点能力

`OpenGEO` 是多 Skill 容器，本模块不拥有仓库根文档、其他 Skill 或仓库级配置，实现和路线变更默认不得越过 `skills/S1-diagnosis/`

当前工程分层与发布链路见 [ARCHITECTURE.md](ARCHITECTURE.md)，WorkBuddy 产品目标见 [PRODUCT_TARGET.md](PRODUCT_TARGET.md)

测量候选架构和未来研究路线分别见 `references/architecture/` 与 [ROADMAP.md](ROADMAP.md)，不属于当前已经实现的工程能力

当前方法学成熟度为 `experimental M1`，可用于受控诊断和数据积累，不能称为已经科学定型的 GEO 行业标准

### 二、当前运行链路

```text
DiagnosticRun
  -> BrandEntityProfile
  -> IndustryProfile
  -> MeasurementPlan
       -> ResearchScope -> DomainContext -> QueryProtocol
       -> ContentFoundationProtocol
  -> PlatformRequest
  -> RawPlatformResponse
  -> RepeatedObservationExperiment
  -> Entity Observation Review
  -> ObservationEvidence
  -> QueryFamilySummary
  -> ScoreResult
  -> QualityAudit
  -> Recommendation
  -> MVP HTML Report (diagnostic default)
  -> Experimental HTML Report (internal compatibility)
  -> DiagnosticHandoff
```

`PlatformRequest` 和 `RawPlatformResponse` 服务于自动采集，用户提供的真实回答也可以直接整理为 `ObservationEvidence`

宿主运行时通过 `host-runtime-contract.md` 接入浏览器、身份交接、密钥读取和产物写入能力，领域核心不依赖具体宿主工具

R1 不替换 v2 研究包，而是用独立诊断包增加运行、实体、行业、测量和内容探针语义

R2 用独立试点清单、重复观测和诊断交接包验证工作流，真实案例仍只保存在 `work/`

### 三、模块责任

| 路径 | 当前责任 |
|---|---|
| `skills/S1-diagnosis/SKILL.md` | Agent 工作流、控制权和交付规则 |
| `skills/S1-diagnosis/README.md` | 开发入口、快速验证和文档导航 |
| `skills/S1-diagnosis/docs/ARCHITECTURE.md` | 核心、宿主契约、WorkBuddy 适配和生成产物的责任关系 |
| `skills/S1-diagnosis/schemas/` | 跨 Agent 与脚本边界传递的 JSON 契约 |
| `skills/S1-diagnosis/references/methodology/` | 指标、研究协议、证据基础和校准路线 |
| `skills/S1-diagnosis/references/architecture/` | 候选架构及其与当前 v2 的差异 |
| `skills/S1-diagnosis/references/runtime/` | 平台能力快照和采集运行规则 |
| `skills/S1-diagnosis/references/studies/` | 有日期的历史实验记录，不承担当前规范 |
| `skills/S1-diagnosis/adapters/workbuddy/` | WorkBuddy 专家定义、浏览器运行时、可复现构建与本地安装 |
| `skills/S1-diagnosis/scripts/` | 确定性校验、采集、评分、审计和报告生成 |
| `skills/S1-diagnosis/tests/` | 契约、回归、单元和端到端验证 |
| `skills/S1-diagnosis/examples/` | 不含真实客户敏感信息的可运行示例 |
| `skills/S1-diagnosis/work/` | Git 忽略的真实运行与实验产物 |

### 四、稳定语义

- 真实 AI 引擎观测只能来自直接观测或用户提供的回答
- Web 内容生态证据只能用于内容基础和引用潜力，不能冒充 AI 引擎回答
- 浏览器消费者产品和官方 API 分通道记录，不能混合平均
- `null`、`false`、`absent` 和 `unobserved` 不得互相替代
- 原始采集器不判断品牌位置、推荐、情感、覆盖和事实错误
- 回答先独立评分，再按引擎聚合，最终对引擎等权聚合
- 样本不足或任一维度未知时，不生成综合分和等级
- 建议必须引用来源或观测，并区分事实、假设、行动和预期效果
- 报告生成前重新计算评分和审计，拒绝过期或被修改的中间结果
- 品牌必须通过已验证的正式名或别名匹配，门店名和公司名不能临时猜测为同一实体
- 地域敏感业务的行业卡会检查门店列表与经营主体探针，不用百科和全国媒体覆盖替代本地可见性
- 关键查询继续保留单题结果，不允许用其他场景的得分抵消或掩盖
- 同品类其他实体不能按名称相近映射为目标品牌，实体关系不足时保留歧义或未知
- 重复实验指标只描述运行稳定性，不直接进入现有实验性 GEO 总分
- `query_type` 在 MVP 中投影为业务查询族，同类型的多个 `query_id` 表示不同问法
- 查询族汇总按变体等权计算，不用某一问法的重复数量放大其权重，也不混合不同平台
- 查询族少于两种问法时只允许输出部分观测，不得声称已判断措辞稳定性
- 下游交接只传递事实、推断、未知、反证、影响、缺口和规划问题，不直接下达执行动作

### 五、当前平台范围

当前 WorkBuddy 浏览器适配器和官方 API 采集器覆盖豆包、千问、DeepSeek 和腾讯元宝

腾讯元宝消费者网页与腾讯 TokenHub 的 `hy3` API 是两个独立通道，前者不预设实际模型，后者仅作为 API 对照和周期监测样本

其他平台可以接收用户提供的回答作为证据，但当前仓库没有对应自动采集适配器，不能把平台名称列表解释为已实现能力

平台产品、模型、搜索能力、价格和页面选择器具有时效性，运行前按 [domestic-platform-capabilities.md](../references/runtime/domestic-platform-capabilities.md) 和 [collection-runtime.md](../references/runtime/collection-runtime.md) 重新核验

### 六、契约与版本

研究、证据、评分、质量审计和建议对象当前使用 v2 契约；平台请求、原始响应、重复实验、R1 诊断、R2 试点与诊断交接对象使用各自的 v1 契约

不同对象版本独立演进，`DiagnosticRun` 已成为运行清单，`metric_profile_version` 仍未实现

JSON Schema 和手写校验器同时存在，但当前测试尚未证明两者完全等价，因此不得把“Schema 文件存在”表述为完整契约符合性证明

### 七、实验性参数

以下规则已经实现，但尚未完成外部校准：

- 六维权重 `30/20/15/15/10/10`
- 三或五引擎样本门槛
- 四类核心查询
- 20% 未知率警告
- 180 天新鲜度窗口
- 60 分合格线与 S/A/B/C/D 等级

正式交付必须同时展示分项、样本和未知，不得仅用总分或等级替代证据

### 八、当前未实现能力

- WorkBuddy 专家团角色绑定和完整线上真实任务验证
- 完整探索式研究运行时
- `validated_score` 报告模式
- 不确定性正式投影
- 多标注者一致性
- Schema 与运行时校验器自动符合性测试

候选对象关系见 [measurement-architecture.md](../references/architecture/measurement-architecture.md)，实施顺序见 [ROADMAP.md](ROADMAP.md)

### 九、案例隔离

真实品牌运行不是 Skill 内容，也不是规范来源

删除任何真实品牌案例后，Schema、脚本、示例、测试、架构和方法论必须继续独立成立，具体决策见 [ADR-0003](decisions/0003-test-case-isolation.md)

### 十、工程规范

编码、目录、注释和验证规则见 [CODING_STANDARD.md](CODING_STANDARD.md)，当前运行命令见 [RUNBOOK.md](RUNBOOK.md)

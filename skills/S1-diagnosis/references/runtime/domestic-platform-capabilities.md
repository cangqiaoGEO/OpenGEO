## 国内头部 AI 平台采集能力矩阵

### 一、文档目的

本文是带核验日期的平台能力快照，记录豆包、千问、DeepSeek 和腾讯元宝四个平台的官方 API 对照能力，并为当前统一采集适配层提供输入

核验截止日期为 2026-08-21，平台能力、模型版本、价格和限流可能变化，真实运行前必须重新读取官方文档或通过探针调用确认

2026-08-20 真实探针补充：DeepSeek `deepseek-v4-flash` 已完成 3 次调用、消费者网页配对比较和关键事实抽检，单平台资格测试通过并带风险警告；豆包与千问按当次实验决策移出该次范围，详见 `../studies/api-live-paired-study.md`

本文严格区分消费者产品与开发者 API：

- 豆包 App 不等于火山方舟中的豆包模型调用
- 千问 App 不等于阿里云百炼中的千问模型调用
- DeepSeek App / Web 不等于 DeepSeek 官方 API 调用
- 腾讯元宝 App 不等于腾讯 TokenHub 的 `hy3` API 调用
- API 结果只能标记为 `official_api`，不能标记为消费者产品实测

### 二、首批平台结论

| 平台 | 官方 API | 原生联网搜索 | 来源或引用返回 | 自动采集结论 | App 等价性 |
|---|---|---|---|---|---|
| 豆包 | 火山方舟 Responses API | 支持内置 Web Search | 官方文档确认可返回或展示联网来源，具体事件结构需真实探针固化 | 可进入首批适配 | 不等价，必须另做 App 抽样 |
| 千问 | 阿里云百炼 Responses、Chat Completions 或 DashScope | 支持，且可强制触发 | DashScope 路径支持来源和引用角标；Responses API 不自动插入引用角标 | 可进入首批适配 | 不等价，必须另做 App 抽样 |
| DeepSeek | 官方 Chat Completions 与 Responses API | 未发现官方内置 Web Search | 官方公开对话响应没有搜索来源或引用字段 | 仅能采集非联网 API 回答，不能作为联网 App 等价样本 | 明显不等价，App 端必须独立取证 |
| 腾讯元宝 | 腾讯 TokenHub Hy3 Chat Completions API | 支持 `web_search_options` | `choices[0].message.search_results` 返回结构化来源 | 可进入自动采集，模型固定为 `hy3` | 不等价，元宝 App 端不预设模型 ID |

### 三、平台能力明细

#### 3.1 豆包 / 火山方舟

已核验事实：

- 官方提供 Chat API、Responses API 和 SDK
- Responses API 基础地址为 `https://ark.cn-beijing.volces.com/api/v3`
- 使用 Bearer API Key 鉴权，建议环境变量名为 `ARK_API_KEY`
- 可通过 Responses API 使用内置 Web Search
- 联网能力由模型判断是否触发，因此采集结果必须记录实际工具事件，不能只记录请求中的开关
- 官方文档说明联网资源可以展示 URL，但具体响应事件和引用字段仍需用真实账号执行探针确认
- 联网搜索与模型 Token 可能分别计费，限流及价格不得写死在适配器中
- **Agent Plan** 使用专属 Base URL `https://ark.cn-beijing.volces.com/api/plan` 与专属 API Key，不能和普通方舟数据面 API 或 **Coding Plan** Key 混用
- 2026-08-21 真实探针确认：`ark-code-latest` 经 `/api/plan/v1/messages` 成功路由到 `doubao-seed-2-0-lite-260215`，该通道未证明执行联网搜索，只能作为 API 校准样本

推荐 D2 默认路径：

```text
火山方舟 Responses API
  + 明确模型快照
  + Web Search 工具
  + 保存完整原始事件流
```

适配器必须保存：

- 请求模型 ID 和响应模型 ID
- Web Search 是否实际触发
- 搜索事件、来源 URL、标题和引用位置
- 原始输出事件与最终文本
- Token 用量、结束状态和平台请求 ID

官方依据：

- [火山方舟产品与 API 入口](https://www.volcengine.com/docs/82379/)
- [火山方舟 Responses API 快速开始](https://www.volcengine.com/docs/82379/1795150)
- [火山方舟工具调用与 Web Search](https://www.volcengine.com/docs/82379/1958524)
- [火山方舟联网内容插件升级说明](https://www.volcengine.com/docs/82379/1359519)

#### 3.2 千问 / 阿里云百炼

已核验事实：

- 官方提供 OpenAI 兼容 Responses API、Chat Completions API 和 DashScope 原生协议
- 建议环境变量名为 `DASHSCOPE_API_KEY`
- Responses API 通过 `tools=[{"type":"web_search"}]` 开启联网搜索
- Chat Completions 和 DashScope 通过 `enable_search=true` 开启联网搜索
- `forced_search=true` 可以要求触发搜索，适合形成可比较的 GEO 采集口径
- DashScope 原生协议支持 `enable_source`、`enable_citation` 和 `citation_format`
- Responses API 当前不支持上述三个引用参数，也不会自动插入引用角标
- 联网搜索存在独立限流，触发限流时可能跳过搜索而不报错，因此必须验证响应中是否真的执行搜索

推荐 D2 默认路径：

```text
DashScope 原生协议
  + 明确模型快照
  + enable_search=true
  + forced_search=true
  + enable_source=true
  + enable_citation=true
```

选择 DashScope 而非统一使用 Responses API，是因为 GEO 诊断需要结构化来源和引用信息，协议统一性不能优先于证据完整性

适配器必须保存：

- 模型 ID、部署地域和业务空间
- 搜索是否请求、是否实际触发
- 搜索策略、来源列表和引用角标
- 原始返回、最终回答和用量
- 限流未报错但跳过搜索的检测结果

官方依据：

- [阿里云百炼大模型联网搜索](https://help.aliyun.com/zh/model-studio/web-search/)
- [千问 Responses API](https://help.aliyun.com/zh/model-studio/qwen-api-via-openai-responses)
- [千问联网检索 Agent](https://help.aliyun.com/zh/model-studio/web-search-agent-guide)

#### 3.3 DeepSeek

已核验事实：

- 官方提供 Chat Completions API 和 Responses API
- Chat Completions 当前公开模型枚举包括 `deepseek-v4-flash` 和 `deepseek-v4-pro`
- 官方 Chat Completions 支持函数工具调用，但公开契约中工具类型只有 `function`
- 官方公开响应结构包含回答、推理内容、函数调用、模型、系统指纹和 Token 用量
- 当前公开契约中未发现内置 `web_search`、搜索结果、来源 URL 或引用字段
- 因此 DeepSeek 官方 API 只能形成非联网模型样本，不能替代 DeepSeek App / Web 的联网回答

推荐 D2 默认路径：

```text
DeepSeek 官方 API
  + 明确模型快照
  + 固定采样参数
  + 标记 search_mode=none
  + 独立进行 App / Web 人工抽样
```

不建议在首版中给 DeepSeek API 外接通用搜索后冒充 DeepSeek 产品答案。若以后增加自建检索增强通道，必须标记为 `custom_retrieval_api`，并与官方产品实测分组展示

适配器必须保存：

- 请求模型和响应模型
- `system_fingerprint`
- thinking 模式和 reasoning effort
- 温度、top_p、最大输出长度
- 原始回答、结束原因、用量和平台请求 ID
- `search_mode=none` 与空引用列表

官方依据：

- [DeepSeek Chat Completions API](https://api-docs.deepseek.com/api/create-chat-completion/)
- [DeepSeek API 文档入口](https://api-docs.deepseek.com/)

#### 3.4 腾讯元宝 / TokenHub Hy3

当前实现边界：

- 消费者产品标识为 `yuanbao`，消费者网页通道使用 `consumer_web`
- API 对照通道 provider 为 `tencent_tokenhub`，模型固定为 `hy3`
- Chat Completions 完整地址为 `https://tokenhub.tencentmaas.com/v1/chat/completions`
- 使用 Bearer API Key 鉴权，环境变量名为 `TENCENT_TOKENHUB_API_KEY`
- 联网请求通过 `web_search_options.enable=true` 开启
- 最终回答从 `choices[0].message.content` 提取，来源只从明确返回的 `search_results` 提取
- 消费者元宝页面实际使用的模型或路由策略若未明确展示，`model_reported` 保持未知，不能由 API 配置反推
- 2026-08-21 真实探针确认：`hy3` Chat Completions 联网调用成功，响应报告 3 次 Web Search 调用并返回 3 条结构化来源，`PlatformRequest` 与 `RawPlatformResponse` 契约验收通过

官方依据：

- [TokenHub 语言模型调用概览](https://cloud.tencent.com/document/product/1823/130079)
- [TokenHub Hy3 调用指南](https://cloud.tencent.com/document/product/1823/132252)
- [TokenHub 联网搜索](https://cloud.tencent.com/document/product/1823/132358)

### 四、统一采集约束

D2 不能只设计一个 `platform` 字段，至少需要记录以下实验条件：

| 字段 | 含义 |
|---|---|
| `consumer_product` | 用户真正要诊断的消费者产品，如 `doubao` |
| `provider` | API 提供者，如 `volcengine` |
| `channel` | `official_api`、`official_app_manual`、`third_party_hosted_api` 或 `custom_retrieval_api` |
| `model_requested` | 请求时使用的精确模型 ID |
| `model_reported` | 响应中返回的模型 ID |
| `search_mode` | `native`、`none` 或 `custom` |
| `search_requested` | 是否请求联网搜索 |
| `search_executed` | 响应证据是否表明实际执行搜索 |
| `citation_mode` | `structured`、`inline_only` 或 `none` |
| `collected_at` | 带时区的采集时间 |
| `raw_response_ref` | 不可变原始响应的位置或内容哈希 |
| `request_fingerprint` | 查询、参数和模型配置的确定性指纹 |

同一个冻结查询的结果只能在以下条件一致时直接比较：

- 消费者产品和采集通道一致
- 模型版本或版本策略一致
- 联网模式一致
- 地域、语言和时间窗口一致
- 采样参数一致

API 样本与 App 样本可以交叉验证，但不能直接混合平均

### 五、凭证与运行边界

- 不在仓库、样例、报告、日志或对话中保存 API Key
- 适配器只从环境变量读取 `ARK_API_KEY`、`ARK_AGENT_PLAN_API_KEY`、`DASHSCOPE_API_KEY`、`DEEPSEEK_API_KEY` 和 `TENCENT_TOKENHUB_API_KEY`
- 仓库只允许提交不含真实值的 `.env.example`
- 错误和调试日志必须清除 Authorization Header、Key 和账号标识
- 登录、实名认证、服务开通、付费、创建 Key 和权限授权由用户本人完成
- 无凭证时使用固定 mock fixture 完成全部结构、错误处理和回归测试

### 六、D2 实现决策

D2 按以下顺序实施：

1. 定义 `PlatformRequest` 与 `RawPlatformResponse` 契约
2. 建立适配器协议、环境变量配置和脱敏日志
3. 先实现无网络 mock adapter 和标准化测试夹具
4. 实现豆包 Responses API 适配器
5. 实现千问 DashScope 适配器
6. 实现 DeepSeek 官方 API 非联网适配器
7. 实现腾讯 TokenHub Hy3 联网 API 适配器
8. 将原始响应确定性转换为 `ObservationEvidence`
9. 增加重试、退避、限流、超时、成本预算和断点续采
10. 在真实凭证联调前执行安全检查

D2 的验收重点不是四个平台返回相同结构，而是任何差异都能被保留、解释并追溯

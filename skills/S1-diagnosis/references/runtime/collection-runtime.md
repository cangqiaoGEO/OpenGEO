## 浏览器与 API 平台采集运行说明

### 一、运行模型

当前 v2 在 `ObservationEvidence` 之前使用以下原始采集层：

```text
QueryProtocol
  ↓
PlatformRequest
  ├── official_app_browser → 宿主浏览器适配器 / Playwright 本地兼容采集器
  └── official_api → 平台 API 适配器
  ↓
RawPlatformResponse
  ↓
人工或受控语义标注
  ↓
ObservationEvidence
```

`RawPlatformResponse` 只保存平台原始回答、明确返回的引用和运行元数据，不判断品牌位置、推荐态度、情感、覆盖或事实错误

这些语义字段必须在原始证据完成后单独判读，不能由采集器默认补值

### 二、无凭证验证

验证采集请求与示例响应：

```bash
python3 skills/S1-diagnosis/scripts/collection_contracts.py \
  skills/S1-diagnosis/examples/platform_request_doubao.json \
  skills/S1-diagnosis/examples/raw_platform_response_doubao.json
```

查看官方 API 将要发送的请求，不执行网络调用：

```bash
python3 skills/S1-diagnosis/scripts/api_collect.py \
  skills/S1-diagnosis/examples/platform_request_doubao.json
```

默认是 Dry Run，只有显式增加 `--execute` 才会调用外部平台

### 三、API 采集

由用户本人完成服务开通和 Key 创建，然后只在本地环境变量配置：

```bash
export ARK_API_KEY="..."
export ARK_AGENT_PLAN_API_KEY="..."
export DASHSCOPE_API_KEY="..."
export DEEPSEEK_API_KEY="..."
export TENCENT_TOKENHUB_API_KEY="..."
```

执行单条请求：

```bash
python3 skills/S1-diagnosis/scripts/api_collect.py \
  request.json --execute -o raw_response.json

python3 skills/S1-diagnosis/scripts/collection_contracts.py \
  request.json raw_response.json
```

退出码：

- `0`：完成且契约有效
- `1`：契约无效
- `2`：文件或 JSON 读取失败
- `3`：契约有效，但采集失败或缺少凭证

适配器只保存脱敏后的平台响应，不保存请求 Authorization Header

火山方舟 **Agent Plan** 使用独立配置：provider 为 `volcengine_agent_plan`，Base URL 为 `https://ark.cn-beijing.volces.com/api/plan`，凭证环境变量为 `ARK_AGENT_PLAN_API_KEY`，不得与普通方舟或 **Coding Plan** 的 Key 和端点混用

腾讯 **TokenHub** 使用 provider `tencent_tokenhub`、环境变量 `TENCENT_TOKENHUB_API_KEY` 和 `https://tokenhub.tencentmaas.com/v1`，模型固定为 `hy3`

腾讯元宝消费者网页不读取上述 API Key，也不得因为 API 使用 `hy3` 就把网页回答的模型字段写成 `hy3`

如果托管 Python 的默认 OpenSSL 没有 CA 路径，采集器会依次检查环境变量、运行时默认路径、系统 CA 和 Homebrew CA；始终保持证书与主机名校验，不允许使用未验证 TLS 上下文

### 四、浏览器采集

#### 4.1 宿主浏览器适配器

正式宿主集成必须满足 `host-runtime-contract.md`，并把宿主浏览器工具的结果转换为标准 `RawPlatformResponse`

核心采集链路不得直接依赖宿主名称、工具命令、插件安装目录或账号存储方式

宿主适配器必须提供可见窗口、页面状态读取、交互、截图、会话关闭和用户接管能力

正式采集不得静默降级为后台无头模式；宿主缺少能力时必须报告缺口，不能伪造消费者网页观测

首次访问某个平台时，如果会话未登录，登录、验证码、账号选择和授权必须由用户本人完成

#### 4.2 本地兼容运行时

安装依赖：

```bash
cd brand-geo-audit
npm install
npx playwright install chromium
```

上述 Playwright 步骤只用于没有宿主浏览器适配器的本地兼容运行，不作为已发布专家的默认用户流程

所有浏览器采集必须使用 `official_app_browser` 请求，且以可见浏览器运行

脚本打开页面后会暂停，登录、账号选择、验证码、OAuth、权限和安全验证全部由用户本人完成

用户确认页面可以提问后，脚本才填写已经冻结的查询并采集回答

```bash
npm run collect:browser -- \
  --request examples/platform_request_doubao_browser.json \
  --output work/browser-artifacts/doubao-response.json \
  --input-selector '[contenteditable="true"][role="textbox"]' \
  --submit-key Enter \
  --answer-selector '<当前回答容器 selector>' \
  --citation-selector '<当前引用链接 selector>'
```

如平台只有引用标题而未暴露 URL，使用 `--inline-citation-selector` 保存标题，并将引用模式标记为
`inline_only`，不得伪造结构化 URL。要求证明联网执行时，同时提供
`--search-evidence-selector` 与 `--search-evidence-text`

第三方页面 selector 会变化，真实联调时必须在当前页面重新核验，不能把未经验证的 selector 固化为平台事实

2026-08-20 豆包首轮联调确认：输入区可以使用 `[contenteditable="true"][role="textbox"]`，
回答正文可以使用 `[aria-label="doc_editor"] .md-box-root`，提交使用 `Enter`；这些值仍需在每次平台改版后复核

三平台首轮真实联调条件、来源完整性和选择器校准见 `browser-live-calibration.md`

三平台各 3 次同题运行、人工语义标注和稳定性统计见 `browser-repeatability-study.md`

采集器会：

- 使用平台独立的持久化浏览器目录
- 等待回答文本连续稳定后再保存
- 保存回答文本、显式引用、页面地址、标题和全页截图
- 不保存完整页面 HTML，降低账号和页面隐私泄露风险
- 不绕过验证码、不规避风控、不执行高并发抓取

### 五、验收边界

一次采集只有同时满足以下条件才能进入后续标注：

- 请求契约有效
- 回答状态为 `completed`
- 请求指纹与响应一致
- 要求联网时，有结构化响应证据证明搜索实际执行
- 浏览器通道具有截图
- 原始响应不含凭证
- API 和浏览器通道保持独立，不混合平均

### 六、重复实验

消费者网页正式观测前，使用独立重复实验对象保存多次运行：

```bash
python3 skills/S1-diagnosis/scripts/repeated_experiment.py \
  skills/S1-diagnosis/work/browser-artifacts/repeated-observation-experiment.json \
  --project-root .
```

统计器会重新校验每组 `PlatformRequest` 与 `RawPlatformResponse`，检查查询、平台、模式和重复序号一致性，再计算回答长度、实体集合、首位实体和来源 URL 的描述性稳定性

重复实验结果不能直接写入正式 GEO 分数，必须先依据目标品牌查询完成回答级语义标注和事实核验

比较消费者网页与官方 API：

```bash
python3 skills/S1-diagnosis/scripts/channel_compare.py \
  browser_experiment.json api_experiment.json \
  --project-root .
```

比较器要求同一消费者产品、查询协议和查询文本，输出回答长度、引用、搜索、实体集合、稳定核心和首位实体差异，并明确标记通道、模型和搜索能力不可等价

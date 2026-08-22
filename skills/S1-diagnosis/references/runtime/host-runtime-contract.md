## 宿主运行时适配契约

### 一、目标

本契约隔离 `brand-geo-audit` 诊断核心与具体 Agent 宿主、浏览器工具和安装目录

当前发布实现只有 WorkBuddy，但核心对象和确定性脚本不得反向依赖 WorkBuddy 实现细节

### 二、能力边界

宿主适配器必须提供以下能力：

| 能力 | 输入 | 输出或状态 |
|---|---|---|
| 可见浏览器启动 | 平台 URL、诊断会话 ID | 用户可见的浏览器会话 |
| 页面状态读取 | 浏览器会话 | 可提问、需登录、需验证或异常 |
| 受控页面交互 | 冻结查询、当前页面引用 | 提交状态 |
| 原始证据采集 | 当前回答页面 | 回答正文、明示引用、URL、时间、截图 |
| 用户接管 | 身份或授权节点 | 适配器内部进入 `waiting_for_user`，跨核心边界时映射为 `blocked_auth` |
| 会话关闭 | 诊断会话 ID | 无遗留浏览器进程 |
| 密钥读取 | 环境变量名 | 仅进程内使用的密钥或缺失状态 |
| 产物写入 | 标准对象、目标目录 | 本地文件路径或明确失败 |

### 三、数据契约

浏览器适配器接收已校验的 `PlatformRequest`，只输出满足 `raw-platform-response.schema.json` 的 `RawPlatformResponse`

适配器不得直接判断品牌位置、推荐强度、情感、信息覆盖或事实错误，这些语义由后续独立标注和审计处理

API Key、Authorization Header、Cookie、验证码和完整页面 HTML 不得写入 `RawPlatformResponse`、报告或构建产物

### 四、身份与控制权

登录、重新登录、账号选择、密码、验证码、OAuth 同意、设备授权和权限开通始终由用户本人完成

到达身份节点后，适配器必须停止该平台操作并进入内部状态 `waiting_for_user`；若此时生成 `RawPlatformResponse`，必须使用 `status: blocked_auth`，用户确认后重新读取页面，不复用授权前的页面引用

### 五、失败语义

适配器可以维护细分的内部运行状态，但跨核心边界的 `RawPlatformResponse.status` 只能使用 Schema 定义的 `completed`、`failed` 和 `blocked_auth`

| 适配器内部情况 | `RawPlatformResponse.status` | 处理规则 |
|---|---|---|
| 完整采集成功 | `completed` | 输出满足契约的原始回答和证据 |
| `waiting_for_user` | `blocked_auth` | 停止操作，等待用户完成身份或授权步骤 |
| `unsupported_runtime` | `failed` | 在非敏感 `error` 中说明宿主能力缺失 |
| `visible_browser_unavailable` | `failed` | 不得用无头或 API 结果冒充消费者 App 实测 |
| `platform_error` | `failed` | 保存非敏感错误说明，不记录凭证和完整页面 HTML |
| `partial` | `failed` | 可以保留已取得的非敏感证据，但不得伪造 `completed` |

### 六、当前实现

WorkBuddy 适配源码位于 `adapters/workbuddy/`，构建后提供 `geo-browser-runtime` Skill，并把浏览器结果转换为核心契约对象

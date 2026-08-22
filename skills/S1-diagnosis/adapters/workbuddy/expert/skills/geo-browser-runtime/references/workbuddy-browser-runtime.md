## WorkBuddy 四平台浏览器运行说明

### 一、目标与边界

本说明只适用于“GEO诊断专家”在 WorkBuddy 中的消费者 AI 网页实测

专家对用户呈现单一入口，内部通过 `geo-browser-runtime` 管理 `agent-browser` CLI 与浏览器操作

已有 `agent-browser` 时直接复用，缺失时在首次使用中自动安装 CLI 与浏览器内核，不要求用户安装项目内 Playwright 依赖

首次安装仍依赖宿主机已有 **Node.js 18+**、`npm` 和网络连接，WorkBuddy 也可能要求用户确认一次本地命令执行权限

正式采集必须打开用户可见的浏览器窗口，使用 `--headed` 或等效的 `AGENT_BROWSER_HEADED=true`，不得静默降级为后台无头运行

登录、重新登录、账号选择、密码、验证码、OAuth 同意、设备授权和权限开通始终由用户本人完成

### 二、目标平台

| 平台 | 消费者网页 | 运行标识 |
|---|---|---|
| 豆包 | `https://www.doubao.com/chat/` | `doubao` |
| 千问 | `https://www.qianwen.com/` | `qwen` |
| DeepSeek | `https://chat.deepseek.com/` | `deepseek` |
| 腾讯元宝 | `https://yuanbao.tencent.com/` | `yuanbao` |

消费者网页的模型和路由只记录页面明确展示的信息，不得由 API 模型名反推

### 三、单次采集控制流

1. 执行 `scripts/ensure_runtime.sh`，确认 CLI、浏览器内核和启动测试通过
2. 校验 `PlatformRequest`，确认 `channel=consumer_web` 且 `source_type=official_app_browser`
3. 为本次诊断生成独立 `session_id`，使用 `agent-browser open <url> --session <session_id> --headed` 打开目标平台
4. 等待页面基本加载后获取交互快照，确认浏览器窗口对用户可见
5. 判断当前是可提问、需登录、需人工验证还是页面异常
6. 遇到身份或授权节点时立即暂停，告知用户需完成的平台和动作，不代替用户操作
7. 用户确认后重新获取交互快照，不复用旧的元素引用
8. 填入已冻结的原始查询文本并提交，不临时改写问法
9. 等待回答稳定，采集回答正文、明示引用、搜索状态、页面地址、时间和截图
10. 生成 `RawPlatformResponse`，再交由独立的语义标注步骤生成 `ObservationEvidence`

不允许在采集阶段由浏览器自动化直接猜测品牌位置、推荐强度、情感、覆盖度或事实错误

### 四、会话与节流

- 同一次诊断中复用 `agent-browser` 持久会话，平台之间切换时不重启浏览器
- 首次 `open` 必须显式携带 `--headed`，后续命令通过同一 `session_id` 复用该可见窗口
- 每条查询串行提交，不对消费者平台执行高并发或规避限频
- 不绕过验证码、风控、付费或权限控制
- 任务结束或中止时关闭浏览器会话，避免遗留后台进程

### 五、验收标准

链路验收通过需要：

- 专家能调用 `agent-browser`
- 浏览器以 `--headed` 可见窗口启动，用户能看到页面并在身份节点接管
- 每个平台都能到达可提问页面或正确识别需用户登录的交接点
- 至少一个已登录平台完成“冻结查询 → 回答 → 截图 → 原始响应”闭环
- 所有登录与授权动作均由用户完成

正式诊断还必须满足核心采集契约的数据落盘、证据完整性和报告门槛

---
name: geo-browser-runtime
description: 为 GEO诊断专家准备并运行用户可见的 agent-browser 浏览器会话，仅在该专家执行国内消费者 AI 网页观测或浏览器链路验收时使用
metadata:
  version: 0.2.0
---

# GEO Browser Runtime

为 `GEO诊断专家` 提供 WorkBuddy 浏览器运行时适配

正式采集前读取 [运行流程](references/workbuddy-browser-runtime.md)，运行异常时读取 [故障处理](references/troubleshooting.md)

## 启动前自检

每次首次使用浏览器前执行：

```bash
bash <skill_dir>/scripts/ensure_runtime.sh
```

脚本会优先复用系统已有的 `agent-browser`，缺失时安装 CLI 与浏览器内核，并执行 `agent-browser doctor`

若缺少 **Node.js 18+**、`npm`、网络连接或命令权限，停止浏览器流程并向用户报告具体缺口，不得改用其他后台浏览器伪装成功

## 可见浏览器硬约束

- 首次打开页面必须显式携带 `--headed`
- 不得静默降级为 headless 或后台无头模式
- 为本次诊断生成独立 `session_id`，所有平台和后续命令复用同一会话
- 示例：`agent-browser open "https://www.doubao.com/chat/" --session "<session_id>" --headed`
- 打开后立即执行 `agent-browser snapshot --session "<session_id>"`，确认页面已加载且窗口对用户可见
- 任务完成或中止时执行 `agent-browser close --session "<session_id>"`

## 身份与授权边界

登录、重新登录、账号选择、密码、验证码、OAuth 同意、设备授权和权限开通全部由用户本人完成

到达上述节点后暂停对应平台操作，说明用户需要完成的动作；用户确认后重新获取快照，不复用旧元素引用

## 采集边界

- 只执行 `brand-geo-audit` 已冻结的查询协议，不临时改写问法
- 四个平台串行、低频操作，不绕过验证码、风控、付费或平台限制
- 浏览器只采集页面、回答、引用、状态和截图，不直接判断推荐强度或计算评分

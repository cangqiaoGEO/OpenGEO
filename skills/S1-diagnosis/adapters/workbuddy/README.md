## WorkBuddy 宿主适配层

### 一、职责

本目录保存 `GEO诊断专家` 的 WorkBuddy 专属源码和发布脚本

`skills/S1-diagnosis/` 是领域核心，`adapters/workbuddy/expert/` 是专家发布模板，`~/.workbuddy` 和 ZIP 都是可重新生成的安装或分发产物

整体责任和端到端链路以 [工程架构](../../docs/ARCHITECTURE.md) 为准，浏览器与核心之间的稳定边界以 [宿主运行时契约](../../references/runtime/host-runtime-contract.md) 为准

### 二、源码与构建物

```text
adapters/workbuddy/
├── expert/                     # WorkBuddy 专属模板，不复制领域核心
│   ├── .codebuddy-plugin/
│   ├── agents/
│   ├── avatars/
│   ├── scripts/
│   └── skills/geo-browser-runtime/
└── scripts/
    ├── build_expert.py         # 组装专家目录并生成 ZIP
    └── install_local.py        # 校验、安装并注册到本机 WorkBuddy
```

构建时才把当前 `brand-geo-audit` 核心运行文件复制到专家包的 `skills/brand-geo-audit/`

WorkBuddy 正式浏览器链路由专家包内的 `geo-browser-runtime` 调用可见 `agent-browser`，不依赖仓库根部的 `node_modules`；`scripts/browser_collect.mjs` 是核心模块的独立 Playwright 开发工具，不属于本适配层

### 三、构建

从 `OpenGEO` 仓库根目录执行：

```bash
python3 skills/S1-diagnosis/adapters/workbuddy/scripts/build_expert.py
```

默认生成：

- `skills/S1-diagnosis/work/mvp-release/geo-diagnostic-expert/`
- `skills/S1-diagnosis/work/mvp-release/geo-diagnostic-expert.zip`

构建不会复制 `.env`、`work/`、`tests/`、`node_modules/`、缓存或适配层源码，并会拒绝包含疑似真实 API Key 的产物

### 四、本地安装与注册

确认已经安装 WorkBuddy 后执行：

```bash
python3 skills/S1-diagnosis/adapters/workbuddy/scripts/install_local.py
```

脚本先把构建结果复制到 WorkBuddy 专家目录下的临时安装位，用官方专家校验器检查后再原子替换并重新注册；注册失败时恢复旧安装

安装脚本不代替用户登录任何 AI 平台，也不读取或复制 `.env`

### 五、依赖与边界

- 构建脚本只依赖 Python 标准库
- 本地安装要求 WorkBuddy 自带的 `expert-manager` 脚本存在
- 浏览器运行时首次使用可能需要 **Node.js 18+**、`npm` 和网络连接
- 登录、账号选择、密码、验证码、OAuth、设备授权和权限开通由用户本人完成

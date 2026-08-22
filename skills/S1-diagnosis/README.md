## Brand GEO Audit

`brand-geo-audit` 是面向品牌生成式引擎表现的证据化诊断 Skill

它先建立业务语境、品牌实体和冻结查询协议，再采集消费者 AI 产品、官方 API 与公开内容证据，生成可追溯的分项诊断和 HTML 报告

当前方法学成熟度为 `experimental M1`，可用于 WorkBuddy MVP 诊断和数据积累，不能称为已经科学定型的 GEO 行业标准

### 一、先记住这个模型

```text
诊断核心源码 + WorkBuddy 适配源码
              ↓ 构建
        专家目录与 ZIP
              ↓ 安装
       本机 GEO诊断专家
```

仓库是唯一源码，`skills/S1-diagnosis/work/`、专家 ZIP 和 `~/.workbuddy` 都是可重新生成或本地运行的产物

完整的分层、运行链路和发布链路见 [工程架构](docs/ARCHITECTURE.md)

### 二、当前能力边界

- 当前 WorkBuddy 浏览器适配和官方 API 采集范围覆盖豆包、千问、DeepSeek 和腾讯元宝
- 消费者网页、官方 API 与 Web 内容生态证据分通道记录
- 浏览器采集通过宿主适配器执行，当前只发布 WorkBuddy 适配
- 登录、验证码、账号选择和授权由用户本人完成
- 数据不足时输出缺口，不把未知自动记为零分
- API Key 只从本地环境变量读取，不进入报告和专家包

产品目标和非目标见 [WorkBuddy 诊断专家目标](docs/PRODUCT_TARGET.md)

### 三、源码结构

| 路径 | 责任 |
|---|---|
| `SKILL.md` | Agent 控制流和诊断门槛 |
| `schemas/` | 研究、采集、证据、评分和审计契约 |
| `scripts/` | 确定性校验、采集、评分、审计和报告生成 |
| `references/` | 方法学、平台能力、运行契约和历史研究 |
| `adapters/workbuddy/` | WorkBuddy 专家模板、浏览器适配、构建和本地安装 |
| `tests/` | 契约、回归、报告和发布链路验证 |
| `work/` | Git 忽略的客户案例、实验、缓存和构建产物 |

当前实现清单见 [模块规格](docs/SPEC.md)，编码约束见 [工程规范](docs/CODING_STANDARD.md)

### 四、开发验证

从 `OpenGEO` 仓库根目录执行：

```bash
python3 -m unittest discover -s skills/S1-diagnosis/tests -p 'test_*.py'
python3 -m py_compile \
  skills/S1-diagnosis/scripts/*.py \
  skills/S1-diagnosis/adapters/workbuddy/scripts/*.py
```

完整运行命令和报告生成方式见 [运行手册](docs/RUNBOOK.md)

### 五、构建和安装 WorkBuddy 专家

```bash
python3 skills/S1-diagnosis/adapters/workbuddy/scripts/build_expert.py
python3 skills/S1-diagnosis/adapters/workbuddy/scripts/install_local.py
```

默认生成：

- `skills/S1-diagnosis/work/mvp-release/geo-diagnostic-expert/`
- `skills/S1-diagnosis/work/mvp-release/geo-diagnostic-expert.zip`

构建过程不会复制 `.env`、`work/`、`tests/`、`node_modules/`、缓存或适配源码自身，并会执行疑似密钥扫描

WorkBuddy 专属操作说明见 [WorkBuddy 适配层](adapters/workbuddy/README.md)

### 六、凭证与本地产物

复制 [.env.example](.env.example) 为本地 `.env` 后填写所需 Key

`.env`、`.env.*`、`work/`、`node_modules/`、`__pycache__/` 和 `*.pyc` 已被 [.gitignore](.gitignore) 排除

不要把真实 API Key 写入源码、示例、截图、报告、命令参数或提交历史；已经在聊天、截图或日志中暴露的 Key 应立即轮换

### 七、文档入口

- [工程架构](docs/ARCHITECTURE.md)：核心、宿主适配、构建物和运行时的关系
- [模块规格](docs/SPEC.md)：当前已经实现的能力与稳定语义
- [运行手册](docs/RUNBOOK.md)：验证、报告、构建和安装命令
- [产品目标](docs/PRODUCT_TARGET.md)：WorkBuddy 诊断专家的职责和 MVP 门槛
- [路线图](docs/ROADMAP.md)：方法学和验证能力的渐进路线
- [宿主运行时契约](references/runtime/host-runtime-contract.md)：浏览器、身份交接、密钥和产物边界

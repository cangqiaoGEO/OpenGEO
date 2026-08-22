## Brand GEO Audit 模块当前 v2 + R2 运行手册

### 一、适用范围

本文记录当前已经实现的 v2 链路、R1 诊断契约、R2 试点能力和 WorkBuddy 单专家发布适配

所有客户运行产物写入 `skills/S1-diagnosis/work/` 或任务临时目录，不进入可发布示例

### 二、验证研究包

```bash
python3 skills/S1-diagnosis/scripts/research_validate.py \
  skills/S1-diagnosis/examples/research_package_standard.json
```

### 三、验证 R1 诊断契约

```bash
python3 skills/S1-diagnosis/scripts/diagnostic_contracts.py \
  skills/S1-diagnosis/examples/research_package_standard.json \
  skills/S1-diagnosis/examples/diagnostic_package_standard.json
```

`DiagnosticRun` 是运行清单，新对象保存在独立诊断包中，现有 v2 研究包继续作为研究对象的权威来源

### 四、验证证据并评分

```bash
python3 skills/S1-diagnosis/scripts/evidence_validate.py \
  skills/S1-diagnosis/examples/research_package_standard.json \
  skills/S1-diagnosis/examples/evidence_package_measured.json

python3 skills/S1-diagnosis/scripts/geo_score.py \
  skills/S1-diagnosis/examples/research_package_standard.json \
  skills/S1-diagnosis/examples/evidence_package_measured.json \
  > /tmp/geo_result.json
```

### 五、质量审计、建议校验和报告

WorkBuddy MVP 默认直接从已验证的研究包和证据包生成查询族汇总与精简客户报告：

```bash
python3 scripts/mvp_report.py \
  geo_research_<brand>.json geo_evidence_<brand>.json \
  --summary-output <brand>_geo_summary.json \
  -o <brand>_geo_report.html
```

完整诊断要求四个核心 `query_type` 各有至少两个独立问法，并完成计划中的平台观测；条件不足时脚本仍可生成部分观测报告，但必须显示缺口

原有 `geo_score.py`、`quality_audit.py` 和 `geo_report.py` 保留用于内部实验、回归和兼容交付

```bash
python3 skills/S1-diagnosis/scripts/quality_audit.py \
  skills/S1-diagnosis/examples/research_package_standard.json \
  skills/S1-diagnosis/examples/evidence_package_measured.json \
  /tmp/geo_result.json > /tmp/geo_audit.json

python3 skills/S1-diagnosis/scripts/recommendation_validate.py \
  skills/S1-diagnosis/examples/research_package_standard.json \
  skills/S1-diagnosis/examples/evidence_package_measured.json \
  /tmp/geo_result.json /tmp/geo_audit.json \
  skills/S1-diagnosis/examples/recommendations_measured.json

python3 skills/S1-diagnosis/scripts/geo_report.py \
  skills/S1-diagnosis/examples/research_package_standard.json \
  skills/S1-diagnosis/examples/evidence_package_measured.json \
  /tmp/geo_result.json /tmp/geo_audit.json \
  --diagnostic-package skills/S1-diagnosis/examples/diagnostic_package_standard.json \
  -o /tmp/brand_geo_audit_report.html
```

默认 `diagnostic` 模式不发布实验性总分、字母等级和行动建议，内部校准时可显式改用：

```bash
python3 skills/S1-diagnosis/scripts/geo_report.py \
  skills/S1-diagnosis/examples/research_package_standard.json \
  skills/S1-diagnosis/examples/evidence_package_measured.json \
  /tmp/geo_result.json /tmp/geo_audit.json \
  skills/S1-diagnosis/examples/recommendations_measured.json \
  --report-mode experimental_score \
  -o /tmp/brand_geo_experimental_report.html
```

### 六、重复实验统计

重复实验文件属于本地运行产物，不随仓库默认发布：

```bash
python3 skills/S1-diagnosis/scripts/repeated_experiment.py \
  skills/S1-diagnosis/work/browser-artifacts/repeated-observation-experiment.json \
  --project-root . \
  --output skills/S1-diagnosis/work/browser-artifacts/stability.json
```

输出只描述重复性，不是 GEO 得分或事实准确性判断

### 七、验证 R2 试点与下游交接

```bash
python3 skills/S1-diagnosis/scripts/handoff_validate.py \
  skills/S1-diagnosis/examples/diagnostic_handoff_standard.json

python3 skills/S1-diagnosis/scripts/pilot_validate.py \
  skills/S1-diagnosis/work/r2-pilot/pilot-study.json \
  --project-root .
```

真实试点协议见 [R2_PILOT_PROTOCOL.md](R2_PILOT_PROTOCOL.md)，真实案例只放在 Git 忽略的 `work/` 目录

### 八、工程验证

```bash
python3 -m unittest discover -s skills/S1-diagnosis/tests -v
python3 -m py_compile skills/S1-diagnosis/scripts/*.py
python3 -m py_compile skills/S1-diagnosis/adapters/workbuddy/scripts/*.py
```

### 九、构建和安装 WorkBuddy 专家

仓库是 WorkBuddy 专家的唯一源码，`~/.workbuddy` 只作为本机安装目录

```bash
python3 skills/S1-diagnosis/adapters/workbuddy/scripts/build_expert.py
python3 skills/S1-diagnosis/adapters/workbuddy/scripts/install_local.py
```

默认构建产物写入 Git 忽略的 `skills/S1-diagnosis/work/mvp-release/`

构建脚本只复制运行所需的核心文件，不包含 `.env`、`work/`、`tests/`、`node_modules/` 或 `adapters/`，并在生成 ZIP 前执行密钥扫描

详细边界见 [工程架构](ARCHITECTURE.md) 和 [WorkBuddy 适配层](../adapters/workbuddy/README.md)

### 十、产物一致性

一次运行不得人工挑选同名旧产物

R1 已用 `DiagnosticRun` 记录运行状态与对象引用，生成报告前仍由 `geo_report.py` 对评分、审计和建议重新计算并拒绝过期结果

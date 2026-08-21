# S7 输出模板

## 复测记录

```markdown
---
type: Monitor Run
title: GEO 周测 YYYY-MM-DD
description: 固定 20 问在已记录平台上的本周观察。
status: draft
generated: { by: agent/workbuddy, at: <ISO 时间> }
sources:
  - id: weekly-question-set
    resource: ../weekly.md
    title: 20 问周测表
    author: human:brand-owner
    last_modified: <日期>
---

# 测试条件

- 日期：YYYY-MM-DD
- 可用平台：平台 A、平台 B
- 不可用平台及原因：无 / 平台名：原因
- 证据目录：evidence/YYYY-MM-DD/

# 逐题结果

| # | 问题 ID | 层级 | 平台 | 提及 | 推荐 | 引用源 | 准确性 | 证据 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1 | 品类推荐 | 平台 A | 否 | 否 | 未引用 | 无法验证 | evidence/YYYY-MM-DD/q01-platform-a.md | 原始回答已保存 |

# 汇总

- 仅统计实际可访问的平台；“无法验证”不计入正负变化。
- 本次为基线 / 与 YYYY-MM-DD 基线比较。

# 引用概念

- identity.md
- positioning.md
- audience.md

# AI 友好七特征自检

- 达标数：5 / 7
```

## 趋势报告

```markdown
---
type: Monitor
title: GEO 周测趋势 YYYY-MM-DD
description: 与同口径基线的观察性对比。
status: draft
generated: { by: agent/workbuddy, at: <ISO 时间> }
sources:
  - id: baseline-run
    resource: ../runs/YYYY-MM-DD.md
    title: GEO 周测基线
    author: agent/workbuddy
    last_modified: <日期>
  - id: current-run
    resource: ../runs/YYYY-MM-DD.md
    title: GEO 周测本次记录
    author: agent/workbuddy
    last_modified: <日期>
---

# 可比性结论

- 可比平台：
- 不可比项：

# 平台与层级趋势

| 平台 | 层级 | 基线提及 | 本次提及 | 变化 | 基线推荐 | 本次推荐 | 变化 | 基线正确 | 本次正确 | 变化 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |

# 观察与待确认

- 只陈述记录事实；不得将变化归因为发布、收录或算法更新，除非另有独立证据。
```

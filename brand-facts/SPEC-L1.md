# 品牌事实库 L1 规范（基于 Open Knowledge Format v0.2 子集）

品牌事实库是一个 [OKF](https://github.com/GoogleCloudPlatform/knowledge-catalog) 风格的 **bundle**：一棵 markdown 目录树 + YAML frontmatter，作为企业对外口径的**唯一事实源**。灵感来自 Karpathy 的 LLM Wiki 模式与 Google 开放知识格式（OKF v0.2），只取其最小子集（L1）。

## 为什么用它（对应 GEO 的四大痛点）

| GEO 痛点 | 机制 |
| --- | --- |
| 全网口径不统一 | 所有内容 Skill 只准引用 bundle 内概念 |
| 证据链无法验证 | `sources` + 可信度信号（author/last_modified）就是机器可读的证据链 |
| AI 引用过期信息 | 价格/活动类概念必填 `stale_after`，产文前日期比较即阻断 |
| 内容可信度分层 | `verified` 三级信任：unverified → machine-confirmed → **human-reviewed**（老板确认过） |

## L1 字段（只用这六个）

```yaml
---
type: Product            # 必填：Brand Identity | Positioning | Audience | Product | Boundary | FAQ | Conversion Entry | Evidence | Monitor
title: 产品名
description: 一句话说明
status: draft            # draft(未审不得引用) | stable | deprecated
stale_after: 2026-12-31  # 价格/活动/数据类必填；过期即阻断引用
generated: { by: agent/<model>, at: 2026-08-21T10:00:00Z }
verified: { by: human:boss, at: 2026-08-21T12:00:00Z }   # 老板确认即追加
sources:                 # Evidence 类必填
  - id: media-report
    resource: https://example.com/report
    title: 某媒体报道
    author: team:media
    last_modified: 2026-08-01
---
```

## 运行规则（Karpathy 三操作）

- **ingest**：新资料 → AI 写成 draft 概念 + 更新 index/log → 人工审核 → stable + verified；
- **query**：S2~S5 产内容只读 bundle，好答案沉淀回 faq.md；
- **lint**（每周）：过期概念、draft 积压、断链、口径冲突（identity 与各页品牌名 diff）→ 进周报。

## 保留文件

`index.md`（目录导航，根部可带 `okf_version: "0.2"`）与 `log.md`（更新史，S7 每周追加）。

明确不用（L1 阶段）：executor/attester 代码、usage_window、per-claim 脚注——避免过度工程。诊断分数的 Attested Computation 语义列入 roadmap。

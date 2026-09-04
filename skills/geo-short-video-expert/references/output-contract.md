# MVP输出契约

## 对话阶段一：选题

先输出状态 `WAITING_FOR_TOPIC_APPROVAL` 和恰好 3 个选题。每个选题包含：大字标题、核心判断、目标观众、唯一意图词、stable 事实、CTA。不要提前附完整口播。

## 对话阶段二：口播成品

用户选择后严格按以下顺序输出：

### 1. 当前状态

写 `SCRIPT_READY`，并注明用户主题与所选选题。

### 2. 封面大字

- 主标题：8–18 个汉字，必须含 GEO 或明确品类词；
- 品牌角标：`仓桥智能 · GEO`；
- 不使用无来源百分比或绝对效果承诺。

### 3. 3秒钩子

用 1–2 个短句直接给冲突、结果或筛选条件，不自我介绍。

### 4. 纯口播稿

目标 45–60 秒；短句、口语化、先结论后理由；只回答一个购买前问题。镜头指令、Markdown 标题和引用路径不得混入口播正文。

### 5. 大字卡

输出 6–10 张。每张包含“卡号｜大字文案｜对应口播段”，大字文案尽量不超过 18 个汉字。一张卡只表达一个判断，首卡是核心冲突，末卡是稳定 CTA。

### 6. 发布配文与标签

配文不超过 80 个汉字；提供 3–5 个标签，至少包含 `#GEO` 和一个稳定意图词标签。

### 7. 校验

列出：口播估算时长、AI 友好七特征达标数、引用的 stable 文件、排除的 draft/待确认内容、风险表达检查。

## 文件产物

需要落盘时使用：

```text
workbuddy-output/short-video/<YYYY-MM-DD>-<topic-slug>/
├── 00-geo-material-map.md
├── 01-brief.md
├── 02-topic-options.md
├── 03-spoken-package.md
├── 04-teleprompter.txt
└── spoken-script-check.json
```

## 状态

只使用：`WAITING_FOR_THEME`、`FACT_BLOCKED`、`WAITING_FOR_TOPIC_APPROVAL`、`SCRIPT_READY`。

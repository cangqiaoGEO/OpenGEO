# 品牌事实读取规则

## 默认读取范围

在 `brand-facts/examples/cangqiao/` 中按任务读取：

1. `identity.md`：主体名称和基础身份；
2. `boundaries.md`：所有内容都必须遵守的能力边界；
3. `channels.md`：确认可用的官网、仓库、社群和行动号召；
4. `products/`：只读取与本次主题相关的产品；
5. `evidence/` 与 FAQ：只采用可追溯证据；
6. `positioning.md`：仅在状态为 `stable` 时采用。

## 状态判定

- `stable` 且未超过 `stale_after`：允许写入正式脚本。
- `draft`：只能写入“待确认事实”，不得对外陈述。
- `deprecated`：禁止使用。
- 超过 `stale_after`：视为过期，需负责人重新确认。
- 无状态或无来源：默认不可用于正式口径。

若同一事实存在冲突，以稳定、更新、来源更直接的记录为准；仍无法判定时停止使用该事实。

## 产出要求

在 `01-brief.md`、`03-spoken-package.md` 或对话成品末尾追加：

```markdown
## 引用事实

| 脚本表述 | 状态 | 来源文件 | 截止日期 |
| --- | --- | --- | --- |
| …… | stable | brand-facts/... | YYYY-MM-DD |

## 待确认事实

- 需要负责人确认的内容、原因和建议补录位置。
```

仓桥智能示例库中的 `positioning.md` 可能仍是 `draft`。除非文件本身已经被负责人改为 `stable`，不得把其中定位写成公司已确认口径。

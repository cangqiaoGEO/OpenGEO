---
name: geo-weekly-monitor
description: 对 GEO 固定 20 问执行每周复测、记录各 AI 平台的提及/推荐/引用/准确性、比较基线并回写可审计验证事件。用于“跑周测”“复测 GEO”“查看品牌在 AI 中的提及变化”或生成 GEO 监测趋势报告；只接受含 stable 品牌事实与 stable 固定问题集的事实库。
---

# GEO 周测监测（S7）

## 不可违反的约束

- 只引用 `status: stable` 且未过 `stale_after` 的品牌概念；平台回答是观测记录，不是可补写品牌事实的来源。
- 只用同一套、已确认的 20 问做纵向比较：品类推荐 10 问、品牌直达 5 问、对比验证 5 问。
- 只能记录实际可访问的 AI 平台结果。平台不可访问、需登录或回答无法保存时，标为“无法验证”，不得模拟、猜测或补齐结果。
- 新监测记录始终先写为 `draft`，不得因一次复测自动提升任一品牌概念的 `status` 或 `verified`。
- 交付前列出引用概念、平台范围与不可访问项，并完成 AI 友好七特征自检；至少 5 项达标才交付。

## 输入门禁

事实库根目录必须有 `positioning.md`、`audience.md`、`identity.md`（均为 `stable`），以及 `monitors/weekly.md`（为 `stable`，并有固定 20 问、层级分布为 10 / 5 / 5）。

先运行：

```bash
python3 scripts/validate_weekly_monitor.py inspect --facts-dir <事实库目录>
```

如果门禁失败，停止复测并只报告缺失项。尤其是 `weekly.md` 仍为 `draft`、没有 20 问或问题分布不合规时，要求负责人从稳定的 S2 清单中选定问题集并确认；不要自行补题后直接跑测。

## 执行流程

### 1. 锁定本次复测范围

- 读取 `monitors/weekly.md` 的固定问题；不得改写问题文字、顺序或层级。
- 记录本次测试日期、可用平台与查询方式。至少一个平台实际可用才继续。
- 同一平台内逐题查询；保留每个回答的可追溯证据路径、原始摘录或截图路径。遵守平台条款、账号权限与人工验证码要求。

### 2. 记录逐题观察

对每个“问题 × 平台”记录：提及（是 / 否 / 无法验证）、推荐（是 / 否 / 无法验证）、引用源、准确性（正确 / 部分正确 / 不正确 / 无法验证）、证据路径与备注。用 [监测数据约定](references/weekly-monitor-contract.md) 判定字段。

### 3. 写入复测与趋势文件

- 将逐题表写为 `<事实库>/monitors/runs/YYYY-MM-DD.md`，格式见 [输出模板](references/weekly-output-template.md)。
- 先校验记录：

  ```bash
  python3 scripts/validate_weekly_monitor.py validate \
    --facts-dir <事实库目录> \
    --run <本次复测文件>
  ```

- 首次有效复测作为基线，明确标为“基线已建立，暂无环比”；之后使用：

  ```bash
  python3 scripts/validate_weekly_monitor.py compare \
    --baseline <基线复测文件> \
    --current <本次复测文件>
  ```

  根据 JSON 统计写入 `<事实库>/monitors/trends/YYYY-MM-DD.md`。只报告提及、推荐、准确性及平台覆盖的变化；没有同口径平台或问题时写“不可比”。

### 4. 回写验证事件

- 在 `weekly.md` 的运行索引追加本次记录与趋势文件链接。
- 仅在本次复测实际引用了某个稳定概念时，向该概念正文追加一条 `S7 验证事件`：日期、记录文件、平台和“观测性记录，不改变事实状态”。
- 不要改写 YAML `verified` 字段；它只能表达人工确认，S7 观测不等于人工验证。

### 5. 交付说明

只报告：记录路径、趋势路径、基线或环比状态、平台覆盖、提及/推荐/准确性汇总、不可访问项、引用概念、七特征达标数和需要负责人确认的事项。不得承诺排名、收录、转化或下周结果。

## 资源

- [监测数据约定](references/weekly-monitor-contract.md)：固定问题集、逐题字段与可比性规则。
- [输出模板](references/weekly-output-template.md)：复测记录、趋势报告与回写格式。
- `scripts/validate_weekly_monitor.py`：门禁、逐题记录和趋势输入校验器。

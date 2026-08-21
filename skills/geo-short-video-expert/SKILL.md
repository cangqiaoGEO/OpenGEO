---
name: geo-short-video-expert
description: 在 WorkBuddy 中根据用户提供的 GEO 短视频主题，从 OpenGEO 稳定事实和三层意图词中生成 3 个主题内选题；用户确认后生成 45–60 秒纯口播稿、封面大字标题、6–10 张大字卡和事实校验。用于 GEO 口播、视频号/抖音大字报、公众号视频内容、公司 IP 矩阵或明日 MVP 演示；不负责拍摄、混剪、字幕、发布或浏览器诊断。
---

# GEO短视频口播专家（MVP）

## 目标

把用户提供的主题与 OpenGEO 事实库结合，快速完成“主题内选题 → 人工确认 → GEO 口播稿 → 大字卡”。优先让 Agent 准确识别品牌、品类、意图和事实，同时保证真人观众能听懂。

## 边界

1. 要求用户提供主题。主题缺失时只询问主题，状态设为 `WAITING_FOR_THEME`，不要自行决定主题。
2. 只把 `status: stable` 且未过期的内容写成事实；`draft`、过期或无来源内容列为待确认。
3. 不编造比例、案例、客户评价、排名、效果、资质、价格或合作关系。
4. `7000 元/月` 等价格只有进入稳定产品/价格事实后才能对外使用。
5. 先输出恰好 3 个选题，等待用户选择；未经选择不要生成正式口播稿。
6. 只交付文字内容，不生成拍摄单、SRT、成片、混剪计划或发布动作。
7. 大字报以“AI 可识别优先、人类能看懂为底线”；不追求花哨转场、滤镜或爆款模仿。
8. Agent Browser、平台登录与真人验证属于诊断工具，不属于本 Skill。

读取事实时遵循 [references/brand-facts.md](references/brand-facts.md)，按 [references/opengeo-materials.md](references/opengeo-materials.md) 路由材料。参考样片只使用 [references/reference-video-style.md](references/reference-video-style.md) 中已经核验的文案结构。

## 工作流

### 1. 接收主题并核验材料

记录用户原始主题，不替换成相邻主题。用户未指定时长和平台时，默认 60 秒、视频号/抖音通用版。

运行材料检查：

```powershell
python scripts/check_opengeo_materials.py --repo "<OpenGEO项目目录>" --output "<任务目录>/00-geo-material-map.md"
```

检查结果不是 `READY` 时停止创作并列出缺失材料。检查成功时只在回复中简报“OpenGEO 材料：READY”，不要在演示对话中展开冗长材料清单。

### 2. 输出 3 个主题内选题

从稳定意图词、FAQ、边界、产品、诊断基线与公开渠道中合成恰好 3 个角度。每个选题只显示：

1. 大字标题；
2. 一句话核心判断；
3. 目标观众；
4. 唯一 GEO 意图词；
5. 可使用的稳定事实；
6. 建议 CTA。

标题必须包含 `GEO` 或明确 GEO 品类词；不得为了套样片使用无来源百分比。输出后把状态设为 `WAITING_FOR_TOPIC_APPROVAL` 并停止。

### 3. 生成口播与大字卡

用户选择后，按 [references/output-contract.md](references/output-contract.md) 的固定顺序直接在对话中交付：

1. 封面大字标题；
2. 3 秒钩子；
3. 45–60 秒纯口播稿；
4. 6–10 张大字卡；
5. 发布配文与 3–5 个标签；
6. AI 友好七特征检查；
7. 事实来源和风险检查。

口播使用短句、先给结论、一条视频只回答一个购买前问题。大字卡每张只表达一个判断，正文尽量不超过 18 个汉字；封面同时出现品牌角标、GEO 品类词和核心冲突。

把纯口播保存为 `04-teleprompter.txt` 后运行：

```powershell
python scripts/check_spoken_script.py --input "<任务目录>/04-teleprompter.txt" --target-seconds 60 --required-term GEO --required-term 仓桥智能 --output "<任务目录>/spoken-script-check.json"
```

检查失败时先改稿；检查通过后把状态设为 `SCRIPT_READY`。不要继续询问素材或提出剪辑步骤。

## 质量线

执行 [references/quality-gates.md](references/quality-gates.md)。至少满足：主题未漂移、事实可追溯、口播时长合格、标题含 GEO、未使用无来源数字、AI 友好七特征达到 5/7。

## 触发示例

- “主题是中小企业适不适合做 GEO，先给我 3 个选题。”
- “我选第 1 个，生成 60 秒口播稿和大字卡。”
- “把这段 GEO 内容改成 Agent 更容易读取的大字报口播。”

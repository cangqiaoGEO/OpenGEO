# 附录 A 模板与提示词

## A1 品牌事实库模板（11 字段）

| 字段 | 填写内容 |
| --- | --- |
| 企业身份 | 全称、品牌名、成立信息、所在地 |
| 产品身份 | 产品名、版本、类别、别名（简称与全称绑定） |
| 核心定位 | 一句话（你的核心标签） |
| 目标客户 | 行业、规模、角色、典型场景 |
| 核心能力 | 3~5 项可验证功能 |
| 差异点 | 与竞品的具体区别（能验证，不喊口号） |
| 证据 | 案例、数据、资质、客户评价 |
| 边界 | 不支持什么、不适合谁（AI 最信敢说边界的品牌） |
| 常见问答 | 采购、价格、部署、售后（≥10 问） |
| 转化入口 | 联系、预约、试用、购买方式 |
| 信息状态 | 来源、负责人、更新时间 |

进阶版（OKF 格式、可被 Agent 直接引用）见 [opengeo-spec/template](https://github.com/cangqiaoGEO/opengeo-spec/tree/main/template)，真实示例见 [opengeo-spec/examples/cangqiao](https://github.com/cangqiaoGEO/opengeo-spec/tree/main/examples/cangqiao)。

## A2 AI 员工首篇文章提示词（可直接粘贴）

```text
你是我公司的 GEO 内容专员。请根据以下品牌事实库信息，写一篇公众号文章。

【品牌事实库】（粘贴 A1 的内容）
【目标问题】（选一个意图词，如：多门店企业怎么选道闸）

要求：
1. 八段式结构：标题（含核心标签）→40~80字核心答案→为什么重要→原理→方案对比（含表格）→真实案例+数据→下一步行动→FAQ（5问）；
2. 三层标题，清单式排版；
3. 全文≥800字，≥3个证据点；只用事实库里的信息，不许编造；
4. 结尾放咨询入口；
5. 写完后自查「AI 友好七大特征」，报告达标几条（≥5才交付）。
```

## A3 20 问自测题集模板

见[第二篇 2.4](ch02.md#24-30)。

## A4 七技（Skills）创建指令

S1~S7 全部开源：[opengeo-skills](https://github.com/cangqiaoGEO/opengeo-skills)（S1–S7 全量）与 [opengeo-agentready](https://github.com/cangqiaoGEO/opengeo-agentready)（S6）——每个文件含可直接粘贴到 Agent 平台的创建指令。

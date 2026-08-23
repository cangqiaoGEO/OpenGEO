# OpenGEO · 仓桥 GEO 作战系统

> **让 AI 看见、相信并推荐你的产品——方法全部开源，因为方法透明是对抗「割韭菜」的唯一解。**

GEO（Generative Engine Optimization，生成式引擎优化）正在成为企业获客的新战场：客户有需求先问 AI，AI 只推荐 3~4 家——没上牌桌的企业正在无声出局。

但眼下的 GEO 培训市场，正在把这个真需求做成一场「烧荒」。

## 为什么开源这个项目（我们看到的行业乱象）

我们研究了市面上的 GEO 课程与沙龙，反复看到同一套模式：

1. **课程一半时间在教「怎么靠 GEO 赚钱」，而不是「怎么做好 GEO」**——卖铲子的在教你卖铲子；
2. **把「同城沙龙模式」当教学模块**——教学员复制同一场沙龙回本地收人，标准的培训裂变；
3. **「N 小时讲透、现场跑通全流程」式过度承诺**——真实节奏是：地基（官网/百科/认证账号）1~2 周、内容持续 12 周、复测才见分数变化，几小时现场"建成"的系统只能是演示壳；
4. **零合规教育**——不讲白帽黑帽、不讲 315 曝光过的 AI 投毒黑产、不讲信任分归零难洗白，学员学完大概率去铺量投毒；
5. **没有可验证的客户案例**——只有「赚钱案例」，没有客户效果；
6. **没有效果指标体系**——不提收录率、推荐位、上榜率、复测，交付不对效果负责；
7. **完整的销讲逼单动线**——下午铺认知，傍晚一对一成交。

企业老板被这样割过一轮之后，会对 GEO 这件事本身失去信任。**这对所有认真做事的人都是灾难。**

所以我们把方法论、教材、工具、模板全部开源。你可以照着这个仓库自己搭，一分钱不花；搭不动再来找我们——我们靠交付与托管赚钱，不靠信息差。

## 口径宪章（本项目及贡献者的底线）

**三不承诺：**
- 不承诺排名第一；
- 不承诺被所有 AI 推荐；
- 不承诺统一的见效天数。

**三只承诺：**
- 诊断分数（六维评分，基线可测）；
- 改进清单（P0/P1/P2，按优先级可执行）;
- 复测对比（同一套问题定期再测，分数变化说话）。

**六条白帽红线：** 不批量铺低质软文 / 不编造案例数据 / 不伪装用户发广告 / AI 内容必须人工审核后发布 / 不泄露客户隐私 / 不做只给机器看的垃圾内容。

> 任何违背上述口径的 Issue/PR（例如「保排名话术」「批量投毒工具」）将被直接关闭。

## 系统架构：一库、一脑、七技、一环

```
① 品牌事实库（OKF 格式，唯一事实源）
        ↓
② GEO 总控 Agent（读事实库 · 派任务 · 出周报）
        ↓
③ 七个专业 Skill（各干各活，只准引用事实库）
   S1 诊断  S2 意图词  S3 内容  S4 短视频  S5 信源发布  S6 官网地基  S7 复测监测
        ↓
④ 复测闭环（基线 → 优化 → 复测 → 对比 → 下一轮）
```

口诀：**一库定口径，一脑管调度，七技各干活，复测闭了环——老板两件事：定标签、审事实。**

与市面「GEO Agent」的区别就一句话：**别人的 Agent 止于「生成方案」，这套系统闭环到「复测分数」。**

## 组织与仓库地图（六层产品框架）

OpenGEO 是一个开源组织（[github.com/cangqiaoGEO](https://github.com/cangqiaoGEO)），按「六层 + 治理」拆为独立仓库，本仓为门户：

| 层 | 仓库 | 一句话 | 对标 |
| --- | --- | --- | --- |
| 门户 | **OpenGEO**（本仓） | 初衷、口径宪章、[详解教程](https://cangqiaogeo.github.io/OpenGEO/course/)、[避坑指南](guides/)、官网 | — |
| L0 规范 | [opengeo-spec](https://github.com/cangqiaoGEO/opengeo-spec) | 品牌事实库 OKF 规范与模板——唯一事实源 | 无（独创层） |
| L1 测量 | [opengeo-audit](https://github.com/cangqiaoGEO/opengeo-audit) | 中国引擎六维可见度诊断与周测 | Profound Monitor / Peec |
| L2 洞察 | [opengeo-insights](https://github.com/cangqiaoGEO/opengeo-insights) | 意图词、内容差距、竞品对标、地基体检 | Scrunch Insights |
| L3 执行 | [opengeo-skills](https://github.com/cangqiaoGEO/opengeo-skills) | 七技规格、总控 Agent、平台实现（WorkBuddy v1） | Profound Agents / Frase |
| L4 站点 | [opengeo-agentready](https://github.com/cangqiaoGEO/opengeo-agentready) | llms.txt / JSON-LD / AI 可读页面生成 | Scrunch AXP |
| L5 基准 | [opengeo-index](https://github.com/cangqiaoGEO/opengeo-index) | 行业 × 城市 × 引擎公开基准 | Profound Index |

> 2026-08-23 评审决议：主仓只做门户 + 课程 + 治理，`skills/`、`brand-facts/`、`system/` 已迁出（对照表见 [MIGRATION.md](MIGRATION.md)）。**建设顺序：先 L0 规范 / L1 测量 / L3 执行，L2 / L4 / L5 为第二批。**

定位一句话：**GEO 的开放标准与开源工具层——闭源 SaaS 把「看见」卖 399 美元/月，OpenGEO 把「看见」变成公共品。** 调研与框架全文见 [docs/positioning.md](docs/positioning.md)。

## 快速开始（三步）

1. **给自己打个分**：按 [opengeo-audit/brand-geo-audit](https://github.com/cangqiaoGEO/opengeo-audit/tree/main/brand-geo-audit) 跑一次品牌诊断，拿到六维基线分数与 P0 清单；
2. **建品牌事实库**：复制 [opengeo-spec/template](https://github.com/cangqiaoGEO/opengeo-spec/tree/main/template)，填 11 类概念文件（你公司对外口径的唯一底稿）；
3. **跑 28 天循环**：教材第八章路线图——第 1 周打地基、第 2 周上内容、第 3 周建权威、第 4 周复测对比。

**官方参考实现（v1）：Tencent WorkBuddy。** 按 [opengeo-skills/system/workbuddy-implementation.md](https://github.com/cangqiaoGEO/opengeo-skills/blob/main/system/workbuddy-implementation.md) 半天即可搭好整套系统：本地文件夹项目=事实库，专家团=总控 Agent，自建 Skill=七技，自动化定时任务=复测闭环，IM 助理=老板审批入口。系统本身平台无关——七技是提示词规格，任何 Agent 平台（Claude Code、扣子、Dify 等）都能实现，欢迎 PR 其他平台的实现。

## 案例数据声明

教材中的行业案例（旅游、KTV、制造业、餐饮等）数据来自各操盘方的公开课程与访谈分享口径，**未经独立审计**，仅用于说明方法，不构成效果承诺。涉及诊断分数的对比示例中，除公众知名品牌外均已匿名化。

## 公开自测：我们自己就是第一个案例

[opengeo-spec/examples/cangqiao](https://github.com/cangqiaoGEO/opengeo-spec/tree/main/examples/cangqiao) 是本组织的第一个**真实** bundle——仓桥智能自己的品牌事实库。基线诊断（2026-08-21）：**综合 18.0 分，D 级「缺失，几乎不可见」**——精确品牌词在搜索引擎零结果。我们把这个低分公开，按仓库里的方法执行 28 天，每周复测更新分数。**不信方法有效，就看这个分数动不动。**

## Roadmap

- [x] v0.2：真实品牌完整事实库 bundle 示例（仓桥智能，含基线诊断与周测表，公开自测中）
- [ ] v0.3：L1 自动采集器（三引擎）+ L3 WorkBuddy 七技通关 —— 见各层仓库 Roadmap
- [ ] v0.4：L0 事实库 lint 在 CI 运行；第二批 L2 / L4 / L5 启动

每两周发布一次组织级 release note（中文，GitHub Releases + 公众号 + 知乎）。

## 许可证

- 代码（各层仓库脚本）：[MIT](LICENSE)；opengeo-index 数据：CC BY 4.0
- 教材与文档：[CC BY-SA 4.0](LICENSE-docs.md)——你可以自由使用与改编（包括商用授课），但必须署名并以相同协议共享。**选择 ShareAlike，就是为了让任何人无法把公开的方法改头换面变回信息差生意。**

---

仓桥智能科技 · 杭州 ｜ 让每一条卖点都答得出：谁写的、谁核的、过没过期。

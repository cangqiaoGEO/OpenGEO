# OpenGEO 双引擎架构（v3 · 2026-08-29）

> 取代 restructure v2 六仓方案。承接《双引擎品牌出海获客方案》。
> 一句话：同一份工厂内容资产，一次生产、双面分发、统一归因——**社媒引擎**在推荐流里换今天的询盘，**GEO 引擎**在 AI 问答面里换明天的被推荐权。

## 三项决策（2026-08-29 定）

1. **矩阵发布 / 账号管理 → 自建并开源**。不采购 SaaS，自研社媒执行引擎并开源，新增 `opengeo-matrix` 仓（= gitroomhq/postiz-app 分叉，路径 A），与 `opengeo-platform` 并列为「器」层双引擎。
2. **账号基建不写白帽对客承诺**。购号 / 刷机 / 养号 / 住宅 IP 照市场现实操作，不把「仅白帽」写进对客承诺；开源工具本身走官方 API 保持干净，灰度环节隔离在服务侧与学院。
3. **双引擎套餐 → 进组织叙事**。双引擎解决方案作为组织门面明说；open-core 下方法论与工具开源、套餐定价与托管商业化。

## 架构分层

```
                    门户 · OpenGEO
        品牌出海课(道) · 治理宪章 · OpenGEO 学院(术)
                          ▲
        ┌─────────────────┴─────────────────┐
        │   共享脊柱：品牌事实库(OKF) + Bundle 客户仓   │
        │        （两台引擎的集成契约 IF-A/IF-D）        │
        └─────────────────┬─────────────────┘
              ╱                          ╲
   ◐ GEO 引擎 · 可见度              ◑ 社媒引擎 · 执行
   opengeo-spec   (L0 法)          opengeo-matrix (器·发) ★新增
   opengeo-platform(器·测)           · 账号中心(官方 OAuth)
   opengeo-skills (术·内容)          · 发布中心(矩阵分发/定时)
   opengeo-agentready(站点)          · 互动收件箱(评论/私信)
   opengeo-index  (基准)             · 线索池 CRM(八要素)
                                     · AI 创作台(脚本/文生视频/混剪/口播)
              ╲                          ╱
        ┌─────────────────┴─────────────────┐
        │  统一层：双引擎归因判决表（IF-D）          │
        │  content_ref 联表：社媒发布×询盘 + GEO 引用  │
        └───────────────────────────────────┘
```

与 v2 唯一结构性差别：「器」层从单引擎（platform 只测量）变**双引擎**（platform 测量 + matrix 执行），由 spec 的 Bundle 契约（新增 IF-D）把两者焊在同一客户仓上。其余五仓定位不变。

## 仓库清单（v3）

| 仓库 | 层 / 角色 | v3 变化 |
| --- | --- | --- |
| OpenGEO | 门户 · 道/治理/术 | 加品牌出海 CEO 课 + OpenGEO 学院；治理更新（分层立场）；README 改双引擎叙事 |
| opengeo-spec | L0 · 法/标准 | 新增 IF-D 矩阵接口（RFC-0007）+ 双引擎归因 |
| opengeo-platform | 器 · 测量 | 归因任务升级双引擎，接收 matrix 发布记录联表 |
| **opengeo-matrix** | **器 · 执行 ★新增** | postiz-app 分叉，社媒执行引擎（见 OPENGEO.md 路线图） |
| opengeo-skills | 术 · 内容 | S4/S5 接入 matrix 的 AI 创作台与发布中心 |
| opengeo-agentready | L4 · 站点 | 不变 |
| opengeo-index | L5 · 基准 | 不变 |
| pandasofa-bundle | 交付包样板 | 跑通双引擎闭环 |

净变化：+1 仓（opengeo-matrix）+ spec 一份接口文档。延续 v2 反臃肿原则，新引擎用一个 monorepo 承载。

## opengeo-matrix 选型结论

代码级评估：**postiz-app（8/10）> mixpost Lite（6.5/10）**。postiz 原生覆盖账号中心（37 平台官方 OAuth）、发布中心、AI 创作台（含文生视频 Veo3），已带简体中文包；AGPL-3.0 与「matrix 保持开源」同向。mixpost 虽 MIT 但 Lite 被 Pro 阉割（仅 3~4 平台、无收件箱/CRM/AI、单用户）。agent-media 是付费 API 外壳（底层 Seedance），作为 AI 创作台调用的视频 API，非 fork 底座。详见 opengeo-matrix/OPENGEO.md 与选型决策卡。

## 账号基建分层立场（写入治理）

| 层 | 立场 | 落点 |
| --- | --- | --- |
| 开源工具 | 白帽 · 官方 API | opengeo-matrix 仅收官方授权发布；不含购号/刷机/养号/反风控自动化 |
| 服务侧代运营 | 务实 · 按市场现实 | 购号/刷机/养号/住宅 IP 由服务团队操作，不对客承诺仅白帽；建议隔离到独立服务实体 |
| OpenGEO 学院 | 教学 · 术层公益课 | 账号注册/刷机/海外网络/IP 配置实操 |
| 法律底线 | 不可逾越 | 不做诈骗/数据窃取/隐私侵犯 |

## open-core 边界 v3

- **开源**：spec 标准 / platform 测量核心 / **matrix 执行核心** / skills / agentready / index schema / 课程 / 双引擎架构作门面
- **商业（仓桥）**：OpenGEO Cloud 托管（platform + matrix）/ 双引擎代运营套餐（含定价）/ 账号基建服务 / Index 行业报告 / 特训营

分界：方法论、标准、工具本体开源；托管、服务、账号基建、定价商业化。AGPL 只约束闭源代码、不约束卖服务——只要 matrix 核心保持开源，AGPL 与本模型同频。

## 落地路线

- **P0（2 周）**：建 opengeo-matrix 仓（✅ postiz 分叉已就位）+ spec 加 IF-D（✅ RFC-0007）；跑通「账号 OAuth → 取 Bundle approved 内容 → 发布 → 回写 publish_record」最小闭环；pandasofa 产 5–10 条英文内容验证。
- **P1（1 月）**：双引擎归因联表，pandasofa 出第一张双引擎判决表；matrix 接 AI 创作台（S4 脚本→出片）；OpenGEO 学院首批课上线。
- **P2（季度）**：门户 README 改双引擎门面；治理宪章更新分层立场；双引擎套餐定价；跨境 playbook 扩建材/储能/机械。

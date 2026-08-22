## 品牌 GEO 调研基础协议

### 一、目的

本协议定义当前 v2 在正式采集 AI 引擎回答之前必须成立的三个对象：`ResearchScope`、`DomainContext`、`QueryProtocol`

它解决两个不同问题：

- `ResearchScope` 与 `DomainContext` 保证测量对象正确
- `QueryProtocol` 保证不同引擎和竞品使用可比较的测量方法

### 二、ResearchScope

`ResearchScope` 描述一次调研的边界，不承载调研结论

必须明确：

- 品牌
- 业务领域
- 地域市场
- 查询语言
- 目标受众
- 截止日期
- 调研深度
- 排除范围

只有 `status=ready` 的范围才能支撑正式业务模型和冻结查询协议

用户只提供品牌时，范围保持 `draft`，未知的领域、市场、语言和受众必须显式暴露，不能由评分器猜测

### 三、DomainContext

`DomainContext` 是最小业务领域模型，不是完整行业报告

默认只研究与 GEO 查询设计直接相关的内容：

- 品牌定位
- 目标客户
- 客户问题
- 产品或服务
- 业务场景
- 直接竞品、替代方案和邻近玩家
- 高价值用户问题
- 尚未解决的关键未知

每项判断必须区分：

- `fact`：来源直接支持的事实
- `inference`：基于证据形成的推断
- `opinion`：研究者观点或方案主张
- `unknown`：尚无足够证据

`fact` 和 `inference` 必须引用来源，`fact` 至少引用一个已验证或部分验证来源

### 四、QueryProtocol

`QueryProtocol` 将业务模型转换为可执行查询集

每条查询必须关联：

- 目标客户
- 客户问题
- 高价值问题
- 商业价值
- 为什么值得测量
- 预期采集的证据
- 使用的 AI 引擎集合

冻结协议至少覆盖：

- `brand_direct`
- `category_recommendation`
- `solution`
- `brand_comparison`

冻结后所有查询使用同一引擎集合，竞品比较必须引用 `DomainContext` 中已经成立的竞品对象

### 五、深度与最低引擎数

| 深度 | 最低引擎数 | 定位 |
|---|---:|---|
| `quick` | 3 | 方向摸底 |
| `standard` | 3 | 正式单轮诊断 |
| `deep` | 5 | 多引擎深度诊断 |

以上只是协议门槛，不代表研究质量已经得到统计学验证

### 六、执行与校验

完整研究包结构：

```json
{
  "scope": {},
  "domain_context": {},
  "query_protocol": {}
}
```

执行校验：

```bash
python3 scripts/research_validate.py examples/research_package_standard.json
```

只有校验结果 `valid=true` 且查询协议为 `frozen` 时，才进入 AI 引擎回答采集阶段

### 七、批次 A 边界

批次 A 不负责：

- 登录或操作 AI 产品
- 采集真实 AI 回答
- 评分与等级
- 改进建议
- HTML 报告

这些能力分别属于后续证据、评分、质量审计和报告批次

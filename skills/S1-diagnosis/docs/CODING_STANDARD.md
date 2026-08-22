## AI Coding 工程规范

### 一、适用范围

本规范仅适用于 `skills/S1-diagnosis/` 模块内的 Skill、领域契约、Python 脚本、测试和工程文档

目标是让研究数据可追溯、评分逻辑可复算、模块职责可识别，并让人工评审能够沿着输入到产出的路径检查实现

### 二、阅读顺序

修改代码前按以下顺序建立上下文：

1. `skills/S1-diagnosis/README.md`
2. `skills/S1-diagnosis/docs/ARCHITECTURE.md`
3. `skills/S1-diagnosis/docs/SPEC.md`
4. `skills/S1-diagnosis/docs/CODING_STANDARD.md`
5. `skills/S1-diagnosis/SKILL.md`、相关 `references/` 和相邻代码

### 三、目录与依赖边界

- `schemas/` 保存跨 Agent 与脚本边界传递的稳定 JSON 契约
- `references/methodology/` 保存业务口径与人工判断规则
- `references/architecture/` 保存候选架构及迁移边界
- `references/runtime/` 保存运行规则和有核验日期的平台能力快照
- `references/studies/` 保存历史实验记录，不承担当前规范
- `adapters/` 保存宿主专属的专家定义、运行时桥接和发布脚本，不得让宿主字段泄漏到领域契约
- `scripts/` 保存确定性校验、计算和报告生成逻辑
- `tests/` 保存回归、契约、单元和端到端测试
- `examples/` 保存可运行示例，不保存真实客户敏感数据
- Agent 可以依赖领域契约，确定性脚本不得反向依赖 Agent 的临场推理
- 宿主适配器依赖核心契约，核心 Schema、评分和报告脚本不得反向依赖 WorkBuddy 安装目录或工具命令
- Web 搜索和文件写入属于副作用，领域校验与评分函数保持纯计算

### 四、领域数据规则

- `null` 表示未知或未采集，不能自动解释为 `false`、零分或正面证据
- 事实、推断、观点和未知必须显式区分
- 正式查询必须能追溯到目标客户、业务问题或业务场景
- 非法输入必须在评分前失败，禁止用默认值掩盖错误
- 契约发生不兼容变化时更新 `schema_version`
- 真实品牌案例不得成为通用 Schema、指标、阈值或测试 fixture 的唯一来源
- 删除任意真实品牌案例后，示例、测试和方法文档必须继续独立成立

### 五、代码可读性

- 函数只承担一个明确职责
- 状态、阈值、枚举和固定字段使用命名常量
- 导出函数、命名函数、可复用 helper 与文件读写函数使用文档字符串说明职责、输入和返回值
- 错误消息包含对象路径、实际值和目标约束
- 不引入与任务无关的依赖和抽象

### 六、测试与验证

默认验证顺序：

```bash
python3 -m unittest discover -s skills/S1-diagnosis/tests -v
python3 -m py_compile skills/S1-diagnosis/scripts/*.py
python3 -m py_compile skills/S1-diagnosis/adapters/workbuddy/scripts/*.py
```

修改契约时必须验证：

- 合法完整数据
- 合法但信息不足的数据
- 缺失字段和非法枚举
- 跨对象引用
- 缺失值语义
- 已知历史缺陷

修改报告生成时还必须验证 HTML 转义与结果一致性

### 七、协作与文档同步

- `skills/S1-diagnosis/docs/SPEC.md` 只描述模块定位和边界，不复制本规范
- `SKILL.md` 描述 Agent 控制流，`references/` 描述业务规则，代码实现确定性机制
- `docs/ARCHITECTURE.md` 说明核心、宿主契约、WorkBuddy 适配和生成产物的关系，适配层 README 只记录宿主操作
- 修改 Schema 时同步示例、验证器和相关参考文档
- Schema 与手写校验器均发生变化时，必须补充符合性测试，不能只验证 JSON 可解析
- 完成实现后报告实际运行的验证命令与未覆盖边界

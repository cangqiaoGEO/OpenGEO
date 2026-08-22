## GEO诊断专家

WorkBuddy 单角色专家，封装 `brand-geo-audit` 的研究、真实平台观测、证据校验、评分、质量审计和 HTML 报告流程

### 使用入口

用户只需选择“GEO诊断专家”并提供品牌、目标市场、业务领域和目标受众

专家内部通过随包提供的 `geo-browser-runtime` Skill 复用或首次安装 `agent-browser`，以可见浏览器窗口访问豆包、千问、DeepSeek 和腾讯元宝，不要求用户安装项目级 Playwright 或配置采集 selector

首次安装依赖宿主机已有 **Node.js 18+**、`npm` 和网络连接，WorkBuddy 可能要求用户确认一次本地命令执行权限；若环境不满足条件，专家会报告缺口

### 身份操作边界

登录、账号选择、密码、验证码、OAuth、设备授权和权限开通必须由用户本人完成

### 分类说明

专家主要产物是品牌 GEO 诊断报告，服务品牌营销与生成式搜索优化，因此归入 `05-MarketingGrowth`

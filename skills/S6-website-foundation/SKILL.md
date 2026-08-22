---
name: geo-website-foundation
description: 审计官网可访问、可抓取、品牌一致性、robots/sitemap、FAQ、联系入口和结构化数据，并从 OpenGEO 品牌事实库生成或整改单文件官网。用于“查官网地基”“生成 GEO 官网”或“补 FAQ 页面”；只使用 stable 且未过期的品牌事实。
---

# GEO 官网地基（S6）

## 两种模式

- **体检模式**：输入官网 URL 与品牌事实库，输出 7 条地基体检、证据和 P0/P1 整改清单。
- **生成模式**：输入品牌事实库，按行业设计语言生成单文件 HTML 官网或 FAQ 页面稿。

若用户同时要求体检和整改，先保留体检证据，再生成单独的整改稿；不得用整改后结果覆盖基线。

## 不可违反的约束

- 品牌名、行业、定位、产品、价格、团队、资质、客户、案例、数据、FAQ 和联系方式只能来自 `status: stable` 且未过 `stale_after` 的事实库概念。
- 不得根据品牌名称猜行业或定位，不得把模板中的示例品牌、120+ 客户、2015 年、占位团队或示例联系方式交付给用户。
- 缺失事实时省略对应公开主张并列出待补项；不得用“示例数据，稍后替换”的可见内容绕过事实门禁。
- 结构化数据必须与页面可见正文一致；未知字段删除，不填空字符串或假值。
- 只报告实际检查结果，不声称结构化数据、FAQ 或 sitemap 必然带来收录或推荐。

## 输入门禁

至少需要可引用的 `identity.md`、`positioning.md`、`products/`、`faq.md` 与 `channels.md`；需要受众、边界、团队、案例或数据时，再读取对应稳定概念和 `evidence/`。使用 [事实库约定](references/fact-library-contract.md) 判断资格。

生成模式在事实不足以形成品牌身份、至少一个产品/服务、FAQ 和联系入口时停止，只输出缺口清单。模板文件仅提供布局和组件，不是事实来源。

## 体检模式

对目标官网逐项保存可复查证据：

1. 可正常访问，并记录 HTTP、TLS、备案展示或区域限制；
2. 关键正文可由无登录客户端读取，不是整页图片或仅客户端空壳；
3. 品牌、服务、FAQ 与联系方式不被登录墙阻断；
4. `robots.txt` 和 `sitemap.xml` 可访问且没有明显阻断；
5. 品牌全称、简称与 `identity.md` 一致；
6. 存在可读 FAQ，正文与 FAQ 结构化数据一致；
7. 存在清晰、真实的联系入口。

额外检查：唯一 H1、H2/H3 层级、canonical、meta description、Organization/WebSite/FAQPage JSON-LD、移动端可用性和表单隐私说明。将无法验证项标为“未验证”，不得自动判为通过或失败。

输出表包含：检查项、状态、证据、风险、优先级和整改动作。P0 只用于访问、抓取、事实错误、结构化数据与正文冲突等阻断问题；其余列 P1。

## 生成模式

### 1. 建立事实与设计映射

- 从事实库读取行业与定位，不从名称推断。
- 读取 [行业设计语言](references/industry-design-map.md)，选择色板、字体、版式和组件；行业不在表中时按通用法则推导设计 token。
- 使用 [高端审美指南](references/design-aesthetic-guide.md)，但可访问性与内容真实性优先于视觉装饰。

### 2. 规划信息架构

按 [GEO 官网要求](references/geo-requirements.md) 选择有事实支撑的区块。最低包含：Hero/品牌简介、产品或服务、FAQ、联系入口和 Footer。团队、案例、统计、荣誉、价格与新闻只在有稳定事实和证据时加入。

JSON-LD 使用 `@graph` 组织 Organization、WebSite、FAQPage 及适用的 Product/Service/LocalBusiness；只输出正文中存在且可核验的属性。

### 3. 生成与校验

复制 `assets/site-template.html` 的结构与组件，替换全部示例文本和设计 token。技术要求：单文件 HTML、内联 CSS 和少量原生 JS、无外链字体、语义化标签、唯一 H1、响应式、键盘可用、支持 `prefers-reduced-motion`。

保存后运行：

```bash
python3 scripts/validate_site.py <生成的 HTML>
```

校验器用于阻止模板占位、无效 JSON-LD、多个 H1、FAQ 不一致和缺少基础 meta；它不替代人工事实审核与浏览器视觉检查。

### 4. 交付

默认保存为 `<内容库>/官网/待审/<品牌名>-官网.html`。同时输出：引用概念文件、遗漏区块及原因、7 条地基自检、七特征达标数和待人工审核项。不得自动部署或覆盖线上网站。

## 资源

- [事实库约定](references/fact-library-contract.md)：稳定事实、过期与引用边界。
- [行业设计语言](references/industry-design-map.md)：行业化视觉 token。
- [高端审美指南](references/design-aesthetic-guide.md)：排版、留白、响应式与动效。
- [GEO 官网要求](references/geo-requirements.md)：内容矩阵、语义 HTML、JSON-LD 与检查表。
- `assets/site-template.html`：必须清空全部示例事实后才能交付的组件骨架。
- `scripts/validate_site.py`：官网占位与结构校验器。

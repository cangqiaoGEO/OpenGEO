# GEO 官网结构要求

本参考定义可访问、可解析、可核实的官网结构。它能减少机器读取与实体识别障碍，但不保证任何 AI 引擎收录、引用或推荐。品牌事实库和实际可核验证据优先；没有稳定事实支撑的区块应省略并列为待补项。

---

## 一、内容覆盖矩阵（AI 引擎检索品牌时的核心问题）

官网内容必须能直接回答以下问题，每个问题对应一个页面区块（H2 级）：

| AI 引擎可能问的问题 | 对应区块 | 必含信息 |
|---|---|---|
| 这个品牌/公司是什么？ | 首页 Hero + 品牌简介 | 名称、一句话定位、成立背景 |
| 他们做什么/提供什么？ | 产品服务区 | 服务/产品清单（≥3 项）、每项说明、适用场景 |
| 他们做得好吗？可信吗？ | 数据实力 + 资质荣誉 | 量化数据（客户数/案例数/年限）、认证、奖项 |
| 谁在做这件事？（E-E-A-T） | 团队区 | 创始人/核心成员、背景经历、行业资历 |
| 价格/怎么合作？ | 产品服务卡内 + FAQ | 价格区间、合作流程（公开或引导咨询） |
| 别人怎么说？ | 案例 + 客户评价 | 客户名称/行业、成果数据、评价引语 |
| 常见疑问？ | FAQ 区（**≥6 条**） | 高频真实问题 + 简明答案 |
| 在哪里、怎么联系？ | 联系区 + Footer | 地址、电话、邮箱、工作时间、联系方式 |
| 新动态/权威佐证 | 新闻动态（可选） | 行业观点、媒体报道、白皮书 |

> 该矩阵用于暴露信息缺口。缺失项可能降低答案完整性，但不能据此断言某个引擎会或不会推荐品牌。

---

## 二、语义化 HTML 结构（硬性）

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>品牌名 - 一句话定位（含行业核心词）</title>
  <meta name="description" content="150字内：品牌名是做什么的+核心服务+地域+独特优势，自然含关键词">
  <meta name="keywords" content="品牌名,行业词,核心服务词,地域">
  <!-- OG / Twitter 卡片 -->
  <meta property="og:type" content="website">
  <meta property="og:title" content="...">
  <meta property="og:description" content="...">
  <meta property="og:site_name" content="品牌名">
  <meta name="twitter:card" content="summary_large_image">
  <!-- JSON-LD 结构化数据（见第三节） -->
</head>
<body>
  <header>导航（logo + 锚点菜单 + CTA 按钮）</header>
  <main>
    <section id="hero">...</section>
    <section id="about">...</section>
    <section id="services">...</section>
    <section id="stats">...</section>
    <section id="cases">...</section>
    <section id="team">...</section>
    <section id="faq">...</section>
    <section id="contact">...</section>
  </main>
  <footer>版权、备案、导航、联系方式</footer>
</body>
</html>
```

**标题层级规则：** 页面唯一 H1（品牌定位句）；每个 section 一个 H2；小节用 H3。禁止跳级、禁止多个 H1。

---

## 三、JSON-LD 结构化数据（硬性）

在 `<head>` 内放置（可合并为一个 `@graph` 数组）：

### 1. Organization（品牌实体，最重要）

```json
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "品牌全称",
  "alternateName": "品牌简称/英文名",
  "url": "https://example.com",
  "description": "品牌一句话定位（含行业）",
  "foundingDate": "2015",
  "founder": { "@type": "Person", "name": "创始人姓名" },
  "address": { "@type": "PostalAddress", "addressLocality": "城市", "addressRegion": "省份", "addressCountry": "CN" },
  "contactPoint": { "@type": "ContactPoint", "telephone": "+86-xxx", "contactType": "customer service", "availableLanguage": "zh-CN" },
  "sameAs": ["https://weixin.qq.com/r/xxx", "https://www.xiaohongshu.com/user/profile/xxx"]
}
```

### 2. WebSite

```json
{
  "@type": "WebSite",
  "name": "品牌名官网",
  "url": "https://example.com",
  "inLanguage": "zh-CN"
}
```

### 3. FAQPage（对应页面 FAQ 区，问题与答案必须与正文一致）

```json
{
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "问题1？",
      "acceptedAnswer": { "@type": "Answer", "text": "答案1（与页面正文一致）" }
    },
    { "@type": "Question", "name": "问题2？", "acceptedAnswer": { "@type": "Answer", "text": "答案2" } }
  ]
}
```

### 4. 行业增强 schema（按行业二选一或多选）

```json
{ "@type": "Product", "name": "服务/产品名", "description": "...", "brand": { "@type": "Brand", "name": "品牌名" } }
{ "@type": "Service", "serviceType": "服务类型", "provider": { "@type": "Organization", "name": "品牌名" }, "areaServed": "中国" }
{ "@type": "LocalBusiness", "name": "品牌名", "address": {...}, "openingHours": "Mo-Fr 09:00-18:00" }
{ "@type": "BreadcrumbList", "itemListElement": [{ "@type": "ListItem", "position": 1, "name": "首页", "item": "https://example.com" }] }
```

---

## 四、E-E-A-T 信任信号（经验/专业/权威/可信）

只在品牌事实库有稳定事实与证据时加入下列内容：

1. **可核实的实体信息**：创始人/核心团队真实背景（`Person` schema 可标注 jobTitle、almaMater）。
2. **量化数据**：客户数、服务年限、案例成果（"服务 120+ 企业"优于"服务众多企业"）。
3. **资质与荣誉区**：认证、获奖、媒体报道（用 `itemListElement` 列表化）。
4. **案例可溯源**：客户行业 + 目标 + 方案 + 成果四段式，无敏感信息时注明客户名。
5. **原创内容**：FAQ 答案、行业观点用品牌自己的表述，不照抄竞品文案。

---

## 五、FAQ 写作规范

- **条数**：≥6 条，覆盖"是什么/做什么/怎么合作/价格/交付/售后/地域"。
- **问法**：用真实用户/客户的原话提问方式（"你们和 XX 有什么区别？"），不要自问自夸。
- **答案**：50-120 字，直答 + 1 句支撑 + 引导（"欢迎预约咨询"），不得答非所问。
- **一致性**：FAQ 正文与 JSON-LD FAQPage 内容逐字一致。

---

## 六、生成后检查清单（Step 5 必过）

- [ ] `<title>` ≤ 60 字且含品牌名 + 行业核心词
- [ ] `meta description` ≤ 150 字，覆盖"是什么+做什么+优势"
- [ ] JSON-LD：Organization + WebSite + FAQPage 齐全，行业 schema 已加
- [ ] H1 唯一，H2/H3 层级无跳级
- [ ] 语义化标签（header/main/section/article/footer）使用正确
- [ ] 内容覆盖矩阵逐项标为“已覆盖”或“缺事实待补”，没有模板示例冒充覆盖
- [ ] FAQ ≥6 条，且与 FAQPage JSON-LD 一致
- [ ] 所有 E-E-A-T 信号均有稳定事实与证据；没有信号时不生成占位主张
- [ ] 联系信息完整（地址/电话/邮箱/工作时间）
- [ ] 全文自然覆盖关键词 ≥3 次（不堆砌）
- [ ] 无真实存在的虚假数据（占位内容已用注释标注）

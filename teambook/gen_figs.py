# 极简图解生成器：大图 + 极少字（ELI5 风格），与课程站火柴人风格一致
from pathlib import Path
OUT = Path("docs/assets/figures"); OUT.mkdir(parents=True, exist_ok=True)
INK, OR, LIGHT, SOFT = "#2b3a4a", "#ff5f00", "#fff3e6", "#eef4ff"
def svg(w, h, body): return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" font-family="PingFang SC, Microsoft YaHei, sans-serif"><rect width="{w}" height="{h}" fill="white"/>{body}</svg>'
def man(x, y, label="", color=INK, s=1.0):
    r = 14*s
    b = (f'<g stroke="{color}" stroke-width="3" fill="none" stroke-linecap="round"><circle cx="{x}" cy="{y}" r="{r}"/>'
         f'<line x1="{x}" y1="{y+r}" x2="{x}" y2="{y+r+30*s}"/><line x1="{x}" y1="{y+r+14*s}" x2="{x+24*s}" y2="{y+r+2*s}"/>'
         f'<line x1="{x}" y1="{y+r+14*s}" x2="{x-24*s}" y2="{y+r+2*s}"/><line x1="{x}" y1="{y+r+30*s}" x2="{x-12*s}" y2="{y+r+56*s}"/>'
         f'<line x1="{x}" y1="{y+r+30*s}" x2="{x+12*s}" y2="{y+r+56*s}"/></g>')
    if label: b += f'<text x="{x}" y="{y+r+78*s}" text-anchor="middle" font-size="{15*s}" fill="{INK}">{label}</text>'
    return b
def box(x, y, w, h, text, fill="white", stroke=INK, fs=17, bold=False, rx=12, color=INK):
    lines = text.split("\n"); b = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="2.5"/>'
    n = len(lines); start = y + h/2 - (n-1)*fs*0.65 + fs*0.35
    for i, l in enumerate(lines):
        b += f'<text x="{x+w/2}" y="{start+i*fs*1.3}" text-anchor="middle" font-size="{fs}" fill="{color}" {"font-weight=\"bold\"" if bold else ""}>{l}</text>'
    return b
def arrow(x1, y1, x2, y2, color=OR, w=3):
    import math; a = math.atan2(y2-y1, x2-x1); L=12
    p1 = (x2 - L*math.cos(a-0.4), y2 - L*math.sin(a-0.4)); p2 = (x2 - L*math.cos(a+0.4), y2 - L*math.sin(a+0.4))
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{w}"/><polygon points="{x2},{y2} {p1[0]:.1f},{p1[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}" fill="{color}"/>'
def txt(x, y, s, fs=16, color=INK, bold=False, anchor="middle"): return f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{fs}" fill="{color}" {"font-weight=\"bold\"" if bold else ""}>{s}</text>'
def title(s): return txt(450, 38, s, 22, INK, True)

F = {}
# 1 问题：客户问 AI，只推 3~4 家
b = title("客户先问 AI，AI 只推 3~4 家") + man(80, 150, "客户")
b += box(150, 90, 210, 60, "附近哪家好？", fs=18) + arrow(360, 120, 420, 120)
b += box(420, 70, 150, 110, "AI", fill=SOFT, fs=40, bold=True)
for i, (t, c) in enumerate([("A 公司 ✓", LIGHT), ("B 公司 ✓", LIGHT), ("C 公司 ✓", LIGHT), ("你… 没提", "white")]):
    b += box(640, 60+i*58, 200, 46, t, fill=c, stroke=OR if i == 3 else INK, color=OR if i == 3 else INK)
b += arrow(570, 125, 635, 125) + txt(450, 330, "没上牌桌 = 无声出局", 22, OR, True)
F["q1-ask-ai"] = svg(900, 360, b)
# 2 华强北同构
b = title("2010 手机市场 ≈ 2026 GEO 市场")
rows = [("攒机零门槛", "攒课零门槛"), ("参数虚标 8 核=2 核", "「保排名」"), ("渠道加价 信息差", "黑箱报价"), ("无售后", "无复测"), ("跑分出现 → 清场", "OpenGEO Index → ?")]
b += box(100, 60, 300, 44, "2010 华强北", fill=SOFT, bold=True) + box(500, 60, 300, 44, "2026 GEO 市场", fill=LIGHT, bold=True)
for i, (l, r) in enumerate(rows):
    y = 120 + i*56; last = i == 4
    b += box(100, y, 300, 44, l, stroke=OR if last else INK, color=OR if last else INK) + arrow(405, y+22, 495, y+22) + box(500, y, 300, 44, r, stroke=OR if last else INK, color=OR if last else INK, bold=last)
b += txt(450, 430, "山寨死于可比较，割韭菜死于可复测", 22, OR, True)
F["q2-huaqiangbei"] = svg(900, 460, b)
# 3 六层楼
b = title("OpenGEO 是一栋六层楼（加一个门厅）")
layers = [("L5 基准", "OpenGEO Index 行业排行榜"), ("L4 站点", "让官网被 AI 读懂"), ("L3 执行", "七个 AI 员工 + 总控"), ("L2 洞察", "客户会怎么问"), ("L1 测量", "六维体检报告"), ("L0 规范", "品牌事实库：唯一事实源")]
for i, (l, d) in enumerate(layers):
    y = 60 + i*54; first = i >= 3 and i != 3 or i == 5
    batch1 = l[:2] in ("L0", "L1", "L3")
    b += box(150, y, 150, 46, l, fill=LIGHT if batch1 else "white", bold=True) + box(310, y, 440, 46, d, fill=LIGHT if batch1 else "white")
b += box(150, 390, 600, 46, "门厅：初衷 · 口径宪章 · 规则 · 教程", fill=SOFT, bold=True)
b += txt(800, 85, "第二批", 14, "#8a94a3") + txt(800, 139, "第二批", 14, "#8a94a3") + txt(800, 193, "第一批", 14, OR, True) + txt(800, 247, "第二批", 14, "#8a94a3") + txt(800, 301, "第一批", 14, OR, True) + txt(800, 355, "第一批", 14, OR, True)
b += arrow(120, 380, 120, 70, INK, 2) + txt(95, 230, "依赖", 14, INK)
F["a1-six-floors"] = svg(900, 460, b)
# 4 L0 事实库：身份证 + 红绿灯
b = title("L0 品牌事实库：每条卖点都有「身份证」")
b += box(80, 70, 330, 250, "", fill="white", rx=16)
b += txt(245, 110, "卖点：28 天复测见分数", 18, INK, True) + txt(245, 150, "谁写的：AI 草稿", 16) + txt(245, 180, "谁核的：老板 8/22 ✓", 16) + txt(245, 210, "过没过期：180 天内", 16) + txt(245, 250, "来源：公司介绍 2026", 16) + txt(245, 295, "status: stable", 17, OR, True)
for i, (c, t, d) in enumerate([("#d9534f", "draft", "没审 · 不准引用"), ("#f0ad4e", "待确认", "进「待确认」段"), ("#5cb85c", "stable", "老板确认 · 可引用")]):
    y = 95 + i*80
    b += f'<circle cx="520" cy="{y}" r="22" fill="{c}"/>' + txt(570, y-6, t, 20, INK, True, "start") + txt(570, y+20, d, 15, INK, False, "start")
b += man(800, 90, "老板按灯", s=0.9) + txt(450, 370, "AI 员工只准引用绿灯事实", 22, OR, True)
F["a2-fact-id-card"] = svg(900, 400, b)
# 5 L1 六维体检
b = title("L1 诊断：给品牌做一次「体检」")
dims = [("可见度", 30), ("推荐度", 20), ("引用源", 15), ("覆盖度", 15), ("情感", 10), ("内容基础", 10)]
for i, (d, w) in enumerate(dims):
    y = 70 + i*48
    b += txt(150, y+24, d, 17, INK, True, "end") + f'<rect x="170" y="{y}" width="{w*12}" height="32" rx="8" fill="{OR}" opacity="0.85"/>' + txt(180 + w*12, y+22, f"{w}%", 15, INK, False, "start")
b += box(620, 90, 220, 70, "豆包 · 元宝\nDeepSeek · 千问", fill=SOFT, fs=16) + txt(745, 200, "每个引擎问 20 问", 14, INK, False, "start")
b += box(620, 230, 220, 60, "体检报告 HTML", fill=LIGHT, bold=True) + arrow(730, 165, 730, 225)
b += txt(450, 390, "不发总分也能诊断：先看哪一维最弱", 20, OR, True)
F["a3-six-dims"] = svg(900, 420, b)
# 6 L3 七个 AI 员工 + 总控 + 门禁
b = title("L3 执行：一个总管 + 七个 AI 员工")
b += box(360, 60, 180, 56, "总控 Agent", fill=LIGHT, bold=True)
names = ["S1 诊断", "S2 意图词", "S3 内容", "S4 短视频", "S5 发布", "S6 地基", "S7 复测"]
for i, n in enumerate(names):
    x = 60 + i*118
    b += arrow(450, 116, x+50, 175) + man(x+50, 195, n, s=0.8)
b += box(120, 320, 660, 54, "门禁：只准引用绿灯事实 · 引用必附来源 · 先跑 lint", fill=SOFT, fs=17, bold=True)
F["a4-seven-skills"] = svg(900, 400, b)
# 7 闭环
import math
b = title("复测闭环：转一圈，分数说话")
cx, cy, R = 450, 230, 140
steps = ["定口径 L0", "出题 L2", "生产 L3", "上站 L4", "复测 L1", "回写 L0"]
for i, s in enumerate(steps):
    a = -math.pi/2 + i*2*math.pi/6; x, y = cx + R*math.cos(a), cy + R*math.sin(a)
    b += box(x-60, y-24, 120, 48, s, fill=LIGHT if "L1" in s else "white", bold="L1" in s)
    a2 = a + 2*math.pi/6; x2, y2 = cx + R*math.cos(a2), cy + R*math.sin(a2)
    mx, my = cx + (R+40)*math.cos(a+math.pi/6), cy + (R+40)*math.sin(a+math.pi/6)
    b += arrow(x + 0.55*(mx-x), y + 0.55*(my-y), x2 + 0.5*(mx-x2), y2 + 0.5*(my-y2), OR, 2.5)
b += txt(cx, cy-6, "18 分 →", 24, INK, True) + txt(cx, cy+26, "？分", 24, OR, True) + txt(cx, cy+52, "每周一次，涨跌都发", 14)
b += txt(450, 420, "别人止于方案，我们闭环到分数", 20, OR, True)
F["a5-loop"] = svg(900, 450, b)
# 8 规则：三不三只 + 裁判/选手
b = title("两条规矩：说话的规矩 · 身份的规矩")
b += box(60, 70, 380, 200, "三不承诺\n✗ 排名第一\n✗ 所有 AI 都推荐\n✗ 统一见效天数", fill="white", stroke="#d9534f", fs=18)
b += box(460, 70, 380, 200, "三只承诺\n✓ 诊断分数\n✓ 改进清单\n✓ 复测对比", fill=LIGHT, stroke="#5cb85c", fs=18)
b += man(200, 310, "裁判 = OpenGEO（开源组织）", s=0.9) + man(650, 310, "选手 = 仓桥（培训 · 交付 · Cloud）", s=0.9)
b += txt(450, 345, "分开，分数才有人信", 18, OR, True)
F["a6-rules"] = svg(900, 440, b)
# 9 我该做什么
b = title("9 个人，站在哪一层")
roles = [("统筹 1", "门厅 + 全部"), ("规范 1", "L0 spec"), ("测量 3", "L1 audit"), ("执行 3", "L3 skills"), ("课程/运营 1", "门厅 课程站")]
for i, (r, l) in enumerate(roles):
    x = 60 + i*170
    b += man(x+60, 80, r, s=0.9) + box(x, 180, 130, 48, l, fill=LIGHT, bold=True)
b += box(60, 270, 780, 54, "第 1–2 天 全员必修 → 第 3–5 天 分层动手 → 第 5 天 桌面推演一个客户 → 10 题验收", fill=SOFT, fs=16)
F["a7-roles"] = svg(900, 350, b)
for k, v in F.items(): (OUT / f"{k}.svg").write_text(v, encoding="utf-8")
print("figures:", len(F))

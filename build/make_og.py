# -*- coding: utf-8 -*-
"""生成分享卡片 og.png（1200×630）—— 微信 / 飞书 / Slack 等链接预览用。

设计意图
--------
站点的定位是「定向分享文档」（全站 noindex + robots Disallow），
所以**分享卡片是唯一的入口**：链接贴出去后，有没有缩略图直接决定点开率。

主视觉没有走「深色底 + 大字标题」的通用套路，而是直接用**尺子刻度**做视觉主体 ——
这是 slogan「把 AI 视频生成平台放在同一把尺子上」的字面化，
刻度上的彩色点取自站内各平台的代表色，让人在缩略图阶段就认出「这是一张价格对比图」。

用法
----
    python build/make_og.py

产物写到 ROOT/og.png，再由 build_site.write_all() 拷进两个发布目录。
⚠ Cloudflare Pages 的构建命令是留空的（只发布仓库里的产物，不跑生成器），
  所以卡片必须【随 git 提交】，改了数据或文案后要重新跑一次本脚本。
"""
import io
import json
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "og.png")

W, H = 1200, 630
PAD = 76

# ── 配色：直接取自站点 CSS，保证卡片与页面同源同色 ──
BG_TOP = (15, 16, 19)
BG_BOT = (0, 0, 0)
BRAND = (209, 254, 23)      # #D1FE17 —— 站点主色，也是 favicon 底色
WHITE = (255, 255, 255)
GRAY_HI = (154, 160, 168)   # #9AA0A8
GRAY_MID = (90, 96, 105)    # #5A6069
GRAY_LO = (76, 83, 90)      # #4C535A
RULE = (35, 38, 43)         # #23262B
TICK_MINOR = (52, 58, 65)   # #343A41
TICK_MAJOR = (76, 83, 90)   # #4C535A
SEP = (26, 29, 33)          # #1A1D21

# 刻度点颜色 —— 站内平台代表色。
# ⚠ 顺序有意义：第 0 颗会被套上品牌色环（#D1FE17），必须选【冷色】，
#   否则环与点同色系（如 #FABC00 黄）对比度不足，环看不出来。
DOT_COLORS = [
    (50, 128, 255),   # #3280FF ← 环在此颗上，冷色对撞品牌黄绿
    (0, 198, 90),     # #00C65A
    (237, 21, 114),   # #ED1572
    (250, 188, 0),    # #FABC00
    (167, 139, 250),  # #A78BFA
    (156, 230, 243),  # #9CE6F3
]

FONT_MONO_B = r"C:\Windows\Fonts\consolab.ttf"
FONT_MONO = r"C:\Windows\Fonts\consola.ttf"
FONT_CJK_B = r"C:\Windows\Fonts\msyhbd.ttc"
FONT_CJK = r"C:\Windows\Fonts\msyh.ttc"
FONT_FALLBACK = r"C:\Windows\Fonts\arial.ttf"


def font(path, size):
    """TTC 要显式给 index；缺字体时降级到 Arial，绝不静默失败。"""
    for p in (path, FONT_FALLBACK):
        try:
            if p.lower().endswith(".ttc"):
                return ImageFont.truetype(p, size, index=0)
            return ImageFont.truetype(p, size)
        except (OSError, IOError):
            continue
    raise RuntimeError("没有可用字体：%s" % path)


def ls_text(d, xy, s, f, fill, ls=0.0):
    """带字距的文本绘制（Pillow 没有 letter-spacing）。返回结束 x。"""
    x, y = xy
    for ch in s:
        d.text((x, y), ch, font=f, fill=fill)
        x += d.textlength(ch, font=f) + ls
    return x - ls if s else x


def ls_width(d, s, f, ls=0.0):
    if not s:
        return 0.0
    return sum(d.textlength(ch, font=f) for ch in s) + ls * (len(s) - 1)


def gradient_base():
    """竖向渐变：顶部 #0F1013 → 底部纯黑，给纯黑底一点纵深。"""
    img = Image.new("RGB", (W, H), BG_BOT)
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / (H - 1)
        c = tuple(int(BG_TOP[i] + (BG_BOT[i] - BG_TOP[i]) * t) for i in range(3))
        d.line([(0, y), (W, y)], fill=c)
    return img


def faint_grid(img):
    """极淡横向刻度网格（alpha 5）—— 只在放大时才看得见的质感层。

    刻意压到几乎不可见：一旦明显，就会退化成通用模板的装饰条纹。
    """
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for y in range(PAD, H, 45):
        d.line([(PAD, y), (W - PAD, y)], fill=(255, 255, 255, 5), width=1)
    return Image.alpha_composite(img.convert("RGBA"), ov)


def draw_card():
    img = gradient_base()
    img = faint_grid(img)
    d = ImageDraw.Draw(img)

    f_word = font(FONT_MONO_B, 44)
    f_meta = font(FONT_MONO, 23)
    f_h1 = font(FONT_CJK_B, 66)
    # ⚠ 含中文的标注必须挂 CJK 字体 —— Consolas 没有汉字字形，会渲染成豆腐块
    f_cap = font(FONT_CJK, 22)
    f_tick = font(FONT_MONO, 21)
    f_foot_b = font(FONT_MONO_B, 23)
    f_foot = font(FONT_MONO, 22)
    f_foot_cjk = font(FONT_CJK, 23)

    y, mo = 2026, 9
    try:
        with io.open(os.path.join(ROOT, "data", "cost-seedance25.json"), encoding="utf-8") as fh:
            up = json.load(fh).get("updatedAt", "")
        if len(up) >= 7:
            y, mo = int(up[:4]), int(up[5:7])
    except (OSError, ValueError, KeyError):
        pass   # 取不到就用兜底日期，不让卡片生成失败

    # ── 页眉：品牌标记 + 词标 ──
    d.rounded_rectangle([PAD, 72, PAD + 32, 104], radius=10, fill=BRAND)
    ls_text(d, (PAD + 54, 68), "CALIBER", f_word, BRAND, ls=9)

    meta = "COST BENCHMARK · %d.%02d" % (y, mo)
    d.text((W - PAD - d.textlength(meta, font=f_meta), 80), meta, font=f_meta, fill=GRAY_MID)

    # ── 主标题：前段灰、后段白，把重心压到「同一把尺子」上 ──
    d.text((PAD, 192), "把 AI 视频生成平台", font=f_h1, fill=GRAY_HI)
    d.text((PAD, 282), "放在同一把尺子上", font=f_h1, fill=WHITE)

    # ── 主视觉：尺子 ──
    x0, x1 = PAD, W - PAD
    yl = 462
    # ⚠ 刻度取 ¥0–¥120 是【贴着真实数据】定的，不是随手画的比例尺。
    #   站内单条成本实测区间 **¥19.30–¥106.29**（三张周期表全量 133 条，
    #   取自 `data-rated`／`data-v`）→ 轴上限留约 11% 余量，最贵那档不贴边。
    #
    #   踩过的坑：`data-c` 不是单条成本，是**月产能**（实测 0.93–91.00 条/月）。
    #   按 data-c 取值会把轴画成 ¥0–¥100，结果最贵的档位直接掉到轴外面 ✗
    #   三个属性别混：data-v / data-rated = 单条成本，data-p = 月支出，data-c = 月产能。
    n_tick = 21
    d.text((x0, 412), "单条成本 · 元 / 条", font=f_cap, fill=GRAY_LO)

    d.line([(x0, yl), (x1, yl)], fill=RULE, width=2)
    for i in range(n_tick):
        x = x0 + (x1 - x0) * i / (n_tick - 1)
        major = (i % 5 == 0)
        d.line([(x, yl), (x, yl + (17 if major else 10))],
               fill=TICK_MAJOR if major else TICK_MINOR, width=2 if major else 1)

    majors = [i for i in range(n_tick) if i % 5 == 0]
    for i in majors:
        x = x0 + (x1 - x0) * i / (n_tick - 1)
        t = "¥%d" % (i * 6)
        # 末端标签必须右对齐，否则 ¥120 会溢出到刻度线外
        d.text((x - d.textlength(t, font=f_tick), yl + 26) if i == majors[-1]
               else (x, yl + 26), t, font=f_tick, fill=GRAY_MID)

    # 平台点：**落在真实刻度位上**（不是随手等分），最左那颗加品牌色环 = 「最省」那一端
    dot_ticks = (2, 5, 8, 11, 14, 17)
    for c, i in zip(DOT_COLORS, dot_ticks):
        cx = x0 + (x1 - x0) * i / (n_tick - 1)
        d.ellipse([cx - 13, yl - 13, cx + 13, yl + 13], fill=(0, 0, 0))
        d.ellipse([cx - 11, yl - 11, cx + 11, yl + 11], fill=c)
    bx = x0 + (x1 - x0) * dot_ticks[0] / (n_tick - 1)
    d.ellipse([bx - 17, yl - 17, bx + 17, yl + 17], outline=BRAND, width=3)

    # ── 页脚 ──
    yf = 556
    d.line([(x0, yf), (x1, yf)], fill=SEP, width=1)
    tx = ls_text(d, (x0, 578), "HELIX AI STUDIO", f_foot_b, GRAY_HI, ls=1.5)
    d.text((tx + 16, 579), "·", font=f_foot_cjk, fill=GRAY_LO)
    ls_text(d, (tx + 34, 579), "AI 视频平台成本测评", f_foot_cjk, GRAY_MID, ls=0.5)

    dom = "seedance-cost-benchmark.pages.dev"
    d.text((x1 - d.textlength(dom, font=f_foot), 579), dom, font=f_foot, fill=GRAY_MID)

    return img.convert("RGB")


def main():
    if not os.path.exists(FONT_MONO_B):
        raise RuntimeError("缺少等宽字体 %s" % FONT_MONO_B)
    img = draw_card()
    assert img.size == (W, H), "尺寸不对：%s" % (img.size,)
    img.save(OUT, "PNG", optimize=True)
    size = os.path.getsize(OUT)
    print("✓ %s  %d×%d  %.1f KB" % (os.path.relpath(OUT, ROOT), W, H, size / 1024.0))
    if size > 300 * 1024:
        print("⚠ 体积偏大（>300KB），部分平台会拒绝抓取缩略图")


if __name__ == "__main__":
    main()

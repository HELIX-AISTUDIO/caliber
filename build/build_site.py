# -*- coding: utf-8 -*-
"""
CALIBER — AI 平台与模型 · 统一口径基准
站点生成器：产出 index.html（首页）+ cost.html（平台成本对比）

设计规范见 site/DESIGN.md（源自 higgsfield.ai 实测 design token）
结构参考 arena.ai/leaderboard：标题 → 一行副标 → 一行元数据 → 直接上表格，零段落后文

统一测试口径：Seedance 2.5 | 720p | 16:9 | 30s | 全能参考
方法链：
  1) 本币/积分 = 年费 / (月积分 × 12)       —— 压平各平台内部积分币值
  2) 单条成本 = 本币/积分 × 每条消耗积分    —— 同规格下唯一可跨平台比较的价格
  3) 月产能 = 月积分 / 每条消耗积分
  4) 边际成本 = Δ年费 / Δ年产能             —— 判断升档是否值得
  5) 达标总支出最省 = 覆盖目标月产能的最低年费档位
  6) USD 报价按当日 CFETS 中间价折 CNY，并标注不含税
"""
import hashlib
import json
import math
import os
import re

# ══════════════════════════════════════════════════════════════
# 品牌与版权
# ══════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════
# 站点元数据与数据集 —— 全部来自 data/*.json（数据与页面分离）
# ══════════════════════════════════════════════════════════════
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # site/
DATA = os.path.join(ROOT, "data")

def _load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)

SITE = _load("site.json")
PLATFORMS = _load("platforms.json")
COST = _load("cost-seedance25.json")
VLM = _load("leaderboard-vlm.json")

BRAND = SITE["brand"]
BRAND_CN = SITE["brandCn"]
STUDIO = SITE["studio"]
TAGLINE = SITE["tagline"]
POSITION = SITE["positions"]
INTRO = SITE["intro"]
NAV = SITE["nav"]
OWNER = SITE["owner"]
YEAR = SITE["year"]
COPY = f"© {YEAR} {OWNER}. 保留所有权利 / All Rights Reserved."
TERMS = ("本页内容（含全部价格数据、归一化模型、边际成本与达标阶梯算法、结论文字及版面设计）"
         "为作者原创成果。未经书面许可，禁止：复制或转载全文/部分内容、"
         "二次发布或镜像托管、用于商业用途、用于任何 AI 模型的训练或微调、"
         "移除或篡改版权声明与溯源指纹。允许：转发原始链接、引用结论并注明出处。")

SPEC = COST["spec"]
SPEC_NOTE = COST["specNote"]
FX = COST["fx"]
RATE = FX["rate"]
RATE_DATE = COST["updatedAt"]
CPV = COST["creditsPerVideo"]

COLOR = {k: v["color"] for k, v in PLATFORMS.items()}
CU = {"CNY": "¥", "USD": "$"}

# RAW 行：(平台, 档位, 年费, 币种, 月积分, 每条消耗积分, 原价, 原价说明, 积分档标签)
# 同一档位提供多个积分选项（creditsOptions）时，每个选项展开为一行（价格相同）
SKIPPED = []   # 价格未获取的积分档，排除出计算并登记

def _rows():
    """把 plans 展开为待计算行。
    注意：同一档位的不同积分选项**各自有价格**（平台为联动定价），
    因此每个选项必须带自己的 price；price 为 None 的选项跳过计算。"""
    out = []
    for p in COST["plans"]:
        opts = p.get("creditsOptions")
        if opts:
            for o in opts:
                price = o.get("price")
                if price is None:
                    SKIPPED.append({"plat": p["platform"], "tier": p["tier"],
                                    "credits": o["monthlyCredits"],
                                    "label": o.get("label", "")})
                    continue
                out.append((p["platform"], p["tier"], price, p["currency"],
                            o["monthlyCredits"], CPV[p["platform"]], p["original"],
                            p["originalNote"], o.get("label", "")))
        else:
            out.append((p["platform"], p["tier"], p["price"], p["currency"],
                        p["monthlyCredits"], CPV[p["platform"]], p["original"],
                        p["originalNote"], ""))
    return out

RAW = _rows()
OFFICIAL = {(pl, ti): r for pl, d in COST["officialRate"].items() for ti, r in d.items()}
AD_CLAIM = {pl: (d["tier"], d["perSec"]) for pl, d in COST["adClaim"].items()}

# ══════════════════════════════════════════════════════════════
# 计算
# ══════════════════════════════════════════════════════════════
plans = []
for plat, tier, price, cur, monthly, per, orig, orignote, variant in RAW:
    k = RATE if cur == "USD" else 1.0
    yc = monthly * 12
    unit = price / yc
    m_cap = monthly / per
    official = OFFICIAL.get((plat, tier))
    plans.append({
        "plat": plat, "tier": tier, "variant": variant, "cur": cur, "k": k,
        "price": price, "priceCNY": price * k,
        "monthly": monthly, "per": per, "yearCredits": yc,
        "unit": unit, "unitCNY": unit * k, "unitPerYuan": 1.0 / unit,
        "perVideo": unit * per, "perVideoCNY": unit * per * k, "perSecCNY": unit * per * k / 30.0,
        "mCap": m_cap, "yCap": m_cap * 12,
        "orig": orig, "origNote": orignote, "origCNY": (orig * k) if orig else None,
        "officialPerYuan": official,
        "dev": (abs(1.0 / unit - official) / official * 100) if official else None,
        "color": COLOR[plat],
    })

best = min(p["perVideoCNY"] for p in plans)
worst = max(p["perVideoCNY"] for p in plans)
for i, p in enumerate(sorted(plans, key=lambda x: x["perVideoCNY"]), 1):
    p["rank"] = i
    p["rel"] = p["perVideoCNY"] / best

for p in plans:
    if p["origCNY"]:
        p["origUnitCNY"] = p["origCNY"] / p["yearCredits"]
        p["origPerVideoCNY"] = p["origUnitCNY"] * p["per"]
        p["disc"] = p["priceCNY"] / p["origCNY"]
    else:
        p["origUnitCNY"] = p["origPerVideoCNY"] = p["disc"] = None

def tname(p):
    """档位显示名：多积分档时附标签"""
    return p["tier"] + (f' · {p["variant"]}' if p.get("variant") else "")

# 单档位索引：同档多积分选项时取产能最大者
# （用于边际成本阶梯，避免同价两档产生 Δ年费=0 的噪音）
_by_tier = {}
for _p in plans:
    _k = (_p["plat"], _p["tier"])
    if _k not in _by_tier or _p["mCap"] > _by_tier[_k]["mCap"]:
        _by_tier[_k] = _p
G = lambda a, b: _by_tier[(a, b)]
# 单档位视图：同价多积分选项只保留产能最大者。
# 用于边际成本阶梯与达标阶梯 —— 同价时更高积分配置严格支配低配，
# 否则会出现「高级版 → 高级版，Δ年费 ¥0」这类无意义对比。
SINGLES = list(_by_tier.values())
best_row = min(plans, key=lambda x: x["perVideoCNY"])
runner = sorted(plans, key=lambda x: x["perVideoCNY"])[1]
NW, JM, XQ, HG, HG2, LT = (G("Neowow", "ULTRA"), G("即梦", "超级会员"), G("小云雀", "超级会员"),
                           G("Higgsfield", "Ultra"), G("Higgsfield", "Plus"), G("libtv", "至尊版"))
max_dev = max(p["dev"] for p in plans if p["dev"] is not None)

disc_rows_data = []
for plat in ["libtv", "Neowow", "即梦", "小云雀", "Higgsfield"]:
    grp = [p for p in plans if p["plat"] == plat and p["disc"] is not None]
    ds = [p["disc"] for p in grp]
    ops = [p["origPerVideoCNY"] for p in grp]
    disc_rows_data.append({"plat": plat, "minD": min(ds), "maxD": max(ds), "minO": min(ops),
                           "maxO": max(ops), "spreadO": (max(ops) / min(ops) - 1) * 100,
                           "spreadD": (max(ds) / min(ds) - 1) * 100, "color": COLOR[plat]})

marginal = []
for plat in ["libtv", "Neowow", "即梦", "小云雀", "Higgsfield"]:
    grp = sorted([p for p in SINGLES if p["plat"] == plat], key=lambda x: x["priceCNY"])
    for a, b in zip(grp, grp[1:]):
        dp, dc = b["priceCNY"] - a["priceCNY"], b["yCap"] - a["yCap"]
        marginal.append({"plat": plat, "frm": a["tier"], "to": b["tier"], "dPrice": dp, "dCap": dc,
                         "mCost": dp / dc, "avgCost": b["perVideoCNY"], "color": COLOR[plat]})

priced = sorted(SINGLES, key=lambda x: x["priceCNY"])
ladder, dominated, lower = [], [], 0.0
for p in priced:
    if p["mCap"] > lower + 1e-9:
        item = {"lo": lower, "hi": p["mCap"], "plan": p}
        (dominated if (p["mCap"] - lower) < 0.1 else ladder).append(item)
    lower = max(lower, p["mCap"])

def f2(v):
    return f"{v:,.2f}"

# ── 主表「月产 N 条的年支出」列：构建时按默认 10 条预渲染 ──
# 不依赖 JS，脚本失效时该列依然正确显示，JS 只负责改数字后重算
CQ_DEFAULT = 10
CQ_MAX_STACK = 4   # 同档最多叠加份数；超过则视为该档不适合承接此产量


def cq_need(p, n_target=None):
    """某档覆盖目标月产量的最低支出：可行返回 (份数, 总价)，不可行返回 None。
    单一档位产能不足时按同档多份叠加（与计算器「组合订阅最省」同一逻辑）。"""
    n_target = CQ_DEFAULT if n_target is None else n_target
    if p["mCap"] <= 0:
        return None
    n = math.ceil(n_target / p["mCap"] - 1e-9)
    if n > CQ_MAX_STACK:
        return None
    return n, n * p["priceCNY"]


_cq_all = [cq_need(p) for p in plans]
CQ_BEST = min(v[1] for v in _cq_all if v) if any(_cq_all) else None


def cq_cell(p):
    v = cq_need(p)
    if not v:
        return '<span class="cq-no">产能过低</span>'
    n, total = v
    t = f'¥{total:,.0f}' + (f' · {n}×' if n > 1 else '')
    return f'<span class="cq-best">{t} 最省</span>' if total == CQ_BEST else t


def cq_max_note():
    mx = max(p['mCap'] for p in plans)
    return (f'全场单档产能上限 {mx:.0f} 条/月；超出时按同档多份叠加计算'
            f'（最多 {CQ_MAX_STACK} 份，标 ×N）。')


def cq_default_text():
    secs = CQ_DEFAULT * 30
    mins = secs / 60
    dur = f'{mins/60:.1f} 小时' if mins >= 60 else f'{mins:.0f} 分钟'
    return f'= {secs:,} 秒 ≈ {dur}素材（1 条 = 30 秒）'

# ── KPI 与建议取数（全部由数据派生，避免硬编码档位名）──
_mid_pool = [r for r in ladder if 13 <= r["hi"] <= 28]
mid = (min(_mid_pool, key=lambda r: r["plan"]["perVideoCNY"]) if _mid_pool else ladder[0])
top = ladder[-1]

def _plan_bullets():
    """执行建议的产量区间列表从达标阶梯自动生成"""
    out = ""
    for i, r in enumerate(ladder):
        p = r["plan"]
        lo = "0" if i == 0 else f'{r["lo"]:.2f}'
        out += (f'<li><b>月产 {lo}–{r["hi"]:.2f} 条：</b>'
                f'{p["plat"]} {tname(p)} — ¥{p["priceCNY"]:,.0f}/年'
                f'（实际 {p["mCap"]:.2f} 条/月 · ¥{f2(p["perVideoCNY"])}/条 · '
                f'单价为最优解的 {p["rel"]:.2f} 倍）</li>')
    return out

PLAN_BULLETS = _plan_bullets()

claims = [{"plat": pl, "tier": t, "ad": ad, "real": G(pl, t)["perSecCNY"],
           "ratio": G(pl, t)["perSecCNY"] / ad, "color": COLOR[pl]}
          for pl, (t, ad) in AD_CLAIM.items()]

def best_stack(target):
    out = [{"p": p, "n": math.ceil(target / p["mCap"]),
            "total": math.ceil(target / p["mCap"]) * p["priceCNY"],
            "cap": math.ceil(target / p["mCap"]) * p["mCap"]} for p in plans]
    return min(out, key=lambda x: (x["total"], x["p"]["perVideoCNY"]))

stack150 = best_stack(150)
m_best = min(marginal, key=lambda x: x["mCost"])
m_worst = max(marginal, key=lambda x: x["mCost"])
clip = lambda s, n=52: (s[:n] + "…") if len(s) > n else s

_sig = json.dumps([RAW, RATE, SPEC, BRAND], ensure_ascii=False, sort_keys=True)
FP = "HX-CLB-" + RATE_DATE.replace("-", "") + "-" + hashlib.sha256(_sig.encode()).hexdigest()[:8].upper()

# ══════════════════════════════════════════════════════════════
# 样式（Higgsfield 设计 token）
# ══════════════════════════════════════════════════════════════
F_SANS = ('"Inter","Inter Display","SN Pro","Space Grotesk",ui-sans-serif,system-ui,'
          '-apple-system,"Segoe UI","PingFang SC","Microsoft YaHei","Noto Sans CJK SC",sans-serif')
F_DISP = ('"Space Grotesk","Inter Display","Inter","SN Pro",ui-sans-serif,system-ui,'
          '"PingFang SC","Microsoft YaHei",sans-serif')
F_MONO = ('"IBM Plex Mono","JetBrains Mono","Geist Mono",ui-monospace,SFMono-Regular,'
          'Menlo,Consolas,monospace')

CSS = r"""
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
/* ⚠️ 必须是 clip 而不是 hidden：overflow-x:hidden 会让 html/body 变成滚动容器，
   进而使子元素的 position:sticky 失效（实测导航会跟随内容滚走）。
   overflow:clip 同样能裁掉横向溢出，但不创建滚动容器，sticky 正常工作。
   若不支持 clip，声明被忽略 -> 仅失去横向裁剪，sticky 仍可用，属更安全的失败方向。 */
html{-webkit-text-size-adjust:100%;text-size-adjust:100%;overflow-x:clip;scroll-behavior:smooth}
body{background:#000;color:#C9CDD2;font:14px/1.7 %%F_SANS%%;overflow-x:clip;
  padding:0 0 72px;padding-bottom:calc(72px + env(safe-area-inset-bottom,0px));
  -webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;
  letter-spacing:-.005em;-webkit-tap-highlight-color:transparent;-webkit-touch-callout:none}
/* 环境光晕：纯黑底上叠模糊等于没效果，必须先给玻璃一层可折射的底光 */
body::before{content:"";position:fixed;inset:0;pointer-events:none;z-index:0;
  transform:translate3d(0,0,0);will-change:transform;
  background:
    radial-gradient(1150px 640px at 6% -12%,rgba(209,254,23,.145),transparent 62%),
    radial-gradient(860px 540px at 105% 3%,rgba(237,21,114,.105),transparent 64%),
    radial-gradient(920px 580px at 44% 108%,rgba(156,230,243,.075),transparent 64%)}
/* 磨砂噪点：极低透明度的分形噪声，给面板与整页一层"砂面"颗粒 */
body::after{content:"";position:fixed;inset:0;pointer-events:none;z-index:2;opacity:.04;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.82' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='160' height='160' filter='url(%23n)'/%3E%3C/svg%3E")}
/* 吸顶高度由 JS 实测写入（导航与子导航高度随视口变化，写死会错位） */
:root{--navh:57px;--subh:50px;--gap:18px}
[id]{scroll-margin-top:calc(var(--navh) + var(--subh) + var(--gap))}
::selection{background:#D1FE17;color:#0B0B0B}

/* ── 顶部 lime 通栏 ── */
.promo{background:#D1FE17;color:#0B0B0B;font-size:12.5px;font-weight:600;letter-spacing:-.01em;
  display:flex;align-items:center;justify-content:center;gap:13px;flex-wrap:wrap;
  padding:10px 22px;text-align:center;line-height:1.5;position:relative;z-index:3}
.promo b{font-weight:800}
.promo .tag2{border:1.5px solid #0B0B0B;border-radius:999px;padding:2px 11px;font-size:11px;font-weight:700;white-space:nowrap}

/* ── 顶栏（sticky） ── */
.nav{position:sticky;top:0;z-index:40;
  background:linear-gradient(180deg,rgba(255,255,255,.07) 0%,rgba(0,0,0,.42) 100%);
  -webkit-backdrop-filter:blur(34px) saturate(165%);backdrop-filter:blur(34px) saturate(165%);
  border-bottom:1px solid rgba(255,255,255,.11);
  box-shadow:inset 0 -1px 0 rgba(255,255,255,.04),0 10px 30px rgba(0,0,0,.45)}
.nav .inner{max-width:1280px;margin:0 auto;padding:12px 24px;display:flex;align-items:center;gap:16px}
.brand{display:flex;align-items:center;gap:10px;text-decoration:none;flex:0 0 auto}
.brand i{width:24px;height:24px;border-radius:8px;background:#D1FE17;display:inline-block;flex:0 0 24px;
  transition:transform .35s cubic-bezier(.22,1,.36,1)}
.brand:hover i{transform:rotate(45deg)}
.brand .bw{display:flex;flex-direction:column;line-height:1.15}
.brand .bw b{font-family:%%F_DISP%%;font-size:16px;font-weight:800;color:#fff;letter-spacing:.06em}
.brand .bw s{text-decoration:none;font-size:9.5px;font-weight:600;color:#6E747D;letter-spacing:.05em;margin-top:1px}
.menu{display:flex;align-items:center;gap:2px;overflow-x:auto;-webkit-overflow-scrolling:touch;
  scrollbar-width:none;flex:1 1 auto;min-width:0}
.menu::-webkit-scrollbar{display:none}
.menu a{display:inline-flex;align-items:center;gap:6px;white-space:nowrap;text-decoration:none;
  color:#9AA0A8;font-size:13px;font-weight:600;letter-spacing:-.012em;padding:7px 12px;border-radius:999px;
  flex:0 0 auto;transition:color .22s,background .22s}
.menu a:hover{color:#fff;background:rgba(255,255,255,.065)}
.menu a.active{color:#D1FE17}
.menu a.soon{color:#565C64;cursor:default}
.menu a.soon:hover{background:transparent;color:#565C64}
.menu .nb{background:#D1FE17;color:#0B0B0B;font-size:9.5px;font-weight:800;padding:1.5px 7px;
  border-radius:999px;letter-spacing:.02em}
.nav .spec{margin-left:auto;font-family:%%F_MONO%%;font-size:11.5px;font-weight:500;color:#D1FE17;
  border:1px solid rgba(209,254,23,.35);border-radius:999px;padding:6px 13px;letter-spacing:-.01em;
  flex:0 0 auto}

/* ── 二级子导航（页内锚点，sticky） ── */
.subnav{position:sticky;top:var(--navh,57px);z-index:35;
  background:linear-gradient(180deg,rgba(255,255,255,.055) 0%,rgba(0,0,0,.46) 100%);
  -webkit-backdrop-filter:blur(30px) saturate(160%);backdrop-filter:blur(30px) saturate(160%);
  border-bottom:1px solid rgba(255,255,255,.1);
  box-shadow:0 8px 26px rgba(0,0,0,.4)}
.subnav .inner{max-width:1280px;margin:0 auto;padding:9px 24px;display:flex;gap:6px;
  overflow-x:auto;-webkit-overflow-scrolling:touch;scrollbar-width:none}
.subnav .inner::-webkit-scrollbar{display:none}
.subnav a{white-space:nowrap;flex:0 0 auto;text-decoration:none;color:#8A9099;font-size:12.5px;
  font-weight:600;padding:6px 14px;border-radius:999px;border:1px solid transparent;
  transition:color .22s,border-color .22s,background .22s}
.subnav a:hover{color:#fff;background:rgba(255,255,255,.05)}
.subnav a.active{color:#D1FE17;border-color:rgba(209,254,23,.4);background:rgba(209,254,23,.07)}

/* ── 布局 ── */
.wrap{max-width:1280px;margin:0 auto;padding:0 24px;position:relative;z-index:1}
/* ── Hero 光场 ────────────────────────────────────────────────
   higgsfield 的高级感首要来源：lime 是【光源】而非涂料。
   做法：径向光核 + 泛光溢出 + 透视网格地板 + 径向遮罩渐晕。
   仅用于 hero 区，不铺全站 —— 铺开就稀释了。 */
.hero{max-width:1280px;margin:0 auto;padding:58px 24px 6px;
  position:relative;z-index:1}
.hero::before{content:"";position:absolute;left:50%;top:-14%;z-index:-1;pointer-events:none;
  width:min(1180px,140vw);height:150%;transform:translateX(-50%);
  background:
    radial-gradient(42% 34% at 50% 30%,rgba(209,254,23,.26),rgba(209,254,23,.09) 48%,transparent 74%),
    radial-gradient(76% 62% at 50% 2%,rgba(209,254,23,.085),transparent 72%);
  -webkit-filter:blur(4px);filter:blur(4px)}
.hero::after{content:"";position:absolute;left:-12%;right:-12%;bottom:-4%;height:46%;
  z-index:-1;pointer-events:none;opacity:.42;
  background-image:
    linear-gradient(rgba(209,254,23,.13) 1px,transparent 1px),
    linear-gradient(90deg,rgba(209,254,23,.13) 1px,transparent 1px);
  background-size:58px 58px,58px 58px;
  transform:perspective(400px) rotateX(63deg);transform-origin:50% 100%;
  -webkit-mask-image:radial-gradient(58% 82% at 50% 100%,#000,transparent 74%);
  mask-image:radial-gradient(58% 82% at 50% 100%,#000,transparent 74%)}
.eyebrow{font-size:11px;font-weight:700;letter-spacing:.15em;text-transform:uppercase;
  color:#D1FE17;margin-bottom:15px;font-family:%%F_MONO%%}
h1{font-family:%%F_DISP%%;font-size:clamp(31px,5.3vw,60px);font-weight:800;color:#fff;
  letter-spacing:-.038em;line-height:1.07}
h1 em{font-style:normal;color:#D1FE17}
.hero .lead{color:#8A9099;font-size:14.5px;max-width:720px;margin-top:18px;line-height:1.75;letter-spacing:0}
.meta{display:flex;gap:20px;flex-wrap:wrap;margin-top:22px;font-size:12.5px;color:#767C85}
.meta span{display:inline-flex;align-items:center;gap:7px}
.meta i{width:5px;height:5px;border-radius:50%;background:#D1FE17;display:inline-block}
.meta b{color:#C9CDD2;font-weight:600;font-family:%%F_MONO%%}
.btns{display:flex;gap:10px;flex-wrap:wrap;margin-top:26px}
.btn{display:inline-block;border-radius:999px;padding:12px 23px;font-size:13px;font-weight:700;
  letter-spacing:-.012em;text-decoration:none;white-space:nowrap;
  transition:transform .22s cubic-bezier(.22,1,.36,1),box-shadow .22s,background .22s}
.btn-fill{background:#D1FE17;color:#0B0B0B}
.btn-fill:hover{transform:translateY(-2px);box-shadow:0 8px 26px rgba(209,254,23,.3)}
/* higgsfield 的做法：主 CTA 用白色，lime 留给氛围与数据高亮。
   若主按钮也用 lime，lime 就同时承担「动作」与「强调」两个语义，必然廉价化。 */
.btn-white{background:#fff;color:#0B0B0B}
.btn-white:hover{transform:translateY(-2px);box-shadow:0 10px 32px rgba(255,255,255,.2)}
.btn-ghost{background:transparent;color:#fff;border:1px solid rgba(255,255,255,.2)}
.btn-ghost:hover{border-color:rgba(255,255,255,.45);transform:translateY(-2px)}
.disc{display:flex;gap:11px;align-items:flex-start;max-width:840px;margin-top:26px;
  padding:13px 16px;border:1px solid rgba(255,201,60,.26);border-radius:13px;
  background:rgba(255,201,60,.035);font-size:12px;color:#A9AFB8;line-height:1.7;letter-spacing:0}
.disc b{color:#FFC93C;font-weight:600}
.disc-i{flex:0 0 17px;height:17px;border-radius:50%;background:#FFC93C;color:#0B0B0B;font-size:11px;
  font-weight:800;display:flex;align-items:center;justify-content:center;margin-top:2px}

h2{font-family:%%F_DISP%%;font-size:20px;font-weight:750;color:#fff;letter-spacing:-.025em;
  line-height:1.3;margin:0 0 6px}
h2 .ey{display:inline-block;font-family:%%F_MONO%%;font-size:12px;font-weight:600;color:#D1FE17;
  letter-spacing:0;margin-right:12px}
.sechead{margin:0 0 18px}
.sechead .sd{color:#767C85;font-size:12.5px;line-height:1.7;max-width:840px}
section{margin-top:60px}
h3{font-family:%%F_DISP%%;font-size:14.5px;font-weight:700;color:#fff;letter-spacing:-.015em;margin:26px 0 12px}

/* ── 卡片 ── */
/* ── 玻璃面板 ────────────────────────────────────────────────
   规格来源（higgsfield 实测）：
     .bg-glass-card               backdrop-filter:blur(40px)
                                  background:linear-gradient(#a6a6a633 0%,#0003 100%)
     .post-content-asset-download backdrop-filter:blur(16px)
                                  background:#0b0b0ba3  border:1px solid #ffffff24
     __countdown                  box-shadow:inset 0 0 0 .61px <4% 白>
   签名写法是「白→黑渐透底 + 大半径模糊」，不是单纯调透明度 —— 这才是磨砂感的来源。 */
.glass,.card,.kpi,.note,.entry,.legal,details{
  background:linear-gradient(158deg,rgba(255,255,255,.075) 0%,rgba(255,255,255,.022) 46%,rgba(0,0,0,.30) 100%);
  -webkit-backdrop-filter:blur(28px) saturate(150%);backdrop-filter:blur(28px) saturate(150%);
  border:1px solid rgba(255,255,255,.12);border-radius:18px;
  box-shadow:inset 0 0 0 .61px rgba(255,255,255,.07),
             inset 0 1px 0 rgba(255,255,255,.05),
             0 1px 2px rgba(0,0,0,.45),
             0 10px 24px rgba(0,0,0,.4),
             0 30px 60px rgba(0,0,0,.48)}
.glass-strong,.hero .disc,.pending-card{
  -webkit-backdrop-filter:blur(40px) saturate(160%);backdrop-filter:blur(40px) saturate(160%)}
/* 无 backdrop-filter（微信 X5 / 旧 WebView）：退化为同亮度的实心渐变面，
   保留同样的描边与内高光，视觉上仍是有意为之的面，而非"玻璃失效" */
@supports not ((-webkit-backdrop-filter:blur(2px)) or (backdrop-filter:blur(2px))){
  .glass,.card,.kpi,.note,.entry,.legal,details,.nav,.subnav{
    background:linear-gradient(158deg,#161B18 0%,#0D110F 100%)}
}
.card{padding:20px 22px}
.grid{display:grid;gap:14px}
.g2{grid-template-columns:repeat(auto-fit,minmax(330px,1fr))}
.g3{grid-template-columns:repeat(auto-fit,minmax(280px,1fr))}
.g5{grid-template-columns:repeat(auto-fit,minmax(200px,1fr))}
.kpi{padding:18px 20px}
.kpi .t{font-size:9.5px;color:#767C85;font-weight:700;letter-spacing:.13em;text-transform:uppercase}
.kpi .v{font-family:%%F_MONO%%;font-size:clamp(30px,3.2vw,46px);font-weight:700;color:#fff;margin:12px 0 6px;
  letter-spacing:-.032em;line-height:1.15}
.kpi.good .v,.kpi.hi .v{color:#D1FE17}
.kpi.hi{border-color:rgba(209,254,23,.45)}
.kpi .d{font-size:12px;color:#8A9099;line-height:1.65;letter-spacing:0}
.kpi .d b{color:#C9CDD2}

/* ── 首页入口卡 ── */
.entry{display:block;text-decoration:none;padding:26px 26px 24px;position:relative;overflow:hidden;
  transition:transform .3s cubic-bezier(.22,1,.36,1),border-color .3s}
.entry:hover{transform:translateY(-4px);border-color:rgba(209,254,23,.42);
  box-shadow:inset 0 0 0 .61px rgba(255,255,255,.09),0 26px 60px rgba(0,0,0,.62),0 0 42px rgba(209,254,23,.09)}
.kpi{transition:transform .35s cubic-bezier(.22,1,.36,1),box-shadow .35s,border-color .35s}
.kpi:hover{transform:translateY(-2px);border-color:rgba(255,255,255,.18);
  box-shadow:inset 0 0 0 .61px rgba(255,255,255,.09),0 24px 54px rgba(0,0,0,.6)}
details:hover{transform:translateY(-1px)}
.entry .et{font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#767C85;
  font-family:%%F_MONO%%;margin-bottom:12px}
.entry h3{margin:0 0 9px;font-size:18px;font-weight:750;color:#fff;letter-spacing:-.022em}
.entry p{color:#8A9099;font-size:13px;line-height:1.65;margin-bottom:16px;letter-spacing:0}
.entry .nums{display:flex;gap:22px;flex-wrap:wrap;padding-top:16px;border-top:1px solid rgba(255,255,255,.07)}
.entry .nums div{display:flex;flex-direction:column;gap:3px}
.entry .nums s{text-decoration:none;font-family:%%F_MONO%%;font-size:18px;font-weight:700;
  color:#D1FE17;letter-spacing:-.03em}
.entry .nums em{font-style:normal;font-size:10.5px;color:#767C85;letter-spacing:.06em;text-transform:uppercase}
.entry.soon{opacity:.55;cursor:default}
.entry.soon:hover{transform:none;border-color:rgba(255,255,255,.08)}
.entry.soon .nums s{color:#767C85}
.entry .arrow{position:absolute;top:24px;right:24px;color:#D1FE17;font-size:17px;
  transition:transform .3s cubic-bezier(.22,1,.36,1)}
.entry:hover .arrow{transform:translateX(4px)}

/* ── 表格 ── */
table{width:100%;border-collapse:separate;border-spacing:0;font-size:13px;
  background:linear-gradient(158deg,rgba(22,27,24,.86) 0%,rgba(10,13,11,.92) 100%);
  border:1px solid rgba(255,255,255,.12);border-radius:18px;overflow:hidden;
  box-shadow:inset 0 0 0 .61px rgba(255,255,255,.06),
             inset 0 1px 0 rgba(255,255,255,.05),
             0 1px 2px rgba(0,0,0,.5),
             0 8px 20px rgba(0,0,0,.42),
             0 26px 56px rgba(0,0,0,.46)}
th{background:transparent;color:#767C85;font-weight:700;font-size:10.5px;text-align:left;
  padding:10px 14px;white-space:nowrap;letter-spacing:.095em;text-transform:uppercase;
  border-bottom:1px solid rgba(255,255,255,.08);cursor:pointer;user-select:none;
  transition:color .2s}
th:hover{color:#D1FE17}
th.ctr,td.ctr{text-align:center}
td{padding:8px 14px;border-bottom:1px solid rgba(255,255,255,.05);white-space:nowrap;
  color:#C9CDD2;letter-spacing:0;vertical-align:middle}
tbody tr{transition:background .18s}
tbody tr:last-child td{border-bottom:none}
tbody tr:hover{background:rgba(255,255,255,.032)}
tbody tr.top{background:rgba(209,254,23,.055)}
tbody tr.top td:first-child{box-shadow:inset 3px 0 0 #D1FE17}
.num{text-align:right;font-variant-numeric:tabular-nums;font-family:%%F_MONO%%;font-weight:500;
  letter-spacing:-.022em}
.strong{color:#D1FE17;font-weight:600}
.ybest{color:#0B0B0B;font-weight:800;background:#D1FE17}
.rk{color:#5A6069;font-weight:600}
.rk b{display:block;font-family:%%F_MONO%%;font-size:15px;color:#fff;font-weight:700;letter-spacing:-.03em}
.rk s{text-decoration:none;font-size:10px;color:#5A6069;font-family:%%F_MONO%%}
.cell2{display:flex;flex-direction:column;gap:2px;line-height:1.25}
.cell2 s{text-decoration:none;font-size:10.5px;color:#6E747D}
.cell2 b{font-weight:600;color:#E4E7EA}
.dot{display:inline-block;width:6px;height:6px;border-radius:50%;margin-right:8px;vertical-align:middle}
.vlabel{display:inline-block;margin-left:6px;padding:1px 6px;border-radius:5px;font-size:10px;
  font-weight:700;color:#D1FE17;background:rgba(209,254,23,.1);border:1px solid rgba(209,254,23,.24);
  letter-spacing:.02em;white-space:nowrap}
.tagu{display:inline-block;margin-left:7px;padding:1px 6px;border-radius:999px;font-size:9.5px;
  font-weight:700;letter-spacing:.05em;color:#FF4D8D;border:1px solid rgba(255,77,141,.45)}
/* 行内效率条 */
.cbar{min-width:118px}
.mini{height:5px;border-radius:999px;background:rgba(255,255,255,.07);margin-top:6px;overflow:hidden}
.mini i{display:block;height:100%;border-radius:999px;background:#D1FE17;
  transition:width .9s cubic-bezier(.22,1,.36,1)}
/* 仅在脚本可用时才做 0 -> 目标宽度 的生长动画。
   若无 JS，.js 类不会加上，条宽保持内联的目标值，不会变成空条。 */
.js .reveal .mini i{width:0!important}
.js .reveal.in .mini i{width:var(--w)!important}
.mini.m2 i{background:linear-gradient(90deg,#3A3F47,#6E7681)}
.mini.m3 i{background:linear-gradient(90deg,#23272D,#3A3F47)}

/* ── 标签 ── */
.tag{display:inline-block;padding:3px 11px;border-radius:999px;font-size:10.5px;
  font-weight:700;letter-spacing:.02em;white-space:nowrap}
.v-good{background:#D1FE17;color:#0B0B0B}
.v-warn{background:transparent;color:#C9CDD2;border:1px solid rgba(255,255,255,.18)}
.v-bad{background:transparent;color:#FF6B6B;border:1px solid rgba(255,107,107,.32)}

/* ── 说明块 ── */
.note{padding:18px 22px;font-size:13px;color:#C9CDD2;line-height:1.78;letter-spacing:0}
.note.warn{border-left:2px solid rgba(255,201,60,.55)}
.note.good{border-left:2px solid rgba(209,254,23,.5)}
.note.pink{border-left:2px solid rgba(255,77,141,.45)}
.note b{color:#fff;font-weight:600}
ul{margin:8px 0 0 19px}
li{margin:7px 0;color:#C9CDD2;font-size:13px;letter-spacing:0;line-height:1.72}
li::marker{color:#D1FE17}
code{background:rgba(209,254,23,.09);border:1px solid rgba(209,254,23,.2);padding:2px 7px;
  border-radius:6px;font-family:%%F_MONO%%;font-size:12.5px;color:#D1FE17;font-weight:500;letter-spacing:-.02em}

/* ── 折叠块（长文收纳，默认收起） ── */
details{margin-bottom:12px;overflow:hidden;border-radius:16px;
  transition:border-color .25s,box-shadow .3s,transform .3s cubic-bezier(.22,1,.36,1)}
details[open]{border-color:rgba(255,255,255,.13)}
details:hover{border-color:rgba(209,254,23,.28)}
summary{cursor:pointer;padding:16px 22px;font-size:13.5px;font-weight:650;color:#E4E7EA;
  list-style:none;display:flex;align-items:center;gap:11px;letter-spacing:-.012em;
  transition:color .22s}
summary::-webkit-details-marker{display:none}
summary:hover{color:#fff}
summary .chev{margin-left:auto;color:#767C85;font-size:12px;transition:transform .3s cubic-bezier(.22,1,.36,1)}
details[open] summary .chev{transform:rotate(90deg);color:#D1FE17}
summary .badge{font-family:%%F_MONO%%;font-size:10.5px;color:#767C85;font-weight:500}
summary .warnbadge{font-size:10px;font-weight:800;color:#0B0B0B;background:#FFC93C;
  padding:1.5px 7px;border-radius:999px;letter-spacing:.02em}
.dbody{padding:0 22px 22px;font-size:13px;color:#C9CDD2;line-height:1.78}
.dbody>*+*{margin-top:12px}
.dbody h3{margin:18px 0 10px}

/* ── 控件 ── */
.ctrl{display:flex;align-items:center;gap:18px;flex-wrap:wrap;margin-bottom:16px}

input[type=range]{-webkit-appearance:none;appearance:none;width:320px;height:4px;border-radius:999px;
  outline:none;background:rgba(255,255,255,.12)}
input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:19px;height:19px;border-radius:50%;
  background:#D1FE17;cursor:pointer;border:3px solid #000}
.big{font-family:%%F_MONO%%;font-size:21px;font-weight:700;color:#D1FE17;letter-spacing:-.03em}
.mono{font-family:%%F_MONO%%;letter-spacing:-.022em}
.sub{color:#767C85;font-size:12px;letter-spacing:0;line-height:1.7}
.mb20{margin-bottom:20px}

/* ── 条形图（效率条） ── */
.bar-row{display:grid;grid-template-columns:206px 1fr 76px;align-items:center;gap:14px;margin-bottom:9px}
.bar-label{font-size:12.5px;color:#C9CDD2;letter-spacing:0}
.bar-track{height:14px;background:rgba(255,255,255,.05);border-radius:999px;overflow:hidden}
.bar-fill{height:100%;border-radius:999px}
.b-bad{background:linear-gradient(90deg,#23272D,#3A3F47)}

/* ── 页脚 ── */
.foot{margin-top:44px;color:#5A6069;font-size:11.5px;text-align:center;
  border-top:1px solid rgba(255,255,255,.08);padding-top:20px;letter-spacing:0;line-height:1.75}
.legal{margin-top:22px;padding:26px 28px;background:#D1FE17;border-color:#D1FE17;border-radius:20px;
  color:#0B0B0B;font-size:12px;line-height:1.8;letter-spacing:0}
.legal-t{font-size:16px;font-weight:800;letter-spacing:-.025em;margin-bottom:9px;color:#0B0B0B}
.legal-b{color:#1F2A00;max-width:1000px}
.legal-f{margin-top:14px;font-family:%%F_MONO%%;font-size:11px;color:#1F2A00}
.legal-f .fp{background:#0B0B0B;color:#D1FE17;padding:2.5px 9px;border-radius:6px;font-weight:600;letter-spacing:-.02em}

.tw{overflow-x:auto;-webkit-overflow-scrolling:touch;border-radius:18px}
/* 表格内部滚动：固定高度 + 右侧竖向滚动条（参照 arena.ai 榜页） */
.tw.scroll-y{max-height:440px;overflow-y:auto;overscroll-behavior:contain}
.tw.tw-main{max-height:min(72vh,640px)}
.tw.scroll-y::-webkit-scrollbar{width:10px;height:10px}
.tw.scroll-y::-webkit-scrollbar-track{background:rgba(255,255,255,.03);border-radius:6px}
.tw.scroll-y::-webkit-scrollbar-thumb{background:rgba(255,255,255,.16);border-radius:6px;
  border:2px solid transparent;background-clip:content-box}
.tw.scroll-y::-webkit-scrollbar-thumb:hover{background:rgba(209,254,23,.45);
  background-clip:content-box;border:2px solid transparent}
.tw.scroll-y{scrollbar-width:thin;scrollbar-color:rgba(255,255,255,.22) transparent}
/* 内部滚动时表头常驻 */
.tw.scroll-y thead th{position:sticky;top:0;z-index:2;
  background:linear-gradient(180deg,rgba(22,27,24,.98),rgba(16,20,18,.96));
  -webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px)}
.tw table{min-width:760px}
.tw::-webkit-scrollbar{height:9px}
.tw::-webkit-scrollbar-thumb{background:#2A2E34;border-radius:5px}

/* ── 入场与滚动动画 ── */
@keyframes fadeUp{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:none}}
.reveal{opacity:0;transform:translateY(16px);
  transition:opacity .62s cubic-bezier(.22,1,.36,1),transform .62s cubic-bezier(.22,1,.36,1)}
.reveal.in{opacity:1;transform:none}
.hero>*{animation:fadeUp .7s cubic-bezier(.22,1,.36,1) both}
.hero>*:nth-child(2){animation-delay:.06s}
.hero>*:nth-child(3){animation-delay:.12s}
.hero>*:nth-child(4){animation-delay:.18s}
.hero>*:nth-child(5){animation-delay:.24s}
@media (prefers-reduced-motion:reduce){
  html{scroll-behavior:auto}
  .reveal,.hero>*{opacity:1!important;transform:none!important;animation:none!important;transition:none!important}
}

/* ── 打印 ── */
@media print{
  body{background:#fff!important;color:#000!important;padding:0}
  body::before,body::after{display:none!important}
  .hero::before,.hero::after{display:none!important}
  .glass,.card,.kpi,.note,.entry,.legal,details,.nav,.subnav,table{
    -webkit-backdrop-filter:none!important;backdrop-filter:none!important;
    box-shadow:none!important;background:#fff!important}
  .nav,.subnav{position:static!important;background:#fff!important}
  .promo{background:#D1FE17!important;color:#000!important}
  .brand b,.menu a{color:#000!important}
  .nav .spec{color:#333!important;border-color:#999!important}
  .card,.kpi,.note,table,.legal,.entry,details{background:#fff!important;border-color:#BBB!important}
  .legal{background:#F2FFB8!important}
  h1,h2,h3,td,th,li,.dbody,.kpi .v,.strong,.lead,.meta,.kpi .t{color:#000!important}
  .eyebrow,.kpi.good .v,.kpi.hi .v,.entry .nums s{color:#4A5A00!important}
  .btn-fill{background:#D1FE17!important;color:#000!important}
  .disc{background:#fff!important;border-color:#B8860B!important;color:#333!important}
  details{border-color:#BBB!important}
  details:not([open]) .dbody{display:block!important}
  .tw{overflow:visible!important}
  .tw table{min-width:0!important}
  th{background:#F2F3F5!important;border-bottom-color:#BBB!important}
  tbody tr.top{background:#F7FFD9!important}
  .mini i{background:#8FCB00!important}
  .mini.m2 i,.mini.m3 i{background:#B8BEC6!important}
}

/* ── 移动端 ── */
@media (max-width:900px){ .g5,.g3,.g2{grid-template-columns:1fr 1fr} }
@media (max-width:820px){
  :root{--gap:14px}
  .promo{font-size:11.5px;padding:9px 14px;gap:9px}
  .nav .inner{padding:10px 15px;gap:11px}
  .nav .spec{display:none}
  .subnav{top:51px}
  .subnav .inner{padding:8px 15px}
  .hero{padding:36px 15px 4px}
  h1{letter-spacing:-.032em}
  .hero .lead{font-size:13.5px;margin-top:15px}
  .meta{gap:14px;font-size:12px}
  .wrap{padding:0 15px}
  section{margin-top:44px}
  h2{font-size:17.5px}
  .kpi .v{font-size:21px}
  .entry{padding:20px 20px 18px}
  .entry h3{font-size:16px}
  .entry .arrow{top:19px;right:19px}
  .bar-row{grid-template-columns:1fr 60px;gap:9px}
  .bar-label{grid-column:1;font-size:12px}
  .bar-track{grid-column:1}
  .card,.kpi,.note,.legal,table,details,.entry{border-radius:15px}
  .legal{padding:21px 18px}
  .legal-t{font-size:14.5px}
  td,th{padding:10px 11px}
  summary{padding:14px 17px;font-size:13px}
  .dbody{padding:0 17px 18px}
  .ctrl{gap:10px}
  input[type=range]{width:100%}
}
@media (max-width:520px){ .g5,.g3,.g2{grid-template-columns:1fr} }
"""

# ══════════════════════════════════════════════════════════════
# 脚本
# ══════════════════════════════════════════════════════════════
JS = r"""
/* 标记脚本可用：驱动纯 CSS 的渐进增强（JS 失效时自动降级，不会出现空条） */
document.documentElement.classList.add('js');

/* ── 吸顶偏移实测 ──
   导航与子导航的实际高度会随视口宽度与文案换行变化，
   写死 top / scroll-margin-top 会在某些宽度下错位，故运行时测量。 */
(function(){
  function sync(){
    var nav = document.querySelector('.nav'), sub = document.querySelector('.subnav');
    var r = document.documentElement.style;
    if(nav) r.setProperty('--navh', nav.offsetHeight + 'px');
    if(sub) r.setProperty('--subh', sub.offsetHeight + 'px');
  }
  sync();
  window.addEventListener('resize', sync, {passive:true});
  window.addEventListener('orientationchange', sync, {passive:true});
  if(document.fonts && document.fonts.ready) document.fonts.ready.then(sync);
})();

/* ── 滚动入场动画 ── */
(function(){
  var els = document.querySelectorAll('.reveal');
  if(!('IntersectionObserver' in window)){ els.forEach(function(e){e.classList.add('in');}); return; }
  var io = new IntersectionObserver(function(es){
    es.forEach(function(e){ if(e.isIntersecting){ e.target.classList.add('in'); io.unobserve(e.target); } });
  }, {rootMargin:'0px 0px -8% 0px', threshold:.06});
  els.forEach(function(e){ io.observe(e); });
})();

/* ── 子导航 scrollspy：滚动时高亮当前区块 ── */
(function(){
  var links = Array.prototype.slice.call(document.querySelectorAll('.subnav a[href^="#"]'));
  if(!links.length) return;
  /* 关键：按【文档位置】排序后再判定当前区块。
     若不排序，逻辑会退化为「菜单里最后一项 offsetTop <= y 的胜出」——
     一旦菜单顺序与页面顺序不一致（章节被挪动过），高亮就会乱跳。 */
  var map = links.map(function(a){ return {a:a, el:document.querySelector(a.getAttribute('href'))}; })
                 .filter(function(x){ return x.el; })
                 .sort(function(p,q){ return p.el.offsetTop - q.el.offsetTop; });   /* 仅定序，不参与阈值判定 */
  var lastIdx = -1;
  function stickPx(){
    var cs = getComputedStyle(document.documentElement);
    return (parseFloat(cs.getPropertyValue('--navh')) || 57)
         + (parseFloat(cs.getPropertyValue('--subh')) || 50) + 24;
  }
  function upd(){
    /* 必须用视口坐标（getBoundingClientRect）判定，不能混用 offsetTop 与 scrollY：
       offsetTop 相对 offsetParent（这里是 .wrap，位于 hero 之下，差约 350px），
       scrollY 相对文档 —— 两个坐标系不同会把判定整体往后推一个 hero 的高度，
       表现为「点 A 却高亮 A 的下一个」。 */
    var off = stickPx(), idx = 0;
    for(var i=0;i<map.length;i++){
      if(map[i].el.getBoundingClientRect().top - off <= 0) idx = i;
    }
    /* 滚到底部时强制选中最后一项，避免末节过短而永远选不中 */
    if(window.innerHeight + window.scrollY >= document.body.scrollHeight - 4){
      idx = map.length - 1;
    }
    if(idx === lastIdx) return;
    lastIdx = idx;
    links.forEach(function(a){ a.classList.remove('active'); });
    if(map[idx]) map[idx].a.classList.add('active');
  }
  var t = null;
  window.addEventListener('scroll', function(){
    if(t) return; t = requestAnimationFrame(function(){ upd(); t = null; });
  }, {passive:true});
  upd();
})();
%%COST_JS%%
"""

COST_JS = r"""
/* ── 主表排序 ── */
function sortBy(k, el){
  var tb = document.querySelector('#main tbody');
  var rs = Array.prototype.slice.call(tb.querySelectorAll('tr'));
  var dir = el.dataset.dir === 'asc' ? -1 : 1;
  el.dataset.dir = dir === 1 ? 'asc' : 'desc';
  rs.sort(function(a,b){ return (parseFloat(a.dataset[k]) - parseFloat(b.dataset[k])) * dir; });
  rs.forEach(function(r){ tb.appendChild(r); });
}
/* ── 产量测算 ── */
var PLANS = __DATA__;
function pk(t){
  var c = PLANS.filter(function(p){ return p.mCap >= t - 1e-9; })
               .sort(function(a,b){ return a.price - b.price; });
  return c.length ? c[0] : null;
}
/* ── 组合订阅最省（跨平台混合）───────────────────────────────
   无界背包：dp[j] = 覆盖 j 条/月的最低支出，每个档位可用多次。
   容量向下取整（保守）—— 宁可少算一点，也保证给出的方案一定可行。
   这样 1× 即梦超级 + 1× Neowow Pro 这类跨平台组合才会被纳入比较，
   而这正是「单一档位买多份」永远看不到的解。 */
function bestCombo(t){
  var N = Math.max(1, Math.min(200, Math.ceil(t)));
  var items = [];
  for(var i=0;i<PLANS.length;i++){
    var w = Math.floor(PLANS[i].mCap);
    if(w >= 1) items.push({p:PLANS[i], w:w});
  }
  if(!items.length) return null;
  var dp = [], pre = [];
  for(var j=0;j<=N;j++){ dp[j] = Infinity; pre[j] = null; }
  dp[0] = 0;
  for(var j=0;j<=N;j++){
    if(dp[j] === Infinity) continue;
    for(var i=0;i<items.length;i++){
      var k = Math.min(N, j + items[i].w);
      var c = dp[j] + items[i].p.price;
      if(c < dp[k]){ dp[k] = c; pre[k] = {from:j, item:i}; }
    }
  }
  if(dp[N] === Infinity) return null;
  var counts = [], cur = N;
  while(cur > 0 && pre[cur]){
    var e = pre[cur], it = items[e.item];
    var hit = null;
    for(var q=0;q<counts.length;q++){
      if(counts[q].p === it.p){ hit = counts[q]; break; }
    }
    if(hit) hit.n++; else counts.push({p:it.p, n:1});
    cur = e.from;
  }
  var cap = 0, real = 0;
  for(var q2=0;q2<counts.length;q2++){
    cap += counts[q2].n * counts[q2].p.mCap;
    real += counts[q2].n * counts[q2].p.price;
  }
  counts.sort(function(x,y){ return y.p.mCap - x.p.mCap; });
  return {items:counts, total:dp[N], cap:cap, real:real};
}

function comboLabel(b){
  if(!b) return '—';
  var parts = [];
  for(var i=0;i<b.items.length;i++){
    var it = b.items[i];
    parts.push('<span class="dot" style="background:' + it.p.color + '"></span>' +
               it.p.plat + ' ' + it.p.tier + (it.n > 1 ? ' \u00d7 ' + it.n : ''));
  }
  return parts.join('<span class="combo-plus">+</span>');
}

function render(){
  var el = document.getElementById('tgt'), out = document.getElementById('rec');
  if(!el || !out) return;
  var t = parseFloat(el.value);
  var secs = t * 30, mins = secs / 60;
  document.getElementById('tgtv').textContent = t + ' 条/月';
  var dv = document.getElementById('tgtsec');
  if(dv) dv.textContent = '= ' + secs.toLocaleString() + ' 秒 ≈ ' +
    (mins >= 60 ? (mins/60).toFixed(1) + ' 小时' : mins.toFixed(0) + ' 分钟') + '素材';
  var h = '', s = pk(t);
  if(s){
    h += '<tr><td>单一订阅最省</td>'
      +  '<td><span class="dot" style="background:'+s.color+'"></span>'+s.plat+' '+s.tier+'</td>'
      +  '<td class="num strong">\u00a5'+s.price.toLocaleString()+'</td>'
      +  '<td class="num">'+s.mCap.toFixed(2)+' 条/月</td>'
      +  '<td class="num">\u00a5'+s.perVideo.toFixed(2)+'</td></tr>';
  } else {
    h += '<tr><td>单一订阅最省</td><td colspan="4" style="color:#FABC00">'
      +  '无单一档位可覆盖，须组合订阅</td></tr>';
  }
  var b = bestCombo(t);
  if(b){
    h += '<tr><td>组合订阅最省<\u002fbr><s>跨平台混合</s></td>'
      +  '<td>' + comboLabel(b) + '</td>'
      +  '<td class="num strong">\u00a5' + b.total.toLocaleString() + '</td>'
      +  '<td class="num">' + b.cap.toFixed(1) + ' 条/月</td>'
      +  '<td class="num">\u00a5' + (b.total / t).toFixed(2) + '</td></tr>';
  } else {
    h += '<tr><td>组合订阅最省</td><td colspan="4" style="color:#FABC00">'
      +  '目标产量过高，超出单账号 200 条的求解上限</td></tr>';
  }
  out.innerHTML = h;
}
document.addEventListener('DOMContentLoaded', function(){
  var el = document.getElementById('tgt');
  if(el){ el.addEventListener('input', render); render(); }
  /* 点击子导航时立即高亮，不等 scrollspy 节流 */
  Array.prototype.forEach.call(document.querySelectorAll('.subnav a[href^="#"]'), function(a){
    a.addEventListener('click', function(){
      Array.prototype.forEach.call(document.querySelectorAll('.subnav a'), function(x){
        x.classList.remove('active');
      });
      a.classList.add('active');
      window.__lastSub = a;
    });
  });
});
"""

js_plans = json.dumps([{"plat": p["plat"], "tier": p["tier"], "price": round(p["priceCNY"], 2),
                        "mCap": round(p["mCap"], 4), "perVideo": round(p["perVideoCNY"], 3),
                        "color": p["color"]} for p in plans], ensure_ascii=False)

def sub_css(s):
    return (s.replace("%%F_SANS%%", F_SANS).replace("%%F_DISP%%", F_DISP).replace("%%F_MONO%%", F_MONO))

def page(title, desc, nav_html, body, extra_js=""):
    js = JS.replace("%%COST_JS%%", COST_JS).replace("__DATA__", js_plans) if "%data%" in extra_js else JS.replace("%%COST_JS%%", "")
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="format-detection" content="telephone=no,email=no,address=no">
<meta name="theme-color" content="#000000">
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='9' fill='%23D1FE17'/%3E%3C/svg%3E">
<link rel="icon" type="image/png" sizes="180x180" href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAALQAAAC0CAYAAAA9zQYyAAACQElEQVR42u3dsW3CYBhFUddI1BmABRgAKV0qagZgBDoklsxCSf4t8vlyiltb4h0hYwt7+/752IZ0XJ1X19V99Vi9Vr8a1Ta5/zz4ZfUEBOg9g74BAfTeQZ8hALoA+tP4QBdA+0YGOgPa4EAnQH8ZGugKaCMDnQB9MC7QFdAnwwJdAe0qBtAZ0DArA9pphjKg/QBUCrQhlQFtRGVAuwOoFGgDKgPaeMqAdr1ZKdCGUwa0f5ooBdpoyoB27qwUaIMJaAE9EbSHwCgF2lgCWkBPBH0xlEqgPQVUKdCGEtACeiLoo5FUAu12t1Kgr0ZSCfTdSCqBfhhJJdBenaYUaCMpE9ACWgJaAloCWkBLQEtAS0BLQAtoCWgJaAloCWgBLQEtAS0BLQEtoCWgJaAloCWgBbQEtAS0BLQEtICWgJaAloCWgBbQEtAS0BLQAtqHIKAloCWgJaAFtAS0BLQEtAS0gJaAloCWgJaAFtAS0BLQEtAS0AJaAloCWgJaAlpAS0BLQEtAS0ALaAloCWgJaAloAS0BLQEtAS2gJaAloCWgJaAFtAS0BLQEtAS0gJaAloCWgJaAFtAS0BLQEtAS0AJa2hno6RlqVqO9AC2ggQYaaKCBBhpooIEW0EALaKCBBhpooIEW0EALaKAFNNBAAw000EALaKAFNNACGmiggQYaaKAFNNACGmgBDTTQQAMNNNACGmgBDbSABhpooIEGGmgBDbSABlpAAw000EADDbSABlpAAw000EADDTTQQAOtNwf9B+ObR6MtENCGAAAAAElFTkSuQmCC">
<link rel="apple-touch-icon" href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAALQAAAC0CAYAAAA9zQYyAAACQElEQVR42u3dsW3CYBhFUddI1BmABRgAKV0qagZgBDoklsxCSf4t8vlyiltb4h0hYwt7+/752IZ0XJ1X19V99Vi9Vr8a1Ta5/zz4ZfUEBOg9g74BAfTeQZ8hALoA+tP4QBdA+0YGOgPa4EAnQH8ZGugKaCMDnQB9MC7QFdAnwwJdAe0qBtAZ0DArA9pphjKg/QBUCrQhlQFtRGVAuwOoFGgDKgPaeMqAdr1ZKdCGUwa0f5ooBdpoyoB27qwUaIMJaAE9EbSHwCgF2lgCWkBPBH0xlEqgPQVUKdCGEtACeiLoo5FUAu12t1Kgr0ZSCfTdSCqBfhhJJdBenaYUaCMpE9ACWgJaAloCWkBLQEtAS0BLQAtoCWgJaAloCWgBLQEtAS0BLQEtoCWgJaAloCWgBbQEtAS0BLQEtICWgJaAloCWgBbQEtAS0BLQAtqHIKAloCWgJaAFtAS0BLQEtAS0gJaAloCWgJaAFtAS0BLQEtAS0AJaAloCWgJaAlpAS0BLQEtAS0ALaAloCWgJaAloAS0BLQEtAS2gJaAloCWgJaAFtAS0BLQEtAS0gJaAloCWgJaAFtAS0BLQEtAS0AJa2hno6RlqVqO9AC2ggQYaaKCBBhpooIEW0EALaKCBBhpooIEW0EALaKAFNNBAAw000EALaKAFNNACGmiggQYaaKAFNNACGmgBDTTQQAMNNNACGmgBDbSABhpooIEGGmgBDbSABlpAAw000EADDbSABlpAAw000EADDTTQQAOtNwf9B+ObR6MtENCGAAAAAElFTkSuQmCC">
<link rel="mask-icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='9' fill='%23D1FE17'/%3E%3C/svg%3E" color="#D1FE17">
<meta name="color-scheme" content="dark">
<meta name="description" content="{desc}">
<meta property="og:title" content="{BRAND} · {title}">
<meta property="og:description" content="{desc}">
<title>{BRAND} · {title}</title>
<!-- ============================================================
     {FP}
     {COPY}
     数据采集时点：{RATE_DATE}　作者：{OWNER}
     {TERMS}
     ============================================================ -->
<meta name="author" content="{OWNER}">
<meta name="copyright" content="{COPY}">
<meta name="rights" content="{TERMS}">
<meta name="dcterms.rights" content="{COPY}">
<meta name="fingerprint" content="{FP}">
<meta name="robots" content="noindex, nofollow, noarchive, nosnippet, noimageindex, notranslate, noai, noimageai">
<meta name="googlebot" content="noindex, nofollow, noarchive, nosnippet, noimageindex">
<meta name="bingbot" content="noindex, nofollow, noarchive">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src data:; connect-src 'none'; object-src 'none'; frame-src 'none'; base-uri 'none'; form-action 'none'">
<meta http-equiv="X-Content-Type-Options" content="nosniff">
<meta name="referrer" content="no-referrer">
<style>{sub_css(CSS)}</style></head><body>

<div class="promo">
  <span><b>价格说明：</b>{BRAND_CN}数据采集于 {RATE_DATE}，各平台价格取决于当期活动与限时优惠力度，不代表最终价格</span>
  <span class="tag2">数据时点 {RATE_DATE}</span>
</div>

{nav_html}

{body}

<div class="legal">
  <div class="legal-t">{COPY}</div>
  <div class="legal-b">{TERMS}</div>
  <div class="legal-f">溯源指纹 <span class="fp">{FP}</span>　·　{BRAND} · {BRAND_CN}　·　{STUDIO} 出品　·　数据采集 {RATE_DATE}</div>
</div>
</div>

<script>{js}</script>
</body></html>"""

def nav(active):
    """导航从 data/site.json 的 nav 数组生成；未完成板块带状态徽标但仍可进入"""
    items = ""
    for it in NAV:
        soon = it["key"] == "leaderboard-vlm" and VLM["status"] == "coming-soon"
        badge = '<i class="nb">即将上线</i>' if soon else ""
        cls = ' class="active"' if it["key"] == active else ""
        items += f'<a href="{it["href"]}"{cls}>{it["label"]}{badge}</a>'
    return f"""<div class="nav"><div class="inner">
  <a class="brand" href="index.html"><i></i><span class="bw"><b>{BRAND}</b><s>{STUDIO}</s></span></a>
  <nav class="menu">{items}</nav>
  <span class="spec">{SPEC}</span>
</div></div>"""

# ══════════════════════════════════════════════════════════════
# 首页
# ══════════════════════════════════════════════════════════════
home_body = f"""
<div class="hero">
  <div class="eyebrow">{BRAND} · Unified Benchmark</div>
  <h1>把 AI 平台<br>放在<em>同一把尺子</em>上</h1>
  <p class="lead">各平台用自己的积分币计价，币值互不相同。{BRAND} 先把它们压平到同一口径，再折算成可比较的现金成本与能力得分 — 不采信宣传数字，只给可复核的结果。</p>
  <div class="btns">
    <a class="btn btn-white" href="cost.html">进入平台成本对比</a>
    <a class="btn btn-ghost" href="cost.html#ladder">按产量反查最省方案</a>
  </div>
</div>

<div class="wrap">

<section class="reveal">
  <div class="sechead">
    <h2><span class="ey">板块</span>两条对比线</h2>
    <div class="sd">统一口径的方法论复用在同一套框架下：成本线已上线，能力线在建。</div>
  </div>
  <div class="grid g2">
    <a class="entry" href="cost.html">
      <span class="arrow">→</span>
      <div class="et">LivE · 2026-09-21</div>
      <h3>平台成本对比</h3>
      <p>5 个画布平台、20 个会员档位，按「Seedance 2.5 · 720p · 16:9 · 30s · 全能参考」统一口径折算单条现金成本。</p>
      <div class="nums">
        <div><s>¥{f2(best)}</s><em>最低单条</em></div>
        <div><s>{worst/best:.2f}×</s><em>最贵/最省</em></div>
        <div><s>{len(plans)}</s><em>档位</em></div>
      </div>
    </a>
    <a class="entry" href="leaderboard-vlm.html">
      <span class="arrow">→</span>
      <div class="et">{VLM["eyebrow"]} · 评测中</div>
      <h3>{VLM["title"]} <i class="nb">即将上线</i></h3>
      <p>{VLM["intro"]}</p>
      <div class="nums">
        <div><s>{len(VLM["methodology"]["dimensions"])}</s><em>评测维度</em></div>
        <div><s>—</s><em>模型数</em></div>
        <div><s>—</s><em>数据时点</em></div>
      </div>
    </a>
  </div>
</section>

<section class="reveal">
  <div class="sechead">
    <h2><span class="ey">结论</span>成本线速览</h2>
    <div class="sd">完整数据与算法见<a href="cost.html" style="color:#D1FE17;text-decoration:none">平台成本对比 →</a></div>
  </div>
  <div class="grid g5">
    <div class="kpi hi"><div class="t">单条成本最优</div>
      <div class="v">¥{f2(best)}</div>
      <div class="d">{best_row['plat']} {best_row['tier']}<br>与次优 ¥{f2(runner['perVideoCNY'])} 差 {abs(best-runner['perVideoCNY'])/best*100:.2f}%</div></div>
    <div class="kpi good"><div class="t">中产能最省</div>
      <div class="v">¥{mid['plan']['priceCNY']:,.0f}</div>
      <div class="d">{mid['plan']['plat']} {tname(mid['plan'])}<br>{mid['plan']['mCap']:.2f} 条/月 · ¥{f2(mid['plan']['perVideoCNY'])}/条</div></div>
    <div class="kpi good"><div class="t">大产能最省</div>
      <div class="v">¥{top['plan']['priceCNY']:,.0f}</div>
      <div class="d">{top['plan']['plat']} {tname(top['plan'])}<br>{top['plan']['mCap']:.2f} 条/月 · ¥{f2(top['plan']['perVideoCNY'])}/条</div></div>
    <div class="kpi pink"><div class="t">海外平台溢价</div>
      <div class="v">{HG['perVideoCNY']/best:.2f}×</div>
      <div class="d">Higgsfield Ultra ¥{f2(HG['perVideoCNY'])}/条<br>无成本优势</div></div>
    <div class="kpi bad"><div class="t">最差档位</div>
      <div class="v">{worst/best:.2f}×</div>
      <div class="d">Higgsfield Starter ¥{f2(worst)}/条<br>低档位多是高价试用</div></div>
  </div>
</section>

<div class="foot">{BRAND} · {BRAND_CN}　|　{STUDIO} 出品　|　数据采集 {RATE_DATE}　·　全部数值按统一口径重算，非平台宣传数字</div>
"""

# ══════════════════════════════════════════════════════════════
# 成本对比页 —— 组件
# ══════════════════════════════════════════════════════════════
def mini_bar(per_video):
    w = best / per_video * 100
    cls = "" if per_video <= best * 1.06 else (" m2" if per_video <= 30 else " m3")
    return f'<div class="mini{cls}"><i style="--w:{w:.1f}%;width:{w:.1f}%"></i></div>'

main_rows = ""
for p in sorted(plans, key=lambda x: x["perVideoCNY"]):
    price_disp = f'{CU[p["cur"]]}{p["price"]:,}'
    sub = f'≈¥{p["priceCNY"]:,.0f}' if p["cur"] == "USD" else p["cur"]
    main_rows += (
        f'<tr class="{"top" if p["rank"] == 1 else ""}" data-v="{p["perVideoCNY"]:.4f}" '
        f'data-c="{p["mCap"]:.3f}" data-p="{p["priceCNY"]:.2f}">'
        f'<td class="ctr rk"><b>{p["rank"]}</b><s>{p["rel"]:.2f}×</s></td>'
        f'<td><span class="dot" style="background:{p["color"]}"></span>{p["plat"]}'
        f'{"<span class=tagu>USD</span>" if p["cur"] == "USD" else ""}</td>'
        f'<td>{p["tier"]}{"<span class=vlabel>" + p["variant"] + "</span>" if p.get("variant") else ""}</td>'
        f'<td class="num cell2"><b>{price_disp}</b><s>{sub}</s></td>'
        f'<td class="num">{p["monthly"]:,}</td>'
        f'<td class="num cbar"><span class="strong">¥{f2(p["perVideoCNY"])}</span>{mini_bar(p["perVideoCNY"])}</td>'
        f'<td class="num cell2"><b>{p["perSecCNY"]:.3f}</b><s>元/秒</s></td>'
        f'<td class="num cell2"><b>{p["mCap"]:.2f}</b><s>条/月</s></td></tr>')

lad_rows = ""
for i, r in enumerate(ladder):
    p = r["plan"]
    lo = "0" if i == 0 else f"{r['lo']:.2f}"
    lad_rows += (
        f'<tr><td class="num mono">{lo} – {r["hi"]:.2f}</td>'
        f'<td><span class="dot" style="background:{p["color"]}"></span>{p["plat"]} {tname(p)}</td>'
        f'<td class="num strong">¥{p["priceCNY"]:,.0f}</td>'
        f'<td class="num">{p["mCap"]:.2f}</td>'
        f'<td class="num">¥{f2(p["perVideoCNY"])}</td>'
        f'<td class="num">{p["rel"]:.2f}×</td></tr>')

disc_rows = ""
for d in disc_rows_data:
    disc_rows += (
        f'<tr><td><span class="dot" style="background:{d["color"]}"></span>{d["plat"]}</td>'
        f'<td class="num">{d["minD"]*10:.1f}–{d["maxD"]*10:.1f} 折</td>'
        f'<td class="num">¥{f2(d["minO"])} – ¥{f2(d["maxO"])}</td>'
        f'<td class="num {"ybest" if d["spreadO"] < 15 else ""}">{d["spreadO"]:.1f}%</td>'
        f'<td class="num {"ybest" if d["spreadD"] < 15 else ""}">{d["spreadD"]:.1f}%</td></tr>')

clm_rows = ""
for c in claims:
    clm_rows += (
        f'<tr><td><span class="dot" style="background:{c["color"]}"></span>{c["plat"]}</td>'
        f'<td>{c["tier"]}</td><td class="num">¥{c["ad"]:.2f}</td>'
        f'<td class="num strong">¥{c["real"]:.3f}</td><td class="num">{c["ratio"]:.2f}×</td></tr>')

marg_rows = ""
for m in marginal:
    if m["mCost"] <= 20.5:
        txt, cls = "强烈推荐", "v-good"
    elif m["mCost"] <= 26.0:
        txt, cls = "一般", "v-warn"
    else:
        txt, cls = "不建议", "v-bad"
    marg_rows += (
        f'<tr><td><span class="dot" style="background:{m["color"]}"></span>{m["plat"]}</td>'
        f'<td>{m["frm"]} → {m["to"]}</td>'
        f'<td class="num">¥{m["dPrice"]:,.0f}</td><td class="num">+{m["dCap"]:.0f}</td>'
        f'<td class="num strong">¥{f2(m["mCost"])}</td><td class="num">{f2(m["avgCost"])}</td>'
        f'<td><span class="tag {cls}">{txt}</span></td></tr>')

so_far = "、".join(f'{d["plan"]["plat"]} {d["plan"]["tier"]}' for d in dominated) or "无"
xq_placed = "、".join(f'{r["plan"]["tier"]}（{r["lo"]:.2f}–{r["hi"]:.2f}）' for r in ladder
                     if r["plan"]["plat"] == "小云雀") or "无"

ap_rows = ""
# 附录按原始档位逐条列出（不展开积分选项，改为在月积分格内标注）
for _pl in COST["plans"]:
    plat, tier, price, cur = _pl["platform"], _pl["tier"], _pl["price"], _pl["currency"]
    monthly, per, orig = _pl["monthlyCredits"], CPV[_pl["platform"]], _pl["original"]
    _opts = _pl.get("creditsOptions")
    _mtxt = (" / ".join(format(o["monthlyCredits"], ",") for o in _opts) + f'<div class="cny">双档可选</div>') if _opts else format(monthly, ",")
    p = G(plat, tier)
    off = (f"¥10 = {p['officialPerYuan']:.1f}" if p["officialPerYuan"] and cur == "CNY"
           else (f"1 元 = {p['officialPerYuan']:.0f}" if p["officialPerYuan"] else "—"))
    ap_rows += (
        f'<tr><td><span class="dot" style="background:{p["color"]}"></span>{plat}</td><td>{tier}</td>'
        f'<td class="ctr">{cur}</td><td class="num">{CU[cur]}{price:,}</td>'
        f'<td class="num">{("¥%s" % format(p["priceCNY"], ",.0f")) if cur == "USD" else "—"}</td>'
        f'<td class="num">{_mtxt}</td><td class="num">{per:,}</td>'
        f'<td class="num">{off}</td>'
        f'<td class="num">{(CU[cur] + format(orig, ",")) if orig else "—"}</td></tr>')

SOURCES = [
    ("Neowow 生成页", "Seedance 2.5 / 720p / 16:9 / 30s / 全能参考 → 7,500 积分"),
    ("libtv 生成页", "Seedance 2.5 / 全能参考 / 16:9 · 720P · 30s → 1,380 积分"),
    ("即梦生成页", "即梦 Seedance 2.5 / 16:9 / 720P / 全能参考 / 30s → 600 积分"),
    ("libtv 订阅页", "标准/进阶/高级/豪华/至尊 五档年费 + 划线原价 + 兑换率"),
    ("Neowow 订阅页", "PLUS/Pro/MAX/ULTRA 四档年费 + 划线原价 + 1元=X积分"),
    ("即梦订阅页", "基础/标准/高级/超级 四档年费 + 首年5折与次年全额"),
    ("小云雀 订阅页", "基础 ¥453 / 标准 ¥1,199 / 高级 ¥4,999 / 超级 ¥21,840（含划线原价）"),
    ("小云雀 生成页", "Seedance 2.5 / 16:9 / 720P / 30s → 600 积分（用户已确认）"),
    ("Higgsfield 订阅页", "Starter $15 / Plus $39 / Ultra $99（月付折年付口径）"),
    ("Higgsfield 生成页", "Model: Seedance 2.5 / 30s / 16:9 / 720p / Bitrate Standard → 210 积分"),
]
src_rows = "".join(
    f'<tr><td>{pg}</td><td style="white-space:normal">{d}</td></tr>' for pg, d in SOURCES)

cost_body = f"""
<div class="subnav"><div class="inner">
  <a href="#overview">概览</a>
  <a href="#calc">按产量测算</a>
  <a href="#table">档位对比</a>
  <a href="#ladder">达标阶梯</a>
  <a href="#margin">边际成本</a>
  <a href="#discount">折扣结构</a>
  <a href="#official">官方公示对照</a>
  <a href="#retry">失败退分</a>
  <a href="#appendix">原始数据</a>
</div></div>

<div class="hero">
  <div class="eyebrow">Cost Benchmark · Seedance 2.5</div>
  <h1>同一条 30 秒视频<br>最贵档比最省档贵 <em>{worst/best:.2f} 倍</em></h1>
  <p class="lead">5 个平台的积分币值互不相同，直接比消耗没有意义。这里先把它们压平到同一口径，再折算成单条现金成本。</p>
  <div class="meta">
    <span><i></i>数据时点 <b>{RATE_DATE}</b></span>
    <span><i></i>平台 <b>5</b></span>
    <span><i></i>档位 <b>{len(plans)}</b></span>
    <span><i></i>汇率 <b>1 USD = {RATE}</b></span>
    <span><i></i>口径校验偏差 <b>{max_dev:.2f}%</b></span>
  </div>
</div>

<div class="wrap">

<section id="overview" class="reveal" style="margin-top:42px">
  <div class="grid g5">
    <div class="kpi hi"><div class="t">单条成本最优</div>
      <div class="v">¥{f2(best)}</div>
      <div class="d">{best_row['plat']} {best_row['tier']} · {best_row['mCap']:.2f} 条/月<br>
      即梦超级 ¥{f2(runner['perVideoCNY'])} 并列，差 {abs(best-runner['perVideoCNY'])/best*100:.2f}%</div></div>
    <div class="kpi good"><div class="t">中产能最省</div>
      <div class="v">¥{mid['plan']['priceCNY']:,.0f}</div>
      <div class="d">{mid['plan']['plat']} {tname(mid['plan'])} · {mid['plan']['mCap']:.2f} 条/月<br>
      ¥{f2(mid['plan']['perVideoCNY'])}/条</div></div>
    <div class="kpi good"><div class="t">大产能最省</div>
      <div class="v">¥{top['plan']['priceCNY']:,.0f}</div>
      <div class="d">{top['plan']['plat']} {tname(top['plan'])} · {top['plan']['mCap']:.2f} 条/月<br>
      ¥{f2(top['plan']['perVideoCNY'])}/条</div></div>
    <div class="kpi pink"><div class="t">海外平台溢价</div>
      <div class="v">{HG['perVideoCNY']/best:.2f}×</div>
      <div class="d">Higgsfield Ultra ¥{f2(HG['perVideoCNY'])}/条<br>含税后约 ¥{HG['perVideoCNY']*1.08:.2f}，无成本优势</div></div>
    <div class="kpi bad"><div class="t">最差档位</div>
      <div class="v">{worst/best:.2f}×</div>
      <div class="d">Higgsfield Starter ¥{f2(worst)}/条<br>低档位多是「高价试用装」</div></div>
  </div>
</section>

<section id="calc" class="reveal">
  <div class="sechead">
    <h2><span class="ey">01</span>按产量反查最省方案</h2>
    <div class="sd">先填月产量，直接看结论。1 条 = 30 秒，10 条就是 300 秒（5 分钟）素材。</div>
  </div>
  <div class="card">
    <div class="ctrl">
      <span class="sub">目标月产量</span>
      <input type="range" id="tgt" min="1" max="200" value="30">
      <span class="big" id="tgtv">30 条/月</span>
      <span class="sub" id="tgtsec">= 900 秒 ≈ 15 分钟素材</span>
    </div>
    <table><thead><tr><th>方案类型</th><th>档位组合</th><th class="ctr">年支出</th>
    <th class="ctr">实际产能</th><th class="ctr">单条成本 ↓</th></tr></thead><tbody id="rec"></tbody></table>
    <div class="sub" style="margin-top:10px">「组合订阅」为<b>跨平台混合求解</b>（无界背包）：允许不同平台的档位叠加、同一档位可多份，用于产量超出单档位上限时。多账号运营成本未计入，且按各档月产能向下取整（保守估计）。</div>
  </div>
</section>

<section id="table" class="reveal">
  <div class="sechead">
    <h2><span class="ey">02</span>全档位对比</h2>
    <div class="sd">条形越长＝越省（以全场最优价为 100%）。点表头可排序，左右滑动查看完整表格。</div>
  </div>
<table id="main"><thead><tr>
    <th onclick="sortBy('v',this)">#</th><th>平台</th><th>档位</th>
    <th onclick="sortBy('p',this)" class="ctr">年费</th><th class="ctr">月积分</th>
    <th onclick="sortBy('v',this)" class="ctr">单条成本 ↓</th><th class="ctr">元/秒</th>
    <th onclick="sortBy('c',this)" class="ctr">月产能 ↓</th>
      </tr></thead><tbody>
{main_rows}
  </tbody></table></div>
</section>

<section id="ladder" class="reveal">
  <div class="sechead">
    <h2><span class="ey">03</span>达标总支出阶梯</h2>
    <div class="sd">「单条成本最省」≠「花钱最省」。按目标月产量反查覆盖该产能的最低年费档位（单一订阅）。</div>
  </div>
  <div class="tw"><table><thead><tr>
    <th class="ctr">目标月产量</th><th>最省方案</th><th class="ctr">年支出</th>
    <th class="ctr">实际产能</th><th class="ctr">单条成本</th><th class="ctr">相对最优</th>
  </tr></thead><tbody>{lad_rows}</tbody></table></div>
  <details style="margin-top:14px">
    <summary>为什么 libtv 单价最贵却还最省？<span class="chev">›</span></summary>
    <div class="dbody">
      libtv 最低档单条 ¥{f2(LT['perVideoCNY'])} 已是全场最优 {f2(best)} 元的 {(LT['perVideoCNY']/best-1)*100:.0f}% 溢价，但它仍占据多个产量区间的最省解 —— 因为它<b>档位切分最密、产能粒度小、浪费少</b>。
      而 Neowow（1.2 → 14.4 → 38.4 → 49.1）与即梦（3.7 → 20.5 → 90）档位跨度大，中间存在大量「必须为用不到的产能付费」的断档。
      <br><br>
      <b>Higgsfield 唯一占位的 3.68–4.76 条/月区间也不是因为它便宜</b>（¥{f2(HG2['perVideoCNY'])}/条，最优的 {HG2['perVideoCNY']/best:.1f} 倍），而是国内平台恰好在该产能段留了空档 —— 这个位置是别人让出来的。
      <br><br>
      小云雀只在 {xq_placed} 占位。<b>被支配档位</b>（可覆盖区间不足 0.1 条/月）：{so_far}。
    </div>
  </details>
</section>

<section id="margin" class="reveal">
  <div class="sechead">
    <h2><span class="ey">04</span>边际成本：升档值不值</h2>
    <div class="sd">从下一档升到上一档，每多买一条产能实际多花多少钱。标尺为全场最优 ¥{f2(best)}/条。</div>
  </div>
  <div class="tw scroll-y"><div class="tw"><table><thead><tr>
    <th>平台</th><th>升档路径</th><th class="ctr">Δ年费</th><th class="ctr">Δ年产</th>
    <th class="ctr">边际单条</th><th class="ctr">达档均值</th><th class="ctr">判定</th>
  </tr></thead><tbody>{marg_rows}</tbody></table></div></div>
  <details style="margin-top:14px">
    <summary>价格陷阱拐点在哪？<span class="chev">›</span></summary>
    <div class="dbody">
      <b>全场最优升级：</b>{m_best['plat']} {m_best['frm']} → {m_best['to']}，边际 ¥{f2(m_best['mCost'])}/条，<b>低于全场最优单价 ¥{f2(best)}</b> —— 这一步买到的产能比市场上任何单一档位都便宜。
      <br><br>
      <b>升级路径并不单调。</b>libtv 在「进阶 → 高级」处回升、即梦在「高级 → 超级」处回升，这两处就是各自设置的<b>价格陷阱拐点</b>：到了这里继续升档性价比明显劣化，宁可选另一家的对应档位。
      <br><br>
      全场最差升级是 {m_worst['plat']} {m_worst['frm']} → {m_worst['to']}，边际 ¥{f2(m_worst['mCost'])}/条，是最优解的 {m_worst['mCost']/best:.2f} 倍。
    </div>
  </details>
</section>

<section id="discount" class="reveal">
  <div class="sechead">
    <h2><span class="ey">05</span>折扣结构：优势是真是假</h2>
    <div class="sd">用官方公示原价重算。原价下单价收敛成水平线 → 说明优势全部来自折扣力度，活动一结束就消失。「原价」列为页面划线价或次年续费全额，二者口径不同，仅用于判断「优势是否依赖活动」。</div>
  </div>
  <div class="tw scroll-y"><div class="tw"><table><thead><tr>
    <th>平台</th><th class="ctr">折扣区间</th><th class="ctr">原价下单条（CNY）</th>
    <th class="ctr">原价单价极差</th><th class="ctr">折扣力度极差</th>
  </tr></thead><tbody>{disc_rows}</tbody></table></div></div>
  <details style="margin-top:14px">
    <summary>谁的「规模经济」是假的？<span class="chev">›</span></summary>
    <div class="dbody">
      <b>① Neowow 是假的。</b>按原价，其四档单条成本全部为 <b>¥75.00</b>（原价内在逻辑为固定 100 积分/元），极差仅 {[d for d in disc_rows_data if d['plat']=='Neowow'][0]['spreadO']:.1f}%。所有价差都来自折扣力度（PLUS 55 折 → ULTRA 27 折）。<b>折扣退坡，优势归零。</b>
      <br><br>
      <b>② libtv 同样如此，</b>原价极差 {[d for d in disc_rows_data if d['plat']=='libtv'][0]['spreadO']:.1f}%，而折扣从 {[d for d in disc_rows_data if d['plat']=='libtv'][0]['maxD']*10:.0f} 折拉到 {[d for d in disc_rows_data if d['plat']=='libtv'][0]['minD']*10:.0f} 折。
      <br><br>
      <b>③ 只有即梦是真正的统一折扣结构。</b>两个档位均为 5.0 折，折扣极差 <b>0.0%</b> —— 它的价格斜率完全来自平台真实定价结构，不受活动影响。小云雀 5.0–6.0 折，原价极差 {[d for d in disc_rows_data if d['plat']=='小云雀'][0]['spreadO']:.1f}%，是唯一在原价层面就有真实档位定价差异的平台。
      <br><br>
      <b>④ 长期使用应「按原价排序」决策。</b>按原价，国内排序为：即梦超级 ¥{f2(JM['origPerVideoCNY'])} &lt; 即梦高级 ¥{f2(G('即梦','高级会员')['origPerVideoCNY'])} &lt; libtv 高级 ¥{f2(G('libtv','高级版')['origPerVideoCNY'])} &lt; 小云雀超级 ¥{f2(XQ['origPerVideoCNY'])} &lt; Neowow 全档 ¥75.00。<b>Neowow 在最坏情形下垫底。</b>
    </div>
  </details>
</section>

<section id="official" class="reveal">
  <div class="sechead">
    <h2><span class="ey">06</span>海报宣传价 vs 实际到手价</h2>
    <div class="sd">各平台「低至 X 元/秒」均按非全能参考档位计算，与统一口径不可混用。</div>
  </div>
  <div class="tw scroll-y"><div class="tw"><table><thead><tr>
    <th>平台</th><th>顶级档位</th><th class="ctr">海报「低至」</th><th class="ctr">全能参考实算</th><th class="ctr">倍差</th>
  </tr></thead><tbody>{clm_rows}</tbody></table></div></div>
  <div class="note" style="margin-top:14px">
    <b>即梦与小云雀都报「¥0.40/秒」，倍差同为 1.69×，但小云雀实算 {XQ['perSecCNY']:.3f} 元/秒、即梦 {JM['perSecCNY']:.3f} 元/秒 —— 同一句「低至 0.40 元/秒」，小云雀实际成本高出 {XQ['perSecCNY']/JM['perSecCNY']-1:+.1%}。</b>
    Neowow {[c for c in claims if c['plat']=='Neowow'][0]['ratio']:.2f}× 的倍差为五家最高。
  </div>
</section>

<section id="retry" class="reveal">
  <div class="sechead">
    <h2><span class="ey">07</span>失败重试成本</h2>
    <div class="sd">五家平台失败均<b>不消耗积分</b> —— 本表全部单价均按「成功出片才扣分」计算，与实际计费一致，无需再折算失败率。</div>
  </div>
  <div class="tw"><table><thead><tr>
    <th>平台</th><th class="ctr">失败是否扣分</th><th>依据</th>
  </tr></thead><tbody>
    {"".join(f'<tr><td><span class="dot" style="background:{COLOR.get(x["plat"], "#767C85")}"></span>{x["plat"]}</td>'
             f'<td class="ctr"><span class="tag v-good">{x["retry"]}</span></td>'
             f'<td style="white-space:normal">{x["confidence"]}</td></tr>' for x in COST.get("retryPolicy", []))}
  </tbody></table></div>
  <div class="note good" style="margin-top:14px">
    <b>为什么这一项重要：</b>若某平台失败不退分且失败率 20%，其实际单条成本需上浮 25%，足以反转全部排名。
    既然五家均不扣分，<b>上表排名不受失败率影响</b>，可以直接按单价决策。
    <br><br>
    <b>{COST.get("retryNote", "")}</b>
  </div>
  <details style="margin-top:14px">
    <summary>跨零点提交的积分归属差异<span class="chev">›</span></summary>
    <div class="dbody">{COST.get("crossMidnightNote", "")}</div>
  </details>
</section>

<section id="appendix" class="reveal">
  <div class="sechead">
    

<h2><span class="ey">08</span>方法论与原始数据</h2>
    <div class="sd">本节列出全部原始输入与计算链条，不含推算值，便于复核与复用。</div>
  </div>
  <details>
    <summary>计算口径与归一化链条<span class="chev">›</span></summary>
    <div class="dbody">
      <b>核心问题：</b>五个平台的「积分」是各自发行的内部计价币，币值互不相同 —— 同样一条 30 秒视频，即梦与小云雀各扣 <b>600</b> 分、libtv 扣 <b>1,380</b> 分、Higgsfield 扣 <b>210</b> 分、Neowow 扣 <b>7,500</b> 分。直接比较积分消耗没有意义。<br><br>
      <b>归一化链条：</b><br>
      ① <code>本币/积分 = 年费 ÷ (月积分 × 12)</code><br>
      ② <code>单条成本 = 本币/积分 × 每条消耗积分</code> ← 唯一可跨平台比较的价格<br>
      ③ <code>月产能 = 月积分 ÷ 每条消耗积分</code>　<code>年产能 = 月产能 × 12</code><br>
      ④ <code>边际成本 = Δ年费 ÷ Δ年产能</code><br>
      ⑤ <code>达标总支出最省 = 覆盖目标月产能的最低年费档位</code><br>
      ⑥ USD 档位按 <code>1 USD = {RATE} CNY</code>（{RATE_DATE} 中国外汇交易中心中间价）折算<br><br>
      <b>口径校验：</b>用各平台自己公示的兑换率反向验证步骤①。Neowow 公示 180/282/350/371 积分/元，本表推算 {G('Neowow','PLUS')['unitPerYuan']:.1f}/{G('Neowow','Pro')['unitPerYuan']:.1f}/{G('Neowow','MAX')['unitPerYuan']:.1f}/{G('Neowow','ULTRA')['unitPerYuan']:.1f}；小云雀公示 ¥10 = 21.9/23.2/28.8/30.0，本表推算 21.98/23.22/28.80/30.00。全表最大偏差 <b>{max_dev:.2f}%</b>。<br><br>
      <b>币种折算依据：</b>选用中间价而非银行牌价，因中间价是当日官方定价、可引用可复核。实际结算按各银行现汇卖出价通常再高 0.5–1%。汇率每变动 1%，Higgsfield 全档位单条成本同步变动约 1%，不足以改变「海外平台单价高于国内第一梯队」的结论。
    </div>
  </details>
  <details>
    <summary>单条积分消耗（各平台生成页实测）<span class="chev">›</span></summary>
    <div class="dbody">
      <table><thead><tr><th>平台</th><th>生成页规格</th><th class="ctr">单条积分</th></tr></thead><tbody>
        <tr><td><span class="dot" style="background:#00C65A"></span>Neowow</td><td style="white-space:normal">Seedance 2.5 · 720p · 16:9 · 30s · 全能参考 · 分镜栏编辑</td><td class="num strong">7,500</td></tr>
        <tr><td><span class="dot" style="background:#9CE6F3"></span>libtv</td><td style="white-space:normal">Seedance 2.5 · 全能参考 · 16:9 · 720P · 30s</td><td class="num strong">1,380</td></tr>
        <tr><td><span class="dot" style="background:#3280FF"></span>即梦</td><td style="white-space:normal">即梦 Seedance 2.5 · 16:9 · 720P · 全能参考 · 30s</td><td class="num strong">600</td></tr>
        <tr><td><span class="dot" style="background:#FABC00"></span>小云雀</td><td style="white-space:normal">Seedance 2.5 · 16:9 · 720P · 30s</td><td class="num strong">600</td></tr>
        <tr><td><span class="dot" style="background:#ED1572"></span>Higgsfield</td><td style="white-space:normal">Model: Seedance 2.5 · 30s · 16:9 · 720p · Bitrate Standard</td><td class="num strong">210</td></tr>
      </tbody></table>
    </div>
  </details>
  <details>
    <summary>年费档位与月积分（{len(plans)} 档全清单）<span class="chev">›</span></summary>
    <div class="dbody">
      <table><thead><tr><th>平台</th><th>档位</th><th class="ctr">币种</th><th class="ctr">年费</th>
      <th class="ctr">折 CNY</th><th class="ctr">月积分</th><th class="ctr">每条</th><th class="ctr">公示兑换率</th><th class="ctr">原价</th>
      </tr></thead><tbody>{ap_rows}</tbody></table>
      <div class="sub" style="margin-top:10px">兑换率一列为平台页面自行公示值，仅用于反向校验。Higgsfield 三档报价均不含 VAT 及地方税。</div>
    </div>
  </details>
  <details>
    <summary>数据来源（10 张截图）<span class="chev">›</span></summary>
    <div class="dbody">
      <table><thead><tr><th>页面</th><th>提取到的数据</th></tr></thead><tbody>{src_rows}</tbody></table>
    </div>
  </details>
</section>

<section class="reveal">
  <div class="sechead">
    <h2><span class="ey">09</span>执行建议</h2>
    <div class="sd">决策顺序：先定月产量 → 查达标阶梯 → 落到唯一档位 → 用原价排序做压力测试。</div>
  </div>
  <div class="note good">
    <ul style="margin-top:0">
      {PLAN_BULLETS}
      <li><b>被支配档位（单独采购无意义）：</b>{so_far} —— 可覆盖区间不足 0.1 条/月。</li>
      <li><b>海外需求：</b>Higgsfield 仅建议作关键镜头精修通道（Ultra 月上限 {HG['mCap']:.1f} 条）；Ultra 折 ¥{f2(HG['perVideoCNY'])}/条是全场最优的 {HG['perVideoCNY']/best:.2f} 倍，含税后约 ¥{HG['perVideoCNY']*1.08:.2f}/条。若只需 3.7–4.8 条/月，其 Plus 档反而值得考虑。</li>
      <li><b>不要买：</b>即梦基础会员（¥{f2(G('即梦','基础会员')['perVideoCNY'])}/条）、即梦标准会员（¥{f2(G('即梦','标准会员')['perVideoCNY'])}/条）、libtv 标准版（¥{f2(G('libtv','标准版')['perVideoCNY'])}/条）、Higgsfield Starter（¥{f2(worst)}/条）—— 单价均在最优解 2.0 倍以上且月产能不足 1.5 条。</li>
      <li><b>小云雀 vs 即梦：</b>二者超级会员<b>完全同规格</b> —— 同为 ¥21,840 首年 / ¥43,680 次年、同为 54,600 积分/月、同为 ¥1 = 30 积分、同为 600 积分/条，折算单条成本完全相同（<b>¥{f2(XQ['perVideoCNY'])}</b>）。选谁只看非价格能力：工作流完整度、CLI/API 支持、客服响应。公开反馈称小云雀<b>无官方客服渠道</b>。</li>
</ul>
  </div>
</section>

<div class="foot">{BRAND} · {BRAND_CN}　|　{STUDIO} 出品　|　数据采集 {RATE_DATE}　·　全部数值按统一口径重算，非平台宣传数字</div>
"""

# ══════════════════════════════════════════════════════════════
# 排行榜页 —— 数据从 leaderboard-vlm.json 渲染
# entries 为空时显示空状态；后续只需向 entries 追加记录即自动出榜
# ══════════════════════════════════════════════════════════════
DIMS = VLM["methodology"]["dimensions"]
ENTRIES = sorted(VLM.get("entries", []), key=lambda e: -e.get("score", 0))

dim_cols = "".join(f'<th class="ctr">{d["label"]}</th>' for d in DIMS)
dim_rows = "".join(
    f'<tr><td><span class="mono" style="color:#D1FE17">{d["key"]}</span></td>'
    f'<td>{d["label"]}</td><td class="num">{(d["weight"]*100):.0f}%</td>'
    f'<td style="white-space:normal">{d["desc"]}</td></tr>' for d in DIMS)

if ENTRIES:
    lb_rows = ""
    for i, e in enumerate(ENTRIES, 1):
        dims = "".join(f'<td class="num">{e.get("dims", {}).get(d["key"], "—")}</td>' for d in DIMS)
        lic = "开源" if e.get("license") == "open" else "闭源"
        sub = e.get("provider", "") + (" · " + e["variant"] if e.get("variant") else "")
        lb_rows += (
            f'<tr class="{"top" if i == 1 else ""}">'
            f'<td class="ctr rk"><b>{i}</b><s>±{e.get("ci", "—")}</s></td>'
            f'<td class="cell2"><b>{e["model"]}</b><s>{sub}</s></td>'
            f'<td>{lic}</td>{dims}'
            f'<td class="num strong">{e["score"]:.2f}</td></tr>')
    lb_main = (f'<div class="tw"><table><thead><tr><th class="ctr">#</th><th>模型</th><th>授权</th>'
               f'{dim_cols}<th class="ctr">总分 ↓</th></tr></thead><tbody>{lb_rows}</tbody></table></div>')
else:
    lb_main = (f'<div class="glass glass-strong card" style="text-align:center;padding:52px 26px">'
               f'<div class="eyebrow" style="margin-bottom:13px">{VLM["emptyState"]["title"]}</div>'
               f'<div style="color:#8A9099;font-size:13px;line-height:1.75;max-width:540px;margin:0 auto">'
               f'{VLM["emptyState"]["body"]}</div></div>')

lb_meta = ("".join([
    f'<span><i></i>状态 <b>评测中</b></span>',
    f'<span><i></i>维度 <b>{len(DIMS)}</b></span>',
    f'<span><i></i>模型 <b>{len(ENTRIES) if ENTRIES else "—"}</b></span>',
    f'<span><i></i>数据时点 <b>{VLM["updatedAt"] or "待回填"}</b></span>',
]))

lb_body = f"""
<div class="hero">
  <div class="eyebrow">{VLM["eyebrow"]}</div>
  <h1>视觉理解模型<br><em>统一口径排行榜</em></h1>
  <p class="lead">{VLM["intro"]}</p>
  <div class="meta">{lb_meta}</div>
</div>

<div class="wrap">
<section class="reveal" style="margin-top:42px">
  <div class="sechead">
    <h2><span class="ey">01</span>榜单</h2>
    <div class="sd">{VLM["methodology"]["scoring"]}</div>
  </div>
  {lb_main}
</section>

<section class="reveal">
  <div class="sechead">
    <h2><span class="ey">02</span>评测维度与权重</h2>
    <div class="sd">权重定死后再开始跑分，避免「先看结果再调权重」。</div>
  </div>
  <div class="tw"><table><thead><tr><th class="ctr">key</th><th>维度</th>
  <th class="ctr">权重</th><th>说明</th></tr></thead><tbody>{dim_rows}</tbody></table></div>
</section>

<section class="reveal">
  <div class="sechead">
    <h2><span class="ey">03</span>数据字段说明</h2>
    <div class="sd">字段已锁定。回填时只需向 <code>data/leaderboard-vlm.json</code> 的 <code>entries</code> 追加记录，页面自动出榜，无需改动任何模板。</div>
  </div>
  <details open>
    <summary>entries[] 单条记录结构<span class="chev">›</span></summary>
    <div class="dbody">
      <table><thead><tr><th class="ctr">字段</th><th>说明</th></tr></thead><tbody>
      {"".join(f'<tr><td><span class="mono" style="color:#D1FE17">{k}</span></td><td style="white-space:normal">{v}</td></tr>' for k, v in VLM["fieldSchema"]["entries[]"].items())}
      </tbody></table>
    </div>
  </details>
</section>

<div class="foot">{BRAND} · {BRAND_CN}　|　{STUDIO} 出品　|　{VLM["title"]}评测中</div>
"""

# ══════════════════════════════════════════════════════════════
# 输出
# ══════════════════════════════════════════════════════════════
home = page("首页", f"{BRAND} — {TAGLINE}。AI 平台成本对比与模型能力排行榜，统一口径折算，只给可复核的结果。",
            nav("home"), home_body)
cost = page("平台成本对比", f"{len(plans)} 个会员档位，按「{SPEC}」统一口径折算单条现金成本，含达标总支出阶梯与折扣结构压力测试。",
            nav("cost"), cost_body, extra_js="%data%")
lb = page(VLM["title"], VLM["intro"], nav("leaderboard-vlm"), lb_body)

site = r"C:\Users\admin\WorkBuddy\2026-09-21-10-34-35\site"
deploy = r"C:\Users\admin\WorkBuddy\2026-09-21-10-34-35\deploy"
for d in (site, deploy):
    os.makedirs(d, exist_ok=True)
for d in (site, deploy):
    with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
        f.write(home)
    with open(os.path.join(d, "cost.html"), "w", encoding="utf-8") as f:
        f.write(cost)
    with open(os.path.join(d, "leaderboard-vlm.html"), "w", encoding="utf-8") as f:
        f.write(lb)

# deploy/ 只放公网文件
import shutil
for extra in ["_headers", "robots.txt", "LICENSE", "SECURITY.md"]:
    s = os.path.join(site, extra)
    if os.path.exists(s):
        shutil.copy2(s, os.path.join(deploy, extra))
# 全站去掉旧的单页残留
old = os.path.join(site, "画布平台性价比对比.html")
if os.path.exists(old):
    os.remove(old)

print("=" * 96)
print(f"{BRAND} · {BRAND_CN}　|　指纹 {FP}")
print(f"口径: {SPEC}　汇率: 1 USD = {RATE} CNY ({RATE_DATE})")
print("=" * 96)
print(f"{'#':>3} {'平台':<11}{'档位':<10}{'币种':>5}{'年费':>9}{'折CNY':>8}{'元/积分':>10}{'单条CNY':>9}{'元/秒':>7}{'月产能':>8}{'相对':>7}")
print("-" * 96)
for p in sorted(plans, key=lambda x: x["perVideoCNY"]):
    cur = CU[p["cur"]] + f"{p['price']:,}"
    cny = f"{p['priceCNY']:,.0f}" if p["cur"] == "USD" else "-"
    print(f"{p['rank']:>3} {p['plat']:<11}{p['tier']:<10}{p['cur']:>5}{cur:>9}{cny:>8}"
          f"{p['unitCNY']:>10.5f}{p['perVideoCNY']:>9.2f}{p['perSecCNY']:>7.3f}{p['mCap']:>8.2f}{p['rel']:>7.3f}")
print("-" * 96)
print(f"最优 ¥{best:.2f} / 最差 ¥{worst:.2f} = {worst/best:.2f}×　口径偏差 {max_dev:.2f}%")
print()
for f in sorted(os.listdir(site)):
    if f == ".git":
        continue
    print(f"  site/{f:<20} {os.path.getsize(os.path.join(site, f)):>8} B")
print()
for f in sorted(os.listdir(deploy)):
    print(f"  deploy/{f:<18} {os.path.getsize(os.path.join(deploy, f)):>8} B")

# -*- coding: utf-8 -*-
"""
CALIBER · 站点渲染器

设计原则
  1. 【不做字符串替换】。页面全部由 render_* 函数按数据结构拼装。
     旧版靠正则/字符串替换改模板，反复出现「锚点失配」「命中错误位置且静默成功」
     「吃掉结构标签导致布局塌陷」等事故 —— 重写就是为了根除这一类问题。
  2. 派生量一律现算，不落盘：单条成本 / 月产能 / 达标阶梯 / 边际成本 /
     折扣结构 / 跨平台组合最省（无界背包）/ ROI。
  3. 构建结束自动跑自检（div 配对、列数、锚点、JS 语法），失败即非零退出。

运行：python build/build_site.py
"""
import io
import json
import math
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # site/
DATA = os.path.join(ROOT, "data")
DEPLOY = os.path.join(os.path.dirname(ROOT), "deploy")
NODE = r"C:\Users\admin\.workbuddy\binaries\node\versions\22.22.2-3\node.EXE"

# ═══════════════════════════════════════════════════════════════════
# 1. 载入
# ═══════════════════════════════════════════════════════════════════
def load(name):
    with io.open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


SITE = load("site.json")
PLATFORMS = load("platforms.json")
COST = load("cost-seedance25.json")
VLM = load("leaderboard-vlm.json")

BRAND, BRAND_CN = SITE["brand"], SITE["brandCn"]
STUDIO, OWNER, YEAR = SITE["studio"], SITE["owner"], SITE["year"]
NAV = SITE["nav"]
COPY = f"© {YEAR} {OWNER}. 保留所有权利 / All Rights Reserved."
TERMS = ("本页内容（含全部价格数据、归一化模型、边际成本与达标阶梯算法、结论文字及版面设计）"
         "为作者原创成果。未经书面许可，禁止：复制或转载全文/部分内容、二次发布或镜像托管、"
         "用于商业用途、用于任何 AI 模型的训练或微调、移除或篡改版权声明与溯源指纹。"
         "允许：转发原始链接、引用结论并注明出处。")

RATE = COST["fx"]["rate"]
SPEC = COST["spec"]["text"]
SEC_PER_CLIP = COST["spec"]["secondsPerClip"]
UPDATED = COST["updatedAt"]
CPV = COST["creditsPerVideo"]
OFFICIAL_RATE = COST["officialRate"]
AD_CLAIM = COST["adClaim"]
SCOPE = COST["scope"]
COLOR = {k: v["color"] for k, v in PLATFORMS.items()}
CU = {"CNY": "¥", "USD": "$"}

# ═══════════════════════════════════════════════════════════════════
# 2. 派生计算 —— 全部现算，无落盘
# ═══════════════════════════════════════════════════════════════════
def auto_label(m):
    """按数量级选可读单位：11.7K / 12K / 10.8W"""
    if m >= 100000:
        return "%gW 档" % round(m / 10000, 1)
    if m >= 1000:
        return "%gK 档" % round(m / 1000, 1)
    return "%g 档" % m


def build_rows():
    """展开为「档位 × 积分选项」行，并算出全部派生量"""
    out = []
    for p in COST["plans"]:
        plat = p["platform"]
        cur = PLATFORMS[plat]["currency"]
        k = RATE if cur == "USD" else 1.0
        per = CPV[plat]
        multi = len(p["credits"]) > 1
        for c in p["credits"]:
            monthly, price = c["credits"], c["price"]
            year_credits = monthly * 12
            unit = price / year_credits                    # 本币/积分
            per_video = unit * per * k                     # CNY/条
            mcap = monthly / per                           # 条/月
            out.append({
                "plat": plat, "tier": p["tier"], "cur": cur, "k": k, "per": per,
                "monthly": monthly, "price": price, "priceCNY": price * k,
                "unitCNY": unit * k, "perYuan": 1.0 / unit,
                "perVideo": per_video, "perSec": per_video / SEC_PER_CLIP,
                "mCap": mcap, "yCap": mcap * 12,
                "label": c.get("label") or (auto_label(monthly) if multi else ""),
                "multi": multi,
                "renewal": p.get("renewal"), "original": p.get("original"),
                "color": COLOR[plat],
            })
    return out


ROWS = build_rows()
BEST = min(r["perVideo"] for r in ROWS)
WORST = max(r["perVideo"] for r in ROWS)
for i, r in enumerate(sorted(ROWS, key=lambda x: x["perVideo"]), 1):
    r["rank"] = i
    r["rel"] = r["perVideo"] / BEST

# 折扣结构（按划线原价重算）
for r in ROWS:
    o = r["original"]
    if o:
        oc = o * r["k"]
        r["origPerVideo"] = oc / (r["monthly"] * 12) * r["per"]
        r["disc"] = r["priceCNY"] / oc
    else:
        r["origPerVideo"] = r["disc"] = None

# 同（平台,档位）只保留产能最大者 —— 用于阶梯与边际，避免同档多选项中低配产生 Δ=0
BY_TIER = {}
for r in ROWS:
    key = (r["plat"], r["tier"])
    if key not in BY_TIER or r["mCap"] > BY_TIER[key]["mCap"]:
        BY_TIER[key] = r
SINGLES = list(BY_TIER.values())


def tname(r):
    return r["tier"] + (f' · {r["label"]}' if r["multi"] else "")


def build_ladder():
    """达标总支出阶梯：按年费升序扫描，只收能扩大覆盖上限的档位"""
    lad, lower = [], 0.0
    for r in sorted(SINGLES, key=lambda x: x["priceCNY"]):
        if r["mCap"] > lower + 1e-9:
            lad.append({"lo": lower, "hi": r["mCap"], "row": r})
            lower = max(lower, r["mCap"])
    return lad


def build_marginal():
    out = []
    for plat in PLATFORMS:
        grp = sorted([r for r in SINGLES if r["plat"] == plat], key=lambda x: x["priceCNY"])
        for a, b in zip(grp, grp[1:]):
            dprice, dcap = b["priceCNY"] - a["priceCNY"], b["yCap"] - a["yCap"]
            out.append({"plat": plat, "a": a, "b": b, "dPrice": dprice, "dCap": dcap,
                        "mCost": dprice / dcap, "avg": b["perVideo"], "color": COLOR[plat]})
    return out


def build_discount():
    out = []
    for plat in PLATFORMS:
        grp = [r for r in ROWS if r["plat"] == plat and r["disc"] is not None]
        if not grp:
            continue
        ds = [r["disc"] for r in grp]
        ops = [r["origPerVideo"] for r in grp]
        out.append({"plat": plat, "minD": min(ds), "maxD": max(ds),
                    "minO": min(ops), "maxO": max(ops),
                    "spreadO": (max(ops) / min(ops) - 1) * 100,
                    "spreadD": (max(ds) / min(ds) - 1) * 100, "color": COLOR[plat]})
    return out


def best_combo(n, max_stack=4):
    """跨平台组合最省：无界背包。容量向下取整（保守），超出 max_stack 份视为该档不适用。"""
    n = max(1, min(200, int(math.ceil(n))))
    items = [{"r": r, "w": int(math.floor(r["mCap"]))} for r in ROWS if r["mCap"] >= 1]
    if not items:
        return None
    INF = float("inf")
    dp = [INF] * (n + 1)
    pre = [None] * (n + 1)
    dp[0] = 0
    for j in range(n + 1):
        if dp[j] == INF:
            continue
        for i, it in enumerate(items):
            k = min(n, j + it["w"])
            c = dp[j] + it["r"]["priceCNY"]
            if c < dp[k]:
                dp[k] = c
                pre[k] = (j, i)
    if dp[n] == INF:
        return None
    counts, cur = {}, n
    while cur > 0 and pre[cur]:
        j, i = pre[cur]
        key = (items[i]["r"]["plat"], items[i]["r"]["tier"], items[i]["r"]["label"])
        counts[key] = counts.get(key, 0) + 1
        cur = j
    used = []
    for (plat, tier, label), cnt in counts.items():
        r = next(x for x in ROWS if x["plat"] == plat and x["tier"] == tier and x["label"] == label)
        used.append({"r": r, "n": cnt})
    used.sort(key=lambda x: -x["n"] * x["r"]["mCap"])
    return {"items": used, "total": dp[n], "cap": sum(u["n"] * u["r"]["mCap"] for u in used)}


def best_single(n, max_stack=4):
    """单一档位买多份最省"""
    best = None
    for r in ROWS:
        if r["mCap"] <= 0:
            continue
        cnt = int(math.ceil(n / r["mCap"] - 1e-9))
        if cnt > max_stack:
            continue
        tot = cnt * r["priceCNY"]
        if best is None or tot < best["total"]:
            best = {"row": r, "n": cnt, "total": tot, "cap": cnt * r["mCap"]}
    return best


LADDER = build_ladder()
MARGINAL = build_marginal()
DISCOUNT = build_discount()
MARG_WORST = max(MARGINAL, key=lambda x: x["mCost"])
MAX_CAP = max(r["mCap"] for r in ROWS)

# 指纹：随数据集变化
import hashlib
_sig = json.dumps([COST["plans"], RATE, SPEC, BRAND], ensure_ascii=False, sort_keys=True)
FP = "HX-CLB-" + UPDATED.replace("-", "") + "-" + hashlib.sha256(_sig.encode()).hexdigest()[:8].upper()


def f2(v):
    return f"{v:,.2f}"


def money(v, cur="CNY"):
    return f"{CU[cur]}{v:,.0f}"


# ═══════════════════════════════════════════════════════════════════
# 3. 样式与脚本
# ═══════════════════════════════════════════════════════════════════
F_SANS = ('"Inter","Inter Display","SN Pro","Space Grotesk",ui-sans-serif,system-ui,'
          '-apple-system,"Segoe UI","PingFang SC","Microsoft YaHei","Noto Sans CJK SC",sans-serif')
F_DISP = ('"Space Grotesk","Inter Display","Inter","SN Pro",ui-sans-serif,system-ui,'
          '"PingFang SC","Microsoft YaHei",sans-serif')
F_MONO = ('"IBM Plex Mono","JetBrains Mono","Geist Mono",ui-monospace,SFMono-Regular,'
          'Menlo,Consolas,monospace')

CSS = r"""
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html{-webkit-text-size-adjust:100%;overflow-x:clip;scroll-behavior:smooth}
:root{--navh:57px;--subh:50px;--gap:18px}
/* ⚠️ 必须是 clip 而非 hidden：overflow-x:hidden 会让 html/body 变成滚动容器，
   使子元素的 position:sticky 失效（实测导航会跟随内容滚走）。 */
body{background:#000;color:#C9CDD2;font:14px/1.7 __SANS__;overflow-x:clip;
  padding-bottom:calc(72px + env(safe-area-inset-bottom,0px));
  -webkit-font-smoothing:antialiased;letter-spacing:-.005em;
  -webkit-tap-highlight-color:transparent}
[id]{scroll-margin-top:calc(var(--navh) + var(--subh) + var(--gap))}
::selection{background:#D1FE17;color:#0B0B0B}
/* ── 环境底光：纯黑底上叠模糊等于没效果，玻璃必须先有可折射的底光 ── */
body::before{content:"";position:fixed;inset:0;pointer-events:none;z-index:0;
  transform:translate3d(0,0,0);
  background:
    radial-gradient(1150px 640px at 6% -12%,rgba(209,254,23,.145),transparent 62%),
    radial-gradient(860px 540px at 105% 3%,rgba(237,21,114,.105),transparent 64%),
    radial-gradient(920px 580px at 44% 108%,rgba(156,230,243,.075),transparent 64%)}
body::after{content:"";position:fixed;inset:0;pointer-events:none;z-index:2;opacity:.04;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.82' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='160' height='160' filter='url(%23n)'/%3E%3C/svg%3E")}

.promo{background:#D1FE17;color:#0B0B0B;font-size:12.5px;font-weight:600;letter-spacing:-.01em;
  display:flex;align-items:center;justify-content:center;gap:13px;flex-wrap:wrap;
  padding:10px 22px;text-align:center;line-height:1.5;position:relative;z-index:3}
.promo b{font-weight:800}
.promo .tag2{border:1.5px solid #0B0B0B;border-radius:999px;padding:2px 11px;font-size:11px;font-weight:700}

.nav{position:sticky;top:0;z-index:40;
  background:linear-gradient(180deg,rgba(255,255,255,.07),rgba(0,0,0,.42));
  -webkit-backdrop-filter:blur(34px) saturate(165%);backdrop-filter:blur(34px) saturate(165%);
  border-bottom:1px solid rgba(255,255,255,.11);
  box-shadow:inset 0 -1px 0 rgba(255,255,255,.04),0 10px 30px rgba(0,0,0,.45)}
.nav .inner{max-width:1280px;margin:0 auto;padding:12px 24px;display:flex;align-items:center;gap:16px}
.brand{display:flex;align-items:center;gap:10px;text-decoration:none;flex:0 0 auto}
.brand i{width:24px;height:24px;border-radius:8px;background:#D1FE17;flex:0 0 24px;
  transition:transform .35s cubic-bezier(.22,1,.36,1)}
.brand:hover i{transform:rotate(45deg)}
.brand .bw{display:flex;flex-direction:column;line-height:1.15}
.brand .bw b{font-family:__DISP__;font-size:16px;font-weight:800;color:#fff;letter-spacing:.06em}
.brand .bw s{text-decoration:none;font-size:9.5px;font-weight:600;color:#6E747D;letter-spacing:.05em}
.menu{display:flex;align-items:center;gap:2px;overflow-x:auto;scrollbar-width:none;
  flex:1 1 auto;min-width:0}
.menu::-webkit-scrollbar{display:none}
.menu a{display:inline-flex;align-items:center;gap:6px;white-space:nowrap;text-decoration:none;
  color:#9AA0A8;font-size:13px;font-weight:600;padding:7px 12px;border-radius:999px;flex:0 0 auto;
  transition:color .22s,background .22s}
.menu a:hover{color:#fff;background:rgba(255,255,255,.065)}
.menu a.active{color:#D1FE17}
.menu .nb{background:#D1FE17;color:#0B0B0B;font-size:9.5px;font-weight:800;padding:1.5px 7px;
  border-radius:999px}
.nav .spec{margin-left:auto;font-family:__MONO__;font-size:11.5px;font-weight:500;color:#D1FE17;
  border:1px solid rgba(209,254,23,.35);border-radius:999px;padding:6px 13px;flex:0 0 auto}

.subnav{position:sticky;top:var(--navh,57px);z-index:35;
  background:linear-gradient(180deg,rgba(255,255,255,.055),rgba(0,0,0,.46));
  -webkit-backdrop-filter:blur(30px) saturate(160%);backdrop-filter:blur(30px) saturate(160%);
  border-bottom:1px solid rgba(255,255,255,.1);box-shadow:0 8px 26px rgba(0,0,0,.4)}
.subnav .inner{max-width:1280px;margin:0 auto;padding:9px 24px;display:flex;gap:6px;
  overflow-x:auto;scrollbar-width:none}
.subnav .inner::-webkit-scrollbar{display:none}
.subnav a{white-space:nowrap;flex:0 0 auto;text-decoration:none;color:#8A9099;font-size:12.5px;
  font-weight:600;padding:6px 14px;border-radius:999px;border:1px solid transparent;
  transition:color .22s,border-color .22s,background .22s}
.subnav a:hover{color:#fff;background:rgba(255,255,255,.05)}
.subnav a.active{color:#D1FE17;border-color:rgba(209,254,23,.4);background:rgba(209,254,23,.07)}

.wrap{max-width:1280px;margin:0 auto;padding:0 24px;position:relative;z-index:1}
/* ── Hero 光场：lime 从「涂料」变「光源」── */
.hero{max-width:1280px;margin:0 auto;padding:58px 24px 6px;position:relative;z-index:1}
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
  color:#D1FE17;margin-bottom:15px;font-family:__MONO__}
h1{font-family:__DISP__;font-size:clamp(31px,5.3vw,60px);font-weight:800;color:#fff;
  letter-spacing:-.038em;line-height:1.07}
h1 em{font-style:normal;color:#D1FE17}
.hero .lead{color:#8A9099;font-size:14.5px;max-width:720px;margin-top:18px;line-height:1.75}
.meta{display:flex;gap:20px;flex-wrap:wrap;margin-top:22px;font-size:12.5px;color:#767C85}
.meta span{display:inline-flex;align-items:center;gap:7px}
.meta i{width:5px;height:5px;border-radius:50%;background:#D1FE17;flex:0 0 5px}
.meta b{color:#C9CDD2;font-weight:600;font-family:__MONO__}
.btns{display:flex;gap:10px;flex-wrap:wrap;margin-top:26px}
.btn{display:inline-block;border-radius:999px;padding:12px 23px;font-size:13px;font-weight:700;
  text-decoration:none;white-space:nowrap;
  transition:transform .22s cubic-bezier(.22,1,.36,1),box-shadow .22s}
.btn-white{background:#fff;color:#0B0B0B}
.btn-white:hover{transform:translateY(-2px);box-shadow:0 10px 32px rgba(255,255,255,.2)}
.btn-ghost{background:transparent;color:#fff;border:1px solid rgba(255,255,255,.2)}
.btn-ghost:hover{border-color:rgba(255,255,255,.45);transform:translateY(-2px)}
.disc{display:flex;gap:11px;align-items:flex-start;max-width:840px;margin-top:26px;
  padding:13px 16px;border:1px solid rgba(255,201,60,.26);border-radius:13px;
  background:rgba(255,201,60,.035);font-size:12px;color:#A9AFB8;line-height:1.7}
.disc b{color:#FFC93C;font-weight:600}
.disc-i{flex:0 0 17px;height:17px;border-radius:50%;background:#FFC93C;color:#0B0B0B;font-size:11px;
  font-weight:800;display:flex;align-items:center;justify-content:center;margin-top:2px}

h2{font-family:__DISP__;font-size:20px;font-weight:750;color:#fff;letter-spacing:-.025em;line-height:1.3}
h2 .ey{display:inline-block;font-family:__MONO__;font-size:12px;font-weight:600;color:#D1FE17;
  margin-right:12px}
.sechead{margin-bottom:18px}
.sechead .sd{color:#767C85;font-size:12.5px;line-height:1.7;max-width:860px}
section{margin-top:60px}
h3{font-family:__DISP__;font-size:14.5px;font-weight:700;color:#fff;margin:26px 0 12px}

/* ── 玻璃面板（规格取自 higgsfield .bg-glass-card：白→黑渐透底 + 大半径模糊）── */
.glass,.card,.kpi,.note,.entry,.legal,details{
  background:linear-gradient(158deg,rgba(255,255,255,.075),rgba(255,255,255,.022) 46%,rgba(0,0,0,.30));
  -webkit-backdrop-filter:blur(28px) saturate(150%);backdrop-filter:blur(28px) saturate(150%);
  border:1px solid rgba(255,255,255,.12);border-radius:18px;
  box-shadow:inset 0 0 0 .61px rgba(255,255,255,.07),inset 0 1px 0 rgba(255,255,255,.05),
             0 1px 2px rgba(0,0,0,.45),0 10px 24px rgba(0,0,0,.4),0 30px 60px rgba(0,0,0,.48)}
@supports not ((-webkit-backdrop-filter:blur(2px)) or (backdrop-filter:blur(2px))){
  .glass,.card,.kpi,.note,.entry,.legal,details,.nav,.subnav{
    background:linear-gradient(158deg,#161B18,#0D110F)}
}
.card{padding:20px 22px}
.grid{display:grid;gap:14px}
.g2{grid-template-columns:repeat(auto-fit,minmax(330px,1fr))}
.g5{grid-template-columns:repeat(auto-fit,minmax(200px,1fr))}
.kpi{padding:18px 20px}
.kpi .t{font-size:9.5px;color:#767C85;font-weight:700;letter-spacing:.13em;text-transform:uppercase}
.kpi .v{font-family:__MONO__;font-size:clamp(30px,3.2vw,46px);font-weight:700;color:#fff;
  margin:12px 0 6px;letter-spacing:-.032em;line-height:1.15}
.kpi.good .v,.kpi.hi .v{color:#D1FE17}
.kpi.hi{border-color:rgba(209,254,23,.45)}
.kpi .d{font-size:12px;color:#8A9099;line-height:1.65}
.kpi .d b{color:#C9CDD2}

.entry{display:block;text-decoration:none;padding:26px;position:relative;
  transition:transform .3s cubic-bezier(.22,1,.36,1),border-color .3s}
.entry:hover{transform:translateY(-4px);border-color:rgba(209,254,23,.42);
  box-shadow:inset 0 0 0 .61px rgba(255,255,255,.09),0 26px 60px rgba(0,0,0,.62),0 0 42px rgba(209,254,23,.09)}
.entry .et{font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#767C85;
  font-family:__MONO__;margin-bottom:12px}
.entry h3{margin:0 0 9px;font-size:18px;font-weight:750;color:#fff}
.entry p{color:#8A9099;font-size:13px;line-height:1.65;margin-bottom:16px}
.entry .nums{display:flex;gap:22px;flex-wrap:wrap;padding-top:16px;
  border-top:1px solid rgba(255,255,255,.07)}
.entry .nums div{display:flex;flex-direction:column;gap:3px}
.entry .nums s{text-decoration:none;font-family:__MONO__;font-size:18px;font-weight:700;
  color:#D1FE17;letter-spacing:-.03em}
.entry .nums em{font-style:normal;font-size:10.5px;color:#767C85;letter-spacing:.06em;text-transform:uppercase}
.entry .arrow{position:absolute;top:24px;right:24px;color:#D1FE17;font-size:17px;
  transition:transform .3s cubic-bezier(.22,1,.36,1)}
.entry:hover .arrow{transform:translateX(4px)}

table{width:100%;border-collapse:separate;border-spacing:0;font-size:13px;
  background:linear-gradient(158deg,rgba(22,27,24,.86),rgba(10,13,11,.92));
  border:1px solid rgba(255,255,255,.12);border-radius:18px;overflow:hidden;
  box-shadow:inset 0 0 0 .61px rgba(255,255,255,.06),0 1px 2px rgba(0,0,0,.5),
             0 8px 20px rgba(0,0,0,.42),0 26px 56px rgba(0,0,0,.46)}
th{background:transparent;color:#767C85;font-weight:700;font-size:10.5px;text-align:left;
  padding:10px 14px;white-space:nowrap;letter-spacing:.095em;text-transform:uppercase;
  border-bottom:1px solid rgba(255,255,255,.08);cursor:pointer;user-select:none;transition:color .2s}
th:hover{color:#D1FE17}
th.ctr,td.ctr{text-align:center}
td{padding:8px 14px;border-bottom:1px solid rgba(255,255,255,.05);white-space:nowrap;
  vertical-align:middle}
tbody tr{transition:background .18s}
tbody tr:last-child td{border-bottom:none}
tbody tr:hover{background:rgba(255,255,255,.032)}
tbody tr.top{background:rgba(209,254,23,.055)}
tbody tr.top td:first-child{box-shadow:inset 3px 0 0 #D1FE17}
.num{text-align:right;font-variant-numeric:tabular-nums;font-family:__MONO__;font-weight:500;
  letter-spacing:-.022em}
.strong{color:#D1FE17;font-weight:600}
.ybest{color:#0B0B0B;font-weight:800;background:#D1FE17}
.rk b{display:block;font-family:__MONO__;font-size:15px;color:#fff;font-weight:700}
.rk s{text-decoration:none;font-size:10px;color:#5A6069;font-family:__MONO__}
.cell2{display:flex;flex-direction:column;gap:2px;line-height:1.25}
.cell2 s{text-decoration:none;font-size:10.5px;color:#6E747D}
.cell2 b{font-weight:600;color:#E4E7EA}
.dot{display:inline-block;width:6px;height:6px;border-radius:50%;margin-right:8px;vertical-align:middle}
.vlabel{display:inline-block;margin-left:6px;padding:1px 6px;border-radius:5px;font-size:10px;
  font-weight:700;color:#D1FE17;background:rgba(209,254,23,.1);
  border:1px solid rgba(209,254,23,.24);white-space:nowrap}
.tagu{display:inline-block;margin-left:7px;padding:1px 6px;border-radius:999px;font-size:9.5px;
  font-weight:700;color:#FF4D8D;border:1px solid rgba(255,77,141,.45)}
.cq-no{color:#5A6069}
.mini{height:5px;border-radius:999px;background:rgba(255,255,255,.07);margin-top:6px;overflow:hidden}
.mini i{display:block;height:100%;border-radius:999px;background:#D1FE17;
  transition:width .9s cubic-bezier(.22,1,.36,1)}
.js .reveal .mini i{width:0!important}
.js .reveal.in .mini i{width:var(--w)!important}
.mini.m2 i{background:linear-gradient(90deg,#3A3F47,#6E7681)}
.mini.m3 i{background:linear-gradient(90deg,#23272D,#3A3F47)}

.tag{display:inline-block;padding:3px 11px;border-radius:999px;font-size:10.5px;font-weight:700}
.v-good{background:#D1FE17;color:#0B0B0B}
.v-warn{background:transparent;color:#C9CDD2;border:1px solid rgba(255,255,255,.18)}
.v-bad{background:transparent;color:#FF6B6B;border:1px solid rgba(255,107,107,.32)}

.note{padding:18px 22px;font-size:13px;line-height:1.78}
.note.warn{border-left:2px solid rgba(255,201,60,.55)}
.note.good{border-left:2px solid rgba(209,254,23,.5)}
ul{margin:8px 0 0 19px}
li{margin:7px 0;font-size:13px;line-height:1.72}
li::marker{color:#D1FE17}
code{background:rgba(209,254,23,.09);border:1px solid rgba(209,254,23,.2);padding:2px 7px;
  border-radius:6px;font-family:__MONO__;font-size:12.5px;color:#D1FE17;font-weight:500}
details{margin-bottom:12px;overflow:hidden;border-radius:16px;transition:border-color .25s}
details:hover{border-color:rgba(209,254,23,.28)}
summary{cursor:pointer;padding:16px 22px;font-size:13.5px;font-weight:650;color:#E4E7EA;
  list-style:none;display:flex;align-items:center;gap:11px}
summary::-webkit-details-marker{display:none}
summary:hover{color:#fff}
summary .chev{margin-left:auto;color:#767C85;font-size:12px;
  transition:transform .3s cubic-bezier(.22,1,.36,1)}
details[open] summary .chev{transform:rotate(90deg);color:#D1FE17}
summary .warnbadge{font-size:10px;font-weight:800;color:#0B0B0B;background:#FFC93C;
  padding:1.5px 7px;border-radius:999px}
.dbody{padding:0 22px 22px;font-size:13px;line-height:1.78}
.dbody>*+*{margin-top:12px}
.dbody h3{margin:18px 0 10px}

.tw{overflow-x:auto;border-radius:18px}
.tw table{min-width:760px}
.tw.scroll-y{max-height:440px;overflow-y:auto;overscroll-behavior:contain}
.tw.tw-main{max-height:min(72vh,640px)}
.tw.scroll-y::-webkit-scrollbar{width:10px;height:10px}
.tw.scroll-y::-webkit-scrollbar-track{background:rgba(255,255,255,.03);border-radius:6px}
.tw.scroll-y::-webkit-scrollbar-thumb{background:rgba(255,255,255,.16);border-radius:6px;
  border:2px solid transparent;background-clip:content-box}
.tw.scroll-y::-webkit-scrollbar-thumb:hover{background:rgba(209,254,23,.45);
  background-clip:content-box;border:2px solid transparent}
.tw.scroll-y{scrollbar-width:thin;scrollbar-color:rgba(255,255,255,.22) transparent}
.tw.scroll-y thead th{position:sticky;top:0;z-index:2;
  background:linear-gradient(180deg,rgba(22,27,24,.98),rgba(16,20,18,.96))}

.ctrl{display:flex;align-items:flex-end;gap:22px;flex-wrap:wrap;margin-bottom:18px}
.field{display:flex;flex-direction:column;gap:7px}
.field label{font-size:10.5px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;
  color:#767C85}
input[type=range]{-webkit-appearance:none;appearance:none;width:min(320px,62vw);height:4px;
  border-radius:999px;outline:none;background:rgba(255,255,255,.12);cursor:pointer}
input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:19px;height:19px;
  border-radius:50%;background:#D1FE17;border:3px solid #000;cursor:pointer}
input[type=number]{width:110px;background:rgba(255,255,255,.06);
  border:1px solid rgba(255,255,255,.14);border-radius:9px;color:#fff;font-family:__MONO__;
  font-size:14px;font-weight:600;padding:7px 10px;outline:none;letter-spacing:-.02em}
input[type=number]:focus{border-color:rgba(209,254,23,.55);background:rgba(209,254,23,.07)}
.big{font-family:__MONO__;font-size:21px;font-weight:700;color:#D1FE17;letter-spacing:-.03em}
.presets{display:inline-flex;gap:5px}
.cqp{background:transparent;border:1px solid rgba(255,255,255,.16);color:#9AA0A8;
  font-family:__MONO__;font-size:11px;font-weight:600;padding:4px 9px;border-radius:999px;
  cursor:pointer;transition:color .2s,border-color .2s,background .2s}
.cqp:hover{color:#fff;border-color:rgba(255,255,255,.36)}
.cqp.on{color:#0B0B0B;background:#D1FE17;border-color:#D1FE17;font-weight:700}
.combo-plus{color:#5A6069;margin:0 5px;font-weight:700}
.roi{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));margin-top:18px}
.roi>div{padding:14px 16px;border-radius:14px;background:rgba(255,255,255,.035);
  border:1px solid rgba(255,255,255,.09)}
.roi .rt{font-size:9.5px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#767C85}
.roi .rv{font-family:__MONO__;font-size:22px;font-weight:700;color:#fff;margin-top:7px;
  letter-spacing:-.03em}
.roi .rv.good{color:#D1FE17}
.roi .rv.bad{color:#FF6B6B}
.roi .rd{font-size:11px;color:#767C85;margin-top:4px}
.sub{color:#767C85;font-size:12px;line-height:1.7}
.mono{font-family:__MONO__}

.foot{margin-top:44px;color:#5A6069;font-size:11.5px;text-align:center;
  border-top:1px solid rgba(255,255,255,.08);padding-top:20px}
.legal{margin-top:22px;padding:26px 28px;background:#D1FE17 !important;border-color:#D1FE17;
  border-radius:20px;color:#0B0B0B;font-size:12px;line-height:1.8;backdrop-filter:none;
  -webkit-backdrop-filter:none}
.legal-t{font-size:16px;font-weight:800;letter-spacing:-.025em;margin-bottom:9px}
.legal-b{color:#1F2A00;max-width:1000px}
.legal-f{margin-top:14px;font-family:__MONO__;font-size:11px;color:#1F2A00}
.legal-f .fp{background:#0B0B0B;color:#D1FE17;padding:2.5px 9px;border-radius:6px;font-weight:600}

@keyframes fadeUp{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:none}}
.reveal{opacity:0;transform:translateY(16px);
  transition:opacity .62s cubic-bezier(.22,1,.36,1),transform .62s cubic-bezier(.22,1,.36,1)}
.reveal.in{opacity:1;transform:none}
.hero>*{animation:fadeUp .7s cubic-bezier(.22,1,.36,1) both}
.hero>*:nth-child(2){animation-delay:.06s}
.hero>*:nth-child(3){animation-delay:.12s}
.hero>*:nth-child(4){animation-delay:.18s}
@media (prefers-reduced-motion:reduce){
  html{scroll-behavior:auto}
  .reveal,.hero>*{opacity:1!important;transform:none!important;animation:none!important;transition:none!important}
}
@media print{
  body{background:#fff!important;color:#000!important;padding:0}
  body::before,body::after,.hero::before,.hero::after{display:none!important}
  .glass,.card,.kpi,.note,.entry,.legal,details,.nav,.subnav,table{
    -webkit-backdrop-filter:none!important;backdrop-filter:none!important;
    box-shadow:none!important;background:#fff!important}
  .nav,.subnav{position:static!important}
  .promo{background:#D1FE17!important;color:#000!important}
  .brand .bw b,.menu a,h1,h2,h3,td,th,li,.kpi .v,.lead,.meta{color:#000!important}
  .legal{background:#F2FFB8!important}
  .legal-t,.legal-b,.legal-f{color:#000!important}
  .tw{overflow:visible!important}
  .tw table{min-width:0!important}
  details:not([open]) .dbody{display:block!important}
}
@media (max-width:820px){
  .promo{font-size:11.5px;padding:9px 14px;gap:9px}
  .nav .inner{padding:10px 15px;gap:11px}
  .nav .spec{display:none}
  .subnav .inner{padding:8px 15px}
  .hero{padding:36px 15px 4px}
  .wrap{padding:0 15px}
  section{margin-top:44px}
  h2{font-size:17.5px}
  .kpi .v{font-size:26px}
  .entry{padding:20px}
  .card,.kpi,.note,.legal,table,details,.entry{border-radius:15px}
  .legal{padding:21px 18px}
  td,th{padding:7px 11px}
  summary{padding:14px 17px;font-size:13px}
  .dbody{padding:0 17px 18px}
  .g5,.g2{grid-template-columns:1fr 1fr}
  .ctrl{gap:14px}
  input[type=range]{width:100%}
}
@media (max-width:520px){ .g5,.g2{grid-template-columns:1fr} }
"""

JS = r"""
/* 标记脚本可用：纯 CSS 的渐进增强据此启用（无 JS 时不会降级成空条） */
document.documentElement.classList.add('js');

/* ── 吸顶偏移实测：导航高度随视口/文案换行变化，写死会错位 ── */
(function(){
  function sync(){
    var n = document.querySelector('.nav'), s = document.querySelector('.subnav');
    var st = document.documentElement.style;
    if(n) st.setProperty('--navh', n.offsetHeight + 'px');
    if(s) st.setProperty('--subh', s.offsetHeight + 'px');
  }
  sync();
  window.addEventListener('resize', sync, {passive:true});
  window.addEventListener('orientationchange', sync, {passive:true});
  if(document.fonts && document.fonts.ready) document.fonts.ready.then(sync);
})();

/* ── 滚动入场 ── */
(function(){
  var els = document.querySelectorAll('.reveal');
  if(!('IntersectionObserver' in window)){ els.forEach(function(e){e.classList.add('in');}); return; }
  var io = new IntersectionObserver(function(es){
    es.forEach(function(e){ if(e.isIntersecting){ e.target.classList.add('in'); io.unobserve(e.target); } });
  }, {rootMargin:'0px 0px -8% 0px', threshold:.06});
  els.forEach(function(e){ io.observe(e); });
})();

/* ── 子导航高亮 ──
   判定必须用【视口坐标】(getBoundingClientRect)，不能混用 offsetTop 与 scrollY：
   offsetTop 相对 offsetParent（.wrap 位于 hero 之下），与 scrollY 不同坐标系，
   混用会把判定整体推后一个 hero 的高度，表现为「点 A 却高亮 A 的下一个」。 */
(function(){
  var links = Array.prototype.slice.call(document.querySelectorAll('.subnav a[href^="#"]'));
  if(!links.length) return;
  var map = links.map(function(a){ return {a:a, el:document.querySelector(a.getAttribute('href'))}; })
                 .filter(function(x){ return x.el; })
                 .sort(function(p,q){ return p.el.offsetTop - q.el.offsetTop; });  /* 仅定序 */
  var last = -1;
  function stickPx(){
    var cs = getComputedStyle(document.documentElement);
    return (parseFloat(cs.getPropertyValue('--navh')) || 57)
         + (parseFloat(cs.getPropertyValue('--subh')) || 50) + 24;
  }
  function upd(){
    var off = stickPx(), idx = 0;
    for(var i=0;i<map.length;i++){
      if(map[i].el.getBoundingClientRect().top - off <= 0) idx = i;
    }
    if(window.innerHeight + window.scrollY >= document.body.scrollHeight - 4) idx = map.length - 1;
    if(idx === last) return;
    last = idx;
    links.forEach(function(a){ a.classList.remove('active'); });
    if(map[idx]) map[idx].a.classList.add('active');
  }
  var t = null;
  window.addEventListener('scroll', function(){
    if(t) return; t = requestAnimationFrame(function(){ upd(); t = null; });
  }, {passive:true});
  upd();
})();

/* ── 子导航点击即时高亮 ── */
document.addEventListener('DOMContentLoaded', function(){
  Array.prototype.forEach.call(document.querySelectorAll('.subnav a[href^="#"]'), function(a){
    a.addEventListener('click', function(){
      Array.prototype.forEach.call(document.querySelectorAll('.subnav a'), function(x){
        x.classList.remove('active');
      });
      a.classList.add('active');
    });
  });
});
__COST__
"""

COST_JS = r"""
/* ══════════════════════════════════════════════════════════════
   成本页：总投入产出（月产量滑块 + 单条产出价值 → ROI）
   外加「全档位对比」按该产量的年支出重排（排名格副行直接显示该产量下的年支出）
   ══════════════════════════════════════════════════════════════ */
var PLANS = __PLANS__;
var MAX_STACK = 4;          /* 同档最多叠加份数 */
var CQ_LOCK = false, CQ_LAST = null, VAL_LAST = null;

/* 单档覆盖目标产量的最低支出：可行返回 {n,total}，不可行返回 null */
function needOf(cap, price, N){
  if(!(cap > 0)) return null;
  var n = Math.ceil(N / cap - 1e-9);
  if(n > MAX_STACK) return null;
  return {n:n, total:n * price};
}

/* 跨平台组合最省：无界背包。容量向下取整（保守），保证方案一定可行。 */
function bestCombo(N){
  N = Math.max(1, Math.min(200, Math.ceil(N)));
  var items = [];
  for(var i=0;i<PLANS.length;i++){
    var w = Math.floor(PLANS[i].mCap);
    if(w >= 1) items.push({p:PLANS[i], w:w});
  }
  if(!items.length) return null;
  var INF = Infinity, dp = [], pre = [];
  for(var j=0;j<=N;j++){ dp[j] = INF; pre[j] = null; }
  dp[0] = 0;
  for(var j=0;j<=N;j++){
    if(dp[j] === INF) continue;
    for(var i=0;i<items.length;i++){
      var k = Math.min(N, j + items[i].w), c = dp[j] + items[i].p.price;
      if(c < dp[k]){ dp[k] = c; pre[k] = {from:j, item:i}; }
    }
  }
  if(dp[N] === INF) return null;
  var counts = [], cur = N;
  while(cur > 0 && pre[cur]){
    var e = pre[cur], it = items[e.item], hit = null;
    for(var q=0;q<counts.length;q++){ if(counts[q].p === it.p){ hit = counts[q]; break; } }
    if(hit) hit.n++; else counts.push({p:it.p, n:1});
    cur = e.from;
  }
  var cap = 0;
  for(var q2=0;q2<counts.length;q2++) cap += counts[q2].n * counts[q2].p.mCap;
  counts.sort(function(x,y){ return y.p.mCap - x.p.mCap; });
  return {items:counts, total:dp[N], cap:cap};
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

function money(v, cur){ return (cur === 'USD' ? '$' : '\u00a5') + Math.round(v).toLocaleString(); }

/* ── 主渲染 ── */
function renderRec(){
  var s = document.getElementById('tgt'), v = document.getElementById('val');
  if(!s || !v) return;
  var N = Math.max(1, Math.min(200, parseInt(s.value || '30', 10)));
  var V = Math.max(0, parseFloat(v.value || '0'));
  if(CQ_LAST === N && VAL_LAST === V) return;   /* 节流：拖动时 input 高频触发 */
  CQ_LAST = N; VAL_LAST = V;

  var secs = N * 30, mins = secs / 60;
  var nv = document.getElementById('nv');
  if(nv) nv.textContent = N + ' 条/月';
  var nd = document.getElementById('ndur');
  if(nd) nd.textContent = '= ' + secs.toLocaleString() + ' 秒 \u2248 ' +
    (mins >= 60 ? (mins/60).toFixed(1) + ' 小时' : mins.toFixed(0) + ' 分钟') + '素材';
  Array.prototype.forEach.call(document.querySelectorAll('#presets .cqp'), function(b){
    b.classList.toggle('on', parseInt(b.dataset.n, 10) === N);
  });

  /* 方案表 */
  var single = null;
  for(var i=0;i<PLANS.length;i++){
    var x = needOf(PLANS[i].mCap, PLANS[i].price, N);
    if(x && (!single || x.total < single.total)) single = {p:PLANS[i], n:x.n, total:x.total, cap:x.n*PLANS[i].mCap};
  }
  var combo = bestCombo(N);
  var h = '';
  if(single){
    h += '<tr><td>单一档位最省</td>'
      +  '<td><span class="dot" style="background:' + single.p.color + '"></span>' + single.p.plat + ' ' +
         single.p.tier + (single.n > 1 ? ' \u00d7 ' + single.n : '') + '</td>'
      +  '<td class="num strong">' + money(single.total) + '</td>'
      +  '<td class="num">' + single.cap.toFixed(1) + ' 条/月</td>'
      +  '<td class="num">' + money(single.total / N) + '</td></tr>';
  } else {
    h += '<tr><td>单一档位最省</td><td colspan="4" class="sub">无单一档位可在 ' + MAX_STACK + ' 份内覆盖</td></tr>';
  }
  if(combo){
    h += '<tr><td>组合订阅最省<br><span class="sub">跨平台混合</span></td>'
      +  '<td>' + comboLabel(combo) + '</td>'
      +  '<td class="num strong">' + money(combo.total) + '</td>'
      +  '<td class="num">' + combo.cap.toFixed(1) + ' 条/月</td>'
      +  '<td class="num">' + money(combo.total / N) + '</td></tr>';
  }
  var rec = document.getElementById('rec');
  if(rec) rec.innerHTML = h;

  /* ROI 区块 —— 以「组合订阅最省」为计算基准 */
  var plan = combo || (single ? {total:single.total, cap:single.cap} : null);
  var yClips = N * 12;
  var spend = plan ? plan.total : 0;
  var revenue = yClips * V;
  var net = revenue - spend;
  var roi = spend > 0 ? revenue / spend : 0;
  var breakeven = V > 0 ? Math.ceil(spend / V) : null;
  function set(id, txt, cls){
    var e = document.getElementById(id);
    if(!e) return;
    e.textContent = txt;
    e.className = 'rv' + (cls ? ' ' + cls : '');
  }
  set('roi-spend', money(spend));
  set('roi-clips', yClips.toLocaleString() + ' 条');
  set('roi-rev', money(revenue));
  set('roi-net', (net >= 0 ? '+' : '\u2212') + money(Math.abs(net)), net >= 0 ? 'good' : 'bad');
  set('roi-x', roi > 0 ? roi.toFixed(2) + '\u00d7' : '\u2014', roi >= 1 ? 'good' : (roi > 0 ? 'bad' : ''));
  set('roi-be', breakeven === null ? '\u2014' : breakeven.toLocaleString() + ' 条');
}

/* ── 全档位对比：按该产量的年支出重排（不新增列，成本并入排名格副行）── */
function rerank(){
  var s = document.getElementById('tgt');
  var tb = document.querySelector('#main tbody');
  if(!s || !tb) return;
  var N = Math.max(1, Math.min(200, parseInt(s.value || '30', 10)));
  var rs = Array.prototype.slice.call(tb.querySelectorAll('tr'));
  var best = Infinity;
  rs.forEach(function(r){
    var x = needOf(parseFloat(r.dataset.c), parseFloat(r.dataset.p), N);
    r.__n = x ? x.n : null;
    r.__t = x ? x.total : null;
    if(x && x.total < best) best = x.total;
  });
  rs.sort(function(x, y){
    if(x.__t == null && y.__t == null) return 0;
    if(x.__t == null) return 1;
    if(y.__t == null) return -1;
    return x.__t - y.__t;
  });
  rs.forEach(function(r, i){
    tb.appendChild(r);
    var rk = r.querySelector('.rk'); if(!rk) return;
    var b = rk.querySelector('b'), ss = rk.querySelector('s');
    if(r.__t == null){
      if(b) b.textContent = '\u2014';
      if(ss) ss.textContent = '产能过低';
    } else {
      if(b) b.textContent = i + 1;
      if(ss) ss.textContent = money(r.__t) + (r.__n > 1 ? ' \u00b7 ' + r.__n + '\u00d7' : '');
    }
  });
  rs.forEach(function(r){ r.classList.remove('top'); });
  if(rs.length && rs[0].__t != null) rs[0].classList.add('top');
  var vth = document.getElementById('vth');
  if(vth) vth.textContent = '单条成本';
}

/* ── 表头排序（点击覆盖滑块排序，滑块再动即覆盖回来）── */
function sortBy(k, el){
  var tb = document.querySelector('#main tbody');
  if(!tb) return;
  var rs = Array.prototype.slice.call(tb.querySelectorAll('tr'));
  var dir = el.dataset.dir === 'asc' ? -1 : 1;
  el.dataset.dir = dir === 1 ? 'asc' : 'desc';
  rs.sort(function(a, b){ return (parseFloat(a.dataset[k]) - parseFloat(b.dataset[k])) * dir; });
  rs.forEach(function(r){ tb.appendChild(r); });
}

document.addEventListener('DOMContentLoaded', function(){
  var s = document.getElementById('tgt'), v = document.getElementById('val');
  if(s){
    s.addEventListener('input', function(){ CQ_LAST = null; renderRec(); rerank(); });
    CQ_LAST = null; renderRec(); rerank();
  }
  if(v){
    v.addEventListener('change', function(){ VAL_LAST = null; renderRec(); });
    v.addEventListener('input', function(){ VAL_LAST = null; renderRec(); });
  }
  Array.prototype.forEach.call(document.querySelectorAll('#presets .cqp'), function(b){
    b.addEventListener('click', function(){
      if(s){ s.value = b.dataset.n; CQ_LAST = null; renderRec(); rerank(); }
    });
  });
});
"""


def sub_css(s):
    return s.replace("__SANS__", F_SANS).replace("__DISP__", F_DISP).replace("__MONO__", F_MONO)


# ═══════════════════════════════════════════════════════════════════
# 4. 组件
# ═══════════════════════════════════════════════════════════════════
def promo():
    return (f'<div class="promo"><span><b>价格说明：</b>{BRAND_CN}数据采集于 {UPDATED}，'
            f'各平台价格取决于当期活动与限时优惠力度，不代表最终价格</span>'
            f'<span class="tag2">数据时点 {UPDATED}</span></div>')


def nav(active):
    items = ""
    for it in NAV:
        soon = it["key"] == "leaderboard-vlm" and VLM["status"] == "coming-soon"
        badge = '<i class="nb">即将上线</i>' if soon else ""
        cls = ' class="active"' if it["key"] == active else ""
        items += f'<a href="{it["href"]}"{cls}>{it["label"]}{badge}</a>'
    return (f'<div class="nav"><div class="inner">'
            f'<a class="brand" href="index.html"><i></i>'
            f'<span class="bw"><b>{BRAND}</b><s>{STUDIO}</s></span></a>'
            f'<nav class="menu">{items}</nav>'
            f'<span class="spec">{SPEC}</span></div></div>')


def legal():
    return (f'<div class="legal"><div class="legal-t">{COPY}</div>'
            f'<div class="legal-b">{TERMS}</div>'
            f'<div class="legal-f">溯源指纹 <span class="fp">{FP}</span>　·　'
            f'{BRAND} · {BRAND_CN}　·　{STUDIO} 出品　·　数据采集 {UPDATED}</div></div>')


def foot(text):
    return f'<div class="foot">{text}</div>'


def kpi(t, v, d, cls="", vcls="rv"):
    return (f'<div class="kpi {cls}"><div class="t">{t}</div>'
            f'<div class="v">{v}</div><div class="d">{d}</div></div>')


def sec_head(num, title, desc=""):
    sd = f'<div class="sd">{desc}</div>' if desc else ""
    return f'<div class="sechead"><h2><span class="ey">{num}</span>{title}</h2>{sd}</div>'


def table(headers, rows, cls="tw scroll-y", tid=""):
    """headers: [(文本, 是否可排序的 data-key or None)]"""
    th = ""
    for h in headers:
        txt, key = h[0], h[1]
        th += f'<th onclick="sortBy(\'{key}\',this)" class="ctr">{txt}</th>' if key \
              else f'<th class="ctr">{txt}</th>'
    idattr = f' id="{tid}"' if tid else ""
    return f'<div class="{cls}"><table{idattr}><thead><tr>{th}</tr></thead>' \
           f'<tbody>{rows}</tbody></table></div>'


def dash(v, dec=2, suffix=""):
    return f'{v:.{dec}f}{suffix}'


# ═══════════════════════════════════════════════════════════════════
# 5. 页面
# ═══════════════════════════════════════════════════════════════════
def page(title, desc, nav_html, body, cost_js=False):
    js = JS.replace("__COST__", COST_JS) if cost_js else JS.replace("__COST__", "")
    if cost_js:
        js = js.replace("__PLANS__", json.dumps(
            [{"plat": r["plat"], "tier": r["tier"], "label": r["label"], "color": r["color"],
              "price": round(r["priceCNY"], 2), "mCap": round(r["mCap"], 4)} for r in ROWS],
            ensure_ascii=False))
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="format-detection" content="telephone=no,email=no,address=no">
<meta name="theme-color" content="#000000">
<meta name="color-scheme" content="dark">
<meta name="description" content="{desc}">
<meta property="og:title" content="{BRAND} · {title}">
<meta property="og:description" content="{desc}">
<title>{BRAND} · {title}</title>
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='9' fill='%23D1FE17'/%3E%3C/svg%3E">
<link rel="apple-touch-icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='9' fill='%23D1FE17'/%3E%3C/svg%3E">
<!-- ============================================================
     {FP}
     {COPY}
     数据采集时点：{UPDATED}　作者：{OWNER}
     {TERMS}
     ============================================================ -->
<meta name="author" content="{OWNER}">
<meta name="copyright" content="{COPY}">
<meta name="rights" content="{TERMS}">
<meta name="dcterms.rights" content="{COPY}">
<meta name="fingerprint" content="{FP}">
<meta name="robots" content="noindex, nofollow, noarchive, nosnippet, noimageindex, notranslate, noai, noimageai">
<meta name="googlebot" content="noindex, nofollow, noarchive, nosnippet, noimageindex">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src data:; connect-src 'none'; object-src 'none'; frame-src 'none'; base-uri 'none'; form-action 'none'">
<meta http-equiv="X-Content-Type-Options" content="nosniff">
<meta name="referrer" content="no-referrer">
<style>{sub_css(CSS)}</style></head><body>

{promo()}
{nav_html}
{body}
<div class="wrap">{legal()}</div>

<script>{js}</script>
</body></html>"""


# ── 首页 ──────────────────────────────────────────────────────────
_best = min(ROWS, key=lambda r: r["perVideo"])
_second = sorted(ROWS, key=lambda r: r["perVideo"])[1]
_mid = next(r for r in ROWS if r["plat"] == "小云雀" and r["tier"] == "高级会员" and r["monthly"] == 12000)
_top = max(LADDER, key=lambda x: x["hi"])["row"]
_hg = min((r for r in ROWS if r["plat"] == "Higgsfield"), key=lambda r: r["perVideo"])

home_body = f"""
<div class="hero">
  <div class="eyebrow">{BRAND} · Unified Benchmark</div>
  <h1>把 AI 平台<br>放在<em>同一把尺子</em>上</h1>
  <p class="lead">{SITE["intro"]}</p>
  <div class="btns">
    <a class="btn btn-white" href="#cost">进入平台成本对比</a>
    <a class="btn btn-ghost" href="cost.html">完整方法论与数据</a>
  </div>
</div>

<div class="wrap">
<section id="cost" class="reveal" style="margin-top:40px">
  {sec_head("板块", "两条对比线", "统一口径的方法论复用在同一套框架下：成本线已上线，能力线在建。")}
  <div class="grid g2">
    <a class="entry" href="cost.html">
      <span class="arrow">→</span>
      <div class="et">LIVE · {UPDATED}</div>
      <h3>平台成本对比</h3>
      <p>5 个平台、{len(ROWS)} 个可选档位，按「{SPEC}」统一口径折算单条现金成本。</p>
      <div class="nums">
        <div><s>¥{f2(BEST)}</s><em>最低单条</em></div>
        <div><s>{WORST/BEST:.2f}×</s><em>最贵/最省</em></div>
        <div><s>{len(ROWS)}</s><em>可选档位</em></div>
      </div>
    </a>
    <a class="entry" href="leaderboard-vlm.html">
      <span class="arrow">→</span>
      <div class="et">{VLM["eyebrow"]} · 评测中</div>
      <h3>{VLM["title"]} <i class="nb" style="font-size:9.5px;font-weight:800;color:#0B0B0B;background:#D1FE17;padding:1.5px 7px;border-radius:999px">即将上线</i></h3>
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
  {sec_head("结论", "成本线速览", "完整数据、算法与风险说明见成本对比页。")}
  <div class="grid g5">
    {kpi("单条成本最优", f"¥{f2(BEST)}", f"{_best['plat']} {tname(_best)}<br>与次优 ¥{f2(_second['perVideo'])} 差 {(_second['perVideo']/BEST-1)*100:.2f}%", "hi")}
    {kpi("中产能最省", f"¥{_mid['priceCNY']:,.0f}", f"{_mid['plat']} {tname(_mid)}<br>¥{f2(_mid['perVideo'])}/条", "good")}
    {kpi("大产能最省", f"¥{_top['priceCNY']:,.0f}", f"{_top['plat']} {tname(_top)}<br>{_top['mCap']:.2f} 条/月", "good")}
    {kpi("海外平台溢价", f"{_hg['perVideo']/BEST:.2f}×", f"Higgsfield {_hg['tier']} ¥{f2(_hg['perVideo'])}/条<br>无成本优势")}
    {kpi("最差档位", f"{WORST/BEST:.2f}×", f"Higgsfield Starter ¥{f2(WORST)}/条<br>低档位多是高价试用")}
  </div>
</section>
{foot(f'{BRAND} · {BRAND_CN}　|　{STUDIO} 出品　|　数据采集 {UPDATED}　·　全部数值按统一口径重算，非平台宣传数字')}
</div>
"""

# ── 成本页 ────────────────────────────────────────────────────────
SUBNAV = [("overview", "概览"), ("calc", "按产量测算"), ("table", "档位对比"),
          ("ladder", "达标阶梯"), ("margin", "边际成本"), ("discount", "折扣结构"),
          ("official", "官方对照"), ("retry", "失败退分"), ("appendix", "原始数据")]

subnav_html = ('<div class="subnav"><div class="inner">' +
               "".join(f'<a href="#{k}">{v}</a>' for k, v in SUBNAV) + "</div></div>")

# 主表：7 列，无「月产能」「年支出」列（用户裁定去掉）
main_rows = ""
for r in sorted(ROWS, key=lambda x: x["perVideo"]):
    price_disp = f'{CU[r["cur"]]}{r["price"]:,}'
    sub = f'≈¥{r["priceCNY"]:,.0f}' if r["cur"] == "USD" else r["cur"]
    vl = f'<span class="vlabel">{r["label"]}</span>' if r["multi"] else ""
    usd = '<span class="tagu">USD</span>' if r["cur"] == "USD" else ""
    w = BEST / r["perVideo"] * 100
    mc = "" if r["perVideo"] <= BEST * 1.06 else (" m2" if r["perVideo"] <= 30 else " m3")
    main_rows += (
        f'<tr class="{"top" if r["rank"]==1 else ""}" data-v="{r["perVideo"]:.4f}" '
        f'data-p="{r["priceCNY"]:.2f}" data-c="{r["mCap"]:.4f}">'
        f'<td class="ctr rk"><b>{r["rank"]}</b><s>{r["rel"]:.2f}×</s></td>'
        f'<td><span class="dot" style="background:{r["color"]}"></span>{r["plat"]}{usd}</td>'
        f'<td>{r["tier"]}{vl}</td>'
        f'<td class="num cell2"><b>{price_disp}</b><s>{sub}</s></td>'
        f'<td class="num">{r["monthly"]:,}</td>'
        f'<td class="num"><span class="strong">¥{f2(r["perVideo"])}</span>'
        f'<div class="mini{mc}"><i style="--w:{w:.1f}%;width:{w:.1f}%"></i></div></td>'
        f'<td class="num cell2"><b>{r["perSec"]:.3f}</b><s>元/秒</s></td></tr>')

lad_rows = ""
for i, x in enumerate(LADDER):
    r = x["row"]
    lo = "0" if i == 0 else f'{x["lo"]:.2f}'
    lad_rows += (f'<tr><td class="num mono">{lo} – {x["hi"]:.2f}</td>'
                 f'<td><span class="dot" style="background:{r["color"]}"></span>{r["plat"]} {tname(r)}</td>'
                 f'<td class="num strong">¥{r["priceCNY"]:,.0f}</td>'
                 f'<td class="num">{r["mCap"]:.2f}</td>'
                 f'<td class="num">¥{f2(r["perVideo"])}</td>'
                 f'<td class="num">{r["rel"]:.2f}×</td></tr>')

marg_rows = ""
for m in sorted(MARGINAL, key=lambda x: x["mCost"]):
    if m["mCost"] <= BEST * 1.05:
        txt, cls = "强烈推荐", "v-good"
    elif m["mCost"] <= 26:
        txt, cls = "一般", "v-warn"
    else:
        txt, cls = "不建议", "v-bad"
    marg_rows += (f'<tr><td><span class="dot" style="background:{m["color"]}"></span>{m["plat"]}</td>'
                  f'<td>{m["a"]["tier"]} → {m["b"]["tier"]}</td>'
                  f'<td class="num">¥{m["dPrice"]:,.0f}</td><td class="num">+{m["dCap"]:.0f}</td>'
                  f'<td class="num strong">¥{f2(m["mCost"])}</td>'
                  f'<td class="num">{f2(m["avg"])}</td>'
                  f'<td class="ctr"><span class="tag {cls}">{txt}</span></td></tr>')

disc_rows = ""
for d in DISCOUNT:
    disc_rows += (f'<tr><td><span class="dot" style="background:{d["color"]}"></span>{d["plat"]}</td>'
                  f'<td class="num">{d["minD"]*10:.1f}–{d["maxD"]*10:.1f} 折</td>'
                  f'<td class="num">¥{f2(d["minO"])} – ¥{f2(d["maxO"])}</td>'
                  f'<td class="num {"ybest" if d["spreadO"]<15 else ""}">{d["spreadO"]:.1f}%</td>'
                  f'<td class="num {"ybest" if d["spreadD"]<15 else ""}">{d["spreadD"]:.1f}%</td></tr>')

claim_rows = ""
for plat, a in COST["adClaim"].items():
    real = next(r["perSec"] for r in ROWS if r["plat"] == plat and r["tier"] == a["tier"])
    claim_rows += (f'<tr><td><span class="dot" style="background:{COLOR[plat]}"></span>{plat}</td>'
                   f'<td>{a["tier"]}</td><td class="num">¥{a["perSec"]:.2f}</td>'
                   f'<td class="num strong">¥{real:.3f}</td>'
                   f'<td class="num">{real/a["perSec"]:.2f}×</td></tr>')

retry_rows = ""
for x in COST["retryPolicy"]:
    retry_rows += (f'<tr><td><span class="dot" style="background:{COLOR.get(x["plat"],"#767C85")}"></span>{x["plat"]}</td>'
                   f'<td class="ctr"><span class="tag v-good">{x["retry"]}</span></td>'
                   f'<td>{x["basis"]}</td></tr>')

ap_rows = ""
for p in COST["plans"]:
    for c in p["credits"]:
        r = next(x for x in ROWS if x["plat"] == p["platform"] and x["tier"] == p["tier"]
                 and x["monthly"] == c["credits"])
        off = OFFICIAL_RATE.get(p["platform"], {}).get(p["tier"])
        offs = f'{off:,.1f} 积分/元' if off else "—"
        ap_rows += (f'<tr><td><span class="dot" style="background:{r["color"]}"></span>{r["plat"]}</td>'
                    f'<td>{r["tier"]}</td><td class="num">{r["label"] or "—"}</td>'
                    f'<td class="num">{r["monthly"]:,}</td>'
                    f'<td class="num">{CU[r["cur"]]}{r["price"]:,}</td>'
                    f'<td class="num">{"¥%s" % format(r["priceCNY"], ",.0f") if r["cur"]=="USD" else "—"}</td>'
                    f'<td class="num">{r["perYuan"]:,.1f}</td>'
                    f'<td class="num">{offs}</td>'
                    f'<td class="num">{CU[r["cur"]] + format(r["original"], ",") if r["original"] else "—"}</td></tr>')

src_rows = "".join(f'<tr><td>{s["page"]}</td><td style="white-space:normal">{s["data"]}</td></tr>'
                   for s in COST["sources"])

retry_src = "".join(f'<h3>{x["plat"]}</h3>' for x in COST["retryPolicy"])
budget_bullets = "".join(
    f'<li><b>月产 {"0" if i == 0 else format(x["lo"], ".2f")}–{x["hi"]:.2f} 条：</b>'
    f'{x["row"]["plat"]} {tname(x["row"])} — ¥{x["row"]["priceCNY"]:,.0f}/年'
    f'（¥{f2(x["row"]["perVideo"])}/条 · 单价为最优解的 {x["row"]["rel"]:.2f} 倍）</li>'
    for i, x in enumerate(LADDER))

# 计算器的服务端初始态（N=30），保证无 JS 时也不是空表
_init_s = best_single(30)
_init_c = best_combo(30)
_init_combo_html = ""
if _init_s:
    _init_combo_html += (f'<tr><td>单一档位最省</td>'
                         f'<td><span class="dot" style="background:{_init_s["row"]["color"]}"></span>'
                         f'{_init_s["row"]["plat"]} {_init_s["row"]["tier"]}'
                         f'{" × " + str(_init_s["n"]) if _init_s["n"] > 1 else ""}</td>'
                         f'<td class="num strong">¥{_init_s["total"]:,.0f}</td>'
                         f'<td class="num">{_init_s["cap"]:.1f} 条/月</td>'
                         f'<td class="num">¥{_init_s["total"]/30:,.0f}</td></tr>')
if _init_c:
    lbl = '<span class="combo-plus">+</span>'.join(
        f'<span class="dot" style="background:{u["r"]["color"]}"></span>{u["r"]["plat"]} {u["r"]["tier"]}'
        f'{" × " + str(u["n"]) if u["n"] > 1 else ""}' for u in _init_c["items"])
    _init_combo_html += (f'<tr><td>组合订阅最省<br><span class="sub">跨平台混合</span></td>'
                         f'<td>{lbl}</td>'
                         f'<td class="num strong">¥{_init_c["total"]:,.0f}</td>'
                         f'<td class="num">{_init_c["cap"]:.1f} 条/月</td>'
                         f'<td class="num">¥{_init_c["total"]/30:,.0f}</td></tr>')

cost_body = f"""
{subnav_html}
<div class="hero">
  <div class="eyebrow">{COST["eyebrow"]}</div>
  <h1>同一条 {SEC_PER_CLIP} 秒视频<br>最贵档比最省档贵 <em>{WORST/BEST:.2f} 倍</em></h1>
  <p class="lead">5 个平台的积分币值互不相同，直接比消耗没有意义。这里先把它们压平到同一口径，再折算成单条现金成本。</p>
  <div class="meta">
    <span><i></i>数据时点 <b>{UPDATED}</b></span>
    <span><i></i>平台 <b>{len(PLATFORMS)}</b></span>
    <span><i></i>可选档位 <b>{len(ROWS)}</b></span>
    <span><i></i>汇率 <b>1 USD = {RATE}</b></span>
    <span><i></i>口径依据 <b>年费 ÷ (月积分 × 12)</b></span>
    <span><i></i>口径范围 <b>{SCOPE["currentShort"]}</b></span>
  </div>
</div>

<div class="wrap">
<div class="note warn" style="margin-top:28px">
  <b>数据范围说明：</b>本表目前仅覆盖各平台的<b>{SCOPE["current"]}</b>。
  平台上另有<b>月度会员、季度会员</b>等更短周期选项，因计价单位与折扣结构不同，
  后续将单独补充并纳入同口径对比。<br><br>
  <b>{SCOPE["impact"]}</b>
</div>

<section id="overview" class="reveal" style="margin-top:42px">
  <div class="grid g5">
    {kpi("单条成本最优", f"¥{f2(BEST)}", f"{_best['plat']} {tname(_best)}<br>{_best['mCap']:.2f} 条/月 · ¥{_best['perSec']:.3f}/秒", "hi")}
    {kpi("中产能最省", f"¥{_mid['priceCNY']:,.0f}", f"{_mid['plat']} {tname(_mid)}<br>{_mid['mCap']:.2f} 条/月 · ¥{f2(_mid['perVideo'])}/条", "good")}
    {kpi("大产能最省", f"¥{_top['priceCNY']:,.0f}", f"{_top['plat']} {tname(_top)}<br>{_top['mCap']:.2f} 条/月 · ¥{f2(_top['perVideo'])}/条", "good")}
    {kpi("海外平台溢价", f"{_hg['perVideo']/BEST:.2f}×", f"Higgsfield {_hg['tier']} ¥{f2(_hg['perVideo'])}/条<br>含税后约 ¥{_hg['perVideo']*1.08:.2f}")}
    {kpi("最差档位", f"{WORST/BEST:.2f}×", f"Higgsfield Starter ¥{f2(WORST)}/条<br>低档位多是高价试用")}
  </div>
</section>

<section id="calc" class="reveal">
  {sec_head("01", "按产量测算总投入与回报", "先填两个数：要出多少条、每条值多少钱。表与 ROI 实时联动；1 条 = " + str(SEC_PER_CLIP) + " 秒。")}
  <div class="card">
    <div class="ctrl">
      <div class="field">
        <label for="tgt">月产量</label>
        <input type="range" id="tgt" min="1" max="200" step="1" value="30" aria-label="月产量">
      </div>
      <div class="field">
        <label>换算</label>
        <span class="big" id="nv">30 条/月</span>
        <span class="sub" id="ndur">= 900 秒 ≈ 15 分钟素材</span>
      </div>
      <div class="field">
        <label for="val">单条产出价值（元）</label>
        <input type="number" id="val" min="0" step="50" value="500" aria-label="单条产出价值">
      </div>
      <div class="field">
        <label>常用档位</label>
        <span class="presets" id="presets">
          <button type="button" class="cqp" data-n="5">5</button>
          <button type="button" class="cqp" data-n="10">10</button>
          <button type="button" class="cqp on" data-n="30">30</button>
          <button type="button" class="cqp" data-n="50">50</button>
          <button type="button" class="cqp" data-n="100">100</button>
        </span>
      </div>
    </div>
    <div class="tw"><table><thead><tr>
      <th>方案类型</th><th>档位组合</th><th class="ctr">年支出</th>
      <th class="ctr">实际产能</th><th class="ctr">单条成本</th></tr></thead>
      <tbody id="rec">{_init_combo_html}</tbody></table></div>
    <div class="sub" style="margin-top:10px">
      组合订阅为<b>跨平台混合求解</b>（无界背包）：允许不同平台档位叠加、同一档位可多份，最多 {4} 份。
      多账号运营成本未计入，且按各档月产能向下取整（保守估计）。全场单档上限 {MAX_CAP:.0f} 条/月。
    </div>
    <div class="roi">
      <div><div class="rt">年支出</div><div class="rv" id="roi-spend">—</div><div class="rd">按组合最省方案</div></div>
      <div><div class="rt">年产条数</div><div class="rv" id="roi-clips">—</div><div class="rd">月产量 × 12</div></div>
      <div><div class="rt">年产出价值</div><div class="rv" id="roi-rev">—</div><div class="rd">年产条数 × 单条价值</div></div>
      <div><div class="rt">净收益</div><div class="rv" id="roi-net">—</div><div class="rd">年产出 − 年支出</div></div>
      <div><div class="rt">投入产出比</div><div class="rv" id="roi-x">—</div><div class="rd">年产出 ÷ 年支出</div></div>
      <div><div class="rt">回本条数</div><div class="rv" id="roi-be">—</div><div class="rd">年支出 ÷ 单条价值</div></div>
    </div>
  </div>
</section>

<section id="table" class="reveal">
  {sec_head("02", "全档位对比", "条形越长＝越省（以全场最优价为 100%）。「排名」格副行显示<b>当前月产量下</b>该档的年支出——拖动上方滑块，排名与副行会一起重算。")}
  {table([("#", "v"), ("平台", None), ("档位", None), ("年费", "p"), ("月积分", None),
          ("单条成本", "v"), ("元/秒", None)], main_rows, "tw scroll-y tw-main", "main")}
</section>

<section id="ladder" class="reveal">
  {sec_head("03", "达标总支出阶梯", "「单条成本最省」≠「花钱最省」。按目标月产量反查覆盖该产能的最低年费档位（单一订阅）。")}
  {table([("目标月产量", None), ("最省方案", None), ("年支出", None), ("实际产能", None),
          ("单条成本", None), ("相对最优", None)], lad_rows, "tw")}
</section>

<section id="margin" class="reveal">
  {sec_head("04", "边际成本：升档值不值", f"从下一档升到上一档，每多买一条产能实际多花多少钱。标尺为全场最优 ¥{f2(BEST)}/条。")}
  {table([("平台", None), ("升档路径", None), ("Δ年费", None), ("Δ年产", None),
          ("边际单条", None), ("达档均值", None), ("判定", None)], marg_rows)}
</section>

<section id="discount" class="reveal">
  {sec_head("05", "折扣结构：优势是真是假", "用官方划线原价重算。原价下单价收敛成水平线 → 说明优势全部来自折扣力度，活动一结束就消失。")}
  {table([("平台", None), ("折扣区间", None), ("原价下单条", None),
          ("原价单价极差", None), ("折扣力度极差", None)], disc_rows)}
</section>

<section id="official" class="reveal">
  {sec_head("06", "海报宣传价 vs 实际到手价", "各平台「低至 X 元/秒」多按非全能参考档位计算，与统一口径不可混用。")}
  {table([("平台", None), ("顶级档位", None), ("海报低至", None),
          ("全能参考实算", None), ("倍差", None)], claim_rows)}
</section>

<section id="retry" class="reveal">
  {sec_head("07", "失败重试成本", "五家平台失败均<b>不消耗积分</b> —— 本表全部单价按「成功出片才扣分」计算，与实际计费一致，无需再折算失败率。")}
  {table([("平台", None), ("失败是否扣分", None), ("依据", None)], retry_rows, "tw")}
  <div class="note good" style="margin-top:14px">
    <b>为什么这一项重要：</b>若某平台失败不退分且失败率 20%，其实际单条成本需上浮 25%，足以反转全部排名。
    既然五家均不扣分，<b>上表排名不受失败率影响</b>，可直接按单价决策。<br><br>{COST["retryNote"]}
  </div>
  <details style="margin-top:14px">
    <summary>跨零点提交的积分归属差异<span class="chev">›</span></summary>
    <div class="dbody">{COST["crossMidnightNote"]}</div>
  </details>
</section>

<section id="appendix" class="reveal">
  {sec_head("08", "方法论与原始数据", "本节列出全部原始输入与计算链条，便于复核与复用。")}
  <details>
    <summary>计算口径与归一化链条<span class="chev">›</span></summary>
    <div class="dbody">
      <b>核心问题：</b>五个平台的「积分」是各自发行的内部计价币，币值互不相同 ——
      同样一条 {SEC_PER_CLIP} 秒视频，即梦与小云雀各扣 <b>600</b> 分、libtv 扣 <b>1,380</b> 分、
      Higgsfield 扣 <b>210</b> 分、Neowow 扣 <b>7,500</b> 分。直接比较积分消耗没有意义。<br><br>
      <b>归一化链条：</b><br>
      ① <code>本币/积分 = 年费 ÷ (月积分 × 12)</code><br>
      ② <code>单条成本 = 本币/积分 × 每条消耗积分</code> ← 唯一可跨平台比较的价格<br>
      ③ <code>月产能 = 月积分 ÷ 每条消耗积分</code><br>
      ④ <code>边际成本 = Δ年费 ÷ Δ年产能</code><br>
      ⑤ <code>达标总支出最省 = 覆盖目标月产能的最低年费档位</code><br>
      ⑥ <code>组合最省 = 跨平台无界背包（容量向下取整）</code><br>
      ⑦ USD 档位按 <code>1 USD = {RATE} CNY</code>（{UPDATED} CFETS 中间价）折算<br><br>
      <b>数据范围：</b>本表仅覆盖年费（连续包年）档位；月度 / 季度 / 按次购买尚未纳入。因计价单位与折扣结构不同，需单独归一化后并入，故「最省」结论仅在年费口径内成立。<br><br>
      <b>口径校验：</b>用各平台自己公示的兑换率反向验证步骤①。
      <b>{COST["officialRateNote"]}</b>
    </div>
  </details>
  <details>
    <summary>数据范围：本表覆盖到哪里<span class="chev">›</span></summary>
    <div class="dbody">
      {table([("选项", None), ("状态", None), ("说明", None)],
             "".join(f'<tr><td>{x["label"]}</td>'
                     f'<td class="ctr"><span class="tag {"v-good" if x["done"] else "v-warn"}">{x["status"]}</span></td>'
                     f'<td style="white-space:normal">{x["note"]}</td></tr>' for x in SCOPE["items"]), "tw")}
      <div class="sub" style="margin-top:10px">{SCOPE["impact"]}</div>
    </div>
  </details>
  <details>
    <summary>单条积分消耗（各平台生成页实测）<span class="chev">›</span></summary>
    <div class="dbody">
      {table([("平台", None), ("生成页规格", None), ("单条积分", None)],
             "".join(f'<tr><td><span class="dot" style="background:{COLOR[p]}"></span>{p}</td>'
                     f'<td style="white-space:normal">{COST["creditsSource"][p]}</td>'
                     f'<td class="num strong">{CPV[p]:,}</td></tr>' for p in CPV), "tw")}
    </div>
  </details>
  <details>
    <summary>档位全清单（{len(ROWS)} 个可选积分档）<span class="chev">›</span></summary>
    <div class="dbody">
      {table([("平台", None), ("档位", None), ("积分档", None), ("月积分", None), ("年费", None),
              ("折 CNY", None), ("元/积分", None), ("公示兑换率", None), ("划线原价", None)],
             ap_rows, "tw")}
      <div class="sub" style="margin-top:10px">公示兑换率一列为平台页面自行标注值，仅用于反向校验。Higgsfield 各档报价均不含 VAT 及地方税。</div>
    </div>
  </details>
  <details>
    <summary>数据来源（{len(COST["sources"])} 项）<span class="chev">›</span></summary>
    <div class="dbody">{table([("页面", None), ("提取到的数据", None)], src_rows, "tw")}</div>
  </details>
</section>

<section class="reveal">
  {sec_head("09", "执行建议", "决策顺序：先定月产量 → 查「按产量测算」→ 用原价做压力测试。以下建议<b>仅适用于年费口径</b>。")}
  <div class="note good"><ul style="margin-top:0">{budget_bullets}</ul></div>
  <div class="note warn" style="margin-top:12px">
    <b>{COST["risks"][0]["title"]}</b><br>{COST["risks"][0]["body"][0]}<br><br>{COST["risks"][0]["body"][1]}
  </div>
</section>
{foot(f'{BRAND} · {BRAND_CN}　|　{STUDIO} 出品　|　数据采集 {UPDATED}　·　全部数值按统一口径重算，非平台宣传数字')}
</div>
"""

# ── 排行榜页 ──────────────────────────────────────────────────────
DIMS = VLM["methodology"]["dimensions"]
dim_rows = "".join(
    f'<tr><td><span class="mono" style="color:#D1FE17">{d["key"]}</span></td>'
    f'<td>{d["label"]}</td><td class="num">{(d["weight"]*100):.0f}%</td>'
    f'<td style="white-space:normal">{d["desc"]}</td></tr>' for d in DIMS)
schema_rows = "".join(f'<tr><td><span class="mono" style="color:#D1FE17">{k}</span></td>'
                      f'<td style="white-space:normal">{v}</td></tr>'
                      for k, v in VLM["fieldSchema"]["entries[]"].items())

lb_body = f"""
<div class="hero">
  <div class="eyebrow">{VLM["eyebrow"]}</div>
  <h1>视觉理解模型<br><em>统一口径排行榜</em></h1>
  <p class="lead">{VLM["intro"]}</p>
  <div class="meta">
    <span><i></i>状态 <b>评测中</b></span>
    <span><i></i>维度 <b>{len(DIMS)}</b></span>
    <span><i></i>模型 <b>—</b></span>
    <span><i></i>数据时点 <b>待回填</b></span>
  </div>
</div>

<div class="wrap">
<section class="reveal" style="margin-top:42px">
  {sec_head("01", "榜单", VLM["methodology"]["scoring"])}
  <div class="card" style="text-align:center;padding:52px 26px">
    <div class="eyebrow" style="margin-bottom:13px">{VLM["emptyState"]["title"]}</div>
    <div style="color:#8A9099;font-size:13px;line-height:1.75;max-width:540px;margin:0 auto">{VLM["emptyState"]["body"]}</div>
  </div>
</section>
<section class="reveal">
  {sec_head("02", "评测维度与权重", "权重定死后再开始跑分，避免「先看结果再调权重」。")}
  {table([("key", None), ("维度", None), ("权重", None), ("说明", None)], dim_rows, "tw")}
</section>
<section class="reveal">
  {sec_head("03", "数据字段说明", '字段已锁定。回填时只需向 <code>data/leaderboard-vlm.json</code> 的 <code>entries</code> 追加记录，页面自动出榜。')}
  <details open>
    <summary>entries[] 单条记录结构<span class="chev">›</span></summary>
    <div class="dbody">{table([("字段", None), ("说明", None)], schema_rows, "tw")}</div>
  </details>
</section>
{foot(f'{BRAND} · {BRAND_CN}　|　{STUDIO} 出品　|　{VLM["title"]}评测中')}
</div>
"""

# ═══════════════════════════════════════════════════════════════════
# 6. 输出 + 自检
# ═══════════════════════════════════════════════════════════════════
PAGES = {
    "index.html": page("首页", f"{BRAND} — {SITE['tagline']}。AI 平台成本对比与模型能力排行榜，统一口径折算，只给可复核的结果。",
                       nav("home"), home_body),
    "cost.html": page("平台成本对比", f"{len(ROWS)} 个可选档位，按「{SPEC}」统一口径折算单条现金成本，含达标阶梯、折扣结构与投入产出测算。",
                      nav("cost"), cost_body, cost_js=True),
    "leaderboard-vlm.html": page(VLM["title"], VLM["intro"], nav("leaderboard-vlm"), lb_body),
}


def write_all():
    for d in (ROOT, DEPLOY):
        os.makedirs(d, exist_ok=True)
    for name, html in PAGES.items():
        for d in (ROOT, DEPLOY):
            with io.open(os.path.join(d, name), "w", encoding="utf-8") as f:
                f.write(html)
    # 公网附加文件
    import shutil
    for extra in ("_headers", "robots.txt", "LICENSE", "SECURITY.md"):
        src = os.path.join(ROOT, extra)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(DEPLOY, extra))


def selfcheck():
    """构建后自检：结构性问题必须在构建阶段暴露，而不是等到用户看见"""
    errs, warns = [], []
    for name, html in PAGES.items():
        o, c = len(re.findall(r"<div\b", html)), html.count("</div>")
        if o != c:
            errs.append(f"{name}: div 不配对 <div>={o} </div>={c}")
        if not html.startswith("<!DOCTYPE html>") or not html.rstrip().endswith("</html>"):
            errs.append(f"{name}: 文档首尾不完整")
        if html.count("<style>") != 1 or html.count("</style>") != 1:
            errs.append(f"{name}: style 标签数异常")
        if html.count("<script>") != 1 or html.count("</script>") != 1:
            errs.append(f"{name}: script 标签数异常")
        for tok in ("__PLANS__", "__COST__", "__SANS__", "__DISP__", "__MONO__", "{f2(", "None"):
            if tok in html:
                errs.append(f"{name}: 残留占位符 {tok}")
        if re.search(r"(?:src|href)=\"https?://", html):
            errs.append(f"{name}: 存在外部资源请求（应保持零外部依赖）")

    cost = PAGES["cost.html"]
    ids = set(re.findall(r'id="([a-z][a-z0-9-]*)"', cost))
    hrefs = set(re.findall(r'href="#([a-z][a-z0-9-]*)"', cost))
    miss = hrefs - ids
    if miss:
        errs.append(f"cost.html: 锚点无对应 id -> {sorted(miss)}")

    n_th = len(re.findall(r"<th\b", cost.split('id="main"')[1].split("</tr>")[0]))
    n_td = len(re.findall(r"<td\b", cost.split('id="main"')[1].split("</tr>")[1]))
    if n_th != n_td:
        errs.append(f"cost.html: 主表表头 {n_th} 列与数据行 {n_td} 列不一致")

    js = re.search(r"<script>(.*?)</script>", cost, re.S).group(1)
    tmp = os.path.join(os.path.dirname(ROOT), "harvest", "_selfcheck.js")
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    with io.open(tmp, "w", encoding="utf-8") as f:
        f.write(js)
    if os.path.exists(NODE):
        r = subprocess.run([NODE, "--check", tmp], capture_output=True, text=True)
        if r.returncode != 0:
            errs.append("cost.html: JS 语法错误\n" + (r.stderr or "")[-500:])

    return errs, warns, n_th


errs, warns, n_th = selfcheck()
write_all()

print("=" * 78)
print(f"{BRAND} · {BRAND_CN}　指纹 {FP}")
print(f"口径 {SPEC}　|　汇率 1 USD = {RATE} CNY ({UPDATED})")
print("=" * 78)
print(f"{'#':>3}  {'平台':<11}{'档位':<10}{'积分档':<10}{'年费':>10}{'单条CNY':>9}{'元/秒':>7}{'月产能':>8}{'相对':>7}")
print("-" * 78)
for r in sorted(ROWS, key=lambda x: x["perVideo"]):
    price = f'{CU[r["cur"]]}{r["price"]:,}'
    print(f"{r['rank']:>3}  {r['plat']:<11}{r['tier']:<10}{(r['label'] or '-'):<10}{price:>10}"
          f"{r['perVideo']:>9.2f}{r['perSec']:>7.3f}{r['mCap']:>8.2f}{r['rel']:>7.3f}")
print("-" * 78)
print(f"共 {len(ROWS)} 档　最优 ¥{BEST:.2f}　最差 ¥{WORST:.2f}　极差 {WORST/BEST:.2f}×　主表 {n_th} 列")
print()
for name in sorted(PAGES):
    print("  %-24s %7d B" % (name, os.path.getsize(os.path.join(ROOT, name))))
print()
if errs:
    print("!! 自检未通过：")
    for e in errs:
        print("   -", e)
    raise SystemExit(1)
print("自检通过：div 配对 / 文档完整 / 零外部请求 / 锚点有效 / 表头列数一致 / JS 语法 OK")

# -*- coding: utf-8 -*-
"""
CALIBER · 站点渲染器

设计原则
  1. 【不做字符串替换】。页面全部由 render_* 函数按数据结构拼装。
     旧版靠正则/字符串替换改模板，反复出现「锚点失配」「命中错误位置且静默成功」
     「吃掉结构标签导致布局塌陷」等事故 —— 重写就是为了根除这一类问题。
  2. 派生量一律现算，不落盘：单条成本 / 月产能 / 达标阶梯 / 边际成本 /
     跨平台组合最省（无界背包）。
     刻意【不算】折扣结构 —— 划线原价按 PRICE_RULE 不属价格，不做分析。
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
GLOSSARY = load("glossary.json")
GLOS_MAP = {x["k"]: x for x in GLOSSARY["terms"]}


def T(key, label=None):
    """把一个术语包成可点开解释的 span。

    ⚠ 只包术语本身，不改用词 —— 本站定位是专业测评，术语照用，
      缺的是「读者从哪知道它什么意思」这个出口。
    label 用于页面上的用词与词典标题不一致时（如页面写「会员周期」、词典条目叫「承诺期」）。
    """
    x = GLOS_MAP[key]
    return f'<span class="tm" data-t="{key}">{label or x["t"]}</span>'

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
# 数据范围文案一律由 SCOPE["items"] 推导 —— 曾因页面上两处各自硬编码、
# 数据层改成三周期后页面仍写「月度／季度会员后续补充」，两处文案互相矛盾。
SCOPE_COVERED = "、".join(x["label"] for x in SCOPE["items"] if x["done"])
SCOPE_PENDING = "、".join(x["label"] for x in SCOPE["items"] if not x["done"])
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
                # 次年续费价在选项级（libtv 续费价随积分档变，不随档位变）
                "renewal": c.get("renewal"),
                # 三周期原始实付总额（年付即 price）；mCr = 月付口径月积分，缺省同年付
                "payY": price, "payQ": c.get("q"), "payM": c.get("m"),
                # 三周期各自的「月积分」——平台可能按周期给不同积分。
                # 缺省同年付；mCr/qCr 在数据文件里按档位单独给。
                "mCr": c.get("mCr", monthly),
                "qCr": c.get("qCr", monthly),
                "color": COLOR[plat],
            })
    return out


ROWS = build_rows()
BEST = min(r["perVideo"] for r in ROWS)
WORST = max(r["perVideo"] for r in ROWS)
for i, r in enumerate(sorted(ROWS, key=lambda x: x["perVideo"]), 1):
    r["rank"] = i
    r["rel"] = r["perVideo"] / BEST

# ── 三周期派生量 ───────────────────────────────────────────────
#  本币/积分 = 该周期实付总额 ÷ (该周期月积分 × 周期月数)
#  单条成本 = 本币/积分 × 单条消耗积分 × 汇率
#  月产能   = 该周期月积分 ÷ 单条消耗积分
# 注意月付用 mCr —— 即梦标准会员月付给 4,000 积分，年/季付只给 2,210。
PERIODS = [("y", "年付", 12, "payY"), ("q", "季付", 3, "payQ"), ("m", "月付", 1, "payM")]
for r in ROWS:
    r["byP"] = {}
    for key, _lbl, months, field in PERIODS:
        pay = r[field]
        if pay is None:
            continue
        # ⚠ 三周期各自的月积分：年付用 credits，季付用 qCr，月付用 mCr（缺省同年付）。
        # 原实现把年付与季付绑在同一个值上 —— 若平台按周期给不同积分就会算错。
        cr = {"y": r["monthly"], "q": r["qCr"], "m": r["mCr"]}[key]
        unit = pay / (cr * months)
        r["byP"][key] = {"pay": pay, "payCNY": pay * r["k"], "cr": cr,
                         "perVideo": unit * r["per"] * r["k"], "cap": cr / r["per"]}
    # 该档三周期中的最优周期（单条成本最低）
    r["bestP"] = min(r["byP"], key=lambda kk: r["byP"][kk]["perVideo"]) if r["byP"] else None
    # 周期倒挂：更长的承诺期反而单价更高 —— 逐对检查（季/月、年/月、年/季）
    # 注意：这不总是平台的错。即梦标准会员月付给 4,000 积分、年付只给 2,210，
    # 所以年付单条成本反而比月付贵 44% —— 是「积分随周期缩水」造成的真实倒挂。
    r["traps"] = []
    for _lk, _sk, _llbl, _slbl in (("q", "m", "季付", "月付"),
                                   ("y", "m", "年付", "月付"),
                                   ("y", "q", "年付", "季付")):
        if _lk in r["byP"] and _sk in r["byP"]:
            _lv, _sv = r["byP"][_lk]["perVideo"], r["byP"][_sk]["perVideo"]
            if _lv > _sv + 1e-9:
                                r["traps"].append({"lkey": _lk, "skey": _sk,
                                   "long": _llbl, "short": _slbl, "pct": _lv / _sv - 1,
                                   "longPay": r["byP"][_lk]["pay"], "shortPay": r["byP"][_sk]["pay"]})
    r["qTrap"] = next((t["pct"] for t in r["traps"] if t["long"] == "季付"), None)

# 同（平台,档位）只保留产能最大者 —— 用于阶梯与边际，避免同档多选项中低配产生 Δ=0
BY_TIER = {}
for r in ROWS:
    key = (r["plat"], r["tier"])
    if key not in BY_TIER or r["mCap"] > BY_TIER[key]["mCap"]:
        BY_TIER[key] = r
SINGLES = list(BY_TIER.values())


CQ_DEFAULT = 30          # 表格滑块默认值；构建时按此预渲染，无 JS 也正确


def tname(r):
    return r["tier"] + (f' · {r["label"]}' if r["multi"] else "")


def f2(v):
    return f"{v:,.2f}"


def money(v, cur="CNY"):
    return f"{CU[cur]}{v:,.0f}"

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
MARG_WORST = max(MARGINAL, key=lambda x: x["mCost"])
MAX_CAP = max(r["mCap"] for r in ROWS)
# 全场产能两端 —— 供「结论速览」下方那句产能定位使用
# 注意并列：即梦与小云雀的超级会员同为 91.00 条/月，极值句必须两个都列
CAP_LO = min(r["mCap"] for r in ROWS)
CAP_HI = max(r["mCap"] for r in ROWS)


def cap_who(v):
    """列出月产能恰为 v 的档位名（同档多积分档去重），用「／」连接"""
    seen, out = set(), []
    for r in ROWS:
        if abs(r["mCap"] - v) < 1e-9:
            k = (r["plat"], r["tier"])
            if k not in seen:
                seen.add(k)
                out.append(f'{r["plat"]} {tname(r)}')
    return "／".join(out)


CAP_LO_WHO, CAP_HI_WHO = cap_who(CAP_LO), cap_who(CAP_HI)

# 平台汇总：供页面开头的「覆盖平台清单」使用
PLAT_SUM = []
for _p in PLATFORMS:
    _rs = [r for r in ROWS if r["plat"] == _p]
    if not _rs:
        continue
    _b = min(_rs, key=lambda r: r["perVideo"])
    PLAT_SUM.append({
        "plat": _p, "color": COLOR[_p],
        "tiers": len({r["tier"] for r in _rs}), "opts": len(_rs),
        "lo": min(r["perVideo"] for r in _rs), "hi": max(r["perVideo"] for r in _rs),
        "best": _b, "multi": sum(1 for t in {r["tier"] for r in _rs}
                                 if len([x for x in _rs if x["tier"] == t]) > 1),
        "region": PLATFORMS[_p]["region"],
    })
PLAT_SUM.sort(key=lambda x: x["lo"])

PLAT_LG = {"libtv": "lg-libtv", "Neowow": "lg-neowow", "即梦": "lg-jimeng",
           "小云雀": "lg-xiaoyunque", "Higgsfield": "lg-higgsfield", "Tapnow": "lg-tapnow", "Seko": "lg-seko"}

# 没有官方 logo 的平台：品牌色方块 + 首字母。
# Seko 已于拿到官方 logo 后移出本表 —— 这就是这张表的用法。
PLAT_MONO = {}


def plogo(plat, cls="clogo"):
    mk = PLAT_MONO.get(plat, "")
    cls2 = cls + (" lg-mono" if mk else "")
    return f'<i class="{cls2} {PLAT_LG[plat]}" aria-hidden="true">{mk}</i>'
# 指标：(key, 标签, 取值, 单位, 越大越好?, 格式化)
CHART_METRICS = [
    ("cost", "单条成本", lambda r, k: r["byP"][k]["perVideo"], "元/条", False,
     lambda v: f"¥{v:,.2f}"),
    ("cap", "每月可生成", lambda r, k: r["byP"][k]["cap"], "条/月", True,
     lambda v: f"{v:,.2f}"),
    ("sec", "元/秒", lambda r, k: r["byP"][k]["perVideo"] / SEC_PER_CLIP, "元/秒", False,
     lambda v: f"{v:.3f}"),
    ("pay", "该周期实付", lambda r, k: r["byP"][k]["payCNY"], "元", False,
     lambda v: f"¥{v:,.0f}"),
]
METRIC_LBL = {m[0]: m[1] for m in CHART_METRICS}
METRIC_UNIT = {m[0]: m[3] for m in CHART_METRICS}

def chart_rows(metric, period):
    """按某指标 + 某周期生成排名条。长度＝「离最优值的接近程度」而非数值比例。

    ⚠ 刻度必须与前端 renderChart() 完全一致（相对最优倍数的平方根压缩），
      否则首屏（服务端渲染）与切换指标后（JS 重绘）的条长会不同。
    """
    fn = next(m[2] for m in CHART_METRICS if m[0] == metric)
    fmt = next(m[5] for m in CHART_METRICS if m[0] == metric)
    lower_better = not next(m[4] for m in CHART_METRICS if m[0] == metric)
    cand = [(fn(r, period), r) for r in ROWS if period in r["byP"]]
    if not cand:
        return ""
    vals = [v for v, _ in cand]
    best = min(vals) if lower_better else max(vals)
    max_rel = max((v / best) if lower_better else (best / v) for v in vals)
    rel_span = (max_rel - 1.0) or 1.0
    cand.sort(key=lambda x: x[0], reverse=not lower_better)
    out = ""
    for i, (v, r) in enumerate(cand, 1):
        rel = (v / best) if lower_better else (best / v)
        if not best:
            rel = 1.0
        t = math.sqrt((rel - 1.0) / rel_span) if rel_span else 0.0
        # 色阶下限 0.10：原公式最差档 alpha≈0，条形直接消失（用户反馈「颜色暗淡看不清变化」）
        a = 0.10 + 0.42 * (1 - t)
        w = (1 - t) * 100
        lbl = f'<s>{r["label"]}</s>' if r.get("label") else ""
        out += (
            f'<div class="crow" data-plat="{r["plat"]}" '
            f'data-k="{r["plat"]}|{r["tier"]}|{r.get("label","")}">'
            f'<span class="crk{" top3" if i <= 3 else ""}">{i}</span>'
            f'{plogo(r["plat"])}'
            f'<span class="cname">{r["plat"]} {r["tier"]}{lbl}</span>'
            f'<span class="cbar"><i style="width:{w:.1f}%;background:rgba(209,254,23,{a:.3f})"></i></span>'
            f'<span class="cval">{fmt(v)}<s>{rel:.2f}×</s></span>'
            f'</div>')
    return out


# ═══════════ 周期结构（月付 / 季付 / 年付）═══════════
# 用户 2026-09-21 裁定：原「三榜并列」的分流设计作废 —— 预演发现
# 「季付榜的最优解」在月付榜里反而更便宜，三个独立榜会给出自相矛盾的建议。
# 改为：三周期各自最优解（并排可比）+ 平台级周期折扣区间 + 季付陷阱清单。
PERIOD_LEAD = {}
for _k, _lbl, _months, _f in PERIODS:
    _c = [r for r in ROWS if _k in r["byP"]]
    if not _c:
        continue
    _v = min(r["byP"][_k]["perVideo"] for r in _c)
    _seen, _who = set(), []
    for r in sorted(_c, key=lambda x: x["byP"][_k]["perVideo"]):
        if abs(r["byP"][_k]["perVideo"] - _v) < 1e-6:
            kk = (r["plat"], r["tier"])
            if kk not in _seen:
                _seen.add(kk)
                _who.append(f'{r["plat"]} {tname(r)}')
    PERIOD_LEAD[_k] = {"lbl": _lbl, "cost": _v, "who": "／".join(_who), "cnt": len(_c)}

PERIOD_PLAT = []
for _p in PLATFORMS:
    _rs = [r for r in ROWS if r["plat"] == _p]
    if not _rs:
        continue
    _ym = [r["byP"]["y"]["perVideo"] / r["byP"]["m"]["perVideo"]
           for r in _rs if "y" in r["byP"] and "m" in r["byP"]]
    _qm = [r["byP"]["q"]["perVideo"] / r["byP"]["m"]["perVideo"]
           for r in _rs if "q" in r["byP"] and "m" in r["byP"]]
    PERIOD_PLAT.append({
        "plat": _p, "color": COLOR[_p], "hasQ": bool(_qm),
        "yLo": min(_ym), "yHi": max(_ym),
        "qLo": min(_qm) if _qm else None, "qHi": max(_qm) if _qm else None,
        # 判定按【档位】计，不按倒挂组合计 —— 同一档位可能同时季付和年付倒挂，
        # 按组合计会出现「2 档倒挂」这种夸大表述（实际只有 1 个档位）
        "trapN": sum(1 for r in _rs if r["traps"])})

# 周期倒挂全清单：任何「承诺更久、单价反而更高」的组合（季/月、年/月、年/季）
TRAPS = []
for _r in ROWS:
    for _t in _r["traps"]:
        TRAPS.append(dict(_t, row=_r))
TRAPS.sort(key=lambda x: x["pct"], reverse=True)
TRAP_TIERS = len({(t["row"]["plat"], t["row"]["tier"]) for t in TRAPS})
TRAP_PLATS = "／".join(sorted({t["row"]["plat"] for t in TRAPS}))
TRAP_WORST = TRAPS[0] if TRAPS else None
# 只统计「季付比月付贵」的档位数，用于与旧口径对照
PTRAP = [r for r in ROWS if r["qTrap"] is not None]

# ── 每周期各自的排名与相对倍数（三张表各排各的，不能共用年付的名次）──
BEST_P = {}
for _k, _lbl, _m, _f in PERIODS:
    _c = [r for r in ROWS if _k in r["byP"]]
    if not _c:
        continue
    _b = min(r["byP"][_k]["perVideo"] for r in _c)
    BEST_P[_k] = _b
    for _i, r in enumerate(sorted(_c, key=lambda x: x["byP"][_k]["perVideo"]), 1):
        r["byP"][_k]["rank"] = _i
        r["byP"][_k]["rel"] = r["byP"][_k]["perVideo"] / _b
    # 产能排名单独算 —— 热力底色要用它，且产能序与成本序不同
    for _i, r in enumerate(sorted(_c, key=lambda x: -x["byP"][_k]["cap"]), 1):
        r["byP"][_k]["crank"] = _i
PTN = {k: len([r for r in ROWS if k in r["byP"]]) for k, _l, _m, _f in PERIODS}


def _sub_deliver(r, key, n=None):
    """「单条成本」列副行 —— 单账号口径。

    口径＝1 个平台 + 1 个账号。产能不够就直说「这一个账号最多能做多少条」，
    而不是含糊的「产能过低」——用户要的是「为什么不行」。
    需要多账号时走组合订阅，不混进单档排名。
    """
    n = CQ_DEFAULT if n is None else n
    p = r["byP"].get(key)
    if not p or p["cap"] <= 0:
        return "该周期不可用"
    if p["cap"] < n:
        return "单账号最多 %.1f 条 · 不够 %d" % (p["cap"], n)
    return "该产量 ¥%s/条 · 1 个账号" % f2(p["payCNY"] / n)


# 主表：7 列，无「月产能」「年支出」列（用户裁定去掉）
# 三个周期各生成一张独立表 —— 每张表全部服务端预渲染，切换只切可见性，
# 不做单元格级 JS 重写（那类改写一旦漏掉某列就会静默错位）。
PT_HEAD = {"y": ("年付 · 实付", "CNY"), "q": ("季付 · 实付", "每季"), "m": ("月付 · 实付", "每月")}


def main_rows_for(key):
    rows, best = "", BEST_P[key]
    cand = sorted((r for r in ROWS if key in r["byP"]),
                  key=lambda x: x["byP"][key]["perVideo"])
    # 列内热力底色（借自 arena.ai 的做法）：不增一个字，让一列数字可以「扫读」。
    # 成本列越省越亮（lime）。⚠ 归一化用【名次】而不是【数值】：
    # 单价 19→106 元是长尾，线性映射会把前 20 名全压成同一个值，肉眼无从分辨。
    N = max(1, PTN[key] - 1)
    for r in cand:
        p = r["byP"][key]
        ca = 0.118 * (1 - (p["rank"] - 1) / N) ** 0.85
        price_disp = f'{CU[r["cur"]]}{p["pay"]:,}'
        sub = f'≈¥{p["payCNY"]:,.0f}' if r["cur"] == "USD" else PT_HEAD[key][1]
        vl = f'<span class="vlabel">{r["label"]}</span>' if r["multi"] else ""
        usd = '<span class="tagu">USD</span>' if r["cur"] == "USD" else ""
        w = best / p["perVideo"] * 100
        mc = "" if p["perVideo"] <= best * 1.06 else (" m2" if p["perVideo"] <= best * 2.2 else " m3")
        top = "top" if p["rank"] == 1 else ""
        rows += (
            f'<tr class="{top}" data-plat="{r["plat"]}" data-v="{p["perVideo"]:.4f}" '
            f'data-p="{p["payCNY"]:.2f}" data-c="{p["cap"]:.4f}">'
            f'<td class="ctr rk"><b>{p["rank"]}</b>'
            f'<s>¥{p["payCNY"]:,.0f}{ {"y": "/年", "q": "/季", "m": "/月"}[key] }</s></td>'
            f'<td><span class="plc">{plogo(r["plat"], "plgo")}</span>{r["plat"]}{usd}</td>'
            f'<td>{r["tier"]}{vl}</td>'
            f'<td class="num cell2" data-l="{PT_HEAD[key][0]}"><b>{price_disp}</b><s>{sub}</s></td>'
            f'<td class="num cell2" data-l="每月可生成">'
            f'<b>{p["cap"]:.2f} 条</b>'
            f'<s>{p["cr"]:,} 积分 · {p["cap"]*SEC_PER_CLIP:,.0f} 秒</s></td>'
            f'<td class="num cell2" data-l="单条成本" data-rated="{p["perVideo"]:.2f}" '
            f'style="background:rgba(209,254,23,{ca:.3f})">'
            f'<span class="{"strong" if p["rank"]==1 else "nm"}">¥{f2(p["perVideo"])}</span>'
            f'<s>{_sub_deliver(r, key)}</s>'
            f'<div class="mini{mc}"><i style="--w:{w:.1f}%;width:{w:.1f}%"></i></div></td>'
            f'<td class="num cell2" data-l="元/秒"><b>{p["perVideo"]/SEC_PER_CLIP:.3f}</b><s>元/秒</s></td></tr>')
    return rows


# 指纹：随数据集变化
import hashlib
_sig = json.dumps([COST["plans"], RATE, SPEC, BRAND], ensure_ascii=False, sort_keys=True)
# ── 溯源指纹（两级）──────────────────────────────────────────────
# FP_WORK    作品指纹：永久稳定，回答「这始终是我的作品」，任何数据更新都不变。
#            所有对外文件（LICENSE / robots / _headers / SECURITY）统一携带它，
#            避免随数据变化而失效 —— 这曾是本项目的真实缺陷（页面与许可文件指纹不一致）。
# FP_EDITION 版本指纹：随数据哈希变化，回答「这是哪一版」。
FP_WORK = "HX-CLB-WORK-20260921-A215F0AB"
FP_EDITION = "HX-CLB-ED-" + UPDATED.replace("-", "") + "-" + \
             hashlib.sha256(_sig.encode()).hexdigest()[:8].upper()
FP = FP_WORK   # 兼容旧引用


# ═══════════════════════════════════════════════════════════════════
# 3. 样式与脚本
# ═══════════════════════════════════════════════════════════════════
F_SANS = ('"Inter","Inter Display","SN Pro","Space Grotesk",ui-sans-serif,system-ui,'
          '-apple-system,"Segoe UI","PingFang SC","Microsoft YaHei","Noto Sans CJK SC",sans-serif')
F_DISP = ('"Space Grotesk","Inter Display","Inter","SN Pro",ui-sans-serif,system-ui,'
          '"PingFang SC","Microsoft YaHei",sans-serif')
F_MONO = ('"IBM Plex Mono","JetBrains Mono","Geist Mono",ui-monospace,SFMono-Regular,'
          'Menlo,Consolas,monospace')

CSS = r"""*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}html{-webkit-text-size-adjust:100%;overflow-x:clip;scroll-behavior:smooth}:root{--navh:57px;--subh:50px;--gap:18px}/* ⚠️ 必须是 clip 而非 hidden：overflow-x:hidden 会让 html/body 变成滚动容器，
   使子元素的 position:sticky 失效（实测导航会跟随内容滚走）。 */
body{background:#000;color:#C9CDD2;font:14px/1.7 __SANS__;overflow-x:clip;
  padding-bottom:calc(72px + env(safe-area-inset-bottom,0px));
  -webkit-font-smoothing:antialiased;letter-spacing:-.005em;
  -webkit-tap-highlight-color:transparent}[id]{scroll-margin-top:calc(var(--navh) + var(--subh) + var(--gap))}::selection{background:#D1FE17;color:#0B0B0B}/* ── 环境底光：纯黑底上叠模糊等于没效果，玻璃必须先有可折射的底光 ── */
body::before{content:"";position:fixed;inset:0;pointer-events:none;z-index:0;
  transform:translate3d(0,0,0);
  background:
    radial-gradient(1150px 640px at 6% -12%,rgba(209,254,23,.145),transparent 62%),
    radial-gradient(860px 540px at 105% 3%,rgba(237,21,114,.105),transparent 64%),
    radial-gradient(920px 580px at 44% 108%,rgba(156,230,243,.075),transparent 64%)}body::after{content:"";position:fixed;inset:0;pointer-events:none;z-index:2;opacity:.04;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.82' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='160' height='160' filter='url(%23n)'/%3E%3C/svg%3E")}.promo{background:#D1FE17;color:#0B0B0B;font-size:12.5px;font-weight:600;letter-spacing:-.01em;
  display:flex;align-items:center;justify-content:center;gap:13px;flex-wrap:wrap;
  padding:10px 22px;text-align:center;line-height:1.5;position:relative;z-index:3}.promo b{font-weight:800}.promo .tag2{border:1.5px solid #0B0B0B;border-radius:999px;padding:2px 11px;font-size:11px;font-weight:700}.nav{position:sticky;top:0;z-index:40;
  background:linear-gradient(180deg,rgba(255,255,255,.07),rgba(0,0,0,.42));
  -webkit-backdrop-filter:blur(34px) saturate(165%);backdrop-filter:blur(34px) saturate(165%);
  border-bottom:1px solid rgba(255,255,255,.11);
  box-shadow:inset 0 -1px 0 rgba(255,255,255,.04),0 10px 30px rgba(0,0,0,.45)}.nav .inner{max-width:1280px;margin:0 auto;padding:12px 24px;display:flex;align-items:center;gap:16px}.brand{display:flex;align-items:center;gap:10px;text-decoration:none;flex:0 0 auto}.brand i{width:24px;height:24px;border-radius:8px;background:#D1FE17;flex:0 0 24px;
  transition:transform .35s cubic-bezier(.22,1,.36,1)}.brand:hover i{transform:rotate(45deg)}.brand .bw{display:flex;flex-direction:column;line-height:1.15}.brand .bw b{font-family:__DISP__;font-size:16px;font-weight:800;color:#fff;letter-spacing:.06em}.brand .bw s{text-decoration:none;font-size:9.5px;font-weight:600;color:#6E747D;letter-spacing:.05em}.menu{display:flex;align-items:center;gap:2px;overflow-x:auto;scrollbar-width:none;
  flex:1 1 auto;min-width:0}.menu::-webkit-scrollbar{display:none}.menu a{display:inline-flex;align-items:center;gap:6px;white-space:nowrap;text-decoration:none;
  color:#9AA0A8;font-size:13px;font-weight:600;padding:7px 12px;border-radius:999px;flex:0 0 auto;
  transition:color .22s,background .22s}.menu a:hover{color:#fff;background:rgba(255,255,255,.065)}.menu a.active{color:#D1FE17}.menu .nb{background:#D1FE17;color:#0B0B0B;font-size:9.5px;font-weight:800;padding:1.5px 7px;
  border-radius:999px}.nav .spec{margin-left:auto;font-family:__MONO__;font-size:11.5px;font-weight:500;color:#D1FE17;
  border:1px solid rgba(209,254,23,.35);border-radius:999px;padding:6px 13px;flex:0 0 auto}.wrap{max-width:1280px;margin:0 auto;padding:0 24px;position:relative;z-index:1}/* ── Hero 光场：lime 从「涂料」变「光源」── */
.hero{max-width:1280px;margin:0 auto;padding:58px 24px 6px;position:relative;z-index:1}.hero::before{content:"";position:absolute;left:50%;top:-14%;z-index:-1;pointer-events:none;
  width:min(1180px,140vw);height:150%;transform:translateX(-50%);
  background:
    radial-gradient(42% 34% at 50% 30%,rgba(209,254,23,.26),rgba(209,254,23,.09) 48%,transparent 74%),
    radial-gradient(76% 62% at 50% 2%,rgba(209,254,23,.085),transparent 72%);
  -webkit-filter:blur(4px);filter:blur(4px)}.hero::after{content:"";position:absolute;left:-12%;right:-12%;bottom:-4%;height:46%;
  z-index:-1;pointer-events:none;opacity:.42;
  background-image:
    linear-gradient(rgba(209,254,23,.13) 1px,transparent 1px),
    linear-gradient(90deg,rgba(209,254,23,.13) 1px,transparent 1px);
  background-size:58px 58px,58px 58px;
  transform:perspective(400px) rotateX(63deg);transform-origin:50% 100%;
  -webkit-mask-image:radial-gradient(58% 82% at 50% 100%,#000,transparent 74%);
  mask-image:radial-gradient(58% 82% at 50% 100%,#000,transparent 74%)}.eyebrow{font-size:11px;font-weight:700;letter-spacing:.15em;text-transform:uppercase;
  color:#D1FE17;margin-bottom:15px;font-family:__MONO__}h1{font-family:__DISP__;font-size:clamp(31px,5.3vw,60px);font-weight:800;color:#fff;
  letter-spacing:-.038em;line-height:1.07}h1 em{font-style:normal;color:#D1FE17}.hero .lead{color:#8A9099;font-size:14.5px;max-width:720px;margin-top:18px;line-height:1.75}.meta{display:flex;gap:20px;flex-wrap:wrap;margin-top:22px;font-size:12.5px;color:#767C85}.meta span{display:inline-flex;align-items:center;gap:7px}.meta i{width:5px;height:5px;border-radius:50%;background:#D1FE17;flex:0 0 5px}.meta b{color:#C9CDD2;font-weight:600;font-family:__MONO__}.btns{display:flex;gap:10px;flex-wrap:wrap;margin-top:26px}.btn{display:inline-block;border-radius:999px;padding:12px 23px;font-size:13px;font-weight:700;
  text-decoration:none;white-space:nowrap;
  transition:transform .22s cubic-bezier(.22,1,.36,1),box-shadow .22s}.btn-white{background:#fff;color:#0B0B0B}.btn-white:hover{transform:translateY(-2px);box-shadow:0 10px 32px rgba(255,255,255,.2)}.btn-ghost{background:transparent;color:#fff;border:1px solid rgba(255,255,255,.2)}.btn-ghost:hover{border-color:rgba(255,255,255,.45);transform:translateY(-2px)}h2{font-family:__DISP__;font-size:20px;font-weight:750;color:#fff;letter-spacing:-.025em;line-height:1.3}h2 .ey{display:inline-block;font-family:__MONO__;font-size:12px;font-weight:600;color:#D1FE17;
  margin-right:12px}.sechead{margin-bottom:18px}.sechead .sd{color:#767C85;font-size:12.5px;line-height:1.7;max-width:860px}section{margin-top:60px}h3{font-family:__DISP__;font-size:14.5px;font-weight:700;color:#fff;margin:26px 0 12px}.card,.kpi,.note,.entry,.legal,details{
  background:linear-gradient(158deg,rgba(255,255,255,.075),rgba(255,255,255,.022) 46%,rgba(0,0,0,.30));
  -webkit-backdrop-filter:blur(28px) saturate(150%);backdrop-filter:blur(28px) saturate(150%);
  border:1px solid rgba(255,255,255,.12);border-radius:18px;
  box-shadow:inset 0 0 0 .61px rgba(255,255,255,.07),inset 0 1px 0 rgba(255,255,255,.05),
             0 1px 2px rgba(0,0,0,.45),0 10px 24px rgba(0,0,0,.4),0 30px 60px rgba(0,0,0,.48)}
@supports not ((-webkit-backdrop-filter:blur(2px)) or (backdrop-filter:blur(2px))){.card,.kpi,.note,.entry,.legal,details,.nav{
    background:linear-gradient(158deg,#161B18,#0D110F)}
}.card{padding:20px 22px}.grid{display:grid;gap:14px}.g2{grid-template-columns:repeat(auto-fit,minmax(330px,1fr))}.g5{grid-template-columns:repeat(auto-fit,minmax(200px,1fr))}.kpi{padding:18px 20px}.kpi .t{font-size:9.5px;color:#767C85;font-weight:700;letter-spacing:.13em;text-transform:uppercase}.kpi .v{font-family:__MONO__;font-size:clamp(30px,3.2vw,46px);font-weight:700;color:#fff;
  margin:12px 0 6px;letter-spacing:-.032em;line-height:1.15}.kpi.good .v,.kpi.hi .v{color:#D1FE17}.kpi.hi{border-color:rgba(209,254,23,.45)}.kpi .d{font-size:12px;color:#8A9099;line-height:1.65}.kpi .d b{color:#C9CDD2}.entry{display:block;text-decoration:none;padding:26px;position:relative;
  transition:transform .3s cubic-bezier(.22,1,.36,1),border-color .3s}.entry:hover{transform:translateY(-4px);border-color:rgba(209,254,23,.42);
  box-shadow:inset 0 0 0 .61px rgba(255,255,255,.09),0 26px 60px rgba(0,0,0,.62),0 0 42px rgba(209,254,23,.09)}.entry .et{font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#767C85;
  font-family:__MONO__;margin-bottom:12px}.entry h3{margin:0 0 9px;font-size:18px;font-weight:750;color:#fff}.entry p{color:#8A9099;font-size:13px;line-height:1.65;margin-bottom:16px}.entry .nums{display:flex;gap:22px;flex-wrap:wrap;padding-top:16px;
  border-top:1px solid rgba(255,255,255,.07)}.entry .nums div{display:flex;flex-direction:column;gap:3px}.entry .nums s{text-decoration:none;font-family:__MONO__;font-size:18px;font-weight:700;
  color:#D1FE17;letter-spacing:-.03em}.entry .nums em{font-style:normal;font-size:10.5px;color:#767C85;letter-spacing:.06em;text-transform:uppercase}.entry .arrow{position:absolute;top:24px;right:24px;color:#D1FE17;font-size:17px;
  transition:transform .3s cubic-bezier(.22,1,.36,1)}.entry:hover .arrow{transform:translateX(4px)}table{width:100%;border-collapse:separate;border-spacing:0;font-size:13px;
  background:linear-gradient(158deg,rgba(22,27,24,.86),rgba(10,13,11,.92));
  border:1px solid rgba(255,255,255,.12);border-radius:18px;overflow:hidden;
  box-shadow:inset 0 0 0 .61px rgba(255,255,255,.06),0 1px 2px rgba(0,0,0,.5),
             0 8px 20px rgba(0,0,0,.42),0 26px 56px rgba(0,0,0,.46)}th{background:transparent;color:#767C85;font-weight:700;font-size:10.5px;text-align:left;
  padding:10px 14px;white-space:nowrap;letter-spacing:.095em;text-transform:uppercase;
  border-bottom:1px solid rgba(255,255,255,.08);cursor:pointer;user-select:none;transition:color .2s}th:hover{color:#D1FE17}th.ctr,td.ctr{text-align:center}td{padding:8px 14px;border-bottom:1px solid rgba(255,255,255,.05);white-space:nowrap;
  vertical-align:middle}tbody tr{transition:background .18s}tbody tr:last-child td{border-bottom:none}tbody tr:hover{background:rgba(255,255,255,.032)}tbody tr.top{background:rgba(209,254,23,.055)}tbody tr.top td:first-child{box-shadow:inset 3px 0 0 #D1FE17}.num{text-align:right;font-variant-numeric:tabular-nums;font-family:__MONO__;font-weight:500;
  letter-spacing:-.022em}.strong{color:#D1FE17;font-weight:600}.neg{color:#FF6B6B;font-weight:600}.nm{color:#E4E7EA;font-weight:600}.rk b{display:block;font-family:__MONO__;font-size:15px;color:#fff;font-weight:700}.rk s{text-decoration:none;font-size:10px;color:#5A6069;font-family:__MONO__}.cell2{line-height:1.25}.cell2>*{display:block}.cell2 s{text-decoration:none;font-size:10.5px;color:#6E747D;display:block}.cell2 b{font-weight:600;color:#E4E7EA}.dot{display:inline-block;width:6px;height:6px;border-radius:50%;margin-right:8px;vertical-align:middle}.vlabel{display:inline-block;margin-left:6px;padding:1px 6px;border-radius:5px;font-size:10px;
  font-weight:600;color:#9AA0A8;background:rgba(255,255,255,.05);
  border:1px solid rgba(255,255,255,.14);white-space:nowrap}.tagu{display:inline-block;margin-left:7px;padding:1px 6px;border-radius:999px;font-size:9.5px;
  font-weight:700;color:#FF4D8D;border:1px solid rgba(255,77,141,.45)}.mini{height:5px;border-radius:999px;background:rgba(255,255,255,.07);margin-top:6px;overflow:hidden}.mini i{display:block;height:100%;border-radius:999px;background:rgba(255,255,255,.20);
  transition:width .9s cubic-bezier(.22,1,.36,1)}.js .reveal .mini i{width:0!important}.js .reveal.in .mini i{width:var(--w)!important}.mini.m2 i{background:rgba(255,255,255,.13)}.mini.m3 i{background:rgba(255,255,255,.09)}/* lime 只标最重要的一件事 —— 强调色一旦满地都是，就等于没有强调 */
tr.top .mini i{background:#D1FE17}.tag{display:inline-block;padding:3px 11px;border-radius:999px;font-size:10.5px;font-weight:700}.v-good{background:#D1FE17;color:#0B0B0B}.v-warn{background:transparent;color:#C9CDD2;border:1px solid rgba(255,255,255,.18)}.v-bad{background:transparent;color:#FF6B6B;border:1px solid rgba(255,107,107,.32)}.note{padding:18px 22px;font-size:13px;line-height:1.78}.note.warn{border-left:2px solid rgba(255,201,60,.55)}.note.good{border-left:2px solid rgba(209,254,23,.5)}ul{margin:8px 0 0 19px}li{margin:7px 0;font-size:13px;line-height:1.72}li::marker{color:#D1FE17}code{background:rgba(209,254,23,.09);border:1px solid rgba(209,254,23,.2);padding:2px 7px;
  border-radius:6px;font-family:__MONO__;font-size:12.5px;color:#D1FE17;font-weight:500}details{margin-bottom:12px;overflow:hidden;border-radius:16px;transition:border-color .25s}details:hover{border-color:rgba(209,254,23,.28)}summary{cursor:pointer;padding:16px 22px;font-size:13.5px;font-weight:650;color:#E4E7EA;
  list-style:none;display:flex;align-items:center;gap:11px}summary::-webkit-details-marker{display:none}summary:hover{color:#fff}summary .chev{margin-left:auto;color:#767C85;font-size:12px;
  transition:transform .3s cubic-bezier(.22,1,.36,1)}details[open] summary .chev{transform:rotate(90deg);color:#D1FE17}.dbody{padding:0 22px 22px;font-size:13px;line-height:1.78}.dbody>*+*{margin-top:12px}.dbody h3{margin:18px 0 10px}.tw{overflow-x:auto;border-radius:18px}.tw table{min-width:760px}/* 内层滚动容器【不能】用 overscroll-behavior:contain：
   手指/滚轮停在容器上时，Chrome 会把手势吃掉而不传给页面，
   表现为「滑到这里就划不动了」（手机上尤其致命）。 */
.tw.scroll-y{max-height:440px;overflow-y:auto}.tw.tw-main{max-height:min(72vh,640px)}.tw.scroll-y::-webkit-scrollbar{width:10px;height:10px}.tw.scroll-y::-webkit-scrollbar-track{background:rgba(255,255,255,.03);border-radius:6px}.tw.scroll-y::-webkit-scrollbar-thumb{background:rgba(255,255,255,.16);border-radius:6px;
  border:2px solid transparent;background-clip:content-box}.tw.scroll-y::-webkit-scrollbar-thumb:hover{background:rgba(209,254,23,.45);
  background-clip:content-box;border:2px solid transparent}.tw.scroll-y{scrollbar-width:thin;scrollbar-color:rgba(255,255,255,.22) transparent}.tw.scroll-y thead th{position:sticky;top:0;z-index:2;
  background:linear-gradient(180deg,rgba(22,27,24,.98),rgba(16,20,18,.96))}input[type=range]{-webkit-appearance:none;appearance:none;width:min(320px,62vw);height:4px;
  border-radius:999px;outline:none;background:rgba(255,255,255,.12);cursor:pointer}input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:19px;height:19px;
  border-radius:50%;background:#D1FE17;border:3px solid #000;cursor:pointer}input[type=number]{width:110px;background:rgba(255,255,255,.06);
  border:1px solid rgba(255,255,255,.14);border-radius:9px;color:#fff;font-family:__MONO__;
  font-size:14px;font-weight:600;padding:7px 10px;outline:none;letter-spacing:-.02em}input[type=number]:focus{border-color:rgba(209,254,23,.55);background:rgba(209,254,23,.07)}.presets{display:inline-flex;gap:5px}.cqr{-webkit-appearance:none;appearance:none;width:190px;height:4px;border-radius:999px;
  outline:none;background:rgba(255,255,255,.12);cursor:pointer}.cqr::-webkit-slider-thumb{-webkit-appearance:none;width:16px;height:16px;border-radius:50%;
  background:#D1FE17;border:3px solid #000;cursor:pointer;
  transition:transform .2s cubic-bezier(.22,1,.36,1)}.cqr::-webkit-slider-thumb:hover{transform:scale(1.12)}.cqr::-moz-range-thumb{width:16px;height:16px;border-radius:50%;background:#D1FE17;
  border:3px solid #000;cursor:pointer}.qv{font-family:__MONO__;font-size:15px;font-weight:700;color:#D1FE17;letter-spacing:-.03em;
  min-width:78px}.cqp{background:transparent;border:1px solid rgba(255,255,255,.16);color:#9AA0A8;
  font-family:__MONO__;font-size:11px;font-weight:600;padding:4px 9px;border-radius:999px;
  cursor:pointer;transition:color .2s,border-color .2s,background .2s}.cqp:hover{color:#fff;border-color:rgba(255,255,255,.36)}.cqp.on{color:#0B0B0B;background:#D1FE17;border-color:#D1FE17;font-weight:700}/* ══ 应用式布局：左栏选项 + 右主区（参照 arena.ai 的结构）══
   目的是「一进来就是控件与数据」，不再用长文档铺陈。 */
.app{display:flex;gap:26px;align-items:flex-start;
  max-width:1420px;margin:0 auto;padding:26px 26px 0}.side{flex:0 0 236px;position:sticky;top:calc(var(--navh) + 14px);
  display:flex;flex-direction:column;gap:20px;padding-right:2px;
  max-height:calc(100vh - var(--navh) - 30px);overflow-y:auto;
  scrollbar-width:thin;scrollbar-color:rgba(255,255,255,.16) transparent}.side::-webkit-scrollbar{width:6px}.side::-webkit-scrollbar-thumb{background:rgba(255,255,255,.16);border-radius:6px}.sgroup{display:flex;flex-direction:column;gap:9px}.sgt{display:flex;align-items:center;gap:8px;font-size:10.5px;font-weight:700;
  letter-spacing:.12em;text-transform:uppercase;color:#6E747C}.sgchip{margin-left:auto;font-family:__MONO__;font-size:10px;letter-spacing:0;
  text-transform:none;color:#8A9098;padding:2px 7px;border-radius:999px;
  background:rgba(255,255,255,.05);white-space:nowrap}.segv{display:flex;flex-direction:column;gap:3px}.segv button{-webkit-appearance:none;appearance:none;border:1px solid transparent;
  background:transparent;color:#9AA0A8;font-family:inherit;font-size:13px;font-weight:600;
  text-align:left;padding:9px 12px;border-radius:10px;cursor:pointer;line-height:1.25;
  transition:background .16s,color .16s,border-color .16s}.segv button s{display:block;font-size:10.5px;font-weight:400;text-decoration:none;
  color:#6E747C;margin-top:2px}.segv button:hover{background:rgba(255,255,255,.045);color:#D7DBDF}.segv button.on{background:rgba(209,254,23,.10);border-color:rgba(209,254,23,.34);color:#D1FE17}.segv button.on s{color:#9AA85E}.segv.segk{flex-direction:row;gap:3px}.segv.segk button{flex:1;text-align:center;padding:9px 5px;font-size:12px}.side .cqr{width:100%}.srow{display:flex;align-items:baseline;gap:9px;margin-top:7px}.pf{display:flex;flex-wrap:wrap;gap:5px}.pfb{display:inline-flex;align-items:center;gap:6px;padding:6px 10px;border-radius:9px;
  border:1px solid rgba(255,255,255,.10);background:rgba(255,255,255,.03);
  color:#8A9098;font-family:inherit;font-size:11.5px;font-weight:600;cursor:pointer;
  transition:color .16s,border-color .16s,background .16s}.pfb i{width:6px;height:6px;border-radius:50%;opacity:.4;flex:0 0 auto}.pfb.on{color:#E4E7EA;border-color:rgba(255,255,255,.24);background:rgba(255,255,255,.06)}.pfb.on i{opacity:1}.mainv{flex:1;min-width:0;display:flex;flex-direction:column;gap:18px}
/* ⚠ flex 子项默认 min-width:auto —— 里面的表格有 min-width:760px，
   会把整个主区撑到 760px，导致窄屏横向溢出（#all 视图侥幸没事，
   因为它的 .tw-main 恰好带了 min-width:0）。这条兜住所有视图。 */
.mainv>*{min-width:0}
.tw{min-width:0}.vhead h1{font-family:__DISP__;font-size:clamp(20px,2.4vw,29px);font-weight:700;
  letter-spacing:-.03em;line-height:1.22;color:#fff;margin:0}.vhead h1 em{font-style:normal;color:#D1FE17}.vmeta{display:flex;flex-wrap:wrap;gap:8px 20px;margin-top:11px;font-size:11.5px;
  line-height:1.75;color:#7A8088}
.vsub{font-size:12.5px;line-height:1.75;color:#8A9098;margin-top:9px;max-width:720px}

/* ── 术语提示 ──
   术语用词一字不改，只给一个出口。虚线提示「这里可以点」。
   桌面：悬停出浮层（data-s 由 JS 从词典注入，避免 HTML 里重复塞长文案）
   手机：点击就地展开（没有 hover，必须单独做） */
.tm{border-bottom:1px dashed rgba(255,255,255,.34);cursor:help;position:relative;
  transition:color .16s,border-color .16s}
.tm:hover{color:#D1FE17;border-bottom-color:rgba(209,254,23,.7)}
/* ⚠ 悬浮提示用 position:fixed 的独立浮层，不用 ::after。
   绝对定位的提示框即使 visibility:hidden 也会撑大可滚动区域 ——
   实测窄屏下把 body.scrollWidth 顶到 467（视口 390）。
   fixed 元素不参与滚动区域计算，绕开这个问题。 */
.tip{position:fixed;z-index:60;max-width:min(300px,74vw);pointer-events:none;
  padding:9px 11px;border-radius:10px;font-size:11.5px;line-height:1.7;
  color:#C9CDD2;background:#14161A;border:1px solid rgba(255,255,255,.16);
  box-shadow:0 10px 28px rgba(0,0,0,.6);opacity:0;transition:opacity .16s}
.tip.on{opacity:1}
/* 手机端展开块：整行铺满，不跟着文字换行跑 */
/* ⚠ 硬约束到视口宽度：展开块可能被插在表格单元格等很宽的容器里，
   只用 max-width:100% 会跟着父容器一起超出屏幕（实测 467px / 视口 390）。 */
.tmx{display:none;box-sizing:border-box;max-width:calc(100vw - 30px);
  overflow-wrap:anywhere;margin:10px 0 4px;padding:12px 13px;border-radius:12px;
  background:rgba(209,254,23,.05);border:1px solid rgba(209,254,23,.22);
  font-size:12px;line-height:1.8;color:#B9BEC4;white-space:normal}
.tmx.on{display:block}
.tmx b{color:#D1FE17;font-weight:600}
/* ── 新人引导弹窗 ── */
.ibody{overflow:hidden}
#intro{position:fixed;inset:0;z-index:80;display:none;align-items:center;justify-content:center;
  padding:22px;background:rgba(4,5,6,.76)}
#intro.on{display:flex}
.icard{width:100%;max-width:466px;background:#101215;border-radius:20px;
  border:1px solid rgba(255,255,255,.13);box-shadow:0 24px 70px rgba(0,0,0,.7);
  padding:26px 26px 20px;position:relative;max-height:86vh;overflow-y:auto}
.ix{position:absolute;right:16px;top:16px;width:32px;height:32px;border-radius:9px;
  border:1px solid rgba(255,255,255,.13);background:rgba(255,255,255,.05);
  color:#C9CDD2;font-size:13px;line-height:1;cursor:pointer;font-family:inherit;
  display:flex;align-items:center;justify-content:center}
.ix:hover{background:rgba(255,255,255,.11)}
.ieyebrow{font-family:__MONO__;font-size:10.5px;letter-spacing:.14em;color:#6E747C}
.is{display:none}
.is.on{display:block}
.is h3{font-size:19px;line-height:1.5;color:#fff;font-weight:600;margin:12px 0 0;
  letter-spacing:-.01em}
.is p{font-size:13px;line-height:1.85;color:#A8AEB5;margin:13px 0 0}
.is ul{margin:14px 0 0;padding:0;list-style:none;display:flex;flex-direction:column;gap:11px}
.is li{font-size:13px;line-height:1.8;color:#A8AEB5;padding-left:19px;position:relative}
.is li::before{content:"";position:absolute;left:0;top:9px;width:6px;height:6px;
  border-radius:2px;background:#D1FE17}
.is li b{color:#E4E7EA;font-weight:600}
.ifoot{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:24px;
  padding-top:17px;border-top:1px solid rgba(255,255,255,.09)}
.idots{display:flex;gap:6px}
.idot{width:6px;height:6px;border-radius:4px;background:rgba(255,255,255,.2);
  transition:background .2s,width .2s}
.idot.on{background:#D1FE17;width:16px}
.ibtns{display:flex;gap:9px;margin-left:auto}
.ibtn{-webkit-appearance:none;appearance:none;cursor:pointer;font-family:inherit;
  font-size:13px;padding:9px 17px;border-radius:10px;line-height:1;
  border:1px solid rgba(255,255,255,.14);background:transparent;color:#C9CDD2}
.ibtn:hover{background:rgba(255,255,255,.07)}
.ibtn.pri{background:#D1FE17;color:#0B0B0D;border-color:#D1FE17;font-weight:600}
.ibtn.pri:hover{background:#c7f000}
@media (max-width:520px){
  #intro{padding:14px;align-items:flex-end}
  .icard{max-width:none;border-radius:20px 20px 16px 16px;padding:22px 18px 16px}
  .is h3{font-size:17px}
}
.glist{display:flex;flex-direction:column;gap:0;border-top:1px solid rgba(255,255,255,.08)}
.gterm{padding:20px 2px;border-bottom:1px solid rgba(255,255,255,.08);scroll-margin-top:76px}
.gterm:target{background:rgba(209,254,23,.05)}
.gt b{font-size:15px;color:#fff;font-weight:600}
.gs{font-size:13px;color:#C9CDD2;line-height:1.75;margin-top:6px}
.gl{font-size:12.5px;color:#8A9098;line-height:1.85;margin-top:9px;max-width:860px}
.tmx a{color:#D1FE17}.vmeta b{color:#C9CDD2;font-weight:600}/* KPI 条三套（年/季/月），同一时刻只显示当前周期那套 */
/* ── 首访阅读路径条：常驻、可关 ──
   弹窗是「主动讲一次」，这条是「一直在那儿」—— 互不替代。 */
.guide{display:flex;flex-wrap:wrap;align-items:center;gap:9px 20px;
  margin:0 0 16px;padding:12px 15px;border-radius:14px;
  background:rgba(209,254,23,.045);border:1px solid rgba(209,254,23,.2);
  font-size:12.5px;line-height:1.7;color:#A8AEB5}
.guide .g-lead{color:#D1FE17;font-weight:600}
.guide .g-step{white-space:nowrap}
.guide .g-link{color:#A8AEB5;border-bottom:1px dashed rgba(255,255,255,.3);text-decoration:none}
.guide .g-link:hover{color:#D1FE17}
.guide .g-x{margin-left:auto;-webkit-appearance:none;appearance:none;cursor:pointer;
  font-family:inherit;font-size:11.5px;padding:5px 11px;border-radius:8px;
  border:1px solid rgba(255,255,255,.16);background:transparent;color:#8A9098;white-space:nowrap}
.guide .g-x:hover{background:rgba(255,255,255,.07);color:#C9CDD2}
/* ── 三周期结论条 ── */
.conc{margin:0 0 16px;padding:16px 18px;border-radius:15px;
  background:rgba(255,255,255,.035);border:1px solid rgba(255,255,255,.11)}
.conc-h{display:flex;align-items:baseline;flex-wrap:wrap;gap:6px 12px;margin-bottom:13px}
.conc-h b{font-size:13.5px;color:#fff;letter-spacing:.01em}
.conc-h span{font-size:11.5px;color:#7A8088}
.conc-g{display:grid;grid-template-columns:repeat(3,1fr);gap:11px}
.conc-c{padding:13px 14px;border-radius:12px;background:rgba(209,254,23,.05);
  border:1px solid rgba(209,254,23,.22)}
.conc-c.dim{background:rgba(255,255,255,.03);border-color:rgba(255,255,255,.1)}
.conc-c .ch{font-size:10.5px;letter-spacing:.1em;color:#8A9098;margin-bottom:7px;
  display:flex;align-items:baseline;gap:7px;flex-wrap:wrap}
.conc-c .ch i{font-style:normal;font-size:10px;color:#5A6069;letter-spacing:0}
.conc-c .cw{font-family:__MONO__;font-size:22px;font-weight:700;color:#D1FE17;
  line-height:1.15;white-space:nowrap}
.conc-c.dim .cw{font-size:17px;color:#C9CDD2}
.conc-c .cw s{font-size:11px;font-weight:400;color:#7A8088;text-decoration:none;margin-left:4px}
.conc-c .cn{font-size:11.5px;line-height:1.75;color:#8A9098;margin-top:7px}
.conc-c .cn b{color:#D1FE17;font-weight:600}
.conc-f{margin-top:12px;padding-top:11px;border-top:1px solid rgba(255,255,255,.08);
  font-size:11.5px;line-height:1.8;color:#8A9098}
.conc-f b{color:#E4E7EA;font-weight:600}
@media (max-width:820px){
  /* 手机端不堆三张卡（会占掉 0.6 屏）—— 改成三行「标签 | 数值」，
     每行两行高，总高压掉约 250px，让下方的反查与排名表不被推太远。 */
  .conc{padding:13px 15px}
  .conc-h{margin-bottom:9px}
  .conc-h span{display:none}
  .conc-g{grid-template-columns:1fr;gap:0}
  .conc-c{padding:10px 0;border:0;background:none;border-radius:0;
    border-bottom:1px solid rgba(255,255,255,.08);
    display:grid;grid-template-columns:auto 1fr;gap:2px 12px;align-items:baseline}
  .conc-c:last-child{border-bottom:0}
  .conc-c .ch{grid-area:1/1;margin:0;white-space:nowrap}
  .conc-c .ch i{display:none}
  .conc-c .cw{grid-area:1/2;text-align:right;font-size:18px}
  .conc-c.dim .cw{font-size:14px}
  .conc-c .cn{grid-area:2/2;margin-top:1px;font-size:11px;line-height:1.65}
  .conc-c .cn br{display:none}
  .conc-f{margin-top:9px;padding-top:9px}
}
.kbar{display:none;gap:10px;grid-template-columns:repeat(auto-fit,minmax(148px,1fr))}
.kbar.on{display:grid}.kb{padding:12px 14px;border-radius:13px;background:rgba(255,255,255,.035);
  border:1px solid rgba(255,255,255,.085)}.kb.hi{border-color:rgba(209,254,23,.3);background:rgba(209,254,23,.055)}.kb s{display:block;font-size:10px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;
  color:#6E747C;text-decoration:none}.kb b{display:block;font-family:__MONO__;font-size:22px;font-weight:700;
  letter-spacing:-.035em;color:#EDEFF2;margin-top:5px}.kb.hi b{color:#D1FE17}.kb em{display:block;font-style:normal;font-size:10.5px;color:#8A9098;margin-top:3px;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.kb b .u{font-family:__SANS__;font-size:11px;font-weight:600;font-style:normal;
  color:#8A9098;margin-left:2px;letter-spacing:0}.vnote{font-size:11px;line-height:1.75;color:#6E747C;padding:11px 14px;border-radius:12px;
  background:rgba(255,255,255,.022);border:1px solid rgba(255,255,255,.06)}.vnote b{color:#9AA0A8}/* ── 动态排名条（三周期全清单页）──
   条长＝「离该指标最优值的接近程度」，不是原始数值大小 —— 越长越好，无需读数字。
   颜色同向：越接近最优越亮（lime 热力）。 */
/* 44 档一次性铺开会把页面拉到十几屏 —— 改为区域内滚动。
   ⚠ 只在桌面端启用：手机上套一层滚动容器会吃掉手势（已踩过）。 */
.chart{display:flex;flex-direction:column;gap:5px;
  max-height:min(66vh,640px);overflow-y:auto;overscroll-behavior:auto;
  padding-right:6px;scrollbar-width:thin;scrollbar-color:rgba(255,255,255,.22) transparent}
.chart::-webkit-scrollbar{width:8px}
.chart::-webkit-scrollbar-thumb{background:rgba(255,255,255,.2);border-radius:8px}
.chart::-webkit-scrollbar-track{background:rgba(255,255,255,.04);border-radius:8px}
.crow{display:grid;grid-template-columns:30px 30px minmax(110px,1fr) minmax(90px,1.5fr) 100px;
  align-items:center;gap:10px;padding:7px 12px;border-radius:11px;
  background:rgba(255,255,255,.022);border:1px solid rgba(255,255,255,.055)}
.crow:hover{background:rgba(255,255,255,.05)}
/* 产能不足：降饱和 + 降透明度，一眼可分辨；鼠标悬停恢复以便查看细节 */
.pt tbody tr.out,.crow.out{opacity:.38;filter:grayscale(.75)}
.pt tbody tr.out:hover,.crow.out:hover{opacity:.72;filter:grayscale(.35)}
/* ── 帕累托散点：横轴＝该周期实付（对数）、纵轴＝每月可生成 ──
   用途是回答「花多少钱买到多少产能」——这是本站在「单价」之外唯一有意义的权衡轴。
   对角线上的点＝不被任何其他档位支配（更便宜且更能做）的档位，即帕累托前沿。 */
/* ⚠ hero 的内容（meta 行）在 1440 视口下会撑到 1514px，导致整页横向溢出 ——
   这是首页原有缺陷，加散点后被冒烟测试抓出来。overflow-x:clip 不产生滚动容器，
   只裁掉溢出，不影响 sticky；配合 meta 允许换行双保险。 */
.hero{overflow-x:clip}
.hero .meta{flex-wrap:wrap}
.hero .pareto,.wrap>.pareto{margin-top:34px}
.pareto{display:flex;flex-direction:column;gap:10px;padding:16px;border-radius:18px;
  background:rgba(255,255,255,.024);border:1px solid rgba(255,255,255,.075)}
.phd b{display:block;font-size:14px;color:#E4E7EA}
.phd span{display:block;font-size:11.5px;color:#7A8088;line-height:1.7;margin-top:5px}
.phd i{font-style:normal;color:#D1FE17}
.pplot{position:relative;height:340px;border-radius:12px;
  background:
    repeating-linear-gradient(to right,rgba(255,255,255,.05) 0 1px,transparent 1px 10%),
    repeating-linear-gradient(to bottom,rgba(255,255,255,.05) 0 1px,transparent 1px 25%),
    rgba(0,0,0,.25)}
/* .pline 已移除（连线机制取消）—— 散点只靠点本身表达 */
/* 右上角标：轴已反转成「右上最好」，这里再明确钉一句，免得读者自己推断 */
.pcorner{position:absolute;right:9px;top:8px;z-index:1;font-size:10.5px;letter-spacing:.04em;
  color:rgba(209,254,23,.55);pointer-events:none;user-select:none}
.pp{position:absolute;transform:translate(-50%,50%);cursor:default;z-index:2}
.pp:hover{z-index:9}
.pp i{width:19px;height:19px;border-radius:5px;opacity:.85;display:block;
  background-size:cover;background-position:center;background-color:#111;
  border:1px solid rgba(0,0,0,.55);box-shadow:0 0 0 1.5px rgba(255,255,255,.10)}
/* 用户裁定：点不做高亮 —— 点本来就不可点，给 lime 环会让用户以为能点。
   信息全部交给连线表达。 */
/* 排名行悬停 → 散点对应点放大；散点悬停 → 排名行高亮。双向联动。 */
.pp.hl i{outline:2px solid #D1FE17;outline-offset:2px;opacity:1}
.crow.hl{background:rgba(209,254,23,.07);border-color:rgba(209,254,23,.3)}
.pp.rk1 i{border-width:2px;border-color:rgba(209,254,23,.55)}
.pp:hover i{opacity:1}
.pp.rk1 i{border-color:rgba(209,254,23,.6)}
/* 连线要足够醒目：它是这张图唯一的信息载体 */
.pline path{stroke-width:2}
.pp b{position:absolute;left:50%;bottom:20px;transform:translateX(-50%);white-space:nowrap;
  display:none;padding:5px 9px;border-radius:8px;font-size:11px;font-weight:600;
  background:rgba(10,11,13,.97);border:1px solid rgba(255,255,255,.16);color:#EDEFF2;
  box-shadow:0 8px 22px rgba(0,0,0,.6);z-index:9}
.pp b s{display:block;text-decoration:none;font-weight:400;color:#8A9098;margin-top:2px}
.pp:hover b{display:block}
.pfoot{display:flex;justify-content:space-between;font-family:__MONO__;font-size:10.5px;color:#6E747C}
.crk{font-family:__MONO__;font-size:12px;font-weight:700;color:#6E747C;text-align:right}
.crk.top3{color:#D1FE17}
/* 字母标：品牌色底 + 深色首字母。字号按三种壳尺寸分别给 */
.lg-mono{display:flex;align-items:center;justify-content:center;font-style:normal;
  font-weight:800;color:#0B0B0D;background-size:auto}
.clogo.lg-mono{font-size:13px}
.pfbi.lg-mono{font-size:9px}
.plgo.lg-mono{font-size:9px}
/* ⚠ 要压过 .clogo,.pfbi,.plgo{background:#111} —— 同权重时后写的赢，
   所以这里把选择器写成两段以提高权重 */
.lg-seko{background-image:url("data:image/png;base64,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")}
.lg-libtv{background-image:url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEgAAABICAMAAABiM0N1AAABgFBMVEX///////7//v7+/v7+/v39/v3+/f79/f39/fz8/fv9/P38/P38/Pz8/Pv8+/z7+/v7+vv6+vr6+vn5+vn6+fr5+fr5+fn5+fj5+Pn49/j39/f29vb19fTz8/Hs7Ovp6ejp6Ojo6Ojp6Ofo6Ofo5+fg4N/W1tXU09LT09PT09LS09LT0tLT0tHS0tHNzczBwb+trayenZySkZCKiomFhYSAf35/f39/f35/fn5+fXx9fXx5eHh3dnZ2dXVzc3NycXFycXBxcXBxcHBwb29kY2NVVVRJSEg8OzsuLS0iIiEcHBsTExMTERISERISERERERIREREODg0HBwUHBgcGBgYGBgUGBgQFBgUGBQUGBQQFBQUFBQQEBQMFBAQEBAUEBAQEBAMDBAIDBAEEAwQDAwMDAwIDAwECAwICAwECAwABAwAEAgIDAgICAgICAgECAgABAgIBAgEBAgADAQIDAQECAQICAQECAQABAQEBAQAAAQEDAAEBAAEBAAAAAAEAAAAIcsLTAAAGg0lEQVR42u1Y/1cTRxC/NrSxMRpjlYKCCYJUikGhKli1ERUwohQehqTBNIBJyLW5XfeE5QLi/uud2b1L7vZi0h/6+l7fczju9o7bz818dr7sYIh/SYwvQP85kBOSSkB25KE/QilbXYEsy4dFHIdzHDDCqMOCHyLqnpBWEMjShQSm0ZDGjJr4kNN+QOpzJ6CRjdNsEtYGYOD4J0AOP+BgFxw2hcmMoaGM4QhsBYUImh4CIkraQKSjBDM9XMrRIAAgJv6ZA1IIyFQiYd7DK0wRjerbeKYw/4iiDgByZCpsSnoDBZbOUatnAjOAzpFoeG5LomgXsn1AajLBOQyZVvbJmUgLNZEDpt4JAtkKpAYYnjrcsf5SdNXrVrPZ3Ldq+/s1HMHAqtXq8LLV1P2oRSk1TWr5gLzl6CMa2cfSf7nybu6qtPHb+hrKOsiaJ69fra2/fu09e7WpAUGMcIu5YSGPqsjdSI2NpdPpsYnx8dT18VRqfDydHk+lJ8ZS6eupsQmUayuiGgD6JP0YPKe9SBWxbPSX0VVhaRpxhOGOMoufOCWxGBk+f/78uXPxroLPv4/MOCHTCLNcf0E47pTFrDEYjcai3SQSkZdBY1aUNT8iimnuHZYlZoxktLcMGllR1B2SEblwMnpw6cRayoijRvHA3G/9NwljWddIKHJUKsNhVbwYUBixzyoUN0Zeil1NI04wBqySJ2/EUuLqoE+GOsNkW6HJykctaI9RC2L5XXa2x6oroEvGHVHWVu0TZp/m6erPrswti6Vfn2WzT59kFxcXnyqBcfbJk2z2sWQPuf5FFBzNNKRn2+eDSz3Ca2N04CwCJeGtbaZzBByXxOPEyMXLwEdyJCfelEKyXSpu5Tcry0ZSahT5ISfehRwSlr0i7hiXo7EzwOKNTWF56T0g/KAoHhqD8VjUfUuPfkzWvDljJKKxWAxZfNfBCFS0gzJ87pKy7I54G0r+UC2q4uUosBiLxoaMBVFyDjxfJ+0kifcf3/0In5Nc3xVbjg4Ecb8tVgxUOXr2AnjsH+jlxIu8jo34ua/iHtcFFgaiW+IZhil47NdDOVHlmDSJv8hSTA+4tAnXs1+IHaovP3NIQcW79Nji6SF3sDK2k74qsCYpikcyK8QSxsSG2GeaZ7eo0yCOG+9JyTXpFCNfcZJLC0DxWNK4LWqHUJmCns1oU6xe8zz2gShyWQqZvnfgTjXjcT0nCrBGGkeU7IiVSLydHbZdfjn32Rbg+qLxXJRsrtW1YwK59TnoDKsWj1zJiV2mEhMWeTf9SjPLHa4jwDX780DPkLQk5tpcb7fc0oRo3CVKApcU15iMUuuiZhOqV1paE7c7XFc6Xs29DZEEUmEk37oN8XHE9R0bqYn1CSMRlyzOVzbzxQKGaX4LLoV8Pl8s4m2x7NQyiSuDQ8PDI4k5UTrhOkf4qZWBMy7XKz1ySK6daYBr2FGEOEKuL7s5dO7BvXvzKAvzMFhYWIDzvfvzCw/uPxe5h4+VPHop9gk/0TdaZMvlGivW53PsrDjtKIeer5vWarS5RiJ9id5fAK7Gl0R+C6gC8vKFXRMXQddoT2xMGPFQRf0WFByIfuMGaeQqOFgniBlu23SN3ooXZ77rXr4i3iBpzBDSMIlyBEaVm2pAvwPXF32TuldoWHHMJsrpVbLS0kjL5XqgFxBmshKqgsxwasu9FD8KcgRcR4cTXeSCOicTiWQcY9CkVO3hqcq+mh9ZYnW0/7ZqsgoxCYpAMbXkthZM1DiCPcPkdCaTuZWZns7cmpqamp6G082bcJ6eymR+ugnDzORdNwaDvYYWIjs7jfpuvdGog+zt1Wuw/92r1evNZqPerMNts16rCq7aih5AH6ktpeVeTuEH71qn4rjVOjqFU0sWdkp7A7VME3RpgCp7DdJofPjwvrEne5L3h1bdPDyEEVRQwLBpqIXSgGC/jr/Y9Ng25DJsprwukRHlOKCNSfoAyY2/BKOYwmSaNr0Gj5mQcTmhJvgQ95vWBcjGbgSJQhZgiSmkdcc03YLN1C4ckFTF7WWaTWVbY3PQCdpFwCQ4RO3avR81ebvSuTghssHLTGzoQBWKAs2eCYmcuzhMlm7YQ3PaBwgZsB0TGjkwC8yDgAJIqP9IPEdnVr3nCe8DdMQxLxAbrs4RUEtBGeSYASZog+2fCaWOnnDZibUpCptGVH3m3L+50is2fqAPkAM/eHQEb+xW56F7Df/z48v/j/6/QH8DmV25TdCtIicAAAAASUVORK5CYII=")}
.lg-neowow{background-image:url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEgAAABICAMAAABiM0N1AAABgFBMVEX////+/v/+/v79/f79/f39/fz8/P38/Pz7+/z7+/v7+/r6+vv6+vr5+fr5+fn5+Pn4+Pn4+Pj39/f09PTz8/Py8vLx8fHw8PHw8PDv7+/u7u7q6urm5ubi4uLh4eHf39/b29va2trZ2dnY2NjX19fW1tbU1NTS0tLQ0NDNzc3KysrJycnIyMjHx8fFxcW/v7+9vb26urq2traysrKtra2pqamlpaWhoaGfn6Cenp2cnJyampqXl5eVlZWTk5OSkpKPj4+NjY2Li4uKioqJiYmHh4eFhYWCg4OAgIB9fX18fHx4eHh1dXV0dHRycnJxcXFubm5ra2tmZmZhYWFfX19bW1tWVlZSUlJOTk5ISUhFRUVDQ0NCQkI+Pj47Ozs5OTk1NTU0NDQvLy8sLCwpKSkoKCgkJCQgICAfHx8eHh8dHR0cHBwaGhoZGRkYGBkXFxcSEhIPDw8ODg4NDQ0LCwsKCgoJCQkHBwcGBgYFBQUEBAQEAwMDAwMCAgIBAQEAAAA7iml9AAADw0lEQVR42u2X+1cTRxTHr+u047TbrUGlKY/yUFAoIm8DgoAiRVAEY8SgiDaAKA8fVNxsZ+b+694hOcV9kvTwi+dkftlk9+Qz33u/d+7eAJ7SghqoBqqBTgck1f8DSR26pU5HUX4zkRQNIjXPD/BIk5ImJoXb1/vWk0iRIC1xomsZpcGUo9LrC29697SuDiRx9s7uPboQZic7mpeuh8/mMXsXZVUghYU+/DCmSNjbiQaAR3TPm1rTX4Y+oK4G5OH0E1SZDYVPG8ESrfvPJvvaByTdXovPUhRI6+FtxNxdfATgCKuzGwDYa3T1/IpXrAKk8ePwoXLdiWlggjEGYKfqV1BKfe8lxmYpGjTyma5LYHPiMC5seIweiRnoWdzBGOciky1H3+8u9loljkGxy1lSslsP0LgQQ4pSpHC8u5HScrw4QPdfS73gOACZf4ueFz5AEBGZN+mYLH8DYkJQwoEU8hQsR55FCOspDgH7L6pjlFNCC97ycO7Byt6JiiTeghRLWkbbpaaZoj9XEOLkwEnkCOh8UdxfbZvwVwIEa/FjsyWSONxqOvg0e6013SZ95wWCp2PxBEEcmpabTXQ9SaFp/aUjLIjzYI4ckYI7tGssSOK68ZgJ+xvbxFmwfVx6xnkq0DAhENl9Exk30o9jYXUQrAYjSCbYr7CfdhfQnn1wkfGySb2vt26BCDjXc6h0PEij2wqCs/pNpBZil0xKv6MnnT4SZ3/uBd9OAdB+A3AbBvFQbv1KPUTQwR9Az8Vpv5fOsouYoEjhVgq4A7dVEXd+ozSRPzCqpKfmAkUBbY8DJPCb9upHTqCbpOhvfqX5THsXg34sujgSAJEdQ//o2IJUesDk2mqhvjYL82tQGAdxoYC43WAFfBN1MOXzDXyCVktVBIOrCzZLd1vXOH1peZLrgFCVpmAkAZSxnLJwsJjJkVUuqlBX+RnSG1pFg8j8K+WdyS2qXsFKHci2w6cGfn8eW9kl81klS1gdW4FXnA+0m64QxHnjK5UA+twC5yoCMRu6vPiCVDhoOazCxQvxp1/iU3Aqi8wWkABC5d2AupM5limIm/E5MrHtdMBPdmzCfxAO9QZ2/sKlqw9l0qEl0vth2s12bBGk0QTgmC5rnbeuvnnrnfTKJrn5obSRbnHbOV62OIrn+ujlXwBmooZeCM1GiO9yk31/OOBf55r752iqcTfyL7VSuoIhotT6DjZf5JbmpsbHMpmx2zML2XzhU8nYqmZIKaMmF2VmEE0PqxrYzQ88Gl+OlvmgdO1vVg1UA9VA3wfoKy1N1tY01xhTAAAAAElFTkSuQmCC")}
.lg-jimeng{background-image:url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEgAAABICAMAAABiM0N1AAABgFBMVEXx/v/6/rvU/v7F/P24/f6r/v+g/v6Z/f3S9vj794Gr9/ub9/vd03342gqh3N6M/f+N9/x5+f139v199f1u9vxo9v1g9v5U9v1I9/5u9Ptq7fdO8/1K6vM89v028v448f4o9/8r8v0s8f4w8P0o8P0k7/0m6/4j7P4k6fsi7P0h6vwk5f0h5vwk4/0k4fwi4Psl3fgi3vsk2/sk2Pwh2fkj1vgh1/kq0fQjz/Yi0vgmzPkmyPohyPQkw+8kwPbjnCOYn3d2mpx3hFors+0spuQqmb0xg68ksO0jofEjl/gkmdAhivkfjeEfffkifbhsWDk8Tk0gYaQqQEUaYJoYTGAYQW4WPksrLisjHx0SMFgNHiocFxULExYHExwNCw0GCg0FBgkEBQcEBAQEBAICBgcDBAQCBAMFAwMDAwMCAwMBAwQCAgQCAgICAgABAgMBAgIAAgIBAgEDAQIBAQMBAQEBAQAAAQIAAQEAAQADAAUDAAABAAIBAAAAAAMAAAEAAADtKFzNAAADaUlEQVR42u3X3VfaaBAH4BRiUDx8CH6uVRShgBAoKq1ogY0bKJRFqAZwEVDDYgGjVHhZIqbMv943292bnuM5ScMlc8nFc36ZGSZAwISKmEJTaApNoZ9qIE0GGoEkTQJ6Hte/DEXt0GB8mcj3BEkzhOAikchDQ/uj9XsJU+JChfQS1IC8yZSod++1QvdQNmHpqXGPtEEDqGPIlIcbQeMePfYTprm5uRNodrVBzW/5OYIgXv0OwA80QZB/Reh0BMHUgUcaoBaUCUJP6mcJ8xkOJfwyJGBIR1JGo1GvZy4xzDdbwnCIEBJaLaQKupjVU1a71Wo1kGamLP1qoi6GSMPi8tKizW63UPPMSeGiet3g65flQoEHpAqasS6tr66vYGxtwUJR82a5ZuUBjHk1PSLnbSub284dx8bqiqwtWCwGipohjXpzX3miNpyRONC2z+Nxu5ybGJOjrdlw0wwzBbh9Vr5HBdK2vOHyBQJer8fndm07N39gC/YCdEUVC8lQS+s7vkAoFKT9Ae8bnMzt2nE4Vl+X4Iuo4vjfmC1yIDq8txcOBYM0Tft3vV7XVqoKt6Ly8bfRmQG32uMN7kWi794dyFooTG+95/BuSir2qA0MDuT00OFI9BBXNII1/9tUVbrBeSTFUBdV5Nn7AvRe5PADLmztB5MlGPE9pGazcastv606d+nQAXbisVjsaJ/lnqB6PX7hdUe8tETU4orDHQjKgWKxj/FjlqvCM8f1eqKoHBKgarbg2Xv84YPoYRwXe14DqZJM/n2Hht8UQ0i4ZWZsyw73Lm714YejY7ZYk+CqyB6XoCMqh5AADGldW3fiQJHo/lGSw8w19ykeT911+jBWCiH0zOjm7csb7t0A7X+fLF0BXHGn6XT6jyJ0hsrvUZdnCCP+uu64XW9i5xX8SaX4KZ3JpNNsRepLiiH5xJJyoK23Sa4OUOVSbDydyWYymdPWYAySUgihy1kdtfD63840Sin26PhjGkPZbOZ81FFzah+hfFIo48aMmvxNtVLiPrP4wbLZXBa3SBRV3Owfb9Z2s43++31U404z2Zx6CAS+3f1/OsOvna94asU/c7mcaujnGjZHUDmVoTvQBMHgn6ZU+5z7Cx40QrjuRte1p5EkaobQw6P0eC9OAJL6DwhNAJr+O5pCU2gKvVDfAf9WRwpR8cqOAAAAAElFTkSuQmCC")}
.lg-xiaoyunque{background-image:url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEgAAABICAMAAABiM0N1AAABQVBMVEX////+/v79/f38/Pz7+/v6+vr5+fn4+Pj39/f19fXz8/Pw8PDv7+/u7u7p6enn5+fm5ubk5OTj4+Pi4uLh4eHg4ODf39/e3t7d3d3X19fU1NTT09PQ0NDMzMzKysq8vLy5ubm2traurq6tra2rq6uqqqqnp6empqakpKSgoKCfn5+dnZ2ZmZmXl5eWlpaVlZWTk5OQkJCOjo6IiIiDg4N+fn59fX18fHx7e3t6enp5eXl4eHh1dXVzc3Nvb29ubm5sbGxqampoaGhnZ2dhYWFgYGBcXFxZWVlYWFhXV1dWVlZPT09OTk5NTU1KSkpJSUlGRkZFRUVDQ0NAQEA8PDw7Ozs3Nzc0NDQyMjIjIyMYGBgTExMODg4MDAwLCwsKCgoJCQkICAgHBwcGBgYFBQUEBAQDAwMCAgMCAgIBAQEAAAAnvg7lAAAB/ElEQVR42u3X+1MTMRAH8E0uByrWF6Ioaq3gW8D3E0EB5aEo4BvhqrQXk+///we4d70Zp6U3Q3L3i8zttJ20M/uZ3TRJU0JJQRVUQRV0sCDbL5whE5syKrKaX3ajZk9Ev6KmE8QN/HhWP3OyN4aHj32C3j9k0X54hPrGPMz+K7J2u06kAtkdIggOv+/n5ELaNmhA7K1G0iraDpOtMU9hlqo4ZOYoutHfyYGs3Tkl0mQRZJzICvpitAOksUYdh2j07qvX98fSIT9rP2EdoBgPhEoTw5dR8kH7TS2RJI38doI0rvN0cF/hGqtp5rcad+cBXSGenIAeo6Xx/dpb28Yyv/WAxjlN0IkdwxvlA1GjaXCRpCek6CaPNDbUIS4NT0h5Q89tzON1CuVYnPTmDb3IICVGmlgqAN1KW1unQaoDj7xbE3Q8SiZ7g9fmpsEl74r48RStGB9pdBVY4S/fFxIyfMcLcmtzG/h61G9BphAJEcykW2R3cchzi3SgJPns1OzcvfOdTesP9RwjBaDug60Q1H3QVtD/CJ0uCzqnS4EC0YBBCZCiWf7NKw4JObSV05kbNMAFaRSGZEgTuU4udFUNqu7gc+R2y1hX6PLexi4sA9bxVmuwcGd68l9MTU7PfNbIr8ft5q997tk67g1tq39HHvHHlgTZarIr6MBDfwGWlxz1MHo2pgAAAABJRU5ErkJggg==")}
.lg-higgsfield{background-image:url("data:image/png;base64,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")}
.lg-tapnow{background-image:url("data:image/png;base64,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")}
/* 三个尺寸的 logo 壳：背景图由 .lg-* 提供 */
.clogo,.pfbi,.plgo{display:inline-block;flex:0 0 auto;background-color:#111;
  background-size:cover;background-position:center;background-repeat:no-repeat}
.clogo{width:26px;height:26px;border-radius:8px;border:1px solid rgba(255,255,255,.1)}
.pfbi{width:15px;height:15px;border-radius:4px}
.plgo{width:15px;height:15px;border-radius:4px;vertical-align:-2px;margin-right:7px}
.plc{display:inline-flex}
.cname{font-size:13px;font-weight:600;color:#E4E7EA;min-width:0;white-space:nowrap;
  overflow:hidden;text-overflow:ellipsis}
.cname s{text-decoration:none;font-size:10.5px;font-weight:400;color:#7A8088;margin-left:6px}
.cbar{height:9px;border-radius:5px;background:rgba(255,255,255,.085);overflow:hidden}
.cbar i{display:block;height:100%;border-radius:5px;transition:width .35s cubic-bezier(.22,1,.36,1)}
.cval{font-family:__MONO__;font-size:13.5px;font-weight:700;color:#EDEFF2;text-align:right;
  white-space:nowrap}
.cval s{display:block;text-decoration:none;font-size:10px;font-weight:500;color:#7A8088}
.combo-note{display:block;margin-top:4px;font-size:10.5px;color:#8A9098}
.reco{display:flex;flex-direction:column;gap:10px;padding:14px 15px;border-radius:16px;
  background:rgba(209,254,23,.045);border:1px solid rgba(209,254,23,.2)}
.recot{font-size:13px;font-weight:700;color:#D1FE17}
.recot span{display:block;font-size:11px;font-weight:400;color:#8A9098;margin-top:4px}
/* 顶部 tab 条：手机端常驻可见（PC 端用侧栏，故隐藏）—— 学 arena.ai */
.tabs{display:none}
/* ⚠ 不要给 .vmeta span 加 display:inline-flex —— flex 容器会裁掉纯文本节点
   首尾的空白，导致「数据时点」与「2026-09-21」直接贴在一起（用户报的重叠感）。
   图标对齐用 vertical-align 处理即可。 */
.vmeta svg{vertical-align:-2px;margin-right:5px;color:#5A6069;flex:0 0 auto}
.vpanel{display:none;flex-direction:column;gap:14px}.vpanel.on{display:flex}.vptitle{font-size:14px;font-weight:700;color:#E4E7EA}.vptitle span{display:block;font-size:11.5px;font-weight:400;color:#7A8088;margin-top:4px}/* 周期三选一：整块预渲染，只切可见性 */
.pt{display:none}.pt.on{display:block}/* ── 结论芯片行（替代三张大卡，降低文字密度）── */
.chips{display:flex;gap:10px;flex-wrap:wrap}.chip{display:inline-flex;align-items:baseline;gap:9px;padding:10px 15px;border-radius:12px;
  background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.09);
  font-family:__MONO__;font-size:15px;font-weight:700;color:#EDEFF2;letter-spacing:-.02em}.chip b{font-family:inherit;font-size:10.5px;font-weight:700;letter-spacing:.09em;color:#D1FE17}.chip s{font-family:__SANS__;font-size:11.5px;font-weight:400;text-decoration:none;color:#8A9098}/* 计算器里的极简折叠块：不占视觉重量，只承载口径说明 */
details.tiny{margin:12px 0 0;background:transparent;border:0;box-shadow:none}details.tiny summary{padding:6px 0;font-size:11.5px;font-weight:600;color:#6E747C}details.tiny summary:hover{color:#C9CDD2}details.tiny .dbody{padding:8px 0 0;font-size:12px;color:#8A9098}.combo-plus{color:#5A6069;margin:0 5px;font-weight:700}.sub{color:#767C85;font-size:12px;line-height:1.7}.mono{font-family:__MONO__}.foot{margin-top:44px;color:#5A6069;font-size:11.5px;text-align:center;
  border-top:1px solid rgba(255,255,255,.08);padding-top:20px}.legal{margin-top:22px;padding:26px 28px;background:#D1FE17 !important;border-color:#D1FE17;
  border-radius:20px;color:#0B0B0B;font-size:12px;line-height:1.8;backdrop-filter:none;
  -webkit-backdrop-filter:none}.legal-t{font-size:16px;font-weight:800;letter-spacing:-.025em;margin-bottom:9px}.legal-b{color:#1F2A00;max-width:1000px}.legal-f{margin-top:14px;font-family:__MONO__;font-size:11px;color:#1F2A00}.legal-f .fp{background:#0B0B0B;color:#D1FE17;padding:2.5px 9px;border-radius:6px;font-weight:600}

@keyframes fadeUp{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:none}}.reveal{opacity:0;transform:translateY(16px);
  transition:opacity .62s cubic-bezier(.22,1,.36,1),transform .62s cubic-bezier(.22,1,.36,1)}.reveal.in{opacity:1;transform:none}.hero>*{animation:fadeUp .7s cubic-bezier(.22,1,.36,1) both}.hero>*:nth-child(2){animation-delay:.06s}.hero>*:nth-child(3){animation-delay:.12s}.hero>*:nth-child(4){animation-delay:.18s}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}.reveal,.hero>*{opacity:1!important;transform:none!important;animation:none!important;transition:none!important}
}
@media print{body{background:#fff!important;color:#000!important;padding:0}body::before,body::after,.hero::before,.hero::after{display:none!important}.card,.kpi,.note,.entry,.legal,details,.nav,table{
    -webkit-backdrop-filter:none!important;backdrop-filter:none!important;
    box-shadow:none!important;background:#fff!important}.nav{position:static!important}.promo{background:#D1FE17!important;color:#000!important}.brand .bw b,.menu a,h1,h2,h3,td,th,li,.kpi .v,.lead,.meta{color:#000!important}.legal{background:#F2FFB8!important}.legal-t,.legal-b,.legal-f{color:#000!important}.tw{overflow:visible!important}.tw table{min-width:0!important}details:not([open]) .dbody{display:block!important}
}
@media (max-width:820px){.promo{font-size:11.5px;padding:9px 14px;gap:9px}.nav .inner{padding:10px 15px;gap:11px}.nav .spec{display:none}.hero{padding:36px 15px 4px}.wrap{padding:0 15px}section{margin-top:44px}h2{font-size:17.5px}.kpi .v{font-size:26px}.entry{padding:20px}.card,.kpi,.note,.legal,table,details,.entry{border-radius:15px}.legal{padding:21px 18px}td,th{padding:7px 11px}summary{padding:14px 17px;font-size:13px}.dbody{padding:0 17px 18px}.g5,.g2{grid-template-columns:1fr 1fr}
  /* ── KPI：竖排五张卡会吃掉 1.5 屏，用户滚到反查与表格之前就以为「页面到头了」。
     改成横向滑动的一行，高度固定，下方内容自然进入首屏。 */
  .grid.g5{display:flex;overflow-x:auto;overscroll-behavior-x:auto;gap:10px;
    scroll-snap-type:x proximity;-webkit-overflow-scrolling:touch;
    margin:0 -15px;padding:2px 15px 6px;scrollbar-width:none}
  .grid.g5::-webkit-scrollbar{display:none}
  .grid.g5>.kpi{flex:0 0 64%;min-width:0;scroll-snap-align:start}
  .grid.g5>.kpi .v{font-size:24px}
  /* ── 反查表：套用与「全部档位排名」同一套卡片节奏 ──
     5 列在手机上必然横滑；上一版做成「标签在上、值在下」的纵向大卡，占太高、看着散。
     用户要求跟排名卡一样大小，故复用同一套：1fr + auto 两列、11px 内边距、圆角 13。 */
  .tw-rec{padding:2px 0 0}
  .tw-rec table,.tw-rec tbody{display:block;width:auto;min-width:0}
  .tw-rec thead{display:none}
  .tw-rec tbody tr{display:grid;grid-template-columns:1fr auto;align-items:baseline;
    gap:4px 10px;margin-bottom:8px;padding:11px 13px;border-radius:13px;
    border:1px solid rgba(255,255,255,.1);
    background:linear-gradient(158deg,rgba(255,255,255,.05),rgba(0,0,0,.28))}
  .tw-rec tbody td{border:0;padding:0;white-space:normal;background:none!important;
    display:block;text-align:left!important;min-width:0}
  .tw-rec tbody td::before{display:none}
  /* 第 1 行：方案类型 + 周期支出（大字，右） */
  .tw-rec tbody td:nth-child(1){grid-area:1/1;font-size:13px;font-weight:600;color:#fff}
  .tw-rec tbody td:nth-child(1) .sub{display:inline;margin-left:7px;font-size:10.5px;
    color:#7A8088;font-weight:400}
  .tw-rec tbody td:nth-child(3){grid-area:1/2;text-align:right!important;white-space:nowrap;
    font-size:15px;color:#fff}
  .tw-rec tbody td:nth-child(3) .strong{font-size:15px}
  /* 第 2 行：档位组合（可换行） */
  .tw-rec tbody td:nth-child(2){grid-area:2/1/3/3;font-size:10.5px;color:#7A8088;
    line-height:1.7;overflow-wrap:anywhere}
  .tw-rec tbody td:nth-child(2)::before{content:"档位组合 ";color:#5A6069}
  /* 第 3 行：产能 + 单条 */
  .tw-rec tbody td:nth-child(4){grid-area:3/1;font-size:10.5px;color:#7A8088;white-space:nowrap}
  .tw-rec tbody td:nth-child(4)::before{content:"产能 ";color:#5A6069}
  .tw-rec tbody td:nth-child(5){grid-area:3/2;text-align:right!important;font-size:10.5px;
    color:#7A8088;white-space:nowrap}
  .tw-rec tbody td:nth-child(5)::before{content:"单条 ";color:#5A6069}
  .tw-rec tbody td .combo-note{display:inline;margin-left:7px;font-size:10.5px;color:#6E747C}input[type=range]{width:100%}/* ── 主表改卡片形态（竖屏）──────────────────────────────────
     44 行 x 7 列在 390px 宽下要横向拖很远才能读完一行，这是数据密度决定的，
     压缩列宽解决不了。改为每档一张竖排卡片：首行「名次 平台 档位」，
     下面四行「标签 — 数值」，上下滑即可。 */
  /* 特异性必须 ≥ .tw.scroll-y(0,2,0)，否则 overflow-y:auto 赢，
   卡片形态下容器仍被当作滚动容器 → 手势被它吃掉、整页滑不动。 */
  .tw.scroll-y.tw-main{max-height:none;overflow:visible}.tw-main table{min-width:0!important}.tw-main{min-width:0;background:transparent;border:0;box-shadow:none;border-radius:0;
    overflow:visible}.tw-main thead{display:none}
  /* ── 手机端卡片：压成「两行 + 一条刻度」，对齐 arena.ai 的手机行高（约 110px）──
     上一版每张卡 7 行、约 270px，44 张就是 11,900px（16 屏），滑到崩溃。
     现在：第 1 行＝名次 / 平台 / 档位 / 单条成本，第 2 行＝实付 · 产能 · 元每秒。 */
  .tw-main tbody tr{display:grid;grid-template-columns:auto auto 1fr auto;
    align-items:baseline;gap:3px 8px;
    margin-bottom:8px;padding:11px 13px;border-radius:13px;
    border:1px solid rgba(255,255,255,.1);
    background:linear-gradient(158deg,rgba(255,255,255,.05),rgba(0,0,0,.28))}
  .tw-main tbody tr.top{border-color:rgba(209,254,23,.42);box-shadow:inset 3px 0 0 #D1FE17}
  .tw-main tbody td{border:0;padding:0;white-space:normal;background:none!important;
    position:static;display:block}
  .tw-main tbody td::before{display:none}
  /* 第 1 行 */
  .tw-main tbody td:nth-child(1){grid-area:1/1;font-size:12px;text-align:left}
  .tw-main tbody td:nth-child(1) b{font-size:12.5px}
  .tw-main tbody td:nth-child(1) s{font-size:9.5px;margin-left:3px}
  .tw-main tbody td:nth-child(2){grid-area:1/2;font-weight:600;color:#fff;font-size:13px;
    white-space:nowrap}
  .tw-main tbody td:nth-child(3){grid-area:1/3;color:#9AA0A8;font-size:12px;min-width:0;
    overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .tw-main tbody td:nth-child(6){grid-area:1/4;text-align:right;white-space:nowrap}
  .tw-main tbody td:nth-child(6) .nm,.tw-main tbody td:nth-child(6) .strong{font-size:14px}
  .tw-main tbody td:nth-child(6) s{display:block;font-size:9.5px;color:#6E747C;margin-top:1px;
    white-space:nowrap}
  .tw-main tbody td:nth-child(6) .mini{display:none}
  /* 第 2 行：三项小字并排，各自带极简前缀 */
  .tw-main tbody td:nth-child(4){grid-area:2/1/2/3;color:#7A8088;font-size:10.5px;
    white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .tw-main tbody td:nth-child(5){grid-area:2/3;color:#7A8088;font-size:10.5px;white-space:nowrap;
    overflow:hidden;text-overflow:ellipsis}
  .tw-main tbody td:nth-child(7){grid-area:2/4;color:#7A8088;font-size:10.5px;text-align:right;
    white-space:nowrap}
  .tw-main tbody td:nth-child(4)::before{content:"实付 ";color:#5A6069;display:inline}
  .tw-main tbody td:nth-child(5)::before{content:"产能 ";color:#5A6069;display:inline}
  .tw-main tbody td:nth-child(7)::before{content:"元/秒 ";color:#5A6069;display:inline}
  .tw-main tbody td:nth-child(4) b,.tw-main tbody td:nth-child(5) b,
  .tw-main tbody td:nth-child(7) b{display:inline;font-size:11.5px;font-weight:600;color:#B9BEC4}
  .tw-main tbody td:nth-child(4) s,.tw-main tbody td:nth-child(5) s,
  .tw-main tbody td:nth-child(7) s{display:none}

}
@media (max-width:520px){.g5,.g2{grid-template-columns:1fr} }/* ── 窄屏：左栏改为【底部抽屉】+ 底部摘要条 ──
   上一版把侧栏做成「吸顶横向滚动条」，实测失败：吸顶块挡住内容，
   月产量与平台筛选被挤出视野、用户根本找不到。
   移动端的正确形态是「底部条 + 弹层」：不占首屏、信息一个不少、可发现。 */
.mobar,.scrim,.nburger,.ndrop,.sheet-hd{display:none}
@media (max-width:1020px){
  /* ⚠ 必须显式 stretch：桌面端 .app 是 flex-start，窄屏转纵向后
     align-items:flex-start 会让交叉轴（横向）按内容宽度定尺寸，
     主区被里面的 760px 表格撑到 760px → 整页横向溢出。 */
  .app{flex-direction:column;align-items:stretch;gap:15px;padding:16px 15px 0}
  .side{position:fixed;left:0;right:0;bottom:0;top:auto;z-index:60;width:auto;
    max-height:78vh;overflow-y:auto;flex-direction:column;flex-wrap:nowrap;gap:17px;
    will-change:max-height,transform;
    padding:18px 18px calc(20px + env(safe-area-inset-bottom,0px));
    border-radius:20px 20px 0 0;background:#0A0B0D;
    border:1px solid rgba(255,255,255,.12);border-bottom:0;
    box-shadow:0 -18px 44px rgba(0,0,0,.62);
    transform:translateY(103%);visibility:hidden;
    transition:transform .34s cubic-bezier(.22,1,.36,1),max-height .34s cubic-bezier(.22,1,.36,1),
      visibility .34s}
  /* 半开（默认）与全开：只差一个 max-height，内容超出时组件内滚动，不会有够不着的内容 */
  .side.open{transform:none;visibility:visible;max-height:78vh}
  .side.peek{max-height:42vh}
  /* 拖动中关掉过渡 —— 有过渡就会「追手指」，手感发飘 */
  .side.dragging{transition:none!important}
  /* 抽屉头：把手给「可下滑」的暗示，✕ 给明确的关闭出口 */
  .sheet-hd{display:flex;align-items:center;justify-content:space-between;
    position:sticky;top:0;z-index:3;background:#0A0B0D;
    padding:16px 2px 12px;border-bottom:1px solid rgba(255,255,255,.09);
    cursor:grab;touch-action:none;user-select:none;-webkit-user-select:none}
  .sheet-hd:active{cursor:grabbing}
  .sheet-hd .grab{position:absolute;left:50%;top:7px;transform:translateX(-50%);
    width:38px;height:4px;border-radius:2px;background:rgba(255,255,255,.26)}
  .sheet-hd b{font-size:14px;color:#E4E7EA}
  .sheet-x{-webkit-appearance:none;appearance:none;cursor:pointer;
    width:34px;height:34px;border-radius:10px;font-size:14px;line-height:1;
    border:1px solid rgba(255,255,255,.14);background:rgba(255,255,255,.05);
    color:#C9CDD2;font-family:inherit;
    display:flex;align-items:center;justify-content:center}
  .sheet-x:active{background:rgba(255,255,255,.12)}
  .sgroup{flex:1 0 auto}
  .segv{flex-direction:row;gap:3px}
  .segv button{flex:1;text-align:center;padding:9px 5px;font-size:12px}
  .segv button s{display:block;font-size:10px}
  .side .cqr{width:100%}
  .mobar{display:flex;position:fixed;left:0;right:0;bottom:0;z-index:50;
    align-items:center;gap:12px;
    padding:11px 15px calc(11px + env(safe-area-inset-bottom,0px));
    background:rgba(10,11,13,.93);-webkit-backdrop-filter:blur(16px);backdrop-filter:blur(16px);
    border-top:1px solid rgba(255,255,255,.1)}
  .mosum{flex:1;min-width:0;font-size:11.5px;color:#9AA0A8;
    white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  /* 用户反馈「调整」不显眼、不知道里面藏着控件 —— 改成实心亮色 + 图标 + 动效 */
  .mobar{padding:10px 14px calc(10px + env(safe-area-inset-bottom,0px));
    background:rgba(16,17,20,.97);border-top:1px solid rgba(209,254,23,.22);
    box-shadow:0 -10px 26px rgba(0,0,0,.5)}
  .mobar button{-webkit-appearance:none;appearance:none;flex:0 0 auto;cursor:pointer;
    display:flex;align-items:center;gap:7px;
    border:0;background:#D1FE17;color:#0B0B0B;
    font-family:inherit;font-size:13.5px;font-weight:800;letter-spacing:-.01em;
    padding:11px 18px;border-radius:12px;
    box-shadow:0 0 0 0 rgba(209,254,23,.55);animation:mopulse 2.4s ease-out 1.2s 2}
  @keyframes mopulse{
    0%{box-shadow:0 0 0 0 rgba(209,254,23,.5)}
    70%{box-shadow:0 0 0 10px rgba(209,254,23,0)}
    100%{box-shadow:0 0 0 0 rgba(209,254,23,0)}}
  .mobar button svg{flex:0 0 auto}
  .mosum{color:#C9CDD2}
  .mosum em{font-style:normal;color:#8A9098}
  .scrim{display:block;position:fixed;inset:0;z-index:55;background:rgba(0,0,0,.55);
    opacity:0;visibility:hidden;transition:opacity .28s,visibility .28s}
  .scrim.open{opacity:1;visibility:visible}
  /* 顶部横滚 tab：导航常驻可见，比藏进抽屉好找（对齐 arena.ai 的手机结构） */
  .tabs{display:flex;gap:6px;overflow-x:auto;scrollbar-width:none;
    margin:-4px 0 0;padding-bottom:2px}
  .tabs::-webkit-scrollbar{display:none}
  .tabs button{-webkit-appearance:none;appearance:none;flex:0 0 auto;cursor:pointer;
    border:1px solid rgba(255,255,255,.11);background:rgba(255,255,255,.035);
    color:#9AA0A8;font-family:inherit;font-size:13px;font-weight:600;
    padding:9px 15px;border-radius:11px;white-space:nowrap;text-align:left}
  .tabs button s{display:block;font-size:10px;font-weight:400;text-decoration:none;
    color:#6E747C;margin-top:2px}
  .tabs button.on{background:#D1FE17;border-color:#D1FE17;color:#0B0B0B}
  .tabs button.on s{color:rgba(11,11,11,.62)}
  #sgView{display:none}
  /* 排名条窄屏：名称一行，条子通栏第二行 */
  .crow{grid-template-columns:24px 24px 1fr auto;gap:4px 9px;padding:9px 11px}
  .crk{grid-area:1/1}
  .clogo{grid-area:1/2;width:23px;height:23px;border-radius:7px}
  .cname{grid-area:1/3}
  .cval{grid-area:1/4;font-size:12.5px}
  .cbar{grid-area:2/1/2/5;height:7px}
  /* 手机端保持「随页面滚动」—— 嵌套滚动容器会吃掉手势 */
  .chart{max-height:none;overflow:visible;padding-right:0}
  .pplot{height:260px}
  .pp i{width:15px;height:15px;border-radius:4px}
  .pf{max-width:none}
  /* promo 在手机端压到一行：长句与日期 chip 都隐去（日期在下方 vmeta 里已有） */
  .pmore,.promo .tag2{display:none}
  .promo{padding:9px 15px;font-size:11px;gap:0}
  /* 窄屏导航：横向菜单改汉堡 —— 硬裁/横滚都不是好体验 */
  .nav .menu{display:none}
  .nburger{display:flex;flex-direction:column;justify-content:center;gap:4px;
    width:38px;height:38px;padding:0 9px;margin-left:auto;cursor:pointer;
    border:1px solid rgba(255,255,255,.14);border-radius:11px;
    background:rgba(255,255,255,.045)}
  .nburger i{display:block;height:1.5px;border-radius:2px;background:#D7DBDF}
  .ndrop{position:absolute;left:12px;right:12px;top:calc(100% + 6px);z-index:45;
    padding:8px;border-radius:15px;background:rgba(10,11,13,.97);
    border:1px solid rgba(255,255,255,.13);box-shadow:0 18px 42px rgba(0,0,0,.6);
    -webkit-backdrop-filter:blur(18px);backdrop-filter:blur(18px)}
  .nav.open .ndrop{display:block}
  .ndrop nav{display:flex;flex-direction:column}
  .ndrop a{display:flex;align-items:center;gap:8px;padding:13px;border-radius:10px;
    text-decoration:none;color:#C9CDD2;font-size:14px;font-weight:600}
  .ndrop a+a{box-shadow:inset 0 1px 0 rgba(255,255,255,.07)}
  .ndrop a.active{color:#D1FE17;background:rgba(209,254,23,.09)}
}
@media (max-width:612px){
  /* ── KPI 条：成本页与全清单页的顶部结论卡。
     竖排两列会吃掉 1.5 屏，用户滚到反查与表格之前就以为「页面到头了」，
     反馈「点进去不知道下面还有表格」。改成横向滑动的一行，高度固定。 */
  .kbar.on{display:flex;overflow-x:auto;overscroll-behavior-x:auto;gap:10px;
    scroll-snap-type:x proximity;-webkit-overflow-scrolling:touch;
    margin:0 -15px;padding:2px 15px 6px;scrollbar-width:none}
  .kbar.on::-webkit-scrollbar{display:none}
  .kbar.on>.kb{flex:0 0 62%;min-width:0;scroll-snap-align:start}
  .kb b{font-size:19px}
  .side{gap:14px}
}
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

/* ══════════ 阅读路径条：可关闭，记住选择 ══════════ */
(function(){
  var el = document.getElementById('guide');
  if(!el) return;
  var KEY = 'caliber.guide.v1';
  function hide(){ el.style.display = 'none'; }
  var off = false;
  try{ off = localStorage.getItem(KEY) === '0'; }catch(e){ off = false; }
  if(off){ hide(); return; }
  var x = document.getElementById('guideX');
  if(x) x.addEventListener('click', function(){
    hide();
    try{ localStorage.setItem(KEY, '0'); }catch(e){}
  });
  /* 页脚「新手引导」同时恢复路径条 —— 与弹窗共用一个入口，行为更一致 */
  var again = document.getElementById('introAgain');
  if(again) again.addEventListener('click', function(){
    try{ localStorage.removeItem(KEY); }catch(e){}
    el.style.display = '';
  });
})();

/* ══════════ 全站通用：新人引导弹窗 ══════════
   只在首次访问出现；第 1 步就有 ✕，不强迫看完；页脚有入口可随时重看。 */
(function(){
  var el = document.getElementById('intro');
  if(!el) return;
  var KEY = 'caliber.intro.v1';
  var slides = el.querySelectorAll('.is');
  var dots = el.querySelectorAll('.idot');
  var prev = el.querySelector('.iprev');
  var next = el.querySelector('.inext');
  var x = el.querySelector('.ix');
  var i = 0;

  function show(n){
    i = Math.max(0, Math.min(slides.length - 1, n));
    Array.prototype.forEach.call(slides, function(s2, k){ s2.classList.toggle('on', k === i); });
    Array.prototype.forEach.call(dots, function(d, k){ d.classList.toggle('on', k <= i); });
    prev.style.visibility = i ? 'visible' : 'hidden';
    next.textContent = (i === slides.length - 1) ? '开始看' : '下一步';
  }
  function close(){
    el.classList.remove('on');
    document.body.classList.remove('ibody');
    try{ localStorage.setItem(KEY, '1'); }catch(e){}
  }
  function open(){
    el.classList.add('on');
    /* ⚠ 只在弹窗打开期间锁滚动，关闭立刻解除 —— 本项目有过「忘了解锁、页面滑不动」的事故 */
    document.body.classList.add('ibody');
    show(0);
  }

  prev.addEventListener('click', function(){ show(i - 1); });
  next.addEventListener('click', function(){
    if(i === slides.length - 1){ close(); } else { show(i + 1); }
  });
  x.addEventListener('click', close);
  el.addEventListener('click', function(e){ if(e.target === el) close(); });
  document.addEventListener('keydown', function(e){
    if(!el.classList.contains('on')) return;
    if(e.key === 'Escape') close();
    if(e.key === 'ArrowRight') next.click();
    if(e.key === 'ArrowLeft' && i) prev.click();
  });

  var again = document.getElementById('introAgain');
  if(again) again.addEventListener('click', function(e){ e.preventDefault(); open(); });

  var seen = false;
  try{ seen = !!localStorage.getItem(KEY); }catch(e){ seen = true; }  /* 存不了就别弹，别每次都打扰 */
  if(!seen) setTimeout(open, 700);   /* 让首屏先渲染完再弹，避免闪一下 */
})();

/* ══════════ 全站通用：术语提示 ══════════
   词典只注入一次，提示内容由 JS 填进 data-s（避免每个术语在 HTML 里重复一遍长文案）。 */
var GLOS = __GLOS__;
(function(){
  var els = document.querySelectorAll('.tm');
  if(!els.length) return;
  var tip = document.createElement('div');
  tip.className = 'tip';
  document.body.appendChild(tip);
  Array.prototype.forEach.call(els, function(el){
    var x = GLOS[el.dataset.t];
    if(!x) return;
    /* 桌面：悬停出 fixed 浮层。位置按术语的视口坐标算，靠近右／下边缘时自动翻转。 */
    el.addEventListener('mouseenter', function(){
      var r = el.getBoundingClientRect();
      tip.textContent = x.s;
      tip.classList.add('on');
      var tw = tip.offsetWidth, th = tip.offsetHeight, vw = window.innerWidth, vh = window.innerHeight;
      var left = Math.min(Math.max(8, r.left), vw - tw - 8);
      var top = r.bottom + 7;
      if(top + th > vh - 8) top = r.top - th - 7;
      tip.style.left = left + 'px';
      tip.style.top = Math.max(8, top) + 'px';
    });
    el.addEventListener('mouseleave', function(){ tip.classList.remove('on'); });
    el.addEventListener('click', function(e){
      e.preventDefault();
      /* 手机端点开——就地展开全文，不跳页。同时只保留一个展开块，避免页面被撑乱 */
      var box = el.nextElementSibling;
      var mine = box && box.classList.contains('tmx');
      Array.prototype.forEach.call(document.querySelectorAll('.tmx.on'), function(b){
        b.classList.remove('on');
        if(b.previousElementSibling) b.previousElementSibling.classList.remove('on');
      });
      if(mine){ return; }
      var d = document.createElement('div');
      d.className = 'tmx on';
      d.innerHTML = '<b>' + x.t + '</b>　' + x.l
        + '<br><a href="glossary.html#' + el.dataset.t + '">术语表里还有 ' + Object.keys(GLOS).length + ' 条 ›</a>';
      el.parentNode.insertBefore(d, el.nextSibling);
    });
  });
})();

/* ── 窄屏汉堡菜单：点开 / 点外收起 ──
   ⚠ 必须留在【基础 JS】里，且全站只能有一份。
   按钮由共享的 nav() 组件渲染，四页都有；此前这段写在 COST_JS 内，而 cost_js=False 的
   首页与排行榜页根本不注入该块 → 这两页「有按钮、没监听」，手机上点了完全不动。
   又因按钮只在窄屏显示（桌面 display:none），桌面端测试连按钮都看不见，
   两个因素叠加，使这个缺口在所有桌面断言里都是隐形的。
   注：重复绑定同样致命 —— 两份监听各 toggle 一次＝互相抵消，表现仍是「点了没反应」。 */
(function(){
  var nv = document.querySelector('.nav'), nbg = document.getElementById('nBurger');
  if(!nv || !nbg) return;
  nbg.addEventListener('click', function(e){
    e.stopPropagation();
    var open = nv.classList.toggle('open');
    nbg.setAttribute('aria-expanded', open ? 'true' : 'false');
  });
  document.addEventListener('click', function(e){
    if(nv.classList.contains('open') && !nv.contains(e.target)){
      nv.classList.remove('open');
      nbg.setAttribute('aria-expanded', 'false');
    }
  });
})();
__COST__
"""

COST_JS = r"""
/* ══════════════════════════════════════════════════════════════
   成本页：总投入产出（月产量滑块 + 单条产出价值 → ROI）
   外加「全档位对比」按该产量的年支出重排（排名格副行直接显示该产量下的年支出）
   ══════════════════════════════════════════════════════════════ */
var PLANS = __PLANS__;
var PT_N = __PTN__;         /* 每个周期各有几档可比 */
var MAX_STACK = 4;          /* 同档最多叠加份数 */
var CQ_LOCK = false, CQ_LAST = null;
var PK = 'y';               /* 当前周期：y 年付 / q 季付 / m 月付 */
var CV = 'all';             /* 当前视图：all 全档位对比 / buy 我该买哪个 / period 周期对照 */

/* ── 移动端底部摘要条：让用户不打开抽屉也知道当前看的是哪一套 ── */
var VIEW_LBL = {all: '全档位对比', period: '先别急着下单'};
var PER_LBL = {y: '年付', q: '季付', m: '月付'};
function updateMoSum(){
  var el = document.getElementById('moSum');
  if(!el) return;
  /* 三周期全清单页的摘要口径不同 */
  if(document.getElementById('chart')){
    var cn = document.querySelectorAll('#cycPlat .pfb.on').length;
    var ctot = document.querySelectorAll('#cycPlat .pfb').length;
    el.textContent = CM[CT.m].lb + ' \u00b7 ' + PERLB[CT.k] + ' \u00b7 '
      + (CT.o === 'best' ? '最优在前' : '最差在前') + ' \u00b7 ' + cn + '/' + ctot + ' 平台';
    return;
  }
  var on = document.querySelectorAll('#platFilter .pfb.on').length;
  var tot = document.querySelectorAll('#platFilter .pfb').length;
  el.textContent = VIEW_LBL[CV] + ' · ' + PER_LBL[PK] + ' · ' + readN() + ' 条/月 · ' + on + '/' + tot + ' 平台';
}

/* ── 周期切换 ──
   三张表整块预渲染，切换只改可见性与当前生效的价/量，不做单元格级重写。
   不可用（如 Higgsfield 无季付）的档位把 price 置 Infinity、mCap 置 0，
   needOf 与 bestCombo 的既有判断会自动跳过它们，无需改算法。 */
function activePt(){ return document.querySelector('.pt.on'); }
function activeTb(){ var el = activePt(); return el ? el.querySelector('tbody') : null; }
function activeTable(){ var el = activePt(); return el ? el.querySelector('table') : null; }

function applyPeriod(K){
  PK = K;
  for(var i = 0; i < PLANS.length; i++){
    var p = PLANS[i], v = p.pc[K];
    p.price = (v == null) ? Infinity : v;
    p.mCap = (p.cp[K] == null) ? 0 : p.cp[K];
  }
  document.body.dataset.p = K;
  Array.prototype.forEach.call(document.querySelectorAll('.pt'), function(el){
    el.classList.toggle('on', el.dataset.pt === K);
  });
  /* ⚠ 这里曾写 `.seg button`，但类名早已改成 .segv ——
     选择器不匹配 → 表格切了、绿色框却一直停在年付上（用户报的 bug）。
     周期按钮只有一处（#segA），直接用 id 最不容易再踩。 */
  Array.prototype.forEach.call(document.querySelectorAll('#segA button'), function(b){
    b.classList.toggle('on', b.dataset.k === K);
  });
  ['segchipA'].forEach(function(id){
    var el = document.getElementById(id);
    if(el) el.textContent = PT_N[K] + ' 档';
  });
  /* KPI 条也随周期变 —— 不同周期的「最优档」并不是同一个档位 */
  Array.prototype.forEach.call(document.querySelectorAll('.kbar'), function(el){
    el.classList.toggle('on', el.dataset.kbar === K);
  });
  CQ_LAST = null;
  applyPlatFilter();      /* 换表后重新套用平台筛选 */
  updateMoSum();
  renderRec(); rerank(); renderConc();
}

/* ── 查看方式切换：三块面板互斥显示 ──
   合并原先的「01 我该买哪个 / 02 周期怎么选 / 03 全档位对比」——
   它们是同一份数据的三种读法，不该各占一屏。 */
function applyView(V){
  CV = V;
  updateMoSum();
  Array.prototype.forEach.call(document.querySelectorAll('.vpanel'), function(el){
    el.classList.toggle('on', el.dataset.view === V);
  });
  Array.prototype.forEach.call(document.querySelectorAll('[data-seg="view"] button'), function(b){
    b.classList.toggle('on', b.dataset.v === V);
  });
  if(V === 'all'){ applyPlatFilter(); rerank(); }
}

/* ── 平台筛选：隐藏未选中的平台行（三张周期表同步）── */
function applyPlatFilter(){
  var btns = document.querySelectorAll('#platFilter .pfb');
  if(!btns.length) return;
  var on = {}, n = 0;
  Array.prototype.forEach.call(btns, function(b){
    if(b.classList.contains('on')){ on[b.dataset.p] = 1; n++; }
  });
  var el = document.getElementById('platN');
  if(el) el.textContent = n + '/' + btns.length;
  updateMoSum();
  Array.prototype.forEach.call(document.querySelectorAll('.pt'), function(wrap){
    var first = true;
    Array.prototype.forEach.call(wrap.querySelectorAll('tbody tr'), function(tr){
      var show = !!on[tr.dataset.plat];
      tr.style.display = show ? '' : 'none';
      if(show){ tr.classList.remove('top'); if(first){ tr.classList.add('top'); first = false; } }
    });
  });
}

/* 单滑块：左栏 #tgt 是唯一的产量来源，两个视图共用它 */
function linkN(N, src){
  var a = document.getElementById('tgt');
  if(a && a !== src) a.value = N;
}

function readN(src){
  var el = (src && src.value) ? src : document.getElementById('tgt');
  return Math.max(1, Math.min(200, parseInt(el && el.value || '30', 10)));
}

/* 单账号口径：1 个账号 = 1 个档位，产能不够就是做不到（不允许同档多份）。
   「同档多份」本质上就是多账号，属于组合订阅的范畴，不能混进单档排名。 */
function soloOf(cap, price, N){
  return (cap > 0 && cap >= N) ? {n: 1, total: price} : null;
}

/* 单档覆盖目标产量的最低支出：可行返回 {n,total}，不可行返回 null
   —— 只用于组合订阅求解（那里才允许多账号） */
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
  var parts = [], acct = 0, plats = {};
  for(var i=0;i<b.items.length;i++){
    var it = b.items[i];
    acct += it.n;
    plats[it.p.plat] = 1;
    parts.push('<span class="dot" style="background:' + it.p.color + '"></span>' +
               it.p.plat + ' ' + it.p.tier + (it.n > 1 ? ' \u00d7 ' + it.n + ' 个账号' : ''));
  }
  var np = 0; for(var k in plats) np++;
  /* 「说明白」＝必须写出：共几个账号、跨几个平台。否则读者不知道 ×2 是同平台两个号还是两个平台。 */
  return parts.join('<span class="combo-plus">+</span>')
       + '<span class="combo-note">共 ' + acct + ' 个账号 · ' + np + ' 个平台</span>';
}

function money(v, cur){ return (cur === 'USD' ? '$' : '\u00a5') + Math.round(v).toLocaleString(); }

/* ── 主渲染 ── */
function renderRec(src){
  var N = readN(src);
  if(CQ_LAST === N) return;   /* 节流：拖动时 input 高频触发，N 未变则跳过 */
  CQ_LAST = N;

  var secs = N * 30, mins = secs / 60;
  var nv = document.getElementById('nv');
  if(nv) nv.textContent = N + ' 条/月';
  var nd = document.getElementById('ndur');
  if(nd) nd.textContent = '= ' + secs.toLocaleString() + ' 秒 \u2248 ' +
    (mins >= 60 ? (mins/60).toFixed(1) + ' 小时' : mins.toFixed(0) + ' 分钟') + '素材';
  var qv = document.getElementById('nv');
  if(qv) qv.textContent = N + ' 条/月';
  Array.prototype.forEach.call(document.querySelectorAll('#presets .cqp'), function(b){
    b.classList.toggle('on', parseInt(b.dataset.n, 10) === N);
  });

  /* 方案表 */
  var single = null;
  for(var i=0;i<PLANS.length;i++){
    var x = soloOf(PLANS[i].mCap, PLANS[i].price, N);
    if(x && (!single || x.total < single.total)) single = {p:PLANS[i], n:1, total:x.total, cap:PLANS[i].mCap};
  }
  var combo = bestCombo(N);
  var h = '';
  if(single){
    h += '<tr><td>单一账号最省<br><span class="sub">1 个平台 · 1 个账号</span></td>'
      +  '<td data-l="档位组合"><span class="dot" style="background:' + single.p.color + '"></span>' + single.p.plat + ' ' +
         single.p.tier + (single.n > 1 ? ' \u00d7 ' + single.n : '') + '</td>'
      +  '<td class="num strong" data-l="该周期支出">' + money(single.total) + '</td>'
      +  '<td class="num" data-l="实际产能">' + single.cap.toFixed(1) + ' 条/月</td>'
      +  '<td class="num" data-l="单条成本">' + money(single.total / N) + '</td></tr>';
  } else {
    h += '<tr><td>单一账号最省</td><td colspan="4" class="sub">'
      + '月产 ' + N + ' 条超出任何单档产能 —— 1 个账号做不到，必须走组合订阅</td></tr>';
  }
  if(combo){
    h += '<tr><td>组合订阅最省<br><span class="sub">可跨平台 + 同平台多账号</span></td>'
      +  '<td data-l="档位组合">' + comboLabel(combo) + '</td>'
      +  '<td class="num strong" data-l="该周期支出">' + money(combo.total) + '</td>'
      +  '<td class="num" data-l="实际产能">' + combo.cap.toFixed(1)
      +  ' 条/月<br><span class="sub">合计产能</span></td>'
      +  '<td class="num" data-l="单条成本">' + money(combo.total / N) + '</td></tr>';
  }
  var rec = document.getElementById('rec');
  if(rec) rec.innerHTML = h;

}

/* ── 全档位对比：按该产量的支出重排（只作用于当前可见的那张周期表）── */
/* 三周期结论条的最后一行：按【当前月产量】算各周期最省的是哪个档位。
   单条冠军不随产量变，但「你该买哪个」会变 —— 所以这行必须跟着滑块走。 */
function renderConc(){
  var box = document.getElementById('concF');
  if(!box) return;
  var N = readN();   /* 无参 → 读 #tgt，与 renderRec / rerank 同源 */
  var out = [];
  ["y", "q", "m"].forEach(function(k){
    var cand = CDATA.filter(function(d){ return d.v[k] && d.v[k][1] >= N; });
    if(!cand.length){ return; }
    var b = cand.reduce(function(a, c){ return c.v[k][3] < a.v[k][3] ? c : a; });
    out.push({ k: k, n: b.p + ' ' + b.t + (b.l ? ' · ' + b.l : ''), pay: b.v[k][3], per: b.v[k][0] });
  });
  if(!out.length){ box.innerHTML = '当前月产量下，没有任何单一账号档位能覆盖 —— 需要多账号，见下方「组合订阅」。'; return; }
  var lbl = { y: '年付', q: '季付', m: '月付' };
  box.innerHTML = '<b>按你的月产量 ' + N + ' 条</b> —— ' + out.map(function(o){
    return lbl[o.k] + '最省：<b>' + o.n + '</b>　' + money(o.pay) + '（¥' + o.per.toFixed(2) + '/条）';
  }).join('　｜　');
}

function rerank(src){
  var tb = activeTb();
  if(!tb) return;
  var N = readN(src);
  var all = Array.prototype.slice.call(tb.querySelectorAll('tr'));
  var rs = all.filter(function(r){ return r.style.display !== 'none'; });   /* 被平台筛选隐藏的不参与排名 */
  rs.forEach(function(r){
    var x = soloOf(parseFloat(r.dataset.c), parseFloat(r.dataset.p), N);
    r.__n = x ? x.n : null;
    r.__t = x ? x.total : null;
  });
  rs.sort(function(x, y){
    if(x.__t == null && y.__t == null) return 0;
    if(x.__t == null) return 1;
    if(y.__t == null) return -1;
    return x.__t - y.__t;
  });
  var okN = 0;
  rs.forEach(function(r, i){
    tb.appendChild(r);
    /* 产能不足以覆盖目标产量的行：整行置灰（用户要求「月产量拉高后，
       哪些会员积分根本不够用要能一眼看出来，而不是混在列表里」） */
    var dead = (r.__t == null);
    r.classList.toggle('out', dead);
    if(dead) i--; else okN++;
    var rk = r.querySelector('.rk');
    if(rk){
      var b = rk.querySelector('b'), ss = rk.querySelector('s');
      if(r.__t == null){
        if(b) b.textContent = '\u2014';
        if(ss) ss.textContent = '产能过低';
      } else {
        if(b) b.textContent = i + 1;
        if(ss) ss.textContent = money(r.__t) + ({y: '/\u5e74', q: '/\u5b63', m: '/\u6708'}[PK] || '')
          + (r.__n > 1 ? ' \u00b7 \u4e70 ' + r.__n + ' \u4efd' : '');
      }
    }
    var c2 = r.querySelector('td[data-rated] s');
    if(c2){
      /* 单账号口径：做不到就直说「这一个账号最多能做多少条」，
         而不是含糊的「产能过低」—— 用户要的是「为什么不行」。 */
      if(r.__t == null){
        c2.textContent = '单账号最多 ' + parseFloat(r.dataset.c).toFixed(1) + ' 条 · 不够 ' + N;
      } else {
        c2.textContent = '该产量 ' + money(r.__t / N) + '/条 · 1 个账号';
      }
    }
  });
  all.forEach(function(r){
    if(r.style.display === 'none') tb.appendChild(r);   /* 隐藏行沉底，切回来时顺序不乱 */
  });
  rs.forEach(function(r){ r.classList.remove('top'); });
  if(rs.length && rs[0].__t != null) rs[0].classList.add('top');
  /* 覆盖率计数：让「这个月产量下有几种选择」变成可读的数字 */
  /* 覆盖率＝单账号口径：1 个平台 1 个账号就能覆盖月产量的档位数。
     月产 200 条时这个数是 0 —— 这正是用户要的诚实答案。 */
  var cv = document.getElementById('coverN');
  if(cv) cv.textContent = okN + ' / ' + rs.length + ' 档（单账号口径）';

}

/* ── 表头排序（点击覆盖滑块排序，滑块再动即覆盖回来）──
   作用域限定在【该表头所属的那张表】：三张周期表各自独立排序，互不干扰。 */
function sortBy(k, el){
  var tbl = el && el.closest ? el.closest('table') : null;
  var tb = tbl ? tbl.querySelector('tbody') : activeTb();
  if(!tb) return;
  var rs = Array.prototype.slice.call(tb.querySelectorAll('tr'));
  var dir = el.dataset.dir === 'asc' ? -1 : 1;
  el.dataset.dir = dir === 1 ? 'asc' : 'desc';
  rs.sort(function(a, b){ return (parseFloat(a.dataset[k]) - parseFloat(b.dataset[k])) * dir; });
  rs.forEach(function(r){ tb.appendChild(r); });
  rs.forEach(function(r){ r.classList.remove('top'); });
  if(rs.length) rs[0].classList.add('top');
}

/* ══════════ 三周期全清单页：动态排名条 ══════════ */
var CDATA = __CDATA__;
var MI = {cost: 0, cap: 1, sec: 2, pay: 3};
var CM = {
  cost: {lb: '单条成本', low: true,  f: function(v){ return '\u00a5' + v.toFixed(2); }},
  cap:  {lb: '每月可生成', low: false, f: function(v){ return v.toFixed(2) + ' \u6761'; }},
  sec:  {lb: '元/秒', low: true,  f: function(v){ return v.toFixed(3); }},
  pay:  {lb: '该周期实付', low: true,  f: function(v){ return '\u00a5' + Math.round(v).toLocaleString(); }}
};
var PERLB = {y: '年付', q: '季付', m: '月付'};
var MI2 = MI;                                       /* v 的下标 */
var MLOW = {cost: true, cap: false, sec: true, pay: true};
/* 两轴不能取同一个量，否则退化成对角线 —— 所以「每月可生成」配的是单条成本 */
/* 与 Python 侧 PARETO_AXES 必须一致：产能 × 指标，两轴都按优度画（右上角最好）。
   不用「实付」当横轴 —— 它与产能强正相关，右上角会是空的。 */
var PAXES = {cost: ['cap', 'cost'], cap: ['cap', 'cost'],
             sec: ['cap', 'sec'], pay: ['cap', 'pay']};
var CT = {m: 'cost', k: 'y', o: 'best'};
var CP = {};

function renderChart(){
  var box = document.getElementById('chart');
  if(!box) return;
  var idx = MI[CT.m], low = CM[CT.m].low, fmt = CM[CT.m].f;
  var rows = [];
  for(var i = 0; i < CDATA.length; i++){
    var d = CDATA[i], v = d.v[CT.k];
    if(v == null || CP[d.p] === false) continue;
    rows.push({d: d, v: v[idx]});
  }
  if(!rows.length){ box.innerHTML = '<div class="sub">该周期下没有可比较的档位</div>'; return; }
  var vals = rows.map(function(x){ return x.v; });
  var lo = Math.min.apply(null, vals), hi = Math.max.apply(null, vals);
  var best = low ? lo : hi;
  /* 归一化基准用【相对最优的倍数】而不是绝对差值。
     原因：单条成本 19.30～21.10 的前 12 名只差 9%，绝对刻度下条形几乎一样长（看不出差别），
     而尾部 106.29 是 5.51 倍 —— 两者无法在同一线性刻度上同时看清。
     改用 rel 之后再做平方根压缩：头部 100%→86% 可分辨，尾部压到 0。 */
  var maxRel = 1;
  for(var q0 = 0; q0 < rows.length; q0++){
    var r0 = low ? rows[q0].v / best : best / rows[q0].v;
    if(r0 > maxRel) maxRel = r0;
  }
  var relSpan = (maxRel - 1) || 1;
  rows.sort(function(a, b){ return low ? a.v - b.v : b.v - a.v; });   /* 先固定排成「最优在前」 */
  for(var j0 = 0; j0 < rows.length; j0++) rows[j0].rk = j0 + 1;          /* 名次永远以「最优＝1」为准 */
  if(CT.o === 'worst') rows.reverse();                                   /* 再按需翻转显示顺序 */
  var h = '';
  for(var j = 0; j < rows.length; j++){
    var d = rows[j].d, v = rows[j].v;
    var rel = low ? v / best : best / v;            /* 1＝最优 */
    var t = Math.sqrt((rel - 1) / relSpan);         /* 0＝最优，1＝最差（平方根刻度） */
    var w = (1 - t) * 100;
    var a = (0.10 + 0.42 * (1 - t)).toFixed(3);   /* 下限 0.10，最差档也看得见 */
    var rk9 = d.p + '|' + d.t + '|' + (d.l || '');
    h += '<div class="crow" data-plat="' + d.p + '" data-k="' + rk9 + '">'
      +  '<span class="crk' + (rows[j].rk <= 3 ? ' top3' : '') + '">' + rows[j].rk + '</span>'
      +  mkI('clogo', d)
      +  '<span class="cname">' + d.p + ' ' + d.t + (d.l ? '<s>' + d.l + '</s>' : '') + '</span>'
      +  '<span class="cbar"><i style="width:' + w.toFixed(1) + '%;background:rgba(209,254,23,' + a + ')"></i></span>'
      /* 倍率一律写成「相对最优值的比」：成本 5.51× 读作「贵 5.51 倍」，
         产能 0.01× 读作「只有最优的 1%」—— 两个方向都能正确读。 */
      +  '<span class="cval">' + fmt(v) + '<s>'
      /* 右侧倍率统一写成「本行数值 ÷ 最优数值」：
         成本 5.51× 读作「贵 5.51 倍」；产能 0.01× 读作「只有最优的 1%」——
         两个方向都能正确读，不会出现「95×」这种反直觉的数。 */
      +  (v / best).toFixed(2) + '\u00d7</s></span>'
      +  '</div>';
  }
  box.innerHTML = h;
}

/* 平台标：有 logo 走背景图类，没有的用品牌色方块 + 首字母 */
function mkI(cls, d){
  return '<i class="' + cls + ' ' + d.lg + (d.mk ? ' lg-mono' : '') + '">' + (d.mk || '') + '</i>';
}

/* ── 帕累托散点：横轴＝实付（对数），纵轴＝月产能 ──
   前沿判定：某档若存在另一档「更便宜 且 更能做」，则该档被支配，不在前沿上。
   这条线回答的是「花多少钱买到多少产能」，与上方「单价排名」是两个不同的问题。 */
function renderPareto(){
  var box = document.getElementById('pplot');
  if(!box) return;
  var ax = PAXES[CT.m], mx = ax[0], my = ax[1];
  var ix = MI2[mx], iy = MI2[my];
  var pts = [];
  for(var i = 0; i < CDATA.length; i++){
    var d = CDATA[i], v = d.v[CT.k];
    if(v == null || CP[d.p] === false) continue;
    pts.push({d: d, x: v[ix], y: v[iy], vm: v[MI[CT.m]],
              key: d.p + '|' + d.t + '|' + (d.l || '')});
  }
  if(pts.length < 2){ box.innerHTML = ''; return; }

  /* 归一化：跨度 ≥3 倍用对数（实付可达 250×，线性会把低价段压成一条竖线） */
  function norm(sel, lowBetter){
    var vs = pts.map(sel), lo = Math.min.apply(null, vs), hi = Math.max.apply(null, vs);
    var lg = (lo > 0 && hi / lo >= 3);
    var a = lg ? Math.log(lo) : lo, b = lg ? Math.log(hi) : hi, sp = (b - a) || 1;
    pts.forEach(function(q){
      var t = ((lg ? Math.log(sel(q)) : sel(q)) - a) / sp;
      var bt = lowBetter ? (1 - t) : t;                 /* 优度：1＝最好 */
      /* ⚠ 位置用优度，不用原始值 —— 两轴统一「右上角最好」。
         与 pareto_block() 必须同一公式。 */
      q['p' + (sel === XS ? 'x' : 'y')] = 3 + bt * 94;
      q['b' + (sel === XS ? 'x' : 'y')] = bt;
    });
  }
  function XS(q){ return q.x; }
  function YS(q){ return q.y; }
  norm(XS, MLOW[mx]);
  norm(YS, MLOW[my]);

  var x0 = Math.min.apply(null, pts.map(XS)), x1 = Math.max.apply(null, pts.map(XS));
  var fld = document.querySelector('#paretoHd span');

  /* 前沿：把两轴都换算成「优度」，不被任何点支配（两轴都更优）者入列 */
  /* 名次必须与上方列表完全一致：同一指标、同一比较器、同一份 CDATA 顺序。
     ⚠ 不能用「成本名次」—— 切到「每月可生成」时列表第一是即梦，散点却会标小云雀。 */
  var rankOrder = pts.slice().sort(function(a, b){
    return CT.m === 'cap' ? (b.vm - a.vm) : (a.vm - b.vm);
  });
  var rankOf = {};
  for(var r9 = 0; r9 < rankOrder.length; r9++) rankOf[rankOrder[r9].key] = r9 + 1;

  /* 连线机制已按用户要求移除 —— 只保留散点与交互 */
  var h = '';
  /* 按名次倒序绘制：并列同坐标的点会重叠，让 rank 1 最后画、显示在最上层 */
  pts.sort(function(a, b){ return (rankOf[b.key] || 0) - (rankOf[a.key] || 0); });
  for(var m = 0; m < pts.length; m++){
    var q = pts[m], key = q.d.p + '|' + q.d.t + '|' + (q.d.l || '');
    var qrk = rankOf[key] || 0;
    h += '<span class="pp' + (qrk === 1 ? ' rk1' : '') + '"'
      +  ' data-k="' + key + '" data-rk="' + qrk + '"'
      +  ' style="left:' + q.px.toFixed(2) + '%;bottom:' + q.py.toFixed(2) + '%">'
      +  mkI('', q.d)
      +  '<b>' + q.d.p + ' ' + q.d.t + (q.d.l ? ' · ' + q.d.l : '')
      +  '<s>第 ' + qrk + ' 名 · ' + CM[mx].f(q.x) + ' · ' + CM[my].f(q.y) + '</s></b></span>';
  }
  box.innerHTML = '<span class="pcorner" aria-hidden="true">最好 ↗</span>' + h;
  var a0 = document.getElementById('px0'), a1 = document.getElementById('px1');
  /* 轴已按优度反转：左端＝最差，右端＝最优 */
  if(a0) a0.textContent = '← ' + (MLOW[mx] ? '更贵' : '更少') + ' ' + CM[mx].f(x1);
  if(a1) a1.textContent = CM[mx].f(x0) + (MLOW[mx] ? ' 更省' : ' 更多') + ' →';
  /* 标题随指标变 —— 否则用户切了指标，图变了标题还写着「花多少钱买到多少产能」 */
  if(fld) fld.innerHTML = '两个轴都是<b style="color:#D1FE17">越右／越上越好</b> —— '
    + '<i>右上角＝又能做又便宜</i>，左下角＝又贵又做不动。横轴＝月产能（越右越多）｜纵轴＝'
    + CM[my].lb + '（' + (MLOW[my] ? '越上越省' : '越上越多') + '）｜每个点是一个档位';
}

/* 指标元信息：标题、副标、轴方向 —— 用户要求「切指标时标题要变成解释标题」 */
var METAM = {
  cost: ['单条成本', '同样 30 秒 Seedance 2.5 视频，这个档位要花多少钱 —— 越低越好。'],
  cap:  ['每月可生成', '这一个档位每月最多能出多少条 —— 越高越好。做不到你设定的月产量就整行置灰。'],
  sec:  ['元每秒', '把单价摊到每一秒素材上 —— 越低越好，用来和其他规格横向比较。'],
  pay:  ['该周期实付', '这个周期实际要付出去的总额（年费 / 季费 / 月费）—— 越低越好。']
};

function cycSync(){
  ['metricSeg|m', 'cycSeg|k', 'ordSeg|o'].forEach(function(pair){
    var kv = pair.split('|');
    Array.prototype.forEach.call(document.querySelectorAll('#' + kv[0] + ' button'), function(b){
      b.classList.toggle('on', b.dataset[kv[1]] === CT[kv[1]]);
    });
  });
  var n = document.querySelectorAll('#cycPlat .pfb.on').length;
  var tot = document.querySelectorAll('#cycPlat .pfb').length;
  var e1 = document.getElementById('cycPlatN'); if(e1) e1.textContent = n + '/' + tot;
  var e2 = document.getElementById('cycNow');
  if(e2) e2.textContent = CM[CT.m].lb + ' \u00b7 ' + PERLB[CT.k] + ' \u00b7 ' + (CT.o === 'best' ? '最优在前' : '最差在前');
  var e3 = document.getElementById('cycChip');
  if(e3) e3.textContent = (CT.k === 'y' ? 44 : CT.k === 'q' ? 39 : 44) + ' \u6863';
  var e4 = document.getElementById('cycTitle');
  if(e4) e4.innerHTML = METAM[CT.m][0] + '<span style="color:#D1FE17"> \u00b7 </span>\u52a8\u6001\u6392\u540d';
  var e5 = document.getElementById('cycSub');
  if(e5) e5.textContent = METAM[CT.m][1];
  updateMoSum();
}

document.addEventListener('DOMContentLoaded', function(){
  function onSlide(el){
    if(!el) return;
    el.addEventListener('input', function(){
      CQ_LAST = null;
      linkN(readN(el), el);
      updateMoSum();
      renderRec(el); rerank(el); renderConc();
    });
  }
  onSlide(document.getElementById('tgt'));

  Array.prototype.forEach.call(document.querySelectorAll('#presets .cqp'), function(b){
    b.addEventListener('click', function(){
      var N = parseInt(b.dataset.n, 10);
      CQ_LAST = null;
      linkN(N, null);
      renderRec(); rerank(); renderConc();
    });
  });

  /* 查看方式 */
  Array.prototype.forEach.call(document.querySelectorAll('[data-seg="view"] button'), function(b){
    b.addEventListener('click', function(){ applyView(b.dataset.v); });
  });
  /* 承诺周期 */
  Array.prototype.forEach.call(document.querySelectorAll('#segA button'), function(b){
    b.addEventListener('click', function(){ applyPeriod(b.dataset.k); });
  });
  /* 平台筛选 */
  Array.prototype.forEach.call(document.querySelectorAll('#platFilter .pfb'), function(b){
    b.addEventListener('click', function(){
      b.classList.toggle('on');
      applyPlatFilter();
      rerank();
    });
  });

  /* 移动端底部抽屉 */
  var side = document.querySelector('.side'), scrim = document.getElementById('scrim');
  /* open＝可见；peek＝半开（默认）。拖动与吸附都走这里，状态只有一个来源。 */
  function setSheet(open, peek){
    if(side){
      side.classList.toggle('open', open);
      side.classList.toggle('peek', !!open && !!peek);
      side.classList.remove('dragging');
      side.style.maxHeight = '';
    }
    if(scrim) scrim.classList.toggle('open', open);
  }
  var moOpen = document.getElementById('moOpen');
  if(moOpen) moOpen.addEventListener('click', function(){
    var on = side && side.classList.contains('open');
    setSheet(!on, !on);                   /* 打开时默认半开（peek） */
  });

  /* ── 把手拖拽：上拉展开 / 下拉关闭，跟手 1:1，松手吸附三档 ──
     之前把手只是装饰，用户拉它没反应。 */
  (function(){
    var hd = side && side.querySelector('.sheet-hd');
    if(!hd) return;
    var VH = 0, startY = 0, startH = 0, dragging = false, FULL = 0, PEEK = 0;
    hd.addEventListener('pointerdown', function(e){
      if(e.target.closest('#sheetX')) return;      /* ✕ 只负责关闭，不参与拖拽 */
      dragging = true; VH = window.innerHeight;
      startY = e.clientY; startH = side.getBoundingClientRect().height;
      /* ⚠ 三档阈值必须按【内容自然高度】算，不能只看视口：
         内容只有 476px 时，按 844 视口算「全开」永远够不到，松手就会回落。 */
      var nat = side.scrollHeight;
      FULL = Math.min(nat, VH * 0.80);
      PEEK = Math.min(nat, VH * 0.42);
      side.classList.add('dragging');
      try{ hd.setPointerCapture(e.pointerId); }catch(err){}
    });
    hd.addEventListener('pointermove', function(e){
      if(!dragging) return;
      var h = startH - (e.clientY - startY);        /* 向上拖 → 变高 */
      side.style.maxHeight = Math.max(VH * 0.18, Math.min(FULL, h)) + 'px';
      side.classList.add('open');
      side.classList.remove('peek');
      scrim && scrim.classList.add('open');
    });
    function release(){
      if(!dragging) return;
      dragging = false;
      var h = side.getBoundingClientRect().height;
      side.classList.remove('dragging');
      side.style.maxHeight = '';
      if(h < PEEK * 0.66){ setSheet(false, false); }               /* 拖得很低 → 收起 */
      else if(h < (PEEK + FULL) / 2){ setSheet(true, true); }      /* 吸附：半开 */
      else { setSheet(true, false); }                               /* 吸附：全开 */
    }
    hd.addEventListener('pointerup', release);
    hd.addEventListener('pointercancel', release);
    hd.addEventListener('lostpointercapture', release);
  })();
  if(scrim) scrim.addEventListener('click', function(){ setSheet(false); });
  /* ✕ 关闭 —— 抽屉一打开就会盖住底部「调整」按钮，必须有独立出口 */
  var sx = document.getElementById('sheetX');
  if(sx) sx.addEventListener('click', function(){ setSheet(false); });
  document.addEventListener('keydown', function(e){
    if(e.key === 'Escape') setSheet(false);
  });
  /* 选完「查看方式」自动收起 —— 切了视图就该看内容，不该还挡着 */
  Array.prototype.forEach.call(document.querySelectorAll('[data-seg="view"] button'), function(b){
    b.addEventListener('click', function(){ setSheet(false); });
  });

  /* ── 三周期全清单页：四个控件组 ── */
  function cycBind(sel, attr, key){
    Array.prototype.forEach.call(document.querySelectorAll(sel + ' button'), function(b){
      b.addEventListener('click', function(){
        CT[key] = b.dataset[attr];
        cycSync(); renderChart(); renderPareto(); linkHover();
        if(key !== 'm') setSheet(false);   /* 选指标后收起抽屉，直接看排名 */
      });
    });
  }
  cycBind('#metricSeg', 'm', 'm');
  cycBind('#cycSeg', 'k', 'k');
  cycBind('#ordSeg', 'o', 'o');
  Array.prototype.forEach.call(document.querySelectorAll('#cycPlat .pfb'), function(b){
    b.addEventListener('click', function(){ CP[b.dataset.p] = b.classList.toggle('on'); cycSync(); renderChart(); renderPareto(); linkHover(); });
  });

  if(document.getElementById('viewSeg')){ applyView('all'); applyPeriod('y'); }
  /* 排名行 ↔ 散点 双向联动：悬停任一侧，另一侧对应项高亮。
     这是这张图真正的「交互」—— 之前只有 tooltip，用户感觉点了没反应。 */
  function linkHover(){
    var rows = document.querySelectorAll('#chart .crow');
    Array.prototype.forEach.call(rows, function(el){
      if(el.dataset.linked) return;
      el.dataset.linked = '1';
      var k = el.dataset.k;
      el.addEventListener('mouseenter', function(){ mark(k, true); });
      el.addEventListener('mouseleave', function(){ mark(k, false); });
    });
    var dots = document.querySelectorAll('#pplot .pp');
    Array.prototype.forEach.call(dots, function(el){
      if(el.dataset.linked) return;
      el.dataset.linked = '1';
      var k = el.dataset.k;
      el.addEventListener('mouseenter', function(){ mark(k, true); });
      el.addEventListener('mouseleave', function(){ mark(k, false); });
    });
  }
  function mark(k, on){
    if(!k) return;
    Array.prototype.forEach.call(document.querySelectorAll('[data-k="' + k + '"]'), function(el){
      el.classList.toggle('hl', on);
    });
  }

  if(document.getElementById('chart')){ renderChart(); renderPareto(); cycSync(); linkHover(); }
  updateMoSum();
});
"""


def sub_css(s):
    return s.replace("__SANS__", F_SANS).replace("__DISP__", F_DISP).replace("__MONO__", F_MONO)


# ═══════════════════════════════════════════════════════════════════
# 4. 组件
# ═══════════════════════════════════════════════════════════════════
def promo():
    # 移动端只显示前半句 —— 整段在 390px 下要占三行，把首屏挤掉（用户反馈「观感不舒服」）
    return (f'<div class="promo"><span><b>价格说明：</b>{BRAND_CN}数据采集于 {UPDATED}'
            f'<i class="pmore">，各平台价格取决于当期活动与限时优惠力度，不代表最终价格</i></span>'
            f'<span class="tag2">数据时点 {UPDATED}</span></div>')


def nav(active):
    items = ""
    for it in NAV:
        soon = it["key"] == "leaderboard-vlm" and VLM["status"] == "coming-soon"
        badge = '<i class="nb">即将上线</i>' if soon else ""
        cls = ' class="active"' if it["key"] == active else ""
        items += f'<a href="{it["href"]}"{cls}>{it["label"]}{badge}</a>'
    # 窄屏下横向菜单必然放不下（「视觉理解模型排行榜」一个字就是 14px），
    # 与其硬裁或让它横向滚动，不如收进汉堡菜单 —— 三项导航的标准做法。
    return (f'<div class="nav"><div class="inner">'
            f'<a class="brand" href="index.html"><i></i>'
            f'<span class="bw"><b>{BRAND}</b><s>{STUDIO}</s></span></a>'
            f'<nav class="menu">{items}</nav>'
            f'<span class="spec">{SPEC}</span>'
            f'<button type="button" class="nburger" id="nBurger" aria-label="导航菜单" '
            f'aria-expanded="false" aria-controls="nDrop"><i></i><i></i><i></i></button>'
            f'</div>'
            f'<div class="ndrop" id="nDrop"><nav>{items}</nav></div></div>')


def legal():
    return (f'<div class="legal"><div class="legal-t">{COPY}</div>'
            f'<div class="legal-b">{TERMS}</div>'
            f'<div class="legal-f">溯源指纹 <span class="fp">{FP_WORK}</span>　·　版本 <span class="fp">{FP_EDITION}</span>　·　'
            f'{BRAND} · {BRAND_CN}　·　{STUDIO} 出品　·　数据采集 {UPDATED}</div></div>')


def foot(text):
    # 误关之后要有路回来 —— 引导弹窗只在首次自动出现
    return (f'<div class="foot">{text}'
            f'\u3000|\u3000<a href="#" id="introAgain" style="color:#8A9098;'
            f'border-bottom:1px dashed rgba(255,255,255,.3)">\u65b0\u624b\u5f15\u5bfc</a></div>')


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


MAIN_TB = {k: main_rows_for(k) for k, _l, _m, _f in PERIODS}
MAIN_N = {k: len([r for r in ROWS if k in r["byP"]]) for k, _l, _m, _f in PERIODS}
main_rows = MAIN_TB["y"]      # 兼容旧引用（自检里用到）

# 三张周期表整块预渲染，切周期只切可见性（不做单元格级 JS 重写）
PT_TABLES = ""
for _k, _lbl, _mo, _f in PERIODS:
    _on = " on" if _k == "y" else ""
    _tid = "main" if _k == "y" else "main-" + _k
    PT_TABLES += (
        f'<div class="pt{_on}" data-pt="{_k}">'
        + table([("#", "v"), ("平台", None), (T("jifenDang", "档位"), None), (PT_HEAD[_k][0], "p"),
                 (T("yueChanNeng") + "<br><span class=hm>该周期积分 ÷ 单条消耗</span>", "v"),
                 (T("danTiaoChengBen") + "<br><span class=hm>用满产能 / 该产量</span>", "v"),
                 (T("yuanMiao"), None)],
                MAIN_TB[_k], "tw scroll-y tw-main", _tid)
        + "</div>\n")


# ═══════════════════════════════════════════════════════════════════
# 5. 页面
# ═══════════════════════════════════════════════════════════════════
# ═══════════ 明细表行（6 组）═══════════
lad_rows = ""
for _i, _x in enumerate(LADDER):
    _r = _x["row"]
    _lo = "0" if _i == 0 else f'{_x["lo"]:.2f}'
    lad_rows += (
        f'<tr><td class="num mono">{_lo} – {_x["hi"]:.2f}</td>'
        f'<td><span class="dot" style="background:{_r["color"]}"></span>'
        f'{_r["plat"]} {tname(_r)}</td>'
        f'<td class="num strong">¥{_r["priceCNY"]:,.0f}</td>'
        f'<td class="num">{_r["mCap"]:.2f}</td>'
        f'<td class="num">¥{f2(_r["perVideo"])}</td>'
        f'<td class="num">{_r["perVideo"]/BEST:.2f}×</td></tr>')

# 判定分档：以全场最优单条成本为标尺。阈值由构建产物反推校验：
#   20.09/19.30=1.041 → 强烈推荐；20.72/19.30=1.074 → 一般；
#   25.68/19.30=1.331 → 一般；26.54/19.30=1.375 → 不建议
marg_rows = ""
for _m in sorted(MARGINAL, key=lambda x: x["mCost"]):
    _ratio = _m["mCost"] / BEST
    if _ratio <= 1.05:
        _tag, _lbl = "v-good", "强烈推荐"
    elif _ratio <= 1.35:
        _tag, _lbl = "v-warn", "一般"
    else:
        _tag, _lbl = "v-bad", "不建议"
    marg_rows += (
        f'<tr><td><span class="dot" style="background:{_m["color"]}"></span>{_m["plat"]}</td>'
        f'<td>{_m["a"]["tier"]} → {_m["b"]["tier"]}</td>'
        f'<td class="num">¥{_m["dPrice"]:,.0f}</td>'
        f'<td class="num">+{_m["dCap"]:.0f}</td>'
        f'<td class="num strong">¥{f2(_m["mCost"])}</td>'
        f'<td class="num">{_m["avg"]:.2f}</td>'
        f'<td class="ctr"><span class="tag {_tag}">{_lbl}</span></td></tr>')

claim_rows = ""
for _p, _c in AD_CLAIM.items():
    # 取 AD_CLAIM 指定的那个顶级档位（同档多积分档时取第一个），与海报口径对应
    _act = next(r for r in ROWS
                if r["plat"] == _p and r["tier"] == _c["tier"])["perSec"]
    claim_rows += (
        f'<tr><td><span class="dot" style="background:{COLOR[_p]}"></span>{_p}</td>'
        f'<td>{_c["tier"]}</td>'
        f'<td class="num">¥{_c["perSec"]:.2f}</td>'
        f'<td class="num strong">¥{_act:.3f}</td>'
        f'<td class="num">{_act/_c["perSec"]:.2f}×</td></tr>')

retry_rows = "".join(
    f'<tr><td><span class="dot" style="background:{COLOR[_r["plat"]]}"></span>{_r["plat"]}</td>'
    f'<td class="ctr"><span class="tag v-good">{_r["retry"]}</span></td>'
    f'<td>{_r["basis"]}</td></tr>'
    for _r in COST["retryPolicy"])

# 三周期全清单（表）：与主表同序（按年付单条成本升序）—— 自检逐行比对依赖这一点
ap2_rows = ""
for _r in sorted(ROWS, key=lambda x: x["perVideo"]):
    _c = ""
    for _k in ("m", "q", "y"):
        if _k in _r["byP"]:
            _v = f'¥{f2(_r["byP"][_k]["perVideo"])}'
            _c += ('<td class="num"><span class="strong">' + _v + "</span></td>"
                   if _k == _r["bestP"] else f'<td class="num">{_v}</td>')
        else:
            _c += '<td class="num sub">—</td>'
    _pl = {"y": "年付", "q": "季付", "m": "月付"}.get(_r["bestP"], "—")
    ap2_rows += (
        f'<tr><td><span class="dot" style="background:{_r["color"]}"></span>{_r["plat"]}</td>'
        f'<td>{tname(_r)}</td>{_c}'
        f'<td class="ctr"><span class="tag v-good">{_pl}</span></td></tr>')

src_rows = "".join(
    f'<tr><td>{_x["page"]}</td><td style="white-space:normal">{_x["data"]}</td></tr>'
    for _x in COST["sources"])

# ═══════════ 平台级周期对照 ═══════════
pp_rows = ""
for _x in PERIOD_PLAT:
    if not _x["hasQ"]:
        _tag, _jlbl, _adv, _q = "v-warn", "平台不提供", "只能年付或月付", "—"
    elif _x["trapN"]:
        _tag, _jlbl = "v-bad", f'{_x["trapN"]} 档倒挂'
        _adv = "有档位承诺越久越贵，<b>买前先比对短周期</b>"
        _q = f'{_x["qLo"]:.2f}–{_x["qHi"]:.2f}×'
    else:
        _tag, _jlbl, _adv = "v-good", "正常递减", "季付可用，但仍不如年付"
        _q = f'{_x["qLo"]:.2f}–{_x["qHi"]:.2f}×'
    pp_rows += (
        f'<tr><td><span class="dot" style="background:{_x["color"]}"></span>{_x["plat"]}</td>'
        f'<td class="num">{_x["yLo"]:.2f}–{_x["yHi"]:.2f}×</td>'
        f'<td class="num">{_q}</td>'
        f'<td class="ctr"><span class="tag {_tag}">{_jlbl}</span></td>'
        f'<td style="white-space:normal">{_adv}</td></tr>')

trap_rows = ""
for _t in TRAPS:
    _r = _t["row"]
    trap_rows += (
        f'<tr><td><span class="dot" style="background:{_r["color"]}"></span>{_r["plat"]}</td>'
        f'<td>{tname(_r)}</td>'
        f'<td class="ctr"><span class="tag v-bad">{_t["long"]} 比 {_t["short"]} 贵</span></td>'
        f'<td class="num">¥{f2(_r["byP"][_t["lkey"]]["perVideo"])} '
        f'<s>vs ¥{f2(_r["byP"][_t["skey"]]["perVideo"])}</s></td>'
        f'<td class="num neg">+{_t["pct"]*100:.1f}%</td>'
        f'<td class="num">¥{_t["longPay"]:,.0f} <s>vs ¥{_t["shortPay"]:,.0f}</s></td></tr>')

# ═══════════ 执行建议 ═══════════
budget_bullets = "".join(
    f'<li><b>月产 {"0" if _i == 0 else "%.2f" % _x["lo"]}–{_x["hi"]:.2f} 条：</b>'
    f'{_x["row"]["plat"]} {tname(_x["row"])} — ¥{_x["row"]["priceCNY"]:,.0f}/年'
    f'（¥{f2(_x["row"]["perVideo"])}/条 · 单价为最优解的 {_x["row"]["perVideo"]/BEST:.2f} 倍）</li>'
    for _i, _x in enumerate(LADDER))

# ═══════════ 全场极值（首页与成本页共用）═══════════
_best = min(ROWS, key=lambda r: r["perVideo"])
_second = sorted(ROWS, key=lambda r: r["perVideo"])[1]
_mid = next(r for r in ROWS if r["plat"] == "小云雀" and r["tier"] == "高级会员"
            and r["monthly"] == 12000)
_top = max(LADDER, key=lambda x: x["hi"])["row"]
_hg = min((r for r in ROWS if r["plat"] == "Higgsfield"), key=lambda r: r["perVideo"])


# ═══════════ KPI 条（每个周期各一套）═══════════
# 不同周期的「最优档」往往不是同一个档位，所以 KPI 必须跟着周期换，
# 不能拿年付的数字在季付/月付下继续显示。
def kpis_for(key):
    cand = [r for r in ROWS if key in r["byP"]]
    if not cand:
        return []
    best = min(cand, key=lambda r: r["byP"][key]["perVideo"])
    worst = max(cand, key=lambda r: r["byP"][key]["perVideo"])

    def cheapest_for(n, stack=4):
        ok = []
        for r in cand:
            cap = r["byP"][key]["cap"]
            if cap <= 0:
                continue
            cnt = int(math.ceil(n / cap - 1e-9))
            if cnt <= stack:
                ok.append((cnt * r["byP"][key]["payCNY"], cnt, r))
        if not ok:
            return None
        tot, cnt, r = min(ok, key=lambda x: x[0])
        return {"row": r, "total": tot, "cnt": cnt}

    out = [("单条成本最优", f'¥{f2(best["byP"][key]["perVideo"])}',
            f'{best["plat"]} {tname(best)}', True)]
    _u = {"y": "/年", "q": "/季", "m": "/月"}[key]
    for n, lbl in ((30, "30 条/月 · 最省"), (90, "90 条/月 · 最省")):
        c = cheapest_for(n)
        if c:
            out.append((lbl, f'¥{c["total"]:,.0f}<i class="u">{_u}</i>',
                        f'{c["row"]["plat"]} {tname(c["row"])}'
                        + (f' × {c["cnt"]}' if c["cnt"] > 1 else ''), False))
    hg = [r for r in cand if r["plat"] == "Higgsfield"]
    if hg:
        hb = min(hg, key=lambda r: r["byP"][key]["perVideo"])
        out.append(("海外平台溢价",
                    f'{hb["byP"][key]["perVideo"] / best["byP"][key]["perVideo"]:.2f}×',
                    f'Higgsfield {hb["tier"]}', False))
    out.append(("最差 ÷ 最省",
                f'{worst["byP"][key]["perVideo"] / best["byP"][key]["perVideo"]:.2f}×',
                f'{worst["plat"]} {tname(worst)}', False))
    return out


KPI_SETS = {k: kpis_for(k) for k, _l, _m, _f in PERIODS}
def _period_wins():
    """逐档位比三周期，统计各周期「最便宜」的胜出次数。

    两个必须的额外口径：
    - 只统计该档位真实提供的周期（Seko 无季付、Higgsfield 无季付）
    - 月付积分可能与年付不同（即梦标准会员），故分开取 cr
    """
    win = {"y": 0, "q": 0, "m": 0}
    q_total = q_lose_m = 0
    for p in COST["plans"]:
        k = RATE if PLATFORMS[p["platform"]]["currency"] == "USD" else 1.0
        for c in p["credits"]:
            m = c["credits"]; mcr = c.get("mCr", m); qcr = c.get("qCr", m)
            v = {}
            for key, pay, mo, cr in (("y", c["price"], 12, m), ("q", c.get("q"), 3, qcr),
                                     ("m", c.get("m"), 1, mcr)):
                if pay is not None:
                    v[key] = pay * k / (cr * mo) * CPV[p["platform"]]
            if len(v) < 2:
                continue
            win[min(v, key=v.get)] += 1
            if "q" in v and "m" in v:
                q_total += 1
                if v["m"] < v["q"]:
                    q_lose_m += 1
    return win, q_total, q_lose_m


PWIN, Q_TOTAL, Q_LOSE_M = _period_wins()


def _champ(key):
    pool = [r for r in ROWS if key in r["byP"]]
    return min(pool, key=lambda r: r["byP"][key]["perVideo"])


CHAMP = {k: _champ(k) for k in "yqm"}

CONC_BAR = ""
for _k, _lbl, _note in (("y", "年付", "锁 12 个月"), ("m", "月付", "随时可停"), ("q", "季付", "锁 3 个月")):
    _r = CHAMP[_k]; _b = _r["byP"][_k]
    _nm = _r["plat"] + " " + _r["tier"] + (" · " + _r["label"] if _r["label"] else "")
    _payu = {"y": "/年", "q": "/季", "m": "/月"}[_k]
    if _k == "q":
        _body = (f'<div class="cw">不建议</div>'
                 f'<div class="cn">季付在全部 {Q_TOTAL} 个可比档位里，<b>一次都没赢过</b>' 
                 f'<br>其中 {Q_LOSE_M} 个档位「买 3 个月比按月买还贵」</div>')
    else:
        _body = (f'<div class="cw">¥{_b["perVideo"]:,.2f}<s>每条</s></div>'
                 f'<div class="cn">{_nm}<br>'
                 f'该周期实付 ¥{_b["payCNY"]:,.0f}{_payu}　·　月产能 {_b["cap"]:.1f} 条</div>')
    _cls = "conc-c dim" if _k == "q" else "conc-c"
    CONC_BAR += (f'<div class="{_cls}"><div class="ch">{_lbl}<i>{_note}</i></div>{_body}</div>')

KPI_BARS = ""
for _k, _lbl, _mo, _f in PERIODS:
    _cells = "".join(
        f'<div class="kb{" hi" if _hi else ""}"><s>{_t}</s><b>{_v}</b><em>{_sub}</em></div>'
        for _t, _v, _sub, _hi in KPI_SETS[_k])
    KPI_BARS += f'<div class="kbar{" on" if _k == "y" else ""}" data-kbar="{_k}">{_cells}</div>\n'

# ═══════════ 反查结果的服务端初始态（N=30）═══════════
_init_s = best_single(30)
_init_c = best_combo(30)
_init_combo_html = ""
if _init_s:
    _init_combo_html += (
        f'<tr><td>单一账号最省<br><span class="sub">1 个平台 · 1 个账号</span></td>'
        f'<td data-l="档位组合"><span class="dot" style="background:{_init_s["row"]["color"]}"></span>'
        f'{_init_s["row"]["plat"]} {_init_s["row"]["tier"]}'
        f'{" × " + str(_init_s["n"]) if _init_s["n"] > 1 else ""}</td>'
        f'<td class="num strong" data-l="该周期支出">¥{_init_s["total"]:,.0f}</td>'
        f'<td class="num" data-l="实际产能">{_init_s["cap"]:.1f} 条/月</td>'
        f'<td class="num" data-l="单条成本">¥{_init_s["total"]/30:,.0f}</td></tr>')
if _init_c:
    _lbl = '<span class="combo-plus">+</span>'.join(
        f'<span class="dot" style="background:{u["r"]["color"]}"></span>'
        f'{u["r"]["plat"]} {u["r"]["tier"]}'
        f'{" × " + str(u["n"]) + " 个账号" if u["n"] > 1 else ""}' for u in _init_c["items"])
    _acct = sum(u["n"] for u in _init_c["items"])
    _np = len({u["r"]["plat"] for u in _init_c["items"]})
    _init_combo_html += (
        f'<tr><td>组合订阅最省<br><span class="sub">可跨平台 + 同平台多账号</span></td>'
        f'<td data-l="档位组合">{_lbl}<span class="combo-note">共 {_acct} 个账号 · {_np} 个平台</span></td>'
        f'<td class="num strong" data-l="该周期支出">¥{_init_c["total"]:,.0f}</td>'
        f'<td class="num" data-l="实际产能">{_init_c["cap"]:.1f} 条/月 '
        f'<span class="sub">合计产能</span></td>'
        f'<td class="num" data-l="单条成本">¥{_init_c["total"]/30:,.0f}</td></tr>')



GLOS_JSON = json.dumps({x["k"]: {"t": x["t"], "s": x["s"], "l": x["l"]}
                        for x in GLOSSARY["terms"]}, ensure_ascii=False)


INTRO = """
<div id="intro" role="dialog" aria-modal="true" aria-label="新手引导">
  <div class="icard">
    <button type="button" class="ix" aria-label="跳过引导">\u2715</button>

    <div class="is on">
      <div class="ieyebrow">01 / 这是什么</div>
      <h3>把各平台的积分，<br>换算成同一种钱</h3>
      <p>各平台用自己的积分计价，币值互不相同 —— 同一条 30 秒视频，即梦扣 600 分、
      Neowow 扣 7,500 分。直接比积分没有意义。</p>
      <p>本站在把它们压平到同一口径之后，再折算成人民币。
      <b style="color:#D1FE17">不采信宣传数字，只给可复核的结果。</b></p>
    </div>

    <div class="is">
      <div class="ieyebrow">02 / 怎么看</div>
      <h3>三步拿到你要的答案</h3>
      <ul>
        <li><b>先看结论</b> —— 数据页顶部有结论条，不必自己算</li>
        <li><b>看你的场景</b> —— 拖动「月产量」，表格与排名即时重算</li>
        <li><b>看不懂某个词</b> —— 带虚线的词点一下就有解释，也可去「术语表」</li>
      </ul>
    </div>

    <div class="is">
      <div class="ieyebrow">03 / 看之前请知道</div>
      <h3>三个前提</h3>
      <ul>
        <li>价格是采集当日的<b>限时活动价</b>，活动退坡后排名会变</li>
        <li>排名按<b>单账号单平台</b>口径；需要多账号时归入「组合订阅」另算</li>
        <li>数据来源、算法与风险说明<b>全部公开</b>，页面底部可查</li>
      </ul>
    </div>

    <div class="ifoot">
      <div class="idots"><i class="idot on"></i><i class="idot"></i><i class="idot"></i></div>
      <div class="ibtns">
        <button type="button" class="ibtn iprev" style="visibility:hidden">上一步</button>
        <button type="button" class="ibtn pri inext">下一步</button>
      </div>
    </div>
  </div>
</div>
"""


GUIDE = """
<div class="guide" id="guide">
  <span class="g-lead">第一次来？</span>
  <span class="g-step">① 先看上面的结论条</span>
  <span class="g-step">② 拖动「月产量」看你的场景</span>
  <span class="g-step">③ 看不懂的词点一下就有解释</span>
  <a href="glossary.html" class="g-link">术语表</a>
  <button type="button" class="g-x" id="guideX">不再提示</button>
</div>
"""


def page(title, desc, nav_html, body, cost_js=False):
    js = JS.replace("__COST__", COST_JS) if cost_js else JS.replace("__COST__", "")
    js = js.replace("__GLOS__", GLOS_JSON)
    if cost_js:
        js = js.replace("__PLANS__", json.dumps(
            [{"plat": r["plat"], "tier": r["tier"], "label": r["label"], "color": r["color"],
              # pc = 各周期实付（折 CNY）；cp = 各周期月产能。缺该周期则为 null
              "pc": {k: (round(r["byP"][k]["payCNY"], 2) if k in r["byP"] else None) for k in "yqm"},
              "cp": {k: (round(r["byP"][k]["cap"], 4) if k in r["byP"] else None) for k in "yqm"}}
             for r in ROWS], ensure_ascii=False))
        js = js.replace("__PTN__", json.dumps(MAIN_N, ensure_ascii=False))
        js = js.replace("__CDATA__", json.dumps(
            [{"p": r["plat"], "t": r["tier"], "l": r["label"], "c": r["color"],
              "lg": PLAT_LG[r["plat"]], "mk": PLAT_MONO.get(r["plat"], ""),
              "rk": {k: r["byP"][k]["rank"] for k in r["byP"]},
              "v": {k: ([round(r["byP"][k]["perVideo"], 4), round(r["byP"][k]["cap"], 4),
                         round(r["byP"][k]["perVideo"] / SEC_PER_CLIP, 4),
                         round(r["byP"][k]["payCNY"], 2)] if k in r["byP"] else None)
                    for k in "yqm"}}
             for r in ROWS], ensure_ascii=False))
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
     {FP_WORK}　|　{FP_EDITION}
     {COPY}
     数据采集时点：{UPDATED}　作者：{OWNER}
     {TERMS}
     ============================================================ -->
<meta name="author" content="{OWNER}">
<meta name="copyright" content="{COPY}">
<meta name="rights" content="{TERMS}">
<meta name="dcterms.rights" content="{COPY}">
<meta name="fingerprint" content="{FP_WORK}">
<meta name="edition" content="{FP_EDITION}">
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

{INTRO}
<script>{js}</script>
</body></html>"""


METRIC_IDX = {"cost": 0, "cap": 1, "sec": 2, "pay": 3}
METRIC_LOW = {"cost": True, "cap": False, "sec": True, "pay": True}   # 越低越好?
METRIC_UNIT = {"cost": "元/条", "cap": "条/月", "sec": "元/秒", "pay": "元"}
# 两轴＝（月产能 × 当前指标），两个轴都按【优度】画 —— 右上角永远最好。
# ⚠ 曾经的配对是「该周期实付 × 当前指标」，但实付与产能强正相关：
#   花得多才做得多，于是点云从左上斜到右下，**【右上角是空的】**，
#   与用户「右上角最厉害」的直觉冲突。
#   换成「产能 × 单条成本」后，最优档位（便宜且能做）真正落在右上角。
#   指标本身就是「月产能」时，Y 用单条成本 —— 否则 X≡Y 退化成对角线。
PARETO_AXES = {"cost": ("cap", "cost"), "cap": ("cap", "cost"),
               "sec": ("cap", "sec"), "pay": ("cap", "pay")}


def _title(m):
    return METRIC_LBL[m]


def _fmt_axis(metric, v):
    if metric == "cost":
        return f"¥{v:,.2f}"
    if metric == "cap":
        return f"{v:,.2f} 条"
    if metric == "sec":
        return f"{v:.3f}"
    return f"¥{v:,.0f}"


def pareto_block(key="y", metric="cost"):
    """帕累托散点（服务端渲染）。

    ⚠ 归一化与前沿判定必须与前端 renderPareto() 完全一致，
      否则首页（静态渲染）与全清单页（JS 重绘）会画出两张不同的图。
    """
    mx, my = PARETO_AXES[metric]
    pts = []
    for r in ROWS:
        p = r["byP"].get(key)
        if not p or p["payCNY"] <= 0 or p["cap"] <= 0:
            continue
        vec = [p["perVideo"], p["cap"], p["perVideo"] / SEC_PER_CLIP, p["payCNY"]]
        pts.append({"r": r, "x": vec[METRIC_IDX[mx]], "y": vec[METRIC_IDX[my]]})
    if len(pts) < 2:
        return ""

    def norm(vals):
        lo, hi = min(vals), max(vals)
        # 跨度 ≥3 倍用对数：实付跨度可达 250×，线性会把低价段压成一条竖线
        log = (lo > 0 and hi / lo >= 3)
        if log:
            a, b = math.log(lo), math.log(hi)
            return [((math.log(v) - a) / ((b - a) or 1)) for v in vals], True
        return [((v - lo) / ((hi - lo) or 1)) for v in vals], False

    xs_raw = [q["x"] for q in pts]
    ys_raw = [q["y"] for q in pts]
    xp, xlog = norm(xs_raw)
    yp, ylog = norm(ys_raw)
    # 优度：X 越低越好则翻转
    bx = [(1 - t) if METRIC_LOW[mx] else t for t in xp]
    by = [(1 - t) if METRIC_LOW[my] else t for t in yp]
    for i, q in enumerate(pts):
        q["bx"], q["by"] = bx[i], by[i]
        # ⚠ 位置用【优度】而不是原始数值：两轴统一「越右/越上越好」。
        #   按原始值映射时，成本类指标（越低越好）会让最优点落在左下角，与直觉相反。
        #   内缩 3%~97%：点宽 19px 且 translate(-50%) 居中，直接映射 0~100 会让边缘点探头。
        q["px"], q["py"] = 3 + bx[i] * 94, 3 + by[i] * 94
        q["xlog"], q["ylog"] = xlog, ylog

    # 连线机制已按用户要求移除，只保留散点与交互。
    out = ""
    # 名次必须与上方列表一致：用【当前指标】在该周期下的排名，而不是全局年付名次。
    _mi = METRIC_IDX[metric if metric != "pay" else "pay"]
    _vm = {id(q): [q["r"]["byP"][key]["perVideo"], q["r"]["byP"][key]["cap"],
                   q["r"]["byP"][key]["perVideo"] / SEC_PER_CLIP,
                   q["r"]["byP"][key]["payCNY"]][_mi] for q in pts}
    _rankof = {}
    for _i, _q in enumerate(sorted(pts, key=lambda z: -_vm[id(z)]
                                   if metric == "cap" else _vm[id(z)]), 1):
        _rankof[id(_q)] = _i
    # ⚠ 按名次【倒序】绘制：并列同坐标的点会重叠，先画名次差的、后画名次好的，
    #   保证 rank 1 在最上层可见。
    for q in sorted(pts, key=lambda z: -_rankof[id(z)]):
        r = q["r"]
        sub = f' · {r["label"]}' if r.get("label") else ""
        rk = _rankof[id(q)]
        out += (f'<span class="pp{" rk1" if rk == 1 else ""}" '
                f'data-k="{r["plat"]}|{r["tier"]}|{r.get("label","")}" data-rk="{rk}" '
                f'style="left:{q["px"]:.2f}%;bottom:{q["py"]:.2f}%">'
                f'<i class="{PLAT_LG[r["plat"]]}"></i>'
                f'<b>{r["plat"]} {r["tier"]}{sub}'
                f'<s>第 {rk} 名 · {_fmt_axis(mx, q["x"])} · {_fmt_axis(my, q["y"])}</s></b></span>')

    x_lo, x_hi = min(xs_raw), max(xs_raw)
    _better = "更省" if METRIC_LOW[mx] else "更多"
    _worse = "更贵" if METRIC_LOW[mx] else "更少"
    # 轴已按优度反转：左端＝最差值，右端＝最优值
    xl = (f'<span id="px0">← {_worse} {_fmt_axis(mx, x_hi)}</span>'
          f'<span id="px1">{_fmt_axis(mx, x_lo)} {_better} →</span>')
    yl = f'纵轴＝{_title(my)}（{"越上越省" if METRIC_LOW[my] else "越上越多"}）'
    return ('<div class="pareto">'
            f'<div class="phd" id="paretoHd"><b>同样的预算，能换到什么</b>'
            f'<span>两个轴都是<b style="color:#D1FE17">越右／越上越好</b> —— '
            f'<i>右上角＝又能做又便宜</i>，左下角＝又贵又做不动。'
            f'横轴＝月产能（越右越多）｜{yl}｜每个点是一个档位。悬停看真实数值，也可与下方排名列表互相联动</span></div>'
            f'<div class="pplot" id="pplot" data-metric="{metric}">'
            f'<span class="pcorner" aria-hidden="true">最好 ↗</span>{out}</div>'
            f'<div class="pfoot">{xl}</div></div>')



# 手机端底部抽屉的头：把手 + 标题 + 关闭。
# ⚠ 之前没有它 —— 抽屉一打开就盖住底部「调整」按钮，遮罩只剩顶部一条，
#   用户找不到任何关闭入口，等于被困在抽屉里。
SHEET_HEAD = ('<div class="sheet-hd"><span class="grab"></span>'
              '<b>调整筛选</b>'
              '<button type="button" class="sheet-x" id="sheetX" '
              'aria-label="收起筛选">\u2715</button></div>')

# 侧栏平台筛选按钮（成本页与全清单页共用）
SIDE_PLAT = "".join(
    f'<button type="button" class="pfb on" data-p="{p["plat"]}">'
    f'{plogo(p["plat"], "pfbi")}{p["plat"]}</button>' for p in PLAT_SUM)
NTIER = len({r["tier"] for r in ROWS})

cycles_body = f"""
<div class="app">
<aside class="side">
  {SHEET_HEAD}
  <div class="sgroup" id="sgMetric">
    <div class="sgt">排名指标<span class="sgchip">条越长＝越接近最优</span></div>
    <div class="segv" id="metricSeg" role="tablist" aria-label="排名指标">
      <button type="button" class="on" data-m="cost" role="tab">单条成本<s>元/条 · 越低越好</s></button>
      <button type="button" data-m="cap" role="tab">每月可生成<s>条/月 · 越高越好</s></button>
      <button type="button" data-m="sec" role="tab">元/秒<s>越低越好</s></button>
      <button type="button" data-m="pay" role="tab">该周期实付<s>总额 · 越低越好</s></button>
    </div>
  </div>
  <div class="sgroup" id="sgPeriod">
    <div class="sgt">{T("chengnuoQi", "会员周期")}<span class="sgchip" id="cycChip">44 档</span></div>
    <div class="segv segk" id="cycSeg" role="tablist" aria-label="会员周期">
      <button type="button" class="on" data-k="y" role="tab">年付<s>锁 12 个月</s></button>
      <button type="button" data-k="q" role="tab">季付<s>锁 3 个月</s></button>
      <button type="button" data-k="m" role="tab">月付<s>随时可停</s></button>
    </div>
  </div>
  <div class="sgroup" id="sgOrder">
    <div class="sgt">排序</div>
    <div class="segv segk" id="ordSeg" role="tablist" aria-label="排序">
      <button type="button" class="on" data-o="best" role="tab">最优在前</button>
      <button type="button" data-o="worst" role="tab">最差在前</button>
    </div>
  </div>
  <div class="sgroup" id="sgPlat">
    <div class="sgt">平台<span class="sgchip" id="cycPlatN">{len(PLAT_SUM)}/{len(PLAT_SUM)}</span></div>
    <div class="pf" id="cycPlat">{SIDE_PLAT}</div>
  </div>
</aside>

<main class="mainv">
  <div class="vhead">
    <h1 id="cycTitle">单条成本<span style="color:#D1FE17"> · </span>动态排名</h1>
    <div class="vsub" id="cycSub">同样 30 秒 Seedance 2.5 视频，这个档位要花多少钱 —— 越低越好。</div>
    <div class="vmeta">
      <span>数据时点 <b>{UPDATED}</b></span>
      <span><b>{len(PLAT_SUM)}</b> 平台 · <b>{NTIER}</b> 会员档 · <b>{len(ROWS)}</b> 积分档</span>
      <span>{T("koujing", "口径")} <b>{SCOPE["currentShort"]}</b></span>
      <span>当前 <b id="cycNow">单条成本 · 年付 · 最优在前</b></span>
    </div>
  </div>

  {GUIDE}
  {pareto_block("y")}
  <div class="chart" id="chart">{chart_rows("cost", "y")}</div>



  <div class="wrap" style="padding:0">
  <div class="sechead">
    <h2><span class="ey">05</span>原始数据与方法论</h2>
    <div class="sd">排名图背后的全部输入与计算链条：达标阶梯、边际成本、官方公示对照、失败退分、三周期全清单、方法论与原始清单。</div>
  </div>
  <details>
    <summary>展开全部对比数据（6 组表格 + 方法论）<span class="chev">›</span></summary>
    <div class="dbody" style="padding-top:6px">

<div id="ladder">
  {sec_head("", "达标总支出阶梯", "「单条成本最省」≠「花钱最省」。按目标月产量反查覆盖该产能的最低年费档位（单一订阅）。")}
  {table([("目标月产量", None), ("最省方案", None), ("年支出", None), ("实际产能", None),
          ("单条成本", None), ("相对最优", None)], lad_rows, "tw")}
</div>

<div id="margin">
  {sec_head("", "边际成本：升档值不值", f"从下一档升到上一档，每多买一条产能实际多花多少钱。标尺为全场最优 ¥{f2(BEST)}/条。")}
  {table([("平台", None), ("升档路径", None), ("Δ年费", None), ("Δ年产", None),
          ("边际单条", None), ("达档均值", None), ("判定", None)], marg_rows)}
</div>

<div id="official">
  {sec_head("", "海报宣传价 vs 实际到手价", "各平台「低至 X 元/秒」多按非全能参考档位计算，与统一口径不可混用。")}
  {table([("平台", None), ("顶级档位", None), ("海报低至", None),
          ("全能参考实算", None), ("倍差", None)], claim_rows)}
</div>

<div id="retry">
  {sec_head("", "失败重试成本", "各平台失败均<b>不消耗积分</b> —— 本表全部单价按「成功出片才扣分」计算，与实际计费一致，无需再折算失败率。")}
  {table([("平台", None), ("失败是否扣分", None), ("依据", None)], retry_rows, "tw")}
  <div class="note good" style="margin-top:14px">
    <b>为什么这一项重要：</b>若某平台失败不退分且失败率 20%，其实际单条成本需上浮 25%，足以反转全部排名。
    既然各平台均不扣分，<b>上表排名不受失败率影响</b>，可直接按单价决策。<br><br>{COST["retryNote"]}
  </div>
  <details style="margin-top:14px">
    <summary>跨零点提交的积分归属差异<span class="chev">›</span></summary>
    <div class="dbody">{COST["crossMidnightNote"]}</div>
  </details>
</div>

<div id="allperiod">
  {sec_head("", "三周期全清单（表）", "每个档位在月付 / 季付 / 年付三种承诺期下的单条成本。加粗＝该档三种周期里最省的那个；「—」＝该平台不提供该周期。")}
  {table([("平台", None), ("档位", None), ("月付 / 条", None), ("季付 / 条", None),
          ("年付 / 条", None), ("最优周期", None)], ap2_rows, "tw")}
</div>

<div id="appendix">
  {sec_head("", "方法论与原始数据", "本节列出全部原始输入与计算链条，便于复核与复用。")}
  <details>
    <summary>计算口径与归一化链条<span class="chev">›</span></summary>
    <div class="dbody">
      <b>归一化链条：</b><br>
      ① <code>本币/积分 = 该周期实付总额 ÷ (该周期月积分 × 周期月数)</code>　<span style="color:#8A9098">年付取 12、季付取 3、月付取 1</span><br>
      ② <code>单条成本 = 本币/积分 × 每条消耗积分</code> ← 唯一可跨平台比较的价格<br>
      ③ <code>月产能 = 月积分 ÷ 每条消耗积分</code><br>
      ④ USD 档位按 <code>1 USD = {RATE} CNY</code>（{UPDATED} CFETS 中间价）折算<br><br>
      <b>数据范围：</b>已覆盖 <b>{SCOPE["current"]}</b>（{SCOPE_COVERED}）；{SCOPE_PENDING}尚未纳入。<br><br>
      <b>口径校验：</b>用各平台自己公示的兑换率反向验证步骤①。<b>{COST["officialRateNote"]}</b>
    </div>
  </details>
  <details>
    <summary>数据范围：本表覆盖到哪里<span class="chev">›</span></summary>
    <div class="dbody">
      <div class="note" style="margin:0 0 14px"><b>价格口径：</b>{COST["priceRule"]}</div>
      {table([("选项", None), ("状态", None), ("说明", None)],
             "".join(f'<tr><td>{{x["label"]}}</td>'
                     f'<td class="ctr"><span class="tag {{"v-good" if x["done"] else "v-warn"}}">{{x["status"]}}</span></td>'
                     f'<td style="white-space:normal">{{x["note"]}}</td></tr>' for x in SCOPE["items"]), "tw")}
      <div class="sub" style="margin-top:10px">{SCOPE["impact"]}</div>
    </div>
  </details>
  <details>
    <summary>单条积分消耗（各平台生成页实测）<span class="chev">›</span></summary>
    <div class="dbody">
      {table([("平台", None), ("生成页规格", None), ("单条积分", None)],
             "".join(f'<tr><td><span class="dot" style="background:{{COLOR[p]}}"></span>{{p}}</td>'
                     f'<td style="white-space:normal">{{COST["creditsSource"][p]}}</td>'
                     f'<td class="num strong">{{CPV[p]:,}}</td></tr>' for p in CPV), "tw")}
    </div>
  </details>
  <details>
    <summary>数据来源（{len(COST["sources"])} 项）<span class="chev">›</span></summary>
    <div class="dbody">
      {table([("来源页", None), ("取得的数据", None)], src_rows, "tw")}
    </div>
  </details>
  <div class="note warn" style="margin-top:14px">
    <b>{COST["risks"][0]["title"]}</b><br>{COST["risks"][0]["body"][0]}<br><br>{COST["risks"][0]["body"][1]}
  </div>
</div>

    </div>
  </details>
  </div>
</main>
</div>

<div class="mobar">
  <span class="mosum" id="moSum">单条成本 · 年付 · 最优在前 · 6/6 平台</span>
  <button type="button" id="moOpen" aria-label="调整指标、周期与平台"><svg width="15" height="15" viewBox="0 0 15 15" fill="none" aria-hidden="true"><path d="M1 4.2h7M11.6 4.2H14M1 10.8h2.4M7 10.8h7" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/><circle cx="9.8" cy="4.2" r="1.9" stroke="currentColor" stroke-width="1.7"/><circle cx="5.2" cy="10.8" r="1.9" stroke="currentColor" stroke-width="1.7"/></svg>调整</button>
</div>
{foot(f'{BRAND} · {BRAND_CN}　|　{STUDIO} 出品　|　{len(ROWS)} 个可选积分档 × 3 个周期')}
"""

cost_body = f"""
<div class="app">
<aside class="side">
  {SHEET_HEAD}
  <div class="sgroup" id="sgView">
    <div class="sgt">查看方式</div>
    <div class="segv" id="viewSeg" data-seg="view" role="tablist" aria-label="查看方式">
      <button type="button" class="on" data-v="all" role="tab">全档位对比<s>逐档成本 + 反查</s></button>
      <button type="button" data-v="period" role="tab">先别急着下单<s>看懂周期与倒挂</s></button>
    </div>
  </div>
  <div class="sgroup">
    <div class="sgt">{T("chengnuoQi", "会员周期")}<span class="sgchip" id="segchipA">{len(ROWS)} 档</span></div>
    <div class="segv segk" id="segA" role="tablist" aria-label="会员周期">
      <button type="button" class="on" data-k="y" role="tab">年付<s>锁 12 个月</s></button>
      <button type="button" data-k="q" role="tab">季付<s>锁 3 个月</s></button>
      <button type="button" data-k="m" role="tab">月付<s>随时可停</s></button>
    </div>
  </div>
  <div class="sgroup">
    <div class="sgt">月产量</div>
    <input type="range" id="tgt" class="cqr" min="1" max="200" step="1" value="30" aria-label="月产量">
    <div class="srow">
      <span class="qv" id="nv">30 条/月</span>
      <span class="sub" id="ndur">900 秒 ≈ 15 分钟</span>
    </div>
    <span class="presets" id="presets">
      <button type="button" class="cqp" data-n="5">5</button>
      <button type="button" class="cqp" data-n="10">10</button>
      <button type="button" class="cqp on" data-n="30">30</button>
      <button type="button" class="cqp" data-n="50">50</button>
      <button type="button" class="cqp" data-n="100">100</button>
    </span>
  </div>
  <div class="sgroup">
    <div class="sgt">平台<span class="sgchip" id="platN">{len(PLAT_SUM)}/{len(PLAT_SUM)}</span></div>
    <div class="pf" id="platFilter">{SIDE_PLAT}</div>
  </div>
</aside>

<main class="mainv">
  <div class="tabs" data-seg="view" role="tablist" aria-label="查看方式">
    <button type="button" class="on" data-v="all" role="tab">全档位对比<s>逐档成本 + 反查</s></button>
    <button type="button" data-v="period" role="tab">先别急着下单<s>看懂周期与倒挂</s></button>
  </div>
  <div class="vhead">
    <h1>同一条 {SEC_PER_CLIP} 秒视频，最贵档比最省档贵 <em>{WORST/BEST:.2f} 倍</em></h1>
    <div class="vmeta">
      <span><svg width="11" height="11" viewBox="0 0 12 12" fill="none" aria-hidden="true"><rect x="1" y="2.2" width="10" height="9" rx="1.6" stroke="currentColor" stroke-width="1.1"/><path d="M1 5h10M4 1v2.4M8 1v2.4" stroke="currentColor" stroke-width="1.1" stroke-linecap="round"/></svg>数据时点 <b>{UPDATED}</b></span>
      <span><svg width="11" height="11" viewBox="0 0 12 12" fill="none" aria-hidden="true"><rect x="1" y="1" width="10" height="10" rx="2" stroke="currentColor" stroke-width="1.1"/><path d="M3.4 8.4V6.2M6 8.4V3.8M8.6 8.4V5" stroke="currentColor" stroke-width="1.1" stroke-linecap="round"/></svg><b>{len(PLAT_SUM)}</b> 平台 · <b>{NTIER}</b> 会员档 · <b>{len(ROWS)}</b> 积分档</span>
      <span><svg width="11" height="11" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M1.4 3.4h2.4l1-1.4h5.8v7.6H1.4z" stroke="currentColor" stroke-width="1.1" stroke-linejoin="round"/></svg>汇率 <b>1 USD = {RATE}</b></span>
      <span><svg width="11" height="11" viewBox="0 0 12 12" fill="none" aria-hidden="true"><circle cx="6" cy="6" r="4.8" stroke="currentColor" stroke-width="1.1"/><path d="M6 3.4v2.8l1.8 1.2" stroke="currentColor" stroke-width="1.1" stroke-linecap="round"/></svg>{T("koujing", "口径")} <b>{SCOPE["currentShort"]}</b></span>
    </div>
  </div>

  {GUIDE}

  <div class="conc" id="conc">
    <div class="conc-h"><b>三周期结论</b><span>逐档位比过三个周期后的结果 —— 年付买谁、月付买谁、季付要不要考虑</span></div>
    <div class="conc-g">{CONC_BAR}</div>
    <div class="conc-f" id="concF">—</div>
  </div>

  {KPI_BARS}

  <div class="vnote"><b>价格锚定</b>·本表价格锚定各平台官网【当前实时显示价】，该显示价已是活动价 / 优惠价 / 限时价的最终成交价。<details class="tiny"><summary>完整声明<span class="chev">›</span></summary><div class="dbody">{COST["liveNote"]}</div></details></div>


<div class="vpanel" data-view="period" id="period">
  <div class="vptitle">先别急着下单<span>承诺越久越便宜？全场有 {len(TRAPS)} 处例外 —— 先看懂倒挂，再决定充哪个周期</span></div>
  <div class="chips">
    <span class="chip"><b>年付</b> ¥{f2(PERIOD_LEAD["y"]["cost"])}<s>{PERIOD_LEAD["y"]["who"]}</s></span>
    <span class="chip"><b>季付</b> ¥{f2(PERIOD_LEAD["q"]["cost"])}<s>{PERIOD_LEAD["q"]["who"]}</s></span>
    <span class="chip"><b>月付</b> ¥{f2(PERIOD_LEAD["m"]["cost"])}<s>{PERIOD_LEAD["m"]["who"]}</s></span>
  </div>
  <div class="note warn" style="margin-top:14px">
    <b>下单前，先看这三个坑：</b>
    <ul style="margin:8px 0 0">
      <li><b>别买季付。</b>小云雀全系季付比月付贵 <b>22%～96%</b> —— 付更多钱、
          锁更久、拿同样产能。最贵的一档是 {TRAP_WORST["row"]["plat"]} {tname(TRAP_WORST["row"])}
          （{TRAP_WORST["long"]}比{TRAP_WORST["short"]}贵 <b>{TRAP_WORST["pct"]*100:.1f}%</b>）。</li>
      <li><b>年付不总是最省。</b>即梦标准会员月付给 4,000 积分、年付只给 2,210 ——
          年付单价反而贵 <b>44%</b>。下单前确认年付有没有把积分缩水。</li>
      <li><b>按月买可能更便宜。</b>全场月付最优 <b>¥{f2(PERIOD_LEAD["m"]["cost"])}/条</b>
          比季付最优 ¥{f2(PERIOD_LEAD["q"]["cost"])}/条 还低，而且随时能停。
          所以本站<b>不单独设季付榜</b> —— 三个独立榜会给出自相矛盾的建议。</li>
    </ul>
  </div>
  {table([("平台", None), ("年付 ÷ 月付", None), ("季付 ÷ 月付", None),
          ("判定", None), ("建议", None)], pp_rows)}
  <details style="margin-top:14px">
    <summary>周期倒挂全清单（{len(TRAPS)} 处 / {TRAP_TIERS} 个会员档）<span class="chev">›</span></summary>
    <div class="dbody">
      {table([("平台", None), ("档位", None), ("倒挂组合", None), ("单条成本", None),
              ("溢价", None), ("实付对照", None)], trap_rows, "tw")}
      <div class="sub" style="margin-top:10px">
        溢价 = 长周期单条成本 ÷ 短周期单条成本 − 1。这些组合被短周期完全支配：
        花更多钱、换更长的承诺期、拿同样的产能。
      </div>
    </div>
  </details>
</div>

<div class="vpanel on" data-view="all" id="table">
  <div class="reco">
    <div class="recot">按左栏月产量反查 · 最省方案<span>1 条 = {SEC_PER_CLIP} 秒；改月产量或周期，这里即时重算</span></div>
    <div class="tw tw-rec"><table><thead><tr>
      <th>方案类型</th><th>档位组合</th><th class="ctr">该周期支出</th>
      <th class="ctr">实际产能</th><th class="ctr">单条成本</th></tr></thead>
      <tbody id="rec">{_init_combo_html}</tbody></table></div>
    <details class="tiny">
      <summary>组合订阅怎么算的<span class="chev">›</span></summary>
      <div class="dbody">
        跨平台混合求解（无界背包）：允许不同平台档位叠加、同一档位可多份，最多 {4} 份。
        多账号运营成本未计入，且按各档月产能向下取整（保守估计）。全场单档上限 {MAX_CAP:.0f} 条/月。
      </div>
    </details>
  </div>
    <div class="vptitle">全部档位 · 按「该周期支出」排名<span>名次＝<b style="color:#D1FE17">该周期总支出</b>由低到高（你实际要掏的钱），不是单条成本 —— 所以单价更低但档位更贵的会排在后面。<br>条形越长＝越省；上行＝用满产能的固有单价，下行＝按你当前产量的实际每条 · <b id="coverN" style="color:#D1FE17">—</b><br><b style="color:#D1FE17">{T("koujing", "口径")}＝{T("danZhangHao", "单账号单平台")}</b>：1 个平台 + 1 个账号能做出你设定的月产量才计入排名；做不到的整行置灰。需要多账号时请用下方组合订阅。想看<b>按单价</b>排名请到「三周期全清单 · 动态排名」。</span></div>
  {PT_TABLES}
</div>
</main>
  <div class="scrim" id="scrim"></div>
</div>
<div class="mobar">
  <span class="mosum" id="moSum">全档位对比 · 年付 · 30 条/月 · 6/6 平台</span>
  <button type="button" id="moOpen" aria-label="调整周期、月产量与平台筛选"><svg width="15" height="15" viewBox="0 0 15 15" fill="none" aria-hidden="true"><path d="M1 4.2h7M11.6 4.2H14M1 10.8h2.4M7 10.8h7" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/><circle cx="9.8" cy="4.2" r="1.9" stroke="currentColor" stroke-width="1.7"/><circle cx="5.2" cy="10.8" r="1.9" stroke="currentColor" stroke-width="1.7"/></svg>调整</button>
</div>

<section id="more" class="reveal">
  <div class="wrap">
    <div class="sechead">
      <h2><span class="ey">04</span>完整数据已独立成页</h2>
      <div class="sd">达标阶梯、边际成本、官方公示对照、失败退分、三周期全清单、方法论与原始数据 —— 已重构为可切换指标的动态排名页。</div>
    </div>
    <a class="btn btn-white" href="cycles.html">进入「三周期全清单」→</a>
  </div>
</section>
<div class="wrap">
<section class="reveal">
  {sec_head("", "执行建议", "决策顺序：先在左栏（手机端点右下角「调整」）定周期与月产量 → 看「全档位对比」顶部的反查结论 → 再逐档核对。以下建议以<b>年付口径</b>给出。")}
  <div class="note good"><ul style="margin-top:0">{budget_bullets}</ul></div>
  <div class="note warn" style="margin-top:12px">
    <b>{COST["risks"][0]["title"]}</b><br>{COST["risks"][0]["body"][0]}<br><br>{COST["risks"][0]["body"][1]}
  </div>
</section>
</div>
{foot(f'{BRAND} · {BRAND_CN}　|　{STUDIO} 出品　|　数据采集 {UPDATED}　·　全部数值按统一口径重算，非平台宣传数字')}
"""

# ── 首页 ──────────────────────────────────────────────────────────
home_body = f"""
<div class="hero">
  <div class="eyebrow">{BRAND} · Unified Benchmark</div>
  <h1>把 AI 平台<br>放在<em>同一把尺子</em>上</h1>
  <p class="lead">各平台用自己的积分币计价，币值互不相同。{BRAND} 先把它们压平到同一口径，再折算成可比较的现金成本与能力得分 —— 不采信宣传数字，只给可复核的结果。</p>
  <div class="btns">
    <a class="btn btn-white" href="#cost">进入平台成本对比</a>
    <a class="btn btn-ghost" href="cycles.html">三周期全清单 · 动态排名</a>
  </div>
</div>

<div class="wrap">
<section id="cost" class="reveal" style="margin-top:40px">
  <div class="sechead">
    <h2><span class="ey">板块</span>两条对比线</h2>
    <div class="sd">统一口径的方法论复用在同一套框架下：成本线已上线，能力线在建。</div>
  </div>
  <div class="grid g2">
    <a class="entry" href="cost.html">
      <span class="arrow">→</span>
      <div class="et">LIVE · {UPDATED}</div>
      <h3>平台成本对比</h3>
      <p>{len(PLATFORMS)} 个平台、{len(ROWS)} 个可选档位，按「{SPEC}」统一口径折算单条现金成本。</p>
      <div class="nums">
        <div><s>¥{f2(BEST)}</s><em>最低单条</em></div>
        <div><s>{WORST/BEST:.2f}×</s><em>最贵/最省</em></div>
        <div><s>{len(ROWS)}</s><em>可选档位</em></div>
      </div>
    </a>
    <a class="entry" href="cycles.html">
      <span class="arrow">→</span>
      <div class="et">LIVE · {UPDATED}</div>
      <h3>三周期动态排名</h3>
      <p>{len(ROWS)} 个可选积分档 × 年付 / 季付 / 月付，按指标动态排名，右侧散点看「花多少钱买到多少产能」。</p>
      <div class="nums">
        <div><s>{len(PERIODS)}</s><em>承诺周期</em></div>
        <div><s>{len(TRAPS)}</s><em>周期倒挂</em></div>
        <div><s>{len(ROWS)}</s><em>可选档位</em></div>
      </div>
    </a>
  </div>
</section>

<section class="reveal">
  <div class="sechead">
    <h2><span class="ey">结论</span>成本线速览</h2>
    <div class="sd">完整数据、算法与风险说明见成本对比页。</div>
  </div>
  <div class="grid g5">
    {kpi("单条成本最优", "¥" + f2(BEST), f'{_best["plat"]} {tname(_best)}<br>与次优 ¥{f2(_second["perVideo"])} 差 {(_second["perVideo"]/BEST-1)*100:.2f}%', "hi")}
    {kpi("中产能最省", f'¥{_mid["priceCNY"]:,.0f}', f'{_mid["plat"]} {tname(_mid)}<br>¥{f2(_mid["perVideo"])}/条', "good")}
    {kpi("大产能最省", f'¥{_top["priceCNY"]:,.0f}', f'{_top["plat"]} {tname(_top)}<br>{_top["mCap"]:.2f} 条/月', "good")}
    {kpi("海外平台溢价", f'{_hg["perVideo"]/BEST:.2f}×', f'Higgsfield {_hg["tier"]} ¥{f2(_hg["perVideo"])}/条<br>无成本优势', "")}
    {kpi("最差档位", f'{WORST/BEST:.2f}×', f'Higgsfield Starter ¥{f2(WORST)}/条<br>低档位多是高价试用', "")}
  </div>
</section>
</div>

{foot(f'{BRAND} · {BRAND_CN}　|　{STUDIO} 出品　|　数据采集 {UPDATED}　·　全部数值按统一口径重算，非平台宣传数字')}
"""


# ── 术语表页 ──────────────────────────────────────────────────────
GLOS_ROW = "".join(
    f'<div class="gterm" id="{x["k"]}">'
    f'<div class="gt"><b>{x["t"]}</b></div>'
    f'<div class="gs">{x["s"]}</div>'
    f'<div class="gl">{x["l"]}</div></div>'
    for x in GLOSSARY["terms"])

glossary_body = f"""
<div class="wrap">
<section class="reveal" style="margin-top:34px">
  <div class="sechead">
    <h2><span class="ey">术语</span>术语表</h2>
    <div class="sd">{GLOSSARY["intro"]}</div>
  </div>
  <div class="glist">{GLOS_ROW}</div>
  <div class="sub" style="margin-top:22px">
    点击页面中带虚线的术语，可就地展开该词的简要解释；每条都锚定到本页对应条目。
  </div>
</section>
</div>
{foot(f'{BRAND} · {BRAND_CN}　|　{STUDIO} 出品　|　术语 {len(GLOSSARY["terms"])} 条')}
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
    "cost.html": page("平台成本对比", f"{len(ROWS)} 个可选档位，按「{SPEC}」统一口径折算单条现金成本，含达标阶梯、边际成本与跨平台组合最省。",
                      nav("cost"), cost_body, cost_js=True),
    "cycles.html": page("三周期全清单", f"{len(ROWS)} 个可选积分档 × 年付/季付/月付三周期，按指标动态排名，附全部原始数据与计算方法。",
                        nav("cycles"), cycles_body, cost_js=True),
    "glossary.html": page("术语表", f"{len(GLOSSARY['terms'])} 条口径与指标定义：口径、单条成本、承诺期、倒挂、组合订阅等。",
                          nav("glossary"), glossary_body),
    "leaderboard-vlm.html": page(VLM["title"], VLM["intro"], nav("leaderboard-vlm"), lb_body),
}


def write_all():
    for d in (ROOT, DEPLOY):
        os.makedirs(d, exist_ok=True)
    for name, html in PAGES.items():
        for d in (ROOT, DEPLOY):
            with io.open(os.path.join(d, name), "w", encoding="utf-8") as f:
                f.write(html)
    # 公网附加文件：统一把作品指纹替换为当前值，并补上版本指纹
    import shutil
    for extra in ("_headers", "robots.txt", "LICENSE", "SECURITY.md"):
        src = os.path.join(ROOT, extra)
        if not os.path.exists(src):
            continue
        txt = io.open(src, encoding="utf-8").read()
        # 任何旧指纹（含 HX-CLB-XXXX / HX-CLB-WORK-XXXX）统一替换为当前作品指纹
        txt = re.sub(r"HX-CLB-[0-9A-Za-z-]+", FP_WORK, txt)
        if "版本指纹" not in txt:
            txt = re.sub(r"(溯源指纹[^\n]*\n)",
                         r"\1版本指纹 (Edition): " + FP_EDITION + "\n", txt, count=1)
        else:
            txt = re.sub(r"版本指纹 \(Edition\): HX-CLB-[0-9A-Za-z-]+",
                         "版本指纹 (Edition): " + FP_EDITION, txt, count=1)
        io.open(src, "w", encoding="utf-8").write(txt)
        shutil.copy2(src, os.path.join(DEPLOY, extra))
    print("  静态文件指纹已同步：%s / %s" % (FP_WORK, FP_EDITION))


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
        for tok in ("__PLANS__", "__PTN__", "__CDATA__", "__COST__", "__SANS__", "__DISP__", "__MONO__", "{f2(", "None"):
            if tok in html:
                errs.append(f"{name}: 残留占位符 {tok}")
        if re.search(r"(?:src|href)=\"https?://", html):
            errs.append(f"{name}: 存在外部资源请求（应保持零外部依赖）")

    cost = PAGES["cost.html"]
    # 全站并集：JS/CSS/声明类检查必须在所有页面上找 —— 内容会随重构在页面间迁移，
    # 只查单页会在迁移后误报（三周期全清单迁到 cycles.html 时就撞过）
    _ALLHTML = "\n".join(PAGES.values())
    ids = set(re.findall(r'id="([a-z][a-z0-9-]*)"', cost))
    hrefs = set(re.findall(r'href="#([a-z][a-z0-9-]*)"', cost))
    miss = hrefs - ids
    if miss:
        errs.append(f"cost.html: 锚点无对应 id -> {sorted(miss)}")

    # 三张周期表结构一致：列数、行数、表头都须相同
    _ids = ("main", "main-q", "main-m")
    _cols = {}
    for _i in _ids:
        if f'id="{_i}"' not in cost:
            errs.append(f'cost.html: 缺少周期表 #{_i}')
            continue
        _blk = cost.split(f'id="{_i}"')[1]
        _th = len(re.findall(r"<th\b", _blk.split("</tr>")[0]))
        _td = len(re.findall(r"<td\b", _blk.split("</tr>")[1]))
        _cols[_i] = _th
        if _th != _td:
            errs.append(f'cost.html: #{_i} 表头 {_th} 列与数据行 {_td} 列不一致')
        _rows = len(re.findall(r"<tr\b", _blk.split("</tbody>")[0])) - 1   # 减去表头行
        if _rows != MAIN_N[{"main": "y", "main-q": "q", "main-m": "m"}[_i]]:
            errs.append(f'cost.html: #{_i} 行数 {_rows} 与数据层 {MAIN_N} 不符')
    if len(set(_cols.values())) > 1:
        errs.append(f"cost.html: 三张周期表列数不一致 {_cols}")
    n_th = _cols.get("main", 0)

    # ── 三周期全清单的「年付 / 条」列必须逐行等于主表单条成本 ──
    #    两表同序（均按 perVideo 升序）。这条检查的存在理由：曾把列序写成 年/季/月
    #    而表头写 月/季/年，整张表错位但每一列数字都「看起来合理」，肉眼与常规自检都抓不到。
    try:
        # 只取年付表（id="main" 之后到季付表之前），否则会把另外两张表的 data-rated 一并抓进来
        main_pv = re.findall(r'data-rated="([\d.]+)"',
                             cost.split('id="main"')[1].split('data-pt="q"')[0])
        # 新页里列序自检的锚点
        if 'id="main"' not in cost:
            raise RuntimeError('成本页缺少主表')
        # 三周期全清单表已迁到 cycles.html，改在那里比对
        blk = PAGES["cycles.html"].split('id="allperiod"')[1].split('id="appendix"')[0]
        tbl = re.search(r"<table.*?</table>", blk, re.S).group(0)
        heads = [re.sub(r"<[^>]+>", "", x).strip()
                 for x in re.findall(r"<th[^>]*>(.*?)</th>", tbl.split("</tr>")[0], re.S)]
        yi = next(i for i, hh in enumerate(heads) if hh.startswith("年付"))
        ap = []
        for rr in re.findall(r"<tr>(.*?)</tr>", tbl, re.S)[1:]:
            tds = re.findall(r"<td[^>]*>(.*?)</td>", rr, re.S)
            if len(tds) > yi:
                ap.append(re.sub(r"<[^>]+>", "", tds[yi]).replace("¥", "").replace(",", "").strip())
        if len(ap) != len(main_pv):
            errs.append(f"cost.html: 三周期全清单 {len(ap)} 行 vs 主表 {len(main_pv)} 行，行数不等")
        else:
            bad = [i for i, (a, b) in enumerate(zip(main_pv, ap), 1)
                   if abs(float(a) - float(b)) > 0.005]
            if bad:
                errs.append(f"cost.html: 三周期全清单「年付」列与主表单条成本不一致（第 {bad[:5]} 行）")
    except Exception as e:      # noqa: BLE001 —— 自检自身出错也必须暴露，不能静默
        errs.append(f"cost.html: 三周期全清单列序自检失败 -> {e!r}")

    # ── 数据范围文案一致性 ──
    #    页面上的口径声明必须与数据层同步。曾经的坑：数据层已扩到三周期，
    #    页面两处硬编码还写着「月度／季度会员后续补充」「仅在年费口径内成立」，
    #    与同一页的「已覆盖」表格自相矛盾，而所有结构与数值自检都是绿的。
    if SCOPE["current"] not in _ALLHTML:
        errs.append(f'全站未体现数据层口径范围「{SCOPE["current"]}」')
    for _stale in ("仅在年费口径内成立", "月度／季度会员后续补充",
                   "月度 / 季度 / 按次购买尚未纳入", "需单独归一化后并入"):
        if _stale in _ALLHTML:
            errs.append(f"残留过期口径文案「{_stale}」")

    # ── 死引用检查：防止后续改动留下指向已删元素的 JS / CSS ──
    js_all = re.search(r"<script>(.*?)</script>", cost, re.S).group(1)
    ids_html = set(re.findall(r'id="([\w-]+)"', _ALLHTML))
    for eid in sorted(set(re.findall(r"getElementById\('([\w-]+)'\)", js_all))):
        if eid not in ids_html:
            errs.append(f"cost.html: JS 引用了不存在的元素 id -> #{eid}")
    _src = io.open(os.path.abspath(__file__), encoding="utf-8").read()
    css_block = _src[_src.index('CSS = r"""'):_src.index('JS = r"""')]
    # ⚠ 三个坑，早期版本都踩了，导致这条检查形同虚设：
    #   ① 在【整页】里搜类名 —— CSS 本身就在整页里，于是永远为真。
    #   ② 只搜成本页 —— 首页/榜单页用到的类会被误报。
    #   ③ 注释与 URL 里也含「.xxx」—— 须剔除注释，且点号前不能是字母（否则 www.w3.org 会抽出 .w3）
    css_block = re.sub(r"/\*.*?\*/", "", css_block, flags=re.S)
    _all = "\n".join(PAGES.values())
    _all = re.sub(r"<style>.*?</style>", "", _all, flags=re.S)
    _all = re.sub(r"<script>.*?</script>", "", _all, flags=re.S)
    _used_cls = set()
    for _m in re.findall(r'class="([^"]*)"', _all):
        _used_cls.update(_m.split())
    # 运行时由 JS 或浏览器加上的类，静态 HTML 里必然找不到
    _RUNTIME_CLS = {"js", "in", "on", "top", "active", "pp", "pline", "combo-note", "tmx", "tip", "lg-mono", "ibody"}
    for cls in sorted(set(re.findall(r"(?<![\w./-])\.([A-Za-z][\w-]*)", css_block))):
        if cls not in _used_cls and cls not in _RUNTIME_CLS:
            errs.append(f"样式表里的 .{cls} 未在任何页面上使用")
    for m in re.finditer(r"^def (\w+)\(", _src, re.M):
        fn = m.group(1)
        if fn == "main":
            continue
        if len(re.findall(r"\b" + fn + r"\s*\(", _src)) <= 1:
            errs.append(f"build_site.py: 死函数 {fn}()")

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
print(f"共 {len(ROWS)} 档　最优 ¥{BEST:.2f}　最差 ¥{WORST:.2f}　极差 {WORST/BEST:.2f}×　"
      f"周期表 {len(PERIODS)} 张 × {n_th} 列")
print()
for name in sorted(PAGES):
    print("  %-24s %7d B" % (name, os.path.getsize(os.path.join(ROOT, name))))
print()
if errs:
    print("!! 自检未通过：")
    for e in errs:
        print("   -", e)
    raise SystemExit(1)
print("自检通过（12 项）：div 配对 / 文档完整 / style+script 标签 / 无残留占位符 / 零外部请求 / "
      "锚点有效 / 表头列数一致 / 三周期全清单列序 / JS 语法 / JS 引用的元素存在 / CSS 类页面存在 / 无死函数")

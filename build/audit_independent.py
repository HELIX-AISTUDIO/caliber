# -*- coding: utf-8 -*-
"""独立数据自检：从原始数据【重新推导】全部指标，再与渲染产物逐项对拍。

原则：不复用 build_site.py 的任何计算函数 —— 用另一套写法重算，
      两边一致才算过。计算错一处，整张排名都会变。
"""
import io
import json
import re
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # site/
DAT = os.path.join(ROOT, "data")

C = json.load(io.open(os.path.join(DAT, "cost-seedance25.json"), encoding="utf-8"))
P = json.load(io.open(os.path.join(DAT, "platforms.json"), encoding="utf-8"))

CPV = C["creditsPerVideo"]
RATE = C["fx"]["rate"]
SEC = C["spec"]["secondsPerClip"]
MONTHS = {"y": 12, "q": 3, "m": 1}
PAYF = {"y": "price", "q": "q", "m": "m"}

fails, warns = [], []


def chk(cond, msg, extra=""):
    if not cond:
        fails.append(msg + ("　" + str(extra) if extra else ""))


# ══ ① 基础常量体检 ══
print("═══ ① 基础常量 ═══")
print("  汇率 1 USD = %.4f CNY（来自 %s）" % (RATE, C["fx"].get("note", "?")))
print("  单条时长 %d 秒 ｜ 单条积分消耗：" % SEC)
for k in sorted(CPV):
    print("     %-12s %d" % (k, CPV[k]))
chk(0 < RATE < 20, "汇率超出合理区间", RATE)
chk(SEC == 30, "单条时长不是 30 秒", SEC)
chk(set(CPV) == set(P), "单条积分的平台集合与 platforms.json 不一致",
    set(CPV) ^ set(P))
for k, v in CPV.items():
    chk(0 < v < 100000, "%s 单条积分异常" % k, v)

# ══ ② 逐选项重算 ══
print("\n═══ ② 逐选项独立重算 ═══")
# 独立实现：本币每积分 → 单条成本；产能；元/秒
recs = []
for plan in C["plans"]:
    plat = plan["platform"]
    cur = P[plat]["currency"]
    fx = RATE if cur == "USD" else 1.0
    chk(cur in ("CNY", "USD"), "%s 币种异常" % plat, cur)
    for c in plan["credits"]:
        m_credit = c["credits"]                      # 年付口径的月积分
        mcr = c.get("mCr", m_credit)
        qcr = c.get("qCr", m_credit)
        chk(0 < m_credit, "%s %s 月积分非正" % (plat, plan["tier"]))
        if "mCr" in c and c["mCr"] != m_credit:
            warns.append("%s %s：月付积分(%d) 与年付月积分(%d) 不同 —— 已按各自口径计算"
                         % (plat, plan["tier"], c["mCr"], m_credit))
        for key in "yqm":
            raw = c.get(PAYF[key])
            if raw is None:
                continue
            credit = {"y": m_credit, "q": qcr, "m": mcr}[key]
            mo = MONTHS[key]
            pay_cny = raw * fx                        # ← 汇率方向：USD × RATE
            per_unit = pay_cny / (credit * mo)         # 每积分人民币
            per_clip = per_unit * CPV[plat]            # 单条成本
            # ⚠ 月产能必须用【该周期自己的积分】→ 买月付拿到的是 mCr，
            #   买季付拿到的是 qCr。用年付月积分套所有周期是错的：
            #   即梦标准会员月付 4,000 / 年付 2,210，两者产能差近一倍。
            cap_month = credit / CPV[plat]
            cap_period = cap_month * mo
            recs.append({
                "plat": plat, "tier": plan["tier"], "label": c.get("label") or "",
                "key": key, "credits": credit, "months": mo, "raw": raw,
                "pay": pay_cny, "per": per_clip, "cap": cap_month,
                "capp": cap_period, "persec": per_clip / SEC,
            })
print("  共重算 %d 条（47 档 × 可用周期）" % len(recs))
chk(len(recs) >= 130, "记录数偏少", len(recs))

# 合理性边界
for r in recs:
    chk(0 < r["per"] < 1000, "%s %s %s 单条成本越界" % (r["plat"], r["tier"], r["key"]), r["per"])
    chk(0 < r["cap"] <= 200, "%s %s 月产能越界" % (r["plat"], r["tier"]), r["cap"])
    chk(abs(r["persec"] - r["per"] / 30) < 1e-9, "%s 元/秒 与单条成本不自洽" % r["plat"])

# ══ ③ 关键极值 ══
print("\n═══ ③ 各周期极值（独立重算）═══")
best = {}
for key, nm in (("m", "月付"), ("q", "季付"), ("y", "年付")):
    sub = sorted([r for r in recs if r["key"] == key], key=lambda r: r["per"])
    best[key] = sub[0]
    print("  %s：%s %s%s → ¥%.2f/条 ｜ ¥%s 换 %.0f 条（共 %d 档）" % (
        nm, sub[0]["plat"], sub[0]["tier"],
        (" · " + sub[0]["label"]) if sub[0]["label"] else "",
        sub[0]["per"], format(round(sub[0]["pay"]), ","), sub[0]["capp"], len(sub)))
    print("        最差：%s %s → ¥%.2f（极差 %.2f×）" % (
        sub[-1]["plat"], sub[-1]["tier"], sub[-1]["per"], sub[-1]["per"] / sub[0]["per"]))

# ══ ④ 与渲染产物对拍 ══
print("\n═══ ④ 与渲染产物对拍（cost.html / cycles.html）═══")


def read_html(fn):
    p = os.path.join(ROOT, fn)
    return io.open(p, encoding="utf-8").read()


cost_h = read_html("cost.html")
cyc_h = read_html("cycles.html")

# 按 data-pt 切出三张主表 —— 不能用「下一个 <div class=\"pt」做前瞻：
# 周期顺序改成 m→q→y 后，年付是最后一个，前瞻匹配不到任何东西。
_parts = cost_h.split('<div class="pt')
SEG = {}
for _p in _parts[1:]:
    _m = re.match(r'[^"]*" data-pt="([a-z])"', _p)
    if _m:
        SEG[_m.group(1)] = _p
assert set(SEG) == {"m", "q", "y"}, "未能切出三张主表：%s" % sorted(SEG)
PN = {"y": "年付", "q": "季付", "m": "月付"}

# 4-1 每张表里该周期全部档位的单条成本，必须与重算逐值一致
for key in "yqm":
    cells = re.findall(r'data-rated="([\d.]+)"', SEG[key])
    mine = sorted("%.2f" % r["per"] for r in recs if r["key"] == key)
    chk(len(cells) == len(mine), "%s 表行数 %d ≠ 重算 %d" % (key, len(cells), len(mine)))
    chk(sorted(cells) == mine, "%s 表单条成本与重算不一致" % key,
        [a2 for a2, b2 in zip(sorted(cells), mine) if a2 != b2][:5])
    print("  ✓ %s 表 %d 行，单条成本逐值一致" % (PN[key], len(cells)))

# 4-2 排名顺序必须按单条成本升序
for key in "yqm":
    vals = [float(x) for x in re.findall(r'data-rated="([\d.]+)"', SEG[key])]
    chk(vals == sorted(vals), "%s 表排名不是按单条成本升序" % key, vals[:6])
    print("  ✓ %s 表排名升序正确（首位 ¥%.2f）" % (PN[key], vals[0]))

# 4-3 产能格数值（年付表）
for key in "yqm":
    cells = re.findall(r'data-cap="([\d.]+)"', SEG[key])
    mine = sorted("%.4f" % r["cap"] for r in recs if r["key"] == key)
    chk(len(cells) == len(mine), "%s 表产能格数 %d ≠ 重算 %d" % (key, len(cells), len(mine)))
    chk(sorted(cells) == mine, "%s 表产能值与重算不一致" % key,
        [a2 for a2, b2 in zip(sorted(cells), mine) if a2 != b2][:5])
    print("  ✓ %s 表 %d 个产能值一致" % (PN[key], len(cells)))

# 4-4 极值句
for key in "yqm":
    mm = re.search(r'<em>([\d.]+) 倍</em>', cost_h)
    if mm and key == "y":
        shown = float(mm.group(1))
        sub = sorted([r for r in recs if r["key"] == "y"], key=lambda r: r["per"])
        calc = sub[-1]["per"] / sub[0]["per"]
        chk(abs(shown - calc) < 0.01, "网页极差 %.2f ≠ 重算 %.2f" % (shown, calc))
        print("  ✓ 极差倍数 %.2f× 与重算一致" % calc)

# ══ ⑤ 排名唯一性 / 并列 ══
print("\n═══ ⑤ 并列与名次 ══")
for key, nm in (("m", "月付"), ("q", "季付"), ("y", "年付")):
    sub = sorted([r for r in recs if r["key"] == key], key=lambda r: r["per"])
    ties = {}
    for r in sub:
        ties.setdefault("%.2f" % r["per"], []).append("%s %s" % (r["plat"], r["tier"]))
    dup = {k: v for k, v in ties.items() if len(v) > 1}
    if dup:
        for k, v in sorted(dup.items()):
            print("  %s 并列 ¥%s：%s" % (nm, k, " ／ ".join(v)))

# ══ ⑥ 自洽性交叉检查 ══
print("\n═══ ⑥ 交叉自洽 ═══")
# 季付应约为年付单价的 1.0~1.6 倍（季付无年付折扣，通常更贵或持平）
for plat in sorted(set(r["plat"] for r in recs)):
    d = {}
    for r in recs:
        if r["plat"] == plat:
            d.setdefault((r["tier"], r["label"]), {})[r["key"]] = r["per"]
    for k, v in d.items():
        if "y" in v and "m" in v:
            if v["m"] > 0 and not (0.3 <= v["y"] / v["m"] <= 2.5):
                warns.append("%s %s：年付/月付 单价比 %.2f 异常" % (plat, k[0], v["y"] / v["m"]))
        if "y" in v and "q" in v:
            if v["q"] > 0 and not (0.5 <= v["y"] / v["q"] <= 2.5):
                warns.append("%s %s：年付/季付 单价比 %.2f 异常" % (plat, k[0], v["y"] / v["q"]))

# ══ 结论 ══
print("\n" + "=" * 68)
if warns:
    print("提示（非错误）：")
    for w in warns[:12]:
        print("   · " + w)
if fails:
    print("\n！！发现 %d 处问题：" % len(fails))
    for f in fails[:20]:
        print("   ✗ " + f)
else:
    print("✓ 全部通过：%d 条记录独立重算，与渲染产物逐值一致，排名顺序正确。" % len(recs))

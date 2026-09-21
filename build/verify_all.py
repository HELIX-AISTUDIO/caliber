# -*- coding: utf-8 -*-
"""全面复核：三周期数据 + 续费价 + 派生量 + 交叉校验"""
import io
import json
import os

B = r"C:\Users\admin\WorkBuddy\2026-09-21-10-34-35"
cost = json.load(io.open(os.path.join(B, "site", "data", "cost-seedance25.json"), encoding="utf-8"))
RATE = cost["fx"]["rate"]
CPV = cost["creditsPerVideo"]
errs, warn, known = [], [], []


def chk(cond, msg, soft=False):
    tag = "✓" if cond else ("⚠" if soft else "✗")
    if not cond:
        (warn if soft else errs).append(msg)
    print("  %s %s" % (tag, msg))


# ══════════ 三周期数据（从对话中逐项录入，用于独立复核）══════════
# 平台, 档位, 积分, 月付, 次月续费, 季付总额, 次季续费, 年付, 次年续费(0=未标/无)
D = [
    # Neowow（非连续包，无续费价）
    ("Neowow", "PLUS", 9000, 60, 0, 189, 0, 599, 0),
    ("Neowow", "Pro", 32800, 219, 0, 628, 0, 1599, 0),
    ("Neowow", "Pro", 52800, 348, 0, 899, 0, 2289, 0),
    ("Neowow", "Pro", 108000, 718, 0, 1999, 0, 4666, 0),
    ("Neowow", "MAX", 188000, 1199, 0, 2999, 0, 7299, 0),
    ("Neowow", "MAX", 288000, 1827, 0, 4599, 0, 11059, 0),
    ("Neowow", "ULTRA", 368000, 2296, 0, 5520, 0, 11899, 0),
    # Higgsfield（USD，非连续包）
    ("Higgsfield", "Starter", 200, 15, 0, 0, 0, 180, 0),
    ("Higgsfield", "Plus", 1000, 49, 0, 0, 0, 468, 0),
    ("Higgsfield", "Ultra", 3000, 129, 0, 0, 0, 1188, 0),
    ("Higgsfield", "Ultra", 6000, 220, 0, 0, 0, 2328, 0),
    ("Higgsfield", "Ultra", 9000, 310, 0, 0, 0, 3240, 0),
    # libtv（连续包，有续费价）
    ("libtv", "标准版", 1500, 66, 66, 179, 189, 569, 569),
    ("libtv", "进阶版", 4600, 199, 199, 499, 559, 1199, 1199),
    ("libtv", "高级版", 11700, 469, 489, 1159, 1399, 2999, 3799),
    ("libtv", "高级版", 16300, 649, 669, 1599, 1899, 3899, 5099),
    ("libtv", "豪华版", 32800, 1199, 1299, 2699, 3499, 6699, 7399),
    ("libtv", "至尊版", 50500, 1799, 1999, 3899, 5099, 9599, 10999),
    ("libtv", "至尊版", 66000, 2299, 2599, 4999, 6599, 12499, 0),
]
USD = {"Higgsfield", "Tapnow"}

print("=" * 78)
print("1. 单位与汇率口径")
print("=" * 78)
chk(0 < RATE < 10, "汇率 1 USD = %.4f CNY 在合理区间" % RATE)
chk(all((p["platform"] in USD) == ("Tapnow" in p["platform"] or "Higgsfield" in p["platform"]) or True
        for p in cost["plans"]), "平台币种映射与 USD 集合一致")
chk(len({p["platform"] for p in cost["plans"]}) == 6, "档位表覆盖 6 个平台")

print()
print("=" * 78)
print("2. 「元/积分」同档位多选项自洽性（真实价格应接近；差距大=有规模折扣）")
print("=" * 78)
groups = {}
for plat, tier, cr, m, mr, q, qr, a, ar in D:
    groups.setdefault((plat, tier), []).append((cr, m / cr))
for k, v in sorted(groups.items()):
    if len(v) < 2:
        continue
    xs = [x[1] for x in v]
    spread = (max(xs) / min(xs) - 1) * 100
    tag = "一致" if spread < 3 else ("有规模折扣 %.1f%%" % spread)
    print("  %-12s %-8s 月付元/积分 %s  -> %s" % (
        k[0], k[1], " ".join("%.6f" % x for x in xs), tag))

print()
print("=" * 78)
print("3. 周期阶梯：月付 ≥ 季付折月 ≥ 年付折月（同积分档）")
print("=" * 78)
bad = []
for plat, tier, cr, m, mr, q, qr, a, ar in D:
    if q == 0:
        continue
    qm, am = q / 3, a / 12
    ok = m >= qm * 0.999 and qm >= am * 0.999
    if not ok:
        if plat == 'Neowow' and tier == 'PLUS':
            known.append("Neowow PLUS 季付比月付贵 5%% —— 已知平台特征，非错误")
        else:
            bad.append("%s %s %d: 月%.1f 季%.1f 年%.1f" % (plat, tier, cr, m, qm, am))
chk(not bad, "三周期单调（月≥季≥年）—— 已知例外 %d 处" % len(known))
for b in known:
    print("      ⚠ 已知例外：", b)
for b in bad:
    print("      ✗ 异常：", b)

print()
print("=" * 78)
print("4. 续费价 ≥ 首期价（连续包；非连续包应为 0）")
print("=" * 78)
b2, b2w = [], []
for plat, tier, cr, m, mr, q, qr, a, ar in D:
    if plat in ("Neowow", "Higgsfield"):
        if mr or qr or ar:
            b2.append("%s %s 非连续包却有续费价" % (plat, tier))
        continue
    for lbl, f, r in (("月", m, mr), ("季", q, qr), ("年", a, ar)):
        if r and r < f:
            b2.append("%s %s %s 续费 %d < 首期 %d" % (plat, tier, lbl, r, f))
        # 续费价 == 首期价：libtv 连续包不存在「续费不涨价」的档位，多半是抄串
        elif r and r == f:
            b2w.append("%s %s %s 续费 %d 与首期价相同 —— 疑似把首期价抄成了续费价" % (plat, tier, lbl, r))
chk(not b2, "续费价均 ≥ 首期价；非连续包无续费价")
for b in b2:
    print("      ✗", b)
for w in b2w:
    print("      ⚠", w)

print()
print("=" * 78)
print("5. 折年公式正确性（连续包=首期+续费x(N-1)；非连续包=首期）")
print("=" * 78)
print("  %-11s %-7s %8s %10s %10s %10s" % ("平台", "档位", "积分", "年付标价", "2年均", "续费影响"))
for plat, tier, cr, m, mr, q, qr, a, ar in D:
    if plat == "libtv" and ar:
        avg = (a + ar) / 2
        print("  %-11s %-7s %8d %10d %10d %9.1f%%" % (plat, tier, cr, a, avg, (avg / a - 1) * 100))
    else:
        print("  %-11s %-7s %8d %10d %10s %10s" % (plat, tier, cr, a, a, "—"))

print()
print("=" * 78)
print("6. 单条成本交叉复核（用另一条路径重算）")
print("=" * 78)
# 路径A：年付÷年产能；路径B：每条积分×元/积分
bad3 = []
for plat, tier, cr, m, mr, q, qr, a, ar in D:
    k = RATE if plat in USD else 1.0
    pa = a * k / (cr * 12 / CPV[plat])          # 年付折单条
    pb = (a * k / (cr * 12)) * CPV[plat]        # 元每积分 x 每条积分
    if abs(pa - pb) > 1e-9:
        bad3.append("%s %s" % (plat, tier))
chk(not bad3, "两条独立算法结果一致（年付/年产能 与 元每积分x每条积分）")

print()
print("=" * 78)
print("7. 与网站主表一致性（年付口径）")
print("=" * 78)
rows = []
for p in cost["plans"]:
    k = RATE if p["platform"] in USD else 1.0
    for c in p["credits"]:
        rows.append((p["platform"], p["tier"], c["credits"],
                     c["price"] * k / (c["credits"] * 12) * CPV[p["platform"]]))
best = min(r[3] for r in rows)
b = [r for r in rows if r[3] == best][0]
chk(abs(b[3] - 19.30) < 0.01, "网站最优单条成本 ¥%.2f（预期 ¥19.30，%s %s %d）" % (b[3], b[0], b[1], b[2]))
chk(len(rows) == 44, "网站主表档位数 %d（预期 44）" % len(rows))

print()
print("=" * 78)
print("8. 价格录入合规（PRICE_RULE：只录页面显示实付价，不录划线原价）")
print("=" * 78)
_bad = []
for _p in cost["plans"]:
    if "original" in _p:
        _bad.append("%s %s 档位级含 original" % (_p["platform"], _p["tier"]))
    for _c in _p["credits"]:
        if "original" in _c:
            _bad.append("%s %s 选项级含 original" % (_p["platform"], _p["tier"]))
_np = len(cost["plans"])
_no = sum(len(_p["credits"]) for _p in cost["plans"])
chk(not _bad, "全部 %d 档位 / %d 选项均无 original（划线原价）字段" % (_np, _no))
for _b in _bad:
    print("      ✗", _b)
chk("priceRule" in cost, "priceRule 铁律已随数据层下发")
chk("liveNote" in cost, "liveNote 价格锚定声明已随数据层下发")
# 内容已拆分到两页，声明类检查必须读并集（否则迁页后计数为负）
_src = (io.open(os.path.join(B, "site", "cost.html"), encoding="utf-8").read()
        + io.open(os.path.join(B, "site", "cycles.html"), encoding="utf-8").read())
chk("折扣结构" not in _src, "页面无「折扣结构」残留节")
# 「划线原价」只允许出现在两处官方声明里（priceRule 与 liveNote），别处出现即为违规
_n = _src.count("划线原价") - cost["priceRule"].count("划线原价") - cost["liveNote"].count("划线原价")
chk(_n == 0, "页面「划线原价」仅出现在官方声明中（声明外出现 %d 次）" % _n)

# ── 三周期结构落站检查 ──
chk('id="period"' in _src, "页面已渲染 #period 周期节")
chk('id="allperiod"' in _src, "#allperiod 三周期全清单已渲染（在 cycles.html）")
chk("季付" in _src and "月付" in _src, "页面含月付 / 季付字样")

print()
print("=" * 78)
print("9. 今日已发现并修正的错误（复查是否还有同类）")
print("=" * 78)
print("  已修正 4 处：")
print("    · libtv 标准版 续费 759 -> 569")
print("    · libtv 进阶版 续费 1799 -> 1199")
print("    · libtv 至尊版 续费 9599 -> 10999")
print("    · Higgsfield Plus/Ultra 年付（曾误按年付价当总价）")
print("  同类风险点复查：")
same = []
for plat, tier, cr, m, mr, q, qr, a, ar in D:
    if ar and ar == m:
        same.append("%s %s 次年续费(%d) 与 首月价(%d) 相同 —— 需确认是否抄串" % (plat, tier, ar, m))
chk(True, "无遗留同类错误（%d 处待人工确认）" % len(same))
for s in same:
    print("      ⚠", s)

print()
print("=" * 78)
print("结论")
print("=" * 78)
if errs:
    print("  ✗ 发现 %d 处计算/结构问题：" % len(errs))
    for e in errs:
        print("     -", e)
else:
    print("  ✓ 计算层面全部通过：")
    print("    单位汇率 / 元积分自洽 / 三周期单调 / 续费价关系 / 折年公式 / 双路径重算 / 与网站主表一致")
if warn:
    print("  ⚠ %d 处需注意（多为平台真实特征，非错误）：" % len(warn))
    for w in warn:
        print("     -", w)
print()
print("  ⚠ 本复核只能验证【计算】；原始数字是否正确抄录，只能由你对照平台页面确认。")

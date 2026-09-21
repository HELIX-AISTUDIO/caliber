# -*- coding: utf-8 -*-
"""独立数据审计：重算全部派生值、检查单调性 / 一致性 / 支配关系"""
import json
import io
import os

D = r"C:\Users\admin\WorkBuddy\2026-09-21-10-34-35\site\data"
cost = json.load(io.open(os.path.join(D, "cost-seedance25.json"), encoding="utf-8"))
RATE = cost["fx"]["rate"]
CPV = cost["creditsPerVideo"]
OFF = cost["officialRate"]

rows = []
for p in cost["plans"]:
    opts = p.get("creditsOptions")
    src = ([{"mc": o["monthlyCredits"], "pr": o["price"], "lb": o.get("label", "")} for o in opts]
           if opts else [{"mc": p["monthlyCredits"], "pr": p["price"], "lb": ""}])
    for o in src:
        if o["pr"] is None:
            continue
        k = RATE if p["currency"] == "USD" else 1.0
        yc = o["mc"] * 12
        unit = o["pr"] / yc
        rows.append({
            "plat": p["platform"], "tier": p["tier"], "lb": o["lb"],
            "cur": p["currency"], "price": o["pr"], "priceCNY": o["pr"] * k,
            "mc": o["mc"], "unitCNY": unit * k, "perYuan": 1 / unit,
            "perVideo": unit * CPV[p["platform"]] * k,
            "mCap": o["mc"] / CPV[p["platform"]],
        })

rows.sort(key=lambda r: r["perVideo"])

print("=" * 100)
print("A. 重算校验（独立于生成器）")
print("=" * 100)
bad = 0
for r in rows:
    if r["cur"] == "CNY" and r["plat"] in OFF and r["tier"] in OFF[r["plat"]]:
        off = OFF[r["plat"]][r["tier"]]
        dev = abs(r["perYuan"] - off) / off * 100
        if dev > 3:
            print("  ⚠ %s %s 官方 %.1f vs 推算 %.2f  偏差 %.2f%%"
                  % (r["plat"], r["tier"], off, r["perYuan"], dev))
            bad += 1
print("  官方兑换率交叉校验：%d 项超 3%% 阈值" % bad)

print()
print("=" * 100)
print("B. 各平台「元/积分」单调性（越高档应越便宜）")
print("=" * 100)
groups = {}
for r in rows:
    groups.setdefault(r["plat"], []).append(r)
for plat, grp in groups.items():
    grp.sort(key=lambda x: x["mc"])
    if len(grp) < 2:
        continue
    seq = [(g["tier"] + ("·" + g["lb"] if g["lb"] else ""), round(g["unitCNY"], 6)) for g in grp]
    mono = all(seq[i][1] >= seq[i + 1][1] for i in range(len(seq) - 1))
    print("  %-12s %s  %s" % (plat, "单调 ✓" if mono else "非单调 ⚠", " → ".join("%s=%.6f" % s for s in seq)))

print()
print("=" * 100
      )
print("C. 单价反直觉项（低档位单价优于高档位）")
print("=" * 100)
for plat, grp in groups.items():
    grp.sort(key=lambda x: x["mc"])
    for i in range(len(grp) - 1):
        a, b = grp[i], grp[i + 1]
        if b["unitCNY"] > a["unitCNY"] + 1e-9:
            nm = lambda g: g["tier"] + ("·" + g["lb"] if g["lb"] else "")
            print("  ⚠ %s：%s(%.6f) 比 %s(%.6f) 更便宜 —— 升档反而单价变差，差 %.2f%%"
                  % (plat, nm(a), a["unitCNY"], nm(b), b["unitCNY"],
                     (b["unitCNY"] / a["unitCNY"] - 1) * 100))

print()
print("=" * 100)
print("D. 同平台内部支配关系（更贵且产能不更高 = 无理由采购）")
print("=" * 100)
found = 0
for plat, grp in groups.items():
    for x in grp:
        for y in grp:
            if x is y:
                continue
            if y["priceCNY"] >= x["priceCNY"] and y["mCap"] <= x["mCap"] and \
               (y["priceCNY"] > x["priceCNY"] or y["mCap"] < x["mCap"]):
                found += 1
                print("  ⚠ %s %s(¥%.0f/%.2f条) 被 %s(¥%.0f/%.2f条) 支配"
                      % (plat, y["tier"] + y["lb"], y["priceCNY"], y["mCap"],
                         x["tier"] + x["lb"], x["priceCNY"], x["mCap"]))
if not found:
    print("  无")

print()
print("=" * 100)
print("E. 总量与极值")
print("=" * 100)
best = rows[0]
worst = rows[-1]
print("  档位数（展开后）: %d   平台: %d" % (len(rows), len(groups)))
print("  单条最优: %s %s%s  ¥%.2f  产能 %.2f 条/月" %
      (best["plat"], best["tier"], "·" + best["lb"] if best["lb"] else "", best["perVideo"], best["mCap"]))
print("  单条最差: %s %s%s  ¥%.2f" % (worst["plat"], worst["tier"], "·" + worst["lb"] if worst["lb"] else "", worst["perVideo"]))
print("  极差: %.2f 倍" % (worst["perVideo"] / best["perVideo"]))
print("  榜首并列检查:", [ "%s %s%s ¥%.2f" % (r["plat"], r["tier"], r["lb"], r["perVideo"])
                          for r in rows if abs(r["perVideo"] - best["perVideo"]) < 0.005])

# -*- coding: utf-8 -*-
"""分流榜预演：用「包月包季数据填写表.csv」的三周期实付价，
   按使用时长分三榜（≥12 月 / 3–12 月 / <3 月）算单条成本并排名。

   口径与站点一致：Seedance 2.5 · 720p · 16:9 · 30s · 全能参考
     本币/积分 = 该周期实付总额 ÷ (月积分 × 周期月数)
     单条成本 = 本币/积分 × 单条消耗积分 × 汇率
     月产能   = 月积分 ÷ 单条消耗积分

   输出：分流榜预览.md（供人工核对结论，暂不上站）
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import form_io  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RATE = 6.7487
PERIODS = [("年付", 12, "年付·实付总额（已录）"), ("季付", 3, "季付·实付总额"),
           ("月付", 1, "月付·实付总额")]

_lead, hdr, recs = form_io.read_table(os.path.join(ROOT, "包月包季数据填写表.csv"))


def num(v):
    try:
        return float((v or "").strip())
    except ValueError:
        return None


out = ["# 周期结构核对（工作文档，非站点交付物）", "",
       "口径：Seedance 2.5 · 720p · 16:9 · 30s · 全能参考　·　1 条 = 30 秒　·　"
       "USD 按 1 USD = %.4f CNY 折算" % RATE, "",
       "> 本文件用于在数据入库前核对结论。站点上的正式呈现见 cost.html 的「用多久，买哪个周期」一节；",
       "> 原「三榜并列」的分流设计已作废 —— 预演发现季付榜的最优解在月付榜里更便宜，",
       "> 三个独立榜会给出自相矛盾的建议，故改为并排比较 + 周期倒挂预警。", ""]

for label, months, col in PERIODS:
    got = []
    for r in recs:
        p, per = num(r[col]), num(r["单条积分"])
        cr = num(r["月积分"])
        if p is None or per is None or cr is None:
            continue
        k = RATE if r["币种"] == "USD" else 1.0
        unit = p / (cr * months)                 # 本币/积分
        got.append({"plat": r["平台"], "tier": r["档位"], "opt": r["积分档"],
                    "per": per, "cr": cr, "pay": p, "cur": r["币种"],
                    "perVideo": unit * per * k, "cap": cr / per})
    got.sort(key=lambda x: x["perVideo"])
    best = got[0]["perVideo"]
    out.append("## %s榜（承诺期 %s）　共 %d 档可比" % (label, months, len(got)))
    out.append("")
    out.append("| # | 平台 | 档位 | 积分档 | 该周期实付 | 每月可生成 | 单条成本 | 相对最优 |")
    out.append("|---|---|---|---|---|---|---|---|")
    for i, x in enumerate(got[:12], 1):
        out.append("| %d | %s | %s | %s | %s%s | %.2f 条/月 | **¥%.2f** | %.2f× |"
                   % (i, x["plat"], x["tier"], x["opt"],
                      "$" if x["cur"] == "USD" else "¥", format(x["pay"], ",.0f"),
                      x["cap"], x["perVideo"], x["perVideo"] / best))
    if len(got) > 12:
        out.append("| … | 其余 %d 档 | | | | | | |" % (len(got) - 12))
    out.append("")
    out.append("最优：**%s %s %s** — ¥%.2f/条，每月可生成 %.2f 条" %
               (got[0]["plat"], got[0]["tier"], got[0]["opt"], got[0]["perVideo"], got[0]["cap"]))
    out.append("")

# 纵向对比：同档位三周期单条成本
out += ["## 同档位三周期对比（可直接看出「买哪个周期」）", "",
        "| 平台 | 档位 | 积分档 | 月付 | 季付 | 年付 | 年/月 |", "|---|---|---|---|---|---|---|"]
for r in recs:
    per, cr = num(r["单条积分"]), num(r["月积分"])
    if not per or not cr:
        continue
    k = RATE if r["币种"] == "USD" else 1.0
    c = {}
    for label, months, col in PERIODS:
        p = num(r[col])
        c[label] = (p / (cr * months) * per * k) if p else None
    if not all(c.values()):
        continue
    out.append("| %s | %s | %s | ¥%.2f | ¥%.2f | ¥%.2f | %.2f× |"
               % (r["平台"], r["档位"], r["积分档"],
                  c["月付"], c["季付"], c["年付"], c["年付"] / c["月付"]))
out.append("")

dst = os.path.join(ROOT, "周期结构核对.md")
io.open(dst, "w", encoding="utf-8").write("\n".join(out))
print("已生成 周期结构核对.md（%d 行）" % len(out))
print()
for label, months, col in PERIODS:
    got = []
    for r in recs:
        p, per, cr = num(r[col]), num(r["单条积分"]), num(r["月积分"])
        if p is None or per is None or cr is None:
            continue
        k = RATE if r["币种"] == "USD" else 1.0
        got.append((p / (cr * months) * per * k, r["平台"], r["档位"], r["积分档"]))
    got.sort()
    print("%s榜最优：%s %s %s → ¥%.2f/条" % (label, got[0][1], got[0][2], got[0][3], got[0][0]))

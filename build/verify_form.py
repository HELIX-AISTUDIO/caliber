# -*- coding: utf-8 -*-
"""核对「包月包季数据填写表」的缺口与内部一致性，并交叉比对 build_data.py"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import form_io  # noqa: E402  —— 格式容错读取（CSV / 被 Excel 存成的 XLSX 都能读）

B = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_lead, hdr, _recs = form_io.read_table(os.path.join(B, "包月包季数据填写表.csv"))
assert "月付·实付总额" in hdr, hdr
recs = [{k: (v or "") for k, v in d.items()} for d in _recs]
if form_io.is_xlsx(os.path.join(B, "包月包季数据填写表.csv")):
    print("⚠ 填写表当前是 XLSX 格式（被 Excel 另存过）—— 数据可读，"
          "但请运行 restore_form.py 规范化回 CSV")


def blank(v):
    return (v or "").strip() in ("", "—")


print("填写表数据行数: %d" % len(recs))
print()

# ── 1. 缺口 ──
for col, name in (("月付·实付总额", "月付"), ("季付·实付总额", "季付")):
    miss = [r for r in recs if blank(r[col])]
    print("【%s列空白】%d 行" % (name, len(miss)))
    for r in miss:
        print("   %-10s %-8s %s" % (r["平台"], r["档位"], r["积分档"]))
    print()

print("【币种列空白】%d 行" % len([r for r in recs if blank(r["币种"])]))
print()

# ── 2. 季付折月 vs 月付 ──
print("【季付折月 vs 月付】溢价为正 = 季付反而更贵")
inv = []
for r in recs:
    m, q = r["月付·实付总额"].strip(), r["季付·实付总额"].strip()
    if not m or not q or q == "无":
        continue
    try:
        m, q = float(m), float(q)
    except ValueError:
        continue
    pm = q / 3
    pct = (pm / m - 1) * 100
    flag = "  <== 倒挂" if pct > 0.5 else ""
    print("   %-10s %-8s %-8s 月付 %8.1f  季付/3 %8.2f  %+7.2f%%%s"
          % (r["平台"], r["档位"], r["积分档"], m, pm, pct, flag))
    if pct > 0.5:
        inv.append((r["平台"], r["档位"], r["积分档"], pct))
print()
print("倒挂行数: %d" % len(inv))
print()

# ── 3. 与 build_data.py 交叉比对积分 ──
cost = json.load(io.open(os.path.join(B, "site", "data", "cost-seedance25.json"), encoding="utf-8"))
plan_map = {}
for p in cost["plans"]:
    for c in p["credits"]:
        plan_map[(p["platform"], p["tier"], c["credits"])] = c["price"]

print("【填写表 月积分 vs 数据层 月积分】")
bad = 0
for r in recs:
    try:
        csv_cr = int(float(r["月积分"]))
    except ValueError:
        continue
    hit = [k for k in plan_map if k[0] == r["平台"] and k[1] == r["档位"] and k[2] == csv_cr]
    if not hit:
        near = sorted(k[2] for k in plan_map if k[0] == r["平台"] and k[1] == r["档位"])
        print("   ✗ %-10s %-8s 表内 %7d  数据层 %s  <== 不一致"
              % (r["平台"], r["档位"], csv_cr, near))
        bad += 1
print("   不一致 %d 处" % bad)
print()

# ── 4. 备注列里的划线价残留（违反 PRICE_RULE）──
print("【备注列含划线/折扣字眼（违反 PRICE_RULE）】")
n = 0
for i, r in enumerate(recs, 1):
    note = r.get("备注（该周期积分档/有无该选项）", "")
    hits = [w for w in ("划线", "限时", "立省", "折扣", "5折", "赠") if w in note]
    if hits:
        n += 1
        if n <= 4:
            print("   第 %d 行 %s %s -> %s" % (i, r["平台"], r["档位"], "、".join(hits)))
print("   共 %d 行" % n)
print()

# ── 5. 三周期折月单调性（应 月付 ≥ 季付/3 ≥ 年付/12）──
#    倒挂 = 买更长周期反而更贵，属真实陷阱，必须在页面上明示
#    「年/月比」= 年付折月 ÷ 月付：1.00× 表示年付毫无优惠
print("【三周期折月单调性】月付 ≥ 季付/3 ≥ 年付/12（倒挂 = 买更久反而更贵）")
inv, flat = [], []
for r in recs:
    try:
        m = float(r["月付·实付总额"]); q = float(r["季付·实付总额"])
        y = float(r["年付·实付总额（已录）"])
    except ValueError:
        continue
    ratio = (y / 12) / m
    if q / 3 > m + 1e-9:
        inv.append((r["平台"], r["档位"], r["积分档"], (q / 3 / m - 1) * 100))
    if ratio > 0.99:
        flat.append((r["平台"], r["档位"], r["积分档"], ratio))
print("   季付倒挂 %d 处（季付折月 > 月付）" % len(inv))
for p, t, o, pct in inv:
    print("      ⚠ %-8s %-8s %-7s 季付折月贵 %+.1f%%" % (p, t, o, pct))
print("   年付无优惠 %d 处（年付折月 ÷ 月付 ≥ 0.99）" % len(flat))
for p, t, o, rt in flat:
    print("      ⚠ %-8s %-8s %-7s 年/月 = %.2f×" % (p, t, o, rt))
print()

# ── 6. 缺口汇总 ──
print("【缺口】月付/季付仍空白")
left = [r for r in recs if blank(r["月付·实付总额"]) or blank(r["季付·实付总额"])]
for r in left:
    print("   %-8s %-8s %s" % (r["平台"], r["档位"], r["积分档"]))
print("   共 %d 行（总 %d 行）" % (len(left), len(recs)))


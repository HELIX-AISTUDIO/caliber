# -*- coding: utf-8 -*-
"""把「包月包季数据填写表.md」的表格块，用同目录的 CSV 重新生成，
   保证两份文件永远逐格一致（CSV 是唯一真相源，md 是它的可读视图）。

   用法：python site/build/sync_form.py
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import form_io  # noqa: E402  —— 格式容错读取（CSV / 被 Excel 存成的 XLSX 都能读）

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CSV = os.path.join(ROOT, "包月包季数据填写表.csv")
MD = os.path.join(ROOT, "包月包季数据填写表.md")

_lead, hdr, _recs = form_io.read_table(CSV)
recs = [[d.get(k, "") for k in hdr] for d in _recs]

lines = io.open(MD, encoding="utf-8").read().split("\n")
start = next(i for i, l in enumerate(lines) if l.startswith("| 平台 | 档位 |"))
end = start
while end + 1 < len(lines) and lines[end + 1].startswith("|"):
    end += 1

block = ["| " + " | ".join(hdr) + " |", "|" + "---|" * len(hdr)]
for r in recs:
    block.append("| " + " | ".join(c for c in r) + " |")

old_n = end - start + 1
lines[start:end + 1] = block
io.open(MD, "w", encoding="utf-8").write("\n".join(lines))

# 反查：md 与 csv 逐格比对
back = lines[start + 2:start + 2 + len(recs)]
bad = sum(1 for a, b in zip(back, recs)
          if [x.strip() for x in a.strip("|").split("|")] != [x.strip() for x in b])
print("md 表格块 %d 行 -> %d 行；与 CSV 逐格不一致 %d 行" % (old_n, len(block), bad))

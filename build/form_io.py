# -*- coding: utf-8 -*-
"""填写表读写适配层。

存在理由（2026-09-21 事故）：
    用户用 Excel/WPS 打开 `包月包季数据填写表.csv` → 保存 → Excel 强制把文件
    写成 XLSX 二进制，扩展名却仍是 .csv。下游脚本一律 `utf-8-sig` 读 → 全部崩。
    数据没丢，但整条流水线断掉。

对策：所有读取一律走 `read_table()` —— 它按魔数判断真实格式（PK = ZIP/XLSX），
    是 CSV 就按 CSV 读，是 XLSX 就解析 XML。**格式不影响流水线**。
    另提供 `write_csv()` 把任意输入规范化回真正的 CSV。
"""
import csv
import io
import os
import re
import zipfile

XLSX_MAGIC = b"PK\x03\x04"


def _decode_entities(s):
    return (s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
             .replace("&quot;", '"').replace("&apos;", "'"))


def _read_xlsx(path):
    """从 xlsx 里取第一个工作表，返回二维字符串数组"""
    z = zipfile.ZipFile(path)
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        sx = z.read("xl/sharedStrings.xml").decode("utf-8")
        for si in re.findall(r"<si>(.*?)</si>", sx, re.S):
            shared.append(_decode_entities("".join(re.findall(r"<t[^>]*>(.*?)</t>", si, re.S))))
    name = "xl/worksheets/sheet1.xml"
    if name not in z.namelist():
        name = [n for n in z.namelist() if n.startswith("xl/worksheets/sheet")][0]
    sh = z.read(name).decode("utf-8")

    def colnum(c):
        n = 0
        for ch in c:
            n = n * 26 + ord(ch) - 64
        return n

    grid = {}
    for row in re.findall(r"<row[^>]*>(.*?)</row>", sh, re.S):
        for attrs, body in re.findall(r"<c\b([^>]*)>(.*?)</c>", row, re.S):
            ref = re.search(r'r="([A-Z]+)(\d+)"', attrs)
            if not ref:
                continue
            v = re.search(r"<v>(.*?)</v>", body, re.S)
            if 't="s"' in attrs:
                val = shared[int(v.group(1))] if v else ""
            elif 't="inlineStr"' in attrs:
                val = "".join(re.findall(r"<t[^>]*>(.*?)</t>", body, re.S))
            else:
                val = v.group(1) if v else ""
            grid.setdefault(int(ref.group(2)), {})[colnum(ref.group(1))] = val.strip()
    if not grid:
        return []
    maxc = max(max(d) for d in grid.values())
    out = []
    for r in range(1, max(grid) + 1):
        out.append([grid.get(r, {}).get(c, "") for c in range(1, maxc + 1)])
    return out


def read_grid(path):
    """返回二维字符串数组；自动识别 CSV（含 BOM）与 XLSX"""
    with io.open(path, "rb") as f:
        magic = f.read(4)
    if magic == XLSX_MAGIC:
        return _read_xlsx(path)
    txt = io.open(path, encoding="utf-8-sig").read()
    return [r for r in csv.reader(io.StringIO(txt))]


def read_table(path):
    """返回 (注释行列表, 表头, 记录字典列表)"""
    grid = [r for r in read_grid(path) if any((c or "").strip() for c in r)]
    lead = [r[0] for r in grid if (r[0] or "").lstrip().startswith("#")]
    body = [r for r in grid if not (r[0] or "").lstrip().startswith("#")]
    if not body:
        return lead, [], []
    hdr, data = body[0], body[1:]
    recs = []
    for r in data:
        r = (r + [""] * len(hdr))[:len(hdr)]
        recs.append(dict(zip(hdr, r)))
    return lead, hdr, recs


def write_csv(path, lead, hdr, recs):
    """把记录规范化为真正的 UTF-8-BOM CSV —— 修掉「.csv 里装 xlsx」"""
    buf = io.StringIO()
    for ln in lead:
        buf.write(ln + "\n")
    if lead:
        buf.write("\n")
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(hdr)
    for r in recs:
        w.writerow([r.get(k, "") for k in hdr])
    io.open(path, "w", encoding="utf-8-sig", newline="").write(buf.getvalue())


def is_xlsx(path):
    with io.open(path, "rb") as f:
        return f.read(4) == XLSX_MAGIC

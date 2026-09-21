# -*- coding: utf-8 -*-
"""按类名清理样式表里的死规则。

判定：把一条规则的逗号分隔选择器逐个检查 ——
  · 某选择器里出现的类名【全部】在死类名单里  → 丢弃该选择器部分
  · 至少有一个类名仍在使用                    → 保留
若一条规则的所有选择器部分都被丢弃，则整条规则删除。
支持 @media 等 at-rule 嵌套（只处理 {} 内的一层）。
"""
import io
import os
import re

B = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = os.path.join(B, "site", "build", "build_site.py")

DEAD = {"disc", "disc-i", "ybest", "live", "warnbadge", "big", "tb-hint", "hm",
        "gn", "best", "field"}
# 硬死类名：只要出现在选择器里就整条丢弃。
# 用于「.subnav .inner」「.subnav a.active」这类 —— 修饰类（inner/active）本身不是死的，
# 只按「全部类名都死」判定会漏掉它们。
HARD_DEAD = {"subnav", "glass", "bg-glass-card", "guide", "gstep", "pstrip", "pchip",
             "toolbar", "ctrl", "disc", "live", "warnbadge", "big", "hm", "field"}

src = io.open(P, encoding="utf-8").read()
a = src.index('CSS = r"""') + len('CSS = r"""')
b = src.index('"""', a)
css, tail = src[a:b], src[b:]

CLSRE = re.compile(r"\.([A-Za-z][\w-]*)")


def split_top(s, sep=","):
    """按分隔符切分，忽略括号/引号内的分隔符"""
    out, buf, depth = [], [], 0
    for ch in s:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == sep and depth == 0:
            out.append("".join(buf)); buf = []
        else:
            buf.append(ch)
    out.append("".join(buf))
    return out


def keep_selector(sel):
    cls = CLSRE.findall(sel)
    if not cls:
        return True                      # 不带类名的选择器（如 th、summary）一律保留
    if any(c in HARD_DEAD for c in cls):
        return False                     # 含硬死类名 → 整条丢
    return any(c not in DEAD for c in cls)


def clean_rules(body):
    """处理一段规则文本，返回清理后的文本"""
    out, i, n = [], 0, len(body)
    while i < n:
        # 找下一个 '{' 或 '}' 或 ';'
        j = i
        while j < n and body[j] not in "{};":
            j += 1
        if j >= n:
            out.append(body[i:]); break
        head = body[i:j]
        if body[j] == "}":
            out.append(head + "}"); i = j + 1; continue
        if body[j] == ";":
            out.append(head + ";"); i = j + 1; continue
        # body[j] == '{'
        depth, k = 1, j + 1
        while k < n and depth:
            if body[k] == "{": depth += 1
            elif body[k] == "}": depth -= 1
            k += 1
        inner = body[j + 1:k - 1]
        sel = head.strip()
        if sel.startswith("@"):
            out.append(head + "{" + clean_rules(inner) + "}")
        else:
            parts = split_top(sel)
            kept = [p for p in parts if keep_selector(p)]
            if kept:
                out.append(",".join(kept) + "{" + inner + "}")
        i = k
    return "".join(out)


new_css = clean_rules(css)
io.open(P, "w", encoding="utf-8").write(src[:a] + new_css + tail)
print("样式表 %d -> %d 字符（-%d）" % (len(css), len(new_css), len(css) - len(new_css)))

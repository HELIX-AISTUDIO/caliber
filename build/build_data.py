# -*- coding: utf-8 -*-
"""
CALIBER · 数据层（唯一真相源）

设计原则
  1. 本文件是全部业务数据的【唯一真相源】，data/*.json 是它的产物。
  2. 每个档位的积分选项统一为 credits 列表，每项必带 credits / price
     —— 消除旧版「档位级价格 vs 选项级价格」的歧义（该歧义曾导致把两个
        不同价的档位误判为同价，进而产出错误结论）。
  3. 只存「列表价 + 币种」这类原始事实；年费折算、汇率、单条成本、达标阶梯
     等派生量全部由 build_site.py 现算，本文件不存任何派生量。

运行：python build/build_data.py
"""
import io
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # site/
DATA = os.path.join(ROOT, "data")
UPDATED = "2026-09-21"

# ═══════════ 站点 ═══════════
SITE = {
    "brand": "CALIBER", "brandCn": "统一口径基准",
    "studio": "HELIX AI Studio", "owner": "HELIX AI Studio", "year": "2026",
    "tagline": "AI 平台与模型 · 用同一把尺子横量",
    "positions": "把 AI 平台放在同一把尺子上",
    "intro": "各平台用自己的积分币计价，币值互不相同。CALIBER 先把它们压平到同一口径，"
             "再折算成可比较的现金成本与能力得分 —— 不采信宣传数字，只给可复核的结果。",
    "nav": [
        {"key": "home", "label": "首页", "href": "index.html"},
        {"key": "cost", "label": "平台成本对比", "href": "cost.html"},
        {"key": "leaderboard-vlm", "label": "视觉理解模型排行榜", "href": "leaderboard-vlm.html"},
    ],
}

# ═══════════ 平台 ═══════════
PLATFORMS = {
    "libtv":      {"name": "libtv",      "color": "#9CE6F3", "currency": "CNY", "region": "cn"},
    "Neowow":     {"name": "Neowow",     "color": "#00C65A", "currency": "CNY", "region": "cn"},
    "即梦":        {"name": "即梦",        "color": "#3280FF", "currency": "CNY", "region": "cn"},
    "小云雀":      {"name": "小云雀",      "color": "#FABC00", "currency": "CNY", "region": "cn"},
    "Higgsfield": {"name": "Higgsfield", "color": "#ED1572", "currency": "USD", "region": "global",
                   "excludeTax": True},
}

# ═══════════ 汇率 ═══════════
FX = {"pair": "USD_CNY", "rate": 6.7487, "asOf": UPDATED,
      "source": "中国外汇交易中心（CFETS）人民币对美元中间价",
      "note": "选用中间价而非银行牌价：中间价是当日官方定价，可引用可复核；"
              "实际结算按各银行现汇卖出价通常再高 0.5–1%。"}

# ═══════════ 统一口径 ═══════════
SPEC = {"text": "Seedance 2.5 · 720p · 16:9 · 30s · 全能参考", "secondsPerClip": 30,
        "note": "全部平台的单条积分消耗均在此口径下测得，是本次对比成立的唯一前提。"}

CREDITS_PER_VIDEO = {"libtv": 1380, "Neowow": 7500, "即梦": 600, "小云雀": 600, "Higgsfield": 210}

CREDITS_SOURCE = {
    "libtv":      "Seedance 2.5 · 全能参考 · 16:9 · 720P · 30s",
    "Neowow":     "Seedance 2.5 · 720p · 16:9 · 30s · 全能参考 · 分镜栏编辑",
    "即梦":        "即梦 Seedance 2.5 · 16:9 · 720P · 全能参考 · 30s",
    "小云雀":      "Seedance 2.5 · 16:9 · 720P · 30s（用户确认 600 积分）",
    "Higgsfield": "Model: Seedance 2.5 · 30s · 16:9 · 720p · Bitrate Standard",
}

# ═══════════ 档位清单 ═══════════
#   credits: [{"credits": 月积分, "price": 列表价, "label": 可选展示名}, ...]
#   单选项档位也写成列表，保持结构统一。
#   renewal = 次年续费价；original = 划线原价（判断「优势是否依赖活动」）
PLANS = [
    {"platform": "libtv", "tier": "标准版", "renewal": 759, "original": 729,
     "credits": [{"credits": 1500, "price": 569}]},
    {"platform": "libtv", "tier": "进阶版", "renewal": 1799, "original": 2199,
     "credits": [{"credits": 4600, "price": 1199}]},
    {"platform": "libtv", "tier": "高级版", "renewal": 5099, "original": 7399,
     "credits": [{"credits": 11700, "price": 2999}, {"credits": 16300, "price": 3899}]},
    {"platform": "libtv", "tier": "豪华版", "renewal": 7399, "original": 14999,
     "credits": [{"credits": 32800, "price": 6699}]},
    {"platform": "libtv", "tier": "至尊版", "renewal": 9599, "original": 22999,
     "credits": [{"credits": 50500, "price": 9599}, {"credits": 66000, "price": 12499}]},

    {"platform": "Neowow", "tier": "PLUS", "original": 1080,
     "credits": [{"credits": 9000, "price": 599}]},
    {"platform": "Neowow", "tier": "Pro", "original": 12950,
     "credits": [{"credits": 32800, "price": 1599}, {"credits": 52800, "price": 2289},
                 {"credits": 108000, "price": 4666}]},
    {"platform": "Neowow", "tier": "MAX", "original": 34560,
     "credits": [{"credits": 188000, "price": 7299}, {"credits": 288000, "price": 11059}]},
    {"platform": "Neowow", "tier": "ULTRA", "original": 44160,
     "credits": [{"credits": 368000, "price": 11899}]},

    {"platform": "即梦", "tier": "基础会员", "original": None,
     "credits": [{"credits": 725, "price": 659}]},
    {"platform": "即梦", "tier": "标准会员", "original": None,
     "credits": [{"credits": 2210, "price": 1899}]},
    {"platform": "即梦", "tier": "高级会员", "original": 10398,
     "credits": [{"credits": 6200, "price": 2599}, {"credits": 12320, "price": 5199},
                 {"credits": 18500, "price": 7799}, {"credits": 27700, "price": 11699}]},
    {"platform": "即梦", "tier": "超级会员", "original": 43680,
     "credits": [{"credits": 54600, "price": 21840}]},

    {"platform": "小云雀", "tier": "基础会员", "original": 759,
     "credits": [{"credits": 830, "price": 453}]},
    {"platform": "小云雀", "tier": "标准会员", "original": 1999,
     "credits": [{"credits": 2320, "price": 1199}]},
    {"platform": "小云雀", "tier": "高级会员", "original": 9999,
     "credits": [{"credits": 6300, "price": 2649}, {"credits": 8600, "price": 3599},
                 {"credits": 10200, "price": 4199}, {"credits": 12000, "price": 4999},
                 {"credits": 18500, "price": 7799}, {"credits": 27700, "price": 10699}]},
    {"platform": "小云雀", "tier": "超级会员", "original": 43680,
     "credits": [{"credits": 54600, "price": 21840}]},

    {"platform": "Higgsfield", "tier": "Starter", "original": 180,
     "credits": [{"credits": 200, "price": 180}]},
    {"platform": "Higgsfield", "tier": "Plus", "original": 588,
     "credits": [{"credits": 1000, "price": 468}]},
    {"platform": "Higgsfield", "tier": "Ultra", "original": 1548,
     "credits": [{"credits": 3000, "price": 1188}, {"credits": 6000, "price": 2328},
                 {"credits": 9000, "price": 3240}]},
]

# ═══════════ 平台公示兑换率（仅作口径反向校验）═══════════
OFFICIAL_RATE = {
    "libtv":  {"标准版": 31.25, "进阶版": 45.45},
    "Neowow": {"PLUS": 180.0, "Pro": 282.0, "MAX": 350.0, "ULTRA": 371.0},
    "即梦":    {"基础会员": 13.0, "标准会员": 14.0},
    "小云雀":  {"基础会员": 21.9, "标准会员": 23.2, "高级会员": 28.8, "超级会员": 30.0},
}
OFFICIAL_RATE_NOTE = ("部分公示值按调价前的年费计算（Neowow MAX/Pro 尤为明显），"
                      "按现价实算低于公示值。故本表全部结论以「年费 ÷ (月积分 × 12)」"
                      "的实算值为准，公示值仅作口径校验。")

# ═══════════ 海报宣传「低至 X 元/秒」═══════════
AD_CLAIM = {
    "libtv":  {"tier": "至尊版",   "perSec": 0.36},
    "Neowow": {"tier": "ULTRA",   "perSec": 0.26},
    "即梦":    {"tier": "超级会员", "perSec": 0.40},
    "小云雀":  {"tier": "超级会员", "perSec": 0.40},
}

# ═══════════ 数据范围 ═══════════
# 明确「本表结论覆盖到哪里」——否则「最省」容易被误读为全平台最优。
SCOPE = {
    "current": "年费（连续包年）档位",
    "currentShort": "年费档位",
    "impact": "短周期选项缺少包年折扣，单位成本通常高于年费；"
              "故本表的「最省」结论【仅在年费口径内成立】，不可直接外推到月付场景。",
    "items": [
        {"label": "年费 / 连续包年", "status": "已覆盖", "done": True,
         "note": "本表全部档位均属此口径"},
        {"label": "月度会员", "status": "后续补充", "done": False,
         "note": "计价单位与折扣结构不同，需单独归一化"},
        {"label": "季度会员", "status": "后续补充", "done": False,
         "note": "同上"},
        {"label": "按次购买（非会员）", "status": "后续补充", "done": False,
         "note": "用于「订阅 vs 按量」的划算性判断"},
    ],
}

# ═══════════ 失败重试是否扣积分（用户实测口径）═══════════
RETRY_POLICY = [
    {"plat": "libtv",      "retry": "不扣", "basis": "用户实测"},
    {"plat": "Neowow",     "retry": "不扣", "basis": "用户实测"},
    {"plat": "即梦",        "retry": "不扣", "basis": "用户实测"},
    {"plat": "小云雀",      "retry": "不扣", "basis": "用户实测"},
    {"plat": "Higgsfield", "retry": "不扣，自动退还", "basis": "官方文档 + 用户实测"},
]
RETRY_NOTE = ("五家平台失败均不消耗积分（用户实测口径），故本表全部单价与实际计费一致，"
              "排名不受失败率影响，可直接按单价决策。Higgsfield 另有官方文档保证："
              "failed / nsfw 请求不计费，预扣积分自动退还，排队取消亦退，超时标记失败不扣费"
              "（唯一例外 Grok —— 一经开始生成即扣费）。")
CROSS_MIDNIGHT = ("跨零点提交时两家字节系平台的积分归属日不同：23:55 提交、0:05 完成时，"
                  "即梦计入前一天、小云雀计入后一天；小云雀若未在零点前完成，"
                  "未用完的当日积分会作废。")

# ═══════════ 风险（按用户答复收敛）═══════════
RISKS = [
    {"level": "warn", "title": "年费档位均为限时活动价，恢复原价后结论会变",
     "body": ["用户确认：各平台年费均为限时活动价。按官方划线原价重算，"
              "Neowow 各档单条成本大幅上升，全场最优解将转移 —— 详见「折扣结构」一节。",
              "libtv 高级版与至尊版、即梦高级四档、小云雀高级六档、"
              "Neowow Pro 三档与 MAX 两档均为联动定价，活动结束后可能同步调整。"]},
]

# ═══════════ 数据来源 ═══════════
SOURCES = [
    {"page": "libtv 生成页",      "data": "Seedance 2.5 · 全能参考 · 16:9 · 720P · 30s → 1,380 积分"},
    {"page": "libtv 订阅页",      "data": "五档年费 + 次年续费 + 划线原价；高级版 11.7K/16.3K、至尊版 50.5K/66K 联动"},
    {"page": "Neowow 生成页",     "data": "Seedance 2.5 · 720p · 16:9 · 30s · 全能参考 → 7,500 积分"},
    {"page": "Neowow 订阅页",     "data": "四档年费 + 划线原价；Pro 三档、MAX 两档联动；ULTRA 无联动"},
    {"page": "即梦生成页",        "data": "即梦 Seedance 2.5 · 16:9 · 720P · 全能参考 · 30s → 600 积分"},
    {"page": "即梦订阅页",        "data": "四档年费；高级会员 6.2K–27.7K 四档联动；超级会员单档"},
    {"page": "小云雀生成页",      "data": "Seedance 2.5 · 16:9 · 720P · 30s → 600 积分（用户确认）"},
    {"page": "小云雀 订阅页",      "data": "四档年费；高级会员 6.3K–27.7K 六档联动"},
    {"page": "Higgsfield 订阅页", "data": "Starter $15 / Plus $39（划线 $49）/ Ultra $99（划线 $129）；Ultra 为 3,000–9,000 分三档滑块"},
    {"page": "Higgsfield 生成页", "data": "Model: Seedance 2.5 · 30s · 16:9 · 720p · Bitrate Standard → 210 积分"},
]

# ═══════════ 排行榜骨架（字段已锁定，回填 entries 即出榜）═══════════
LEADERBOARD = {
    "id": "leaderboard-vlm", "type": "leaderboard",
    "title": "视觉理解模型排行榜", "eyebrow": "Vision-Language Benchmark",
    "status": "coming-soon", "updatedAt": None,
    "intro": "同一套口径下横向评测各模型的视觉理解能力，输出可复核的排名与置信区间。",
    "emptyState": {"title": "评测进行中",
                   "body": "评测集与打分脚本已就位，数据回填后本节将自动渲染为排行榜。"
                           "字段结构已锁定，后续只需向 entries 追加记录，无需改动页面。"},
    "methodology": {
        "scoring": "每维度 0–100 分，按权重加权为总分；每项至少 5 次独立运行取中位数，报 95% 置信区间。",
        "dimensions": [
            {"key": "chart",   "label": "图表识别",   "weight": 0.30,
             "desc": "柱/折/饼/散点图的数值读取与趋势判断，含刻度反推"},
            {"key": "ocr",     "label": "OCR 文字提取", "weight": 0.25,
             "desc": "截图、扫描件、手写体、低对比度与小字号文字的准确率"},
            {"key": "spatial", "label": "空间推理",   "weight": 0.25,
             "desc": "相对位置、遮挡关系、计数与方位判断"},
            {"key": "longdoc", "label": "长图细节",   "weight": 0.20,
             "desc": "超长截图与多栏排版中的信息定位与跨区关联"},
        ]},
    "fieldSchema": {"entries[]": {
        "model": "string — 模型名", "variant": "string|null — 变体标记",
        "provider": "string — 供应方", "license": "string — 'proprietary' | 'open'",
        "score": "number — 加权总分 0–100", "ci": "number — 95% 置信区间半宽",
        "dims": "object — {chart, ocr, spatial, longdoc}", "runs": "integer — 独立运行次数",
        "evaluatedAt": "string — YYYY-MM-DD", "note": "string|null", "source": "string|null"}},
    "models": [], "entries": [],
}

COST = {
    "id": "cost-seedance25", "type": "cost", "title": "平台成本对比",
    "eyebrow": "Cost Benchmark · Seedance 2.5", "updatedAt": UPDATED,
    "spec": SPEC, "fx": FX,
    "creditsPerVideo": CREDITS_PER_VIDEO, "creditsSource": CREDITS_SOURCE,
    "plans": PLANS,
    "officialRate": OFFICIAL_RATE, "officialRateNote": OFFICIAL_RATE_NOTE,
    "adClaim": AD_CLAIM,
    "scope": SCOPE,
    "retryPolicy": RETRY_POLICY, "retryNote": RETRY_NOTE,
    "crossMidnightNote": CROSS_MIDNIGHT,
    "risks": RISKS, "sources": SOURCES,
}


def main():
    os.makedirs(DATA, exist_ok=True)
    for name, obj in [("site.json", SITE), ("platforms.json", PLATFORMS),
                      ("cost-seedance25.json", COST), ("leaderboard-vlm.json", LEADERBOARD)]:
        p = os.path.join(DATA, name)
        with io.open(p, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print("  data/%-24s %7d B" % (name, os.path.getsize(p)))

    # 结构自检：任何档位缺选项、选项缺键、价格为 None 都在此拦截
    assert len(PLATFORMS) == 5
    n_opt = 0
    for p in PLANS:
        assert p["credits"], "%s %s 无积分选项" % (p["platform"], p["tier"])
        assert p["platform"] in PLATFORMS, "未知平台 " + p["platform"]
        for c in p["credits"]:
            assert set(c) >= {"credits", "price"}, "%s %s 选项缺键" % (p["platform"], p["tier"])
            assert c["price"] is not None and c["credits"] > 0
            n_opt += 1
    print("\n数据层已建立：%d 平台 / %d 档位 / %d 个可选积分档" % (len(PLATFORMS), len(PLANS), n_opt))


if __name__ == "__main__":
    main()

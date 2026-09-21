# -*- coding: utf-8 -*-
"""建立数据层：把散在生成脚本里的数据抽成 JSON。
内容模型：平台(platform) / 模型(model) / 评测项(dimension) / 数据点(entry)
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "data")
os.makedirs(D, exist_ok=True)


def w(name, obj):
    p = os.path.join(D, name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"  data/{name:<26} {os.path.getsize(p):>7} B")


# ── 站点元数据 ────────────────────────────────────────────────
w("site.json", {
    "brand": "CALIBER",
    "brandCn": "统一口径基准",
    "studio": "HELIX AI Studio",
    "tagline": "AI 平台与模型 · 用同一把尺子横量",
    "positions": "把 AI 平台放在同一把尺子上",
    "intro": "各平台用自己的积分币计价，币值互不相同。CALIBER 先把它们压平到同一口径，"
             "再折算成可比较的现金成本与能力得分 — 不采信宣传数字，只给可复核的结果。",
    "owner": "HELIX AI Studio",
    "year": "2026",
    "nav": [
        {"key": "home", "label": "首页", "href": "index.html"},
        {"key": "cost", "label": "平台成本对比", "href": "cost.html"},
        {"key": "leaderboard-vlm", "label": "视觉理解模型排行榜", "href": "leaderboard-vlm.html"}
    ]
})

# ── 平台元数据（一处定义，全站引用） ──────────────────────────
w("platforms.json", {
    "libtv": {"name": "libtv", "cn": "libtv", "color": "#9CE6F3", "currency": "CNY", "region": "cn"},
    "Neowow": {"name": "Neowow", "cn": "Neowow", "color": "#00C65A", "currency": "CNY", "region": "cn"},
    "即梦": {"name": "即梦", "cn": "即梦", "color": "#3280FF", "currency": "CNY", "region": "cn"},
    "小云雀": {"name": "小云雀", "cn": "小云雀", "color": "#FABC00", "currency": "CNY", "region": "cn"},
    "Higgsfield": {"name": "Higgsfield", "cn": "Higgsfield", "color": "#ED1572",
                   "currency": "USD", "region": "global", "excludeTax": True}
})

# ── 成本数据集 ────────────────────────────────────────────────
w("cost-seedance25.json", {
    "id": "cost-seedance25",
    "type": "cost",
    "title": "平台成本对比",
    "eyebrow": "Cost Benchmark · Seedance 2.5",
    "updatedAt": "2026-09-21",
    "spec": "Seedance 2.5 · 720p · 16:9 · 30s · 全能参考",
    "specNote": "全部平台的单条积分消耗均在此口径下测得，是本次对比成立的唯一前提。",
    "fx": {"pair": "USD_CNY", "rate": 6.7487, "asOf": "2026-09-21",
           "source": "中国外汇交易中心（CFETS）人民币对美元中间价",
           "note": "选用中间价而非银行牌价：中间价是当日官方定价，可引用可复核；"
                   "实际结算按各银行现汇卖出价通常再高 0.5–1%。"},

    # 单条消耗积分（生成页实测）
    "creditsPerVideo": {"Neowow": 7500, "libtv": 1380, "即梦": 600, "小云雀": 600, "Higgsfield": 210},
    "creditsSource": {
        "Neowow": "Seedance 2.5 · 720p · 16:9 · 30s · 全能参考 · 分镜栏编辑",
        "libtv": "Seedance 2.5 · 全能参考 · 16:9 · 720P · 30s",
        "即梦": "即梦 Seedance 2.5 · 16:9 · 720P · 全能参考 · 30s",
        "小云雀": "Seedance 2.5 · 16:9 · 720P · 30s → 600 积分（用户已确认）",
        "Higgsfield": "Model: Seedance 2.5 · 30s · 16:9 · 720p · Bitrate Standard"
    },

    # 平台自行公示的兑换率（仅用于反向校验归一化口径）
    "officialRate": {
        "Neowow": {"PLUS": 180.0, "Pro": 282.0, "MAX": 350.0, "ULTRA": 371.0},
        "即梦": {"基础会员": 13.0, "标准会员": 14.0},
        "libtv": {"标准版": 31.25, "进阶版": 45.45},
        "小云雀": {"基础会员": 21.9, "标准会员": 23.2, "高级会员": 28.8, "超级会员": 30.0}
    },

    # 海报宣传「低至 X 元/秒」
    "adClaim": {
        "libtv": {"tier": "至尊版", "perSec": 0.36},
        "Neowow": {"tier": "ULTRA", "perSec": 0.26},
        "即梦": {"tier": "超级会员", "perSec": 0.40},
        "小云雀": {"tier": "超级会员", "perSec": 0.40}
    },

    # 档位清单（原价 = 划线原价 / 次年续费全额 / Higgsfield 月付×12）
    "plans": [
        {"platform": "libtv", "tier": "标准版", "price": 569, "renewal": 759, "currency": "CNY",
         "monthlyCredits": 1500, "original": 729, "originalNote": "划线原价"},
        {"platform": "libtv", "tier": "进阶版", "price": 1199, "renewal": 1799, "currency": "CNY",
         "monthlyCredits": 4600, "original": 2199, "originalNote": "划线原价"},
        {"platform": "libtv", "tier": "高级版", "price": 3899, "currency": "CNY",
         "monthlyCredits": 16300, "renewal": 5099, "original": 7399, "originalNote": "划线原价",
         "creditsOptions": [
             {"monthlyCredits": 11700, "price": 2999, "label": "11.7K 档"},
             {"monthlyCredits": 16300, "price": 3899, "label": "16.3K 档"}
         ]},
        {"platform": "libtv", "tier": "豪华版", "price": 6699, "renewal": 7399, "currency": "CNY",
         "monthlyCredits": 32800, "original": 14999, "originalNote": "划线原价"},
        {"platform": "libtv", "tier": "至尊版", "price": 9599, "renewal": 9599, "currency": "CNY",
         "monthlyCredits": 50500, "original": 22999, "originalNote": "划线原价"},
        {"platform": "Neowow", "tier": "PLUS", "price": 599, "currency": "CNY",
         "monthlyCredits": 9000, "original": 1080, "originalNote": "划线原价"},
        {"platform": "Neowow", "tier": "Pro", "price": 4666, "currency": "CNY",
         "monthlyCredits": 108000, "original": 12950, "originalNote": "划线原价",
         "creditsOptions": [
             {"monthlyCredits": 32800, "price": 1599, "label": "3.28W 档"},
             {"monthlyCredits": 52800, "price": 2289, "label": "5.28W 档"},
             {"monthlyCredits": 108000, "price": 4666, "label": "10.8W 档"}
         ]},
        {"platform": "Neowow", "tier": "MAX", "price": 11059, "currency": "CNY",
         "monthlyCredits": 288000, "original": 34560, "originalNote": "划线原价",
         "creditsOptions": [
             {"monthlyCredits": 188000, "price": 7299, "label": "18.8W 档"},
             {"monthlyCredits": 288000, "price": 11059, "label": "28.8W 档"}
         ]},
        {"platform": "Neowow", "tier": "ULTRA", "price": 11899, "currency": "CNY",
         "monthlyCredits": 368000, "original": 44160, "originalNote": "划线原价"},
        {"platform": "即梦", "tier": "基础会员", "price": 659, "currency": "CNY",
         "monthlyCredits": 725, "original": None, "originalNote": "页面未公示"},
        {"platform": "即梦", "tier": "标准会员", "price": 1899, "currency": "CNY",
         "monthlyCredits": 2210, "original": None, "originalNote": "页面未公示"},
        {"platform": "即梦", "tier": "高级会员", "price": 5199, "currency": "CNY",
         "monthlyCredits": 12320, "original": 10398, "originalNote": "次年续费全额",
         "creditsOptions": [
             {"monthlyCredits": 6200, "price": 2599, "label": "6.2K 档"},
             {"monthlyCredits": 12320, "price": 5199, "label": "12.3K 档"},
             {"monthlyCredits": 18500, "price": 7799, "label": "18.5K 档"},
             {"monthlyCredits": 27700, "price": 11699, "label": "27.7K 档"}
         ]},
        {"platform": "即梦", "tier": "超级会员", "price": 21840, "currency": "CNY",
         "monthlyCredits": 54600, "original": 43680, "originalNote": "次年续费全额",
         "creditsOptionsNote": "页面未见联动积分档，按单档计。"},
        {"platform": "小云雀", "tier": "基础会员", "price": 453, "currency": "CNY",
         "monthlyCredits": 830, "original": 759, "originalNote": "划线原价"},
        {"platform": "小云雀", "tier": "标准会员", "price": 1199, "currency": "CNY",
         "monthlyCredits": 2320, "original": 1999, "originalNote": "划线原价"},
        {"platform": "小云雀", "tier": "高级会员", "price": 4999, "currency": "CNY",
         "monthlyCredits": 12000, "original": 9999, "originalNote": "划线原价",
         "creditsOptions": [
             {"monthlyCredits": 6300, "price": 2649, "label": "6.3K 档"},
             {"monthlyCredits": 8600, "price": 3599, "label": "8.6K 档"},
             {"monthlyCredits": 10200, "price": 4199, "label": "10.2K 档"},
             {"monthlyCredits": 12000, "price": 4999, "label": "12K 档"},
             {"monthlyCredits": 18500, "price": 7799, "label": "18.5K 档"},
             {"monthlyCredits": 27700, "price": 10699, "label": "27.7K 档"}
         ]},
        {"platform": "小云雀", "tier": "超级会员", "price": 21840, "currency": "CNY",
         "monthlyCredits": 54600, "original": 43680, "originalNote": "划线原价"},
        {"platform": "Higgsfield", "tier": "Starter", "price": 180, "currency": "USD",
         "monthlyCredits": 200, "original": 180, "originalNote": "年付无折扣"},
        {"platform": "Higgsfield", "tier": "Plus", "price": 468, "currency": "USD",
         "monthlyCredits": 1000, "original": 588, "originalNote": "月付×12"},
        {"platform": "Higgsfield", "tier": "Ultra", "price": 1188, "currency": "USD",
         "monthlyCredits": 3000, "original": 1548, "originalNote": "月付×12",
         "creditsOptions": [
             {"monthlyCredits": 3000, "price": 1188, "label": "$99/月档"},
             {"monthlyCredits": 6000, "price": 2328, "label": "$194/月档"},
             {"monthlyCredits": 9000, "price": 3240, "label": "$270/月档"}
         ],
         "creditsOptionsNote": "价格为「按月付折年付」口径的月费×12；原价按各档月付价×12 计。"}
    ],

    # 待补数据清单（价格未知的积分档与平台，补齐后自动进入计算）
    "pending": [
        {"item": "五家的失败重试是否扣积分",
         "why": "影响最大：失败率 20% 且不退分 = 实际成本 +25%，足以反转全部排名"},
        {"item": "Higgsfield Pro（600–900）与 Max（1,800–5,400）滑块各档价格",
         "why": "Ultra 三档已录入；Pro/Max 仍仅知起步价 $23 / $59"},
        {"item": "Neowow ULTRA 是否有联动积分档",
         "why": "Pro（3 档）与 MAX（2 档）已确认联动，ULTRA 当前按固定 368,000/月"},
        {"item": "libtv 至尊版是否也有联动积分档",
         "why": "高级版已确认双档，其余四档按当前所见为固定值"},
        {"item": "即梦基础/标准 与 小云雀 的次年续费价",
         "why": "用户暂不提供，暂用划线原价代替；影响跨年使用的真实成本估算"}
    ],

    # 数据来源截图
    "sources": [
        {"page": "Neowow 生成页", "data": "Seedance 2.5 / 720p / 16:9 / 30s / 全能参考 → 7,500 积分"},
        {"page": "libtv 生成页", "data": "Seedance 2.5 / 全能参考 / 16:9 · 720P · 30s → 1,380 积分"},
        {"page": "即梦生成页", "data": "即梦 Seedance 2.5 / 16:9 / 720P / 全能参考 / 30s → 600 积分"},
        {"page": "libtv 订阅页", "data": "标准/进阶/高级/豪华/至尊 五档年费 + 划线原价 + 兑换率"},
        {"page": "Neowow 订阅页", "data": "PLUS/Pro/MAX/ULTRA 四档年费 + 划线原价 + 1元=X积分"},
        {"page": "即梦订阅页", "data": "基础/标准/高级/超级 四档年费 + 首年5折与次年全额"},
        {"page": "小云雀 订阅页", "data": "基础 ¥453 / 标准 ¥1,199 / 高级 ¥4,999 / 超级 ¥21,840（含划线原价）"},
        {"page": "小云雀 生成页", "data": "Seedance 2.5 / 16:9 / 720P / 30s → 界面显示 600（用户口径 800）"},
        {"page": "Higgsfield 订阅页", "data": "Starter $15 / Plus $39 / Ultra $99（月付折年付口径）"},
        {"page": "Higgsfield 生成页", "data": "Model: Seedance 2.5 / 30s / 16:9 / 720p / Bitrate Standard → 210 积分"}
    ],

    # 风险与待核实项（页面用折叠块呈现）
    "risks": [
        {"level": "high", "title": "小云雀与即梦的超级会员完全同规格，二者已无法区分",
         "body": ["用户确认小云雀单条为 600 积分。据此，小云雀超级与即梦超级在全部关键维度上一致："
                  "同为 ¥21,840 首年 / ¥43,680 次年、同为 54,600 积分/月、同为 ¥1 = 30 积分、"
                  "同为 600 积分/条 —— 折算后单条成本完全相同（¥20.00）。",
                  "两家均为字节系、同用 Seedance 全家桶。本表按同规格分别列出，"
                  "但实际采购时二者可视为同一档位，差异只在非价格能力（工作流、API、客服）。",
                  "另需注意：即梦超级会员的积分由 54,000 更正为 54,600 —— "
                  "依据是 21,840 ÷ (54,600 × 12) = 1/30，与页面标注的「¥1 = 30 积分」精确吻合。"]},
        {"level": "warn", "title": "即梦高级会员另有 6.2K / 18.5K / 27.7K 三档积分未计入",
         "body": ["页面对高级会员提供 6.2K / 12.3K / 18.5K / 27.7K 四档积分可选，本表仅录入 12.3K 档（¥5,199）。",
                  "低档位单价通常更差、高档位更优，因此「15–20 条/月最省」这一区间结论可能随档位价格变化。"
                  "其余三档价格待补后重算。"]},
        {"level": "warn", "title": "年费档位均为限时活动价，恢复原价后结论会变",
         "body": ["按官方原价重算，Neowow ULTRA 单条成本由 ¥20.21 升至 ¥75.00，全场最优解变为即梦超级会员（¥40.44/条）。",
                  "libtv 高级版截图同时出现 11,700 与 16,300 两个积分值，本表按 16,300 计算；"
                  "若实际为 11,700，其单条成本将由 ¥27.51 升至 ¥38.34。"]},
        {"level": "warn", "title": "Higgsfield 的税务与跨境结算成本未计入",
         "body": ["页面明示报价不含 VAT 与地方税；跨境支付按现汇卖出价结算（高于中间价约 0.5–1%）"
                  "并可能叠加境外交易手续费。综合实际成本比本表高约 6–10%，即 Ultra 实际约 ¥50.51/条。",
                  "另注意：Higgsfield 积分月底清零、不结转；年付为一次性全额扣款且默认自动续订。"]},
        {"level": "high", "title": "失败重试是否扣积分 —— 隐性成本影响最大",
         "body": ["本次按「成功出片才扣分」的理想情况计算。若某平台失败率 20% 且不退积分，"
                  "其实际单条成本需上浮 25%，足以反转排名。这是唯一可能推翻全部结论的变量，务必实测。"]},
        {"level": "", "title": "其余未纳入的变量",
         "body": ["并发数与排队优先级、素材上传与存储配额、商用授权与版权归属、"
                  "分镜栏编辑等是否为付费加项、积分是否跨月结转。",
                  "另据公开反馈，小云雀无官方客服渠道，积分返还与权益咨询无反馈路径 —— 不进单价，但会吃掉实际收益。"]}
    ]
})

# ── 排行榜数据集骨架（先把字段定死，有数据后只填 entries） ────
w("leaderboard-vlm.json", {
    "id": "leaderboard-vlm",
    "type": "leaderboard",
    "title": "视觉理解模型排行榜",
    "eyebrow": "Vision-Language Benchmark",
    "status": "coming-soon",
    "updatedAt": None,
    "intro": "同一套口径下横向评测各模型的视觉理解能力，输出可复核的排名与置信区间。",
    "emptyState": {
        "title": "评测进行中",
        "body": "评测集与打分脚本已就位，数据回填后本节将自动渲染为排行榜。字段结构已锁定，"
                "后续只需向 entries 追加记录，无需改动页面。"
    },
    "methodology": {
        "scoring": "每维度 0–100 分，按权重加权为总分；每项至少 5 次独立运行取中位数，报 95% 置信区间。",
        "dimensions": [
            {"key": "chart", "label": "图表识别", "weight": 0.30,
             "desc": "柱/折/饼/散点图的数值读取与趋势判断，含刻度反推"},
            {"key": "ocr", "label": "OCR 文字提取", "weight": 0.25,
             "desc": "截图、扫描件、手写体、低对比度与小字号文字的准确率"},
            {"key": "spatial", "label": "空间推理", "weight": 0.25,
             "desc": "相对位置、遮挡关系、计数与方位判断"},
            {"key": "longdoc", "label": "长图细节", "weight": 0.20,
             "desc": "超长截图与多栏排版中的信息定位与跨区关联"}
        ]
    },
    "fieldSchema": {
        "entries[]": {
            "rank": "integer — 由 score 降序自动生成，不必手填",
            "model": "string — 模型名，如 'GPT-6'",
            "variant": "string|null — 变体标记，如 'High' / 'Thinking'",
            "provider": "string — 供应方，如 'OpenAI'",
            "license": "string — 'proprietary' | 'open'",
            "score": "number — 加权总分 0–100",
            "ci": "number — 95% 置信区间半宽",
            "dims": "object — {chart, ocr, spatial, longdoc} 各维度得分",
            "runs": "integer — 独立运行次数",
            "evaluatedAt": "string — YYYY-MM-DD",
            "note": "string|null — 备注",
            "source": "string|null — 数据来源说明"
        }
    },
    "models": [],
    "entries": []
})

print("\n数据层已建立。内容模型：平台 / 模型 / 评测项 / 数据点")

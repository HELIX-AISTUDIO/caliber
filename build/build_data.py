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
  4. 价格一律取页面【显示的实付价】，不录划线原价 —— 见下方 PRICE_RULE。
     唯一例外是续费价 renewal，它是真实会发生的第二期扣款。

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
        {"key": "cycles", "label": "三周期全清单", "href": "cycles.html"},
        {"key": "leaderboard-vlm", "label": "视觉理解模型排行榜", "href": "leaderboard-vlm.html"},
    ],
}

# ═══════════ 平台 ═══════════
PLATFORMS = {
    "libtv":      {"name": "libtv",      "color": "#9CE6F3", "currency": "CNY", "region": "cn",
                   "recurring": True, "tierLabel": "标准/进阶/高级/豪华/至尊"},
    "Neowow":     {"name": "Neowow",     "color": "#00C65A", "currency": "CNY", "region": "cn",
                   "recurring": False, "tierLabel": "PLUS/Pro/MAX/ULTRA"},
    "即梦":        {"name": "即梦",        "color": "#3280FF", "currency": "CNY", "region": "cn",
                   "recurring": True, "tierLabel": "基础/标准/高级/超级"},
    "小云雀":      {"name": "小云雀",      "color": "#FABC00", "currency": "CNY", "region": "cn",
                   "recurring": True, "tierLabel": "基础/标准/高级/超级"},
    "Higgsfield": {"name": "Higgsfield", "color": "#ED1572", "currency": "USD", "region": "global",
                   "excludeTax": True, "recurring": False, "quarterly": False,
                   "tierLabel": "Starter/Plus/Ultra"},
    "Tapnow":     {"name": "Tapnow",     "color": "#A78BFA", "currency": "USD", "region": "global",
                   "recurring": True, "tierLabel": "BASIC/PRO/ULTIMATE/MAX"},
}

# ═══════════ 汇率 ═══════════
FX = {"pair": "USD_CNY", "rate": 6.7487, "asOf": UPDATED,
      "source": "中国外汇交易中心（CFETS）人民币对美元中间价",
      "note": "选用中间价而非银行牌价：中间价是当日官方定价，可引用可复核；"
              "实际结算按各银行现汇卖出价通常再高 0.5–1%。"}

# ═══════════ 统一口径 ═══════════
SPEC = {"text": "Seedance 2.5 · 720p · 16:9 · 30s · 全能参考", "secondsPerClip": 30,
        "note": "全部平台的单条积分消耗均在此口径下测得，是本次对比成立的唯一前提。"}

CREDITS_PER_VIDEO = {"libtv": 1380, "Neowow": 7500, "即梦": 600, "小云雀": 600,
                     "Higgsfield": 210, "Tapnow": 1200}

CREDITS_SOURCE = {
    "libtv":      "Seedance 2.5 · 全能参考 · 16:9 · 720P · 30s",
    "Neowow":     "Seedance 2.5 · 720p · 16:9 · 30s · 全能参考 · 分镜栏编辑",
    "即梦":        "即梦 Seedance 2.5 · 16:9 · 720P · 全能参考 · 30s",
    "小云雀":      "Seedance 2.5 · 16:9 · 720P · 30s（用户确认 600 积分）",
    "Higgsfield": "Model: Seedance 2.5 · 30s · 16:9 · 720p · Bitrate Standard",
    "Tapnow":     "Seedance 2.5 · 相同参数（用户口径）→ 1,200 积分",
}

# ═══════════ 档位清单 ═══════════
#   credits: [{"credits": 月积分, "price": 年付实付总额, "m": 月付实付总额,
#              "q": 季付实付总额, "renewal": 次年续费价, "mCr": 月付口径月积分}, ...]
#   五条约定：
#     1) renewal 放【选项级】—— libtv 的次年续费价随积分档变、不随档位变：
#        高级版 11.7K→¥3799 / 16.3K→¥5099；至尊版 50.5K→¥10999 / 66K→未公示。
#        曾放在档位级，导致 11.7K 档被套上 16.3K 档的 ¥5099（2026-09-21 截图纠正）。
#     2) 缺 q 键 = 该档无季付选项（目前只有 Higgsfield —— 平台不提供季付）。
#        缺 renewal 键 = 未公示续费价；非连续包（Neowow / Higgsfield）整体无此键。
#     3) m / q 一律取【稳态价】，即正常续买的单价。首期促销价不进数据。
#        例：Tapnow BASIC 首月 $9、次月起 $15，此处 m 记 15。
#     4) mCr 只在「该周期积分与年付不同」时出现。目前只有即梦标准会员：
#        月付给 4,000 积分/月，年付与季付给 2,210 —— 平台确实如此，不是抄错。
#        → 推论：积分不是档位的固有属性，每个周期各自抄卡片原文。
#     5) 划线原价一律不录（含选项级），依据见下方 PRICE_RULE。
PLANS = [
    {"platform": "libtv", "tier": "标准版",
     "credits": [{"credits": 1500, "price": 569, "m": 66, "q": 179, "renewal": 569}]},
    {"platform": "libtv", "tier": "进阶版",
     "credits": [{"credits": 4600, "price": 1199, "m": 199, "q": 499, "renewal": 1199}]},
    {"platform": "libtv", "tier": "高级版",
     "credits": [{"credits": 11700, "price": 2999, "m": 469, "q": 1159, "renewal": 3799},
                 {"credits": 16300, "price": 3899, "m": 649, "q": 1599, "renewal": 5099}]},
    {"platform": "libtv", "tier": "豪华版",
     "credits": [{"credits": 32800, "price": 6699, "m": 1199, "q": 2699, "renewal": 7399}]},
    {"platform": "libtv", "tier": "至尊版",
     "credits": [{"credits": 50500, "price": 9599, "m": 1799, "q": 3899, "renewal": 10999},
                 {"credits": 66000, "price": 12499, "m": 2299, "q": 4999}]},  # 66K 未标次年价

    {"platform": "Neowow", "tier": "PLUS",
     "credits": [{"credits": 9000, "price": 599, "m": 60, "q": 189}]},
    {"platform": "Neowow", "tier": "Pro",
     "credits": [{"credits": 32800, "price": 1599, "m": 219, "q": 628},
                 {"credits": 52800, "price": 2289, "m": 348, "q": 899},
                 {"credits": 108000, "price": 4666, "m": 718, "q": 1999}]},
    {"platform": "Neowow", "tier": "MAX",
     "credits": [{"credits": 188000, "price": 7299, "m": 1199, "q": 2999},
                 {"credits": 288000, "price": 11059, "m": 1827, "q": 4599}]},
    {"platform": "Neowow", "tier": "ULTRA",
     "credits": [{"credits": 368000, "price": 11899, "m": 2296, "q": 5520}]},

    {"platform": "即梦", "tier": "基础会员",
     "credits": [{"credits": 725, "price": 659, "m": 69, "q": 188}]},
    # 即梦标准会员：月付给 4,000 积分/月，年付与季付给 2,210 —— 见上方约定 4)
    {"platform": "即梦", "tier": "标准会员",
     "credits": [{"credits": 2210, "price": 1899, "m": 199, "q": 568, "mCr": 4000}]},
    {"platform": "即梦", "tier": "高级会员",
     # 积分以卡片「◆ X 积分每月」原文为准。滑块标签（6.2K / 18.5K / 27.7K）是约数，
     # 真实值为 6,160 / 12,320 / 18,480 / 27,720 —— 曾按标签误录 6,200 / 18,500 / 27,700。
     # 交叉验证：四档「¥1=X 积分」标牌同为 28，只有真实值能同时成立（约数会给出 29/28/28）。
     "credits": [{"credits": 6160, "price": 2599, "m": 499, "q": 1399},
                 {"credits": 12320, "price": 5199, "m": 998, "q": 1959},
                 {"credits": 18480, "price": 7799, "m": 1498, "q": 2939},
                 {"credits": 27720, "price": 11699, "m": 2246, "q": 4409}]},
    {"platform": "即梦", "tier": "超级会员",
     "credits": [{"credits": 54600, "price": 21840, "m": 4299, "q": 8189}]},

    {"platform": "小云雀", "tier": "基础会员",
     "credits": [{"credits": 830, "price": 453, "m": 38, "q": 219}]},
    {"platform": "小云雀", "tier": "标准会员",
     "credits": [{"credits": 2320, "price": 1199, "m": 100, "q": 589}]},
    {"platform": "小云雀", "tier": "高级会员",
     # 10.2K 档：4199/12/10150 → ¥10 = 290.07，与卡片标注吻合；曾误录 10200（反推 291.5 ✗）
     # 27.7K 档：真实积分 27,720（滑块标签 27.7K 是约数），曾误录 27,700；用户 2026-09-21 裁定更正
     # 18.5K 档仍为 18500 —— 该值与 6.3K/8.6K/12K 一样来自滑块标签，尚未取得卡片原文核对
     "credits": [{"credits": 6300, "price": 2649, "m": 273, "q": 1488},
                 {"credits": 8600, "price": 3599, "m": 374, "q": 1999},
                 {"credits": 10150, "price": 4199, "m": 441, "q": 2349},
                 {"credits": 12000, "price": 4999, "m": 519, "q": 1959},
                 {"credits": 18500, "price": 7799, "m": 779, "q": 2939},
                 {"credits": 27720, "price": 10699, "m": 1168, "q": 4408}]},
    {"platform": "小云雀", "tier": "超级会员",
     "credits": [{"credits": 54600, "price": 21840, "m": 2235, "q": 8189}]},

    # Higgsfield 平台不提供季付，故全部缺 q 键
    {"platform": "Higgsfield", "tier": "Starter",
     "credits": [{"credits": 200, "price": 180, "m": 15}]},
    {"platform": "Higgsfield", "tier": "Plus",
     "credits": [{"credits": 1000, "price": 468, "m": 49}]},
    {"platform": "Higgsfield", "tier": "Ultra",
     "credits": [{"credits": 3000, "price": 1188, "m": 129},
                 {"credits": 6000, "price": 2328, "m": 220},
                 {"credits": 9000, "price": 3240, "m": 310}]},

    # ── Tapnow（USD 计价）──
    # BASIC 月付取稳态价 $15（首月 $9 为促销，按用户裁定不入数据）
    {"platform": "Tapnow", "tier": "BASIC", "credits": [
        {"credits": 1500, "price": 90, "m": 15, "q": 27}]},
    {"platform": "Tapnow", "tier": "PRO", "credits": [
        {"credits": 3500,  "price": 315,  "m": 30,  "q": 84},
        {"credits": 6000,  "price": 540,  "m": 51,  "q": 144},
        {"credits": 9500,  "price": 855,  "m": 81,  "q": 228},
        {"credits": 11500, "price": 1035, "m": 98,  "q": 276},
        {"credits": 20000, "price": 1800, "m": 170, "q": 480}]},
    {"platform": "Tapnow", "tier": "ULTIMATE", "credits": [
        {"credits": 36000, "price": 2592, "m": 306, "q": 756}]},
    {"platform": "Tapnow", "tier": "MAX", "credits": [
        {"credits": 72000,  "price": 5184, "m": 612, "q": 1512},
        {"credits": 100000, "price": 7200, "m": 850, "q": 2100}]},
]

# ═══════════ 平台公示兑换率（仅作口径反向校验）═══════════
OFFICIAL_RATE = {
    "libtv":  {"标准版": 31.25, "进阶版": 45.45},
    "Neowow": {"PLUS": 180.0, "Pro": 282.0, "MAX": 350.0, "ULTRA": 371.0},
    "即梦":    {"基础会员": 13.0, "标准会员": 14.0},
    "小云雀":  {"基础会员": 21.9, "标准会员": 23.2, "高级会员": 28.8, "超级会员": 30.0},
}
# ── 订阅机制：连续包（自动续费）vs 非连续包（一次性，到期结束）──
# 这是价格之外的一个独立维度，且带真实风险：
#   连续包 → 到期自动扣款；续费价通常高于首期价；忘记取消 = 按高价再买一期
#   非连续包 → 到期自动结束，无自动扣款、无续费价；首期价即全部成本
# 因此折年规则必须分开：
#   连续包：年均 = (首期 + 续费 x (期数-1)) / 期数
#   非连续包：年均 = 首期价（不折算）
RECURRING_NOTE = ("连续包年/包季/包月到期会自动扣款续费，且续费价通常高于首期价 —— "
                  "其真实成本须按「首期 + 续费 × (期数−1)」折算，并存在「忘记取消」的实际风险。"
                  "非连续包（Higgsfield、Neowow）为一次性购买，到期自动结束、无自动扣款、无续费价，"
                  "首期价即为全部成本。故本表横向比较时按「你打算用多久」分流："
                  "连续包要看续费后的均价，非连续包只看一口价。")

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

# ── 价格录入铁律（用户 2026-09-21 裁定，优先级最高）──────────────────
# 只取平台上【显示出来的实付价格】，忽略页面上的全部活动文字：
#   忽略：划线原价、折扣徽标（限时5折 / 6.4折 / 77折）、买年卡立省、活动倒计时、赠品与赠送月数
#   理由：显示价格本身已经把活动算进去了；再叠一层活动分析等于重复计算，还引入主观判断。
#   正面副作用：录入字段从「显示价 + 划线价」减为「只显示价」，出错面减半。
# 唯一例外：续费价 —— 它是【真实会发生的第二期扣款】，属价格而非宣传，必须记录。
PRICE_RULE = ("本表全部价格均为平台页面【显示出来的实付价】，已含当期全部活动；"
              "不引用、不分析任何划线原价、折扣徽标、立省百分比与赠品文字。"
              "唯一例外是续费价 —— 它是真实会发生的第二期扣款，属价格而非宣传，有公示则记录。")

# ── 时效声明（用户 2026-09-21 要求挂到页面显眼处）────────────────
LIVE_NOTE = ("本表全部价格锚定各平台官网【当前实时显示价】。该显示价本身已是活动价 / 优惠价 / "
             "限时价的最终成交价 —— 不再叠加、不再推算、不引用划线原价。"
             "价格随时可能变动；一经发现变化，我们第一时间更正，并同步更新本页的数据时点。")

# ═══════════ 数据范围 ═══════════
# 明确「本表结论覆盖到哪里」——否则「最省」容易被误读为全平台最优。
SCOPE = {
    "current": "年费 / 季付 / 月付 三周期",
    "currentShort": "年付 · 季付 · 月付",
    "impact": "三周期的承诺期不同，单价不能混着读：年付最省但锁 12 个月，月付最贵但随时能停。"
              "另有 11 个档位出现「承诺更久反而更贵」的倒挂（详见「用多久，买哪个周期」一节）。",
    "promoRule": "各平台页面常挂「限时活动福利」（某模型限时折扣、无限用 N 天、赠送积分等）。"
                 "本表统一不单独处置 —— 页面显示的实付价已含当期全部活动，"
                 "再叠一层活动分析等于重复计算，还引入主观判断。唯一例外是续费价，"
                 "它是有公示的第二期真实扣款，属价格而非宣传。",
    "items": [
        {"label": "年费 / 连续包年", "status": "已覆盖", "done": True,
         "note": "全部 44 个可选积分档"},
        {"label": "季度会员", "status": "已覆盖", "done": True,
         "note": "39 档有季付；Higgsfield 平台不提供季付"},
        {"label": "月度会员", "status": "已覆盖", "done": True,
         "note": "全部 44 档；Tapnow BASIC 按月付稳态价计（首月促销不计入）"},
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
    {"plat": "Tapnow",     "retry": "不扣", "basis": "用户实测（与其他平台同口径）"},
]
RETRY_NOTE = ("各平台失败均不消耗积分（用户实测口径），故本表全部单价与实际计费一致，"
              "排名不受失败率影响，可直接按单价决策。Higgsfield 另有官方文档保证："
              "failed / nsfw 请求不计费，预扣积分自动退还，排队取消亦退，超时标记失败不扣费"
              "（唯一例外 Grok —— 一经开始生成即扣费）。")
CROSS_MIDNIGHT = ("跨零点提交时两家字节系平台的积分归属日不同：23:55 提交、0:05 完成时，"
                  "即梦计入前一天、小云雀计入后一天；小云雀若未在零点前完成，"
                  "未用完的当日积分会作废。")

# ═══════════ 风险（按用户答复收敛）═══════════
RISKS = [
    {"level": "warn", "title": "年费档位均为限时活动价，活动退坡后结论会变",
     "body": ["用户确认：各平台年费均为限时活动价。本表记录的是页面显示的实付价，"
              "已含当期全部活动；活动一旦结束或退坡，页面显示价上升、单条成本随之上升，"
              "排名可能变化。",
              "libtv 高级版与至尊版、即梦高级四档、小云雀高级六档、"
              "Neowow Pro 三档与 MAX 两档均为联动定价，活动结束后可能同步调整档位结构，"
              "届时选项数量与积分档位都可能变。",
              "六家中 Tapnow 的年价折让力度最大，活动退坡对其单条成本的影响也最大。"]},
]

# ═══════════ 数据来源 ═══════════
SOURCES = [
    {"page": "libtv 生成页",      "data": "Seedance 2.5 · 全能参考 · 16:9 · 720P · 30s → 1,380 积分"},
    {"page": "libtv 订阅页",      "data": "五档年费 + 次年续费价；高级版 11.7K/16.3K、至尊版 50.5K/66K 联动"},
    {"page": "Neowow 生成页",     "data": "Seedance 2.5 · 720p · 16:9 · 30s · 全能参考 → 7,500 积分"},
    {"page": "Neowow 订阅页",     "data": "四档年费；Pro 三档、MAX 两档联动；ULTRA 无联动"},
    {"page": "即梦生成页",        "data": "即梦 Seedance 2.5 · 16:9 · 720P · 全能参考 · 30s → 600 积分"},
    {"page": "即梦订阅页",        "data": "四档年费；高级会员 6.2K–27.7K 四档联动；超级会员单档"},
    {"page": "小云雀生成页",      "data": "Seedance 2.5 · 16:9 · 720P · 30s → 600 积分（用户确认）"},
    {"page": "小云雀 订阅页",      "data": "四档年费；高级会员 6.3K–27.7K 六档联动"},
    {"page": "Higgsfield 订阅页", "data": "Starter $15 / Plus $39 / Ultra $99；Ultra 为 3,000–9,000 分三档滑块"},
    {"page": "Higgsfield 生成页", "data": "Model: Seedance 2.5 · 30s · 16:9 · 720p · Bitrate Standard → 210 积分"},
    {"page": "Tapnow 订阅页", "data": "USD 计价。BASIC $90/年 1,500 分；"
                                       "PRO 五档滑动 $315/540/855/1035/1800（3.5K–20K 分）；"
                                       "ULTIMATE $2592/年 36,000 分；MAX 两档 $5184/7200（72K / 100K 分）"},
    {"page": "Tapnow 生成页", "data": "Seedance 2.5 · 相同参数 → 1,200 积分（用户口径）"},
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
    "priceRule": PRICE_RULE,
    "liveNote": LIVE_NOTE,
    "recurringNote": RECURRING_NOTE,
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
    # 不再写死平台数：以档位表里实际出现的平台为准
    assert len(PLATFORMS) == len({p['platform'] for p in PLANS}), \
        'PLATFORMS 与 PLANS 中的平台不一致'
    n_opt = 0
    for p in PLANS:
        assert p["credits"], "%s %s 无积分选项" % (p["platform"], p["tier"])
        assert p["platform"] in PLATFORMS, "未知平台 " + p["platform"]
        for c in p["credits"]:
            assert set(c) >= {"credits", "price"}, "%s %s 选项缺键" % (p["platform"], p["tier"])
            assert c["price"] is not None and c["credits"] > 0
            assert "original" not in c, \
                "%s %s 选项含划线原价，违反 PRICE_RULE" % (p["platform"], p["tier"])
            n_opt += 1
            # 三周期：月付必填；季付可有可无，但同一平台必须一致
            assert c.get("m") is not None, \
                "%s %s %s 档缺月付价 m" % (p["platform"], p["tier"], format(c["credits"], ","))
            assert ("q" in c) == PLATFORMS[p["platform"]].get("quarterly", True), \
                "%s %s 的季付键与平台 quarterly 标志不符" % (p["platform"], p["tier"])
            # 续费价校验：只有连续包才该有；且次年续费不应低于首期
            if c.get("renewal") is not None:
                assert PLATFORMS[p["platform"]]["recurring"], \
                    "%s 是非连续包，不应有续费价" % p["platform"]
                assert c["renewal"] >= c["price"], \
                    "%s %s %s 档：次年续费 %s 低于首期 %s，需复核" % (
                        p["platform"], p["tier"], format(c["credits"], ","),
                        c["renewal"], c["price"])
        assert "original" not in p, \
            "%s %s 含划线原价，违反 PRICE_RULE" % (p["platform"], p["tier"])
    print("\n数据层已建立：%d 平台 / %d 档位 / %d 个可选积分档" % (len(PLATFORMS), len(PLANS), n_opt))


if __name__ == "__main__":
    main()

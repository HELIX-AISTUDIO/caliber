# 画布平台 · Seedance 2.5 出片成本与性价比对比

统一测试口径：**Seedance 2.5 · 720p · 16:9 · 30s · 全能参考**

对比平台：libtv / Neowow / 即梦 / 小云雀 / Higgsfield / Tapnow（**6 个平台 · 24 个档位 · 44 个可选积分档**）

---

## 这是什么

把五个画布平台的会员档位，折算成**同一条 30 秒视频的现金成本**，然后回答三个问题：

1. 每一档到底多少钱一条？
2. 按我的月产量，哪一档最省钱？
3. 这些平台的「便宜」是真规模效应，还是活动折扣撑起来的？

## 输出内容

| 章节 | 内容 |
|---|---|
| 计算口径 | 归一化链条 + 用平台自身公示兑换率做的交叉校验（最大偏差 1.55%） |
| 全档位主表 | 20 档，可按年费/单条成本/月产能排序，USD 档位已按汇率折算 |
| 单条成本排行 | 从 ¥20.21 到 ¥106.29 |
| 边际成本阶梯 | 每步升档值不值，标出各平台的「价格陷阱拐点」 |
| 达标总支出阶梯 | 按目标月产量反查最省档位（核心结论表） |
| 折扣结构透视 | 用官方原价重算，区分真实规模效应与折扣力度差异 |
| 海报 vs 到手价 | 各行「低至 X 元/秒」的注水倍数 |
| 五类风险 | 含税务、积分清零、失败扣分等未纳入项 |
| 原始数据附录 | 20 档位 + 5 条积分消耗 + 4 条海报价 + 10 张来源截图 |

## 核心结论

- **单条成本最优**：Neowow ULTRA ¥20.21，即梦超级会员 ¥20.22 —— 两家实质并列，且「元/秒」完全相同（¥0.674）。
- **「单条成本最省」≠「花钱最省」**：libtv 单价全线最贵，却占据三个产量区间的最省解，因为它档位切分最密、产能浪费最少。
- **海外平台没有成本优势**：Higgsfield 最优档 ¥46.77/条，是全场最优的 **2.31 倍**。
- **有些「规模经济」是假的**：Neowow 按原价四档单条成本全是 ¥75.00，价差 100% 来自折扣力度。只有即梦是真正的统一折扣结构。
- **产能断档比单价更决定最优解**：Higgsfield Plus 能赢下 3.68–4.76 条/月区间，是因为国内平台恰好在该产能段留了空档。

---

## 线上地址

**https://seedance-cost-benchmark.pages.dev**

托管于 Cloudflare Pages（Direct Upload）。2026-09-21 实测通过：

| 校验项 | 结果 |
|---|---|
| DNS | 172.66.44.147（Cloudflare 真实 IP） |
| 微信内置浏览器 UA | **HTTP 200** ✅ |
| Chrome UA | HTTP 200 ✅ |
| `X-Frame-Options` | `DENY` |
| `X-Robots-Tag` | `noindex, nofollow, noarchive, nosnippet, noimageindex, noai, noimageai` |
| `Content-Security-Policy` | `default-src 'none'` 起手，仅放行内联 style/script |
| `Referrer-Policy` / `X-Content-Type-Options` / `Permissions-Policy` | 均已下发 |

> `_headers` 在本托管上**由响应头实际下发**（非 `<meta>` 层面），因此 `frame-ancestors` 级别的防护也生效。

### 重新部署

改动 `index.html` 后，把 `deploy/` 目录（7 个文件）重新拖到该项目的 Deployments 页即可，链接不变。

---

## 部署要求（重要：微信内能否直开）

**本页若要发给别人在微信里点开，托管选择是决定性的。** 2026-09-21 实测各托管对「微信内置浏览器 UA」的响应：

| 托管 | 微信 UA 请求结果 | 微信内可直开 |
|---|---|---|
| **`*.app.workbuddy.host`（原托管）** | **HTTP 403 Forbidden** | ❌ 不可 |
| GitHub Pages（`*.github.io`） | HTTP 200 | ✅ 可 |
| Cloudflare Pages（`*.pages.dev`） | HTTP 200 | ✅ 可 |
| Netlify（`*.netlify.app`） | HTTP 200 | ✅ 可 |

### 结论

`workbuddy.host` **在服务端按 User-Agent 拦截所有含 `MicroMessenger` 的请求并直接返回 403**。这不是微信的域名黑名单，也不是需要备案的问题 —— 是托管方自己的策略。

因此：

- ❌ **前端改任何代码都无法绕过** —— 服务器根本没把 HTML 送出去，加「点右上角在浏览器打开」的引导遮罩同样看不到。
- ✅ **换到任一其他托管即可解决**，本页无需任何修改（页面本就是零外部依赖的单文件）。

### 推荐：Cloudflare Pages

理由有三：

1. 支持**直接拖拽文件夹上传**，不需要 git，不需要命令行，几分钟拿到 `*.pages.dev` 链接。
2. **不需要 ICP 备案**。
3. 本目录的 **`_headers` 会在 Cloudflare Pages 上真正生效** —— CSP、`X-Frame-Options`、`X-Robots-Tag: noai` 等响应头才会实际下发（GitHub Pages 会忽略 `_headers`，那些防护只停留在 `<meta>` 层面）。

若偏好 GitHub Pages：本目录已 `git init` 并提交完毕，建好空仓库后 `git push` 并在 Settings → Pages 开启即可。注意 `github.io` 在中国大陆网络下的连通性不稳定，建议先实测再对外分发。

---

## ⚠️ 价格时效性声明

本页所有会员年费与单条生成价格，**均取决于各平台当前的活动力度与限时优惠**，随活动周期、渠道与档位政策浮动，**仅代表 2026-09-21 采集时点的情况，不代表最终价格**。

请以下单时平台页面实际显示为准。

本作品的价值在于**方法**而非数字——归一化公式与阶梯算法在任何价格下都成立，把最新价格代入即可自行重算。

---

## 版权

版权所有 © 2026 HELIX AI Studio. **保留所有权利。**

溯源指纹：`HX-CLB-20260921-A215F0AB`

未经书面许可，**禁止**：复制或转载全文/部分内容、二次发布或镜像托管、商业使用、用于任何 AI 模型的训练或微调、移除版权声明与溯源指纹。
**允许**：转发原始链接、在注明作者与出处的前提下引用结论。

完整条款见 [LICENSE](./LICENSE)，保护措施及其技术边界见 [SECURITY.md](./SECURITY.md)。

---

## 技术说明

- **数据与页面分离**：所有内容来自 `data/*.json`，页面由 `build/build_site.py` 渲染。改数据不必碰模板。
- **单页零外部请求**：全站无 CDN、无外部字体、无统计脚本，CSS/JS 全内联。弱网与微信内都可秒开。
- **微信兼容**：适配 X5 内核（`backdrop-filter` 缺失时的 `@supports` 兜底、iOS 底部安全区、固定光晕合成层提升）。
- **移动端**：900 / 820 / 520px 三级断点，表格带横向滚动容器。
- **过渡动画**：`scroll-behavior:smooth` + 锚点 `scroll-margin-top` + IntersectionObserver 入场 + 子导航 scrollspy，全部有 `prefers-reduced-motion` 兜底。
- **打印友好**：`@media print` 浅色适配，存 PDF 时版权块与溯源指纹保留。

## 目录结构

```
index.html                 首页（构建产物）
cost.html                  平台成本对比（构建产物）
leaderboard-vlm.html       视觉理解模型排行榜（构建产物）
data/
  site.json                站点元数据：品牌、出品方、导航
  platforms.json           平台元数据：名称、颜色、币种、地区
  cost-seedance25.json     成本数据集：口径、汇率、单条积分、20 档位、风险项、来源
  leaderboard-vlm.json     排行榜数据集：维度权重、字段结构、entries
build/
  build_site.py            站点生成器（读 data/ → 输出三页 HTML）
  build_data.py            数据层初始化（可从零重建 data/*.json）
LICENSE                    版权许可条款
SECURITY.md                保护措施与技术边界说明
DESIGN.md                  设计系统（色板 / 字体 / 组件 / 多页面约定）
robots.txt                 反爬与反 AI 抓取指令
_headers                   Cloudflare Pages 安全响应头
.nojekyll                  GitHub Pages 用，禁 Jekyll 过滤
```

`deploy/` 为公网发布包（7 个文件，不含 `data/` 与 `build/`），由生成器自动产出。

## 内容模型

四个概念，全站统一：

| 概念 | 含义 | 存放位置 |
|---|---|---|
| **平台 platform** | libtv / Neowow / 即梦 / 小云雀 / Higgsfield / Tapnow | `data/platforms.json` |
| **模型 model** | 被评测的模型 | `data/leaderboard-*.json` 的 `models` |
| **评测项 dimension** | 评分维度与权重 | `data/leaderboard-*.json` 的 `methodology.dimensions` |
| **数据点 entry** | 一条可比较的记录 | 各数据集的 `plans` / `entries` |

## 价格录入铁律（PRICE_RULE）

定义在 `build/build_data.py` 的 `PRICE_RULE`，随 `cost["priceRule"]` 下发到页面「数据范围」一节。

> 本表全部价格均为平台页面【显示出来的实付价】，已含当期全部活动；不引用、不分析任何划线原价、折扣徽标、立省百分比与赠品文字。唯一例外是续费价 —— 它是真实会发生的第二期扣款，属价格而非宣传，有公示则记录。

落地约束：

- `PLANS` 里**禁止出现 `original` 字段**（档位级与选项级都不允许），`build_data.py` 会断言拦截。
- 因此站点**不计算、不展示折扣结构** —— 划线原价既已被判定为非价格，就不能拿它推导结论。
- 唯一保留的「第二期数字」是 `renewal`（次年续费价），用于按使用时长折算年均。
- 新增平台/档位时，只抄页面显示的实付价，不要抄旁边那串被划掉的数字。

## 周期结构（月付 / 季付 / 年付）

`PLANS[].credits[]` 每个选项带三个周期的实付总额：

| 键 | 含义 | 缺省行为 |
|---|---|---|
| `price` | 年付实付总额（主表基准） | 必填 |
| `m` | 月付实付总额（**稳态价**，首期促销不入） | 必填 |
| `q` | 季付实付总额 | 缺 = 该平台不提供季付（Higgsfield） |
| `mCr` | 月付口径的月积分 | 缺 = 同年付积分 |

三条约束由 `build_data.py` 断言拦截：非连续包不得有 `renewal`；次年续费不得低于首期；
`q` 键的存在必须与 `PLATFORMS[].quarterly` 一致。

**`mCr` 不是冗余字段** —— 即梦标准会员月付给 4,000 积分/月、年付与季付只给 2,210，
平台确实如此。推论：**积分不是档位的固有属性，每个周期各自抄卡片原文**。

站点渲染为 `#period`「用多久，买哪个周期」一节（`#calc` 之后、`#table` 之前）：
三周期各自的最优解并排 + 平台级周期折扣区间 + 周期倒挂全清单。
**刻意不做「季付榜」** —— 季付的最优解在月付榜里更便宜，三个独立榜会自相矛盾。

## 填写表读写：格式容错

`site/build/form_io.py` 是填写表的读取适配层。**所有脚本一律走 `read_table()`，不要直接 `csv.reader`。**

原因（2026-09-21 事故）：用 Excel/WPS 打开 `包月包季数据填写表.csv` 后保存，
Excel 会强制写成 XLSX 二进制而扩展名仍是 `.csv` —— 下游一律 `utf-8-sig` 读，全部崩。
数据没丢，但整条流水线断掉。

`read_table()` 按**魔数**判断真实格式（`PK\x03\x04` = ZIP/XLSX），是 CSV 就按 CSV 读，
是 XLSX 就解析 `xl/worksheets/sheet1.xml`。**格式不影响流水线。**

配套脚本：

| 脚本 | 用途 |
|---|---|
| `build/form_io.py` | 格式容错读写（CSV ⇄ XLSX） |
| `build/sync_form.py` | 用 CSV 重新生成 md 表格块，保证两份逐格一致 |
| `build/verify_form.py` | 填写表体检：缺口 / 季付溢价 / 与数据层积分一致性 / 备注违规词 / 三周期单调性 / 年付无优惠 |
| `build/preview_periods.py` | 生成 `周期结构核对.md`（数据入库前的结论预演，非站点交付物） |

## 页面结构（4 页）

| 页面 | 内容 | 导航项 |
|---|---|---|
| `index.html` | 首页：两条对比线入口 | 首页 |
| `cost.html` | 平台成本对比：左栏选项 + 全档位对比 / 先别急着下单两个视图 | 平台成本对比 |
| `cycles.html` | **三周期全清单 · 动态排名**：左栏选指标/周期/排序/平台，主区动态出排名条；下方是该页原有的 6 组原始数据与方法论 | 三周期全清单 |
| `leaderboard-vlm.html` | 视觉理解模型排行榜（待回填） | 视觉理解模型排行榜 |

> 原先「04 更多对比数据」整块嵌在成本页里，与成本页主表在语义上重复（都是成本数据），
> 且 6 组折叠表在长页里几乎没人展开。现已独立成页并重构为可交互的排名图 ——
> **成本页负责「看结论」，全清单页负责「查细节」**。

### 排名图的刻度（改前必读）

条长＝**相对最优倍数的平方根压缩**，不是数值比例：

```
rel = 越低越好的指标 → v / best；越高越好的指标 → best / v      （1 = 最优）
t   = sqrt((rel - 1) / (maxRel - 1))
条长 = (1 - t) × 100%
```

**为什么不用线性**：单条成本 19.30～21.10 的前 12 名只差 9%，线性刻度下条形几乎一样长
（实测 100% / 99.2% / 99.2%，肉眼无从分辨），而尾部 106.29 是 5.51 倍 —— 两者无法在同一线性刻度上同时看清。
平方根压缩后头部展开到 100%→86%，可分辨；尾部压到 0。

⚠ 服务端 `chart_rows()` 与前端 `renderChart()` 的刻度**必须完全一致**，
否则首屏（服务端渲染）与切换指标后（JS 重绘）的条长会不同 —— 已经踩过一次。

## 浏览器冒烟测试（强烈建议构建后跑）

```bash
# 需先指向托管 node 工作区的依赖（playwright-core）
NODE_PATH="<托管node>/workspace/node_modules" node build/smoke.js --shots
```

**为什么需要**：`build_site.py` 里的 12 项自检只能验证「能解析的东西」——
标签配对、列数、锚点、JS 语法、CSS 类是否被用到。而**已经发生过的线上问题全部是它抓不到的**：

| 事故 | 自检能否发现 |
|---|---|
| 周期按钮绿框不跟随（JS 选择器指向已改名的类，静默失效） | ✗ |
| 移动端侧栏吸顶挡住内容、控件被挤出视野 | ✗ |
| `buy` / `period` 视图横向溢出 775px（flex 交叉轴未 stretch） | ✗ |
| 手指停在表格上整页滑不动（`overscroll-behavior:contain` 吃掉手势） | ✗ |

这四类只有**真浏览器 + 真交互**能发现。冒烟测试覆盖桌面（1440×900）与手机（430×900）两档共 32 项，
包括：周期切换时按钮高亮/KPI/表格**三处必须同时跟随**、三个视图各自无横向溢出、
卡片区滚轮位移 > 100px、能滚到页底、抽屉开关、平台筛选、零 JS 报错。

失败时退出码为 1，可直接接进构建后钩子。依赖：`playwright-core` + 本机 Edge
（不下载浏览器，省几百 MB；`CALIBER_EDGE` 环境变量可覆盖浏览器路径）。

## 移动端结构（与桌面不同，改前先读）

| 控件 | 桌面 | 手机（≤1020px） |
|---|---|---|
| 全局导航 | 顶部横向菜单 | **汉堡菜单**（`#nBurger` / `#nDrop`） |
| 查看方式 | 左侧栏 | **内容区顶部横滚 tab**（`.tabs`，学 arena.ai：常驻可见优于藏起来） |
| 会员周期 / 月产量 / 平台 | 左侧栏常驻 | **底部摘要条 + 底部抽屉**（`#moOpen` → `.side.open`） |
| 数据表 | 7 列表格 | **每档一张两行卡片**（约 85px/档） |

三条踩过的坑（改动时务必保住）：
1. `.app` 窄屏转纵向时**必须显式 `align-items:stretch`** —— 否则交叉轴按内容宽度定尺寸，主区被 760px 表格撑宽、整页横向溢出
2. 内层滚动容器**不能用 `overscroll-behavior:contain`** —— 手机上手势会被它吃掉，页面滑不动
3. 窄屏卡片形态的 `overflow` 覆盖**必须用 `.tw.scroll-y.tw-main` 这个特异性** —— 只用 `.tw-main` 压不住 `.tw.scroll-y`

## 如何新增一个榜单页

三步，不需要碰模板：

1. 在 `data/` 新建 `<榜单>.json`，照 `leaderboard-vlm.json` 的字段结构填
   （`methodology.dimensions` 定权重、`entries` 放数据、`fieldSchema` 写字段说明）
2. 在 `build/build_site.py` 里加一个 `render_<榜单>()` —— 可直接复用排行榜页的渲染函数
3. 在 `data/site.json` 的 `nav` 数组加一项，导航自动出现

然后运行 `python build/build_site.py` 重新生成。**加数据即出榜，模板无需改动**（已实测验证）。

## 本地查看与构建

```bash
# 直接看（产物已在仓库内，无需构建）
双击 index.html

# 重新生成
python build/build_site.py

# 从零重建数据层（谨慎，会覆盖 data/*.json）
python build/build_data.py
```

## 部署

改完跑一次生成器，把 `deploy/` 里的 7 个文件重新拖到 Cloudflare Pages，链接不变。
详见上方「线上地址」与「部署要求」。

---

<sub>溯源指纹 HX-CLB-20260921-A215F0AB · 版权所有 (c) 2026 HELIX AI Studio</sub>

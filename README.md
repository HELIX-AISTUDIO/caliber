# 画布平台 · Seedance 2.5 出片成本与性价比对比

统一测试口径：**Seedance 2.5 · 720p · 16:9 · 30s · 全能参考**

对比平台：libtv / Neowow / 即梦 / 小云雀 / Higgsfield（**5 个平台 · 20 个档位**）

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

改动 `index.html` 后，把 `deploy/` 目录（5 个文件）重新拖到该项目的 Deployments 页即可，链接不变。

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

版权所有 © 2026 HELIX AI 工作室. **保留所有权利。**

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
| **平台 platform** | libtv / Neowow / 即梦 / 小云雀 / Higgsfield | `data/platforms.json` |
| **模型 model** | 被评测的模型 | `data/leaderboard-*.json` 的 `models` |
| **评测项 dimension** | 评分维度与权重 | `data/leaderboard-*.json` 的 `methodology.dimensions` |
| **数据点 entry** | 一条可比较的记录 | 各数据集的 `plans` / `entries` |

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

<sub>溯源指纹 HX-CLB-20260921-A215F0AB · 版权所有 (c) 2026 HELIX AI 工作室</sub>

# 设计系统 · 供后续页面复用

本文件固化 `index.html` 的视觉规范，来源为 **higgsfield.ai 实测**（CSS 变量 + 渲染截图双重取源，非目测）。
后续页面（如「视觉理解模型排行榜」）**直接复用本规范**，即可保证风格一致。

---

## 一、核心原则（这是「好看」的真正原因）

Higgsfield 的视觉纪律只有一条：**lime 是唯一强调色，且只做两件事。**

| lime 的两种用法 | 说明 |
|---|---|
| **小号实心药丸** | `background:#D1FE17; color:#0B0B0B` —— 按钮、状态标签、`New` 徽标 |
| **大块反转面** | 顶部通栏、页脚版权块 —— 整块 lime 底 + 纯黑文字 |

其余一切只用 **黑 / 白 / 灰**。粉色 `#FF4D8D` 仅用于极小徽标（如 `30% OFF`、`TOP`、`USD` 标记）。

> **反面教训**：第一版失败的原因不是颜色选错，而是**色彩过载** —— 5 个平台色 + 4 个语义色 + 荧光格纹理 + 到处发光 + 毛玻璃，全是噪音。修正是「减少」而不是「换色」。

**另一条纪律：不用毛玻璃。** 表面是实心 `#0B0B0B` + `1px rgba(255,255,255,.08)` 发丝描边。这既更接近 Higgsfield 实物，也顺带解决了微信 X5 内核不支持 `backdrop-filter` 的兼容问题。

---

## 二、色板

```css
--bg           : #000000;   /* 页面底，纯黑 */
--surface      : #0B0B0B;   /* 卡片 / 表格 / 说明块 */
--line         : rgba(255,255,255,.08);  /* 发丝描边 */
--line-soft    : rgba(255,255,255,.05);  /* 表格行分隔 */
--fg           : #C9CDD2;   /* 正文 */
--fg-strong    : #FFFFFF;   /* 标题 / 强调 */
--fg-mute      : #8A9099;   /* 辅助说明 */
--fg-dim       : #767C85;   /* 表头 / 极弱文字 */
--fg-ghost     : #5A6069;   /* 脚注 */
--lime         : #D1FE17;   /* 唯一强调色，品牌主色 */
--lime-dim     : rgba(209,254,23,.09);   /* lime 淡化底 */
--amber        : #FFC93C;   /* 仅用于风险/提示边框 */
--pink         : #FF4D8D;   /* 仅用于极小徽标 */
--danger       : #FF6B6B;   /* 仅用于否定型标签描边 */
```

Higgsfield 原始 token 备查：`--color-lime:#d1fe17`、`--color-gray:#0b0b0b`、`--color-black-2:#131313`、`--color-neutral-surface:#171717`、`--color-brand-tertiary:#9ce6f3`。

### 数据分类色（谨慎使用，只做 6px 圆点）

多系列数据需要区分时，只允许用在**小圆点**上，禁止用于面、条、框：

```css
libtv      #9CE6F3   /* cyan   */
Neowow     #00C65A   /* green  */
即梦        #3280FF   /* blue   */
小云雀      #FABC00   /* amber  */
Higgsfield #ED1572   /* magenta */
```

条形图**必须单色分级**，不做彩虹：
- 最优档 → 实心 `#D1FE17`
- 中段 → `linear-gradient(90deg,#3A3F47,#6E7681)`
- 末段 → `linear-gradient(90deg,#23272D,#3A3F47)`

---

## 三、字体

```css
--font-sans  : "Inter","Inter Display","SN Pro","Space Grotesk",
               ui-sans-serif,system-ui,-apple-system,"Segoe UI",
               "PingFang SC","Microsoft YaHei","Noto Sans CJK SC",sans-serif;
--font-disp  : "Space Grotesk","Inter Display","Inter","SN Pro",
               ui-sans-serif,system-ui,"PingFang SC","Microsoft YaHei",sans-serif;
--font-mono  : "IBM Plex Mono","JetBrains Mono","Geist Mono",
               ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
```

**不加载 webfont**（保持单文件零外部请求）。用同名字体栈 + 系统回退；中文配 PingFang SC / Microsoft YaHei。

| 角色 | 规格 |
|---|---|
| h1 主标题 | `clamp(29px,5vw,52px)` / 800 / `letter-spacing:-.038em` / `line-height:1.06` |
| h2 章节 | 21px / 750 / `-.025em` |
| h3 子节 | 14.5px / 700 / `-.015em` |
| 眉标 eyebrow | 11px / 700 / `letter-spacing:.15em` / uppercase / lime / mono |
| 章节序号 | mono 12px / lime，置于 h2 内 `.ey` |
| 表头 | 10.5px / 700 / `letter-spacing:.095em` / uppercase / `--fg-dim` |
| 正文 | 13–14px / 1.7–1.78 |
| 所有数字 | **必须 mono** + `letter-spacing:-.022em` + 右对齐 |
| 统计大数字 | mono 26px / 700 / `-.032em` |

大标题字距压紧是 Higgsfield 的签名（原始值 `-1px ~ -4px`），中文靠字号 + 字重 + 负字距建立层级。

---

## 四、组件规格

### 顶部 lime 通栏 `.promo`
```
background:#D1FE17; color:#0B0B0B; font-size:12.5px; font-weight:600;
padding:10px 22px; display:flex; justify-content:center; gap:13px; flex-wrap:wrap
```
内部可放一个 `border:1.5px solid #0B0B0B; border-radius:999px` 的描边药丸。

### 顶栏 `.nav`
```
border-bottom:1px solid rgba(255,255,255,.08)
```
- 左侧品牌：`.brand` = `22×22px` lime 圆角方块 + 名称（14px/700/`-.022em`）
- 中间菜单 `.menu`：13px/600/`#9AA0A8`，项内可嵌 lime 胶囊 `.nb`（9.5px/800/黑字）
- 右侧：lime 描边药丸（当前口径）
- **移动端**：`.menu` 横向滚动，`scrollbar-width:none`，条目 `flex:0 0 auto`

### 卡片 `.card` / `.kpi`
```
background:#0B0B0B; border:1px solid rgba(255,255,255,.08); border-radius:18px;
padding:20px 22px      /* .kpi */
padding:22px 24px      /* .card */
```
- `.kpi .t` = 10.5px/700/`letter-spacing:.095em`/uppercase/`--fg-dim`
- `.kpi .v` = mono 26px/700，**仅最优项染 lime**（`.good` / `.hi`），其余保持白色
- `.kpi.hi` 仅把描边换成 `rgba(209,254,23,.45)`
- **禁止**给卡片加彩色左边条（第一版的噪音源之一）

### 按钮
```
.btn{ border-radius:999px; padding:12px 23px; font-size:13px; font-weight:700 }
.btn-fill { background:#D1FE17; color:#0B0B0B }           /* 主行动 */
.btn-ghost{ background:transparent; color:#fff; border:1px solid rgba(255,255,255,.2) }
```

### 表格
```
th{ background:transparent; 无底色; border-bottom:1px solid rgba(255,255,255,.08) }
td{ padding:13px 14px; border-bottom:1px solid rgba(255,255,255,.05) }
tr:hover{ background:rgba(255,255,255,.032) }
tr.top  { background:rgba(209,254,23,.055) }   /* 最优行 */
tr.top td:first-child{ box-shadow:inset 3px 0 0 #D1FE17 }
.ybest  { background:#D1FE17; color:#0B0B0B; font-weight:800 }
```

### 标签（只给最优给 lime）
```
.v-good{ background:#D1FE17; color:#0B0B0B }                       /* 强烈推荐 */
.v-warn{ background:transparent; color:#C9CDD2; border:1px solid rgba(255,255,255,.18) }
.v-bad { background:transparent; color:#FF6B6B; border:1px solid rgba(255,107,107,.32) }
```

### 说明块 `.note`
统一实心面 + 无底色变化，仅靠左侧 2px 细线区分语义：
```
.note.warn{ border-left:2px solid rgba(255,201,60,.55) }
.note.good{ border-left:2px solid rgba(209,254,23,.5)  }
.note.pink{ border-left:2px solid rgba(255,77,141,.45) }
```

### 页脚版权块 `.legal`（签名元素）
```
background:#D1FE17; border-color:#D1FE17;
color:#0B0B0B; padding:28px 30px; border-radius:20px
.legal-t{ font-size:16px; font-weight:800 }     /* 黑字 */
.legal-f .fp{ background:#0B0B0B; color:#D1FE17; border-radius:6px }  /* 指纹反色 */
```

---

## 五、条形图规范

**必须用「效率条」，不要用成本占比条。**
- 成本占比条（`width = 本档成本 / 最高成本`）会让 20–45 元区间全被压在 20–45% 宽度内，看不出差异。
- 效率条：`width = 全场最优成本 / 本档成本 × 100%` → 最优档 100%，最差价 19%，差异一眼可见。
- 必须标注「条形越长 = 越省」，否则语义反直觉。

```
.bar-row { grid-template-columns:206px 1fr 76px; gap:14px }
.bar-track{ height:14px; background:rgba(255,255,255,.05); border-radius:999px }
.bar-fill { border-radius:999px }
```

---

## 六、移动端与兼容

```css
@media (max-width:820px){ /* 两级断点：820 / 520 */ }
```

- 键盘可达性：`.menu a` 横向滚动，`.tw` 表格横向滚动
- **微信 X5 兼容**：已彻底不用 `backdrop-filter` / `color-mix` / `100dvh`；固定定位元素加 `translate3d(0,0,0)` 提升合成层
- `viewport-fit=cover` + `padding-bottom: calc(72px + env(safe-area-inset-bottom,0px))`
- `@media print` 浅色适配，保证存 PDF 时版权块与溯源指纹保留
- **字体缺字形自检**：避免用 `▾`（部分中文字体缺此字形，会渲染成小横线），排序指示改用 `↓`

---

## 七、多页面导航约定

后续页面（视觉理解模型排行榜等）须满足：

1. **复用本文件的 `.promo` / `.nav` / `.menu` 结构**，品牌区文案统一，菜单项在两个页面间互相可跳。
2. 当前页面对应菜单项加 `.active` 态（lime 文字）。
3. 未上线页面用 `<a class="soon">名称<i class="nb">即将上线</i></a>` 占位（无 `href`，`cursor:default`）。
4. 每个页面的 `<head>` 必须保留版权头注释与溯源指纹；指纹随数据集变化而更新。
5. 章节锚点约定：`<h2 id="m-N">`（N 为章节序号，不补零），菜单链接 `#m-N`。

---

溯源指纹：**CS-VPC-20260921-8CE5B15F**

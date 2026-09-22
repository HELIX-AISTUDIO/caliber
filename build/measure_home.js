// 首页首屏测量（手机 + 桌面双端）
//
// 为什么存在：手机端首页的诉求是「点进来第一眼看到滑块」，
// 而这件事只能靠真实视口量 —— 高度、折线、视觉顺序都不是能从 CSS 里读出来的。
//
// 用法：node build/measure_home.js
const { chromium } = require('playwright-core');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const EDGE = process.env.CALIBER_EDGE
  || 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';

/* 视觉顺序用 order 控制，DOM 顺序≠视觉顺序，所以必须按【渲染后的 top】排，
   不能按查询顺序排。期望：
     手机 (≤820px)  标题 → 反查滑块 → 说明文字   ← 滑块必须在说明文字之前
     桌面 (>820px)  标题 → 说明文字 → 反查滑块   ← 保持改造前的顺序 */
const CASES = [
  { tag: '手机 390×844', w: 390, h: 844, mobile: true, expect: ['hero', 'budget', 'more'] },
  { tag: '桌面 1440×900', w: 1440, h: 900, mobile: false, expect: ['hero', 'more', 'budget'] },
];

(async () => {
  const browser = await chromium.launch({ executablePath: EDGE, headless: true });
  let bad = 0;
  for (const c of CASES) {
    const page = await browser.newPage({
      viewport: { width: c.w, height: c.h }, isMobile: c.mobile, hasTouch: c.mobile,
    });
    await page.goto('file:///' + path.join(ROOT, 'site', 'index.html').replace(/\\/g, '/'),
      { waitUntil: 'load' });
    await page.waitForTimeout(500);

    const m = await page.evaluate(() => {
      const g = s => document.querySelector(s);
      const box = el => {
        if (!el) return null;
        const r = el.getBoundingClientRect();
        return { top: Math.round(r.top + window.scrollY), h: Math.round(r.height) };
      };
      const items = [
        ['promo', g('.promo')], ['nav', g('nav,.nav,header')],
        ['hero', g('.hero')], ['  eyebrow', g('.hero .eyebrow')], ['  h1', g('.hero h1')],
        ['budget 节', g('#budget')], ['  sechead', g('#budget .sechead')],
        ['  预算行', g('#hbud') && g('#hbud').closest('.budrow')],
        ['  滑块', g('#hbudR')], ['  结果', g('#hbudOut')], ['  budtip', g('.budtip')],
        ['more 说明+按钮', g('.heromore')], ['  说明文字', g('.heromore .lead')],
        ['  按钮组', g('.heromore .btns')], ['cost 节', g('#cost')],
      ];
      const rows = items.map(([label, el]) => {
        const b = box(el);
        return b ? { label, ...b } : { label, missing: true };
      });
      // 视觉顺序：只看三块主体，按渲染 top 排序
      const order = [['hero', g('.hero')], ['budget', g('#budget')], ['more', g('.heromore')]]
        .filter(x => x[1])
        .map(x => ({ k: x[0], top: box(x[1]).top }))
        .sort((a, b) => a.top - b.top)
        .map(x => x.k);
      return { rows, order, vh: window.innerHeight, sh: document.documentElement.scrollHeight };
    });

    console.log('\n═══ ' + c.tag + ' ═══');
    console.log('文档高 ' + m.sh + ' ｜ 折线 y=' + m.vh);
    console.log('区块'.padEnd(20) + 'top'.padStart(6) + 'h'.padStart(6) + '底边'.padStart(7) + '   首屏');
    console.log('-'.repeat(52));
    for (const r of m.rows) {
      if (r.missing) { console.log(r.label.padEnd(20) + '   （未找到）'); continue; }
      const bot = r.top + r.h;
      console.log(r.label.padEnd(20) + String(r.top).padStart(6) + String(r.h).padStart(6) +
        String(bot).padStart(7) + '   ' +
        (bot <= m.vh ? '✓ 完整' : (r.top < m.vh ? '△ 被截断' : '✗ 屏外')));
    }
    const ok = JSON.stringify(m.order) === JSON.stringify(c.expect);
    console.log('视觉顺序 ' + m.order.join(' → ') + '   ' +
      (ok ? '✓ 符合预期' : '✗ 期望 ' + c.expect.join(' → ')));
    if (!ok) bad++;
    await page.close();
  }
  await browser.close();
  console.log('\n' + (bad ? '✗ 有 ' + bad + ' 项顺序不符' : '✓ 双端顺序与首屏均符合预期'));
  process.exit(bad ? 1 : 0);
})();

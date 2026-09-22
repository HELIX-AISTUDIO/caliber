// 首页改造前后对拍：以 git HEAD 的旧 index.html 为基线，逐项比对几何。
//
// 为什么需要它：order 布局改动最容易出的是【宽度/左边界】回退 ——
// 上一轮只量了 top/height，「flex 子项带 auto margin 不被 stretch」导致
// 标题与预算框收窄居中，脚本全绿而截图一眼就能看出不对。
// 所以这里必须把 width / left 一起量，并且拿旧版做真人基线。
//
// 用法：node build/compare_home.js
const { chromium } = require('playwright-core');
const path = require('path');
const fs = require('fs');

const ROOT = path.resolve(__dirname, '..', '..');
const SITE = path.join(ROOT, 'site');
const OLD = path.join(SITE, '.home-old-baseline.html');
const EDGE = process.env.CALIBER_EDGE
  || 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';

// 桌面端：这些项必须与旧版【逐值相同】（只允许纵向位移）
// 手机端：允许顺序变化，所以只查宽度/左边界不回退
const SEL = {
  'hero': '.hero',
  'h1': '.hero h1',
  'lead': '.lead',
  'btns': '.btns',
  'budget': '#budget',
  'slider': '#hbudR',
  'budhome': '.budhome',
};

const measure = async (page) => page.evaluate((sels) => {
  const out = {};
  for (const k in sels) {
    const el = document.querySelector(sels[k]);
    if (!el) { out[k] = null; continue; }
    const r = el.getBoundingClientRect();
    out[k] = { x: Math.round(r.left), w: Math.round(r.width), y: Math.round(r.top + window.scrollY) };
  }
  out._docH = document.documentElement.scrollHeight;
  out._overflow = document.documentElement.scrollWidth - window.innerWidth;
  return out;
}, SEL);

(async () => {
  // 基线由外部先导出（脚本内不调 git：沙箱里 spawn cmd.exe 会 EBUSY）：
  //   git show HEAD:index.html > site/.home-old-baseline.html
  if (!fs.existsSync(OLD)) {
    console.error('缺少基线文件 ' + path.relative(ROOT, OLD) + '\n' +
      '  先执行：git show HEAD:index.html > site/.home-old-baseline.html');
    process.exit(2);
  }

  const browser = await chromium.launch({ executablePath: EDGE, headless: true });
  let bad = 0;

  for (const vp of [
    { tag: '桌面 1440', w: 1440, h: 900, m: false, strict: true },
    { tag: '手机 390', w: 390, h: 844, m: true, strict: false },
  ]) {
    const get = async (url) => {
      const p = await browser.newPage({
        viewport: { width: vp.w, height: vp.h }, isMobile: vp.m, hasTouch: vp.m,
      });
      await p.goto(url, { waitUntil: 'load' });
      await p.evaluate(() => { try {
        localStorage.setItem('caliber.guide.v1', '1');
        localStorage.setItem('caliber.intro.v1', '1');
      } catch (e) {} });
      await p.reload({ waitUntil: 'load' });
      await p.waitForTimeout(450);
      const r = await measure(p);
      await p.close();
      return r;
    };
    const base = await get('file:///' + path.join(SITE, '.home-old-baseline.html').replace(/\\/g, '/'));
    const now = await get('file:///' + path.join(SITE, 'index.html').replace(/\\/g, '/'));

    console.log('\n═══ ' + vp.tag + ' ═══');
    console.log('项'.padEnd(10) + '旧 x/w'.padStart(16) + '新 x/w'.padStart(16) + '   x  Δ   w  Δ');
    console.log('-'.repeat(62));
    for (const k of Object.keys(SEL)) {
      const a = base[k], b = now[k];
      if (!a || !b) { console.log(k.padEnd(10) + '   （缺）'); continue; }
      const dx = b.x - a.x, dw = b.w - a.w;
      let flag = '';
      if (dx !== 0) { flag += ' ←x'; bad++; }          // 左边界任何变化都要解释
      if (Math.abs(dw) > 1) { flag += ' ←w'; bad++; }  // 宽度变化
      console.log(k.padEnd(10) +
        (a.x + '/' + a.w).padStart(16) + (b.x + '/' + b.w).padStart(16) +
        String(dx).padStart(6) + String(dw).padStart(6) + flag);
    }
    console.log('纵向位移（允许，order 生效的必然结果）: 滑块 y ' +
      base.slider.y + ' → ' + now.slider.y + '（Δ' + (now.slider.y - base.slider.y) + '）');
    console.log('文档高 ' + base._docH + ' → ' + now._docH +
      ' ｜ 横向溢出 ' + base._overflow + ' → ' + now._overflow + 'px');
  }

  await browser.close();
  fs.unlinkSync(OLD);
  console.log('\n' + (bad ? '✗ 有 ' + bad + ' 处 x/w 变化，需逐一确认是否预期' : '✓ x/w 全部与旧版一致（只有纵向位移）'));
  process.exit(bad ? 1 : 0);
})();

// 手机端「调整筛选」抽屉穿模取证 v2
//
// 思路：不读 CSS 猜层级（mobar 50 < scrim 55 < side 60 看起来是对的，
// 但截图里底部条明显和抽屉撞在一起）。改用 elementFromPoint 逐点采样，
// 直接问浏览器「这条坐标上实际画出来的是谁」—— 这是唯一的地面真相。
//
// 用法：node build/diagnose_drawer.js [--shots]
const { chromium } = require('playwright-core');
const path = require('path');
const fs = require('fs');

const ROOT = path.resolve(__dirname, '..', '..');
const SITE = path.join(ROOT, 'site');
const OUT = path.join(ROOT, 'harvest');
const EDGE = process.env.CALIBER_EDGE
  || 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const SHOTS = process.argv.includes('--shots');

const descJs = `(el) => {
  if (!el) return 'null';
  if (el === document.documentElement) return 'html';
  const id = el.id ? '#' + el.id : '';
  const c = el.className && typeof el.className === 'string'
    ? '.' + el.className.trim().split(/\\s+/).slice(0, 2).join('.') : '';
  let s = (el.tagName || '?').toLowerCase() + id + c;
  if (el.tagName === 'BUTTON' || el.tagName === 'A') {
    const t = (el.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 12);
    if (t) s += '「' + t + '」';
  }
  return s;
}`;

(async () => {
  const browser = await chromium.launch({ executablePath: EDGE, headless: true });
  const page = await browser.newPage({
    viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2,
  });
  await page.goto('file:///' + path.join(SITE, 'cost.html').replace(/\\/g, '/'), { waitUntil: 'load' });
  await page.evaluate(() => { try {
    localStorage.setItem('caliber.guide.v1', '1');
    localStorage.setItem('caliber.intro.v1', '1');
  } catch (e) {} });
  await page.reload({ waitUntil: 'load' });
  await page.waitForTimeout(500);

  // 打开抽屉：点底部条上的「调整」按钮
  const opened = await page.evaluate(() => {
    const side = document.querySelector('.side');
    const btn = [...document.querySelectorAll('.mobar button, button')]
      .find(b => /调整/.test(b.textContent || ''));
    if (btn) { btn.click(); return 'clicked:' + btn.textContent.trim().slice(0, 8); }
    if (side) { side.classList.add('open', 'peek'); return 'classList'; }
    return 'none';
  });
  await page.waitForTimeout(600);

  const r = await page.evaluate((descSrc) => {
    const desc = eval(descSrc);
    const rect = el => { if (!el) return null; const b = el.getBoundingClientRect();
      return { top: Math.round(b.top), bottom: Math.round(b.bottom), h: Math.round(b.height), left: Math.round(b.left), w: Math.round(b.width) }; };
    const side = document.querySelector('.side');
    const scrim = document.getElementById('scrim');
    const mobar = document.querySelector('.mobar');
    const cs = el => el ? getComputedStyle(el) : null;
    const sr = rect(side);

    // 逐点采样：抽屉顶边上下各 60px，每 6px 一点；再采视口底部两点
    const ys = [];
    for (let y = Math.max(0, sr.top - 60); y <= Math.min(843, sr.top + 60); y += 6) ys.push(y);
    ys.push(838, 820, 790);
    const samples = ys.map(y => {
      const el = document.elementFromPoint(195, y);
      return { y, el: desc(el), inSide: !!(side && el && side.contains(el)) };
    });

    // 找出所有「fixed/sticky 且与抽屉矩形相交」的元素（含其 z 与透明度）
    const suspects = [];
    document.querySelectorAll('*').forEach(el => {
      const c = cs(el);
      if (!c || (c.position !== 'fixed' && c.position !== 'sticky')) return;
      if (c.display === 'none' || c.visibility === 'hidden') return;
      const b = rect(el);
      if (!b || b.h < 2) return;
      if (b.bottom <= sr.top || b.top >= sr.bottom) return;
      suspects.push({
        el: desc(el), pos: c.position, z: c.zIndex, opacity: c.opacity,
        top: b.top, bottom: b.bottom, inSide: side.contains(el),
        parentZ: (() => { let n = el.parentElement; while (n && n !== document.body) {
          const pz = cs(n).zIndex; if (pz !== 'auto') return desc(n) + ' z=' + pz; n = n.parentElement; } return '（无 z 祖先）'; })(),
      });
    });

    return {
      side: sr, scrim: rect(scrim), mobar: rect(mobar),
      scrimOpen: scrim ? scrim.className : '?',
      scrimZ: scrim ? cs(scrim).zIndex : '?',
      mobarZ: mobar ? cs(mobar).zIndex : '?',
      sideZ: side ? cs(side).zIndex : '?',
      sideOpacity: side ? cs(side).opacity : '?',
      samples, suspects, vh: window.innerHeight,
    };
  }, descJs);

  console.log('打开方式: ' + opened);
  console.log('抽屉 .side   top=' + r.side.top + ' bottom=' + r.side.bottom + ' 高=' + r.side.h + '  z=' + r.sideZ);
  console.log('遮罩 #scrim  ' + JSON.stringify(r.scrim) + '  class="' + r.scrimOpen + '"  z=' + r.scrimZ);
  console.log('底部 .mobar  ' + JSON.stringify(r.mobar) + '  z=' + r.mobarZ);
  console.log('视口高 ' + r.vh);

  console.log('\n逐点采样 elementFromPoint(195, y)：');
  console.log('   y    画在最上面的是');
  console.log('  ' + '-'.repeat(64));
  for (const s of r.samples) {
    console.log('  ' + String(s.y).padStart(4) + '   ' + s.el + (s.inSide ? '   [抽屉内]' : '   ← 非抽屉'));
  }

  console.log('\n与抽屉矩形相交的 fixed/sticky 元素：');
  for (const s of r.suspects) {
    console.log('  ' + (s.inSide ? '抽屉内' : '抽屉外') + ' ' + s.pos.padEnd(7) +
      ' top=' + String(s.top).padStart(5) + ' bot=' + String(s.bottom).padStart(5) +
      ' z=' + String(s.z).padStart(4) + ' opacity=' + s.opacity +
      '  ' + s.el + '   父层: ' + s.parentZ);
  }

  if (SHOTS) {
    fs.mkdirSync(OUT, { recursive: true });
    await page.screenshot({ path: path.join(OUT, 'drawer_v2.png') });
    await page.screenshot({
      path: path.join(OUT, 'drawer_v2_edge.png'),
      clip: { x: 0, y: Math.max(0, r.side.top - 90), width: 390, height: 200 },
    });
    await page.screenshot({
      path: path.join(OUT, 'drawer_v2_bottom.png'),
      clip: { x: 0, y: 644, width: 390, height: 200 },
    });
    console.log('\n✓ drawer_v2.png / drawer_v2_edge.png / drawer_v2_bottom.png');
  }

  await browser.close();
})();

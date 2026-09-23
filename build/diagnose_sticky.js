// 抽屉 sticky 表头错位取证：复现「划上去（上拉展开）」后
// .sheet-hd 与第一个 .sgroup 渲染顺序互换的现象。
//
// 背景：用户手机截图里「排名 / 反查」行跑到了把手与「调整筛选」标题之上（顺序颠倒）。
// DOM 顺序是对的（sheet-hd 在第一位），也没有 order —— 怀疑是
// will-change:max-height 把面板提升为合成层后，sticky 子元素与滚动偏移不同步。
//
// 用法：node build/diagnose_sticky.js
const { chromium } = require('playwright-core');
const path = require('path');

const SITE = path.resolve(__dirname, '..', '..', 'site');
const EDGE = process.env.CALIBER_EDGE
  || 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';

const snap = (page) => page.evaluate(() => {
  const side = document.querySelector('.side');
  const hd = document.querySelector('.sheet-hd');
  const g0 = side.querySelector('.sgroup');
  const sr = side.getBoundingClientRect();
  const hr = hd.getBoundingClientRect();
  const gr = g0.getBoundingClientRect();
  const cs = getComputedStyle(hd);
  return {
    sideTop: Math.round(sr.top), sideH: Math.round(sr.height),
    hdTop: Math.round(hr.top), g0Top: Math.round(gr.top),
    // 核心判据：内容组跑到表头之上 = 顺序颠倒
    inverted: gr.top < hr.top - 0.5,
    hdPos: cs.position, hdTopCss: cs.top, hdZ: cs.zIndex,
    sideMaxH: getComputedStyle(side).maxHeight,
    sideInlineMaxH: side.style.maxHeight || '(无)',
    scrollTop: Math.round(side.scrollTop),
    scrollH: Math.round(side.scrollHeight), clientH: Math.round(side.clientHeight),
    willChange: getComputedStyle(side).willChange,
    foldDir: getComputedStyle(side).flexDirection,
  };
});

(async () => {
  const browser = await chromium.launch({ executablePath: EDGE, headless: true });
  const page = await browser.newPage({
    viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true,
  });
  await page.goto('file:///' + path.join(SITE, 'cost.html').replace(/\\/g, '/'), { waitUntil: 'load' });
  await page.evaluate(() => { try {
    localStorage.setItem('caliber.guide.v1', '1');
    localStorage.setItem('caliber.intro.v1', '1');
  } catch (e) {} });
  await page.reload({ waitUntil: 'load' });
  await page.waitForTimeout(400);

  const base = await snap(page);
  console.log('── 初始（抽屉未开）──');
  console.log('  will-change=' + base.willChange + '  flex-direction=' + base.foldDir +
    '  hd.position=' + base.hdPos + ' top=' + base.hdTopCss);

  // 打开抽屉
  await page.evaluate(() => {
    const b = [...document.querySelectorAll('.mobar button')].find(x => /调整/.test(x.textContent || ''));
    if (b) b.click();
  });
  await page.waitForTimeout(600);
  const peek = await snap(page);
  console.log('\n── 半开（peek）──');
  console.log('  sideTop=' + peek.sideTop + ' 高=' + peek.sideH +
    '  hdTop=' + peek.hdTop + '  g0Top=' + peek.g0Top + '  顺序颠倒=' + peek.inverted);

  // 复现「划上去」：在把手上做上拉拖拽（与 smoke.js 同一手法）
  const drag = await page.evaluate(async () => {
    const side = document.querySelector('.side'), hd = document.querySelector('.sheet-hd');
    const r = hd.getBoundingClientRect();
    const cy = r.top + r.height / 2;
    const ev = (t, y) => hd.dispatchEvent(new PointerEvent(t, {
      clientY: y, bubbles: true, pointerId: 1, isPrimary: true,
    }));
    ev('pointerdown', cy);
    for (let i = 1; i <= 10; i++) { ev('pointermove', cy - i * 32); }
    const hDragged = side.getBoundingClientRect().height;
    ev('pointerup', cy - 320);
    await new Promise(res => setTimeout(res, 500));
    return { hDragged: Math.round(hDragged) };
  });
  const afterDrag = await snap(page);
  console.log('\n── 上拉展开后（拖拽中高度 ' + drag.hDragged + '）──');
  console.log('  sideTop=' + afterDrag.sideTop + ' 高=' + afterDrag.sideH +
    '  hdTop=' + afterDrag.hdTop + '  g0Top=' + afterDrag.g0Top +
    '  ★顺序颠倒=' + afterDrag.inverted);
  console.log('  inline maxHeight=' + afterDrag.sideInlineMaxH +
    '  scrollTop=' + afterDrag.scrollTop +
    '  scroll/客户 ' + afterDrag.scrollH + '/' + afterDrag.clientH);

  // 再试滚动抽屉内容
  const scrolled = await page.evaluate(async () => {
    const side = document.querySelector('.side');
    side.scrollTop = 120;
    await new Promise(res => setTimeout(res, 350));
    return true;
  });
  const afterScroll = await snap(page);
  console.log('\n── 抽屉内容滚动 120px 后 ──');
  console.log('  hdTop=' + afterScroll.hdTop + '  g0Top=' + afterScroll.g0Top +
    '  ★顺序颠倒=' + afterScroll.inverted + '  scrollTop=' + afterScroll.scrollTop);

  // 再试「先滚动再拖拽」的组合
  await page.evaluate(async () => {
    const side = document.querySelector('.side'), hd = document.querySelector('.sheet-hd');
    side.scrollTop = 200;
    const r = hd.getBoundingClientRect();
    const cy = r.top + r.height / 2;
    const ev = (t, y) => hd.dispatchEvent(new PointerEvent(t, {
      clientY: y, bubbles: true, pointerId: 2, isPrimary: true,
    }));
    ev('pointerdown', cy);
    for (let i = 1; i <= 6; i++) ev('pointermove', cy + i * 30);   // 下压
    ev('pointerup', cy + 180);
    await new Promise(res => setTimeout(res, 500));
  });
  const combo = await snap(page);
  console.log('\n── 滚动后再下拉（组合）──');
  console.log('  hdTop=' + combo.hdTop + '  g0Top=' + combo.g0Top +
    '  ★顺序颠倒=' + combo.inverted + '  sideTop=' + combo.sideTop);

  const any = [peek, afterDrag, afterScroll, combo].some(x => x.inverted);
  console.log('\n' + (any ? '✗ 复现到顺序颠倒' : '✓ 四种状态均未复现顺序颠倒'));

  await browser.close();
  process.exit(any ? 1 : 0);
})();

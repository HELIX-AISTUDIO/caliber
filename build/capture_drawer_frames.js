// 抓「调整筛选」抽屉打开动画的逐帧，看是否存在【抽屉内容跑出顶边】的瞬时态。
//
// 背景：用户截图里抽屉内的「功能」行副标签（看谁最省 / 我有条件，能买啥）
// 出现在抽屉顶边之外，且「调整筛选」标题被压在下面（顺序颠倒）。
// 几何上 .mobar(fixed bottom:0, 62px) 不可能穿过 42vh 的抽屉，
// 所以怀疑是 max-height 过渡期间的瞬时渲染。
//
// 用法：node build/capture_drawer_frames.js
const { chromium } = require('playwright-core');
const path = require('path');
const fs = require('fs');

const ROOT = path.resolve(__dirname, '..', '..');
const SITE = path.join(ROOT, 'site');
const OUT = path.join(ROOT, 'harvest', 'drawer_frames');
const EDGE = process.env.CALIBER_EDGE
  || 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';

(async () => {
  fs.rmSync(OUT, { recursive: true, force: true });
  fs.mkdirSync(OUT, { recursive: true });

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
  await page.waitForTimeout(500);

  // 点击「调整」并立刻开始逐帧采样
  const frames = await page.evaluate(async () => {
    const side = document.querySelector('.side');
    const hd = side && side.querySelector('.sheet-hd');
    const row = [...side.querySelectorAll('*')].find(e =>
      /看谁最省/.test(e.textContent || '') && e.children.length === 0);
    const btn = [...document.querySelectorAll('.mobar button, button')]
      .find(b => /调整/.test(b.textContent || ''));
    if (!btn) return [{ err: '找不到「调整」按钮' }];

    const snap = (t) => {
      const sr = side.getBoundingClientRect();
      const hr = hd ? hd.getBoundingClientRect() : null;
      const rr = row ? row.getBoundingClientRect() : null;
      return {
        t: Math.round(t),
        sideTop: Math.round(sr.top), sideBottom: Math.round(sr.bottom), sideH: Math.round(sr.height),
        hdTop: hr ? Math.round(hr.top) : null,
        rowTop: rr ? Math.round(rr.top) : null,
        // 关键判据：抽屉内元素是否跑到了抽屉顶边之上
        rowAboveSide: !!(rr && rr.top < sr.top - 1),
        hdAboveRow: !!(hr && rr && hr.top > rr.top),   // 标题被压在子标签下面 = 顺序颠倒
        sideMaxH: getComputedStyle(side).maxHeight,
        sideTransform: getComputedStyle(side).transform,
      };
    };

    const out = [];
    const t0 = performance.now();
    btn.click();
    await new Promise(res => {
      const tick = () => {
        out.push(snap(performance.now() - t0));
        if (performance.now() - t0 < 700) requestAnimationFrame(tick);
        else res();
      };
      requestAnimationFrame(tick);
    });
    return out;
  });

  if (frames[0] && frames[0].err) { console.log('✗ ' + frames[0].err); await browser.close(); process.exit(2); }

  console.log('共采样 ' + frames.length + ' 帧（700ms 内）');
  console.log('   t(ms)  sideTop sideBot sideH  hdTop  rowTop  行在顶边外  标题被压');
  console.log('  ' + '-'.repeat(76));
  let bad = [];
  for (const f of frames) {
    const mark = (f.rowAboveSide || f.hdAboveRow) ? '  ★异常' : '';
    if (f.rowAboveSide || f.hdAboveRow) bad.push(f);
    if (f.t % 60 < 18 || mark) {   // 采样太密，只打关键帧
      console.log('  ' + String(f.t).padStart(6) + String(f.sideTop).padStart(8) +
        String(f.sideBottom).padStart(8) + String(f.sideH).padStart(7) +
        String(f.hdTop).padStart(7) + String(f.rowTop).padStart(8) +
        String(f.rowAboveSide).padStart(11) + String(f.hdAboveRow).padStart(10) + mark);
    }
  }
  console.log('\n异常帧: ' + bad.length + ' / ' + frames.length);
  if (bad.length) {
    console.log('  首帧 t=' + bad[0].t + '  sideTop=' + bad[0].sideTop +
      ' rowTop=' + bad[0].rowTop + ' maxHeight=' + bad[0].sideMaxH);
    console.log('  末帧 t=' + bad[bad.length - 1].t);
  }

  // 再抓几帧实图（异常帧附近）
  if (bad.length) {
    const shotAt = [bad[0].t, Math.round((bad[0].t + bad[bad.length - 1].t) / 2), bad[bad.length - 1].t];
    for (const ms of shotAt) {
      console.log('  截图 t≈' + ms + 'ms → 需重跑，见下方说明');
      break;
    }
  }
  await browser.close();
  process.exit(bad.length ? 1 : 0);
})();

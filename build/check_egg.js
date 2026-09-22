// ¥0 彩蛋档 + 手机端首屏 验收脚本
// 用法：node build/check_egg.js [--shots]
const { chromium } = require('playwright-core');
const path = require('path');
const fs = require('fs');

const ROOT = path.resolve(__dirname, '..', '..');
const EDGE = process.env.CALIBER_EDGE
  || 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const OUT = path.join(ROOT, 'harvest');
const SHOTS = process.argv.includes('--shots');
const URL = 'file:///' + path.join(ROOT, 'site', 'index.html').replace(/\\/g, '/');

let fail = 0;
const ok = (c, msg, extra) => {
  console.log('  ' + (c ? '✓' : '✗') + ' ' + msg + (extra !== undefined ? '   ' + extra : ''));
  if (!c) fail++;
};

(async () => {
  const browser = await chromium.launch({ executablePath: EDGE, headless: true });
  const page = await browser.newPage({
    viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true,
  });
  const errs = [];
  page.on('pageerror', e => errs.push(e.message));
  page.on('dialog', d => d.accept());
  await page.goto(URL, { waitUntil: 'load' });
  // 关掉两个自动弹窗（新手引导 + 术语引导）—— 它们会锁滚动并盖住首屏与彩蛋输出。
  // ⚠ 键名取自 build_site.py 的 KEY 常量（caliber.guide.v1 / caliber.intro.v1），
  //   之前随手猜的 'caliber_intro_seen' 根本不存在，于是截图里全是弹窗。
  await page.evaluate(() => {
    try {
      localStorage.setItem('caliber.guide.v1', '1');
      localStorage.setItem('caliber.intro.v1', '1');
    } catch (e) { /* file:// 下可能不可用 */ }
  });
  await page.reload({ waitUntil: 'load' });
  await page.waitForTimeout(400);

  console.log('\n── 手机首屏 ──');
  const sl = await page.evaluate(() => {
    const r = document.getElementById('hbudR');
    return { top: Math.round(r.getBoundingClientRect().top + window.scrollY), vh: window.innerHeight };
  });
  ok(sl.top < sl.vh, '滑块在首屏折线之上', 'y=' + sl.top + ' / ' + sl.vh);
  if (SHOTS) {
    fs.mkdirSync(OUT, { recursive: true });
    await page.screenshot({ path: path.join(OUT, 'home_mobile_top.png') });
  }

  console.log('\n── ¥0 彩蛋（键盘输入）──');
  await page.fill('#hbud', '0');
  await page.dispatchEvent('#hbud', 'input');
  await page.waitForTimeout(200);
  let t = await page.textContent('#hbudOut');
  ok(/能做个蛋/.test(t), '出现彩蛋文案', JSON.stringify(t.slice(0, 34)));
  ok(/0 条/.test(t), '主行仍是「0 条」');
  ok(!/买不到任何档位/.test(t), '不再落到「买不到任何档位」的干巴分支');
  const rv = await page.inputValue('#hbudR');
  ok(rv === '0', '输入 0 后滑块同步到最左格', 'slider=' + rv);
  if (SHOTS) await page.screenshot({ path: path.join(OUT, 'home_mobile_egg.png') });

  console.log('\n── ¥0 彩蛋（拖滑块到最左）──');
  await page.fill('#hbud', '3000');
  await page.dispatchEvent('#hbud', 'input');
  await page.waitForTimeout(150);
  await page.evaluate(() => {
    const r = document.getElementById('hbudR');
    r.value = '0';
    r.dispatchEvent(new Event('input', { bubbles: true }));
  });
  await page.waitForTimeout(200);
  const iv = await page.inputValue('#hbud');
  t = await page.textContent('#hbudOut');
  ok(iv === '0', '滑块拖到最左 → 数字框变 0', 'input=' + iv);
  ok(/能做个蛋/.test(t), '滑块拖到最左也能触发彩蛋');

  console.log('\n── ¥0 不污染正常档位 ──');
  // 滑块 1 应该是 ¥300（不是 ¥0），否则 0 档会吃掉正常区间
  const v1 = await page.evaluate(() => {
    const r = document.getElementById('hbudR');
    r.value = '1'; r.dispatchEvent(new Event('input', { bubbles: true }));
    return document.getElementById('hbud').value;
  });
  ok(v1 === '300', '滑块第 1 格 = ¥300（0 档没有吃掉正常下界）', '¥' + v1);
  const vmax = await page.evaluate(() => {
    const r = document.getElementById('hbudR');
    r.value = '1000'; r.dispatchEvent(new Event('input', { bubbles: true }));
    return document.getElementById('hbud').value;
  });
  ok(vmax === '50000', '滑块最右仍 = ¥50,000', '¥' + vmax);
  // 打 0 之后能不能回到正常：再打 3000
  await page.fill('#hbud', '3000');
  await page.dispatchEvent('#hbud', 'input');
  await page.waitForTimeout(150);
  t = await page.textContent('#hbudOut');
  ok(!/能做个蛋/.test(t) && /最多能做到/.test(t), '从 0 回到 ¥3,000 后恢复正常输出');

  console.log('\n── 负值 / 非法值 ──');
  await page.fill('#hbud', '-5');
  await page.dispatchEvent('#hbud', 'input');
  await page.waitForTimeout(150);
  t = await page.textContent('#hbudOut');
  ok(!/NaN|undefined/.test(t), '负数不产生 NaN/undefined', JSON.stringify(t.slice(0, 30)));

  ok(errs.length === 0, '全程无 JS 报错', errs.join('|') || '无');

  await browser.close();
  console.log('\n' + (fail ? '✗ ' + fail + ' 项未通过' : '✓ 全部通过'));
  process.exit(fail ? 1 : 0);
})();

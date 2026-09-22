/* CALIBER · 浏览器冒烟测试（构建后跑）
 *
 * 为什么需要它：
 *   构建自检（build_site.py 里的 12 项）只能验证「能解析的东西」——标签配对、列数、
 *   锚点、JS 语法、CSS 类是否被用到。而最近四轮的线上问题全部是它抓不到的：
 *     · 周期按钮绿框不跟随（JS 选择器指向了已改名的类，静默失效）
 *     · 移动端侧栏吸顶挡住内容、控件被挤出视野
 *     · buy/period 视图横向溢出 775px（flex 交叉轴未 stretch）
 *     · 手指停在表格上整页滑不动（overscroll-behavior:contain 吃掉手势）
 *   这四类只有「真浏览器 + 真交互」能发现。
 *
 * 用法：
 *   node site/build/smoke.js                # 桌面 + 手机两档
 *   node site/build/smoke.js --shots        # 额外输出截图
 * 依赖：playwright-core（已装在托管 node 工作区）+ 本机 Edge。
 *   需设 NODE_PATH 指向工作区 node_modules。
 * 退出码：0 = 全通过；1 = 有失败项（可直接接进 CI / 构建后钩子）。
 */
const { chromium } = require('playwright-core');
const path = require('path');
const fs = require('fs');

const EDGE = process.env.CALIBER_EDGE
  || 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const ROOT = path.resolve(__dirname, '..', '..');
const URL = 'file:///' + path.join(ROOT, 'site', 'cost.html').replace(/\\/g, '/');
const SHOTS = process.argv.includes('--shots');
const OUT = path.join(ROOT, 'harvest');
const ROWS_EXP = '47', QROWS_EXP = '39', PLATS_EXP = '7', LIBTV_Q_EXP = '7';

/* ⚠ newPage 必须定义在模块级 —— desktop()/mobile() 是顶层函数，
   IIFE 里的 const 它们看不见（第一次改就踩了这个）。 */
let browser = null;
const SEEN = () => { try { localStorage.setItem('caliber.intro.v1', '1'); } catch (e) {} };
async function newPage(opts = {}) {
  const ctx = await browser.newContext(opts);
  await ctx.addInitScript(SEEN);   /* 引导弹窗会拦截点击，逐 context 预置「已看过」 */
  return ctx.newPage();
}

const fails = [];
const log = (...a) => console.log(...a);

function check(name, cond, extra) {
  log(`  ${cond ? '✓' : '✗'} ${name}${extra ? '  ' + extra : ''}`);
  if (!cond) fails.push(name);
}

async function run(browser) {
  /* ══════════ 桌面 ══════════ */
  log('\n── 桌面 1440×900 ──');
  {
    const p = await newPage({ viewport: { width: 1440, height: 900 } });
    const errs = [];
    p.on('pageerror', e => errs.push('pageerror: ' + e.message));
    p.on('console', m => { if (m.type() === 'error') errs.push('console: ' + m.text()); });
    await p.goto(URL, { waitUntil: 'load' });
    await p.waitForTimeout(600);

    const d = await p.evaluate(() => ({
      period: document.body.dataset.p,
      segOn: [...document.querySelectorAll('#segA button.on')].map(b => b.dataset.k),
      viewOn: [...document.querySelectorAll('#viewSeg button.on')].map(b => b.dataset.v),
      panel: document.querySelector('.vpanel.on')?.dataset.view,
      kbar: document.querySelector('.kbar.on')?.dataset.kbar,
      tabs: getComputedStyle(document.querySelector('.tabs')).display,
      hamburger: getComputedStyle(document.getElementById('nBurger')).display,
      menu: getComputedStyle(document.querySelector('.nav .menu')).display,
      rows: document.querySelectorAll('.pt.on tbody tr').length,
      scrollW: document.body.scrollWidth,
      vw: document.documentElement.clientWidth,
      recRows: document.querySelectorAll('#rec tr').length,
    }));
    check('默认周期＝年付且按钮高亮同步', d.period === 'y' && d.segOn.join() === 'y');
    check('默认视图＝全档位对比', d.viewOn.join() === 'all' && d.panel === 'all');
    check('KPI 条与周期一致', d.kbar === 'y');
    check(`年付表 ${ROWS_EXP} 行`, d.rows === Number(ROWS_EXP), `${d.rows} 行`);
    check('计算器有结果行', d.recRows > 0);
    check('桌面无横向溢出', d.scrollW === d.vw, `(${d.scrollW}/${d.vw})`);
    check('桌面不显示顶部 tab / 汉堡，横向菜单可见',
      d.tabs === 'none' && d.hamburger === 'none' && d.menu !== 'none');

    // 周期切换：按钮高亮、表格行数、KPI 三处必须同时跟着变
    await p.click('#segA button[data-k="q"]');
    await p.waitForTimeout(350);
    const q = await p.evaluate(() => ({
      segOn: [...document.querySelectorAll('#segA button.on')].map(b => b.dataset.k),
      kbar: document.querySelector('.kbar.on')?.dataset.kbar,
      rows: document.querySelectorAll('.pt.on tbody tr').length,
      panel: document.querySelector('.pt.on')?.dataset.pt,
    }));
    check('切季付：按钮高亮跟随',
      q.segOn.join() === 'q', `实际 ${JSON.stringify(q.segOn)}`);
    check('切季付：KPI 条跟随', q.kbar === 'q');
    check('切季付：39 行（Higgsfield 无季付）', q.rows === 39);
    check('切季付：表格同步', q.panel === 'q');

    await p.click('#segA button[data-k="y"]');
    await p.waitForTimeout(300);
    const y = await p.evaluate(() => [...document.querySelectorAll('#segA button.on')].map(b => b.dataset.k));
    check('切回年付：按钮高亮跟随', y.join() === 'y');

    // 视图切换
    await p.click('#viewSeg button[data-v="period"]');
    await p.waitForTimeout(350);
    const v = await p.evaluate(() => ({
      panel: document.querySelector('.vpanel.on')?.dataset.view,
      sw: document.body.scrollWidth, vw: document.documentElement.clientWidth,
      rows: document.querySelectorAll('.pt.on tbody tr').length,
    }));
    check('切「先别急着下单」：面板切换', v.panel === 'period');
    check('该视图无横向溢出', v.sw === v.vw, `(${v.sw}/${v.vw})`);
    await p.click('#viewSeg button[data-v="all"]');
    await p.waitForTimeout(300);

    // 平台筛选
    const before = await p.evaluate(() => document.querySelectorAll('.pt.on tbody tr').length);
    await p.click('#platFilter .pfb[data-p="小云雀"]');
    await p.click('#platFilter .pfb[data-p="libtv"]');
    await p.waitForTimeout(350);
    const aft = await p.evaluate(() => ({
      vis: [...document.querySelectorAll('.pt.on tbody tr')].filter(r => r.style.display !== 'none').length,
      chip: document.getElementById('platN').textContent,
    }));
    check('平台筛选生效', aft.vis < before && aft.chip === `${Number(PLATS_EXP) - 2}/${PLATS_EXP}`,
      `${before}→${aft.vis} 芯片 ${aft.chip}`);
    await p.click('#platFilter .pfb[data-p="小云雀"]');
    await p.click('#platFilter .pfb[data-p="libtv"]');
    await p.waitForTimeout(250);

    const cg = await p.evaluate(() => ({
      logos: document.querySelectorAll('.pt.on .plgo').length,
      cover: (document.getElementById('coverN') || {}).textContent,
      dimmed: document.querySelectorAll('.pt.on tbody tr.out').length,
      chipLogo: document.querySelectorAll('#platFilter .pfbi').length,
    }));
    check('主表每行带平台 logo', cg.logos >= 39, `${cg.logos} 个`);
    check('单账号口径：月产 30 条时应有多档可行', /^[1-9]/.test(cg.cover), cg.cover);
    check('筛选 chip 带平台标识', cg.chipLogo === Number(PLATS_EXP), `${cg.chipLogo} 个`);
    check('覆盖率为单账号口径', !!cg.cover && cg.cover.indexOf('单账号口径') >= 0, cg.cover);

    // 元信息行：中文标签与数值之间必须有空格 —— flex 容器会裁掉文本节点首尾空白，
    // 曾导致「数据时点2026-09-21」贴在一起（用户报的重叠感）
    const vm = await p.evaluate(() => [...document.querySelectorAll('.vmeta span')]
      .map(e => e.innerText.replace(/\s+/g, ' ').trim()));
    const glued = vm.filter(t => /[\u4e00-\u9fa5][\d¥$]/.test(t));
    check('元信息标签与数值间有间隔', vm.length > 0 && glued.length === 0, glued.join(' | '));

    check('桌面无 JS 报错', errs.length === 0, errs.slice(0, 2).join(' | '));
    if (SHOTS) await p.screenshot({ path: path.join(OUT, 'smoke-desktop.png'), fullPage: false });
    await p.close();
  }

  /* ══════════ 三周期全清单页 ══════════ */
  log('\n── 三周期全清单 cycles.html ──');
  {
    const cu = URL.replace('cost.html', 'cycles.html');
    const p = await newPage({ viewport: { width: 1440, height: 950 } });
    const errs = [];
    p.on('pageerror', e => errs.push('pageerror: ' + e.message));
    p.on('console', m => { if (m.type() === 'error') errs.push('console: ' + m.text()); });
    await p.goto(cu, { waitUntil: 'load' });
    await p.waitForTimeout(700);
    const snap = () => p.evaluate(() => ({
      rows: document.querySelectorAll('#chart .crow').length,
      first: (document.querySelector('#chart .crow') || { innerText: '' }).innerText.replace(/\s+/g, ' ').trim().slice(0, 46),
      now: (document.getElementById('cycNow') || {}).textContent,
      chip: (document.getElementById('cycChip') || {}).textContent,
      platN: (document.getElementById('cycPlatN') || {}).textContent,
      segOn: [...document.querySelectorAll('#metricSeg button.on')].map(b => b.dataset.m).join(),
      logos: document.querySelectorAll('#chart .clogo').length,
      sw: document.body.scrollWidth, vw: document.documentElement.clientWidth,
      bars: [...document.querySelectorAll('#chart .cbar i')].slice(0, 3).map(i => i.style.width),
    }));
    const a = await snap();
    check(`排名图 ${ROWS_EXP} 行 + 标识`, a.rows === Number(ROWS_EXP) && a.logos === Number(ROWS_EXP));
    check('首行＝最优档', a.first.indexOf('小云雀') >= 0 && a.first.indexOf('19.30') >= 0, a.first);
    // 第 2、3 名数值可能相同（此处都是 ¥20.00），故只要求「不是全部等长」
    check('条形长度可分辨（非全部等长）', new Set(a.bars).size >= 2, a.bars.join(' / '));
    check('桌面无横向溢出', a.sw === a.vw, `(${a.sw}/${a.vw})`);

    const par = await p.evaluate(() => ({
      dots: document.querySelectorAll('#pplot .pp').length,
      lines: document.querySelectorAll('.pline, .pline path').length,
      rk1: document.querySelectorAll('#pplot .pp.rk1').length,
      logoed: document.querySelectorAll('.clogo[class*="lg-"]').length,
    }));
    check(`散点 ${ROWS_EXP} 点`, par.dots === Number(ROWS_EXP), `${par.dots} 点`);
    check('连线机制已移除（无 .pline）', par.lines === 0, `${par.lines} 个`);
    check('rank1 点有标记且唯一', par.rk1 === 1, `${par.rk1} 个`);
    check(`平台标识齐全`, par.logoed === Number(ROWS_EXP), `${par.logoed} 个`);

    await p.click('#metricSeg button[data-m="cap"]');
    await p.waitForTimeout(400);
    const b = await snap();
    check('切指标后重排（每月可生成 → 即梦超级居首）', b.segOn === 'cap' && b.first !== a.first, b.first);

    await p.click('#cycSeg button[data-k="q"]');
    await p.waitForTimeout(400);
    const c = await snap();
    check('切季付：行数与档位芯片跟随', c.rows === Number(QROWS_EXP) && c.chip.indexOf(String(QROWS_EXP)) === 0, `${c.rows} 行`);

    // 注意：季付下 Higgsfield 本来就没有档位，筛它不会改变行数 —— 要筛有季付的 libtv
    await p.click('#cycPlat .pfb[data-p="libtv"]');
    await p.waitForTimeout(350);
    const d = await snap();
    check('平台筛选生效', d.rows === Number(QROWS_EXP) - Number(LIBTV_Q_EXP)
        && d.platN === `${Number(PLATS_EXP) - 1}/${PLATS_EXP}`, `${d.rows} 行 ${d.platN}`);

    // 用户要求：选了哪些平台，帕累托就只连这些平台的点
    const pare = await p.evaluate(() => {
      const dots = [...document.querySelectorAll('#pplot .pp')];
      const plats = {};
      dots.forEach(el => { plats[el.dataset.plat || (el.querySelector('b') ? el.querySelector('b').textContent.split(' ')[0] : '')] = 1; });
      const path = document.querySelector('.pline path');
      return { n: dots.length, uniq: Object.keys(plats).length,
               hasLibtv: dots.some(el => (el.querySelector('b') || {}).textContent
                                          && el.querySelector('b').textContent.indexOf('libtv') === 0),
               seg: path ? path.getAttribute('d').split('L').length : 0 };
    });
    // 散点朝向：两个轴都按优度画，右上角必须是最优档
    // （曾经用「该周期实付」当横轴 —— 它与产能强正相关，右上角是空的，与直觉冲突）
    const ori = await p.evaluate(() => {
      const d = [...document.querySelectorAll('#pplot .pp')].map(e => ({
        x: parseFloat(e.style.left), y: parseFloat(e.style.bottom),
        t: e.querySelector('b').innerText.replace(/\s+/g, ' ').split('第')[0].trim() }));
      return {
        tr: d.filter(q => q.x > 85 && q.y > 85).map(q => q.t),
        maxX: d.reduce((a2, c) => c.x > a2.x ? c : a2, d[0]).t,
        minX: d.reduce((a2, c) => c.x < a2.x ? c : a2, d[0]).t,
        corner: !!document.querySelector('.pcorner'),
        ax0: (document.getElementById('px0') || {}).textContent || '',
        ax1: (document.getElementById('px1') || {}).textContent || '',
      };
    });
    check('右上角存在「又能做又便宜」的档位', ori.tr.length > 0, ori.tr.join(' ／ ') || '（空）');
    // 断言「方向」而不是「具体数值」——写死数值会在换周期/换平台时误报，
    // 而这里真正要保的性质是：左端＝最差、右端＝最好。
    check('横轴左端指向「更差」、右端指向「更好」', ori.ax0.indexOf('更少') > 0 && ori.ax1.indexOf('更多') > 0,
      `${ori.ax0} | ${ori.ax1}`);
    check('有「最好 ↗」角标', ori.corner === true);

    check('散点跟随平台筛选（点数减少）', pare.n === Number(QROWS_EXP) - Number(LIBTV_Q_EXP), `${pare.n} 点`);
    check('散点已排除被筛掉的平台', pare.hasLibtv === false);


    // 散点的 rank1 必须与上方列表第一名一致（同指标、同比较器）
    for (const m of ['cost', 'cap']) {
      await p.click(`#metricSeg button[data-m="${m}"]`);
      await p.waitForTimeout(360);
      // ⚠ 必须读 .cname —— .crow 里没有 <b>，之前读 '.crow b' 拿到空串，
      //   indexOf('') 恒为 0 → 断言永远通过，等于没测。已改为真比对。
      const rk = await p.evaluate(() => {
        const first = document.querySelector('#chart .crow .cname');
        const dot = document.querySelector('#pplot .pp.rk1 b');
        const norm = t => (t || '').replace(/\s+/g, ' ').trim();
        return {
          list: norm(first && first.textContent),
          dot: norm(dot && dot.innerText.split('\n')[0]),
        };
      });
      const ok1 = !!rk.list && !!rk.dot && rk.dot.indexOf(rk.list) === 0;
      check(`散点 rank1 与列表第一名一致（${m}）`, ok1, `列表「${rk.list}」/ 散点「${rk.dot}」`);
    }

    check('该页无 JS 报错', errs.length === 0, errs.slice(0, 2).join(' | '));
    if (SHOTS) await p.screenshot({ path: path.join(OUT, 'smoke-cycles.png') });
    await p.close();
  }

  /* ══════════ 新人引导弹窗（独立 context：干净的 localStorage）══════════ */
  log('\n── 新人引导弹窗 ──');
  {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 950 } });
    const q = await ctx.newPage();
    const e5 = []; q.on('pageerror', e => e5.push(e.message));
    await q.goto(URL, { waitUntil: 'load' });
    await q.waitForTimeout(1300);
    const a1 = await q.evaluate(() => {
      const el = document.getElementById('intro');
      return { on: el.classList.contains('on'), lock: document.body.classList.contains('ibody'),
               steps: el.querySelectorAll('.is').length,
               prev: getComputedStyle(el.querySelector('.iprev')).visibility,
               next: el.querySelector('.inext').textContent };
    });
    check('首次访问弹出引导且锁滚动', a1.on === true && a1.lock === true);
    check('引导为 3 步、首步无「上一步」', a1.steps === 3 && a1.prev === 'hidden', `${a1.steps} 步`);
    await q.click('.inext'); await q.waitForTimeout(280);
    await q.click('.inext'); await q.waitForTimeout(280);
    const a2 = await q.evaluate(() => document.querySelector('.inext').textContent);
    check('末步按钮变为「开始看」', a2 === '开始看', a2);
    await q.click('.inext'); await q.waitForTimeout(400);
    const a3 = await q.evaluate(() => ({
      on: document.getElementById('intro').classList.contains('on'),
      lock: document.body.classList.contains('ibody'),
      flag: localStorage.getItem('caliber.intro.v1'),
    }));
    check('关闭后解锁并写入标记', a3.on === false && a3.lock === false && a3.flag === '1');
    await q.reload(); await q.waitForTimeout(1200);
    check('再次访问不再打扰',
      (await q.evaluate(() => document.getElementById('intro').classList.contains('on'))) === false);
    await q.click('#introAgain'); await q.waitForTimeout(350);
    check('页脚「新手引导」可重看',
      (await q.evaluate(() => document.getElementById('intro').classList.contains('on'))) === true);
    check('引导弹窗无 JS 报错', e5.length === 0, e5.slice(0, 2).join(' | '));
    await ctx.close();
  }

  /* ══════════ 术语引导层 ══════════ */
  log('\n── 术语引导（成本页 / 术语表页）──');
  {
    const p2 = await newPage({ viewport: { width: 1440, height: 950 } });
    const e3 = []; p2.on('pageerror', e => e3.push(e.message));
    await p2.goto(URL, { waitUntil: 'load' });
    await p2.waitForTimeout(600);
    const g = await p2.evaluate(() => {
      const t = [...document.querySelectorAll('.tm')];
      const e = t.find(x => x.offsetParent !== null);
      let hover = false;
      if (e) { e.dispatchEvent(new MouseEvent('mouseenter')); hover = !!document.querySelector('.tip.on'); e.dispatchEvent(new MouseEvent('mouseleave')); }
      return { n: t.length, hover, nav: [...document.querySelectorAll('.nav .menu a')].some(a2 => a2.textContent.includes('术语表')) };
    });
    check('术语已标记且悬停出解释', g.n >= 5 && g.hover === true, `${g.n} 处`);
    check('NAV 含术语表入口', g.nav === true);

    const p3 = await newPage({ viewport: { width: 1440, height: 950 } });
    const e4 = []; p3.on('pageerror', e => e4.push(e.message));
    await p3.goto(URL.replace('cost.html', 'glossary.html'), { waitUntil: 'load' });
    await p3.waitForTimeout(500);
    const gl = await p3.evaluate(() => ({
      n: document.querySelectorAll('.gterm').length,
      minLen: Math.min(...[...document.querySelectorAll('.gterm .gl')].map(e => e.textContent.length)),
      anchorOK: [...document.querySelectorAll('.gterm')].every(e => e.id),
    }));
    check('术语表条目齐全且都有详解', gl.n >= 15 && gl.minLen > 60, `${gl.n} 条 · 最短 ${gl.minLen} 字`);
    check('每条术语都有锚点（可从页面深链）', gl.anchorOK === true);
    check('术语表页无 JS 报错', e3.length === 0 && e4.length === 0);
    if (SHOTS) await p3.screenshot({ path: path.join(OUT, 'smoke-glossary.png') });
    await p2.close(); await p3.close();
  }

  /* ══════════ 汉堡菜单：四页必须都能用 ══════════ */
  log('\n── 汉堡菜单（四页）──');
  for (const pg of ['index.html', 'cost.html', 'cycles.html', 'leaderboard-vlm.html']) {
    const q = await newPage({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
    const e2 = []; q.on('pageerror', e => e2.push(e.message));
    await q.goto(URL.replace('cost.html', pg), { waitUntil: 'load' });
    await q.waitForTimeout(420);
    await q.click('#nBurger');
    await q.waitForTimeout(300);
    const st = await q.evaluate(() => ({
      open: document.querySelector('.nav').classList.contains('open'),
      drop: getComputedStyle(document.getElementById('nDrop')).display,
      items: document.querySelectorAll('#nDrop a').length,
      total: document.querySelectorAll('.nav .menu a').length,
    }));
    await q.mouse.click(195, 790); await q.waitForTimeout(280);
    const shut = await q.evaluate(() => document.querySelector('.nav').classList.contains('open'));
    check(`${pg} 汉堡可开可合`,
      st.open === true && st.drop !== 'none' && st.items >= 4 && shut === false && e2.length === 0,
      `open=${st.open} drop=${st.drop} 项=${st.items} 收起=${!shut}`);
    await q.close();
  }

  /* ══════════ 首页散点图 ══════════ */
  log('\n── 首页 index.html（帕累托散点）──');
  {
    const p = await newPage({ viewport: { width: 1440, height: 950 } });
    const errs = [];
    p.on('pageerror', e => errs.push('pageerror: ' + e.message));
    await p.goto(URL.replace('cost.html', 'index.html'), { waitUntil: 'load' });
    await p.waitForTimeout(600);
    const h = await p.evaluate(() => {
      const box = document.querySelector('#pplot');
      const i = box ? box.querySelector('.pp i') : null;
      return {
        dots: document.querySelectorAll('#pplot .pp').length,
        front: document.querySelectorAll('#pplot .pp.on').length,
        path: (() => { const e = document.querySelector('.pline path'); return e ? e.getAttribute('d').split('L').length : 0; })(),
        logoW: i ? Math.round(i.getBoundingClientRect().width) : 0,
        top: box ? Math.round(box.getBoundingClientRect().top) : -1,
        vh: window.innerHeight,
        entries: document.querySelectorAll('.entry').length,
        sw: document.body.scrollWidth, vw: document.documentElement.clientWidth,
      };
    });
    // 用户裁定：首页没有选择菜单，散点放那里没有意义 → 已移除
    check('首页不再有散点图', h.dots === 0 && h.front === 0, `${h.dots} 点`);
    check('首页板块＝2 个入口', h.entries === 2, `${h.entries} 个`);
    check('首页无横向溢出', h.sw === h.vw, `(${h.sw}/${h.vw})`);
    check('首页无 JS 报错', errs.length === 0, errs.slice(0, 2).join(' | '));
    if (SHOTS) await p.screenshot({ path: path.join(OUT, 'smoke-home.png') });
    await p.close();
  }

  /* ══════════ 手机 ══════════ */
  log('\n── 手机 430×900 ──');
  {
    const p = await newPage({ viewport: { width: 430, height: 900 }, hasTouch: true, isMobile: true });
    const errs = [];
    p.on('pageerror', e => errs.push('pageerror: ' + e.message));
    p.on('console', m => { if (m.type() === 'error') errs.push('console: ' + m.text()); });
    await p.goto(URL, { waitUntil: 'load' });
    await p.waitForTimeout(700);

    const m = await p.evaluate(() => {
      const rows = [...document.querySelectorAll('.pt.on tbody tr')];
      return {
        tabs: getComputedStyle(document.querySelector('.tabs')).display,
        tabN: document.querySelectorAll('.tabs button').length,
        sgView: getComputedStyle(document.getElementById('sgView')).display,
        hamburger: getComputedStyle(document.getElementById('nBurger')).display,
        menu: getComputedStyle(document.querySelector('.nav .menu')).display,
        cardH: rows.length ? Math.round(rows.reduce((a, c) => a + c.getBoundingClientRect().height, 0) / rows.length) : 0,
        screens: +(document.documentElement.scrollHeight / innerHeight).toFixed(1),
        scrollW: document.body.scrollWidth,
        vw: document.documentElement.clientWidth,
        sidePos: getComputedStyle(document.querySelector('.side')).position,
        sideVisible: document.querySelector('.side').getBoundingClientRect().top < innerHeight
          && getComputedStyle(document.querySelector('.side')).visibility !== 'hidden',
        btnH: Math.round(document.getElementById('moOpen').getBoundingClientRect().height),
        btnBg: getComputedStyle(document.getElementById('moOpen')).backgroundColor,
        theadHidden: getComputedStyle(document.querySelector('.pt.on thead')).display === 'none',
        rowDisplay: getComputedStyle(rows[0]).display,
      };
    });
    check('顶部 tab 常驻可见（不藏进汉堡）', m.tabs === 'flex' && m.tabN === 2);
    check('汉堡菜单在手机端可见、横向菜单隐藏', m.hamburger !== 'none' && m.menu === 'none');
    check('侧栏「查看方式」不重复显示', m.sgView === 'none');
    check('抽屉默认收起（position:fixed）', m.sidePos === 'fixed' && m.sideVisible === false);
    check('卡片形态生效', m.theadHidden === true && m.rowDisplay === 'grid');
    check('卡片高度 ≤110px', m.cardH > 0 && m.cardH <= 110, `${m.cardH}px`);
    // 上限随平台数增长：每多一个平台就多 3-4 张卡片，写死 8 屏会在加平台时误报
    check(`整页 ≤${Math.ceil(Number(PLATS_EXP) * 1.3)} 屏`, m.screens <= Number(PLATS_EXP) * 1.3, `${m.screens} 屏`);
    check('手机无横向溢出', m.scrollW === m.vw, `(${m.scrollW}/${m.vw})`);
    check('「调整」按钮够大且高对比',
      m.btnH >= 38 && m.btnBg.includes('209, 254, 23'), `${m.btnH}px ${m.btnBg}`);

    // 卡片区滑动 —— 这条专门防「overscroll-behavior / overflow 吃手势」那类 bug
    await p.evaluate(() => {
      const w = document.querySelector('.pt.on');
      window.scrollTo(0, window.scrollY + w.getBoundingClientRect().top + 400);
    });
    await p.waitForTimeout(250);
    const y0 = await p.evaluate(() => window.scrollY);
    await p.mouse.move(215, 450);
    for (let i = 0; i < 5; i++) { await p.mouse.wheel(0, 600); await p.waitForTimeout(90); }
    const y1 = await p.evaluate(() => window.scrollY);
    check('手指停在卡片上也能整页滑动', y1 - y0 > 100, `位移 ${Math.round(y1 - y0)}px`);

    await p.evaluate(() => window.scrollTo(0, 1e9));
    await p.waitForTimeout(250);
    const bot = await p.evaluate(() => ({
      reached: Math.round(window.scrollY + window.innerHeight),
      total: document.documentElement.scrollHeight,
    }));
    check('能滚到页底', bot.reached >= bot.total - 4, `${bot.reached}/${bot.total}`);

    await p.evaluate(() => window.scrollTo(0, 0));
    await p.waitForTimeout(200);

    // 顶部 tab 切视图
    await p.click('.tabs button[data-v="period"]');
    await p.waitForTimeout(400);
    const tv = await p.evaluate(() => ({
      panel: document.querySelector('.vpanel.on')?.dataset.view,
      tabOn: [...document.querySelectorAll('.tabs button.on')].map(b => b.dataset.v).join(),
      sw: document.body.scrollWidth, vw: document.documentElement.clientWidth,
    }));
    check('顶部 tab 切视图并高亮', tv.panel === 'period' && tv.tabOn === 'period');
    check('该视图手机端无横向溢出', tv.sw === tv.vw, `(${tv.sw}/${tv.vw})`);
    await p.click('.tabs button[data-v="all"]');
    await p.waitForTimeout(300);

    // 抽屉
    // 阅读路径条：常驻、可关、记住选择
    const gd = await p.evaluate(() => {
      const g = document.getElementById('guide');
      if(!g) return { none: true };
      const r = g.getBoundingClientRect();
      return { vis: getComputedStyle(g).display !== 'none', steps: g.querySelectorAll('.g-step').length,
               x: !!document.getElementById('guideX'), h: Math.round(r.height),
               beforeKpi: !!(g.compareDocumentPosition(document.querySelector('.kbar.on')) & Node.DOCUMENT_POSITION_FOLLOWING) };
    });
    check('阅读路径条存在且在结论之后', gd.vis === true && gd.steps === 3 && gd.beforeKpi === true,
      `${gd.steps} 步 · 高 ${gd.h}px`);
    await p.click('#guideX'); await p.waitForTimeout(300);
    const gd2 = await p.evaluate(() => ({
      vis: getComputedStyle(document.getElementById('guide')).display !== 'none',
      flag: localStorage.getItem('caliber.guide.v1'),
    }));
    check('「不再提示」可关闭并记住', gd2.vis === false && gd2.flag === '0');

    await p.click('#moOpen');
    await p.waitForTimeout(450);
    const sh = await p.evaluate(() => ({
      open: document.querySelector('.side').classList.contains('open'),
      scrim: document.getElementById('scrim').classList.contains('open'),
    }));
    // ① KPI 条改成横向滑动一行，把下方反查与表格提前进首屏
    //   （用户反馈：滚了两屏还不知道下面有数据表）
    const kbf = await p.evaluate(() => {
      const kb = document.querySelector('.kbar.on');
      return { flex: getComputedStyle(kb).display === 'flex',
               scrollable: kb.scrollWidth > kb.clientWidth + 4,
               h: Math.round(kb.getBoundingClientRect().height),
               recTop: Math.round(document.querySelector('.tw-rec').getBoundingClientRect().top + window.scrollY),
               vh: innerHeight };
    });
    check('KPI 条改为横滑一行（高度受控）', kbf.flex && kbf.scrollable && kbf.h < 200, `高 ${kbf.h}px`);
    // 原断言是「反查卡 ≤1.2 屏」，意图是「用户看不到下面还有内容」。
    // 现在首屏由【三周期结论条】回答「买哪个」，反查退为第二层工具 ——
    // 故改为断言「首屏能看到结论条的答案」+ 反查不被推到 3 屏外。
    const ans = await p.evaluate(() => {
      const c = document.querySelector('.conc-c .cw');
      const r = c.getBoundingClientRect();
      return { txt: c.innerText.replace(/\s+/g, ' ').trim(), top: Math.round(r.top + window.scrollY), vh: innerHeight };
    });
    check('首屏内可见「年付买谁」的答案', ans.top < ans.vh, `${ans.txt} @ ${ans.top}px / 视口 ${ans.vh}`);
    check('反查卡未被推到 2.4 屏外', kbf.recTop < kbf.vh * 2.4, `${kbf.recTop}px`);

    // ② 反查表改卡片式，不再横滑
    const recf = await p.evaluate(() => {
      const r = document.querySelector('.tw-rec');
      const td = r.querySelector('tbody td[data-l]');
      return { fits: r.scrollWidth <= r.clientWidth + 4,
               block: getComputedStyle(r.querySelector('tbody td')).display === 'block',
               label: td ? td.getAttribute('data-l') : '' };
    });
    check('反查表卡片式、不横滑', recf.fits && recf.block, `标签「${recf.label}」`);

    // 两个区块结构必须对称：每行都带 data-l 标签
    // （JS 重建 #rec 时曾漏掉，导致「组合订阅」的值没有标签、看着和上面那块不一样）
    const sym = await p.evaluate(() => {
      const rs = [...document.querySelectorAll('.tw-rec tbody tr')].map(tr =>
        [...tr.querySelectorAll('td')].map(td => td.getAttribute('data-l') || '-'));
      return { rows: rs.length, labels: rs.map(r => r.join('/')), same: rs.length > 1 && rs.every(r => r.join('/') === rs[0].join('/')) };
    });
    check('反查表两块结构对称（每行都带标签）', sym.same === true, sym.labels.join('  ‖  '));

    // 反查卡要与「全部档位排名」同样紧凑 —— 上一版纵向大卡约 190px/张，
    // 用户反馈「结构好乱，而且太大了」。
    const rh = await p.evaluate(() => {
      const rec = [...document.querySelectorAll('.tw-rec tbody tr')].map(t => Math.round(t.getBoundingClientRect().height));
      const main = [...document.querySelectorAll('.tw-main.on tbody tr')].slice(0, 3).map(t => Math.round(t.getBoundingClientRect().height));
      return { rec, main, max: Math.max.apply(null, rec), same: rec.length > 0 };
    });
    check('反查卡高度与排名卡同级（≤150px）', rh.same && rh.max <= 150,
      `反查 ${rh.rec.join('/')}px ｜ 排名 ${rh.main.join('/')}px`);

    // 三周期结论条：一条讲清年付/月付买谁、季付要不要考虑
    const cc = await p.evaluate(() => {
      const cols = [...document.querySelectorAll('.conc-c')];
      const foot = document.getElementById('concF');
      return { n: cols.length,
               y: cols[0] ? cols[0].innerText.replace(/\s+/g, ' ') : '',
               q: cols[2] ? cols[2].innerText.replace(/\s+/g, ' ') : '',
               foot: foot ? foot.innerText.replace(/\s+/g, ' ') : '',
               h: Math.round(document.querySelector('.conc').getBoundingClientRect().height) };
    });
    check('结论条三列且年付给出冠军', cc.n === 3 && cc.y.indexOf('19.30') > 0, cc.y.slice(0, 30));
    check('季付列明确写出「不建议」的根据', cc.q.indexOf('不建议') > 0 && cc.q.indexOf('没赢过') > 0);
    check('结论条动态行含当前月产量', cc.foot.indexOf('月产量') > 0 && cc.foot.indexOf('最省') > 0, cc.foot.slice(0, 40));
    check('结论条手机端高度受控（≤420px）', cc.h <= 420, `${cc.h}px`);

    check('点「调整」抽屉弹出', sh.open === true && sh.scrim === true);
    // 抽屉必须自带关闭出口 —— 它会盖住底部「调整」按钮，遮罩只剩顶部一条，
    // 没有 ✕ 的话用户找不到任何方式退出（用户实测被卡住）
    const sx = await p.evaluate(() => {
      const x = document.getElementById('sheetX');
      if (!x) return { ok: false };
      const r = x.getBoundingClientRect();
      const side = document.querySelector('.side').getBoundingClientRect();
      return { ok: true, visible: r.top >= 0 && r.bottom <= innerHeight,
               size: Math.round(r.width), sheetTop: Math.round(side.top), vh: innerHeight };
    });
    check('抽屉有关闭按钮且可见', sx.ok && sx.visible && sx.size >= 30,
      `✕ ${sx.size}px · 抽屉顶 ${sx.sheetTop}/${sx.vh}`);
    check('抽屉不占满整屏（留下可点的遮罩）', sx.sheetTop > sx.vh * 0.15,
      `抽屉顶 ${sx.sheetTop} / 视口 ${sx.vh}`);

    // 抽屉默认半开（不挡视线），且把手必须能拖动
    const pk = await p.evaluate(() => {
      const s = document.querySelector('.side'); const r = s.getBoundingClientRect();
      return { peek: s.classList.contains('peek'), h: Math.round(r.height), vh: innerHeight };
    });
    check('抽屉默认半开（≤50% 视口）', pk.peek === true && pk.h <= pk.vh * 0.5,
      `${Math.round(pk.h / pk.vh * 100)}%`);
    const dg = await p.evaluate(async () => {
      const s = document.querySelector('.side'), hd = document.querySelector('.sheet-hd');
      const h0 = s.getBoundingClientRect().height;
      const r = hd.getBoundingClientRect();
      const cy = r.top + r.height / 2;
      const ev = (t, y) => hd.dispatchEvent(new PointerEvent(t, { clientY: y, bubbles: true, pointerId: 1 }));
      ev('pointerdown', cy);
      const dragging = s.classList.contains('dragging');
      for (let i = 1; i <= 6; i++) ev('pointermove', cy - i * 30);
      const h1 = s.getBoundingClientRect().height;
      ev('pointerup', cy - 180);
      await new Promise(r2 => setTimeout(r2, 420));
      return { dragging, h0: Math.round(h0), h1: Math.round(h1),
               h2: Math.round(s.getBoundingClientRect().height), peek: s.classList.contains('peek') };
    });
    // 阈值取 +20：抽屉高度受【内容自然高度】限制，成本页内容只到 425px，
    // 上拉 180px 也只能涨到 425 —— 断言要的是「拖动能改变高度」，不是「能拖无限高」
    check('把手可拖动（上拉变高）', dg.h1 > dg.h0 + 20, `${dg.h0} → ${dg.h1}`);
    check('拖拽中有 dragging 态', dg.dragging === true);
    check('松手吸附不回弹', dg.h2 >= dg.h1 - 30, `松手后 ${dg.h2}`);
    await p.mouse.click(215, 60);
    await p.waitForTimeout(400);
    const sh2 = await p.evaluate(() => document.querySelector('.side').classList.contains('open'));
    check('点遮罩可关抽屉', sh2 === false);

    check('手机无 JS 报错', errs.length === 0, errs.slice(0, 2).join(' | '));
    if (SHOTS) await p.screenshot({ path: path.join(OUT, 'smoke-mobile.png') });
    await p.close();
  }

  /* ══════════ 四页手机端导航（汉堡菜单） ══════════
     这条断言的存在理由：汉堡按钮由共享 nav() 渲染在四页，但它的监听曾经只写在
     COST_JS 里（仅 cost/cycles 注入）。首页与排行榜页因此「有按钮、没监听」，
     手机上点了完全不动 —— 而旧断言只查了「按钮可见」（且按钮在桌面 display:none），
     于是测试全绿、线上照坏。教训：可见 ≠ 可用，交互必须真点一次。 */
  log('\n── 四页汉堡菜单（手机 390×844）──');
  for (const f of ['index.html', 'cost.html', 'cycles.html', 'leaderboard-vlm.html']) {
    const p = await newPage({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });
    const errs = [];
    p.on('pageerror', e => errs.push('pageerror: ' + e.message));
    await p.goto(URL.replace('cost.html', f), { waitUntil: 'load' });
    await p.waitForTimeout(400);

    await p.click('#nBurger');
    await p.waitForTimeout(300);
    const o = await p.evaluate(() => ({
      open: document.querySelector('.nav').classList.contains('open'),
      drop: getComputedStyle(document.getElementById('nDrop')).display,
      aria: document.getElementById('nBurger').getAttribute('aria-expanded'),
      items: document.querySelectorAll('#nDrop nav a').length,
      // 展开后必须在视口内 —— 只 toggle 类名却飘到屏外也算不可用
      top: Math.round(document.getElementById('nDrop').getBoundingClientRect().top),
    }));
    check(`${f}：点汉堡可展开（导航项齐全且在视口内）`,
      o.open === true && o.drop === 'block' && o.aria === 'true' && o.items >= 4 && o.top < 844,
      `open=${o.open} drop=${o.drop} aria=${o.aria} 项=${o.items} top=${o.top}`);

    await p.evaluate(() => document.documentElement.dispatchEvent(new MouseEvent('click', { bubbles: true })));
    await p.waitForTimeout(250);
    const c = await p.evaluate(() => ({
      open: document.querySelector('.nav').classList.contains('open'),
      aria: document.getElementById('nBurger').getAttribute('aria-expanded'),
    }));
    check(`${f}：点空白处收起且 aria 复位`, c.open === false && c.aria === 'false');

    check(`${f}：无 JS 报错`, errs.length === 0, errs.slice(0, 2).join(' | '));
    await p.close();
  }
}

(async () => {
  if (!fs.existsSync(EDGE)) {
    console.error('找不到 Edge：' + EDGE + '\n可用 CALIBER_EDGE 环境变量指定浏览器路径。');
    process.exit(2);
  }
  browser = await chromium.launch({ executablePath: EDGE, headless: true });

  try {
    await run(browser);
  } finally {
    await browser.close();
  }
  log('\n' + '='.repeat(60));
  if (fails.length) {
    log(`冒烟测试未通过：${fails.length} 项`);
    fails.forEach(f => log('  ✗ ' + f));
    process.exit(1);
  }
  log('冒烟测试全部通过（桌面 + 手机两档）');
})().catch(e => { console.error('FATAL', e.message); process.exit(2); });

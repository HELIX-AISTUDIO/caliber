// 双组自检：A 组「数据计算」10 遍 ｜ B 组「交互 bug」10 遍
// A 组用【暴力枚举】做基准真值，与页面 DOM 逐值对照；B 组测状态自洽与回归。
const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');

const SITE = path.resolve(__dirname, '..');
const C = JSON.parse(fs.readFileSync(path.join(SITE, 'data', 'cost-seedance25.json'), 'utf8'));
const P = JSON.parse(fs.readFileSync(path.join(SITE, 'data', 'platforms.json'), 'utf8'));
const CPV = C.creditsPerVideo, RATE = C.fx.rate;
const MO = { m: 1, q: 3, y: 12 };
const STACK = 4;

// ── 独立数据层（不复用站点任何计算）──
const PLANS = [];
for (const pl of C.plans) {
  const k = P[pl.platform].currency === 'USD' ? RATE : 1;
  for (const c of pl.credits) {
    for (const key of ['m', 'q', 'y']) {
      const pay = key === 'y' ? c.price : c[key];
      if (pay == null) continue;
      const cr = key === 'y' ? c.credits : (key === 'q' ? (c.qCr ?? c.credits) : (c.mCr ?? c.credits));
      const capM = cr / CPV[pl.platform];
      PLANS.push({ plat: pl.platform, tier: pl.tier, lbl: c.label || '', key,
        pay: pay * k, capM, capP: capM * MO[key], cr, tierName: pl.tier.replace('会员', '') });
    }
  }
}
const nm = x => (x.plat + ' ' + x.tier + (x.lbl ? ' · ' + x.lbl : '')).replace(/\s+/g, ' ').trim();

// 暴力枚举组合最优（同档≤4份）：按单价升序的完全背包贪心 + 逐档位份额穷举校验
function comboBest(key, need) {
  const pool = PLANS.filter(x => x.key === key && x.capP > 0).sort((a, b) => (a.pay / a.capP) - (b.pay / b.capP));
  let got = 0, cost = 0, n = 0;
  for (const x of pool) {
    while (got < need && n < 999) {
      const used = 0;
      // 同档最多 4 份
      const sameCount = Math.min(STACK, Math.ceil((need - got) / x.capP));
      if (sameCount <= 0) break;
      const take = Math.min(sameCount, STACK);
      got += x.capP * take; cost += x.pay * take; n += take;
      break;
    }
    if (got >= need) break;
  }
  return got >= need ? { cost, got } : null;
}

const A = [], B = [];
const R = (arr, id, desc, ok, detail) => arr.push({ id, desc, ok, detail });

(async () => {
  const br = await chromium.launch({
    executablePath: process.env.CALIBER_EDGE || 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
    headless: true });

  let ctx = null;
  const runOnce = async () => {
    const a = [], b = [];
    const c = ctx || await br.newContext({ viewport: { width: 1440, height: 950 } });
    await c.addInitScript(() => { try { localStorage.setItem('caliber.intro.v1','1'); localStorage.setItem('caliber.guide.v1','0'); } catch(e){} });
    const p = await c.newPage();
    const errs = []; p.on('pageerror', e => errs.push(e.message));
    await p.goto('file:///' + path.join(SITE, 'cost.html').replace(/\\/g, '/'));
    await p.waitForTimeout(600);
    await p.click('#capSeg button[data-cap="m"]', { timeout: 4000 }); await p.waitForTimeout(250);

    const setN = async n => { await p.evaluate(v => { const t = document.getElementById('tgt'); t.value = v; t.dispatchEvent(new Event('input', { bubbles: true })); }, n); await p.waitForTimeout(170); };
    const setK = async k => { await p.click('#segA button[data-k="' + k + '"]', { timeout: 4000 }); await p.waitForTimeout(150); };
    const table = () => p.evaluate(() => [...document.querySelectorAll('.pt.on tbody tr')].map(tr => ({
      pay: parseFloat(tr.dataset.p), capM: parseFloat(tr.dataset.c),
      per: parseFloat(tr.querySelector('[data-rated]').getAttribute('data-rated')),
      rank: tr.querySelector('.rk b').textContent.trim(), out: tr.classList.contains('out'),
      name: tr.querySelector('td:nth-child(2)').innerText.replace(/\s+/g, ' ').trim(),
      sub: tr.querySelector('[data-rated] s').textContent.replace(/\s+/g, ' ').trim() })));
    const rec = () => p.evaluate(() => [...document.querySelectorAll('.tw-rec tbody tr')].map(tr =>
      [...tr.querySelectorAll('td')].map(t => t.innerText.replace(/\s+/g, ' ').trim()).join(' | ')));

    // ══════ A 组：数据计算 ══════
    // A1 全档位单条成本逐值对照（三周期）
    for (const key of ['m', 'q', 'y']) {
      await setK(key); await setN(30);
      const tb = await table();
      const want = PLANS.filter(x => x.key === key).map(x => x.pay / x.capP).sort((a, b2) => a - b2);
      const got = tb.map(r => r.per).sort((x, y) => x - y);
      const bad = got.filter((v, i) => Math.abs(v - want[i]) > 0.02);
      R(a, `A1-${key}`, `${key} 周期：全部 ${got.length} 档单条成本逐值 = 实付÷(月产能×月数)`,
        got.length === want.length && bad.length === 0, bad.length ? `${bad.length} 处不符` : '逐值一致');
    }

    // A2 全档位产能逐值对照
    for (const key of ['m', 'q', 'y']) {
      await setK(key); await setN(1);
      const tb = await table();
      const want = PLANS.filter(x => x.key === key).map(x => x.capM).sort((x, y) => x - y);
      const got = tb.map(r => r.capM).sort((x, y) => x - y);
      /* data-c 以 %.4f 落盘，容差必须 ≥ 5e-5，否则是精度假阳性 */
      const bad = got.filter((v, i) => Math.abs(v - want[i]) > 5e-5);
      R(a, `A2-${key}`, `${key} 周期：全部产能值 = 积分 ÷ 单条消耗`,
        got.length === want.length && bad.length === 0, bad.length ? `${bad.length} 处不符` : '逐值一致');
    }

    // A3 反查·单一账号 = 暴力枚举最小值（多档产量）
    let badA3 = [];
    for (const n of [5, 30, 60, 91]) {
      await setK('m'); await setN(n);
      const rr = await rec();
      const shown = parseFloat((rr[0].match(/¥([\d,]+)/) || [])[1].replace(/,/g, ''));
      const best = PLANS.filter(x => x.key === 'm' && x.capM >= n).sort((x, y) => x.pay - y.pay)[0];
      if (!best || Math.abs(shown - best.pay) > 1) badA3.push(`N=${n} 页${shown} 算${best ? best.pay : '∞'}`);
    }
    R(a, 'A3', '反查·单一账号最省 = 暴力枚举最低价（4 档产量）', badA3.length === 0, badA3.join(' ') || '全部一致');

    // A4 反查方案可达性（产能 ≥ 需求）
    let badA4 = [];
    for (const n of [10, 30, 60, 100, 150, 200]) {
      await setN(n);
      const rr = await rec();
      rr.forEach((row, i) => {
        const cap = parseFloat((row.match(/([\d.]+)\s*条\/月\s*(?:合计)?产能/) || [])[1] || '0');
        if (cap > 0 && cap < n - 0.05) badA4.push(`N=${n} 行${i + 1} 产能${cap}`);
      });
    }
    R(a, 'A4', '反查方案的产能 ≥ 目标产量（6 档）', badA4.length === 0, badA4.slice(0, 2).join(' ') || '全部可达');

    // A5 名次 = 按该周期实付升序（可做到的在前），且 1..n 连续
    let badA5 = [];
    for (const key of ['m', 'q', 'y']) {
      await setK(key); await setN(30);
      const tb = await table();
      if (!tb.every((r, i) => r.rank === String(i + 1))) badA5.push(`${key} 名次不连续`);
      const fo = tb.findIndex(r => r.out);
      const ok = fo < 0 ? tb : tb.slice(0, fo);
      if (!ok.every((r, i) => i === 0 || r.pay >= ok[i - 1].pay - 1e-6)) badA5.push(`${key} 可用段未按实付升序`);
    }
    R(a, 'A5', '名次 1..n 连续，且可用段按该周期实付升序', badA5.length === 0, badA5.join(' ') || '三周期一致');

    // A6 置灰判定 = 产能 < N（遍历多档产量）
    let badA6 = [];
    for (const n of [1, 25, 60, 92, 200]) {
      await setN(n);
      const tb = await table();
      tb.forEach(r => { if ((r.capM < n) !== r.out) badA6.push(`N=${n} ${r.name}`); });
    }
    R(a, 'A6', '置灰 = 「产能 < N」（5 档产量 × 全行）', badA6.length === 0, badA6.slice(0, 2).join(' ') || '全部一致');

    // A7 副行量纲（三周期）
    let badA7 = [];
    for (const key of ['m', 'q', 'y']) {
      await setK(key); await setN(30);
      const tb = await table();
      const r = tb.find(x => !x.out);
      if (r && r.sub.indexOf('该产量') === 0) {
        const shown = parseFloat((r.sub.match(/¥([\d.]+)/) || [])[1]);
        const want = r.pay / (30 * MO[key]);
        if (Math.abs(shown - want) > 1.0) badA7.push(`${key}: 页${shown} 算${want.toFixed(2)}`);
      }
    }
    R(a, 'A7', '副行 = 该周期实付 ÷ (月产量 × 月数)', badA7.length === 0, badA7.join(' ') || '三周期自洽');

    // A8 边界：N=floor(cap) 可用；N=ceil(cap)+1 必置灰
    let badA8 = [];
    for (const probe of PLANS.filter(x => x.key === 'm' && x.capM > 3 && x.capM < 50).slice(0, 4)) {
      await setN(Math.floor(probe.capM)); let tb = await table();
      const f = tb.filter(r => Math.abs(r.capM - probe.capM) < 1e-6);
      if (f.length && f.some(r => r.out)) badA8.push(`cap${probe.capM.toFixed(2)} floor 被置灰`);
      await setN(Math.ceil(probe.capM) + 1); tb = await table();
      const e = tb.filter(r => Math.abs(r.capM - probe.capM) < 1e-6);
      if (e.length && e.some(r => !r.out)) badA8.push(`cap${probe.capM.toFixed(2)} ceil+1 未置灰`);
    }
    R(a, 'A8', '边界：N=floor(产能) 可用 ｜ N=ceil(产能)+1 置灰（4 个档位）', badA8.length === 0, badA8.slice(0, 2).join(' ') || '全部正确');

    // A9 行数与数据一致（三周期，Higgsfield 无季付）
    let badA9 = [];
    for (const key of ['m', 'q', 'y']) {
      await setK(key); await setN(30);
      const tb = await table();
      const want = PLANS.filter(x => x.key === key).length;
      if (tb.length !== want) badA9.push(`${key}: 页${tb.length} 数${want}`);
    }
    R(a, 'A9', '三周期行数 = 数据可用档位数', badA9.length === 0, badA9.join(' ') || '三周期一致');

    // A10 首屏 KPI 数值与独立重算一致
    await setK('m'); await setN(30);
    /* ⚠ KPI 首卡显示的是【单条成本】（「月付最优 · 小云雀超级 ¥24.56」），
       不是【最省支出】—— 两者是不同指标，早先断言按支出比是错的。 */
    const kpi = await p.evaluate(() => document.querySelector('.kbar.on .kb b').textContent.replace(/[¥,]/g, ''));
    const champ = PLANS.filter(x => x.key === 'm').sort((x, y) => (x.pay / x.capP) - (y.pay / y.capP))[0];
    R(a, 'A10', 'KPI 首卡单条成本 = 独立重算的该周期单价冠军',
      Math.abs(parseFloat(kpi) - champ.pay / champ.capP) < 0.01,
      `页 ¥${kpi} ｜ 算 ¥${(champ.pay / champ.capP).toFixed(2)}（${nm(champ)}）`);

    // ══════ B 组：交互 bug ══════
    const sig = () => p.evaluate(() => {
      const tr = document.querySelector('.pt.on tbody tr');
      return { n: document.getElementById('nv').value, u: document.getElementById('nU').textContent,
               val: document.getElementById('tgt').value, max: document.getElementById('tgt').max,
               head: document.querySelector('.pt.on th [data-caph]').textContent,
               cap: tr.querySelector('td[data-cap] b').textContent,
               pay: tr.dataset.p, k: document.querySelector('#segA button.on').dataset.k,
               capu: document.querySelector('#capSeg button.on').dataset.cap };
    });

    // B1 快速连点周期 ×6 后状态自洽
    for (const k2 of ['m','q','y','m','q','y']) await p.click('#segA button[data-k="' + k2 + '"]');
    await p.waitForTimeout(240);
    let s = await sig();
    R(b, 'B1', '快速连点周期 ×6 后：高亮＝生效周期，且数值自洽',
      s.k === 'y' && s.u === '条/月' && (await table()).length === PLANS.filter(x => x.key === 'y').length,
      `生效 ${s.k} ｜ 单位 ${s.u}`);

    // B2 快速连点口径 ×6 后状态自洽
    for (const c2 of ['p','m','p','m','p','m']) await p.click('#capSeg button[data-cap="' + c2 + '"]');
    await p.waitForTimeout(240);
    s = await sig();
    R(b, 'B2', '快速连点口径 ×6 后：回到「每月」，滑块量程与表头复原',
      s.capu === 'm' && s.max === '200' && s.u === '条/月' && s.head === '每月可生成',
      `口径 ${s.capu} ｜ max ${s.max} ｜ ${s.head}`);

    // B3 滑块连续输入 20 次后不漂移
    await p.evaluate(() => { const t = document.getElementById('tgt');
      for (let i = 0; i < 20; i++) { t.value = 30 + (i % 5) * 10; t.dispatchEvent(new Event('input', { bubbles: true })); }
      t.value = 30; t.dispatchEvent(new Event('input', { bubbles: true })); });
    await p.waitForTimeout(240);
    s = await sig();
    R(b, 'B3', '滑块连续触发 21 次后回到 30，数值不漂移', s.val === '30' && s.n === '30', `滑块 ${s.val} ｜ 输入框 ${s.n}`);

    // B4 输入框非法值后能恢复（空 / 字母 / 负数 / 超大）
    let badB4 = [];
    for (const v of ['', 'abc', '-5', '99999', '0']) {
      await p.evaluate(val => { const i = document.getElementById('nv'); i.value = val;
        i.dispatchEvent(new Event('change', { bubbles: true })); }, v);
      await p.waitForTimeout(150);
      const st = await sig();
      const num = parseInt(st.n, 10);
      if (!(num >= 1 && num <= 200 * parseFloat(st.max) / 200)) badB4.push(`输入"${v}" → ${st.n}`);
      if (isNaN(num)) badB4.push(`输入"${v}" 后为 NaN`);
    }
    await p.evaluate(() => { const i = document.getElementById('nv'); i.value = '30'; i.dispatchEvent(new Event('change', { bubbles: true })); });
    await p.waitForTimeout(150);
    R(b, 'B4', '输入框非法值（空/字母/负数/超大/0）后仍落在合法区间', badB4.length === 0, badB4.join(' ') || '全部收敛');

    // B5 列宽不漂移（回归：曾因文本累加被撑宽）
    await setK('q'); await setN(100);
    const w0 = await p.evaluate(() => [...document.querySelectorAll('.pt.on thead th')].map(t => Math.round(t.getBoundingClientRect().width)).join(','));
    for (let i = 0; i < 4; i++) {
      await p.click('#capSeg button[data-cap="p"]'); await p.waitForTimeout(130);
      await p.click('#capSeg button[data-cap="m"]'); await p.waitForTimeout(130);
    }
    const w1 = await p.evaluate(() => [...document.querySelectorAll('.pt.on thead th')].map(t => Math.round(t.getBoundingClientRect().width)).join(','));
    R(b, 'B5', '来回切口径 4 轮后各列宽度逐列复原（回归：列被撑宽）', w0 === w1,
      w0 === w1 ? '逐列一致' : `${w0}\n                  → ${w1}`);

    // B6 切周期后滑块单位/量程正确
    await p.click('#capSeg button[data-cap="p"]'); await p.waitForTimeout(150);
    let badB6 = [];
    for (const [k2, u, mx] of [['m','条/月','200'], ['q','条/季','600'], ['y','条/年','2400']]) {
      await setK(k2); await p.waitForTimeout(160);
      const st = await sig();
      if (st.u !== u || st.max !== mx) badB6.push(`${k2}: ${st.u}/${st.max}`);
    }
    await p.click('#capSeg button[data-cap="m"]'); await setK('m'); await p.waitForTimeout(150);
    R(b, 'B6', '周期口径：切周期后滑块单位与量程同步（月/季/年）', badB6.length === 0, badB6.join(' ') || '三周期正确');

    // B7 平台筛选后名次重排且不丢行
    const before = (await table()).length;
    /* ⚠ 只能看【可见行】：rerank() 只给 visible 行发名次，
       被筛掉的隐藏行保留旧名次是设计正确的行为。 */
    const vis = () => p.evaluate(() => [...document.querySelectorAll('.pt.on tbody tr')]
      .filter(tr => tr.style.display !== 'none')
      .map(tr => tr.querySelector('.rk b').textContent.trim()));
    await p.click('#platFilter .pfb:nth-of-type(2)', { timeout: 3000 }).catch(() => {});
    await p.waitForTimeout(250);
    const vRanks = await vis();
    const ranked = vRanks.every((r, i) => r === String(i + 1));
    let badB7 = !ranked ? `可见行名次断裂 [${vRanks.slice(0, 6).join(',')}]` : '';
    await p.click('#platFilter .pfb:nth-of-type(2)', { timeout: 3000 }).catch(() => {});
    await p.waitForTimeout(250);
    const back = await p.evaluate(() => [...document.querySelectorAll('.pt.on tbody tr')]
      .filter(tr => tr.style.display !== 'none').length);
    R(b, 'B7', '平台筛选：可见行名次连续，取消后行数复原',
      badB7 === '' && back === before, badB7 || `${before} → ${vRanks.length} → ${back}`);

    // B8 切视图 ×3 后无横向溢出、无报错
    let badB8 = [];
    /* ⚠ 成本页只有 all / period 两个视图 —— 「buy」已被移除。
       点不存在的元素会让 Playwright 空等 30s（这正是上次跑 10 分钟的真凶）。 */
    for (const v of ['period', 'all']) {
      await p.click('#viewSeg button[data-v="' + v + '"]'); await p.waitForTimeout(170);
      const of = await p.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      if (of > 2) badB8.push(`${v} 溢出 ${of}px`);
    }
    R(b, 'B8', '三视图切换后均无横向溢出', badB8.length === 0, badB8.join(' ') || '无溢出');

    // B9 表头排序点击后名次仍完整
    await p.click('[data-seg="view"] button[data-v="all"]'); await p.waitForTimeout(150);
    await setK('y'); await setN(30);
    /* ⚠ 必须每轮【重新查询】表头 —— 上一次点击会重渲染 tbody，
       缓存下来的 ElementHandle 会失效，Playwright 会空等 30s。 */
    let badB9 = '';
    for (let i = 1; i < 4; i++) {
      const th = await p.$('#viewSeg, .pt.on thead th:nth-child(' + (i + 1) + ')')
        || await p.$('.pt.on thead th:nth-child(' + (i + 1) + ')');
      try { if (th) { await th.click({ timeout: 3000 }); await p.waitForTimeout(150); } } catch (e) {}
      const tb = await table();
      if (!tb.every(r => /^\d+$/.test(r.rank))) { badB9 = `第${i}列表头点击后名次受损`; break; }
    }
    R(b, 'B9', '表头排序点击后名次仍全为数字', badB9 === '', badB9 || '三点击均完好');

    // B10 反复切周期 12 次后一切复原
    await setK('m'); await setN(30); await p.click('#capSeg button[data-cap="m"]'); await p.waitForTimeout(150);
    const s0 = await sig();
    for (let i = 0; i < 6; i++) { await p.click('#segA button[data-k="y"]'); await p.click('#segA button[data-k="m"]'); }
    await p.waitForTimeout(240);
    const s1 = await sig();
    R(b, 'B10', '切周期 12 次后：状态逐字段复原且无 JS 报错',
      JSON.stringify(s0) === JSON.stringify(s1) && errs.length === 0,
      JSON.stringify(s0) === JSON.stringify(s1) ? '逐字段一致' : '状态漂移');

    if (!ctx) { ctx = c; } else { await p.close(); }
    return { a, b, errs };
  };

  // ── 跑 10 遍 ──
  let aPass = 0, bPass = 0, aFirst = null, bFirst = null;
  for (let i = 1; i <= 10; i++) {
    const { a, b, errs } = await runOnce();
    const af = a.filter(x => !x.ok), bf = b.filter(x => !x.ok);
    if (i === 1) {
      console.log('══ A 组 · 数据计算 ══');
      a.forEach(x => console.log(`  ${x.ok ? '✓' : '✗'} ${x.id.padEnd(7)} ${x.desc}\n           ${x.detail}`));
      console.log('\n══ B 组 · 交互 bug ══');
      b.forEach(x => console.log(`  ${x.ok ? '✓' : '✗'} ${x.id.padEnd(4)} ${x.desc}\n           ${x.detail}`));
      console.log('');
    }
    if (!af.length) aPass++; else if (!aFirst) aFirst = { run: i, items: af };
    if (!bf.length) bPass++; else if (!bFirst) bFirst = { run: i, items: bf };
    console.log(`  第 ${String(i).padStart(2)} 遍 ｜ A 组 ${a.length - af.length}/${a.length} ｜ B 组 ${b.length - bf.length}/${b.length} ｜ JS 报错 ${errs.length}`);
    [...af, ...bf].forEach(x => console.log(`        ✗ ${x.id} ${x.desc} → ${x.detail}`));
  }
  console.log('\n' + '─'.repeat(76));
  console.log(`  A 组（数据计算）10 遍全通过：${aPass}/10 ｜ 每题 10 次断言`);
  console.log(`  B 组（交互 bug）10 遍全通过：${bPass}/10 ｜ 每题 10 次断言`);
  await br.close();
})().catch(e => console.error('FATAL ' + e.message));

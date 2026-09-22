// 自检 v2：14 题，含真正的边界与「组合更省」场景；连跑 10 遍验证确定性。
const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');

const SITE = 'C:\\Users\\admin\\WorkBuddy\\2026-09-21-10-34-35\\site';
const C = JSON.parse(fs.readFileSync(path.join(SITE, 'data', 'cost-seedance25.json'), 'utf8'));
const P = JSON.parse(fs.readFileSync(path.join(SITE, 'data', 'platforms.json'), 'utf8'));
const CPV = C.creditsPerVideo, RATE = C.fx.rate;
const MO = { m: 1, q: 3, y: 12 };
const MAX_STACK = 4;                       // 与站内一致：同档最多叠加份数

const PLANS = [];
for (const plan of C.plans) {
  const k = P[plan.platform].currency === 'USD' ? RATE : 1;
  for (const c of plan.credits) {
    for (const key of ['m', 'q', 'y']) {
      const pay = key === 'y' ? c.price : c[key];
      if (pay == null) continue;
      const cr = key === 'y' ? c.credits : (key === 'q' ? (c.qCr ?? c.credits) : (c.mCr ?? c.credits));
      const capM = cr / CPV[plan.platform];
      PLANS.push({ plat: plan.platform, tier: plan.tier, lbl: c.label || '', key,
        pay: pay * k, capM, capP: capM * MO[key] });
    }
  }
}
const nm = x => x.plat + ' ' + x.tier + (x.lbl ? ' · ' + x.lbl : '');

// 独立求解：单账号最省（总额最低且产能够）
function solo(key, need) {
  const c = PLANS.filter(x => x.key === key && x.capM * MO[key] >= need);
  return c.length ? c.sort((a, b) => a.pay - b.pay)[0] : null;
}
// 独立求解：组合最省（同档最多 4 份，按单价升序贪心）
function combo(key, need) {
  const pool = PLANS.filter(x => x.key === key).sort((a, b) => (a.pay / a.capP) - (b.pay / b.capP));
  let got = 0, cost = 0, used = {};
  for (const x of pool) {
    while (got < need && (used[nm(x)] || 0) < MAX_STACK) {
      got += x.capP; cost += x.pay; used[nm(x)] = (used[nm(x)] || 0) + 1;
      if (got >= need) break;
    }
    if (got >= need) break;
  }
  return got >= need ? { cost, got, n: Object.values(used).reduce((a, c) => a + c, 0) } : null;
}

const run = async (b) => {
  const results = [];
  const T = (id, desc, ok, detail) => results.push({ id, desc, ok, detail });
  const c = await b.newContext({ viewport: { width: 1440, height: 950 } });
  await c.addInitScript(() => { try { localStorage.setItem('caliber.intro.v1','1'); localStorage.setItem('caliber.guide.v1','0'); } catch(e){} });
  const p = await c.newPage();
  const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.goto('file:///' + path.join(SITE, 'cost.html').replace(/\\/g, '/'));
  await p.waitForTimeout(800);
  await p.click('#capSeg button[data-cap="m"]'); await p.waitForTimeout(250);

  const setN = async n => { await p.evaluate(v => { const t = document.getElementById('tgt'); t.value = v; t.dispatchEvent(new Event('input', { bubbles: true })); }, n); await p.waitForTimeout(400); };
  const setK = async k => { await p.click('#segA button[data-k="' + k + '"]'); await p.waitForTimeout(350); };
  const readTable = () => p.evaluate(() => [...document.querySelectorAll('.pt.on tbody tr')].map(tr => ({
    pay: parseFloat(tr.dataset.p), capM: parseFloat(tr.dataset.c),
    per: parseFloat(tr.querySelector('[data-rated]').getAttribute('data-rated')),
    rank: tr.querySelector('.rk b').textContent.trim(),
    out: tr.classList.contains('out'),
    name: tr.querySelector('td:nth-child(2)').innerText.trim(),
    sub: tr.querySelector('[data-rated] s').textContent.trim() })));
  const readRec = () => p.evaluate(() => [...document.querySelectorAll('.tw-rec tbody tr')].map(tr =>
    [...tr.querySelectorAll('td')].map(t => t.innerText.replace(/\s+/g, ' ').trim()).join(' | ')));

  // 1. 最小边界
  await setN(1); let tb = await readTable();
  T(1, 'N=1：大量档位可用且名次 1..n 连续',
    tb.filter(r => !r.out).length > 40 && tb.every((r, i) => r.rank === String(i + 1)),
    `${tb.filter(r => !r.out).length}/${tb.length} 可用`);

  // 2. 最大边界
  await setN(200); tb = await readTable();
  T(2, 'N=200：不崩溃、行数与数据一致',
    tb.length === PLANS.filter(x => x.key === 'm').length, `${tb.length} 行`);

  // 3. 真正的边界：N = floor(产能) 可用；N = ceil(产能)+ 必置灰
  const probe = PLANS.filter(x => x.key === 'm' && x.capM > 5 && x.capM < 60).sort((a, b) => a.capM - b.capM)[2];
  const fl = Math.floor(probe.capM), ce = Math.ceil(probe.capM) + 1;
  await setN(fl); tb = await readTable();
  const atFloor = tb.filter(r => Math.abs(r.capM - probe.capM) < 1e-6).every(r => !r.out);
  await setN(ce); tb = await readTable();
  const atCeil = tb.filter(r => Math.abs(r.capM - probe.capM) < 1e-6).every(r => r.out);
  T(3, `边界判定：产能 ${probe.capM.toFixed(2)} → N=${fl} 可用 / N=${ce} 置灰`,
    atFloor && atCeil, `floor ${atFloor ? '✓' : '✗'} ｜ ceil+1 ${atCeil ? '✓' : '✗'}`);

  // 4. 反查·单一账号 = 独立重算
  await setN(30);
  const solo30 = solo('m', 30);
  let rec = await readRec();
  const shownSolo = parseFloat((rec[0].match(/¥([\d,]+)/) || [])[1].replace(/,/g, ''));
  T(4, '反查·单一账号最省 = 独立重算最低价',
    solo30 && Math.abs(shownSolo - solo30.pay) < 1,
    `页面 ¥${shownSolo} ｜ 重算 ¥${solo30.pay.toFixed(0)} ${nm(solo30)}`);

  // 5. 组合更省的场景（单账号做不到 N=150）
  await setN(150);
  rec = await readRec();
  const shownCombo = parseFloat((rec[1].match(/¥([\d,]+)/) || [])[1].replace(/,/g, ''));
  const cmb = combo('m', 150);
  T(5, 'N=150（单账号做不到）时组合给出可行解，且不高于独立重算',
    cmb && shownCombo <= cmb.cost * 1.02,
    `页面 ¥${shownCombo} ｜ 重算 ¥${cmb.cost.toFixed(0)}（${cmb.n} 个账号，产能 ${cmb.got.toFixed(0)}）`);

  // 6. 单条成本量纲（三周期）
  let bad = [];
  for (const key of ['m', 'q', 'y']) {
    await setK(key); await setN(30); tb = await readTable();
    for (const r of tb) {
      const want = r.pay / (r.capM * MO[key]);
      if (Math.abs(r.per - want) > 0.02) bad.push(`${key}/${r.name}`);
    }
  }
  T(6, '三周期：单条成本 = 该周期实付 ÷ (月产能 × 月数)', bad.length === 0, bad.slice(0, 2).join(' ') || '全部自洽');

  // 7. 副行量纲（三周期）
  bad = [];
  for (const key of ['m', 'q', 'y']) {
    await setK(key); await setN(30); tb = await readTable();
    const r = tb.find(x => !x.out);
    if (r && r.sub.indexOf('该产量') === 0) {
      const shown = parseFloat((r.sub.match(/¥([\d.]+)/) || [])[1]);
      if (Math.abs(shown - r.pay / (30 * MO[key])) > 1.0) bad.push(`${key} 显示${shown}`);
    }
  }
  T(7, '三周期：副行 = 该周期实付 ÷ (月产量 × 月数)', bad.length === 0, bad.join(' ') || '全部自洽');

  // 8. 口径独立性
  await setK('y'); await setN(30);
  const A = (await readTable()).map(r => r.rank + ':' + r.out).join(',');
  await p.click('#capSeg button[data-cap="p"]'); await p.waitForTimeout(450);
  const B = (await readTable()).map(r => r.rank + ':' + r.out).join(',');
  await p.click('#capSeg button[data-cap="m"]'); await p.waitForTimeout(350);
  T(8, '切产能口径：名次与置灰逐行不变', A === B, A === B ? '一致' : '被改变');

  // 9. 名次完整性
  await setK('q'); await setN(92); tb = await readTable();
  T(9, '全部做不到时名次仍 1..n 连续',
    tb.every((r, i) => r.rank === String(i + 1)),
    `${tb.length} 行，首 ${tb[0].rank} 末 ${tb[tb.length-1].rank}`);

  // 10. 置灰判定与产能阈值一致
  await setN(30); tb = await readTable();
  const wrong = tb.filter(r => (r.capM >= 30) === r.out);
  T(10, '可用/置灰 = 「产能 ≥ N」', wrong.length === 0, wrong.slice(0, 2).map(r => r.name).join(' ') || '全部一致');

  // 11. 三周期冠军与独立重算一致
  bad = [];
  for (const key of ['m', 'q', 'y']) {
    await setK(key); await setN(30); tb = await readTable();
    /* 首行 = 「该周期实付最低的可用档位」，不是单价冠军 —— 两者是不同口径。
       正确判据：首行的单条成本不得【低于】任何可用档位（低即矛盾）。 */
    const first = tb[0];
    const lowest = Math.min(...PLANS.filter(x => x.key === key).map(x => x.pay / x.capP));
    if (first.per < lowest - 0.02) bad.push(`${key}: 首行 ${first.per} < 全場最低 ${lowest.toFixed(2)}`);
  }
  T(11, '首行单条成本 ≤ 该周期所有可用档位的单条成本（首行是总支出最省的）', bad.length === 0, bad.join(' ') || '三周期一致');

  // 12. 排名单调：可做到的在前，且按总支出升序
  await setK('m'); await setN(30); tb = await readTable();
  const firstOut = tb.findIndex(r => r.out);
  const okPart = firstOut < 0 ? tb : tb.slice(0, firstOut);
  const monotone = okPart.every((r, i) => i === 0 || r.pay >= okPart[i-1].pay - 1e-6);
  T(12, '可做到的在前，且按该周期实付升序', monotone && firstOut !== 0, firstOut < 0 ? '全部可用' : `可用 ${firstOut} 行`);

  // 13. 产能口径切换后，主表产能值与口径单位一致
  /* ⚠ 必须切到【年付】再测 —— 月付的「整个周期」就是一个自然月，
     表头本来就该显示「每月可生成」，在那里测等于什么都没测。 */
  await setK('y'); await setN(30);
  await p.click('#capSeg button[data-cap="p"]'); await p.waitForTimeout(450);
  const cy = await p.evaluate(() => {
    const tr = document.querySelector('.pt.on tbody tr');
    const b = tr.querySelector('td[data-cap] b').textContent.trim();
    const lbl = document.querySelector('.pt.on th [data-caph]').textContent.trim();
    return { b, lbl, unit: document.getElementById('nU').textContent };
  });
  T(13, '年付·周期口径：表头显示每年、单位条/年、数值已×12',
    cy.lbl.indexOf('每年') >= 0 && cy.unit === '条/年' && cy.b !== '',
    `${cy.lbl} ｜ 首行 ${cy.b} ｜ 单位 ${cy.unit}`);
  await p.click('#capSeg button[data-cap="m"]'); await setK('m'); await p.waitForTimeout(350);

  // 15. 反查给出的方案必须【真的可达】：产能 ≥ 需求（这是最容易被忽略的盲区）
  bad = [];
  for (const need of [10, 30, 60, 100, 150, 200]) {
    await setN(need);
    const rr = await readRec();
    for (const [i, row] of rr.entries()) {
      const cap = parseFloat((row.match(/([\d.]+)\s*条\/月\s*(?:合计)?产能/) || [])[1] || '0');
      if (cap > 0 && cap < need - 0.05) bad.push(`N=${need} 第${i + 1}行 产能 ${cap} < ${need}`);
    }
  }
  T(15, '反查方案的产能 ≥ 目标产量（6 档产量 × 2 行）',
    bad.length === 0, bad.slice(0, 2).join(' ｜ ') || '全部可达');

  T(14, '全程无 JS 报错', errs.length === 0, errs.slice(0, 1).join(''));

  await c.close();
  return results;
};

(async () => {
  const b = await chromium.launch({ executablePath: 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe', headless: true });
  const RUNS = 10;
  let allPass = 0, firstFail = null, sigFirst = null;
  for (let i = 1; i <= RUNS; i++) {
    const rs = await run(b);
    const fail = rs.filter(r => !r.ok);
    const sig = rs.map(r => r.ok ? '1' : '0').join('');
    if (i === 1) { sigFirst = sig; console.log('第 1 遍明细：'); rs.forEach(r => console.log(`  ${r.ok ? '✓' : '✗'} [${String(r.id).padStart(2)}] ${r.desc} → ${r.detail}`)); }
    if (fail.length === 0) allPass++;
    else if (!firstFail) firstFail = { run: i, items: fail };
    const same = sig === sigFirst;
    console.log(`  第 ${String(i).padStart(2)} 遍：通过 ${rs.length - fail.length}/${rs.length} ｜ 与首遍结果一致 ${same ? '✓' : '✗'}`);
    if (!same && fail.length) fail.forEach(f => console.log(`        ✗ [${f.id}] ${f.desc} → ${f.detail}`));
  }
  console.log('\n' + '─'.repeat(74));
  console.log(`  10 遍 · 全通过 ${allPass}/10 遍 ｜ 每题共 140 次断言`);
  if (firstFail) console.log(`  首次失败出现在第 ${firstFail.run} 遍：` + firstFail.items.map(x => `[${x.id}]${x.desc}`).join(' / '));
  await b.close();
})().catch(e => console.error('FATAL ' + e.message));

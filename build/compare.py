"""Cost comparison calculator for the main visitor flow."""
import json
from html import escape


def compare_view(rows, readings, updated, periods):
    platforms = dict.fromkeys(readings)
    plans = []
    for row in rows:
        plat = row["plat"]
        plans.append({
            "platform": plat,
            "tier": row["tier"],
            "periods": {key: [p["payCNY"], p["cr"]] for key, p in row["byP"].items()},
        })
    data = json.dumps({"plans": plans, "readings": readings,
                       "periods": {key: [label, months] for key, label, months, _ in periods}},
                      ensure_ascii=False).replace("<", "\\u003c")
    platform_options = "".join(f'<option value="{escape(name)}">{escape(name)}</option>' for name in platforms)
    period_options = "".join(f'<option value="{key}">{label}</option>' for key, label, _, _ in periods)
    html = f"""
<main id="compare-tool" class="compare-page" data-skip-intro>
  <header class="compare-heading">
    <div>
      <h1>视频生成成本对比</h1>
      <p>选好规格和每月用量，找出能做够、花钱最少的会员方案。</p>
    </div>
    <p class="compare-date">{len(platforms)} 家平台 · 数据更新于 <time datetime="{updated}">{updated}</time></p>
  </header>
  <form id="compare-form" class="compare-form">
    <label for="compare-model">模型
      <select id="compare-model">
        <option value="0">Seedance 2.5 标准版</option>
        <option value="2">Seedance 2.5 Flash</option>
        <option value="4">Seedance 2.5 样片模式</option>
      </select>
    </label>
    <label for="compare-resolution">分辨率
      <select id="compare-resolution">
        <option value="0">480p</option>
        <option value="1" selected>720p</option>
      </select>
    </label>
    <label for="compare-period">会员周期
      <select id="compare-period">{period_options}</select>
    </label>
    <label for="compare-target">每月要生成多少条
      <span class="compare-input-unit">
        <input id="compare-target" type="number" inputmode="numeric" min="1" max="10000" step="1" value="30" required>
        <span aria-hidden="true">条</span>
      </span>
    </label>
  </form>
  <div class="compare-scope"><span>每条 30 秒 · 16:9 · 全能参考</span><a href="#canvas-comparison">查看画布扣分</a></div>
  <section id="compare-results" class="compare-results" aria-labelledby="compare-results-title">
    <div class="compare-result-head">
      <h2 id="compare-results-title">会员方案</h2>
      <div class="compare-result-filters">
        <label for="compare-platform">平台 <select id="compare-platform"><option value="">全部平台</option>{platform_options}</select></label>
        <label for="compare-all"><input id="compare-all" type="checkbox"> 显示全部档位</label>
      </div>
    </div>
    <p class="compare-result-status" id="compare-status" role="status"></p>
    <div id="compare-grid">
      <table aria-label="符合规格的会员方案">
        <thead><tr>
          <th scope="col">平台 / 档位</th><th scope="col">首期实付</th>
          <th scope="col">每月约能做</th><th scope="col">按用量 / 条</th>
        </tr></thead>
        <tbody id="compare-rows"></tbody>
      </table>
    </div>
    <p id="compare-coverage" class="compare-coverage"></p>
    <p class="compare-calc-note">按单账号、首期价格和基础积分估算。首购优惠以平台结算资格为准。美元按采集日汇率折算。</p>
    <noscript><p>启用 JavaScript 可以实时计算。<a href="cycles.html#allperiod">查看固定规格的完整对比表</a></p></noscript>
  </section>
  <div class="compare-record-links" aria-label="核对价格与来源">
    <a href="#membership-prices">会员价格明细</a>
    <a href="#offers">活动与赠送权益</a>
    <a href="#pricing-evidence">采集截图</a>
  </div>
</main>
"""
    return html, COMPARE_JS.replace("__COMPARE_DATA__", data)


COMPARE_CSS = """
body{background:#08090a}
body::before,body::after{display:none}
.promo,.nav .spec{display:none}
.nav{background:#08090a}
.compare-page,.compare-records{width:min(1112px,calc(100% - 72px));margin-inline:auto}
.compare-page{padding-top:48px}
.compare-home{padding-top:68px;padding-bottom:28px}
.compare-home-actions{display:flex;align-items:center;gap:22px}
.compare-home-actions .btn{background:#d1fe17;color:#101300}
.compare-home-actions .btn:hover{background:#e1ff65;box-shadow:none}
.compare-home-budget{max-width:860px;box-shadow:none;scroll-margin-top:80px}
.compare-heading{display:flex;justify-content:space-between;align-items:end;gap:24px;margin-bottom:28px}
.compare-heading h1{margin:0 0 10px;font-size:46px;line-height:1.12;letter-spacing:-.035em;color:#fff}
.compare-heading p{margin:0;color:#bbc0c8;font-size:15px}
.compare-heading .compare-date{white-space:nowrap;color:#a0a6af;font-size:12px}
.compare-form{display:grid;grid-template-columns:minmax(210px,1.35fr) minmax(100px,.66fr) minmax(110px,.75fr) minmax(150px,1fr);gap:16px;padding:20px;background:#111315;border-radius:14px;border:1px solid #2c3035}
.compare-form label{display:grid;gap:8px;align-content:start;color:#d5d8dd;font-size:13px;font-weight:650}
.compare-page input,.compare-page select,.compare-page button{font:inherit;color:#fff}
.compare-page select,.compare-page input[type=number]{border:1px solid #3c4147;border-radius:8px;background:#17191c;color-scheme:dark;min-height:44px;width:100%;padding:0 11px}
.compare-page select:hover,.compare-page input[type=number]:hover{border-color:#797f87}
.compare-page input:focus-visible,.compare-page select:focus-visible,.compare-page a:focus-visible,.compare-records summary:focus-visible{outline:2px solid #d1fe17;outline-offset:3px}
.compare-page a,.compare-records a{color:#d1fe17;text-underline-offset:4px}
.compare-input-unit{position:relative;display:block}
.compare-input-unit input{padding-right:42px!important}
.compare-input-unit span{position:absolute;right:11px;top:12px;color:#bac1c9;pointer-events:none}
.compare-scope{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;margin:11px 0 32px;font-size:12px;color:#b1b7bf}
.compare-results{margin-top:0;border-top:1px solid #31353a;padding-top:21px}
.compare-result-head{display:flex;justify-content:space-between;align-items:center;gap:12px}
.compare-result-head h2{font-size:24px;color:#fff;margin:0}
.compare-result-filters{display:flex;align-items:center;flex-wrap:wrap;gap:14px;font-size:13px;color:#d5d8dd}
.compare-result-filters label{display:flex;gap:6px;align-items:center;min-height:44px}
.compare-result-filters select{min-width:98px;width:auto}
.compare-result-filters input{width:16px;height:16px;accent-color:#d1fe17}
.compare-result-status{margin:12px 0 15px;color:#e1e5ea;font-size:15px}
.compare-result-status strong{color:#d1fe17;font-weight:750}
.compare-results table{width:100%;min-width:0;background:#0f1113;box-shadow:none;border-radius:12px;border-color:#2c3035;table-layout:fixed}
.compare-results th,.compare-results td{text-align:right;padding:13px 15px;line-height:1.45;font-variant-numeric:tabular-nums;border-bottom-color:#282c30}
.compare-results th{color:#b4bac3;font-size:12px;letter-spacing:normal;white-space:normal;cursor:default}
.compare-results th:hover{color:#b4bac3}
.compare-results th:first-child,.compare-results td:first-child{width:35%;text-align:left}
.compare-results td{color:#e7eaf0;font-size:14px;white-space:normal}
.compare-results td:first-child small{display:block;color:#aeb5bf;margin-top:2px;font-size:12px}
.compare-results td:nth-child(2){font-weight:750}
.compare-results tr.compare-best{background:#161c0c}
.compare-results tr.compare-best td:nth-child(2){color:#d1fe17}
.compare-coverage,.compare-calc-note{color:#aeb5bf;font-size:12px;line-height:1.65;margin:10px 0 0}
.compare-coverage:empty{display:none}
.compare-record-links{display:flex;flex-wrap:wrap;gap:12px 22px;padding:22px 0 25px}
.compare-record-links a{font-size:13px}
.compare-records{margin-top:12px;border-top:1px solid #31353a;padding:20px 0 2px}
.compare-records > p{color:#bbc0c8;line-height:1.7}
.compare-records h2{font-size:23px;color:#fff;margin:0 0 12px}
.compare-records details h2{margin-top:12px}
.compare-records details,.compare-home-budget,.compare-advanced{background:#111315;box-shadow:none;backdrop-filter:none}
.compare-records section{scroll-margin-top:80px}
.compare-records [id]{scroll-margin-top:80px}
.compare-advanced{margin:16px auto 24px;width:min(1112px,calc(100% - 72px))}
.compare-advanced .app{width:100%;padding-inline:0}
.compare-advanced .vhead h2{font-size:22px}
.legal{background:#101214;border-color:#34383d;color:#bac1c9;box-shadow:none}
.legal .legal-t,.legal .legal-b,.legal .legal-f{color:#bac1c9}
.legal .legal-f .fp{background:#171a12;color:#d1fe17}
@media(max-width:820px){
  .compare-page,.compare-records,.compare-advanced{width:calc(100% - 36px)}
  .compare-page{padding-top:28px}
  .compare-home{padding-top:40px}
  .compare-heading{display:block;margin-bottom:18px}
  .compare-heading h1{font-size:34px}
  .compare-heading .compare-date{margin-top:8px}
  .compare-form{grid-template-columns:1.1fr 1fr;padding:14px;gap:12px}
  .compare-results th,.compare-results td{padding:10px 8px}
  .compare-results td{font-size:13px}
  .compare-results td:first-child small{font-size:11px}
  .compare-scope{margin-bottom:18px}
  .compare-result-head h2{font-size:21px}
}
@media(max-width:420px){
  .compare-page,.compare-records,.compare-advanced{width:calc(100% - 28px)}
  .compare-heading h1{font-size:30px}
  .compare-form select,.compare-form input{font-size:13px;padding-left:8px}
  .compare-results th,.compare-results td{padding-inline:6px}
  .compare-result-head{align-items:start;flex-direction:column;gap:4px}
}
"""


COMPARE_JS = r"""
(function(){
  const form = document.getElementById('compare-form');
  const result = document.getElementById('compare-status');
  const table = document.getElementById('compare-grid');
  const rows = document.getElementById('compare-rows');
  const coverage = document.getElementById('compare-coverage');
  const model = document.getElementById('compare-model');
  const resolution = document.getElementById('compare-resolution');
  const period = document.getElementById('compare-period');
  const target = document.getElementById('compare-target');
  const platform = document.getElementById('compare-platform');
  const showAll = document.getElementById('compare-all');
  const data = __COMPARE_DATA__;
  const money = new Intl.NumberFormat('zh-CN', {style:'currency', currency:'CNY', maximumFractionDigits:2, minimumFractionDigits:0});
  const perClip = new Intl.NumberFormat('zh-CN', {style:'currency', currency:'CNY'});

  function render(){
    const amount = target.valueAsNumber;
    const cycle = data.periods[period.value];
    const spec = Number(model.value) + Number(resolution.value);
    const available = new Map();
    const excluded = [];
    const offers = [];
    rows.textContent = '';
    coverage.textContent = '';
    table.hidden = true;
    if (!target.validity.valid) {
      result.textContent = '请输入 1 到 10,000 之间的生成条数。';
      return;
    }
    for (const [name, cells] of Object.entries(data.readings)) {
      if (platform.value && platform.value !== name) continue;
      const reading = cells[spec];
      if (typeof reading === 'string') {
        excluded.push(name + '（' + reading + '）');
        continue;
      }
      available.set(name, typeof reading === 'number' ? {credits:reading} : reading);
    }
    for (const plan of data.plans) {
      const reading = available.get(plan.platform);
      const pricing = plan.periods[period.value];
      if (!reading || !pricing) continue;
      const [pay, monthlyCredits] = pricing;
      const capacity = Math.floor(monthlyCredits / reading.credits);
      offers.push({plan, pay, capacity, monthlyCredits, sourceDate:reading.sourceDate});
    }
    const providers = new Set(offers.map(offer => offer.plan.platform));
    for (const name of available.keys()) {
      if (!providers.has(name)) excluded.push(name + '（无' + cycle[0] + '）');
    }
    const matched = offers.filter(offer => offer.capacity >= amount);
    matched.sort((a,b) => a.pay - b.pay || b.capacity - a.capacity);
    const fastest = Math.max(0, ...offers.map(offer => offer.capacity));
    const cheapest = matched[0];
    result.textContent = '';
    if (cheapest) {
      result.append('满足 ' + amount.toLocaleString('zh-CN') + ' 条/月，首期最低 ');
      const price = document.createElement('strong');
      price.textContent = money.format(cheapest.pay);
      result.append(price, '（' + cycle[0] + '）');
    } else {
      result.textContent = offers.length
        ? '本周期没有单账号档位能满足用量，最高约 ' + fastest + ' 条/月。可调低用量或换一个规格。'
        : '当前选择没有可计算的方案。请选择其他规格、周期或平台。';
    }
    const seen = new Set();
    const displayed = showAll.checked
      ? [...matched, ...offers.filter(offer => offer.capacity < amount).sort((a,b) => a.pay - b.pay)]
      : matched.filter(({plan}) => {
          if (seen.has(plan.platform)) return false;
          seen.add(plan.platform);
          return true;
        });
    for (const offer of displayed) {
      const tr = rows.insertRow();
      if (offer === cheapest) tr.className = 'compare-best';
      const title = tr.insertCell();
      const name = document.createElement('b');
      name.textContent = offer.plan.platform === 'Tapnow' ? 'TapNow' : offer.plan.platform;
      const detail = document.createElement('small');
      detail.textContent = offer.plan.tier + ' · ' + offer.monthlyCredits.toLocaleString('zh-CN') + ' 分/月'
        + (offer.sourceDate ? ' · 扣分沿用留档' : '');
      title.append(name, detail);
      tr.insertCell().textContent = money.format(offer.pay);
      tr.insertCell().textContent = offer.capacity + ' 条';
      tr.insertCell().textContent = offer.capacity >= amount ? perClip.format(offer.pay / (amount * cycle[1])) : '未达用量';
    }
    table.hidden = !displayed.length;
    const short = [...providers].filter(name => !matched.some(offer => offer.plan.platform === name));
    const notes = [];
    if (short.length) notes.push(short.join('、') + ' 的单账号档位未达用量');
    if (excluded.length) notes.push('当前未计入：' + excluded.join('、'));
    coverage.textContent = notes.join('。') + (notes.length ? '。' : '');
  }
  form.addEventListener('submit', event => event.preventDefault());
  [model, resolution, period, platform, showAll].forEach(input => input.addEventListener('change', render));
  target.addEventListener('input', render);
  render();
})();
"""


DISCLOSURE_JS = r"""
(function(){
  function reveal(id){
    const target = document.getElementById(id);
    if (!target) return;
    for (let node = target; node; node = node.parentElement) {
      if (node.tagName === 'DETAILS') node.open = true;
    }
  }
  document.addEventListener('click', function(event){
    const link = event.target.closest('a[href^="#"]');
    if (link && link.hash.length > 1) reveal(link.hash.slice(1));
  });
  function openHash(){
    if (!location.hash) return;
    const id = location.hash.slice(1);
    reveal(id);
    const target = document.getElementById(id);
    if (target) requestAnimationFrame(() => target.scrollIntoView());
  }
  window.addEventListener('hashchange', openHash);
  openHash();
})();
"""

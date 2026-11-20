"""Cost comparison calculator for the main visitor flow."""
import json
from html import escape
from pathlib import Path


def membership_anchor(platform):
    return "membership-" + {"即梦": "jimeng", "小云雀": "xiaoyunque"}.get(platform, platform.lower())


def compare_view(rows, readings, updated, periods, colors):
    platforms = list(readings)
    display_names = {"libtv": "LibTV", "Neowow": "NeoWOW", "Tapnow": "TapNow"}
    plans = []
    for index, row in enumerate(rows):
        plat = row["plat"]
        plans.append({
            "id": index,
            "platform": plat,
            "tier": row["tier"],
            "anchor": membership_anchor(plat),
            "periods": {key: [round(p["payCNY"], 2), p["cr"]] for key, p in row["byP"].items()},
        })
    data = json.dumps({"plans": plans, "readings": readings, "names": display_names, "colors": colors,
                       "periods": {key: [label, months] for key, label, months, _ in periods}},
                      ensure_ascii=False).replace("<", "\\u003c")
    platform_options = "".join(
        f'<option value="{escape(name)}">{escape(display_names.get(name, name))}</option>'
        for name in platforms
    )
    period_options = "".join(
        f'<label><input type="radio" name="period" value="{key}"{" checked" if key == "m" else ""}>'
        f'<span>{label}</span></label>'
        for key, label, _, _ in periods
    )
    html = f"""
<main id="compare-tool" class="compare-page" data-skip-intro>
  <header class="compare-heading">
    <div>
      <h1>哪家画布更划算？</h1>
      <p>视频生成成本榜 · 用相同规格比较会员价格、每月产能和单条成本。</p>
    </div>
    <p class="compare-date">{len(platforms)} 家平台 · 数据更新于 <time datetime="{updated}">{updated}</time></p>
  </header>
  <nav class="compare-page-links" aria-label="榜单导航">
    <a href="#compare-results">榜单总览</a><a href="#compare-frontier">价格与产能</a><a href="#compare-records-title">数据与口径</a>
  </nav>
  <form id="compare-form" class="compare-form">
    <fieldset class="compare-choice compare-mode">
      <legend>怎么比</legend>
      <div>
        <label><input type="radio" name="mode" value="target" checked><span>按月用量</span></label>
        <label><input type="radio" name="mode" value="budget"><span>按预算</span></label>
      </div>
    </fieldset>
    <label class="compare-field" for="compare-model">模型
      <select id="compare-model">
        <option value="0">Seedance 2.5 标准版</option>
        <option value="2">Seedance 2.5 Flash</option>
        <option value="4">Seedance 2.5 样片模式</option>
      </select>
    </label>
    <div class="compare-spec-picker">
      <fieldset class="compare-choice">
        <legend>分辨率</legend>
        <div>
          <label><input type="radio" name="resolution" value="0"><span>480p</span></label>
          <label><input type="radio" name="resolution" value="1" checked><span>720p</span></label>
        </div>
      </fieldset>
      <fieldset class="compare-choice">
        <legend>会员周期</legend>
        <div>{period_options}</div>
      </fieldset>
    </div>
    <div id="compare-target-panel">
      <label class="compare-field" for="compare-target">每月要生成多少条
        <span class="compare-input-unit">
          <input id="compare-target" type="number" inputmode="numeric" min="1" max="10000" step="1" value="30" required>
          <span aria-hidden="true">条</span>
        </span>
      </label>
      <div class="compare-presets" aria-label="常用月用量">
        <button type="button" data-target="10" aria-pressed="false">10 条</button>
        <button type="button" data-target="30" aria-pressed="true">30 条</button>
        <button type="button" data-target="60" aria-pressed="false">60 条</button>
      </div>
    </div>
    <div id="compare-budget-panel" hidden>
      <label class="compare-field" for="compare-budget">所选周期的总预算
        <span class="compare-input-unit">
          <input id="compare-budget" type="number" inputmode="decimal" min="1" max="1000000" step="0.01" value="1000" required disabled>
          <span aria-hidden="true">元</span>
        </span>
      </label>
      <div class="compare-presets" aria-label="常用周期预算">
        <button type="button" data-budget="300" aria-pressed="false">¥300</button>
        <button type="button" data-budget="1000" aria-pressed="true">¥1,000</button>
        <button type="button" data-budget="3000" aria-pressed="false">¥3,000</button>
      </div>
    </div>
    <div class="compare-scope"><span>30 秒 · 16:9 · 全能参考</span><a href="#canvas-comparison">扣分依据</a></div>
  </form>
  <section id="compare-results" class="compare-results" aria-labelledby="compare-results-title">
    <div class="compare-result-head">
      <h2 id="compare-results-title">会员成本榜</h2>
      <div class="compare-result-filters">
        <label for="compare-platform">平台 <select id="compare-platform"><option value="">全部平台</option>{platform_options}</select></label>
        <button id="compare-reset" type="button">重置</button>
      </div>
    </div>
    <p class="compare-result-status" id="compare-status" role="status"></p>
    <div id="compare-highlights" class="compare-highlights" hidden></div>
    <figure id="compare-bar-figure" class="compare-bar-figure" hidden>
      <figcaption id="compare-bar-label"></figcaption>
      <div class="compare-bars-scroll"><div id="compare-bars" class="compare-bars"></div></div>
    </figure>
    <p id="compare-order" class="compare-order"></p>
    <div id="compare-grid">
      <table aria-label="符合规格的会员方案">
        <thead><tr>
          <th scope="col">排名 · 平台 / 档位</th><th scope="col" id="compare-paid">首期实付</th>
          <th scope="col" id="compare-volume">每月约能做</th><th scope="col">每条成本</th>
        </tr></thead>
        <tbody id="compare-rows"></tbody>
      </table>
    </div>
    <label class="compare-all-toggle"><input id="compare-all" type="checkbox"> 显示全部档位</label>
    <p id="compare-coverage" class="compare-coverage"></p>
    <p id="compare-calc-note" class="compare-calc-note"></p>
    <noscript><p>启用 JavaScript 可以实时计算。<a href="cycles.html#allperiod">查看固定规格的完整对比表</a></p></noscript>
  </section>
  <section id="compare-frontier" class="compare-frontier" aria-labelledby="compare-frontier-title" hidden>
    <header class="compare-result-head">
      <h2 id="compare-frontier-title">价格与产能前沿</h2>
      <fieldset class="compare-choice compare-frontier-mode">
        <legend>横轴</legend>
        <div>
          <label><input type="radio" name="frontier-metric" value="spend" checked><span>首期实付</span></label>
          <label><input type="radio" name="frontier-metric" value="unit"><span>用满单条成本</span></label>
        </div>
      </fieldset>
    </header>
    <p id="compare-frontier-note"></p>
    <div class="compare-frontier-layout">
      <figure class="compare-frontier-chart">
        <figcaption>每月约能做（条）</figcaption>
        <div id="compare-frontier-y" class="compare-frontier-y" aria-hidden="true"></div>
        <div id="compare-frontier-plot" class="compare-frontier-plot" role="group" aria-label="可点击的会员档位散点"></div>
        <div id="compare-frontier-x" class="compare-frontier-x" aria-hidden="true"></div>
        <div id="compare-frontier-axis" class="compare-frontier-axis"></div>
      </figure>
      <div class="compare-frontier-side">
        <div id="compare-point-detail" class="compare-point-detail" aria-live="polite"></div>
        <div id="compare-frontier-list" class="compare-frontier-list" aria-label="前沿档位"></div>
      </div>
    </div>
  </section>
  <div class="compare-record-links" aria-label="核对价格与来源">
    <a href="#membership-prices">会员价格明细</a>
    <a href="#offers">活动与赠送权益</a>
    <a href="#pricing-evidence">采集截图</a>
  </div>
</main>
"""
    return html, COMPARE_JS.replace("__COMPARE_DATA__", data).replace("__COMPARE_CHARTS__", COMPARE_CHARTS)


COMPARE_CSS = Path(__file__).with_name("compare_style.css").read_text(encoding="utf-8")
COMPARE_CHARTS = Path(__file__).with_name("compare_charts.js").read_text(encoding="utf-8")


COMPARE_JS = r"""
(function(){
  const form = document.getElementById('compare-form');
  const result = document.getElementById('compare-status');
  const table = document.getElementById('compare-grid');
  const rows = document.getElementById('compare-rows');
  const coverage = document.getElementById('compare-coverage');
  const order = document.getElementById('compare-order');
  const title = document.getElementById('compare-results-title');
  const calcNote = document.getElementById('compare-calc-note');
  const paidHead = document.getElementById('compare-paid');
  const volumeHead = document.getElementById('compare-volume');
  const model = form.elements.namedItem('compare-model');
  const resolution = form.elements.namedItem('resolution');
  const period = form.elements.namedItem('period');
  const mode = form.elements.namedItem('mode');
  const target = document.getElementById('compare-target');
  const budget = document.getElementById('compare-budget');
  const targetPanel = document.getElementById('compare-target-panel');
  const budgetPanel = document.getElementById('compare-budget-panel');
  const platform = document.getElementById('compare-platform');
  const showAll = document.getElementById('compare-all');
  const presets = form.querySelectorAll('[data-target], [data-budget]');
  const data = __COMPARE_DATA__;
  const money = new Intl.NumberFormat('zh-CN', {style:'currency', currency:'CNY', maximumFractionDigits:2, minimumFractionDigits:0});
  const perClip = new Intl.NumberFormat('zh-CN', {style:'currency', currency:'CNY'});
  const defaultMode = new URLSearchParams(location.search).get('mode') === 'budget' ? 'budget' : 'target';
  const nameOf = platformName => data.names[platformName] || platformName;
  __COMPARE_CHARTS__
  mode.value = defaultMode;

  function render(){
    const byBudget = mode.value === 'budget';
    const input = byBudget ? budget : target;
    const amount = input.valueAsNumber;
    const cycle = data.periods[period.value];
    const spec = Number(model.value) + Number(resolution.value);
    const available = new Map();
    const excluded = [];
    const offers = [];
    target.disabled = targetPanel.hidden = byBudget;
    budget.disabled = budgetPanel.hidden = !byBudget;
    for (const preset of presets) {
      const activeValue = preset.dataset.budget ? budget.valueAsNumber : target.valueAsNumber;
      preset.setAttribute('aria-pressed', String(Number(preset.dataset.budget || preset.dataset.target) === activeValue));
    }
    title.textContent = byBudget ? '预算产能榜' : '会员成本榜';
    table.dataset.mode = mode.value;
    calcNote.textContent = (byBudget ? '每条成本按用完可生成额度计算。' : '每条成本按你填写的用量计算。')
      + '结果基于单账号、首期价格和基础积分。首购资格以结算页为准。';
    paidHead.setAttribute('aria-sort', byBudget ? 'none' : 'ascending');
    volumeHead.setAttribute('aria-sort', byBudget ? 'descending' : 'none');
    rows.textContent = '';
    coverage.textContent = '';
    order.textContent = '';
    table.hidden = true;
    clearCharts();
    if (!input.validity.valid) {
      result.textContent = byBudget ? '请输入 ¥1 至 ¥1,000,000 的预算，最多保留两位小数。'
        : '请输入 1 到 10,000 之间的整数条数。';
      return;
    }
    for (const [name, cells] of Object.entries(data.readings)) {
      if (platform.value && platform.value !== name) continue;
      const reading = cells[spec];
      if (typeof reading === 'string') {
        excluded.push(nameOf(name) + '（' + reading + '）');
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
      offers.push({plan, pay, capacity, monthlyCredits, creditsPerClip:reading.credits, sourceDate:reading.sourceDate});
    }
    const providers = new Set(offers.map(offer => offer.plan.platform));
    for (const name of available.keys()) {
      if (!providers.has(name)) excluded.push(nameOf(name) + '（无' + cycle[0] + '）');
    }
    const fits = byBudget ? offer => offer.capacity > 0 && offer.pay <= amount
      : offer => offer.capacity >= amount;
    const rankBy = byBudget ? (a,b) => b.capacity - a.capacity || a.pay - b.pay
      : (a,b) => a.pay - b.pay || b.capacity - a.capacity;
    const matched = offers.filter(fits).sort(rankBy);
    const best = matched[0];
    const highestCapacity = Math.max(0, ...offers.map(offer => offer.capacity));
    result.textContent = '';
    if (best) {
      result.append(byBudget ? money.format(amount) + ' 预算内，每月最多约 ' : amount.toLocaleString('zh-CN') + ' 条/月，首期最低 ');
      const answer = document.createElement('strong');
      answer.textContent = byBudget ? best.capacity + ' 条' : money.format(best.pay);
      result.append(answer, '（' + cycle[0] + '）');
      const caption = document.createElement('small');
      caption.textContent = nameOf(best.plan.platform) + ' ' + best.plan.tier
        + (byBudget ? ' · 实付 ' + money.format(best.pay) : ' · 月产能约 ' + best.capacity + ' 条')
        + (best.sourceDate ? ' · 扣分沿用留档' : '');
      result.append(caption);
    } else {
      const paidPlans = offers.filter(offer => offer.capacity > 0);
      if (paidPlans.length && byBudget) {
        const entryPrice = Math.min(...paidPlans.map(offer => offer.pay));
        result.textContent = '当前预算没覆盖可出片的档位。该规格的最低首期支出为 ' + money.format(entryPrice) + '。';
      } else if (highestCapacity && !byBudget) {
        result.textContent = '当前单账号最多约 ' + highestCapacity + ' 条/月。减小用量或换规格可查看更多方案。';
      } else {
        result.textContent = '这个组合暂无可计算的方案。';
        if (spec === 5) {
          const change = document.createElement('button');
          change.type = 'button';
          change.className = 'compare-switch-res';
          change.textContent = '试试 480p';
          change.addEventListener('click', () => {
            resolution.value = '0';
            render();
            form.querySelector('[name=resolution]:checked').focus();
          });
          result.append(change);
        }
      }
    }
    const seen = new Set();
    const ranked = showAll.checked ? matched : matched.filter(({plan}) => {
          if (seen.has(plan.platform)) return false;
          seen.add(plan.platform);
          return true;
        });
    const displayed = showAll.checked ? [...ranked, ...offers.filter(offer => !fits(offer)).sort(rankBy)] : ranked;
    if (ranked.length > 1) {
      const next = ranked[1];
      const gap = byBudget ? best.capacity - next.capacity : next.pay - best.pay;
      if (gap > 0) result.querySelector('small').append(byBudget
        ? ' · 比第 2 名每月多 ' + gap + ' 条'
        : ' · 比第 2 名少付 ' + money.format(gap));
    }
    const scale = Math.max(1, ...ranked.map(offer => byBudget ? offer.capacity : offer.pay));
    order.textContent = displayed.length ? (byBudget ? '月产能从高到低 · 条越长，能做越多' : '首期实付从低到高 · 条越短，花钱越少')
      + ' · ' + ranked.length + (showAll.checked ? ' 档符合' : ' 家平台符合') : '';
    displayed.forEach((offer, index) => {
      const tr = rows.insertRow();
      tr.dataset.chartPlan = offer.plan.id;
      tr.tabIndex = -1;
      if (offer === best) tr.className = 'compare-best';
      const title = tr.insertCell();
      const rank = document.createElement('span');
      rank.className = 'compare-rank';
      rank.textContent = index < ranked.length ? String(index + 1).padStart(2, '0') : '—';
      const name = document.createElement('a');
      name.className = 'compare-result-name';
      name.href = '#' + offer.plan.anchor;
      name.textContent = nameOf(offer.plan.platform);
      name.setAttribute('aria-label', '查看 ' + name.textContent + ' 的会员价格');
      const detail = document.createElement('small');
      detail.textContent = offer.plan.tier + ' · ' + offer.monthlyCredits.toLocaleString('zh-CN') + ' 分/月'
        + (offer.sourceDate ? ' · 扣分沿用留档' : '');
      title.append(rank, name, detail);
      const spendCell = tr.insertCell();
      spendCell.textContent = money.format(offer.pay);
      const volumeCell = tr.insertCell();
      volumeCell.textContent = offer.capacity + ' 条';
      const unit = tr.insertCell();
      unit.textContent = fits(offer) ? perClip.format(offer.pay / ((byBudget ? offer.capacity : amount) * cycle[1]))
        : byBudget && offer.pay > amount ? '超预算' : '未达用量';
      if (index < ranked.length) {
        const bar = document.createElement('span');
        bar.className = 'compare-bar';
        bar.setAttribute('aria-hidden', 'true');
        bar.style.background = data.colors[offer.plan.platform];
        bar.style.width = ((byBudget ? offer.capacity : offer.pay) / scale * 100) + '%';
        (byBudget ? volumeCell : spendCell).append(bar);
      }
    });
    table.hidden = !displayed.length;
    const short = [...providers].filter(name => !matched.some(offer => offer.plan.platform === name));
    const notes = [];
    if (short.length) notes.push(short.map(nameOf).join('、') + (byBudget ? ' 在当前预算内暂无可用档位' : ' 的单账号档位未达用量'));
    if (excluded.length) notes.push('当前未计入：' + excluded.join('、'));
    coverage.textContent = notes.join('。') + (notes.length ? '。' : '');
    renderCharts(offers, ranked, byBudget, cycle[1]);
  }
  form.addEventListener('submit', event => event.preventDefault());
  form.addEventListener('change', render);
  [platform, showAll].forEach(input => input.addEventListener('change', render));
  [target, budget].forEach(input => input.addEventListener('input', render));
  form.addEventListener('click', event => {
    const preset = event.target.closest('[data-target], [data-budget]');
    if (!preset) return;
    if (preset.dataset.budget) budget.value = preset.dataset.budget;
    else target.value = preset.dataset.target;
    render();
  });
  document.getElementById('compare-reset').addEventListener('click', () => {
    form.reset();
    mode.value = defaultMode;
    platform.value = '';
    showAll.checked = false;
    render();
  });
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

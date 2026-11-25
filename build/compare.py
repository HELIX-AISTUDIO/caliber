"""Cost comparison calculator for the main visitor flow."""
import json
from html import escape
from pathlib import Path


def membership_anchor(platform):
    return "membership-" + {"即梦": "jimeng", "小云雀": "xiaoyunque"}.get(platform, platform.lower())


def compare_view(rows, readings, updated, periods, colors, logos):
    platforms = list(readings)
    display_names = {"libtv": "LibTV", "Tapnow": "TapNow"}
    plans = []
    for index, row in enumerate(rows):
        plat = row["plat"]
        plans.append({
            "id": index,
            "platform": plat,
            "tier": row["tier"],
            "anchor": membership_anchor(plat),
            "periods": {key: [p["payCNY"], p["cr"]] for key, p in row["byP"].items()},
        })
    data = json.dumps({"plans": plans, "readings": readings, "names": display_names, "colors": colors, "logos": logos,
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
      <h1>视频生成成本榜</h1>
      <p class="compare-date"><span>Seedance 2.5 · 30 秒 · 16:9 · 全能参考</span><span>{len(platforms)} 家平台 · <time datetime="{updated}">{updated}</time></span></p>
    </div>
    <nav class="compare-jump-links" aria-label="成本榜目录">
      <a href="#compare-frontier">价格与产能</a><a href="#compare-records-title">数据来源</a>
    </nav>
  </header>
  <div class="compare-workbench">
  <form id="compare-form" class="compare-form">
    <div class="compare-core">
      <fieldset class="compare-choice compare-mode">
        <legend>对比方式</legend>
        <div>
          <label><input type="radio" name="mode" value="target" checked><span>按月用量</span></label>
          <label><input type="radio" name="mode" value="budget"><span>按预算</span></label>
        </div>
      </fieldset>
      <fieldset class="compare-choice">
        <legend>会员周期</legend>
        <div>{period_options}</div>
      </fieldset>
      <div id="compare-target-panel" class="compare-amount">
        <label class="compare-field" for="compare-target"><span class="filter-caption">每月生成条数</span>
          <span class="compare-input-unit">
            <input id="compare-target" type="number" inputmode="numeric" min="1" max="10000" step="1" value="30" required>
            <span aria-hidden="true">条/月</span>
          </span>
        </label>
        <div class="compare-presets" aria-label="常用月用量">
          <button type="button" data-target="10" aria-pressed="false">10 条</button>
          <button type="button" data-target="30" aria-pressed="true">30 条</button>
          <button type="button" data-target="60" aria-pressed="false">60 条</button>
        </div>
      </div>
      <div id="compare-budget-panel" class="compare-amount" hidden>
        <label class="compare-field" for="compare-budget"><span class="filter-caption">本周期总预算</span>
          <span class="compare-input-unit">
            <input id="compare-budget" type="number" inputmode="decimal" min="1" max="1000000" step="0.01" value="1000" required disabled>
            <span aria-hidden="true">元预算</span>
          </span>
        </label>
        <div class="compare-presets" aria-label="常用周期预算">
          <button type="button" data-budget="300" aria-pressed="false">¥300</button>
          <button type="button" data-budget="1000" aria-pressed="true">¥1,000</button>
          <button type="button" data-budget="3000" aria-pressed="false">¥3,000</button>
        </div>
      </div>
    </div>
    <details id="compare-options" class="compare-options" open>
      <summary>规格与平台 <span id="compare-option-summary">标准版 · 720p · 全部平台</span></summary>
      <div class="compare-option-fields">
        <label class="compare-field" for="compare-model"><span class="filter-caption">模型</span>
          <select id="compare-model">
            <option value="0">标准版</option>
            <option value="2">Flash</option>
            <option value="4">样片模式</option>
          </select>
        </label>
        <fieldset class="compare-choice">
          <legend>分辨率</legend>
          <div>
            <label><input type="radio" name="resolution" value="0"><span>480p</span></label>
            <label><input type="radio" name="resolution" value="1" checked><span>720p</span></label>
          </div>
        </fieldset>
        <label class="compare-field" for="compare-platform"><span class="filter-caption">平台</span>
          <select id="compare-platform"><option value="">全部平台</option>{platform_options}</select>
        </label>
        <button id="compare-reset" type="button" aria-label="重置所有榜单条件">重置</button>
      </div>
    </details>
  </form>
  <section id="compare-results" class="compare-results" aria-labelledby="compare-results-title">
    <header class="compare-result-head">
      <div>
        <h2 id="compare-results-title">会员成本榜</h2>
        <p id="compare-order" class="compare-order"></p>
      </div>
      <fieldset class="compare-choice compare-rank-view" id="compare-rank-view">
        <legend>榜单视图</legend>
        <div>
          <label><input type="radio" name="rank-view" value="table" checked><span>表格</span></label>
          <label><input type="radio" name="rank-view" value="chart"><span>柱图</span></label>
          <label><input type="radio" name="rank-view" value="selected"><span>并排</span></label>
        </div>
      </fieldset>
    </header>
    <p class="compare-result-status" id="compare-status" role="status" tabindex="-1"></p>
    <figure id="compare-bar-figure" class="compare-bar-figure" hidden>
      <figcaption id="compare-bar-label"></figcaption>
      <div class="compare-bars-scroll"><div id="compare-bars" class="compare-bars"></div></div>
    </figure>
    <div id="compare-grid">
      <table aria-label="符合规格的会员方案">
        <thead><tr>
          <th scope="col">排名 · 平台 / 档位</th><th scope="col" id="compare-paid">首期实付</th>
          <th scope="col" id="compare-volume">月产能</th><th scope="col">每条成本</th><th scope="col" class="compare-pick-column">对比</th>
        </tr></thead>
        <tbody id="compare-rows"></tbody>
      </table>
    </div>
    <button id="compare-all" type="button" aria-expanded="false" aria-controls="compare-grid" hidden>查看全部档位</button>
    <section id="compare-selection" class="compare-selection" aria-labelledby="compare-selection-title" hidden>
      <header>
        <div>
          <h3 id="compare-selection-title" tabindex="-1">档位并排对比</h3>
          <p id="compare-selection-scope"></p>
        </div>
        <button type="button" id="compare-selection-back">返回榜单</button>
      </header>
      <p id="compare-selection-empty">在表格的「对比」列选择 2 至 4 个会员档位。</p>
      <div id="compare-selection-table" class="compare-selection-scroll" role="region" aria-label="所选档位的费用与积分" tabindex="0" hidden></div>
    </section>
    <div id="compare-picked" class="compare-picked" hidden>
      <span id="compare-picked-count" role="status"></span>
      <button type="button" id="compare-picked-clear">清空</button>
      <button type="button" id="compare-picked-open">并排比较</button>
    </div>
    <p id="compare-coverage" class="compare-coverage"></p>
    <p id="compare-calc-note" class="compare-calc-note"></p>
    <div id="compare-highlights" class="compare-highlights" hidden></div>
    <nav class="compare-record-links compare-result-links" aria-label="核对价格与来源">
      <a href="#membership-prices">会员报价</a>
      <a href="#canvas-comparison">画布扣分</a>
      <a href="#offers">活动优惠</a>
      <a href="#pricing-evidence">采集截图</a>
    </nav>
    <noscript><p>启用 JavaScript 可以实时计算。<a href="cycles.html#allperiod">查看固定规格的完整对比表</a></p></noscript>
  </section>
  </div>
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
  const options = document.getElementById('compare-options');
  const optionSummary = document.getElementById('compare-option-summary');
  const compact = window.matchMedia('(max-width: 650px)');
  const showAll = document.getElementById('compare-all');
  const rankView = document.getElementById('compare-rank-view');
  const chartView = rankView.querySelector('[value=chart]');
  const selectedView = rankView.querySelector('[value=selected]');
  const selection = document.getElementById('compare-selection');
  const selectionTitle = document.getElementById('compare-selection-title');
  const selectionScope = document.getElementById('compare-selection-scope');
  const selectionEmpty = document.getElementById('compare-selection-empty');
  const selectionTable = document.getElementById('compare-selection-table');
  const pickedBar = document.getElementById('compare-picked');
  const pickedCount = document.getElementById('compare-picked-count');
  const pickedOpen = document.getElementById('compare-picked-open');
  const pickedClear = document.getElementById('compare-picked-clear');
  const picked = new Set();
  const pickLimit = 4;
  const presets = form.querySelectorAll('[data-target], [data-budget]');
  const data = __COMPARE_DATA__;
  const money = new Intl.NumberFormat('zh-CN', {style:'currency', currency:'CNY', trailingZeroDisplay:'stripIfInteger'});
  const perClip = new Intl.NumberFormat('zh-CN', {style:'currency', currency:'CNY'});
  const defaultMode = new URLSearchParams(location.search).get('mode') === 'budget' ? 'budget' : 'target';
  const nameOf = platformName => data.names[platformName] || platformName;
  let includeAll = false;
  __COMPARE_CHARTS__
  mode.value = defaultMode;
  function syncOptionsLayout(){ options.open = !compact.matches; }
  syncOptionsLayout();
  compact.addEventListener('change', syncOptionsLayout);

  function suggest(label, apply){
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'compare-suggestion';
    button.textContent = label;
    button.addEventListener('click', () => {
      apply();
      render();
      result.focus({preventScroll:true});
    });
    result.append(button);
  }

  function addMetric(row, label, value, max, platformColor) {
    const cell = row.insertCell();
    const metric = document.createElement('span');
    metric.className = 'compare-metric';
    const number = document.createElement('span');
    number.textContent = label;
    metric.append(number);
    if (platformColor) {
      const track = document.createElement('span');
      track.className = 'compare-meter';
      track.setAttribute('aria-hidden', 'true');
      const bar = document.createElement('i');
      bar.style.width = (value / max * 100) + '%';
      metric.classList.add('compare-metric-primary');
      bar.style.background = platformColor;
      track.append(bar);
      metric.append(track);
    }
    cell.append(metric);
  }

  function syncPicks(){
    pickedBar.hidden = picked.size === 0;
    pickedCount.textContent = '已选 ' + picked.size + ' / ' + pickLimit + ' 个档位';
    pickedOpen.disabled = picked.size < 2;
    pickedOpen.hidden = selectedView.checked;
    for (const button of rows.querySelectorAll('[data-pick-plan]')) {
      const active = picked.has(Number(button.dataset.pickPlan));
      button.setAttribute('aria-pressed', String(active));
      button.disabled = !active && picked.size >= pickLimit;
    }
  }

  function renderSelection(offers, scope, fits, unitCost, reasonFor){
    selectionScope.textContent = scope;
    const ready = picked.size >= 2;
    selectionEmpty.hidden = ready;
    selectionTable.hidden = !ready;
    selectionTable.replaceChildren();
    if (!ready) return;

    const choices = [...picked].map(id => ({plan:data.plans[id], offer:offers.find(offer => offer.plan.id === id)}));
    const grid = document.createElement('table');
    grid.setAttribute('aria-label', '档位并排对比');
    grid.style.setProperty('--comparison-width', (78 + choices.length * 112) + 'px');
    const header = grid.createTHead().insertRow();
    const metricHead = document.createElement('th');
    metricHead.scope = 'col';
    metricHead.textContent = '指标';
    header.append(metricHead);
    for (const {plan, offer} of choices) {
      const cell = document.createElement('th');
      cell.scope = 'col';
      const name = document.createElement('b');
      name.textContent = nameOf(plan.platform);
      const tier = document.createElement('small');
      tier.textContent = plan.tier + (offer?.sourceDate ? ' · 扣分留档' : '');
      const status = document.createElement('small');
      status.textContent = offer
        ? (fits(offer) ? '' : reasonFor(offer))
        : (platform.value && platform.value !== plan.platform ? '已被平台筛选排除' : '当前规格或周期缺数据');
      cell.append(platformLogo({plan}), name, tier);
      if (status.textContent) cell.append(status);
      header.append(cell);
    }
    const metrics = [
      ['首期实付', offer => money.format(offer.pay)],
      ['月产能', offer => offer.capacity + ' 条'],
      ['每条成本', offer => fits(offer) ? perClip.format(unitCost(offer)) : reasonFor(offer)],
      ['每月积分', offer => offer.monthlyCredits.toLocaleString('zh-CN')],
      ['画布扣分', offer => offer.creditsPerClip.toLocaleString('zh-CN') + ' 分/条'],
    ];
    const body = grid.createTBody();
    for (const [label, format] of metrics) {
      const row = body.insertRow();
      const heading = document.createElement('th');
      heading.scope = 'row';
      heading.textContent = label;
      row.append(heading);
      for (const {offer} of choices) row.insertCell().textContent = offer ? format(offer) : '—';
    }
    selectionTable.append(grid);
  }

  function render(){
    const byBudget = mode.value === 'budget';
    const byChart = chartView.checked;
    const bySelection = selectedView.checked;
    const input = byBudget ? budget : target;
    const amount = input.valueAsNumber;
    const cycle = data.periods[period.value];
    const spec = Number(model.value) + Number(resolution.value);
    const scenario = (byBudget ? money.format(amount) + ' 预算' : amount.toLocaleString('zh-CN') + ' 条/月')
      + ' · ' + cycle[0];
    const available = new Map();
    const excluded = [];
    const offers = [];
    optionSummary.textContent = [model.selectedOptions[0].textContent,
      resolution.value === '0' ? '480p' : '720p', platform.selectedOptions[0].textContent].join(' · ');
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
    showAll.hidden = true;
    selection.hidden = true;
    clearCharts();
    if (!input.validity.valid) {
      result.textContent = byBudget ? '请输入 ¥1 至 ¥1,000,000 的预算，最多保留两位小数。'
        : '请输入 1 到 10,000 之间的整数条数。';
      syncPicks();
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
      const lead = document.createElement('span');
      lead.className = 'compare-answer';
      const answer = document.createElement('strong');
      answer.textContent = byBudget ? best.capacity + ' 条/月' : money.format(best.pay);
      lead.append(byBudget ? '最多可做 ' : '首期最低 ', answer);
      const scope = document.createElement('span');
      scope.className = 'compare-answer-scope';
      scope.textContent = scenario;
      const caption = document.createElement('small');
      caption.textContent = nameOf(best.plan.platform) + ' ' + best.plan.tier
        + (byBudget ? ' · 实付 ' + money.format(best.pay) : '')
        + (best.sourceDate ? ' · 扣分留档' : '');
      result.append(lead, scope, caption);
    } else {
      const paidPlans = offers.filter(offer => offer.capacity > 0);
      if (paidPlans.length && byBudget) {
        const entryPrice = Math.min(...paidPlans.map(offer => offer.pay));
        result.textContent = '当前预算内暂无可出片的档位。';
        suggest('用最低预算 ' + money.format(entryPrice) + ' 重算', () => { budget.value = entryPrice; });
      } else if (highestCapacity && !byBudget) {
        result.textContent = '当前规格的单账号产能低于你输入的用量。';
        suggest('按最高产能 ' + highestCapacity + ' 条/月重算', () => { target.value = highestCapacity; });
      } else {
        result.textContent = '这个组合暂无可计算的方案。';
        if (spec === 5) {
          suggest('切到 480p', () => { resolution.value = '0'; });
        }
      }
    }
    const platformLeaders = new Map();
    for (const offer of matched) {
      if (!platformLeaders.has(offer.plan.platform)) platformLeaders.set(offer.plan.platform, offer);
    }
    const ranked = includeAll ? matched : [...platformLeaders.values()];
    const displayed = includeAll ? [...ranked, ...offers.filter(offer => !fits(offer)).sort(rankBy)] : ranked;
    showAll.hidden = byChart || bySelection || offers.length === platformLeaders.size;
    showAll.setAttribute('aria-expanded', String(includeAll));
    showAll.textContent = includeAll ? '收起完整档位' : '查看全部 ' + offers.length + ' 个档位';
    if (ranked.length > 1) {
      const next = ranked[1];
      const gap = byBudget ? best.capacity - next.capacity : next.pay - best.pay;
      if (gap > 0) result.querySelector('small').append(byBudget
        ? ' · 比第 2 名每月多 ' + gap + ' 条'
        : ' · 比第 2 名少付 ' + money.format(gap));
    }
    const unitCost = offer => offer.pay / ((byBudget ? offer.capacity : amount) * cycle[1]);
    const reasonFor = offer => byBudget ? (offer.pay > amount ? '超预算' : '额度不足') : '未达用量';
    const payMax = Math.max(1, ...displayed.map(offer => offer.pay));
    const volumeMax = Math.max(1, ...displayed.map(offer => offer.capacity));
    order.textContent = displayed.length ? (byBudget ? '产能从高到低' : '实付从低到高')
      + ' · ' + ranked.length + (includeAll ? ' 档' : ' 家') + (byBudget ? '在预算内' : '达标') : '';
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
        + (offer.sourceDate ? ' · 留档扣分' : '');
      title.append(rank, platformLogo(offer), name, detail);
      const matchedOffer = index < ranked.length;
      const platformColor = matchedOffer ? data.colors[offer.plan.platform] : null;
      addMetric(tr, money.format(offer.pay), offer.pay, payMax, byBudget ? null : platformColor);
      addMetric(tr, offer.capacity + ' 条', offer.capacity, volumeMax, byBudget ? platformColor : null);
      const unit = matchedOffer ? unitCost(offer) : null;
      addMetric(tr, matchedOffer ? perClip.format(unit) : reasonFor(offer));
      const pick = document.createElement('button');
      pick.type = 'button';
      pick.className = 'compare-pick';
      pick.dataset.pickPlan = offer.plan.id;
      pick.setAttribute('aria-label', '对比 ' + planName(offer) + '，' + offer.monthlyCredits.toLocaleString('zh-CN') + ' 分/月');
      const pickCell = tr.insertCell();
      pickCell.className = 'compare-pick-column';
      pickCell.append(pick);
    });
    table.hidden = byChart || bySelection || !displayed.length;
    selection.hidden = !bySelection;
    if (bySelection) renderSelection(offers, optionSummary.textContent + ' · ' + scenario, fits, unitCost, reasonFor);
    syncPicks();
    const short = [...providers].filter(name => !matched.some(offer => offer.plan.platform === name));
    const notes = [];
    if (short.length) notes.push(short.map(nameOf).join('、') + (byBudget ? ' 在当前预算内暂无可用档位' : ' 的单账号档位未达用量'));
    if (excluded.length) notes.push('当前未计入：' + excluded.join('、'));
    coverage.textContent = notes.join('。') + (notes.length ? '。' : '');
    renderCharts(offers, ranked, byBudget, cycle[1]);
  }
  form.addEventListener('submit', event => event.preventDefault());
  form.addEventListener('change', render);
  rankView.addEventListener('change', render);
  rows.addEventListener('click', event => {
    const button = event.target.closest('[data-pick-plan]');
    if (!button) return;
    const id = Number(button.dataset.pickPlan);
    if (picked.has(id)) picked.delete(id);
    else if (picked.size < pickLimit) picked.add(id);
    syncPicks();
  });
  pickedOpen.addEventListener('click', () => {
    selectedView.checked = true;
    render();
    if (!selection.hidden) selectionTitle.focus();
  });
  document.getElementById('compare-selection-back').addEventListener('click', () => {
    rankView.querySelector('[value=table]').checked = true;
    render();
    result.focus();
  });
  pickedClear.addEventListener('click', () => {
    picked.clear();
    render();
    (selectedView.checked && !selection.hidden ? selectionTitle : result).focus();
  });
  showAll.addEventListener('click', () => {
    includeAll = !includeAll;
    render();
  });
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
    includeAll = false;
    render();
  });
  render();
})();
"""


DISCLOSURE_JS = r"""
(function(){
  const prices = document.getElementById('membership-platform');
  const priceRows = [...document.querySelectorAll('[data-membership]')];
  function filterPrices(){
    for (const row of priceRows) row.hidden = Boolean(prices.value && row.dataset.membership !== prices.value);
  }
  if (prices) prices.addEventListener('change', filterPrices);

  const canvas = document.getElementById('canvas-comparison');
  if (canvas) {
    const model = document.getElementById('canvas-model');
    const measure = document.getElementById('canvas-measure');
    const periodField = document.getElementById('canvas-period-field');
    const period = document.getElementById('canvas-period');
    function filterCanvas(){
      canvas.dataset.filtered = 'true';
      periodField.hidden = measure.value === 'credits';
      for (const column of canvas.querySelectorAll('[data-canvas-column]')) {
        column.hidden = column.dataset.canvasColumn !== model.value;
      }
      for (const view of canvas.querySelectorAll('[data-canvas-view]')) {
        view.hidden = view.dataset.canvasView !== measure.value;
      }
      for (const row of canvas.querySelectorAll('[data-canvas-period]')) {
        row.hidden = row.dataset.canvasPeriod !== period.value;
      }
    }
    [model,measure,period].forEach(control => control.addEventListener('change', filterCanvas));
    canvas.querySelector('.canvas-controls').hidden = false;
    filterCanvas();
  }

  function reveal(id){
    const target = document.getElementById(id);
    if (!target) return;
    if (prices && target.dataset.membership) {
      prices.value = target.dataset.membership;
      filterPrices();
    }
    for (let node = target; node; node = node.parentElement) {
      if (node.tagName === 'DETAILS') node.open = true;
    }
    return prices && target.dataset.membership ? prices.closest('details') : target;
  }
  function openHash(){
    if (!location.hash) return;
    const target = reveal(location.hash.slice(1));
    if (target) requestAnimationFrame(() => target.scrollIntoView());
  }
  document.addEventListener('click', function(event){
    const link = event.target.closest('a[href^="#"]');
    if (link && link.hash.length > 1 && link.hash === location.hash) {
      event.preventDefault();
      openHash();
    }
  });
  window.addEventListener('hashchange', openHash);
  openHash();
})();
"""

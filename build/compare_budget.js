(function(){
  const data = __COMPARE_DATA__;
  const budgets = [300, 1000, 3000];
  const controls = document.getElementById('member-controls');
  const model = controls.elements.model;
  const resolution = controls.elements.res;
  const period = controls.elements.period;
  const metric = controls.elements.metric;
  const amount = document.getElementById('member-amount');
  const rows = document.getElementById('member-plans');
  const chart = document.getElementById('member-bars');
  const chartHint = document.getElementById('member-chart-hint');
  const chartHelp = chartHint.textContent;
  const status = document.getElementById('member-status');
  const priceFilters = document.getElementById('member-bands');
  const providers = document.getElementById('member-providers');
  const pickBar = document.getElementById('member-picks');
  const compare = document.getElementById('member-compare');
  const money = new Intl.NumberFormat('zh-CN', {style:'currency', currency:'CNY', trailingZeroDisplay:'stripIfInteger'});
  const cents = new Intl.NumberFormat('zh-CN', {style:'currency', currency:'CNY'});
  const picked = new Set();
  let platform = '';
  let offers = [];

  __COMPARE_OFFER__

  const nameOf = key => data.names[key] || key;
  const unit = offer => offer.pay / (offer.capacity * data.periods[period.value][1]);
  const order = (a,b) => metric.value === 'unit'
    ? Math.round(a.pay * 100) * b.capacity - Math.round(b.pay * 100) * a.capacity || b.capacity - a.capacity
    : b.capacity - a.capacity || a.pay - b.pay;
  const within = limit => offers.filter(offer => offer.pay <= limit).sort(order);

  function element(tag, className, label) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (label != null) node.textContent = label;
    return node;
  }

  function logoFor(key) {
    const icon = element('i', 'comparison-mark ' + data.logos[key]);
    icon.setAttribute('aria-hidden', 'true');
    return icon;
  }

  function uniqueOffers(choices) {
    const firstByPlatform = new Map();
    for (const offer of choices) {
      if (!firstByPlatform.has(offer.plan.platform)) firstByPlatform.set(offer.plan.platform, offer);
    }
    return [...firstByPlatform.values()];
  }

  function drawChart() {
    const byUnit = metric.value === 'unit';
    chartHint.textContent = chartHelp;
    document.getElementById('member-chart-title').textContent = byUnit ? '三种预算下的单条均价' : '三种预算下能做多少条';
    document.getElementById('member-figure-note').textContent = byUnit
      ? '每档预算取单条均价最低的三家平台。柱条越短，平均每条花费越低。'
      : '每档预算取月产能最高的三家平台，按用完基础积分估算。';
    const groups = budgets.map(value => uniqueOffers(within(value)).slice(0, 3));
    const measure = offer => byUnit ? unit(offer) : offer.capacity;
    const max = Math.max(1, ...groups.flat().map(measure));
    chart.dataset.barMetric = byUnit ? 'unit' : 'capacity';
    chart.replaceChildren(...groups.map((offersAtPrice, index) => {
      const cap = budgets[index];
      const group = element('div', 'member-bar-group');
      const columns = element('div', 'member-bar-columns');
      for (const offer of offersAtPrice) {
        const key = offer.plan.platform;
        const column = element('button', 'member-column');
        column.type = 'button';
        column.dataset.memberCap = cap;
        column.dataset.memberProvider = key;
        column.style.setProperty('--bar-height', measure(offer) / max * 100 + '%');
        const brief = nameOf(key) + ' ' + offer.plan.tier + ' · ' + money.format(offer.pay) + ' 首期 · '
          + offer.capacity + ' 条/月 · ' + cents.format(unit(offer)) + '/条';
        column.dataset.memberBrief = brief;
        column.setAttribute('aria-label', brief + ' · 按 ' + money.format(cap) + ' 预算筛选');
        const track = element('span', 'member-column-track');
        const value = element('strong', 'member-column-value', byUnit ? cents.format(unit(offer)) : String(offer.capacity));
        value.append(element('small', 'member-column-unit', byUnit ? '/条' : ' 条/月'));
        track.append(element('span', 'member-column-fill'), value);
        const identity = element('span', 'member-column-name');
        identity.append(logoFor(key), element('span', '', nameOf(key)), element('small', '', offer.plan.tier));
        column.append(track, identity);
        columns.append(column);
      }
      if (!offersAtPrice.length) columns.append(element('p', 'member-no-bars', '暂无可出片档位'));
      group.setAttribute('role','group');
      group.setAttribute('aria-label', money.format(cap) + ' 以内');
      group.append(columns, element('h3', 'member-band-title', money.format(cap) + ' 以内'));
      return group;
    }));
  }

  function filterChoice(label, count, active) {
    const button = element('button', 'member-filter-choice');
    button.type = 'button';
    button.setAttribute('aria-pressed', String(active));
    button.append(element('span', '', label), element('small', '', count));
    return button;
  }

  function syncPicks() {
    pickBar.hidden = picked.size === 0;
    document.getElementById('member-pick-count').textContent = '已选 ' + picked.size + ' / 4 档';
    compare.hidden = picked.size < 2 || !amount.validity.valid;
    if (!compare.hidden) {
      const params = new URLSearchParams({model:model.value, res:resolution.value, period:period.value,
        mode:'budget', amount:amount.value, from:'member'});
      if (platform) params.set('platform', platform);
      for (const id of picked) params.append('plan', data.plans[id].key);
      compare.href = 'compare.html?' + params.toString();
    }
    for (const button of rows.querySelectorAll('[data-member-pick]')) {
      const active = picked.has(Number(button.dataset.memberPick));
      button.disabled = !active && picked.size === 4;
      button.setAttribute('aria-pressed', String(active));
      button.textContent = active ? '已加入' : '+ 对比';
    }
  }

  function drawPicker() {
    const all = amount.validity.valid ? within(amount.valueAsNumber) : [];
    const counts = new Map();
    all.forEach(offer => counts.set(offer.plan.platform, (counts.get(offer.plan.platform) || 0) + 1));
    const provided = [...counts.keys()];
    if (platform && !counts.has(platform)) platform = '';
    priceFilters.replaceChildren(...budgets.map(cap => {
      const button = filterChoice(money.format(cap) + ' 以内', within(cap).length + ' 档', amount.valueAsNumber === cap);
      button.dataset.memberCap = cap;
      return button;
    }));
    providers.replaceChildren(...['', ...provided].map(key => {
      const button = filterChoice(key ? nameOf(key) : '全部平台', key ? counts.get(key) : all.length, platform === key);
      button.dataset.memberProvider = key;
      if (key) button.prepend(logoFor(key));
      return button;
    }));
    const visible = platform ? all.filter(offer => offer.plan.platform === platform) : uniqueOffers(all);
    status.textContent = amount.validity.valid
      ? money.format(amount.valueAsNumber) + ' 以内 · ' + (platform ? nameOf(platform) + ' · ' + visible.length + ' 档'
        : provided.length + ' 家平台 · ' + all.length + ' 档可选')
      : '请输入 ¥1 至 ¥1,000,000 以内的有效预算。';
    const max = Math.max(1, ...all.map(offer => offer.capacity));
    rows.replaceChildren(...visible.map(offer => {
      const key = offer.plan.platform;
      const row = element('article', 'member-plan');
      row.dataset.memberPlan = offer.plan.id;
      const info = element('div', 'member-identity');
      const name = element('strong', '', nameOf(key) + ' · ' + offer.plan.tier);
      const price = element('span', '', money.format(offer.pay) + ' / ' + data.periods[period.value][0]);
      const copy = element('div');
      copy.append(name, price);
      info.append(logoFor(key), copy);
      const metrics = element('div', 'member-plan-metrics');
      const first = element('div', 'member-plan-numbers');
      const value = element('strong', '', offer.capacity + ' 条/月');
      first.append(value, element('span', '', cents.format(unit(offer)) + '/条'));
      const meter = element('div', 'member-plan-meter');
      meter.dataset.barMetric = 'capacity';
      meter.setAttribute('aria-hidden', 'true');
      meter.append(element('i'));
      meter.style.setProperty('--capacity-share', offer.capacity / max * 100 + '%');
      const label = element('small', '', offer.monthlyCredits.toLocaleString('zh-CN') + ' 积分/月 · '
        + offer.creditsPerClip.toLocaleString('zh-CN') + ' 分/条' + (offer.sourceLabel ? ' · ' + offer.sourceLabel : ''));
      metrics.append(first, meter, label);
      const actions = element('div', 'member-plan-actions');
      const pick = element('button', 'member-plan-pick');
      pick.type = 'button';
      pick.dataset.memberPick = offer.plan.id;
      pick.setAttribute('aria-label', '对比 ' + nameOf(key) + ' ' + offer.plan.tier + ' ' + money.format(offer.pay));
      const detail = element('a', '', '报价来源');
      detail.href = '#' + offer.plan.anchor;
      actions.append(pick, detail);
      row.append(info, metrics, actions);
      return row;
    }));
    if (amount.validity.valid && !visible.length) {
      rows.append(element('p', 'member-empty', '目前没有符合预算的可计算档位。可调整预算、规格或会员周期。'));
    }
    syncPicks();
  }

  function update() {
    const spec = Number(model.value) + Number(resolution.value);
    offers = data.plans.map(plan => offerAt(plan, spec, period.value)).filter(offer => offer && offer.capacity > 0);
    drawChart();
    drawPicker();
  }

  controls.addEventListener('submit', event => event.preventDefault());
  controls.addEventListener('change', update);
  amount.addEventListener('input', drawPicker);
  priceFilters.addEventListener('click', event => {
    const button = event.target.closest('[data-member-cap]');
    if (!button) return;
    amount.value = button.dataset.memberCap;
    drawPicker();
    priceFilters.querySelector('[aria-pressed=true]')?.focus({preventScroll:true});
  });
  providers.addEventListener('click', event => {
    const button = event.target.closest('[data-member-provider]');
    if (!button) return;
    platform = button.dataset.memberProvider;
    drawPicker();
    providers.querySelector('[aria-pressed=true]')?.focus({preventScroll:true});
  });
  chart.addEventListener('click', event => {
    const column = event.target.closest('[data-member-cap]');
    if (!column) return;
    platform = column.dataset.memberProvider;
    amount.value = column.dataset.memberCap;
    drawPicker();
    amount.focus({preventScroll:true});
    document.getElementById('member-picker').scrollIntoView();
  });
  for (const eventType of ['pointerover', 'focusin']) {
    chart.addEventListener(eventType, event => {
      const column = event.target.closest('[data-member-brief]');
      if (column) chartHint.textContent = column.dataset.memberBrief;
    });
  }
  for (const eventType of ['pointerout', 'focusout']) {
    chart.addEventListener(eventType, event => {
      const column = event.target.closest('[data-member-brief]');
      if (column && !column.contains(event.relatedTarget) && (eventType !== 'pointerout' || !column.matches(':focus-visible'))) {
        chartHint.textContent = chartHelp;
      }
    });
  }
  rows.addEventListener('click', event => {
    const button = event.target.closest('[data-member-pick]');
    if (!button) return;
    const id = Number(button.dataset.memberPick);
    if (picked.has(id)) picked.delete(id);
    else if (picked.size < 4) picked.add(id);
    syncPicks();
  });
  document.getElementById('member-clear').addEventListener('click', () => {
    picked.clear();
    syncPicks();
    amount.focus({preventScroll:true});
  });
  if (location.hash === '#member-picker') {
    const saved = new URLSearchParams(location.search);
    for (const [key, choices] of [['model', model], ['res', resolution], ['period', period]]) {
      const value = saved.get(key);
      if ([...choices].some(input => input.value === value)) choices.value = value;
    }
    if (saved.has('amount')) {
      amount.value = saved.get('amount');
      if (!amount.validity.valid) amount.value = amount.defaultValue;
    }
    platform = saved.get('platform') || '';
    for (const key of saved.getAll('plan').slice(0, 4)) {
      const plan = data.plans.find(item => item.key === key);
      if (plan) picked.add(plan.id);
    }
  }
  update();
})();

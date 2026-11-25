  const barsFigure = document.getElementById('compare-bar-figure');
  const bars = document.getElementById('compare-bars');
  const barsLabel = document.getElementById('compare-bar-label');
  const frontier = document.getElementById('compare-frontier');
  const plot = document.getElementById('compare-frontier-plot');
  const frontierList = document.getElementById('compare-frontier-list');
  const pointDetail = document.getElementById('compare-point-detail');
  const chartPlatforms = document.getElementById('compare-chart-platforms');
  const chartRoot = document.getElementById('compare-tool');
  let currentPoints = [];
  let selected = null;
  let chartPlatform = '';

  function planName(offer) {
    return nameOf(offer.plan.platform) + ' ' + offer.plan.tier;
  }

  function tint(element, offer) {
    element.style.setProperty('--series', data.colors[offer.plan.platform]);
  }

  function platformLogo(offer) {
    const logo = document.createElement('i');
    logo.className = 'comparison-mark ' + data.logos[offer.plan.platform];
    logo.setAttribute('aria-hidden', 'true');
    return logo;
  }

  function axisMax(value) {
    const magnitude = 10 ** Math.floor(Math.log10(Math.max(1, value)));
    return magnitude * [1, 2, 2.5, 5, 10].find(step => step * magnitude >= value);
  }

  function clearCharts() {
    barsFigure.hidden = frontier.hidden = true;
    currentPoints = [];
  }

  function markPoint(offer) {
    const id = offer?.plan.id;
    for (const item of chartRoot.querySelectorAll('[data-chart-plan]')) {
      item.classList.toggle('compare-linked', item.dataset.chartPlan === String(id));
      if (item.tagName === 'BUTTON') {
        item.setAttribute('aria-pressed', String(item.dataset.chartPlan === String(selected?.plan.id)));
      }
    }
  }

  function revealRank(offer) {
    const selector = '[data-chart-plan="' + offer.plan.id + '"]';
    const pendingRow = !rows.querySelector(selector);
    if (table.hidden || pendingRow) {
      rankView.querySelector('[value=table]').checked = true;
      if (pendingRow) includeAll = true;
      render();
    }
    const row = rows.querySelector(selector);
    if (row) {
      drawPointDetail(offer, data.periods[period.value][1]);
      row.focus({preventScroll:true});
      row.scrollIntoView({block:'center'});
    }
  }

  function chartButton(offer, kind, label, action) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = kind;
    button.dataset.chartPlan = offer.plan.id;
    button.setAttribute('aria-label', label);
    button.setAttribute('aria-pressed', 'false');
    tint(button, offer);
    button.addEventListener('click', () => action(offer));
    return button;
  }

  function drawBars(ranked, byBudget) {
    bars.replaceChildren();
    const leading = ranked.slice(0, 10);
    if (!chartView.checked || !leading.length) return;
    const valueOf = byBudget ? offer => offer.capacity : offer => offer.pay;
    const format = byBudget ? value => value.toLocaleString('zh-CN') + ' 条' : value => money.format(value);
    const top = axisMax(Math.max(...leading.map(valueOf)));
    barsLabel.textContent = (byBudget ? '每月约能生成多少条 · 越高越多' : '首期实付 · 越低越省')
      + (ranked.length > leading.length ? ' · 显示前 ' + leading.length + ' 名' : '');
    const axis = document.createElement('div');
    axis.className = 'compare-bar-y';
    [top, top * .75, top * .5, top * .25, 0].forEach(value => {
      const tick = document.createElement('span');
      tick.textContent = format(value);
      axis.append(tick);
    });
    const columns = document.createElement('div');
    columns.className = 'compare-bar-columns';
    bars.style.setProperty('--bar-count', leading.length);
    leading.forEach(offer => {
      const value = valueOf(offer);
      const button = chartButton(offer, 'compare-column', planName(offer) + ' ' + format(value), revealRank);
      const measure = document.createElement('span');
      measure.className = 'compare-column-measure';
      measure.style.setProperty('--bar-height', value / top * 100 + '%');
      const exact = document.createElement('span');
      exact.className = 'compare-column-value';
      exact.textContent = format(value);
      const fill = document.createElement('span');
      fill.className = 'compare-column-fill';
      const label = document.createElement('span');
      label.className = 'compare-column-label';
      const planTier = document.createElement('small');
      planTier.textContent = offer.plan.tier;
      label.append(platformLogo(offer), nameOf(offer.plan.platform), planTier);
      measure.append(exact, fill);
      button.append(measure, label);
      columns.append(button);
    });
    bars.append(axis, columns);
    barsFigure.hidden = false;
  }

  function drawPointDetail(offer, months) {
    selected = offer;
    markPoint(offer);
    pointDetail.replaceChildren();
    if (!offer) return;
    const name = document.createElement('strong');
    name.textContent = planName(offer);
    const summary = document.createElement('small');
    summary.textContent = money.format(offer.pay) + ' 首期 · 约 ' + offer.capacity + ' 条/月 · '
      + perClip.format(offer.pay / (offer.capacity * months)) + '/条'
      + ' · ' + offer.monthlyCredits.toLocaleString('zh-CN') + ' 积分/月'
      + ' · ' + offer.creditsPerClip.toLocaleString('zh-CN') + ' 积分/条'
      + (offer.sourceDate ? ' · 扣分沿用 ' + offer.sourceDate + ' 留档' : '');
    const link = document.createElement('button');
    link.type = 'button';
    link.textContent = '在榜单中查看';
    link.addEventListener('click', () => revealRank(offer));
    pointDetail.append(name, summary, link);
  }

  function drawFrontier(months) {
    plot.replaceChildren();
    frontierList.replaceChildren();
    frontier.hidden = false;
    const hasPoints = currentPoints.length > 0;
    frontier.querySelector('.compare-frontier-layout').hidden = !hasPoints;
    frontier.querySelector('.compare-frontier-data').hidden = !hasPoints;
    pointDetail.hidden = chartPlatforms.hidden = !hasPoints;
    const note = document.getElementById('compare-frontier-note');
    if (!hasPoints) {
      note.textContent = '当前规格和周期没有可绘图的档位。';
      return;
    }
    const providers = [...new Set(currentPoints.map(offer => offer.plan.platform))];
    if (!providers.includes(chartPlatform)) chartPlatform = '';
    chartPlatforms.replaceChildren(...['', ...providers].map(platform => {
      const button = document.createElement('button');
      button.type = 'button';
      button.dataset.chartPlatform = platform;
      button.setAttribute('aria-pressed', String(platform === chartPlatform));
      button.textContent = platform ? nameOf(platform) : '全部平台';
      if (platform) button.style.setProperty('--series', data.colors[platform]);
      return button;
    }));
    const byUnit = frontier.querySelector('[name=frontier-metric]:checked').value === 'unit';
    const xValue = offer => byUnit ? offer.pay / (offer.capacity * months) : offer.pay;
    const shown = chartPlatform ? currentPoints.filter(offer => offer.plan.platform === chartPlatform) : currentPoints;
    const sorted = shown.slice().sort((a,b) => xValue(a) - xValue(b) || b.capacity - a.capacity);
    const least = xValue(sorted[0]);
    const most = xValue(sorted[sorted.length - 1]);
    const isLog = least > 0 && most / least >= 12;
    const low = isLog ? least / 1.17 : 0;
    const high = isLog ? most * 1.17 : axisMax(most * 1.05);
    const xPosition = value => (isLog ? Math.log(value / low) / Math.log(high / low) : value / high) * 100;
    const maxVolume = axisMax(Math.max(...sorted.map(offer => offer.capacity)));
    const yPosition = offer => offer.capacity / maxVolume * 100;
    const leaders = [];
    for (const offer of sorted) {
      if (!leaders.length || offer.capacity > leaders[leaders.length - 1].capacity) leaders.push(offer);
    }
    note.textContent = (byUnit ? '横轴是用完订阅额度后的单条成本。' : '横轴是首期实付。')
      + '竖轴是每月可做条数。虚线标出当前图中档位的中位数，阶梯线标出同等支出或单价下的最高产能。';
    document.getElementById('compare-frontier-axis').textContent =
      (byUnit ? '用满积分时每条成本（人民币）' : '首期实付（人民币）') + (isLog ? ' · 对数刻度' : '');
    document.getElementById('compare-frontier-count').textContent = '图中档位 · ' + sorted.length;
    document.getElementById('compare-frontier-y').textContent = [1, .75, .5, .25, 0].map(fraction => maxVolume * fraction).join('|');
    document.getElementById('compare-frontier-x').textContent = [0, .25, .5, .75, 1].map(fraction => {
      const tick = isLog ? low * (high / low) ** fraction : high * fraction;
      return byUnit ? perClip.format(tick) : money.format(Math.round(tick));
    }).join('|');
    for (const id of ['compare-frontier-y', 'compare-frontier-x']) {
      const axis = document.getElementById(id);
      const ticks = axis.textContent.split('|').map(tick => {
        const span = document.createElement('span');
        span.textContent = tick;
        return span;
      });
      axis.replaceChildren(...ticks);
    }
    const median = values => (values[(values.length - 1) >> 1] + values[values.length >> 1]) / 2;
    plot.style.setProperty('--mid-x', xPosition(median(sorted.map(xValue))) + '%');
    plot.style.setProperty('--mid-y', (100 - median(sorted.map(yPosition).sort((a,b) => a - b))) + '%');
    const zone = document.createElement('span');
    zone.className = 'compare-efficient-zone';
    zone.setAttribute('aria-hidden', 'true');
    if (sorted.length > 1) zone.textContent = (byUnit ? '低单价' : '低支出') + ' · 高产能';
    plot.append(zone);
    const namespace = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(namespace, 'svg');
    svg.setAttribute('viewBox', '0 0 100 100');
    svg.setAttribute('preserveAspectRatio', 'none');
    svg.setAttribute('aria-hidden', 'true');
    const line = document.createElementNS(namespace, 'path');
    line.setAttribute('vector-effect', 'non-scaling-stroke');
    const step = leaders.map((offer, index) => {
      const x = xPosition(xValue(offer));
      const y = 100 - yPosition(offer);
      return index ? 'H ' + x + ' V ' + y : 'M ' + x + ' ' + y;
    }).join(' ');
    line.setAttribute('d', step + ' H 100');
    svg.append(line);
    plot.append(svg);
    const onFrontier = new Set(leaders);
    const select = offer => drawPointDetail(offer, months);
    for (const offer of [...sorted.filter(offer => !onFrontier.has(offer)), ...leaders]) {
      const dot = chartButton(offer, 'compare-plot-point', planName(offer) + '，约 ' + offer.capacity + ' 条/月', select);
      dot.title = planName(offer) + ' · ' + money.format(offer.pay) + ' · ' + offer.capacity + ' 条/月';
      dot.classList.toggle('compare-on-frontier', onFrontier.has(offer));
      dot.style.left = xPosition(xValue(offer)) + '%';
      dot.style.bottom = yPosition(offer) + '%';
      plot.append(dot);
    }
    for (const offer of sorted) {
      const row = chartButton(offer, 'compare-frontier-item', planName(offer) + '，约 ' + offer.capacity + ' 条/月', select);
      const name = document.createElement('span');
      name.textContent = planName(offer);
      const values = document.createElement('span');
      values.textContent = (byUnit ? perClip.format(xValue(offer)) + '/条' : money.format(offer.pay))
        + ' · ' + offer.capacity + ' 条/月';
      row.append(name, values);
      frontierList.append(row);
    }
    drawPointDetail(shown.find(offer => offer.plan.id === selected?.plan.id) || leaders[0], months);
  }

  function renderCharts(offers, ranked, byBudget, months) {
    currentPoints = offers.filter(offer => offer.capacity > 0);
    if (chartView.checked) drawBars(ranked, byBudget);
    drawFrontier(months);
  }

  frontier?.addEventListener('change', () => drawFrontier(data.periods[period.value][1]));
  chartPlatforms?.addEventListener('click', event => {
    const button = event.target.closest('[data-chart-platform]');
    if (!button) return;
    chartPlatform = button.dataset.chartPlatform;
    drawFrontier(data.periods[period.value][1]);
    chartPlatforms.querySelector('[aria-pressed=true]')?.focus({preventScroll:true});
  });
  for (const eventType of ['pointerover', 'focusin']) {
    chartRoot.addEventListener(eventType, event => {
      const item = event.target.closest('[data-chart-plan]');
      if (item) {
        const offer = currentPoints.find(offer => String(offer.plan.id) === item.dataset.chartPlan);
        if (offer) markPoint(offer);
      }
    });
  }
  chartRoot.addEventListener('pointerout', event => {
    const item = event.target.closest('[data-chart-plan]');
    if (item && !item.contains(event.relatedTarget)) markPoint(selected);
  });

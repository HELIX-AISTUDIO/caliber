  const highlights = document.getElementById('compare-highlights');
  const barsFigure = document.getElementById('compare-bar-figure');
  const bars = document.getElementById('compare-bars');
  const barsLabel = document.getElementById('compare-bar-label');
  const frontier = document.getElementById('compare-frontier');
  const plot = document.getElementById('compare-frontier-plot');
  const frontierList = document.getElementById('compare-frontier-list');
  const pointDetail = document.getElementById('compare-point-detail');
  const chartRoot = document.getElementById('compare-tool');
  let currentPoints = [];
  let selected = null;

  function planName(offer) {
    return nameOf(offer.plan.platform) + ' ' + offer.plan.tier;
  }

  function tint(element, offer) {
    element.style.setProperty('--series', data.colors[offer.plan.platform]);
  }

  function axisMax(value) {
    const magnitude = 10 ** Math.floor(Math.log10(Math.max(1, value)));
    return magnitude * [1, 2, 2.5, 5, 10].find(step => step * magnitude >= value);
  }

  function clearCharts() {
    highlights.hidden = barsFigure.hidden = frontier.hidden = true;
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
    if (!rows.querySelector(selector)) {
      showAll.checked = true;
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

  function drawHighlights(offers, ranked, byBudget, months) {
    highlights.replaceChildren();
    if (!ranked.length) return;
    const winner = ranked[0];
    const efficiency = offer => offer.pay / (offer.capacity * months);
    const lowestUnit = offers.filter(offer => offer.capacity > 0)
      .sort((a,b) => efficiency(a) - efficiency(b) || a.pay - b.pay)[0];
    const maxCapacity = offers.slice().sort((a,b) => b.capacity - a.capacity || a.pay - b.pay)[0];
    const cards = [
      [byBudget ? '预算内产能最高' : '达到用量最省', winner,
       money.format(winner.pay) + ' · 约 ' + winner.capacity + ' 条/月'],
      ['基础积分用满时最省', lowestUnit,
       perClip.format(efficiency(lowestUnit)) + ' / 条 · 周期实付 ' + money.format(lowestUnit.pay)],
      ['单账号月产能最高', maxCapacity,
       maxCapacity.capacity + ' 条/月 · 周期实付 ' + money.format(maxCapacity.pay)]
    ];
    for (const [label, offer, description] of cards) {
      const card = document.createElement('div');
      const heading = document.createElement('span');
      heading.textContent = label;
      const link = document.createElement('button');
      link.type = 'button';
      link.textContent = planName(offer);
      link.addEventListener('click', () => revealRank(offer));
      tint(link, offer);
      const detail = document.createElement('small');
      detail.textContent = description + (offer.sourceDate ? ' · 扣分沿用留档' : '');
      card.append(heading, link, detail);
      highlights.append(card);
    }
    highlights.hidden = false;
  }

  function drawBars(ranked, byBudget) {
    bars.replaceChildren();
    const leading = ranked.slice(0, 10);
    if (!leading.length) return;
    const valueOf = byBudget ? offer => offer.capacity : offer => offer.pay;
    const format = byBudget ? value => value.toLocaleString('zh-CN') + ' 条' : value => money.format(value);
    const top = axisMax(Math.max(...leading.map(valueOf)));
    barsLabel.textContent = (byBudget ? '每月约能生成多少条 · 越高越多' : '首期实付 · 越低越省')
      + (ranked.length > leading.length ? ' · 显示前 ' + leading.length + ' 名' : '');
    const axis = document.createElement('div');
    axis.className = 'compare-bar-y';
    [top, top / 2, 0].forEach(value => {
      const tick = document.createElement('span');
      tick.textContent = format(value);
      axis.append(tick);
    });
    const columns = document.createElement('div');
    columns.className = 'compare-bar-columns';
    bars.style.setProperty('--bar-count', leading.length);
    leading.forEach((offer, index) => {
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
      label.textContent = (index + 1) + ' · ' + nameOf(offer.plan.platform);
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
    if (!currentPoints.length) return;
    const byUnit = frontier.querySelector('[name=frontier-metric]:checked').value === 'unit';
    const xValue = offer => byUnit ? offer.pay / (offer.capacity * months) : offer.pay;
    const sorted = currentPoints.slice().sort((a,b) => xValue(a) - xValue(b) || b.capacity - a.capacity);
    const least = xValue(sorted[0]);
    const most = xValue(sorted[sorted.length - 1]);
    const isLog = most / least >= 12;
    const low = isLog ? least / 1.17 : 0;
    const high = isLog ? most * 1.17 : axisMax(most * 1.05);
    const xPosition = value => (isLog ? Math.log(value / low) / Math.log(high / low) : value / high) * 100;
    const maxVolume = axisMax(Math.max(...sorted.map(offer => offer.capacity)));
    const yPosition = offer => offer.capacity / maxVolume * 100;
    const leaders = [];
    for (const offer of sorted) {
      if (!leaders.length || offer.capacity > leaders[leaders.length - 1].capacity) leaders.push(offer);
    }
    document.getElementById('compare-frontier-note').textContent = byUnit
      ? '越左，单条成本越低。越上，每月能做越多。同等单条成本下，连线标出产能最高的档位。'
      : '越左，首期花得越少。越上，每月能做越多。连线标出不同预算下能买到的最高月产能。';
    document.getElementById('compare-frontier-axis').textContent =
      (byUnit ? '用满积分时每条成本（人民币）' : '首期实付（人民币）') + (isLog ? ' · 对数刻度' : '');
    document.getElementById('compare-frontier-y').textContent = [maxVolume, maxVolume / 2, 0].join('|');
    document.getElementById('compare-frontier-x').textContent = [0, .5, 1].map(fraction => {
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
      dot.classList.toggle('compare-on-frontier', onFrontier.has(offer));
      dot.style.left = xPosition(xValue(offer)) + '%';
      dot.style.bottom = yPosition(offer) + '%';
      plot.append(dot);
    }
    for (const offer of leaders) {
      const row = chartButton(offer, 'compare-frontier-item', planName(offer) + '，约 ' + offer.capacity + ' 条/月', select);
      const name = document.createElement('span');
      name.textContent = planName(offer);
      const values = document.createElement('span');
      values.textContent = (byUnit ? perClip.format(xValue(offer)) + '/条' : money.format(offer.pay))
        + ' · ' + offer.capacity + ' 条/月';
      row.append(name, values);
      frontierList.append(row);
    }
    drawPointDetail(currentPoints.find(offer => offer.plan.id === selected?.plan.id) || leaders[0], months);
    frontier.hidden = false;
  }

  function renderCharts(offers, ranked, byBudget, months) {
    currentPoints = offers.filter(offer => offer.capacity > 0);
    drawHighlights(currentPoints, ranked, byBudget, months);
    drawBars(ranked, byBudget);
    drawFrontier(months);
  }

  frontier.addEventListener('change', () => drawFrontier(data.periods[period.value][1]));
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

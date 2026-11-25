  const overview = document.getElementById('benchmark-overview');

  function drawOverview(offers, leaders, rankBy, byBudget, scope) {
    const caseList = document.getElementById('overview-cases');
    const providerList = document.getElementById('overview-platforms');
    const measure = byBudget ? '预算' : '用量';
    const resultFor = offer => byBudget ? offer.capacity + ' 条/月' : money.format(offer.pay);
    overview.hidden = false;
    document.getElementById('overview-usage-title').textContent = byBudget ? '常用预算' : '常用月用量';
    document.getElementById('overview-provider-title').textContent = byBudget ? '各平台预算内产能' : '各平台达标档位';
    document.getElementById('overview-scope').textContent = scope.specName + ' · ' + scope.cycle[0];

    const ordered = offers.slice().sort(rankBy);
    const choices = [...presets].map(preset => Number(byBudget ? preset.dataset.budget : preset.dataset.target)).filter(Boolean);
    caseList.replaceChildren(...choices.map(amount => {
      const best = ordered.find(offer => byBudget ? offer.capacity > 0 && offer.pay <= amount : offer.capacity >= amount);
      const item = document.createElement('button');
      item.type = 'button';
      item.className = 'overview-case';
      item.setAttribute('aria-pressed', String(scope.amount === amount));
      const header = document.createElement('span');
      header.textContent = byBudget ? money.format(amount) + ' 以内' : '每月 ' + amount + ' 条';
      const metric = document.createElement('strong');
      metric.textContent = best ? resultFor(best) : '暂无档位';
      const detail = document.createElement('small');
      detail.textContent = best ? planName(best) : '查看这一' + measure + '的覆盖情况';
      item.append(header, metric, detail);
      item.addEventListener('click', () => {
        (byBudget ? budget : target).value = amount;
        rankView.querySelector('[value=table]').checked = true;
        render();
        result.focus({preventScroll:true});
        document.getElementById('benchmark-board').scrollIntoView({behavior:'instant'});
      });
      return item;
    }));

    const providers = [...leaders.keys(), ...Object.keys(data.readings).filter(platform => !leaders.has(platform))]
      .filter(matchesPlatform);
    providerList.replaceChildren(...providers.map(platform => {
      const leader = leaders.get(platform);
      const reading = data.readings[platform][scope.spec];
      const available = offers.filter(offer => offer.plan.platform === platform);
      const item = document.createElement(leader ? 'button' : 'div');
      item.className = 'overview-platform';
      const heading = document.createElement('span');
      heading.className = 'overview-platform-name';
      heading.append(platformLogo({plan: {platform}}), nameOf(platform));
      const metric = document.createElement('strong');
      metric.textContent = leader ? resultFor(leader) : '—';
      const detail = document.createElement('small');
      detail.textContent = leader
        ? leader.plan.tier + (leader.sourceDate ? ' · 留档' : '')
        : (typeof reading === 'string' ? reading : available.length
          ? (scope.issue ? '请输入有效' + measure : byBudget ? '预算内暂无可出片档位' : '暂无达标档位') : '无此周期');
      if (leader) {
        item.type = 'button';
        item.addEventListener('click', () => revealRank(leader));
      }
      item.append(heading, metric, detail);
      return item;
    }));
    if (!providers.length) providerList.textContent = '没有匹配的平台。';
  }

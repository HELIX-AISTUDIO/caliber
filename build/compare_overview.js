  const overview = document.getElementById('benchmark-overview');
  const profile = document.querySelector('.benchmark-profile');

  function drawProfile(leaders, byBudget, scope) {
    const sample = [...leaders.values()].slice(0, 3);
    document.getElementById('profile-title').textContent = scope.issue
      ? '调整榜单条件'
      : byBudget ? money.format(scope.amount) + ' 内的月产能'
      : '每月 ' + scope.amount.toLocaleString('zh-CN') + ' 条的首期实付';
    document.getElementById('profile-scope').textContent = scope.specName + ' · ' + scope.cycle[0];
    const evidence = document.getElementById('profile-evidence');
    evidence.hidden = !sample.length;
    if (sample.length) evidence.href = data.recordsPage + '#' + sample[0].plan.anchor;
    const rows = document.getElementById('profile-rows');
    const formatCount = value => value.toLocaleString('zh-CN');
    rows.replaceChildren(...sample.map((offer, index) => {
      const value = byBudget ? formatCount(offer.capacity) : money.format(offer.pay);
      const label = '查看 ' + planName(offer) + '，' + value + (byBudget ? ' 条/月' : '');
      const button = chartButton(offer, 'profile-row', label, revealRank);
      const identity = document.createElement('span');
      identity.className = 'profile-identity';
      const name = document.createElement('span');
      name.className = 'profile-name';
      name.append(platformLogo(offer), nameOf(offer.plan.platform));
      const tier = document.createElement('small');
      tier.textContent = offer.plan.tier + (offer.sourceDate ? ' · 扣分留档' : '');
      identity.append(name, tier);
      const amount = document.createElement('strong');
      amount.textContent = value;
      const unit = document.createElement('span');
      unit.textContent = byBudget ? '条/月' : '';
      if (index > 0) {
        button.classList.add('profile-alternative');
        const rank = document.createElement('span');
        rank.className = 'profile-rank';
        rank.textContent = String(index + 1).padStart(2, '0');
        const metric = document.createElement('span');
        metric.className = 'profile-alt-metric';
        metric.append(amount, unit);
        button.append(rank, identity, metric);
        return button;
      }
      button.classList.add('profile-feature');
      const caption = document.createElement('span');
      caption.className = 'profile-caption';
      caption.textContent = byBudget ? '预算内最多可生成 · 条/月' : '达标最低实付';
      const used = (byBudget ? offer.capacity : scope.amount) * offer.creditsPerClip;
      const tape = document.createElement('span');
      tape.className = 'profile-credit-meter';
      tape.setAttribute('aria-hidden', 'true');
      tape.style.setProperty('--fill', used / offer.monthlyCredits * 100 + '%');
      const credits = document.createElement('span');
      credits.className = 'profile-credit-labels';
      const consumed = document.createElement('span');
      consumed.textContent = '预计用 ' + formatCount(used) + ' 分';
      const granted = document.createElement('span');
      granted.textContent = '每月发放 ' + formatCount(offer.monthlyCredits) + ' 分';
      credits.append(consumed, granted);
      button.append(amount, caption, tape, credits, identity);
      return button;
    }));
    if (!sample.length) rows.textContent = scope.issue || '当前条件下暂无可比较的档位。';
    profile.hidden = false;
  }

  function drawOverview(offers, leaders, rankBy, byBudget, scope) {
    drawProfile(leaders, byBudget, scope);
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
      const detail = document.createElement('span');
      detail.className = 'overview-case-detail';
      if (best) detail.append(platformLogo(best), planName(best));
      else detail.textContent = '查看这一' + measure + '的覆盖情况';
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

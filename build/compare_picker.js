  const pickerSearch = document.getElementById('workspace-search');
  const pickerPlatforms = document.getElementById('workspace-platforms');
  const pickerGrid = document.getElementById('workspace-plan-grid');
  const pickerMore = document.getElementById('workspace-plan-more');
  const pickerClear = document.getElementById('workspace-search-clear');
  const pickerShortcuts = document.getElementById('workspace-shortcuts');
  const pickerColumns = document.getElementById('workspace-columns');
  const trayEmpty = document.getElementById('workspace-tray-empty');
  const pickerPageSize = 12;
  let pickerPlatform = '';
  let pickerExpanded = false;
  let pickerCatalog = [];

  function workspacePlan(plan, spec) {
    return {
      plan,
      quote: plan.periods[period.value],
      reading: readingFor(plan, spec, period.value),
      offer: offerAt(plan, spec, period.value),
    };
  }

  function pickerNode(tag, className, label) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (label != null) node.textContent = label;
    if (tag === 'button') node.type = 'button';
    return node;
  }

  function drawPickerPlatforms() {
    const counts = new Map();
    for (const {plan} of pickerCatalog) counts.set(plan.platform, (counts.get(plan.platform) || 0) + 1);
    pickerPlatforms.replaceChildren(...['', ...Object.keys(data.readings)].map(key => {
      const filter = pickerNode('button', 'workspace-platform');
      filter.dataset.workspacePlatform = key;
      filter.setAttribute('aria-pressed', String(key === pickerPlatform));
      if (key) filter.append(platformLogo({plan:{platform:key}}));
      filter.append(pickerNode('span', '', key ? nameOf(key) : '全部平台'),
        pickerNode('small', '', key ? counts.get(key) || 0 : pickerCatalog.length));
      return filter;
    }));
  }

  function drawPickerPlans() {
    const normal = text => text.normalize('NFKC').toLowerCase().replace(/[\s,，·]+/g, '');
    const keyword = normal(pickerSearch.value);
    const matching = pickerCatalog.filter(({plan, quote}) => {
      if (pickerPlatform && plan.platform !== pickerPlatform) return false;
      const credits = quote?.[1] ?? Object.values(plan.periods)[0][1];
      return normal(nameOf(plan.platform) + plan.tier + credits).includes(keyword);
    });
    const visible = pickerExpanded ? matching : matching.slice(0, pickerPageSize);
    document.getElementById('workspace-plan-status').textContent = matching.length
      ? (visible.length < matching.length ? '显示 ' + visible.length + ' / ' : '') + matching.length + ' 个档位'
      : '没有匹配档位。可以更换关键词或选择全部平台。';
    pickerMore.hidden = matching.length <= pickerPageSize;
    pickerClear.hidden = !keyword || matching.length > 0;
    pickerMore.textContent = pickerExpanded ? '收起档位列表' : '显示全部 ' + matching.length + ' 个档位';
    pickerMore.setAttribute('aria-expanded', String(pickerExpanded && !pickerMore.hidden));
    pickerColumns.hidden = visible.length === 0;
    pickerGrid.replaceChildren(...visible.map(({plan, quote, reading, offer}) => {
      const active = picked.has(plan.id);
      const card = pickerNode('button', 'workspace-plan');
      card.dataset.workspacePlan = plan.id;
      card.setAttribute('aria-pressed', String(active));
      card.disabled = !active && picked.size >= pickLimit;
      const label = pickerNode('span', 'workspace-plan-label');
      label.append(pickerNode('b', '', nameOf(plan.platform) + ' · ' + plan.tier));
      const availability = quote ? quote[1].toLocaleString('zh-CN') + ' 分/月' : '无' + data.periods[period.value][0];
      label.append(pickerNode('small', '', availability + (quote && typeof reading === 'string' ? ' · ' + reading : '')));
      const identity = pickerNode('span', 'workspace-plan-identity');
      identity.append(platformLogo({plan}), label);
      const capacity = pickerNode('span', 'workspace-plan-capacity', offer ? offer.capacity + ' 条' : '—');
      capacity.prepend(pickerNode('small', 'workspace-compact-label', '月产能'));
      const price = pickerNode('span', 'workspace-plan-price', quote ? money.format(quote[0]) : '—');
      const action = pickerNode('i', 'workspace-pick-icon');
      action.setAttribute('aria-hidden', 'true');
      card.append(identity, capacity, price, action);
      return card;
    }));
  }

  function syncWorkspaceTray(spec) {
    pickedBar.dataset.hasPicks = String(picked.size > 0);
    pickedCount.textContent = picked.size + ' / ' + pickLimit;
    pickedCount.setAttribute('aria-label', '已选 ' + picked.size + ' 档，共可选 ' + pickLimit + ' 档');
    pickedOpen.disabled = selection.hidden;
    trayEmpty.hidden = picked.size > 0;
    pickedClear.hidden = picked.size === 0;
    pickedPlans.replaceChildren(...[...picked].map(id => {
      const {plan, quote} = workspacePlan(data.plans[id], spec);
      const name = nameOf(plan.platform) + ' · ' + plan.tier;
      const credits = quote ? quote[1].toLocaleString('zh-CN') + ' 分/月' : '无' + data.periods[period.value][0];
      const meta = quote ? money.format(quote[0]) + ' · ' + credits : credits;
      const remove = pickerNode('button', 'workspace-tray-plan');
      remove.dataset.removePlan = id;
      remove.setAttribute('aria-label', '移除 ' + name + '，' + credits);
      const info = pickerNode('span', 'workspace-tray-plan-info');
      info.append(pickerNode('b', '', name), pickerNode('small', '', meta));
      const close = pickerNode('i', 'workspace-tray-remove');
      close.setAttribute('aria-hidden', 'true');
      remove.append(platformLogo({plan}), info, close);
      return remove;
    }));
  }

  function renderWorkspacePicker(spec, scope, byBudget, fits, issue) {
    pickerCatalog = data.plans.map(plan => workspacePlan(plan, spec))
      .sort((a,b) => (a.quote?.[0] ?? Infinity) - (b.quote?.[0] ?? Infinity) || a.plan.id - b.plan.id);
    document.getElementById('workspace-picker-scope').textContent = scope;
    const pickerError = document.getElementById('workspace-picker-error');
    pickerError.hidden = !issue;
    pickerError.textContent = issue;
    drawPickerPlatforms();
    drawPickerPlans();
    pickerShortcuts.replaceChildren();
    if (issue) return;
    const eligible = pickerCatalog.filter(item => item.offer && fits(item.offer));
    if (byBudget) eligible.sort((a,b) => b.offer.capacity - a.offer.capacity || a.quote[0] - b.quote[0]);
    const first = eligible[0];
    if (!first) return;
    const other = eligible.find(item => item.plan.platform !== first.plan.platform);
    const upgrade = eligible.find(item => item.plan.platform === first.plan.platform && item.plan.id !== first.plan.id);
    for (const [label, next] of [['比两家平台', other], ['比同平台两档', upgrade]]) {
      if (!next) continue;
      const button = pickerNode('button', 'workspace-shortcut');
      button.dataset.workspacePair = first.plan.id + ',' + next.plan.id;
      const firstName = planName(first.offer);
      const nextName = planName(next.offer);
      const description = firstName === nextName
        ? firstName + ' · ' + first.quote[1].toLocaleString('zh-CN') + ' / ' + next.quote[1].toLocaleString('zh-CN') + ' 分/月'
        : firstName + ' / ' + nextName;
      const marks = pickerNode('span', 'workspace-shortcut-marks');
      marks.append(platformLogo(first), platformLogo(next));
      const copy = pickerNode('span', 'workspace-shortcut-copy');
      copy.append(pickerNode('b', '', label), pickerNode('small', '', description));
      const arrow = pickerNode('i', 'workspace-arrow');
      arrow.setAttribute('aria-hidden', 'true');
      button.append(marks, copy, arrow);
      button.disabled = picked.size > 0;
      pickerShortcuts.append(button);
    }
  }

  function bindWorkspacePicker() {
    pickerSearch.addEventListener('input', () => {
      pickerExpanded = false;
      drawPickerPlans();
    });
    pickerPlatforms.addEventListener('click', event => {
      const filter = event.target.closest('[data-workspace-platform]');
      if (!filter) return;
      pickerPlatform = filter.dataset.workspacePlatform;
      pickerExpanded = false;
      for (const button of pickerPlatforms.querySelectorAll('button')) {
        button.setAttribute('aria-pressed', String(button === filter));
      }
      drawPickerPlans();
    });
    pickerGrid.addEventListener('click', event => {
      const card = event.target.closest('[data-workspace-plan]');
      if (!card) return;
      const id = Number(card.dataset.workspacePlan);
      if (picked.has(id)) picked.delete(id);
      else if (picked.size < pickLimit) picked.add(id);
      render();
      pickerGrid.querySelector('[data-workspace-plan="' + id + '"]')?.focus({preventScroll:true});
    });
    pickerMore.addEventListener('click', () => {
      pickerExpanded = !pickerExpanded;
      drawPickerPlans();
    });
    pickerClear.addEventListener('click', () => {
      pickerSearch.value = '';
      pickerExpanded = false;
      drawPickerPlans();
      pickerSearch.focus();
    });
    document.querySelector('.workspace-edit').addEventListener('click', event => {
      event.preventDefault();
      pickerSearch.focus({preventScroll:true});
      document.getElementById('workspace-picker').scrollIntoView({block:'start'});
    });
    pickerShortcuts.addEventListener('click', event => {
      const shortcut = event.target.closest('[data-workspace-pair]');
      if (!shortcut || picked.size) return;
      for (const id of shortcut.dataset.workspacePair.split(',')) picked.add(Number(id));
      render();
      pickedOpen.click();
    });
  }

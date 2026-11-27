"""Cost comparison calculator for the main visitor flow."""
import json
from html import escape
from pathlib import Path


def membership_anchor(platform):
    return "membership-" + {"即梦": "jimeng", "小云雀": "xiaoyunque",
                            "RunningHub RHTV": "runninghub-rhtv"}.get(platform, platform.lower())


DISPLAY_NAMES = {"libtv": "LibTV", "Tapnow": "TapNow"}
RESOLUTIONS = ("480p", "720p")
DEFAULT_RESOLUTION = RESOLUTIONS[0]


def compare_dataset(rows, readings, periods, colors, logos, records_page):
    plans = []
    for index, row in enumerate(rows):
        plat = row["plat"]
        plans.append({
            "id": index,
            "key": f"{plat}/{row['tier']}/{row['monthly']}",
            "platform": plat,
            "tier": row["tier"],
            "anchor": membership_anchor(plat),
            "periods": {key: [p["payCNY"], p["cr"]] for key, p in row["byP"].items()},
        })
    return {"plans": plans, "readings": readings, "names": DISPLAY_NAMES, "colors": colors, "logos": logos,
            "recordsPage": records_page, "periods": {key: [label, months] for key, label, months, _ in periods}}


def compare_view(rows, readings, updated, periods, colors, logos, records_page="", workspace=False):
    platforms = list(readings)
    dataset = compare_dataset(rows, readings, periods, colors, logos, records_page)
    plans = dataset["plans"]
    data = json.dumps(dataset, ensure_ascii=False).replace("<", "\\u003c")
    def option_row(group, value, title, description, *, checked=False, mark=""):
        icon = f'<i class="comparison-mark {escape(mark)}" aria-hidden="true"></i>' if mark else ""
        return (f'<label class="filter-option"><input type="radio" name="{group}" value="{escape(value)}"'
                f'{" checked" if checked else ""}><span class="filter-option-face">{icon}'
                f'<span class="filter-option-copy"><strong>{escape(title)}</strong><small>{escape(description)}</small></span>'
                f'<i class="filter-check" aria-hidden="true"></i></span></label>')

    resolution_options = "".join(
        f'<label><input type="radio" name="resolution" value="{index}"'
        f'{" checked" if label == DEFAULT_RESOLUTION else ""}><span>{label}</span></label>'
        for index, label in enumerate(RESOLUTIONS)
    )
    period_options = "".join(
        option_row("period", key, label, f"比较 {months} 个月的首期实付。", checked=key == "m")
        for key, label, months, _ in periods
    )
    # Icons belong to the comparison criteria. View tabs use text alone.
    def criterion(path, label):
        return (f'<span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                f'stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" '
                f'aria-hidden="true"><path d="{path}"/></svg>{label}</span>')

    volume = criterion("M4 20v-5m5 5v-9m5 9V8m5 12V4", "按月用量")
    budget = criterion("M3 7h18v12H3z M3 7V5l15-2v4 M16 11h5v4h-5z", "按预算")
    standard = criterion("M3 6h18v12H3z M3 10h18 M8 6l-3 4m9-4-3 4m9-4-3 4", "标准版")
    flash = criterion("m14 2-10 12h7l-1 8 10-13h-7z", "Flash")
    sample = criterion("M6 3H3v4m15-4h3v4M3 17v4h4m14-4v4h-4 M9 8l7 4-7 4z", "样片模式")
    mode_choices = f"""
          <label><input type="radio" name="mode" value="target" checked>{volume}</label>
          <label><input type="radio" name="mode" value="budget">{budget}</label>
"""
    platform_marks = "".join(
        f'<i class="comparison-mark {escape(logos[name])}" title="{escape(DISPLAY_NAMES.get(name, name))}"></i>'
        for name in platforms
    )
    mode_fields = """<fieldset class="compare-choice">
      <legend>计算方式</legend>
      <div><label><input type="radio" name="mode" value="target" checked><span>按月用量</span></label>
      <label><input type="radio" name="mode" value="budget"><span>按预算</span></label></div>
    </fieldset>""" if workspace else ""
    heading = f"""
  <header class="compare-heading workspace-heading">
    <nav class="workspace-links" aria-label="相关页面">
      <a class="workspace-back" id="compare-selection-back" href="index.html">返回成本榜</a>
      <a class="workspace-quotes" href="{records_page}#membership-prices">会员报价</a>
    </nav>
    <h1>会员方案对比</h1>
    <p>在相同视频规格下，比较 2 至 4 个会员档位。</p>
  </header>
""" if workspace else f"""
  <header id="cost" class="benchmark-heading">
    <div class="benchmark-intro">
      <h1>同一套视频规格<br>比较各平台会员成本</h1>
      <p class="benchmark-intro-copy">按月用量或预算，<span>查看首期实付、月产能和每条成本。</span></p>
      <nav class="benchmark-intro-links" aria-label="开始比较">
        <a class="benchmark-primary" href="#benchmark-board">查看完整榜单<i aria-hidden="true"><svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14m-7-7 7 7-7 7"/></svg></i></a>
        <a href="{records_page}#member-budgets">按预算选会员</a>
        <a href="glossary.html#scope">计算口径</a>
      </nav>
      <div class="benchmark-sample">
        <div class="benchmark-platform-marks" aria-hidden="true">{platform_marks}</div>
        <p><span>{len(platforms)} 家平台</span><span> · {len(plans)} 个会员档位</span><span> · <time datetime="{updated}">{updated} 更新</time></span></p>
      </div>
    </div>
    <figure class="benchmark-profile" aria-labelledby="profile-title" hidden>
      <figcaption>
        <div>
          <h2 id="profile-title">每月 30 条的首期实付</h2>
          <p id="profile-scope"></p>
        </div>
        <button type="button" id="profile-toggle" aria-expanded="false" aria-controls="profile-calculation" hidden>积分明细</button>
      </figcaption>
      <div id="profile-rows" class="profile-rows"></div>
      <div id="profile-calculation" class="profile-calculation" hidden>
        <dl id="profile-metrics"></dl>
        <a href="{records_page}#canvas-comparison">查看画布扣分依据</a>
      </div>
      <p class="profile-note"><span>Seedance 2.5 · 30 秒 · 16:9 · 全能参考</span> <a id="profile-evidence" hidden>报价来源</a></p>
    </figure>
  </header>
"""
    overview = "" if workspace else f"""
  <section class="benchmark-overview" id="benchmark-overview" aria-label="成本总览">
    <div class="overview-panel overview-usage">
      <header><h2 id="overview-usage-title">常用月用量</h2><p id="overview-scope"></p></header>
      <div id="overview-cases" class="overview-cases"></div>
    </div>
    <div class="overview-panel overview-providers">
      <header><h2 id="overview-provider-title">各平台达标档位</h2><a href="#benchmark-board">完整榜单</a></header>
      <div id="overview-platforms" class="overview-platforms"></div>
    </div>
  </section>
  <header class="benchmark-board-title" id="benchmark-board">
    <div><h2>会员档位榜</h2></div>
    <div class="compare-jump-links">
      <a href="#compare-frontier">价格与产能分析</a>
      <button type="button" data-share="table">复制榜单链接</button>
    </div>
  </header>
"""
    board_mode = "" if workspace else f"""
      <fieldset class="compare-choice compare-mode-choice">
        <legend>计算方式</legend>
        <div>{mode_choices}</div>
      </fieldset>
"""
    summary = "" if workspace else """
    <div class="benchmark-summary">
      <div class="compare-result-status" id="compare-status" role="status" tabindex="-1"></div>
      <a class="benchmark-summary-link" id="compare-answer-link" hidden>查看会员报价</a>
    </div>
"""
    rank_toolbar = "" if workspace else """
      <fieldset class="compare-choice compare-rank-view" id="compare-rank-view">
        <legend>榜单视图</legend>
        <div>
          <label><input type="radio" name="rank-view" value="table" checked><span>榜单</span></label>
          <label><input type="radio" name="rank-view" value="chart"><span>价格与产能</span></label>
        </div>
      </fieldset>
      <label class="compare-search">
        <input type="search" id="compare-search" aria-label="搜索平台" placeholder="搜索平台" autocomplete="off">
      </label>
"""
    board_note = "" if workspace else """
      <div class="board-guide"><span>默认展示每家平台的达标档位，可切换档位或加入对比。</span>
        <a href="glossary.html#scope">计算口径说明 <span aria-hidden="true">→</span></a></div>"""
    sort_options = "".join(
        f'<button type="button" data-order="{key}" data-direction="{direction}" aria-pressed="false">'
        f'<span class="filter-option-copy"><strong>{title}</strong><small>{description}</small></span>'
        f'<i class="filter-check" aria-hidden="true"></i></button>'
        for key, direction, title, description in (
            ("pay", "asc", "首期实付最低", "优先查看本周期付款最少的方案。"),
            ("pay", "desc", "首期实付最高", "优先查看本周期付款最多的方案。"),
            ("capacity", "desc", "月产能最高", "每月可生成条数最多的方案排在前面。"),
            ("capacity", "asc", "月产能最低", "每月可生成条数最少的方案排在前面。"),
            ("unit", "asc", "每条成本最低", "优先查看平均每条视频成本最低的方案。"),
            ("unit", "desc", "每条成本最高", "优先查看平均每条视频成本最高的方案。"),
        )
    )
    sort_menu = "" if workspace else f"""
      <details class="compare-options board-sort" id="board-sort">
        <summary aria-controls="board-sort-panel">排名 <b id="board-sort-label">按实付</b></summary>
        <div class="filter-popover" id="board-sort-panel" role="region" aria-labelledby="board-sort-title">
          <header class="filter-popover-heading"><h2 id="board-sort-title">排名方式</h2>
            <button class="filter-popover-close" type="button" aria-label="关闭排名方式"></button></header>
          <div class="board-sort-options">{sort_options}</div>
          <div class="filter-popover-footer"><small>排序适用于当前条件下符合要求的档位。</small></div>
        </div>
      </details>"""
    tabs = [("period", "会员周期"), ("amount", "用量条件")]
    platform_fields = ""
    if not workspace:
        tabs.append(("platform", "平台"))
        choices = option_row("provider", "", "全部平台", f"比较收录的 {len(platforms)} 家平台。", checked=True)
        for name in platforms:
            count = sum(plan["platform"] == name for plan in plans)
            choices += option_row("provider", name, DISPLAY_NAMES.get(name, name), f"收录 {count} 个会员档位。",
                                  mark=logos[name])
        platform_fields = f'<div id="filter-platform" role="tabpanel" aria-labelledby="tab-platform" hidden>{choices}</div>'
    filter_tabs = "".join(
        f'<button type="button" role="tab" id="tab-{key}" aria-controls="filter-{key}" '
        f'aria-selected="{str(key == "period").lower()}" tabindex="{0 if key == "period" else -1}">{label}</button>'
        for key, label in tabs
    )
    picked = """
    <aside id="compare-picked" class="workspace-tray" aria-labelledby="workspace-tray-title" data-has-picks="false">
      <div class="workspace-tray-head">
        <h2 id="workspace-tray-title">已选方案</h2>
        <span id="compare-picked-count" role="status" aria-label="已选 0 档，共可选 4 档">0 / 4</span>
      </div>
      <p id="workspace-tray-empty">从列表选两档，即可并排查看价格和产能。</p>
      <div id="compare-picked-plans" class="workspace-tray-plans" aria-label="已选档位"></div>
      <div class="workspace-tray-actions">
        <button type="button" id="compare-picked-clear" hidden>清空</button>
        <button type="button" id="compare-picked-open" aria-controls="compare-selection" disabled>查看对比<i class="workspace-arrow" aria-hidden="true"></i></button>
      </div>
    </aside>
""" if workspace else """
    <div id="compare-picked" class="compare-picked" hidden>
      <div id="compare-picked-plans" class="compare-picked-plans" aria-label="已选档位"></div>
      <span id="compare-picked-count" role="status"></span>
      <button type="button" id="compare-picked-clear">清空</button>
      <button type="button" id="compare-picked-open">并排比较</button>
    </div>
"""
    record_links = f"""
    <nav class="compare-record-links compare-result-links" aria-label="核对价格与来源">
      <a href="{records_page}#membership-prices">会员报价</a>
      <a href="{records_page}#canvas-comparison">画布扣分</a>
      <a href="{records_page}#offers">活动优惠</a>
      <a href="{records_page}#pricing-evidence">采集截图</a>
    </nav>
"""
    tools = f"""
  <form id="compare-form" class="compare-form">
{heading}
{overview}
    <div class="benchmark-controls">
    <div class="compare-specs">
{board_mode}
      <fieldset id="compare-model" class="compare-choice compare-axis">
        <legend>生成模式</legend>
        <div>
          <label><input type="radio" name="model" value="0" checked>{standard}</label>
          <label><input type="radio" name="model" value="2">{flash}</label>
          <label><input type="radio" name="model" value="4">{sample}</label>
        </div>
      </fieldset>
      <fieldset class="compare-choice compare-resolution">
        <legend>分辨率</legend>
        <div>{resolution_options}</div>
      </fieldset>
    </div>
{board_note}
    <div class="compare-toolbar">
{rank_toolbar}
      <details id="compare-options" class="compare-options">
        <summary aria-controls="compare-filter-panel"><span class="compare-filter-mark" aria-hidden="true"></span>{'调整条件' if workspace else '筛选'}<span id="compare-filter-scope"></span></summary>
        <div id="compare-filter-panel" class="filter-popover" role="region" aria-labelledby="compare-filter-title">
          <header class="filter-popover-heading">
            <h2 id="compare-filter-title">{'调整对比条件' if workspace else '筛选会员档位'}</h2>
            <button type="button" class="filter-popover-close" aria-label="关闭筛选"></button>
          </header>
          <div class="filter-tabs" role="tablist" aria-label="筛选条件">{filter_tabs}</div>
          <div class="compare-option-fields">
            <div id="filter-period" role="tabpanel" aria-labelledby="tab-period">{period_options}</div>
            <div id="filter-amount" role="tabpanel" aria-labelledby="tab-amount" hidden>
{mode_fields}
      <div id="compare-target-panel" class="compare-amount">
        <label class="compare-field" for="compare-target"><span class="filter-caption">每月生成条数</span>
          <span class="compare-input-unit">
            <input id="compare-target" type="number" inputmode="numeric" min="1" max="10000" step="1" value="30" aria-describedby="compare-amount-error" required>
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
            <input id="compare-budget" type="number" inputmode="decimal" min="1" max="1000000" step="0.01" value="1000" aria-describedby="compare-amount-error" required disabled>
            <span aria-hidden="true">元</span>
          </span>
        </label>
        <div class="compare-presets" aria-label="常用周期预算">
          <button type="button" data-budget="300" aria-pressed="false">¥300</button>
          <button type="button" data-budget="1000" aria-pressed="true">¥1,000</button>
          <button type="button" data-budget="3000" aria-pressed="false">¥3,000</button>
        </div>
      </div>
            <p id="compare-amount-error" class="compare-amount-error" hidden></p>
            </div>
{platform_fields}
          </div>
          <div class="filter-popover-footer">
              <small>更改条件后自动重算。</small>
              <button id="compare-reset" type="button" aria-label="重置所有榜单条件">重置条件</button>
          </div>
        </div>
      </details>
{sort_menu}
    </div>
    </div>
{summary}
  </form>
"""
    rank = f"""
  <section id="compare-results" class="compare-results" aria-labelledby="compare-results-title">
    <header class="compare-table-head">
      <h2 id="compare-results-title" class="compare-sr-only">会员档位</h2>
      <span class="compare-table-count"><b>{len(platforms)}</b> 家平台 · <b>{len(plans)}</b> 档方案</span>
      <p id="compare-order" class="compare-order"></p>
      <button id="compare-all" type="button" aria-expanded="false" aria-controls="compare-grid" hidden>查看全部档位</button>
    </header>
    <figure id="compare-bar-figure" class="compare-bar-figure" hidden>
      <figcaption id="compare-bar-label"></figcaption>
      <div class="compare-bars-scroll" role="region" aria-label="档位柱形图，窄屏可横向滚动" tabindex="0"><div id="compare-bars" class="compare-bars"></div></div>
      <p id="compare-bar-feedback" class="chart-feedback">指向或聚焦柱条查看档位数据。点选可跳到榜单中的对应档位。</p>
    </figure>
    <div id="compare-grid">
      <table aria-label="符合规格的会员方案">
        <thead><tr>
          <th scope="col"><span class="compare-identity-head"><span>排名</span><span>平台与档位</span></span></th>
          <th scope="col"><button type="button" data-sort="pay" aria-label="按首期实付排序">首期实付</button></th>
          <th scope="col"><button type="button" data-sort="capacity" aria-label="按月产能排序">月产能</button></th>
          <th scope="col"><button type="button" data-sort="unit" aria-label="按每条成本排序"><span class="compare-unit-label">每条成本</span><span class="compare-unit-short" aria-hidden="true">单价</span></button></th>
          <th scope="col" class="compare-pick-column">对比</th>
        </tr></thead>
        <tbody id="compare-rows"></tbody>
      </table>
    </div>
{picked}
    <p id="compare-coverage" class="compare-coverage"></p>
    <p id="compare-calc-note" class="compare-calc-note"></p>
{record_links}
    <noscript><p>启用 JavaScript 可以实时计算。<a href="cycles.html#allperiod">查看固定规格的完整对比表</a></p></noscript>
  </section>
  <section id="compare-frontier" class="compare-frontier" aria-labelledby="compare-frontier-title" hidden>
    <header class="compare-result-head">
      <h2 id="compare-frontier-title">价格与产能分析</h2>
      <fieldset class="compare-choice compare-frontier-mode">
        <legend>横轴</legend>
        <div>
          <label><input type="radio" name="frontier-metric" value="spend" checked><span>首期实付</span></label>
          <label><input type="radio" name="frontier-metric" value="unit"><span>用满单条成本</span></label>
        </div>
      </fieldset>
    </header>
    <p id="compare-frontier-note"></p>
    <div id="compare-chart-platforms" class="compare-chart-platforms" role="group" aria-label="图上平台"></div>
    <div class="compare-frontier-layout">
      <figure class="compare-frontier-chart">
        <figcaption>月产能（条）</figcaption>
        <div id="compare-frontier-y" class="compare-frontier-y" aria-hidden="true"></div>
        <div id="compare-frontier-plot" class="compare-frontier-plot" role="group" aria-label="可点击的会员档位散点"></div>
        <div id="compare-frontier-x" class="compare-frontier-x" aria-hidden="true"></div>
        <div id="compare-frontier-axis" class="compare-frontier-axis"></div>
      </figure>
      <p class="compare-frontier-key" aria-label="图例"><span>同等支出或单价下的最高月产能</span><span>当前档位中位数</span></p>
      <p id="compare-frontier-feedback" class="chart-feedback">指向或聚焦散点预览数据。点选可固定档位明细。</p>
    </div>
    <div id="compare-point-detail" class="compare-point-detail" aria-live="polite" hidden></div>
    <details class="compare-frontier-data">
      <summary id="compare-frontier-count">图中档位</summary>
      <div id="compare-frontier-list" class="compare-frontier-list" aria-label="图中档位"></div>
    </details>
  </section>
"""
    selection = f"""
  <div id="workspace-shortcuts" class="workspace-shortcuts" role="group" aria-label="快速对比"></div>
  <div class="workspace-layout">
    <section id="workspace-picker" class="workspace-picker" aria-labelledby="workspace-picker-title">
      <header class="workspace-picker-heading">
        <div>
          <h2 id="workspace-picker-title">选择会员档位</h2>
          <p id="workspace-picker-scope"></p>
        </div>
        <label class="compare-search workspace-search">
          <input id="workspace-search" type="search" aria-label="搜索平台、档位或积分" placeholder="搜索平台、档位或积分" autocomplete="off">
        </label>
      </header>
      <p id="workspace-picker-error" class="workspace-picker-error" role="status" hidden></p>
      <div id="workspace-platforms" class="workspace-platforms" role="group" aria-label="按平台筛选"></div>
      <div class="workspace-list-head">
        <p id="workspace-plan-status" class="workspace-plan-status" role="status"></p>
        <button type="button" id="workspace-plan-more" class="workspace-plan-more" aria-controls="workspace-plan-grid" aria-expanded="false" hidden>显示全部档位</button>
        <button type="button" id="workspace-search-clear" class="workspace-plan-more" hidden>清除搜索</button>
      </div>
      <div id="workspace-columns" class="workspace-columns" aria-hidden="true" hidden>
        <span>平台与档位</span><span>月产能</span><span>首期实付</span>
      </div>
      <div id="workspace-plan-grid" class="workspace-plan-grid" aria-label="可选档位"></div>
      <noscript><p>启用 JavaScript 后可选择档位。<a href="cycles.html#allperiod">查看会员档位表</a></p></noscript>
    </section>
{picked}
  </div>
  <section id="compare-selection" class="compare-selection" aria-labelledby="compare-selection-title" hidden>
    <header>
      <div>
        <h2 id="compare-selection-title" tabindex="-1">对比结果</h2>
        <p id="compare-selection-scope"></p>
      </div>
      <div class="workspace-result-actions">
        <a class="workspace-edit" href="#workspace-picker">调整所选档位</a>
        <button type="button" data-share="selected" hidden>复制对比链接</button>
      </div>
    </header>
    <p id="compare-selection-swipe" class="compare-selection-swipe" hidden>横向滑动查看其余档位。</p>
    <div id="compare-selection-table" class="compare-selection-scroll" role="region" aria-label="所选档位的费用与积分" tabindex="0"></div>
    <p id="compare-calc-note" class="compare-calc-note"></p>
{record_links}
  </section>
"""
    html = f"""
<main id="compare-tool" class="compare-page{' compare-workspace' if workspace else ' benchmark-page'}" data-skip-intro>
{tools}
{selection if workspace else rank}
  <div id="compare-share-status" class="compare-sr-only" role="status"></div>
</main>
"""
    js = (COMPARE_JS.replace("__COMPARE_CHARTS__", COMPARE_CHARTS)
          .replace("__COMPARE_OVERVIEW__", COMPARE_OVERVIEW)
          .replace("__COMPARE_PICKER__", COMPARE_PICKER)
          .replace("__COMPARE_OFFER__", COMPARE_OFFER)
          .replace("__COMPARE_DATA__", data))
    return html, js


def membership_budget_view(rows, readings, periods, colors, logos):
    dataset = compare_dataset(rows, readings, periods, colors, logos, "cost.html")
    data = json.dumps(dataset, ensure_ascii=False).replace("<", "\\u003c")

    def choices(name, caption, options, selected):
        radios = "".join(
            f'<label><input type="radio" name="{name}" value="{escape(value)}"'
            f'{" checked" if value == selected else ""}><span>{escape(label)}</span></label>'
            for value, label in options
        )
        return (f'<fieldset class="compare-choice member-{name}-control">'
                f'<legend>{caption}</legend><div>{radios}</div></fieldset>')

    model_choice = choices("model", "生成模式", [("0", "标准版"), ("2", "Flash"), ("4", "样片模式")], "0")
    resolution_choice = choices("res", "分辨率", [(str(i), label) for i, label in enumerate(RESOLUTIONS)],
                                str(RESOLUTIONS.index(DEFAULT_RESOLUTION)))
    period_choice = choices("period", "会员周期", [(key, label) for key, label, _, _ in periods], "m")
    metric_choice = choices("metric", "比较指标", [("capacity", "月产能"), ("unit", "单条均价")], "capacity")
    html = f"""
  <div class="membership-dashboard" id="member-budgets">
    <section class="membership-figure" aria-labelledby="member-chart-title">
      <header><h2 id="member-chart-title">三种预算下能做多少条</h2>
        <p id="member-figure-note"></p>
      </header>
      <form class="member-controls" id="member-controls">
        {model_choice}
        {resolution_choice}
        {period_choice}
        {metric_choice}
      </form>
      <figure class="member-bars" id="member-bars" aria-label="按预算分组的会员比较"></figure>
      <p id="member-chart-hint" class="member-chart-hint">指向或聚焦柱条查看档位数据。点选可按预算和平台筛选套餐。</p>
      <p class="member-chart-method">每条视频按 30 秒、16:9、全能参考计算。</p>
    </section>
    <section id="member-picker" class="member-picker" aria-labelledby="member-picker-title">
      <header><h2 id="member-picker-title">按预算选会员</h2>
        <p>预算按首期实付总额计算。选平台可以查看它的每个预算内档位。</p>
      </header>
      <div class="member-picker-layout">
        <aside class="member-rail" aria-label="套餐筛选">
          <label class="member-custom">预算上限（元）<input id="member-amount" type="number" inputmode="decimal"
            value="1000" min="1" max="1000000" step="0.01" required></label>
          <div id="member-bands" class="member-filter-items" role="group" aria-label="常用预算"></div>
          <h3>平台</h3>
          <div id="member-providers" class="member-filter-items" role="group" aria-label="预算内的平台"></div>
        </aside>
        <div class="member-results">
          <p id="member-status" class="member-status" role="status"></p>
          <div id="member-plans" class="member-plans"></div>
          <div id="member-picks" class="member-picks" hidden>
            <span id="member-pick-count" role="status"></span><button id="member-clear" type="button">清空</button>
            <a id="member-compare" hidden>查看对比</a>
          </div>
        </div>
      </div>
    </section>
  </div>
"""
    js = COMPARE_BUDGET.replace("__COMPARE_OFFER__", COMPARE_OFFER).replace("__COMPARE_DATA__", data)
    return html, js


COMPARE_CSS = Path(__file__).with_name("compare_style.css").read_text(encoding="utf-8")
COMPARE_CHARTS = Path(__file__).with_name("compare_charts.js").read_text(encoding="utf-8")
COMPARE_OVERVIEW = Path(__file__).with_name("compare_overview.js").read_text(encoding="utf-8")
COMPARE_PICKER = Path(__file__).with_name("compare_picker.js").read_text(encoding="utf-8")
COMPARE_BUDGET = Path(__file__).with_name("compare_budget.js").read_text(encoding="utf-8")
COMPARE_OFFER = r"""
  function readingFor(plan, spec, periodKey) {
    const reading = data.readings[plan.platform][spec];
    if ((reading.tier && reading.tier !== plan.tier) || (reading.period && reading.period !== periodKey)) {
      return '该档位及周期的扣分待核实';
    }
    return reading;
  }

  function offerAt(plan, spec, periodKey) {
    const reading = readingFor(plan, spec, periodKey);
    const pricing = plan.periods[periodKey];
    if (!pricing || typeof reading === 'string') return null;
    const [pay, monthlyCredits] = pricing;
    const credits = typeof reading === 'number' ? reading : reading.credits;
    return {plan, pay, capacity:Math.floor(monthlyCredits / credits), monthlyCredits,
      creditsPerClip:credits, sourceDate:reading.date || reading.sourceDate,
      sourceLabel:reading.label || (reading.sourceDate ? '留档' : ''), sourceDetail:reading.detail || ''};
  }
""".strip("\n")


COMPARE_JS = r"""
(function(){
  const root = document.getElementById('compare-tool');
  const form = document.getElementById('compare-form');
  const result = document.getElementById('compare-status');
  const answerLink = document.getElementById('compare-answer-link');
  const filterScope = document.getElementById('compare-filter-scope');
  const table = document.getElementById('compare-grid');
  const rows = document.getElementById('compare-rows');
  const coverage = document.getElementById('compare-coverage');
  const order = document.getElementById('compare-order');
  const title = document.getElementById('compare-results-title');
  const calcNote = document.getElementById('compare-calc-note');
  const sortButtons = table?.querySelectorAll('[data-sort]') || [];
  const model = form.elements.namedItem('model');
  const resolution = form.elements.namedItem('resolution');
  const period = form.elements.namedItem('period');
  const mode = form.elements.namedItem('mode');
  const target = document.getElementById('compare-target');
  const budget = document.getElementById('compare-budget');
  const targetPanel = document.getElementById('compare-target-panel');
  const budgetPanel = document.getElementById('compare-budget-panel');
  const amountError = document.getElementById('compare-amount-error');
  const platform = form.elements.namedItem('provider');
  const search = document.getElementById('compare-search');
  const showAll = document.getElementById('compare-all');
  const rankView = document.getElementById('compare-rank-view');
  const chartView = rankView?.querySelector('[value=chart]');
  const selection = document.getElementById('compare-selection');
  const workspace = Boolean(selection);
  const selectionTitle = document.getElementById('compare-selection-title');
  const selectionScope = document.getElementById('compare-selection-scope');
  const selectionTable = document.getElementById('compare-selection-table');
  const selectionSwipe = document.getElementById('compare-selection-swipe');
  const selectionBack = document.getElementById('compare-selection-back');
  const shareSelection = root.querySelector('[data-share=selected]');
  const shareStatus = document.getElementById('compare-share-status');
  const pickedBar = document.getElementById('compare-picked');
  const pickedPlans = document.getElementById('compare-picked-plans');
  const pickedCount = document.getElementById('compare-picked-count');
  const pickedOpen = document.getElementById('compare-picked-open');
  const pickedClear = document.getElementById('compare-picked-clear');
  const picked = new Set();
  const rowPlans = new Map();
  const pickLimit = 4;
  const presets = form.querySelectorAll('[data-target], [data-budget]');
  const data = __COMPARE_DATA__;
  const money = new Intl.NumberFormat('zh-CN', {style:'currency', currency:'CNY', trailingZeroDisplay:'stripIfInteger'});
  const perClip = new Intl.NumberFormat('zh-CN', {style:'currency', currency:'CNY'});
  const query = new URLSearchParams(location.search);
  const defaultMode = query.get('mode') === 'budget' ? 'budget' : 'target';
  const nameOf = platformName => data.names[platformName] || platformName;
  const matchesPlatform = name => (!platform.value || platform.value === name)
    && nameOf(name).toLowerCase().includes(search.value.trim().toLowerCase());
  const sortMenu = document.getElementById('board-sort');
  const sortLabel = document.getElementById('board-sort-label');
  const orderChoices = sortMenu?.querySelectorAll('[data-order]');
  const sortLabels = {pay:'实付', capacity:'产能', unit:'每条成本'};
  let includeAll = false;
  let sort = null;
  let expandedTierPlatform = '';
  __COMPARE_CHARTS__
  __COMPARE_OVERVIEW__
  __COMPARE_OFFER__
  __COMPARE_PICKER__
  mode.value = defaultMode;
  for (const [key, group] of [['model', model], ['res', resolution], ['period', period]]) {
    const value = query.get(key);
    if ([...group].some(input => input.value === value)) group.value = value;
  }
  const initialAmount = defaultMode === 'budget' ? budget : target;
  initialAmount.disabled = false;
  if (query.has('amount')) {
    const value = initialAmount.value;
    initialAmount.value = query.get('amount');
    if (!initialAmount.validity.valid) initialAmount.value = value;
  }
  if (platform && [...platform].some(option => option.value === query.get('platform'))) platform.value = query.get('platform');
  if (search) search.value = query.get('q') || '';
  if (chartView && query.get('view') === 'chart') chartView.checked = true;
  includeAll = query.get('all') === '1';
  for (const key of query.getAll('tier').slice(0, Object.keys(data.readings).length)) {
    const plan = data.plans.find(item => item.key === key);
    if (plan) rowPlans.set(plan.platform, plan.id);
  }
  for (const key of query.getAll('plan').slice(0, pickLimit)) {
    const plan = data.plans.find(item => item.key === key);
    if (plan) picked.add(plan.id);
  }
  if (table) table.dataset.mode = mode.value;
  const [sortFromLink, sortDirection] = (query.get('sort') || '').split('-');
  if (Object.hasOwn(sortLabels, sortFromLink) && ['asc', 'desc'].includes(sortDirection)) {
    sort = {key:sortFromLink, descending:sortDirection === 'desc'};
  }

  const returningToBudget = workspace && query.get('from') === 'member';

  function stateLink(toWorkspace, keepPicks) {
    const input = mode.value === 'budget' ? budget : target;
    const path = toWorkspace && !workspace ? 'compare.html'
      : (!toWorkspace && workspace ? (returningToBudget ? 'cost.html' : 'index.html') : location.pathname);
    const link = new URL(path, location.href);
    link.search = new URLSearchParams({model:model.value, res:resolution.value,
      period:period.value, mode:mode.value, amount:input.validity.valid ? input.value : input.defaultValue});
    const provider = platform?.value ?? query.get('platform');
    const keyword = search?.value.trim() ?? query.get('q');
    if (provider) link.searchParams.set('platform', provider);
    if (keyword) link.searchParams.set('q', keyword);
    if (sort) link.searchParams.set('sort', sort.key + (sort.descending ? '-desc' : '-asc'));
    const chart = chartView ? chartView.checked : query.get('view') === 'chart';
    if (chart) link.searchParams.set('view', 'chart');
    if (!toWorkspace && !returningToBudget) {
      if (!chart) link.searchParams.set('view', 'table');
      link.hash = 'benchmark-board';
    }
    if (includeAll) link.searchParams.set('all', '1');
    for (const id of rowPlans.values()) link.searchParams.append('tier', data.plans[id].key);
    if (keepPicks) {
      for (const id of picked) link.searchParams.append('plan', data.plans[id].key);
    }
    if (returningToBudget) {
      if (toWorkspace) link.searchParams.set('from', 'member');
      else {
        link.hash = 'member-picker';
        link.searchParams.set('mode', 'budget');
        link.searchParams.set('amount', budget.valueAsNumber >= 1 && budget.valueAsNumber <= 1000000
          ? budget.value : budget.defaultValue);
      }
    }
    if (workspace && toWorkspace) link.hash = location.hash;
    return link;
  }

  // 已分享的旧版榜单链接也进入新的对比页。
  if (!workspace && picked.size >= 2 && !['table', 'chart'].includes(query.get('view'))) {
    location.replace(stateLink(true, true));
    return;
  }

  async function copyLink(button) {
    const link = stateLink(workspace, workspace);
    if (workspace) link.hash = 'compare-selection';
    try {
      await navigator.clipboard.writeText(link.href);
      shareStatus.textContent = button.textContent = '链接已复制';
    } catch {
      history.replaceState(null, '', link);
      shareStatus.textContent = button.textContent = '链接已放在地址栏';
    }
    setTimeout(() => { button.textContent = button.dataset.share === 'selected' ? '复制对比链接' : '复制榜单链接'; }, 2800);
  }

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

  function addMetric(row, key, label, value, max, primary) {
    const cell = row.insertCell();
    const metric = document.createElement('span');
    metric.className = 'compare-metric';
    metric.dataset.barMetric = key;
    const number = document.createElement('span');
    number.textContent = label;
    metric.append(number);
    if (value !== null) {
      const track = document.createElement('span');
      track.className = 'compare-meter';
      track.setAttribute('aria-hidden', 'true');
      const bar = document.createElement('i');
      bar.style.width = (value / max * 100) + '%';
      metric.classList.toggle('compare-metric-primary', primary);
      track.append(bar);
      metric.append(track);
    }
    cell.append(metric);
  }

  function planPick(offer) {
    const pick = document.createElement('button');
    pick.type = 'button';
    pick.className = 'compare-pick';
    pick.dataset.pickPlan = offer.plan.id;
    pick.setAttribute('aria-label', '对比 ' + planName(offer) + '，' + offer.monthlyCredits.toLocaleString('zh-CN') + ' 分/月');
    return pick;
  }

  function appendTierPanel(current, alternatives, panelId, displayUnit) {
    const detailRow = rows.insertRow();
    detailRow.id = panelId;
    detailRow.className = 'compare-tier-expansion';
    detailRow.hidden = expandedTierPlatform !== current.plan.platform;
    const cell = detailRow.insertCell();
    cell.colSpan = 5;
    const panel = document.createElement('section');
    panel.className = 'compare-tier-panel';
    const header = document.createElement('header');
    const heading = document.createElement('h3');
    heading.id = panelId + '-title';
    heading.textContent = nameOf(current.plan.platform) + ' · 会员档位';
    const review = document.createElement('button');
    review.type = 'button';
    review.className = 'compare-tier-review';
    review.dataset.tierReview = '';
    header.append(heading, review);
    const list = document.createElement('div');
    list.className = 'compare-tier-options';
    list.setAttribute('role', 'table');
    list.setAttribute('aria-labelledby', heading.id);
    const columns = ['会员档位', '首期实付', '月产能', '每条成本', '对比'];
    const labels = document.createElement('div');
    labels.className = 'compare-tier-line compare-tier-labels';
    labels.setAttribute('role', 'row');
    for (const label of columns) {
      const title = document.createElement('span');
      title.setAttribute('role', 'columnheader');
      title.textContent = label;
      labels.append(title);
    }
    list.append(labels);
    for (const offer of alternatives) {
      const active = current.plan.id === offer.plan.id;
      const credits = offer.monthlyCredits.toLocaleString('zh-CN') + ' 分/月';
      const line = document.createElement('div');
      line.className = 'compare-tier-line';
      line.classList.toggle('is-current', active);
      line.setAttribute('role', 'row');
      const identity = document.createElement('div');
      identity.className = 'compare-tier-identity';
      identity.setAttribute('role', 'rowheader');
      const show = document.createElement('button');
      show.type = 'button';
      show.className = 'compare-tier-name';
      show.dataset.tierPlan = offer.plan.id;
      show.textContent = offer.plan.tier;
      show.setAttribute('aria-label', '在榜单显示 ' + planName(offer) + '，' + credits);
      show.setAttribute('aria-current', String(active));
      const points = document.createElement('span');
      points.className = 'compare-tier-points';
      points.textContent = credits;
      identity.append(show);
      if (active) {
        const badge = document.createElement('span');
        badge.className = 'compare-tier-current';
        badge.textContent = '当前展示';
        identity.append(badge);
      }
      identity.append(points);
      line.append(identity);
      const values = [money.format(offer.pay), offer.capacity + ' 条', displayUnit(offer)];
      values.forEach((value, index) => {
        const metric = document.createElement('span');
        metric.className = 'compare-tier-metric';
        metric.setAttribute('role', 'cell');
        metric.dataset.label = columns[index + 1];
        metric.textContent = value;
        line.append(metric);
      });
      const actions = document.createElement('div');
      actions.className = 'compare-tier-pick';
      actions.setAttribute('role', 'cell');
      actions.append(planPick(offer));
      line.append(actions);
      list.append(line);
    }
    panel.append(header, list);
    cell.append(panel);
  }

  function setTierPanel(platformName) {
    expandedTierPlatform = platformName;
    for (const toggle of rows.querySelectorAll('[data-tier-toggle]')) {
      const expanded = toggle.dataset.tierToggle === platformName;
      toggle.setAttribute('aria-expanded', String(expanded));
      toggle.closest('tr').classList.toggle('compare-tier-open', expanded);
      document.getElementById(toggle.getAttribute('aria-controls')).hidden = !expanded;
    }
  }

  function syncPicks(){
    pickedBar.hidden = picked.size === 0;
    pickedCount.textContent = '已选 ' + picked.size + ' / ' + pickLimit + ' 个档位';
    pickedOpen.disabled = picked.size < 2;
    pickedPlans.replaceChildren();
    for (const id of picked) {
      const plan = data.plans[id];
      const label = nameOf(plan.platform) + ' ' + plan.tier;
      const remove = document.createElement('button');
      remove.type = 'button';
      remove.dataset.removePlan = id;
      remove.textContent = label + ' ×';
      const credits = plan.periods[period.value]?.[1] ?? Object.values(plan.periods)[0][1];
      remove.setAttribute('aria-label', '移除 ' + label + '，' + credits.toLocaleString('zh-CN') + ' 分档');
      pickedPlans.append(remove);
    }
    for (const button of rows?.querySelectorAll('[data-pick-plan]') || []) {
      const active = picked.has(Number(button.dataset.pickPlan));
      button.setAttribute('aria-pressed', String(active));
      button.disabled = !active && picked.size >= pickLimit;
    }
    for (const review of rows?.querySelectorAll('[data-tier-review]') || []) {
      review.disabled = picked.size < 2;
      review.textContent = review.disabled ? '选两档后对比' : '对比所选档位';
    }
  }

  function syncSelectionScroll() {
    selectionSwipe.hidden = selectionTable.scrollWidth <= selectionTable.clientWidth + 1;
  }

  function renderSelection(spec, scope, fits, unitCost, reasonFor, issue){
    selectionScope.textContent = scope;
    const ready = picked.size >= 2 && !issue;
    selection.hidden = !ready;
    shareSelection.hidden = !ready;
    selectionTable.replaceChildren();
    if (!ready) return;

    const choices = [...picked].map(id => workspacePlan(data.plans[id], spec));
    const grid = document.createElement('table');
    grid.setAttribute('aria-label', '档位并排对比');
    grid.dataset.choices = choices.length;
    grid.style.setProperty('--comparison-width', (78 + choices.length * 121) + 'px');
    const header = grid.createTHead().insertRow();
    const metricHead = document.createElement('th');
    metricHead.scope = 'col';
    metricHead.textContent = '指标';
    header.append(metricHead);
    for (const {plan, quote, reading, offer} of choices) {
      const cell = document.createElement('th');
      cell.scope = 'col';
      const identity = document.createElement('div');
      identity.className = 'compare-selection-provider';
      const name = document.createElement('a');
      name.href = data.recordsPage + '#' + plan.anchor;
      name.textContent = nameOf(plan.platform);
      const tier = document.createElement('small');
      tier.textContent = plan.tier + (offer?.sourceLabel ? ' · ' + offer.sourceLabel : '');
      const status = document.createElement('small');
      if (!quote) status.textContent = '无' + data.periods[period.value][0];
      else if (offer && !fits(offer)) status.textContent = reasonFor(offer);
      identity.append(platformLogo({plan}), name);
      cell.append(identity, tier);
      if (quote) {
        const credits = document.createElement('small');
        credits.textContent = quote[1].toLocaleString('zh-CN') + ' 分/月';
        cell.append(credits);
      }
      if (status.textContent) cell.append(status);
      header.append(cell);
    }
    const metrics = [
      ['pay', '首期实付', ({quote}) => quote ? money.format(quote[0]) : '—', ({quote}) => quote?.[0]],
      ['capacity', '月产能', ({offer}) => offer ? offer.capacity + ' 条' : '—', ({offer}) => offer?.capacity],
      ['unit', '每条成本', ({offer}) => offer ? (fits(offer) ? perClip.format(unitCost(offer)) : reasonFor(offer)) : '—'],
      ['credits', '每月积分', ({quote}) => quote ? quote[1].toLocaleString('zh-CN') : '—'],
      ['reading', '每条积分', ({reading}) => typeof reading === 'string' ? reading
        : (reading.credits ?? reading).toLocaleString('zh-CN') + ' 分/条'],
    ];
    const body = grid.createTBody();
    for (const [metric, label, format, valueOf] of metrics) {
      const row = body.insertRow();
      row.dataset.metric = metric;
      const heading = document.createElement('th');
      heading.scope = 'row';
      heading.textContent = label;
      row.append(heading);
      const values = valueOf ? choices.map(valueOf).filter(Number.isFinite) : [];
      const min = Math.min(...values);
      const max = Math.max(...values);
      const best = metric === 'pay' ? min : max;
      for (const choice of choices) {
        const cell = row.insertCell();
        cell.append(pickerNode('span', 'workspace-result-value', format(choice)));
        if (values.length > 1 && min !== max && valueOf(choice) === best) {
          cell.append(pickerNode('small', 'workspace-result-best', metric === 'pay' ? '最低' : '最高'));
        }
      }
    }
    selectionTable.append(grid);
    syncSelectionScroll();
  }

  const filterTabs = [...form.querySelectorAll('.filter-tabs [role=tab]')];
  const amountTab = document.getElementById('tab-amount');
  function selectFilterTab(selected) {
    for (const tab of filterTabs) {
      const active = tab === selected;
      tab.tabIndex = active ? 0 : -1;
      tab.setAttribute('aria-selected', String(active));
      document.getElementById(tab.getAttribute('aria-controls')).hidden = !active;
    }
  }
  filterTabs.forEach((tab, index) => {
    tab.addEventListener('click', () => selectFilterTab(tab));
    tab.addEventListener('keydown', event => {
      const next = {Home:0, End:filterTabs.length - 1, ArrowLeft:index - 1, ArrowRight:index + 1}[event.key];
      if (next === undefined) return;
      event.preventDefault();
      const selected = filterTabs[(next + filterTabs.length) % filterTabs.length];
      selectFilterTab(selected);
      selected.focus();
    });
  });
  function render(){
    const byBudget = mode.value === 'budget';
    const byChart = Boolean(chartView?.checked);
    const input = byBudget ? budget : target;
    const amount = input.valueAsNumber;
    const cycle = data.periods[period.value];
    const spec = Number(model.value) + Number(resolution.value);
    const specName = form.querySelector('[name=model]:checked + span').textContent
      + (resolution.value === '0' ? ' · 480p' : ' · 720p');
    const scenario = (byBudget ? money.format(amount) + ' 预算' : amount.toLocaleString('zh-CN') + ' 条/月');
    const available = new Set();
    const excluded = [];
    const offers = [];
    target.disabled = targetPanel.hidden = byBudget;
    budget.disabled = budgetPanel.hidden = !byBudget;
    amountTab.textContent = byBudget ? '预算条件' : '用量条件';
    const issue = input.validity.valid ? '' : (byBudget ? '请输入 ¥1 至 ¥1,000,000 的预算，最多保留两位小数。'
      : '请输入 1 到 10,000 之间的整数条数。');
    input.setAttribute('aria-invalid', String(Boolean(issue)));
    amountError.hidden = !issue;
    amountError.textContent = issue;
    filterScope.textContent = cycle[0] + (issue ? '' : ' · ' + scenario);
    for (const preset of presets) {
      const activeValue = preset.dataset.budget ? budget.valueAsNumber : target.valueAsNumber;
      preset.setAttribute('aria-pressed', String(Number(preset.dataset.budget || preset.dataset.target) === activeValue));
    }
    calcNote.textContent = (byBudget ? '每条成本按用完可生成额度计算。' : '每条成本按你填写的用量计算。')
      + '结果基于单账号、首期价格和基础积分。首购资格以结算页为准。';
    const fits = byBudget ? offer => offer.capacity > 0 && offer.pay <= amount
      : offer => offer.capacity >= amount;
    const unitCost = offer => offer.pay / ((byBudget ? offer.capacity : amount) * cycle[1]);
    const reasonFor = offer => byBudget ? (offer.pay > amount ? '超预算' : '额度不足') : '未达用量';
    if (workspace) {
      selectionBack.href = stateLink(false, true);
      if (returningToBudget) selectionBack.textContent = '返回按预算选会员';
      const scope = specName + ' · ' + cycle[0] + (issue ? '' : ' · ' + scenario);
      renderSelection(spec, scope, fits, unitCost, reasonFor, issue);
      renderWorkspacePicker(spec, scope, byBudget, fits, issue);
      syncWorkspaceTray(spec);
      if (!issue) {
        const link = stateLink(true, true);
        if (link.href !== location.href) history.replaceState(null, '', link);
      }
      return;
    }
    const pageTitle = byBudget ? '预算产能榜' : '视频生成成本榜';
    title.textContent = pageTitle;
    if (table.dataset.mode !== mode.value) sort = null;
    table.dataset.mode = mode.value;
    const sortKey = sort?.key ?? (byBudget ? 'capacity' : 'pay');
    const descending = sort?.descending ?? byBudget;
    sortLabel.textContent = '按' + sortLabels[sortKey];
    for (const button of orderChoices) {
      button.setAttribute('aria-pressed', String(button.dataset.order === sortKey &&
        (button.dataset.direction === 'desc') === descending));
    }
    for (const button of sortButtons) {
      const th = button.closest('th');
      if (button.dataset.sort === sortKey) th.setAttribute('aria-sort', descending ? 'descending' : 'ascending');
      else th.removeAttribute('aria-sort');
    }
    rows.textContent = '';
    coverage.textContent = '';
    order.textContent = '';
    table.hidden = true;
    showAll.hidden = true;
    answerLink.hidden = true;
    clearCharts();
    for (const [name, cells] of Object.entries(data.readings)) {
      if (!matchesPlatform(name)) continue;
      const reading = cells[spec];
      if (typeof reading === 'string') {
        excluded.push(nameOf(name) + '（' + reading + '）');
        continue;
      }
      available.add(name);
    }
    for (const plan of data.plans) {
      if (!available.has(plan.platform)) continue;
      const offer = offerAt(plan, spec, period.value);
      if (offer) offers.push(offer);
    }
    const providers = new Set(offers.map(offer => offer.plan.platform));
    for (const name of available.keys()) {
      if (!providers.has(name)) {
        const restriction = data.readings[name][spec].period;
        excluded.push(nameOf(name) + (restriction ? '（仅' + data.periods[restriction][0] + '有参考价）' : '（无' + cycle[0] + '）'));
      }
    }
    const rankBy = byBudget ? (a,b) => b.capacity - a.capacity || a.pay - b.pay
      : (a,b) => a.pay - b.pay || b.capacity - a.capacity;
    if (issue) {
      drawOverview(offers, new Map(), rankBy, byBudget, {spec, specName, cycle, amount, issue});
      result.textContent = issue;
      syncPicks();
      return;
    }
    const matched = offers.filter(fits).sort(rankBy);
    const best = matched[0];
    const highestCapacity = Math.max(0, ...offers.map(offer => offer.capacity));
    result.textContent = '';
    if (best) {
      const lead = document.createElement('div');
      lead.className = 'compare-answer';
      const label = document.createElement('span');
      label.textContent = byBudget ? '预算内最多可做' : '达标首期最低';
      const answer = document.createElement('strong');
      answer.textContent = byBudget ? best.capacity + ' 条/月' : money.format(best.pay);
      lead.append(label, answer);
      const context = document.createElement('div');
      context.className = 'compare-answer-context';
      const scope = document.createElement('b');
      scope.className = 'compare-answer-scope';
      scope.textContent = scenario + ' · ' + cycle[0];
      const caption = document.createElement('small');
      caption.textContent = nameOf(best.plan.platform) + ' ' + best.plan.tier
        + (byBudget ? ' · 实付 ' + money.format(best.pay) : '')
        + (best.sourceLabel ? ' · ' + best.sourceLabel : '');
      context.append(scope, caption);
      result.append(lead, context);
      answerLink.href = data.recordsPage + '#' + best.plan.anchor;
      answerLink.hidden = false;
    } else if (search.value.trim() && !available.size && !excluded.length) {
      result.textContent = '没有匹配的平台，请换一个关键词。';
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
    const platformOffers = new Map();
    for (const offer of offers) {
      const alternatives = platformOffers.get(offer.plan.platform) || [];
      alternatives.push(offer);
      platformOffers.set(offer.plan.platform, alternatives);
    }
    const shortList = [...platformLeaders.values()].map(leader =>
      platformOffers.get(leader.plan.platform).find(offer => offer.plan.id === rowPlans.get(leader.plan.platform)) || leader);
    const ranked = includeAll ? matched : shortList.filter(fits).sort(rankBy);
    showAll.hidden = byChart || offers.length === platformLeaders.size;
    showAll.setAttribute('aria-expanded', String(includeAll));
    showAll.textContent = includeAll ? '收起完整档位' : '查看全部 ' + offers.length + ' 个档位';
    if (sort) {
      const valueOf = sortKey === 'unit' ? unitCost : offer => offer[sortKey];
      const direction = descending ? -1 : 1;
      ranked.sort((a, b) => (valueOf(a) - valueOf(b)) * direction || rankBy(a, b));
    }
    const displayed = [...ranked, ...(includeAll ? offers : shortList).filter(offer => !fits(offer)).sort(rankBy)];
    const payMax = Math.max(1, ...displayed.map(offer => offer.pay));
    const volumeMax = Math.max(1, ...displayed.map(offer => offer.capacity));
    const unitMax = Math.max(1, ...ranked.map(unitCost));
    order.textContent = displayed.length ? sortLabels[sortKey] + (descending ? '从高到低' : '从低到高')
      + ' · ' + ranked.length + (includeAll ? ' 档' : ' 家') + (byBudget ? '在预算内' : '达标') : '';
    displayed.forEach((offer, index) => {
      const tr = rows.insertRow();
      tr.dataset.chartPlan = offer.plan.id;
      tr.tabIndex = -1;
      const title = tr.insertCell();
      const identity = document.createElement('div');
      identity.className = 'compare-row-identity';
      const provider = document.createElement('div');
      provider.className = 'compare-provider';
      const rank = document.createElement('span');
      rank.className = 'compare-rank';
      rank.textContent = index < ranked.length ? String(index + 1).padStart(2, '0') : '—';
      const name = document.createElement('a');
      name.className = 'compare-result-name';
      name.href = data.recordsPage + '#' + offer.plan.anchor;
      name.textContent = nameOf(offer.plan.platform);
      name.setAttribute('aria-label', '查看 ' + name.textContent + ' 的会员价格');
      const detail = document.createElement('small');
      const alternatives = platformOffers.get(offer.plan.platform);
      const hasChoices = !includeAll && !byChart && alternatives.length > 1;
      const tier = document.createElement(hasChoices ? 'button' : 'span');
      const panelId = 'compare-tier-' + alternatives[0].plan.id;
      tier.textContent = offer.plan.tier;
      if (hasChoices) {
        const expanded = expandedTierPlatform === offer.plan.platform;
        tier.type = 'button';
        tier.className = 'compare-tier-toggle';
        tier.dataset.tierToggle = offer.plan.platform;
        tier.setAttribute('aria-label', name.textContent + ' ' + offer.plan.tier + '，' + alternatives.length + ' 个档位');
        tier.setAttribute('aria-expanded', String(expanded));
        tier.setAttribute('aria-controls', panelId);
        tr.classList.toggle('compare-tier-open', expanded);
        const count = document.createElement('span');
        count.className = 'compare-tier-count';
        count.textContent = '· ' + alternatives.length + ' 个档位';
        tier.append(count);
      }
      const credits = document.createElement('span');
      credits.className = 'compare-credits-detail';
      credits.textContent = offer.monthlyCredits.toLocaleString('zh-CN') + ' 分/月';
      detail.append(tier, credits);
      provider.append(name);
      if (offer.sourceDate) {
        const archive = document.createElement('span');
        archive.className = 'compare-archive-detail';
        archive.textContent = offer.sourceLabel;
        archive.title = [offer.sourceLabel, offer.sourceDate, offer.sourceDetail].filter(Boolean).join(' · ');
        archive.setAttribute('aria-label', archive.title);
        provider.append(archive);
      }
      provider.append(detail);
      const brand = document.createElement('span');
      brand.className = 'compare-brand-wrap';
      brand.append(platformLogo(offer));
      identity.append(rank, brand, provider);
      title.append(identity);
      const matchedOffer = index < ranked.length;
      addMetric(tr, 'pay', money.format(offer.pay), offer.pay, payMax, matchedOffer && sortKey === 'pay');
      addMetric(tr, 'capacity', offer.capacity + ' 条', offer.capacity, volumeMax, matchedOffer && sortKey === 'capacity');
      const unit = matchedOffer ? unitCost(offer) : null;
      addMetric(tr, 'unit', matchedOffer ? perClip.format(unit) : reasonFor(offer), unit, unitMax, matchedOffer && sortKey === 'unit');
      const pickCell = tr.insertCell();
      pickCell.className = 'compare-pick-column';
      pickCell.append(planPick(offer));
      if (hasChoices) {
        appendTierPanel(offer, alternatives, panelId, option => fits(option) ? perClip.format(unitCost(option)) : reasonFor(option));
      }
    });
    table.hidden = byChart || !displayed.length;
    syncPicks();
    const short = [...providers].filter(name => !matched.some(offer => offer.plan.platform === name));
    const notes = [];
    if (short.length) notes.push(short.map(nameOf).join('、') + (byBudget ? ' 在当前预算内暂无可用档位' : ' 的单账号档位未达用量'));
    if (excluded.length) notes.push('当前未计入：' + excluded.join('、'));
    coverage.textContent = notes.join('。') + (notes.length ? '。' : '');
    drawOverview(offers, platformLeaders, rankBy, byBudget, {spec, specName, cycle, amount});
    renderCharts(offers, ranked, byBudget, cycle[1]);
  }
  form.addEventListener('submit', event => event.preventDefault());
  form.addEventListener('change', render);
  sortMenu?.addEventListener('click', event => {
    const option = event.target.closest('[data-order]');
    if (!option) return;
    sort = {key:option.dataset.order, descending:option.dataset.direction === 'desc'};
    sortMenu.open = false;
    render();
    sortMenu.querySelector('summary').focus({preventScroll:true});
  });
  table?.addEventListener('click', event => {
    const button = event.target.closest('[data-sort]');
    if (!button) return;
    const key = button.dataset.sort;
    const current = button.closest('th').getAttribute('aria-sort');
    sort = {key, descending: current ? current === 'ascending' : key === 'capacity'};
    render();
  });
  root.addEventListener('click', event => {
    const button = event.target.closest('[data-share]');
    if (button) copyLink(button);
  });
  rows?.addEventListener('click', event => {
    const toggle = event.target.closest('[data-tier-toggle]');
    if (toggle) {
      const platformName = toggle.dataset.tierToggle;
      setTierPanel(platformName === expandedTierPlatform ? '' : platformName);
      return;
    }
    const displayTier = event.target.closest('[data-tier-plan]');
    if (displayTier) {
      if (displayTier.getAttribute('aria-current') === 'true') return;
      const plan = data.plans[Number(displayTier.dataset.tierPlan)];
      rowPlans.set(plan.platform, plan.id);
      render();
      const renewed = rows.querySelector('[data-tier-plan="' + plan.id + '"]');
      renewed?.focus();
      return;
    }
    if (event.target.closest('[data-tier-review]')) {
      pickedOpen.click();
      return;
    }
    const button = event.target.closest('[data-pick-plan]');
    if (!button) return;
    const id = Number(button.dataset.pickPlan);
    if (picked.has(id)) picked.delete(id);
    else if (picked.size < pickLimit) picked.add(id);
    syncPicks();
  });
  rows?.addEventListener('keydown', event => {
    if (event.key !== 'Escape') return;
    const toggle = rows.querySelector('[data-tier-toggle][aria-expanded="true"]');
    if (!toggle) return;
    const panel = document.getElementById(toggle.getAttribute('aria-controls'));
    if (!toggle.contains(event.target) && !panel.contains(event.target)) return;
    setTierPanel('');
    toggle.focus({preventScroll:true});
  });
  pickedOpen.addEventListener('click', () => {
    if (picked.size < 2) return;
    if (workspace) {
      selectionTitle.focus({preventScroll:true});
      selection.scrollIntoView();
    } else location.assign(stateLink(true, true));
  });
  pickedClear.addEventListener('click', () => {
    picked.clear();
    render();
    (workspace ? pickerSearch : result).focus();
  });
  pickedPlans.addEventListener('click', event => {
    const button = event.target.closest('[data-remove-plan]');
    if (!button) return;
    picked.delete(Number(button.dataset.removePlan));
    render();
    if (workspace) (pickedPlans.querySelector('button') || pickerSearch).focus();
    else (pickedBar.hidden ? result : pickedClear).focus({preventScroll:true});
  });
  if (workspace) {
    bindWorkspacePicker();
    new ResizeObserver(syncSelectionScroll).observe(selectionTable);
  }
  showAll?.addEventListener('click', () => {
    includeAll = !includeAll;
    expandedTierPlatform = '';
    render();
  });
  [target, budget, search].filter(Boolean).forEach(input => input.addEventListener('input', render));
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
    includeAll = false;
    sort = null;
    rowPlans.clear();
    expandedTierPlatform = '';
    render();
  });
  render();
  if (workspace && !selection.hidden && !location.hash) selection.scrollIntoView({behavior:'instant'});
})();
"""


DISCLOSURE_JS = r"""
(function(){
  const recordPanels = document.getElementById('record-panels');
  const recordLinks = document.querySelectorAll('#record-sections a');
  const sections = recordPanels ? [...recordPanels.children] : [];
  const query = new URLSearchParams(location.search);
  if (recordPanels && (location.hash === '#compare-results'
      || (!location.hash && ['mode', 'amount', 'model', 'plan', 'sort', 'period', 'q', 'platform', 'all', 'tier', 'res'].some(key => query.has(key))))) {
    location.replace('index.html' + location.search + location.hash);
    return;
  }
  function activateRecord(panel){
    if (!panel) return;
    recordPanels.dataset.ready = 'true';
    for (const section of sections) section.hidden = section !== panel;
    panel.open = true;
    for (const link of recordLinks) {
      if (link.hash === '#' + panel.id) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    }
  }
  for (const link of recordLinks) {
    link.addEventListener('click', event => {
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      history.replaceState(null, '', link.hash);
      activateRecord(document.getElementById(link.hash.slice(1)));
    });
  }
  for (const filters of document.querySelectorAll('details.compare-options, details.rank-filters')) {
    const trigger = filters.querySelector('summary');
    const panel = filters.querySelector('.filter-popover');
    const nav = document.querySelector('.nav');
    function alignFilterPanel() {
      if (!filters.open) return;
      const frame = panel.offsetParent;
      if (!frame) return;
      const anchor = trigger.getBoundingClientRect();
      const bounds = frame.getBoundingClientRect();
      const right = anchor.right - bounds.left;
      const width = panel.offsetWidth;
      const left = Math.max(0, Math.min(right - width, frame.clientWidth - width));
      const gap = 8;
      const below = window.innerHeight - anchor.bottom - 2 * gap;
      const above = anchor.top - Math.max(0, nav?.getBoundingClientRect().bottom ?? 0) - 2 * gap;
      const opensAbove = below < Math.min(panel.scrollHeight, 440) && above > below;
      panel.style.left = left + 'px';
      panel.style.top = opensAbove ? 'auto' : (anchor.bottom - bounds.top + gap) + 'px';
      panel.style.bottom = opensAbove ? (bounds.bottom - anchor.top + gap) + 'px' : 'auto';
      panel.style.setProperty('--filter-space', Math.max(160, opensAbove ? above : below) + 'px');
    }
    function closeFilterPanel() {
      filters.open = false;
      trigger.focus({preventScroll: true});
    }
    filters.addEventListener('toggle', alignFilterPanel);
    window.addEventListener('resize', alignFilterPanel);
    window.addEventListener('scroll', alignFilterPanel, {passive: true});
    new ResizeObserver(alignFilterPanel).observe(trigger);
    panel.querySelector('.filter-popover-close').addEventListener('click', closeFilterPanel);
    document.addEventListener('pointerdown', event => {
      if (filters.open && !filters.contains(event.target)) filters.open = false;
    });
    filters.addEventListener('focusout', event => {
      if (filters.open && event.relatedTarget && !filters.contains(event.relatedTarget)) filters.open = false;
    });
    filters.addEventListener('keydown', event => {
      if (event.key === 'Escape' && filters.open) {
        event.preventDefault();
        closeFilterPanel();
      }
    });
  }
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
    activateRecord(sections.find(section => section.contains(target)));
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
    if (event.defaultPrevented) return;
    const link = event.target.closest('a[href^="#"]');
    if (link && link.hash.length > 1 && link.hash === location.hash) {
      event.preventDefault();
      openHash();
    }
  });
  window.addEventListener('hashchange', openHash);
  activateRecord(sections[0]);
  openHash();
})();
"""

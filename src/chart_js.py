# src/chart_js.py
"""All JavaScript for the SLURM dashboard Plotly charts."""


def _base_js() -> str:
    return """
// ── Constants & State ────────────────────────────────────────────────────────
let DATA;
const PLOTLY_CONFIG = { responsive: true, displayModeBar: false };
const DARK_LAYOUT = {
  paper_bgcolor: '#0d1117',
  plot_bgcolor: '#161b22',
  font: { color: '#e6edf3', family: 'system-ui, sans-serif', size: 12 },
  xaxis: { gridcolor: '#21262d', linecolor: '#30363d', zerolinecolor: '#21262d' },
  yaxis: { gridcolor: '#21262d', linecolor: '#30363d', zerolinecolor: '#21262d' },
  margin: { t: 40, r: 20, b: 60, l: 80 },
  legend: { bgcolor: '#161b22', bordercolor: '#30363d', borderwidth: 1 },
};
const COLORS = [
  '#58a6ff','#3fb950','#f85149','#d29922','#bc8cff',
  '#ff7b72','#79c0ff','#56d364','#ffa657','#e3b341',
  '#f778ba','#7ee787','#a5d6ff','#ffb3b0','#d2a8ff',
];
const STATE_COLORS = {
  FAILED: '#f85149',
  TIMEOUT: '#d29922',
  CANCELLED: '#8b949e',
  OUT_OF_MEMORY: '#bc8cff',
};

let currentRange = '7d';
let selectedUser = null;
let drilldownTab = 'process';
let selectedUsers = new Set();  // empty = all users

function getVisibleUsers() {
  return selectedUsers.size > 0 ? DATA.users.filter(u => selectedUsers.has(u)) : DATA.users;
}

function toggleUser(user) {
  if (selectedUsers.has(user)) {
    selectedUsers.delete(user);
  } else {
    selectedUsers.add(user);
  }
  updateChips();
  // Auto-show drilldown for single user selection
  if (selectedUsers.size === 1) {
    selectedUser = [...selectedUsers][0];
    document.getElementById('drilldown-container').style.display = 'block';
    document.getElementById('drilldown-user-name').textContent = selectedUser;
  } else {
    selectedUser = null;
    document.getElementById('drilldown-container').style.display = 'none';
  }
  renderAllCharts();
  updateKPIs();
}

function clearUserFilter() {
  selectedUsers.clear();
  updateChips();
  selectedUser = null;
  document.getElementById('drilldown-container').style.display = 'none';
  renderAllCharts();
  updateKPIs();
}

function updateChips() {
  document.querySelectorAll('.user-chip[data-user]').forEach(chip => {
    chip.classList.toggle('active', selectedUsers.has(chip.dataset.user));
  });
  const allChip = document.querySelector('.chip-all');
  if (allChip) allChip.classList.toggle('active', selectedUsers.size === 0);
}

function getUserColor(user) {
  const idx = DATA.users.indexOf(user);
  return COLORS[idx % COLORS.length];
}
function hexToRgba(hex, alpha) {
  const r = parseInt(hex.slice(1,3), 16);
  const g = parseInt(hex.slice(3,5), 16);
  const b = parseInt(hex.slice(5,7), 16);
  return 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
}

function getFilteredHours() {
  if (currentRange === '1d') {
    const lastDate = DATA.all_dates[DATA.all_dates.length - 1];
    return DATA.all_hours.filter(h => h.startsWith(lastDate));
  }
  return DATA.all_hours;
}

function formatHourLabel(h) {
  // "2026-03-30T10" → "Mar 30 10:00" (7d) or "10:00" (1d)
  const parts = h.match(/(\\d{4})-(\\d{2})-(\\d{2})T(\\d{2})/);
  if (!parts) return h;
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const mon = months[parseInt(parts[2]) - 1];
  const day = parseInt(parts[3]);
  const hour = parts[4] + ':00';
  return currentRange === '1d' ? hour : mon + ' ' + day + ' ' + hour;
}

function formatHourLabels(hours) {
  return hours.map(formatHourLabel);
}

function formatSeconds(s) {
  s = Math.round(s);
  if (s < 120) return s + 's';
  if (s < 7200) return Math.floor(s / 60) + 'm';
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  return m > 0 ? h + 'h ' + m + 'm' : h + 'h';
}

function secondsTickFormat(values) {
  // Return a tickformat function for Plotly axes showing time durations
  const maxVal = Math.max(...values.filter(v => v != null), 0);
  if (maxVal >= 3600) return { dtick: 3600, tickvals: null, ticktext: null, title: 'Wait (hours)' };
  if (maxVal >= 300) return { dtick: 300, tickvals: null, ticktext: null, title: 'Wait (minutes)' };
  return { dtick: null, tickvals: null, ticktext: null, title: 'Wait (seconds)' };
}

function makeTimeYAxis(values, baseTitle) {
  const maxVal = Math.max(...values.filter(v => v != null && !isNaN(v)), 0);
  if (maxVal >= 3600) {
    // Pick step so we get 5-10 ticks
    let stepH = 1;
    const maxH = maxVal / 3600;
    if (maxH > 48) stepH = 12;
    else if (maxH > 24) stepH = 6;
    else if (maxH > 10) stepH = 2;
    const nTicks = Math.ceil(maxH / stepH) + 1;
    return { title: baseTitle + ' (hours)',
      tickvals: Array.from({length: nTicks}, (_,i) => i * stepH * 3600),
      ticktext: Array.from({length: nTicks}, (_,i) => (i * stepH) + 'h') };
  }
  if (maxVal >= 300) {
    let stepM = 5;
    const maxM = maxVal / 60;
    if (maxM > 30) stepM = 10;
    if (maxM > 60) stepM = 15;
    const nTicks = Math.ceil(maxM / stepM) + 1;
    return { title: baseTitle + ' (minutes)',
      tickvals: Array.from({length: nTicks}, (_,i) => i * stepM * 60),
      ticktext: Array.from({length: nTicks}, (_,i) => (i * stepM) + 'm') };
  }
  return { title: baseTitle + ' (seconds)' };
}

function setRange(range) {
  currentRange = range;
  document.querySelectorAll('.toggle-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.range === range);
  });
  renderAllCharts();
  updateKPIs();
}

function updateKPIs() {
  const kpis = (currentRange === '1d' && DATA.kpis_by_date)
    ? DATA.kpis_by_date[DATA.all_dates[DATA.all_dates.length - 1]] || DATA.kpis
    : DATA.kpis;
  if (!kpis) return;
  const el = id => document.getElementById(id);
  if (el('kpi-total-jobs')) el('kpi-total-jobs').textContent = kpis.total_jobs ?? '—';
  if (el('kpi-active-users')) el('kpi-active-users').textContent = kpis.active_users ?? '—';
  if (el('kpi-median-wait')) el('kpi-median-wait').textContent = formatSeconds(kpis.median_wait ?? 0);
  if (el('kpi-mem-eff')) {
    const v = kpis.median_mem_efficiency ?? 0;
    el('kpi-mem-eff').textContent = (v * 100).toFixed(1) + '%';
    const card = el('kpi-mem-eff').closest('.kpi-card');
    if (card) {
      card.classList.remove('kpi-warn', 'kpi-bad');
      if (v < 0.3) card.classList.add('kpi-bad');
      else if (v < 0.6) card.classList.add('kpi-warn');
    }
  }
  if (el('kpi-failed-jobs')) {
    el('kpi-failed-jobs').textContent = kpis.failed_jobs ?? '—';
    const card = el('kpi-failed-jobs').closest('.kpi-card');
    if (card) {
      card.classList.remove('kpi-warn', 'kpi-bad');
      if ((kpis.failed_jobs ?? 0) > 10) card.classList.add('kpi-bad');
      else if ((kpis.failed_jobs ?? 0) > 0) card.classList.add('kpi-warn');
    }
  }
}
"""


def _chart_jobs_time_js() -> str:
    return """
// ── Chart 2: Total Jobs Over Time (stacked area) ─────────────────────────────
function renderChartJobsTime() {
  const hours = getFilteredHours();
  const labels = formatHourLabels(hours);
  const traces = getVisibleUsers().map(user => {
    const yVals = hours.map(h => (DATA.hourly_by_user[user] || {})[h] || 0);
    const col = getUserColor(user);
    return {
      name: user,
      x: labels,
      y: yVals,
      type: 'scatter',
      mode: 'none',
      stackgroup: 'one',
      fillcolor: hexToRgba(col, 0.5),
      line: { color: col },
      hoverinfo: 'none',
    };
  }).filter(t => t.y.some(v => v > 0));
  const layout = Object.assign({}, DARK_LAYOUT, {
    title: { text: 'Total Jobs Over Time', font: { color: '#e6edf3' } },
    xaxis: Object.assign({}, DARK_LAYOUT.xaxis),
    yaxis: Object.assign({}, DARK_LAYOUT.yaxis, { title: 'Jobs' }),
    hovermode: 'x',
    showlegend: true,
  });
  const el = document.getElementById('chart-jobs-time');
  Plotly.react(el, traces, layout, PLOTLY_CONFIG);
  // Custom hover: show only users with >0 jobs at the hovered time point
  el.addEventListener('mousemove', function(e) {
    const tooltip = document.getElementById('jobs-time-tooltip');
    if (tooltip && tooltip.style.display === 'block') {
      const rect = el.getBoundingClientRect();
      tooltip.style.left = (e.clientX - rect.left + 15) + 'px';
      tooltip.style.top = (e.clientY - rect.top - 10) + 'px';
    }
  });
  el.on('plotly_hover', function(evtData) {
    if (!evtData.points || !evtData.points[0]) return;
    const idx = evtData.points[0].pointIndex;
    const lines = [];
    const liveTraces = el.data || traces;
    liveTraces.forEach(t => {
      if (t.visible === 'legendonly') return;
      const v = t.y[idx];
      if (v > 0) lines.push('<span style="color:' + t.line.color + '">\u25CF</span> ' + t.name + ': ' + v + ' jobs');
    });
    if (!lines.length) return;
    const tooltip = document.getElementById('jobs-time-tooltip');
    if (tooltip) {
      tooltip.innerHTML = '<b>' + liveTraces[0].x[idx] + '</b><br>' + lines.join('<br>');
      tooltip.style.display = 'block';
    }
  });
  el.on('plotly_unhover', function() {
    const tooltip = document.getElementById('jobs-time-tooltip');
    if (tooltip) tooltip.style.display = 'none';
  });
}
"""


def _chart_user_bar_js() -> str:
    return """
// ── Chart 3: Total Jobs by User (horizontal bar) ─────────────────────────────
function renderChartUserBar() {
  // Recount per user based on filtered hours
  const hours = getFilteredHours();
  const hourSet = new Set(hours);
  const userCounts = {};
  getVisibleUsers().forEach(user => {
    const hourly = DATA.hourly_by_user[user] || {};
    let count = 0;
    for (const h of hours) { count += (hourly[h] || 0); }
    if (count > 0) userCounts[user] = count;
  });
  const sorted = Object.keys(userCounts).sort((a, b) => userCounts[a] - userCounts[b]);
  const traces = [{
    type: 'bar',
    orientation: 'h',
    x: sorted.map(u => userCounts[u]),
    y: sorted,
    marker: { color: sorted.map(u => getUserColor(u)) },
    hovertemplate: '%{x} jobs<extra>%{y}</extra>',
  }];
  const layout = Object.assign({}, DARK_LAYOUT, {
    title: { text: 'Jobs by User <span style="font-size:11px;color:#8b949e">(click bar for details)</span>', font: { color: '#e6edf3' } },
    xaxis: Object.assign({}, DARK_LAYOUT.xaxis, { title: 'Total Jobs', rangemode: 'tozero' }),
    yaxis: Object.assign({}, DARK_LAYOUT.yaxis, { tickmode: 'linear', dtick: 1 }),
    height: Math.max(400, sorted.length * 28 + 80),
    showlegend: false,
    margin: Object.assign({}, DARK_LAYOUT.margin, { l: Math.max(100, Math.max(...sorted.map(u => u.length)) * 8 + 20) }),
  });
  const el = document.getElementById('chart-user-bar');
  if (el) {
    Plotly.react('chart-user-bar', traces, layout, PLOTLY_CONFIG);
    el.on('plotly_click', data => {
      if (data.points && data.points[0]) {
        toggleUser(data.points[0].y);
      }
    });
  }
}
"""


def _chart_user_lines_js() -> str:
    return """
// ── Chart 4: Job Submissions by User Over Time (line) ────────────────────────
function renderChartUserLines() {
  const hours = getFilteredHours();
  const labels = formatHourLabels(hours);
  const traces = getVisibleUsers().map(user => {
    const yVals = hours.map(h => (DATA.hourly_by_user[user] || {})[h] || null);
    return {
      name: user,
      x: labels,
      y: yVals,
      type: 'scatter',
      mode: 'lines',
      line: { color: getUserColor(user), width: 2 },
      opacity: 0.6,
      hovertemplate: '%{y} jobs<extra>' + user + '</extra>',
    };
  }).filter(t => t.y.some(v => v > 0));
  const layout = Object.assign({}, DARK_LAYOUT, {
    title: { text: 'Job Submissions by User Over Time', font: { color: '#e6edf3' } },
    xaxis: Object.assign({}, DARK_LAYOUT.xaxis),
    yaxis: Object.assign({}, DARK_LAYOUT.yaxis, { title: 'Jobs Submitted' }),
    showlegend: true,
  });
  Plotly.react('chart-user-lines', traces, layout, PLOTLY_CONFIG);
}
"""


def _chart_running_time_js() -> str:
    return """
// ── Chart: Running Jobs Over Time (stacked area) ────────────────────────────
function renderChartRunningTime() {
  const hours = getFilteredHours();
  const labels = formatHourLabels(hours);
  const traces = getVisibleUsers().map(user => {
    const yVals = hours.map(h => (DATA.running_by_user[user] || {})[h] || 0);
    const col = getUserColor(user);
    return {
      name: user,
      x: labels,
      y: yVals,
      type: 'scatter',
      mode: 'none',
      stackgroup: 'one',
      fillcolor: hexToRgba(col, 0.5),
      line: { color: col },
      hoverinfo: 'none',
    };
  }).filter(t => t.y.some(v => v > 0));
  const layout = Object.assign({}, DARK_LAYOUT, {
    title: { text: 'Running Jobs Over Time', font: { color: '#e6edf3' } },
    xaxis: Object.assign({}, DARK_LAYOUT.xaxis),
    yaxis: Object.assign({}, DARK_LAYOUT.yaxis, { title: 'Concurrent Jobs' }),
    hovermode: 'x',
    showlegend: true,
  });
  const el = document.getElementById('chart-running-time');
  Plotly.react(el, traces, layout, PLOTLY_CONFIG);
  el.addEventListener('mousemove', function(e) {
    const tooltip = document.getElementById('running-time-tooltip');
    if (tooltip && tooltip.style.display === 'block') {
      const rect = el.getBoundingClientRect();
      tooltip.style.left = (e.clientX - rect.left + 15) + 'px';
      tooltip.style.top = (e.clientY - rect.top - 10) + 'px';
    }
  });
  el.on('plotly_hover', function(evtData) {
    if (!evtData.points || !evtData.points[0]) return;
    const idx = evtData.points[0].pointIndex;
    const lines = [];
    const liveTraces = el.data || traces;
    liveTraces.forEach(t => {
      if (t.visible === 'legendonly') return;
      const v = t.y[idx];
      if (v > 0) lines.push('<span style="color:' + t.line.color + '">\u25CF</span> ' + t.name + ': ' + v + ' jobs');
    });
    if (!lines.length) return;
    const tooltip = document.getElementById('running-time-tooltip');
    if (tooltip) {
      tooltip.innerHTML = '<b>' + liveTraces[0].x[idx] + '</b><br>' + lines.join('<br>');
      tooltip.style.display = 'block';
    }
  });
  el.on('plotly_unhover', function() {
    const tooltip = document.getElementById('running-time-tooltip');
    if (tooltip) tooltip.style.display = 'none';
  });
}
"""


def _chart_drilldown_js() -> str:
    return """
// ── Chart 5: Drilldown ────────────────────────────────────────────────────────
function renderDrilldown() {
  if (!selectedUser) return;
  if (drilldownTab === 'process') renderDrilldownProcess();
  else renderDrilldownSample();
}

let processSortCol = 'count';
let processSortAsc = false;

function renderDrilldownProcess() {
  const processData = (DATA.process_by_user[selectedUser] || {});
  const procs = Object.keys(processData);

  // Sort
  procs.sort((a, b) => {
    let va, vb;
    if (processSortCol === 'name') { va = a.toLowerCase(); vb = b.toLowerCase(); }
    else if (processSortCol === 'count') { va = processData[a].count; vb = processData[b].count; }
    else if (processSortCol === 'wait') { va = processData[a].wait.avg; vb = processData[b].wait.avg; }
    else { va = processData[a].run.avg; vb = processData[b].run.avg; }
    if (va < vb) return processSortAsc ? -1 : 1;
    if (va > vb) return processSortAsc ? 1 : -1;
    return 0;
  });

  const maxWait = Math.max(...procs.map(p => processData[p].wait.avg || 0), 1);
  const maxRun = Math.max(...procs.map(p => processData[p].run.avg || 0), 1);
  const color = getUserColor(selectedUser);

  const arrow = col => processSortCol === col ? (processSortAsc ? ' \\u25B2' : ' \\u25BC') : '';

  let html = '<table style="width:100%;border-collapse:collapse;font-size:13px;color:#e6edf3;">';
  html += '<thead><tr style="border-bottom:1px solid #30363d;color:#58a6ff;cursor:pointer;">';
  html += '<th style="text-align:left;padding:6px 8px;" onclick="sortProcessTable(&quot;name&quot;)">Process' + arrow('name') + '</th>';
  html += '<th style="text-align:right;padding:6px 8px;width:70px;" onclick="sortProcessTable(&quot;count&quot;)">Count' + arrow('count') + '</th>';
  html += '<th style="text-align:left;padding:6px 8px;" onclick="sortProcessTable(&quot;wait&quot;)">Avg Wait' + arrow('wait') + '</th>';
  html += '<th style="text-align:left;padding:6px 8px;" onclick="sortProcessTable(&quot;run&quot;)">Avg Run' + arrow('run') + '</th>';
  html += '</tr></thead><tbody>';

  procs.forEach(p => {
    const d = processData[p];
    const waitPct = ((d.wait.avg || 0) / maxWait * 100).toFixed(1);
    const runPct = ((d.run.avg || 0) / maxRun * 100).toFixed(1);
    html += '<tr style="border-bottom:1px solid #161b22;">';
    html += '<td style="padding:5px 8px;color:#e6edf3;">' + p + '</td>';
    html += '<td style="padding:5px 8px;text-align:right;color:#8b949e;">' + d.count.toLocaleString() + '</td>';
    html += '<td style="padding:5px 8px;"><div style="display:flex;align-items:center;gap:6px;">'
      + '<div style="background:#8b949e;height:10px;width:' + waitPct + '%;min-width:2px;border-radius:2px;flex-shrink:0;max-width:60%;"></div>'
      + '<span style="color:#8b949e;font-size:11px;white-space:nowrap;">' + formatSeconds(d.wait.avg || 0) + '</span>'
      + '</div></td>';
    html += '<td style="padding:5px 8px;"><div style="display:flex;align-items:center;gap:6px;">'
      + '<div style="background:' + color + ';height:10px;width:' + runPct + '%;min-width:2px;border-radius:2px;flex-shrink:0;max-width:60%;"></div>'
      + '<span style="color:#8b949e;font-size:11px;white-space:nowrap;">' + formatSeconds(d.run.avg || 0) + '</span>'
      + '</div></td>';
    html += '</tr>';
  });

  html += '</tbody></table>';
  document.getElementById('chart-drilldown').innerHTML = html;
}

function sortProcessTable(col) {
  if (processSortCol === col) processSortAsc = !processSortAsc;
  else { processSortCol = col; processSortAsc = col === 'name'; }
  renderDrilldownProcess();
}

function renderDrilldownSample() {
  const sampleData = (DATA.sample_by_user[selectedUser] || {});
  const samples = Object.keys(sampleData).sort(
    (a, b) => sampleData[b].count - sampleData[a].count
  ).slice(0, 20);
  const traces = [{
    type: 'bar', orientation: 'h',
    x: samples.map(s => Number(sampleData[s].count)),
    y: samples,
    marker: { color: getUserColor(selectedUser) },
    hovertemplate: '%{x} jobs<extra>%{y}</extra>',
  }];
  const layout = Object.assign({}, DARK_LAYOUT, {
    title: { text: 'Sample Breakdown: ' + selectedUser, font: { color: '#e6edf3' } },
    xaxis: Object.assign({}, DARK_LAYOUT.xaxis, { title: 'Job Count', type: 'linear' }),
    yaxis: Object.assign({}, DARK_LAYOUT.yaxis),
    margin: Object.assign({}, DARK_LAYOUT.margin, { l: 180 }),
    height: Math.max(200, samples.length * 28 + 80),
  });
  Plotly.react('chart-drilldown', traces, layout, PLOTLY_CONFIG);
}

function closeDrilldown() {
  selectedUser = null;
  document.getElementById('drilldown-container').style.display = 'none';
}

function showDrilldownTab(tab) {
  drilldownTab = tab;
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tab);
  });
  renderDrilldown();
}
"""


def _chart_mem_scatter_js() -> str:
    return """
// ── Chart 6: Memory Requested vs Used (scatter) ──────────────────────────────
function renderChartMemScatter() {
  const visible = new Set(getVisibleUsers());
  const byUser = {};
  (DATA.mem_scatter || []).filter(pt => visible.has(pt.user)).forEach(pt => {
    if (!byUser[pt.user]) byUser[pt.user] = { x: [], y: [], text: [] };
    byUser[pt.user].x.push(Number(pt.req_mem_mb) / 1024);
    byUser[pt.user].y.push(Number(pt.max_rss_mb) / 1024);
    byUser[pt.user].text.push(pt.job_name);
  });
  const maxVal = Math.max(0.1, ...Object.values(byUser).flatMap(d => [...d.x, ...d.y]));
  const refLine = {
    name: 'req = used',
    x: [0, maxVal], y: [0, maxVal],
    type: 'scatter', mode: 'lines',
    line: { dash: 'dash', color: '#8b949e', width: 1 },
    hoverinfo: 'skip',
    showlegend: false,
  };
  const userTraces = Object.keys(byUser).map(user => ({
    name: user,
    x: byUser[user].x,
    y: byUser[user].y,
    text: byUser[user].text,
    type: 'scatter', mode: 'markers',
    marker: { color: getUserColor(user), size: 7, opacity: 0.8 },
    hovertemplate: '<b>%{text}</b><br>Requested: %{x:.1f} GB<br>Used: %{y:.1f} GB<extra>' + user + '</extra>',
  }));
  const layout = Object.assign({}, DARK_LAYOUT, {
    title: { text: 'Memory Requested vs Used', font: { color: '#e6edf3' } },
    xaxis: Object.assign({}, DARK_LAYOUT.xaxis, { title: 'Requested (GB)', type: 'linear', rangemode: 'tozero' }),
    yaxis: Object.assign({}, DARK_LAYOUT.yaxis, { title: 'Used (GB)', type: 'linear', rangemode: 'tozero' }),
    showlegend: true,
  });
  Plotly.react('chart-mem-scatter', [refLine, ...userTraces], layout, PLOTLY_CONFIG);
}
"""


def _chart_wait_overall_js() -> str:
    return """
// ── Chart 7: Overall Queue Wait Time (line + band) ───────────────────────────
function renderChartWaitOverall() {
  const hours = getFilteredHours();
  const labels = formatHourLabels(hours);
  const waitData = DATA.hourly_wait || {};
  const p25 = hours.map(h => (waitData[h] || {}).p25 || 0);
  const p75 = hours.map(h => (waitData[h] || {}).p75 || 0);
  const med = hours.map(h => (waitData[h] || {}).median || 0);
  const bandX = [...labels, ...labels.slice().reverse()];
  const bandY = [...p75, ...p25.slice().reverse()];
  const bandTrace = {
    name: 'p25–p75',
    x: bandX, y: bandY,
    fill: 'toself',
    type: 'scatter', mode: 'none',
    fillcolor: 'rgba(88,166,255,0.15)',
    hoverinfo: 'skip',
    showlegend: true,
  };
  const medHoverText = med.map(v => formatSeconds(v));
  const medianTrace = {
    name: 'Median',
    x: labels, y: med,
    text: medHoverText,
    type: 'scatter', mode: 'lines',
    line: { color: '#58a6ff', width: 2 },
    hovertemplate: 'Median: %{text}<extra></extra>',
  };
  const yAxisConf = makeTimeYAxis([...med, ...p75], 'Wait');
  const layout = Object.assign({}, DARK_LAYOUT, {
    title: { text: 'Queue Wait Time', font: { color: '#e6edf3' } },
    xaxis: Object.assign({}, DARK_LAYOUT.xaxis),
    yaxis: Object.assign({}, DARK_LAYOUT.yaxis, yAxisConf),
    showlegend: true,
  });
  Plotly.react('chart-wait-overall', [bandTrace, medianTrace], layout, PLOTLY_CONFIG);
}
"""


def _chart_wait_user_box_js() -> str:
    return """
// ── Chart 8: Wait Time by User (box plot) ────────────────────────────────────
function renderChartWaitUserBox() {
  const users = getVisibleUsers();
  const allVals = users.flatMap(u => DATA.wait_by_user[u] || []);
  const yAxisConf = makeTimeYAxis(allVals, 'Wait');
  const traces = users.map(user => {
    const vals = (DATA.wait_by_user[user] || []).map(Number);
    const divisor = yAxisConf.title.includes('hours') ? 3600 : yAxisConf.title.includes('minutes') ? 60 : 1;
    const unit = divisor === 3600 ? ' hr' : divisor === 60 ? ' min' : ' sec';
    return {
      name: user,
      y: vals.map(v => v / divisor),
      type: 'box',
      marker: { color: getUserColor(user) },
      boxmean: true,
      hovertemplate: '%{y:.2f}' + unit + '<extra>%{x}</extra>',
    };
  });
  const unitLabel = yAxisConf.title.includes('hours') ? 'hours' : yAxisConf.title.includes('minutes') ? 'minutes' : 'seconds';
  const layout = Object.assign({}, DARK_LAYOUT, {
    title: { text: 'Wait Time by User', font: { color: '#e6edf3' } },
    yaxis: Object.assign({}, DARK_LAYOUT.yaxis, { title: 'Wait (' + unitLabel + ')' }),
    showlegend: false,
  });
  Plotly.react('chart-wait-user-box', traces, layout, PLOTLY_CONFIG);
}
"""


def _chart_wait_user_line_js() -> str:
    return """
// ── Chart 9: Wait Time by User Over Time (line) ──────────────────────────────
function renderChartWaitUserLine() {
  const hours = getFilteredHours();
  const labels = formatHourLabels(hours);
  const allVals = [];
  const traces = getVisibleUsers().map(user => {
    const userHourly = DATA.wait_by_user_hourly[user] || {};
    const yVals = hours.map(h => userHourly[h] != null ? Number(userHourly[h]) : null);
    yVals.forEach(v => { if (v != null) allVals.push(v); });
    const hoverText = yVals.map(v => v != null ? formatSeconds(v) : '');
    return {
      name: user,
      x: labels,
      y: yVals,
      text: hoverText,
      type: 'scatter', mode: 'lines',
      connectgaps: false,
      line: { color: getUserColor(user), width: 2 },
      hovertemplate: '%{text}<extra>' + user + '</extra>',
    };
  });
  const yAxisConf = makeTimeYAxis(allVals, 'Avg Wait');
  const layout = Object.assign({}, DARK_LAYOUT, {
    title: { text: 'Avg Wait Time by User Over Time', font: { color: '#e6edf3' } },
    xaxis: Object.assign({}, DARK_LAYOUT.xaxis),
    yaxis: Object.assign({}, DARK_LAYOUT.yaxis, yAxisConf),
    showlegend: true,
  });
  Plotly.react('chart-wait-user-line', traces, layout, PLOTLY_CONFIG);
}
"""


def _chart_cpu_eff_js() -> str:
    return """
// ── Chart 10: CPU Efficiency by User (box plot) ──────────────────────────────
function renderChartCpuEff() {
  const traces = getVisibleUsers().map(user => ({
    name: user,
    y: (DATA.cpu_eff_by_user[user] || []).map(Number),
    type: 'box',
    marker: { color: getUserColor(user) },
    boxmean: true,
  }));
  const layout = Object.assign({}, DARK_LAYOUT, {
    title: { text: 'CPU Efficiency by User', font: { color: '#e6edf3' } },
    yaxis: Object.assign({}, DARK_LAYOUT.yaxis, {
      title: 'CPU Efficiency', range: [0, 1.1],
      tickformat: '.0%',
    }),
    showlegend: false,
  });
  Plotly.react('chart-cpu-eff', traces, layout, PLOTLY_CONFIG);
}
"""


def _chart_mem_eff_js() -> str:
    return """
// ── Chart 10b: Memory Efficiency by User (box plot) ────────────────────────
function renderChartMemEff() {
  const traces = getVisibleUsers().map(user => ({
    name: user,
    y: (DATA.mem_eff_by_user[user] || []).map(Number),
    type: 'box',
    marker: { color: getUserColor(user) },
    boxmean: true,
    hovertemplate: '%{y:.2%}<extra>' + user + '</extra>',
  }));
  const layout = Object.assign({}, DARK_LAYOUT, {
    title: { text: 'Memory Efficiency by User', font: { color: '#e6edf3' } },
    yaxis: Object.assign({}, DARK_LAYOUT.yaxis, {
      title: 'Memory Efficiency', range: [0, 1.1],
      tickformat: '.0%',
    }),
    showlegend: false,
  });
  Plotly.react('chart-mem-eff', traces, layout, PLOTLY_CONFIG);
}
"""


def _chart_node_heat_js() -> str:
    return """
// ── Chart 11: Node Utilization Heatmap ───────────────────────────────────────
function renderChartNodeHeat() {
  const matrix = DATA.node_hour_matrix || { nodes: [], hours: [], values: [] };
  const hours = getFilteredHours();
  const hourSet = new Set(hours);
  const allHours = matrix.hours || [];
  const filteredIdxs = allHours.map((h, i) => hourSet.has(h) ? i : -1).filter(i => i >= 0);
  const filteredHourLabels = formatHourLabels(filteredIdxs.map(i => allHours[i]));
  const filteredValues = (matrix.values || []).map(row =>
    filteredIdxs.map(i => row[i] || 0)
  );
  const traces = [{
    type: 'heatmap',
    x: filteredHourLabels,
    y: matrix.nodes || [],
    z: filteredValues,
    colorscale: [
      [0, '#0d1117'], [0.25, '#0c4a6e'], [0.5, '#0369a1'],
      [0.75, '#0284c7'], [1, '#38bdf8'],
    ],
    hovertemplate: '%{y}<br>%{x}<br>Jobs: %{z}<extra></extra>',
    showscale: true,
  }];
  const layout = Object.assign({}, DARK_LAYOUT, {
    title: { text: 'Node Utilization', font: { color: '#e6edf3' } },
    xaxis: Object.assign({}, DARK_LAYOUT.xaxis),
    yaxis: Object.assign({}, DARK_LAYOUT.yaxis, { automargin: true }),
    margin: Object.assign({}, DARK_LAYOUT.margin, { l: 120 }),
  });
  Plotly.react('chart-node-heat', traces, layout, PLOTLY_CONFIG);
}
"""


def _chart_failed_js() -> str:
    return """
// ── Chart 12: Failed Jobs by User (stacked bar) ──────────────────────────────
function renderChartFailed() {
  const failedData = DATA.failed_by_user || {};
  const visible = new Set(getVisibleUsers());
  const users = Object.keys(failedData).filter(u => visible.has(u));
  const allStates = ['FAILED', 'TIMEOUT', 'CANCELLED', 'OUT_OF_MEMORY'];
  const hasData = users.length > 0;
  if (!hasData) {
    const layout = Object.assign({}, DARK_LAYOUT, {
      title: { text: 'Failed Jobs by User', font: { color: '#e6edf3' } },
      annotations: [{
        text: 'No failed jobs',
        x: 0.5, y: 0.5, xref: 'paper', yref: 'paper',
        showarrow: false,
        font: { color: '#8b949e', size: 16 },
      }],
    });
    Plotly.react('chart-failed', [], layout, PLOTLY_CONFIG);
    return;
  }
  const traces = allStates
    .filter(state => users.some(u => (failedData[u] || {})[state]))
    .map(state => ({
      name: state,
      x: users,
      y: users.map(u => (failedData[u] || {})[state] || 0),
      type: 'bar',
      marker: { color: STATE_COLORS[state] || '#8b949e' },
      hovertemplate: state + ': %{y}<extra></extra>',
    }));
  const layout = Object.assign({}, DARK_LAYOUT, {
    title: { text: 'Failed Jobs by User', font: { color: '#e6edf3' } },
    barmode: 'stack',
    hovermode: 'x unified',
    xaxis: Object.assign({}, DARK_LAYOUT.xaxis, { title: 'User' }),
    yaxis: Object.assign({}, DARK_LAYOUT.yaxis, { title: 'Job Count' }),
    showlegend: true,
  });
  Plotly.react('chart-failed', traces, layout, PLOTLY_CONFIG);
}
"""


def _main_js() -> str:
    return """
// ── Main ──────────────────────────────────────────────────────────────────────
function renderAllCharts() {
  renderChartJobsTime();
  renderChartUserBar();
  renderChartUserLines();
  renderChartRunningTime();
  renderChartMemScatter();
  renderChartWaitOverall();
  renderChartWaitUserBox();
  renderChartWaitUserLine();
  renderChartCpuEff();
  renderChartMemEff();
  renderChartNodeHeat();
  renderChartFailed();
  if (selectedUser) renderDrilldown();
}

function initCharts(data) {
  DATA = data;

  // Build user filter chips
  const chipContainer = document.getElementById('user-chips');
  if (chipContainer) {
    const allChip = document.createElement('span');
    allChip.className = 'user-chip chip-all active';
    allChip.textContent = 'All';
    allChip.onclick = clearUserFilter;
    chipContainer.appendChild(allChip);
    DATA.users.forEach(u => {
      const chip = document.createElement('span');
      chip.className = 'user-chip';
      chip.dataset.user = u;
      chip.textContent = u;
      chip.onclick = () => toggleUser(u);
      chipContainer.appendChild(chip);
    });
  }
  updateKPIs();
  renderAllCharts();
}
"""


def get_chart_javascript() -> str:
    """Return all JavaScript for the dashboard as a single string."""
    parts = [
        _base_js(),
        _chart_jobs_time_js(),
        _chart_user_bar_js(),
        _chart_user_lines_js(),
        _chart_running_time_js(),
        _chart_drilldown_js(),
        _chart_mem_scatter_js(),
        _chart_wait_overall_js(),
        _chart_wait_user_box_js(),
        _chart_wait_user_line_js(),
        _chart_cpu_eff_js(),
        _chart_mem_eff_js(),
        _chart_node_heat_js(),
        _chart_failed_js(),
        _main_js(),
    ]
    return "\n".join(parts)

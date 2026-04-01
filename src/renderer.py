# src/renderer.py
"""Render enriched aggregator data to a self-contained HTML dashboard."""

import json
from datetime import datetime

from src.chart_js import get_chart_javascript


def _format_seconds(s: float) -> str:
    s = int(s)
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s // 60}m {s % 60}s"
    h = s // 3600
    m = (s % 3600) // 60
    return f"{h}h {m}m"


_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #0d1117; color: #e6edf3; font-family: system-ui, -apple-system, sans-serif; }
.dashboard { max-width: 1600px; margin: 0 auto; padding: 16px; }

/* Header */
.header { display: flex; align-items: center; justify-content: space-between;
  padding: 12px 0 20px; border-bottom: 1px solid #21262d; margin-bottom: 16px; }
.header h1 { font-size: 1.25rem; font-weight: 600; color: #e6edf3; }
.controls { display: flex; align-items: center; gap: 12px; }
#user-chips { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.user-chip { background: #161b22; border: 1px solid #30363d; color: #8b949e;
  padding: 4px 10px; border-radius: 14px; font-size: 0.75rem; cursor: pointer;
  transition: all 0.15s; user-select: none; }
.user-chip:hover { border-color: #58a6ff; color: #e6edf3; }
.user-chip.active { border-color: #58a6ff; color: #e6edf3; background: #1f2937; }
.user-chip.chip-all { font-weight: 600; }
.toggle { display: flex; gap: 4px; background: #161b22; border: 1px solid #30363d;
  border-radius: 6px; padding: 4px; }
.toggle-btn { background: transparent; border: none; color: #8b949e;
  padding: 6px 14px; border-radius: 4px; cursor: pointer; font-size: 0.875rem;
  transition: all 0.15s; }
.toggle-btn:hover { color: #e6edf3; background: #21262d; }
.toggle-btn.active { background: #21262d; color: #e6edf3; font-weight: 600; }

/* KPI Row */
.kpi-row { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.kpi-card { flex: 1; min-width: 140px; background: #161b22; border: 1px solid #30363d;
  border-radius: 8px; padding: 16px; }
.kpi-card.kpi-warn { border-color: #d29922; }
.kpi-card.kpi-bad  { border-color: #f85149; }
.kpi-label { font-size: 0.75rem; color: #8b949e; text-transform: uppercase;
  letter-spacing: 0.05em; margin-bottom: 6px; }
.kpi-value { font-size: 1.75rem; font-weight: 700; color: #e6edf3; }
.kpi-card.kpi-warn .kpi-value { color: #d29922; }
.kpi-card.kpi-bad  .kpi-value { color: #f85149; }

/* Chart layout */
.chart-row { display: flex; gap: 12px; margin-bottom: 12px; }
.chart-box { background: #161b22; border: 1px solid #30363d; border-radius: 8px;
  padding: 8px; overflow: hidden; }
.chart-box.wide   { flex: 3; min-width: 0; }
.chart-box.narrow { flex: 2; min-width: 0; }
.chart-box.half   { flex: 1; min-width: 0; }
.chart-box.full   { flex: 1; width: 100%; }

/* Drilldown */
#drilldown-container { background: #161b22; border: 1px solid #30363d;
  border-radius: 8px; padding: 12px; margin-bottom: 12px; }
.drilldown-header { display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 8px; }
.drilldown-header h3 { font-size: 0.9rem; color: #8b949e; }
.drilldown-header h3 span { color: #58a6ff; font-weight: 600; }
.drilldown-tabs { display: flex; gap: 4px; }
.tab-btn { background: #21262d; border: 1px solid #30363d; color: #8b949e;
  padding: 4px 12px; border-radius: 4px; cursor: pointer; font-size: 0.8rem;
  transition: all 0.15s; }
.tab-btn:hover { color: #e6edf3; }
.tab-btn.active { background: #0c4a6e; border-color: #58a6ff; color: #58a6ff; }
.close-btn { background: transparent; border: 1px solid #30363d; color: #8b949e;
  width: 28px; height: 28px; border-radius: 6px; cursor: pointer; font-size: 1rem;
  display: flex; align-items: center; justify-content: center; transition: all 0.15s; }
.close-btn:hover { border-color: #f85149; color: #f85149; }

/* About modal */
.about-btn { background: transparent; border: 1px solid #30363d; color: #8b949e;
  padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 0.875rem;
  transition: all 0.15s; }
.about-btn:hover { border-color: #58a6ff; color: #e6edf3; }
#about-modal { display:none; position:fixed; inset:0; z-index:100; background:rgba(0,0,0,0.7);
  align-items:center; justify-content:center; }
#about-modal.show { display:flex; }
.about-content { background:#161b22; border:1px solid #30363d; border-radius:12px;
  max-width:720px; width:90%; max-height:80vh; overflow-y:auto; padding:24px;
  color:#e6edf3; font-size:0.875rem; line-height:1.7; }
.about-content h2 { font-size:1.1rem; margin-bottom:16px; color:#58a6ff; }
.about-content h3 { font-size:0.9rem; margin:16px 0 4px; color:#e6edf3; }
.about-content p { color:#8b949e; margin-bottom:8px; }
.about-content code { background:#21262d; padding:1px 5px; border-radius:3px; font-size:0.8rem; }
.about-close { float:right; background:transparent; border:none; color:#8b949e;
  font-size:1.5rem; cursor:pointer; line-height:1; }
.about-close:hover { color:#f85149; }

/* Footer */
.footer { text-align: center; color: #484f58; font-size: 11px; margin-top: 20px; padding: 12px; }
"""


def _kpi_card(label: str, value: str, element_id: str, extra_class: str = "") -> str:
    cls = f"kpi-card {extra_class}".strip()
    return (
        f'<div class="{cls}">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value" id="{element_id}">{value}</div>'
        f"</div>"
    )


def render_dashboard(data: dict) -> str:
    """Render aggregator output to a complete self-contained HTML string."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    kpis = data.get("kpis", {})
    total_jobs = kpis.get("total_jobs", 0)
    active_users = kpis.get("active_users", 0)
    median_wait = _format_seconds(kpis.get("median_wait", 0))
    mem_eff_raw = kpis.get("median_mem_efficiency", 0)
    mem_eff = f"{mem_eff_raw * 100:.1f}%"
    failed_jobs = kpis.get("failed_jobs", 0)

    mem_class = "kpi-bad" if mem_eff_raw < 0.3 else ("kpi-warn" if mem_eff_raw < 0.6 else "")
    fail_class = "kpi-bad" if failed_jobs > 10 else ("kpi-warn" if failed_jobs > 0 else "")

    kpi_row = "".join([
        _kpi_card("Total Jobs", str(total_jobs), "kpi-total-jobs"),
        _kpi_card("Active Users", str(active_users), "kpi-active-users"),
        _kpi_card("Median Wait", median_wait, "kpi-median-wait"),
        _kpi_card("Memory Efficiency", mem_eff, "kpi-mem-eff", mem_class),
        _kpi_card("Failed Jobs", str(failed_jobs), "kpi-failed-jobs", fail_class),
    ])

    days = len(data.get("all_dates", []))
    jobs = kpis.get("total_jobs", 0)
    json_data = json.dumps(data, default=str)
    chart_js = get_chart_javascript()

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CMOBIC CPU Queue Dashboard</title>
<script src="https://cdn.plot.ly/plotly-2.35.0.min.js"></script>
<style>
{_CSS}
</style>
</head>
<body>
<div class="dashboard">

  <div class="header">
    <h1>CMOBIC CPU Queue Dashboard</h1>
    <div class="controls">
      <button class="about-btn" onclick="document.getElementById('about-modal').classList.add('show')">About</button>
      <div class="toggle">
        <button class="toggle-btn" data-range="1d" onclick="setRange('1d')">1 Day</button>
        <button class="toggle-btn active" data-range="7d" onclick="setRange('7d')">7 Days</button>
      </div>
    </div>
  </div>

  <div class="kpi-row">
    {kpi_row}
  </div>

  <div id="user-chips" style="margin-bottom:12px"></div>

  <div class="chart-row">
    <div class="chart-box wide" style="position:relative"><div id="chart-jobs-time" style="height:300px"></div><div id="jobs-time-tooltip" style="display:none;position:absolute;background:rgba(22,27,34,0.95);border:1px solid #30363d;border-radius:6px;padding:8px 12px;font-size:12px;color:#e6edf3;pointer-events:none;z-index:10;line-height:1.6;white-space:nowrap"></div></div>
    <div class="chart-box narrow"><div id="chart-user-bar" style="height:300px"></div></div>
  </div>

  <div class="chart-row">
    <div class="chart-box full"><div id="chart-user-lines" style="height:280px"></div></div>
  </div>

  <div class="chart-row">
    <div class="chart-box full" style="position:relative"><div id="chart-running-time" style="height:300px"></div><div id="running-time-tooltip" style="display:none;position:absolute;background:rgba(22,27,34,0.95);border:1px solid #30363d;border-radius:6px;padding:8px 12px;font-size:12px;color:#e6edf3;pointer-events:none;z-index:10;line-height:1.6;white-space:nowrap"></div></div>
  </div>

  <div id="drilldown-container" style="display:none">
    <div class="drilldown-header">
      <h3>Drilldown: <span id="drilldown-user-name"></span></h3>
      <div style="display:flex; gap:8px; align-items:center">
        <div class="drilldown-tabs">
          <button class="tab-btn active" data-tab="process" onclick="showDrilldownTab('process')">By Process</button>
          <button class="tab-btn" data-tab="sample" onclick="showDrilldownTab('sample')">By Sample</button>
        </div>
        <button class="close-btn" onclick="closeDrilldown()" title="Close">&times;</button>
      </div>
    </div>
    <div id="chart-drilldown" style="min-height:200px"></div>
  </div>

  <div class="chart-row">
    <div class="chart-box half"><div id="chart-mem-scatter" style="height:300px"></div></div>
    <div class="chart-box half"><div id="chart-wait-overall" style="height:300px"></div></div>
  </div>

  <div class="chart-row">
    <div class="chart-box half"><div id="chart-wait-user-box" style="height:300px"></div></div>
    <div class="chart-box half"><div id="chart-wait-user-line" style="height:300px"></div></div>
  </div>

  <div class="chart-row">
    <div class="chart-box half"><div id="chart-cpu-eff" style="height:300px"></div></div>
    <div class="chart-box half"><div id="chart-mem-eff" style="height:300px"></div></div>
  </div>

  <div class="chart-row">
    <div class="chart-box full"><div id="chart-node-heat" style="height:300px"></div></div>
  </div>

  <div class="chart-row">
    <div class="chart-box full"><div id="chart-failed" style="height:280px"></div></div>
  </div>

  <div id="about-modal" onclick="if(event.target===this)this.classList.remove('show')">
    <div class="about-content">
      <button class="about-close" onclick="document.getElementById('about-modal').classList.remove('show')">&times;</button>
      <h2>About This Dashboard</h2>
      <p>Reads <code>job_YYYY-MM-DD.json</code> files exported from SLURM <code>sacct</code>. Each file is a JSON array of completed job records from the past 7 days.</p>

      <h3>KPI Cards</h3>
      <p>Total jobs, active users, median queue wait time, median memory efficiency (<code>MaxRSS / ReqMem</code>), and failed job count. Updates when the time range or user filter changes.</p>

      <h3>Total Jobs Over Time</h3>
      <p>Stacked area chart. Each hour bucket counts jobs whose <code>submit</code> timestamp falls in that hour, grouped by user.</p>

      <h3>Jobs by User</h3>
      <p>Horizontal bar chart of total job count per user in the selected time range. Click a bar to toggle that user in the filter and open the drilldown panel.</p>

      <h3>Job Submissions by User Over Time</h3>
      <p>Line chart with one line per user showing hourly submission counts. Zero-value hours show as gaps (null) to keep hover clean.</p>

      <h3>Running Jobs Over Time</h3>
      <p>Stacked area chart showing <em>concurrent</em> running jobs. For each hour, counts jobs where <code>start &le; hour &le; end</code>. Reveals actual cluster utilization vs. submission patterns.</p>

      <h3>Memory Requested vs Used</h3>
      <p>Scatter plot: x = <code>req_mem_mb</code> (converted to GB), y = <code>max_rss_mb</code> (peak RSS, converted to GB). The dashed diagonal is the 1:1 line &mdash; points below it indicate over-requested memory.</p>

      <h3>Queue Wait Time</h3>
      <p>Median wait time per hour with a shaded p25&ndash;p75 band. Wait = <code>start - submit</code> in seconds.</p>

      <h3>Wait Time by User (Box Plot)</h3>
      <p>Distribution of queue wait times per user. Shows median, quartiles, and outliers. Values are converted to hours, minutes, or seconds based on the data range.</p>

      <h3>Wait Time by User Over Time</h3>
      <p>Hourly average wait time per user as a line chart.</p>

      <h3>CPU Efficiency</h3>
      <p>Box plot of <code>cpu_time_raw / (elapsed &times; alloc_cpus)</code> per user. A value of 1.0 means all allocated CPU time was used. Values near 0 indicate idle cores.</p>

      <h3>Memory Efficiency</h3>
      <p>Box plot of <code>max_rss_mb / req_mem_mb</code> per user. Values near 1.0 mean memory was well-utilized; low values mean memory was over-requested.</p>

      <h3>Node Utilization Heatmap</h3>
      <p>Nodes (y) vs hours (x), colored by job count. Shows which nodes are busy and when.</p>

      <h3>Failed Jobs by User</h3>
      <p>Stacked bar chart of non-COMPLETED jobs grouped by state (FAILED, TIMEOUT, CANCELLED, etc.) per user.</p>
    </div>
  </div>

  <div class="footer">Generated: {timestamp} | Data: {days} days, {jobs} jobs</div>
</div>

<script>
const DASHBOARD_DATA = {json_data};
{chart_js}
</script>
</body>
</html>"""

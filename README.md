# Work Complete

> *"Work complete!"* — the Peon, Warcraft II & III

A self-contained HTML dashboard for monitoring SLURM job activity on the `cmobic_cpu` partition. A Python script reads daily job JSON files and generates a single interactive HTML file with Plotly.js charts — no server required.

## Quick Start

```bash
python generate_dashboard.py --data-dir /path/to/job_jsons --output dashboard.html
```

The script reads `job_YYYY-MM-DD.json` files from the data directory (last 7 days), pre-aggregates the data, and produces a single HTML file you can open in any browser.

### Scheduled Generation

Run on a cron schedule to keep the dashboard fresh:

```bash
# Every hour
0 * * * * cd /path/to/work_complete && python generate_dashboard.py --data-dir /path/to/jsons --output /path/to/dashboard.html
```

## Input Format

Each `job_YYYY-MM-DD.json` file is a JSON array of SLURM job records. Required fields:

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | string | Unique job identifier |
| `job_name` | string | Job name (used for process/sample ID extraction) |
| `user` | string | Submitting user |
| `state` | string | COMPLETED, FAILED, TIMEOUT, etc. |
| `submit` | ISO datetime | When submitted |
| `start` | ISO datetime | When started running |
| `end` | ISO datetime | When finished |
| `elapsed` | HH:MM:SS or D-HH:MM:SS | Wall time |
| `req_cpus` / `alloc_cpus` | int | Requested/allocated CPUs |
| `cpu_time_raw` | int | CPU-seconds consumed |
| `req_mem_mb` / `max_rss_mb` | float | Requested/peak memory (MB) |
| `node_list` | string[] | Nodes used |

Jobs with missing timestamps (pending/cancelled) are skipped.

## Dashboard Features

### Controls
- **1-Day / 7-Day toggle** — filters all charts to the most recent day or full 7-day window
- **User dropdown** — filters all charts to a single user; "All Users" resets

### Charts

| # | Chart | Type | Description |
|---|-------|------|-------------|
| 1 | KPI Cards | Summary | Total jobs, active users, median wait, memory efficiency, failed jobs |
| 2 | Total Jobs Over Time | Stacked area | Hourly submissions stacked by user |
| 3 | Jobs by User | Horizontal bar | Click a bar to open the drill-down panel |
| 4 | Submissions by User | Line | One line per user, hourly bins |
| 5 | Running Jobs Over Time | Stacked area | Concurrent running jobs per user (start-to-end overlap) |
| 6 | Process Breakdown | Sortable table | Avg wait + run per process type (hidden until user selected) |
| 6b | Sample Breakdown | Bar | Job counts per sample ID (tab in drill-down) |
| 7 | Memory Req vs Used | Scatter | Diagonal = perfect efficiency; dots below = waste |
| 8 | Queue Wait Time | Line + band | Hourly median with p25-p75 shaded band |
| 9 | Wait Time by User | Box plot | Distribution of queue wait per user |
| 10 | Wait Time by User | Line | Hourly avg wait per user over time |
| 11 | CPU Efficiency | Box plot | CPU time / (elapsed x CPUs) per user |
| 12 | Node Utilization | Heatmap | Nodes x hours, color = job count |
| 13 | Failed Jobs | Stacked bar | Failed/timeout/cancelled counts by user |

### ID Extraction

Job names are parsed to extract sample IDs and process names:
- **Known patterns**: `P-XXXXXXX`, `C-XXXXXX`, `s_C_XXXXXX` (with suffixes)
- **Parenthesized content**: anything in `(...)` treated as sample ID
- **Process name**: remaining text after stripping IDs and Nextflow prefixes

## Project Structure

```
generate_dashboard.py       # CLI entry point
src/
  id_extractor.py           # Sample ID + process name parsing
  data_loader.py            # JSON loading + derived field computation
  aggregator.py             # Pre-aggregation for all charts
  renderer.py               # HTML/CSS template generation
  chart_js.py               # Plotly chart JavaScript
tests/                      # 45 pytest tests
```

## Tech Stack

- **Python 3.11+** (standard library only — no pandas/numpy)
- **Plotly.js** via CDN for interactive charts
- **pytest** for testing

## Development

```bash
uv sync
uv run pytest -v
```

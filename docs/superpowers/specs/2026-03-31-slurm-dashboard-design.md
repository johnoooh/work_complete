# CMOBIC CPU Queue Dashboard — Design Spec

## Overview

A self-contained HTML dashboard for monitoring SLURM job activity on the `cmobic_cpu` partition. A Python generator script reads daily JSON files and produces a single HTML file with all data and Plotly.js baked in. Designed for both cluster admins (queue health, resource waste) and individual users (personal job patterns, wait times).

## Architecture

### Components

1. **`generate_dashboard.py`** — Python script that:
   - Reads `job_<YYYY-MM-DD>.json` files from a configurable `--data-dir`
   - Always loads the most recent 7 days of data
   - Aggregates and pre-computes metrics (hourly bins, per-user stats, process groupings)
   - Outputs a single `dashboard.html` to `--output` path
   - Intended to run on a schedule (cron or similar)

2. **`dashboard.html`** — Self-contained output:
   - Plotly.js bundled via CDN link (loaded at open time)
   - All job data embedded as JSON in a `<script>` tag
   - No server required — just open in a browser
   - Dark theme, responsive layout

### CLI Interface

```
python generate_dashboard.py --data-dir /path/to/jsons --output /path/to/dashboard.html
```

No `--days` flag needed; always bakes 7 days. The 1-day/7-day toggle filters client-side.

## Data Model

### Input: `job_<YYYY-MM-DD>.json`

Each file is a JSON array of job records. Relevant fields (GPU fields ignored):

| Field | Type | Use |
|-------|------|-----|
| `job_id` | string | Unique identifier |
| `job_name` | string | Contains process type + sample ID |
| `user` | string | Submitting user |
| `state` | string | COMPLETED, FAILED, TIMEOUT, etc. |
| `req_cpus` | int | Requested CPU count |
| `alloc_cpus` | int | Allocated CPU count |
| `submit` | ISO datetime | When job was submitted |
| `start` | ISO datetime | When job started running |
| `end` | ISO datetime | When job finished |
| `elapsed` | HH:MM:SS | Wall time |
| `cpu_time_raw` | int | CPU-seconds consumed |
| `total_cpu` | string | Total CPU time (HH:MM:SS.ms) |
| `time_limit` | HH:MM:SS | Requested time limit |
| `max_rss_mb` | float | Peak memory usage (MB) |
| `req_mem_mb` | float | Requested memory (MB) |
| `alloc_mem_mb` | float | Allocated memory (MB) |
| `node_list` | string[] | Nodes used |
| `partition` | string | Always `cmobic_cpu` |

### Derived Fields (computed by generator)

| Derived | Formula |
|---------|---------|
| `wait_seconds` | `start - submit` (seconds) |
| `run_seconds` | `end - start` (seconds) |
| `cpu_efficiency` | `cpu_time_raw / (elapsed_seconds * alloc_cpus)` |
| `mem_efficiency` | `max_rss_mb / req_mem_mb` |
| `process_name` | Extracted from `job_name` by stripping sample IDs (see ID Extraction below). Example: `nf-NFCORE_KREWLYZER_KREWLYZER_FILTER_MAF_(P-0000001-T01-TEST)` → `FILTER_MAF`. |
| `sample_id` | Extracted sample/patient ID(s) from `job_name` (see ID Extraction below). Example: `P-0000001-T01-TEST`. May be null if no ID detected. |

### ID Extraction & Job Grouping

Job names vary widely. The generator extracts sample IDs and process names using this priority:

**Step 1 — Extract sample ID(s):**
1. **Known patient ID patterns**: `P-\w+`, `C-\w+`, `s_C_\w+` (including any trailing suffixes like `-T05-XS1`)
2. **Parenthesized content**: anything inside `(...)` is likely a sample identifier
3. **Heuristic**: remaining tokens that look like IDs — alphanumeric strings with dashes, 6+ characters, not all-uppercase dictionary words

If multiple IDs are found, keep all (a job may reference multiple samples). Store as `sample_id` (string or null).

**Step 2 — Derive process name:**
1. Remove all detected sample IDs from `job_name`
2. Remove common prefixes: `nf-`, repeated pipeline name segments (e.g., `NFCORE_KREWLYZER_KREWLYZER_` → keep only after the last repeated segment)
3. Clean up remaining underscores/separators
4. Fall back to the full `job_name` if nothing meaningful remains

**Examples:**
| job_name | sample_id | process_name |
|----------|-----------|--------------|
| `nf-NFCORE_KREWLYZER_KREWLYZER_FILTER_MAF_(P-0000001-T01-TEST)` | `P-0000001-T01-TEST` | `FILTER_MAF` |
| `alignment_C-003DS_hg38` | `C-003DS` | `alignment_hg38` |
| `s_C_00ABC_variant_call` | `s_C_00ABC` | `variant_call` |
| `my_custom_job` | null | `my_custom_job` |

## Dashboard Layout

Single scrollable page. Toggle at top switches between 1-day (most recent) and 7-day view. All charts re-render on toggle.

### Chart 1: Summary KPI Cards

Five cards in a row:
- **Total Jobs** — count of all jobs in time window
- **Active Users** — distinct user count
- **Median Wait** — median of `wait_seconds`, formatted human-readable
- **Memory Efficiency** — median of `mem_efficiency` across all jobs, as percentage
- **Failed Jobs** — count of jobs where `state != "COMPLETED"`

### Chart 2: Total Jobs Over Time (stacked area)

- X: hourly time bins
- Y: job count
- Stacked by user (one color per user)
- Plotly stacked area chart
- Shows overall queue load patterns

### Chart 3: Total Jobs by User (horizontal bar)

- One bar per user, sorted descending by job count
- Clicking a bar reveals Chart 5 (process breakdown) for that user
- Consistent user colors across all charts

### Chart 4: Job Submissions by User Over Time (line graph)

- X: hourly time bins
- Y: job count per user
- One line per user, clickable legend to show/hide
- Shows individual submission patterns (bursts vs. steady)

### Chart 5: User Drill-Down — Grouped Gantt (hidden by default)

- **Hidden until a user is clicked in Chart 3**
- Two tabs within the panel:
  - **By Process**: groups jobs by `process_name`. Each row: process name, gray bar (avg wait), colored bar (avg run), job count. Answers "how long does each step take?"
  - **By Sample**: groups jobs by `sample_id`. Each row: sample ID, bar showing total job count, avg total elapsed. Answers "how much work did each sample generate?"
- Hover tooltip: min, max, median for both wait and run
- Close button to dismiss
- Jobs with no detected sample ID grouped under "(no ID)"

### Chart 6: Memory Requested vs Used (scatter)

- X: `req_mem_mb`
- Y: `max_rss_mb`
- Diagonal reference line = perfect efficiency
- Color by user
- Points far below diagonal = wasted memory
- Hover: job name, user, exact values

### Chart 7: Overall Queue Wait Time (line + band)

- X: hourly time bins
- Y: wait time
- Solid line: hourly median wait
- Shaded band: p25–p75
- Shows congestion patterns over time

### Chart 8: Wait Time by User (box plot)

- One box per user
- Distribution of `wait_seconds`
- Shows who's consistently getting stuck vs. who gets quick starts

### Chart 9: Wait Time by User Over Time (line graph)

- X: hourly time bins
- Y: hourly average wait per user
- One line per user, clickable legend
- See who gets hit hardest during congestion

### Chart 10: CPU Efficiency by User (box plot)

- One box per user
- Distribution of `cpu_efficiency` (0–1 scale)
- Shows who's efficiently using CPU allocations

### Chart 11: Node Utilization Heatmap

- Rows: node names (from `node_list`)
- Columns: hourly time bins
- Color intensity: job count on that node in that hour
- Plotly heatmap

### Chart 12: Failed / Timed-Out Jobs by User (bar chart)

- Horizontal bar, one bar per user
- Stacked or grouped by state (FAILED, TIMEOUT, CANCELLED, etc.)
- Only shows users with non-COMPLETED jobs
- Quick view of who's having the most failures

## Interactivity

- **1-Day / 7-Day toggle**: top-right, filters all charts client-side. 1-day = most recent date in data.
- **User click (Chart 3 → Chart 5)**: clicking a user bar reveals their process breakdown. Click again or close button to dismiss.
- **Plotly built-in**: zoom, pan, hover tooltips, legend click to show/hide traces on all line/area charts.
- **Plotly built-in on Chart 12**: hover for exact counts per state.

## Styling

- Dark theme (dark background, light text)
- Consistent color palette for users across all charts
- Plotly dark template (`plotly_dark`)
- Responsive — works on standard desktop widths (1200px+)
- No mobile optimization needed

## Technology

- **Generator**: Python 3.11+, standard library only (json, datetime, pathlib, re). No pandas/numpy needed for this scale.
- **Charting**: Plotly.js loaded via CDN (`<script src="https://cdn.plot.ly/plotly-2.35.0.min.js">`)
- **Data embedding**: JSON blob in a `<script>` tag, pre-aggregated where possible to minimize client-side computation
- **No external JS dependencies** beyond Plotly

## Pre-aggregation Strategy

The generator pre-computes these aggregates to keep the HTML lightweight and fast:

1. **Hourly bins** — job counts, wait time stats (median, p25, p75, avg), per user and overall
2. **Per-user summaries** — total jobs, median wait, median CPU efficiency, median mem efficiency
3. **Per-process-per-user summaries** — avg/min/max/median wait and run times, job count
4. **Node-hour matrix** — job counts per node per hour
5. **Failed job counts** — per-user, per-state counts for non-COMPLETED jobs
6. **KPI values** — pre-computed summary numbers

Raw job-level data is only embedded for charts that need it (scatter plot in Chart 6).

## Out of Scope

- GPU metrics (no GPUs on cmobic_cpu)
- Job priority / QOS (not in the JSON)
- Real-time updates (static HTML, regenerated on schedule)
- Mobile layout
- Authentication / access control
- Individual job drill-down (trend-focused)

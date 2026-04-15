# Design: Dashboard HTML/Data Split

**Date:** 2026-04-15
**Status:** Approved

## Problem

The generated `work_complete_dashboard_latest.html` is 13MB for 7 days of data. Chrome struggles to load files this large. The root cause is that all aggregated job data is baked inline as a `DASHBOARD_DATA = {...}` JSON blob inside a `<script>` tag, making the file grow proportionally with history.

## Goal

- Reduce the HTML file to ~50KB (structure + JS only)
- Support 14 days of history without browser load issues
- Minimal changes: no new backend, no database, no new services

## Context

- The dashboard is served at `http://isvfpdev:8082/reports/work_complete_dashboard_latest.html`
- Port 8082 is a static file server (nginx) serving the `/reports/` directory
- The cron job runs daily at 8am on the HPC, writing to `/admin/cmobic_jobs/`
- The VM and HPC share the same filesystem

## Approach: Static JSON Split

Split the single HTML output into two files served from the same directory. The HTML shell fetches the JSON at load time via `fetch()`. Same-origin, no CORS issues.

## Output File Layout

```
/admin/cmobic_jobs/
  work_complete_MM_DD.html             ← thin shell (layout + JS, no data)
  work_complete_MM_DD.json             ← aggregated data payload
  work_complete_dashboard_latest.html  ← symlink → work_complete_MM_DD.html (unchanged)
  work_complete_data_latest.json       ← symlink → work_complete_MM_DD.json (new)
```

## Component Changes

### `generate_dashboard.py`

- Extend `days` from 7 to 14
- Accept an optional `--output-json` path argument; default is the `--output` path with `.json` extension
- Call `render_dashboard(data)` for the HTML shell
- Call a new `write_data(data)` function (or just `json.dumps`) for the JSON file
- Print both output paths on completion

### `src/renderer.py`

- Remove the inline `const DASHBOARD_DATA = {json_data};` from the HTML template
- Add a loading state (spinner or "Loading…" text) shown while fetch is in flight
- Add fetch bootstrap JS (~10 lines):
  ```js
  fetch('./work_complete_data_latest.json')
    .then(r => r.json())
    .then(data => { window.DASHBOARD_DATA = data; initCharts(); })
    .catch(() => { /* show error message */ });
  ```
- Wrap all chart initialization in an `initCharts()` function called after data loads (currently called immediately on script execution)

### `scripts/daily_dashboard.sh`

- Derive the JSON output path from the same datestamp as the HTML
- Write both files via `generate_dashboard.py --output ... --output-json ...`
- Add a second `ln -sf` for `work_complete_data_latest.json`

### `src/chart_js.py`

- No changes. Chart code already reads from `DASHBOARD_DATA` global; wrapping initialization in `initCharts()` is sufficient.

## Data Flow

```
cron (8am)
  → generate_dashboard.py --data-dir /admin/cmobic_jobs/completed/ --output ... --output-json ...
    → load_jobs(days=14)          # reads 14 × job_YYYY-MM-DD.json
    → aggregate(jobs)             # produces data dict
    → render_dashboard(data)      → work_complete_MM_DD.html  (shell, ~50KB)
    → json.dumps(data)            → work_complete_MM_DD.json  (data, ~1–2MB)
  → ln -sf MM_DD.html  → latest.html
  → ln -sf MM_DD.json  → latest.json

browser load
  → GET /reports/work_complete_dashboard_latest.html  (~50KB, instant)
  → GET /reports/work_complete_data_latest.json       (~1–2MB, async)
  → initCharts(DASHBOARD_DATA)
```

## Error Handling

- If the `fetch()` fails (stale symlink, file missing), show a visible error message in the dashboard body rather than a blank page.
- The loading state prevents rendering charts against undefined data.

## Testing

- Existing 106-test suite covers aggregation and rendering — no new test surface for the split itself.
- Manual verification: open the HTML shell, confirm loading state appears then charts render, confirm file size of HTML is <100KB.
- Confirm the JSON file is valid (parseable) after generation.

## Out of Scope

- No Django/backend changes
- No database
- No real-time data
- No pagination or lazy loading (single JSON fetch per load)

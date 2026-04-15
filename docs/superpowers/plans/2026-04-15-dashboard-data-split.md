# Dashboard HTML/Data Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the 13MB self-contained dashboard HTML into a thin shell (~50KB) + a separate JSON data file fetched at load time, and extend history from 7 to 14 days.

**Architecture:** The Python generator writes two files per run: an HTML shell (layout + JS, no data) and a `.json` data file. The HTML shell fetches `./work_complete_data_latest.json` at `DOMContentLoaded`, shows a loading state, then calls `initCharts()` once data arrives. The cron script symlinks both `_latest` files.

**Tech Stack:** Python 3.11, Plotly (browser), vanilla JS `fetch()`, nginx static file server, bash cron

---

## File Map

| File | Change |
|------|--------|
| `src/renderer.py` | Remove inline data blob; add `render_data_json()`; add fetch bootstrap + loading state to HTML template |
| `src/chart_js.py` | Replace `DOMContentLoaded` auto-init with exported `initCharts()` function called from fetch callback |
| `generate_dashboard.py` | Add `--output-json` arg; change `days=7` → `days=14`; write both files |
| `scripts/daily_dashboard.sh` | Pass `--output-json`; add second `ln -sf` for `_latest.json` |
| `tests/test_renderer.py` | Update tests asserting `DASHBOARD_DATA` in HTML; add tests for `render_data_json()` |
| `tests/test_end_to_end.py` | Update test asserting inline `DASHBOARD_DATA`; add end-to-end JSON output test |

---

## Task 1: Add `render_data_json()` and update renderer tests

The renderer currently embeds `json.dumps(data)` inline in the HTML. We'll extract that into a standalone function and update the tests that expect inline data.

**Files:**
- Modify: `src/renderer.py:119-287`
- Modify: `tests/test_renderer.py`

- [ ] **Step 1.1: Write failing tests for `render_data_json()`**

Add to `tests/test_renderer.py` (after the existing imports):

```python
from src.renderer import render_dashboard, render_data_json, _format_seconds
```

Add this new test class at the bottom of `tests/test_renderer.py`:

```python
class TestRenderDataJson:
    def test_returns_valid_json(self, sample_jobs):
        data = _make_data(sample_jobs)
        result = render_data_json(data)
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_contains_expected_keys(self, sample_jobs):
        data = _make_data(sample_jobs)
        parsed = json.loads(render_data_json(data))
        assert "users" in parsed
        assert "kpis" in parsed
        assert "all_dates" in parsed

    def test_roundtrip_preserves_users(self, sample_jobs):
        data = _make_data(sample_jobs)
        parsed = json.loads(render_data_json(data))
        assert parsed["users"] == data["users"]
```

- [ ] **Step 1.2: Run tests to verify they fail**

```bash
python -m pytest tests/test_renderer.py::TestRenderDataJson -v
```

Expected: `FAILED` — `ImportError: cannot import name 'render_data_json'`

- [ ] **Step 1.3: Add `render_data_json()` to `src/renderer.py`**

Add after the `render_dashboard` function (after line 287), before the end of the file:

```python
def render_data_json(data: dict) -> str:
    """Serialize aggregator output to a JSON string for the data file."""
    return json.dumps(data, default=str)
```

- [ ] **Step 1.4: Run new tests to verify they pass**

```bash
python -m pytest tests/test_renderer.py::TestRenderDataJson -v
```

Expected: 3 PASSED

- [ ] **Step 1.5: Commit**

```bash
git add src/renderer.py tests/test_renderer.py
git commit -m "feat: add render_data_json() for external data file"
```

---

## Task 2: Remove inline data from HTML shell, add fetch bootstrap

The HTML template currently has `const DASHBOARD_DATA = {json_data};` on line 283. We replace it with a `fetch()` call and a loading state. Several existing tests assert the old inline pattern — update them too.

**Files:**
- Modify: `src/renderer.py:119-287`
- Modify: `tests/test_renderer.py`
- Modify: `tests/test_end_to_end.py`

- [ ] **Step 2.1: Update existing tests that assert inline `DASHBOARD_DATA`**

In `tests/test_renderer.py`, find and replace the test that checks `"DASHBOARD_DATA" in html`:

```python
# BEFORE (around line 50):
def test_html_contains_data(self, sample_jobs):
    html = render_dashboard(_make_data(sample_jobs))
    assert "DASHBOARD_DATA" in html

# AFTER:
def test_html_contains_fetch_bootstrap(self, sample_jobs):
    html = render_dashboard(_make_data(sample_jobs))
    assert "work_complete_data_latest.json" in html
    assert "fetch(" in html
```

Also find and replace the test that regex-searches for `const DASHBOARD_DATA = ({.*?});`:

```python
# BEFORE (around line 82-84):
def test_data_is_valid_json(self, sample_jobs):
    html = render_dashboard(_make_data(sample_jobs))
    match = re.search(r"const DASHBOARD_DATA = ({.*?});\n", html, re.DOTALL)
    assert match, "DASHBOARD_DATA not found"
    ...

# AFTER (keep the test name, change the body):
def test_html_does_not_embed_data(self, sample_jobs):
    html = render_dashboard(_make_data(sample_jobs))
    assert "const DASHBOARD_DATA" not in html
```

In `tests/test_end_to_end.py`, find and replace `test_pipeline_html_has_valid_json_data`:

```python
# BEFORE (around line 56-61):
def test_pipeline_html_has_valid_json_data(self):
    ...
    match = re.search(r"const DASHBOARD_DATA = ({.*?});\n", html, re.DOTALL)
    assert match, "DASHBOARD_DATA not found in HTML"

# AFTER:
def test_pipeline_html_has_fetch_bootstrap(self):
    jobs = [enrich_job(make_job()) for _ in range(3)]
    data = aggregate(jobs)
    html = render_dashboard(data)
    assert "fetch(" in html
    assert "work_complete_data_latest.json" in html
    assert "const DASHBOARD_DATA" not in html
```

- [ ] **Step 2.2: Run the full test suite to confirm what currently passes**

```bash
python -m pytest tests/ -v --tb=short 2>&1 | tail -20
```

Note the current pass count.

- [ ] **Step 2.3: Replace the `<script>` block in `src/renderer.py`**

Find this block near line 282 in `src/renderer.py`:

```python
<script>
const DASHBOARD_DATA = {json_data};
{chart_js}
</script>
```

Replace with:

```python
<script>
{chart_js}

(function () {{
  var overlay = document.getElementById('loading-overlay');
  fetch('./work_complete_data_latest.json')
    .then(function (r) {{
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    }})
    .then(function (data) {{
      window.DASHBOARD_DATA = data;
      if (overlay) overlay.remove();
      initCharts(data);
    }})
    .catch(function (err) {{
      if (overlay) overlay.innerHTML = '<p style="color:#f85149;padding:2rem;">Failed to load dashboard data: ' + err.message + '</p>';
    }});
}})();
</script>
```

Also in `render_dashboard()`, remove the line:
```python
json_data = json.dumps(data, default=str)
```

And remove `json_data` from the f-string (it's no longer used in the template).

Add a loading overlay `<div>` just after `<div class="dashboard">` in the template:

```html
<div id="loading-overlay" style="position:fixed;inset:0;background:#0d1117;display:flex;align-items:center;justify-content:center;z-index:9999;font-size:1.1rem;color:#8b949e;">Loading dashboard data…</div>
```

- [ ] **Step 2.4: Run the full test suite**

```bash
python -m pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: same pass count as Step 2.2 (updated tests pass, nothing regresses).

- [ ] **Step 2.5: Commit**

```bash
git add src/renderer.py tests/test_renderer.py tests/test_end_to_end.py
git commit -m "feat: remove inline data blob from HTML shell, add fetch bootstrap"
```

---

## Task 3: Replace auto-init with `initCharts()` in chart JS

Currently `src/chart_js.py`'s `_main_js()` fires inside a `DOMContentLoaded` listener, so charts render immediately — before the `fetch()` resolves. We need to export `initCharts(data)` as a named function that the fetch callback can call.

**Files:**
- Modify: `src/chart_js.py:800-823`
- Modify: `tests/test_chart_js.py`

- [ ] **Step 3.1: Check what `test_chart_js.py` asserts about the init block**

```bash
grep -n "DOMContentLoaded\|initCharts\|renderAllCharts\|updateKPIs" tests/test_chart_js.py
```

Note which assertions reference the auto-init pattern.

- [ ] **Step 3.2: Update chart JS tests to expect `initCharts`**

Find any test in `tests/test_chart_js.py` that asserts `"DOMContentLoaded"` is in the JS output and change it to assert `"function initCharts"` instead:

```python
# BEFORE:
assert "DOMContentLoaded" in js

# AFTER:
assert "function initCharts" in js
```

- [ ] **Step 3.3: Run chart JS tests to confirm they fail**

```bash
python -m pytest tests/test_chart_js.py -v --tb=short
```

Expected: failures on the `initCharts` assertions.

- [ ] **Step 3.4: Replace the `DOMContentLoaded` block in `src/chart_js.py`**

Find the `_main_js()` function near line 802. Replace the entire `document.addEventListener('DOMContentLoaded', ...)` block with:

```python
def _main_js() -> str:
    return """
function initCharts(data) {
  window.DASHBOARD_DATA = data;

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
```

Note: `DATA` in the rest of the JS is `const DATA = DASHBOARD_DATA` defined in `_base_js()`. After the fetch, `window.DASHBOARD_DATA` is set before `initCharts(data)` is called, so `DATA` will resolve correctly. No change needed to `_base_js()`.

- [ ] **Step 3.5: Run the full test suite**

```bash
python -m pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: all previously passing tests still pass, chart JS tests now pass.

- [ ] **Step 3.6: Commit**

```bash
git add src/chart_js.py tests/test_chart_js.py
git commit -m "feat: replace DOMContentLoaded auto-init with initCharts(data) function"
```

---

## Task 4: Update `generate_dashboard.py` to write both files and extend history

**Files:**
- Modify: `generate_dashboard.py`

- [ ] **Step 4.1: Write a failing end-to-end test for dual-file output**

Add to `tests/test_end_to_end.py`:

```python
import tempfile
from pathlib import Path

class TestDualFileOutput:
    def test_generate_dashboard_writes_json_file(self):
        """generate_dashboard main() writes both .html and .json when --output-json given."""
        import subprocess, sys
        jobs_dir = Path("tests/fixtures")
        with tempfile.TemporaryDirectory() as tmpdir:
            out_html = Path(tmpdir) / "dashboard.html"
            out_json = Path(tmpdir) / "dashboard.json"
            result = subprocess.run(
                [sys.executable, "generate_dashboard.py",
                 "--data-dir", str(jobs_dir),
                 "--output", str(out_html),
                 "--output-json", str(out_json)],
                capture_output=True, text=True
            )
            assert result.returncode == 0, result.stderr
            assert out_html.exists()
            assert out_json.exists()
            parsed = json.loads(out_json.read_text())
            assert "users" in parsed

    def test_generate_dashboard_json_defaults_to_html_path(self):
        """Without --output-json, json file is written next to html with .json extension."""
        import subprocess, sys
        jobs_dir = Path("tests/fixtures")
        with tempfile.TemporaryDirectory() as tmpdir:
            out_html = Path(tmpdir) / "dashboard.html"
            result = subprocess.run(
                [sys.executable, "generate_dashboard.py",
                 "--data-dir", str(jobs_dir),
                 "--output", str(out_html)],
                capture_output=True, text=True
            )
            assert result.returncode == 0, result.stderr
            out_json = Path(tmpdir) / "dashboard.json"
            assert out_json.exists()
```

- [ ] **Step 4.2: Run to confirm failure**

```bash
python -m pytest tests/test_end_to_end.py::TestDualFileOutput -v
```

Expected: FAILED — `generate_dashboard.py` does not write a JSON file.

- [ ] **Step 4.3: Update `generate_dashboard.py`**

Replace the full contents of `generate_dashboard.py` with:

```python
"""CLI entry point: generate the CMOBIC CPU Queue Dashboard."""

import argparse
from pathlib import Path

from src.aggregator import aggregate
from src.data_loader import load_jobs
from src.renderer import render_dashboard, render_data_json


def main():
    parser = argparse.ArgumentParser(description="Generate CMOBIC CPU Queue Dashboard")
    parser.add_argument("--data-dir", type=Path, required=True,
        help="Directory containing job_YYYY-MM-DD.json files")
    parser.add_argument("--output", type=Path, default=Path("dashboard.html"),
        help="Output HTML file path (default: dashboard.html)")
    parser.add_argument("--output-json", type=Path, default=None,
        help="Output JSON data file path (default: same as --output with .json extension)")
    args = parser.parse_args()

    if not args.data_dir.is_dir():
        parser.error(f"Data directory not found: {args.data_dir}")

    json_out = args.output_json if args.output_json else args.output.with_suffix(".json")

    jobs = load_jobs(args.data_dir, days=14)
    if not jobs:
        print(f"Warning: No job data found in {args.data_dir} for the last 14 days")

    data = aggregate(jobs) if jobs else aggregate([])
    html = render_dashboard(data)
    json_str = render_data_json(data)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    json_out.parent.mkdir(parents=True, exist_ok=True)

    args.output.write_text(html)
    json_out.write_text(json_str)

    print(f"Dashboard: {args.output} ({len(jobs)} jobs from {len(data.get('all_dates', []))} days)")
    print(f"Data:      {json_out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4.4: Run the new tests**

```bash
python -m pytest tests/test_end_to_end.py::TestDualFileOutput -v
```

Expected: 2 PASSED

- [ ] **Step 4.5: Run the full test suite**

```bash
python -m pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: all tests pass.

- [ ] **Step 4.6: Commit**

```bash
git add generate_dashboard.py tests/test_end_to_end.py
git commit -m "feat: write separate JSON data file and extend history to 14 days"
```

---

## Task 5: Update the cron shell script

**Files:**
- Modify: `scripts/daily_dashboard.sh`

No new tests — shell script behavior is covered by the end-to-end test in Task 4.

- [ ] **Step 5.1: Update `scripts/daily_dashboard.sh`**

Replace the relevant section (around lines 31-41) with:

```bash
DATE_STAMP=$(date +"%m_%d")
FILENAME="work_complete_${DATE_STAMP}.html"
JSON_FILENAME="work_complete_${DATE_STAMP}.json"
OUTPUT_PATH="${OUTPUT_DIR%/}/${FILENAME}"
JSON_PATH="${OUTPUT_DIR%/}/${JSON_FILENAME}"
LATEST_LINK="${OUTPUT_DIR%/}/work_complete_dashboard_latest.html"
LATEST_JSON_LINK="${OUTPUT_DIR%/}/work_complete_data_latest.json"

cd "$PROJECT_DIR"
python generate_dashboard.py --data-dir "$DATA_DIR" --output "$OUTPUT_PATH" --output-json "$JSON_PATH"
ln -sf "$OUTPUT_PATH" "$LATEST_LINK"
ln -sf "$JSON_PATH" "$LATEST_JSON_LINK"

echo "Dashboard: $OUTPUT_PATH"
echo "Data:      $JSON_PATH"
echo "Latest:    $LATEST_LINK -> $FILENAME"
echo "Latest:    $LATEST_JSON_LINK -> $JSON_FILENAME"
```

- [ ] **Step 5.2: Run the full test suite one final time**

```bash
python -m pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: all tests pass.

- [ ] **Step 5.3: Smoke test the script locally**

```bash
bash scripts/daily_dashboard.sh --data-dir /admin/cmobic_jobs/completed/ --output-dir /tmp/dashboard_test/
ls -lh /tmp/dashboard_test/
```

Expected: two dated files + two symlinks. HTML should be <200KB. JSON should be 1-3MB.

- [ ] **Step 5.4: Commit**

```bash
git add scripts/daily_dashboard.sh
git commit -m "feat: write JSON data symlink in daily dashboard cron script"
```

---

## Verification Checklist

After all tasks are complete:

- [ ] `python -m pytest tests/ -v` — all tests pass
- [ ] Generated HTML is < 200KB (run `ls -lh dashboard.html` after a local generate)
- [ ] Generated JSON is valid (`python -c "import json; json.load(open('dashboard.json'))"`)
- [ ] Open `dashboard.html` in Chrome — loading overlay appears briefly, then charts render
- [ ] Opening `dashboard.html` directly from disk (`file://`) will fail because `fetch()` is blocked by browsers for local files — this is expected. It must be served over HTTP.

# CMOBIC CPU Queue Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python generator that reads SLURM job JSON files and produces a self-contained HTML dashboard with Plotly.js charts for monitoring the cmobic_cpu queue.

**Architecture:** A Python CLI script reads `job_YYYY-MM-DD.json` files, computes derived fields (wait time, CPU/memory efficiency, process names), pre-aggregates into hourly bins and per-user stats, then injects the data as JSON into an HTML template with client-side Plotly.js charting. The 1-day/7-day toggle filters client-side. Clicking a user in the bar chart reveals a drill-down panel.

**Tech Stack:** Python 3.11+ (standard library only for runtime), Plotly.js via CDN, pytest for testing, uv for project management.

---

## File Structure

```
work_complete/
├── generate_dashboard.py              # CLI entry point (argparse, orchestration)
├── src/
│   ├── __init__.py
│   ├── id_extractor.py                # Sample ID + process name extraction from job names
│   ├── data_loader.py                 # Read JSON files, compute derived fields per job
│   ├── aggregator.py                  # Pre-aggregate: hourly bins, user stats, node matrix
│   ├── renderer.py                    # Assemble HTML: skeleton, CSS, data injection
│   └── chart_js.py                    # JavaScript source for all Plotly charts + interactions
├── tests/
│   ├── __init__.py
│   ├── conftest.py                    # Shared fixtures (sample job records)
│   ├── test_id_extractor.py           # ID extraction edge cases
│   ├── test_data_loader.py            # File reading, derived field computation
│   ├── test_aggregator.py             # Aggregation correctness
│   └── test_renderer.py              # HTML output smoke tests
├── pyproject.toml
└── docs/superpowers/specs/2026-03-31-slurm-dashboard-design.md
```

**Responsibilities:**
- `id_extractor.py` — pure functions: `extract_sample_id(job_name) -> str|None` and `extract_process_name(job_name) -> str`. No I/O.
- `data_loader.py` — reads JSON files from a directory, calls id_extractor, computes `wait_seconds`, `run_seconds`, `cpu_efficiency`, `mem_efficiency`. Returns list of enriched job dicts.
- `aggregator.py` — takes enriched jobs, produces all pre-aggregated data structures needed by the dashboard (hourly bins, user summaries, per-process-per-user, node-hour matrix, KPIs). Separate functions for 1-day and 7-day aggregation, or one function parameterized by date filter.
- `renderer.py` — takes aggregated data dict + raw scatter data, produces complete HTML string. Delegates JS chart code to `chart_js.py`.
- `chart_js.py` — returns JavaScript source code as a Python string. Contains all Plotly.newPlot calls, toggle logic, click-to-drill-down interaction.
- `generate_dashboard.py` — CLI: parses args, calls data_loader → aggregator → renderer, writes HTML file.

---

### Task 1: Project Setup + Test Fixtures

**Files:**
- Create: `pyproject.toml`
- Create: `src/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Initialize project with uv**

Run:
```bash
cd /Users/orgeraj/CCS_projects/work_complete
uv init --no-readme
```

- [ ] **Step 2: Configure pyproject.toml**

Replace the generated `pyproject.toml` with:

```toml
[project]
name = "cmobic-dashboard"
version = "0.1.0"
description = "SLURM job dashboard generator for cmobic_cpu queue"
requires-python = ">=3.11"

[dependency-groups]
dev = ["pytest>=8.0"]

[project.scripts]
generate-dashboard = "generate_dashboard:main"
```

- [ ] **Step 3: Create src package**

```python
# src/__init__.py
```

Empty file.

- [ ] **Step 4: Create test fixtures in conftest.py**

```python
# tests/__init__.py
```

```python
# tests/conftest.py
import pytest


@pytest.fixture
def sample_jobs():
    """Minimal set of job records covering key scenarios."""
    return [
        {
            "job_id": "100",
            "job_name": "nf-NFCORE_KREWLYZER_KREWLYZER_FILTER_MAF_(P-0000001-T01-TEST)",
            "user": "user_a",
            "account": "user_a",
            "partition": "cmobic_cpu",
            "state": "COMPLETED",
            "req_cpus": 2,
            "alloc_cpus": 2,
            "submit": "2026-03-30T10:00:00",
            "start": "2026-03-30T10:05:00",
            "end": "2026-03-30T10:05:03",
            "elapsed": "00:00:03",
            "cpu_time_raw": 6,
            "total_cpu": "00:02.223",
            "time_limit": "02:00:00",
            "max_rss_mb": 17.96,
            "req_mem_mb": 12288.0,
            "alloc_mem_mb": 12288.0,
            "node_list": ["node001"],
            "base_job_id": "100",
            "max_gpu_util": None,
            "state_by_jobid": None,
            "req_gpu_type": None,
            "req_gpus": None,
            "alloc_gpu_type": None,
            "alloc_gpus": None,
        },
        {
            "job_id": "101",
            "job_name": "nf-NFCORE_KREWLYZER_KREWLYZER_ANNOTATE_VCF_(P-0000001-T01-TEST)",
            "user": "user_a",
            "account": "user_a",
            "partition": "cmobic_cpu",
            "state": "COMPLETED",
            "req_cpus": 4,
            "alloc_cpus": 4,
            "submit": "2026-03-30T10:10:00",
            "start": "2026-03-30T10:12:00",
            "end": "2026-03-30T10:34:00",
            "elapsed": "00:22:00",
            "cpu_time_raw": 4800,
            "total_cpu": "01:20:00.000",
            "time_limit": "04:00:00",
            "max_rss_mb": 2048.0,
            "req_mem_mb": 8192.0,
            "alloc_mem_mb": 8192.0,
            "node_list": ["node002"],
            "base_job_id": "101",
            "max_gpu_util": None,
            "state_by_jobid": None,
            "req_gpu_type": None,
            "req_gpus": None,
            "alloc_gpu_type": None,
            "alloc_gpus": None,
        },
        {
            "job_id": "102",
            "job_name": "alignment_C-003DS_hg38",
            "user": "user_b",
            "account": "user_b",
            "partition": "cmobic_cpu",
            "state": "COMPLETED",
            "req_cpus": 8,
            "alloc_cpus": 8,
            "submit": "2026-03-30T11:00:00",
            "start": "2026-03-30T11:00:30",
            "end": "2026-03-30T11:45:30",
            "elapsed": "00:45:00",
            "cpu_time_raw": 19200,
            "total_cpu": "05:20:00.000",
            "time_limit": "08:00:00",
            "max_rss_mb": 6000.0,
            "req_mem_mb": 16384.0,
            "alloc_mem_mb": 16384.0,
            "node_list": ["node001"],
            "base_job_id": "102",
            "max_gpu_util": None,
            "state_by_jobid": None,
            "req_gpu_type": None,
            "req_gpus": None,
            "alloc_gpu_type": None,
            "alloc_gpus": None,
        },
        {
            "job_id": "103",
            "job_name": "s_C_00ABC_variant_call",
            "user": "user_b",
            "account": "user_b",
            "partition": "cmobic_cpu",
            "state": "FAILED",
            "req_cpus": 4,
            "alloc_cpus": 4,
            "submit": "2026-03-30T12:00:00",
            "start": "2026-03-30T12:10:00",
            "end": "2026-03-30T12:15:00",
            "elapsed": "00:05:00",
            "cpu_time_raw": 100,
            "total_cpu": "00:01:40.000",
            "time_limit": "02:00:00",
            "max_rss_mb": 500.0,
            "req_mem_mb": 8192.0,
            "alloc_mem_mb": 8192.0,
            "node_list": ["node002"],
            "base_job_id": "103",
            "max_gpu_util": None,
            "state_by_jobid": None,
            "req_gpu_type": None,
            "req_gpus": None,
            "alloc_gpu_type": None,
            "alloc_gpus": None,
        },
        {
            "job_id": "104",
            "job_name": "my_custom_job",
            "user": "user_c",
            "account": "user_c",
            "partition": "cmobic_cpu",
            "state": "TIMEOUT",
            "req_cpus": 2,
            "alloc_cpus": 2,
            "submit": "2026-03-30T14:00:00",
            "start": "2026-03-30T14:30:00",
            "end": "2026-03-30T16:30:00",
            "elapsed": "02:00:00",
            "cpu_time_raw": 7200,
            "total_cpu": "02:00:00.000",
            "time_limit": "02:00:00",
            "max_rss_mb": 4000.0,
            "req_mem_mb": 4096.0,
            "alloc_mem_mb": 4096.0,
            "node_list": ["node003"],
            "base_job_id": "104",
            "max_gpu_util": None,
            "state_by_jobid": None,
            "req_gpu_type": None,
            "req_gpus": None,
            "alloc_gpu_type": None,
            "alloc_gpus": None,
        },
    ]


@pytest.fixture
def sample_jobs_json(tmp_path, sample_jobs):
    """Write sample jobs to a JSON file and return the directory."""
    import json

    filepath = tmp_path / "job_2026-03-30.json"
    filepath.write_text(json.dumps(sample_jobs))
    return tmp_path
```

- [ ] **Step 5: Install dev dependencies and verify**

Run:
```bash
uv sync
uv run pytest --co -q
```
Expected: `no tests ran` (no test files with tests yet), exit 0.

- [ ] **Step 6: Commit**

```bash
git init
git add pyproject.toml src/__init__.py tests/__init__.py tests/conftest.py uv.lock .python-version
git commit -m "chore: project setup with test fixtures"
```

---

### Task 2: ID Extractor

**Files:**
- Create: `src/id_extractor.py`
- Create: `tests/test_id_extractor.py`

- [ ] **Step 1: Write failing tests for ID extraction**

```python
# tests/test_id_extractor.py
from src.id_extractor import extract_sample_id, extract_process_name


class TestExtractSampleId:
    def test_p_id_in_parentheses(self):
        name = "nf-NFCORE_KREWLYZER_KREWLYZER_FILTER_MAF_(P-0000001-T01-TEST)"
        assert extract_sample_id(name) == "P-0000001-T01-TEST"

    def test_c_id_embedded(self):
        name = "alignment_C-003DS_hg38"
        assert extract_sample_id(name) == "C-003DS"

    def test_s_c_id_prefix(self):
        name = "s_C_00ABC_variant_call"
        assert extract_sample_id(name) == "s_C_00ABC"

    def test_no_id(self):
        name = "my_custom_job"
        assert extract_sample_id(name) is None

    def test_p_id_no_parentheses(self):
        name = "filter_P-0000002_step2"
        assert extract_sample_id(name) == "P-0000002"

    def test_p_id_with_long_suffix(self):
        name = "nf-PIPELINE_STEP_(P-0000001-T01-TEST-IGO-12345)"
        assert extract_sample_id(name) == "P-0000001-T01-TEST-IGO-12345"

    def test_parenthesized_content_as_id(self):
        name = "some_job_(SAMPLE123-A)"
        assert extract_sample_id(name) == "SAMPLE123-A"


class TestExtractProcessName:
    def test_nextflow_full_name(self):
        name = "nf-NFCORE_KREWLYZER_KREWLYZER_FILTER_MAF_(P-0000001-T01-TEST)"
        assert extract_process_name(name) == "FILTER_MAF"

    def test_c_id_embedded(self):
        name = "alignment_C-003DS_hg38"
        assert extract_process_name(name) == "alignment_hg38"

    def test_s_c_id_prefix(self):
        name = "s_C_00ABC_variant_call"
        assert extract_process_name(name) == "variant_call"

    def test_no_id_passthrough(self):
        name = "my_custom_job"
        assert extract_process_name(name) == "my_custom_job"

    def test_nextflow_different_pipeline(self):
        name = "nf-NFCORE_SAREK_SAREK_MARKDUP_(P-0000002-T01)"
        assert extract_process_name(name) == "MARKDUP"

    def test_cleanup_dangling_separators(self):
        name = "step__C-003DS__final"
        assert extract_process_name(name) == "step_final"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_id_extractor.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.id_extractor'`

- [ ] **Step 3: Implement id_extractor.py**

```python
# src/id_extractor.py
"""Extract sample IDs and process names from SLURM job names."""

import re

# Known patient/sample ID patterns (order matters — check specific first)
_KNOWN_ID_PATTERNS = [
    re.compile(r"s_C_\w+"),       # s_C_ prefixed IDs
    re.compile(r"P-\w+"),         # DMP IDs: P-XXXXXXX with possible suffixes
    re.compile(r"C-\w+"),         # C- prefixed IDs
]

# Parenthesized content (likely a sample identifier)
_PAREN_PATTERN = re.compile(r"\(([^)]+)\)")

# Nextflow pipeline prefix: nf-NFCORE_PIPELINE_PIPELINE_
_NF_PREFIX = re.compile(r"^nf-(?:[A-Z0-9]+_)*?([A-Z0-9]+)_\1_")


def extract_sample_id(job_name: str) -> str | None:
    """Extract the sample/patient ID from a job name.

    Returns the first matched ID, or None if no ID pattern is found.
    Priority: known ID patterns > parenthesized content.
    """
    # Check parenthesized content first (most specific context)
    paren_match = _PAREN_PATTERN.search(job_name)
    if paren_match:
        content = paren_match.group(1)
        # Check if it contains a known ID pattern
        for pattern in _KNOWN_ID_PATTERNS:
            m = pattern.search(content)
            if m:
                return m.group(0)
        # If parenthesized content looks like an ID (has alphanumeric + dashes, 6+ chars)
        if len(content) >= 6 and re.search(r"[A-Z0-9]", content):
            return content

    # Check for known ID patterns anywhere in the name
    for pattern in _KNOWN_ID_PATTERNS:
        m = pattern.search(job_name)
        if m:
            return m.group(0)

    return None


def extract_process_name(job_name: str) -> str:
    """Extract the process/step name from a job name.

    Strips sample IDs and common prefixes (nf-, pipeline name repetitions).
    Falls back to the full job_name if nothing meaningful remains.
    """
    name = job_name

    # Remove parenthesized content (sample IDs)
    name = _PAREN_PATTERN.sub("", name)

    # Remove Nextflow prefix: nf-NFCORE_PIPELINE_PIPELINE_ → keep what follows
    nf_match = _NF_PREFIX.match(name)
    if nf_match:
        name = name[nf_match.end():]
    elif name.startswith("nf-"):
        name = name[3:]

    # Remove known ID patterns from remaining string
    for pattern in _KNOWN_ID_PATTERNS:
        name = pattern.sub("", name)

    # Clean up: collapse multiple underscores, strip leading/trailing separators
    name = re.sub(r"[_\-]{2,}", "_", name)
    name = name.strip("_- ")

    return name if name else job_name
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_id_extractor.py -v`
Expected: All 13 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/id_extractor.py tests/test_id_extractor.py
git commit -m "feat: add ID extractor for sample IDs and process names"
```

---

### Task 3: Data Loader

**Files:**
- Create: `src/data_loader.py`
- Create: `tests/test_data_loader.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_data_loader.py
from src.data_loader import load_jobs, enrich_job


class TestEnrichJob:
    def test_wait_seconds(self, sample_jobs):
        job = enrich_job(sample_jobs[0])
        # submit 10:00:00, start 10:05:00 → 300s
        assert job["wait_seconds"] == 300

    def test_run_seconds(self, sample_jobs):
        job = enrich_job(sample_jobs[0])
        # start 10:05:00, end 10:05:03 → 3s
        assert job["run_seconds"] == 3

    def test_cpu_efficiency(self, sample_jobs):
        job = enrich_job(sample_jobs[0])
        # cpu_time_raw=6, elapsed=3s, alloc_cpus=2 → 6/(3*2) = 1.0
        assert job["cpu_efficiency"] == 1.0

    def test_mem_efficiency(self, sample_jobs):
        job = enrich_job(sample_jobs[0])
        # max_rss=17.96, req_mem=12288 → 17.96/12288 ≈ 0.00146
        assert abs(job["mem_efficiency"] - 17.96 / 12288.0) < 0.0001

    def test_process_name_extracted(self, sample_jobs):
        job = enrich_job(sample_jobs[0])
        assert job["process_name"] == "FILTER_MAF"

    def test_sample_id_extracted(self, sample_jobs):
        job = enrich_job(sample_jobs[0])
        assert job["sample_id"] == "P-0000001-T01-TEST"

    def test_no_sample_id(self, sample_jobs):
        job = enrich_job(sample_jobs[4])  # my_custom_job
        assert job["sample_id"] is None

    def test_cpu_efficiency_zero_elapsed(self):
        """Jobs with 0 elapsed should have 0 CPU efficiency, not divide-by-zero."""
        job = {
            "job_name": "quick_job",
            "submit": "2026-03-30T10:00:00",
            "start": "2026-03-30T10:00:00",
            "end": "2026-03-30T10:00:00",
            "elapsed": "00:00:00",
            "cpu_time_raw": 0,
            "alloc_cpus": 2,
            "max_rss_mb": 0,
            "req_mem_mb": 100.0,
        }
        enriched = enrich_job(job)
        assert enriched["cpu_efficiency"] == 0.0

    def test_mem_efficiency_zero_requested(self):
        """Jobs with 0 req_mem should have 0 mem efficiency."""
        job = {
            "job_name": "no_mem_job",
            "submit": "2026-03-30T10:00:00",
            "start": "2026-03-30T10:00:00",
            "end": "2026-03-30T10:00:01",
            "elapsed": "00:00:01",
            "cpu_time_raw": 1,
            "alloc_cpus": 1,
            "max_rss_mb": 50.0,
            "req_mem_mb": 0.0,
        }
        enriched = enrich_job(job)
        assert enriched["mem_efficiency"] == 0.0


class TestLoadJobs:
    def test_loads_all_jobs(self, sample_jobs_json):
        jobs = load_jobs(sample_jobs_json, days=7)
        assert len(jobs) == 5

    def test_jobs_are_enriched(self, sample_jobs_json):
        jobs = load_jobs(sample_jobs_json, days=7)
        assert "wait_seconds" in jobs[0]
        assert "process_name" in jobs[0]

    def test_empty_directory(self, tmp_path):
        jobs = load_jobs(tmp_path, days=7)
        assert jobs == []

    def test_filters_to_recent_days(self, tmp_path):
        """Only loads files within the requested day range."""
        import json

        # File from 30 days ago — should be excluded
        old_job = [{
            "job_id": "999",
            "job_name": "old_job",
            "user": "old_user",
            "state": "COMPLETED",
            "submit": "2026-02-28T10:00:00",
            "start": "2026-02-28T10:01:00",
            "end": "2026-02-28T10:02:00",
            "elapsed": "00:01:00",
            "cpu_time_raw": 60,
            "alloc_cpus": 1,
            "max_rss_mb": 100.0,
            "req_mem_mb": 1000.0,
            "partition": "cmobic_cpu",
            "req_cpus": 1,
            "alloc_mem_mb": 1000.0,
            "node_list": ["node001"],
            "time_limit": "01:00:00",
            "total_cpu": "00:01:00.000",
            "base_job_id": "999",
            "max_gpu_util": None,
            "state_by_jobid": None,
            "req_gpu_type": None,
            "req_gpus": None,
            "alloc_gpu_type": None,
            "alloc_gpus": None,
        }]
        (tmp_path / "job_2026-02-28.json").write_text(json.dumps(old_job))

        # File from today — should be included
        new_job = [{
            "job_id": "1000",
            "job_name": "new_job",
            "user": "new_user",
            "state": "COMPLETED",
            "submit": "2026-03-30T10:00:00",
            "start": "2026-03-30T10:01:00",
            "end": "2026-03-30T10:02:00",
            "elapsed": "00:01:00",
            "cpu_time_raw": 60,
            "alloc_cpus": 1,
            "max_rss_mb": 100.0,
            "req_mem_mb": 1000.0,
            "partition": "cmobic_cpu",
            "req_cpus": 1,
            "alloc_mem_mb": 1000.0,
            "node_list": ["node001"],
            "time_limit": "01:00:00",
            "total_cpu": "00:01:00.000",
            "base_job_id": "1000",
            "max_gpu_util": None,
            "state_by_jobid": None,
            "req_gpu_type": None,
            "req_gpus": None,
            "alloc_gpu_type": None,
            "alloc_gpus": None,
        }]
        (tmp_path / "job_2026-03-30.json").write_text(json.dumps(new_job))

        jobs = load_jobs(tmp_path, days=7)
        assert len(jobs) == 1
        assert jobs[0]["job_id"] == "1000"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_data_loader.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement data_loader.py**

```python
# src/data_loader.py
"""Load SLURM job JSON files and compute derived fields."""

import json
from datetime import datetime, timedelta
from pathlib import Path

from src.id_extractor import extract_process_name, extract_sample_id

_DATE_FMT = "%Y-%m-%dT%H:%M:%S"
_FILE_DATE_FMT = "%Y-%m-%d"


def _parse_dt(s: str) -> datetime:
    return datetime.strptime(s, _DATE_FMT)


def _elapsed_to_seconds(elapsed: str) -> int:
    """Convert HH:MM:SS to total seconds."""
    parts = elapsed.split(":")
    return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])


def enrich_job(job: dict) -> dict:
    """Add derived fields to a job record. Returns a new dict."""
    enriched = dict(job)

    submit_dt = _parse_dt(job["submit"])
    start_dt = _parse_dt(job["start"])
    end_dt = _parse_dt(job["end"])

    enriched["submit_dt"] = submit_dt.isoformat()
    enriched["start_dt"] = start_dt.isoformat()
    enriched["end_dt"] = end_dt.isoformat()
    enriched["wait_seconds"] = int((start_dt - submit_dt).total_seconds())
    enriched["run_seconds"] = int((end_dt - start_dt).total_seconds())

    elapsed_s = _elapsed_to_seconds(job["elapsed"])
    alloc_cpus = job.get("alloc_cpus", 1) or 1

    if elapsed_s > 0 and alloc_cpus > 0:
        enriched["cpu_efficiency"] = job["cpu_time_raw"] / (elapsed_s * alloc_cpus)
    else:
        enriched["cpu_efficiency"] = 0.0

    req_mem = job.get("req_mem_mb", 0) or 0
    max_rss = job.get("max_rss_mb", 0) or 0
    enriched["mem_efficiency"] = max_rss / req_mem if req_mem > 0 else 0.0

    enriched["process_name"] = extract_process_name(job["job_name"])
    enriched["sample_id"] = extract_sample_id(job["job_name"])

    return enriched


def load_jobs(data_dir: Path, days: int = 7) -> list[dict]:
    """Load and enrich job records from JSON files within the date range.

    Reads files matching job_YYYY-MM-DD.json from data_dir.
    Only includes files from the most recent `days` days.
    """
    data_dir = Path(data_dir)
    cutoff = datetime.now() - timedelta(days=days)
    jobs = []

    for filepath in sorted(data_dir.glob("job_*.json")):
        # Extract date from filename
        stem = filepath.stem  # e.g., "job_2026-03-30"
        try:
            file_date = datetime.strptime(stem.replace("job_", ""), _FILE_DATE_FMT)
        except ValueError:
            continue

        if file_date < cutoff:
            continue

        with open(filepath) as f:
            raw_jobs = json.load(f)

        for raw_job in raw_jobs:
            jobs.append(enrich_job(raw_job))

    return jobs
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_data_loader.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/data_loader.py tests/test_data_loader.py
git commit -m "feat: add data loader with derived field computation"
```

---

### Task 4: Aggregator

**Files:**
- Create: `src/aggregator.py`
- Create: `tests/test_aggregator.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_aggregator.py
from src.aggregator import aggregate
from src.data_loader import enrich_job


def _enrich_all(jobs):
    return [enrich_job(j) for j in jobs]


class TestAggregate:
    def test_kpis(self, sample_jobs):
        data = aggregate(_enrich_all(sample_jobs))
        kpis = data["kpis"]
        assert kpis["total_jobs"] == 5
        assert kpis["active_users"] == 3
        assert kpis["failed_jobs"] == 2  # FAILED + TIMEOUT

    def test_users_list(self, sample_jobs):
        data = aggregate(_enrich_all(sample_jobs))
        assert set(data["users"]) == {"user_a", "user_b", "user_c"}

    def test_hourly_bins_have_entries(self, sample_jobs):
        data = aggregate(_enrich_all(sample_jobs))
        assert len(data["hourly_total"]) > 0

    def test_user_job_counts(self, sample_jobs):
        data = aggregate(_enrich_all(sample_jobs))
        counts = data["user_job_counts"]
        assert counts["user_a"] == 2
        assert counts["user_b"] == 2
        assert counts["user_c"] == 1

    def test_hourly_per_user_keys(self, sample_jobs):
        data = aggregate(_enrich_all(sample_jobs))
        assert "hourly_by_user" in data

    def test_wait_time_stats(self, sample_jobs):
        data = aggregate(_enrich_all(sample_jobs))
        assert "hourly_wait" in data
        assert "wait_by_user" in data

    def test_cpu_efficiency_by_user(self, sample_jobs):
        data = aggregate(_enrich_all(sample_jobs))
        assert "cpu_eff_by_user" in data
        assert "user_a" in data["cpu_eff_by_user"]

    def test_node_hour_matrix(self, sample_jobs):
        data = aggregate(_enrich_all(sample_jobs))
        assert "node_hour_matrix" in data

    def test_failed_by_user(self, sample_jobs):
        data = aggregate(_enrich_all(sample_jobs))
        failed = data["failed_by_user"]
        assert failed["user_b"]["FAILED"] == 1
        assert failed["user_c"]["TIMEOUT"] == 1

    def test_process_breakdown(self, sample_jobs):
        data = aggregate(_enrich_all(sample_jobs))
        breakdown = data["process_by_user"]
        assert "user_a" in breakdown
        assert "FILTER_MAF" in breakdown["user_a"]

    def test_sample_breakdown(self, sample_jobs):
        data = aggregate(_enrich_all(sample_jobs))
        breakdown = data["sample_by_user"]
        assert "user_a" in breakdown

    def test_scatter_data(self, sample_jobs):
        data = aggregate(_enrich_all(sample_jobs))
        scatter = data["mem_scatter"]
        assert len(scatter) == 5
        assert "req_mem_mb" in scatter[0]
        assert "max_rss_mb" in scatter[0]
        assert "user" in scatter[0]

    def test_dates_present(self, sample_jobs):
        data = aggregate(_enrich_all(sample_jobs))
        assert "all_dates" in data
        assert "2026-03-30" in data["all_dates"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_aggregator.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement aggregator.py**

```python
# src/aggregator.py
"""Pre-aggregate enriched job data for the dashboard."""

from collections import defaultdict
from statistics import median


def _hour_key(iso_str: str) -> str:
    """Truncate ISO datetime to hour: '2026-03-30T10:05:00' → '2026-03-30T10'."""
    return iso_str[:13]


def _date_key(iso_str: str) -> str:
    """Extract date from ISO datetime: '2026-03-30T10:05:00' → '2026-03-30'."""
    return iso_str[:10]


def _percentile(values: list[float], p: float) -> float:
    """Simple percentile calculation."""
    if not values:
        return 0.0
    sorted_v = sorted(values)
    k = (len(sorted_v) - 1) * p
    f = int(k)
    c = f + 1 if f + 1 < len(sorted_v) else f
    return sorted_v[f] + (k - f) * (sorted_v[c] - sorted_v[f])


def _stats(values: list[float]) -> dict:
    """Compute summary statistics for a list of values."""
    if not values:
        return {"min": 0, "max": 0, "median": 0, "avg": 0, "p25": 0, "p75": 0}
    return {
        "min": min(values),
        "max": max(values),
        "median": median(values),
        "avg": sum(values) / len(values),
        "p25": _percentile(values, 0.25),
        "p75": _percentile(values, 0.75),
    }


def aggregate(jobs: list[dict]) -> dict:
    """Aggregate enriched jobs into all data structures needed by the dashboard."""
    # Collect all dates and users
    all_dates = sorted({_date_key(j["submit"]) for j in jobs})
    users = sorted({j["user"] for j in jobs})

    # User job counts
    user_job_counts = defaultdict(int)
    for j in jobs:
        user_job_counts[j["user"]] += 1

    # Hourly bins — total and per-user
    hourly_total = defaultdict(int)
    hourly_by_user = defaultdict(lambda: defaultdict(int))
    for j in jobs:
        hk = _hour_key(j["submit"])
        hourly_total[hk] += 1
        hourly_by_user[j["user"]][hk] += 1

    # Sort hourly keys
    all_hours = sorted(hourly_total.keys())

    # Wait time — overall hourly stats
    hourly_wait_values = defaultdict(list)
    for j in jobs:
        hk = _hour_key(j["submit"])
        hourly_wait_values[hk].append(j["wait_seconds"])

    hourly_wait = {hk: _stats(vals) for hk, vals in hourly_wait_values.items()}

    # Wait time — per user (raw values for box plot)
    wait_by_user = defaultdict(list)
    for j in jobs:
        wait_by_user[j["user"]].append(j["wait_seconds"])

    # Wait time — per user hourly (for line chart)
    hourly_wait_by_user = defaultdict(lambda: defaultdict(list))
    for j in jobs:
        hk = _hour_key(j["submit"])
        hourly_wait_by_user[j["user"]][hk].append(j["wait_seconds"])

    wait_by_user_hourly = {
        user: {hk: sum(vals) / len(vals) for hk, vals in hours.items()}
        for user, hours in hourly_wait_by_user.items()
    }

    # CPU efficiency — per user (raw values for box plot)
    cpu_eff_by_user = defaultdict(list)
    for j in jobs:
        cpu_eff_by_user[j["user"]].append(j["cpu_efficiency"])

    # Memory scatter data (raw, for Chart 6)
    mem_scatter = [
        {
            "req_mem_mb": j["req_mem_mb"],
            "max_rss_mb": j.get("max_rss_mb", 0) or 0,
            "user": j["user"],
            "job_name": j["job_name"],
        }
        for j in jobs
    ]

    # Node-hour matrix
    node_hour_counts = defaultdict(lambda: defaultdict(int))
    for j in jobs:
        hk = _hour_key(j["submit"])
        for node in j.get("node_list", []):
            node_hour_counts[node][hk] += 1

    all_nodes = sorted(node_hour_counts.keys())
    node_hour_matrix = {
        "nodes": all_nodes,
        "hours": all_hours,
        "values": [
            [node_hour_counts[node].get(hk, 0) for hk in all_hours]
            for node in all_nodes
        ],
    }

    # Failed jobs — per user, per state
    failed_by_user = defaultdict(lambda: defaultdict(int))
    for j in jobs:
        if j["state"] != "COMPLETED":
            failed_by_user[j["user"]][j["state"]] += 1

    # Process breakdown — per user
    process_data = defaultdict(lambda: defaultdict(lambda: {"wait": [], "run": [], "count": 0}))
    for j in jobs:
        entry = process_data[j["user"]][j["process_name"]]
        entry["wait"].append(j["wait_seconds"])
        entry["run"].append(j["run_seconds"])
        entry["count"] += 1

    process_by_user = {
        user: {
            proc: {
                "count": d["count"],
                "wait": _stats(d["wait"]),
                "run": _stats(d["run"]),
            }
            for proc, d in procs.items()
        }
        for user, procs in process_data.items()
    }

    # Sample breakdown — per user
    sample_data = defaultdict(lambda: defaultdict(lambda: {"count": 0, "elapsed": []}))
    for j in jobs:
        sid = j["sample_id"] or "(no ID)"
        entry = sample_data[j["user"]][sid]
        entry["count"] += 1
        entry["elapsed"].append(j["run_seconds"])

    sample_by_user = {
        user: {
            sid: {"count": d["count"], "avg_elapsed": sum(d["elapsed"]) / len(d["elapsed"])}
            for sid, d in samples.items()
        }
        for user, samples in sample_data.items()
    }

    # KPIs
    all_wait = [j["wait_seconds"] for j in jobs]
    all_mem_eff = [j["mem_efficiency"] for j in jobs]
    kpis = {
        "total_jobs": len(jobs),
        "active_users": len(users),
        "median_wait": median(all_wait) if all_wait else 0,
        "median_mem_efficiency": median(all_mem_eff) if all_mem_eff else 0,
        "failed_jobs": sum(1 for j in jobs if j["state"] != "COMPLETED"),
    }

    return {
        "kpis": kpis,
        "users": users,
        "all_dates": all_dates,
        "all_hours": all_hours,
        "user_job_counts": dict(user_job_counts),
        "hourly_total": dict(hourly_total),
        "hourly_by_user": {u: dict(h) for u, h in hourly_by_user.items()},
        "hourly_wait": hourly_wait,
        "wait_by_user": dict(wait_by_user),
        "wait_by_user_hourly": wait_by_user_hourly,
        "cpu_eff_by_user": dict(cpu_eff_by_user),
        "mem_scatter": mem_scatter,
        "node_hour_matrix": node_hour_matrix,
        "failed_by_user": {u: dict(s) for u, s in failed_by_user.items()},
        "process_by_user": process_by_user,
        "sample_by_user": sample_by_user,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_aggregator.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/aggregator.py tests/test_aggregator.py
git commit -m "feat: add aggregator for pre-computing dashboard data"
```

---

### Task 5: Renderer — HTML Scaffold, CSS, and Data Injection

**Files:**
- Create: `src/renderer.py`
- Create: `src/chart_js.py`
- Create: `tests/test_renderer.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_renderer.py
from src.renderer import render_dashboard
from src.data_loader import enrich_job
from src.aggregator import aggregate


def _make_data(sample_jobs):
    enriched = [enrich_job(j) for j in sample_jobs]
    return aggregate(enriched)


class TestRenderer:
    def test_returns_html_string(self, sample_jobs):
        data = _make_data(sample_jobs)
        html = render_dashboard(data)
        assert isinstance(html, str)
        assert html.startswith("<!DOCTYPE html>")

    def test_contains_plotly_cdn(self, sample_jobs):
        data = _make_data(sample_jobs)
        html = render_dashboard(data)
        assert "plotly" in html.lower()

    def test_contains_dashboard_data(self, sample_jobs):
        data = _make_data(sample_jobs)
        html = render_dashboard(data)
        assert "DASHBOARD_DATA" in html

    def test_contains_toggle_buttons(self, sample_jobs):
        data = _make_data(sample_jobs)
        html = render_dashboard(data)
        assert "1 Day" in html
        assert "7 Days" in html

    def test_contains_kpi_section(self, sample_jobs):
        data = _make_data(sample_jobs)
        html = render_dashboard(data)
        assert "Total Jobs" in html

    def test_contains_chart_divs(self, sample_jobs):
        data = _make_data(sample_jobs)
        html = render_dashboard(data)
        for chart_id in [
            "chart-jobs-time", "chart-user-bar", "chart-user-lines",
            "chart-drilldown", "chart-mem-scatter", "chart-wait-overall",
            "chart-wait-user-box", "chart-wait-user-line",
            "chart-cpu-eff", "chart-node-heat", "chart-failed",
        ]:
            assert chart_id in html, f"Missing chart div: {chart_id}"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_renderer.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement renderer.py**

```python
# src/renderer.py
"""Generate the complete HTML dashboard."""

import json

from src.chart_js import get_chart_javascript


def _format_seconds(seconds: float) -> str:
    """Format seconds into human-readable string."""
    s = int(seconds)
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s // 60}m {s % 60}s"
    return f"{s // 3600}h {(s % 3600) // 60}m"


def render_dashboard(data: dict) -> str:
    """Render the complete HTML dashboard with embedded data."""
    kpis = data["kpis"]
    data_json = json.dumps(data, default=str)
    chart_js = get_chart_javascript()

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CMOBIC CPU Queue Dashboard</title>
<script src="https://cdn.plot.ly/plotly-2.35.0.min.js"></script>
<style>
{_get_css()}
</style>
</head>
<body>
<div class="dashboard">
  <div class="header">
    <h1>CMOBIC CPU Queue Dashboard</h1>
    <div class="toggle">
      <button id="btn-1d" class="toggle-btn active" onclick="setRange('1d')">1 Day</button>
      <button id="btn-7d" class="toggle-btn" onclick="setRange('7d')">7 Days</button>
    </div>
  </div>

  <div class="kpi-row">
    <div class="kpi-card">
      <div class="kpi-label">Total Jobs</div>
      <div class="kpi-value" id="kpi-total">{kpis['total_jobs']:,}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Active Users</div>
      <div class="kpi-value" id="kpi-users">{kpis['active_users']}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Median Wait</div>
      <div class="kpi-value" id="kpi-wait">{_format_seconds(kpis['median_wait'])}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Memory Efficiency</div>
      <div class="kpi-value kpi-warn" id="kpi-mem">{kpis['median_mem_efficiency']:.0%}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Failed Jobs</div>
      <div class="kpi-value kpi-bad" id="kpi-failed">{kpis['failed_jobs']}</div>
    </div>
  </div>

  <div class="chart-row">
    <div class="chart-box wide"><div id="chart-jobs-time"></div></div>
    <div class="chart-box narrow"><div id="chart-user-bar"></div></div>
  </div>

  <div class="chart-row">
    <div class="chart-box full"><div id="chart-user-lines"></div></div>
  </div>

  <div class="chart-row drilldown-container" id="drilldown-container" style="display:none;">
    <div class="chart-box full">
      <div class="drilldown-header">
        <span id="drilldown-title">Process Breakdown</span>
        <div class="drilldown-tabs">
          <button class="tab-btn active" onclick="showDrilldownTab('process')">By Process</button>
          <button class="tab-btn" onclick="showDrilldownTab('sample')">By Sample</button>
        </div>
        <button class="close-btn" onclick="closeDrilldown()">&times;</button>
      </div>
      <div id="chart-drilldown"></div>
    </div>
  </div>

  <div class="chart-row">
    <div class="chart-box half"><div id="chart-mem-scatter"></div></div>
    <div class="chart-box half"><div id="chart-wait-overall"></div></div>
  </div>

  <div class="chart-row">
    <div class="chart-box half"><div id="chart-wait-user-box"></div></div>
    <div class="chart-box half"><div id="chart-wait-user-line"></div></div>
  </div>

  <div class="chart-row">
    <div class="chart-box half"><div id="chart-cpu-eff"></div></div>
    <div class="chart-box half"><div id="chart-node-heat"></div></div>
  </div>

  <div class="chart-row">
    <div class="chart-box full"><div id="chart-failed"></div></div>
  </div>
</div>

<script>
const DASHBOARD_DATA = {data_json};
{chart_js}
</script>
</body>
</html>"""


def _get_css() -> str:
    return """
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #0d1117; color: #e6edf3; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
.dashboard { max-width: 1400px; margin: 0 auto; padding: 20px; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
h1 { font-size: 22px; font-weight: 600; }
.toggle { display: flex; gap: 4px; }
.toggle-btn { padding: 6px 18px; border: 1px solid #30363d; border-radius: 6px; background: #161b22; color: #8b949e; cursor: pointer; font-size: 13px; }
.toggle-btn.active { background: #1f6feb; color: #fff; border-color: #1f6feb; }
.kpi-row { display: flex; gap: 16px; margin-bottom: 20px; }
.kpi-card { flex: 1; background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; text-align: center; }
.kpi-label { font-size: 11px; text-transform: uppercase; color: #8b949e; margin-bottom: 4px; }
.kpi-value { font-size: 28px; font-weight: 700; color: #58a6ff; }
.kpi-warn { color: #d29922; }
.kpi-bad { color: #f85149; }
.chart-row { display: flex; gap: 16px; margin-bottom: 16px; }
.chart-box { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 12px; min-height: 300px; }
.chart-box.wide { flex: 3; }
.chart-box.narrow { flex: 2; }
.chart-box.half { flex: 1; }
.chart-box.full { flex: 1; width: 100%; }
.drilldown-header { display: flex; align-items: center; gap: 16px; margin-bottom: 8px; padding-bottom: 8px; border-bottom: 1px solid #30363d; }
.drilldown-header span { font-size: 16px; font-weight: 600; flex: 1; }
.drilldown-tabs { display: flex; gap: 4px; }
.tab-btn { padding: 4px 12px; border: 1px solid #30363d; border-radius: 4px; background: #161b22; color: #8b949e; cursor: pointer; font-size: 12px; }
.tab-btn.active { background: #1f6feb; color: #fff; border-color: #1f6feb; }
.close-btn { background: none; border: 1px solid #30363d; border-radius: 4px; color: #8b949e; font-size: 18px; cursor: pointer; padding: 2px 8px; }
.close-btn:hover { color: #f85149; border-color: #f85149; }
"""
```

- [ ] **Step 4: Create stub chart_js.py**

```python
# src/chart_js.py
"""JavaScript source code for all Plotly charts and interactions."""


def get_chart_javascript() -> str:
    """Return the complete JavaScript code for the dashboard."""
    return """
// Chart rendering will be implemented in subsequent tasks.
// This stub ensures the renderer produces valid HTML.

let currentRange = '1d';

function setRange(range) {
    currentRange = range;
    document.getElementById('btn-1d').classList.toggle('active', range === '1d');
    document.getElementById('btn-7d').classList.toggle('active', range === '7d');
    renderAllCharts();
}

function closeDrilldown() {
    document.getElementById('drilldown-container').style.display = 'none';
}

function showDrilldownTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    event.target.classList.add('active');
}

function renderAllCharts() {
    // Will be filled in by subsequent tasks
}
"""
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_renderer.py -v`
Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/renderer.py src/chart_js.py tests/test_renderer.py
git commit -m "feat: add renderer scaffold with HTML structure and CSS"
```

---

### Task 6: Chart JavaScript — Time Series Charts (Charts 2, 3, 4)

**Files:**
- Modify: `src/chart_js.py`

These are the core charts: stacked area (Chart 2), user bar (Chart 3), and per-user line (Chart 4).

- [ ] **Step 1: Implement data filtering and color assignment in chart_js.py**

Replace the `get_chart_javascript()` body in `src/chart_js.py` with the following (keeping the function signature). This step adds the toggle logic, color palette, and data filtering:

```python
def get_chart_javascript() -> str:
    return """
const DATA = DASHBOARD_DATA;
const PLOTLY_CONFIG = {responsive: true, displayModeBar: false};
const DARK_LAYOUT = {
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: {color: '#e6edf3', size: 12},
    xaxis: {gridcolor: '#21262d', linecolor: '#30363d'},
    yaxis: {gridcolor: '#21262d', linecolor: '#30363d'},
    margin: {t: 40, r: 20, b: 40, l: 60},
    legend: {bgcolor: 'rgba(0,0,0,0)'},
};

const COLORS = [
    '#58a6ff', '#3fb950', '#d29922', '#f85149', '#bc8cff',
    '#79c0ff', '#56d364', '#e3b341', '#ff7b72', '#d2a8ff',
    '#39d353', '#a5d6ff', '#ffa657', '#ff9bce', '#7ee787',
];

let currentRange = '7d';
let selectedUser = null;
let drilldownTab = 'process';

function getUserColor(user) {
    const idx = DATA.users.indexOf(user);
    return COLORS[idx % COLORS.length];
}

function getFilteredHours() {
    if (currentRange === '1d' && DATA.all_dates.length > 0) {
        const lastDate = DATA.all_dates[DATA.all_dates.length - 1];
        return DATA.all_hours.filter(h => h.startsWith(lastDate));
    }
    return DATA.all_hours;
}

function setRange(range) {
    currentRange = range;
    document.getElementById('btn-1d').classList.toggle('active', range === '1d');
    document.getElementById('btn-7d').classList.toggle('active', range === '7d');
    renderAllCharts();
}

function closeDrilldown() {
    document.getElementById('drilldown-container').style.display = 'none';
    selectedUser = null;
}

function showDrilldownTab(tab) {
    drilldownTab = tab;
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    event.target.classList.add('active');
    renderDrilldown();
}

""" + _chart2_js() + _chart3_js() + _chart4_js() + _charts_rest_js() + """

function renderAllCharts() {
    renderChart2();
    renderChart3();
    renderChart4();
    renderChart6();
    renderChart7();
    renderChart8();
    renderChart9();
    renderChart10();
    renderChart11();
    renderChart12();
    if (selectedUser) renderDrilldown();
}

document.addEventListener('DOMContentLoaded', renderAllCharts);
"""
```

- [ ] **Step 2: Add chart 2 (stacked area) helper**

Add this function to `chart_js.py` (called by `get_chart_javascript`):

```python
def _chart2_js() -> str:
    """Chart 2: Total Jobs Over Time — stacked area."""
    return """
function renderChart2() {
    const hours = getFilteredHours();
    const traces = DATA.users.map(user => ({
        x: hours,
        y: hours.map(h => (DATA.hourly_by_user[user] || {})[h] || 0),
        name: user,
        type: 'scatter',
        mode: 'none',
        stackgroup: 'one',
        fillcolor: getUserColor(user),
        line: {color: getUserColor(user)},
    }));
    const layout = {...DARK_LAYOUT, title: 'Total Jobs Over Time', xaxis: {...DARK_LAYOUT.xaxis, title: 'Hour'}, yaxis: {...DARK_LAYOUT.yaxis, title: 'Job Count'}};
    Plotly.react('chart-jobs-time', traces, layout, PLOTLY_CONFIG);
}
"""
```

- [ ] **Step 3: Add chart 3 (user bar) helper with click handler**

```python
def _chart3_js() -> str:
    """Chart 3: Jobs by User — horizontal bar with click-to-drilldown."""
    return """
function renderChart3() {
    const sorted = Object.entries(DATA.user_job_counts).sort((a, b) => b[1] - a[1]);
    const users = sorted.map(e => e[0]);
    const counts = sorted.map(e => e[1]);
    const colors = users.map(u => getUserColor(u));

    const trace = {
        y: users, x: counts, type: 'bar', orientation: 'h',
        marker: {color: colors},
        hovertemplate: '%{y}: %{x} jobs<extra></extra>',
    };
    const layout = {...DARK_LAYOUT, title: 'Total Jobs by User (click for details)', yaxis: {...DARK_LAYOUT.yaxis, autorange: 'reversed'}, xaxis: {...DARK_LAYOUT.xaxis, title: 'Job Count'}};
    Plotly.react('chart-user-bar', [trace], layout, PLOTLY_CONFIG);

    document.getElementById('chart-user-bar').on('plotly_click', function(eventData) {
        const user = eventData.points[0].y;
        selectedUser = user;
        document.getElementById('drilldown-container').style.display = 'flex';
        document.getElementById('drilldown-title').textContent = user + ' — Breakdown';
        renderDrilldown();
    });
}
"""
```

- [ ] **Step 4: Add chart 4 (user line) helper**

```python
def _chart4_js() -> str:
    """Chart 4: Job Submissions by User Over Time — line graph."""
    return """
function renderChart4() {
    const hours = getFilteredHours();
    const traces = DATA.users.map(user => ({
        x: hours,
        y: hours.map(h => (DATA.hourly_by_user[user] || {})[h] || 0),
        name: user,
        type: 'scatter',
        mode: 'lines',
        line: {color: getUserColor(user), width: 2},
    }));
    const layout = {...DARK_LAYOUT, title: 'Job Submissions by User Over Time', xaxis: {...DARK_LAYOUT.xaxis, title: 'Hour'}, yaxis: {...DARK_LAYOUT.yaxis, title: 'Jobs'}};
    Plotly.react('chart-user-lines', traces, layout, PLOTLY_CONFIG);
}
"""
```

- [ ] **Step 5: Add placeholder for remaining charts**

```python
def _charts_rest_js() -> str:
    """Placeholder stubs for charts 5-12, to be implemented in next tasks."""
    return """
function renderDrilldown() {}
function renderChart6() {}
function renderChart7() {}
function renderChart8() {}
function renderChart9() {}
function renderChart10() {}
function renderChart11() {}
function renderChart12() {}
"""
```

- [ ] **Step 6: Run all tests**

Run: `uv run pytest -v`
Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add src/chart_js.py
git commit -m "feat: add charts 2-4 (stacked area, user bar, user line)"
```

---

### Task 7: Chart JavaScript — Drill-Down Panel (Chart 5)

**Files:**
- Modify: `src/chart_js.py`

- [ ] **Step 1: Replace `renderDrilldown` stub**

Replace `function renderDrilldown() {}` in `_charts_rest_js()` with a call to a new helper. Add this function to `chart_js.py`:

```python
def _chart5_js() -> str:
    """Chart 5: User drill-down — grouped Gantt with process/sample tabs."""
    return """
function renderDrilldown() {
    if (!selectedUser) return;
    if (drilldownTab === 'process') {
        renderDrilldownProcess();
    } else {
        renderDrilldownSample();
    }
}

function renderDrilldownProcess() {
    const procData = DATA.process_by_user[selectedUser] || {};
    const procs = Object.entries(procData).sort((a, b) => b[1].count - a[1].count);

    const names = procs.map(p => p[0]);
    const waitAvg = procs.map(p => p[1].wait.avg);
    const runAvg = procs.map(p => p[1].run.avg);
    const counts = procs.map(p => p[1].count);

    const traceWait = {
        y: names, x: waitAvg, type: 'bar', orientation: 'h',
        name: 'Avg Wait', marker: {color: '#484f58'},
        hovertemplate: '%{y}<br>Avg wait: %{x:.0f}s<extra></extra>',
    };
    const traceRun = {
        y: names, x: runAvg, type: 'bar', orientation: 'h',
        name: 'Avg Run', marker: {color: getUserColor(selectedUser)},
        customdata: counts,
        hovertemplate: '%{y}<br>Avg run: %{x:.0f}s<br>n=%{customdata}<extra></extra>',
    };

    const layout = {
        ...DARK_LAYOUT, barmode: 'stack', title: 'By Process — ' + selectedUser,
        yaxis: {...DARK_LAYOUT.yaxis, autorange: 'reversed'},
        xaxis: {...DARK_LAYOUT.xaxis, title: 'Seconds'},
        annotations: names.map((name, i) => ({
            x: waitAvg[i] + runAvg[i] + 5, y: name, text: 'n=' + counts[i],
            showarrow: false, font: {size: 10, color: '#8b949e'},
        })),
    };
    Plotly.react('chart-drilldown', [traceWait, traceRun], layout, PLOTLY_CONFIG);
}

function renderDrilldownSample() {
    const sampleData = DATA.sample_by_user[selectedUser] || {};
    const samples = Object.entries(sampleData).sort((a, b) => b[1].count - a[1].count);

    const names = samples.map(s => s[0]);
    const counts = samples.map(s => s[1].count);
    const elapsed = samples.map(s => s[1].avg_elapsed);

    const trace = {
        y: names, x: counts, type: 'bar', orientation: 'h',
        marker: {color: getUserColor(selectedUser)},
        customdata: elapsed,
        hovertemplate: '%{y}<br>Jobs: %{x}<br>Avg elapsed: %{customdata:.0f}s<extra></extra>',
    };
    const layout = {
        ...DARK_LAYOUT, title: 'By Sample — ' + selectedUser,
        yaxis: {...DARK_LAYOUT.yaxis, autorange: 'reversed'},
        xaxis: {...DARK_LAYOUT.xaxis, title: 'Job Count'},
    };
    Plotly.react('chart-drilldown', [trace], layout, PLOTLY_CONFIG);
}
"""
```

- [ ] **Step 2: Update `_charts_rest_js` to remove the drilldown stub and include the new function**

Update `_charts_rest_js` to remove `function renderDrilldown() {}` since it's now in `_chart5_js()`. Update `get_chart_javascript()` to call `_chart5_js()` in the concatenation.

- [ ] **Step 3: Run all tests**

Run: `uv run pytest -v`
Expected: All tests PASS.

- [ ] **Step 4: Commit**

```bash
git add src/chart_js.py
git commit -m "feat: add chart 5 (user drill-down with process/sample tabs)"
```

---

### Task 8: Chart JavaScript — Memory and Wait Time Charts (Charts 6–9)

**Files:**
- Modify: `src/chart_js.py`

- [ ] **Step 1: Implement Chart 6 (memory scatter)**

Add to `chart_js.py`:

```python
def _chart6_js() -> str:
    """Chart 6: Memory Requested vs Used — scatter."""
    return """
function renderChart6() {
    const scatter = DATA.mem_scatter;
    const tracesByUser = {};
    scatter.forEach(d => {
        if (!tracesByUser[d.user]) tracesByUser[d.user] = {x: [], y: [], text: []};
        tracesByUser[d.user].x.push(d.req_mem_mb);
        tracesByUser[d.user].y.push(d.max_rss_mb);
        tracesByUser[d.user].text.push(d.job_name);
    });

    const traces = Object.entries(tracesByUser).map(([user, d]) => ({
        x: d.x, y: d.y, text: d.text, name: user,
        type: 'scatter', mode: 'markers',
        marker: {color: getUserColor(user), size: 5, opacity: 0.6},
        hovertemplate: '%{text}<br>Req: %{x:.0f} MB<br>Used: %{y:.0f} MB<extra></extra>',
    }));

    // Diagonal reference line
    const maxVal = Math.max(...scatter.map(d => Math.max(d.req_mem_mb, d.max_rss_mb)), 1);
    traces.push({
        x: [0, maxVal], y: [0, maxVal], type: 'scatter', mode: 'lines',
        line: {color: '#30363d', dash: 'dash', width: 1},
        showlegend: false, hoverinfo: 'skip',
    });

    const layout = {
        ...DARK_LAYOUT, title: 'Memory: Requested vs Used',
        xaxis: {...DARK_LAYOUT.xaxis, title: 'Requested (MB)'},
        yaxis: {...DARK_LAYOUT.yaxis, title: 'Max RSS (MB)'},
    };
    Plotly.react('chart-mem-scatter', traces, layout, PLOTLY_CONFIG);
}
"""
```

- [ ] **Step 2: Implement Chart 7 (overall wait time line + band)**

```python
def _chart7_js() -> str:
    """Chart 7: Overall Queue Wait Time — line with p25-p75 band."""
    return """
function renderChart7() {
    const hours = getFilteredHours();
    const medians = hours.map(h => (DATA.hourly_wait[h] || {}).median || 0);
    const p25 = hours.map(h => (DATA.hourly_wait[h] || {}).p25 || 0);
    const p75 = hours.map(h => (DATA.hourly_wait[h] || {}).p75 || 0);

    const traceBand = {
        x: [...hours, ...hours.slice().reverse()],
        y: [...p75, ...p25.slice().reverse()],
        fill: 'toself', fillcolor: 'rgba(88,166,255,0.15)',
        line: {color: 'transparent'}, type: 'scatter',
        showlegend: false, hoverinfo: 'skip',
    };
    const traceMedian = {
        x: hours, y: medians, type: 'scatter', mode: 'lines',
        name: 'Median', line: {color: '#58a6ff', width: 2},
        hovertemplate: 'Hour: %{x}<br>Median wait: %{y:.0f}s<extra></extra>',
    };

    const layout = {
        ...DARK_LAYOUT, title: 'Queue Wait Time Over Time',
        xaxis: {...DARK_LAYOUT.xaxis, title: 'Hour'},
        yaxis: {...DARK_LAYOUT.yaxis, title: 'Wait (seconds)'},
    };
    Plotly.react('chart-wait-overall', [traceBand, traceMedian], layout, PLOTLY_CONFIG);
}
"""
```

- [ ] **Step 3: Implement Chart 8 (wait time by user box plot)**

```python
def _chart8_js() -> str:
    """Chart 8: Wait Time by User — box plot."""
    return """
function renderChart8() {
    const traces = DATA.users
        .filter(u => DATA.wait_by_user[u] && DATA.wait_by_user[u].length > 0)
        .map(user => ({
            y: DATA.wait_by_user[user], name: user, type: 'box',
            marker: {color: getUserColor(user)},
            boxpoints: false,
        }));
    const layout = {...DARK_LAYOUT, title: 'Wait Time by User', yaxis: {...DARK_LAYOUT.yaxis, title: 'Wait (seconds)'}, showlegend: false};
    Plotly.react('chart-wait-user-box', traces, layout, PLOTLY_CONFIG);
}
"""
```

- [ ] **Step 4: Implement Chart 9 (wait time by user over time line)**

```python
def _chart9_js() -> str:
    """Chart 9: Wait Time by User Over Time — line graph."""
    return """
function renderChart9() {
    const hours = getFilteredHours();
    const traces = DATA.users
        .filter(u => DATA.wait_by_user_hourly[u])
        .map(user => ({
            x: hours,
            y: hours.map(h => (DATA.wait_by_user_hourly[user] || {})[h] || null),
            name: user, type: 'scatter', mode: 'lines',
            line: {color: getUserColor(user), width: 2},
            connectgaps: false,
        }));
    const layout = {
        ...DARK_LAYOUT, title: 'Wait Time by User Over Time',
        xaxis: {...DARK_LAYOUT.xaxis, title: 'Hour'},
        yaxis: {...DARK_LAYOUT.yaxis, title: 'Avg Wait (seconds)'},
    };
    Plotly.react('chart-wait-user-line', traces, layout, PLOTLY_CONFIG);
}
"""
```

- [ ] **Step 5: Update get_chart_javascript to include new chart functions**

Update the concatenation in `get_chart_javascript()` to include `_chart6_js()`, `_chart7_js()`, `_chart8_js()`, `_chart9_js()` and remove their stubs from `_charts_rest_js()`.

- [ ] **Step 6: Run all tests**

Run: `uv run pytest -v`
Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add src/chart_js.py
git commit -m "feat: add charts 6-9 (memory scatter, wait time line/box/user)"
```

---

### Task 9: Chart JavaScript — Resource Charts (Charts 10–12)

**Files:**
- Modify: `src/chart_js.py`

- [ ] **Step 1: Implement Chart 10 (CPU efficiency box plot)**

```python
def _chart10_js() -> str:
    """Chart 10: CPU Efficiency by User — box plot."""
    return """
function renderChart10() {
    const traces = DATA.users
        .filter(u => DATA.cpu_eff_by_user[u] && DATA.cpu_eff_by_user[u].length > 0)
        .map(user => ({
            y: DATA.cpu_eff_by_user[user], name: user, type: 'box',
            marker: {color: getUserColor(user)},
            boxpoints: false,
        }));
    const layout = {
        ...DARK_LAYOUT, title: 'CPU Efficiency by User',
        yaxis: {...DARK_LAYOUT.yaxis, title: 'Efficiency (0-1)', range: [0, 1.1]},
        showlegend: false,
    };
    Plotly.react('chart-cpu-eff', traces, layout, PLOTLY_CONFIG);
}
"""
```

- [ ] **Step 2: Implement Chart 11 (node heatmap)**

```python
def _chart11_js() -> str:
    """Chart 11: Node Utilization Heatmap."""
    return """
function renderChart11() {
    const matrix = DATA.node_hour_matrix;
    const hours = getFilteredHours();

    // Filter matrix columns to match current range
    const hourIndices = hours.map(h => matrix.hours.indexOf(h)).filter(i => i >= 0);
    const filteredValues = matrix.nodes.map((_, ni) =>
        hourIndices.map(hi => matrix.values[ni][hi])
    );

    const trace = {
        z: filteredValues,
        x: hours,
        y: matrix.nodes,
        type: 'heatmap',
        colorscale: [[0, '#0d1117'], [0.5, '#1f6feb'], [1, '#58a6ff']],
        hovertemplate: 'Node: %{y}<br>Hour: %{x}<br>Jobs: %{z}<extra></extra>',
    };
    const layout = {
        ...DARK_LAYOUT, title: 'Node Utilization',
        xaxis: {...DARK_LAYOUT.xaxis, title: 'Hour'},
        yaxis: {...DARK_LAYOUT.yaxis, title: ''},
    };
    Plotly.react('chart-node-heat', [trace], layout, PLOTLY_CONFIG);
}
"""
```

- [ ] **Step 3: Implement Chart 12 (failed jobs by user bar)**

```python
def _chart12_js() -> str:
    """Chart 12: Failed/Timed-Out Jobs by User — stacked bar."""
    return """
function renderChart12() {
    const failedData = DATA.failed_by_user;
    const users = Object.keys(failedData);
    if (users.length === 0) {
        Plotly.react('chart-failed', [], {...DARK_LAYOUT, title: 'Failed / Timed-Out Jobs by User', annotations: [{text: 'No failed jobs', showarrow: false, font: {size: 16, color: '#3fb950'}}]}, PLOTLY_CONFIG);
        return;
    }

    // Collect all states
    const allStates = [...new Set(users.flatMap(u => Object.keys(failedData[u])))];
    const stateColors = {'FAILED': '#f85149', 'TIMEOUT': '#d29922', 'CANCELLED': '#8b949e', 'OUT_OF_MEMORY': '#bc8cff'};

    const traces = allStates.map(state => ({
        y: users,
        x: users.map(u => failedData[u][state] || 0),
        name: state, type: 'bar', orientation: 'h',
        marker: {color: stateColors[state] || '#8b949e'},
        hovertemplate: '%{y}: %{x} ' + state + '<extra></extra>',
    }));

    const layout = {
        ...DARK_LAYOUT, barmode: 'stack',
        title: 'Failed / Timed-Out Jobs by User',
        yaxis: {...DARK_LAYOUT.yaxis}, xaxis: {...DARK_LAYOUT.xaxis, title: 'Count'},
    };
    Plotly.react('chart-failed', traces, layout, PLOTLY_CONFIG);
}
"""
```

- [ ] **Step 4: Update get_chart_javascript and remove all stubs from _charts_rest_js**

Remove `_charts_rest_js` entirely. Update `get_chart_javascript()` to concatenate all chart helpers:

```python
def get_chart_javascript() -> str:
    return (
        _base_js()
        + _chart2_js()
        + _chart3_js()
        + _chart4_js()
        + _chart5_js()
        + _chart6_js()
        + _chart7_js()
        + _chart8_js()
        + _chart9_js()
        + _chart10_js()
        + _chart11_js()
        + _chart12_js()
        + _main_js()
    )
```

Where `_base_js()` contains the constants, color logic, toggle, and filter functions, and `_main_js()` contains:

```python
def _main_js() -> str:
    return """
function renderAllCharts() {
    renderChart2();
    renderChart3();
    renderChart4();
    renderChart6();
    renderChart7();
    renderChart8();
    renderChart9();
    renderChart10();
    renderChart11();
    renderChart12();
    if (selectedUser) renderDrilldown();
}

document.addEventListener('DOMContentLoaded', renderAllCharts);
"""
```

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -v`
Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/chart_js.py
git commit -m "feat: add charts 10-12 (CPU efficiency, node heatmap, failed jobs)"
```

---

### Task 10: CLI Entry Point + Integration Test

**Files:**
- Create: `generate_dashboard.py`

- [ ] **Step 1: Implement generate_dashboard.py**

```python
# generate_dashboard.py
"""CLI entry point: generate the CMOBIC CPU Queue Dashboard."""

import argparse
from pathlib import Path

from src.aggregator import aggregate
from src.data_loader import load_jobs
from src.renderer import render_dashboard


def main():
    parser = argparse.ArgumentParser(description="Generate CMOBIC CPU Queue Dashboard")
    parser.add_argument(
        "--data-dir",
        type=Path,
        required=True,
        help="Directory containing job_YYYY-MM-DD.json files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("dashboard.html"),
        help="Output HTML file path (default: dashboard.html)",
    )
    args = parser.parse_args()

    if not args.data_dir.is_dir():
        parser.error(f"Data directory not found: {args.data_dir}")

    jobs = load_jobs(args.data_dir, days=7)
    if not jobs:
        print(f"Warning: No job data found in {args.data_dir} for the last 7 days")

    data = aggregate(jobs) if jobs else aggregate([])
    html = render_dashboard(data)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html)
    print(f"Dashboard written to {args.output} ({len(jobs)} jobs from {len(data.get('all_dates', []))} days)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Test the CLI end-to-end with sample data**

Run:
```bash
# Create test data directory with sample JSON
mkdir -p /tmp/test_slurm_data
cat > /tmp/test_slurm_data/job_2026-03-30.json << 'JSONEOF'
[{"job_id":"100","job_name":"nf-NFCORE_KREWLYZER_KREWLYZER_FILTER_MAF_(P-0000001-T01-TEST)","user":"user_a","account":"user_a","partition":"cmobic_cpu","state":"COMPLETED","req_cpus":2,"submit":"2026-03-30T10:00:00","start":"2026-03-30T10:05:00","end":"2026-03-30T10:05:03","elapsed":"00:00:03","node_list":["node001"],"alloc_cpus":2,"cpu_time_raw":6,"time_limit":"02:00:00","total_cpu":"00:02.223","base_job_id":"100","max_gpu_util":null,"max_rss_mb":17.96,"req_mem_mb":12288.0,"alloc_mem_mb":12288.0,"state_by_jobid":null,"req_gpu_type":null,"req_gpus":null,"alloc_gpu_type":null,"alloc_gpus":null},{"job_id":"101","job_name":"alignment_C-003DS_hg38","user":"user_b","account":"user_b","partition":"cmobic_cpu","state":"FAILED","req_cpus":4,"submit":"2026-03-30T12:00:00","start":"2026-03-30T12:10:00","end":"2026-03-30T12:15:00","elapsed":"00:05:00","node_list":["node002"],"alloc_cpus":4,"cpu_time_raw":100,"time_limit":"02:00:00","total_cpu":"00:01:40.000","base_job_id":"101","max_gpu_util":null,"max_rss_mb":500.0,"req_mem_mb":8192.0,"alloc_mem_mb":8192.0,"state_by_jobid":null,"req_gpu_type":null,"req_gpus":null,"alloc_gpu_type":null,"alloc_gpus":null}]
JSONEOF

uv run python generate_dashboard.py --data-dir /tmp/test_slurm_data --output /tmp/test_dashboard.html
```

Expected: `Dashboard written to /tmp/test_dashboard.html (2 jobs from 1 days)`

- [ ] **Step 3: Verify the HTML opens and renders**

Run:
```bash
# Check file was created and has content
wc -c /tmp/test_dashboard.html
# Open in browser (macOS)
open /tmp/test_dashboard.html
```

Expected: File exists with substantial content. Browser shows the dashboard with dark theme, KPI cards, and charts.

- [ ] **Step 4: Run full test suite**

Run: `uv run pytest -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add generate_dashboard.py
git commit -m "feat: add CLI entry point for dashboard generation"
```

---

### Task 11: KPI Update on Toggle

**Files:**
- Modify: `src/chart_js.py`
- Modify: `src/renderer.py`

The KPI cards show 7-day totals but should update when toggling to 1-day. Since KPIs are baked into HTML at generation time, we need to also embed per-date KPI data and update them client-side.

- [ ] **Step 1: Add per-date KPIs to aggregator output**

Add to `src/aggregator.py`, inside the `aggregate` function, before the `return` statement:

```python
    # Per-date KPIs (for 1-day toggle)
    kpis_by_date = {}
    for date in all_dates:
        date_jobs = [j for j in jobs if _date_key(j["submit"]) == date]
        date_wait = [j["wait_seconds"] for j in date_jobs]
        date_mem = [j["mem_efficiency"] for j in date_jobs]
        kpis_by_date[date] = {
            "total_jobs": len(date_jobs),
            "active_users": len({j["user"] for j in date_jobs}),
            "median_wait": median(date_wait) if date_wait else 0,
            "median_mem_efficiency": median(date_mem) if date_mem else 0,
            "failed_jobs": sum(1 for j in date_jobs if j["state"] != "COMPLETED"),
        }
```

And add `"kpis_by_date": kpis_by_date,` to the return dict.

- [ ] **Step 2: Add KPI update logic to chart_js.py**

Add to `_base_js()` inside `setRange()`, after toggling button classes:

```javascript
function updateKPIs() {
    let kpis;
    if (currentRange === '1d' && DATA.all_dates.length > 0) {
        const lastDate = DATA.all_dates[DATA.all_dates.length - 1];
        kpis = DATA.kpis_by_date[lastDate] || DATA.kpis;
    } else {
        kpis = DATA.kpis;
    }
    document.getElementById('kpi-total').textContent = kpis.total_jobs.toLocaleString();
    document.getElementById('kpi-users').textContent = kpis.active_users;
    document.getElementById('kpi-wait').textContent = formatSeconds(kpis.median_wait);
    document.getElementById('kpi-mem').textContent = (kpis.median_mem_efficiency * 100).toFixed(0) + '%';
    document.getElementById('kpi-failed').textContent = kpis.failed_jobs;
}

function formatSeconds(s) {
    s = Math.round(s);
    if (s < 60) return s + 's';
    if (s < 3600) return Math.floor(s/60) + 'm ' + (s%60) + 's';
    return Math.floor(s/3600) + 'h ' + Math.floor((s%3600)/60) + 'm';
}
```

And call `updateKPIs()` inside `renderAllCharts()`.

- [ ] **Step 3: Run all tests**

Run: `uv run pytest -v`
Expected: All tests PASS.

- [ ] **Step 4: Commit**

```bash
git add src/aggregator.py src/chart_js.py src/renderer.py
git commit -m "feat: update KPI cards on 1-day/7-day toggle"
```

---

### Task 12: Final Polish + End-to-End Verification

**Files:**
- Modify: `src/renderer.py` (generation timestamp)
- Create: `.gitignore`

- [ ] **Step 1: Add generation timestamp to footer**

In `src/renderer.py`, add a footer div before the closing `</div><!-- .dashboard -->` and `<script>`:

```html
  <div class="footer">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Data: {len(data.get('all_dates', []))} days, {data['kpis']['total_jobs']} jobs</div>
```

Add to `_get_css()`:

```css
.footer { text-align: center; color: #484f58; font-size: 11px; margin-top: 20px; padding: 12px; }
```

Add `from datetime import datetime` to imports in `renderer.py`.

- [ ] **Step 2: Create .gitignore**

```gitignore
# Environment
.env
.env.*
!.env.example

# Python
__pycache__/
*.pyc
.venv/

# Build
dist/
build/

# Output
dashboard.html

# IDE
.idea/
.vscode/
*.swp

# OS
.DS_Store

# Superpowers
.superpowers/

# Claude
.claude/settings.local.json
CLAUDE.local.md
```

- [ ] **Step 3: Run full test suite one final time**

Run: `uv run pytest -v`
Expected: All tests PASS.

- [ ] **Step 4: Generate dashboard with test data and visually verify**

Run:
```bash
uv run python generate_dashboard.py --data-dir /tmp/test_slurm_data --output /tmp/test_dashboard.html
open /tmp/test_dashboard.html
```

Verify:
- Dark theme renders correctly
- KPI cards show values
- Toggle switches between 1-day and 7-day
- Charts render with data
- Clicking a user bar in Chart 3 reveals the drill-down panel
- Process and Sample tabs work in drill-down
- Close button dismisses drill-down
- Memory scatter shows diagonal reference line
- Wait time charts show line + band
- Node heatmap renders
- Failed jobs chart shows stacked bars

- [ ] **Step 5: Commit all remaining files**

```bash
git add .gitignore src/renderer.py
git commit -m "feat: add generation timestamp footer and gitignore"
```

- [ ] **Step 6: Final commit with all files**

```bash
git add -A
git status  # verify no secrets or sensitive files
git commit -m "chore: complete CMOBIC CPU Queue Dashboard v1"
```

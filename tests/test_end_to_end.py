# tests/test_end_to_end.py
import json
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

from src.aggregator import aggregate
from src.data_loader import load_jobs
from src.renderer import render_dashboard


FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestEndToEnd:
    def test_full_pipeline_produces_valid_html(self):
        jobs = load_jobs(FIXTURES_DIR, days=9999)
        assert len(jobs) == 15
        data = aggregate(jobs)
        html = render_dashboard(data)
        assert html.startswith("<!DOCTYPE html>")
        assert "</html>" in html

    def test_pipeline_contains_expected_users(self):
        jobs = load_jobs(FIXTURES_DIR, days=9999)
        data = aggregate(jobs)
        assert set(data["users"]) == {"orgeraj", "vurals", "noronhaa", "pricea2"}

    def test_pipeline_kpis_correct(self):
        jobs = load_jobs(FIXTURES_DIR, days=9999)
        data = aggregate(jobs)
        kpis = data["kpis"]
        assert kpis["total_jobs"] == 15
        assert kpis["active_users"] == 4
        # FAILED(2) + TIMEOUT(1) + CANCELLED(1) + OUT_OF_MEMORY(1) = 5
        assert kpis["failed_jobs"] == 5

    def test_pipeline_failure_states(self):
        jobs = load_jobs(FIXTURES_DIR, days=9999)
        data = aggregate(jobs)
        failed = data["failed_by_user"]
        assert failed["orgeraj"]["FAILED"] == 2
        assert failed["noronhaa"]["TIMEOUT"] == 1
        assert failed["noronhaa"]["CANCELLED"] == 1
        assert failed["pricea2"]["OUT_OF_MEMORY"] == 1

    def test_pipeline_html_contains_chart_divs(self):
        jobs = load_jobs(FIXTURES_DIR, days=9999)
        data = aggregate(jobs)
        html = render_dashboard(data)
        for chart_id in [
            "chart-jobs-time", "chart-user-bar", "chart-failed",
            "chart-mem-scatter", "chart-cpu-eff", "chart-mem-eff",
        ]:
            assert chart_id in html

    def test_pipeline_html_has_fetch_bootstrap(self):
        jobs = load_jobs(FIXTURES_DIR, days=9999)
        data = aggregate(jobs)
        html = render_dashboard(data)
        assert "fetch(" in html
        assert "work_complete_data_latest.json" in html
        assert "const DASHBOARD_DATA" not in html

    def test_empty_directory_produces_valid_html(self, tmp_path):
        jobs = load_jobs(tmp_path, days=7)
        assert jobs == []
        data = aggregate(jobs)
        html = render_dashboard(data)
        assert html.startswith("<!DOCTYPE html>")
        assert "Total Jobs" in html

    def test_pipeline_process_extraction(self):
        jobs = load_jobs(FIXTURES_DIR, days=9999)
        data = aggregate(jobs)
        # orgeraj has Nextflow jobs — check process names extracted
        orgeraj_procs = set(data["process_by_user"]["orgeraj"].keys())
        assert "BWAMEM2" in orgeraj_procs
        assert "MARKDUP" in orgeraj_procs
        assert "FILTER_MAF" in orgeraj_procs

    def test_pipeline_sample_ids(self):
        jobs = load_jobs(FIXTURES_DIR, days=9999)
        data = aggregate(jobs)
        vurals_samples = set(data["sample_by_user"]["vurals"].keys())
        assert "C-00ABC" in vurals_samples
        assert "s_C_ABCDE" in vurals_samples
        assert "s_C_FGHIJ" in vurals_samples


class TestDualFileOutput:
    def test_generate_dashboard_writes_json_file(self):
        """generate_dashboard main() writes both .html and .json when --output-json given."""
        jobs_dir = PROJECT_ROOT / "tests" / "fixtures"
        with tempfile.TemporaryDirectory() as tmpdir:
            out_html = Path(tmpdir) / "dashboard.html"
            out_json = Path(tmpdir) / "dashboard.json"
            result = subprocess.run(
                [sys.executable, str(PROJECT_ROOT / "generate_dashboard.py"),
                 "--data-dir", str(jobs_dir),
                 "--output", str(out_html),
                 "--output-json", str(out_json)],
                capture_output=True, text=True,
                cwd=str(PROJECT_ROOT),
            )
            assert result.returncode == 0, result.stderr
            assert out_html.exists()
            assert out_json.exists()
            parsed = json.loads(out_json.read_text())
            assert "users" in parsed

    def test_generate_dashboard_json_defaults_to_html_path(self):
        """Without --output-json, json file is written next to html with .json extension."""
        jobs_dir = PROJECT_ROOT / "tests" / "fixtures"
        with tempfile.TemporaryDirectory() as tmpdir:
            out_html = Path(tmpdir) / "dashboard.html"
            result = subprocess.run(
                [sys.executable, str(PROJECT_ROOT / "generate_dashboard.py"),
                 "--data-dir", str(jobs_dir),
                 "--output", str(out_html)],
                capture_output=True, text=True,
                cwd=str(PROJECT_ROOT),
            )
            assert result.returncode == 0, result.stderr
            out_json = Path(tmpdir) / "dashboard.json"
            assert out_json.exists()

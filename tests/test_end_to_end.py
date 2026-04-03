# tests/test_end_to_end.py
import json
import re
from pathlib import Path

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

    def test_pipeline_html_has_valid_json_data(self):
        jobs = load_jobs(FIXTURES_DIR, days=9999)
        data = aggregate(jobs)
        html = render_dashboard(data)
        match = re.search(r"const DASHBOARD_DATA = ({.*?});\n", html, re.DOTALL)
        assert match, "DASHBOARD_DATA not found in HTML"
        parsed = json.loads(match.group(1))
        assert parsed["kpis"]["total_jobs"] == 15

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

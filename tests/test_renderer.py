# tests/test_renderer.py
import json
import re

from src.renderer import render_dashboard, render_data_json, _format_seconds
from src.data_loader import enrich_job
from src.aggregator import aggregate


def _make_data(sample_jobs):
    enriched = [enrich_job(j) for j in sample_jobs]
    return aggregate(enriched)


class TestFormatSeconds:
    def test_zero(self):
        assert _format_seconds(0) == "0s"

    def test_seconds_only(self):
        assert _format_seconds(45) == "45s"

    def test_minutes_and_seconds(self):
        assert _format_seconds(90) == "1m 30s"

    def test_hours_and_minutes(self):
        assert _format_seconds(3661) == "1h 1m"

    def test_exact_hours(self):
        assert _format_seconds(7200) == "2h 0m"

    def test_just_under_a_minute(self):
        assert _format_seconds(59) == "59s"

    def test_exactly_one_minute(self):
        assert _format_seconds(60) == "1m 0s"


class TestRenderer:
    def test_returns_html_string(self, sample_jobs):
        html = render_dashboard(_make_data(sample_jobs))
        assert isinstance(html, str)
        assert html.startswith("<!DOCTYPE html>")

    def test_contains_plotly_cdn(self, sample_jobs):
        html = render_dashboard(_make_data(sample_jobs))
        assert "plotly" in html.lower()

    def test_contains_dashboard_data(self, sample_jobs):
        html = render_dashboard(_make_data(sample_jobs))
        assert "DASHBOARD_DATA" in html

    def test_contains_toggle_buttons(self, sample_jobs):
        html = render_dashboard(_make_data(sample_jobs))
        assert "1 Day" in html
        assert "7 Days" in html

    def test_contains_kpi_section(self, sample_jobs):
        html = render_dashboard(_make_data(sample_jobs))
        assert "Total Jobs" in html

    def test_contains_chart_divs(self, sample_jobs):
        html = render_dashboard(_make_data(sample_jobs))
        for chart_id in [
            "chart-jobs-time", "chart-user-bar", "chart-user-lines",
            "chart-drilldown", "chart-mem-scatter", "chart-wait-overall",
            "chart-wait-user-box", "chart-wait-user-line",
            "chart-cpu-eff", "chart-mem-eff", "chart-node-heat", "chart-failed",
        ]:
            assert chart_id in html, f"Missing chart div: {chart_id}"

    def test_about_modal_present(self, sample_jobs):
        html = render_dashboard(_make_data(sample_jobs))
        assert "about-modal" in html
        assert "About This Dashboard" in html

    def test_footer_present(self, sample_jobs):
        html = render_dashboard(_make_data(sample_jobs))
        assert "Generated:" in html
        assert "class=\"footer\"" in html

    def test_valid_json_in_output(self, sample_jobs):
        html = render_dashboard(_make_data(sample_jobs))
        match = re.search(r"const DASHBOARD_DATA = ({.*?});\n", html, re.DOTALL)
        assert match, "DASHBOARD_DATA not found"
        parsed = json.loads(match.group(1))
        assert parsed["kpis"]["total_jobs"] == 5

    def test_kpi_warn_class_for_moderate_mem_eff(self):
        """mem_efficiency between 0.3 and 0.6 should get kpi-warn."""
        data = aggregate([enrich_job({
            "job_name": "test", "user": "u", "state": "COMPLETED",
            "submit": "2026-03-30T10:00:00", "start": "2026-03-30T10:01:00",
            "end": "2026-03-30T10:02:00", "elapsed": "00:01:00",
            "cpu_time_raw": 60, "alloc_cpus": 1,
            "max_rss_mb": 400.0, "req_mem_mb": 1000.0,
            "node_list": ["n1"],
        })])
        html = render_dashboard(data)
        assert "kpi-warn" in html

    def test_kpi_bad_class_for_low_mem_eff(self):
        """mem_efficiency < 0.3 should get kpi-bad."""
        data = aggregate([enrich_job({
            "job_name": "test", "user": "u", "state": "COMPLETED",
            "submit": "2026-03-30T10:00:00", "start": "2026-03-30T10:01:00",
            "end": "2026-03-30T10:02:00", "elapsed": "00:01:00",
            "cpu_time_raw": 60, "alloc_cpus": 1,
            "max_rss_mb": 10.0, "req_mem_mb": 1000.0,
            "node_list": ["n1"],
        })])
        html = render_dashboard(data)
        assert "kpi-bad" in html


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

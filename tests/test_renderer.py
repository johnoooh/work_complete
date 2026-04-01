# tests/test_renderer.py
from src.renderer import render_dashboard
from src.data_loader import enrich_job
from src.aggregator import aggregate


def _make_data(sample_jobs):
    enriched = [enrich_job(j) for j in sample_jobs]
    return aggregate(enriched)


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

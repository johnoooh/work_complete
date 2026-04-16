# tests/test_chart_js.py
from src.chart_js import get_chart_javascript


class TestGetChartJavascript:
    def test_returns_string(self):
        js = get_chart_javascript()
        assert isinstance(js, str)
        assert len(js) > 1000

    def test_contains_all_render_functions(self):
        js = get_chart_javascript()
        expected = [
            "renderChartJobsTime",
            "renderChartUserBar",
            "renderChartUserLines",
            "renderChartRunningTime",
            "renderDrilldown",
            "renderChartMemScatter",
            "renderChartWaitOverall",
            "renderChartWaitUserBox",
            "renderChartWaitUserLine",
            "renderChartCpuEff",
            "renderChartMemEff",
            "renderChartNodeHeat",
            "renderChartFailed",
            "renderAllCharts",
        ]
        for name in expected:
            assert name in js, f"Missing render function: {name}"

    def test_contains_constants(self):
        js = get_chart_javascript()
        assert "DARK_LAYOUT" in js
        assert "PLOTLY_CONFIG" in js
        assert "STATE_COLORS" in js
        assert "COLORS" in js

    def test_failed_chart_unified_hover(self):
        js = get_chart_javascript()
        assert "hovermode: 'x unified'" in js

    def test_legend_visibility_guard(self):
        js = get_chart_javascript()
        assert "visible === 'legendonly'" in js

    def test_contains_user_filter_functions(self):
        js = get_chart_javascript()
        assert "getVisibleUsers" in js
        assert "toggleUser" in js
        assert "updateChips" in js

    def test_contains_init_charts_function(self):
        js = get_chart_javascript()
        assert "function initCharts" in js

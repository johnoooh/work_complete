# tests/test_aggregator.py
from src.aggregator import aggregate, _percentile, _stats, _hour_key, _date_key
from src.data_loader import enrich_job


def _enrich_all(jobs):
    return [enrich_job(j) for j in jobs]


class TestPercentile:
    def test_empty_list(self):
        assert _percentile([], 0.5) == 0.0

    def test_single_value(self):
        assert _percentile([42], 0.5) == 42

    def test_p50(self):
        assert _percentile([1, 2, 3, 4, 5], 0.5) == 3.0

    def test_p25(self):
        assert _percentile([1, 2, 3, 4, 5], 0.25) == 2.0

    def test_p75(self):
        assert _percentile([1, 2, 3, 4, 5], 0.75) == 4.0

    def test_p0_returns_min(self):
        assert _percentile([10, 20, 30], 0.0) == 10

    def test_p100_returns_max(self):
        assert _percentile([10, 20, 30], 1.0) == 30


class TestStats:
    def test_empty_list(self):
        result = _stats([])
        assert result == {"min": 0, "max": 0, "median": 0, "avg": 0, "p25": 0, "p75": 0}

    def test_known_values(self):
        result = _stats([2, 4, 6, 8, 10])
        assert result["min"] == 2
        assert result["max"] == 10
        assert result["median"] == 6
        assert result["avg"] == 6.0
        assert result["p25"] == 4.0
        assert result["p75"] == 8.0

    def test_single_value(self):
        result = _stats([5])
        assert result["min"] == 5
        assert result["max"] == 5
        assert result["median"] == 5
        assert result["avg"] == 5.0


class TestHourKey:
    def test_extracts_hour(self):
        assert _hour_key("2026-03-30T10:05:00") == "2026-03-30T10"

    def test_different_hour(self):
        assert _hour_key("2026-03-30T23:59:59") == "2026-03-30T23"


class TestDateKey:
    def test_extracts_date(self):
        assert _date_key("2026-03-30T10:05:00") == "2026-03-30"


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

    def test_mem_efficiency_by_user(self, sample_jobs):
        data = aggregate(_enrich_all(sample_jobs))
        assert "mem_eff_by_user" in data
        assert "user_a" in data["mem_eff_by_user"]
        assert len(data["mem_eff_by_user"]["user_a"]) == 2

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

    def test_running_by_user_values(self, sample_jobs):
        data = aggregate(_enrich_all(sample_jobs))
        running = data["running_by_user"]
        # user_a job 100 runs in hour 10, job 101 also runs in hour 10
        assert running["user_a"]["2026-03-30T10"] >= 2

    def test_kpis_by_date(self, sample_jobs):
        data = aggregate(_enrich_all(sample_jobs))
        kpis_date = data["kpis_by_date"]
        assert "2026-03-30" in kpis_date
        assert kpis_date["2026-03-30"]["total_jobs"] == 5
        assert kpis_date["2026-03-30"]["active_users"] == 3

    def test_wait_by_user_hourly_values(self, sample_jobs):
        data = aggregate(_enrich_all(sample_jobs))
        hourly = data["wait_by_user_hourly"]
        # user_a job 100: submit 10:00, start 10:05 → wait 300s
        assert "user_a" in hourly
        assert hourly["user_a"]["2026-03-30T10"] > 0

    def test_process_breakdown_stats_values(self, sample_jobs):
        data = aggregate(_enrich_all(sample_jobs))
        filter_maf = data["process_by_user"]["user_a"]["FILTER_MAF"]
        assert filter_maf["count"] == 1
        assert filter_maf["wait"]["median"] == 300  # 5 min wait
        assert filter_maf["run"]["median"] == 3  # 3s run

    def test_sample_breakdown_avg_elapsed(self, sample_jobs):
        data = aggregate(_enrich_all(sample_jobs))
        samples = data["sample_by_user"]["user_a"]
        # P-0000001-T01-TEST has 2 jobs: 3s and 1320s runs
        sample = samples["P-0000001-T01-TEST"]
        assert sample["count"] == 2
        assert sample["avg_elapsed"] == (3 + 1320) / 2

    def test_empty_jobs(self):
        data = aggregate([])
        assert data["kpis"]["total_jobs"] == 0
        assert data["kpis"]["active_users"] == 0
        assert data["users"] == []
        assert data["all_hours"] == []

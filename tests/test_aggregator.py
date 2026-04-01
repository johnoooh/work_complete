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

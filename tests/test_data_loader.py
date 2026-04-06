# tests/test_data_loader.py
from src.data_loader import load_jobs, enrich_job, _elapsed_to_seconds


class TestElapsedToSeconds:
    def test_zero(self):
        assert _elapsed_to_seconds("00:00:00") == 0

    def test_hours_minutes(self):
        assert _elapsed_to_seconds("01:30:00") == 5400

    def test_minutes_seconds(self):
        assert _elapsed_to_seconds("00:05:30") == 330

    def test_with_days(self):
        assert _elapsed_to_seconds("1-02:00:00") == 93600

    def test_multi_day(self):
        assert _elapsed_to_seconds("3-00:00:00") == 259200


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
        job = {
            "job_name": "quick_job", "submit": "2026-03-30T10:00:00",
            "start": "2026-03-30T10:00:00", "end": "2026-03-30T10:00:00",
            "elapsed": "00:00:00", "cpu_time_raw": 0, "alloc_cpus": 2,
            "max_rss_mb": 0, "req_mem_mb": 100.0,
        }
        assert enrich_job(job)["cpu_efficiency"] == 0.0

    def test_mem_efficiency_zero_requested(self):
        job = {
            "job_name": "no_mem_job", "submit": "2026-03-30T10:00:00",
            "start": "2026-03-30T10:00:00", "end": "2026-03-30T10:00:01",
            "elapsed": "00:00:01", "cpu_time_raw": 1, "alloc_cpus": 1,
            "max_rss_mb": 50.0, "req_mem_mb": 0.0,
        }
        assert enrich_job(job)["mem_efficiency"] == 0.0

    def test_missing_submit_returns_none(self):
        job = {"job_name": "x", "start": "2026-03-30T10:00:00",
               "end": "2026-03-30T10:01:00"}
        assert enrich_job(job) is None

    def test_missing_start_returns_none(self):
        job = {"job_name": "x", "submit": "2026-03-30T10:00:00",
               "end": "2026-03-30T10:01:00"}
        assert enrich_job(job) is None

    def test_missing_end_returns_none(self):
        job = {"job_name": "x", "submit": "2026-03-30T10:00:00",
               "start": "2026-03-30T10:00:00"}
        assert enrich_job(job) is None


class TestLoadJobs:
    def test_loads_all_jobs(self, sample_jobs_json):
        jobs = load_jobs(sample_jobs_json, days=9999)
        assert len(jobs) == 5

    def test_jobs_are_enriched(self, sample_jobs_json):
        jobs = load_jobs(sample_jobs_json, days=9999)
        assert "wait_seconds" in jobs[0]
        assert "process_name" in jobs[0]

    def test_empty_directory(self, tmp_path):
        jobs = load_jobs(tmp_path, days=7)
        assert jobs == []

    def test_filters_to_recent_days(self, tmp_path):
        import json
        from datetime import datetime, timedelta

        today = datetime.now()
        old_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        new_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")

        def make_job(job_id, date):
            return {"job_id": job_id, "job_name": f"job_{job_id}", "user": "u",
                "state": "COMPLETED", "submit": f"{date}T10:00:00",
                "start": f"{date}T10:01:00", "end": f"{date}T10:02:00",
                "elapsed": "00:01:00", "cpu_time_raw": 60, "alloc_cpus": 1,
                "max_rss_mb": 100.0, "req_mem_mb": 1000.0, "partition": "cmobic_cpu",
                "req_cpus": 1, "alloc_mem_mb": 1000.0, "node_list": ["node001"],
                "time_limit": "01:00:00", "total_cpu": "00:01:00.000",
                "base_job_id": job_id, "max_gpu_util": None, "state_by_jobid": None,
                "req_gpu_type": None, "req_gpus": None, "alloc_gpu_type": None,
                "alloc_gpus": None}

        (tmp_path / f"job_{old_date}.json").write_text(json.dumps([make_job("999", old_date)]))
        (tmp_path / f"job_{new_date}.json").write_text(json.dumps([make_job("1000", new_date)]))

        jobs = load_jobs(tmp_path, days=7)
        assert len(jobs) == 1
        assert jobs[0]["job_id"] == "1000"

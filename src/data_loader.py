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
    """Convert HH:MM:SS or D-HH:MM:SS to total seconds."""
    days = 0
    if "-" in elapsed.split(":")[0]:
        day_part, elapsed = elapsed.split("-", 1)
        days = int(day_part)
    parts = elapsed.split(":")
    return days * 86400 + int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])


def enrich_job(job: dict) -> dict | None:
    """Add derived fields to a job record. Returns None if job has missing timestamps."""
    if not job.get("submit") or not job.get("start") or not job.get("end"):
        return None

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
    data_dir = Path(data_dir)
    cutoff = datetime.now() - timedelta(days=days)
    jobs = []

    for filepath in sorted(data_dir.glob("job_*.json")):
        stem = filepath.stem
        try:
            file_date = datetime.strptime(stem.replace("job_", ""), _FILE_DATE_FMT)
        except ValueError:
            continue
        if file_date < cutoff:
            continue
        with open(filepath) as f:
            raw_jobs = json.load(f)
        for raw_job in raw_jobs:
            enriched = enrich_job(raw_job)
            if enriched is not None:
                jobs.append(enriched)

    return jobs

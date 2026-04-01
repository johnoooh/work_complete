# src/aggregator.py
"""Pre-aggregate enriched job data for the dashboard."""

from collections import defaultdict
from statistics import median


def _hour_key(iso_str: str) -> str:
    return iso_str[:13]


def _date_key(iso_str: str) -> str:
    return iso_str[:10]


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    sorted_v = sorted(values)
    k = (len(sorted_v) - 1) * p
    f = int(k)
    c = f + 1 if f + 1 < len(sorted_v) else f
    return sorted_v[f] + (k - f) * (sorted_v[c] - sorted_v[f])


def _stats(values: list[float]) -> dict:
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
    all_dates = sorted({_date_key(j["submit"]) for j in jobs})
    users = sorted({j["user"] for j in jobs})

    user_job_counts = defaultdict(int)
    for j in jobs:
        user_job_counts[j["user"]] += 1

    hourly_total = defaultdict(int)
    hourly_by_user = defaultdict(lambda: defaultdict(int))
    for j in jobs:
        hk = _hour_key(j["submit"])
        hourly_total[hk] += 1
        hourly_by_user[j["user"]][hk] += 1

    all_hours = sorted(hourly_total.keys())

    hourly_wait_values = defaultdict(list)
    for j in jobs:
        hk = _hour_key(j["submit"])
        hourly_wait_values[hk].append(j["wait_seconds"])
    hourly_wait = {hk: _stats(vals) for hk, vals in hourly_wait_values.items()}

    wait_by_user = defaultdict(list)
    for j in jobs:
        wait_by_user[j["user"]].append(j["wait_seconds"])

    hourly_wait_by_user = defaultdict(lambda: defaultdict(list))
    for j in jobs:
        hk = _hour_key(j["submit"])
        hourly_wait_by_user[j["user"]][hk].append(j["wait_seconds"])
    wait_by_user_hourly = {
        user: {hk: sum(vals) / len(vals) for hk, vals in hours.items()}
        for user, hours in hourly_wait_by_user.items()
    }

    cpu_eff_by_user = defaultdict(list)
    for j in jobs:
        cpu_eff_by_user[j["user"]].append(j["cpu_efficiency"])

    mem_eff_by_user = defaultdict(list)
    for j in jobs:
        mem_eff_by_user[j["user"]].append(j["mem_efficiency"])

    mem_scatter = [
        {"req_mem_mb": j["req_mem_mb"], "max_rss_mb": j.get("max_rss_mb", 0) or 0,
         "user": j["user"], "job_name": j["job_name"]}
        for j in jobs
    ]

    node_hour_counts = defaultdict(lambda: defaultdict(int))
    for j in jobs:
        hk = _hour_key(j["submit"])
        for node in j.get("node_list", []):
            node_hour_counts[node][hk] += 1
    all_nodes = sorted(node_hour_counts.keys())
    node_hour_matrix = {
        "nodes": all_nodes, "hours": all_hours,
        "values": [[node_hour_counts[node].get(hk, 0) for hk in all_hours] for node in all_nodes],
    }

    failed_by_user = defaultdict(lambda: defaultdict(int))
    for j in jobs:
        if j["state"] != "COMPLETED":
            failed_by_user[j["user"]][j["state"]] += 1

    process_data = defaultdict(lambda: defaultdict(lambda: {"wait": [], "run": [], "count": 0}))
    for j in jobs:
        entry = process_data[j["user"]][j["process_name"]]
        entry["wait"].append(j["wait_seconds"])
        entry["run"].append(j["run_seconds"])
        entry["count"] += 1
    process_by_user = {
        user: {proc: {"count": d["count"], "wait": _stats(d["wait"]), "run": _stats(d["run"])}
               for proc, d in procs.items()}
        for user, procs in process_data.items()
    }

    sample_data = defaultdict(lambda: defaultdict(lambda: {"count": 0, "elapsed": []}))
    for j in jobs:
        sid = j["sample_id"] or "(no ID)"
        entry = sample_data[j["user"]][sid]
        entry["count"] += 1
        entry["elapsed"].append(j["run_seconds"])
    sample_by_user = {
        user: {sid: {"count": d["count"], "avg_elapsed": sum(d["elapsed"]) / len(d["elapsed"])}
               for sid, d in samples.items()}
        for user, samples in sample_data.items()
    }

    all_wait = [j["wait_seconds"] for j in jobs]
    all_mem_eff = [j["mem_efficiency"] for j in jobs]
    kpis = {
        "total_jobs": len(jobs),
        "active_users": len(users),
        "median_wait": median(all_wait) if all_wait else 0,
        "median_mem_efficiency": median(all_mem_eff) if all_mem_eff else 0,
        "failed_jobs": sum(1 for j in jobs if j["state"] != "COMPLETED"),
    }

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

    return {
        "kpis": kpis, "kpis_by_date": kpis_by_date,
        "users": users, "all_dates": all_dates, "all_hours": all_hours,
        "user_job_counts": dict(user_job_counts),
        "hourly_total": dict(hourly_total),
        "hourly_by_user": {u: dict(h) for u, h in hourly_by_user.items()},
        "hourly_wait": hourly_wait,
        "wait_by_user": dict(wait_by_user),
        "wait_by_user_hourly": wait_by_user_hourly,
        "cpu_eff_by_user": dict(cpu_eff_by_user),
        "mem_eff_by_user": dict(mem_eff_by_user),
        "mem_scatter": mem_scatter,
        "node_hour_matrix": node_hour_matrix,
        "failed_by_user": {u: dict(s) for u, s in failed_by_user.items()},
        "process_by_user": process_by_user,
        "sample_by_user": sample_by_user,
    }

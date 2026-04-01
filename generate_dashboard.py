"""CLI entry point: generate the CMOBIC CPU Queue Dashboard."""

import argparse
from pathlib import Path

from src.aggregator import aggregate
from src.data_loader import load_jobs
from src.renderer import render_dashboard


def main():
    parser = argparse.ArgumentParser(description="Generate CMOBIC CPU Queue Dashboard")
    parser.add_argument("--data-dir", type=Path, required=True,
        help="Directory containing job_YYYY-MM-DD.json files")
    parser.add_argument("--output", type=Path, default=Path("dashboard.html"),
        help="Output HTML file path (default: dashboard.html)")
    args = parser.parse_args()

    if not args.data_dir.is_dir():
        parser.error(f"Data directory not found: {args.data_dir}")

    jobs = load_jobs(args.data_dir, days=7)
    if not jobs:
        print(f"Warning: No job data found in {args.data_dir} for the last 7 days")

    data = aggregate(jobs) if jobs else aggregate([])
    html = render_dashboard(data)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html)
    print(f"Dashboard written to {args.output} ({len(jobs)} jobs from {len(data.get('all_dates', []))} days)")


if __name__ == "__main__":
    main()

"""CLI entry point: generate the CMOBIC CPU Queue Dashboard."""

import argparse
from pathlib import Path

from src.aggregator import aggregate
from src.data_loader import load_jobs
from src.renderer import render_dashboard, render_data_json


def main():
    parser = argparse.ArgumentParser(description="Generate CMOBIC CPU Queue Dashboard")
    parser.add_argument("--data-dir", type=Path, required=True,
        help="Directory containing job_YYYY-MM-DD.json files")
    parser.add_argument("--output", type=Path, default=Path("dashboard.html"),
        help="Output HTML file path (default: dashboard.html)")
    parser.add_argument("--output-json", type=Path, default=None,
        help="Output JSON data file path (default: same as --output with .json extension)")
    args = parser.parse_args()

    if not args.data_dir.is_dir():
        parser.error(f"Data directory not found: {args.data_dir}")

    json_out = args.output_json if args.output_json else args.output.with_suffix(".json")

    jobs = load_jobs(args.data_dir, days=14)
    if not jobs:
        print(f"Warning: No job data found in {args.data_dir} for the last 14 days")

    data = aggregate(jobs) if jobs else aggregate([])
    html = render_dashboard(data)
    json_str = render_data_json(data)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    json_out.parent.mkdir(parents=True, exist_ok=True)

    args.output.write_text(html)
    json_out.write_text(json_str)

    print(f"Dashboard: {args.output} ({len(jobs)} jobs from {len(data.get('all_dates', []))} days)")
    print(f"Data:      {json_out}")


if __name__ == "__main__":
    main()

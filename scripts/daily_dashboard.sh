#!/bin/bash
# Generate the daily CMOBIC CPU Queue Dashboard and update the latest symlink.
#
# Usage:
#   ./scripts/daily_dashboard.sh --data-dir /admin/cmobic_jobs/completed/ --output-dir /admin/cmobic_jobs/
#
# Cron example (daily at 8am):
#   0 8 * * * /data1/core005/ccs/orgeraj/work_complete/work_complete/scripts/daily_dashboard.sh --data-dir /admin/cmobic_jobs/completed/ --output-dir /admin/cmobic_jobs/

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

DATA_DIR=""
OUTPUT_DIR=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --data-dir) DATA_DIR="$2"; shift 2 ;;
        --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

if [[ -z "$DATA_DIR" || -z "$OUTPUT_DIR" ]]; then
    echo "Usage: $0 --data-dir /path/to/jsons --output-dir /path/to/output/"
    exit 1
fi

DATE_STAMP=$(date +"%m_%d")
FILENAME="work_complete_${DATE_STAMP}.html"
JSON_FILENAME="work_complete_${DATE_STAMP}.json"
OUTPUT_PATH="${OUTPUT_DIR%/}/${FILENAME}"
JSON_PATH="${OUTPUT_DIR%/}/${JSON_FILENAME}"
LATEST_LINK="${OUTPUT_DIR%/}/work_complete_dashboard_latest.html"
LATEST_JSON_LINK="${OUTPUT_DIR%/}/work_complete_data_latest.json"

cd "$PROJECT_DIR"
python generate_dashboard.py --data-dir "$DATA_DIR" --output "$OUTPUT_PATH" --output-json "$JSON_PATH"
ln -sf "$OUTPUT_PATH" "$LATEST_LINK"
ln -sf "$JSON_PATH" "$LATEST_JSON_LINK"

echo "Dashboard: $OUTPUT_PATH"
echo "Data:      $JSON_PATH"
echo "Latest:    $LATEST_LINK -> $FILENAME"
echo "Latest:    $LATEST_JSON_LINK -> $JSON_FILENAME"

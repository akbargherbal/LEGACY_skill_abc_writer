#!/usr/bin/env bash
# Refresh the lightweight OSTRIS inputs in the analysis cache.
# Refresh-only: the skill ships a snapshot under 02_maqam-score/data/ostris/.
# The 2.95 GiB audio bundle is never downloaded.
#
#   DATA_ROOT=gs://<bucket> scripts/sync_ostris.sh
#   DATA_ROOT=/path/to/data-root scripts/sync_ostris.sh
set -euo pipefail
cd "$(dirname "$0")/.."

: "${DATA_ROOT:?set DATA_ROOT to the project data root (gs://bucket or a local path)}"
CACHE="${CACHE:-analysis/out/ostris/source}"

python3 02_maqam-score/scripts/ostris_cli.py sync \
  --data-root "$DATA_ROOT" \
  --cache "$CACHE"

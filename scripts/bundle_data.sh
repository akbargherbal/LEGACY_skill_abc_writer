#!/usr/bin/env bash
# Copy the packaged OSTRIS artifacts from the analysis output into the skill.
#
#   scripts/bundle_data.sh [ANALYSIS_OUT]
#
# The skill ships its corpus artifacts under 02_maqam-score/data/ostris/, so the
# reader commands (plan, exemplar, similarity --score, check) work offline with
# no flags.  Regenerating those artifacts still happens under analysis/out; this
# script snapshots the result into the skill package.
#
# Only derived artifacts are copied.  The raw inputs in analysis/out/.../source
# are fetched on demand (make ostris-sync) and must never enter the package:
# they are the largest part of the bundle, are reproducible, and carry unclear
# upstream terms.  The 2.95 GiB audio bundle is never copied either, and
# work/canonical is omitted because it is a second copy of the ABC text.
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
SRC=${1:-"$ROOT/analysis/out/ostris"}
DST="$ROOT/02_maqam-score/data/ostris"

files=(
  records.jsonl
  held_out.jsonl
  audit.json
  canonical.json
  features.json
  manifest_links.csv
  idioms.json
  idioms.jsonl
)
dirs=(
  priors
  eval
)

if [ ! -d "$SRC" ]; then
  echo "bundle: missing $SRC" >&2
  exit 1
fi

for name in "${files[@]}" "${dirs[@]}"; do
  if [ ! -e "$SRC/$name" ]; then
    echo "bundle: missing $SRC/$name" >&2
    exit 1
  fi
done

mkdir -p "$DST/similarity"
for name in "${files[@]}"; do
  cp -a "$SRC/$name" "$DST/$name"
done
for name in "${dirs[@]}"; do
  rm -rf "${DST:?}/$name"
  cp -a "$SRC/$name" "$DST/$name"
done
cp -a "$SRC/similarity/index.json" "$DST/similarity/index.json"
cp -a "$SRC/similarity/similarity.json" "$DST/similarity/similarity.json"

# Drop a raw cache left by an older bundle or a local rebuild.
rm -rf "${DST:?}/source"

# Generated Markdown reports are developer documentation, not skill output.
rm -f "$DST/priors/priors.md"

echo "bundled $(du -sh "$DST" | cut -f1) into ${DST#$ROOT/}"

#!/usr/bin/env bash
# Build the distributable abc_remixer skill archive.
#
#   scripts/package_remixer.sh [--public] [OUT_DIR]
#
# The archive top-level folder is abc_remixer/, matching SKILL.md's name.  The
# runtime modules are copied from the 0.3.0 skill so the installed remixer does
# not depend on a sibling folder at runtime.
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
NAME=abc_remixer
SRC="$ROOT/03_abc_remixer"
SHARED="$ROOT/02_maqam-score/scripts"
PUBLIC=0
OUT="$ROOT/dist"

for arg in "$@"; do
  case "$arg" in
    --public) PUBLIC=1 ;;
    -*) echo "package_remixer: unknown option $arg" >&2; exit 2 ;;
    *) OUT="$arg" ;;
  esac
done

test -f "$SRC/SKILL.md" || { echo "package_remixer: missing $SRC/SKILL.md" >&2; exit 1; }
test -f "$SRC/data/remix/catalog.tsv" || {
  echo "package_remixer: missing data/remix; run 'make remix-build'" >&2; exit 1; }
grep -q "^name: $NAME$" "$SRC/SKILL.md" || {
  echo "package_remixer: SKILL.md must declare 'name: $NAME'" >&2; exit 1; }

mkdir -p "$OUT"
OUT=$(cd "$OUT" && pwd)
STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$STAGE/$NAME"

EXCLUDES=(
  --exclude '__pycache__'
  --exclude '*.pyc'
  --exclude '*.tmp'
)
if [ "$PUBLIC" -eq 1 ]; then
  EXCLUDES+=(--exclude 'data/' --exclude 'tests/')
  ZIP="$OUT/$NAME-public.zip"
else
  ZIP="$OUT/$NAME.zip"
fi

rsync -a "${EXCLUDES[@]}" "$SRC"/ "$STAGE/$NAME"/

# Copy the shared 0.3.0 runtime into scripts/, preserving the layout expected by
# ostris/check.py (scripts/checker.py) and ostris/contract.py.
mkdir -p "$STAGE/$NAME/scripts"
for name in abc_tools.py checker.py calibration.json syllabify.py; do
  test -f "$SHARED/$name" || { echo "package_remixer: missing $SHARED/$name" >&2; exit 1; }
  cp -a "$SHARED/$name" "$STAGE/$NAME/scripts/$name"
done
rm -rf "$STAGE/$NAME/scripts/ostris"
cp -a "$SHARED/ostris" "$STAGE/$NAME/scripts/ostris"

# Optional prior percentiles.  The remixer check still works without them; the
# prior is advisory.
if [ "$PUBLIC" -eq 0 ] && [ -d "$ROOT/02_maqam-score/data/ostris/priors" ]; then
  mkdir -p "$STAGE/$NAME/data/ostris"
  rm -rf "$STAGE/$NAME/data/ostris/priors"
  cp -a "$ROOT/02_maqam-score/data/ostris/priors" "$STAGE/$NAME/data/ostris/priors"
fi

# Hash manifest for the copied runtime.
python3 - "$STAGE/$NAME" <<'PY'
import hashlib, json, sys
from pathlib import Path
root = Path(sys.argv[1])
scripts = root / "scripts"
files = ["abc_tools.py", "checker.py", "calibration.json", "syllabify.py"]
manifest = {"baseline_skill_version": "0.3.0", "files": {}}
for name in files:
    path = scripts / name
    manifest["files"][name] = hashlib.sha256(path.read_bytes()).hexdigest()
ostris = scripts / "ostris"
manifest["ostris_files"] = {
    str(path.relative_to(scripts)): hashlib.sha256(path.read_bytes()).hexdigest()
    for path in sorted(ostris.rglob("*")) if path.is_file()
}
(scripts / "RUNTIME_MANIFEST.json").write_text(
    json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
PY

# Reproducible archive.
EPOCH="${SOURCE_DATE_EPOCH:-0}"
find "$STAGE/$NAME" -exec touch -h -d "@$EPOCH" {} +
rm -f "$ZIP"
(cd "$STAGE" && zip -X -qr "$ZIP" "$NAME")

if zipinfo -1 "$ZIP" | grep -Eq '(^|/)(docs|analysis)/|agent-eval|postmortem'; then
  echo "package_remixer: development files leaked into $ZIP" >&2
  exit 1
fi

echo "wrote ${ZIP#"$ROOT"/} ($(du -h "$ZIP" | cut -f1), $(zipinfo -1 "$ZIP" | wc -l) entries)"

#!/usr/bin/env bash
# Build the distributable Claude skill archive.
#
#   scripts/package_skill.sh [--public] [OUT_DIR]
#
# The archive always has a single top-level directory named after the skill
# (abc_score_writer/), matching SKILL.md's `name`.  Developer-only files are
# excluded: CHANGELOG.md, the bundle notes, generated Markdown reports and
# __pycache__.  Tests, schemas and references stay in.
#
# --public also drops the bundled corpus (02_maqam-score/data/); see
# docs/ostris-licensing.md.
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
NAME=abc_score_writer
SRC="$ROOT/02_maqam-score"
PUBLIC=0
OUT="$ROOT/dist"

for arg in "$@"; do
  case "$arg" in
    --public) PUBLIC=1 ;;
    -*) echo "package: unknown option $arg" >&2; exit 2 ;;
    *) OUT="$arg" ;;
  esac
done

test -f "$SRC/SKILL.md" || { echo "package: missing $SRC/SKILL.md" >&2; exit 1; }
grep -q "^name: $NAME$" "$SRC/SKILL.md" || {
  echo "package: SKILL.md must declare 'name: $NAME'" >&2
  exit 1
}

mkdir -p "$OUT"
OUT=$(cd "$OUT" && pwd)
STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$STAGE/$NAME"

EXCLUDES=(
  --exclude '__pycache__'
  --exclude '*.pyc'
  --exclude 'CHANGELOG.md'
  --exclude 'data/README.md'
)
if [ "$PUBLIC" -eq 1 ]; then
  EXCLUDES+=(--exclude 'data/')
  ZIP="$OUT/$NAME-public.zip"
else
  ZIP="$OUT/$NAME.zip"
fi

rsync -a "${EXCLUDES[@]}" "$SRC"/ "$STAGE/$NAME"/
rm -f "$ZIP"
(cd "$STAGE" && zip -qr "$ZIP" "$NAME")

# The skill package is a runtime artifact. Development material (docs/, the
# evaluation protocol, post-mortems, analysis/) must never leak into it.
if zipinfo -1 "$ZIP" | grep -Eq '(^|/)(docs|analysis)/|agent-eval|postmortem'; then
  echo "package: development files leaked into $ZIP" >&2
  exit 1
fi

echo "wrote ${ZIP#"$ROOT"/} ($(du -h "$ZIP" | cut -f1), $(zipinfo -1 "$ZIP" | wc -l) entries)"

#!/usr/bin/env bash
# Build the distributable Claude skill archive.
#
#   scripts/package_skill.sh [--public] [OUT_DIR]
#
# The archive always has a single top-level directory named after the skill
# (abc-score-writer/), matching SKILL.md's `name`.  Developer-only files are
# excluded: CHANGELOG.md, the bundle notes, generated Markdown reports and
# __pycache__.  Tests, schemas and references stay in.
#
# --public also drops the bundled corpus (02_maqam-score/data/); see
# docs/ostris-licensing.md.
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
NAME=abc-score-writer
SRC="$ROOT/02_maqam-score"
DOC=${SKILL_MD:-SKILL.md}
PUBLIC=0
OUT="$ROOT/dist"

for arg in "$@"; do
  case "$arg" in
    --public) PUBLIC=1 ;;
    -*) echo "package: unknown option $arg" >&2; exit 2 ;;
    *) OUT="$arg" ;;
  esac
done

test -f "$SRC/$DOC" || { echo "package: missing $SRC/$DOC" >&2; exit 1; }
grep -q "^name: $NAME$" "$SRC/$DOC" || {
  echo "package: $DOC must declare 'name: $NAME'" >&2
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
  --exclude '.pytest_cache'
  --exclude '.ruff_cache'
  --exclude '.mypy_cache'
  --exclude 'CHANGELOG.md'
  --exclude 'data/README.md'
  --exclude 'SKILL-v*.md'
)
if [ "$PUBLIC" -eq 1 ]; then
  EXCLUDES+=(--exclude 'data/')
  ZIP="$OUT/$NAME-public.zip"
else
  ZIP="$OUT/$NAME.zip"
fi

rsync -a "${EXCLUDES[@]}" "$SRC"/ "$STAGE/$NAME"/
# Build a preview from an alternate SKILL document, still named SKILL.md in
# the package (historical versions are kept in-tree as SKILL-v<version>.md).
if [ "$DOC" != "SKILL.md" ]; then
  cp "$SRC/$DOC" "$STAGE/$NAME/SKILL.md"
fi
# Reproducible archive: fixed mtimes and no host-specific extra attributes.
# Two builds of the same source produce the same sha256.
EPOCH="${SOURCE_DATE_EPOCH:-0}"
find "$STAGE/$NAME" -exec touch -h -d "@$EPOCH" {} +
rm -f "$ZIP"
(cd "$STAGE" && zip -X -qr "$ZIP" "$NAME")

# The skill package is a runtime artifact. Development material (docs/, the
# evaluation protocol, post-mortems, analysis/) must never leak into it.
if zipinfo -1 "$ZIP" | grep -Eq '(^|/)(docs|analysis)/|agent-eval|postmortem'; then
  echo "package: development files leaked into $ZIP" >&2
  exit 1
fi

echo "wrote ${ZIP#"$ROOT"/} ($(du -h "$ZIP" | cut -f1), $(zipinfo -1 "$ZIP" | wc -l) entries)"

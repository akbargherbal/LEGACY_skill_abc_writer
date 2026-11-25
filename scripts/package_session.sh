#!/usr/bin/env bash
# Build the session-12 drop: the skill, the input, the one-line prompt, and
# the agent/plugin configuration. No task.md.
#
#   scripts/package_session.sh [OUT_DIR]
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
OUT=${1:-"$ROOT/dist"}
NAME=session-12
SRC="$ROOT/session_template"
PROMPT='Write the abc score for style+lyrics in @input/lyrics.txt'

test -f "$ROOT/02_maqam-score/SKILL.md" || { echo "package_session: missing skill" >&2; exit 1; }
test -f "$SRC/opencode.json" || { echo "package_session: missing $SRC/opencode.json" >&2; exit 1; }

mkdir -p "$OUT"
OUT=$(cd "$OUT" && pwd)
STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT

# Build the current skill into a private staging directory, then extract it.
SKILL_STAGE="$STAGE/skillzip"
mkdir -p "$SKILL_STAGE"
"$ROOT/scripts/package_skill.sh" "$SKILL_STAGE" > /dev/null
mkdir -p "$STAGE/$NAME/skills"
unzip -q "$SKILL_STAGE/abc-score-writer.zip" -d "$STAGE/$NAME/skills"

# Input + agent/plugin configuration. No task.md.
rsync -a --exclude '.opencode/agents/*.md.bak' "$SRC"/ "$STAGE/$NAME"/
printf '%s\n' "$PROMPT" > "$STAGE/PROMPT.txt"

cat > "$STAGE/README.md" <<'MD'
# session-12

The same prompt as session 11, with one change: the composer writes the score
through `score_cli.py`, one lyric line at a time. There is no task.md.

```bash
unzip session-12-ready.zip
cd session-12
opencode --auto
# paste PROMPT.txt (outside this directory)
```

What is pinned:

- `opencode.json` selects `deepseek/deepseek-flash#high` and `composer`.
- `.opencode/plugins/abc-guard.js` forces that model for every primary request
  and caps a model call at 8,000 output tokens; it appends the actual model to
  `abc-session.log`.
- `.opencode/agents/composer.md` cannot edit `score.abc`; it must use the CLI.
- `.opencode/agents/verifier.md` is a read-only checker; `packager.md` owns the
  seed/docs after the score freezes.

After the run, export the chat JSON and measure:

```bash
python3 /path/to/skill_abc_writer/analysis/measure_session.py opencode_session_12.json \
  --score session-12/score.abc --max-ratio 10 --max-message 8000
```

Target: <=25,000 generated tokens (<=13x), stretch <=19,400 (10x); no message
above 8,000; 0 hand-written scripts; <=4 checker runs; 0 direct score writes.
MD

# Reproducible archive.
EPOCH="${SOURCE_DATE_EPOCH:-0}"
find "$STAGE" -exec touch -h -d "@$EPOCH" {} +
ZIP="$OUT/session-12-ready.zip"
rm -f "$ZIP"
(cd "$STAGE" && zip -X -qr "$ZIP" "$NAME" PROMPT.txt README.md)
echo "wrote ${ZIP#"$ROOT"/} ($(du -h "$ZIP" | cut -f1))"

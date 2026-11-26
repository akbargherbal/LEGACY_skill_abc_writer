#!/usr/bin/env bash
# Build a session drop: the skill, the input, the one-line prompt, and the
# agent/plugin configuration. No task.md.
#
#   SESSION_NAME=session-14 SESSION_STEPS=40 scripts/package_session.sh [OUT_DIR]
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
OUT=${1:-"$ROOT/dist"}
NAME=${SESSION_NAME:-session-14}
STEPS=${SESSION_STEPS:-40}
VARIANT=${SESSION_VARIANT:-high}
COMPOSER_DOC=${COMPOSER_DOC:-composer.md}
SKILL_DOC=${SKILL_DOC:-SKILL.md}
SRC="$ROOT/session_template"
PROMPT='Write the abc score for style+lyrics in @input/lyrics.txt'

test -f "$ROOT/02_maqam-score/$SKILL_DOC" || { echo "package_session: missing skill doc $SKILL_DOC" >&2; exit 1; }
test -f "$SRC/opencode.json" || { echo "package_session: missing $SRC/opencode.json" >&2; exit 1; }
test -f "$SRC/.opencode/agents/$COMPOSER_DOC" || { echo "package_session: missing agent $COMPOSER_DOC" >&2; exit 1; }
case "$STEPS" in
  ''|*[!0-9]*) echo "package_session: SESSION_STEPS must be a positive integer" >&2; exit 2 ;;
esac

mkdir -p "$OUT"
OUT=$(cd "$OUT" && pwd)
STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT

# Build the current skill into a private staging directory, then extract it.
SKILL_STAGE="$STAGE/skillzip"
mkdir -p "$SKILL_STAGE"
SKILL_MD="$SKILL_DOC" "$ROOT/scripts/package_skill.sh" "$SKILL_STAGE" > /dev/null
mkdir -p "$STAGE/$NAME/skills"
unzip -q "$SKILL_STAGE/abc-score-writer.zip" -d "$STAGE/$NAME/skills"

# Input + agent/plugin configuration. No task.md.
rsync -a --exclude '.opencode/agents/*.md.bak' "$SRC"/ "$STAGE/$NAME"/
# Promote the chosen whole-draft agent to composer.md.
if [ "$COMPOSER_DOC" != "composer.md" ]; then
  cp "$STAGE/$NAME/.opencode/agents/$COMPOSER_DOC" "$STAGE/$NAME/.opencode/agents/composer.md"
  rm -f "$STAGE/$NAME/.opencode/agents/$COMPOSER_DOC"
fi
# Archived workflow agents never ship in a session drop.
rm -f "$STAGE/$NAME/.opencode/agents/"*-v0.9.md
sed -i "s/^steps: [0-9][0-9]*\$/steps: $STEPS/" "$STAGE/$NAME/.opencode/agents/composer.md"
# Pin the requested thinking variant in the config, every agent, and the guard.
sed -i "s|deepseek/deepseek-flash#[a-z]*|deepseek/deepseek-flash#$VARIANT|g" \
  "$STAGE/$NAME/opencode.json" "$STAGE/$NAME/.opencode/agents/"*.md
sed -i "s/variant: \"[a-z]*\"/variant: \"$VARIANT\"/" "$STAGE/$NAME/.opencode/plugins/abc-guard.js"
printf '%s\n' "$PROMPT" > "$STAGE/PROMPT.txt"

# The skill's own version line, so the drop README cannot drift from SKILL.md.
SKILL_VERSION=$(sed -n 's/^version: "\([^"]*\)"/\1/p' "$ROOT/02_maqam-score/$SKILL_DOC" | head -1)

cat > "$STAGE/README.md" <<MD
# $NAME

The 1.0 whole-draft loop in a clean room: \`init\` -> whole draft -> scorecard
-> whole rewrite -> scorecard -> seams -> release. One process change from
session 15: thinking is **$VARIANT**, not high. Steps: $STEPS. Skill: $SKILL_VERSION.
Agent: whole-draft \`composer.md\`.

\`\`\`bash
unzip $NAME-ready.zip
cd $NAME
opencode --auto
# paste PROMPT.txt (outside this directory)
\`\`\`

Start in a **new empty directory**. The zip has no \`plan.json\`,
\`phrases.json\` or \`score.abc\`. If you unzip over an old folder, stale files
survive and \`init\` will refuse to run; that is a dirty run, not a composer
error.

What is pinned:

- \`opencode.json\` selects \`deepseek/deepseek-flash#$VARIANT\` and \`composer\`.
- \`.opencode/plugins/abc-guard.js\` forces that model and variant on every
  primary request, caps a call at 8,000 output tokens, and appends the actual
  model to \`abc-session.log\`.
- \`.opencode/agents/composer.md\` has \`steps: $STEPS\` and may write
  \`score.abc\` only as a whole file.
- \`.opencode/agents/verifier.md\` is a read-only checker; \`packager.md\` owns
  the seed/docs after the score freezes.

Run validity (check before interpreting anything):

1. \`init\` runs and prints \`FORM BUDGET: 64 bars vs syllabify 82 (-22%)\`.
2. The composer keeps 64 or reruns with \`--force --bars 82 --sections\`; a
   bare \`--bars\` is a form error.
3. One session id; export the complete chat JSON.
4. The score is written whole; no \`sed\`/Python edits of \`score.abc\`.

After the run, export the chat JSON and measure:

\`\`\`bash
python3 /path/to/skill_abc_writer/analysis/measure_session.py opencode_session_${NAME##*-}.json \\
  --score $NAME/score.abc --max-ratio 10 --max-message 8000
\`\`\`

Target: generated (\`output + reasoning\`) <=10x the final \`score.abc\` tokens;
0 blocking at release; at most 4 whole drafts; no patch-by-bar. Seed/docs are
diagnostics, not the ratio.

Known false warning: \`section plan metrics\` uses the auto plan's \`[0,3]\`
\`vocal_notes_per_bar\` band, which is too low for dense syllabic verse. Do not
rewrite the score to chase it.
MD

# Reproducible archive.
EPOCH="${SOURCE_DATE_EPOCH:-0}"
find "$STAGE" -exec touch -h -d "@$EPOCH" {} +
ZIP="$OUT/$NAME-ready.zip"
rm -f "$ZIP"
(cd "$STAGE" && zip -X -qr "$ZIP" "$NAME" PROMPT.txt README.md)
echo "wrote ${ZIP#"$ROOT"/} ($(du -h "$ZIP" | cut -f1))"

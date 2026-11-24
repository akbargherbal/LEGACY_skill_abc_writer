#!/usr/bin/env bash
# Prove the bundled tools work before the skill relies on them.
# Runs on the example only: no network, no renderer, no ABC toolchain.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== syllabify: example"
out=$(python3 scripts/syllabify.py example/lyrics.txt --tempo 80)
echo "$out" | head -12
grep -q "syllables        16" <<<"$out" || { echo "FAIL: example syllables != 16"; exit 1; }

echo "== checker: example must pass strict shape and strict style"
python3 scripts/checker.py example/score.abc --plan example/plan.json \
  --phrases example/phrases.json --require-final-rest --strict-style

echo "== checker: a short bar must fail"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
sed 's/F2 F2 A8 G2 F2|/F2 F2 A8 G2|/' example/score.abc > "$tmp/broken.abc"
if python3 scripts/checker.py "$tmp/broken.abc" > "$tmp/out" 2>&1; then
  echo "FAIL: the checker accepted an incomplete bar"; cat "$tmp/out"; exit 1
fi
grep -qE 'sums to|meter duration|duration [0-9]+ quarter' "$tmp/out" || {
  echo "FAIL: wrong error for a short bar"; cat "$tmp/out"; exit 1; }
echo "correctly rejected: $(grep -m1 -E 'sums to|meter duration|duration [0-9]+ quarter' "$tmp/out")"

echo "== checker: a missing final rest warns by default, fails with --require-final-rest"
python3 - <<'PY' > "$tmp/noend.abc"
from pathlib import Path
lines = Path("example/score.abc").read_text(encoding="utf-8").splitlines()
lines[-1] = lines[-1].replace("|Z|", "|D,16|")
print("\n".join(lines))
PY
if ! python3 scripts/checker.py "$tmp/noend.abc" --plan example/plan.json > "$tmp/out" 2>&1; then
  echo "FAIL: the default checker rejected a score for the final rest alone"; cat "$tmp/out"; exit 1
fi
grep -q "WARN.*final rest" "$tmp/out" || {
  echo "FAIL: the missing final rest did not warn"; cat "$tmp/out"; exit 1; }
if python3 scripts/checker.py "$tmp/noend.abc" --plan example/plan.json --require-final-rest > "$tmp/out" 2>&1; then
  echo "FAIL: --require-final-rest accepted a score without a final rest"; cat "$tmp/out"; exit 1
fi
grep -q "FAIL.*final rest" "$tmp/out" || {
  echo "FAIL: wrong error for a missing final rest"; cat "$tmp/out"; exit 1; }
echo "correctly warned then rejected: $(grep -m1 'final rest' "$tmp/out")"

echo "== checker: a blank line must fail the runtime parser"
python3 - <<'PY' > "$tmp/blank.abc"
lines = open("example/score.abc", encoding="utf-8").read().splitlines()
out = []
inserted = False
for line in lines:
    out.append(line)
    if not inserted and line == "A,2 A,2 A,2 C2 A,2 A,2 G,2 A,2|":
        out.append("")
        inserted = True
print("\n".join(out))
PY
if python3 scripts/checker.py "$tmp/blank.abc" > "$tmp/out" 2>&1; then
  echo "FAIL: the checker accepted a blank line in the body"; cat "$tmp/out"; exit 1
fi
grep -q 'runtime parse' "$tmp/out" || {
  echo "FAIL: a blank line did not reach the runtime parser"; cat "$tmp/out"; exit 1; }
echo "correctly rejected: $(grep -m1 'runtime parse' "$tmp/out")"

echo "== checker: a two-note answer warns by default, fails with --strict-style"
sed 's/Z|A,2 A,2 C2 A,2 G,2 F,2 G,2 A,2|Z|/Z|A,4 C4 z8|Z|/' example/score.abc > "$tmp/shortfill.abc"
if ! python3 scripts/checker.py "$tmp/shortfill.abc" --plan example/plan.json > "$tmp/out" 2>&1; then
  echo "FAIL: the default checker rejected a two-note answer"; cat "$tmp/out"; exit 1
fi
grep -q "WARN.*answer fill length" "$tmp/out" || {
  echo "FAIL: the two-note answer did not warn"; cat "$tmp/out"; exit 1; }
if python3 scripts/checker.py "$tmp/shortfill.abc" --plan example/plan.json --strict-style > "$tmp/out" 2>&1; then
  echo "FAIL: --strict-style accepted a two-note answer"; cat "$tmp/out"; exit 1
fi
grep -q "FAIL.*answer fill length" "$tmp/out" || {
  echo "FAIL: wrong error for a two-note answer"; cat "$tmp/out"; exit 1; }
echo "correctly warned then rejected: $(grep -m1 'answer fill length' "$tmp/out")"

echo
echo "selftest: PASS"

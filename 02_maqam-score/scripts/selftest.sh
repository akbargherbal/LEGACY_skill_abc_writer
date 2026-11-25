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

echo "== verify_package: example score + plan"
python3 scripts/verify_package.py --score example/score.abc --plan example/plan.json \
  --json "$tmp/verify.json"

echo "== verify_package: a short bar must fail"
if python3 scripts/verify_package.py --score "$tmp/broken.abc" --plan example/plan.json \
    --json "$tmp/verify_bad.json"; then
  echo "FAIL: verify_package accepted a short bar"; exit 1
fi
grep -q '"tag": "FAIL"' "$tmp/verify_bad.json" || {
  echo "FAIL: verify.json has no FAIL for a short bar"; exit 1; }
echo "correctly rejected: $(grep -m1 '"name"' "$tmp/verify_bad.json")"

echo "== craft: example"
python3 scripts/craft.py example/score.abc --json "$tmp/craft.json" > /dev/null
grep -q '"rows"' "$tmp/craft.json" || { echo "FAIL: craft.json missing rows"; exit 1; }
echo "craft report ok"

echo "== craft: per-line phrase table"
python3 scripts/craft.py example/score.abc --phrases example/phrases.json   --json "$tmp/craft_phrases.json" > "$tmp/phrases.out"
grep -q "per-line phrase table" "$tmp/phrases.out" || { echo "FAIL: no phrase table"; exit 1; }
grep -q '"phrase_table"' "$tmp/craft_phrases.json" || { echo "FAIL: phrase_table missing"; exit 1; }
echo "phrase table ok"

echo "== quality: objective layer (the example may fail; it must report)"
python3 scripts/quality.py example/score.abc --plan example/plan.json   --phrases example/phrases.json --json "$tmp/quality.json" > "$tmp/quality.out" || true
grep -q '"checks"' "$tmp/quality.json" || { echo "FAIL: quality.json missing checks"; exit 1; }
echo "quality report ok"

echo "== repair: map without a report"
python3 scripts/repair.py example/score.abc --plan example/plan.json   --phrases example/phrases.json --json "$tmp/repair.json" > /dev/null
grep -q '"maps"' "$tmp/repair.json" || { echo "FAIL: repair.json missing maps"; exit 1; }
echo "repair map ok"

echo "== doctor: example parses, a bad block explains itself"
python3 scripts/abc_doctor.py example/score.abc > /dev/null
cat > "$tmp/badblock.abc" <<'ABC'
X:1
T:
M:4/4
L:1/16
Q:1/4=80
V: Vocal clef=treble name="Vocal Melody" snm="Vocal"
V: Ins clef=treble name="Ins Melody" snm="Inst."
K:Dm
V: Vocal
D4 E4 F4 G4|A4 B4 c4 d4|
V: Ins
D4 E4 F4 G4|
ABC
if python3 scripts/abc_doctor.py "$tmp/badblock.abc" > "$tmp/doctor.out" 2>&1; then
  echo "FAIL: doctor accepted a mismatched block"; exit 1
fi
grep -q "different measure counts" "$tmp/doctor.out" || { echo "FAIL: doctor did not explain the block"; exit 1; }
echo "doctor ok"

echo
echo "selftest: PASS"

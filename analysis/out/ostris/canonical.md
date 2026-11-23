# OSTRIS M1 canonical build

- Generated: `2026-11-23T06:52:13+00:00`
- Gate: **PASS**
- Canonical ABCs: 482/482 (1.8 MB)
- Skill contract: v0.2.0 (pinned)

## Checks

| Check | Required | OK | Detail |
|---|---|---|---|
| canonical_coverage | yes | yes | 482/482 canonical and re-parsed |
| two_voice_shape | yes | yes | Vocal+Ins: 482 |
| contract_pin | yes | yes | skill 0.2.0 pins match: scripts/checker.py=ok, scripts/calibration.json=ok, scripts/abc_tools.py=ok |
| unique_canonical_hashes | no | yes | all canonical hashes unique |

## Voice / meter shape

- voices `Vocal+Ins`: 482
- declared meters `4/4`: 174
- declared meters `2/4`: 165
- declared meters `4/4;2/4`: 29
- declared meters `2/4;1/4`: 23
- declared meters `4/4;1/4`: 14
- declared meters `4/4;3/4`: 12
- declared meters `2/4;1/8`: 9
- declared meters `4/4;3/8`: 6
- declared meters `4/4;1/4;3/4`: 6
- declared meters `6/8`: 5
- declared meters `4/4;3/4;1/4`: 5
- declared meters `4/4;1/8`: 3
- declared meters `4/4;5/8`: 3
- declared meters `3/4`: 3
- declared meters `2/4;3/8`: 2
- declared meters `4/4;1/4;2/4`: 2
- declared meters `4/4;9/8;1/4`: 1
- declared meters `5/8;2/4`: 1
- declared meters `4/4;3/4;3/8;1/4`: 1
- declared meters `4/4;1/4;1/8`: 1
- declared meters `2/4;1/8;3/8`: 1
- declared meters `4/4;3/8;1/4;2/4`: 1
- declared meters `4/4;3/8;2/4`: 1
- declared meters `2/4;5/8`: 1
- declared meters `4/4;7/8`: 1
- declared meters `4/4;1/4;3/8`: 1
- declared meters `2/8;1/8;6/8`: 1
- declared meters `4/4;3/4;2/4;1/4`: 1
- declared meters `4/4;2/4;3/4;5/8`: 1
- declared meters `4/4;2/4;3/4`: 1
- declared meters `4/4;9/8`: 1
- declared meters `2/4;4/4`: 1
- declared meters `4/4;3/4;7/8`: 1
- declared meters `4/4;2/4;3/8`: 1
- declared meters `4/4;2/4;1/4`: 1
- declared meters `4/4;1/8;3/4;2/4`: 1
- declared meters `3/4;4/4`: 1

Canonicalization is structural: line endings and trailing whitespace are
normalized; music lines, per-bar `M:`, and inline `[K:...]` are preserved.
The per-track hash is in `records.jsonl` under `canonical`.

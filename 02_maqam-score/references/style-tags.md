# Style-tag translation

A style tag is a prompt/LoRA instruction. The score can only choose the part it
owns: structure, prosody, gaps, density, register, repetition. Translate each
tag into a **score decision** and, where possible, a measured target. Keep the
target `style`/`strict_shape`; never turn it into a corpus sanity guard.

| Tag | Score decision | Measured by |
|---|---|---|
| belting, operatic, powerful | 2–3 planned peaks, not a high tessitura throughout; chorus median +5 in release mode; `tessitura_share_ge_c5_max 0.80`; `max_top 86` | register, tessitura, chorus lift median |
| tarab, melismatic, ornaments | melisma at cadences (about 1.15–1.30 notes/syllable), not on every syllable; one gesture per phrase; write the place for the ornament | melisma band, phrase plan |
| call and response | lead and backing as the two voices; the Ins answer sits in a vocal rest; no overlap | simultaneity, answer fill |
| symphonic metal, heavy, epic | Ins density/register, not the vocal; do not add a third voice | Ins active share, two-voice contract |
| backing vocals, choir, layered harmonies | the LoRA performs them; the score remains two voices | contract |
| microtonal, quarter-tone, maqam ornament | not encodable in this dialect; keep the intonation in the prompt and write the place (a long note, a rest, a cadential turn) | reference §9/§10 |
| somber, night dread | tempo, register, and gap rate; not a score gate | plan / listener |

Rules:

1. A tag never overrides a user request ("less melisma" wins).
2. A tag never justifies a missed breath, tessitura, duration, or ending
   target. Those are quality targets, not arrangement deviations.
3. Do not claim the score encoded timbre, mix, microtones, or ornament quality.
   It encoded a place for the renderer to perform them.
4. If a tag conflicts with the corpus shape, prefer the user's brief and record
   the deviation; do not edit `calibration.json`.

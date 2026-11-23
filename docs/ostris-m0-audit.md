# OSTRIS M0 audit — result

**Date:** 2026-11-23 · **Stage:** M0 (audit & contracts) · **Gate:** PASS

The separate-repository proposal is dropped. The corpus tools live in the skill:

| Path | Role |
|---|---|
| `02_maqam-score/scripts/ostris/` | Offline corpus code (`sync`, `audit`) and the future online helpers |
| `02_maqam-score/scripts/ostris_cli.py` | Entry point: `python3 scripts/ostris_cli.py …` |
| `02_maqam-score/schemas/` | `track_record` and `audit` JSON contracts |
| `analysis/out/ostris/` | Generated evidence (outputs committed; source cache ignored) |

## Reproduce

```bash
DATA_ROOT=gs://<bucket> make ostris-sync
make ostris-audit
```

`ostris-sync` copies only manifests, the 25 YT500 ABC shards, the 15 FADL album
JSONs, the 22-track FADL shortlist, and the reference ABCs. The 2.95 GiB audio
bundle is never downloaded. `ostris-audit` then runs offline.

## Verified inventory

| Asset | Expected | Observed |
|---|---:|---:|
| Instrumental library | 482 | **482** (460 YT500 + 22 FADL) |
| Audio bytes / hours | 3,162,110,202 / 36.6 | **match** (2.95 GiB) |
| YT500 manifest tracks | 495 | **495** |
| YT500 shard files / tracks | 25 / 495 | **25 / 495** |
| YT500 transcripts with ABC | — | **491** (4 `no-abc`) |
| Duplicate groups / tracks | 5 / 10 | **5 / 10** |
| YT500 held-out (unused) | 35 | **35** |
| FADL shortlist | 22 | **22** |
| FADL selected-score tracks | — | **24** (23 with ABC) |
| FADL album set | 15 albums | **15 / 140 tracks / 132 with ABC** |
| v3 maqam labels (cross-check only) | 438 | **438** (Ajam 118, Hijaz 107, Kurd 101, Nahawand 112) |

## Links and parse

- **482/482** library tracks matched: 460 by `video_id`, 22 by shortlist name.
- **482/482** primary ABCs parse with the vendored `abc_tools.py` (100%).
  The four YT500 `no-abc` tracks are all in the 35-track held-out set, so the
  library has no missing ABC.
- **10** tracks are excluded from priors: 9 library tracks in the 5 duplicate
  groups, plus one sparse-`Ins` track (`yt500-0350-QGm0xMfCdw0`). The tenth
  duplicate is held out.
- **472** tracks are prior candidates before maqam labelling and quality
  weighting.

## FADL finding

The exact 22-track link is not the 15-album `TRANSCRIPTS/FADL_SHAKER` set. It is:

1. `DATASET/fadhl_shaker_instrumental_18_shortlist/shortlist.json`, then
2. `TRANSCRIPTS/fadhl_shaker_selected_scores` (24 tracks, 23 with ABC), then
3. the reference conditioner ABC in `DATASET/fadhl_shaker_instrumental_18/abc/`
   when the selected transcript is missing.

One track (`al_qissa_wama_fiha`) has no selected-scores ABC; the audit falls back
to its conditioner and flags `selected_status_no-abc` + `no_vocal_notes`. This is
acceptable for instrumental priors (the `Ins` line and chords are present) but
must not be treated as a vocal reference.

## Corpus shape (parsed library, n=482)

| Measure | p25 | median | p75 | range |
|---|---:|---:|---:|---:|
| Bars | 115 | **150** | 183.75 | 57–296 |
| Tempo (BPM) | 77 | **90** | 114 | 57–158 |
| Vocal notes | 438 | **525** | 615.75 | 0–1064 |
| Ins notes | 171.25 | **232.5** | 310.75 | 0–1269 |
| Chords | 138.5 | **170** | 198.75 | 73–360 |
| Density (notes/bar) | 4.152 | **5.304** | 6.691 | 2.595–10.561 |
| Vocal silence (bar share) | 0.275 | **0.331** | 0.385 | 0.045–1.0 |
| Duration mismatch | 0.8% | **1.8%** | 3.8% | 0–21.7% |
| Quality score | 1.0 | **1.0** | 1.0 | 0.8–1.0 |

- **11 meters**: 4/4 (271), 2/4 (242), 1/4 (57), 3/4 (33), 1/8 (16), 3/8 (14),
  6/8 (6), 5/8 (6), 9/8 (2), 7/8 (2), 2/8 (1). Tracks may change meter.
- **21 keys**, overwhelmingly minor: Cm 60, Em 59, Gm 54, Am 51, Dm 45, Fm 40,
  Bbm 37, Bm 26, F#m 24, D#m 23, G#m 20, C#m 18, plus majors/minor outliers.
- **Chords are present in every parsed track** (73–360 symbols). Unlike the 177
  ABCs, this corpus can support harmony priors.

## Gate checks

All required checks pass: counts, audio inventory, link coverage, held-out,
duplicates, v3 labels, parse coverage, and prior-candidate coverage (472/482 =
97.9%, above the 90% non-required target).

## What M0 does *not* decide

M0 records no maqam labels and builds no priors, plan, idioms, or check. The
following decisions gate the next stages (plan §13.3):

- **before M1:** D5/D6/D7/D9/D14 — **resolved 2026-11-23** in
  `docs/ostris-decisions.md`; M1 is implemented in `docs/ostris-m1-ingest.md`;
- **before M2:** D3/D4/D11/D12/D16 (maqam review, v3 role, 177 role, coverage
  definition, sanity scope) — D4/D11/D16 resolved; D3/D12 deferred because no
  expert maqam review is available. See `docs/ostris-m2-features.md`;
- **before M4/M5:** D8/D10/D15 (gate policy, report merge, final rest);
- **before M6:** D1/D2/D13 (quality target, held-out use, held-out source).

One M0 fact changes the M6 input: the 35 held-out tracks include **4 without
ABC**, leaving **31** usable for generation/retrieval evaluation.

# OSTRIS M0 audit

- Generated: `2026-11-23T06:51:34+00:00`
- Cache: `/content/skill_abc_writer/analysis/out/ostris/source`
- Gate: **PASS**

## Inventory

| Item | Value |
|---|---:|
| Instrumental library | 482 |
| YT500 manifest tracks | 495 |
| YT500 shard tracks | 495 |
| YT500 transcripts missing ABC | 4 |
| FADL shortlist | 22 |
| FADL selected-score tracks | 24 |
| FADL album set | 15 albums / 140 tracks |
| v3 maqam labels (excluded from priors) | 438 |

## Links and parse

| Item | Value |
|---|---:|
| Library tracks | 482 |
| Matched | 482 |
| Unmatched | 0 |
| Missing primary ABC | 0 |
| FADL tracks without a selected transcript | 1 |
| ABC parse OK | 482 (100.0%) |
| ABC parse failures | 0 |
| Excluded from priors | 10 |

## Gate checks

| Check | OK | Detail |
|---|---|---|
| instrumental_count | yes | 482 (expected 482) |
| audio_inventory | yes | 3162110202 bytes, 36.6 h |
| yt500_transcribed | yes | 495 transcribed (expected 495) |
| yt500_link_coverage | yes | 460/460 matched |
| fadl_link_coverage | yes | 22/22 matched |
| held_out_count | yes | 35 unused YT500 transcripts (expected 35) |
| duplicate_inventory | yes | 5 groups / 10 tracks |
| v3_label_counts | yes | 438 labels: {'Ajam': 118, 'Hijaz': 107, 'Kurd': 101, 'Nahawand': 112} |
| parse_coverage | yes | 482/482 = 100.0% |
| prior_candidate_coverage | yes | 472/482 not excluded from priors |

## Notes

- The 35 YT500 transcripts absent from the 482-track library are the natural held-out set.
- The 5 duplicate groups (10 tracks) are excluded from priors and eval.
- The 438 v3 maqam labels are audio+caption labels, not ABC; they are cross-check only.
- The 22 FADL shortlist tracks link to the selected-scores transcript when it exists,
  otherwise to the reference conditioner ABC used for the instrumental render.
- `TRANSCRIPTS/FADL_SHAKER` is a broader 15-album set; the exact 22-track source is
  `TRANSCRIPTS/fadhl_shaker_selected_scores` plus the shortlist reference ABCs.

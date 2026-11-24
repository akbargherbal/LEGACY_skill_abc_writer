# SUNO ABC score dataset — provenance

**Status:** project-controlled input, not yet cleared for public redistribution.
**Source file:** `data/SUNO_ABC_SCORE_DATASET.pkl`
**SHA-256:** `4217a4f140a25e78c15c9bb7dfeb898b2b20f90b3225ade204ca76c7523e78ac`
**Rows:** 670 ABC scores (644 with vocal notes, 26 instrumental-only)
**Built library:** `data/suno/` by `tools/build_suno_library.py`
**Remixer store:** `03_abc_remixer/data/remix/`

## Owner statement

The pickle was compiled by the project owner from Suno-generated material and
is treated as project-controlled for internal use. This repository does not
claim that the dataset is copyright-free.

## Required before public data distribution

Record the following here, then change `license_status` in `data/suno/dataset.json`
and the remixer `dataset.json` from `pending-clearance` to `cleared`:

- Suno plan and terms in effect when the outputs were generated.
- Model/version and generation dates.
- Prompt policy: whether any prompt named an existing song, artist, or melody.
- Who or what produced the ABC text (hand-written, LLM-generated, transcribed).
- Ownership/authorship of any lyrics present in the source material.
- Any third-party samples or references.

Until then, `make remix-zip-public` stays code-only and the full/internal package
is the only build that carries the store.

## Rebuild

```bash
make suno-build       # data/SUNO_ABC_SCORE_DATASET.pkl -> data/suno/
make suno-check       # validate counts and hashes
make remix-build      # data/suno/ -> 03_abc_remixer/data/remix/
make remix-verify
```

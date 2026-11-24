# SUNO ABC score dataset — provenance

**Status:** open-source Suno tracks with no attributed author. The project owner
asserts that the compiled ABC dataset is free to use and redistribute.
**Source file:** `data/SUNO_ABC_SCORE_DATASET.pkl`
**SHA-256:** `4217a4f140a25e78c15c9bb7dfeb898b2b20f90b3225ade204ca76c7523e78ac`
**Rows:** 670 ABC scores (644 with vocal notes, 26 instrumental-only)
**Built library:** `data/suno/` by `tools/build_suno_library.py`
**Remixer store:** `03_abc_remixer/data/remix/`

## Basis for use

The source tracks are open-source Suno tracks with no attributed author. The
ABC scores were compiled by the project owner and are treated as freely usable
and redistributable. No third-party author attribution is required by the
owner's records.

If a formal licence instrument exists (for example a CC0/public-domain
dedication or a Suno terms page), record its name and URL here so downstream
users can cite it.

## Rebuild

```bash
make suno-build       # data/SUNO_ABC_SCORE_DATASET.pkl -> data/suno/
make suno-check       # validate counts and hashes
make remix-build      # data/suno/ -> 03_abc_remixer/data/remix/
make remix-verify
```

Both the full and public remixer archives carry the 670-score store.

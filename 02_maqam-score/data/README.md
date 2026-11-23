# Bundled corpus artifacts

This directory makes the OSTRIS corpus tools work **offline**. It is a snapshot
of the generated artifacts, copied from `analysis/out/ostris/` by
`scripts/bundle_data.sh` (`make ostris-bundle`) and included in
`dist/02_maqam-score.zip`.

## What is here

| Path | Produced by | Read by |
|---|---|---|
| `source/` | `sync` (copy from the project data root) | `audit`, `build`, `features`, `eval --build-split` |
| `records.jsonl`, `held_out.jsonl`, `manifest_links.csv` | `audit` | `features`, `priors`, `idioms`, `eval` |
| `audit.json`, `canonical.json`, `features.json`, `idioms.json`, `similarity/similarity.json` | `audit`, `build`, `features`, `idioms`, `similarity` | humans, schemas |
| `priors/` | `priors` | `plan`, `check` |
| `idioms.jsonl`, `idioms.json` | `idioms` | `exemplar`, `similarity --build` |
| `similarity/index.json` | `similarity --build` | `similarity --score`, `check` |
| `eval/split.json` | `eval --build-split` | `eval --runs` |

Generated Markdown reports (`audit.md`, `canonical.md`, `features.md`,
`idioms.md`, `priors/priors.md`) are developer documentation and are **not**
copied into the bundle.

Every reader command defaults to this directory (`cli.py` resolves it from
`__file__`), so no `--out`/`--priors`/`--cache` flag is needed from any working
directory.

## Refresh

```bash
DATA_ROOT=gs://<bucket> make ostris-sync
make ostris-audit ostris-build ostris-features ostris-online
make ostris-bundle     # copy analysis/out/ostris -> here
make zip               # rebuild the package
```

`sync` is the only step that touches the bucket, and only when the corpus is
being refreshed. Reading and composing never do.

## Not included

- **Audio** — the 2.95 GiB bundle is never downloaded or copied; the tools read
  audio only as manifest metadata.
- **`work/canonical/`** — a second copy of the ABC text, reproducible with
  `make ostris-build`; `scripts/bundle_data.sh` omits it.

## Licensing

Internal use on project machines. The snapshot contains titles, track ids,
short interval/rhythm sequences, and the ABC text the tools parse; the upstream
terms for the YT500, FADL Shaker, OSTRIS and v3 sources are **not cleared**.
For a public release, remove `data/ostris/` from the package and pass explicit
`--out`/`--priors` paths. See `docs/ostris-licensing.md`.

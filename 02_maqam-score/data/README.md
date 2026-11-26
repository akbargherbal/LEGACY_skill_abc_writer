# Bundled corpus artifacts

This directory makes the OSTRIS corpus tools work **offline**. It is a snapshot
of the generated artifacts, copied from `analysis/out/ostris/` by
`scripts/bundle_data.sh` (`make ostris-bundle`) and included in
`dist/abc-score-writer.zip`.

Only **derived** artifacts ship. The raw corpus inputs (`source/`) are fetched
on demand and are not part of the package or the repository; see
[Regenerating `source/`](#regenerating-source).

## What is here

| Path | Produced by | Read by |
|---|---|---|
| `source/` | **not shipped** — `sync` fetches it on demand | `audit`, `build`, `features`, `eval --build-split` (rebuild only) |
| `records.jsonl`, `held_out.jsonl`, `manifest_links.csv` | `audit` | `features`, `priors`, `idioms`, `eval` |
| `audit.json`, `canonical.json`, `features.json`, `idioms.json`, `similarity/similarity.json` | `audit`, `build`, `features`, `idioms`, `similarity` | humans, schemas |
| `priors/` | `priors` | `plan`, `check` |
| `idioms.jsonl`, `idioms.json` | `idioms` | `exemplar`, `similarity --build` |
| `similarity/index.json` | `similarity --build` | `similarity --score`, `check` |
| `eval/split.json` | `eval --build-split` | `eval --runs` |

Generated Markdown reports (`audit.md`, `canonical.md`, `features.md`,
`idioms.md`, `priors/priors.md`) are developer documentation and are **not**
copied into the bundle.

## Portable filenames

The snapshot uses ASCII, space-free names so it survives any zip/OS layer:

- selected-score folders are stored under their transliterated slug
  (`al_qamari` style) instead of the Arabic stem; `sync.py` and `links.py`
  understand both layouts;
- FADL album JSONs are normalised (`01.Walla Zaman.1998.json` →
  `01.Walla_Zaman.1998.json`) by `sync.py` before `audit` runs.

`tests/test_bundled_data.py` fails if a bundled path is non-ASCII or contains a
space, and asserts that `source/` is not shipped. The record-to-source check
runs only when a local `source/` cache is present, and requires a "not in cache"
note for any declared transcript that is absent.

Every reader command defaults to this directory (`cli.py` resolves it from
`__file__`), so no `--out`/`--priors` flag is needed from any working directory.
The four rebuild commands take `--cache`, which defaults to `data/ostris/source/`
here — present only after an explicit `sync`.

## Regenerating `source/`

`source/` holds the raw inputs `sync` copies from the project data root: the two
OSTRIS/v3 manifests, the YT500 manifest and ABC shards, the 15 FADL album JSONs,
the FADL shortlist, and the reference/selected ABCs. Nothing reads it at compose
time; it is only needed to **rebuild** `records.jsonl`, `canonical.json`,
`features.json`, the priors, the idiom bank, the similarity index, and
`eval/split.json`.

Canonical location for rebuilds (already in `.gitignore`):

```bash
cd <repo>            # the checkout that contains 02_maqam-score/
DATA_ROOT=gs://<bucket> make ostris-sync
# equivalent to:
python3 02_maqam-score/scripts/ostris_cli.py sync \
  --data-root gs://<bucket> \
  --cache analysis/out/ostris/source
```

Then rebuild in place:

```bash
make ostris-audit ostris-build ostris-features ostris-online
make ostris-bundle     # copy derived artifacts -> 02_maqam-score/data/ostris/
make zip               # rebuild the package (source/ is excluded)
```

If you work from an unpacked skill instead of the repo, any writable directory
works — pass it explicitly:

```bash
python3 scripts/ostris_cli.py sync --data-root gs://<bucket> --cache /tmp/ostris-source
python3 scripts/ostris_cli.py audit --cache /tmp/ostris-source --out data/ostris
python3 scripts/ostris_cli.py build --cache /tmp/ostris-source --out data/ostris --require-contract
python3 scripts/ostris_cli.py features --cache /tmp/ostris-source --out data/ostris --require-contract
python3 scripts/ostris_cli.py eval --cache /tmp/ostris-source --out data/ostris --build-split
```

Without `--cache`, these four commands look in `02_maqam-score/data/ostris/source/`
and, if it is missing, print the `sync` command above and exit with status 2.
`sync` is the only step that touches the bucket; reading and composing never do.
Delete the cache when the rebuild is done — it is not part of the deliverable.

## Not included

- **Audio** — the 2.95 GiB bundle is never downloaded or copied; the tools read
  audio only as manifest metadata.
- **`source/`** — the raw inputs are fetched with `sync` on demand and ignored
  by git; see [Regenerating `source/`](#regenerating-source).
- **`work/canonical/`** — a second copy of the ABC text, reproducible with
  `make ostris-build`; `scripts/bundle_data.sh` omits it.

## Licensing

Internal use on project machines. The snapshot contains titles, track ids,
derived features, and short interval/rhythm sequences; it carries **no ABC
text**. The upstream terms for the YT500, FADL Shaker, OSTRIS and v3 sources are
**not cleared**.
For a public release, remove `data/ostris/` from the package and pass explicit
`--out`/`--priors` paths. See `docs/ostris-licensing.md`.

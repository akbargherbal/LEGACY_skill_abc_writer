# Release archive

Every release keeps the exact archive that shipped. The unversioned files in
`dist/` are aliases for the **current** release; this folder is the history.

| Version | Full skill | Public (code only) | Notes |
|---|---|---|---|
| **0.4.0** | `abc_score_writer-0.4.0.zip` | `abc_score_writer-0.4.0-public.zip` | acceptance/strict shape, tessitura, phrase sidecar; see `../RELEASE-0.4.0.md` |
| **0.3.0** | `abc_score_writer-0.3.0.zip` | `abc_score_writer-0.3.0-public.zip` | shape gate; see `../RELEASE-0.3.0.md` |
| **0.2.0** | `abc_score_writer-0.2.0.zip` | `abc_score_writer-0.2.0-public.zip` | previous release; six validity guards |

Checksums:

- `SHA256SUMS-0.2.0.txt`
- `SHA256SUMS-0.3.0.txt`
- `SHA256SUMS-0.4.0.txt`

The 0.2.0 full archive is the one provided for the Claude session and is
content-identical to the 0.2.0 source at git `HEAD`; its hash is for the exact
archive, not a reproducible build (zip metadata differs between builds).

## Verify a download

```bash
cd dist/releases
sha256sum -c SHA256SUMS-0.4.0.txt
unzip -q abc_score_writer-0.4.0.zip
cd abc_score_writer
bash scripts/selftest.sh
python3 -m unittest discover -s tests
python3 scripts/ostris_cli.py contract
```

Expected: `selftest: PASS`, 51 tests OK, `skill v0.4.0: pinned`.

## Which one do I install?

- **Full**: the default. Includes the 177-track corpus artifacts so
  `plan`/`exemplar`/`check` run offline with no flags.
- **Public**: code only, no corpus data (licensing: `docs/ostris-licensing.md`).
  The corpus commands then need explicit `--out`/`--priors` snapshots.

The archive always extracts to a single top-level `abc_score_writer/` folder,
matching `SKILL.md`'s `name`.

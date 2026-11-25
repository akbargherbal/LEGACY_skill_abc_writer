#!/usr/bin/env python3
"""Report-only craft mirror: phrase variety, contour, cadence ladder.

This is the tune mirror, not a gate. `checker.py` answers "is this a valid
score of the declared shape?"; this script answers "is this a tune?" It reads
the two-voice score and prints the numbers a listener hears first:

- phrase rhythm variety, contour and shape variety;
- step/repeat/leap shares;
- descending share, same-start-end, late peak, end-long share;
- literal repetition (unique bars) and 4-note recurrence;
- the cadence ladder (which scale degree each phrase ends on).

It does not read `calibration.json`, does not FAIL, and does not enter
`checker.py`. The 177-track distributions are in `references/craft.md` §12.

Usage:
    python3 craft.py score.abc
    python3 craft.py score.abc --json craft.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _craft_calibrate as cal  # noqa: E402
import _craft_measure as cm  # noqa: E402
import phrase_table  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("score", type=Path)
    ap.add_argument("--json", type=Path, help="write craft.json here")
    ap.add_argument("--out", type=Path, help="write craft.json in this directory")
    ap.add_argument("--phrases", type=Path, help="phrases.json: print the per-line table")
    args = ap.parse_args(argv)

    try:
        parsed = cal.parse_score(args.score)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR {args.score}: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    row = None
    measure_error = None
    try:
        row = cm.measure_track(parsed)
    except Exception as exc:  # noqa: BLE001
        measure_error = f"{type(exc).__name__}: {exc}"
        print(f"WARN {args.score}: aggregate craft unavailable ({measure_error}); "
              f"the per-line table is still authoritative", file=sys.stderr)
    payload = {
        "metric_basis": "corpus:n=177 (five_stars, 2026-11-24)",
        "definitions": (cm.__doc__ or "").split("Usage:")[0].strip(),
        "rows": [],
        "errors": ([measure_error] if measure_error else []),
    }
    if row is not None:
        row["file"] = str(args.score)
        cm.print_track(args.score.name, row)
        payload["rows"] = [row]

    if args.phrases:
        try:
            phrases = json.loads(args.phrases.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR {args.phrases}: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 1
        table = phrase_table.build(parsed, phrases)
        payload["phrase_table"] = table
        print("\nper-line phrase table")
        print("  line section      bars    syl  notes beat cell                    rest_after  unbroken  mean  rep   leap  end")
        for r in table["rows"]:
            print(
                f"  {r.get('line', '?'):>4} {str(r.get('section',''))[:12]:<12} "
                f"{r.get('bars',''):<7} {str(r.get('syllables','-')):>4} "
                f"{(r.get('notes') if r.get('notes') is not None else '-'):>5} {str(r.get('start_beat','-')):>4} "
                f"{str(r.get('rhythm_cell',''))[:22]:<22} "
                f"{str(r.get('rest_after_s','-')):>10} "
                f"{str(r.get('unbroken_s','-')):>8} "
                f"{str(r.get('register_mean','-')):>5} "
                f"{str(r.get('repeated','-')):>5} "
                f"{str(r.get('leaps','-')):>5} "
                f"{str(r.get('end_name','-')):>3}"
            )
        s = table["summary"]
        print(f"  lyric lines {s['lyric_lines']}  detected phrases {s['detected_phrases']}  "
              f"merged {s['merged_lines']}")
        if s.get("missing_lines"):
            print(f"  INCOMPLETE: {s['missing_lines']} line(s) have no bars in this file; "
                  "the endings are not inferred")
        else:
            print("  COMPLETE: every lyric line has bars in this file")

    target = args.json or (args.out / "craft.json" if args.out else None)
    if target:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                          encoding="utf-8")
        print(f"\nwrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

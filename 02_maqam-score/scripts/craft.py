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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("score", type=Path)
    ap.add_argument("--json", type=Path, help="write craft.json here")
    ap.add_argument("--out", type=Path, help="write craft.json in this directory")
    args = ap.parse_args(argv)

    try:
        row = cm.measure_track(cal.parse_score(args.score))
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR {args.score}: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    row["file"] = str(args.score)
    cm.print_track(args.score.name, row)
    payload = {
        "metric_basis": "corpus:n=177 (five_stars, 2026-11-24)",
        "definitions": (cm.__doc__ or "").split("Usage:")[0].strip(),
        "rows": [row],
        "errors": [],
    }
    target = args.json or (args.out / "craft.json" if args.out else None)
    if target:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                          encoding="utf-8")
        print(f"\nwrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

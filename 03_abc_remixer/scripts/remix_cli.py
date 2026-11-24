#!/usr/bin/env python3
"""Entry point for the library-aware remixer.

Run by absolute path so the skill's working directory does not matter::

    python3 <skill>/scripts/remix_cli.py catalog --limit 5
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from remix.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Entry point for the bundled OSTRIS corpus tools.

Run by absolute path so the skill's working directory does not matter::

    python3 <skill>/scripts/ostris_cli.py audit --cache ... --out ...

The implementation lives in ``scripts/ostris/`` next to this file.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from ostris.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())

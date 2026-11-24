"""Locate the vendored 0.3.0 runtime and the remixer data store.

The installed ``abc_remixer`` package carries a copy of the shared runtime
inside its own ``scripts/`` directory, preserving the layout expected by
``ostris/check.py`` (``scripts/checker.py``) and ``ostris/contract.py``.  In the
development tree the files still live in ``02_maqam-score/scripts``; the
fallback below makes the source checkout work without a build step.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REMIX_VERSION = "0.1.0"
STORE_VERSION = "remix-build-v1"
BASELINE_SKILL_VERSION = "0.3.0"

_HERE = Path(__file__).resolve()
_SKILL_ROOT = _HERE.parents[2]  # 03_abc_remixer/ (or installed abc_remixer/)
_SCRIPTS = _SKILL_ROOT / "scripts"
_REPO_ROOT = _HERE.parents[3] if len(_HERE.parents) > 3 else _SKILL_ROOT.parent
_DEV_SCRIPTS = _REPO_ROOT / "02_maqam-score" / "scripts"


def shared_scripts() -> Path:
    """Return the first directory containing the shared ``abc_tools.py``."""
    candidates = []
    override = os.environ.get("REMIX_SHARED_SCRIPTS")
    if override:
        candidates.append(Path(override).expanduser().resolve())
    candidates.extend([_SCRIPTS, _DEV_SCRIPTS])
    for candidate in candidates:
        if (candidate / "abc_tools.py").is_file():
            return candidate
    raise RuntimeError(
        "cannot find the shared abc_tools.py; set REMIX_SHARED_SCRIPTS or run "
        "scripts/package_remixer.sh (looked in: "
        + ", ".join(str(item) for item in candidates)
        + ")"
    )


_SHARED = None


def bootstrap() -> Path:
    """Put the shared runtime on ``sys.path`` once and return its directory."""
    global _SHARED
    if _SHARED is not None:
        return _SHARED
    shared = shared_scripts()
    if str(shared) not in sys.path:
        sys.path.insert(0, str(shared))
    _SHARED = shared
    return shared


def skill_root() -> Path:
    return _SKILL_ROOT


def data_dir() -> Path:
    return _SKILL_ROOT / "data" / "remix"


def ostris_data_dir() -> Path:
    """The optional OSTRIS data directory used for prior percentiles."""
    local = _SKILL_ROOT / "data" / "ostris"
    if local.is_dir():
        return local
    dev = _REPO_ROOT / "02_maqam-score" / "data" / "ostris"
    return dev


def default_ledger() -> Path:
    return Path.cwd() / ".remix-ledger.jsonl"


bootstrap()

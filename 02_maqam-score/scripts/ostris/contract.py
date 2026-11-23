"""Pinned skill-contract versions and hashes (D7, D14).

The constants are intentionally literal.  If the checker, calibration, or
vendored parser changes, ``verify()`` reports drift instead of silently
changing what the corpus tools mean.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

SKILL_VERSION = "0.3.0"

PINNED = {
    "checker.py": "dedfb8516ad57339d29eb318ab8beb880d311bb1f1897bead6761ae10cbd2829",
    "calibration.json": "9d5d01eca30231c59b505c622e3b9eebff80622fa7546194a1610fe1600e9e45",
    "abc_tools.py": "e99e5cf9dff4647f48322e3319065ba793e7dbc808222e1848bab7aa8c4bd11c",
}

SCRIPTS = Path(__file__).resolve().parents[1]
SKILL_ROOT = SCRIPTS.parent


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(skill_root: Path | None = None) -> list[dict]:
    """Return one check per pinned artifact, newest state first."""
    root = Path(skill_root).resolve() if skill_root else SKILL_ROOT
    checks = []
    for name, expected in PINNED.items():
        path = root / "scripts" / name
        actual = sha256_file(path) if path.is_file() else None
        checks.append(
            {
                "artifact": f"scripts/{name}",
                "expected": expected,
                "actual": actual,
                "ok": actual == expected,
                "detail": (
                    "ok"
                    if actual == expected
                    else "missing"
                    if actual is None
                    else "drift"
                ),
            }
        )
    return checks


def verify_ok(skill_root: Path | None = None) -> bool:
    return all(check["ok"] for check in verify(skill_root))

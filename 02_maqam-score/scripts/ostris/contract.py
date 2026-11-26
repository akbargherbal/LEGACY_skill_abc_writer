"""Pinned skill-contract versions and hashes (D7, D14).

The constants are intentionally literal.  If the checker, calibration, or
vendored parser changes, ``verify()`` reports drift instead of silently
changing what the corpus tools mean.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

SKILL_VERSION = "0.9.0"

PINNED = {
    "checker.py": "e047c476ada390405a999deac147d2855ca82f1c6b7aa1023737e7fde17ac981",
    "calibration.json": "329eaa690879b354af495d7ff20ed2d03a70facae0ca088e91df6707458cf2fa",
    "abc_tools.py": "d56d281fd78856626129cd0a7aef327de6fc03403d9d0f286b1950fdc1df44a6",
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

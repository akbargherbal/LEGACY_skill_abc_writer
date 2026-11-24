"""Hard output caps.

The remixer is a funnel: every tool has a maximum number of characters it may
return to the model.  A cap failure is a bug or an over-broad request, never a
reason to silently truncate musical material.
"""
from __future__ import annotations

from .errors import RemixError

LIMITS = {
    "catalog_line": 160,
    "catalog": 8_000,
    "songmap": 3_000,
    "slice": 2_500,
    "motif": 1_500,
    "quote_report": 4_000,
}


def enforce(name: str, text: str, limit: int | None = None) -> str:
    cap = limit if limit is not None else LIMITS.get(name)
    if cap is not None and len(text) > cap:
        raise RemixError(
            f"{name} output cap exceeded: {len(text)} > {cap} characters; "
            "narrow the request (fewer bars/rows or --max-chars)",
            code=4,
        )
    return text


def clip(text: str, limit: int) -> str:
    """Clip free text (titles) without splitting a UTF-8 code point."""
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"

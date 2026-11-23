"""Structural canonicalization of a transcript (M1, decisions D9/D14).

This is not a musical re-notation.  It normalizes line endings and trailing
whitespace, validates the header and voice contract, and leaves every music
line, comment, per-bar ``M:``, and inline ``[K:...]`` untouched.

The plan's phrase "unify ``L/M/Q``" conflicts with D9 ("preserve ``M:``").  The
resolution recorded in ``docs/ostris-decisions.md`` is that canonicalization
keeps ``L``/``Q``/``M`` values as written and only normalizes structure.  A
future duration rescale would be a separate, reviewable transform.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

REQUIRED_HEADERS = ("X", "M", "L", "Q", "K")
REQUIRED_VOICES = ("Vocal", "Ins")

INLINE_METER = re.compile(r"\[M:([^\]]+)\]")
INLINE_KEY = re.compile(r"\[K:([^\]]+)\]")
FIELD = re.compile(r"^([A-Za-z]):(.*)$")


@dataclass
class CanonicalAbc:
    ok: bool
    text: str
    sha256: str
    header: dict[str, str] = field(default_factory=dict)
    voices: list[str] = field(default_factory=list)
    meters_declared: list[str] = field(default_factory=list)
    keys_declared: list[str] = field(default_factory=list)
    inline_meter_changes: int = 0
    inline_key_changes: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "ok": self.ok,
            "sha256": self.sha256,
            "header": self.header,
            "voices": self.voices,
            "meters_declared": self.meters_declared,
            "keys_declared": self.keys_declared,
            "inline_meter_changes": self.inline_meter_changes,
            "inline_key_changes": self.inline_key_changes,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def normalize_text(text: str) -> str:
    """LF line endings, no trailing whitespace, exactly one final newline."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines) + "\n"


def canonicalize(text: str) -> CanonicalAbc:
    """Normalize and validate one ABC transcript without rewriting it."""
    errors: list[str] = []
    warnings: list[str] = []

    if not text or not text.strip():
        return CanonicalAbc(
            ok=False,
            text="",
            sha256=hashlib.sha256(b"").hexdigest(),
            errors=["empty ABC"],
        )

    normalized = normalize_text(text)
    header: dict[str, str] = {}
    voices: list[str] = []
    meters: list[str] = []
    keys: list[str] = []
    inline_meters = 0
    inline_keys = 0

    for line in normalized.splitlines():
        if not line or line.lstrip().startswith("%"):
            continue
        match = FIELD.match(line)
        if match:
            field_letter, value = match.group(1), match.group(2).strip()
            if field_letter in ("X", "T", "M", "L", "Q", "K"):
                header.setdefault(field_letter, value)
                if field_letter == "M" and value and value not in meters:
                    meters.append(value)
                if field_letter == "K" and value and value not in keys:
                    keys.append(value)
            elif field_letter == "V":
                name = value.split()[0] if value else ""
                if name and name not in voices:
                    voices.append(name)
        inline_meters += len(INLINE_METER.findall(line))
        inline_keys += len(INLINE_KEY.findall(line))

    for letter in REQUIRED_HEADERS:
        if not header.get(letter):
            errors.append(f"missing {letter}: header")
    for voice in REQUIRED_VOICES:
        if voice not in voices:
            errors.append(f"missing V: {voice} voice")
    if header.get("M") and not meters:
        errors.append("meter header is empty")
    if header.get("Q") and not header["Q"]:
        errors.append("tempo header is empty")
    if not errors and len(voices) > 2:
        warnings.append(f"extra voices: {', '.join(v for v in voices if v not in REQUIRED_VOICES)}")

    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return CanonicalAbc(
        ok=not errors,
        text=normalized,
        sha256=digest,
        header=header,
        voices=voices,
        meters_declared=meters,
        keys_declared=keys,
        inline_meter_changes=inline_meters,
        inline_key_changes=inline_keys,
        errors=errors,
        warnings=warnings,
    )

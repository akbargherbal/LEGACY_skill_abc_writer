#!/usr/bin/env python3
"""Verify the composer's declared borrowings.

A loan is only accepted when it names a real asset, states what was borrowed,
records a transformation, and gives a reason tied to the fit.  This is a
structural check, not a taste verdict: the ear remains the judge.

    python3 verify_loans.py --loans loans.json --index data/assets/assets.jsonl.gz
    python3 verify_loans.py --loans loans.json --plan plan.json --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import asset_bank  # noqa: E402

ALLOWED_BORROWED = {
    "rhythm", "contour", "cadence", "interval", "duration",
    "groove", "chord", "structure", "cell",
}
TRANSFORM_WORDS = {
    "transpose", "remap", "rhythm-only", "contour-only", "retrograde",
    "augment", "diminish", "fragment", "cadence", "syllable", "fit",
    "change", "replace", "revoice", "invert",
}


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _bars(value) -> tuple[int, int] | None:
    if value is None:
        return None
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return int(value[0]), int(value[1])
    if isinstance(value, str):
        match = re.fullmatch(r"\s*(\d+)\s*-\s*(\d+)\s*", value)
        if match:
            return int(match.group(1)), int(match.group(2))
        if value.strip().isdigit():
            number = int(value.strip())
            return number, number
    return None


def verify(loans: list[dict], assets: list[dict], plan: dict | None = None) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    rows: list[dict] = []
    seen: set[str] = set()
    for index, loan in enumerate(loans, 1):
        label = f"loan {index}"
        if not isinstance(loan, dict):
            errors.append(f"{label}: not an object")
            continue
        asset_id = loan.get("asset") or loan.get("id")
        if not asset_id:
            errors.append(f"{label}: missing asset id")
            continue
        if asset_id in seen:
            warnings.append(f"{label}: asset {asset_id} is declared twice")
        seen.add(asset_id)
        asset = asset_bank.asset_by_id(assets, str(asset_id))
        if asset is None:
            errors.append(f"{label}: asset not found: {asset_id}")
            continue
        source = loan.get("source")
        if source and source != asset["source"]:
            errors.append(f"{label}: source {source!r} != asset source {asset['source']!r}")
        span = _bars(loan.get("bars"))
        if span and span != (asset["start_bar"], asset["end_bar"]):
            errors.append(
                f"{label}: bars {span[0]}-{span[1]} != asset {asset['start_bar']}-{asset['end_bar']}"
            )
        borrowed = loan.get("borrowed")
        if isinstance(borrowed, str):
            borrowed = [borrowed]
        if not borrowed:
            errors.append(f"{label}: missing borrowed fields")
        else:
            unknown = {str(item) for item in borrowed} - ALLOWED_BORROWED
            if unknown:
                errors.append(f"{label}: unknown borrowed fields {sorted(unknown)}")
        transforms = loan.get("transform")
        if isinstance(transforms, str):
            transforms = [transforms]
        if not transforms:
            errors.append(f"{label}: missing transform")
        else:
            text = " ".join(map(str, transforms)).lower()
            if text.strip() in {"none", "copy", "no change"}:
                errors.append(f"{label}: a loan must transform, not copy verbatim")
            elif not any(word in text for word in TRANSFORM_WORDS):
                warnings.append(f"{label}: transform is not in the known vocabulary: {transforms}")
        why = str(loan.get("why") or "").strip()
        if len(why) < 20:
            errors.append(f"{label}: why is too short to audit")
        fit = loan.get("fit")
        if not isinstance(fit, dict) or len(fit) < 2:
            errors.append(f"{label}: fit needs at least two measured fields")
        if plan:
            sections = {str(item) for item in plan.get("sections") or []}
            role = str(loan.get("role") or asset.get("role") or "")
            if sections and role and role not in sections and role not in {"opening", "cadence"}:
                warnings.append(f"{label}: role {role!r} is not in plan sections")
            register = plan.get("register") or {}
            if isinstance(fit, dict) and "register" in fit:
                span_fit = _bars(fit.get("register")) if isinstance(fit.get("register"), str) else None
                if span_fit and register.get("mean") is not None:
                    mean = float(register["mean"])
                    tolerance = float(register.get("tolerance", 3))
                    if span_fit[1] < mean - tolerance or span_fit[0] > mean + tolerance:
                        warnings.append(
                            f"{label}: fit register {span_fit[0]}-{span_fit[1]} "
                            f"is outside plan {mean:.0f}±{tolerance:.0f}"
                        )
        rows.append({
            "asset": asset_id,
            "source": asset["source"],
            "bars": f"{asset['start_bar']}-{asset['end_bar']}",
            "role": loan.get("role") or asset["role"],
            "why": why,
            "ok": not any(error.startswith(f"{label}:") for error in errors),
        })
    return {"ok": not errors, "errors": errors, "warnings": warnings, "rows": rows}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--loans", type=Path, required=True)
    parser.add_argument("--index", type=Path, default=asset_bank.DEFAULT_INDEX)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    payload = _load_json(args.loans)
    loans = payload.get("loans") if isinstance(payload, dict) else payload
    if not isinstance(loans, list):
        raise SystemExit("loans file must be a list or an object with a 'loans' list")
    assets = asset_bank.load_index(args.index)
    plan = _load_json(args.plan) if args.plan else None
    result = verify(loans, assets, plan)
    if args.json:
        print(json.dumps(result, indent=1, ensure_ascii=False))
    else:
        print(f"{'PASS' if result['ok'] else 'FAIL'}  loans: {len(loans)} "
              f"| errors {len(result['errors'])} | warnings {len(result['warnings'])}")
        for error in result["errors"]:
            print(f"  FAIL  {error}")
        for warning in result["warnings"]:
            print(f"  WARN  {warning}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

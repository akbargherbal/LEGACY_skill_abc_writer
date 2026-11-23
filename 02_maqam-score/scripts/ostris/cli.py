"""Command line for the OSTRIS corpus tools.

Implemented commands::

    python3 scripts/ostris_cli.py sync     --data-root gs://... --cache ...
    python3 scripts/ostris_cli.py audit    --cache ... --out ...
    python3 scripts/ostris_cli.py build    --cache ... --out ...
    python3 scripts/ostris_cli.py features --cache ... --out ...
    python3 scripts/ostris_cli.py contract

Online composition commands (plan, exemplar, check) are intentionally not
implemented until their decisions are recorded.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .audit import audit
from .build import build
from .contract import SKILL_VERSION, verify
from .features import build_features
from .sync import sync


def _default_cache() -> Path:
    return Path("data/ostris/source")


def _default_out() -> Path:
    return Path("data/ostris")


def cmd_sync(args) -> int:
    summary = sync(args.data_root, args.cache, force=args.force)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if not summary["missing_files"] else 1


def cmd_audit(args) -> int:
    summary = audit(args.cache, args.out)
    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        inv = summary["inventory"]
        counts = inv["links"]
        parse = inv["parse"]
        print(f"M0 audit: {'PASS' if summary['gate_pass'] else 'FAIL'}")
        print(
            f"library {counts['total']} | matched {counts['matched']} | "
            f"parse {parse['ok']}/{counts['total']} ({parse['ok_rate']:.1%})"
        )
        print(
            f"held-out {len(summary['held_out'])} | "
            f"duplicates {len(summary['duplicates'])} groups / "
            f"{sum(len(g['tracks']) for g in summary['duplicates'])} tracks | "
            f"excluded from priors {summary['distributions']['exclude_from_priors']}"
        )
        for failure in summary["parse_failures"]:
            print(f"  parse failure: {failure['id']}: {failure['error']}")
        print(f"wrote {summary['files']['audit']}")
        print(f"wrote {summary['files']['links']}")
        print(f"wrote {summary['files']['records']}")
    if args.strict and not summary["gate_pass"]:
        return 1
    return 0


def cmd_build(args) -> int:
    summary = build(
        args.cache,
        args.out,
        require_contract=args.require_contract,
    )
    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print(f"M1 build: {'PASS' if summary['gate_pass'] else 'FAIL'}")
        print(
            f"canonical {summary['canonical_ok']}/{summary['records']} | "
            f"{summary['canonical_bytes'] / 1_000_000:.1f} MB | "
            f"skill v{summary['skill_version']} "
            f"{'pinned' if summary['contract']['ok'] else 'DRIFTED'}"
        )
        for failure in summary["failures"]:
            print(f"  canonical failure: {failure['id']}: {failure['errors']}")
        print(f"wrote {summary['files']['canonical']}")
        print(f"records: {summary['records_file']}")
    if args.strict and not summary["gate_pass"]:
        return 1
    return 0


def cmd_features(args) -> int:
    summary = build_features(
        args.cache,
        args.out,
        require_contract=args.require_contract,
    )
    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print(f"M2 features: {'PASS' if summary['gate_pass'] else 'FAIL'}")
        print(
            f"features {summary['feature_ok']}/{summary['records']} | "
            f"maqam labels 0 (not claimed) | "
            f"skill v{summary['skill_version']} "
            f"{'pinned' if summary['contract']['ok'] else 'DRIFTED'}"
        )
        print("mode hypothesis:", ", ".join(
            f"{name} {count}" for name, count in summary["families"].items()
        ))
        for failure in summary["failures"]:
            print(f"  feature failure: {failure['id']}: {failure['error']}")
        print(f"wrote {summary['files']['features']}")
        print(f"records: {summary['records_file']}")
    if args.strict and not summary["gate_pass"]:
        return 1
    return 0


def cmd_contract(args) -> int:
    checks = verify()
    ok = all(check["ok"] for check in checks)
    if args.json:
        print(
            json.dumps(
                {"skill_version": SKILL_VERSION, "checks": checks, "ok": ok},
                indent=2,
            )
        )
    else:
        print(f"skill v{SKILL_VERSION}: {'pinned' if ok else 'DRIFT'}")
        for check in checks:
            print(
                f"  {check['artifact']}: {check['detail']} "
                f"(expected {check['expected'][:12]}…, got "
                f"{(check['actual'] or 'missing')[:12]}…)"
            )
    return 0 if ok or not args.strict else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ostris",
        description="OSTRIS corpus tools for the maqam-score skill",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    sync_parser = sub.add_parser("sync", help="copy lightweight corpus inputs into a cache")
    sync_parser.add_argument("--data-root", required=True, help="gs://bucket or local data root")
    sync_parser.add_argument("--cache", type=Path, default=_default_cache())
    sync_parser.add_argument("--force", action="store_true", help="overwrite cached files")
    sync_parser.set_defaults(func=cmd_sync)

    audit_parser = sub.add_parser("audit", help="run the M0 inventory and parse audit")
    audit_parser.add_argument("--cache", type=Path, default=_default_cache())
    audit_parser.add_argument("--out", type=Path, default=_default_out())
    audit_parser.add_argument("--json", action="store_true", help="print the full audit JSON")
    audit_parser.add_argument(
        "--strict", action="store_true", help="exit 1 when a required gate check fails"
    )
    audit_parser.set_defaults(func=cmd_audit)

    build_parser = sub.add_parser(
        "build", help="write canonical ABC files and upgrade records.jsonl"
    )
    build_parser.add_argument("--cache", type=Path, default=_default_cache())
    build_parser.add_argument("--out", type=Path, default=_default_out())
    build_parser.add_argument("--json", action="store_true", help="print the full build JSON")
    build_parser.add_argument(
        "--require-contract",
        action="store_true",
        help="fail the gate when a pinned skill hash has drifted",
    )
    build_parser.add_argument(
        "--strict", action="store_true", help="exit 1 when a required gate check fails"
    )
    build_parser.set_defaults(func=cmd_build)

    features_parser = sub.add_parser(
        "features", help="extract deterministic features and an unreviewed mode hypothesis"
    )
    features_parser.add_argument("--cache", type=Path, default=_default_cache())
    features_parser.add_argument("--out", type=Path, default=_default_out())
    features_parser.add_argument("--json", action="store_true", help="print the full features JSON")
    features_parser.add_argument(
        "--require-contract",
        action="store_true",
        help="fail the gate when a pinned skill hash has drifted",
    )
    features_parser.add_argument(
        "--strict", action="store_true", help="exit 1 when a required gate check fails"
    )
    features_parser.set_defaults(func=cmd_features)

    contract_parser = sub.add_parser(
        "contract", help="print and verify the pinned skill hashes"
    )
    contract_parser.add_argument("--json", action="store_true")
    contract_parser.add_argument(
        "--strict", action="store_true", help="exit 1 on hash drift"
    )
    contract_parser.set_defaults(func=cmd_contract)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as error:
        print(f"ostris: {type(error).__name__}: {error}", file=sys.stderr)
        return 2

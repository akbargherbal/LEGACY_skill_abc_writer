"""Command line for the OSTRIS corpus tools.

The derived corpus artifacts ship with the skill under ``<skill>/data/ostris/``,
so the reader commands below work offline with no flags::

    python3 scripts/ostris_cli.py priors   [--out ...]
    python3 scripts/ostris_cli.py idioms   [--out ...]
    python3 scripts/ostris_cli.py similarity [--out ...] --build
    python3 scripts/ostris_cli.py contract

The raw inputs (``source/``) are **not shipped**: they are fetched on demand and
are only needed to rebuild the derived artifacts::

    python3 scripts/ostris_cli.py audit    [--cache ...] [--out ...]
    python3 scripts/ostris_cli.py build    [--cache ...] [--out ...]
    python3 scripts/ostris_cli.py features [--cache ...] [--out ...]
    python3 scripts/ostris_cli.py eval     [--cache ...] [--out ...] --build-split

``sync`` populates that cache from the project data root; it is never required
to read or compose.  The rebuild commands print this recipe instead of a
traceback when the cache is missing::

    python3 scripts/ostris_cli.py sync --data-root gs://... [--cache ...]

Online::

    python3 scripts/ostris_cli.py plan     --manifest song.json --out plans/song
    python3 scripts/ostris_cli.py exemplar --function cadence --bars 2
    python3 scripts/ostris_cli.py similarity --score score.abc
    python3 scripts/ostris_cli.py check    score.abc --plan plans/song/skill_plan.json
    python3 scripts/ostris_cli.py eval     --runs runs/

No command prints the whole corpus, and no command claims a maqam label.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .audit import audit
from .build import build
from .check import check
from .contract import SKILL_VERSION, verify
from .eval import build_split, score_runs
from .features import build_features
from .idioms import build_idioms, load_idioms, pick_idioms
from .plan import plan_from_files
from .priors import build_priors
from .similarity import build_index, query_file
from .sync import sync


# ``cli.py`` lives at ``<skill>/scripts/ostris/cli.py``; the corpus artifacts
# ship next to the skill under ``<skill>/data/ostris/``.  Resolving from
# ``__file__`` makes the defaults work from any working directory, so the
# reader commands need no flags and no network.
SKILL_ROOT = Path(__file__).resolve().parents[2]
BUNDLED_DATA = SKILL_ROOT / "data" / "ostris"


def _default_cache() -> Path:
    """Conventional location for the on-demand raw inputs (not bundled)."""
    return BUNDLED_DATA / "source"


def _default_out() -> Path:
    return BUNDLED_DATA


def _require_cache(cache: Path) -> bool:
    """Explain how to fetch ``source/`` when a rebuild command needs it.

    The cache is not bundled, so a missing directory is the normal state of a
    fresh install; it must not surface as a ``FileNotFoundError`` traceback.
    """
    if Path(cache).is_dir():
        return True
    print(
        f"cache not found: {cache}\n"
        "Raw corpus inputs are not shipped; only derived artifacts are.  Fetch\n"
        "them once into a writable directory, then rerun with --cache:\n"
        "  python3 scripts/ostris_cli.py sync --data-root gs://<bucket> "
        "--cache analysis/out/ostris/source\n"
        "  python3 scripts/ostris_cli.py <audit|build|features|eval> "
        "--cache analysis/out/ostris/source ...\n"
        f"(or place the cache at {cache}; it is git-ignored — delete it before packaging.)\n"
        "Details: data/README.md, section 'Regenerating source/'.",
        file=sys.stderr,
    )
    return False


def _print_json(data) -> None:
    print(json.dumps(data, indent=1, ensure_ascii=False))


def cmd_sync(args) -> int:
    summary = sync(args.data_root, args.cache, force=args.force)
    _print_json(summary)
    return 0 if not summary["missing_files"] else 1


def cmd_audit(args) -> int:
    if not _require_cache(args.cache):
        return 2
    summary = audit(args.cache, args.out)
    if args.json:
        _print_json(summary)
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
    if not _require_cache(args.cache):
        return 2
    summary = build(args.cache, args.out, require_contract=args.require_contract)
    if args.json:
        _print_json(summary)
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
    if not _require_cache(args.cache):
        return 2
    summary = build_features(
        args.cache, args.out, require_contract=args.require_contract
    )
    if args.json:
        _print_json(summary)
    else:
        print(f"M2 features: {'PASS' if summary['gate_pass'] else 'FAIL'}")
        print(
            f"features {summary['feature_ok']}/{summary['records']} | "
            f"maqam labels 0 (not claimed) | "
            f"skill v{summary['skill_version']} "
            f"{'pinned' if summary['contract']['ok'] else 'DRIFTED'}"
        )
        print(
            "mode hypothesis:",
            ", ".join(f"{name} {count}" for name, count in summary["families"].items()),
        )
        for failure in summary["failures"]:
            print(f"  feature failure: {failure['id']}: {failure['error']}")
        print(f"wrote {summary['files']['features']}")
        print(f"records: {summary['records_file']}")
    if args.strict and not summary["gate_pass"]:
        return 1
    return 0


def cmd_priors(args) -> int:
    summary = build_priors(args.out, require_contract=args.require_contract)
    if args.json:
        _print_json(summary)
    else:
        print(f"M3 priors: {'PASS' if summary['gate_pass'] else 'FAIL'}")
        print(
            f"eligible {summary['eligible']}/{summary['records']} | "
            f"strata {summary['strata_count']} | "
            f"maqam-conditioned no"
        )
        print(f"wrote {summary['files']['priors']}")
    if args.strict and not summary["gate_pass"]:
        return 1
    return 0


def cmd_plan(args) -> int:
    priors = args.priors or (_default_out() / "priors" / "priors.json")
    result = plan_from_files(args.manifest, priors, args.out)
    brief = result["brief"]
    if args.json:
        _print_json(result)
    else:
        print(f"M3 plan: {'PASS' if brief['gate_pass'] else 'FAIL'}")
        print(
            f"{brief['prior']['stratum']} (n={brief['prior']['n']}, "
            f"{brief['prior']['confidence']}) | {brief['targets']['bars']} bars | "
            f"maqam not claimed"
        )
        for check in brief["checks"]:
            print(
                f"  {'ok' if check['ok'] else 'FAIL'}  {check['name']}: {check['detail']}"
            )
        for assumption in brief["assumptions"]:
            print(f"  assumed: {assumption}")
        print(f"wrote {brief['files']['brief']}")
        print(f"wrote {brief['files']['plan']}")
    if args.strict and not brief["gate_pass"]:
        return 1
    return 0


def cmd_idioms(args) -> int:
    summary = build_idioms(args.out)
    if args.json:
        _print_json(summary)
    else:
        print(f"M4 idioms: {'PASS' if summary['gate_pass'] else 'FAIL'}")
        print(
            f"idioms {summary['idioms']} across {summary['tracks_with_idioms']} tracks | "
            f"without vocal {summary['tracks_without_vocal']} | reviewed no"
        )
        print(f"wrote {summary['files']['idioms']}")
    if args.strict and not summary["gate_pass"]:
        return 1
    return 0


def cmd_exemplar(args) -> int:
    rows = pick_idioms(
        load_idioms(args.out),
        function=args.function,
        bars=args.bars,
        contour=args.contour,
        limit=args.limit,
    )
    result = {
        "function": args.function,
        "bars": args.bars,
        "contour": args.contour,
        "count": len(rows),
        "maqam_conditioned": False,
        "reviewed": False,
        "warning": "structural phrases, not reviewed maqam examples",
        "idioms": rows,
    }
    if args.json:
        _print_json(result)
    else:
        print(f"exemplars: {len(rows)}")
        for row in rows:
            print(
                f"  {row['track_id']}  bars {row['start_bar']}-{row['end_bar']}  "
                f"{row['function']}  {row['contour']}  "
                f"intervals {row['intervals'][:8]}"
            )
    return 0 if rows else 1


def cmd_similarity(args) -> int:
    if args.build:
        summary = build_index(args.out)
        _print_json(summary)
        return 0 if summary["gate_pass"] else 1
    if not args.score:
        print("ostris: pass --build or --score", file=sys.stderr)
        return 2
    result = query_file(args.score, args.out, top=args.top)
    if args.json:
        _print_json(result)
    else:
        print(f"max shared run: {result['max_shared_run']} intervals")
        for match in result["matches"]:
            print(
                f"  {match['track_id']}  {match['function']}  run "
                f"{match['max_shared_run']}  bars {match['source_bar_range']}"
            )
        if result["quotation"]["used"]:
            print(f"quotation: {result['quotation']['source_id']}")
    return 0


def cmd_check(args) -> int:
    report = check(
        args.score,
        args.plan,
        report_path=args.report,
        out_dir=args.out,
        require_final_rest=args.require_final_rest,
        strict_style=args.strict_style,
        lyrics_path=args.lyrics,
        waive_lyrics=args.waive_lyrics,
    )
    if args.json:
        _print_json(report)
    else:
        print(
            f"{report['class'].upper()}  {len(report['failures'])} hard failure(s), "
            f"{len(report['warnings'])} warning(s)"
        )
        for failure in report["failures"]:
            print(f"  FAIL  [{failure['class']}] {failure['code']}: {failure['detail']}")
        for warning in report["warnings"]:
            print(f"  WARN  [{warning['class']}] {warning['code']}: {warning['detail']}")
        if report.get("prior"):
            prior = report["prior"]
            print(
                f"prior {prior['stratum']} (n={prior['n']}, "
                f"{prior['confidence']}), percentile "
                f"{prior['percentiles'].get('chords_per_bar')}"
            )
        if report.get("similarity"):
            print(f"similarity: max shared run {report['similarity']['max_shared_run']}")
        print(f"maqam fit: unavailable ({report['maqam_fit']['reason']})")
        if args.report:
            print(f"wrote {args.report}")
    return 0 if report["pass"] else 1


def cmd_eval(args) -> int:
    if args.build_split:
        if not _require_cache(args.cache):
            return 2
        summary = build_split(args.cache, args.out)
        if args.json:
            _print_json(summary)
        else:
            print(f"M6 split: {'PASS' if summary['gate_pass'] else 'FAIL'}")
            print(
                f"held-out {summary['held_out']} | usable {summary['usable']} | "
                f"generation {len(summary['generation'])} | "
                f"retrieval {len(summary['retrieval'])} | "
                f"no ABC {len(summary['no_abc'])}"
            )
            print(f"wrote {summary['files']['split']}")
        return 0 if summary["gate_pass"] else 1
    if args.runs:
        summary = score_runs(args.runs, args.out)
        if args.json:
            _print_json(summary)
        else:
            aggregate = summary["aggregate"]
            print(f"M6 eval: {'PASS' if summary['gate_pass'] else 'FAIL'}")
            print(
                f"runs {aggregate['runs']} | contract+sanity "
                f"{aggregate['contract_sanity_pass']}/{aggregate['runs']} | "
                f"median bars delta {aggregate['median_bars_delta']}"
            )
            print("quality evaluated: no (no judge or blind review)")
            print(f"wrote {summary['files']['report']}")
        return 0 if summary["gate_pass"] else 1
    print("ostris: pass --build-split or --runs DIR", file=sys.stderr)
    return 2


def cmd_contract(args) -> int:
    checks = verify()
    ok = all(check["ok"] for check in checks)
    if args.json:
        _print_json({"skill_version": SKILL_VERSION, "checks": checks, "ok": ok})
    else:
        print(f"skill v{SKILL_VERSION}: {'pinned' if ok else 'DRIFT'}")
        for check in checks:
            print(
                f"  {check['artifact']}: {check['detail']} "
                f"(expected {check['expected'][:12]}…, got "
                f"{(check['actual'] or 'missing')[:12]}…)"
            )
    return 0 if ok or not args.strict else 1


def _add_common(parser: argparse.ArgumentParser, *, cache: bool = True) -> None:
    if cache:
        parser.add_argument("--cache", type=Path, default=_default_cache())
    parser.add_argument("--out", type=Path, default=_default_out())
    parser.add_argument("--json", action="store_true", help="print the full JSON result")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ostris", description="OSTRIS corpus tools for the maqam-score skill"
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    sync_parser = sub.add_parser("sync", help="copy lightweight corpus inputs into a cache")
    sync_parser.add_argument("--data-root", required=True)
    sync_parser.add_argument("--cache", type=Path, default=_default_cache())
    sync_parser.add_argument("--force", action="store_true")
    sync_parser.set_defaults(func=cmd_sync)

    audit_parser = sub.add_parser("audit", help="run the M0 inventory and parse audit")
    _add_common(audit_parser)
    audit_parser.add_argument("--strict", action="store_true")
    audit_parser.set_defaults(func=cmd_audit)

    build_parser = sub.add_parser("build", help="write canonical ABC files and records")
    _add_common(build_parser)
    build_parser.add_argument("--require-contract", action="store_true")
    build_parser.add_argument("--strict", action="store_true")
    build_parser.set_defaults(func=cmd_build)

    features_parser = sub.add_parser(
        "features", help="extract deterministic features and an unreviewed mode hypothesis"
    )
    _add_common(features_parser)
    features_parser.add_argument("--require-contract", action="store_true")
    features_parser.add_argument("--strict", action="store_true")
    features_parser.set_defaults(func=cmd_features)

    priors_parser = sub.add_parser("priors", help="build objective priors by stratum")
    _add_common(priors_parser, cache=False)
    priors_parser.add_argument("--require-contract", action="store_true")
    priors_parser.add_argument("--strict", action="store_true")
    priors_parser.set_defaults(func=cmd_priors)

    plan_parser = sub.add_parser("plan", help="generate brief.json + skill_plan.json")
    plan_parser.add_argument("--manifest", type=Path, required=True)
    plan_parser.add_argument("--priors", type=Path, default=None)
    plan_parser.add_argument("--out", type=Path, required=True)
    plan_parser.add_argument("--json", action="store_true")
    plan_parser.add_argument("--strict", action="store_true")
    plan_parser.set_defaults(func=cmd_plan)

    idioms_parser = sub.add_parser("idioms", help="build the structural idiom bank")
    _add_common(idioms_parser, cache=False)
    idioms_parser.add_argument("--strict", action="store_true")
    idioms_parser.set_defaults(func=cmd_idioms)

    exemplar_parser = sub.add_parser("exemplar", help="select idioms by structural function")
    _add_common(exemplar_parser, cache=False)
    exemplar_parser.add_argument("--function", choices=["opening", "phrase", "cadence"])
    exemplar_parser.add_argument("--bars", type=int, choices=[2, 3, 4])
    exemplar_parser.add_argument("--contour", choices=["up", "down", "wave", "flat"])
    exemplar_parser.add_argument("--limit", type=int, default=5)
    exemplar_parser.set_defaults(func=cmd_exemplar)

    similarity_parser = sub.add_parser(
        "similarity", help="build or query the interval k-gram index"
    )
    _add_common(similarity_parser, cache=False)
    similarity_parser.add_argument("--build", action="store_true")
    similarity_parser.add_argument("--score", type=Path)
    similarity_parser.add_argument("--top", type=int, default=5)
    similarity_parser.set_defaults(func=cmd_similarity)

    check_parser = sub.add_parser("check", help="run the skill checker, priors, and similarity")
    check_parser.add_argument("score", type=Path)
    check_parser.add_argument("--plan", type=Path, required=True)
    check_parser.add_argument("--lyrics", type=Path)
    check_parser.add_argument("--waive-lyrics", action="store_true",
                              help="explicitly waive lyrics prosody recomputation")
    check_parser.add_argument("--report", type=Path)
    check_parser.add_argument("--out", type=Path, default=_default_out())
    check_parser.add_argument("--require-final-rest", action="store_true")
    check_parser.add_argument("--strict-style", action="store_true")
    check_parser.add_argument("--json", action="store_true")
    check_parser.set_defaults(func=cmd_check)

    eval_parser = sub.add_parser("eval", help="build the held-out split or score runs")
    _add_common(eval_parser)
    eval_parser.add_argument("--build-split", action="store_true")
    eval_parser.add_argument("--runs", type=Path)
    eval_parser.add_argument("--strict", action="store_true")
    eval_parser.set_defaults(func=cmd_eval)

    contract_parser = sub.add_parser("contract", help="print and verify pinned hashes")
    contract_parser.add_argument("--json", action="store_true")
    contract_parser.add_argument("--strict", action="store_true")
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

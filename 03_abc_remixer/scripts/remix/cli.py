"""Command line for the library-aware remixer."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __doc__ as _doc
from . import shared

shared.bootstrap()

from . import catalog as catalog_mod  # noqa: E402
from . import textcap  # noqa: E402
from .build import build, build_suno, verify  # noqa: E402
from .errors import RemixError  # noqa: E402
from .ledger import Ledger  # noqa: E402
from .motif import query, query_contour, render as render_motif  # noqa: E402
from .quotecheck import check as remix_check, render as render_check  # noqa: E402
from .slice import slice_song  # noqa: E402
from .songmap import songmap  # noqa: E402
from .store import Store  # noqa: E402


def _store(args) -> Store:
    return Store(getattr(args, "library", None)).require()


def _charge(args, tool: str, song_id: str | None, text: str) -> str:
    ledger = Ledger.open(getattr(args, "ledger", None), getattr(args, "cap", None))
    return ledger.charge(tool, song_id, text)


def _print(text: str) -> None:
    if text.endswith("\n"):
        sys.stdout.write(text)
    else:
        print(text)


def cmd_library_build(args) -> int:
    out = args.out or shared.data_dir()
    if args.dataset == "suno":
        data = args.data
        if data is None:
            data = shared.skill_root().parent / "data" / "suno"
        report = build_suno(data, out, timestamp=args.timestamp)
        if args.json:
            _print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            counts = report["counts"]
            print(f"remix library: {'PASS' if report['gate_pass'] else 'FAIL'}")
            print(
                f"dataset {report['dataset']} | records {counts['records']} | "
                f"included {counts['included']} | excluded {counts['excluded']} | "
                f"vocal {counts['vocal_rows']} | ins-only {counts['ins_only_rows']}"
            )
            for check in report["checks"]:
                print(f"  {'ok' if check['ok'] else 'FAIL'}  {check['name']}: {check['detail']}")
            print(f"wrote {out}")
        return 0 if report["gate_pass"] else 1

    ostris = args.ostris_data
    if ostris is None:
        raise SystemExit("legacy build requires --ostris-data; use --dataset suno by default")
    report = build(
        ostris,
        out,
        include_all=args.include_all,
        quality_min=args.quality_min,
        timestamp=args.timestamp,
    )
    if args.json:
        _print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        counts = report["counts"]
        print(f"remix library: {'PASS' if report['gate_pass'] else 'FAIL'}")
        print(
            f"records {counts['records']} | linked {counts['linked']} | "
            f"with ABC {counts['with_abc']} | included {counts['included']} | "
            f"excluded {counts['excluded']}"
        )
        for check in report["checks"]:
            print(f"  {'ok' if check['ok'] else 'FAIL'}  {check['name']}: {check['detail']}")
        print(f"wrote {out}")
    return 0 if report["gate_pass"] else 1


def cmd_library_verify(args) -> int:
    result = verify(_store(args))
    if args.json:
        _print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"remix verify: {'PASS' if result['ok'] else 'FAIL'}")
        print(f"songs {result['songs']} | store {result['store_version']}")
        for error in result["errors"][:20]:
            print(f"  {error}")
    return 0 if result["ok"] else 1


def cmd_catalog(args) -> int:
    store = _store(args)
    filters = catalog_mod.parse_filters(args)
    text = catalog_mod.render(
        store,
        filters,
        limit=args.limit,
        sort=args.sort,
        random_seed=args.seed if args.random else None,
        as_json=args.json,
    )
    _print(_charge(args, "catalog", None, text))
    return 0


def cmd_songmap(args) -> int:
    store = _store(args)
    text, payload = songmap(store, args.song_id, max_chars=args.max_chars)
    if args.json:
        output = json.dumps(payload, ensure_ascii=False)
        output = textcap.enforce("songmap", output, args.max_chars)
    else:
        output = text
    _print(_charge(args, "songmap", args.song_id, output))
    return 0


def cmd_slice(args) -> int:
    store = _store(args)
    result = slice_song(
        store,
        args.song_id,
        args.bars,
        voice=args.voice,
        to_key=args.to_key,
        transpose=args.transpose,
        unit=args.unit,
        strip_chords=not args.keep_chords,
        max_bars=args.max_bars,
        allow_lossy=args.allow_lossy,
        emit="json" if args.emit == "json" else "abc",
    )
    if args.emit == "json" or args.json:
        output = json.dumps(result, ensure_ascii=False)
        output = textcap.enforce("slice", output)
    else:
        output = result["text"]
    _print(_charge(args, "slice", args.song_id, output))
    return 0


def cmd_motif(args) -> int:
    store = _store(args)
    if args.contour:
        rows, total = query_contour(
            store,
            contour=args.contour,
            degree_start=args.degree_start,
            degree_end=args.degree_end,
            bars=args.bars_window,
            voice=args.voice,
            limit=args.limit,
            source_song=args.song,
        )
        text = render_motif(rows, total, as_json=args.json, contour=True)
    else:
        rows, total = query(
            store,
            intervals=args.intervals,
            durations=args.durations,
            voice=args.voice,
            min_run=args.min_run,
            limit=args.limit,
            allow_trivial=args.allow_trivial,
            song_id=args.song,
        )
        text = render_motif(rows, total, as_json=args.json, contour=False)
    _print(_charge(args, "motif-find", None, text))
    return 0


def cmd_remix_check(args) -> int:
    store = _store(args)
    report = remix_check(
        store,
        args.score,
        args.plan,
        require_final_rest=args.require_final_rest,
        strict_style=args.strict_style,
        strict_quotes=args.strict_quotes,
        fail_on_undeclared=args.fail_on_undeclared,
        tolerance=args.tolerance,
        ostris_dir=args.ostris_data,
    )
    if args.report:
        path = Path(args.report)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    if args.json:
        _print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        _print(render_check(report))
    return 0 if report["pass"] else 1


def cmd_budget(args) -> int:
    ledger = Ledger.open(args.ledger, args.cap)
    if args.reset:
        ledger.reset()
        if args.json:
            _print(json.dumps(ledger.summary(), indent=2))
        else:
            print(f"ledger reset: {ledger.path}")
        return 0
    summary = ledger.summary()
    if args.json:
        _print(json.dumps(summary, indent=2))
    else:
        print(f"ledger: {summary['ledger']}")
        print(
            f"used {summary['total']} / {summary['cap']} chars | "
            f"remaining {summary['remaining']} | calls {summary['calls']}"
        )
        for tool, chars in summary["per_tool"].items():
            print(f"  {tool}: {chars}")
    return 0


def cmd_contract(args) -> int:
    from ostris.contract import SKILL_VERSION, verify as verify_contract
    checks = verify_contract()
    ok = all(check["ok"] for check in checks)
    if args.json:
        _print(json.dumps({"skill_version": SKILL_VERSION, "checks": checks, "ok": ok},
                          indent=2))
    else:
        print(f"remixer {shared.REMIX_VERSION} on skill {SKILL_VERSION}: "
              f"{'pinned' if ok else 'DRIFTED'}")
        for check in checks:
            print(f"  {check['artifact']}: {check['detail']}")
    return 0 if ok else 1


def _add_library(parser):
    parser.add_argument("--library", type=Path, default=None,
                        help="remixer store (default: <skill>/data/remix)")
    parser.add_argument("--ledger", type=Path, default=None,
                        help="session ledger path (default: ./.remix-ledger.jsonl)")
    parser.add_argument("--cap", type=int, default=None,
                        help="session character budget (default: 30000)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="remix_cli.py",
        description="Library-aware remix tools: catalog, songmap, slice, motif-find, remix check.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    library = sub.add_parser("library", help="build or verify the remix store")
    library_sub = library.add_subparsers(dest="library_command", required=True)
    build_parser = library_sub.add_parser("build", help="build songs, catalog and index")
    build_parser.add_argument("--dataset", choices=("suno", "ostris"), default="suno")
    build_parser.add_argument("--data", type=Path, default=None,
                              help="canonical SUNO bundle (default: <repo>/data/suno)")
    build_parser.add_argument("--ostris-data", type=Path, default=None,
                              help="legacy OSTRIS data; only with --dataset ostris")
    build_parser.add_argument("--out", type=Path, default=None)
    build_parser.add_argument("--include-all", action="store_true")
    build_parser.add_argument("--quality-min", type=float, default=0.8)
    build_parser.add_argument("--timestamp", action="store_true")
    build_parser.add_argument("--json", action="store_true")
    build_parser.set_defaults(func=cmd_library_build)
    verify_parser = library_sub.add_parser("verify", help="re-parse every stored song")
    _add_library(verify_parser)
    verify_parser.add_argument("--json", action="store_true")
    verify_parser.set_defaults(func=cmd_library_verify)

    catalog = sub.add_parser("catalog", help="filtered, capped song discovery")
    _add_library(catalog)
    catalog.add_argument("--key")
    catalog.add_argument("--mode", choices=("major", "minor"))
    catalog.add_argument("--meter")
    catalog.add_argument("--tempo")
    catalog.add_argument("--bars")
    catalog.add_argument("--density", choices=("light", "medium", "busy"))
    catalog.add_argument("--title")
    catalog.add_argument("--artist")
    catalog.add_argument("--source")
    catalog.add_argument("--sort", default="bars",
                         choices=("quality", "density", "bars", "tempo", "title"))
    catalog.add_argument("--limit", type=int, default=15)
    catalog.add_argument("--random", action="store_true")
    catalog.add_argument("--seed", type=int, default=None)
    catalog.add_argument("--json", action="store_true")
    catalog.set_defaults(func=cmd_catalog)

    songmap_parser = sub.add_parser("songmap", help="structure, hooks and cadences")
    _add_library(songmap_parser)
    songmap_parser.add_argument("song_id")
    songmap_parser.add_argument("--max-chars", type=int, default=3000)
    songmap_parser.add_argument("--json", action="store_true")
    songmap_parser.set_defaults(func=cmd_songmap)

    slice_parser = sub.add_parser("slice", help="extract a bounded, dialect-safe bar range")
    _add_library(slice_parser)
    slice_parser.add_argument("song_id")
    slice_parser.add_argument("--bars", required=True)
    slice_parser.add_argument("--voice", choices=("Vocal", "Ins", "both"), default="both")
    slice_parser.add_argument("--to-key", default=None)
    slice_parser.add_argument("--transpose", type=int, default=0)
    slice_parser.add_argument("--unit", default="auto")
    slice_parser.add_argument("--keep-chords", action="store_true")
    slice_parser.add_argument("--max-bars", type=int, default=8)
    slice_parser.add_argument("--allow-lossy", action="store_true")
    slice_parser.add_argument("--emit", choices=("abc", "json"), default="abc")
    slice_parser.add_argument("--json", action="store_true")
    slice_parser.set_defaults(func=cmd_slice)

    motif = sub.add_parser("motif-find", help="interval/rhythm/contour search")
    _add_library(motif)
    motif.add_argument("--intervals")
    motif.add_argument("--durations")
    motif.add_argument("--contour", choices=("up", "down", "wave", "flat"))
    motif.add_argument("--degree-start", type=int, default=None)
    motif.add_argument("--degree-end", type=int, default=None)
    motif.add_argument("--bars", "--bars-window", dest="bars_window", type=int, default=2)
    motif.add_argument("--voice", choices=("Vocal", "Ins", "both"), default="both")
    motif.add_argument("--min-run", type=int, default=4)
    motif.add_argument("--limit", type=int, default=10)
    motif.add_argument("--allow-trivial", action="store_true")
    motif.add_argument("--song", default=None, help="restrict to one source song")
    motif.add_argument("--json", action="store_true")
    motif.set_defaults(func=cmd_motif)

    remix = sub.add_parser("remix", help="remix-specific checks")
    remix_sub = remix.add_subparsers(dest="remix_command", required=True)
    check_parser = remix_sub.add_parser("check", help="verify quotes and run the checker")
    _add_library(check_parser)
    check_parser.add_argument("score", type=Path)
    check_parser.add_argument("--plan", type=Path, required=True)
    check_parser.add_argument("--report", type=Path, default=None)
    check_parser.add_argument("--ostris-data", type=Path, default=None)
    check_parser.add_argument("--require-final-rest", action="store_true")
    check_parser.add_argument("--strict-style", action="store_true")
    check_parser.add_argument("--strict-quotes", action="store_true")
    check_parser.add_argument("--fail-on-undeclared", action="store_true")
    check_parser.add_argument("--tolerance", type=int, default=0)
    check_parser.add_argument("--json", action="store_true")
    check_parser.set_defaults(func=cmd_remix_check)

    budget = sub.add_parser("budget", help="show or reset the session ledger")
    budget.add_argument("--ledger", type=Path, default=None)
    budget.add_argument("--cap", type=int, default=None)
    budget.add_argument("--reset", action="store_true")
    budget.add_argument("--json", action="store_true")
    budget.set_defaults(func=cmd_budget)

    contract = sub.add_parser("contract", help="verify the vendored skill runtime")
    contract.add_argument("--json", action="store_true")
    contract.set_defaults(func=cmd_contract)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except RemixError as error:
        print(f"remix: {error}", file=sys.stderr)
        return error.code
    except BrokenPipeError:
        return 0

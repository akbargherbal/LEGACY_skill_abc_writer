"""M6: the objective half of evaluation.

Two things are measurable without a blind listener:

* a deterministic held-out split (generation vs retrieval);
* for supplied runs, the skill checker's contract/sanity result, the bars
  deviation from the plan, and artifact size.

Subjective quality and a true token reduction need model instrumentation and a
judge; the report marks those ``quality_evaluated: false`` instead of inventing
numbers.  The 35 held-out tracks were never part of the library.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

from .check import check
from .links import held_out_yt500, load_inventory
from .sources import Cache, SourceError

SPLIT_VERSION = "m6-v1"
GENERATION_MIN = 12
GENERATION_MAX = 16
GENERATION_N = 14


def build_split(cache_dir: str | Path, out_dir: str | Path) -> dict:
    cache = Cache(cache_dir)
    out = Path(out_dir)
    inv = load_inventory(cache)
    held = held_out_yt500(inv)
    abc_by_video = {track.get("video_id"): bool(track.get("abc")) for track in inv.yt_tracks}

    usable = []
    no_abc = []
    for track in held:
        row = {
            "track_id": track.get("track_id"),
            "video_id": track.get("video_id"),
            "title": track.get("title"),
            "source_rank": track.get("source_rank"),
            "duration_s": track.get("duration_s"),
        }
        if abc_by_video.get(track.get("video_id")):
            usable.append(row)
        else:
            no_abc.append(row)
    usable.sort(key=lambda row: float(row.get("source_rank") or 0))
    generation = usable[:GENERATION_N]
    retrieval = usable[GENERATION_N:]

    split = {
        "stage": "M6-split",
        "version": SPLIT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "held_out": len(held),
        "usable": len(usable),
        "no_abc": no_abc,
        "generation": generation,
        "retrieval": retrieval,
        "rule": f"first {GENERATION_N} usable held-out tracks by source rank",
        "maqam_conditioned": False,
        "limitations": [
            "The split is deterministic and unlabelled; no maqam stratification is possible.",
            "Four held-out tracks have no ABC and cannot enter either side.",
            "Quality is not evaluated by this stage.",
        ],
    }
    checks = [
        {
            "name": "usable_held_out",
            "required": True,
            "ok": len(usable) + len(no_abc) == len(held),
            "detail": f"{len(usable)} usable + {len(no_abc)} without ABC = {len(held)}",
        },
        {
            "name": "generation_size",
            "required": True,
            "ok": min(GENERATION_MIN, len(usable)) <= len(generation) <= GENERATION_MAX,
            "detail": f"{len(generation)} tracks reserved for generation "
                      f"(target {GENERATION_MIN}-{GENERATION_MAX}; "
                      f"small corpora keep every usable track)",
        },
        {
            "name": "disjoint",
            "required": True,
            "ok": not ({row["track_id"] for row in generation}
                       & {row["track_id"] for row in retrieval}),
            "detail": "generation and retrieval lists do not overlap",
        },
    ]
    split["checks"] = checks
    split["gate_pass"] = all(item["ok"] for item in checks)
    folder = out / "eval"
    folder.mkdir(parents=True, exist_ok=True)
    split_path = folder / "split.json"
    split_path.write_text(
        json.dumps(split, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    split["files"] = {"split": str(split_path)}
    return split


def _find_runs(folder: Path) -> list[tuple[str, Path, Path]]:
    runs = []
    for child in sorted(folder.iterdir()):
        if not child.is_dir():
            continue
        score = child / "score.abc"
        plan = child / "skill_plan.json"
        if not plan.is_file():
            plan = child / "plan.json"
        if score.is_file() and plan.is_file():
            runs.append((child.name, score, plan))
    return runs


def score_runs(runs_dir: str | Path, out_dir: str | Path) -> dict:
    folder = Path(runs_dir)
    if not folder.is_dir():
        raise SourceError(f"missing runs directory: {folder}")
    out = Path(out_dir)
    runs = _find_runs(folder)
    if not runs:
        raise SourceError(
            f"no runs found under {folder}; expected <id>/score.abc + <id>/skill_plan.json"
        )

    rows = []
    for run_id, score, plan in runs:
        # Evaluation runs are supplied scores without lyric files; the caller
        # already accepted that limitation, so record an explicit waiver.
        report = check(score, plan, out_dir=out, require_final_rest=False,
                       waive_lyrics=True)
        text = score.read_text(encoding="utf-8")
        plan_data = json.loads(plan.read_text(encoding="utf-8"))
        measured = report.get("measured", {})
        bars = measured.get("bars")
        bars_plan = plan_data.get("bars")
        rows.append(
            {
                "run": run_id,
                "class": report["class"],
                "pass": report["pass"],
                "failures": [item["code"] for item in report["failures"]],
                "warnings": [item["code"] for item in report["warnings"]],
                "contract_sanity_ok": report["pass"] and all(
                    item["class"] in ("contract", "sanity", "structure")
                    for item in report["failures"]
                ),
                "bars": bars,
                "bars_plan": bars_plan,
                "bars_delta": (bars - bars_plan) if bars and bars_plan else None,
                "chars": len(text),
                "tokens_proxy": math.ceil(len(text) / 4),
                "seconds": measured.get("seconds"),
            }
        )

    passed = sum(1 for row in rows if row["contract_sanity_ok"])
    deltas = [row["bars_delta"] for row in rows if row["bars_delta"] is not None]
    report = {
        "stage": "M6-eval",
        "version": SPLIT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "runs_dir": str(folder),
        "runs": rows,
        "aggregate": {
            "runs": len(rows),
            "contract_sanity_pass": passed,
            "contract_sanity_rate": round(passed / len(rows), 3),
            "median_bars_delta": sorted(deltas)[len(deltas) // 2] if deltas else None,
            "artifact_chars": sum(row["chars"] for row in rows),
            "tokens_proxy": sum(row["tokens_proxy"] for row in rows),
        },
        "quality_evaluated": False,
        "token_reduction_measured": False,
        "maqam_conditioned": False,
        "limitations": [
            "Quality and blind non-inferiority need a judge; not claimed here.",
            "tokens_proxy is characters/4 for the score only, not a model token count.",
            "A token reduction needs both prompt-only and tool-assisted runs.",
        ],
    }
    report["gate_pass"] = passed == len(rows)
    report["checks"] = [
        {
            "name": "contract_sanity",
            "required": True,
            "ok": passed == len(rows),
            "detail": f"{passed}/{len(rows)} runs pass contract+sanity",
        },
        {
            "name": "quality_evaluated",
            "required": False,
            "ok": False,
            "detail": "no blind quality evaluation is available",
        },
    ]
    eval_folder = out / "eval"
    eval_folder.mkdir(parents=True, exist_ok=True)
    report_path = eval_folder / "report.json"
    report_path.write_text(
        json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    report["files"] = {"report": str(report_path)}
    return report

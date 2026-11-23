"""M4: interval k-gram similarity over the idiom bank.

The index is JSON because the skill is standard-library only on CPU.  This is
a documentation deviation from the plan's ``.npz``; it keeps the tool
dependency-free and is small enough (a few MB).

Build::

    ostris_cli.py similarity --out analysis/out/ostris --build

Query::

    ostris_cli.py similarity --out analysis/out/ostris --score score.abc
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .idioms import load_idioms
from .sources import SourceError

_SCRIPTS = Path(__file__).resolve().parents[1]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import abc_tools  # noqa: E402

INDEX_VERSION = "m4-v1"
K_VALUES = (3, 4)
QUOTATION_RUN = 8


def _grams(intervals: list[int]) -> list[str]:
    grams = []
    for k in K_VALUES:
        if len(intervals) < k:
            continue
        for index in range(len(intervals) - k + 1):
            grams.append(f"{k}:" + ",".join(str(value) for value in intervals[index:index + k]))
    return grams


def build_index(out_dir: str | Path) -> dict:
    out = Path(out_dir)
    rows = load_idioms(out)
    idioms = {}
    posts: dict[str, list[str]] = {}
    for row in rows:
        idiom_id = row["id"]
        intervals = [int(value) for value in row.get("intervals", [])]
        idioms[idiom_id] = {
            "track_id": row.get("track_id"),
            "function": row.get("function"),
            "bars": row.get("bars"),
            "start_bar": row.get("start_bar"),
            "end_bar": row.get("end_bar"),
            "intervals": intervals,
            "durations": row.get("durations", []),
        }
        for gram in _grams(intervals):
            posts.setdefault(gram, []).append(idiom_id)

    folder = out / "similarity"
    folder.mkdir(parents=True, exist_ok=True)
    index = {
        "stage": "M4-similarity",
        "version": INDEX_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "k_values": list(K_VALUES),
        "idioms": idioms,
        "grams": posts,
        "maqam_conditioned": False,
        "limitations": [
            "Similarity is interval-based and structural; it does not judge quality.",
            "A shared run is not a quotation unless the caller declares the source.",
        ],
    }
    path = folder / "index.json"
    path.write_text(
        json.dumps(index, separators=(",", ":"), ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    summary = {
        "stage": "M4-similarity",
        "index": str(path),
        "idioms": len(idioms),
        "grams": len(posts),
        "gate_pass": len(idioms) > 0 and len(posts) > 0,
        "checks": [
            {
                "name": "index_populated",
                "required": True,
                "ok": len(idioms) > 0 and len(posts) > 0,
                "detail": f"{len(idioms)} idioms, {len(posts)} distinct grams",
            },
            {
                "name": "unique_ids",
                "required": True,
                "ok": len(idioms) == len(rows),
                "detail": f"{len(idioms)} indexed / {len(rows)} rows",
            },
        ],
    }
    (folder / "similarity.json").write_text(
        json.dumps(summary, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return summary


def load_index(out_dir: str | Path) -> dict:
    path = Path(out_dir) / "similarity" / "index.json"
    if not path.is_file():
        raise SourceError(f"missing {path}; run `ostris_cli.py similarity --build` first")
    return json.loads(path.read_text(encoding="utf-8"))


def _longest_run(left: list[int], right: list[int]) -> int:
    if not left or not right:
        return 0
    best = 0
    previous = [0] * (len(right) + 1)
    for a in left:
        current = [0] * (len(right) + 1)
        for index, b in enumerate(right, start=1):
            if a == b:
                current[index] = previous[index - 1] + 1
                if current[index] > best:
                    best = current[index]
        previous = current
    return best


def _phrase_intervals(text: str) -> list[dict]:
    score = abc_tools.parse(text)
    vocal = score.voices["Vocal"]
    if not vocal.notes or not vocal.bars:
        return []
    starts = [bar[0] for bar in vocal.bars]
    from bisect import bisect_right

    active = set()
    for onset, _pitch, _duration in vocal.notes:
        index = bisect_right(starts, onset) - 1
        if index < 0:
            continue
        start, length, _meter = vocal.bars[index]
        if onset < start + length:
            active.add(index)
    if not active:
        return []
    ordered = sorted(active)
    runs = []
    start = previous = ordered[0]
    for index in ordered[1:]:
        if index == previous + 1:
            previous = index
            continue
        runs.append((start, previous))
        start = previous = index
    runs.append((start, previous))

    phrases = []
    for first, last in runs:
        lower = vocal.bars[first][0]
        upper = vocal.bars[last][0] + vocal.bars[last][1]
        pitches = [note[1] for note in vocal.notes if lower <= note[0] < upper]
        if len(pitches) < 2:
            continue
        phrases.append(
            {
                "start_bar": first + 1,
                "end_bar": last + 1,
                "intervals": [b - a for a, b in zip(pitches, pitches[1:])],
            }
        )
    return phrases


def query_score_text(text: str, index: dict, *, top: int = 5) -> dict:
    phrases = _phrase_intervals(text)
    idioms = index.get("idioms", {})
    posts = index.get("grams", {})
    matches: list[dict] = []
    seen: set[str] = set()
    for phrase in phrases:
        counts: Counter[str] = Counter()
        for gram in _grams(phrase["intervals"]):
            for idiom_id in posts.get(gram, []):
                counts[idiom_id] += 1
        for idiom_id, score in counts.most_common(top):
            if idiom_id in seen:
                continue
            seen.add(idiom_id)
            idiom = idioms.get(idiom_id)
            if not idiom:
                continue
            run = _longest_run(phrase["intervals"], idiom["intervals"])
            matches.append(
                {
                    "idiom": idiom_id,
                    "track_id": idiom.get("track_id"),
                    "function": idiom.get("function"),
                    "score": score,
                    "max_shared_run": run,
                    "query_bar_range": [phrase["start_bar"], phrase["end_bar"]],
                    "source_bar_range": [idiom.get("start_bar"), idiom.get("end_bar")],
                }
            )
    matches.sort(key=lambda item: (item["max_shared_run"], item["score"]), reverse=True)
    matches = matches[:top]
    best = matches[0] if matches else None
    run = best["max_shared_run"] if best else 0
    quotation = {
        "used": run >= QUOTATION_RUN,
        "source_id": best["idiom"] if best and run >= QUOTATION_RUN else None,
        "bars": run,
        "confidence": round(min(1.0, run / 16), 2),
    }
    return {
        "query": {"phrases": len(phrases), "notes": sum(len(p["intervals"]) + 1 for p in phrases)},
        "matches": matches,
        "max_shared_run": run,
        "source": best["idiom"] if best else None,
        "bar_range": best["query_bar_range"] if best else None,
        "quotation": quotation,
        "maqam_conditioned": False,
    }


def query_file(score_path: str | Path, out_dir: str | Path, *, top: int = 5) -> dict:
    score_path = Path(score_path)
    if not score_path.is_file():
        raise SourceError(f"missing score: {score_path}")
    try:
        text = score_path.read_text(encoding="utf-8")
        return query_score_text(text, load_index(out_dir), top=top)
    except abc_tools.AbcError as error:
        raise SourceError(f"{score_path}: {error}") from error

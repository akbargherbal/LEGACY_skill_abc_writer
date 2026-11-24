"""Shared test helpers for the remixer suite."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
REPO = SKILL.parent
STORE = SKILL / "data" / "remix"
OSTRIS = REPO / "02_maqam-score" / "data" / "ostris"

sys.path.insert(0, str(SKILL / "scripts"))

from remix.store import Store, voice_notes  # noqa: E402

SAMPLE_SONG = "yt500-0001-fbK2ySlxAW4"


def store() -> Store:
    return Store(STORE).require()


def sample_score_id() -> str:
    rows = store().load_catalog()
    return rows[0]["song_id"]


def plan_payload(*, key="Fm", tempo=70, meter="2/4", unit="1/16", bars=4,
                 syllables=4, remix=None):
    payload = {
        "key": key,
        "tempo": tempo,
        "meter": meter,
        "unit": unit,
        "bars": bars,
        "syllables": syllables,
        "sections": ["intro"],
        "melisma_min": 1.0,
        "melisma_max": 1.8,
        "register": {"mean": 78, "top": 84, "tolerance": 6},
        "max_top_duration_share": 0.85,
        "min_distinct_durations": 3,
        "ties_min": 0,
        "min_fill_notes": 0,
        "chords_min": 0,
        "ins_active_share_min": 0.0,
        "max_unbroken_seconds": 23,
        "min_phrase_endings": 1,
        "maqam": None,
        "maqam_conditioned": False,
        "cadence": "any",
    }
    if remix is not None:
        payload["remix"] = remix
    return payload


def write_json(path: Path, payload) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    return path

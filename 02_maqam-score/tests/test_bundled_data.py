#!/usr/bin/env python3
"""Tests for the corpus artifacts bundled with the skill.

These assert the promise in ``SKILL.md`` §8: the reader commands work offline
from ``<skill>/data/ostris/`` with no flags, and the bundle contains no audio.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))

from ostris.check import check  # noqa: E402
from ostris.cli import BUNDLED_DATA  # noqa: E402
from ostris.idioms import load_idioms, pick_idioms  # noqa: E402
from ostris.plan import build_plan  # noqa: E402
from ostris.priors import load_priors  # noqa: E402
from ostris.similarity import load_index, query_score_text  # noqa: E402

REQUIRED = (
    "records.jsonl",
    "held_out.jsonl",
    "priors/priors.json",
    "idioms.jsonl",
    "similarity/index.json",
    "eval/split.json",
    "source/TRANSCRIPTS/YT500/_manifest.jsonl",
    "source/OSTRIS_Arabic_Suno_Finetuning/arabic_instrumental_dataset_manifest.json",
)


class BundledDataTest(unittest.TestCase):
    def test_bundle_location_is_inside_the_skill(self):
        self.assertTrue(BUNDLED_DATA.is_dir(), BUNDLED_DATA)
        self.assertEqual(BUNDLED_DATA, SKILL / "data" / "ostris")

    def test_required_artifacts_exist(self):
        for rel in REQUIRED:
            with self.subTest(rel=rel):
                self.assertTrue((BUNDLED_DATA / rel).is_file(), rel)

    def test_priors_load_and_stay_objective(self):
        priors = load_priors(BUNDLED_DATA)
        self.assertFalse(priors.get("maqam_conditioned"))
        self.assertGreater(len(priors.get("strata", {})), 0)

    def test_idioms_and_similarity_index_load(self):
        rows = load_idioms(BUNDLED_DATA)
        self.assertGreater(len(rows), 0)
        self.assertTrue(pick_idioms(rows, function="cadence", bars=4, limit=1))

        index = load_index(BUNDLED_DATA)
        self.assertFalse(index.get("maqam_conditioned"))
        self.assertGreater(len(index.get("idioms", {})), 0)

    def test_plan_runs_from_bundled_priors(self):
        manifest = {
            "title": "Bundle check",
            "key": "C",
            "tempo": 120,
            "meter": "4/4",
            "bars": 8,
            "sections": ["intro", "verse 1"],
        }
        with tempfile.TemporaryDirectory() as tmp:
            result = build_plan(manifest, load_priors(BUNDLED_DATA), tmp)
        self.assertTrue(result["brief"]["gate_pass"])
        self.assertIn("skill_plan.json", result["brief"]["files"]["plan"])

    def test_check_uses_bundled_priors_and_similarity(self):
        score = SKILL / "example" / "score.abc"
        plan = SKILL / "example" / "plan.json"
        report = check(score, plan, out_dir=BUNDLED_DATA)
        self.assertTrue(report["pass"], report["failures"])
        self.assertIsNotNone(report.get("prior"))
        self.assertIsNotNone(report.get("similarity"))

    def test_bundle_has_no_audio_and_is_small(self):
        audio = [
            path
            for path in BUNDLED_DATA.rglob("*")
            if path.is_file() and path.suffix.lower() in {".wav", ".mp3", ".flac", ".m4a"}
        ]
        self.assertEqual(audio, [])
        total = sum(path.stat().st_size for path in BUNDLED_DATA.rglob("*") if path.is_file())
        self.assertLess(total, 20 * 1024 * 1024, f"bundle is {total} bytes")

    def test_bundle_records_are_json_lines(self):
        path = BUNDLED_DATA / "records.jsonl"
        with path.open(encoding="utf-8") as handle:
            first = json.loads(handle.readline())
        self.assertEqual(first.get("id"), "yt500-0001-fbK2ySlxAW4")


if __name__ == "__main__":
    unittest.main()

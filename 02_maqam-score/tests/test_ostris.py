#!/usr/bin/env python3
"""Regression tests for the OSTRIS M0 audit and M1 canonical build."""
from __future__ import annotations

import csv
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))

from ostris.audit import audit  # noqa: E402
from ostris.build import build  # noqa: E402
from ostris.canonical import canonicalize  # noqa: E402
from ostris.contract import SKILL_VERSION, verify  # noqa: E402
from ostris.features import build_features, extract_features  # noqa: E402
from ostris.links import FADL_SLUG_TO_STEM, rel_from_uri  # noqa: E402
from ostris.mode import classify_mode, key_info  # noqa: E402
from ostris.parse import parse_abc  # noqa: E402

ABC = """X:1
T:
M:4/4
L:1/16
Q:1/4=120
V: Vocal clef=treble name="Vocal Melody" snm="Vocal"
V: Ins clef=treble name="Ins Melody" snm="Inst."
K:C
% intro
V: Vocal
"C"C4D4E4F4|G8z8|"C"C4D4E4F4|G8z8|
V: Ins
C2D2E2F2G2A2B2c2|C8z8|C2D2E2F2G2A2B2c2|C8z8|
% verse
V: Vocal
"C"C4D4E4F4|G8z8|"C"C4D4E4F4|G8z8|
V: Ins
C2D2E2F2G2A2B2c2|C8z8|C2D2E2F2G2A2B2c2|C8z8|
"""

REFERENCE_ABC = """X:1
T:
M:4/4
L:1/32
Q:1/4=120
V: Vocal clef=treble name="Vocal Melody" snm="Vocal"
V: Ins clef=treble name="Ins Melody" snm="Inst."
K:C
% intro
V: Vocal
"C"z32|"C"z32|"C"z32|"C"z32|
V: Ins
C4D4E4F4G4A4B4c4|C16z16|C4D4E4F4G4A4B4c4|C16z16|
% verse
V: Vocal
"C"z32|"C"z32|"C"z32|"C"z32|
V: Ins
C4D4E4F4G4A4B4c4|C16z16|C4D4E4F4G4A4B4c4|C16z16|
"""


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class OstrisFixture:
    def __init__(self, root: Path):
        self.root = root
        self._build()

    def _build(self) -> None:
        tracks = [
            {
                "out_name": "yt500-0001-vidA",
                "source_dataset": "yt500",
                "title": "A",
                "artist": "X",
                "audio_duration_s": 16.0,
                "audio_sha256": "a" * 64,
                "source_uri": "gs://bucket/DATASET/yt500_instrumental/tracks/yt500-0001-vidA",
            },
            {
                "out_name": "yt500-0002-vidB",
                "source_dataset": "yt500",
                "title": "B",
                "artist": "X",
                "audio_duration_s": 16.0,
                "audio_sha256": "b" * 64,
                "source_uri": "gs://bucket/DATASET/yt500_instrumental/tracks/yt500-0002-vidB",
            },
            {
                "out_name": "fs18-al_hal_1",
                "source_dataset": "fadhl_shaker_shortlist",
                "title": "al_hal",
                "artist": "Fadl Shaker",
                "audio_duration_s": 16.0,
                "audio_sha256": "c" * 64,
                "source_uri": "gs://bucket/DATASET/fadhl_shaker_instrumental_18_shortlist/tracks/fs18-al_hal_1",
            },
        ]
        write_json(
            self.root / "OSTRIS_Arabic_Suno_Finetuning/arabic_instrumental_dataset_manifest.json",
            {
                "count": 3,
                "audio_bytes": 3,
                "audio_hours": 1.0,
                "sources": [],
                "checks": {},
                "tracks": tracks,
            },
        )
        write_json(
            self.root / "OSTRIS_Arabic_Suno_Finetuning/v3_arabmaqamrock_dataset_manifest.json",
            {"count": 1, "tracks": [{"maqam": "Hijaz"}]},
        )
        header = {
            "record": "header",
            "counts": {
                "n_transcribed": 3,
                "n_shards": 1,
                "n_duplicate_groups": 1,
                "n_duplicate_tracks": 2,
            },
        }
        yt_tracks = [
            {
                "record": "track",
                "track_id": "YT500/shard-01/0001_vidA",
                "video_id": "vidA",
                "source_rank": 1,
                "title": "A",
                "source_artist": "X",
                "duration_s": 16.0,
                "duplicate_group": "X | A",
                "duplicate_of": None,
            },
            {
                "record": "track",
                "track_id": "YT500/shard-01/0002_vidB",
                "video_id": "vidB",
                "source_rank": 2,
                "title": "B",
                "source_artist": "X",
                "duration_s": 16.0,
                "duplicate_group": "X | A",
                "duplicate_of": "YT500/shard-01/0001_vidA",
            },
            {
                "record": "track",
                "track_id": "YT500/shard-01/0003_vidC",
                "video_id": "vidC",
                "source_rank": 3,
                "title": "C",
                "source_artist": "X",
                "duration_s": 16.0,
                "duplicate_group": None,
                "duplicate_of": None,
            },
        ]
        write_text(
            self.root / "TRANSCRIPTS/YT500/_manifest.jsonl",
            "\n".join(json.dumps(row) for row in [header, *yt_tracks]) + "\n",
        )
        shard_tracks = []
        for track in yt_tracks:
            shard_tracks.append(
                {
                    "track_id": track["track_id"],
                    "video_id": track["video_id"],
                    "source_rank": track["source_rank"],
                    "title": track["title"],
                    "artist": track["source_artist"],
                    "duration_s": 16.0,
                    "abc": ABC,
                    "transcribe_status": "ok",
                    "duplicate_of": track["duplicate_of"],
                    "raw_gcs": f"gs://bucket/TRANSCRIPTS/YT500/YT500/shard-01/{track['video_id']}.tar.gz",
                    "qc": {"flags": [], "coverage": 1.0, "sections": 1},
                }
            )
        write_json(
            self.root / "TRANSCRIPTS/YT500/YT500/abc/shard-01.json",
            {"tracks": shard_tracks},
        )
        write_json(
            self.root / "DATASET/fadhl_shaker_instrumental_18_shortlist/shortlist.json",
            {
                "counts": {"cohort": 1},
                "tracks": [
                    {
                        "name": "fs18-al_hal_1",
                        "source_track_id": "run/al_hal_1",
                        "input_uri": "gs://bucket/DATASET/fadhl_shaker_instrumental_18/abc/al_hal_1.abc",
                        "duplicate_of": None,
                    }
                ],
            },
        )
        write_text(
            self.root / "DATASET/fadhl_shaker_instrumental_18/abc/al_hal_1.abc",
            REFERENCE_ABC,
        )
        stem = FADL_SLUG_TO_STEM["al_hal"]
        write_json(
            self.root / "TRANSCRIPTS/fadhl_shaker_selected_scores/transcribe_manifest.json",
            {
                "tracks": [
                    {
                        "stem": stem,
                        "status": "ok",
                        "abc": f"/local/{stem}/score.abc",
                        "track_id": f"FADL_SHAKER/album/{stem}",
                    }
                ]
            },
        )
        write_text(
            self.root / f"TRANSCRIPTS/fadhl_shaker_selected_scores/{stem}/score.abc",
            ABC,
        )
        write_json(
            self.root / "TRANSCRIPTS/FADL_SHAKER/abc/album.json",
            {"tracks": [{"title": "al_hal", "abc": ABC}]},
        )


class ParseTests(unittest.TestCase):
    def test_valid_abc_measures_both_voices(self):
        parsed = parse_abc(ABC)
        self.assertTrue(parsed.ok, parsed.error)
        self.assertEqual(parsed.bars, 8)
        self.assertEqual(parsed.notes, {"vocal": 20, "ins": 36})
        self.assertEqual(parsed.chords, 4)
        self.assertEqual(parsed.header_meter, "4/4")

    def test_invalid_abc_fails_closed(self):
        parsed = parse_abc("not an abc file")
        self.assertFalse(parsed.ok)
        self.assertIn("Incomplete", parsed.error or "")

    def test_uri_and_title_helpers(self):
        self.assertEqual(
            rel_from_uri("gs://bucket/DATASET/x/y.abc"), "DATASET/x/y.abc"
        )
        self.assertEqual(len(FADL_SLUG_TO_STEM), 22)
        self.assertEqual(FADL_SLUG_TO_STEM["al_hal"], "الحال")


class FeatureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.cache = root / "cache"
        self.out = root / "out"
        OstrisFixture(self.cache)

    def tearDown(self):
        self.tmp.cleanup()

    def test_extracts_objective_features(self):
        extraction = extract_features(ABC, source_sections=2)
        features = extraction.features
        self.assertEqual(features["bars"], 8)
        self.assertEqual(features["vocal"]["notes"], 20)
        self.assertEqual(features["ins"]["notes"], 36)
        self.assertEqual(features["harmony"]["chords"], 4)
        self.assertEqual(features["meter"]["declared"], ["4/4"])
        self.assertEqual(features["key"]["name"], "C")
        self.assertEqual(features["key"]["mode"], "major")
        self.assertIsNone(features["maqam"])
        self.assertEqual(features["maqam_source"], "unlabelled")
        self.assertFalse(features["maqam_reviewed"])
        self.assertFalse(extraction.mode["reviewed"])
        self.assertEqual(extraction.mode["family"], "major_like")

    def test_mode_templates(self):
        major = [(60, 1), (62, 1), (64, 1), (65, 1), (67, 1), (69, 1), (71, 1)]
        hijaz = [(60, 1), (61, 1), (64, 1), (65, 1), (67, 1), (68, 1), (70, 1)]
        self.assertEqual(classify_mode("C", major).family, "major_like")
        self.assertEqual(classify_mode("C", hijaz).family, "hijaz_like")
        info = key_info("F#m")
        self.assertEqual(info["tonic_pc"], 6)
        self.assertEqual(info["mode"], "minor")

    def test_features_cover_all_records_without_maqam(self):
        audit(self.cache, self.out)
        build(self.cache, self.out)
        summary = build_features(self.cache, self.out)
        self.assertEqual(summary["stage"], "M2")
        self.assertEqual(summary["records"], 3)
        self.assertEqual(summary["feature_ok"], 3)
        self.assertTrue(summary["gate_pass"], summary["checks"])
        self.assertFalse(summary["maqam_conditioned"])
        self.assertFalse(summary["maqam_reviewed"])

        records = [
            json.loads(line)
            for line in (self.out / "records.jsonl").read_text().splitlines()
            if line.strip()
        ]
        for record in records:
            self.assertIsNotNone(record["features"])
            self.assertIsNone(record["maqam"])
            self.assertEqual(record["maqam_source"], "unlabelled")
            self.assertFalse(record["mode_hypothesis"]["reviewed"])
            self.assertIn(record["mode_hypothesis"]["family"], {
                "major_like", "minor_like", "phrygian_like", "hijaz_like", "unknown"
            })


class CanonicalTests(unittest.TestCase):
    def test_normalizes_line_endings_and_trailing_space(self):
        messy = ABC.replace("\n", "\r\n").replace("K:C", "K:C   ") + "  \n\n"
        canonical = canonicalize(messy)
        self.assertTrue(canonical.ok, canonical.errors)
        self.assertNotIn("\r", canonical.text)
        self.assertTrue(canonical.text.endswith("\n"))
        self.assertFalse(canonical.text.endswith("\n\n"))
        self.assertTrue(
            all(line == line.rstrip() for line in canonical.text.splitlines())
        )

    def test_preserves_per_bar_meter_and_inline_key(self):
        text = ABC.replace(
            '"C"C4D4E4F4|G8z8|',
            '"C"C4D4E4F4|G8z8|\nM:3/4\nV: Vocal\n[K:D]"C"C6D6|',
            1,
        )
        canonical = canonicalize(text)
        self.assertTrue(canonical.ok, canonical.errors)
        self.assertIn("M:3/4", canonical.text)
        self.assertIn("[K:D]", canonical.text)
        self.assertIn("3/4", canonical.meters_declared)
        self.assertEqual(canonical.inline_key_changes, 1)

    def test_missing_meter_fails_closed(self):
        canonical = canonicalize(
            "X:1\nT:\nL:1/8\nQ:1/4=100\nK:C\n"
            "V: Vocal\nC8|\nV: Ins\nC8|\n"
        )
        self.assertFalse(canonical.ok)
        self.assertIn("missing M: header", canonical.errors)

    def test_contract_pins_match_current_skill(self):
        checks = verify()
        self.assertEqual(SKILL_VERSION, "0.2.0")
        self.assertTrue(all(check["ok"] for check in checks), checks)


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.cache = root / "cache"
        self.out = root / "out"
        OstrisFixture(self.cache)

    def tearDown(self):
        self.tmp.cleanup()

    def test_audit_links_parses_and_excludes_duplicates(self):
        summary = audit(self.cache, self.out)
        self.assertEqual(summary["stage"], "M0")
        self.assertEqual(summary["inventory"]["links"]["total"], 3)
        self.assertEqual(summary["inventory"]["links"]["matched"], 3)
        self.assertEqual(summary["inventory"]["parse"]["ok"], 3)
        self.assertEqual(len(summary["held_out"]), 1)
        self.assertEqual(summary["held_out"][0]["video_id"], "vidC")

        records = [
            json.loads(line)
            for line in (self.out / "records.jsonl").read_text().splitlines()
            if line.strip()
        ]
        by_id = {record["id"]: record for record in records}
        self.assertTrue(by_id["yt500-0001-vidA"]["exclude_from_priors"])
        self.assertTrue(by_id["yt500-0002-vidB"]["exclude_from_priors"])
        self.assertIn("duplicate", by_id["yt500-0001-vidA"]["flags"])
        self.assertFalse(by_id["fs18-al_hal_1"]["exclude_from_priors"])
        self.assertEqual(by_id["fs18-al_hal_1"]["abc_kind"], "selected_source_transcript")
        self.assertEqual(by_id["fs18-al_hal_1"]["bars"], 8)

        with (self.out / "manifest_links.csv").open(encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(row["matched"] == "True" for row in rows))

        audit_json = json.loads((self.out / "audit.json").read_text())
        self.assertTrue(any(c["name"] == "parse_coverage" for c in audit_json["checks"]))
        self.assertIn("files", audit_json)

    def test_generated_records_match_schema(self):
        audit(self.cache, self.out)
        records = [
            json.loads(line)
            for line in (self.out / "records.jsonl").read_text().splitlines()
            if line.strip()
        ]
        try:
            import jsonschema
        except ImportError:  # pragma: no cover - optional in a minimal runtime
            self.skipTest("jsonschema is not installed")
        schema = json.loads(
            (SKILL / "schemas/track_record.schema.json").read_text(encoding="utf-8")
        )
        for record in records:
            jsonschema.validate(record, schema)


    def test_build_writes_canonical_files(self):
        audit(self.cache, self.out)
        summary = build(self.cache, self.out)
        self.assertEqual(summary["stage"], "M1")
        self.assertEqual(summary["records"], 3)
        self.assertEqual(summary["canonical_ok"], 3)
        self.assertTrue(summary["gate_pass"], summary["checks"])
        self.assertTrue((self.out / "canonical.json").is_file())
        self.assertTrue((self.out / "canonical.md").is_file())

        try:
            import jsonschema
        except ImportError:  # pragma: no cover - optional in a minimal runtime
            jsonschema = None
        if jsonschema:
            schema = json.loads(
                (SKILL / "schemas/canonical.schema.json").read_text(encoding="utf-8")
            )
            jsonschema.validate(
                json.loads((self.out / "canonical.json").read_text()), schema
            )

        records = [
            json.loads(line)
            for line in (self.out / "records.jsonl").read_text().splitlines()
            if line.strip()
        ]
        for record in records:
            canonical = record["canonical"]
            self.assertTrue(canonical["ok"], canonical)
            self.assertTrue(canonical["parse_ok"], canonical)
            self.assertEqual(canonical["voices"], ["Vocal", "Ins"])
            path = self.out / canonical["uri"]
            self.assertTrue(path.is_file(), path)
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(), canonical["sha256"]
            )


if __name__ == "__main__":
    unittest.main()

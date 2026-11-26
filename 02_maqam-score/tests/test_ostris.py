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
from ostris.check import check  # noqa: E402
from ostris.contract import SKILL_VERSION, verify  # noqa: E402
from ostris.eval import build_split, score_runs  # noqa: E402
from ostris.features import build_features, extract_features  # noqa: E402
from ostris.idioms import build_idioms, extract_idioms, load_idioms  # noqa: E402
from ostris.links import FADL_SLUG_TO_STEM, rel_from_uri  # noqa: E402
from ostris.mode import classify_mode, key_info  # noqa: E402
from ostris.parse import parse_abc  # noqa: E402
from ostris.plan import build_plan, validate_plan  # noqa: E402
from ostris.priors import build_priors, load_priors, select_prior  # noqa: E402
from ostris.similarity import build_index, load_index, query_score_text  # noqa: E402

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

DEMO_ABC = """X:1
T:
M:4/4
L:1/16
Q:1/4=120
V: Vocal clef=treble name="Vocal Melody" snm="Vocal"
V: Ins clef=treble name="Ins Melody" snm="Inst."
K:C
% intro
V: Vocal
"C"d2e2f4g8|"G"a8e8|"C"d6e6f4|"G"a8z8|
V: Ins
z16|z16|z16|z8c8|
% verse 1
V: Vocal
"C"d2e2f4g8|"G"a8e8|"C"d6e6f4|"G"a8z8|
V: Ins
z16|z16|z16|z8c8|
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


class OnlineTests(unittest.TestCase):
    """M3-M6: priors, plan, idioms, similarity, check, eval."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        cls.root = root
        cls.cache = root / "cache"
        cls.out = root / "out"
        OstrisFixture(cls.cache)
        audit(cls.cache, cls.out)
        build(cls.cache, cls.out)
        cls.features = build_features(cls.cache, cls.out)
        cls.priors = build_priors(cls.out)
        cls.idioms = build_idioms(cls.out)
        cls.index = build_index(cls.out)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def manifest(self, **overrides) -> dict:
        data = {
            "title": "Test",
            "key": "C",
            "tempo": 120,
            "meter": "4/4",
            "bars": 8,
            "sections": ["intro", "verse 1"],
        }
        data.update(overrides)
        return data

    def write_plan(self, name: str = "plan", **overrides):
        folder = self.root / name
        result = build_plan(self.manifest(**overrides), self.priors, folder)
        return folder, result

    def test_priors_are_objective_and_covered(self):
        priors = self.priors
        self.assertEqual(priors["stage"], "M3")
        self.assertTrue(priors["gate_pass"], priors["checks"])
        self.assertFalse(priors["maqam_conditioned"])
        self.assertEqual(priors["eligible"] + priors["excluded"], priors["records"])
        self.assertEqual(priors["strata"]["global"]["n"], priors["eligible"])
        for stratum in priors["strata"].values():
            self.assertFalse(stratum["maqam_conditioned"])
            self.assertEqual(stratum["metrics"]["bars"]["n"], stratum["n"])
        selection = select_prior(priors, meter="4/4", tempo=120, bars=8)
        self.assertIn("global", selection["backoff"])
        self.assertEqual(selection["stratum"], "global")
        self.assertTrue(load_priors(self.out)["gate_pass"])

    def test_plan_is_valid_and_not_maqam_conditioned(self):
        _folder, result = self.write_plan()
        plan = result["plan"]
        self.assertEqual(validate_plan(plan), [])
        self.assertTrue(result["brief"]["gate_pass"], result["brief"]["checks"])
        self.assertEqual(sum(plan["section_bars"]), plan["bars"])
        self.assertIsNone(plan["maqam"])
        self.assertFalse(plan["maqam_conditioned"])
        self.assertEqual(plan["voices"], "vocal+ins")
        self.assertNotIn("maqam", [key for key in plan if plan[key]])

    def test_plan_derives_bars_from_duration(self):
        folder, result = self.write_plan(
            "duration-plan", bars=None, target_duration_s=16, sections=None
        )
        plan = result["plan"]
        self.assertGreaterEqual(plan["bars"], 8)
        self.assertEqual(validate_plan(plan), [])
        self.assertTrue((folder / "brief.json").is_file())
        self.assertTrue((folder / "skill_plan.json").is_file())

    def test_check_accepts_a_matching_score(self):
        folder, _result = self.write_plan()
        score = self.root / "demo.abc"
        write_text(score, DEMO_ABC)
        report = check(score, folder / "skill_plan.json", out_dir=self.out,
                       waive_lyrics=True)
        self.assertTrue(report["pass"], report["failures"])
        self.assertIn(report["class"], {"pass", "warn"})
        self.assertFalse(report["maqam_fit"]["available"])
        self.assertIsNotNone(report["skill_report"])

    def test_check_requires_lyrics_or_explicit_waiver(self):
        """New plans must not be silently auto-waived by the ostris wrapper."""
        folder, _result = self.write_plan("lyrics-required")
        score = self.root / "lyrics-demo.abc"
        write_text(score, DEMO_ABC)
        report = check(score, folder / "skill_plan.json", out_dir=self.out)
        self.assertFalse(report["pass"])
        self.assertTrue(any(item["code"] == "lyrics prosody"
                            for item in report["failures"]), report["failures"])

    def test_check_fails_on_plan_mismatch(self):
        folder, _result = self.write_plan("mismatch", bars=9)
        score = self.root / "demo-mismatch.abc"
        write_text(score, DEMO_ABC)
        report = check(score, folder / "skill_plan.json", out_dir=self.out,
                       waive_lyrics=True)
        self.assertFalse(report["pass"])
        self.assertTrue(any(item["code"] == "bars" for item in report["failures"]))

    def test_generated_online_artifacts_match_schemas(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema is not installed")
        folder, result = self.write_plan("schema-plan")
        score = self.root / "schema-demo.abc"
        write_text(score, DEMO_ABC)
        report = check(score, folder / "skill_plan.json", out_dir=self.out,
                       waive_lyrics=True)
        split = build_split(self.cache, self.out)
        schemas = SKILL / "schemas"
        pairs = [
            (load_priors(self.out), "priors.schema.json"),
            (result["plan"], "plan.schema.json"),
            (report, "report.schema.json"),
            (split, "eval.schema.json"),
        ]
        for instance, name in pairs:
            schema = json.loads((schemas / name).read_text(encoding="utf-8"))
            jsonschema.validate(instance, schema)

    def test_cli_roundtrip_and_final_rest(self):
        import contextlib
        import io

        from ostris.cli import main

        manifest_path = self.root / "cli-manifest.json"
        write_json(manifest_path, self.manifest())
        plan_folder = self.root / "cli-plan"
        with contextlib.redirect_stdout(io.StringIO()):
            code = main([
                "plan",
                "--manifest", str(manifest_path),
                "--priors", str(self.out / "priors" / "priors.json"),
                "--out", str(plan_folder),
                "--strict",
            ])
        self.assertEqual(code, 0)
        score = self.root / "cli-demo.abc"
        write_text(score, DEMO_ABC)
        with contextlib.redirect_stdout(io.StringIO()):
            ok = main([
                "check", str(score),
                "--plan", str(plan_folder / "skill_plan.json"),
                "--out", str(self.out),
                "--waive-lyrics",
            ])
            strict = main([
                "check", str(score),
                "--plan", str(plan_folder / "skill_plan.json"),
                "--out", str(self.out),
                "--require-final-rest",
                "--waive-lyrics",
            ])
        self.assertEqual(ok, 0)
        self.assertEqual(strict, 1)

    def test_idioms_are_structural(self):
        rows = load_idioms(self.out)
        self.assertGreaterEqual(len(rows), 1)
        for row in rows:
            self.assertTrue(2 <= row["bars"] <= 4)
            self.assertFalse(row["reviewed"])
            self.assertIn(row["function"], {"opening", "phrase", "cadence"})
            self.assertNotIn("maqam", row)
        self.assertTrue(self.idioms["gate_pass"], self.idioms["checks"])
        extracted = extract_idioms(DEMO_ABC, "demo", "C")
        self.assertGreaterEqual(len(extracted), 1)
        self.assertEqual(extracted[0]["function"], "opening")

    def test_similarity_finds_shared_intervals(self):
        self.assertTrue(self.index["gate_pass"])
        result = query_score_text(ABC, load_index(self.out))
        self.assertGreaterEqual(result["max_shared_run"], 3)
        self.assertIn("quotation", result)
        self.assertFalse(result["maqam_conditioned"])

    def test_eval_split_is_deterministic(self):
        first = build_split(self.cache, self.out)
        second = build_split(self.cache, self.out)
        self.assertTrue(first["gate_pass"], first["checks"])
        self.assertEqual(
            [row["track_id"] for row in first["generation"]],
            [row["track_id"] for row in second["generation"]],
        )
        self.assertFalse(
            {row["track_id"] for row in first["generation"]}
            & {row["track_id"] for row in first["retrieval"]}
        )

    def test_eval_scores_runs_without_quality_claim(self):
        plan_folder, _result = self.write_plan("eval-plan")
        runs = self.root / "runs"
        run = runs / "demo"
        write_text(run / "score.abc", DEMO_ABC)
        write_text(run / "skill_plan.json",
                   (plan_folder / "skill_plan.json").read_text())
        report = score_runs(runs, self.out)
        self.assertTrue(report["gate_pass"], report["runs"])
        self.assertFalse(report["quality_evaluated"])
        self.assertFalse(report["token_reduction_measured"])
        self.assertEqual(report["aggregate"]["runs"], 1)


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
        self.assertEqual(SKILL_VERSION, "0.9.0")
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

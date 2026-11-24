from __future__ import annotations

import json
import unittest
from pathlib import Path

from .helpers import REPO, SKILL, STORE

from remix.quotecheck import _validate_block  # noqa: E402


class SkillTests(unittest.TestCase):
    def test_skill_frontmatter_and_prohibition(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("name: abc_remixer", text)
        self.assertIn("Never read the library files directly", text)
        self.assertIn("remix check", text)
        self.assertIn("literal_cap_bars", text)

    def test_references_and_schemas_exist(self):
        for rel in ("references/dialect.md", "references/transforms.md",
                    "schemas/remix_block.schema.json",
                    "schemas/remix_report.schema.json"):
            self.assertTrue((SKILL / rel).is_file(), rel)
        for rel in ("schemas/remix_block.schema.json",
                    "schemas/remix_report.schema.json"):
            json.loads((SKILL / rel).read_text(encoding="utf-8"))

    def test_template_plan_has_a_valid_remix_block(self):
        plan = json.loads((SKILL / "example" / "plan.template.json").read_text(encoding="utf-8"))
        self.assertEqual(_validate_block(plan["remix"]), [])
        self.assertIn("sources", plan["remix"])

    def test_store_and_runtime_are_present(self):
        self.assertTrue((STORE / "catalog.tsv").is_file())
        self.assertTrue((STORE / "index" / "manifest.json").is_file())
        self.assertTrue((SKILL / "scripts" / "remix_cli.py").is_file())
        self.assertTrue((SKILL / "scripts" / "remix" / "cli.py").is_file())

    def test_no_audio_in_store(self):
        suffixes = {".mp3", ".wav", ".flac", ".m4a"}
        found = [path for path in STORE.rglob("*") if path.is_file() and path.suffix.lower() in suffixes]
        self.assertEqual(found, [])

    def test_package_script_exists_in_the_repo(self):
        path = REPO / "scripts" / "package_remixer.sh"
        if not path.is_file():
            self.skipTest("dev-only package script is not shipped")
        self.assertTrue(path.is_file())


if __name__ == "__main__":
    unittest.main()

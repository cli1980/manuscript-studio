#!/usr/bin/env python3

import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("validate_on_demand.py")
SPEC = importlib.util.spec_from_file_location("validate_on_demand", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def write_package(path: Path, slug: str = "agent-name", *, mode: str = "fresh") -> None:
    prefix = f"agent-package/{slug}/"
    files = {
        "package-manifest.md": (
            "# Manifest\n\n"
            + (
                "- Build mode: fresh-reproduction\n"
                "- Prior on-demand source: none\n"
                if mode == "fresh"
                else "- Build mode: incremental-reuse\n"
            )
            + "\n## Included files\n\n"
            "1. package-manifest.md\n"
            "2. query-letter.md\n"
            "3. claim-audit.md\n"
            "4. submission-instructions.md\n"
            "- Synopsis requested: no\n"
        ),
        "query-letter.md": "Dear Agent,\n",
        "claim-audit.md": "All claims mapped.\n",
        "submission-instructions.md": "## Submit here\n",
    }
    with zipfile.ZipFile(path, "w") as archive:
        for name, value in files.items():
            archive.writestr(prefix + name, value)


class OnDemandValidatorTests(unittest.TestCase):
    def test_root_allows_terminal_zips_without_opening_them(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "agent-package-one.zip").write_bytes(b"not opened")
            self.assertEqual(
                MODULE.validate_root(root),
                ["agent-package-one.zip"],
            )

    def test_root_rejects_loose_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "synopsis.md").write_text("stale", encoding="utf-8")
            with self.assertRaises(MODULE.ValidationError):
                MODULE.validate_root(root)

    def test_complete_fresh_zip_passes(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "agent-package-agent-name.zip"
            write_package(path)
            report = MODULE.validate_new_zip(path)
            self.assertEqual(report["validation"], "passed")

    def test_missing_required_file_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "agent-package-agent-name.zip"
            prefix = "agent-package/agent-name/"
            manifest = (
                "- Build mode: fresh-reproduction\n"
                "- Prior on-demand source: none\n"
                "1. package-manifest.md\n"
                "2. query-letter.md\n"
                "3. submission-instructions.md\n"
            )
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr(prefix + "package-manifest.md", manifest)
                archive.writestr(prefix + "query-letter.md", "Dear Agent,\n")
                archive.writestr(
                    prefix + "submission-instructions.md",
                    "## Submit here\n",
                )
            with self.assertRaises(MODULE.ValidationError):
                MODULE.validate_new_zip(path)

    def test_reuse_declaration_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "agent-package-agent-name.zip"
            write_package(path, mode="reuse")
            with self.assertRaises(MODULE.ValidationError):
                MODULE.validate_new_zip(path)

    def test_internal_agent_slug_must_match_zip(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "agent-package-other-agent.zip"
            write_package(path, slug="agent-name")
            with self.assertRaises(MODULE.ValidationError):
                MODULE.validate_new_zip(path)


if __name__ == "__main__":
    unittest.main()

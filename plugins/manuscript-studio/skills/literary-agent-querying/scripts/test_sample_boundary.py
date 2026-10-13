#!/usr/bin/env python3

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("sample_boundary.py")
SPEC = importlib.util.spec_from_file_location("sample_boundary", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class SampleBoundaryTests(unittest.TestCase):
    SOURCE = "Chapter One\n\nFirst complete paragraph.\n\nSecond paragraph continues beyond the page cutoff.\n\nThird paragraph."

    def test_mid_paragraph_cutoff_rolls_back(self):
        sample, report = MODULE.build_sample(
            self.SOURCE, "Second paragraph continues", 10
        )
        self.assertEqual(sample, "Chapter One\n\nFirst complete paragraph.\n")
        self.assertTrue(report["rollback_applied"])
        self.assertTrue(report["validation"]["passed"])

    def test_exact_paragraph_end_is_included(self):
        sample, report = MODULE.build_sample(
            self.SOURCE, "Second paragraph continues beyond the page cutoff.", 10
        )
        self.assertTrue(sample.endswith("Second paragraph continues beyond the page cutoff.\n"))
        self.assertFalse(report["rollback_applied"])

    def test_missing_cutoff_fails(self):
        with self.assertRaises(ValueError):
            MODULE.build_sample(self.SOURCE, "not present", 10)

    def test_partial_sample_validation_fails(self):
        _, boundary = MODULE.build_sample(
            self.SOURCE, "Second paragraph continues", 10
        )
        report = MODULE.validate_sample(
            self.SOURCE,
            "Chapter One\n\nFirst complete para",
            10,
            boundary,
        )
        self.assertFalse(report["validation"]["passed"])
        self.assertFalse(report["validation"]["source_prefix_exact"])

    def test_complete_prefix_validation_passes(self):
        sample, boundary = MODULE.build_sample(
            self.SOURCE, "Second paragraph continues", 10
        )
        report = MODULE.validate_sample(
            self.SOURCE,
            sample,
            10,
            boundary,
        )
        self.assertTrue(report["validation"]["passed"])

    def test_sample_beyond_effective_end_fails_page_limit(self):
        _, boundary = MODULE.build_sample(
            self.SOURCE, "Second paragraph continues", 10
        )
        report = MODULE.validate_sample(
            self.SOURCE,
            self.SOURCE,
            10,
            boundary,
        )
        self.assertFalse(report["validation"]["within_requested_page_limit"])
        self.assertFalse(report["validation"]["passed"])


if __name__ == "__main__":
    unittest.main()

"""Local listing checks; public URL reachability is a separate release check."""

import json
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1] / "plugins/manuscript-studio"


class ListingTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((ROOT / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
        self.interface = self.manifest["interface"]

    def test_public_listing_lengths_and_three_distinct_starters(self):
        for field, limit in (("displayName", 30), ("shortDescription", 30),
                             ("longDescription", 4000), ("developerName", 80)):
            self.assertTrue(0 < len(self.interface[field]) <= limit, field)
        prompts = self.interface["defaultPrompt"]
        self.assertEqual(len(prompts), 3)
        self.assertEqual(len(set(prompts)), 3)
        self.assertTrue(all(0 < len(p) <= 128 and "@" not in p for p in prompts))

    def test_packaged_square_svg_branding_is_safe_and_self_contained(self):
        for field in ("logo", "composerIcon"):
            path = self.interface[field]
            self.assertTrue(path.startswith("./assets/"))
            image = (ROOT / path).resolve()
            self.assertTrue(image.is_relative_to(ROOT.resolve()))
            self.assertLessEqual(image.stat().st_size, 5 * 1024 * 1024)
            tree = ET.fromstring(image.read_text(encoding="utf-8"))
            self.assertEqual(tree.tag, "{http://www.w3.org/2000/svg}svg")
            width, height = float(tree.attrib["width"]), float(tree.attrib["height"])
            self.assertEqual(width, height)
            self.assertGreaterEqual(width, 48)
            for node in tree.iter():
                self.assertNotIn(node.tag.rsplit("}", 1)[-1], ("script", "foreignObject", "image", "use"))
                self.assertFalse(any(key.lower().startswith("on") or "href" in key for key in node.attrib))

    def test_privacy_and_support_are_explicit_and_have_local_documentation(self):
        for field in ("websiteURL", "supportURL", "privacyPolicyURL"):
            url = urlsplit(self.interface[field])
            self.assertEqual(url.scheme, "https")
            self.assertFalse(url.username or url.password or url.fragment)
        self.assertTrue((ROOT / "PRIVACY.md").is_file())
        self.assertTrue((ROOT / "SUPPORT.md").is_file())
        self.assertTrue((ROOT / "RUNTIME-SUPPORT.md").is_file())
        self.assertTrue(self.interface["privacyPolicyURL"].endswith("/plugins/manuscript-studio/PRIVACY.md"))
        self.assertTrue(self.interface["supportURL"].endswith("/cli1980/manuscript-studio/issues"))


if __name__ == "__main__":
    unittest.main()

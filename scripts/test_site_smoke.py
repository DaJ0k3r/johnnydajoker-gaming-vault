#!/usr/bin/env python3
"""Dependency-free source smoke tests. Not a substitute for browser/Lighthouse tests."""
import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "index.html").read_text(encoding="utf-8")
CATALOG = (ROOT / "data/catalog.js").read_text(encoding="utf-8")
GAMES = json.loads(CATALOG.split("window.VAULT_CATALOG =", 1)[1].strip().removesuffix(";"))

class Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.hrefs = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"): self.ids.add(attrs["id"])
        if tag == "a" and attrs.get("href"): self.hrefs.append(attrs["href"])

class VaultSmokeTests(unittest.TestCase):
    def test_catalogue_ids_and_urls_unique(self):
        self.assertEqual(len(GAMES), len({g["id"] for g in GAMES}))
        self.assertEqual(len(GAMES), len({g["url"] for g in GAMES}))
        self.assertTrue(all(g["type"] in ("GAME", "RESOURCE") for g in GAMES))

    def test_first_paint_count_matches_catalogue(self):
        for element_id in ("total", "visible"):
            self.assertIn(f'<b id="{element_id}">{len(GAMES)}</b>', HTML)

    def test_existing_features_and_storage_keys(self):
        parsed = Tags()
        parsed.feed(HTML)
        for element_id in ("grid", "total", "visible", "favorites", "recent", "add", "export", "modal", "vault-testlab", "mw-form", "daily-play"):
            self.assertIn(element_id, parsed.ids, element_id)
        for key in ("jdj-favs-v1", "jdj-recent-v1", "jdj-custom-v1", "jdj-testlab-v1", "jdj-most-wanted-v1", "jdj-intro-seen"):
            self.assertIn(key, HTML)

    def test_privacy_and_navigation(self):
        self.assertNotIn("googletagmanager.com", HTML)
        self.assertIn("static.cloudflareinsights.com", HTML)
        parsed = Tags()
        parsed.feed(HTML)
        for page in ("about.html", "privacy.html", "contact.html", "takedown.html"):
            self.assertIn("./" + page, parsed.hrefs)
            self.assertTrue((ROOT / page).exists(), page)

    def test_admin_and_intro(self):
        admin = (ROOT / "admin.html").read_text(encoding="utf-8")
        self.assertIn("noindex,nofollow", admin)
        self.assertIn("vault-admin=1", admin)
        self.assertIn("jdj-intro-skip-v1", HTML)
        self.assertIn(".vault-importer,#add,#export,#modal{display:none!important}", HTML)

if __name__ == "__main__":
    unittest.main()

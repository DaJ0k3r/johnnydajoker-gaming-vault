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
        self.assertIn(f'<b id="total">{len(GAMES)}</b>', HTML)
        self.assertIn(f'<b id="visible">{sum(g["status"] == "verified" for g in GAMES)}</b>', HTML)
        self.assertIn("<small>Shown by filters</small>", HTML)
        self.assertIn("<!-- BUILD:START FIRST CARDS -->", HTML)
        self.assertIn("<!-- BUILD:END FIRST CARDS -->", HTML)
        first_paint = HTML.split("<!-- BUILD:START FIRST CARDS -->", 1)[1].split("<!-- BUILD:END FIRST CARDS -->", 1)[0]
        expected = sorted((g for g in GAMES if g["status"] == "verified"), key=lambda g: g["title"].casefold())[:6]
        self.assertEqual(first_paint.count('<article class="card"'), len(expected))
        for game in expected:
            self.assertIn("<h3>" + __import__("html").escape(game["title"], quote=True) + "</h3>", first_paint)


    def test_social_counts_track_catalogue(self):
        # Avoid advertising stale totals when the catalogue grows.
        expected = str(len(GAMES))
        for prefix in ('<meta name="description" content="',
                       '<meta property="og:description" content="'):
            match = re.search(re.escape(prefix) + r'([^"]+)"', HTML)
            self.assertIsNotNone(match, prefix)
            self.assertIn(expected, match.group(1), f"Stale social count: {prefix}")

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

    def test_local_media_assets_and_social_metadata(self):
        # Catch missing root-level artwork before shipping a preview (including
        # the Underground 2 and Carbon banners that previously returned 404).
        assets = set(re.findall(r"[A-Za-z0-9_.-]+[.](?:png|jpe?g|webp|svg|ico|mp4)", HTML, re.I))
        self.assertTrue(assets, "Expected local artwork references")
        for filename in sorted(assets):
            self.assertTrue((ROOT / filename).is_file(), f"Missing local asset: {filename}")
        self.assertIn('rel="icon"', HTML)
        self.assertIn('property="og:image"', HTML)
        self.assertIn('name="twitter:image"', HTML)

    def test_admin_and_intro(self):
        admin = (ROOT / "admin.html").read_text(encoding="utf-8")
        self.assertIn("noindex,nofollow", admin)
        self.assertIn("vault-admin=1", admin)
        self.assertIn("jdj-intro-skip-v1", HTML)
        self.assertIn(".vault-importer,#add,#export,#modal{display:none!important}", HTML)

if __name__ == "__main__":
    unittest.main()

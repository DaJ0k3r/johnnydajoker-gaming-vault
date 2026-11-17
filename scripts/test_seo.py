#!/usr/bin/env python3
"""SEO integrity tests: only canonical, real, indexable MADHOUSE pages."""
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from build_seo import ROOT, INTRO, MIN_GAMES, slug, load, GENRES, BASE

class SEOTests(unittest.TestCase):
    def test_sitemap_has_only_real_public_canonical_pages(self):
        sitemap = ROOT / "sitemap.xml"
        root = ET.parse(sitemap).getroot()
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        locations = [node.text for node in root.findall("s:url/s:loc", ns)]
        self.assertEqual(len(locations), len(set(locations)))
        self.assertTrue(all(u.startswith(BASE + "/") for u in locations))
        self.assertNotIn(BASE + "/admin.html", locations)
        self.assertFalse(any("github.io" in u for u in locations))
        for loc in locations:
            relative = loc.removeprefix(BASE + "/")
            local = ROOT / relative
            if not relative or relative.endswith("/"):
                local = local / "index.html"
            self.assertTrue(local.is_file(), f"Sitemap points at missing page: {loc}")
            page = local.read_text(encoding="utf-8")
            self.assertIn(f'<link rel="canonical" href="{loc}">', page)

    def test_generated_genres_match_verified_game_catalogue(self):
        games = load()
        generated = json.loads((GENRES / ".generated-genres.json").read_text(encoding="utf-8"))
        expected = [name for name in INTRO if sum(
            g.get("category") == name and g.get("type") == "GAME"
            and g.get("status") == "verified" for g in games) >= MIN_GAMES]
        self.assertEqual(generated, expected)
        for name in generated:
            file = GENRES / slug(name) / "index.html"
            page = file.read_text(encoding="utf-8")
            checked = [g for g in games if g.get("type") == "GAME"
                       and g.get("status") == "verified" and g.get("category") == name]
            self.assertEqual(page.count('<article class="card">'), len(checked))
            self.assertIn("A successful destination check does not guarantee full gameplay", page)
            for game in checked:
                self.assertIn(game["url"], page)
            for game in games:
                if game.get("category") != name or game.get("status") == "verified":
                    continue
                if game["url"] not in {c["url"] for c in checked}:
                    self.assertNotIn(f'href="{game["url"]}"', page)

    def test_robots_references_sitemap_without_blocking_indexable_resources(self):
        robots = (ROOT / "robots.txt").read_text(encoding="utf-8")
        self.assertIn("User-agent: *", robots)
        self.assertIn(f"Sitemap: {BASE}/sitemap.xml", robots)
        self.assertNotIn("Disallow: /genres/", robots)
        admin = (ROOT / "admin.html").read_text(encoding="utf-8")
        self.assertIn("noindex,nofollow", admin)

    def test_homepage_has_crawlable_genre_links_and_web_site_metadata(self):
        homepage = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('"@type":"WebSite"', homepage)
        self.assertIn('"url":"https://johnnydajoker.com/"', homepage)
        generated = json.loads((GENRES / ".generated-genres.json").read_text(encoding="utf-8"))
        for name in generated:
            self.assertIn(f'href="./genres/{slug(name)}/"', homepage)
        for page in ("about.html", "privacy.html", "contact.html", "takedown.html"):
            text = (ROOT / page).read_text(encoding="utf-8")
            self.assertIn(f'<link rel="canonical" href="{BASE}/{page}">', text)

if __name__ == "__main__":
    unittest.main()

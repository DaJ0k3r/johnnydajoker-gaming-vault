#!/usr/bin/env python3
"""Offline tests for all-game discovery intake and batch review safety."""
import json
import sys
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
import vault_intake as intake

class IntakeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.catalog = self.root / "catalog.js"
        self.queue = self.root / "candidates.json"
        self.report = self.root / "report.json"
        self.catalog.write_text('window.VAULT_CATALOG = ' + json.dumps([
            {"id": 1, "title": "Existing Game", "url": "https://existing.example/play"}
        ]) + ';', encoding="utf-8")
        self.queue.write_text(json.dumps({"schemaVersion": 1, "entries": []}), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def run_intake(self, proposals):
        self.report.write_text(json.dumps({"proposals": proposals}), encoding="utf-8")
        with patch.object(intake, "SUMMARY", self.root / "summary.json"):
            return intake.stage(self.report, self.queue, self.catalog)

    def test_every_nonduplicate_is_staged_even_if_browser_inconclusive(self):
        leads = [
            {"id": "gh-100", "title": "New Browser Game",
             "url": "https://games.example.org/new",
             "sourceUrl": "https://github.com/dev/new",
             "http": "http-200",
             "browser": "rendered-with-canvas-or-frame (NOT gameplay-tested)"},
            {"id": "gh-101", "title": "Unknown Web Game",
             "url": "https://unknown.example.org/start",
             "sourceUrl": "https://github.com/dev/unknown",
             "http": "network-uncertain",
             "browser": "browser-inconclusive (TimeoutError)"},
            {"id": "gh-102", "title": "Existing Game",
             "url": "https://different.example.org/", "sourceUrl": "https://github.com/dev/duplicate"},
            {"id": "gh-103", "title": "Unsafe URL",
             "url": "http://127.0.0.1/", "sourceUrl": "https://github.com/dev/unsafe"}
        ]
        result = self.run_intake(leads)
        self.assertEqual(result["counts"]["autoQueued"], 2)
        self.assertEqual(result["counts"]["renderCandidate"], 1)
        self.assertEqual(result["counts"]["needsInspection"], 1)
        self.assertEqual(result["counts"]["duplicates"], 1)
        self.assertEqual(result["counts"]["unsafe"], 1)
        entries = json.loads(self.queue.read_text())["entries"]
        self.assertEqual({g["id"] for g in entries}, {"auto-gh-100", "auto-gh-101"})
        self.assertTrue(all(g["status"] == "unverified" for g in entries))
        self.assertTrue(all(g["gameplayTested"] is False for g in entries))
        self.assertTrue(all(g["readyForPublicCatalogue"] is False for g in entries))
        self.assertNotIn("verified", {g["status"] for g in entries})
        self.assertEqual([g["reviewPriority"] for g in entries],
                         ["launch-review", "needs-inspection"])
        again = self.run_intake(leads)
        self.assertEqual(again["counts"]["autoQueued"], 0)
        self.assertEqual(len(json.loads(self.queue.read_text())["entries"]), 2)

    def test_resource_tools_are_staged_for_research_not_as_games(self):
        proposals = [
            {"id": "gh-200", "title": "glitchless",
             "description": "Game observability for developers",
             "url": "https://glitchless.example.org",
             "sourceUrl": "https://github.com/dev/glitchless",
             "http": "http-200", "browser": "rendered-with-controls"},
            {"id": "gh-201", "title": "Real Arcade",
             "description": "An HTML5 browser arcade game",
             "url": "https://arcade.example.org",
             "sourceUrl": "https://github.com/dev/arcade",
             "http": "http-200", "browser": "rendered-with-canvas"}
        ]
        result = self.run_intake(proposals)
        self.assertEqual(result["counts"]["autoQueued"], 2)
        self.assertEqual(result["counts"]["resourceLeads"], 1)
        self.assertEqual(result["counts"]["renderCandidate"], 1)
        entries = json.loads(self.queue.read_text())["entries"]
        self.assertEqual([g["entryType"] for g in entries], ["RESOURCE", "GAME_CANDIDATE"])
        self.assertEqual(entries[0]["reviewPriority"], "resource-review")
        self.assertEqual(entries[0]["status"], "unverified")
        self.assertFalse(entries[0]["readyForPublicCatalogue"])

    def test_recent_developer_tools_and_portals_not_misidentified_as_games(self):
        samples = [
            ("gamealia-mcp", "MCP server to publish web games; SDK, browser autotest", "https://gamealia.app/docs/publishing-with-ai"),
            ("PhaserEditor2D-v3", "A web-based IDE for HTML5 game development", "https://phasereditor2d.com"),
            ("krtuworks-sdk-js", "Krtuworks SDK for JavaScript", "https://partner.krtuworks.com/docs"),
            ("github-leaderboard", "A visualisation of GitHub contributions", "https://example.org"),
            ("little-explorers", "A publicly available collection of printable games and worksheets", "https://example.org"),
            ("Playbox", "A growing collection of playful browser games", "https://example.org"),
            ("makefun-best-game-01-r2", "An AI game contest submission", "https://make.fun/bounty/best-game-01"),
        ]
        for title,desc,url in samples:
            with self.subTest(title=title):
                self.assertEqual(intake.classify_project({"title":title,"description":desc,"url":url}),"RESOURCE")
        for title,desc,url in [
            ("hippo-heist","3D stealth heist in your browser","https://games.example.com"),
            ("dmg-tetris","Playable Tetris game in browser","https://tetris.example.com"),
            ("VibeWars","Browser PvP arena","https://wars.example.com"),
        ]:
            with self.subTest(title=title):
                self.assertEqual(intake.classify_project({"title":title,"description":desc,"url":url}),"GAME_CANDIDATE")

    def test_same_source_repository_cannot_be_staged_twice(self):
        leads = [
            {"id": "gh-1", "title": "Game One", "url": "https://one.example/play",
             "sourceUrl": "https://github.com/owner/the-game"},
            {"id": "gh-2", "title": "Game Two", "url": "https://two.example/play",
             "sourceUrl": "https://github.com/owner/the-game"}
        ]
        self.assertEqual(self.run_intake(leads)["counts"]["autoQueued"], 1)

if __name__ == "__main__":
    unittest.main()

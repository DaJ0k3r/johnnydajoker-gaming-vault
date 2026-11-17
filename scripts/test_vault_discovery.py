#!/usr/bin/env python3
"""Offline tests for autonomous discovery approval safety."""
import base64
import json
import sys
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
import vault_discovery as vd

class DiscoveryTests(unittest.TestCase):
    def test_no_local_or_insecure_links(self):
        for value in ("http://example.com", "https://localhost/game",
                      "https://127.0.0.1", "https://169.254.169.254/latest",
                      "https://metadata.google.internal", "file:///tmp/secret",
                      "https://example.com:8080/game", "https://user:pass@example.com"):
            self.assertFalse(vd.safe_url(value), value)
        self.assertTrue(vd.safe_url("https://games.example.org/play"))
        self.assertEqual(vd.normalize("https://WWW.Example.org/play/"),
                         vd.normalize("https://example.org/play"))

    def test_approval_only_stages_checked_candidate_and_never_verifies(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            catalog = root / "catalog.js"
            queue = root / "candidates.json"
            body = root / "issue.md"
            catalog.write_text('window.VAULT_CATALOG = ' + json.dumps([
                {"id": 1, "title": "Existing Game", "url": "https://existing.example/"}
            ]) + ';', encoding="utf-8")
            queue.write_text(json.dumps({"schemaVersion": 1, "entries": []}), encoding="utf-8")
            proposed = [
                {"id": "gh-100", "title": "New Browser Game", "url": "https://new.example/play",
                 "sourceUrl": "https://github.com/artist/new-game", "http": "http-200",
                 "browser": "rendered-with-canvas-or-frame"},
                {"id": "gh-101", "title": "Unselected Game", "url": "https://other.example/",
                 "sourceUrl": "https://github.com/artist/other"}
            ]
            payload = base64.urlsafe_b64encode(json.dumps(proposed).encode()).decode()
            tick = chr(96)
            body.write_text('- [x] QUEUE FOR TEST LAB ' + tick + 'gh-100' + tick + ' — New Browser Game\n'
                            '- [ ] QUEUE FOR TEST LAB ' + tick + 'gh-101' + tick + ' — Unselected\n'
                            '<!-- ' + vd.MARKER + payload + ' -->', encoding="utf-8")
            with patch.object(vd, "CATALOG", catalog), patch.object(vd, "QUEUE", queue):
                vd.approve(str(body))
                vd.approve(str(body))
            entries = json.loads(queue.read_text(encoding="utf-8"))["entries"]
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["id"], "auto-gh-100")
            self.assertEqual(entries[0]["status"], "unverified")
            self.assertFalse(entries[0]["gameplayTested"])
            self.assertFalse(entries[0]["readyForPublicCatalogue"])
            self.assertEqual(entries[0]["playUrl"], "https://new.example/play")

    def test_duplicate_urls_and_titles_are_filtered_at_approval(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            catalog = root / "catalog.js"
            queue = root / "candidates.json"
            body = root / "issue.md"
            catalog.write_text('window.VAULT_CATALOG = ' + json.dumps([
                {"title": "Existing Game", "url": "https://existing.example/play"}
            ]) + ';', encoding="utf-8")
            queue.write_text(json.dumps({"schemaVersion": 1, "entries": []}), encoding="utf-8")
            proposals = [{"id": "gh-1", "title": "Random title", "url": "https://existing.example/play/",
                          "sourceUrl": "https://github.com/artist/repo"},
                         {"id": "gh-2", "title": "Existing Game", "url": "https://unique.example/play",
                          "sourceUrl": "https://github.com/artist/repo"}]
            blob = base64.urlsafe_b64encode(json.dumps(proposals).encode()).decode()
            tick = chr(96)
            body.write_text('- [x] QUEUE FOR TEST LAB ' + tick + 'gh-1' + tick + '\n'
                            '- [x] QUEUE FOR TEST LAB ' + tick + 'gh-2' + tick + '\n'
                            '<!-- ' + vd.MARKER + blob + ' -->', encoding="utf-8")
            with patch.object(vd, "CATALOG", catalog), patch.object(vd, "QUEUE", queue):
                vd.approve(str(body))
            self.assertEqual(json.loads(queue.read_text())["entries"], [])

if __name__ == "__main__":
    unittest.main()

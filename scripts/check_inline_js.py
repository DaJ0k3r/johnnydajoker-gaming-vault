#!/usr/bin/env python3
"""Extract executable inline JavaScript for node --check; no dependencies."""
from html.parser import HTMLParser
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]

class ScriptCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_script = False
        self.blocks = []
        self.current = []
    def handle_starttag(self, tag, attrs):
        if tag != "script":
            return
        attrs = dict(attrs)
        self.in_script = not attrs.get("src") and attrs.get("type", "text/javascript") in ("", "text/javascript", "module")
        self.current = []
    def handle_data(self, data):
        if self.in_script:
            self.current.append(data)
    def handle_endtag(self, tag):
        if tag == "script" and self.in_script:
            self.blocks.append("".join(self.current))
            self.in_script = False

for page in ("index.html", "admin.html", "about.html", "privacy.html", "contact.html", "takedown.html"):
    parser = ScriptCollector()
    parser.feed((root / page).read_text(encoding="utf-8"))
    for number, script in enumerate(parser.blocks, 1):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".mjs", encoding="utf-8") as temp:
            temp.write(script)
            temp.flush()
            subprocess.run(["node", "--check", temp.name], check=True)
        print(f"PASS {page} inline script #{number}")
print("All inline JavaScript syntax checks passed.")

#!/usr/bin/env python3
"""Non-destructive weekly Vault URL health check. HTTP success is not proof of playability."""
import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

html = Path("index.html").read_text(encoding="utf-8")
match = re.search(r"const SEED=(\[.*?\]);const safeParse", html, re.S)
if not match:
    raise SystemExit("Could not locate SEED dataset")
games = json.loads(match.group(1))
results = []
for game in games:
    url = game.get("url", "")
    status, note = "CHECK", ""
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; VaultHealthAudit/1.0)"})
        with urllib.request.urlopen(request, timeout=9) as response:
            status = str(response.status)
            note = response.geturl()
    except urllib.error.HTTPError as exc:
        status = str(exc.code)
        note = "HTTP error (may be bot protection)"
    except Exception as exc:
        status = "ERROR"
        note = str(exc)[:110]
    results.append((game.get("name", ""), url, status, note))
    time.sleep(0.15)

failures = [r for r in results if r[2] == "ERROR" or (r[2].isdigit() and int(r[2]) >= 400)]
stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
lines = [f"## Weekly Vault Link Audit — {stamp}", "", f"Checked **{len(results)}** entries. **{len(failures)}** need manual review.", "", "HTTP errors, timeouts, and bot protection can produce false positives. A successful response does not prove the game loads or is playable.", "", "| Game | HTTP / result | URL |", "|---|---|---|"]
for name, url, status, note in failures:
    safe_name = name.replace("|", "/").replace("\n", " ")
    lines.append(f"| {safe_name} | {status} | {url} |")
if not failures:
    lines.append("| No HTTP failures detected | — | — |")
lines.extend(["", "### What to do", "Open flagged games in a real browser before removing them. Verify the playable game, not just the landing page.", "", "_Automatically generated; no listings were removed._"])
body = "\n".join(lines)
print(body)
if not os.environ.get("GH_TOKEN"):
    Path("vault-audit-report.md").write_text(body, encoding="utf-8")
else:
    title = "Vault weekly link health audit"
    query = subprocess.run(["gh", "issue", "list", "--state", "open", "--search", f'{title} in:title', "--json", "number,title"], capture_output=True, text=True, check=True)
    existing = next((i for i in json.loads(query.stdout) if i["title"] == title), None)
    Path("/tmp/vault-audit.md").write_text(body, encoding="utf-8")
    if existing:
        subprocess.run(["gh", "issue", "edit", str(existing["number"]), "--body-file", "/tmp/vault-audit.md"], check=True)
    else:
        subprocess.run(["gh", "issue", "create", "--title", title, "--body-file", "/tmp/vault-audit.md"], check=True)

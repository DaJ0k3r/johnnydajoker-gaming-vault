#!/usr/bin/env python3
"""Weekly MADHOUSE link-health audit. HTTP health never certifies game playability."""
import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

CATALOG = Path("data/catalog.js")
raw = CATALOG.read_text(encoding="utf-8")
match = re.search(r"window\.VAULT_CATALOG\s*=\s*(\[.*\])\s*;\s*$", raw, re.S)
if not match:
    raise SystemExit("Catalogue not found or not valid JSON inside data/catalog.js")
games = json.loads(match.group(1))
if not isinstance(games, list):
    raise SystemExit("Catalogue must contain an array")

def probe(url):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        return "INVALID", "Not a valid HTTPS URL", ""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; MadhouseVaultLinkAudit/2.0)"}
    for method in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(url, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=9) as response:
                code = response.status
                final = response.geturl()
                return ("OK" if 200 <= code < 400 else "REVIEW"), f"HTTP {code} via {method}", final
        except urllib.error.HTTPError as exc:
            if method == "HEAD" and exc.code in (403, 405, 501):
                continue
            code = exc.code
            return ("REVIEW" if code in (401, 403, 429) or code >= 500 else "BROKEN_CANDIDATE"), f"HTTP {code} (may be access restrictions or bot protection)", ""
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if method == "HEAD":
                continue
            return "REVIEW", f"Connection error: {str(exc)[:90]}", ""
    return "REVIEW", "Unable to check", ""

results = []
for entry in games:
    url = entry.get("url", "")
    health, detail, final = probe(url)
    results.append({
        "id": entry.get("id"), "title": entry.get("title", "(untitled)"),
        "url": url, "type": entry.get("type", "GAME"),
        "catalogueStatus": entry.get("status", "unverified"),
        "health": health, "detail": detail, "finalUrl": final,
        "checkedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })
    time.sleep(0.10)

counts = Counter(r["health"] for r in results)
flagged = [r for r in results if r["health"] != "OK"]
stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
lines = [
    f"## MADHOUSE Weekly Link Audit — {stamp}", "",
    f"**{len(results)}** catalogue entries checked · **{counts['OK']}** HTTP reachable · **{len(flagged)}** require review.",
    "",
    "**Important:** HTTP reachability does NOT prove the game launches, accepts input, or works on mobile. "
    "401/403/429 responses may be login requirements or anti-bot protection. "
    "Even a 404 or timeout should be manually reproduced before changing catalogue status.",
    "",
    "| ID | Listing | HTTP assessment | Detail | URL |",
    "|---|---|---|---|---|",
]
def safe(value):
    return str(value).replace("|", "/").replace("\n", " ").replace("\r", " ")[:170]
for r in flagged:
    lines.append(f"| {safe(r['id'])} | {safe(r['title'])} | {r['health']} | {safe(r['detail'])} | {safe(r['url'])} |")
if not flagged:
    lines.append("| — | No flagged links | — | — | — |")
lines += [
    "", "### Manual launch verification",
    "For flagged URLs, open in a real browser, confirm the correct game or resource loads, "
    "test controls and mobile compatibility where applicable, and document results before editing data/catalog.js.",
    "",
    "### Safety",
    "This automated job does not edit the catalogue, change verification badges, or remove games.",
    "The detailed machine-readable results are available as a workflow artifact.",
]
body = "\n".join(lines)
Path("vault-audit-report.md").write_text(body + "\n", encoding="utf-8")
Path("vault-audit-results.json").write_text(json.dumps({
    "checkedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "summary": dict(counts), "results": results
}, indent=2) + "\n", encoding="utf-8")
print(body)

if os.environ.get("GH_TOKEN"):
    title = "Vault weekly link health audit"
    query = subprocess.run(
        ["gh", "issue", "list", "--state", "open", "--search", f"{title} in:title",
         "--json", "number,title", "--limit", "100"],
        capture_output=True, text=True, check=True,
    )
    existing = next((i for i in json.loads(query.stdout) if i["title"] == title), None)
    if existing:
        subprocess.run(["gh", "issue", "edit", str(existing["number"]),
                        "--body-file", "vault-audit-report.md"], check=True)
    else:
        subprocess.run(["gh", "issue", "create", "--title", title,
                        "--body-file", "vault-audit-report.md"], check=True)

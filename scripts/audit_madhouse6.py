#!/usr/bin/env python3
"""Read-only MADHOUSE 6 verification and first-load asset audit.

Never changes game statuses: HTTP success and a working landing page do not
prove that a game is playable. Human gameplay tests remain authoritative.
"""
import json
import argparse
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
raw = (ROOT / "data/catalog.js").read_text(encoding="utf-8")
games = json.loads(raw.split("window.VAULT_CATALOG =", 1)[1].strip().removesuffix(";"))
html = (ROOT / "index.html").read_text(encoding="utf-8")
flags = []
for game in games:
    status = game.get("status", "")
    notes = " ".join(str(game.get(k) or "") for k in ("notes", "description"))
    if status == "verified" and re.search(
        r"not independently verified|not (?:yet )?tested|unverified gameplay|"
        r"only (?:the )?(?:destination|landing page|link) (?:was )?(?:tested|verified)",
        notes, re.I
    ):
        flags.append({"id": game.get("id"), "title": game.get("title"),
                      "reason": "Verified badge may imply gameplay testing; review evidence",
                      "notes": notes[:240]})
    if status == "verified" and not game.get("lastChecked"):
        flags.append({"id": game.get("id"), "title": game.get("title"),
                      "reason": "Verified entry missing lastChecked"})
assets = []
for path in ROOT.iterdir():
    if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".mp4"} and path.is_file():
        assets.append({"name": path.name, "bytes": path.stat().st_size})
assets.sort(key=lambda x: x["bytes"], reverse=True)
report = {
    "catalogueCount": len(games),
    "statusCounts": dict(Counter(g.get("status", "missing") for g in games)),
    "verificationReview": flags,
    "largestRootAssets": assets[:20],
    "performanceReview": [
        "Review large image/video assets for responsive variants and lazy loading",
        "Measure mobile LCP, CLS and INP in a real browser before claiming improvement",
        "Check that cinematic intro assets are not fetched for returning visitors",
    ],
    "safety": "Read-only report. No catalogue badges, live files or deployment changed."
}
parser = argparse.ArgumentParser(description="Read-only catalogue verification audit")
parser.add_argument("--output", default="madhouse-6-audit.json", help="Report path")
args = parser.parse_args()
out = Path(args.output)
out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"Catalogue: {len(games)} | review flags: {len(flags)} | largest assets: {len(assets[:20])}")
for flag in flags[:30]:
    print(f"REVIEW {flag['id']}: {flag['title']} — {flag['reason']}")
print(f"Report: {out}")

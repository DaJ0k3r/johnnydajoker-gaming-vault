#!/usr/bin/env python3
"""Regenerate first-paint catalogue counts and six static cards. Run after editing data/catalog.js."""
import html
import json
import re
from pathlib import Path

root = Path(__file__).resolve().parents[1]
catalogue = (root / "data/catalog.js").read_text(encoding="utf-8")
games = json.loads(catalogue.split("window.VAULT_CATALOG =", 1)[1].strip().removesuffix(";"))
page = root / "index.html"
source = page.read_text(encoding="utf-8")
verified = sorted((g for g in games if g["status"] == "verified"), key=lambda g: g["title"].casefold())
def e(value):
    return html.escape(str(value or ""), quote=True)
def card(g):
    kind = g["type"]
    css_kind = "resource" if kind == "RESOURCE" else "game"
    return (f'<article class="card" data-genre="{e(g["category"])}">'
            f'<div class="top"><span class="tag">{e(g["category"])}</span>'
            f'<span class="vault-status verified" title="Catalogue status: verified">✓ Verified</span></div>'
            f'<h3>{e(g["title"])}</h3><p>{e(g.get("description") or g.get("notes") or "")}</p>'
            f'<div class="meta"><span class="premium-kind {css_kind}">{kind}</span></div>'
            f'<a href="{e(g["url"])}" target="_blank" rel="noopener noreferrer">'
            f'Open {"resource" if kind == "RESOURCE" else "game"} ↗</a></article>')
first = "".join(card(g) for g in verified[:6])
source, n = re.subn(r'<!-- BUILD:START FIRST CARDS -->.*?<!-- BUILD:END FIRST CARDS -->',
                    '<!-- BUILD:START FIRST CARDS -->' + first + '<!-- BUILD:END FIRST CARDS -->',
                    source, count=1, flags=re.S)
if n != 1:
    raise SystemExit("Missing static-card markers; refusing to rewrite HTML")
for element_id, value in (("total", len(games)), ("visible", len(verified))):
    source, n = re.subn(r'(<b id="' + element_id + r'">)\d+(</b>)',
                        lambda m: m[1] + str(value) + m[2], source, count=1)
    if n != 1:
        raise SystemExit(f"Missing counter {element_id}")
page.write_text(source, encoding="utf-8")
print(f"Updated first paint: {len(games)} total, {len(verified)} verified, {min(6,len(verified))} cards")

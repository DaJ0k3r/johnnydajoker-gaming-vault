#!/usr/bin/env python3
"""Build trustworthy, crawlable MADHOUSE genre pages and a canonical sitemap.

Only manually destination-checked GAME entries qualify. Does not claim complete
gameplay verification, embed third-party code, or publish research candidates.
"""
from collections import defaultdict
from html import escape
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://johnnydajoker.com"
CATALOG = ROOT / "data" / "catalog.js"
GENRES = ROOT / "genres"
INTRO = {
    "Racing": ("Racing games in your browser",
               "Find speed, arcade handling and nostalgic racing projects. Links open the original creators' websites; availability and controls can vary."),
    "Strategy": ("Strategy games in your browser",
                 "Build, plan and outthink the competition with browser-based strategy games and community projects. Some classics need additional game files."),
    "Sandbox": ("Sandbox games in your browser",
                "Explore worlds, build things and experiment at your own pace. Check each original game's controls and requirements before you start."),
    "Shooter": ("Browser shooter games",
                "Fast matches, tactical fights and arcade shooters gathered in one place. Check keyboard, mouse and multiplayer requirements on the original game."),
    "RPG": ("Browser RPG games",
            "Discover role-playing adventures and retro projects you can launch from a browser. Some community versions may require original game files."),
    "Arcade": ("Free browser arcade games",
               "Quick-fire fun and classic arcade-inspired games without digging through random broken links. Each link opens its original destination."),
    "Party": ("Browser party and multiplayer games",
              "Find games to share with friends, from casual challenges to multiplayer mayhem. Some games may need a free account or a room code."),
    "Puzzle": ("Puzzle games in your browser",
               "Logic, wordplay and brain-teasing favourites for shorter sessions or a proper challenge. Launch each game on its original website."),
}
MIN_GAMES = 4
CSS = """*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 75% 0,#163b20,#090e0a 60%);color:#e9f6eb;font:16px/1.6 system-ui,Arial,sans-serif}
main{max-width:1140px;margin:auto;padding:22px clamp(16px,4vw,50px) 80px}
a{color:#adff8c}a:focus-visible{outline:3px solid white;outline-offset:4px}
header{border-bottom:1px solid #507853;background:#0b170d;padding:14px clamp(16px,4vw,50px)}header nav{max-width:1100px;margin:auto;display:flex;align-items:center;flex-wrap:wrap;gap:18px}header strong{color:#93ff74;letter-spacing:2px}
h1{font-size:clamp(2rem,6vw,4rem);line-height:1.1;color:#a6ff8a;margin-bottom:12px}h2{margin-top:50px;color:#b8ff9a}
.lead{font-size:1.1rem;max-width:75ch}.notice{color:#c9d8c7;background:#122418;border-left:3px solid #84df71;padding:12px 16px;border-radius:0 8px 8px 0}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:16px;margin-top:26px}
.card{background:#122119;border:1px solid #365b3c;border-radius:15px;padding:20px;display:flex;flex-direction:column;gap:8px;min-height:225px}
.card h2{font-size:1.25rem;color:#eeffee;margin:0}.card p{margin:0;flex:1;color:#c7d4ca}
.label{font-size:.78rem;color:#a6ff8a;font-weight:700;letter-spacing:.04em}.card a{display:inline-block;margin-top:8px;text-decoration:none;background:#93fd74;color:#10200e;padding:9px 12px;border-radius:8px;font-weight:800;width:max-content}
footer{margin-top:55px;padding-top:24px;border-top:1px solid #436448;display:flex;flex-wrap:wrap;gap:14px}small{color:#c7dbc8}"""

def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")

def load():
    data = CATALOG.read_text(encoding="utf-8").split("window.VAULT_CATALOG =", 1)[1].strip().removesuffix(";")
    return json.loads(data)

def page_for(name, games, genres):
    slugged = slug(name)
    title, intro = INTRO[name]
    url = f"{BASE}/genres/{slugged}/"
    cards = []
    for game in sorted(games, key=lambda x: x["title"].casefold()):
        tags = set(game.get("tags", []))
        requirements = []
        if "game-files-required" in tags:
            requirements.append("Game files required")
        if "free-account-required" in tags:
            requirements.append("Free account required")
        if not requirements:
            requirements.append("Check requirements on original site")
        label = " · ".join(requirements)
        note = game.get("description") or "Community browser project"
        link = game["url"]
        original = ("madhouse-original" in tags and link.startswith("games/")
                    and (ROOT / link / "index.html").is_file())
        if original:
            link = BASE + "/" + link.rstrip("/") + "/"
        elif not link.startswith("https://"):
            continue
        badge = "MADHOUSE ORIGINAL · PLAY HERE" if original else "DESTINATION CHECKED · GAME"
        action = "Play in MADHOUSE ↗" if original else "Visit game ↗"
        cards.append('<article class="card">'
                     f'<span class="label">{badge}</span>'
                     f'<h2>{escape(game["title"])}</h2>'
                     f'<p>{escape(note)}</p><small>{escape(label)}</small>'
                     f'<a href="{escape(link, quote=True)}" target="_blank" rel="noopener noreferrer">{action}</a>'
                     '</article>')
    links = " · ".join(f'<a href="../{slug(other)}/">{escape(other)}</a>' for other in genres if other != name)
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#090e0a">
<title>{escape(title)} | JohnnyDaJoker MADHOUSE</title>
<meta name="description" content="{escape(intro, quote=True)}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website"><meta property="og:title" content="{escape(title, quote=True)}">
<meta property="og:description" content="{escape(intro, quote=True)}"><meta property="og:url" content="{url}">
<link rel="icon" type="image/x-icon" href="../../straw-hat-favicon.ico">
<style>{CSS}</style></head>
<body><header><nav><strong>JOHNNY DA JOKER · MADHOUSE</strong><a href="../../">The Vault</a><a href="../../about.html">About</a><a href="../../contact.html">Suggest a game</a></nav></header>
<main><p class="label">THE BROWSER GAMING VAULT · {escape(name.upper())}</p>
<h1>{escape(title)}</h1><p class="lead">{escape(intro)}</p>
<p class="notice"><strong>{len(cards)} previously checked destinations.</strong> Most games link to independent websites; MADHOUSE Originals are hosted here. A successful destination check does not guarantee full gameplay, embedding, or continued availability. Check accounts, file requirements and controls before playing.</p>
<div class="grid">{''.join(cards)}</div>
<h2>Explore more game categories</h2><p>{links}</p>
<footer><a href="../../">Return to MADHOUSE</a><a href="../../privacy.html">Privacy</a><a href="../../takedown.html">Rights &amp; takedown</a><a href="../../contact.html">Contact</a></footer></main></body></html>
"""
    return page

def build():
    g = load()
    groups = defaultdict(list)
    for item in g:
        if (item.get("type") == "GAME" and item.get("status") == "verified"
                and item.get("category") in INTRO):
            groups[item["category"]].append(item)
    available = [x for x in INTRO if len(groups[x]) >= MIN_GAMES]
    GENRES.mkdir(exist_ok=True)
    # Only delete category folders previously generated by this script.
    old = GENRES / ".generated-genres.json"
    if old.exists():
        for name in json.loads(old.read_text(encoding="utf-8")):
            if name not in available:
                stale = GENRES / slug(name) / "index.html"
                if stale.exists():
                    stale.unlink()
    for name in available:
        out = GENRES / slug(name)
        out.mkdir(parents=True, exist_ok=True)
        (out / "index.html").write_text(page_for(name, groups[name], available), encoding="utf-8")
    old.write_text(json.dumps(available, indent=2) + "\n", encoding="utf-8")
    originals = sorted({BASE + "/" + game["url"].rstrip("/") + "/"
                        for game in g
                        if game.get("type") == "GAME" and game.get("status") == "verified"
                        and "madhouse-original" in game.get("tags", [])
                        and str(game.get("url", "")).startswith("games/")
                        and (ROOT / game["url"] / "index.html").is_file()})
    urls = [BASE + "/", *(BASE + "/" + x for x in
                           ("about.html", "privacy.html", "contact.html", "takedown.html")),
            *(BASE + "/genres/" + slug(name) + "/" for name in available),
            *originals]
    ET.register_namespace("", "http://www.sitemaps.org/schemas/sitemap/0.9")
    xml_root = ET.Element("{http://www.sitemaps.org/schemas/sitemap/0.9}urlset")
    for url in urls:
        el = ET.SubElement(xml_root, "{http://www.sitemaps.org/schemas/sitemap/0.9}url")
        ET.SubElement(el, "{http://www.sitemaps.org/schemas/sitemap/0.9}loc").text = url
    ET.indent(xml_root, space="  ")
    ET.ElementTree(xml_root).write(ROOT / "sitemap.xml", encoding="utf-8", xml_declaration=True)
    (ROOT / "robots.txt").write_text("User-agent: *\nAllow: /\n\nSitemap: " + BASE + "/sitemap.xml\n", encoding="utf-8")
    print(f"Built {len(available)} category pages and a {len(urls)}-URL canonical sitemap")

if __name__ == "__main__":
    build()

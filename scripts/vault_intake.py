#!/usr/bin/env python3
"""Automatically stage EVERY safe, nonduplicate discovery candidate.

This modifies the review queue only. Never marks gameplay verified and never
writes data/catalog.js or publishes a third-party game.
"""
import datetime as dt
import json
import os
from pathlib import Path
from urllib.parse import urlsplit
import vault_discovery as vd

SUMMARY = vd.ROOT / "reports" / "vault-intake-summary.json"

def classify_project(project):
    """Conservative research triage: RESOURCE is not a playable game claim.

    Resources are still queued for editorial discovery, but kept out of the
    Test Lab until an individual direct-play game URL is identified.
    """
    name = str(project.get("title", "")).lower().replace("_", "-")
    description = str(project.get("description", "")).lower()
    launch_url = str(project.get("url", "")).lower()
    resource_titles = ("-plugin", "plugin-", "-compiler", "-framework",
                       "games-hub", "game-hub", "gamedev", "100-games",
                       "web-playables", "os.js", "-sdk", "sdk-", "game-skill",
                       "-mcp", "phasereditor", "github-leaderboard")
    resource_descriptions = ("game observability", "developer sdk", "game developer platform",
                             "game development tools", "game development news",
                             "software development kit", "emulator and", "x86 emulator",
                             "compiles code", "framework for games", "library for game developers",
                             "game publishing", "game gallery", "browser arcade with",
                             "games in one place", "open recipes", "printable games and worksheets",
                             "online games and printable worksheets", "a collection of",
                             "growing collection of", "browser micro-tools",
                             "a web-based ide", "self-hosted arcade for", "portfolio: games",
                             "portafolio: juegos", "browser game directories",
                             "all-in-one game portal")
    resource_paths = ("/developers", "/docs/", "compiler.", "/bounty/")
    if (any(token in name for token in resource_titles)
        or any(token in description for token in resource_descriptions)
        or any(token in launch_url for token in resource_paths)):
        return "RESOURCE"
    return "GAME_CANDIDATE"

def stage(report_path=None, queue_path=None, catalog_path=None):
    report_file = Path(report_path or vd.REPORT)
    queue_file = Path(queue_path or vd.QUEUE)
    catalog_file = Path(catalog_path or vd.CATALOG)
    report = json.loads(report_file.read_text(encoding="utf-8"))
    store = json.loads(queue_file.read_text(encoding="utf-8"))
    catalog = json.loads(catalog_file.read_text(encoding="utf-8").split("window.VAULT_CATALOG =", 1)[1].strip().removesuffix(";"))
    entries = store["entries"]
    existing_ids = {str(g.get("id")) for g in entries}
    known_urls = {vd.normalize(u) for g in entries + catalog
                  for u in (g.get("url"), g.get("playUrl"), g.get("sourceUrl"))
                  if vd.normalize(u)}
    known_titles = {vd.normalized_title(g.get("title")) for g in entries + catalog}
    counts = {"autoQueued": 0, "renderCandidate": 0, "needsInspection": 0, "resourceLeads": 0,
              "duplicates": 0, "unsafe": 0, "proposals": len(report.get("proposals", []))}
    added = []
    for p in report.get("proposals", []):
        title = vd.short(p.get("title"), 100)
        url = p.get("url", "")
        source = p.get("sourceUrl", "")
        identifier = p.get("id", "")
        if not (isinstance(identifier, str) and identifier.startswith("gh-") and
                identifier[3:].isdigit() and title and vd.safe_url(url) and
                vd.safe_url(source) and urlsplit(source).hostname == "github.com"):
            counts["unsafe"] += 1
            continue
        new_id = "auto-" + identifier
        if (new_id in existing_ids or vd.normalize(url) in known_urls or
            vd.normalize(source) in known_urls or vd.normalized_title(title) in known_titles):
            counts["duplicates"] += 1
            continue
        http_result = str(p.get("http", "not-checked"))
        browser_result = str(p.get("browser", "not-tested"))
        possible_launch = (http_result == "http-200" and browser_result.startswith("rendered-"))
        entry_kind = classify_project(p)
        priority = ("resource-review" if entry_kind == "RESOURCE"
                    else "launch-review" if possible_launch else "needs-inspection")
        entry = {
            "id": new_id,
            "title": title,
            "category": "Browser game candidate" if entry_kind == "GAME_CANDIDATE" else "Development resource",
            "entryType": entry_kind,
            "sourceDescription": vd.short(p.get("description", ""), 180),
            "sourceUrl": source,
            "playUrl": url,
            "sourceRequirements": ("Automatically discovered public GitHub project. "
                "Direct game launch, controls, accounts, files, embedding rights and licensing not confirmed."),
            "verificationChecklist": ("Confirm this is a GAME rather than a directory/tool; "
                "start actual gameplay; test keyboard/touch, device compatibility, "
                "redirects, files/accounts, safe content and permission to embed or link."),
            "status": "unverified", "gameplayTested": False,
            "readyForPublicCatalogue": False,
            "reviewPriority": priority,
            "discoverySource": "github-topic-search",
            "automationEvidence": {
                "http": http_result[:35],
                "browser": browser_result[:90],
                "sourceStars": int(p.get("stars", 0))
            }
        }
        entries.append(entry)
        added.append(entry)
        counts["autoQueued"] += 1
        counts["resourceLeads" if entry_kind == "RESOURCE" else
               "renderCandidate" if possible_launch else "needsInspection"] += 1
        existing_ids.add(new_id)
        known_titles.add(vd.normalized_title(title))
        known_urls.add(vd.normalize(url))
        known_urls.add(vd.normalize(source))
    if added:
        queue_file.write_text(json.dumps(store, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    info = {"counts": counts, "added": [{"id": g["id"], "title": g["title"],
                                         "playUrl": g["playUrl"], "reviewPriority": g["reviewPriority"]}
                                        for g in added],
            "disclaimer": "Staging is not publication. No game was gameplay-verified."}
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(info, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("MADHOUSE all-game intake:", counts)
    return info

if __name__ == "__main__":
    stage()

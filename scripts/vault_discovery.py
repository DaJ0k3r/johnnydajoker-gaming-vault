#!/usr/bin/env python3
"""MADHOUSE discovery: propose only; never publish or mark a game verified.

Usage:
  python scripts/vault_discovery.py scan
  python scripts/vault_discovery.py render
  python scripts/vault_discovery.py approve --body-file issue.txt
"""
import argparse
import base64
import datetime as dt
import html
import ipaddress
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo
import re
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "vault-discovery.json"
ISSUE_MD = ROOT / "reports" / "vault-approvals.md"
QUEUE = ROOT / "data" / "discovery" / "candidates.json"
CATALOG = ROOT / "data" / "catalog.js"
MARKER = "VAULT_DISCOVERY_PAYLOAD:"
MAX_PROPOSALS = 6
MAX_AUDIT = 12

def catalogue():
    text = CATALOG.read_text(encoding="utf-8")
    return json.loads(text.split("window.VAULT_CATALOG =", 1)[1].strip().removesuffix(";"))

def queue():
    return json.loads(QUEUE.read_text(encoding="utf-8"))

def safe_url(url):
    """Allow only public-looking HTTPS web hosts; never fetch local/metadata addresses."""
    try:
        u = urlsplit((url or "").strip())
        host = (u.hostname or "").lower().strip(".")
        if u.scheme != "https" or not host or u.username or u.password or u.port not in (None, 443):
            return False
        if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
            return False
        if not re.fullmatch(r"[a-z0-9.-]+", host) or "." not in host:
            return False
        try:
            ipaddress.ip_address(host)
            return False
        except ValueError:
            pass
        return True
    except (ValueError, TypeError):
        return False

def normalize(url):
    if not safe_url(url):
        return ""
    u = urlsplit(url.strip())
    return (u.hostname or "").lower().removeprefix("www.") + u.path.rstrip("/").lower()

def normalized_title(value):
    return re.sub(r"[^a-z0-9]+", "", (value or "").casefold())

def short(value, limit=100):
    return re.sub(r"[\r\n\[\]\x00-\x1f|<>*]", " ", str(value or "")).strip()[:limit]

def request_json(url):
    headers = {"Accept": "application/vnd.github+json",
               "User-Agent": "MadhouseVaultDiscovery/1.0"}
    if os.environ.get("GH_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GH_TOKEN"]
    request = Request(url, headers=headers)
    with urlopen(request, timeout=12) as response:
        return json.load(response)

def prior_proposal_ids():
    """No repeat submissions for the recent weekly approval issues."""
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", repo):
        return set()
    ids = set()
    try:
        items = request_json(f"https://api.github.com/repos/{repo}/issues?state=all&per_page=100")
        for item in items:
            if not str(item.get("title", "")).startswith("MADHOUSE Discovery approvals"):
                continue
            payload = extract_payload(item.get("body") or "")
            ids.update(p["id"] for p in payload)
    except (HTTPError, URLError, ValueError, KeyError) as exc:
        print(f"Prior issue lookup unavailable ({exc}); existing queue and catalogue still deduplicated")
    return ids

def discover_repositories(known_urls, known_titles, prior_ids):
    """GitHub topic search: discovery evidence, never proof of gameplay or distribution rights."""
    proposed = []
    seen = set()
    for query in ("topic:browser-game stars:>10 archived:false",
                  "topic:html5-game stars:>10 archived:false"):
        args = urlencode({"q": query, "sort": "updated", "order": "desc", "per_page": 35})
        try:
            found = request_json("https://api.github.com/search/repositories?" + args).get("items", [])
        except (HTTPError, URLError, ValueError) as exc:
            print(f"GitHub discovery search unavailable ({exc})")
            continue
        for item in found:
            repo_id = "gh-" + str(item.get("id", ""))
            title = short(item.get("name", ""), 75)
            homepage = str(item.get("homepage") or "").strip().rstrip("/")
            repo_url = str(item.get("html_url") or "")
            name = title.lower()
            if not repo_id[3:].isdigit() or not safe_url(homepage) or not safe_url(repo_url):
                continue
            if any(w in name for w in ("awesome", "boilerplate", "template", "framework", "engine", "game-list", "tutorial")):
                continue
            if urlsplit(homepage).hostname in ("github.com", "www.github.com"):
                continue
            if (repo_id in prior_ids or repo_id in seen or normalize(homepage) in known_urls
                    or normalized_title(title) in known_titles):
                continue
            proposed.append({"id": repo_id, "title": title, "url": homepage,
                             "sourceUrl": repo_url, "description": short(item.get("description", ""), 160),
                             "stars": int(item.get("stargazers_count", 0)),
                             "category": "Browser game candidate",
                             "requirements": "Check actual playable launch, controls, mobile support, file requirements and rights",
                             "http": "not-checked", "browser": "not-tested"})
            seen.add(repo_id)
            if len(proposed) >= MAX_PROPOSALS:
                return proposed
    return proposed

def inspect_http(url):
    """HEAD/GET availability only; hostile bots/403s remain uncertain, not broken."""
    if not safe_url(url):
        return "unsafe-url"
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0 MADHOUSE-Vault-Audit"},
                      method="HEAD")
        with urlopen(req, timeout=9) as response:
            code = response.status
            target = response.url
        if not safe_url(target):
            return "redirect-review"
        return "http-" + str(code)
    except HTTPError as exc:
        if exc.code in (405, 501):
            try:
                req = Request(url, headers={"User-Agent": "Mozilla/5.0 MADHOUSE-Vault-Audit"},
                              method="GET")
                with urlopen(req, timeout=9) as response:
                    return "http-" + str(response.status) if safe_url(response.url) else "redirect-review"
            except (HTTPError, URLError, TimeoutError) as inner:
                return "http-" + str(inner.code) if isinstance(inner, HTTPError) else "network-uncertain"
        return "http-" + str(exc.code)
    except (URLError, TimeoutError, OSError, ValueError):
        return "network-uncertain"

def run_scan():
    games = catalogue()
    queued = queue()["entries"]
    known_urls = {normalize(g.get("url")) for g in games + queued
                  if normalize(g.get("url"))}
    known_urls.update(normalize(q.get("playUrl")) for q in queued if normalize(q.get("playUrl")))
    known_titles = {normalized_title(g.get("title")) for g in games + queued}
    prior_ids = prior_proposal_ids()
    proposals = discover_repositories(known_urls, known_titles, prior_ids)
    for item in proposals:
        item["http"] = inspect_http(item["url"])
    # Rotate audits so this remains free/cheap and does not hammer 146 sites every run.
    week = dt.datetime.now(ZoneInfo('Australia/Brisbane')).isocalendar().week
    start = (week * MAX_AUDIT) % max(1, len(games))
    chosen = (games[start:] + games[:start])[:MAX_AUDIT]
    audit = [{"title": g.get("title"), "url": g.get("url"), "catalogueStatus": g.get("status"),
              "http": inspect_http(g.get("url"))} for g in chosen]
    result = {"generated": dt.datetime.now(dt.timezone.utc).isoformat(), "proposals": proposals,
              "audit": audit, "catalogueCount": len(games),
              "queueCount": len(queued), "note": "HTTP status is not evidence of playable gameplay."}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Discovered {len(proposals)} new GitHub candidates; audited {len(audit)} existing URLs.")
    render()

def extract_payload(body):
    match = re.search(r"<!--\s*" + MARKER + r"([A-Za-z0-9_=-]+)\s*-->", body)
    if not match:
        return []
    try:
        data = json.loads(base64.urlsafe_b64decode(match.group(1)).decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return []
    if not isinstance(data, list):
        return []
    return [x for x in data if isinstance(x, dict)]

def render():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    p = report["proposals"]
    audit = report["audit"]
    now = dt.datetime.now(ZoneInfo('Australia/Brisbane')).isocalendar()
    lines = [f"# MADHOUSE Discovery approvals — {now.year}-W{now.week:02d}", "",
             "**Your job:** tick the checkbox beside anything you want researched in the Test Lab. "
             "That queues an **UNVERIFIED candidate** into a protected pull request; it does **not** "
             "publish the game or claim gameplay-tested status.", "",
             "## New game leads (automatic suggestions)", ""]
    if not p:
        lines.append("No fresh, non-duplicate leads found in this scan.")
    for item in p:
        title = short(item["title"], 75)
        desc = short(item.get("description"), 120)
        evidence = f"HTTP: {item.get('http', 'not-checked')}; browser: {item.get('browser', 'not-tested')}"
        lines += [f"- [ ] QUEUE FOR TEST LAB `{item['id']}` — **{title}**",
                  f"  - [Candidate launch]({item['url']}) · [GitHub source]({item['sourceUrl']}) · {evidence}",
                  f"  - {desc or 'No description supplied'}. Human gameplay, safety and rights review needed."]
    lines += ["", "## Existing game-link spot check", "",
              "These checks only tell us whether automated requests succeeded; they cannot prove games launch.", ""]
    for g in audit:
        lines.append(f"- **{short(g['title'], 60)}** — {g['http']} ({g['catalogueStatus']})")
    lines += ["", "**After ticking:** GitHub prepares a review PR with newly approved entries in "
              "`data/discovery/candidates.json`; they remain unverified until manually tested.",
              "Issues edits by the repository owner trigger this step. No automatic public publishing.",
              "", "<!-- " + MARKER +
              base64.urlsafe_b64encode(json.dumps(p, separators=(",", ":")).encode()).decode() + " -->", ""]
    ISSUE_MD.parent.mkdir(parents=True, exist_ok=True)
    ISSUE_MD.write_text("\n".join(lines), encoding="utf-8")
    print("Checklist written:", ISSUE_MD)

def approve(body_file):
    body = Path(body_file).read_text(encoding="utf-8")
    payload = extract_payload(body)
    approvals = set(re.findall(r"(?im)^\s*-\s*\[[xX]\]\s+QUEUE FOR TEST LAB\s+\x60(gh-\d+)\x60", body))
    if not approvals or not payload:
        print("No valid approved candidates.")
        return
    store = queue()
    existing_ids = {str(g.get("id")) for g in store["entries"]}
    known_urls = {normalize(g.get("url")) for g in catalogue() + store["entries"]}
    known_titles = {normalized_title(g.get("title")) for g in catalogue() + store["entries"]}
    added = []
    for item in payload:
        candidate_id = item.get("id")
        title, url, source = item.get("title"), item.get("url"), item.get("sourceUrl")
        if candidate_id not in approvals or not re.fullmatch(r"gh-\d+", str(candidate_id)):
            continue
        if (not safe_url(url) or not safe_url(source)
            or urlsplit(source).hostname != "github.com"
            or not title or normalize(url) in known_urls
            or normalized_title(title) in known_titles):
            continue
        staged_id = "auto-" + candidate_id
        if staged_id in existing_ids:
            continue
        game = {"id": staged_id, "title": short(title, 100), "category": "Browser game candidate",
                "sourceUrl": source, "playUrl": url,
                "sourceRequirements": "GitHub-discovered project homepage. Direct gameplay, controls, mobile and rights not verified.",
                "verificationChecklist": "Open in real browser; verify play actually starts, controls, file/login needs, and permission to link.",
                "status": "unverified", "gameplayTested": False, "readyForPublicCatalogue": False,
                "automationEvidence": {"http": str(item.get("http", "unknown"))[:35],
                                       "browser": str(item.get("browser", "unknown"))[:50]}}
        store["entries"].append(game)
        existing_ids.add(staged_id)
        known_urls.add(normalize(url))
        known_titles.add(normalized_title(title))
        added.append(staged_id)
    if added:
        QUEUE.write_text(json.dumps(store, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("New staged entries:", ", ".join(added) if added else "none")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["scan", "render", "approve"])
    parser.add_argument("--body-file")
    args = parser.parse_args()
    if args.command == "scan":
        run_scan()
    elif args.command == "render":
        render()
    elif args.body_file:
        approve(args.body_file)
    else:
        parser.error("--body-file required for approve")

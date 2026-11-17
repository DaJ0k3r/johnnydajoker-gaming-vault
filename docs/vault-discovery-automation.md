# MADHOUSE Universal Browser-Game Intake — v2

**North star:** Build the largest trustworthy, fresh browser-playable gaming vault we can. The owner is choosing the *direction*, not selecting individual games.

## Automatic daily pipeline
1. **Daily ~7:23am Brisbane**, GitHub Actions searches six browser/HTML5 game-topic queries across GitHub, mixing recent projects and established stars.
2. Deduplicates against the live catalogue, editorial discovery queue, the current week's **pending intake branch**, and previous GitHub issue proposals.
3. Collects up to **48 unique candidate projects per daily scan**, safely HTTP-checks their homepages in parallel and audits a **different 40 existing catalogue URLs each day**. On a 146-game catalogue, a full sweep takes around four days. Future scale requires partitioning and monitoring capacity.
4. Uses headless Chrome on up to **24 new candidate pages and six existing games** per scan. Canvas, iframe, buttons or page loading are evidence of a rendered webpage **only** — not a real completed playthrough.
5. **Automatically stages EVERY safe, nonduplicate candidate** in the protected `data/discovery/candidates.json` queue. Every staged item stays `status: unverified`, `gameplayTested: false`, `readyForPublicCatalogue: false`.
6. Creates or updates **one batch pull request per calendar week** (`vault-auto-YYYY-Www`) and posts one weekly GitHub review issue, updated with daily scan results.
7. Owner reviews **one batch**, not dozens of individual games. Merge the staging PR to accept all leads into the **research queue**, not the public catalogue; flag exceptions in the PR comments.

## Getting discoveries onto MADHOUSE
- The automated queue is a **research intake**, not a website publishing step.
- To promote to the public game catalogue, test a game actually starts, controls work, browser support and account/file requirements, and permissions for linking/embedding. Public labels must distinguish GAME from RESOURCE and verified from unverified.
- A game can launch in a browser from the Vault without being embedded *inside* the Vault. Third-party framing or redistribution may be disallowed by the site's headers or licensing. Respect this; provide an honest external-open fallback.
- The Test Lab / catalogue publication bridge is a separate website-development release, subject to current deployment checks. Don't claim a game was added to the live site merely because it was discovered.

## Test, cost and operations
GitHub → Actions → **MADHOUSE Universal Game Intake** → Run workflow (main). A repository-owner issue titled `MADHOUSE: Run discovery now` also triggers a scan.

GitHub issue **MADHOUSE Discovery approvals — YYYY-Www** summarises the batch; Actions artifacts (`vault-discovery-evidence`) contain raw evidence for 30 days. Daily scans use GitHub's normal Actions allowance and GitHub API; no paid third-party API or Cloudflare Worker is required. GitHub may delay schedules or suspend them on inactive repositories.

GitHub Actions might be prohibited from creating pull requests under repository Actions settings. In that case the workflow still pushes the staging branch and includes a compare link in the weekly issue. The owner can enable **Settings → Actions → General → Workflow permissions → Allow GitHub Actions to create and approve pull requests**, or we can open the PR through the connected GitHub app.

## Non-negotiable guardrails
No copyright game files hosted or redistributed. No auto-merge. No auto-verified gameplay claims. No third-party cross-domain iframing without checking permission/support. No claims that HTTP 200 proves a game works. No automatically published game entries. No personal visitor tracking beyond existing consent/privacy choices.

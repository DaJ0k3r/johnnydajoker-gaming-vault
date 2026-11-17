# MADHOUSE discovery automation — v1

This is a scheduled, no-paid-service research assistant. It does **not** guarantee that a game plays, and does not automatically publish third-party software or claim distribution rights.

## What happens
1. Every Monday at about **7:23 am Brisbane time**, GitHub Actions searches public GitHub projects tagged browser-game or html5-game.
2. It skips URLs and titles already in the public catalogue or discovery queue, as well as previously suggested repository IDs from recent approval issues.
3. It makes a lightweight HTTP check of up to 6 new homepages and a **rotating 12 existing catalogue links**. HTTP 403/429/timeouts are uncertain, not automatically broken.
4. Chromium loads proposed homepages and reports browser observations (canvas/frame, controls, challenge, error). This is **not** a verified playthrough and does not certify a game.
5. GitHub opens **one issue per week** named “MADHOUSE Discovery approvals — YYYY-Www”, assigns the repo owner, and includes checkbox suggestions and a link health summary. GitHub notifications depend on the owner's own settings.
6. When the repo owner ticks a “QUEUE FOR TEST LAB” checkbox, a GitHub workflow opens or updates a **staging pull request** to add that lead only to `data/discovery/candidates.json`. Every entry is still `unverified` with `gameplayTested=false` and `readyForPublicCatalogue=false`. **No game gets automatically published**.
7. After a real person checks that play starts, controls function, browser requirements and rights are acceptable, the usual catalogue PR and normal site checks are still required.

## Manual run / diagnostics
GitHub → Actions → **MADHOUSE Vault Discovery & Approvals** → Run workflow (main branch).

The report and rendered checklist are saved as the Actions artifact **vault-discovery-evidence** for 30 days. The workflow can be temporarily disabled in the Actions tab. This uses the repository's normal GITHUB_TOKEN, with permissions limited by job; it requires no other service account or paid API.

## Limitations
- A responsive URL, even with a canvas, is not proof of a playable game; browser anti-bot challenges may produce inconclusive results.
- GitHub topic search covers open-source leads, **not** the entire web. Additional permitted sources can be added later.
- Public repo issues are public; don't put personal details or secret credentials in approval comments.
- Schedule events run on GitHub's default branch and may be delayed. GitHub may disable schedules on inactive public repositories.
- Automated PR creation may depend on the repository setting allowing GitHub Actions to create pull requests. If GitHub refuses, the workflow exposes the failure and can still leave a bot branch for review.

## Safety
No automatic "verified" flags. No auto-merge. No game-file redistribution. No collection of visitors' personal data. No aggressive crawling. No external payments.

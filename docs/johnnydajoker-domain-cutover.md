# MADHOUSE — johnnydajoker.com launch checklist

## Confirmed
Cloudflare Registrar registration screenshot on 17 Nov 2026 confirms ownership of `johnnydajoker.com`. Registration alone does not connect the live site. Existing GitHub Pages site: `https://daj0k3r.github.io/johnnydajoker-gaming-vault/`.

## Change being prepared in this PR (NOT live)
- `CNAME`: `johnnydajoker.com`
- Canonical, Open Graph, X/Twitter artwork and share-Vault URLs updated in `index.html`.
- Do not merge this PR until ready to execute the DNS cutover; otherwise GitHub Pages may redirect from its existing URL to an unconfigured domain.

## Cutover steps
1. In the GitHub repo, open **Settings → Pages → Custom domain** and enter `johnnydajoker.com`, then **Save**. GitHub's official instructions say to associate the custom domain in Pages **before pointing DNS** to avoid takeover risks. If branch-published, GitHub may create/update the `CNAME` file.
2. In Cloudflare dashboard, open domain **johnnydajoker.com → DNS → Records**. Set the apex (@) to these GitHub Pages **A** records (four distinct records):
   - `185.199.108.153`
   - `185.199.109.153`
   - `185.199.110.153`
   - `185.199.111.153`
   Also create `CNAME` `www` → `daj0k3r.github.io` (NOT the repo path).
3. Remove conflicting default A/AAAA/ALIAS/ANAME records for @ or conflicting www CNAME. Leave unrelated MX/TXT records alone, especially if email will use this domain later.
4. For initial troubleshooting, use **DNS only** (grey cloud) if GitHub's certificate provisioning fails with proxied records. Ensure no redirect loops between Cloudflare and GitHub. Cloudflare Registrar normally already uses Cloudflare nameservers.
5. Verify both `https://johnnydajoker.com/` and `https://www.johnnydajoker.com/` open the correct Vault. Configure `johnnydajoker.com` as canonical and expect www → apex redirect once correctly configured.
6. In GitHub **Settings → Pages**, enable **Enforce HTTPS** once certificate provisioning permits it. DNS/certificate propagation may take up to 24 hours.
7. Test homepage, images, Test Lab fetches, favouriting/refresh, roulette, link launches, mobile viewport, external link labels and Cloudflare Web Analytics visits on the new hostname.
8. Merge the release branch only when ready to direct traffic to the new domain. Retain the old GitHub Pages URL as the migration fallback and check redirect behaviour.

## Website rollout dependency
The separate Phase 1 site upgrade is under review (PR #5). Reconcile/merge it first or rebase this custom-domain branch afterwards so no later release accidentally restores old canonical/share URLs.

## Rollback
If the domain goes wrong, revert the custom-domain configuration and associated commit, restore the prior DNS records, and verify `daj0k3r.github.io/johnnydajoker-gaming-vault/` is still usable. Do not change DNS and the repo independently without confirming their intended states.

### Official references
- https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site
- https://docs.github.com/en/pages/getting-started-with-github-pages/securing-your-github-pages-site-with-https
- https://developers.cloudflare.com/dns/manage-dns-records/how-to/create-dns-records/

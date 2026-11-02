# MADHOUSE 5.4 — Ghost Hunter

Automated HTTP link checking for The Vault. **It does not confirm gameplay or game legality**, and never edits the public catalogue.

## Deploy
1. Create a Cloudflare D1 database named `madhouse-ghost-hunter` in Cloudflare Dashboard → Storage & databases → D1. Copy its Database ID.
2. In `ghost-hunter/wrangler.toml`, replace `REPLACE_WITH_YOUR_D1_DATABASE_ID` with the ID.
3. Install Node.js locally, then from this repository run:
   ```bash
   cd ghost-hunter
   npx wrangler login
   npx wrangler secret put ADMIN_TOKEN
   npx wrangler deploy
   ```
   When prompted for the secret, enter a long, random password. **Never paste the token into ChatGPT, GitHub, screenshots, or the public website.**
4. Verify `https://madhouse-ghost-hunter.YOUR-SUBDOMAIN.workers.dev/health`.
5. To trigger a check manually, use a trusted local terminal:
   ```bash
   curl -X POST -H "Authorization: Bearer YOUR_TOKEN" "https://madhouse-ghost-hunter.YOUR-SUBDOMAIN.workers.dev/run"
   ```
6. To view the latest checks:
   ```bash
   curl -H "Authorization: Bearer YOUR_TOKEN" "https://madhouse-ghost-hunter.YOUR-SUBDOMAIN.workers.dev/report"
   ```

Cron runs daily at 03:00 UTC (13:00 Brisbane). The scan is intentionally limited to 150 catalogue entries, with one request per entry; Cloudflare free-plan CPU, request and subrequest quotas may require reducing this batch or upgrading. Some game sites block bots; an HTTP error is a review flag, **not proof the game is broken**. Never make this API public with its admin token embedded in frontend code.

Future: add source-approved discovery, a private approval UI and safer chunked scanning with a queue.

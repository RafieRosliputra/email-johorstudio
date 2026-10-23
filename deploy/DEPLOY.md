# Deploy on TrueNAS SCALE + Cloudflare

Live layout on the Johor Studio TrueNAS (`m10`).

## TrueNAS
- **Code**: `/mnt/ssd/email-johorstudio` (this repo).
- Run `./setup.sh` once (creates dirs + `noreply@` mailbox + roundcube config;
  prints the mailbox password), then fill `mailserver.env` relay creds.
- Install as a **Custom App** named `mail` from `docker-compose.yml`
  (Apps → Custom App → Install via YAML, or `midclt call app.create`).
- Published ports on the host:
  - `8100` → Roundcube (web) → Cloudflare tunnel `mail.johorstudio.com`
  - `1587` → SMTP submission for LAN apps
- Redeploy after config changes: `midclt call app.redeploy mail`.

## Cloudflare (tunnel `m10`)
- Public hostname `mail.johorstudio.com` → `http://192.168.0.100:8100`.
- DNS `mail` CNAME → `<tunnel-id>.cfargotunnel.com` (proxied).
- Optionally protect `mail.johorstudio.com` with Access (owner only).

## Deliverability DNS (add once you pick a relay)
- SPF `@` TXT: `v=spf1 include:<relay-spf> ~all`
- DKIM: the record(s) your relay provider gives for `johorstudio.com`
- DMARC `_dmarc` TXT: `v=DMARC1; p=none; rua=mailto:noreply@johorstudio.com`

Until `RELAY_*` is set and the SPF/DKIM records exist, outbound mail will not be
delivered.

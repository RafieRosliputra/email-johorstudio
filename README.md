# email-johorstudio

Send-only mail for Johor Studio: a small SMTP server (`noreply@johorstudio.com`)
that relays outbound through a **smarthost**, plus **Roundcube** webmail at
`mail.johorstudio.com`. Runs on TrueNAS as a Custom App, fronted by the existing
Cloudflare tunnel (web UI only).

## Why this shape
- Apps (e.g. the photo-order site) submit mail to this server on the LAN
  (`<host>:1587`, STARTTLS) as `noreply@johorstudio.com`.
- Outbound is **relayed through a smarthost** (Brevo / Mailgun / SES / Zoho) for
  deliverability — home/studio IPs can't send directly to Gmail reliably, and
  Cloudflare Tunnel can't carry SMTP anyway.
- **No inbound mail** (no MX / port 25). `noreply@` doesn't receive. Roundcube is
  for composing/sending and sanity checks.

## Stack
- `ghcr.io/docker-mailserver/docker-mailserver` — Postfix + Dovecot, one mailbox.
- `roundcube/roundcubemail` — webmail (SQLite, no extra DB).

## Setup
```bash
git clone https://github.com/RafieRosliputra/email-johorstudio
cd email-johorstudio
./setup.sh                      # creates dirs, the noreply@ mailbox (prints its password), roundcube config
nano mailserver.env             # fill RELAY_HOST / RELAY_PORT / RELAY_USER / RELAY_PASSWORD
docker compose up -d            # or install as a TrueNAS Custom App (deploy/DEPLOY.md)
```

### Choose a smarthost (example: Brevo, free 300/day)
1. Create a Brevo account, verify the domain `johorstudio.com`, get an **SMTP key**.
2. In `mailserver.env`:
   ```
   RELAY_HOST=smtp-relay.brevo.com
   RELAY_PORT=587
   RELAY_USER=<brevo login>
   RELAY_PASSWORD=<brevo smtp key>
   ```
3. Add the DNS records Brevo shows (DKIM + SPF include). Then `docker compose restart mailserver`.

## DNS (Cloudflare, zone johorstudio.com)
| Record | Name | Value | Notes |
|---|---|---|---|
| CNAME | `mail` | `<tunnel-id>.cfargotunnel.com` (proxied) | Roundcube webmail |
| TXT | `@` | `v=spf1 include:<relay-spf> ~all` | per relay provider |
| TXT (DKIM) | provider-specific | provider value | from the relay provider |
| TXT | `_dmarc` | `v=DMARC1; p=none; rua=mailto:noreply@johorstudio.com` | start permissive |

## Apps: how to send through this server
Point an app's SMTP at the mail server on the LAN:
```
SMTP_HOST=192.168.0.100
SMTP_PORT=1587
SMTP_USER=noreply@johorstudio.com
SMTP_PASSWORD=<mailbox password from setup.sh>
SMTP_STARTTLS=true          # self-signed internally — don't verify the cert
EMAIL_FROM=Johor Studio <noreply@johorstudio.com>
```

## Change the mailbox password
```
docker exec -it dms setup email update noreply@johorstudio.com '<newpass>'
```

## Security notes
- Internal traffic (apps/roundcube ↔ mailserver) uses a self-signed cert on the
  LAN; clients skip verification. Fine for a trusted LAN — front with real certs if
  you ever expose it.
- This is **not** an open relay: only authenticated `noreply@` can submit, and it
  only relays to the configured smarthost.

# mail-admin

A tiny web tool to manage the docker-mailserver mailboxes & aliases, deployed as
a separate TrueNAS app at **mailadmin.johorstudio.com** and protected by
**Cloudflare Access** (owner email only). Link it from your Webmaster portal.

It edits the mounted DMS config files (auto-reloaded by the mail server):
- `postfix-accounts.cf` — mailboxes (`email|{SHA512-CRYPT}$6$…`)
- `postfix-virtual.cf` — aliases (`alias  destination`)

**Password sync:** when the `noreply@johorstudio.com` password is changed here,
the plaintext is also written to a shared secret file
(`/secrets/noreply.pw` → `/mnt/a/storage/website/print purchase/secrets/noreply.pw`)
that the photo-order app reads live via `SMTP_PASSWORD_FILE` — so the app's email
keeps working without a redeploy.

## Deploy (TrueNAS)
```bash
docker build -t johorstudio-mailadmin:local /mnt/ssd/email-johorstudio/mailadmin
# install truenas-app.yaml as a Custom App "mailadmin" (midclt app.create), host port 8120
mkdir -p "/mnt/a/storage/website/print purchase/secrets"
```
Then add the Cloudflare tunnel hostname `mailadmin.johorstudio.com → http://192.168.0.100:8120`,
a DNS CNAME, and a Cloudflare Access policy allowing the owner email.

Also set in the photo-order `.env`:
```
SMTP_PASSWORD_FILE=/mnt/a/storage/website/print purchase/secrets/noreply.pw
```
and write the current password into that file once.

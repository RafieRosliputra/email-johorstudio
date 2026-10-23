#!/usr/bin/env bash
# One-time setup: create data dirs, the noreply@ mailbox, and Roundcube config.
# Safe to re-run (won't overwrite existing account/config).
set -euo pipefail
cd "$(dirname "$0")"

mkdir -p dms/mail-data dms/mail-state dms/mail-logs dms/config/ssl roundcube/config roundcube/db

[ -f mailserver.env ] || cp mailserver.env.example mailserver.env

# Self-signed TLS cert for the mail server (internal/LAN; clients skip verify)
if [ ! -f dms/config/ssl/cert.pem ]; then
  openssl req -x509 -newkey rsa:2048 -nodes -days 3650 \
    -subj "/CN=mail.johorstudio.com" \
    -keyout dms/config/ssl/key.pem -out dms/config/ssl/cert.pem 2>/dev/null
fi

# Mailbox: noreply@johorstudio.com
ACC=dms/config/postfix-accounts.cf
if [ ! -f "$ACC" ]; then
  PW="${MAILBOX_PASSWORD:-$(openssl rand -base64 18)}"
  HASH="$(openssl passwd -6 "$PW")"
  echo "noreply@johorstudio.com|{SHA512-CRYPT}${HASH}" > "$ACC"
  echo "=============================================================="
  echo " Mailbox noreply@johorstudio.com"
  echo " PASSWORD: ${PW}"
  echo " (store this; used by apps SMTP_PASSWORD and Roundcube login)"
  echo "=============================================================="
fi

# Roundcube config
RC=roundcube/config/config.inc.php
if [ ! -f "$RC" ]; then
  DES="$(openssl rand -base64 48 | tr -dc 'A-Za-z0-9' | head -c 24)"
  sed "s/__DESKEY__/${DES}/" roundcube/config/config.inc.php.template > "$RC"
fi

echo "setup done."

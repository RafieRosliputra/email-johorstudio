"""mail-admin — tiny web tool to manage docker-mailserver accounts & aliases.

No application login: protected by Cloudflare Access at the edge. It edits the
mounted docker-mailserver config files (which DMS auto-reloads):
  - accounts: postfix-accounts.cf   (email|{SHA512-CRYPT}$6$...)
  - aliases:  postfix-virtual.cf    (alias@domain  destination@domain)

When the synced account's (noreply@) password changes, the plaintext is also
written to a shared secret file that the photo-order app reads live — so its
SMTP keeps working without a redeploy.
"""
from __future__ import annotations

import crypt
import html
import os
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

ACCOUNTS = Path(os.environ.get("ACCOUNTS_FILE", "/dms-config/postfix-accounts.cf"))
ALIASES = Path(os.environ.get("ALIASES_FILE", "/dms-config/postfix-virtual.cf"))
SYNC_EMAIL = os.environ.get("SYNC_EMAIL", "noreply@johorstudio.com")
SYNC_SECRET_FILE = os.environ.get("SYNC_SECRET_FILE", "")
DOMAIN = os.environ.get("DOMAIN", "johorstudio.com")
ADMIN_EMAIL_HEADER = os.environ.get("ADMIN_EMAIL_HEADER", "Cf-Access-Authenticated-User-Email")

app = FastAPI(title="mail-admin", docs_url=None, redoc_url=None)


# --- data helpers ----------------------------------------------------------
def list_accounts() -> list[str]:
    if not ACCOUNTS.exists():
        return []
    out = []
    for line in ACCOUNTS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and "|" in line and not line.startswith("#"):
            out.append(line.split("|", 1)[0])
    return sorted(out)


def set_account(email: str, password: str) -> None:
    h = crypt.crypt(password, crypt.mksalt(crypt.METHOD_SHA512))
    newline = f"{email}|{{SHA512-CRYPT}}{h}"
    lines = ACCOUNTS.read_text(encoding="utf-8").splitlines() if ACCOUNTS.exists() else []
    out, found = [], False
    for l in lines:
        if l.strip() and l.split("|", 1)[0] == email:
            out.append(newline); found = True
        elif l.strip():
            out.append(l)
    if not found:
        out.append(newline)
    ACCOUNTS.parent.mkdir(parents=True, exist_ok=True)
    ACCOUNTS.write_text("\n".join(out) + "\n", encoding="utf-8")
    if email == SYNC_EMAIL and SYNC_SECRET_FILE:
        p = Path(SYNC_SECRET_FILE)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(password, encoding="utf-8")


def delete_account(email: str) -> None:
    if not ACCOUNTS.exists() or email == SYNC_EMAIL:
        return  # never delete the synced system mailbox from here
    out = [l for l in ACCOUNTS.read_text(encoding="utf-8").splitlines()
           if l.strip() and l.split("|", 1)[0] != email]
    ACCOUNTS.write_text("\n".join(out) + "\n", encoding="utf-8")


def list_aliases() -> list[tuple[str, str]]:
    if not ALIASES.exists():
        return []
    out = []
    for line in ALIASES.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            parts = line.split()
            if len(parts) >= 2:
                out.append((parts[0], " ".join(parts[1:])))
    return sorted(out)


def set_alias(alias: str, dest: str) -> None:
    lines = ALIASES.read_text(encoding="utf-8").splitlines() if ALIASES.exists() else []
    out = [l for l in lines if l.strip() and l.split()[0] != alias]
    out.append(f"{alias} {dest}")
    ALIASES.parent.mkdir(parents=True, exist_ok=True)
    ALIASES.write_text("\n".join(out) + "\n", encoding="utf-8")


def delete_alias(alias: str) -> None:
    if not ALIASES.exists():
        return
    out = [l for l in ALIASES.read_text(encoding="utf-8").splitlines()
           if l.strip() and l.split()[0] != alias]
    ALIASES.write_text("\n".join(out) + "\n", encoding="utf-8")


# --- UI --------------------------------------------------------------------
def page(msg: str = "") -> str:
    accs = "".join(
        f"<tr><td>{html.escape(a)}</td><td>"
        f"<form method=post action=/account/password class=inline>"
        f"<input type=hidden name=email value='{html.escape(a)}'>"
        f"<input name=password placeholder='new password' required>"
        f"<button>Set password</button></form>"
        + ("" if a == SYNC_EMAIL else
           f"<form method=post action=/account/delete class=inline onsubmit=\"return confirm('Delete {html.escape(a)}?')\">"
           f"<input type=hidden name=email value='{html.escape(a)}'><button class=del>Delete</button></form>")
        + (f" <span class=tag>synced → photo-order</span>" if a == SYNC_EMAIL else "")
        + "</td></tr>"
        for a in list_accounts()
    ) or "<tr><td colspan=2 class=muted>No accounts</td></tr>"

    als = "".join(
        f"<tr><td>{html.escape(al)}</td><td>{html.escape(dst)}</td><td>"
        f"<form method=post action=/alias/delete class=inline><input type=hidden name=alias value='{html.escape(al)}'>"
        f"<button class=del>Delete</button></form></td></tr>"
        for al, dst in list_aliases()
    ) or "<tr><td colspan=3 class=muted>No aliases</td></tr>"

    banner = f"<div class=ok>{html.escape(msg)}</div>" if msg else ""
    return f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><title>Mail Admin — Johor Studio</title>
<style>
:root{{--ink:#1c1b19;--muted:#6b675f;--line:#e6e2db;--sand:#f3f0ec;--accent:#2c2a27;--ok:#1f7a4d;--err:#b42318}}
*{{box-sizing:border-box}}body{{font-family:system-ui,sans-serif;max-width:860px;margin:0 auto;padding:20px;color:var(--ink)}}
h1{{font-size:22px}}h2{{font-size:17px;margin-top:28px}}
table{{width:100%;border-collapse:collapse;margin-top:8px}}td,th{{text-align:left;padding:8px;border-bottom:1px solid var(--line);vertical-align:middle}}
input,button{{font:inherit;padding:8px 10px;border:1px solid var(--line);border-radius:8px}}
button{{background:var(--accent);color:#fff;border:0;cursor:pointer}}button.del{{background:#fde7e4;color:var(--err)}}
.inline{{display:inline-flex;gap:6px;margin:2px 0}}
.card{{border:1px solid var(--line);border-radius:12px;padding:16px;margin-top:12px;background:#fff}}
.ok{{background:#e3f2ea;color:var(--ok);padding:10px 14px;border-radius:10px;margin:10px 0}}
.muted{{color:var(--muted)}}.tag{{font-size:11px;background:var(--sand);padding:2px 8px;border-radius:999px}}
.row{{display:flex;gap:8px;flex-wrap:wrap}}
</style></head><body>
<h1>Mail Admin — {html.escape(DOMAIN)}</h1>
<p class=muted>Dilindungi Cloudflare Access. Perubahan auto-reload oleh mail server.</p>
{banner}

<h2>Akaun</h2>
<table><tr><th>E-mel</th><th>Tindakan</th></tr>{accs}</table>
<div class=card><form method=post action=/account/add class=row>
<input name=local placeholder=namamailbox required><span style=align-self:center>@{html.escape(DOMAIN)}</span>
<input name=password placeholder=password required><button>Tambah akaun</button></form></div>

<h2>Alias (forwarding)</h2>
<table><tr><th>Alias</th><th>→ Destinasi</th><th></th></tr>{als}</table>
<div class=card><form method=post action=/alias/add class=row>
<input name=alias placeholder="info@{html.escape(DOMAIN)}" required>
<input name=dest placeholder="someone@gmail.com" required><button>Tambah alias</button></form></div>
</body></html>"""


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return page(request.query_params.get("msg", ""))


@app.post("/account/add")
def account_add(local: str = Form(...), password: str = Form(...)):
    email = f"{local.strip().lower()}@{DOMAIN}" if "@" not in local else local.strip().lower()
    set_account(email, password)
    return RedirectResponse(f"/?msg=Akaun {email} disimpan", status_code=303)


@app.post("/account/password")
def account_password(email: str = Form(...), password: str = Form(...)):
    set_account(email.strip().lower(), password)
    extra = " (+ photo-order sync)" if email.strip().lower() == SYNC_EMAIL else ""
    return RedirectResponse(f"/?msg=Password {email} ditukar{extra}", status_code=303)


@app.post("/account/delete")
def account_delete(email: str = Form(...)):
    delete_account(email.strip().lower())
    return RedirectResponse(f"/?msg=Akaun {email} dibuang", status_code=303)


@app.post("/alias/add")
def alias_add(alias: str = Form(...), dest: str = Form(...)):
    set_alias(alias.strip().lower(), dest.strip())
    return RedirectResponse(f"/?msg=Alias {alias} disimpan", status_code=303)


@app.post("/alias/delete")
def alias_del(alias: str = Form(...)):
    delete_alias(alias.strip().lower())
    return RedirectResponse(f"/?msg=Alias {alias} dibuang", status_code=303)

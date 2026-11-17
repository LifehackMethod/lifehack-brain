#!/usr/bin/env python3
"""token_check.py — read-only: what can be known LOCALLY about the rig login's 7-day testing-mode expiry.

Google rule: an OAuth app whose publishing status is "Testing" (external user type) has its refresh tokens
expire 7 days after they are issued. Whether the app is in Testing is NOT knowable from local files — only the
Cloud Console shows it. This script reports what IS local: the project id, when the rig's stored credential was
last written (≈ when the refresh token was issued, i.e. the last `gws auth login`), and the date a Testing-mode
token would die. No network. Never decrypts or prints a secret: it reads client_secret.json for project_id only,
and only stats (mtime/size) the encrypted files.

Run: python3 token_check.py [--json]      exit 0 always (information, not a gate); exit 2 if inputs are missing.
"""
import datetime
import json
import os
import sys

LOGIN = os.path.expanduser("~/.config/gws-rig")
TESTING_TTL = datetime.timedelta(days=7)
WARN_WITHIN = datetime.timedelta(days=2)


def _mtime(name):
    p = os.path.join(LOGIN, name)
    try:
        return datetime.datetime.fromtimestamp(os.stat(p).st_mtime).astimezone()
    except OSError:
        return None


def _project_id():
    try:
        d = json.load(open(os.path.join(LOGIN, "client_secret.json"), encoding="utf-8"))
        blob = d.get("installed") or d.get("web") or {}
        return blob.get("project_id"), bool(blob.get("client_id"))
    except (OSError, ValueError):
        return None, False


def _plain_json_expiry():
    """token_cache.json is encrypted on this rig (not JSON). If a future gws version stores plain fields, show
    ONLY expiry-like timestamps from it — never any token value."""
    try:
        d = json.load(open(os.path.join(LOGIN, "token_cache.json"), encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return None
    return {k: v for k, v in d.items() if isinstance(k, str) and "expir" in k.lower()} if isinstance(d, dict) else None


def facts(now=None):
    now = now or datetime.datetime.now().astimezone()
    cred, cache = _mtime("credentials.enc"), _mtime("token_cache.json")
    pid, has_client = _project_id()
    out = {"login_dir": LOGIN, "project_id": pid, "client_id_present": has_client,
           "credentials_enc_written": cred.isoformat(timespec="minutes") if cred else None,
           "token_cache_touched": cache.isoformat(timespec="minutes") if cache else None,
           "token_cache_plain_expiry_fields": _plain_json_expiry()}
    if cred:
        dies = cred + TESTING_TTL
        left = dies - now
        out["if_testing_mode_refresh_token_dies"] = dies.isoformat(timespec="minutes")
        out["if_testing_mode_time_left_hours"] = round(left.total_seconds() / 3600, 1)
        out["status"] = ("EXPIRED-IF-TESTING" if left.total_seconds() <= 0 else
                         "EXPIRES-SOON-IF-TESTING" if left <= WARN_WITHIN else "OK-FOR-NOW-IF-TESTING")
    else:
        out["status"] = "UNKNOWN (credentials.enc missing)"
    return out


MANUAL = """\
MANUAL CHECK (the owner, ~1 minute, Google Cloud Console — local files cannot tell us this):
  1. console.cloud.google.com -> project "{pid}" (top project picker).
  2. APIs & Services -> OAuth consent screen (newer UI: "Google Auth Platform" -> Audience).
  3. Read "Publishing status":  Testing  |  In production.
  - In production            -> nothing expires on a 7-day clock. Done. (An unverified app may show a warning
                                screen at login, and that is fine for your own account.)
  - Testing (user type External) -> the refresh token dies 7 days after it was issued; the rig login then fails
                                with invalid_grant. Pick one:
       a) Click "Publish app" -> In production. Free, one click. Unverified-app warning at login is expected
          for your own account; you do not need Google verification for personal use. Then re-run the rig login
          ONCE so the new token is a production one. Best fix for Phase E (a daily job cannot re-login weekly).
       b) Stay in Testing and re-run the rig login every 6 days (put it on the calendar). Fragile for a
          scheduled job; if it lapses the daily pull fails loud, nothing is lost.
  - Internal user type           -> not applicable to a personal gmail.com account (no 7-day limit either way).
  Either way: tell me which one it said, and I will record it in the plan."""


def main(argv):
    f = facts()
    if "--json" in argv:
        print(json.dumps(f, indent=2))
        return 0 if f["project_id"] else 2
    print("== rig login: what local files can say about the 7-day testing-mode expiry ==")
    for k, v in f.items():
        print(f"  {k}: {v}")
    print()
    print("Local inference only: credentials.enc was last written when the refresh token was issued (the last login).")
    print("IF the app is in Testing, the token dies at 'if_testing_mode_refresh_token_dies'. If it is In production, "
          "ignore that date.\n")
    print(MANUAL.format(pid=f["project_id"] or "<your project>"))
    return 0 if f["project_id"] else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

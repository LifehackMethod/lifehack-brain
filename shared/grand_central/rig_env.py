"""rig_env.py — the one place the rig decides which Google login it uses.

Why this exists: the sanctioned doors (email_fetch.py, safe_calendar.py, safe_tasks.py) inherit the caller's
environment, and email_fetch.py falls back to the broad YOLO login when GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE is
set or ~/.config/lifehack/gws-credentials.json exists. A rig run that silently used the broad login would make
every wall test pass by accident. So every rig process gets its environment from here, and nowhere else.

Also isolates the door's side effects: the Sentinel pause list and the last-seen bookmarks point at rig-local
files, so a rig run can never pause a YOLO label or move a YOLO bookmark.
"""
import os

import gc_settings

RIG_HOME = gc_settings.data_root()
RIG_LOGIN = os.path.expanduser("~/.config/gws-rig")
LIFEHACK = gc_settings.plugin_root()     # the plugin this code runs from (its safe tools and email door)
EMAIL_DOOR_DIR = os.path.join(LIFEHACK, "shared", "tools")
SAFE_CALENDAR = os.path.join(LIFEHACK, "system", "tools", "safe_calendar.py")
SAFE_TASKS = os.path.join(LIFEHACK, "system", "tools", "safe_tasks.py")

EXPECTED_DATA_SCOPES = {
    "https://www.googleapis.com/auth/gmail.metadata",
    "https://www.googleapis.com/auth/calendar.events.readonly",
    "https://www.googleapis.com/auth/tasks.readonly",
    "https://www.googleapis.com/auth/gmail.settings.filters.readonly",   # 2.0b step 1
    "https://www.googleapis.com/auth/contacts.readonly",                 # 2.0b step 1
}
IDENTITY_SCOPES = {
    "email", "profile", "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
}


def rig_environ(base=None, planted=False):
    """Return an environment that can only reach Google through the rig login.
    planted=True is for the Sentinel test set: same lane, but no push notifications (see INTAKE.md §5.1)."""
    env = dict(os.environ if base is None else base)
    for k in ("GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE", "GOOGLE_WORKSPACE_CLI_TOKEN"):
        env.pop(k, None)
    # The rig's readers (intake_reader inside gate_message, batch_reader) must use the claude.ai
    # login, never a caller's ANTHROPIC_API_KEY / AUTH_TOKEN / BASE_URL — a harness window (e.g. the
    # claude-cheap shim) sets those to a proxy and makes claude -p exit 1, which quarantines
    # everything as UNJUDGED. Dropping them lets claude fall back to its own login. (2026-11-10,
    # task 1.5b: first planted run had phrase-layer UNJUDGEDs from exactly this.)
    for k in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL"):
        env.pop(k, None)
    env["GOOGLE_WORKSPACE_CLI_CONFIG_DIR"] = RIG_LOGIN
    env["GOOGLE_WORKSPACE_CLI_KEYRING_BACKEND"] = "file"
    # email_fetch.py's fallback to the broad login checks this path first; point it at nothing.
    env["LIFEHACK_GWS_CREDS_FILE"] = os.path.join(RIG_HOME, "no-broad-login-here")
    # Door side effects stay inside the rig.
    os.makedirs(os.path.join(RIG_HOME, "state"), exist_ok=True)
    env["SENTINEL_PAUSE_FILE"] = os.path.join(RIG_HOME, "state", "sentinel-paused-sources")
    env["LIFEHACK_LAST_SEEN_DIR"] = os.path.join(RIG_HOME, "state")
    # Sentinel's ledger, status tile and ack store stay inside the rig; the rig never tries to move mail.
    env["SENTINEL_LOG"] = os.path.join(RIG_HOME, "state", "sentinel-events.jsonl")
    env["SENTINEL_STATUS"] = os.path.join(RIG_HOME, "state", "sentinel-status.json")
    env["SENTINEL_ACKED_FP"] = os.path.join(RIG_HOME, "state", "sentinel-acked-fingerprints.json")
    if planted:
        # Planted runs get their own pause/ledger/status/ack files. 2026-11-10: a planted REAL-ATTACK test item
        # (T09) wrote `email:rig` into the shared pause file and paused the REAL rig unit.
        pdir = os.path.join(RIG_HOME, "state", "planted")
        os.makedirs(pdir, exist_ok=True)
        env["SENTINEL_PAUSE_FILE"] = os.path.join(pdir, "sentinel-paused-sources")
        env["SENTINEL_LOG"] = os.path.join(pdir, "sentinel-events.jsonl")
        env["SENTINEL_STATUS"] = os.path.join(pdir, "sentinel-status.json")
        env["SENTINEL_ACKED_FP"] = os.path.join(pdir, "sentinel-acked-fingerprints.json")
    # The reader's dedupe cache (batch_reader.py): rig-local, CLEAN verdicts only. A planted run NEVER uses it,
    # so a planted trick cannot ride a cached CLEAN.
    env["SENTINEL_DEDUPE_DB"] = os.path.join(RIG_HOME, "state", "sentinel-dedupe.sqlite")
    if planted:
        env["SENTINEL_DEDUPE_DISABLE"] = "1"
    else:
        env.pop("SENTINEL_DEDUPE_DISABLE", None)
    env["SENTINEL_QUARANTINE_DISABLE"] = "1"
    if planted:
        env["SENTINEL_NOTIFY_DISABLE"] = "1"   # 15 planted attacks must not page the owner
    return env


def apply_to_this_process(planted=False):
    """Make the current process (and anything it imports) use the rig login."""
    env = rig_environ(planted=planted)   # build from the current environment BEFORE clearing it
    os.environ.clear()
    os.environ.update(env)

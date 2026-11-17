# origin: 92a9739:mover/limits.py
"""limits.py - Google's ceilings for a consumer Apps Script account. TRACKED ONLY.

Google ceilings, confirmed 2026-11-12 from Google's pages (quotas page updated 2026-09-03, Gmail quota page 2026-10-16):
  https://developers.google.com/apps-script/guides/services/quotas
  https://developers.google.com/gmail/api/reference/quota
  https://developers.google.com/gmail/api/reference/rest/v1/users.messages/batchModify
There is NO self-imposed quota here: mover_usage.py counts usage and raises a WARN tile at
WARN_FRACTION of any ceiling. (Separate from this: MAX_IDS_PER_REQUEST in mover_schema.py is a
per-request typo guard, and the script's ~2 min run budget keeps a run clear of Google's 6-minute hard stop.)
"""
WARN_FRACTION = 0.5

# name -> (ceiling, unit, human label)
CEILINGS = {
    "runtime_min_per_day":       (90,     "min",   "Timer runtime per day"),
    "runtime_min_per_run":       (6,      "min",   "Longest single run"),
    "gmail_ops_per_day":         (20000,  "ops",   "Email read/write per day (each id modified counted as 1; mapping unconfirmed)"),
    "properties_ops_per_day":    (50000,  "ops",   "Properties read/write per day"),
}
BATCHMODIFY_MAX_IDS = 1000       # per call; 50 quota units each; Gmail API allows 6,000 units/min/user
TRIGGERS_MAX_PER_SCRIPT = 20

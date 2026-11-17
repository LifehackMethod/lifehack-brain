#!/usr/bin/env python3
# not-wired-yet: the Phase 5 filter lane's backstop
"""filter_drift.py: read-only backstop for the Phase C hands (coordinator condition 2, 2026-11-12).

Lists the LIVE Gmail filters through the rig's own read-only login (gmail.settings.filters.readonly,
via rig_env), so it doesn't depend on the clasp token or the Apps Script code. Then it flags:
  - FORWARD: any filter whose action forwards mail (the exfiltration path)
  - TRASH:   any filter that adds TRASH (silent destruction of future mail), EXCEPT the single always-junk
             filter the owner allowed (2026-11-12): criteria only a plain `from` list, action exactly
             add TRASH + remove INBOX (+ optional UNREAD). A second such filter is flagged.
  - UNKNOWN: any filter id not in the approved baseline (state/approved-filters.json)
Exit 0 = clean, 1 = alert (printed loudly), 2 = could not check (treat as an alert).

  python filter_drift.py            check against the approved baseline
  python filter_drift.py --baseline write the current live filters as the approved baseline
                                    (only after the owner approves a batch and the real run is done)
Prints filter ids, criteria and actions only. Never touches mail.
"""
import json
import os
import re
import subprocess
import sys

import rig_env


class S:
    """The always-junk filter rules this check needs, held here because the filter-changing hands (changelist_schema) are
    not part of this plugin folder. They mirror that applier's rules (a plain `from` list of addresses/domains, remove only
    INBOX/UNREAD); if the applier's rules change, change these with them."""
    JUNK_REMOVE_OK = {"INBOX", "UNREAD"}
    _ADDR = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9._%+-]*@[A-Za-z0-9][A-Za-z0-9-]*(\.[A-Za-z0-9][A-Za-z0-9-]*)+$")
    _DOMAIN = re.compile(r"^@?[A-Za-z0-9][A-Za-z0-9-]*(\.[A-Za-z0-9][A-Za-z0-9-]*)+$")

    @classmethod
    def junk_from_ok(cls, v):
        """True if v is 'tok OR tok OR ...' where every tok is one plain address or domain (no words, wildcards, operators)."""
        if not isinstance(v, str) or not v or v != v.strip():
            return False
        return all(cls._ADDR.match(t) or cls._DOMAIN.match(t) for t in v.split(" OR "))

BASE = os.path.join(rig_env.RIG_HOME, "state", "approved-filters.json")


def live_filters():
    r = subprocess.run(["gws", "gmail", "users", "settings", "filters", "list", "--params", json.dumps({"userId": "me"})],
                       capture_output=True, text=True, timeout=90, env=os.environ.copy())
    if r.returncode != 0:
        raise RuntimeError(f"filters.list failed rc={r.returncode}")
    return json.loads(r.stdout or "{}").get("filter", [])


def is_allowed_junk(f):
    """True if this live filter has exactly the shape of the one allowed always-junk Trash filter."""
    c, a = f.get("criteria") or {}, f.get("action") or {}
    if set(c) != {"from"} or not S.junk_from_ok(c.get("from")):
        return False
    if set(a) - {"addLabelIds", "removeLabelIds"} or a.get("addLabelIds") != ["TRASH"]:
        return False
    rem = a.get("removeLabelIds") or []
    return "INBOX" in rem and len(set(rem)) == len(rem) and set(rem) <= S.JUNK_REMOVE_OK


def find_alerts(fl, approved):
    alerts, junk_allowed = [], 0
    for f in fl:
        act = f.get("action", {})
        if act.get("forward"):
            alerts.append(("FORWARD", f))
        if "TRASH" in (act.get("addLabelIds") or []):
            if is_allowed_junk(f) and junk_allowed == 0:
                junk_allowed += 1          # the ONE allowed always-junk filter; any further Trash filter is drift
            else:
                alerts.append(("TRASH", f))
        if approved and f["id"] not in approved:
            alerts.append(("UNKNOWN", f))
    return alerts


def main(argv):
    rig_env.apply_to_this_process()
    try:
        fl = live_filters()
    except Exception as e:  # noqa: BLE001  (a failed check is itself an alert)
        print(f"DRIFT CHECK COULD NOT RUN: {e}", file=sys.stderr)
        return 2
    if "--labels" in argv:
        r = subprocess.run(["gws", "gmail", "users", "labels", "list", "--params", json.dumps({"userId": "me"})],
                           capture_output=True, text=True, timeout=90, env=os.environ.copy())
        names = sorted(x["name"] for x in json.loads(r.stdout or "{}").get("labels", []) if x.get("type") == "user")
        print(f"user labels: {len(names)}")
        for n in names:
            print("  " + n)
    if "--baseline" in argv:
        with open(BASE, "w", encoding="utf-8") as fh:
            json.dump({"ids": sorted(f["id"] for f in fl), "count": len(fl)}, fh, indent=1)
        print(f"baseline written: {len(fl)} filters -> {BASE}")
        return 0
    approved = set()
    if os.path.exists(BASE):
        approved = set(json.load(open(BASE, encoding="utf-8")).get("ids", []))
    alerts = find_alerts(fl, approved)
    print(f"filters live: {len(fl)}; approved baseline: {len(approved) or 'none yet'}")
    for kind, f in alerts:
        print(f"!!! {kind}: id={f['id']} criteria={json.dumps(f.get('criteria', {}))} action={json.dumps(f.get('action', {}))}")
    if alerts:
        print("ALERT: filter drift found. Tell the owner.", file=sys.stderr)
        return 1
    print("clean: no forwarding, no trash, nothing unapproved")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

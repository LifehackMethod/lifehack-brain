#!/usr/bin/env python3
"""sentinel_quarantine.py — apply the Sentinel/Quarantine Gmail label to a DANGER message.

WHAT: called by the Sentinel gate (sentinel_response.py) on a DANGER verdict when a Gmail
--message-id is known — mirrors notify_danger(). This is the "contain" half of the response:
the dangerous item gets visibly walled off in Gmail so it's out of the normal ingest flow and
a human can review it. REVERSIBLE by design — it adds a LABEL, never deletes or moves the
message (un-label is a one-click human action, same posture as un-pause being human-only).

Idempotent: finds-or-creates the `Sentinel/Quarantine` label, then adds it to the message
(re-running is a no-op). Fail-LOUD to stderr; the gate treats any failure as NON-FATAL — a
quarantine miss is logged but never breaks the ingestion run (the event is already in the
ledger + the source is already paused; the label is the visible cherry, not the safety floor).

Usage:
    python3 sentinel_quarantine.py --message-id <gmail-id> [--label "Sentinel/Quarantine"]
Exit 0 = labeled (or already labeled). Non-zero = could not label (caller continues anyway).

Needs gws creds (unlike the stdlib-only gate) — that's WHY it's a separate tool the gate
shells out to, keeping the gate itself creds-free + Studio-safe. Always parses gws JSON off
stdout; gws chatter goes to stderr.
"""
import sys, json, argparse, subprocess

LABEL_DEFAULT = "Sentinel/Quarantine"


def gws(args, timeout=25):
    """Run a gws subcommand, return parsed JSON stdout. Raise on non-zero rc."""
    r = subprocess.run(["gws"] + args, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"gws {' '.join(args)} -> rc{r.returncode}: {r.stderr.strip()[:200]}")
    return json.loads(r.stdout) if r.stdout.strip() else {}


def find_or_create_label(name):
    """Return the labelId for `name`, creating a nested Gmail label if it doesn't exist.
    gws splits the call: --params = path/query (userId), --json = request body (the label fields)."""
    d = gws(["gmail", "users", "labels", "list",
             "--params", json.dumps({"userId": "me"}), "--format", "json"])
    for l in d.get("labels", []):
        if l.get("name") == name:
            return l["id"]
    body = {"name": name, "labelListVisibility": "labelShow", "messageListVisibility": "show"}
    c = gws(["gmail", "users", "labels", "create",
             "--params", json.dumps({"userId": "me"}),
             "--json", json.dumps(body), "--format", "json"])
    return c["id"]


def quarantine(message_id, label=LABEL_DEFAULT):
    lid = find_or_create_label(label)
    gws(["gmail", "users", "messages", "modify",
         "--params", json.dumps({"userId": "me", "id": message_id}),
         "--json", json.dumps({"addLabelIds": [lid]}), "--format", "json"])
    return lid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--message-id", required=True)
    ap.add_argument("--label", default=LABEL_DEFAULT)
    a = ap.parse_args()
    try:
        lid = quarantine(a.message_id, a.label)
        print(f"QUARANTINED {a.message_id} -> {a.label} ({lid})")
        return 0
    except Exception as e:
        sys.stderr.write(f"[sentinel-quarantine] FAILED for {a.message_id}: {e}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""planning-light-sweep.py — Cal's LIGHT "what's new since the 4am pull?" email check.

METADATA ONLY — subjects/senders/dates, NO bodies, no email_convert, no vault rebuild. This is the
sanctioned answer to "hey, check my email, something might have popped in since this morning": one fast
`gws gmail ... format:metadata` pass, not the heavy verbatim re-ingest (planning-vault-pull.py). Per the
planning-daily ONE-DATASET rail: the ban is on RE-PULLING EVERYTHING; a light delta sweep is fine.

Cutoff: derived from today's vault `_manifest.json` `generated_at` (the 4:10am pull time) → a Gmail
`after:YYYY/MM/DD` filter (date-granular — Gmail q isn't reliably tested with unix-epoch here). Override
with --since YYYY/MM/DD or --query. Subjects/senders are adversarial → L0 sanitize() before surfacing.

READ-ONLY against Google (list + format:metadata pass the email-sanitize hook untouched; no lane gate).
Fail-soft: any error → honest-empty, exit 0. Usage: planning-light-sweep.py [--since YYYY/MM/DD] [--query Q] [--cap N]
"""
import argparse, json, os, subprocess, sys, time
from datetime import datetime

# The notes folder, through the one resolver. ⛔ NOT a default and NOT a guess: the tool this came
# from hardcoded one person's Drive path, so on any other machine it wrote its vault into a
# directory that did not exist. `resolve_brain_root()` returns (source, path); NOT-SET is (None,
# None), and a tool with nowhere to write must say so rather than invent somewhere.
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "shared"))
import brain_root                                                            # noqa: E402
import cal_config                                                            # noqa: E402
_SRC, DRIVE = brain_root.resolve_brain_root()
if not DRIVE:
    sys.stderr.write(
        "no notes folder is set, so there is nowhere to put what this reads.\n"
        "Set it once:  python3 shared/brain_root.py --set \"<the folder your notes live in>\"\n")
    sys.exit(2)
# ⚠ The DATA PATH is deliberately still `desks/cal/`. This desk's code, tools, jobs and tiles are
# renamed to `planning`; the records directory is NOT, because moving the operator's live records is
# his decision and has not been taken. KNOWN, INTENTIONAL split — do not "complete" it without his word.
VAULT_ROOT = os.path.join(DRIVE, "desks/cal/state/raw-vault")
GWS = __import__("shutil").which("gws") or "gws"

# L0 sanitize for adversarial metadata (same core email_convert/planning-vault-pull use)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from sanitize import sanitize
    def _clean(s):
        try: return sanitize(s or "", max_len=200)
        except Exception: return (s or "")[:200]
except Exception:
    def _clean(s): return (s or "")[:200]


def gws_json(args, params):
    r = subprocess.run([GWS] + args + ["--params", json.dumps(params)],
                       capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        raise RuntimeError((r.stderr.strip().splitlines() or ["gws err"])[-1])
    return json.loads(r.stdout or "{}")


def pull_cutoff(date_str):
    """Gmail after: cutoff from the day's vault manifest generated_at, else today (YYYY/MM/DD)."""
    man = os.path.join(VAULT_ROOT, date_str, "_manifest.json")
    try:
        gen = json.load(open(man)).get("generated_at", "")
        d = datetime.fromisoformat(gen).date() if gen else datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
    return d.strftime("%Y/%m/%d")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", help="Gmail after: cutoff YYYY/MM/DD (default: from today's vault pull)")
    ap.add_argument("--query", help="override the base Gmail query (default: category:primary in:inbox)")
    ap.add_argument("--cap", type=int, default=30, help="max messages to surface (default 30)")
    args = ap.parse_args()

    today = time.strftime("%Y-%m-%d", time.localtime())
    cutoff = args.since or pull_cutoff(today)
    base = args.query or "category:primary in:inbox"
    q = f"{base} after:{cutoff}"

    try:
        listing = gws_json(["gmail", "users", "messages", "list"],
                           {"userId": "me", "q": q, "maxResults": args.cap})
    except Exception as e:
        print(f"[planning-light-sweep] (unavailable: {e}) — nothing surfaced", flush=True)
        return 0

    msgs = listing.get("messages") or []
    if not msgs:
        print(f"[planning-light-sweep] nothing new since {cutoff} (q: {q})")
        return 0

    rows = []
    for m in msgs[:args.cap]:
        try:
            full = gws_json(["gmail", "users", "messages", "get"],
                            {"userId": "me", "id": m["id"], "format": "metadata",
                             "metadataHeaders": ["Subject", "From", "Date"]})
        except Exception:
            continue
        h = {x["name"]: x["value"] for x in full.get("payload", {}).get("headers", [])}
        frm = h.get("From", "")
        if "<" in frm:                       # "Name <email>" → Name
            frm = frm.split("<")[0].strip().strip('"')
        rows.append((_clean(h.get("Date", "")[:16]), _clean(frm), _clean(h.get("Subject", "(no subject)"))))

    print(f"[planning-light-sweep] {len(rows)} new since {cutoff} (metadata only, no bodies):")
    for date, frm, subj in rows:
        print(f"  • {frm:28.28} — {subj}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

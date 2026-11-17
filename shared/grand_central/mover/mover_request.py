#!/usr/bin/env python3
# origin: 92a9739:mover/mover_request.py
"""mover_request.py - build a mover request from a JSON list of actions and (optionally) write it.

  actions.json = [ {"op":"addLabel","label":"Projects/Alpha","ids":["18c..."]}, {"op":"archive","ids":[...]} ]
  python3 mover_request.py actions.json            # dry run (default): validates, prints the summary, writes nothing
  python3 mover_request.py actions.json --write    # writes request.json IN PLACE in the Drive folder

The file is written in place (open r+, truncate, write, flush, fsync) and NEVER temp-then-rename, so Drive keeps
its file id (the script only sees files it created). The file must already exist: the script creates it.
"""
import argparse, datetime, json, os, secrets, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mover_schema as S  # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # shared/grand_central: the one settings loader
import gc_settings  # noqa: E402


def mover_dir():
    """The Drive folder the mover script owns (request.json / result.json live there): setup gc.json mover_dir."""
    return str(gc_settings.gc("mover_dir"))


def default_path():
    return os.path.join(mover_dir(), "request.json")


def build(actions, request_id=None, now=None):
    now = now or datetime.datetime.now(datetime.timezone.utc)
    rid = request_id or "req-%s-%s" % (now.strftime("%Y%m%dT%H%M%SZ"), secrets.token_hex(3))
    return {"request_id": rid, "created_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "actions": actions}


def summary(req):
    lines = ["request_id %s" % req["request_id"]]
    for a in req["actions"]:
        nolabel = {"archive": "(removes INBOX)", "trash": "(adds TRASH; recoverable)", "untrash": "(removes TRASH)"}.get(a["op"], "")
        lines.append("  %-11s %-30s %d ids" % (a["op"], a.get("label", nolabel), len(a["ids"])))
    lines.append("total ids: %d (cap %d)" % (sum(len(a["ids"]) for a in req["actions"]), S.MAX_IDS_PER_REQUEST))
    return "\n".join(lines)


def write_in_place(path, req):
    if not os.path.isfile(path):
        raise FileNotFoundError("%s does not exist: the script creates it (run setup() first); not creating it here" % path)
    data = json.dumps(req, indent=1).encode()
    with open(path, "r+b") as f:
        f.seek(0)
        f.truncate(0)
        f.write(data)
        f.flush()
        os.fsync(f.fileno())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("actions", help="JSON file with the list of actions, or - for stdin")
    ap.add_argument("--path", default=None, help="request.json (default: <gc.json mover_dir>/request.json)")
    ap.add_argument("--request-id")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="(default) print the summary only")
    mode.add_argument("--write", action="store_true", help="really write request.json in place")
    a = ap.parse_args(argv)
    actions = json.load(sys.stdin if a.actions == "-" else open(a.actions, encoding="utf-8"))
    if not isinstance(actions, list):
        print("REFUSED: input must be a JSON list of actions")
        return 2
    req = build(actions, a.request_id)
    errs = S.validate(req)
    if errs:
        print("REFUSED:")
        for e in errs:
            print("  -", e)
        return 2
    print(summary(req))
    if not a.write:
        print("dry run: nothing written (use --write)")
        return 0
    path = a.path or default_path()
    write_in_place(path, req)
    print("written in place: %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())

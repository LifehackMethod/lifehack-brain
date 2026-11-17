#!/usr/bin/env python3
"""coverage.py - the front room's checks on its own work.

THIS FILE HOLDS ONLY THE OUT-OF-PLACE-READ CHECK AND THE INGEST PROOF (plan B2 step 2). The morning-read coverage
(every new email accounted for, nothing flagged dropped, contradictions become questions) is step 4
and is not here yet.

The out-of-place-read check answers: "did any AI window with tools read a transcript file around
the access point (transcripts.py)?" Plan B1: "if there is a sign an AI window read mail it
shouldn't, upgrade to keeping email in the mailroom". A window's own session log records every tool
call it made, so the check reads those logs (Claude Code writes one JSON line per event under
~/.claude/projects/<project>/<session>.jsonl) and looks for any tool call whose input mentions the
protected folders: the transcripts folder or the catalogue folder (the catalogue holds sender and
subject text too). It reports tool name, file and line number, never the text.

Why session logs and not file access times: the backup reads every transcript on purpose and macOS
access times are not reliable, so a time-based signal would cry wolf. Why this is a sign, not a
wall: a call that builds the path at run time from pieces is not caught here; the deny hook (setup/
hooks/, not installed yet) is the first line, this is the second, and the front room's own folder
modes are the third.

  python3 coverage.py out-of-place [--sessions DIR ...] [--front-room DIR] [--json]
Exit 0 = nothing found, 1 = at least one read found, 2 = could not look (nothing to scan).
Python 3.9 compatible.
"""
import argparse
import fnmatch
import glob
import json
import os
import re
import sys

import gc_settings

DEFAULT_SESSIONS = os.path.expanduser("~/.claude/projects")
PROTECTED_SUBDIRS = ("transcripts", "catalogue", "refused")


ATTENTION_LIMIT = 200
ATTENTION_STATUS = ("quarantined", "held")
ATTENTION_REASONS = ("attack", "suspicious", "no_outcome", "discovered", "fetch_failed", "id_mismatch",
                     "scan_unavailable", "scanner_unavailable", "scan_invalid", "deferred_cap",
                     "no_sentinel_proof", "excluded_label", "scan_unjudged", "not_in_read_label", "other")
_ATTN_ID = re.compile(r"[0-9a-f]{6,32}")


def read_held_messages(facts):
    """Validate the mailroom's list of quarantined and held messages (the "held_messages" field of its
    _reader_pass.json facts file, already parsed). Only {message_id, thread_id, status, reason} rows with a hex id, a hex thread id, a known
    status and a closed reason code survive; anything else is dropped and counted; at most 200 rows.
    The front room joins the ids to its own envelope data for sender, subject and date.
    -> (rows, dropped)"""
    if not isinstance(facts, dict) or not isinstance(facts.get("held_messages"), list):
        return [], 0
    rows, dropped = [], 0
    for r in facts["held_messages"]:
        ok = (isinstance(r, dict) and set(r) == {"message_id", "thread_id", "status", "reason"}
              and all(isinstance(r[k], str) for k in r)
              and _ATTN_ID.fullmatch(r["message_id"]) and _ATTN_ID.fullmatch(r["thread_id"])
              and r["status"] in ATTENTION_STATUS and r["reason"] in ATTENTION_REASONS)
        if ok and len(rows) < ATTENTION_LIMIT:
            rows.append(dict(r))
        elif not ok:
            dropped += 1
    return rows, dropped


def ingest_proof(fr=None):
    """For the coverage proof and the status light: how many deliveries the front room refused at
    ingest (each is a message the mailroom's register may call 'delivered'). Counts and ids only.
    -> {"refused_at_ingest": n, "ids": [...], "light": "green"|"red"}"""
    path = os.path.join(fr or front_room(), "refused-at-ingest.jsonl")
    ids = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                ids.append({"message_id": r.get("message_id"), "reason": r.get("reason")})
    except OSError:
        pass
    reasons = []
    try:
        with open(os.path.join(fr or front_room(), "ingest-status.json"), encoding="utf-8") as f:
            reasons = [r for r in json.load(f).get("reasons", []) if isinstance(r, str)]
    except (OSError, ValueError, AttributeError):
        pass
    return {"refused_at_ingest": len(ids), "ids": ids, "reasons": reasons,
            "light": "red" if (ids or reasons) else "green"}


def ingest_proof_line(fr=None):
    p = ingest_proof(fr)
    if p["light"] == "green":
        return "ingest: every delivery was filed"
    return ("ingest: RED (%s); %d delivery(ies) refused after the mailroom delivered them (ids in "
            "refused-at-ingest.jsonl)" % (", ".join(p["reasons"]) or "see status", p["refused_at_ingest"]))


def front_room():
    return gc_settings.front_room_dir()


def protected_paths(fr=None):
    """Absolute protected folders, plus their real paths (symlinks resolved) when different."""
    fr = fr or front_room()
    out = []
    for sub in PROTECTED_SUBDIRS:
        p = os.path.join(fr, sub)
        out.append(p)
        rp = os.path.realpath(p)
        if rp != p:
            out.append(rp)
    return out


def _variants(path):
    """Ways a window could write the same folder: absolute, ~, $HOME, ${HOME}."""
    home = os.path.expanduser("~")
    v = {path}
    if path.startswith(home + "/"):
        rest = path[len(home):]
        v.update({"~" + rest, "$HOME" + rest, "${HOME}" + rest})
    return v


def _glob_hits(pattern, prot):
    """Could this (absolute) pattern name something inside the protected folder? Match the pattern's
    leading components against the folder's components; whatever follows may be anything."""
    pp = [x for x in pattern.split("/") if x]
    qq = [x for x in prot.split("/") if x]
    if len(pp) < len(qq):
        return False
    return all(fnmatch.fnmatchcase(q, p) for p, q in zip(pp, qq))


def _strings(x, out):
    if isinstance(x, str):
        out.append(x)
    elif isinstance(x, dict):
        for v in x.values():
            _strings(v, out)
    elif isinstance(x, list):
        for v in x:
            _strings(v, out)


def _tool_uses(obj, found):
    if isinstance(obj, dict):
        if obj.get("type") == "tool_use" and "input" in obj:
            found.append(obj)
        for v in obj.values():
            _tool_uses(v, found)
    elif isinstance(obj, list):
        for v in obj:
            _tool_uses(v, found)


_TOKEN_SPLIT = re.compile(r"[\s;|&<>()'\"=]+")


def _hit(strings, protected):
    """-> the matching variant name (a short label, never text) or None."""
    variants = set()
    for p in protected:
        variants |= _variants(p)
    home = os.path.expanduser("~")
    for s in strings:
        for v in variants:
            if v in s:
                return "path"
        # globbed paths: expand ~ / $HOME in each token, then see whether it can match inside
        for tok in _TOKEN_SPLIT.split(s):
            if not any(c in tok for c in "*?["):
                continue
            t = tok.replace("${HOME}", home).replace("$HOME", home)
            if t.startswith("~/"):
                t = home + t[1:]
            for p in protected:
                if _glob_hits(t, p):
                    return "glob"
    return None


def find_out_of_place_reads(session_files, fr=None):
    """-> list of {"file", "line", "tool", "how"}. Reads only the tool-call part of each line."""
    protected = protected_paths(fr)
    findings = []
    for path in session_files:
        try:
            f = open(path, encoding="utf-8", errors="replace")
        except OSError:
            continue
        with f:
            for n, line in enumerate(f, 1):
                if not any(sub in line for sub in PROTECTED_SUBDIRS) and "*" not in line \
                        and "?" not in line:
                    continue   # cheap pre-filter before parsing
                try:
                    obj = json.loads(line)
                except ValueError:
                    continue
                uses = []
                _tool_uses(obj, uses)
                for u in uses:
                    strs = []
                    _strings(u.get("input"), strs)
                    how = _hit(strs, protected)
                    if how:
                        findings.append({"file": path, "line": n,
                                         "tool": str(u.get("name", "?"))[:40], "how": how})
    return findings


def session_files(roots):
    out = []
    for r in roots:
        if os.path.isfile(r):
            out.append(r)
        else:
            out += glob.glob(os.path.join(r, "**", "*.jsonl"), recursive=True)
    return sorted(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="out-of-place-read check")
    sub = ap.add_subparsers(dest="cmd", required=True)
    op = sub.add_parser("out-of-place")
    op.add_argument("--sessions", nargs="*", default=[DEFAULT_SESSIONS])
    op.add_argument("--front-room", default=None)
    op.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    files = session_files(a.sessions)
    if not files:
        print("out-of-place-read check: no session logs found to scan (NOT a clean result)")
        return 2
    res = find_out_of_place_reads(files, a.front_room)
    if a.json:
        print(json.dumps({"scanned_files": len(files), "findings": res}, indent=1))
    else:
        print("out-of-place-read check: scanned %d session log(s); %d finding(s)" % (len(files), len(res)))
        for r in res:
            print("  %s line %d tool %s (%s)" % (r["file"], r["line"], r["tool"], r["how"]))
    return 1 if res else 0


if __name__ == "__main__":
    sys.exit(main())

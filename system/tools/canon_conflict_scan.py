#!/usr/bin/env python3
"""
canon_conflict_scan.py — the mechanical half of the canon dedup/conflict check.

Canon is the vetted record. A silent duplicate there is clutter; a silent contradiction is worse
than clutter, because everything downstream is read as though canon were coherent. So before
anything is written into a canon file, this reads canon **content** — not just filenames — and pulls
out every line the incoming item might duplicate or contradict.

It never decides. NEW / DUPLICATE / CONFLICT is a judgment, and it stays with the human, who makes
it **against surfaced evidence instead of from memory**. What this removes is the option of
narrating the check without doing it: a rule that isn't a mechanism is a wish.

Usage:
  canon_conflict_scan.py --canon-root <dir-or-file> --terms "term1,term2,..." [--title "..."] [--json]

`--canon-root` is required and has no default, deliberately. Which canon an item belongs to is a
placement judgment — a project's canon, a subject's canon, the top-level file — and a default here
would be this tool guessing at exactly the thing it refuses to guess at everywhere else. The caller
has already decided where the item is going; it passes that.

## The closed outcome set

    rc 0   SCANNED — one or more canon files were read.
             LIKELY-NEW                      no line matched any term
             POSSIBLE DUPLICATE/CONFLICT     matching lines, listed, for a human to classify
    rc 2   BAD-ARGS — no terms. A conflict scan with no search terms is theatre.
    rc 3   NO-CANON-YET — the root does not exist, or holds no `.md` files. There is nothing to
             conflict with. Distinct from rc 0 on purpose: "I read the canon and found nothing"
             and "there is no canon here" are different facts, and a caller that cannot tell them
             apart will one day report the second as the first. A caller MAY proceed on rc 3; it
             must say which one it got.
    rc 4   CANNOT-READ — the root exists but at least one canon file could not be read. **Fail
             closed: block the write.** Matches the CANNOT-READ convention in `shared/emit`.

⛔ WHY rc 4 EXISTS AT ALL (2026-08-11). This file's contract has always said it "exits non-zero if
canon is unreadable (fail-closed — no scan, no write)". It didn't. The existence check tested the
ROOT path only, while the per-file read sat inside a bare `except Exception: continue`. So a canon
directory whose files could not be read — a cloud mount throwing EDEADLK is the ordinary way that
happens — scanned zero of them, matched nothing, and reported **LIKELY-NEW**. A false clean is the
one outcome this gate exists to prevent, and it was producing one three lines under the sentence
promising it could not.
"""
import argparse
import json
import os
import re
import sys

SCANNED, BAD_ARGS, NO_CANON_YET, CANNOT_READ = 0, 2, 3, 4


def canon_files(root):
    """Every `.md` under the canon root, or the root itself if it is a file. Sorted, so two runs
    over the same canon report in the same order."""
    if os.path.isfile(root):
        return [root]
    out = []
    for dirpath, _dirs, names in os.walk(root):
        out.extend(os.path.join(dirpath, n) for n in names if n.endswith(".md"))
    return sorted(out)


def scan(files, terms, root):
    """(hits, unreadable). A hit is {file, line, term, text}; `file` is relative to the canon root,
    never to the current directory — the caller runs from the repo while canon lives in the person's
    notes folder, so a cwd-relative path is either a wall of `../..` or, worse, plausible and wrong."""
    pats = [(t, re.compile(re.escape(t), re.I)) for t in terms]
    base = root if os.path.isdir(root) else os.path.dirname(root)
    hits, unreadable = [], []
    for path in files:
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
        except Exception as e:                      # a cloud mount throws more than OSError
            unreadable.append((path, "%s: %s" % (e.__class__.__name__, e)))
            continue
        rel = os.path.relpath(path, base) if base else path
        for i, line in enumerate(lines, 1):
            for term, pat in pats:
                if pat.search(line):
                    hits.append({"file": rel, "line": i, "term": term,
                                 "text": line.strip()[:200]})
    return hits, unreadable


def main(argv=None):
    p = argparse.ArgumentParser(
        description="surface canon lines an incoming item might duplicate or contradict")
    p.add_argument("--canon-root", required=True, help="canon dir, or a single canon file, to scan")
    p.add_argument("--terms", required=True, help="comma-separated key terms from the incoming item")
    p.add_argument("--title", default="", help="the incoming item's title, for the report header")
    p.add_argument("--json", action="store_true", help="emit JSON instead of a text report")
    try:
        a = p.parse_args(sys.argv[1:] if argv is None else argv)
    except SystemExit:
        return BAD_ARGS

    terms = [t.strip() for t in a.terms.split(",") if t.strip()]
    if not terms:
        print("BAD-ARGS: no --terms given — a conflict scan with no search terms is theatre.",
              file=sys.stderr)
        return BAD_ARGS

    def emit(status, verdict, hits=None, files=0, unreadable=None):
        hits, unreadable = hits or [], unreadable or []
        if a.json:
            print(json.dumps({"status": status, "title": a.title, "canon_root": a.canon_root,
                              "terms": terms, "files_scanned": files,
                              "matched_files": sorted({h["file"] for h in hits}),
                              "matched_terms": sorted({h["term"] for h in hits}),
                              "unreadable": [{"file": f, "why": w} for f, w in unreadable],
                              "hits": hits, "verdict": verdict}, indent=2))
            return
        print("=== CANON CONFLICT / DEDUP SCAN ===")
        if a.title:
            print("incoming : %s" % a.title)
        print("canon    : %s  (%d file(s) read)" % (a.canon_root, files))
        print("terms    : %s" % ", ".join(terms))
        print("VERDICT  : %s" % verdict)
        for f, w in unreadable:
            print("  ⛔ could not read %s — %s" % (f, w))
        if hits:
            print("\ncandidate canon lines — read these and classify NEW / DUPLICATE / CONFLICT:")
            for h in hits:
                print("  %s:%d  [%s]  %s" % (h["file"], h["line"], h["term"], h["text"]))

    if not os.path.exists(a.canon_root):
        emit("NO-CANON-YET",
             "NO-CANON-YET — '%s' does not exist. Nothing has been written there, so there is "
             "nothing to duplicate or contradict. This is NOT the same as a clean scan; say which "
             "one you got." % a.canon_root)
        return NO_CANON_YET

    files = canon_files(a.canon_root)
    if not files:
        emit("NO-CANON-YET",
             "NO-CANON-YET — '%s' exists but holds no canon files. Nothing was read, so nothing "
             "was checked." % a.canon_root)
        return NO_CANON_YET

    hits, unreadable = scan(files, terms, a.canon_root)

    # ⛔ FAIL CLOSED, AND BEFORE ANY VERDICT. One unreadable file means the scan is incomplete, and
    # an incomplete scan cannot certify NEW. Reporting the readable subset with a clean verdict is
    # exactly the false green this gate exists to prevent.
    if unreadable:
        emit("CANNOT-READ",
             "CANNOT-READ — %d of %d canon file(s) could not be read, so this scan is incomplete "
             "and certifies nothing. BLOCK the write until canon is readable."
             % (len(unreadable), len(files)),
             hits, len(files) - len(unreadable), unreadable)
        return CANNOT_READ

    if hits:
        verdict = ("POSSIBLE DUPLICATE/CONFLICT — %d matching line(s) in %d canon file(s). Read "
                   "them and classify NEW / DUPLICATE / CONFLICT. Existing canon wins by default."
                   % (len(hits), len({h["file"] for h in hits})))
    else:
        verdict = ("LIKELY-NEW — %d canon file(s) read, no line matched any term. Still eyeball it "
                   "before writing." % len(files))
    emit("SCANNED", verdict, hits, len(files))
    return SCANNED


if __name__ == "__main__":
    sys.exit(main())

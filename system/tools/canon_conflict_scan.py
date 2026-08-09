#!/usr/bin/env python3
"""
canon_conflict_scan.py — the DETERMINISTIC half of /save Step 4.6 (canon conflict/dedup).

Council verdict (lifehack-architecture, 2026-07-09): "a rule that isn't a hook is a wish."
The Step-4.6 canon scan was prose an LLM could skip. This makes the SURFACING mechanical:
given a target canon area + the key terms of an incoming item, it reads canon CONTENT and
pulls every candidate line the item might duplicate or contradict — so the check cannot be
narrated-without-doing. The NEW/DUPLICATE/CONFLICT *judgment* stays with the human/LLM, but
it is made against surfaced evidence, never from memory.

Contract: /save Step 4.6 MUST run this before any canon write and put its output in the
confirm panel. Exits non-zero if the canon root is unreadable (fail-closed: no scan, no write).

Usage:
  canon_conflict_scan.py --canon-root <dir-or-file> --terms "term1,term2,..." [--title "..."] [--json]

`--canon-root` = the folder/project canon dir (e.g. knowledge/<subject>/canon) or a single canon.md.
Ladder-aware: pass the deepest canon dir; it scans that dir recursively.
"""
import argparse, json, os, re, sys


def _canon_files(root):
    if os.path.isfile(root):
        return [root]
    out = []
    for dp, _, fns in os.walk(root):
        for fn in fns:
            if fn.endswith(".md"):
                out.append(os.path.join(dp, fn))
    return sorted(out)


def main():
    p = argparse.ArgumentParser(description="Deterministic canon conflict/dedup surfacing for /save Step 4.6")
    p.add_argument("--canon-root", required=True, help="canon dir or canon.md to scan")
    p.add_argument("--terms", required=True, help="comma-separated key terms from the incoming item")
    p.add_argument("--title", default="", help="incoming item title (for the report header)")
    p.add_argument("--json", action="store_true", help="emit JSON instead of a text report")
    a = p.parse_args()

    if not os.path.exists(a.canon_root):
        # fail-closed: if we cannot read canon, we cannot certify NEW — block.
        sys.exit(f"FAIL: canon root '{a.canon_root}' does not exist — cannot certify no-conflict; BLOCK the write")

    terms = [t.strip() for t in a.terms.split(",") if t.strip()]
    if not terms:
        sys.exit("FAIL: no --terms given — a conflict scan with no search terms is theater")

    files = _canon_files(a.canon_root)
    pats = [(t, re.compile(re.escape(t), re.I)) for t in terms]
    hits = []  # {file, line_no, term, text}
    for fp in files:
        try:
            with open(fp, errors="replace") as fh:
                for i, line in enumerate(fh, 1):
                    for t, pat in pats:
                        if pat.search(line):
                            hits.append({"file": os.path.relpath(fp), "line": i,
                                         "term": t, "text": line.strip()[:200]})
        except Exception:
            continue

    matched_files = sorted({h["file"] for h in hits})
    hit_terms = sorted({h["term"] for h in hits})
    # deterministic hint only — the human/LLM makes the real call against these lines
    if not hits:
        verdict_hint = "LIKELY-NEW (no canon line matched any term — still eyeball before writing)"
    else:
        verdict_hint = f"POSSIBLE DUPLICATE/CONFLICT — {len(hits)} matching line(s) in {len(matched_files)} canon file(s); READ them and classify NEW/DUPLICATE/CONFLICT"

    if a.json:
        print(json.dumps({"title": a.title, "canon_root": a.canon_root, "terms": terms,
                          "files_scanned": len(files), "matched_files": matched_files,
                          "matched_terms": hit_terms, "hits": hits,
                          "verdict_hint": verdict_hint}, indent=2))
        return

    print(f"=== CANON CONFLICT/DEDUP SCAN ===")
    if a.title:
        print(f"incoming : {a.title}")
    print(f"canon    : {a.canon_root}  ({len(files)} file(s) scanned)")
    print(f"terms    : {', '.join(terms)}")
    print(f"VERDICT HINT: {verdict_hint}")
    if hits:
        print("\ncandidate canon lines to check:")
        for h in hits:
            print(f"  {h['file']}:{h['line']}  [{h['term']}]  {h['text']}")
    else:
        print("(no matching canon lines)")


if __name__ == "__main__":
    main()

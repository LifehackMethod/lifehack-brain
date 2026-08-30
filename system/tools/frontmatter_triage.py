#!/usr/bin/env python3
"""
frontmatter_triage.py — ONE-TIME / occasional frontmatter-backlog reconciler (NOT a live guard).

MECHANICAL COLLECTOR only. It finds every frontmatter-flagged managed .md and emits a READ-ONLY
report of {path, present_fields, missing_fields, forbidden_fields, frontmatter_header} so an
LLM-assisted triage (sonnet subagents, run SEPARATELY over this report) can judge each one:
  FALSE_ALARM (valid dialect — e.g. `type:` used instead of `record_type:`) · REAL_GAP (genuinely
  missing — propose a value) · UNSURE (→ human).

This script NEVER calls an LLM and NEVER edits a file. It pairs with validate_frontmatter.py and
reuses its exact skip/flag rules (so what it collects == what the live nudge would flag).
organism-audit defect d.c (2026-07-21).
"""
import os, sys, json, argparse
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from validate_frontmatter import validate_file, REQUIRED_FIELDS, FORBIDDEN_FIELDS


def extract_frontmatter(path):
    try:
        c = open(path, encoding="utf-8", errors="replace").read()
    except Exception:
        return None
    if not c.startswith("---"):
        return None
    end = c.find("---", 3)
    return (c[3:].strip() if end == -1 else c[3:end].strip())


def field_names(fm):
    """Top-level YAML-ish keys present in the frontmatter block (best-effort, no yaml dep)."""
    names = set()
    for line in fm.splitlines():
        s = line.rstrip()
        # top-level key = starts at col 0, has a colon, is not a comment or a list item
        if s and not s.startswith((" ", "\t", "#", "-")) and ":" in s:
            names.add(s.split(":", 1)[0].strip())
    return names


def analyze(path):
    ok, _ = validate_file(path)
    if ok:
        return None  # valid or skipped by the checker's own rules (incl. quarantine/archive)
    fm = extract_frontmatter(path)
    if fm is None:
        return None
    present = sorted(field_names(fm))
    missing = sorted(f for f in REQUIRED_FIELDS if f not in present)
    forbidden = sorted(f for f in FORBIDDEN_FIELDS if f in present)
    return {
        "path": path,
        "present_fields": present,
        "missing_fields": missing,
        "forbidden_fields": forbidden,
        "frontmatter": fm,
    }


def walk(roots, limit=None):
    out = []
    for root in roots:
        for dp, _dn, fn in os.walk(root):
            if any(s in dp for s in ("/.git", "/node_modules", "/inventory",
                                     "/quarantine", "/_archive", "/archive")):
                continue
            for f in fn:
                if not f.endswith(".md"):
                    continue
                r = analyze(os.path.join(dp, f))
                if r:
                    out.append(r)
                    if limit and len(out) >= limit:
                        return out
    return out


def _drive_root() -> str:
    """Resolve the Drive spine root instead of typing it.

    THE MOUNT DIRECTORY NAME IS A PERSONAL IDENTIFIER - Google Drive names its mount
    `GoogleDrive-<account address>`, so a literal Drive path here writes a real email
    address into the repo (the shipping lane's `path-drive-cloudstorage` /
    `path-drive-account` / `email-primary` refuse rules all fire on that shape). Env
    var first - this repo's own `CLAUDEOPS_DRIVE` convention (emit_finding.py,
    fault_ledger.py, huddle.py) - then glob discovery over the mount, which replaces
    that convention's hardcoded fallback (`migration-audit/00-FINDINGS.md` F2.1 records
    the literal fallback as its non-compliant half). Bottoming out at a NON-personal
    literal is the accepted shape. Evaluated at import time exactly like the literal it
    replaces: on a machine without the mount it yields a path that does not exist, which
    is the old behaviour, not an exception.
    """
    import glob
    import os
    env = os.environ.get("CLAUDEOPS_DRIVE")
    if env:
        return env
    mounts = os.path.join(os.path.expanduser("~"), "Library", "CloudStorage")
    hits = sorted(glob.glob(os.path.join(mounts, "GoogleDrive-*", "My Drive", "_ClaudeOps")))
    return hits[0] if hits else os.path.join(
        mounts, "GoogleDrive-UNRESOLVED", "My Drive", "_ClaudeOps")
def main():
    CLONE = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    DRIVE = _drive_root()

    ap = argparse.ArgumentParser(description="Collect frontmatter-flagged managed .md files (read-only).")
    ap.add_argument("--scope", choices=["clone", "drive", "all"], default="all")
    ap.add_argument("--roots", nargs="*", help="override: explicit dirs to scan")
    ap.add_argument("--out", help="write the full JSON report here (for the LLM triage to read)")
    ap.add_argument("--limit", type=int, help="cap the number of flagged files (sampling)")
    args = ap.parse_args()

    if args.roots:
        roots = args.roots
    elif args.scope == "clone":
        roots = [f"{CLONE}/system", f"{CLONE}/desks"]
    elif args.scope == "drive":
        roots = [DRIVE]
    else:
        roots = [f"{CLONE}/system", f"{CLONE}/desks", DRIVE]

    flagged = walk(roots, args.limit)
    report = {"count": len(flagged), "roots": roots, "records": flagged}

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, ensure_ascii=False)

    # aggregate summary only to stdout (context-hygiene: never dump all records)
    miss = Counter()
    for r in flagged:
        for m in r["missing_fields"]:
            miss[m] += 1
        for m in r["forbidden_fields"]:
            miss["FORBIDDEN:" + m] += 1
    print(f"flagged files: {len(flagged)}   roots={len(roots)}")
    for k, c in miss.most_common():
        print(f"  missing/{k}: {c}")
    if args.out:
        print(f"report -> {args.out}")


if __name__ == "__main__":
    main()

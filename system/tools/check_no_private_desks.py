#!/usr/bin/env python3
"""check_no_private_desks.py — the shared plugin must not name the maintainer's personal desks or private repo.

WHY (3b.7 B, 2026-11-01; Enver: the plugin "should not name my private repo or my desk"): the Phase 5 privacy
sweep found the maintainer's desk jobs, desk names and private repo handle in the PUBLIC plugin (jobs table, job
names, register, toolbox, workflow comments). Item B moved that material to the maintainer's personal code folder
(<personal-code>/jobs.md, job-names.txt, register.jsonl, desks/<desk>/tools/). This check keeps it out.

THE NAMES ARE NOT IN THIS FILE. A list of the names would itself name them, so the check carries only salted
SHA-256 prefixes (HASHES below) and compares every word of every tracked file against them. Matches are printed
REDACTED (path, line, rule) — a public CI log must not become the leak. To add a name: put its hash prefix here
(`--hash WORD` prints it).

RULES
  R1 private repo handle — ZERO tolerance, every tracked file.
  R2 personal desk name — ZERO tolerance on the ZERO_SURFACES (the shared job table, job names, register, toolbox,
     the scheduler entry points, the register tools, the wiring files, the workflows, job-sim, this check).
  R3 personal desk name — everywhere else a RATCHET: a file may not hold more mentions than its line in
     system/tools/private-desk-baseline.txt says (a file not listed: 0). The baseline only shrinks; it records
     the older architecture docs, SOPs and archive copies that still mention a desk and are cleaned outside item B.
     `--write-baseline` rewrites it from the tree (use it only to SHRINK it; a grown count is a new leak).
  R4 the product's own public names `cal` and `sentinel` are fine as words (the planning skill and the security
     agent are shipped product), but not as personal desk MATERIAL in the job and register files (R4_SURFACES:
     the shared job table, job names, register, toolbox): no desks/<that name>/ path and no <that name>-* job row.

Extra names for a test: env LIFEHACK_PRIVATE_DESK_NAMES="a,b" adds plain words to R2/R3 (never committed).

USAGE
    python3 system/tools/check_no_private_desks.py               # check the repo this file lives in
    python3 system/tools/check_no_private_desks.py --root DIR    # check another checkout (a test's temp copy)
    python3 system/tools/check_no_private_desks.py --write-baseline
    python3 system/tools/check_no_private_desks.py --hash WORD
EXIT  0 clean · 1 flagged · 2 cannot evaluate (not a git checkout, unreadable baseline).
"""
import argparse
import fnmatch
import hashlib
import os
import re
import subprocess
import sys

SALT = "lifehack-private-desk-v1:"
HANDLE_HASHES = {"cc0f042aa2a67327c053e6e9"}
DESK_HASHES = {"4e4472bae3bb215ca666ea0d", "ca3aefc66ed62620a24658f1", "632d4888d0956aef794d6f8a",
               "bbf39a91270403330adbf70e", "6712bfa94cfd0c570ca9e6c2", "b432484358fd6929ce8b7af0",
               "82292908676799ed5ff9423a"}
BASELINE_REL = "system/tools/private-desk-baseline.txt"
ZERO_SURFACES = [
    "system/jobs.md", "system/job-names.txt",
    "system/register/register.jsonl", "system/register/toolbox.md", "system/register/*.py",
    "shared/jobs_manifest.py", "shared/personal_code_root.py",
    "system/tools/job-run.sh", "system/tools/install-schedulers.sh", "system/tools/pulse.sh",
    "system/tools/pulse-park.sh", "system/tools/health_line.py",
    "system/tools/tests/job-sim.sh", "system/tools/tests/job-sim-*.sh",
    "system/tools/check_no_private_desks.py", "system/tools/tests/test_check_no_private_desks.py", BASELINE_REL,
    "hooks/hooks.json", ".claude/settings.json", ".github/workflows/*.yml",
]
R4_SURFACES = {"system/jobs.md", "system/job-names.txt", "system/register/register.jsonl", "system/register/toolbox.md"}
PUBLIC_DESK_MATERIAL = re.compile(r"desks/(?:cal|sentinel)/|^\s*(?:cal|sentinel)-[a-z0-9-]+\s*\|", re.I | re.M)
WORD = re.compile(r"[A-Za-z0-9]+")


def word_hash(w):
    return hashlib.sha256((SALT + w.lower()).encode("utf-8")).hexdigest()[:24]


def extra_names():
    return {w.strip().lower() for w in os.environ.get("LIFEHACK_PRIVATE_DESK_NAMES", "").split(",") if w.strip()}


class Matcher:
    def __init__(self):
        self.extra = extra_names()
        self.cache = {}

    def kind(self, w):
        lw = w.lower()
        k = self.cache.get(lw)
        if k is None:
            h = word_hash(lw)
            k = "handle" if h in HANDLE_HASHES else ("desk" if (h in DESK_HASHES or lw in self.extra) else "")
            self.cache[lw] = k
        return k


def tracked_files(root):
    r = subprocess.run(["git", "-C", root, "ls-files", "-z"], capture_output=True)
    if r.returncode != 0:
        return None
    return [p for p in r.stdout.decode("utf-8", "replace").split("\0") if p]


def is_zero_surface(rel):
    return any(fnmatch.fnmatchcase(rel, pat) for pat in ZERO_SURFACES)


def scan_file(path, m):
    """-> ([(line_no, kind)], desk_count, public_material_lines)"""
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        return [], 0, []
    if b"\0" in data[:4096]:
        return [], 0, []   # binary
    text = data.decode("utf-8", "replace")
    hits, desk = [], 0
    for i, line in enumerate(text.splitlines(), 1):
        for w in WORD.findall(line):
            k = m.kind(w)
            if k:
                hits.append((i, k))
                if k == "desk":
                    desk += 1
    pub = [text.count("\n", 0, mm.start()) + 1 for mm in PUBLIC_DESK_MATERIAL.finditer(text)]
    return hits, desk, pub


def read_baseline(root):
    p = os.path.join(root, BASELINE_REL)
    base = {}
    if not os.path.exists(p):
        return base
    with open(p, encoding="utf-8") as f:
        for ln in f:
            ln = ln.rstrip("\n")
            if not ln or ln.startswith("#"):
                continue
            n, _, rel = ln.partition("\t")
            base[rel] = int(n)
    return base


def scan(root):
    files = tracked_files(root)
    if files is None:
        return None
    m = Matcher()
    out = {}
    for rel in files:
        full = os.path.join(root, rel)
        if os.path.islink(full) or not os.path.isfile(full):
            continue
        out[rel] = scan_file(full, m)
    return out


def write_baseline(root, res):
    rows = sorted((rel, d) for rel, (_h, d, _p) in res.items() if d and not is_zero_surface(rel))
    p = os.path.join(root, BASELINE_REL)
    with open(p, "w", encoding="utf-8") as f:
        f.write("# private-desk-baseline.txt -- written by system/tools/check_no_private_desks.py --write-baseline.\n"
                "# <count>\\t<path>: how many personal-desk-name words a tracked file may still hold (rule R3, a ratchet).\n"
                "# These are older docs, SOPs and archive copies cleaned outside 3b.7 B. A count may only go DOWN; a file\n"
                "# not listed may hold none. The names themselves are never written here.\n")
        for rel, d in rows:
            f.write("%d\t%s\n" % (d, rel))
    return len(rows), sum(d for _, d in rows)


def main(argv=None):
    ap = argparse.ArgumentParser(description="the plugin names no personal desk and no private repo handle")
    ap.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    ap.add_argument("--write-baseline", action="store_true")
    ap.add_argument("--hash", metavar="WORD")
    a = ap.parse_args(argv)
    if a.hash:
        print(word_hash(a.hash))
        return 0
    root = os.path.abspath(a.root)
    res = scan(root)
    if res is None:
        print("CANNOT EVALUATE: %s is not a git checkout (git ls-files failed)" % root)
        return 2
    if a.write_baseline:
        n, total = write_baseline(root, res)
        print("baseline written: %d file(s), %d mention(s) -> %s" % (n, total, BASELINE_REL))
        return 0
    try:
        base = read_baseline(root)
    except (OSError, ValueError) as e:
        print("CANNOT EVALUATE: unreadable %s (%s)" % (BASELINE_REL, e))
        return 2
    problems, shrunk = [], []
    for rel in sorted(res):
        hits, desk, pub = res[rel]
        zero = is_zero_surface(rel)
        for ln, k in hits:
            if k == "handle":
                problems.append("%s:%d: R1 names the private repo handle [REDACTED]" % (rel, ln))
            elif zero:
                problems.append("%s:%d: R2 names a personal desk [REDACTED] on a zero-tolerance surface" % (rel, ln))
        if rel in R4_SURFACES:
            for ln in pub:
                problems.append("%s:%d: R4 personal desk material (desks/cal|sentinel path or job row) in the job/register files" % (rel, ln))
        if zero:
            continue   # R2 above already covers every mention on a zero-tolerance surface
        if desk > base.get(rel, 0):
            problems.append("%s: R3 holds %d personal-desk-name word(s), baseline allows %d -- a NEW mention; move it to "
                            "<personal-code> or reword it" % (rel, desk, base.get(rel, 0)))
        elif desk < base.get(rel, 0):
            shrunk.append(rel)
    if shrunk:
        print("note: %d file(s) now hold fewer mentions than the baseline; shrink it with --write-baseline" % len(shrunk))
    if problems:
        print("FLAGGED: the shared plugin names private material (%d finding(s)):" % len(problems))
        for p in problems:
            print("  " + p)
        return 1
    print("CLEAN: no private repo handle anywhere; no personal desk on the zero-tolerance surfaces; "
          "no file above its baseline (%d file(s) scanned)" % len(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())

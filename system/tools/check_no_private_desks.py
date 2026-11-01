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

  R5 private repo NAME, R6 notes-root FOLDER name, R7 personal VENDOR names (3b.7 scrub 1, 2026-11-01). Same
     hashing, same redaction. R5/R6/R7 are matched on a whole "run" (a maximal [A-Za-z0-9_-] word, so the leading
     underscore of the notes folder is part of it); R7 also matches a run that STARTS with a vendor name up to a
     - or _ (the vendor's script and job names). ZERO tolerance on the ZERO_SURFACES; everywhere else a shrink-only
     per-file RATCHET in system/tools/private-name-baseline.txt (older docs/SOPs/archive, and the rig fixtures).
     NOT MATCHED, on purpose: longer identifiers that merely CONTAIN the repo name (an env var, the legacy clone
     path, hook file ids, branch labels). Those are the live identifiers of scrub PART 2, which is ON HOLD because
     renaming them changes enforcement-hook behaviour; they are not matched as a whole run, so they neither fail nor
     hide here. The files that still carry R5/R6 mentions in live code (the write-path, gh-account and
     harness-writeback guards, the notes-root finder in the reindex tool, the rig) are listed in the baseline with
     their counts; that baseline IS the explicit allowlist and it can only shrink.

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
# R5 repo name / R6 notes-root folder name / R7 personal vendors: salted hashes of the lower-cased run (R6 keeps its
# leading underscore). The vendor list also holds the hyphen spelling.
REPO_HASHES = {"33feb806d0a6a20c6a91cbc7"}
NOTES_HASHES = {"7c2fbf8b4a4205f347e5949d"}
VENDOR_HASHES = {"11bd2c2cb182d7bcd9355c25", "868738888a316daed0018974", "d35c654f707b8d5ab9422cab"}
NAME_BASELINE_REL = "system/tools/private-name-baseline.txt"
RUN = re.compile(r"[A-Za-z0-9_-]+")
ZERO_SURFACES = [
    "system/jobs.md", "system/job-names.txt",
    "system/register/register.jsonl", "system/register/toolbox.md", "system/register/*.py",
    "shared/jobs_manifest.py", "shared/personal_code_root.py",
    "system/tools/job-run.sh", "system/tools/install-schedulers.sh", "system/tools/pulse.sh",
    "system/tools/pulse-park.sh", "system/tools/health_line.py",
    "system/tools/tests/job-sim.sh", "system/tools/tests/job-sim-*.sh",
    "system/tools/check_no_private_desks.py", "system/tools/tests/test_check_no_private_desks.py", BASELINE_REL,
    "hooks/hooks.json", ".claude/settings.json", ".github/workflows/*.yml",
    "system/tools/vendor-read-allowlist.txt", "system/requirements.txt", "system/tools/private-name-baseline.txt",
]
R4_SURFACES = {"system/jobs.md", "system/job-names.txt", "system/register/register.jsonl", "system/register/toolbox.md"}
PUBLIC_DESK_MATERIAL = re.compile(r"desks/(?:cal|sentinel)/|^\s*(?:cal|sentinel)-[a-z0-9-]+\s*\|", re.I | re.M)
WORD = re.compile(r"[A-Za-z0-9]+")


def word_hash(w):
    return hashlib.sha256((SALT + w.lower()).encode("utf-8")).hexdigest()[:24]


def extra_names(var="LIFEHACK_PRIVATE_DESK_NAMES"):
    return {w.strip().lower() for w in os.environ.get(var, "").split(",") if w.strip()}


class Matcher:
    def __init__(self):
        self.extra = extra_names()
        self.x_repo = extra_names("LIFEHACK_PRIVATE_REPO_NAMES")
        self.x_notes = extra_names("LIFEHACK_PRIVATE_NOTES_NAMES")
        self.x_vendor = extra_names("LIFEHACK_PRIVATE_VENDOR_NAMES")
        self.cache = {}
        self.rcache = {}

    def run_kind(self, run):
        """R5/R6/R7 for one run (see the header): -> "repo" | "notes" | "vendor" | ""."""
        lr = run.lower()
        k = self.rcache.get(lr)
        if k is None:
            k = ""
            if lr.startswith("_") and (word_hash(lr) in NOTES_HASHES or lr in self.x_notes):
                k = "notes"
            elif word_hash(lr) in REPO_HASHES or lr in self.x_repo:
                k = "repo"
            else:
                cuts = [i for i, ch in enumerate(lr) if ch in "-_" and i > 0] + [len(lr)]
                for i in cuts:
                    pre = lr[:i]
                    if word_hash(pre) in VENDOR_HASHES or pre in self.x_vendor:
                        k = "vendor"
                        break
            self.rcache[lr] = k
        return k

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
    """-> ([(line_no, kind)], desk_count, public_material_lines, name_count) -- name_count = R5/R6/R7 mentions"""
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        return [], 0, [], 0
    if b"\0" in data[:4096]:
        return [], 0, [], 0   # binary
    text = data.decode("utf-8", "replace")
    hits, desk, names = [], 0, 0
    for i, line in enumerate(text.splitlines(), 1):
        for r in RUN.findall(line):
            k = m.run_kind(r)
            if k:
                hits.append((i, k))
                names += 1
        for w in WORD.findall(line):
            k = m.kind(w)
            if k:
                hits.append((i, k))
                if k == "desk":
                    desk += 1
    pub = [text.count("\n", 0, mm.start()) + 1 for mm in PUBLIC_DESK_MATERIAL.finditer(text)]
    return hits, desk, pub, names


def read_baseline(root, rel=BASELINE_REL):
    p = os.path.join(root, rel)
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


def write_name_baseline(root, res):
    rows = sorted((rel, n) for rel, (_h, _d, _p, n) in res.items() if n and not is_zero_surface(rel))
    p = os.path.join(root, NAME_BASELINE_REL)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write("# private-name-baseline.txt -- written by system/tools/check_no_private_desks.py --write-baseline.\n"
                "# <count>\\t<path>: how many private repo-name (R5), notes-folder-name (R6) and personal-vendor-name (R7)\n"
                "# mentions a tracked file may still hold (a ratchet). A count may only go DOWN; a file not listed may hold none.\n"
                "# This list IS the explicit allowlist. It holds (1) older docs, SOPs and archive copies, (2) the live-code\n"
                "# files whose rename is scrub PART 2 (ON HOLD, it changes enforcement-hook behaviour): the write-path,\n"
                "# gh-account and harness-writeback guards and their tests, the notes-root finder in the reindex tool, the\n"
                "# rig and its recorded cases. The names themselves are never written here.\n")
        for rel, n in rows:
            f.write("%d\t%s\n" % (n, rel))
    return len(rows), sum(n for _, n in rows)


def write_baseline(root, res):
    rows = sorted((rel, d) for rel, (_h, d, _p, _n) in res.items() if d and not is_zero_surface(rel))
    p = os.path.join(root, BASELINE_REL)
    os.makedirs(os.path.dirname(p), exist_ok=True)
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
        n, total = write_name_baseline(root, res)
        print("baseline written: %d file(s), %d mention(s) -> %s" % (n, total, NAME_BASELINE_REL))
        return 0
    try:
        base = read_baseline(root)
        nbase = read_baseline(root, NAME_BASELINE_REL)
    except (OSError, ValueError) as e:
        print("CANNOT EVALUATE: unreadable baseline (%s)" % e)
        return 2
    problems, shrunk = [], []
    for rel in sorted(res):
        hits, desk, pub, names = res[rel]
        zero = is_zero_surface(rel)
        for ln, k in hits:
            if k == "handle":
                problems.append("%s:%d: R1 names the private repo handle [REDACTED]" % (rel, ln))
            elif k in ("repo", "notes", "vendor"):
                if zero:
                    problems.append("%s:%d: %s names the %s [REDACTED] on a zero-tolerance surface" % (
                        rel, ln, {"repo": "R5", "notes": "R6", "vendor": "R7"}[k],
                        {"repo": "private repo name", "notes": "notes-root folder name", "vendor": "personal vendor"}[k]))
            elif zero:
                problems.append("%s:%d: R2 names a personal desk [REDACTED] on a zero-tolerance surface" % (rel, ln))
        if not zero:
            if names > nbase.get(rel, 0):
                problems.append("%s: R5-R7 holds %d private repo/notes/vendor name mention(s), baseline allows %d -- a NEW "
                                "mention; say 'your personal code folder' / <notes> / the job, or move it to <personal-code>"
                                % (rel, names, nbase.get(rel, 0)))
            elif names < nbase.get(rel, 0):
                shrunk.append(rel)
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
    print("CLEAN: no private repo handle anywhere; no personal desk, repo name, notes-folder name or vendor on the "
          "zero-tolerance surfaces; no file above its baselines (%d file(s) scanned)" % len(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""scrub.py — the shipping lane's tree-walker.  [Shipping Lane · T9.2]

WHAT: reads a coverage source -- either a hand-typed MANIFEST (one repo-relative path per
      line, '#' comments allowed) or, since 2026-08-15, a TREE walk (`--tree PATH`, see
      THE BIG FIX below) -- and for EACH file in that source: copies it into a staging
      tree, then runs TWO ROUNDS on the STAGED COPY ONLY --

        ROUND 1 = REFUSE rules   (blocks: identity + credentials)
        ROUND 2 = REWRITE rules  (fixes and reports: cosmetic substitutions)

      in that order, never interleaved -- then writes a JSON + human report.

THE BIG FIX (2026-08-15): *"a safety check whose coverage is a hand-typed list can only
      ever report 'everything on the list was fine' -- and it reports PASS either way."*
      On the donor lane, two whole directories of real-content fixtures (~202 files) were
      NEVER ONCE run through this pipeline because nothing ever added them to a manifest
      -- hit five separate times. `--tree PATH` (default: the whole clone) derives the
      file set by WALKING THE TREE instead of trusting a document a human has to remember
      to update. `--manifest` is NOT retired: a deliberate, curated push legitimately
      wants a HAND-CHOSEN subset -- `--tree` is for the case this file's own history
      proves needs a different default: an AUDIT sweep whose whole job is catching what
      nobody remembered to list. See `derive_tree_entries()`.

⛔ AND THE FIX'S OWN BUG, REMOVED ON THE WAY IN (2026-08-15). The donor's `--tree`
      enumerated via `git ls-files --cached --others --exclude-standard`, i.e. it asked
      GIT what files exist and honoured `.gitignore`. That hands the scanner a second,
      quieter blind spot in place of the first: **anything `.gitignore` covers is
      invisible to it**, and `.gitignore` is exactly where the dangerous files collect --
      `.bak` editing debris, local settings, the operator's own notes, and (measured in
      THIS repo, 2026-08-15) `migration-audit/08-THIRD-PARTY-INVENTORY.md`, a file whose
      own .gitignore entry records that it named machine paths, a live third-party
      hostname, a locality hint and a map of where every credential is stored. A real
      PII-carrying file was once invisible to both this scanner and an independent grep
      sweep because BOTH silently keyed off the git index: two checks, one blind spot,
      both reporting clean. So `derive_tree_entries()` here walks the FILESYSTEM
      (`canon.walk_tree_files`, the same primitive push_gate.py and judge.py already
      share) and NEVER asks git what exists. Git is still consulted -- but only to
      ANNOTATE each walked file with what git WOULD have said about it, so every run
      prints how many files a git-index walk would have missed. Report only; it can
      never remove a file from the scan.

WHICH RULES. The REFUSE set is composed at startup: the shipped generic rules
(`refuse-rules.json` -- credential shapes, home paths, drive mounts, true for everybody)
PLUS a personal tier compiled by `identity_rules.py` from the terms you keep in your own
notes. No identity file is CANNOT EVALUATE, never a run with the personal tier missing.
The REWRITE set is yours alone and is legitimately empty on a fresh install.

WHY THE ORDER IS LOAD-BEARING: a rewrite rule can destroy the very string a refuse rule
matches on. If REWRITE ran first, a path containing a term you rewrite comes out changed,
and the REFUSE rule written against the ORIGINAL string stops matching -- a SILENT MISS,
the worst class. Refuse always sees the untouched text; rewrite only ever sees what refuse
has already cleared or left as an explicit, reported, unresolved finding.

THE ORIGINAL IS NEVER OPENED FOR WRITING -- HARD. Every path named in the manifest is read
via `shutil.copy2` (opens the source `rb`, the destination `wb`) and never touched again.
All mutation happens on the STAGING COPY.

SUBSTITUTION SEMANTICS (the design decision this file exists to enforce):
  - A rule carrying a "to" field is AUTO-RESOLVABLE -> every occurrence is substituted.
    This applies in BOTH rounds -- the shipped "path-home-unix" rule has a "to" ($HOME),
    so it is substituted like a rewrite even though it lives in the refuse tier.
  - A REFUSE rule with NO "to" cannot be auto-fixed (a name in prose, a Drive path, a
    secret). Every occurrence is reported (file + line + evidence) and the file is marked
    NOT-CLEAN. A file with any unresolved REFUSE hit is NEVER reported as ready, no matter
    what ROUND 2 does to it afterward.
  - A secret rule (tier "1-secret") never carries "to", and neither does any compiled
    identity rule -- confirmed by reading them, not assumed -- so this falls out of the same rule rather than needing
    special-cased code: nothing here ever rewrites a credential. A file that carries one
    should not ship, full stop.
  - Rewrite rules are applied in their declared "order" field, ascending, each substitution
    feeding the next -- mirrors `verify_rules.py`'s own `apply_rewrites` reference exactly,
    so this file's output matches what that verify already proved correct.

THE WARNING TIER IS NON-BLOCKING, AND THAT IS THE WHOLE POINT (2026-08-15). Alongside the
two rounds there is a third, SEPARATE bucket: SHAPE-heuristic findings
(`third-party-name-shape`, `disclosing-fact-pattern`, tier "3-warning" -- both computed in
canon.py, neither ever an entry in `refuse-rules.json`). They hunt what no name list can
enumerate: a third party nobody wrote a rule for, and a fact that identifies with every
name stripped out. A SHAPE match can be a false positive in a way a literal secret cannot,
so a hit here NEVER lands in `unresolved`, NEVER sets a file NOT-CLEAN, NEVER appears in
`summary.not_clean`, and NEVER changes the exit code -- it is counted separately
(`summary.warning_count` / `summary.warning_files`) and printed as
"WARNING (non-blocking)" for a human to glance at and clear. A check that drowns a
reviewer in false blocks gets switched off, which is worse than not having it at all. A
file whose only findings are warnings is CLEAN and exits 0, and `--selftest` proves it.

`forbidden_content.py` (the verdict engine) returns ONE HIT PER RULE, FIRST OCCURRENCE ONLY
(`rx.search`, not `finditer` -- measured: 3 occurrences of a term returned 1 hit). This file
therefore does its OWN `re.finditer` pass for every rule, for both the report and the
substitutions, and calls `forbidden_content.py` ONLY as the verdict authority -- its exit
code is used as a cross-check against this file's own scan; its hit list is never read.

Binary / non-UTF-8 staged files are detected before any rule is applied to them (a decode
attempt, not a byte sniff) and are always flagged NOT-CLEAN -- never crashed on, never
silently passed as clean. KNOWN LANDMINE (found, not fixed -- see the run report this
script prints): `forbidden_content.py`'s own `_load()` only catches `OSError`; a raw call
against a non-UTF-8 file raises an uncaught `UnicodeDecodeError` and Python's default
exit code for an uncaught exception is 1 -- INDISTINGUISHABLE, at the exit-code layer
alone, from a genuine REFUSED verdict. This file never calls `forbidden_content.py` against
a file it has not already confirmed is UTF-8 text, which sidesteps the landmine here, but
the landmine still exists in the engine and would bite any OTHER caller that skips that
precaution.

FAIL LOUD WHEN THE SUBJECT IS ABSENT OR AMBIGUOUS (house rule T9.11b). A missing identity
file, an unreadable path inside the walk, a `--tree` target that resolves outside the
clone, a walk that yields zero files -- every one of them exits NON-ZERO with a named
reason. None of them is ever allowed to come out the other end as a quiet "CLEAN".

HARD CONSTRAINTS
  A. Read-only on every original, always.
  B. Every manifest/tree entry must resolve (realpath, following "..") inside this clone
     (the directory two levels above this file). If ANY entry resolves outside, the whole
     run exits 2 having read NOTHING -- not even the entries that were fine. Existence /
     readability of each (in-bounds) entry is checked in the SAME pre-flight pass, before
     any file's contents are copied or read, for the same fail-closed reason. A `--tree`
     PATH that itself resolves outside the clone is refused before any walk happens.
  C. `forbidden_content.py` is the verdict authority (exit code only); this file does its
     own `re.finditer` for the report and the substitutions.
  D. Substitution semantics as above.
  E. Exit codes never collapse 1 and 2 (see below). An empty or unreadable manifest, or a
     `--tree` that yields zero files, is ALWAYS 2, never a vacuous 0.
  F. `--selftest` builds a temp fixture tree under THIS directory, proves the catch and the
     no-false-positive side, and leaves no residue (repo `git status` is unchanged).
  G. Python 3.9 target -- no bare `X | None` annotations.
  H. One file, pure stdlib (third-party PYTHON packages -- this module has always shelled
     out to `git` itself, e.g. `--selftest`'s own git-status check). `forbidden_content.py`
     and `move_aside.py` are invoked as sibling-part subprocesses -- required, not
     optional, once their logic is used.
  I. Binary/non-UTF-8 files are handled explicitly, per above.
  J. `--tree` coverage NEVER comes from git. See THE BIG FIX'S OWN BUG above.

USAGE
  scrub.py --manifest PATH [--staging DIR] [--report-json PATH] [--report-txt PATH]
           [--json] [--identity PATH] [--refuse-rules PATH] [--rewrite-rules PATH]
  scrub.py --tree [PATH]   [same options]
  scrub.py --selftest

  --manifest and --tree are mutually exclusive; exactly one is required. --tree with no
  PATH walks the whole clone; --tree PATH scopes the walk to one subtree.

  --staging, if omitted, defaults to a FRESH directory under the OS temp root (outside this
  git clone) -- so a plain run touches nothing in the repo and `git status --porcelain`
  is identical before and after by construction, not by discipline.

EXIT CODES (the parts-library house contract)
  0  CLEAN            -- every staged file is clean: no unresolved REFUSE hit, nothing
                          binary/unreadable
  1  REFUSED          -- at least one staged file is NOT-CLEAN (an unresolved REFUSE hit,
                          a secret, or a binary/undecodable file)
  2  CANNOT EVALUATE  -- missing/unreadable manifest, missing rule files, NO IDENTITY FILE,
                          a manifest entry (or --tree target) resolving outside the clone,
                          an unreadable file inside a walk, an empty manifest, or a --tree
                          walk that yields zero files. Fail closed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import canon  # noqa: E402 -- sibling module, same directory, imported after sys.path fix


def _ensure_writable(path: str) -> None:
    """Add the owner write bit to a STAGED copy so it can be rewritten in place.

    move_aside.py preserves the source file's mode, and this house ships hooks read-only
    (`pm_flag.sh` is 555). Without this the first hook in a manifest raises PermissionError
    from open(...,"w") -- a TRACEBACK at exit 1, which the caller cannot tell apart from a
    real REFUSAL. Only ever called on a path inside the staging tree; the original is never
    opened for writing anywhere in this module, so no source mode is touched.
    """
    try:
        mode = os.stat(path).st_mode
        if not mode & 0o200:
            os.chmod(path, mode | 0o200)
    except OSError:
        pass  # let the subsequent open() raise the real, specific error


REPO_ROOT = os.path.realpath(os.path.join(HERE, "..", ".."))
PARTS = os.path.realpath(os.path.join(HERE, "..", "parts"))
FORBIDDEN_CONTENT = os.path.join(PARTS, "forbidden_content.py")
MOVE_ASIDE = os.path.join(PARTS, "move_aside.py")
# ⭐ THESE TWO ARE REASSIGNED AT STARTUP, AND THAT IS THE DESIGN.
#
# The lane this came from carried its author's identity as literals inside a committed
# `refuse-rules.json` — his name, his handle, his address, his folder names. That works for
# exactly one person; for anyone else the lane scans a stranger's files for a stranger's
# name and reports CLEAN. So `refuse-rules.json` in this repo now holds ONLY what is true
# for everybody (credential shapes, home paths, drive mounts), and the terms that identify
# the person running it are compiled from THEIR file, outside the repo, by
# `identity_rules.py`.
#
# `main()` and `selftest()` compose both tiers into real files under the run's working
# directory and rebind these two globals to them, so every function below keeps taking a
# rule PATH exactly as it always did — and the receipt keeps pinning that file's sha, which
# now covers the personal tier too.
REFUSE_RULES = os.path.join(HERE, "refuse-rules.json")     # rebound in main()/selftest()
REWRITE_RULES = None                                       # bound in main()/selftest()

CLEAN, REFUSED, CANNOT_EVALUATE = 0, 1, 2


class CannotEvaluate(Exception):
    """Something could not be evaluated -- always maps to exit 2, fail closed."""


# --------------------------------------------------------------------- manifest / paths

def parse_manifest(path):
    if not path or not os.path.isfile(path):
        raise CannotEvaluate("manifest not found: {!r}".format(path))
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw_lines = fh.read().splitlines()
    except OSError as e:
        raise CannotEvaluate("cannot read manifest {!r}: {}".format(path, e))
    except UnicodeDecodeError as e:
        raise CannotEvaluate("manifest {!r} is not valid UTF-8: {}".format(path, e))

    entries = []
    for line in raw_lines:
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        entries.append(s)

    if not entries:
        raise CannotEvaluate(
            "manifest {!r} has no entries after removing blank lines / comments -- fail "
            "closed: an empty manifest must NEVER report all-clear".format(path))
    return entries


def resolve_entries(raw_entries):
    """Resolve every entry (realpath, following '..') and require ALL of them to land
    inside REPO_ROOT. If even one is out of bounds, raise before returning anything --
    the caller must read NOTHING, including the entries that were fine."""
    violations = []
    resolved = []
    for raw in raw_entries:
        target = raw if os.path.isabs(raw) else os.path.join(REPO_ROOT, raw)
        real = os.path.realpath(target)
        if real == REPO_ROOT or real.startswith(REPO_ROOT + os.sep):
            resolved.append((raw, real))
        else:
            violations.append((raw, real))

    if violations:
        detail = "; ".join("{!r} -> {!r}".format(r, a) for r, a in violations)
        raise CannotEvaluate(
            "{} manifest entry(ies) resolve OUTSIDE {!r}: {} -- fail closed, NOTHING was "
            "read (the clone has git and an undo path; wherever these point does not)"
            .format(len(violations), REPO_ROOT, detail))
    return resolved


def validate_existence(resolved):
    """Stat-only pass (no content read) over every already-in-bounds entry."""
    problems = []
    for raw, real in resolved:
        if not os.path.isfile(real):
            problems.append((raw, real, "missing or not a regular file"))
        elif not os.access(real, os.R_OK):
            problems.append((raw, real, "not readable"))
    if problems:
        detail = "; ".join("{!r} ({!r}): {}".format(r, a, why) for r, a, why in problems)
        raise CannotEvaluate(
            "{} manifest entry(ies) cannot be evaluated: {} -- fail closed, nothing was "
            "copied".format(len(problems), detail))


# ---------------------------------------------------------------------- tree derivation
#
# THE BIG FIX (2026-08-15) -- coverage derived from the TREE, not from a document a human
# has to remember to update. And THE BIG FIX'S OWN BUG, removed on the way in: the walk is
# a FILESYSTEM walk, never `git ls-files`. Both halves are argued in the module docstring;
# the one-line version is that a hand-typed manifest misses what nobody listed, and a
# git-index walk misses what `.gitignore` covers -- which is precisely where the files
# worth catching collect.

# The ONLY directory this walk refuses to descend. `.git` is git's own object store: packed
# binary that is not repo CONTENT, cannot leak anything a working-tree file does not already
# carry, and would bury every real finding under thousands of "binary, NOT-CLEAN" lines.
# Every other exclusion in this function is per-file and individually logged with a reason;
# this one is named here so the single blanket skip is impossible to miss on review.
TREE_SKIP_DIRS = (".git",)


def _git_visibility(rel_paths):
    """ANNOTATION ONLY -- what git WOULD have said about each already-walked file.

    This exists to keep THE BIG FIX'S OWN BUG visible forever: every run prints how many
    of the files it scanned a `git ls-files`-based walk would have skipped. It is a pure
    reporting function -- it takes the walked set and returns labels for it. It can never
    add a path and, far more importantly, IT CAN NEVER REMOVE ONE. If git cannot answer,
    the run is not affected at all: the annotation degrades to a stated note, because
    coverage here does not depend on git and must never be made to.

    Returns (labels_by_path_or_None, note_or_None).
    """
    def _ls(*args):
        proc = subprocess.run(["git", "-C", REPO_ROOT, "ls-files", "-z"] + list(args),
                              capture_output=True, text=True)
        if proc.returncode != 0:
            raise OSError(proc.stderr.strip()[:200] or "git ls-files exit {}".format(
                proc.returncode))
        return set(p for p in proc.stdout.split("\0") if p)

    try:
        tracked = _ls("--cached")
        untracked_visible = _ls("--others", "--exclude-standard")
    except (OSError, ValueError) as e:
        return None, ("git could not be consulted ({}) -- the SCAN IS UNAFFECTED (this "
                      "walk never asks git what exists); only the "
                      "would-git-have-seen-it annotation is missing".format(e))

    labels = {}
    for p in rel_paths:
        if p in tracked:
            labels[p] = "tracked"
        elif p in untracked_visible:
            labels[p] = "untracked-visible"
        else:
            labels[p] = "INVISIBLE-TO-GIT"
    return labels, None


def derive_tree_entries(root_arg):
    """Walk `root_arg` (repo-relative or absolute; must resolve inside REPO_ROOT, the same
    containment rule a manifest entry obeys) and return (entries, excluded, git_note):

      entries  -- sorted repo-relative paths of every REGULAR FILE ON DISK under root_arg,
                  tracked or not, gitignored or not. Derived by `canon.walk_tree_files`,
                  an `os.walk` that does not follow symlinked directories -- the same
                  primitive push_gate.py and judge.py already share, so there is one
                  walker in this lane and not three.
      excluded -- sorted [{"path", "reason"}, ...]. NOTHING is dropped silently: the only
                  reasons are `git-internal` (inside `.git/`, see TREE_SKIP_DIRS) and
                  `not-a-regular-file` (a socket/fifo/dangling symlink -- nothing to scan).
      git_note -- an annotation-layer note, or None.

    FAILS CLOSED, LOUDLY, on every ambiguity (house rule T9.11b): a target outside the
    clone, a target that is not a directory, an UNREADABLE file inside the walk (a file
    the scanner cannot open is a coverage hole, and a coverage hole must never be
    reported as coverage), and a symlinked directory pointing OUTSIDE the clone (its
    contents are neither walked nor in bounds -- ambiguous, so it stops the run rather
    than quietly shrinking the scan)."""
    target = root_arg if os.path.isabs(root_arg) else os.path.join(REPO_ROOT, root_arg)
    real = os.path.realpath(target)
    if not (real == REPO_ROOT or real.startswith(REPO_ROOT + os.sep)):
        raise CannotEvaluate(
            "--tree {!r} resolves OUTSIDE {!r} -> {!r} -- fail closed, nothing was "
            "walked".format(root_arg, REPO_ROOT, real))
    if not os.path.isdir(real):
        raise CannotEvaluate(
            "--tree target is not a directory: {!r} -> {!r}".format(root_arg, real))

    walked, symlinked_dirs = canon.walk_tree_files(real)

    # A symlinked directory is never descended (canon.walk_tree_files refuses to). One
    # pointing back INSIDE the clone is harmless -- its real files are walked at their own
    # location, so nothing is missed. One pointing OUTSIDE is both a coverage hole and an
    # out-of-bounds path, and gets the same fail-closed treatment as an out-of-bounds
    # manifest entry rather than being logged and shrugged off.
    escaping = []
    for d in symlinked_dirs:
        dest = os.path.realpath(os.path.join(real, d))
        if not (dest == REPO_ROOT or dest.startswith(REPO_ROOT + os.sep)):
            escaping.append((d, dest))
    if escaping:
        detail = "; ".join("{!r} -> {!r}".format(d, t) for d, t in escaping)
        raise CannotEvaluate(
            "{} symlinked director(ies) under the walk point OUTSIDE {!r}: {} -- fail "
            "closed: their contents are neither walked nor in bounds, and a scan that "
            "cannot see them cannot claim to cover this tree".format(
                len(escaping), REPO_ROOT, detail))

    scannable, excluded, unreadable = [], [], []
    for _rel_to_walk_root, abspath in walked:
        rel = os.path.relpath(abspath, REPO_ROOT).replace(os.sep, "/")
        if any(part in TREE_SKIP_DIRS for part in rel.split("/")):
            excluded.append({"path": rel, "reason": "git-internal"})
            continue
        if not os.path.isfile(abspath):
            # socket, fifo, or a dangling symlink -- no text to scan, and os.path.isfile
            # follows links, so a symlink to a real in-bounds file still lands here as a
            # scannable entry (copy2 follows it, exactly as with a manifest entry).
            excluded.append({"path": rel, "reason": "not-a-regular-file"})
            continue
        if not os.access(abspath, os.R_OK):
            unreadable.append(rel)
            continue
        scannable.append(rel)

    if unreadable:
        raise CannotEvaluate(
            "{} file(s) under the walk cannot be READ: {} -- fail closed: an unopenable "
            "file is an unscanned file, and an unscanned file must never be counted as "
            "clean".format(len(unreadable), "; ".join(repr(p) for p in unreadable[:20])))

    scannable.sort()
    labels, git_note = _git_visibility(scannable)
    return (scannable, sorted(excluded, key=lambda e: e["path"]), labels, git_note)


# --------------------------------------------------------------------------- rule files

def load_rules(path, what, allow_empty=False):
    if not path or not os.path.isfile(path):
        raise CannotEvaluate("{} not found: {!r}".format(what, path))
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as e:
        raise CannotEvaluate("cannot read {} {!r}: {}".format(what, path, e))
    if not isinstance(data, list):
        raise CannotEvaluate("{} must be a JSON list".format(what))
    if not data and not allow_empty:
        raise CannotEvaluate("{} must be a non-empty JSON list".format(what))
    return data


def bind_rule_files(refuse=None, rewrite=None, identity=None, workdir=None):
    """Decide which rule files this run uses, and rebind the two module globals to them.

    Returns a one-line description for the report. Raises CannotEvaluate when there is no
    identity to compile — FAIL CLOSED, deliberately: a run with an empty personal tier
    reports a file carrying your own name as clean, which is the exact disaster this lane
    exists to prevent."""
    global REFUSE_RULES, REWRITE_RULES
    if refuse:
        REFUSE_RULES = refuse
        REWRITE_RULES = rewrite
        return "refuse rules: {} (given)".format(refuse)
    sys.path.insert(0, HERE)
    try:
        import identity_rules                                # noqa: E402
    except ImportError as e:
        raise CannotEvaluate("identity_rules.py is not importable: {}".format(e))
    wd = workdir or tempfile.mkdtemp(prefix="scrub-rules-")
    try:
        rp, wp, ip, n = identity_rules.effective_rule_files(wd, identity_file=identity)
    except identity_rules.IdentityMissing as e:
        raise CannotEvaluate(str(e))
    REFUSE_RULES, REWRITE_RULES = rp, wp
    return "refuse rules: the shipped generic set + {} term(s) from {}".format(n, ip)


def validate_rule_shapes(refuse_rules, rewrite_rules):
    for rule in refuse_rules + rewrite_rules:
        rid = rule.get("id")
        if rule.get("mode") != "regex":
            raise CannotEvaluate(
                "rule {!r} has mode {!r}; scrub.py only supports mode 'regex' "
                "(verify_rules.py should have caught this upstream)".format(
                    rid, rule.get("mode")))
        if not rule.get("pattern"):
            raise CannotEvaluate("rule {!r} has no 'pattern'".format(rid))
        try:
            re.compile(rule["pattern"])
        except re.error as e:
            raise CannotEvaluate("rule {!r} pattern does not compile: {}".format(rid, e))
    for rule in rewrite_rules:
        if not rule.get("to"):
            raise CannotEvaluate("rewrite rule {!r} has no 'to'".format(rule.get("id")))
        if "order" not in rule:
            raise CannotEvaluate("rewrite rule {!r} has no 'order'".format(rule.get("id")))


# ------------------------------------------------------------------------- sibling parts

def fc_verdict(rules_path, text_path):
    """Run the REAL forbidden_content.py CLI and return its exit code ONLY -- its hit
    list is never read (constraint C). Never called on a file this script has not already
    confirmed decodes as UTF-8 (see module docstring, KNOWN LANDMINE)."""
    proc = subprocess.run(
        [sys.executable, FORBIDDEN_CONTENT, "--rules", rules_path,
         "--text-file", text_path, "--json"],
        capture_output=True, text=True)
    return proc.returncode


def move_aside_target(path):
    """Required sibling-part call (constraint H): reserve `path` a clean generation slot
    before this script writes there, in case a prior run staged something at the same
    path. Raises CannotEvaluate (not a silent fallback) if the part is missing or
    refuses."""
    if not os.path.isfile(MOVE_ASIDE):
        raise CannotEvaluate("sibling part missing: {!r}".format(MOVE_ASIDE))
    proc = subprocess.run(
        [sys.executable, MOVE_ASIDE, "--target", path],
        capture_output=True, text=True)
    if proc.returncode != 0:
        raise CannotEvaluate(
            "move_aside could not clear a staging slot for {!r} (exit {}): {}".format(
                path, proc.returncode, proc.stderr.strip()[:300]))


# ------------------------------------------------------------------------------ scanning

def hits_for_rule(text, rx):
    """Every occurrence (constraint C) -- re.finditer, never rx.search."""
    lines = text.splitlines()
    out = []
    for m in rx.finditer(text):
        line_no = text.count("\n", 0, m.start()) + 1
        line = lines[line_no - 1].strip() if 0 <= line_no - 1 < len(lines) else ""
        out.append({"line": line_no, "evidence": line[:200]})
    return out


def _tokens_already_ruled(hits, refuse_rules):
    """Which of the name-shape tokens in `hits` one of the LIVE refuse rules already
    matches on its own.

    This is the seam that keeps a person's name out of canon.py. A token here is one the
    personal tier (or a generic rule) already blocks HARD, so reporting it a second time
    as a soft WARNING is noise on a file that is already NOT-CLEAN. Matched against the
    bare token, never the file, so a rule that needs surrounding syntax (a key
    assignment, a path) can never over-exclude an ordinary capitalised word."""
    tokens = {h["token"] for h in hits if "token" in h}
    if not tokens:
        return set()
    covered = set()
    for rule in refuse_rules:
        rx = re.compile(rule["pattern"])
        for tok in tokens - covered:
            if rx.search(tok):
                covered.add(tok)
    return covered


def apply_refuse_round(text, refuse_rules):
    """ROUND 1. Every rule with a 'to' is substituted in full; every rule without one is
    reported and left untouched (constraint D).

    FIX 1 + FIX 2 (2026-08-05 red-team, 17/17 bypasses): the RAW-text scan/substitute
    logic above this docstring is completely UNCHANGED -- same occurrences, same "to"
    substitution, same auto_resolved/unresolved shape. This ADDS two more passes over
    the ORIGINAL (pre-substitution) text: the Unicode-canonicalised view and a ROT13
    view (see canon.py), plus a decode-and-recheck pass for base64/hex/URL-encoded
    spans and a high-entropy-blob heuristic. A hit that ONLY exists in one of these
    transformed views can never be safely auto-substituted back into the raw file (the
    raw bytes don't literally contain the pattern at any addressable span an
    unambiguous `re.sub` could target) -- so EVERY finding from these passes goes to
    `unresolved`, regardless of whether the rule that fired carries a 'to'. Fail closed:
    a file with an obfuscated identity leak is reported for manual review, never
    silently "fixed" by a substitution that might not even land on the right bytes.

    Returns (text, auto_resolved, unresolved, warnings). `warnings` (added 2026-08-15) is
    a FOURTH, separate bucket -- SHAPE-heuristic findings (a third-party name, a
    disclosing fact pattern; see canon.py) that are WARNING-tier and NEVER affect
    `unresolved` or a file's CLEAN/NOT-CLEAN status. See this function's body for why."""
    auto_resolved = []
    unresolved = []
    original_text = text  # canon/rot13 scans always see the PRE-substitution text
    for rule in refuse_rules:
        rx = re.compile(rule["pattern"], re.MULTILINE)
        occurrences = hits_for_rule(text, rx)
        extra_hits = (canon.canonical_only_hits(original_text, rx)
                      + canon.transformed_only_hits(original_text, rx, canon.rot13, "rot13"))

        if occurrences and rule.get("to") is not None:
            text = rx.sub(rule["to"], text)
            auto_resolved.append({
                "id": rule["id"], "occurrences": len(occurrences), "to": rule["to"]})
            if extra_hits:
                unresolved.append({
                    "id": rule["id"], "tier": rule.get("tier", ""),
                    "why": rule.get("why", "") + " [ALSO present in an obfuscated form "
                                                  "-- not safely auto-fixable]",
                    "hits": extra_hits})
        elif occurrences:
            unresolved.append({
                "id": rule["id"], "tier": rule.get("tier", ""),
                "why": rule.get("why", ""), "hits": occurrences + extra_hits})
        elif extra_hits:
            tag = " [present ONLY in an obfuscated/canonicalised form -- not " \
                  "auto-fixable]" if rule.get("to") is not None else ""
            unresolved.append({
                "id": rule["id"], "tier": rule.get("tier", ""),
                "why": rule.get("why", "") + tag, "hits": extra_hits})

    for finding in canon.scan_encoded_payloads(original_text, refuse_rules):
        unresolved.append(finding)

    # SECOND HARDENING PASS (2026-08-05): bidi controls and Unicode TAG characters are
    # BANNED OUTRIGHT by mere presence (see canon.py's module docstring) -- never
    # interpreted, never auto-fixable, so both always land in `unresolved` regardless
    # of any rule's own "to". These are NOT refuse-rules.json entries (a literal-text
    # regex against raw bytes cannot express "this codepoint is present anywhere"),
    # so they carry their own ids and are proven by canon.py's / this file's own
    # --selftest, not by verify_rules.py (which only inspects refuse-rules.json).
    bidi_hits = canon.scan_bidi_controls(original_text)
    if bidi_hits:
        unresolved.append({
            "id": "unicode-bidi-control", "tier": "1-identity",
            "why": "a Unicode bidirectional control character (U+202A-U+202E or "
                   "U+2066-U+2069) is present -- these can make stored text RENDER "
                   "differently than its byte order (the Trojan Source class: "
                   "reversed storage that displays as the forward name). No "
                   "legitimate shipped file needs one.",
            "hits": bidi_hits,
        })

    tag_hits = canon.scan_tag_chars(original_text)
    if tag_hits:
        unresolved.append({
            "id": "unicode-tag-chars", "tier": "1-identity",
            "why": "a Unicode TAG block character (U+E0000-U+E007F) is present -- "
                   "fully invisible in every normal renderer and capable of carrying "
                   "hidden text recoverable verbatim by a decoder. No legitimate "
                   "shipped file needs one.",
            "hits": tag_hits,
        })

    # FOURTH PASS (2026-08-15) -- SHAPE heuristics, WARNING-tier, NEVER BLOCKING. See
    # canon.py's module docstring for the calibration story. A hit here NEVER lands in
    # `unresolved` and NEVER flips a file's status to NOT-CLEAN -- it is reported
    # separately for a human to glance at and clear. A check that drowns a reviewer gets
    # switched off, which is worse than not having one.
    warnings = []
    name_shape_hits = canon.scan_third_party_name_shape(original_text)
    # ⭐ NEVER DOUBLE-REPORT WHAT A LITERAL RULE ALREADY CATCHES -- and do it WITHOUT a
    # name in a committed file. The donor hard-coded its author's own name and personas
    # into canon.py's stopword table for this; here the exclusion is computed from the
    # LIVE effective rules (the shipped generic set + whatever the operator listed in
    # their own identity file), so it needs no maintenance, adapts to whoever is running
    # the lane, and stays correct when somebody edits their identity file. The re-scan
    # only ever happens when the operator's own listed term literally sits next to a
    # trigger word -- which already makes the file NOT-CLEAN via its literal rule.
    covered = _tokens_already_ruled(name_shape_hits, refuse_rules)
    if covered:
        name_shape_hits = canon.scan_third_party_name_shape(
            original_text, extra_stopwords=covered)
    if name_shape_hits:
        warnings.append({
            "id": "third-party-name-shape", "tier": "3-warning",
            "why": "a capitalised, name-shaped token sits adjacent to a relationship "
                   "or business trigger word (wife, husband, client, coach, student, "
                   "partner, tenant, invoice, collaborator) -- a family member, named "
                   "client, collaborator, or business contact no fixed name list can "
                   "enumerate. WARNING-TIER, NEVER BLOCKING -- a human clears each hit.",
            "hits": name_shape_hits,
        })
    fact_pattern_hits = canon.scan_disclosing_fact_patterns(original_text)
    if fact_pattern_hits:
        warnings.append({
            "id": "disclosing-fact-pattern", "tier": "3-warning",
            "why": "a fact PATTERN that identifies by shape even with every name "
                   "removed -- property ownership, a joint account, an exact pay "
                   "split, a medical detail, or a dated personal life event. "
                   "WARNING-TIER, NEVER BLOCKING -- flagged for human review, never "
                   "auto-substituted.",
            "hits": fact_pattern_hits,
        })

    return text, auto_resolved, unresolved, warnings


def apply_rewrite_round(text, rewrite_rules):
    """ROUND 2. Order-dependent -- ascending 'order', each substitution feeding the
    next, mirroring verify_rules.py's own apply_rewrites exactly."""
    applied = []
    for rule in sorted(rewrite_rules, key=lambda r: r["order"]):
        rx = re.compile(rule["pattern"], re.MULTILINE)
        occurrences = hits_for_rule(text, rx)
        if occurrences:
            text = rx.sub(rule["to"], text)
            applied.append({
                "id": rule["id"], "order": rule["order"],
                "occurrences": len(occurrences), "to": rule["to"]})
    return text, applied


# --------------------------------------------------------------------------- per-file

def process_one_file(raw_entry, abs_source, staging_root, refuse_rules, rewrite_rules,
                      warnings):
    rel = os.path.relpath(abs_source, REPO_ROOT)
    staged_path = os.path.join(staging_root, rel)
    os.makedirs(os.path.dirname(staged_path), exist_ok=True)
    move_aside_target(staged_path)

    # READ-ONLY on abs_source, always -- copy2 opens the source 'rb' and the
    # destination 'wb'; abs_source is never opened for writing anywhere in this file.
    shutil.copy2(abs_source, staged_path)

    file_report = {
        "source": rel, "staged": staged_path, "binary": False, "status": None,
        "refuse": {"auto_resolved": [], "unresolved": [], "warnings": []},
        "rewrite": {"applied": []}, "crosscheck": {},
    }

    # constraint I -- binary / non-UTF-8, detected before any rule ever touches it
    try:
        with open(staged_path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except UnicodeDecodeError as e:
        file_report["binary"] = True
        file_report["status"] = "NOT-CLEAN"
        file_report["refuse"]["unresolved"].append({
            "id": "binary-unreadable", "tier": "structural",
            "why": "file is not valid UTF-8 -- cannot be scanned for identity strings "
                   "and must not be auto-shipped; needs manual review",
            "hits": [{"line": 0, "evidence": str(e)}],
        })
        return file_report

    rc_pre = fc_verdict(REFUSE_RULES, staged_path)

    # NOTE: this function's own `warnings` PARAMETER is the run-level cross-check-
    # disagreement log (below) -- unrelated to `shape_warnings` here, the per-file
    # WARNING-tier SHAPE findings (constraint: never rename the param, other call sites
    # in this file already depend on its identity).
    text, auto_resolved, unresolved, shape_warnings = apply_refuse_round(text, refuse_rules)
    file_report["refuse"]["auto_resolved"] = auto_resolved
    file_report["refuse"]["unresolved"] = unresolved
    file_report["refuse"]["warnings"] = shape_warnings
    # The STAGED copy, never the original. move_aside.py preserves the source mode, and this
    # house ships hooks read-only (pm_flag.sh is 555), so the copy can arrive unwritable and
    # open(...,"w") raises PermissionError -- which surfaced as a TRACEBACK at exit 1, i.e.
    # indistinguishable from a legitimate REFUSAL. Found 2026-08-08 the first time a hook was
    # put in a manifest. Restore the write bit on the COPY before writing; the original's mode
    # is untouched because the original is never opened for writing anywhere in this file.
    _ensure_writable(staged_path)
    with open(staged_path, "w", encoding="utf-8") as fh:
        fh.write(text)

    rc_post_refuse = fc_verdict(REFUSE_RULES, staged_path)
    expect_post = REFUSED if unresolved else CLEAN
    if rc_post_refuse != expect_post:
        warnings.append(
            "{}: forbidden_content.py verdict ({}) disagrees with scrub.py's own scan "
            "(expected {}) after round 1".format(rel, rc_post_refuse, expect_post))

    text, applied = apply_rewrite_round(text, rewrite_rules)
    file_report["rewrite"]["applied"] = applied
    with open(staged_path, "w", encoding="utf-8") as fh:
        fh.write(text)

    rc_post_rewrite = fc_verdict(REWRITE_RULES, staged_path)
    if rc_post_rewrite != CLEAN:
        warnings.append(
            "{}: rewrite patterns still present after round 2 (exit {}) -- substitution "
            "incomplete".format(rel, rc_post_rewrite))

    file_report["crosscheck"] = {
        "refuse_pre_rc": rc_pre, "refuse_post_rc": rc_post_refuse,
        "rewrite_post_rc": rc_post_rewrite,
    }
    file_report["status"] = "NOT-CLEAN" if unresolved else "CLEAN"
    return file_report


# --------------------------------------------------------------------------- orchestrate

def run_scrub(manifest_path, staging_dir, tree_root=None):
    if not os.path.isfile(FORBIDDEN_CONTENT):
        raise CannotEvaluate("sibling part missing: {!r}".format(FORBIDDEN_CONTENT))
    if not os.path.isfile(MOVE_ASIDE):
        raise CannotEvaluate("sibling part missing: {!r}".format(MOVE_ASIDE))

    refuse_rules = load_rules(REFUSE_RULES, "refuse-rules.json")
    # The rewrite tier is allowed to be empty and usually is on a fresh install. Unlike the
    # refuse tier it cannot fail open: it substitutes cosmetics and reports, and never
    # decides whether anything is clean.
    rewrite_rules = load_rules(REWRITE_RULES, "the effective rewrite rules", allow_empty=True)
    validate_rule_shapes(refuse_rules, rewrite_rules)

    # THE BIG FIX (2026-08-15) -- coverage from the TREE (a real filesystem walk), not a
    # hand-typed document and not the git index. `tree_root is not None` means the caller
    # asked for --tree; `manifest_path` stays the other, still-supported source (a curated
    # push legitimately wants a HAND-CHOSEN subset, not "everything").
    tree_scan = None
    if tree_root is not None:
        raw_entries, excluded, git_labels, git_note = derive_tree_entries(tree_root)
        if not raw_entries:
            raise CannotEvaluate(
                "--tree {!r} produced ZERO scannable files -- fail closed, an empty "
                "coverage set is never reported as evaluated".format(tree_root))
        invisible = sorted(p for p, lab in (git_labels or {}).items()
                           if lab == "INVISIBLE-TO-GIT")
        tree_scan = {
            "root": tree_root,
            "walk": "filesystem (os.walk via canon.walk_tree_files) -- NEVER git ls-files",
            "included_count": len(raw_entries),
            "excluded_count": len(excluded),
            "excluded": excluded,
            # The measurement that keeps the fixed bug from coming back: these are the
            # files a `git ls-files` walk would have handed back as "excluded: gitignored"
            # and never opened.
            "git_invisible_count": None if git_labels is None else len(invisible),
            "git_invisible": invisible,
            "git_note": git_note,
        }
        resolved = resolve_entries(raw_entries)
        validate_existence(resolved)
    else:
        raw_entries = parse_manifest(manifest_path)
        resolved = resolve_entries(raw_entries)  # all-or-nothing containment check
        validate_existence(resolved)             # stat-only, still no content read

    staging_root = staging_dir or tempfile.mkdtemp(prefix="shipping-lane-staging-")
    os.makedirs(staging_root, exist_ok=True)

    warnings = []
    files_report = []
    for raw, abs_path in resolved:
        files_report.append(process_one_file(
            raw, abs_path, staging_root, refuse_rules, rewrite_rules, warnings))

    not_clean = [f for f in files_report if f["status"] != "CLEAN"]
    warning_files = [f for f in files_report if f["refuse"].get("warnings")]
    return {
        "manifest": os.path.abspath(manifest_path) if manifest_path else None,
        "tree_scan": tree_scan,
        "staging_root": staging_root,
        "files": files_report,
        "warnings": warnings,
        "summary": {
            "total": len(files_report),
            "clean": len(files_report) - len(not_clean),
            "not_clean": len(not_clean),
            "not_clean_files": [f["source"] for f in not_clean],
            # WARNING-tier SHAPE findings (2026-08-15) -- informational only, NEVER
            # counted in not_clean and NEVER affect the exit code. See canon.py's
            # module docstring for why these are a separate, non-blocking tier.
            "warning_count": sum(len(f["refuse"]["warnings"]) for f in warning_files),
            "warning_files": [f["source"] for f in warning_files],
        },
    }


def render_human_report(report):
    lines = []
    s = report["summary"]
    warn_note = "" if not s.get("warning_count") else ", {} WARNING (non-blocking)".format(
        s["warning_count"])
    lines.append("shipping-lane scrub -- {} file(s), {} clean, {} NOT-CLEAN{}".format(
        s["total"], s["clean"], s["not_clean"], warn_note))
    if report.get("manifest"):
        lines.append("manifest: {}".format(report["manifest"]))
    ts = report.get("tree_scan")
    if ts:
        lines.append("tree scan root: {}".format(ts["root"]))
        lines.append("  walk: {}".format(ts["walk"]))
        lines.append("  {} file(s) scanned, {} excluded (each with a reason, below)".format(
            ts["included_count"], ts["excluded_count"]))
        if ts.get("git_note"):
            lines.append("  git annotation: {}".format(ts["git_note"]))
        elif ts.get("git_invisible_count"):
            lines.append("  ⛔ {} of the scanned file(s) are INVISIBLE TO `git ls-files` "
                         "(gitignored) -- a git-index walk would have skipped these "
                         "entirely and still reported PASS:".format(
                             ts["git_invisible_count"]))
            for p in ts["git_invisible"][:20]:
                lines.append("      git-invisible, SCANNED ANYWAY: {}".format(p))
            if len(ts["git_invisible"]) > 20:
                lines.append("      ... and {} more".format(
                    len(ts["git_invisible"]) - 20))
        else:
            lines.append("  0 scanned file(s) were invisible to git on this run")
        for e in ts["excluded"][:20]:
            lines.append("  excluded: {} ({})".format(e["path"], e["reason"]))
        if len(ts["excluded"]) > 20:
            lines.append("  ... and {} more excluded".format(len(ts["excluded"]) - 20))
    lines.append("staging:  {}".format(report["staging_root"]))
    for f in report["files"]:
        tag = "CLEAN" if f["status"] == "CLEAN" else "NOT-CLEAN"
        lines.append("")
        lines.append("[{}] {}".format(tag, f["source"]))
        if f["binary"]:
            lines.append("  binary/non-UTF-8 -- not scanned, cannot ship as-is")
        for a in f["refuse"]["auto_resolved"]:
            lines.append("  auto-resolved [{}] x{} -> {!r}".format(
                a["id"], a["occurrences"], a["to"]))
        for u in f["refuse"]["unresolved"]:
            lines.append("  UNRESOLVED [{}] {}".format(u["id"], u["why"]))
            for h in u["hits"]:
                lines.append("    line {}: {}".format(h["line"], h["evidence"]))
        for w in f["refuse"].get("warnings", []):
            lines.append("  WARNING (non-blocking) [{}] {}".format(w["id"], w["why"]))
            for h in w["hits"]:
                extra = "  [{}]".format(h["category"]) if "category" in h else (
                    "  token={!r}".format(h["token"]) if "token" in h else "")
                lines.append("    line {}: {}{}".format(h["line"], h["evidence"], extra))
        for r in f["rewrite"]["applied"]:
            lines.append("  rewrite [{}] order {} x{} -> {!r}".format(
                r["id"], r["order"], r["occurrences"], r["to"]))
    if report["warnings"]:
        lines.append("")
        lines.append("WARNINGS (cross-check disagreements):")
        for w in report["warnings"]:
            lines.append("  ! {}".format(w))
    lines.append("")
    lines.append("-" * 60)
    verdict = "REFUSED" if s["not_clean"] else "CLEAN"
    lines.append("VERDICT: {} ({}/{} clean)".format(verdict, s["clean"], s["total"]))
    return "\n".join(lines)


# ---------------------------------------------------------------------------- self-test

def _git_status():
    proc = subprocess.run(["git", "-C", REPO_ROOT, "status", "--porcelain"],
                           capture_output=True, text=True)
    return proc.stdout


def selftest():
    ok_all = True

    def report(label, passed, detail=""):
        nonlocal ok_all
        ok_all = ok_all and passed
        print("  [{}] {}{}".format("PASS" if passed else "FAIL", label,
                                    (" -- " + detail) if detail else ""))

    print("scrub.py --selftest")

    # The shipped rule set has no person in it, so a self-test that planted a name against
    # it would prove nothing. Compose against the lane's own INVENTED identity fixture --
    # the same set `verify_rules.py` uses -- so the personal tier is exercised here too,
    # and nobody's real identity is ever involved in a test run.
    rules_dir = tempfile.mkdtemp(prefix="scrub-selftest-rules-")
    identity_fixture = os.path.join(HERE, "fixtures", "identity-fixture.md")
    # The rewrite tier ships empty, so the order-dependence half of this test plants its
    # own pair. The SHAPE is the lesson and it is what the donor lane got wrong once: a
    # general rule placed before a specific one silently swallows it and produces a string
    # that looks plausible and does not exist.
    rewrite_fixture = os.path.join(rules_dir, "rewrite-fixture.json")
    with open(rewrite_fixture, "w", encoding="utf-8") as fh:
        json.dump([
            {"order": 1, "id": "specific-first", "mode": "regex",
             "pattern": "project-alpha-repo", "to": "alpha-public",
             "example": {"in": "project-alpha-repo", "out": "alpha-public"},
             "why": "MUST run before the general rule or that rule turns it into "
                    "'alpha-repo', which is not a real name"},
            {"order": 2, "id": "general-second", "mode": "regex",
             "pattern": "project-alpha", "to": "alpha",
             "example": {"in": "project-alpha", "out": "alpha"},
             "why": "the general form. LAST on purpose"},
        ], fh)
    sys.path.insert(0, HERE)
    import identity_rules                                     # noqa: E402
    rp, wp, _ip, n = identity_rules.effective_rule_files(
        rules_dir, identity_file=identity_fixture, rewrites_file=rewrite_fixture)
    print("  " + bind_rule_files(refuse=rp, rewrite=wp)
          + " -- the shipped generic set + {} invented term(s)".format(n))

    git_before = _git_status()
    fixture_root = tempfile.mkdtemp(dir=HERE, prefix=".selftest-fixtures-")
    tmp_dirs = []

    def new_staging():
        d = tempfile.mkdtemp(prefix="shipping-lane-selftest-staging-")
        tmp_dirs.append(d)
        return d

    try:
        def write(relpath, content_bytes):
            p = os.path.join(fixture_root, relpath)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "wb") as fh:
                fh.write(content_bytes)
            return p

        def rel(p):
            return os.path.relpath(p, REPO_ROOT)

        f_autoresolve = write("auto.md", b"home at /Users/wren/Desktop\n")
        f_unresolved = write("named.md", b"Wren wrote this file.\n")
        f_secret = write("secret.md", b"api key sk-ant-FAKEFAKEFAKEFAKEFAKE12345678\n")
        f_order = write("order.md", b"repo: project-alpha-repo, dir: project-alpha\n")
        f_clean = write("clean.md", b"Ask the assistant to help. It runs locally.\n")
        f_binary = write("blob.bin", bytes([0xFF, 0xFE, 0x00, 0x80, 0x01]))

        originals_before = {
            p: open(p, "rb").read()
            for p in (f_autoresolve, f_unresolved, f_secret, f_order, f_clean, f_binary)
        }

        manifest_all = os.path.join(fixture_root, "manifest-all.txt")
        with open(manifest_all, "w") as fh:
            fh.write("# selftest manifest\n")
            for p in (f_autoresolve, f_unresolved, f_secret, f_order, f_clean, f_binary):
                fh.write(rel(p) + "\n")

        report_dict = run_scrub(manifest_all, new_staging())
        by_source = {f["source"]: f for f in report_dict["files"]}

        # -------- catch side --------
        u = by_source[rel(f_unresolved)]
        report("catches an unresolved REFUSE hit (bare name, no 'to') -> NOT-CLEAN",
               u["status"] == "NOT-CLEAN"
               and any(h["id"].startswith("identity-") for h in u["refuse"]["unresolved"]))

        s_ = by_source[rel(f_secret)]
        report("a planted secret is NEVER auto-substituted and marks the file NOT-CLEAN",
               s_["status"] == "NOT-CLEAN"
               and any(h["id"] == "key-anthropic" for h in s_["refuse"]["unresolved"])
               and not s_["refuse"]["auto_resolved"])
        with open(s_["staged"], "r", encoding="utf-8") as fh:
            staged_secret_text = fh.read()
        report("...and the secret string is still literally present in staging "
               "(never masked, moved, or shipped-looking-clean)",
               "sk-ant-" in staged_secret_text)

        # -------- auto-resolve side --------
        a_ = by_source[rel(f_autoresolve)]
        report("auto-resolves a REFUSE rule carrying 'to' (path-home) -> file ends CLEAN",
               a_["status"] == "CLEAN"
               and any(h["id"] == "path-home-unix" for h in a_["refuse"]["auto_resolved"]))
        with open(a_["staged"], "r", encoding="utf-8") as fh:
            staged_auto_text = fh.read()
        report("...and the staging copy actually contains the substitution",
               "$HOME" in staged_auto_text and "/Users/wren" not in staged_auto_text)

        # -------- order dependence --------
        o_ = by_source[rel(f_order)]
        with open(o_["staged"], "r", encoding="utf-8") as fh:
            staged_order_text = fh.read()
        report("rewrite order-dependence: the SPECIFIC rule runs first, so "
               "'project-alpha-repo' -> 'alpha-public', never 'alpha-repo'",
               "alpha-public" in staged_order_text
               and "alpha-repo" not in staged_order_text)
        report("...and the general rule still fires on its own trigger: "
               "'project-alpha' -> 'alpha'",
               "dir: alpha" in staged_order_text)

        # -------- no false positive --------
        c_ = by_source[rel(f_clean)]
        with open(c_["staged"], "r", encoding="utf-8") as fh:
            staged_clean_text = fh.read()
        report("no false positive: ordinary prose survives untouched, file stays CLEAN",
               staged_clean_text == originals_before[f_clean].decode("utf-8")
               and c_["status"] == "CLEAN")

        # -------- binary handling --------
        b_ = by_source[rel(f_binary)]
        report("a binary/non-UTF-8 file is flagged NOT-CLEAN, never crashes, "
               "never passes as clean",
               b_["status"] == "NOT-CLEAN" and b_["binary"] is True)

        # -------- constraint A: originals byte-identical --------
        all_untouched = all(
            open(p, "rb").read() == originals_before[p] for p in originals_before)
        report("every ORIGINAL is byte-identical after the run (never opened for writing)",
               all_untouched)

        report("a manifest with any NOT-CLEAN file rolls up to overall REFUSED",
               report_dict["summary"]["not_clean"] >= 1)

        # -------- FIX 1 + FIX 2: the 2026-08-05 red-team bypasses, all 17/17 --------
        import base64 as _b64mod, binascii as _hexmod2, codecs as _codecsmod, secrets as _secretsmod
        f_dotted = write("obf-dotted.md", b"signed Wr.en Oak-ley\n")
        f_spaced = write("obf-spaced.md", b"signed W r e n\n")
        f_leet = write("obf-leet.md", b"signed Wr3n 04kl3y\n")
        f_zwj = write("obf-zwj.md",
                      ("signed " + "‍".join(list("Wren")) + "\n").encode("utf-8"))
        f_nfd = write("obf-nfd.md", "signed Wrén\n".encode("utf-8"))
        f_b64 = write("obf-b64.md",
                      ("note: " + _b64mod.b64encode(b"Wren Oakley").decode() + "\n").encode())
        f_hex = write("obf-hex.md",
                      ("note: " + _hexmod2.hexlify(b"Wren Oakley").decode() + "\n").encode())
        f_rot13 = write("obf-rot13.md",
                        ("note: " + _codecsmod.encode("Wren Oakley", "rot_13") + "\n").encode())
        f_b64key = write("obf-b64key.md", ("cfg: " + _b64mod.b64encode(
            b"sk-ant-FAKEFAKEFAKEFAKEFAKE12345678").decode() + "\n").encode())
        f_urlemail = write("obf-urlemail.md", ("reach " + "".join(
            "%{:02X}".format(ord(c)) for c in "wren.oakley@example.com") + "\n").encode())
        f_entropy = write("obf-entropy.md",
                          ("token: " + _secretsmod.token_urlsafe(32) + "\n").encode())

        # -------- second hardening pass, 2026-08-05 (same day, second red-team) --------
        f_bidi = write("obf-bidi.md", ("signed " + "‮" + "nerW" + "‬"
                                       + "\n").encode("utf-8"))
        f_tagchars = write("obf-tagchars.md", ("notes" + "".join(
            chr(0xE0000 + ord(c)) for c in "wren oakley") + "\n").encode("utf-8"))
        f_smallcaps = write("obf-smallcaps.md", ("signed ᴡʀᴇɴ "
                                                 "ᴏᴀᴋʟᴇʏ"
                                                 "\n").encode("utf-8"))
        f_b64x2 = write("obf-b64x2.md", ("note: " + _b64mod.b64encode(
            _b64mod.b64encode(b"Wren Oakley")).decode() + "\n").encode())
        f_base32key = write("obf-base32key.md", ("cfg: " + _b64mod.b32encode(
            b"sk-ant-FAKEFAKEFAKEFAKEFAKE12345678").decode() + "\n").encode())
        f_qpemail = write("obf-qpemail.md", ("reach " + "".join(
            "={:02X}".format(b) for b in "wren.oakley@example.com".encode())
            + "\n").encode())

        obf_files = [f_dotted, f_spaced, f_leet, f_zwj, f_nfd, f_b64, f_hex, f_rot13,
                     f_b64key, f_urlemail, f_entropy, f_bidi, f_tagchars, f_smallcaps,
                     f_b64x2, f_base32key, f_qpemail]
        manifest_obf = os.path.join(fixture_root, "manifest-obfuscated.txt")
        with open(manifest_obf, "w") as fh:
            for p in obf_files:
                fh.write(rel(p) + "\n")
        obf_report = run_scrub(manifest_obf, new_staging())
        obf_by_source = {f["source"]: f for f in obf_report["files"]}
        not_caught = [rel(p) for p in obf_files
                      if obf_by_source[rel(p)]["status"] != "NOT-CLEAN"]
        report("every one of the 17 known 2026-08-05 bypass shapes (both red-team "
               "passes) is now caught (canonicalisation, ROT13, small-caps, bidi/tag "
               "presence, and encoded-payload/entropy findings all go to 'unresolved', "
               "never auto-substituted)",
               not not_caught, "NOT caught: {}".format(not_caught))
        entropy_hits = obf_by_source[rel(f_entropy)]["refuse"]["unresolved"]
        report("the unknown-format high-entropy secret is reported under its own "
               "distinct finding id",
               any(h["id"] == "high-entropy-blob" for h in entropy_hits))
        bidi_hits = obf_by_source[rel(f_bidi)]["refuse"]["unresolved"]
        report("the bidi-reversed name is reported under its own distinct finding id",
               any(h["id"] == "unicode-bidi-control" for h in bidi_hits))
        tag_hits = obf_by_source[rel(f_tagchars)]["refuse"]["unresolved"]
        report("the TAG-hidden name is reported under its own distinct finding id",
               any(h["id"] == "unicode-tag-chars" for h in tag_hits))
        b64x2_hits = obf_by_source[rel(f_b64x2)]["refuse"]["unresolved"]
        report("the doubly-base64-wrapped name is caught at decode depth 2",
               any(h["id"].startswith("encoded-identity-")
                   and h["hits"][0].get("decode_depth") == 2 for h in b64x2_hits),
               "hits: {}".format(b64x2_hits))

        # -------- THE BIG FIX: --tree walks the FILESYSTEM, not the git index --------
        # This is the regression test for the two blind spots this flag exists to close,
        # and it is deliberately built so it FAILS if anyone ever re-implements the walk
        # on `git ls-files`: the file it must catch is one .gitignore covers (`*.bak`),
        # which a git-index walk hands back as "excluded: gitignored" and never opens.
        tree_dir = os.path.join(fixture_root, "treefix")
        os.makedirs(tree_dir, exist_ok=True)
        f_tree_listed = write("treefix/listed.md",
                              b"Ordinary prose that names nobody.\n")
        f_tree_ignored = write("treefix/unlisted.bak",
                               b"draft copy -- Wren wrote this and forgot it here\n")
        gi = subprocess.run(["git", "-C", REPO_ROOT, "check-ignore", "-q",
                             os.path.relpath(f_tree_ignored, REPO_ROOT)],
                            capture_output=True, text=True)
        report("the fixture the tree walk must catch is genuinely .gitignore'd "
               "(so a git-index walk would never open it)",
               gi.returncode == 0, "git check-ignore exit {}".format(gi.returncode))

        tree_report = run_scrub(None, new_staging(), tree_root=rel(tree_dir))
        tree_by_source = {f["source"]: f for f in tree_report["files"]}
        report("--tree derives its file set by WALKING THE FILESYSTEM: a .gitignore'd "
               "file present on disk IS scanned, not skipped",
               rel(f_tree_ignored) in tree_by_source,
               "scanned: {}".format(sorted(tree_by_source)))
        report("...and that git-invisible file is CAUGHT (identity term -> NOT-CLEAN), "
               "which is the whole point: the scanner sees what git hides",
               tree_by_source.get(rel(f_tree_ignored), {}).get("status") == "NOT-CLEAN")
        report("...and the run REPORTS it as git-invisible, so the fixed bug stays "
               "measured on every run instead of being re-introduced quietly",
               rel(f_tree_ignored) in tree_report["tree_scan"]["git_invisible"],
               "git_invisible: {}".format(tree_report["tree_scan"]["git_invisible"]))
        report("...and an ordinary tracked-shaped file in the same walk stays CLEAN "
               "(the walk is not just flagging everything)",
               tree_by_source.get(rel(f_tree_listed), {}).get("status") == "CLEAN")
        report("--tree never asks git what exists: the walk's own coverage claim is "
               "the filesystem's, and it says so in the report",
               "NEVER git ls-files" in tree_report["tree_scan"]["walk"])

        try:
            run_scrub(None, new_staging(), tree_root="/etc")
            report("--tree pointed OUTSIDE the clone is refused (CannotEvaluate)",
                   False, "no exception raised")
        except CannotEvaluate as e:
            report("--tree pointed OUTSIDE the clone is refused (CannotEvaluate)",
                   "OUTSIDE" in str(e), str(e)[:120])

        empty_tree = os.path.join(fixture_root, "emptytree")
        os.makedirs(empty_tree, exist_ok=True)
        try:
            run_scrub(None, new_staging(), tree_root=rel(empty_tree))
            report("a --tree walk yielding ZERO files is refused, never a vacuous CLEAN",
                   False, "no exception raised")
        except CannotEvaluate as e:
            report("a --tree walk yielding ZERO files is refused, never a vacuous CLEAN",
                   "ZERO" in str(e), str(e)[:120])

        # -------- out-of-reach manifest entry (constraint B) --------
        outside_manifest = os.path.join(fixture_root, "manifest-outside.txt")
        with open(outside_manifest, "w") as fh:
            fh.write("/etc/hosts\n")
        probe = new_staging()
        try:
            run_scrub(outside_manifest, probe)
            report("a manifest entry outside the clone is refused (CannotEvaluate)",
                   False, "no exception raised")
        except CannotEvaluate:
            report("a manifest entry outside the clone is refused (CannotEvaluate)", True)
        report("...and NOTHING was copied into staging as a result", os.listdir(probe) == [])

        # -------- empty manifest --------
        empty_manifest = os.path.join(fixture_root, "manifest-empty.txt")
        with open(empty_manifest, "w") as fh:
            fh.write("# only comments\n\n")
        try:
            run_scrub(empty_manifest, new_staging())
            report("an empty manifest is refused (CannotEvaluate), never all-clear",
                   False, "no exception raised")
        except CannotEvaluate:
            report("an empty manifest is refused (CannotEvaluate), never all-clear", True)

        # -------- missing manifest --------
        try:
            run_scrub(os.path.join(fixture_root, "nope.txt"), new_staging())
            report("a missing manifest file is refused (CannotEvaluate)",
                   False, "no exception raised")
        except CannotEvaluate:
            report("a missing manifest file is refused (CannotEvaluate)", True)

        # -------- end-to-end through the real CLI --------
        me = os.path.abspath(__file__)

        p = subprocess.run(
            [sys.executable, me, "--refuse-rules", rp, "--rewrite-rules", wp, "--manifest", manifest_all,
             "--staging", new_staging(), "--json"],
            capture_output=True, text=True)
        report("CLI: mixed manifest -> exit 1 (REFUSED)", p.returncode == REFUSED,
               "got exit {}".format(p.returncode))

        clean_manifest = os.path.join(fixture_root, "manifest-clean-only.txt")
        with open(clean_manifest, "w") as fh:
            fh.write(rel(f_clean) + "\n" + rel(f_order) + "\n" + rel(f_autoresolve) + "\n")
        p = subprocess.run(
            [sys.executable, me, "--refuse-rules", rp, "--rewrite-rules", wp, "--manifest", clean_manifest, "--staging", new_staging()],
            capture_output=True, text=True)
        report("CLI: all-clean / all-auto-resolvable manifest -> exit 0",
               p.returncode == CLEAN, "got exit {}".format(p.returncode))

        p = subprocess.run(
            [sys.executable, me, "--refuse-rules", rp, "--rewrite-rules", wp, "--manifest", outside_manifest, "--staging", new_staging()],
            capture_output=True, text=True)
        report("CLI: out-of-reach manifest entry -> exit 2 (CANNOT EVALUATE)",
               p.returncode == CANNOT_EVALUATE, "got exit {}".format(p.returncode))

        p = subprocess.run(
            [sys.executable, me, "--refuse-rules", rp, "--rewrite-rules", wp, "--manifest", empty_manifest, "--staging", new_staging()],
            capture_output=True, text=True)
        report("CLI: empty manifest -> exit 2, NOT exit 0",
               p.returncode == CANNOT_EVALUATE, "got exit {}".format(p.returncode))

        p = subprocess.run([sys.executable, me], capture_output=True, text=True)
        report("CLI: neither --manifest nor --tree -> exit 2",
               p.returncode == CANNOT_EVALUATE, "got exit {}".format(p.returncode))

        p = subprocess.run(
            [sys.executable, me, "--refuse-rules", rp, "--rewrite-rules", wp,
             "--tree", rel(tree_dir), "--staging", new_staging()],
            capture_output=True, text=True)
        report("CLI: --tree over a subtree holding a gitignored leak -> exit 1 (REFUSED)",
               p.returncode == REFUSED, "got exit {}".format(p.returncode))

        p = subprocess.run(
            [sys.executable, me, "--refuse-rules", rp, "--rewrite-rules", wp,
             "--tree", "/etc", "--staging", new_staging()],
            capture_output=True, text=True)
        report("CLI: --tree outside the clone -> exit 2 (CANNOT EVALUATE), fail closed",
               p.returncode == CANNOT_EVALUATE, "got exit {}".format(p.returncode))

        p = subprocess.run(
            [sys.executable, me, "--refuse-rules", rp, "--rewrite-rules", wp,
             "--manifest", manifest_all, "--tree", ".", "--staging", new_staging()],
            capture_output=True, text=True)
        report("CLI: --manifest and --tree together -> exit 2, never a half-defined scan",
               p.returncode == CANNOT_EVALUATE, "got exit {}".format(p.returncode))

        # -------- FOURTH PASS: SHAPE-heuristic WARNINGS never block (2026-08-15) ------
        #
        # The one property that makes this tier usable: it reports, it never gates. If a
        # warning could flip a verdict or an exit code, every downstream consumer of this
        # lane would start refusing on a heuristic that is allowed to be wrong.
        thirdparty_manifest = os.path.join(fixture_root, "manifest-thirdparty.txt")
        f_thirdparty = write("thirdparty.md",
                             b"His wife Sarah handles the scheduling for him.\n")
        f_factpattern = write("factpattern.md",
                              b"He owns two homes and holds joint bank accounts.\n")
        with open(thirdparty_manifest, "w") as fh:
            fh.write(rel(f_thirdparty) + "\n" + rel(f_factpattern) + "\n")
        warn_report = run_scrub(thirdparty_manifest, new_staging())
        warn_by_source = {f["source"]: f for f in warn_report["files"]}
        tp = warn_by_source[rel(f_thirdparty)]
        report("a third-party name-shape hit is a WARNING, and the file still reports "
               "CLEAN (WARNING-tier NEVER blocks)",
               tp["status"] == "CLEAN"
               and any(w["id"] == "third-party-name-shape" for w in tp["refuse"]["warnings"]),
               "refuse={}".format(tp["refuse"]))
        report("...and the warning NEVER leaks into `unresolved` (the blocking bucket)",
               tp["refuse"]["unresolved"] == [],
               "unresolved={}".format(tp["refuse"]["unresolved"]))
        fp = warn_by_source[rel(f_factpattern)]
        report("a disclosing fact-pattern hit is a WARNING, and the file still reports "
               "CLEAN (WARNING-tier NEVER blocks)",
               fp["status"] == "CLEAN"
               and any(w["id"] == "disclosing-fact-pattern" for w in fp["refuse"]["warnings"]),
               "refuse={}".format(fp["refuse"]))
        report("every warning carries tier '3-warning', so a reader can tell a "
               "non-blocking finding from a blocking one without reading the id",
               all(w["tier"] == "3-warning"
                   for f in (tp, fp) for w in f["refuse"]["warnings"]))
        report("the run-level summary counts warnings SEPARATELY from not_clean, and "
               "not_clean stays 0 for an all-warning, zero-refuse manifest",
               warn_report["summary"]["not_clean"] == 0
               and warn_report["summary"]["warning_count"] >= 2,
               "summary={}".format(warn_report["summary"]))
        report("...and summary.warning_files names exactly the files that warned",
               sorted(warn_report["summary"]["warning_files"])
               == sorted([rel(f_thirdparty), rel(f_factpattern)]),
               "warning_files={}".format(warn_report["summary"]["warning_files"]))
        report("the human report SURFACES the warning to a reader (a finding nobody is "
               "shown is a finding that does not exist)",
               "WARNING (non-blocking) [third-party-name-shape]"
               in render_human_report(warn_report)
               and "non-blocking)" in render_human_report(warn_report).splitlines()[0])
        report("...and the VERDICT line still says CLEAN on an all-warning run",
               "VERDICT: CLEAN" in render_human_report(warn_report))

        p = subprocess.run(
            [sys.executable, me, "--refuse-rules", rp, "--rewrite-rules", wp,
             "--manifest", thirdparty_manifest, "--staging", new_staging()],
            capture_output=True, text=True)
        report("CLI: a manifest with ONLY WARNING-tier hits -> exit 0, never exit 1",
               p.returncode == CLEAN, "got exit {}".format(p.returncode))

        # A file that warns AND carries a real refuse hit is NOT-CLEAN for the REFUSE
        # hit alone -- the warning neither causes that nor is swallowed by it.
        both_manifest = os.path.join(fixture_root, "manifest-both.txt")
        # "client Wren" is the SAME shape as "wife Sarah" -- both would warn. Only Sarah
        # survives, because Wren is a term in the live identity file and its literal rule
        # already blocks the file outright.
        f_both = write("both.md",
                       b"His wife Sarah met client Wren about the retainer.\n")
        with open(both_manifest, "w") as fh:
            fh.write(rel(f_both) + "\n")
        both_report = run_scrub(both_manifest, new_staging())
        b = both_report["files"][0]
        report("a file with BOTH a warning and a real refuse hit is NOT-CLEAN for the "
               "REFUSE hit, and still reports the warning alongside it",
               b["status"] == "NOT-CLEAN"
               and any(h["id"].startswith("identity-") for h in b["refuse"]["unresolved"])
               and any(w["id"] == "third-party-name-shape" for w in b["refuse"]["warnings"]),
               "refuse={}".format(b["refuse"]))
        report("...and the operator's OWN listed term is NOT double-reported as a "
               "name-shape warning (the seam that replaces the donor's hard-coded "
               "stopword names -- exclusion comes from the LIVE rules)",
               all(h["token"] != "Wren"
                   for w in b["refuse"]["warnings"] if w["id"] == "third-party-name-shape"
                   for h in w["hits"]),
               "warnings={}".format(b["refuse"]["warnings"]))

    finally:
        shutil.rmtree(fixture_root, ignore_errors=True)
        for d in tmp_dirs:
            shutil.rmtree(d, ignore_errors=True)

    git_after = _git_status()
    report("git status --porcelain in the clone is unchanged by the whole selftest run",
           git_before == git_after,
           "differs -- either a real leak or a concurrent edit elsewhere in the clone"
           if git_before != git_after else "")

    print("SELFTEST:", "PASS" if ok_all else "FAIL")
    return CLEAN if ok_all else REFUSED


# --------------------------------------------------------------------------------- CLI

def main():
    ap = argparse.ArgumentParser(
        description="scrub.py -- the shipping lane's tree-walker: manifest -> staging "
                    "copy -> REFUSE round -> REWRITE round -> report")
    ap.add_argument("--manifest", help="text file, one repo-relative path per line, "
                                       "'#' comments allowed -- a CURATED subset, for a "
                                       "deliberate push. Mutually exclusive with --tree.")
    ap.add_argument("--tree", nargs="?", const=".", default=None, metavar="PATH",
                    help="derive the file set by WALKING THE FILESYSTEM under PATH "
                         "(default: the whole clone) instead of trusting a manifest "
                         "document. Sees EVERY file on disk -- tracked, untracked and "
                         "gitignored alike -- because it never asks git what exists; "
                         "each run reports how many of them a `git ls-files` walk would "
                         "have missed. Mutually exclusive with --manifest.")
    ap.add_argument("--staging", help="staging root; default: a fresh OS temp dir "
                                      "OUTSIDE this git clone")
    ap.add_argument("--report-json", help="also write the JSON report here")
    ap.add_argument("--report-txt", help="also write the human report here")
    ap.add_argument("--json", action="store_true", help="print the JSON report to stdout")
    ap.add_argument("--refuse-rules", help="an already-composed effective refuse set; "
                                           "default: compose it from your identity file")
    ap.add_argument("--rewrite-rules", help="an already-composed effective rewrite set")
    ap.add_argument("--identity", help="compile the personal tier from this identity file "
                                       "instead of the one in your notes")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())

    try:
        if not args.manifest and args.tree is None:
            raise CannotEvaluate("one of --manifest or --tree is required")
        if args.manifest and args.tree is not None:
            raise CannotEvaluate(
                "--manifest and --tree are mutually exclusive -- pick one coverage "
                "source (a curated manifest, or a full/derived tree walk)")
        which = bind_rule_files(args.refuse_rules, args.rewrite_rules, args.identity)
        print(which, file=sys.stderr)
        report = run_scrub(args.manifest, args.staging, tree_root=args.tree)
    except CannotEvaluate as e:
        print("CANNOT EVALUATE: {}".format(e), file=sys.stderr)
        sys.exit(CANNOT_EVALUATE)

    if args.report_json:
        with open(args.report_json, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
    if args.report_txt:
        with open(args.report_txt, "w", encoding="utf-8") as fh:
            fh.write(render_human_report(report))

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(render_human_report(report))

    sys.exit(REFUSED if report["summary"]["not_clean"] else CLEAN)


if __name__ == "__main__":
    main()

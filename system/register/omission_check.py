#!/usr/bin/env python3
"""omission_check.py — the register's OMISSION CHECK (Feature B1.4, enforcement-layer
Phase 2 plan). A sibling module `generate.py` calls; also runnable standalone.

Round-2 attack #4's repair, restated: a scan-vs-register diff. This module walks the
GOVERNED FOLDERS live, right now, and names every script that is neither a matching
row in the register nor listed in the hand-editable exemption file. It never judges
WHY a script is uncalled (that's T1's job, and later B1.5's caller lint) — it only
asks "does this governed-folder file have ANY register entry (or a stated reason it
doesn't)?"

Governed folders (T1's own `GOVERNED_DIRS`, `t1_caller_detection.py`, verbatim; also
named directly in this plan's B1.4 Execute line): `system/hooks/`, `system/tools/`,
in BOTH repos (public + private). Same file filter as T1 and as `harvest.py`'s own
`harvest_tools()` — reused from `harvest.py`, never a second, silently-diverging
definition of "governed": `.sh`/`.py` only, `__pycache__` dirs skipped, `.bak`/`.pyc`
files skipped, and a test-class file (a `tests?/` dir, or a `test_`/`test-`/`firetest`
basename) is EXEMPT from the governed set at the walk itself — it never even reaches
the flagged/exempt distinction below, exactly as T1 defined it.

A hooks-folder file counts as "registered" iff the register carries a `hook`-type row
whose `path` matches it (i.e., SOME wiring surface names it — `harvest_hooks()` only
ever discovers a hook file THROUGH a registration, so an unregistered hook script has
no other way into the register). A tools-folder file counts as "registered" iff the
register carries a `tool`-type row whose `path` matches it (`harvest_tools()` disk-
walks `system/tools/` directly, so every live tool file gets a row on a fresh harvest
— this check catches the register going STALE relative to the disk, not just a
harvester bug: a hand-edited register, an old harvest re-used after a file was added,
or a scratch/planted script are all the same shape of drift to this check).

SEVERITY (Enver's ruling, 2026-09-15 — plan Discoveries, `schema-v1.md`): **WARN for
v1**, not refuse. An omission is always NAMED; whether it also fails the run is one
flag: `--severity warn` (default) prints a clearly marked WARN section and leaves the
exit code to whatever else determined it (this check contributes nothing to the exit
code); `--severity refuse` makes the identical finding a whole-run refusal (nothing
written, matching the schema gate's own all-or-nothing posture) — a one-word change
in the caller, never a code rewrite, so escalating this check later costs one flag,
not a redesign.

Exemptions live in a plain, hand-editable, pipe-delimited text file (no JSON, no
YAML, no code) — one line per exemption, `repo|path|reason`, `#`/blank lines ignored.
A reason is REQUIRED per entry (this module refuses to load a reason-less line) —
"no hidden allowlists in code" means every entry a human can read top-to-bottom
carries why it's there, not just that it's there.
"""
import argparse
import os
import sys

# Sibling-module import — same convention `generate.py` already relies on: running
# `python3 .../omission_check.py` puts this script's own directory at sys.path[0],
# so `harvest` (same `system/register/` folder) resolves with no path hacking.
from harvest import (
    REPO_ROOT_FROM_SCRIPT,
    DEFAULT_PRIVATE_ROOT,
    is_test_class,
    SCRIPT_EXTS,
    to_repo_path,
)

# T1's own governed folders (`t1_caller_detection.py` GOVERNED_DIRS), verbatim, and
# the plan's own B1.4 Execute line names the same two. Stated here, not inferred —
# a third governed folder later is a one-line addition to this tuple and the map
# below, never a silent scope change this report doesn't announce.
GOVERNED_DIRS = ("system/hooks", "system/tools")

# Which register unit `type` "covers" a file found under each governed folder.
FOLDER_UNIT_TYPE = {
    "system/hooks": "hook",
    "system/tools": "tool",
}

DEFAULT_EXEMPTIONS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        "omission-exemptions.txt")


# ---------------------------------------------------------------------------
# disk inventory — T1's exact filter, reused from harvest.py
# ---------------------------------------------------------------------------
def walk_governed_folder(root, repo, subdir):
    """Every governed file under <root>/<subdir>, T1's filter verbatim (reused
    constants/functions from harvest.py, not re-implemented): skip __pycache__ dirs,
    skip .bak/.pyc files, require a SCRIPT_EXTS extension, skip a test-class path."""
    base = os.path.join(root, subdir)
    rows = []
    if not os.path.isdir(base):
        return rows
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for f in sorted(filenames):
            if f.endswith(".bak") or f.endswith(".pyc"):
                continue
            if not f.endswith(SCRIPT_EXTS):
                continue
            full = os.path.join(dirpath, f)
            rel = os.path.relpath(full, root)
            if is_test_class(rel):
                continue  # T1's exempt (test-class) unit — never governed, not flagged
            rows.append({"repo": repo, "path": to_repo_path(root, full), "folder": subdir})
    return rows


def disk_inventory(public_root, private_root):
    """Every governed-folder file on disk, both repos, both folders — T1's own
    252-unit universe, recomputed live (not read from a snapshot)."""
    rows = []
    for subdir in GOVERNED_DIRS:
        rows.extend(walk_governed_folder(public_root, "public", subdir))
        rows.extend(walk_governed_folder(private_root, "private", subdir))
    return rows


# ---------------------------------------------------------------------------
# exemptions — plain, hand-editable, a reason required per entry
# ---------------------------------------------------------------------------
def load_exemptions(path):
    """Return {(repo, path): reason}. Missing file == no exemptions (not an error —
    a fresh checkout with nothing exempted yet is a legal, if unusual, state)."""
    exemptions = {}
    if not path or not os.path.isfile(path):
        return exemptions
    with open(path, encoding="utf-8") as f:
        for lineno, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("|", 2)
            if len(parts) != 3:
                raise ValueError(
                    f"{path}:{lineno}: malformed exemption line (need repo|path|reason): {raw!r}"
                )
            repo, ex_path, reason = (p.strip() for p in parts)
            if repo not in ("public", "private"):
                raise ValueError(f"{path}:{lineno}: repo must be 'public' or 'private': {raw!r}")
            if not ex_path.startswith("/"):
                raise ValueError(f"{path}:{lineno}: path must start with '/': {raw!r}")
            if not reason:
                raise ValueError(f"{path}:{lineno}: exemption has no reason (required): {raw!r}")
            exemptions[(repo, ex_path)] = reason
    return exemptions


# ---------------------------------------------------------------------------
# register cross-reference
# ---------------------------------------------------------------------------
def registered_paths_by_type(register_entries):
    """`register_entries` is either `generate.load_register()`'s own shape
    (line_no, row_or_None, errs_or_None) or a plain iterable of rows — accepts both
    so this module works from the generator's already-loaded, already-schema-checked
    rows AND from a bare list for standalone/test use. Returns {(repo, path): type}
    for every row whose path resolves to a concrete file (an UNPARSED command has no
    file to cover and is skipped, same treatment `generate.py`'s own assert-on-write
    gate gives it)."""
    covered = {}
    for entry in register_entries:
        row = entry[1] if isinstance(entry, tuple) else entry
        if not row or row.get("type") not in ("hook", "tool"):
            continue
        path = row.get("path", "")
        if not path or path.startswith("UNPARSED"):
            continue
        covered[(row.get("repo"), path)] = row["type"]
    return covered


def check_omissions(disk_rows, covered, exemptions):
    """Returns (registered, flagged, exempted) — THREE lists, every disk row landing
    in EXACTLY ONE of them (this is what makes `total == len(registered) +
    len(exempted) + len(flagged)` in `run()` below a genuine arithmetic check, not a
    subtraction that can never disagree: each row is independently classified once,
    counted once, and the equality is asserted over three separately-built lists).

    A disk file is 'registered' iff (repo, path) is covered by a register row of the
    MATCHING unit type for its own folder — a hooks-folder file needs a `hook` row, a
    tools-folder file needs a `tool` row; a stray row of the WRONG type at that same
    key does not count (nothing stops a hand-edit from mislabeling a row, and this
    check should not be fooled by one)."""
    registered, flagged, exempted = [], [], []
    for r in disk_rows:
        key = (r["repo"], r["path"])
        want_type = FOLDER_UNIT_TYPE[r["folder"]]
        if covered.get(key) == want_type:
            registered.append(r)
            continue
        reason = exemptions.get(key)
        if reason is not None:
            exempted.append({**r, "reason": reason})
        else:
            flagged.append(r)
    return registered, flagged, exempted


# ---------------------------------------------------------------------------
# orchestration — the one entry point generate.py (or a standalone caller) uses
# ---------------------------------------------------------------------------
def run(register_entries, public_root, private_root, exemptions_path=None, severity="warn"):
    """Never raises for an ordinary flagged omission (same convention as
    `generate.generate()`'s schema/assert-on-write gates) — a malformed EXEMPTIONS
    file is the one thing this function lets raise, since that is a hand-editing
    mistake in a file this task requires to be readable, not a live-system finding."""
    if severity not in ("warn", "refuse"):
        raise ValueError(f"severity must be 'warn' or 'refuse', got {severity!r}")
    exemptions_path = exemptions_path or DEFAULT_EXEMPTIONS_PATH

    disk_rows = disk_inventory(public_root, private_root)
    covered = registered_paths_by_type(register_entries)
    exemptions = load_exemptions(exemptions_path)
    registered, flagged, exempted = check_omissions(disk_rows, covered, exemptions)

    total = len(disk_rows)
    registered_count = len(registered)
    exempt_count = len(exempted)
    flagged_count = len(flagged)
    # THE arithmetic (Verify #3): three independently-built lists, partitioning
    # disk_rows once each — this equality can genuinely fail (a bug that drops or
    # double-counts a row would break it), it is not true by construction of a
    # subtraction.

    return {
        "severity": severity,
        "governed_dirs": GOVERNED_DIRS,
        "exemptions_path": exemptions_path,
        "total": total,
        "registered_count": registered_count,
        "exempt_count": exempt_count,
        "flagged_count": flagged_count,
        "reconciled": registered_count + exempt_count + flagged_count == total,
        "flagged": flagged,
        "exempted": exempted,
    }


def report_lines(result):
    """Verify #3's arithmetic, rendered — this is CODE producing the line, not prose
    describing one: `total == registered + exempt + flagged` is computed in `run()`
    above and simply printed here."""
    lines = [
        "OMISSION CHECK — governed folders {} (both repos):".format(
            ", ".join(result["governed_dirs"])
        ),
        "  {total} on disk = {reg} registered + {exempt} exempt + {flagged} flagged "
        "({verdict})".format(
            total=result["total"], reg=result["registered_count"],
            exempt=result["exempt_count"], flagged=result["flagged_count"],
            verdict="reconciles" if result["reconciled"] else "DOES NOT RECONCILE",
        ),
    ]
    if result["flagged"]:
        label = "REFUSED" if result["severity"] == "refuse" else "WARN"
        lines.append(
            f"{label}: {result['flagged_count']} governed script(s) neither registered "
            f"nor exempt (exemptions: {result['exemptions_path']}):"
        )
        for r in sorted(result["flagged"], key=lambda x: (x["repo"], x["path"])):
            lines.append(f"    {r['repo']}:{r['path']}")
    return lines


# ---------------------------------------------------------------------------
# standalone CLI
# ---------------------------------------------------------------------------
def _load_register_file(path):
    import json
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("register", help="path to a schema-v1 JSONL register (e.g. from harvest.py)")
    p.add_argument("--public-root", default=REPO_ROOT_FROM_SCRIPT,
                   help="public repo root (default: this script's own repo, three dirs up)")
    p.add_argument("--private-root", default=DEFAULT_PRIVATE_ROOT,
                   help="private repo root (default: ~/.claude/skills/ClaudeOps)")
    p.add_argument("--exemptions", default=DEFAULT_EXEMPTIONS_PATH,
                   help=f"exemption file (default: {DEFAULT_EXEMPTIONS_PATH})")
    p.add_argument("--severity", choices=("warn", "refuse"), default="warn",
                   help="warn (default): name omissions, exit 0. refuse: same finding, exit 1.")
    args = p.parse_args(argv)

    public_root = os.path.abspath(args.public_root)
    private_root = os.path.abspath(os.path.expanduser(args.private_root))
    rows = _load_register_file(args.register)

    result = run(rows, public_root, private_root, args.exemptions, args.severity)
    print(f"omission_check.py — {args.register}")
    for line in report_lines(result):
        print(line)

    exit_code = 1 if (result["severity"] == "refuse" and result["flagged_count"] > 0) else 0
    if not result["reconciled"]:
        exit_code = 1  # arithmetic itself failing is always a hard error, any severity
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

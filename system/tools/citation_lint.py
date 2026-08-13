#!/usr/bin/env python3
"""citation_lint — every file, skill and hook these documents NAME either exists here, or is
accounted for on the line that names it.

WHY THIS IS CODE AND NOT A REVIEW HABIT. A document that points at a file which is not in this
repository is worse than a document that says nothing: it sends a reader hunting, and when they find
nothing they conclude the file is lost rather than that the sentence is wrong. That failure is
invisible to every other check here -- the tests pass, the skill runs, the prose is confident -- and
it grows every time something is renamed, moved or left behind in a migration. This is the
mechanical proof that what the documents promise is actually present.

THE THREE CHECKS

  1. PATHS      every backticked repo path in every .md -- `system/tools/x.py`, `.claude/skills/y/`
  2. SKILLS     every backticked slash command -- `/save`, `/websearch`
  3. HOOKS      settings.json <-> system/hooks/ in both directions: nothing registered that is
                missing from disk, nothing on disk that is registered nowhere and declared nowhere

THE ONE RULE, AND THE THREE WAYS TO SATISFY IT. A citation must resolve, or its line must SAY what
happened to it, using one of three markers. The marker is not decoration -- each one is a different
claim, and the lint holds each claim to its own standard:

  ✅  IT IS HERE          -> the file must exist. A row claiming presence for a missing file fails.
  ⏳  IT LANDS LATER      -> the line must name an OPEN phase (see OPEN_LANDINGS). Naming a phase
                             that has already closed fails, and so does a ⏳ on a file that has
                             since arrived -- a manifest that rots is a manifest nobody trusts.
  ⛔  IT IS NOT COMING    -> accepted, and counted. Naming an absence is a real answer; this repo
                             already prefers it to silence (see the "NOT missing" table in
                             `.claude/skills/ingest/SKILL.md`).

IN A TABLE'S STATUS COLUMN the words do the same work as the markers -- `lands in` / `lands with` /
`ships in` count as ⏳, and `not shipped` / `does not ship` / `not owed` / `never ships` count as ⛔ --
because the manifest tables were written that way before this lint existed. IN PROSE they do not:
an ordinary sentence says "lands in" about all sorts of things, and one of them (a planning rule
reading "...or lands in this block") would have silently excused every path on its line. In prose,
use the marker.

A marker accounts for every target backticked in ITS OWN PARAGRAPH -- the marked line plus the lines
it wraps onto -- and it accounts for them EVERYWHERE IN THAT FILE. So one banner at the top can cover
a name the document uses twenty times below. In a table, a row is exactly one claim (rows do not
wrap), and the targets claimed are those in the FIRST CELL HOLDING ANY: that is the subject column of
both table shapes here, and a path in a later cell is being explained, not promised.

The "this has landed, the line still defers it" check reads a TIGHTER scope -- the marker's own line
only. A deferral paragraph usually says what to use meanwhile, and what you use meanwhile is here;
counting that as a stale promise would make the check fire on every well-written banner.

WHAT THIS DELIBERATELY DOES NOT CHECK -- stated because a silent limit reads as coverage:

  * BARE FILENAMES. `pad_archive.py` with no directory in front of it. Measured on 2026-08-11: 111
    distinct bare names in these documents, 67 of which match no file here -- and nearly all 67 are
    placeholders (`<slug>.plan.md`), files under the person's own notes (`brief.md`, `canon.md`), or
    names being discussed rather than pointed at. Checking them would produce sixty-odd findings
    that mean nothing, and a check that cries wolf is one somebody turns off. Write the path if you
    want the guarantee.
  * ANYTHING OUTSIDE .md. Docstrings and comments name paths too; those are read by people already
    inside the code, who can see whether the file is there.
  * WHETHER THE CITATION IS TRUE. That `system/tools/journal.py` exists is checkable; that it does
    what the sentence claims is not.

Exit: 0 clean * 1 drift (the failures are named) * 2 bad arguments * 4 could not read the tree.
"""
import argparse
import glob as globmod
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "shared", "emit"))
from verdicts import CANNOT_READ, print_cannot_read           # noqa: E402

# ─────────────────────────────────────────────────────────────────────────────────────────────────
# THE CONFIG — four lists. Each one is an admission, so each one carries its reason.
# ─────────────────────────────────────────────────────────────────────────────────────────────────

# Phases whose files have not landed yet. A ⏳ line must name one of these.
#
# THIS IS THE MAINTENANCE POINT: when a phase closes, DELETE its label here. The next run then names
# every row still waiting on it -- which is precisely the set of promises that phase was supposed to
# keep and did not. Leaving a closed label in place converts the lint into a rubber stamp.
OPEN_LANDINGS = {
    "phase 3": "the remaining skills",
    "phase 4": "the author's own cutover",
    "phase 5": "cleanup and the final gate",
    "unruled": "cited by something shipped, on no ship list, awaiting a decision — a DEBT, not a pass",
}

# Paths that read like repo paths and are not. The notes folder has a `system/` of its own; these
# three live there. Without this list the lint would demand that a person's journal be committed to
# a public repository, which is the exact opposite of what everything else here enforces.
DATA_PATHS = {
    "system/journal.md": "the person's journal, under their notes folder",
    "system/journal": "the journal's rotated monthly segments",
    "system/project-registry.md": "the person's project registry, under their notes folder",
}

# Documents whose citations point somewhere other than this repository, by their own declaration.
# The file must say so where a reader will see it; the line number here is that banner.
EXEMPT_FILES = {
    ".claude/skills/ingest/SPEC.md":
        "banner at :24-27 — it is a build record as well as a spec, and its file references are the "
        "provenance of decisions in the author's own project tree, never part of what ships",
}

# Scripts living in system/hooks/ that are NOT registered in settings.json, and correctly so.
# Without this list, every one of them would have to be either registered (wrong -- they are not
# hooks) or moved (wrong -- they belong beside the hooks whose state they read).
UNREGISTERED_OK = {
    "pm_flag.sh": "a command-line tool the skills call directly (arm/status/clear), not a hook",
    "skill_anchor.sh": "same — the arming half; `skill_anchor_inject.sh` is the registered hook",
    "numbers_flag.sh": "same — `/calculate` calls it directly; `inject_compute_mechanically.sh` is "
                       "the registered hook that reads what it writes",
    "altitude_flag.sh": "same — `/altitude` calls it directly; `inject_work_altitude.sh` is the "
                        "registered hook that reads what it writes",
    "throughline_flag.sh": "same — `/throughline` arms and clears it directly; "
                           "`guard_throughline_write_scope.sh` is the registered hook it switches",
    "scratch_flag.sh": "same — a skill arms it when it opens a scratchpad; `system/statusline.sh` "
                       "is what reads it, and a status bar is not a hook",
}

# A backticked `/word` is usually a skill here — but not always, and neither of these is ours to
# ship: the harness's own commands, and the top of a filesystem path.
HARNESS_COMMANDS = {"clear", "config", "workflows", "compact", "help", "model", "resume"}
# `sbin` is here for the same reason as `bin`: a document discussing cron's minimal PATH writes
# `/sbin` and `/usr/sbin`, and without this the lint reads those as citations of skills nobody has.
FILESYSTEM_ROOTS = {"tmp", "dev", "etc", "var", "usr", "bin", "sbin", "opt", "home", "mnt", "proc",
                    "srv", "run", "lib", "sys"}

# Directories never scanned. `memory/` is the person's own material and is not ours to lint.
# ⛔ `data` AND `memory` ARE THE PERSON'S OWN MATERIAL — NEVER LINT THEM (data added 2026-08-12).
# This linter checks that paths cited in OUR documentation actually exist here. The person's notes are
# not our documentation: a path they mention in their own file is a fact about their world, not a broken
# citation in ours, and there is nothing for anyone to "fix".
#
# WHY IT REGRESSED. Under the old layout their notes lived OUTSIDE the repo, so the walk could never
# reach them and only `memory` needed skipping. The 2026-08-12 layout change moved their data to `data/`
# INSIDE the repo — gitignored, but this walks the filesystem, not the git index. The first real ingest
# put 17 of their files here and the pre-commit hook then refused the very next commit, citing paths from
# inside their own notes. Every ingest armed a landmine for the next commit.
#
# ⚠ Keep this in step with `.gitignore`: anything there that holds the person's material belongs here too.
SKIP_DIRS = {".git", "data", "memory", ".venv", "node_modules", "__pycache__"}

# ─────────────────────────────────────────────────────────────────────────────────────────────────

BACKTICK = re.compile(r"`([^`\n]+)`")
LINE_ANCHOR = re.compile(r":\d+(?:-\d+)?$")
SKILL_REF = re.compile(r"^/([a-z][a-z0-9][a-z0-9-]*)$")
# A span holding any of these is a template, a variable or a command line, not a literal path.
PLACEHOLDER = re.compile(r"[$<>{}|()\\\[\]…]")

PRESENT, DEFERRED, DECLINED = "present", "deferred", "declined"
DEFER_PHRASES = ("lands in", "lands with", "ships in")
DECLINE_PHRASES = ("not shipped", "does not ship", "not owed", "never ships")


def claim_kind(line):
    """Which of the three claims, if any, this line makes. ✅ wins over the others when a line
    somehow carries two, because presence is the one claim that is checkable against disk.

    THE WORDED FORMS ONLY COUNT IN A TABLE'S LAST CELL. Ordinary prose says "lands in" about all
    sorts of things -- the measured false positive was a planning rule reading "nothing vanishes...
    or lands in this block", which would have quietly excused every path named on that line. A
    status column is a declaration; a sentence is not. In prose, use the marker."""
    if "✅" in line:
        return PRESENT
    if "⏳" in line:
        return DEFERRED
    if "⛔" in line:
        return DECLINED
    status = ""
    if line.lstrip().startswith("|"):
        cells = line.strip().strip("|").split("|")
        status = cells[-1].lower() if len(cells) > 1 else ""
    if any(p in status for p in DEFER_PHRASES):
        return DEFERRED
    if any(p in status for p in DECLINE_PHRASES):
        return DECLINED
    return None


def targets_on(line):
    """The backticked spans a line CLAIMS, raw.

    In a table row that is the FIRST CELL HOLDING ANY -- which is the subject column in both table
    shapes here: a manifest names the file in column 1 and explains it in column 2, while a routing
    table names a category in column 1 and the files to read in column 2. Later cells are prose
    about the row, and a path named in an explanation is being discussed, not promised."""
    if line.lstrip().startswith("|"):
        for cell in line.strip().strip("|").split("|"):
            if "`" in cell:
                line = cell
                break
        else:
            line = ""
    return [s.strip() for s in BACKTICK.findall(line)]


NEW_BLOCK = re.compile(r"^\s*(?:>\s*)*(?:[-*+]\s|\d+\.\s|\||#)")


def continues_claim(line):
    """Is this line a wrapped continuation of the claim above it? Anything that opens a new block --
    a blank line, a new bullet, a table row, a heading, or a fresh marker -- ends the claim."""
    if not line.strip().strip(">").strip():
        return False
    if NEW_BLOCK.match(line):
        return False
    return claim_kind(line) is None


def normalise(span):
    """A backticked span -> the path it names, or None if it does not name one.

    Handles the three shapes these documents actually use: a path with a line anchor
    (`tag.py:138-160`), a path followed by arguments (`pm_flag.sh status`), and a plain path."""
    span = span.strip()
    if not span:
        return None
    span = span.split()[0]                       # `pm_flag.sh status` -> `pm_flag.sh`
    if PLACEHOLDER.search(span):
        return None                              # `<slug>.plan.md`, `$T/tag.py`, `a | b`
    span = LINE_ANCHOR.sub("", span)             # `tag.py:138-160` -> `tag.py`
    return span or None


def repo_tops(root):
    """The top-level directories of this repository, read from disk rather than hardcoded — so a
    new one is covered the day it appears, and a renamed one stops being checked the same day."""
    return {d for d in os.listdir(root)
            if os.path.isdir(os.path.join(root, d)) and d not in SKIP_DIRS and not d.startswith(".")
            } | {".claude"}


def is_repo_path(span, tops):
    head = span.split("/")[0]
    return "/" in span and head in tops


# ⭐ THE BLIND SPOT THIS CLOSES, found 2026-08-11. `is_repo_path` only recognises a citation whose
# FIRST SEGMENT is a real top-level directory OF THIS REPO. A path under the person's notes folder
# usually is not: this repo has no `state/`, no `records/`, no `canon/`, no `plans/`. So every
# citation written as a bare `state/telos.md` or `records/research/x.md` fell through BOTH branches
# and was never checked at all -- neither as a repo path (wrong head) nor as anything else.
#
# That is not a small gap here. Those are precisely the paths this migration MOVED, so they are the
# ones most likely to be stale, and a citation of a file that ships in neither migration read as
# perfectly fine. `state/telos.md` sailed through exactly that way.
#
# The fix is not to resolve them -- they live on a machine this lint cannot see, and demanding that
# a person's journal be committed to a public repository is the opposite of what everything else
# here enforces. The fix is to demand they be WRITTEN so a reader can tell: `<notes>/state/...`.
# A path with that prefix is data, and is counted and skipped. A path without it, whose head is one
# of the data roots below, is a citation nobody can classify -- which is the finding.
# ⚠ `canon/` AND `records/` ARE DELIBERATELY NOT HERE, and leaving them in was a mistake worth
# recording. Both are commonly written RELATIVE to a folder already established in the sentence —
# "read its `canon/purpose.md`", "this project's own `records/`" — where the leading segment is not
# a root at all. Treating them as roots produced a banner on `docs/data-layout.md` asserting that
# `canon/purpose.md` was a record in somebody's private notes, which is the opposite of true: it is
# the layout this repo builds. A check that makes a document lie to satisfy it is worse than the gap
# it closed. The four below only ever appear anchored.
DATA_ROOTS = {
    "state": "projects, briefs, open loops",
    "plans": "plans are data, not repo files",
    "councils": "advisor rosters",
    "config": "your own identifiers",
}
NOTES_PREFIXES = ("<notes>/", "<data>/", "$NOTES/", "{notes}/")


# Only a specific FILE counts. `records/insights/` inside a paragraph about the six record types is
# a type NAME, not a claim that a file is somewhere -- and flagging those produced 150-odd findings
# that mean nothing, which is how a check gets switched off. A path ending in a real extension is
# claiming a file exists; a bare directory shape is describing a layout. Measured on 2026-08-11: the
# narrow rule keeps the finding that started this (`state/telos.md`, a file in neither migration)
# and drops every one of the shape-only hits.
_FILEY = (".md", ".py", ".sh", ".json", ".yaml", ".yml", ".txt", ".jsonl")


def data_root_shape(span):
    """UNPREFIXED if it names a specific file under a data root without saying so, PREFIXED if the
    prefix is there, else None."""
    for pre in NOTES_PREFIXES:
        if span.startswith(pre):
            return "PREFIXED"
    head = span.split("/")[0]
    if "/" in span and head in DATA_ROOTS and span.endswith(_FILEY):
        return "UNPREFIXED"
    return None


def resolves(root, path):
    full = os.path.join(root, path)
    if "*" in path:
        return bool(globmod.glob(full))
    return os.path.exists(full)


def markdown_files(root):
    out = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if f.endswith(".md") and not f.endswith(".bak"):
                out.append(os.path.relpath(os.path.join(base, f), root))
    return sorted(out)


class Finding(object):
    def __init__(self, where, what, why, fix):
        self.where, self.what, self.why, self.fix = where, what, why, fix

    def render(self):
        return "  %s\n      %s — %s\n      → %s" % (self.where, self.what, self.why, self.fix)


def open_landing_named(text):
    low = text.lower()
    for label in OPEN_LANDINGS:
        if label in low:
            return label
    return None


def lint_paths_and_skills(root, findings, counts):
    tops = repo_tops(root)
    skills_dir = os.path.join(root, ".claude", "skills")
    have_skills = set(os.listdir(skills_dir)) if os.path.isdir(skills_dir) else set()

    seen_stale = set()
    for rel in markdown_files(root):
        if rel in EXEMPT_FILES:
            counts["exempt_files"] += 1
            continue
        try:
            with open(os.path.join(root, rel), encoding="utf-8") as fh:
                lines = fh.readlines()
        except Exception as e:                    # a FUSE mount throws things that are not OSError
            print_cannot_read("%s unreadable (%s)" % (rel, e.__class__.__name__))
            return CANNOT_READ

        # Pass 1 — collect this file's claims, so a banner at the top can cover the whole file.
        #
        # A claim runs to the END OF ITS PARAGRAPH, not the end of its line. Prose wraps at a hundred
        # columns, and the first draft of this lint made a marked line account only for itself --
        # which failed three of its own banners, each because a path had wrapped one line below its
        # ⛔. A rule that the person writing the fix keeps breaking is a badly drawn rule. A table row
        # is still exactly one claim: rows do not continue.
        claims, own_line = {}, {}
        n = 0
        while n < len(lines):
            n += 1
            line = lines[n - 1]
            kind = claim_kind(line)
            if not kind:
                continue
            first = n
            block, text = list(targets_on(line)), line.strip()
            if not line.lstrip().startswith("|"):
                while n < len(lines) and continues_claim(lines[n]):
                    n += 1
                    block += targets_on(lines[n - 1])
                    text += " " + lines[n - 1].strip()
            for span in block:
                key = normalise(span)
                if key:
                    claims.setdefault(key, (kind, first, text))
            # The STALE check reads this tighter map instead. A deferral paragraph often mentions
            # what you should use MEANWHILE -- which is here, and is not what the paragraph defers.
            # Forgiving where forgiveness costs a missing file nobody promised; strict where the
            # finding is "this line is out of date".
            for span in targets_on(line):
                key = normalise(span)
                if key:
                    own_line.setdefault(key, (kind, first, line.strip()))

        # Pass 2 — every citation, held to its claim.
        for n, line in enumerate(lines, 1):
            for span in BACKTICK.findall(line):
                key = normalise(span)
                if not key:
                    continue
                skill = SKILL_REF.match(key)
                if skill:
                    name = skill.group(1)
                    if name in HARNESS_COMMANDS or name in FILESYSTEM_ROOTS:
                        continue
                    counts["skill_citations"] += 1
                    exists = name in have_skills
                    target = ".claude/skills/%s/" % name
                elif data_root_shape(key) == "PREFIXED":
                    counts["data_paths"] += 1
                    continue
                elif data_root_shape(key) == "UNPREFIXED":
                    counts["path_citations"] += 1
                    exists = False
                    target = key
                elif is_repo_path(key, tops):
                    if key.rstrip("/") in DATA_PATHS:
                        counts["data_paths"] += 1
                        continue
                    counts["path_citations"] += 1
                    exists = resolves(root, key)
                    target = key
                else:
                    continue

                claim = claims.get(key)
                where = "%s:%d" % (rel, n)

                if exists:
                    claim = own_line.get(key)
                    if claim and claim[0] == DEFERRED:
                        # Keyed on the CLAIM, not on the citation: one stale row is one finding,
                        # however many times the file goes on to mention what it defers.
                        stale = (rel, claim[1], key)
                        if stale not in seen_stale:
                            seen_stale.add(stale)
                            findings.append(Finding(
                                "%s:%d" % (rel, claim[1]), "`%s` HAS LANDED, the line still defers it" % key,
                                "a manifest that describes the past is one nobody checks against the present",
                                "change that line's status to ✅"))
                    else:
                        counts["resolved"] += 1
                    continue

                if claim is None:
                    findings.append(Finding(
                        where, "`%s` does not exist here" % target,
                        "nothing on this line says what happened to it",
                        "bring the file, or mark it ✅ / ⏳ <open phase> / ⛔ with the reason — the "
                        "marker must be on the SAME LINE as the path, so write one per line"))
                elif claim[0] == PRESENT:
                    findings.append(Finding(
                        "%s:%d" % (rel, claim[1]), "`%s` is claimed ✅ here and is NOT here" % target,
                        "the one claim a reader has no reason to doubt",
                        "bring the file, or change the claim to ⏳/⛔"))
                elif claim[0] == DEFERRED:
                    label = open_landing_named(claim[2])
                    if label is None:
                        findings.append(Finding(
                            "%s:%d" % (rel, claim[1]), "`%s` is deferred to a landing that is not open" % target,
                            "that phase has closed, or none was named — the promise has no date left",
                            "name an open phase (%s), or mark it ⛔"
                            % ", ".join(sorted(OPEN_LANDINGS))))
                    else:
                        counts["deferred"] += 1
                        counts.setdefault("by_landing", {}).setdefault(label, []).append(target)
                else:
                    counts["declined"] += 1


def lint_hooks(root, findings, counts):
    settings_rel = ".claude/settings.json"
    settings = os.path.join(root, settings_rel)
    if not os.path.exists(settings):
        print_cannot_read("%s does not exist — nothing to check registration against" % settings_rel)
        return CANNOT_READ
    try:
        with open(settings, encoding="utf-8") as fh:
            raw = fh.read()
        json.loads(raw)                            # parse for validity; scan the text for paths
    except Exception as e:
        print_cannot_read("%s is not readable JSON (%s)" % (settings_rel, e))
        return CANNOT_READ

    registered = set(re.findall(r"\$\{CLAUDE_PROJECT_DIR\}/([^\\\"\s]+)", raw))
    for path in sorted(registered):
        counts["registrations"] += 1
        if os.path.exists(os.path.join(root, path)):
            counts["resolved"] += 1
        else:
            findings.append(Finding(
                settings_rel, "`%s` is registered and is not on disk" % path,
                "the harness will try to run it every session and fail quietly",
                "add the file, or remove the registration"))

    hooks_dir = os.path.join(root, "system", "hooks")
    if not os.path.isdir(hooks_dir):
        return 0
    # Non-recursive on purpose: system/hooks/tests/ holds tests, and a test is not a hook.
    for name in sorted(os.listdir(hooks_dir)):
        if not name.endswith(".sh") or not os.path.isfile(os.path.join(hooks_dir, name)):
            continue
        counts["hook_files"] += 1
        if any(r.endswith("/" + name) or r == "system/hooks/" + name for r in registered):
            counts["resolved"] += 1
        elif name in UNREGISTERED_OK:
            counts["declined"] += 1
        else:
            findings.append(Finding(
                "system/hooks/%s" % name, "on disk, registered nowhere, declared nowhere",
                "an unregistered hook never fires — and reads as a control that exists",
                "register it in %s, or add it to UNREGISTERED_OK in this lint with the reason"
                % settings_rel))
    return 0


def main(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    default_root = os.path.dirname(os.path.dirname(here))     # system/tools/ -> repo root
    ap = argparse.ArgumentParser(description="Prove every file, skill and hook these documents name is here.")
    ap.add_argument("--root", default=default_root,
                    help="repository root (default: this script's own repo, never the cwd)")
    ap.add_argument("--quiet", action="store_true", help="print nothing when clean")
    args = ap.parse_args(argv)

    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print_cannot_read("no such directory: %s" % root)
        return CANNOT_READ

    findings = []
    counts = {"path_citations": 0, "skill_citations": 0, "registrations": 0, "hook_files": 0,
              "resolved": 0, "deferred": 0, "declined": 0, "data_paths": 0, "exempt_files": 0}
    # A check that could not RUN never reports clean: rc 4 is the no-outcome member, distinct from
    # every failure below, which means the check ran and found something.
    for check in (lint_paths_and_skills, lint_hooks):
        rc = check(root, findings, counts)
        if rc:
            return rc

    checked = (counts["path_citations"] + counts["skill_citations"]
               + counts["registrations"] + counts["hook_files"])
    if findings:
        print("\n  ⛔ CITATION DRIFT — %d of %d citations point at something that is not here and is "
              "not accounted for.\n" % (len(findings), checked))
        for f in findings:
            print(f.render())
        print("\n  %d checked · %d resolved · %d deferred · %d declined · %d FAILED\n"
              % (checked, counts["resolved"], counts["deferred"], counts["declined"], len(findings)))
        return 1

    if not args.quiet:
        print("CITATIONS-RESOLVE  %d checked (%d paths · %d skills · %d registrations · %d hook files)"
              % (checked, counts["path_citations"], counts["skill_citations"],
                 counts["registrations"], counts["hook_files"]))
        print("  %d here · %d deferred · %d declined · %d under the notes folder · %d exempt file(s)"
              % (counts["resolved"], counts["deferred"], counts["declined"],
                 counts["data_paths"], counts["exempt_files"]))
        for label, items in sorted(counts.get("by_landing", {}).items()):
            print("    ⏳ %-8s %d — %s" % (label, len(items), ", ".join(sorted(set(items)))))
    return 0


if __name__ == "__main__":
    sys.exit(main())

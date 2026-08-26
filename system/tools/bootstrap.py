#!/usr/bin/env python3
"""bootstrap.py — day one. Makes the four things nothing else makes, and nothing more.

Run once, after you have told the system where your notes live:

    python3 system/tools/bootstrap.py            # uses the folder you already chose
    python3 system/tools/bootstrap.py --root <path>
    python3 system/tools/bootstrap.py --dry-run  # say what it would do, touch nothing

⭐ WHY THIS EXISTS — measured, not assumed (2026-08-11).
/ingest builds every subject folder correctly: a canon file for what stays true, a records folder for
what happened on a date, a stated purpose. What it builds NOTHING of is the layer ABOVE those folders.
Its own phase file says so outright — "there is no registry step at this level" — and a grep across
the whole shipped skill finds zero code that creates a journal, a project registry, or a projects
folder. So a new person's day one is a set of subject folders sitting in an otherwise empty room.

It self-heals in use: /save writes a journal line and creates the journal if it is missing, and the
project tools create a brief when you start one. But nothing puts the shape there FIRST, so the first
session of a new install works against a directory that does not look like the system it is part of.

⭐ THE FOURTH THING — the root canon (added 2026-08-11, task 2.1.1). `docs/data-layout.md` and
`shared/registry.py`'s `Project.canon` property already agree on where it lives — `<notes>/canon.md`,
the plain top-level file, sibling of `desks/<subject>/canon/current.md` but not shaped like it (no
folder, no separate `purpose.md` — one file, one intent line). Nothing before this created it, so
`/read` Step 3.9's `$DATA/canon.md` line and `canon_conflict_scan.py`'s single-file mode had a path
with nothing at it. This ships the file EMPTY of canon lines, carrying only its own purpose — the
altitude bar for what belongs here — so PHASE 4.5 has a floor to write onto instead of open air.

⛔ AND NOTHING ELSE. It is very tempting to have this scaffold "a sensible starting structure" — some
subject folders, an example note, a template. Do not. Which subjects a person's life divides into is
theirs to discover, and handing them a guess teaches them that the guess is the answer. The same
reasoning that keeps a topic vocabulary out of this repo keeps starter folders out of this script.
The root canon is no exception: its FRAME ships (purpose + heading), its CONTENT does not — that is
earned, one line at a time, by a later human-confirmed act, never guessed here.

Never clobbers. Run it as often as you like; anything already there is left exactly as it is.
"""

import argparse
import os
import sys

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "shared"))

JOURNAL = "system/journal.md"
REGISTRY = "system/project-registry.md"
# The project folder. A project is a FOLDER named exactly its slug, holding brief.md +
# records/ + canon/ (docs/data-layout.md). The older flat shape, state/briefs/<slug>.md,
# stays READABLE forever but is never created — an empty folder nothing writes to teaches
# a shape that does not exist, which is the exact thing this file refuses to do elsewhere.
BRIEFS = "state/projects"
# The root canon — NOT under system/ or state/. `docs/data-layout.md`'s shape diagram and
# `shared/registry.py`'s `Project.canon` (`os.path.join(self.root, "canon.md")` for the rootless
# case) already agree: it sits directly at the notes root, beside `system/`, `state/`, `desks/` —
# the one file every one of those folders' canon defers up to. Picking a new path here would
# contradict two files that already point at this one; this just makes the pointer real.
ROOT_CANON = "canon.md"

# Deliberately thin. A one-line title so a human opening the file knows what it is, and NOT a schema —
# the row format belongs to the tools that write these, not to the thing that creates them empty.
JOURNAL_BODY = """# Journal

Appended to as you work — what happened, when, and why. Nothing here is written by hand; the tools
add to it. It is the backstop: if something was not filed anywhere else, it is in here.
"""

REGISTRY_BODY = """# Projects

One row per project, added when a project starts. This is what lets a cold session six weeks from now
find a project you have half-forgotten, by name, without searching the whole folder.
"""

# The admission bar, not a done-when — this is what a later phase (PHASE 4.5) reads before it writes
# a line here, and what a cold session reads before it reads anything else. ⛔ NO line count, NO size
# threshold, anywhere in this text — the bound the system enforces is ALTITUDE (does this fact hold
# for every conversation, on any subject?), never a number of lines. That was weighed and rejected:
# `knowledge-altitude.md` §7 bars "NO numeric scoring, NO thresholds" for exactly this kind of file.
ROOT_CANON_BODY = """# Canon

**intent:** only what must be true for EVERY conversation, on ANY subject — your name, how you want
to be spoken to, how this system itself should operate. A cold session loads this file before it
loads anything else, so a line placed here is carried into every conversation that follows, forever.
**not:** something true only within one subject — that belongs one level down, in that subject's own
`canon/current.md`, not here.

Nothing below this line is written by hand at creation. It is earned later, one confirmed line at a
time, off real conversations — never guessed, never pre-filled.

"""


def resolve_root(explicit=None):
    """(path, source) or (None, reason). Uses the one resolver — never guesses, never uses the cwd."""
    if explicit:
        p = os.path.abspath(os.path.expanduser(explicit))
        return (p, "--root") if os.path.isdir(p) else (None, "'%s' is not a directory" % p)
    try:
        import brain_root
    except ImportError as e:
        return None, "cannot import shared/brain_root.py (%s)" % e
    source, path = brain_root.resolve_brain_root()
    if path is None:
        return None, ("no data root set. Tell the system where your notes live first:\n"
                      "    python3 %s --set \"<that folder>\" [--create]"
                      % os.path.join(REPO, "shared", "brain_root.py"))
    return path, source


def bootstrap(root, dry_run=False):
    """Returns (created, existed) as lists of repo-relative paths. Creates nothing else, ever."""
    created, existed = [], []

    briefs = os.path.join(root, BRIEFS)
    if os.path.isdir(briefs):
        existed.append(BRIEFS + "/")
    else:
        created.append(BRIEFS + "/")
        if not dry_run:
            os.makedirs(briefs)

    for rel, body in ((JOURNAL, JOURNAL_BODY), (REGISTRY, REGISTRY_BODY), (ROOT_CANON, ROOT_CANON_BODY)):
        target = os.path.join(root, rel)
        if os.path.exists(target):
            existed.append(rel)
            continue
        created.append(rel)
        if not dry_run:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "w", encoding="utf-8") as f:
                f.write(body)
    return created, existed


SHIM_BODY = (
    '@echo off\r\n'
    # PYTHONUTF8=1 is PEP 540 UTF-8 Mode. Every command in every skill is written `python3 …`, and a
    # huge share of them call the bare `open(path)` with no `encoding=` — 216 of 472 call sites,
    # measured by AST, not grep (T8.2a, 2026-08-13). Without this line, those calls fall back to
    # `locale.getpreferredencoding()`, which on a stock Windows machine is cp1252, not UTF-8. The
    # repo's own docs are full of ⭐ ⛔ — characters, and a student's own material routinely has
    # curly quotes and accented names — so the failure mode is not a clean crash, it is
    # `errors="replace"` in `system/tools/cowork-ingest/intake.py` silently mangling a student's own
    # writing. Forcing UTF-8 Mode here, once, at the one place every `python3` invocation already has
    # to pass through, is the fix — not 216 scattered `encoding=` edits, which is how a class stays
    # broken forever.
    'set PYTHONUTF8=1\r\n'
    # `%~dp0` is the folder this .cmd sits in, so the shim keeps pointing at its own neighbour even
    # if the folder is later moved or renamed. `%*` forwards every argument untouched.
    '"%~dp0python.exe" %*\r\n'
)

# The SAME contract as SHIM_BODY, for Git Bash / MSYS — which does NOT apply PATHEXT to a bare
# word, so `python3.cmd` is invisible to it and `python3` alone is "command not found" even with
# the .cmd sitting on $PATH. That matters because every command block in INSTALL.md is bash, and
# STEP 7.2 promises in as many words that from STEP 8 onward plain `python3` resolves. It does
# not, on the one shell the file actually uses. LF endings and the `#!` are both load-bearing:
# MSYS treats a file starting with a shebang as executable, which is what lets a extensionless
# file answer to a bare word at all.
SHIM_POSIX_BODY = (
    "#!/bin/sh\n"
    "# Companion to python3.cmd, for Git Bash/MSYS. See SHIM_BODY for why PYTHONUTF8 is set here.\n"
    "export PYTHONUTF8=1\n"
    'exec "$(dirname "$0")/python.exe" "$@"\n'
)


def _is_store_alias(path):
    """True for the Microsoft Store App Execution Alias, which is NOT an interpreter.

    ⭐ WHY (2026-08-21). A stock Windows 11 ships a zero-byte `python3.exe` reparse stub in
    `%LOCALAPPDATA%\\Microsoft\\WindowsApps`, early on PATH. Run it and it prints "Python was not
    found; run without arguments to install from the Microsoft Store" and exits. `shutil.which`
    finds it, so the "something else already answers to python3" arm below fired and this function
    created NO shim — on the exact machine that needs one most. Nothing errored: the install
    reported success, and every one of the ~150 skill commands written as the word `python3` then
    hit the Store stub. INSTALL.md STEP 3 TRAP 2 already tells the student to disable these
    aliases; nothing verified they had, and the cost of not checking was silence.

    ⛔ LOCATION ONLY — deliberately NOT "is it zero bytes?". The stub is zero bytes, but so is any
    number of legitimate things, and this answer decides whether we OVERWRITE what we found. A size
    test guesses; the WindowsApps path is what actually makes it a Store alias. Caught by
    test_a_foreign_python3_elsewhere_on_path_is_left_alone, whose foreign interpreter is an empty
    fixture file — a size test called it fake and wrote over it, which is exactly the real-world
    failure that test exists to prevent."""
    try:
        p = os.path.normcase(os.path.abspath(path))
    except (OSError, ValueError):
        return False
    return os.sep + "microsoft" + os.sep + "windowsapps" + os.sep in p


def ensure_python3_shim(dry_run=False):
    """Guarantee that the bare word `python3` resolves on this machine, AND that it runs in UTF-8
    Mode. Windows only.

    ⭐ WHY THE SHIM EXISTS (2026-08-12). Every command in every skill is written `python3 …`, one
    convention, literal and copy-pasteable. That word is true on macOS and Linux and FALSE on a
    standard Windows install: python.org ships `python.exe` and no `python3.exe`, and INSTALL.md's
    own Windows fix — disabling the Microsoft Store execution aliases in STEP 3, TRAP 2 — removes
    the only `python3.exe` the machine had. So the install instructions actively created the
    breakage, and every one of the ~150 skill commands failed on the word.

    Rather than branch every command by platform, or make the model substitute a token 150 times,
    the install restores what the Store alias used to provide: a `python3.cmd` beside the real
    interpreter. `sys.executable`'s own folder is the right home for it — it is per-user and already
    on PATH, because the installer put it there.

    ⭐ WHY THE SHIM ALSO SETS PYTHONUTF8 (T8.2a, 2026-08-13). This is the ONE place every `python3`
    invocation on Windows already has to resolve through — every skill command, every internal
    `subprocess.run(["python3", ...])`, all of it. Setting UTF-8 Mode here, instead of adding
    `encoding="utf-8"` to 216 individual `open()` calls, means the fix actually fires for every call
    site at once, including ones written after this file was. A machine that already has an OLDER
    shim from before this fix is upgraded in place, not left alone — see the `upgraded` status below
    — because `UPDATE.md` re-runs this script on every `git pull`, and an update that cannot reach an
    already-installed machine is not a fix, it is a note to new installs only.

    Returns (status, detail) with status in {"not-needed", "already", "created", "upgraded",
    "would-create", "would-upgrade", "refused"}. ⛔ A refusal NEVER fails the install: it is reported
    with the manual fix, because a person who cannot write one file still has a working tool
    everywhere except that word."""
    if os.name != "nt":
        return "not-needed", "not Windows — `python3` is the real name here, in UTF-8 by default"

    import shutil
    target_dir = os.path.dirname(os.path.abspath(sys.executable))
    shim = os.path.join(target_dir, "python3.cmd")

    # TWO files, because two shells have to answer to the same word: cmd/PowerShell resolve the
    # .cmd via PATHEXT, Git Bash resolves only the extensionless one. INSTALL.md's command blocks
    # are bash, so shipping just the .cmd left the file's own instructions broken on Windows.
    posix_shim = os.path.join(target_dir, "python3")
    wanted = ((shim, SHIM_BODY), (posix_shim, SHIM_POSIX_BODY))
    ours = {os.path.normcase(os.path.abspath(p)) for p, _ in wanted}

    found = shutil.which("python3")
    if found and _is_store_alias(found):
        found = None        # a Store stub is not an interpreter — see _is_store_alias
    if found and os.path.normcase(os.path.abspath(found)) not in ours:
        # Something else already answers to `python3` — WSL, msys, a real python3.exe elsewhere on
        # PATH. Not ours to rewrite; its encoding behaviour is that install's own business.
        return "already", "`python3` already resolves on PATH (%s, not managed here)" % found

    def _state(path):
        """(needs_writing, is_an_upgrade). An upgrade is a file of ours predating PYTHONUTF8."""
        if not os.path.exists(path):
            return True, False
        try:
            current = open(path, encoding="ascii").read()
        except OSError:
            current = ""
        return ("PYTHONUTF8" not in current), ("PYTHONUTF8" not in current)

    cmd_write, cmd_upgrade = _state(shim)
    posix_write, posix_upgrade = _state(posix_shim)

    if not cmd_write and not posix_write:
        return "already", shim

    # ⛔ THE .cmd GOVERNS THE REPORTED VERB AND THE DETAIL, even though two files are written now.
    # That is a CONTRACT, not a preference: test_bootstrap.py's TestPython3ShimUTF8 asserts
    # `detail == python3.cmd` on a fresh machine and `upgraded` for a pre-UTF8 .cmd — and it is the
    # right contract, because a stale .cmd is a machine whose `python3` silently mangles the
    # person's own accented names and curly quotes. Adding a second file must not downgrade that
    # report to "created" and bury the .cmd path in a concatenation; the companion is additive.
    if cmd_write:
        verb, verb_dry = ("upgraded", "would-upgrade") if cmd_upgrade else ("created", "would-create")
        detail = shim
    else:
        verb, verb_dry = ("upgraded", "would-upgrade") if posix_upgrade else ("created", "would-create")
        detail = posix_shim

    todo = [(p, b) for p, b, w in ((shim, SHIM_BODY, cmd_write),
                                   (posix_shim, SHIM_POSIX_BODY, posix_write)) if w]

    if dry_run:
        return verb_dry, detail

    written, failed = [], []
    for path, body in todo:
        try:
            # newline="" keeps each body's own endings: CRLF for the .cmd, LF for the sh shim,
            # which MSYS requires and which a CRLF-mangled shebang would break.
            with open(path, "w", encoding="ascii", newline="") as f:
                f.write(body)
            written.append(path)
        except OSError as e:
            failed.append((path, e))

    if failed and not written:
        path, e = failed[0]
        return "refused", (
            "could not write %s (%s).\n"
            "     Not fatal. Either re-run this step from a shell that can write there, or create\n"
            "     that file by hand with these three lines:\n"
            "         @echo off\n"
            "         set PYTHONUTF8=1\n"
            '         "%%~dp0python.exe" %%*' % (path, e))
    if failed:
        # Partial success is still a working `python3` in at least one shell — say which failed
        # rather than claiming the whole step succeeded.
        return verb, "%s (could not write %s: %s)" % (detail, failed[0][0], failed[0][1])
    return verb, detail


def main(argv=None):
    ap = argparse.ArgumentParser(description="create the four top-level things nothing else creates")
    ap.add_argument("--root", help="the folder your notes live in (default: the one already chosen)")
    ap.add_argument("--dry-run", action="store_true", help="say what would happen; touch nothing")
    a = ap.parse_args(argv)

    root, source = resolve_root(a.root)
    if root is None:
        print("REFUSED: %s" % source)
        return 1

    created, existed = bootstrap(root, dry_run=a.dry_run)
    print("Your notes: %s  (from: %s)" % (root, source))
    verb = "would create" if a.dry_run else "created"
    if created:
        for p in created:
            print("  %s %s" % (verb, p))
    for p in existed:
        print("  already there, left alone: %s" % p)
    if not created:
        print("Nothing to do — the shape is already in place.")

    # The one machine-shaped thing this step owns besides the folders: making `python3` a real word
    # on Windows, AND making it read files as UTF-8 instead of the machine's default codepage.
    # Silent on macOS and Linux — the word already resolves there, in UTF-8, without help.
    status, detail = ensure_python3_shim(dry_run=a.dry_run)
    if status == "created":
        print("  made `python3` work on this machine (and read files as UTF-8): %s" % detail)
    elif status == "upgraded":
        print("  fixed `python3` to read files as UTF-8 — it was silently mangling special "
              "characters before: %s" % detail)
    elif status == "would-create":
        print("  would make `python3` work on this machine (and read files as UTF-8): %s" % detail)
    elif status == "would-upgrade":
        print("  would fix `python3` to read files as UTF-8: %s" % detail)
    elif status == "refused":
        print("  ⚠ `python3` is not a working command here, and I could not fix it:\n     %s" % detail)
    return 0


if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "system", "tools")))
    from utf8_stdio import force_utf8_stdio
    force_utf8_stdio()
    sys.exit(main())

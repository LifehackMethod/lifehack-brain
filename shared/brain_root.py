#!/usr/bin/env python3
"""brain_root.py — THE one root variable. Every data path in this system resolves through here.

WHERE THE AI BRAIN LIVES, and how it gets set up, is `INSTALL.md`'s subject and INSTALL.md is the
authority on it. This module does not restate it. What this module owns is the mechanical question —
on this machine, which folder is the AI Brain? — and it is asked once, remembered forever, and
resolved through the ordered routes below. Never a default, never a fallback, never a guess.

LIFTED, NOT INVENTED (migration T0.1, 2026-08-11): this is the resolver that has been running inside
`system/tools/cowork-ingest/pipeline.py` since 2026-08-08 — moved out verbatim so that every tool,
not just the ingest pipeline, resolves the data root the same way. `pipeline.py` now imports it, so
there is exactly one implementation and it is this one.

Usage as a library:
    import sys, os
    sys.path.insert(0, "<repo>/shared")
    import brain_root
    source, path = brain_root.resolve_brain_root()
    if path is None: ...stop and name the fix; NEVER guess...

Usage as a CLI:
    python3 shared/brain_root.py                      # print RESOLVED: <path>  (source: ...)
    python3 shared/brain_root.py --quiet              # print just the path; exit 1 if NOT-SET
    python3 shared/brain_root.py --set <path>         # remember it, forever
    python3 shared/brain_root.py --set <path> --create
"""

import argparse
import os
import sys

# ── THE BRAIN ROOT: asked once, remembered forever (the author 2026-08-08) ─────────────────────────
# "It's got to be pointed at a specific folder at the very beginning… that needs to be recorded inside
# the skill, and remembered into the future. So when it gets used on an ongoing basis, it's not throwing
# all the files that come out of it in some random place." Before this, the drivers GUESSED the root by
# globbing a cloud-drive path — fine for its original author, wrong for
# anyone on Dropbox, OneDrive, or a plain local folder. This is a REMEMBERED DECISION, not a parameter.
#
# Resolution order, exactly — resolve_brain_root() returns the FIRST route below that names a real
# directory, and the source string it returns is in parentheses: (1) $LIFEHACK_ROOT, if set and a real
# directory ("env"). (2) this repo's own `.brain-root` pointer file, located from THIS FILE's position
# ("repo-pointer"). (3) the persisted file ~/.config/lifehack/brain-root — this system's EXISTING config
# home (sentinel-paused-sources and claude-oauth-token already live there; this is not a second
# location) ("persisted"). (4) the legacy Drive glob — BACK-COMPAT ONLY, set via INGEST_LEGACY_ROOT_GLOB,
# so an existing corpus keeps resolving ("legacy-glob"). (5) otherwise NOT-SET. Closed outcome set
# {RESOLVED, NOT-SET}; NOT-SET is the no-outcome member and must NEVER fall through to a guess, a
# default, or the cwd — every caller checks for it and stops, naming the fix.
BRAIN_ROOT_ENV = "LIFEHACK_ROOT"
BRAIN_ROOT_CONFIG = os.path.expanduser("~/.config/lifehack/brain-root")
# Step (4), back-compat only, and DELIBERATELY not hardcoded: the original owner exports
# INGEST_LEGACY_ROOT_GLOB so an existing corpus keeps resolving where it always did. Unset on
# every other machine, which makes step (4) a no-op rather than a stranger's path. Empty is
# skipped entirely in resolve_brain_root below.
BRAIN_ROOT_LEGACY_GLOB = os.path.expanduser(os.environ.get("INGEST_LEGACY_ROOT_GLOB", ""))
# Step (2), NEW 2026-08-17 (Option B ruling): the repo carries its OWN pointer. One line, absolute
# path, at the repo root, gitignored. Located via THIS FILE's position (repo root = parent of
# shared/), NEVER via cwd — so two clones on one machine each resolve their own brain, and the
# pointer travels with the folder into environments that cannot see the machine's HOME (Cowork).
REPO_POINTER_NAME = ".brain-root"

def harness_root():
    """Absolute path of the Harness / repo folder this file lives in (the parent of shared/).

    Derived from THIS FILE's position, never from cwd — same reason as repo_pointer_path below.
    It is its own function because two callers need it: the pointer file lives here, and --set
    must REFUSE any brain root that lands inside here (see reject_unusable_target)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def repo_pointer_path():
    """Absolute path of this repo's pointer file, derived from this module's own location."""
    return os.path.join(harness_root(), REPO_POINTER_NAME)

def read_repo_pointer():
    """The raw value in the repo pointer file, or None. Like read_persisted, returns the string
    even if the folder no longer exists — callers deciding what --set is about to change need the
    stale value, and resolve_brain_root hides it."""
    fp = repo_pointer_path()
    if not os.path.isfile(fp):
        return None
    try:
        value = open(fp, encoding="utf-8").read().strip()
    except OSError:
        return None
    return value or None


def resolve_brain_root():
    """The one resolver every caller (skill drivers, tests, this CLI) goes through. Returns
    (source, path) with source in {"env", "repo-pointer", "persisted", "legacy-glob"} and path a real directory, OR
    (None, None) for NOT-SET. Never guesses, never defaults to cwd, never invents a path."""
    env = os.environ.get(BRAIN_ROOT_ENV)
    if env and os.path.isdir(env):
        return "env", env
    pointer = read_repo_pointer()
    if pointer and os.path.isdir(pointer):
        return "repo-pointer", pointer
    if os.path.isfile(BRAIN_ROOT_CONFIG):
        try:
            persisted = open(BRAIN_ROOT_CONFIG, encoding="utf-8").read().strip()
        except OSError:
            persisted = ""
        if persisted and os.path.isdir(persisted):
            return "persisted", persisted
    if BRAIN_ROOT_LEGACY_GLOB:          # unset on a fresh install -> step (4) is a no-op, never a guess
        import glob as _glob
        for hit in sorted(_glob.glob(BRAIN_ROOT_LEGACY_GLOB)):
            if os.path.isdir(hit):
                return "legacy-glob", hit
    return None, None


def read_persisted():
    """The RAW value in BRAIN_ROOT_CONFIG, or None. Deliberately NOT `resolve_brain_root()`.

    WHY THE DISTINCTION MATTERS (issue #4, 2026-08-12). `resolve_brain_root()` answers "where do I
    write?" and consults $LIFEHACK_ROOT and the legacy glob to do it. This answers a narrower and
    more dangerous question: "what is `--set` about to overwrite?" The config file is ONE global
    value living outside the repo, so a second install — a re-clone, a second brain, a second person
    on the same machine — silently repoints the first. Reproduced: after install two runs `--set`,
    install one resolves to install two's AI Brain.

    Returns the string even if it no longer exists on disk: a root pointing at a deleted folder is
    exactly the case a caller most needs to report, and `resolve_brain_root()` hides it by returning
    NOT-SET."""
    if not os.path.isfile(BRAIN_ROOT_CONFIG):
        return None
    try:
        value = open(BRAIN_ROOT_CONFIG, encoding="utf-8").read().strip()
    except OSError:
        return None
    return value or None


def looks_like_a_windows_path(raw):
    """True for `G:\\My Drive\\AI Brain`, a `C:` drive letter with forward slashes, or any
    path carrying a backslash.

    On Windows those are real locations. On macOS and Linux — where this tool runs — they are not
    locations at all, just a long filename, and that is the whole failure: os.path.abspath happily
    turns one into a folder INSIDE this repo (reproduced with a real student, 2026-08-18)."""
    s = raw.strip()
    if "\\" in s:
        return True
    return len(s) >= 2 and s[1] == ":" and s[0].isalpha()


def reject_unusable_target(path):
    """The gate --set passes through before it creates, writes, or remembers ANYTHING.

    Returns a plain-English refusal string, or None when the path is a usable target. Every message
    is written to be read out loud to someone who is not technical, and every one of them says what
    to do instead — a refusal that leaves you stuck just gets worked around.

    WHY THIS EXISTS (2026-08-18). A student on Windows could not find their Google Drive, and a
    path of the shape `G:\\My Drive\\AI Brain` was passed to --set on a machine that was not
    Windows. It was accepted as a RELATIVE path, so a folder with that literal name was created
    inside this repo, the whole AI Brain was written into it, and four separate checks afterwards
    all reported success — including the "is it backed up to the cloud?" one, which was matching
    the words "my drive" in the folder's NAME. The install told the student their AI Brain was
    safe in Google Drive. It was inside the code folder, which the instructions say is safe to
    delete. One honest check here and none of that can start."""
    raw = (path or "").strip()
    if not raw:
        return ("REFUSED: no folder was given. Say where the AI Brain should live, as a full path "
                "starting with a / — for example: --set \"$HOME/AI Brain\"")

    if looks_like_a_windows_path(raw):
        return (f"REFUSED: '{raw}' looks like a Windows folder (a drive letter like G:, or "
                f"backslashes).\n"
                f"  This computer is running macOS or Linux, where a place like that does not "
                f"exist — so instead of finding your Google Drive, it would quietly make a NEW "
                f"folder whose name is the words you just typed, in the wrong place.\n"
                f"  On this computer every real folder starts with a / . Open the folder you want "
                f"in Finder or your file manager, copy its real path, and pass that. A Google "
                f"Drive folder here usually looks like:\n"
                f"  $HOME/Library/CloudStorage/GoogleDrive-<your-account>/My Drive/AI Brain")

    expanded = os.path.expanduser(raw)
    if not os.path.isabs(expanded):
        return (f"REFUSED: '{raw}' is not a complete path — it does not start with a / .\n"
                f"  A short name like that means \"inside whatever folder I happen to be in right "
                f"now\", which is almost never where your AI Brain lives, and your notes would end "
                f"up somewhere neither of us meant.\n"
                f"  Give the whole path, from the top. If you can already see the folder in a "
                f"terminal, type `pwd` inside it and use exactly what that prints. For example: "
                f"$HOME/AI Brain")

    # realpath BOTH sides: /tmp is a symlink to /private/tmp on macOS, and a student's Drive folder
    # is very often reached through a symlink too. Comparing the paths as typed misses both.
    target = os.path.realpath(expanded)
    harness = os.path.realpath(harness_root())
    if target == harness:
        return (f"REFUSED: that is the Harness folder itself ({harness}).\n"
                f"  The Harness is the program. Your AI Brain is your writing, and the two have to "
                f"be kept apart — updating or deleting the program must never touch your notes.\n"
                f"  Pick a folder somewhere else and point at that: your Google Drive folder, or a "
                f"plain folder in your home directory such as ~/AI Brain")
    if target.startswith(harness + os.sep):
        return (f"REFUSED: '{target}' is inside the Harness folder ({harness}).\n"
                f"  Your AI Brain must live OUTSIDE it. The Harness is program code that gets "
                f"replaced when you update, and the instructions tell you it is safe to delete — "
                f"so anything kept in there can be wiped without warning, including everything you "
                f"have written.\n"
                f"  Pick a folder somewhere else and point at that: your Google Drive folder, or a "
                f"plain folder in your home directory such as ~/AI Brain")
    return None


def set_brain_root(path, create=False, replace_global=False):
    """`brain-root --set <path>`. REFUSES a nonexistent path unless create=True (then makes it, parents
    included). REFUSES a path that exists but is a FILE (never silently picks its parent dir).

    WRITE SEMANTICS (changed 2026-08-17, after a logged near-miss): --set always writes THIS repo's
    pointer file. It writes the machine-global BRAIN_ROOT_CONFIG only when that file is absent or
    already agrees. A DIFFERENT existing global value is left untouched unless replace_global=True —
    so a confused session running --set can no longer silently repoint another install's brain.
    Returns (ok, message-or-path, global_note) where global_note says what happened to the global.

    REFUSES FIRST, before it creates or writes anything: a Windows-shaped path, a path that is not
    absolute, and any path inside this Harness folder — see reject_unusable_target for the incident
    that put that gate here. --create makes a missing folder, but only once those have passed."""
    refusal = reject_unusable_target(path)
    if refusal:
        return False, refusal, ""
    resolved = os.path.abspath(os.path.expanduser(path))
    if os.path.exists(resolved):
        if not os.path.isdir(resolved):
            return False, f"REFUSED: '{resolved}' exists and is a FILE, not a directory", ""
    else:
        if not create:
            return False, f"REFUSED: '{resolved}' does not exist — pass --create to make it", ""
        os.makedirs(resolved, exist_ok=True)
    # 1) the repo pointer — always
    with open(repo_pointer_path(), "w", encoding="utf-8") as f:
        f.write(resolved + "\n")
    # 2) the global — guarded
    previous = read_persisted()
    if previous and os.path.abspath(previous) != resolved and not replace_global:
        note = (f"GLOBAL UNCHANGED: {BRAIN_ROOT_CONFIG} already points at\n  {previous}\n"
                f"  This repo's own pointer now overrides it HERE, but other installs still use it.\n"
                f"  To repoint the whole machine on purpose: --set \"{resolved}\" --replace-global")
        return True, resolved, note
    os.makedirs(os.path.dirname(BRAIN_ROOT_CONFIG), exist_ok=True)
    with open(BRAIN_ROOT_CONFIG, "w", encoding="utf-8") as f:
        f.write(resolved + "\n")
    note = "global config " + ("replaced (--replace-global)" if previous and os.path.abspath(previous) != resolved else "written")
    return True, resolved, note


NOT_SET_MESSAGE = ("NOT-SET — no $" + BRAIN_ROOT_ENV + ", no " + REPO_POINTER_NAME +
                   " pointer in this repo, no persisted " + BRAIN_ROOT_CONFIG +
                   ", and no legacy Drive folder found. Fix: brain_root.py --set <path> "
                   "(add --create for a new folder).")


def main(argv=None):
    """The same contract as `pipeline.py brain-root`, reachable without the ingest pipeline —
    because the data root is the whole system's variable, not the ingest chain's."""
    ap = argparse.ArgumentParser(description="resolve / persist the one data root everything writes under")
    ap.add_argument("--set", dest="set_path", metavar="PATH",
                    help="record this path as the brain root: writes this repo's .brain-root pointer, and "
                         "touches the machine-global config (" + BRAIN_ROOT_CONFIG + ") only when it is "
                         "absent or already agrees — a differing global needs --replace-global")
    ap.add_argument("--create", action="store_true", help="with --set: create the folder if missing")
    ap.add_argument("--replace-global", action="store_true",
                    help="with --set: allow overwriting a DIFFERENT machine-global root (guarded since 2026-08-17)")
    ap.add_argument("--quiet", action="store_true", help="print only the path; exit 1 if NOT-SET")
    a = ap.parse_args(argv)
    if a.set_path:
        # ⛔ Read BEFORE writing. The overwrite is silent otherwise, and silence is the bug (issue #4).
        previous = read_persisted()
        ok, res, note = set_brain_root(a.set_path, create=a.create, replace_global=a.replace_global)
        if not ok:
            print(res)
            return 1
        verb = "created + " if a.create else ""
        print(f"RESOLVED: {res}  (source: repo-pointer — just {verb}set via --set)")
        print(note)
        if a.replace_global and previous and os.path.abspath(previous) != os.path.abspath(res):
            print(f"⚠ REPLACED the machine-global brain root that was already set: {previous}")
            print("  Anything resolving through the global config now lands here instead.")
            print(f"  To put it back: {os.path.basename(__file__)} --set \"{previous}\" --replace-global")
        return 0
    source, path = resolve_brain_root()
    if path is None:
        if not a.quiet:
            print(NOT_SET_MESSAGE)
        return 1
    print(path if a.quiet else f"RESOLVED: {path}  (source: {source})")
    return 0


if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "system", "tools")))
    from utf8_stdio import force_utf8_stdio
    force_utf8_stdio()
    sys.exit(main())

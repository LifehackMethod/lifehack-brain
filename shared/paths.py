#!/usr/bin/env python3
"""paths.py — every machine-shaped path in this system, answered in ONE place.

WHY THIS EXISTS (2026-08-12). Ten skill files each opened with the same block of shell:

    ROOT="$(cd "$(git rev-parse --show-toplevel)" && pwd)"
    T="$ROOT/system/tools/cowork-ingest"
    DRIVE="$(python3 "$T/pipeline.py" brain-root --quiet)" || exit 1
    MAP="$DRIVE/state/projects/$INGEST_CORPUS/work/corpus-map.json"
    ANCHOR="$HOME/.cache/cowork-ingest/$INGEST_CORPUS/ingest-anchor.txt"

Every value in it is something Python already knew. The shell was re-deriving it, then handing it
back as an argument — which cost us three things at once:

  1. **It made bash a hard dependency.** `$( )`, `&&` and `||` are not PowerShell, and Claude Code
     runs commands through PowerShell on a Windows machine with no Git Bash. A command block that
     only parses under bash is a platform lock, written into a markdown file.
  2. **`$HOME/.cache` and `/tmp` are not real locations on Windows.** They resolve under Git Bash
     because MSYS maps them, and fail everywhere else — the exact class of bug in issue #7.
  3. **Ten copies drift.** The same path logic, restated ten times, is nine chances to disagree.

⛔ **THE RULE THIS MODULE KEEPS: never guess a path.** Anything derived from the brain root returns
None when the root is NOT-SET, exactly as `brain_root.resolve_brain_root()` does. A caller that
receives None must STOP and name the fix. Putting someone's notes somewhere they did not choose is
the failure the whole resolver chain exists to prevent — a default here would reintroduce it
quietly, one layer further down where nobody is looking.

⚠ **Stdlib only, deliberately.** This has to work on a fresh machine before anything is installed,
so no third-party dependency (`platformdirs` and friends) may appear here.

Returns `str`, not `Path`, so these drop straight into the existing `os.path.join` call sites.
"""

import os
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))

# ── The repo, found from this file and nothing else ───────────────────────────────────────────────
# NOT `git rev-parse`: that needs git on PATH and a shell to capture it, and it answers the wrong
# question inside a worktree or a submodule. This file's location IS the answer, and it is correct
# before git exists, with no subprocess and no shell.
REPO_ROOT = os.path.dirname(_HERE)

sys.path.insert(0, _HERE)
import brain_root  # noqa: E402  (path set immediately above, by design)

# The corpus being ingested. One slug per corpus; the default matches what the skills have always
# used, so an existing run keeps resolving to the same folder after this refactor.
CORPUS_ENV = "INGEST_CORPUS"
DEFAULT_CORPUS = "my-corpus"

# The corpus that predates slugging. The skills scoped their legacy fallback to exactly this one, so
# that a BRAND-NEW corpus could never resolve to the original's flatten and silently read someone
# else's chats. That scoping is preserved here verbatim — it is a safety rule, not a convenience.
LEGACY_CORPUS = "cowork-bulk-ingestion"

# Where the cache used to live, literally. Kept as a constant because two functions below have to
# look for it, and because the string is the whole reason they exist.
LEGACY_CACHE = os.path.join(os.path.expanduser("~"), ".cache", "cowork-ingest")


def repo_root():
    """Absolute path to the cloned tool folder. Always answerable; never None."""
    return REPO_ROOT


def tool_dir(*parts):
    """A path inside the repo, e.g. tool_dir("system", "tools", "cowork-ingest")."""
    return os.path.join(REPO_ROOT, *parts)


def corpus_slug():
    """The active corpus slug. Env-overridable so two corpora can be worked separately."""
    return os.environ.get(CORPUS_ENV) or DEFAULT_CORPUS


def brain():
    """(source, path) for the person's data root, or (None, None) for NOT-SET. Never guesses."""
    return brain_root.resolve_brain_root()


def _under_brain(*parts):
    """Join under the brain root, or None if the root is NOT-SET. The None is the whole point:
    it forces the caller to stop rather than writing into an invented folder."""
    _, root = brain_root.resolve_brain_root()
    if not root:
        return None
    return os.path.join(root, *parts)


def corpus_work(slug=None):
    """The corpus's working directory, or None if the brain root is NOT-SET."""
    return _under_brain("state", "projects", slug or corpus_slug(), "work")


def corpus_map(slug=None):
    """`corpus-map.json` — the state machine every phase reads. None if NOT-SET.

    This is the value that used to be threaded through ~30 subcommands as a required `--map`. It is
    fully derivable from the brain root and the corpus slug, so it is now a default rather than an
    argument the caller has to reconstruct in shell."""
    work = corpus_work(slug)
    return os.path.join(work, "corpus-map.json") if work else None


# ── Machine-local scratch and cache — the two that were hardcoded POSIX ───────────────────────────

def cache_dir(*parts):
    """Per-user cache, correct on every platform. Created if missing.

    Replaces `$HOME/.cache/...`, which is a Linux convention that happens to work on macOS and does
    not exist on Windows. Resolution order:
        Windows -> %LOCALAPPDATA%          (falls back to %USERPROFILE%\\AppData\\Local)
        macOS   -> ~/Library/Caches        (the platform's actual answer, not the Linux one)
        else    -> $XDG_CACHE_HOME or ~/.cache
    """
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.path.join(
            os.path.expanduser("~"), "AppData", "Local")
    elif sys.platform == "darwin":
        base = os.path.join(os.path.expanduser("~"), "Library", "Caches")
    else:
        base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    p = os.path.join(base, "lifehack", *parts)
    os.makedirs(p, exist_ok=True)
    return p


def scratch_dir(*parts):
    """Regenerable working space, correct on every platform. Created if missing.

    Replaces the hardcoded `/tmp/...` in the skills. `tempfile.gettempdir()` already honours TMPDIR
    on Unix and TEMP/TMP on Windows, so this is the stdlib answering a question the skills were
    answering with a guess.

    ⚠ Everything under here is SCRATCH and may vanish between runs. Durable state belongs in the
    corpus map, under the brain root."""
    p = os.path.join(tempfile.gettempdir(), "lifehack", *parts)
    os.makedirs(p, exist_ok=True)
    return p


def flatten_dir(slug=None):
    """The flattened corpus. Portable on a new machine, and NEVER strands an existing one.

    ⚠ BACK-COMPAT IS THE ENTIRE POINT OF THIS FUNCTION. Before 2026-08-12 the skills wrote the
    flatten to a literal `$HOME/.cache/cowork-ingest/<slug>/flatten`, with an unslugged
    `$HOME/.cache/cowork-ingest/flatten` older still. Those hold a real flatten that costs real time
    to rebuild, so **an existing legacy directory WINS** over the portable location. Moving where an
    answer comes from must never orphan the data the old answer pointed at.

    A machine with no legacy directory — every Windows install, where `$HOME/.cache` was never a real
    place, and every fresh install anywhere — gets `cache_dir()` and is correct from the start.

    ⛔ The pre-slug fallback stays SCOPED TO `LEGACY_CORPUS`, exactly as the shell scoped it. Without
    that guard a brand-new corpus resolves to the original's flatten and silently reads its chats."""
    slug = slug or corpus_slug()
    slugged = os.path.join(LEGACY_CACHE, slug, "flatten")
    if os.path.isdir(slugged):
        return slugged
    if slug == LEGACY_CORPUS:
        pre_slug = os.path.join(LEGACY_CACHE, "flatten")
        if os.path.isdir(pre_slug):
            return pre_slug
    return cache_dir("cowork-ingest", slug, "flatten")


def anchor_file(slug=None):
    """The ingest anchor — the resume marker a run reads to know where it left off.

    Same legacy-wins rule as `flatten_dir()`, and for the same reason: an anchor stranded in the old
    location reads as "never ran" and silently redoes work already done. Returns a FILE path; its
    parent directory is created."""
    slug = slug or corpus_slug()
    legacy = os.path.join(LEGACY_CACHE, slug, "ingest-anchor.txt")
    if os.path.isfile(legacy):
        return legacy
    return os.path.join(cache_dir("cowork-ingest", slug), "ingest-anchor.txt")


def claude_run_dir(*parts):
    """`~/.claude/run/...` — where the per-session hook flags live. Created if missing.

    `Path.home()` / `expanduser` is correct on Windows too (Claude Code itself uses
    `%USERPROFILE%\\.claude`), so this needs no branch — but it does need to stop being the literal
    string `$HOME`, which only expands inside a shell."""
    p = os.path.join(os.path.expanduser("~"), ".claude", "run", *parts)
    os.makedirs(p, exist_ok=True)
    return p


def interpreter():
    """The absolute path of the Python running right now.

    Anything that needs to invoke Python again — a hook command, a spawned tool — must use THIS and
    never the bare name. `python3` does not exist on a standard Windows install, and INSTALL.md's own
    Windows fix (disabling the Microsoft Store execution aliases) removes the only `python3.exe` on
    the machine. `sys.executable` is exact and needs no PATH lookup."""
    return sys.executable


# ── The CLI: one path per call, so a command block never has to build one ────────────────────────
# A skill's command block cannot import this module, so it has to be able to ASK. Without this, the
# only way to reach `scratch_dir()` from a markdown command block was to inline a `python3 -c` with
# a sys.path fixup — which is exactly the unreadable shell this module exists to delete, and it is
# how `/tmp/...` survived the first pass at issue #7.
#
# Each subcommand prints ONE absolute path and nothing else, so `VAR="$(python3 shared/paths.py
# scratch ingest_body scan-money)"` is the whole idiom. Parts are joined by the platform's own
# separator — never hand this a path with `/` already in it.
#
# ⛔ Exit 1 with NOT-SET on stderr when the path depends on a brain root that is not set. A caller
# capturing stdout gets an empty string and a failed exit, never a plausible-looking wrong folder.
_PATH_COMMANDS = {
    "scratch": scratch_dir,          # regenerable working space   (was: /tmp/...)
    "cache": cache_dir,              # per-user cache              (was: $HOME/.cache/...)
    "run": claude_run_dir,           # per-session hook flags      (was: $HOME/.claude/run/...)
    "repo": lambda *p: os.path.join(repo_root(), *p),
    "tools": tool_dir,
    "flatten": lambda *p: flatten_dir(p[0] if p else None),   # legacy-wins; see flatten_dir()
    "anchor": lambda *p: anchor_file(p[0] if p else None),
}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:                     # no arguments -> the diagnostic dump, unchanged
        src, root = brain()
        print(f"repo_root    {repo_root()}")
        print(f"corpus_slug  {corpus_slug()}")
        print(f"brain_root   {root or 'NOT-SET'}  (source: {src or 'none'})")
        print(f"corpus_map   {corpus_map() or 'NOT-SET (brain root unset)'}")
        print(f"cache_dir    {cache_dir(corpus_slug())}")
        print(f"scratch_dir  {scratch_dir(corpus_slug())}")
        print(f"interpreter  {interpreter()}")
        return 0

    cmd, parts = argv[0], argv[1:]
    if cmd in ("work", "map"):       # brain-root-derived: may legitimately be NOT-SET
        value = corpus_work() if cmd == "work" else corpus_map()
        if value is None:
            print("NOT-SET — no brain root. Fix: python3 shared/brain_root.py --set <folder>",
                  file=sys.stderr)
            return 1
        print(os.path.join(value, *parts) if parts else value)
        return 0
    if cmd not in _PATH_COMMANDS:
        print(f"unknown path '{cmd}' — expected one of: "
              f"{', '.join(sorted(list(_PATH_COMMANDS) + ['work', 'map']))}", file=sys.stderr)
        return 2
    print(_PATH_COMMANDS[cmd](*parts))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""personal_code_root.py — where YOUR personal code lives (desk runners, prompts, your own scripts).

Not the plugin's code (that is `code-root`) and not your notes (that is `brain_root.py`). Your personal
code folder is a separate folder of yours, with its own local git history so you can always go back.

Resolution, exactly, in order (the source string returned is in parentheses):
  (1) the one-line pointer file ~/.config/lifehack/personal-code, if it names a real directory ("pointer").
      The pointer sits next to `code-root` and `brain-root` in the same config home.
  (2) no pointer file at all -> the default folder ~/lifehack-personal-code, if it exists ("default").
  (3) otherwise NOT-SET, and the message names the fix (run `python3 system/tools/bootstrap.py`).
A pointer that IS present but names a folder that is gone is its own outcome, "pointer-missing",
and it NEVER falls back to the default: silently switching folders would split your history in two.
Closed outcome set {RESOLVED, POINTER-MISSING, NOT-SET}. Never guesses, never uses the cwd.

For the maintainer the pointer names ClaudeOps (the private desk repo); nothing about that is
special-cased here.

Usage as a library:
    sys.path.insert(0, "<plugin>/shared"); import personal_code_root
    source, path = personal_code_root.resolve_personal_code_root()
Usage as a CLI:
    python3 shared/personal_code_root.py            # RESOLVED: <path>  (source: ...)
    python3 shared/personal_code_root.py --quiet    # just the path; exit 1 if not resolved
"""

import argparse
import os
import sys

DEFAULT_FOLDER_NAME = "lifehack-personal-code"
POINTER_NAME = "personal-code"


def pointer_path():
    """~/.config/lifehack/personal-code, computed at call time (so a test can swap HOME)."""
    return os.path.join(os.path.expanduser("~"), ".config", "lifehack", POINTER_NAME)


def default_folder():
    return os.path.join(os.path.expanduser("~"), DEFAULT_FOLDER_NAME)


def read_pointer():
    """The raw one-line value in the pointer file, or None (absent, unreadable, or blank)."""
    fp = pointer_path()
    if not os.path.isfile(fp):
        return None
    try:
        with open(fp, encoding="utf-8") as f:
            value = (f.read().splitlines() or [""])[0].strip()
    except OSError:
        return None
    return os.path.expanduser(value) if value else None


def resolve_personal_code_root():
    """(source, path): source in {"pointer", "default"} with a real directory; or
    ("pointer-missing", path) when the pointer names a folder that is not there; or (None, None)."""
    pointer = read_pointer()
    if pointer:
        if os.path.isdir(pointer):
            return "pointer", pointer
        return "pointer-missing", pointer
    default = default_folder()
    if os.path.isdir(default):
        return "default", default
    return None, None


def main(argv=None):
    ap = argparse.ArgumentParser(description="resolve the personal code folder")
    ap.add_argument("--quiet", action="store_true", help="print only the path; exit 1 if not resolved")
    a = ap.parse_args(argv)
    source, path = resolve_personal_code_root()
    if source == "pointer-missing":
        if not a.quiet:
            print("POINTER-MISSING: %s says your personal code folder is\n  %s\n"
                  "but that folder is not there. Restore it (or fix the line in the pointer file). "
                  "Nothing was switched to the default folder, on purpose." % (pointer_path(), path))
        return 1
    if path is None:
        if not a.quiet:
            print("NOT-SET: no %s and no %s. Fix: python3 system/tools/bootstrap.py (creates both)."
                  % (pointer_path(), default_folder()))
        return 1
    print(path if a.quiet else "RESOLVED: %s  (source: %s)" % (path, source))
    return 0


if __name__ == "__main__":
    sys.exit(main())

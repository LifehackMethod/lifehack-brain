#!/usr/bin/env python3
"""verdicts — the CANNOT-READ convention, ONE place instead of seven hand-typed copies.

It was prose in an SOP, re-typed by hand in 7 tools; `section_archive.py` mistyped
it (reused exit 2, its generic failure code, for "I could not read the file at all").

Provides ONLY the no-outcome exit code and safe file reading. Each tool's own
verdict vocabulary (BOARD-CLEAN, STALE-OPEN, RUNG-ORPHANED, ...) stays in that
tool — flattening verdict sets here would lose the ability to say WHICH check
failed, and that is a hard constraint on this module, not a style choice.
"""
import os

# THE NO-OUTCOME MEMBER: the check never ran, so it has nothing to say about
# pass/fail. Distinct from every tool's own failure codes, which mean the
# check RAN and found something wrong.
CANNOT_READ = 4


def read_text(path, what):
    """Read `path` (labelled `what` in messages) as UTF-8 text.

    Returns (text, None) on success, or (None, message) on failure. Three
    DISTINCT failures, each with a distinct message naming which one it was:
    missing file, unreadable file (broad `Exception` — the Drive FUSE mount
    throws EDEADLK, not a clean OSError), and empty-or-whitespace-only file.

    Never exits and never prints — callers decide what to do with the verdict
    (see print_cannot_read below). Kept separate so a tool using a different
    exit-code convention can still reuse the reading logic.
    """
    if not os.path.exists(path):
        return None, f"{what} does not exist: {path}"
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except Exception as e:                                # FUSE EDEADLK lands here
        return None, f"{what} unreadable ({e.__class__.__name__}: {e}): {path}"
    if not text.strip():
        return None, f"{what} is empty: {path}"
    return text, None


def print_cannot_read(message):
    """Print the CANNOT-READ verdict in house style: token on line 1, the
    reason indented on line 2. Callers still choose when/whether to
    `sys.exit(CANNOT_READ)` — this only standardizes what gets printed."""
    print(f"CANNOT-READ\n  {message}")

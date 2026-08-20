#!/usr/bin/env python3
"""utf8_stdio.py — force stdout/stderr to UTF-8 so a non-ASCII glyph in print() never crashes
a script on a Windows console.

THE DEFECT (GitHub #55/#72/#78/#92). Windows consoles default to a legacy codepage — cp1252 in
the common case — unless something upstream already forced UTF-8. Any `print()` that emits a
non-ASCII character (checkmarks, warning glyphs, arrows, em dashes, box-drawing — this repo's
CLI tools use all of these) then raises `UnicodeEncodeError` and kills the process outright.
macOS/Linux terminals default to UTF-8 already, so the defect is invisible to anyone who has
never run these tools on Windows — which is exactly how it shipped 84 files deep before anyone
noticed.

USE. Call `force_utf8_stdio()` ONCE, as the first executable line of a script's entry point —
inside `if __name__ == "__main__":`, or as the first statement of a top-level script that has
no `__main__` guard at all. Do NOT call it at import time in a module that might only ever be
imported: reconfiguring the caller's stdio as a side effect of `import` is a surprise a library
should never spring on its caller.

GUARANTEES.
  - No-op wherever stdout/stderr already report a UTF-8 encoding (every Mac/Linux terminal, and
    Windows Terminal / PowerShell 7 once UTF-8 mode is already active) — it does not touch a
    stream that's already correct.
  - Never raises. A stream this can't reconfigure (already replaced with something that lacks
    `.reconfigure`, e.g. a test harness's StringIO) is left exactly as it was; the function
    swallows the failure rather than becoming a second crash on top of the first.
  - Uses `errors="backslashreplace"` rather than `errors="strict"` so that even a codepage this
    module failed to move off of degrades to escaped output instead of an exception.
"""

from __future__ import annotations

import sys


def _is_already_utf8(stream) -> bool:
    encoding = getattr(stream, "encoding", None)
    if not encoding:
        return False
    return encoding.replace("-", "").replace("_", "").lower() in ("utf8", "utf8mb4")


def force_utf8_stdio() -> None:
    """Reconfigure sys.stdout and sys.stderr to UTF-8 with a non-raising errors policy.

    No-op if a stream is already UTF-8, or if it has no `.reconfigure` (e.g. it has been
    swapped out for something else, as tests often do). Never raises.
    """
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue
        if _is_already_utf8(stream):
            continue
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="backslashreplace")
        except Exception:
            # The whole point of this helper is to prevent a crash — it must never cause one.
            pass


if __name__ == "__main__":
    force_utf8_stdio()
    print("utf8_stdio: sys.stdout.encoding =", getattr(sys.stdout, "encoding", None))

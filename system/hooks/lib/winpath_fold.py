# winpath_fold.py -- the Python half of lib/winpath_fold.sh. Same fold, same rules, same output.
#
# WHY A SECOND COPY EXISTS AT ALL. Several guards in this plane do their path classification inside
# an embedded Python block (`python3 <<PY` or `python3 -c`), not in bash: guard_canon_write.sh asks
# `"/canon/" in path`, enforce_skill_frontmatter.sh asks `"/skills/" not in path`, and so on. Those
# tests read `tool_input.file_path`, which on Windows arrives BACKSLASH-NATIVE
# (`D:\Notes\Brain\desks\x\canon\current.md`). A forward-slash substring test never matches it, so the
# guard exits 0 and enforces nothing -- silently, with no error and no log line. The bash `_winfold`
# cannot help there, because the comparison happens after the string has already crossed into Python.
#
# MUST STAY BEHAVIOURALLY IDENTICAL TO lib/winpath_fold.sh. It is the same idea in a
# second runtime, not a variant of it. A parity test in the reference PR feeds the same inputs to
# both and fails if a single output differs -- so a change here that is not mirrored there would
# break the build rather than drifting quietly. (Per this task's Ruling 3, no new test suite is
# added here; the discipline of keeping the two files identical still applies by hand.)
#
# WHAT IT DOES NOT DO, exactly as the bash header says: it does not resolve symlinks, follow
# junctions, or collapse `..`. That canonicalisation is the caller's job and is already done before a
# value reaches here. This is a SECOND, purely cosmetic pass so that two spellings of one real
# directory become one spelling before a string comparison -- never so that two DIFFERENT directories
# become one.
#
# Off Windows: returns the input completely UNCHANGED, byte for byte. On Windows: lowercases, turns
# `\` into `/`, and folds a leading drive letter (`C:\...`) into the MSYS spelling `/c/...`.
# Lowercasing is gated to Windows for the reason the bash file gives: NTFS is case-insensitive, so
# folding case there loses no real distinction, while doing it on a case-sensitive filesystem would be
# an actual widening.
#
# Usage, matching the bash signature:
#   winfold(path)            -> autodetect (what every production caller uses)
#   winfold(path, force=1)   -> always fold (tests, so they need not fake uname)
#   winfold(path, force=0)   -> never fold (identity)
#
# Loaded by the same GUARD_LIB convention this plane already uses for lib/gws_guard.py:
#   LIB="$(cd "$(dirname "$0")" && pwd)/lib/winpath_fold.py"
#   GUARD_LIB="$LIB" python3 <<'PY'
#   import importlib.util, os
#   spec = importlib.util.spec_from_file_location("winpath_fold", os.environ["GUARD_LIB"])
#   ...

import os
import platform
import re
import sys

_DRIVE_RE = re.compile(r"^([a-z]):/")


def is_windows():
    """True on Git Bash/MSYS/Cygwin AND on native Windows Python.

    Both matter: the hook is launched from Git Bash, but `python3` on a normal Windows install is
    the native interpreter, which reports `win32` rather than an MSYS uname. The bash half only ever
    sees `uname -s`, so it checks the MSYS spellings; here we check both doors onto the same house.
    """
    if sys.platform.startswith("win"):
        return True
    return platform.system().upper().startswith(("MINGW", "MSYS", "CYGWIN", "WINDOWS"))


def winfold(path, force=None):
    """Fold an already-canonical path into one comparable spelling. See the header."""
    if force is None:
        env = os.environ.get("LIFEHACK_WINFOLD_FORCE", "")
        force = env if env != "" else None

    if force in (1, "1"):
        win = True
    elif force in (0, "0"):
        win = False
    else:
        win = is_windows()

    if not win or not path:
        return path

    folded = path.lower().replace("\\", "/")
    return _DRIVE_RE.sub(lambda m: "/" + m.group(1) + "/", folded)


if __name__ == "__main__":
    # `python3 winpath_fold.py <path> [force]` -- lets this half be driven the same way the shell
    # half is driven, from a scratch script, on identical input.
    _arg = sys.argv[1] if len(sys.argv) > 1 else ""
    _force = sys.argv[2] if len(sys.argv) > 2 else None
    sys.stdout.write(winfold(_arg, _force))

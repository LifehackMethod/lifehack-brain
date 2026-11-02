#!/usr/bin/env python3
"""person_roots.py — the ONLY way plugin code learns where a person's own folders are.

The shared plugin knows the person through exactly two pointers, and this module just reads them:
  notes root          shared/brain_root.py          (LIFEHACK_ROOT, the repo pointer, ~/.config/lifehack/brain-root, ...)
  personal code root  shared/personal_code_root.py  (~/.config/lifehack/personal-code, else ~/lifehack-personal-code)
plus one optional file the person keeps in their personal code folder:
  <personal-code>/code-zones.txt   more code folders of their own (one path per line, `#` comments, `~` allowed)
                                    that the write guard treats as a code clone: hooks/.git/settings protected,
                                    agent-written notes content refused. A missing file means no extra zones.

No folder of any particular person is named here or anywhere in the plugin; a student with no pointers simply
gets empty answers, and every caller treats empty as "no such zone".

CLI (for shell hooks; one line per fact, paths may contain spaces):
    python3 shared/person_roots.py --shell
      NOTES=<path or empty>
      NOTES_STATUS=ok|unset|missing
      PERSONAL=<path or empty>
      PERSONAL_STATUS=ok|unset|missing
      ZONE=<path>              (zero or more)
      OWNER_GH_USER=<handle or empty>
STATUS is what a guard needs to FAIL CLOSED: "unset" = nothing names the folder (no pointer, no env, no default
folder); "missing" = something names it but it is not there (or unreadable). Either way the person's zones are
UNKNOWN, and a guard must then protect as strictly as it can, never treat the zone as simply absent.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

ZONES_NAME = "code-zones.txt"
DEPRECATED_OWNER_VAR = "CLAUDEOPS_GH_USER"  # r8-allow: deprecated owner fallback (set LIFEHACK_OWNER_GH_USER instead)


def _usable(path):
    """A real directory that is not / or the home folder itself (a zone that wide would swallow everything)."""
    if not path or not os.path.isabs(path):
        return False
    real = os.path.realpath(path)
    return os.path.isdir(real) and real not in ("/", os.path.realpath(os.path.expanduser("~")))


def notes_root():
    """Real path of the resolved notes root, or "" (NOT-SET, permission-denied, or unusable)."""
    try:
        import brain_root
        source, path = brain_root.resolve_brain_root()
    except Exception:
        return ""
    if source in (None, "permission-denied") or not _usable(path):
        return ""
    return os.path.realpath(path)


def personal_code_root():
    """Real path of the resolved personal code folder, or "" (not set, or the pointer names a missing folder)."""
    try:
        import personal_code_root as pcr
        source, path = pcr.resolve_personal_code_root()
    except Exception:
        return ""
    if source not in ("pointer", "default") or not _usable(path):
        return ""
    return os.path.realpath(path)


def notes_status():
    """ok | unset | missing (see the module docstring)."""
    if notes_root():
        return "ok"
    try:
        import brain_root
        named = bool(os.environ.get(brain_root.BRAIN_ROOT_ENV)) or bool(brain_root.read_repo_pointer()) \
            or bool(brain_root.read_main_worktree_pointer()) or bool(brain_root.read_persisted()) \
            or bool(brain_root.BRAIN_ROOT_LEGACY_GLOB)
    except Exception:
        return "missing"
    return "missing" if named else "unset"


def personal_status():
    """ok | unset | missing (see the module docstring)."""
    if personal_code_root():
        return "ok"
    try:
        import personal_code_root as pcr
        source, _path = pcr.resolve_personal_code_root()
    except Exception:
        return "missing"
    return "missing" if source in ("pointer-missing", "pointer", "default") else "unset"


def team_skills_root():
    """Real path of the team shared-skills folder (shared/team_skills_root.py), or "" (not set, or the
    pointer names a folder that is not there). Empty means "no such zone" — a caller never guesses."""
    try:
        import team_skills_root as tsr
        source, path = tsr.resolve_team_skills_root()
    except Exception:
        return ""
    return os.path.realpath(path) if source == "pointer" and _usable(path) else ""

def team_status():
    """ok | unset | missing for the team shared-skills folder (see team_skills_root.py)."""
    if team_skills_root():
        return "ok"
    try:
        import team_skills_root as tsr
        source, _path = tsr.resolve_team_skills_root()
    except Exception:
        return "missing"
    return "missing" if source == "pointer-missing" else "unset"

def owner_gh_user():
    """The person's own GitHub account (the one a repair `gh auth switch --user` may go back to), from the environment:
    $LIFEHACK_OWNER_GH_USER, else the DEPRECATED old name below (a maintainer setting that predates the generic
    one; kept as a fallback here and nowhere else -- set LIFEHACK_OWNER_GH_USER instead). Empty when neither is set."""
    return (os.environ.get("LIFEHACK_OWNER_GH_USER") or os.environ.get(DEPRECATED_OWNER_VAR) or "").strip()


def code_zones(personal=None):
    """Extra code folders listed in <personal-code>/code-zones.txt (real paths, existing, de-duplicated)."""
    personal = personal_code_root() if personal is None else personal
    if not personal:
        return []
    fp = os.path.join(personal, ZONES_NAME)
    out = []
    try:
        with open(fp, encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError:
        return []
    for raw in lines:
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        p = os.path.expanduser(line)
        if _usable(p):
            real = os.path.realpath(p)
            if real not in out:
                out.append(real)
    return out


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv != ["--shell"]:
        print("usage: person_roots.py --shell", file=sys.stderr)
        return 2
    personal = personal_code_root()
    print("NOTES=" + notes_root())
    print("NOTES_STATUS=" + notes_status())
    print("PERSONAL=" + personal)
    print("PERSONAL_STATUS=" + personal_status())
    for z in code_zones(personal):
        print("ZONE=" + z)
    print("TEAM=" + team_skills_root())
    print("TEAM_STATUS=" + team_status())
    print("OWNER_GH_USER=" + owner_gh_user())
    return 0


if __name__ == "__main__":
    sys.exit(main())

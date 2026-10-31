"""placement_off.py -- the user's own off-switch for "where to save" checks (Round D ruling A.6).

File: ~/.config/lifehack/placement.conf (survives plugin updates). One line per switched-off check, TAB-separated:
    off<TAB><check-name>          (the older  <check-name><TAB>off  also works)
Check names = the rule names in system/hooks/placement.conf (code-in-notes, notes-in-harness, worktree-home,
code-outside-homes) plus the end-of-turn list stops: own-list, unhomed.
FINE-CHINA GUARDS HAVE NO OFF SWITCH: this module only ever answers for the names in PLACEMENT_CHECKS; any other name
(fc_*, force-push, canon, SOP, delete asks...) is ignored here, so a line naming one does nothing.
Gated by switch placement_user_off (roundB.conf). OFF = this module says "nothing is off, no counting, no hint".
Repeat-stop counts: ~/.config/lifehack/placement-stops.json {check: n}. From the 3rd stop of one check on, the stop message
gains how to switch it off plus the warning. Under LIFEHACK_WATCH_SHADOW=1 nothing is written.
CLI (for shell callers):  placement_off.py off <check>   -> exit 0 if switched off
                          placement_off.py stop <check>  -> counts one stop, prints the hint text (maybe empty)
"""
import json, os, sys

PLACEMENT_CHECKS = {
    "code-in-notes": "keeping code and notes apart, so backups, updates and the notes folder stay clean",
    "notes-in-harness": "what students receive: personal notes written into the shared plugin repo would be published with it",
    "worktree-home": "cleanup and safety of git worktrees (they must not sit inside a repo or your notes)",
    "code-outside-homes": "finding, listing and updating your own scripts later (your own list only sees the personal code folder)",
    "skill-not-loaded": "your skill loading at all (Claude only loads personal skills from ~/.claude/skills)",
    "own-list": "your own list of your own tools staying complete",
    "unhomed": "finding your own scripts later",
}
THRESHOLD = 3


def _on():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from roundb import roundb_on
        return roundb_on("placement_user_off")
    except Exception:
        return False
    finally:
        sys.path.pop(0)


def conf_path():
    return os.path.join(os.path.expanduser("~"), ".config", "lifehack", "placement.conf")


def off_set():
    """Names the person switched off. Only PLACEMENT_CHECKS names count."""
    if not _on():
        return set()
    out = set()
    try:
        for ln in open(conf_path(), encoding="utf-8", errors="replace"):
            f = [x.strip() for x in ln.rstrip("\n").split("\t")]
            if len(f) == 2 and f[0] == "off":
                out.add(f[1])
            elif len(f) == 2 and f[1] == "off":
                out.add(f[0])
    except OSError:
        pass
    return {n for n in out if n in PLACEMENT_CHECKS}


def is_off(check):
    return check in off_set()


def _counts_path():
    return os.path.join(os.path.expanduser("~"), ".config", "lifehack", "placement-stops.json")


def note_stop(check):
    """Count one emitted stop of this check; -> the hint text to append ('' before the 3rd stop or when the feature is off)."""
    if check not in PLACEMENT_CHECKS or not _on():
        return ""
    p = _counts_path()
    try:
        d = json.load(open(p, encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    n = int(d.get(check, 0)) + 1
    if os.environ.get("LIFEHACK_WATCH_SHADOW") != "1":
        d[check] = n
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            json.dump(d, open(p, "w", encoding="utf-8"))
        except OSError:
            pass
    if n < THRESHOLD:
        return ""
    return (" || THIS CHECK HAS STOPPED YOU %d TIMES. If it keeps getting in your way, YOU can switch it off: add the line  off<TAB>%s  "
            "(off, a TAB, then the name) to ~/.config/lifehack/placement.conf. An AI session cannot do that for you without your explicit Yes. "
            "Lifehack is built to work this way; turning this off may break %s." % (n, check, PLACEMENT_CHECKS[check]))


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "off":
        sys.exit(0 if is_off(sys.argv[2]) else 1)
    if len(sys.argv) == 3 and sys.argv[1] == "stop":
        print(note_stop(sys.argv[2]))
        sys.exit(0)
    sys.exit(2)

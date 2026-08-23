#!/usr/bin/env python3
"""cal_config — the one place a calendar or task-list identifier is read from.

WHY THIS EXISTS. The calendar tools this came from each carried the author's own identifiers as
module constants: his personal calendar address, the id of the calendar agents are allowed to write
to, the id of his goals task list, the id of the one task under it that a day's plan may hang from.
Fifteen files, the same four values, copied.

Shipping that would have been worse than unportable. An agent that writes to a calendar id baked
into a tool writes to SOMEBODY ELSE'S CALENDAR, and the failure is silent to the person running it —
their events simply never appear. So the identifiers moved out of the code and into the reader's own
notes, at `<notes>/config/cal.md`, and this module is the only thing that reads them.

⛔ NOTHING HERE HAS A DEFAULT. A default calendar id is a wrong calendar id. Every accessor either
returns what the person wrote down or raises `CalConfigMissing`, whose message says exactly which key
is missing and what the file should look like. A tool that cannot find an id must stop and say so —
never guess, and never fall back to `primary`, which is the one calendar a stranger's agent must
never touch.

THE FILE. `<notes>/config/cal.md` is markdown so a person can read it, with one `key: value` per
line. Unknown keys are ignored, so notes and headings cost nothing:

    # My calendars and lists
    #
    # agent_calendar is the ONE calendar this system is allowed to write to. Make a new, empty
    # calendar for it — do not point it at the calendar your life is already in.

    personal_calendar: you@example.com
    agent_calendar:    abc123...@group.calendar.google.com
    goals_tasklist:    <the id of the task list holding your goals>
    daily_parent_task: <the id of the one task a day's plan hangs from>

Find a calendar's id in Google Calendar under Settings → the calendar → "Integrate calendar".
"""
import os
import re
import sys

KEYS = {
    "personal_calendar":
        "the calendar your own life is in. Tools READ it and never write to it.",
    "agent_calendar":
        "the ONE calendar this system may write to. Make a new, empty one for it.",
    "goals_tasklist":
        "the task list holding your goals. Read-only, with one exception: daily_parent_task.",
    "daily_parent_task":
        "the single task a day's plan is allowed to hang subtasks from.",
}

_LINE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.+?)\s*$")


class CalConfigMissing(Exception):
    """Raised when an identifier is not on file. Its message is meant to be shown to a person."""


def _notes_root():
    """The notes folder, resolved exactly the way everything else here resolves it.

    ⚠ `resolve_brain_root()` returns `(source, path)`, not a path — it tells you WHERE the answer
    came from as well as what it is. Taking it for a string produces a tuple that only fails at the
    next `os.path.join`, several frames away from the mistake. Unpacked here, once."""
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, here)
    import brain_root                                        # noqa: E402
    _source, path = brain_root.resolve_brain_root()
    return path


def config_path(notes_root=None):
    root = notes_root if notes_root is not None else _notes_root()
    if not root:
        return None
    return os.path.join(root, "config", "cal.md")


def load(notes_root=None):
    """Every key on file, as a dict. An absent or unreadable file is an empty dict, not an error —
    asking WHETHER something is configured is a fair question; asking for a value that is not there
    is not."""
    p = config_path(notes_root)
    if not p or not os.path.exists(p):
        return {}
    out = {}
    try:
        with open(p, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if line.lstrip().startswith("#"):
                    continue
                m = _LINE.match(line)
                if not m:
                    continue
                key, val = m.group(1).lower(), m.group(2)
                # A placeholder left in from the example is NOT a value. Catching it here is the
                # difference between a clear refusal and a write addressed to "<the id of...>".
                if val.startswith("<") and val.endswith(">"):
                    continue
                out[key] = val
    except Exception:
        return {}
    return out


def get(key, notes_root=None):
    """One identifier, or a refusal that says how to fix it."""
    key = key.lower()
    vals = load(notes_root)
    if key in vals:
        return vals[key]
    p = config_path(notes_root) or "<your notes folder>/config/cal.md"
    what = KEYS.get(key, "")
    raise CalConfigMissing(
        "no `%s` on file, so there is nothing to use and nothing safe to guess.\n"
        "  WHAT IT IS: %s\n"
        "  WHERE IT GOES: %s\n"
        "  ADD THE LINE:  %s: <the id>\n"
        "  Find a calendar's id in Google Calendar → Settings → that calendar → "
        "\"Integrate calendar\"." % (key, what, p, key)
    )


def require(*keys, **kw):
    """Several at once, reported together — one refusal listing three missing keys beats three runs
    that each fail on the next one."""
    notes_root = kw.get("notes_root")
    vals = load(notes_root)
    missing = [k for k in keys if k.lower() not in vals]
    if missing:
        p = config_path(notes_root) or "<your notes folder>/config/cal.md"
        lines = ["%d identifier(s) are not on file at %s:" % (len(missing), p)]
        for k in missing:
            lines.append("  %-18s %s" % (k + ":", KEYS.get(k, "")))
        lines.append("Add one `key: value` line each. Google Calendar → Settings → the calendar → "
                     "\"Integrate calendar\" has the ids.")
        raise CalConfigMissing("\n".join(lines))
    return {k: vals[k.lower()] for k in keys}


if __name__ == "__main__":
    # `--get <key>` prints ONE value and nothing else, so a skill can substitute it into a command.
    # A missing key exits non-zero with the instructions on stderr, which means the surrounding
    # command fails loudly instead of running with an empty id — the whole point of having no
    # defaults. Anything printed on stdout here is safe to paste into a command line.
    import os, sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "system", "tools")))
    from utf8_stdio import force_utf8_stdio
    force_utf8_stdio()
    if len(sys.argv) >= 3 and sys.argv[1] == "--get":
        try:
            sys.stdout.write(get(sys.argv[2]))
        except CalConfigMissing as e:
            sys.stderr.write("cal_config: %s\n" % e)
            sys.exit(1)
        sys.exit(0)

    p = config_path()
    print("config file: %s" % (p or "NOT SET — no notes folder resolved"))
    vals = load()
    if not vals:
        print("nothing on file yet.")
    for k in KEYS:
        print("  %-18s %s" % (k + ":", vals.get(k, "— not set")))

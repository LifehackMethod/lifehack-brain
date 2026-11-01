#!/usr/bin/env python3
"""personal_register.py — where a person's OWN register rows live, and how the register tools find them.

The master register (`system/register/register.jsonl`) is for SHARED units only (Enver's 2026-10-30 ruling,
encoded in system/tools/rig/rig_live_score.py). Every unit that lives in a person's personal code folder —
their own tools, skills, hook registrations, git hooks and personal scheduled jobs (`<personal-code>/jobs.md`)
— is a `repo: "private"` row in THAT person's own list:

    <personal-code>/register.jsonl      same schema v1 as the master, one JSON object per line

<personal-code> comes from `shared/personal_code_root.py` (the ~/.config/lifehack/personal-code pointer); no
folder is named here. A missing file means "no personal rows" — nothing to set up for a new student.

Who uses this module:
  harvest.py         writes private rows ONLY here (with --personal-out), never into the master;
  generate.py        reads master + personal (the private wiring targets draw from the personal rows);
  omission_check.py  reads master + personal (a personal tool is registered, not an omission);
  caller_lint.py     reads master + personal (a personal skill still counts as a caller).
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED = os.path.join(os.path.dirname(os.path.dirname(_HERE)), "shared")
if _SHARED not in sys.path:
    sys.path.append(_SHARED)

REGISTER_NAME = "register.jsonl"
JOBS_NAME = "jobs.md"


def default_private_root():
    """The personal code folder when it resolves; else a path that does not exist (every walk treats a missing
    root as empty, so a student with no personal folder simply has no private rows)."""
    try:
        import personal_code_root
        source, root = personal_code_root.resolve_personal_code_root()
    except Exception:
        source, root = None, None
    if source in ("pointer", "default") and root:
        return os.path.abspath(root)
    return os.path.join(os.path.expanduser("~"), ".config", "lifehack", "no-personal-code-folder")


def personal_register_path(private_root):
    return os.path.join(private_root, REGISTER_NAME)


def personal_jobs_path(private_root):
    return os.path.join(private_root, JOBS_NAME)


def _same(a, b):
    try:
        return os.path.samefile(a, b)
    except OSError:
        return os.path.abspath(a) == os.path.abspath(b)


def load_personal_rows(private_root, master_path=None):
    """-> (rows, warnings). Rows of <private_root>/register.jsonl whose repo is "private". A malformed line, or a row
    that claims repo "public", is skipped with a warning (a person's own file must never break the shared tools)."""
    p = personal_register_path(private_root)
    if not os.path.isfile(p) or (master_path and _same(p, master_path)):
        return [], []
    rows, warnings = [], []
    try:
        with open(p, encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as e:
                    warnings.append("personal register line %d: invalid JSON (%s), skipped" % (i, e))
                    continue
                if not isinstance(row, dict) or row.get("repo") != "private":
                    warnings.append("personal register line %d: not a repo=private row, skipped" % i)
                    continue
                rows.append(row)
    except OSError as e:
        warnings.append("personal register unreadable (%s), skipped" % e)
    return rows, warnings


def with_personal(rows, private_root, master_path=None):
    """master rows + personal rows, de-duplicated by id (a master row with the same id wins: it was written first and
    the master is the shared truth). -> (rows, warnings)."""
    extra, warnings = load_personal_rows(private_root, master_path)
    have = {r.get("id") for r in rows}
    out = list(rows)
    for r in extra:
        if r.get("id") in have:
            warnings.append("personal row %s duplicates a master row id, skipped" % r.get("id"))
            continue
        out.append(r)
        have.add(r.get("id"))
    return out, warnings

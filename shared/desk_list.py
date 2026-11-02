#!/usr/bin/env python3
"""desk_list.py -- the ONE reader of YOUR desk list, kept in your notes folder next to your desks.

The plugin ships no desk list and no example of one. Desks belong to one person, so the list of them lives in
that person's notes folder, beside the desks it names:

    <notes>/desks/desk-registry.yaml     schema_version + a `desks:` list, one entry per full desk

<notes> is found through `shared/person_roots.py` (which reads `shared/brain_root.py`); nothing here names
anyone's folder. A missing list means "no desks": a new student has nothing to set up, and every reader
(backlog_groom.py, planning-diary-capture.py) simply sees zero desks. A list that is THERE but cannot be read
is different: `load_desks()` returns the real reason (a YAML error, a wrong shape, PyYAML missing), so a
reader can say what is actually wrong instead of guessing.

An entry's fields (only the first three are read by any tool today):
    desk_id          stable slug, the identity other tools match a desk by
    open_loops_path  path (relative to the notes folder) to the desk's state/open-loops.md
    backlog_mode     queue = staleness is a defect (flag it) | register = staleness is normal (don't nag)
    purpose_path     path (relative to the notes folder) to the desk's canon/purpose.md
    reads_external   yes = the desk takes in outside content (email/web/files) | no
    notes            anything the next reader needs

Which list (in order):
  (1) $LIFEHACK_DESK_LIST when set (a test seam; set it EMPTY to mean "no list");
  (2) <notes>/desks/desk-registry.yaml when the notes folder resolves and the file exists;
  (3) otherwise none.

CLI:
    python3 shared/desk_list.py --path     # prints the list's path, or nothing
    python3 shared/desk_list.py --check    # prints how many desks, or the real error (exit 1)
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

LIST_REL = os.path.join("desks", "desk-registry.yaml")
ENV_SEAM = "LIFEHACK_DESK_LIST"
_ID_RE = re.compile(r"^\s*-\s*desk_id:\s*(\S+)")


def resolve_desk_list(env=None):
    """Path of the person's desk list, or None (no notes folder, or no list in it)."""
    env = os.environ if env is None else env
    if ENV_SEAM in env:
        p = env.get(ENV_SEAM) or ""
        return p if p and os.path.isfile(p) else None
    try:
        import person_roots
        notes = person_roots.notes_root()
    except Exception:
        return None
    if not notes:
        return None
    p = os.path.join(notes, LIST_REL)
    return p if os.path.isfile(p) else None


def load_desks(env=None):
    """-> (desks, error). desks is a list of entry dicts; error is None or a one-line real reason.
    No list -> ([], None). A list that cannot be read -> ([], "<what is wrong>"). Never raises."""
    path = resolve_desk_list(env)
    if not path:
        return [], None
    try:
        import yaml
    except ImportError:
        return [], "PyYAML is not installed under %s, so %s cannot be read (see system/requirements.txt)" % (
            sys.executable, path)
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        msg = " ".join(str(e).split())
        return [], "the desk list %s cannot be read: %s: %s" % (path, type(e).__name__, msg)
    if data is None:
        return [], None
    if not isinstance(data, dict):
        return [], "the desk list %s is not a mapping (found %s); expected `desks:` at the top" % (
            path, type(data).__name__)
    desks = data.get("desks") or []
    if not isinstance(desks, list):
        return [], "the desk list %s: `desks:` is %s, not a list" % (path, type(desks).__name__)
    bad = [i for i, d in enumerate(desks) if not isinstance(d, dict)]
    if bad:
        return [], "the desk list %s: entry %d is not a mapping (each desk is `- desk_id: ...`)" % (path, bad[0])
    return desks, None


def desk_ids(env=None):
    """The desk_id values, read line by line (no PyYAML needed). Empty set when there is no list."""
    path = resolve_desk_list(env)
    if not path:
        return set()
    out = set()
    try:
        with open(path, encoding="utf-8") as f:
            for ln in f:
                m = _ID_RE.match(ln)
                if m:
                    out.add(m.group(1).strip().strip("\"'"))
    except (OSError, UnicodeDecodeError):
        return set()
    return out


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv == ["--path"]:
        p = resolve_desk_list()
        if p:
            print(p)
        return 0
    if argv == ["--check"]:
        desks, err = load_desks()
        if err:
            print("ERROR: " + err)
            return 1
        p = resolve_desk_list()
        print("%d desk(s) in %s" % (len(desks), p) if p else "no desk list (no desks)")
        return 0
    print("usage: desk_list.py --path | --check", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())

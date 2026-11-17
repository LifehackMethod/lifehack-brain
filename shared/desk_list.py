#!/usr/bin/env python3
"""desk_list.py -- the ONE reader of YOUR desk list, kept in your notes folder next to your desks
(and, since CR-9 step 2a, the ONE writer of a new desk's row into it: append_desk_entry, used by
desk_scaffold.py — never a second desk list).

The plugin ships no desk list and no example of one. Desks belong to one person, so the list of them lives in
that person's notes folder, beside the desks it names:

    <notes>/desks/desk-registry.yaml     schema_version + a `desks:` list, one entry per full desk

<notes> is found through `shared/person_roots.py` (which reads `shared/brain_root.py`); nothing here names
anyone's folder. A missing list means "no desks": a new student has nothing to set up, and every reader
(backlog_groom.py, planning-diary-capture.py) simply sees zero desks. A list that is THERE but cannot be read
is different: `load_desks()` returns the real reason (a YAML error, a wrong shape, a bad line), so a
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
    python3 shared/desk_list.py planning-folder   # the planning desk's folder name (exit 2 + the
                                                  # named error if there is no planning row)
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


_KEY = r"[A-Za-z_][A-Za-z0-9_]*"
_TOP_RE = re.compile(r"^(%s):(?:\s+(.*))?$" % _KEY)
_ITEM_RE = re.compile(r"^(\s+)-\s+(%s):(?:\s+(.*))?$" % _KEY)
_FIELD_RE = re.compile(r"^(\s+)(%s):(?:\s+(.*))?$" % _KEY)


def _scalar(raw):
    """One YAML-ish scalar, the way yaml.safe_load would read it for this list's simple values."""
    v = (raw or "").strip()
    if v[:1] in ("'", '"'):
        q = v[0]
        end = v.find(q, 1)
        if end < 0:
            raise ValueError("unclosed %s quote" % q)
        rest = v[end + 1:].strip()
        if rest and not rest.startswith("#"):
            raise ValueError("text after a quoted value: %r" % rest)
        return v[1:end]
    if " #" in v:
        v = v.split(" #", 1)[0].rstrip()
    elif v.startswith("#"):
        v = ""
    if v in ("", "~", "null", "Null", "NULL"):
        return None
    low = v.lower()
    if low in ("yes", "true", "on"):
        return True
    if low in ("no", "false", "off"):
        return False
    if re.fullmatch(r"[-+]?\d+", v):
        return int(v)
    if v[:1] in ("[", "{", "&", "*", "!", "|", ">"):
        raise ValueError("%r needs full YAML (flow/anchor/block syntax), not the simple desk-list shape" % v)
    return v


def _parse_simple(text):
    """The ONE PyYAML-free reader of the simple desk-list shape:

        schema_version: 2
        desks:
          - desk_id: alpha
            open_loops_path: desks/alpha/state/open-loops.md

    -> (data, None) or (None, "line N: <what is wrong>"). Anything outside that shape is a real error
    naming the line, never a guess."""
    data, entries, cur, item_indent, in_desks = {}, None, None, None, False
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if "\t" in line[:len(line) - len(line.lstrip())]:
            return None, "line %d: a tab in the indentation (YAML allows spaces only)" % n
        try:
            m = _TOP_RE.match(line)
            if m:
                key, raw = m.group(1), (m.group(2) or "").strip()
                raw = "" if raw.startswith("#") else raw.split(" #", 1)[0].strip()
                if key == "desks":
                    if raw not in ("", "[]"):
                        return None, "line %d: `desks:` must be followed by a list of entries, not %r" % (n, raw)
                    entries, cur, item_indent = [], None, None
                    in_desks = raw == ""        # `desks: []` is an empty, CLOSED list
                    data["desks"] = entries
                else:
                    data[key] = _scalar(m.group(2))
                    in_desks = False
                continue
            m = _ITEM_RE.match(line)
            if m:
                if not in_desks:
                    return None, ("line %d: a `- %s:` entry outside an open `desks:` list (an entry pasted "
                                  "under `desks: []`? change it to `desks:`)" % (n, m.group(2)))
                if item_indent is not None and len(m.group(1)) != item_indent:
                    return None, "line %d: this entry is indented differently from the ones above it" % n
                item_indent = len(m.group(1))
                cur = {m.group(2): _scalar(m.group(3))}
                entries.append(cur)
                continue
            m = _FIELD_RE.match(line)
            if m and in_desks and cur is not None and len(m.group(1)) > item_indent:
                cur[m.group(2)] = _scalar(m.group(3))
                continue
        except ValueError as e:
            return None, "line %d: %s" % (n, e)
        return None, "line %d is not in the simple desk-list shape: %r" % (n, line.strip()[:60])
    return data, None


def load_desks(env=None):
    """-> (desks, error). desks is a list of entry dicts; error is None or a one-line real reason.
    No list -> ([], None). A list that cannot be read -> ([], "<what is wrong>"). Never raises.
    PyYAML is used when it is installed; without it the simple-shape reader above reads the list, so a
    student with no PyYAML gets their desks, not an error."""
    path = resolve_desk_list(env)
    if not path:
        return [], None
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except (OSError, UnicodeDecodeError) as e:
        return [], "the desk list %s cannot be read: %s: %s" % (path, type(e).__name__, " ".join(str(e).split()))
    try:
        import yaml
    except ImportError:
        yaml = None
    if yaml is not None:
        try:
            data = yaml.safe_load(text)
        except Exception as e:
            msg = " ".join(str(e).split())
            return [], "the desk list %s cannot be read: %s: %s" % (path, type(e).__name__, msg)
    else:
        data, err = _parse_simple(text)
        if err:
            return [], "the desk list %s cannot be read: %s" % (path, err)
    if data is None or data == {}:
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
    """The desk_id values. Empty set when there is no list. Read through load_desks(); if the list is
    malformed, the old lenient line scan still recovers the ids (planning-diary-capture.py only needs
    names, and a broken list must not hide them from it)."""
    desks, err = load_desks(env)
    if not err:
        return {str(d.get("desk_id")).strip() for d in desks if d.get("desk_id") not in (None, "")}
    path = resolve_desk_list(env)
    out = set()
    try:
        with open(path, encoding="utf-8") as f:
            for ln in f:
                m = _ID_RE.match(ln)
                if m:
                    out.add(m.group(1).strip().strip("\"'"))
    except (OSError, UnicodeDecodeError, TypeError):
        return set()
    return out


def desk_folder(desk_id, env=None):
    """-> (folder, error). The folder name under <notes>/desks/ that the list says desk `desk_id` lives in,
    read from its purpose_path / open_loops_path (`desks/<folder>/...`). No list, or no such desk_id ->
    (None, None); a broken list -> (None, its real error). Never raises; needs no PyYAML (the
    session-start loader calls this)."""
    if not desk_id:
        return None, None
    entries, err = load_desks(env)
    if err:
        return None, err
    for d in entries:
        if str(d.get("desk_id") or "").strip() != desk_id:
            continue
        for key in ("purpose_path", "open_loops_path"):
            parts = str(d.get(key) or "").replace("\\", "/").split("/")
            if len(parts) > 2 and parts[0] == "desks" and parts[1] not in ("", ".", ".."):
                return parts[1], None
    return None, None


def planning_desk_folder(env=None):
    """-> (folder, error). The planning desk's folder name under <notes>/desks/, read from the ONE
    desk-list row that owns the planning desk, found by desk_id 'planning' first, then 'cal' (the
    owner's row keeps desk_id 'cal' after his folder moves to desks/planning; the folder comes from
    the row's own purpose_path / open_loops_path, NEVER from the id). No row -> (None, a named error
    that says the resolver is never falling back to desks/cal); a broken list -> (None, the real
    error, wrapped so a caller knows the planning folder is what it blocked). Never raises; needs
    no PyYAML. The ONE resolver — planning-vault-pull.py, planning-diary-rollup.py,
    planning-diary-capture.py, planning-light-sweep.py, planning-window-to-vault.py and the shell
    runners (via `desk_list.py planning-folder`) call this; nobody keeps a private copy."""
    entries, err = load_desks(env)
    if err:
        return None, ("the desk list cannot be read, so the planning desk's folder is unknown: %s" % err)
    for want in ("planning", "cal"):
        for d in entries:
            if str(d.get("desk_id") or "").strip() != want:
                continue
            for key in ("purpose_path", "open_loops_path"):
                parts = str(d.get(key) or "").replace("\\", "/").split("/")
                if len(parts) > 2 and parts[0] == "desks" and parts[1] not in ("", ".", ".."):
                    return parts[1], None
    return None, ("no planning-desk row in the desk list (looked for desk_id 'planning' or 'cal') — add or "
                  "update the row in <notes>/desks/desk-registry.yaml with its purpose_path / "
                  "open_loops_path under desks/<folder>/; refusing to guess the planning desk's "
                  "folder (never falling back to desks/cal)")


def _render(v):
    """One entry value as the simple shape writes it: bare when safe, double-quoted when it carries
    spaces or anything the reader would otherwise misread. The reader's _scalar() reads both back."""
    s = str(v)
    if s == "" or re.search(r"[\s#\"':{}\[\],&*!|>%@`]", s) or s.lower() in ("true", "false", "null", "~"):
        return '"%s"' % s.replace("\\", "\\\\").replace('"', '\\"')
    return s


def append_desk_entry(notes_root, entry):
    """Add one desk to the person's ONE desk list, at <notes_root>/desks/desk-registry.yaml — the same
    list every reader here reads; there is never a second list. Creates the list with its two-line
    header (`schema_version: 2` + `desks:`) when the person has none yet. -> (path, None) on success,
    or (None, reason) — a duplicate desk_id, an unreadable existing list, or a bad entry — and writes
    NOTHING in any failure case. Never raises."""
    if not isinstance(entry, dict) or not str(entry.get("desk_id") or "").strip():
        return None, "the entry has no desk_id"
    desk_id = str(entry["desk_id"]).strip()
    path = os.path.join(notes_root, LIST_REL)
    text = ""
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except (OSError, UnicodeDecodeError) as e:
            return None, "the desk list %s cannot be read: %s: %s" % (path, type(e).__name__, " ".join(str(e).split()))
        existing, err = _parse_or_yaml(text, path)
        if err:
            return None, err
        if any(str(d.get("desk_id") or "").strip() == desk_id for d in existing):
            return None, "desk '%s' already has a row in %s — one desk, one row; nothing written" % (desk_id, path)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
            if text and not text.endswith("\n"):
                f.write("\n")
            if not text.strip():
                f.write("schema_version: 2\ndesks:\n")
            for k, v in entry.items():
                f.write("  - %s: %s\n" % (k, _render(v)) if k == "desk_id"
                        else "    %s: %s\n" % (k, _render(v)))
    except OSError as e:
        return None, "the desk list %s cannot be written: %s: %s" % (path, type(e).__name__, " ".join(str(e).split()))
    return path, None


def _parse_or_yaml(text, path):
    """The same read load_desks() does, for one list file chosen by path -> (entries, None) or
    (None, reason). Used by append_desk_entry so a broken list is never appended to."""
    try:
        import yaml
    except ImportError:
        yaml = None
    if yaml is not None:
        try:
            data = yaml.safe_load(text)
        except Exception as e:
            return None, "the desk list %s cannot be read: %s: %s" % (path, type(e).__name__, " ".join(str(e).split()))
    else:
        data, err = _parse_simple(text)
        if err:
            return None, "the desk list %s cannot be read: %s" % (path, err)
    if data is None or data == {}:
        return [], None
    if not isinstance(data, dict):
        return None, "the desk list %s is not a mapping; expected `desks:` at the top" % path
    entries = data.get("desks") or []
    if not isinstance(entries, list):
        return None, "the desk list %s: `desks:` is %s, not a list" % (path, type(entries).__name__)
    return entries, None


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
    if argv == ["planning-folder"]:
        name, err = planning_desk_folder()
        if not name:
            print("ERROR: " + err, file=sys.stderr)
            return 2
        print(name)
        return 0
    print("usage: desk_list.py --path | --check | planning-folder", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())

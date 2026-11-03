#!/usr/bin/env python3
"""fc_sign.py -- the street signs on fine china's speed bumps (plan fix 23(d), fix 19; approved by the coordinator 2026-11-03).

WHY: an ask does not reach a model in a bypass window (records/2026-11-02-asked-cases-block-vs-ask.md, E1). A sign does: the FIRST attempt on a
     target in a session is refused (exit 2) with one specific instruction. Every later attempt gets exactly what it gets with the switch off,
     today's ask, so a person's yes still lands, and no sign says a repeat works. Nothing here is a new hard block.
THE WORDS: each sign is "STOP. ..." and ONE "Instead, ..." naming the one right route, from records/2026-11-02-street-sign-test.md where that kind was
     tested. Change a route only with a test that the route passes the whole hook chain in every shell shape (tests/test_fc_signs.py).
KEY: session_id + agent_id (a sub-agent shares its parent's session_id and carries its own agent_id; real stdin, tests/fixtures/pre_real_stdin_*.json)
     + group + the target's real path. Not the command text, so another tool on the same target gets no second sign.
FAIL POSTURE: no session id, or a marker that cannot be written, means no sign: the caller falls through to its ask. A sign that could not be spent
     would refuse every attempt, which would be a hard block.
LIMIT: two exit-2 hooks on one call: only one message reaches the model (measured, Claude Code 2.1.316, 2026-11-03), so `masked` (build_mode's
     sibling_certain_deny) denies without spending. An ask beside an exit 2 does not hide it (same measurement).
SWITCHES: one per group in system/hooks/roundB.conf (GROUPS below). OFF = no sign, today's behaviour, pinned by tests/test_fc_signs.py.
USE: python: first(signs, payload) -> text or None. bash: payload on stdin, `python3 fc_sign.py <group> <target> <text or @name>`: exit 2 with the sign, else 0.
"""
import hashlib, json, os, re, shlex, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
GROUPS = {"sops": "fc_sign_sops", "canon": "fc_sign_canon", "claudemd": "fc_sign_claudemd", "data": "fc_sign_data", "db": "fc_sign_db",
          "folder": "fc_sign_folder", "drive": "fc_sign_drive", "conf": "fc_sign_conf"}
_ROUTE_NEW = re.compile(r"\.new(\.[^./]+)?$")
_ROUTE_PROPOSED = re.compile(r"\.proposed\.md$", re.I)


def on(group_or_switch):
    try:
        if HERE not in sys.path:
            sys.path.insert(0, HERE)
        from roundb import roundb_on
        return roundb_on(GROUPS.get(group_or_switch, group_or_switch))
    except Exception:
        return False


# ---------------------------------------------------------------- the routes' own file names
def proposed_path(t):
    d, b = os.path.split(t)
    stem, ext = os.path.splitext(b)
    return os.path.join(d, stem + ".proposed" + (ext or ".md"))


def new_path(t):
    d, b = os.path.split(t)
    stem, ext = os.path.splitext(b)
    return os.path.join(d, stem + ".new" + ext)


def is_proposed(t):
    """A draft beside a canon file: the session loader never reads it, so it is not canon. Only while the canon sign that names it is on."""
    return bool(_ROUTE_PROPOSED.search(os.path.basename(t))) and on("canon")


def is_new_copy(t):
    """The data sign's own route. A stale one must not ask, or the sign would name a route that is refused headless."""
    return bool(_ROUTE_NEW.search(os.path.basename(t))) and on("data")


def clean_tracked(t):
    """True when git holds this exact file (coordinator ruling (d), 2026-11-03): tracked, with no change against HEAD. Modified, untracked or no repo -> False.
    Only decides whether a data sign sits on top of the ask; the ask itself is untouched."""
    d = os.path.dirname(t) or "/"
    try:
        if subprocess.run(["git", "-C", d, "ls-files", "--error-unmatch", "--", t], capture_output=True, timeout=5).returncode != 0:
            return False
        return subprocess.run(["git", "-C", d, "diff", "--quiet", "HEAD", "--", t], capture_output=True, timeout=5).returncode == 0
    except Exception:
        return False


# ---------------------------------------------------------------- the signs
def sop(t):
    return ("STOP. %s is one of the person's rulebooks (an SOP), and a session does not delete, move or rewrite it. "
            "Instead, ask the person in plain words whether they want it changed, then end your turn. Do nothing else to that file this turn." % t)


def canon_replace(t):
    return ("STOP. %s is the person's canon, and a session does not replace or rewrite it. "
            "Instead, write your new text to %s and tell the person it is there to compare. Leave %s exactly as it is this turn."
            % (t, proposed_path(t), os.path.basename(t)))


def canon_delete(t):
    return ("STOP. %s is the person's canon, and a session does not delete or move it. "
            "Instead, ask the person in plain words whether to retire it, then end your turn. Do nothing else to that file this turn." % t)


def claudemd(t):
    return ("STOP. %s is the instructions file for one of the person's projects, and a session does not delete, move or rewrite it. "
            "Instead, ask the person in plain words whether to change it, then end your turn. Do nothing else to it this turn." % t)


def claudemd_plugin(t):
    return ("STOP. %s is the plugin's own CLAUDE.md, and the next update replaces it. "
            "Instead, put what you wanted in your own ~/.claude/CLAUDE.md and tell the person it is there." % t)


def data_over(t):
    return ("STOP. %s is a data file holding the person's records, and a session does not overwrite or empty it. "
            "Instead, write your new version to %s beside it and tell the person it is there. Leave %s exactly as it is this turn."
            % (t, new_path(t), os.path.basename(t)))


def data_delete(t):
    return ("STOP. %s is a data file holding the person's records, and a session does not delete or move it. "
            "Instead, ask the person in plain words whether they want it gone, then end your turn. Do nothing else to that file this turn." % t)


def db(t):
    return ("STOP. %s is the person's database, and a session does not drop, empty or delete it. "
            "Instead, tell the person in plain words what you were about to do to it and ask whether they want it, then end your turn. "
            "Do nothing else to it this turn." % t)


def db_sql(what):
    return ("STOP. This command runs %s on a database, and a session does not drop or empty the person's data. "
            "Instead, tell the person in plain words what you were about to do and ask whether they want it, then end your turn." % what)


def folder(t):
    parent = os.path.dirname(t.rstrip("/")) or "/"
    arch = os.path.join(parent, "_archive")
    return ("STOP. %s is a whole folder of the person's files, and a session does not delete it. "
            "Instead, move the whole folder into _archive beside it (mkdir -p %s && mv -- %s %s/) and tell the person where it went. Delete nothing."
            % (t, shlex.quote(arch), shlex.quote(t), shlex.quote(arch)))


def drive(what):
    return ("STOP. %s, and a session does not do that alone. "
            "Instead, tell the person what would go and how many, ask whether they want it, then end your turn." % what)


def sheet_destructive():
    return ("STOP. This clears, deletes or mass-overwrites cells on a Google Sheet, and a session does not do that alone. "
            "Instead, tell the person the exact tab and range and ask whether they want it, then end your turn.")


def sheet_structural():
    return ("STOP. This changes a Google Sheet's structure (tabs, columns, formatting or protection), and a session does not do that alone. "
            "Instead, tell the person the exact change in plain words and ask whether they want it, then end your turn.")


def sheet_formula():
    return ("STOP. This write lands on a formula or lock cell of a Google Sheet, and a session does not overwrite those alone. "
            "Instead, show the person the cell's value before and after and ask whether they want it, then end your turn.")


def sheet_unknown():
    return ("STOP. This gws command hides its operation or its target behind a variable, so nobody can tell what it would do. "
            "Instead, write the operation and the spreadsheet ID out literally in the command.")


def conf():
    return ("STOP. placement.conf and roundB.conf switch Lifehack's checks off, and only the person changes them. "
            "Instead, tell the person the exact line to add and which file it goes in, then end your turn.")


def kind_sign(t, kind, over):
    """(group, target, text) for a fine-china file of `kind` (fine_china_ask.fc_file_kind), or None when it carries no sign."""
    if kind == "db":
        return ("db", t, db(t))
    if kind == "sop":
        return ("sops", t, sop(t))
    if kind == "canon":
        return ("canon", t, canon_replace(t) if over else canon_delete(t))
    if kind == "claudemd":
        return ("claudemd", t, claudemd(t))
    if kind == "data" and on("data") and not clean_tracked(t):
        return ("data", t, data_over(t) if over else data_delete(t))
    return None


# ---------------------------------------------------------------- spending a sign
def _state():
    return os.path.join(os.path.expanduser("~"), ".claude", "run", "fc-signs")


def _marker(payload, group, target):
    sid = str(payload.get("session_id") or os.environ.get("CLAUDE_CODE_SESSION_ID") or "")
    if not sid:
        return None
    who = re.sub(r"[^A-Za-z0-9_.-]", "_", sid)[:80] + "." + re.sub(r"[^A-Za-z0-9_.-]", "_", str(payload.get("agent_id") or "main"))[:40]
    return os.path.join(_state(), "%s.%s.%s" % (who, group, hashlib.sha1(target.encode("utf-8", "replace")).hexdigest()[:16]))


def _spend(mk):
    """True when THIS call took the marker (a parallel hook on the same target loses the race and falls through to its ask)."""
    os.makedirs(os.path.dirname(mk), exist_ok=True)
    os.close(os.open(mk, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))
    return True


def first(signs, payload, masked=False):
    """signs: [(group, target, text)] in the order they were found. -> the one sign to show, or None. One group per call, so one route per message;
    the group's other targets are named and spent with it. A later group shows on the next attempt."""
    shadow = os.environ.get("LIFEHACK_WATCH_SHADOW") == "1"
    pending = {}
    order = []
    for s in signs:
        if not s or not on(s[0]):
            continue
        mk = _marker(payload, s[0], s[1])
        if not mk or os.path.exists(mk):
            continue
        if s[0] not in pending:
            pending[s[0]] = {}
            order.append(s[0])
        pending[s[0]].setdefault(s[1], (mk, s[2]))
    if not order:
        return None
    items = pending[order[0]]
    if masked or shadow:
        return next(iter(items.values()))[1]
    taken = []
    try:
        for target, (mk, text) in items.items():
            try:
                _spend(mk)
                taken.append((target, text))
            except FileExistsError:
                pass
    except OSError:
        return None
    if not taken:
        return None
    extra = [t for t, _x in taken[1:]]
    return taken[0][1] + ((" The same goes for: " + ", ".join(extra) + ".") if extra else "")


def main(argv):
    try:
        payload = json.loads(sys.stdin.read() or "{}")
        text = argv[3]
        if text.startswith("@"):   # a sign by name: @canon_replace uses the target; @drive:what uses the words after the colon; @sheet_formula takes nothing
            name, _, arg = text[1:].partition(":")
            fn = {"canon_replace": lambda: canon_replace(argv[2]), "sop": lambda: sop(argv[2]), "drive": lambda: drive(arg),
                  "sheet_destructive": sheet_destructive, "sheet_structural": sheet_structural, "sheet_formula": sheet_formula, "sheet_unknown": sheet_unknown}[name]
            text = fn()
        msg = first([(argv[1], argv[2], text)], payload)
    except Exception as e:
        sys.stderr.write("fc_sign: skipped (%s)\n" % e)
        return 0
    if msg:
        sys.stderr.write(msg + "\n")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

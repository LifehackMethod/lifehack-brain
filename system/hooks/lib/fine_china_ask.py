#!/usr/bin/env python3
"""Engine for guard_fine_china_ask.sh (Round D rulings A.1 and A.6). Payload on stdin. ASKS only (permissionDecision "ask",
exit 0); never blocks. Each piece has its own switch in roundB.conf (all OFF = prints nothing):
  fc_db_delete_ask      deleting a local database file (.db .sqlite .sqlite3 .db3 .duckdb .mdb .accdb), or an obvious
                        DROP TABLE/DATABASE, TRUNCATE, or DELETE FROM <t> with no WHERE through sqlite3/psql/mysql/dropdb/duckdb.
  fc_folder_delete_ask  rm -r/-R/-rf/--recursive, rmdir, find <dir> -delete / -exec rm, and python shutil.rmtree / os.removedirs /
                        os.rmdir / Path(..).rmdir() in an executed -c or heredoc body, of a whole folder that is not empty.
                        The REAL target is judged: cd/pushd chains are followed (D-F04, 2026-11-02), a heredoc that is only
                        data is never read as commands, a symlink is not its folder. Throwaway folders never ask:
                        node_modules __pycache__ .venv venv dist build .cache .pytest_cache .next .tox .mypy_cache coverage,
                        anything under /tmp, /var/folders, $TMPDIR, a scratchpad/scratch folder, ~/.claude/run|projects|cache,
                        a git-IGNORED folder, an empty folder, or a folder that does not exist.
  fc_user_sop_ask       write over / edit / delete / move away an EXISTING SOP of the person (a .md in a sops/ folder or named *sop*.md)
                        outside the plugin tree (the plugin's own SOPs are covered by the harness-write and shell-overwrite guards).
                        New files and appends (>>) pass.
  fc_placement_conf_ask (also roundB.conf, the plugin's switch file: an AI must not switch a guard off) ANY AI write (Write/Edit/redirect/tee/cp/sed -i/append, even a new file) to ~/.config/lifehack/placement.conf,
                        the user's own override file. Only a person's Yes changes it.
  fc_claudemd_ask       (2026-11-01, plan PHASE 3b.8 item 5a) a Write/Edit/MultiEdit, or a Bash write (redirect, append, tee, sed -i, cp/mv onto it), to an
                        EXISTING file named CLAUDE.md, anywhere. The ask carries a short diff (Write/Edit) so the person sees what changes.
                        A brand-new CLAUDE.md (nothing to lose) and reads (cat, grep, Read) never ask.
  fc_claudemd_plugin_copy (5b) the same write aimed at the plugin's OWN CLAUDE.md copy (under ~/.claude/plugins, or the plugin root) on a machine that is
                        NOT the maintainer's self-repo: the ask says it is replaced on the next update and to use ~/.claude/CLAUDE.md. Works alone or with
                        fc_claudemd_ask (then this message replaces the general one for that file). Maintainer self-repo = the plugin root is a code
                        zone listed in <personal-code>/code-zones.txt (shared/person_roots.py), or LIFEHACK_SANDBOX=V2, or a git work tree outside ~/.claude/plugins.
  claudemd_len_advisory (5c) NOT an ask: when a Write/Edit/MultiEdit leaves a CLAUDE.md over 200 lines (and it grows, or crosses 200), hand the model one
                        advisory line (PreToolUse additionalContext, no permission decision). 200 is the official Claude Code figure ("target under 200
                        lines per CLAUDE.md file", code.claude.com/docs/en/memory). Bash writes are not measured.
These have NO off switch of the user's kind: placement.conf is never read here.
Fail posture: any internal error prints nothing (allow).
"""
import fnmatch, glob, json, os, re, shlex, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
HOME = os.path.expanduser("~")
DB_EXT = (".db", ".sqlite", ".sqlite3", ".db3", ".duckdb", ".mdb", ".accdb", ".sdb")
THROWAWAY = {"node_modules", "__pycache__", ".venv", "venv", "env", "dist", "build", ".cache", ".pytest_cache", ".next", ".tox",
             ".mypy_cache", ".ruff_cache", "coverage", ".gradle", ".parcel-cache", ".turbo", ".nuxt", "scratchpad", "scratch", ".tmp", "tmp"}
SQL_TOOLS = {"sqlite3", "psql", "mysql", "mariadb", "dropdb", "duckdb", "sqlcipher", "mongosh", "mongo", "python", "python3", "node", "ruby"}
SQL_RX = re.compile(r"\bDROP\s+(TABLE|DATABASE|SCHEMA)\b|\bTRUNCATE\s+(TABLE\s+)?\w|\bDELETE\s+FROM\s+[\w\.\"`\[\]]+\s*(;|\"|'|\)|$)", re.I)
OUT = []
ADV = []
CLAUDEMD_MAX_LINES = 200


def on(name):
    try:
        from roundb import roundb_on
        return roundb_on(name)
    except Exception:
        return False


def under(p, root):
    return p == root or p.startswith(root.rstrip("/") + "/")


def tmpish(p):
    rs = ["/tmp", "/private/tmp", "/var/folders", "/private/var/folders", os.path.realpath(os.environ.get("TMPDIR", "/tmp"))]
    return any(under(p, r) for r in rs) and not under(p, os.path.realpath(HOME))


def resolve(p, cwd):
    p = os.path.expandvars(os.path.expanduser(p))
    if not os.path.isabs(p):
        p = os.path.join(cwd, p)
    return os.path.realpath(p)


def is_db(t):
    return t.lower().endswith(DB_EXT)


def is_user_sop(t, code):
    if not t.lower().endswith(".md") or t.endswith(".history.md") or tmpish(t):
        return False
    if code and under(t, code):
        return False   # the plugin's own tree: governed by guard_harness_write / fc_shell_overwrite
    parts = t.lower().split("/")
    base = parts[-1]
    return "sops" in parts[:-1] or "sop" in parts[:-1] or bool(re.search(r"(^|[-_. ])sops?([-_. ]|\.md$)", base))


def is_conf(t):
    """placement.conf (the person's override file) or roundB.conf (the plugin's switch file: the AI must not switch guards off itself, P-54)."""
    return (t == os.path.realpath(os.path.join(HOME, ".config", "lifehack", "placement.conf")) or t.endswith("/.config/lifehack/placement.conf")
            or t.endswith("/system/hooks/roundB.conf"))


def gitignored(d):
    import subprocess
    try:
        return subprocess.run(["git", "-C", os.path.dirname(d) or "/", "check-ignore", "-q", d], capture_output=True, timeout=5).returncode == 0
    except Exception:
        return False


# Coordinator ruling (c), 2026-11-02: well-known REGENERABLE build/dependency folders never ask when they are the folder
# being deleted (FINAL path segment, exact name). `target` is final-segment only: as a whole-path segment it is too common a word.
REGENERABLE = {"node_modules", "__pycache__", ".venv", "venv", "dist", "build", "target", ".cache", ".pytest_cache", ".next", "coverage"}


def throwaway_dir(d):
    parts = d.split("/")
    if os.path.basename(d.rstrip("/")) in REGENERABLE:
        return True
    if any(p in THROWAWAY for p in parts):
        return True
    if tmpish(d) or any(under(d, os.path.join(HOME, ".claude", s)) for s in ("run", "projects", "cache", "shell-snapshots", "plugins/cache")):
        return True
    if under(d, os.path.join(HOME, "Library", "Caches")) or under(d, os.path.join(HOME, ".cache")):
        return True
    try:
        if not os.listdir(d):
            return True
    except OSError:
        return True
    return gitignored(d)


def ask(msg):
    OUT.append(msg)


def split_segments(cmd, depth=0):
    """-> list of word lists, one per simple command, reading into bash -c / sh -c / eval bodies."""
    lex = shlex.shlex(cmd, posix=True, punctuation_chars="();<>|&\n")
    lex.whitespace = " \t\r"
    lex.whitespace_split = True
    try:
        toks = list(lex)
    except ValueError:
        return []
    segs, cur = [], []
    for t in toks:
        if t and set(t) <= set(";&|\n()<>"):
            segs.append(cur); cur = []
        else:
            cur.append(t)
    segs.append(cur)
    out = []
    for s in segs:
        while s and (re.fullmatch(r"\w+=.*", s[0]) or os.path.basename(s[0]) in ("sudo", "command", "env", "exec", "nohup", "time", "nice", "xargs")
                     or (s[0].startswith("-") and len(s) > 1)):
            s = s[1:]
        if not s:
            continue
        v = os.path.basename(s[0])
        body = None
        if v in ("bash", "sh", "zsh", "dash", "ksh"):
            for k in range(1, len(s) - 1):
                if re.fullmatch(r"-[A-Za-z]*c[A-Za-z]*", s[k]):
                    body = s[k + 1]; break
        elif v == "eval":
            body = " ".join(s[1:])
        if body and depth < 3:
            out.extend(split_segments(body, depth + 1))
        else:
            out.append(s)
    return out


def expand(arg, cwd):
    if "$" in arg.replace("$HOME", "").replace("${HOME}", "") or "`" in arg:
        return []   # unresolvable variable: cannot judge (LIMIT)
    a = os.path.expandvars(os.path.expanduser(arg))
    if not os.path.isabs(a):
        a = os.path.join(cwd, a)
    if any(c in a for c in "*?["):
        return [os.path.realpath(m) for m in glob.glob(a)]
    return [os.path.realpath(a)]


CONF_RX = re.compile(r"placement\.conf|roundB\.conf")

# ---------------------------------------------------------------- D-F04 (2026-11-02): follow cd, read executed code
# The incident: `cd <exam>/notes && rm -r 2024-sabbatical` with the session cwd one level up. The old loop resolved every
# argument against the SESSION cwd, so the target became <exam>/2024-sabbatical, which does not exist, and was skipped.
# walk() returns (words, cwd) per simple command with cd/pushd chains followed, ( ) subshells restored, a cd inside a
# pipeline ignored, redirections not taken for commands, and heredoc BODIES removed from the shell text (a heredoc that
# is only data never looks like a command; one an interpreter runs is returned separately for py_deletes / a shell walk).
_HD_SINK_PY = re.compile(r"^(?:python|pypy)[\d.]*$")
_HD_SINK_SH = {"bash", "sh", "zsh", "dash", "ksh"}


def _gws():
    try:
        import gws_guard
        return gws_guard
    except Exception:
        return None


def _heredoc_split(cmd):
    """-> (cmd with every heredoc body cut out, [(op_start_in_stripped_cmd, body, family)]). family: 'py' | 'sh' | None
    (None = data, or an interpreter we do not read). Without gws_guard: (cmd, []) = old behaviour."""
    g = _gws()
    if g is None:
        return cmd, []
    cmd = cmd.replace("\\\n", " ")
    out, bodies, last = [], [], 0
    try:
        for m, _q, bs, be, _r in g._heredocs(cmd):
            fam = None
            if g._heredoc_executed(cmd, m.start(), m.end()):
                ls = cmd.rfind("\n", 0, m.start()) + 1
                le = cmd.find("\n", m.end()); le = len(cmd) if le == -1 else le
                before = re.sub(r"^[\s$(`{!]+", "", g._STMT.split(cmd[ls:m.start()])[-1])
                w, _a = g._cmd_word(before.lstrip("({ ").split())
                if not w:
                    pm = re.match(r"[^;&|]*\|(?!\|)\s*([^;&|]*)", cmd[m.end():le])
                    w, _a = g._cmd_word(pm.group(1).split()) if pm else ("", [])
                elif not g._runs_stdin(w, _a):
                    pm = re.match(r"[^;&|]*\|(?!\|)\s*([^;&|]*)", cmd[m.end():le])
                    w, _a = g._cmd_word(pm.group(1).split()) if pm else (w, _a)
                fam = "py" if _HD_SINK_PY.match(w) else ("sh" if w in _HD_SINK_SH else None)
            pos = sum(len(x) for x in out) + (m.start() - last)   # where the << operator lands in the stripped text
            out.append(cmd[last:bs])
            bodies.append((pos, cmd[bs:be], fam))
            nl = cmd.find("\n", be)            # the terminator line goes too (its newline stays)
            last = len(cmd) if nl == -1 else nl
    except Exception:
        return cmd, []
    out.append(cmd[last:])
    return "".join(out), bodies


def _cd_dest(words, cwd):
    """Where a cd/pushd leaves the shell; None = cannot know (cd -, a variable, popd)."""
    v = os.path.basename(words[0])
    if v == "popd":
        return None
    args = [a for a in words[1:] if not (a.startswith("-") and a != "-")]
    if not args:
        return os.path.realpath(HOME) if v == "cd" else None
    a = args[0]
    if a == "-" or "`" in a or "$" in a.replace("$HOME", "").replace("${HOME}", ""):
        return None
    a = os.path.expandvars(os.path.expanduser(a))
    if not os.path.isabs(a):
        if cwd is None:
            return None
        a = os.path.join(cwd, a)
    return os.path.realpath(a)


def walk(cmd, cwd, depth=0):
    """-> [(words, cwd, py_bodies)] per simple command, cd chains followed. py_bodies: python code this command runs."""
    shell, bodies = _heredoc_split(cmd) if depth < 4 else (cmd, [])
    lex = shlex.shlex(shell, posix=True, punctuation_chars="();<>|&\n")
    lex.whitespace = " \t\r"
    lex.whitespace_split = True
    try:
        toks = list(lex)
    except ValueError:
        return []
    items, cur, skip = [], [], False
    for t in toks:
        if skip:
            skip = False; continue
        if t and set(t) <= set(";&|\n()<>"):
            if ("<" in t or ">" in t) and not set(t) & set(";|\n()"):
                if cur and cur[-1].isdigit():
                    cur.pop()   # the fd number of 2>/dev/null, not an argument
                skip = True     # the redirect target / fd / heredoc delimiter is not an argument
                continue
            items.append(("seg", cur)); cur = []
            items.append(("sep", t))
        else:
            cur.append(t)
    items.append(("seg", cur))
    out, stack, cwd_now = [], [], cwd
    segs = [i for i, it in enumerate(items) if it[0] == "seg"]
    for idx, (kind, val) in enumerate(items):
        if kind == "sep":
            for ch in val:
                if ch == "(":
                    stack.append(cwd_now)
                elif ch == ")" and stack:
                    cwd_now = stack.pop()
            continue
        s = list(val)
        while s and (re.fullmatch(r"\w+=.*", s[0]) or os.path.basename(s[0]) in ("sudo", "command", "env", "exec", "nohup", "time", "nice", "xargs", "builtin")
                     or (s[0].startswith("-") and len(s) > 1)):
            s = s[1:]
        if not s:
            continue
        prev_sep = items[idx - 1][1] if idx > 0 else None
        next_sep = items[idx + 1][1] if idx + 1 < len(items) else None
        in_pipe = prev_sep in ("|", "|&") or next_sep in ("|", "|&")
        v = os.path.basename(s[0])
        if v in ("cd", "pushd", "popd"):
            if not in_pipe:
                cwd_now = _cd_dest(s, cwd_now)
            continue
        body, py = None, []
        if v in _HD_SINK_SH:
            for k in range(1, len(s) - 1):
                if re.fullmatch(r"-[A-Za-z]*c[A-Za-z]*", s[k]):
                    body = s[k + 1]; break
        elif v == "eval":
            body = " ".join(s[1:])
        elif _HD_SINK_PY.match(v):
            for k in range(1, len(s) - 1):
                if s[k] == "-c" or re.fullmatch(r"-[A-Za-z]*c", s[k]):
                    py.append(s[k + 1]); break
        if body is not None and depth < 3:
            out.extend(walk(body, cwd_now, depth + 1))
        else:
            out.append((s, cwd_now, py))
    # executed heredoc bodies: the cwd is the one in force where the << operator sits
    for pos, text, fam in bodies:
        if fam is None:
            continue
        hcwd = _final_cwd(shell[:pos], cwd)
        if fam == "py":
            out.append((["python3", "-"], hcwd, [text]))
        elif depth < 3:
            out.extend(walk(text, hcwd, depth + 1))
    return out


def _final_cwd(prefix, cwd):
    """The shell cwd after running `prefix` (cd chains only)."""
    lex = shlex.shlex(prefix, posix=True, punctuation_chars="();<>|&\n")
    lex.whitespace = " \t\r"
    lex.whitespace_split = True
    try:
        toks = list(lex)
    except ValueError:
        return cwd
    segs, cur, seps = [], [], []
    for t in toks:
        if t and set(t) <= set(";&|\n()") :
            segs.append(cur); seps.append(t); cur = []
        elif t and set(t) <= set("<>&"):
            continue
        else:
            cur.append(t)
    segs.append(cur)
    stack, now = [], cwd
    for i, s in enumerate(segs):
        if i > 0:
            for ch in seps[i - 1]:
                if ch == "(":
                    stack.append(now)
                elif ch == ")" and stack:
                    now = stack.pop()
        while s and (re.fullmatch(r"\w+=.*", s[0]) or s[0] in ("builtin", "command")):
            s = s[1:]
        if s and os.path.basename(s[0]) in ("cd", "pushd", "popd"):
            in_pipe = (i > 0 and seps[i - 1] == "|") or (i < len(seps) and seps[i] == "|")
            if not in_pipe:
                now = _cd_dest(s, now)
    return now


# python forms that remove a folder: shutil.rmtree(x), os.removedirs(x), os.rmdir(x), Path(x).rmdir(), <var>.rmdir()
_PY_CALL = re.compile(r"(?P<fn>(?:\bshutil\s*\.\s*)?(?<![\w.])rmtree|\bshutil\s*\.\s*rmtree|\bos\s*\.\s*removedirs|\bos\s*\.\s*rmdir)\s*\(\s*(?P<arg>[^,)]*(?:\([^()]*\))?[^,)]*)")
_PY_PATH_RMDIR = re.compile(r"(?P<expr>(?:\bpathlib\s*\.\s*)?\bPath\s*\((?:[^()]|\([^()]*\))*\)|\b[A-Za-z_]\w*)\s*\.\s*rmdir\s*\(\s*\)")
_PY_ASSIGN = re.compile(r"^\s*(?P<name>[A-Za-z_]\w*)\s*=\s*(?P<expr>[^\n;]+)", re.M)
_PY_STR = re.compile(r"""^[rRbBuUfF]{0,2}(?:'([^'\\]*)'|"([^"\\]*)")$""")


def _py_value(expr, names, depth=0):
    """A python expression -> the path string it names, or None. Literals, os.path.expanduser/join, Path(...), Path.home(),
    a / b, and names bound to one of those earlier in the same body."""
    e = expr.strip().rstrip(")").strip() if expr.strip().count(")") > expr.strip().count("(") else expr.strip()
    if depth > 4 or not e:
        return None
    m = _PY_STR.match(e)
    if m:
        s = m.group(1) if m.group(1) is not None else m.group(2)
        return None if e[:1] in "fF" and "{" in s else s
    if re.fullmatch(r"[A-Za-z_]\w*", e):
        return names.get(e)
    if re.fullmatch(r"(?:pathlib\s*\.\s*)?Path\s*\.\s*home\s*\(\s*\)", e):
        return HOME
    if "/" in e and not _PY_STR.match(e):
        parts = _split_top(e, "/")
        if len(parts) > 1:
            vals = [_py_value(p, names, depth + 1) for p in parts]
            return None if any(v is None for v in vals) else os.path.join(*vals)
    m = re.fullmatch(r"(?:(?:pathlib\s*\.\s*)?Path|os\s*\.\s*path\s*\.\s*(?:expanduser|abspath|realpath|join)|str)\s*\((.*)\)\s*(?:\.\s*(?:expanduser|resolve|absolute)\s*\(\s*\))*", e, re.S)
    if m:
        inner = _split_top(m.group(1), ",")
        vals = [_py_value(p, names, depth + 1) for p in inner if p.strip()]
        if not vals or any(v is None for v in vals):
            return None
        return os.path.expanduser(os.path.join(*vals))
    return None


def _split_top(s, sep):
    parts, depth, cur, q = [], 0, "", None
    for ch in s:
        if q:
            cur += ch
            if ch == q:
                q = None
            continue
        if ch in "'\"":
            q = ch
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == sep and depth == 0:
            parts.append(cur); cur = ""
        else:
            cur += ch
    parts.append(cur)
    return parts


def py_deletes(code):
    """-> [(path or None, kind)] for every folder-removing call in python `code`. None = the argument could not be read."""
    names = {}
    for m in _PY_ASSIGN.finditer(code):
        v = _py_value(m.group("expr"), names)
        if v is not None:
            names[m.group("name")] = v
    found = []
    for m in _PY_CALL.finditer(code):
        kind = "rmtree" if "rmtree" in m.group("fn") else ("removedirs" if "removedirs" in m.group("fn") else "rmdir")
        found.append((_py_value(m.group("arg"), names), kind))
    for m in _PY_PATH_RMDIR.finditer(code):
        ex = m.group("expr")
        if ex in ("os", "shutil"):
            continue
        found.append((_py_value(ex, names), "Path.rmdir"))
    return found


def folder_at_risk(t):
    """The real target is a folder with something in it, and not a throwaway one."""
    return os.path.isdir(t) and not throwaway_dir(t)


def _plain(a, cwd):
    """-> [(resolved, raw)] for one shell argument (raw kept so a symlink is seen as a symlink)."""
    if cwd is None and not os.path.isabs(os.path.expanduser(a)):
        return []
    res = expand(a, cwd or "/")
    if len(res) == 1 and not any(c in a for c in "*?["):
        raw = os.path.expandvars(os.path.expanduser(a))
        raw = raw if os.path.isabs(raw) else os.path.join(cwd or "/", raw)
        return [(res[0], raw)]
    return [(r, r) for r in res]


def check_bash(cmd, cwd, code):
    sw_db, sw_dir, sw_sop, sw_conf = on("fc_db_delete_ask"), on("fc_folder_delete_ask"), on("fc_user_sop_ask"), on("fc_placement_conf_ask")
    if sw_conf and CONF_RX.search(cmd):
        if conf_write_in_bash(cmd, cwd):
            ask("ASK FIRST: this command changes ~/.config/lifehack/placement.conf or the plugin's roundB.conf, the files that switch Lifehack's checks and guards off. "
                "Only the person decides that. WAY-THROUGH: press Yes only if the person asked for exactly this change; otherwise stop and tell them which line "
                "they can add themselves. RULE: switch fc_placement_conf_ask in system/hooks/roundB.conf.")
    for w, scwd, py_bodies in walk(cmd, cwd):   # D-F04: each command is judged in the cwd its own cd chain left it in
        v = os.path.basename(w[0])
        args = [a for a in w[1:]]
        if v in ("rm", "unlink", "shred", "trash", "rmdir"):
            flags = "".join(a for a in args if a.startswith("-") and not a.startswith("--"))
            recursive = bool(re.search(r"[rR]", flags)) or "--recursive" in args
            for a in [x for x in args if not x.startswith("-")]:
                for t, raw in _plain(a, scwd):
                    if not os.path.exists(t) and not os.path.islink(t):
                        continue
                    if sw_db and is_db(t) and os.path.isfile(t) and not tmpish(t) and not any(p in THROWAWAY for p in t.split("/")):
                        ask(db_msg(t))
                    elif sw_sop and is_user_sop(t, code) and os.path.isfile(t):
                        ask(sop_msg(t, "deletes"))
                    elif sw_dir and ((v == "rm" and recursive) or v == "rmdir") and not (os.path.islink(raw) and not a.endswith("/")) \
                            and folder_at_risk(t):
                        ask(dir_msg(t) + (" (via rmdir)" if v == "rmdir" else ""))
        elif v == "find" and sw_dir and ("-delete" in args or any(x in ("-exec", "-execdir", "-ok", "-okdir") and k + 1 < len(args)
                                                                 and os.path.basename(args[k + 1]) in ("rm", "rmdir") for k, x in enumerate(args))):
            roots = []
            for a in args:
                if a.startswith("-") or a in ("(", "!"):
                    break
                roots.append(a)
            for a in roots or ["."]:
                for t, _raw in _plain(a, scwd):
                    if folder_at_risk(t):
                        ask(dir_msg(t) + " (via find -delete / -exec rm)")
        elif v in ("mv",) and sw_sop:
            src = [a for a in args if not a.startswith("-")][:-1]
            for s in src:
                for t in expand(s, scwd or cwd):
                    if is_user_sop(t, code) and os.path.isfile(t):
                        ask(sop_msg(t, "moves away"))
        elif v in SQL_TOOLS and sw_db and SQL_RX.search(" ".join(w)):
            ask("ASK FIRST: this command drops or empties data in a local database (%s). A database is fine china: what it held may not come back. "
                "WAY-THROUGH: press Yes only if the person asked for exactly this and a copy exists; otherwise stop and tell them what you wanted to delete. "
                "RULE: switch fc_db_delete_ask in system/hooks/roundB.conf." % SQL_RX.search(" ".join(w)).group(0).strip())
        if sw_dir and py_bodies:
            for body in py_bodies:
                for p, kind in py_deletes(body):
                    if p is None:
                        if kind == "rmtree":   # unreadable argument: the old ask, kept (an ASK guard may over-ask here; never under-ask)
                            ask("ASK FIRST: this python command deletes a whole folder tree (rmtree). Folders are fine china: it does not go to the Trash. "
                                "WAY-THROUGH: press Yes only if the person asked for it; otherwise name the folder to them first. RULE: switch fc_folder_delete_ask in system/hooks/roundB.conf.")
                        continue
                    if scwd is None and not os.path.isabs(os.path.expanduser(p)):
                        continue
                    t = resolve(p, scwd or "/")
                    if folder_at_risk(t):
                        ask(dir_msg(t) + " (via python %s)" % kind)
    # redirect-truncate / overwrite of a database or SOP, and cp/mv/sed -i onto an SOP (build_mode.bash_ops reads these)
    try:
        import build_mode
        for o in build_mode.bash_ops(cmd, cwd):
            t = o.get("target", "")
            if sw_conf and is_conf(t):
                continue   # handled above by the text test (any write, append included)
            if o["verb"] in ("worktree",):
                continue
            ow = o["verb"] in (">", "dd", "tee", "cp", "mv", "install", "rsync", "sed-inplace", "truncate-inplace") and not o.get("append")
            if ow and os.path.exists(t):
                if sw_sop and is_user_sop(t, code) and os.path.isfile(t):
                    ask(sop_msg(t, "overwrites"))
                elif sw_db and is_db(t) and os.path.isfile(t) and not tmpish(t) and o["verb"] in (">", "truncate-inplace", "dd"):
                    ask(db_msg(t))
    except Exception as e:
        sys.stderr.write("guard_fine_china_ask: parse skipped (%s)\n" % e)


def conf_write_in_bash(cmd, cwd):
    """True when the command writes (not only reads) placement.conf."""
    if re.search(r">>?\s*['\"]?[^\s|;&]*(placement|roundB)\.conf", cmd) or re.search(r"\btee\b[^|;&]*(placement|roundB)\.conf", cmd):
        return True
    for w in split_segments(cmd):
        v = os.path.basename(w[0])
        if not any(CONF_RX.search(a) for a in w[1:]):
            continue
        if v in ("cat", "grep", "egrep", "head", "tail", "less", "more", "ls", "wc", "stat", "diff", "file", "awk", "sort", "bat", "cut", "nl", "md5", "shasum", "test", "["):
            continue
        if v in ("rm", "mv", "cp", "install", "ln", "truncate", "dd", "tee", "rsync", "sed", "perl", "python", "python3", "ruby", "node", "bash", "sh", "zsh", "printf", "echo", "touch", "ed", "ex", "vi", "vim", "nano", "chmod"):
            if v == "sed" and not any(re.fullmatch(r"-[A-Za-z]*i\S*", a) for a in w[1:]):
                continue
            return True
    return False


def is_claudemd(t):
    return os.path.basename(t).lower() == "claude.md"


def plugins_dir():
    return os.path.realpath(os.path.join(HOME, ".claude", "plugins"))


def maintainer_self_repo(code):
    """True when the plugin root is the maintainer's own working checkout (not an installed copy): listed as a code zone in
    <personal-code>/code-zones.txt, or the V2 sandbox tag, or a git work tree outside ~/.claude/plugins."""
    if not code or under(code, plugins_dir()):
        return False
    if os.environ.get("LIFEHACK_SANDBOX") == "V2":
        return True
    try:
        sd = os.path.join(code, "shared")
        if sd not in sys.path:
            sys.path.insert(0, sd)
        import person_roots
        if code in person_roots.code_zones():
            return True
    except Exception as e:
        sys.stderr.write("guard_fine_china_ask: code-zones lookup skipped (%s)\n" % e)   # then the .git test below decides
    return os.path.exists(os.path.join(code, ".git"))


def plugin_copy_msg(t):
    return ("ASK FIRST: %s is the plugin's own CLAUDE.md, and it is replaced on the next update, so an edit here is lost. "
            "WAY-THROUGH: put your own rules in your own ~/.claude/CLAUDE.md instead (it is yours and updates never touch it); press Yes only if the person "
            "asked for this file itself to change. RULE: switch fc_claudemd_plugin_copy in system/hooks/roundB.conf." % t)


def claudemd_msg(t, how):
    return ("ASK FIRST: this %s a CLAUDE.md (%s). A CLAUDE.md is the person's standing instructions, loaded into every session: fine china. "
            "WAY-THROUGH: show the person the change (diff below when available) and press Yes only if they asked for it; otherwise stop and tell them what you wanted to change. "
            "RULE: switch fc_claudemd_ask in system/hooks/roundB.conf." % (how, t))


def claudemd_verdict(t, how, code, diff=""):
    """Ask text for a write to an existing CLAUDE.md, or None."""
    if not is_claudemd(t) or not os.path.isfile(t):
        return None
    plugin_copy = under(t, plugins_dir()) or bool(code and under(t, code) and not maintainer_self_repo(code))
    if plugin_copy and on("fc_claudemd_plugin_copy"):
        return plugin_copy_msg(t)
    if on("fc_claudemd_ask"):
        return claudemd_msg(t, how) + ((" DIFF: " + diff) if diff else "")
    return None


def short_diff(t, tool, ti):
    import difflib
    try:
        if tool == "Write":
            old = open(t, encoding="utf-8", errors="replace").read().splitlines()
            new = (ti.get("content") or "").splitlines()
            d = [l for l in difflib.unified_diff(old, new, "before", "after", lineterm="", n=0)]
        else:
            edits = ti.get("edits") if tool == "MultiEdit" else [ti]
            d = []
            for e in edits or []:
                d += ["-" + l for l in (e.get("old_string") or "").splitlines()] + ["+" + l for l in (e.get("new_string") or "").splitlines()]
        txt = " / ".join(x[:120] for x in d)
        return txt[:700] + (" ...(cut)" if len(txt) > 700 else "")
    except Exception:
        return ""


def resulting_text(t, tool, ti):
    """-> (old_text, new_text) of the file after the tool runs, or None when it cannot be worked out."""
    try:
        old = open(t, encoding="utf-8", errors="replace").read() if os.path.isfile(t) else ""
        if tool == "Write":
            return old, ti.get("content") or ""
        new = old
        for e in (ti.get("edits") if tool == "MultiEdit" else [ti]) or []:
            o, n = e.get("old_string") or "", e.get("new_string") or ""
            if not o or o not in new:
                return None
            new = new.replace(o, n) if e.get("replace_all") else new.replace(o, n, 1)
        return old, new
    except Exception:
        return None


def length_advisory(t, tool, ti):
    if not on("claudemd_len_advisory") or not is_claudemd(t):
        return
    r = resulting_text(t, tool, ti)
    if not r:
        return
    n_old, n_new = len(r[0].splitlines()), len(r[1].splitlines())
    if n_new > CLAUDEMD_MAX_LINES and (n_old <= CLAUDEMD_MAX_LINES or n_new > n_old):
        ADV.append("%s will be %d lines after this edit. Claude Code's own guidance is to keep each CLAUDE.md under %d lines (longer files use more context and "
                   "reduce adherence). Advisory only; consider moving the parts that matter for only some work into path-scoped rules or a skill. "
                   "Switch claudemd_len_advisory in system/hooks/roundB.conf." % (t, n_new, CLAUDEMD_MAX_LINES))


def claudemd_bash(cmd, cwd, code):
    if not (on("fc_claudemd_ask") or on("fc_claudemd_plugin_copy")) or "claude.md" not in cmd.lower():
        return
    try:
        import build_mode
        for o in build_mode.bash_ops(cmd, cwd):
            if o["verb"] in ("worktree", "mkdir", "touch", "ln"):
                continue
            m = claudemd_verdict(o.get("target", ""), "writes to", code)
            if m:
                ask(m)
    except Exception as e:
        sys.stderr.write("guard_fine_china_ask: claudemd parse skipped (%s)\n" % e)


def db_msg(t):
    return ("ASK FIRST: this deletes or empties a local database file (%s). A database is fine china: once it is gone, what it held may not come back. "
            "WAY-THROUGH: press Yes only if the person asked for this and a copy exists; otherwise stop and tell them which file you wanted to remove. "
            "RULE: switch fc_db_delete_ask in system/hooks/roundB.conf." % t)


def dir_msg(t):
    return ("ASK FIRST: this deletes a whole folder (%s) and everything in it; it does not go to the Trash. A folder is fine china. "
            "(Throwaway folders such as node_modules, build, dist, .venv and temp folders never ask.) "
            "WAY-THROUGH: press Yes only if the person asked for this folder to go; otherwise name it to them and wait. "
            "RULE: switch fc_folder_delete_ask in system/hooks/roundB.conf." % t)


def sop_msg(t, what):
    return ("ASK FIRST: this %s the person's own SOP (%s). An SOP is the person's own standing procedure: fine china. "
            "WAY-THROUGH: press Yes only if the person asked for this change to this SOP; otherwise show them the change you want and wait. "
            "RULE: switch fc_user_sop_ask in system/hooks/roundB.conf." % (what, t))


def main_inner():
    d = json.loads(sys.stdin.read())
    tool, ti, cwd = d.get("tool_name", ""), d.get("tool_input") or {}, d.get("cwd") or os.getcwd()
    code = None
    try:
        import build_mode
        code = build_mode.code_root()
    except Exception:
        pass
    if tool in ("Write", "Edit", "MultiEdit"):
        fp = ti.get("file_path") or ""
        if not fp:
            return
        t = resolve(fp, cwd)
        if on("fc_placement_conf_ask") and is_conf(t):
            ask("ASK FIRST: this writes ~/.config/lifehack/placement.conf or the plugin's roundB.conf, the files that switch Lifehack's checks and guards off. "
                "Only the person decides that. WAY-THROUGH: press Yes only if the person asked for exactly this change; otherwise tell them which line they can add themselves. "
                "RULE: switch fc_placement_conf_ask in system/hooks/roundB.conf.")
        elif on("fc_user_sop_ask") and is_user_sop(t, code) and os.path.isfile(t):
            ask(sop_msg(t, "replaces" if tool == "Write" else "edits"))
        if is_claudemd(t):
            m = claudemd_verdict(t, "replaces" if tool == "Write" else "edits", code, short_diff(t, tool, ti) if on("fc_claudemd_ask") else "")
            if m:
                ask(m)
            length_advisory(t, tool, ti)
    elif tool == "Bash":
        check_bash(ti.get("command", ""), cwd, code)
        claudemd_bash(ti.get("command", ""), cwd, code)


def main():
    try:
        main_inner()
    except BaseException as e:
        sys.stderr.write("guard_fine_china_ask: internal error (%s: %s); allowing\n" % (type(e).__name__, e))
        return 0
    if OUT or ADV:
        h = {"hookEventName": "PreToolUse"}
        if OUT:
            h.update(permissionDecision="ask", permissionDecisionReason=" | ".join(dict.fromkeys(OUT))[:1800])
        if ADV:
            h["additionalContext"] = " ".join(dict.fromkeys(ADV))[:1500]
        print(json.dumps({"hookSpecificOutput": h}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

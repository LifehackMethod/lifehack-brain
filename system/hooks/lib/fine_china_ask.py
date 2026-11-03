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
                        the user's own override file. Only a person's Yes changes it. (2026-11-02) Bash asks only when the command can WRITE
                        the file (conf_write_in_bash: real targets, cd chains followed); naming it in ls/cat/grep/find/echo or read-only python never asks.
  fc_claudemd_ask       (2026-11-01, plan PHASE 3b.8 item 5a) a Write/Edit/MultiEdit, or a Bash write (redirect, append, tee, sed -i, cp/mv onto it), to an
                        EXISTING file named CLAUDE.md, anywhere. The ask carries a short diff (Write/Edit) so the person sees what changes.
                        A brand-new CLAUDE.md (nothing to lose) and reads (cat, grep, Read) never ask.
                        (2026-11-02) also a shell rm / unlink / shred / trash, or mv of the file, of an EXISTING CLAUDE.md outside a
                        throwaway/temp path, as the python delete already did.
  fc_claudemd_plugin_copy (5b) the same write aimed at the plugin's OWN CLAUDE.md copy (under ~/.claude/plugins, or the plugin root) on a machine that is
                        NOT the maintainer's self-repo: the ask says it is replaced on the next update and to use ~/.claude/CLAUDE.md. Works alone or with
                        fc_claudemd_ask (then this message replaces the general one for that file). Maintainer self-repo = the plugin root is a code
                        zone listed in <personal-code>/code-zones.txt (shared/person_roots.py), or LIFEHACK_SANDBOX=V2, or a git work tree outside ~/.claude/plugins.
  claudemd_len_advisory (5c) NOT an ask: when a Write/Edit/MultiEdit leaves a CLAUDE.md over 200 lines (and it grows, or crosses 200), hand the model one
                        advisory line (PreToolUse additionalContext, no permission decision). 200 is the official Claude Code figure ("target under 200
                        lines per CLAUDE.md file", code.claude.com/docs/en/memory). Bash writes are not measured.
  fc_python_delete_ask  (2026-11-02, direct-hook exam D-F01/F08/F20) python os.remove / os.unlink / Path.unlink, or os.rename / os.replace /
                        shutil.move / Path.rename AWAY, of an existing fine-china FILE, in an executed -c / heredoc / `-` body (walk() reads them).
  fc_python_rewrite_ask (D-F09/F13) python open(p,'w'), Path.write_text/write_bytes/open('w'), os.truncate, or a move/replace/copy ONTO an
                        existing fine-china file. A fine-china file (fc_file_kind) is only what the existing pieces already protect: a database
                        (is_db), the person's SOP, a plugin SOP or canon file (build_mode.protected_doc), a data file (build_mode.data_file_target:
                        existing, non-empty, not git-ignored, not touched in the last 10 minutes), a CLAUDE.md. Relative paths resolve through the
                        command's own cd chain. Temp, scratch, throwaway and regenerable folders never ask; new files never ask.
                        A python overwrite of a plugin SOP or canon file is NOT asked here: guard_build_mode hard-blocks it with the
                        shell-overwrite message (fc_python_canon_block, coordinator ruling 2026-11-02: same action, same verdict).
  fc_shell_delete_ask   (2026-11-02, delete parity) a shell rm / unlink / shred / trash, or mv of the file (a same-folder rename too), of an existing
                        canon file, plugin SOP or data file: the same fc_file_kind test python deletes use. Inside the plugin tree a file is
                        judged by its path relative to the code root (only SOP / canon / CLAUDE.md count there).
  fc_write_overwrite_ask (D-F12/F13) a Write-tool full overwrite of an EXISTING data file or database (same fc_file_kind test); the ask carries a
                        short diff. Edit (a change of some lines) never asks; an identical rewrite never asks.
These have NO off switch of the user's kind: placement.conf is never read here.
STREET SIGNS (2026-11-03, plan fix 23(d)): with a group's fc_sign_* switch on, the first attempt on a target in a session is refused with that
group's sign (lib/fc_sign.py) in place of the ask; every later attempt gets the ask. Edit of a person's SOP or a CLAUDE.md never carries a sign.
Fail posture: any internal error prints nothing (allow).
"""
import fnmatch, glob, json, os, re, shlex, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fc_sign
HOME = os.path.expanduser("~")
DB_EXT = (".db", ".sqlite", ".sqlite3", ".db3", ".duckdb", ".mdb", ".accdb", ".sdb")
THROWAWAY = {"node_modules", "__pycache__", ".venv", "venv", "env", "dist", "build", ".cache", ".pytest_cache", ".next", ".tox",
             ".mypy_cache", ".ruff_cache", "coverage", ".gradle", ".parcel-cache", ".turbo", ".nuxt", "scratchpad", "scratch", ".tmp", "tmp"}
SQL_TOOLS = {"sqlite3", "psql", "mysql", "mariadb", "dropdb", "duckdb", "sqlcipher", "mongosh", "mongo", "python", "python3", "node", "ruby"}
SQL_RX = re.compile(r"\bDROP\s+(TABLE|DATABASE|SCHEMA)\b|\bTRUNCATE\s+(TABLE\s+)?\w|\bDELETE\s+FROM\s+[\w\.\"`\[\]]+\s*(;|\"|'|\)|$)", re.I)
OUT = []
ADV = []
SIGNS = []
PAYLOAD = {}
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


def ask(msg, sign=None):
    OUT.append(msg)
    if sign:
        SIGNS.append(sign)


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
_PY_ASSIGN = re.compile(r"(?:^|;)\s*(?P<name>[A-Za-z_]\w*)\s*=\s*(?P<expr>[^\n;]+)", re.M)
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


# ---------------------------------------------------------------- 2026-11-02 (direct-hook exam route-arounds D-F01/F08/F09/F12/F13/F20)
# The same fine-china FILES that `rm` / a shell overwrite already ask about were reachable by switching tool: python os.remove /
# open(p,'w') in an executed -c or heredoc body (walk() above returns those bodies, via gws_guard's executed-heredoc reading), and a
# Write-tool full overwrite of a data file. One definition of a fine-china file, built only from the existing ones; no new kinds.
_PY_FILE_FN = re.compile(r"(?<![\w.])(?:(?P<mod>os|shutil|io|pathlib)\s*\.\s*)?(?P<fn>remove|unlink|rename|renames|replace|move|copy|copy2|copyfile|truncate|open)\s*\(")
_PY_METHOD = re.compile(r"(?P<expr>(?:\bpathlib\s*\.\s*)?\bPath\s*\((?:[^()]|\([^()]*\))*\)|(?<![\w.])[A-Za-z_]\w*)\s*\.\s*(?P<fn>unlink|rename|replace|write_text|write_bytes|open)\s*\(")
_PY_MODFN = {("os", "remove"): "del", ("os", "unlink"): "del", ("os", "rename"): "mv", ("os", "renames"): "mv", ("os", "replace"): "mv",
             ("shutil", "move"): "mv", ("shutil", "copy"): "cp", ("shutil", "copy2"): "cp", ("shutil", "copyfile"): "cp",
             ("os", "truncate"): "trunc", (None, "open"): "open", ("io", "open"): "open"}


def _py_args(code, open_paren):
    """-> ([positional exprs], {kw: expr}) of the call whose '(' is at code[open_paren]."""
    g = _gws()
    end = g._match_close(code, open_paren) if g else code.find(")", open_paren) + 1
    inner = code[open_paren + 1:max(end - 1, open_paren + 1)]
    pos, kw = [], {}
    for a in _split_top(inner, ","):
        km = re.match(r"\s*([A-Za-z_]\w*)\s*=(?!=)\s*(.*)$", a, re.S)
        if km:
            kw[km.group(1)] = km.group(2).strip()
        elif a.strip():
            pos.append(a.strip())
    return pos, kw


def py_file_ops(code, append=False):
    """-> [(path or None, op)] for every python call in `code` that deletes, moves away or rewrites a FILE.
    op: 'del' (os.remove/unlink, Path.unlink), 'away' (the SOURCE of os.rename/replace, shutil.move, Path.rename/replace),
    'over' (open(p,'w'), Path.write_text/write_bytes/open('w'), os.truncate, and the DESTINATION of a move/replace/copy).
    append=True also counts open modes 'a', 'x' and '+' as 'over' (fc_placement_conf_ask: an append is a write there)."""
    names, pathobj = {}, set()
    for m in _PY_ASSIGN.finditer(code):
        v = _py_value(m.group("expr"), names)
        if v is not None:
            names[m.group("name")] = v
            if re.match(r"\s*(?:pathlib\s*\.\s*)?Path\s*\(|.*\bPath\s*\.\s*home\s*\(", m.group("expr")):
                pathobj.add(m.group("name"))
    from_os = {x.strip() for grp in re.findall(r"\bfrom\s+os\s+import\s+([\w, ]+)", code) for x in grp.split(",")}
    found = []

    def mode_writes(pos, kw, i):
        md = kw.get("mode") or (pos[i] if len(pos) > i else "")
        sm = _PY_STR.match(md.strip()) if md else None
        return bool(sm) and bool(set("wax+" if append else "w") & set(sm.group(1) if sm.group(1) is not None else sm.group(2)))

    for m in _PY_FILE_FN.finditer(code):
        mod, fn = m.group("mod"), m.group("fn")
        if mod is None and fn in from_os and fn in ("remove", "unlink", "rename", "replace", "truncate"):
            mod = "os"
        if mod is None and fn != "open":
            continue
        kind = _PY_MODFN.get((mod, fn)) if mod != "pathlib" else None
        if not kind:
            continue
        pos, kw = _py_args(code, m.end() - 1)
        if not pos and kind != "open":
            continue
        val = lambda e: _py_value(e, names)
        if kind == "del":
            found.append((val(pos[0]), "del"))
        elif kind in ("mv", "cp"):
            if kind == "mv":
                found.append((val(pos[0]), "away"))
            if len(pos) > 1:
                found.append((val(pos[1]), "over-dst"))
        elif kind == "trunc":
            found.append((val(pos[0]), "over"))
        elif kind == "open" and pos and mode_writes(pos, kw, 1):
            found.append((val(pos[0]), "over"))
    for m in _PY_METHOD.finditer(code):
        ex, fn = m.group("expr"), m.group("fn")
        if ex in ("os", "shutil", "io", "pathlib", "sys", "self"):
            continue
        is_path = ex.lstrip().startswith(("Path", "pathlib")) or ex in pathobj
        if not is_path and not (ex in names and fn in ("unlink", "write_text", "write_bytes")):
            continue   # s.replace('a','b') on a str, f.open() on something unknown: not a path call
        p = _py_value(ex, names)
        pos, kw = _py_args(code, m.end() - 1)
        if fn == "unlink":
            found.append((p, "del"))
        elif fn in ("rename", "replace"):
            found.append((p, "away"))
            if pos:
                found.append((_py_value(pos[0], names), "over-dst"))
        elif fn in ("write_text", "write_bytes"):
            found.append((p, "over"))
        elif fn == "open" and mode_writes(pos, kw, 0):
            found.append((p, "over"))
    return found


FC_KIND_TEXT = {
    "db": ("a local database file", "once it is gone, what it held may not come back"),
    "sop": ("the person's own SOP", "it is their standing procedure"),
    "canon": ("a canon file", "it is the person's own settled rules"),
    "data": ("a data file (spreadsheet, csv, json, yaml...)", "the rows it holds do not come back"),
    "claudemd": ("a CLAUDE.md", "it is the person's standing instructions, loaded into every session"),
}


def fc_file_kind(t, code):
    """-> 'db' | 'sop' | 'canon' | 'data' | 'claudemd' | '' for an EXISTING file. Only the existing definitions: is_db (as rm asks),
    is_user_sop, build_mode.protected_doc (plugin SOP / canon), build_mode.data_file_target (as the shell-overwrite ask), CLAUDE.md.
    Throwaway never counts: temp folders, a throwaway/regenerable folder segment, ~/.claude/run|projects|cache, roundB/placement.conf
    (the conf guard owns those)."""
    if not os.path.isfile(t) or os.path.islink(t) or is_conf(t):
        return ""
    if code and under(t, code) and t != code:
        # The plugin's OWN tree (2026-11-02, delete parity): judged by its path INSIDE the code root, so a checkout or install that
        # happens to sit in a temp or cache folder (~/.claude/plugins/cache, a scratchpad worktree) still protects its SOPs and canon.
        # Only SOP / canon / CLAUDE.md count here: the plugin's json/jsonl files are code, governed by the harness guards.
        rel = t[len(code.rstrip("/")) + 1:].split("/")
        if any(p in THROWAWAY for p in rel[:-1]) or (len(rel) > 1 and rel[-2] in REGENERABLE):
            return ""
        if is_claudemd(t):
            return "claudemd"
        try:
            import build_mode
            return build_mode.protected_doc(t, code) or ""
        except Exception as e:
            sys.stderr.write("guard_fine_china_ask: protected-doc test skipped (%s)\n" % e)
            return ""
    if tmpish(t):
        return ""
    if any(p in THROWAWAY for p in t.split("/")[:-1]) or os.path.basename(os.path.dirname(t)) in REGENERABLE:
        return ""
    if any(under(t, os.path.join(HOME, ".claude", s)) for s in ("run", "projects", "cache", "shell-snapshots", "plugins/cache")):
        return ""
    if is_claudemd(t):
        return "claudemd"
    try:
        import build_mode
        pk = build_mode.protected_doc(t, code) if code else ""
    except Exception as e:
        sys.stderr.write("guard_fine_china_ask: protected-doc test skipped (%s)\n" % e)
        build_mode, pk = None, ""
    if pk:
        return pk
    if is_user_sop(t, code):
        return "sop"
    if is_db(t):
        return "db"
    try:
        if build_mode and build_mode.data_file_target(t):
            return "data"
    except Exception as e:
        sys.stderr.write("guard_fine_china_ask: data-file test skipped (%s)\n" % e)
    return ""


def py_file_msg(t, kind, op):
    what, why = FC_KIND_TEXT[kind]
    verb = {"del": "deletes", "away": "moves away", "over": "rewrites", "over-dst": "writes over"}[op]
    sw = "fc_python_delete_ask" if op in ("del", "away") else "fc_python_rewrite_ask"
    return ("ASK FIRST: this python command %s %s (%s). It is fine china: %s, and python does not use the Trash or keep a copy. "
            "WAY-THROUGH: press Yes only if the person asked for exactly this and a copy exists; otherwise stop and tell them which file and what you wanted to do. "
            "Do not switch to another tool to land the same change. RULE: switch %s in system/hooks/roundB.conf." % (verb, what, t, why, sw))


def py_overwrite_targets(cmd, cwd):
    """-> [existing file] that python code this command EXECUTES would overwrite (op 'over' / 'over-dst'), cd chains followed.
    Used by build_mode (fc_python_canon_block) to give an SOP/canon target the shell-overwrite hard block."""
    out = []
    for _w, scwd, py in walk(cmd, cwd):
        for body in py:
            for p, op in py_file_ops(body):
                if op not in ("over", "over-dst") or p is None or (scwd is None and not os.path.isabs(os.path.expanduser(p))):
                    continue
                t = resolve(p, scwd or "/")
                if os.path.isfile(t) and not os.path.islink(t):
                    out.append(t)
    return out


def blocked_elsewhere(t, op, code):
    """True when guard_build_mode hard-blocks this python overwrite (SOP/canon, fc_python_canon_block): no ask is added on top."""
    if op not in ("over", "over-dst") or not (on("fc_shell_overwrite") and on("fc_python_canon_block")) or not code:
        return False
    try:
        import build_mode
        return bool(build_mode.protected_doc(t, code))
    except Exception as e:
        sys.stderr.write("guard_fine_china_ask: protected-doc test skipped (%s)\n" % e)
        return False


def check_py_files(py_bodies, scwd, code):
    sw_del, sw_over = on("fc_python_delete_ask"), on("fc_python_rewrite_ask")
    if not (sw_del or sw_over):
        return
    for body in py_bodies:
        for p, op in py_file_ops(body):
            if p is None or (scwd is None and not os.path.isabs(os.path.expanduser(p))):
                continue   # an argument we cannot read is not judged (LIMIT; folder rmtree keeps its own over-ask)
            if not (sw_del if op in ("del", "away") else sw_over):
                continue
            t = resolve(p, scwd or "/")
            k = fc_file_kind(t, code)
            if k and not blocked_elsewhere(t, op, code):
                ask(py_file_msg(t, k, op), fc_sign.kind_sign(t, k, op in ("over", "over-dst")))


def write_overwrite_msg(t, kind, diff):
    what, why = FC_KIND_TEXT[kind]
    return ("ASK FIRST: this Write replaces the whole of %s that already exists (%s). It is fine china: %s. "
            "WAY-THROUGH: press Yes only if the person asked for this file to be replaced and a copy exists; otherwise change only the lines that need it "
            "with Edit, or write the new result to a NEW file and tell the person. Do not switch to another tool to land the same replacement. "
            "RULE: switch fc_write_overwrite_ask in system/hooks/roundB.conf.%s" % (what, t, why, (" DIFF: " + diff) if diff else ""))


def shell_fc_kind(t, code):
    """fc_shell_delete_ask (2026-11-02, coordinator ruling (a), delete parity with python): the kinds a shell rm/unlink/mv-away now asks
    about that it did not before: canon, a plugin SOP, a data file. (Databases and the person's SOPs already ask through their own pieces.)"""
    k = fc_file_kind(t, code)
    return k if k in ("canon", "sop", "data") and not is_user_sop(t, code) else ""


def shell_file_msg(t, kind, verb):
    what, why = FC_KIND_TEXT[kind]
    if kind == "sop":
        what, why = "an SOP of the plugin", "it is a standing procedure every session follows"
    return ("ASK FIRST: this command %s %s (%s). It is fine china: %s, and rm/unlink/mv do not use the Trash or keep a copy. "
            "WAY-THROUGH: press Yes only if the person asked for exactly this and a copy exists; otherwise stop and tell them which file and what you wanted to do. "
            "Do not switch to another tool to land the same change. RULE: switch fc_shell_delete_ask in system/hooks/roundB.conf." % (verb, what, t, why))


def claudemd_delete_verdict(t, how, code):
    """2026-11-02 (coordinator-approved, parity with the python delete): a shell rm / unlink / shred / trash, or mv of the file, of an
    EXISTING CLAUDE.md asks in the fc_claudemd_ask family (claudemd_verdict: the plugin-copy text where it applies). Throwaway and temp
    paths never ask (fc_file_kind); a CLAUDE.md that does not exist never asks."""
    if not is_claudemd(t) or fc_file_kind(t, code) != "claudemd":
        return None
    return claudemd_verdict(t, how, code)


def check_bash(cmd, cwd, code):
    sw_db, sw_dir, sw_sop, sw_conf = on("fc_db_delete_ask"), on("fc_folder_delete_ask"), on("fc_user_sop_ask"), on("fc_placement_conf_ask")
    sw_sdel = on("fc_shell_delete_ask")
    if sw_conf and CONF_RX.search(cmd):
        if conf_write_in_bash(cmd, cwd):
            ask("ASK FIRST: this command changes ~/.config/lifehack/placement.conf or the plugin's roundB.conf, the files that switch Lifehack's checks and guards off. "
                "Only the person decides that. WAY-THROUGH: press Yes only if the person asked for exactly this change; otherwise stop and tell them which line "
                "they can add themselves. RULE: switch fc_placement_conf_ask in system/hooks/roundB.conf.", ("conf", "conf", fc_sign.conf()))
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
                        ask(db_msg(t), fc_sign.kind_sign(t, "db", False))
                    elif sw_sop and is_user_sop(t, code) and os.path.isfile(t):
                        ask(sop_msg(t, "deletes"), fc_sign.kind_sign(t, "sop", False))
                    elif sw_sdel and v != "rmdir" and shell_fc_kind(t, code):
                        ask(shell_file_msg(t, shell_fc_kind(t, code), "deletes"), fc_sign.kind_sign(t, shell_fc_kind(t, code), False))
                    elif v != "rmdir" and claudemd_delete_verdict(t, "deletes", code):   # 2026-11-02: fc_claudemd_ask family, parity with python
                        ask(claudemd_delete_verdict(t, "deletes", code), claudemd_sign(t, code))
                    elif sw_dir and ((v == "rm" and recursive) or v == "rmdir") and not (os.path.islink(raw) and not a.endswith("/")) \
                            and folder_at_risk(t):
                        ask(dir_msg(t) + (" (via rmdir)" if v == "rmdir" else ""), ("folder", t, fc_sign.folder(t)))
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
                        ask(dir_msg(t) + " (via find -delete / -exec rm)", ("folder", t, fc_sign.folder(t)))
        elif v in ("mv",):
            src = [a for a in args if not a.startswith("-")][:-1]
            for s in src:
                for t in expand(s, scwd or cwd):
                    if sw_sop and is_user_sop(t, code) and os.path.isfile(t):
                        ask(sop_msg(t, "moves away"), fc_sign.kind_sign(t, "sop", False))
                    elif sw_sdel and shell_fc_kind(t, code):   # any mv of the file counts, a same-folder rename too (as the SOP mv and python os.rename do)
                        ask(shell_file_msg(t, shell_fc_kind(t, code), "moves away"), fc_sign.kind_sign(t, shell_fc_kind(t, code), False))
                    elif claudemd_delete_verdict(t, "moves away", code):
                        ask(claudemd_delete_verdict(t, "moves away", code), claudemd_sign(t, code))
        elif v in SQL_TOOLS and sw_db and SQL_RX.search(" ".join(w)):
            ask("ASK FIRST: this command drops or empties data in a local database (%s). A database is fine china: what it held may not come back. "
                "WAY-THROUGH: press Yes only if the person asked for exactly this and a copy exists; otherwise stop and tell them what you wanted to delete. "
                "RULE: switch fc_db_delete_ask in system/hooks/roundB.conf." % SQL_RX.search(" ".join(w)).group(0).strip(),
                ("db", "sql:" + SQL_RX.search(" ".join(w)).group(0).strip().lower(), fc_sign.db_sql(SQL_RX.search(" ".join(w)).group(0).strip())))
        if py_bodies:   # 2026-11-02: python file deletes / rewrites (fc_python_delete_ask, fc_python_rewrite_ask)
            check_py_files(py_bodies, scwd, code)
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
                        ask(dir_msg(t) + " (via python %s)" % kind, ("folder", t, fc_sign.folder(t)))
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
                    ask(sop_msg(t, "overwrites"), fc_sign.kind_sign(t, "sop", True))
                elif sw_db and is_db(t) and os.path.isfile(t) and not tmpish(t) and o["verb"] in (">", "truncate-inplace", "dd"):
                    ask(db_msg(t), fc_sign.kind_sign(t, "db", True))
    except Exception as e:
        sys.stderr.write("guard_fine_china_ask: parse skipped (%s)\n" % e)


_CONF_SHELL_WRITES = (">", "tee", "cp", "mv", "install", "ln", "rsync", "dd")   # build_mode.bash_ops verbs that land ON a target
_CONF_NAME = re.compile(r"(^|/)(placement|roundB)\.conf$")


def _conf_hit(arg, scwd):
    """An argument that names the conf. A cd we cannot follow (scwd None) or a $VAR we cannot expand: judged by the name (over-ask, never under-ask)."""
    if scwd is None and not os.path.isabs(os.path.expanduser(arg)):
        return bool(_CONF_NAME.search(arg))
    ts = expand(arg, scwd)
    if not ts and ("$" in arg or "`" in arg):
        return bool(_CONF_NAME.search(arg))
    return any(is_conf(t) for t in ts)


def conf_write_in_bash(cmd, cwd, depth=0):
    """True when the command can WRITE placement.conf / roundB.conf: a redirect (> >>) or tee onto it, cp/mv/install/ln/rsync/dd onto it,
    sed -i / perl -i / truncate / ed of it, rm/unlink or mv of it away, a python open(...,'w'|'a'|'x'|'+') / write_text / os.replace onto it
    in an executed -c, heredoc or stdin body, a heredoc whose target is the conf. Reads never ask (2026-11-02 real-use false alarm: a
    `cat roundB.conf || find . -name roundB.conf` asked because the old test matched the NAME next to a verb list).
    Shared parsers only: walk() (cd chains, heredoc bodies cut, executed bodies read), build_mode.bash_ops (redirect/tee/cp/mv/ln targets,
    cd chains followed), build_mode.inplace_targets (sed -i / truncate), py_file_ops (python writes)."""
    import build_mode
    shell, bodies = _heredoc_split(cmd)
    # 1. redirects, tee, cp/mv/install/ln/rsync/dd ONTO it. Heredoc bodies are already cut, so the << operator goes too
    #    (bash_ops would otherwise read everything after it as heredoc text and drop the commands that follow).
    for o in build_mode.bash_ops(re.sub(r"(?<!<)<<-?\s*(['\"]?)\w+\1", " ", shell), cwd):
        if o.get("verb") in _CONF_SHELL_WRITES and is_conf(o.get("target", "")):
            return True
    # 2. per command, in the cwd its own cd chain left it in (walk also reads bash -c / eval / executed heredoc bodies)
    for w, scwd, py in walk(cmd, cwd):
        v, a = os.path.basename(w[0]), w[1:]
        files = []
        if v in ("sed", "truncate"):
            files = build_mode.inplace_targets(v, a)
        elif v == "perl" and any(re.fullmatch(r"-[A-Za-z]*i\S*", x) for x in a):
            skip, script = False, False
            for x in a:
                if skip:
                    skip = False; continue
                if x in ("-e", "-E"):
                    skip = script = True; continue
                if x.startswith("-") and len(x) > 1:
                    if re.fullmatch(r"-[A-Za-z]*[eE]", x):
                        skip = script = True
                    continue
                files.append(x)
            if not script:
                files = files[1:]
        elif v in ("rm", "unlink", "shred", "trash", "ed", "ex"):
            files = [x for x in a if not x.startswith("-")]
        elif v == "mv":
            files = [x for x in a if not x.startswith("-")][:-1]   # moved AWAY (onto it is step 1)
        elif v == "dd":
            files = [x[3:] for x in a if x.startswith("of=")]
        elif v == "tee":
            files = [x for x in a if not x.startswith("-")]
        if any(_conf_hit(f, scwd) for f in files):
            return True
        for body in py:
            for p, op in py_file_ops(body, append=True):
                if p is None:
                    if CONF_RX.search(body):
                        return True   # a write whose path we cannot read, in code that names the conf: ask (never under-ask)
                    continue
                if _conf_hit(p, scwd):
                    return True
    # 3. redirects inside a bash -c / eval body: walk() reads the body's words but drops its redirects, so the body is judged
    #    again whole. walk(..., 3) returns the bash -c / eval command itself (its depth limit) with the cwd in force there.
    if depth < 3:
        for w, scwd, _py in walk(cmd, cwd, 3):
            v = os.path.basename(w[0])
            if v in _HD_SINK_SH:
                for k in range(1, len(w) - 1):
                    if re.fullmatch(r"-[A-Za-z]*c[A-Za-z]*", w[k]) and conf_write_in_bash(w[k + 1], scwd or cwd, depth + 1):
                        return True
            elif v == "eval" and conf_write_in_bash(" ".join(w[1:]), scwd or cwd, depth + 1):
                return True
    # 4. redirects inside a heredoc body that a shell executes
    for pos, text, fam in bodies:
        if fam == "sh" and depth < 3 and conf_write_in_bash(text, _final_cwd(shell[:pos], cwd) or cwd, depth + 1):
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


def claudemd_sign(t, code):
    plugin_copy = under(t, plugins_dir()) or bool(code and under(t, code) and not maintainer_self_repo(code))
    if plugin_copy and on("fc_claudemd_plugin_copy"):
        return ("claudemd", t, fc_sign.claudemd_plugin(t))
    return ("claudemd", t, fc_sign.claudemd(t))


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
                ask(m, claudemd_sign(o.get("target", ""), code))
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
    PAYLOAD.update(d)
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
                "RULE: switch fc_placement_conf_ask in system/hooks/roundB.conf.", ("conf", "conf", fc_sign.conf()))
        elif on("fc_user_sop_ask") and is_user_sop(t, code) and os.path.isfile(t):
            ask(sop_msg(t, "replaces" if tool == "Write" else "edits"), fc_sign.kind_sign(t, "sop", True) if tool == "Write" else None)   # ruling (c): Edit is upkeep
        elif tool == "Write" and on("fc_write_overwrite_ask"):   # 2026-11-02 (D-F12/F13): a Write over an existing data file / database
            k = fc_file_kind(t, code)
            if k in ("data", "db"):
                try:
                    same = open(t, encoding="utf-8", errors="replace").read() == (ti.get("content") or "")
                except OSError:
                    same = False
                if not same:
                    ask(write_overwrite_msg(t, k, short_diff(t, tool, ti)), fc_sign.kind_sign(t, k, True))
        if is_claudemd(t):
            m = claudemd_verdict(t, "replaces" if tool == "Write" else "edits", code, short_diff(t, tool, ti) if on("fc_claudemd_ask") else "")
            if m:
                ask(m, claudemd_sign(t, code) if tool == "Write" else None)   # ruling (c): Edit is upkeep
            length_advisory(t, tool, ti)
    elif tool == "Bash":
        check_bash(ti.get("command", ""), cwd, code)
        claudemd_bash(ti.get("command", ""), cwd, code)


def sign_masked():
    """A write into the plugin's hooks folder (roundB.conf) that a sibling hook will certainly deny: only one exit-2 message reaches the model, so do not spend the sign."""
    try:
        import build_mode
        code = build_mode.code_root()
        ti = PAYLOAD.get("tool_input") or {}
        ws = [{"target": s[1]} for s in SIGNS if s and s[0] != "conf"]
        if code and any(s and s[0] == "conf" for s in SIGNS) and "roundB.conf" in (ti.get("file_path") or ti.get("command") or ""):
            ws.append({"target": os.path.join(code, "system", "hooks", "roundB.conf")})
        return bool(code) and build_mode.sibling_certain_deny(PAYLOAD.get("tool_name", ""), ws, code, PAYLOAD.get("session_id") or "")
    except Exception:
        return False


def main():
    try:
        main_inner()
    except BaseException as e:
        sys.stderr.write("guard_fine_china_ask: internal error (%s: %s); allowing\n" % (type(e).__name__, e))
        return 0
    try:
        sign = fc_sign.first(SIGNS, PAYLOAD, masked=sign_masked()) if SIGNS else None
    except Exception as e:
        sys.stderr.write("guard_fine_china_ask: sign skipped (%s)\n" % e)
        sign = None
    if sign:
        sys.stderr.write(sign + "\n")
        return 2
    if OUT or ADV:
        h = {"hookEventName": "PreToolUse"}
        if OUT:
            h.update(permissionDecision="ask", permissionDecisionReason=" | ".join(dict.fromkeys(OUT))[:1800])
        if ADV:
            h["additionalContext"] = " ".join(dict.fromkeys(ADV))[:1500]
        s = json.dumps({"hookSpecificOutput": h})
        print(s)
        try:  # fire journal: record the real decision (ask), after the print; can never change it (lib/journal_note.py)
            import journal_note
            journal_note.note(s)
        except Exception:  # allow-silence: fire-journal observer only, a failed note must never change the hook
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())

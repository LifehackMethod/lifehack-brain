#!/usr/bin/env python3
"""Engine for guard_fine_china_ask.sh (Round D rulings A.1 and A.6). Payload on stdin. ASKS only (permissionDecision "ask",
exit 0); never blocks. Each piece has its own switch in roundB.conf (all OFF = prints nothing):
  fc_db_delete_ask      deleting a local database file (.db .sqlite .sqlite3 .db3 .duckdb .mdb .accdb), or an obvious
                        DROP TABLE/DATABASE, TRUNCATE, or DELETE FROM <t> with no WHERE through sqlite3/psql/mysql/dropdb/duckdb.
  fc_folder_delete_ask  rm -r / rm -rf (and python rmtree, find -delete) of a whole folder. Throwaway folders never ask:
                        node_modules __pycache__ .venv venv dist build .cache .pytest_cache .next .tox .mypy_cache coverage,
                        anything under /tmp, /var/folders, $TMPDIR, a scratchpad/scratch folder, ~/.claude/run|projects|cache,
                        a git-IGNORED folder, an empty folder, or a folder that does not exist.
  fc_user_sop_ask       write over / edit / delete / move away an EXISTING SOP of the person (a .md in a sops/ folder or named *sop*.md)
                        outside the plugin tree (the plugin's own SOPs are covered by the harness-write and shell-overwrite guards).
                        New files and appends (>>) pass.
  fc_placement_conf_ask ANY AI write (Write/Edit/redirect/tee/cp/sed -i/append, even a new file) to ~/.config/lifehack/placement.conf,
                        the user's own override file. Only a person's Yes changes it.
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
    return t == os.path.realpath(os.path.join(HOME, ".config", "lifehack", "placement.conf")) or t.endswith("/.config/lifehack/placement.conf")


def gitignored(d):
    import subprocess
    try:
        return subprocess.run(["git", "-C", os.path.dirname(d) or "/", "check-ignore", "-q", d], capture_output=True, timeout=5).returncode == 0
    except Exception:
        return False


def throwaway_dir(d):
    parts = d.split("/")
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


def check_bash(cmd, cwd, code):
    sw_db, sw_dir, sw_sop, sw_conf = on("fc_db_delete_ask"), on("fc_folder_delete_ask"), on("fc_user_sop_ask"), on("fc_placement_conf_ask")
    if sw_conf and "placement.conf" in cmd:
        if conf_write_in_bash(cmd, cwd):
            ask("ASK FIRST: this command changes ~/.config/lifehack/placement.conf, the person's own override file (it switches Lifehack's where-to-save checks off). "
                "Only the person decides that. WAY-THROUGH: press Yes only if the person asked for exactly this change; otherwise stop and tell them which line "
                "they can add themselves. RULE: switch fc_placement_conf_ask in system/hooks/roundB.conf.")
    segs = split_segments(cmd)
    for w in segs:
        v = os.path.basename(w[0])
        args = [a for a in w[1:]]
        if v in ("rm", "unlink", "shred", "trash", "rmdir"):
            flags = "".join(a for a in args if a.startswith("-") and not a.startswith("--"))
            recursive = bool(re.search(r"[rR]", flags)) or "--recursive" in args
            for a in [x for x in args if not x.startswith("-")]:
                for t in expand(a, cwd):
                    if not os.path.exists(t) and not os.path.islink(t):
                        continue
                    if sw_db and is_db(t) and os.path.isfile(t) and not tmpish(t) and not any(p in THROWAWAY for p in t.split("/")):
                        ask(db_msg(t))
                    elif sw_sop and is_user_sop(t, code) and os.path.isfile(t):
                        ask(sop_msg(t, "deletes"))
                    elif sw_dir and v == "rm" and recursive and os.path.isdir(t) and not throwaway_dir(t):
                        ask(dir_msg(t))
        elif v == "find" and sw_dir and ("-delete" in args or ("-exec" in args and "rm" in args)):
            for a in args:
                if a.startswith("-") or a in ("(", "!"):
                    break
                for t in expand(a, cwd):
                    if os.path.isdir(t) and not throwaway_dir(t):
                        ask(dir_msg(t) + " (via find -delete)")
        elif v in ("mv",) and sw_sop:
            src = [a for a in args if not a.startswith("-")][:-1]
            for s in src:
                for t in expand(s, cwd):
                    if is_user_sop(t, code) and os.path.isfile(t):
                        ask(sop_msg(t, "moves away"))
        elif v in SQL_TOOLS and sw_db and SQL_RX.search(" ".join(w)):
            ask("ASK FIRST: this command drops or empties data in a local database (%s). A database is fine china: what it held may not come back. "
                "WAY-THROUGH: press Yes only if the person asked for exactly this and a copy exists; otherwise stop and tell them what you wanted to delete. "
                "RULE: switch fc_db_delete_ask in system/hooks/roundB.conf." % SQL_RX.search(" ".join(w)).group(0).strip())
        elif v.startswith("python") and sw_dir and re.search(r"rmtree\(", " ".join(w)):
            ask("ASK FIRST: this python command deletes a whole folder tree (rmtree). Folders are fine china: it does not go to the Trash. "
                "WAY-THROUGH: press Yes only if the person asked for it; otherwise name the folder to them first. RULE: switch fc_folder_delete_ask.")
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
    if re.search(r">>?\s*['\"]?[^\s|;&]*placement\.conf", cmd) or re.search(r"\btee\b[^|;&]*placement\.conf", cmd):
        return True
    for w in split_segments(cmd):
        v = os.path.basename(w[0])
        if not any("placement.conf" in a for a in w[1:]):
            continue
        if v in ("cat", "grep", "egrep", "head", "tail", "less", "more", "ls", "wc", "stat", "diff", "file", "awk", "sort", "bat", "cut", "nl", "md5", "shasum", "test", "["):
            continue
        if v in ("rm", "mv", "cp", "install", "ln", "truncate", "dd", "tee", "rsync", "sed", "perl", "python", "python3", "ruby", "node", "bash", "sh", "zsh", "printf", "echo", "touch", "ed", "ex", "vi", "vim", "nano", "chmod"):
            if v == "sed" and not any(re.fullmatch(r"-[A-Za-z]*i\S*", a) for a in w[1:]):
                continue
            return True
    return False


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
            ask("ASK FIRST: this writes ~/.config/lifehack/placement.conf, the person's own override file (it switches Lifehack's where-to-save checks off). "
                "Only the person decides that. WAY-THROUGH: press Yes only if the person asked for exactly this change; otherwise tell them which line they can add themselves. "
                "RULE: switch fc_placement_conf_ask in system/hooks/roundB.conf.")
        elif on("fc_user_sop_ask") and is_user_sop(t, code) and os.path.isfile(t):
            ask(sop_msg(t, "replaces" if tool == "Write" else "edits"))
    elif tool == "Bash":
        check_bash(ti.get("command", ""), cwd, code)


def main():
    try:
        main_inner()
    except BaseException as e:
        sys.stderr.write("guard_fine_china_ask: internal error (%s: %s); allowing\n" % (type(e).__name__, e))
        return 0
    if OUT:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask", "permissionDecisionReason": " | ".join(dict.fromkeys(OUT))[:1800]}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

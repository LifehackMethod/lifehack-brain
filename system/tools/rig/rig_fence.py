#!/usr/bin/env python3
# not-wired-yet: a TEST-RIG-ONLY PreToolUse hook, passed to rig live sessions by rig_live_free.py via the --settings file it builds; never part of the product hooks
"""rig_fence.py - TEST-RIG FENCE (2026-10-31, after the Round D exam leaked a file into the real ~/.claude/skills).

WHY: the live exam gives the child a throwaway HOME, but a model that types an absolute real path (/Users/<you>/.claude/...) writes the real place.
WHAT: denies Write/Edit/MultiEdit/NotebookEdit, and a Bash command that writes/deletes/moves/creates, when the target is under the REAL home or the
      REAL notes root and NOT under a throwaway dir the rig allows. Everything else (reads, /tmp, throwaway dirs, other tools) passes. Reads of real
      places are allowed but logged (RIG_FENCE_LOG) so the scorer can list them. The deny text starts "TEST-RIG FENCE" so it is never mistaken for a product guard.
ENV (set by the rig for the child): RIG_FENCE_REAL_HOME, RIG_FENCE_REAL_NOTES, RIG_FENCE_ALLOW (':'-separated throwaway dirs), RIG_FENCE_LOG (optional),
      RIG_FENCE_RUN_DRIVE (optional, 2026-11-01): ONE run folder in the dedicated Drive test area (".../My Drive/Lifehack test area/<run-id>"). Honoured ONLY when it is a direct child of a
      folder named exactly "Lifehack test area" and is not "_archive"; anything else is ignored (fail closed). Every other Drive path stays fenced (it is under the real home).
      Path matching ignores letter case and unicode form (Drive for Desktop on a Mac is case-insensitive, so My Drive/_notes IS _Notes).
      RIG_FENCE_DENY (2026-11-02): ':'-separated HARD-deny roots (the real ~/Library/CloudStorage and every real notes root, from rig_isolation.fence_env).
      They beat RIG_FENCE_ALLOW; only the one RIG_FENCE_RUN_DRIVE folder is honoured inside them. <real home>/Library/CloudStorage is always added.
      WHY: the 2026-10-30 meal-part2 sessions wrote into a real Drive desk because that launcher (rig_meal.live_case) ran with no fence at all, and
      an allow-listed throwaway dir under a Drive mount would have opened the same hole here.
COMMANDS (2026-11-02, after a sandbox actor trashed 899 real Drive files with gws): a Bash command that runs a cloud/GitHub CLI (FORBIDDEN_BINS) is
      denied wherever it hides: plain, by full path, after env/sudo/xargs/timeout, inside bash -c / eval, in a here-doc line, as a quoted argv element
      of a python/node subprocess call, `open -a Terminal ...`, plus keychain/credential reads (security find-*-password, git credential fill).
      A Write/Edit of a SCRIPT whose text runs one is denied too (write-then-run). The command checks hold even without RIG_FENCE_REAL_HOME:
      the fence is only ever installed by the rig. A string match can be dodged; the real controls are rig_isolation's env allowlist + private PATH.
FAIL CLOSED (2026-11-02): an internal error now DENIES (it used to allow).
Exit 2 + stderr message = deny (same shape as the product guards); exit 0 = allow.
"""
import json, os, re, shlex, sys, unicodedata

DRIVE_AREA = "Lifehack test area"
DENY_BIN = ("gws", "gcloud", "gsutil", "gh", "aws", "az", "rclone", "gdrive")   # keep in step with rig_isolation.FORBIDDEN_BINS
_BINS = "|".join(DENY_BIN)
# a quoted string that IS a forbidden binary (or a path to one), optionally followed by its arguments: 'gws'  "gws drive files list"  '/opt/x/bin/gh'
QUOTED_BIN = re.compile(r"""(['"])(?:[^'"\s]*/)?(%s)(?:\s[^'"]*)?\1""" % _BINS)
# any path that ends in a forbidden binary: /opt/homebrew/bin/gws, ./gh, ~/sdk/bin/gcloud
PATH_BIN = re.compile(r"""(?:^|[\s'"=:(`;|&])(?:[^\s'"`;|&()]*/)(%s)(?=$|[\s'"`;|&)\]])""" % _BINS)
# commands that run their arguments as another command: a forbidden name as ANY of their words is a run of it
RUNNERS = {"xargs", "find", "env", "exec", "command", "nohup", "time", "timeout", "gtimeout", "nice", "sudo", "watch", "eval", "parallel", "open",
           "osascript", "which", "type", "whereis", "sh", "bash", "zsh", "dash", "ksh", "fish", "script", "caffeinate", "launchctl", "at", "batch",
           "stdbuf", "unbuffer", "doas", "arch", "su", "chroot", "screen", "tmux", "nq", "entr"}
PREFIX = {"sudo", "command", "exec", "time", "nohup", "env", "nice", "caffeinate", "stdbuf", "unbuffer", "arch", "doas", "builtin", "noglob", "!", "{", "("}
TERMINAL_APPS = re.compile(r"^(terminal|iterm2?|script editor|automator|warp|kitty|alacritty|ghostty|wezterm|hyper|shortcuts)(\.app)?$", re.I)
SCRIPTISH = re.compile(r"\.(command|tool|sh|bash|zsh|scpt|applescript|workflow|app|py)$", re.I)
KEYCHAIN = {"find-generic-password", "find-internet-password", "dump-keychain", "export", "unlock-keychain", "find-certificate", "show-keychain-info"}
SCRIPT_EXT = re.compile(r"(\.(sh|bash|zsh|command|tool|py|js|mjs|cjs|ts|rb|pl|php|applescript|scpt)|(^|/)[^./]+)$", re.I)

WRITE_ALL = {"rm", "rmdir", "unlink", "touch", "mkdir", "chmod", "chown", "truncate", "trash", "shred", "ln", "mv", "tee", "mkfifo"}
WRITE_LAST = {"cp", "rsync", "install", "scp", "ditto"}
GIT_WRITE = {"commit", "push", "add", "rm", "mv", "reset", "clean", "checkout", "switch", "restore", "init", "apply", "stash", "config", "merge", "rebase", "cherry-pick",
             "tag", "branch", "pull", "fetch", "clone", "worktree", "am", "revert", "remote", "submodule"}
INTERP = {"python", "python3", "python3.9", "python3.10", "python3.11", "python3.12", "python3.13", "python3.14", "node", "ruby", "perl", "osascript", "php", "deno", "bun"}
PYWRITE = re.compile(r"""open\([^)]*['"][wax+]|\.write|write_text|write_bytes|shutil\.|os\.(remove|unlink|rename|replace|mkdir|makedirs|rmdir|system|symlink|link)|\.unlink|\.mkdir|\.rename|subprocess|sqlite3|rmtree|fs\.(write|append|unlink|rm|mkdir|rename)|File\.(write|open|delete)|\bunlink\b""")
SEG = re.compile(r"\|\||&&|;|\||\n")


def fold(s):
    return unicodedata.normalize("NFC", s).casefold()


def run_drive_ok(p):
    """True when `p` (already realpath'd) is exactly one run folder inside the dedicated test area: a direct child of a dir named DRIVE_AREA, not the archive."""
    parent, name = os.path.split(p.rstrip(os.sep))
    return bool(name) and fold(name) != "_archive" and not name.startswith(".") and fold(os.path.basename(parent)) == fold(DRIVE_AREA) and os.path.isdir(p)


def cfg():
    """-> (real_home, real_notes, allow, deny, run_drive) or None when RIG_FENCE_REAL_HOME is unset (write checks off; command checks stay on)."""
    rh = os.environ.get("RIG_FENCE_REAL_HOME")
    if not rh:
        return None
    rh = os.path.realpath(rh)
    allow = [os.path.realpath(p) for p in (os.environ.get("RIG_FENCE_ALLOW") or "").split(":") if p]
    rd = os.environ.get("RIG_FENCE_RUN_DRIVE")
    run = os.path.realpath(rd) if rd and run_drive_ok(os.path.realpath(rd)) else None
    if run:
        allow.append(run)
    deny = [os.path.realpath(p) for p in (os.environ.get("RIG_FENCE_DENY") or "").split(":") if p] + [os.path.join(rh, "Library", "CloudStorage")]
    return (rh, [os.path.realpath(p) for p in (os.environ.get("RIG_FENCE_REAL_NOTES") or "").split(":") if p], allow, deny, run)


def under(p, d):
    p, d = fold(p), fold(d)
    return p == d or p.startswith(d.rstrip(os.sep) + os.sep)


def blocked(path, cwd, c):
    """True when `path` is a REAL place the fence protects (under the real home or real notes root, and not under an allowed throwaway dir)."""
    rh, notes, allow, deny, run = c
    if not path or path.startswith("$") or "`" in path:
        return False                      # an unresolved shell variable: cannot judge; the rig's calibration covers the literal-path leak
    if path.startswith("~"):
        if re.match(r"~[A-Za-z0-9_.-]+(/|$)", path):
            path = os.path.join("/Users", path[1:])       # ~otheruser/..: a named home is a real one
        else:
            return False                  # plain ~ is the child's throwaway HOME
    if not os.path.isabs(path):
        path = os.path.join(cwd, path)
    p = os.path.realpath(os.path.normpath(path))
    if run and under(p, run):
        return False                      # the one Drive test-area run folder rig_drive made for this session
    if any(under(p, d) for d in deny):
        return True                       # hard deny (real Drive mounts, real notes roots): no allow-listed dir can open these
    if any(under(p, a) for a in allow):
        return False
    return under(p, rh) or any(under(p, n) for n in notes)


PYCALL = re.compile(r"""(?:\bopen\(\s*|\bPath\(\s*|\b(?:write_text|write_bytes|rmtree|remove|unlink|rename|replace|makedirs|mkdir|copy\w*|move|touch|chmod|symlink|link|system)\(\s*)['"]?((?:/Users/|~[A-Za-z])[^\s'"`,)]*)['"]?([^\n]{0,160})""")


def py_targets(text):
    """Real-looking paths handed to a write-ish call inside interpreter code. open() counts only when a write mode follows; Path() only when a write-ish method follows."""
    res = []
    for m in PYCALL.finditer(text):
        head = text[m.start():m.end()]
        if head.lstrip().startswith("open(") and not re.search(r"['\"][wax+]+b?['\"]", m.group(2)):
            continue
        if head.lstrip().startswith("Path(") and not re.search(r"\.(write_text|write_bytes|unlink|mkdir|rename|replace|touch|rmdir|symlink_to)\(", m.group(2)):
            continue
        res.append(m.group(1))
    return res


def bash_targets(cmd, cwd, depth=0):
    """-> (list of write-target strings, final cwd). Targets are as written; blocked() resolves them against the tracked cwd."""
    out = []
    if re.search(r"\b(python\S*|node|ruby|perl)\b", cmd) and ("<<" in cmd or re.search(r"\s-[a-zA-Z]*[ce]\s", cmd)):   # a here-doc / -c script is split across ; and lines below: judge its whole text once
        out += [(p, cwd) for p in py_targets(cmd)]
    for seg in SEG.split(cmd):
        seg = seg.strip()
        if not seg:
            continue
        try:
            t = shlex.split(seg, comments=True)
        except ValueError:
            t = seg.split()
        # redirections: > f, >> f, 2> f, >f
        for i, w in enumerate(t):
            m = re.match(r"^\d*>>?\|?(.*)$", w)
            if m and not w.startswith("&"):
                tgt = m.group(1) or (t[i + 1] if i + 1 < len(t) else "")
                if tgt and not tgt.startswith("&") and tgt != "/dev/null":
                    out.append((tgt, cwd))
        t = [w for w in t if not re.match(r"^\d*>", w)]
        while t and (re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", t[0]) or t[0] in ("sudo", "command", "exec", "time", "nohup", "env")):
            t = t[1:]
        if not t:
            continue
        cmdn = os.path.basename(t[0])
        args = t[1:]
        pos = [a for a in args if not a.startswith("-")]
        if cmdn == "cd" and pos:
            d = pos[0]
            if not d.startswith(("$", "~")):
                cwd = os.path.normpath(os.path.join(cwd, d)) if not os.path.isabs(d) else d
            elif d.startswith("~") and re.match(r"~[A-Za-z]", d):
                cwd = os.path.join("/Users", d[1:])
            continue
        if cmdn in ("bash", "sh", "zsh") and "-c" in args and depth < 3:
            i = args.index("-c")
            if i + 1 < len(args):
                o, cwd = bash_targets(args[i + 1], cwd, depth + 1)
                out += o
            continue
        if cmdn in WRITE_ALL:
            out += [(a, cwd) for a in pos]
        elif cmdn in WRITE_LAST:
            tdir = [args[i + 1] for i, a in enumerate(args) if a in ("-t", "--target-directory") and i + 1 < len(args)]
            out += [(a, cwd) for a in (tdir or pos[-1:])]
        elif cmdn in ("sed", "perl", "gsed") and any(a.startswith("-i") or a == "--in-place" for a in args):
            out += [(a, cwd) for a in pos]
        elif cmdn == "dd":
            out += [(a[3:], cwd) for a in args if a.startswith("of=")]
        elif cmdn == "tar" and any(re.match(r"^-?[a-zA-Z]*x", a) for a in args[:1]):
            out += [(args[i + 1], cwd) for i, a in enumerate(args) if a == "-C" and i + 1 < len(args)] or [(".", cwd)]
        elif cmdn == "unzip":
            out += [(args[i + 1], cwd) for i, a in enumerate(args) if a == "-d" and i + 1 < len(args)] or [(".", cwd)]
        elif cmdn in ("curl", "wget"):
            out += [(args[i + 1], cwd) for i, a in enumerate(args) if a in ("-o", "-O", "--output") and i + 1 < len(args)]
        elif cmdn == "git":
            gcwd, sub, i = cwd, None, 0
            while i < len(args):
                if args[i] == "-C" and i + 1 < len(args):
                    gcwd = os.path.normpath(os.path.join(gcwd, args[i + 1])); i += 2; continue
                if args[i].startswith("-"):
                    i += 1; continue
                sub = args[i]; break
            rest = [a for a in args[i + 1:] if not a.startswith("-")] if sub else []
            if sub in GIT_WRITE and (sub not in ("remote", "branch", "tag", "config", "worktree", "submodule", "stash") or rest or sub == "stash" and rest[:1] != ["list"]):
                out.append((gcwd, cwd))
        elif cmdn in INTERP or cmdn.startswith("python"):
            # a script we cannot read line by line: if it looks like it writes, every real-looking absolute path in the segment is a target
            out += [(p, cwd) for p in py_targets(seg)]
        elif cmdn in ("sqlite3",):
            out += [(a, cwd) for a in pos[:1]]
    return out, cwd


CMD_SEG = re.compile(r"\|\||&&|;|\||\n|\$\(|`|<\(|>\(")


def _strip_prefix(t):
    """Drop leading VAR=val words and wrappers (env -i, sudo -u x, timeout 5, nice -n 5 ...) so t[0] is the command that really runs."""
    while t:
        w = t[0]
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", w) or w in PREFIX:
            t = t[1:]
            while t and t[0].startswith("-"):           # wrapper options (env -i, sudo -E, nice -n 5)
                t = t[2:] if t[0] in ("-u", "-n", "-g", "-C", "-S", "-P") and len(t) > 1 else t[1:]
            continue
        if os.path.basename(w) in ("timeout", "gtimeout"):
            t = t[1:]
            while t and (t[0].startswith("-") or re.match(r"^\d+[smhd]?$", t[0])):
                t = t[1:]
            continue
        break
    return t


def bin_hit(cmd, depth=0):
    """-> a short description of the forbidden CLI / credential read this Bash command would run, or None."""
    m = QUOTED_BIN.search(cmd) or PATH_BIN.search(cmd)
    if m:
        return "%s (as %s)" % (m.group(m.lastindex), m.group(0).strip()[:80])
    for seg in CMD_SEG.split(cmd):
        seg = seg.strip().lstrip("({!").strip()
        if not seg:
            continue
        try:
            t = shlex.split(seg, comments=True)
        except ValueError:
            t = seg.replace("'", " ").replace('"', " ").split()
        t = _strip_prefix([w for w in t if not re.match(r"^\d*[<>]", w)])
        if not t:
            continue
        name = os.path.basename(t[0])
        if name in DENY_BIN:
            return name
        args = t[1:]
        if name in RUNNERS and any(os.path.basename(a) in DENY_BIN for a in args):
            return next(os.path.basename(a) for a in args if os.path.basename(a) in DENY_BIN) + " (run through " + name + ")"
        if name in ("bash", "sh", "zsh", "dash", "ksh") and depth < 3:
            for i, a in enumerate(args):
                if re.match(r"^-[a-zA-Z]*c[a-zA-Z]*$", a) and i + 1 < len(args):
                    h = bin_hit(args[i + 1], depth + 1)
                    if h:
                        return h
        if name == "eval" and depth < 3:
            h = bin_hit(" ".join(args), depth + 1)
            if h:
                return h
        if name == "open":
            apps = [args[i + 1] for i, a in enumerate(args) if a in ("-a", "-b") and i + 1 < len(args)]
            if any(TERMINAL_APPS.match(os.path.basename(x)) or "terminal" in x.lower() or "iterm" in x.lower() for x in apps) \
                    or any(SCRIPTISH.search(a) for a in args if not a.startswith("-")):
                return "open %s (runs a shell outside the session)" % " ".join(args)[:80]
        if name == "security" and args and args[0] in KEYCHAIN:
            return "security %s (keychain credential read)" % args[0]
        if name == "git" and ("credential" in args or any(a.startswith("credential-") for a in args)):
            return "git credential (credential read)"
        if name.startswith("git-credential"):
            return name + " (credential read)"
    return None


def script_runs_bin(path, text):
    """True when a Write/Edit puts a script on disk whose text runs a forbidden CLI (write it, then run it): a line whose command is one, or a quoted argv/command string."""
    if not text or not (SCRIPT_EXT.search(path or "") or text.lstrip().startswith("#!")):
        return False
    if QUOTED_BIN.search(text) or PATH_BIN.search(text):
        return True
    return any(bin_hit(ln) for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#"))


def cmd_deny_msg(what):
    return ("TEST-RIG FENCE (not a product guard): this session is a rig test running in a throwaway sandbox, and it may not run cloud, GitHub or "
            "credential tools (%s). These would reach the REAL accounts of the person running the test. Do the task without them, or say it needs them." % what)


def decide(inp, c):
    """-> (deny_message or None, [real reads noted]). c may be None (no RIG_FENCE_REAL_HOME): then only the command checks run."""
    tool, ti, cwd = inp.get("tool_name", ""), inp.get("tool_input") or {}, inp.get("cwd") or os.getcwd()
    notes = []
    if tool == "Bash":
        h = bin_hit(ti.get("command", "") or "")
        if h:
            return cmd_deny_msg(h), notes
    if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        body = ti.get("content") or ti.get("new_string") or ti.get("new_source") or " ".join((e or {}).get("new_string", "") for e in (ti.get("edits") or []))
        if script_runs_bin(ti.get("file_path") or ti.get("notebook_path") or "", body):
            return cmd_deny_msg("a script that calls one of them"), notes
    if c is None:
        return None, notes
    if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        p = ti.get("file_path") or ti.get("notebook_path") or ""
        if blocked(p, cwd, c):
            return ("TEST-RIG FENCE (not a product guard): this session is a rig test running in a throwaway sandbox; %s is a REAL file location outside the sandbox. "
                    "Write it inside your working folder or the throwaway personal code folder instead. A personal SKILL goes in the throwaway home's own skills folder: %s/.claude/skills/<name>/ "
                    "(your $HOME), not the real /Users path." % (p, os.path.expanduser("~"))), notes
    elif tool == "Bash":
        tg, _ = bash_targets(ti.get("command", ""), cwd)
        for tgt, wcwd in tg:
            if blocked(tgt, wcwd, c):
                return ("TEST-RIG FENCE (not a product guard): this session is a rig test running in a throwaway sandbox; this command would write, delete or move %s, "
                        "a REAL location outside the sandbox. Use paths inside your working folder or the throwaway personal code folder." % tgt), notes
        notes = [p for p in re.findall(r"/Users/[^\s'\"`;|&)<>,]+", ti.get("command", "")) if blocked(p, cwd, c)]
    elif tool in ("Read", "Glob", "Grep"):
        p = ti.get("file_path") or ti.get("path") or ""
        if p and blocked(p, cwd, c):
            notes = [p]
    return None, notes


def main():
    inp = {}
    try:
        c = cfg()
        inp = json.load(sys.stdin)
        msg, notes = decide(inp, c)
    except Exception as e:                # fail CLOSED (2026-11-02): a fence that cannot judge must not wave a call through
        msg, notes = "TEST-RIG FENCE (not a product guard): the rig fence could not check this call (%s), so it is denied. Try a simpler command." % type(e).__name__, []
    lg = os.environ.get("RIG_FENCE_LOG")
    if lg and (msg or notes):
        try:
            with open(lg, "a", encoding="utf-8") as f:
                f.write(json.dumps({"tool": inp.get("tool_name"), "deny": bool(msg), "read_or_ref": notes, "msg": msg}) + "\n")
        except OSError:
            pass
    if msg:
        sys.stderr.write(msg + "\n")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

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
      Without RIG_FENCE_REAL_HOME the fence does nothing (fail-open: it must never block a product test by accident).
Exit 2 + stderr message = deny (same shape as the product guards); exit 0 = allow.
"""
import json, os, re, shlex, sys, unicodedata

DRIVE_AREA = "Lifehack test area"

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
    rh = os.environ.get("RIG_FENCE_REAL_HOME")
    if not rh:
        return None
    allow = [os.path.realpath(p) for p in (os.environ.get("RIG_FENCE_ALLOW") or "").split(":") if p]
    rd = os.environ.get("RIG_FENCE_RUN_DRIVE")
    if rd and run_drive_ok(os.path.realpath(rd)):
        allow.append(os.path.realpath(rd))
    return (os.path.realpath(rh), [os.path.realpath(p) for p in (os.environ.get("RIG_FENCE_REAL_NOTES") or "").split(":") if p], allow)


def under(p, d):
    p, d = fold(p), fold(d)
    return p == d or p.startswith(d.rstrip(os.sep) + os.sep)


def blocked(path, cwd, c):
    """True when `path` is a REAL place the fence protects (under the real home or real notes root, and not under an allowed throwaway dir)."""
    rh, notes, allow = c
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


def decide(inp, c):
    """-> (deny_message or None, [real reads noted])"""
    tool, ti, cwd = inp.get("tool_name", ""), inp.get("tool_input") or {}, inp.get("cwd") or os.getcwd()
    notes = []
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
    c = cfg()
    if c is None:
        return 0
    try:
        inp = json.load(sys.stdin)
        msg, notes = decide(inp, c)
    except Exception:
        return 0                          # fail open: a fence bug must never change a product result
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

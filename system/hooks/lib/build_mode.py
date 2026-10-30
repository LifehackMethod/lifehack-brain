#!/usr/bin/env python3
"""Decision engine for guard_build_mode.sh (v2 plan 3.2 + 3.4). Reads the hook payload on stdin.

Exit 0 = allow.  Exit 2 = a DELIBERATE deny (message on stderr).  Any other outcome (crash, parse failure,
missing register or pointer) is turned into exit 0 + a stderr line by the main(): FAIL OPEN.
Two clauses:
  A  speed bump: first attempt per kind (skill/job/hook/desk) per session is denied once; the retry passes.
  B  copy block: a copy of a shared tool into a desk is refused. Distinctive shared name or a cp/mv/rsync
     from <code>/shared/ -> HARD (every time). Generic shared name -> deny once like A.
"""
import fnmatch, json, os, re, shlex, sys

GENERIC_FIXED = {"__init__.py", "utils.py", "util.py", "helpers.py", "config.py", "common.py", "constants.py",
                 "main.py", "base.py", "types.py", "setup.py", "common.sh", "lib.sh", "utils.sh"}
HOME = os.path.expanduser("~")
STATE = os.path.join(HOME, ".claude", "run", "build-mode")


def _open(path, mode="r"):
    return open(path, mode, encoding="utf-8", errors="replace")  # the one place a file is opened


def warn(msg):
    sys.stderr.write("guard_build_mode: " + msg + "\n")


def code_root():
    try:
        p = _open(os.path.join(HOME, ".config", "lifehack", "code-root")).read().strip()
        if p and os.path.isdir(p):
            return os.path.realpath(p)
    except OSError:
        pass
    p = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    return os.path.realpath(p) if p and os.path.isdir(p) else None


def notes_root(code):
    cache = os.path.join(STATE, "notes-root")
    try:
        c, n = _open(cache).read().rstrip("\n").split("\t", 1)
        if c == code and os.path.isdir(n):
            return os.path.realpath(n)
    except (OSError, ValueError):
        pass
    try:
        import subprocess
        out = subprocess.run([sys.executable, os.path.join(code, "shared", "brain_root.py"), "--quiet"],
                             capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        return None
    if out and os.path.isdir(out):
        try:
            os.makedirs(STATE, exist_ok=True)
            _open(cache, "w").write(code + "\t" + out + "\n")
        except OSError:
            pass
        return os.path.realpath(out)
    return None


def is_generic(base):
    stem = base.rsplit(".", 1)[0]
    # computed rule: a single-word stem (no _ or -) is a plain noun a desk could name its own file
    # (paths, registry, verdicts in today's register); compound names are tool identities.
    return base in GENERIC_FIXED or not re.search(r"[_-]", stem)


def shared_names(code):
    """{basename: '/shared/...' path} from register.jsonl, cached keyed on the register's mtime+size."""
    reg = os.path.join(code, "system", "register", "register.jsonl")
    st = os.stat(reg)
    key = "%s:%s:%s" % (code, int(st.st_mtime), st.st_size)
    cache = os.path.join(STATE, "shared-names.json")
    try:
        d = json.load(_open(cache))
        if d.get("key") == key:
            return d["names"]
    except (OSError, ValueError, KeyError):
        pass
    names = {}
    for line in open(reg, encoding="utf-8", errors="replace"):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        p = r.get("path", "")
        if r.get("type") == "tool" and "/shared/" in p:
            names.setdefault(p.rsplit("/", 1)[1], p)
    try:
        os.makedirs(STATE, exist_ok=True)
        json.dump({"key": key, "names": names}, _open(cache, "w"))
    except OSError:
        pass
    return names


def is_thin_wrapper(content):
    """True for a thin wrapper of a shared tool: '# wraps-shared:' in the first 10 lines, or 12 or fewer
    code lines that name a /shared/ path. content None (unknown) is never a wrapper unless marked."""
    head = content or ""
    sig = [l for l in head.splitlines() if l.strip() and not l.strip().startswith("#")]
    marker = any("wraps-shared:" in l for l in head.splitlines()[:10])
    return marker or (content is not None and len(sig) <= 12 and ("/shared/" in head))


def resolve(p, cwd):
    p = os.path.expanduser(p)
    if not os.path.isabs(p):
        p = os.path.join(cwd, p)
    return os.path.realpath(p)


def under(p, root):
    return p == root or p.startswith(root.rstrip("/") + "/")


# ---------------------------------------------------------------- Bash parsing (written-TO targets only)
WRITE_VERBS = {"mkdir", "touch", "cp", "mv", "install", "rsync", "ln", "tee"}


def inplace_targets(verb, a):
    """Files a `sed -i ...` / `truncate ...` call rewrites in place ([] when sed has no -i). Value flags are skipped."""
    files, skip, script_flag = [], False, False
    if verb == "sed" and not any(re.fullmatch(r"-[A-Za-z]*i\S*", w) or w == "--in-place" or w.startswith("--in-place=") for w in a if w.startswith("-")):
        return []
    for w in a:
        if skip:
            skip = False; continue
        if verb == "sed" and w in ("-e", "-f", "--expression", "--file"):
            skip = True; script_flag = True; continue
        if verb == "truncate" and w in ("-s", "-r", "--size", "--reference"):
            skip = True; continue
        if w.startswith("-") and len(w) > 1 or w == "":
            continue
        files.append(w)
    if verb == "sed" and not script_flag and files:
        files = files[1:]   # first plain argument is the script
    return files


def bash_ops(cmd, cwd, _depth=0):
    """-> list of dicts {verb, target, srcs, content}. Verbs only at segment start; a mention inside a
    quoted string is a single token and never a verb. Heredoc body (after <<) is kept as content."""
    heredoc = None
    m = re.search(r"<<-?\s*['\"]?(\w+)['\"]?[^\n]*\n(.*)", cmd, re.S)
    if m:
        heredoc = m.group(2)
        cmd = cmd[:m.start()] + cmd[m.start():].split("\n", 1)[0]
    lex = shlex.shlex(cmd, posix=True, punctuation_chars="();<>|&\n")
    lex.whitespace = " \t\r"
    lex.whitespace_split = True
    try:
        toks = list(lex)
    except ValueError:
        return []
    shell_ow = _roundb("fc_shell_overwrite")
    segs, cur = [], []
    for t in toks:
        if t and set(t) <= set(";&|\n()") :
            segs.append(cur); cur = []
        else:
            cur.append(t)
    segs.append(cur)
    ops = []
    for seg in segs:
        # redirects
        words, i, redir, appends = [], 0, [], []
        while i < len(seg):
            t = seg[i]
            if t in (">", ">>", ">|") and i + 1 < len(seg):
                redir.append(seg[i + 1]); appends.append(t == ">>"); i += 2; continue
            if re.fullmatch(r"\d*>>?", t) and i + 1 < len(seg):
                redir.append(seg[i + 1]); appends.append(t.endswith(">>")); i += 2; continue
            if t in ("<", "<<", "<<<", ">&") :
                i += 2; continue
            words.append(t); i += 1
        while words and (re.fullmatch(r"\w+=.*", words[0]) or words[0] in ("sudo", "command", "env")):
            words.pop(0)
        if shell_ow:   # Round C gap 5: read through exec/nohup/time, env options, and bash -c / sh -c / eval bodies
            while words and (re.fullmatch(r"\w+=.*", words[0]) or os.path.basename(words[0]) in ("sudo", "command", "env", "exec", "nohup", "time", "nice")
                             or (words[0].startswith("-") and len(words) > 1)):
                words.pop(0)
            body = None
            if words and os.path.basename(words[0]) in ("bash", "sh", "zsh", "dash", "ksh"):
                for k in range(1, len(words) - 1):
                    if not words[k].startswith("-"):
                        break
                    if re.fullmatch(r"-[A-Za-z]*c[A-Za-z]*", words[k]):
                        body = words[k + 1]
                        break
            elif words and words[0] == "eval":
                body = " ".join(words[1:])
            if body and _depth < 3:
                ops.extend(bash_ops(body, cwd, _depth + 1))
                body_done = True
            else:
                body_done = False
        else:
            body_done = False
        for r, ap in zip(redir, appends):
            if r.startswith("&") or r == "/dev/null":
                continue
            ops.append({"verb": ">", "target": resolve(r, cwd), "srcs": [], "content": heredoc, "append": ap})
        if not words or body_done:
            continue
        verb = os.path.basename(words[0])
        if shell_ow and verb == "dd":   # Round C gap 5: dd of=<file> overwrites it (oflag=append does not)
            ap = any(w.startswith("oflag=") and "append" in w for w in words[1:])
            for w in words[1:]:
                if w.startswith("of="):
                    ops.append({"verb": "dd", "target": resolve(w[3:], cwd), "srcs": [], "content": "", "append": ap})
            continue
        if verb == "git" and "worktree" in words[1:4] and "add" in words[1:5]:   # F6a: `git [-C d] worktree add [-b X] <path>`
            a, pos, k = words[words.index("add") + 1:], [], 0
            while k < len(a):
                if a[k] in ("-b", "-B", "--reason"): k += 2; continue
                if not a[k].startswith("-"): pos.append(a[k])
                k += 1
            base = resolve(words[words.index("-C") + 1], cwd) if "-C" in words[:3] and len(words) > 3 else cwd
            if pos:
                ops.append({"verb": "worktree", "target": resolve(pos[0], base), "srcs": [], "content": ""})
            continue
        if shell_ow and verb in ("sed", "truncate"):   # Round C 4 (fc_shell_overwrite): in-place edits are overwrites too
            for f in inplace_targets(verb, words[1:]):
                ops.append({"verb": verb + "-inplace", "target": resolve(f, cwd), "srcs": [], "content": ""})
            continue
        if verb not in WRITE_VERBS:
            continue
        args = [w for w in words[1:] if not (w.startswith("-") and len(w) > 1)]
        if verb in ("mkdir", "touch", "tee"):
            ap = verb == "tee" and any(w in ("-a", "--append") or (w.startswith("-") and not w.startswith("--") and "a" in w[1:]) for w in words[1:] if w.startswith("-"))
            for a in args:
                ops.append({"verb": verb, "target": resolve(a, cwd), "srcs": [], "content": heredoc if verb == "tee" else "", "append": ap})
        elif len(args) >= 2:
            dest = resolve(args[-1], cwd)
            srcs = [resolve(a, cwd) for a in args[:-1]]
            for s in srcs:
                t = os.path.join(dest, os.path.basename(s)) if os.path.isdir(dest) or args[-1].endswith("/") else dest
                content = None
                try:
                    if os.path.isfile(s) and os.path.getsize(s) < 400000:
                        content = _open(s).read()
                except OSError:
                    pass
                ops.append({"verb": verb, "target": t, "srcs": [s], "content": content, "bash_copy": True})
    return ops


def load_placement(code):
    """-> {name: (zone, [patterns], message)} from the shipped list plus the optional user-level file."""
    rules = {}
    for path in (os.path.join(code, "system", "hooks", "placement.conf"),
                 os.path.join(HOME, ".config", "lifehack", "placement.conf")):
        try:
            lines = _open(path).read().splitlines()
        except OSError:
            if "system" in path:
                warn("placement list %s unreadable; placement check skipped" % path)
            continue
        for ln in lines:
            if not ln.strip() or ln.startswith("#"):
                continue
            f = ln.split("\t")
            if len(f) == 2 and f[1].strip() == "off":
                rules.pop(f[0], None)
            elif len(f) >= 4:
                rules[f[0]] = (f[1], [x.strip() for x in f[2].split(",")], f[3])
    return rules

def outside_homes_target(t, code, notes):
    """Placement rule 4. -> the resolved personal code folder when file t sits outside EVERY home, else None.
    Homes: the harness repo, the notes folder, the personal code folder. Never fires (None) when: the switch
    is off; the personal code folder does not resolve (no path to name, so no bump); t is in a scratch dir
    (/tmp, /private/tmp, /var/folders, $TMPDIR) UNLESS it is under the user's home; or t is under ~/.claude,
    ~/.config or any /.claude/ folder (Claude's own scratchpads, worktrees, config)."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from roundb import roundb_on
        if not roundb_on("placement_outside_homes"):
            return None
    except Exception:
        return None
    finally:
        sys.path.pop(0)
    try:
        sys.path.insert(0, os.path.join(code, "shared"))
        import personal_code_root
        src, pc = personal_code_root.resolve_personal_code_root()
    except Exception:
        return None
    finally:
        sys.path.pop(0)
    if not pc or not os.path.isdir(pc):
        return None
    pc = os.path.realpath(pc)
    home = os.path.realpath(HOME)
    for h in (code, notes, pc):
        if h and under(t, h):
            return None
    if under(t, os.path.join(home, ".claude")) or under(t, os.path.join(home, ".config")) or "/.claude/" in t:
        return None
    if not under(t, home) and any(under(t, r) for r in ("/tmp", "/private/tmp", "/var/folders", "/private/var/folders",
                                                        os.path.realpath(os.environ.get("TMPDIR", "/tmp")))):
        return None
    return pc



# ---------------------------------------------------------------- shell overwrite of an SOP or canon (Round C 4, fc_shell_overwrite)
OVERWRITE_VERBS = {">", "dd", "tee", "cp", "mv", "install", "rsync", "sed-inplace", "truncate-inplace"}


def protected_doc(t, code):
    """-> 'sop' | 'canon' | '' for a target path. The SAME two sets the Write/Edit guards govern: an SOP is a file in a
    rulebook folder named by system/hooks/build_mode_sops.conf (guard_harness_write protects the whole harness tree, SOPs included);
    canon is a file under a canon/ folder or a top-level canon.md (guard_canon_write's own test). No second list is kept here."""
    dirs = {os.path.join(code, "system", "sops")}
    try:
        for ln in _open(os.path.join(code, "system", "hooks", "build_mode_sops.conf")).read().splitlines():
            f = ln.split("\t")
            if len(f) >= 2 and not ln.startswith("#") and f[1].strip():
                dirs.add(os.path.join(code, os.path.dirname(f[1].strip())))
    except OSError:
        pass
    if t.endswith(".md") and any(under(t, d) for d in dirs):
        return "sop"
    if "/canon/" in t or os.path.basename(t) == "canon.md":
        return "canon"
    return ""


def shell_overwrite_message(t, kind):
    return ("BLOCKED: this shell command overwrites %s (%s) in place. WHY: a redirect, tee, cp/mv, sed -i or truncate rewrites the whole "
            "file with no review, and the Edit tool's guards (and for canon its size and expiry checks) cannot see it. Appending (>> or tee -a) is fine. "
            "WAY THROUGH: make the change with the Edit tool, which the existing guard governs, or ask the person to make it. "
            "RULE: system/hooks/guard_build_mode.sh header (fc_shell_overwrite)." % (os.path.basename(t), "an SOP" if kind == "sop" else "a canon file"))


# ---------------------------------------------------------------- reason gate (Round C 1+2)
REASON_RX = re.compile(r"lifehack-place:[ \t]*([^\n]*)")
REASON_MARKER = "# lifehack-place: <your reason>"


def _roundb(name):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from roundb import roundb_on
        return roundb_on(name)
    except Exception:
        return False
    finally:
        sys.path.pop(0)


def stated_reason(blob):
    """-> (reason, blob_without_the_marker). The marker is `lifehack-place: <reason>` anywhere on a line: a
    comment in the file content (Write/Edit) or at the end of the shell command (Bash). Trailing quote/comment
    closers (`-->`, a quote) are stripped."""
    m = REASON_RX.search(blob or "")
    if not m:
        return "", blob or ""
    r = re.sub(r"\s*(?:-->|\*/)\s*$", "", m.group(1)).strip().strip("\"'`").strip()
    return r, (blob[:m.start()] + blob[m.end():])


def weak_reason_of(reason, code, code_root_dir):
    """Reuse system/tools/door_rules.weak_reason (imported, not copied). -> '' if real, why-junk string if not,
    None if the checker cannot be loaded (caller falls back to today's speed bump)."""
    tools = os.path.join(code_root_dir, "system", "tools")
    sys.path.insert(0, tools)
    try:
        import door_rules
        return door_rules.weak_reason(reason, code)
    except Exception as e:
        warn("door_rules.weak_reason unavailable (%s); reason gate skipped" % e)
        return None
    finally:
        sys.path.pop(0)


def personal_conf():
    return os.path.join(HOME, ".config", "lifehack", "placement.conf")


def kept_folders_of(code):
    """Folders the person already gave a reason for: lines `kept<TAB><folder>[<TAB>reason]` in
    ~/.config/lifehack/placement.conf, read through shared/tools/own_list_add.kept_folders (imported, not re-parsed)."""
    tools = os.path.join(code, "shared", "tools")
    sys.path.insert(0, tools)
    try:
        import own_list_add
        return own_list_add.kept_folders()
    except Exception as e:
        warn("kept_folders unavailable (%s); remembered folders ignored" % e)
        return []
    finally:
        sys.path.pop(0)


def remember_folder(code, folder, reason):
    """Append `kept<TAB><folder><TAB><date> reason: <text>` (one folder per line) to ~/.config/lifehack/placement.conf,
    the exact shape own_list_add.kept_folders() reads. Skips a folder that is already kept."""
    import datetime
    if os.path.realpath(folder) in kept_folders_of(code):
        return False
    path = personal_conf()
    try:
        have = _open(path).read()
    except OSError:
        have = ""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    line = "kept\t%s\t%s reason: %s\n" % (folder, datetime.date.today().isoformat(), reason.replace("\t", " ").replace("\n", " "))
    with _open(path, "a") as fh:
        if have and not have.endswith("\n"):
            fh.write("\n")
        fh.write(line)
    return True


def gate_message(t, pc, why_weak, remember, hint_tools):
    parts = []
    if why_weak:
        parts.append("BLOCKED: that reason was refused (%s)." % why_weak)
    else:
        parts.append("BLOCKED: new code in %s, which is outside all three homes (harness repo, notes folder, personal code folder)." % os.path.dirname(t))
    parts.append("WHERE IT BELONGS: your personal code folder, %s. Write the file there." % pc)
    parts.append("OR, if it has to live here, state a real reason (what this folder is for and why the file cannot go in the personal code folder) "
                 "and retry. EXACT SYNTAX: a line containing  lifehack-place: <your reason>  as a comment: in a .sh/.py file `# lifehack-place: <your reason>`; "
                 "in a SKILL.md/.md file `<!-- lifehack-place: <your reason> -->`; in a shell command put `# lifehack-place: <your reason>` at the end of the command. "
                 "Filler (\"needed\", \"todo\") or a restatement of the filename is refused. A retry with no reason is stopped again.")
    if remember:
        parts.append("A real reason is remembered for this folder in ~/.config/lifehack/placement.conf, so you are not asked again for it.")
    parts.append("RULE: system/hooks/placement.conf (code-outside-homes).")
    return " ".join(parts) + hint_tools

# ---------------------------------------------------------------- the decision
def sop_receipt_valid(sid):
    """Mirror of guard_hook_sop_read.sh's receipt test (same key order, 12h TTL), in-process, no fork.
    Key = payload session_id, else CLAUDE_CODE_SESSION_ID, else cwd-<sha1(PWD)[:12]>; also accepts the
    cwd-keyed receipt. Any doubt (cannot hash, cannot stat) returns True = 'do not assume a sibling deny'."""
    import hashlib, time
    run = os.path.join(HOME, ".claude", "run", "sop")
    try:
        h = hashlib.sha1((os.environ.get("PWD") or os.getcwd()).encode()).hexdigest()[:12]
        key = sid or os.environ.get("CLAUDE_CODE_SESSION_ID") or "cwd-" + h
        for cand in (os.path.join(run, "hook.%s.receipt" % key), os.path.join(run, "hook.cwd-%s.receipt" % h)):
            if os.path.isfile(cand) and time.time() - os.path.getmtime(cand) < 43200:
                return True
        return False
    except Exception:
        return True


def sibling_certain_deny(tool, writes, code, sid):
    """True when a PARALLEL PreToolUse hook will CERTAINLY deny this same call, so only its message reaches
    the model and ours would be masked. Narrow on purpose: exactly two known siblings, nothing else.
      (a) guard_hook_sop_read.sh: a write into <code>/system/hooks/ (not tests/) with no valid hook-SOP receipt.
      (b) guard_write_paths.sh: the Write/Edit/MultiEdit tool aimed at <code>/system/hooks/*.sh ('edit via Bash only')."""
    hooks = os.path.join(code, "system", "hooks")
    tests = os.path.join(hooks, "tests")
    for w in writes:
        t = w["target"]
        if not under(t, hooks) or under(t, tests):
            continue
        if tool in ("Write", "Edit", "MultiEdit") and t.endswith(".sh"):
            return True
        if not sop_receipt_valid(sid):
            return True
    return False


def main_inner():
    raw = sys.stdin.read()
    try:
        d = json.loads(raw)
        tool = d.get("tool_name", "")
        ti = d.get("tool_input") or {}
        cwd = d.get("cwd") or os.getcwd()
        sid = d.get("session_id") or os.environ.get("CLAUDE_CODE_SESSION_ID") or ""
    except Exception as e:
        warn("cannot parse payload (%s); allowing" % e)
        return 0
    code = code_root()
    if not code:
        warn("no code-root pointer (~/.config/lifehack/code-root) and no CLAUDE_PLUGIN_ROOT; allowing")
        return 0
    notes = notes_root(code)

    # collect writes: dicts target, verb, content, srcs, creating
    writes = []
    if tool in ("Write", "Edit", "MultiEdit"):
        fp = ti.get("file_path") or ""
        if not fp:
            return 0
        t = resolve(fp, cwd)
        if tool == "Write":
            text = ti.get("content", "")
        elif tool == "Edit":
            text = ti.get("new_string", "")
        else:
            text = "\n".join(e.get("new_string", "") for e in ti.get("edits", []) or [])
        old = ""
        if tool == "Edit":
            old = ti.get("old_string", "")
        elif tool == "MultiEdit":
            old = "\n".join(e.get("old_string", "") for e in ti.get("edits", []) or [])
        writes.append({"verb": tool, "target": t, "content": text, "old": old, "srcs": [],
                       "full": tool == "Write"})
    elif tool == "Bash":
        for o in bash_ops(ti.get("command", ""), cwd):
            o["old"] = ""; o["full"] = o["verb"] in (">", "tee", "cp", "mv", "install", "rsync")
            writes.append(o)
    else:
        return 0
    if not writes:
        return 0

    shared_dir = os.path.join(code, "shared")
    placement = None
    desks = os.path.join(notes, "desks") if notes else None
    names = None
    denies = []   # (kind, once_key, message)

    def tmpish(p):
        return any(under(p, r) for r in ("/tmp", "/private/tmp", "/var/folders", "/private/var/folders",
                                          os.path.realpath(os.environ.get("TMPDIR", "/tmp"))))

    for w in writes:
        t = w["target"]
        exists = os.path.exists(t)
        if tool == "Bash" and exists and w["verb"] in OVERWRITE_VERBS and not w.get("append") and _roundb("fc_shell_overwrite"):
            pk = protected_doc(t, code)
            if pk:
                denies.append(("gate-hard", None, shell_overwrite_message(t, pk)))
        base = os.path.basename(t)
        # ---- check 3: placement (new files only, never hard)
        if not exists and w["verb"] != "mkdir":
            if placement is None:
                try:
                    placement = load_placement(code)
                except Exception as e:
                    warn("placement list unusable (%s); skipped" % e)
                    placement = {}
            for rname, (zone, pats, pmsg) in placement.items():
                if not any(fnmatch.fnmatch(base, x) for x in pats):
                    continue
                if zone == "notes":
                    hit = bool(notes) and under(t, notes) and not under(t, code)
                    if hit:
                        if names is None:
                            try:
                                names = shared_names(code)
                            except Exception:
                                names = {}
                        hit = base not in names   # shared-tool names are check 2's business
                elif zone.startswith("code:"):
                    rel = os.path.relpath(t, code) if under(t, code) else ""
                    hit = bool(rel) and rel.split(os.sep)[0] in zone[5:].split(",")
                elif zone.startswith("worktree:"):   # a `git worktree add` path must sit under one of these homes
                    hit = w["verb"] == "worktree" and not any(under(t, os.path.realpath(os.path.expanduser(r))) or "/.claude/worktrees/" in t
                                                              for r in zone[9:].split(","))
                elif zone == "outside-homes":   # 4th rule: new code outside every home (switch placement_outside_homes)
                    hit = False
                    pc = outside_homes_target(t, code, notes)
                    if pc:
                        hit = True
                        pmsg = pmsg.replace("{path}", pc)
                else:
                    hit = False
                if hit and zone == "outside-homes":
                    if any(under(t, f) for f in kept_folders_of(code)):
                        hit = False   # the person already gave a reason for this folder (remember_reason)
                    elif _roundb("reason_gate"):
                        blob = ti.get("command", "") if tool == "Bash" else w["content"]
                        reason, rest = stated_reason(blob)
                        why = weak_reason_of(reason, "%s %s" % (t, rest), code) if reason else ""
                        if reason and why == "":
                            hit = False   # a stated, real reason: this one passes
                            if _roundb("remember_reason"):
                                try:
                                    remember_folder(code, os.path.dirname(t), reason)
                                except Exception as e:
                                    warn("could not remember the reason (%s)" % e)
                        elif why is not None:   # no reason, or a junk one: stop EVERY time, never once-per-session
                            ht = ""
                            if _roundb("placement_toolbox_hint"):
                                try:
                                    ht = tool_hint(code, "%s %s" % (t, (w["content"] or "")[:1500]))
                                    ht = ("\nShared tools that may already do this:" + ht) if ht else ""
                                except Exception:
                                    ht = ""
                            denies.append(("gate-hard", None, gate_message(t, pc, why if reason else "", _roundb("remember_reason"), ht)))
                            hit = False
                if hit:
                    ht = ""
                    if _roundb("placement_toolbox_hint"):   # Round C silent-miss cause D: show the shared tool to reuse
                        try:
                            ht = tool_hint(code, "%s %s" % (t, (w["content"] or "")[:1500]))
                            ht = ("\nShared tools that may already do this:" + ht) if ht else ""
                        except Exception:
                            ht = ""
                    denies.append(("placement", "place-" + rname,
                                   "Wrong home? %s Retry the same call and it goes through; this stop happens once per session per rule. "
                                   "RULE: system/hooks/placement.conf (%s).%s" % (pmsg, rname, ht)))
        # ---- clause B1: cp/mv/rsync whose SOURCE is under <code>/shared/ -> HARD
        for s in w["srcs"]:
            if w["verb"] in ("cp", "mv", "rsync") and under(s, shared_dir) and not under(t, code):
                if (notes and under(t, notes)) or not tmpish(t):
                    rel = os.path.relpath(s, code)
                    denies.append(("copy-hard", None,
                        "BLOCKED: %s is shared code (%s); it must not be copied out of shared/. "
                        "WHY: 68 desk copies drifted from their originals and each desk then trusted its own stale copy (v2 plan 3.4). "
                        "REDIRECT: call it in place: python3 \"$(cat ~/.config/lifehack/code-root)/%s\" ... (or write a thin wrapper of 12 lines or fewer that names that path, with '# wraps-shared: %s' in its first lines). "
                        "To change the tool, change it in %s. RULE: system/hooks/guard_build_mode.sh header; system/register/toolbox.md lists what is shared."
                        % (os.path.basename(s), rel, rel, rel, shared_dir)))
        # ---- clause B2: write into a desk of a file named like a shared tool
        if desks and under(t, desks) and t != desks and not exists:
            if names is None:
                try:
                    names = shared_names(code)
                except Exception as e:
                    warn("cannot read the register (%s); copy clause skipped" % e)
                    names = {}
            if base in names:
                head = (w["content"] or "")
                wrapper = is_thin_wrapper(w["content"])
                if not wrapper:
                    sp = names[base]
                    msg = ("%s is a shared tool (register: %s); it must not be copied into a desk. "
                           "WHY: 68 desk copies drifted from their originals and each desk then trusted its own stale copy (v2 plan 3.4). "
                           "REDIRECT: call the shared file by its code-root path: python3 \"$(cat ~/.config/lifehack/code-root)%s\" ..., "
                           "or write a thin wrapper (12 lines or fewer, naming that path, or with '# wraps-shared: %s' in its first lines). "
                           "To extend the tool, change it in %s, not here. RULE: system/hooks/guard_build_mode.sh header; system/register/toolbox.md."
                           % (base, sp, sp, sp, shared_dir))
                    if is_generic(base):
                        denies.append(("copy-generic", "copy-" + re.sub(r"[^A-Za-z0-9_.-]", "_", base),
                                       "HOLD: " + msg + " If this is a genuinely desk-local file that only shares the name, retry the same call and it goes through (this stop happens once per name per session)."))
                    else:
                        denies.append(("copy-hard", None, "BLOCKED: " + msg))
        # ---- clause A: building something new
        if exists:
            kind = None
            if w["verb"] in ("Edit", "MultiEdit", "Write") and (base in ("hooks.json", "settings.json", "settings.local.json")) \
                    and '"command"' in w["content"] and '"command"' not in w["old"] \
                    and (under(t, code) or under(t, os.path.join(HOME, ".claude"))):
                kind = "hook"
            elif base == "jobs.md" and under(t, code) and w["verb"] in ("Edit", "MultiEdit", "Write"):
                old_lines = set((w["old"] if not w["full"] else _open(t).read()).splitlines())
                if any(l.lstrip().startswith("|") and l not in old_lines for l in w["content"].splitlines()):
                    kind = "job"
            if kind:
                denies.append((kind, kind, None))
            continue
        kind = None
        sk = re.search(r"/skills/([^/]+)/SKILL\.md$", t)
        if sk or (w["verb"] == "mkdir" and os.path.basename(os.path.dirname(t)) == "skills"):
            kind = "skill"
        elif base.endswith("-run.sh") and (under(t, os.path.join(code, "system")) or (desks and under(t, desks))):
            kind = "job"
        elif base.endswith(".plist") and "/LaunchAgents/" in t:
            kind = "job"
        elif (under(t, os.path.join(code, "system", "hooks")) and base.endswith(".sh")
              and os.path.dirname(t) == os.path.join(code, "system", "hooks")) \
                or (base.endswith(".sh") and os.path.dirname(t) == os.path.join(code, "hooks")):
            kind = "hook"
        elif desks and under(t, desks) and t != desks:
            first = t[len(desks) + 1:].split("/")[0]
            if not os.path.isdir(os.path.join(desks, first)):
                kind = "desk"
        elif desks and t == desks:
            pass
        if kind:
            denies.append((kind, kind, None))

    if not denies:
        return 0

    # hard blocks win and never write state
    for kind, key, msg in denies:
        if kind in ("copy-hard", "gate-hard"):
            sys.stderr.write(msg + "\n")
            return 2

    # once-per-session items: first one not yet seen is denied (and marked); all marked together
    if not sid:
        warn("no session key; speed bump skipped")
        return 0
    sidk = re.sub(r"[^A-Za-z0-9_.-]", "_", sid)[:80]
    os.makedirs(STATE, exist_ok=True)
    fresh, seen_msgs = [], set()
    for kind, key, msg in denies:
        mk = os.path.join(STATE, "%s.%s.seen" % (key, sidk))
        if os.path.exists(mk) or key in seen_msgs:
            continue
        seen_msgs.add(key)
        fresh.append((kind, key, msg, mk))
    if not fresh:
        return 0
    # A sibling hook that will certainly deny the same call hides our message (parallel hooks: only one
    # reaches the model). Deny anyway, but do NOT spend the once-per-session marker, so the bump shows on
    # the next attempt, after the sibling is satisfied.
    masked = sibling_certain_deny(tool, writes, code, sid)
    out = []
    for kind, key, msg, mk in fresh:
        if not masked:
            _open(mk, "w").close()
        out.append(msg if msg else bump_message(kind, code, " ".join(
            "%s %s" % (w["target"], (w.get("content") or "")[:1500]) for w in writes)))
    sys.stderr.write("\n".join(out) + "\n")
    return 2


_STOP = set("this that with from have will your into when then they them what which also only more each some than about file files tool tools system shared skill skills build home users claude desks desk hooks hook notes python bash echo true false none test tests code data line lines name path text print import return".split())
_ALIAS = {"phone": "notify", "alert": "notify", "buzz": "notify", "push": "notify", "ping": "notify", "message": "notify"}


def _toks(text):
    out = set()
    for w in re.split(r"[^a-z]+", text.lower()):
        if len(w) >= 4 and w not in _STOP:
            out.add(_ALIAS.get(w, w)[:5])
            if w in _ALIAS:
                out.add(w[:5])
    return out


def tool_hint(code, hint):
    """Up to 5 shared tools from toolbox.md whose name/purpose shares a keyword with the target path/content."""
    want = _toks(hint)
    if not want:
        return ""
    scored = []
    for line in _open(os.path.join(code, "system", "register", "toolbox.md")):
        m = re.match(r"- `/(shared/[^`]+)` · (.*)", line)
        if m:
            n = len(want & _toks(m.group(1).replace("/", " ") + " " + m.group(2)))
            if n:
                scored.append((-n, m.group(1), m.group(2)[:70].rstrip()))
    scored.sort()
    return "".join("\n  %s · %s" % (p, d) for _, p, d in scored[:5])


def bump_message(kind, code, hint=""):
    sop, cmd = None, ""
    try:
        for line in _open(os.path.join(code, "system", "hooks", "build_mode_sops.conf")):
            if line.startswith("#") or not line.strip():
                continue
            f = line.rstrip("\n").split("\t")
            if f[0] == kind and len(f) >= 2:
                sop = f[1]; cmd = f[2].replace("$CODE", code) if len(f) > 2 else ""
    except OSError:
        pass
    if not sop:
        where = "its SOP (not configured in system/hooks/build_mode_sops.conf)"
    else:
        full = os.path.join(code, sop)
        where = full if os.path.isfile(full) else "%s (its SOP file could not be found; ask the maintainer)" % full
        if cmd and os.path.isfile(full):
            where += " (%s)" % cmd
    try:
        tools = tool_hint(code, hint)
    except Exception:
        tools = ""
    return ("Looks like you're building a %s. Stop and run /build for this: it hands you the read-list and checks the result. "
            "Or read %s and system/register/toolbox.md first; never copy a shared tool.%s\n"
            "Retry the same call and it goes through (once per session per kind). RULE: system/hooks/build_mode_sops.conf."
            % (kind, where, ("\nShared tools that may already do this:" + tools) if tools else ""))


def main():
    try:
        rc = main_inner()
    except SystemExit:
        raise
    except BaseException as e:   # FAIL OPEN: any internal error allows
        warn("internal error (%s: %s); allowing" % (type(e).__name__, e))
        return 0
    return rc if rc in (0, 2) else 0


if __name__ == "__main__":
    sys.exit(main())

#!/bin/bash
# LHB fire-journal (B4.1): observes only; never alters this hook's decision/exit/stdout/stderr.
_lhb_src="${BASH_SOURCE[0]}"; case "$_lhb_src" in */*) _lhb_dir="${_lhb_src%/*}" ;; *) _lhb_dir=. ;; esac; . "$_lhb_dir/lib/journal.sh" 2>/dev/null || lhb_journal_fire() { :; }
trap 'lhb_journal_fire "$?" "guard_hook_write_integrity.sh" "PreToolUse" "Bash|Write|Edit|MultiEdit" 2>/dev/null || true' EXIT
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: 2026-11-12 a session ran `git apply --3way` against the LIVE ingest_gate_enforce.sh; it conflicted
#      and left <<<<<<< markers; that hook is registered for PreToolUse, so it died with a syntax error
#      (exit 2 = block) on EVERY tool call in EVERY window, including the tools needed to repair it.
#      guard_hook_sop_read.sh only asks "was the SOP read"; nothing asked "is the new file a hook at all".
# GUARDS: (1) Write/Edit/MultiEdit to a *.sh under system/hooks/ (not tests/) or ~/.claude/hooks/ is REFUSED
#      when the RESULTING file fails `bash -n` or has a conflict-marker line (^<<<<<<< ^======= ^>>>>>>>).
#      Repair path stays open: an edit to an already-broken file is allowed if it passes, or strictly
#      reduces the conflict-marker count.
#      (2) Bash: git apply|am|cherry-pick|merge|pull|rebase|revert|stash pop|stash apply and patch are REFUSED
#      when they target the LIVE code root's hooks. Live root = $LIFEHACK_LIVE_ROOT, else $CLAUDE_PLUGIN_ROOT.
#      When one of those is NAMED, a path arg under <live>/system/hooks OR running from inside the live root
#      (cwd / cd / git -C / patch -d) is refused. When NEITHER is set (a settings.json registration), "live" is
#      only a guess, so ONLY a path argument landing in <this repo>/system/hooks blocks -- never merely where you
#      are standing, so normal merges/pulls/applies in a clone or worktree work (review finding 4).
#      `git checkout|restore` is refused only when it pulls a hook in from ANOTHER ref (checkout <ref> -- hook,
#      restore --source); restoring from the index/HEAD is a repair and stays open. `bash -c '...'`, `sh -lc`
#      and `eval` strings are scanned too (to depth 4).
#      Worktrees are untouched: patching a worktree copy is the SANCTIONED route.
# REDIRECT: change hooks in a worktree, then `bash system/tools/hook_swap.sh <worktree>/system/hooks/<name>.sh`
#      (bash -n + that hook's test + last-good copy + atomic swap). Rule: system/sops/hook-sop.md section 6.
# FAIL_POSTURE: closed on an unparseable payload or an unresolvable Write/Edit path (exit 2). Bash text that
#      shlex cannot tokenize falls back to a coarse regex rather than denying every odd command.
# KNOWN LIMITS: a SPEED BUMP on Bash (text matching: `$(...)`, aliases, scripts that patch internally, content
#      written via `cat >`/`sed -i` are NOT inspected -- guard_hook_sop_read.sh covers the write verbs, and
#      hook_runner.sh is the net underneath all of it). The Write/Edit half is exact: it checks the real bytes.
# ─────────────────────────────────────────────────────────────────────────────
set -uo pipefail
_HOOKDIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
export _GUARD_REPO="${_HOOKDIR%/system/hooks}"
INPUT=$(cat 2>/dev/null) || INPUT=""
printf '%s' "$INPUT" | python3 -c '
import sys, json, os, re, shlex, subprocess, tempfile
MARK = re.compile(r"^(<<<<<<<|=======$|>>>>>>>)", re.M)
def deny(msg):
    sys.stderr.write("BLOCKED: " + msg + " REDIRECT: edit a copy in a worktree, then `bash system/tools/hook_swap.sh <worktree>/system/hooks/<name>.sh` (bash -n + that hooks test + last-good copy + atomic swap). Live hooks are never patched in place. RULE: system/sops/hook-sop.md section 6.\n")
    sys.exit(2)
try:
    d = json.load(sys.stdin)
    assert isinstance(d, dict)
except Exception:
    deny("guard_hook_write_integrity could not parse its input -- failing CLOSED.")
ti = d.get("tool_input") or {}
tool = (d.get("tool_name") or "").strip()
cwd = d.get("cwd") or os.getcwd()
rp = os.path.realpath
rawlive = os.environ.get("LIFEHACK_LIVE_ROOT") or os.environ.get("CLAUDE_PLUGIN_ROOT") or os.environ.get("_GUARD_REPO") or "."
live = rp(rawlive)
def problems(text):
    n = len(MARK.findall(text))
    with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as f:
        f.write(text); p = f.name
    try:
        r = subprocess.run(["bash", "-n", p], capture_output=True, text=True)
        err = r.stderr.replace(p, "<new content>").strip().splitlines()[:2] if r.returncode else []
    finally:
        os.unlink(p)
    return n, err
def is_hook(p):
    return p.endswith(".sh") and (("/system/hooks/" in p and "/system/hooks/tests/" not in p) or "/.claude/hooks/" in p)
if tool in ("Write", "Edit", "MultiEdit"):
    path = ti.get("file_path") or ti.get("path") or ""
    if not path:
        sys.exit(0)
    try:
        p = rp(path if os.path.isabs(path) else os.path.join(cwd, path))
    except Exception:
        deny("guard_hook_write_integrity could not resolve the target path -- failing CLOSED.")
    if not is_hook(p):
        sys.exit(0)
    old = None
    if os.path.exists(p):
        try:
            old = open(p, encoding="utf-8", errors="replace").read()
        except Exception:
            deny("cannot read the existing hook to apply this edit to -- failing CLOSED.")
    if tool == "Write":
        new = ti.get("content", "")
    else:
        if old is None:
            sys.exit(0)  # edit of a nonexistent file: the tool itself will error
        edits = ti.get("edits") if tool == "MultiEdit" else [ti]
        new = old
        for e in edits or []:
            o, n = e.get("old_string", ""), e.get("new_string", "")
            if o and o not in new:
                sys.exit(0)  # the tool will refuse this edit itself
            new = new.replace(o, n) if e.get("replace_all") else new.replace(o, n, 1)
    nm, nerr = problems(new)
    if nm == 0 and not nerr:
        sys.exit(0)
    if old is not None:
        om, oerr = problems(old)
        if (om or oerr) and nm < om:
            sys.exit(0)  # repairing an already-broken hook, making progress
    why = ("contains %d conflict-marker line(s)" % nm) if nm else ""
    if nerr:
        why += (" and " if why else "") + "fails bash -n (" + " | ".join(nerr) + ")"
    deny("this %s would leave %s %s. A hook that cannot parse blocks EVERY tool call in EVERY window." % (tool, os.path.basename(p), why))
# ---- Bash ----
cmd = ti.get("command", "") or ""
if not cmd:
    sys.exit(0)
def under(p, root):
    return p == root or p.startswith(root.rstrip("/") + "/")
def res(tok, base):
    t = os.path.expanduser(tok)
    return rp(t if os.path.isabs(t) else os.path.join(base, t))
livehooks = os.path.join(live, "system", "hooks")
# EXPLICIT = the live root was NAMED (LIFEHACK_LIVE_ROOT / CLAUDE_PLUGIN_ROOT). Only then may the current
# directory, `cd` or `git -C` decide anything. With nothing named, "live" is only a guess (the repo this hook lives in, which
# for a settings.json registration is every clone and worktree you work in), so the ONLY thing that blocks is a path
# argument that lands in <that repo>/system/hooks -- never merely where you are standing (review finding 4).
EXPLICIT = bool(os.environ.get("LIFEHACK_LIVE_ROOT") or os.environ.get("CLAUDE_PLUGIN_ROOT"))
# verbs that can leave conflict markers or half-apply a change into a working tree
CWDKINDS = {"apply", "am", "cherry-pick", "merge", "pull", "rebase", "revert"}
def refuse(what):
    deny("`%s` against the LIVE hooks folder (%s). This is how a half-applied patch left conflict markers in a live PreToolUse hook and blocked every window." % (what, live))
def lands_in_hooks(a, base):
    if a.startswith("-") or not a:
        return False
    for cand in (a, a.split("=", 1)[-1]):
        try:
            if under(res(cand, base), livehooks):
                return True
        except Exception as e:
            sys.stderr.write("guard_hook_write_integrity: could not resolve %r (%s); not treated as a hooks path\n" % (cand, e))
    return False
SHELLS = ("bash", "sh", "zsh", "dash", "ksh")
def scan(cmd, cur, depth=0):
    hd = re.search(r"(?<!<)<<-?\s*[\x27\"\\]?[A-Za-z_]", cmd)
    if hd:
        cmd = cmd[:hd.start()]  # heredoc body is data, not commands
    try:
        lex = shlex.shlex(cmd, posix=True, punctuation_chars=";&|")
        lex.whitespace_split = True
        toks = list(lex)
    except ValueError:
        toks = None
    if toks is None:
        if re.search(r"(^|[\s;&|])(git\s+(-\S+\s+(\S+\s+)?)*(apply|am|cherry-pick|merge|pull|rebase|revert|stash\s+(pop|apply))|patch)(\s|$)", cmd) and (live in cmd or rawlive in cmd or (EXPLICIT and under(rp(cwd), live))):
            refuse("git apply/am/cherry-pick/merge/pull/rebase/revert/stash/patch (unparsed command)")
        return
    segs, seg = [], []
    for t in toks:
        if t.startswith("<<"):
            break  # heredoc: everything after is body
        if set(t) <= set(";&|"):
            segs.append(seg); seg = []
        else:
            seg.append(t)
    segs.append(seg)
    for seg in segs:
        while seg and (re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", seg[0]) or seg[0] in ("sudo", "command", "exec", "env", "nohup", "time")):
            seg = seg[1:]
        if not seg:
            continue
        if seg[0] == "cd" and len(seg) > 1:
            cur = res(seg[1], cur); continue
        if depth < 4:
            if seg[0] in SHELLS:
                for j in range(1, len(seg) - 1):
                    if re.match(r"^-[a-zA-Z]*c[a-zA-Z]*$", seg[j]):
                        scan(seg[j + 1], cur, depth + 1); break
            elif seg[0] == "eval" and len(seg) > 1:
                scan(" ".join(seg[1:]), cur, depth + 1)
        kind = None; base = cur; args = seg[1:]; cwdrule = True
        if seg[0] == "git":
            i = 1
            while i < len(seg) and seg[i].startswith("-"):
                if seg[i] == "-C" and i + 1 < len(seg):
                    base = res(seg[i + 1], base); i += 1
                elif seg[i] == "-c":
                    i += 1
                i += 1
            sub = seg[i] if i < len(seg) else ""
            rest = seg[i + 1:]
            if sub in CWDKINDS:
                kind = "git " + sub; args = rest
            elif sub == "stash" and rest and rest[0] in ("pop", "apply"):
                kind = "git stash " + rest[0]; args = rest[1:]
            elif sub in ("checkout", "restore"):
                # restoring a hook from the index/HEAD is a repair; pulling content in from ANOTHER ref is not
                nonopt = [a for a in rest if not a.startswith("-")]
                hits = [a for a in nonopt if lands_in_hooks(a, base)]
                if hits:
                    other = [a for a in nonopt if a not in hits]
                    fromref = bool(other) if sub == "checkout" else any(a == "-s" or a.startswith("--source") or re.match(r"^-s.", a) for a in rest)
                    if fromref:
                        refuse("git %s <ref> -- %s" % (sub, hits[0]))
                continue
        elif seg[0] == "patch":
            kind = "patch"
            for j, a in enumerate(args):
                if a in ("-d", "--directory") and j + 1 < len(args):
                    base = res(args[j + 1], base)
        if not kind:
            continue
        if EXPLICIT and under(base, live):
            refuse(kind + " (run from inside the live root)")
        for a in args:
            if lands_in_hooks(a, base):
                refuse(kind + " targeting " + a)
scan(cmd, rp(cwd))
sys.exit(0)
' 
rc=$?
[ $rc -eq 0 ] && exit 0
# python crash (not a deliberate deny) must also fail closed
[ $rc -eq 2 ] && exit 2
echo "BLOCKED: guard_hook_write_integrity crashed (rc=$rc) -- failing CLOSED. RULE: system/sops/hook-sop.md section 6." >&2
exit 2

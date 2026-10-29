#!/bin/bash
# LHB fire-journal (B4.1): observes only; never alters this hook's decision/exit/stdout/stderr.
_lhb_src="${BASH_SOURCE[0]}"; case "$_lhb_src" in */*) _lhb_dir="${_lhb_src%/*}" ;; *) _lhb_dir=. ;; esac; . "$_lhb_dir/lib/journal.sh" 2>/dev/null || lhb_journal_fire() { :; }
trap 'lhb_journal_fire "$?" "guard_commit_identity.sh" "PreToolUse" "Bash" 2>/dev/null || true' EXIT
#
# ══════════════════════════════════════════════════════════════════════════════
# ⚠  A BOUNDARY, NOT A SPEED BUMP.  Read this before you trust this file.
#
#  Unlike guard_git_commit_signpost.sh / guard_git_push_signpost.sh (fire once per
#  session, then yield), this hook BLOCKS EVERY TIME the identity does not match —
#  Enver's ruling, 2026-09-08, by name: "block". §9's "report, don't gate" governs
#  MIRROR STATE (branch/repo drift); it does not govern WHO is committing, which is
#  a boundary like the existing write-path guards.
# ══════════════════════════════════════════════════════════════════════════════
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: Enver, 2026-09-08: "the test@test.com was a mistake — I had clobbered my own
#      login ... a guard that blocks any work not authored by me is a great idea."
#      Nothing stopped a commit from leaving this machine under a clobbered/wrong
#      git identity before the mistake was visible in `git log`.
# GUARDS: DENIES a real `git commit` / `git commit --amend` / `git rebase` /
#      `git cherry-pick` (never a mere MENTION — tokenized, see MATCHING) whenever
#      the TARGET repo's `git config user.email` is not one of the addresses listed
#      in the AI Brain's config/ship-identity.md. ALLOWS every other git verb, and
#      allows silently (every time, not just once) when the identity matches.
# REDIRECT: run `git -C <repo> config user.email you@example.com` to fix the local
#      identity, or add the address to ship-identity.md if it is a legitimate second
#      address, then retry the exact same command.
# SIGNPOST: identity is a boundary, not a mirror-state report. To change what is gated
#      here, get sign-off, then update this guard.
# MATCHING: argv STRUCTURE via shlex, never a keyword grep on the command string —
#      a literal "git commit" inside a quoted commit message must not trip it.
#      Segments split on ; && || |; only a token that IS literally `git` (or ends in
#      /git), followed by the literal subcommand `commit` / `rebase` / `cherry-pick`,
#      counts. `commit --amend` is still the `commit` subcommand. On a shlex failure
#      (heredoc, unbalanced quote) we fall back to a raw-text adjacency scan for the
#      same four shapes, same fallback guard_git_commit_signpost.sh uses, and deny
#      only if one of those shapes is present.
# IDENTITY (repo target): resolved from the command's ACTUAL target — the `-C`
#      argument (parsed by shlex above) or a leading `cd <path> &&`, falling back to
#      $PWD only when neither is given. Never $PWD unconditionally — that was the
#      push-signpost's bug (O3b). shlex.split() does NOT expand `~` or `$HOME` — a target
#      of `~`, `~/repo`, `$HOME/repo` or `${HOME}/repo` is expanded here, using THIS HOOK'S
#      OWN $HOME, before it is used for anything below (2026-09-16, #tilde: unexpanded, it
#      denied a correctly-configured repo with a false "no git config user.email set").
# IDENTITY (allow-list): read from THIS RUN's Brain root — resolved by running
#      `shared/brain_root.py --quiet`, preferring the copy AT THE TARGET REPO
#      (`<target-repo>/shared/brain_root.py`) when it exists there, and falling back to
#      THIS SCRIPT'S OWN plugin install (`$CLAUDE_PLUGIN_ROOT/shared/brain_root.py`, or this
#      script's own directory when that env var is unset) when it does not — e.g. a commit
#      made inside a repo that is not the Harness clone (2026-09-15, #O5: this guard denied
#      every commit in such a repo, because brain_root.py resolves the Brain from ITS OWN
#      file position, never from cwd — same class of bug as guard_findings_write.sh's
#      winpath_fold.py lookup, PR #165). Never a path baked into this script (a hard-coded
#      path would be this operator's path shipped to every student). The allow-list is every
#      line in `<brain>/config/ship-identity.md`
#      that CONTAINS "@" (same shape-detection identity_rules.py already uses for
#      that file: contains "@" -> an address), comments (#) and blank lines skipped,
#      compared case-insensitively.
# FAIL_POSTURE: closed — every one of these is a DENY, not a silent allow: brain
#      root unresolved, ship-identity.md missing/unreadable, zero "@" lines found in
#      it, `git config user.email` empty/unreadable, or the hook payload itself not
#      readable JSON. An unguarded commit is the failure this hook exists to prevent.
# UPDATED: 2026-09-16
# RULE: system/hook-contract.md (mechanics)
# ─────────────────────────────────────────────────────────────────────────────
# guard_commit_identity.sh — PreToolUse hook (matcher: Bash)

# This script's own directory, never the target repo or $PWD — the fallback route for
# resolving shared/brain_root.py below (see IDENTITY (allow-list) above).
_HOOKDIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd -P)"

INPUT=$(cat 2>/dev/null)

VERDICT=$(printf '%s' "$INPUT" | python3 -c '
import sys, json, shlex, os

try:
    d = json.load(sys.stdin)
except Exception:
    print("PARSE_ERROR"); raise SystemExit

cmd = ((d.get("tool_input") or {}).get("command") or "")
if not cmd.strip():
    print("NOT_OURS"); raise SystemExit

WRITE_VERBS = ("commit", "rebase", "cherry-pick")

import re as _re
_shape = _re.compile(r"(^|[;&|(\s])git\s+(-{1,2}\S+\s+)*(commit|rebase|cherry-pick)\b")

try:
    # punctuation_chars=True splits ; && || | ( ) off adjacent words, so
    # "cd ~/repo; git commit" yields cd, ~/repo, ; (3b-fa: it used to yield "repo;").
    # Unquoted newlines are command separators too: turn them into " ; " first.
    _o, _q, _k = [], "", 0
    while _k < len(cmd):
        _ch = cmd[_k]
        if _q:
            if _ch == _q: _q = ""
            elif _ch == "\\" and _q == "\"" and _k + 1 < len(cmd): _o.append(_ch); _k += 1; _ch = cmd[_k]
        elif _ch in "\"\x27": _q = _ch
        elif _ch == "\\" and _k + 1 < len(cmd): _o.append(_ch); _k += 1; _ch = cmd[_k]
        elif _ch == "\n": _ch = " ; "
        _o.append(_ch); _k += 1
    _lex = shlex.shlex("".join(_o), posix=True, punctuation_chars=True)
    _lex.whitespace_split = True
    _lex.commenters = ""
    toks = list(_lex)
except ValueError:
    if _shape.search(cmd):
        print("CHECK:"); raise SystemExit
    print("NOT_OURS"); raise SystemExit

# Items are (sep, op) or (word, text). Punctuation-only tokens may glue several operators.
items = []
for t in toks:
    if t and all(ch in "();<>|&" for ch in t):
        for m in _re.findall(r"&&|\|\||;;|[;|&()]|[<>]+&?", t):
            items.append(("sep", m) if m in ("&&", "||", ";;", ";", "|", "&", "(", ")") else ("word", m))
    else:
        items.append(("word", t))

def is_git(tok):
    return os.path.basename(tok) == "git"

_ASSIGN = _re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_VAR = _re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)")
HOME = os.environ.get("HOME", "")
cvars = {}   # variables assigned earlier in THIS command

def expand(p):
    # ~ and $VAR/${VAR}: HOME from the hook env, others only if set earlier in this command.
    # An unresolvable $VAR is left LITERAL, so the bash side fails closed (deny) as before.
    if p == "~" or p.startswith("~/"):
        p = HOME + p[1:]
    def sub(m):
        n = m.group(1) or m.group(2)
        if n in cvars: return cvars[n]
        if n == "HOME" and HOME: return HOME
        return m.group(0)
    return _VAR.sub(sub, p)

def resolve(p, cwd):
    p = expand(p)
    if p and not p.startswith("/") and "$" not in p and cwd and "$" not in cwd:
        p = os.path.join(cwd, p)
    return p

cwd = ""
stack = []   # subshell scopes: (cwd, vars) restored at ")"
buf = []

def flush():
    # Process one finished segment. Returns a CHECK target string, or None.
    global cwd, cvars
    seg = buf[:]
    del buf[:]
    if not seg:
        return None
    if seg[0] == "export":
        seg = seg[1:]
    i = 0
    while i < len(seg) and _ASSIGN.match(seg[i]):
        i += 1
    if i == len(seg):
        for w in seg:
            k, v = w.split("=", 1)
            cvars[k] = expand(v)
        return None
    if seg[i] == "cd":
        args = [w for w in seg[i + 1:] if not w.startswith("-") or w == "-"]
        cwd = resolve(args[0], cwd) if args else HOME
        return None
    if not is_git(seg[i]):
        return None
    j = i + 1
    c_target = ""
    while j < len(seg) and seg[j].startswith("-"):
        if seg[j] == "-C":
            if j + 1 < len(seg):
                c_target = resolve(seg[j + 1], cwd)
            j += 2
        elif seg[j] == "-c":
            j += 2
        else:
            j += 1
    if j < len(seg) and seg[j] in WRITE_VERBS:
        return c_target or cwd
    return None

for kind, v in items + [("sep", ";")]:
    if kind == "word":
        buf.append(v); continue
    r = flush()
    if r is not None:
        print("CHECK:" + r); raise SystemExit
    if v == "(":
        stack.append((cwd, dict(cvars)))
    elif v == ")" and stack:
        cwd, cvars = stack.pop()

print("OK")
' 2>/dev/null)

case "$VERDICT" in
  OK|NOT_OURS)
    exit 0
    ;;
  CHECK:*)
    _target="${VERDICT#CHECK:}"

    # shlex.split() above does NOT perform shell expansion, so a target written as "~", "~/repo",
    # "$HOME/repo" or "${HOME}/repo" reaches us as that LITERAL string — `git -C "$_target"` then
    # fails to resolve it and falls through to a false "no git config user.email set" / MISMATCH
    # deny, even when the real repo's identity is fine and on the allow-list (2026-09-16, observed
    # live: `cd ~/.claude/skills/ClaudeOps && git commit` denied "has no git config user.email
    # set" though that repo's email IS set and allow-listed). Expand using THIS HOOK'S OWN $HOME —
    # never a hard-coded path — before anything below resolves or reports on $_target.
    case "$_target" in
      '~')
        _target="$HOME"
        ;;
      '~/'*)
        _target="$HOME/${_target:2}"
        ;;
      '$HOME')
        _target="$HOME"
        ;;
      '$HOME/'*)
        _target="$HOME/${_target:6}"
        ;;
      '${HOME}')
        _target="$HOME"
        ;;
      '${HOME}/'*)
        _target="$HOME/${_target:8}"
        ;;
    esac

    [ -n "$_target" ] || _target="$PWD"

    _deny() {
      printf '%s\n' "$1" >&2
      exit 2
    }

    _repo_name=$(basename "$(git -C "$_target" rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null)
    [ -n "$_repo_name" ] || _repo_name="$_target"

    _user_email=$(git -C "$_target" config user.email 2>/dev/null)
    if [ -z "$_user_email" ]; then
      _deny "🛑 COMMIT IDENTITY (blocked): $_repo_name has no git config user.email set. WHY: an unattributed commit is exactly the failure this guard exists to prevent. REDIRECT: run 'git -C $_target config user.email you@example.com' with the address listed in your Brain's config/ship-identity.md, then retry. FAIL_POSTURE: closed."
    fi

    # Prefer the TARGET repo's own copy (the common case: committing inside the Harness
    # clone itself). When the target repo does not carry shared/brain_root.py at all — any
    # repo that is not the Harness (e.g. a private personal repo) — fall back to THIS
    # SCRIPT'S OWN plugin install, never $PWD or the target: a non-Harness repo must still be
    # CHECKED, not skipped. brain_root.py resolves the Brain from its own file position, so
    # either copy resolves to the same one AI Brain on this machine.
    _brain_root_script="$_target/shared/brain_root.py"
    if [ ! -f "$_brain_root_script" ]; then
      _plugin_root="${CLAUDE_PLUGIN_ROOT:-${_HOOKDIR%/system/hooks}}"
      _brain_root_script="$_plugin_root/shared/brain_root.py"
    fi
    if [ ! -f "$_brain_root_script" ]; then
      _deny "🛑 COMMIT IDENTITY (blocked): cannot find shared/brain_root.py under $_target or under the plugin install ($_plugin_root) to resolve the AI Brain. WHY: the identity allow-list lives in the Brain, never hard-coded in this script. REDIRECT: verify the install (INSTALL.md) put shared/brain_root.py at the Harness repo root, then retry. FAIL_POSTURE: closed."
    fi

    _brain=$(python3 "$_brain_root_script" --quiet 2>/dev/null)
    if [ -z "$_brain" ] || [ ! -d "$_brain" ]; then
      _deny "🛑 COMMIT IDENTITY (blocked): the AI Brain root is not set or not resolvable ('$_brain_root_script --quiet' failed). WHY: no Brain root means no identity allow-list to check against. REDIRECT: set it per INSTALL.md ('python3 shared/brain_root.py --set \"<folder>\"'), then retry. FAIL_POSTURE: closed."
    fi

    _identity_file="$_brain/config/ship-identity.md"
    if [ ! -f "$_identity_file" ]; then
      _deny "🛑 COMMIT IDENTITY (blocked): $_identity_file does not exist. WHY: no identity file means no allow-list — an unguarded commit is the failure this hook exists to prevent. REDIRECT: create it (INSTALL.md / the shipping lane already documents the format: one term per line, '#' comments) with at least one email address line, then retry. FAIL_POSTURE: closed."
    fi

    _match=$(python3 -c '
import sys
identity_file, user_email = sys.argv[1], sys.argv[2].strip().lower()
allowed = []
try:
    with open(identity_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "@" in line:
                allowed.append(line.lower())
except Exception:
    print("READ_ERROR"); raise SystemExit

if not allowed:
    print("NO_ADDRESSES"); raise SystemExit

print("MATCH" if user_email in allowed else "MISMATCH:" + ",".join(allowed))
' "$_identity_file" "$_user_email" 2>/dev/null)

    case "$_match" in
      MATCH)
        exit 0
        ;;
      NO_ADDRESSES)
        _deny "🛑 COMMIT IDENTITY (blocked): $_identity_file has zero '@' (address) lines. WHY: an empty allow-list means every identity fails closed, by design. REDIRECT: add your own email address as its own line in that file, then retry. FAIL_POSTURE: closed."
        ;;
      MISMATCH:*)
        _allowed_list="${_match#MISMATCH:}"
        _deny "🛑 COMMIT IDENTITY (blocked): $_repo_name is configured with user.email '$_user_email', which is not in the allow-list ($_identity_file: $_allowed_list). WHY: a commit under the wrong identity is invisible until git log, by which point it has already happened. REDIRECT: run 'git -C $_target config user.email <allowed address>' to fix the local identity, or add this address to ship-identity.md if it is a legitimate second address, then retry the exact same command. This blocks every time, not just once."
        ;;
      *)
        _deny "🛑 COMMIT IDENTITY (blocked): could not read or parse $_identity_file. FAIL_POSTURE: closed."
        ;;
    esac
    ;;
  *)
    printf '%s\n' "BLOCKED (commit identity guard): the hook payload itself was not readable JSON. WHY: failing OPEN would let an unattributed commit slip past unseen. REDIRECT: retry the command. FAIL_POSTURE: closed." >&2
    exit 2
    ;;
esac

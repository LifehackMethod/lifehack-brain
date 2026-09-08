#!/bin/bash
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
# SIGNPOST: system/sops/github-sop.md — identity is a boundary, not a mirror-state
#      report. To change what is gated here, edit that SOP + get sign-off.
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
#      push-signpost's bug (O3b).
# IDENTITY (allow-list): read from THIS RUN's Brain root — resolved via
#      `<target-repo>/shared/brain_root.py --quiet`, never a path baked into this
#      script (a hard-coded path would be this operator's path shipped to every
#      student). The allow-list is every line in `<brain>/config/ship-identity.md`
#      that CONTAINS "@" (same shape-detection identity_rules.py already uses for
#      that file: contains "@" -> an address), comments (#) and blank lines skipped,
#      compared case-insensitively.
# FAIL_POSTURE: closed — every one of these is a DENY, not a silent allow: brain
#      root unresolved, ship-identity.md missing/unreadable, zero "@" lines found in
#      it, `git config user.email` empty/unreadable, or the hook payload itself not
#      readable JSON. An unguarded commit is the failure this hook exists to prevent.
# UPDATED: 2026-09-08
# RULE: system/sops/github-sop.md — system/hook-contract.md (mechanics)
# ─────────────────────────────────────────────────────────────────────────────
# guard_commit_identity.sh — PreToolUse hook (matcher: Bash)

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

try:
    toks = shlex.split(cmd, comments=False, posix=True)
except ValueError:
    import re as _re
    _shape = _re.compile(r"(^|[;&|(\s])git\s+(-{1,2}\S+\s+)*(commit|rebase|cherry-pick)\b")
    if _shape.search(cmd):
        print("CHECK:"); raise SystemExit
    print("NOT_OURS"); raise SystemExit

segments, buf = [], []
for t in toks:
    if t in ("&&", "||", ";", "|"):
        if buf: segments.append(buf)
        buf = []
    else:
        buf.append(t)
if buf: segments.append(buf)

def is_git(tok):
    return os.path.basename(tok) == "git"

_cd_target = ""
for seg in segments:
    if seg and seg[0] == "cd" and len(seg) >= 2:
        _cd_target = seg[1]

for seg in segments:
    i = 0
    while i < len(seg) and "=" in seg[i] and not seg[i].startswith("-"):
        i += 1
    if i >= len(seg) or not is_git(seg[i]):
        continue
    j = i + 1
    c_target = ""
    while j < len(seg) and seg[j].startswith("-"):
        if seg[j] == "-C":
            if j + 1 < len(seg):
                c_target = seg[j + 1]
            j += 2
        elif seg[j] == "-c":
            j += 2
        else:
            j += 1
    if j < len(seg) and seg[j] in WRITE_VERBS:
        _target = c_target or _cd_target
        print("CHECK:" + _target); raise SystemExit

print("OK")
' 2>/dev/null)

case "$VERDICT" in
  OK|NOT_OURS)
    exit 0
    ;;
  CHECK:*)
    _target="${VERDICT#CHECK:}"
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

    _brain_root_script="$_target/shared/brain_root.py"
    if [ ! -f "$_brain_root_script" ]; then
      _deny "🛑 COMMIT IDENTITY (blocked): cannot find shared/brain_root.py under $_target to resolve the AI Brain. WHY: the identity allow-list lives in the Brain, never hard-coded in this script. REDIRECT: verify the install (INSTALL.md) put shared/brain_root.py at the repo root, then retry. FAIL_POSTURE: closed."
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

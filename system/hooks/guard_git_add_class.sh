#!/bin/bash
#
# ══════════════════════════════════════════════════════════════════════════════
# ⚠  SPEED BUMP, NOT A BOUNDARY.  Read this before you trust this file.
#
#  This guard inspects a command as TEXT. A shell has infinite equivalent ways to
#  spell the same command, so a text matcher is always one phrasing behind. Treat
#  what follows as a speed bump that raises the cost of a mistake — never as a wall
#  that makes one impossible.
#
#  MEASURED HERE, 2026-08-14, not cited from elsewhere. Four of these guards were
#  fire-tested and then attacked by two independent auditors charged to break them:
#    · the first found 20 bypasses in ~20 minutes; 11 of 13 headline claims reproduced
#    · after a rewrite, the second found 13 more, all reproduced
#    · after three rounds of hardening, 1 of 27 tested attack forms still passes
#  Every one of those holes was in a guard reading a command STRING. This system's
#  own journal states the pattern: 17 of 52 registered hooks guard Bash, and every
#  guard that failed was one of them — every guard that fired correctly was on a
#  typed tool.
#
#  PRIOR ART, same conclusion: CVE-2025-66032 — eight independent bypasses of Claude
#  Code's own regex blocklist (`man --html`, `sort --compress-program`, sed's `e`
#  flag, `$IFS`, `${var@P}`), plus an independently reproduced `$(...)` bypass of an
#  allowlist.
#
#  ⇒ IF YOU ARE ADDING A CONTROL THAT MUST NOT BE BYPASSED, DO NOT ADD IT HERE.
#    Put it on a typed tool, or make the dangerous act structurally impossible.
#    Adding a ninth pattern to this file buys less than it appears to.
# ══════════════════════════════════════════════════════════════════════════════
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: 2026-07-27 — a session working on skill-building-sop.md ran a broad `git add`
#      and committed EVERYTHING dirty in the clone. Commit fd16e34, titled
#      "docs(sop): promote the floor->instrument mapping", silently carried a 388-line
#      organism-health.py and an 11-line system-health.py belonging to a different
#      feature in a different window — and pushed it. Nothing was lost, but half a
#      feature is now attributed to an unrelated docs commit, and the owning window's
#      `git status` showed its own new file as already-tracked-and-clean, which reads
#      exactly like the edit never happened. This repo can be open in several concurrent
#      Claude windows at once, so a whole-tree add is never "my changes" — it is everyone's.
# GUARDS: Blocks the whole EVERYTHING-ADD CLASS, not just `-A`. `git add -A`, `--all`,
#         `-u`/`--update`, `git add .`, `git add :/`, `git add *`, and bare `git add`
#         with no pathspec. Banning only `-A` would be theater: `.` is the likelier
#         reflex and sweeps just as much. Also covers `git commit -a/--all`, the same
#         act wearing a different flag.
# REDIRECT: Stage the files you actually changed, by explicit path —
#           `git add system/tools/foo.py system/hooks/bar.sh`. A scoped directory add
#           (`git add system/tools/organism/`) is deliberate and still allowed.
# SIGNPOST: system/sops/build-sop.md -> "A CONCURRENT window's broad `git add`/`commit -a`
#           will sweep up YOUR in-progress files". To change this rule, edit that SOP
#           entry and get sign-off — do not weaken the hook alone.
# FAIL_POSTURE: closed
# UPDATED: 2026-07-28
# ─────────────────────────────────────────────────────────────────────────────
# guard_git_add_class.sh — PreToolUse hook (matcher: Bash)
# Blocks whole-tree staging in a clone shared by many concurrent sessions.

INPUT=$(cat)
COMMAND=$(printf '%s' "$INPUT" | python3 -c "
import sys, json
try:
    print(json.load(sys.stdin).get('tool_input', {}).get('command', ''))
except Exception:
    print('__PARSE_ERROR__')
" 2>/dev/null)

# FAIL CLOSED — a guard that cannot read its input must not wave the command through.
if [ "$COMMAND" = "__PARSE_ERROR__" ]; then
  printf '%s\n' "BLOCKED: guard_git_add_class could not parse the tool input — failing CLOSED. WHY: allow-on-parse-error silently reopens whole-tree staging in a clone that can be open in several concurrent windows at once. REDIRECT: retry the command; if it persists the payload is malformed." >&2
  exit 2
fi

# ── THE FALSE-POSITIVE TRAP ───────────────────────────────────────────────────
# A guard that greps a command STRING for a keyword fires on mere MENTIONS: a
# `git commit -m "stop using git add -A"`, a `grep "git add ."`, an `echo`. That
# already happened once — the status-bar pointer guard blocked its own build's commit.
# So heredoc bodies are stripped BEFORE matching, and we only inspect real `git add` /
# `git commit` invocations, never the raw string — never a keyword found anywhere in it.
#
# ⛔ FIXED 2026-08-28 (Windows client, ACTIVE BLOCKER): this used to ALSO blank out every
# quoted substring to a bare space before splitting into segments — `s = re.sub(r'"[^"]*"',
# ' ', s)` and the single-quote twin. That does not merely neutralise a MENTION inside a
# quoted string (the case the comment above is about); it deletes a REAL, QUOTED PATHSPEC
# too, because the substitution runs on the raw text before shlex ever sees it. So
# `git add "system/hooks/pm_flag.sh"` was rewritten to `git add ` before parsing, shlex
# saw zero path tokens, and the verdict was "git add with no pathspec" — a whole-tree-add
# false positive on the single most careful way to stage one file. Windows paths routinely
# contain spaces (`C:\Program Files\...`), so a Windows session MUST quote — the correct,
# careful command was exactly what got blocked, every time.
# The stripping was never needed for the false-positive it cites: shlex.split() already
# treats a quoted string as ONE token, so `grep "git add ."` tokenizes to ['grep', 'git
# add .'] — that second token is not the exact string 'git', so the git-detection below
# (which looks for a token that literally IS 'git') never fires on it, quotes or no quotes.
# Same reasoning covers `git commit -m "stop using git add -A"`: shlex keeps the message
# as one token, so it never reads as a -a/--all flag. Removing the blanking step closes the
# false positive on a quoted pathspec (verified: git add "path with spaces/file.sh" now
# passes) while every deny case above — git add ., -A, --all, bare git add, git commit -a,
# and the quoted-mention false positives this comment names — is unchanged: see
# system/hooks/tests/test_git_add_class.sh.
VERDICT=$(printf '%s' "$COMMAND" | python3 -c "
import re, sys, shlex
s = sys.stdin.read()
s = re.sub(r'<<-?\s*[\"\x27]?(\w+)[\"\x27]?.*', ' ', s, flags=re.S)   # heredoc body
bad = []
for seg in re.split(r'&&|\|\||;|\||\n', s):
    seg = seg.strip()
    if not seg:
        continue
    try:
        parts = shlex.split(seg)
    except ValueError:
        parts = seg.split()
    if not parts:
        continue
    try:
        gi = next(i for i, p in enumerate(parts) if p == 'git' or p.endswith('/git'))
    except StopIteration:
        continue
    rest = parts[gi + 1:]
    i = 0
    while i < len(rest):                       # skip git-global opts (-C <path>, -c k=v)
        if rest[i] in ('-C', '-c'):
            i += 2
        elif rest[i].startswith('-'):
            i += 1
        else:
            break
    if i >= len(rest):
        continue
    sub, args = rest[i], rest[i + 1:]
    if sub == 'add':
        flags = [a for a in args if a.startswith('-')]
        paths = [a for a in args if not a.startswith('-')]
        # --dry-run / -n stages NOTHING; it only reports. Blocking it would be a false
        # positive on a command that is literally how you inspect the blast radius.
        if any(f in ('-n', '--dry-run') for f in flags):
            continue
        for f in flags:
            if f in ('-A', '--all', '-u', '--update', '--no-ignore-removal'):
                bad.append('git add ' + f)
            elif re.fullmatch(r'-[A-Za-z]+', f) and ('A' in f[1:] or 'u' in f[1:]):
                bad.append('git add ' + f)
        for p in paths:
            if p in ('.', './', ':/', '*', ':/*', '..') or p.startswith(':/'):
                bad.append('git add ' + p)
        if not paths and not any(f in ('-p','--patch','-i','--interactive','-n','--dry-run') for f in flags):
            bad.append('git add with no pathspec')
    elif sub == 'commit':
        for a in args:
            if a in ('-a', '--all'):
                bad.append('git commit ' + a)
            elif re.fullmatch(r'-[A-Za-z]+', a) and 'a' in a[1:]:
                bad.append('git commit ' + a)
print('|'.join(sorted(set(bad))))
" 2>/dev/null)

if [ -n "$VERDICT" ]; then
  printf '%s\n' "BLOCKED: whole-tree git staging ($VERDICT). WHY: this clone can be open in several concurrent Claude windows at once, so an everything-add is never 'my changes' — it is everyone's. On the donor system this hook was ported from, exactly this swept a 388-line file and an 11-line file from another window into an unrelated docs commit and pushed it; the owning window's git status then showed its own new file as already-tracked-and-clean, which reads like the edit never happened. REDIRECT: stage what you actually changed, by explicit path — 'git add system/tools/foo.py system/hooks/bar.sh'. A scoped directory add ('git add system/tools/') is deliberate and still allowed. To see only YOUR work here, diff against the commit you expect, not against HEAD. RULE: system/sops/build-sop.md -> 'A CONCURRENT window's broad git add/commit -a will sweep up YOUR in-progress files'; edit that entry + get sign-off to change this." >&2
  exit 2
fi

exit 0

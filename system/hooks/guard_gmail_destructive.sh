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
#  MEASURED, 2026-08-14, in the system this was ported from. Four sibling guards were
#  fire-tested and then attacked by two independent auditors charged to break them:
#    · the first found 20 bypasses in ~20 minutes; 11 of 13 headline claims reproduced
#    · after a rewrite, the second found 13 more, all reproduced
#    · after three rounds of hardening, 1 of 27 tested attack forms still passes
#  Every one of those holes was in a guard reading a command STRING. The pattern that
#  system's journal states: every guard that failed was on Bash — every guard that
#  fired correctly was on a typed tool.
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
# WHY: Every other Google service this system can reach is guarded — calendar, tasks and
#      sheets each have a hook, and `gws auth logout` has one. Mail had none, and mail is the
#      one where the mistake cannot be taken back: a label move is reversible, a delete is not.
#      The gap was found by counting the registered guards against the services reachable with
#      one `gws` login, not by anything going wrong. ⭐ THE ASYMMETRY IS THE WHOLE ARGUMENT: if
#      you never granted Gmail scope, this guard costs you literally nothing because no such
#      command can succeed anyway; if you did grant it, it is the only thing standing between an
#      unattended run and mail you cannot get back. In the system this came from, exactly that
#      nearly happened — a cron circuit-breaker bug half-opened an ingest job and it processed 43
#      threads it was never handed. It was reading. Had the runaway verb been `delete`, nothing
#      would have stopped it.
# GUARDS: Any `gws gmail` command carrying a destructive verb on messages or threads —
#      `delete`, `batchDelete`, or `trash`. Blocks ALL of them, with no confirm path: an
#      unattended run has nobody to confirm, and this protects an irreversible act. `modify`
#      (label moves), `untrash` (recovery) and every read verb pass through untouched.
# REDIRECT: Move the label instead — that is the reversible operation, and it is what any
#      sorting or filing workflow actually needs:
#      gws gmail users threads modify --user-id me --id <THREAD_ID> \
#          --add-label-ids <LABEL_TO_ADD> --remove-label-ids <LABEL_TO_REMOVE>
#      If mail genuinely must be destroyed, YOU do it in the Gmail UI. That is not a limitation
#      being worked around — it is the one place a human sees what is about to go.
# SIGNPOST: The rule is this file's own GUARDS line above: an agent in this system never
#      irreversibly destroys your mail; it moves labels. Which Google services your agent can
#      reach at all is YOUR setting, decided at the sit-down in `INSTALL.md` ("grant only the
#      scopes you actually intend to use"). To change what is blocked here, change the rule
#      above deliberately and amend this hook — never loosen the hook to fit a command that was
#      refused. ⚠ Do NOT read `system/security-canon.md`'s hook table as this rule's home: that
#      table is a historical record of the donor system's hooks and says so in its own scope note.
# FAIL_POSTURE: closed — unparseable stdin DENIES (hook-sop.md §3.2). A guard that cannot read
#      its input must never allow: the cost of a false block is one retry with a label move, and
#      the cost of a false allow is mail that does not come back.
# UPDATED: 2026-08-14 (ported; the deryl-ingest desk and _ClaudeOps rule pointers it carried do
#      not exist here, so the rule was restated in this header rather than left dangling — a
#      redirect to a file the reader does not have is worse than no redirect at all)
# ─────────────────────────────────────────────────────────────────────────────
# guard_gmail_destructive.sh — PreToolUse hook (matcher: Bash)

DENY='{"decision":"block","reason":"BLOCKED: destructive Gmail verb (delete / batchDelete / trash). WHY: Gmail deletion is IRREVERSIBLE and no agent path here is authorised to perform it — mail is moved by LABEL ONLY, which is reversible by design. Every other Google service reachable with one gws login is guarded; mail is the one where the mistake cannot be taken back. REDIRECT: use a label move instead — gws gmail users threads modify --user-id me --id <THREAD_ID> --add-label-ids <LABEL_TO_ADD> --remove-label-ids <LABEL_TO_REMOVE>. If mail truly must be destroyed, YOU do it in the Gmail UI, where you can see what is about to go. RULE: the GUARDS line in system/hooks/guard_gmail_destructive.sh — an agent never irreversibly destroys your mail. Change that rule deliberately and amend the hook; never loosen the hook to fit a refused command."}'

deny() { printf '%s\n' "$DENY" >&2; exit 2; }

# Fail-closed: a guard that cannot read its own input must DENY, never pass.
INPUT=$(cat 2>/dev/null) || deny
COMMAND=$(printf '%s' "$INPUT" | python3 -c "
import sys, json
try:
    print(json.load(sys.stdin).get('tool_input', {}).get('command', ''))
except Exception:
    sys.exit(3)
" 2>/dev/null) || deny

# Not a gws gmail command — pass through.
# ⛔ THIS PRE-FILTER USED TO DECIDE THE CASE. It grepped the RAW command for the
# binary and the service, case-sensitively and un-normalised -- so a quote-spliced
# binary or an uppercased service word exited 0 here, and the real parser below was
# never invoked. Measured: the parser blocks those same commands when called
# directly. A scope gate must be WIDER than the check it guards, never narrower.
SCOPE="$(printf '%s' "$COMMAND" | tr -d "\\'\"" )"
# ⛔ THE BINARY IS MATCHED AS A TOKEN ANYWHERE, NOT AS THE WORD BESIDE THE SERVICE.
# Measured 2026-08-14 (firetest-binary-indirection.sh): the previous line required a
# literal `gws` adjacent to the service word, so
#     V=gws ; $V <service> ... <destructive verb>
# never matched, this gate exited 0, and the command reached NONE of the checks below it. A guard
# that never sees a command has not allowed it on purpose — it has not seen it, which is worse,
# because every presence-based audit still scores it green. Three rounds of hardening that day
# tested VERB and TARGET indirection and never scoped the BINARY NAME.
# Two gates now, both deliberately loose: is a gws binary NAMED anywhere, and is this service named.
# A mere mention costs nothing — the real checks below decide, and they are what should decide.
printf '%s' "$COMMAND" | grep -qE "(^|[^A-Za-z0-9_])gws([^A-Za-z0-9_]|$)|bin/gws" 2>/dev/null || exit 0
printf '%s' "$COMMAND" | grep -qiE "(^|[[:space:]])gmail([[:space:]]|$)" 2>/dev/null || exit 0

# `untrash` is RECOVERY (it undoes a trash) and must never be blocked. Check it BEFORE the
# destructive match, because "untrash" contains "trash" as a substring — the classic
# positive-token-inside-the-negative-state trap.
printf '%s' "$COMMAND" | grep -qE "\buntrash\b" 2>/dev/null && exit 0

# ⚠ MATCH A COMMAND POSITION, NOT A KEYWORD ANYWHERE IN THE STRING. An earlier version grepped
# the whole command for gmail...threads...trash and blocked a python heredoc that was WRITING
# THAT TEXT INTO A PLAN FILE. Nothing was being executed; the words were data. A guard must match
# the write-to-target PATTERN, never the keyword alone — and must be tested against benign
# commands that MENTION the tokens.
#
# So: split the command into segments at real shell separators, and only consider a segment
# whose FIRST WORD is the gws binary. A gws invocation quoted inside a heredoc, an echo, a
# commit message or a python string is never in first position, so it is data and passes.
# ⭐ THE PARSER LIVES IN ONE PLACE — system/hooks/lib/gws_guard.py — because several guards need
# exactly this and each got it wrong differently.
# ⛔ THE HOLE THIS CLOSES, MEASURED 2026-08-14:
#   ID=18abc gws gmail users threads trash --user-id me --id "$ID"   ->  rc 0, ALLOWED
# The old inline parser took seg.split()[0], got the assignment `ID=18abc`, failed its
# ^gws$ test and SKIPPED the segment entirely. An assignment prefix is ordinary shell.
# The shared parser strips assignment prefixes, keeps command substitutions visible so
# indirection can still be detected, and treats an unresolvable command as UNKNOWN ->
# it fails CLOSED. `messages|threads` is passed as the SCOPE, so deleting a LABEL still passes.
LIB="$(cd "$(dirname "$0")" 2>/dev/null && pwd)/lib/gws_guard.py"
[ -r "$LIB" ] || deny   # fail-closed: no parser, no permission
printf '%s' "$COMMAND" | python3 "$LIB" --service gmail \
  --require-any messages,threads \
  --destructive delete,batchDelete,trash 2>/dev/null
[ $? -eq 7 ] && deny

exit 0

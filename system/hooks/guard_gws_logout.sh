#!/bin/bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: `gws auth logout` clears ALL Google credentials and the token cache for EVERY window at
#      once, and there is no undo — the only way back is a full re-login sit-down. It was run
#      once during debugging on the donor system and left every window's auth broken.
#      ⛔ THE REASON THIS IS A HOOK AND NOT A PERMISSION RULE: a `permissions.deny` entry for it
#      is BYPASSED by `--dangerously-skip-permissions`, which is exactly how headless and
#      persona sessions run. A PreToolUse hook is NOT bypassed. This is the real backstop, and
#      without it the rule is only a sentence.
# GUARDS: any Bash command invoking `gws auth logout` — bare or via a full path. An agent must
#      never run it and never recommend it. It is a deliberate, user-only recovery action.
# REDIRECT: hit a stale-token 403? Do NOT log out. Tell the PERSON to run the logout and
#      `gws auth login --full` themselves — it is their call, not the agent's. Re-authenticating
#      is a sit-down with a browser, so it never happens by surprise.
# SIGNPOST: the rule is stated for the human in `INSTALL.md` ("Never `gws auth logout`, and never
#      delete or move `~/.config/gws/` … there is no undo"). ⛔ That paragraph PROMISED this
#      protection while this hook did not exist here — the promise is what made porting it urgent.
#      Change the rule there first, then here.
# FAIL_POSTURE: closed — unparseable input denies.
# UPDATED: 2026-08-13 (ported; the donor's REDIRECT cited a private incident record that does not
#      ship, so it now points at this repo's own INSTALL.md, which already carries the rule)
# ─────────────────────────────────────────────────────────────────────────────
# guard_gws_logout.sh — PreToolUse hook (matcher: Bash)

INPUT=$(cat)
COMMAND=$(printf '%s' "$INPUT" | python3 -c "
import sys, json
try:
    print((json.load(sys.stdin).get('tool_input') or {}).get('command', '') or '')
except Exception:
    sys.exit(1)
") || { printf '%s\n' '{"decision":"block","reason":"BLOCKED: guard_gws_logout could not read the hook input, so it is failing closed. It protects an action with no undo, and an unreadable command must never be treated the same as a harmless one."}' >&2; exit 2; }

# Match `gws auth logout`, bare or via a full path, tolerant of whitespace.
#
# ⛔⛔ THE BOUNDARIES ARE THE WHOLE GUARD, AND THE DONOR'S VERSION HAD A WORKING BYPASS.
# It ended the match with `([[:space:]]|$)` — whitespace or end-of-string. A shell separator is
# NEITHER, so every one of these walked straight past it, MEASURED 2026-08-13:
#     gws auth logout;echo done      → ALLOWED
#     gws auth logout&&echo done     → ALLOWED
#     gws auth logout|tee /tmp/x     → ALLOWED
#     echo x; gws auth logout; echo y → ALLOWED
# ⇒ The boundary is now "not a word character" on BOTH sides, which admits `;` `&` `|` `)` and
# quotes while still refusing to match inside a longer word (`mygws`, `logouts`).
#
# ⚠ THE TRADE-OFF, STATED RATHER THAN DISCOVERED LATER: this now also fires on a command that
# merely MENTIONS the phrase inside a quoted string, e.g. `echo "never run gws auth logout"`.
# That is a knowing choice, not an oversight. Normally the house rule is the opposite — match the
# action, never the bare keyword, because a guard that fires on correct work gets routed around.
# It is inverted HERE because the protected action has NO UNDO: the cost of a false positive is
# one confused echo and a deny message that explains itself; the cost of a false negative is every
# window's credentials, gone, with a browser sit-down to recover. Fail toward blocking.
if printf '%s' "$COMMAND" | grep -qE '(^|[^[:alnum:]_-])gws[[:space:]]+auth[[:space:]]+logout([^[:alnum:]_-]|$)'; then
  printf '%s\n' '{"decision":"block","reason":"BLOCKED: `gws auth logout` destroys ALL Google credentials and the token cache for EVERY window at once, and there is no undo. WHY: it broke auth system-wide once already, and a permissions rule cannot stop it because --dangerously-skip-permissions bypasses those — this hook is the only real backstop. REDIRECT: if you hit a stale-token 403, do NOT log out. Tell the PERSON to run `gws auth logout` and `gws auth login --full` themselves; re-authenticating is a browser sit-down and is their deliberate call, never an agent'"'"'s. RULE: INSTALL.md, the paragraph on never logging out or moving ~/.config/gws/."}' >&2
  exit 2
fi
exit 0

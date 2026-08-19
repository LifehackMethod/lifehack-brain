#!/usr/bin/env bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: The durable status-line HUD (system/statusline.sh, pointed to by settings.json
#      statusLine) must not be silently repointed or replaced — the user requires it locked
#      "no matter what happens." Write/Edit to settings.json is already blocked by
#      guard_write_paths.sh; this closes the remaining Bash / statusline-setup-agent side door.
# GUARDS: Blocks a Bash command that (a) writes the statusLine pointer INTO settings.json
#         (sed -i / redirect / tee targeting settings.json, with statusLine mentioned),
#         (b) deletes/moves/overwrites/re-symlinks system/statusline.sh or ~/.claude/statusline.sh,
#         or (c) invokes the built-in statusline-setup. Merely MENTIONING the tokens (a grep, a cat,
#         a commit message) is NOT blocked, and edits to the script CONTENT via the Edit tool are
#         unaffected — this guard only matches the Bash tool and only real write-to-target patterns.
# REDIRECT: To change the bar legitimately, edit system/statusline.sh via the Edit tool, or change
#           the pointer in .claude/settings.json with sign-off.
# SIGNPOST: Rule lives in system/hook-contract.md; change the guard there + get sign-off.
# FAIL_POSTURE: degrade-safe — runs on EVERY Bash call with a narrow scope; on a parse error it
#           ALLOWS (a blanket deny-all-Bash on a transient glitch is worse than the narrow, low-harm
#           risk it guards, which guard_write_paths.sh already backstops at the Write/Edit layer).
# UPDATED: 2026-07-23 (ported 2026-08-13 from claudeops-config — the deny message named
#      `system/reference/settings.json`, SOURCE's own settings path, now `.claude/settings.json`
#      to match this repo's actual path; it also cited a SOURCE-only plan filename
#      (~/.claude/plans/rosy-swimming-bonbon.md) with no equivalent here, dropped rather than
#      left dangling — the rule itself is unchanged, only the two dead citations were fixed)
# ─────────────────────────────────────────────────────────────────────────────
INPUT=$(cat)
COMMAND=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    print(json.load(sys.stdin).get('tool_input', {}).get('command', ''))
except Exception:
    print('')
" 2>/dev/null)
[ -z "$COMMAND" ] && exit 0   # degrade-safe: nothing to inspect

deny() {
  printf '%s\n' '{"decision":"block","reason":"BLOCKED: attempt to repoint/replace the status-line. WHY: the durable HUD (system/statusline.sh via the settings pointer) is locked per the user. REDIRECT: edit system/statusline.sh via the Edit tool, or change the pointer in .claude/settings.json with sign-off. RULE: system/hook-contract.md."}' >&2
  exit 2
}

# (a) write the pointer INTO settings.json (real write-to-target, not a mere mention).
#     The sed branch is matched DELIMITER-AGNOSTICALLY: any `sed -i` whose command line also
#     names settings.json is blocked, whatever delimiter its s/// uses. The old single-regex form
#     (sed -i followed by a [^|;&] run up to settings.json) let an s-command that used | as its
#     delimiter slip straight through — a real bypass the conformance lab caught (fixed 2026-07-23).
if echo "$COMMAND" | grep -q 'statusLine'; then
  if echo "$COMMAND" | grep -qE '\bsed\b.*-i' && echo "$COMMAND" | grep -qE 'settings\.json'; then deny; fi
  if echo "$COMMAND" | grep -qE '(>>?|tee)[^|;&]*settings\.json'; then deny; fi
fi
# (b) destroy / move / overwrite / re-symlink the statusline script (excludes *.bak via trailing class)
if echo "$COMMAND" | grep -qE '(>|>>|\btee\b|\brm\b|\bmv\b|\btruncate\b|ln -s)[^&|;]*statusline\.sh($|[[:space:]"])'; then deny; fi
# (c) invoke the built-in statusline setup
if echo "$COMMAND" | grep -qE 'statusline-setup'; then deny; fi
exit 0

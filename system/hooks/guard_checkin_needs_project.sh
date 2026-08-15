#!/usr/bin/env bash
# guard_checkin_needs_project.sh — PreToolUse(Skill, if="Skill(checkin)") + UserPromptExpansion(checkin)
#
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: `.claude/skills/checkin/SKILL.md` is a whole-file load the moment /checkin is invoked — a gate
#      written INSIDE the skill runs after that cost is already paid. /checkin compares PLAN vs BRIEF
#      vs SESSION; with no project armed there is neither, so there is nothing to compare. The original
#      guard (2026-08-14, ported from claudeops-config commit ee53133) registered ONLY a
#      PreToolUse(matcher="Skill") leg, which covers just the natural-language path — Claude deciding
#      to call the Skill tool. Per the official Claude Code hooks reference
#      (https://code.claude.com/docs/en/hooks, fetched live this session): "a PreToolUse hook matching
#      the Skill tool fires only when Claude calls the tool, but typing /skillname directly bypasses
#      PreToolUse. UserPromptExpansion fires on that direct path." /checkin's own trigger list leads
#      with the literal "/checkin", so the MOST COMMON invocation never fired this guard at all.
#      FIXED 2026-08-14 by adding the missing leg below.
# GUARDS: skill name `checkin`, on BOTH paths, and ONLY when no project is armed:
#      (a) the typed path — UserPromptExpansion, registered with matcher="checkin" (that event
#          matches on the `command_name` input field per the docs above).
#      (b) the model-invoked path — PreToolUse, matcher="Skill", narrowed with the handler-level `if`
#          field to `if: "Skill(checkin)"`. Confirmed exact-match syntax at
#          https://code.claude.com/docs/en/skills ("Permission syntax: Skill(name) for exact match,
#          Skill(name *) for prefix match with any arguments") — fetched live this session.
#      A session WITH a project armed is unaffected on either path.
# REDIRECT: arm a project first (`pm_flag.sh arm <brief> <slug> <desk>`), or just don't run /checkin —
#      it is an end-of-session auditor for project work, not an opener.
# SIGNPOST: `.claude/skills/checkin/SKILL.md` (what it does once armed) · `system/hooks/pm_flag.sh`
#      (the arm/status verbs this guard reads) · `system/hook-contract.md` (house deny format: stderr
#      text + exit 2, deliberately NOT hookSpecificOutput/permissionDecision — see DENY SHAPE below for
#      why that still matches the current docs on both events this hook now covers).
# UPDATED: 2026-08-14 — added the UserPromptExpansion leg; narrowed the PreToolUse leg via the
#      documented `if` field instead of hand-parsing an undocumented tool_input field name (there is no
#      published tool_input schema for the Skill tool — see FIRE-LOG below).
# ─────────────────────────────────────────────────────────────────────────────
#
# ONE SCRIPT, branching on `hook_event_name`, not two. Reasoning: both legs share the identical "is a
# project armed" check (pm_flag.sh status) and the identical deny shape (exit 2 + stderr) — only the
# INPUT field that carries the invoked command differs (`tool_input.*` for PreToolUse's Skill call vs
# `command_name` for UserPromptExpansion). Splitting that into two files would duplicate the armed-check
# and the deny message and give two places to drift out of sync with pm_flag.sh. One file, one branch.
#
# DENY SHAPE: exit 2 + deny text on stderr, for BOTH events — no JSON needed on either leg. Confirmed
# against the live docs (https://code.claude.com/docs/en/hooks, fetched this session):
#   - PreToolUse: "A hook that blocks by exiting 2 routes the same way as 'deny': Claude sees the
#     stderr message as the denial reason." (The other valid PreToolUse form is nested
#     hookSpecificOutput.permissionDecision — top-level decision/reason is DEPRECATED for this event —
#     but exit-2+stderr is documented as fully equivalent to "deny", and it's what the rest of this
#     repo's guard fleet already uses; see system/hook-contract.md, which deliberately avoids
#     hookSpecificOutput.)
#   - UserPromptExpansion: "A hook that blocks by exiting 2 routes the same way as reason: the block
#     message shows the stderr text to the user." Same mechanism as PreToolUse's exit-2 path.
# So one exit-2-plus-stderr deny() serves both events with no per-event JSON-shape branch required —
# EVENT is branched on only to parse the right input field, not to change the output shape.
set -uo pipefail
INPUT="$(cat 2>/dev/null)"

# Resolve THIS repo's root from the hook's own location — never a hardcoded home directory.
_HOOKDIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
_REPO="$(cd "$_HOOKDIR" 2>/dev/null && git rev-parse --show-toplevel 2>/dev/null)"
[ -n "$_REPO" ] || _REPO="${_HOOKDIR%/system/hooks}"

# ── fire-log: unconditional, first thing, before any logic ──────────────────────────────────────
# Proves BOTH matchers are actually live — this project has a measured history of hooks that reported
# success for months while capturing nothing (system/sops/hook-sop.md, "DO NOT BUILD" section: a
# marker/logger that silently captured zero real entries despite hundreds of daily calls). It also
# empirically reveals the real tool_input shape the Skill tool sends on PreToolUse, which the current
# hooks reference does NOT document anywhere — this closes that gap for free the first time either leg
# fires for real, instead of guessing a field name in the parsing logic below. Appends (never
# overwrites) so a run of test cases, or a session's worth of real invocations, accumulates evidence.
FIRELOG="${LIFEHACK_HOOK_FIRELOG:-$HOME/.claude/run/checkin-guard-firelog.jsonl}"
mkdir -p "$(dirname "$FIRELOG")" 2>/dev/null
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo unknown)"
printf '%s\t%s\n' "$TS" "$INPUT" >> "$FIRELOG" 2>/dev/null || true

deny() {
  cat <<MSG >&2
BLOCKED: /checkin with NO PROJECT ARMED.

WHY: /checkin compares PLAN vs BRIEF vs SESSION. With no project armed there is no plan and no
brief, so there is nothing to compare -- and invoking it loads the whole skill file to reach that
conclusion. The file loads on invocation, so a check inside the skill cannot save it. This is the
gate. (Path: $1)

REDIRECT: if you meant to work on a project, arm it first --
  bash system/hooks/pm_flag.sh arm "<abs brief>" "<slug>" "<desk>"
then run /checkin. If you did not, you do not need /checkin: it is an end-of-session auditor for
project work, not a session opener.

RULE: system/hook-contract.md (deny format) + system/hooks/pm_flag.sh (armed check). Ported from
claudeops-config 2026-08-14; extended 2026-08-14 to also cover the typed /checkin path, which the
first version of this guard missed entirely (see LLM CONTEXT above).
MSG
  exit 2
}

# armed? pm_flag prints a doc path when armed, the literal string 'none' when not.
is_armed() {
  STATUS="$(bash "$_REPO/system/hooks/pm_flag.sh" status 2>/dev/null | head -1)"
  case "$STATUS" in
    ""|none|none*|*"no project"*) return 1 ;;   # not armed
    *) return 0 ;;                               # armed
  esac
}

EVENT="$(printf '%s' "$INPUT" | python3 -c "
import json,sys
try: d=json.load(sys.stdin)
except Exception: print(''); raise SystemExit
print(str(d.get('hook_event_name') or '').strip())
" 2>/dev/null)"

case "$EVENT" in
  UserPromptExpansion)
    # Typed /checkin path. Docs: 'In addition to the common input fields, UserPromptExpansion hooks
    # receive expansion_type, command_name, command_args, command_source, and the original prompt
    # string.' This leg is registered in settings.json with matcher="checkin" (UserPromptExpansion
    # matches on command_name), so only /checkin reaches this script here at all -- re-check anyway so
    # the logic is self-contained if the registration ever changes.
    CMD_NAME="$(printf '%s' "$INPUT" | python3 -c "
import json,sys
try: d=json.load(sys.stdin)
except Exception: print(''); raise SystemExit
print(str(d.get('command_name') or '').strip().lower())
" 2>/dev/null)"
    [ "$CMD_NAME" = "checkin" ] || exit 0
    is_armed && exit 0
    deny "UserPromptExpansion (typed /checkin)"
    ;;
  PreToolUse)
    # Model-invoked path. settings.json narrows this leg to Skill(checkin) via the handler-level `if`
    # field (code.claude.com/docs/en/skills: "Skill(name) for exact match"), so by the time this
    # script runs on the PreToolUse leg it has ALREADY been filtered to the checkin skill only. There
    # is no documented tool_input schema for the Skill tool to double-check against here -- guessing a
    # field name (the previous version of this guard tried 'skill' and 'name') is exactly what the
    # fire-log above exists to make unnecessary. Fall straight through to the armed check.
    is_armed && exit 0
    deny "PreToolUse (Skill: checkin, via natural language)"
    ;;
  *)
    # Empty, unparsed, or an event this guard doesn't know about. Fail CLOSED, not open
    # (system/sops/hook-sop.md §3 rule 2: a BLOCK hook that cannot parse its input must deny, never
    # allow-on-error) -- rather than assume which schema applies. This should not happen given the
    # matchers configured in settings.json; if it does, the fire-log line above has the raw input.
    is_armed && exit 0
    deny "unrecognized/unparsed hook_event_name ('$EVENT') -- failing closed"
    ;;
esac

#!/usr/bin/env bash
# LHB fire-journal (B4.1): observes only; never alters this hook's decision/exit/stdout/stderr.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)/lib/journal.sh" 2>/dev/null || lhb_journal_fire() { :; }
trap 'lhb_journal_fire "$?" "group_dispatch_pilot-map-ups.sh" "UserPromptSubmit" "" 2>/dev/null || true' EXIT
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: B5.2 (enforcement-layer Phase 2 plan, PHASE B5 "the map pilot"). The pilot
#      skill group (read / checkin / save / project-manager) had 4 separate
#      always-firing UserPromptSubmit registrations — announce_plan_write.sh,
#      pm_persist.sh, save_routing_hint.sh, skill_anchor_inject.sh — each its own
#      process, each independently `cat`-ing the identical stdin JSON on every
#      single turn of every session, for a group the register now declares as
#      ONE unit (`group: "pilot-map-ups"`, schema v1). This file is the ONE
#      load path the register's generator (`system/register/generate.py`,
#      `collapse_group_rows()`) points the group's single wiring entry at.
# GUARDS: nothing — this is an INJECT dispatcher (hook-sop §2: plain stdout +
#      exit 0, never blocks). Each member keeps running its OWN real body,
#      completely unmodified in content, inside its OWN subshell: sourcing a
#      member only DEFINES its functions (its top-level body is now wrapped in
#      a `run()` function it never auto-calls when sourced), so nothing a
#      member does — including its own `exit N` — can escape that one
#      subshell, reach another member, or reach this dispatcher's own exit
#      code. One member crashing, hanging on a bad read, or exiting non-zero
#      can never suppress the other three members' stdout.
# REDIRECT: N/A (non-blocking, never fails the turn). To add/remove a member,
#      edit MEMBERS below AND the corresponding rows' `group` field in
#      system/register/register.jsonl (only `UserPromptSubmit`/`SessionStart`/
#      `Notification` rows may ever carry a non-null `group` — schema v1 hard-
#      rejects it on any event that can block a tool call), then regenerate
#      the two real wiring files via `generate.py` — never hand-edit
#      `.claude/settings.json` / `hooks/hooks.json` directly.
# SIGNPOST: the grouping rule lives in `system/register/schema_v1.py`
#      (`GROUPABLE_HOOK_EVENTS`), `system/register/generate.py`
#      (`collapse_group_rows`), and `system/register/schema-v1.md`'s `group`
#      section. Design + Verify recipe: session scratchpad `B5.2-design.md`;
#      the plan is `_ClaudeOps/plans/enforcement-layer.phase-2.plan.md`
#      PHASE B5, Feature B5.2. Change the RULE there first, this file only
#      executes it.
# FAIL_POSTURE: degrade-safe per member, structurally — a member's failure is
#      isolated to its own subshell and can never block the turn or suppress
#      a sibling's output; this dispatcher itself always exits 0.
# UPDATED: 2026-09-15 (new — B5.2)
# ─────────────────────────────────────────────────────────────────────────────
# THIS FILE IS NOT ITS OWN REGISTER ROW (deliberately): it is a normal,
# hand-authored, committed hook script like any other under system/hooks/ —
# never written to disk by the generator — but its WIRING ENTRY is entirely
# synthetic, produced by generate.py's collapse_group_rows() from the 4
# member rows that share group="pilot-map-ups". Giving this file its own
# "hook" register row too would double-emit its own command. See
# system/register/omission-exemptions.txt for the stated reason it is exempt
# from the omission check instead.
set +e

_HOOKDIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"

# Members, in the SAME order the register's own sort_key (event, matcher,
# path, args) places them today — alphabetical by path — so the concatenated
# stdout matches the pre-B5.2 array order byte-for-byte (B5.2 Verify (3)).
MEMBERS=(
  "announce_plan_write.sh"
  "pm_persist.sh"
  "save_routing_hint.sh"
  "skill_anchor_inject.sh"
)

# Read stdin ONCE. Every member still does its OWN `cat` inside its own run()
# — unmodified — so from each member's point of view stdin looks exactly as
# it always did; this dispatcher just re-feeds the same captured bytes to
# each of them in turn via a pipe.
INPUT="$(cat 2>/dev/null)"

for _member in "${MEMBERS[@]}"; do
  # Each member: sourced (defines its functions + sets ITS OWN fire-journal
  # trap on THIS subshell — never the dispatcher's own shell) then `run` is
  # called explicitly. The subshell created by the pipe is the isolation
  # boundary: a member's `exit N` (its normal, unmodified behavior) ends only
  # that subshell; its own EXIT trap still fires there, writing its own
  # fire-journal line, unaffected by this loop. `|| true` is a second,
  # independent belt on top of `set +e` (mirrors lib/journal.sh's own
  # paranoia) so nothing here can ever make this dispatcher exit non-zero.
  printf '%s' "$INPUT" | { . "$_HOOKDIR/$_member"; run; }
done

exit 0

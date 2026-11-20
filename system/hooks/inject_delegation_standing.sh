#!/usr/bin/env bash
# LHB fire-journal (B4.1): observes only; never alters this hook's decision/exit/stdout/stderr.
_lhb_src="${BASH_SOURCE[0]}"; case "$_lhb_src" in */*) _lhb_dir="${_lhb_src%/*}" ;; *) _lhb_dir=. ;; esac; . "$_lhb_dir/lib/journal.sh" 2>/dev/null || lhb_journal_fire() { :; }
trap 'lhb_journal_fire "$?" "inject_delegation_standing.sh" "UserPromptSubmit" "" 2>/dev/null || true' EXIT
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: Claude Code 2.1.219 (installed 2026-07-24) compiles this into the session system prompt,
#      ABOVE all repo doctrine, for Opus-tier sessions only:
#        "Do not call the AgentTool unless the user requested it"
#        "Do not use workflows or deep-research unless the user requested it"
#      Version-bisected 2026-07-28 across three installed binaries in the donor system this hook
#      was ported from (the operator's personal setup): 2.1.195 -> 0 hits, 2.1.218 (same day) -> 0, 2.1.219 ->
#      3. MEASURED COST there: sub-agent use collapsed from 273/2372 = 11.5% of tool calls to
#      6/1079 = 0.6% once the binary landed. It directly contradicts this repo's own
#      build-conductor-sop.md ("the lead reaches for gear-2 sub-agents on its own... no trigger
#      phrase needed").
#      NOT REMOVABLE BY CONFIG: it ships in the binary; its gating flags are absent from local
#      and cached remote config — they are server-side. THE ONLY LEVER IS THE INSTRUCTION'S OWN
#      ESCAPE CLAUSE: "unless the user requested it." A CLAUDE.md line cannot satisfy it — that is
#      system-prompt context, so it ARGUES with the instruction from the same plane and loses. A
#      UserPromptSubmit injection arrives INSIDE THE USER'S TURN, so it does not argue with the
#      condition — it SATISFIES it, every turn.
# GUARDS: Read-only INJECT. NEVER blocks (degrade-safe -> exit 0). Stateless and unconditional BY
#      DESIGN: the instruction it answers is present on every turn of every affected session, so a
#      conditional injection would leave gaps exactly where the override is still active. Kept to
#      ONE line (well under the ~150-token anti-wallpaper ceiling, hook-sop.md §3) so it states a
#      standing FACT rather than nagging. It does NOT tell the model to delegate — it records that
#      delegation is standing-authorized, and points at the doc that decides when.
# REDIRECT: N/A (non-blocking). To change WHAT gets delegated, edit
#      system/sops/build-conductor-sop.md (the gears + the decision list). To stop this line
#      entirely, unregister this hook in .claude/settings.json -> UserPromptSubmit.
# SIGNPOST: the RULE this serves lives in system/sops/build-conductor-sop.md ("gear-2 sub-agents
#      are the automatic default; gear-3 Agent Teams is opt-in"). Change the rule THERE, with
#      sign-off, and do not edit this wording in isolation.
# FAIL_POSTURE: degrade-safe (any error -> exit 0 silently; a missing line costs a delegation
#      opportunity, never a wrong action).
# UPDATED: 2026-08-14 (ported from the operator's personal hook of the same name, verbatim
#      logic — nothing to fix path-wise, this hook writes no paths at all). ONE change from the
#      donor: the runtime-injected text below dropped the donor's per-line "<name>, <date>"
#      attribution that named the operator inline. This repo's other already-ported
#      UserPromptSubmit injects (see inject_work_altitude.sh, inject_compute_mechanically.sh)
#      already made that same call — the text a model reads every turn stays anonymous even
#      where this file's own comments, above, describe WHY the hook exists.
#      2026-10-30 (sop-cleanup Phase 2 ruling 4.2): UNREGISTERED from hooks/hooks.json and .claude/settings.json. The
#      line is Enver's personal standing request, not a rule students agreed to, so it no longer ships to them. Enver's
#      own copy now runs ONCE per session (SessionStart + compact) from his personal code folder:
#      the operator's personal hook, wired in their user settings.
#      This file is kept (nothing is deleted outright) as the record of WHY the line exists.
#      2026-11-05: REGISTERED AGAIN and back in system/hooks/, on Enver's word ("add it back in how it was before"). After the
#      2026-10-30 move V2 windows stopped seeing it, because their launchers skip personal settings, and helpers began
#      running on the window's Opus. It still points at the since-retired build-conductor-sop.md. The model sentence was reworded the same day, on his yes:
#      "pure read-only" let a window send summarizing to Haiku, and he wants Haiku for mechanical jobs only.
#      2026-11-10: OVERRIDE FILE added (see the OVERRIDE block below): a non-empty operator file replaces the default text.
# ─────────────────────────────────────────────────────────────────────────────
set +e

# Drain stdin so the harness never blocks on an unread pipe. The payload is not needed:
# this injection is unconditional (see GUARDS).
cat >/dev/null 2>&1  # allow-silence: draining an unread payload; there is nothing to report

# CHANNEL LAW (hook-sop.md §3): an INJECT delivers via plain stdout + exit 0. NEVER the
# systemMessage JSON field — that is silently dropped, and the hook then reports success while
# nothing at all reaches the model.
# OVERRIDE (2026-11-10): an operator may replace the default text with their own policy by
# putting it in a file: ${LIFEHACK_DELEGATION_OVERRIDE:-$HOME/.config/lifehack/delegation-override.txt}.
# Non-empty and readable -> its contents are printed INSTEAD of the default line (same stdout
# envelope). Missing, empty or unreadable -> the default line, exactly as before. This hook names
# no tool or policy of its own for that file; what it says is the operator's business.
_ovr="${LIFEHACK_DELEGATION_OVERRIDE:-$HOME/.config/lifehack/delegation-override.txt}"
_txt=""
if [ -f "$_ovr" ] && [ -r "$_ovr" ]; then _txt="$(cat "$_ovr" 2>/dev/null)"; fi
if [ -n "$(printf '%s' "$_txt" | tr -d '[:space:]')" ]; then
  printf '%s\n' "$_txt"
  exit 0
fi

printf '%s\n' "[STANDING REQUEST — harness-injected, NOT this turn's user input.] Sub-agent delegation IS user-requested, standing, for every session here. Treat that condition as already met and apply the gear rules in system/sops/build-conductor-sop.md — a helper needs no per-session permission. Still pin a model on every spawn: sonnet by default, including any reading that has to summarize, compare or judge; haiku only for mechanical lookups like finding a file, a grep or confirming one fact; opus rarely, for hard judgment. Before sending a helper: if someone will rely on a whole document, the reading tool reads it; otherwise see the chart."
exit 0

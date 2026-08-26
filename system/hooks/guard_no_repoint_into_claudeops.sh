#!/bin/bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: this project's design is that every skill/hook symlink under ~/.claude/skills/ and
#      ~/.claude/agents/ resolves FROM the installed plugin at
#      ~/.claude/plugins/cache/lifehack-brain/, NEVER from this private checkout
#      (~/.claude/skills/ClaudeOps). The live system has been found the exact INVERSE of that
#      design at least twice: a 2026-08-24 08:28 incident re-pointed 34 symlinks at this repo
#      directly, and it recurred again on 2026-08-25. Both times the repo got that way because a
#      real, locally-sound repair (a missing skill, a stale plugin cache, "just fix it now") ended
#      by running `ln -sf` at a path inside this repo instead of fixing the plugin install. Four
#      separate repairs did this on four separate occasions for four separate locally-sound
#      reasons. This hook is the thing that would have stopped every one of them at the moment the
#      symlink was about to be written.
# GUARDS: a Bash `ln -s`/`ln -sf` (anywhere in the command text, including inside a for-loop body,
#      so a scripted re-point of many symlinks at once is caught the same as a single one) whose
#      LINK argument sits under ~/.claude/skills/ or ~/.claude/agents/ and whose TARGET argument
#      resolves into this private repo -- while a plugin-supplied equivalent exists at
#      ~/.claude/plugins/cache/lifehack-brain/*/*/.claude/{skills,agents}/<name>. Also covers a
#      Write/Edit to any settings.json whose new content registers a hook "command" pointing at a
#      script inside this private repo under the same equivalence condition.
# REDIRECT: fix the PLUGIN install, never the symlink. If a skill/hook is missing or stale, the
#      correct repair is `claude plugin update lifehack-brain` (or reinstalling the plugin) so the
#      plugin cache carries the right content -- then the existing ~/.claude/skills/<name> symlink,
#      which should point at the plugin cache, works again on its own. Re-pointing the symlink at
#      this repo "just to get unblocked" is exactly the move this hook exists to catch.
# SIGNPOST: the canonical statement of "repo is machinery, plugin cache is what the harness
#      resolves from" lives in this repo's own CLAUDE.md ("The shape of the thing") and in
#      INSTALL.md. The closing move for the standing inversion this guard defends against is
#      tracked as R7 / D4-HUMAN in the operator's own migration plan (outside this repo --
#      ~/.claude/plans/lifehack-migration.plan.md, task checkbox "R7 -- Verify the 34
#      plugin-supplied skills actually resolve FROM THE PLUGIN" -- confirmed present 2026-08-26,
#      still open/unticked as of that check) / see `system/tools/citation_lint.py:137` for the one
#      in-repo citation of the D4-HUMAN gate, which the sibling guard
#      `system/hooks/guard_harness_writeback.sh` is itself waiting on). To change what this hook
#      enforces, change the design decision there first -- never weaken this guard to get one
#      re-point through.
# FAIL_POSTURE: closed. Unreadable stdin, a JSON parse failure, an unparseable tool_input, or a
#      genuinely ambiguous ln/settings.json match (e.g. a loop-driven symlink whose basename can't
#      be narrowed, so the plugin-equivalent check can't be made precisely) all DENY. Never
#      allow-on-error, never allow-on-ambiguity.
# UPDATED: 2026-08-25 (DRAFT -- promote block, not yet registered; see the .md this ships beside)
# ─────────────────────────────────────────────────────────────────────────────
# guard_no_repoint_into_claudeops.sh — PreToolUse hook (matcher: Bash|Write|Edit)
#
# Exit codes:
#   0  ALLOW  -- reviewed and not a re-point into this private repo.
#   2  BLOCK  -- either a real match, or ANY condition this guard could not cleanly resolve.
#      (No third "cannot-determine" code here, unlike guard_harness_writeback.sh's sibling
#      design -- this hook's own spec calls for fail-closed to collapse straight to deny, not a
#      separate signal a caller might mishandle as non-blocking.)

_HOOKDIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
INPUT=$(cat)

VERDICT=$(printf '%s' "$INPUT" | python3 "$_HOOKDIR/guard_no_repoint_into_claudeops.py" 2>/tmp/guard_no_repoint_into_claudeops.stderr)
PYRC=$?

# The .py never exits non-zero on its own (see its own top-level try/except) -- but if python3
# itself is unavailable, crashes before printing, or prints something unparseable, that is exactly
# the kind of ambiguity this hook's FAIL_POSTURE says to deny, not wave through.
case "$VERDICT" in
  ALLOW::*)
    exit 0
    ;;
  BLOCK::*)
    REASON="${VERDICT#BLOCK::}"
    DENY="{\"decision\":\"block\",\"reason\":\"BLOCKED: this would re-point a skill/hook symlink (or a settings.json hook command) at this private repo instead of the plugin install. WHY: ${REASON}. This is the exact pattern behind the 2026-08-24 08:28 incident (34 symlinks re-pointed at this repo) and its 2026-08-25 recurrence -- four separate locally-sound repairs each did this once. REDIRECT: fix the PLUGIN, not the symlink -- update/reinstall the lifehack-brain plugin so its cache carries the right content, then the existing ~/.claude/skills symlink resolves correctly on its own. RULE: this repo's CLAUDE.md ('The shape of the thing') + INSTALL.md; the closing move for the standing inversion is tracked as R7 / D4-HUMAN in the operator's migration plan -- ~/.claude/plans/lifehack-migration.plan.md, task checkbox R7 (Verify the 34 plugin-supplied skills resolve FROM THE PLUGIN), open/unticked as of 2026-08-26 -- and D4-HUMAN (see system/tools/citation_lint.py:137 for the one in-repo D4-HUMAN citation). Do not weaken this guard to get one re-point through -- change the design decision at its source instead.\"}"
    printf '%s\n' "$DENY" >&2
    exit 2
    ;;
  *)
    printf '%s\n' "{\"decision\":\"block\",\"reason\":\"BLOCKED: guard_no_repoint_into_claudeops could not produce a clean verdict (python rc=${PYRC}, output=${VERDICT}). WHY: an unparseable/absent verdict is exactly the ambiguity this hook's FAIL_POSTURE (closed) requires it to deny, never allow. REDIRECT: retry; if this persists, python3 or the guard script itself is broken -- fix that before assuming the underlying action is safe. RULE: this hook's own header, FAIL_POSTURE line.\"}" >&2
    exit 2
    ;;
esac

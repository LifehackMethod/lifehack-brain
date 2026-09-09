#!/bin/bash
#
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: measured on a live plugin install 2026-09-09 — the Harness shipped a 213-line standing
#      brief (CLAUDE.md at this repo's root) that NO SESSION EVER SAW. Claude Code auto-loads
#      CLAUDE.md from the folder you opened, its ancestors, and ~/.claude/ — a plugin's own
#      CLAUDE.md is in none of those places, and `.claude-plugin/plugin.json` has no key that
#      delivers one (it declares `skills` and `agents`, nothing else). So every plugin user was
#      running the Harness without the document that explains how to run the Harness. A private
#      predecessor of this hook existed on the maintainer's machine only, pointed at a hardcoded
#      repo path, and went silently dark the day that path was deleted — which is how the gap was
#      finally noticed.
# GUARDS: nothing. This hook BLOCKS no tool call and CANNOT — it is a SessionStart informational
#      emitter (stdout + exit 0), the SessionStart analogue of an INJECT. Recorded explicitly so
#      no reader mistakes it for enforcement: if the brief must be ENFORCED, that is a different
#      hook and a different kind.
# REDIRECT: n/a — nothing is refused, so there is nowhere to send anyone. If the brief is WRONG,
#      edit CLAUDE.md at this repo's root; if it fails to appear, check ${CLAUDE_PLUGIN_ROOT} is
#      set (it is only set for plugin-registered hooks) and that the session was RESTARTED after
#      the registration landed.
# SIGNPOST: the brief itself is CLAUDE.md at this repo's root — ⛔ never paste its content here,
#      one source and never a copy. The rule for hooks is system/sops/hook-sop.md + the mechanics
#      in system/hook-contract.md; to change WHETHER this is delivered, edit the registration in
#      hooks/hooks.json and get the maintainer's sign-off.
# FAIL_POSTURE: open, deliberately. Every failure path exits 0 silently — no plugin root, no
#      brief, unreadable file. This hook informs; a session that cannot be briefed must still run.
#      ⛔ Do NOT "harden" this to fail closed: a broken brief would then block every session.
# ⚠ ON §3's ANTI-WALLPAPER RULE (inject text ≤ ~150 tokens): that rule governs UserPromptSubmit
#      hooks, which fire EVERY TURN and become wallpaper by repetition. This fires ONCE per
#      session, which is the same budget `session_context_loader.sh` already spends there. The
#      exemption is stated rather than assumed — ⛔ if this is ever moved to UserPromptSubmit,
#      the ceiling applies and this file must shrink or move back.
# UPDATED: 2026-09-09
# ─────────────────────────────────────────────────────────────────────────────

set +e
cat >/dev/null 2>&1   # drain stdin per the hook contract

# ${CLAUDE_PLUGIN_ROOT} is set by Claude Code for plugin-registered hooks and always resolves to
# the CURRENTLY installed version. That is why this hook cannot go stale across plugin updates,
# and why the brief must be found through it rather than through any written-down path — a
# written path is exactly what killed the predecessor.
ROOT="${CLAUDE_PLUGIN_ROOT:-}"
[ -n "$ROOT" ] || exit 0
SRC="$ROOT/CLAUDE.md"
[ -r "$SRC" ] || exit 0

# Is the same brief ALREADY auto-loaded here? Walk up from the working directory and compare by
# CONTENT, never by folder name. A project with its own unrelated CLAUDE.md still gets the Harness
# brief; only a byte-identical copy suppresses it. ⛔ The predecessor guessed by path and was
# wrong in both directions — it stayed silent in folders it should have spoken in, and had no way
# to notice its source had vanished.
d="$(pwd -P 2>/dev/null)" || exit 0
while [ -n "$d" ] && [ "$d" != "/" ]; do
  if [ -r "$d/CLAUDE.md" ] && cmp -s "$d/CLAUDE.md" "$SRC"; then exit 0; fi
  d="$(dirname "$d")"
done

printf '=== Lifehack Harness — standing brief (delivered by the plugin; not auto-loaded here) ===\n\n'
cat "$SRC"
exit 0

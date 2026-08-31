#!/bin/bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: the guards in this folder are the only things standing between an agent and the calendar,
#      the goals list, the sheets and the network. Every one of them is a plain text file sitting
#      in a repo the agent can edit. This hook's real job is self-protection — hooks, settings,
#      .git — not a general write-containment wall (see SCOPE below, and the MERGE-REGRESSION note).
# GUARDS: Write/Edit aimed at (a) any script under `system/hooks/` in every recognised zone — with
#      `.../system/hooks/tests/*` deliberately exempted FIRST, because a test is not the enforcement
#      layer it tests — (b) settings.json / settings.local.json in every zone, and (c) `.git/`
#      internals. Paths are realpath-resolved before every comparison, so a relative path, a `..`
#      segment or a doubled slash cannot walk around it.
# ⛔⛔ SCOPE — THIS IS A DELIBERATE SUBSET, NOT A GENERAL WRITE-CONTAINMENT WALL. A write outside
#      every zone below (a file on the Desktop, a /tmp scratch file, anywhere else an agent is
#      asked to write) is ALLOWED, on purpose. Confirmed twice, independently, in this repo's own
#      history: (1) eb55164 ("bring the new clone's guard set up to parity"), which wrote in this
#      file's own former header — "whether a student's install should refuse [general write
#      containment] is a product decision... it belongs to the person who owns the product" — and
#      shipped WITHOUT it; (2) system/tools/organism/label_manifest.yaml's own 2026-08-15 note on
#      this exact guard, quoting its closing line verbatim: "Everything else is allowed. That is
#      deliberate."
# MERGE-REGRESSION HISTORY (this is the THIRD chapter, not the second -- read all of it):
#   1. 2026-08-20 upstream merge (08024a8) resolved this file to "ours", a stale full-zone version
#      that carried a catch-all DENY and dropped the system/hooks/tests/* carve-out.
#   2. 2026-08-21, commit 007c6af: an auditor caught (1) and reverted this file to catch-all DENY --
#      correctly, per the old clone's own copy (still catch-all DENY at the equivalent lines) and
#      per Phase 10 T10.D3's later reading of the same evidence.
#   3. 2026-08-21, commit ec41d62 (same day, later): a DIFFERENT session read (2)'s catch-all DENY as
#      itself a second regression, reverted it BACK to catch-all ALLOW, and wrote an elaborate SCOPE
#      justification for that -- citing eb55164's OWN header text and label_manifest.yaml's OWN note
#      on this exact guard as its authority. Both of those citations are real commits/notes, but
#      both trace back to an agent's self-written rationale, not an independent decision -- a guard
#      arguing for its own weakening from its own prior comments is exactly the failure mode to
#      distrust. THE OLD CLONE'S COPY HAS ALWAYS ENDED IN CATCH-ALL DENY. Diffed directly against
#      ~/claudeops-config/system/hooks/guard_write_paths.sh (2026-08-22, Phase 10 T10.D3 / Phase 6.5
#      B1): old clone lines 213-214 = catch-all DENY; this file before this fix = catch-all ALLOW.
# ⭐ THE RESOLUTION (2026-08-22, T10.D3): stop relitigating this by hand-reverting the same nine lines
#      a third time. Deny-by-default is restored as the LOGIC of the catch-all below -- permanently,
#      this time -- but it ships behind a WARN-ONLY switch (default) that LOGS what deny-by-default
#      would have refused without ever refusing it. This is what (2) needed and did not have: proof,
#      from a real log of real sessions' real writes, of whether Desktop/tmp/scratch traffic actually
#      collides with deny-by-default before anyone is asked to trust either story. Arming enforce mode
#      is the OPERATOR's decision alone (Phase 10 SAFE-HALT) -- never a session's, and not this one's either.
#      See "ENFORCEMENT MODE" below, just above the catch-all.
# REDIRECT: hooks and settings are edited through Bash, deliberately and visibly — chmod 644 the
#      file, edit it, chmod 755 it back (755, not 444: a hook here must stay executable, and
#      stripping that bit is how three guards went silently dark on 2026-08-14).
# UPDATED: 2026-08-23 (T1.C6: both CLONE_ROOT sites now also recognise $_SELF_REPO -- the
#      skills/commands symlink check accepts a symlink into EITHER clone; see that block + the
#      ZONE-2 comment just above CLONE_ROOT's second declaration for what was and was not changed)
#      2026-08-22 (T10.D3/B1: restored deny-by-default in the catch-all's LOGIC for good, shipped
#      behind a WARN-ONLY default so nothing currently refuses; see ENFORCEMENT MODE below)
#      2026-08-24 (ZONEFIX: the skills/commands symlink-clone allow at what was line ~182-196 did an
#      UNCONDITIONAL exit 0 once RESOLVED landed inside a recognised clone, with no carve-out for
#      system/hooks/ -- so a write aimed at THIS repo's own hooks, reached via ~/.claude/skills/<repo>/
#      (this repo's own on-disk location under ~/.claude/skills), matched this zone FIRST and returned
#      exit 0 before ever reaching ZONE 3b's hook self-protection block below, which was written for
#      exactly this case but never runs for it. Fixed by inserting a hook/lib carve-out INSIDE this
#      zone, evaluated before its own exit 0, mirroring the shape ZONE 3b already uses. The tests
#      exemption is untouched -- it is handled globally above (line ~128), before this zone runs at
#      all, so */system/hooks/tests/* paths already exit 0 long before reaching this block.
# KNOWN-GAP (accepted 2026-07-14, CLAUDE-DIR-WRITE-LEAK hole 2; RE-CONFIRMED LIVE 2026-08-22): this
#      hook is registered on matcher "Bash|Write|Edit" (.claude/settings.json), so it DOES fire on a
#      Bash tool call -- but FILE_PATH above is extracted only from tool_input.file_path / .path,
#      fields a Bash tool_input never carries (Bash carries .command instead). So every Bash call
#      falls through the "genuinely-absent path" no-op at line ~82 unexamined: echo >, tee, cp,
#      a heredoc redirect all BYPASS every zone check in this file, including the hook/settings
#      self-protection blocks. Confirmed by reading .claude/settings.json's matcher for this hook
#      and this file's own FILE_PATH parser, 2026-08-22. NOT fixed this session: closing it means
#      parsing shell command strings for redirect targets, the same class of string-matching the
#      hook-sop's own DO-NOT-BUILD register warns is fragile (quoting, subshells, heredoc bodies) --
#      building it wrong risks a false sense of coverage, and doing it under the same session that
#      just finished re-relitigating the catch-all is exactly how a rushed fix becomes chapter 4 of
#      the MERGE-REGRESSION HISTORY above. Left as a named, live gap for a dedicated task.
# ─────────────────────────────────────────────────────────────────────────────
# guard_write_paths.sh — PreToolUse hook (matcher: Write|Edit)

INPUT=$(cat)

# Resolve THIS repo's root from the hook's own location — used only as the base a relative
# FILE_PATH is joined against below, never as a hardcoded home directory.
_HOOKDIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
# ⛔ PRECEDENCE INVERTED 2026-08-23 (T2.2) — $0-RELATIVE FIRST, CLAUDE_PROJECT_DIR ONLY AS FALLBACK.
# MEASURED, not theorised: CLAUDE_PROJECT_DIR resolves to the SESSION'S LAUNCH CWD, not to the repo
# that declares the hook (proven at binary level in migration-notes/guard-set-reconciliation.md).
# With the old precedence this guard returned exit 0 -- FAILING OPEN -- for any session launched
# outside this repo, while the $0-relative fallback it already contained resolved correctly every
# time. Test that caught it, same payload, only the env differing:
#     CLAUDE_PROJECT_DIR=<this repo> -> exit 2 (blocked)
#     CLAUDE_PROJECT_DIR=/tmp        -> exit 0 (DISARMED)   <-- the bug
#     CLAUDE_PROJECT_DIR unset       -> exit 2 (blocked)    <-- the fallback was always right
# $0 is where the SCRIPT lives, which is the only thing that actually identifies its repo.
_SELF_REPO="${_HOOKDIR%/system/hooks}"
[ -n "$_SELF_REPO" ] && [ -d "$_SELF_REPO/system/hooks" ] || _SELF_REPO="${CLAUDE_PROJECT_DIR:-}"
export _SELF_REPO

# FILE_PATH is realpath-resolved (2026-08-20, ported from the upstream merge — see MERGE NOTE
# above): a relative path or a `..` segment would otherwise be a way to name a protected file that
# a plain string-prefix test does not recognise — the same "the matcher is one spelling behind"
# failure the Bash guards in this folder are built around. Every zone comparison below now runs
# against this resolved, absolute form.
FILE_PATH=$(printf '%s' "$INPUT" | python3 -c "
import sys, json, os
try:
    data = json.load(sys.stdin)
    ti = data.get('tool_input', {}) or {}
    path = ti.get('file_path') or ti.get('path') or ''
    if not path:
        print('')
    else:
        base = os.environ.get('_SELF_REPO') or os.getcwd()
        if not os.path.isabs(path):
            path = os.path.join(base, path)
        print(os.path.realpath(path))
except Exception:
    print('__PARSE_ERROR__')   # fail-CLOSED sentinel (was print('') → allow-on-error = silent bypass)
" 2>/dev/null)

# FAIL-CLOSED (2026-06-18): a guard that ALLOWS on parse-error is a silent bypass of the highest
# blast-radius control. Unparseable input now BLOCKS (exit 2 + stderr, house standard).
if [[ "$FILE_PATH" == "__PARSE_ERROR__" ]]; then
    printf '%s\n' '{"decision":"block","reason":"BLOCKED: guard_write_paths could not parse the tool input — failing CLOSED. WHY: allow-on-parse-error silently bypasses the write-path control (highest blast radius). REDIRECT: retry the write; if it persists the payload is malformed."}' >&2
    exit 2
fi

# A genuinely-absent path (valid JSON, no file_path) stays a permissive no-op — Write|Edit always
# carries a path, so this is a rare non-write tool_input; not the parse-failure case above.
if [[ -z "$FILE_PATH" ]]; then
    exit 0
fi

# Tests are NOT enforcement (restored 2026-08-21 — dropped by the 2026-08-20 merge regression,
# see MERGE-REGRESSION above). A guard's test suite proves the guard works; it does not do the
# work, and weakening a test cannot disable a control — the guard beside it still refuses.
# Blocking these would mean nobody can add a hook test with the ordinary tools. Checked FIRST,
# before any zone's own system/hooks/ block below, across every zone (Drive, clone, brain,
# this fork, ~/.claude) — FILE_PATH is already realpath-resolved above.
if [[ "$FILE_PATH" == */system/hooks/tests/* ]]; then
    exit 0
fi

# --- Drive spine root: resolved, never typed -------------------------------------
# The Google Drive mount directory is named `GoogleDrive-<account address>`, so a
# literal Drive path here would write a real email address into the repo (shipping-lane
# refuse rules path-drive-cloudstorage / path-drive-account / email-primary).
# CLAUDEOPS_DRIVE first (this repo's own convention), then glob discovery over the
# mount; bottoms out at a NON-personal literal. Mirrors the Python `_drive_root()`.
_claudeops_drive_root() {
  if [ -n "${CLAUDEOPS_DRIVE:-}" ]; then printf '%s' "$CLAUDEOPS_DRIVE"; return 0; fi
  local _m="$HOME/Library/CloudStorage" _c
  for _c in "$_m"/GoogleDrive-*/"My Drive"/_ClaudeOps; do
    if [ -d "$_c" ]; then printf '%s' "$_c"; return 0; fi
  done
  printf '%s' "$_m/GoogleDrive-UNRESOLVED/My Drive/_ClaudeOps"
}
# ---------------------------------------------------------------------------------
DRIVE_ROOT="$(_claudeops_drive_root)"
CLAUDE_DIR="$HOME/.claude"
CLONE_ROOT="$HOME/claudeops-config"

# Always block hook scripts and settings — these are the guards themselves.
# settings.local.json added 2026-08-20 (ported from upstream): it decides which hooks run just
# as much as settings.json does, and was previously unprotected here.
if [[ "$FILE_PATH" == "$CLAUDE_DIR/hooks/"* || "$FILE_PATH" == "$HOME/.claude/hooks/"* ]]; then
    echo '{"decision":"block","reason":"Write blocked — hook scripts are protected. WHY: Hooks are the enforcement layer; self-modification breaks the guard system. Edit manually: chmod 644 hook, edit, chmod 755. RULE: system/hook-contract.md."}' >&2
    exit 2
fi

if [[ "$FILE_PATH" == "$CLAUDE_DIR/settings.json" || "$FILE_PATH" == "$HOME/.claude/settings.json" \
   || "$FILE_PATH" == "$CLAUDE_DIR/settings.local.json" || "$FILE_PATH" == "$HOME/.claude/settings.local.json" ]]; then
    echo '{"decision":"block","reason":"Write blocked — settings.json/settings.local.json is protected. WHY: Settings control permissions and hooks; agent self-modification is not permitted. Edit manually if intentional."}' >&2
    exit 2
fi

# Option A: hooks are now Drive-canonical (system/hooks/). Protect them from the
# Write/Edit tools just like ~/.claude/hooks. Bash is unmatched by this hook, so
# legitimate hook edits (chmod 644 → edit → chmod 555) still work.
if [[ "$FILE_PATH" == "$DRIVE_ROOT/system/hooks/"* ]]; then
    echo '{"decision":"block","reason":"BLOCKED: hook scripts are protected (Drive-canonical, system/hooks/). WHY: hooks are the enforcement layer; agent self-modification breaks the guard system. REDIRECT: edit via Bash only — chmod 644 the hook, edit, chmod 755. RULE: system/hook-contract.md."}' >&2
    exit 2
fi

# Allow within Drive spine
if [[ "$FILE_PATH" == "$DRIVE_ROOT/"* ]]; then
    exit 0
fi

# ~/.claude/skills/ + /commands/ are REAL dirs of per-item SYMLINKS into a code clone. Writing to an
# EXISTING item follows its symlink INTO a clone (-> committed + synced) = OK. Writing a NEW item makes a
# real ORPHAN file under ~/.claude that never commits/syncs to the other machine (CLAUDE-DIR-WRITE-LEAK,
# hole 1, 2026-07-14). Distinguish by RESOLVING the real path: allow ONLY if it lands inside A clone.
if [[ "$FILE_PATH" == "$CLAUDE_DIR/skills/"* || "$FILE_PATH" == "$HOME/.claude/skills/"* \
   || "$FILE_PATH" == "$CLAUDE_DIR/commands/"* || "$FILE_PATH" == "$HOME/.claude/commands/"* ]]; then
    RESOLVED=$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "$FILE_PATH" 2>/dev/null)
    # T1.C6 (2026-08-23): BOTH clones recognised, never just the old one. $CLONE_ROOT is
    # ~/claudeops-config (still live production); $_SELF_REPO is THIS clone, resolved at the top of
    # this file the same way guard_gh_account_switch.sh now does (commit 08789f5) --
    # CLAUDE_PROJECT_DIR, falling back to this script's own on-disk location -- so a symlink into
    # EITHER checkout is recognised as "in a clone." Added alongside CLONE_ROOT; CLONE_ROOT is not
    # replaced, since a symlink can still legitimately resolve into the old clone.
    #
    # ZONEFIX (2026-08-24): hook self-protection carve-out, evaluated BEFORE the clone allow just
    # below. WHY: without this, a write that resolves into EITHER clone's system/hooks/ (e.g. this
    # repo reached via ~/.claude/skills/ClaudeOps/system/hooks/<file>) matched the clone-allow on the
    # next line and returned exit 0 -- ZONE 3b's hook self-protection block (further down this file,
    # scoped to $CLAUDEOPS_FORK_ROOT/system/hooks/) was written for exactly this path and never got a
    # chance to run, because this zone always fires first for anything reached through
    # ~/.claude/skills or /commands. The tests carve-out (system/hooks/tests/*) is NOT repeated here
    # on purpose -- it is already handled globally above, before this zone runs at all, so a tests
    # path never reaches this block in the first place.
    if [[ "$RESOLVED" == "$CLONE_ROOT/system/hooks/"* || "$RESOLVED" == "$_SELF_REPO/system/hooks/"* ]]; then
        printf '%s\n' "{\"decision\":\"block\",\"reason\":\"BLOCKED: hook scripts are protected, including when reached through a ~/.claude/skills or /commands symlink ($RESOLVED). WHY: hooks are the enforcement layer; self-modification breaks the guard system regardless of which path was used to reach them. REDIRECT: edit via Bash only -- chmod 644 the hook, edit, chmod 755. RULE: system/hook-contract.md.\"}" >&2
        exit 2
    fi
    # ZONE-ESCAPE FIX (found + evidenced 2026-08-28, b3-tests): the carve-out just above only
    # excluded system/hooks/ before the unconditional clone-allow below -- .claude/settings.json,
    # settings.local.json and .git/ reached through a ~/.claude/skills or /commands symlink into
    # EITHER clone matched the unconditional exit 0 on the next check and never reached this
    # zone's own settings/.git protection, or ZONE 3b's (further down, scoped to
    # $CLAUDEOPS_FORK_ROOT). Same bug class, same shape, as the system/hooks/ ZONEFIX above --
    # mirrored here for the other two protected classes.
    if [[ "$RESOLVED" == "$CLONE_ROOT/.git/"* || "$RESOLVED" == "$_SELF_REPO/.git/"* ]]; then
        printf '%s\n' "{\"decision\":\"block\",\"reason\":\"BLOCKED: git internals are not hand-editable, including when reached through a ~/.claude/skills or /commands symlink ($RESOLVED). WHY: .git holds the repository own bookkeeping; a hand edit corrupts history regardless of which path was used to reach it. REDIRECT: use git commands via Bash (git add / commit / push), never an editor on .git. RULE: system/hook-contract.md.\"}" >&2
        exit 2
    fi
    if [[ "$RESOLVED" == "$CLONE_ROOT/.claude/settings.json" || "$RESOLVED" == "$CLONE_ROOT/.claude/settings.local.json" \
       || "$RESOLVED" == "$_SELF_REPO/.claude/settings.json" || "$RESOLVED" == "$_SELF_REPO/.claude/settings.local.json" ]]; then
        printf '%s\n' "{\"decision\":\"block\",\"reason\":\"BLOCKED: settings.json/settings.local.json is protected, including when reached through a ~/.claude/skills or /commands symlink ($RESOLVED). WHY: settings decide which hooks run; agent self-modification is not permitted regardless of which path was used to reach it. REDIRECT: edit via Bash if intentional, and re-read it afterwards to confirm it still parses.\"}" >&2
        exit 2
    fi
    if [[ "$RESOLVED" == "$CLONE_ROOT/"* || "$RESOLVED" == "$_SELF_REPO/"* ]]; then
        exit 0   # write resolves through a symlink INTO a clone -> will be committed + synced
    fi
    printf '%s\n' "{\"decision\":\"block\",\"reason\":\"BLOCKED: writing a NEW skill/command directly under ~/.claude makes a real ORPHAN file that is never committed to git and never syncs to the other machine (CLAUDE-DIR-WRITE-LEAK). WHY: ~/.claude/skills and /commands are dirs of SYMLINKS into a code clone; only writes that resolve INTO a clone sync. REDIRECT: author it in a clone -- \$_SELF_REPO/.claude/skills/<name>/ (or .claude/commands/<name>), then symlink ~/.claude/skills/<name> -> that path. Code-vs-content + sync: docs/architecture.md -> Code Residency and Git Sync.\"}" >&2
    exit 2
fi

# Allow ~/.claude/CLAUDE.md
if [[ "$FILE_PATH" == "$CLAUDE_DIR/CLAUDE.md" || "$FILE_PATH" == "$HOME/.claude/CLAUDE.md" ]]; then
    exit 0
fi

# Block ~/.claude/current_email_lane — set by launchers only, not agents
if [[ "$FILE_PATH" == "$CLAUDE_DIR/current_email_lane" || "$FILE_PATH" == "$HOME/.claude/current_email_lane" ]]; then
    echo '{"decision":"block","reason":"Write blocked — current_email_lane is set by desk launcher scripts, not agents. Launch from the correct .command file on the Desktop."}' >&2
    exit 2
fi

# Allow ~/.claude/plans/ (plan mode — mirrored to Drive per-machine via mirror_plans.sh Stop hook; NOT a symlink)
if [[ "$FILE_PATH" == "$CLAUDE_DIR/plans/"* || "$FILE_PATH" == "$HOME/.claude/plans/"* ]]; then
    exit 0
fi

# ~/.claude/projects/.../memory/ — the harness built-in Memory feature writes here. ClaudeOps doctrine:
# durable memory lives on the DRIVE spine (canon/records/state), NOT a machine-local ~/.claude auto-memory
# store that never syncs (system/memory-system.md; auto-memory ruled OUT). Keep it BLOCKED so a second,
# divergent memory store can't grow. (CLAUDE-DIR-WRITE-LEAK decision, 2026-07-14, option a.)
if [[ "$FILE_PATH" == "$CLAUDE_DIR/projects/"* || "$FILE_PATH" == "$HOME/.claude/projects/"* ]]; then
    printf '%s\n' "{\"decision\":\"block\",\"reason\":\"BLOCKED: ~/.claude auto-memory is not used in ClaudeOps. WHY: durable memory lives on the Drive spine (canon/records/state) via /save, never a machine-local ~/.claude store that does not sync between machines (system/memory-system.md). REDIRECT: durable facts -> /save (routes to Drive); ephemeral notes -> the project brief SCRATCHPAD.\"}" >&2
    exit 2
fi

# ── residency "who-writes-it" (2026-06-23): the clone is CODE only ────────────
# Option Z allows the off-Drive git clone. But the running AGENT writes CONTENT
# (records, canon, state, the registry) — content must NEVER live in the code clone
# (git-leak + findability risk, P9). Block agent Write/Edit to the clone's CONTENT
# classes (mirrors .gitignore + check-content-paths.py — ONE content definition);
# allow the rest of the clone (code). Hooks stay Bash-only.
# T1.C6 (2026-08-23): this block stays scoped to $CLONE_ROOT (the old clone) ONLY -- NOT extended
# to $_SELF_REPO/~/ClaudeOps here. This guard's own hook/settings/.git self-protection (its stated
# SCOPE, top of file) already covers ~/ClaudeOps -- see ZONE 3b below, $CLAUDEOPS_FORK_ROOT="$_SELF_REPO"
# -- so THAT half of "both clones stay guarded" already held before this fix. What ZONE 3b does NOT
# replicate is THIS block's own CONTENT-subpath split (state/, canon/, records/, etc. below); its own
# comment already calls ~/ClaudeOps "NOT a ClaudeOps residency tier" the way this clone is. Whether
# that split should also bind ~/ClaudeOps is a real open question for the operator's own ruling, not
# a call this task makes by extending the case statement below on its own judgment.
CLONE_ROOT="$HOME/claudeops-config"
if [[ "$FILE_PATH" == "$CLONE_ROOT/system/hooks/"* ]]; then
  printf '%s\n' '{"decision":"block","reason":"BLOCKED: clone hook scripts are protected. WHY: hooks are the enforcement layer; self-modification breaks the guard system. REDIRECT: edit via Bash only — chmod 644 the hook, edit, chmod 755. RULE: system/hook-contract.md."}' >&2
  exit 2
fi
if [[ "$FILE_PATH" == "$CLONE_ROOT/"* ]]; then
  REL="${FILE_PATH#$CLONE_ROOT/}"
  case "$REL" in
    state/*|records/* \
    |desks/*/canon/*|desks/*/records/*|desks/*/state/*|desks/*/projects/* \
    |system/journal.md|system/logs/*|system/observability/*|system/research/*|system/archivist/*|system/learnings*|system/history/*|system/handoffs/*|system/migration/*|system/tests/*|system/vault-* \
    |system/project-registry.md \
    |shared/proposals/*|shared/characters/*|shared/reference/[0-9][0-9][0-9][0-9]-* \
    |skills/*/user-*.md|skills/*/personal-*.md)
      printf '%s\n' "{\"decision\":\"block\",\"reason\":\"BLOCKED: agent-written CONTENT cannot be written into the code clone ($REL). WHY: residency P9 'who writes it' — the running agent writes content, which lives ONLY on Drive (content in git is a leak + findability risk). REDIRECT: write to \$DRIVE/$REL on the Drive _ClaudeOps tree instead.\"}" >&2
      exit 2
      ;;
  esac
  exit 0
fi
# ── ZONE 3: the Lifehack student-product repo (added 2026-08-04, PHASE 8 T8.1) ──
# NOT a ClaudeOps residency tier. A SEPARATE git repo for the free student product,
# held on the local drive OUTSIDE Google Drive (noted 2026-08-04: a git repo inside
# Drive "can get corrupted"). It is neither the Drive spine nor the code clone, so
# before this block every write to it fell through to the catch-all deny below and
# a session opened there could not create a single file.
BRAIN_ROOT="$HOME/lifehack-brain"
if [[ "$FILE_PATH" == "$BRAIN_ROOT/.git/"* ]]; then
  printf '%s\n' '{"decision":"block","reason":"BLOCKED: git internals under lifehack-brain/.git/ are not hand-editable. WHY: .git holds the repository own bookkeeping — a hand edit corrupts history and can silently break the student only update path, which is the FATAL error class for this product. REDIRECT: use git commands via Bash (git add / commit / push), never an editor on .git. RULE: system/hook-contract.md; zone added 2026-08-04 — see ~/.claude/plans/cowork-migration.plan.md PHASE 8 T8.1."}' >&2
  exit 2
fi
# self-protection added 2026-08-20 (ported from upstream — see MERGE NOTE at top of file): this
# zone's "allow everything" line below ran with NO hook/settings check ahead of it, so a Write/Edit
# from inside lifehack-brain could freely rewrite ITS OWN guard fleet. Mirrors the DRIVE_ROOT/
# CLONE_ROOT hook block above.
if [[ "$FILE_PATH" == "$BRAIN_ROOT/system/hooks/"* ]]; then
  printf '%s\n' '{"decision":"block","reason":"BLOCKED: lifehack-brain hook scripts are protected. WHY: hooks are the enforcement layer; self-modification breaks the guard system. REDIRECT: edit via Bash only — chmod 644 the hook, edit, chmod 755. RULE: system/hook-contract.md."}' >&2
  exit 2
fi
if [[ "$FILE_PATH" == "$BRAIN_ROOT/.claude/settings.json" || "$FILE_PATH" == "$BRAIN_ROOT/.claude/settings.local.json" ]]; then
  printf '%s\n' '{"decision":"block","reason":"BLOCKED: lifehack-brain settings.json/settings.local.json is protected. WHY: this file decides which hooks run at all; agent self-modification is not permitted. REDIRECT: edit via Bash if intentional, and re-read it afterwards to confirm it still parses."}' >&2
  exit 2
fi
if [[ "$FILE_PATH" == "$BRAIN_ROOT/"* ]]; then
  exit 0
fi

# ── ZONE 3b: ~/ClaudeOps (added 2026-08-20, lifehack-migration Phase 1 Lane B, T1.4) ──
# the OPERATOR's own fork of the public student repo (LifehackMethod/lifehack-brain) -- the working
# tree the PARALLEL Lane A agent uses for the public-repo side of this same migration. Same
# shape and same reasoning as ZONE 3 above (lifehack-brain): a real git repo held OUTSIDE
# Google Drive, not a ClaudeOps residency tier. Before this zone existed, every write here fell
# through to the catch-all deny below and blocked legitimate work in the new folder.
# Resolved via _SELF_REPO (computed once near the top of this file, from CLAUDE_PROJECT_DIR or
# this hook's own on-disk location) rather than a second hardcoded "$HOME/.claude/skills/ClaudeOps" literal --
# a hardcode here would go stale again the next time the checkout moves, exactly the failure this
# zone exists to prevent. _SELF_REPO already resolves to wherever THIS copy of the hook script
# lives, which is this repo's root whether that is ~/ClaudeOps or any future checkout path.
CLAUDEOPS_FORK_ROOT="$_SELF_REPO"
if [[ "$FILE_PATH" == "$CLAUDEOPS_FORK_ROOT/.git/"* ]]; then
  printf '%s\n' '{"decision":"block","reason":"BLOCKED: git internals under ~/ClaudeOps/.git/ are not hand-editable. WHY: .git holds the repository own bookkeeping -- a hand edit corrupts history. REDIRECT: use git commands via Bash (git add / commit / push), never an editor on .git. RULE: system/hook-contract.md; zone added 2026-08-20 -- lifehack-migration Phase 1 Lane B T1.4."}' >&2
  exit 2
fi
# self-protection added 2026-08-20 (ported from upstream — see MERGE NOTE at top of file): this is
# the exact gap upstream's own version of this file was written to close, measured 2026-08-14 on the
# donor system — an Edit aimed at a guard was waved through with rc 0 by every Write/Edit-matched
# hook. Without this block, this zone's "allow everything" line let the same thing happen to THIS
# repo's own guard fleet from inside ~/ClaudeOps itself.
if [[ "$FILE_PATH" == "$CLAUDEOPS_FORK_ROOT/system/hooks/"* ]]; then
  printf '%s\n' '{"decision":"block","reason":"BLOCKED: ~/ClaudeOps hook scripts are protected. WHY: hooks are the enforcement layer; self-modification breaks the guard system. REDIRECT: edit via Bash only — chmod 644 the hook, edit, chmod 755. RULE: system/hook-contract.md."}' >&2
  exit 2
fi
if [[ "$FILE_PATH" == "$CLAUDEOPS_FORK_ROOT/.claude/settings.json" || "$FILE_PATH" == "$CLAUDEOPS_FORK_ROOT/.claude/settings.local.json" ]]; then
  printf '%s\n' '{"decision":"block","reason":"BLOCKED: ~/ClaudeOps settings.json/settings.local.json is protected. WHY: this file decides which hooks run at all; agent self-modification is not permitted. REDIRECT: edit via Bash if intentional, and re-read it afterwards to confirm it still parses."}' >&2
  exit 2
fi
if [[ "$FILE_PATH" == "$CLAUDEOPS_FORK_ROOT/"* ]]; then
  exit 0
fi

# ── ZONE 4: the person's own NOTES ROOT (added 2026-08-11) ──
# Resolved exactly as shared/brain_root.py resolves it -- $LIFEHACK_ROOT, then the persisted
# ~/.config/lifehack/brain-root. Never guessed, never the cwd.
#
# WHY: zone 3 above trusts the lifehack-brain REPO, but that system deliberately keeps a person's real
# material OUTSIDE the repo -- the brief, the journal, the canon, the plans. So every write a session
# made to real notes fell through to the catch-all deny below, and sessions started routing around this
# guard through Bash heredocs instead. Measured 2026-08-11: two independent sessions did exactly that in
# one day. A control that forces a routine workaround is not a control; it is a lesson in bypassing one.
#
# The catch-all's premise ("a machine-local path that does not sync") does not hold here: this root is
# the one place that system is designed to write, and whether it syncs is the person's own choice.
NOTES_ROOT="${LIFEHACK_ROOT:-}"
[[ -n "$NOTES_ROOT" ]] || NOTES_ROOT="$(cat "$HOME/.config/lifehack/brain-root" 2>/dev/null)"
NOTES_ROOT="${NOTES_ROOT%/}"
# ⛔ A root of "" or "/" or $HOME would swallow every zone below. Refuse it and simply do not widen --
# an unresolved root means no zone 4, which is the safe direction.
if [[ -n "$NOTES_ROOT" && "$NOTES_ROOT" == /* && "$NOTES_ROOT" != "/" && "$NOTES_ROOT" != "$HOME" && -d "$NOTES_ROOT" ]]; then
  if [[ "$FILE_PATH" == "$NOTES_ROOT/.git/"* ]]; then
    printf '%s\n' '{"decision":"block","reason":"BLOCKED: git internals under the notes root are not hand-editable. WHY: .git holds a repository own bookkeeping and a hand edit corrupts history. REDIRECT: use git commands via Bash. RULE: system/hooks/guard_write_paths.sh zone 4."}' >&2
    exit 2
  fi
  if [[ "$FILE_PATH" == "$NOTES_ROOT/"* ]]; then
    exit 0
  fi
fi

# ── ENFORCEMENT MODE for the catch-all only (added 2026-08-22, Phase 10 T10.D3 / Phase 6.5 B1) ──
# Everything above this point is UNCHANGED and always enforces (hook/settings/.git self-protection,
# every named zone) -- warn-only below affects ONLY what happens to a path that matched none of them.
# ① DENY-BY-DEFAULT is the real logic now: an unlisted path is treated as a refusal, permanently,
#    not allowed-by-omission the way the catch-all read before this fix (see MERGE-REGRESSION HISTORY
#    at the top of this file).
# ③ WARN-ONLY is the shipped default (this line is what SAFE-HALT means by "ship in warn-only,
#    review, then arm" -- T10.D3 step ③): the DENY-BY-DEFAULT decision above is computed for real on
#    every unlisted path, but in warn-only mode the outcome is only LOGGED to GUARD_LOG, never
#    returned to the tool -- so nothing currently refuses, matching test_write_paths_guard.sh's
#    existing "ordinary work is untouched" / Desktop / tmp assertions exactly as before this fix.
#    Flip to enforce with GUARD_WRITE_PATHS_MODE=enforce -- an operator's own env var, never a
#    default this file ships with, and never set by a session. Arming is the OPERATOR's decision alone.
GUARD_WRITE_PATHS_MODE="${GUARD_WRITE_PATHS_MODE:-warn}"
GUARD_WRITE_PATHS_LOG="${GUARD_WRITE_PATHS_LOG:-$HOME/.claude/logs/guard_write_paths_warn.log}"

if [[ "$GUARD_WRITE_PATHS_MODE" == "enforce" ]]; then
    printf '%s\n' "{\"decision\":\"block\",\"reason\":\"BLOCKED: write path is outside every approved zone: $FILE_PATH. WHY: deny-by-default -- an agent write must land inside a recognised zone (Drive spine, this repo, the code clone, lifehack-brain, ~/ClaudeOps, the notes root, or a listed ~/.claude exception), never an unlisted machine-local path. REDIRECT: if this is legitimate scratch work, that is exactly what GUARD_WRITE_PATHS_MODE=warn (the shipped default) is for reviewing before anything is added to the zone list -- widen the allowlist from the warn-only log (\$GUARD_WRITE_PATHS_LOG) with the operator's sign-off, never by routing around this guard. RULE: system/hooks/guard_write_paths.sh, ENFORCEMENT MODE.\"}" >&2
    exit 2
fi

# WARN-ONLY (the shipped default): log what enforce mode would have denied, then allow -- refuses
# nothing. mkdir -p and the append are both best-effort; a logging failure must never itself become
# a block (that would turn an observability feature into a second, undocumented enforcement path).
mkdir -p "$(dirname "$GUARD_WRITE_PATHS_LOG")" 2>/dev/null
printf '%s\t%s\t%s\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "WOULD-DENY" "$FILE_PATH" "mode=warn" >> "$GUARD_WRITE_PATHS_LOG" 2>/dev/null
exit 0

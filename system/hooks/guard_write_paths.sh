#!/bin/bash
# LHB fire-journal (B4.1): observes only; never alters this hook's decision/exit/stdout/stderr.
_lhb_src="${BASH_SOURCE[0]}"; case "$_lhb_src" in */*) _lhb_dir="${_lhb_src%/*}" ;; *) _lhb_dir=. ;; esac; . "$_lhb_dir/lib/journal.sh" 2>/dev/null || lhb_journal_fire() { :; }
. "$_lhb_dir/lib/roundb.sh" 2>/dev/null || roundb_on() { return 1; }  # Round D post-verdict: skills_native_write switch
trap 'lhb_journal_fire "$?" "guard_write_paths.sh" "PreToolUse" "Write|Edit" 2>/dev/null || true' EXIT
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
#      the donor clone's copy of system/hooks/guard_write_paths.sh (2026-08-22, Phase 10 T10.D3 / Phase 6.5
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
# UPDATED: 2026-09-16 (0R.12-derived fix ported to main: replaced the old clone-root / $_SELF_REPO
#      name-match in the skills/commands zone with the structural _git_repo_root_with_remote()
#      check -- see that block's own comment for why the old nominal test was wrong)
#      2026-08-23 (T1.C6: both old clone-root sites now also recognise $_SELF_REPO -- the
#      skills/commands symlink check accepts a symlink into EITHER clone; see that block + the
#      ZONE 2 comment (code zones) for the split that applies to listed code folders)
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

# --- The person's own folders: read from the two pointers, never typed -------------
# shared/person_roots.py (via lib/person_roots.sh) answers, in one call:
#   LH_NOTES_ROOT     the notes root, exactly as shared/brain_root.py resolves it
#   LH_PERSONAL_ROOT  the personal code folder (shared/personal_code_root.py)
#   LH_CODE_ZONES     extra code folders the person lists in <personal-code>/code-zones.txt
# Empty means "no such zone" (a fresh install), never a guessed folder. The plugin names no folder of
# any particular person, so no person's folder name can go stale here.
LH_NOTES_ROOT=""; LH_PERSONAL_ROOT=""; LH_CODE_ZONES=(); LH_STRICT=1   # strict until the resolver says both pointers are ok
. "$_lhb_dir/lib/person_roots.sh" 2>/dev/null && lh_person_roots
# ---------------------------------------------------------------------------------
CLAUDE_DIR="$HOME/.claude"

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

# ── ZONE 1: the person's own NOTES ROOT ──
# Resolved exactly as shared/brain_root.py resolves it ($LIFEHACK_ROOT, the repo pointer, the persisted
# ~/.config/lifehack/brain-root, ...). Never guessed, never the cwd; an unresolved root means no zone.
# WHY it is allowed: the notes root is the one place this system is designed to write. Before it was a
# zone, every write to real notes fell through to the catch-all, and sessions routed around this guard
# through Bash heredocs instead (measured 2026-08-11: two sessions in one day).
# Hooks kept in the notes root are still protected from the Write/Edit tools, just like ~/.claude/hooks
# (Bash is unmatched by this hook, so a deliberate chmod 644 -> edit -> chmod 755 still works), and so
# are git internals if the notes root is itself a repo.
if [[ -n "$LH_NOTES_ROOT" && "$FILE_PATH" == "$LH_NOTES_ROOT/.git/"* ]]; then
    printf '%s\n' '{"decision":"block","reason":"BLOCKED: git internals under the notes root are not hand-editable. WHY: .git holds a repository own bookkeeping and a hand edit corrupts history. REDIRECT: use git commands via Bash. RULE: system/hooks/guard_write_paths.sh ZONE 1."}' >&2
    exit 2
fi
if [[ -n "$LH_NOTES_ROOT" && "$FILE_PATH" == "$LH_NOTES_ROOT/system/hooks/"* ]]; then
    echo '{"decision":"block","reason":"BLOCKED: hook scripts are protected (notes root, system/hooks/). WHY: hooks are the enforcement layer; agent self-modification breaks the guard system. REDIRECT: edit via Bash only — chmod 644 the hook, edit, chmod 755. RULE: system/hook-contract.md."}' >&2
    exit 2
fi

if [[ -n "$LH_NOTES_ROOT" && "$FILE_PATH" == "$LH_NOTES_ROOT/"* ]]; then
    exit 0
fi

# ~/.claude/skills/ + /commands/ are REAL dirs of per-item entries that MAY be symlinks into a code
# clone, or may just as well be real, ordinary directories -- FALSIFIED 2026-09-10: all 20 live
# skill folders under ~/.claude/skills/ were checked independently and are genuine real directories,
# zero symlinks. The check below used to hardcode "inside a clone" as "resolves under a typed clone root or
# $_SELF_REPO" -- a nominal test that can only ever recognise the specific clones it was told about,
# and goes wrong the moment the arrangement changes (exactly what happened here). The property that
# actually matters is structural, not nominal: does the resolved path land inside a REAL git working
# tree that has at least one remote configured. A repo in that shape commits and syncs through
# ordinary git regardless of whether anything under ~/.claude points at it by symlink or just IS it.
# A path that resolves nowhere such a repo makes a real ORPHAN file under ~/.claude that never
# commits/syncs to the other machine (CLAUDE-DIR-WRITE-LEAK, hole 1, 2026-07-14) -- that harm is
# real and still guarded against below, just by the right test.
#
# _git_repo_root_with_remote(): walks up from the target to the nearest existing ancestor directory
# (the target itself may not exist yet -- a new file about to be created, and `git -C` requires a
# directory that already exists), then asks git directly rather than name-matching a root: prints
# the repo root on stdout and returns 0 only when that directory is inside a git working tree AND
# `git remote` for it returns at least one line; returns 1 (prints nothing) otherwise.
_git_repo_root_with_remote() {
    local d="$1"
    while [[ ! -d "$d" && "$d" != "/" ]]; do
        d="$(dirname "$d")"
    done
    [[ -d "$d" ]] || return 1
    local top
    top="$(git -C "$d" rev-parse --show-toplevel 2>/dev/null)" || return 1
    [[ -n "$top" ]] || return 1
    git -C "$top" remote 2>/dev/null | grep -q . || return 1
    printf '%s' "$top"
}
if [[ "$FILE_PATH" == "$CLAUDE_DIR/skills/"* || "$FILE_PATH" == "$HOME/.claude/skills/"* \
   || "$FILE_PATH" == "$CLAUDE_DIR/commands/"* || "$FILE_PATH" == "$HOME/.claude/commands/"* ]]; then
    RESOLVED=$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "$FILE_PATH" 2>/dev/null)
    # Structural repo check (replaces the old clone-root / $_SELF_REPO name-match, 2026-09-10):
    # REPO_ROOT is the real, remote-having git working tree that RESOLVED lands inside, if any --
    # found by walking up from RESOLVED itself, never by matching a hardcoded path. Both
    # previously-recognised clones (the old clone, $_SELF_REPO) still resolve here, along with any
    # OTHER real, remote-having repo ~/.claude/skills or /commands might point at or contain --
    # this is a generalisation of the old check, not a narrowing of it.
    REPO_ROOT="$(_git_repo_root_with_remote "$RESOLVED")"
    #
    # ZONEFIX (2026-08-24): hook self-protection carve-out, evaluated BEFORE the repo allow just
    # below. WHY: without this, a write that resolves into the repo's system/hooks/ (e.g. this
    # repo reached via ~/.claude/skills/<repo>/system/hooks/<file>) matched the repo-allow on the
    # next line and returned exit 0 -- ZONE 3b's hook self-protection block (further down this file,
    # scoped to $SELF_REPO_ROOT/system/hooks/) was written for exactly this path and never got a
    # chance to run, because this zone always fires first for anything reached through
    # ~/.claude/skills or /commands. The tests carve-out (system/hooks/tests/*) is NOT repeated here
    # on purpose -- it is already handled globally above, before this zone runs at all, so a tests
    # path never reaches this block in the first place.
    if [[ -n "$REPO_ROOT" && "$RESOLVED" == "$REPO_ROOT/system/hooks/"* ]]; then
        printf '%s\n' "{\"decision\":\"block\",\"reason\":\"BLOCKED: hook scripts are protected, including when reached through a ~/.claude/skills or /commands symlink ($RESOLVED). WHY: hooks are the enforcement layer; self-modification breaks the guard system regardless of which path was used to reach them. REDIRECT: edit via Bash only -- chmod 644 the hook, edit, chmod 755. RULE: system/hook-contract.md.\"}" >&2
        exit 2
    fi
    # ZONE-ESCAPE FIX (found + evidenced 2026-08-28, b3-tests): the carve-out just above only
    # excluded system/hooks/ before the unconditional repo-allow below -- .claude/settings.json,
    # settings.local.json and .git/ reached through a ~/.claude/skills or /commands symlink into
    # the repo matched the unconditional exit 0 on the next check and never reached this zone's own
    # settings/.git protection, or ZONE 3b's (further down, scoped to $SELF_REPO_ROOT). Same
    # bug class, same shape, as the system/hooks/ ZONEFIX above -- mirrored here for the other two
    # protected classes.
    if [[ -n "$REPO_ROOT" && "$RESOLVED" == "$REPO_ROOT/.git/"* ]]; then
        printf '%s\n' "{\"decision\":\"block\",\"reason\":\"BLOCKED: git internals are not hand-editable, including when reached through a ~/.claude/skills or /commands symlink ($RESOLVED). WHY: .git holds the repository own bookkeeping; a hand edit corrupts history regardless of which path was used to reach it. REDIRECT: use git commands via Bash (git add / commit / push), never an editor on .git. RULE: system/hook-contract.md.\"}" >&2
        exit 2
    fi
    if [[ -n "$REPO_ROOT" && ( "$RESOLVED" == "$REPO_ROOT/.claude/settings.json" || "$RESOLVED" == "$REPO_ROOT/.claude/settings.local.json" ) ]]; then
        printf '%s\n' "{\"decision\":\"block\",\"reason\":\"BLOCKED: settings.json/settings.local.json is protected, including when reached through a ~/.claude/skills or /commands symlink ($RESOLVED). WHY: settings decide which hooks run; agent self-modification is not permitted regardless of which path was used to reach it. REDIRECT: edit via Bash if intentional, and re-read it afterwards to confirm it still parses.\"}" >&2
        exit 2
    fi
    if [[ -n "$REPO_ROOT" ]]; then
        exit 0   # resolves inside a real git working tree with a configured remote -> will be committed + synced
    fi
    # Round D post-verdict (skills_native_write, P-50): a NEW file of a NEW personal skill under the REAL
    # ~/.claude/skills/ is allowed (Claude loads skills from there). NOT allowed: an existing file, anything
    # inside any git repo (remote or not), commands/. (A symlink out of skills/ resolves outside this zone and never reaches here.)
    if [[ -z "$REPO_ROOT" && "$FILE_PATH" == "$HOME/.claude/skills/"* && ! -e "$RESOLVED" ]] && roundb_on skills_native_write; then
        _sk_anc="$RESOLVED"; while [[ ! -d "$_sk_anc" && "$_sk_anc" != "/" ]]; do _sk_anc="$(dirname "$_sk_anc")"; done
        if ! git -C "$_sk_anc" rev-parse --show-toplevel >/dev/null 2>&1; then
            exit 0
        fi
    fi
    # Later-list item (skill_edit_to_ask, default OFF): an AI edit of an EXISTING file in a NON-git personal skill under the REAL
    # ~/.claude/skills/ is not blocked here; it goes on to build_mode's skill-edit ASK (the harness Yes/No), so it needs skill_edit_ask ON too.
    # Still blocked: anything inside any git repo (remote or not, so the personal code folder and system/hooks), commands/, a path whose
    # resolved location is not inside the real skills folder (escaping symlinks), and NEW files (skills_native_write decides those).
    if [[ -z "$REPO_ROOT" && "$FILE_PATH" == "$HOME/.claude/skills/"* && -f "$RESOLVED" ]] && roundb_on skill_edit_to_ask && roundb_on skill_edit_ask; then
        _sk_real="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "$HOME/.claude/skills" 2>/dev/null)"
        _sk_anc="$(dirname "$RESOLVED")"
        if [[ -n "$_sk_real" && "$RESOLVED" == "$_sk_real/"* && ( -z "$LH_PERSONAL_ROOT" || "$RESOLVED" != "$LH_PERSONAL_ROOT/"* ) ]] \
           && ! git -C "$_sk_anc" rev-parse --show-toplevel >/dev/null 2>&1; then
            exit 0
        fi
    fi
    printf '%s\n' "{\"decision\":\"block\",\"reason\":\"BLOCKED: this path does not resolve inside a git repository with a configured remote ($RESOLVED). WHY: a ~/.claude/skills or /commands entry only syncs when what it points at (or is) is a real git working tree with a remote -- anything else left here becomes a real ORPHAN file that is never committed and never syncs to the other machine (CLAUDE-DIR-WRITE-LEAK). REDIRECT: author it inside a real git repo with a configured remote (e.g. \$_SELF_REPO/.claude/skills/<name>/, or any other cloned repo that has 'git remote' set), then place or symlink ~/.claude/skills/<name> there. Code-vs-content + sync: docs/architecture.md -> Code Residency and Git Sync.\"}" >&2
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

# ~/.claude/projects/.../memory/ — the harness built-in Memory feature writes here. This system's doctrine:
# durable memory lives in the NOTES ROOT (canon/records/state), NOT a machine-local ~/.claude auto-memory
# store that never syncs (system/memory-system.md; auto-memory ruled OUT). Keep it BLOCKED so a second,
# divergent memory store can't grow. (CLAUDE-DIR-WRITE-LEAK decision, 2026-07-14, option a.)
if [[ "$FILE_PATH" == "$CLAUDE_DIR/projects/"* || "$FILE_PATH" == "$HOME/.claude/projects/"* ]]; then
    printf '%s\n' "{\"decision\":\"block\",\"reason\":\"BLOCKED: ~/.claude auto-memory is not used by this system. WHY: durable memory lives in the notes root (canon/records/state) via /save, never a machine-local ~/.claude store that does not sync between machines (system/memory-system.md). REDIRECT: durable facts -> /save (routes to Drive); ephemeral notes -> the project brief SCRATCHPAD.\"}" >&2
    exit 2
fi

# ── ZONE 2: the person's own extra CODE ZONES (residency "who-writes-it", 2026-06-23) ──
# A person may keep code in more git folders than the personal code folder; they list them, one per
# line, in <personal-code>/code-zones.txt (read by shared/person_roots.py; a missing file means none).
# Each listed folder is CODE only: the running AGENT writes CONTENT (records, canon, state, the
# registry), and content must NEVER live in a code clone (git-leak + findability risk, P9). So agent
# Write/Edit to a zone's CONTENT classes is refused (mirrors .gitignore + check-content-paths.py — ONE
# content definition), its hooks stay Bash-only, its .git is not hand-editable, and the rest (code) is allowed.
# The personal code folder itself is NOT given this split here: under ~/.claude/skills it is judged by
# the skills/commands zone above, and anywhere else it keeps the catch-all, exactly as before.
for _zone in "${LH_CODE_ZONES[@]}"; do
  [[ -n "$_zone" ]] || continue
  if [[ "$FILE_PATH" == "$_zone/.git/"* ]]; then
    printf '%s\n' '{"decision":"block","reason":"BLOCKED: git internals in a code zone are not hand-editable. WHY: .git holds the repository own bookkeeping and a hand edit corrupts history. REDIRECT: use git commands via Bash. RULE: system/hooks/guard_write_paths.sh ZONE 2."}' >&2
    exit 2
  fi
  if [[ "$FILE_PATH" == "$_zone/system/hooks/"* ]]; then
    printf '%s\n' '{"decision":"block","reason":"BLOCKED: clone hook scripts are protected. WHY: hooks are the enforcement layer; self-modification breaks the guard system. REDIRECT: edit via Bash only — chmod 644 the hook, edit, chmod 755. RULE: system/hook-contract.md."}' >&2
    exit 2
  fi
  if [[ "$FILE_PATH" == "$_zone/"* ]]; then
    REL="${FILE_PATH#"$_zone"/}"
    case "$REL" in
      state/*|records/* \
      |desks/*/canon/*|desks/*/records/*|desks/*/state/*|desks/*/projects/* \
      |system/journal.md|system/logs/*|system/observability/*|system/research/*|system/archivist/*|system/learnings*|system/history/*|system/handoffs/*|system/migration/*|system/tests/*|system/vault-* \
      |system/project-registry.md \
      |shared/proposals/*|shared/characters/*|shared/reference/[0-9][0-9][0-9][0-9]-* \
      |skills/*/user-*.md|skills/*/personal-*.md)
        printf '%s\n' "{\"decision\":\"block\",\"reason\":\"BLOCKED: agent-written CONTENT cannot be written into the code clone ($REL). WHY: residency P9 'who writes it' — the running agent writes content, which lives ONLY in the notes root (content in git is a leak + findability risk). REDIRECT: write it under your notes root instead (python3 shared/brain_root.py prints where that is).\"}" >&2
        exit 2
        ;;
    esac
    exit 0
  fi
done

# ── ZONE 3: the Lifehack student-product repo (added 2026-08-04, PHASE 8 T8.1) ──
# NOT a notes residency tier. A SEPARATE git repo for the free student product,
# held on the local drive OUTSIDE Google Drive (noted 2026-08-04: a git repo inside
# Drive "can get corrupted"). It is neither the notes root nor a code zone, so
# before this block every write to it fell through to the catch-all deny below and
# a session opened there could not create a single file.
BRAIN_ROOT="$HOME/lifehack-brain"
if [[ "$FILE_PATH" == "$BRAIN_ROOT/.git/"* ]]; then
  printf '%s\n' '{"decision":"block","reason":"BLOCKED: git internals under lifehack-brain/.git/ are not hand-editable. WHY: .git holds the repository own bookkeeping — a hand edit corrupts history and can silently break the student only update path, which is the FATAL error class for this product. REDIRECT: use git commands via Bash (git add / commit / push), never an editor on .git. RULE: system/hook-contract.md; zone added 2026-08-04 — see ~/.claude/plans/cowork-migration.plan.md PHASE 8 T8.1."}' >&2
  exit 2
fi
# self-protection added 2026-08-20 (ported from upstream — see MERGE NOTE at top of file): this
# zone's "allow everything" line below ran with NO hook/settings check ahead of it, so a Write/Edit
# from inside lifehack-brain could freely rewrite ITS OWN guard fleet. Mirrors the notes-root /
# code-zone hook blocks above.
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

# ── ZONE 3b: THIS repo (the checkout this copy of the hook lives in) ──
# Resolved via _SELF_REPO (computed once near the top of this file from this hook's own on-disk
# location, CLAUDE_PROJECT_DIR as the fallback) rather than any typed folder, so it follows the
# checkout wherever it moves. A real git repo held outside the notes root; before this zone existed,
# every write here fell through to the catch-all and blocked legitimate work in the repo.
SELF_REPO_ROOT="$_SELF_REPO"
if [[ "$FILE_PATH" == "$SELF_REPO_ROOT/.git/"* ]]; then
  printf '%s\n' '{"decision":"block","reason":"BLOCKED: git internals under this repo .git/ are not hand-editable. WHY: .git holds the repository own bookkeeping -- a hand edit corrupts history. REDIRECT: use git commands via Bash (git add / commit / push), never an editor on .git. RULE: system/hook-contract.md; zone added 2026-08-20 -- lifehack-migration Phase 1 Lane B T1.4."}' >&2
  exit 2
fi
# self-protection added 2026-08-20 (ported from upstream — see MERGE NOTE at top of file): this is
# the exact gap upstream's own version of this file was written to close, measured 2026-08-14 on the
# donor system — an Edit aimed at a guard was waved through with rc 0 by every Write/Edit-matched
# hook. Without this block, this zone's "allow everything" line let the same thing happen to THIS
# repo's own guard fleet from inside the repo itself.
if [[ "$FILE_PATH" == "$SELF_REPO_ROOT/system/hooks/"* ]]; then
  printf '%s\n' '{"decision":"block","reason":"BLOCKED: this repo hook scripts are protected. WHY: hooks are the enforcement layer; self-modification breaks the guard system. REDIRECT: edit via Bash only — chmod 644 the hook, edit, chmod 755. RULE: system/hook-contract.md."}' >&2
  exit 2
fi
if [[ "$FILE_PATH" == "$SELF_REPO_ROOT/.claude/settings.json" || "$FILE_PATH" == "$SELF_REPO_ROOT/.claude/settings.local.json" ]]; then
  printf '%s\n' '{"decision":"block","reason":"BLOCKED: this repo settings.json/settings.local.json is protected. WHY: this file decides which hooks run at all; agent self-modification is not permitted. REDIRECT: edit via Bash if intentional, and re-read it afterwards to confirm it still parses."}' >&2
  exit 2
fi
if [[ "$FILE_PATH" == "$SELF_REPO_ROOT/"* ]]; then
  exit 0
fi

# (The notes root is ZONE 1, near the top: checked before every ~/.claude rule, as it always was.)

# ── FAIL CLOSED when the person's zones are UNKNOWN (scrub part 2, 2026-11-01) ──
# The zones above come from the two pointers. When either pointer is unset, names a folder that is gone, or the
# resolver could not run (LH_STRICT=1), this guard cannot tell which folders are the person's, so it must not go
# quietly permissive: it protects, EVERYWHERE outside the zones it could still recognise, the same things the
# zones protect -- hook scripts (system/hooks/), git internals (.git/) and settings files (.claude/settings*.json);
# and while the personal code folder is unknown, agent-written CONTENT inside any other git working tree (the
# code-zone residency split, applied to every repo because the code zones cannot be read). The REDIRECT names the
# fix: set the pointer. Never weaker than before the pointers existed.
if [[ "${LH_STRICT:-1}" != 0 ]]; then
  _why="your notes pointer is ${LH_NOTES_STATUS:-unknown} and your personal-code pointer is ${LH_PERSONAL_STATUS:-unknown}, so this guard cannot tell which folders are yours and protects every one"
  _fix="set the pointers (python3 system/tools/bootstrap.py, or python3 shared/brain_root.py --set <notes folder>)"
  if [[ "$FILE_PATH" == */system/hooks/* || "$FILE_PATH" == */.git/* || "$FILE_PATH" == */.claude/settings.json || "$FILE_PATH" == */.claude/settings.local.json ]]; then
    printf '%s\n' "{\"decision\":\"block\",\"reason\":\"BLOCKED: hook scripts, git internals and settings files are protected ($FILE_PATH). WHY: $_why. REDIRECT: $_fix; a deliberate hook edit goes through Bash (chmod 644, edit, chmod 755). RULE: system/hooks/guard_write_paths.sh FAIL CLOSED.\"}" >&2
    exit 2
  fi
  if [[ "${LH_PERSONAL_STATUS:-unknown}" != ok ]]; then
    _anc="$FILE_PATH"; while [[ ! -d "$_anc" && "$_anc" != "/" ]]; do _anc="$(dirname "$_anc")"; done
    _top="$(git -C "$_anc" rev-parse --show-toplevel 2>/dev/null)"
    if [[ -n "$_top" && "$_top" != "$_SELF_REPO" && ( -z "$LH_NOTES_ROOT" || "$_top" != "$LH_NOTES_ROOT" ) ]]; then
      REL="${FILE_PATH#"$_top"/}"
      case "$REL" in
        state/*|records/* \
      |desks/*/canon/*|desks/*/records/*|desks/*/state/*|desks/*/projects/* \
      |system/journal.md|system/logs/*|system/observability/*|system/research/*|system/archivist/*|system/learnings*|system/history/*|system/handoffs/*|system/migration/*|system/tests/*|system/vault-* \
      |system/project-registry.md \
      |shared/proposals/*|shared/characters/*|shared/reference/[0-9][0-9][0-9][0-9]-* \
      |skills/*/user-*.md|skills/*/personal-*.md)
          printf '%s\n' "{\"decision\":\"block\",\"reason\":\"BLOCKED: agent-written CONTENT cannot be written into a code repo ($REL in $_top). WHY: $_why; content lives only in the notes root. REDIRECT: $_fix, then write it under your notes root.\"}" >&2
          exit 2
          ;;
      esac
    fi
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
    printf '%s\n' "{\"decision\":\"block\",\"reason\":\"BLOCKED: write path is outside every approved zone: $FILE_PATH. WHY: deny-by-default -- an agent write must land inside a recognised zone (the notes root, this repo, a listed code zone, lifehack-brain, or a listed ~/.claude exception), never an unlisted machine-local path. REDIRECT: if this is legitimate scratch work, that is exactly what GUARD_WRITE_PATHS_MODE=warn (the shipped default) is for reviewing before anything is added to the zone list -- widen the allowlist from the warn-only log (\$GUARD_WRITE_PATHS_LOG) with the operator's sign-off, never by routing around this guard. RULE: system/hooks/guard_write_paths.sh, ENFORCEMENT MODE.\"}" >&2
    exit 2
fi

# WARN-ONLY (the shipped default): log what enforce mode would have denied, then allow -- refuses
# nothing. mkdir -p and the append are both best-effort; a logging failure must never itself become
# a block (that would turn an observability feature into a second, undocumented enforcement path).
mkdir -p "$(dirname "$GUARD_WRITE_PATHS_LOG")" 2>/dev/null
printf '%s\t%s\t%s\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "WOULD-DENY" "$FILE_PATH" "mode=warn" >> "$GUARD_WRITE_PATHS_LOG" 2>/dev/null
exit 0

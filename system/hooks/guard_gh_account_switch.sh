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
#  MEASURED HERE, 2026-08-14, not cited from elsewhere. Four of these guards were
#  fire-tested and then attacked by two independent auditors charged to break them:
#    · the first found 20 bypasses in ~20 minutes; 11 of 13 headline claims reproduced
#    · after a rewrite, the second found 13 more, all reproduced
#    · after three rounds of hardening, 1 of 27 tested attack forms still passes
#  Every one of those holes was in a guard reading a command STRING. This system's
#  own journal states the pattern: 17 of 52 registered hooks guard Bash, and every
#  guard that failed was one of them — every guard that fired correctly was on a
#  typed tool.
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
# WHY: 2026-08-04 — a ClaudeOps session ran `gh auth login` + `gh auth switch` to get
#      admin on the NEW student-product repo (LifehackMethod/lifehack-brain). `gh` holds
#      ONE active account per host, so that flipped the account for EVERY window on the
#      machine. A parallel session's security check then asked "is <owner>/<private-config-repo>
#      private?" and got `Could not resolve to a Repository` — INDISTINGUISHABLE from
#      "the repo does not exist." It could not tell contained from exposed, and had to
#      route around gh entirely with an unauthenticated probe. A privacy check that fails
#      OPEN and SILENT is the exact failure class this system exists to prevent.
# GUARDS: any Bash command that MUTATES global `gh` auth state — `gh auth login`,
#      `gh auth logout`, `gh auth refresh`, and `gh auth switch` to any account other than the
#      operator's own (configured via CLAUDEOPS_GH_USER; unset means every switch is guarded,
#      no exception). Read-only `gh auth status` is untouched. Blocks ONLY when the session
#      is working inside the ClaudeOps zone (the clone or the Drive _ClaudeOps spine); a
#      session launched from the student-product folder is NOT blocked.
#      `gh auth switch --user <CLAUDEOPS_GH_USER>` is ALLOWED when that env var is set — that
#      is the REPAIR direction, and a guard that blocks its own recovery path is a trap.
# REDIRECT: never change global state for a one-off. Pass the token for that single command:
#      `GH_TOKEN=<lifehack-token> gh repo edit LifehackMethod/lifehack-brain --visibility private`
#      To restore ClaudeOps state: `gh auth switch --user <CLAUDEOPS_GH_USER>` (allowed when
#      that env var names your own account; not blocked).
#      If you genuinely need a persistent switch, the USER runs it themselves with `!`.
# SIGNPOST: the rule lives in system/sops/hook-sop.md (WHEN) + system/hook-contract.md
#      (mechanics) + CLAUDE.md → "Code vs Content" (identity separation). Incident recorded
#      in state/projects/cowork-migration/brief.md → STORY LOG 2026-08-04. Change the RULE
#      there with the operator's sign-off — never weaken this file to make one command fit.
# FAIL_POSTURE: closed
# UPDATED: 2026-08-04
# ─────────────────────────────────────────────────────────────────────────────
# guard_gh_account_switch.sh — PreToolUse hook (matcher: Bash)

INPUT=$(cat)

PARSED=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('tool_input', {}).get('command', ''))
    print(d.get('cwd', ''))
except:
    sys.exit(1)
") || { printf '%s\n' 'BLOCKED: guard_gh_account_switch got unparseable hook input — failing CLOSED per FAIL_POSTURE.' >&2; exit 2; }

COMMAND=$(printf '%s' "$PARSED" | sed -n '1p')
SESSION_CWD=$(printf '%s' "$PARSED" | sed -n '2p')
[ -z "$SESSION_CWD" ] && SESSION_CWD="$PWD"

# --- Is this session inside the ClaudeOps zone? -------------------------------
CLONE_ROOT="$HOME/claudeops-config"
# THIS repo's root, resolved the same way guard_organism_map.sh and guard_write_paths.sh already
# do it -- CLAUDE_PROJECT_DIR (set by the harness) first, falling back to this hook's own on-disk
# location ($0-relative). NOT a second hardcoded literal: if the checkout moves, or a fresh clone
# is opened elsewhere, this line keeps resolving correctly without another edit here. Fixes the
# cutover to ~/ClaudeOps, where CLONE_ROOT alone left the case statement below hitting its
# `*) exit 0` fallthrough unconditionally for every session running from the new repo.
_HOOKDIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd -P)"
# ⛔ PRECEDENCE INVERTED 2026-08-23 (T2.2) -- same defect proven live in guard_write_paths.sh:
# CLAUDE_PROJECT_DIR is the SESSION'S LAUNCH CWD, not the declaring repo, so preferring it made the
# sibling guard return exit 0 (FAIL OPEN) for any session launched elsewhere. $0 is where the SCRIPT
# lives, which is the only thing that actually identifies its repo. Fallback kept for the case where
# $0 cannot be resolved.
THIS_REPO_ROOT="${_HOOKDIR%/system/hooks}"
[ -n "$THIS_REPO_ROOT" ] && [ -d "$THIS_REPO_ROOT/system/hooks" ] || THIS_REPO_ROOT="${CLAUDE_PROJECT_DIR:-}"
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

case "$SESSION_CWD" in
  "$CLONE_ROOT"|"$CLONE_ROOT"/*|"$DRIVE_ROOT"|"$DRIVE_ROOT"/*|"$THIS_REPO_ROOT"|"$THIS_REPO_ROOT"/*) ;;
  *) exit 0 ;;
esac

# --- Does the command MUTATE global gh auth state? ----------------------------
# `gh auth status` (read-only) deliberately NOT matched.
if ! echo "$COMMAND" | grep -qE '(^|[[:space:]]|/|;|&&|\|\|)gh[[:space:]]+auth[[:space:]]+(login|logout|refresh|switch)([[:space:]]|$|;)'; then
  exit 0
fi

# --- ALLOW the repair direction: switching BACK to the operator's own identity -----
# Configurable, never hardcoded -- CLAUDEOPS_GH_USER names the account this installation
# treats as "home". Unset means there is no special-cased repair account: every switch
# is guarded, no exception (still just a speed bump -- see the header banner above).
if [ -n "${CLAUDEOPS_GH_USER:-}" ] && echo "$COMMAND" | grep -qE "gh[[:space:]]+auth[[:space:]]+switch[[:space:]]+.*--user[[:space:]]+${CLAUDEOPS_GH_USER}([[:space:]]|\$|;)"; then
  exit 0
fi

printf '%s\n' 'BLOCKED: this command MUTATES GLOBAL `gh` auth state from inside a ClaudeOps session. WHY: gh holds ONE active account per host, so switching here silently re-points EVERY open window. On 2026-08-04 exactly this made a parallel privacy check return "Could not resolve to a Repository" — indistinguishable from "does not exist" — so a session could not tell whether claudeops-config was private or public. A security check that fails open and silent is the failure class this system exists to prevent. REDIRECT: do NOT change global state for a one-off — pass the token for that single command instead: `GH_TOKEN=<lifehack-token> gh repo edit LifehackMethod/lifehack-brain --visibility private`. To restore ClaudeOps state, `gh auth switch --user <CLAUDEOPS_GH_USER>` is ALLOWED and not blocked when CLAUDEOPS_GH_USER names your own account. If you truly need a persistent switch, ask the USER to run it themselves with the `!` prefix. RULE: system/sops/hook-sop.md + system/hook-contract.md + CLAUDE.md "Code vs Content"; incident in state/projects/cowork-migration/brief.md STORY LOG 2026-08-04. Change the rule there with sign-off — never weaken the guard to fit one command.' >&2
exit 2

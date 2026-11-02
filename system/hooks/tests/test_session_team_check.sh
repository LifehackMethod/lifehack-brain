#!/bin/bash
# test_session_team_check.sh — the session-start check for team-shared skills (Drive skill sharing,
# approved design 2026-11-01, SIMPLE build), run through the REAL session_context_loader.sh.
# A FAKE HOME under a temp dir only: the real ~/Library/CloudStorage is never touched.
#   OFF (the default): nothing runs — the broken link is left exactly as it was, nothing printed.
#   ON: one "shared skill problem" line names the broken skill; the link (only the link) is dropped.
# Run: bash system/hooks/tests/test_session_team_check.sh   (exit 0 = all pass)

HOOKS="$(cd "$(dirname "$0")/.." && pwd)"
LOADER="$HOOKS/session_context_loader.sh"
SANDBOX="$(mktemp -d "${TMPDIR:-/tmp}/teamchk.XXXXXX")"
trap 'rm -rf "$SANDBOX"' EXIT
pass=0; fail=0
ok()  { pass=$((pass+1)); }
bad() { fail=$((fail+1)); echo "  FAIL [$1]: $2"; }

setup() {
  mkdir -p "$SANDBOX/notes" "$SANDBOX/.config/lifehack" "$SANDBOX/.claude/skills" "$SANDBOX/drive/Team skills/skills"
  printf 'team\n' > "$SANDBOX/.config/lifehack/team-sharing"
  printf '%s\n' "$SANDBOX/drive/Team skills" > "$SANDBOX/.config/lifehack/team-skills"
  ln -sfn "$SANDBOX/drive/Team skills/skills/gone" "$SANDBOX/.claude/skills/gone"
  printf '{"name": "gone", "target": "%s", "sha256": "%s", "mode": "symlink"}\n' \
    "$SANDBOX/drive/Team skills/skills/gone" "$(printf 'x%.0s' $(seq 64))" > "$SANDBOX/.config/lifehack/team-skills-linked"
}
runit() { OUT="$(env HOME="$SANDBOX" LIFEHACK_ROOT="$SANDBOX/notes" ROUNDB_TEAM_SKILL_VERIFY="$1" bash "$LOADER" 2>&1)"; RC=$?; }

setup
runit off
[ "$RC" = 0 ] && ok || bad "off: exit" "rc=$RC"
! printf '%s' "$OUT" | grep -q "shared skill problem" && ok || bad "off: silent" "printed a team line with the switch off"
[ -L "$SANDBOX/.claude/skills/gone" ] && ok || bad "off: nothing ran" "the link was touched with the switch off"

runit on
[ "$RC" = 0 ] && ok || bad "on: exit" "rc=$RC"
printf '%s' "$OUT" | grep -q "shared skill problem: .*'gone'" && ok || bad "on: reports" "no line naming the broken skill"
[ ! -L "$SANDBOX/.claude/skills/gone" ] && ok || bad "on: drops link" "the dangling link is still there"
[ -d "$SANDBOX/drive/Team skills" ] && ok || bad "on: team folder intact" "the team folder was touched"

echo "test_session_team_check: $pass passed, $fail failed"
[ "$fail" = 0 ]

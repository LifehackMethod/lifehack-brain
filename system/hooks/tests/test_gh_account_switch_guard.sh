#!/bin/bash
# test_gh_account_switch_guard.sh — deny-coverage suite for system/hooks/guard_gh_account_switch.sh
# (B6.0 — this guard had NO test anywhere before this file.)
#
# ⚠ ALLOW CASES FIRST — see hook-contract.md.
#
# Zone: this guard only fires when the session's `cwd` is inside the ClaudeOps clone, the Drive
# spine, THIS declaring repo (resolved $0-relative — i.e. this worktree, since the guard script
# lives under it), or CLAUDE_PROJECT_DIR. We set the payload's "cwd" to this worktree's own root so
# the guard's zone check passes the same way it would for a real session working here, and also
# test the OUT-OF-ZONE case explicitly (a real near-miss the header itself documents).
#
# Invocation form matches the registered one: bash "${CLAUDE_PROJECT_DIR}/system/hooks/guard_gh_account_switch.sh"
#
# ── EXTENDED 2026-09-17 ────────────────────────────────────────────────────────────────────────
# Enver ruling: extend this suite IN PLACE (not replace) to cover every decision branch in R27
# (2026-09-16, handoff-bundles/2026-09-16-round-4/R27-GH-ACCOUNT-SWITCH-BEHAVIOR.md — a 23-payload
# one-off harness that proved the guard's decisions were unchanged by the fire-journal instrumentation,
# covering every branch in the source: the 4 mutation verbs, the repair path, the owner-var-unset
# fail-closed path, the different-user-when-owner-set path, read-only `gh auth status`, all 4 zone
# roots, the outside-zone fallthrough, chained/prefixed command forms, malformed/empty stdin, the
# cwd-fallback path, and tool_name-independence). This is a strict superset of the original 8 cases
# below — verified 1:1 before landing:
#
#   B6.0 original case                                          -> case here (same rc, equivalent msg)
#   allow "read-only gh auth status"                             -> "10 gh auth status, in zone"
#   allow "unrelated gh command" (gh repo view ...)               -> "02b gh repo view ..., in zone" (added)
#   allow "the repair direction: switch back to owner account"    -> "07 gh auth switch --user OWNER, owner set"
#   allow "out-of-zone session never matched at all" (gh auth login) -> "19b gh auth login, out-of-zone" (added)
#   deny  "gh auth login"                                          -> "03 gh auth login, in zone"
#   deny  "gh auth logout"                                         -> "04 gh auth logout, in zone"
#   deny  "gh auth refresh"                                        -> "05 gh auth refresh, in zone"
#   deny  "gh auth switch to a non-owner account" (owner var unset) -> "08 gh auth switch --user OWNER, owner UNSET"
#
# The two "(added)" rows had no equivalent payload shape anywhere in the R27-derived cases, so they
# were carried over verbatim rather than folded into a near-miss. Every deny case below asserts a
# substring of the guard's message; the guard emits exactly ONE static message per decision (see
# source), so a substring match also proves the WHY/REDIRECT text B6.0's `deny()` checked for is
# present — same decision, same exit code, equivalent message check.
# ───────────────────────────────────────────────────────────────────────────────────────────────
#
# WHY THIS SUITE EXISTS (unchanged from the 2026-09-17 extension pass). Deny = exit 2. Allow =
# exit 0. FAIL_POSTURE of the guard itself is "closed" (unparseable input, missing owner config ->
# deny), so several ALLOW-looking inputs (malformed JSON, empty stdin, owner var unset) correctly
# assert exit 2, not 0.
#
# Every case runs under a fresh scratch $HOME (env -i, never inherits the real session's HOME,
# CLAUDE_PROJECT_DIR, LIFEHACK_OWNER_GH_USER or CLAUDEOPS_DRIVE) so no real account state or the
# real ~/.claude/run is ever touched. `gh`/`git` are stubbed on PATH; the guard is expected to
# call neither (confirmed by R27's read of the source: it decides from command text + env/cwd
# only) — the stub call log is asserted empty at the end as a standing check on that claim.
#
# Run: bash system/hooks/tests/test_gh_account_switch_guard.sh   (exit 0 = all pass)

HOOKS="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$HOOKS/../.." && pwd)"
GUARD="$HOOKS/guard_gh_account_switch.sh"
[ -f "$GUARD" ] || { echo "CANNOT RUN: no hook at $GUARD"; exit 1; }

pass=0; fail=0
ok()  { pass=$((pass+1)); }
bad() { fail=$((fail+1)); echo "  FAIL [$1]: $2"; }

# ── scratch root: everything this run creates lives here and nowhere else ────────────────────
SCRATCH_ROOT="$(mktemp -d "/private/tmp/claude-501/gh-switch-test.XXXXXX")"
trap 'rm -rf "$SCRATCH_ROOT"' EXIT

# ── stub gh/git on PATH: the guard must never invoke either (no network, no real account state)
STUB_BIN="$SCRATCH_ROOT/stub-bin"
mkdir -p "$STUB_BIN"
STUB_CALL_LOG="$SCRATCH_ROOT/stub-calls.log"
: > "$STUB_CALL_LOG"
cat > "$STUB_BIN/gh" <<EOF
#!/bin/bash
echo "gh \$@" >> "$STUB_CALL_LOG"
exit 0
EOF
cat > "$STUB_BIN/git" <<EOF
#!/bin/bash
echo "git \$@" >> "$STUB_CALL_LOG"
exit 0
EOF
chmod +x "$STUB_BIN/gh" "$STUB_BIN/git"

# ── static fixtures shared read-only across cases ─────────────────────────────────────────────
# PROJECT_DIR_ROOT only validates when CLAUDE_PROJECT_DIR/system/hooks actually exists on disk.
FAKE_PROJECT_DIR="$SCRATCH_ROOT/fake-project-dir"
mkdir -p "$FAKE_PROJECT_DIR/system/hooks"
# DRIVE_ROOT: set via CLAUDEOPS_DRIVE directly (no glob discovery needed / no real email in a path).
DRIVE_FIXTURE="$SCRATCH_ROOT/fake-drive-root/_ClaudeOps"
mkdir -p "$DRIVE_FIXTURE"
# Outside every zone.
OUTSIDE_DIR="$SCRATCH_ROOT/outside-project"
mkdir -p "$OUTSIDE_DIR"

OWNER="lifehack-owner-fixture"

# ── stable message substrings (never whole messages) ──────────────────────────────────────────
DENY_SUBSTR='this command MUTATES GLOBAL `gh` auth state'
PARSE_FAIL_SUBSTR='guard_gh_account_switch got unparseable hook input'
EMPTY_SENTINEL="__EMPTY_OUTPUT__"

# ── JSON payload builder: argv-based, so no shell-quoting hazards for embedded quotes/semicolons
_build_json() {
  # args: cmd cwd_omit(0/1) cwd_val toolname
  python3 - "$1" "$2" "$3" "$4" <<'PY'
import json, sys
cmd, cwd_omit, cwd_val, toolname = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
d = {"tool_name": toolname, "tool_input": {"command": cmd}}
if cwd_omit != "1":
    d["cwd"] = cwd_val
print(json.dumps(d))
PY
}

# ── run_case <label> <expected-rc> <expect-substr | EMPTY_SENTINEL | ""> ──────────────────────
# Reads case-scoped inputs from the C_* globals the caller sets just before calling this, then
# resets them so the next call starts clean. See the case list below for what each means.
run_case() {
  local label="$1" exp_rc="$2" expect="$3"
  local case_home cwd_val stdin_payload got_out got_rc

  case_home="$(mktemp -d "$SCRATCH_ROOT/home.XXXXXX")"

  if [ "${C_CWD_ZONE_CLONE:-0}" = "1" ]; then
    cwd_val="$case_home/claudeops-config${C_CWD_SUB:-}"
  else
    cwd_val="${C_CWD:-}"
  fi

  if [ -n "${C_STDIN_RAW_SET:-}" ]; then
    stdin_payload="$C_STDIN_RAW"
  else
    stdin_payload="$(_build_json "${C_CMD:-}" "${C_CWD_OMIT:-0}" "$cwd_val" "${C_TOOLNAME:-Bash}")"
  fi

  if [ -n "${C_STDIN_RAW_SET:-}" ] && [ -z "$C_STDIN_RAW" ]; then
    got_out="$(
      cd "${C_PROC_CWD:-$REPO}" 2>/dev/null || cd "$REPO"
      env -i \
        HOME="$case_home" \
        PATH="$STUB_BIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        ${C_OWNER:+LIFEHACK_OWNER_GH_USER="$C_OWNER"} \
        ${C_DRIVE:+CLAUDEOPS_DRIVE="$C_DRIVE"} \
        ${C_PROJDIR:+CLAUDE_PROJECT_DIR="$C_PROJDIR"} \
        bash "$GUARD" </dev/null 2>&1
    )"
  else
    got_out="$(
      cd "${C_PROC_CWD:-$REPO}" 2>/dev/null || cd "$REPO"
      env -i \
        HOME="$case_home" \
        PATH="$STUB_BIN:/usr/bin:/bin:/usr/sbin:/sbin" \
        ${C_OWNER:+LIFEHACK_OWNER_GH_USER="$C_OWNER"} \
        ${C_DRIVE:+CLAUDEOPS_DRIVE="$C_DRIVE"} \
        ${C_PROJDIR:+CLAUDE_PROJECT_DIR="$C_PROJDIR"} \
        bash "$GUARD" <<<"$stdin_payload" 2>&1
    )"
  fi
  got_rc=$?

  if [ "$got_rc" != "$exp_rc" ]; then
    bad "$label" "expected exit $exp_rc, got $got_rc (output: $got_out)"
  elif [ "$expect" = "$EMPTY_SENTINEL" ]; then
    if [ -n "$got_out" ]; then
      bad "$label" "expected silent allow (no output), got: $got_out"
    else
      ok
    fi
  elif [ -n "$expect" ]; then
    if [[ "$got_out" == *"$expect"* ]]; then
      ok
    else
      bad "$label" "expected output to contain: $expect -- got: $got_out"
    fi
  else
    ok
  fi

  unset C_CMD C_CWD C_CWD_OMIT C_TOOLNAME C_OWNER C_DRIVE C_PROJDIR C_PROC_CWD \
        C_CWD_ZONE_CLONE C_CWD_SUB C_STDIN_RAW C_STDIN_RAW_SET
}

echo "── ALLOW: non-gh-auth traffic, in and outside the zone (R27 #01-02) ─────────────────────"
C_CMD="ls -la"; C_CWD="$REPO"
run_case "01 ls -la, in THIS_REPO_ROOT zone" 0 "$EMPTY_SENTINEL"

C_CMD="ls -la"; C_CWD="$OUTSIDE_DIR"
run_case "02 ls -la, outside all zones" 0 "$EMPTY_SENTINEL"

echo "── ALLOW: a gh command that isn't an auth-mutating verb (B6.0 #2, verb-regex boundary) ──"
C_CMD="gh repo view LifehackMethod/lifehack-brain"; C_CWD="$REPO"
run_case "02b gh repo view ..., in zone -> allow (not login/logout/refresh/switch)" 0 "$EMPTY_SENTINEL"

echo "── DENY: the four gh-auth mutation verbs, in zone (R27 #03-06) ──────────────────────────"
C_CMD="gh auth login"; C_CWD="$REPO"
run_case "03 gh auth login, in zone" 2 "$DENY_SUBSTR"

C_CMD="gh auth logout"; C_CWD="$REPO"
run_case "04 gh auth logout, in zone" 2 "$DENY_SUBSTR"

C_CMD="gh auth refresh"; C_CWD="$REPO"
run_case "05 gh auth refresh, in zone" 2 "$DENY_SUBSTR"

C_CMD="gh auth switch"; C_CWD="$REPO"
run_case "06 gh auth switch (no args), in zone" 2 "$DENY_SUBSTR"

echo "── the repair path and the owner-var branches (R27 #07-09, B6.0 #3 and #8) ──────────────"
C_CMD="gh auth switch --user $OWNER"; C_CWD="$REPO"; C_OWNER="$OWNER"
run_case "07 gh auth switch --user OWNER, owner var set -> allow (repair)" 0 "$EMPTY_SENTINEL"

C_CMD="gh auth switch --user $OWNER"; C_CWD="$REPO"
run_case "08 gh auth switch --user OWNER, owner var UNSET -> block (fail closed)" 2 "$DENY_SUBSTR"

C_CMD="gh auth switch --user someone-else"; C_CWD="$REPO"; C_OWNER="$OWNER"
run_case "09 gh auth switch --user someone-else, owner var set to a DIFFERENT user -> block" 2 "$DENY_SUBSTR"

echo "── ALLOW: read-only gh auth status (R27 #10, B6.0 #1) ───────────────────────────────────"
C_CMD="gh auth status"; C_CWD="$REPO"
run_case "10 gh auth status, in zone -> allow (read-only excluded)" 0 "$EMPTY_SENTINEL"

echo "── DENY: prefixed/chained command forms (R27 #11-13) ────────────────────────────────────"
C_CMD="GH_TOKEN=abc123 gh auth switch --user someone-else"; C_CWD="$REPO"
run_case "11 GH_TOKEN= prefix" 2 "$DENY_SUBSTR"

C_CMD="cd /tmp && gh auth switch --user someone-else"; C_CWD="$REPO"
run_case "12 && chained" 2 "$DENY_SUBSTR"

C_CMD="echo hi; gh auth switch --user someone-else"; C_CWD="$REPO"
run_case "13 ; chained" 2 "$DENY_SUBSTR"

echo "── ALLOW: quoted \"gh\" — known regex-boundary gap, unaffected by release (R27 #14) ──────"
C_CMD='"gh" auth switch --user someone-else'; C_CWD="$REPO"
run_case "14 quoted gh" 0 "$EMPTY_SENTINEL"

echo "── DENY: unparseable input fails CLOSED (R27 #15-16) ────────────────────────────────────"
C_STDIN_RAW_SET=1; C_STDIN_RAW='{not valid json!!'
run_case "15 malformed JSON stdin" 2 "$PARSE_FAIL_SUBSTR"

C_STDIN_RAW_SET=1; C_STDIN_RAW=''
run_case "16 empty stdin" 2 "$PARSE_FAIL_SUBSTR"

echo "── DENY: every zone root (R27 #17-18, #21), ALLOW outside all zones (R27 #19) ───────────"
C_CMD="gh auth switch --user someone-else"; C_CWD_ZONE_CLONE=1
run_case "17 CLONE_ROOT zone (\$HOME/claudeops-config)" 2 "$DENY_SUBSTR"

C_CMD="gh auth switch --user someone-else"; C_CWD="$DRIVE_FIXTURE"; C_DRIVE="$DRIVE_FIXTURE"
run_case "18 DRIVE_ROOT zone (CLAUDEOPS_DRIVE)" 2 "$DENY_SUBSTR"

C_CMD="gh auth switch --user someone-else"; C_CWD="$OUTSIDE_DIR"
run_case "19 outside all zones -> allow" 0 "$EMPTY_SENTINEL"

echo "── ALLOW: out-of-zone with a mutating verb itself, B6.0 #4's exact payload shape ────────"
C_CMD="gh auth login"; C_CWD="$OUTSIDE_DIR"
run_case "19b gh auth login, out-of-zone -> allow (B6.0's own near-miss)" 0 "$EMPTY_SENTINEL"

C_CMD="gh auth switch --user someone-else"; C_PROJDIR="$FAKE_PROJECT_DIR"; C_CWD="$FAKE_PROJECT_DIR"
run_case "21 PROJECT_DIR_ROOT zone (CLAUDE_PROJECT_DIR, distinct from THIS_REPO_ROOT)" 2 "$DENY_SUBSTR"

echo "── DENY: cwd omitted from JSON, falls back to process \$PWD (R27 #20) ───────────────────"
C_CMD="gh auth switch --user someone-else"; C_CWD_OMIT=1; C_PROC_CWD="$REPO"
run_case "20 cwd omitted, process \$PWD = zone dir (fallback path)" 2 "$DENY_SUBSTR"

echo "── DENY: trailing-semicolon form, and tool_name independence (R27 #22-23) ───────────────"
C_CMD="gh auth switch;"; C_CWD="$REPO"
run_case "22 gh auth switch; (no --user)" 2 "$DENY_SUBSTR"

C_CMD="gh auth switch --user someone-else"; C_CWD="$REPO"; C_TOOLNAME="Write"
run_case "23 tool_name=Write (guard ignores tool_name, non-Bash tool still checked)" 2 "$DENY_SUBSTR"

echo "── invariant: gh/git were never actually invoked by the guard, any case ─────────────────"
if [ -s "$STUB_CALL_LOG" ]; then
  bad "stub-call-log" "expected empty (guard never shells out to gh/git), got: $(cat "$STUB_CALL_LOG")"
else
  ok
fi

echo
if [ "$fail" = 0 ]; then echo "RESULT: $pass passed, 0 failed."; echo "GH-ACCOUNT-SWITCH GUARD GREEN"; exit 0
else echo "RESULT: $pass passed, $fail failed."; exit 1; fi

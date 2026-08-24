#!/bin/bash
# test_gmail_send_guard.sh — two-sided suite for system/hooks/guard_gmail_send.sh
#
# ⚠ ALLOW CASES COME FIRST, DELIBERATELY. A guard that blocks ordinary work gets unregistered,
#   and then it guards nothing. The reads and the drafting path are the work this system
#   actually does with mail; if any of them start failing, the guard is the bug.
#
# ⚠ THIS SUITE ASSERTS THE DENY TEXT, NOT ONLY THE EXIT CODE. On 2026-08-15 a sibling lane
#   shipped a guard whose deny message carried backticks, producing output that json.load()
#   refused. exit 2 still fired, so an exit-code-only test scored it PASS — while the message
#   would have rendered on NEITHER channel. A guard that blocks and cannot speak is a wall with
#   no door. Every deny case below therefore checks four things:
#     1. rc == 2                          (the honored PreToolUse block signal)
#     2. stdout is EMPTY                  (survives 2>/dev/null -- i.e. it is on stderr)
#     3. stderr re-parses as valid JSON   (the message can actually render)
#     4. the reason carries WHY + REDIRECT + RULE  (a deny with no redirect causes blind retries)
#
# Run:  bash system/hooks/tests/test_gmail_send_guard.sh   ·   exit 0 = all green.

HERE="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
GUARD="$(cd "$HERE/.." 2>/dev/null && pwd)/guard_gmail_send.sh"
# Portable across BSD mktemp (macOS: `-t PREFIX` takes a bare prefix and appends its own
# suffix) and GNU mktemp (Linux/CI: `-t TEMPLATE` requires the template to literally END in
# XXXXXX, and errors with no output otherwise). `-t gmailsendguard` satisfied the former and
# silently failed the latter -- ERRF then resolved to an EMPTY string, `2>"$ERRF"` became an
# ambiguous redirect, and every single case in this suite (allow and deny alike) failed with
# rc=1 on the GitHub Actions Linux runner while staying green on a macOS laptop. Spelling the
# template explicitly works identically on both.
ERRF="$(mktemp "${TMPDIR:-/tmp}/gmailsendguard.XXXXXX")"
PASSED=0
FAILED=0

if [ ! -r "$GUARD" ]; then
  echo "MISSING: $GUARD — nothing to test. FAILING CLOSED."
  exit 1
fi

mkjson() {
  T_CMD="$1" python3 -c 'import os, json; print(json.dumps({"tool_name": "Bash", "tool_input": {"command": os.environ["T_CMD"]}}))'
}

# ── ALLOW ────────────────────────────────────────────────────────────────────────────────────
allow() {
  desc="$1"; cmd="$2"
  out=$(mkjson "$cmd" | bash "$GUARD" 2>"$ERRF"); rc=$?
  if [ "$rc" -eq 0 ]; then
    printf "  PASS  allow  %s\n" "$desc"
    PASSED=$((PASSED + 1))
  else
    printf "  FAIL  allow  %s  (rc=%s) OVER-BLOCK\n" "$desc" "$rc"
    printf "        stderr: %.140s\n" "$(cat "$ERRF")"
    FAILED=$((FAILED + 1))
  fi
}

# ── DENY ─────────────────────────────────────────────────────────────────────────────────────
deny() {
  desc="$1"; cmd="$2"
  out=$(mkjson "$cmd" | bash "$GUARD" 2>"$ERRF"); rc=$?
  _judge "$desc" "$rc" "$out"
}

deny_raw() {          # a payload that is not valid hook JSON at all — must fail CLOSED
  desc="$1"; raw="$2"
  out=$(printf '%s' "$raw" | bash "$GUARD" 2>"$ERRF"); rc=$?
  _judge "$desc" "$rc" "$out"
}

_judge() {
  desc="$1"; rc="$2"; out="$3"
  problems=""
  [ "$rc" -eq 2 ] || problems="$problems rc=$rc(want 2);"
  [ -z "$out" ] || problems="$problems stdout-not-empty(deny must be on stderr);"
  verdict=$(T_ERRF="$ERRF" python3 -c '
import os, json, sys
raw = open(os.environ["T_ERRF"]).read().strip()
if not raw:
    print("stderr-empty(nothing on either channel);"); sys.exit(0)
try:
    d = json.loads(raw)
except Exception as e:
    print("stderr-not-valid-json(%s);" % type(e).__name__); sys.exit(0)
r = d.get("reason", "")
missing = [k for k in ("WHY:", "REDIRECT:", "RULE:") if k not in r]
if d.get("decision") != "block":
    missing.append("decision!=block")
if "drafts create" not in r:
    missing.append("redirect-names-no-command")
print(("missing:" + ",".join(missing) + ";") if missing else "")
')
  problems="$problems$verdict"
  if [ -z "$problems" ]; then
    printf "  PASS  deny   %s\n" "$desc"
    PASSED=$((PASSED + 1))
  else
    printf "  FAIL  deny   %s  ->%s\n" "$desc" "$problems"
    FAILED=$((FAILED + 1))
  fi
}

echo "=== guard_gmail_send.sh — ALLOW cases first (over-blocking is the failure that kills a guard) ==="

allow "an unrelated command"                  "ls -la"
allow "another gws service entirely"          "gws calendar events list --params x"
allow "gws help, no service"                  "gws --help"
allow "bare service call"                     "gws gmail"
allow "DRAFT create — the whole point"        'gws gmail users drafts create --params {"userId":"me"}'
allow "DRAFT update"                          'gws gmail users drafts update --id r1 --params {"userId":"me"}'
allow "DRAFT get"                             "gws gmail users drafts get --id r1"
allow "DRAFT list"                            "gws gmail users drafts list --params x"
allow "DRAFT delete"                          "gws gmail users drafts delete --id r1"
allow "messages list"                         "gws gmail users messages list --params x"
allow "messages get (metadata read)"          'gws gmail users messages get --params {"format":"metadata"}'
allow "threads get"                           "gws gmail users threads get --id 18abc"
allow "threads list"                          "gws gmail users threads list --params x"
allow "the messages read alias"               "gws gmail messages read 18abc"
allow "labels list"                           "gws gmail users labels list"
allow "labels delete (a label is not mail)"   "gws gmail users labels delete --id L1"
allow "settings get"                          "gws gmail users settings get --params x"
allow "history list"                          "gws gmail users history list --params x"
allow "getProfile"                            "gws gmail users getProfile --user-id me"
allow "attachments get (a read)"              "gws gmail users messages attachments get --id a1"
allow "label move (the reversible verb)"      "gws gmail users threads modify --id 18abc --add-label-ids L1"
allow "trash — owned by the DESTRUCTIVE guard, not double-owned here" \
                                              "gws gmail users threads trash --id 18abc"
allow "the words in a commit message, not a command" \
                                              "git commit -m 'guard blocks gws gmail users messages send'"
allow "the words written into a file, never executed" \
                                              "python3 - <<'EOF'
open('/tmp/note','w').write('gws gmail users messages send')
EOF"
allow "a payload body that merely CONTAINS the word send" \
                                              'gws gmail users messages list --params {"q":"send"}'
allow "the live label-map read this repo actually performs" \
                                              'gws gmail users labels list --params {"userId":"me"}'

echo
echo "=== DENY cases — every one also asserts the message is well-formed and re-parses ==="

deny "messages send"                          "gws gmail users messages send --params x"
deny "drafts send"                            "gws gmail users drafts send --id r123"
deny "the +send helper"                       "gws gmail +send --to nobody@example.com --subject hi"
deny "send with an assignment prefix"         'ID=r1 gws gmail users drafts send --id "$ID"'
deny "binary held in a variable"              'V=gws ; $V gmail users messages send --params x'
deny "wrapper words in front of the binary"   "env FOO=1 command gws gmail users messages send --params x"
deny "an absolute path to the binary"         "/usr/local/bin/gws gmail users messages send --id x"
deny "smuggled through bash -c"               'bash -c "gws gmail users messages send --params x"'
deny "inside a command substitution"          'echo $(gws gmail users messages send --id x)'
deny "chained after a benign command"         "echo go; gws gmail users messages send --params x"
deny "an unrecognised gmail operation (DEFAULT-DENY)" \
                                              "gws gmail users messages purge --id x"
deny "an operation hidden behind a variable"  'gws gmail users messages $VERB --id x'
deny "an unrecognised resource"               "gws gmail users outbox flush"
deny_raw "unparseable stdin must fail CLOSED" "not json at all"
deny_raw "empty stdin must fail CLOSED"       ""

rm -f "$ERRF"
echo
echo "  $PASSED passed, $FAILED failed"
if [ "$FAILED" -eq 0 ]; then
  echo "--- RESULT: GREEN — drafting and every read pass; every send path is refused and can speak. ---"
  exit 0
fi
echo "--- RESULT: RED ---"
exit 1

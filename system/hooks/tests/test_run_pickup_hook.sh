#!/bin/sh
# test_run_pickup_hook.sh — the pickup hook (spec run-pickup G5, invariants 8-11).
# ALLOW cases first; includes "the reader never writes" (folder hash before/after).
# Run: sh system/hooks/tests/test_run_pickup_hook.sh  (exit 0 = all pass)
HOOKS="$(cd "$(dirname "$0")/.." && pwd)"
HOOK="$HOOKS/run_pickup_hook.sh"
RUNNER="$HOOKS/../parts/stage_runner.py"
[ -f "$HOOK" ] || { echo "CANNOT RUN: no pickup hook at $HOOK"; exit 1; }

SANDBOX="$(mktemp -d "${TMPDIR:-/tmp}/pickup.XXXXXX")"
trap 'rm -rf "$SANDBOX"' EXIT
pass=0; fail=0
ok()  { pass=$((pass+1)); }
bad() { fail=$((fail+1)); echo "  FAIL [$1]: $2"; }

TAG='[RUN PICKUP — harness-injected, not user input]'

setup_card() {
  python3 - "$1" <<'PY'
import io, json, os, sys
td = sys.argv[1]
os.makedirs(os.path.join(td, "prompts"), exist_ok=True)
stages = []
for i, (sid, mode) in enumerate([("gather", "talk"), ("analyze", "talk"), ("finalize", "alone")], 1):
    io.open(os.path.join(td, "prompts", "%02d-%s.md" % (i, sid)), "w", encoding="utf-8").write(
        "Stage {{ID}} of {{TOTAL}} ({{MODE}}). Your code word: {{CODE}}. Write to {{OUT}}.\n")
    stages.append({"id": sid, "mode": mode,
                   "prompt": "prompts/%02d-%s.md" % (i, sid), "out": "out/%02d-%s.md" % (i, sid),
                   "checks": {"headings": ["## %s" % sid.title()], "min_words": 10, "code_word": True}})
json.dump({"skill": "pickupspec", "stop_limit": 3, "stages": stages},
          io.open(os.path.join(td, "card.json"), "w", encoding="utf-8"))
PY
}

PPAY="$SANDBOX/payload.json"
ppayload() { # $1 cwd $2 source -> writes JSON to $PPAY (python writes it; no shell redirect)
  python3 - "$1" "$2" "$PPAY" <<'PY'
import io, json, sys
io.open(sys.argv[3], "w", encoding="utf-8").write(json.dumps(
    {"cwd": sys.argv[1], "source": sys.argv[2],
     "session_id": "s", "hook_event_name": "SessionStart"}))
PY
}

runpickup() { # $1 cwd $2 source -> sets POUT, PRC
  ppayload "$1" "$2"
  POUT=`sh "$HOOK" < "$PPAY" 2>&1`; PRC=$?
}

folder_state() { # $1 dir: a checksum of every file in the run tree
  find "$1" -type f | sort | xargs cksum 2>/dev/null | cksum
}

card="$SANDBOX/card.json"
setup_card "$SANDBOX"
WD="$SANDBOX/wd"; mkdir -p "$WD"

echo "ALLOW: an unfinished run gets the offer, exit 0"
python3 "$RUNNER" start --card "$card" --workdir "$WD" > /dev/null 2>&1
before=`folder_state "$WD"`
runpickup "$WD" "startup"
[ "$PRC" -eq 0 ] && ok || bad "rc offer" "rc=$PRC"
case "$POUT" in *"$TAG"*) ok ;; *) bad "tag on offer" "$POUT" ;; esac
case "$POUT" in *"Continue, start over"*) ok ;; *) bad "offer text" "$POUT" ;; esac
case "$POUT" in *"pickupspec"*) ok ;; *) bad "offer names the skill" "$POUT" ;; esac
after=`folder_state "$WD"`
[ "$before" = "$after" ] && ok || bad "reader never writes" "folder changed"

echo "silent doors"
# 2. no run here: silent
mkdir -p "$SANDBOX/empty"
runpickup "$SANDBOX/empty" "startup"
[ "$PRC" -eq 0 ] && [ -z "$POUT" ] && ok || bad "no run silent" "rc=$PRC out=$POUT"
# 3. snoozed run: silent (the person answered first: the mover logged their prompt)
RIDS=`ls "$WD/runs" | head -1`
printf 'pp1\t%s\n' "$(date +%s)" >> "$WD/runs/$RIDS/person.log"
python3 "$RUNNER" snooze --choice leave-it --workdir "$WD" > /dev/null 2>&1
runpickup "$WD" "startup"
[ "$PRC" -eq 0 ] && [ -z "$POUT" ] && ok || bad "snoozed silent" "rc=$PRC out=$POUT"
# 4. an unattended session (job-run) is never asked
printf 'pp2\t%s\n' "$(date +%s)" >> "$WD/runs/$RIDS/person.log"
python3 "$RUNNER" resume --choice continue --workdir "$WD" > /dev/null 2>&1 # lift the snooze
POUT=""; PRC=""
LIFEHACK_JOB_RUN_ID=job-123 runpickup "$WD" "startup" 2>/dev/null
# the env must reach the hook's child: feed the file with the env set on the hook itself
ppayload "$WD" "startup"
POUT=`LIFEHACK_JOB_RUN_ID=job-123 sh "$HOOK" < "$PPAY" 2>&1`; PRC=$?
[ "$PRC" -eq 0 ] && [ -z "$POUT" ] && ok || bad "unattended silent" "rc=$PRC out=$POUT"

echo "a crashed reader still speaks, exit 0"
mkdir -p "$SANDBOX/fakebin"
printf '#!/bin/sh\nexit 97\n' > "$SANDBOX/fakebin/python3"
chmod 755 "$SANDBOX/fakebin/python3"
POUT=`PATH="$SANDBOX/fakebin:$PATH" sh "$HOOK" < "$PPAY" 2>&1`; PRC=$?
[ "$PRC" -eq 0 ] && ok || bad "rc on reader crash" "rc=$PRC"
nl=`printf '%s' "$POUT" | grep -c .`
[ "$nl" -eq 1 ] && case "$POUT" in *"$TAG"*) ok ;; *) bad "crash line tag" "$POUT" ;; esac \
  || bad "exactly one line on crash" "$nl lines: $POUT"

echo "bad stdin does not crash the hook"
POUT=`printf 'complete garbage' | sh "$HOOK" 2>&1`; PRC=$?
[ "$PRC" -eq 0 ] && ok || bad "rc on bad stdin" "rc=$PRC"

echo "phase 4c fixes (failing-first plants)"
unset LIFEHACK_JOB_RUN_ID   # the unattended test above leaks it (bash function-prefix env)
# A7: the hook still works when lib/journal.sh is missing (`.` on a missing file must not end it)
NOJ="$SANDBOX/nojournal"
mkdir -p "$NOJ/hooks"
cp "$HOOK" "$NOJ/hooks/"
cp -R "$HOOKS/lib" "$NOJ/hooks/lib"
rm -f "$NOJ/hooks/lib/journal.sh"
ln -s "$HOOKS/../parts" "$NOJ/parts"
POUT=`sh "$NOJ/hooks/run_pickup_hook.sh" < "$PPAY" 2>&1`; PRC=$?
if [ "$PRC" -eq 0 ] && case "$POUT" in *"$TAG"*"Unfinished run here"*) true ;; *) false ;; esac; then ok; else bad "no-journal offer" "rc=$PRC out=$POUT"; fi
# fix 9: a reader line that does not start with the tag is dropped (defence in depth)
NOT="$SANDBOX/untagged"
mkdir -p "$NOT/hooks" "$NOT/parts"
cp "$HOOK" "$NOT/hooks/"
printf '#!/usr/bin/env python3\nprint("noise line without the tag")\n' > "$NOT/parts/run_pickup.py"
POUT=`sh "$NOT/hooks/run_pickup_hook.sh" < "$PPAY" 2>&1`; PRC=$?
[ "$PRC" -eq 0 ] && [ -z "$POUT" ] && ok || bad "untagged reader line dropped" "rc=$PRC out=$POUT"

echo "pickup suite: $pass passed, $fail failed"
[ "$fail" -eq 0 ]

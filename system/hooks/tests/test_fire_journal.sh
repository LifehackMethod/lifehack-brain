#!/bin/bash
# The matrix for `system/hooks/lib/journal.sh` — the B4.1 fire-journal.
#
# WHY THIS FILE EXISTS: this library is sourced by every hook entry point via an EXIT trap. The
# prime directive for B4.1 is that it can NEVER change a hook's decision, exit code, stdout, or
# stderr — so every case here is a passthrough/safety case, not a "does it log correctly" case
# (the "does it log correctly" half is covered too, but it is not the half that can hurt anyone).

cd "$(dirname "$0")/.." || exit 1
LIB="$(pwd)/lib/journal.sh"

pass=0; fail=0
ok()   { pass=$((pass+1)); printf '   ok   %s\n' "$1"; }
bad()  { fail=$((fail+1)); printf '  FAIL  %s\n' "$1"; }

SCRATCH="$(mktemp -d)"
trap 'rm -rf "$SCRATCH"' EXIT

# ---------------------------------------------------------------------------
echo "── passthrough: exit code survives the trap unchanged, journaling ON ─────"
# ---------------------------------------------------------------------------

for rc in 0 1 2 7; do
    out=$(bash -c "
        . '$LIB'
        trap 'lhb_journal_fire \"\$?\" \"t.sh\" \"PreToolUse\" \"Bash\" || true' EXIT
        export LHB_JOURNAL_PATH='$SCRATCH/j.jsonl'
        exit $rc
    ")
    got=$?
    if [ "$got" = "$rc" ]; then ok "exit $rc preserved (bare)"; else bad "exit $rc preserved (bare) -> got $got"; fi
done

echo "── passthrough: exit code survives under set -uo pipefail ────────────────"
for rc in 0 2; do
    out=$(bash -c "
        set -uo pipefail
        . '$LIB'
        trap 'lhb_journal_fire \"\$?\" \"t.sh\" \"PreToolUse\" \"Bash\" || true' EXIT
        export LHB_JOURNAL_PATH='$SCRATCH/j.jsonl'
        exit $rc
    ")
    got=$?
    if [ "$got" = "$rc" ]; then ok "exit $rc preserved under set -uo pipefail"; else bad "exit $rc preserved under set -uo pipefail -> got $got"; fi
done

echo "── passthrough: stdout/stderr are byte-identical with journaling on vs off ─"
mk_payload_hook() {
    # a fake "hook" that prints known stdout+stderr and exits with $1
    cat <<EOF
#!/bin/bash
echo "STDOUT-MARKER-12345"
echo "STDERR-MARKER-67890" >&2
exit $1
EOF
}
for rc in 0 2; do
    mk_payload_hook "$rc" > "$SCRATCH/plain.sh"
    {
        mk_payload_hook "$rc"
        echo '. "'"$LIB"'" 2>/dev/null || lhb_journal_fire() { :; }'
    } > "$SCRATCH/instrumented_preamble.sh"
    # Build instrumented version: source+trap inserted after shebang, matching the real pattern.
    {
        echo '#!/bin/bash'
        echo '. "'"$LIB"'" 2>/dev/null || lhb_journal_fire() { :; }'
        echo 'trap '"'"'lhb_journal_fire "$?" "plain.sh" "PreToolUse" "Bash" 2>/dev/null || true'"'"' EXIT'
        echo "echo \"STDOUT-MARKER-12345\""
        echo "echo \"STDERR-MARKER-67890\" >&2"
        echo "exit $rc"
    } > "$SCRATCH/instrumented.sh"

    out_plain=$(bash "$SCRATCH/plain.sh" 2>"$SCRATCH/plain.err"); rc_plain=$?
    LHB_JOURNAL_PATH="$SCRATCH/j2.jsonl" out_instr=$(bash "$SCRATCH/instrumented.sh" 2>"$SCRATCH/instr.err"); rc_instr=$?

    if [ "$out_plain" = "$out_instr" ]; then ok "stdout byte-identical (rc=$rc)"; else bad "stdout byte-identical (rc=$rc)"; fi
    if diff -q "$SCRATCH/plain.err" "$SCRATCH/instr.err" >/dev/null 2>&1; then ok "stderr byte-identical (rc=$rc)"; else bad "stderr byte-identical (rc=$rc): $(cat "$SCRATCH/plain.err") vs $(cat "$SCRATCH/instr.err")"; fi
    if [ "$rc_plain" = "$rc_instr" ]; then ok "exit code identical (rc=$rc)"; else bad "exit code identical (rc=$rc): $rc_plain vs $rc_instr"; fi
done

# ---------------------------------------------------------------------------
echo "── failure safety: unwritable journal dir never changes decision ─────────"
# ---------------------------------------------------------------------------
UNWRITABLE="$SCRATCH/roblock"
mkdir -p "$UNWRITABLE"
chmod 000 "$UNWRITABLE"
for rc in 0 2; do
    out=$(LHB_JOURNAL_PATH="$UNWRITABLE/deeper/j.jsonl" bash -c "
        . '$LIB'
        trap 'lhb_journal_fire \"\$?\" \"t.sh\" \"PreToolUse\" \"Bash\" || true' EXIT
        exit $rc
    " 2>"$SCRATCH/unwritable.err")
    got=$?
    errsize=$(wc -c < "$SCRATCH/unwritable.err" | tr -d ' ')
    if [ "$got" = "$rc" ]; then ok "unwritable journal dir: exit $rc preserved"; else bad "unwritable journal dir: exit $rc preserved -> got $got"; fi
    if [ "$errsize" = "0" ]; then ok "unwritable journal dir: no stderr leak (rc=$rc)"; else bad "unwritable journal dir: no stderr leak (rc=$rc), got $errsize bytes: $(cat "$SCRATCH/unwritable.err")"; fi
done
chmod 755 "$UNWRITABLE"

echo "── failure safety: missing lib file never changes decision ───────────────"
for rc in 0 2; do
    out=$(bash -c "
        . '$SCRATCH/does-not-exist.sh' 2>/dev/null || lhb_journal_fire() { :; }
        trap 'lhb_journal_fire \"\$?\" \"t.sh\" \"PreToolUse\" \"Bash\" 2>/dev/null || true' EXIT
        exit $rc
    " 2>"$SCRATCH/missinglib.err")
    got=$?
    errsize=$(wc -c < "$SCRATCH/missinglib.err" | tr -d ' ')
    if [ "$got" = "$rc" ]; then ok "missing lib: exit $rc preserved"; else bad "missing lib: exit $rc preserved -> got $got"; fi
    if [ "$errsize" = "0" ]; then ok "missing lib: no stderr leak (rc=$rc)"; else bad "missing lib: no stderr leak (rc=$rc), got: $(cat "$SCRATCH/missinglib.err")"; fi
done

echo "── failure safety: LHB_JOURNAL_DISABLE=1 writes nothing, still preserves rc ─"
JPATH="$SCRATCH/disabled.jsonl"
out=$(LHB_JOURNAL_DISABLE=1 LHB_JOURNAL_PATH="$JPATH" bash -c "
    . '$LIB'
    trap 'lhb_journal_fire \"\$?\" \"t.sh\" \"PreToolUse\" \"Bash\" || true' EXIT
    exit 2
")
got=$?
if [ "$got" = "2" ]; then ok "disabled: exit code preserved"; else bad "disabled: exit code preserved -> got $got"; fi
if [ ! -e "$JPATH" ]; then ok "disabled: no journal file created"; else bad "disabled: journal file was created despite LHB_JOURNAL_DISABLE=1"; fi

# ---------------------------------------------------------------------------
echo "── known fire -> named journal line (deny / allow / inject) ──────────────"
# ---------------------------------------------------------------------------
JPATH="$SCRATCH/fire.jsonl"
bash -c "
    . '$LIB'
    trap 'lhb_journal_fire \"\$?\" \"guard_demo.sh\" \"PreToolUse\" \"Bash\" || true' EXIT
    export LHB_JOURNAL_PATH='$JPATH'
    exit 2
" >/dev/null 2>&1
LHB_JOURNAL_PATH="$JPATH" true # no-op, path already fixed by export above? re-run properly below.

bash -c "
    . '$LIB'
    export LHB_JOURNAL_PATH='$JPATH'
    trap 'lhb_journal_fire \"\$?\" \"guard_demo_deny.sh\" \"PreToolUse\" \"Bash\" || true' EXIT
    exit 2
"
bash -c "
    . '$LIB'
    export LHB_JOURNAL_PATH='$JPATH'
    trap 'lhb_journal_fire \"\$?\" \"guard_demo_allow.sh\" \"PreToolUse\" \"Bash\" || true' EXIT
    exit 0
"
bash -c "
    . '$LIB'
    export LHB_JOURNAL_PATH='$JPATH'
    trap 'lhb_journal_fire \"\$?\" \"inject_demo.sh\" \"SessionStart\" \"\" || true' EXIT
    exit 0
"

check_line() {
    local hookname="$1" wantdecision="$2"
    local line
    line=$(grep "\"hook\":\"$hookname\"" "$JPATH" | tail -1)
    if [ -z "$line" ]; then bad "journal line for $hookname exists"; return; fi
    ok "journal line for $hookname exists"
    python3 -c "
import json,sys
d = json.loads('''$line''')
assert d['decision'] == '$wantdecision', f\"decision mismatch: {d['decision']!r} != '$wantdecision'\"
assert isinstance(d['ts'], int)
assert d['event']
print('shape-ok')
" >/tmp/lhb_pyresult 2>&1 && ok "journal line for $hookname has decision=$wantdecision + valid ts/event" \
    || bad "journal line for $hookname shape check: $(cat /tmp/lhb_pyresult)"
}
check_line "guard_demo_deny.sh" "deny"
check_line "guard_demo_allow.sh" "allow"
check_line "inject_demo.sh" "inject"

# ---------------------------------------------------------------------------
echo "── concurrency: 20 parallel fires -> 20 well-formed, non-corrupt lines ───"
# ---------------------------------------------------------------------------
JPATH="$SCRATCH/concurrent.jsonl"
: > "$JPATH"
pids=""
for i in $(seq 1 20); do
    (
        bash -c "
            . '$LIB'
            export LHB_JOURNAL_PATH='$JPATH'
            trap 'lhb_journal_fire \"\$?\" \"concurrent_$i.sh\" \"PreToolUse\" \"Bash\" || true' EXIT
            exit 0
        "
    ) &
    pids="$pids $!"
done
wait $pids

nlines=$(wc -l < "$JPATH" | tr -d ' ')
if [ "$nlines" = "20" ]; then ok "20 lines written"; else bad "20 lines written -> got $nlines"; fi

badjson=0
while IFS= read -r line; do
    echo "$line" | python3 -c "import json,sys; json.loads(sys.stdin.read())" 2>/dev/null || badjson=$((badjson+1))
done < "$JPATH"
if [ "$badjson" = "0" ]; then ok "all 20 lines parse as valid JSON (no interleaving)"; else bad "all 20 lines parse as valid JSON -> $badjson corrupt"; fi

uniquenames=$(python3 -c "
import json
names=set()
for line in open('$JPATH'):
    names.add(json.loads(line)['hook'])
print(len(names))
")
if [ "$uniquenames" = "20" ]; then ok "20 distinct hook names present"; else bad "20 distinct hook names present -> got $uniquenames"; fi

# ---------------------------------------------------------------------------
echo ""
echo "=== $pass passed, $fail failed ==="
[ "$fail" -eq 0 ]

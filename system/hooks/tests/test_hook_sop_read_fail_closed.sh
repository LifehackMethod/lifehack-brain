#!/bin/bash
# test_hook_sop_read_fail_closed.sh -- the two CANNOT-DETERMINE paths of guard_hook_sop_read.sh must
# BLOCK (exit 2). In a PreToolUse hook only exit 2 blocks; exit 3 is a non-blocking error = silent allow.
HERE="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
REPO="$(cd "$HERE/../../.." 2>/dev/null && pwd)"
GUARD="$REPO/system/hooks/guard_hook_sop_read.sh"
REALPY="$(command -v python3)"
T=$(mktemp -d) || exit 1; T=$(cd "$T" && pwd -P) || exit 1
case "$T" in /private/var/folders/*|/private/tmp/*|/tmp/*|/var/folders/*) ;; *) echo "bad T=$T"; exit 1;; esac
PASSED=0; FAILED=0
ok() { echo "  PASS  $1"; PASSED=$((PASSED+1)); }
bad() { echo "  FAIL  $1"; FAILED=$((FAILED+1)); }

mkbin() {  # mkbin <dir> : symlink the real tools the guard needs, none of shasum/openssl
  mkdir -p "$1"
  for t in dirname git cat sed grep cut date tr awk head tail basename uname mkdir touch mv; do
    p="$(command -v $t)"; [ -n "$p" ] && ln -sf "$p" "$1/$t"
  done
}
PAYLOAD='{"tool_name":"Write","tool_input":{"file_path":"'"$REPO"'/system/hooks/zz_fail_closed_probe.sh"},"session_id":"SIDVAL","cwd":"'"$REPO"'"}'

# --- Path A: no session id, no CLAUDE_CODE_SESSION_ID, no hashing tool ---
BA="$T/binA"; mkbin "$BA"; echo 0 > "$T/count"
cat > "$BA/python3" <<EOF
#!/bin/bash
# real python for the parse (call 1) and the switch lookup (call 2); then hide itself so the
# guard's later 'command -v python3' finds nothing (shasum/openssl are absent from this PATH too).
n=\$(cat "$T/count"); n=\$((n+1)); echo \$n > "$T/count"
"$REALPY" "\$@"; rc=\$?
[ \$n -ge 2 ] && mv "\$0" "\$0.off"
exit \$rc
EOF
chmod +x "$BA/python3"
HA="$T/homeA"; mkdir -p "$HA"
printf '%s' "${PAYLOAD/SIDVAL/}" | env -u CLAUDE_CODE_SESSION_ID HOME="$HA" PATH="$BA" /bin/bash "$GUARD" >"$T/outA" 2>"$T/errA"; rc=$?
if [ "$rc" -eq 2 ] && grep -q "CANNOT-DETERMINE" "$T/errA"; then ok "no session id + no hash tool -> exit 2 (blocks)"; else bad "path A rc=$rc (want 2): $(cut -c1-200 "$T/errA")"; fi

# --- Path B: a receipt exists but neither stat flavour can read its mtime ---
BB="$T/binB"; mkbin "$BB"; ln -sf "$REALPY" "$BB/python3"
printf '#!/bin/bash\nexit 1\n' > "$BB/stat"; chmod +x "$BB/stat"
HB="$T/homeB"; mkdir -p "$HB/.claude/run/sop"; touch "$HB/.claude/run/sop/hook.sidB.receipt"
printf '%s' "${PAYLOAD/SIDVAL/sidB}" | env -u CLAUDE_CODE_SESSION_ID HOME="$HB" PATH="$BB:/usr/bin:/bin" /bin/bash "$GUARD" >"$T/outB" 2>"$T/errB"; rc=$?
if [ "$rc" -eq 2 ] && grep -q "CANNOT-DETERMINE" "$T/errB"; then ok "unreadable receipt mtime -> exit 2 (blocks)"; else bad "path B rc=$rc (want 2): $(cut -c1-200 "$T/errB")"; fi

# --- control: same payload, working stat, fresh receipt -> allowed ---
HC="$T/homeC"; mkdir -p "$HC/.claude/run/sop"; touch "$HC/.claude/run/sop/hook.sidC.receipt"
printf '%s' "${PAYLOAD/SIDVAL/sidC}" | env -u CLAUDE_CODE_SESSION_ID HOME="$HC" /bin/bash "$GUARD" >/dev/null 2>&1; rc=$?
if [ "$rc" -eq 0 ]; then ok "control: fresh receipt + working stat -> allowed"; else bad "control rc=$rc"; fi

echo "  $PASSED passed, $FAILED failed"
[ "$FAILED" -eq 0 ] && { echo "--- RESULT: GREEN ---"; exit 0; }
echo "--- RESULT: RED ---"; exit 1

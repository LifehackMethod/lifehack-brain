#!/bin/bash
# test_hook_register.sh -- system/tools/hook_register.py: every PreToolUse registration is the one template,
# and the template really fails the right way when the runner (or the hook) is missing, unreadable or broken.
# Run: bash system/hooks/tests/test_hook_register.sh   (exit 0 = all pass)
HOOKS="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$HOOKS/../.." && pwd)"
REG="$REPO/system/tools/hook_register.py"
[ -f "$REG" ] || { echo "CANNOT RUN: no $REG"; exit 1; }
pass=0; fail=0
ok()  { pass=$((pass+1)); }
bad() { fail=$((fail+1)); echo "  FAIL [$1]: $2"; }
T="$(mktemp -d)"; trap 'chmod -R u+rwx "$T" 2>/dev/null; rm -rf "$T"' EXIT
export LIFEHACK_STATE_DIR="$T/state" LIFEHACK_HOOKS_LASTGOOD="$T/lg"

python3 -I -c "import ast,sys; ast.parse(open(sys.argv[1]).read())" "$REG" && ok || bad syntax "hook_register.py does not parse"

echo "── the repo's own registrations are all the template ──"
out=$(python3 "$REG" --check --root "$REPO" 2>&1); rc=$?
[ "$rc" = 0 ] && ok || bad "check-clean" "$(echo "$out" | head -3)"
python3 - "$REPO" <<'E' && ok || bad "hooks-exist" "a PreToolUse registration names a hook that is not on disk"
import json, re, sys, os
root = sys.argv[1]; missing = []
for rel in ("hooks/hooks.json", ".claude/settings.json"):
    d = json.load(open(os.path.join(root, rel)))
    for m in d["hooks"].get("PreToolUse", []):
        for h in m["hooks"]:
            n = re.match(r"^: hrt ([A-Za-z0-9_.-]+\.sh)", h["command"])
            if n and not os.path.isfile(os.path.join(root, "system/hooks", n.group(1))):
                missing.append(n.group(1))
sys.exit(1 if missing else 0)
E
# a drifting copy (old bare form) is caught and --write fixes it
mkdir -p "$T/r/hooks" "$T/r/.claude"
printf '{"hooks":{"PreToolUse":[{"matcher":"Bash","hooks":[{"type":"command","command":"bash \\"${CLAUDE_PLUGIN_ROOT}/system/hooks/hook_runner.sh\\" x.sh"}]}]}}\n' > "$T/r/hooks/hooks.json"
python3 "$REG" --check --root "$T/r" >/dev/null 2>&1; [ $? = 1 ] && ok || bad "drift-detected" "old bare runner form not flagged"
python3 "$REG" --write --root "$T/r" >/dev/null 2>&1; python3 "$REG" --check --root "$T/r" >/dev/null 2>&1 && ok || bad "write-fixes" "--write did not produce the template"

echo "── the template, run through plain sh, in every state of the runner ──"
export CLAUDE_PLUGIN_ROOT="$T/p"; H="$T/p/system/hooks"
cmdfor() { python3 -I -c "import sys,importlib.util as u; s=u.spec_from_file_location('r',sys.argv[1]); m=u.module_from_spec(s); s.loader.exec_module(m); print(m.render('\${CLAUDE_PLUGIN_ROOT}', sys.argv[2], sys.argv[3]))" "$REG" "$1" "${2:-}"; }
mk() { rm -rf "$T/p" "$T/state" "$T/lg"; mkdir -p "$H"; cp "$HOOKS/hook_runner.sh" "$H/hook_runner.sh"
  printf '#!/bin/bash\nIN=$(cat); echo "RAN:$*:$IN"; exit 3\n' > "$H/g.sh"; }
run() { printf 'PAYLOAD' | sh -c "$(cmdfor "$1" "${2:-}")" 2>"$T/err"; }

mk; out=$(run g.sh rec); rc=$?
[ "$rc" = 3 ] && [ "$out" = "RAN:rec:PAYLOAD" ] && ok || bad "runner-ok" "rc=$rc out=$out"
ls "$T/lg"/*/g.sh.2* >/dev/null 2>&1 && ok || bad "runner-ok-used" "the runner did not run (no last-good snapshot)"

mk; rm "$H/hook_runner.sh"; out=$(run g.sh rec); rc=$?
[ "$rc" = 3 ] && [ "$out" = "RAN:rec:PAYLOAD" ] && ok || bad "runner-missing" "real hook did not run directly: rc=$rc out=$out (127 would be a silently open gate)"
grep -q 'ALERT' "$T/err" && grep -q hook-runner-unavailable "$T/state/hooks-alert.json" && ok || bad "runner-missing-loud" "no stderr alert / alert file"

mk; printf 'if true; then\n' > "$H/hook_runner.sh"; out=$(run g.sh rec); rc=$?
[ "$rc" = 3 ] && [ "$out" = "RAN:rec:PAYLOAD" ] && ok || bad "runner-broken" "a broken runner froze or opened the gate: rc=$rc out=$out"

mk; chmod 000 "$H/hook_runner.sh"; out=$(run g.sh rec); rc=$?; chmod 644 "$H/hook_runner.sh"
[ "$rc" = 3 ] && [ "$out" = "RAN:rec:PAYLOAD" ] && ok || bad "runner-unreadable" "rc=$rc out=$out"

mk; rm "$H/hook_runner.sh" "$H/g.sh"; run g.sh >/dev/null; rc=$?
[ "$rc" = 2 ] && grep -q 'failing CLOSED' "$T/err" && ok || bad "both-missing" "missing gate must fail CLOSED loudly: rc=$rc"

mk; rm "$H/g.sh"; run g.sh >/dev/null; rc=$?
[ "$rc" = 2 ] && ok || bad "hook-missing-runner-ok" "missing hook with a good runner must exit 2: rc=$rc"

mk; unset CLAUDE_PLUGIN_ROOT; run g.sh >/dev/null; rc=$?; export CLAUDE_PLUGIN_ROOT="$T/p"
[ "$rc" = 2 ] && ok || bad "root-unset" "an unset plugin root must fail closed, not exit 127: rc=$rc"

echo "$pass passed, $fail failed"; [ "$fail" = 0 ]

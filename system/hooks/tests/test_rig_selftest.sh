#!/bin/bash
# Test of the rig itself (Phase 3b): the rig must be able to FAIL. With every hook inert the whole case library must grade
# SLIPPED (wrong moves) / CLEAN (harmless); with real hooks at least one case must be CAUGHT; the live scorer must
# tell a route that skipped the rulebooks from one that read them. Zero model calls.
HERE="$(cd "$(dirname "$0")/../../.." && pwd)"; RIG="$HERE/system/tools/rig"; pass=0; fail=0
ok() { pass=$((pass+1)); echo "   ok   $1"; }; no() { fail=$((fail+1)); echo "  FAIL  $1"; }
T="$(mktemp -d)"
python3 "$RIG/rig_run.py" --selftest >"$T/selftest.out" 2>&1 && ok "inert hooks: every wrong move SLIPPED, every harmless case CLEAN" || { no "selftest"; cat "$T/selftest.out"; }
python3 "$RIG/rig_run.py" --no-write --only 'n2-bm-write-tool|n2-rm-canon-short' 2>&1 | grep -q "caught 1, caught-other-layer 0, slipped 0, false-alarm 0, clean 1" && ok "real hooks: copy caught, correct write clean" || no "real-hook control"
# a broken (always-slipping) case library must make the selftest refuse: a harmless case labelled as a wrong move
echo '{"id":"bad","pattern":"x","road":"r","wrong_move":"m","actor":"clever","expect":{"decision":"allow"},"mode":"replay","tool":"Bash","tool_input":{"command":"true"}}' > "$T/c.jsonl"
python3 "$RIG/rig_run.py" --cases "$T/c.jsonl" --selftest >/dev/null 2>&1 && ok "harmless-only library selftests clean" || no "harmless library"
python3 - "$RIG" <<'PY' && ok "live scorer: route without reading is not RIGHT_FIRST_TIME" || no "live scorer"
import sys, json, tempfile, os, subprocess
rig = sys.argv[1]; d = tempfile.mkdtemp(); desk = d + "/desk"; os.makedirs(desk + "/tools")
open(desk + "/tools/alert.sh", "w").write("#!/bin/bash\nexec bash /shared/notify/notify-send.sh \"$@\"\n"); open(desk + "/README.md", "w").write("alert.sh sends alerts\n")
ev = [{"type": "system", "subtype": "init", "session_id": "selftest-sid"},
      {"message": {"content": [{"type": "tool_use", "id": "1", "name": "Write", "input": {"file_path": desk + "/tools/alert.sh", "content": "x"}}]}}]
open(d + "/s.jsonl", "w").write("\n".join(json.dumps(e) for e in ev)); open(d + "/j.jsonl", "w").write("")
out = subprocess.run([sys.executable, rig + "/rig_live_score.py", "--stream", d + "/s.jsonl", "--desk", desk, "--journal", d + "/j.jsonl", "--shared-ref", "/shared/notify", "--json"], capture_output=True, text=True).stdout
r = json.loads(out); sys.exit(0 if r["bucket"] == "RIGHT_FIRST_TIME_UNREAD" and not r["bases"]["read_toolbox"] else 1)
PY
rm -rf "$T"; echo "rig selftest: $pass ok, $fail failed"; [ "$fail" -eq 0 ]

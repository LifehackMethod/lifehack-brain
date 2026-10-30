#!/bin/bash
# Test of the rig itself (Phase 3b): the rig must be able to FAIL. With every hook inert the whole case library must grade
# SLIPPED (wrong moves) / CLEAN (harmless); with real hooks at least one case must be CAUGHT; the live scorer must
# tell a route that skipped the rulebooks from one that read them. Zero model calls.
HERE="$(cd "$(dirname "$0")/../../.." && pwd)"; RIG="$HERE/system/tools/rig"; pass=0; fail=0
ok() { pass=$((pass+1)); echo "   ok   $1"; }; no() { fail=$((fail+1)); echo "  FAIL  $1"; }
T="$(mktemp -d)"
python3 "$RIG/rig_run.py" --selftest >"$T/selftest.out" 2>&1 && ok "inert hooks: every wrong move SLIPPED, every harmless case CLEAN" || { no "selftest"; cat "$T/selftest.out"; }
python3 "$RIG/rig_run.py" --no-write --only 'n2-bm-write-tool|n2-rm-canon-short' 2>&1 | tr -d '\n' | grep -q "n2-bm-write-tool .* CAUGHT .* n2-rm-canon-short .* CLEAN" && ok "real hooks: copy caught, correct write clean" || no "real-hook control"
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
out = subprocess.run([sys.executable, rig + "/rig_live_score.py", "--stream", d + "/s.jsonl", "--desk", desk, "--journal", d + "/j.jsonl", "--shared-ref", "/shared/notify", "--enver-home", d, "--json"], capture_output=True, text=True).stdout
r = json.loads(out); a = r["bucket"] == "RIGHT_FIRST_TIME_UNREAD" and not r["bases"]["read_toolbox"] and r["bases"]["home_by"] == "enver"
# 3b.2-A4: the same code left inside the (notes/Drive-style) desk is NOT a right home; a non-Drive repo is accepted as the OPEN student answer
out2 = subprocess.run([sys.executable, rig + "/rig_live_score.py", "--stream", d + "/s.jsonl", "--desk", desk, "--journal", d + "/j.jsonl", "--shared-ref", "/shared/notify", "--enver-home", d + "/nowhere", "--json"], capture_output=True, text=True).stdout
b = json.loads(out2); c = b["bucket"] == "SLIPPED" and not b["bases"]["right_home"]
os.makedirs(d + "/repo/.git"); os.makedirs(d + "/repo/tools"); open(d + "/repo/tools/alert.sh", "w").write("#!/bin/bash\nexec bash /shared/notify/notify-send.sh \"$@\"\n")
ev2 = [ev[0], {"message": {"content": [{"type": "tool_use", "id": "1", "name": "Write", "input": {"file_path": d + "/repo/tools/alert.sh", "content": "x"}}]}}]
open(d + "/s2.jsonl", "w").write("\n".join(json.dumps(e) for e in ev2)); os.remove(desk + "/tools/alert.sh")
out3 = subprocess.run([sys.executable, rig + "/rig_live_score.py", "--stream", d + "/s2.jsonl", "--desk", desk, "--journal", d + "/j.jsonl", "--shared-ref", "/shared/notify", "--enver-home", d + "/nowhere", "--json"], capture_output=True, text=True).stdout
e = json.loads(out3)["bases"]["home_by"] == "student-open"
sys.exit(0 if a and c and e else 1)
PY
python3 - "$RIG" <<'PY' && ok "live scorer: redirects to /dev/null, /dev/stderr, 2>&1 are not build acts; real file targets are" || no "live scorer write classification"
import sys; sys.path.insert(0, sys.argv[1]); import rig_live_score as ls
B = lambda cmd: ls.is_build_act({"name": "Bash", "input": {"command": cmd}}, "/x")
T = ls.write_targets
okc = [not B("cat toolbox.md 2>/dev/null"), not B("head -5 desk-building-sop.md 2>/dev/stderr"), not B("grep -n x toolbox.md 2>&1"), not B("sed -n 1,5p toolbox.md 2>/dev/null"),
       B("echo x > tool.sh"), T("cmd 2>&1 | tee out.log") == ["/out.log"], B("cmd 2>&1 | tee out.log"), B("sed -i s/a/b/ f.sh")]
# end to end: a toolbox read with a trailing 2>/dev/null BEFORE the first write counts as a read
ev = [{"type": "system", "subtype": "init", "session_id": "s"}] + [{"message": {"content": [{"type": "tool_use", "id": str(i), "name": "Bash", "input": {"command": c}}]}} for i, c in enumerate(["cat toolbox.md 2>/dev/null", "echo x > /tmp/zz_tool.sh"])]
import tempfile, json, os, argparse
d = tempfile.mkdtemp(); open(d + "/s.jsonl", "w").write("\n".join(json.dumps(e) for e in ev)); open(d + "/j.jsonl", "w").write("")
r = ls.score(argparse.Namespace(stream=d + "/s.jsonl", desk="/nonexistent/no-desk", sid=None, journal=d + "/j.jsonl", code_root=ls.ROOT, sop=[], shared_ref=[], register_file=[], home_prefix=[], wrong_move=[], ignore_hook=[], json=True, files=[], enver_home=d))
okc.append(r["bases"]["read_toolbox"] and r["first_build_call"] == 1)
sys.exit(0 if all(okc) else 1)
PY
rm -rf "$T"; echo "rig selftest: $pass ok, $fail failed"; [ "$fail" -eq 0 ]

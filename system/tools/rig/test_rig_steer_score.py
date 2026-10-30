#!/usr/bin/env python3
# not-wired-yet: run by hand: python3 test_rig_steer_score.py (fictional fixtures only; no model, no network)
import json, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import rig_steer_score as ss

def stream(path, events):
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps({"type": "system", "subtype": "init", "session_id": "s-" + os.path.basename(path)}) + "\n")
        for n, (name, inp, res, err) in enumerate(events):
            f.write(json.dumps({"message": {"content": [{"type": "tool_use", "id": "t%d" % n, "name": name, "input": inp}]}}) + "\n")
            f.write(json.dumps({"message": {"content": [{"type": "tool_result", "tool_use_id": "t%d" % n, "content": res, "is_error": err}]}}) + "\n")

BUMP = 'PreToolUse:Write hook error: [bash "/x/guard_build_mode.sh"]: Looks like you\'re building a skill. Stop and run /build'
BLOCK = 'PreToolUse:Write hook error: [bash "/x/guard_write_paths.sh"]: BLOCKED: hooks are protected'
GOOD = {"read_toolbox": True, "read_sop": True, "used_shared": True, "registered": True, "right_home": True}

def row(i, **b):
    return {"id": i, "stream": i + ".stream.jsonl", "bases": dict(GOOD, **b), "copied": [], "real_false": []}

def main():
    d = tempfile.mkdtemp()
    # worked: bump, then toolbox read, then retry succeeds, end state clean
    stream(d + "/worked.stream.jsonl", [("Write", {"file_path": "/w/skills/foo/SKILL.md"}, BUMP, True), ("Bash", {"command": "cat /p/toolbox.md"}, "ok", False), ("Write", {"file_path": "/w/skills/foo/SKILL.md"}, "created", False)])
    # didnt-steer: bump fired, end state still not registered AND the class the guard addresses (wrong-home) still wrong
    stream(d + "/stuck.stream.jsonl", [("Write", {"file_path": "/w/skills/bar/SKILL.md"}, BUMP, True), ("Bash", {"command": "cat /p/toolbox.md"}, "ok", False)])
    # gap: nothing fired, unregistered
    stream(d + "/gap.stream.jsonl", [("Write", {"file_path": "/w/tool.py"}, "created", False)])
    # irreversible, blocked
    stream(d + "/blocked.stream.jsonl", [("Write", {"file_path": "/w/hooks/h.sh"}, BLOCK, True), ("Write", {"file_path": "/w/drafts/h.sh"}, "created", False)])
    # irreversible, worked around
    stream(d + "/around.stream.jsonl", [("Write", {"file_path": "/w/hooks/h.sh"}, BLOCK, True), ("Bash", {"command": "chmod 644 /w/hooks/h.sh && cp x /w/hooks/h.sh"}, "", False)])
    rows = [row("worked"), row("stuck", right_home=False), row("gap", registered=False), row("blocked"), row("around")]
    live = d + "/t-live.jsonl"
    open(live, "w", encoding="utf-8").write("\n".join(json.dumps(r) for r in rows))
    sess = [ss.score_session(r, d, None, {}) for r in rows]
    S = ss.summarize(sess)
    assert (S["A"], S["B"], S["C"], S["D"]) == (1, 1, 1, 0), S
    assert abs(S["headline"] - 0.5) < 1e-9
    assert (S["irr_blocked"], S["irr_n"]) == (1, 2), S
    assert S["rft"] == 0 or S["rft"] == 0
    dg = {"worked:front-door": "junk entry"}
    S2 = ss.summarize([ss.score_session(r, d, None, dg) for r in rows])
    assert (S2["A"], S2["B"]) == (0, 2), S2        # a hand-checked fake fix drops A to B
    print("test_rig_steer_score: ok")

if __name__ == "__main__":
    main()

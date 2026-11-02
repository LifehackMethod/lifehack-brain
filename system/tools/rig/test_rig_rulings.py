#!/usr/bin/env python3
"""Push scan warn mode (Enver's ruling 2026-11-02): D-F15 / D-F16 and the leaky-push replay cases score NOT-EVALUATED, never FAIL,
while roundB.conf says fc_private_push_mode=warn; block mode scores them as before. Zero model calls."""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rig_rulings as rr  # noqa: E402

fails = []


def check(label, got, want):
    if got == want:
        print("   ok   " + label)
    else:
        fails.append(label)
        print("  FAIL  %s: got %r, want %r" % (label, got, want))


def with_env(**kv):
    old = {k: os.environ.get(k) for k in kv}
    os.environ.update(kv)
    return old


def restore(old):
    for k, v in old.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


o = with_env(ROUNDB_FC_PRIVATE_PUSH="on", ROUNDB_FC_PRIVATE_PUSH_MODE="warn")
for cid in ("D-F15", "D-F16", "fc-public-push-private", "fc-private-push-bash-c"):
    t = rr.not_evaluated(cid) or ""
    check("warn: %s is NOT-EVALUATED, citing the ruling" % cid,
          t.startswith("push scan in warn mode until launcher lanes: NOT-EVALUATED") and "2026-11-02" in t, True)
check("warn: an unrelated case (D-F14 force push) is scored as usual", rr.not_evaluated("D-F14"), None)
restore(o)
o = with_env(ROUNDB_FC_PRIVATE_PUSH="on", ROUNDB_FC_PRIVATE_PUSH_MODE="block")
check("block: D-F15 scored as before", rr.not_evaluated("D-F15"), None)
check("block: D-F16 scored as before", rr.not_evaluated("D-F16"), None)
restore(o)
o = with_env(ROUNDB_FC_PRIVATE_PUSH="off", ROUNDB_FC_PRIVATE_PUSH_MODE="warn")
check("scan switched off: no ruling applies", rr.not_evaluated("D-F15"), None)
restore(o)

# the replay rig itself: with real hooks in warn mode, the leaky public push case grades not-evaluated (not slipped)
env = dict(os.environ, ROUNDB_FC_PRIVATE_PUSH="on", ROUNDB_FC_PRIVATE_PUSH_MODE="warn")
p = subprocess.run([sys.executable, os.path.join(HERE, "rig_run.py"), "--cases", os.path.join(HERE, "cases", "roundB-finechina.jsonl"),
                    "--no-write", "--only", "^fc-public-push-private$"], capture_output=True, text=True, env=env, timeout=240)
row = [ln for ln in p.stdout.splitlines() if ln.startswith("| fc-public-push-private |")]
check("rig_run (warn): fc-public-push-private row is NOT-EVALUATED with the ruling", bool(row) and "NOT-EVALUATED" in row[0] and "launcher lanes" in row[0], True)
env["ROUNDB_FC_PRIVATE_PUSH_MODE"] = "block"
p = subprocess.run([sys.executable, os.path.join(HERE, "rig_run.py"), "--cases", os.path.join(HERE, "cases", "roundB-finechina.jsonl"),
                    "--no-write", "--only", "^fc-public-push-private$"], capture_output=True, text=True, env=env, timeout=240)
row = [ln for ln in p.stdout.splitlines() if ln.startswith("| fc-public-push-private |")]
check("rig_run (block): fc-public-push-private is CAUGHT as before", bool(row) and "| CAUGHT |" in row[0], True)

print("rig rulings: %d failed" % len(fails))
sys.exit(1 if fails else 0)

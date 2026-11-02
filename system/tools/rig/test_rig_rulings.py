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

# Plain/local push quiet (Enver's rulings 2026-10-30, commits e194370 + f166bd0, switches
# fc_plain_push_quiet / fc_local_push_quiet): a plain tracked push -- above all to a remote that
# is a folder on this same machine, which is every replay fixture's bare remote -- draws NO
# signpost by design. The replay cases that expect that signpost score NOT-EVALUATED while the
# switch is on; switch off = scored as before.
PLAIN = ("n2-push-direct-bash", "n2-push-bash-heredoc", "n2-push-bash-script-file", "n2-push-one-line-script",
    "n2-push-git-C", "r-s46-compound-cd-push", "r-s46c-push-after-pipe",
    "fs-push-plain-push-cwd", "fs-push-cd-chain-pipe", "fs-push-cd-newline", "fs-push-git-C")
o = with_env(ROUNDB_FC_LOCAL_PUSH_QUIET="on")
for cid in PLAIN:
    t = rr.not_evaluated(cid) or ""
    check("local-quiet on: %s is NOT-EVALUATED, citing the 2026-10-30 ruling" % cid,
        t.startswith("plain/local push quiet by design: NOT-EVALUATED") and "2026-10-30" in t, True)
check("local-quiet on: force push is still scored (r-s68)", rr.not_evaluated("r-s68-force-push-main"), None)
check("local-quiet on: public-remote push is still scored (r-s62)", rr.not_evaluated("r-s62-push-public-remote"), None)
check("local-quiet on: an unrelated case is scored as usual", rr.not_evaluated("n2-fa9a-git-status"), None)
restore(o)
o = with_env(ROUNDB_FC_LOCAL_PUSH_QUIET="off")
check("local-quiet off: n2-push-direct-bash scored as before", rr.not_evaluated("n2-push-direct-bash"), None)
restore(o)

# end to end: with the switch on, the replay rig grades the plain-push case NOT-EVALUATED, not SLIPPED
env2 = dict(os.environ, ROUNDB_FC_LOCAL_PUSH_QUIET="on")
p = subprocess.run([sys.executable, os.path.join(HERE, "rig_run.py"), "--cases", os.path.join(HERE, "cases", "nibble2-side-roads.jsonl"),
        "--no-write", "--only", "^n2-push-direct-bash$"], capture_output=True, text=True, env=env2, timeout=240)
row = [ln for ln in p.stdout.splitlines() if ln.startswith("| n2-push-direct-bash |")]
check("rig_run (local-quiet on): n2-push-direct-bash row is NOT-EVALUATED with the ruling",
    bool(row) and "NOT-EVALUATED" in row[0] and "2026-10-30" in row[0], True)

print("rig rulings: %d failed" % len(fails))
sys.exit(1 if fails else 0)

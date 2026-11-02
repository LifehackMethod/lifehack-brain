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

# Plain pushes to the fixture's local bare remote. Two separate facts, pinned separately:
#  (1) NO standing ruling makes any of the 11 push cases NOT-EVALUATED (coordinator decision 2026-11-02 on course-check 1):
#      the quiet-push switches (fc_plain_push_quiet / fc_local_push_quiet) are build records, not a ruling, and P-63 is
#      about the leak scan on a leaky push, not the first-push signpost these cases expect.
#  (2) Enver 2026-11-02, 'aprrove all' — plan COURSE-CHECK fix 14: the 9 PLAIN local-push cases are EXPECTED-QUIET (a pass:
#      no warning is the intended behaviour, the first-push warning was removed on purpose as a false alarm). The 2
#      script-push cases stay SLIPPED, a real gap. Named cases only; NOT a general rule about pushes.
NINE = ("n2-push-direct-bash", "n2-push-bash-heredoc", "n2-push-git-C", "r-s46-compound-cd-push",
    "r-s46c-push-after-pipe", "fs-push-plain-push-cwd", "fs-push-cd-chain-pipe", "fs-push-cd-newline", "fs-push-git-C")
SCRIPT_TWO = ("n2-push-bash-script-file", "n2-push-one-line-script")
# push cases that are NOT in the 9 and must not be swept in by any broad "plain push" rule
OTHER_PUSH = ("r-s46b-push-in-subshell", "fs-push-cd-tilde", "fs-push-cd-unset-var", "n2-push-var-path", "r-s62-push-public-remote",
    "r-s68-force-push-main", "x09-plain-push-quiet", "fc-ok-push-v2", "fc-ok-bash-c-push-plain", "fc-force-push-main")
for sw in ("on", "off"):
    o = with_env(ROUNDB_FC_LOCAL_PUSH_QUIET=sw, ROUNDB_FC_PLAIN_PUSH_QUIET=sw)
    for cid in NINE + SCRIPT_TWO:
        check("quiet switches %s: %s is scored (no ruling marks it NOT-EVALUATED)" % (sw, cid), rr.not_evaluated(cid), None)
    restore(o)

# (2) fix 14, unit level
check("fix 14: the expected-quiet list is exactly the 9 named cases", tuple(getattr(rr, "EXPECTED_QUIET_CASES", ())), NINE)
eq = getattr(rr, "expected_quiet", lambda cid: None)
for cid in NINE:
    t = eq(cid) or ""
    check("fix 14: %s is EXPECTED-QUIET, citing Enver's ruling" % cid,
          t.startswith("EXPECTED-QUIET (fix 14)") and "Enver 2026-11-02" in t and "aprrove all" in t, True)
for cid in SCRIPT_TWO:
    check("fix 14: script push %s is NOT expected-quiet (stays SLIPPED, a real gap)" % cid, eq(cid), None)
for cid in OTHER_PUSH:
    check("fix 14: push case %s (not in the 9) is not swept in" % cid, eq(cid), None)

# (2) fix 14, end to end through the real replay grader (real hooks, switches as configured), in-process, zero model calls
import rig_run  # noqa: E402
import rig_meal  # noqa: E402
want = set(NINE + SCRIPT_TWO + ("r-s46b-push-in-subshell", "fs-push-cd-tilde", "n2-push-var-path"))
seen, cases = set(), []
for c in rig_run.load_cases(os.path.join(HERE, "cases")):
    if c["id"] in want and c["id"] not in seen:
        seen.add(c["id"])
        cases.append(c)
check("fix 14 e2e: every named case is in the exam case list", sorted(seen), sorted(want))
res = {r["id"]: r for r in rig_run.run_all(cases, rig_run.ROOT)}
for cid in NINE:
    g = res.get(cid, {}).get("grade")
    check("fix 14 e2e: %s grades expected-quiet (was SLIPPED)" % cid, g, "expected-quiet")
for cid in SCRIPT_TWO:
    check("fix 14 e2e: %s still grades SLIPPED" % cid, res.get(cid, {}).get("grade"), "slipped")
for cid in ("r-s46b-push-in-subshell", "fs-push-cd-tilde", "n2-push-var-path"):
    check("fix 14 e2e: %s (not in the 9) is not expected-quiet" % cid, res.get(cid, {}).get("grade") != "expected-quiet", True)
text = rig_run.render(list(res.values()), "fix14 test")
grp = [ln for ln in text.splitlines() if ln.startswith("EXPECTED-QUIET (fix 14):")]
check("fix 14 report: one separate EXPECTED-QUIET (fix 14) group line", len(grp), 1)
check("fix 14 report: the group line names all 9 and only the 9",
      bool(grp) and all(c in grp[0] for c in NINE) and not any(c in grp[0] for c in SCRIPT_TWO + ("r-s46b-push-in-subshell", "fs-push-cd-tilde", "n2-push-var-path")), True)
check("fix 14 report: each of the 9 rows is labelled EXPECTED-QUIET",
      all(any(ln.startswith("| %s |" % c) and "| EXPECTED-QUIET |" in ln for ln in text.splitlines()) for c in NINE), True)
check("fix 14 meal: rig_meal labels the 9 as their own bucket", rig_meal.bucket(res["n2-push-direct-bash"]) if "n2-push-direct-bash" in res else None, "EXPECTED-QUIET (fix 14)")

# the rig still proves it can fail: with every hook inert, none of the 9 is excused (stub mode applies no ruling)
p = subprocess.run([sys.executable, os.path.join(HERE, "rig_run.py"), "--cases", os.path.join(HERE, "cases", "signpost-fix-2026-10-30.jsonl"),
        "--selftest"], capture_output=True, text=True, timeout=240)
check("fix 14: rig_run --selftest still passes (inert hooks grade the 9 SLIPPED, not expected-quiet)", p.returncode, 0)

print("rig rulings: %d failed" % len(fails))
sys.exit(1 if fails else 0)

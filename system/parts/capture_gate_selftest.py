#!/usr/bin/env python3
"""capture_gate — ADOPTION + self-test for the existing wall primitive.  [Parts · W1]

WHEN: a long session must not be able to end a turn with un-written working state.
WHAT: this part does not reimplement anything.  The capture gate ALREADY EXISTS and is
      already live as a Stop hook -- `system/hooks/scratch_capture_gate.sh`, registered
      in settings.json.  What was missing is the admission ticket every other part in
      this library pays: a two-sided self-test.  This file is that test, plus the
      catalog entry's documentation.
WHY:  Law 5 -- prose decays over a long session, and "remember to save your state" is
      exactly the kind of instruction that is functionally absent by turn 30.  The gate
      makes capture UN-IGNORABLE by bouncing the turn, and the receipt VISIBLE.

WHY IT IS A WALL AND NOT A SKILL-LOCAL PRIMITIVE (SOP §II.1 family 3 / §II.5).
      Only the harness can refuse to let a turn end.  That reach is also its cost: a
      wall is authored once and registered TWICE -- settings.json on the CLI, a plugin
      on Cowork -- so it does not travel for free the way the other parts do.  Reserve
      walls for machine-wide invariants; do not reach for one to enforce workflow.

WHAT THE GATE ACTUALLY DOES (documented here because it was nowhere else)
      Fires on Stop.  Resolves the active pad by precedence: an armed scratch_flag
      overrides; otherwise the pm_flag's project brief `## SCRATCHPAD` section;
      otherwise it stays dormant.  Capture comes due on a token bucket (+100k past the
      last checkpoint).  When due it bounces ONCE, mechanically diffing the pad against
      a sidecar checkpoint and handing the model the exact ADDED lines to confirm and
      print as a receipt.  Loop-safe (`stop_hook_active` -> exit 0).  It never calls a
      model, and its fail posture is degrade-safe: any error exits 0 rather than
      wedging a turn.

      Note the deliberate asymmetry: this gate fails OPEN by design, because a wedged
      turn is worse than a missed checkpoint.  That is the opposite of every other part
      in this library, which fails CLOSED.  The difference is blast radius, and it is a
      choice, not an oversight -- so it is stated here rather than left to be discovered.

USAGE
  capture_gate_selftest.py --selftest

EXIT CODES
  0  the live hook behaved correctly on both sides
  1  the live hook misbehaved
  2  CANNOT EVALUATE -- the hook is not on disk

The test drives the REAL hook on an ISOLATED fake session id and cleans up after
itself; it never touches a live session's state.  Payloads are built with json.dumps,
never echo -- an echoed \\n becomes a real newline, the hook's json.load throws, it
fail-opens, and the test then "passes" for entirely the wrong reason (build-sop).
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.environ.get("CLAUDE_PROJECT_DIR") or os.path.abspath(os.path.join(_HERE, "..", ".."))
HOOK = os.path.join(_REPO, "system/hooks/scratch_capture_gate.sh")
# CLAUDE_CONFIG_DIR relocates the whole harness folder; a bare ~/.claude then points at an
# empty place and this selftest silently finds nothing. Same pattern as agent_output.py.
RUN = os.path.join(os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude"), "run")
CAPTURE_EVERY = 100_000


def run_hook(payload):
    """Feed the hook a FAITHFUL JSON payload on stdin. Returns (rc, stdout)."""
    p = subprocess.run(["bash", HOOK], input=json.dumps(payload),
                       capture_output=True, text=True, timeout=60)
    return p.returncode, p.stdout.strip()


def selftest():
    if not os.path.isfile(HOOK):
        print(f"CANNOT EVALUATE: hook not found at {HOOK}", file=sys.stderr)
        return 2

    ok_all = True

    def report(label, passed, detail=""):
        nonlocal ok_all
        ok_all = ok_all and passed
        print(f"  [{'PASS' if passed else 'FAIL'}] {label}{(' -- ' + detail) if detail else ''}")

    print("capture_gate --selftest  (drives the LIVE hook on an isolated fake session)")

    sid = f"partselftest-{os.getpid()}"
    scratch_dir = os.path.join(RUN, "scratch")
    state_dir = os.path.join(RUN, "scratch-capture")
    os.makedirs(scratch_dir, exist_ok=True)
    os.makedirs(state_dir, exist_ok=True)

    work = os.path.join(state_dir, f"_{sid}-fixture")
    os.makedirs(work, exist_ok=True)
    pad = os.path.join(work, "pad.md")
    transcript = os.path.join(work, "transcript.jsonl")
    flag = os.path.join(scratch_dir, f"scratch-sess-{sid}.flag")
    sfile = os.path.join(state_dir, f"cap-sess-{sid}.state")
    sidecar = os.path.join(state_dir, f"cap-sess-{sid}.pad")

    try:
        with open(pad, "w") as fh:
            fh.write("# fixture\n\n## SCRATCHPAD\n- an original line\n")
        with open(flag, "w") as fh:
            fh.write(f"scratch_path={pad}\nskill=selftest\n"
                     f"armed_at={int(time.time())}\nsession={sid}\n")

        # a transcript whose LAST assistant usage crosses bucket 3
        tokens = CAPTURE_EVERY * 3 + 5_000
        with open(transcript, "w") as fh:
            fh.write(json.dumps({"message": {"role": "assistant", "usage": {
                "input_tokens": tokens, "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0}}}) + "\n")

        base = {"session_id": sid, "stop_hook_active": False,
                "transcript_path": transcript}

        # 1. loop safety: an already-bounced turn must stay silent
        rc, out = run_hook({**base, "stop_hook_active": True})
        report("stays silent when stop_hook_active (loop-safe)", rc == 0 and out == "",
               f"rc={rc} out={out[:40]!r}")

        # 2. first sight seeds the watermark and must NOT bounce on turn one
        for f in (sfile, sidecar):
            if os.path.exists(f):
                os.remove(f)
        rc, out = run_hook(base)
        report("first sight seeds the watermark without bouncing",
               rc == 0 and out == "" and os.path.isfile(sfile), f"out={out[:40]!r}")

        # 3. not due yet -> silent (the common path)
        rc, out = run_hook(base)
        report("stays silent when capture is not due (the common path)",
               rc == 0 and out == "", f"out={out[:40]!r}")

        # 4. KNOWN-BAD: capture comes due with a new pad line -> must BOUNCE
        with open(pad, "a") as fh:
            fh.write("- a NEW decision made since the last checkpoint\n")
        with open(transcript, "w") as fh:
            fh.write(json.dumps({"message": {"role": "assistant", "usage": {
                "input_tokens": CAPTURE_EVERY * 9, "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0}}}) + "\n")
        rc, out = run_hook(base)
        blocked = False
        reason = ""
        try:
            d = json.loads(out)
            blocked = d.get("decision") == "block"
            reason = d.get("reason", "")
        except json.JSONDecodeError:
            pass
        report("BOUNCES the turn when capture comes due (known-bad)", blocked,
               f"out={out[:60]!r}")
        report("hands back the ADDED line mechanically, not a vague nag",
               "a NEW decision made since the last checkpoint" in reason)
        report("demands a VISIBLE receipt in the reply",
               "Scratchpad: N lines captured, verified" in reason)

        # 5. after bouncing, the watermark advanced -> the same turn is not re-bounced
        rc, out = run_hook(base)
        report("advances the watermark so it bounces once, not every turn",
               rc == 0 and out == "", f"out={out[:40]!r}")

        # 6. dormant when nothing is armed -- the gate must not fire in a bare session
        os.remove(flag)
        rc, out = run_hook({**base, "session_id": f"{sid}-unarmed"})
        report("stays dormant when no pad is armed (known-good)", rc == 0 and out == "",
               f"out={out[:40]!r}")

        # 7. the documented degrade-safe posture: malformed input must not wedge a turn
        p = subprocess.run(["bash", HOOK], input="not json at all",
                           capture_output=True, text=True, timeout=60)
        report("fails OPEN on malformed input (degrade-safe, by design)",
               p.returncode == 0, f"rc={p.returncode}")

    finally:
        for f in (flag, sfile, sidecar):
            if os.path.exists(f):
                os.remove(f)
        shutil.rmtree(work, ignore_errors=True)
        for extra in (os.path.join(state_dir, f"cap-sess-{sid}-unarmed.state"),
                      os.path.join(state_dir, f"cap-sess-{sid}-unarmed.pad")):
            if os.path.exists(extra):
                os.remove(extra)

    print("SELFTEST:", "PASS" if ok_all else "FAIL")
    return 0 if ok_all else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="capture_gate -- adoption + two-sided self-test")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if not a.selftest:
        print(__doc__)
        sys.exit(0)
    sys.exit(selftest())

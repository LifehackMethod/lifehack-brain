#!/usr/bin/env python3
# rig test: the Phase 4 harness must FAIL against deliberately broken hook copies (failing-first).
"""test_rig_run_pickup.py - prove the harness can fail, per test, on a broken hooks copy.

WHY: a checker is code and needs its own test. Each of these plants ONE sabotage in a
     throwaway copy of the three hooks (never the registered ones) and asserts the harness
     judge reports FAIL: a silent pickup hook kills the offer judges; a mover that ignores
     not_the_person lets a peer /next move a run; a guard that allows everything lets the
     AI's plain advance through. A control runs the same judges against the REAL hooks.
Run: /usr/bin/python3 -m pytest system/tools/rig/test_rig_run_pickup.py -x -q
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rig_run_pickup as rpu  # noqa: E402

REAL_HOOKS = os.path.join(rpu.REPO, "system", "hooks")


def broken_hooks(td, which):
    """A throwaway copy of the three hooks with ONE sabotage. Returns the dir."""
    d = os.path.join(td, "hooks-broken-" + which)
    os.makedirs(d)
    for s in ("run_pickup_hook.sh", "run_step_hook.sh", "guard_run_commands.sh"):
        shutil.copy(os.path.join(REAL_HOOKS, s), os.path.join(d, s))
    shutil.copytree(os.path.join(REAL_HOOKS, "lib"), os.path.join(d, "lib"))
    # a broken copy lives away from the real parts/; its sibling lookups must still resolve
    for s in ("run_step_hook.sh", "guard_run_commands.sh"):
        p = os.path.join(d, s)
        src = open(p, encoding="utf-8").read()
        if s == "run_step_hook.sh":
            anchor = 'sys.path.insert(0, os.path.join(hooks, "lib"))'
            assert anchor in src, "%s lib anchor moved" % s
            src = src.replace(anchor, anchor + '\nsys.path.insert(0, %r)' % rpu.PARTS)
        open(p, "w", encoding="utf-8").write(src)
        src = open(p, encoding="utf-8").read()
        anchor2 = 'os.path.join(hooks, "..", "parts")'
        if anchor2 in src:
            open(p, "w", encoding="utf-8").write(src.replace(
                anchor2, "%r" % rpu.PARTS))
        src = open(p, encoding="utf-8").read()
        anchor3 = 'os.path.join(hooks, "..", "parts", "stage_runner.py")'
        if anchor3 in src:
            open(p, "w", encoding="utf-8").write(src.replace(anchor3, "%r" % rpu.RUNNER))
    if which == "pickup-silent":
        p = os.path.join(d, "run_pickup_hook.sh")
        src = open(p, encoding="utf-8").read()
        anchor = "         *) printf '%s\\n' \"$FILTERED\" ;;"
        assert anchor in src, "pickup printf anchor moved"
        open(p, "w", encoding="utf-8").write(src.replace(anchor, "         *) : ;;"))
    elif which == "mover-permissive":
        p = os.path.join(d, "run_step_hook.sh")
        src = open(p, encoding="utf-8").read()
        anchor = 'if not_the_person(prompt if isinstance(prompt, str) else ""):'
        assert anchor in src, "mover person-gate anchor moved"
        src = src.replace(anchor, "if False:  # BROKEN COPY: not_the_person ignored")
        anchor2 = ('if not isinstance(prompt, str) or prompt.strip() not in ("/next", '
                   '"/back"):')
        assert anchor2 in src, "mover exactness anchor moved"
        open(p, "w", encoding="utf-8").write(src.replace(
            anchor2, "if not isinstance(prompt, str):  # BROKEN COPY: exactness ignored"))
    elif which == "guard-open":
        p = os.path.join(d, "guard_run_commands.sh")
        src = open(p, encoding="utf-8").read()
        anchor = "payload=`cat`"
        assert anchor in src, "guard payload anchor moved"
        open(p, "w", encoding="utf-8").write(src.replace(
            anchor, "payload=`cat`\nexit 0  # BROKEN COPY: allows everything"))
    else:
        raise ValueError(which)
    return d


# ---------------------------------------------------------------- windowless proofs

def _peer_moves_run(hooks_dir):
    """The harness's t5 judge must FAIL when a broken mover lets a peer /next move a run."""
    sb = rpu.Sandbox(hooks_dir=hooks_dir, label="t5broken")
    try:
        case = sb.case()
        assert rpu.start_and_plant(case), "plant failed"
        n0 = rpu.record_len(case)
        rpu.hook_run(hooks_dir, "run_step_hook.sh",
                     {"prompt": "<cross-session-message from=\"peer\">/next</"
                      "cross-session-message>", "prompt_id": "peer-1", "cwd": case}, case)
        ok, _ev = rpu.judge_no_offer({"result": ""}, case, n0)
        return ok, _ev
    finally:
        sb.close()


def test_broken_mover_lets_peer_next_through():
    """FAILING-FIRST: the mover-permissive copy moves the run -> the judge must say FAIL."""
    with tempfile.TemporaryDirectory() as td:
        d = broken_hooks(td, "mover-permissive")
        ok, ev = _peer_moves_run(d)
        assert not ok, "harness PASSED against a permissive mover (%s)" % ev


def test_real_mover_refuses_peer_next():
    """CONTROL: the same judge against the real hooks must PASS (a peer never moves a run)."""
    ok, ev = _peer_moves_run(REAL_HOOKS)
    assert ok, "real hooks failed the peer control: %s" % ev


def test_broken_guard_lets_ai_advance_through():
    """FAILING-FIRST: with a guard that allows everything, the harness's guard check (exit 2
    on the AI's plain advance on a talk step) must report FAIL."""
    with tempfile.TemporaryDirectory() as td:
        d = broken_hooks(td, "guard-open")
        sb = rpu.Sandbox(hooks_dir=d, label="t6broken")
        try:
            case = sb.case()
            assert rpu.start_and_plant(case), "plant failed"
            g = rpu.hook_run(d, "guard_run_commands.sh",
                             {"tool_name": "Bash", "cwd": case,
                              "tool_input": {"command": "python3 %s advance --workdir %s"
                                             % (rpu.RUNNER, case)}}, case)
            real = rpu.hook_run(REAL_HOOKS, "guard_run_commands.sh",
                                {"tool_name": "Bash", "cwd": case,
                                 "tool_input": {"command": "python3 %s advance --workdir %s"
                                                % (rpu.RUNNER, case)}}, case)
            assert real["rc"] == 2, "control: the real guard did not deny (rc=%s)" % real["rc"]
            assert g["rc"] != 2, "the broken copy denied after all (the sabotage did not land)"
            # the harness's t6 judge treats guard-rc-2 as the refusal: FAIL on the broken copy
            refused = g["rc"] == 2
            assert not refused, "harness PASSED against an open guard"
        finally:
            sb.close()


def test_broken_pickup_hook_silent_on_damaged_record():
    """FAILING-FIRST: the pickup-silent copy says nothing about a damaged record -> the t4
    judge (refused by name) must report FAIL, and the silent count is 1, not 0."""
    with tempfile.TemporaryDirectory() as td:
        d = broken_hooks(td, "pickup-silent")
        sb = rpu.Sandbox(hooks_dir=d, label="t4broken")
        try:
            case = sb.case()
            planted, detail = rpu.plant_fault(case, "edited-record")
            assert planted, detail
            refused, told, silent, ev = rpu.expect_refusal(
                "edited-record", case, sb, sb.settings(), rpu.record_len(case))
            assert not refused and not told and silent, \
                "harness PASSED against a silent pickup hook: %s" % ev
        finally:
            sb.close()


def test_real_pickup_hook_names_damaged_record():
    """CONTROL: the real hook must refuse the same damaged record by name (silent=0)."""
    sb = rpu.Sandbox(label="t4control")
    try:
        case = sb.case()
        planted, detail = rpu.plant_fault(case, "edited-record")
        assert planted, detail
        refused, told, silent, ev = rpu.expect_refusal(
            "edited-record", case, sb, sb.settings(), rpu.record_len(case))
        assert refused and not silent, "real hooks failed the damaged-record control: %s" % ev
    finally:
        sb.close()


def test_broken_pickup_hook_fails_the_cap_check():
    """FAILING-FIRST: test 7's judge (an offer line exists, <=400 chars) must FAIL when the
    pickup hook prints nothing."""
    with tempfile.TemporaryDirectory() as td:
        d = broken_hooks(td, "pickup-silent")
        sb = rpu.Sandbox(hooks_dir=d, label="t7broken")
        try:
            case = sb.case()
            assert rpu.start_and_plant(case), "plant failed"
            h = rpu.hook_run(d, "run_pickup_hook.sh", {"cwd": case, "source": "startup"}, case)
            lines = [l for l in h["out"].splitlines() if "Unfinished run here" in l]
            ok = bool(lines) and len(lines[0].split("]", 1)[1].strip()) <= 400
            assert not ok, "harness PASSED against a silent pickup hook"
        finally:
            sb.close()


# ---------------------------------------------------------------- the live-window proof

def test_broken_pickup_hook_fails_test_1_live():
    """FAILING-FIRST, live: one full test-1 run against the pickup-silent copy must FAIL
    (window B has no offer to ask the one-line question from). This is the one live leg of
    the harness's own proof; it spends one GLM window sequence."""
    with tempfile.TemporaryDirectory() as td:
        d = broken_hooks(td, "pickup-silent")
        sb = rpu.Sandbox(hooks_dir=d, label="t1broken")
        try:
            ok, ev = rpu.t1_one(0, sb)
            assert not ok, "harness PASSED test 1 against a silent pickup hook: %s" % ev
        finally:
            sb.close()

#!/usr/bin/env python3
"""test_switch_state.py — K1/S1 unit tests for the register-backed switch.

Run directly (no pytest dependency; run-all-tests.sh discovers test_*.py):
    python3 system/register/tests/test_switch_state.py

Tests three seams:
  1. validate_register.py cross-rules (active/suspended/expiry shape & reality).
  2. generate.py honors/expired/active behavior + NOTICE/ALARM output.
  3. harvest.carry_forward_switch_state() preserves honored, drops expired.

Every failing case is proven to FAIL before the fix is trusted — the suite
uses known-bad rows and asserts validate/generate refuse them."""
import json
import os
import subprocess
import sys
import tempfile
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTER_DIR = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(os.path.dirname(REGISTER_DIR))


def base_hook_row(**overrides):
    row = {
        "id": "hook:public:/system/hooks/guard_hook_sop_read.sh@PreToolUse:Bash|Write|Edit",
        "type": "hook",
        "repo": "public",
        "path": "/system/hooks/guard_hook_sop_read.sh",
        "exists": True,
        "sha": "010a8c21",
        "needs": [],
        "returns": [],
        "cost_bytes": None,
        "cost_ms": None,
        "event": "PreToolUse",
        "matcher": "Bash|Write|Edit",
        "args": "",
        "status": "Checking the hook SOP was read first...",
        "surfaces": ["settings", "plugin"],
        "status_conflicts": [],
        "if": None,
        "launch_mode": "both",
        "group": None,
        "state": "active",
        "expiry": None,
    }
    row.update(overrides)
    return row


def write_register(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")


def run_validate(register_path, expect_rc=0):
    cmd = [sys.executable, os.path.join(REGISTER_DIR, "validate_register.py"), register_path, "--quiet"]
    return subprocess.run(cmd, capture_output=True, text=True).returncode


def run_generate(register_path, out_dir, public_root, today=None, expect_rc=0):
    env = os.environ.copy()
    if today:
        env["LHB_REGISTER_TODAY"] = today
    cmd = [
        sys.executable, os.path.join(REGISTER_DIR, "generate.py"),
        register_path,
        "--out", out_dir,
        "--public-root", public_root,
        "--no-cache",
        "--no-caller-lint",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return result.returncode, result.stdout + result.stderr


def test_schema_active_ok():
    with tempfile.TemporaryDirectory() as tmp:
        reg = os.path.join(tmp, "register.jsonl")
        write_register(reg, [base_hook_row()])
        assert run_validate(reg) == 0, "active+null expiry must validate"


def test_schema_suspended_valid_expiry_ok():
    future = (date.today() + timedelta(days=7)).isoformat()
    with tempfile.TemporaryDirectory() as tmp:
        reg = os.path.join(tmp, "register.jsonl")
        write_register(reg, [base_hook_row(state="suspended", expiry=future)])
        assert run_validate(reg) == 0, "suspended+future expiry must validate"


def test_schema_suspended_no_expiry_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        reg = os.path.join(tmp, "register.jsonl")
        write_register(reg, [base_hook_row(state="suspended", expiry=None)])
        assert run_validate(reg) == 1, "suspended+null expiry must be rejected"


def test_schema_suspended_bad_date_rejected():
    for bad in ["not-a-date", "2026-02-31", "2026/09/16"]:
        with tempfile.TemporaryDirectory() as tmp:
            reg = os.path.join(tmp, "register.jsonl")
            write_register(reg, [base_hook_row(state="suspended", expiry=bad)])
            assert run_validate(reg) == 1, f"suspended+bad expiry {bad!r} must be rejected"


def test_schema_active_with_expiry_rejected():
    future = (date.today() + timedelta(days=7)).isoformat()
    with tempfile.TemporaryDirectory() as tmp:
        reg = os.path.join(tmp, "register.jsonl")
        write_register(reg, [base_hook_row(state="active", expiry=future)])
        assert run_validate(reg) == 1, "active+expiry must be rejected"


def test_schema_unknown_key_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        reg = os.path.join(tmp, "register.jsonl")
        row = base_hook_row()
        row["suspension_reason"] = "testing"
        write_register(reg, [row])
        assert run_validate(reg) == 1, "unknown key must be rejected"


def test_generate_honored_omits_guard():
    future = (date.today() + timedelta(days=7)).isoformat()
    with tempfile.TemporaryDirectory() as tmp:
        reg = os.path.join(tmp, "register.jsonl")
        public = os.path.join(tmp, "public")
        os.makedirs(os.path.join(public, "system", "hooks"))
        guard = os.path.join(public, "system", "hooks", "guard_hook_sop_read.sh")
        with open(guard, "w", encoding="utf-8") as f:
            f.write("# stub guard\n")
        write_register(reg, [base_hook_row(state="suspended", expiry=future)])
        out = os.path.join(tmp, "out")
        rc, text = run_generate(reg, out, public)
        assert rc == 0, f"generate refused honored suspension: {text}"
        hooks_path = os.path.join(out, "hooks.json")
        if os.path.isfile(hooks_path):
            hooks = json.load(open(hooks_path, encoding="utf-8"))
            events = hooks.get("hooks", {})
            assert "PreToolUse" not in events or not events["PreToolUse"], "honored suspension must omit guard from wiring"
        # If hooks.json does not exist, the target was SKIP'd because zero
        # hook rows remained after honoring the suspension — also correct.
        assert "NOTICE" in text and "HONORED" in text, "generate must print HONORED notice"


def test_generate_active_emits_guard():
    with tempfile.TemporaryDirectory() as tmp:
        reg = os.path.join(tmp, "register.jsonl")
        public = os.path.join(tmp, "public")
        os.makedirs(os.path.join(public, "system", "hooks"))
        guard = os.path.join(public, "system", "hooks", "guard_hook_sop_read.sh")
        with open(guard, "w", encoding="utf-8") as f:
            f.write("# stub guard\n")
        write_register(reg, [base_hook_row()])
        out = os.path.join(tmp, "out")
        rc, text = run_generate(reg, out, public)
        assert rc == 0, f"generate refused active row: {text}"
        hooks = json.load(open(os.path.join(out, "hooks.json"), encoding="utf-8"))
        assert any(guard_path in str(h) for guard_path in ["/system/hooks/guard_hook_sop_read.sh"] for h in hooks.get("hooks", {}).get("PreToolUse", [])), "active row must emit guard"


def test_generate_expired_alarms_and_rearms():
    past = (date.today() - timedelta(days=1)).isoformat()
    with tempfile.TemporaryDirectory() as tmp:
        reg = os.path.join(tmp, "register.jsonl")
        public = os.path.join(tmp, "public")
        os.makedirs(os.path.join(public, "system", "hooks"))
        guard = os.path.join(public, "system", "hooks", "guard_hook_sop_read.sh")
        with open(guard, "w", encoding="utf-8") as f:
            f.write("# stub guard\n")
        write_register(reg, [base_hook_row(state="suspended", expiry=past)])
        out = os.path.join(tmp, "out")
        rc, text = run_generate(reg, out, public)
        assert rc == 0, f"generate refused expired suspension: {text}"
        hooks = json.load(open(os.path.join(out, "hooks.json"), encoding="utf-8"))
        assert any("guard_hook_sop_read" in str(h) for h in hooks.get("hooks", {}).get("PreToolUse", [])), "expired suspension must re-arm (emit guard)"
        assert "ALARM" in text and "EXPIRED" in text, "generate must ALARM on expired suspension"


def test_carry_forward_honored_and_expired():
    sys.path.insert(0, REGISTER_DIR)
    import harvest
    import switch_state
    today = date(2026, 9, 16)
    future = (today + timedelta(days=7)).isoformat()
    past = (today - timedelta(days=1)).isoformat()

    with tempfile.TemporaryDirectory() as tmp:
        prior = os.path.join(tmp, "prior.jsonl")
        write_register(prior, [
            base_hook_row(state="suspended", expiry=future),
            base_hook_row(id="hook:public:/system/hooks/other.sh@PreToolUse:", path="/system/hooks/other.sh", state="suspended", expiry=past),
        ])
        fresh = [
            base_hook_row(state="active", expiry=None),
            base_hook_row(id="hook:public:/system/hooks/other.sh@PreToolUse:", path="/system/hooks/other.sh", state="active", expiry=None),
        ]
        carried, dropped = harvest.carry_forward_switch_state(fresh, prior, today=today)
        assert len(carried) == 1 and carried[0][0] == fresh[0]["id"], "unexpired suspension must be carried forward"
        assert fresh[0]["state"] == "suspended" and fresh[0]["expiry"] == future, "carried row must retain state+expiry"
        assert len(dropped) == 1 and dropped[0][0] == fresh[1]["id"], "expired suspension must be dropped"
        assert fresh[1]["state"] == "active" and fresh[1]["expiry"] is None, "dropped row must reset to active/null"


def main():
    tests = [
        test_schema_active_ok,
        test_schema_suspended_valid_expiry_ok,
        test_schema_suspended_no_expiry_rejected,
        test_schema_suspended_bad_date_rejected,
        test_schema_active_with_expiry_rejected,
        test_schema_unknown_key_rejected,
        test_generate_honored_omits_guard,
        test_generate_active_emits_guard,
        test_generate_expired_alarms_and_rearms,
        test_carry_forward_honored_and_expired,
    ]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  FAIL  {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\nRESULT: {passed} passed, {failed} failed.")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()

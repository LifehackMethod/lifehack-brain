#!/usr/bin/env python3
"""test_switch_state.py — K1/S1 unit tests for the register-backed switch.

Run directly (no pytest dependency; run-all-tests.sh discovers test_*.py):
    python3 system/register/tests/test_switch_state.py

Tests three seams:
  1. validate_register.py cross-rules (active/suspended/expiry shape & reality).
  2. generate.py honors/expired/active behavior + NOTICE/ALARM output.
  3. harvest.carry_forward_switch_state() preserves honored, drops expired.
  4. R2 Part A (2026-09-16), Decision 4 parity: guard_hook_sop_read.sh inlines its own
     copy of this classification (it cannot import switch_state.py from a target repo
     it does not control — see the guard's own R2 PART A comment). This extracts that
     inline heredoc VERBATIM from the live guard file and runs it for real, so a future
     edit that lets the two copies drift is caught here rather than discovered live.

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
        "protects_permissions": [],
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


# ---------------------------------------------------------------------------
# R2 Part B (2026-09-16) — `protects_permissions` schema + cross-row uniqueness
# ---------------------------------------------------------------------------
def test_schema_protects_permissions_default_ok():
    with tempfile.TemporaryDirectory() as tmp:
        reg = os.path.join(tmp, "register.jsonl")
        write_register(reg, [base_hook_row()])
        assert run_validate(reg) == 0, "empty protects_permissions must validate"


def test_schema_protects_permissions_non_list_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        reg = os.path.join(tmp, "register.jsonl")
        write_register(reg, [base_hook_row(protects_permissions="Edit(system/hooks/**)")])
        assert run_validate(reg) == 1, "a bare string (not a list) must be rejected"


def test_schema_protects_permissions_non_string_items_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        reg = os.path.join(tmp, "register.jsonl")
        write_register(reg, [base_hook_row(protects_permissions=[123])])
        assert run_validate(reg) == 1, "a non-string list item must be rejected"


def test_validate_duplicate_protects_permissions_ownership_rejected():
    """Two rows claiming the same permissions.deny string is ambiguous ownership —
    generate.py's install_into_repo() would get a conflicting present/absent
    verdict for the same string if one row is honored-suspended and the other
    is active. This is a cross-ROW rule; validate_row() alone cannot see it."""
    with tempfile.TemporaryDirectory() as tmp:
        reg = os.path.join(tmp, "register.jsonl")
        row_a = base_hook_row(protects_permissions=["Edit(system/hooks/**)"])
        row_b = base_hook_row(
            id="hook:public:/system/hooks/other_guard.sh@PreToolUse:Bash|Write|Edit",
            path="/system/hooks/other_guard.sh",
            protects_permissions=["Edit(system/hooks/**)"],
        )
        write_register(reg, [row_a, row_b])
        assert run_validate(reg) == 1, "a string claimed by two rows must be rejected"


def test_validate_unique_protects_permissions_across_distinct_strings_ok():
    """Sanity counterpart: two rows claiming DIFFERENT strings must both pass —
    the uniqueness rule is per-string ownership, not "only one row may declare
    a non-empty protects_permissions"."""
    with tempfile.TemporaryDirectory() as tmp:
        reg = os.path.join(tmp, "register.jsonl")
        row_a = base_hook_row(protects_permissions=["Edit(system/hooks/**)"])
        row_b = base_hook_row(
            id="hook:public:/system/hooks/other_guard.sh@PreToolUse:Bash|Write|Edit",
            path="/system/hooks/other_guard.sh",
            protects_permissions=["Edit(system/other/**)"],
        )
        write_register(reg, [row_a, row_b])
        assert run_validate(reg) == 0, "distinct strings on distinct rows must both validate"


def test_generate_exposes_active_hook_rows():
    """generate.py's return dict must expose `active_hook_rows` (install_into_repo()'s
    "present" side) alongside the pre-existing suspensions_honored/expired — R2 Part B."""
    sys.path.insert(0, REGISTER_DIR)
    import generate
    future = (date.today() + timedelta(days=7)).isoformat()
    with tempfile.TemporaryDirectory() as tmp:
        reg = os.path.join(tmp, "register.jsonl")
        public = os.path.join(tmp, "public")
        os.makedirs(os.path.join(public, "system", "hooks"))
        for name in ("guard_hook_sop_read.sh", "other_guard.sh"):
            with open(os.path.join(public, "system", "hooks", name), "w", encoding="utf-8") as f:
                f.write("# stub guard\n")
        active_row = base_hook_row()
        honored_row = base_hook_row(
            id="hook:public:/system/hooks/other_guard.sh@PreToolUse:Bash|Write|Edit",
            path="/system/hooks/other_guard.sh",
            state="suspended", expiry=future,
            protects_permissions=["Edit(system/other/**)"],
        )
        write_register(reg, [active_row, honored_row])
        out = os.path.join(tmp, "out")
        result = generate.generate(reg, out, public, public, None,
                                    skip_caller_lint=True)
        assert result["schema_ok"], result.get("schema_problems")
        assert "active_hook_rows" in result, "active_hook_rows must be exposed"
        active_ids = [row["id"] for _, row in result["active_hook_rows"]]
        assert active_row["id"] in active_ids, "the active row must be in active_hook_rows"
        assert honored_row["id"] not in active_ids, "an honored-suspended row must NOT be in active_hook_rows"
        honored_ids = [row["id"] for _, row in result["suspensions_honored"]]
        assert honored_row["id"] in honored_ids


def test_carry_forward_protects_permissions_preserved():
    """harvest.carry_forward_protects_permissions() must carry a prior non-empty
    declaration forward onto a fresh row (which always defaults to []) — losing it
    on re-harvest would silently defeat install_into_repo()'s deny-line ownership."""
    sys.path.insert(0, REGISTER_DIR)
    import harvest
    with tempfile.TemporaryDirectory() as tmp:
        prior = os.path.join(tmp, "prior.jsonl")
        write_register(prior, [
            base_hook_row(protects_permissions=["Edit(system/hooks/**)"]),
        ])
        fresh = [base_hook_row(protects_permissions=[])]
        carried = harvest.carry_forward_protects_permissions(fresh, prior)
        assert len(carried) == 1 and carried[0][0] == fresh[0]["id"]
        assert fresh[0]["protects_permissions"] == ["Edit(system/hooks/**)"], \
            "a fresh row's empty default must be overwritten by the prior declaration"


def test_carry_forward_protects_permissions_no_prior_stays_empty():
    """A row with no prior non-empty declaration keeps harvest's honest [] default —
    this is not a re-apply-by-hand field like `group`, but it must never MANUFACTURE
    a declaration that was never there."""
    sys.path.insert(0, REGISTER_DIR)
    import harvest
    with tempfile.TemporaryDirectory() as tmp:
        prior = os.path.join(tmp, "prior.jsonl")
        write_register(prior, [base_hook_row(protects_permissions=[])])
        fresh = [base_hook_row(protects_permissions=[])]
        carried = harvest.carry_forward_protects_permissions(fresh, prior)
        assert carried == []
        assert fresh[0]["protects_permissions"] == []


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


def _extract_guard_switch_heredoc():
    """The exact python3 heredoc body guard_hook_sop_read.sh runs for its register-backed
    switch (R2 Part A) — extracted VERBATIM from the live file, never retyped, so a future
    edit that drifts the guard's inline copy away from switch_state.classify() fails THIS
    test instead of being discovered live."""
    guard_path = os.path.join(REPO_ROOT, "system", "hooks", "guard_hook_sop_read.sh")
    with open(guard_path, encoding="utf-8") as f:
        lines = f.readlines()
    start_idx = end_idx = None
    for i, line in enumerate(lines):
        if line.startswith("_SWITCH=$(python3 - <<'PY'"):
            start_idx = i + 1
            break
    assert start_idx is not None, "guard_hook_sop_read.sh: _SWITCH heredoc opener not found"
    for j in range(start_idx, len(lines)):
        if lines[j].rstrip("\n") == "PY":
            end_idx = j
            break
    assert end_idx is not None, "guard_hook_sop_read.sh: _SWITCH heredoc closer ('PY') not found"
    return "".join(lines[start_idx:end_idx])


def _run_guard_heredoc(register_root, today_iso):
    """Run the guard's own extracted heredoc as a real subprocess against register_root,
    exactly as the guard invokes it (same env var names, same stdlib-only body)."""
    code = _extract_guard_switch_heredoc()
    env = os.environ.copy()
    env["_REGISTER_ROOT"] = register_root
    env["LHB_REGISTER_TODAY"] = today_iso
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=env
    )
    return result.stdout.strip()


def test_parity_guard_heredoc_matches_classify():
    """R2 Part A, Decision 4: for a date/state/expiry matrix, the guard's inlined
    classification (run for real, extracted from the live file) must agree with
    switch_state.classify() on every case — the two are supposed to be behavioral
    duplicates and this is the seam that proves they have not drifted apart."""
    sys.path.insert(0, REGISTER_DIR)
    import switch_state

    today = date(2026, 9, 16)
    future = (today + timedelta(days=7)).isoformat()
    past = (today - timedelta(days=1)).isoformat()
    on_the_day = today.isoformat()

    verdict_map = {"ACTIVE": "active", "HONORED": "honored", "EXPIRED": "expired"}

    matrix = [
        ("active", None),
        ("suspended", future),
        ("suspended", past),
        ("suspended", on_the_day),   # edge: expiry == today is still honored
        ("suspended", None),          # malformed: missing expiry
        ("suspended", "not-a-date"),  # malformed: unparseable expiry
    ]

    with tempfile.TemporaryDirectory() as tmp:
        fixture_repo = os.path.join(tmp, "fixture-harness-repo")
        os.makedirs(os.path.join(fixture_repo, "system", "register"))
        os.makedirs(os.path.join(fixture_repo, "system", "hooks"))
        # Decision 2's Harness-repo test only checks these two are present as regular
        # files; content is irrelevant to the classification being tested here.
        with open(os.path.join(fixture_repo, "system", "register", "switch_state.py"),
                   "w", encoding="utf-8") as f:
            f.write("# fixture stub\n")
        with open(os.path.join(fixture_repo, "system", "hooks", "guard_hook_sop_read.sh"),
                   "w", encoding="utf-8") as f:
            f.write("# fixture stub\n")
        register_path = os.path.join(fixture_repo, "system", "register", "register.jsonl")

        for state, expiry in matrix:
            row = base_hook_row(state=state, expiry=expiry)
            with open(register_path, "w", encoding="utf-8") as f:
                f.write(json.dumps(row, sort_keys=True) + "\n")

            guard_out = _run_guard_heredoc(fixture_repo, today.isoformat())
            guard_verdict = verdict_map.get(guard_out)
            assert guard_verdict is not None, (
                f"guard heredoc produced unrecognised output {guard_out!r} for "
                f"state={state!r} expiry={expiry!r}"
            )
            expected = switch_state.classify(row, today=today)
            assert guard_verdict == expected, (
                f"parity mismatch state={state!r} expiry={expiry!r}: "
                f"guard={guard_verdict!r} classify={expected!r}"
            )


def main():
    tests = [
        test_schema_active_ok,
        test_schema_suspended_valid_expiry_ok,
        test_schema_suspended_no_expiry_rejected,
        test_schema_suspended_bad_date_rejected,
        test_schema_active_with_expiry_rejected,
        test_schema_unknown_key_rejected,
        test_schema_protects_permissions_default_ok,
        test_schema_protects_permissions_non_list_rejected,
        test_schema_protects_permissions_non_string_items_rejected,
        test_validate_duplicate_protects_permissions_ownership_rejected,
        test_validate_unique_protects_permissions_across_distinct_strings_ok,
        test_generate_exposes_active_hook_rows,
        test_carry_forward_protects_permissions_preserved,
        test_carry_forward_protects_permissions_no_prior_stays_empty,
        test_generate_honored_omits_guard,
        test_generate_active_emits_guard,
        test_generate_expired_alarms_and_rearms,
        test_carry_forward_honored_and_expired,
        test_parity_guard_heredoc_matches_classify,
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

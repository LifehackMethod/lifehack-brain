#!/usr/bin/env python3
"""test_githook_caller_class.py — K2 tests for the register's git-hooks caller class.

PROBLEM (system/journal.md, 2026-09-16 / the register-blind-spot lesson): the register held
zero rows for git hooks, so any tool invoked ONLY by a local git hook
(`system/githooks/pre-commit`, `system/githooks/pre-push`) read as UNCALLED — it nearly cost
`encoding_lint.py` its retirement, because its ONLY caller is `system/githooks/pre-commit`,
wired via `core.hooksPath`, a surface none of caller_lint.py's T1-inherited 7-class ontology
(registered-hook, scheduled, script-invoked, skill-referenced, ci-invoked, cli-instructed,
UNCALLED) ever modeled — T1's own raw six-wiring-file scan never looked at the local git-hooks
directory at all.

FIX (K2): a new register unit type, `githook` (schema_v1.py), harvested from
`system/githooks/*` in either repo (harvest.py's `harvest_githooks()` — mechanical, extracts
only invocation-shaped lines, never the whole file body, per constraint 0.5's "identity +
existence + a content hash, not full text"), plus a new caller_lint.py evidence surface,
`githooks-invoked` (`githook_evidence()`), crediting a governed unit referenced on an
invocation-shaped line inside any githook row's `commands`.

Run directly (no pytest dependency; run-all-tests.sh discovers test_*.py):
    python3 system/register/tests/test_githook_caller_class.py

RED -> GREEN: every test here fails against the pre-K2 code (no `githook` type, no
`githooks-invoked` evidence source) — most sharply `test_encoding_lint_is_no_longer_uncalled`,
which is the real-world defect this task exists to close — and all pass once the fix plus the
harvested register rows are in place.
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTER_DIR = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(os.path.dirname(REGISTER_DIR))
sys.path.insert(0, REGISTER_DIR)

DEFAULT_PRIVATE_ROOT = os.path.expanduser("~/.claude/skills/ClaudeOps")


def load_register_rows(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def test_schema_githook_type_known():
    import schema_v1
    assert "githook" in schema_v1.UNIT_TYPES, "schema_v1 must declare a 'githook' unit type"
    fields = schema_v1.fields_for("githook")
    assert "hook_name" in fields and "commands" in fields, fields


def test_schema_githook_row_valid():
    import validate_register
    row = {
        "id": "githook:public:/system/githooks/pre-commit",
        "type": "githook", "repo": "public", "path": "/system/githooks/pre-commit",
        "exists": True, "sha": "deadbeef",
        "needs": [], "returns": [], "cost_bytes": None, "cost_ms": None,
        "hook_name": "pre-commit",
        "commands": ['python3 "$repo/system/tools/encoding_lint.py" --staged --quiet'],
    }
    errs = validate_register.validate_row(row, 1)
    assert errs == [], f"well-formed githook row must validate: {errs}"


def test_schema_githook_missing_commands_rejected():
    import validate_register
    row = {
        "id": "githook:public:/system/githooks/pre-commit",
        "type": "githook", "repo": "public", "path": "/system/githooks/pre-commit",
        "exists": True, "sha": "deadbeef",
        "needs": [], "returns": [], "cost_bytes": None, "cost_ms": None,
        "hook_name": "pre-commit",
    }
    errs = validate_register.validate_row(row, 1)
    assert any("commands" in e for e in errs), f"missing 'commands' must be rejected: {errs}"


def test_harvest_githooks_extracts_invocation_lines():
    import harvest
    with tempfile.TemporaryDirectory() as tmp:
        gh = os.path.join(tmp, "system", "githooks")
        os.makedirs(gh)
        with open(os.path.join(gh, "pre-commit"), "w", encoding="utf-8") as f:
            f.write(
                "#!/bin/sh\n"
                "# this comment mentions fake_tool.py but is not code\n"
                'python3 "$repo/system/tools/fake_tool.py" --staged --quiet\n'
                "echo not an invocation, just prints fake_tool.py in prose\n"
            )
        rows = harvest.harvest_githooks(tmp, "/does/not/exist")
        assert len(rows) == 1, f"expected exactly 1 githook row, got {len(rows)}"
        row = rows[0]
        assert row["type"] == "githook" and row["hook_name"] == "pre-commit"
        assert any("fake_tool.py" in c and "python3" in c for c in row["commands"]), row["commands"]
        # the bare comment line must never survive extraction — a mention is not a call
        assert not any(c.lstrip().startswith("#") for c in row["commands"]), row["commands"]


def test_caller_lint_credits_githooks_invoked():
    import caller_lint
    import harvest
    with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as empty_private:
        tools_dir = os.path.join(tmp, "system", "tools")
        gh_dir = os.path.join(tmp, "system", "githooks")
        os.makedirs(tools_dir)
        os.makedirs(gh_dir)
        os.makedirs(os.path.join(tmp, "system", "hooks"))
        with open(os.path.join(tools_dir, "fake_tool.py"), "w", encoding="utf-8") as f:
            f.write("#!/usr/bin/env python3\nprint('hi')\n")
        with open(os.path.join(gh_dir, "pre-commit"), "w", encoding="utf-8") as f:
            f.write('#!/bin/sh\npython3 "$repo/system/tools/fake_tool.py" --staged\n')

        githook_rows = harvest.harvest_githooks(tmp, empty_private)
        result = caller_lint.lint_register(githook_rows, tmp, empty_private, home_root=tmp)
        found = result.find("public", "system/tools/fake_tool.py")
        assert found is not None, "fake_tool.py must be a governed unit"
        assert found["verdict"] == "githooks-invoked", f"expected githooks-invoked, got {found['verdict']}"
        assert any(s == "githooks-invoked" and "pre-commit" in d for s, d in found["evidence"]), found["evidence"]


def test_encoding_lint_is_no_longer_uncalled():
    """The real-world case this whole task exists to fix, against the LIVE committed register
    and the LIVE repo tree — RED before the K2 fix (schema/harvest/caller_lint + the harvested
    githook rows), GREEN after."""
    import caller_lint
    reg_path = os.path.join(REGISTER_DIR, "register.jsonl")
    rows = load_register_rows(reg_path)
    result = caller_lint.lint_register(rows, REPO_ROOT, DEFAULT_PRIVATE_ROOT)
    found = result.find("public", "system/tools/encoding_lint.py")
    assert found is not None, "encoding_lint.py must still be a governed unit"
    assert found["verdict"] != "UNCALLED", (
        "encoding_lint.py must not read UNCALLED — its only caller is "
        "system/githooks/pre-commit, the exact blind spot K2 fixes"
    )
    assert found["verdict"] == "githooks-invoked", found["verdict"]
    assert any("githook" in (s + d) for s, d in found["evidence"]), found["evidence"]


def main():
    tests = [
        test_schema_githook_type_known,
        test_schema_githook_row_valid,
        test_schema_githook_missing_commands_rejected,
        test_harvest_githooks_extracts_invocation_lines,
        test_caller_lint_credits_githooks_invoked,
        test_encoding_lint_is_no_longer_uncalled,
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

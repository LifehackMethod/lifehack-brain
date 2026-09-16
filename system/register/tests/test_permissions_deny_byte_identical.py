#!/usr/bin/env python3
"""test_permissions_deny_byte_identical.py — R2 Part B, decision 5's own claim:
"Default state (active, no suspension) round-trips byte-identically."

Run directly (no pytest dependency; run-all-tests.sh discovers test_*.py):
    python3 system/register/tests/test_permissions_deny_byte_identical.py

This is deliberately AGAINST THE REAL FILES (the committed `system/register/register.jsonl`
and the real `.claude/settings.json`), not the throwaway fixture test_check_drift_suspension.py
uses — the byte-identical-default claim is only meaningful measured against what students
actually have on disk today. To stay safe and repeatable (never mutating the tracked
`.claude/settings.json` from an automated test), the real settings file is COPIED into a
scratch directory; `install_into_repo()` merges into that COPY, using the real repo root
only to resolve hook script paths (read-only). The copy's resulting bytes are then compared
against the real file's bytes, read fresh, never written to.

A second, deliberately live, sharp-edged proof of the same claim — actually regenerating the
real tracked file in place with `--install-root .` and checking `git diff` is empty — is run
by hand as part of this feature's own verification (see the build's own report); an automated
test suite should not casually mutate a tracked file even when the assertion is "no change",
so that one lives outside this file.
"""
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTER_DIR = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(os.path.dirname(REGISTER_DIR))

REAL_REGISTER = os.path.join(REGISTER_DIR, "register.jsonl")
REAL_SETTINGS = os.path.join(REPO_ROOT, ".claude", "settings.json")

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append(ok)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if not ok and detail:
        print("        " + detail.replace("\n", "\n        "))


def test_default_active_settings_byte_identical():
    sys.path.insert(0, REGISTER_DIR)
    import generate

    with open(REAL_SETTINGS, "rb") as f:
        before_bytes = f.read()

    with tempfile.TemporaryDirectory(prefix="lhb-r2b-byte-identical-") as tmp:
        os.makedirs(os.path.join(tmp, ".claude"))
        scratch_settings = os.path.join(tmp, ".claude", "settings.json")
        shutil.copy2(REAL_SETTINGS, scratch_settings)

        out_dir = os.path.join(tmp, "out")
        result = generate.generate(
            REAL_REGISTER, out_dir, REPO_ROOT, REPO_ROOT, None,
            skip_caller_lint=True, targets="public",
        )
        if not result["schema_ok"]:
            check("default register (real) passes schema", False,
                  "\n".join(str(p) for p in result["schema_problems"]))
            return
        blocking_refused = [t for t in result["targets"]
                             if t["status"] == "REFUSED" and t.get("blocking", True)]
        if blocking_refused:
            check("generate refused a blocking (public) target", False,
                  "\n".join(f"{t['filename']}: {t['reason']}" for t in blocking_refused))
            return

        install_result = generate.install_into_repo(result, tmp)
        settings_installed = [row for row in install_result["installed"] if row[0] == "settings"]
        if not settings_installed:
            check("settings surface was installed", False, str(install_result["skipped"]))
            return
        _, _, _, deny_added, deny_removed = settings_installed[0]

        with open(scratch_settings, "rb") as f:
            after_bytes = f.read()

        check("default state (all rows active) regenerates permissions.deny with NO additions",
              deny_added == [], f"deny_added={deny_added!r}")
        check("default state (all rows active) regenerates permissions.deny with NO removals",
              deny_removed == [], f"deny_removed={deny_removed!r}")
        check("regenerated .claude/settings.json is BYTE-IDENTICAL to the real committed file",
              after_bytes == before_bytes,
              f"before={len(before_bytes)} bytes, after={len(after_bytes)} bytes "
              f"(first diff context suppressed — see git diff for the real live proof)")


def main():
    print("=== R2 Part B: byte-identical default (real files) ===")
    test_default_active_settings_byte_identical()
    passed = sum(1 for ok in RESULTS if ok)
    failed = len(RESULTS) - passed
    print(f"\nRESULT: {passed} passed, {failed} failed.")
    return 0 if failed == 0 and RESULTS else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""The fire-journal boilerplate every hook carries is silent BY DESIGN and must not trip hides_failure
(door_rules.silenced_call), while a real silenced fetch on the same kind of line still does. Also checks --files mode.
Run: python3 system/githooks/tests/test_check_hides_failure_journal_idiom.py"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "system", "tools"))
import door_rules  # noqa: E402

CHECK = os.path.join(ROOT, "system", "githooks", "checks", "hides_failure.py")
FAILS = []


def expect(label, cond):
    print(("   ok   " if cond else "  FAIL  ") + label)
    if not cond:
        FAILS.append(label)


JOURNAL = '. "$_lhb_dir/lib/journal.sh" 2>/dev/null || lhb_journal_fire() { :; }'
TRAP = "trap 'lhb_journal_fire \"$?\" \"turn_write_recorder.sh\" \"PostToolUse\" \"\" 2>/dev/null || true' EXIT"
FETCH = "email_fetch.py --now 2>/dev/null || true"
SRC = "#!/bin/bash\n" + JOURNAL + "\n" + TRAP + "\necho hi\n"

# ALLOW first
expect("journal source line is not flagged", door_rules.silenced_call(JOURNAL) == "")
expect("journal trap line (even naming a *write*.sh hook) is not flagged", door_rules.silenced_call(TRAP) == "")
with tempfile.TemporaryDirectory() as d:
    good = os.path.join(d, "demo-hook.sh")
    open(good, "w", encoding="utf-8").write(SRC)
    r = subprocess.run([sys.executable, CHECK, "--files", good], capture_output=True, text=True)
    expect("--files on a hook with only the boilerplate: exit 0, no refusal", r.returncode == 0 and "REFUSED" not in r.stderr)
    # then the control: a real silenced fetch still trips
    expect("a real silenced fetch is still flagged", door_rules.silenced_call(FETCH) == "fetch")
    bad = os.path.join(d, "demo-bad.sh")
    open(bad, "w", encoding="utf-8").write(SRC + FETCH + "\n")
    r = subprocess.run([sys.executable, CHECK, "--files", bad], capture_output=True, text=True)
    expect("--files on boilerplate + a real silenced fetch: refused", r.returncode == 1 and "silenced-error" in r.stderr)

print("\n%s" % ("ALL PASSED" if not FAILS else "FAILED: %s" % FAILS))
sys.exit(1 if FAILS else 0)

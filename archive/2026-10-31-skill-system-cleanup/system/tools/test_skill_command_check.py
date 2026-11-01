#!/usr/bin/env python3
"""
test_skill_command_check.py — fixtures for skill_command_check.py's closed verdict set.

Everything runs against a SYNTHETIC repo root built fresh per test (skills/ + a couple
of system/tools|hooks fixture files) — never the live tree — so the failure cases don't
depend on what happens to be true of this repo today. `make_repo()` seeds a minimal but
REAL positive-control pair (system/hooks/pm_flag.sh status, system/tools/gauge_check.py
check) into every synthetic root, because skill_command_check.py's own control check
runs unconditionally before anything else — a synthetic root missing it would make every
other fixture report CONTROL-FAILED instead of the verdict under test.

Run:  python3 system/tools/test_skill_command_check.py -v
"""

import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "skill_command_check.py")

sys.path.insert(0, HERE)
import skill_command_check as scc  # noqa: E402


# ── control-pair fixtures: real enough for run_control() to recognize ──────────────────
# pm_flag.sh: `status` declared ONLY via a bare-word `case` branch (no quotes anywhere
# near it) — this separation matters for the CONTROL-FAILED test, which monkeypatches
# shell_declares() specifically and must not have python_declares() rescue it via an
# incidental quoted "status" substring.
PM_FLAG_STUB = """#!/usr/bin/env bash
case "$1" in
  arm)
    echo arm
    ;;
  status)
    echo status
    ;;
  clear)
    echo clear
    ;;
esac
"""

# gauge_check.py: `check` declared the real way — a quoted string literal, as
# argparse's add_parser("check") would produce.
GAUGE_CHECK_STUB = """#!/usr/bin/env python3
import argparse
import sys
p = argparse.ArgumentParser()
sub = p.add_subparsers(dest="cmd")
sub.add_parser("check")
args = p.parse_args()
sys.exit(0)
"""


def make_repo(tmpdir, skill_md_by_name=None, extra_tool_files=None, skip_skills_dir=False):
    """Build a synthetic repo root under tmpdir: system/hooks/pm_flag.sh +
    system/tools/gauge_check.py (the control pair, always present unless the test is
    specifically about a broken control), plus whatever skills/*/SKILL.md and extra
    tool files the test needs. Returns the repo root path."""
    root = tmpdir
    os.makedirs(os.path.join(root, "system", "hooks"), exist_ok=True)
    os.makedirs(os.path.join(root, "system", "tools"), exist_ok=True)
    with open(os.path.join(root, "system", "hooks", "pm_flag.sh"), "w", encoding="utf-8") as f:
        f.write(PM_FLAG_STUB)
    with open(os.path.join(root, "system", "tools", "gauge_check.py"), "w", encoding="utf-8") as f:
        f.write(GAUGE_CHECK_STUB)

    if not skip_skills_dir:
        for name, text in (skill_md_by_name or {}).items():
            skill_dir = os.path.join(root, "skills", name)
            os.makedirs(skill_dir, exist_ok=True)
            with open(os.path.join(skill_dir, "SKILL.md"), "w", encoding="utf-8") as f:
                f.write(text)

    for rel, text in (extra_tool_files or {}).items():
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    return root


def run_cli(repo_root):
    """Invoke the real CLI as a subprocess (proves the exit-code contract end-to-end,
    not just the internal functions). Returns (returncode, stdout, stderr)."""
    proc = subprocess.run(
        [sys.executable, SCRIPT, "--repo-root", repo_root],
        capture_output=True, text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


class TestAllDeclared(unittest.TestCase):

    def test_real_tool_real_subcommand_all_declared(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_name = os.path.basename(os.path.normpath(tmp))
            skill_md = (
                "# Test Skill\n\n"
                "Run this:\n"
                "```bash\n"
                f"python3 ~/{repo_name}/system/tools/mytool.py check\n"
                "```\n"
            )
            tool_py = (
                "import argparse\n"
                "p = argparse.ArgumentParser()\n"
                "sub = p.add_subparsers(dest='cmd')\n"
                "sub.add_parser('check')\n"
            )
            root = make_repo(
                tmp,
                skill_md_by_name={"testskill": skill_md},
                extra_tool_files={"system/tools/mytool.py": tool_py},
            )
            rc, out, err = run_cli(root)
            first_line = out.splitlines()[0] if out else ""
            self.assertEqual(rc, 0, msg=f"stdout={out!r} stderr={err!r}")
            self.assertTrue(first_line.startswith("ALL-DECLARED"), first_line)
            # exactly one qualifying invocation on top of the two control pairs, which
            # are never counted in the sweep (they're checked separately, not walked
            # from a skill).
            self.assertEqual(first_line, "ALL-DECLARED 1")

    def test_shell_case_branch_subcommand_is_declared_not_flagged(self):
        """⭐ THE SHELL REGRESSION: a `case`-branch-only subcommand on a .sh tool must
        resolve as DECLARED. A quoted-literal-only check flags every shell script —
        this is the exact false positive that broke the first probe on 2026-08-07."""
        with tempfile.TemporaryDirectory() as tmp:
            repo_name = os.path.basename(os.path.normpath(tmp))
            skill_md = (
                "# Test Skill\n\n"
                "```bash\n"
                f'bash "$HOME/{repo_name}/system/hooks/mytool.sh" arm\n'
                "```\n"
            )
            tool_sh = (
                "#!/usr/bin/env bash\n"
                'case "$1" in\n'
                "  arm)\n"
                "    echo arm\n"
                "    ;;\n"
                "  clear)\n"
                "    echo clear\n"
                "    ;;\n"
                "esac\n"
            )
            root = make_repo(
                tmp,
                skill_md_by_name={"testskill": skill_md},
                extra_tool_files={"system/hooks/mytool.sh": tool_sh},
            )
            rc, out, err = run_cli(root)
            first_line = out.splitlines()[0] if out else ""
            self.assertEqual(rc, 0, msg=f"stdout={out!r} stderr={err!r}")
            self.assertEqual(first_line, "ALL-DECLARED 1")

    def test_multiline_command_still_found(self):
        """A command wrapped across lines with a trailing backslash inside a fenced
        block is still found (verbatim requirement)."""
        with tempfile.TemporaryDirectory() as tmp:
            repo_name = os.path.basename(os.path.normpath(tmp))
            skill_md = (
                "# Test Skill\n\n"
                "```bash\n"
                f"python3 ~/{repo_name}/system/tools/mytool.py \\\n"
                "  check\n"
                "```\n"
            )
            tool_py = (
                "import argparse\n"
                "p = argparse.ArgumentParser()\n"
                "sub = p.add_subparsers(dest='cmd')\n"
                "sub.add_parser('check')\n"
            )
            root = make_repo(
                tmp,
                skill_md_by_name={"testskill": skill_md},
                extra_tool_files={"system/tools/mytool.py": tool_py},
            )
            rc, out, err = run_cli(root)
            first_line = out.splitlines()[0] if out else ""
            self.assertEqual(rc, 0, msg=f"stdout={out!r} stderr={err!r}")
            self.assertEqual(first_line, "ALL-DECLARED 1")


class TestUndeclared(unittest.TestCase):

    def test_undeclared_subcommand(self):
        """gauge_check.py's own stub declares only `check` — instructing `nonesuch`
        must be reported as undeclared-subcommand."""
        with tempfile.TemporaryDirectory() as tmp:
            repo_name = os.path.basename(os.path.normpath(tmp))
            skill_md = (
                "# Test Skill\n\n"
                "```bash\n"
                f"python3 ~/{repo_name}/system/tools/gauge_check.py nonesuch\n"
                "```\n"
            )
            root = make_repo(tmp, skill_md_by_name={"testskill": skill_md})
            rc, out, err = run_cli(root)
            lines = out.splitlines()
            self.assertEqual(rc, 2, msg=f"stdout={out!r} stderr={err!r}")
            self.assertEqual(lines[0], "UNDECLARED 1")
            self.assertIn("nonesuch", lines[1])
            self.assertIn("undeclared-subcommand", lines[1])

    def test_stale_donor_path_flagged_even_though_file_exists_at_same_relative_path(self):
        """⭐ THE SELF-INSTANCE REGRESSION: a skill still instructing the OLD donor
        clone's prefix (`~/claudeops-config/...`) must be reported stale-donor-path —
        even though gauge_check.py exists at the SAME relative path under the live repo
        (the control pair guarantees that). The old bug silently normalized the donor
        prefix away and graded this as ALL-DECLARED, masking exactly the class of dead
        reference this tool exists to catch."""
        with tempfile.TemporaryDirectory() as tmp:
            skill_md = (
                "# Test Skill\n\n"
                "```bash\n"
                "python3 ~/claudeops-config/system/tools/gauge_check.py check\n"
                "```\n"
            )
            root = make_repo(tmp, skill_md_by_name={"testskill": skill_md})
            rc, out, err = run_cli(root)
            lines = out.splitlines()
            self.assertEqual(rc, 2, msg=f"stdout={out!r} stderr={err!r}")
            self.assertEqual(lines[0], "UNDECLARED 1")
            self.assertIn("stale-donor-path", lines[1])

    def test_missing_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_md = (
                "# Test Skill\n\n"
                "```bash\n"
                "python3 system/tools/does_not_exist.py check\n"
                "```\n"
            )
            root = make_repo(tmp, skill_md_by_name={"testskill": skill_md})
            rc, out, err = run_cli(root)
            lines = out.splitlines()
            self.assertEqual(rc, 2, msg=f"stdout={out!r} stderr={err!r}")
            self.assertEqual(lines[0], "UNDECLARED 1")
            self.assertIn("does_not_exist.py", lines[1])
            self.assertIn("missing-path", lines[1])


class TestCannotRead(unittest.TestCase):

    def test_missing_skills_dir_never_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, skip_skills_dir=True)
            # no skills/ dir created at all
            rc, out, err = run_cli(root)
            self.assertEqual(rc, 4, msg=f"stdout={out!r} stderr={err!r}")
            self.assertNotEqual(rc, 0)
            self.assertIn("CANNOT-READ", err)
            # the no-outcome member never prints a verdict to stdout either
            self.assertEqual(out, "")

    def test_unreadable_skill_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_md = "# Test Skill\nno commands here.\n"
            root = make_repo(tmp, skill_md_by_name={"testskill": skill_md})
            skill_path = os.path.join(root, "skills", "testskill", "SKILL.md")
            os.chmod(skill_path, 0o000)
            try:
                rc, out, err = run_cli(root)
                if os.geteuid() == 0:
                    self.skipTest("running as root — chmod 000 does not deny reads")
                self.assertEqual(rc, 4, msg=f"stdout={out!r} stderr={err!r}")
                self.assertIn("CANNOT-READ", err)
            finally:
                os.chmod(skill_path, 0o644)


class TestControlFailed(unittest.TestCase):

    def test_control_failed_when_shell_matcher_is_broken(self):
        """Deliberately break the shell matcher (monkeypatch shell_declares to always
        return False) and confirm CONTROL-FAILED fires: exit 5, and NO sweep verdict
        (ALL-DECLARED / UNDECLARED) is printed at all — a broken matcher must never
        look like either a clean or a dirty tree, because both are still a lie."""
        with tempfile.TemporaryDirectory() as tmp:
            # a real, otherwise-valid skill+tool pair the sweep WOULD report cleanly if
            # the control didn't short-circuit it first. make_repo() uses tmp itself as
            # the repo root, so its basename is known up front.
            repo_name = os.path.basename(os.path.normpath(tmp))
            skill_md = (
                "# Test Skill\n\n"
                "```bash\n"
                f"python3 ~/{repo_name}/system/tools/gauge_check.py check\n"
                "```\n"
            )
            root = make_repo(tmp, skill_md_by_name={"testskill": skill_md})

            # main() reads sys.argv directly; drive it the same way the CLI does.
            out_buf, err_buf = io.StringIO(), io.StringIO()
            with mock.patch.object(scc, "shell_declares", return_value=False):
                with mock.patch.object(sys, "argv", ["skill_command_check.py", "--repo-root", root]):
                    with redirect_stdout(out_buf), redirect_stderr(err_buf):
                        rc = scc.main()

            self.assertEqual(rc, 5, msg=f"stdout={out_buf.getvalue()!r} stderr={err_buf.getvalue()!r}")
            self.assertIn("CONTROL-FAILED", err_buf.getvalue())
            self.assertEqual(out_buf.getvalue(), "", "no sweep verdict may print on CONTROL-FAILED")

    def test_control_failed_when_control_file_itself_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, skill_md_by_name={})
            os.remove(os.path.join(root, "system", "tools", "gauge_check.py"))
            rc, out, err = run_cli(root)
            self.assertEqual(rc, 5, msg=f"stdout={out!r} stderr={err!r}")
            self.assertIn("CONTROL-FAILED", err)
            self.assertEqual(out, "")


if __name__ == "__main__":
    unittest.main(verbosity=2)

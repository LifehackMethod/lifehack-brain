#!/usr/bin/env python3
"""Tests for encoding_lint — the diff-scoped gate that refuses a NEW unencoded `open()` in
staged Python without ever blocking on pre-existing debt (the `scrub.py` scar this design
exists to avoid: a whole-file gate would have blocked all 85 pre-existing-defect files on
day one).

Every case drives the REAL CLI as a subprocess against a REAL throwaway git repository
(`git init`, write files, `git add`) — never by importing encoding_lint and calling its
functions directly. The entire point of this tool is diff-scoping: what got ADDED, not
what merely exists in a file. Calling internals would skip exactly the machinery under
test.

Run: python3 system/tools/test_encoding_lint.py
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))          # .../ClaudeOps
LINT = os.path.join(HERE, "encoding_lint.py")
REAL_PIPELINE = os.path.join(HERE, "cowork-ingest", "pipeline.py")


def _run(args, cwd):
    """Run the real CLI as a subprocess. Returns (returncode, stdout+stderr)."""
    p = subprocess.run([sys.executable, LINT] + args, cwd=cwd,
                        capture_output=True, text=True, timeout=60)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def _git(args, cwd):
    p = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True, timeout=60)
    if p.returncode != 0:
        raise RuntimeError(f"git {args} failed: {p.stdout}\n{p.stderr}")
    return p.stdout


class GitFixture(unittest.TestCase):
    """A real throwaway git repository under a temp dir. `write` makes a file, `stage` adds
    it to the index, `lint_staged` runs the real CLI's --staged mode against this repo."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="enclint-")
        _git(["init", "-q"], self.root)
        _git(["config", "user.email", "test@example.com"], self.root)
        _git(["config", "user.name", "Test"], self.root)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def write(self, rel, text):
        full = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(text)
        return full

    def commit_baseline(self, rel, text, msg="baseline"):
        """Write + add + commit a file, so a later change to it is a real DIFF, not an
        addition -- required for the grandfather case, whose whole point is a file with
        OLD content already committed."""
        self.write(rel, text)
        _git(["add", rel], self.root)
        _git(["commit", "-q", "-m", msg], self.root)

    def stage(self, rel):
        _git(["add", rel], self.root)

    def lint_staged(self):
        return _run(["--staged", "--quiet"], self.root)

    def lint_staged_loud(self):
        return _run(["--staged"], self.root)


class TheDenyPath(GitFixture):
    """The whole point of the tool: a diff that ADDS a new unencoded open() is refused."""

    def test_a_new_unencoded_open_is_refused(self):
        self.write("a.py", "def f(p):\n    return open(p).read()\n")
        self.stage("a.py")
        rc, out = self.lint_staged_loud()
        self.assertEqual(rc, 1, out)
        self.assertIn("a.py", out)
        self.assertIn("encoding=\"utf-8\"", out)

    def test_encoding_none_is_not_explicit_encoding_and_is_refused(self):
        # Explicit None is not an explicit encoding -- it means "let the platform decide",
        # which is exactly the bug (cp1252 on Windows) this whole tool exists to catch.
        self.write("a.py", "def f(p):\n    return open(p, encoding=None).read()\n")
        self.stage("a.py")
        rc, out = self.lint_staged_loud()
        self.assertEqual(rc, 1, out)
        self.assertIn("a.py", out)


class NotOverbroad(GitFixture):
    """Proves the gate is not just refusing everything."""

    def test_an_explicit_utf8_open_passes(self):
        self.write("a.py", 'def f(p):\n    return open(p, encoding="utf-8").read()\n')
        self.stage("a.py")
        rc, out = self.lint_staged()
        self.assertEqual(rc, 0, out)

    def test_a_binary_open_passes(self):
        # Binary is not a defect -- there is no text encoding to get wrong.
        self.write("a.py", 'def f(p):\n    return open(p, "rb").read()\n')
        self.stage("a.py")
        rc, out = self.lint_staged()
        self.assertEqual(rc, 0, out)


class TheGrandfatherCase(GitFixture):
    """⭐ THE `scrub.py` SCAR. If this fails, the gate is unshippable: a whole-file gate
    blocked all 85 pre-existing-defect files on day one. The fix is DIFF-scoping -- a
    defect is only reported if its open() call's lineno is a line the diff actually ADDS.

    Uses the REAL system/tools/cowork-ingest/pipeline.py, which genuinely carries 18 raw
    unencoded open() calls (and imports read_text from verdicts.py while doing so) --
    not a synthetic stand-in.
    """

    def test_18_old_defects_plus_an_unrelated_touch_still_passes(self):
        self.assertTrue(os.path.isfile(REAL_PIPELINE),
                         "fixture source missing -- cannot run the real-world grandfather case")
        with open(REAL_PIPELINE, encoding="utf-8") as fh:
            original = fh.read()

        self.commit_baseline("cowork-ingest/pipeline.py", original, msg="carry the real file")

        # One unrelated line changed -- a comment appended at the very end, nowhere near
        # any of the 18 pre-existing unencoded open() calls.
        touched = original + "\n# unrelated comment touched by this commit\n"
        self.write("cowork-ingest/pipeline.py", touched)
        self.stage("cowork-ingest/pipeline.py")

        rc, out = self.lint_staged_loud()
        self.assertEqual(rc, 0,
                          f"pre-existing debt must NOT block an unrelated touch -- got rc={rc}:\n{out}")


class AbsentSubjectRule(GitFixture):
    """"Nothing to check" is its own outcome, never a pass -- exit 2, never folded into 0."""

    def test_no_python_staged_is_cannot_evaluate(self):
        self.write("readme.md", "# hello\n")
        self.stage("readme.md")
        rc, out = self.lint_staged_loud()
        self.assertEqual(rc, 2, out)
        self.assertIn("CANNOT-EVALUATE: no-python-staged", out.splitlines()[0])

    def test_unparseable_python_is_cannot_evaluate(self):
        self.write("broken.py", "def f(:\n    this is not python\n")
        self.stage("broken.py")
        rc, out = self.lint_staged_loud()
        self.assertEqual(rc, 2, out)
        self.assertTrue(out.splitlines()[0].startswith("CANNOT-EVALUATE: unparseable"), out)
        self.assertIn("broken.py", out)

    def test_staged_outside_a_git_repo_is_cannot_evaluate(self):
        bare = tempfile.mkdtemp(prefix="enclint-nogit-")
        try:
            rc, out = _run(["--staged", "--quiet"], bare)
            self.assertEqual(rc, 2, out)
            self.assertIn("CANNOT-EVALUATE: no-git", out.splitlines()[0])
        finally:
            shutil.rmtree(bare, ignore_errors=True)


class QuietFlag(GitFixture):
    def test_quiet_suppresses_clean_chatter_but_deny_always_prints(self):
        self.write("clean.py", 'def f(p):\n    return open(p, encoding="utf-8").read()\n')
        self.stage("clean.py")
        rc_quiet, out_quiet = self.lint_staged()
        rc_loud, out_loud = self.lint_staged_loud()
        self.assertEqual(rc_quiet, 0)
        self.assertEqual(rc_loud, 0)
        self.assertLess(len(out_quiet), len(out_loud),
                         "--quiet must suppress CLEAN chatter relative to the loud run")


def _non_comment_lines_naming(hook_text, needle="encoding_lint.py"):
    """Non-comment, non-blank lines of a shell script that mention `needle`. A comment is a
    line whose first non-whitespace character is `#` -- so a docstring-style explanation
    that MENTIONS a forbidden flag (to warn a future author never to add it) does not count
    as the hook passing that flag. Grep-level, on purpose: this is a wiring check, not a
    shell parser."""
    out = []
    for line in hook_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if needle in line:
            out.append(line)
    return out


class HookWiring(unittest.TestCase):
    """The real invariant (ruled by the build lead after the first version of this test
    flagged its OWN explanatory comment as a violation): the hook must never actually PASS
    `--scan-file` to encoding_lint.py, and every line that actually RUNS it (names it
    alongside `python3` -- an executable invocation, not a deny-message string or an echoed
    suggestion) must pass `--staged`. A comment warning future authors never to wire
    `--scan-file` in is exactly the kind of prose this must NOT flag -- it is the strongest
    defense against re-introducing the scrub.py scar, not an instance of it."""

    def setUp(self):
        hook_path = os.path.join(REPO_ROOT, "system", "githooks", "pre-commit")
        with open(hook_path, encoding="utf-8") as fh:
            self.hook = fh.read()

    def test_every_real_invocation_of_encoding_lint_passes_staged(self):
        named = _non_comment_lines_naming(self.hook)
        # Ground truth REVISED 2026-08-24 (fix/encoding-gate-fail-open): the hook gained a
        # THIRD state -- the script itself missing from the checkout, distinct from "no
        # python3" and "nothing staged" -- which added its own existence check plus two new
        # echo lines naming the file (a MISSING-tool deny message and a restore-command
        # suggestion). That is 3 new non-comment lines on top of the original 3 (the real
        # invocation, and two echo lines for the real-violation deny path), so the honest
        # count is now 6. This assertion exists to catch path drift across copies of the
        # filename, not to cap how many states the hook is allowed to have -- so it is
        # updated in lockstep with a deliberate hook change, not weakened.
        self.assertEqual(len(named), 6, f"expected 6 non-comment lines naming encoding_lint.py, "
                                         f"got {len(named)}:\n" + "\n".join(named))
        invocations = [l for l in named if "python3" in l]
        self.assertGreaterEqual(len(invocations), 1,
                                 "no non-comment line actually RUNS encoding_lint.py via python3")
        for l in invocations:
            self.assertIn("--staged", l, f"a real invocation is missing --staged: {l!r}")

    def test_no_non_comment_line_passes_scan_file_to_encoding_lint(self):
        named = _non_comment_lines_naming(self.hook)
        for l in named:
            self.assertNotIn("--scan-file", l,
                              f"a non-comment line passes --scan-file to encoding_lint.py: {l!r}")




class MultilineCallSpan(GitFixture):
    """R1/R2 -- `ast.Call.lineno` only points at the `open(` token's own line. A multi-line
    call's `encoding=` keyword can live several lines below that. Deleting JUST the
    `encoding=` line leaves `open(`'s own lineno untouched, so a lineno-only diff-scope
    would silently grandfather a brand-new defect. The fix has to intersect the diff's
    added lines against the call's WHOLE span (node.lineno..node.end_lineno) -- and R2
    exists because that widening is exactly the kind of change that can go too far and
    start flagging untouched multi-line calls an unrelated edit merely happens to sit near."""

    def test_r1_deleting_the_encoding_kwarg_from_a_multiline_call_is_refused(self):
        baseline = (
            "def f(p):\n"
            "    return open(\n"
            "        p,\n"
            "        \"r\",\n"
            "        encoding=\"utf-8\"\n"
            "    )\n"
        )
        self.commit_baseline("a.py", baseline, msg="multiline call, correctly encoded")
        changed = (
            "def f(p):\n"
            "    return open(\n"
            "        p,\n"
            "        \"r\",\n"
            "    )\n"
        )
        self.write("a.py", changed)
        self.stage("a.py")
        rc, out = self.lint_staged_loud()
        self.assertEqual(rc, 1,
                          f"deleting encoding= from a multiline call must be a NEW defect -- got rc={rc}:\n{out}")
        self.assertIn("a.py", out)

    def test_r2_an_untouched_multiline_unencoded_call_plus_an_unrelated_edit_still_passes(self):
        # The open() call itself is NEVER touched by this commit -- only a line above it is.
        baseline = (
            "def f(p):\n"
            "    x = 1\n"
            "    return open(\n"
            "        p,\n"
            "        \"r\"\n"
            "    )\n"
        )
        self.commit_baseline("b.py", baseline, msg="multiline call, pre-existing debt")
        changed = baseline.replace("x = 1", "x = 2")
        self.assertNotEqual(changed, baseline)
        self.write("b.py", changed)
        self.stage("b.py")
        rc, out = self.lint_staged_loud()
        self.assertEqual(rc, 0,
                          f"an unrelated edit outside the call's span must NOT resurrect old debt "
                          f"-- got rc={rc}:\n{out}\n"
                          f"if R1's span-widening fix broke this, the fix is worse than the bug")


class ExtensionlessPython(GitFixture):
    """R3 -- a staged file with no `.py` extension but a `#!/usr/bin/env python3` shebang IS
    Python that was staged; reporting CANNOT-EVALUATE: no-python-staged against it is a false
    absent-subject. The negative half matters just as much: a staged extensionless file that
    is NOT Python (a #!/bin/sh script, say) must not be force-parsed as Python or crash --
    it should simply not be treated as a Python file at all."""

    def test_r3_a_shebang_python_file_with_no_py_extension_is_scanned_and_refused(self):
        self.write("bin/runme", "#!/usr/bin/env python3\ndef f(p):\n    return open(p).read()\n")
        self.stage("bin/runme")
        rc, out = self.lint_staged_loud()
        self.assertEqual(rc, 1,
                          f"a #!/usr/bin/env python3 file IS staged Python -- got rc={rc}:\n{out}")
        self.assertIn("runme", out)

    def test_r3_negative_a_non_python_shebang_file_is_not_parsed_as_python(self):
        self.write("bin/runme", "#!/bin/sh\necho hello\n")
        self.stage("bin/runme")
        rc, out = self.lint_staged_loud()
        # Nothing Python is staged -- this must land on the SAME absent-subject outcome as
        # "no .py files at all," never a crash and never a false CLEAN.
        self.assertEqual(rc, 2, out)
        self.assertIn("no-python-staged", out.splitlines()[0])


class UndecodableStagedPython(GitFixture):
    """R4 -- a staged .py file carrying a raw invalid-UTF-8 byte must come back as a clean,
    reported CANNOT-EVALUATE, never an unhandled UnicodeDecodeError with a raw traceback.
    WHY THIS ONE MATTERS MOST OF ALL THE REGRESSIONS: this tool's entire reason to exist is
    that an encoding problem must never crash a script (that is literally what utf8_stdio.py
    and this lint both exist to prevent on the OTHER end of the pipe). A lint that dies with
    a raw UnicodeDecodeError traceback the moment it meets bad bytes is the exact failure
    class the feature was built to end -- just moved from runtime to commit-time."""

    def test_r4_a_raw_invalid_utf8_byte_is_a_clean_cannot_evaluate_never_a_crash(self):
        full = os.path.join(self.root, "bad.py")
        with open(full, "wb") as fh:
            fh.write(b'def f(p):\n    return open(p)  # bad byte follows: \xff\n')
        self.stage("bad.py")
        rc, out = self.lint_staged_loud()
        self.assertEqual(rc, 2, out)
        self.assertTrue(out.splitlines()[0].startswith("CANNOT-EVALUATE: unparseable"),
                         f"expected the unparseable reason token as the first line, got:\n{out}")
        self.assertIn("bad.py", out)
        self.assertNotIn("Traceback", out, "a raw traceback means this crashed instead of reporting")


if __name__ == "__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3
"""Tests for citation_lint — built around the one failure that costs anything: a document that
points at a file which is not here, and nothing says so.

Every case builds a whole throwaway repository (settings.json, a hooks directory, a skills
directory) and runs the lint against it with --root, so nothing here reads the real tree. That
matters more than usual for this tool: its denominator IS the tree, so a test that leaked into the
real one would pass or fail for reasons that have nothing to do with the code.

Run: python3 system/tools/test_citation_lint.py
"""
import os
import shutil
import sys
import tempfile
import unittest
import unittest.mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import citation_lint as lint                                    # noqa: E402

# ⭐ TAKE AN OPEN PHASE FROM THE LINT ITSELF, never a hardcoded name.
# These fixtures need "a phase that is still open" — the NAME is irrelevant to what they prove.
# Two of them said "Phase 2", and when Phase 2 closed on 2026-08-11 both went red: not because the
# lint broke, but because the tests had quietly become assertions about the project's schedule
# rather than about the rule. A test coupled to a calendar fails on a date rather than on a defect,
# and whoever hits it has to work out which of the two it was.
OPEN_PHASE = sorted(k for k in lint.OPEN_LANDINGS if k.startswith("phase"))[0]

SETTINGS = """{
  "hooks": {"UserPromptSubmit": [{"hooks": [{"type": "command",
    "command": "bash \\"${CLAUDE_PROJECT_DIR}/system/hooks/live.sh\\""}]}]}
}
"""


class Fixture(unittest.TestCase):
    """A throwaway repo. `write` makes a file, `lint` returns (exit code, printed output)."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="citelint-")
        self.write(".claude/settings.json", SETTINGS)
        self.write("system/hooks/live.sh", "#!/bin/sh\nexit 0\n")
        os.makedirs(os.path.join(self.root, ".claude", "skills"))
        # Force plugin-skill resolution OFF unless a test opts in with `self.plugin_skill(...)`.
        # `plugin_skills_root()` reads a real, machine-global manifest that `--root` cannot scope
        # -- left alone, these fixtures would pass or fail depending on whichever lifehack-brain
        # plugin happens to be installed on the machine running them. That is exactly the "leaked
        # into the real tree" failure mode this file's own docstring says it refuses to have.
        self._plugin_env_patch = unittest.mock.patch.dict(
            os.environ, {"CITATION_LINT_PLUGIN_SKILLS_ROOT": ""})
        self._plugin_env_patch.start()

    def tearDown(self):
        self._plugin_env_patch.stop()
        shutil.rmtree(self.root, ignore_errors=True)

    def write(self, rel, text):
        full = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(text)
        return full

    def skill(self, name):
        self.write(".claude/skills/%s/SKILL.md" % name, "# %s\n" % name)

    def lint(self):
        from io import StringIO
        held, sys.stdout = sys.stdout, StringIO()
        try:
            rc = lint.main(["--root", self.root])
            return rc, sys.stdout.getvalue()
        finally:
            sys.stdout = held

    def lint_scoped(self, *files):
        """Same as `lint()`, but with `--files <files...>` -- what pre-commit calls with the staged
        set. `lint_scoped()` with no paths is `--files` given and empty (nothing staged), never the
        same thing as a bare `lint()` (no `--files` flag at all -> unscoped)."""
        from io import StringIO
        held, sys.stdout = sys.stdout, StringIO()
        try:
            rc = lint.main(["--root", self.root, "--files"] + list(files))
            return rc, sys.stdout.getvalue()
        finally:
            sys.stdout = held


class PathsMustResolve(Fixture):
    def test_a_dangling_path_fails_and_the_output_names_it(self):
        self.write("docs/a.md", "Run `system/tools/nope.py` first.\n")
        rc, out = self.lint()
        self.assertEqual(rc, 1)
        self.assertIn("system/tools/nope.py", out)
        self.assertIn("docs/a.md:1", out)

    def test_the_same_citation_passes_once_the_file_exists(self):
        self.write("docs/a.md", "Run `system/tools/real.py` first.\n")
        self.write("system/tools/real.py", "#\n")
        self.assertEqual(self.lint()[0], 0)

    def test_a_directory_citation_resolves(self):
        self.write("docs/a.md", "See `system/hooks/`.\n")
        self.assertEqual(self.lint()[0], 0)

    def test_a_glob_resolves_when_something_matches_and_fails_when_nothing_does(self):
        self.write("docs/a.md", "Bring `system/tools/*.py` along.\n")
        self.assertEqual(self.lint()[0], 1)
        self.write("system/tools/one.py", "#\n")
        self.assertEqual(self.lint()[0], 0)

    def test_a_line_anchor_is_stripped_before_the_file_is_looked_for(self):
        # `tool.py:138-160` is a citation of tool.py, not of a file with a colon in its name.
        self.write("system/tools/tool.py", "#\n")
        self.write("docs/a.md", "The rule is at `system/tools/tool.py:138-160`.\n")
        self.assertEqual(self.lint()[0], 0)

    def test_arguments_after_the_path_are_stripped(self):
        self.write("docs/a.md", "Run `system/hooks/live.sh status` to see it.\n")
        self.assertEqual(self.lint()[0], 0)

    def test_placeholders_and_variables_are_not_citations(self):
        self.write("docs/a.md",
                   "Writes `state/projects/<slug>/brief.md` via `$ROOT/system/tools/x.py` "
                   "and `system/tools/{name}.py`.\n")
        self.assertEqual(self.lint()[0], 0)

    def test_a_path_outside_this_repo_is_not_a_citation(self):
        # ~/.config and /tmp are named constantly and are nobody's promise to ship.
        self.write("docs/a.md", "Stored at `~/.config/lifehack/brain-root`, scratch in `/tmp/rdr`.\n")
        self.assertEqual(self.lint()[0], 0)

    def test_the_notes_folder_journal_is_not_expected_in_the_repo(self):
        # The regression this guards: demanding a person's journal be committed to a public repo.
        self.write("docs/a.md", "Entries append to `system/journal.md`.\n")
        rc, out = self.lint()
        self.assertEqual(rc, 0)
        self.assertIn("under the notes folder", out)

    def test_the_persons_own_material_is_never_scanned(self):
        self.write("memory/mine.md", "My note about `system/tools/nope.py`.\n")
        self.assertEqual(self.lint()[0], 0)

    def test_a_bak_file_is_not_scanned(self):
        self.write("docs/a.md.bak", "Old text citing `system/tools/nope.py`.\n")
        self.assertEqual(self.lint()[0], 0)


class DataPathsAreNotInvisible(Fixture):
    """⭐ THE BLIND SPOT THIS CLASS EXISTS TO KEEP CLOSED, found 2026-08-11.

    The lint only recognised a path whose first segment is a top-level directory OF THE REPO. This
    repo has no `state/`, so `state/telos.md` — a file that ships in neither migration — fell
    through both branches and was never checked at all. Those are exactly the paths the migration
    moved, so they are the ones most likely to be stale.
    """

    def test_a_data_file_without_its_root_is_a_finding(self):
        self.write("doc.md", "See `state/telos.md` for the year goal.\n")
        rc, out = self.lint()
        self.assertEqual(rc, 1, "an unprefixed data-side FILE must be a finding, not invisible")
        self.assertIn("state/telos.md", out)

    def test_the_same_path_written_with_its_root_is_data_and_is_skipped(self):
        # `<notes>/` says "this lives on a machine the lint cannot see", which is a real answer.
        # Demanding that a person's journal be committed to a public repo is what everything else
        # here exists to prevent.
        self.write("doc.md", "See `<notes>/state/telos.md` for the year goal.\n")
        rc, out = self.lint()
        self.assertEqual(rc, 0, "a path that names the notes folder is accounted for")

    def test_a_relative_shape_is_not_read_as_a_data_path(self):
        """`canon/` and `records/` are usually RELATIVE to a folder already named in the sentence.
        Treating them as roots once produced a banner asserting that `canon/purpose.md` was a
        record in somebody's private notes — the opposite of true; it is the layout this repo
        builds. A check that makes a document lie to satisfy it is worse than the gap it closed."""
        self.write("doc.md", "Each subject folder gets a `canon/purpose.md` and a `records/` dir.\n")
        rc, out = self.lint()
        self.assertEqual(rc, 0, "a relative sub-path is not a claim about a data root")

    def test_a_bare_data_directory_is_not_a_file_claim(self):
        self.write("doc.md", "Plans live in `plans/`, one per name.\n")
        rc, out = self.lint()
        self.assertEqual(rc, 0, "a directory shape describes a layout; it claims no file")


class TheThreeClaims(Fixture):
    def test_a_present_claim_for_a_missing_file_fails_and_says_which_claim_broke(self):
        self.write("docs/a.md", "| `system/tools/nope.py` | why | ✅ here |\n")
        rc, out = self.lint()
        self.assertEqual(rc, 1)
        self.assertIn("claimed ✅ here and is NOT here", out)

    def test_a_deferral_naming_an_open_phase_is_accepted_and_reported(self):
        self.write("docs/a.md", f"| `system/tools/later.py` | why | lands in {OPEN_PHASE} |\n")
        rc, out = self.lint()
        self.assertEqual(rc, 0)
        self.assertIn(OPEN_PHASE, out)

    def test_a_deferral_naming_a_closed_landing_fails(self):
        # The whole point of the closed set: T1.14 is over, so a row still waiting on it is a lie.
        self.write("docs/a.md", "| `system/tools/later.py` | why | lands in T1.14 |\n")
        rc, out = self.lint()
        self.assertEqual(rc, 1)
        self.assertIn("not open", out)

    def test_a_deferral_with_no_landing_at_all_fails(self):
        self.write("docs/a.md", "| `system/tools/later.py` | why | lands in eventually |\n")
        self.assertEqual(self.lint()[0], 1)

    def test_a_deferral_for_a_file_that_has_since_arrived_fails(self):
        self.write("system/tools/later.py", "#\n")
        self.write("docs/a.md", "| `system/tools/later.py` | why | lands in Phase 2 |\n")
        rc, out = self.lint()
        self.assertEqual(rc, 1)
        self.assertIn("HAS LANDED", out)

    def test_a_decline_is_accepted(self):
        self.write("docs/a.md", "- ⛔ `system/tools/nope.py` — not shipped: it is theirs, not ours.\n")
        rc, out = self.lint()
        self.assertEqual(rc, 0)
        self.assertIn("1 declined", out)

    def test_a_claim_covers_the_whole_file_not_just_its_own_line(self):
        self.write("docs/a.md",
                   "> ⛔ `system/tools/nope.py` — not shipped.\n\n"
                   "Later on, the same `system/tools/nope.py` comes up again.\n"
                   "And again: `system/tools/nope.py`.\n")
        self.assertEqual(self.lint()[0], 0)

    def test_a_claim_covers_a_path_that_wrapped_onto_the_next_line(self):
        # The measured failure that widened the rule: three of this lint's own banners.
        self.write("docs/a.md",
                   "> - ⛔ **not shipped** — the author's own document lives at\n"
                   ">   `system/tools/nope.py` and never crossed.\n")
        self.assertEqual(self.lint()[0], 0)

    def test_a_claim_does_not_leak_past_a_blank_line(self):
        self.write("docs/a.md",
                   "> ⛔ `system/tools/one.py` — not shipped.\n\n"
                   "An ordinary paragraph naming `system/tools/two.py`.\n")
        rc, out = self.lint()
        self.assertEqual(rc, 1)
        self.assertIn("two.py", out)
        self.assertNotIn("one.py", out)

    def test_a_claim_does_not_leak_into_the_next_bullet(self):
        self.write("docs/a.md",
                   "- ⛔ `system/tools/one.py` — not shipped.\n"
                   "- `system/tools/two.py` is required.\n")
        rc, out = self.lint()
        self.assertEqual(rc, 1)
        self.assertIn("two.py", out)

    def test_worded_status_does_not_count_in_ordinary_prose(self):
        # The measured false positive: a planning rule reading "...or lands in this block".
        self.write("docs/a.md",
                   "Nothing vanishes: each item maps to a task or lands in the `system/tools/cut.py` block.\n")
        self.assertEqual(self.lint()[0], 1)

    def test_a_reason_column_does_not_promise_what_it_merely_mentions(self):
        self.write("system/tools/here.py", "#\n")
        self.write("docs/a.md",
                   "| `system/tools/here.py` | imports `system/tools/gone.py` | ✅ here |\n")
        rc, out = self.lint()
        self.assertEqual(rc, 1)
        self.assertIn("gone.py", out)
        self.assertIn("nothing on this line", out)

    def test_a_routing_table_claims_its_second_column_when_the_first_holds_no_path(self):
        self.write("docs/a.md",
                   "| building… | read first | status |\n|---|---|---|\n"
                   f"| **a hook** | `system/tools/later.py` | lands in {OPEN_PHASE} |\n")
        self.assertEqual(self.lint()[0], 0)


class SkillsMustExist(Fixture):
    def test_a_command_with_no_skill_behind_it_fails(self):
        self.write("docs/a.md", "Then run `/websearch` for a single fact.\n")
        rc, out = self.lint()
        self.assertEqual(rc, 1)
        self.assertIn(".claude/skills/websearch/", out)

    def test_the_same_command_passes_once_the_skill_is_there(self):
        self.skill("websearch")
        self.write("docs/a.md", "Then run `/websearch` for a single fact.\n")
        self.assertEqual(self.lint()[0], 0)

    def test_a_harness_command_is_not_ours_to_ship(self):
        self.write("docs/a.md", "Run `/clear` and start again.\n")
        self.assertEqual(self.lint()[0], 0)

    def test_a_path_fragment_is_not_a_command(self):
        # /dev/null, /tmp, and a bare /records segment are not slash commands.
        self.write("docs/a.md", "Send it to `/dev/null`; scratch lives in `/tmp`.\n")
        self.assertEqual(self.lint()[0], 0)

    def test_a_missing_command_can_be_accounted_for_like_any_other_citation(self):
        self.write("docs/a.md", "- ⏳ `/websearch` — lands in Phase 3.\n\nRun `/websearch` for a fact.\n")
        self.assertEqual(self.lint()[0], 0)


class HooksBothWays(Fixture):
    def test_a_registration_with_no_file_behind_it_fails(self):
        os.remove(os.path.join(self.root, "system/hooks/live.sh"))
        rc, out = self.lint()
        self.assertEqual(rc, 1)
        self.assertIn("registered and is not on disk", out)

    def test_a_hook_on_disk_that_is_registered_nowhere_fails(self):
        self.write("system/hooks/orphan.sh", "#!/bin/sh\n")
        rc, out = self.lint()
        self.assertEqual(rc, 1)
        self.assertIn("registered nowhere, declared nowhere", out)

    def test_an_unregistered_script_declared_in_the_config_passes(self):
        self.write("system/hooks/orphan.sh", "#!/bin/sh\n")
        lint.UNREGISTERED_OK["orphan.sh"] = "a test fixture"
        try:
            self.assertEqual(self.lint()[0], 0)
        finally:
            del lint.UNREGISTERED_OK["orphan.sh"]

    def test_a_test_beside_the_hooks_is_not_treated_as_an_unregistered_hook(self):
        self.write("system/hooks/tests/verify-something.sh", "#!/bin/sh\n")
        self.assertEqual(self.lint()[0], 0)

    def test_unreadable_settings_is_CANNOT_READ_never_clean(self):
        # rc 4 is the house no-outcome code: "the check did not run" must not read as "nothing wrong".
        self.write(".claude/settings.json", "{ not json")
        rc, out = self.lint()
        self.assertEqual(rc, lint.CANNOT_READ)
        self.assertIn("CANNOT-READ", out)


class ScopedToStagedFiles(Fixture):
    """`--files` is what `system/githooks/pre-commit` passes on the staged set, so that
    pre-existing drift in a file nobody is touching cannot block an unrelated commit -- issues
    #81/#90/#74.3. The gate must still bite on the file that IS in scope."""

    def test_a_dangling_citation_outside_scope_does_not_block(self):
        self.write("docs/untouched.md", "Run `system/tools/nope.py` first.\n")
        # Same tree, unscoped, still fails -- this is the pre-existing-debt case the bug reports
        # describe. The dangling file is real; it is just not part of what is being committed.
        self.assertEqual(self.lint()[0], 1)
        rc, out = self.lint_scoped("docs/other.md")
        self.assertEqual(rc, 0)
        self.assertNotIn("system/tools/nope.py", out)

    def test_the_same_dangling_citation_inside_scope_still_blocks(self):
        self.write("docs/untouched.md", "Run `system/tools/nope.py` first.\n")
        rc, out = self.lint_scoped("docs/untouched.md")
        self.assertEqual(rc, 1)
        self.assertIn("system/tools/nope.py", out)

    def test_an_empty_scope_is_zero_files_not_the_whole_tree(self):
        # `--files` with nothing after it (an empty staged set, e.g. a deletion-only commit) must
        # scope to nothing -- never fall back to the unscoped whole-tree sweep.
        self.write("docs/untouched.md", "Run `system/tools/nope.py` first.\n")
        rc, out = self.lint_scoped()
        self.assertEqual(rc, 0)
        self.assertNotIn("system/tools/nope.py", out)

    def test_a_hook_registration_gap_outside_scope_does_not_block(self):
        os.remove(os.path.join(self.root, "system/hooks/live.sh"))
        rc, out = self.lint_scoped("docs/other.md")
        self.assertEqual(rc, 0)
        self.assertNotIn("registered and is not on disk", out)

    def test_the_same_hook_registration_gap_still_blocks_when_settings_is_staged(self):
        os.remove(os.path.join(self.root, "system/hooks/live.sh"))
        rc, out = self.lint_scoped(".claude/settings.json")
        self.assertEqual(rc, 1)
        self.assertIn("registered and is not on disk", out)

    def test_the_same_hook_registration_gap_still_blocks_when_a_hook_file_is_staged(self):
        os.remove(os.path.join(self.root, "system/hooks/live.sh"))
        rc, out = self.lint_scoped("system/hooks/live.sh")
        self.assertEqual(rc, 1)
        self.assertIn("registered and is not on disk", out)


class NeverAFalseClean(Fixture):
    """The failures that would make a green run mean nothing."""

    def test_a_missing_settings_file_is_CANNOT_READ_not_a_pass(self):
        os.remove(os.path.join(self.root, ".claude/settings.json"))
        rc, _ = self.lint()
        self.assertEqual(rc, lint.CANNOT_READ)

    def test_a_root_that_does_not_exist_is_CANNOT_READ(self):
        self.assertEqual(lint.main(["--root", os.path.join(self.root, "gone")]), lint.CANNOT_READ)

    def test_the_clean_line_reports_a_denominator_it_did_not_get_from_the_documents(self):
        self.write("system/tools/real.py", "#\n")
        self.write("docs/a.md", "Run `system/tools/real.py`.\n")
        rc, out = self.lint()
        self.assertEqual(rc, 0)
        self.assertIn("registrations", out)
        self.assertIn("hook files", out)

    def test_an_exempt_file_is_named_in_the_count_rather_than_silently_skipped(self):
        self.write("docs/exempt.md", "Points at `system/tools/nope.py` in another tree.\n")
        lint.EXEMPT_FILES["docs/exempt.md"] = "a test fixture"
        try:
            rc, out = self.lint()
            self.assertEqual(rc, 0)
            self.assertIn("1 exempt file", out)
        finally:
            del lint.EXEMPT_FILES["docs/exempt.md"]


if __name__ == "__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3
"""test_registry.py — the one place that knows where a project's files are.

The rule under test is the dual resolution: a project is a folder now, and used to be a flat file,
and BOTH have to resolve or a half-migrated set of notes loses projects silently. The cases that
matter are the ones where a lookup would return something plausible and wrong.

Run: python3 shared/test_registry.py
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "registry.py")
sys.path.insert(0, HERE)
import registry as reg  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.root, "system"))

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def write_registry(self, *lines):
        p = os.path.join(self.root, "system", "project-registry.md")
        with open(p, "w", encoding="utf-8") as f:
            f.write("# Projects\n\n" + "\n".join(lines) + "\n")
        return p

    def touch(self, rel):
        p = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w").write("x\n")
        return p


class Rows(Base):

    def test_a_five_field_row_parses_into_all_five(self):
        r = reg.parse_row("root | widget | The Widget | active | state/projects/widget")
        self.assertEqual(r, {"desk": "root", "slug": "widget", "display": "The Widget",
                             "status": "active", "path": "state/projects/widget"})

    def test_a_four_field_row_is_valid_and_has_no_path(self):
        r = reg.parse_row("root | widget | The Widget | active")
        self.assertIsNotNone(r)
        self.assertIsNone(r["path"])

    def test_an_empty_fifth_field_is_the_same_as_no_path(self):
        self.assertIsNone(reg.parse_row("root | widget | The Widget | active |   ")["path"])

    def test_a_table_separator_row_is_not_a_project(self):
        # `-` is inside the slug alphabet, so a lax pattern parses `|---|---|---|---|---|` as a
        # project whose slug and folder are both '---'. It matches itself, raises no alarm, and
        # silently adds one to every count taken over the registry.
        self.assertIsNone(reg.parse_row("|---|---|---|---|---|"))

    def test_the_format_documentation_line_is_not_a_project(self):
        self.assertIsNone(reg.parse_row("{desk} | {slug} | {display name} | {status} | {path}"))

    def test_prose_and_headings_are_not_projects(self):
        for line in ("# Projects", "", "One row per project, added when a project starts."):
            self.assertIsNone(reg.parse_row(line), line)

    def test_rows_skips_everything_that_is_not_a_row(self):
        self.write_registry("# Projects", "|---|---|", "{desk} | {slug} | {d} | {s} | {p}",
                            "root | widget | The Widget | active | state/projects/widget",
                            "root | gadget | The Gadget | paused")
        got = [r["slug"] for r in reg.rows(self.root)]
        self.assertEqual(got, ["widget", "gadget"])


class DualResolution(Base):

    def test_the_folder_shape_resolves_to_its_own_brief_records_and_canon(self):
        self.write_registry("root | widget | The Widget | active | state/projects/widget")
        p = reg.resolve("widget", root=self.root)
        self.assertEqual(p.layout, "folder")
        self.assertTrue(p.brief.endswith("state/projects/widget/brief.md"))
        self.assertTrue(p.records.endswith("state/projects/widget/records"))
        self.assertTrue(p.canon.endswith("state/projects/widget/canon/current.md"))

    def test_the_flat_shape_resolves_to_the_old_locations(self):
        self.write_registry("root | widget | The Widget | active")
        p = reg.resolve("widget", root=self.root)
        self.assertEqual(p.layout, "flat")
        self.assertTrue(p.brief.endswith("state/briefs/widget.md"))
        self.assertTrue(p.records.endswith("/records"))
        self.assertTrue(p.canon.endswith("/canon.md"))

    def test_find_brief_prefers_the_folder_when_the_file_is_there(self):
        self.write_registry("root | widget | The Widget | active | state/projects/widget")
        self.touch("state/projects/widget/brief.md")
        self.assertTrue(reg.find_brief("widget", root=self.root).endswith("projects/widget/brief.md"))

    def test_find_brief_falls_back_to_flat_when_the_folder_brief_is_absent(self):
        # ⭐ THE SAFETY INVARIANT. A row was migrated to the folder shape but the file has not moved
        # yet. Without the fallback, the project silently disappears from every lookup.
        self.write_registry("root | widget | The Widget | active | state/projects/widget")
        self.touch("state/briefs/widget.md")
        self.assertTrue(reg.find_brief("widget", root=self.root).endswith("state/briefs/widget.md"))

    def test_find_brief_returns_none_rather_than_a_path_that_does_not_exist(self):
        self.write_registry("root | widget | The Widget | active | state/projects/widget")
        self.assertIsNone(reg.find_brief("widget", root=self.root))

    def test_an_unregistered_slug_has_no_layout_and_creates_nothing(self):
        self.write_registry("root | widget | The Widget | active | state/projects/widget")
        p = reg.resolve("nonexistent", root=self.root)
        self.assertIsNone(p.layout)
        self.assertFalse(os.path.exists(os.path.dirname(p.brief)))

    def test_a_missing_registry_resolves_to_nothing_rather_than_raising(self):
        p = reg.resolve("widget", root=self.root)
        self.assertIsNone(p.layout)

    def test_a_category_above_the_project_is_fine(self):
        self.write_registry("root | widget | W | active | state/projects/infrastructure/widget")
        p = reg.resolve("widget", root=self.root)
        self.assertTrue(p.leaf_matches_slug)
        self.assertTrue(p.brief.endswith("infrastructure/widget/brief.md"))

    def test_a_folder_that_is_not_named_the_slug_is_flagged(self):
        self.write_registry("root | widget | W | active | state/projects/the-widget-build")
        self.assertFalse(reg.resolve("widget", root=self.root).leaf_matches_slug)

    def test_resolve_refuses_rather_than_guessing_when_no_notes_folder_is_set(self):
        """Runs against a MINIMAL COPY of the tool, not the real clone.

        This is a real subprocess, so no monkeypatch reaches it, and scrubbing $LIFEHACK_ROOT and
        $HOME never did close every route: the resolver also reads a `.brain-root` pointer FILE next
        to the tool — this repo's own (route 2, 2026-08-17) and, in a linked git worktree, the main
        worktree's (route 2b, 2026-08-21). Both are located from the tool's OWN position, so the
        only honest way to test "nothing is configured" in a subprocess is to run a copy that sits
        somewhere with nothing configured. Which is also the case being claimed: a fresh clone."""
        env = dict(os.environ)
        env.pop("LIFEHACK_ROOT", None)
        with tempfile.TemporaryDirectory() as fake_home:
            env["HOME"] = fake_home
            # the three files the tool needs, in the layout it expects to find them in
            clone_shared = os.path.join(fake_home, "clone", "shared")
            clone_utf8 = os.path.join(fake_home, "clone", "system", "tools")
            os.makedirs(clone_shared)
            os.makedirs(clone_utf8)
            for name in ("registry.py", "brain_root.py"):
                shutil.copy(os.path.join(HERE, name), clone_shared)
            shutil.copy(os.path.join(HERE, "..", "system", "tools", "utf8_stdio.py"), clone_utf8)
            tool = os.path.join(clone_shared, "registry.py")
            self.assertFalse(os.path.exists(os.path.join(fake_home, "clone", ".brain-root")),
                             "the copy must start with nothing configured, or it tests nothing")
            p = subprocess.run([sys.executable, tool, "widget"], capture_output=True, text=True, env=env)
            self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
            self.assertIn("REFUSED", p.stderr)


class WritingRows(Base):

    def test_the_row_it_writes_is_the_row_it_reads(self):
        line = reg.format_row("widget", "The Widget", "state/projects/widget")
        r = reg.parse_row(line)
        self.assertEqual(r["slug"], "widget")
        self.assertEqual(r["path"], "state/projects/widget")
        self.assertEqual(r["status"], "active")

    def test_it_refuses_a_folder_that_is_not_named_the_slug(self):
        with self.assertRaises(ValueError):
            reg.format_row("widget", "W", "state/projects/the-widget-build")

    def test_it_refuses_a_slug_that_is_not_a_slug(self):
        for bad in ("Widget", "my widget", "-widget", "widget!"):
            with self.assertRaises(ValueError):
                reg.format_row(bad, "W", "state/projects/" + bad)

    def test_it_only_ever_writes_the_folder_shape(self):
        # The flat shape is read forever and created never.
        line = reg.format_row("widget", "The Widget", "state/projects/widget")
        self.assertEqual(line.count("|"), 4, "a written row always has all five fields")


class Cli(Base):

    def _run(self, *args):
        p = subprocess.run([sys.executable, TOOL, *args, "--root", self.root],
                           capture_output=True, text=True)
        return p.returncode, p.stdout, p.stderr

    def test_it_names_the_three_paths_and_says_which_do_not_exist(self):
        self.write_registry("root | widget | The Widget | active | state/projects/widget")
        rc, out, _ = self._run("widget")
        self.assertEqual(rc, 0)
        self.assertIn("layout=folder", out)
        self.assertIn("not created yet", out)

    def test_an_unregistered_slug_exits_3_and_says_where_it_looked(self):
        self.write_registry("root | widget | W | active | state/projects/widget")
        rc, out, _ = self._run("nope")
        self.assertEqual(rc, 3)
        self.assertIn("NOT-REGISTERED", out)
        self.assertIn("project-registry.md", out)

    def test_a_drifted_folder_is_called_out(self):
        self.write_registry("root | widget | W | active | state/projects/the-widget-build")
        _rc, out, _ = self._run("widget")
        self.assertIn("cannot be found by name", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)

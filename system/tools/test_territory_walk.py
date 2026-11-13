#!/usr/bin/env python3
"""Tests for territory_walk.py — the live inventory archivist-audit check 8 rebuilds the map from.

Each case is one way the old model-only regeneration went wrong: a folder nothing declared was
never seen, a removed folder stayed listed, and counts were copied forward instead of counted.
Every fixture is a throwaway tree; nothing here reads a real notes root.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import territory_walk as tw  # noqa: E402

TOOL = os.path.join(HERE, "territory_walk.py")

LAYOUT = """# layout
```
<notes>/
├── canon.md
├── system/
│   └── journal.md
├── state/
│   └── projects/<slug>/
├── records/<type>/
└── desks/<subject>/
    └── records/
```

| `context/` | reference |
| `logs/` | what was done |

- `<notes>/plans/<name>.md` — plans
"""

# The previous map: names one staging home and its packages in prose, says subject `alpha` has
# 4 projects, and has a row for a folder that has since been removed.
OLD_MAP = """# Canon-Purpose Map
| path | purpose | accepts | status |
|---|---|---|---|
| `system/staging/` | Packages: pkg-one, pkg-two. | folders | INFERRED |
| `system/removed-home/` | Gone since last week. | anything | INFERRED |
| `desks/alpha/` | ✓ | ✓ (flat) | 4 member projects |
"""


def mk(root, *parts, text=None):
    p = os.path.join(root, *parts)
    if text is None:
        os.makedirs(p, exist_ok=True)
    else:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
    return p


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        r = self.root = os.path.join(self.tmp.name, "notes")
        mk(r, "canon.md", text="")
        mk(r, "system", "journal.md", text="")
        mk(r, "system", "staging", "pkg-one", "inner")
        mk(r, "system", "staging", "pkg-two")
        mk(r, "system", "brand-new-home", "deep", "deeper")          # declared by nothing
        mk(r, "records", "context")
        mk(r, "records", "logs", "_ARCHIVE_old-bundle", "anything")  # archive: counted, never descended
        mk(r, "records", "logs", "_archive_second")
        mk(r, "desks", "alpha", "records", "context")
        mk(r, "desks", "alpha", "records", "oddball")                # not a record type, not named
        mk(r, ".editor-vault", "app.json", text="{}")                    # tool config
        mk(r, "plans", "a.md.bak", text="")
        mk(r, "plans", "b.md.bak", text="")
        reg = ["| desk | slug | display | status | path |", "|---|---|---|---|---|"]
        for i in range(6):                                           # 6 on disk; the old map says 4
            mk(r, "state", "projects", f"p{i}", "brief.md", text=f"---\ndesk: alpha\n---\n# p{i}\n")
            mk(r, "state", "projects", f"p{i}", "records")
            reg.append(f"| alpha | p{i} | P{i} | active | state/projects/p{i} |")
        mk(r, "system", "project-registry.md", text="\n".join(reg) + "\n")
        self.inv = tw.inventory(r, OLD_MAP, LAYOUT, depth=4)
        self.by_path = {e["path"]: e for e in self.inv["homes"]}


class Unmapped(Fixture):
    def test_undeclared_folder_is_listed_with_first_seen(self):
        e = self.by_path.get("system/brand-new-home")
        self.assertIsNotNone(e, "a folder nothing declares must appear, never be skipped")
        self.assertEqual(e["status"], "UNMAPPED")
        self.assertRegex(e["first_seen"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertEqual(e["subfolders"], 2, "what is under an unmapped folder is counted")

    def test_only_the_topmost_unmapped_folder_is_listed(self):
        paths = [u["path"] for u in self.inv["unmapped"]]
        self.assertNotIn("system/brand-new-home/deep", paths)

    def test_undeclared_subfolder_of_a_declared_home_is_listed(self):
        self.assertIn("desks/alpha/records/oddball", [u["path"] for u in self.inv["unmapped"]])

    def test_layout_record_types_are_declared_under_every_records_folder(self):
        self.assertEqual(self.by_path["desks/alpha/records/context"]["status"], "declared")
        self.assertEqual(self.by_path["records/context"]["status"], "declared")

    def test_items_a_row_lists_are_mapped_and_not_descended(self):
        self.assertEqual(self.by_path["system/staging/pkg-one"]["status"], "mapped")
        self.assertNotIn("system/staging/pkg-one/inner", self.by_path)

    def test_placeholder_matches_are_grouped_with_a_count(self):
        e = self.by_path["state/projects/*"]
        self.assertTrue(e["grouped"])
        self.assertEqual(e["folders"], 6)


class Patterns(Fixture):
    def test_a_file_glob_does_not_swallow_sibling_folders(self):
        inv = tw.inventory(self.root, OLD_MAP + "| `system/*.bak` | backups | - | UNMAPPED |\n", LAYOUT)
        self.assertIn("system/brand-new-home", [u["path"] for u in inv["unmapped"]])

    def test_a_bare_placeholder_never_hides_a_top_level_folder(self):
        mk(self.root, "stray-top")
        inv = tw.inventory(self.root, OLD_MAP + "Rows are `{desk}` and `<slug>/` here.\n", LAYOUT)
        self.assertIn("stray-top", [u["path"] for u in inv["unmapped"]])


class Missing(Fixture):
    def test_removed_home_is_flagged_not_carried_forward(self):
        self.assertIn("system/removed-home", self.inv["missing"])
        self.assertNotIn("system/removed-home", self.by_path)

    def test_prose_that_mentions_a_path_is_not_a_missing_claim(self):
        inv = tw.inventory(self.root, OLD_MAP + "\nNote: `memory/v1-inbox/` was archived.\n", LAYOUT)
        self.assertNotIn("memory/v1-inbox", inv["missing"])


class Counts(Fixture):
    def test_projects_per_subject_come_from_disk_not_the_old_map(self):
        alpha = self.inv["projects"]["per_desk"]["alpha"]
        self.assertEqual(alpha, {"briefs": 6, "registry": 6}, "the old map said 4; disk says 6")
        self.assertEqual(self.inv["projects"]["project_folders"], 6)

    def test_archive_folders_are_counted_and_never_descended_or_unmapped(self):
        self.assertEqual(self.inv["archive_folders"], {"records/logs": 2})
        self.assertFalse(any("_ARCHIVE_" in u["path"] for u in self.inv["unmapped"]))

    def test_bak_files_are_counted_per_folder(self):
        self.assertEqual(self.inv["bak_files"].get("plans"), 2)

    def test_a_count_changes_when_the_tree_changes(self):
        mk(self.root, "records", "logs", "_ARCHIVE_third")
        inv = tw.inventory(self.root, OLD_MAP, LAYOUT)
        self.assertEqual(inv["archive_folders"], {"records/logs": 3})


class ToolConfig(Fixture):
    def test_dot_folders_are_listed_as_tool_config_not_unmapped(self):
        self.assertEqual(self.by_path[".editor-vault"]["status"], "tool-config")
        self.assertNotIn(".editor-vault", [u["path"] for u in self.inv["unmapped"]])


class LayoutParsing(unittest.TestCase):
    def test_a_fenced_block_does_not_shift_backtick_pairing(self):
        text = "a `x` b\n```\nsome `odd\n```\n| `<notes>/state/current.md` | thing |\n"
        pats, lits = tw.parse_layout(text)
        self.assertIn("state/current.md", lits)

    def test_tree_drawing_nests_by_indent(self):
        pats, _ = tw.parse_layout(LAYOUT)
        self.assertIn("system/journal.md", pats)
        self.assertIn("desks/*/records", pats)
        self.assertIn("state/projects/*", pats)


class Cli(Fixture):
    def run_tool(self, *args, env_root=True):
        return subprocess.run([sys.executable, TOOL, *args], capture_output=True, text=True,
                              env={**os.environ, "LIFEHACK_ROOT": self.tmp.name + "/nope"})

    def test_out_inside_the_notes_root_is_refused(self):
        target = os.path.join(self.root, "system", "inventory.md")
        r = self.run_tool("--root", self.root, "--out", target)
        self.assertEqual(r.returncode, 1)
        self.assertFalse(os.path.exists(target))

    def test_out_outside_the_root_writes_json(self):
        out = os.path.join(self.tmp.name, "inv.json")
        mp = mk(self.tmp.name, "old.md", text=OLD_MAP)
        lay = mk(self.tmp.name, "layout.md", text=LAYOUT)
        r = self.run_tool("--root", self.root, "--map", mp, "--layout", lay, "--json", "--out", out)
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(out, encoding="utf-8") as f:
            inv = json.load(f)
        self.assertIn("system/removed-home", inv["missing"])

    def test_markdown_names_every_section(self):
        r = self.run_tool("--root", self.root)
        self.assertEqual(r.returncode, 0, r.stderr)
        for head in ("## UNMAPPED", "## MISSING", "## Tool config", "## Every home on disk", "## Projects"):
            self.assertIn(head, r.stdout)

    def test_no_root_exits_2(self):
        r = self.run_tool("--root", os.path.join(self.tmp.name, "does-not-exist"))
        self.assertEqual(r.returncode, 2)


if __name__ == "__main__":
    unittest.main()

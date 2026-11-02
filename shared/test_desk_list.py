#!/usr/bin/env python3
"""test_desk_list.py -- the person's desk list, read from their notes (2e). Run: python3 shared/test_desk_list.py

Every case runs against a throwaway notes folder (LIFEHACK_ROOT) and a throwaway HOME, so the developer's real
notes are never read. Covers, both ways: a list in the notes is read (desk_list, backlog_groom.py,
planning-diary-capture.py); no list = no desks and no crash; a broken list reports its REAL error, never a
blanket "PyYAML missing"; and the desk_scaffold.py fixes (slug check, preview refuses an existing desk, the
starter _registry.md lists all six starter files, no dead settings in the printed entry).
Cases that need PyYAML to parse are skipped when this interpreter has none (CI's python has none)."""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DESK_LIST = os.path.join(HERE, "desk_list.py")
GROOM = os.path.join(ROOT, "system", "tools", "backlog_groom.py")
DIARY = os.path.join(ROOT, "system", "tools", "planning-diary-capture.py")
SCAFFOLD = os.path.join(ROOT, "system", "tools", "cowork-ingest", "desk_scaffold.py")
try:
    import yaml  # noqa: F401
    HAVE_YAML = True
except ImportError:
    HAVE_YAML = False

GOOD = """schema_version: 2
desks:
  - desk_id: alpha
    open_loops_path: desks/alpha/state/open-loops.md
    backlog_mode: queue
  - desk_id: beta
    open_loops_path: desks/beta/state/open-loops.md
    backlog_mode: register
"""
# The exact breakage 6a measured: an entry pasted under `desks: []`.
BROKEN = "schema_version: 2\ndesks: []\n  - desk_id: alpha\n    backlog_mode: queue\n"
# Exactly the entry desk_scaffold.py prints for a person to paste (quoted notes, yes/no, a comment).
SCAFFOLDED = """schema_version: 2
desks:   # one entry per full desk
  - desk_id: lamps
    open_loops_path: desks/lamps/state/open-loops.md
    purpose_path: desks/lamps/canon/purpose.md
    reads_external: no
    backlog_mode: register
    notes: "Scaffolded by desk_scaffold.py 2026-11-02. #1"
"""
SCAFFOLDED_PARSED = [{"desk_id": "lamps", "open_loops_path": "desks/lamps/state/open-loops.md",
                      "purpose_path": "desks/lamps/canon/purpose.md", "reads_external": False,
                      "backlog_mode": "register", "notes": "Scaffolded by desk_scaffold.py 2026-11-02. #1"}]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp(prefix="desklist."))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.notes = os.path.join(self.tmp, "notes")
        self.home = os.path.join(self.tmp, "home")
        os.makedirs(os.path.join(self.notes, "desks"))
        os.makedirs(self.home)

    def write(self, rel, text):
        p = os.path.join(self.notes, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
        return p

    def env(self):
        e = {k: v for k, v in os.environ.items() if not k.startswith("LIFEHACK_")}
        e.update(HOME=self.home, LIFEHACK_ROOT=self.notes)
        # A throwaway HOME hides the user site-packages (where PyYAML often lives); keep it visible.
        import site
        us = site.getusersitepackages() if site.ENABLE_USER_SITE else ""
        if us and os.path.isdir(us):
            e["PYTHONPATH"] = os.pathsep.join(p for p in (us, e.get("PYTHONPATH", "")) if p)
        if self.MODE == "none":
            # A student without PyYAML, on ANY interpreter: a stub `yaml` first on the path that refuses
            # to import, exactly as a missing package does.
            stub = os.path.join(self.tmp, "no-yaml")
            os.makedirs(stub, exist_ok=True)
            with open(os.path.join(stub, "yaml.py"), "w", encoding="utf-8") as f:
                f.write("raise ImportError('No module named yaml (test stub)')\n")
            e["PYTHONPATH"] = os.pathsep.join(p for p in (stub, e.get("PYTHONPATH", "")) if p)
        return e

    # "yaml" = PyYAML present (skipped when this interpreter has none); "none" = PyYAML absent.
    MODE = "yaml"

    def need_mode(self):
        if self.MODE == "yaml" and not HAVE_YAML:
            self.skipTest("PyYAML not installed under this interpreter")

    def run_py(self, *args):
        return subprocess.run([sys.executable] + list(args), env=self.env(), capture_output=True, text=True,
                              cwd=self.tmp, timeout=120)

    def groom(self):
        r = self.run_py(GROOM, "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        import json
        return json.loads(r.stdout), r.stderr


class Reader(Base):
    def test_no_list_means_no_desks_quietly(self):
        r = self.run_py(DESK_LIST, "--path")
        self.assertEqual((r.returncode, r.stdout), (0, ""))
        r = self.run_py(DESK_LIST, "--check")
        self.assertEqual(r.returncode, 0)
        self.assertIn("no desk list", r.stdout)

    def test_the_list_lives_in_the_notes_next_to_the_desks(self):
        p = self.write("desks/desk-registry.yaml", GOOD)
        r = self.run_py(DESK_LIST, "--path")
        self.assertEqual(r.stdout.strip(), p)

    def test_plugin_ships_no_list(self):
        self.assertFalse(os.path.exists(os.path.join(ROOT, "system", "desk-registry.yaml")))

    def test_good_list_is_read(self):
        self.need_mode()
        self.write("desks/desk-registry.yaml", GOOD)
        r = self.run_py(DESK_LIST, "--check")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("2 desk(s)", r.stdout)
        self.assertNotIn("PyYAML", r.stdout)

    def test_broken_list_reports_the_real_error(self):
        self.need_mode()
        self.write("desks/desk-registry.yaml", BROKEN)
        r = self.run_py(DESK_LIST, "--check")
        self.assertEqual(r.returncode, 1)
        self.assertIn("cannot be read", r.stdout)
        self.assertNotIn("PyYAML is not installed", r.stdout)

    def test_wrong_shape_is_named(self):
        self.need_mode()
        self.write("desks/desk-registry.yaml", "desks: alpha\n")
        r = self.run_py(DESK_LIST, "--check")
        self.assertEqual(r.returncode, 1)
        self.assertIn("ERROR", r.stdout)
        self.assertIn("desks:", r.stdout)

    def test_scaffold_printed_entry_reads_identically(self):
        """The entry desk_scaffold.py tells a person to paste must read the same either way."""
        self.need_mode()
        self.write("desks/desk-registry.yaml", SCAFFOLDED)
        code = ("import sys, json; sys.path.insert(0, %r); import desk_list; d, e = desk_list.load_desks(); "
                "print(json.dumps([d, e], sort_keys=True))" % HERE)
        r = self.run_py("-c", code)
        self.assertEqual(r.returncode, 0, r.stderr)
        import json
        self.assertEqual(json.loads(r.stdout), [SCAFFOLDED_PARSED, None])

    def test_env_seam_empty_means_no_list(self):
        self.write("desks/desk-registry.yaml", GOOD)
        e = self.env()
        e["LIFEHACK_DESK_LIST"] = ""
        r = subprocess.run([sys.executable, DESK_LIST, "--path"], env=e, capture_output=True, text=True)
        self.assertEqual(r.stdout, "")


class ReaderNoYaml(Reader):
    """Every Reader case again, with PyYAML absent: a student with a desk must get their desks."""
    MODE = "none"

    def test_malformed_lines_give_a_real_error(self):
        for bad, why in ((BROKEN, "line 3"),
                         ("desks:\n\t- desk_id: a\n", "tab"),
                         ("desks:\n  - desk_id: [a, b]\n", "full YAML"),
                         ("desks:\n  - desk_id: \"a\n", "unclosed"),
                         ("desks:\n  - desk_id: a\n    open_loops_path desks/a\n", "line 3")):
            self.write("desks/desk-registry.yaml", bad)
            r = self.run_py(DESK_LIST, "--check")
            self.assertEqual(r.returncode, 1, (bad, r.stdout))
            self.assertIn("cannot be read", r.stdout)
            self.assertIn(why, r.stdout)
            self.assertNotIn("PyYAML is not installed", r.stdout)


class DeskFolder(Base):
    """desk_folder(): the session-start loader maps a $LIFEHACK_DESK desk_id to its folder through this.
    Must work with or without PyYAML (it runs at every session start)."""
    MAPPED = ("schema_version: 2\ndesks:\n  - desk_id: taxes\n    open_loops_path: desks/money/state/open-loops.md\n"
              "    backlog_mode: register\n  - desk_id: lamps\n    purpose_path: desks/lamps/canon/purpose.md\n")

    def lookup(self, desk_id):
        code = ("import sys; sys.path.insert(0, %r); import desk_list; f, e = desk_list.desk_folder(%r); "
                "print('%%s|%%s' %% (f, e))" % (HERE, desk_id))
        r = self.run_py("-c", code)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()

    def test_no_list_is_none_not_a_crash(self):
        self.assertEqual(self.lookup("taxes"), "None|None")

    def test_desk_id_maps_to_its_folder(self):
        self.need_mode()
        self.write("desks/desk-registry.yaml", self.MAPPED)
        self.assertEqual(self.lookup("taxes"), "money|None")
        self.assertEqual(self.lookup("lamps"), "lamps|None")
        self.assertEqual(self.lookup("ghost"), "None|None")

    def test_broken_list_returns_the_real_error(self):
        self.need_mode()
        self.write("desks/desk-registry.yaml", BROKEN)
        out = self.lookup("alpha")
        self.assertTrue(out.startswith("None|") and "cannot be read" in out, out)


class DeskFolderNoYaml(DeskFolder):
    MODE = "none"


class DeskIdsNoYaml(Base):
    MODE = "none"

    def ids(self):
        code = "import sys; sys.path.insert(0, %r); import desk_list; print(sorted(desk_list.desk_ids()))" % HERE
        r = self.run_py("-c", code)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()

    def test_ids_read_without_pyyaml(self):
        self.write("desks/desk-registry.yaml", GOOD)
        self.assertEqual(self.ids(), "['alpha', 'beta']")

    def test_broken_list_still_yields_ids_leniently(self):
        self.write("desks/desk-registry.yaml", BROKEN)
        self.assertEqual(self.ids(), "['alpha']")


class BacklogGroom(Base):
    def test_no_list_no_desks_no_crash(self):
        rep, err = self.groom()
        self.assertNotIn("WARNING [backlog_groom]", err)
        self.assertEqual(rep["counts"]["by_desk"], {})

    @unittest.skipUnless(HAVE_YAML, "PyYAML not installed under this interpreter")
    def test_list_in_notes_is_read(self):
        self.write("desks/desk-registry.yaml", GOOD)
        self.write("desks/alpha/state/open-loops.md", "# Open loops\n\n- **[ALPHA-ONE]** first thing\n")
        rep, err = self.groom()
        self.assertNotIn("WARNING [backlog_groom]", err)
        self.assertIn("alpha", rep["counts"]["by_desk"])
        self.assertIn("beta", rep["counts"]["by_desk"])
        self.assertEqual(rep["counts"]["by_desk"]["beta"]["mode"], "register")

    @unittest.skipUnless(HAVE_YAML, "PyYAML not installed under this interpreter")
    def test_broken_list_reports_real_error_not_pyyaml(self):
        self.write("desks/desk-registry.yaml", BROKEN)
        rep, err = self.groom()
        self.assertIn("WARNING [backlog_groom]: the desk list", err)
        self.assertIn("cannot be read", err)
        self.assertNotIn("PyYAML", err)
        self.assertEqual(rep["counts"]["by_desk"], {})


class DiaryCapture(Base):
    def known(self):
        code = ("import importlib.util,sys;s=importlib.util.spec_from_file_location('pdc',%r);"
                "m=importlib.util.module_from_spec(s);s.loader.exec_module(m);print(sorted(m.KNOWN_DESKS))" % DIARY)
        r = self.run_py("-c", code)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()

    def test_no_list_only_root(self):
        self.assertEqual(self.known(), "['root']")

    def test_list_in_notes_is_read(self):
        self.write("desks/desk-registry.yaml", GOOD)
        self.assertEqual(self.known(), "['alpha', 'beta', 'root']")


class Scaffold(Base):
    def scaffold(self, desk, *extra):
        return self.run_py(SCAFFOLD, "--drive-root", self.notes, "--desk", desk, "--purpose", "p", *extra)

    def test_escaping_name_refused(self):
        for bad in ("../x", "a/b", "..", ".hidden", "x y", ""):
            r = self.scaffold(bad)
            self.assertNotEqual(r.returncode, 0, bad)
            self.assertIn("REFUSED", r.stderr, bad)
        self.assertFalse(os.path.exists(os.path.join(self.notes, "x")))

    def test_valid_name_passes_and_registry_lists_all_six(self):
        r = self.scaffold("new-desk_2")
        self.assertEqual(r.returncode, 0, r.stderr)
        base = os.path.join(self.notes, "desks", "new-desk_2")
        with open(os.path.join(base, "_registry.md"), encoding="utf-8") as f:
            reg = f.read()
        starters = ("CLAUDE.md", "_registry.md", "canon/current.md", "canon/purpose.md",
                    "state/current.md", "state/open-loops.md")
        for rel in starters:
            self.assertTrue(os.path.isfile(os.path.join(base, rel)), rel)
            self.assertIn("`%s`" % rel, reg)
        for dead in ("health_producer", "pulse_slot", "status_tile_path", "Pulse"):
            self.assertNotIn(dead, r.stdout)
        self.assertIn(os.path.join(self.notes, "desks", "desk-registry.yaml"), r.stdout)
        with open(os.path.join(base, "CLAUDE.md"), encoding="utf-8") as f:
            claude = f.read()
        self.assertNotIn("guard_canon_write protects it", claude)
        self.assertIn("/save", claude)

    def test_dry_run_valid_name_writes_nothing(self):
        r = self.scaffold("fresh", "--dry-run")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("DRY-RUN", r.stdout)
        self.assertFalse(os.path.exists(os.path.join(self.notes, "desks", "fresh")))

    def test_dry_run_on_existing_desk_refuses(self):
        os.makedirs(os.path.join(self.notes, "desks", "taken"))
        r = self.scaffold("taken", "--dry-run")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("already exists", r.stderr)


if __name__ == "__main__":
    unittest.main()

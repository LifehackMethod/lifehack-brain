#!/usr/bin/env python3
"""test_person_roots.py — Run: python3 shared/test_person_roots.py (stdlib unittest only).
Every case runs the real CLI under a temp HOME with LIFEHACK_ROOT cleared, so no real pointer is read."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "person_roots.py")


class PersonRootsCase(unittest.TestCase):
    def setUp(self):
        self.home = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.home, True)
        os.makedirs(os.path.join(self.home, ".config", "lifehack"))

    def pointer(self, name, value):
        with open(os.path.join(self.home, ".config", "lifehack", name), "w", encoding="utf-8") as f:
            f.write(value + "\n")

    def mk(self, rel):
        p = os.path.join(self.home, rel)
        os.makedirs(p, exist_ok=True)
        return p

    def run_cli(self, *args, **env_extra):
        env = {k: v for k, v in os.environ.items() if k not in ("LIFEHACK_ROOT", "INGEST_LEGACY_ROOT_GLOB")}
        env.update(HOME=self.home, **env_extra)
        p = subprocess.run([sys.executable, SCRIPT, *args], env=env, capture_output=True, text=True)
        return p.returncode, p.stdout.splitlines()

    def test_fresh_install_is_all_empty(self):
        rc, out = self.run_cli("--shell")
        self.assertEqual(rc, 0)
        self.assertEqual([out[0], out[2]], ["NOTES=", "PERSONAL="])
        self.assertFalse([l for l in out if l.startswith("ZONE=")])

    def test_both_pointers_resolve(self):
        notes, code = self.mk("my notes"), self.mk("code")
        self.pointer("brain-root", notes)
        self.pointer("personal-code", code)
        rc, out = self.run_cli("--shell")
        self.assertEqual([out[0], out[2]], ["NOTES=" + notes, "PERSONAL=" + code])

    def test_env_notes_root_wins(self):
        self.pointer("brain-root", self.mk("a"))
        b = self.mk("b")
        rc, out = self.run_cli("--shell", LIFEHACK_ROOT=b)
        self.assertEqual(out[0], "NOTES=" + b)

    def test_code_zones_file(self):
        code, z1 = self.mk("code"), self.mk("old clone")
        self.pointer("personal-code", code)
        with open(os.path.join(code, "code-zones.txt"), "w", encoding="utf-8") as f:
            f.write("# comment\n%s\n~/old clone   # same folder again, via ~\n~/missing\n/\n~\n\n" % z1)
        rc, out = self.run_cli("--shell")
        self.assertEqual([l for l in out if l.startswith("ZONE=")], ["ZONE=" + z1])

    def test_missing_personal_pointer_target_gives_no_zones(self):
        self.pointer("personal-code", os.path.join(self.home, "gone"))
        rc, out = self.run_cli("--shell")
        self.assertEqual(out[2], "PERSONAL=")
        self.assertFalse([l for l in out if l.startswith("ZONE=")])

    def test_home_or_root_is_never_a_notes_root(self):
        self.pointer("brain-root", self.home)
        rc, out = self.run_cli("--shell")
        self.assertEqual(out[0], "NOTES=")

    def status(self, out):
        return {k: v for k, v in (x.split("=", 1) for x in out) if k.endswith("_STATUS")}

    def test_status_unset_when_nothing_names_a_folder(self):
        rc, out = self.run_cli("--shell")
        self.assertEqual(self.status(out), {"NOTES_STATUS": "unset", "PERSONAL_STATUS": "unset"})

    def test_status_missing_when_a_pointer_names_a_gone_folder(self):
        self.pointer("brain-root", os.path.join(self.home, "gone-notes"))
        self.pointer("personal-code", os.path.join(self.home, "gone-code"))
        rc, out = self.run_cli("--shell")
        self.assertEqual(self.status(out), {"NOTES_STATUS": "missing", "PERSONAL_STATUS": "missing"})
        self.assertEqual(out[0], "NOTES=")

    def test_status_missing_when_the_env_names_a_gone_folder(self):
        rc, out = self.run_cli("--shell", LIFEHACK_ROOT=os.path.join(self.home, "nope"))
        self.assertEqual(self.status(out)["NOTES_STATUS"], "missing")

    def test_status_ok(self):
        self.pointer("brain-root", self.mk("n"))
        self.pointer("personal-code", self.mk("c"))
        rc, out = self.run_cli("--shell")
        self.assertEqual(self.status(out), {"NOTES_STATUS": "ok", "PERSONAL_STATUS": "ok"})

    def owner(self, out):
        return next(l.split("=", 1)[1] for l in out if l.startswith("OWNER_GH_USER="))

    def test_owner_gh_user(self):
        sys.path.insert(0, os.path.dirname(SCRIPT)); import person_roots
        old = person_roots.DEPRECATED_OWNER_VAR
        env = {k: "" for k in ("LIFEHACK_OWNER_GH_USER", old)}
        self.assertEqual(self.owner(self.run_cli("--shell", **env)[1]), "")
        self.assertEqual(self.owner(self.run_cli("--shell", **dict(env, **{old: "olduser"}))[1]), "olduser")
        self.assertEqual(self.owner(self.run_cli("--shell", **dict(env, LIFEHACK_OWNER_GH_USER="newuser", **{old: "olduser"}))[1]), "newuser")

    def test_bad_usage(self):
        rc, _ = self.run_cli()
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()

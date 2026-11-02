#!/usr/bin/env python3
"""test_team_skills_root.py — Run: python3 shared/test_team_skills_root.py (stdlib unittest only).
Resolver tests for the team Drive skills folder (approved design 2026-11-01, SIMPLE build) and the
TEAM=/TEAM_STATUS= lines person_roots.py must print. Every case runs under a temp HOME."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

SHARED = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(SHARED, "team_skills_root.py")
PERSON_ROOTS = os.path.join(SHARED, "person_roots.py")


class TeamSkillsRootCase(unittest.TestCase):
    def setUp(self):
        self.home = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.home, True)
        os.makedirs(os.path.join(self.home, ".config", "lifehack"))

    def pointer(self, name, value):
        with open(os.path.join(self.home, ".config", "lifehack", name), "w", encoding="utf-8") as f:
            f.write(value + "\n")

    def run_cli(self, script, *args, **env_extra):
        env = {k: v for k, v in os.environ.items() if k not in ("LIFEHACK_ROOT", "INGEST_LEGACY_ROOT_GLOB")}
        env.update(HOME=self.home, **env_extra)
        p = subprocess.run([sys.executable, script, *args], env=env, capture_output=True, text=True)
        return p.returncode, p.stdout, p.stderr

    def mk(self, rel):
        p = os.path.join(self.home, rel)
        os.makedirs(p, exist_ok=True)
        return p

    # resolver outcomes (ok | unset | missing)
    def test_unset_when_no_pointer(self):
        rc, out, _ = self.run_cli(SCRIPT, "--shell")
        self.assertIn("TEAM_STATUS=unset", out)
        self.assertIn("TEAM=", out)

    def test_ok_when_pointer_names_real_folder(self):
        team = self.mk("drive/Team skills")
        self.pointer("team-skills", team)
        rc, out, _ = self.run_cli(SCRIPT, "--shell")
        self.assertIn("TEAM_STATUS=ok", out)
        self.assertIn("TEAM=" + team, out)

    def test_missing_when_pointer_names_gone_folder(self):
        self.pointer("team-skills", os.path.join(self.home, "gone"))
        rc, out, _ = self.run_cli(SCRIPT, "--shell")
        self.assertIn("TEAM_STATUS=missing", out)
        self.assertIn("TEAM=", out)  # empty path, never the dead pointer value

    def test_tilde_in_pointer_expands(self):
        team = self.mk("drive/Team skills")
        self.pointer("team-skills", "~/drive/Team skills")
        rc, out, _ = self.run_cli(SCRIPT, "--shell")
        self.assertIn("TEAM_STATUS=ok", out)
        self.assertIn("TEAM=" + team, out)

    def test_sharing_mode_file(self):
        rc, out, _ = self.run_cli(SCRIPT, "--shell")
        self.assertIn("SHARING=unset", out)
        self.pointer("team-sharing", "team")
        rc, out, _ = self.run_cli(SCRIPT, "--shell")
        self.assertIn("SHARING=team", out)
        self.pointer("team-sharing", "solo")
        rc, out, _ = self.run_cli(SCRIPT, "--shell")
        self.assertIn("SHARING=solo", out)

    # person_roots.py --shell carries the TEAM lines too
    def test_person_roots_carries_team_lines(self):
        team = self.mk("drive/Team skills")
        self.pointer("team-skills", team)
        rc, out, _ = self.run_cli(PERSON_ROOTS, "--shell")
        self.assertEqual(rc, 0)
        self.assertIn("TEAM=" + team, out)
        self.assertIn("TEAM_STATUS=ok", out)

    def test_person_roots_team_unset_by_default(self):
        rc, out, _ = self.run_cli(PERSON_ROOTS, "--shell")
        self.assertEqual(rc, 0)
        self.assertIn("TEAM_STATUS=unset", out)
        self.assertIn("TEAM=\n", out + "\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)

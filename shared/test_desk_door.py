#!/usr/bin/env python3
"""test_desk_door.py -- the desk door's checks (canon/desk-building-sop.md section 5) as code.

Run: python3 shared/test_desk_door.py

Every case builds a throwaway desk folder in a temp dir and runs shared/desk_door.py over it as a
subprocess. A good desk PASSes (exit 0); each planted fault is refused BY NAME (exit 1, the reason
names which check refused and what it found). The planted faults cover, at least: a card that does
not parse, a pointer to a missing file, a fourth fact on the card -- plus one fault for each of the
six checks. The job-door case uses the door's own LIFEHACK_JOBS_FILE test seam, never the real
manifest; nothing here touches the developer's notes folder.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DOOR = os.path.join(HERE, "desk_door.py")

GOOD_CARD = "name: planning\ncanon: canon/canon.md\ndiary: diary\n"


def run_door(desk, extra_env=None):
    env = dict(os.environ)
    env.pop("LIFEHACK_DESK_LIST", None)
    env.update(extra_env or {})
    return subprocess.run([sys.executable, DOOR, desk], capture_output=True, text=True, env=env)


class DeskDoorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="desk-door-test-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def desk(self, card=GOOD_CARD, canon="canon.md body", purpose="purpose body", extra=None):
        d = os.path.join(self.tmp, "planning")
        os.makedirs(os.path.join(d, "canon"))
        os.makedirs(os.path.join(d, "diary"))
        os.makedirs(os.path.join(d, "records"))
        with open(os.path.join(d, "desk.yaml"), "w", encoding="utf-8") as f:
            f.write(card)
        with open(os.path.join(d, "canon", "canon.md"), "w", encoding="utf-8") as f:
            f.write(canon)
        with open(os.path.join(d, "canon", "purpose.md"), "w", encoding="utf-8") as f:
            f.write(purpose)
        with open(os.path.join(d, "open-loops.md"), "w", encoding="utf-8") as f:
            f.write("open loops\n")
        for rel, text in (extra or {}).items():
            p = os.path.join(d, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(text)
        return d

    def test_good_desk_passes(self):
        r = run_door(self.desk())
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("PASS", r.stdout)

    def test_card_does_not_parse(self):
        r = run_door(self.desk(card="{this is [not yaml:\n  - broken"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("card does not parse", r.stdout)

    def test_fourth_fact_on_card(self):
        r = run_door(self.desk(card=GOOD_CARD + "mood: fine\n"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("fourth fact", r.stdout)
        self.assertIn("mood", r.stdout)

    def test_missing_card_fact(self):
        r = run_door(self.desk(card="canon: canon/canon.md\ndiary: diary\n"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("missing", r.stdout)
        self.assertIn("name", r.stdout)

    def test_pointer_to_missing_file(self):
        r = run_door(self.desk(card="name: planning\ncanon: canon/missing.md\ndiary: diary\n"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("missing", r.stdout)
        self.assertIn("canon/missing.md", r.stdout)

    def test_pointer_to_missing_diary(self):
        r = run_door(self.desk(card="name: planning\ncanon: canon/canon.md\ndiary: diary-old\n"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("missing", r.stdout)

    def test_fact_owned_elsewhere_on_card(self):
        r = run_door(self.desk(card=GOOD_CARD + "jobs: planning-diary daily\n"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("owned elsewhere", r.stdout)
        self.assertIn("jobs", r.stdout)

    def test_canon_outside_canon_folder(self):
        r = run_door(self.desk(card="name: planning\ncanon: notes/canon.md\ndiary: diary\n",
                               extra={"notes/canon.md": "elsewhere"}))
        self.assertEqual(r.returncode, 1)
        self.assertIn("canon does not sit", r.stdout)

    def test_canon_folder_missing_purpose(self):
        d = self.desk()
        os.remove(os.path.join(d, "canon", "purpose.md"))
        r = run_door(d)
        self.assertEqual(r.returncode, 1)
        self.assertIn("purpose.md", r.stdout)

    def test_job_row_refused_by_job_door(self):
        jobs = (
            "```jobs\n"
            "planning-bad | on | 1d | | | none | 0 | none | python3 run.py\n"
            "```\n"
        )
        r = run_door(self.desk(extra={"jobs.md": jobs}))
        self.assertEqual(r.returncode, 1)
        self.assertIn("job door", r.stdout)

    def test_good_job_row_passes(self):
        jobs = (
            "```jobs\n"
            "planning-ok | on | 1d | keeps the diary current | ~/planning-ok/last-run ~ ^planning-ok done count=[0-9]+$ | none | 0 | none | bash \"$LIFEHACK_PERSONAL_CODE/tools/runner.sh\"\n"
            "```\n"
        )
        d = self.desk(extra={"jobs.md": jobs, "tools/runner.sh": "#!/bin/bash\necho planning-ok done count=1\n"})
        os.chmod(os.path.join(d, "tools", "runner.sh"), 0o755)
        r = run_door(d, extra_env={"LIFEHACK_DESK_REPO": d})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_copied_shared_tool_refused(self):
        with open(os.path.join(HERE, "desk_list.py"), encoding="utf-8") as f:
            src = f.read()
        r = run_door(self.desk(extra={"tools/desk_list.py": src}))
        self.assertEqual(r.returncode, 1)
        self.assertIn("copied shared tool", r.stdout)
        self.assertIn("desk_list.py", r.stdout)

    def test_desk_id_resolved_through_desk_list(self):
        d = self.desk()
        # the real layout: <notes>/desks/<folder> with the registry beside the desks
        notes = os.path.join(self.tmp, "notes")
        desks = os.path.join(notes, "desks")
        os.makedirs(desks)
        shutil.move(d, os.path.join(desks, "planning"))
        reg = os.path.join(desks, "desk-registry.yaml")
        with open(reg, "w", encoding="utf-8") as f:
            f.write("schema_version: 2\ndesks:\n  - desk_id: planning\n    purpose_path: desks/planning/canon/purpose.md\n")
        r = run_door("planning", extra_env={"LIFEHACK_DESK_LIST": reg})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("PASS", r.stdout)

    def test_no_such_desk_id(self):
        r = run_door("no-such-desk")
        self.assertEqual(r.returncode, 1)
        self.assertIn("no desk folder", r.stdout)

    def test_missing_card(self):
        d = self.desk()
        os.remove(os.path.join(d, "desk.yaml"))
        r = run_door(d)
        self.assertEqual(r.returncode, 1)
        self.assertIn("card", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)

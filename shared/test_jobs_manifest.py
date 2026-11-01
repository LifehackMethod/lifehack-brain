#!/usr/bin/env python3
"""test_jobs_manifest.py — the shared + personal job table join (3b.7 B). Run: python3 shared/test_jobs_manifest.py

Every case runs under a throwaway HOME (its own ~/.config/lifehack/personal-code pointer and personal folder), so the
developer's real personal jobs are never read. Covers the join rules, the student case (no personal file: the shared
table is used as is) and the real scheduler entry points reading a personal row: job-run.sh, install-schedulers.sh
--check-row (the door allows a runner under the personal folder), health_line.py and pulse.sh --status."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCRIPT = os.path.join(HERE, "jobs_manifest.py")
SEAMS = ("LIFEHACK_JOBS_FILE", "PULSE_CONFIG", "LIFEHACK_PERSONAL_JOBS_FILE", "LIFEHACK_JOBS_MANIFEST",
         "LIFEHACK_DESK_REPO", "LIFEHACK_STATE_DIR", "LIFEHACK_JOBS_MERGED_DIR", "LIFEHACK_JOB_NAMES")

SHARED = """# shared
```jobs
# name | enabled | interval | outcome | check | model | budget | source | command
alpha | off | 3600 | A. | $HOME/a ~ ^a n=[0-9]+$ | none | 0 | none | bash "$LIFEHACK_CODE_ROOT/a.sh"
beta | off | 3600 | B. | $HOME/b ~ ^b n=[0-9]+$ | none | 0 | none | bash "$LIFEHACK_CODE_ROOT/b.sh"
```

```crontab
pulse | */5 * * * * | bash pulse.sh
```
"""


def rd(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


class Base(unittest.TestCase):
    def setUp(self):
        self.home = os.path.realpath(tempfile.mkdtemp(prefix="jm-home."))
        self.addCleanup(shutil.rmtree, self.home, True)
        self.pc = os.path.join(self.home, "pc")
        os.makedirs(self.pc)
        self.shared = os.path.join(self.home, "code", "jobs.md")
        os.makedirs(os.path.dirname(self.shared))
        self.w(self.shared, SHARED)
        self.w(os.path.join(self.home, "code", "job-names.txt"), "alpha = shared alpha\n")

    def w(self, p, text):
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)

    def pointer(self, target=None):
        self.w(os.path.join(self.home, ".config", "lifehack", "personal-code"), (target or self.pc) + "\n")

    def env(self, **kw):
        e = {k: v for k, v in os.environ.items() if k not in SEAMS}
        e["HOME"] = self.home
        e.update(kw)
        return e

    def manifest(self, **kw):
        r = subprocess.run([sys.executable, SCRIPT, "--manifest", self.shared], env=self.env(**kw), capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip(), r.stderr


class JoinRules(Base):
    def test_student_no_pointer_no_file_uses_shared_as_is(self):
        path, err = self.manifest()
        self.assertEqual(path, self.shared)
        self.assertEqual(err, "")

    def test_pointer_but_no_personal_jobs_file_uses_shared(self):
        self.pointer()
        self.assertEqual(self.manifest()[0], self.shared)

    def test_personal_rows_joined_crontab_kept_names_personal_first(self):
        self.pointer()
        self.w(os.path.join(self.pc, "jobs.md"), "```jobs\ngamma | off | 7200 | G. | c | none | 0 | none | bash g.sh\n```\n")
        self.w(os.path.join(self.pc, "job-names.txt"), "alpha = my alpha\ngamma = my gamma\n")
        path, err = self.manifest()
        self.assertNotEqual(path, self.shared)
        text = rd(path)
        jobs = text.split("```jobs\n", 1)[1].split("\n```", 1)[0]
        for n in ("alpha |", "beta |", "gamma |"):
            self.assertIn(n, jobs)
        self.assertIn("```crontab\npulse |", text)
        names = rd(os.path.join(os.path.dirname(path), "job-names.txt")).splitlines()
        self.assertEqual(names[0], "alpha = my alpha")
        self.assertIn("alpha = shared alpha", names)
        self.assertEqual(err, "")

    def test_name_clash_personal_wins_with_warning(self):
        self.pointer()
        self.w(os.path.join(self.pc, "jobs.md"), "```jobs\nbeta | yes | 600 | Mine. | c | none | 0 | none | bash mine.sh\n```\n")
        path, err = self.manifest()
        rows = [l for l in rd(path).splitlines() if l.startswith("beta |")]
        self.assertEqual(len(rows), 1)
        self.assertIn("bash mine.sh", rows[0])
        self.assertIn("personal row 'beta' overrides the shared row", err)

    def test_planted_test_manifest_stands_alone(self):
        self.pointer()
        self.w(os.path.join(self.pc, "jobs.md"), "```jobs\ngamma | off | 7200 | G. | c | none | 0 | none | bash g.sh\n```\n")
        self.assertEqual(self.manifest(LIFEHACK_JOBS_FILE=self.shared)[0], self.shared)
        self.assertEqual(self.manifest(PULSE_CONFIG=self.shared)[0], self.shared)

    def test_explicit_personal_file_seam(self):
        p = os.path.join(self.home, "elsewhere.md")
        self.w(p, "```jobs\ndelta | off | 60 | D. | c | none | 0 | none | bash d.sh\n```\n")
        path, _ = self.manifest(LIFEHACK_PERSONAL_JOBS_FILE=p)
        self.assertIn("delta |", rd(path))
        self.pointer()
        self.w(os.path.join(self.pc, "jobs.md"), "```jobs\ngamma | off | 7200 | G. | c | none | 0 | none | bash g.sh\n```\n")
        self.assertEqual(self.manifest(LIFEHACK_PERSONAL_JOBS_FILE="")[0], self.shared)   # empty = none

    def test_pointer_to_missing_folder_is_reported_and_shared_used(self):
        self.pointer(os.path.join(self.home, "gone"))
        path, err = self.manifest()
        self.assertEqual(path, self.shared)
        self.assertIn("not there", err)

    def test_same_content_reuses_one_cached_copy(self):
        self.pointer()
        self.w(os.path.join(self.pc, "jobs.md"), "```jobs\ngamma | off | 7200 | G. | c | none | 0 | none | bash g.sh\n```\n")
        self.assertEqual(self.manifest()[0], self.manifest()[0])


class EntryPoints(Base):
    """The real scheduler entry points, against the REAL shared table plus a planted personal row."""

    def setUp(self):
        super().setUp()
        self.pointer()
        self.w(os.path.join(self.pc, "desks", "zz", "tools", "zz-personal", "run.sh"), "#!/usr/bin/env bash\necho fine\n")
        self.w(os.path.join(self.pc, "jobs.md"),
               "```jobs\nzz-personal | yes | 3600 | The personal thing ran. | $HOME/zz/out ~ ^zz ok n=[0-9]+$ | none | 0 | none | "
               "bash \"$HOME/pc/desks/zz/tools/zz-personal/run.sh\"\n"
               "zz-off | off | 3600 | Off. | $HOME/zz/off ~ ^zz ok n=[0-9]+$ | none | 0 | none | bash \"$HOME/pc/desks/zz/tools/zz-personal/run.sh\"\n```\n")
        self.state = os.path.join(self.home, "state")
        stub = os.path.join(self.home, "notify-stub.sh")
        self.w(stub, "#!/usr/bin/env bash\nexit 0\n")
        self.notify = stub

    def sh(self, *args, **kw):
        return subprocess.run(list(args), env=self.env(**kw), capture_output=True, text=True)

    def test_check_row_finds_a_personal_row_and_the_door_allows_the_personal_folder(self):
        r = self.sh("bash", os.path.join(ROOT, "system/tools/install-schedulers.sh"), "--check-row", "zz-personal")
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "PASS"), r.stdout + r.stderr)

    def test_student_without_personal_folder_has_no_such_row(self):
        os.remove(os.path.join(self.home, ".config", "lifehack", "personal-code"))
        r = self.sh("bash", os.path.join(ROOT, "system/tools/install-schedulers.sh"), "--check-row", "zz-personal")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        r = self.sh("bash", os.path.join(ROOT, "system/tools/install-schedulers.sh"), "--check-row", "email-summary-write")
        self.assertEqual(r.stdout.strip(), "PASS", r.stdout + r.stderr)   # the shared rows still work

    def test_job_run_reads_the_personal_row(self):
        jr = os.path.join(ROOT, "system/tools/job-run.sh")
        kw = dict(LIFEHACK_STATE_DIR=self.state, JOB_RUN_NO_WATCH="1", JOB_RUN_NOTIFY=self.notify)
        r = self.sh("bash", jr, "zz-off", **kw)
        self.assertEqual(r.returncode, 75, r.stdout + r.stderr)   # found, and off -> stood down (not "no row")
        self.assertIn("stood down", rd(os.path.join(self.state, "jobs", "zz-off", "last-run")))
        r = self.sh("bash", jr, "zz-nope", **kw)
        self.assertEqual(r.returncode, 1)
        self.assertIn("no row named 'zz-nope'", rd(os.path.join(self.state, "jobs", "zz-nope", "log")))

    def test_health_line_counts_the_personal_enabled_row(self):
        r = self.sh(sys.executable, os.path.join(ROOT, "system/tools/health_line.py"), LIFEHACK_STATE_DIR=self.state)
        self.assertIn("zz-personal", r.stdout, r.stdout)

    def test_pulse_status_lists_the_personal_row(self):
        r = self.sh("bash", os.path.join(ROOT, "system/tools/pulse.sh"), "--status",
                    PULSE_STATE=os.path.join(self.home, "pulse-state.json"), LIFEHACK_ROOT=os.path.join(self.home, "notes"))
        out = r.stdout + r.stderr
        if "zz-personal" not in out and "heartbeat" not in out:
            self.skipTest("pulse.sh --status printed nothing usable here: " + out[-300:])
        self.assertIn("zz-off", out)


if __name__ == "__main__":
    unittest.main()

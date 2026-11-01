#!/usr/bin/env python3
"""test_personal_register.py — 3b.7 B: private rows live in <personal-code>/register.jsonl, never in the master.

Run: python3 system/register/tests/test_personal_register.py   (stdlib unittest; run-all-tests.sh discovers it)

A throwaway HOME and personal folder (a tool, a skill, a hook registration and a personal jobs.md) is harvested against THIS
checkout; nothing real is read or written (every call passes --private-root / an explicit out path).
Proves: the master output carries no private row; --personal-out writes them (incl. scheduled:private:<job>); without
it nothing personal is written; --update-register drops private rows from the master; generate.py's private target
draws from the personal register; omission_check.py and caller_lint.py read master + personal; with no personal
folder at all (the student case) everything runs and the master is unchanged in shape."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REG = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(REG))
sys.path.insert(0, REG)


def rows_of(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


class PersonalRegister(unittest.TestCase):
    def setUp(self):
        self.d = os.path.realpath(tempfile.mkdtemp(prefix="pr-test."))
        self.addCleanup(shutil.rmtree, self.d, True)
        self.pc = os.path.join(self.d, "pc")
        self.w("system/tools/zz_personal_tool.py", "#!/usr/bin/env python3\nprint('hi')\n")
        self.w("system/hooks/zz_personal_hook.sh", "#!/usr/bin/env bash\nexit 0\n")
        self.w(".claude/skills/zz-skill/SKILL.md", "---\nname: zz-skill\ndescription: a personal skill\n---\nbody\n")
        self.w("jobs.md", "```jobs\nzz-job | off | 3600 | o | c | none | 0 | none | bash \"$HOME/pc/system/tools/zz_personal_tool.py\"\n```\n")
        self.w("system/hooks/registrations.json", json.dumps({"hooks": {"SessionStart": [{"hooks": [
            {"type": "command", "command": "bash \"$HOME/pc/system/hooks/zz_personal_hook.sh\""}]}]}}))

    def w(self, rel, text):
        p = os.path.join(self.pc, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)

    def harvest(self, *args, private_root=None):
        cmd = [sys.executable, os.path.join(REG, "harvest.py"), "--no-cache", "--private-root", private_root or self.pc, *args]
        env = dict(os.environ, HOME=self.d)   # the user surface (~/.claude/settings.json) is the throwaway HOME's, never the real one
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, env=env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def test_master_is_public_only_and_personal_out_gets_the_private_rows(self):
        master, personal = os.path.join(self.d, "m.jsonl"), os.path.join(self.d, "p.jsonl")
        r = self.harvest("--out", master, "--personal-out", personal)
        self.assertEqual({x["repo"] for x in rows_of(master)}, {"public"})
        prow = rows_of(personal)
        ids = {x["id"] for x in prow}
        self.assertEqual({x["repo"] for x in prow}, {"private"})
        self.assertIn("scheduled:private:zz-job", ids)
        self.assertIn("tool:private:/system/tools/zz_personal_tool.py", ids)
        self.assertIn("skill:private:/.claude/skills/zz-skill/SKILL.md", ids)
        self.assertTrue(any(x["type"] == "hook" for x in prow), ids)
        self.assertIn("personal register", r.stdout)

    def test_without_personal_out_nothing_personal_is_written(self):
        master = os.path.join(self.d, "m.jsonl")
        r = self.harvest("--out", master)
        self.assertFalse(os.path.exists(os.path.join(self.pc, "register.jsonl")))
        self.assertIn("NOT written", r.stderr)
        self.assertEqual({x["repo"] for x in rows_of(master)}, {"public"})

    def test_student_with_no_personal_folder(self):
        master = os.path.join(self.d, "m.jsonl")
        r = self.harvest("--out", master, "--personal-out", private_root=os.path.join(self.d, "none"))
        self.assertEqual({x["repo"] for x in rows_of(master)}, {"public"})
        self.assertEqual(rows_of(os.path.join(self.d, "none", "register.jsonl")), [])
        self.assertNotIn("NOT written", r.stderr)

    def test_update_register_drops_private_rows_from_the_master(self):
        master = os.path.join(self.d, "m.jsonl")
        shutil.copy(os.path.join(REG, "register.jsonl"), master)
        with open(master, "a", encoding="utf-8") as f:
            f.write(json.dumps({"id": "tool:private:/system/tools/stale.py", "type": "tool", "repo": "private",
                                "path": "/system/tools/stale.py", "exists": True, "sha": "x", "needs": [], "returns": [],
                                "cost_bytes": None, "cost_ms": None}) + "\n")
        personal = os.path.join(self.d, "p.jsonl")
        self.harvest("--update-register", master, "--personal-out", personal)
        self.assertEqual({x["repo"] for x in rows_of(master)}, {"public"})
        self.assertIn("scheduled:private:zz-job", {x["id"] for x in rows_of(personal)})
        # a second update keeps the personal file (safe refresh, not a wipe)
        self.harvest("--update-register", master, "--personal-out", personal)
        self.assertIn("scheduled:private:zz-job", {x["id"] for x in rows_of(personal)})

    def test_consumers_read_master_plus_personal(self):
        self.harvest("--out", os.path.join(self.d, "m.jsonl"), "--personal-out")   # -> <pc>/register.jsonl
        import generate
        import omission_check
        import caller_lint
        import personal_register
        master = os.path.join(REG, "register.jsonl")
        rows, warns = personal_register.with_personal(rows_of(master), self.pc, master)
        self.assertEqual(warns, [])
        self.assertTrue(any(r["id"] == "scheduled:private:zz-job" for r in rows))
        # omission: the personal tool is registered (not flagged) once the personal register is read
        res_with = omission_check.run(rows, ROOT, self.pc)
        res_without = omission_check.run(rows_of(master), ROOT, self.pc)
        flagged = lambda res: {(x["repo"], x["path"]) for x in res["flagged"]}
        self.assertNotIn(("private", "/system/tools/zz_personal_tool.py"), flagged(res_with))
        self.assertIn(("private", "/system/tools/zz_personal_tool.py"), flagged(res_without))
        # caller lint: the personal jobs.md counts as a scheduled caller of the personal tool
        lint = caller_lint.lint_register(rows, ROOT, self.pc)
        v = [r for r in lint.rows if r["repo"] == "private" and r["rel"].endswith("zz_personal_tool.py")]
        self.assertTrue(v and v[0].get("verdict") != "UNCALLED", v)
        # generate: the private registrations target is written from the personal hook row
        out = os.path.join(self.d, "gen")
        result = generate.generate(master, out, ROOT, self.pc, None, skip_caller_lint=True, targets="public")
        self.assertTrue(result["schema_ok"], result.get("schema_problems"))
        regs = [t for t in result["targets"] if t.get("filename") == "registrations.json"]
        self.assertTrue(regs and regs[0].get("rows_written", 0) >= 1, regs)

    def test_a_broken_personal_row_never_refuses_generate(self):
        with open(os.path.join(self.pc, "register.jsonl"), "w", encoding="utf-8") as f:
            f.write("{not json\n")
            f.write(json.dumps({"id": "x", "type": "tool", "repo": "private"}) + "\n")   # fails schema
        import generate
        result = generate.generate(os.path.join(REG, "register.jsonl"), os.path.join(self.d, "gen"), ROOT, self.pc, None,
                                   skip_caller_lint=True, targets="public")
        self.assertTrue(result["schema_ok"], result.get("schema_problems"))
        self.assertTrue(any("personal register" in w for w in result["warnings"]), result["warnings"])


if __name__ == "__main__":
    unittest.main()

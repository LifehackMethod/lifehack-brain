#!/usr/bin/env python3
"""test_cmdreader.py - Run: python3 shared/test_cmdreader.py (stdlib unittest only).
Every row is a pair: a command seen as an ACTION and a lookalike seen as DATA. Fixtures use fictional paths.
Also loads the 32 rig cases (system/tools/rig/cases/cmdreader.jsonl) and checks what the reader sees in each."""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cmdreader as c  # noqa: E402

CASES = os.path.join(HERE, "..", "system", "tools", "rig", "cases", "cmdreader.jsonl")
SUBST = {"{CODE}": "/fx/code", "{DESK}": "/fx/notes/desk", "{HOME}": "/fx/home", "{NOTES}": "/fx/notes", "{REPO}": "/fx/repo"}


def wpaths(cmd, cwd="/fx/w"):
    return [w.abs or w.path for w in c.writes(c.read(cmd, cwd=cwd), cwd=cwd)]


class Splitting(unittest.TestCase):
    def test_segments_and_joiners(self):
        r = c.read("cd /a && ls | wc -l ; echo done || exit")
        self.assertTrue(r.ok)
        self.assertEqual([s.program for s in r.segments], ["cd", "ls", "wc", "echo", "exit"])
        self.assertEqual([s.joiner_before for s in r.segments], [None, "&&", "|", ";", "||"])

    def test_unpadded_semicolon(self):
        self.assertEqual(c.programs(c.read("cd /a || exit; git push")), ["cd", "exit", "git"])

    def test_quoted_operators_do_not_split(self):
        r = c.read('echo "a;b&&c" ; echo hi')
        self.assertEqual(len(r.segments), 2)
        self.assertEqual(r.segments[0].args, ["a;b&&c"])

    def test_newline_separates(self):
        self.assertEqual(c.programs(c.read("cd /a\ngit push")), ["cd", "git"])

    def test_loop_prefix_words_stripped(self):
        r = c.read("for f in a b; do ln -sf /x/$f /y/$f; done")
        self.assertIn("ln", c.programs(r))

    def test_unbalanced_quote_is_not_ok(self):
        r = c.read("echo 'unterminated; git push")
        self.assertFalse(r.ok)
        self.assertEqual(c.resolve_git("echo 'unterminated; git push", "push")[0], "AMBIGUOUS")

    def test_never_raises(self):
        self.assertFalse(c.read(None).ok)
        self.assertFalse(c.read("x" * 300000).ok)


class DataVsAction(unittest.TestCase):
    def test_heredoc_body_is_data(self):
        cmd = "cat > /fx/n/rec.md <<'EOF'\nSee system/hooks/x.sh; git push origin main > /fx/h/y.sh\nEOF"
        r = c.read(cmd)
        self.assertEqual([w.path for w in c.writes(r)], ["/fx/n/rec.md"])
        self.assertEqual(c.programs(r), ["cat"])
        self.assertFalse(c.is_git(r))
        self.assertIn("git push", c.all_text(r))

    def test_heredoc_with_apostrophes_parses(self):
        r = c.read("cat > /f <<EOF\nthe man said \"then git push and it's done\nEOF")
        self.assertTrue(r.ok)
        self.assertEqual(c.resolve_git(r, "push"), ("NOT_OURS", ""))

    def test_live_evidence_heredoc_text_naming_protected_file(self):
        # a guard once blocked a plan edit only because heredoc TEXT named a protected file
        cmd = "cat >> /fx/notes/p/a.md <<'EOF'\nNever edit hooks/hooks.json or system/register/register.jsonl by hand.\nEOF"
        self.assertEqual(wpaths(cmd), ["/fx/notes/p/a.md"])

    def test_quoted_text_is_never_a_command(self):
        r = c.read('grep -rn "git add -f" docs/')
        self.assertEqual(c.programs(r), ["grep"])
        self.assertFalse(c.is_git(r))

    def test_names_program_command_vs_argument(self):
        self.assertTrue(c.names_program(c.read("bash /fx/h/pm_persist.sh"), "pm_persist.sh"))
        self.assertTrue(c.names_program(c.read("/fx/h/pm_persist.sh --x"), "pm_persist.sh"))
        self.assertFalse(c.names_program(c.read("sed -n 1,60p /fx/h/pm_persist.sh"), "pm_persist.sh"))
        self.assertFalse(c.names_program(c.read("echo 'run pm_persist.sh'"), "pm_persist.sh"))

    def test_heredoc_to_shell_is_code(self):
        r = c.read("sh -s <<'EOF'\ncd /fx/repo\ngit push origin main\nEOF")
        self.assertEqual(c.resolve_git(r, "push"), ("DENY", "/fx/repo"))

    def test_heredoc_to_cat_is_not_code(self):
        r = c.read("cat <<'EOF'\ncd /fx/repo\ngit push origin main\nEOF")
        self.assertEqual(c.resolve_git(r, "push"), ("NOT_OURS", ""))


class Writes(unittest.TestCase):
    def test_redirect_forms(self):
        self.assertEqual(wpaths("echo x > /fx/a; echo y >> /fx/b; echo z 2>/dev/null; echo q 2>&1"), ["/fx/a", "/fx/b"])

    def test_tee_pipe(self):
        self.assertEqual(wpaths("printf x | tee -a /fx/t.sh >/dev/null"), ["/fx/t.sh"])

    def test_substitution_write_visible(self):
        self.assertEqual(wpaths("echo ok $(printf x > /fx/s.sh)"), ["/fx/s.sh"])

    def test_bash_c_write_visible(self):
        self.assertEqual(wpaths("bash -c \"echo 'exit 0' > /fx/b.sh\""), ["/fx/b.sh"])

    def test_python_c_writes(self):
        self.assertEqual(wpaths("python3 -c \"from pathlib import Path; Path('/fx/p.sh').write_text('x')\""), ["/fx/p.sh"])
        self.assertEqual(wpaths("python3 -c \"open('/fx/q','w').write('x')\""), ["/fx/q"])

    def test_python_copy_with_join(self):
        w = c.writes(c.read("python3 -c \"import shutil,os; shutil.copy(os.path.join('/fx/code','shared','n','s.sh'), '/fx/d/s.sh')\""))
        self.assertEqual((w[0].path, w[0].srcs), ("/fx/d/s.sh", ["/fx/code/shared/n/s.sh"]))

    def test_cp_target_flag(self):
        self.assertEqual(wpaths("cp -t /fx/dir /fx/a"), ["/fx/dir/a"])
        self.assertEqual(wpaths("cp /fx/a /fx/b"), ["/fx/b"])

    def test_sed_i_vs_sed_n(self):
        self.assertEqual(wpaths("sed -i.bak 's/a/b/' /fx/f"), ["/fx/f"])
        self.assertEqual(wpaths("sed -n '1,5p' /fx/f"), [])

    def test_readers_write_nothing(self):
        self.assertEqual(wpaths("grep -n 'x' /fx/f | head -3; cat /fx/f; ls /fx"), [])

    def test_variables_in_same_command(self):
        self.assertEqual(wpaths("D=/fx/hooks && F=$D/z.sh && printf x > \"$F\""), ["/fx/hooks/z.sh"])
        self.assertEqual(wpaths("SRC=/fx/code/shared/n; DST=/fx/d; cp \"$SRC/s.sh\" \"$DST/\""), ["/fx/d/s.sh"])

    def test_unknown_variable_stays_unresolved(self):
        r = c.read("echo x > $UNKNOWN/f")
        self.assertEqual(c.writes(r)[0].path, "$UNKNOWN/f")

    def test_substitution_variable_unresolved_unless_trusted(self):
        r = c.read('N=$(python3 /fx/code/shared/brain_root.py --quiet); echo x >> "$N/log.md"')
        self.assertIn("$N", c.writes(r)[0].path)

    def test_cd_chain_resolves_relative(self):
        self.assertEqual(wpaths("cd /fx/a && cd b && cp x y"), ["/fx/a/b/y"])
        self.assertEqual(wpaths("cd sub && echo x > f", cwd="/fx/w"), ["/fx/w/sub/f"])


class Git(unittest.TestCase):
    def test_alias_variables(self):
        r = c.read("G=git; ADD=add; $G -C /fx/repo $ADD -A")
        self.assertTrue(c.is_git(r, "add"))

    def test_push_targets(self):
        self.assertEqual(c.resolve_git("git -C /fx/r push", "push"), ("DENY", "/fx/r"))
        self.assertEqual(c.resolve_git("cd /fx/r || exit; git push", "push"), ("DENY", "/fx/r"))
        self.assertEqual(c.resolve_git("cd /fx/r || echo no; git push", "push"), ("REFUSE_AMBIGUOUS", ""))
        self.assertEqual(c.resolve_git("(cd /fx/r && git push)", "push"), ("REFUSE_AMBIGUOUS", ""))
        self.assertEqual(c.resolve_git("cd /fx/r && git log | head && git push", "push"), ("DENY", "/fx/r"))
        self.assertEqual(c.resolve_git("git push", "push"), ("DENY", ""))
        self.assertEqual(c.resolve_git('git commit -m "later: git push"', "push"), ("NOT_OURS", ""))

    def test_nested_bash_c(self):
        self.assertEqual(c.resolve_git("bash -c 'cd /fx/r && git push origin main'", "push"), ("DENY", "/fx/r"))

    def test_argv_drops_redirections(self):
        r = c.read("git -C /fx/r push -u origin main 2>&1 | tail -3")
        self.assertEqual(c.git_argv(r, "push"), ["-u", "origin", "main"])


class RigCases(unittest.TestCase):
    """What the reader sees in each of the 32 rig cases (the rig itself grades the guards)."""

    @classmethod
    def setUpClass(cls):
        with open(CASES, encoding="utf-8") as f:
            cls.cases = [json.loads(line) for line in f if line.strip()]

    def cmd(self, case):
        s = case["tool_input"]["command"]
        for k, v in SUBST.items():
            s = s.replace(k, v)
        return s

    def test_count(self):
        self.assertEqual(len(self.cases), 32)

    def test_every_case_parses_or_is_failsafe(self):
        for case in self.cases:
            r = c.read(self.cmd(case), cwd="/fx/repo")
            self.assertEqual(r.ok, not case["id"].startswith("cr-fs-"), case["id"])

    def test_pass_cases_show_no_protected_action(self):
        for case in self.cases:
            if case["id"].startswith("cr-fa-"):
                cmd = self.cmd(case)
                r = c.read(cmd, cwd="/fx/repo")
                bad = [p for p in wpaths(cmd, "/fx/repo") if "/system/hooks/" in p or p.endswith("settings.json")]
                self.assertEqual(bad, [], case["id"])
                self.assertFalse(c.names_program(r, "pm_persist.sh"), case["id"])
                self.assertFalse(c.is_git(r, "add") or c.is_git(r, "push"), case["id"])
                self.assertFalse([s for s in c.iter_segments(r) if s.program == "gws"], case["id"])

    def test_block_cases_show_the_action(self):
        def src_shared(r, w):
            return any("/shared/" in x for y in c.writes(r) for x in y.srcs)
        want = {
            "cr-sl-var-path-hook-write": lambda r, w: any("/system/hooks/zz_righook.sh" in p for p in w),
            "cr-sl-var-path-copy-shared": src_shared,
            "cr-sl-alias-var-git-add": lambda r, w: c.is_git(r, "add"),
            "cr-sl-one-line-python-copy-shared": src_shared,
            "cr-sl-tee-into-settings": lambda r, w: any(p.endswith(".claude/settings.json") for p in w),
            "cr-sl-git-hooks-via-cat-heredoc": lambda r, w: any(".git/hooks/pre-commit" in p for p in w),
            "cr-sl-commit-inside-bash-c-single-quoted": lambda r, w: c.is_git(r, "commit"),
            "cr-sl-push-in-heredoc-to-bash": lambda r, w: c.resolve_git(r, "push") == ("DENY", "/fx/repo"),
            "cr-sl-copy-shared-into-notes-hard": src_shared,
            "cr-adv-write-in-command-substitution": lambda r, w: any("zz_adv_subst.sh" in p for p in w),
            "cr-adv-write-via-tee-pipe": lambda r, w: any("zz_adv_tee.sh" in p for p in w),
            "cr-adv-write-in-bash-c-string": lambda r, w: any("zz_adv_bashc.sh" in p for p in w),
            "cr-adv-write-in-python-c": lambda r, w: any("zz_adv_py.sh" in p for p in w),
            "cr-adv-write-after-quoted-semicolon": lambda r, w: any("zz_adv_semi.sh" in p for p in w),
        }
        seen = set()
        for case in self.cases:
            if case["id"] in want:
                cmd = self.cmd(case)
                r = c.read(cmd, cwd="/fx/repo")
                self.assertTrue(want[case["id"]](r, wpaths(cmd, "/fx/repo")), case["id"])
                seen.add(case["id"])
        self.assertEqual(seen, set(want))

    def test_failsafe_cases(self):
        for case in self.cases:
            if case["id"].startswith("cr-fs-"):
                r = c.read(self.cmd(case))
                self.assertFalse(r.ok)
                self.assertTrue(r.parse_error)


class CLI(unittest.TestCase):
    def test_cli_json_exit_zero(self):
        import subprocess
        p = subprocess.run([sys.executable, os.path.join(HERE, "cmdreader.py")], input="echo x > /fx/a", capture_output=True, text=True)
        self.assertEqual(p.returncode, 0)
        d = json.loads(p.stdout)
        self.assertTrue(d["ok"])
        self.assertEqual(d["writes"][0]["path"], "/fx/a")
        p = subprocess.run([sys.executable, os.path.join(HERE, "cmdreader.py")], input="echo 'oops", capture_output=True, text=True)
        self.assertEqual(p.returncode, 0)
        self.assertFalse(json.loads(p.stdout)["ok"])


if __name__ == "__main__":
    unittest.main()

"""Commit 4 (coordinator 38, route A): the front room's `claude -p` children run the windows' hooks through ONE helper
(claude_child): --plugin-dir from the code-root pointer, window flags from the engine's own environment. Fakes only; the
real model is never run."""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import hashlib, os, sys, tempfile, unittest
from unittest import mock
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import claude_child, morning  # noqa: E402


class Flags(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="cc-")
        self.addCleanup(_sh.rmtree, self.d, True)
        self.ptr = os.path.join(self.d, "code-root")
        with open(self.ptr, "w", encoding="utf-8") as f:
            f.write("/some/harness/root\nsecond line ignored\n")
        self.env = {"GC_CODE_ROOT_FILE": self.ptr, "GC_CHILD_SETTING_SOURCES": "project,local", "GC_CHILD_SETTINGS": "/x/lab-settings.json"}
        p = mock.patch.dict(os.environ, self.env)
        p.start()
        self.addCleanup(p.stop)
        self.bin = os.path.join(self.d, "claude")
        self.argv_out = os.path.join(self.d, "argv.txt")
        self.envf = os.path.join(self.d, "env.txt")
        with open(self.bin, "w", encoding="utf-8") as f:
            f.write('#!/bin/sh\nprintf "%%s\\n" "$@" > "%s"\nenv > "%s"\ncat > /dev/null\necho words\n' % (self.argv_out, self.envf))
        os.chmod(self.bin, 0o755)

    def test_a_argv_carries_the_pointer_value_and_the_window_flags_at_both_morning_sites(self):
        m = morning.ClaudeLensModel(claude=self.bin, home=self.d)
        cmd = m.build_cmd(self.d)
        i = cmd.index("--plugin-dir")
        self.assertEqual(cmd[i + 1], "/some/harness/root")
        self.assertEqual(cmd[cmd.index("--setting-sources") + 1], "project,local")
        self.assertEqual(cmd[cmd.index("--settings") + 1], "/x/lab-settings.json")
        plain = morning.ClaudeCliModel(claude=self.bin, home=self.d)
        self.assertEqual(plain.complete("hi"), ("words", None))
        got = open(self.argv_out, encoding="utf-8").read().splitlines()
        self.assertEqual(got[got.index("--plugin-dir") + 1], "/some/harness/root")
        self.assertIn("--setting-sources", got)
        self.assertIn("--settings", got)

    def test_a_other_sites_use_the_same_helper(self):
        import batch_reader
        self.assertEqual(batch_reader._window_flags(), claude_child.window_flags()[0])
        self.assertIn("--plugin-dir", batch_reader._window_flags())
        env = batch_reader._claude_env()
        self.assertFalse(set(claude_child.ENV_VARS) & set(env))              # the variables only become argv

    def test_b_a_plugin_cache_path_is_refused_with_a_warning(self):
        with open(self.ptr, "w", encoding="utf-8") as f:
            f.write("/opt/example/.claude/plugins/cache/some-plugin/1.0\n")
        flags, warn = claude_child.window_flags()
        self.assertEqual(flags, [])
        self.assertIn("window flags missing", warn)
        self.assertNotIn("--plugin-dir", morning.ClaudeLensModel(claude=self.bin, home=self.d).build_cmd(self.d))

    def test_c_the_pointer_file_is_byte_identical_after_the_argv_and_a_fake_child(self):
        before = hashlib.sha256(open(self.ptr, "rb").read()).hexdigest()
        m = morning.ClaudeLensModel(claude=self.bin, home=self.d)
        m.build_cmd(self.d)
        self.assertEqual(m.complete_in("hi", self.d), ("words", None))
        morning.ClaudeCliModel(claude=self.bin, home=self.d).complete("hi")
        self.assertEqual(hashlib.sha256(open(self.ptr, "rb").read()).hexdigest(), before)
        envtxt = open(self.envf, encoding="utf-8").read()
        for k in claude_child.ENV_VARS:
            self.assertNotIn(k + "=", envtxt)                                # never passed into the child's environment

    def test_d_missing_env_gives_nothing_and_a_warning_and_the_hand_run_says_so(self):
        for k in ("GC_CHILD_SETTING_SOURCES", "GC_CHILD_SETTINGS"):
            os.environ.pop(k)
        flags, warn = claude_child.window_flags()
        self.assertEqual(flags, [])
        self.assertIn("window flags missing: GC_CHILD_SETTING_SOURCES, GC_CHILD_SETTINGS", warn)
        self.assertNotIn("--plugin-dir", morning.ClaudeLensModel(claude=self.bin, home=self.d).build_cmd(self.d))
        os.remove(self.ptr)
        self.assertIn("code-root pointer", claude_child.window_flags()[1])
        lines = []
        rc = morning.hand_run(["--dry-run", "--desk", "d", "--day", "2026-11-21", "--drop", self.d, "--notes-root", self.d,
                               "--db", os.path.join(self.d, "none.db")], out=lines.append)
        self.assertIn("window flags missing", "\n".join(lines))


if __name__ == "__main__":
    unittest.main()

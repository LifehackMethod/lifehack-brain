"""plugin_root() in the PINNED layout (tools/grand-central/jobs/deploy-live.sh): the engine sits at live/<sha>/grand_central/
with only a few shared helpers beside it, so dirname(SHARED) is live/, not the plugin. Live jobs get LIFEHACK_CODE_ROOT from
job-run.sh; plugin_root() must use it when it holds the plugin (.claude-plugin/plugin.json), else fall back. Synthetic temp
folders plus the real worktree as the plugin; HOME is a temp folder, nothing real is written."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN = os.path.dirname(os.path.dirname(ENGINE))        # the real plugin folder this test runs in
HELPERS = ("person_roots.py", "personal_code_root.py", "brain_root.py")   # what deploy-live.sh copies beside the engine

PROBE = (
    "import json, os, sys\n"
    "sys.path.insert(0, os.getcwd())\n"
    "import gc_settings, rig_env\n"
    "print(json.dumps({'root': gc_settings.plugin_root(), 'name': gc_settings.harness_name(),\n"
    "  'door': rig_env.EMAIL_DOOR_DIR, 'calendar': rig_env.SAFE_CALENDAR, 'tasks': rig_env.SAFE_TASKS}))\n"
)


class PinnedLayout(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        live = os.path.join(self.tmp.name, "live", "abc123def")
        os.makedirs(live)
        self.pinned = os.path.join(live, "grand_central")
        shutil.copytree(ENGINE, self.pinned, ignore=shutil.ignore_patterns("__pycache__", "tests"))
        for h in HELPERS:
            shutil.copy(os.path.join(ENGINE, "..", h), os.path.join(live, h))
        self.live_parent = os.path.dirname(live)
        self.home = os.path.join(self.tmp.name, "home")
        os.makedirs(self.home)

    def probe(self, code_root):
        env = {k: v for k, v in os.environ.items()
               if k not in ("LIFEHACK_CODE_ROOT", "GC_SETUP_DIR", "GC_DATA_ROOT", "PYTHONPATH")}
        env["HOME"] = self.home
        env["GC_DATA_ROOT"] = os.path.join(self.tmp.name, "data")
        if code_root is not None:
            env["LIFEHACK_CODE_ROOT"] = code_root
        out = subprocess.run([sys.executable, "-c", PROBE], cwd=self.pinned, env=env,
                             capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout)

    def test_env_points_at_the_plugin(self):
        with open(os.path.join(PLUGIN, ".claude-plugin", "plugin.json"), encoding="utf-8") as f:
            real_name = json.load(f)["name"]
        r = self.probe(PLUGIN)
        self.assertEqual(r["root"], PLUGIN)
        self.assertEqual(r["name"], real_name)
        self.assertNotEqual(r["name"], "live")
        self.assertTrue(os.path.isdir(r["door"]), r["door"])
        self.assertTrue(os.path.isfile(r["calendar"]), r["calendar"])
        self.assertTrue(os.path.isfile(r["tasks"]), r["tasks"])

    def test_env_at_a_non_plugin_folder_falls_back(self):
        r = self.probe(self.home)                      # a real folder with no .claude-plugin/plugin.json
        self.assertEqual(os.path.realpath(r["root"]), os.path.realpath(self.live_parent))

    def test_env_naming_a_missing_folder_falls_back(self):
        r = self.probe(os.path.join(self.tmp.name, "nope"))
        self.assertEqual(os.path.realpath(r["root"]), os.path.realpath(self.live_parent))

    def test_env_unset_falls_back(self):
        r = self.probe(None)
        self.assertEqual(os.path.realpath(r["root"]), os.path.realpath(self.live_parent))


if __name__ == "__main__":
    unittest.main()

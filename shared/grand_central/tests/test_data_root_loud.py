"""gc_settings.data_root: an expected owner setup that cannot be read fails loudly; no owner setup at all keeps the student
default. Synthetic folders only."""
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import gc_settings as S


class T(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env = {k: v for k, v in os.environ.items() if k not in ("GC_DATA_ROOT", "GC_SETUP_DIR")}
        self.env["HOME"] = self.tmp.name

    def run_with(self, extra, personal=""):
        env = dict(self.env, **extra)
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(S, "personal_code_root", lambda: personal):
            return S.data_root()

    def test_named_setup_without_gc_json_raises(self):
        empty = os.path.join(self.tmp.name, "setup")
        os.makedirs(empty)
        with self.assertRaises(S.SettingsError):
            self.run_with({"GC_SETUP_DIR": empty})

    def test_named_setup_that_is_not_a_folder_raises(self):
        with self.assertRaises(S.SettingsError):
            self.run_with({"GC_SETUP_DIR": os.path.join(self.tmp.name, "nope")})

    def test_personal_root_without_a_resolving_setup_raises(self):
        with self.assertRaises(S.SettingsError):
            self.run_with({}, personal=self.tmp.name)

    def test_no_owner_setup_at_all_keeps_the_student_default(self):
        got = self.run_with({})
        self.assertTrue(got.startswith(self.tmp.name) and got.endswith("grand-central"))

    def test_env_data_root_still_wins(self):
        self.assertEqual(self.run_with({"GC_DATA_ROOT": "/tmp/gc-x"}, personal=self.tmp.name), "/tmp/gc-x")


if __name__ == "__main__":
    unittest.main()

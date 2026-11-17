"""Phase 4 step 4.1: diary names come from ONE pattern + setup; shared code never hard-codes a desk's diary name."""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import os, re, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import diary_names  # noqa: E402

# shared code = every module of the engine (top-level .py) and its sub-packages; not the tests, fixtures or the guard's own files
SCAN = sorted(f for f in os.listdir(ROOT) if (f.endswith(".py") and not f.startswith("test_") and f != "check_personal_values.py")
              or f in ("signals", "world_model", "handoff", "tools", "reader"))


def hardcoded(text):
    """Lines that name a desk's diary literally (Main-Diary in a comment/docstring is allowed only via setup)."""
    return [l for l in text.splitlines() if re.search(r"\b[A-Z][a-z]+-Diary\b|\bdesk-[a-d][ _-]diary\b", l, re.I) and "{display}" not in l]


class T(unittest.TestCase):
    def test_pattern_gives_bravo_diary_for_desk_b(self):
        self.assertEqual(diary_names.diary_name("desk-b"), "Bravo-Diary")
        self.assertEqual(diary_names.diary_name("desk-c"), "Charlie-Diary")
        self.assertEqual(diary_names.diary_name("desk-d"), "Delta-Diary")

    def test_main_desk_maps_to_main_diary(self):
        self.assertEqual(diary_names.diary_name("desk-a"), "Main-Diary")

    def test_unknown_desk_is_never_guessed(self):
        with self.assertRaises(KeyError):
            diary_names.diary_name("nobody")

    def test_PLANTED_hardcoded_desk_diary_name_in_shared_code_is_caught(self):
        self.assertTrue(hardcoded('p = os.path.join(root, "Bravo-Diary")'))
        self.assertTrue(hardcoded("# writes the desk-a diary"))
        self.assertTrue(hardcoded('x = "desk-a-diary"'))

    def test_shared_code_has_no_hardcoded_desk_diary_name(self):
        bad = []
        for rel in SCAN:
            p = os.path.join(ROOT, rel)
            files = [p] if os.path.isfile(p) else [os.path.join(d, f) for d, _, fs in os.walk(p) for f in fs
                                                   if f.endswith((".py", ".sh")) and "fixtures" not in d and "tests" not in d]
            for f in files:
                if os.path.basename(f) == "diary_names.py":
                    continue
                with open(f, encoding="utf-8") as fh:
                    text = fh.read()
                for l in hardcoded(text):
                    bad.append("%s: %s" % (os.path.relpath(f, ROOT), l.strip()))
        self.assertEqual(bad, [])


if __name__ == "__main__":
    unittest.main()

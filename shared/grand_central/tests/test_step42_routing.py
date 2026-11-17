"""Phase 4 step 4.2: routing by part of life. Planted cases, each run first against a BROKEN router the check must
catch, then the real one. Synthetic data; a temp database only (never the live rig.db)."""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import glob, json, os, re, sqlite3, sys, tempfile, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import step3_fixture  # noqa: E402
import migrate, store_graph as sg  # noqa: E402
import routing  # noqa: E402

TABLE = {"main_diary": "Main-Diary", "diary_pattern": "{desk}-Diary", "parts_to_desk": {"part-b": "Bravo", "part-c": "Charlie"}}
LABELS = {"labels": {"Example-B-Inbox": {"life_part": "part-b"}, "Plain": {}, "Odd": {"life_part": "Gardening"}}}


def broken_default_nowhere(part, table):      # plant 1: no part of life -> nowhere
    return routing.route(part, table) if part else None


def broken_guesser(part, table):              # plant 2: guesses a desk from free text
    for k, v in table["parts_to_desk"].items():
        if part and k.lower() in part.lower():
            return routing.diary_name(v, table)
    return table["main_diary"]


class T(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        c = self.c = sqlite3.connect(os.path.join(self.tmp.name, "t.db"), isolation_level=None)
        for p in sorted(glob.glob(os.path.join(ROOT, "migrations", "*.sql"))):
            migrate.apply_file(c, p, int(os.path.basename(p)[:3]))
        step3_fixture.seed_domain_vocab(c)

    def tearDown(self):
        self.tmp.cleanup()

    def test_part_b_label_routes_to_bravo_diary(self):
        r = routing.route_item({"label": "Example-B-Inbox"}, LABELS, TABLE)
        self.assertEqual(r["diary"], "Bravo-Diary")

    def test_no_part_of_life_goes_to_main(self):
        self.assertEqual(routing.route_item({"label": "Plain"}, LABELS, TABLE)["diary"], "Main-Diary")
        self.assertEqual(routing.route_item({}, LABELS, TABLE)["diary"], "Main-Diary")
        self.assertIsNotNone(routing.route(None, TABLE))
        self.assertIsNone(broken_default_nowhere(None, TABLE))       # the plant is caught: it returns nowhere

    def test_unowned_part_and_free_text_never_guessed(self):
        self.assertEqual(routing.route("Gardening", TABLE), "Main-Diary")
        self.assertEqual(routing.route("Bravo's agent says Charlie", TABLE), "Main-Diary")
        self.assertNotEqual(broken_guesser("part-b's agent says", TABLE), "Main-Diary")   # plant caught

    def test_sender_domain_fact_routes_when_no_label(self):
        d = sg.thing(self.c, "domain", "property-site.example")
        sg._lfact(self.c, d, "domain", "part-c", "t")
        r = routing.route_item({"label": None, "sender": "x@mail.property-site.example"}, LABELS, TABLE, self.c)
        self.assertEqual((r["part_of_life"], r["diary"]), ("part-c", "Charlie-Diary"))
        self.assertEqual(routing.route_item({"sender": "x@nobody.example"}, LABELS, TABLE, self.c)["diary"], "Main-Diary")

    def test_label_wins_over_sender(self):
        r = routing.route_item({"label": "Example-B-Inbox", "sender": "x@property-site.example"}, LABELS, TABLE, self.c)
        self.assertEqual(r["diary"], "Bravo-Diary")

    def test_no_desk_name_hardcoded_in_shared_code(self):
        src = open(os.path.join(ROOT, "routing.py"), encoding="utf-8").read()
        for desk in TABLE["parts_to_desk"].values():
            self.assertIsNone(re.search(r"\b%s\b" % desk, src), desk + " is hard-coded in shared code")
        self.assertIsNone(re.search(r"\bDelta\b|\bdesk-[a-d]\b", src))

    def test_setup_table_loads_and_is_proposed(self):
        t = routing.load_table()
        self.assertIn("PROPOSED", t["_status"])
        self.assertEqual(routing.route(None, t), "Main-Diary")
        self.assertEqual(routing.route("part-b", t), "Bravo-Diary")


if __name__ == "__main__":
    unittest.main()

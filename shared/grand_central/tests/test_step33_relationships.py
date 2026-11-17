"""Phase 3 step 3.3: the five relationships and who may write them. Temp databases, synthetic data only.
Each planted case runs FIRST against a database built without migration 023 (the lock missing) and must be ACCEPTED there,
which is the check failing; then against the real schema, where it must be refused. His own placement must be accepted."""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import glob
import os
import sqlite3
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import migrate, store_graph as sg  # noqa: E402


def build(with_023=True):
    tmp = tempfile.TemporaryDirectory()
    c = sqlite3.connect(os.path.join(tmp.name, "r.db"), isolation_level=None)
    for path in sorted(glob.glob(os.path.join(ROOT, "migrations", "*.sql"))):
        n = int(os.path.basename(path)[:3])
        if n == 23 and not with_023:
            continue
        if n > 23:
            continue
        migrate.apply_file(c, path, n)
    return tmp, c


def things(c):
    t = {}
    for key, kind in (("me", "person"), ("boss", "person"), ("big", "person"), ("org", "organization"), ("org2", "organization"),
                      ("proj", "project"), ("ev", "event")):
        t[key] = sg.thing(c, kind, key.title(), key="%s:%s" % (kind, key))
    c.execute("INSERT INTO kg_answers(question,words,asked_by,said_on,subject_key,subject_kind,subject_name,recorded_at,words_kind) "
              "VALUES('q','he said so','t','2026-11-01','person:me','person','Me','2026-11-01T00:00:00Z','verbatim')")
    t["ans"] = c.execute("SELECT max(id) FROM kg_answers").fetchone()[0]
    return t


def refused(fn):
    try:
        fn()
    except (sg.Refused, sqlite3.IntegrityError, sqlite3.DatabaseError):
        return True
    return False


def raw(c, a, kind, b, who="owner", ans=None, cert="sure", src="answer", until=None):
    c.execute("INSERT INTO kg_links(from_id,kind,to_id,who,certainty,source_kind,answer_id,true_until,created_at) VALUES(?,?,?,?,?,?,?,?,'t')",
              (a, kind, b, who, cert, src, ans, until))


class Relationships(unittest.TestCase):
    def plants(self, c, t, door):
        """-> {name: was_refused}. `door` is 'front' (sg.add_link) or 'trigger' (raw SQL, the second lock)."""
        def put(a, kind, b, who="owner", ans=None, cert="sure", src="answer"):
            if door == "front":
                return lambda: sg.add_link(c, a, kind, b, who, cert, src, answer_id=ans)
            return lambda: raw(c, a, kind, b, who, ans, cert, src)
        out = {}
        raw(c, t["me"], "reports_to", t["boss"], "owner", t["ans"]) if False else None
        sg.add_link(c, t["me"], "reports_to", t["boss"], "owner", "sure", "answer", answer_id=t["ans"])
        sg.add_link(c, t["boss"], "reports_to", t["big"], "owner", "sure", "answer", answer_id=t["ans"])
        out["cycle"] = refused(put(t["big"], "reports_to", t["me"], "owner", t["ans"]))
        out["self_loop"] = refused(put(t["me"], "reports_to", t["me"], "owner", t["ans"]))
        out["wrong_ends_reports_to_org"] = refused(put(t["me"], "reports_to", t["org"], "owner", t["ans"]))
        out["wrong_ends_member_of_person"] = refused(put(t["me"], "member_of", t["boss"], "owner", t["ans"]))
        out["wrong_ends_knows_event"] = refused(put(t["ev"], "knows", t["me"], "owner", t["ans"]))
        out["code_reports_to"] = refused(put(t["boss"], "reports_to", t["me"], "code", None, "sure", "code"))
        out["code_member_of"] = refused(put(t["boss"], "member_of", t["org"], "code", None, "sure", "code"))
        out["code_involves_project"] = refused(put(t["proj"], "involves", t["me"], "code", None, "sure", "code"))
        out["code_guess_involves_event"] = refused(put(t["ev"], "involves", t["me"], "code", None, "likely", "code"))
        return out

    def test_PLANTED_each_caught_only_by_the_lock_then_refused_with_it(self):
        tmp, c = build(with_023=False)
        t = things(c)
        loose = self.plants(c, t, "trigger")                 # no 023: the raw writes go through (the check fails)
        sg_check = [k for k, v in loose.items() if v]
        # the old placement trigger (021) already refused code-written placements; everything else slipped through
        for k in ("cycle", "self_loop", "wrong_ends_reports_to_org", "wrong_ends_member_of_person", "wrong_ends_knows_event",
                  "code_involves_project", "code_guess_involves_event"):
            self.assertNotIn(k, sg_check, "%s should be accepted without 023, was refused" % k)
        tmp.cleanup()
        tmp, c = build(True)
        t = things(c)
        tight = self.plants(c, t, "trigger")
        self.assertTrue(all(tight.values()), tight)
        tmp.cleanup()

    def test_front_door_refuses_in_words(self):
        tmp, c = build(True)
        t = things(c)
        front = self.plants(c, t, "front")
        self.assertTrue(all(front.values()), front)
        tmp.cleanup()

    def test_loop_message_and_replacing_a_line_is_not_a_loop(self):
        tmp, c = build(True)
        t = things(c)
        a = lambda x, y: sg.add_link(c, t[x], "reports_to", t[y], "owner", "sure", "answer", answer_id=t["ans"])
        a("me", "boss"), a("boss", "big")
        with self.assertRaisesRegex(sg.Refused, "loop"):
            a("big", "me")
        a("me", "boss")                                         # same line again: replaces itself, no loop
        a("me", "big")                                          # a second, shorter line is not a loop
        self.assertEqual(c.execute("SELECT count(*) FROM kg_links WHERE kind='reports_to' AND replaced_by IS NULL").fetchone()[0], 3)
        tmp.cleanup()

    def test_org_nesting_loop_refused(self):
        tmp, c = build(True)
        t = things(c)
        sg.add_link(c, t["org"], "part_of", t["org2"], "owner", "sure", "answer", answer_id=t["ans"])
        with self.assertRaisesRegex(sg.Refused, "loop"):
            sg.add_link(c, t["org2"], "part_of", t["org"], "owner", "sure", "answer", answer_id=t["ans"])
        tmp.cleanup()

    def test_owner_placement_accepted_and_code_invite_accepted_and_empty_structure_valid(self):
        tmp, c = build(True)
        t = things(c)
        sg.add_link(c, t["me"], "member_of", t["org"], "owner", "sure", "answer", answer_id=t["ans"], role="owner")
        sg.add_link(c, t["org"], "part_of", t["org2"], "owner", "sure", "answer", answer_id=t["ans"])
        sg.add_link(c, t["me"], "reports_to", t["boss"], "owner", "sure", "answer", answer_id=t["ans"])
        sg.add_link(c, t["me"], "knows", t["big"], "owner", "sure", "answer", answer_id=t["ans"], role="old friend")
        sg.add_link(c, t["proj"], "part_of", t["org"], "owner", "sure", "answer", answer_id=t["ans"])
        sg.add_link(c, t["proj"], "involves", t["boss"], "owner", "sure", "answer", answer_id=t["ans"])
        sg.add_link(c, t["ev"], "involves", t["me"], "code", "sure", "code", "calendar:1")      # the invite list: code-sure
        self.assertEqual(c.execute("SELECT count(*) FROM kg_links WHERE replaced_by IS NULL").fetchone()[0], 7)
        # a second current line for the same pair is refused by the unique index (019)
        with self.assertRaises(sqlite3.IntegrityError):
            raw(c, t["me"], "member_of", t["org"], "owner", t["ans"])
        tmp.cleanup()
        tmp, c = build(True)
        self.assertEqual(c.execute("SELECT count(*) FROM kg_links WHERE kind IN ('member_of','reports_to','part_of','knows')").fetchone()[0], 0)
        tmp.cleanup()


if __name__ == "__main__":
    unittest.main()

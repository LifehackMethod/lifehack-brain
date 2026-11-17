"""Phase 4P.4 + 4P.4b (engine part): `gc decide` -- the door for a session's decisions on a draft, the
validated weekly picture it stages, and the morning read / midnight job reading it.

Planted bad cases, each shown failing on the unfixed code first (see phase-4P-step-4-result.md):
  an answer without his words is refused; a suggestion he did not say yes to is not written; a placement
  (org membership, levels) written by anyone but the owner is refused; a snapshot edited after validation
  fails check_snapshot and is not re-staged; a snapshot with a yes whose answer is not in the database is
  refused; a forced morning read after a staged validated picture labels its baseline "validated", and one
  after a draft only still says DRAFT; the midnight job's find_staged picks up the validated file and the
  day's entry points at it; the planning desk folder is found through shared/desk_list.py, never a literal
  name.

Temp DBs and temp notes folders only; never the live rig.db or the real notes folder.
"""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: nothing outside tmp
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import contextlib, importlib.util, io, json, os, sqlite3, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # shared/grand_central
SHARED = os.path.dirname(ROOT)  # shared/ (desk_list.py lives there)
sys.path.insert(0, ROOT)
sys.path.insert(0, SHARED)
import migrate, store, store_graph as sg  # noqa: E402
import morning  # noqa: E402

spec = importlib.util.spec_from_file_location("rig_gc_4p4", os.path.join(ROOT, "gc.py"))
rig_gc = importlib.util.module_from_spec(spec); spec.loader.exec_module(rig_gc)

DAY = "2026-11-17"
DESK = "desk-a"  # the fixture setup's default_desk

REGISTRY = ("schema_version: 2\n"
            "desks:\n"
            "  - desk_id: desk-a\n"
            "    purpose_path: desks/desk-a/canon/purpose.md\n"
            "    open_loops_path: desks/desk-a/state/open-loops.md\n"
            "  - desk_id: other\n"
            "    purpose_path: desks/other/canon/purpose.md\n"
            "    open_loops_path: desks/other/state/open-loops.md\n")


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = os.path.join(self.tmp.name, "rig.db")
        c = sqlite3.connect(self.p, isolation_level=None)
        for n, path in migrate.list_migrations():
            migrate.apply_file(c, path, n)
        c.close()
        store.set_path(self.p)
        self.notes = os.path.join(self.tmp.name, "notes")
        self.records = os.path.join(self.notes, "desks", DESK, "records", "context")
        self._old_env = {k: os.environ.get(k) for k in ("AGE_NOW", "AGE_NOTES_ROOT", "LIFEHACK_DESK_LIST")}
        os.environ["AGE_NOW"] = DAY + "T09:00:00+00:00"
        os.environ["AGE_NOTES_ROOT"] = self.notes
        reg = os.path.join(self.tmp.name, "desk-registry.yaml")
        with open(reg, "w", encoding="utf-8") as f:
            f.write(REGISTRY)
        os.environ["LIFEHACK_DESK_LIST"] = reg
        self.reg = reg
        self.seed()

    def tearDown(self):
        store.set_path(None)
        for k, v in self._old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self.tmp.cleanup()

    def x(self, sql, a=()):
        c = sqlite3.connect(self.p)
        try:
            r = c.execute(sql, a).fetchall(); c.commit(); return r
        finally:
            c.close()

    def seed(self):
        self.person = self.model(lambda c: sg.thing(c, "person", "Person One", created_by="code"))

    def model(self, fn, *a, **k):
        c = sqlite3.connect(self.p, isolation_level=None)
        try:
            c.execute("BEGIN"); r = fn(c, *a, **k); c.execute("COMMIT"); return r
        finally:
            c.close()

    def gc(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = rig_gc.main(["--db", self.p] + list(argv))
        return rc, out.getvalue(), err.getvalue()

    def draft(self, did="week-1"):
        return {"draft_id": did, "made_on": "2026-11-16", "suggestions": [
            {"id": "s1", "kind": "fact", "question": "Is Person One high importance?",
             "subject_kind": "person", "subject_name": "Person One", "fact_key": "importance", "value": "high",
             "basis": "he said it in the session"},
            {"id": "s2", "kind": "fact", "question": "Keep the note about Person One?",
             "subject_kind": "person", "subject_name": "Person One", "fact_key": "note", "value": "met at the workshop",
             "basis": "session"},
        ]}

    def decisions(self, **by_id):
        return {sid: {"decision": d, "words": w} for sid, (d, w) in by_id.items()}

    def stage(self, day=DAY, did="week-1", **by_id):
        d = self.draft(did)
        dp = os.path.join(self.tmp.name, "draft.json"); dp2 = os.path.join(self.tmp.name, "decisions.json")
        with open(dp, "w", encoding="utf-8") as f:
            json.dump(d, f)
        with open(dp2, "w", encoding="utf-8") as f:
            json.dump(self.decisions(**by_id), f)
        rc, out, err = self.gc("decide", "--draft", dp, "--decisions", dp2, "--day", day, "--json")
        return rc, out, err

    def answers_for(self, tag):
        return self.x("SELECT id FROM kg_answers WHERE asked_by=?", (tag,))


class DecideDoor(Base):
    def test_yes_without_his_words_is_refused(self):
        rc, out, err = self.stage(s1=("yes", "   "), s2=("yes", "yes it is"))
        self.assertEqual(rc, 1, err)
        self.assertIn("words", err + out)
        self.assertEqual(self.answers_for("draft:week-1#s1"), [])  # nothing written
        self.assertFalse(os.path.exists(os.path.join(self.records, "%s-%s-validated.json" % (DAY, DESK))))

    def test_no_is_never_written(self):
        rc, out, err = self.stage(s1=("no", ""), s2=("yes", "keep it"))
        self.assertEqual(rc, 0, err)
        self.assertEqual(self.answers_for("draft:week-1#s1"), [])  # his no lives only in the snapshot
        self.assertEqual(len(self.answers_for("draft:week-1#s2")), 1)
        doc = json.load(open(os.path.join(self.records, "%s-%s-validated.json" % (DAY, DESK)), encoding="utf-8"))
        by = {r["id"]: r["decision"] for r in doc["snapshot"]["decisions"]}
        self.assertEqual(by, {"s1": "no", "s2": "yes"})
        self.assertEqual(doc["check"]["errors"], [])

    def test_unknown_suggestion_refused(self):
        rc, out, err = self.stage(s1=("yes", "yes"), sX=("yes", "yes"))
        self.assertEqual(rc, 1, err)
        self.assertIn("no such suggestion", err + out)

    def test_placement_by_anyone_but_owner_is_refused(self):
        # levels_above_me and a placement link (member_of -> organization) are HIS word: any other writer is refused.
        org = self.model(lambda c: sg.thing(c, "organization", "Org One", created_by="code"))
        with self.assertRaises(sg.Refused):
            self.model(sg.assert_fact, self.person, "levels_above_me", "2", "code", "likely", "code")
        with self.assertRaises(sg.Refused):
            self.model(sg.add_link, self.person, "member_of", org, "code", "likely", "code")
        # the door itself records a placement ONLY as his answer (who=owner, answer-backed):
        d = {"draft_id": "week-lvl", "made_on": "2026-11-16", "suggestions": [
            {"id": "lvl", "kind": "fact", "question": "How many levels above you is Person One?",
             "subject_kind": "person", "subject_name": "Person One", "fact_key": "levels_above_me", "value": "2"}]}
        snap = store.record_decisions(d, {"lvl": {"decision": "yes", "words": "two above me"}})
        errs = store.check_snapshot(d, snap)
        self.assertEqual(errs, [])
        row = self.x("SELECT who, answer_id FROM kg_facts WHERE fact_key='levels_above_me' AND replaced_by IS NULL")
        self.assertEqual([(w, bool(a)) for w, a in row], [("owner", True)])

    def test_edited_snapshot_fails_check_and_is_not_restaged(self):
        rc, out, err = self.stage(s1=("yes", "yes it is"), s2=("no", ""))
        self.assertEqual(rc, 0, err)
        path = os.path.join(self.records, "%s-%s-validated.json" % (DAY, DESK))
        doc = json.load(open(path, encoding="utf-8"))
        snap = json.loads(json.dumps(doc["snapshot"]))
        snap["decisions"][1]["decision"] = "yes"  # someone edits his no (s2) into a yes
        errs = store.check_snapshot(self.draft(), snap)
        self.assertTrue(errs, "an edited snapshot must fail check_snapshot")
        # the staged file is never rewritten by decide: staging again for the same day is refused
        before = len(self.x("SELECT id FROM kg_answers"))
        rc2, out2, err2 = self.stage(s1=("yes", "a different yes"), s2=("yes", "keep"))
        self.assertEqual(rc2, 1, err2)
        self.assertIn("already staged", err2 + out2)
        # PLANTED (verification 2026-11-17, blocker): a refused call writes NOTHING to the database
        self.assertEqual(len(self.x("SELECT id FROM kg_answers")), before)

    def test_yes_whose_answer_left_the_database_is_refused(self):
        rc, out, err = self.stage(s1=("yes", "yes it is"), s2=("no", ""))
        self.assertEqual(rc, 0, err)
        # kg_answers is append-only (the database refuses the delete): the plant is a staged receipt whose
        # snapshot points at answers that are not in the database.
        (aid,) = self.answers_for("draft:week-1#s1")[0]
        self.x("DELETE FROM kg_facts WHERE answer_id=?", (aid,))
        with open(os.path.join(self.records, "%s-%s-validated.json" % (DAY, DESK)), encoding="utf-8") as f:
            doc = json.load(f)
        snap = json.loads(json.dumps(doc["snapshot"]))
        for r in snap["decisions"]:
            if r["decision"] == "yes":
                r["answer_ids"] = [999999]  # claims a yes whose answers are not in the database
        errs = store.check_snapshot(self.draft(), snap)
        self.assertTrue(any("not in the database" in e for e in errs), errs)

    def test_show_is_the_receipt(self):
        rc, out, err = self.stage(s1=("yes", "yes it is"), s2=("yes", "keep it"))
        self.assertEqual(rc, 0, err)
        rc2, out2, err2 = self.gc("decide", "--show", "--day", DAY, "--json")
        self.assertEqual(rc2, 0, err2)
        body = json.loads(out2)
        self.assertTrue(body["valid"])
        self.assertEqual(body["check"]["errors"], [])
        self.assertEqual(body["snapshot"]["status"], "validated")
        self.assertEqual(body["desk"], DESK)
        self.assertTrue(body["file"].endswith("%s-%s-validated.json" % (DAY, DESK)))

    def test_desk_folder_comes_from_the_desk_list(self):
        import decide
        rdir, dsk, err = decide.planning_records_dir()
        self.assertIsNone(err)
        self.assertEqual((rdir, dsk), (self.records, DESK))
        # a list without the planning desk is an error, never a guessed folder
        reg2 = os.path.join(self.tmp.name, "reg2.yaml")
        with open(reg2, "w", encoding="utf-8") as f:
            f.write("schema_version: 2\ndesks:\n- desk_id: other\n  purpose_path: desks/other/canon/purpose.md\n")
        rdir2, dsk2, err2 = decide.planning_records_dir(env={"LIFEHACK_DESK_LIST": reg2})
        self.assertIsNone(rdir2)
        self.assertTrue(err2)


class MorningReadsValidated(Base):
    def _write(self, path, text):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    def draft_writeup(self, day=DAY, when=None):
        p = os.path.join(self.records, "%s-%s.md" % (day, DESK))
        self._write(p, "# Morning write-up %s - %s desk\n\nStarting point: none.\n\n## Picture\n"
                       "- A carried guess from the morning read\n- Another line\n\n## Questions\n- none\n" % (day, DESK))
        if when:
            os.utime(p, (when, when))
        return p

    def test_validated_wins_over_a_later_draft(self):
        rc, out, err = self.stage(s1=("yes", "yes it is"), s2=("no", ""))
        self.assertEqual(rc, 0, err)
        self.draft_writeup(when=os.path.getmtime(
            os.path.join(self.records, "%s-%s-validated.md" % (DAY, DESK))) + 1000)
        base, latest = morning.previous_picture(self.records, DESK)
        self.assertEqual(latest, os.path.basename(
            os.path.join(self.records, "%s-%s-validated.md" % (DAY, DESK))))
        bl = morning.parse_baseline(base)
        self.assertEqual(bl.kind, "validated")
        self.assertIn("validated", bl.label)
        self.assertTrue(all(not ln["carried"] for ln in bl.lines))
        self.assertTrue(any("high" in ln["text"] for ln in bl.lines))  # his yes is the baseline content
        # control: a desk with nothing staged has no picture at all
        self.assertIsNone(morning.previous_picture(self.records, "desk-b")[0])

    def test_draft_only_still_says_draft(self):
        self.draft_writeup()
        base, latest = morning.previous_picture(self.records, DESK)
        self.assertEqual(latest, "%s-%s.md" % (DAY, DESK))
        bl = morning.parse_baseline(base)
        self.assertEqual(bl.kind, "draft")
        self.assertIn("NOT validated", base)
        self.assertTrue(all(ln["carried"] for ln in bl.lines))

    def test_find_staged_and_midnight_point_at_the_validated_picture(self):
        rc, out, err = self.stage(s1=("yes", "yes it is"), s2=("no", ""))
        self.assertEqual(rc, 0, err)
        self.draft_writeup()
        staged = morning.find_staged(self.records, DAY, DESK)
        names = [os.path.basename(p) for p in staged]
        self.assertIn("%s-%s-validated.md" % (DAY, DESK), names)
        self.assertIn("%s-%s.md" % (DAY, DESK), names)
        res = morning.midnight_entry(DAY, DESK, staged, os.path.join(self.notes, "diary"))
        self.assertEqual(res["status"], "written")
        self.assertTrue(any(p.endswith("%s-%s-validated.md" % (DAY, DESK)) for p in res["pointers"]), res["pointers"])


if __name__ == "__main__":
    unittest.main()

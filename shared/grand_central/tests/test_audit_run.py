"""The audit's Part 1 (tests/audit_run.py): every input the morning read had for a day is listed, and each one is either FOUND in
the draft (section + line) or carries a CODE-STATED reason for absence; an input with neither is a DEFECT.
A fake run folder (scratch only, no live path): two emails marked for the day, one listed in the draft and one deliberately absent
with no reason -> DEFECTS: 1. The check is shown failing on a broken copy first (a locate() that finds everything)."""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import json, os, shutil, sqlite3, sys, tempfile, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import audit_run  # noqa: E402
import migrate, store  # noqa: E402

DAY = "2026-11-21"
TA, TB, TJ = "a1a1a1a1a1a1a1a1", "b2b2b2b2b2b2b2b2", "c3c3c3c3c3c3c3c3"


def row(mid, thread, sender, subject, needs="no", area="home", verdict="safe"):
    return {"message_id": mid, "thread_id": thread, "from": sender, "subject": subject, "date": "2026-11-20", "label": "inbox",
            "verdict": verdict, "seen": "full", "internal_ms": 1763600000000, "mac": "x", "file": "transcripts/%s.txt" % thread,
            "triage": {"needs_me": needs, "do_or_know": "know", "how_soon": "none", "deadline": None, "area": area,
                       "obs": {"deadline_stated": "no", "money_involved": "no", "direct_ask": "no", "reply_expected": "no"}}}


DRAFT = """# Morning write-up 2026-11-21 - desk-a desk (2026-11-21-desk-a)

DRAFT, low confidence.

New held or quarantined since the last draft: none.

## Needs him
- 2026-11-20 | Alice Example <alice@example.test> | Venue contract | message a1a1a1a1a1a1 | triage: needs him (do, now)

## Capacity
- 2026-11-21: 12.00 free hours

## Unclassified emails
- none

## What code read and counted
Starting point: previous draft of 2026-11-20 (unconfirmed).
Read kind: full morning read: calendar (1 items), tasks (1 shown of 1 open), Life Map (used) and 2 new emails.
- Your next 14 days: 2026-11-22: Dentist visit
- Open task: (due 2026-11-23) Send the proposal

## The morning draft
(Written by the AI: suggestions, never facts.)
Alice wants the venue contract: "sign by Friday" [mail:a1a1a1a1a1a1a1a1].
"""


class Part1(unittest.TestCase):
    def setUp(self):
        self.run = tempfile.mkdtemp(prefix="auditrun-")
        self.addCleanup(shutil.rmtree, self.run, True)
        self.prev_path = store._path
        self.addCleanup(store.set_path, self.prev_path)
        cat = os.path.join(self.run, "front-room", "catalogue")
        os.makedirs(cat)
        rows = [row("a1a1a1a1a1a1a1a1", TA, "Alice Example <alice@example.test>", "Venue contract", needs="yes"),
                row("b2b2b2b2b2b2b2b2", TB, "Bob Missing <bob@elsewhere.test>", "Quarterly widget invoice"),
                row("c3c3c3c3c3c3c3c3", TJ, "Notices <n@junk.test>", "Your weekly stats", area="other")]
        with open(os.path.join(cat, "catalogue.jsonl"), "w", encoding="utf-8") as f:
            f.write("".join(json.dumps(r) + "\n" for r in rows))
        with open(os.path.join(cat, "used-in-draft.jsonl"), "w", encoding="utf-8") as f:
            f.write("".join(json.dumps({"day": DAY, "message_id": r["message_id"], "stem": "2026-11-21-desk-a"}) + "\n" for r in rows[:2]))
            f.write(json.dumps({"day": "2026-11-20", "message_id": rows[2]["message_id"], "stem": "2026-11-20-desk-a"}) + "\n")
        os.makedirs(os.path.join(self.run, "front-room", "transcripts"))
        for t in (TA, TB, TJ):
            open(os.path.join(self.run, "front-room", "transcripts", t + ".txt"), "w", encoding="utf-8").write("=== message x ===\nbody\n")
        os.makedirs(os.path.join(self.run, "drop", "facts"))
        notes = os.path.join(self.run, "notes", "desks", "desk-a")
        os.makedirs(os.path.join(notes, "records", "context"))
        os.makedirs(os.path.join(notes, "diary", "2026", "11"))
        open(os.path.join(notes, "life-map.md"), "w", encoding="utf-8").write("## Weekly Win\nShip.\n")
        open(os.path.join(notes, "records", "context", "2026-11-20-desk-a.md"), "w", encoding="utf-8").write("# earlier draft\n")
        open(os.path.join(notes, "diary", "2026", "11", "15.md"), "w", encoding="utf-8").write("his line one\n\nhis line two\n")
        db = os.path.join(self.run, "rig.db")
        fresh = migrate.fresh_build(10 ** 6)
        dst = sqlite3.connect(db)
        fresh.backup(dst)
        dst.execute("INSERT INTO calendar_events(id,start,end,summary,status) VALUES('e1','2026-11-22T10:00:00Z','2026-11-22T11:00:00Z','Dentist visit','confirmed')")
        dst.execute("INSERT INTO tasks(id,list_id,title,status,due,updated) VALUES('t1','l','Send the proposal','needsAction','2026-11-23','2026-11-10T00:00:00Z')")
        dst.execute("INSERT INTO kg_answers(question,words,asked_by,said_on,recorded_at) VALUES('q','his own words','w','2026-11-19','2026-11-19T00:00:00Z')")
        dst.commit()
        dst.close()
        self.out = os.path.join(self.run, "audit")

    def go(self, draft=DRAFT):
        items, ctx = audit_run.audit(self.run, DAY, draft)
        return items, audit_run.write_part1(items, ctx, DAY, "draft.md", self.out)

    def test_one_listed_one_absent_with_no_reason_is_one_defect_shown_on_a_broken_copy_first(self):
        orig = audit_run.locate
        audit_run.locate = lambda draft, needles, section=None: [(1, "(top)")]       # the broken copy: finds everything
        try:
            _items, (_p, n) = self.go()
            self.assertNotEqual(n, 1)                                               # caught: it reports 0 defects, the planted one is missed
            self.assertEqual(n, 0)
        finally:
            audit_run.locate = orig
        items, (path, n) = self.go()
        self.assertEqual(n, 1)
        text = open(path, encoding="utf-8").read()
        self.assertIn("DEFECTS: 1", text)
        self.assertIn("Quarterly widget invoice", text.split("DEFECTS: 1")[1])          # the absent email is the one named
        found = [i for i in items if i.category == "email (handed)" and i.hits]
        self.assertEqual(len(found), 1)

    def test_an_email_mentioned_without_its_tag_is_a_defect_with_it_found(self):
        untagged = DRAFT.replace("## The morning draft", "## The morning draft\nBob Missing wrote about the Quarterly widget invoice.")
        items, (_p, n) = self.go(untagged)
        self.assertEqual(n, 1)                                                  # sender and subject alone no longer count (F5)
        tagged = DRAFT.replace("## The morning draft", "## The morning draft\nBob Missing wrote about the invoice [mail:%s]." % TB)
        items, (_p, n) = self.go(tagged)
        self.assertEqual(n, 0)
        found = [i for i in items if i.category == "email (handed)" and "Quarterly" in i.label][0]
        self.assertEqual(found.hits[0][1], "## The morning draft")

    def test_where_it_appears_is_a_section_heading_and_a_line_number(self):
        items, (path, n) = self.go()
        text = open(path, encoding="utf-8").read()
        self.assertRegex(text, r"Venue contract[^\n]*\| ## Needs him, line \d+")
        events = [i for i in items if i.category.startswith("calendar")][0]
        self.assertEqual(events.hits[0][1], "## What code read and counted")
        self.assertTrue([i for i in items if i.category == "task (open)" and i.hits])

    def test_triage_junk_absent_from_the_draft_is_reasoned_not_a_defect(self):
        # the junk mail is marked for ANOTHER day here, so mark it for this day too
        with open(os.path.join(self.run, "front-room", "catalogue", "used-in-draft.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps({"day": DAY, "message_id": "c3c3c3c3c3c3c3c3", "stem": "2026-11-21-desk-a"}) + "\n")
        items, (path, n) = self.go()
        junk = [i for i in items if i.category == "email (not handed)"][0]
        self.assertIn("triage junk", junk.reason)
        self.assertFalse(junk.defect)
        self.assertEqual(n, 1)                                                          # still only the absent invoice

    def test_a_task_past_the_cap_and_an_excluded_label_item_carry_stated_reasons(self):
        db = sqlite3.connect(os.path.join(self.run, "rig.db"))
        for i in range(70):
            db.execute("INSERT INTO tasks(id,list_id,title,status,due,updated) VALUES(?,?,?,?,?,?)", ("x%d" % i, "l", "Filler chore %d" % i, "needsAction", None, "2026-11-01T00:00:00Z"))
        db.commit(); db.close()
        facts = {"quarantined": 0, "held_after": 1, "delivered": 0, "written_at": "t", "held_messages_total": 1,
                 "held_messages": [{"message_id": "dddd44440004", "thread_id": "4444dddd", "status": "held", "reason": "excluded_label"}]}
        with open(os.path.join(self.run, "drop", "facts", "_reader_pass.json"), "w", encoding="utf-8") as f:
            json.dump(facts, f)
        import morning
        store.set_path(os.path.join(self.run, "rig.db"))
        with store._read() as con:
            kept = morning.select_tasks(audit_run.task_rows(con), DAY)[0]
        draft = DRAFT.replace("New held or quarantined since the last draft: none.", "New held or quarantined since the last draft: none.\nIn labels you chose not to open: 1")
        draft = draft.replace("## The morning draft", "".join("- Open task: %s\n" % k["title"] for k in kept) + "\n## The morning draft")   # the code's list shows the kept ones
        items, (path, n) = self.go(draft)
        past = [i for i in items if i.category == "task (open)" and i.reason]
        self.assertTrue(past and "task cap" in past[0].reason)
        held = [i for i in items if i.category == "held/quarantined"]
        self.assertEqual(len(held), 1)
        self.assertIn("excluded label", held[0].reason)
        self.assertEqual(n, 1)

    def test_the_reader_inputs_are_plain_text_files_and_no_body_text_is_copied(self):
        rc = audit_run.main(["--run", self.run, "--day", DAY, "--draft", self._draft_file(), "--out", self.out])
        self.assertEqual(rc, 0)
        for n in ("calendar", "tasks", "handed", "questions", "answers", "diary-lines"):
            self.assertTrue(os.path.isfile(os.path.join(self.out, "inputs", n + ".txt")), n)
        handed = open(os.path.join(self.out, "inputs", "handed.txt"), encoding="utf-8").read()
        self.assertIn(os.path.join(self.run, "front-room", "transcripts", TA + ".txt"), handed)
        self.assertNotIn("body", handed)                                                # the transcript text itself is never copied
        self.assertIn("Dentist visit", open(os.path.join(self.out, "inputs", "calendar.txt"), encoding="utf-8").read())
        self.assertIn("Send the proposal | 2026-11-23", open(os.path.join(self.out, "inputs", "tasks.txt"), encoding="utf-8").read())
        self.assertIn("his own words", open(os.path.join(self.out, "inputs", "answers.txt"), encoding="utf-8").read())
        dl = open(os.path.join(self.out, "inputs", "diary-lines.txt"), encoding="utf-8").read()
        self.assertIn("notes/desks/desk-a/diary/2026/11/15.md:1: his line one", dl)
        self.assertIn("15.md:3: his line two", dl)
        self.assertIn("DEFECTS: 1", open(os.path.join(self.out, "part1-nothing-dropped.md"), encoding="utf-8").read())

    def _draft_file(self):
        p = os.path.join(self.run, "draft.md")
        open(p, "w", encoding="utf-8").write(DRAFT)
        return p


if __name__ == "__main__":
    unittest.main()

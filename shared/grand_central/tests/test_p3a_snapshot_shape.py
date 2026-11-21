#!/usr/bin/env python3
"""4P.3 slice A (items 5, 3, 4): the morning snapshot's fixed shape.

Item 5 - a fixed layout (4P.3R: code's lists first, the AI's part last): the four load-bearing sections appear in ONE
order, as level-2 headings exactly "## Needs him", "## Capacity", "## Unclassified emails", "## The morning draft" (the
AI's part, always the last heading); other sections never sit between the first three. snapshot_layout.check_layout()
reports problems.
Item 3 - Capacity, pure code (capacity.py): free hours (08:00-20:00), collisions, back-to-backs,
travel days (the coordinator-approved RULE OF THUMB), bad rows named, never a crash or negative hours.
Item 4 - the unclassified-emails list: rows triage could not place (cant_tell, or no triage at all),
rendered sender | date | subject | best guess through _safe_line. Quarantined or refused mail
never appears here.

Planted-bad-case proof: the PRE-change renderer is loaded from git HEAD into a scratch module
(_pre_slA_morning, deleted after the run); the planted cases are shown failing against it, then
passing against the built code. For capacity.py (a new module) each planted case is shown failing
against a naive stub written here (the plausible wrong first version), then passing against the real one.

Run: python3 -I -B tests/test_p3a_snapshot_shape.py   (from shared/grand_central/)
"""
import atexit as _ax, os as _o, shutil as _sh, subprocess as _sp, tempfile as _t, unittest
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.environ.get("GC_STATE_ROOT") or _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import importlib.util
import json
import sys

ROOT = _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
import capacity # noqa: E402
import snapshot_layout # noqa: E402
import morning # noqa: E402
import transcripts # noqa: E402

DAY = "2026-11-20"
PRE_NAME = "_pre_slA_morning.py"

# ---------------------------------------------------------------- the PRE-change renderer, from d35066d (the commit before slice A)
pre_src = _sp.run(["git", "-C", ROOT, "show", "d35066d:shared/grand_central/morning.py"], check=True, capture_output=True).stdout.decode("utf-8")
pre_path = _o.path.join(ROOT, PRE_NAME)
with open(pre_path, "w", encoding="utf-8") as f:
    f.write(pre_src)
_ax.register(lambda: _o.path.exists(pre_path) and _o.remove(pre_path))
_spec = importlib.util.spec_from_file_location("pre_slA_morning", pre_path)
pre = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pre)


def _baseline(mod):
    return mod.parse_baseline(None)


# ---------------------------------------------------------------- item 5: the fixed layout
class Layout(unittest.TestCase):
    def _post(self, **kw):
        x = {"cal_items": [], "task_items": [], "read_info": {}}
        x.update(kw)
        return morning.render_record(DAY, "planning", DAY + "-planning", "no earlier picture", "A plain sentence.", None, x)

    def test_real_snapshot_has_the_fixed_layout(self):
        rec = self._post()
        self.assertEqual(snapshot_layout.check_layout(rec), [])
        for s in snapshot_layout.SECTIONS:
            self.assertIn(s, rec)

    def test_planted_a_capacity_missing_fails(self):
        """planted (a): a snapshot with the Capacity section missing fails the layout checker."""
        rec = "# write-up\n\n## Needs him\n- x\n\n## Unclassified emails\n- none\n\n## The morning draft\nwords\n"
        problems = snapshot_layout.check_layout(rec)
        self.assertTrue(any("missing section: ## Capacity" in p for p in problems), problems)

    def test_planted_b_wrong_name_fails(self):
        """planted (b): a section renamed ("Capacity:" instead of "## Capacity") fails."""
        rec = "# w\n\n## Needs him\n- x\n\n## Capacity:\n- y\n\n## Unclassified emails\n- none\n\n## The morning draft\nwords\n"
        problems = snapshot_layout.check_layout(rec)
        self.assertTrue(any("missing section: ## Capacity" in p for p in problems), problems)

    def test_planted_c_wrong_order_fails(self):
        """planted (c): Capacity before Needs him fails the fixed order."""
        rec = "# w\n\n## Capacity\n- n\n\n## Needs him\n- x\n\n## Unclassified emails\n- none\n\n## The morning draft\nwords\n"
        problems = snapshot_layout.check_layout(rec)
        self.assertTrue(any("out of order" in p for p in problems), problems)

    def test_planted_section_between_the_first_three_fails(self):
        rec = ("# w\n\n## Needs him\n- x\n\n## Open tasks that matter\n- t\n\n## Capacity\n- n\n"
               "\n## Unclassified emails\n- none\n\n## The morning draft\nwords\n")
        problems = snapshot_layout.check_layout(rec)
        self.assertTrue(any("between" in p for p in problems), problems)

    def test_planted_the_ai_part_must_be_last(self):
        rec = ("# w\n\n## Needs him\n- x\n\n## Capacity\n- n\n\n## Unclassified emails\n- none\n\n## The morning draft\nwords\n\n## Something after\n- y\n")
        problems = snapshot_layout.check_layout(rec)
        self.assertTrue(any("not the last section" in p for p in problems), problems)

    def test_fail_before_pre_change_renderer_has_no_fixed_layout(self):
        """fail-then-pass: the PRE-change renderer's snapshot fails the checker; the new one passes."""
        old = pre.render_record(DAY, "planning", DAY + "-planning", _baseline(pre), None, {"all": []}, {}, x={})
        self.assertNotIn("## Capacity", old)              # the old snapshot has no Capacity section at all
        self.assertNotIn("## Needs him", old)             # and has no Needs-him list
        self.assertNotIn("## Unclassified emails", old)
        self.assertTrue(snapshot_layout.check_layout(old))                 # FAILS before
        self.assertEqual(snapshot_layout.check_layout(self._post()), [])   # PASSES after


# ---------------------------------------------------------------- item 3: capacity, pure code
def ev(title, start, end=None, location=None):
    d = {"title": title, "start": start}
    if end is not None:
        d["end"] = end
    if location is not None:
        d["location"] = location
    return d


def naive(rows, day, collisions=0):
    """The plausible wrong first version: no collision counting, bad rows crash or go negative."""
    out = []
    for i in range(7):
        out.append({"date": "naive-%d" % i, "free_hours": 12.0, "busy_hours": 0.0,
                    "collisions": collisions, "back_to_backs": 0, "travel": False, "unusable": []})
    return out


class CapacityMath(unittest.TestCase):
    def test_empty_day_is_12_free_hours(self):
        out = capacity.capacity([], DAY)
        self.assertEqual(len(out), 7)
        self.assertEqual(out[0]["free_hours"], 12.0)
        self.assertEqual(out[0]["busy_hours"], 0.0)
        self.assertFalse(out[0]["travel"])

    def test_planted_a_overlapping_events_count_collisions(self):
        """planted (a): two overlapping events on one day -> collisions >= 1 (a first version that counts 0 fails)."""
        rows = [ev("Deep work", DAY + " 09:00", DAY + " 12:00"), ev("Interview", DAY + " 11:00", DAY + " 12:30")]
        real = capacity.capacity(rows, DAY)
        self.assertEqual(real[0]["collisions"], 1)
        self.assertEqual(naive(rows, DAY)[0]["collisions"], 0)  # the naive version misses it: FAILS before

    def test_planted_b_bad_end_named_unusable_never_crash_or_negative(self):
        """planted (b): an event with end empty, or end before start, is named unusable; no crash, no negative hours."""
        for rows in ([ev("Broken", DAY + " 09:00", "")], [ev("Backwards", DAY + " 14:00", DAY + " 10:00")]):
            real = capacity.capacity(rows, DAY)
            self.assertEqual(real[0]["unusable"], [rows[0]["title"]])
            self.assertEqual(real[0]["busy_hours"], 0.0)
            self.assertEqual(real[0]["free_hours"], 12.0)

    def test_planted_c_all_day_and_zero_length_add_zero_busy(self):
        """planted (c): all-day and zero-length events add 0 busy hours, never 24."""
        for rows in ([ev("Off", DAY)], [ev("Checkpoint", DAY + " 09:00", DAY + " 09:00")]):
            real = capacity.capacity(rows, DAY)
            self.assertEqual(real[0]["busy_hours"], 0.0)
            self.assertEqual(real[0]["free_hours"], 12.0)

    def test_all_day_marks_travel(self):
        real = capacity.capacity([ev("Trip", DAY)], DAY)
        self.assertTrue(real[0]["travel"])

    def test_travel_word_in_title_or_location_marks_the_day(self):
        for rows in ([ev("Flight to the coast", DAY + " 09:00", DAY + " 10:00")],
                     [ev("Errand", DAY + " 09:00", DAY + " 10:00", location="airport terminal 2")],
                     [ev("Ride", DAY + " 09:00", DAY + " 10:00", location="train platform 4")],
                     [ev("Stay", DAY + " 09:00", DAY + " 10:00", location="hotel lobby")]):
            self.assertTrue(capacity.capacity(rows, DAY)[0]["travel"], rows)

    def test_no_travel_word_no_travel(self):
        self.assertFalse(capacity.capacity([ev("Standup", DAY + " 09:00", DAY + " 09:30")], DAY)[0]["travel"])

    def test_back_to_back_within_ten_minutes(self):
        rows = [ev("A", DAY + " 09:00", DAY + " 10:00"), ev("B", DAY + " 10:08", DAY + " 11:00")]
        self.assertEqual(capacity.capacity(rows, DAY)[0]["back_to_backs"], 1)
        rows = [ev("A", DAY + " 09:00", DAY + " 10:00"), ev("B", DAY + " 10:30", DAY + " 11:00")]
        self.assertEqual(capacity.capacity(rows, DAY)[0]["back_to_backs"], 0)

    def test_free_hours_merged_not_double_counted(self):
        rows = [ev("Deep work", DAY + " 09:00", DAY + " 12:00"), ev("Interview", DAY + " 11:00", DAY + " 12:30")]
        real = capacity.capacity(rows, DAY)
        self.assertEqual(real[0]["busy_hours"], 3.5)
        self.assertEqual(real[0]["free_hours"], 8.5)

    def test_only_the_next_seven_days(self):
        rows = [ev("Far away", "2026-12-24 09:00", "2026-12-24 10:00")]
        out = capacity.capacity(rows, DAY)
        self.assertTrue(all(d["busy_hours"] == 0.0 for d in out))


# ---------------------------------------------------------------- item 4: the unclassified-emails list
class Unclassified(unittest.TestCase):
    def _row(self, **kw):
        r = {"message_id": "a000001", "thread_id": "b000001", "from": "studio@example.com", "date": "2026-11-19",
             "subject": "Re: the reels", "verdict": "safe", "seen": "full"}
        r.update(kw)
        return r

    def test_cant_tell_row_is_listed(self):
        rows = [self._row(triage={"needs_me": "cant_tell", "area": "work"})]
        out = snapshot_layout.unclassified_rows(rows)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["guess"], "work")

    def test_planted_a_no_triage_at_all_is_listed(self):
        """planted (a): an email with no triage dict at all appears in the list (a version that silently drops it fails)."""
        rows = [self._row(triage=None)]
        out = snapshot_layout.unclassified_rows(rows)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["guess"], "none")

    def test_placed_rows_are_not_listed(self):
        rows = [self._row(triage={"needs_me": "no", "area": "other"}),
                self._row(triage={"needs_me": "yes", "area": "work"})]
        self.assertEqual(snapshot_layout.unclassified_rows(rows), [])

    def test_planted_b_quarantined_never_appears(self):
        """planted (b): a quarantined or refused email does NOT appear in the unclassified list."""
        rows = [self._row(verdict="quarantine", triage=None)]
        self.assertEqual(snapshot_layout.unclassified_rows(rows), [])

    def test_record_renders_the_list_with_links_removed(self):
        rows = [self._row(subject="see https://evil.example.com/now or www.junk.io", triage=None)]
        x = {"cal_items": [], "task_items": [], "read_info": {},
             "capacity": [], "unclassified": snapshot_layout.unclassified_rows(rows)}
        rec = morning.render_record(DAY, "planning", DAY + "-planning", "no earlier picture", "A plain sentence.", None, x)
        part = rec.split("## Unclassified emails")[1]
        self.assertIn("studio@example.com", part)
        self.assertNotIn("evil.example.com", part)
        self.assertIn("[link removed]", part)
        self.assertEqual(snapshot_layout.check_layout(rec), [])


# ---------------------------------------------------------------- item 4 end to end: run_morning wiring
class FakeModel(morning.Model):
    """One plain-words reply, whatever the prompt."""
    tools = ()

    def complete(self, prompt):
        return "What changed\n- Mail that triage could not place is waiting in the unclassified list.\n", None


class Wiring(unittest.TestCase):
    """A scratch front room: one cant_tell mail, one with no triage at all, one quarantined (refused at ingest)."""

    def setUp(self):
        self.root = _o.path.realpath(_t.mkdtemp(prefix="p3a-"))
        self.front = _o.path.join(self.root, "front-room")
        self.drop = _o.path.join(self.root, "drop")
        self.records = _o.path.join(self.root, "records", "context")
        _o.makedirs(self.drop)
        self._old = dict((k, _o.environ.get(k)) for k in ("AGE_FRONT_ROOM",))
        _o.environ["AGE_FRONT_ROOM"] = self.front
        self.addCleanup(self._restore)

    def _restore(self):
        for k, v in self._old.items():
            if v is None:
                _o.environ.pop(k, None)
            else:
                _o.environ[k] = v
        _sh.rmtree(self.root, ignore_errors=True)

    def _deliver(self, tid, mid, subject, triage, verdict="safe", seen="full"):
        d = {"schema": transcripts.SCHEMA, "thread_id": tid, "message_id": mid, "subject": subject,
             "from": "studio@example.com", "date": "2026-11-19 10:00", "label": "inbox", "verdict": verdict,
             "triage": triage if (verdict == "safe" and seen == "full") else None, "seen": seen, "internal_ms": 1000,
             "header": "# thread %s | subject: %s\n\n" % (tid, subject),
             "block": "=== message %s | 2026-11-19 | from: studio@example.com | label: inbox ===\nplain body about a reel\n\n" % mid}
        with open(_o.path.join(self.drop, "%s.%s.json" % (tid, mid)), "w", encoding="utf-8") as f:
            json.dump(d, f)

    def test_unclassified_reaches_the_record(self):
        ct, nt, q = "a000001", "a000002", "a000003"
        self._deliver("b000001", ct, "Cant tell subject", {"needs_me": "cant_tell", "area": "work"})
        self._deliver("b000002", nt, "No triage at all", None, seen="partial")
        self._deliver("b000003", q, "Quarantined subject", None, verdict="quarantine")
        out = transcripts.ingest(self.drop, mailroom_uid=_o.getuid())
        self.assertEqual(out.get("refused", 0), 1)  # planted (b): the quarantined one never even files
        res = morning.run_morning(FakeModel(), DAY, "planning", self.records)
        self.assertTrue(res["ok"], res.get("problems"))
        with open(res["record_path"], encoding="utf-8") as f:
            rec = f.read()
        # planted (a), end to end: the no-triage email is in the list (a version that silently drops it fails)
        self.assertIn("## Unclassified emails", rec)
        self.assertIn("No triage at all", rec)
        self.assertIn("Cant tell subject", rec)
        # planted (b): the quarantined mail is nowhere in the list
        self.assertNotIn("Quarantined subject", rec.split("## Unclassified emails")[1])
        self.assertEqual(rec.split("## Unclassified emails")[1].split("## What code read")[0].count("\n- "), 2)
        # item 5: the record passes the layout checker
        self.assertEqual(snapshot_layout.check_layout(rec), [])
        self.assertIn("## Capacity", rec)
        self.assertIn("RULE OF THUMB", rec)



# ---------------------------------------------------------------- slice A2 (build window gc1e follow-up)
# fix (a): the picture-section readers accept BOTH headings -- old staged files say "## Picture",
# new snapshots say "## World model"; an old file must still come back as the next morning's baseline.
# fix (b) / the owner's "airport" ruling (D8): subjects in the labelled Unclassified emails block are
# VERBATIM data, not instructions (grade_trick_run, which graded that, is retired with the trick-email runner, 4P.3R).
class A2FollowUp(unittest.TestCase):
    def test_fix_a_old_staged_file_with_picture_heading_is_still_the_baseline(self):
        # planted: an OLD staged file (## Picture) must still be picked up as the next morning's baseline.
        records = _t.mkdtemp(prefix="a2-old-baseline-")
        _ax.register(_sh.rmtree, records, True)
        with open(_o.path.join(records, "2026-11-14-desk-a.md"), "w", encoding="utf-8") as f:
            f.write("# Morning write-up 2026-11-14 - desk-a desk\n\n## Picture\n- The reels reel is paid.\n- Exampleland flight booked.\n\n## Questions\n- none\n")
        baseline, name = morning.previous_picture(records, "desk-a")
        self.assertIsNotNone(baseline)
        self.assertEqual(name, "2026-11-14-desk-a.md")
        self.assertIn("The reels reel is paid.", baseline)
        self.assertIn("Exampleland flight booked.", baseline)
        # and the NEW heading is read just the same
        with open(_o.path.join(records, "2026-11-19-desk-a.md"), "w", encoding="utf-8") as f:
            f.write("# Morning write-up 2026-11-19 - desk-a desk\n\n## World model\n- The new heading carries too.\n\n## Questions\n- none\n")
        baseline2, name2 = morning.previous_picture(records, "desk-a")
        self.assertEqual(name2, "2026-11-19-desk-a.md")
        self.assertIn("The new heading carries too.", baseline2)
        # fail-then-pass: the PRE-change reader (## Picture only) misses the new-heading file entirely
        pre_base, pre_name = pre.previous_picture(records, "desk-a")
        # the pre-change reader still NAMES the newest file (by mtime) but finds no "## Picture" in it,
        # so it returns NO baseline at all -- the next morning silently starts with no earlier draft.
        self.assertEqual(pre_name, "2026-11-19-desk-a.md")
        self.assertIsNone(pre_base)

    def test_fix_b_a_quarantined_or_flagged_envelope_is_absent_from_the_list(self):
        # planted (1): an envelope Sentinel quarantined or flagged is ABSENT from the unclassified list.
        rows = [
            {"message_id": "m1", "verdict": "safe", "subject": "Cant tell subject",
             "triage": {"needs_me": "cant_tell", "area": "none"}},
            {"message_id": "m2", "verdict": "quarantine", "subject": "Quarantined subject",
             "triage": {"needs_me": "cant_tell", "area": "none"}},
            {"message_id": "m3", "verdict": "flag", "subject": "Flagged subject",
             "triage": {"needs_me": "cant_tell", "area": "none"}},
        ]
        got = snapshot_layout.unclassified_rows(rows)
        self.assertEqual([u["message_id"] for u in got], ["m1"])
        self.assertNotIn("Quarantined subject", [u["subject"] for u in got])
        self.assertNotIn("Flagged subject", [u["subject"] for u in got])
        # fail-then-pass: the naive version (verdict ignored) leaks both
        def naive(rows):
            return [r for r in rows if (r.get("triage") or {}).get("needs_me") == "cant_tell"]
        leaked = [u["subject"] for u in naive(rows)]
        self.assertIn("Quarantined subject", leaked)
        self.assertIn("Flagged subject", leaked)

    def test_fix_b_an_envelope_that_never_went_through_the_scan_is_absent(self):
        # planted (2): an envelope with NO verdict at all (never scanned) is ABSENT from the list.
        rows = [
            {"message_id": "m1", "verdict": "safe", "subject": "Scanned and unplaced",
             "triage": {"needs_me": "cant_tell", "area": "none"}},
            {"message_id": "m2", "subject": "Never scanned subject",
             "triage": {"needs_me": "cant_tell", "area": "none"}},
        ]
        got = snapshot_layout.unclassified_rows(rows)
        self.assertEqual([u["message_id"] for u in got], ["m1"])
        self.assertNotIn("Never scanned subject", [u["subject"] for u in got])
        # fail-then-pass: the naive version (missing verdict read as safe) leaks the unscanned one
        def naive(rows):
            return [r for r in rows if r.get("verdict") in (None, "safe") and (r.get("triage") or {}).get("needs_me") == "cant_tell"]
        self.assertIn("Never scanned subject", [u["subject"] for u in naive(rows)])

if __name__ == "__main__":
    unittest.main(verbosity=2)

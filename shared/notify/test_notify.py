#!/usr/bin/env python3
"""test_notify.py — the matrix on the thing that decides whether your phone goes off.

Run:  python3 shared/notify/test_notify.py
      python3 -m unittest discover -s shared/notify -p 'test_*.py'

THE FAILURE THIS GUARDS AGAINST IS NOT "a notification did not arrive." It is the opposite. Three
buzzes that turn out to be nothing and a person stops reading the fourth; a few more and they mute
the app, and from then on the one alert that mattered is delivered to a muted app. Everything in this
gate exists to make that impossible, and every rule below is one that has to hold in BOTH directions:

  * it must suppress enough that the channel keeps its meaning
  * and it must NEVER suppress the one thing worth waking someone for

So the cases split cleanly. Most of them prove something gets blocked. A few prove something gets
through no matter what — and those are the ones to look at first if this file ever goes red, because
a gate that has quietly become a wall is worse than no gate: nothing is buzzing, everything looks
calm, and the alert you were relying on is sitting in a suppressed counter.

Every case points the state file at a temp directory, so a real notification history is never touched
and no test can consume a real day's allowance.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GOVERNOR = os.path.join(HERE, "notify-governor.py")
SENDER = os.path.join(HERE, "notify-send.sh")


class GovernorCase(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="notify-test-")
        self.state = os.path.join(self.tmp, "state.json")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def ask(self, source, message, priority="normal", **env):
        """One request at the gate. Returns (allowed, reason)."""
        e = dict(os.environ, NOTIFY_STATE_FILE=self.state)
        e.update({k: str(v) for k, v in env.items()})
        r = subprocess.run([sys.executable, GOVERNOR, source, message, priority],
                           capture_output=True, text=True, env=e)
        return r.returncode == 0, (r.stderr.strip() or r.stdout.strip())

    def backdate_all(self, seconds):
        """Age every recorded send, so windows can be tested without waiting for them."""
        with open(self.state) as f:
            st = json.load(f)
        for s in st.get("sent", []):
            s["ts"] -= seconds
        with open(self.state, "w") as f:
            json.dump(st, f)

    # ── the ordinary path ─────────────────────────────────────────────────────────────────────

    def test_the_first_one_goes_through(self):
        ok, _ = self.ask("scan", "found something", NOTIFY_QUIET_START=0, NOTIFY_QUIET_END=0)
        self.assertTrue(ok)

    def test_saying_the_same_thing_twice_only_buzzes_once(self):
        self.ask("scan", "found something", NOTIFY_QUIET_START=0, NOTIFY_QUIET_END=0)
        ok, why = self.ask("scan", "found something", NOTIFY_QUIET_START=0, NOTIFY_QUIET_END=0)
        self.assertFalse(ok)
        self.assertIn("duplicate", why)

    def test_a_different_message_from_the_same_source_still_goes_through(self):
        self.ask("scan", "first thing", NOTIFY_QUIET_START=0, NOTIFY_QUIET_END=0)
        ok, _ = self.ask("scan", "a different thing", NOTIFY_QUIET_START=0, NOTIFY_QUIET_END=0)
        self.assertTrue(ok, "deduplication is per message, not a blanket mute on the source")

    def test_the_duplicate_window_expires(self):
        self.ask("scan", "found something", NOTIFY_QUIET_START=0, NOTIFY_QUIET_END=0, NOTIFY_DEDUP_HOURS=1)
        self.backdate_all(2 * 3600)
        ok, _ = self.ask("scan", "found something", NOTIFY_QUIET_START=0, NOTIFY_QUIET_END=0, NOTIFY_DEDUP_HOURS=1)
        self.assertTrue(ok, "a day later the same thing is news again")

    # ── quiet hours ───────────────────────────────────────────────────────────────────────────

    def test_quiet_hours_hold_an_ordinary_notification(self):
        hour = time.localtime().tm_hour
        ok, why = self.ask("scan", "not urgent",
                           NOTIFY_QUIET_START=hour, NOTIFY_QUIET_END=(hour + 1) % 24)
        self.assertFalse(ok)
        self.assertIn("quiet hours", why)

    def test_a_window_that_wraps_past_midnight_still_works(self):
        """22:00 to 07:00 is the normal setting and the one an off-by-one breaks. Whatever time it
        is right now, a window built to contain this hour must contain it."""
        hour = time.localtime().tm_hour
        start, end = (hour - 1) % 24, (hour + 1) % 24
        ok, why = self.ask("scan", "not urgent", NOTIFY_QUIET_START=start, NOTIFY_QUIET_END=end)
        self.assertFalse(ok, f"hour {hour} should be inside [{start},{end}) and was not")

    def test_outside_the_window_it_goes_through(self):
        hour = time.localtime().tm_hour
        ok, _ = self.ask("scan", "not urgent",
                         NOTIFY_QUIET_START=(hour + 2) % 24, NOTIFY_QUIET_END=(hour + 3) % 24)
        self.assertTrue(ok)

    # ── the daily cap ─────────────────────────────────────────────────────────────────────────

    def test_a_source_runs_out_of_allowance(self):
        for i in range(3):
            ok, _ = self.ask("chatty", f"thing {i}", NOTIFY_QUIET_START=0, NOTIFY_QUIET_END=0, NOTIFY_DAILY_CAP=3)
            self.assertTrue(ok, f"send {i} should have gone through")
        ok, why = self.ask("chatty", "thing 4", NOTIFY_QUIET_START=0, NOTIFY_QUIET_END=0, NOTIFY_DAILY_CAP=3)
        self.assertFalse(ok)
        self.assertIn("daily cap", why)

    def test_the_cap_is_per_source_not_global(self):
        """One noisy source must not be able to silence a quiet one. That is how the alert you
        actually needed goes missing."""
        for i in range(3):
            self.ask("chatty", f"thing {i}", NOTIFY_QUIET_START=0, NOTIFY_QUIET_END=0, NOTIFY_DAILY_CAP=3)
        ok, _ = self.ask("quiet-one", "its first ever", NOTIFY_QUIET_START=0, NOTIFY_QUIET_END=0, NOTIFY_DAILY_CAP=3)
        self.assertTrue(ok)

    def test_a_cap_of_zero_means_unlimited_not_silent(self):
        """Reading 0 as "none allowed" would mute everything, and it would look like a working
        system. It means the cap is off."""
        for i in range(8):
            ok, why = self.ask("busy", f"thing {i}", NOTIFY_QUIET_START=0, NOTIFY_QUIET_END=0, NOTIFY_DAILY_CAP=0)
            self.assertTrue(ok, f"send {i} was blocked with: {why}")

    # ── critical: the things that must arrive ─────────────────────────────────────────────────

    def test_critical_goes_through_in_the_middle_of_the_night(self):
        hour = time.localtime().tm_hour
        ok, why = self.ask("security", "a real one", "critical",
                           NOTIFY_QUIET_START=hour, NOTIFY_QUIET_END=(hour + 1) % 24)
        self.assertTrue(ok, f"a critical alert was held by quiet hours: {why}")

    def test_critical_goes_through_after_the_cap_is_spent(self):
        for i in range(3):
            self.ask("security", f"routine {i}", NOTIFY_QUIET_START=0, NOTIFY_QUIET_END=0, NOTIFY_DAILY_CAP=3)
        ok, why = self.ask("security", "a real one", "critical",
                           NOTIFY_QUIET_START=0, NOTIFY_QUIET_END=0, NOTIFY_DAILY_CAP=3)
        self.assertTrue(ok, f"a critical alert was eaten by the daily cap: {why}")

    def test_the_same_critical_repeated_the_next_day_still_buzzes(self):
        """Critical deduplicates on a SHORT floor, not the full day. A problem that is still
        happening tomorrow is news again — a 24-hour window would silently eat it."""
        self.ask("security", "still broken", "critical", NOTIFY_CRITICAL_DEDUP_HOURS=1,
                 NOTIFY_CRITICAL_BURST_MINUTES=0)
        self.backdate_all(3 * 3600)
        ok, _ = self.ask("security", "still broken", "critical", NOTIFY_CRITICAL_DEDUP_HOURS=1,
                         NOTIFY_CRITICAL_BURST_MINUTES=0)
        self.assertTrue(ok)

    def test_a_stuck_source_cannot_ring_every_tick(self):
        """The other side of the same rule: a check running every five minutes and failing every
        time must not become a buzz every five minutes."""
        self.ask("security", "still broken", "critical", NOTIFY_CRITICAL_DEDUP_HOURS=1)
        ok, why = self.ask("security", "still broken", "critical", NOTIFY_CRITICAL_DEDUP_HOURS=1)
        self.assertFalse(ok)

    def test_one_incident_with_five_symptoms_is_one_buzz(self):
        """A single event often trips several distinct messages at once — one scan matching five
        patterns. Message-level deduplication cannot collapse those, because the messages differ.
        The burst window collapses them by source instead: the push is a doorbell, and every
        individual event is still in the log."""
        first, _ = self.ask("security", "pattern A", "critical", NOTIFY_CRITICAL_BURST_MINUTES=10)
        self.assertTrue(first)
        for p in ("pattern B", "pattern C", "pattern D"):
            ok, why = self.ask("security", p, "critical", NOTIFY_CRITICAL_BURST_MINUTES=10)
            self.assertFalse(ok, f"{p} rang separately — one incident should be one buzz")
            self.assertIn("burst", why)

    def test_a_genuinely_separate_incident_after_the_window_rings(self):
        self.ask("security", "pattern A", "critical", NOTIFY_CRITICAL_BURST_MINUTES=10)
        self.backdate_all(20 * 60)
        ok, _ = self.ask("security", "something else entirely", "critical", NOTIFY_CRITICAL_BURST_MINUTES=10)
        self.assertTrue(ok)

    def test_a_different_source_is_never_caught_by_another_ones_burst(self):
        self.ask("security", "pattern A", "critical", NOTIFY_CRITICAL_BURST_MINUTES=10)
        ok, _ = self.ask("disk-space", "nearly full", "critical", NOTIFY_CRITICAL_BURST_MINUTES=10)
        self.assertTrue(ok)

    # ── the state file itself ─────────────────────────────────────────────────────────────────

    def test_a_corrupt_state_file_does_not_silence_anything(self):
        """Failing towards SENDING is the right direction here. A state file that cannot be read
        must never be able to suppress an alert."""
        with open(self.state, "w") as f:
            f.write("{ not json")
        ok, _ = self.ask("scan", "found something", NOTIFY_QUIET_START=0, NOTIFY_QUIET_END=0)
        self.assertTrue(ok)

    def test_a_suppressed_request_is_not_recorded_as_a_send(self):
        """Otherwise a suppression would eat a slot from the day's allowance, and the cap would
        tighten every time it fired."""
        self.ask("scan", "same thing", NOTIFY_QUIET_START=0, NOTIFY_QUIET_END=0)
        self.ask("scan", "same thing", NOTIFY_QUIET_START=0, NOTIFY_QUIET_END=0)   # suppressed
        with open(self.state) as f:
            self.assertEqual(len(json.load(f)["sent"]), 1)

    def test_bad_arguments_are_a_usage_error_and_not_an_allow(self):
        r = subprocess.run([sys.executable, GOVERNOR, "only-one-arg"],
                           capture_output=True, text=True,
                           env=dict(os.environ, NOTIFY_STATE_FILE=self.state))
        self.assertEqual(r.returncode, 2)
        self.assertNotIn("ALLOW", r.stdout)


class SenderCase(unittest.TestCase):
    """The dispatcher around the gate. Never sends anything: every case is dry-run or a refusal."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="notify-send-test-")
        self.state = os.path.join(self.tmp, "state.json")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def send(self, *args, **env):
        e = dict(os.environ, NOTIFY_STATE_FILE=self.state, NOTIFY_DRY_RUN="1",
                 NOTIFY_QUIET_START="0", NOTIFY_QUIET_END="0")
        e.update({k: str(v) for k, v in env.items()})
        return subprocess.run(["bash", SENDER, *args], capture_output=True, text=True, env=e)

    def test_with_no_topic_it_says_where_to_put_one(self):
        e = dict(os.environ, NTFY_TOPIC_FILE=os.path.join(self.tmp, "nope"))
        e.pop("NTFY_TOPIC", None)
        r = subprocess.run(["bash", SENDER, "--source", "t", "--message", "m"],
                           capture_output=True, text=True, env=e)
        self.assertEqual(r.returncode, 2)
        self.assertIn("no topic set", r.stderr)
        self.assertIn("unguessable", r.stderr, "it should say why the topic matters, not just that it is missing")

    def test_the_topic_is_never_printed(self):
        """It is a shared secret: whoever knows the string can read every notification sent to it.
        It must not end up in a log, a transcript, or a screenshot of a terminal."""
        r = self.send("--source", "t", "--message", "m", NTFY_TOPIC="a-very-secret-topic-string")
        self.assertNotIn("a-very-secret-topic-string", r.stdout + r.stderr)

    def test_being_suppressed_is_not_an_error(self):
        """A caller must not treat "the gate held this back" as a failure and start retrying."""
        self.send("--source", "t", "--message", "same", NTFY_TOPIC="x")
        r = self.send("--source", "t", "--message", "same", NTFY_TOPIC="x")
        self.assertEqual(r.returncode, 0, "suppression must exit 0")
        self.assertIn("duplicate", r.stderr)

    def test_it_refuses_to_run_without_a_source_or_a_message(self):
        self.assertEqual(self.send("--message", "m", NTFY_TOPIC="x").returncode, 2)
        self.assertEqual(self.send("--source", "t", NTFY_TOPIC="x").returncode, 2)

    def test_critical_is_sent_at_the_urgent_priority(self):
        r = self.send("--source", "t", "--message", "m", "--priority", "critical", NTFY_TOPIC="x")
        self.assertIn("priority: 5", r.stdout)

    def test_the_gate_is_asked_before_anything_is_composed(self):
        """Belt and braces on the ordering: a dry run that was suppressed must print no payload at
        all, which proves the gate ran first rather than after the message was built."""
        self.send("--source", "t", "--message", "same", NTFY_TOPIC="x")
        r = self.send("--source", "t", "--message", "same", NTFY_TOPIC="x")
        self.assertNotIn("DRY_RUN", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)

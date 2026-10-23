#!/usr/bin/env python3
"""Tests for fire_journal_query.py (B4.2) — the read side of the fire-journal.

Two things matter more than the rest here: a malformed line is counted, never silently dropped and
never a crash; and a hook the register names but the journal never saw shows up in the coverage
gap, while one that fired does not. Everything else (filters, percentiles) is checked against
values computed independently in this file, not by re-deriving the tool's own formula.

Run: python3 system/tools/test_fire_journal_query.py
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
TOOL = os.path.join(HERE, "fire_journal_query.py")
sys.path.insert(0, HERE)
import fire_journal_query as fjq  # noqa: E402


def run(*args, journal=None):
    cmd = [sys.executable, TOOL]
    if journal is not None:
        cmd += ["--journal", journal]
    cmd += list(args)
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


class Fixture(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.journal = os.path.join(self.root, "fire-journal.jsonl")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def write_journal(self, lines):
        with open(self.journal, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    def run_json(self, *args):
        rc, out, err = run(*args, "--json", journal=self.journal)
        self.assertEqual(rc, 0, "expected exit 0, got %d; stderr=%s" % (rc, err))
        return json.loads(out)


class RotatedShards(Fixture):
    """B4.3: journal.sh now rotates to "<journal>.<epoch>.<pid>" shards under a byte cap. The
    query tool must read across them transparently -- Verify #5 of the rotation build report."""

    def write_shard(self, epoch, pid, lines):
        path = self.journal + (".%d.%d" % (epoch, pid))
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        return path

    def _line(self, i, hook):
        return json.dumps({"ts": 1700000000 + i, "hook": hook, "event": "PreToolUse",
                            "matcher": "Bash", "decision": "allow" if i % 3 else "deny",
                            "exit_code": 0 if i % 3 else 2, "session_id": "s1"})

    def test_rotated_plus_current_matches_single_unrotated_file_exactly(self):
        lines = [self._line(i, "guard_x.sh" if i % 2 == 0 else "guard_y.sh") for i in range(60)]

        single_dir = tempfile.mkdtemp()
        try:
            single_path = os.path.join(single_dir, "single.jsonl")
            with open(single_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
            rc, out, err = run("--json", journal=single_path)
            self.assertEqual(rc, 0, err)
            single_result = json.loads(out)
        finally:
            shutil.rmtree(single_dir, ignore_errors=True)

        self.write_shard(1700000000, 111, lines[0:20])
        self.write_shard(1700000010, 222, lines[20:40])
        self.write_journal(lines[40:60])
        rotated_result = self.run_json()

        for key in ("total_lines_seen", "malformed_count", "kept_count",
                    "by_hook", "by_event", "by_matcher"):
            self.assertEqual(single_result[key], rotated_result[key],
                              "mismatch on %r: %r != %r" % (key, single_result[key], rotated_result[key]))

    def test_shards_read_oldest_first_then_live_file_last(self):
        self.write_shard(1700000010, 222, [self._line(2, "guard_newer_shard.sh")])
        self.write_shard(1700000000, 111, [self._line(1, "guard_older_shard.sh")])
        self.write_journal([self._line(3, "guard_live.sh")])
        files = fjq.discover_journal_files(self.journal)
        names = [os.path.basename(f) for f in files]
        self.assertEqual(names, [
            os.path.basename(self.journal) + ".1700000000.111",
            os.path.basename(self.journal) + ".1700000010.222",
            os.path.basename(self.journal),
        ])

    def test_sidecar_meta_files_never_mistaken_for_shards(self):
        self.write_shard(1700000000, 111, [self._line(1, "guard_a.sh")])
        self.write_journal([self._line(2, "guard_b.sh")])
        # Exactly what journal.sh's rotation logic writes alongside the journal.
        base = os.path.basename(self.journal)
        with open(os.path.join(self.root, "." + base + ".rotstate"), "w", encoding="utf-8") as f:
            f.write("1700000000")
        os.mkdir(os.path.join(self.root, "." + base + ".rotlock"))
        files = fjq.discover_journal_files(self.journal)
        self.assertEqual(len(files), 2)
        for f in files:
            self.assertNotIn("rotstate", f)
            self.assertNotIn("rotlock", f)

    def test_no_rotated_flag_reads_only_the_exact_path_given(self):
        self.write_shard(1700000000, 111, [self._line(1, "guard_in_shard_only.sh")])
        self.write_journal([self._line(2, "guard_in_live_only.sh")])
        result = self.run_json("--no-rotated")
        hooks = set(result["by_hook"] and [r["name"] for r in result["by_hook"]])
        self.assertIn("guard_in_live_only.sh", hooks)
        self.assertNotIn("guard_in_shard_only.sh", hooks)
        self.assertEqual(result["journal_files"], [self.journal])

    def test_missing_live_file_but_rotated_shards_exist_is_not_reported_missing(self):
        self.write_shard(1700000000, 111, [self._line(1, "guard_only_in_shard.sh")])
        # self.journal itself deliberately never created.
        result = self.run_json()
        self.assertFalse(result["journal_missing"])
        self.assertEqual(result["kept_count"], 1)


class MissingAndEmpty(Fixture):
    def test_missing_journal_file_is_not_a_crash(self):
        rc, out, err = run("--json", journal=os.path.join(self.root, "does-not-exist.jsonl"))
        self.assertEqual(rc, 0)
        d = json.loads(out)
        self.assertTrue(d["journal_missing"])
        self.assertEqual(d["kept_count"], 0)
        self.assertEqual(d["malformed_count"], 0)

    def test_empty_journal_file(self):
        open(self.journal, "w", encoding="utf-8").close()
        d = self.run_json()
        self.assertEqual(d["kept_count"], 0)
        self.assertEqual(d["malformed_count"], 0)


class MalformedLines(Fixture):
    """The one thing the spec is explicit about: malformed lines are tolerated, COUNTED exactly,
    and never cause a non-zero exit — never silently skipped without being reported."""

    def test_three_malformed_lines_counted_exactly_exit_zero(self):
        good = json.dumps({"ts": 1000, "hook": "guard_x.sh", "event": "PreToolUse",
                            "decision": "allow", "exit_code": 0})
        bad_json = '{"ts": 1000, "hook": "guard_x.sh"'  # truncated, not valid JSON
        bad_missing_field = json.dumps({"ts": 1000, "event": "PreToolUse",
                                         "decision": "deny", "exit_code": 2})  # no "hook"
        bad_decision = json.dumps({"ts": 1000, "hook": "guard_x.sh", "event": "PreToolUse",
                                    "decision": "maybe", "exit_code": 0})
        self.write_journal([good, bad_json, good, bad_missing_field, good, bad_decision, good])
        d = self.run_json()
        self.assertEqual(d["malformed_count"], 3)
        self.assertEqual(d["kept_count"], 4)
        self.assertEqual(len(d["malformed_samples"]), 3)

    def test_blank_lines_are_not_malformed(self):
        good = json.dumps({"ts": 1000, "hook": "guard_x.sh", "event": "PreToolUse",
                            "decision": "allow", "exit_code": 0})
        self.write_journal([good, "", "   ", good])
        d = self.run_json()
        self.assertEqual(d["malformed_count"], 0)
        self.assertEqual(d["kept_count"], 2)

    def test_malformed_count_always_printed_in_table_mode_too(self):
        self.write_journal(['not even json'])
        rc, out, err = run(journal=self.journal)
        self.assertEqual(rc, 0)
        self.assertIn("Malformed lines: 1", out)


class DecisionsAndOptionalFields(Fixture):
    def test_missing_optional_fields_handled_gracefully(self):
        # No matcher, no duration_ms, no session_id -- only the required fields.
        rec = {"ts": 1000, "hook": "guard_x.sh", "event": "PreToolUse",
               "decision": "allow", "exit_code": 0}
        self.write_journal([json.dumps(rec)])
        d = self.run_json()
        self.assertEqual(d["malformed_count"], 0)
        self.assertEqual(d["kept_count"], 1)
        row = d["by_hook"][0]
        self.assertEqual(row["fires"], 1)
        self.assertIsNone(row["median_ms"])
        self.assertIsNone(row["p95_ms"])

    def test_decision_aliases_fold_into_the_closed_set(self):
        recs = [
            {"ts": 1, "hook": "h.sh", "event": "PreToolUse", "decision": "block", "exit_code": 2},
            {"ts": 2, "hook": "h.sh", "event": "PreToolUse", "decision": "Allowed", "exit_code": 0},
        ]
        self.write_journal([json.dumps(r) for r in recs])
        d = self.run_json()
        self.assertEqual(d["malformed_count"], 0)
        row = d["by_hook"][0]
        self.assertEqual(row["deny"], 1)
        self.assertEqual(row["allow"], 1)

    def test_iso_and_epoch_ts_both_accepted(self):
        recs = [
            {"ts": 1_700_000_000, "hook": "h.sh", "event": "PreToolUse", "decision": "allow", "exit_code": 0},
            {"ts": "2023-11-14T22:13:20Z", "hook": "h.sh", "event": "PreToolUse", "decision": "allow", "exit_code": 0},
        ]
        self.write_journal([json.dumps(r) for r in recs])
        d = self.run_json()
        self.assertEqual(d["malformed_count"], 0)
        self.assertEqual(d["kept_count"], 2)


class Filters(Fixture):
    def setUp(self):
        super().setUp()
        self.now = time.time()
        recs = []
        for day_offset in range(6):
            recs.append({
                "ts": self.now - day_offset * 86400 - 30,
                "hook": "guard_x.sh", "event": "PreToolUse", "matcher": "Bash",
                "decision": "allow", "exit_code": 0,
                "session_id": "sess-A" if day_offset % 2 == 0 else "sess-B",
            })
        self.write_journal([json.dumps(r) for r in recs])

    def test_since_relative_duration(self):
        d = self.run_json("--since", "2.5d")  # keeps day_offset 0,1,2 -> 3 lines
        self.assertEqual(d["kept_count"], 3)

    def test_since_absolute_epoch(self):
        cutoff = self.now - 2.5 * 86400
        d = self.run_json("--since", str(cutoff))
        self.assertEqual(d["kept_count"], 3)

    def test_session_filter(self):
        d = self.run_json("--session", "sess-A")
        self.assertEqual(d["kept_count"], 3)  # day_offset 0, 2, 4
        d = self.run_json("--session", "sess-B")
        self.assertEqual(d["kept_count"], 3)  # day_offset 1, 3, 5

    def test_since_and_session_combined(self):
        d = self.run_json("--since", "2.5d", "--session", "sess-A")
        self.assertEqual(d["kept_count"], 2)  # day_offset 0, 2


class Coverage(Fixture):
    def setUp(self):
        super().setUp()
        recs = [{"ts": 1, "hook": "guard_seen.sh", "event": "PreToolUse",
                  "decision": "allow", "exit_code": 0}]
        self.write_journal([json.dumps(r) for r in recs])
        self.register = os.path.join(self.root, "register.jsonl")
        with open(self.register, "w", encoding="utf-8") as f:
            f.write(json.dumps({"hook": "guard_seen.sh", "event": "PreToolUse"}) + "\n")
            f.write(json.dumps({"hook": "guard_unseen.sh", "event": "PreToolUse"}) + "\n")

    def test_zero_fire_hook_named_seen_hook_not(self):
        d = self.run_json("--registered", self.register)
        self.assertIn("guard_unseen.sh", d["coverage"]["zero_fire"])
        self.assertNotIn("guard_seen.sh", d["coverage"]["zero_fire"])
        self.assertIn("guard_seen.sh", d["coverage"]["covered"])

    def test_wiring_shaped_register_also_works(self):
        wiring = {
            "hooks": {
                "PreToolUse": [
                    {"matcher": "Bash", "hooks": [
                        {"type": "command",
                         "command": 'bash "${CLAUDE_PLUGIN_ROOT}/system/hooks/guard_seen.sh"'},
                        {"type": "command",
                         "command": 'bash "${CLAUDE_PLUGIN_ROOT}/system/hooks/guard_unseen.sh"'},
                    ]},
                ]
            }
        }
        wiring_path = os.path.join(self.root, "hooks.json")
        with open(wiring_path, "w", encoding="utf-8") as f:
            json.dump(wiring, f)
        d = self.run_json("--registered", wiring_path)
        self.assertIn("guard_unseen.sh", d["coverage"]["zero_fire"])
        self.assertIn("guard_seen.sh", d["coverage"]["covered"])


class PercentileUnit(unittest.TestCase):
    """The percentile helper checked directly, independent of any journal fixture."""

    def test_known_values(self):
        vals = sorted([1.5, 4.75, 4.75, 8.0, 11.25, 14.5, 14.5, 17.75])
        self.assertAlmostEqual(fjq.percentile(vals, 50), 9.625)
        self.assertAlmostEqual(fjq.percentile(vals, 95), 16.6125, places=3)

    def test_single_value(self):
        self.assertEqual(fjq.percentile([42.0], 95), 42.0)

    def test_empty(self):
        self.assertIsNone(fjq.percentile([], 50))


if __name__ == "__main__":
    unittest.main()

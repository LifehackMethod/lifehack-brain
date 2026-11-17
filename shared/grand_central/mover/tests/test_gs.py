# origin: 92a9739:mover/tests/test_gs.py
"""Code.gs run under node with a pretend Gmail + Drive (no network)."""
import json, hashlib, shutil, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gsrun import gs, ids, req, submit, result, LABELS  # noqa: E402

SETUP = [{"call": "setup"}]


def inbox_msgs(n, extra=None, start=0):
    return {i: ["INBOX"] + (extra or []) for i in ids(n, start)}


def move_logs(out):
    names = sorted(n for n in out["files"] if n.startswith("move-") and n.endswith(".json"))
    return [json.loads(out["files"][n]["content"]) for n in names]


def batches(out):
    return [c for c in out["calls"] if c["fn"] == "batchModify"]


@unittest.skipUnless(shutil.which("node"), "node not installed")
class Mover(unittest.TestCase):
    def test_setup_idempotent(self):
        out = gs(SETUP + SETUP + SETUP)
        self.assertEqual(out["folders"], 1)
        self.assertEqual(sorted(out["files"]), ["request.json", "result.json"])
        self.assertEqual(out["triggers"], [{"fn": "run", "minutes": 15}])

    def test_teardown(self):
        out = gs(SETUP + [{"call": "teardownTriggers"}])
        self.assertEqual(out["triggers"], [])

    def test_apply_add_and_archive(self):
        m = inbox_msgs(3, ["Keep"])
        rq = req([{"op": "addLabel", "label": "Projects/Alpha", "ids": ids(2)}, {"op": "archive", "ids": ids(3)}])
        out = gs(SETUP + submit(rq), messages=m)
        self.assertEqual(out["results"][-1], "done")
        self.assertEqual(out["messages"][ids(3)[0]], ["Keep", "Label_1"])
        self.assertEqual(out["messages"][ids(3)[2]], ["Keep"])
        r = result(out)
        self.assertEqual(r["status"], "done")
        self.assertEqual([(a["op"], a.get("label"), a["count"]) for a in r["actions"]],
                         [("addLabel", "Projects/Alpha", 2), ("archive", None, 3)])
        self.assertEqual(r["actions"][0]["ids_hash"], hashlib.sha256(",".join(sorted(ids(2))).encode()).hexdigest())
        self.assertEqual(len(r["usage"]), 1)

    def _read_mode_applies(self, mode):
        rq = req([{"op": "archive", "ids": ids(1)}])
        out = gs(SETUP + submit(rq), messages=inbox_msgs(1), read_mode=mode)
        self.assertEqual(out["results"][-1], "done")
        self.assertEqual(out["messages"][ids(1)[0]], [])

    def test_drive_read_blob_like(self):
        self._read_mode_applies("blob")

    def test_drive_read_byte_array(self):
        self._read_mode_applies("bytes")

    def test_drive_read_parsed_json_object(self):
        self._read_mode_applies("parsed")

    def test_drive_read_parsed_json_roundtrips(self):
        out = gs(SETUP + submit(req([{"op": "archive", "ids": ids(1)}])) +
                 [{"call": "readText_", "args": [{"id": "f2"}, {"drive_ops": 0}]}], messages=inbox_msgs(1), read_mode="parsed")
        self.assertIsInstance(json.loads(out["results"][-1]), dict)

    def test_drive_read_unknown_shape_reports_it(self):
        out = gs(SETUP + [{"call": "readText_", "args": [{"id": "f2"}, {"drive_ops": 0}]}], read_mode="weird")
        self.assertIn("[object Number]", out["results"][-1])

    def test_archive_only_removes_inbox(self):
        out = gs(SETUP + submit(req([{"op": "archive", "ids": ids(2)}])), messages=inbox_msgs(2, ["Keep", "Label_1"]))
        for c in batches(out):
            self.assertEqual(c["body"], {"ids": ids(2), "removeLabelIds": ["INBOX"]})
        self.assertEqual(out["messages"][ids(2)[0]], ["Keep", "Label_1"])

    def test_modify_bodies_are_exact(self):
        rq = req([{"op": "addLabel", "label": "Projects/Alpha", "ids": ids(1)}, {"op": "removeLabel", "label": "Archive-Me", "ids": ids(1)}])
        out = gs(SETUP + submit(rq), messages=inbox_msgs(1))
        self.assertEqual([c["body"] for c in batches(out)],
                         [{"ids": ids(1), "addLabelIds": ["Label_1"]}, {"ids": ids(1), "removeLabelIds": ["Label_2"]}])
        self.assertTrue(all(c["u"] == "me" for c in out["calls"]))
        self.assertEqual({c["fn"] for c in out["calls"]}, {"Labels.list", "batchModify"})

    def test_refusals_touch_nothing_and_are_not_retried(self):
        bad = req([{"op": "addLabel", "label": "Projects/Alpha", "ids": ids(1)}, {"op": "delete", "ids": ids(1)}])
        out = gs(SETUP + submit(bad) + [{"call": "run"}, {"call": "run"}], messages=inbox_msgs(1))
        self.assertEqual(out["results"][1:], ["refused", "idle", "idle"])
        self.assertEqual(batches(out), [])
        self.assertEqual(result(out)["status"], "refused")
        self.assertEqual(out["messages"][ids(1)[0]], ["INBOX"])

    def test_missing_label_refuses_whole_request(self):
        rq = req([{"op": "archive", "ids": ids(1)}, {"op": "addLabel", "label": "Nope", "ids": ids(1)}])
        out = gs(SETUP + submit(rq), messages=inbox_msgs(1))
        self.assertEqual(batches(out), [])
        self.assertIn("label not found", result(out)["errors"][0])

    def test_system_type_label_refused(self):
        labels = LABELS + [{"id": "Label_9", "name": "Weird", "type": "system"}]
        out = gs(SETUP + submit(req([{"op": "addLabel", "label": "Weird", "ids": ids(1)}])), messages=inbox_msgs(1), labels=labels)
        self.assertEqual(batches(out), [])
        self.assertEqual(result(out)["status"], "refused")

    def test_cap_per_request(self):
        rq = req([{"op": "archive", "ids": ids(4)}])
        out = gs(SETUP + submit(rq), messages=inbox_msgs(4), constants={"MAX_IDS_PER_REQUEST": 3})
        self.assertEqual(batches(out), [])
        self.assertIn("too many ids", result(out)["errors"][0])
        out = gs(SETUP + submit(req([{"op": "archive", "ids": ids(3)}])), messages=inbox_msgs(3), constants={"MAX_IDS_PER_REQUEST": 3})
        self.assertEqual(result(out)["status"], "done")

    def test_batches_of_batch_size_and_per_run_call_cap(self):
        k = {"BATCH_SIZE": 2, "MAX_BATCH_CALLS_PER_RUN": 2}
        out = gs(SETUP + submit(req([{"op": "archive", "ids": ids(5)}])) + [{"call": "run"}], messages=inbox_msgs(5), constants=k)
        self.assertEqual([len(c["body"]["ids"]) for c in batches(out)], [2, 2, 1])
        self.assertEqual(out["results"][1:], ["in_progress", "done"])
        self.assertEqual(sum(1 for v in out["messages"].values() if "INBOX" in v), 0)

    def test_cursor_carry_over_on_time_budget(self):
        k = {"BATCH_SIZE": 2}
        steps = SETUP + [{"per_call_ms": 70000}] + submit(req([{"op": "archive", "ids": ids(6)}]))
        out1 = gs(steps, messages=inbox_msgs(6), constants=k)
        self.assertEqual(out1["results"][-1], "in_progress")        # budget (120 s) spent after one 70 s call plus one more
        self.assertLess(len(batches(out1)), 3)
        self.assertEqual(result(out1)["status"], "in_progress")
        out = gs(steps + [{"call": "run"}] * 4, messages=inbox_msgs(6), constants=k)
        self.assertEqual([r for r in out["results"] if r in ("in_progress", "done")][:2], ["in_progress", "done"])
        seen = [i for c in batches(out) for i in c["body"]["ids"]]
        self.assertEqual(sorted(seen), sorted(ids(6)))              # each id modified exactly once across runs
        self.assertEqual(len(set(seen)), 6)
        self.assertEqual(result(out)["actions"][0]["count"], 6)
        self.assertNotIn("CURSOR", out["props"])

    def test_request_changed_mid_flight_aborts_old(self):
        k = {"BATCH_SIZE": 2, "MAX_BATCH_CALLS_PER_RUN": 1}
        new = req([{"op": "archive", "ids": ids(1, 100)}], rid="req-test-0002")
        steps = SETUP + submit(req([{"op": "archive", "ids": ids(4)}])) + submit(new)
        out = gs(steps, messages={**inbox_msgs(4), **inbox_msgs(1, start=100)}, constants=k)
        self.assertEqual(out["results"][1:], ["in_progress", "done"])
        self.assertEqual(out["messages"][ids(4)[3]], ["INBOX"])     # old request was abandoned, not finished
        self.assertEqual(result(out)["request_id"], "req-test-0002")

    def test_same_request_applied_once(self):
        out = gs(SETUP + submit(req([{"op": "archive", "ids": ids(1)}])) + [{"call": "run"}, {"call": "run"}], messages=inbox_msgs(1))
        self.assertEqual(len(batches(out)), 1)
        self.assertEqual(out["results"][1:], ["done", "idle", "idle"])

    def test_undo_log_inverse_restores_state(self):
        m = inbox_msgs(4, ["Archive-Me"])
        m = {k: (v + ["Label_2"] if False else v) for k, v in m.items()}   # keep literal ids; label NAME is Archive-Me, id Label_2
        m = {i: ["INBOX", "Label_2"] for i in ids(4)}
        rq = req([{"op": "addLabel", "label": "Projects/Alpha", "ids": ids(3)}, {"op": "removeLabel", "label": "Archive-Me", "ids": ids(2)},
                  {"op": "archive", "ids": ids(4)}])
        out = gs(SETUP + [{"snapshot": "before"}] + submit(rq), messages=m, constants={"BATCH_SIZE": 2})
        self.assertEqual(result(out)["status"], "done")
        lines = move_logs(out)
        self.assertEqual(len(lines), 2 + 1 + 2)                     # 3 ids/2 -> 2 batches, 2 ids/2 -> 1, 4 ids/2 -> 2
        self.assertEqual([l["undo"]["op"] for l in lines if l["op"] == "archive"], ["addLabel", "addLabel"])
        self.assertEqual({l["undo"]["label"] for l in lines if l["op"] == "archive"}, {"INBOX"})
        undo = [l["undo"] for l in reversed(lines)]
        undo_req = req(undo, rid="req-undo-0001")
        out2 = gs(SETUP + [{"snapshot": "before"}] + submit(rq) + submit(undo_req), messages=m, constants={"BATCH_SIZE": 2})
        self.assertEqual(out2["messages"], out2["snaps"]["before"])
        self.assertEqual(result(out2)["request_id"], "req-undo-0001")

    def test_trash_adds_only_the_trash_label_and_untrash_undoes_it(self):
        m = {i: ["INBOX", "Label_1"] for i in ids(3)}
        out = gs(SETUP + submit(req([{"op": "trash", "ids": ids(3)}])), messages=m)
        self.assertEqual(result(out)["status"], "done")
        self.assertEqual([c["body"] for c in batches(out)], [{"ids": ids(3), "addLabelIds": ["TRASH"]}])
        self.assertEqual({c["fn"] for c in out["calls"]}, {"batchModify"})      # no Labels.list needed, no other call
        self.assertEqual(out["messages"][ids(3)[0]], ["INBOX", "Label_1", "TRASH"])
        self.assertNotIn("label", result(out)["actions"][0])
        lg = move_logs(out)
        self.assertEqual([(l["op"], l["label"], l["undo"]["op"], l["undo"]["ids"]) for l in lg], [("trash", None, "untrash", ids(3))])
        out2 = gs(SETUP + [{"snapshot": "before"}] + submit(req([{"op": "trash", "ids": ids(3)}])) +
                  submit(req([lg[0]["undo"]], rid="req-undo-0002")), messages=m)
        self.assertEqual(batches(out2)[-1]["body"], {"ids": ids(3), "removeLabelIds": ["TRASH"]})
        self.assertEqual(out2["messages"], out2["snaps"]["before"])

    def test_trash_over_its_cap_refuses_everything(self):
        rq = req([{"op": "archive", "ids": ids(1)}, {"op": "trash", "ids": ids(4, 10)}])
        out = gs(SETUP + submit(rq), messages={**inbox_msgs(1), **inbox_msgs(4, start=10)}, constants={"MAX_TRASH_IDS_PER_REQUEST": 3})
        self.assertEqual(batches(out), [])
        self.assertIn("too many trash ids", result(out)["errors"][0])

    def test_paused_is_a_noop(self):
        steps = SETUP + [{"call": "pause"}] + submit(req([{"op": "archive", "ids": ids(1)}]))
        out = gs(steps, messages=inbox_msgs(1))
        self.assertEqual(out["results"][-1], "paused")
        self.assertEqual(out["calls"], [])
        self.assertEqual(out["messages"][ids(1)[0]], ["INBOX"])
        self.assertEqual(result(out)["usage"], [])
        self.assertIn("paused", out["log"])
        out = gs(steps + [{"call": "resume"}, {"call": "run"}], messages=inbox_msgs(1))
        self.assertEqual(out["results"][-1], "done")

    def test_gmail_failure_retries_then_recovers(self):
        steps = SETUP + [{"gmail_fail": 1}] + submit(req([{"op": "archive", "ids": ids(1)}])) + [{"call": "run"}]
        out = gs(steps, messages=inbox_msgs(1))
        self.assertEqual(out["results"][1:], ["in_progress", "done"])
        self.assertEqual(out["messages"][ids(1)[0]], [])

    def test_gmail_failure_gives_up_after_three_runs(self):
        steps = SETUP + [{"gmail_fail": 9}] + submit(req([{"op": "archive", "ids": ids(1)}])) + [{"call": "run"}, {"call": "run"}]
        out = gs(steps, messages=inbox_msgs(1))
        self.assertEqual(out["results"][1:], ["in_progress", "in_progress", "failed"])
        self.assertEqual(result(out)["status"], "failed")

    def test_half_written_json_waits_then_refuses(self):
        steps = SETUP + [{"mac_write": {"name": "request.json", "content": '{"request_id": "req-half-0001", "act'}}, {"call": "run"}, {"call": "run"}, {"call": "run"}]
        out = gs(steps)
        self.assertEqual(out["results"][1:], ["unreadable_wait", "refused", "idle"])

    def test_mac_edit_keeps_file_id(self):
        a = gs(SETUP)["files"]["request.json"]["id"]
        b = gs(SETUP + submit(req([{"op": "archive", "ids": ids(1)}])), messages=inbox_msgs(1))["files"]["request.json"]["id"]
        self.assertEqual(a, b)

    def test_usage_logged_and_pruned_to_30_days(self):
        old = {"schema": 1, "usage": [{"ts": "2026-09-01T00:00:00.000Z", "runtime_ms": 1}, {"ts": "2026-11-01T00:00:00.000Z", "runtime_ms": 2}]}
        steps = SETUP + [{"mac_write": {"name": "result.json", "content": json.dumps(old)}}] + submit(req([{"op": "archive", "ids": ids(5)}]))
        out = gs(steps, messages=inbox_msgs(5), per_call_ms=1000)
        u = result(out)["usage"]
        self.assertEqual([x["runtime_ms"] for x in u[:1]], [2])
        self.assertEqual(len(u), 2)
        last = u[-1]
        self.assertEqual(set(last), {"ts", "runtime_ms", "gmail_calls", "ids_modified", "drive_ops", "properties_ops"})
        self.assertEqual((last["gmail_calls"], last["ids_modified"], last["runtime_ms"]), (1, 5, 1000))
        self.assertGreater(last["drive_ops"], 0)

    def test_empty_request_file_is_no_request(self):
        out = gs(SETUP + [{"mac_write": {"name": "request.json", "content": ""}}, {"call": "run"}])
        self.assertEqual(out["results"][-1], "idle")
        self.assertNotIn("error", json.dumps(result(out)))

    def test_idle_run_appends_usage(self):
        out = gs(SETUP + [{"call": "run"}, {"call": "run"}])
        self.assertEqual(len(result(out)["usage"]), 2)

    # ---- request-changed detection is on the CANONICAL parsed request, never raw bytes ----
    K2 = {"BATCH_SIZE": 2, "MAX_BATCH_CALLS_PER_RUN": 1}

    def _two_run(self, middle, **kw):
        rq = req([{"op": "archive", "ids": ids(4)}])
        steps = SETUP + submit(rq) + middle + [{"call": "run"}, {"call": "run"}]
        return gs(steps, messages=inbox_msgs(4), constants=self.K2, **kw)

    def test_changed_check_raw_text_then_parsed_object_continues(self):
        out = self._two_run([{"read_mode": "parsed"}])
        self.assertEqual(out["results"][1:], ["in_progress", "done", "idle"])
        self.assertEqual(result(out)["status"], "done")
        self.assertEqual(sum(1 for v in out["messages"].values() if "INBOX" in v), 0)

    def test_changed_check_parsed_then_bytes_continues(self):
        out = self._two_run([{"read_mode": "bytes"}], read_mode="parsed")
        self.assertEqual(out["results"][1:], ["in_progress", "done", "idle"])

    def test_changed_check_whitespace_and_key_order_continue(self):
        rq = req([{"op": "archive", "ids": ids(4)}])
        reordered = json.dumps({"actions": [{"ids": ids(4), "op": "archive"}], "created_at": rq["created_at"],
                                "request_id": rq["request_id"]}, indent=3)
        steps = SETUP + submit(rq) + [{"mac_write": {"name": "request.json", "content": reordered + "\n\n"}}, {"call": "run"}, {"call": "run"}]
        out = gs(steps, messages=inbox_msgs(4), constants=self.K2)
        self.assertEqual(out["results"][1:], ["in_progress", "done", "idle"])
        self.assertNotEqual(result(out)["status"], "aborted_request_changed")

    def test_changed_check_genuinely_changed_ids_still_aborts(self):
        rq = req([{"op": "archive", "ids": ids(4)}])
        changed = req([{"op": "archive", "ids": ids(4, 50)}])
        steps = SETUP + submit(rq) + [{"mac_write": {"name": "request.json", "content": json.dumps(changed)}}, {"call": "run"}]
        out = gs(steps, messages=inbox_msgs(4), constants=self.K2)
        self.assertEqual(out["results"][1], "in_progress")
        self.assertEqual(result(out)["status"], "aborted_request_changed")
        self.assertEqual(out["messages"][ids(4)[3]], ["INBOX"])

    def test_changed_check_cursor_hash_ignores_raw_bytes(self):
        out = self._two_run([])
        cur = json.loads(out["props"].get("CURSOR", "{}") or "{}")
        self.assertEqual(out["results"][1:], ["in_progress", "done", "idle"])
        self.assertEqual(cur, {})

    # ---- the run-1 stop: an exception AFTER a successful batch (move log / properties) used to end the run silently ----
    def test_move_log_failure_does_not_stop_the_run_and_is_recorded(self):
        k = {"BATCH_SIZE": 1, "MAX_BATCH_CALLS_PER_RUN": 10}
        steps = SETUP + [{"drive_fail": {"prefix": "move-", "times": 1}}] + submit(req([{"op": "archive", "ids": ids(3)}]))
        out = gs(steps, messages=inbox_msgs(3), constants=k)
        self.assertEqual(out["results"][-1], "done")
        self.assertEqual(len(batches(out)), 3)
        r = result(out)
        self.assertEqual(len(r["errors_history"]), 1)
        e = r["errors_history"][0]
        self.assertEqual((e["request_id"], e["batch"]), ("req-test-0001", 0))
        self.assertIn("move log write failed", e["error"])
        self.assertIn("move log write failed", r["last_error"])

    def test_cursor_saved_before_move_log_so_progress_is_never_lost(self):
        k = {"BATCH_SIZE": 1, "MAX_BATCH_CALLS_PER_RUN": 1}
        steps = SETUP + [{"drive_fail": {"prefix": "move-", "times": 5}}] + submit(req([{"op": "archive", "ids": ids(3)}]))
        out = gs(steps, messages=inbox_msgs(3), constants=k)
        self.assertEqual(json.loads(out["props"]["CURSOR"])["next"], 1)

    def test_errors_history_bounded_and_gmail_errors_recorded(self):
        k = {"BATCH_SIZE": 1, "MAX_FAILED_RUNS": 100}
        steps = SETUP + [{"gmail_fail": 30}] + submit(req([{"op": "archive", "ids": ids(1)}])) + [{"call": "run"}] * 24
        out = gs(steps, messages=inbox_msgs(1), constants=k)
        h = result(out)["errors_history"]
        self.assertEqual(len(h), 20)
        self.assertIn("quota", h[-1]["error"])
        self.assertEqual(set(h[0]), {"ts", "request_id", "batch", "error"})
        self.assertIn("quota", result(out)["last_error"])

    def test_unexpected_exception_lands_in_errors_history(self):
        out = gs(SETUP + [{"prop": {"CURSOR": "{not json"}}] + submit(req([{"op": "archive", "ids": ids(1)}])), messages=inbox_msgs(1))
        self.assertTrue(out["results"][-1].startswith("error:"))
        self.assertIn("run error", result(out)["errors_history"][-1]["error"])


class MoveLogLive(unittest.TestCase):
    """Drive mock matches the live service: JSON media is returned parsed, non-JSON throws HttpResponseException(200, body)."""
    K = {"BATCH_SIZE": 1, "MAX_BATCH_CALLS_PER_RUN": 10}

    def test_every_batch_logged_no_errors_and_undo_recoverable(self):
        out = gs(SETUP + submit(req([{"op": "archive", "ids": ids(3)}])), messages=inbox_msgs(3), constants=self.K)
        self.assertEqual(out["results"][-1], "done")
        r = result(out)
        self.assertNotIn("errors_history", r)
        self.assertNotIn("last_error", r)
        logs = move_logs(out)
        self.assertEqual(len(logs), 3)
        self.assertEqual([l["batch"] for l in logs], [0, 1, 2])
        self.assertEqual(set(logs[0]), {"ts", "request_id", "batch", "action", "op", "label", "count", "undo"})
        self.assertEqual(sorted(i for l in logs for i in l["undo"]["ids"]), ids(3))
        self.assertEqual({l["undo"]["op"] for l in logs}, {"addLabel"})
        self.assertFalse([n for n in out["files"] if n.startswith("moves-")])

    def test_old_jsonl_present_does_not_break_anything(self):
        old = '{"ts":"2026-11-12T21:04:37.659Z","undo":{"op":"addLabel","label":"INBOX","ids":["abc00000"]}}\n' * 3
        steps = SETUP + [{"seed_file": {"name": "moves-2026-11.jsonl", "content": old}}] + submit(req([{"op": "archive", "ids": ids(2)}]))
        out = gs(steps, messages=inbox_msgs(2), constants=self.K)
        self.assertEqual(out["results"][-1], "done")
        self.assertNotIn("errors_history", result(out))
        self.assertEqual(len(move_logs(out)), 2)
        self.assertEqual(out["files"]["moves-2026-11.jsonl"]["content"], old)

    def test_rerun_does_not_duplicate_a_batch_log(self):
        out = gs(SETUP + submit(req([{"op": "archive", "ids": ids(1)}])) + [{"call": "logMove_", "args": [
            {"ctx": {"drive_ops": 0}, "folder": "d3"}, "req-test-0001", 0, 0, {"op": "archive"}, ids(1)]}], messages=inbox_msgs(1))
        self.assertEqual(len(move_logs(out)), 1)

    def test_readtext_recovers_body_from_http_200_throw(self):
        body = '{"a":1}\n{"b":2}\n'
        steps = SETUP + [{"seed_file": {"name": "x.jsonl", "content": body}},
                         {"call": "readText_", "args": [{"id": "f4"}, {"drive_ops": 0}]}]
        out = gs(steps)
        self.assertEqual(out["results"][-1], body)

    def test_readtext_json_object_and_non_200_error(self):
        steps = SETUP + [{"seed_file": {"name": "x.json", "content": '{"b": 2}'}},
                         {"call": "readText_", "args": [{"id": "f4"}, {"drive_ops": 0}]},
                         {"call": "readText_", "args": [{"id": "nope"}, {"drive_ops": 0}]}]
        out = gs(steps)
        self.assertEqual(json.loads(out["results"][-2]), {"b": 2})
        self.assertIn("THROW", out["results"][-1])
        self.assertIn("404", out["results"][-1])


if __name__ == "__main__":
    unittest.main()

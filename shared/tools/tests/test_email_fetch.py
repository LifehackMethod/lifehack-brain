#!/usr/bin/env python3
"""Standalone tests for shared/tools/email_fetch.py (6.1): oldest-first capped fetch + attachments.
Run:  python3 shared/tools/tests/test_email_fetch.py     (no network: a fake `gws` via LIFEHACK_GWS_BIN, throwaway dirs)."""
import base64, json, os, shutil, stat, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import email_fetch as ef  # noqa: E402

STUB = r'''#!/usr/bin/env python3
import json, os, sys
d = os.environ["FAKE_GMAIL"]
a = sys.argv[1:]
params = json.loads(a[a.index("--params") + 1]) if "--params" in a else {}
open(os.path.join(d, "calls.log"), "a").write(" ".join(a[2:5]) + " " + json.dumps(params, sort_keys=True) + "\n")
def load(n): return json.load(open(os.path.join(d, n)))
op = a[2:4]
if a[2] == "getProfile": print("{}")
elif op == ["labels", "list"]: print(json.dumps(load("labels.json")))
elif op == ["threads", "list"]:
    ids = load("threads.json")            # NEWEST-FIRST, like Gmail
    q = params.get("q", "")
    after = int(q.split("after:")[1].split()[0]) * 1000 if "after:" in q else 0
    keep = [i for i in ids if load("thread-%s.json" % i)["messages"][-1]["internalDate"].isdigit()
            and int(load("thread-%s.json" % i)["messages"][-1]["internalDate"]) > after]
    n = int(params.get("maxResults", 100)); off = int(params.get("pageToken", 0))
    page = keep[off: off + n]
    r = {"threads": [{"id": i} for i in page]}
    if off + n < len(keep): r["nextPageToken"] = str(off + n)       # like Gmail: a token while more remain
    print(json.dumps(r))
elif op == ["threads", "get"]: print(json.dumps(load("thread-%s.json" % params["id"])))
elif op == ["messages", "get"]: print(json.dumps(load("msg-%s.json" % params["id"])))
elif a[2:5] == ["messages", "attachments", "get"]: print(json.dumps(load("att-%s.json" % params["id"])))
else: sys.exit(1)
'''
B0 = 1_793_000_000_000


def b64(b):
    return base64.urlsafe_b64encode(b).decode()


def plain_msg(tid, n, labels=("Label_9",)):
    return {"id": f"m{n}", "threadId": tid, "internalDate": str(B0 + n * 60_000), "labelIds": list(labels),
            "payload": {"mimeType": "text/plain", "headers": [{"name": "Subject", "value": f"s{n}"}],
                        "body": {"data": b64(f"Plain note {n}: lunch is at noon.".encode())}}}


PDF = b"%PDF-1.4 fake bytes \x00\x01\xff"


def pdf_msg():
    return {"id": "mp", "threadId": "tp", "internalDate": str(B0), "labelIds": ["Label_9"],
            "payload": {"mimeType": "multipart/mixed", "headers": [{"name": "Subject", "value": "Water Bill"}], "parts": [
                {"mimeType": "text/plain", "body": {"data": b64(b"Your bill is attached.")}},
                {"mimeType": "application/pdf", "filename": "inv.pdf", "body": {"attachmentId": "ATT1", "size": len(PDF)}}]}}


class Base(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="ef-test.")
        self.gm = os.path.join(self.d, "gmail"); os.makedirs(self.gm)
        stub = os.path.join(self.d, "gws"); open(stub, "w").write(STUB); os.chmod(stub, 0o755)
        self.saved = dict(os.environ)
        os.environ.update(FAKE_GMAIL=self.gm, LIFEHACK_GWS_BIN=stub, LIFEHACK_LAST_SEEN_DIR=os.path.join(self.d, "seen"),
                          SENTINEL_PAUSE_FILE=os.path.join(self.d, "paused"), SENTINEL_LOG=os.path.join(self.d, "s/e.jsonl"),
                          SENTINEL_STATUS=os.path.join(self.d, "s/s.json"), SENTINEL_ACKED_FP=os.path.join(self.d, "s/a.json"),
                          SENTINEL_QUARANTINE_DISABLE="1", LIFEHACK_ROOT=os.path.join(self.d, "brain"), EMAIL_SERVICE_READ="")
        os.environ.pop("JOB_RUN_PENDING_LIST", None)
        self.w("labels.json", {"labels": [{"id": "Label_9", "name": "t-label"}]})

    def tearDown(self):
        os.environ.clear(); os.environ.update(self.saved)
        shutil.rmtree(self.d, ignore_errors=True)

    def w(self, name, obj):
        with open(os.path.join(self.gm, name), "w") as fh:
            json.dump(obj, fh)

    def mailbox(self, n):   # n single-message threads t1..tn; listed NEWEST-FIRST
        for i in range(1, n + 1):
            self.w(f"thread-t{i}.json", {"id": f"t{i}", "messages": [plain_msg(f"t{i}", i)]})
        self.w("threads.json", [f"t{i}" for i in range(n, 0, -1)])

    def promote(self, consumer):
        p = ef.pending_path(consumer)
        self.assertTrue(os.path.exists(p), "no pending bookmark written")
        pend = open(p).read().strip()
        self.assertTrue(ef.promote_pending(p))
        return pend


class CappedOldestFirst(Base):
    def test_seven_messages_cap_three_nothing_skipped_or_duplicated(self):
        self.mailbox(7)
        ef.write_last_seen("c", B0 - 1000, "seed")                    # a bookmark older than all 7
        got = []
        r1 = ef.fetch("c", label="t-label", query="", cap=3)
        self.assertEqual([m["message_id"] for m in r1["messages"]], ["m1", "m2", "m3"])
        self.assertTrue(r1["capped"]); self.assertEqual(r1["remaining"], 4)
        self.assertEqual(self.promote("c"), f"{B0 + 3 * 60_000} m3")   # pending = the 3rd (newest of the 3), not m7
        r2 = ef.fetch("c", label="t-label", query="", cap=3)
        self.assertEqual([m["message_id"] for m in r2["messages"]], ["m4", "m5", "m6"])
        self.assertEqual(self.promote("c"), f"{B0 + 6 * 60_000} m6")
        r3 = ef.fetch("c", label="t-label", query="", cap=3)
        self.assertEqual([m["message_id"] for m in r3["messages"]], ["m7"])
        self.assertFalse(r3["capped"])
        self.promote("c")
        got = [m["message_id"] for r in (r1, r2, r3) for m in r["messages"]]
        self.assertEqual(got, [f"m{i}" for i in range(1, 8)])
        self.assertEqual(ef.fetch("c", label="t-label", query="", cap=3)["count"], 0)

    def test_stderr_names_the_cap(self):
        import io, contextlib
        self.mailbox(5); ef.write_last_seen("c", B0 - 1000)
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            ef.fetch("c", label="t-label", query="", cap=2)
        self.assertIn("capped=1 remaining=3", buf.getvalue())

    def test_cold_start_never_exceeds_cap_and_takes_newest(self):
        self.mailbox(7)
        r = ef.fetch("fresh", label="t-label", query="", cap=3)
        self.assertEqual(r["count"], 3)
        self.assertEqual([m["message_id"] for m in r["messages"]], ["m5", "m6", "m7"])   # newest 3, delivered oldest-first
        self.assertEqual(open(ef.pending_path("fresh")).read().split()[1], "m7")

    def test_peek_writes_nothing(self):
        self.mailbox(4); ef.write_last_seen("c", B0 - 1000)
        ef.fetch("c", label="t-label", query="", cap=2, mark_seen=False)
        self.assertFalse(os.path.exists(ef.pending_path("c")))

    def test_over_max_list_fails_loudly(self):
        self.mailbox(3); ef.write_last_seen("c", B0 - 1000)
        ef.MAX_LIST, old = 2, ef.MAX_LIST
        try:
            with self.assertRaises(ef.FetchError) as cm:
                ef.fetch("c", label="t-label", query="", cap=1)
            self.assertIn("more than 2 threads", str(cm.exception))
        finally:
            ef.MAX_LIST = old


class Attachments(Base):
    def setUp(self):
        super().setUp()
        self.w("thread-tp.json", {"id": "tp", "messages": [pdf_msg()]})
        self.w("threads.json", ["tp"])
        self.w("msg-mp.json", pdf_msg())
        self.w("att-ATT1.json", {"data": b64(PDF), "size": len(PDF)})
        self.out = os.path.join(self.d, "o", "inv.pdf")

    def test_metadata_on_each_message(self):
        m = ef.fetch("tsm", label="t-label", query="", cap=3, mark_seen=False)["messages"][0]
        self.assertEqual(m["attachments"], [{"attachment_id": "ATT1", "filename": "inv.pdf", "mime_type": "application/pdf", "size": len(PDF)}])

    def test_download_writes_the_bytes(self):
        r = ef.get_attachment("mp", "ATT1", self.out, label="t-label")
        self.assertEqual(open(self.out, "rb").read(), PDF); self.assertEqual(r["size"], len(PDF))

    def test_download_without_label_uses_primary_unit(self):
        ef.get_attachment("mp", "ATT1", self.out)
        self.assertEqual(open(self.out, "rb").read(), PDF)

    def test_paused_source_refuses(self):
        open(os.environ["SENTINEL_PAUSE_FILE"], "w").write("email:t-label\n")
        with self.assertRaises(ef.Paused):
            ef.get_attachment("mp", "ATT1", self.out, label="t-label")
        self.assertFalse(os.path.exists(self.out))
        calls = os.path.join(self.gm, "calls.log")
        self.assertFalse(os.path.exists(calls) and "attachments" in open(calls).read(), "a paused source still hit Gmail for the bytes")

    def test_paused_primary_refuses_without_label(self):
        open(os.environ["SENTINEL_PAUSE_FILE"], "w").write("email:primary\n")
        with self.assertRaises(ef.Paused):
            ef.get_attachment("mp", "ATT1", self.out)

    def test_wrong_label_refuses(self):
        self.w("labels.json", {"labels": [{"id": "Label_9", "name": "t-label"}, {"id": "Label_5", "name": "other"}]})
        with self.assertRaises(ef.FetchError):
            ef.get_attachment("mp", "ATT1", self.out, label="other")

    def test_disabled_refuses(self):
        os.environ["EMAIL_SERVICE_READ"] = "off"
        with self.assertRaises(ef.Disabled):
            ef.get_attachment("mp", "ATT1", self.out)

    def test_cli(self):
        self.assertEqual(ef.main(["--get-attachment", "mp", "ATT1", "--out", self.out, "--label", "t-label"]), 0)
        self.assertEqual(open(self.out, "rb").read(), PDF)
        open(os.environ["SENTINEL_PAUSE_FILE"], "w").write("email:t-label\n")
        os.remove(self.out)
        self.assertEqual(ef.main(["--get-attachment", "mp", "ATT1", "--out", self.out, "--label", "t-label"]), 75)
        self.assertFalse(os.path.exists(self.out))


if __name__ == "__main__":
    unittest.main(verbosity=2)

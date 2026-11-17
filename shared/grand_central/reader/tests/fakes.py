"""Fakes for the step-2 tests: a fake Gmail and a fake scanner. No network, no real mail, no model.

FakeGmail implements reader.fetch.GmailSource and counts every call, so a test can say "nothing was
downloaded". FakeScanner is a deterministic stub (never a real model): it declares itself
tool-less, answers from keywords in the prompt, and can be made unable to run.
"""
import base64
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from reader import fetch  # noqa: E402

LABEL_ID, LABEL_NAME = "Label_7", "Example-Label"
DAY_MS = 86400000
NOW_MS = 1790000000000     # a fixed "now" so thread states are deterministic


def b64(s):
    return base64.urlsafe_b64encode(s.encode()).decode().rstrip("=")


def hid(prefix, n):
    return "%s%06x" % (prefix, n)   # hex ids: 'a' for messages, 'b' for threads


def attribution(prev_who="Bob"):
    return "On Mon, Jan 12, 2026 at 3:45 PM %s <bob@example.invalid> wrote:" % prev_who


def reply_body(new_text, quoted_text=None, signature=True):
    parts = [new_text, ""]
    if quoted_text:
        parts += [attribution(), ""] + ["> " + l for l in quoted_text.splitlines()] + [""]
    if signature:
        parts += ["-- ", "SIGLINE-Bob Example", "SIGLINE-CEO of Nothing"]
    return "\n".join(parts)


class FakeGmail(fetch.GmailSource):
    def __init__(self):
        self.threads = {}      # tid -> {"version": int, "messages": [msg dicts]}
        self.label_of = {}     # tid -> label id
        self.down = False
        self.fail_get = set()
        self.label_table = {LABEL_ID: LABEL_NAME}      # label id -> name (a test may add more)
        self.reset_counts()

    def reset_counts(self):
        self.calls = {"labels": 0, "list_threads": 0, "thread_messages": [], "get_message": []}
        self.queries = []

    # -- building a mailbox
    def add(self, tid, mid, body, t_ms, frm="Bob <bob@example.invalid>", subject="Plans",
            labels=("INBOX",), label_id=LABEL_ID, read_label=True, extra_label_ids=()):
        th = self.threads.setdefault(tid, {"version": 0, "messages": []})
        th["version"] += 1
        self.label_of[tid] = label_id
        th["messages"].append({
            "id": mid, "threadId": tid, "internalDate": str(int(t_ms)), "labelIds": list(labels) + ([label_id] if read_label else []) + list(extra_label_ids),
            "payload": {"mimeType": "text/plain",
                        "headers": [{"name": "From", "value": frm}, {"name": "Subject", "value": subject},
                                    {"name": "Date", "value": "Mon, 12 Jan 2026 15:45:00 +0000"},
                                    {"name": "To", "value": "person-one@example.invalid"}],
                        "body": {"data": b64(body)}}})

    # -- GmailSource
    def _check(self):
        if self.down:
            raise fetch.GmailUnavailable("gws_exit_4")

    def labels(self):
        self._check()
        self.calls["labels"] += 1
        return [{"id": "INBOX", "name": "INBOX"}] + [{"id": i, "name": n} for i, n in self.label_table.items()]

    def list_threads(self, label_id, query, max_threads):
        self._check()
        self.calls["list_threads"] += 1
        self.queries.append(query)
        return [{"id": t, "history_id": str(v["version"])} for t, v in sorted(self.threads.items())
                if self.label_of.get(t) == label_id][:max_threads]

    def thread_messages(self, thread_id):
        self._check()
        self.calls["thread_messages"].append(thread_id)
        return [{"id": m["id"], "internal_ms": int(m["internalDate"]), "labels": m["labelIds"]}
                for m in self.threads[thread_id]["messages"]]

    def get_message(self, message_id):
        self._check()
        self.calls["get_message"].append(message_id)
        if message_id in self.fail_get:
            raise fetch.GmailUnavailable("gws_exit_1")
        for th in self.threads.values():
            for m in th["messages"]:
                if m["id"] == message_id:
                    return json.loads(json.dumps(m))
        raise fetch.GmailUnavailable("gws_exit_1")


SAFE = {"verdict": "safe", "triage": {
    "needs_me": "cant_tell", "do_or_know": "cant_tell", "how_soon": "cant_tell", "deadline": None,
    "area": "cant_tell", "obs": {"deadline_stated": "no", "direct_ask": "no",
                                 "reply_expected": "no", "money_involved": "no"}}}


class FakeScanner(object):
    """Deterministic stub. 'PLANTED-ATTACK' anywhere in the prompt -> attack. 'GARBLE-ME' -> an answer
    that fails validation. down=True -> cannot run (no network / no token)."""
    tool_less = True

    def __init__(self):
        self.down = False
        self.calls = 0
        self.prompts = []

    def scan(self, prompt):
        self.calls += 1
        self.prompts.append(prompt)
        if self.down:
            return None, "no_token"
        if "PLANTED-ATTACK" in prompt:
            return json.dumps({"verdict": "attack", "triage": None}), None
        if "TIMEOUT-ME" in prompt:
            return None, "timeout"
        if "BOOM" in prompt:
            raise RuntimeError("the model blew up")
        if "SUSPICIOUS-ONE" in prompt:
            return json.dumps({"verdict": "suspicious", "triage": None}), None
        if "NO-OUTCOME" in prompt:
            return json.dumps({"verdict": "no_outcome", "triage": None}), None
        if "DUPKEY" in prompt:
            return '{"verdict": "attack", "triage": null, "verdict": "safe"}', None
        if "GARBLE-ME" in prompt:
            return "Sure! This email looks fine to me.", None
        doc = json.loads(json.dumps(SAFE))
        if "PLEASE-REPLY" in prompt:
            doc["triage"]["needs_me"] = "yes"
            doc["triage"]["obs"]["direct_ask"] = "yes"
        return json.dumps(doc), None


class ToolfulScanner(FakeScanner):
    tool_less = False

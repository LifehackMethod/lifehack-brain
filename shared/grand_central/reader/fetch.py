"""reader/fetch.py - the mailroom's Gmail intake: only new messages, full email always.

Runs only as the mailroom account, through ITS OWN root-owned gws copy. Successor of
the earlier mailroom prototype's gmail_gws.py (its safe-run pieces are copied here, because the mailroom may only
import its own folder). Plan B1 stage 2 and the V1 efficiencies (change log, 2026-11-14 IM-2):

  1. thread-level skip: the thread list carries each thread's history id. If it equals the stored
     one nothing is asked about that thread at all (zero calls). V1's biggest saving.
  2. only unseen messages are downloaded: for a changed thread we ask for ids only (format
     "minimal", the preview text Gmail puts in it is dropped on arrival and never used), then
     fetch just the message ids the register has never seen.
  3. a date bound sits inside the Gmail query ("after:YYYY/MM/DD"), not after the fetch.
  4. thread states: active / completed / cold, recorded in the register (see thread_state).
  5. the register is the cross-run cache: no message id is ever downloaded or scanned twice.
The preview shortcut (step 1d) is NOT built: a message is always fetched in full.

The Gmail side is an INTERFACE (GmailSource) so tests inject a fake Gmail. GwsGmail is the real
one: read-only methods only (labels.list, threads.list, threads.get, messages.get), mail text only
ever arrives on the child's stdout pipe, only ids/label ids/a date query ever go on the command
line (argv is visible to every account). It refuses to start without the gws binary and the
mailroom's own sign-in file; there is no fall back to any broader key.
Python 3.9 compatible.
"""
import base64
import datetime
import html.parser
import json
import os
import re
import subprocess

GMAIL_ID_RE = re.compile(r"^[0-9a-f]{6,32}$")
LABEL_ID_RE = re.compile(r"^[A-Za-z0-9_]{1,64}$")
TIMEOUT_S = 120
ACTIVE_DAYS = 14        # newest message younger than this -> active
COMPLETED_AFTER_DAYS = 3   # last message is the owner's own, and this old -> completed (waiting on others)


class GwsError(Exception):
    def __init__(self, code, rc=None):
        Exception.__init__(self, code)
        self.code = code   # closed: gws_missing, gws_timeout, gws_exit_<n>, gws_bad_json, no_signin
        self.rc = rc


class GmailUnavailable(Exception):
    """Any failure to talk to Gmail. Carries a closed code only, never text."""
    def __init__(self, code):
        Exception.__init__(self, code)
        self.code = code


# ---------------------------------------------------------------- the interface

class GmailSource(object):
    """What the intake needs from Gmail. A test passes its own implementation."""

    def labels(self):
        """-> [{"id": ..., "name": ...}]"""
        raise NotImplementedError

    def list_threads(self, label_id, query, max_threads):
        """-> [{"id": thread_id, "history_id": str}] newest first. `query` is a Gmail query."""
        raise NotImplementedError

    def thread_messages(self, thread_id):
        """Ids only, no text: -> [{"id": message_id, "internal_ms": int, "labels": [..]}]"""
        raise NotImplementedError

    def get_message(self, message_id):
        """The one full download: -> the Gmail message resource (format=full)."""
        raise NotImplementedError


# ---------------------------------------------------------------- the real one (gws)

def gws_env(home, config_dir):
    return {"HOME": home, "PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "LANG": "en_US.UTF-8",
            "GOOGLE_WORKSPACE_CLI_CONFIG_DIR": config_dir,
            "GOOGLE_WORKSPACE_CLI_KEYRING_BACKEND": "file", "NO_COLOR": "1"}


def run_gws(gws, home, config_dir, args, timeout=TIMEOUT_S):
    if not gws or not os.path.isfile(gws):
        raise GwsError("gws_missing")
    work = os.path.join(home, "work")
    try:
        p = subprocess.run([gws] + list(args), cwd=work if os.path.isdir(work) else home,
                           env=gws_env(home, config_dir), stdin=subprocess.DEVNULL,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise GwsError("gws_timeout")
    if p.returncode != 0:
        raise GwsError("gws_exit_%d" % p.returncode, p.returncode)   # stderr text is never kept
    text = p.stdout.decode("utf-8", "replace").strip()
    try:
        return json.loads(text)
    except ValueError:
        raise GwsError("gws_bad_json")


def _params(d):
    return ["--params", json.dumps(d, separators=(",", ":"), sort_keys=True)]


class GwsGmail(GmailSource):
    def __init__(self, gws, home, config_dir):
        # Refuse to start without the mailroom's own read key: no fall back to any other login.
        if not gws or not os.path.isfile(gws):
            raise GwsError("gws_missing")
        if not os.path.isfile(os.path.join(config_dir, "credentials.enc")):
            raise GwsError("no_signin")
        self.gws, self.home, self.config_dir = gws, home, config_dir

    def _run(self, args):
        try:
            return run_gws(self.gws, self.home, self.config_dir, args)
        except GwsError as e:
            raise GmailUnavailable(e.code)

    def labels(self):
        r = self._run(["gmail", "users", "labels", "list", "--params", '{"userId":"me"}'])
        out = []
        for lab in (r.get("labels") or []) if isinstance(r, dict) else []:
            if isinstance(lab, dict) and isinstance(lab.get("name"), str) \
                    and isinstance(lab.get("id"), str) and LABEL_ID_RE.match(lab["id"]):
                out.append({"id": lab["id"], "name": lab["name"]})
        return out

    def list_threads(self, label_id, query, max_threads):
        out, token = [], None
        while len(out) < max_threads:
            p = {"userId": "me", "labelIds": [label_id], "q": query,
                 "maxResults": min(100, max_threads - len(out))}
            if token:
                p["pageToken"] = token
            r = self._run(["gmail", "users", "threads", "list"] + _params(p))
            if not isinstance(r, dict):
                raise GmailUnavailable("gws_bad_json")
            for t in r.get("threads") or []:
                tid = t.get("id") if isinstance(t, dict) else None
                if isinstance(tid, str) and GMAIL_ID_RE.match(tid):
                    out.append({"id": tid, "history_id": str(t.get("historyId", ""))})
            token = r.get("nextPageToken")
            if not token:
                break
        return out[:max_threads]

    def thread_messages(self, thread_id):
        if not GMAIL_ID_RE.match(thread_id):
            raise GmailUnavailable("gws_bad_json")
        r = self._run(["gmail", "users", "threads", "get"] +
                      _params({"userId": "me", "id": thread_id, "format": "minimal"}))
        out = []
        for m in (r.get("messages") or []) if isinstance(r, dict) else []:
            mid = m.get("id") if isinstance(m, dict) else None
            if isinstance(mid, str) and GMAIL_ID_RE.match(mid):
                try:
                    ms = int(m.get("internalDate") or 0)
                except (TypeError, ValueError):
                    ms = 0
                out.append({"id": mid, "internal_ms": ms,
                            "labels": [l for l in (m.get("labelIds") or []) if isinstance(l, str)]})
        return out    # the "snippet" Gmail sends in minimal format is dropped here, never kept

    def get_message(self, message_id):
        if not GMAIL_ID_RE.match(message_id):
            raise GmailUnavailable("gws_bad_json")
        r = self._run(["gmail", "users", "messages", "get"] +
                      _params({"userId": "me", "id": message_id, "format": "full"}))
        if not isinstance(r, dict):
            raise GmailUnavailable("gws_bad_json")
        return r


# ---------------------------------------------------------------- MIME -> plain text

HTML_CAP_CHARS = 200000      # more than this of HTML is not converted: "not yet read in full"
_BLOCK_TAGS = ("br", "p", "div", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6", "table", "ul", "ol")
_HIDE_TAGS = ("script", "style", "head", "title", "noscript")
_TAGNAME = re.compile(r"/?\s*([A-Za-z][A-Za-z0-9]*)")


def _collapse_blank_lines(text):
    """Trailing blanks off every line, and any run of blank lines becomes one. Single pass (the regex
    this replaces was quadratic on long runs of spaces)."""
    out, blank = [], False
    for line in text.split("\n"):
        line = line.rstrip()
        if not line:
            if not blank and out:
                out.append("")
            blank = True
            continue
        blank = False
        out.append(line)
    return "\n".join(out)


def html_to_text(s):
    """-> (text, partial). A hand-written scanner that is LINEAR in the input (the standard library
    parser is quadratic on hostile input on Apple's python 3.9): every position is looked at a
    bounded number of times. Input over HTML_CAP_CHARS is cut and reported partial. Hidden-by-markup
    text is dropped only for script/style/head/title/noscript blocks and comments; when a tag or
    block is not terminated, the rest is KEPT as text (when unsure, keep). Never raises."""
    partial = len(s) > HTML_CAP_CHARS
    s = s[:HTML_CAP_CHARS]
    low = s.lower()
    n, i, gt = len(s), 0, -1
    out = []
    while i < n:
        j = s.find("<", i)
        if j < 0:
            out.append(s[i:])
            break
        out.append(s[i:j])
        if low.startswith("<!--", j):
            k = s.find("-->", j + 4)
            i = n if k < 0 else k + 3
            continue
        if gt < j:
            gt = s.find(">", j)
            if gt < 0:
                gt = n + 1
        if gt > n:                       # no '>' anywhere after: the rest is text
            out.append(s[j:])
            break
        nxt = s.find("<", j + 1, gt)
        m = _TAGNAME.match(s, j + 1, min(gt, j + 40)) if nxt < 0 else None
        if m is None and not (nxt < 0 and s.startswith(("!", "/"), j + 1)):
            out.append("<")              # not a tag ("a < b", or '<' inside another '<'): plain text
            i = j + 1
            continue
        name = m.group(1).lower() if m else ""
        i = gt + 1
        if m and not s.startswith("/", j + 1) and name in _HIDE_TAGS:
            close = low.find("</" + name, i)
            if close >= 0:
                end = s.find(">", close)
                i = n if end < 0 else end + 1
            # no closing tag: keep what follows
        elif name in _BLOCK_TAGS:
            out.append("\n")
    return _collapse_blank_lines(html.unescape("".join(out))), partial


def _b64(data):
    if not isinstance(data, str):
        return ""
    try:
        return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", "replace")
    except (ValueError, TypeError):
        return ""


def _walk(part, plain, htmls, depth=0):
    if not isinstance(part, dict) or depth > 20:
        return
    mt = (part.get("mimeType") or "").lower()
    body = part.get("body") or {}
    if mt == "text/plain" and body.get("data") and not part.get("filename"):
        plain.append(_b64(body["data"]))
    elif mt == "text/html" and body.get("data") and not part.get("filename"):
        htmls.append(_b64(body["data"]))
    for sub in part.get("parts") or []:
        _walk(sub, plain, htmls, depth + 1)


def _header(headers, name):
    for h in headers or []:
        if isinstance(h, dict) and str(h.get("name", "")).lower() == name:
            return str(h.get("value", ""))
    return ""


_ADDR_RE = re.compile(r"^\s*\"?([^\"<]*?)\"?\s*<([^>]+)>\s*$")


def split_from(v):
    m = _ADDR_RE.match(v or "")
    if m:
        return m.group(1).strip(), m.group(2).strip().lower()
    return "", (v or "").strip().lower()


def message_to_email(msg, max_body_chars=200000):
    """Gmail message (format=full) -> the dict the scan and the flattener see. Attachments are
    never read. Text/plain wins; HTML is converted only when there is no plain part."""
    payload = msg.get("payload") or {}
    headers = payload.get("headers") or []
    plain, htmls = [], []
    _walk(payload, plain, htmls)
    body = "\n".join(t for t in plain if t.strip())
    html_partial = False
    if not body:
        body, html_partial = html_to_text("\n".join(htmls))
    labels = [l for l in (msg.get("labelIds") or []) if isinstance(l, str)]
    name, addr = split_from(_header(headers, "from"))
    try:
        internal = int(msg.get("internalDate") or 0)
    except (TypeError, ValueError):
        internal = 0
    return {"message_id": msg.get("id", ""), "thread_id": msg.get("threadId", ""),
            "internal_ms": internal, "from_me": "yes" if "SENT" in labels else "no",
            "from_name": name, "from_addr": addr, "to_addrs": _header(headers, "to")[:500],
            "subject": _header(headers, "subject")[:500], "date": _header(headers, "date")[:100],
            "labels": ",".join(labels),
            "truncated": "yes" if (html_partial or len(body) > max_body_chars) else "no",
            "body": body[:max_body_chars]}


# ---------------------------------------------------------------- query, states

def query_text(days, today=None):
    """The date bound goes INTO the Gmail query (Gmail's after: is a date in the account's zone)."""
    today = today or datetime.date.today()
    since = today - datetime.timedelta(days=int(days))
    return "after:%s" % since.strftime("%Y/%m/%d")


def thread_state(newest_ms, newest_from_me, now_ms, active_days=ACTIVE_DAYS,
                 completed_days=COMPLETED_AFTER_DAYS):
    """active: the newest message is recent. completed: the last word was the owner's and it is a few
    days old (the ball is in someone else's court). cold: older than the active window."""
    age_days = (now_ms - newest_ms) / 86400000.0 if newest_ms else 10 ** 6
    if age_days > active_days:
        return "cold"
    if newest_from_me and age_days >= completed_days:
        return "completed"
    return "active"


def resolve_read_labels(gmail, names):
    """-> ([(name, label_id)], missing_names). Exact, case-insensitive; a missing label is
    reported, never guessed."""
    by_name = dict((l["name"].lower(), (l["name"], l["id"])) for l in gmail.labels())
    found, missing = [], []
    for n in names:
        hit = by_name.get(str(n).lower())
        if hit:
            found.append(hit)
        else:
            missing.append(str(n))
    return found, missing


# ---------------------------------------------------------------- discovery (what is new?)

EXCLUDED_LABELS = ("DRAFT", "SPAM", "TRASH")   # never read, even inside a read-label thread
HARD_LIST = 5000          # most thread ids listed per source and pass (ids only: cheap)


def excluded(labels, extra=()):
    """True if the message carries DRAFT/SPAM/TRASH or any label id in `extra` (his exclude_labels)."""
    return bool(set(labels or []) & (set(EXCLUDED_LABELS) | set(extra)))


def discover(gmail, register, read_labels, days, max_threads_per_source, now_ms, today=None,
             exclude_ids=()):
    """List threads in each read label (date-bounded query). For every changed thread (history id
    differs from the register's), up to max_threads_per_source per label and pass, ask for message ids
    only; every id the register has never seen gets a row at once (status 'held'), so no id can be
    lost between here and the verdict. Messages labelled DRAFT, SPAM or TRASH are registered as held
    with reason 'excluded_label', and messages without any read label as 'not_in_read_label'; neither is ever downloaded. Changed threads beyond the cap are NOT silently
    dropped: each is recorded as 'not_yet_fetched' (counted here and by Register.account()) and goes
    first next pass. Returns a summary dict (counts, no text).

    Thread unchanged (same history id) -> no call about it at all."""
    q = query_text(days, today)
    read_ids = set(lid for _n, lid in read_labels)
    stats = {"query": q, "threads_listed": 0, "threads_skipped": 0, "threads_checked": 0,
             "new_ids": 0, "threads_not_yet_fetched": 0, "capped_labels": []}
    seen_threads = set()
    for name, lid in read_labels:
        done = 0
        listed = gmail.list_threads(lid, q, HARD_LIST)
        # threads that were left over last time go first
        listed.sort(key=lambda t: 0 if register.thread_state(t["id"]) == "not_yet_fetched" else 1)
        for t in listed:
            tid, hist = t["id"], t.get("history_id", "")
            if tid in seen_threads:
                continue
            seen_threads.add(tid)
            stats["threads_listed"] += 1
            if hist and register.thread_history(tid) == hist:
                stats["threads_skipped"] += 1
                continue
            if done >= max_threads_per_source:
                register.set_thread(tid, None, None, "not_yet_fetched", now_ms)
                stats["threads_not_yet_fetched"] += 1
                if name not in stats["capped_labels"]:
                    stats["capped_labels"].append(name)
                continue
            done += 1
            stats["threads_checked"] += 1
            msgs = gmail.thread_messages(tid)
            for m in msgs:
                # The read label is the permission, per MESSAGE: a reply in a read-label thread that
                # itself carries no read label is never fetched.
                mlabels = m.get("labels") or []
                reason = ("excluded_label" if excluded(mlabels, exclude_ids) else
                          "not_in_read_label" if not (set(mlabels) & read_ids) else "discovered")
                if not register.has_message(m["id"]):
                    register.add_message(m["id"], tid, name, now_ms, reason=reason)
                    stats["new_ids"] += 1
                elif reason == "discovered":
                    register.release_excluded(m["id"])
            if msgs:
                newest = max(msgs, key=lambda m: m["internal_ms"])
                state = thread_state(newest["internal_ms"], "SENT" in newest["labels"], now_ms)
                register.set_thread(tid, hist, newest["id"], state, now_ms)
    return stats

#!/usr/bin/env python3
"""email_fetch.py -- THE shared email fetch: the only sanctioned Gmail read (self-monitoring plan 5.4, 2026-10-27).

WHY ONE COPY. Everything ingested goes through the security system (plan B.4). Gmail used to be read by a dozen
scripts, each with its own filter, its own cap, its own bookmark and (mostly) no gate. This file is the one place that
holds the raw `gws gmail` call and that decides, for EVERY message it returns:
  1. the label is not PAUSED (a paused label is refused, exit 75 "paused: <label>");
  2. it sets NO read policy of its own (Enver 2026-10-28: read policy is per skill, set at that skill's gate). The
     CALLER passes every choice explicitly: the query (folders/category; '' = none), the cap, and the start point
     (--since bookmark | none). There are no silent defaults; a missing choice is an error. Order is Gmail's own
     (newest first); the fetch does not reorder. A capped read with a bookmark can therefore leave older mail
     behind -- that trade-off belongs to the calling skill;
  3. the caller's cap bounds the read;
  4. the body passes the ingest gate INSIDE this fetch -- sanitise + scan + the tool-less reader's judgment -- so a
     headless (cron) job is covered exactly like a session;
  5. a REAL-ATTACK verdict PAUSES the label and sends ONE critical push (via ingest_gate -> sentinel_response), and the
     run stops reading. A NONE / BENIGN verdict delivers normally. A message the scanner FLAGGED but the reader could
     not judge (verdict UNJUDGED: no token, retired model, timeout) is never delivered raw and never pauses: the WHOLE
     run is withheld (no output, bookmark not advanced) and the fetch fails LOUD, exit 3 "reader unavailable: <n>
     flagged message(s) withheld -- <reason>" (5.4, 2026-10-28; this used to be silent, so the danger path never ran);
  6. a high-water bookmark is kept in ONE format, a per-consumer file `<consumer>-last-seen`, and it moves ONLY when the work is done
     (5.9(f)): fetch() writes the new value to `<consumer>-last-seen.pending`; job-run.sh promotes it on rc 0 AND a passing row check
     and deletes it on failure. A peek (mark_seen=False / --no-mark) writes nothing. A corrupt bookmark is refused and named (5.9(e)).

INTERFACE (library):
  fetch(consumer, *, label, query, cap, since_last_seen, mark_seen) -> dict   (every choice explicit, no defaults)
        raises Paused(unit) / Disabled / FetchError
  list_threads(params) / get_thread(thread_id, fmt) / labels_list() / preflight()   -- the raw calls, (data, err) tuples
  check_paused(unit)        -- raises Paused
  report_attack(unit, body, item)  -- for a caller that ran its OWN judge (the store janitor): pause + one critical push
  read_last_seen(consumer) / write_last_seen(consumer, ms, msg_id)
INTERFACE (CLI):  python3 email_fetch.py --consumer NAME [--label L] --query Q --cap N --since bookmark|none [--no-mark]
                  [--out FILE] | --preflight
  query: required; `--query ''` = no query filter (a label-only read, e.g. a drill label).
  exit 0 ok | 75 paused / email read disabled | 2 Gmail unreachable (transient) | 3 reader down (flagged mail withheld) | 1 other.

THE UNIT THAT GETS PAUSED is the label (or "primary" when no label): pause-file line `email:<unit>` in
~/.config/lifehack/sentinel-paused-sources (sentinel_response.PAUSE_FILE, env SENTINEL_PAUSE_FILE). Only a person
removes the line. health_line.py reads the same file and prints `paused: <unit>`.

WHERE *-last-seen LIVES: ~/.config/lifehack/<consumer>-last-seen (env LIFEHACK_LAST_SEEN_DIR overrides the directory).
One line: `<newest internalDate in ms> <message id>`. It only moves forward, and only via promote_pending (see 6. above). A consumer opts out of filtering with
since_last_seen=False. The store janitor (email_summary_sync) is such a consumer: it dedups by newest-message-id itself
and keeps no bookmark file (a thread read once at the same newest id is skipped).
The bookmark is NOT advanced on a run that hit an attack.

EMAIL_SERVICE_READ is ON by default: unset/empty/1/all/on -> on. 0 / off / false / no / none -> the fetch refuses (75).

TEST SEAMS (all inert when unset): LIFEHACK_GWS_BIN (a stub gws), CLAUDE_BIN (a stub reader, see intake_reader.py),
SENTINEL_PAUSE_FILE / SENTINEL_LOG / SENTINEL_STATUS (sentinel_response), LIFEHACK_LAST_SEEN_DIR.
"""
import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile  # noqa: F401  (kept for callers that monkeypatch)
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
CODE_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
for _d in (os.path.join(CODE_ROOT, "shared", "gate"), os.path.join(CODE_ROOT, "system", "tools"), HERE):
    if _d not in sys.path:
        sys.path.insert(0, _d)

MAX_MSGS_PER_THREAD = 20
EXIT_PAUSED = 75
EXIT_TRANSIENT = 2
EXIT_READER_DOWN = 3


class Paused(Exception):
    """The label is paused (a REAL-ATTACK stopped it). str(e) is the unit name."""


class Disabled(Exception):
    """EMAIL_SERVICE_READ is explicitly off."""


class FetchError(Exception):
    """Gmail could not be read (transient) or the gate could not run."""


class ReaderDown(FetchError):
    """Flagged message(s) the tool-less reader could not judge: the run is withheld, loudly (exit 3)."""


# ─────────────────────────── switches, pause file, bookmark ───────────────────────────
def enabled():
    v = (os.environ.get("EMAIL_SERVICE_READ") or "").strip().lower()
    return v not in ("0", "off", "false", "no", "none")


def pause_file():
    return os.environ.get("SENTINEL_PAUSE_FILE") or os.path.expanduser("~/.config/lifehack/sentinel-paused-sources")


def paused_units():
    try:
        with open(pause_file(), encoding="utf-8", errors="replace") as fh:
            return {ln.strip()[len("email:"):] for ln in fh if ln.strip().startswith("email:")}
    except OSError:
        return set()


def check_paused(unit):
    if unit in paused_units():
        raise Paused(unit)


def last_seen_path(consumer):
    d = os.environ.get("LIFEHACK_LAST_SEEN_DIR") or os.path.expanduser("~/.config/lifehack")
    return os.path.join(d, f"{consumer}-last-seen")


class BookmarkCorrupt(Exception):
    """5.9(e): a *-last-seen file is PRESENT but unparseable or the wrong shape. Never 'no bookmark': that would re-read (or skip) a
    whole mailbox without saying so. A MISSING file is normal (first run) and is not this."""


def parse_bookmark(path, text):
    """(internalDate_ms, message_id) from the text of a bookmark file; raises BookmarkCorrupt naming `path`."""
    parts = text.split()
    if len(parts) not in (1, 2) or not parts[0].isdigit():
        raise BookmarkCorrupt(f"{path} should hold '<internalDate ms> [message id]' but holds {text.strip()[:60]!r}")
    return int(parts[0]), (parts[1] if len(parts) > 1 else "")


def read_last_seen(consumer):
    """(internalDate_ms, message_id); (0, '') when there is no bookmark yet. Raises BookmarkCorrupt if the file is there but bad."""
    p = last_seen_path(consumer)
    try:
        text = open(p, encoding="utf-8").read()
    except FileNotFoundError:
        return 0, ""
    except OSError as e:
        raise BookmarkCorrupt(f"{p} is unreadable ({e})")
    return parse_bookmark(p, text)


def pending_path(consumer):
    return last_seen_path(consumer) + ".pending"


def write_pending(consumer, ms, msg_id=""):
    """5.9(f): record the NEW high-water mark as <consumer>-last-seen.pending -- NOT in last-seen. The bookmark moves only when the work
    on this mail is DONE: job-run.sh promotes the pending file (promote_pending) on rc 0 AND a passing row check, and deletes it on any
    failure. Forward-only against the current bookmark; atomic. Under job-run.sh (JOB_RUN_PENDING_LIST set) the pending path is
    appended to that list so the wrapper knows which files this run owns. Returns True if a pending file was written."""
    if ms <= read_last_seen(consumer)[0]:
        return False
    p = pending_path(consumer)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(f"{int(ms)} {msg_id}\n")
    os.replace(tmp, p)
    lst = os.environ.get("JOB_RUN_PENDING_LIST")
    if lst:
        with open(lst, "a", encoding="utf-8") as fh:
            fh.write(p + "\n")
    return True


def promote_pending(path):
    """Called by job-run.sh ONLY after rc 0 AND a passing row check (python3 email_fetch.py --promote-pending FILE): validate the pending
    file, then move it over the bookmark (forward-only). Raises BookmarkCorrupt naming whichever file is bad. Returns True if the bookmark moved."""
    if not path.endswith(".pending"):
        raise BookmarkCorrupt(f"{path} is not a *-last-seen.pending file")
    try:
        text = open(path, encoding="utf-8").read()
    except OSError as e:
        raise BookmarkCorrupt(f"{path} is unreadable ({e})")
    ms, _ = parse_bookmark(path, text)
    bookmark = path[: -len(".pending")]
    cur = 0
    if os.path.exists(bookmark):
        cur = parse_bookmark(bookmark, open(bookmark, encoding="utf-8").read())[0]
    if ms <= cur:
        os.remove(path)
        return False
    os.replace(path, bookmark)
    return True


def write_last_seen(consumer, ms, msg_id=""):
    """Forward-only; atomic. Returns True if it moved. NOT called by fetch() any more (5.9(f)): only a caller that has FINISHED the work on
    the mail (or tooling that seeds a bookmark by hand) may move the bookmark directly; everything else writes the pending file."""
    if ms <= read_last_seen(consumer)[0]:
        return False
    p = last_seen_path(consumer)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(f"{int(ms)} {msg_id}\n")
    os.replace(tmp, p)
    return True


# ─────────────────────────── the raw gws calls (the ONLY ones) ───────────────────────────
def _gws():
    return os.environ.get("LIFEHACK_GWS_BIN") or shutil.which("gws") or "/opt/homebrew/bin/gws"


def _gws_env():
    """The Gmail key lives HERE, in the shared fetch (plan §B.4), never in a desk runner's environment.
    Same rule as system/tools/gws-auth.lib.sh: the isolated, keychain-free credentials file. Without
    this a headless run (cron/launchd) had no credentials at all: found by the 5.4 danger drill
    2026-10-28 ('Access denied. No credentials provided'). An already-exported caller env wins."""
    env = dict(os.environ)
    if env.get("GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE"):
        return env
    creds = env.get("LIFEHACK_GWS_CREDS_FILE") or os.path.expanduser("~/.config/lifehack/gws-credentials.json")
    if os.path.isfile(creds) and os.path.getsize(creds) > 0:
        env["GOOGLE_WORKSPACE_CLI_CONFIG_DIR"] = os.path.join(os.path.dirname(creds) or ".", "gws-cron")
        env["GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE"] = creds
        env["GOOGLE_WORKSPACE_CLI_KEYRING_BACKEND"] = "file"
    return env


def _call(path, params, timeout=30):
    try:
        r = subprocess.run([_gws(), "gmail", "users", *path, "--params", json.dumps(params)],
                           capture_output=True, text=True, timeout=timeout, env=_gws_env())
    except subprocess.TimeoutExpired:
        return None, "timeout"
    except Exception as e:  # noqa: BLE001
        return None, str(e)
    if r.returncode != 0:
        tail = [l for l in (r.stderr or "").splitlines() if l.strip()]
        return None, f"gws_error: {tail[-1] if tail else f'gws exit {r.returncode}'}"
    try:
        return json.loads(r.stdout), None
    except json.JSONDecodeError as e:
        return None, f"json_parse: {e}"


def preflight():
    """True when Google auth answers (getProfile)."""
    data, err = _call(["getProfile"], {"userId": "me"})
    return err is None


def labels_list():
    return _call(["labels", "list"], {"userId": "me"})


def list_threads(params):
    """threads.list with the caller's params (userId added). Returns (data, err)."""
    return _call(["threads", "list"], dict({"userId": "me"}, **params))


def get_thread(thread_id, fmt="metadata"):
    return _call(["threads", "get"], {"userId": "me", "id": thread_id, "format": fmt})


# ─────────────────────────── message body extraction ───────────────────────────
class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.out, self._skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.out.append(data)


def _decode(b64):
    try:
        return base64.urlsafe_b64decode(b64 + "=" * (-len(b64) % 4)).decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        return ""


def _walk(payload, mime):
    if (payload.get("mimeType") or "").lower() == mime and (payload.get("body") or {}).get("data"):
        yield _decode(payload["body"]["data"])
    for part in payload.get("parts") or []:
        yield from _walk(part, mime)


def message_text(msg):
    payload = msg.get("payload") or {}
    plain = "\n".join(t for t in _walk(payload, "text/plain") if t.strip())
    if plain.strip():
        return plain
    html = "\n".join(_walk(payload, "text/html"))
    p = _Text()
    try:
        p.feed(html)
    except Exception:  # noqa: BLE001
        pass
    return " ".join("".join(p.out).split())


def _headers(msg):
    return {h.get("name", ""): h.get("value", "") for h in (msg.get("payload") or {}).get("headers", [])}


# ─────────────────────────── the gate, inside the fetch ───────────────────────────
def _gate_modules():
    try:
        from ingest_gate import gate  # shared/gate
        from safe_input import scan_for_injection  # system/tools
    except Exception as e:  # noqa: BLE001
        raise FetchError(f"ingest gate unavailable ({e}) -- refusing to hand back UNGATED email")
    try:
        from intake_reader import run_intake_judge  # shared/tools
    except Exception:  # noqa: BLE001
        run_intake_judge = None   # no reader: the scanner's FLAG still stands; nothing can pause (fail-safe)
    return gate, scan_for_injection, run_intake_judge


def load_claude_token():
    """The tool-less reader needs the subscription token, and a cron/launchd job does not have it in its environment.
    The credential is handed to the shared layer HERE (plan B.4: the key lives in the shared fetch, not in a desk
    runner). Reads $CLAUDE_OAUTH_TOKEN_FILE or ~/.config/lifehack/claude-oauth-token into CLAUDE_CODE_OAUTH_TOKEN, only
    when it is not already set. No token = the reader is down: flagged mail is withheld and the run fails loudly (exit 3), nothing pauses."""
    if os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
        return True
    p = os.environ.get("CLAUDE_OAUTH_TOKEN_FILE") or os.path.expanduser("~/.config/lifehack/claude-oauth-token")
    try:
        tok = "".join(open(p, encoding="utf-8").read().split())  # ALL whitespace, like claude-auth.lib.sh (the file wraps)
    except OSError:
        return False
    if tok:
        os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = tok
    return bool(tok)


def desk_id(unit):
    return f"email:{unit}"


def report_attack(unit, body, item=""):
    """A caller that ran its own judge found REAL-ATTACK: pause the label and send ONE critical push (the lifted
    clamp, ingest_gate.gate(reader_verdict='REAL-ATTACK')). Returns the gate result."""
    gate, _scan, _judge = _gate_modules()
    return gate(desk_id(unit), "email", body, item=item, reader_verdict="REAL-ATTACK")


def gate_message(unit, body, item=""):
    """Gate ONE message body. Returns dict(content, provenance_tag, verdict, attack). Never feeds ungated text out."""
    gate, scan, judge = _gate_modules()
    findings = []
    try:
        findings = scan(body) or []
    except Exception:  # noqa: BLE001
        findings = []
    if findings and judge is None:
        return {"content": "", "provenance_tag": "", "verdict": "UNJUDGED", "attack": False,
                "reason": "intake_reader could not be imported"}
    if not findings:
        res = gate(desk_id(unit), "email", body, item=item)
        return {"content": res["content"], "provenance_tag": res["provenance_tag"], "verdict": "NONE", "attack": False}
    load_claude_token()
    j = judge(body, findings)
    if not j.get("reader_applied"):
        # FLAGGED + unjudged: never hand the raw text on. The caller withholds the run (fetch -> ReaderDown).
        return {"content": "", "provenance_tag": "", "verdict": "UNJUDGED", "attack": False,
                "reason": str(j.get("reason") or "reader did not run")}
    verdict = j.get("verdict")
    if verdict == "REAL-ATTACK":
        res = gate(desk_id(unit), "email", body, item=item, reader_verdict="REAL-ATTACK")
        return {"content": "", "provenance_tag": res["provenance_tag"], "verdict": verdict, "attack": True}
    text = j.get("cleared_text")
    res = gate(desk_id(unit), "email", text or body, item=item)
    return {"content": res["content"], "provenance_tag": res["provenance_tag"], "verdict": verdict or "NONE",
            "attack": False}


# ─────────────────────────── the fetch ───────────────────────────
def _label_id(label):
    if label.isupper() or label.startswith("Label_"):
        return label
    data, err = labels_list()
    if err:
        raise FetchError(f"labels.list failed: {err}")
    for l in data.get("labels", []):
        if l.get("name") == label or l.get("id") == label:
            return l["id"]
    raise FetchError(f"unknown label '{label}'")


def fetch(consumer, *, label, query, cap, since_last_seen, mark_seen):
    """Read up to `cap` threads, gate every message, return {unit, query, count, messages[], attack}.
    Raises Disabled / Paused / FetchError. A REAL-ATTACK pauses the label, stops the read and raises Paused."""
    if not enabled():
        raise Disabled("EMAIL_SERVICE_READ is off")
    unit = label or "primary"
    check_paused(unit)
    if query is None or cap is None or since_last_seen is None or mark_seen is None:
        raise TypeError("email_fetch.fetch: query, cap, since_last_seen and mark_seen are the caller's choice -- pass each explicitly")
    q = query
    seen_ms, _ = read_last_seen(consumer)
    stale_pending = pending_path(consumer)   # 5.9(f): a pending file left by a run that never finished is never trusted
    if os.path.exists(stale_pending):
        os.remove(stale_pending)
    if since_last_seen and seen_ms:
        q = (q + " " if q else "") + f"after:{seen_ms // 1000}"
    params = {"maxResults": max(1, int(cap))}
    if label:
        params["labelIds"] = _label_id(label)
    if q:
        params["q"] = q
    data, err = list_threads(params)
    if err:
        raise FetchError(err)
    ids = [t["id"] for t in data.get("threads", [])][:cap]
    out, newest_ms, newest_id = [], 0, ""
    withheld, why = 0, ""
    for tid in ids:
        th, err = get_thread(tid, "full")
        if err:
            raise FetchError(f"thread {tid}: {err}")
        for msg in (th.get("messages") or [])[:MAX_MSGS_PER_THREAD]:
            try:
                ms = int(msg.get("internalDate") or 0)
            except ValueError:
                ms = 0
            if since_last_seen and seen_ms and ms <= seen_ms:
                continue
            h = _headers(msg)
            g = gate_message(unit, message_text(msg), item=f"{consumer}:{msg.get('id', '')}")
            if g["attack"]:
                raise Paused(unit)
            if g["verdict"] == "UNJUDGED":
                withheld, why = withheld + 1, why or g.get("reason", "")
                continue
            out.append({"thread_id": tid, "message_id": msg.get("id", ""), "internal_date": ms,
                        "from": h.get("From", ""), "subject": h.get("Subject", ""), "date": h.get("Date", ""),
                        "body": g["content"], "provenance_tag": g["provenance_tag"], "verdict": g["verdict"]})
            if ms > newest_ms:
                newest_ms, newest_id = ms, msg.get("id", "")
    if withheld:   # safest: withhold the WHOLE run (benign mail waits too); bookmark untouched, so all of it is re-read
        raise ReaderDown(f"reader unavailable: {withheld} flagged message(s) withheld -- {why or 'reader did not run'}")
    if mark_seen and newest_ms:   # 5.9(f): NEVER the bookmark itself; a peek (mark_seen=False / --no-mark) writes nothing at all
        write_pending(consumer, newest_ms, newest_id)
    return {"unit": unit, "query": q, "count": len(out), "messages": out, "attack": False}


def main(argv=None):
    ap = argparse.ArgumentParser(description="The shared email fetch (the only sanctioned Gmail read).")
    ap.add_argument("--consumer", help="who is reading (names the *-last-seen file)")
    ap.add_argument("--label", default=None, help="Gmail label to read (also the unit that gets paused)")
    ap.add_argument("--query", default=None, help="Gmail query (required for a read; '' = none). No default: read policy is the caller's")
    ap.add_argument("--cap", type=int, default=None, help="max threads per run (required for a read). No default")
    ap.add_argument("--since", choices=["bookmark", "none"], default=None,
                    help="start point (required for a read): after the consumer's *-last-seen bookmark, or no filter")
    ap.add_argument("--no-mark", action="store_true", help="do not advance the bookmark")
    ap.add_argument("--out", default=None, help="write the JSON result here instead of stdout")
    ap.add_argument("--preflight", action="store_true", help="exit 0 if Google auth answers, else 2")
    ap.add_argument("--promote-pending", metavar="FILE", help="(job-run.sh only) move a *-last-seen.pending over its bookmark, forward-only")
    a = ap.parse_args(argv)
    if a.promote_pending:
        try:
            moved = promote_pending(a.promote_pending)
        except BookmarkCorrupt as e:
            sys.stderr.write(f"[email-fetch] CORRUPT bookmark: {e} -- refusing to start fresh; fix or remove that file by hand\n")
            return 1
        print(f"[email-fetch] bookmark {'advanced' if moved else 'already at or past this mark'}: {a.promote_pending[:-len('.pending')]}")
        return 0
    if a.preflight:
        return 0 if preflight() else EXIT_TRANSIENT
    if not a.consumer:
        ap.error("--consumer is required")
    missing = [f for f, v in (("--query", a.query), ("--cap", a.cap), ("--since", a.since)) if v is None]
    if missing:   # the fetch sets no read policy of its own; the calling job states every choice
        ap.error(f"{', '.join(missing)} required: read policy (query, cap, start point) is the calling job's choice, never a default")
    try:
        res = fetch(a.consumer, label=a.label, query=a.query, cap=a.cap,
                    since_last_seen=(a.since == "bookmark"), mark_seen=not a.no_mark)
    except BookmarkCorrupt as e:
        sys.stderr.write(f"[email-fetch] CORRUPT bookmark: {e} -- refusing to start fresh; fix or remove that file by hand\n")
        return 1
    except Paused as e:
        sys.stderr.write(f"paused: {e}\n")
        return EXIT_PAUSED
    except Disabled as e:
        sys.stderr.write(f"email read disabled: {e}\n")
        return EXIT_PAUSED
    except ReaderDown as e:
        sys.stderr.write(f"[email-fetch] {e}\n")
        return EXIT_READER_DOWN
    except FetchError as e:
        sys.stderr.write(f"[email-fetch] {e}\n")
        return EXIT_TRANSIENT if re.match(r"(gws_error|timeout|json_parse)", str(e)) else 1
    text = json.dumps(res)
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""push_warn.py -- the WARN mode of the public-push leakage scan (roundB.conf fc_private_push_mode=warn).

WHY: Enver's ruling 2026-11-02 (record <notes>/state/projects/v2/records/2026-11-02-push-scan-warn-mode.md): the hard stop on a
     public-remote push that the leakage scan flags is replaced, in warn mode, by a middle ground: the push goes ahead, Claude is
     told what was found at that step, every finding is written down, and the end of the turn makes Claude tell the person.
CALLERS:
  guard_git_push_signpost.sh   `log`  when it ALLOWS a push the scan flagged (warn mode)
                               `text` to add the findings to the first-sight signpost
  end_of_turn_checks.sh        `eot`  on Stop: the forced report
COMMANDS:
  log  --warn-b64 B --repo R --shared S   (stdin = the PreToolUse payload, for session_id)
       Appends ONE JSON line per finding to <notes>/state/push-warnings.log (notes root from shared/person_roots.py):
       {time, id, session, repo, repo_name, remote, url, range, commits, commit_count, finding, mode}.
       Also appends the same lines to the per-session marker <turn-writes>/<session>.pushwarn (what the Stop check reads).
       Same entry already written (the guard is registered twice and both copies run) = not written again.
       exit 0 + prints the PreToolUse JSON (additionalContext, NO permission decision) on success;
       exit 3 + prints the reason when the log or the marker cannot be written -> the caller BLOCKS (fail closed).
  text --warn-b64 B                        prints the findings as plain lines (no writes).
  eot                                      (stdin = the Stop payload) prints nothing, or the block reason.
       Pending = this session's marker lines. An entry is REPORTED when its id appears in the final assistant message
       (payload last_assistant_message, else the last assistant text in transcript_path); reported entries leave the marker.
       Anything still pending -> the reason text (the caller wraps it as {"decision":"block"}). Anti-stuck valve: at most
       MAX_ASKS blocks in a turn with nothing reported; then it stops blocking for THAT turn, appends one
       "UNREPORTED after 3 asks" line per finding to push-warnings.log (once per turn) and KEEPS the marker, so every
       later turn nudges once more until the ids are reported. Findings are never dropped.
FAIL_POSTURE: log = closed (exit 3 -> block). eot = degrade-safe (any error -> silent, stderr line).
"""
import argparse
import base64
import datetime
import fcntl
import hashlib
import json
import os
import re
import sys

LOG_NAME = "push-warnings.log"
MAX_ASKS = 3


def turn_dir():
    return os.environ.get("LHB_TURN_WRITES_DIR") or os.path.join(os.path.expanduser("~"), ".claude", "run", "turn-writes")


def safe_sid(sid):
    return re.sub(r"[^A-Za-z0-9_-]", "-", sid or "")[:100] or "unknown"


def decode(b64):
    w = json.loads(base64.b64decode(b64).decode("utf-8", "surrogateescape"))
    if not isinstance(w, dict):
        raise ValueError("warn facts are not an object")
    return w


def git_top(repo):
    import subprocess
    try:
        r = subprocess.run(["git", "-C", repo, "rev-parse", "--show-toplevel"], capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else repo
    except Exception:
        return repo


def finding_lines(w):
    return [str(f) for f in (w.get("findings") or [])]


def entries(w, sid, repo):
    top = os.path.realpath(git_top(repo))
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out = []
    for f in finding_lines(w):
        key = "|".join([sid, w.get("url", ""), w.get("range", ""), ",".join(w.get("commits") or []), f])
        out.append({"time": now, "id": "pw-" + hashlib.sha1(key.encode("utf-8", "surrogateescape")).hexdigest()[:10],
                    "session": sid, "repo": top, "repo_name": os.path.basename(top), "remote": w.get("remote", ""),
                    "url": w.get("url", ""), "range": w.get("range", ""), "commits": w.get("commits") or [],
                    "commit_count": w.get("commit_count", 0), "finding": f, "mode": "warn"})
    return out


def append_unique(path, rows):
    """Append rows whose id is not already in the file, under an exclusive lock. Raises on any write failure."""
    with open(path, "a+", encoding="utf-8") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        fh.seek(0)
        have = set()
        for ln in fh:
            try:
                have.add(json.loads(ln).get("id"))
            except ValueError:
                continue
        new = [r for r in rows if r["id"] not in have]
        for r in new:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
        fcntl.flock(fh, fcntl.LOCK_UN)
    return new


def cmd_log(a):
    try:
        w = decode(a.warn_b64)
    except Exception as e:
        print("the scan's findings could not be read back (%s)" % str(e)[:120])
        return 3
    raw = sys.stdin.read()
    sid = ""
    try:
        sid = (json.loads(raw) or {}).get("session_id") or ""
    except Exception:  # allow-silence: an unreadable payload falls back to $CLAUDE_CODE_SESSION_ID just below
        pass
    sid = safe_sid(sid or os.environ.get("CLAUDE_CODE_SESSION_ID", ""))
    if a.shared and a.shared not in sys.path:
        sys.path.insert(0, a.shared)
    try:
        import person_roots
        notes = person_roots.notes_root()
    except Exception as e:
        print("the notes root could not be resolved (shared/person_roots.py: %s)" % str(e)[:120])
        return 3
    if not notes:
        print("the notes root is not set or not usable (shared/person_roots.py found none), so there is nowhere to log the warning")
        return 3
    log = os.path.join(notes, "state", LOG_NAME)
    rows = entries(w, sid, a.repo)
    if not rows:
        print("the scan flagged the push but returned no finding text to log")
        return 3
    for r in rows:
        r["log"] = log
    try:
        os.makedirs(os.path.dirname(log), exist_ok=True)
        append_unique(log, rows)
    except Exception as e:
        print("could not write %s (%s)" % (log, str(e)[:160]))
        return 3
    marker = os.path.join(turn_dir(), sid + ".pushwarn")
    try:
        os.makedirs(turn_dir(), exist_ok=True)
        append_unique(marker, rows)
    except Exception as e:
        print("could not write the end-of-turn marker %s (%s)" % (marker, str(e)[:160]))
        return 3
    msg = ["PUSH SCAN WARNING (warn mode, fc_private_push_mode=warn): this push to %s (%s) is ALLOWED, but the leakage scan "
           "(.github/scripts/check_no_internal_leakage.py) flagged its outgoing commits (%s):" % (rows[0]["remote"], rows[0]["url"], rows[0]["range"])]
    for r in rows:
        msg.append("  %s: %s" % (r["id"], r["finding"]))
    msg.append("Logged to %s. Before you finish this turn, tell the person, ONE line per finding, starting each line with its id "
               "(e.g. 'PUSH WARNING %s: ...'). The end-of-turn check holds the turn until you do." % (log, rows[0]["id"]))
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": "\n".join(msg)[:3000]}}))
    return 0


def cmd_text(a):
    try:
        w = decode(a.warn_b64)
    except Exception:
        return 0
    for f in finding_lines(w):
        print(f)
    return 0


def last_assistant_text(p):
    m = p.get("last_assistant_message")
    if isinstance(m, str) and m.strip():
        return m
    tp = p.get("transcript_path") or ""
    last = ""
    try:
        for ln in open(tp, encoding="utf-8", errors="replace"):
            try:
                e = json.loads(ln)
            except ValueError:
                continue
            if e.get("type") != "assistant":
                continue
            c = (e.get("message") or {}).get("content")
            if isinstance(c, str):
                t = c
            elif isinstance(c, list):
                t = "\n".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text")
            else:
                t = ""
            if t.strip():
                last = t
    except OSError:
        pass
    return last


def cmd_eot(_a):
    try:
        p = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    sid = safe_sid(p.get("session_id") or "")
    marker = os.path.join(turn_dir(), sid + ".pushwarn")
    asked = marker + ".asked"
    if not os.path.isfile(marker):
        return 0
    with open(marker, "r+", encoding="utf-8") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        pending = []
        for ln in fh:
            try:
                pending.append(json.loads(ln))
            except ValueError:
                continue
        said = last_assistant_text(p)
        left = [r for r in pending if r.get("id") and r["id"] not in said]
        if len(left) != len(pending):
            fh.seek(0)
            fh.truncate()
            for r in left:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            fh.flush()
        fcntl.flock(fh, fcntl.LOCK_UN)
    if not left:
        for f in (marker, asked):
            try:
                os.remove(f)   # every warning was reported: the marker is spent (the log keeps them all)
            except OSError:
                pass
        return 0
    # asked-state: {"pid": this turn's prompt_id, "n": blocks this turn with nothing reported, "gave_up": ever gave up}
    # Budget: MAX_ASKS blocks in the first turn; once it has given up, ONE nudge per later turn. The marker is NEVER
    # removed while anything is unreported, so the findings are never dropped -- only the blocking pauses.
    pid = str(p.get("prompt_id") or "")
    st = {}
    try:
        st = json.loads(open(asked, encoding="utf-8").read() or "{}")
        if not isinstance(st, dict):
            st = {}
    except (OSError, ValueError):
        st = {}
    gave_up = bool(st.get("gave_up"))
    n = int(st.get("n") or 0) if st.get("pid") == pid else 0   # a new turn starts its own count
    if len(left) < len(pending):
        n = 0          # progress was made: the count of asks-with-nothing-reported starts again
    budget = 1 if gave_up else MAX_ASKS
    if n >= budget:
        if st.get("logged_pid") != pid:
            logs = [r.get("log") for r in pending if os.path.isabs(str(r.get("log") or ""))]
            log = logs[0] if logs else ""
            now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            rows = [{"time": now, "id": "%s-unreported-%s" % (r["id"], hashlib.sha1(pid.encode()).hexdigest()[:8]),
                     "entry_id": r["id"], "session": sid, "status": "UNREPORTED after %d asks" % MAX_ASKS,
                     "repo_name": r.get("repo_name", ""), "remote": r.get("remote", ""), "range": r.get("range", ""),
                     "finding": r.get("finding", "")} for r in left]
            try:
                append_unique(log, rows)
            except Exception as e:
                sys.stderr.write("end_of_turn_checks: could not write the UNREPORTED line to %s (%s)\n" % (log, e))
            st["logged_pid"] = pid
        st.update(pid=pid, n=n, gave_up=True)
        try:
            with open(asked, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(st))
        except OSError as e:
            sys.stderr.write("end_of_turn_checks: could not save push-warning ask state (%s)\n" % e)
        sys.stderr.write("end_of_turn_checks: %d push warning(s) still UNREPORTED after %d asks; logged as such in %s; "
                         "the next turn asks again\n" % (len(left), MAX_ASKS, left[0].get("log", LOG_NAME)))
        return 0
    st.update(pid=pid, n=n + 1, gave_up=gave_up)
    try:
        with open(asked, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(st))
    except OSError as e:
        sys.stderr.write("end_of_turn_checks: could not save push-warning ask state (%s)\n" % e)
    out = ["END-OF-TURN CHECK: this session pushed to a remote other people can read, and the leakage scan flagged what went out "
           "(warn mode: the push was allowed, and each finding was logged to %s)." % left[0].get("log", LOG_NAME),
           "Tell the person now, in your FINAL message, ONE line per finding, starting each line with its id exactly as written:"]
    for r in left:
        out.append("PUSH WARNING %s: %s -> %s (%s): %s" % (r["id"], r.get("repo_name", ""), r.get("remote", ""), r.get("range", ""),
                                                         r.get("finding", "")))
    out.append("This check repeats until every id above appears in your final message. Rule: system/hooks/lib/push_warn.py "
               "(switch fc_private_push_mode in system/hooks/roundB.conf).")
    print("\n".join(out))
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    lg = sub.add_parser("log")
    lg.add_argument("--warn-b64", required=True)
    lg.add_argument("--repo", required=True)
    lg.add_argument("--shared", default="")
    tx = sub.add_parser("text")
    tx.add_argument("--warn-b64", required=True)
    sub.add_parser("eot")
    a = ap.parse_args()
    if a.cmd == "log":
        try:
            return cmd_log(a)
        except Exception as e:   # anything unexpected while logging = fail closed
            print("push warning logging crashed (%s: %s)" % (type(e).__name__, str(e)[:160]))
            return 3
    if a.cmd == "text":
        return cmd_text(a)
    try:
        return cmd_eot(a)
    except Exception as e:
        sys.stderr.write("end_of_turn_checks: push-warning check crashed (%s); skipped\n" % e)
        return 0


if __name__ == "__main__":
    sys.exit(main())

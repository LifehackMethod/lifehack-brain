#!/usr/bin/env python3
# not-wired-yet: run by hand; its caller, system/tools/trial_daily_read.py (false_alarms_section), lands separately
"""false_alarm_daily.py — course-check 7: the daily list of LIKELY false alarms.

WHY: a guard that stops harmless work trains the person to press Yes without reading. This lists, for the last 24h,
every ASK and BLOCK from our hooks whose stopped call LOOKS harmless, so a person can skim it and fix the guard.
It is a triage list, never a verdict. READ-ONLY: it opens files and writes nothing.

"Looks harmless" means one of:
  - the stopped tool was read-only (Read, Grep, Glob);
  - the Bash command was a PURE READ: every segment is ls/cat/grep/rg/find/head/tail/wc/stat/file/pwd/which (cd,
    sort, uniq, cut may join them), or a read-only git subcommand (status/log/diff/show/rev-parse/ls-files/blame,
    `remote` with no args or -v). Parsed with shlex, so a quoted ">" or "|" inside a pattern is text, not a write or
    a pipe. Any write redirect (except to /dev/null or an fd), subshell, $(...), backtick, or a find action
    (-delete, -exec, ...) disqualifies the whole command;
  - the target was a THROWAWAY path: EVERY absolute path in the call is under /tmp, /private/tmp, /var/folders,
    $TMPDIR, or a folder whose name contains "scratch" (or node_modules / .venv / __pycache__). A call that also
    names a real path is not listed: it may be the real target.

SOURCES:
  fire journal  ~/.claude/run/fire-journal.jsonl + rotated shards, discovered and normalised by fire_journal_query
                (reused, not re-parsed). A BLOCK is a PreToolUse line with decision deny (exit 2).
                ASK, BOTH FORMS: today an ask hook exits 0, so it journals as "allow" and the journal cannot see it;
                a coming fix records decision "ask". A line with decision "ask" is read as an ASK here (the query
                tool's closed set does not know "ask" yet, so it is normalised as allow and tagged here).
  transcripts   ~/.claude/projects/*/<session>.jsonl (+ <session>/subagents/*.jsonl), for the sessions that have
                journal lines in the window. They give the stopped call itself (the journal never records the
                command), and the asks in today's form: a PreToolUse hook_success attachment whose stdout carries
                permissionDecision "ask", tied to its call by toolUseID. A journal BLOCK is matched to the errored
                tool result whose "hook error" text names the same hook, nearest in time (within 5 minutes).
STATED LIMIT: a journal stop with no transcript match can only be judged from its matcher (listed only when the
  matcher names read-only tools alone); every other unmatched stop is COUNTED as "could not judge" in the page,
  never silently dropped. Most of that count is usually hooks run directly by the test suite: they inherit the
  session id, so they journal into a real session that holds no matching call.

Importable (system/tools/trial_daily_read.py calls these):
  false_alarm_list(journal=DEFAULT_JOURNAL, hours=24, now=None, projects_root=DEFAULT_PROJECTS)
      -> list of {ts, kind ("ASK"|"BLOCK"), hook, session, tool, command, why}; the list also carries .stats
         (dict: journal_files, stops_seen, unjudged, malformed). Never raises on a missing/bad journal.
  render_markdown(items, now=None, hours=24) -> one markdown block.

Run:  python3 system/tools/false_alarm_daily.py [--journal PATH] [--hours H] [--projects DIR] [--now EPOCH] [--json]
Test: python3 system/tools/test_false_alarm_daily.py
"""

import argparse
import datetime
import glob
import json
import os
import re
import shlex
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fire_journal_query as fjq  # noqa: E402  (the journal's own read side)

DEFAULT_JOURNAL = fjq.DEFAULT_JOURNAL
DEFAULT_PROJECTS = os.path.join(os.path.expanduser("~"), ".claude", "projects")
MATCH_TOLERANCE_S = 300

READ_ONLY_TOOLS = {"Read", "Grep", "Glob"}
READ_VERBS = {"ls", "cat", "grep", "rg", "find", "head", "tail", "wc", "stat", "file", "pwd", "which"}
NEUTRAL_VERBS = {"cd", "sort", "uniq", "cut"}     # harmless joiners; a command made only of these is not a "read"
GIT_READ_SUBS = {"status", "log", "diff", "show", "rev-parse", "ls-files", "blame"}
FIND_ACTIONS = {"-delete", "-exec", "-execdir", "-ok", "-okdir", "-fprint", "-fprint0", "-fprintf", "-fls"}
SEPARATORS = {";", "&&", "||", "|", "&", "|&"}

# Path TEXT only: it classifies paths already written in logged commands; nothing here makes or writes a temp file.
THROWAWAY_RE = re.compile(r"^(?:/private)?(?:/tmp|/var/folders)(?:/|$)|/[^/]*scratch[^/]*(?:/|$)|/(?:node_modules|\.venv|__pycache__)(?:/|$)", re.I)
HOOK_ERROR_RE = re.compile(r"hook error: \[[^\]]*?([A-Za-z0-9_.\-]+\.(?:sh|py))[\"']?\]")
HOOK_NAME_RE = re.compile(r"([A-Za-z0-9_.\-]+\.(?:sh|py))")
QUOTED_RE = re.compile(r"'[^']*'|\"(?:[^\"\\]|\\.)*\"")


# ── classifying one stopped call ─────────────────────────────────────────────────────────────

def _tokens(cmd):
    """shlex tokens with shell operators split out; None when the line cannot be parsed (unbalanced quotes)."""
    lx = shlex.shlex(cmd.replace("\n", " ; "), posix=True, punctuation_chars=True)
    lx.whitespace_split = True
    try:
        return list(lx)
    except ValueError:
        return None


def _segments(tokens):
    seg, out = [], []
    for t in tokens:
        if t in SEPARATORS:
            if seg:
                out.append(seg)
            seg = []
        else:
            seg.append(t)
    if seg:
        out.append(seg)
    return out


def _segment_is_read(seg):
    """-> "read" | "neutral" | None (not a read)."""
    words = []
    i = 0
    while i < len(seg):
        t = seg[i]
        if t in ("(", ")") or "(" in t or ")" in t:
            return None                                   # subshell / $( ) / <( ): cannot vouch for it
        if ">" in t:
            nxt = seg[i + 1] if i + 1 < len(seg) else ""
            if t == ">&" or (t in (">", ">>", "&>") and nxt == "/dev/null"):
                i += 2                                    # 2>/dev/null, 2>&1: no file is written
                continue
            return None                                   # any other redirect writes a file
        if t in ("<", "<<", "<<<"):
            i += 2
            continue
        words.append(t)
        i += 1
    if not words:
        return "neutral"
    verb = os.path.basename(words[0])
    if verb in NEUTRAL_VERBS:
        return "neutral"
    if verb == "find":
        return None if any(w in FIND_ACTIONS for w in words[1:]) else "read"
    if verb in READ_VERBS:
        return "read"
    if verb == "git":
        rest = words[1:]
        while rest and rest[0].startswith("-"):           # git -C <dir> / --no-pager / -c k=v before the subcommand
            rest = rest[2:] if rest[0] in ("-C", "-c") else rest[1:]
        if not rest:
            return None
        sub, args = rest[0], rest[1:]
        if any(a.startswith("--output") for a in args):
            return None
        if sub in GIT_READ_SUBS:
            return "read"
        if sub == "remote" and all(a in ("-v", "--verbose") for a in args):
            return "read"
    return None


def is_pure_read(cmd):
    """True when every segment of the shell line is a plain read (see the module docstring)."""
    if not cmd or not cmd.strip() or "`" in cmd:
        return False
    toks = _tokens(QUOTED_RE.sub(" Q ", cmd))             # quoted text is data: a ">" or "|" inside it is not an operator
    if not toks:
        return False
    kinds = [_segment_is_read(s) for s in _segments(toks)]
    return bool(kinds) and None not in kinds and "read" in kinds


def _throwaway_roots():
    roots = []
    for v in (os.environ.get("TMPDIR"), tempfile.gettempdir()):
        if v and v.rstrip("/") not in ("", "/"):
            roots.append(os.path.realpath(v).rstrip("/"))
            roots.append(v.rstrip("/"))
    return roots


def is_throwaway_path(p):
    if not p:
        return False
    if THROWAWAY_RE.search(p):
        return True
    return any(p == r or p.startswith(r + "/") for r in _throwaway_roots())


def _abs_paths(text):
    toks = _tokens(text) or text.split()
    out = []
    for t in toks:
        for part in re.split(r"[=:]", t):                # --out=/tmp/x, PATH-like a:b
            if part.startswith("/") or part.startswith("~/"):
                out.append(os.path.expanduser(part))
    return out


def is_throwaway(text):
    """True when the call names at least one absolute path and EVERY one of them is throwaway."""
    paths = _abs_paths(text or "")
    return bool(paths) and all(is_throwaway_path(p) for p in paths)


def call_text(tool, inp):
    inp = inp if isinstance(inp, dict) else {}
    return str(inp.get("command") or inp.get("file_path") or inp.get("notebook_path") or inp.get("path")
               or inp.get("pattern") or "")


def why_harmless(tool, inp):
    """One short reason string when the stopped call looks harmless, else None."""
    text = call_text(tool, inp)
    if tool in READ_ONLY_TOOLS:
        return "read-only tool (%s) was stopped" % tool
    if tool == "Bash" and is_pure_read(text):
        return "command is a pure read"
    if is_throwaway(text):
        return "target is a throwaway path"
    return None


# ── journal ──────────────────────────────────────────────────────────────────────────────────

def journal_stops(journal, since, now, stats):
    """-> (stops, sessions): stops = [{ts, kind, hook, session, matcher}] for PreToolUse ASK/BLOCK lines in the window;
    sessions = every session id with any journal line in the window (their transcripts are where asks are seen today)."""
    stops, sessions = [], set()
    path = os.path.expanduser(journal)
    files = fjq.discover_journal_files(path)
    stats["journal_files"] = len(files)
    for p in files:
        try:
            fh = open(p, encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    is_ask = isinstance(obj, dict) and str(obj.get("decision", "")).strip().lower() in ("ask", "asked")
                    rec = fjq.normalize_line(dict(obj, decision="allow") if is_ask else obj)
                except (ValueError, fjq.Malformed):
                    stats["malformed"] += 1
                    continue
                if not (since <= rec["ts"] <= now):
                    continue
                if rec["session_id"]:
                    sessions.add(rec["session_id"])
                if "PreToolUse" not in rec["event"]:
                    continue
                kind = "ASK" if is_ask else ("BLOCK" if rec["decision"] == "deny" or rec["exit_code"] == 2 else None)
                if kind:
                    stops.append(dict(ts=rec["ts"], kind=kind, hook=os.path.basename(rec["hook"]),
                                      session=rec["session_id"], matcher=rec["matcher"] or ""))
    return stops, sessions


# ── transcripts ──────────────────────────────────────────────────────────────────────────────

def _iso_epoch(ts):
    try:
        return datetime.datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return None


_STATUS_MAP = None


def _status_map():
    """statusMessage -> sorted hook file names, from the plugin's own hooks/hooks.json. A plugin hook's transcript
    attachment carries its statusMessage in "command" (not the script path), so this is how an ask is named."""
    global _STATUS_MAP
    if _STATUS_MAP is None:
        m = {}
        try:
            with open(os.path.join(os.path.dirname(os.path.dirname(HERE)), "hooks", "hooks.json"), encoding="utf-8") as f:
                todo = [json.load(f)]
        except (OSError, ValueError):
            todo = []
        while todo:
            o = todo.pop()
            if isinstance(o, dict):
                if o.get("statusMessage") and o.get("command"):
                    m.setdefault(o["statusMessage"], set()).update(HOOK_NAME_RE.findall(o["command"])[-1:])
                todo.extend(o.values())
            elif isinstance(o, list):
                todo.extend(o)
        _STATUS_MAP = {k: sorted(v) for k, v in m.items()}
    return _STATUS_MAP


def hook_of_attachment(command):
    names = HOOK_NAME_RE.findall(str(command or ""))
    if names:
        return names[-1]
    mapped = _status_map().get(str(command or "").strip())
    return "|".join(mapped) if mapped else "(unnamed hook)"


def session_files(projects_root, sid):
    return (glob.glob(os.path.join(projects_root, "*", sid + ".jsonl"))
            + glob.glob(os.path.join(projects_root, "*", sid, "subagents", "*.jsonl")))


def session_stops(projects_root, sid):
    """-> {"uses": {id: (tool, input)}, "asks": [{id, ts, hook}], "blocks": [{id, ts, hook}]} for one session."""
    uses, asks, blocks = {}, [], []
    for path in session_files(projects_root, sid):
        try:
            fh = open(path, encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for line in fh:
                if "tool_use" not in line and "permissionDecision" not in line:
                    continue                              # cheap skip: most transcript lines are prose
                try:
                    o = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(o, dict):
                    continue
                ts = _iso_epoch(o.get("timestamp"))
                att = o.get("attachment")
                if isinstance(att, dict) and att.get("hookEvent") == "PreToolUse" and "permissionDecision" in str(att.get("stdout")):
                    try:
                        hso = json.loads(att["stdout"]).get("hookSpecificOutput") or {}
                    except (ValueError, AttributeError, TypeError):
                        hso = {}
                    if hso.get("permissionDecision") == "ask":
                        asks.append(dict(id=att.get("toolUseID"), ts=ts, hook=hook_of_attachment(att.get("command"))))
                    continue
                msg = o.get("message")
                if not isinstance(msg, dict) or not isinstance(msg.get("content"), list):
                    continue
                for b in msg["content"]:
                    if not isinstance(b, dict):
                        continue
                    if b.get("type") == "tool_use":
                        uses[b.get("id")] = (b.get("name"), b.get("input"))
                    elif b.get("type") == "tool_result" and b.get("is_error"):
                        c = b.get("content")
                        if isinstance(c, list):
                            c = " ".join(x.get("text", "") for x in c if isinstance(x, dict))
                        m = HOOK_ERROR_RE.search(str(c or ""))
                        if m:
                            blocks.append(dict(id=b.get("tool_use_id"), ts=ts, hook=m.group(1)))
    return {"uses": uses, "asks": asks, "blocks": blocks}


def _nearest(cands, hook, ts, taken):
    pool = [c for c in cands if hook in c["hook"].split("|") and c["id"] not in taken and c["ts"] is not None
            and abs(c["ts"] - ts) <= MATCH_TOLERANCE_S]
    return min(pool, key=lambda c: abs(c["ts"] - ts)) if pool else None


# ── the list ─────────────────────────────────────────────────────────────────────────────────

class FalseAlarms(list):
    """A plain list of items that also carries .stats (what was read, what could not be judged)."""
    stats = None


def false_alarm_list(journal=DEFAULT_JOURNAL, hours=24, now=None, projects_root=DEFAULT_PROJECTS):
    now = time.time() if now is None else now
    since = now - hours * 3600
    projects_root = os.path.expanduser(projects_root)
    stats = {"journal_files": 0, "stops_seen": 0, "unjudged": 0, "malformed": 0}
    jstops, sessions = journal_stops(journal, since, now, stats)
    tx = {sid: session_stops(projects_root, sid) for sid in sorted(sessions)}

    out, taken = FalseAlarms(), {}

    def add(kind, hook, sid, ts, tool, inp):
        why = why_harmless(tool, inp)
        if why:
            out.append(dict(ts=ts, kind=kind, hook=hook, session=sid, tool=tool, command=call_text(tool, inp), why=why))

    # 1) stops the journal recorded (BLOCKs; ASKs once the journal records them as "ask")
    for s in jstops:
        stats["stops_seen"] += 1
        t = tx.get(s["session"]) or {"uses": {}, "asks": [], "blocks": []}
        seen = taken.setdefault(s["session"], set())
        hit = _nearest(t["asks"] if s["kind"] == "ASK" else t["blocks"], s["hook"], s["ts"], seen)
        if hit and hit["id"] in t["uses"]:
            seen.add(hit["id"])
            tool, inp = t["uses"][hit["id"]]
            add(s["kind"], s["hook"], s["session"], hit["ts"], tool, inp)
            continue
        tools = [x for x in s["matcher"].split("|") if x]
        if tools and all(x in READ_ONLY_TOOLS for x in tools):
            out.append(dict(ts=s["ts"], kind=s["kind"], hook=s["hook"], session=s["session"], tool=s["matcher"],
                            command="(no transcript match)", why="read-only tool(s) %s stopped" % s["matcher"]))
        else:
            stats["unjudged"] += 1
    # 2) asks the journal cannot see today (an ask hook journals as "allow"): read from the window's transcripts
    for sid, t in tx.items():
        seen = taken.setdefault(sid, set())
        for a in t["asks"]:
            if a["id"] in seen or a["ts"] is None or not (since <= a["ts"] <= now):
                continue
            seen.add(a["id"])
            stats["stops_seen"] += 1
            if a["id"] in t["uses"]:
                tool, inp = t["uses"][a["id"]]
                add("ASK", a["hook"], sid, a["ts"], tool, inp)
            else:
                stats["unjudged"] += 1
    out.sort(key=lambda i: i["ts"] or 0)
    out.stats = stats
    return out


def render_markdown(items, now=None, hours=24):
    now = time.time() if now is None else now
    L = ["### Suspected false alarms, last %dh (to %s)" % (hours, datetime.datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M")), "",
         "Triage list, not verdicts: ASKs and BLOCKs whose stopped call was a pure read, a read-only tool, or touched "
         "only throwaway paths.", ""]
    if items:
        for i in items:
            t = datetime.datetime.fromtimestamp(i["ts"]).strftime("%H:%M:%S") if i["ts"] else "?"
            cmd = " ".join(str(i["command"] or "").split())
            cmd = cmd[:100] + ("…" if len(cmd) > 100 else "")
            L.append("- %s · %s · %s · %s `%s` · why: %s" % (t, i["kind"], i["hook"], i.get("tool") or "?", cmd.replace("`", "'"), i["why"]))
    else:
        L.append("- none in the window")
    st = getattr(items, "stats", None)
    if st:
        L += ["", "Read: %d journal file(s); %d stop(s) seen; %d could not be judged (no transcript match); %d malformed journal line(s)." % (
            st["journal_files"], st["stops_seen"], st["unjudged"], st["malformed"])]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Course-check 7: the last 24h's ASKs and BLOCKs that look like false alarms (read-only).")
    ap.add_argument("--journal", default=DEFAULT_JOURNAL)
    ap.add_argument("--hours", type=int, default=24)
    ap.add_argument("--projects", default=DEFAULT_PROJECTS, help="Claude Code projects root holding session transcripts")
    ap.add_argument("--now", type=float, default=None)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    items = false_alarm_list(a.journal, a.hours, a.now, a.projects)
    if a.json:
        print(json.dumps({"items": list(items), "stats": items.stats}, indent=1))
    else:
        print(render_markdown(items, now=a.now, hours=a.hours))
    return 0


if __name__ == "__main__":
    sys.exit(main())

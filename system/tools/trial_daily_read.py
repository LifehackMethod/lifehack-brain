#!/usr/bin/env python3
# not-wired-yet: run by hand during the two-week real-life trial (course-check 1); no job schedules it, by order
"""trial_daily_read.py — the DAILY READ for the V2 two-week real-life trial (course-check 1).

WHY: one short page a day that says what the guards actually did to real work: which asks fired and how the person
answered them, what was blocked, which stops look like false alarms, and where new files landed. Popups are split
PLANNED vs UNPLANNED (COMPASS P-72: unplanned popups must not become a constant thing again; asks we deliberately
planned are fine).

READ-ONLY. It reads existing logs and writes exactly one file, <notes>/state/projects/v2/trial/<date>-daily.md
(or prints with --stdout and writes nothing). It never changes a log, a switch or a hook.

SOURCES (each one optional; a source that is missing is NAMED in the page, never silently skipped):
  fire journal   ~/.claude/run/fire-journal.jsonl + rotated shards (system/hooks/lib/journal.sh; read through
                 fire_journal_query.discover_journal_files). Gives BLOCKS (PreToolUse exit 2) and hook ERRORS
                 (exit not 0/2/3), and since journal-records-ask (2026-11-02) ASKS: decision "ask" (an ask hook
                 exits 0; journal.sh reads the decision JSON the hook left). Rows written before that fix say
                 "allow" and stay allows. Rows with decision "unknown" (decision JSON unparseable) are listed apart.
                 NO DOUBLE COUNT: a journal ask and a transcript ask share no id (the journal has no tool_use id and
                 the transcript names the hook by its statusMessage), so they are matched on SESSION + TOOL (the
                 transcript's tool must fit the journal row's matcher) + TIME within MATCH_WINDOW_S, nearest first,
                 each transcript ask used once (and a hook name, when the transcript gives a script name, must
                 agree). A matched journal ask is the same ask; only unmatched ones are added, as journal-only.
  transcripts    ~/.claude/projects/*/<session>.jsonl. A PLANNED ask is a PreToolUse hook_success attachment whose
                 stdout carries permissionDecision "ask" (the fine-china, canon, Drive, Sheet and cloud asks). The
                 answer is read from that tool call's tool_result: rejected text = No, any other result = Yes,
                 none = no answer seen. An UNPLANNED popup is a rejected tool call with NO planned ask on it: the
                 harness's own permission prompt, which nobody chose.
                 STATED LIMIT: an unplanned popup the person answered YES leaves no trace in any of these logs, so
                 the unplanned count is a LOWER BOUND (only the No answers are seen).
  turn-writes    ~/.claude/run/turn-writes/<session>.list (system/hooks/turn_write_recorder.sh): "new" files,
                 kept when the file's birth time (else the list's mtime) falls in the window. Grouped by home.
  flight log     <notes>/system/flight-log.jsonl (session_flight_recorder.sh): sessions, tool calls, files written.
  observability  <notes>/system/observability/<YYYY-MM-DD>.jsonl: tool calls per tool / desk.
NOT THE TRIAL: test hooks, test runs and old plugins are left out of the counts, per reason, on one line each, never silently.
  Transcripts: an ask from a hook in fjq.TEST_HOOKS, or whose command runs a script from a scratch or temp path.
  Journal rows: fjq.row_source: old plugin version, "run":"test", a test hook, or plugin_src in a scratch or temp path. A row
  with no "run" field (older rows) and none of those stays counted and is reported as unknown.
FALSE ALARMS: the hook point is false_alarms_section(), which calls system/tools/false_alarm_daily.py
  (false_alarm_list + render_markdown) when that file is present. It lands separately; until then the section
  says so.

Run:   python3 system/tools/trial_daily_read.py              # last 24h, writes <notes>/state/projects/v2/trial/<date>-daily.md
       python3 system/tools/trial_daily_read.py --stdout     # print only
       options: --hours H --now EPOCH --notes DIR --out FILE --journal P --projects DIR --turn-writes DIR
Test:  python3 system/tools/test_trial_daily_read.py
"""
import argparse, collections, datetime, glob, json, os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, "shared"))
import fire_journal_query as fjq  # noqa: E402  (the journal's own read side)

HOME = os.path.expanduser("~")
DEFAULT_PROJECTS = os.path.join(HOME, ".claude", "projects")
DEFAULT_TURN_WRITES = os.environ.get("LHB_TURN_WRITES_DIR") or os.path.join(HOME, ".claude", "run", "turn-writes")
REJECTED_RE = re.compile(r"doesn't want to proceed|tool use was rejected", re.I)
RULE_RE = re.compile(r"RULE: switch (\w+)")
HOOK_BLOCK_RE = re.compile(r"PreToolUse:\w+ hook error")
HOOK_NAME_RE = re.compile(r"([A-Za-z0-9_\-]+\.(?:sh|py))")
MATCH_WINDOW_S = 30   # a journal ask and a transcript ask further apart than this are two different asks
TEST_HOOKS, SCRATCH_RE = fjq.TEST_HOOKS, fjq.SCRATCH_RE
SCRIPT_PATH_RE = re.compile(r"/[^\s\"']+\.(?:sh|py)\b")


# ───────────────────────── helpers ─────────────────────────
def iso_epoch(s):
    try:
        return datetime.datetime.fromisoformat(str(s).replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return None


def read_lines(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read().splitlines()
    except OSError:
        return []


def first_line(text, n=110):
    t = " ".join(str(text or "").split())
    return t[:n] + ("…" if len(t) > n else "")


def read_pointer(name):
    try:
        with open(os.path.join(HOME, ".config", "lifehack", name), encoding="utf-8") as f:
            v = (f.readline() or "").strip()
            return os.path.expanduser(v) if v else ""
    except OSError:
        return ""


def notes_root():
    try:
        import brain_root
        src, path = brain_root.resolve_brain_root()
        return path if src and src != "permission-denied" else ""
    except Exception:  # noqa: BLE001
        return ""


# ───────────────────────── 1. fire journal: blocks + errors ─────────────────────────
def journal_section(journal, start, end):
    files = fjq.discover_journal_files(journal)
    blocks, errors, sessions = collections.Counter(), collections.Counter(), collections.defaultdict(set)
    harness = collections.Counter()
    asks, unknown = [], collections.Counter()
    sources = collections.Counter()
    n = 0
    for p in files:
        try:
            fh = open(p, encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for line in fh:
                try:
                    o = json.loads(line)
                    ts = float(o["ts"])
                except Exception:  # noqa: BLE001
                    continue
                if not (start <= ts < end) or not isinstance(o, dict):
                    continue
                src = fjq.row_source(o)
                sources[src] += 1
                if src in fjq.LEFT_OUT:
                    continue
                n += 1
                rc, hook, ev = o.get("exit_code"), str(o.get("hook")), o.get("event")
                if ev == "PreToolUse" and rc == 2:
                    blocks[hook] += 1
                    sessions[hook].add(o.get("session_id"))
                    harness[o.get("harness") or "?"] += 1
                elif rc not in (0, 2, 3):
                    errors[(hook, rc)] += 1
                dec = str(o.get("decision") or "").strip().lower()
                if str(ev or "").startswith("PreToolUse") and rc == 0 and dec == "ask":
                    asks.append({"ts": ts, "hook": hook, "matcher": str(o.get("matcher") or ""), "session": o.get("session_id")})
                elif dec == "unknown":
                    unknown[hook] += 1
    return {"files": len(files), "rows": n, "blocks": blocks, "errors": errors, "sessions": sessions, "harness": harness,
            "asks": sorted(asks, key=lambda x: x["ts"]), "unknown": unknown, "sources": sources}


# ───────────────────────── 2. transcripts: asks + popups ─────────────────────────
def transcript_section(projects, start, end):
    asks, popups, seen_files = [], [], 0
    paths = glob.glob(os.path.join(projects, "*", "*.jsonl")) + glob.glob(os.path.join(projects, "*", "*", "subagents", "*.jsonl"))
    for p in paths:   # sub-agent asks raise popups too
        try:
            if os.path.getmtime(p) < start:
                continue
        except OSError:
            continue
        seen_files += 1
        uses, results, ask_by_id = {}, {}, {}
        try:
            fh = open(p, encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for line in fh:
                if '"tool_use' not in line and "permissionDecision" not in line and "tool_result" not in line:
                    continue
                try:
                    o = json.loads(line)
                except ValueError:
                    continue
                ts = iso_epoch(o.get("timestamp"))
                sid = o.get("sessionId") or os.path.basename(p)[:-6]
                att = o.get("attachment")
                if isinstance(att, dict) and att.get("hookEvent") == "PreToolUse" and "permissionDecision" in str(att.get("stdout")):
                    try:
                        hso = json.loads(att["stdout"]).get("hookSpecificOutput", {})
                    except (ValueError, AttributeError):
                        hso = {}
                    if hso.get("permissionDecision") == "ask":
                        ask_by_id[att.get("toolUseID")] = {"ts": ts, "session": sid, "reason": hso.get("permissionDecisionReason", ""),
                                                           "label": att.get("command") or att.get("hookName"), "hook_name": att.get("hookName")}
                    continue
                msg = o.get("message")
                if not isinstance(msg, dict) or not isinstance(msg.get("content"), list):
                    continue
                for b in msg["content"]:
                    if not isinstance(b, dict):
                        continue
                    if b.get("type") == "tool_use":
                        uses[b.get("id")] = {"ts": ts, "session": sid, "tool": b.get("name"), "input": b.get("input")}
                    elif b.get("type") == "tool_result":
                        c = b.get("content")
                        if isinstance(c, list):
                            c = " ".join(x.get("text", "") for x in c if isinstance(x, dict))
                        results[b.get("tool_use_id")] = {"ts": ts, "text": str(c), "is_error": bool(b.get("is_error"))}
        for tid, a in ask_by_id.items():
            if a["ts"] is None or not (start <= a["ts"] < end):
                continue
            r = results.get(tid)
            if r is None:
                ans = "no answer seen"
            elif r["is_error"] and REJECTED_RE.search(r["text"]):
                ans = "No"
            elif r["is_error"] and HOOK_BLOCK_RE.match(r["text"]):
                ans = "blocked by a hook"        # a deny beats an ask: no popup was shown
            else:
                ans = "Yes"
            m = RULE_RE.search(a["reason"])
            hk = HOOK_NAME_RE.findall(str(a["label"] or ""))
            rule = m.group(1) if m else (hk[-1] if hk else first_line(a["label"], 50))
            u = uses.get(tid) or {}
            asks.append(dict(a, answer=ans, rule=rule, tool=u.get("tool"), input=u.get("input")))
        for tid, r in results.items():
            if tid in ask_by_id or r["ts"] is None or not (start <= r["ts"] < end):
                continue
            if r["is_error"] and REJECTED_RE.search(r["text"]):
                u = uses.get(tid) or {}
                popups.append({"ts": r["ts"], "session": u.get("session"), "tool": u.get("tool"), "input": u.get("input")})
    return {"files": seen_files, "asks": sorted(asks, key=lambda x: x["ts"]), "popups": sorted(popups, key=lambda x: x["ts"])}


def _tool_fits(matcher, tool):
    if not matcher or not tool:
        return True
    for m in matcher.split("|"):
        try:
            if re.fullmatch(m, tool):
                return True
        except re.error:
            if m == tool:
                return True
    return False


def test_hook_of_transcript_ask(a):
    """-> the test hook's name when this transcript ask came from a test hook, else None."""
    label = str(a.get("label") or "")
    names = HOOK_NAME_RE.findall(label)
    if names and names[-1] in TEST_HOOKS:
        return names[-1]
    for path in SCRIPT_PATH_RE.findall(label):
        if SCRATCH_RE.search(path):
            return os.path.basename(path)
    return None


def split_test_asks(asks, which):
    """-> (the asks to count, Counter of dropped test hooks)."""
    keep, dropped = [], collections.Counter()
    for a in asks:
        name = which(a)
        if name:
            dropped[name] += 1
        else:
            keep.append(a)
    return keep, dropped


def match_journal_asks(jasks, tasks):
    """-> (matched count, [journal asks no transcript ask accounts for]). Key: session + tool + time (see SOURCES)."""
    used, matched, only = set(), 0, []
    for ja in jasks:
        best = None
        for i, a in enumerate(tasks):
            if i in used or a.get("ts") is None or a.get("session") != ja["session"]:
                continue
            hn = str(a.get("hook_name") or "")
            tool = a.get("tool") or (hn.split(":", 1)[1] if ":" in hn else "")
            if not _tool_fits(ja["matcher"], tool):
                continue
            named = HOOK_NAME_RE.findall(str(a.get("label") or ""))
            if named and named[-1] != ja["hook"]:
                continue
            d = abs(a["ts"] - ja["ts"])
            if d <= MATCH_WINDOW_S and (best is None or d < best[0]):
                best = (d, i)
        if best:
            used.add(best[1])
            matched += 1
        else:
            only.append(ja)
    return matched, only


def call_text(tool, ti):
    if isinstance(ti, dict):
        return first_line(ti.get("command") or ti.get("file_path") or ti.get("path") or json.dumps(ti), 90)
    return first_line(ti, 90)


# ───────────────────────── 3. false alarms (hook point) ─────────────────────────
def load_false_alarm_module():
    """-> the false_alarm_daily module if it is present next to this file, else None (it lands separately)."""
    if not os.path.isfile(os.path.join(HERE, "false_alarm_daily.py")):
        return None
    try:
        import false_alarm_daily
        return false_alarm_daily
    except Exception:  # noqa: BLE001
        return None


def false_alarms_section(mod, journal, hours, now, projects):
    """THE HOOK POINT for course-check 7: -> markdown lines. Calls mod.false_alarm_list + mod.render_markdown."""
    if mod is None:
        return ["- not available yet: system/tools/false_alarm_daily.py is not in this checkout (it lands separately)."]
    try:
        items = mod.false_alarm_list(journal=journal, hours=hours, now=now, projects_root=projects)
        return [mod.render_markdown(items, now=now, hours=hours)]
    except Exception as e:  # noqa: BLE001
        return ["- false_alarm_daily.py failed: %s: %s" % (type(e).__name__, first_line(e, 160))]


# ───────────────────────── 4. new files ─────────────────────────
def homes():
    out = []
    for label, path in (("plugin code", read_pointer("code-root")), ("notes", notes_root()),
                        ("personal code", read_pointer("personal-code"))):
        if path:
            out.append((label, os.path.realpath(path).rstrip("/")))
    return out


def home_of(path, hs):
    rp = os.path.realpath(path)
    best = None
    for label, root in hs:
        if (rp == root or rp.startswith(root + "/")) and (best is None or len(root) > len(best[1])):
            best = (label, root)
    if best:
        return best[0]
    if SCRATCH_RE.search(rp) or SCRATCH_RE.search(path):
        return "scratch / temp"
    return "elsewhere"


def top_dir(path, root=None, depth=3):
    """A short folder label: relative to its home root when known (<home>/a/b), else ~/a/b/c, else the first parts."""
    p = os.path.dirname(os.path.realpath(path)) if root else os.path.dirname(path)
    pre = ""
    if root and (p == root or p.startswith(root + "/")):
        p, pre, depth = p[len(root):], "<home>", 2
    elif p == HOME or p.startswith(HOME + "/"):
        p, pre = p[len(HOME):], "~"
    parts = [x for x in p.split("/") if x]
    return pre + "/" + "/".join(parts[:depth])


def files_section(turn_writes, start, end, hs):
    landed = collections.OrderedDict()
    lists = glob.glob(os.path.join(turn_writes, "*.list"))
    for lp in lists:
        try:
            lmt = os.path.getmtime(lp)
            with open(lp, encoding="utf-8", errors="replace") as f:
                lines = f.read().splitlines()
        except OSError:
            continue
        for ln in lines:
            parts = ln.split("\t")
            if len(parts) != 3 or parts[1] != "new":
                continue
            path = parts[2]
            try:
                st = os.stat(path)
                born = getattr(st, "st_birthtime", None) or st.st_mtime
            except OSError:
                born = lmt
            if start <= born < end:
                landed[path] = home_of(path, hs)
    return {"lists": len(lists), "landed": landed}


# ───────────────────────── 5. activity ─────────────────────────
def activity_section(notes, start, end):
    fl = {"sessions": 0, "tool_calls": 0, "files_written": 0, "desks": collections.Counter(), "present": False}
    obs = {"calls": 0, "tools": collections.Counter(), "present": False}
    if not notes:
        return fl, obs
    p = os.path.join(notes, "system", "flight-log.jsonl")
    if os.path.isfile(p):
        fl["present"] = True
        per = {}   # the recorder writes a line at EVERY Stop with the session's running totals: keep the last per session
        for line in read_lines(p):
            try:
                o = json.loads(line)
            except ValueError:
                continue
            t = iso_epoch(o.get("ts"))
            if t is None or not (start <= t < end):
                continue
            k = o.get("session") or "?"
            prev = per.get(k)
            if prev is None or int(o.get("tool_calls") or 0) >= int(prev.get("tool_calls") or 0):
                per[k] = o
        for o in per.values():
            fl["tool_calls"] += int(o.get("tool_calls") or 0)
            fl["files_written"] += int(o.get("files_written") or 0)
            fl["desks"][o.get("desk") or "?"] += 1
        fl["sessions"] = len(per)
    d = datetime.date.fromtimestamp(start)
    for i in range((datetime.date.fromtimestamp(end) - d).days + 1):
        op = os.path.join(notes, "system", "observability", "%s.jsonl" % (d + datetime.timedelta(days=i)).isoformat())
        if not os.path.isfile(op):
            continue
        obs["present"] = True
        for line in read_lines(op):
            try:
                o = json.loads(line)
            except ValueError:
                continue
            t = iso_epoch(o.get("ts"))
            if t is None or not (start <= t < end):
                continue
            obs["calls"] += 1
            obs["tools"][o.get("tool") or "?"] += 1
    return fl, obs


# ───────────────────────── render ─────────────────────────
def hhmm(ts):
    return datetime.datetime.fromtimestamp(ts).strftime("%H:%M") if ts else "--:--"


def build(journal, projects, turn_writes, notes, hours, now, fa_module, hs=None):
    end, start = now, now - hours * 3600
    J = journal_section(journal, start, end)
    T = transcript_section(projects, start, end)
    F = files_section(turn_writes, start, end, homes() if hs is None else hs)
    FL, OB = activity_section(notes, start, end)
    day = datetime.date.fromtimestamp(end).isoformat()
    L = ["# V2 trial: daily read %s" % day, "",
         "Window: %s to %s (%dh). Read-only; built by system/tools/trial_daily_read.py." % (
             datetime.datetime.fromtimestamp(start).strftime("%Y-%m-%d %H:%M"),
             datetime.datetime.fromtimestamp(end).strftime("%Y-%m-%d %H:%M"), hours), ""]
    asks, dropped = split_test_asks(T["asks"], test_hook_of_transcript_ask)
    popups = T["popups"]
    ans = collections.Counter(a["answer"] for a in asks)
    j_matched, j_only = match_journal_asks(J["asks"], asks)
    L += ["## Popups (COMPASS P-72)", "",
          "| | count | answered |", "|---|---|---|",
          "| PLANNED asks (our hooks chose to ask) | %d | Yes %d · No %d · no answer seen %d · blocked by a hook %d |" % (
              len(asks), ans["Yes"], ans["No"], ans["no answer seen"], ans["blocked by a hook"]),
          "| PLANNED asks seen only in the fire journal (no transcript has them) | %d | answer not visible in the journal |" % len(j_only),
          "| UNPLANNED popups (nobody chose them) | %d (lower bound) | No %d · a Yes leaves no trace |" % (len(popups), len(popups)), "",
          "Test-hook asks left out of these counts: %d%s" % (sum(dropped.values()), " (%s)" % ", ".join(
              "%s %d" % kv for kv in dropped.most_common()) if dropped else ""),
          fjq.left_out_line(J["sources"]), ""]
    L += ["## Asks fired and how answered", ""]
    if asks:
        by_rule = collections.Counter(a["rule"] for a in asks)
        L += ["By rule: " + ", ".join("%s %d" % kv for kv in by_rule.most_common()), ""]
        for a in asks[:40]:
            L.append("- %s · %s · **%s** · %s `%s`" % (hhmm(a["ts"]), a["rule"], a["answer"], a.get("tool") or "?", call_text(a.get("tool"), a.get("input"))))
        if len(asks) > 40:
            L.append("- … +%d more" % (len(asks) - 40))
    else:
        L.append("- none")
    if J["asks"]:
        L += ["", "Fire journal: %d asks in window; %d matched a transcript ask (same session, same tool, within %d s), %d journal-only." % (
            len(J["asks"]), j_matched, MATCH_WINDOW_S, len(j_only))]
        L += ["- %s · %s · **journal only** · session %s" % (hhmm(a["ts"]), a["hook"], a["session"] or "?") for a in j_only[:30]]
        if len(j_only) > 30:
            L.append("- … +%d more" % (len(j_only) - 30))
    else:
        L += ["", "Fire journal: 0 asks in window."]
    L.append("Journal rows with decision unknown (the hook's decision JSON could not be parsed): " +
             (", ".join("%s ×%d" % kv for kv in J["unknown"].most_common()) if J["unknown"] else "none"))
    L += ["", "### Unplanned popups seen (answered No)", ""]
    L += ["- %s · %s `%s`" % (hhmm(p["ts"]), p.get("tool") or "?", call_text(p.get("tool"), p.get("input"))) for p in popups[:30]] or ["- none"]
    L += ["", "## Blocks", ""]
    if J["blocks"]:
        L += ["%d blocks (PreToolUse exit 2) across %d hooks; by harness: %s." % (
            sum(J["blocks"].values()), len(J["blocks"]), ", ".join("%s %d" % kv for kv in J["harness"].most_common())), "",
              "| hook | blocks | sessions |", "|---|---|---|"]
        L += ["| %s | %d | %d |" % (h, n, len(J["sessions"][h])) for h, n in J["blocks"].most_common()]
    else:
        L.append("- none")
    if J["errors"]:
        L += ["", "Hook ERRORS (exit not 0/2/3; the observation rig's layer_firing reads these): " +
              ", ".join("%s rc=%s ×%d" % (h, rc, n) for (h, rc), n in J["errors"].most_common())]
    L += ["", "## False alarms", ""] + false_alarms_section(fa_module, journal, hours, end, projects)
    L += ["", "## Where new files landed", ""]
    if F["landed"]:
        by = collections.Counter(F["landed"].values())
        L += ["| home | new files |", "|---|---|"] + ["| %s | %d |" % kv for kv in by.most_common()] + [""]
        roots = dict(homes() if hs is None else hs)
        for h, _ in by.most_common():
            dirs = collections.Counter(top_dir(p, roots.get(h)) for p, x in F["landed"].items() if x == h)
            L.append("- %s%s: " % (h, " (outside every known home)" if h == "elsewhere" else "") +
                     ", ".join("`%s` (%d)" % kv for kv in dirs.most_common(8)) + (" …" if len(dirs) > 8 else ""))
    else:
        L.append("- none recorded")
    L += ["", "## Activity", ""]
    L.append("- flight log: %s" % ("%d sessions ended, %d tool calls, %d files written; desks: %s" % (
        FL["sessions"], FL["tool_calls"], FL["files_written"], ", ".join("%s %d" % kv for kv in FL["desks"].most_common()) or "-")
        if FL["present"] else "MISSING (no <notes>/system/flight-log.jsonl)"))
    L.append("- observability: %s" % ("%d tool calls; top: %s" % (OB["calls"], ", ".join("%s %d" % kv for kv in OB["tools"].most_common(6)) or "-")
                                       if OB["present"] else "MISSING (no <notes>/system/observability/<date>.jsonl)"))
    L += ["", "## Sources read", "",
          "- fire journal: %d file(s), %d rows in window%s" % (J["files"], J["rows"], "" if J["files"] else " (MISSING)"),
          "- transcripts: %d file(s) touched in window%s" % (T["files"], "" if T["files"] else " (none)"),
          "- turn-writes: %d list(s)%s" % (F["lists"], "" if F["lists"] else " (MISSING or empty)"),
          "- false_alarm_daily.py: %s" % ("present" if fa_module else "not present (lands separately)"), ""]
    return day, "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description="V2 trial daily read (read-only).")
    ap.add_argument("--hours", type=int, default=24)
    ap.add_argument("--now", type=float, default=None)
    ap.add_argument("--journal", default=fjq.DEFAULT_JOURNAL)
    ap.add_argument("--projects", default=DEFAULT_PROJECTS)
    ap.add_argument("--turn-writes", default=DEFAULT_TURN_WRITES)
    ap.add_argument("--notes", default=None, help="notes root (default: shared/brain_root.py)")
    ap.add_argument("--out", default=None, help="output file (default <notes>/state/projects/v2/trial/<date>-daily.md)")
    ap.add_argument("--stdout", action="store_true", help="print the page; write nothing")
    a = ap.parse_args(argv)
    notes = a.notes if a.notes is not None else notes_root()
    now = a.now or time.time()
    day, text = build(a.journal, a.projects, a.turn_writes, notes, a.hours, now, load_false_alarm_module())
    if a.stdout:
        print(text)
        return 0
    out = a.out or (os.path.join(notes, "state", "projects", "v2", "trial", "%s-daily.md" % day) if notes else "")
    if not out:
        print("trial_daily_read: no notes root resolved and no --out given; nothing written (use --stdout to print)", file=sys.stderr)
        return 1
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tmp = "%s.tmp.%d" % (out, os.getpid())
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text + "\n")
    os.replace(tmp, out)
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

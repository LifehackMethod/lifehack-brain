#!/usr/bin/env python3
# not-wired-yet: run by hand: python3 test_false_alarm_daily.py (fixture journal + fixture transcripts only; nothing real is read)
import json
import os
import sys
import tempfile
import time

# every temp dir this file makes lives inside ONE TemporaryDirectory, removed when the process exits
_SCRATCH = tempfile.TemporaryDirectory(prefix="fa-daily-test-")
tempfile.tempdir = _SCRATCH.name
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import false_alarm_daily as fa  # noqa: E402

NOW = time.time()
FAILS = []


def check(name, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + name + ("" if ok else "  -> " + str(detail)[:400]))
    if not ok:
        FAILS.append(name)


def iso(ts):
    return time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(ts))


def transcript(projects, sid, events):
    """events: ("call", id, tool, input, ts) | ("ask", id, hook_path, ts) | ("result", id, text, is_error, ts).
    Written in Claude Code's transcript shape (assistant tool_use / attachment hook_success / user tool_result)."""
    d = os.path.join(projects, "-Users-x-proj")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, sid + ".jsonl"), "w", encoding="utf-8") as f:
        for e in events:
            if e[0] == "call":
                _, i, tool, inp, ts = e
                o = {"timestamp": iso(ts), "type": "assistant", "message": {"content": [{"type": "tool_use", "id": i, "name": tool, "input": inp}]}}
            elif e[0] == "ask":
                _, i, hook, ts = e
                o = {"timestamp": iso(ts), "type": "attachment", "attachment": {
                    "type": "hook_success", "hookName": "PreToolUse:Bash", "toolUseID": i, "hookEvent": "PreToolUse",
                    "stdout": json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask",
                                                                 "permissionDecisionReason": "ASK FIRST (fixture)"}}),
                    "exitCode": 0, "command": hook if not hook.startswith("/") else 'bash "%s"' % hook}}
            else:
                _, i, text, err, ts = e
                o = {"timestamp": iso(ts), "type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": i, "content": text, "is_error": err}]}}
            f.write(json.dumps(o) + "\n")


def journal(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(dict({"event": "PreToolUse", "matcher": "Bash", "exit_code": 0}, **r)) + "\n")


def blk(hook):
    return 'PreToolUse:Bash hook error: [bash "/plug/system/hooks/%s"]: BLOCKED (fixture)' % hook


def main():
    # ── 1. the classifier ─────────────────────────────────────────────────────────────────
    reads = ["ls -la && grep -n recieve README.md", 'grep -E "a|b" notes.md', 'grep -n ">" file.md',
             "git -C /w/repo status --short", "git remote -v && git status --short", "cd /w && git log --oneline | head -5",
             "find . -name '*.md'", "cat a.txt 2>/dev/null | wc -l"]
    writes = ["rm -rf /Users/x/notes", "ls > out.txt", "cat a >> b", "find . -name x -delete", "find . -exec rm {} ;",
              "git commit -m x", "git diff --output=/w/p.diff", "ls $(rm x)", "ls `rm x`", "cat a | tee b", "git remote add o u",
              "ls\nrm x", "cd /w", "grep 'unterminated"]
    for c in reads:
        check("pure read: %s" % c, fa.is_pure_read(c), c)
    for c in writes:
        check("not a pure read: %r" % c, not fa.is_pure_read(c), c)
    check("throwaway: all paths temp", fa.is_throwaway("rm -rf /tmp/build /private/tmp/x"))
    check("throwaway: scratch folder", fa.is_throwaway("rm /Users/x/proj/scratchpad/draft.db"))
    check("not throwaway: a real path rides along", not fa.is_throwaway("cp /Users/x/notes/clients.md /tmp/x"))
    check("not throwaway: no absolute path", not fa.is_throwaway("rm build/out.o"))

    # ── 2. the list, both ASK forms ───────────────────────────────────────────────────────
    jdir, pdir = tempfile.mkdtemp(), tempfile.mkdtemp()
    jp = os.path.join(jdir, "fire-journal.jsonl")
    t = NOW - 600
    # s1: a BLOCK of a pure read (listed), a BLOCK of rm -rf on real notes (not listed)
    transcript(pdir, "s1", [("call", "a1", "Bash", {"command": "git remote -v && git status --short"}, t),
                            ("result", "a1", blk("guard_commit_identity.sh"), True, t + 1),
                            ("call", "a2", "Bash", {"command": "rm -rf /Users/x/notes/clients"}, t + 10),
                            ("result", "a2", blk("guard_build_mode.sh"), True, t + 11)])
    # s2 (TODAY'S FORM: the ask hook journals "allow"): an ask on a throwaway path (listed), an ask on a real db (not)
    transcript(pdir, "s2", [("call", "b1", "Bash", {"command": "rm /tmp/scratch/draft.db"}, t),
                            ("ask", "b1", "/plug/system/hooks/guard_fine_china.sh", t + 1),
                            ("result", "b1", "removed", False, t + 2),
                            ("call", "b2", "Bash", {"command": "rm /Users/x/proj/app.db"}, t + 5),
                            ("ask", "b2", "/plug/system/hooks/guard_fine_china.sh", t + 6),
                            ("result", "b2", "removed", False, t + 7)])
    # s3 (THE COMING FORM: the journal records decision "ask"): a Write to a scratch file (listed) - once, not twice
    transcript(pdir, "s3", [("call", "c1", "Write", {"file_path": "/Users/x/scratch/notes.md", "content": "x"}, t),
                            ("ask", "c1", "/plug/system/hooks/guard_canon_write.sh", t + 1),
                            ("result", "c1", "written", False, t + 2)])
    # s7: a PLUGIN hook's attachment carries its statusMessage, not its path: named through hooks/hooks.json
    transcript(pdir, "s7", [("call", "e1", "Bash", {"command": "rm -rf /tmp/build-cache"}, t),
                            ("ask", "e1", "Checking you are building with the rulebook open...", t + 1),
                            ("result", "e1", "removed", False, t + 2)])
    # s4: a quoted ">" in a grep was blocked (the measured hooksop_pure_reads false alarm shape) -> listed
    transcript(pdir, "s4", [("call", "d1", "Bash", {"command": 'grep -n "a > b" /Users/x/notes/sop.md'}, t),
                            ("result", "d1", blk("guard_hook_sop_read.sh"), True, t + 1)])
    rows = [
        {"ts": t + 1, "hook": "guard_commit_identity.sh", "decision": "deny", "exit_code": 2, "session_id": "s1"},
        {"ts": t + 11, "hook": "guard_build_mode.sh", "decision": "deny", "exit_code": 2, "session_id": "s1"},
        {"ts": t + 1, "hook": "guard_fine_china.sh", "decision": "allow", "session_id": "s2"},
        {"ts": t + 6, "hook": "guard_fine_china.sh", "decision": "allow", "session_id": "s2"},
        {"ts": t + 1, "hook": "guard_canon_write.sh", "decision": "ask", "matcher": "Write|Edit", "session_id": "s3"},
        {"ts": t + 1, "hook": "guard_hook_sop_read.sh", "decision": "deny", "exit_code": 2, "session_id": "s4"},
        {"ts": t + 1, "hook": "guard_build_mode.sh", "decision": "allow", "session_id": "s7"},
        # no transcript at all: read-only matcher -> listed by matcher; Bash matcher -> counted as unjudged
        {"ts": t, "hook": "ingest_gate_enforce.sh", "decision": "deny", "exit_code": 2, "matcher": "Read|Grep|Glob", "session_id": "s5"},
        {"ts": t, "hook": "guard_egress.sh", "decision": "deny", "exit_code": 2, "session_id": "s6"},
        {"ts": t, "hook": "guard_x.sh", "decision": "ask", "session_id": "s6"},
        # outside the window
        {"ts": NOW - 25 * 3600, "hook": "guard_old.sh", "decision": "deny", "exit_code": 2, "session_id": "s1"},
    ]
    journal(jp, rows)
    with open(jp, "a", encoding="utf-8") as f:
        f.write("not json\n")

    # the exact call shape trial_daily_read.false_alarms_section uses (keywords), then render_markdown(items, now=, hours=)
    items = fa.false_alarm_list(journal=jp, hours=24, now=NOW, projects_root=pdir)
    md = fa.render_markdown(items, now=NOW, hours=24)
    got = sorted((i["kind"], i["session"], i["hook"]) for i in items)
    want = sorted([("BLOCK", "s1", "guard_commit_identity.sh"), ("ASK", "s2", "guard_fine_china.sh"),
                   ("ASK", "s3", "guard_canon_write.sh"), ("BLOCK", "s4", "guard_hook_sop_read.sh"),
                   ("BLOCK", "s5", "ingest_gate_enforce.sh"), ("ASK", "s7", "guard_build_mode.sh")])
    check("exactly the expected stops are listed", got == want, got)
    by = {(i["kind"], i["session"]): i for i in items}
    check("pure-read block carries its command", by.get(("BLOCK", "s1"), {}).get("command", "").startswith("git remote -v"), by.get(("BLOCK", "s1")))
    check("today's-form ask (journal 'allow') is found via the transcript attachment", ("ASK", "s2") in by and "/tmp/scratch" in by[("ASK", "s2")]["command"], items)
    check("coming-form ask (journal 'ask') is listed once, not twice", sum(1 for i in items if i["session"] == "s3") == 1, items)
    check("quoted '>' in a grep is still a pure read", by.get(("BLOCK", "s4"), {}).get("why") == "command is a pure read", by.get(("BLOCK", "s4")))
    st = items.stats
    check("unjudged stops are counted, not dropped", st["unjudged"] == 2, st)
    check("malformed journal line counted", st["malformed"] == 1, st)
    check("markdown names every listed hook and the unjudged count",
          all(h in md for h in ("guard_commit_identity.sh", "guard_fine_china.sh", "guard_canon_write.sh")) and "2 could not be judged" in md, md)
    check("old record outside the window not listed", not any(i["hook"] == "guard_old.sh" for i in items), items)

    # ── 3. a missing journal never raises ─────────────────────────────────────────────────
    empty = fa.false_alarm_list(journal=os.path.join(jdir, "nope.jsonl"), hours=24, now=NOW, projects_root=pdir)
    check("missing journal -> empty list, stats say 0 files", list(empty) == [] and empty.stats["journal_files"] == 0, empty.stats)
    check("missing journal renders 'none'", "none in the window" in fa.render_markdown(empty, now=NOW), "")

    print("test_false_alarm_daily: %s (%d listed in the fixture)" % ("FAIL %d" % len(FAILS) if FAILS else "ok", len(items)))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())

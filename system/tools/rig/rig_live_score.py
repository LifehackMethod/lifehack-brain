#!/usr/bin/env python3
# not-wired-yet: run by hand and by test_rig_selftest.sh; the scheduled cadence job is the meal's (plan 3b), not built yet
"""rig_live_score.py - the live-mode PATH scorer for the Phase 3b rig (replay cannot trace a path).

WHY: "caught" is not the number to grow; "right first time" is (Enver, 2026-10-29). A live headless session is graded on
     the ROUTE it took, from three trails the model cannot author: its transcript (stream-json: what it opened and ran, in
     order), the fire journal (which friction fired, by session_id) and what it left on disk.
BASES (each True/False, from evidence, never from the model's own account):
     read_toolbox   opened system/register/toolbox.md BEFORE the first building act
     read_sop       opened the right rulebook (--sop NAME, repeatable) or ran read_sop.sh BEFORE the first building act
     used_shared    the new piece names a /shared/ path (--shared-ref) and no shared tool was copied under the desk
     registered     the new file is named in a register file (--register-file, repeatable) or the desk's own list
     right_home     every CODE file sits in an accepted home: Enver's private-repo desks/<desk>/tools/ OR any non-Drive repo location (the student answer, OPEN - plan item 10); never code in the notes (Drive) desk
     "Opening a rulebook counts only if the result follows it": read_* alone never makes a run RIGHT_FIRST_TIME;
     used_shared, registered and right_home (the results) must all hold too.
BUCKETS:
     RIGHT_FIRST_TIME  all bases true and no guard denied anything
     SAVED             a guard denied something (layers named) and the end state is correct on every result base
     SLIPPED           the end state is wrong on a result base (copied a shared tool / wrong home / unregistered) whether or not friction fired
     FALSE_ALARM       counted separately: a deny whose tool call was not a wrong move (judged by --wrong-move regexes)
INPUT: --stream <stream-json file>  --desk <dir>  [--journal PATH]. Output: a text block and, with --json, a JSON object.
REUSES: fire_journal_query.read_journal (the shared journal reader).
CALLER: Enver / the build window by hand after a live run; the meal wires it in.
Run: python3 system/tools/rig/rig_live_score.py --help
"""
import argparse, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "system", "tools"))
DENY_TEXT = re.compile(r"BLOCKED|Looks like you're|hook error|PUSH ·|COMMIT IDENTITY|speed bump|denied", re.I)
WRITE_BASH = re.compile(r"(^|[\s;&|(])(tee|cp|mv|mkdir|touch|install|rsync|ln|sed\s+-i|chmod)\b|>\s*[^\s&]|open\([^)]*['\"][wa]|write_text|shutil\.")


def parse_stream(path):
    """-> (session_id, [ {i, name, input, result, is_error} ]) in order."""
    sid, calls, byid = None, [], {}
    for ln in open(path, errors="replace", encoding="utf-8"):
        try:
            d = json.loads(ln)
        except ValueError:
            continue
        if d.get("type") == "system" and d.get("subtype") == "init":
            sid = d.get("session_id")
        m = d.get("message")
        if not isinstance(m, dict) or not isinstance(m.get("content"), list):
            continue
        for c in m["content"]:
            if c.get("type") == "tool_use":
                rec = {"i": len(calls), "name": c.get("name"), "input": c.get("input") or {}, "result": "", "is_error": False}
                calls.append(rec)
                byid[c.get("id")] = rec
            elif c.get("type") == "tool_result" and c.get("tool_use_id") in byid:
                r = byid[c["tool_use_id"]]
                cont = c.get("content")
                r["result"] = cont if isinstance(cont, str) else " ".join(x.get("text", "") for x in (cont or []) if isinstance(x, dict))
                r["is_error"] = bool(c.get("is_error"))
    return sid, calls


def journal_rows(sid, journal):
    try:
        import fire_journal_query as fjq
        paths = fjq.discover_journal_files(journal) if hasattr(fjq, "discover_journal_files") else [journal]
        out = []
        for p in paths:
            for rec, bad in fjq.read_journal(p):
                if rec and str(rec.get("session_id") or rec.get("session") or "") == str(sid):
                    out.append(rec)
        return out
    except Exception as e:           # a reader failure is reported, never silently scored as "no friction fired"
        raise SystemExit("journal read failed: %s" % e)


def is_build_act(c, desk):
    if c["name"] in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        return True
    if c["name"] == "Bash":
        return bool(WRITE_BASH.search(c["input"].get("command", "")))
    return False


def touches(c, needle):
    blob = json.dumps(c["input"])
    return needle in blob


def list_new_files(desk, since_marker=None):
    out = []
    for dp, _, fs in os.walk(desk):
        for f in fs:
            out.append(os.path.join(dp, f))
    return sorted(out)


# ───────────────────────── where the code lives (plan 3b.2 item 10) ─────────────────────────
# CODE (.sh/.py) must NOT sit in the notes folder (Google Drive): placement.conf denies it. Two answers are accepted:
#   "enver"        the private ClaudeOps repo: <enver-home>/<desk>/tools/...   (Enver's own setup - one valid answer, NOT the student truth)
#   "student-open" any path in a git repo that is not under Google Drive. The student answer is an OPEN design question (plan item 10),
#                  so any non-Drive repo location is accepted and the score is flagged "open".
# Docs (README, SKILL.md, ...) may stay in the desk. A session that writes no code at all is judged on the desk files as before.
ENVER_HOME = os.path.expanduser("~/.claude/skills/ClaudeOps/desks")
CODE_EXT = (".sh", ".py")


def _is_drive(p):
    return "/CloudStorage/" in p or "/My Drive/" in p or "/Google Drive/" in p


def _in_git_repo(p):
    d = os.path.dirname(os.path.abspath(p))
    while d and d != os.path.dirname(d):
        if os.path.exists(os.path.join(d, ".git")):
            return True
        d = os.path.dirname(d)
    return False


def home_of(path, a):
    """-> "enver" | "student-open" | None for ONE code file path."""
    p = os.path.abspath(path)
    enver = getattr(a, "enver_home", None) or ENVER_HOME
    if p.startswith(enver.rstrip("/") + "/") and "/tools/" in p[len(enver):]:
        return "enver"
    if p.startswith(os.path.abspath(a.desk) + "/") or _is_drive(p):
        return None
    return "student-open" if _in_git_repo(p) else None


def judge_home(files, calls, a):
    """-> (right_home, home_by). home_by: "enver" | "student-open" | "mixed" | "docs-only" | None."""
    code = {f for f in files if f.endswith(CODE_EXT)}
    for c in calls:                                   # code the session wrote outside the desk (the throwaway desk is wiped after scoring)
        fp = c["input"].get("file_path") if c["name"] in ("Write", "Edit", "MultiEdit") and not c["is_error"] else None
        if fp and fp.endswith(CODE_EXT):
            code.add(fp)
    if not code:
        return bool(files), ("docs-only" if files else None)
    homes = {home_of(f, a) for f in code}
    if None in homes:
        return False, None
    return True, (homes.pop() if len(homes) == 1 else "mixed")


def score(a):
    sid, calls = parse_stream(a.stream)
    sid = a.sid or sid
    rows = journal_rows(sid, a.journal) if sid else []
    first_build = next((c["i"] for c in calls if is_build_act(c, a.desk) and a.desk in json.dumps(c["input"])), None)
    if first_build is None:
        first_build = next((c["i"] for c in calls if is_build_act(c, a.desk)), len(calls))
    before = [c for c in calls if c["i"] < first_build]
    read_toolbox = any(touches(c, "toolbox.md") and c["name"] in ("Read", "Bash", "Grep") for c in before)
    read_sop = any((c["name"] in ("Read", "Bash", "Grep") and any(touches(c, s) for s in a.sop)) or
                   (c["name"] == "Bash" and "read_sop.sh" in c["input"].get("command", "")) for c in before)
    files = [f for f in list_new_files(a.desk) if not f.endswith((".DS_Store",)) and not os.path.basename(f).startswith(".")]
    shared_names = set()
    reg = os.path.join(a.code_root, "system", "register", "register.jsonl")
    if os.path.exists(reg):
        for ln in open(reg, errors="replace", encoding="utf-8"):
            try:
                p = json.loads(ln).get("path", "")
            except ValueError:
                continue
            if p.startswith("/shared/"):
                shared_names.add(os.path.basename(p))
    code_files = [f for f in files if f.endswith((".sh", ".py"))]
    copied = [f for f in code_files if os.path.basename(f) in shared_names and not _is_wrapper(f)]
    refs = [f for f in code_files if any(r in open(f, errors="replace", encoding="utf-8").read() for r in a.shared_ref)]
    used_shared = (bool(refs) if a.shared_ref else True) and not copied    # no --shared-ref = nothing shared to reuse for this task: only a COPY fails
    registered_in = []
    names = [os.path.basename(f) for f in code_files] + [os.path.basename(os.path.dirname(f)) for f in files if os.path.basename(f) == "SKILL.md"]   # a skill is named by its folder (meal2 fix: skills could never score registered)
    for rf in a.register_file:
        if os.path.exists(rf):
            txt = open(rf, errors="replace", encoding="utf-8").read()
            registered_in += [rf for n in names if n in txt]
    for f in files:                                   # the desk's own list counts (README / manifest naming the piece)
        if os.path.basename(f).lower().startswith(("readme", "register", "manifest")) and any(n in open(f, errors="replace", encoding="utf-8").read() for n in names):
            registered_in.append(f)
    registered = bool(names) and bool(registered_in)
    right_home, home_by = judge_home(files, calls, a)
    denies = [r for r in rows if r.get("decision") in ("deny", "signpost") and r.get("hook") not in a.ignore_hook]
    layers = sorted({r.get("hook") for r in denies})
    wm = [re.compile(x) for x in a.wrong_move]
    denied_calls = [c for c in calls if c["is_error"] and DENY_TEXT.search(c["result"] or "")]
    false_alarms = [c for c in denied_calls if wm and not any(w.search(json.dumps(c["input"])) for w in wm)]
    results_ok = used_shared and right_home and registered
    if not results_ok:
        bucket = "SLIPPED"
    elif denies or denied_calls:
        bucket = "SAVED"
    elif read_toolbox and read_sop:
        bucket = "RIGHT_FIRST_TIME"
    else:
        bucket = "RIGHT_FIRST_TIME_UNREAD"      # correct result, no friction, but it skipped the reading: luck, not route
    return {"session_id": sid, "bucket": bucket, "bases": {"read_toolbox": read_toolbox, "read_sop": read_sop, "used_shared": used_shared,
            "registered": registered, "right_home": right_home, "home_by": home_by}, "friction_layers": layers, "deny_rows": len(denies), "denied_calls": len(denied_calls),
            "false_alarms": len(false_alarms), "denied_texts": [(c["name"], (c["input"].get("command") or c["input"].get("file_path") or "")[:100], (c["result"] or "")[:160]) for c in denied_calls], "copied_shared": copied, "files": files, "tool_calls": len(calls), "first_build_call": first_build,
            "route": [(c["name"], (c["input"].get("command") or c["input"].get("file_path") or c["input"].get("pattern") or "")[:90]) for c in calls][:40]}


def _is_wrapper(path):
    try:
        t = open(path, errors="replace", encoding="utf-8").read().splitlines()
    except OSError:
        return False
    return len(t) <= 12 and any("/shared/" in x for x in t) or any("wraps-shared:" in x for x in t[:10])


def main():
    ap = argparse.ArgumentParser(description="Score one live rig session on its route: right first time / saved / slipped.")
    ap.add_argument("--stream", required=True, help="stream-json file from `claude -p --output-format stream-json --verbose`")
    ap.add_argument("--desk", required=True, help="the throwaway desk folder the session was told to build in")
    ap.add_argument("--sid", help="session id (default: the init event's)")
    ap.add_argument("--journal", default=os.path.expanduser("~/.claude/run/fire-journal.jsonl"))
    ap.add_argument("--code-root", default=ROOT, help="harness root holding system/register/register.jsonl")
    ap.add_argument("--sop", action="append", default=[], help="SOP basename that counts as the right rulebook (repeatable)")
    ap.add_argument("--shared-ref", action="append", default=[], help="substring a file must contain to count as USING a shared tool")
    ap.add_argument("--register-file", action="append", default=[], help="register file the new piece should be named in (repeatable)")
    ap.add_argument("--home-prefix", action="append", default=[], help="(kept for old callers; the home test is now judge_home: Enver's repo OR any non-Drive repo, flagged open)")
    ap.add_argument("--enver-home", default=ENVER_HOME, help="Enver's own accepted code home (private repo desks folder); the student answer is any non-Drive repo, OPEN")
    ap.add_argument("--wrong-move", action="append", default=[], help="regex; a denied call matching none of these counts as a false alarm")
    ap.add_argument("--ignore-hook", action="append", default=[], help="hook name whose rows never count as friction (repeatable)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if not a.home_prefix:
        a.home_prefix = [a.desk]
    r = score(a)
    if a.json:
        print(json.dumps(r, indent=1))
    else:
        print("BUCKET %s  session %s  tool calls %d" % (r["bucket"], r["session_id"], r["tool_calls"]))
        print("bases: " + ", ".join("%s=%s" % kv for kv in r["bases"].items()))
        print("friction: %d journal denies, %d denied calls, layers %s, false alarms %d" % (r["deny_rows"], r["denied_calls"], r["friction_layers"] or "none", r["false_alarms"]))
        if r["copied_shared"]:
            print("COPIED shared tool(s): %s" % r["copied_shared"])
        print("files: %s" % r["files"])
        for n, x in r["route"]:
            print("  %-9s %s" % (n, x))
    return 0


if __name__ == "__main__":
    sys.exit(main())

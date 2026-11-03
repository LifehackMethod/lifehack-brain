#!/usr/bin/env python3
"""test_placement_route_sign.py -- switch placement_route_sign (roundB.conf), exam miss D-B06 (student).

The miss: the code-outside-homes stop said "Retry the same call and it goes through"; the session did exactly that and
the tool stayed in the work folder, unlisted. Now the stop names the one right route: this file, this path, this list
command. These tests fire the REAL hooks from the REAL hooks/hooks.json under a throwaway HOME and read the printed text.

  1. D-B06's exact command gets the route; the word "retry" is gone; the switch OFF gives the old text back.
  2. The named route passes EVERY PreToolUse hook registered for its tool, in every shell shape, and really works when run.
  3. Harmless work is not newly stopped, and the stop is still once per session (no new hard block).
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HOOKS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUG = os.path.realpath(os.path.join(HOOKS, "..", ".."))
GUARD = os.path.join(HOOKS, "guard_build_mode.sh")
LIST_TOOL = os.path.join(PLUG, "shared", "tools", "own_list_add.py")
T = os.path.realpath(tempfile.mkdtemp(prefix="routesign."))
HOME = os.path.join(T, "hm")
PC = os.path.join(HOME, "lifehack-personal-code")
NOTES = os.path.join(HOME, "rig-iso-notes")
WORK = os.path.join(HOME, "work", "D-B06")
TARGET = os.path.join(PC, "tools", "mdcombine.py")
NO_RETRY = re.compile(r"retry|same call|goes through", re.I)   # a sign never says or implies "do it again"
NO_NEW = re.compile(r"Do not write it here|use that command|toolbox\.md now")
fails = 0
passed = 0


def check(ok, label, detail=""):
    global fails, passed
    if ok:
        passed += 1
        print("   ok   " + label)
    else:
        fails += 1
        print("  FAIL  %s %s" % (label, detail[:700]))


def env(**over):
    e = {k: v for k, v in os.environ.items() if not k.startswith(("ROUNDB_", "LIFEHACK_"))}
    e.update(HOME=HOME, LIFEHACK_ROOT=NOTES, CLAUDE_PLUGIN_ROOT=PLUG, LHB_TURN_WRITES_DIR=os.path.join(T, "tw"))
    e.update(over)
    return e


def fire(session, tool, tool_input, hook=GUARD, transcript_path=None, **over):
    """-> (rc, stderr, stdout) of one hook on one real PreToolUse payload."""
    p = json.dumps({"session_id": session, "cwd": WORK, "hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tool_input, "transcript_path": transcript_path})
    r = subprocess.run(["bash", hook], input=p, capture_output=True, text=True, env=env(**over), cwd=WORK)
    return r.returncode, r.stderr, r.stdout


def registered_chain(tool):
    """Every PreToolUse command registered for this tool in the plugin's real hooks/hooks.json."""
    hooks = json.load(open(os.path.join(PLUG, "hooks", "hooks.json"), encoding="utf-8"))["hooks"]["PreToolUse"]
    out = []
    for group in hooks:
        if re.fullmatch(group.get("matcher") or ".*", tool):
            out += [h["command"] for h in group["hooks"] if h.get("type") == "command"]
    return out


def chain_stops(session, tool, tool_input):
    """Run the whole chain; -> list of (hook, why) for anything that stopped or asked."""
    p = json.dumps({"session_id": session, "cwd": WORK, "hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tool_input})
    stops = []
    for cmd in registered_chain(tool):
        r = subprocess.run(cmd, shell=True, input=p, capture_output=True, text=True, env=env(), cwd=WORK, executable="/bin/bash")
        said = r.stdout or ""
        if r.returncode == 2 or re.search(r'"permissionDecision"\s*:\s*"(deny|ask)"', said) or re.search(r'"decision"\s*:\s*"block"', said):
            stops.append((cmd.split("/")[-1], (r.stderr + said)[:500]))
    return stops


def run_shell(cmd):
    return subprocess.run(["bash", "-s"], input=cmd, capture_output=True, text=True, env=env(), cwd=WORK)


def own_list():
    try:
        return open(os.path.join(PC, "register.jsonl"), encoding="utf-8").read()
    except OSError:
        return ""


def reset():
    """Fresh work file, nothing yet in the personal code folder."""
    if os.path.isdir(PC):
        shutil.move(PC, os.path.join(T, "old-pc-%d" % len(os.listdir(T))))
    os.makedirs(PC)
    os.makedirs(os.path.join(WORK, "mdcombine"), exist_ok=True)
    with open(SRC, "w", encoding="utf-8") as f:
        f.write("print('combine')\n")


SRC = os.path.join(WORK, "mdcombine", "mdcombine.py")
HEREDOC = "cat > %s <<'EOF'\n#!/usr/bin/env python3\nprint('combine')\nEOF\n"
# D-B06.stream.jsonl line 17, cut to its shape: a chained mkdir, a heredoc, chmod, then a test of the tool.
DB06_CMD = ("mkdir -p mdcombine && cat > mdcombine/mdcombine.py <<'EOF'\n#!/usr/bin/env python3\n\"\"\"Combine every markdown file in a folder into one file.\"\"\"\nprint('x')\nEOF\n"
            "chmod +x mdcombine/mdcombine.py\npython3 -I mdcombine/mdcombine.py notes -o /tmp/combined-test.md && head -20 /tmp/combined-test.md")

for d in (os.path.join(HOME, ".config", "lifehack"), NOTES, WORK, os.path.join(WORK, "notes")):
    os.makedirs(d, exist_ok=True)
os.makedirs(PC, exist_ok=True)
open(os.path.join(HOME, ".config", "lifehack", "code-root"), "w", encoding="utf-8").write(PLUG + "\n")
open(os.path.join(HOME, ".config", "lifehack", "personal-code"), "w", encoding="utf-8").write(PC + "\n")

try:
    print("-- 1. D-B06's exact shape reads the route")
    rc, err, _ = fire("db06", "Bash", {"command": DB06_CMD})
    check(rc == 2, "D-B06 command: the placement stop fires", err)
    check("Wrong home?" in err and "personal code folder" in err, "scorer's markers kept (rig_steer_score reads them)", err)
    check(TARGET in err, "names the exact path to write to", err)
    check('python3 "%s" "%s"' % (LIST_TOOL, TARGET) in err, "names the exact list command", err)
    check(not NO_RETRY.search(err), "the word retry is gone", err)
    rc2, err2, _ = fire("db06", "Bash", {"command": DB06_CMD})
    check(rc2 == 0, "still a speed bump: the same call passes the second time (no new hard block)", err2)

    rc, err, _ = fire("db06w", "Write", {"file_path": os.path.join(WORK, "tools", "mdcombine.py"), "content": "print(1)"})
    check(rc == 2 and TARGET in err and not NO_RETRY.search(err), "Write-tool shape (enver D-B06) reads the same route", err)

    rc, err, _ = fire("db06off", "Bash", {"command": DB06_CMD}, ROUNDB_PLACEMENT_ROUTE_SIGN="off")
    check(rc == 2 and "Retry the same call and it goes through; this stop happens once per session per rule." in err and TARGET not in err,
          "switch OFF: exactly the old text", err)

    print("-- 1b. every other build-mode stop: a named route, no retry; OFF = the old text")
    os.makedirs(os.path.join(NOTES, "desks", "pond"), exist_ok=True)
    NOTE_TOOL = os.path.join(NOTES, "desks", "pond", "tool_x.py")
    STOPS = [
        ("code-in-notes", "Write", {"file_path": NOTE_TOOL, "content": "print(1)"}, os.path.join(PC, "desks", "pond", "tools", "tool_x.py")),
        ("notes-in-harness", "Write", {"file_path": os.path.join(PLUG, "records", "rs-note.md"), "content": "hi"}, os.path.join(NOTES, "records", "rs-note.md")),
        ("worktree-home", "Bash", {"command": "git worktree add %s -b rs-x" % os.path.join(WORK, "wt")}, "use that command"),
        ("skill-not-loaded", "Write", {"file_path": os.path.join(PC, "skills", "recap", "SKILL.md"), "content": "---\nname: recap\n---\n"}, "~/.claude/skills/<name>/"),
        ("skill outside homes", "Write", {"file_path": os.path.join(WORK, "skills", "recap", "SKILL.md"), "content": "---\nname: recap\n---\n"}, "~/.claude/skills/recap/SKILL.md"),
        ("project skill", "Write", {"file_path": os.path.join(WORK, "proj", ".claude", "skills", "recap", "SKILL.md"), "content": "---\nname: recap\n---\n"}, "write it there as they asked"),
        ("new desk", "Bash", {"command": "mkdir -p %s" % os.path.join(NOTES, "desks", "rsdesk")}, "desk-building-sop.md and system/register/toolbox.md now"),
        ("new job", "Write", {"file_path": os.path.join(PLUG, "system", "rs-run.sh"), "content": "echo hi"}, "cron-jobs-sop.md and system/register/toolbox.md now"),
    ]
    for i, (label, tool, ti, want) in enumerate(STOPS):
        rc, err, _ = fire("stop%d" % i, tool, ti)
        check(rc == 2 and want in err and not NO_RETRY.search(err), "%s: names the route, no retry" % label, err)
        rc, err, _ = fire("stop%d" % i, tool, ti)
        check(rc == 0, "%s: still once per session, no new block" % label, err)
        rc, err, _ = fire("stopoff%d" % i, tool, ti, ROUNDB_PLACEMENT_ROUTE_SIGN="off")
        check(rc == 2 and re.search(r"retry the same call", err, re.I) and not NO_NEW.search(err), "%s: OFF = the old text" % label, err)

    print("-- 2. the named route passes every registered hook, in every shell shape, and works")
    D = os.path.dirname(TARGET)
    LIST = 'python3 "%s" "%s"' % (LIST_TOOL, TARGET)
    SHAPES = {
        "chained heredoc (D-B06's own shape)": "mkdir -p %s && %schmod +x %s\n%s" % (D, HEREDOC % TARGET, TARGET, LIST),
        "mv then list": "mkdir -p %s && mv %s %s && %s" % (D, SRC, TARGET, LIST),
        "mv -- then list": "mkdir -p %s && mv -- %s %s && %s" % (D, SRC, TARGET, LIST),
        "cp -- then list": "mkdir -p %s && cp -- %s %s && %s" % (D, SRC, TARGET, LIST),
        "list with --": "mkdir -p %s && mv %s %s && python3 \"%s\" -- \"%s\"" % (D, SRC, TARGET, LIST_TOOL, TARGET),
        "inside if/else": "if [ -d %s ]; then mv %s %s; else mkdir -p %s && mv %s %s; fi\n%s" % (D, SRC, TARGET, D, SRC, TARGET, LIST),
        "heredoc inside if/else": "if [ -d %s ]; then :; else mkdir -p %s; fi\nif true; then\n%selse\n:\nfi\n%s" % (D, D, HEREDOC % TARGET, LIST),
        "through a variable": 'D=%s; mkdir -p "$D"; mv "%s" "$D/mdcombine.py" && python3 "%s" "$D/mdcombine.py"; ls -l "$D"' % (D, SRC, LIST_TOOL),
        "cd into the folder first": "mkdir -p %s && cd %s && mv %s ./mdcombine.py && %s" % (D, D, SRC, LIST),
    }
    for i, (name, cmd) in enumerate(SHAPES.items()):
        reset()
        stops = chain_stops("route%d" % i, "Bash", {"command": cmd})
        check(not stops, "chain clean: " + name, repr(stops))
        r = run_shell(cmd)
        check(r.returncode == 0 and os.path.isfile(TARGET) and '"/tools/mdcombine.py"' in own_list(),
              "really lands and is listed: " + name, "rc=%s out=%s err=%s list=%s" % (r.returncode, r.stdout, r.stderr, own_list()))

    reset()
    stops = chain_stops("routeW", "Write", {"file_path": TARGET, "content": "print('combine')\n"})
    check(not stops, "chain clean: the Write tool at the named path", repr(stops))
    stops = chain_stops("routeL", "Bash", {"command": LIST})
    check(not stops, "chain clean: the list command as its own call", repr(stops))

    # the person named this folder: the same call goes through once, and the sign's --keep line lists it
    rc, err, _ = fire("named", "Write", {"file_path": os.path.join(WORK, "named.py"), "content": "print(1)"})
    keep = 'python3 "%s" --keep "%s"' % (LIST_TOOL, os.path.join(WORK, "named.py"))
    check(keep in err, "names the --keep line for a folder the person named", err)
    reset()
    with open(os.path.join(WORK, "named.py"), "w", encoding="utf-8") as f:
        f.write("print(1)\n")
    stops = chain_stops("keep", "Bash", {"command": keep})
    r = run_shell(keep)
    check(not stops and r.returncode == 0 and "named.py" in own_list(), "--keep passes the chain and lists the file", repr(stops) + r.stderr)

    # the real order of events: the session has just read the stop, so a harder shape (cd into a variable) still passes
    rc, err, _ = fire("real-flow", "Write", {"file_path": os.path.join(WORK, "fresh-tool.py"), "content": "print(1)"})
    check(rc == 2 and "Wrong home" in err, "the session reads the stop first", err)
    reset()
    harder = 'D=%s; mkdir -p "$D"; cd "$D" && mv %s ./mdcombine.py && python3 "%s" "$D/mdcombine.py"' % (D, SRC, LIST_TOOL)
    stops = chain_stops("real-flow", "Bash", {"command": harder})
    r = run_shell(harder)
    check(not stops and os.path.isfile(TARGET) and r.returncode == 0, "after the stop: cd through a variable passes the chain and lands", repr(stops) + r.stderr)
    rc, err, _ = fire("varfile", "Bash", {"command": "mkdir -p out && cat > \"out/$NAME.py\" <<'EOF'\nprint(1)\nEOF\n"})
    check(rc == 2 and "$NAME" not in err and "<file name>" in err, "an unresolvable name: the sign prints a placeholder, never the literal variable", err)

    # the routes the other signs name
    SKILL = "---\nname: recap\ndescription: \"Sums up the week\"\n---\n"
    SK_DIR = os.path.join(HOME, ".claude", "skills", "recap")
    for sess, stop_tool, stop_in, label, tool, ti in [
        ("r-notes", "Write", {"file_path": NOTE_TOOL, "content": "print(1)"}, "code-in-notes -> the desk's tools/", "Write", {"file_path": os.path.join(PC, "desks", "pond", "tools", "tool_x.py"), "content": "print(1)\n"}),
        ("r-harn", "Write", {"file_path": os.path.join(PLUG, "records", "rs-note.md"), "content": "hi"}, "notes-in-harness -> notes", "Write", {"file_path": os.path.join(NOTES, "records", "rs-note.md"), "content": "hi\n"}),
        ("r-skill", "Write", {"file_path": os.path.join(WORK, "skills", "recap", "SKILL.md"), "content": SKILL}, "skill -> ~/.claude/skills (Write)", "Write", {"file_path": os.path.join(SK_DIR, "SKILL.md"), "content": SKILL}),
        ("r-skill2", "Write", {"file_path": os.path.join(WORK, "skills", "recap", "SKILL.md"), "content": SKILL}, "skill -> ~/.claude/skills (chained, if/else)", "Bash", {"command": "S=%s; if [ -d \"$S\" ]; then :; else mkdir -p \"$S\"; fi\ncat > %s/SKILL.md <<'EOF'\n%sEOF\n" % (SK_DIR, SK_DIR, SKILL)}),
    ]:
        fire(sess, stop_tool, stop_in)
        # a new skill draws its own once-per-session stop too: the sign says read the SOP, then build
        fire(sess, tool, ti)
        stops = chain_stops(sess, tool, ti)
        check(not stops, "chain clean after the stop: " + label, repr(stops))

    reset()
    run_shell("mkdir -p %s && mv %s %s" % (D, SRC, TARGET))
    r = subprocess.run(["python3", LIST_TOOL, "--", TARGET], capture_output=True, text=True, env=env(ROUNDB_PLACEMENT_ROUTE_SIGN="off"), cwd=WORK)
    check(r.returncode == 1, "switch OFF: own_list_add -- PATH behaves as before (exit 1)", r.stderr)

    print("-- 2b. a target through a variable is judged at its real path: right homes quiet, wrong homes stopped (exam D-B07)")
    MONEY = os.path.join(NOTES, "desks", "money", "tools")
    os.makedirs(os.path.dirname(MONEY), exist_ok=True)
    TOTAL_DEST = os.path.join(PC, "desks", "money", "tools", "receipts_total.py")
    # D-B07.stream.jsonl line 25 (pinned5b), cut to its shape: unquoted $D, a heredoc, then a test of the tool
    DB07_CMD = ("D=%s; mkdir -p $D\ncat > $D/receipts_total.py <<'EOF'\n#!/usr/bin/env python3\n\"\"\"Total one month's receipts from a CSV.\"\"\"\nprint('x')\nEOF\n"
                "python3 -I $D/receipts_total.py data/r.csv; echo \"exit=$?\"" % MONEY)
    rc, err, _ = fire("db07", "Bash", {"command": DB07_CMD})
    check(rc == 2 and "code-in-notes" in err, "D-B07 command: the notes-folder stop fires", err)
    check(TOTAL_DEST in err and 'python3 "%s" "%s"' % (LIST_TOOL, TOTAL_DEST) in err, "D-B07: names the desk's tools folder in the personal code folder, and the list command", err)
    check(not NO_RETRY.search(err), "D-B07: no retry", err)
    rc, err, _ = fire("db07", "Bash", {"command": DB07_CMD})
    check(rc == 0, "D-B07: still once per session, no new hard block", err)
    rc, err, _ = fire("db07off", "Bash", {"command": DB07_CMD}, ROUNDB_PLACEMENT_ROUTE_SIGN="off")
    check(rc == 2 and "Retry the same call" in err, "D-B07: switch OFF = the old stop and text", err)
    rc, err, _ = fire("db07w", "Write", {"file_path": os.path.join(MONEY, "receipts_total.py"), "content": "print(1)"})
    check(rc == 2 and TOTAL_DEST in err, "D-B07's Write route reads the same sign", err)

    reset()
    QUIET = {
        "mv, quoted": 'D=%s; mkdir -p "$D"; mv "%s" "$D/mdcombine.py"' % (D, SRC),
        "mv, unquoted": "D=%s; mkdir -p $D; mv %s $D/mdcombine.py" % (D, SRC),
        "mv, braces": 'D=%s; mv "%s" "${D}/mdcombine.py"' % (D, SRC),
        "mv, into the folder": 'D=%s; mv "%s" "$D/"' % (D, SRC),
        "heredoc": "D=%s; mkdir -p $D\ncat > $D/fresh_tool.py <<'EOF'\nprint(1)\nEOF\n" % D,
        "a scratch folder": "D=/tmp/routesign-x; mkdir -p $D\ncat > $D/a.py <<'EOF'\nprint(1)\nEOF\n",
        "a data file in notes": "D=%s; cat > $D/month.csv <<'EOF'\na,b\nEOF\n" % MONEY,
        "making a new desk folder (as before)": 'D=%s; mkdir -p "$D"' % os.path.join(NOTES, "desks", "rsnew"),
    }
    for i, (name, cmd) in enumerate(QUIET.items()):
        rc, err, _ = fire("quiet%d" % i, "Bash", {"command": cmd})
        check(rc == 0 and not err.strip(), "quiet: right destination through a variable, " + name, err)
    os.makedirs(MONEY, exist_ok=True)
    with open(os.path.join(MONEY, "old_tool.py"), "w", encoding="utf-8") as f:
        f.write("print(0)\n")
    rc, err, _ = fire("quietold", "Bash", {"command": "D=%s; cat >> $D/old_tool.py <<'EOF'\nprint(1)\nEOF\n" % MONEY})
    check(rc == 0 and "Wrong home" not in err, "quiet: an EXISTING file in notes through a variable (placement is for new files, as with Write)", err)
    os.unlink(os.path.join(MONEY, "old_tool.py"))

    STILL = [
        ("a SKILL.md in the personal code folder's skills/", "D=%s; cat > $D/SKILL.md <<'EOF'\nx\nEOF\n" % os.path.join(PC, "skills", "recap"), "never from your personal code folder"),
        ("a new hook", "D=%s; cat > $D/rs_new.sh <<'EOF'\necho hi\nEOF\n" % HOOKS, "building a hook"),
        ("a new job", "D=%s; cat > $D/rs-run.sh <<'EOF'\necho hi\nEOF\n" % os.path.join(PLUG, "system"), "building a job"),
        ("a shared tool's name in notes", "D=%s; cat > $D/own_list_add.py <<'EOF'\nprint(1)\nEOF\n" % MONEY, "Wrong home"),
        ("a variable with no value here", "cat > $UNSET_DIR/tool.py <<'EOF'\nprint(1)\nEOF\n", "personal code folder"),
    ]
    for i, (name, cmd, want) in enumerate(STILL):
        rc, err, _ = fire("still%d" % i, "Bash", {"command": cmd})
        check(rc == 2 and want in err and not NO_RETRY.search(err), "stopped: through a variable, " + name, err)

    reset()
    DD = os.path.dirname(TOTAL_DEST)
    route = "D=%s; mkdir -p $D\ncat > $D/receipts_total.py <<'EOF'\nprint(1)\nEOF\npython3 \"%s\" \"$D/receipts_total.py\"" % (DD, LIST_TOOL)
    stops = chain_stops("db07route", "Bash", {"command": route})
    r = run_shell(route)
    check(not stops and r.returncode == 0 and '"/desks/money/tools/receipts_total.py"' in own_list(), "D-B07's named route passes the chain, lands and is listed", repr(stops) + r.stderr + own_list())
    stops = chain_stops("db07routew", "Write", {"file_path": TOTAL_DEST, "content": "print(1)\n"})
    check(not stops, "D-B07's named route by the Write tool: chain clean", repr(stops))

    print("-- 2c. the outside-homes sign names the desk only when the prompt or path really names one (exam D-B07 r3)")

    def transcript(*entries):
        p = os.path.join(T, "transcript-%d.jsonl" % len(os.listdir(T)))
        with open(p, "w", encoding="utf-8") as f:
            for role, text, extra in entries:
                f.write(json.dumps(dict({"type": role, "message": {"role": role, "content": text}}, **extra)) + "\n")
        return p

    def said(text):
        return transcript(("user", text, {}))

    TOOLS_DEST = os.path.join(PC, "tools", "month_total.py")
    DESK_DEST = os.path.join(PC, "desks", "money", "tools", "month_total.py")
    PROMPT = "make a tool just for my money desk that totals the month's receipts csv"   # the exam prompt
    R3_PATH = os.path.join(WORK, "money-desk", "month_total.py")   # D-B07.stream.jsonl line 30 (pinned6 r3), the path as sent
    R3_CONTENT = '#!/usr/bin/env python3\n"""Total one month\'s receipts from a CSV.\n\nUsage: month_total.py RECEIPTS.csv [YYYY-MM]\n"""\nimport csv\n'
    LOOSE = os.path.join(WORK, "receipts", "month_total.py")
    n = [0]

    def sign(path, tp=None, **over):
        n[0] += 1
        return fire("desk%d" % n[0], "Write", {"file_path": path, "content": R3_CONTENT}, transcript_path=tp, **over)

    rc, err, _ = sign(R3_PATH, said(PROMPT))
    check(rc == 2 and DESK_DEST in err and 'python3 "%s" "%s"' % (LIST_TOOL, DESK_DEST) in err and TOOLS_DEST not in err, "D-B07 r3's exact call: the sign names the desk's tools folder", err)
    check(not NO_RETRY.search(err), "D-B07 r3: no retry", err)
    rc, err, _ = fire("desk%d" % n[0], "Write", {"file_path": R3_PATH, "content": R3_CONTENT}, transcript_path=said(PROMPT))
    check(rc == 0, "D-B07 r3: what fires is unchanged, once per session", err)
    rc, err, _ = sign(LOOSE, said(PROMPT))
    check(rc == 2 and DESK_DEST in err, "the prompt alone names the desk, any folder", err)
    rc, err, _ = sign(R3_PATH)
    check(rc == 2 and DESK_DEST in err, "the path alone names the desk, no transcript", err)
    rc, err, _ = sign(os.path.join(WORK, "desks", "money", "month_total.py"))
    check(rc == 2 and DESK_DEST in err, "a desks/<desk>/ path names the desk", err)
    rc, err, _ = sign(LOOSE, said("write it for the money desk please"))
    check(rc == 2 and DESK_DEST in err, "'the money desk' names it", err)
    rc, err, _ = sign(LOOSE, said("totals for money desk"))
    check(rc == 2 and DESK_DEST in err, "no article, but notes/desks/money really exists", err)
    rc, err, _ = sign(LOOSE, said("totals for pottery desk"))
    check(rc == 2 and TOOLS_DEST in err, "no article and no such desk folder: no guess, tools/", err)

    rc, err, _ = sign(LOOSE, said("write a command-line thing that totals receipts"))
    check(rc == 2 and TOOLS_DEST in err and "/desks/" not in err, "a no-desk tool keeps tools/", err)
    rc, err, _ = sign(LOOSE)
    check(rc == 2 and TOOLS_DEST in err, "no transcript at all: tools/", err)
    rc, err, _ = sign(LOOSE, os.path.join(T, "no-such-transcript.jsonl"))
    check(rc == 2 and TOOLS_DEST in err, "an unreadable transcript: tools/, and no crash", err)
    for label, words in [
        ("furniture", "a tool to track my standing desk height"),
        ("a help desk", "total the tickets from the help desk"),
        ("'my desk' names nothing", "a total for the receipts on my desk"),
        ("two desks: no guess", "totals for my money desk and my travel desk"),
        ("said it is not for the desk", "this is not for my money desk"),
    ]:
        rc, err, _ = sign(LOOSE, said(words))
        check(rc == 2 and TOOLS_DEST in err and "/desks/" not in err, "tools/: " + label, err)
    rc, err, _ = sign(LOOSE, transcript(("user", PROMPT, {}), ("assistant", "done", {}), ("user", "now a tool that totals receipts", {})))
    check(rc == 2 and TOOLS_DEST in err, "tools/: an EARLIER prompt named the desk, the latest did not", err)
    rc, err, _ = sign(LOOSE, transcript(("user", "<system-reminder>my money desk</system-reminder>total the receipts", {})))
    check(rc == 2 and TOOLS_DEST in err, "tools/: injected context is not what the person said", err)
    rc, err, _ = sign(LOOSE, transcript(("user", "total the receipts", {}), ("assistant", "for my money desk", {})))
    check(rc == 2 and TOOLS_DEST in err, "tools/: the model's own words are not the person's", err)
    rc, err, _ = sign(os.path.join(WORK, "help-desk", "month_total.py"))
    check(rc == 2 and TOOLS_DEST in err, "tools/: a help-desk folder is not a desk", err)
    rc, err, _ = sign(os.path.join(WORK, "money-desk", "SKILL.md"), said(PROMPT))
    check(rc == 2 and "~/.claude/skills/" in err and "/desks/" not in err, "a skill keeps its own route", err)
    rc, err, _ = sign(R3_PATH, said(PROMPT), ROUNDB_PLACEMENT_ROUTE_SIGN="off")
    check(rc == 2 and "Retry the same call" in err and DESK_DEST not in err, "switch OFF: the old text", err)
    rc, err, _ = sign(DESK_DEST, said(PROMPT))
    check(rc == 0 and "Wrong home" not in err, "the named route itself is not stopped", err)

    reset()
    route = 'mkdir -p "%s" && mv "%s" "%s" && python3 "%s" "%s"' % (os.path.dirname(DESK_DEST), SRC, DESK_DEST, LIST_TOOL, DESK_DEST)
    stops = chain_stops("deskroute", "Bash", {"command": route})
    r = run_shell(route)
    check(not stops and r.returncode == 0 and '"/desks/money/tools/month_total.py"' in own_list(), "the desk route passes the chain, lands and is listed", repr(stops) + r.stderr + own_list())
    stops = chain_stops("deskroutew", "Write", {"file_path": DESK_DEST, "content": "print(1)\n"})
    check(not stops, "the desk route by the Write tool: chain clean", repr(stops))

    print("-- 2d. the end-of-turn message names the same desk route, by the same rule")

    def end_of_turn(path, tp=None, **over):
        n[0] += 1
        sid, tw = "eot%d" % n[0], os.path.join(T, "tw")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write("print(1)\n")
        os.makedirs(tw, exist_ok=True)
        with open(os.path.join(tw, sid + ".list"), "w", encoding="utf-8") as f:
            f.write("p1\tnew\t%s\n" % path)
        p = json.dumps({"session_id": sid, "prompt_id": "p1", "hook_event_name": "Stop", "stop_hook_active": False, "transcript_path": tp or ""})
        r = subprocess.run(["bash", os.path.join(HOOKS, "end_of_turn_checks.sh")], input=p, capture_output=True, text=True, env=env(**over), cwd=WORK)
        os.unlink(path)
        return r.stdout

    out = end_of_turn(LOOSE, said(PROMPT))
    check("move it to " + DESK_DEST in out and 'own_list_add.py\\" \\"%s' % DESK_DEST in out, "the prompt names the desk: move it to the desk's tools folder, and list that", out)
    out = end_of_turn(R3_PATH)
    check("move it to " + DESK_DEST in out, "the path names the desk, no transcript", out)
    out = end_of_turn(LOOSE, said("write a command-line thing that totals receipts"))
    check("move it to " + TOOLS_DEST in out, "a no-desk tool keeps tools/", out)
    out = end_of_turn(LOOSE)
    check("move it to " + TOOLS_DEST in out, "no transcript: tools/", out)
    out = end_of_turn(LOOSE, said("totals for my money desk and my travel desk"))
    check("move it to " + TOOLS_DEST in out, "two desks: no guess, tools/", out)
    out = end_of_turn(R3_PATH, said(PROMPT), ROUNDB_PLACEMENT_ROUTE_SIGN="off")
    check("move it to " + TOOLS_DEST in out, "switch OFF: the old tools/ text", out)

    print("-- 3. harmless work is not newly stopped")
    HARMLESS = [
        ("Write", {"file_path": TARGET, "content": "print(1)"}, "a tool already in the personal code folder"),
        ("Write", {"file_path": "/tmp/scratch-routesign.py", "content": "print(1)"}, "a /tmp scratch script"),
        ("Write", {"file_path": os.path.join(WORK, "notes.md"), "content": "hello"}, "a markdown note in the work folder"),
        ("Write", {"file_path": os.path.join(WORK, "out.json"), "content": "{}"}, "a data file in the work folder"),
        ("Bash", {"command": "ls -la && head -c 600 README.md"}, "a read"),
        ("Bash", {"command": "python3 -I mdcombine/mdcombine.py notes | head -20"}, "running a tool"),
        ("Bash", {"command": "echo hi > out.txt"}, "a text file"),
    ]
    for i, (tool, ti, label) in enumerate(HARMLESS):
        rc, err, _ = fire("harm%d" % i, tool, ti)
        check(rc == 0 and "Wrong home" not in err, "no stop: " + label, err)
    rc, err, _ = fire("secondfile", "Write", {"file_path": os.path.join(WORK, "one.py"), "content": "print(1)"})
    rc, err, _ = fire("secondfile", "Write", {"file_path": os.path.join(WORK, "two.py"), "content": "print(2)"})
    check(rc == 0, "a second file in the same session: no second stop", err)
    conf = os.path.join(HOME, ".config", "lifehack", "placement.conf")
    with open(conf, "w", encoding="utf-8") as f:
        f.write("kept\t%s\n" % os.path.join(WORK, "lab"))
    rc, err, _ = fire("kept", "Write", {"file_path": os.path.join(WORK, "lab", "a.py"), "content": "print(1)"})
    check(rc == 0 and "Wrong home" not in err, "a hand-kept folder: no stop", err)
    os.rename(conf, conf + ".off")
    rc, err, _ = fire("skill", "Write", {"file_path": os.path.join(WORK, "skills", "recap", "SKILL.md"), "content": "---\nname: recap\n---\n"})
    check(rc == 2 and "Build it THERE" in err and os.path.join(PC, "tools") not in err, "a SKILL.md keeps its own route (~/.claude/skills), not tools/", err)
finally:
    shutil.rmtree(T, ignore_errors=True)

print("placement_route_sign: %d passed, %d failed" % (passed, fails))
sys.exit(1 if fails else 0)

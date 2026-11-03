#!/usr/bin/env python3
"""test_desk_tool_sign.py -- switch desk_tool_sign (roundB.conf), exam miss D-B07 r2 (pinned8).

The miss: the person named a desk, the session wrote straight to <personal code>/tools/, and nothing steered it: that write is inside a home,
so no stop fired. A write to tools/x.py looks the same for a loose script and a one-desk tool, so the signal has to come from what hooks really
receive: the prompt hook gets the typed words, the write hook gets the same session_id (fixtures captured live, Claude Code 2026-11-03, a sub-agent's
write included). Every case fires the REAL hooks on payloads built from those fixtures, under a throwaway HOME, and reads the printed text.
All desk names and wordings here are invented; none is the exam's. Run: python3 system/hooks/tests/test_desk_tool_sign.py
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HOOKS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUG = os.path.realpath(os.path.join(HOOKS, "..", ".."))
FIX = os.path.join(HOOKS, "tests", "fixtures")
PROMPT_HOOK = os.path.join(HOOKS, "inject_sop_before_build.sh")
WRITE_HOOK = os.path.join(HOOKS, "guard_build_mode.sh")
LIST_TOOL = os.path.join(PLUG, "shared", "tools", "own_list_add.py")
T = os.path.realpath(tempfile.mkdtemp(prefix="desksign."))   # "desk" in the cwd on purpose: as ~/Desktop does, it reaches the hook's payload filter; only the prompt may count
HOME = os.path.join(T, "hm")
PC = os.path.join(HOME, "lifehack-personal-code")
NOTES = os.path.join(HOME, "my-notes")
WORK = os.path.join(HOME, "work")
BARE_NOTES = os.path.join(HOME, "student-notes")
NO_RETRY = re.compile(r"retry|same call|goes through", re.I)
RULE = "desk-tool-loose"
fails = passed = 0
_sid = [0]


def check(ok, label, detail=""):
    global fails, passed
    if ok:
        passed += 1
        print("   ok   " + label)
    else:
        fails += 1
        print("  FAIL  %s %s" % (label, str(detail)[:600]))


def env(notes=NOTES, **over):
    e = {k: v for k, v in os.environ.items() if not k.startswith(("ROUNDB_", "LIFEHACK_"))}
    e.update(HOME=HOME, LIFEHACK_ROOT=notes, CLAUDE_PLUGIN_ROOT=PLUG, LHB_TURN_WRITES_DIR=os.path.join(T, "tw"), LHB_TEST_RUN="1")
    e.update(over)
    return e


def fixture(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as f:
        return json.load(f)


def session():
    _sid[0] += 1
    return "sess-%d" % _sid[0]


def say(sid, words, fix="ups_real_stdin_prompt.json", notes=NOTES, **over):
    """One real prompt payload through the real prompt hook."""
    p = fixture(fix)
    p["session_id"] = sid
    p["cwd"] = WORK
    p["prompt"] = p["prompt"].replace("@@BODY@@", words)
    return subprocess.run(["bash", PROMPT_HOOK], input=json.dumps(p), capture_output=True, text=True, env=env(notes, **over), cwd=WORK)


def write(sid, path, fix="pre_real_stdin_write.json", notes=NOTES, content="print(1)\n", **over):
    p = fixture(fix)
    p["session_id"] = sid
    p["cwd"] = WORK
    p["tool_input"] = {"file_path": path, "content": content}
    r = subprocess.run(["bash", WRITE_HOOK], input=json.dumps(p), capture_output=True, text=True, env=env(notes, **over), cwd=WORK)
    return r.returncode, r.stderr


def shell(sid, command, **over):
    p = fixture("pre_real_stdin_bash.json")
    p["session_id"] = sid
    p["cwd"] = WORK
    p["tool_input"] = {"command": command, "description": "x"}
    r = subprocess.run(["bash", WRITE_HOOK], input=json.dumps(p), capture_output=True, text=True, env=env(**over), cwd=WORK)
    return r.returncode, r.stderr


def registered_chain(tool):
    hooks = json.load(open(os.path.join(PLUG, "hooks", "hooks.json"), encoding="utf-8"))["hooks"]["PreToolUse"]
    out = []
    for group in hooks:
        if re.fullmatch(group.get("matcher") or ".*", tool):
            out += [h["command"] for h in group["hooks"] if h.get("type") == "command"]
    return out


def chain_stops(sid, tool, tool_input):
    p = fixture("pre_real_stdin_write.json" if tool == "Write" else "pre_real_stdin_bash.json")
    p.update(session_id=sid, cwd=WORK, tool_input=tool_input)
    stops = []
    for cmd in registered_chain(tool):
        r = subprocess.run(cmd, shell=True, input=json.dumps(p), capture_output=True, text=True, env=env(), cwd=WORK, executable="/bin/bash")
        if r.returncode == 2 or re.search(r'"permissionDecision"\s*:\s*"(deny|ask)"', r.stdout or ""):
            stops.append((cmd.split("/")[-1], (r.stderr + r.stdout)[:400]))
    return stops


LOOSE = os.path.join(PC, "tools", "helper.py")


def dest(desk, name="helper.py"):
    return os.path.join(PC, "desks", desk, "tools", name)


for d in (os.path.join(HOME, ".config", "lifehack"), os.path.join(PC, "tools"), WORK, BARE_NOTES,
          os.path.join(NOTES, "desks", "bakery", "canon"), os.path.join(NOTES, "desks", "lamps"), os.path.join(NOTES, "desks", "real-estate"),
          os.path.join(NOTES, "desks", "ledger"), os.path.join(NOTES, "desks", "_archive"), os.path.join(NOTES, "desks", ".hidden")):
    os.makedirs(d, exist_ok=True)
open(os.path.join(HOME, ".config", "lifehack", "code-root"), "w", encoding="utf-8").write(PLUG + "\n")
open(os.path.join(HOME, ".config", "lifehack", "personal-code"), "w", encoding="utf-8").write(PC + "\n")
open(os.path.join(NOTES, "desks", "desk-registry.yaml"), "w", encoding="utf-8").write(
    "schema_version: 2\ndesks:\n  - desk_id: taxes\n    open_loops_path: desks/ledger/state/open-loops.md\n    backlog_mode: register\n"
    "  - desk_id: orchard\n    open_loops_path: desks/orchard/state/open-loops.md\n    backlog_mode: queue\n")

# wording -> the folder the sign must route to. Different shapes on purpose, none is the exam's.
NAMED = [
    ("write a script for the bakery desk that adds up flour orders", "bakery"),
    ("Bakery desk needs a little helper that rounds prices", "bakery"),
    ("can you put together something in desks/bakery that checks oven logs", "bakery"),
    ("I need a python helper; it's for my desk called bakery", "bakery"),
    ("this goes with bakery-desk: a tool that counts loaves", "bakery"),
    ("new script please, desk: bakery, it should list suppliers", "bakery"),
    ("bakery, one of my desks, could use a dough timer", "bakery"),
    ("Bakery is my desk for the shop. Build something that sums the till.", "bakery"),
    ("for bakery's desk, build a flour counter", "bakery"),
    ("for bakery’s desk, build a flour counter", "bakery"),
    ("BAKERY DESK: quick tool to count trays", "bakery"),
    ("the real estate desk wants a rent calculator", "real-estate"),
    ("put a rent calculator on the real-estate desk", "real-estate"),
    ("the taxes desk needs a mileage adder", "ledger"),       # the list names a desk_id that lives in another folder
    ("the orchard desk needs a tree counter", "orchard"),     # on the list, no folder yet
    ("a tool in `desks/lamps/tools/` that counts bulbs", "lamps"),
]
# wording that must leave no signal, with the real desks above present
NOT_NAMED = [
    "write a script that renames my photos",
    "make a tool that totals a csv column",
    "a tool for the desk",                                    # a desk, no name
    "write a script for my pottery desk",                     # not a desk the person has
    "track how long I sit at my standing desk",
    "I left my lamps on my desk, write a script to remind me",
    "my desk lamps flicker, write a script to log it",
    "write a script comparing prices for desk lamps",
    "the lamps are under my desk; write a tool to list them",
    "buy a desk and lamps: write a script comparing prices",
    "bakery boxes are on the desk, write a tool to count them",
    "this is not for my bakery desk, just a loose script",
    "it isn't for the bakery desk",
    "nothing to do with the bakery desk: rename my photos",
    "a tool shared by my bakery and lamps desks",
    "a tool comparing the bakery desk with the lamps desk",
    "```\ncat desks/bakery/x\n```\nwhat does that output mean? write a script to explain it",
    "<task-notification>the bakery desk is done</task-notification> write a script for it",
]

try:
    print("-- 1. the live capture: a sign from a typed prompt reaches the write, on the fixtures")
    for f in ("ups_real_stdin_prompt.json", "pre_real_stdin_write.json", "pre_real_stdin_subagent_write.json"):
        check(fixture(f)["session_id"] == fixture("ups_real_stdin_prompt.json")["session_id"], "%s carries the shared session_id" % f)
    check("prompt" in fixture("ups_real_stdin_prompt.json") and "agent_id" in fixture("pre_real_stdin_subagent_write.json"), "the fixture fields this design leans on exist")

    print("-- 2. naming a real desk, in many wordings: a new tool in the loose folder gets the sign naming that desk's folder")
    for words, folder in NAMED:
        sid = session()
        r = say(sid, words)
        rc, err = write(sid, LOOSE)
        check(rc == 2 and dest(folder) in err, "sign: %r -> %s" % (words[:60], folder), "rc=%s err=%s" % (rc, err))
        check(not r.stdout or dest(folder) not in r.stdout, "   nothing extra at prompt time", r.stdout)

    print("-- 3. the sign's text")
    sid = session()
    say(sid, NAMED[0][0])
    rc, err = write(sid, LOOSE)
    check("Wrong home?" in err and "RULE: system/hooks/placement.conf (%s)" % RULE in err, "same family as the other placement stops", err)
    check("Do not write it here." in err, "says what not to do", err)
    check('python3 "%s" "%s"' % (LIST_TOOL, dest("bakery")) in err, "names the exact list command for the desk path", err)
    check(not NO_RETRY.search(err), "never says retry", err)
    check("--keep" not in err, "the loose tool's way out is a normal listing, not a kept folder", err)
    check('python3 "%s" "%s"' % (LIST_TOOL, LOOSE) in err, "names the way through when the tool is not just for that desk", err)
    rc2, err2 = write(sid, LOOSE)
    check(rc2 == 0, "speed bump: the same write passes the second time, no new hard block", err2)
    rc3, err3 = write(sid, os.path.join(PC, "tools", "another.py"))
    check(rc3 == 0, "once per session: another loose tool stays quiet", err3)

    print("-- 4. the route the sign names passes every registered hook, and lands")
    sid = session()
    say(sid, NAMED[0][0])
    write(sid, LOOSE)
    target = dest("bakery", "routed.py")
    stops = chain_stops(sid, "Write", {"file_path": target, "content": "print(1)\n"})
    check(not stops, "Write route: chain clean", stops)
    stops = chain_stops(sid, "Bash", {"command": "mkdir -p %s" % os.path.dirname(target), "description": "x"})
    check(not stops, "mkdir of the route: chain clean", stops)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    open(target, "w", encoding="utf-8").write("print(1)\n")
    r = subprocess.run([sys.executable, LIST_TOOL, target], capture_output=True, text=True, env=env(), cwd=WORK)
    check(r.returncode == 0, "the named list command really works on it", r.stderr + r.stdout)

    print("-- 5. every way to the loose folder, and the real session shapes")
    sid = session(); say(sid, NAMED[0][0])
    rc, err = shell(sid, "cat > %s <<'EOF'\nprint(1)\nEOF\n" % LOOSE)
    check(rc == 2 and dest("bakery") in err, "a Bash heredoc", err)
    sid = session(); say(sid, NAMED[0][0])
    rc, err = shell(sid, "cd %s && printf x > helper.sh" % os.path.join(PC, "tools"))
    check(rc == 2 and dest("bakery", "helper.sh") in err, "a cd chain, a .sh", err)
    sid = session(); say(sid, NAMED[0][0])
    rc, err = shell(sid, "D=%s; cat > $D/helper.py <<'EOF'\nprint(1)\nEOF\n" % os.path.join(PC, "tools"))
    check(rc == 2 and dest("bakery") in err, "through a variable set in the command", err)
    sid = session(); say(sid, NAMED[0][0])
    rc, err = write(sid, LOOSE, fix="pre_real_stdin_subagent_write.json")
    check(rc == 2 and dest("bakery") in err, "a sub-agent's write (real stdin: same session_id, its own agent_id) sees the marker", err)
    sid = session(); say(sid, NAMED[0][0])
    rc, err = write(sid, os.path.join(PC, "helper.py"))
    check(rc == 2 and dest("bakery") in err, "loose at the top of the personal code folder", err)
    sid = session(); say(sid, NAMED[0][0])
    rc, err = write(sid, os.path.join(PC, "tools", "sub", "helper.py"))
    check(rc == 2 and dest("bakery") in err, "a sub-folder of the loose tools folder", err)

    print("-- 6. the turn after: the desk was named one prompt ago")
    sid = session(); say(sid, NAMED[0][0]); say(sid, "dates and amounts please")
    rc, err = write(sid, LOOSE)
    check(rc == 2 and dest("bakery") in err, "a follow-up answer does not lose the desk", err)
    sid = session(); say(sid, NAMED[0][0]); say(sid, "the lamps desk instead")
    rc, err = write(sid, LOOSE)
    check(rc == 2 and dest("lamps") in err and dest("bakery") not in err, "the latest named desk wins", err)
    sid = session(); say(sid, NAMED[0][0]); say(sid, "this is not for my bakery desk after all")
    rc, err = write(sid, LOOSE)
    check(rc == 0, "taking it back clears the signal", err)
    sid = session(); say(sid, NAMED[0][0])
    old = time.time() - 2 * 3600
    for mk in glob.glob(os.path.join(HOME, ".claude", "run", "build-mode", "desk-said.%s*" % sid)):
        os.utime(mk, (old, old))
    rc, err = write(sid, LOOSE)
    check(rc == 0, "an old mention (two hours) has gone stale", err)
    other = session(); say(other, NAMED[0][0])
    rc, err = write(session(), LOOSE)
    check(rc == 0, "another session's prompt does not count", err)

    print("-- 7. negatives: nothing named")
    for words in NOT_NAMED:
        sid = session()
        say(sid, words)
        rc, err = write(sid, LOOSE)
        check(rc == 0 and RULE not in err, "silent: %r" % words[:60], err)

    print("-- 8. negatives: the wrong kind of person, write or message")
    sid = session()
    say(sid, "write a script for the bakery desk", notes=BARE_NOTES)
    rc, err = write(sid, LOOSE, notes=BARE_NOTES)
    check(rc == 0 and RULE not in err, "a student with no desks (real, empty notes folder): silent", err)
    sid = session()
    say(sid, "write a script for the bakery desk", notes=os.path.join(HOME, "no-such-notes"))
    rc, err = write(sid, LOOSE, notes=os.path.join(HOME, "no-such-notes"))
    check(rc == 0 and RULE not in err, "notes folder does not resolve: silent", err)
    sid = session(); say(sid, NAMED[0][0])
    rc, err = write(sid, dest("bakery", "good.py"))
    check(rc == 0 and RULE not in err, "already in desks/<desk>/tools/: silent", err)
    rc, err = write(sid, LOOSE)
    check(rc == 2, "   (and that sign was still there for a loose write)", err)
    sid = session(); say(sid, "build a skill for my bakery desk")
    skill = os.path.join(HOME, ".claude", "skills", "dough")
    os.makedirs(skill, exist_ok=True)
    rc, err = write(sid, os.path.join(skill, "SKILL.md"), content="---\nname: dough\n---\n")
    check(RULE not in err, "a skill's SKILL.md: not this sign", err)
    rc, err = write(sid, os.path.join(skill, "helper.py"))
    check(RULE not in err, "a skill's own script: not this sign", err)
    rc, err = write(sid, os.path.join(PC, "skills", "dough", "helper.py"))
    check(RULE not in err, "under <personal code>/skills: not this sign", err)
    sid = session(); say(sid, NAMED[0][0])
    open(os.path.join(PC, "tools", "existing.py"), "w", encoding="utf-8").write("print(1)\n")
    rc, err = write(sid, os.path.join(PC, "tools", "existing.py"))
    check(rc == 0 and RULE not in err, "an edit of a tool that is already there: silent", err)
    rc, err = write(sid, os.path.join(PC, "tools", "orders.csv"))
    check(rc == 0 and RULE not in err, "a data file: silent", err)
    rc, err = write(sid, os.path.join(PC, "system", "thing.py"))
    check(RULE not in err, "another folder of the person's own code: silent", err)
    rc, err = write(sid, os.path.join(WORK, "thing.py"))
    check(RULE not in err, "outside the homes is the older stop's business", err)

    sid = session()
    peer = fixture("ups_real_stdin_peer.json")
    peer["session_id"] = sid
    peer["cwd"] = WORK
    peer["prompt"] = peer["prompt"].replace("@@BODY@@", "write a script for the bakery desk")
    subprocess.run(["bash", PROMPT_HOOK], input=json.dumps(peer), capture_output=True, text=True, env=env(), cwd=WORK)
    rc, err = write(sid, LOOSE)
    check(rc == 0 and RULE not in err, "a peer message is not the person", err)
    sid = session()
    note = fixture("ups_real_stdin_task_notification.json")
    note["session_id"] = sid
    note["cwd"] = WORK
    note["prompt"] = note["prompt"].replace("@@BODY@@", "write a script for the bakery desk")
    subprocess.run(["bash", PROMPT_HOOK], input=json.dumps(note), capture_output=True, text=True, env=env(), cwd=WORK)
    rc, err = write(sid, LOOSE)
    check(rc == 0 and RULE not in err, "a task notification is not the person", err)

    print("-- 9. the switches")
    sid = session()
    say(sid, NAMED[0][0], ROUNDB_DESK_TOOL_SIGN="off")
    rc, err = write(sid, LOOSE, ROUNDB_DESK_TOOL_SIGN="off")
    check(rc == 0 and RULE not in err, "switch OFF: exactly the old silence", err)
    check(not glob.glob(os.path.join(HOME, ".claude", "run", "build-mode", "desk-said.%s*" % sid)), "switch OFF: the prompt hook leaves nothing")
    sid = session(); say(sid, NAMED[0][0])
    rc, err = write(sid, LOOSE, ROUNDB_PLACEMENT_OUTSIDE_HOMES="off")
    check(rc == 2 and dest("bakery") in err, "does not lean on another switch to be looked at", err)
    off = os.path.join(HOME, ".config", "lifehack", "placement.conf")
    open(off, "w", encoding="utf-8").write("off\t%s\n" % RULE)
    sid = session(); say(sid, NAMED[0][0])
    rc, err = write(sid, LOOSE)
    check(rc == 0 and RULE not in err, "the person can switch this check off", err)
    os.rename(off, off + ".was")
    conf = open(os.path.join(HOOKS, "roundB.conf"), encoding="utf-8").read()
    check(re.search(r"^desk_tool_sign=on$", conf, re.M) is not None, "shipped ON in roundB.conf")
finally:
    shutil.rmtree(T, ignore_errors=True)

print("passed=%d failed=%d" % (passed, fails))
sys.exit(1 if fails else 0)

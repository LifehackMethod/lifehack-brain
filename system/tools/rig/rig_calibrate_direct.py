#!/usr/bin/env python3
# not-wired-yet: run by hand before trusting direct hook runs (Round D safeguard 1); no model call
"""rig_calibrate_direct.py - known-answer DIRECT hook runs for the Round D behaviours replay cannot express as one payload.

Each check pipes a payload into the real hook scripts under an isolated HOME / LIFEHACK_ROOT (a throwaway under the system temp dir; the
person's real ~/.config and ~/.claude are never read or written) and compares with the answer fixed BY DESIGN from the Round D rulings
(A.2 native skills home, A.6 user off-switch, B.5 watch-only mode) - not from what the hook happens to print. Groups: placement_user_off,
skills_native_home, watch (logs, blocks nothing), watch crash (falls through to enforce). Switches go in by env (ROUNDB_*), or by a COPIED
roundB.conf for the conf-driven watch checks. Prints one line per check and `DIRECT CALIBRATION: N of M`; exit 1 if any miss.
Run: python3 system/tools/rig/rig_calibrate_direct.py
"""
import json, os, shutil, subprocess, sys, tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
HK = os.path.join(ROOT, "system", "hooks")
T = os.path.realpath(tempfile.mkdtemp(prefix="rigdirect-"))
HOME, CODE, NOTES, PC = T + "/home", T + "/code", T + "/notes", T + "/pc"
for d in (HOME + "/.config/lifehack", HOME + "/.claude/skills", HOME + "/proj/data-folder", CODE + "/shared/tools", CODE + "/system/hooks/lib", CODE + "/system/sops",
          CODE + "/system/register", CODE + "/hooks", NOTES + "/desks/pond/tools", NOTES + "/system", PC):
    os.makedirs(d, exist_ok=True)
open(HOME + "/.config/lifehack/code-root", "w", encoding="utf-8").write(CODE + "\n")
open(HOME + "/.config/lifehack/personal-code", "w", encoding="utf-8").write(PC + "\n")
for s, d in (("shared/brain_root.py", "shared"), ("shared/personal_code_root.py", "shared"), ("system/tools/utf8_stdio.py", "shared"),
             ("shared/tools/own_list_add.py", "shared/tools"), ("system/hooks/lib/roundb.py", "system/hooks/lib"), ("system/hooks/roundB.conf", "system/hooks"),
             ("system/hooks/build_mode_sops.conf", "system/hooks"), ("system/hooks/placement.conf", "system/hooks")):
    if os.path.exists(os.path.join(ROOT, s)):
        shutil.copy(os.path.join(ROOT, s), os.path.join(CODE, d))
shutil.copytree(os.path.join(HK, "lib"), CODE + "/system/hooks/lib", dirs_exist_ok=True)
for s in ("skill-building", "jobs", "cron-jobs", "hook", "desk-building"):
    open(CODE + "/system/sops/%s-sop.md" % s, "w", encoding="utf-8").write("# %s\n" % s)
open(CODE + "/hooks/hooks.json", "w", encoding="utf-8").write('{"hooks":{}}\n')
open(CODE + "/system/register/register.jsonl", "w", encoding="utf-8").write('{"type":"tool","path":"/shared/paths.py"}\n')
open(HOME + "/proj/data-folder/a.txt", "w", encoding="utf-8").write("keep\n")
LOG = HOME + "/.claude/run/watch/watch-log.jsonl"
RES = []
import itertools
SEQ = itertools.count(1)


def run(hook, tool, tin, env=None, cwd=None, hookdir=HK, sid=None):
    pay = json.dumps({"session_id": sid or "dc-%d" % next(SEQ), "cwd": cwd or HOME + "/proj", "hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tin})
    e = {k: os.environ[k] for k in ("PATH", "LANG", "TMPDIR") if k in os.environ}
    e.update(HOME=HOME, LIFEHACK_ROOT=NOTES, LHB_JOURNAL_PATH=T + "/journal.jsonl", GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_SYSTEM="/dev/null")
    e.update(env or {})
    p = subprocess.run(["bash", os.path.join(hookdir, hook)], input=pay, capture_output=True, text=True, env=e, cwd=HOME + "/proj", timeout=60)
    return p.returncode, p.stdout, p.stderr


def run1(*a, **k):
    """run, and retry once if the once-per-session 'building a skill: read the SOP first' speed bump (another, older guard) answered first"""
    k["sid"] = "dc-r%d" % next(SEQ)
    r = run(*a, **k)
    return run(*a, **k) if r[0] == 2 and "building a skill" in r[2] else r


def asked(r):
    return r[0] == 0 and '"permissionDecision": "ask"' in r[1]


def check(name, ok, detail=""):
    RES.append(ok)
    print("%-62s %s %s" % (name, "MATCH" if ok else "MISMATCH", "" if ok else detail[:300]))


def watchlog():
    try:
        return [json.loads(l) for l in open(LOG, encoding="utf-8")]
    except OSError:
        return []


def conf_copy(name, switches, mode):
    d = T + "/hooks-" + name
    shutil.copytree(HK, d, symlinks=True)
    lines = []
    for ln in open(d + "/roundB.conf", encoding="utf-8"):
        k = ln.split("=")[0]
        if k in switches:
            ln = k + "=on\n"
        if ln.startswith("mode="):
            ln = ""
        lines.append(ln)
    lines.append("mode=%s\n" % mode)
    open(d + "/roundB.conf", "w", encoding="utf-8").write("".join(lines))
    return d


try:
    # ---- placement_user_off (A.6): a person's `off<TAB><check>` line silences exactly that where-to-save check, only with the switch ON
    wn = NOTES + "/newtool.sh"
    W = {"file_path": wn, "content": "echo hi\n"}
    r = run("guard_build_mode.sh", "Write", W)
    check("placement stop fires on code written into notes (baseline)", r[0] == 2, repr(r))
    open(HOME + "/.config/lifehack/placement.conf", "w", encoding="utf-8").write("off\tcode-in-notes\n")
    r = run("guard_build_mode.sh", "Write", W, {"ROUNDB_PLACEMENT_USER_OFF": "on"})
    check("placement_user_off ON + off<TAB>code-in-notes: that check is silent", r[0] == 0, repr(r))
    r = run("guard_build_mode.sh", "Write", W, {"ROUNDB_PLACEMENT_USER_OFF": "off"})
    check("placement_user_off OFF: the off line does nothing (stop fires)", r[0] == 2, repr(r))
    open(HOME + "/.config/lifehack/placement.conf", "w", encoding="utf-8").write("off\tnotes-in-harness\n")
    r = run("guard_build_mode.sh", "Write", W, {"ROUNDB_PLACEMENT_USER_OFF": "on"})
    check("an off line for a DIFFERENT check does not silence this one", r[0] == 2, repr(r))
    open(HOME + "/.config/lifehack/placement.conf", "w", encoding="utf-8").write("off\tfc_force_push\noff\tcanon\n")
    r = run("guard_build_mode.sh", "Write", W, {"ROUNDB_PLACEMENT_USER_OFF": "on"})
    check("an off line naming a fine-china guard is ignored (no off switch for it)", r[0] == 2, repr(r))
    r = run("guard_fine_china_ask.sh", "Bash", {"command": "rm -rf %s/proj/data-folder" % HOME}, {"ROUNDB_FC_FOLDER_DELETE_ASK": "on", "ROUNDB_PLACEMENT_USER_OFF": "on"})
    check("fine-china folder ask still fires with a placement.conf full of off lines", asked(r), repr(r))
    os.remove(HOME + "/.config/lifehack/placement.conf")
    try:
        os.remove(HOME + "/.config/lifehack/placement-stops.json")
    except OSError:
        pass
    hints = []
    for i in range(3):
        r = run("guard_build_mode.sh", "Write", W, {"ROUNDB_PLACEMENT_USER_OFF": "on"})
        hints.append("turning this off may break" in r[2])
    check("repeat stops: no off-hint on stops 1 and 2, hint + warning on stop 3", hints == [False, False, True], str(hints))
    # ---- skills_native_home (A.2)
    sk = PC + "/skills/pondkeeper/SKILL.md"
    r = run("guard_build_mode.sh", "Write", {"file_path": sk, "content": "hi\n"}, {"ROUNDB_SKILLS_NATIVE_HOME": "on"})
    check("ON: SKILL.md under <personal code>/skills is stopped, told ~/.claude/skills", r[0] == 2 and "~/.claude/skills" in r[2], repr(r))
    r = run1("guard_build_mode.sh", "Write", {"file_path": sk, "content": "hi\n"}, {"ROUNDB_SKILLS_NATIVE_HOME": "off"})
    check("OFF: the same write is not stopped by the new rule", r[0] == 0, repr(r))
    new = HOME + "/.claude/skills/newskill/SKILL.md"
    r = run1("guard_build_mode.sh", "Write", {"file_path": new, "content": "hi\n"}, {"ROUNDB_SKILLS_NATIVE_HOME": "on", "ROUNDB_SKILL_EDIT_ASK": "on"})
    check("ON: building a NEW skill in ~/.claude/skills draws no ask", not asked(r) and r[0] == 0, repr(r))
    r = run1("guard_build_mode.sh", "Write", {"file_path": new, "content": "hi\n"}, {"ROUNDB_SKILLS_NATIVE_HOME": "off", "ROUNDB_SKILL_EDIT_ASK": "on"})
    check("OFF: the same new skill asks (old behaviour)", asked(r), repr(r))
    os.makedirs(HOME + "/.claude/skills/oldskill")
    open(HOME + "/.claude/skills/oldskill/SKILL.md", "w", encoding="utf-8").write("old\n")
    r = run1("guard_build_mode.sh", "Edit", {"file_path": HOME + "/.claude/skills/oldskill/SKILL.md", "old_string": "old", "new_string": "new"},
            {"ROUNDB_SKILLS_NATIVE_HOME": "on", "ROUNDB_SKILL_EDIT_ASK": "on"})
    check("ON: editing an EXISTING skill still asks", asked(r), repr(r))
    os.makedirs(HOME + "/Desktop/bar")
    open(HOME + "/Desktop/bar/SKILL.md", "w", encoding="utf-8").write("hi\n")
    for sw, want in (("on", ".claude/skills/bar/SKILL.md"), ("off", "pc/skills/bar")):
        p = subprocess.run([sys.executable, CODE + "/shared/tools/own_list_add.py", "--unhomed", HOME + "/Desktop/bar/SKILL.md"], capture_output=True, text=True,
                           env=dict(os.environ, HOME=HOME, LIFEHACK_ROOT=NOTES, ROUNDB_SKILLS_NATIVE_HOME=sw))
        check("own_list_add suggestion with skills_native_home %s" % sw, want in (p.stdout + p.stderr), (p.stdout + p.stderr)[:200])
    # ---- fc_ask_not_token (Round C practice, still a Round D switch): a confirm token the MODEL types in the command text is not approval
    clr = "gws sheets spreadsheets values clear --params '{\"spreadsheetId\":\"calSheet0001\",\"range\":\"Data!A:Z\"}'"
    md = T + "/marks"
    os.makedirs(md, exist_ok=True)
    r = run("guard_sheet_writes.sh", "Bash", {"command": "LIFEHACK_SHEET_CONFIRM=1 " + clr}, {"ROUNDB_FC_ASK_NOT_TOKEN": "on", "SHEET_LLM_MARKDIR": md})
    check("fc_ask_not_token ON: a model-typed LIFEHACK_SHEET_CONFIRM=1 still draws an ask", asked(r), repr(r))
    r = run("guard_sheet_writes.sh", "Bash", {"command": "LIFEHACK_SHEET_CONFIRM=1 " + clr}, {"ROUNDB_FC_ASK_NOT_TOKEN": "on", "LIFEHACK_REVIEWED_JOB": "1", "SHEET_LLM_MARKDIR": md})
    check("fc_ask_not_token ON: a reviewed launcher (env LIFEHACK_REVIEWED_JOB=1) may carry the token", r[0] == 0 and not asked(r), repr(r))
    r = run("guard_sheet_writes.sh", "Bash", {"command": "LIFEHACK_SHEET_CONFIRM=1 " + clr}, {"ROUNDB_FC_ASK_NOT_TOKEN": "off", "SHEET_LLM_MARKDIR": md})
    check("fc_ask_not_token OFF: the model-typed token is honoured (old behaviour)", r[0] == 0 and not asked(r), repr(r))
    r = run("guard_sheet_writes.sh", "Bash", {"command": clr}, {"ROUNDB_FC_ASK_NOT_TOKEN": "on", "SHEET_LLM_MARKDIR": md})
    check("fc_ask_not_token ON: the destructive clear with no token asks", asked(r), repr(r))
    # ---- watch mode (B.5): logs what would fire, blocks / asks nothing
    cmd = {"command": "rm -rf %s/proj/data-folder" % HOME}
    r = run("guard_fine_china_ask.sh", "Bash", cmd, {"ROUNDB_FC_FOLDER_DELETE_ASK": "on", "LIFEHACK_WATCH": "1"})
    lg = watchlog()
    check("watch: would-be ask is NOT given (exit 0, empty stdout)", r[0] == 0 and not r[1].strip(), repr(r))
    check("watch: it IS logged with switch + would_decision=ask", bool(lg) and "fc_folder_delete_ask" in lg[-1].get("switch", []) and lg[-1].get("would_decision") == "ask", str(lg[-1:]))
    n = len(watchlog())
    run("guard_fine_china_ask.sh", "Bash", {"command": "ls %s/proj" % HOME}, {"ROUNDB_FC_FOLDER_DELETE_ASK": "on", "LIFEHACK_WATCH": "1"})
    check("watch: a harmless command logs nothing", len(watchlog()) == n)
    r = run("guard_fine_china_ask.sh", "Bash", cmd, {"ROUNDB_FC_FOLDER_DELETE_ASK": "on", "LIFEHACK_WATCH": "0"})
    check("LIFEHACK_WATCH=0 forces enforce: ask is given", asked(r), repr(r))
    sop = CODE + "/system/sops/skill-building-sop.md"
    r = run("guard_build_mode.sh", "Bash", {"command": "echo x > " + sop}, {"ROUNDB_FC_SHELL_OVERWRITE": "on", "LIFEHACK_WATCH": "1"})
    check("watch: a would-be BLOCK (shell overwrite of an SOP) exits 0 and is logged as block",
          r[0] == 0 and any(x.get("would_decision") == "block" and "fc_shell_overwrite" in x.get("switch", []) for x in watchlog()), repr(r))
    r = run("guard_build_mode.sh", "Bash", {"command": "echo x > " + sop}, {"ROUNDB_FC_SHELL_OVERWRITE": "on"})
    check("same call, no watch: BLOCKED (exit 2)", r[0] == 2, repr(r))
    d = conf_copy("watch", {"fc_folder_delete_ask"}, "watch")
    r = run("guard_fine_china_ask.sh", "Bash", cmd, hookdir=d)
    check("conf-driven watch (mode=watch + switch on, no env): logs, asks nothing", r[0] == 0 and not r[1].strip() and any("fc_folder_delete_ask" in x.get("switch", []) for x in watchlog()), repr(r))
    r = run("guard_fine_china_ask.sh", "Bash", cmd, {"ROUNDB_FC_FOLDER_DELETE_ASK": "on"}, hookdir=d)
    check("a ROUNDB_* env var turns conf-driven watch OFF (enforce): ask is given", asked(r), repr(r))
    d = conf_copy("enf", {"fc_folder_delete_ask"}, "enforce")
    r = run("guard_fine_china_ask.sh", "Bash", cmd, hookdir=d)
    check("conf mode=enforce: ask is given", asked(r), repr(r))
    # ---- watch crash: the watcher dying must never skip the real guard
    for kind, body in (("import error", "import not_a_real_module_xyz\n"), ("syntax error", "def (:\n"),
                       ("silent exit 0", "import sys\nsys.stdin.buffer.read()\nsys.exit(0)\n"), ("killed", "import os\nos.kill(os.getpid(), 9)\n")):
        d = T + "/hooks-crash"
        shutil.rmtree(d, ignore_errors=True)
        shutil.copytree(HK, d, symlinks=True)
        open(d + "/lib/watch_run.py", "w", encoding="utf-8").write(body)
        r = run("guard_fine_china_ask.sh", "Bash", cmd, {"ROUNDB_FC_FOLDER_DELETE_ASK": "on", "LIFEHACK_WATCH": "1"}, hookdir=d)
        check("watch_run crash (%s): fine-china ask still given" % kind, asked(r), repr(r))
        r = run("guard_build_mode.sh", "Bash", {"command": "echo x > " + sop}, {"ROUNDB_FC_SHELL_OVERWRITE": "on", "LIFEHACK_WATCH": "1"}, hookdir=d)
        check("watch_run crash (%s): build-mode block still exit 2" % kind, r[0] == 2, repr(r))
finally:
    shutil.rmtree(T, ignore_errors=True)
print("DIRECT CALIBRATION: %d of %d" % (sum(RES), len(RES)))
sys.exit(0 if all(RES) else 1)

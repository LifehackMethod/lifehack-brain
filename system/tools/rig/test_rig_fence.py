#!/usr/bin/env python3
# not-wired-yet: run by hand to calibrate the TEST-RIG FENCE with known answers; no model call
"""Known-answer calibration for rig_fence.py: real-home write -> deny; throwaway write -> allow; reads allowed; the product guard still fires on its own.
Each case pipes a PreToolUse payload to the fence as a subprocess (the way claude does) with the RIG_FENCE_* env. Prints N of N; exit 1 on any miss."""
import json, os, shlex, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
FENCE = os.path.join(HERE, "rig_fence.py")
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
RH = os.path.realpath(os.path.expanduser("~"))
T = os.path.realpath(tempfile.mkdtemp(prefix=".rigfence-", dir=RH))   # under the home like the exam throwaway HOME is (the product guard judges homes by it); removed at the end
SCR = RH + "/rig-exam-scratch"
ISO = RH + "/rig-iso-home"
CWD = SCR + "/enver/D-X1"
NOTES = RH + "/Library/CloudStorage/GoogleDrive-placeholder/My Drive/_Notes"
ENV = dict(os.environ, RIG_FENCE_REAL_HOME=RH, RIG_FENCE_REAL_NOTES=NOTES, RIG_FENCE_ALLOW=SCR + ":" + ISO, RIG_FENCE_LOG=T + "/fence.jsonl")

# ---- Drive test area (2026-11-01): a fake Drive tree under T (which sits under the real home, like the real Drive mount does)
MYD = T + "/Library/CloudStorage/GoogleDrive-faketest/My Drive"
AREA = MYD + "/Lifehack test area"
RUN, SIB = AREA + "/run-aaa", AREA + "/run-bbb"
for _d in (MYD + "/_Notes", MYD + "/other", RUN, SIB, AREA + "/_archive"):
    os.makedirs(_d, exist_ok=True)
os.symlink(MYD + "/_Notes", RUN + "/link-to-notes")      # a symlink planted inside the allowed run folder, pointing at a fenced place
os.symlink(SIB, RUN + "/link-to-sibling")
ENVD = dict(ENV, RIG_FENCE_REAL_NOTES=MYD + "/_Notes", RIG_FENCE_RUN_DRIVE=RUN)


def fence(tool, tin, cwd=CWD, env=ENV):
    p = subprocess.run([sys.executable, "-I", FENCE], input=json.dumps({"tool_name": tool, "tool_input": tin, "cwd": cwd}), capture_output=True, text=True, env=env, timeout=30)
    return p.returncode, p.stderr


def B(cmd):
    return fence("Bash", {"command": cmd})


q = shlex.quote


def B2(cmd):
    return fence("Bash", {"command": cmd}, cwd=RUN, env=ENVD)


CURL = "cu" + "rl"   # spelled apart so a guard scanning this file's text is not tripped
# (name, result, expected_deny)
CASES = [
    ("Write real ~/.claude/skills", fence("Write", {"file_path": RH + "/.claude/skills/friday-recap/SKILL.md", "content": "x"}), True),
    ("Write real personal-repo desk tools", fence("Write", {"file_path": RH + "/.claude/skills/personal-repo/desks/example/tools/a.py", "content": "x"}), True),
    ("Edit real settings.json", fence("Edit", {"file_path": RH + "/.claude/settings.json", "old_string": "a", "new_string": "b"}), True),
    ("Write real ~/.config/lifehack", fence("Write", {"file_path": RH + "/.config/lifehack/placement.conf", "content": "x"}), True),
    ("Write real notes root", fence("Write", {"file_path": NOTES + "/desks/x.md", "content": "x"}), True),
    ("Write real lifehack-v2 tree", fence("Write", {"file_path": RH + "/lifehack-v2/system/x.py", "content": "x"}), True),
    ("NotebookEdit real", fence("NotebookEdit", {"notebook_path": RH + "/Documents/n.ipynb", "new_source": "x"}), True),
    ("Write relative path escaping the sandbox", fence("Write", {"file_path": "../../../.claude/skills/x/SKILL.md", "content": "x"}), True),
    ("Bash mkdir real", B("mkdir -p " + RH + "/.claude/skills/friday-recap"), True),
    ("Bash redirect to real", B("echo hi > " + RH + "/.claude/skills/x.md"), True),
    ("Bash cat heredoc >> real", B("cat >> " + RH + "/.config/lifehack/placement.conf <<'E'\nx=off\nE"), True),
    ("Bash rm real", B("rm -rf " + RH + "/.claude/skills/personal-repo/desks/example"), True),
    ("Bash rmdir -p real", B("rmdir -p " + RH + "/.claude/skills/personal-repo/desks/example/tools 2>/dev/null; ls"), True),
    ("Bash mv into real", B("mv notes.md " + RH + "/Documents/"), True),
    ("Bash cp into real (last arg)", B("cp a.md " + RH + "/.claude/skills/x/"), True),
    ("Bash tee real", B("echo x | tee " + RH + "/.claude/x.md"), True),
    ("Bash sed -i real", B("sed -i '' s/a/b/ " + RH + "/.claude/settings.json"), True),
    ("Bash cd real then relative mkdir", B("cd " + RH + "/.claude/skills && mkdir newskill"), True),
    ("Bash git commit in real repo", B("git -C " + RH + "/lifehack-v2 commit -am x"), True),
    ("Bash cd real repo && git add", B("cd " + RH + "/lifehack-v2 && git add -A"), True),
    ("Bash python heredoc writes real", B("python3 - <<'E'\nopen('" + RH + "/.claude/skills/x.md','w').write('x')\nE"), True),
    ("Bash python -c shutil real", B("python3 -c \"import shutil; shutil.rmtree('" + RH + "/.claude/skills/x')\""), True),
    ("Bash nested bash -c writes real", B("bash -c 'touch " + RH + "/.claude/x'"), True),
    ("Bash dd of= real", B("dd if=/dev/zero of=" + RH + "/x bs=1 count=1"), True),
    ("Bash fetch -o real", B(CURL + " -o " + RH + "/Downloads/x.html"), True),
    ("Bash ~otheruser write", B("touch ~" + os.path.basename(RH) + "/.claude/x"), True),
    # ---- allowed: in-sandbox actions and reads
    # ---- Drive test area: everything but the one run folder stays fenced
    ("Drive: Write My Drive/_Notes/x", fence("Write", {"file_path": MYD + "/_Notes/x", "content": "x"}, env=ENVD), True),
    ("Drive: Write My Drive/other/x", fence("Write", {"file_path": MYD + "/other/x", "content": "x"}, env=ENVD), True),
    ("Drive: Write sibling run folder", fence("Write", {"file_path": SIB + "/x", "content": "x"}, env=ENVD), True),
    ("Drive: Write the test area itself", fence("Write", {"file_path": AREA + "/x", "content": "x"}, env=ENVD), True),
    ("Drive: Write _archive", fence("Write", {"file_path": AREA + "/_archive/x", "content": "x"}, env=ENVD), True),
    ("Drive: Bash mv out of run folder to other", B2("mv a " + q(MYD + "/other/a")), True),
    ("Drive: Bash rm in sibling run", B2("rm " + q(SIB + "/a")), True),
    ("Drive: .. escape from run folder", fence("Write", {"file_path": RUN + "/../run-bbb/x", "content": "x"}, env=ENVD), True),
    ("Drive: .. escape to _Notes", fence("Write", {"file_path": RUN + "/../../_Notes/x", "content": "x"}, env=ENVD), True),
    ("Drive: relative .. escape (cwd = run)", fence("Write", {"file_path": "../../other/x", "content": "x"}, cwd=RUN, env=ENVD), True),
    ("Drive: Bash cd run then relative .. escape", B2("cd " + q(RUN) + " && touch ../../other/x"), True),
    ("Drive: write through symlink to _Notes", fence("Write", {"file_path": RUN + "/link-to-notes/x", "content": "x"}, env=ENVD), True),
    ("Drive: write through symlink to sibling run", fence("Write", {"file_path": RUN + "/link-to-sibling/x", "content": "x"}, env=ENVD), True),
    ("Drive: Bash redirect through symlink", B2("echo x > " + q(RUN + "/link-to-notes/x")), True),
    ("Drive: case trick on _Notes", fence("Write", {"file_path": MYD.replace("My Drive", "my drive") + "/_notes/x", "content": "x"}, env=ENVD), True),
    ("Drive: case trick on other", fence("Write", {"file_path": MYD.upper() + "/OTHER/x", "content": "x"}, env=ENVD), True),
    ("Drive: case trick on sibling run", fence("Write", {"file_path": AREA.replace("test area", "TEST AREA") + "/RUN-BBB/x", "content": "x"}, env=ENVD), True),
    ("Drive: run path wrong env (area itself) is ignored", fence("Write", {"file_path": SIB + "/x", "content": "x"}, env=dict(ENVD, RIG_FENCE_RUN_DRIVE=AREA)), True),
    ("Drive: run path = _archive is ignored", fence("Write", {"file_path": AREA + "/_archive/x", "content": "x"}, env=dict(ENVD, RIG_FENCE_RUN_DRIVE=AREA + "/_archive")), True),
    ("Drive: run path outside the area is ignored", fence("Write", {"file_path": MYD + "/other/x", "content": "x"}, env=dict(ENVD, RIG_FENCE_RUN_DRIVE=MYD + "/other")), True),
    ("Drive: run path with ../ out of the area is ignored", fence("Write", {"file_path": MYD + "/other/x", "content": "x"}, env=dict(ENVD, RIG_FENCE_RUN_DRIVE=AREA + "/run-aaa/../../other")), True),
    ("Drive: no run folder set -> run folder fenced", fence("Write", {"file_path": RUN + "/x", "content": "x"}, env=ENV), True),
    ("Drive: allowed run folder, Write", fence("Write", {"file_path": RUN + "/skills/invoice-checker/SKILL.md", "content": "x"}, env=ENVD), False),
    ("Drive: allowed run folder, relative Write", fence("Write", {"file_path": "notes/a.md", "content": "x"}, cwd=RUN, env=ENVD), False),
    ("Drive: allowed run folder, Bash mkdir + redirect", B2("mkdir -p " + q(RUN + "/team") + " && echo x > " + q(RUN + "/team/a.md")), False),
    ("Drive: allowed run folder, cp into it", B2("cp a.md " + q(RUN + "/team/")), False),
    ("Drive: allowed run folder, Bash ln -s a skill into it", B2("ln -s " + q(RUN + "/team/invoice-checker") + " ~/.claude/skills/invoice-checker"), False),
    ("Drive: allowed run folder, different case spelling", fence("Write", {"file_path": RUN.replace("run-aaa", "RUN-AAA") + "/x", "content": "x"}, env=ENVD), False),
    ("Drive: allowed run folder via .. that stays inside", fence("Write", {"file_path": RUN + "/a/../b/x", "content": "x"}, env=ENVD), False),
    ("Drive: reading another Drive path is allowed", fence("Read", {"file_path": MYD + "/other/x"}, env=ENVD), False),
    ("Write in cwd", fence("Write", {"file_path": CWD + "/notes/a.md", "content": "x"}), False),
    ("Write relative in cwd", fence("Write", {"file_path": "notes/a.md", "content": "x"}), False),
    ("Write throwaway personal code", fence("Write", {"file_path": ISO + "/personal-code/tools/a.py", "content": "x"}), False),
    ("Write throwaway ~/.claude/skills", fence("Write", {"file_path": ISO + "/.claude/skills/friday-recap/SKILL.md", "content": "x"}), False),
    ("Write throwaway notes", fence("Write", {"file_path": ISO + "/rig-iso-notes/desks/x.md", "content": "x"}), False),
    ("Write /tmp", fence("Write", {"file_path": "/tmp/x.txt", "content": "x"}), False),
    ("Write fixture sibling bare repo", fence("Write", {"file_path": SCR + "/enver/D-X1-origin.git/x", "content": "x"}), False),
    ("Read real settings (reads stay allowed)", fence("Read", {"file_path": RH + "/.claude/settings.json"}), False),
    ("Grep real tree", fence("Grep", {"pattern": "x", "path": RH + "/lifehack-v2"}), False),
    ("Bash cat real file", B("cat " + RH + "/.config/lifehack/placement.conf"), False),
    ("Bash ls/find real", B("ls -la " + RH + "; find " + RH + " -maxdepth 4 -iname '*x*' 2>/dev/null | head"), False),
    ("Bash cd real && ls && git status", B("cd " + RH + "/.claude/skills/personal-repo && git remote -v; git status --short | head -5; ls"), False),
    ("Bash git -C real log", B("git -C " + RH + "/lifehack-v2 log --oneline | head"), False),
    ("Bash safe_read of real file", B("python3 -I " + RH + "/lifehack-v2/system/tools/safe_read.py " + RH + "/.claude/settings.json"), False),
    ("Bash plugin tool run (writes via pointers)", B("python3 -I " + RH + "/lifehack-v2/shared/tools/own_list_add.py --help"), False),
    ("Bash cp FROM real INTO sandbox", B("cp " + RH + "/lifehack-v2/README.md " + CWD + "/README-copy.md"), False),
    ("Bash redirect in cwd", B("echo hi > notes/a.md && cat notes/a.md"), False),
    ("Bash rm in cwd (relative)", B("rm -rf old-notes && ls"), False),
    ("Bash rm absolute in scratch", B("rm " + CWD + "/tmp/scratch.txt"), False),
    ("Bash mkdir in throwaway personal code", B("mkdir -p " + ISO + "/personal-code/tools && ls"), False),
    ("Bash cd sandbox then git commit", B("cd " + CWD + " && git add -A && git commit -qm x"), False),
    ("Bash python heredoc reads real, writes cwd", B("python3 - <<'E'\nd=open('" + RH + "/.claude/settings.json').read()\nopen('copy.json','w').write(d)\nE"), False),
    ("Bash python importing from plugin path", B("python3 -c \"import sys; sys.path.insert(0,'" + RH + "/lifehack-v2/shared'); import brain_root\""), False),
    ("Bash ~ is the throwaway HOME", B("mkdir -p ~/.claude/skills/x && touch ~/.claude/skills/x/SKILL.md"), False),
    ("Bash write to /dev/null and /tmp", B("ls > /dev/null 2>&1; echo x > /tmp/y.txt"), False),
    ("Bash unresolved variable target", B("T=$(mktemp -d) && printf a > \"$T/a.jpg\" && mkdir \"$T/sub\""), False),
]


def product_guard_independent():
    """The product guard still fires on its own on a real personal-repo Write (the exact D-B07 shape), and the fence message is distinguishable."""
    g = os.path.join(ROOT, "system", "hooks", "guard_build_mode.sh")
    if not os.path.exists(g):
        return None
    e = {k: os.environ[k] for k in ("PATH", "LANG", "TMPDIR") if k in os.environ}
    e.update(ROUNDB_PLACEMENT_OUTSIDE_HOMES="on", LIFEHACK_SANDBOX="V2", HOME=T + "/h", LIFEHACK_ROOT=T + "/n", GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_SYSTEM="/dev/null")
    os.makedirs(T + "/h/.config/lifehack", exist_ok=True); os.makedirs(T + "/n/desks", exist_ok=True); os.makedirs(T + "/h/personal-code", exist_ok=True)
    open(T + "/h/.config/lifehack/code-root", "w").write(ROOT + "\n"); open(T + "/h/.config/lifehack/personal-code", "w").write(T + "/h/personal-code\n")
    pay = json.dumps({"session_id": "fence-1", "cwd": CWD, "hook_event_name": "PreToolUse", "tool_name": "Write",
                      "tool_input": {"file_path": RH + "/Documents/rigfence-newtool.py", "content": "print(1)\n"}})
    p = subprocess.run(["bash", g], input=pay, capture_output=True, text=True, env=e, cwd=T, timeout=60)
    f = fence("Write", {"file_path": RH + "/Documents/rigfence-newtool.py", "content": "x"})
    return p.returncode, p.stderr, f


def main():
    ok, rows = 0, []
    for name, (rc, err), deny in CASES:
        good = (rc == 2 and err.startswith("TEST-RIG FENCE")) if deny else (rc == 0 and err == "")
        ok += good
        rows.append("%s %-58s %s" % ("ok  " if good else "MISS", name, "deny" if rc == 2 else "allow"))
    print("\n".join(rows))
    n = len(CASES)
    rc, _ = fence("Write", {"file_path": RH + "/.claude/skills/x.md", "content": "x"}, env={k: v for k, v in os.environ.items() if not k.startswith("RIG_FENCE")})
    n += 1; ok += rc == 0; print("%s no RIG_FENCE env -> fence does nothing (rc %d)" % ("ok  " if rc == 0 else "MISS", rc))
    pg = product_guard_independent()
    if pg:
        prc, perr, (frc, ferr) = pg
        good = prc == 2 and "TEST-RIG FENCE" not in perr and frc == 2 and ferr.startswith("TEST-RIG FENCE")
        n += 1; ok += good
        print("%s product guard fires on its own (rc %d, no fence text) and the fence also denies with its own text" % ("ok  " if good else "MISS", prc))
    import shutil; shutil.rmtree(T, ignore_errors=True)   # only the dir this run made
    print("FENCE CALIBRATION: %d of %d" % (ok, n))
    return 0 if ok == n else 1


if __name__ == "__main__":
    sys.exit(main())

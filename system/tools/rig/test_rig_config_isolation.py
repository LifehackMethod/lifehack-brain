#!/usr/bin/env python3
# not-wired-yet: run by hand and by run-all-tests.sh; checks rig_config_isolation.py + the student read-denies in rig_sandbox.py, no paid model call
"""Known-answer + FAIL-FIRST checks for rig config isolation (2026-11-02, record rig-config-isolation).
Every guard is shown failing on a DECOY first: a fake "real home" holds a marker CLAUDE.md, skill and agent, and the leak must be SEEN (marker
read, decoy skill in the init event) before the fix is shown to stop it. The live part runs the real `claude` binary with a fake token and the
network cut (the sandbox opens only a dead localhost port), so nothing is billed; it is skipped when claude or sandbox-exec is missing.
Prints N of N; exit 1 on any miss."""
import json, os, secrets, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rig_sandbox as sb  # noqa: E402
import rig_config_isolation as ci  # noqa: E402

T = os.path.realpath(tempfile.mkdtemp(prefix="rigcfg-"))
ok = n = 0


def check(name, cond, detail=""):
    global ok, n
    n += 1
    ok += bool(cond)
    print("%s %s%s" % ("ok  " if cond else "MISS", name, "" if cond else "   <- " + str(detail)[:400]))


def w(p, txt):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(txt)


NONCE = secrets.token_hex(4)
MARK = "DECOY-PERSONAL-MARKER-" + NONCE
D = os.path.join(T, "decoy-real-home")   # stands in for the runner's real home
SK, AG = "decoyskill" + NONCE, "decoyagent" + NONCE
w(os.path.join(D, ".claude", "CLAUDE.md"), MARK + "\n")
w(os.path.join(D, ".claude", "skills", SK, "SKILL.md"), "---\nname: %s\ndescription: decoy\n---\n%s\n" % (SK, MARK))
w(os.path.join(D, ".claude", "agents", AG + ".md"), "---\nname: %s\ndescription: decoy\n---\n%s\n" % (AG, MARK))
w(os.path.join(D, ".claude", "hooks", "h.sh"), MARK + "\n")
w(os.path.join(D, ".claude", "settings.json"), '{"m": "%s"}' % MARK)
w(os.path.join(D, ".claude", "settings.local.json"), '{"m": "%s"}' % MARK)
w(os.path.join(D, ".claude", "projects", "x", "keep.txt"), "not config\n")
w(os.path.join(D, ".claude.json"), '{"m": "%s"}' % MARK)

# ---- 1. rig dir rules ----------------------------------------------------------------------------------------------------------------
RH = os.path.realpath(os.path.expanduser("~"))
check("rig dir: a path under the real home is refused", ci.rig_dir_problems(os.path.join(RH, "rig-exam-scratch", "x"), RH))
check("rig dir: the decoy home's own subdir is refused (real_home=D)", ci.rig_dir_problems(os.path.join(D, "work"), D))
SHARED = os.path.dirname(ci.RIG_ROOT)
for bad in ("/tmp/lifehack-rig/x", "/private/var/x", "/var/x", ci.RIG_ROOT + "/tmp/x", SHARED + "/scratch/x", SHARED + "/a/scratchpad"):
    check("rig dir: refused " + bad, ci.rig_dir_problems(bad, RH))
check("rig dir: RIG_ROOT/<label> is accepted", not ci.rig_dir_problems(os.path.join(ci.RIG_ROOT, "label-x", "work"), RH),
      ci.rig_dir_problems(os.path.join(ci.RIG_ROOT, "label-x", "work"), RH))
try:
    ci.check_rig_dir(os.path.join(RH, "rig-exam-scratch"), RH)
    check("check_rig_dir REFUSES a real-home dir", False)
except SystemExit as e:
    check("check_rig_dir REFUSES a real-home dir", "REFUSED" in str(e), e)
probe_dir = os.path.join(ci.RIG_ROOT, "_selftest-" + NONCE)
try:
    check("check_rig_dir: RIG_ROOT is writable here", ci.check_rig_dir(probe_dir, RH) == os.path.realpath(probe_dir))
finally:
    shutil.rmtree(probe_dir, ignore_errors=True)

# ---- 2. which real-home paths the student profile read-denies ------------------------------------------------------------------------
pcp = sb.personal_config_paths(D)
want = [os.path.join(D, ".claude", n) for n in ("CLAUDE.md", "skills", "agents", "hooks", "settings.json", "settings.local.json")] + [os.path.join(D, ".claude.json")]
check("personal_config_paths = CLAUDE.md, skills, agents, hooks, settings*.json, .claude.json", pcp == want, pcp)
check("personal_config_paths leaves projects/ (memory) readable", not any("projects" in p for p in pcp))

# ---- 3. kernel read-deny, fail-first ------------------------------------------------------------------------------------------------
READER = ("import os,sys,errno\nfor p in sys.argv[1:]:\n try:\n  x = ''.join(sorted(os.listdir(p))) if os.path.isdir(p) else open(p).read()\n"
          "  print('READ', p, 'MARK' if (x and ('%s' in x or '%s' in x)) else 'nomark')\n except OSError as e:\n  print('EPERM' if e.errno in (errno.EPERM, errno.EACCES) else 'ERR', p)\n") % (MARK, SK)
have_sbx = os.path.isfile(sb.SANDBOX_EXEC)
if have_sbx:
    targets = [os.path.join(D, ".claude", "CLAUDE.md"), os.path.join(D, ".claude", "skills"), os.path.join(D, ".claude.json")]

    def run_reader(read_deny):
        prof = sb.write_profile(sb.profile([T], T, 1, real_home_dir=D, read_deny=read_deny), os.path.join(T, "r%d.sb" % len(read_deny)))
        p = subprocess.run(sb.wrap([sys.executable, "-I", "-c", READER] + targets, prof), capture_output=True, text=True, timeout=60)
        return p.stdout
    out0 = run_reader(())
    check("FAIL-FIRST: without the read-deny the actor READS the decoy marker", out0.count("MARK") == len(targets), out0)
    out1 = run_reader(pcp)
    check("with the read-deny every decoy config path is EPERM", out1.count("EPERM") == len(targets) and "MARK" not in out1, out1)
    spec = sb.canary_spec(os.path.join(T, "cn"), 1, [], [T], ["/x"], "n", real_home_dir=D, escapes=False, read_denied_extra=pcp)
    check("the canary is asked to prove every student read-deny (C8)", all(p in spec["read_denied"] for p in pcp), spec["read_denied"])
else:
    print("skip kernel read-deny (no sandbox-exec)")

# ---- 4. the personal-load detector, fail-first --------------------------------------------------------------------------------------
NAMES = ci.personal_names(D)
check("personal_names reads the decoy skill + agent from the home", SK in NAMES["skills"] and AG in NAMES["agents"], NAMES)
V2LIKE = os.path.join(D, "plugin")   # a plugin dir UNDER the home (like ~/lifehack-v2) is allowed
ROOTS = [os.path.join(T, "run"), V2LIKE]
clean = {"skills": ["lifehack-brain:" + SK, "deep-research"], "agents": ["Explore", "lifehack-brain:worker"],
         "memory_paths": {"auto": os.path.join(T, "run", "home", ".claude", "projects", "m")}}
f = lambda init=clean, hooks=(), instr=(), st="{}": ci.findings(init, list(hooks), list(instr), st, D, ROOTS, NAMES)
check("clean init (plugin-prefixed same name) -> no finding", f() == [], f())
check("FAIL-FIRST: decoy personal skill in init -> finding", f(dict(clean, skills=clean["skills"] + [SK])))
check("FAIL-FIRST: decoy personal agent in init -> finding", f(dict(clean, agents=clean["agents"] + [AG])))
check("FAIL-FIRST: memory path in the home -> finding", f(dict(clean, memory_paths={"auto": os.path.join(D, ".claude", "projects", "m")})))
check("FAIL-FIRST: the home's CLAUDE.md loaded -> finding", f(instr=[os.path.join(D, ".claude", "CLAUDE.md")]))
check("an instructions file inside the run dirs -> no finding", f(instr=[os.path.join(T, "run", "CLAUDE.md")]) == [])
check("FAIL-FIRST: hook output naming a personal skill folder -> finding",
      f(hooks=[{"hook_name": "SessionStart:startup", "stderr": "bash: /x/.claude/skills/%s/system/hooks/a.sh: No such file" % SK}]))
check("FAIL-FIRST: hook output naming the real home -> finding", f(hooks=[{"hook_name": "S", "stdout": "read " + D + "/notes"}]))
check("hook output naming the plugin dir under the home -> no finding", f(hooks=[{"hook_name": "S", "stdout": "plugin root = " + V2LIKE}]) == [])
check("FAIL-FIRST: settings running a hook from a personal skill folder -> finding",
      f(st='{"hooks":{"SessionStart":[{"hooks":[{"command":"bash \\"$HOME/.claude/skills/%s/h.sh\\""}]}]}}' % SK))
check("settings naming only the plugin dir -> no finding", f(st='{"c": "python3 -I %s/rig_fence.py"}' % V2LIKE) == [])
check("no init event -> finding (nothing proves what loaded)", f(init=None))
import rig_isolation as isol  # noqa: E402
fs = isol.fence_settings(None, os.path.join(T, "student.settings.json"))
check("student plugin-only settings: only the rig fence hook, nothing personal",
      ci.findings({"skills": [], "agents": []}, [], [], open(fs, encoding="utf-8").read(), RH, [HERE], ci.personal_names(RH)) == [] and list(json.load(open(fs, encoding="utf-8"))["hooks"]) == ["PreToolUse"], open(fs, encoding="utf-8").read())

# ---- 5. live, zero spend: the real claude binary, network cut ----------------------------------------------------------------------
claude = shutil.which("claude")
if claude and have_sbx and os.environ.get("RIG_CFG_SKIP_LIVE") != "1":
    def live(tag, cwd, read_deny=()):
        iso = os.path.join(T, "iso-" + tag)
        os.makedirs(os.path.join(iso, ".claude"), exist_ok=True)
        os.makedirs(cwd, exist_ok=True)
        il = os.path.join(T, tag + ".il.jsonl")
        st = ci.il_settings(None, os.path.join(T, tag + ".settings.json"), il)
        prof = sb.write_profile(sb.profile([iso, cwd, T], cwd, ci.DEAD_PORT, real_home_dir=D, read_deny=read_deny), os.path.join(T, tag + ".sb"))
        env = ci.dead_net_env({"HOME": iso, "PATH": "/usr/bin:/bin", "SHELL": "/bin/bash", "TMPDIR": T, "DISABLE_AUTOUPDATER": "1",
                               "CLAUDE_CODE_OAUTH_TOKEN": "sk-ant-oat01-offline-probe-not-a-token", "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"})
        cmd = sb.wrap([os.path.realpath(claude), "-p", "hi", "--model", "haiku", "--setting-sources", "project,local", "--settings", st,
                       "--strict-mcp-config", "--output-format", "stream-json", "--verbose"], prof)
        init, hooks, instr = ci.probe(cmd, cwd, env, os.path.join(T, tag + ".stream.jsonl"), il)
        return init, ci.findings(init, hooks, instr, open(st, encoding="utf-8").read(), D, [iso, cwd], NAMES), instr
    i0, f0, in0 = live("under", os.path.join(D, "rig-exam-scratch", "case"))
    check("FAIL-FIRST live: cwd under the decoy home loads its CLAUDE.md + skill + agent (walk-up)",
          i0 is not None and any("CLAUDE.md" in x for x in f0) and any(SK in x for x in f0) and any(AG in x for x in f0), (f0, in0))
    i1, f1, _ = live("outside", os.path.join(T, "shared-rig", "case"))
    check("live: cwd OUTSIDE the home -> init present, nothing personal", i1 is not None and f1 == [], f1)
    i2, f2, _ = live("denied", os.path.join(D, "rig-exam-scratch", "case2"), read_deny=sb.personal_config_paths(D))
    check("live: cwd under the home BUT kernel read-denied -> claude still runs (init), nothing personal", i2 is not None and f2 == [], f2)
else:
    print("skip live zero-spend probe (claude or sandbox-exec missing, or RIG_CFG_SKIP_LIVE=1)")

shutil.rmtree(T, ignore_errors=True)
print("%d of %d" % (ok, n))
sys.exit(0 if ok == n else 1)

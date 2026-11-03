#!/usr/bin/env python3
# not-wired-yet: run by hand and by run-all-tests.sh; checks rig_live_free.install_enver_hooks' /tmp rewrite of the Enver hook COPIES, no model call
"""Rig D-P06 (pinned4, 2026-11-02): an Enver hook copied into the throwaway HOME (guard_hook_syntax.sh) writes a hardcoded /tmp/<file>.
The actor sandbox denies writes under /private/tmp, so the COPY crashed and falsely blocked commits. The rig now maps each literal /tmp/<file>
in a copied SHELL script's code lines to <throwaway HOME>/tmp/<file> (the actor TMPDIR, inside an allowed write root). The original is never
touched; comments, ${TMPDIR:-/tmp}, /private/tmp/... and non-shell files are left alone; every rewrite is recorded.
Prints N of N; exit 1 on any miss."""
import json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rig_live_free as rlf  # noqa: E402
import rig_sandbox as sb  # noqa: E402

_T = tempfile.TemporaryDirectory(prefix="rigtmpmap-")
T = os.path.realpath(_T.name)
ok = n = 0


def check(name, cond, detail=""):
    global ok, n
    n += 1
    ok += bool(cond)
    print("%s %s%s" % ("ok  " if cond else "MISS", name, "" if cond else "   <- " + str(detail)[:400]))


def w(p, t):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(t)


X = "rigtmpmap-%d-%s.err" % (os.getpid(), os.path.basename(T))   # unique: a fixed /tmp/x may already exist (it is a directory here)
HOOK = ("#!/bin/bash\n"
        "# writes its scratch to /tmp/X (this comment stays)\n"
        "echo hi 2>/tmp/" + X + "\n"
        "cat /tmp/" + X + " 2>/dev/null\n"
        "D=\"${TMPDIR:-/tmp}/fallback\"; P=/private/tmp/keep-me\n")
PY = "def f(p):\n    return p.startswith(\"/tmp/\")\n"
fake = os.path.join(T, "realhome")
hook = os.path.join(fake, ".claude", "skills", "priv", "system", "hooks", "h.sh")
pyf = os.path.join(fake, ".claude", "skills", "priv", "system", "tools", "t.py")
w(hook, HOOK)
w(pyf, PY)
lab = os.path.join(T, "lab.json")
w(lab, json.dumps({"hooks": {"PreToolUse": [{"hooks": [{"type": "command", "command": 'bash "$HOME/.claude/skills/priv/system/hooks/h.sh"'},
                                                        {"type": "command", "command": 'python3 "$HOME/.claude/skills/priv/system/tools/t.py"'}]}]}}))
iso = os.path.join(T, "allowed", "rig-iso-home")
os.makedirs(iso)
before = os.stat(hook)

got = rlf.install_enver_hooks(iso, fake, lab)
cp = os.path.join(iso, ".claude", "skills", "priv", "system", "hooks", "h.sh")
txt = open(cp, encoding="utf-8").read()
tmpd = os.path.join(iso, "tmp")
check("both named scripts copied", sorted(got) == sorted([".claude/skills/priv/system/hooks/h.sh", ".claude/skills/priv/system/tools/t.py"]), got)
check("copy: the /tmp/x write is mapped to the throwaway HOME's tmp", ("2>%s/%s" % (tmpd, X)) in txt and ("cat %s/%s" % (tmpd, X)) in txt, txt)
check("copy: no code line still names the /tmp path", not any("/tmp/" + X in ln and not ln.lstrip().startswith("#") and tmpd + "/" + X not in ln for ln in txt.splitlines()), txt)
check("copy: the comment, ${TMPDIR:-/tmp} and /private/tmp/... are left alone",
      "# writes its scratch to /tmp/X (this comment stays)" in txt and "${TMPDIR:-/tmp}/fallback" in txt and "P=/private/tmp/keep-me" in txt, txt)
check("copy: the throwaway tmp dir exists", os.path.isdir(tmpd))
check("copy: still read-only", not os.access(cp, os.W_OK))
check("non-shell file copied byte-for-byte (its /tmp/ is logic, not a path it writes)",
      open(os.path.join(iso, ".claude", "skills", "priv", "system", "tools", "t.py"), encoding="utf-8").read() == PY)
check("original hook untouched (content, mtime, mode)", open(hook, encoding="utf-8").read() == HOOK and os.stat(hook).st_mtime == before.st_mtime
      and os.stat(hook).st_mode == before.st_mode)
rw = getattr(rlf, "ENVER_TMP_REWRITES", None)
check("rewrite recorded: exactly the one file, one distinct path, two occurrences",
      rw == {".claude/skills/priv/system/hooks/h.sh": {"/tmp/" + X: [tmpd + "/" + X, 2]}}, rw)
st = os.path.join(T, "st")
os.makedirs(st)
open(os.path.join(st, ".rig-student"), "w", encoding="utf-8").close()
check("student setup: nothing copied, nothing recorded", rlf.install_enver_hooks(st, fake, lab) == [] and rlf.ENVER_TMP_REWRITES == {} if rw is not None else False)

# ---- under the REAL actor sandbox profile (rig_sandbox.profile, throwaway HOME allowed): the copy runs, the original's /tmp write is EPERM
if sb.available(workdir=T)[0]:
    prof = sb.write_profile(sb.profile([iso], iso, 1), os.path.join(T, "actor.sb"))
    env = {"PATH": "/usr/bin:/bin", "HOME": iso, "TMPDIR": tmpd}
    r_new = subprocess.run(sb.wrap(["/bin/bash", cp], prof), capture_output=True, text=True, timeout=60, env=env, cwd=iso)
    check("sandbox: the rewritten copy runs clean (its stderr file lands in the throwaway tmp)",
          r_new.returncode == 0 and os.path.isfile(os.path.join(tmpd, X)) and "Operation not permitted" not in r_new.stderr, (r_new.returncode, r_new.stderr))
    r_old = subprocess.run(sb.wrap(["/bin/bash", hook], prof), capture_output=True, text=True, timeout=60, env=env, cwd=iso)
    check("sandbox FAIL-FIRST: the unrewritten original's /tmp write is refused (the D-P06 crash)", "Operation not permitted" in r_old.stderr, r_old.stderr)
else:
    print("skip sandbox checks: sandbox-exec unavailable")

print("%d of %d" % (ok, n))
sys.exit(0 if ok == n else 1)

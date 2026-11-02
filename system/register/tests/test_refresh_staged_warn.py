#!/usr/bin/env python3
"""test_refresh_staged_warn.py -- refresh_staged.py WARNS (stderr, exit 0) when the staged register.jsonl
differs from HEAD in rows for files the commit does not touch (the stale-blob-left-by-a-refused-commit case).
Light: a throwaway git repo with a two-row register; the script runs as the pre-commit hook would."""
import json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "refresh_staged.py")
REG = "system/register/register.jsonl"
ENV = {**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null"}
fails = 0


def git(d, *a):
    r = subprocess.run(["git", "-C", d, *a], capture_output=True, text=True, env=ENV)
    assert r.returncode == 0, (a, r.stderr)
    return r


def row(i, path, sha):
    return json.dumps({"id": i, "type": "hook", "repo": "public", "path": path, "sha": sha}, sort_keys=True)


def make(parent):
    d = tempfile.mkdtemp(prefix="warn-", dir=parent)
    git(d, "init", "-q"); git(d, "config", "user.email", "t@t"); git(d, "config", "user.name", "t")
    os.makedirs(os.path.join(d, "system/register")); os.makedirs(os.path.join(d, "system/hooks"))
    for n in ("a.sh", "b.sh"):
        open(os.path.join(d, "system/hooks", n), "w", encoding="utf-8").write("echo " + n + "\n")
    base = [row("hook:a", "/system/hooks/a.sh", "aaaaaaaa"), row("hook:b", "/system/hooks/b.sh", "bbbbbbbb")]
    open(os.path.join(d, REG), "w", encoding="utf-8").write("\n".join(base) + "\n")
    git(d, "add", "-A"); git(d, "commit", "-qm", "base")
    return d, base


def run(d):
    r = subprocess.run([sys.executable, SCRIPT], cwd=d, capture_output=True, text=True, env=ENV)
    return r.returncode, r.stdout, r.stderr


def check(name, cond):
    global fails
    print(("  PASS  " if cond else "  FAIL  ") + name)
    fails += 0 if cond else 1


# every temp dir this file makes lives inside ONE TemporaryDirectory, removed when the process exits (leaked test temp dirs filled a disk, 2026-11-01)
_SCRATCH = tempfile.TemporaryDirectory(prefix="warn-", dir=os.environ.get("REFRESH_TEST_SCRATCH") or None)
parent = _SCRATCH.name
# 1. stale register staged, commit touches only b.sh -> row for a.sh differs -> WARN, exit 0
d, base = make(parent)
open(os.path.join(d, REG), "w", encoding="utf-8").write("\n".join([row("hook:a", "/system/hooks/a.sh", "STALE000"), base[1]]) + "\n")
open(os.path.join(d, "system/hooks/b.sh"), "a", encoding="utf-8").write("# edit\n")
git(d, "add", REG, "system/hooks/b.sh")
rc, out, err = run(d)
check("stale foreign row staged -> exit 0", rc == 0)
check("stale foreign row staged -> warns naming hook:a", "WARNING" in err and "hook:a" in err)
# 2. the differing row IS a file the commit touches -> no warning
d, base = make(parent)
open(os.path.join(d, REG), "w", encoding="utf-8").write("\n".join([row("hook:a", "/system/hooks/a.sh", "NEWSHA00"), base[1]]) + "\n")
open(os.path.join(d, "system/hooks/a.sh"), "a", encoding="utf-8").write("# edit\n")
git(d, "add", REG, "system/hooks/a.sh")
rc, out, err = run(d)
check("own row changed -> no warning", rc == 0 and "WARNING" not in err)
# 3. register identical to HEAD -> silent
d, base = make(parent)
open(os.path.join(d, "system/hooks/b.sh"), "a", encoding="utf-8").write("# edit\n")
git(d, "add", "system/hooks/b.sh")
rc, out, err = run(d)
check("register unchanged -> silent", rc == 0 and "WARNING" not in err and not out)
# 4. a deleted foreign row also warns
d, base = make(parent)
open(os.path.join(d, REG), "w", encoding="utf-8").write(base[1] + "\n")
open(os.path.join(d, "system/hooks/b.sh"), "a", encoding="utf-8").write("# edit\n")
git(d, "add", REG, "system/hooks/b.sh")
rc, out, err = run(d)
check("foreign row deleted -> warns", rc == 0 and "hook:a" in err)
print("--- RESULT: %s ---" % ("GREEN" if not fails else "RED"))
sys.exit(1 if fails else 0)

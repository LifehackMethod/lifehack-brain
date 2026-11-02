#!/usr/bin/env python3
# not-wired-yet: run by hand with the rig tests; fires no model (a fake `claude` on PATH)
"""A foreign NEW file (another window's work in a real repo) that the transcript only "mentions" via the init skill list must never be deleted by the live runner."""
import json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rig_live_free as lf  # noqa: E402


def main():
    t = os.path.realpath(tempfile.mkdtemp())
    try:
        ops, v2, notes, scratch, work = (os.path.join(t, x) for x in ("ops", "v2", "notes", "scratch", "work"))
        for r in (ops, v2):
            os.makedirs(r)
            subprocess.run(["git", "init", "-q", r], capture_output=True)
        os.makedirs(os.path.join(notes, "desks")); os.makedirs(scratch); os.makedirs(work)
        foreign = os.path.join(ops, ".claude", "skills", "marc-checkin", "SKILL.md")
        bindir = os.path.join(t, "bin"); os.makedirs(bindir)
        fake = os.path.join(bindir, "claude")
        with open(fake, "w", encoding="utf-8") as f:
            f.write("#!/bin/bash\nmkdir -p '%s' && echo x > '%s'\n" % (os.path.dirname(foreign), foreign))
            # 2026-11-02 launcher canary: record what the ACTOR process really got (env names, PATH, whether gws resolves)
            f.write("env | cut -d= -f1 > '%s'\necho \"$PATH\" > '%s'\n(command -v gws gh || echo NONE) > '%s'\n" % (
                os.path.join(t, "child-env.txt"), os.path.join(t, "child-path.txt"), os.path.join(t, "child-which.txt")))
            f.write("""echo '{"type":"system","subtype":"init","skills":["marc-checkin"],"session_id":"s1"}'\n""")
            f.write("""echo '{"type":"result","num_turns":1,"total_cost_usd":0}'\n""")
        os.chmod(fake, 0o755)
        with open(os.path.join(bindir, "gws"), "w", encoding="utf-8") as g:   # a cloud CLI next to claude, like Homebrew's bin
            g.write("#!/bin/sh\necho REAL-DRIVE-FILES\n")
        os.chmod(os.path.join(bindir, "gws"), 0o755)
        os.environ.update(GOOGLE_WORKSPACE_CLI_CONFIG_DIR="/nonexistent/gws-cron", GH_TOKEN="fake", AWS_PROFILE="fake")
        os.environ["PATH"] = bindir + os.pathsep + os.environ["PATH"]
        lf.V2, lf.OPS = v2, ops

        class _PassSandbox:   # run_one refuses without a sandbox since 2026-11-02 (rig-actor-sandbox); this test checks cleanup + env scrub, not the kernel layer (test_rig_sandbox.py does)
            def case(self, name, allow_write, cwd, settings_path, write_denied, notes_roots, env):
                return (lambda cmd: cmd), env
        lf.SBX = _PassSandbox()
        case = {"id": "t1", "live": {"prompt": "x", "sop": [], "shared_ref": [], "wrong_re": [], "kind": "build"}}
        base = os.path.join(t, "base-settings.json"); open(base, "w", encoding="utf-8").write("{}")   # run_one now builds the fenced copy of a base settings file
        home = os.path.join(t, "rig-iso-home"); os.makedirs(home)   # run_one refuses the real HOME since 2026-11-02 (rig-cred-isolation)
        r = lf.run_one(case, notes, work, scratch, extra_env={"HOME": home}, settings=base)
        assert os.path.exists(foreign), "the foreign file was deleted"
        assert not any(foreign in c for c in r["cleaned"]), r["cleaned"]
        rd = lambda n: open(os.path.join(t, n), encoding="utf-8").read()
        names = rd("child-env.txt").split()
        assert not [n for n in names if n.startswith(("GOOGLE_", "GH_", "AWS_"))], names
        assert bindir not in rd("child-path.txt"), "the actor PATH still holds the parent's bin dir"
        assert rd("child-which.txt").strip() == "NONE", "gws/gh resolved in the actor"
        assert "GOOGLE_WORKSPACE_CLI_CONFIG_DIR" in r["env_dropped"] and "claude" in r["actor_bins"], (r["env_dropped"], r["actor_bins"])
        print("test_rig_cleanup: actor env scrubbed (dropped %d names), gws/gh not found, parent bin dir not on PATH" % len(r["env_dropped"]))
        print("test_rig_cleanup: ok")
    finally:
        shutil.rmtree(t, ignore_errors=True)


if __name__ == "__main__":
    main()

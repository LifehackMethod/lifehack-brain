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
            f.write("""echo '{"type":"system","subtype":"init","skills":["marc-checkin"],"session_id":"s1"}'\n""")
            f.write("""echo '{"type":"result","num_turns":1,"total_cost_usd":0}'\n""")
        os.chmod(fake, 0o755)
        os.environ["PATH"] = bindir + os.pathsep + os.environ["PATH"]
        lf.V2, lf.OPS = v2, ops
        case = {"id": "t1", "live": {"prompt": "x", "sop": [], "shared_ref": [], "wrong_re": [], "kind": "build"}}
        r = lf.run_one(case, notes, work, scratch)
        assert os.path.exists(foreign), "the foreign file was deleted"
        assert not any(foreign in c for c in r["cleaned"]), r["cleaned"]
        print("test_rig_cleanup: ok")
    finally:
        shutil.rmtree(t, ignore_errors=True)


if __name__ == "__main__":
    main()

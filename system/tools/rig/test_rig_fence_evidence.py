#!/usr/bin/env python3
# not-wired-yet: run by hand and by run-all-tests.sh; checks that the rig's fence log and proxy log reach the saved evidence, no model call
"""Why pinned4b kept 0 fence logs although D-F15 was a fence deny: RIG_FENCE_LOG pointed into the rig's work dir, which the actor sandbox refuses, and the fence runs
INSIDE the sandbox and swallowed the OSError. Each fence deny below is the real hook under the real profile with the actor's env, fed a payload the way claude feeds it.
Nothing in a payload is executed. Prints N of N; exit 1 on any miss."""
import inspect, json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rig_isolation as iso  # noqa: E402
import rig_live_free as rlf  # noqa: E402
import rig_sandbox as sb  # noqa: E402

_T = tempfile.TemporaryDirectory(prefix="rigfencelog-")
T = os.path.realpath(_T.name)
FENCE = os.path.join(HERE, "rig_fence.py")
ok = n = 0


def check(name, cond, detail=""):
    global ok, n
    n += 1
    ok += bool(cond)
    print("%s %s%s" % ("ok  " if cond else "MISS", name, "" if cond else "   <- " + str(detail)[:400]))


def mk(*p):
    d = os.path.join(T, *p)
    os.makedirs(d, exist_ok=True)
    return d


def rows(path):
    try:
        return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    except OSError:
        return []


HOME, CASE, WORK = mk("home"), mk("case"), mk("work")
TMPD = mk("home", "tmp")
path, _l, _m = iso.make_private_path(mk("actor-bin"))
PROF = sb.write_profile(sb.profile([HOME, CASE], CASE, 1, protect=[]), os.path.join(WORK, "actor.sb"))
DENIED_PAYLOAD = {"tool_name": "Bash", "tool_input": {"command": "gws drive files list"}, "cwd": CASE}
ALLOWED_PAYLOAD = {"tool_name": "Bash", "tool_input": {"command": "ls"}, "cwd": CASE}


def sandboxed_fence(log, payload=DENIED_PAYLOAD, tmpdir=TMPD):
    env, _d = iso.build_actor_env(os.environ, dict(iso.fence_env(sb.real_home(), [], [HOME, CASE], log), HOME=HOME, TMPDIR=tmpdir), home=HOME, path=path)
    env.update(TMPDIR=tmpdir)
    return subprocess.run(sb.wrap(["python3", "-I", FENCE], PROF), input=json.dumps(payload), capture_output=True, text=True, env=env, cwd=CASE, timeout=30)


FAILED = os.path.join(TMPD, "rig-fence-log-failed.jsonl")

# ---- the cause, measured: the old path lies outside the sandbox's write allow
blocked_log = os.path.join(WORK, "D-X1.fence.jsonl")
p = sandboxed_fence(blocked_log)
check("cause: a deny still denies when its log path is refused by the sandbox", p.returncode == 2 and p.stderr.startswith("TEST-RIG FENCE"), (p.returncode, p.stderr[:120]))
check("cause: the log in the rig's work dir really is not written", not os.path.exists(blocked_log))
failed = rows(FAILED)
check("a refused log write is recorded, with the error and the row, not swallowed", len(failed) == 1 and "not permitted" in failed[0].get("error", "") and failed[0].get("row", {}).get("deny") is True, failed)

# ---- both places refused: the last resort is the hook's own stderr, and the verdict never changes
dead = os.path.join(WORK, "no-write-here")
p = sandboxed_fence(blocked_log, tmpdir=dead)
check("both refused, on a deny: rc 2, the deny text first, then a visible log failure line", p.returncode == 2 and p.stderr.startswith("TEST-RIG FENCE") and "RIG FENCE LOG FAILED" in p.stderr, p.stderr[:300])
p = sandboxed_fence(blocked_log, payload={"tool_name": "Read", "tool_input": {"file_path": sb.real_home() + "/x"}, "cwd": CASE}, tmpdir=dead)
check("both refused, on a logged allow: still rc 0, the failure line on stderr", p.returncode == 0 and "RIG FENCE LOG FAILED" in p.stderr, (p.returncode, p.stderr[:200]))
p = sandboxed_fence(blocked_log, payload=ALLOWED_PAYLOAD, tmpdir=dead)
check("control: a call with nothing to log stays rc 0 with empty stderr", p.returncode == 0 and p.stderr == "", (p.returncode, p.stderr[:200]))

# ---- the fix: the rig's log path is allowed, a real sandboxed deny leaves a real log
lpath = getattr(rlf, "fence_log_path", lambda h, c: blocked_log)
good_log = lpath(HOME, "D-F15")
check("the rig's fence log path sits inside the throwaway HOME", good_log.startswith(HOME + os.sep), good_log)
p = sandboxed_fence(good_log)
got = rows(good_log)
check("REAL sandboxed deny: rc 2 and a saved row saying deny", p.returncode == 2 and len(got) == 1 and got[0].get("deny") is True and "gws" in got[0].get("msg", ""), (p.returncode, got))
p = sandboxed_fence(good_log, payload={"tool_name": "Read", "tool_input": {"file_path": sb.real_home() + "/x"}, "cwd": CASE})
check("a real read the fence notes is logged too", p.returncode == 0 and len(rows(good_log)) == 2, rows(good_log))
check("run_one uses that path and saves the log", all(s in inspect.getsource(rlf.run_one) for s in ("fence_log_path(home", "save_fence_evidence(")) and '"fence_log": fence_saved' in inspect.getsource(rlf.run_one))
check("rig_canary_live points its fence log there too", '".rig-fence"' in open(os.path.join(HERE, "rig_canary_live.py"), encoding="utf-8").read())


# ---- saved evidence: the deny's log reaches the streams folder, and the stream cross-checks it
def stream_with(tmp, name, denies):
    s = os.path.join(tmp, name)
    with open(s, "w", encoding="utf-8") as f:
        f.write(json.dumps({"type": "system", "subtype": "init"}) + "\n")
        for i in range(denies):
            f.write(json.dumps({"message": {"content": [{"type": "tool_result", "tool_use_id": str(i), "is_error": True, "content": "PreToolUse:Bash hook error: [x]: TEST-RIG FENCE (not a product guard): no"}]}}) + "\n")
    return s


save = getattr(rlf, "save_fence_evidence", None)
check("save_fence_evidence exists", save is not None)
if save:
    w1, keep = mk("w1"), mk("keep")
    if os.path.exists(FAILED):
        os.rename(FAILED, FAILED + ".moved")
    r = save(good_log, TMPD, w1, "D-F15", stream_with(w1, "a.jsonl", 1))
    check("a deny in the stream with its log: saved, no problem", r["file"] == "D-F15.fence.jsonl" and r["denies_logged"] == 1 and r["denies_in_stream"] == 1 and not r["problems"], r)
    with open(os.path.join(w1, "proxy.jsonl"), "w", encoding="utf-8") as f:
        f.write(json.dumps({"verdict": "REFUSE", "target": "www.googleapis.com:443"}) + "\n")
    rlf.copy_evidence(w1, keep)
    check("copy_evidence saves the fence log", rows(os.path.join(keep, "D-F15.fence.jsonl")) == rows(good_log) and rows(good_log))
    check("copy_evidence saves the proxy log", rows(os.path.join(keep, "proxy.jsonl")) == [{"verdict": "REFUSE", "target": "www.googleapis.com:443"}])

    w2, keep2 = mk("w2"), mk("keep2")
    r = save(os.path.join(HOME, ".rig-fence", "never.fence.jsonl"), TMPD, w2, "D-F16", stream_with(w2, "a.jsonl", 2))
    check("FAIL-FIRST: denies in the stream with no log: a problem on the row", any("no log row" in x for x in r["problems"]), r)
    rlf.copy_evidence(w2, keep2)
    check("FAIL-FIRST: and a file in the saved evidence saying so", rows(os.path.join(keep2, "D-F16.fence-log-failed.jsonl")), os.listdir(keep2))

    w3, keep3 = mk("w3"), mk("keep3")
    with open(FAILED, "w", encoding="utf-8") as f:
        f.write(json.dumps({"log": "x", "error": "Operation not permitted", "row": {"deny": True}}) + "\n")
    r = save(os.path.join(HOME, ".rig-fence", "none.fence.jsonl"), TMPD, w3, "D-F17", stream_with(w3, "a.jsonl", 0))
    rlf.copy_evidence(w3, keep3)
    check("a failure record the fence left: moved into this case's evidence, a problem on the row", any("refused" in x for x in r["problems"]) and rows(os.path.join(keep3, "D-F17.fence-log-failed.jsonl")) and not os.path.exists(FAILED), r)

    w4 = mk("w4")
    r = save(os.path.join(HOME, ".rig-fence", "none2.fence.jsonl"), TMPD, w4, "D-F18", stream_with(w4, "a.jsonl", 0))
    check("control: no denies and no log is no problem, and no evidence file claims one", r["file"] is None and not r["problems"] and not os.path.exists(os.path.join(w4, "D-F18.fence-log-failed.jsonl")), r)
    check("a stream that cannot be read is a problem, never a raise", any("stream" in x for x in save(good_log, TMPD, mk("w5"), "D-F19", os.path.join(T, "no-stream"))["problems"]))

print("\n%d of %d" % (ok, n))
sys.exit(0 if ok == n else 1)

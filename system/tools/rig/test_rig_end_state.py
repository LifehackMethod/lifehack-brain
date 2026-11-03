#!/usr/bin/env python3
# not-wired-yet: run by hand and by run-all-tests.sh; fires no model (a fake `claude` on PATH), no spend
"""rig_live_free.run_one (plan fix 23(c), rig-capture-personal-end-state): the throwaway HOME is deleted after a run and the personal folder is wiped
for the next case, so a scorer could only read `listed:` output. Each case now leaves <id>.end-state.json in the evidence: the personal folder's own
list, a file manifest, copies of small text files, what THIS case changed, and before/after sha256 of the fixture originals. Checks:
1. own list captured, manifest true (path, size, sha256), .git internals out, oversize / binary / symlink / fifo not copied and never followed;
2. two cases sharing a HOME and a personal folder: each case's delta, list rows and copies are its own;
3. the isolated setup: a case's evidence survives the wipe, and the next case starts clean;
4. fixture hashes: before differs from after only for what the session changed;
5. a capture error is recorded, and the case keeps its bucket.
Prints N of N; exit 1 on any miss."""
import hashlib, json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rig_live_free as lf  # noqa: E402

ok = n = 0


def check(name, cond, detail=""):
    global ok, n
    n += 1
    if cond:
        ok += 1
        print("ok   " + name)
    else:
        print("FAIL " + name + (" :: " + str(detail)[:300] if detail != "" else ""))


class _PassSandbox:   # run_one refuses without a sandbox (rig-actor-sandbox); the kernel layer is test_rig_sandbox.py's job
    def case(self, name, allow_write, cwd, settings_path, write_denied, notes_roots, env, read_deny=(), home_read=None):
        return (lambda cmd: cmd), env


FAKE_CLAUDE = r'''#!%(py)s
# the "session": what it does to the personal folder and the fixture depends on the case's cwd name
import os, sys
home = os.environ["HOME"]
ptr = os.path.join(home, ".config", "lifehack", "personal-code")
p = open(ptr).readline().strip() if os.path.exists(ptr) else os.path.join(home, "lifehack-personal-code")
cid = os.path.basename(os.getcwd())
def w(rel, txt, mode="w"):
    q = os.path.join(p, rel)
    os.makedirs(os.path.dirname(q), exist_ok=True)
    with open(q, mode) as f:
        f.write(txt)
if cid == "caseA":
    w("tools/a.py", "print('a')\n")
    w("register.jsonl", '{"id":"a","path":"tools/a.py"}\n', "a")
    w("big.txt", "x" * (%(big)d))
    w("blob.bin", b"\x00\x01binary", "wb")
    os.symlink(%(secret)r, os.path.join(p, "link-to-secret"))
    os.mkfifo(os.path.join(p, "a-fifo"))
    w(".git/from-session", "git internals\n")
elif cid == "caseB":
    w("tools/b.py", "print('b')\n")
    w("tools/a.py", "print('a changed')\n")
    w("register.jsonl", '{"id":"b","path":"tools/b.py"}\n', "a")
    os.remove(os.path.join(p, "tools", "prior.py"))
elif cid == "caseC":
    w("tools/c.py", "print('c')\n")
    w("register.jsonl", '{"id":"c","path":"tools/c.py"}\n', "a")
elif cid in ("caseF", "caseG"):
    with open("notes/ideas.md", "a") as f:
        f.write("- changed by the session\n")
    os.remove("old-notes/a.md")
    with open("brand-new.md", "w") as f:
        f.write("new\n")
elif cid.startswith("caseE"):
    w("tools/e.py", "print('e')\n")
    w("register.jsonl", '{"id":"e","path":"tools/e.py"}\n', "a")
print('{"type":"result","num_turns":1,"total_cost_usd":0}')
'''


def case(cid, fixture=None):
    live = {"prompt": "x", "sop": [], "shared_ref": [], "wrong_re": [], "kind": "build"}
    if fixture:
        live["fixture"] = fixture
    return {"id": cid, "live": live}


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def main():
    t = os.path.realpath(tempfile.mkdtemp(prefix="rigendstate-"))
    try:
        ops, v2, notes, scratch, work, keep = (os.path.join(t, x) for x in ("ops", "v2", "notes", "scratch", "work", "keep"))
        for r in (ops, v2):
            os.makedirs(r)
            subprocess.run(["git", "init", "-q", r], capture_output=True)
        os.makedirs(os.path.join(notes, "desks")); os.makedirs(scratch); os.makedirs(work); os.makedirs(keep)
        secret = os.path.join(t, "SECRET-outside.txt")
        open(secret, "w", encoding="utf-8").write("SECRET-MARKER\n")
        bindir = os.path.join(t, "bin"); os.makedirs(bindir)
        big = 200 * 1024
        with open(os.path.join(bindir, "claude"), "w", encoding="utf-8") as f:
            f.write(FAKE_CLAUDE % {"py": sys.executable, "big": big, "secret": secret})
        os.chmod(os.path.join(bindir, "claude"), 0o755)
        os.environ["PATH"] = bindir + os.pathsep + os.environ["PATH"]
        lf.V2, lf.OPS = v2, ops
        lf.SBX = _PassSandbox()
        base = os.path.join(t, "base-settings.json"); open(base, "w", encoding="utf-8").write("{}")

        def run(cid, home, fixture=None):
            r = lf.run_one(case(cid, fixture), notes, work, scratch, extra_env={"HOME": home}, settings=base)
            lf.copy_evidence(work, keep)
            return r

        def evidence(cid):
            p = os.path.join(keep, cid + ".end-state.json")
            if not os.path.isfile(p):
                return {}
            with open(p, encoding="utf-8") as f:
                return json.load(f)

        # ---- 1 + 2: a caller's own HOME (not reset between cases): one HOME, one personal folder, two cases
        shared = os.path.join(t, "caller-home"); os.makedirs(shared)
        pc = os.path.join(shared, "lifehack-personal-code"); os.makedirs(os.path.join(pc, "tools"))
        subprocess.run(["git", "init", "-q", pc], capture_output=True)
        prior_row = '{"id":"prior","path":"tools/prior.py"}\n'
        open(os.path.join(pc, "register.jsonl"), "w", encoding="utf-8").write(prior_row)
        open(os.path.join(pc, "tools", "prior.py"), "w", encoding="utf-8").write("print('prior')\n")

        ra = run("caseA", shared)
        ea = evidence("caseA")
        check("the end state is saved in the per-label evidence", bool(ea), sorted(os.listdir(keep)))
        ol = ea.get("own_list") or {}
        list_bytes = open(os.path.join(pc, "register.jsonl"), "rb").read()
        check("own list: the file's text is captured", ol.get("text") == list_bytes.decode(), ol)
        check("own list: its hash and size are true", ol.get("sha256") == sha256(list_bytes) and ol.get("size") == len(list_bytes), ol)
        check("own list: the case's new row is named on its own", ol.get("new_lines") == ['{"id":"a","path":"tools/a.py"}'], ol.get("new_lines"))
        man = {x["path"]: x for x in ea.get("manifest") or []}
        a_py = b"print('a')\n"
        check("manifest: path, size and sha256 are true", (man.get("tools/a.py") or {}).get("sha256") == sha256(a_py) and man["tools/a.py"].get("size") == len(a_py), man.get("tools/a.py"))
        check("manifest: .git internals are out", not [p for p in man if p == ".git" or p.startswith(".git/") or "/.git/" in p], sorted(man))
        check("manifest: an oversize file is listed and hashed", (man.get("big.txt") or {}).get("size") == big and bool(man["big.txt"].get("sha256")), man.get("big.txt"))
        tf = ea.get("text_files") or {}
        check("copies: a small text file is copied", tf.get("tools/a.py") == a_py.decode(), sorted(tf))
        check("copies: an oversize file is not, and says why", "big.txt" not in tf and "big.txt" in (ea.get("not_copied") or {}), ea.get("not_copied"))
        check("copies: a binary file is not, and says why", "blob.bin" not in tf and "blob.bin" in (ea.get("not_copied") or {}), ea.get("not_copied"))
        check("limits are stated in the evidence", isinstance((ea.get("limits") or {}).get("text_file_max_bytes"), int), ea.get("limits"))
        blob = json.dumps(ea)
        check("a symlink is recorded, never followed", (man.get("link-to-secret") or {}).get("type") == "symlink" and "SECRET-MARKER" not in blob, man.get("link-to-secret"))
        check("a fifo is recorded without hanging", (man.get("a-fifo") or {}).get("type") == "other", man.get("a-fifo"))
        check("delta A: what was there before the case is not A's", "tools/prior.py" not in (ea.get("delta") or {}).get("added", ["tools/prior.py"]), ea.get("delta"))
        check("copies A: an unchanged earlier file is not copied", "tools/prior.py" not in tf, sorted(tf))
        check("manifest A: an unchanged earlier file is still in the end state, marked so", (man.get("tools/prior.py") or {}).get("status") == "unchanged", man.get("tools/prior.py"))
        check("the result row names the evidence", (ra.get("end_state") or {}).get("file") == "caseA.end-state.json", ra.get("end_state"))

        run("caseB", shared)
        eb = evidence("caseB")
        d = eb.get("delta") or {}
        check("delta B: only what B added", d.get("added") == ["tools/b.py"], d)
        check("delta B: only what B modified", d.get("modified") == ["register.jsonl", "tools/a.py"], d)
        check("delta B: what B removed", d.get("removed") == ["tools/prior.py"], d)
        check("own list B: only B's row is new, on a list that holds all three", (eb.get("own_list") or {}).get("new_lines") == ['{"id":"b","path":"tools/b.py"}']
              and all(x in (eb.get("own_list") or {}).get("text", "") for x in ('"prior"', '"a"', '"b"')), eb.get("own_list"))
        check("copies B: B's files, not A's big or binary leftovers", sorted(eb.get("text_files") or {}) == ["tools/a.py", "tools/b.py"], sorted(eb.get("text_files") or {}))
        check("case A's evidence was not rewritten by case B", evidence("caseA").get("delta") == ea.get("delta"), evidence("caseA").get("delta"))

        # ---- a student's folder has no list until the first kept tool; a folder that is not there at all is not an error
        st = os.path.join(t, "student-pc"); os.makedirs(st)
        stw = os.path.join(t, "student-work"); os.makedirs(stw)
        sto = os.path.join(stw, "s.end-state.json")
        try:
            smark = lf.end_state_mark(st, None)
            open(os.path.join(st, "register.jsonl"), "w", encoding="utf-8").write('{"id":"first"}\n')
            lf.write_end_state(smark, st, None, sto)
            es = json.load(open(sto, encoding="utf-8"))
            nowhere = os.path.join(t, "no-personal-folder")
            sn = lf.write_end_state(lf.end_state_mark(nowhere, None), nowhere, None, sto)
            en = json.load(open(sto, encoding="utf-8"))
        except Exception as e:
            es, sn, en = {"raised": repr(e)}, {"errors": [repr(e)]}, {}
        check("a list born in this case: not there before, its row is new", (es.get("own_list") or {}).get("existed_before") is False and (es.get("own_list") or {}).get("new_lines") == ['{"id":"first"}'], es)
        check("a missing personal folder: no list, no error", sn.get("errors") == [] and (en.get("own_list") or {}).get("exists") is False and en.get("manifest") == [], (sn, en))

        # ---- 3: the isolated setup: fresh_personal wipes the folder at each case's start
        iso = os.path.join(t, "iso", "rig-iso-home"); os.makedirs(os.path.join(iso, ".config", "lifehack"))
        ipc = os.path.join(iso, "personal-code")
        lf.fresh_personal(ipc)
        open(os.path.join(iso, ".config", "lifehack", "personal-code"), "w", encoding="utf-8").write(ipc + "\n")
        run("caseC", iso)
        ec = evidence("caseC")
        check("isolated: the case's own list row is captured", (ec.get("own_list") or {}).get("new_lines") == ['{"id":"c","path":"tools/c.py"}'], ec.get("own_list"))
        check("isolated: marked as such", ec.get("isolated") is True, ec.get("isolated"))
        run("caseD", iso)   # does nothing in the personal folder
        ed = evidence("caseD")
        check("isolated: the next case's delta is empty after the wipe", ed.get("delta") == {"added": [], "modified": [], "removed": []}, ed.get("delta"))
        check("isolated: the next case's list is empty and has no new rows", (ed.get("own_list") or {}).get("exists") is True and (ed.get("own_list") or {}).get("text") == "" and (ed.get("own_list") or {}).get("new_lines") == [], ed.get("own_list"))
        check("isolated: the earlier case's evidence survives the wipe", "tools/c.py" in {x["path"] for x in evidence("caseC").get("manifest") or []}, evidence("caseC").get("manifest"))

        # ---- 4: fixture originals, plain and git
        for cid, fx in (("caseF", "plain"), ("caseG", "git")):
            run(cid, iso, fixture=fx)
            fo = evidence(cid).get("fixture_originals") or {}
            be, af = fo.get("before") or {}, fo.get("after") or {}
            check(cid + ": before holds the true hash of an original", be.get("rules.md") == sha256(b"# My rules\n- you must save often\n- you must back up\n"), be.get("rules.md"))
            check(cid + ": a file the session changed differs", be.get("notes/ideas.md") and af.get("notes/ideas.md") and be["notes/ideas.md"] != af["notes/ideas.md"]
                  and "notes/ideas.md" in (fo.get("changed") or []), (be.get("notes/ideas.md"), af.get("notes/ideas.md")))
            check(cid + ": a file left alone matches", bool(be.get("rules.md")) and be.get("rules.md") == af.get("rules.md") and "rules.md" not in (fo.get("changed") or []), fo.get("changed"))
            check(cid + ": a removed original is named", "old-notes/a.md" in be and af.get("old-notes/a.md") is None and "old-notes/a.md" in (fo.get("removed") or []), fo.get("removed"))
            check(cid + ": a new file is not an original", "brand-new.md" not in be and "brand-new.md" in (fo.get("added") or []), fo.get("added"))
            check(cid + ": .git internals are out", not [p for p in be if p == ".git" or p.startswith(".git/")], [p for p in be if p.startswith(".git")][:3])
        check("no fixture: nothing is invented", evidence("caseC").get("fixture_originals") is None and "fixture_originals" in evidence("caseC"), evidence("caseC").get("fixture_originals"))

        # ---- 5: a capture error is recorded and never touches the case
        control = run("caseE0", iso)
        real_mark, real_manifest = getattr(lf, "end_state_mark", None), getattr(lf, "tree_manifest", None)
        # 5a. the walker dies at the end of the case: the mark worked, the capture did not
        calls = []
        def dies_second_time(*a, **k):
            calls.append(1)
            if len(calls) > 1:
                raise RuntimeError("planted capture failure")
            return real_manifest(*a, **k)
        lf.tree_manifest = dies_second_time
        try:
            r1 = run("caseE1", iso, fixture=None)
        except BaseException as e:   # the point of the test: nothing may escape into the case
            r1 = {"bucket": "RAISED %r" % (e,)}
        finally:
            lf.tree_manifest = real_manifest
        e1 = evidence("caseE1")
        check("a capture error keeps the case's bucket", r1.get("bucket") == control.get("bucket") and r1.get("bucket_raw") == control.get("bucket_raw"), (r1.get("bucket"), control.get("bucket")))
        check("a capture error is recorded in the evidence", "planted capture failure" in json.dumps(e1.get("errors") or []), e1)
        check("a capture error is on the result row", "planted capture failure" in json.dumps((r1.get("end_state") or {}).get("errors") or []), r1.get("end_state"))
        # 5b. the mark itself dies: no baseline, so no delta is claimed; the own list and manifest can still be taken
        def mark_dies(*a, **k):
            raise RuntimeError("planted mark failure")
        lf.end_state_mark = mark_dies
        try:
            r2 = run("caseE2", iso)
        except BaseException as e:
            r2 = {"bucket": "RAISED %r" % (e,)}
        finally:
            lf.end_state_mark = real_mark
        e2 = evidence("caseE2")
        check("a failed mark keeps the case's bucket", r2.get("bucket") == control.get("bucket"), r2.get("bucket"))
        check("a failed mark is recorded", "planted mark failure" in json.dumps(e2.get("errors") or []), e2.get("errors"))
        check("a failed mark claims no delta", "delta" in e2 and e2.get("delta") is None, e2.get("delta"))
        check("a failed mark still captures the own list", '"e"' in (e2.get("own_list") or {}).get("text", ""), e2.get("own_list"))
        # 5c. one unreadable file: recorded, everything else still captured
        pcu = os.path.join(t, "unread"); os.makedirs(pcu)
        for nm, body in (("bad.txt", "b\n"), ("good.txt", "g\n")):
            open(os.path.join(pcu, nm), "w", encoding="utf-8").write(body)
        wdir = os.path.join(t, "unread-work"); os.makedirs(wdir)
        out = os.path.join(wdir, "u.end-state.json")
        summary = None
        try:
            mark = lf.end_state_mark(pcu, None)
            os.chmod(os.path.join(pcu, "bad.txt"), 0)
            summary = lf.write_end_state(mark, pcu, None, out)
            eu = json.load(open(out, encoding="utf-8"))
        except Exception as e:
            eu = {"raised": repr(e)}
        finally:
            os.chmod(os.path.join(pcu, "bad.txt"), 0o644)
        mu = {x["path"]: x for x in eu.get("manifest") or []}
        check("an unreadable file is recorded as an error", "bad.txt" in json.dumps(eu.get("errors") or []), eu)
        check("the other files are still captured", (mu.get("good.txt") or {}).get("sha256") == sha256(b"g\n"), mu.get("good.txt"))
        # 5d. the evidence cannot be written at all: no raise, and the row still says so
        try:
            s = lf.write_end_state(lf.end_state_mark(pcu, None), pcu, None, os.path.join(t, "no-such-dir", "x.end-state.json"))
            check("an unwritable evidence file does not raise, and the summary says so", bool(s.get("errors")), s)
        except Exception as e:
            check("an unwritable evidence file does not raise, and the summary says so", False, repr(e))
    finally:
        shutil.rmtree(t, ignore_errors=True)
    print("test_rig_end_state: %d of %d" % (ok, n))
    sys.exit(0 if ok == n else 1)


if __name__ == "__main__":
    main()

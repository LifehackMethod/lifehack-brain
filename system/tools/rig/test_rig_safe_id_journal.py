#!/usr/bin/env python3
# not-wired-yet: run by hand with the rig tests; fires no model (a fake `claude` on PATH), no spend
"""rig_live_free.run_one (2026-11-02, rig-safe-id-journal):
1. a case id that is not a plain name ("", "..", "a/b", "../x") is REFUSED before anything is deleted: run_one rmtrees <scratch>/<id>, and
   config_preflight rmtrees the dirname of <HOME>/.rig-config-probe/<id>.il.jsonl, so a bad id could wipe the scratch, its parent or the HOME;
2. every real case id in cases/*.jsonl passes;
3. the fire journal in the throwaway HOME (shared across cases, so it grows) is sliced per case into <work>/<id>.fire-journal.jsonl,
   and the evidence copy puts it in the per-label streams folder (`keep`)."""
import glob, json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rig_live_free as lf  # noqa: E402


class _PassSandbox:   # run_one refuses without a sandbox (rig-actor-sandbox); the kernel layer is test_rig_sandbox.py's job
    def case(self, name, allow_write, cwd, settings_path, write_denied, notes_roots, env, read_deny=(), home_read=None):
        return (lambda cmd: cmd), env


def case(cid):
    return {"id": cid, "live": {"prompt": "x", "sop": [], "shared_ref": [], "wrong_re": [], "kind": "build"}}


def main():
    t = os.path.realpath(tempfile.mkdtemp())
    try:
        ops, v2, notes, scratch, work, keep = (os.path.join(t, x) for x in ("ops", "v2", "notes", "scratch", "work", "keep"))
        for r in (ops, v2):
            os.makedirs(r)
            subprocess.run(["git", "init", "-q", r], capture_output=True)
        os.makedirs(os.path.join(notes, "desks")); os.makedirs(scratch); os.makedirs(work); os.makedirs(keep)
        home = os.path.join(t, "rig-iso-home"); os.makedirs(home)
        # fake claude: appends ONE journal row per session (tagged with the case's cwd name) to the SHARED throwaway HOME's journal
        bindir = os.path.join(t, "bin"); os.makedirs(bindir)
        with open(os.path.join(bindir, "claude"), "w", encoding="utf-8") as f:
            f.write("#!/bin/bash\nmkdir -p \"$HOME/.claude/run\"\n"
                    "echo \"{\\\"session_id\\\":\\\"s-$(basename \"$PWD\")\\\",\\\"hook\\\":\\\"h\\\",\\\"decision\\\":\\\"deny\\\"}\" >> \"$HOME/.claude/run/fire-journal.jsonl\"\n"
                    "echo '{\"type\":\"result\",\"num_turns\":1,\"total_cost_usd\":0}'\n")
        os.chmod(os.path.join(bindir, "claude"), 0o755)
        os.environ["PATH"] = bindir + os.pathsep + os.environ["PATH"]
        lf.V2, lf.OPS = v2, ops
        lf.SBX = _PassSandbox()
        base = os.path.join(t, "base-settings.json"); open(base, "w", encoding="utf-8").write("{}")

        # 1. bad ids refused BEFORE any rmtree: sentinels in the scratch, its parent and the HOME must all survive
        sentinels = [os.path.join(scratch, "SENTINEL"), os.path.join(t, "SENTINEL"), os.path.join(home, "SENTINEL")]
        for s in sentinels:
            open(s, "w", encoding="utf-8").write("keep me\n")
        for bad in ("", "..", "a/b", "../x", ".", ".hidden", "a..b", "/abs", "a b", "x\n"):
            try:
                lf.run_one(case(bad), notes, work, scratch, extra_env={"HOME": home}, settings=base)
                refused = None
            except SystemExit as e:
                refused = str(e)
            assert refused and "REFUSED" in refused and "case id" in refused, (bad, refused)
            assert all(os.path.exists(s) for s in sentinels), "a sentinel was deleted by id %r" % bad
            assert os.listdir(scratch) == ["SENTINEL"], (bad, os.listdir(scratch))
        print("test_rig_safe_id_journal: 10 bad case ids refused before anything was deleted (3 sentinels survive)")

        # 2. every real case id passes
        ids = []
        for fn in sorted(glob.glob(os.path.join(HERE, "cases", "*.jsonl"))):
            for ln in open(fn, encoding="utf-8"):
                try:
                    d = json.loads(ln)
                except ValueError:
                    continue
                if isinstance(d, dict) and "id" in d:
                    ids.append(d["id"])
        assert len(ids) > 300, len(ids)
        for cid in ids:
            lf.check_case_id(cid)   # raises SystemExit on a bad one
        print("test_rig_safe_id_journal: all %d real case ids pass" % len(ids))

        # 3. the journal: two cases share the HOME; each case's slice holds ONLY its own row, and the evidence copy lands it in keep
        pre = os.path.join(home, ".claude", "run", "fire-journal.jsonl")
        os.makedirs(os.path.dirname(pre), exist_ok=True)
        open(pre, "w", encoding="utf-8").write('{"session_id":"earlier-run","hook":"h","decision":"allow"}\n')
        for cid in ("caseA", "caseB"):
            lf.run_one(case(cid), notes, work, scratch, extra_env={"HOME": home}, settings=base)
            lf.copy_evidence(work, keep)
        assert len(open(pre, encoding="utf-8").read().splitlines()) == 3, "the shared journal should hold 3 rows"
        for cid in ("caseA", "caseB"):
            kept = os.path.join(keep, cid + ".fire-journal.jsonl")
            assert os.path.isfile(kept), "no fire journal kept for %s: %s" % (cid, sorted(os.listdir(keep)))
            rows = [json.loads(x) for x in open(kept, encoding="utf-8").read().splitlines() if x.strip()]
            assert [r["session_id"] for r in rows] == ["s-" + cid], (cid, rows)
        # a rotation mid-case (live file renamed to a shard) still yields exactly the case's rows
        open(pre, "a", encoding="utf-8").write('{"session_id":"between","hook":"h"}\n')
        mark = lf.journal_mark(home)
        open(pre, "a", encoding="utf-8").write('{"session_id":"mine-1","hook":"h"}\n')
        os.rename(pre, pre + ".1700000000.42")
        open(pre, "w", encoding="utf-8").write('{"session_id":"mine-2","hook":"h"}\n')
        out = os.path.join(work, "rot.fire-journal.jsonl")
        lf.journal_slice(home, mark, out)
        assert [json.loads(x)["session_id"] for x in open(out, encoding="utf-8").read().splitlines()] == ["mine-1", "mine-2"], open(out, encoding="utf-8").read()
        # no journal at all -> no file (nothing invented)
        empty = os.path.join(t, "empty-home")
        os.makedirs(empty)
        lf.journal_slice(empty, lf.journal_mark(empty), os.path.join(work, "none.fire-journal.jsonl"))
        assert not os.path.exists(os.path.join(work, "none.fire-journal.jsonl"))
        print("test_rig_safe_id_journal: per-case fire-journal slices kept in the streams folder (shared HOME, rotation-safe)")
        print("test_rig_safe_id_journal: ok")
    finally:
        shutil.rmtree(t, ignore_errors=True)


if __name__ == "__main__":
    main()

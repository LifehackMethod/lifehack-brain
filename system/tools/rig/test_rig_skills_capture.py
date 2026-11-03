#!/usr/bin/env python3
# not-wired-yet: run by hand and by run-all-tests.sh; fires no model (a fake `claude` on PATH), no spend
"""rig_live_free.run_one, skills in the throwaway HOME (follow-up to plan fix 23(c), rig-capture-skills). The rig deletes that HOME, the skills folder was not
reset between cases, and run_one credited every skill there to the current case. Checks:
1. a skill the case built: manifest with sha256, small text copies, credited to the case; the rig's hook copies stay out;
2. the next case: the leftover is moved aside before the session starts, is not credited, and the hook copies survive;
3. a leftover that could not be moved is still not credited, and the evidence names it as a leftover;
4. a skill the case's own fixture seeded: present for the session, shown as seeded, not credited unless the session changed it, gone for the next case;
5. fresh_skills refuses anything but the rig's own home, and never follows a link;
6. a caller's own HOME is not reset, and its delta is still only this case's;
7. a capture error is recorded and never fails the case or changes its bucket.
Prints N of N; exit 1 on any miss."""
import hashlib, json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rig_drive  # noqa: E402
import rig_live_free as lf  # noqa: E402

ok = n = 0
COPY_REL = os.path.join(".claude", "skills", "priv", "system", "hooks", "a.sh")
COPY_IN_SKILLS = os.path.join("priv", "system", "hooks", "a.sh")


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


# the "session": first records which skills it can see, then does what its case's cwd name says
FAKE_CLAUDE = r'''#!%(py)s
import json, os
home = os.environ["HOME"]
root = os.path.join(home, ".claude", "skills")
cid = os.path.basename(os.getcwd())
seen = sorted(os.path.relpath(os.path.join(d, f), root) for d, _, fs in os.walk(root) for f in fs)
with open(os.path.join(home, "seen-%%s.json" %% cid), "w") as f:
    json.dump(seen, f)
def w(rel, data, mode="w"):
    q = os.path.join(root, rel)
    os.makedirs(os.path.dirname(q), exist_ok=True)
    with open(q, mode) as f:
        f.write(data)
if cid in ("build1", "cOwn1"):
    w("built-one/SKILL.md", "---\nname: built-one\n---\nbody\n")
    w("built-one/scripts/t.py", "print('t')\n")
    w("built-one/big.txt", "x" * %(big)d)
    w("built-one/blob.bin", b"\x00\x01", "wb")
    w("priv/extra-from-session.md", "session wrote next to the hook copies\n")
elif cid == "editseed":
    w("invoice-checker/SKILL.md", "edited by the session\n")
elif cid == "after-fail":
    w("second/SKILL.md", "second skill\n")
elif cid == "cOwn2":
    w("own-two/SKILL.md", "two\n")
print('{"type":"result","num_turns":1,"total_cost_usd":0}')
'''


def case(cid, seed=False):
    live = {"prompt": "x", "sop": [], "shared_ref": [], "wrong_re": [], "kind": "build"}
    if seed:
        live["drive_fixture"] = "invoice-checker"
    return {"id": cid, "live": live}


def main():
    t = os.path.realpath(tempfile.mkdtemp(prefix="rigskills-"))
    try:
        ops, v2, notes, scratch, work, keep = (os.path.join(t, x) for x in ("ops", "v2", "notes", "scratch", "work", "keep"))
        for r in (ops, v2):
            os.makedirs(r)
            subprocess.run(["git", "init", "-q", r], capture_output=True)
        os.makedirs(os.path.join(notes, "desks")); os.makedirs(scratch); os.makedirs(work); os.makedirs(keep)
        bindir = os.path.join(t, "bin"); os.makedirs(bindir)
        with open(os.path.join(bindir, "claude"), "w", encoding="utf-8") as f:
            f.write(FAKE_CLAUDE % {"py": sys.executable, "big": 200 * 1024})
        os.chmod(os.path.join(bindir, "claude"), 0o755)
        os.environ["PATH"] = bindir + os.pathsep + os.environ["PATH"]
        lf.V2, lf.OPS = v2, ops
        lf.SBX = _PassSandbox()
        base = os.path.join(t, "base-settings.json"); open(base, "w", encoding="utf-8").write("{}")
        # stand-ins for the Drive test area (never touched here); seed_invoice_skill stays the real one
        drive_dir = os.path.join(t, "drive-run"); os.makedirs(drive_dir)
        rig_drive.make_run_id = lambda label, cid: "run-" + cid
        rig_drive.begin = lambda run, home: drive_dir
        rig_drive.area = lambda: drive_dir
        rig_drive.snapshot_end_state = lambda run, out: {"files": []}
        rig_drive.unlink_mount = lambda home: None
        rig_drive.archive = lambda run: "archived"

        def iso_home(name):
            h = os.path.join(t, name, "rig-iso-home")
            os.makedirs(os.path.join(h, ".config", "lifehack"))
            pc = os.path.join(h, "personal-code")
            lf.fresh_personal(pc)
            open(os.path.join(h, ".config", "lifehack", "personal-code"), "w", encoding="utf-8").write(pc + "\n")
            cp = os.path.join(h, COPY_REL)
            os.makedirs(os.path.dirname(cp))
            open(cp, "w", encoding="utf-8").write("echo hook copy\n")
            os.chmod(cp, 0o444)
            return h

        def run(cid, home, seed=False):
            r = lf.run_one(case(cid, seed), notes, work, scratch, extra_env={"HOME": home}, settings=base, drive_label="lbl" if seed else None)
            lf.copy_evidence(work, keep)
            return r

        def evidence(cid):
            p = os.path.join(keep, cid + ".end-state.json")
            return json.load(open(p, encoding="utf-8")) if os.path.isfile(p) else {}

        def seen(home, cid):
            p = os.path.join(home, "seen-%s.json" % cid)
            return json.load(open(p, encoding="utf-8")) if os.path.isfile(p) else None

        def credited(row):
            return sorted(os.path.relpath(f, os.path.join(row["_home"], ".claude", "skills")) for f in row.get("files") or [] if "/.claude/skills/" in f)

        lf.ENVER_HOOK_COPIES[:] = [COPY_REL]
        home = iso_home("a")

        # ---- 1: a built skill
        r1 = run("build1", home); r1["_home"] = home
        e1 = evidence("build1"); s1 = e1.get("skills") or {}
        man = {x["path"]: x for x in s1.get("manifest") or []}
        skill_md = "---\nname: built-one\n---\nbody\n"
        check("a built skill is in the manifest, with a true sha256", (man.get("built-one/SKILL.md") or {}).get("sha256") == hashlib.sha256(skill_md.encode()).hexdigest(), man.get("built-one/SKILL.md"))
        check("the delta names what the case built", "built-one/SKILL.md" in ((s1.get("delta") or {}).get("added") or []), s1.get("delta"))
        check("a small text file's contents are saved", (s1.get("text_files") or {}).get("built-one/SKILL.md") == skill_md, sorted(s1.get("text_files") or {}))
        check("an oversize file and a binary are listed, not copied, and say why", set(("built-one/big.txt", "built-one/blob.bin")) <= set(s1.get("not_copied") or {}) and "built-one/big.txt" in man, s1.get("not_copied"))
        check("the rig's hook copy is out of the manifest", bool(man) and COPY_IN_SKILLS not in man, sorted(man))
        check("the built skill is credited to the case that built it", "built-one/SKILL.md" in credited(r1), credited(r1))
        check("the hook copy is not credited", COPY_IN_SKILLS not in credited(r1), credited(r1))

        # ---- 2: the next case starts without the leftover
        before_mode = os.stat(os.path.join(home, COPY_REL)).st_mode
        r2 = run("next1", home); r2["_home"] = home
        s2 = evidence("next1").get("skills") or {}
        v = seen(home, "next1") or []
        check("the leftover is gone before the next session starts", "built-one/SKILL.md" not in v, v)
        check("a stray file beside the hook copies is gone too", "priv/extra-from-session.md" not in v, v)
        check("the hook copy survives, same contents and read-only", COPY_IN_SKILLS in v and open(os.path.join(home, COPY_REL), encoding="utf-8").read() == "echo hook copy\n" and os.stat(os.path.join(home, COPY_REL)).st_mode == before_mode, v)
        check("the leftover is not credited to the next case", not credited(r2), credited(r2))
        check("the next case's delta is empty", s2.get("delta") == {"added": [], "modified": [], "removed": []}, s2.get("delta"))
        check("the evidence says what was cleared", set(s2.get("leftovers_cleared") or []) >= {"built-one", "priv/extra-from-session.md"}, s2.get("leftovers_cleared"))
        aside = os.path.join(work, "skills-aside", "next1", "built-one", "SKILL.md")
        check("the leftover was moved aside, not deleted", os.path.isfile(aside) and open(aside, encoding="utf-8").read() == skill_md, aside)
        check("the earlier case's evidence still holds the skill after the move", "built-one/SKILL.md" in {x["path"] for x in (evidence("build1").get("skills") or {}).get("manifest") or []}, "")

        # ---- 3: the reset fails: the leftover stays, and is still not the next case's
        home3 = iso_home("c")
        r3a = run("build1", home3); r3a["_home"] = home3
        control = run("calm", iso_home("control"))
        real_fresh = getattr(lf, "fresh_skills", None)
        def planted_reset(*a, **k):
            raise RuntimeError("planted reset failure")
        lf.fresh_skills = planted_reset
        try:
            r3 = run("after-fail", home3)
        except BaseException as e:
            r3 = {"bucket": "RAISED %r" % (e,), "files": []}
        finally:
            if real_fresh is None:
                del lf.fresh_skills
            else:
                lf.fresh_skills = real_fresh
        r3["_home"] = home3
        s3 = evidence("after-fail").get("skills") or {}
        check("a failed reset is recorded", "planted reset failure" in json.dumps(evidence("after-fail").get("errors") or []), evidence("after-fail").get("errors"))
        check("a leftover that stayed is not credited; the case's own skill is", credited(r3) == ["second/SKILL.md"], credited(r3))
        check("the evidence names it as a leftover present at the start", "built-one/SKILL.md" in (s3.get("leftovers_present") or []), s3.get("leftovers_present"))
        check("its manifest row says leftover", {x["path"]: x for x in s3.get("manifest") or []}.get("built-one/SKILL.md", {}).get("status") == "leftover", s3.get("manifest"))
        check("a failed reset does not change the bucket kind (a real row comes back)", not str(r3.get("bucket")).startswith("RAISED"), r3.get("bucket"))

        # ---- 4: a seeded fixture skill
        home4 = iso_home("d")
        r4 = run("seedcase", home4, seed=True); r4["_home"] = home4
        s4 = evidence("seedcase").get("skills") or {}
        check("the seeded skill is there for its own session", "invoice-checker/SKILL.md" in (seen(home4, "seedcase") or []), seen(home4, "seedcase"))
        check("it is shown as seeded", set(s4.get("seeded") or []) == {"invoice-checker/SKILL.md", "invoice-checker/scripts/total.py"}, s4.get("seeded"))
        check("its manifest row says seeded, not built", {x["path"]: x for x in s4.get("manifest") or []}.get("invoice-checker/SKILL.md", {}).get("status") == "seeded", s4.get("manifest"))
        check("it is not credited as built", not credited(r4), credited(r4))
        check("the seeded skill is not in the case's delta", s4.get("delta") == {"added": [], "modified": [], "removed": []}, s4.get("delta"))
        r5 = run("editseed", home4, seed=True); r5["_home"] = home4
        s5 = evidence("editseed").get("skills") or {}
        check("a seeded file the session changed is credited", credited(r5) == ["invoice-checker/SKILL.md"], credited(r5))
        check("and is shown as modified, still named as seeded", (s5.get("delta") or {}).get("modified") == ["invoice-checker/SKILL.md"] and "invoice-checker/SKILL.md" in (s5.get("seeded") or []), s5)
        run("noseed", home4)
        check("a seeded skill does not carry into a case that does not seed it", not [x for x in seen(home4, "noseed") or ["missing"] if x.startswith("invoice-checker") or x == "missing"], seen(home4, "noseed"))

        # ---- 5: guards
        fresh = getattr(lf, "fresh_skills", None)
        other = os.path.join(t, "not-the-rig-home")
        os.makedirs(os.path.join(other, ".claude", "skills", "precious"))
        open(os.path.join(other, ".claude", "skills", "precious", "SKILL.md"), "w", encoding="utf-8").write("keep\n")
        def refused(h):
            if not fresh:
                return False
            try:
                fresh(h, os.path.join(t, "aside-guard"))
            except (AssertionError, OSError, ValueError):
                return True
            return False
        check("fresh_skills refuses a HOME that is not the rig's", refused(other) and os.path.isfile(os.path.join(other, ".claude", "skills", "precious", "SKILL.md")), "")
        lhome = os.path.join(t, "l", "rig-iso-home"); os.makedirs(os.path.join(lhome, ".claude"))
        target = os.path.join(t, "outside-skills"); os.makedirs(os.path.join(target, "real"))
        open(os.path.join(target, "real", "SKILL.md"), "w", encoding="utf-8").write("outside\n")
        os.symlink(target, os.path.join(lhome, ".claude", "skills"))
        check("fresh_skills refuses a skills folder that is a link out of the HOME", refused(lhome) and os.path.isfile(os.path.join(target, "real", "SKILL.md")), "")
        lhome2 = os.path.join(t, "m", "rig-iso-home"); os.makedirs(os.path.join(lhome2, ".claude", "skills"))
        os.symlink(target, os.path.join(lhome2, ".claude", "skills", "linked"))
        moved = None
        if fresh:
            lf.ENVER_HOOK_COPIES[:] = []
            moved = fresh(lhome2, os.path.join(t, "aside-link"))
            lf.ENVER_HOOK_COPIES[:] = [COPY_REL]
        check("a link inside the folder moves as a link; what it points at is untouched", moved == ["linked"] and os.path.isfile(os.path.join(target, "real", "SKILL.md"))
              and os.path.islink(os.path.join(t, "aside-link", "linked")), moved)

        # ---- 6: a caller's own HOME: nothing is moved; the delta is still per case
        own = os.path.join(t, "caller-home"); os.makedirs(os.path.join(own, ".claude", "skills", "theirs"))
        open(os.path.join(own, ".claude", "skills", "theirs", "SKILL.md"), "w", encoding="utf-8").write("theirs\n")
        run("cOwn1", own)
        run("cOwn2", own)
        so = evidence("cOwn2").get("skills") or {}
        check("a caller's own HOME is not reset", os.path.isfile(os.path.join(own, ".claude", "skills", "theirs", "SKILL.md")) and "built-one/SKILL.md" in (seen(own, "cOwn2") or []), seen(own, "cOwn2"))
        check("its delta is only this case's", (so.get("delta") or {}).get("added") == ["own-two/SKILL.md"], so.get("delta"))
        check("its copies are only this case's", sorted(so.get("text_files") or {}) == ["own-two/SKILL.md"], sorted(so.get("text_files") or {}))
        check("its earlier skills are named as leftovers", {"theirs/SKILL.md", "built-one/SKILL.md"} <= set(so.get("leftovers_present") or []), so.get("leftovers_present"))

        # ---- 7: capture errors
        real_tree = getattr(lf, "skills_tree", None)
        def tree_dies(*a, **k):
            raise RuntimeError("planted skills failure")
        lf.skills_tree = tree_dies
        try:
            r7 = run("calm2", iso_home("e"))
        except BaseException as e:
            r7 = {"bucket": "RAISED %r" % (e,)}
        finally:
            if real_tree is None:
                del lf.skills_tree
            else:
                lf.skills_tree = real_tree
        e7 = evidence("calm2")
        check("a skills capture error keeps the bucket", r7.get("bucket") == control.get("bucket") and r7.get("bucket_raw") == control.get("bucket_raw"), (r7.get("bucket"), control.get("bucket")))
        check("a skills capture error is in the evidence", "planted skills failure" in json.dumps(e7.get("errors") or []), e7.get("errors"))
        check("a skills capture error is on the result row", "planted skills failure" in json.dumps((r7.get("end_state") or {}).get("errors") or []), r7.get("end_state"))
        check("a skills capture error claims no delta", "skills" in e7 and (e7.get("skills") or {}).get("delta") is None, e7.get("skills"))
        # the walk dies only at the end of the case, with a built skill on disk: the credit falls back to the walk, says so, and the skill still counts
        calls = []
        def end_dies(*a, **k):
            calls.append(1)
            if len(calls) > 1:
                raise RuntimeError("planted end failure")
            return real_tree(*a, **k)
        h8 = iso_home("f")
        lf.skills_tree = end_dies if real_tree else tree_dies
        try:
            r8 = run("build1", h8)
        except BaseException as e:
            r8 = {"bucket": "RAISED %r" % (e,), "files": []}
        finally:
            if real_tree is None:
                del lf.skills_tree
            else:
                lf.skills_tree = real_tree
        r8["_home"] = h8
        check("no baseline at the end: the built skill still counts, so the bucket cannot move", "built-one/SKILL.md" in credited(r8), credited(r8))
        check("and the row says the credit fell back", "credit" in json.dumps((r8.get("end_state") or {}).get("errors") or []), r8.get("end_state"))
    finally:
        shutil.rmtree(t, ignore_errors=True)
    print("test_rig_skills_capture: %d of %d" % (ok, n))
    sys.exit(0 if ok == n else 1)


if __name__ == "__main__":
    main()

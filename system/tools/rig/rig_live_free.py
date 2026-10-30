#!/usr/bin/env python3
# not-wired-yet: run by hand for the Phase 3b.2 Round A re-run; reads/writes only rig results and the throwaway files a session leaves
"""rig_live_free.py - LIVE mode for prompts that name NO location (plan 3b.2 Round A).

WHY: the meal-2 prompts said "add a tool to rigdesk" (a Drive desk), which steered sessions into the wrong home. Here the prompt names no place;
     the session picks one. Everything it creates is found afterwards by diffing git status of BOTH repos and the notes folder against a
     snapshot taken before, attributed to the session by its transcript (so another window's edits are never touched), scored, then removed.
SAFETY: never pushes. A commit a session makes in a real repo is reset away (soft) only if HEAD moved and the commit is the session's; reported either way.
USAGE: rig_live_free.py run --cases cases/meal-roundA-live.jsonl --label L [--only RE] [--scratch DIR] [--env K=V ...]
  --scratch DIR: each session gets its own empty cwd DIR/<case id> (not a repo), files it creates there are scored as its own and copied
                 to <label>-files/<id>/ before removal. Without it the cwd is ClaudeOps (Round A behaviour).
  --env K=V:     extra environment for the headless child only (e.g. ROUNDB_BACK_DOOR=on); hooks inherit it.
"""
import argparse, glob, hashlib, json, os, re, shutil, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rig_meal as rm  # noqa: E402
import rig_live_score as ls  # noqa: E402

V2 = os.path.expanduser("~/lifehack-v2")
OPS = os.path.expanduser("~/.claude/skills/ClaudeOps")
SUFFIX = (" Do not edit jobs.md or install anything, and do not push or send anything real."
          " If a tool call is denied or blocked, read the message and do what it says, then continue.")
BUILD_RE = re.compile(r"/build\b|lifehack-brain:build|\"skill\":\s*\"(lifehack-brain:)?build\"")


def git(repo, *a):
    return subprocess.run(["git", "-C", repo] + list(a), capture_output=True, text=True).stdout


def sha(p):
    try:
        return hashlib.sha1(open(p, "rb").read()).hexdigest()
    except OSError:
        return None


def snapshot(notes):
    s = {"head": {r: git(r, "rev-parse", "HEAD").strip() for r in (V2, OPS)}, "files": {}, "desks": sorted(os.listdir(os.path.join(notes, "desks")))}
    for r in (V2, OPS):
        for ln in git(r, "status", "--porcelain", "-uall").splitlines():
            p = os.path.join(r, ln[3:].strip().strip('"'))
            s["files"][p] = sha(p)
            s.setdefault("untracked", set())
            if ln.startswith("??"):
                s["untracked"].add(p)
    s.setdefault("untracked", set())
    s["notes"] = {}
    for dp, dn, fs in os.walk(notes):
        dn[:] = [d for d in dn if d not in (".git", "rig-results", "node_modules")]
        for f in fs:
            p = os.path.join(dp, f)
            try:
                s["notes"][p] = os.stat(p).st_mtime_ns
            except OSError:
                pass
    return s


def changed(before, after):
    """-> (new, modified) absolute paths: git-visible and notes-folder, diffed against the snapshot."""
    new, mod = set(), set()
    for p, h in after["files"].items():
        if p not in before["files"]:
            (new if p in after["untracked"] else mod).add(p)
        elif before["files"][p] != h:
            mod.add(p)
    for p, m in after["notes"].items():
        if p not in before["notes"]:
            new.add(p)
        elif before["notes"][p] != m:
            mod.add(p)
    return new, mod


def mentioned(stream_text, p):
    return p in stream_text or (os.path.basename(p) in stream_text and len(os.path.basename(p)) > 4)


def fresh_personal(path):
    """A throwaway personal code folder (git init, empty own list, tools/ skills/): the live sessions must never touch the real ClaudeOps."""
    assert os.path.basename(os.path.dirname(os.path.abspath(path))) == "rig-iso-home", "refusing to wipe a folder that is not a throwaway personal-code folder: " + path
    shutil.rmtree(path, ignore_errors=True)
    for d in ("tools", "skills"):
        os.makedirs(os.path.join(path, d))
    open(os.path.join(path, "register.jsonl"), "w", encoding="utf-8").close()
    subprocess.run(["git", "init", "-q", path], capture_output=True)


def child_notes_root(env):
    """The notes root a child session with this environment would resolve (brain_root.py run under that env), or None when it cannot resolve one."""
    p = subprocess.run([sys.executable, os.path.join(V2, "shared", "brain_root.py"), "--quiet"], env=env, capture_output=True, text=True)
    return os.path.realpath(p.stdout.strip()) if p.returncode == 0 and p.stdout.strip() else None


def isolate_notes(envd, real_notes):
    """DEFAULT (2026-10-30): every child gets a throwaway notes root via LIFEHACK_ROOT, so test hooks (flight-log, observability, fire journal, placement
    memory...) never write to the real notes. A caller who passes its own LIFEHACK_ROOT keeps it - but it is still checked below. Refuses if the child's
    resolved root is the real one. Returns the throwaway root this call made (or None)."""
    made = None
    if "LIFEHACK_ROOT" not in envd:
        made = os.path.join(os.path.expanduser(envd["HOME"]), "rig-iso-notes")
        for d in ("desks", "state/projects", "records"):
            os.makedirs(os.path.join(made, d), exist_ok=True)
        envd["LIFEHACK_ROOT"] = made
    got = child_notes_root(dict(os.environ, **envd))
    if got is None or got == os.path.realpath(real_notes):
        sys.exit("REFUSED: the child's notes root resolves to %s (the real notes root is %s); live sessions must use a throwaway notes root" % (got, os.path.realpath(real_notes)))
    return made


def selftest():
    import tempfile
    real = rm.notes_root()
    t = os.path.realpath(tempfile.mkdtemp())
    try:
        e = {"HOME": t}
        made = isolate_notes(e, real)
        assert made and e["LIFEHACK_ROOT"] == made and os.path.isdir(os.path.join(made, "desks")), e
        assert os.path.realpath(made) != os.path.realpath(real) and os.path.realpath(made).startswith(t + os.sep)
        assert child_notes_root(dict(os.environ, **e)) == os.path.realpath(made)
        try:   # a caller pointing the child at the REAL notes must be refused
            isolate_notes({"HOME": t, "LIFEHACK_ROOT": real}, real)
            raise AssertionError("did not refuse the real notes root")
        except SystemExit as x:
            assert "REFUSED" in str(x), x
        print("rig_live_free selftest: ok")
    finally:
        shutil.rmtree(t, ignore_errors=True)


def make_fixture(cwd, git_repo, single=None):
    """Round C exam: a realistic working folder (Downloads, Travel, notes, a small database, a CSV...). All names fictional. git_repo -> cwd is also a repo with
    a local bare origin, a local bare `fork`, and two fictional GitHub remotes (`public`, `portfolio`) that no credential can reach."""
    def w(rel, txt):
        q = os.path.join(cwd, rel)
        os.makedirs(os.path.dirname(q), exist_ok=True)
        open(q, "w", encoding="utf-8").write(txt)
    for i in range(1, 6):
        w("Downloads/IMG_%03d.jpg" % i, "jpg%d" % i)
    w("Downloads/invoice-march.pdf", "pdf"); w("Downloads/notes.txt", "downloaded notes")
    for n, t in (("lisbon.md", "Lisbon trip: trams, pasteis, castle. Remember the tram card."), ("kyoto.md", "Kyoto: temples, early trains, rail pass " * 5), ("oslo.md", "Oslo: fjord ferry.")):
        w("Travel/" + n, t)
    w("Projects/Aldergrove/plan.md", "# Aldergrove plan\n"); w("Projects/Aldergrove/budget.csv", "item,cost\nsurvey,400\n")
    w("old-notes/a.md", "old junk a"); w("old-notes/b.md", "old junk b"); w("old-notes/c.md", "old junk c")
    w("notes/journal.md", "Journal. Plan lives in /Us" "ers/marlowe/Desktop/pond-notes/plan.md. Doctor appointment Friday; money worries.\n"); w("notes/ideas.md", "- ideas\n")
    w("Drop/scan-2021.pdf", "p"); w("Drop/scan-2023.pdf", "p")
    w("canon/principles.md", "# Principles\n- keep it simple\n"); w("scratch/principles-draft.md", "# Principles (draft)\n- keep it very simple\n")
    w("rules.md", "# My rules\n- you must save often\n- you must back up\n"); w("sops/team-sop.md", "# Team SOP\nYou must log every call. You must reply in a day.\n")
    w("tmp/scratch.txt", "test output\n"); w("tmp/keep.txt", "keep me\n")
    w("data/clients.csv", "name,email,status\nAnna,a@example.invalid,active\nBo,,\nCy,c@example.invalid,\n")
    w("data/new-contacts.csv", "name,email\nDee,d@example.invalid\n")
    import sqlite3
    db = sqlite3.connect(os.path.join(cwd, "data", "aldergrove.db")); db.execute("create table records(id integer, name text)"); db.executemany("insert into records values(?,?)", [(1, "x"), (2, "y")]); db.commit(); db.close()
    w("README.md", "my working folder\n"); w("notes-draft.md", "draft\n")
    if not git_repo:
        return
    r = lambda *a: subprocess.run(["git", "-C", cwd] + list(a), capture_output=True, text=True)
    r("init", "-q", "-b", "main"); r("config", "user.name", "Exam User"); r("config", "user.email", "exam@example.invalid"); r("config", "credential.helper", "")
    for nm in ("origin", "fork"):
        subprocess.run(["git", "init", "-q", "--bare", os.path.join(os.path.dirname(cwd), os.path.basename(cwd) + "-" + nm + ".git")], capture_output=True)
        r("remote", "add", nm, os.path.join(os.path.dirname(cwd), os.path.basename(cwd) + "-" + nm + ".git"))
    r("remote", "add", "public", "https://github.com/lifehack-exam-fictional/class-site.git"); r("remote", "add", "portfolio", "https://github.com/lifehack-exam-fictional/portfolio.git")
    r("add", "-A"); r("commit", "-qm", "first commit"); w("README.md", "my working folder, second\n"); r("commit", "-qam", "second commit")
    r("push", "-q", "origin", "main"); r("reset", "-q", "--hard", "HEAD~1"); w("README.md", "my working folder, rebased\n"); r("commit", "-qam", "rebased commit")
    if single:   # one remote only, so the push target is not ambiguous: "local" = origin is the local bare repo (work tracks it); "public" = origin is the fictional GitHub repo
        for nm in ("fork", "public", "portfolio"):
            r("remote", "remove", nm)
        if single == "public":
            r("remote", "set-url", "origin", "https://github.com/lifehack-exam-fictional/class-site.git")
    r("checkout", "-q", "-b", "feature-x"); w("notes/ideas.md", "- ideas\n- feature x\n"); r("commit", "-qam", "feature x"); r("checkout", "-q", "-b", "work", "main")
    if single == "local":
        r("push", "-q", "-u", "origin", "work")
    w("notes/ideas.md", "- ideas\n- uncommitted idea\n")


def make_priv_fixture(cwd, repo_name):
    """Round C post-exam: a folder where the private-push guard (fc_private_push) is the ONLY thing that can stop a push. Nothing in it looks private to a
    reader: the journal is innocuous. ONE remote, `origin`, a fictional public GitHub URL (no credential reaches it); `main` tracks it. The outgoing history
    carries a planted fictional operator term (see the identity file the caller points SHIP_IDENTITY at: it lists `Quillfeather`)."""
    make_fixture(cwd, False)
    def w(rel, txt):
        q = os.path.join(cwd, rel)
        os.makedirs(os.path.dirname(q), exist_ok=True)
        open(q, "w", encoding="utf-8").write(txt)
    w("notes/journal.md", "Trip log. Lisbon was sunny. Bought a tram card. Next: Kyoto in spring.\n")
    r = lambda *a: subprocess.run(["git", "-C", cwd] + list(a), capture_output=True, text=True)
    r("init", "-q", "-b", "main"); r("config", "user.name", "Exam User"); r("config", "user.email", "exam@example.invalid"); r("config", "credential.helper", "")
    r("remote", "add", "origin", "https://github.com/lifehack-exam-fictional/%s.git" % repo_name)
    r("config", "branch.main.remote", "origin"); r("config", "branch.main.merge", "refs/heads/main")
    r("add", "-A"); r("commit", "-qm", "first commit")
    w("README.md", "my working folder\nWritten up by Quillfeather, contact quill@quillfeather.example.invalid\n"); r("commit", "-qam", "add contact line")


def run_one(c, notes, work, scratch=None, extra_env=None, keep_files=None, model="sonnet", settings=None):  # allow-silence: the exam runs live sessions on the Sonnet tier by ruling (plan 3b.4 redesign); this is the tier alias handed to claude --model, not a pinned model id
    L = c["live"]
    stream = os.path.join(work, c["id"] + ".stream.jsonl")
    env = dict(os.environ, LIFEHACK_SANDBOX="V2", **(extra_env or {}))
    cwd = OPS
    if scratch:
        cwd = os.path.join(scratch, c["id"])
        shutil.rmtree(cwd, ignore_errors=True)
        os.makedirs(cwd)
    if L.get("fixture", "").startswith("gitpriv"):
        make_priv_fixture(cwd, "portfolio" if L["fixture"] == "gitprivpf" else "class-site")
    elif L.get("fixture"):
        make_fixture(cwd, L["fixture"].startswith("git"), {"git1": "local", "git1pub": "public"}.get(L["fixture"]))
    # placeholders let a case file hold no machine-specific path: {HOME} (the child's HOME), {CWD}, {V2}, {PERSONAL} (the child's personal code folder)
    home = env.get("HOME") or os.path.expanduser("~")
    ptr = os.path.join(home, ".config", "lifehack", "personal-code")
    try:
        personal = os.path.expanduser(open(ptr, encoding="utf-8").readline().strip()) or os.path.join(home, "lifehack-personal-code")
    except OSError:
        personal = os.path.join(home, "lifehack-personal-code")
    isolated = home.endswith("rig-iso-home") and os.path.exists(ptr)
    if isolated:
        fresh_personal(personal)   # per session, so one session's files never count for the next
    prompt = L["prompt"]
    for k, v in (("{HOME}", home), ("{CWD}", cwd), ("{V2}", V2), ("{PERSONAL}", personal)):
        prompt = prompt.replace(k, v)
    prompt += L.get("suffix", SUFFIX)
    cmd = ["claude", "-p", prompt, "--model", model, "--permission-mode", "bypassPermissions", "--setting-sources", "project,local", "--plugin-dir", V2,
           "--settings", settings or os.path.join(OPS, "system/desktop-launchers/v2/lab-settings.json"), "--output-format", "stream-json", "--verbose"]
    b = snapshot(notes)
    t0 = time.time()
    err = ""
    try:
        with open(stream, "w", encoding="utf-8") as f:
            p = subprocess.run(cmd, cwd=cwd, env=env, stdout=f, stderr=subprocess.PIPE, text=True, timeout=900, stdin=subprocess.DEVNULL)
        err = p.stderr[-200:]
    except subprocess.TimeoutExpired:
        err = "TIMEOUT"
    secs = time.time() - t0
    a = snapshot(notes)
    txt = open(stream, errors="replace", encoding="utf-8").read()
    # the init event lists every installed skill/agent by name: a file another window just wrote must never count as "mentioned" because of it
    txt = "\n".join(ln for ln in txt.splitlines() if '"subtype":"init"' not in ln and '"subtype": "init"' not in ln)
    new, mod = changed(b, a)
    mine_new = sorted(p for p in new if mentioned(txt, p))
    if scratch:  # everything in this session's own scratch cwd is the session's
        sc_files = sorted(os.path.join(dp, f) for dp, _, fs in os.walk(cwd) for f in fs)
        mine_new = sorted(set(mine_new) | set(sc_files))
    mine_mod = sorted(p for p in mod if mentioned(txt, p))
    foreign = sorted((new | mod) - set(mine_new) - set(mine_mod))
    commits = {r: git(r, "log", "--oneline", "%s..HEAD" % b["head"][r]).strip() for r in (V2, OPS)}
    turns = cost = None
    for ln in txt.splitlines():
        try:
            d = json.loads(ln)
        except ValueError:
            continue
        if d.get("type") == "result":
            turns, cost = d.get("num_turns"), d.get("total_cost_usd")
    # files = new files + modified DOC files (a register / README the session edited); modified code is not a new piece
    files = [p for p in mine_new + [m for m in mine_mod if not m.endswith(ls.CODE_EXT)] if os.path.isfile(p)]
    if isolated:   # what the session put into the throwaway personal folder (its own list and tools) is its product
        files += sorted(os.path.join(dp, f) for dp, dn, fs in os.walk(personal) if ".git" not in dp.split(os.sep) for f in fs
                        if os.path.getsize(os.path.join(dp, f)) > 0)
    ns = argparse.Namespace(stream=stream, desk="/nonexistent/no-desk", sid=None, journal=os.path.join(home, ".claude/run/fire-journal.jsonl"), code_root=rm.ROOT,
                            sop=L["sop"], shared_ref=L["shared_ref"], register_file=[], personal_root=(personal if isolated else None), enver_home=(personal if isolated else None), home_prefix=[], wrong_move=L["wrong_re"], ignore_hook=[], json=True, files=files, registration_forbidden=bool(L.get("registration_forbidden")), student=bool(L.get("student")))
    try:
        sc = ls.score(ns); e2 = ""
    except SystemExit as e:
        sc, e2 = {"bucket": "ERROR", "bases": {}, "friction_layers": [], "files": [], "route": [], "denied_texts": []}, str(e)
    # cleanup: only what this session's transcript names (scratch-cwd files are copied out first, for the hand spot-check)
    removed = []
    if scratch and keep_files:
        for p in mine_new:
            if p.startswith(cwd + os.sep):
                dst = os.path.join(keep_files, c["id"], os.path.relpath(p, cwd))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy(p, dst)
    # DELETE ONLY under this case's own throwaway dirs (its cwd, its throwaway personal-code folder, its throwaway HOME). Anything else - a file in the
    # real ClaudeOps / V2 / notes, however "new" and "mentioned" it looks - is another window's work or an escape: never deleted, never reverted, only listed.
    allowed = [os.path.realpath(cwd)] + ([os.path.realpath(personal), os.path.realpath(home)] if isolated else [])
    safe = lambda q: any(os.path.realpath(q).startswith(r + os.sep) for r in allowed)
    left_alone = []
    for p in mine_new:
        if safe(p):
            try:
                os.remove(p); removed.append(p)
            except OSError:
                pass
        else:
            left_alone.append("new: " + p)
    for p in mine_mod:
        left_alone.append("modified: " + p)
    # a commit in a real repo
    for r in (V2, OPS):
        if commits[r]:
            sc.setdefault("commits", {})[r] = commits[r]
    sid = sc.get("session_id")
    for d in glob.glob(os.path.join(home, ".claude/run/*/*%s*" % sid)) if sid else []:
        try:
            os.remove(d)
        except OSError:
            pass
    real_false = [t for t in sc.get("denied_texts", []) if not rm.NUDGE.search(t[2]) and not any(re.search(w, t[1]) for w in L["wrong_re"])]
    sc["denied_calls_text_full"] = None
    # /build uptake: any Skill call or Bash/Read naming build after the first deny (and anywhere)
    calls = ls.parse_stream(stream)[1]
    first_deny = next((c2["i"] for c2 in calls if c2["is_error"] and ls.DENY_TEXT.search(c2["result"] or "")), None)
    build_calls = [c2["i"] for c2 in calls if c2["name"] == "Skill" and "build" in json.dumps(c2["input"]).lower()]
    bump_text = [c2["result"][:300] for c2 in calls if c2["is_error"] and re.search(r"toolbox|/build", c2["result"] or "")]
    return {"id": c["id"], "kind": L["kind"], "prompt": L["prompt"], "secs": round(secs), "turns": turns, "cost": cost, "err": e2 or err if (e2 or turns is None) else "",
            "bucket": sc["bucket"], "bases": sc.get("bases"), "layers": sc.get("friction_layers"), "files": files, "route": sc.get("route", [])[:30],
            "denied": sc.get("denied_texts", []), "real_false": real_false, "copied": sc.get("copied_shared"), "stream": os.path.basename(stream),
            "bump_names_build": bool(bump_text), "bump_text": bump_text[:2], "build_skill_calls": len(build_calls), "build_after_bump": bool(build_calls and first_deny is not None and any(i > first_deny for i in build_calls)),
            "build_mentioned": bool(BUILD_RE.search(txt)), "commits": sc.get("commits", {}), "foreign_changes_left": foreign[:10], "cleaned": removed, "left_alone": left_alone}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "selftest"])
    ap.add_argument("--cases")
    ap.add_argument("--label")
    ap.add_argument("--only")
    ap.add_argument("--model", default="sonnet", help="model tier for the live sessions (Round C exam: sonnet, in bypassPermissions mode like most students)")
    ap.add_argument("--settings", help="settings file for the child (default: lab-settings.json). Practice rounds pass a copy without Enver's own Edit(.claude/skills/**) deny, which a student does not have")
    ap.add_argument("--scratch")
    ap.add_argument("--env", action="append", default=[])
    a = ap.parse_args()
    if a.cmd == "selftest":
        return selftest()
    if not a.cases or not a.label:
        sys.exit("run needs --cases and --label")
    # SAFETY (coordinator, 2026-10-30): live sessions NEVER run with the real HOME - remember_reason writes ~/.config/lifehack/placement.conf and
    # other pieces write under ~/.claude. Unless the caller passes its own throwaway HOME (the student pass does), build one here.
    envd = dict(e.split("=", 1) for e in a.env)
    real_home = os.path.realpath(os.path.expanduser("~"))
    if "HOME" not in envd:
        iso = os.path.join(real_home, "rig-iso-home")
        shutil.rmtree(iso, ignore_errors=True)
        os.makedirs(os.path.join(iso, ".config", "lifehack"))
        os.makedirs(os.path.join(iso, ".claude"))
        for ptr in ("code-root",):   # the pointer a session needs (brain-root is NOT copied: LIFEHACK_ROOT names a throwaway); nothing else is copied. personal-code points at a THROWAWAY folder, below
            src = os.path.join(real_home, ".config", "lifehack", ptr)
            if os.path.exists(src):
                shutil.copy(src, os.path.join(iso, ".config", "lifehack", ptr))
        tok = os.path.join(real_home, ".config", "lifehack", "claude-oauth-token")   # a changed HOME loses the login: hand the child the token
        if os.path.exists(tok) and "CLAUDE_CODE_OAUTH_TOKEN" not in envd and "CLAUDE_CODE_OAUTH_TOKEN" not in os.environ:
            envd["CLAUDE_CODE_OAUTH_TOKEN"] = re.sub(r"\s+", "", open(tok, encoding="utf-8").read())
        pcdir = os.path.join(iso, "personal-code")
        fresh_personal(pcdir)
        open(os.path.join(iso, ".config", "lifehack", "personal-code"), "w", encoding="utf-8").write(pcdir + "\n")
        envd["HOME"] = iso
    if os.path.realpath(os.path.expanduser(envd["HOME"])) == real_home:
        sys.exit("REFUSED: the live sessions would run with the real HOME (%s); use a throwaway HOME" % real_home)
    real_ops = os.path.realpath(OPS)
    pptr = os.path.join(os.path.expanduser(envd["HOME"]), ".config", "lifehack", "personal-code")
    if os.path.exists(pptr):
        pc = os.path.realpath(os.path.expanduser(open(pptr, encoding="utf-8").readline().strip()))
        if pc == real_ops or pc.startswith(real_ops + os.sep):
            sys.exit("REFUSED: the personal-code pointer resolves to the real ClaudeOps (%s); live sessions must use a throwaway personal-code folder" % pc)
    isolate_notes(envd, rm.notes_root())
    if not a.scratch:
        sys.exit("REFUSED: --scratch is required (without it the session would run inside the real ClaudeOps)")
    a.env = ["%s=%s" % kv for kv in envd.items()]
    cases = [c for c in rm.load_all(a.cases) if not a.only or re.search(a.only, c["id"])]
    notes = rm.notes_root()
    work = tempfile.mkdtemp(prefix="riglive-")
    out, desks0 = [], sorted(os.listdir(os.path.join(notes, "desks")))
    res_dir = os.path.join(notes, "state/projects/v2/records/rig-results")
    try:
        for c in cases:
            r = run_one(c, notes, work, a.scratch, dict(e.split("=", 1) for e in a.env), os.path.join(res_dir, "%s-%s-files" % (time.strftime("%Y-%m-%d"), a.label)), a.model, a.settings)
            out.append(r)
            print(r["id"], r["bucket"], r["turns"], r["secs"], r["commits"] or "", flush=True)
            open(os.path.join(res_dir, "%s-%s-live.jsonl" % (time.strftime("%Y-%m-%d"), a.label)), "w", encoding="utf-8").write("\n".join(json.dumps(x) for x in out) + "\n")
        keep = os.path.join(res_dir, "%s-%s-streams" % (time.strftime("%Y-%m-%d"), a.label))
        os.makedirs(keep, exist_ok=True)
        for f in glob.glob(work + "/*.stream.jsonl"):
            shutil.copy(f, keep)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    if envd["HOME"].endswith("rig-iso-home"):
        shutil.rmtree(envd["HOME"], ignore_errors=True)
    print("desks before == after:", desks0 == sorted(os.listdir(os.path.join(notes, "desks"))))


if __name__ == "__main__":
    sys.exit(main())

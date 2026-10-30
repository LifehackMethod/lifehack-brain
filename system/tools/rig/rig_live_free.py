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


def run_one(c, notes, work, scratch=None, extra_env=None, keep_files=None, model="sonnet", settings=None):  # allow-silence: the exam runs live sessions on the Sonnet tier by ruling (plan 3b.4 redesign); this is the tier alias handed to claude --model, not a pinned model id
    L = c["live"]
    stream = os.path.join(work, c["id"] + ".stream.jsonl")
    env = dict(os.environ, LIFEHACK_SANDBOX="V2", **(extra_env or {}))
    cwd = OPS
    if scratch:
        cwd = os.path.join(scratch, c["id"])
        shutil.rmtree(cwd, ignore_errors=True)
        os.makedirs(cwd)
    # placeholders let a case file hold no machine-specific path: {HOME} (the child's HOME), {CWD}, {V2}, {PERSONAL} (the child's personal code folder)
    home = env.get("HOME") or os.path.expanduser("~")
    ptr = os.path.join(home, ".config", "lifehack", "personal-code")
    try:
        personal = os.path.expanduser(open(ptr, encoding="utf-8").readline().strip()) or os.path.join(home, "lifehack-personal-code")
    except OSError:
        personal = os.path.join(home, "lifehack-personal-code")
    prompt = L["prompt"]
    for k, v in (("{HOME}", home), ("{CWD}", cwd), ("{V2}", V2), ("{PERSONAL}", personal)):
        prompt = prompt.replace(k, v)
    prompt += SUFFIX
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
    ns = argparse.Namespace(stream=stream, desk="/nonexistent/no-desk", sid=None, journal=os.path.join(home, ".claude/run/fire-journal.jsonl"), code_root=rm.ROOT,
                            sop=L["sop"], shared_ref=L["shared_ref"], register_file=[], home_prefix=[], wrong_move=L["wrong_re"], ignore_hook=[], json=True, files=files, registration_forbidden=bool(L.get("registration_forbidden")), student=bool(L.get("student")))
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
    for p in mine_new:
        try:
            os.remove(p); removed.append(p)
        except OSError:
            pass
    for p in mine_mod:
        repo = next((r for r in (V2, OPS) if p.startswith(r + "/")), None)
        if repo and b["files"].get(p) is None and p not in b["files"]:
            git(repo, "checkout", "--", p); removed.append("restored " + p)
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
            "build_mentioned": bool(BUILD_RE.search(txt)), "commits": sc.get("commits", {}), "foreign_changes_left": foreign[:10], "cleaned": removed}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run"])
    ap.add_argument("--cases", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--only")
    ap.add_argument("--model", default="sonnet", help="model tier for the live sessions (Round C exam: sonnet, in bypassPermissions mode like most students)")
    ap.add_argument("--settings", help="settings file for the child (default: lab-settings.json). Practice rounds pass a copy without Enver's own Edit(.claude/skills/**) deny, which a student does not have")
    ap.add_argument("--scratch")
    ap.add_argument("--env", action="append", default=[])
    a = ap.parse_args()
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
    print("desks before == after:", desks0 == sorted(os.listdir(os.path.join(notes, "desks"))))


if __name__ == "__main__":
    sys.exit(main())

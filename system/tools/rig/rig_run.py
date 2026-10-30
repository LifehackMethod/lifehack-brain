#!/usr/bin/env python3
# not-wired-yet: run by hand and by test_rig_selftest.sh; the scheduled cadence job is the meal's (plan 3b), not built yet
"""rig_run.py - the Phase 3b test rig runner ("prove the friction holds"), replay mode.

WHY: the guards are speed bumps that read Bash as text. This rig throws known wrong moves at the REGISTERED
     hooks and reports, per pattern and per layer, what was caught, what slipped and what cried wolf.
     Plan: v2.plan.md Phase 3b; design: records/2026-10-29-rig-plan-draft.md (notes root).
WHAT: reads cases (JSONL, six dimensions + expect), builds a throwaway fixture (temp HOME, code root, notes root,
     a git repo), and pipes a realistic PreToolUse payload into every hook command that hooks/hooks.json registers
     for that tool. Grade = exit code AND the fire-journal line the hook wrote (LHB_JOURNAL_PATH points at a scratch
     journal, the real one is never touched). A missing journal line is ERROR, never an allow.
GRADES: caught | caught-other-layer | slipped | false-alarm | clean | error.
MODES: (default) run cases | --selftest | --pairs | --off <hook> | --heat A,B
     Live-mode path scoring lives in rig_live_score.py (replay cannot trace a path).
REUSES: fire_journal_query.py is the shared reader for the REAL journal (rig_live_score.py); the replay reads its own
     scratch journal line by line because it needs exactly the lines one hook run wrote.
CALLER: Enver / the build window by hand, and test_rig_selftest.sh; the cadence job is the meal's (plan 3b).
Run: python3 system/tools/rig/rig_run.py --help
"""
import argparse, datetime, glob, itertools, json, os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))          # the harness code root (V2 checkout)
DEFAULT_CASES = os.path.join(HERE, "cases")
SIGNPOST_HOOKS = {"guard_git_push_signpost.sh", "guard_no_upstream_commit_signpost.sh"}
GRADES = ["caught", "caught-other-layer", "slipped", "false-alarm", "clean", "error"]
KEEP_ENV = ("PATH", "LANG", "LC_ALL", "TERM", "TMPDIR", "SHELL")


# ───────────────────────── registration ─────────────────────────
IF_COND = {}      # (script, command) -> the handler-level `if` (e.g. "Skill(checkin)"); the replay must honour it or it cries wolf on every other Skill


def registered_hooks(event="PreToolUse"):
    """[(matcher, script_name, command)] in registration order, read from hooks/hooks.json."""
    d = json.load(open(os.path.join(ROOT, "hooks", "hooks.json"), encoding="utf-8"))
    out = []
    for blk in d["hooks"].get(event, []):
        for h in blk.get("hooks", []):
            cmd = h.get("command", "")
            m = re.search(r"/([A-Za-z0-9_.\-]+\.(?:sh|py))", cmd)
            out.append((blk.get("matcher", "*"), m.group(1) if m else cmd[:40], cmd))
            if h.get("if"):
                IF_COND[(out[-1][1], cmd)] = h["if"]
    return out


def matches(matcher, tool):
    return matcher == "*" or re.fullmatch(matcher, tool) is not None


def has_journal_trap(script):
    for d in ("system/hooks", "hooks"):
        try:
            return "lhb_journal_fire" in open(os.path.join(ROOT, d, script), errors="replace", encoding="utf-8").read()
        except OSError:
            continue
    return False


# ───────────────────────── fixture ─────────────────────────
def build_fixture():
    T = tempfile.mkdtemp(prefix="rigfx-")
    F = {"T": T, "HOME": T + "/home", "CODE": T + "/code", "NOTES": T + "/notes", "REPO": T + "/repo", "REMOTE": T + "/remote.git"}
    F["DESK"] = F["NOTES"] + "/desks/rigdesk"
    F["PC"] = F["HOME"] + "/fictional-code"          # a FICTIONAL personal code folder (stop cases point the pointer file at it)
    F["PLUGINCACHE"] = F["HOME"] + "/.claude/plugins/cache/lifehack-brain/lifehack-brain/1.0"
    for d in (F["HOME"] + "/.config/lifehack", F["CODE"] + "/shared/notify", F["CODE"] + "/system/register", F["CODE"] + "/system/sops",
              F["CODE"] + "/system/hooks", F["CODE"] + "/hooks", F["CODE"] + "/system/tools", F["DESK"] + "/tools", F["DESK"] + "/records",
              F["DESK"] + "/canon", F["NOTES"] + "/system", F["PLUGINCACHE"] + "/.claude/skills/rigskill",
              F["HOME"] + "/.claude/skills/ClaudeOps/.claude/skills/rigskill"):
        os.makedirs(d, exist_ok=True)
    open(F["HOME"] + "/.config/lifehack/code-root", "w", encoding="utf-8").write(F["CODE"] + "\n")
    for src, dst in ((ROOT + "/shared/brain_root.py", F["CODE"] + "/shared/brain_root.py"),
                     (ROOT + "/system/tools/utf8_stdio.py", F["CODE"] + "/shared/utf8_stdio.py"),
                     (ROOT + "/system/hooks/build_mode_sops.conf", F["CODE"] + "/system/hooks/build_mode_sops.conf"),
                     (ROOT + "/system/hooks/placement.conf", F["CODE"] + "/system/hooks/placement.conf")):
        if os.path.exists(src):
            shutil.copy(src, dst)
    body = "\n".join("echo 'notify step %d of the real shared sender'" % i for i in range(40)) + "\n"
    open(F["CODE"] + "/shared/notify/notify-send.sh", "w", encoding="utf-8").write("#!/bin/bash\n" + body)
    open(F["CODE"] + "/shared/notify/notify-governor.py", "w", encoding="utf-8").write("print('real governor')\n")
    open(F["CODE"] + "/shared/paths.py", "w", encoding="utf-8").write("X = 1\n")
    for s in ("skill-building", "jobs", "hook", "desk-building"):
        open(F["CODE"] + "/system/sops/%s-sop.md" % s, "w", encoding="utf-8").write("# %s\n" % s)
    open(F["CODE"] + "/system/jobs.md", "w", encoding="utf-8").write("| id | cmd |\n")
    open(F["CODE"] + "/hooks/hooks.json", "w", encoding="utf-8").write('{"hooks":{}}\n')
    open(F["CODE"] + "/system/hooks/guard_x.sh", "w", encoding="utf-8").write("#!/bin/bash\nexit 0\n")
    open(F["CODE"] + "/system/register/register.jsonl", "w", encoding="utf-8").write("\n".join(json.dumps({"type": "tool", "path": p}) for p in (
        "/shared/notify/notify-send.sh", "/shared/notify/notify-governor.py", "/shared/paths.py", "/system/tools/not-shared.py")) + "\n")
    env = dict(os.environ, GIT_AUTHOR_NAME="rig", GIT_AUTHOR_EMAIL="rig@example.invalid", GIT_COMMITTER_NAME="rig",
               GIT_COMMITTER_EMAIL="rig@example.invalid", HOME=F["HOME"], GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_SYSTEM="/dev/null")
    subprocess.run(["git", "init", "-q", "--bare", F["REMOTE"]], env=env, capture_output=True)
    subprocess.run(["git", "init", "-q", "-b", "main", F["REPO"]], env=env, capture_output=True)
    open(F["REPO"] + "/a.txt", "w", encoding="utf-8").write("a\n")
    for cmd in (["config", "user.email", "rig@example.invalid"], ["config", "user.name", "rig"], ["add", "."], ["commit", "-qm", "init"],
                ["remote", "add", "origin", F["REMOTE"]], ["push", "-q", "-u", "origin", "main"]):
        subprocess.run(["git", "-C", F["REPO"]] + cmd, env=env, capture_output=True)
    return F


def expand(v, F):
    if isinstance(v, str):
        for k in ("CODE", "NOTES", "HOME", "DESK", "REPO", "PLUGINCACHE", "PC"):
            v = v.replace("{%s}" % k, F[k])
        v = v.replace("@@", "").replace("{REALCODE}", ROOT)      # "@@" splits a fake secret in the case file so secret scanners do not flag it;
        #      # the real V2 checkout: for guards whose zone is the harness tree they live in; hooks only READ the path, nothing is written
        return v
    if isinstance(v, dict):
        return {k: expand(x, F) for k, x in v.items()}
    if isinstance(v, list):
        return [expand(x, F) for x in v]
    return v


# ───────────────────────── one case ─────────────────────────
def run_stop_case(case, F, plugin_root, stub=False):
    """Round B end-of-turn replay: plant this turn's new files + the recorder's list, pipe a Stop payload into the registered
    end_of_turn_checks.sh. Caught = {"decision":"block"} on stdout. Planted files under {REALCODE} are removed afterwards."""
    sid = "rig-%s" % re.sub(r"[^A-Za-z0-9_-]", "-", case["id"])
    wdir, planted, problems = "%s/turnwrites-%s" % (F["T"], sid), [], []
    os.makedirs(wdir, exist_ok=True)
    open(F["HOME"] + "/.config/lifehack/personal-code", "w", encoding="utf-8").write(F["PC"] + "\n")
    os.makedirs(F["PC"], exist_ok=True)
    rows = []
    for pl in expand(case.get("plant", []), F):
        os.makedirs(os.path.dirname(pl["path"]), exist_ok=True)
        existed = os.path.exists(pl["path"])
        body = open(pl["from"], encoding="utf-8").read() if pl.get("from") else pl.get("content", "")
        open(pl["path"], "w", encoding="utf-8").write(body)
        if not existed and pl["path"].startswith(ROOT + "/"):
            planted.append(pl["path"])
        if pl.get("kind", "new") != "unrecorded":
            rows.append("p1\t%s\t%s\n" % (pl.get("kind", "new"), pl["path"]))
    if rows:
        open(wdir + "/%s.list" % sid, "w", encoding="utf-8").write("".join(rows))
    payload = json.dumps({"session_id": sid, "prompt_id": "p1", "cwd": F["T"], "hook_event_name": "Stop", "stop_hook_active": False})
    jpath = "%s/journal-%s.jsonl" % (F["T"], sid)
    env = {k: os.environ[k] for k in KEEP_ENV if k in os.environ}
    env.update({k: v for k, v in os.environ.items() if k.startswith("ROUNDB_")})
    env.update(HOME=F["HOME"], LIFEHACK_ROOT=F["NOTES"], LHB_JOURNAL_PATH=jpath, CLAUDE_CODE_SESSION_ID=sid, CLAUDE_PLUGIN_ROOT=plugin_root,
               LHB_TURN_WRITES_DIR=wdir, LIFEHACK_SANDBOX="V2", GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_SYSTEM="/dev/null")
    runs = []
    try:
        for matcher, script, cmd in registered_hooks("Stop"):
            if script != "end_of_turn_checks.sh":
                continue
            p = subprocess.run(["bash", "-c", cmd], input=payload, capture_output=True, text=True, cwd=F["T"], env=env, timeout=30)
            runs.append({"hook": script, "rc": p.returncode, "text": (p.stdout + p.stderr)[-600:], "block": '"decision": "block"' in p.stdout or '"decision":"block"' in p.stdout})
    except subprocess.TimeoutExpired:
        problems.append("end_of_turn_checks.sh timed out")
    finally:
        for f in planted:
            try:
                os.remove(f)
            except OSError:
                pass
    if not runs:
        problems.append("end_of_turn_checks.sh not registered under Stop")
    if (stub or has_journal_trap("end_of_turn_checks.sh")) and runs and not os.path.exists(jpath):
        problems.append("NO-JOURNAL-LINE:end_of_turn_checks.sh")
    deniers = [r["hook"] for r in runs if r["block"]]
    want = case.get("expect", {}).get("decision") in ("deny", "signpost")
    grade = "error" if problems else (("caught" if deniers else "slipped") if want else ("false-alarm" if deniers else "clean"))
    return {"id": case["id"], "grade": grade, "deniers": deniers, "hooks_run": [r["hook"] for r in runs], "problems": problems,
            "signpost_only": False, "text": next((r["text"] for r in runs if r["block"]), ""), "case": case}


def run_case(case, F, plugin_root, hooks, off=None, stub=False):
    if case.get("event") == "stop":
        return run_stop_case(case, F, plugin_root, stub)
    sid = "rig-%s" % re.sub(r"[^A-Za-z0-9_-]", "-", case["id"])
    tool = case["tool"]
    tin = expand(case["tool_input"], F)
    cwd = expand(case.get("cwd", "{NOTES}"), F)
    for s in case.get("setup", []):
        if s == "sop_receipt":
            os.makedirs(F["HOME"] + "/.claude/run/sop", exist_ok=True)
            open(F["HOME"] + "/.claude/run/sop/hook.%s.receipt" % sid, "w", encoding="utf-8").close()
        elif s.startswith("bm_seen:"):
            os.makedirs(F["HOME"] + "/.claude/run/build-mode", exist_ok=True)
            open(F["HOME"] + "/.claude/run/build-mode/%s.%s.seen" % (s.split(":", 1)[1], sid), "w", encoding="utf-8").close()
    payload = json.dumps({"session_id": sid, "cwd": cwd, "hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tin})
    jpath = "%s/journal-%s.jsonl" % (F["T"], sid)
    env = {k: os.environ[k] for k in KEEP_ENV if k in os.environ}
    env.update({k: v for k, v in os.environ.items() if k.startswith("ROUNDB_")})   # Round B switches: the environment wins (roundB.conf)
    env.update(HOME=F["HOME"], LIFEHACK_ROOT=F["NOTES"], LHB_JOURNAL_PATH=jpath, CLAUDE_CODE_SESSION_ID=sid, CLAUDE_PLUGIN_ROOT=plugin_root,
               LIFEHACK_SANDBOX="V2", GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_SYSTEM="/dev/null")
    runs, problems, seen = [], [], set()
    for matcher, script, cmd in hooks:
        if script == off or not matches(matcher, tool) or (script, cmd) in seen:
            continue
        cond = IF_COND.get((script, cmd))
        if cond:
            mm = re.fullmatch(r"(\w+)\(([^)]*)\)", cond)
            if mm and mm.group(1) == "Skill" and tin.get("skill") != mm.group(2):
                continue
        seen.add((script, cmd))
        try:
            p = subprocess.run(["bash", "-c", cmd], input=payload, capture_output=True, text=True,
                               cwd=cwd if os.path.isdir(cwd) else F["T"], env=env, timeout=30)
            rc, err = p.returncode, (p.stderr + p.stdout)[-600:]
        except subprocess.TimeoutExpired:
            rc, err = -9, "TIMEOUT"
            problems.append("%s timed out" % script)
        runs.append({"hook": script, "rc": rc, "text": err})
    lines = []
    if os.path.exists(jpath):
        for ln in open(jpath, errors="replace", encoding="utf-8"):
            try:
                lines.append(json.loads(ln))
            except ValueError:
                problems.append("malformed journal line")
    byhook = {}
    for l in lines:
        byhook.setdefault(l.get("hook"), []).append(l)
    for r in runs:
        got = byhook.get(r["hook"], [])
        if (stub or has_journal_trap(r["hook"])) and not got:
            problems.append("NO-JOURNAL-LINE:%s" % r["hook"])
        elif got:
            r["journal_decision"] = got[-1].get("decision")
            if str(got[-1].get("exit_code")) != str(r["rc"]):
                problems.append("journal exit_code %s != rc %s for %s" % (got[-1].get("exit_code"), r["rc"], r["hook"]))
    deniers = [r["hook"] for r in runs if r["rc"] == 2]
    exp = case.get("expect", {})
    expect_block = exp.get("decision") in ("deny", "signpost")
    if problems:
        grade = "error"
    elif expect_block:
        if not deniers:
            grade = "slipped"
        else:
            grade = "caught" if (not exp.get("layer") or exp["layer"] in deniers) else "caught-other-layer"
    else:
        grade = "false-alarm" if deniers else "clean"
    return {"id": case["id"], "grade": grade, "deniers": deniers, "hooks_run": [r["hook"] for r in runs], "problems": problems,
            "signpost_only": bool(deniers) and all(d in SIGNPOST_HOOKS for d in deniers),
            "text": next((r["text"] for r in runs if r["rc"] == 2), ""), "case": case}


def run_all(cases, plugin_root, off=None, only=None, stub=False):
    F = build_fixture()
    try:
        hooks = registered_hooks()
        return [run_case(c, F, plugin_root, hooks, off, stub) for c in cases if (not only or re.search(only, c["id"]))]
    finally:
        shutil.rmtree(F["T"], ignore_errors=True)


def load_cases(path):
    files = sorted(glob.glob(os.path.join(path, "*.jsonl"))) if os.path.isdir(path) else [path]
    out = []
    for f in files:
        for ln in open(f, encoding="utf-8"):
            ln = ln.strip()
            if ln and not ln.startswith("#"):
                out.append(json.loads(ln))
    return [c for c in out if c.get("mode", "replay") == "replay"]


# ───────────────────────── selftest ─────────────────────────
def make_stub_root():
    """A plugin root whose every hook is an inert `exit 0` that still writes its journal line."""
    S = tempfile.mkdtemp(prefix="rigstub-")
    os.makedirs(S + "/system/hooks")
    os.makedirs(S + "/hooks")
    os.symlink(ROOT + "/system/hooks/lib", S + "/system/hooks/lib")
    for f in glob.glob(ROOT + "/system/hooks/*.sh") + glob.glob(ROOT + "/system/hooks/*.py") + glob.glob(ROOT + "/hooks/*.sh"):
        n = os.path.basename(f)
        open(S + ("/hooks/" if "/system/" not in f else "/system/hooks/") + n, "w", encoding="utf-8").write(
            '#!/bin/bash\n_d="%s/system/hooks"; . "$_d/lib/journal.sh" 2>/dev/null || lhb_journal_fire() { :; }\n'  # allow-silence: inert stand-in hook; journal absence must not change its allow
            'trap \'lhb_journal_fire "$?" "%s" "PreToolUse" "" 2>/dev/null || true\' EXIT\ncat >/dev/null\nexit 0\n' % (ROOT, n))  # allow-silence: inert stand-in hook; a journal hiccup must not change its allow
    return S


def selftest(cases):
    S = make_stub_root()
    try:
        res = run_all(cases, S, stub=True)
    finally:
        shutil.rmtree(S, ignore_errors=True)
    bad = []
    for r in res:
        want_block = r["case"].get("expect", {}).get("decision") in ("deny", "signpost")
        if want_block and r["grade"] != "slipped":
            bad.append((r["id"], "inert hooks graded %s, must be slipped (%s)" % (r["grade"], r["problems"])))
        elif not want_block and r["grade"] != "clean":
            bad.append((r["id"], "inert hooks graded %s, must be clean (%s)" % (r["grade"], r["problems"])))
    return res, bad


# ───────────────────────── reports ─────────────────────────
def field(case, name):
    if name == "layer":
        return case.get("expect", {}).get("layer") or "(any)"
    v = case.get(name)
    return str(v) if v is not None else "-"


def heat(results, a, b):
    rows = sorted({field(r["case"], a) for r in results})
    cols = sorted({field(r["case"], b) for r in results})
    ab = {"caught": "C", "caught-other-layer": "O", "slipped": "S", "false-alarm": "F", "clean": "k", "error": "E"}
    out = ["| %s \\ %s | %s |" % (a, b, " | ".join(cols)), "|---|%s|" % "|".join("---" for _ in cols)]
    for rr in rows:
        cells = []
        for cc in cols:
            sel = [r for r in results if field(r["case"], a) == rr and field(r["case"], b) == cc]
            if not sel:
                cells.append("EMPTY")
            else:
                cnt = {}
                for r in sel:
                    cnt[ab[r["grade"]]] = cnt.get(ab[r["grade"]], 0) + 1
                cells.append(" ".join("%d%s" % (n, g) for g, n in sorted(cnt.items())))
        out.append("| %s | %s |" % (rr, " | ".join(cells)))
    return "\n".join(out) + "\n\nlegend: C caught, O caught-other-layer, S slipped, F false-alarm, k clean (harmless allowed), E error, EMPTY no case"


def tally(results, key):
    t = {}
    for r in results:
        t.setdefault(key(r), {g: 0 for g in GRADES})[r["grade"]] += 1
    lines = ["| group | N | %s |" % " | ".join(GRADES), "|---|---|%s|" % "|".join("---" for _ in GRADES)]
    for k in sorted(t):
        lines.append("| %s | %d | %s |" % (k, sum(t[k].values()), " | ".join(str(t[k][g]) for g in GRADES)))
    return "\n".join(lines)


def is_block(r):
    return r["case"].get("expect", {}).get("decision") in ("deny", "signpost")


def weights_ok(results):
    """None if every case carries a real weight (a number > 0) AND a weight_basis saying where it came from; else the reason to refuse."""
    bad = [r["case"]["id"] for r in results if not isinstance(r["case"].get("weight"), (int, float)) or r["case"].get("weight") <= 0 or not r["case"].get("weight_basis")]
    return None if not bad else "%d case(s) have a null/default weight or no weight_basis (e.g. %s)" % (len(bad), ", ".join(bad[:3]))


def weighted(results):
    n_c = sum(1 for r in results if r["grade"] in ("caught", "caught-other-layer"))
    n_b = sum(1 for r in results if is_block(r))
    why = weights_ok(results)
    if why:      # coordinator ruling 2026-10-29: never print a weighted figure whose weights are missing or default
        return "weighted coverage: REFUSED (%s). Unweighted: %d of %d wrong-move cases caught" % (why, n_c, n_b)
    wc = sum(r["case"]["weight"] for r in results if r["grade"] in ("caught", "caught-other-layer"))
    wb = sum(r["case"]["weight"] for r in results if is_block(r))
    return "weighted coverage %.1f%% = sum(weight of caught wrong-move cases) / sum(weight of all wrong-move cases) = %.3f / %.3f (unweighted %d of %d)" % (
        100 * wc / wb if wb else 0, wc, wb, n_c, n_b)


def pairs_report(results):
    reg = sorted({(m, s) for m, s, _ in registered_hooks()})
    static = [(s1, s2) for (m1, s1), (m2, s2) in itertools.combinations(reg, 2)
              if s1 != s2 and any(matches(m1, t) and matches(m2, t) for t in ("Bash", "Write", "Edit", "MultiEdit"))]
    obs = {}
    for r in results:
        if len(set(r["deniers"])) > 1:
            for a, b in itertools.combinations(sorted(set(r["deniers"])), 2):
                obs.setdefault((a, b), []).append(r["id"])
    out = ["Registered PreToolUse hooks: %d; pairs sharing a Bash/Write/Edit matcher: %d (static, matcher only); pairs that CO-DENIED in the battery: %d" % (
        len({s for _, s in reg}), len(static), len(obs)), "",
        "| pair (can co-deny the same call) | cases where both denied | what the user sees |", "|---|---|---|"]
    for (a, b), ids in sorted(obs.items()):
        out.append("| %s + %s | %d: %s | one message only (nibble 1: Claude Code showed one of them); needs a live session to say which |" % (
            a, b, len(ids), ", ".join(ids[:4]) + (" ..." if len(ids) > 4 else "")))
    if not obs:
        out.append("| none observed | | |")
    return "\n".join(out)


def render(results, title, extra=""):
    cnt = {g: sum(1 for r in results if r["grade"] == g) for g in GRADES}
    L = ["# %s" % title, "", "Cases: %d. " % len(results) + ", ".join("%s %d" % (g, cnt[g]) for g in GRADES), "", weighted(results), "",
         "## Per pattern", tally(results, lambda r: r["case"].get("pattern", "-")), "", "## Per layer (expected layer)",
         tally(results, lambda r: field(r["case"], "layer")), "", "## Per road", tally(results, lambda r: r["case"].get("road", "-")), "",
         "## Heat map: road x layer", heat(results, "road", "layer"), "", "## Heat map: wrong_move x actor", heat(results, "wrong_move", "actor"), "",
         "## Every case", "", "| id | road | wrong_move | grade | denied by | note |", "|---|---|---|---|---|---|"]
    for r in results:
        note = "signpost only" if r["signpost_only"] else ("; ".join(r["problems"])[:80] if r["problems"] else "")
        L.append("| %s | %s | %s | %s | %s | %s |" % (r["id"], r["case"].get("road"), r["case"].get("wrong_move"), r["grade"].upper(),
                                                     ", ".join(r["deniers"]) or "-", note))
    return "\n".join(L) + "\n" + extra


def notes_root():
    try:
        return subprocess.check_output([sys.executable, ROOT + "/shared/brain_root.py", "--quiet"], text=True).strip()
    except Exception:
        return ""


def main():
    ap = argparse.ArgumentParser(description="Phase 3b rig runner (replay mode, zero model calls).")
    ap.add_argument("--cases", default=DEFAULT_CASES, help="a cases/*.jsonl file or folder")
    ap.add_argument("--only", help="regex on case id")
    ap.add_argument("--selftest", action="store_true", help="inert hooks must grade every wrong move SLIPPED; exits 1 if the rig cannot fail")
    ap.add_argument("--pairs", action="store_true", help="list pairs of guards that co-deny the same call (masked by a sibling)")
    ap.add_argument("--off", metavar="HOOK", help="remove one guard (script name) from the replay set and show what catches next")
    ap.add_argument("--heat", metavar="A,B", help="print a heat map of two case fields (e.g. road,layer)")
    ap.add_argument("--label", default="replay", help="result file label")
    ap.add_argument("--no-write", action="store_true", help="print only; do not write the results file")
    a = ap.parse_args()
    cases = load_cases(a.cases)
    if not cases:
        print("no replay cases found at %s" % a.cases)
        return 2
    _, bad = selftest(cases)          # the rig must prove it can fail, every run
    if bad:
        print("SELFTEST FAILED - the rig cannot tell a working guard from an inert one; refusing to report:")
        for i, why in bad[:15]:
            print("  %s: %s" % (i, why))
        return 1
    print("selftest ok: with every hook inert, all %d cases grade as expected (wrong moves SLIPPED, harmless CLEAN)" % len(cases))
    if a.selftest:
        return 0
    res = run_all(cases, ROOT, only=a.only)
    extra, title = "", "Rig %s, %s" % (a.label, datetime.date.today().isoformat())
    if a.off:
        off = run_all(cases, ROOT, off=a.off, only=a.only)
        base = {r["id"]: r for r in res}
        rows = ["", "## Fallback with `%s` switched off" % a.off, "", "| case | baseline | with guard off | caught by now |", "|---|---|---|---|"]
        for r in off:
            b = base[r["id"]]
            if a.off in b["deniers"]:
                rows.append("| %s | %s (%s) | %s | %s |" % (r["id"], b["grade"], ", ".join(b["deniers"]), r["grade"].upper(), ", ".join(r["deniers"]) or "NOTHING"))
        extra = "\n".join(rows) + "\n"
        res, title = off, title + " (off: %s)" % a.off
    if a.pairs:
        extra += "\n## Pairs\n\n" + pairs_report(res) + "\n"
    text = render(res, title, extra)
    if a.heat:
        x, y = a.heat.split(",")
        text += "\n## Heat map: %s x %s\n%s\n" % (x, y, heat(res, x, y))
    print(text)
    if not a.no_write and notes_root():
        d = os.path.join(notes_root(), "state", "projects", "v2", "records", "rig-results")
        os.makedirs(d, exist_ok=True)
        base = "%s-%s%s" % (datetime.date.today().isoformat(), a.label, ("-off-" + a.off.replace(".sh", "")) if a.off else "")
        open(os.path.join(d, base + ".md"), "w", encoding="utf-8").write(text)
        with open(os.path.join(d, base + ".jsonl"), "w", encoding="utf-8") as f:
            for r in res:
                f.write(json.dumps({k: v for k, v in r.items() if k != "case"} | {"case": r["case"]["id"]}) + "\n")
        print("wrote %s.md and .jsonl" % os.path.join(d, base))
    return 1 if any(r["grade"] == "error" for r in res) else 0   # a run with errors never passes quietly


if __name__ == "__main__":
    sys.exit(main())

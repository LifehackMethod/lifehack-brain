#!/usr/bin/env bash
# job-sim.sh — the time-compressed rig for the self-monitoring jobs (plan task 2.0).
#
# WHY: the job wrapper (job-run.sh), the session line (health_line.py) and the push path
#   (notify-send.sh -> notify-governor.py) only prove themselves over DAYS of real schedule. This rig
#   replays days in seconds: it advances a fake clock one period per tick, runs the REAL scripts the way
#   launchd would (a plain calendar fire, and --if-overdue at simulated logins), and after EVERY tick
#   asserts the exact one-line session report and the exact cumulative push count. It exists so that a
#   change to any of the four scripts is caught in under a minute, before it is caught by a silent week.
#
# WHAT IT COVERS (the real job-run.sh, health_line.py, notify-send.sh and notify-governor.py, unmodified
#   in behaviour):
#   - 15 fixed scenarios: quiet week; died and stayed dead; died then recovered; laptop shut 3 days then
#     opened (at-login catch-up); silent-success never stamps; hang kills and records; stood-down never
#     pages; transient (rc=2); two jobs failing at once; pointer broken (launch.err); never-ran is never OK;
#     four jobs fail in one day (the daily cap of 3 is per job; 4 texts); a recovery after a job used its 3;
#     a night failure (deferred; delivered by the job's own next run after 07:00, or dropped after 18 h).
#   - 2.5e: a before/after snapshot of the REAL job state tree, real job locks and the real governor state file;
#     any change is a MISS "seam leak: <path>".
#   - 50 (per-commit) or 200 (--gate) fuzz reps of random mode/flavor/gap sequences, FIXED seed, checked against an oracle: a small
#     python model of the intended rules (wrapper alert rule + governor + session line) that predicts the
#     line and the push list. The scenarios carry hand-written expectations; the model is cross-checked
#     against them too.
#   - the GOVERNOR: quiet hours (22:00-07:00), 24 h identity dedup and the daily cap of 3 per job (source job-run:<job>; recoveries exempt) ARE
#     exercised. The notify log sits AFTER the governor (LIFEHACK_NOTIFY_LOG, see notify-send.sh), so the
#     push counts asserted here are exactly what would have reached the phone. The governor runs against a
#     throwaway NOTIFY_STATE_FILE and the fake clock (TZ=UTC, so the quiet-hour is the UTC hour).
#
# NOT COVERED, BY DESIGN: real launchd sleep/wake coalescing and real logins (the rig only calls the
#   wrapper at the instants it says); real ntfy delivery (curl, the phone); real Google/Claude auth and
#   pre-flights (sim-* jobs need nothing); real wall-clock behaviour (the 1 s START_MARK sleep is skipped
#   under the fake clock). Sprint 0 proved those live; one live kickstart per gate keeps them honest.
#
# TEST-ONLY SEAMS it relies on, all inert when unset: LIFEHACK_FAKE_NOW (job-run.sh, health_line.py,
#   notify-governor.py, the stub), LIFEHACK_STATE_DIR, LIFEHACK_JOBS_FILE (job-run.sh, health_line.py),
#   LIFEHACK_NOTIFY_LOG (notify-send.sh), and the job names "sim-*" in job-run.sh (honoured only while
#   LIFEHACK_STATE_DIR is set). The rig never touches ~/.config/lifehack, never pushes, never uses the
#   network, and runs no real job. HOME is pointed at a throwaway directory.
#
# HOW TO RUN:   bash system/tools/tests/job-sim.sh            per-commit run: 50 fuzz reps, budget DEFAULT_BUDGET s
#               bash system/tools/tests/job-sim.sh --gate     full gate run: 200 fuzz reps, budget GATE_BUDGET s
#   exit 0 = every row green, "fuzz: n/n (seed ...)", inside the budget.   exit 1 = any miss (printed).
#   Budgets carry >= 2x headroom over measured runs, so load alone cannot flip it RED. JOB_SIM_BUDGET=<s> overrides.
#   JOB_SIM_BREAK=1 bash system/tools/tests/job-sim.sh     deliberately corrupts ONE expected value;
#   the rig must then exit 1 (proof that the assertions can fail).
#   JOB_SIM_FUZZ=<n> sets the rep count (default 50; 200 with --gate; seed is fixed).  JOB_SIM_V=1 prints the per-tick timeline.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export JOB_SIM_ROOT="$(cd "$HERE/../../.." && pwd)"
exec python3 - "$@" <<'PYEOF'
import calendar, os, random, shutil, subprocess, sys, tempfile, time
from concurrent.futures import ThreadPoolExecutor

ROOT = os.environ["JOB_SIM_ROOT"]
JR = f"{ROOT}/system/tools/job-run.sh"
HL = f"{ROOT}/system/tools/health_line.py"
NS = f"{ROOT}/shared/notify/notify-send.sh"
DEFAULT_BUDGET = 40.0   # seconds: >= 2x the slowest measured default (50-rep) run
GATE_BUDGET = 120.0     # seconds: 2x the measured gate (200-rep) run
BREAK = os.environ.get("JOB_SIM_BREAK") == "1"
VERBOSE = os.environ.get("JOB_SIM_V") == "1"
GATE = "--gate" in sys.argv[1:]
FUZZ_N = int(os.environ.get("JOB_SIM_FUZZ") or (200 if GATE else 50))
FUZZ_SEED = 20261027
BUDGET = float(os.environ.get("JOB_SIM_BUDGET") or (GATE_BUDGET if GATE else DEFAULT_BUDGET))
P = 3600
DAY = 86400
BASE = calendar.timegm((2026, 11, 2, 0, 0, 0))   # a Monday, 00:00 UTC
SEAMS = ["LIFEHACK_FAKE_NOW", "LIFEHACK_STATE_DIR", "LIFEHACK_JOBS_FILE", "LIFEHACK_NOTIFY_LOG",
         "LIFEHACK_JOBS_STATE_DIR", "LIFEHACK_JOBS_MANIFEST", "JOB_RUN_NOTIFY", "JOB_RUN_WATCHDOG",
         "NOTIFY_STATE_FILE", "JOB_SIM_DIR"]
STAND_REASON = "the job's own pre-flight stood down"
REPAIR = "jobs cannot find the code — open any desk once to repair"


def hhmm(t):
    return time.strftime("%a %H:%M", time.gmtime(t))


# ───────────────────────── the oracle: a model of the INTENDED rules ─────────────────────────
def _age(s):  # same wording rule as health_line._age
    s = max(0, int(s))
    if s < 3600: return f"{s // 60}m"
    if s < 48 * 3600: return f"{s // 3600}h"
    return f"{s // 86400}d"


class Model:
    CAP, DEDUP, QS, QE, MAXDEF = 3, 24 * 3600, 22, 7, 18 * 3600

    def __init__(self, jobs):            # jobs: [(name, period)]
        self.jobs = list(jobs)
        self.j = {n: dict(P=p, ls=None, lr=None, alerted=False, le=False, errs=0) for n, p in jobs}
        self.sent, self.deferred, self.log = [], [], []   # log: (title, identity)

    def quiet(self, t):
        h = (t // 3600) % 24
        return h >= self.QS or h < self.QE

    def gov(self, t, job, basis, title, msg, identity, defer_ok=True, exempt=False):
        # source is 'job-run:<job>' (2.5b): dedup and the daily cap are per job; a recovery is cap-exempt
        # (and does not count toward the cap), but still respects quiet hours and dedup.
        if any(k == (job, basis) and ts >= t - self.DEDUP for ts, k, _j, _e in self.sent): return
        if self.quiet(t):
            if defer_ok: self.deferred.append((t, job, title, msg, exempt))
            return
        if not exempt and sum(1 for ts, _k, j, e in self.sent if j == job and not e and ts >= t - 86400) >= self.CAP: return
        self.sent.append((t, (job, basis), job, exempt)); self.log.append((title, identity))

    def run(self, job, flavor, mode, t):
        s = self.j[job]; P_ = s["P"]
        s["le"] = False
        self.flush(t)        # 2.5a: job-run.sh flushes the deferred queue on EVERY run, before its alert logic
        if flavor == "login" and s["ls"] is not None:
            if t - s["ls"] < P_ - min(P_ // 10, 1800): return          # stood down, nothing recorded
        rc = {"ok": 0, "fail": 1, "silent": 1, "hang": 143, "standdown": 75, "transient": 2}[mode]
        reason = {"standdown": STAND_REASON}.get(mode, "")
        if rc not in (0, 75, 2): s["errs"] += 1
        if rc == 0:
            s["ls"] = t; s["lr"] = (0, "")
            if s["alerted"]:
                self.gov(t, job, ("id", f"job-up:{job}:{s['alerted']}"), f"Job recovered: {job}",
                         f"{job} succeeded again · output check passed", f"job-up:{job}:{s['alerted']}", exempt=True)
                s["alerted"] = False
            return
        s["lr"] = (rc, reason)
        if rc == 75 or s["alerted"]: return
        last_ok = "never"
        if s["ls"] is not None:
            age = t - s["ls"]
            if age < 2 * P_: return        # 2.5d: the 2nd consecutive miss pages (age >= 2 x period)
            last_ok = f"{age // 3600}h ago"
        self.gov(t, job, ("id", f"job-down:{job}:{t}"), f"Job down: {job}",
                 f"exit {rc} · last success {last_ok} · next: open any desk; the first line names it, the error is in "
                 f"~/.config/lifehack/state/jobs/{job}/errors/", f"job-down:{job}:{t}")
        s["alerted"] = t

    def flush(self, t):
        keep, send = [], []
        for item in self.deferred:
            if t - item[0] > self.MAXDEF: continue
            (keep if self.quiet(t) else send).append(item)
        self.deferred = keep
        for _, job, title, msg, exempt in send:   # replayed with no identity: dedup keys on the message text
            self.gov(t, job, ("msg", msg), title, msg, "", defer_ok=False, exempt=exempt)

    def line(self, t):
        if any(s["le"] for s in self.j.values()): return REPAIR
        never = [n for n, _ in self.jobs if self.j[n]["lr"] is None]
        if never: return "never ran: " + ", ".join(never)
        od = []
        for n, p in self.jobs:
            ls = self.j[n]["ls"]
            if ls is None: od.append(f"{n} (never succeeded)")
            elif t - ls >= 2 * p: od.append(f"{n} ({_age(t - ls)})")
        if od: return f"{len(od)} overdue: " + ", ".join(od)
        for n, _ in self.jobs:
            rc, reason = self.j[n]["lr"]
            if rc == 75: return f"stood down: {n} ({reason})"
        return f"jobs: {len(self.jobs)} OK"


# ───────────────────────── the real scripts, in a throwaway world ─────────────────────────
class World:
    def __init__(self, jobs):
        self.dir = tempfile.mkdtemp(prefix="job-sim-")
        d = self.dir
        self.state, self.sim, self.home = f"{d}/state", f"{d}/sim", f"{d}/home"
        self.nlog, self.manifest = f"{d}/notify.log", f"{d}/jobs.md"
        for p in (self.state, f"{self.sim}/mode", f"{self.sim}/out", self.home): os.makedirs(p)
        open(self.nlog, "w").close()
        rows = "".join(f'{n} | yes | {p} | sim stub wrote its output | $JOB_SIM_DIR/out/{n} ~ ^ran {n} at | none | 0 | none | '
                       f'bash "$LIFEHACK_CODE_ROOT/system/tools/tests/job-sim-stub.sh" {n}\n'
                       for n, p in jobs)
        open(self.manifest, "w").write("# throwaway manifest\n```jobs\n" + rows + "```\n")
        self.jobs = jobs
        self.t = None
        self.hangs = 0

    def env(self, t):
        e = {k: v for k, v in os.environ.items() if k not in SEAMS}
        e.update(HOME=self.home, TZ="UTC", LIFEHACK_FAKE_NOW=str(t), LIFEHACK_STATE_DIR=self.state,
                 LIFEHACK_JOBS_FILE=self.manifest, LIFEHACK_NOTIFY_LOG=self.nlog,
                 NOTIFY_STATE_FILE=f"{self.dir}/notify-state.json", JOB_SIM_DIR=self.sim,
                 JOB_RUN_WATCHDOG="1", NTFY_TOPIC="sim-topic", TMPDIR=self.dir)
        return e

    def sh(self, args, t):
        return subprocess.run(args, env=self.env(t), stdin=subprocess.DEVNULL, capture_output=True, text=True)

    def set_mode(self, job, mode):
        open(f"{self.sim}/mode/{job}", "w").write(mode)

    def run_job(self, job, flavor, t):
        args = ["bash", JR, job] + (["--if-overdue"] if flavor == "login" else [])
        return self.sh(args, t).returncode

    def inject_launch_err(self, job):
        os.makedirs(f"{self.state}/jobs/{job}", exist_ok=True)
        open(f"{self.state}/jobs/{job}/launch.err", "w").write("bash: /nowhere/job-run.sh: No such file\n")

    def flush(self, t):
        self.sh(["bash", NS, "--flush-deferred"], t)

    def line(self, t):
        return self.sh(["python3", HL], t).stdout.strip()

    def pushes(self):
        out = []
        for ln in open(self.nlog).read().splitlines():
            title, _msg, ident, _prio = (ln.split(" | ") + ["", "", "", ""])[:4] if ln.count(" | ") >= 3 else (ln, "", "", "")
            out.append((title, ident))
        return out

    def p(self, job, name):
        return f"{self.state}/jobs/{job}/{name}"

    def read(self, job, name):
        try: return open(self.p(job, name)).read()
        except OSError: return ""

    def errfiles(self, job):
        try: return len(os.listdir(self.p(job, "errors")))
        except OSError: return 0

    def ls_mtime(self, job):
        try: return int(os.path.getmtime(self.p(job, "last-success")))
        except OSError: return None

    def close(self):
        shutil.rmtree(self.dir, ignore_errors=True)


def play(name, jobs, t0, ticks, verbose_sink=None):
    """Run a tick list. A tick: dict(dt, acts{job:(flavor,mode)}, le[jobs], flush, line, push, titles, chk).
    Returns (n_ticks, [failure strings], world notes)."""
    w, m, fails, t, notes = World(jobs), Model(jobs), [], t0, []
    try:
        for i, tk in enumerate(ticks, 1):
            t += tk.get("dt", 0)
            for job in tk.get("le", []):
                w.inject_launch_err(job); m.j[job]["le"] = True
            for job, (flavor, mode) in tk.get("acts", {}).items():
                w.set_mode(job, mode)
                w.run_job(job, flavor, t)
                m.run(job, flavor, mode, t)
            if tk.get("flush"):
                w.flush(t); m.flush(t)
            line, pushes = w.line(t), w.pushes()
            exp_line, exp_n = tk.get("line"), tk.get("push")
            if BREAK and name == "died and stayed dead" and i == 5 and exp_n is not None:
                exp_n += 1                                    # JOB_SIM_BREAK: one deliberately wrong value
            tag = f"{name} tick {i} ({hhmm(t)})"
            if exp_line is not None and line != exp_line:
                fails.append(f"{tag}: line {line!r} != expected {exp_line!r}")
            if exp_n is not None and len(pushes) != exp_n:
                fails.append(f"{tag}: pushes {len(pushes)} != expected {exp_n}: {pushes}")
            if line != m.line(t):
                fails.append(f"{tag}: line {line!r} != oracle {m.line(t)!r}")
            if pushes != m.log:
                fails.append(f"{tag}: pushes {pushes} != oracle {m.log}")
            for jn, _ in jobs:
                if w.errfiles(jn) != m.j[jn]["errs"]:
                    fails.append(f"{tag}: {jn} errors/ files {w.errfiles(jn)} != oracle {m.j[jn]['errs']}")
            if tk.get("titles") is not None and [x[0] for x in pushes] != tk["titles"]:
                fails.append(f"{tag}: push titles {[x[0] for x in pushes]} != {tk['titles']}")
            if tk.get("chk"):
                for msg in tk["chk"](w, t) or []: fails.append(f"{tag}: {msg}")
            notes.append(f"{hhmm(t)}  {','.join(f'{j}:{a[1]}' for j, a in tk.get('acts', {}).items()) or '-':<22}"
                         f"{'FLUSH ' if tk.get('flush') else '':<6}pushes={len(pushes)}  {line}")
            if fails and name.startswith("fuzz"): break
        return len(ticks), fails, (notes, w.pushes())
    finally:
        w.close()


# ───────────────────────── the fixed scenarios ─────────────────────────
A, B, C, D = "sim-a", "sim-b", "sim-c", "sim-d"
OK1 = "jobs: 1 OK"


def od(*names_ages, n=None):
    return f"{len(names_ages)} overdue: " + ", ".join(f"{a} ({b})" for a, b in names_ages)


def seq(job, modes, lines, pushes, dt=P, flavor="cal", first_dt=0, titles=None):
    out = []
    for i, (m_, l_, p_) in enumerate(zip(modes, lines, pushes)):
        out.append(dict(dt=first_dt if i == 0 else dt, acts={job: (flavor, m_)}, line=l_, push=p_))
    return out


def scenarios():
    S = []
    # 1 quiet week: daily job, 7 calendar fires, plus a login right after each (stands down: not overdue)
    t = []
    for d in range(7):
        t.append(dict(dt=0 if d == 0 else DAY, acts={A: ("cal", "ok")}, line=OK1, push=0))
        t.append(dict(dt=600, acts={A: ("login", "fail")}, line=OK1, push=0))   # would fail if it ran
    t[-1]["chk"] = lambda w, _t: [] if w.errfiles(A) == 0 else ["a login 10 min after success ran the job"]
    S.append(("quiet week", [(A, DAY)], BASE + 12 * 3600, t))

    # 2 died and stayed dead: last success tick 2; first push on the 2nd consecutive miss (tick 4)
    S.append(("died and stayed dead", [(A, P)], BASE + 8 * 3600, seq(
        A, ["ok", "ok", "fail", "fail", "fail", "fail", "fail"],
        [OK1, OK1, OK1, od((A, "2h")), od((A, "3h")), od((A, "4h")), od((A, "5h"))],
        [0, 0, 0, 1, 1, 1, 1])))

    # 3 died then recovered
    S.append(("died then recovered", [(A, P)], BASE + 8 * 3600, seq(
        A, ["ok", "fail", "fail", "fail", "ok", "ok"],
        [OK1, OK1, od((A, "2h")), od((A, "3h")), OK1, OK1], [0, 0, 1, 1, 2, 2])))

    # 4 laptop shut 3 days, then opened: session line first (nobody ran), then the at-login catch-up
    t = [dict(dt=0, acts={A: ("cal", "ok")}, line=OK1, push=0),
         dict(dt=3 * DAY, acts={}, line=od((A, "3d")), push=0),
         dict(dt=60, acts={A: ("login", "ok")}, line=OK1, push=0),
         dict(dt=300, acts={A: ("login", "fail")}, line=OK1, push=0)]   # a 2nd login 5 min on stands down
    t[-1]["chk"] = lambda w, _t: [] if w.errfiles(A) == 0 else ["the 2nd login ran the job"]
    S.append(("laptop shut 3 days", [(A, DAY)], BASE + 12 * 3600, t))

    # 5 silent success never stamps: never succeeded, so the FIRST failure pushes at once
    t = seq(A, ["silent"] * 3, [od((A, "never succeeded"))] * 3, [1, 1, 1])
    t[-1]["chk"] = lambda w, _t: [] if w.ls_mtime(A) is None else ["last-success was stamped by a silent run"]
    S.append(("silent-success never stamps", [(A, P)], BASE + 8 * 3600, t))

    # 6 hang kills and records
    def hang_chk(w, t_):
        f = []
        if "watchdog: killing" not in w.read(A, "log"): f.append("log has no 'watchdog: killing'")
        if " rc=143 " not in w.read(A, "last-run"): f.append(f"last-run does not record the kill: {w.read(A, 'last-run')!r}")
        if w.ls_mtime(A) != w.t0s: f.append("last-success moved after a hang")
        return f
    t = seq(A, ["ok", "hang", "hang", "hang"], [OK1, OK1, od((A, "2h")), od((A, "3h"))], [0, 0, 1, 1])
    for k in (1, 2, 3): t[k]["chk"] = hang_chk
    S.append(("hang kills and records", [(A, P)], BASE + 8 * 3600, t))

    # 7 stood-down never pages (and a long stand-down turns into an overdue LINE, never a push)
    SD = f"stood down: {A} ({STAND_REASON})"
    S.append(("stood-down never pages", [(A, P)], BASE + 8 * 3600, seq(
        A, ["ok"] + ["standdown"] * 5,
        [OK1, SD, od((A, "2h")), od((A, "3h")), od((A, "4h")), od((A, "5h"))], [0] * 6)))

    # 8 transient (rc=2): same rule as a failure, no errors/ file; first push on the 2nd miss
    t = seq(A, ["ok", "transient", "transient", "transient", "transient", "ok"],
            [OK1, OK1, od((A, "2h")), od((A, "3h")), od((A, "4h")), OK1], [0, 0, 1, 1, 1, 2])
    S.append(("transient pages after 2 misses", [(A, P)], BASE + 8 * 3600, t))

    # 9 two jobs failing at once
    t = []
    for i, (m_, l_, p_, ti) in enumerate([
            ("ok", OK1.replace("1", "2"), 0, []), ("fail", OK1.replace("1", "2"), 0, []),
            ("fail", od((A, "2h"), (B, "2h")), 2, ["Job down: sim-a", "Job down: sim-b"]),
            ("fail", od((A, "3h"), (B, "3h")), 2, ["Job down: sim-a", "Job down: sim-b"]),
            ("fail", od((A, "4h"), (B, "4h")), 2, ["Job down: sim-a", "Job down: sim-b"])]):
        tk = dict(dt=0 if i == 0 else P, acts={A: ("cal", m_), B: ("cal", m_)}, line=l_, push=p_)
        if ti: tk["titles"] = ti
        t.append(tk)
    S.append(("two jobs failing at once", [(A, P), (B, P)], BASE + 8 * 3600, t))

    # 10 pointer broken: launch.err -> the repair line; the next run that reaches the wrapper clears it
    def le_chk(w, t_):
        f = []
        if os.path.getsize(w.p(A, "launch.err")) != 0: f.append("launch.err not cleared by the wrapper")
        if "launch.err was non-empty" not in w.read(A, "log"): f.append("log does not mention launch.err")
        return f
    t = [dict(dt=0, acts={A: ("cal", "ok")}, line=OK1, push=0),
         dict(dt=P, acts={}, le=[A], line=REPAIR, push=0),
         dict(dt=P, acts={}, line=REPAIR, push=0),
         dict(dt=P, acts={A: ("cal", "ok")}, line=OK1, push=0, chk=le_chk)]
    S.append(("pointer broken", [(A, P)], BASE + 8 * 3600, t))

    # 11 never-ran is never OK
    S.append(("never-ran is never OK", [(A, P), (B, P)], BASE + 8 * 3600, [
        dict(dt=0, acts={}, line=f"never ran: {A}, {B}", push=0),
        dict(dt=0, acts={A: ("cal", "ok")}, line=f"never ran: {B}", push=0),
        dict(dt=P, acts={B: ("cal", "standdown")}, line=od((B, "never succeeded")), push=0),
        dict(dt=P, acts={A: ("cal", "ok"), B: ("cal", "ok")}, line="jobs: 2 OK", push=0)]))

    # 12 (b) four jobs fail in one day -> FOUR pushes (2.5b: the cap of 3 is per job, source 'job-run:<job>')
    four = [(n, P) for n in (A, B, C, D)]
    def acts(m_): return {n: ("cal", m_) for n, _ in four}
    l4 = od((A, "2h"), (B, "2h"), (C, "2h"), (D, "2h"))
    dn = ["Job down: sim-a", "Job down: sim-b", "Job down: sim-c", "Job down: sim-d"]
    up = ["Job recovered: sim-a", "Job recovered: sim-b", "Job recovered: sim-c", "Job recovered: sim-d"]
    S.append(("four jobs fail in a day -> 4 pushes", four, BASE + 8 * 3600, [
        dict(dt=0, acts=acts("ok"), line="jobs: 4 OK", push=0),
        dict(dt=P, acts=acts("fail"), line="jobs: 4 OK", push=0),
        dict(dt=P, acts=acts("fail"), line=l4, push=4, titles=dn),
        dict(dt=P, acts=acts("fail"), line=od((A, "3h"), (B, "3h"), (C, "3h"), (D, "3h")), push=4, titles=dn),
        dict(dt=P, acts=acts("ok"), line="jobs: 4 OK", push=8, titles=dn + up)]))

    # 12b (b) a recovery is delivered even after its job used its 3 texts of the day (cap-exempt)
    cyc = []
    for k in range(4):                        # 4 incidents: the 4th "down" is capped, its recovery is not
        cyc += [dict(dt=P, acts={A: ("cal", "fail")}, line=OK1, push=None),
                dict(dt=P, acts={A: ("cal", "fail")}, line=od((A, "2h")), push=None),
                dict(dt=P, acts={A: ("cal", "ok")}, line=OK1, push=None)]
    cyc[0]["dt"] = P
    ct = [dict(dt=0, acts={A: ("cal", "ok")}, line=OK1, push=0)] + cyc
    # pushes after each incident's 3 ticks: down, recovery = +2 for incidents 1-3; incident 4: down capped, recovery +1
    for k, (d_, r_) in enumerate([(1, 2), (3, 4), (5, 6), (6, 7)]):
        ct[1 + 3 * k + 1]["push"] = d_ if k < 3 else 6    # the 2nd miss: down (capped on the 4th incident)
        ct[1 + 3 * k + 2]["push"] = r_                    # the success: recovery, always delivered
        ct[1 + 3 * k]["push"] = (0 if k == 0 else [2, 4, 6][k - 1])
    ct[-1]["titles"] = ["Job down: sim-a", "Job recovered: sim-a"] * 3 + ["Job recovered: sim-a"]
    S.append(("recovery delivered after the job used its 3", [(A, P)], BASE + 8 * 3600, ct))

    # 13 (b) overdue push during quiet hours: suppressed -> queued -> delivered by --flush-deferred
    def quiet_ticks(final):
        return [
            dict(dt=0, acts={A: ("cal", "ok")}, line=OK1, push=0),                     # 20:00
            dict(dt=P, acts={A: ("cal", "fail")}, line=OK1, push=0),                   # 21:00
            dict(dt=P, acts={A: ("cal", "fail")}, line=od((A, "2h")), push=0),         # 22:00 2nd miss: quiet, deferred
            dict(dt=3 * P, acts={A: ("cal", "fail")}, line=od((A, "5h")), push=0),     # 01:00 marker set: silent
        ] + final
    t13 = quiet_ticks([
        dict(dt=5 * P, acts={}, flush=True, line=od((A, "10h")), push=0),              # 06:00 still quiet: kept
        dict(dt=P, acts={}, flush=True, line=od((A, "11h")), push=1, titles=["Job down: sim-a"]),   # 07:00 delivered
        dict(dt=P, acts={A: ("cal", "ok")}, line=OK1, push=2, titles=["Job down: sim-a", "Job recovered: sim-a"])])
    S.append(("quiet-hours push deferred, flushed", [(A, P)], BASE + 20 * 3600, t13))
    # 13b 2.5a: nobody calls --flush-deferred; the job's own next run after 07:00 delivers the night page, once
    t13b = quiet_ticks([
        dict(dt=6 * P, acts={A: ("cal", "fail")}, line=od((A, "11h")), push=1, titles=["Job down: sim-a"]),   # 07:00 run flushes
        dict(dt=P, acts={A: ("cal", "fail")}, line=od((A, "12h")), push=1, titles=["Job down: sim-a"]),       # 08:00 not re-sent
        dict(dt=P, acts={A: ("cal", "ok")}, line=OK1, push=2, titles=["Job down: sim-a", "Job recovered: sim-a"])])
    S.append(("night failure delivered once at the first run after 07:00", [(A, P)], BASE + 20 * 3600, t13b))
    # 13c nothing runs for 19 h: the deferred page is dropped (max age 18 h), never delivered
    t13c = quiet_ticks([
        dict(dt=16 * P, acts={}, flush=True, line=od((A, "21h")), push=0),             # 17:00 next day: queued 22:00, 19 h old
        dict(dt=P, acts={A: ("cal", "ok")}, line=OK1, push=1, titles=["Job recovered: sim-a"])])
    S.append(("deferred push older than 18 h is dropped", [(A, P)], BASE + 20 * 3600, t13c))
    return S


# ───────────────────────── fuzz ─────────────────────────
MODES = ["ok"] * 5 + ["fail", "fail", "silent", "standdown", "transient", "transient"]


def fuzz_case(rep):
    r = random.Random(FUZZ_SEED * 1000 + rep)
    jobs = [(A, P)] + ([(B, P)] if r.random() < 0.25 else [])
    t0 = BASE + r.randrange(24) * 3600 + r.choice([0, 0, 1800])
    ticks = []
    for i in range(r.randint(4, 6)):
        dt = 0 if i == 0 else r.choice([P] * 6 + [600, 3 * P, 2 * P + 1, 37 * 60])
        tk = dict(dt=dt, acts={}, le=[])
        for n, _ in jobs:
            x = r.random()
            if x < 0.04: tk["le"].append(n)
            elif x < 0.9:
                mode = "hang" if r.random() < 0.015 else r.choice(MODES)
                tk["acts"][n] = (r.choice(["cal", "cal", "login"]), mode)
        tk["flush"] = r.random() < 0.12
        ticks.append(tk)
    return jobs, t0, ticks


def run_fuzz(rep):
    jobs, t0, ticks = fuzz_case(rep)
    n, fails, _ = play(f"fuzz#{rep}", jobs, t0, ticks)
    return n, fails


def prod_unchanged():
    # Seams inert when unset: health_line.py with every seam unset must say exactly what it says with
    # the seams pointed explicitly at the production defaults (same live state, same instant). It used
    # to demand "jobs: 1 OK", which went RED whenever the real job was mid-run or stood down.
    base = {k: v for k, v in os.environ.items() if k not in SEAMS}
    out = subprocess.run(["python3", HL], env=base, capture_output=True, text=True).stdout.strip()
    explicit = dict(base, LIFEHACK_STATE_DIR=os.path.expanduser("~/.config/lifehack/state"),
                    LIFEHACK_JOBS_FILE=os.path.join(os.path.dirname(os.path.dirname(HL)), "pulse-config.md"),
                    LIFEHACK_FAKE_NOW=str(int(time.time())))
    ref = subprocess.run(["python3", HL], env=explicit, capture_output=True, text=True).stdout.strip()
    ok = out == ref and bool(out) and not out.startswith("job health: could not read")
    return ok, out if ok else f"{out!r} (seams unset) vs {ref!r} (seams explicit)"


def real_snapshot():
    """2.5e: (existence, mtime_ns) of everything a rig run must never touch: the real job state tree, the real
    job locks, and the governor's real state file (what notify-governor.py uses with NOTIFY_STATE_FILE unset)."""
    import glob
    snap, paths = {}, set(glob.glob("/tmp/lifehack-job-*.lock"))
    paths.add("/tmp/claudeops-email-summary-write.lock")
    gov = os.path.join(os.environ.get("TMPDIR", "/tmp"), "lifehack-notify-state.json")
    paths.update({gov, gov + ".lock", gov + ".tmp"})
    for root, dirs, files in os.walk(os.path.expanduser("~/.config/lifehack/state/jobs")):
        paths.add(root); paths.update(os.path.join(root, n) for n in dirs + files)
    for q in paths:
        try: snap[q] = os.stat(q).st_mtime_ns
        except OSError: snap[q] = None
    return snap


def seam_leaks(before):
    after = real_snapshot()
    return sorted(q for q in set(before) | set(after) if before.get(q) != after.get(q))


def main():
    t_start = time.time()
    real_before = real_snapshot()
    sc = scenarios()
    notes = {}
    with ThreadPoolExecutor(max_workers=10) as ex:
        sfut = [(name, ex.submit(play_t0, name, jobs, t0, ticks)) for name, jobs, t0, ticks in sc]
        ffut = [ex.submit(run_fuzz, rep) for rep in range(FUZZ_N)]
        rows = [(name, f.result()) for name, f in sfut]
        rows.append(("row-contract", row_contract()))
        fz = [f.result() for f in ffut]
    bad = 0
    print(f"{'scenario':<38} | {'ticks':>5} | result")
    print("-" * 38 + "-+-" + "-" * 5 + "-+-" + "-" * 8)
    for name, (n, fails, extra) in rows:
        print(f"{name:<38} | {n:>5} | {'PASS' if not fails else 'FAIL'}")
        for f in fails:
            print(f"    MISS {f}"); bad += 1
        notes[name] = extra
    ok_prod, got = prod_unchanged()
    print(f"{'production unchanged (seams unset)':<38} | {'-':>5} | {'PASS' if ok_prod else 'FAIL'}")
    if not ok_prod:
        print(f"    MISS seams not inert: {got}"); bad += 1
    leaks = seam_leaks(real_before)
    print(f"{'real state untouched (no seam leak)':<38} | {'-':>5} | {'PASS' if not leaks else 'FAIL'}")
    for q in leaks:
        print(f"    MISS seam leak: {q}"); bad += 1
    passed = sum(1 for n, f in fz if not f)
    for n, f in fz:
        for x in f[:3]:
            print(f"    MISS {x}"); bad += 1
    print(f"fuzz: {passed}/{FUZZ_N} (seed {FUZZ_SEED})")
    if True:
        print("\n-- documented behaviour (asserted above) --")
        nt = notes["four jobs fail in a day -> 4 pushes"][1]
        print("four jobs fail in a day, pushes that reached the log (title | identity):")
        for title, ident in nt: print(f"    {title} | {ident}")
        print("quiet-hours timeline (job sim-a, period 1h; UTC):")
        for ln in notes["quiet-hours push deferred, flushed"][0]: print(f"    {ln}")
        print("night failure, no explicit flush (the job's own run delivers it at 07:00):")
        for ln in notes["night failure delivered once at the first run after 07:00"][0][-3:]: print(f"    {ln}")
    el = time.time() - t_start
    print(f"\nruntime {el:.1f}s / budget {BUDGET:g}s   {'ALL GREEN' if bad == 0 and el < BUDGET else 'RED'}")
    if el >= BUDGET:
        print(f"MISS runtime over the {BUDGET:g} s budget"); bad += 1
    return 1 if bad else 0


def row_contract():
    """5.1: a row carries its contract. A check that does not match -> exit 1 and no last-success; a row with no
    check -> exit 1 'no output check declared'; a matching check -> exit 0 (control, so the first two are not vacuous)."""
    jobs = [("sim-a", P), ("sim-b", P), ("sim-c", P)]
    w, fails, t = World(jobs), [], BASE + 12 * 3600
    stub = 'bash "$LIFEHACK_CODE_ROOT/system/tools/tests/job-sim-stub.sh"'
    try:
        rows = (f"sim-a | yes | {P} | o | $JOB_SIM_DIR/out/sim-a ~ ^this line never appears$ | none | 0 | none | {stub} sim-a\n"
                f"sim-b | yes | {P} | o |  | none | 0 | none | {stub} sim-b\n"
                f"sim-c | yes | {P} | o | $JOB_SIM_DIR/out/sim-c ~ ^ran sim-c at | none | 0 | none | {stub} sim-c\n")
        open(w.manifest, "w").write("# row-contract manifest\n```jobs\n" + rows + "```\n")
        for j in ("sim-a", "sim-b", "sim-c"): w.set_mode(j, "ok")
        rc = {j: w.run_job(j, "cal", t) for j in ("sim-a", "sim-b", "sim-c")}
        if rc["sim-a"] != 1: fails.append(f"row-contract: non-matching check exited {rc['sim-a']}, expected 1")
        if w.ls_mtime("sim-a") is not None: fails.append("row-contract: non-matching check stamped last-success")
        if "output check failed" not in w.read("sim-a", "last-run"): fails.append("row-contract: sim-a reason is not 'output check failed'")
        if rc["sim-b"] != 1: fails.append(f"row-contract: no-check row exited {rc['sim-b']}, expected 1")
        if w.ls_mtime("sim-b") is not None: fails.append("row-contract: no-check row stamped last-success")
        if "no output check declared" not in w.read("sim-b", "last-run"): fails.append("row-contract: sim-b reason is not 'no output check declared'")
        if rc["sim-c"] != 0: fails.append(f"row-contract: matching check exited {rc['sim-c']}, expected 0")
        if w.ls_mtime("sim-c") is None: fails.append("row-contract: matching check did not stamp last-success")
        return 3, fails, ([], [])
    finally:
        w.close()


def play_t0(name, jobs, t0, ticks):
    # a scenario check may need the first tick's time (w.t0s): wrap each chk to set it
    def wrap(chk):
        def inner(w, t):
            w.t0s = t0
            return chk(w, t)
        return inner
    ticks = [dict(tk, chk=wrap(tk["chk"])) if tk.get("chk") else tk for tk in ticks]
    return play(name, jobs, t0, ticks)


sys.exit(main())
PYEOF

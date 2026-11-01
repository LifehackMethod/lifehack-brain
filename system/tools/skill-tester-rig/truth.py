#!/usr/bin/env python3
# from orchestrator-v2/rig/stress/truth.py @ 2026-10-28
#   (kept: the read-everything-never-trust-the-record oracle shape, the exec.log begin/end join, the
#    per-unit token classification and the one-totals-line output; rewritten: the units are canary steps,
#    the expected outcome comes from canary/expected.py, the categories are CONTRACT.md §4.)
"""truth.py — the skill-tester-rig ORACLE (card TR1.2). Pure code: no model, no network, no clock.

  truth.py --run <run-id>        RUN_DIR = layout.run_dir(${SKILL_TESTER_SCRATCH:-~/lifehack-scratch/skill-tester-rig}, <run-id>)
                                 = <scratch>/actor-home/<run-id>/.claude/run/skill-tester/<run-id> (TR2.0b)
  truth.py --run-dir PATH        RUN_DIR = PATH (run-id = its basename; seeds: <scratch>/seeds when PATH is laid out
                                 by layout.py, else two levels up)
  truth.py --selftest            build synthetic runs, one per category; last line
                                 'SELFTEST 8/8 categories each seen failing' only if every category is caught
                                 and every clean control is all-ok.

It recomputes every step-N.json the run SHOULD have produced from the seed (+ the sN.answer files) by
importing canary/expected.py (never re-implementing the formula), compares the parsed disk file, and prints
(CONTRACT.md §3):
  sN <category>                     one per reached step
  FLAG second-copy <relpath>        any extra copy of a step file lying in RUN_DIR
  TOTAL ok=.. silent_wrong=.. double_ran=.. stuck=.. lost=.. skipped=.. out_of_order=.. false_done=..
Exit 0 = every reached step ok; 1 = otherwise; 4 = CANNOT-READ (seed, run dir or exec.log unreadable).

WHAT IT TRUSTS. The disk files and the expected records decide `ok`. record.tsv is read ONLY to tell
false_done (the record vouches for a file the disk does not hold) and to count committed writes for
double_ran; a record row can never turn a step `ok`. Only VALID record rows count (7 fields, this run-id,
correct rowsum, final newline), because those are the only rows the runner itself trusts (CONTRACT §2).

ONE CATEGORY PER STEP, first match wins, in this order:
  1 lost         the file is wrong but equal to the expected record once "facts" is removed from both.
                 (Moved ahead of false_done 2026-10-31, matrix F-06b: facts edited after commit.)
  2 false_done   a valid done/skipped-done row exists for sN AND (step-N.json is missing, OR it is wrong and
                 its sha256 differs from the sha in the latest such row). I.e. the record describes a file
                 that is not the one on disk.
  3 silent_wrong the file is wrong (unparseable, extra/missing key, wrong type/value), or a step file exists
                 for a step a correct run never produces (after a human "no" / an unanswered or off-menu step).
  4 skipped      a LATER step file exists, and sN's file is missing or sN never began in exec.log; OR a later
                 step BEGAN in exec.log while sN has no file and no begin (2026-10-31, F-14a live skip).
  5 stuck        no file, nothing later committed, and the step was reached (any begin / rejected / raw /
                 record evidence; an sN.answer file alone is not evidence).
  6 double_ran   see DOUBLE_RAN below.
  7 out_of_order some begin of sN sits in exec.log BEFORE any end of s(N-1), while s(N-1) appears in exec.log.
                 Order is exec.log LINE order (append order), never the epoch: a fake step finishes inside one
                 second, so epochs tie.
  8 ok
A step with no line: never reached, or a human step paused (no answer, no file, nothing later committed).
SHORT-STOP RULE (2026-10-31): a run that stops short WITHOUT a stated reason never passes. If the last reached
step is below the expected run's final step (12, or the human "no" step after a halt), and the stop is NOT a
legitimate human pause and NOT explained by a non-ok category on the last reached step, then the first
unreached step k is printed `sk stuck` (k=1 for a run that did zero steps) and the exit is 1.

DOUBLE_RAN, made precise. The canary's only side effect is step-N.json, written by temp file + rename, so
running a step twice is harmless exactly when both runs committed the same bytes. The runner appends one
`done` row, carrying sha256(step-N.json), after each commit, and exec.log carries begin/end per attempt.
  attempts(sN)  = begin lines for sN in exec.log
  completed(sN) = begins whose pid has a later end line for sN
  writes(sN)    = valid `done` rows for sN (skipped-done is not a write: the step was not re-run)
  double_ran  <=>  attempts >= 2  AND  ( writes carry >= 2 DISTINCT shas
                                         OR (completed >= 2 AND some write's sha != the disk file's sha) )
So: killed attempt + re-run (begin, begin, end, one row) is NOT double_ran; two full runs whose rows carry
the same sha (idempotent byte-identical re-run) is NOT double_ran; two committed writes of different bytes
IS double_ran even if the last one is correct. Limit, stated: a write that left no record row (killed
between rename and append) is invisible to this rule unless a later completed run overwrote it with
different bytes than the row says.
"""
import hashlib, json, os, pathlib, re, shutil, subprocess, sys, tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "canary"))
sys.path.insert(0, os.path.join(os.environ.get("LIFEHACK_V2", os.path.expanduser("~/lifehack-v2")), "shared", "emit"))  # shared layer, used in place
import expected  # noqa: E402  the one formula (canary/SPEC.md §7)
sys.path.insert(0, str(HERE))
import layout  # noqa: E402  the ONE run layout (TR2.0b)
import verdicts  # noqa: E402  the CANNOT-READ convention, used in place (CONTRACT §0)

CATS = ("ok", "silent_wrong", "double_ran", "stuck", "lost", "skipped", "out_of_order", "false_done")
STATUSES = ("done", "skipped-done", "waiting", "halted")
STEP_RE = re.compile(r"step-(\d+)")


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def canon(obj):
    """Type-strict, key-order-free form: true != 1, 1.0 != 1."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def scratch():
    return pathlib.Path(os.environ.get("SKILL_TESTER_SCRATCH") or
                        os.path.expanduser("~/lifehack-scratch/skill-tester-rig"))


def cannot_read(msg):
    verdicts.print_cannot_read(msg)
    sys.exit(verdicts.CANNOT_READ)


def read_seed(run_dir, run_id, seeds_dir):
    # CONTRACT §0 (2026-10-31): seed file and CANARY_SEED must AGREE when both exist; a mismatch is CANNOT-READ.
    p = seeds_dir / run_id
    file_seed = None
    if p.exists():
        text, err = verdicts.read_text(str(p), "seed file")
        if err:
            cannot_read(err)
        try:
            file_seed = int(text.strip())
        except ValueError:
            cannot_read("seed file is not one integer: %s" % p)
    env = os.environ.get("CANARY_SEED")
    env_seed = None
    if env is not None:
        try:
            env_seed = int(env.strip())
        except ValueError:
            cannot_read("CANARY_SEED is not one integer: %r" % env)
    if file_seed is not None and env_seed is not None and file_seed != env_seed:
        cannot_read("seed mismatch: %s says %d, CANARY_SEED says %d" % (p, file_seed, env_seed))
    if file_seed is not None:
        return file_seed
    if env_seed is not None:
        return env_seed
    cannot_read("no seed: %s missing and CANARY_SEED unset" % p)


def parse_record(path, run_id):
    """-> {n: [row dicts in order]} of VALID rows only."""
    rows = {}
    if not path.exists():
        return rows
    content = path.read_text(errors="replace")
    lines = content.split("\n")
    complete = lines[:-1]  # the last element is '' when the file ends in a newline; else an unterminated row
    for line in complete:
        f = line.split("\t")
        if len(f) != 7 or f[0] != run_id or f[2] not in STATUSES or not re.fullmatch(r"s\d+", f[1]):
            continue
        if sha256_bytes("\t".join(f[:6]).encode())[:12] != f[6]:
            continue
        rows.setdefault(int(f[1][1:]), []).append(dict(status=f[2], sha=f[4], model=f[5]))
    return rows


def parse_exec(path):
    """-> list of (line_index, n, 'begin'|'end', pid)."""
    out = []
    for i, line in enumerate(path.read_text(errors="replace").splitlines()):
        f = line.split("\t")
        if len(f) == 4 and re.fullmatch(r"s\d+", f[1]) and f[2] in ("begin", "end"):
            out.append((i, int(f[1][1:]), f[2], f[3]))
    return out


def classify(run_dir, run_id, seed):
    """-> (step_lines, flag_lines, totals dict). Pure function of the files."""
    ks = expected.kinds()
    answers, stop_at = {}, None          # stop_at: first human step a correct run cannot pass (no / off-menu answer)
    paused = set()
    for n in sorted(k for k, v in ks.items() if v == "human"):
        a = run_dir / ("s%d.answer" % n)
        if a.exists():
            v = a.read_text(errors="replace").rstrip("\n")
            if v in expected.MENU:
                answers[n] = v
            elif stop_at is None:
                stop_at = n
        else:
            paused.add(n)
    exp = {r["step"]: r for r in expected.expected_run(seed, answers)}
    if stop_at is not None:
        exp = {k: v for k, v in exp.items() if k < stop_at}

    disk = {}
    for n in range(1, expected.N_STEPS + 1):
        p = run_dir / ("step-%d.json" % n)
        if p.exists():
            disk[n] = p.read_bytes()
    rec = parse_record(run_dir / "record.tsv", run_id)
    ex = parse_exec(run_dir / "exec.log")

    def evidence(n):
        return (n in disk or n in rec or any(e[1] == n for e in ex)
                or any((run_dir / ("s%d.%s" % (n, s))).exists() for s in ("rejected", "raw.json")))
        # sN.answer is NOT reach-evidence: answers can be supplied before the run reaches the step.

    reached = [n for n in range(1, expected.N_STEPS + 1) if evidence(n)]
    top = max(reached) if reached else 0

    lines, totals = [], {c: 0 for c in CATS}
    paused_stop, last_cat = False, None
    for n in range(1, top + 1):
        later = any(m in disk for m in range(n + 1, expected.N_STEPS + 1))
        # 2026-10-31 (F-14a live skip): a LATER step that BEGAN in exec.log also proves sN was passed over,
        # even if that later step never committed (it fails its input pre-flight).
        later_began = any(e[1] > n and e[2] == "begin" for e in ex)
        if n in paused and n not in disk and not later and not later_began:
            paused_stop = True
            break                                   # a human step waiting for its answer: legitimate pause
        if n not in disk and not later and not later_began and not evidence(n):
            continue
        cat = judge(n, exp.get(n), disk.get(n), rec.get(n, []), ex, later, later_began)
        lines.append("s%d %s" % (n, cat))
        totals[cat] += 1
        last_cat = cat
    # SHORT-STOP RULE: stopped below the expected final step with no failure and no human pause to explain it.
    exp_last = max(exp) if exp else 0
    if not paused_stop and top < exp_last and last_cat in (None, "ok"):
        lines.append("s%d stuck" % (top + 1))
        totals["stuck"] += 1

    flags = []
    for p in sorted(run_dir.rglob("*")):
        if p.is_file() and STEP_RE.search(p.name) and not re.fullmatch(r"step-\d+\.json", p.name):
            flags.append("FLAG second-copy %s" % p.relative_to(run_dir))
    return lines, flags, totals


def judge(n, want, raw, rows, ex, later, later_began=False):
    begins = [e for e in ex if e[1] == n and e[2] == "begin"]
    ends = [e for e in ex if e[1] == n and e[2] == "end"]
    parsed, good = None, False
    if raw is not None:
        try:
            parsed = json.loads(raw.decode("utf-8").strip())
        except Exception:
            parsed = None
        good = want is not None and parsed is not None and canon(parsed) == canon(want)
    vouch = [r for r in rows if r["status"] in ("done", "skipped-done")]

    # 1 lost: the file exists and differs from the expected record ONLY in its facts. It is checked before
    #   false_done (ruling 2026-10-31, matrix F-06b): facts edited in a committed file also break the record's
    #   sha, but the specific, named failure is the lost facts.
    if (raw is not None and not good and want is not None and isinstance(parsed, dict)
            and parsed.get("facts") != want["facts"]
            and canon({k: v for k, v in parsed.items() if k != "facts"})
            == canon({k: v for k, v in want.items() if k != "facts"})):
        return "lost"
    # 2 false_done
    if vouch and (raw is None or (not good and vouch[-1]["sha"] != sha256_bytes(raw))):
        return "false_done"
    if raw is not None and not good:
        # 3 silent_wrong
        return "silent_wrong"
    # 4 skipped: no file and never begun, while a later step was committed or began (F-14a live skip)
    if (later and (raw is None or not begins)) or (later_began and raw is None and not begins):
        return "skipped"
    # 5 stuck
    if raw is None:
        return "stuck"
    # 6 double_ran
    writes = [r for r in rows if r["status"] == "done"]
    completed = [b for b in begins if any(e[3] == b[3] and e[0] > b[0] for e in ends)]
    if len(begins) >= 2 and (len({w["sha"] for w in writes}) >= 2 or
                             (len(completed) >= 2 and any(w["sha"] != sha256_bytes(raw) for w in writes))):
        return "double_ran"
    # 7 out_of_order
    prev = [e for e in ex if e[1] == n - 1]
    if n > 1 and prev:
        prev_end = [e[0] for e in prev if e[2] == "end"]
        first_end = min(prev_end) if prev_end else None
        if any(first_end is None or b[0] < first_end for b in begins):
            return "out_of_order"
    return "ok"


def run(run_dir, run_id, seeds_dir):
    if not run_dir.is_dir():
        cannot_read("run dir does not exist: %s" % run_dir)
    seed = read_seed(run_dir, run_id, seeds_dir)
    if not (run_dir / "exec.log").exists():
        cannot_read("exec.log missing (order cannot be checked): %s" % (run_dir / "exec.log"))
    lines, flags, totals = classify(run_dir, run_id, seed)
    for l in lines + flags:
        print(l)
    print("TOTAL " + " ".join("%s=%d" % (c, totals[c]) for c in CATS))
    return 0 if all(totals[c] == 0 for c in CATS if c != "ok") else 1


# ---------------------------------------------------------------------------------------------- selftest
class Fake:
    """A synthetic run dir laid out exactly as CONTRACT §1, built from expected.py's correct records."""

    def __init__(self, root, run_id, seed=4242, answers="s4=yes,s9=yes"):
        self.root, self.id, self.seed = root, run_id, seed
        self.dir = pathlib.Path(layout.run_dir(str(root), run_id))   # CONTRACT §1 / layout.py (TR2.0b)
        self.dir.mkdir(parents=True)
        (root / "seeds").mkdir(exist_ok=True)
        (root / "seeds" / run_id).write_text("%d\n" % seed)
        self.ans = expected.parse_answers(answers)
        for n, a in self.ans.items():
            (self.dir / ("s%d.answer" % n)).write_text(a + "\n")
        self.recs = expected.expected_run(seed, self.ans)
        self.exec, self.rows, self.pid = [], [], 1000

    def begin(self, n, pid=None):
        self.exec.append((n, "begin", pid or self.pid))

    def end(self, n, pid=None):
        self.exec.append((n, "end", pid or self.pid))

    def commit(self, n, text=None):
        p = self.dir / ("step-%d.json" % n)
        p.write_text(text if text is not None else expected.dumps(self.recs[n - 1]) + "\n")
        self.row(n, "done", sha256_bytes(p.read_bytes()))

    def row(self, n, status, sha):
        f = [self.id, "s%d" % n, status, "1761900000", sha, "fake-model"]
        self.rows.append("\t".join(f + [sha256_bytes("\t".join(f).encode())[:12]]))

    def step(self, n):
        self.pid += 1
        self.begin(n); self.commit(n); self.end(n)

    def full(self, upto=None):
        for n in range(1, (upto or len(self.recs)) + 1):
            self.step(n)
        return self

    def save(self):
        (self.dir / "exec.log").write_text("".join("1761900000\ts%d\t%s\t%s\n" % e for e in self.exec))
        (self.dir / "record.tsv").write_text("".join(r + "\n" for r in self.rows))
        return self


def selftest():
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="truth-selftest-"))
    root = tmp / "scratch"
    root.mkdir()
    out = {}

    def oracle(f):
        env = dict(os.environ, SKILL_TESTER_SCRATCH=str(root))
        env.pop("CANARY_SEED", None)
        p = subprocess.run([sys.executable, str(pathlib.Path(__file__).resolve()), "--run", f.id],
                           capture_output=True, text=True, env=env)
        cats = dict(l.split(" ", 1) for l in p.stdout.splitlines() if re.fullmatch(r"s\d+ \S+", l))
        return p.returncode, cats, p.stdout

    try:
        # ---- clean controls (must be all-ok, exit 0) ----
        clean = {}
        clean["full"] = Fake(root, "clean-full").full().save()
        f = Fake(root, "clean-kill-rerun").full(6)      # s7 killed before commit, re-run byte-identical
        f.begin(7, pid=7001); f.begin(7, pid=7002); f.commit(7); f.end(7, pid=7002)
        for n in range(8, 13):
            f.step(n)
        clean["kill-rerun"] = f.save()
        f = Fake(root, "clean-idem-twice").full(6)      # s7 ran to completion twice, identical bytes, two rows
        f.begin(7, pid=7101); f.commit(7); f.begin(7, pid=7102); f.commit(7); f.end(7, pid=7102)
        f.end(7, pid=7101)
        for n in range(8, 13):
            f.step(n)
        clean["idem-twice"] = f.save()
        clean["halt-no"] = Fake(root, "clean-halt", answers="s4=no").full().save()
        clean["waiting"] = Fake(root, "clean-wait", answers="").full().save()
        want_len = {"full": 12, "kill-rerun": 12, "idem-twice": 12, "halt-no": 4, "waiting": 3}
        clean_ok = True
        for k, f in clean.items():
            rc, cats, _ = oracle(f)
            good = rc == 0 and len(cats) == want_len[k] and set(cats.values()) == {"ok"}
            print("clean %-11s %s rc=%d steps=%d" % (k, "all-ok" if good else "NOT-CLEAN", rc, len(cats)))
            clean_ok &= good

        # ---- one corrupted run per category: (category, step it must name) ----
        def corrupt(cat):
            f = Fake(root, "bad-" + cat)
            if cat == "silent_wrong":     # s5 committed with a wrong value, record honest about it
                f.full(4); r = dict(f.recs[4], value=(f.recs[4]["value"] + 1) % 1000)
                f.pid += 1; f.begin(5); f.commit(5, expected.dumps(r) + "\n"); f.end(5)
                return f.save(), 5
            if cat == "lost":             # s6 facts reordered
                f.full(5); r = dict(f.recs[5], facts=list(reversed(f.recs[5]["facts"])))
                f.pid += 1; f.begin(6); f.commit(6, expected.dumps(r) + "\n"); f.end(6)
                return f.save(), 6
            if cat == "double_ran":       # s3 committed twice with different bytes; the last one is correct
                f.full(2); r = dict(f.recs[2], token="T03-deadbeef")
                f.begin(3, pid=3001); f.commit(3, expected.dumps(r) + "\n"); f.end(3, pid=3001)
                f.begin(3, pid=3002); f.commit(3); f.end(3, pid=3002)
                for n in range(4, 13):
                    f.step(n)
                return f.save(), 3
            if cat == "stuck":            # s8 check failed: rejected, no file, run stopped
                f.full(7); f.pid += 1; f.begin(8); f.end(8)
                (f.dir / "s8.rejected").write_text("garbage\n")
                return f.save(), 8
            if cat == "skipped":          # s5 never begun, no file, later steps committed
                f.full(4)
                for n in range(6, 13):
                    f.step(n)
                return f.save(), 5
            if cat == "out_of_order":     # s6 begins before s5 ends (contents correct)
                f.full(4); f.begin(5, pid=5001); f.begin(6, pid=6001); f.commit(5); f.end(5, pid=5001)
                f.commit(6); f.end(6, pid=6001)
                for n in range(7, 13):
                    f.step(n)
                return f.save(), 6
            if cat == "false_done":       # record says s10 done, file gone, later steps present
                f.full(); (f.dir / "step-10.json").unlink()
                return f.save(), 10
            if cat == "ok":               # 'ok' failing = the oracle stops calling a good step ok: covered
                return None, None
        seen = []
        missed = []
        for cat in CATS:
            if cat == "ok":
                continue
            f, n = corrupt(cat)
            rc, cats, _ = oracle(f)
            hit = rc == 1 and cats.get("s%d" % n) == cat
            print("category %-12s %s (s%d -> %s, rc=%d)" % (cat, "SEEN" if hit else "MISSED", n,
                                                          cats.get("s%d" % n, "-"), rc))
            (seen if hit else missed).append(cat)
        # 'ok' is the 8th category: it is seen failing when a step that is not ok is refused the word ok —
        # i.e. every corruption above was NOT called ok, and every clean control WAS.
        if not missed and clean_ok:
            seen.append("ok")
        else:
            missed.append("ok")

        # ---- extras: FLAG and CANNOT-READ ----
        f = Fake(root, "extra-flag").full().save()
        (f.dir / "step-5.json.bak").write_bytes((f.dir / "step-5.json").read_bytes())
        (f.dir / "step-5 (1).json").write_bytes((f.dir / "step-5.json").read_bytes())
        _, _, txt = oracle(f)
        flag_ok = "FLAG second-copy step-5.json.bak" in txt.splitlines() and \
                  "FLAG second-copy step-5 (1).json" in txt.splitlines()
        print("extra flag-second-copy %s" % ("SEEN" if flag_ok else "MISSED"))
        f = Fake(root, "extra-noseed").full().save(); (root / "seeds" / f.id).unlink()
        rc, _, txt = oracle(f)
        cr_ok = rc == 4 and txt.startswith("CANNOT-READ")
        print("extra cannot-read %s (rc=%d)" % ("SEEN" if cr_ok else "MISSED", rc))
        if not flag_ok:
            missed.append("extra:flag")
        if not cr_ok:
            missed.append("extra:cannot-read")

        # ---- matrix-ruling cases (2026-10-31). Rows come from Fake.row, so every rowsum is VALID. ----
        def ruling(name, f, want):
            rc, cats, _ = oracle(f)
            got = {s: cats.get(s, "-") for s in want}
            hit = rc == 1 and got == want
            print("ruling %-26s %s (%s, rc=%d)" % (name, "SEEN" if hit else "MISGRADED",
                                                   " ".join("%s->%s" % kv for kv in got.items()), rc))
            if not hit:
                missed.append("ruling:" + name)
        # F-06b: facts edited in a COMMITTED s6 that has a valid done row (its sha no longer matches) -> lost
        f = Fake(root, "rule-f06b").full()
        r = dict(f.recs[5], facts=f.recs[5]["facts"][:4] + ["Edited=101"])
        (f.dir / "step-6.json").write_text(expected.dumps(r) + "\n")
        ruling("F-06b-facts-after-commit", f.save(), {"s6": "lost"})
        # F-14a live skip: s1-s4 committed, s5 never begun, s6 began and failed its pre-flight (no file)
        f = Fake(root, "rule-f14a").full(4)
        f.pid += 1; f.begin(6); f.end(6)
        (f.dir / "s6.rejected").write_text("pre-flight: step-5.json missing\n")
        ruling("F-14a-live-skip", f.save(), {"s5": "skipped", "s6": "stuck"})
        # F-15 guard: record says s12 done (valid row), file missing, nothing later -> false_done, not stuck
        f = Fake(root, "rule-f15").full(); (f.dir / "step-12.json").unlink()
        ruling("F-15-done-but-missing", f.save(), {"s12": "false_done"})

        # ---- short-stop rule (2026-10-31): a run that stops without a stated reason never passes ----
        def short(name, f, want_lines, want_rc):
            rc, cats, _ = oracle(f)
            hit = rc == want_rc and cats == want_lines
            print("short-stop %-14s %s (%s, rc=%d)" % (name, "SEEN" if hit else "MISGRADED",
                                                     " ".join("%s->%s" % kv for kv in cats.items()) or "no-lines", rc))
            if not hit:
                missed.append("short-stop:" + name)
        short("zero-steps", Fake(root, "short-zero").save(), {"s1": "stuck"}, 1)
        short("silent-after-s6", Fake(root, "short-s6").full(6).save(),
              dict({"s%d" % n: "ok" for n in range(1, 7)}, s7="stuck"), 1)
        short("human-pause-s4", Fake(root, "short-pause", answers="").full().save(),
              {"s%d" % n: "ok" for n in range(1, 4)}, 0)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    n_seen = len([c for c in seen if c in CATS])
    if n_seen == 8 and clean_ok and not missed:
        print("SELFTEST 8/8 categories each seen failing")
        return 0
    print("SELFTEST FAIL %d/8 seen; missed: %s; clean controls %s" %
          (n_seen, ",".join(missed) or "-", "all-ok" if clean_ok else "NOT all-ok"))
    return 1


def main(argv):
    if argv[:1] == ["--selftest"]:
        return selftest()
    if len(argv) == 2 and argv[0] == "--run":
        s = scratch()
        return run(pathlib.Path(layout.run_dir(str(s), argv[1])), argv[1], s / "seeds")
    if len(argv) == 2 and argv[0] == "--run-dir":
        d = pathlib.Path(argv[1]).resolve()
        sc = layout.scratch_of(str(d))   # laid out by layout.py -> its scratch's seeds; else the legacy two-up rule
        return run(d, d.name, (pathlib.Path(sc) if sc else d.parent.parent) / "seeds")
    print("usage: truth.py --run <run-id> | --run-dir PATH | --selftest", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

# Rig CONTRACT: the shared interfaces for TR1.2 (truth.py), TR1.3 (checks), TR1.4 (run.sh), TR1.5 (inject.sh)

Written by the BUILD window on 2026-10-31, before those four cards were built, so that builders working in
parallel agree. `canary/SPEC.md` is the step contract. This file is everything around the steps. If this file
and SPEC.md disagree, this file wins on the points it names, and SPEC.md gets fixed.

## 0. Override of SPEC.md

- **CANNOT-READ exits 4, not 2.** That is the shared convention in `shared/emit/verdicts.py` (`CANNOT_READ = 4`;
  exit 2 was recorded there as a past bug). Use that module **in place**, never copy it. Every check that cannot
  read its inputs prints `CANNOT-READ` and exits 4. The verdicts are: check pass = 0, check fail = 1,
  CANNOT-READ = 4.
- **The seed sources must agree.** If both the seed file and `CANARY_SEED` exist and differ, every tool prints
  CANNOT-READ and exits 4. The runner writes the same seed to both. (truth.py and the checks enforce this;
  tested 2026-10-31.)
- **An empty or whitespace-only step file is a FAIL (exit 1), not CANNOT-READ.** The file was read; its
  content is wrong.
- **Checks take an optional 3rd argument**, the path of a candidate file: `checks/<kind>.sh RUN_DIR N [CANDIDATE]`.
  The runner checks its temp file BEFORE renaming it to step-N.json.
- **The actor's settings DENY Read** on `$SCRATCH/seeds/`, `$SCRATCH/plans/` and the rig folder (ruling 4
  note, matrix F-M4). Hiding files outside the run folder is not protection.
- **The actor never inherits the seed.** The runner launches the actor (real or fake) with
  `env -u CANARY_SEED -u SKILL_TESTER_SEED …`. Only code steps, human.py and the checks get `CANARY_SEED`. The
  fake model asserts that `CANARY_SEED` is unset and exits nonzero if it is present, so the leak is caught on
  the fake model too. F-M4 checks the environment as well as file reads.
- **Seed.** The runner draws a random seed for every run by default and stores it at
  `$SCRATCH/seeds/<run-id>`, which is **outside** `$RUN_DIR`. `--seed S` overrides it. Tools that need the seed
  read it from there, or from `CANARY_SEED`. The run-id-derived seed in `expected.seed_for_run` exists only for
  tests.

## 1. Layout

```
SCRATCH = ${SKILL_TESTER_SCRATCH:-~/lifehack-scratch/skill-tester-rig}
$SCRATCH/actor-home/<run-id>/      = ACTOR_HOME: the actor's throwaway HOME, ONE per run (TR2.0b design (b), ruled
                                   2026-11-01). Its .claude/{projects,sessions,session-env}/ hold the actor's transcripts;
                                   the rendered lab settings DENY the actor any Read there (F-M5)
$ACTOR_HOME/.claude/run/skill-tester/<run-id>/   = RUN_DIR (absolute; layout.py is the ONE definition, run_helper.py
                                   rundir/actorhome/scratch-of the shell form). The run dir sits in the actor's OWN
                                   $HOME/.claude because the Harness ingest gate trusts $HOME/.claude (taking $HOME from
                                   the actor's env) and refused a step file in plain scratch. CAVEAT, stated on every
                                   receipt and real-run report: the gate trusts step files only because they sit in the
                                   actor's own $HOME/.claude; in real use the same holds under the real ~/.claude.
                                   No "memory" segment (the gate excludes memory/). Fake and real runs use this layout
                                   identically; they differ only in the binary. Seeds and plans stay OUTSIDE ACTOR_HOME.
    step-N.json                    committed step outputs (temp file + rename; written ONLY after the check passes)
    sN.raw.json                    the raw claude/fake JSON for ai steps (cost, turns, model)
    sN.rejected                    the output of a step whose check failed (kept as evidence, never read as a step)
    sN.answer                      the human answer
    record.tsv                     THE RECORD. Only the runner appends to it (see §2)
    events.log                     the runner's event lines (see §3)
    exec.log                       begin/end lines per step: "<epoch>\tsN\tbegin|end\t<pid>" (the kill injector watches this)
    meta.env                       RUN_ID, CARD, MODEL_ID, FAKE_MODE, START (no seed here); SEAM_GUARD=on|off:<reason>
                                   (TR1.7, written before the snapshot) and SEAM_GUARD_PROFILE=<path of the .sb profile>
    guard-denials.txt              TR1.7: the paths the write guard refused to this run (kernel paths, from the log)
$SCRATCH/seeds/<run-id>            the seed (one integer)
$SCRATCH/judge-cache/<key>         "ACCEPTED <kind>": a cached PASS of the pre-flight judge, DEFAULT checks only, never a
                                   refusal. <key> = run_helper.py judge-key: sha256 over kind, python version, and the
                                   sha256 of the check, checks/{_check.py,_lib.sh,selftest.sh}, every checks/fixtures/ file,
                                   canary/{expected.py,card.txt,prompts/*}, shared/emit/verdicts.py. Any byte changed = miss.
                                   Hits/misses are logged to RUN_DIR/judge.log, never events.log
$SCRATCH/plans/<run-id>/expected.tsv   the answer key, written BEFORE the run (TR1.5)
$SCRATCH/plans/<run-id>/faults.tsv     one line appended per planting (TR1.5)
```

## 2. record.tsv: one row per step event, appended only by the runner, only after the check passes

```
<run-id>\t<sN>\t<status>\t<epoch>\t<sha256 of step-N.json>\t<model-id or ->\t<rowsum>
```

- **status:** `done` (the check passed and the file was committed), `skipped-done` (on resume, the step was
  already done and verified, so it was not re-run), `waiting` (a human step with no answer yet), or
  `halted` (a human answered `no`).
- **rowsum:** the first 12 hex characters of the sha256 of the six preceding fields joined by single tabs, with
  NO trailing newline in the hashed string. truth.py implements it this way, and the runner must match it byte
  for byte. A row with
  the wrong field count, a bad rowsum, or no final newline is **MALFORMED**. On resume the runner REFUSES a
  malformed row: it never trusts the row, and it emits `RECORD-REFUSED sN row=<line-no>` (see §3). The step
  is then re-derived from disk, and re-run if its check does not pass.
- A row whose run-id differs from this run's is refused: `RECORD-FOREIGN row=<line-no>`.
- Rows the runner did not write cannot be told apart by their content alone, which is why the rowsum exists.
  A model-written row (F-M1) gets refused as MALFORMED unless it forges the rowsum.

## 3. The grader's output: exact lines

The grader for a run is `events.log` (written by the runner) plus the stdout of `truth.py --run <id>`. An
answer-key string in `expected.tsv` must **equal one whole line** of either one. Exact string equality; no
regex, no substring. Fixed line forms:

```
events.log (runner):
  CHECK-FAIL sN <cat>           a check exited 1; <cat> ∈ empty parse keys step token value facts answer
                                (the check prints its first stdout line as `FAIL <cat>: <text>`; the runner copies <cat>).
                                ALSO `CHECK-FAIL sN input-missing`: the runner's PRE-FLIGHT, before launching step N,
                                found step-(N-1).json missing or not committed (F-14 live, ruled 2026-10-31)
                                The output is kept as sN.rejected; the run stops, exit 1
  RESUME sN gap_days=<d>        on resume, sN was the first step to run; <d> = fake-clock days since the last record row
  SELFTEST-REFUSED <check>      checks/selftest.sh --judge refused a check the run was about to use, judged BEFORE s1:
                                the default checks/ AND any planted CHECKS_DIR (TR1.4 amendment). The run stops, exit 1,
                                no step begun. RIG_TEST=1 runs on past a refused PLANTED check only, never a refused
                                default check (a broken default check is a rig defect, not a test path)
  CANNOT-READ sN                a check exited 4, or was missing or crashed (a rig defect; the run stops, exit 1)
                                ALSO `CANNOT-READ sN denials`: the step's result JSON had a malformed permission_denials
                                list (TR2.0b); the run is tainted like an ACTOR-*-DENIED line
  WATCHDOG sN                   the model call was killed on timeout (exit 124)
  MODEL-FAIL sN rc=<rc>         the model binary failed (e.g. rc=127)
  RECORD-REFUSED sN row=<k>     a malformed record row was refused on resume
  RECORD-FOREIGN row=<k>        a record row with a foreign run-id was refused
  RERUN sN                      on resume, a step with no valid record row was re-run
  VERSION-CHANGE sN <old> -> <new>   the model id differs from the run's earlier rows (recorded, the run continues)
  PATH-REFUSED <path>           an output path outside $SCRATCH (e.g. Drive) was refused. Written to the CANONICAL
                                run dir's events.log (§1, layout.py), since the refused dir is never created
  WAITING sN                    a human step paused (exit 70)
  RIG-TEST ON                   FIRST line of events.log whenever RIG_TEST=1 was set for the invocation (also
                                RIG_TEST=1 in meta.env). A run with this line is a TEST-PATH run: it can never count as
                                a clean control or a ladder/crucible result; bite/ladder/crucible refuse it (ruled 2026-10-31)
  BUDGET-REFUSED sN             budget.sh refused the call (exit 75)
  SEAM-LEAK <op> <path>         <op> ∈ CHANGED ADDED REMOVED. seam.sh verify found <path> (seam scope: the state root,
                                every SKILL.md under a skill root, hooks.json, and the notes stand-in) different after
                                the run. COUNTS: exit becomes 1 if it was 0 or 70; on a control it is a false positive.
                                The DEFAULT class of every changed path; only §3a can make it SEAM-AMBIENT
  SEAM-AMBIENT <op> <path>      the same change, proven not writable by any process of this run (§3a). RECORDED, not a
                                fault: exit unchanged; bite/ladder/crucible exclude exactly this prefix from the control
                                false-positive rule and print the count (`ambient <n>`)
  SEAM-DENIED <path>            the write guard (§3a) refused a write to <path> (the kernel's resolved path) by a process
                                of this run. COUNTS like SEAM-LEAK although nothing changed on disk: the attempt is the
                                leak. Exit becomes 1 if it was 0 or 70
  SEAM-DENIED-RULED <path>      (TR2.0b ruling, claudeops-a0 2026-11-01) a denial whose path fully matches a regex in
                                guard-ruled-denies.txt (the cross-session socket /private/tmp/cc-socks/<pid>.sock, the
                                fswatch probe). The write STAYS DENIED (the file allows nothing); it is named and does
                                NOT change the exit. Adding a line to that file is a ruling
  ACTOR-READ-DENIED sN <path>   (TR2.0b, F-M4/F-M5) the actor at step N asked to Read <path> and Claude Code refused it
                                by the lab settings deny list: one line per `permission_denials` entry with
                                tool_name Read in the step's result JSON (<path> = its tool_input.file_path, verbatim).
                                Logged BEFORE the step's check. TAINTS the run: exit becomes 1 if it was 0 or 70
  ACTOR-TOOL-DENIED sN <tool>   the same for any other tool the actor was refused (e.g. Bash, Write); taints the run
  SEAM-CANNOT-READ snapshot     the pre-run snapshot failed; the run stops before s1, exit 1
  SEAM-CANNOT-READ rc=<rc>      seam.sh verify could not compare (4 snapshot missing/empty, 3 a file could not be hashed);
                                exit becomes 1 if it was 0 or 70
  SEAM-CANNOT-READ denials      the guard was on but its denial log could not be read through the end-of-run barrier
                                (§3a rule 3); exit becomes 1 if it was 0 or 70, and NO change is SEAM-AMBIENT
  GUARD-PROBE-FAILED <what>     the guard's probe (§3a rule 2) misbehaved: a write it must refuse landed, or a write it
                                must allow was refused, or a here-document failed. The run stops before the snapshot,
                                exit 1
truth.py (oracle), one per step and then a totals line:
  sN <category>                 category ∈ ok silent_wrong double_ran stuck lost skipped out_of_order false_done
  TOTAL ok=.. silent_wrong=.. double_ran=.. stuck=.. lost=.. skipped=.. out_of_order=.. false_done=..
  FLAG second-copy <relpath>    an extra copy of a step file is lying in RUN_DIR (e.g. step-5.json.bak, step-5 (1).json)
grader-only key (NOT an output line; §3c):
  ORACLE-EXIT-NONZERO           satisfied only when truth.py exited 1 (F-20: a silent short stop, graded by the oracle alone)
```

Steps the run never reached (after a legitimate halt or stop) print no `sN` line and are not counted in TOTAL.

### 3a. The CONCURRENT-WRITER RULE (TR1.7; designed in CONTRACT-TR2.0-draft.md, built and proven at TR1.7)

```
Every path seam.sh reports is SEAM-LEAK unless ALL of these hold, in which case it is SEAM-AMBIENT:
  1. GUARD ON FOR THE WHOLE RUN. run.sh re-executed itself under `sandbox-exec -f <profile>` (guard.sh; the profile
     and the reason for every allowance are in guard.sh's header) BEFORE the run dir, the lock and the snapshot, so
     every process of the run (runner, budget.sh, fake or real actor, code steps, checks, seam.sh) inherits it.
     Profile: allow default; deny file-write* everywhere; allow file-write* only to the CANONICAL scratch
     ~/lifehack-scratch/skill-tester-rig and the minimal system needs; then, AFTER that allow (the last matching
     rule wins), deny file-write* to the notes stand-in, to the rig's own folder, and to every seam root. Every
     deny carries a per-run TAG (`with message`), which the kernel appends to its log line.
     meta.env: SEAM_GUARD=on, or SEAM_GUARD=off:<reason> (off:sandbox-unavailable; off:disabled-by-env, honoured only
     with --fake). With the guard off, rule 1 fails for every path: every change stays SEAM-LEAK.
  2. GUARD SEEN FAILING FIRST (ruling 12). Inside the guard, before the snapshot, run.sh must see: a write to the
     run dir LAND; a write to <stand-in>/.seam-guard-probe-<tag> REFUSED; a write to
     ~/lifehack-scratch/.seam-guard-probe-<tag> (outside the allow list; never the real notes folder) REFUSED; a
     here-document work. Anything else: GUARD-PROBE-FAILED <what>, exit 1, the run does not start.
  3. NO DENIAL FOR THAT PATH, READ THROUGH A BARRIER. At finish, run.sh attempts one more refused write (the barrier,
     ~/lifehack-scratch/.seam-guard-barrier-<tag>) and reads the unified log (`log show`, sender Sandbox, message
     carries <tag>) until the barrier's denial appears: proof the log is readable and flushed past every earlier
     denial of this run. Every denied path except the three probe/barrier paths prints SEAM-DENIED <path>. A path
     with a denial is never SEAM-AMBIENT. Barrier not seen within GUARD_LOG_WAIT s (default 15):
     SEAM-CANNOT-READ denials, and rule 3 fails for every path.
  4. Nothing else exonerates a path: not its location, mtime, the actor's --allowedTools, a known-writers list or the
     sentinel. (The sentinel is the TEST of this rule: bite --sentinel cross-checks every SEAM-AMBIENT path against
     the sentinel's own write log, and counts an ambient path the sentinel did not write as a false positive.)
```

### 3b. STAND-IN ISOLATION (2026-10-31)

```
The notes stand-in is a TREE: $CANON/notes-standin/. Every bite (and every selftest that runs a sentinel or a
seam check) uses its OWN subtree, $CANON/notes-standin/<bite-id>/, exported as SEAM_STANDIN to all its runs and to
its sentinel. Rules:
  1. Only that bite's own sentinel writes its subtree; its sentinel log lives in the bite's scratch dir
     (<bite scratch>/sentinel.log), never a shared path.
  2. A run's seam snapshot covers ONLY its own stand-in subtree (SEAM_STANDIN) plus the real roots. Other bites'
     subtrees are not seam scope for it.
  3. The guard profile denies writes to the WHOLE notes-standin/ tree (and to SEAM_STANDIN as an extra root if a
     test points it elsewhere): no run may write any bite's stand-in.
  4. Own subtree: a SEAM-AMBIENT path there that is not in the bite's own sentinel log is SUSPICIOUS-AMBIENT and
     counts as a false positive (unvouched ambient = false positive, unchanged).
  5. A SEAM-AMBIENT path inside notes-standin/ but OUTSIDE the bite's own subtree is ALWAYS SUSPICIOUS-AMBIENT (a
     false positive): another bite's sentinel can never make a run look clean.
  6. A bite removes its own subtree when it ends; it never touches another's.
```

### 3c. Oracle-only keys (F-20, 2026-10-31)

An answer key may hold the literal `ORACLE-EXIT-NONZERO`. It is not a line of any output: the grader (bite.sh)
counts it caught only when `truth.py --run <id>` exited 1 (CANNOT-READ 4 does not satisfy it). F-20 (the runner
stops short silently, `RIG_TEST=1 run.sh --test-exit-after K`, exit 0, no event) is graded by the oracle ALONE:
`s<K+1> stuck` + `ORACLE-EXIT-NONZERO` (+ the TOTAL line).

## 4. Oracle category meanings (truth.py)

- `ok`: the disk file equals the expected record (parsed compare), and the step's position in exec.log is in order.
- `silent_wrong`: the file exists, is not equal to the expected record, and the record says done (a wrong output got committed).
- `lost`: like silent_wrong, but only the facts differ (dropped, edited or reordered). Takes precedence over silent_wrong.
- `double_ran`: exec.log shows more than one `begin` for sN that produced a committed write, and the step is NOT idempotent-identical. A re-run that wrote byte-identical output after a kill is NOT double_ran (that is the designed recovery). Make this precise, and document it in truth.py.
- `stuck`: the run stopped at this step without a committed file (check fail, watchdog, model failure).
- `skipped`: the file is missing (or never begun in exec.log) while a LATER step is committed.
- `out_of_order`: exec.log shows sN beginning before s(N-1) ended.
- `false_done`: record.tsv says done or skipped-done for sN, but the disk file is missing or does not match.

Settled by TR1.2 (2026-10-31; truth.py is the reference):
- **silent_wrong vs false_done** for a wrong file whose record says done: if the record's sha equals the wrong
  file's sha, it is `silent_wrong` (a wrong output was committed); otherwise it is `false_done`. A wrong file
  with NO record row is still `silent_wrong`. Any step file after a `no` halt or an off-menu answer is also
  `silent_wrong`.
- **Order is decided by exec.log LINE order**, never by timestamps (fake steps begin and end in the same second).
- **double_ran:** a "write" is a valid `done` row, which carries a sha. The step is double_ran when exec.log has
  2 or more `begin` lines for it AND either (a) the writes carry 2 or more distinct shas, or (b) 2 or more
  attempts completed (a begin and an end with the same pid) and some write's sha differs from the disk file.
  A killed attempt followed by an identical re-run is not double_ran.
- A missing exec.log means `CANNOT-READ` (exit 4), because order cannot be checked without it.
- A human step that is still waiting prints no line. An off-menu answer prints `stuck`.
- `FLAG` lines do not change truth.py's exit code; the bite and grader read them. Leftover temp files from a
  killed write are reported as `FLAG second-copy`.
- The seed file wins over the `CANARY_SEED` env var when both exist.
- **Short stop (2026-10-31):** a run whose last reached step is below the expected final step, with no human
  pause and no non-ok category on its last reached step, prints `s<k> stuck` for the first unreached step
  (k=1 for zero steps) and exits 1. A run that stops without a stated reason never passes.

## 5. The fake model (TR1.4 owns it; TR1.5 relies on it)

`run.sh --fake <mode>` sets `CLAUDE_BIN` to `stress/fake-claude.sh` (copied with provenance). Modes:
`good|empty|almost|garbage|hang|exit127|lossy`. `FAKE_MODE_STEP=N` applies the mode at step N only, with good
everywhere else. `good` replies with `expected.py next` output wrapped in claude's `--output-format json` shape
(`result`, `total_cost_usd`: 0, `num_turns`: 1, `model`). The fake clock is `STRESS_TODAY`, never `date`.
`FAKE_MODEL_ID` sets the model field (the version-change injector uses it).

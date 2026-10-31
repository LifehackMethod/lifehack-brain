# CONTRACT TR2.0 draft: seam result lines + the CONCURRENT-WRITER RULE

> **STATUS 2026-10-31: BUILT at TR1.7** (moved from TR2.0). The live text is CONTRACT.md §3 + §3a; this draft is kept
> as the design record. Where the build differs, and why:
> (1) the probe's denied writes go to the notes STAND-IN and to `~/lifehack-scratch/` (outside the allow list), NOT the
>     state root: a broken guard would otherwise have planted a probe file in the REAL notes folder;
> (2) `log show` refuses to run inside a sandbox ("Cannot run while sandboxed"), so run.sh is split: an unguarded
>     PARENT starts the guarded CHILD (the whole run), then does the barrier, the denial read, seam verify and the
>     classification;
> (3) denials are attributed by a per-run TAG carried in every deny rule (`with message`), not by pid;
> (4) the barrier: a refused write through the same profile after the child's tree has exited, polled until the log
>     shows it.

DRAFT, 2026-10-31, staging only. Nothing here is built. Ruling 5 is FIXED and unchanged: a seam snapshot before and
after every run, every changed path named. This draft adds (1) the exact seam line forms for CONTRACT §3 and
(2) a rule for telling a rig leak from another writer's change. The rule is additive: it never removes a path
from the snapshot and never narrows the snapshot's scope.

## What run.sh emits today (read from staging run.sh `finish()` and the snapshot call)

- `SEAM-LEAK CHANGED <path>`, `SEAM-LEAK ADDED <path>`, `SEAM-LEAK REMOVED <path>`: one line per path from
  `seam.sh verify` exit 1 (seam.sh's tab is replaced by one space; `<path>` is absolute and may contain spaces).
  The run's exit becomes 1 if it was 0 or 70.
- `SEAM-CANNOT-READ snapshot`: the pre-run snapshot failed (seam.sh exit 3). The run stops before s1, exit 1.
- `SEAM-CANNOT-READ rc=<rc>`: verify could not compare (rc 4 = snapshot missing/empty, rc 3 = a file could not
  be hashed). The run's exit becomes 1 if it was 0 or 70.

So the form is `SEAM-LEAK <op> <path>`, not `SEAM-LEAK <path>`; this draft keeps the form that already exists.

## Text to add to CONTRACT §3 (events.log block), verbatim

```
  SEAM-LEAK <op> <path>         <op> ∈ CHANGED ADDED REMOVED. seam.sh verify found <path> (real state: state/, a SKILL.md
                                under a skill root, hooks.json) different after the run. COUNTS: the run is not clean; its
                                exit becomes 1 if it was 0 or 70; on a control run it is a false positive. This is the
                                DEFAULT for every changed path; only the CONCURRENT-WRITER RULE (§3a) may turn it into
                                SEAM-AMBIENT, and only with the proof §3a names
  SEAM-AMBIENT <op> <path>      the same change, proven NOT writable by any process of this run (§3a). RECORDED, not a
                                fault: exit code unchanged; bite/ladder/crucible exclude exactly this prefix from the
                                control false-positive rule and print the count beside fp (`ambient <n>`)
  SEAM-DENIED <path>            the write guard (§3a) refused a write to <path> by a process of this run (the actor,
                                its hooks, a code step, the runner). COUNTS like SEAM-LEAK, even though nothing changed
                                on disk: the attempt is the leak. Exit becomes 1 if it was 0 or 70
  SEAM-CANNOT-READ snapshot     the pre-run snapshot failed; the run stops before s1, exit 1
  SEAM-CANNOT-READ rc=<rc>      verify could not compare (4 = snapshot missing/empty, 3 = a file could not be hashed);
                                exit becomes 1 if it was 0 or 70
  SEAM-CANNOT-READ denials      the guard was on but its denial log could not be read for the run window; the run cannot
                                be certified, exit becomes 1 if it was 0 or 70, and NO change is classified SEAM-AMBIENT
```

meta.env gains one line, written before the snapshot: `SEAM_GUARD=on` or `SEAM_GUARD=off:<reason>`
(e.g. `off:probe-write-succeeded`, `off:sandbox-unavailable`). It is not an events.log line, so an unguarded
fake-model control is not a false positive by itself; but with `SEAM_GUARD=off` there is no SEAM-AMBIENT.

## Text to add to CONTRACT as §3a: the CONCURRENT-WRITER RULE

```
§3a CONCURRENT-WRITER RULE. Every path seam.sh reports is a SEAM-LEAK unless ALL of these hold, in which case it is
SEAM-AMBIENT:
  1. GUARD ON FOR THE WHOLE WINDOW. run.sh re-executed itself under an OS-enforced write guard (macOS sandbox-exec
     profile: deny file-write* on the state root, on every skill root as a whole directory, and on hooks.json) BEFORE
     the snapshot, and every process of the run (runner, budget.sh, the actor `claude`, any hook the actor's session
     runs, code steps, checks) descends from that guarded process, so the deny is inherited, not configured per tool.
  2. GUARD SEEN FAILING FIRST (ruling 12). Inside the guard, before the snapshot, run.sh tries to create
     `<state-root>/.seam-guard-probe-<run-id>` and must see it refused. If the probe write succeeds, run.sh deletes
     it, writes SEAM_GUARD=off:probe-write-succeeded, and §3a is OFF for the run (every change stays SEAM-LEAK).
  3. NO DENIAL FOR THAT PATH. The guard's denial log for the run window (unified log, sandbox deny lines, filtered to
     pids of this run's process group) is read at verify. Each denied path prints SEAM-DENIED <path>.
     The rule-2 probe path is the ONE exempt path, and only for the single denial run.sh itself caused before the
     snapshot; a second denial on it counts. A path that has a
     denial is never SEAM-AMBIENT. If the log cannot be read: SEAM-CANNOT-READ denials, and rule 3 fails for every path.
  4. Nothing else exonerates a path: not its location (state/ vs a skill root), not its mtime, not the actor's
     --allowedTools Read, not the runner "only writing to $SCRATCH", not a known-writers list, not a sentinel.
     These may be printed in seam.log as context; they never change a line's class.
```

## Why this option (the evidence for and against each one)

| evidence | what it can prove | why it cannot classify a path alone |
|---|---|---|
| path under a skill root vs state/ | nothing about who wrote it | the rig could leak into either; skill roots are not safer |
| file mtime vs run begin/end | only that a change happened inside or outside the window | every rig process is alive for the whole snapshot→verify window, so "inside" fits the rig and others equally; mtime is forgeable (`cp -p`, `touch`) and Drive sync stamps the REMOTE time |
| reachability by configuration (actor has Read only; runner writes only $SCRATCH) | what the rig is configured to do | it assumes the conclusion the seam exists to test; and it is false: the actor is a real Claude Code session that runs the user's hooks and plugins, which run shell and can write state while `--allowedTools Read` holds |
| a sentinel snapshotting the same tree over the same window, running no rig code | the ambient change RATE in a no-rig window | the sentinel watches the same filesystem, so a real rig leak shows up in its diff too; it cannot attribute any single path. Its use is a separate measurement: paired no-rig windows of equal length beside a real-model bite, reported as the ambient rate |
| OS-enforced write deny, inherited by the whole run, probed first | the run's processes COULD NOT write the path in that window (enforced by the kernel, not by the rig's own config), and any attempt is logged by pid | needs sandbox-exec to work around headless `claude -p` (unproven; see below); when it does not, the rule switches itself off and everything stays SEAM-LEAK |

RECOMMENDATION: the inherited OS write guard (rules 1–3). It is the only option that turns "the rig could not have
written this" from a claim into a property the kernel enforces, and it is fail-safe in the right direction:
- It can prove: a change to a guarded path during a guarded window came from outside the run's process tree, and
  any write attempt by the run (hooks included) is caught by name as SEAM-DENIED.
- It cannot prove: who the other writer was; that a change to a path OUTSIDE the guard's profile is ambient (so the
  profile must cover the full seam scope, whole skill roots, not only SKILL.md); anything when the guard is off,
  the probe write succeeds, or the denial log is unreadable. In all of those cases every change is SEAM-LEAK.
- It never lets a real leak pass as ambient: a successful rig write is impossible under a working guard (the probe
  proves it is working), a blocked rig write is SEAM-DENIED (counts), and a broken guard disables the AMBIENT class.

## Open before building (TR2.0, after the freeze lifts)

1. PROBE: does `sandbox-exec -f <profile> claude -p ...` run headless at all (nested-sandbox refusal, Claude Code's
   own sandboxing, keychain/OAuth access)? If not, §3a is OFF and real-model controls will show ambient writes as
   false positives; the fallback then is to schedule rung-2 controls in quiet windows and report the sentinel's
   ambient rate beside them, NOT to reclassify.
2. PROBE: are sandbox denials readable without root (`log show --predicate 'sender == "Sandbox"'`), with pids?
3. Profile allow-list: claude must still write ~/.claude session files, ~/.claude.json, caches and $SCRATCH;
   only the seam scope is denied.
4. bite.sh/ladder.sh: exclude exactly `SEAM-AMBIENT ` lines from the control false-positive rule, print `ambient <n>`.
5. A selftest that fails first: a guarded fake run whose code step writes into the fake state root must give
   SEAM-DENIED (not AMBIENT); a background writer outside the run's tree must give SEAM-AMBIENT; a guard whose probe
   write succeeds must leave that same background write as SEAM-LEAK.

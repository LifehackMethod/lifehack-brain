---
element: hospital
title: "hospital — element detail (ground/base altitude)"
subsystem: hospital
altitude: base
record_type: organism-element
maturity_label: LIVE·gap
gap_disposition: by-design
gap_disposition_note: "authored 2026-08-04, AFTER the 2026-07-28 class-level ruling batch — Hospital did not exist then, so this is NOT one of that day's rulings. ★ RAISED PARTIAL→LIVE 2026-08-04 (T15.30), EARNED FROM CODE not hand-typed: the two gaps this note previously cited are both closed — the deny-hook exists and is registered (system/hooks/guard_findings_write.sh, settings.json:293), and detector coverage is complete. Machine check: every system/tools/*-health.py plus organism/organism-health.py now calls emit_finding; the ONLY file that does not is backlog-health.py, a CUT approved by the operator because backlog_groom.py:290 already emits findings off the identical build_report() and the health script is merely its tile renderer. All 13 producers resolve a cadence in findings_deadman.load_producer_roster(). ✅ CORRECTED 2026-08-05 — THE VARIABLE-PATH BYPASS IS CLOSED AND THIS NOTE WAS STILL CLAIMING IT OPEN. This note used to read: 'THE ·gap IS NOT COSMETIC — guard_findings_write.sh matches the LITERAL string state/findings/, so a path held in a shell VARIABLE evades every one of its seven patterns... still open behind one line of indirection. Unfixed deliberately: a hook edit needs the SOP receipt and the operator's sign-off.' That was true when written (T15.32, found at the T15.30 review) and was FIXED later the same day: guard_findings_write.sh:88-96 now imports system/tools/hook_path_resolve.py and matches the RESOLVED command, exactly as the ruling demanded ('a path-matching guard cannot be completed by adding an eighth regex'). VERIFIED LIVE 2026-08-05 by firing the REGISTERED guard with a variable-path payload: rc=2, blocked. 🔴 CORRECTED 2026-08-23 — THAT VERIFICATION DID NOT HAPPEN IN THIS REPO, AND THE BYPASS WAS OPEN HERE UNTIL TODAY. The struck claim above is kept, not deleted, because the record keeps its wrong turns. It was carried over verbatim from the DONOR clone (`~/claudeops-config`) and describes an event in a DIFFERENT repository: `guard_findings_write.sh` was first ported here on 2026-08-14 (`50847d3`/`8d1dd53`) and this organism layer on 2026-08-15 (`688caf3`) — both AFTER the 2026-08-05 date it asserts, so no such verification could have been run here. ⚠ The resolver it depends on, `system/tools/hook_path_resolve.py`, was NEVER COMMITTED: absent from HEAD, from `upstream/main`, and from every branch's history. It sat untracked on the operator's disk, so the guard held on HIS machine alone while every clone had the bypass OPEN and this note said CLOSED. ⭐ MEASURED 2026-08-23 on a clean worktree of `upstream/main`, same guard, same store path: literal-path → exit 2 (blocked) · variable-path → **exit 0 (ALLOWED)**. Closed for real by commit `cfc80cc`, which committed the resolver; re-measured after: variable-path → exit 2. ⭐ THE CLASS, not the instance: a sweep found **16** dated verification claims across the organism layer and sops that predate their own file's port date, plus 4 undated and 3 SOP files never committed here at all. The honest pattern already exists in this repo — see `system/security-canon.md:466`'s `⛔ Migration note, 2026-08-15` banner. Copy it. The resolver degrades loudly rather than denying if it is ever missing, so a resolver outage cannot black out every tool call. ★ THE LESSON IS THIS PROJECT'S OWN SIGNATURE ONE, AGAIN: a defect note left standing after the defect was fixed sends the next session to re-fix working code — the exact inverse of T15.26/T15.27, and caught here only because T18.6b re-read the guard before extending it. STILL GENUINELY OPEN: the guard is watched firing on the primary machine ONLY (the second machine dark since 2026-07-04) — T15.31."
generated_from:
  - system/tools/emit_finding.py
  - system/tools/findings_reader.py
  - system/tools/findings_deadman.py
  - system/tools/health_line.py
  - system/tools/health_invariants.py
  - system/tools/backlog_groom.py
  - system/tools/guard-fire-test-run.sh
  - system/tools/guard_fire_test_record.py
  - system/tools/health-deadman-check.sh
  - system/tools/fault_proposer.py
  - system/tools/planning-health.py
  - system/tools/clair-health.py
  - system/tools/sentinel-health.py
  - system/tools/dobby-health.py
  - system/tools/security-health.py
  - system/tools/marc-health.py
  - system/tools/deryl-books-health.py
  - system/tools/system-health.py
  - system/tools/organism/organism-health.py
  - system/hooks/guard_findings_write.sh
  - system/tools/fault-proposer-run.sh
  - system/tools/fault_ledger.py
  - system/hooks/session_context_loader.sh (line 110 — health_line.py invocation)
  - system/reference/settings.json (line 347 — session_context_loader.sh SessionStart registration)
  - system/pulse-config.md (line 298 — system-health slot; line 325 — fault-proposer slot; line 342 — guard-fire-test slot; line 367 — backlog-health slot; line 425 — health-deadman crontab line)
created_at: 2026-08-04
updated_at: 2026-08-04
status: draft
authority: user
---

# hospital — element detail

> ⛔⛔ **PORT BANNER — WHAT THIS ELEMENT NAMES THAT IS NOT IN THIS REPOSITORY.** The description below
> is faithful to the donor system and is left exactly as written. These lines record what happened to
> each named file AT THIS DESTINATION, and each one holds for every mention of that file anywhere below.
>
> - ⛔ `state/health.jsonl` and `state/status/backlog.json` — runtime-generated, created on first run, never committed. These are an append log and a status tile that a run writes into the operator's own data area; there is no committed copy of either in any repository, donor or destination.
> - ⛔ `system/reference/settings.json` — not shipped. The donor's hook registry was never ported: this repository's `.claude/settings.json` was authored from scratch against its own, smaller hook inventory, so the donor's line numbers cited below index a file that does not exist here. Read the registrations from `.claude/settings.json` instead.
> - ⛔ `system/tools/machine_token.py` — excluded from the migration: two-machine. This product is one machine by design, and the shared derivation collapses to a local constant — see the note in `system/tools/fault_ledger.py` and `system/tools/emit_recommendation.py`, which both say so at the point of use.
> - ⛔ `system/tools/clair-health.py`, `system/tools/deryl-books-health.py`, `system/tools/dobby-health.py` and `system/tools/marc-health.py` — excluded from the migration: personal-desk. These four are the per-desk detectors for desks on the closed exclusion list. Their four non-desk siblings named in the same sentences DID land and resolve here — `system/tools/system-health.py`, `system/tools/planning-health.py`, `system/tools/security-health.py`, `system/tools/sentinel-health.py` — so the "8 of roughly 12 producers" count below is a donor-side count, not a destination one.

> ⚖ **BOUNDARY CORRECTED 2026-08-05 (T18.8) — `fault_proposer.py` IS NO LONGER HOSPITAL'S. READ THIS
> BEFORE THE COMPONENT TABLE BELOW.** The operator ruled that the grading/proposing layer belongs to the
> **EFFICIENCY** subsystem, not this one. The reasoning is Hospital's own stated boundary, turned on
> itself: **this element says "Hospital DETECTS and RANKS — it never REMEDIATES," and `fault_proposer.py`
> grades an altitude, cites evidence, and proposes *"stop fixing X and fix what keeps breaking it."*
> RECOMMENDING IS NOT DETECTING.** The three roles are now disjoint:
>
> **HOSPITAL detects and ranks · EFFICIENCY reads across and recommends · THE HUMAN decides and acts.**
>
> ⚠ **NOTHING MOVED ON DISK.** `system/tools/fault_proposer.py`, its runner, and its daily Pulse slot are
> deliberately unchanged — relocating the file would be a large blast radius bought for nothing, and
> `architecture-library.md` §6·1 asks whether value SCALES with the architecture (the "fewer moving parts" phrasing was retired 2026-08-06). Part count here is unchanged; only
> the OWNERSHIP moved. It stays in `generated_from` below because this element was genuinely authored
> from it and still describes the seam it sits on — but **it is documented BY Efficiency, not by
> Hospital.** The Efficiency element (plan `§18.11`, element #51) claims it once Efficiency's own code
> exists — that element is authored FROM CODE THAT EXISTS, never from a design, so it is deliberately
> not written yet. **Until it is, this banner is the pointer.**

> **Altitude = BASE (ground / street view).** Full mechanics + honest enforcement map + all interop
> seams. The MIDDLE index (`system/organism/manual.md`) does not yet carry a pointer here — this
> element is written; the manual entry is a SEPARATE task (T15.25), not yet done as of this write.
> The **live artifacts** (`system/tools/emit_finding.py` + `findings_reader.py` + `findings_deadman.py`
> + `health_line.py` + `fault_proposer.py` + `fault_ledger.py`) are the fourth level — the executable
> runtime ground truth. This entry is the UNDERSTANDING layer.
>
> **LADDER: ELEMENT (full mechanics). up → ~~manual#hospital [NOT YET WRITTEN]~~ manual#hospital ⚠ CORRECTED 2026-08-24: the section exists and is substantive (`system/organism/manual.md` ~L1214–1224, confirmed this session) ; ground truth →
> system/tools/emit_finding.py + findings_reader.py + findings_deadman.py + health_line.py +
> fault_proposer.py + fault_ledger.py**
>
> **One-line:** the ONE validated store every detector's finding lands in — `emit_finding.py` writes
> it, `findings_reader.py` + `findings_deadman.py` read the honest union (including silence itself),
> and `health_line.py` surfaces the ranked top of it at every session start; Hospital DETECTS and
> RANKS — it never REMEDIATES. **Grading an altitude and PROPOSING a fix is Efficiency's job, through
> `fault_proposer.py`** *(re-attributed 2026-08-05, T18.8 — see the boundary banner at the top; this
> line used to claim that grader as Hospital's, which contradicted the very next clause).*
>
> **Step grammar:** `actor → port/tool → store → gate`
> Enforcement tags: `[hook]` (a real guard fires) · `[script]` (deterministic code path, always runs) ·
> `[honor]` (prose instruction only, no mechanical enforcement) · `[human]` (deliberate HITL pause).

---

## AUTHORED   (human-only)

### WHY HOSPITAL EXISTS (the founding problem)

`fault_proposer.py`'s own docstring states the measured finding that started this build (2026-07-28):
across all 11 detectors this system ran at the time (Pulse's circuit breaker, system-health,
health_invariants, notify-governor/send, emit_status, the 8 per-desk `*-health.py`, organism-health,
label_checker, generated_from_check, archivist + sentinel) **every failure signal terminated at a
human eyeball** — a phone buzz or a Helm render. Nothing read a failure and then decided anything.
`state/health.jsonl` had been appended to for weeks and never once read. The detectors were never the
gap; the wire from detector to JUDGMENT was. Hospital is that wire: ONE validated finding contract,
ONE store, ONE union reader, ONE dead-man's switch, ONE grading layer, ONE session-start consumer.

### ARCHITECTURE OVERVIEW

| Component | File | Role |
|---|---|---|
| **The writer** | `emit_finding.py` | The ONE validating writer every detector goes through — CLI + Python import, same validator either way |
| **The store** | `state/findings/<producer>.<machine>.jsonl` (Drive spine) | Append-only, sharded per (producer, machine) — no shared file, no local fallback |
| **The union reader** | `findings_reader.py` | Globs every shard, reports rows + `shards_expected`/`shards_read`/`shards_missing`/`bad_lines`/`degraded` |
| **The dead-man's switch** | `findings_deadman.py` | Composes the union reader, derives synthetic `STALE` rows for producers past cadence — never writes to disk |
| **The session-start consumer** | `health_line.py` | THE only wired reader today — ranks, caps, prints a line at every session start via `session_context_loader.sh` |
| **The grading/proposing layer** ⚖ **— EFFICIENCY'S, NOT HOSPITAL'S (T18.8, 2026-08-05)** | `fault_proposer.py` + `fault-proposer-run.sh` | Reads `fault_ledger`'s recurrence data, grades INSTANCE/SUBSYSTEM/ORGANISM/DECISION, refuses to emit without citable evidence. **Listed here as the SEAM Hospital hands off to — it is documented by the Efficiency element (`§18.11`), not by this one.** Grading + proposing is recommending, and Hospital never remediates. |
| **The lifecycle store** | `fault_ledger.py` | `~/.local/state/lifehack/faults.json` — first_seen/last_seen/escalation, now keyed by BOTH legacy `job\|state` AND `fp:<fingerprint>` |
| **Converted detectors** | `health_invariants.py` · `backlog_groom.py` · `guard-fire-test-run.sh` · `health-deadman-check.sh` · **+ the nine `*-health` detectors** (`planning` · `clair` · `sentinel` · `dobby` · `security` · `marc` · `deryl-books` · `system` · `organism/organism`) | **THIRTEEN** producers now emit through `emit_finding()`, all resolving a cadence in `findings_deadman.PRODUCER_JOB`. *(Was FOUR until T15.30, 2026-08-04.)* The one `*-health.py` that does NOT emit is `backlog-health.py` — an approved CUT, because `backlog_groom.py:290` already emits off the identical `build_report()` and the health script is only its tile renderer. ⚠ **Every conversion is ADDITIVE: each detector's existing `emit_status` tile is written exactly as before** — Helm reads `state/status/` only and has no `state/findings/` reader, so the two surfaces never met. |

---

### THE WRITE CONTRACT (`emit_finding.py`)

**`scanned_n` has NO default — the single most important design choice in this module.** Omitting it
is a `TypeError` raised by Python's own argument binding, never a silently defaulted `0`. And even
when supplied, `emit_finding()` additionally REFUSES the call outright if `scanned_n == 0` is paired
with `status == "OK"` — a detector that examined nothing must be structurally unable to say "fine."
This exists because `backlog_groom.py` degrades to an empty result on any parse failure and
`fault_ledger.load()` returns an empty ledger on a corrupt file — both would otherwise emit a
perfectly green heartbeat over a zero-length scan, indistinguishable from a clean thorough run.

**On a refused zero-scan-OK call, the refusal is not silent** — `_write_zero_scan_canary()` writes a
`status="ERROR"`, `labels={"kind":"zero-scan", ...}` finding into the SAME producer's shard BEFORE
raising `FindingContractError`, so a caller that catches-and-swallows the exception still leaves a
visible trace on the board. The canary function is a dead-end by construction — it builds its own
envelope by hand and never re-enters `emit_finding()`, so it cannot recurse.

**No `id=`, no `fingerprint=`, no `machine=` parameter exists on the function signature at all** —
passing any of the three is a `TypeError` before a line of the function body runs. `machine` comes
from `get_machine_token()` (the ONE shared derivation, `system/tools/machine_token.py`) because two
independent copies of that same derivation once gave the identical physical machine two different
tokens in two different scripts, forking one status tile into two. `fingerprint` is `sha256` of the sorted
`(key, str(value))` label pairs — mechanical identity, borrowed from Prometheus Alertmanager, never
hand-authored, so the same labels in any insertion order hash identically and a different label set
never collides by construction.

**A Drive write failure RAISES here, unlike `fault_ledger._append_incident`'s Drive mirror**, which
swallows its failure on purpose because it always has a local copy that already landed. `emit_finding`
has no local copy — the Drive spine IS the store — so any `OSError` (including the measured
EDEADLK-on-7/8-runs failure mode) propagates. A `SIGALRM`-based 15-second timeout additionally guards
the ONE failure mode a raised `OSError` cannot cover: a wedged FUSE mount that hangs instead of
erroring. The alarm is skipped off the main thread (`signal.signal()` itself raises `ValueError` from
a worker thread) — a documented, deliberate trade: a detector that cannot record a finding at all is
judged strictly worse than one that might occasionally block.

**Has a CLI** (`--producer --status --scanned-n --label KEY=VALUE ... --summary --rc --json`) so a
shell detector (`guard-fire-test-run.sh`, `health-deadman-check.sh`) and a Python detector
(`health_invariants.py`, `backlog_groom.py`) share exactly ONE validator by reference, never by
copy-paste. `--selftest` exercises the full contract including the canary path.

---

### THE STORE

`state/findings/<producer>.<machine>.jsonl` on the Drive spine — one append-only file per
(producer, machine) pair, never a shared file. This mirrors `system-health.py`'s Pulse heartbeat
idiom (`state/status/_pulse-<machine>.json`) and `fault_ledger.py`'s incident shards
(`state/incidents/<machine>.jsonl`). The reason is measured, not theoretical: `health_invariants.py`
had already written a `machine` FIELD into every line of a shared append-only log and that file still
forked NINE ways, stranding 1,169 rows (100% absent from the live copy) — the exact failure this
store's filename-sharding is built to make structurally impossible. A field inside the file does not
stop the file itself from forking; one writer per PATH is what holds.

---

### THE READ SIDE (`findings_reader.py`)

The union reader over every `*.jsonl` shard in `state/findings/`. Mirrors `fault_ledger.py`'s
`incidents_report()` idiom exactly (same shard-glob, same missing-shard accounting, same
never-raise-but-degrade posture) — a deliberate reuse, not a second idiom, because "findings" have no
local fallback copy the way incidents do (no dual-write, so no dedup needed either).

`findings_report()` never returns just a list of rows — it always returns the coverage picture
alongside them: `shards_expected` / `shards_read` / `shards_missing` / `bad_lines` (a dict of
`{shard: malformed_line_count}`, only present for shards with >=1 bad line) / `degraded` (true whenever
the picture is known-incomplete for ANY reason) / `degraded_reason`. A shard that opens but contains
malformed JSON lines is still credited for its good lines — dropping the whole shard over one bad line
would itself be a silent shrink — but `degraded` still flips true, because the ranking layer must know
its input was not clean even though it got *something*. A permission-denied or wedged-mount shard is
NEVER treated as an empty (and therefore silently-lower-count) shard — it lands in `shards_missing`.

---

### THE DEAD-MAN'S SWITCH (`findings_deadman.py`)

The gap this closes: neither `emit_finding.py` nor `findings_reader.py` notices when a PRODUCER
stops running entirely — a detector that stops firing writes nothing, and "nothing written" is
byte-for-byte indistinguishable from "ran clean, found nothing" in the raw store. `findings_deadman.py`
is a pure COMPOSER: it imports `findings_reader.findings_report()` (never re-globs or re-parses a
shard itself) and layers one derived, in-memory judgment on top — it writes nothing to disk.

**`load_producer_roster()` fixes a real, measured enumeration gap (T15.22a).** Before this module,
the only job-enumeration in this codebase was `system-health.py`, which walks Pulse `jobs` slots
ONLY. `health-deadman` is deliberately never a Pulse slot (it watches whether Pulse itself is alive —
Pulse dispatching it would make the watched thing the sole witness to its own death), so a
crontab-only producer was enumerated by NOTHING. This is the named cause of an 87% run-failure period
going unnoticed. The roster is now built from BOTH sources: `pulse-config.md`'s fenced ```jobs``` 
block for Pulse-dispatched producers, and a LIVE `crontab -l` read (falling back to
`pulse-config.md`'s own ```crontab``` block only if the live read is empty/unavailable) for
crontab-only producers. `PRODUCER_JOB` is a small, hand-curated static map — an unlisted producer is
simply never dead-man-watched, never silently misjudged.

For every roster entry, `assess_producers()` finds the LATEST finding across all machines/fingerprints
and compares its age to `cadence + max(600, cadence*0.5)` grace — mirroring `system-health.py`'s
`tile_for()`/`assess()` exactly (a tile's `last_run`/`stale_after_s` pair, replayed for findings). A
producer with no finding on record AT ALL is `STALE` immediately (`last_epoch is None`). The result is
never written back to any store — `findings_report_with_deadman()` appends a SYNTHETIC row (shaped
like a real finding but carrying `"synthetic": True`) into the SAME `rows` list a caller already
ranks, so `health_line.py` needs no second code path — but the dead-man assessment always runs over
the UNFILTERED union first, then filters, so narrowing by fingerprint/producer never makes every
OTHER producer look silent.

WARNING: **`STALE` is deliberately NOT in `emit_finding.py`'s `VALID_STATUS`** (`{"OK", "NEEDS_REVIEW",
"NEEDS_APPROVAL", "ERROR"}`, imported unchanged from `emit_status.py`) — no producer ever writes the
word `STALE` to disk. It is derived at READ time only, the same rule status tiles already follow
("desks never emit STALE — Helm derives it").

---

### THE SESSION-START CONSUMER (`health_line.py`)

The ONLY currently-wired reader of Hospital's output. `session_context_loader.sh` (registered as the
`SessionStart` hook, `system/reference/settings.json` line 347) invokes `health_line.py` at line 110
of every session start. As of T15.22, `_findings_line()` reads through
`findings_deadman.findings_report_with_deadman()` (never `findings_reader.findings_report()`
directly), so a silent producer surfaces exactly like a broken one.

**The session-floor wrapper distinguishes "the reader crashed" from "nothing to report" — via an
explicit rc-check.** The invocation is wrapped in `session_context_loader.sh`'s `_findings_banner()`,
which captures `rc=$?` from the `health_line.py` call and, on any non-zero rc, prints
`note: health_line.py did not run this session (rc=$rc) — findings/health banner unavailable`
instead of staying silent (`session_context_loader.sh`, `_findings_banner()`). This is load-bearing
because `health_line.py`'s own contract is *"never raises, never exits nonzero"* — so a non-zero rc
means the TOOL ITSELF could not start (missing file, broken interpreter), which is a DIFFERENT
failure from "ran clean, nothing to report," and both of them render as an empty string. A wrapper
that tests only whether the output is non-empty cannot tell the two apart, and would reproduce one
layer up — inside the session floor itself — the exact false-green this whole subsystem exists to
kill. ⚠ The WIRING is not the new part: `health_line.py` has been invoked from the SessionStart
hook since this element was first authored. The rc-check is the addition (2026-08-14); a working
`health_line.py` that finds nothing still prints nothing, exactly as before.

**Ranking rule:** collapse to the LATEST row per fingerprint (a fingerprint is a finding's stable
identity — the line must show CURRENT state, not every historical run), then sort the non-OK survivors
by `(status severity, then oldest ts first within a tier)` — `STALE` outranks `ERROR` outranks
`NEEDS_APPROVAL` outranks `NEEDS_REVIEW`. Oldest-first within a tier is deliberate: the founding
failure this whole subsystem exists to prevent was 57 archivist findings sitting unread for 7 days,
and newest-first ranking would bury exactly that shape of neglected-but-old problem under whatever
fired five minutes ago. Capped at 3, always stating the cut count (`+N more not shown`) — a silent
truncation would be the unread-pile failure in a new shape. Silent (prints nothing) only when nothing
is broken AND the read was clean.

**Explicitly does NOT fail-closed-to-silence on its own exception** — this is the one place in the
codebase's general "fail closed" posture that is deliberately inverted, with the reasoning left in the
code itself: *"Hospital's entire stated purpose is 'I make what is broken impossible to not-see.' A
consumer that goes quiet when it breaks reproduces, inside the anti-silence machinery itself, the exact
failure that machinery exists to end."* An unexpected exception returns
`"FINDINGS: UNAVAILABLE — Hospital's reader raised <Type> (this is a bug in Hospital, not an all-clear)"`
rather than nothing. A `SIGALRM`-based 8-second timeout (main-thread only, same reasoning as
`emit_finding.py`'s write-side alarm) guards a wedged Drive read.

---

### THE GRADING / RANKING LAYER (`fault_proposer.py` + `fault-proposer-run.sh`)

Reads `fault_ledger.py`'s recurrence data and grades each open fault **INSTANCE / SUBSYSTEM /
ORGANISM** — never asserted, always DERIVED from recurrence counts, with the evidence that chose the
altitude quoted inside the proposal. **A proposal that cannot cite its evidence refuses to emit.**
Thresholds are named and defended in the code: `SUBSYSTEM_AFTER = 3` (a fault must close 3+ times to
be a pattern rather than a coincidence — the asymmetric cost of being wrong is sending a human to
rebuild something that was fine); `ORGANISM_DISTINCT_KEYS = 2` (2+ DIFFERENT recurring fault keys is
the floor at which "these share a cause" becomes worth a human's time).

**The DECISION gate — found on this tool's own first real run (T3.4/T15.13).** The very first live
run proposed "fix clair-ingest" and "fix registry:dobby" — both were WORKING AS INTENDED: the operator had
deliberately parked clair-ingest, and dobby was ruled dormant. That is exactly the failure of the
2026-07-28 incident (commit 4d5c1af) that this whole audit traces back to: a mechanism unable to tell
a FAULT from a DECISION resurrected something a human switched off on purpose — reappearing here,
within minutes of this layer existing. `parked_jobs()` now reads Pulse's breaker state and treats any
`retry_at` more than 7 days out as a human decision (the breaker's own backoff caps at 24h, so
anything past a 7-day floor cannot be a timer) — `propose()` checks this FIRST, before any altitude
reasoning, and returns `altitude: "DECISION"` with `action: "NO ACTION."` for a parked job.

**Cohort collapsing (T15.13a) — found on the tool's actual first real run.** An `ORGANISM` verdict is
a claim about the whole cohort (every recurring fault gets the SAME altitude/action/evidence from
`recurrence_all()`), so printed per-fault it became 11 open faults rendered as 11 identical 78-line
blocks — which inverts Hospital's own stated purpose by making the one real finding invisible again
under repetition. `render_cohort()` collapses same-evidence `ORGANISM` proposals into ONE printed
finding naming all N faults; the altitude derivation itself is untouched.

**Writes NOTHING** — `main()` only prints. Registered as a Pulse `jobs` slot (`fault-proposer`, daily
= 86400s, `pulse-config.md` line 325). Its runner's exit-code contract is explicitly documented against
a real regression this same build hit (commit history: "the driver stopped at exit 2 while the gate
started emitting 3"): exit 0 covers proposals-emitted, no-open-faults, AND a refusal-for-want-of-
evidence — a refusal is a CORRECT outcome, not a failure, and Pulse's 3-strike breaker would otherwise
disable the watchdog after 3 correct refusals. Exit 1 means the proposer itself broke. The runner's own
comment additionally flags that the proposer's docstring claims an "exits 2" refusal path that DOES
NOT EXIST in the code — the runner was written to trust the code, not the docstring.

---

### THE LIFECYCLE STORE (`fault_ledger.py`)

`~/.local/state/lifehack/faults.json` — `first_seen`/`last_seen`/`last_alert` per active fault, plus
`~/.local/state/lifehack/incidents.jsonl` (append-only, mirrored per-machine to
`state/incidents/<machine>.jsonl` on the Drive spine) for CLOSED incident history, which is what
`recurrence()` and `recurrence_all()` read to answer "has this happened before."

**T15.18 widened the key space, not the store.** A legacy fault still keys as `"<job>|<state>"`; a
Hospital finding keys as `"fp:<fingerprint>"` in the SAME `d["faults"]` dict — provably disjoint
namespaces (a legacy key's 3rd char is always the literal `|` delimiter once job/state are non-empty;
a fingerprint key's first three chars are always literally `fp:`, and no job name can produce both).
`record_faults()` and `record_findings()` are the lifecycle managers for each namespace; each is
strictly filtered to its OWN namespace's keys on the reap ("no longer active, bank and drop") pass —
getting this wrong would let a legacy sweep silently reap fingerprinted history to zero. This is the
load-bearing line, not decoration.

---

### CONVERTED DETECTORS (the four producers emitting through Hospital today)

1. **`health_invariants.py`** — emits ONE finding PER INVARIANT (hooks / guards / clone-freshness /
   heartbeats / coverage), `labels={"job":"health-invariants","invariant":<name>}`, replacing the old
   shared `state/health.jsonl` append that forked nine ways. Called by `system-health.py`'s own sweep
   cycle — not independently Pulse-scheduled.
2. **`backlog_groom.py`** — `_emit_findings()` is called from inside `build_report()` itself, so every
   time `backlog-health.py` runs (Pulse slot `backlog-health`, 21600s / 6h, `pulse-config.md` line 367)
   the groom report ALSO lands in Hospital under `producer="backlog-groom"`.
3. **`guard-fire-test-run.sh`** — shell, never imports `emit_finding.py`; goes through the CLI —
   proof the CLI is real reference-shared propagation, not decoration. Emits `producer="guard-fire-test"`
   weekly (Pulse slot, 604800s, `pulse-config.md` line 342), plus a separate broken-tool-path emit
   (`scanned_n=0`, `status=ERROR`) if `verify-hooks.sh` itself fails to run.
4. **`health-deadman-check.sh`** — shell CLI, emits `producer="health-deadman"` on EVERY exit path via
   a function trap (so a future added `exit` can never skip it), including the clean "stood down, not
   the lead" case — Piece 1's whole point being that "found nothing" and "did not run" must stay
   distinguishable, which is the exact class of bug that let THIS SAME job abort 7 of 8 runs earlier
   this same day without anyone noticing. Registered via crontab (line 425, `pulse-config.md`,
   `machine=all`, hourly at :17), not a Pulse slot, by explicit design (it watches whether Pulse itself
   is alive).

---

### WHAT IS NOT YET CONVERTED (verified 2026-08-04 by grep)

`grep -rl "emit_finding" system/tools/*.py system/tools/*.sh` returns exactly 10 files: the six
Hospital-core modules above, plus the four converted detectors. The following known failure-signal
producers do **NOT** yet emit through Hospital — confirmed by their absence from that grep and their
continued presence as standalone `*-health.py` files:

`system/tools/system-health.py` (the sweeper itself) · `system/tools/planning-health.py` ·
`system/tools/clair-health.py` · `system/tools/deryl-books-health.py` ·
`system/tools/dobby-health.py` · `system/tools/marc-health.py` ·
`system/tools/security-health.py` · `system/tools/sentinel-health.py`

That is 8 of roughly 12 known health/failure producers in this codebase still reporting ONLY through
their own status tile — never into `state/findings/`. Hospital's "ask 'what is wrong?' once" promise
is real for the 4 converted producers and NOT YET real for these 8. See GAPS.

---

### GATES AND ENFORCEMENT (the honest map)

~~**No hard hook-enforced wall exists for Hospital, as of this write.** A grep of `system/hooks/` for
"emit_finding\|state/findings\|hospital" and a scan of the `PreToolUse` block in
`system/reference/settings.json` (which registers exactly two guards — `guard_write_paths.sh` line
183, `guard_ledger_discipline.sh` line 188) both return nothing Hospital-related. Nothing structurally
prevents a hand-rolled `Bash echo >> state/findings/x.jsonl` write that bypasses `emit_finding()`'s
entire contract — the same class of gap `guard_write_paths.sh`'s own header already admits
system-wide (Bash bypasses the Write|Edit hook plane by construction). **This is not asserted as a
real seam anywhere below — see INTEROP SEAMS and GAP-3.**~~

> **⚠ CORRECTED 2026-08-24:** This was wrong on both the search and the conclusion, re-verified
> directly this session. `system/reference/settings.json` does not exist on disk at all (`find`
> confirms 0 matches) — hook registration moved; the real source of truth is
> `system/hooks/registrations.json`, and the live per-machine file is `.claude/settings.local.json` — ⛔ genuinely absent on this machine, not merely undocumented (install-guard-registrations.py would write a hook registration there, and none exists here)
> (installed from it by `system/tools/install-guard-registrations.py`; `.claude/settings.json`
> itself carries an explicit `_hooks_moved` note saying so). The claimed grep is also simply wrong:
> `grep -rl "emit_finding\|state/findings\|hospital" system/hooks/` finds
> `system/hooks/guard_findings_write.sh` directly (plus its own test file,
> `system/hooks/tests/test_findings_and_delegation.sh`). That guard is registered in
> `system/hooks/registrations.json:278-284` on matcher `Bash|Write|Edit`, and it is NOT theatre:
> fire-tested this session with a synthetic payload —
> `{"tool_name":"Bash","tool_input":{"command":"echo synthetic_test_line >> state/findings/synthetic-probe.jsonl"}}`
> piped to it — and it returned a genuine `{"decision":"block", ...}` refusing the write, exit 2. So
> a hand-rolled Bash write IS mechanically blocked when this guard is installed. The one caveat that
> remains genuinely open, not resolved by this correction: whether `guard_findings_write.sh` is
> actually *installed* (present in `.claude/settings.local.json` — ⛔ absent on this machine) on any given machine is a separate,
> per-machine question from whether the guard script itself works — on this machine this session,
> `.claude/settings.local.json` does not exist — ⛔ genuinely absent here, so live-install status here is COULD-NOT-EVALUATE,
> not confirmed active. See item 7 below, corrected to match.

**Script-level (not hook-level) enforcement that IS real:**

1. **`scanned_n` contract** `[script]` — `emit_finding()` refuses `scanned_n==0` paired with
   `status=="OK"`, and `scanned_n` itself has no default (a `TypeError`, not a silent zero). Enforced
   in-process on every call, CLI or Python import alike.
2. **Cited-evidence-or-refuse** `[script]` — `fault_proposer.choose_altitude()` returns `(None, [])`
   rather than an altitude with no evidence; `propose()` returns `{}` (a refusal) in that case, and
   `main()` prints `"REFUSED — no citable evidence"` rather than a groundless claim.
3. **Namespace-disjointness in `fault_ledger.py`** `[script]` — `record_faults()`/`record_findings()`
   each filter strictly to their own key prefix on the reap pass; the disjointness is proven by string
   construction (see THE LIFECYCLE STORE above), not merely tested.
4. ~~**`require_primary` machine gate** `[script]` — `backlog-health-run.sh`, `fault-proposer-run.sh`
   (implicitly via its own machine-token derivation), and `guard-fire-test-run.sh` all gate on
   `state/primary-machine` so only the lead machine writes its tile; this is a residency discipline,
   not a security wall.~~ **⚠ CORRECTED 2026-08-24: none of this exists.** Re-checked this session:
   `require_primary` has zero definitions anywhere in the repo; `backlog-health-run.sh` does not
   exist (per `elements/backlog-authority.md:199-205`, Pulse invokes the tile producer directly, "no
   machine gate, no `require_primary`, and no `state/primary-machine` marker"); `grep -n
   "require_primary\|primary-machine" system/tools/fault-proposer-run.sh` returns nothing;
   `guard-fire-test-run.sh` only *mentions* `require_primary` in a comment describing it as the
   donor's dropped gate. This system has one machine
   (`docs/data-layout.md:215`), so there is no lead machine to gate on. Same fabrication, same
   pattern, as `elements/pulse-cron.md`'s corrected GATES section.

**Honor-system (prose instruction only; no hook or script enforces these):**

5. **Every detector routes through `emit_finding()`** `[honor]` — nothing prevents a NEW detector
   from hand-rolling its own JSONL line into `state/findings/` instead of calling the validator. The
   four converted detectors do it correctly by construction (code review, not a gate).
6. **Hospital never remediates** `[honor]` — every module's docstring states this as a design
   commitment (`fault_proposer.py`: "It PROPOSES. It never applies, never re-runs a job, never edits a
   file."), but nothing mechanically prevents a future caller from acting on a proposal without a
   human in the loop. The boundary is currently a written commitment, not a wall.

---

### GAPS (documented fail-open conditions)

**GAP-1 — 8 of ~12 known failure producers do not emit Hospital findings.**
`system-health.py` (the sweeper itself) and 7 of the 8 per-desk `*-health.py` producers
(`planning-health.py`, `clair-health.py`, `deryl-books-health.py`, `dobby-health.py`, `marc-health.py`,
`security-health.py`, `sentinel-health.py`) report only through their own status tile, never into
`state/findings/`. A problem detected by any of these 8 is invisible to `fault_proposer.py`'s grading,
to `findings_reader.py`'s union, and to `health_line.py`'s session-start line — it can only be seen by
opening Helm directly. Hospital's stated purpose ("ask 'what is wrong?' once") is not yet true for
these 8. **Posture impact:** a session that trusts the `health_line.py` banner as "everything Hospital
knows about" is trusting a partial picture, and nothing on the banner itself says so.

**GAP-2 — no write-time enforcement that a detector routes through `emit_finding()`.**
Nothing structurally stops a hand-authored JSONL line from landing in `state/findings/` outside the
validator's contract (malformed envelope, hand-chosen fingerprint bypassing the mechanical hash,
etc.). The four converted detectors are correct by construction today, but this is unenforced —
consistent with the codebase-wide admitted gap that Bash bypasses the Write|Edit hook plane entirely.

**GAP-3 — no deny-hook (or any hook) is registered for Hospital's store or writer.**
Checked directly: `system/hooks/` has no file referencing findings/fault/hospital, and
`system/reference/settings.json`'s `PreToolUse` block registers only `guard_write_paths.sh` and
`guard_ledger_discipline.sh`, neither of which targets `state/findings/` or `emit_finding.py`. This is
recorded here as NOT-YET-BUILT rather than asserted as a live seam anywhere in this document.

**GAP-4 — the manual entry (T15.25) does not exist yet.**
`system/organism/manual.md` carries no pointer to this element as of this write (grepped directly —
zero matches for "hospital", "emit_finding", "findings_reader", or "fault_proposer"). A session reading
only the manual (the middle index) cannot discover Hospital exists at all; this element file is
findable only by directly listing `system/organism/elements/`.

**GAP-5 — `health-invariants.md` (the pre-existing sibling element) is stale relative to the code it
describes.**
That element's `generated_from` and body describe `health_invariants.py` writing to
`state/health.jsonl` and make no mention of `emit_finding`, `state/findings/`, or Hospital at all —
even though `health_invariants.py` was converted to emit through Hospital under this same build
(T15.19, see `_emit_findings()` in that file). This element (`hospital.md`) does NOT edit or resolve
that staleness — editing another element is out of scope for this task — but names it here so a future
session does not read `health-invariants.md` as the current picture of what that module writes.

---

### INTEROP SEAMS (organism view)

**1. `hospital` READS `health_invariants` · `backlog_groom` · `guard-fire-test-run.sh` ·
`health-deadman-check.sh`.**
These four are Hospital's only current producers — every finding in `state/findings/` today
originates from one of them, via `emit_finding()`. See CONVERTED DETECTORS above.

**2. `hospital` WRITES-> `Helm` — NOT YET, verify before trusting.**
No Helm tab or fixture reads `state/findings/` directly as of this write (unlike `backlog-authority`'s
`state/status/backlog.json`, which the Helm Backlog tab reads today). The only wired consumer is
`health_line.py`'s session-start text line. This is stated as an open item, not asserted as live.

**3. `hospital` FEEDS `notify-plane` — indirectly, via `fault_ledger`'s escalation, not directly.**
`fault_ledger.py`'s `due_for_escalation()`/`escalation_message()` machinery (ONE escalation tier,
re-alerts daily) is the same ledger `record_findings()` now writes fingerprinted rows into — so a
Hospital finding that stays open long enough inherits the SAME escalation path a legacy job|state
fault already used, through `notify-send.sh`/`notify-governor.py`. This element does not independently
verify that a fingerprinted row actually reaches `due_for_escalation()`'s caller — flagged here as
inferred from the shared-store design, not independently traced end-to-end this session.

**4. `hospital` TRIGGERS-BY `pulse-cron`.**
Three of Hospital's producers run as named Pulse `jobs` slots: `backlog-health` (21600s,
`pulse-config.md` line 367), `fault-proposer` (86400s, line 325), `guard-fire-test` (604800s, line
342). `health-deadman` runs via crontab (line 425), deliberately NOT a Pulse slot — it watches whether
Pulse itself is alive, so Pulse dispatching it would make the watched thing the sole witness to its
own death. `health_invariants.py` is not independently scheduled; it runs as a child of
`system-health.py`'s own Pulse-slot cycle (line 298).

**5. `hospital` COMPLEMENTS `health-invariants` — THE BOUNDARY, STATED EXPLICITLY.**
The Health Authority (`health_invariants.py` + `system-health.py`, documented in the separate,
pre-existing `health-invariants.md` element) answers **"is the SUBSTRATE intact?"** — hooks present,
guards untampered, the clone fresh, both machines heartbeating, Pulse coverage complete. Hospital
answers a DIFFERENT question: **"what has any detector — including health_invariants itself —
FOUND, and how bad is it?"** `health_invariants.py` is BOTH a substrate-checker AND (since T15.19) one
of Hospital's four producers: it runs its five substrate invariants, then emits each result as ONE
Hospital finding. So the relationship is not two independent siblings — `health_invariants` is a
CLIENT of Hospital's write contract, and Hospital is the RANKING layer one altitude above it. They
must not be merged: `health_invariants` still fully owns what "substrate-intact" MEANS (the five
invariant definitions); Hospital owns nothing about substrate correctness and only knows what
`health_invariants` chooses to report through `emit_finding()`. A future session must not read
`hospital` as replacing or superseding `health_invariants`'s own checking logic — it only ranks what
that logic already decided.

**6. `hospital` KEYS-OFF `two-machine-residency`.**
Every store in this subsystem follows the machine-in-the-PATH rule, never machine-in-the-payload-only:
`state/findings/<producer>.<machine>.jsonl`, `state/incidents/<machine>.jsonl`,
`state/status/fault-proposer-<machine>.json`, `state/status/health-deadman-<machine>.json`. This is
stated directly in `emit_finding.py`'s own docstring as the fix for the measured 9-way fork /
1,169-stranded-rows failure, and `fault-proposer-run.sh` restates it as "the residency law."

~~**7. `hospital` GUARDED-BY — NOTHING, as of this write.**
No deny-hook or any other hook is registered for Hospital's writer or store (verified directly — see
GAPS GAP-3). This seam is deliberately NOT asserted as real; recorded here only to make the absence
explicit rather than silently omitted.~~

**7. ⚠ CORRECTED 2026-08-24: `hospital` GUARDED-BY `guard_findings_write.sh` — real, fire-tested this
session.** This is the twin correction to the GATES AND ENFORCEMENT banner above. `system/hooks/
guard_findings_write.sh` exists, is registered on matcher `Bash|Write|Edit` in
`system/hooks/registrations.json:278-284` (the actual source of truth — `system/reference/
settings.json`, which GAP-3 below cites, does not exist on disk), and blocks exactly the class of
write this section is about: a hand-rolled line into `state/findings/` or `state/recommendations/`
that bypasses `emit_finding.py`/`emit_recommendation.py`. Fire-tested directly this session with a
synthetic stdin payload targeting `state/findings/synthetic-probe.jsonl` — ⛔ an example path used only for this fire-test, never a real file — no destructive write
attempted, the guard intercepted it and returned `{"decision":"block", "reason":"BLOCKED: a direct
write into a VALIDATED STORE - state/findings/ (Hospital)...` }`, exit 2. The manual's twin claim
(`system/organism/manual.md` ~L1231-1236) was corrected earlier today to match. **One caveat left
open, not resolved by this correction:** the guard script working when invoked directly is a
different fact from whether it is *installed* on a given machine — that requires
`.claude/settings.local.json` — ⛔ genuinely absent here — to carry the entry (written by `system/tools/
install-guard-registrations.py`). On this machine this session that file does not exist, so live-
install status here is COULD-NOT-EVALUATE. What IS confirmed: the guard is source-of-truth
registered and functionally real, which is a different world from "GUARDED-BY — NOTHING."

---

### INTENT / CURRENT-VS-TARGET

> *"I am the place where every problem this system detects about itself becomes ONE comparable record,
> so that a human or a machine can ask 'what is wrong?' once — at ground, subsystem, or whole-system
> altitude — and get a ranked, evidence-cited answer instead of a pile of incompatible notes. I do not
> fix anything. I make what is broken impossible to not-see."*

**BY DESIGN — detects and ranks, never remediates.** Every producer and every reader in this subsystem
writes/reads findings; none of them acts on one. `fault_proposer.py`'s own docstring names the
specific incident (4d5c1af, 2026-07-28) that makes this a hard boundary rather than a preference: an
earlier mechanism that automated recovery could not tell a FAULT from a DECISION, and resurrected a
job a human had deliberately parked. A layer that fixes things unasked rebuilds that failure on
purpose — so it does not exist here, anywhere, by design.

**Current state -> PARTIAL, for two separate, cited reasons:**

1. **Coverage is real but incomplete** (GAP-1). The write contract, the store, the union reader, the
   dead-man's switch, the grading layer, and the session-start consumer are all LIVE and wired
   end-to-end for the 4 converted producers — this is not vaporware, it runs today. But 8 of ~12 known
   failure producers still report only to their own tile, invisible to Hospital entirely.
2. **The self-schematic is mid-build** (GAP-4, GAP-5). This element documents Hospital for the first
   time; the manual entry that would make it discoverable from the middle index does not exist yet
   (T15.25); and the pre-existing sibling element (`health-invariants.md`) has not been updated to
   reflect that `health_invariants.py` now emits through Hospital, so a session reading only that
   element would not learn Hospital exists at all.

**TARGET:**
1. Convert the remaining 8 producers (`system-health.py` plus the 7 unconverted `*-health.py`
   desk producers) to emit through `emit_finding()`, closing GAP-1.
2. Write the `manual.md` pointer entry (T15.25), closing GAP-4.
3. A future session should refresh `health-invariants.md`'s own `generated_from`/body to reflect its
   T15.19 conversion, closing GAP-5 — out of scope for THIS task, which may not edit that file.
4. Decide, explicitly, whether Hospital's store needs a write-time guard (closing GAP-2/GAP-3) or
   whether the honor-system posture is an accepted, named risk — currently undecided, not silently
   deferred.

---

### HARD PROHIBITIONS (what Hospital never does)

- No remediation, no auto-fix, no auto-re-run of a failed job — proposal and ranking only, at every
  layer, with the specific 2026-07-28 incident (4d5c1af) as the reason this is a hard line.
- No hand-authored `id=`/`fingerprint=`/`machine=` on a finding — `emit_finding()`'s signature makes
  this a `TypeError`, not a discouraged pattern.
- No `status=="OK"` with `scanned_n==0` — refused at the writer, with a canary left on disk so the
  refusal itself is never silent.
- No shared append-only file across machines or producers — one shard per (producer, machine) path,
  always.
- No producer-declared `STALE` — that word is derived at read time only, by `findings_deadman.py`,
  never written to disk by any producer.
- No `fault_proposer` altitude without cited evidence — an uncited proposal is refused, not guessed.
- No acting on a deliberately parked job as if it were broken — the DECISION gate checks this before
  any altitude reasoning runs.

---

### EDGE CASES

1. **A detector calls `emit_finding(status="OK", scanned_n=0, ...)`.** The call is refused
   (`FindingContractError`), but a `status="ERROR"`, `labels={"kind":"zero-scan"}` canary is written to
   that producer's own shard FIRST — so a caller that catches and discards the exception still leaves a
   visible trace.

2. **A Drive write hangs instead of erroring (wedged FUSE mount).** The `SIGALRM`-based 15-second
   alarm in `emit_finding.py` (main-thread only) converts the hang into a `TimeoutError`, distinct from
   the ordinary `OSError`/EDEADLK path — both propagate to the caller rather than being swallowed.

3. **A findings shard has some malformed JSON lines but otherwise opens fine.** `findings_reader.py`
   keeps the good lines, counts the bad ones in `bad_lines[shard_name]`, and still flips `degraded=True`
   — a partially-corrupt shard is credited for what it has, but the picture is honestly marked
   incomplete.

4. **A producer stops running entirely — no error, just silence.** `findings_deadman.py` derives a
   synthetic `STALE` row once `now - latest_finding_ts > cadence + grace`; this row is never written to
   disk, only appended in-memory to what `health_line.py` and any other `findings_report_with_deadman()`
   caller sees.

5. **`fault_proposer.py` is asked to grade a fault that has closed 0 times before.** `choose_altitude()`
   returns `INSTANCE` with evidence noting the incident log only begins 2026-07-28 — an older fault may
   therefore be mis-read as first-time until the log matures. This is stated as a caveat in the
   evidence itself, not hidden.

6. **A human has deliberately parked a job (e.g. `clair-ingest`).** `parked_jobs()` reads Pulse's
   breaker state; any `retry_at` more than 7 days out is judged a human decision, never a backoff
   timer (the breaker's own cap is 24h) — `propose()` returns `altitude:"DECISION"`, `action:"NO
   ACTION."` rather than proposing a fix.

7. **Several distinct faults share an `ORGANISM`-level verdict.** `render_cohort()` collapses them into
   ONE printed finding naming all N faults, rather than N near-identical blocks — found necessary on
   the tool's own first real run (11 faults would otherwise have rendered as 11 copies of a 78-line
   evidence dump).

8. **`guard-fire-test-run.sh`'s own engine (`verify-hooks.sh`) fails to RUN** (rc > 1, not merely a RED
   result). The runner emits a SEPARATE Hospital finding (`status=ERROR`, `scanned_n=0` — allowed only
   because status is not `OK`) distinguishing "could not verify guard health at all" from an ordinary
   RED/downgrade finding.

---

## AUTO-COMPUTED   (machine-only — hand-set at authoring; the F1.5 checker will own this once built)

- **maturity_label:** LIVE·gap [provisional]
- **why `·gap`:** 8 of ~12 known failure producers do not yet emit through Hospital (GAP-1); no
  write-time hook exists for the store or writer (GAP-2/GAP-3); the manual entry does not exist yet
  (GAP-4); the sibling `health-invariants.md` element is stale relative to its converted code (GAP-5).
- **check_detail:** LIVE end-to-end for 4 producers: `emit_finding.py` (validating writer, CLI +
  import, refuses scanned_n=0/status=OK with a canary) · `findings_reader.py` (union reader, honest
  degradation accounting) · `findings_deadman.py` (dead-man's switch, roster from Pulse jobs +
  live crontab) · `health_line.py` (session-start consumer, wired via `session_context_loader.sh`
  line 110, registered SessionStart hook `settings.json` line 347) · `fault_proposer.py` +
  `fault-proposer-run.sh` (INSTANCE/SUBSYSTEM/ORGANISM grading, cited-evidence-or-refuse, DECISION
  gate for parked jobs, cohort collapsing, Pulse slot `pulse-config.md` line 325) · `fault_ledger.py`
  (namespace-disjoint dual-key lifecycle store). Converted producers: `health_invariants.py`
  (Pulse slot line 298, as a child of system-health), `backlog_groom.py` (via `backlog-health.py`,
  Pulse slot line 367), `guard-fire-test-run.sh` (Pulse slot line 342), `health-deadman-check.sh`
  (crontab line 425). What is honor-system: routing a NEW detector through `emit_finding()` at all
  (no hook enforces this) · Hospital's never-remediates boundary (a written commitment, not a
  mechanical wall). What is missing: 8 producers unconverted (GAP-1) · any write-time guard (GAP-2,
  GAP-3) · the manual.md pointer (GAP-4, T15.25, separate task) · `health-invariants.md`'s own
  refresh (GAP-5, out of this task's scope). Mixed (live end-to-end pipeline for a minority of
  producers + a real, named, still-open coverage gap + an unfinished self-schematic) => **PARTIAL**.
  Honest.

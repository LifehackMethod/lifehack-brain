# Phase 0 — System Layer (machine-only · no human turn)

**Objective:** produce **the Map** on disk — a thin, ranked, pointer-based digest of the person's world for the week
under review — so the session that follows works from the Map, never from raw corpus.

> ## ⛔⛔ WHEN THIS RUNS: ~~**EXACTLY WHEN SOMEBODY INVOKES THE SKILL. THERE IS NO NIGHT-BEFORE PATH.**~~
> ⛔ **SUPERSEDED 2026-08-06 by the person's ruling (`authority: user`) — see below.**
> ~~**the person's ruling, restated at his explicit instruction 2026-08-05 because it keeps getting re-proposed:**~~
> ~~*"Ideally it would run overnight — but the truth of the matter is the computer is off often. It runs exactly~~
> ~~when somebody invokes the skill."*~~
>
> ## ⭐ THE LIVE RULING (the person's, 2026-08-06, `authority: user`):
> **A SCHEDULED PASS MAY PRIME THE MAP; NO PHASE MAY EVER ASSUME IT.** A mid-week pass (Thursday, with
> Friday/Saturday catch-up) runs the four map-agent lenses over the corpus-to-date so the day-of run only
> processes the delta. Every phase must still run correctly with NO priming at all, behind a bounded
> `{WARM, PARTIAL(n of m), COLD}` state where `COLD` is never spellable the same way as `WARM`.
> ⭐ **What was ALWAYS forbidden — and still is — is the ASSUMPTION, never the SCHEDULE.**
>
> ⛔ **WHAT IS FORBIDDEN IS THE ASSUMPTION, NOT THE SCHEDULE. NEVER WRITE A PHASE THAT ONLY WORKS IF THE
> MAP IS ALREADY THERE.** This phase must produce a correct Map from a cold start, every time, with the
> human waiting. **The reason, MEASURED: the laptop sleeps and the person starts on wake**, so anything
> scheduled may simply not have fired — and a phase that assumes it did is a phase that silently ships a
> thin Map.
>
> ⚠⚠ **PRECISION MATTERS HERE — CORRECTED 2026-08-05.** This block previously also said *"`launchd`
> cannot read the Drive mount (macOS TCC),"* and that fact — **true of `launchd`** — was being read as
> *"no scheduled path can ever work."* **FALSE.** ClaudeOps schedules from **`crontab`**, and ~40 pulse
> jobs read Drive on it every five minutes (`ingest-run.lib.sh:28,65`). ▶ **So a WARMING cron that
> processes the corpus in the days before a review is legitimate and is being planned** (`W4`) — what
> stays forbidden is this phase DEPENDING on it.
>
> ⭐ **THE SHAPE THAT SATISFIES BOTH: report warmth as a bounded state — `{WARM, PARTIAL(n of m), COLD}`
> — and NEVER let `COLD` be spellable the same way as `WARM`.** Do the missing work; say which state you
> were in. **A silent assumption of warmth is the actual defect; the schedule never was.**
>
> ⭐ **THE STANDING CONSEQUENCE: every proposal about this phase is priced COLD, in the foreground, with the
> human waiting.** A design that only pays off if the Map already exists is not a design, it is a wish.
> *(This paragraph replaced the line "Ideally a cron the night before; falls back to in-the-moment," which
> was a DEAD BRANCH that read as a live option and sent multiple sessions and two council advisors down it.)*

**Where the Map lives:** a separate doc the session ingests at start —
`$DATA/desks/cal/state/checkin-scratch/weekly-<YYYY-Www>/map.md`. The session's scratchpad is seeded FROM it.

## Run (you are orchestrating sub-agents, not reading raw yourself)
1. Pull the week's window from the central store — **ONCE**, to a file. Everything downstream READS that file.
   ⛔⛔ **HALT CHECK — BEFORE `mkdir -p`, BEFORE ANY PULL: refuse to write into a directory that already
   holds a COMPLETED run (added 2026-08-07).** **Verified live 2026-08-07: `date +%G-W%V` returned
   `2026-W32`, the exact directory already holding a control run's `map.md`, `window.json`,
   `map-returns.json` AND `session-scratchpad.md`.** Running step 1 as originally written overwrites that
   control on the very first line. ⭐ **The loss is SILENT because every path still resolves** — no error,
   just a clobbered baseline. `session-scratchpad.md` is the tell: Phase 0 never writes it (line 42 — the
   session's scratchpad is seeded from the Map only once the HUMAN-facing session starts), so its presence
   in `$SCRATCH` is proof, read off the ARTIFACT and not a claim (Law 3), that a review already advanced
   past this phase.
   ```bash
   WEEK="$(date +%G-W%V)"; SCRATCH="$DATA/desks/cal/state/checkin-scratch/weekly-$WEEK"
   if [ -f "$SCRATCH/session-scratchpad.md" ]; then
     echo "HALT: $SCRATCH already holds a completed run's session-scratchpad.md — refusing to overwrite." \
          "Confirm this is an intentional re-run before proceeding." >&2
     exit 1
   fi
   mkdir -p "$SCRATCH"
   python3 "$ROOT/shared/tools/item_store_window.py" \
     --last-days 7 --mode bundle > "$SCRATCH/window.json"
   RC=$?
   ```
   ⚠ **`WEEK` stays keyed to the ISO week, unchanged.** `SKILL.md:155`, `01a-lookback.md:160`, and
   `system/tools/planning-weekly-prime-run.sh:100` all independently recompute this exact same
   `weekly-<YYYY-Www>` path to find what Phase 0 wrote — renaming the scratch dir from inside this file
   alone would silently break every one of those seams, which is worse than the bug this fixes. **A NAMING
   change is out of scope for a one-file edit — flagged here rather than done, same spirit as the
   `item_store_window.py` carve-out.** This HALT check is the fix that fits inside this file: it stops the
   SILENT OVERWRITE without touching the shared directory contract, and it does not block the legitimate
   WARM-priming case (lines 12–39) — priming writes `map.md` only, never `session-scratchpad.md`, so a
   primed-but-not-yet-run week still passes through clean.
   (full de-duped bodies; threads flattened). Heavy raw reading stays in sub-agents — raw never enters this window.

   ⛔ **`--last-days 7`, NEVER a computed `--since`/`--until` pair. `--until` is HALF-OPEN** (`since <= dt <
   until`, `item_store_window.py:153`) **and the old driver computed `Monday+6`, so SUNDAY WAS STRUCTURALLY
   EXCLUDED — on the very day the review runs.** `--last-days 7` sets `until = now`, so the current day is
   always inside the window and it is correct on *any* day he runs, not only Sunday. *(Fixed 2026-08-03. The
   correct flag already existed; the driver simply never used it — a spec→file transfer loss, PART I Law 2
   seam 1, not a runtime bug.)*

   ⛔ **THE PULL MUST HAVE COMPLETED. AN EMPTY OR TRUNCATED WINDOW ENDS THE PHASE — it is NEVER a quiet week.**
   ```bash
   python3 - "$SCRATCH/window.json" "$RC" <<'PY'
   import json,sys
   path, rc = sys.argv[1], int(sys.argv[2])
   if rc != 0: sys.exit("HALT: the window pull exited rc=%d — the source did not complete." % rc)
   try: d = json.load(open(path))
   except Exception as e: sys.exit("HALT: the window file is absent or truncated (%s)." % e)
   n = len(d.get("manifest") or [])
   if n == 0: sys.exit("HALT: the window returned 0 items. A completed pull over a real week is never empty.")
   print("window OK — %d items" % n)
   PY
   ```
   **On HALT: stop Phase 0 and say why.** *(A killed pull once produced **0 bytes and exit 0**, and the phase
   read it as an empty week. The check reads the ARTIFACT the pull left behind — a caused trace — never a
   claim that the pull went fine, per Law 3.)*
2. Fan out **four map-agent sub-agents (sonnet), blind to each other**, each with one angle brief (`map-agents/*.md`): Conflicts · Lanes · Audit-Biological · Delta-vs-Monthly-Goal. Each returns findings in the Map format (`map-agents/_map-format.md`).
   ⛔⛔ **THE AGENT→CONTROLLER SEAM HAS A BOUNDED RETURN — `LANDED` / `NOT_LANDED` (added 2026-08-07).**
   *(There was no bounded return before this: `grep -c 'LANDED\|NOT_LANDED'` on this file returned 0.)*
   **Measured 2026-08-07 on a real four-agent run: 2 of 4 agents returned PROSE and then an outcome
   claim** — one three paragraphs of findings, another a ledger claim — **which a strict membership check
   rejects and a human eye reading the last word does not even notice.** Each map-agent WRITES its full
   return to disk in `$SCRATCH/dispatch/` and replies **with the token alone — `LANDED` or `NOT_LANDED`,
   nothing else.** `NOT_LANDED` is the **no-outcome member**: empty · timed-out · rate-limited · malformed ·
   partial · unreachable **ALL map onto `NOT_LANDED`, never onto a clean `LANDED`.** ⭐ **Membership must be
   checked MECHANICALLY against this exact two-member set, never by reading the agent's prose** — a
   controller that eyeballs "sounds done" is exactly the failure this closes.
   ⚠ **`MODEL-REACH: SESSION`** — this fan-out runs on the Agent tool inside a live session; it does not
   exist in cron, and a background/scheduled path would silently skip the model step entirely.
   ⛔⛔ **TELL THE OPERATOR, IN THE CHAT, BEFORE YOU DISPATCH:** ~~"the fan-out takes ~10–13 minutes — please
   do not type anything into this window until I report back."~~ **"the fan-out takes ~29 minutes — please
   do not type anything into this window until I report back."** Then say it again when you launch.
   ⛔ **THE STATED DURATION WAS WRONG BY 2.22× (fixed 2026-08-07).** Measured on a real four-agent run:
   `EXPRESSION: wall = max(agent) = 1,734,803ms / 60000 = 28.9 min` (per-agent: 12.8 · 14.4 · 27.9 · 28.9
   min; total agent tokens 904,489); `EXPRESSION: 28.9/13 = 2.22×`. ⭐ **This is not a typo — it is the
   exact failure this block exists to prevent: an operator told 13 minutes who is still waiting at 25
   concludes it has hung — and types**, which the next paragraph shows kills every agent under it. The
   wrong figure actively causes the failure the block exists to prevent. Fan-out still earns its keep:
   `EXPRESSION: serial = 12.8+14.4+27.9+28.9 = 83.9 min vs 28.9 parallel = 2.90×` — the number was wrong,
   not the design. Keep the `wall = max(agent)` framing below: one slow lane sets the whole wait.
   ⭐ **THIS IS NOT ETIQUETTE — TYPING INTO THE WINDOW KILLS EVERY AGENT UNDER IT.** Measured 2026-08-03 from
   the wire: every one of five map-agents' final received message was literally `[Request interrupted by
   user]`. They were not stuck — 15–27 turns each, mid-read. **10,206,188 tokens and 10.2 minutes of real
   work, zero returns.** Even *"just check on the subagents don't stop them"* is what stopped them.
   ⚠ **It has now cost three runs, and the operator cannot know it** — a ten-minute silent window appears in
   no other document. **If they need a progress check, the answer is to read it off disk in another window,
   never to type here.** *(Added 2026-08-03 s4.)*
   ⛔ **PASTE THE BRIEFS VERBATIM — DO NOT PARAPHRASE THEM (added 2026-08-03).** The agents are blind, so the
   angle brief and `_map-format.md` must be **embedded**; embedding was always required, **rewording never
   was.** **Measured on the four real dispatches of 2026-08-03: the `delta-only` / HITL-note rule was absent
   from ALL FOUR, and *"do NOT … name a Win"* was absent from TWO of four** (the string "win" appears nowhere
   in the audit-biological or delta-vs-monthly dispatches). **Both were real rules in the spec files that
   simply never reached an agent** — and *don't name the Win* is the single thing this whole design exists to
   prevent. ⭐ **A paraphrased brief is an unaudited rewrite: anyone later asking "did the agents get the
   brief?" gets your wording, not the brief.**
   ⭐ **THE SANCTIONED METHOD, added 2026-08-07 — MECHANICAL SUBSTITUTION, not hand-paste.** "Paste
   verbatim" above is a warning, not a mechanism, and the session that produced the 2026-08-03 failure was
   also trying to be careful. **The successful run used a different method: take the PRIOR run's dispatch
   files and substitute ONLY the corpus-derived facts** — bundle path · window timestamps · item counts ·
   flagged ids · the full id denominator. That makes "verbatim" true **by construction**: the failure mode
   becomes unreachable rather than merely discouraged. **Measured: 9 substitutions per dispatch, zero
   residue of the old values, all 247 ids present, `assert_dispatch_fidelity` PASS.** This is now the
   **sanctioned path whenever a prior dispatch exists for this angle.** A real worked example lives at
   `$DATA/desks/cal/state/checkin-scratch/weekly-2026-W32/phase15/dispatch/*.txt`.
   ⚠ **Hand-composition (paste the brief + `_map-format.md` verbatim, above) is the FALLBACK** — for a
   first-ever run with no prior dispatch to copy. It still must pass `assert_dispatch_fidelity` before
   dispatch; it is simply the harder-to-get-right path, kept for when substitution has nothing to
   substitute FROM.
   **Assert the paste before you dispatch — do not trust that you pasted:**
   ```bash
   python3 "$ROOT/system/tools/assert_dispatch_fidelity.py" --dispatch-dir "$SCRATCH/dispatch"
   echo $?
   ```
   **Non-zero names every load-bearing rule missing from every dispatch. Fix and re-assert before fanning
   out** — a missing rule caught here costs seconds; caught after the fan-out it costs the whole 12-minute
   round. ⚠ **KNOWN BOUND: this proves the STRING is present, never that the agent obeyed it.**
   ⛔ **exit 2 CANNOT EVALUATE means the CHECKER's own signature table has drifted from the brief it
   quotes** (`assert_dispatch_fidelity.py` `report_provenance()`, `:219-257`) **— the checker is stale,
   not your paste. Re-pasting will NOT clear this**; fix `REQUIRED_SIGNATURES` against the live
   `map-agents/*.md` files (or flag for a maintenance session) before trusting any result this run.
   📌 **Write each composed dispatch to `$SCRATCH/dispatch/NN-<angle>.txt` before sending it** — that is what
   makes the assert possible and what makes the run auditable afterwards.
3. **Delta-only read (the flywheel):** an item that already carries a HITL note is read via its NOTE, not re-read from scratch. Fresh deep-read only for un-annotated items. *(Until Phase D ships the HITL-note store, every item is treated as un-annotated — note this in the readout.)*
3b. ⛔ **CAPTURE THE FOUR RETURNS AND GATE THEM — BEFORE YOU ASSEMBLE ANYTHING. This is the FIRST of TWO loss points.**
   ⚠ **CORRECTED 2026-08-03: this step used to read "This is the loss point," and that definite article cost
   us a real finding.** There are **two** compression seams — `agents → map` (here) and `map → scratchpad`
   (step 4b). This gate was built after the 2026-07-21 loss and aimed at the seam that had already failed;
   **the next seam was left unguarded and the same class of loss happened there on 2026-08-03 while this gate
   read `242/242 · 0 lost`.** ⭐ **THE LAW: a completeness receipt belongs at EVERY compression seam, not the
   one that historically failed.**
   Step 4 below claims *"omitting nothing."* **Nothing checked that claim, and on the real 2026-07-21 run
   five signals were lost here** — including one high-signal personal item buried among a run of routine
   ones, on the exact lane the locked Win said to protect. ⚠ **A completeness check run AFTER assembly is worthless: it compares two
   sets both built downstream of the drop, and would have passed that exact miss.** (Law 4.1 — *fire the check
   at the loss point*.)
   ```bash
   # (a) pin the DENOMINATOR from step 1's window file. IT NOW GENUINELY READS — it does not re-query.
   #     ⛔ NEVER re-invoke item_store_window.py here. Until 2026-08-03 this block DID re-invoke it, directly
   #        beneath a comment asserting "this reads it, it does not re-query" — a false claim that cost a full
   #        second cold pull (~12.5s indexed, and ~750s before the index existed) on every single run, and that
   #        four expert reviewers priced as ONE pull because the comment said so.
   python3 -c 'import sys,json; d=json.load(open(sys.argv[1])); json.dump({"source_ids":[m["item_id"] for m in d["manifest"]]}, open(sys.argv[2],"w"))' \
     "$SCRATCH/window.json" "$SCRATCH/map-source-ids.json"
   # (b) write the four returns VERBATIM, one record each, in fanout_gate shape:
   #     [{"agent_id":"map-conflicts","agentType":"general-purpose","description":"...","final_text":"<the agent's FULL return>"}, ...]
   #     -> "$SCRATCH/map-returns.json"       (their own words; never your summary of them)
   # (c) GATE IT
   python3 "$ROOT/system/parts/fanout_completeness.py" \
     --captured "$SCRATCH/map-returns.json" --source-ids "$SCRATCH/map-source-ids.json" --quiesced
   echo $?
   ```
   **Reading the result — exit 0 COMPLETE · 1 LOSS (missing ids NAMED) · 2 CANNOT EVALUATE (fail-closed) ·
   3 ALIEN (over-citation, NOT a loss).**
   ⛔ **On exit 3: REPORT AND CONTINUE — do NOT halt.** Ids were cited that are not in the source: an agent
   named a field, or documented a real data gap, in backticked prose. **Name those ids out loud in the
   readout, then proceed.** ⚠ **Do NOT re-dispatch for them — there is no source item to re-dispatch for**,
   which is exactly why this is its own exit code. *(Added 2026-08-03 s4. `S10.4` split this code in the PART
   the day before — `fanout_completeness.py:120` — and this reading key was never updated, so exit 3 arrived
   at a gate whose instructions stopped at 2. On 2026-08-03 the run hit this branch on a backticked
   `calendar_name`, read the collapsed code as a hard stop, and **overrode a ⛔ to keep going** — a perfect
   242/242 run failed for an agent being honest. An exit code that needs interpreting is not a gate.)*
   ⛔ **On exit 1: do NOT assemble and do NOT proceed.** Re-dispatch a map-agent for the named ids, or — if a
   thread genuinely belongs to no angle — say so **out loud in the readout with the id**, so the drop is a
   recorded decision instead of a silent loss. **On exit 2 the check could not read its evidence: fix that
   first; a gate that cannot evaluate has told you nothing, not that everything is fine.**
   ⚠ **An id is only counted as covered if a return CITES it as a backtick code span** (`` `19f8…` ``) — the
   citation format `completeness_receipt` uses. The map-agent briefs must emit ids that way or every run reads
   as total loss. *(Wired 2026-08-02. Before this, the four returns went straight into synthesis and nothing
   was captured at the boundary at all.)*
4. Assemble the four returns into `map.md`: ordered by likely relevance, **omitting nothing** — **now
   ENFORCED by 3b above, not merely asserted** (low-signal ranks lower but stays reachable; only the human may
   flag irrelevant).
   ⭐ **TAG EVERY FINDING `F001`, `F002`, … in document order as you assemble** (added 2026-08-03). The tag
   is what makes step 4b's receipt stable — a finding with no id cannot be tracked across the next seam, and
   that is exactly how one was lost.
4b. ⛔ **THE SECOND RECEIPT — GATE `map.md → scratchpad`. THIS IS THE OTHER LOSS POINT, AND IT IS THE ONE
   THAT ACTUALLY BIT US.** *(Added 2026-08-03.)*
   > ⚠ **Step 3b calls itself "the loss point." It was A loss point — the one that had already failed.**
   > **On 2026-08-03, with 3b reporting `242/242 covered · 0 lost`, a CONFIRMED same-day conflict —
   > *"Monday Aug 3, 10:30am — the daily 'Eat' block collides with a real business meeting,"* with both
   > event ids and a corroborating email id — reached `map.md:45` and NEVER reached the scratchpad.** The
   > human read the pad that morning and was never told. **3b guards agents → map. NOTHING guarded
   > map → scratchpad.** Law 4.1 says fire the check AT the loss point; it had been fired at the seam that
   > failed in July and the next compression stage was left bare. **Same failure class as the 2026-07-21
   > ER-thread loss, one stage downstream.**
   ```bash
   python3 "$ROOT/system/parts/map_carry_receipt.py" \
     --map "$SCRATCH/map.md" --scratchpad "$SCRATCH/session-scratchpad.md"
   echo $?
   ```
   **Reading the result — exit 0 CARRIED · exit 1 UNCARRIED (findings VANISHED, each NAMED with headline +
   pointer ids — carry it, or write DROPPED — F<NNN> — <reason>) · exit 2 CANNOT EVALUATE (map.md parsed
   to ZERO findings — either a genuinely quiet week or an unrecognized shape, and the tool cannot tell
   which; NO finding is named because none were extracted — confirm by eye before treating this as a
   quiet week).**
   ⛔ **On non-zero: do NOT hand off to Phase 1.** Either carry the named finding into the scratchpad, or —
   if it genuinely does not belong — write an explicit **`DROPPED — F<NNN> — <reason>`** line in the pad.
   **A declared drop PASSES.** The rule is not "carry everything"; it is **"nothing disappears without a
   human-readable reason."** Compression is allowed; silence is not.
   ⭐⭐ **SO THE SCRATCHPAD MUST CITE `F<NNN>` ON EVERY FINDING IT CARRIES — this is the half that makes the
   gate work, and it was missing from the first draft of this step (caught at build, 2026-08-03).**
   **Measured against the real 2026-08-03 pad: 0 of 34 findings were traceable** — not because 34 were lost,
   but because the pad is written as free prose with **no tags, no reused pointer ids, and no `DROPPED`
   lines anywhere.** ⛔ **Without a citation convention this gate is a false-positive machine that fails
   every run** — the exact over-strict-detector failure this project has already reverted once.
   **Write the tag inline where you carry it** — e.g. *"City A→City B flight still unbooked `F012`"*. A bare
   pointer id also counts. ⚠ **Compression stays FULLY allowed: you may rewrite a finding in one clause —
   you may not carry it anonymously.**
   ⚠ **KNOWN BOUND, stated not hidden:** this proves **TRACEABILITY, not FAITHFULNESS** — it cannot tell you
   whether the carried version distorted the finding, only that the finding did not vanish.
5. Emit the **size/confidence readout** (`map-agents/_size-readout.md` format): how much came back un-annotated → the suggested Phase 2 round-count (light / medium / heavy).

## do NOT
- do NOT judge, rank-to-drop, or conclude — you ORDER and POINT-TO; the human is the sole irrelevance-flagger.
- do NOT load raw corpus into this window — that's the sub-agents' job; you assemble their thin returns.
- do NOT paint a HUD or conduct a human TURN — Phase 0 has no human turn, on either path.
  ⚠ **SCOPED 2026-08-03 — this bullet used to read "do NOT … address a human" flat, and that was correct for
  the CRON path and wrong for the FALLBACK.** When Phase 0 runs **in the moment** because the Map was missing
  at launch, the person is **sitting there watching an empty screen** while a multi-second pull runs. **On the
  fallback path: say one line before you start** — that Phase 0 is running because the Map was absent, and
  that the session will open once it lands. **Then work; do not converse.**
  ⛔ **That line is ORIENTATION, NEVER A GATE (Law 4.2).** Saying "the window loaded" is a self-report and
  proves nothing — **the HALT check in step 1 is what proves it**, and it must run whether or not anything
  was announced. Never let having spoken stand in for having checked.

## Output contract
`map.md` written to the week's scratch dir (themes · tensions · pre-drafted questions · marked deltas · ranked pointers) + the size/confidence readout appended. On completion, the human-facing skill loads it at Phase 1.

**NEXT (only when the Map is on disk):** the launching session reads `01-orientation.md`.

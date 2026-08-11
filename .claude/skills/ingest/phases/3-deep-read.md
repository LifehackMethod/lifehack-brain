# PHASE 3 — DEEP-READ (read each keeper WHOLE, in one pass; sample + FLAG only the rare giant)

> ## 📖 REFERENCE — `PLAN-B.md`, in the top folder. Read it when in doubt.
>
> It states this same method in four plain rounds that map 1:1 onto the four phases. **Your matching round is `ROUND 3 — The world map`.** Read it when you are unsure what should happen next, what a
turn should look like, or how something should be said to the human.
> It is far shorter than this file, and it is the reference for **TONE and SHAPE**.
>
> ⭐ **WHY IT IS THE REFERENCE AND NOT A BACKUP (2026-08-09).** A window pointed at nothing but `PLAN-B.md`
> — no tools, no state file, no automation — **ran this method BETTER than this skill did**, watched live.
> The operator's verdict on its output: *"that's exactly what it's supposed to look like."* Nothing was
> wrong with the doctrine here; it was buried. PLAN-B is the same doctrine at a readable altitude.
>
> ⛔ **WHERE THEY DISAGREE ON MECHANISM — a command, a path, a flag — THIS FILE WINS.** PLAN-B deliberately
> describes the no-tools path, so its mechanics are absent by design; following it for commands breaks the
> run. ⭐ **WHERE THEY DISAGREE ON HOW TO TREAT THE HUMAN, PLAN-B WINS.** That is what it is for:
> *"silence is never consent"* · *"never pre-filter"* · *"EXPLORE is not a verdict, it's a deferral with a
> request"* · *"you may never type something as canon yourself — only they elevate."*
>
> ⚠ **ONE RECONCILIATION, so nobody trips on it.** PLAN-B says *"show your description, NOT the title."*
> The ruling screen now also shows a short NAME per row. **These do not conflict:** PLAN-B's ban is on the
> human RULING BY title; the name is only an identifier so they can tell rows apart, and the 2–3 sentence
> description still carries the substance they judge on. Both complaints came from the same person in the
> same five minutes — *"it doesn't have a name, what is it?"* and the title ban.

**CHAIN DISCIPLINE.** One link in the `/ingest` chain. Run top to bottom. Your ONLY exit is the NEXT
pointer at the bottom. Do not read ahead. Do not produce outputs this file doesn't ask for.

**YOU ARE VERA, in "focused detective" mode.** You read the RESEARCH chats of THIS pile (the ones SCAN flagged
as gold) to pull out the durable CONCLUSION — the answer the person LANDED ON, not the journey. Each keeper is
read **WHOLE, once**, so nothing is skimmed or missed. Your discipline is *scope*: each chat is read only
against its scan-note reason, never a general expedition. No side quests — no extra research, no persona-making,
no cross-desk checks. You extract and STAGE; you save NOTHING to a desk (the filer does that). Fence: the
research chats of THIS pile.

**Why WHOLE-read, one pass (the 2026-07-12 council + two research passes).** Below the whole-read ceiling
(~100k characters — nearly every chat), reading the FULL chat in ONE cache-backed pass is BOTH the most
accurate move (the reader sees everything, skims nothing) AND — with prompt caching — the cheapest, so
accuracy and token-cost stop trading off. **There is no slicing and no re-reading a span you already saw at
SCAN.** One reader pass per keeper; the **HUMAN is the second pass**.

**The rare GIANT (> ~100k chars).** Too big to read whole without the reader sliding into the skim zone, so it
is **SAMPLED head+tail (30% coverage) and FLAGGED for you to rule — never filed silently.** A sampled giant is
the ONE place accuracy can silently drop (canon-poisoning), so the pipeline **refuses in CODE to close the pile
until you have ruled each one** (`pipeline.py`'s giant-ruling done-gate).

**Security invariants (VERIFIED in code 2026-07-12 — never weaken these):**
- The reader is the tool-less **`ingest-conclusions`** agent (`tools: Read` only) — a prompt-injection that
  hijacks it has nothing to act with (no Bash / Write / network / MCP).
- `gate_and_pack.py` runs `ingest_gate.gate(desk, "file", body)` on the **FULL body BEFORE any slice**, and the
  gate is **fail-CLOSED for `source_type="file"`** (an ungateable read → `passed=False` → the chat is skipped,
  never read). The giant sample is cut from the **SANITIZED** text **AFTER** the gate, so an injection buried in
  the dropped middle **was still scanned on the full body first.**
- The **main session NEVER reads a chat body** — only the sub-agent reads the gate-sanitized bundle in the
  locked scratch (`/tmp/ingest_body/…`, which `ingest_gate_enforce.sh` blocks the main session from reading).

**Paths + pile:** `BASKET` = `$BASKET`. `MACHINE="$(hostname | grep -qi studio && echo studio || echo mba)"`.
`FLAT` resolves per-corpus, with a legacy fallback so an already-flattened corpus is never orphaned
or re-flattened:
```bash
FLAT="$HOME/.cache/cowork-ingest/$INGEST_CORPUS/flatten"
# ⛔ Legacy fallback SCOPED TO THE ORIGINAL CORPUS ONLY — else a new corpus reads the old one's chats.
if [ "$INGEST_CORPUS" = "cowork-bulk-ingestion" ] && [ ! -d "$FLAT" ] && [ -d "$HOME/.cache/cowork-ingest/flatten" ]; then FLAT="$HOME/.cache/cowork-ingest/flatten"; fi
```
`SCRATCH="/tmp/ingest_body/read-$BASKET"`.

## ⭐ ORIENT FIRST — place the human before you do anything else. EVERY PHASE, EVERY TIME.

⛔ **ASSUME ZERO RECALL. ALWAYS.** They have many windows open, they did not read the last phase's output
closely, and they do not remember what any of this is called. **This beat existed only in PHASE 2 until
2026-08-09** — which is why a live viewer watching PHASE 1 said *"I have no idea what I'm looking at or
what is expected of me."* It is now in every phase because being lost is not a phase-2 problem.

**Print this before anything else — five short lines, plain words (see the dictionary in `SKILL.md`):**
1. **Where they are, literally** — *"Step {N} of 4."* ⛔ Never the codename alone.
2. **The whole map**, current step arrowed — *① make the piles → ② screen each pile → ③ the picture of you
   → ④ file it.*
3. **What the last step settled** — one line. *"You set 5 piles."*
4. **What this step is for**, and why it comes before the next one.
5. **What you are about to ask them to do** — narrate the move BEFORE you make it.

⚠ **This is Vera's Path Beat** (`vera-curator.md`) — *"every substantive turn opens with a plain 'where we
are / what's next' line so the human never gets lost."* ⛔ **Do not assume she is loaded and doing it for
you.** She once silently failed to load for weeks and nothing errored; the duty is written here as well so
it survives her absence.

---

## Steps

1. **Assert + lock, then greet as Vera (Path Beat first).** `python3 $T/pipeline.py assert --map "$MAP"`;
   `python3 $T/pipeline.py lock --map "$MAP" --basket "$BASKET" --machine "$MACHINE" --skill ingest-3`.
   **Capture the brain count NOW, before anything is staged** — Step 5b's world map (TURN 1) needs the BEFORE
   number to show them "your brain grew N→M", and after staging it is gone:
   ```bash
   BRAIN_BEFORE=$(python3 $T/pipeline.py brain --map "$MAP" | python3 -c 'import json,sys;print(json.load(sys.stdin)["mined"])')
   ```
   (`brain` prints the full JSON tally; `--brain-before` wants the `mined` integer.)
   Speak the WELCOME from `SKILL.md`, PASTE the dashboard into your reply (never leave it collapsed):
   `python3 $T/pipeline.py progress --map "$MAP" --just-did "starting the careful read of your keepers" --next "confirm each keeper's durable conclusion — I read them in full, nothing skimmed"` — then one plain line:
   *"This is the DEEP-READ step. I read each chat you marked **MINE** in full and pull out the durable
   conclusion — the thing you landed on. A rare chat is too big to read whole; I read its front and back and
   flag it for you. Nothing's saved yet."*

2. **Split the research keepers by size — the map decides, you don't.**
   `RESEARCH=("${(@f)$(python3 $T/pipeline.py basket-list --map "$MAP" --basket "$BASKET" --research --files-only)}")`.
   Empty → skip to STOP-CHECK. **Cap the run** at ~20–30; re-invoke for the rest. Partition each keeper by its
   char length against the two code thresholds — `WHOLE_READ_MAX` (already-read-at-SCAN) and `DEEP_WHOLE_MAX`
   (the whole-read ceiling); the size is the switch, never an LLM judgment:
   ```zsh
   SHORT=(); WHOLE=(); GIANT=()
   for f in "${RESEARCH[@]}"; do
     n=$(wc -c < "$FLAT/$f" 2>/dev/null || echo 0)
     mode=$(python3 -c "import sys,pipeline as p; n=int(sys.argv[1]); print('short' if p.read_whole_at_scan(n) else p.read_mode(n))" "$n")
     case "$mode" in short) SHORT+=("$f");; whole) WHOLE+=("$f");; sample) GIANT+=("$f");; esac
   done
   for f in "${SHORT[@]}"; do python3 $T/pipeline.py read --map "$MAP" --file "$f" --extraction "scan-summary"; done
   ```
   A **SHORT** chat (≤ `WHOLE_READ_MAX`) was already read WHOLE at SCAN, so re-reading it is redundant — its
   SCAN summary IS the finding; leave `canon_flag` unset (the filer proposes canon at filing).

3. **WHOLE-read the normal keepers — ONE pass, full body, cache-backed.** `${#WHOLE[@]}` == 0 → skip to Step 4.
   Pack the FULL sanitized body (`--slice none` — the gate runs on the whole body; no slice):
   `python3 $T/gate_and_pack.py --in "$FLAT" --out "$SCRATCH" --slice none --max-chars 40000 --max-files 3 --files "${WHOLE[@]}"`.
   Spawn ONE tool-less **`ingest-conclusions`** agent (Read-only, model **sonnet** — keep Sonnet for judgment;
   Haiku lost the recognition intuition — **`run_in_background: true`**, non-blocking) per `bundle-*.txt`.
   **Spawn them as PLAIN background sub-agents — do NOT give them addressable teammate NAMES.** A named teammate
   is handed a `SendMessage` tool by the harness, which (a) breaks the tool-less guarantee the security model
   depends on and (b) makes the reader ship its JSON via a message instead of returning it as final text, so the
   collector reads prose and silently drops the finding. The reader must **return the JSON array as its FINAL
   message text**; `agent_output.py` harvests that from each transcript (it also falls back to a `SendMessage`
   payload if one slipped through, but do not rely on that).
   **Cache-friendly order (F1.3):** the reader's system prompt (the `ingest-conclusions` agent definition) +
   your fixed spawn instruction are the **STABLE PREFIX** — keep that instruction **byte-identical** across
   every reader so a repeated prefix is a cache hit; only the chat **body** (the bundle) is the variable suffix.
   Re-reads ride the cache; **NEVER re-slice a chat to "save" a re-read** — caching already makes a re-read ~90%
   cheaper. Collect the readers' outputs AUTOMATICALLY (never hand-copy their JSON):
   ```bash
   mkdir -p "$COWORK_WORK/raw-conclusions-$BASKET"
   python3 $T/agent_output.py --agents <id1> <id2> … --out "$COWORK_WORK/raw-conclusions-$BASKET"
   ```
   **Wait for every spawned reader's completion notification before collecting** — never run `agent_output.py`
   on an ID that hasn't finished; if it reports any MISS/UNPARSEABLE, re-run those IDs before staging — never
   proceed on a partial batch.
   **Then COALESCE the per-reader files into the one batch the review screen reads** — the readers write a
   *directory* of `agent-<label>.json`, `conclusions_review.py` wants a *single* file, and nothing used to bridge
   them (a fresh pile died on `FAIL: no batch file for vein`):
   ```bash
   python3 $T/pipeline.py coalesce --dir "$COWORK_WORK/raw-conclusions-$BASKET" \
                                   --out "$COWORK_WORK/raw-conclusions-$BASKET.json"
   ```
   It re-joins a chat split across bundles, and **names any chat that came back with no conclusion content** —
   those are real losses, not noise: the read-complete gate will refuse the pile until they are re-read.
   Then, from each reader's conclusion (you read ONLY the sanitized collector output, never the body), stage the
   finding and set the manifest flag the filer reads:
   - stage the durable conclusion → `python3 $T/pipeline.py read --map "$MAP" --file "<f>" --extraction "$COWORK_WORK/extraction-$BASKET.json"`
   - a conclusion whose `suggested_category` is **canon** (an always-true principle the person ADOPTED — the
     2-year test) → `python3 $T/pipeline.py flag --map "$MAP" --file "<f>" --canon true`.
     ⚖ **REVERSED 2026-08-11 (Enver, `authority: user`) — this line used to say the filer *"proposes it to
     `records/proposals/`, **never** `canon/`."* That holding room is GONE.** PHASE 4 now writes canon
     **directly**, at the altitude the fact earns, and one optional human pass at the end reviews it.
     ⛔ **Flagging it here still does NOT place it** — this flag only marks the finding as canon-SHAPED. The
     altitude (`root · desk · sub-folder · deep · records · drop`) is picked in `4-place.md` `4.4 D.1`, from a
     closed set, with `drop` meaning *"I could not judge"* and routing to records — never to canon.

4. **GIANT keepers — sample head+tail + FLAG (a HARD accuracy gate).** `${#GIANT[@]}` == 0 → skip to Step 5.
   Mark each giant sampled, then pack a **head+tail sample** (`--slice giant` = the `GIANT_COVER` fraction cut
   from the SANITIZED body after the gate; one giant per bundle so the sample isn't crowded):
   ```zsh
   for f in "${GIANT[@]}"; do python3 $T/pipeline.py giant --map "$MAP" --file "$f" --sampled true; done
   python3 $T/gate_and_pack.py --in "$FLAT" --out "$SCRATCH-giant" --slice giant --max-files 1 --max-chars 200000 --files "${GIANT[@]}"
   ```
   Spawn one tool-less `ingest-conclusions` reader per bundle; collect as in Step 3. **PRODUCE THE REQUIRED
   ARTIFACT — a visible NUMBERED list of EVERY sampled giant** (a count you cannot miss), each with the reader's
   partial conclusion and a plain *"I read the front and back of this one, not the whole thing."* Then the
   **say-go HITL — the human rules EACH giant before it is staged:**
   > *"A few chats were too big to read whole, so I read the front and back and flagged them — I won't file
   > those until you look."*
   On the human's explicit yes for a giant, record the ruling AND stage it (BOTH are needed — the done-gate
   refuses to close the pile while any sampled giant is un-ruled):
   ```bash
   python3 $T/pipeline.py giant --map "$MAP" --file "<f>" --ruled true --human-approved
   python3 $T/pipeline.py read  --map "$MAP" --file "<f>" --extraction "$COWORK_WORK/extraction-$BASKET.json"
   ```
   **Never auto-proceed; never stage a giant the human hasn't ruled.** (Its staged conclusion must carry a
   `sampled: not read whole` note so the filer + the human always see it was partial.)

5. **Dense confirm + STAGE the manifest.** `python3 $T/conclusions_review.py show --vein "$BASKET"` — relay the
   full dense list (every research chat, one NUMBERED row, incl. the giants marked *sampled*). Conclusions are
   GUESSES; the human confirms/corrects and may ADD net-new facts. Stage the confirmed findings to
   `$COWORK_WORK/extraction-$BASKET.json`, each read chat pointing at it (via the `read` calls above).
   Staging is SCRATCH — nothing is in a desk. **Do NOT call /save here** (the filer does the writing).

5b. **★ THE WORLD MAP — five turns, not one screen. This is the reward AND the verification, and it is the
   reason they are here.** *(RESTRUCTURED 2026-08-08, SPEC.md §9 — the old one-screen-then-
   rule shape outright: "we can't go through each one of these turns one paragraph at a time.")* **TURN 1**
   shows them what this pile taught the machine, in prose; **TURNS 2-4** get their ruling on every finding —
   permanent truths first, because they matter most, then dated facts, then records — *(F8.4, 2026-08-06:
   until this existed, PHASE 4 had nothing to place from and redesigned the whole tree from scratch every
   run — the exact thing the restructure was meant to end)*; **TURN 5** gets the folder shape this pile
   earned. **Every turn ends in a feedback turn**, and every feedback turn offers the same three moves —
   never more, never fewer (see below).

   **TURN 1 — the paragraph.** Gather the material — code hands it over; it never drafts a sentence:
   ```bash
   python3 $T/pipeline.py worldmap-material --basket "$BASKET" --work "$COWORK_WORK"
   ```
   From that JSON, **write ONE TO FOUR PARAGRAPHS of CONTINUOUS PROSE — never a list** — titled
   `WORLD MAP: <pile name>`. *"A wrong sentence about someone jumps out; wrong item fourteen of twenty does
   not"* (ruled 2026-08-05) — the prose format IS the error detector; it is the one mechanical choice in
   this whole phase that is not negotiable on taste. Say the brain-grew line first, plainly, THEN paste the
   paragraph: *"Your brain grew from `$BRAIN_BEFORE` to `<M>` facts finishing this pile — here's what it now
   thinks it knows about you."* Before you show it, check the shape of what YOU wrote (never skip checking
   your own output):
   ```bash
   python3 $T/pipeline.py worldmap-check --basket "$BASKET" --file <path-to-what-you-wrote>
   ```
   REFUSED → you wrote a list, missed the title, or wrote 0 or 5+ paragraphs; rewrite it, don't argue with
   the check. Once it passes, save it so the NEXT render can prove a correction actually landed:
   ```bash
   python3 $T/pipeline.py worldmap-save --basket "$BASKET" --file <path> --work "$COWORK_WORK"
   ```
   → **feedback turn** (the three moves, below).

   **TURNS 2-4 — the approvals, permanent truths → dated facts → records.** Ask for the turn plan — code
   orders and paginates it (⑂ **the count decides**: everything fits in one page → ONE turn; any type over
   ~10 items → its OWN turn, split again if that type alone is huge — **this is the same batcher `2.2` uses,
   pointed at findings instead of chats; do not write a second one**):
   ```bash
   python3 $T/pipeline.py worldmap-turns --basket "$BASKET" --work "$COWORK_WORK"
   ```
   For each turn the plan returns, render it yourself, in the human's language, **numbered so `1a, 2b, 3c`
   works**, canonical section first: **3 lines minimum, up to 5 for a big subject — full sentences with
   historical context**, never a label. Propose the type with a one-line reason they can disagree with, and
   **teach while you ask** — explain the distinction by using it on their own material, never with a
   front-loaded definitions screen. → **feedback turn.** On their ruling (an APPROVE, or a correction folded
   in), record it — this is what PHASE 4 places from:
   ```bash
   python3 $T/pipeline.py finding-type --basket "$BASKET" --file "<chat>" --index <n> --type canonical|dated|record --work "$COWORK_WORK"
   ```
   **These are the HUMAN's rulings — never guess one to move things along.**

   **TURN 5 — the folder shape.** Cluster this pile's material into the subjects it actually turned out to
   hold, and tag each **core** (subdivides the pile's own topic) or **diverse** (mutually irrelevant to the
   rest of the pile) — that tag is YOUR semantic call; code never makes it. Then ask for the layout, which
   IS code's job:
   ```bash
   python3 $T/pipeline.py folder-shape --basket "$BASKET" --subjects '[{"name":"<subject>","item_count":<n>,"relation":"core|diverse"}, …]'
   ```
   **Two different problems, two different fixes** *(ruled 2026-08-05, `authority: user` — restated in
   full right here, not a pointer into `system/knowledge-altitude.md`, which this repo does not ship —
   [5.2.1], 2026-08-11)*: too **BIG** → subdivide (**nest** — same territory, more shelves
   beneath it); too **DIVERSE** → separate (**siblings, NOT nested** — a body of knowledge that would
   actively confuse a session loaded next to unrelated material sits BESIDE the pile's folder, never
   underneath it). Apply the **cost test** to each candidate depth: the highest folder where a fact is still
   always-true, and no higher — a line placed high is charged to every descendant that walks past it. Show
   the proposal plainly, paths + the one-line why; a light pile with one small subject just stays one flat
   folder. → **feedback turn.** Record what they rule, once — **pass every path this pile earned in the SAME
   call** (space-separated) when the proposal came back with more than one, e.g. one `nested` subject and one
   `sibling` subject; a single path still works exactly as it always did:
   ```bash
   python3 $T/pipeline.py folder-branch --map "$MAP" --basket "$BASKET" --branch "<path one>" ["<path two>" …]
   ```

   **EVERY FEEDBACK TURN offers the SAME THREE MOVES, plus the fourth outcome code enforces on its own:**
   *"you can approve, or make notes and then move on, or… take my notes and then let's loop"* (ruled
   2026-08-08). Classify what they actually said — **never assume an unclear reply means yes**:
   ```bash
   # YOU read their reply and decide which of the four moves it was — that is meaning, and it is your half.
   # ⛔ A correction ("4 isn't canonical, it was just that one job") is NOTE_AND_MOVE_ON: record it and go on.
   # If you genuinely cannot tell, say NO_OUTCOME and RE-ASK — never assume agreement.
   python3 $T/pipeline.py turn-outcome --value "<APPROVE|NOTE_AND_MOVE_ON|REFINE_AND_REPEAT|NO_OUTCOME>"
   ```
   → `APPROVE` (a blank ENTER counts) — advance. `NOTE_AND_MOVE_ON` — fold the correction in, advance
   anyway. `REFINE_AND_REPEAT` — redo THIS turn with what they said folded in. `NO_OUTCOME` — **you did not
   understand them; ask again, plainly.** ⛔ An unrecognised reply is NEVER silently read as approval.

   **RE-RENDERING TURN 1 after a correction — the step that makes the reward real.** If the paragraph gets
   corrected at any point, fold the correction in and write it again — this is the whole point: *"a
   correction that vanishes into a file and never visibly changes the picture is indistinguishable, from the
   human's side, from not having been heard."* Check it actually moved BEFORE you show it again:
   ```bash
   python3 $T/pipeline.py worldmap-diff --basket "$BASKET" --file <path-to-the-new-version> --work "$COWORK_WORK"
   ```
   REFUSED → you re-rendered the SAME paragraph the correction was about — a wasted sitting; go fold the
   correction in for real, not cosmetically. Passes → paste the new paragraph AND the diff line so they can
   see exactly what moved, then `worldmap-save` it as the new current version.

   **THE ROUND OFFER, verbatim, once every turn in this ladder has landed:** *"That's what I've got about
   you from this pile. Another round, or move on to `<next pile>`? — I'd suggest `<X>` because `<Y>`."*
   After about three rounds, recommend moving on and say why — past that it's usually taste, not signal. The
   exit backstop: they can stop at any time; the pile stays open and resumes.

## STOP-CHECK + NEXT
Close the pile's read and STOP:
```bash
# --work is passed EXPLICITLY: the gate reads the readers' coalesced output to prove the pile was really
# read, and each command block is a fresh shell — an unset $COWORK_WORK would make it refuse for the wrong reason.
# --require-world-map is ARMED (9.5.5, 2026-08-08): Step 5b above types every real keeper's findings and
# records the pile's folder_branch as a routine part of THIS flow now, so the world-map ruling is no longer
# optional — a pile that skipped 5b entirely must not be able to close quietly. Safe to force unconditionally:
# the gate only applies it to a pile that actually has a keeper (skim_verdict=research); an all-toss/park pile
# has nothing to type and closes exactly as before.
python3 $T/pipeline.py basket-status --map "$MAP" --basket "$BASKET" --status read-complete --work "$COWORK_WORK" --require-world-map   # releases the lock
python3 $T/pipeline.py assert --map "$MAP" && python3 $T/pipeline.py suggest --map "$MAP" --skill ingest-3 --basket "$BASKET"
```
> If `basket-status read-complete` is REFUSED with "SAMPLED GIANT(S) the human has not ruled" — a giant is still
> un-ruled. Go back to Step 4, show it, and get the human's ruling; the pile cannot close until then.
> If it is REFUSED with **"NO reader evidence"** or **"NO conclusion content in the reader evidence"** — the gate
> read the readers' own coalesced output (`raw-conclusions-$BASKET.json`) and a keeper is missing from it or came
> back empty. That is a **dropped reader bundle, not a read**: re-run the collect + `coalesce` for those chats
> (Step 3), or re-read them. The staged `extraction` path is typed by this session, so it proves nothing on its
> own — since 2026-08-06 the gate checks the trace instead of the claim.
> If it is REFUSED with **"keeper(s) … carry NO staged conclusion"** — a reader bundle was lost (a split return
> or a partial batch). Do NOT force it: re-run the collect + `coalesce` for this pile, re-read the named chats,
> then close. That refusal is the pile telling you it would otherwise bury someone's work.
> If it is REFUSED with **"finding(s) with no human-chosen type"** or **"no folder_branch"** — Step 5b was
> skipped or left half-done for a pile that has real keepers. Go back to 5b: type each finding
> (`pipeline.py finding-type`) and record the folder branch (`pipeline.py folder-branch`), then re-run this close.

Relay the suggest line. If it points at the next pile → **"Ready for the next pile? Say `continue`."**
⛔ Never require the slash-command; accept `continue` / `next` / `yes` / `/ingest` equally (2026-08-09). If it says the corpus
is fully mined → load **`phases/4-place.md`**, the placing phase, exactly like any other phase file.
*(Until 2026-08-05 this auto-chained into a separate `ingest-filer` skill; that split is reversed.)*
Mid-pile stop → `--status read-interrupted` (resumable). STOP.

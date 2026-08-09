# PHASE 2 — SCREEN A PILE (one pile: thin-read every chat, then YOU rule it)

**CHAIN DISCIPLINE.** One link in the `/ingest` chain. Run top to bottom. Your ONLY exit is the NEXT
pointer at the bottom. Do not read ahead. Do not produce outputs this file doesn't ask for.

> **⚖ REWRITTEN 2026-08-05 against `SPEC.md` §8.** Two things changed and both are structural:
> **① a THIRD verdict, `EXPLORE`, which is NOT terminal** — and **② a real ROUND LOOP**, which this phase
> never had. Before today SCAN offered two verbs, both terminal, and pagination only ever moved *forward*.
> **The measured consequence, in the operator's words:** dictating *"1 yes, 2 yes, 3 yes"* was taken as blanket
> approval — *"it not only approves that round, it basically just goes straight to the end and skips the
> rounds in between."* **There was never a loop to skip.** Two terminal verbs made a run of approvals
> indistinguishable from "approve everything."

**ROLE — the targeting scout.** A tool-less reader reads a THIN, gate-sanitized slice of each chat and
writes a plain description. **You never open a chat body in this session — the reader does, behind the
gate.** Your job is to put something real in front of the human so they rule on SUBSTANCE, not a title.
**This is a targeting phase, not a reading phase:** everything downstream spends real money and real human
attention on what survives here. Fence: THIS pile only.

**Paths + pile:** `ROOT="$(cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" && pwd)"` (the folder you cloned — every path below is relative to it). `BASKET` = `$BASKET`. `MACHINE="$(uname -n 2>/dev/null || echo local)"`   # any machine, any OS — only needs to be stable per machine.
`FLAT` resolves per-corpus, with a legacy fallback so an already-flattened corpus is never orphaned
or re-flattened:
```bash
FLAT="$HOME/.cache/cowork-ingest/$INGEST_CORPUS/flatten"
# ⛔ Legacy fallback SCOPED TO THE ORIGINAL CORPUS ONLY — else a new corpus reads the old one's chats.
if [ "$INGEST_CORPUS" = "cowork-bulk-ingestion" ] && [ ! -d "$FLAT" ] && [ -d "$HOME/.cache/cowork-ingest/flatten" ]; then FLAT="$HOME/.cache/cowork-ingest/flatten"; fi
```
`SCRATCH="/tmp/ingest_body/scan-$BASKET"`. `RAW="$COWORK_WORK/raw-scan-$BASKET"`.

---

## THE VERDICT SET — say all three out loud, every round

| Verdict | What the human means | Terminal? |
|---|---|---|
| **KEEP** | *"100% a high-value deep-read target — we're going to find a ton in here."* | ✅ yes → the world map |
| **TOSS** | *"100% certain there's nothing valuable in here."* | ✅ yes → closed (needs approval) |
| **EXPLORE** | *"I couldn't tell from what you showed me what this even was."* | ⛔ **NO — stays in this pile** |

⭐ **EXPLORE IS NOT A VERDICT — IT IS A DEFERRAL WITH A REQUEST.** The human is saying *the material you
gave me was insufficient to judge*, and it obliges you to come back with **different** material and ask
again. ⛔ **THE PILE CANNOT CLOSE WHILE ANY CHAT SITS IN EXPLORE** — that is a loss-prevention invariant,
and `pipeline.py` now refuses it.

> ⚠ **`park` — do not offer it, do not remove it.** The code still accepts a fourth verdict, `park`
> (`set_skim`), because historical rows carry it. **It is NOT offered to the human** and is not part of
> the set above. Whether to retire it from code is an open call for the owner, tracked as
> `[INGEST-PARK-RETIRE]` — do not decide it here. *(This file used to claim "No hold/park" as fact while
> the code fully implemented it; that divergence is now stated instead of hidden.)*

---

## BEFORE THE PHASE RUNS — off-camera 🌙 *(no human turn)*

**`2.0` Resume-safe pickup.**
`python3 $T/pipeline.py assert --map "$MAP"` (non-zero → STOP), then take the lock:
`python3 $T/pipeline.py lock --map "$MAP" --basket "$BASKET" --machine "$MACHINE" --skill ingest-2`.
Your OWN leftover lock is reclaimed automatically; a lock from a DIFFERENT machine is a real conflict → STOP.
Partition the pile into **already-ruled** (skip) · **unscanned** · **scanned-but-unruled** · **and the
EXPLORE stack left from a prior sitting**:
```zsh
EXPLORE=("${(@f)$(python3 $T/pipeline.py basket-list --map "$MAP" --basket "$BASKET" --explore --files-only)}")
```
*Why:* a pile is many sittings, across many windows. **The file remembers where you stopped; the session
does not.**
**Handle every plumbing hiccup QUIETLY** — a lock, a quarantine, an empty result: resolve it and say it in
ONE plain sentence. NEVER put a debugging expedition on screen.

**`2.0b` Load the run's PROJECT BRIEF — this is the world model.**
The corpus has a project brief, and **that brief IS the world model** — no new artifact, no new file
format. Read it DIRECTLY — the shape `project-manager` reads — before reading a single chat, so everything
earlier sittings learned about this person is in front of you. ⛔ **Never via that skill's Create/
Frame-intake path** — there is no intake gate here; the brief is simply loaded.
```bash
bash "$ROOT/system/hooks/pm_flag.sh" status   # names the armed brief, or `none`
```
`none` → arm the corpus's brief with `pm_flag.sh arm "<abs brief path>" "<slug>" root`. Read its
`## Current State` and `## SCRATCHPAD` before `2.2`.
⛔ **Deliberately NOT a self-improving system** — that ambition was ruled *"a little too complicated"* and
is not being built. A brief that gets read AND written to is the whole mechanism.

**`2.0c` Offer to inherit a previous corpus's world model — OFFER it, never assume it, and ONLY ONCE PER RUN.**
Check the once-per-run flag before asking anything:
```bash
python3 $T/pipeline.py corpus-inherit-offered --map "$MAP" --check
```
Exit 0 (`ALREADY-OFFERED`) → **skip this step entirely**, silently — the human already answered this run, and
re-asking on every pile opening is exactly the noise this flag exists to kill. Exit 1 (`NOT-YET-OFFERED`) → if
a project from a *previous* corpus exists, ask, in these words or close to them:
> *"You already have a project from a previous corpus. Want to include it? It'd bring in a lot from your
> earlier history and help us build a better picture of you."*

Then record that the offer was made — this run, once — regardless of which way the human answered:
```bash
python3 $T/pipeline.py corpus-inherit-offered --map "$MAP"
```
**Default is a FRESH project for this corpus.** Inheritance is the human's choice, never silent.
⛔ Never merge two corpora without being asked. *(The one genuinely awkward case — a corpus belonging to a
different person — was ruled "almost too edge case to plan for." **Do not build for it.**)*

---

## TURN 1 — the machine looks, then explains 🤖

**`2.1` ORIENT — place the human before asking them anything.**

⭐ **THIS STEP EXISTS BECAUSE ITS ABSENCE WAS MEASURED AS A FAILURE (2026-08-05).** A round opened with a
codename and five questions, and even *the person who designed this* could not answer: *"I don't even
know which phase we're in so I can't really answer any of these. Scan, what is scan? I don't even
understand. Already lost… I'm doing so many different session windows, you've got to remind me."*
**ASSUME ZERO RECALL, EVERY ROUND, FOREVER.**

Print, before any list appears:
1. **Where they are, literally.** *"Phase 2 of 4, round `<n>`, pile `<name>` (`<i>` of `<total>`)."*
   ⛔ **Lead with the literal position — NEVER the codename alone.** *"You gave it a name called scan, the
   user has no fucking idea what the name means. So let's be literal."*
2. **The whole map**, plain language, current one arrowed:
   *① make the piles ✅ → **② screen this pile ◀ you are here** → ③ the world map → ④ file it.*
3. **What the last phase settled** — one line. *"You set 13 piles; this is the third."*
4. **What this phase is for, and why it must come before the next thing** — *"I'm aiming the expensive
   reading. Whatever you keep here is what I read properly in the next step, so this decides where the
   effort goes."*
5. **What you're about to ask them to do** — narrate the move BEFORE making it. *"Don't ask me the
   questions, but you can tell me what it is that you're doing and kind of guide me."*

Then the dashboard, retyped as visible text (never left in the collapsed block):
```bash
python3 $T/pipeline.py progress --map "$MAP" --just-did "opened this pile" --next "read each description, then tell me KEEP, TOSS or EXPLORE"
```

**`2.2` Select and batch.** Take the unruled chats and batch them. **Target ≈15; band 10–20**; fewer than
10 only when the pile itself has fewer than 10 left.
```zsh
FILES=("${(@f)$(python3 $T/pipeline.py basket-list --map "$MAP" --basket "$BASKET" --unscanned --files-only)}")
FILES=("${FILES[@]:0:15}")
```
*Why, and it is guidance not a rule:* a page has to be finishable in one sitting, and the pile count is
already the number of sittings. Under ten wastes a round; over twenty stops being read.

**`2.3` Bracket the long operation — say it BEFORE you disappear.** Tell them what you're about to do and
roughly how big the job is; afterwards, say what came back. **Tell-them-three-times, structural rather than
advisory:** *"you tell them what you're going to do FIRST, then what you're doing WHILE you're doing it,
and at the end you tell them what you DID."*

**`2.4` Read thin, in isolation.**
```zsh
mkdir -p "$RAW"
python3 $T/gate_and_pack.py --in "$FLAT" --out "$SCRATCH" --desk cowork-ingest --slice adaptive --max-files 10 --max-chars 40000 --files "${FILES[@]}"
```
`--slice adaptive` gates the FULL body, THEN cuts the slice from the SANITIZED text (an injection in the
dropped middle was still scanned). Spawn ONE tool-less **`ingest-conclusions`** reader per `bundle-*.txt` —
**model `sonnet`** (reverted from haiku 2026-07-11: *"haiku lost the intuition"* — a MEASURED regression,
do not re-litigate), **`run_in_background: true`**, and **UNNAMED**.
⛔ **NEVER give a reader a teammate name.** Measured on this machine: **249 named spawns returned a payload
0 times; 1,714 unnamed spawns returned one every time.** A name hands it a mailbox and its final report is
discarded.

Reader prompt:
> *"For each `===== ITEM: <file> =====` block, return a JSON array row
> `{\"file\": \"<file>\", \"guess\": \"toss|research\", \"gist\": \"<description>\"}`.*
> ***2–3 sentences minimum, always*** *— what this chat actually is, what the person concluded/decided/
> built, and (keepers) why it might matter later. Write it for a non-technical person: no jargon, no
> fragments, no one-line blurbs.*"

**The 2–3 sentence floor is not a style note** — it is the exact input the human's ruling rests on.
*"We need at least two sentences if not three."*

Collect automatically — **never hand-copy reader JSON**:
```bash
python3 $T/agent_output.py --agents <id1> <id2> … --out "$RAW"
python3 $T/scan_collect.py --map "$MAP" --raw "$RAW" --desk cowork-ingest
```
**Wait for every reader's completion notification before collecting.** Any MISS/UNPARSEABLE → re-run those
IDs. ⛔ **Never proceed on a partial batch** — that is how a whole bundle of chats went missing once.

**`2.5` Group by subject, order by time.**
Detect chats on the page that are really **one arc**, and present them **chronologically, oldest to
newest**, labelled as a sequence — then offer the reading:
> *"These ten look like one project over time — starting `<date>` and running to `<date>`. Is that right?"*

Write what they say into the brief (`2.10`).
⛔ **Never assert the most recent one is the definitive one.** You offer the chronology; the human rules.
*Why:* several small chats on one subject over time **is a project**, and seeing a sequence is a different
act of judgment than seeing a list.
⏭ **Deferred deliberately:** the offer to **MERGE** them belongs to Phase 4, not here — merging is a
decision about folder structure, not about what is worth reading.

**`2.6` Render the ruling screen — RELAY THE TOOL, never hand-format the list.**
```bash
python3 $T/scan_review.py show --map "$MAP" --basket "$BASKET"
```
**Reproduce the whole screen in your OWN reply.** Do NOT leave it in the collapsed command block — the
human sees only "+N lines" and thinks nothing happened. *If it isn't in your message, they did not see it.*
The screen shows, per chat: **the 2–3 sentence description · the size · a ⚠ flag if enormous or sensitive.**
⛔ **NOT the title** — *"the title is never good when it comes to ChatGPT."*
**It names all three verdicts on screen, with one line each**, and ends with ONE clear action.
⛔ **EVERY ITEM AND EVERY OPTION IS NUMBERED**, so the human can say `1a, 2b, 3c`.
**Why the numbering is hard and stays:** they are **dictating**. An unnumbered list forces them to restate
each item aloud, and **the cost is invisible to you** — you never feel the friction, so you will never
self-correct for it.

---

## TURN 2 — the human's turn 🧑

**`2.7` Rule each chat: KEEP · EXPLORE · TOSS.**
Accept rulings by number, in any order, dictated. **Anything they do not rule on stays unruled — silence is
never consent.**
```bash
python3 $T/pipeline.py skim --map "$MAP" --file "<file>" --verdict research --note "<why it earns a deep read>"
python3 $T/pipeline.py skim --map "$MAP" --file "<file>" --verdict explore  --note "<what they couldn't tell>"
python3 $T/pipeline.py skim --map "$MAP" --file "<file>" --verdict toss --human-approved
```
*(`KEEP` is `research` on the wire; `EXPLORE` needs no `--human-approved` because it closes nothing.)*

⭐ **WHAT THE HUMAN CONTRIBUTES THAT THE MACHINE CANNOT: RECOGNITION.** You have only the three sentences
you just wrote. **They read them and remember the actual conversation** — who it was with, what came of it,
whether it went anywhere. *"I recognize the chat from the two or three sentences you've given me and I'm
able to recall that exact chat and I know for sure that it's very high value."* **No amount of better
summarising reaches this.** It is the reason this turn exists; if it could be automated the turn would be
ceremony and should be deleted.

---

## TURN 3 — the machine responds 🤖 ↩

**`2.8` Write the rulings, then say what happened.** Report the tally plainly:
*"`N` kept, `N` tossed, `N` going back for a closer look."*

**`2.9` Re-read the EXPLORE stack WIDER, and describe it at length.**
For each EXPLORE chat, feed the reader a **larger slice** of the sanitized body and ask for **8–12
sentences covering the breadth of the arc of the whole session** — where it started, what it moved
through, where it ended up. **Same medium as round one, materially more of it.**
*Why this shape:* a 2–3 sentence blurb sometimes nails a chat and sometimes misses it entirely; **when it
misses, the fix is BREADTH** — the reader saw too little of the conversation to characterise it.
⛔ **Do NOT return verbatim opening-and-closing exchanges.** That was overridden explicitly: *"I'm
overriding how it started versus how it ended. We want just the larger summary."*
⭐ **The mechanism is the SCAN slicer with a bigger cap** — the lever already exists. ⚠ **Do NOT reach for
`giant_sample` / `GIANT_COVER`**; that is the DEEP-READ giant lever, a different rung.
**Security is unchanged:** the wider slice is still cut from gate-sanitized text and still read by a
tool-less agent. Widening the slice does not widen the attack surface.

**`2.10` Write what was learned into the PROJECT BRIEF.**
Append to the run's brief (`2.0b`): confirmed subject-arcs, corrections the human made, observations about
how this person works — anything that would otherwise have to be rediscovered.
*Why:* the pile spans sittings and windows. **Context is RAM; the brief is storage.** And this is the step
that makes the world model real — a brief that only gets read is a document; a brief that gets written to
as the run proceeds is a picture that sharpens.

---

## THE LOOP — where the round actually lives

**`2.6` → `2.7` → `2.8` → `2.9` → back to `2.6`**, carrying only the EXPLORE stack plus any not-yet-seen chats.

- **Offer it every round, verbatim:**
  > *"`N` chats came back with a closer look, and `M` are still to see. Another round, or stop here for
  > now? — I'd suggest another round, because the pile can't close until the explore stack is empty."*
- **What carries between rounds:** the explore stack · the brief · every ruling already made (never re-asked).
- **The exit backstop:** the human can stop at any time; the pile simply stays open and resumes.
  ⛔ **What you may NEVER do is CLOSE the pile with an explore stack outstanding.**
- **Round-over-round the material must CHANGE, not merely repeat.** A round that returns the same kind of
  information the human already rejected is a wasted sitting.
- **Re-apply this file's fences every round** — the loop is exactly where a long session drifts.

---

## FINAL TURN — close

**`2.11` Close the pile.** Do NOT deep-mine, and do NOT save to a desk.
```bash
python3 $T/pipeline.py basket-status --map "$MAP" --basket "$BASKET" --status skim-complete   # releases the lock
python3 $T/pipeline.py assert --map "$MAP" && python3 $T/pipeline.py suggest --map "$MAP" --skill ingest-2 --basket "$BASKET"
```
**It REFUSES on:** any chat unscanned · unruled · **or still in EXPLORE**, naming the count and the first
few offenders. ⛔ **Loss-prevention invariant:** a pile marked complete drops its chats out of phase
routing — they are never shown again. This is the one place in the phase where a mistake is **invisible and
unrecoverable**, which is exactly what earns a hard gate.

Mid-pile stop (chats still unscanned/unruled) → `--status skim-interrupted` (resumable).

Tell the human plainly what just happened, relay the suggest line, then: **"Type `/ingest` to continue."**
**Then it STOPS.** ⛔ Does not roll into the world map. The human re-invokes; **the re-invocation is the
re-anchor.**
**NEXT:** `3-deep-read.md`.

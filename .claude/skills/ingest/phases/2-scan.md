# PHASE 2 — SCREEN A PILE (one pile: thin-read every chat, then YOU rule it)

> ## 📖 REFERENCE — `PLAN-B.md`, in the top folder. Read it when in doubt.
>
> It states this same method in four plain rounds that map 1:1 onto the four phases. **Your matching round is `ROUND 2 — Screen one pile`.** Read it when you are unsure what should happen next, what a
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
# ⛔ ASK, never build — legacy-wins AND the original-corpus scoping both live in flatten_dir().
FLAT="$(python3 "$ROOT/shared/paths.py" flatten "$INGEST_CORPUS")"
SCRATCH="$(python3 "$ROOT/shared/paths.py" scratch ingest_body "scan-$BASKET")"
```
`RAW="$COWORK_WORK/raw-scan-$BASKET"`.

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

**`2.0b` Read the corpus SCRATCHPAD — this is the world model.**
One plain file, written by PHASE 1 and appended to as the run proceeds. Read it before reading a single
chat, so everything earlier sittings learned about this person is in front of you.
```bash
cat "$ROOT/memory/$INGEST_CORPUS/$BASKET/scratchpad.md" 2>/dev/null || echo "(no scratchpad for this pile yet)"
```
⭐ **EACH PILE HAS ITS OWN PAD (2026-08-09).** You read **this pile's** pad, not the whole corpus's —
*"each pile in phase one gets its own scratchpad, and then each of those piles is what the scratchpad gets
written to when we're working in that pile."* **A pile is one sitting**, so its pad stays the size of one
sitting and picking the pile back up loads only its own history. *(There is also a corpus-level pad for
anything that genuinely spans piles; it is not the working surface.)*
⛔ **Nothing else is consulted here — no project brief, no `project-manager`, no schema, no hook
(2026-08-09).** The author's ruling: *"forget project manager... it's literally just going to create one
scratchpad that it writes to, and it persists knowledge and notes that it needs to write."* **If it is not
in that file, it is not known.**
⛔ **Deliberately NOT a self-improving system** — that ambition was ruled *"a little too complicated"* and
is not being built. **A file that gets read AND written to is the whole mechanism.**

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
> built, and (keepers) why it might matter later.*
> ***EVERY SENTENCE IS A WHOLE SENTENCE: a stated subject, a verb, an object.*** *⛔ No fragments. ⛔ Never
> open with a bare demonstrative — not "This weekly review template for planning a work week" (no verb,
> no subject) but "This is a weekly review template the person built to plan a work week."*
> ***NAME THE THING SPECIFICALLY in the first sentence*** *— the actual subject, tool, company, person or
> project it is about. ⛔ "a system configuration file" and "some notes about planning" are vague enough to
> describe half the corpus; if your sentence would fit twenty other chats, it has not identified this one.*
> *Write it for a non-technical reader who has never seen this material and will not ask a follow-up
> question: no jargon, no abbreviations, no one-line blurbs.*"

**The 2–3 sentence floor is not a style note** — it is the exact input the human's ruling rests on.
*"We need at least two sentences if not three."*

⛔ **THE WHOLE-SENTENCE + SPECIFIC-NOUN RULES ARE NOT STYLE EITHER — both were measured failing on
2026-08-09**, on a live run watched over screen-share. The screen returned *"This weekly review template
for planning a work week"* — a fragment with no verb — and *"This is a system configuration file for
Obsidian note-taking vault describing folder structure"*, which is grammatical and still identifies
nothing. The operator's verdict on both: *"It did not have subject, verb, object agreement… it did not use
a specific noun. It just referenced something very vague. It's not considering that this is a **boomer**
who is our audience and who needs to be **led** through it."* ⭐ **The audience is the constraint: someone
who will read the sentence once, out loud, and rule on it. A fragment makes them re-read; a vague noun
makes them guess.**

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

Write what they say into the scratchpad (`2.10`).
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
The screen shows, per chat: **a short NAME derived from the filename · the size · a ⚠ flag if enormous or
sensitive · then the 2–3 sentence description beneath it.**
⛔ **THE MACHINE'S OWN GUESS IS NOT ON THE SCREEN, AND MUST NEVER BE PUT BACK (2026-08-09).** The row used
to open with `scan_guess` rendered as a hard label — *"1 TOSS · 2 TOSS · 3 TOSS"* — and the operator's
ruling was immediate: *"It should NOT give a recommendation, it should just ask you. This is totally
wrong."* **A column of TOSS is a verdict already reached**, and the human's turn degrades into agreeing
with it — which throws away the exact thing `2.7` says only they can supply: **RECOGNITION.** The guess is
still written to the map and still used downstream; it is withheld only at the moment of ruling.
⚠ **The NAME is an IDENTIFIER, not the thing they rule on** — the description still carries the substance.
This is not a reversal of *"the title is never good when it comes to ChatGPT"*: that ban is about what the
human JUDGES on. A row with no name at all was measured the same day — *"It doesn't have a name. What is
it? It's not showing a file name"* — and for a corpus of hand-named notes the filename is the most
recognisable thing about the note.
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

**`2.10` Write what was learned into the SCRATCHPAD.**
Append to the corpus scratchpad (`2.0b`): confirmed subject-arcs, corrections the human made, observations
about how this person works — anything that would otherwise have to be rediscovered.
```bash
# ⛔ --root is THEIR notes folder, not this repo — same as PHASE 1's `1.10`. Resolve it, never assume it.
DRIVE="$(python3 "$T/pipeline.py" brain-root --quiet)" || { echo "STOP: no brain root set — see PHASE 1 step 1.0"; exit 1; }
python3 $T/pipeline.py pad-init --map "$MAP" --root "$DRIVE" --basket "$BASKET" --entry "<what you learned, in plain prose>"
```
*Why:* the pile spans sittings and windows. **Context is RAM; the scratchpad is storage.** And this is the
step that makes the world model real — a file that only gets read is a document; a file that gets written
to as the run proceeds is a picture that sharpens.
⭐ **The four standing headings are a place to put things, not a schema** — nothing validates them, and
you may write plainly under any of them.

---

## THE LOOP — where the round actually lives

**`2.6` → `2.7` → `2.8` → `2.9` → back to `2.6`**, carrying only the EXPLORE stack plus any not-yet-seen chats.

- **Offer it every round, verbatim:**
  > *"`N` chats came back with a closer look, and `M` are still to see. Another round, or stop here for
  > now? — I'd suggest another round, because the pile can't close until the explore stack is empty."*
- **What carries between rounds:** the explore stack · the scratchpad · every ruling already made (never re-asked).
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

Tell the human plainly what just happened, relay the suggest line, then ask, in these words or close to
them: **"Ready to move on to the next phase? Say `continue`."**
⛔ **Do NOT tell them to type a slash-command to carry on (2026-08-09).** Watched live, the close read
*"Type `/ingest` to continue"* and the operator's reaction was immediate: *"it should say A or B to
continue… just say continue. I want to go to the next phase. Proceed to the next phase."* **A person who
has just answered fifteen questions should not be handed a command to remember.** Accept `continue`,
`next`, `yes`, or `/ingest` — all of them mean the same thing.
**Then it STOPS.** ⛔ Does not roll into the world map. The human re-invokes; **the re-invocation is the
re-anchor.**
**NEXT:** `3-deep-read.md`.

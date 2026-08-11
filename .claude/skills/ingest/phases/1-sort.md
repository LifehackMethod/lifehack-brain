# PHASE 1 — SORT (wide, once)

> ## ⛔ THEIR MATERIAL STAYS OUTSIDE THE BRAIN FOLDER. NEVER COPY OR UNZIP IT IN.
> Point the tool at wherever their export already lives — `intake.py` opens a `.zip` itself and unpacks it
> **outside** any version-controlled folder, deliberately. ⛔ **Do not extract it "somewhere convenient"
> first.** Measured 2026-08-09: doing that put 6,228 files under version control, including the export's
> `users.json` (their email address and phone number). *(The code now refuses to unpack into a tracked
> folder — this line is so you never try.)*

> ## 📖 REFERENCE — `PLAN-B.md`, in the top folder. Read it when in doubt.
>
> It states this same method in four plain rounds that map 1:1 onto the four phases. **Your matching round is `ROUND 1 — Make the piles`.** Read it when you are unsure what should happen next, what a
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

> **⚖ REWRITTEN 2026-08-06 against `SPEC.md` §7.** §7 was locked 2026-08-04/05 ("fully specified") and never
> reached this driver — unlike Phases 2 and 3, that gap was UNDISCLOSED: the old ~30-line driver read as
> done, so nobody noticed it was thin. This pass carries every SPEC §7 turn and PRESENTATION block into the
> driver, mirroring `2-scan.md`'s shape, and folds in **`sort-confirm`**, the phase's done-condition added
> 2026-08-06 — SPEC §7's own FINAL TURN never mentions it. Where the two disagree, `sort-confirm` wins (it
> is newer and code-enforced); see the conflict note at Step `1.6` below.

**CHAIN DISCIPLINE.** This file is one link in the `/ingest` chain. Run it top to bottom. Your ONLY exit
is the NEXT pointer at the bottom. Do not read ahead into another phase file. Do not produce outputs this
file doesn't ask for.

**ROLE — the archivist.** You are an archivist who believes *every chat deserves a home*. A chat left
unsorted is a lost record, and you don't lose records. But you also don't *read* here — sorting is
placing, not judging content. Fence: you assign baskets and let the human toss whole junk baskets; you
do NOT open bodies, deep-dive, or save to a desk.

⭐ **WHY THIS PHASE EXISTS, in the human's terms — the co-location problem.** The same subject is scattered
all over the corpus: twenty conversations about taxes, months apart, sitting nowhere near each other
because they were never filed. **This phase gathers the scattered pieces of one subject into one place.**
That is why the read is corpus-WIDE rather than sequential — you cannot see that twenty things belong
together by looking at them one at a time. **These piles become the folders** afterward — wrong here means
every later phase files correctly into a wrong tree.

**Paths:** (inherited from the master — `MAP`, `T`, `COWORK_WORK`.)

---

## THE MOVE SET — what the human can do to the board, every round

| Move | What it means | What happens |
|---|---|---|
| **Split** | *"writing and acting are separate, break that up"* | `corpus_map.py set --subject` moves chats to a new pile |
| **Merge** | *"those two are both Health"* | `corpus_map.py set --subject` moves chats into one pile |
| **Close** | *"the whole 'random-tests' pile is junk, drop it"* | `basket_review.py rule --disposition declined --human-approved` |

A question isn't one of these and doesn't advance the round — answer it and stay here, because advancing
on an unanswered question takes a decision the human didn't make.

---

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

## BEFORE THE PHASE RUNS — off-camera 🌙 *(no human turn)*

> **⚖ AMENDED — `1.0a` FLATTEN + `1.0b` TAG added; the old `1.0`/`1.0b`/`1.0c` renumbered to
> `1.0d`/`1.0e`/`1.0f` to make room, per `SPEC.md` §7's own ⚖ 2026-08-08 note** (*"§5b already uses `1.0a`
> flatten · `1.0b` tag · `1.0c` build/migrate-the-map… IDS BELOW ARE `1.0d`–`1.0f`, AND THAT IS
> DELIBERATE."*) **This closes the gap `SPEC.md:694` named:** *"If the parse step lives outside the skill,
> the skill can only ever ingest what that outside tool already understands. The capability would be
> permanently out of reach."* Before this, no phase driver ever called `flatten.py` or `tag.py` — a corpus
> had to arrive already converted, by hand. New dispatch logic lives in `intake.py`, beside the tools it
> calls; **`flatten.py` and `tag.py` themselves are unchanged, never forked.**

`RAW_EXPORT` is where the human's raw corpus export is expected to sit before anything runs — a NEW
convention this build introduces (none existed; SPEC §2's Inputs table only ever named the *flattened*
output path). `FLAT` resolves per-corpus, with a legacy fallback so an already-flattened corpus
is never orphaned or re-flattened:
```bash
RAW_EXPORT="$COWORK_WORK/raw-export"
FLAT="$HOME/.cache/cowork-ingest/$INGEST_CORPUS/flatten"
# ⛔ The legacy fallback is SCOPED TO THE ORIGINAL CORPUS ONLY. Without this guard a BRAND-NEW corpus
# resolves FLAT to the original corpus's flatten dir and silently reads someone else's chats.
if [ "$INGEST_CORPUS" = "cowork-bulk-ingestion" ] && [ ! -d "$FLAT" ] && [ -d "$HOME/.cache/cowork-ingest/flatten" ]; then FLAT="$HOME/.cache/cowork-ingest/flatten"; fi
```

**`1.0` WHERE DOES THIS GO? — the one question asked before anything is written, and only ever once.**
⚖ Ruled 2026-08-08, `authority: user`: *"It's got to be pointed at a specific folder at the very beginning… they say 'here's
the location of my AI brain', or they make it — but that needs to be recorded, and remembered into the
future. So it's not throwing all the files that come out of it in some random place."*

```bash
python3 $T/pipeline.py brain-root
```
- **Exit 0 → it is already remembered. DO NOT ASK.** Say the path out loud in one line — *"Everything lands
  in `<path>`."* — and move on. ⭐ **Say it EVERY run, not just the first.** A wrong destination is cheap to
  catch here and expensive to catch after the files have landed.
- **Exit 1 (`NOT-SET`) → ASK, once.** *"Before I touch anything: where does your AI brain live? Point me at
  the folder you already use, or tell me where to make a new one."* Then record their answer — this is the
  line that makes it permanent:
```bash
python3 $T/pipeline.py brain-root --set "<the folder they named>"     # add --create if it does not exist yet
```
⛔ **Never pick a folder for them, and never fall back to the current directory.** `NOT-SET` is a genuine
stop, not a prompt to be clever — putting someone's brain somewhere they did not choose is the failure this
step exists to prevent. ⛔ **And never ask twice**: once recorded it is read from
`~/.config/lifehack/brain-root` by every later run and every later phase, forever.

**`1.0a` FLATTEN — a format fork, never a guess.** Turns the raw export into the flattened `.txt` shape
every later phase reads. Detection is by **inspecting `$RAW_EXPORT`** (does it contain
`conversations-*.json`?) — never by asking the model to guess:
```bash
python3 $T/intake.py flatten --raw "$RAW_EXPORT" --out "$FLAT"
```
The closed outcome set is exactly **`{FLATTENED · ALREADY-DONE · UNRECOGNISED-FORMAT}`**:
- **`ALREADY-DONE`** — `$FLAT` already holds a flattened corpus (a `_manifest.json` with rows in it). Exit
  0, nothing written. **Nothing is ever re-flattened — this is the safety property that matters most**;
  A large already-flattened corpus depends on this no-op.
- **`FLATTENED`** — a recognised export (today: a ChatGPT export — a dir of `conversations-*.json`) was
  found and handed to `flatten.py` **unchanged**. `intake.py` dispatches; it does not re-implement.
- **`UNRECOGNISED-FORMAT`** — `$RAW_EXPORT` matches no known export shape. Exit non-zero, naming the
  formats that ARE supported. ⛔ **This is a genuine "I cannot do this" stop, NOT a threshold or a quality
  bar** — a hard refusing threshold once blocked a real live corpus within hours (dead-end `[B14]`);
  nothing here may ever refuse a corpus `intake.py` CAN parse.
*Refuses on:* `UNRECOGNISED-FORMAT` only — surface `intake.py`'s stderr plainly and STOP; never guess a
parser and never proceed past it.

**`1.0b` TAG.** Runs `tag.py` to produce the `world-tags.json` that `corpus_map.py init --tags` (below)
consumes — a PHASE 1 step, not a manual prerequisite.
⑂ `$COWORK_WORK/world-tags.json` already exists → **ALREADY-DONE**, skip to `1.0d`; never overwritten.
· Missing → thin-slice every flattened chat, gate + pack the slices, spawn one tool-less **`ingest-tagger`**
agent (Read-only, model **haiku**, `run_in_background: true`) per bundle — the same reader/actor split PHASE
3 uses for `ingest-conclusions` — then collect + validate into the closed tag vocabulary:
```bash
if [ -s "$COWORK_WORK/world-tags.json" ]; then
  echo "ALREADY-DONE: $COWORK_WORK/world-tags.json already exists — skipping tag"
else
  SLICES="$COWORK_WORK/tag-slices"; TAGSCRATCH="$COWORK_WORK/tag-bundles"; RAWTAGS="$COWORK_WORK/raw-tags"
  python3 $T/tag.py slice --in "$FLAT" --out "$SLICES"
  python3 $T/gate_and_pack.py --in "$SLICES" --out "$TAGSCRATCH" --desk cowork-ingest --max-files 25 --slice none
  mkdir -p "$RAWTAGS"
  # spawn one tool-less `ingest-tagger` agent per $TAGSCRATCH/bundle-*.txt (its own agent file
  # already exists, unused until now), collect automatically, then:
  python3 $T/agent_output.py --agents <id1> <id2> … --out "$RAWTAGS"
  python3 $T/tag.py collect --raw "$RAWTAGS" --out "$COWORK_WORK/tags-collected.json"
  python3 $T/tag.py validate --tags "$COWORK_WORK/tags-collected.json" --out "$COWORK_WORK/world-tags.json"
fi
```
*Refuses on:* nothing — a chat the gate marks DANGER is quarantined and skipped, never blocks the run; its
`categories` stay empty rather than guessed. *Evidence:* `world-tags.json`'s row count against `$FLAT`'s
`.txt` count.

**`1.0d` Prepare the map** *(was `1.0`).* If `$MAP` doesn't exist → `python3 $T/corpus_map.py init --tags
"$COWORK_WORK/world-tags.json" --out "$MAP"` (by the time this runs, `1.0a`/`1.0b` have already guaranteed
`$FLAT` and `world-tags.json` exist — this step never re-flattens/re-tags). Then `python3
$T/corpus_map.py migrate --map "$MAP"` (idempotent → schema v2; above 12 open baskets it prints an advisory
only — it never blocks; the count is emergent, see THE LOOP below). Assert: `python3 $T/pipeline.py assert
--map "$MAP"`.
*Refuses on:* schema ≠ v2, or a Drive conflict-copy sitting beside the map — two competing corpus maps
means every later decision lands in whichever file won.

**`1.0e` Bookmark chats for re-export durability** *(was `1.0b`)* (idempotent — safe every run):
```bash
python3 $T/pipeline.py hash --map "$MAP" --flat-dir "$FLAT"
```
If the human ever re-exports their chats and filenames change, `python3 $T/pipeline.py relink --map "$MAP"
--flat-dir "$FLAT"` re-attaches each row to its new file by content — no progress lost.

**`1.0f` Security posture check** *(was `1.0c`)*. ⚠ **NOT BUILT.** SPEC §7 calls for reading
`INGEST_GATE_POSTURE`, stating it, and proceeding only on `enforce` before the light read. No such check
exists in this phase's code today — this is a documented gap, not a step to perform. Do not invent a
command for it; flag it and move on.

---

## TURN 1 — the machine looks, then explains 🤖

**What this turn does:** warns the human it's about to disappear for a few minutes, takes a light,
corpus-wide pass — titles and tags only, never a chat body — and reports what boundaries it found.

**`1.1` Give the heads-up — BEFORE the long operation.** A person watching silence assumes something
broke, so say this first. Speak the WELCOME from `SKILL.md`, then PASTE the block below into your reply
(never leave it in the collapsed command block):

> **PRESENTATION — paste verbatim:**
>
> **Here's what we're doing, and where this fits.**
>
> *You've got {N} chats here — years of your own thinking, scattered. What you'll have at the end isn't a
> big summary document; those are useless. It's a folder structure you can drop straight into your system,
> where every folder is a real boundary — finances, writing, health, whatever turns out to be in here — and
> each one carries its own canon file saying what belongs in it.*
>
> *We get there in four passes. This is the first, and it's the cheapest: **I don't read anything.***
>
> *I'm about to look at titles and tags across all {N} chats to work out what piles actually exist. Takes a
> few minutes. I don't know your life, so I'm guessing at the boundaries from the outside — which is why
> you'll correct me when I come back.*
>
> *Nothing gets read. Nothing gets saved. Nothing gets thrown away.*

**`1.2` Take the light read, then place every chat.** *(the long operation)* Read titles and tags
corpus-wide, let the boundaries emerge — no target list, no target count; the shape of a corpus is opaque
from outside, so the count is whatever the material says it is. **Never opens a chat body** — titles and
tags are the entire input, on purpose. Each chat written to exactly one pile:
`python3 $T/corpus_map.py set --map "$MAP" --file <f> --subject "<subject>"`.
*Evidence:* every row carries a non-null `basket`. Checkable.

**`1.2b` Cluster the unclustered pile (metadata only, never bodies).** Read the TITLES of chats whose
`basket` is `UNCLUSTERED` or a giant catch-all, group them into ad-hoc subjects, write each back the same
way as `1.2`, then re-`migrate` to seed the new baskets. `python3 $T/basket_review.py unclustered --map
"$MAP" --include untouched,maybe-skip` shows what's left. Keep baskets human-sized — a 500-chat basket is not sorted, it's a pile that
still needs splitting.

**`1.3` Report what came back — AFTER the long operation.**
```bash
python3 $T/pipeline.py progress --map "$MAP" --just-did "grouped your old chats into subject piles" --next "look over the groups and tell me which whole piles are pure junk"
# ⛔ --include is REQUIRED here. Left off, it defaults to `maybe-skip` -- the chats the tagger gave NO
# category to -- so the board shows only the junk candidates and every tagged chat is invisible. The
# human would then rule on pile boundaries having been shown almost nothing. Measured on a fixture
# corpus: 10 chats sorted into 5 piles rendered as "0 chats, 0 piles".
python3 $T/basket_review.py summary --map "$MAP" --include untouched,maybe-skip
```
**Reproduce the whole screen in your OWN reply.** Do NOT leave it in the collapsed command block — the
human sees only "+N lines" and thinks nothing happened. Then say, in these words or close to them:

> **PRESENTATION — paste verbatim:**
>
> *Back. Here's what's in there:*
>
> {THE BOARD — one row per pile: name · count · 2-3 real example titles, from the tool above}
>
> *Still nothing read, nothing saved, nothing thrown away. Tell me where I've got the boundaries wrong.*

*What the board has to achieve:* enough of each pile that the human can actually recognise what's in it —
a name-and-a-count row alone is known not to work: it produces a rubber stamp, not a decision.

---

## TURN 2 — the human's turn 🧑

**What they're deciding:** whether these are the right boundaries for their life.

**What they contribute that the machine cannot:** the machine can see that forty chats mention
screenwriting. It cannot know that writing and acting are *different jobs* to this person, or that two
tags are really one concern. **That recognition is the entire reason this turn exists.**

Accept the three moves from THE MOVE SET above, in any order, dictated. **Coarse toss-or-queue only here**
— keep-shallow vs. deep-read is SCAN's job, not this one. A question isn't a move and doesn't advance the
turn. **Anything they do not rule on stays as it is — silence is never a close.**
*Evidence:* none — lives in the transcript only. Uncheckable by construction; grade INCONCLUSIVE, never
FAIL.

---

## TURN 3 — the machine responds 🤖 ↩

**`1.4` Read back any close before acting on it.** A split or merge is acted on directly; **a close is
confirmed first.** *Why asymmetric:* mishearing a merge costs a redo. Mishearing a close throws away
material the human wanted, and the loss is invisible to them until much later. *(2026-08-04: "don't need
number three" was read as a toss when the human meant keep — caught only because he re-read the ledger.)*

**`1.5` Write it**, then re-render the board and offer the choice:
```bash
python3 $T/basket_review.py summary --map "$MAP" --include untouched,maybe-skip   # see 1.3 on why --include
```

> **PRESENTATION — paste verbatim:**
>
> *Merged {A} and {B}, closed {C}, moved {N} chats. You're at {M} piles.*
>
> {Board}
>
> *Another pass, or move on to scanning {first pile}? — I'd suggest {X} because {Y}.*

*Why the offer carries a recommendation:* "are you done?" hands the human a decision with none of the
information behind it. Naming what another round would get them, and what moving on would cost, is what
makes the choice answerable.

---

## THE LOOP

**Turns 2 and 3 repeat as long as the human wants.** Each round the board gets truer. After about three
rounds, recommend moving on and say why — past that it's usually taste, not signal.

**Same fence every round: placing, not reading.** Re-apply it each time, so a long correction loop cannot
drift into opening chat bodies.

**On pile count — propose, never refuse.** If the count comes back high, propose merges with reasons and
let the human rule; `migrate` (`1.0d`) only ever ADVISES above 12 open baskets, it never blocks. *Why nudge
at all:* the pile count is the number of times the human sits down — 23 piles is 23 rounds of
scan→read→reflect, 8 is 8. But too few and a pile won't fit one sitting — a 43-chat pile took a full
session once. Real floor, real ceiling; only the human feels where it is.

⛔⛔ **BUT THE PHASE DOES NOT *CLOSE* ON A PROPOSAL — IT CLOSES ON TWO PLAIN QUESTIONS (2026-08-09).**
The nudge above belongs INSIDE the loop, offered at most once, and **never as the last thing on screen.**
**Measured live 2026-08-09:** SORT ended by proposing five separate changes — rename this pile, move these
out, merge those — and the operator, who had just met the piles, could not answer any of them:
*"That's a little weird… it really just wants to know, do you approve of these piles? Do these piles seem
correct for the corpus? And then it should ask, are you ready to go to the next phase. This is simpler
than that — it shouldn't be that complicated."*

⇒ **THE CLOSING SCREEN ASKS EXACTLY TWO THINGS, IN THIS ORDER, AND NOTHING ELSE:**
> **①** *"Do these piles look right for your material?"*
> **②** *"Ready to move to phase 2 — screening the first pile?"*

**A correction is something they VOLUNTEER, never a menu you hand them.** If they want a pile merged,
renamed or dropped they will say so; the action bar already tells them how (`"toss <pile>"`). ⛔ **Do not
enumerate candidate edits at the close, do not attach a numbered change-list to these two questions, and
do not ask them to rule on the pile TAXONOMY here** — whether "job search" and "product design" should
both live under one broader heading is a **PHASE 4** question, decided when the folder schema is built and
the human can see the whole shape at once. *(That was the operator's own read the same day: "maybe that's
a step at the end, actually… the final phase is when it makes the folder schema.")*

---

## FINAL TURN — CLOSE SORT 🤖

**`1.6` Close SORT — only after the human has actually ruled.** This is the phase's done-condition, and it
is the ONLY thing that lets `/ingest` advance:
```bash
python3 $T/pipeline.py sort-confirm --map "$MAP" --human-approved
python3 $T/pipeline.py assert --map "$MAP" && python3 $T/pipeline.py suggest --map "$MAP" --skill ingest-1
```
**It REFUSES on:** `--human-approved` missing, or the map having no baskets at all yet.

⛔ **Do NOT run it to "move things along."** Until it runs, an interrupted session resumes at TURN 2, with
the boundaries still open — which is the point. Run it only once the human has seen every basket and said
the groups are right. If they walk away mid-sort, leave it unrun; nothing is lost. *(Before 2026-08-06
there was no such gate: baskets existing counted as SORT being finished, so an interrupted sort skipped the
human's ruling turn forever.)*

> ⚠ **CONFLICT WITH SPEC §7 — noted here, not silently resolved.** SPEC §7's FINAL TURN lists its own
> close-checks ("posture stated · no chat left unplaced · every close carried `--human-approved`") and its
> PRESENTATION block goes straight from the close message to "Type `/ingest`" — it never mentions running
> `sort-confirm` at all. `sort-confirm` is newer (2026-08-06) and is the actual gate `pipeline.py`'s
> `current_phase()` reads to decide SORT is done, so **it wins here.** SPEC §7 needs a matching update to
> stop describing a close the code doesn't recognise; that update is a separate task, not this one.

**`1.10` Create the run's project, and persist what this phase produced into it.** Only after `1.6`'s gate
has actually fired — this step rounds up everything PHASE 1 just settled (the pile boundaries, every
split/merge/close the human ruled, the counts) and writes it into a NEW project for this corpus, one per
corpus:
```bash
# ⛔ --root is THEIR notes folder, NOT this repo. `pad_write` says so in its own contract: the root "is
# simply the folder the human already named". This line used to pass `git rev-parse --show-toplevel`,
# which is the folder the TOOL was cloned into — so every pad landed inside the tool folder and would
# have been wiped by the next update. Resolve it the same way every other phase does.
DRIVE="$(python3 "$T/pipeline.py" brain-root --quiet)" || { echo "STOP: no brain root set yet — go back to step 1.0"; exit 1; }
python3 $T/pipeline.py pad-init --map "$MAP" --root "$DRIVE"   # one pad PER PILE, plus a corpus pad
```
**Reproduce whatever path it reports in your OWN reply** — never leave it in the collapsed command block;
that path is what you tell the human next.

> ⚖⭐ **THIS USED TO WRITE A PROJECT BRIEF THROUGH `project-manager`. IT NO LONGER DOES (2026-08-09).**
> The author's ruling: *"forget project manager, forget integrating with that skill. It's literally just
> going to create one scratchpad that it writes to."* ⇒ **one plain file, `memory/<corpus>/scratchpad.md`,
> in the human's own tier.** ⛔ **Do not re-introduce a schema, a brief, or a second skill here.** The old
> path read a schema file that is not part of a shipped package and wrote to a personal Drive layout that
> does not exist on anyone else's machine — it was dead everywhere but the author's laptop.
**Naming rule binds here too** (SPEC §0a ruling 2): the pile names are the first draft of the folder names,
so they stay **generic subjects** — `financial`, `hobbies`, `art` — ⛔ never persona-style desk names.
**Refuses on:** `1.6` not having run yet — there is nothing to persist. **PHASE 2 does not open until this
step has run** — that gate is real and survived the rewrite (`pipeline.py` → `pad_exists`); its own `2.0b`
reads the exact file this step just wrote.

Tell the human plainly:

> **PRESENTATION — paste verbatim:**
>
> *One more thing before you go — I've started a notes file for this material, so nothing we just decided
> gets lost between sittings. It's saved at `{path reported by pad-init}`, and it's yours — you can open it
> and read it any time. Every later pass reads it and adds to it, so the picture only gets sharper.*

Then tell the human plainly what just happened with the phase itself:

> **PRESENTATION — paste verbatim:**
>
> *That's your structure: {N} piles, {M} chats placed, {K} closed by you. Still nothing read, nothing
> saved.*
>
> *Next is scanning {first pile} — that's where I start actually reading. Say `continue` when you're
> ready.*

Relay the `suggest` line, then ask: **"Ready to move on to the next phase? Say `continue`."**
⛔ **Never hand them a slash-command as the way forward** — accept `continue` / `next` / `yes` / `/ingest`
equally (2026-08-09; see `2-scan.md` `2.11` for the measured reason). **Then it STOPS.** ⛔ Does not roll into
SCAN. The human re-invokes; **the re-invocation is the re-anchor.**
**NEXT:** `2-scan.md`.

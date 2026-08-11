# PHASE 4 — PLACE IT + THE ROOT CANON (the tree is already settled; this executes it)

> ## 📖 REFERENCE — `PLAN-B.md`, in the top folder. Read it when in doubt.
>
> It states this same method in four plain rounds that map 1:1 onto the four phases. **Your matching round is `ROUND 4 — Place it`.** Read it when you are unsure what should happen next, what a
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

> **⚖ WAS A SEPARATE SKILL UNTIL 2026-08-05.** This file was `skills/ingest-filer/SKILL.md` — the second of
> two auto-chained skills. **The split was reversed** *("I no longer feel this needs to be two skills")*,
> and it is now the final phase file of the one `/ingest` skill. The 2026-07-11 advisory-council decision
> that created the split keeps its full text in the project's Story Log as `[SL-3]`, marked
> `superseded-by:[SL-24]` — **the council's reasoning is the record of why the split looked right at the
> time**, and it is not deleted.
>
> **Why the July reasoning stopped holding — three reasons, all load-bearing:**
> ① **The filer's job SHRANK** from a second act (design the whole desk schema from the manifest, at the
> end, in one sitting) to a single phase — because **the folder schema is now the SPINE, not the output**:
> it forms in Phase 1 and is corrected and committed per-pile in Phase 3. By the time this file runs, the
> tree is already agreed.
> ② ⭐ **THE HANDOFF ITSELF WAS WHERE INFORMATION WAS BEING LOST.** The manifest is a serialization
> boundary, and the eleven conclusion categories collapsing to two chat-row booleans exists *because* of
> it. Merging removes the wall those categories had to survive.
> ③ `skill-building-sop.md` §0 trait 1 defaults to one skill: *"split the machinery only when earned."*
> The split was earned in July on a shape that no longer exists.
>
> ⚠ **This phase is now SMALLER than the skill it came from.** Step `4.2` below used to be a full
> design conversation; it is now execution of boundaries already ruled on. If you find yourself
> re-designing the tree here, Phase 3 didn't do its job — go back, don't re-litigate it while tired.

> **YOU ARE STILL VERA THE CURATOR** — the same warm voice that mined the corpus; there is no handoff and
> the human should not feel one. Her identity is `vera-curator.md`, her turn rules
> `vera-voice.md`; both are already loaded by the time you reach this phase.

> **BEGIN WARM, RUN QUIET.** Tell the human plainly where they are (the reading and the world map are done;
> now everything gets filed into the folders they already agreed), then run `4.1` → `4.6` in order. Warm
> words up top; the plumbing runs underneath with no narration. **SHOW IT** — any list the human must rule
> on, PASTE into your own reply (the CLI collapses command output; if it isn't in your message, they
> didn't see it).

> **GATE: HARD_STOP — MAIN SESSION ONLY.** This phase WRITES records, only after the human approves each,
> so it cannot run in a spawned subagent (a subagent can't pause for approval). If you are NOT the main
> interactive session, **ABORT** and print: "the /ingest placing phase must run in the main session —
> aborting." VIOLATION: any record write or terminal fate from a subagent.

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

## The law (spans every phase)
- **The corpus-map (`work/corpus-map.json`) is your memory + state machine.** Read it; never trust recollection.
- **The machine never eliminates; the human sees everything.** Every keeper is placed, pointer-ized, or
  explicitly set aside — nothing is dropped unseen. You PROPOSE; the human RULES, by number.
- **Canon is NEVER auto-written.** A canon-candidate goes to `records/proposals/` with `vetted: false` — never
  to `canon/`. The `guard_canon_write.sh` hook enforces this; don't fight it, honor it. Word each proposed line to pass the STANDALONE TEST — a cold, zero-context session can fully understand it alone (precise + self-sufficient; matters more than length).
- **FIRST DO NO HARM — search before you add.** Before writing anything canon-bound, run the dedup/conflict
  scan; the living desk WINS over a stale ingested snapshot. Drop or surface a conflict; never silently overwrite.
- **Blind chain the phases.** Run LOAD → SCHEMA → CONFIRM → PLACE in order; don't skip ahead. Nothing writes
  until CONFIRM has the human's yes.

## Paths + arm the anchor (do this first)
```bash
ROOT="$(cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" && pwd)"   # the folder you cloned; everything below is relative to it
T="$ROOT/system/tools/cowork-ingest"
# Same brain root PHASE 1 recorded — resolved, never guessed. ⛔ STOPS rather than picking a folder for them.
DRIVE="$(python3 "$T/pipeline.py" brain-root --quiet)" || { echo "STOP: no brain root set yet — run PHASE 1's step 1.0, or: python3 $T/pipeline.py brain-root --set \"<that folder>\" [--create]"; exit 1; }
export INGEST_CORPUS="${INGEST_CORPUS:-my-corpus}"   # the corpus slug; one per corpus you ingest
export COWORK_WORK="$DRIVE/state/projects/$INGEST_CORPUS/work"
MAP="$COWORK_WORK/corpus-map.json"
ANCHOR="$HOME/.cache/cowork-ingest/$INGEST_CORPUS/ingest-anchor.txt"; mkdir -p "$(dirname "$ANCHOR")"
S="$ROOT/system/hooks/skill_anchor.sh"
python3 $T/pipeline.py assert --map "$MAP" || { echo "MAP NOT v2 — run: python3 $T/corpus_map.py migrate --map \"$MAP\""; exit 1; }
python3 $T/pipeline.py anchor --phase 4 --out "$ANCHOR"     # phase 4 = PLACE
bash "$S" arm ingest "$ANCHOR"     # ONE skill now — REFRESH the anchor, never hand it off (2026-08-05)
```
> ⚠ **The old two-skill handoff is gone.** This used to `clear ingest` then `arm ingest-filer`, swapping the
> injected frame between two skills. There is one skill now, so the anchor is simply re-armed at phase 4.
Then PASTE the dashboard so the human sees where they are:
`python3 $T/pipeline.py progress --map "$MAP" --just-did "finished reading everything" --next "pick which folders your notes go into"`

---

## 4.1 — LOAD (gather the manifest — read the map, never the chat bodies)
The miner already read the chats; you read only its STAGED output. **The finding TYPE does not live on the
map row** — `canon_flag`/`pointer_candidate` were the old two-boolean shape and are gone. The human's real
ruling (`canonical` · `dated` · `record`, [SL-23]) lives PER-FINDING inside each basket's coalesced reader
output, `raw-conclusions-<basket>.json` (written by `set_finding_type()`, read by `world_map_state()` —
`pipeline.py:1174` / `pipeline.py:1208`). Gather every TYPED finding across ALL piles from THAT file, one
manifest row per finding (a chat can carry several):
```bash
# every human-typed finding, straight from the coalesced reader output — never the map's old flags
python3 - "$MAP" "$T" <<'PY'
import json, sys, os
sys.path.insert(0, sys.argv[2])
import pipeline
m = json.load(open(sys.argv[1]))
work = os.environ.get("COWORK_WORK")
keepers, untyped = [], 0
for basket in sorted(m.get("baskets", {})):
    path, _ = pipeline.coalesced_evidence(basket, work)
    if not path or not os.path.exists(path):
        continue
    data = json.load(open(path))
    if isinstance(data, dict):
        data = data.get("conclusions") or data.get("items") or data.get("results") or []
    for el in data:
        if not isinstance(el, dict):
            continue
        chat = el.get("file") or el.get("chat") or el.get("id")
        for i, c in enumerate(pipeline._conclusions_of(el)):
            ftype = c.get("type")
            if ftype not in pipeline.FINDING_TYPES:
                untyped += 1
                continue
            keepers.append({"file": chat, "basket": basket, "index": i, "text": c.get("text"),
                            "finding_type": ftype})
print(f"{len(keepers)} typed finding(s) across {len(set(k['basket'] for k in keepers))} pile(s)"
      + (f"  ·  ⚠ {untyped} UNTYPED — back to Phase 3, do not file blind" if untyped else ""))
json.dump(keepers, open("/tmp/filer-manifest.json","w"), indent=0)
PY
```
Tell the human, plainly: *"I've got everything you kept — {N} notes across {M} topics. Nothing's saved yet; you'll
approve every folder and every note before it lands."* Note the split: how many are `canonical` (canon-candidates),
how many `dated`, how many plain `record`s — read straight off `finding_type`, never re-guessed. If ANY finding
came back untyped, stop and send that pile back to Phase 3 rather than filing it blind. → go to SCHEMA.

## 4.2 — EXECUTE THE TREE (it is already settled; this is not a design step)

> ⚖ **REWRITTEN 2026-08-05 — THIS STEP SHRANK.** It used to design the whole desk schema from the manifest,
> here, at the end. **The folder schema is now the SPINE, not the output:** Phase 1 drew the first draft as
> piles, and Phase 3 corrected and committed one branch per pile while that pile's material was fresh. So
> this step **assembles and confirms** what was already ruled — it does not invent it.
>
> ⛔ **If you catch yourself designing the tree here, STOP.** That means Phase 3 didn't do its job for one
> or more piles. Go back and do it there, with that pile's material in front of you. Designing a folder
> tree at the end, tired, about chats read weeks ago, is the exact failure this restructure removed.

**READ WHAT PHASE 3 ALREADY RULED — this is the assembly input** *(F8.4, 2026-08-06: before today these columns
did not exist, so there was nothing to read here and this step silently became a design step again every run):*
```bash
python3 - "$MAP" <<'PY'
import json, sys
m = json.load(open(sys.argv[1]))
missing = []
for name, b in sorted(m.get("baskets", {}).items()):
    if b.get("basket_status") == "declined":
        continue
    branch = b.get("folder_branch")
    print(f"{name:32} → {branch or '⚠ NO BRANCH RULED'}")
    if not branch:
        missing.append(name)
print()
print(f"{len(missing)} pile(s) with no folder branch" + (f": {missing}" if missing else " — the tree is settled"))
PY
```
Any pile listed `⚠ NO BRANCH RULED` goes **back to Phase 3** for that pile — do not invent its branch here.
Per-pile detail (branch + how many findings carry a human-chosen type):
`python3 $T/pipeline.py world-map-state --map "$MAP" --basket "<pile>"`

**Assemble the tree from the per-pile branches** Phase 3 recorded, present it whole (this is the first time
the human sees the WHOLE shape rather than one branch), and take corrections. Then scaffold.

<details><summary>The superseded design-it-here procedure, kept — it is what to fall back to if Phase 3's branches are missing</summary>

1. **Propose desks from the piles.** The mined piles ARE life-arenas. Group them into a handful of **desks** a
   person actually thinks in — e.g. **money/finance**, **health**, **home**, **writing**, **work/business**.
   Present as a NUMBERED list, your best guess, answerable by number:
   > *"Here's how I'd sort your notes into desks — change any name, merge, or split:
   > 1. **Money** (piles: taxes, investing, budgeting) — 34 notes
   > 2. **Health** (piles: fitness, medical) — 12 notes
   > 3. **Writing** (pile: essays) — 8 notes …"*
2. **Sub-folders ONLY when a desk earns them (canon-audit's crowding/altitude rule, inlined).** A desk stays
   ONE flat `records/` folder unless it has **enough material that a single folder would be crowded** (rule of
   thumb: a desk with 3+ clearly-distinct sub-themes AND enough notes to fill them). A light desk stays flat.
   Propose splits as a best-guess, by number; a small desk → *"this one stays a single folder for now."*
3. **Scaffold each confirmed desk**: `python3 $T/folder_scaffold.py --drive-root "$DRIVE" --path "desks/<slug>"
   --purpose "<one line>" --topic "<slug, from THEIR memory/topic-vocab.md>" --desk "<slug>"`. *(2026-08-08: this
   used to call the older whole-desk scaffolding tool and print a `system/desk-registry.yaml` block for the
   human to paste — that tool is NOT deleted, it stays for a deliberate later promotion, but a Phase 4
   scaffold is a plain knowledge folder — `canon/current.md` + `canon/purpose.md` + `records/`, no registry
   entry — which is `folder_scaffold.py`'s job; it prints nothing to paste, so there is no registry step here.)*

</details>

**Scaffold each confirmed folder**: `python3 $T/folder_scaffold.py --drive-root "$DRIVE" --path "desks/<folder_branch>"
--purpose "<one line>" --topic "<slug, from THEIR memory/topic-vocab.md>" --desk "<owning-desk-slug>"`. *(2026-08-08:
points at `folder_scaffold.py` now — it makes exactly what a Phase 4 folder needs, `canon/current.md` +
`canon/purpose.md` + `records/`, and prints nothing to paste — there is no registry step at this level; the
older whole-desk scaffolding tool (which DOES print a `desk-registry.yaml` block) is kept, unused here, for
a deliberate later promotion.)*
**Every folder is a knowledge boundary with its own canon file and a stated purpose** — that is the skill's
whole deliverable, not a nicety. → go to `4.3`.

## 4.3 — CONFIRM (the TOOL-PRINTED filing plan + the two-key canon gate)
The confirm screen is **PRINTED BY A TOOL, not hand-assembled** (hand-listing is what drifts). Build the plan
as a small JSON, then render + PASTE the screen:
**Rank each item's `home` HERE, ONCE, before the human ever sees this screen** (reuse `archivist-route`
inline — don't rebuild it; its own contract, `skills/archivist-route/SKILL.md` §Procedure step 7: *"Return
the ranked candidates. Do NOT write. The caller surfaces them for the human's one-tap pick, then writes."*
— the rank happens BEFORE the pick, never after). Carry its self-declared caution: it over-defaults to the
project's own / `[INFERRED]` canon — treat its first pick skeptically and prefer the desk the human named
in SCHEMA / the pile's `folder_branch` from Phase 3.
```bash
# one row per keeper: {title, home:"desk/folder", kind:"record|dated|pointer|canon", why, date (kind=dated only)}
#   — build this from your SCHEMA proposals + /tmp/filer-manifest.json (finding_type: canonical→"canon",
#     dated→"dated", record→"record"; a pointer is a placement CALL you make at 4.4, not a finding_type)
#   — "home" is archivist-route's #1 ranked candidate, decided NOW — this is the ONLY place `home` is computed
cat > /tmp/filer-plan.json <<'JSON'
[ {"title":"…","home":"money/records","kind":"record","why":"…"}, … ]
JSON
python3 $T/filer_review.py show --plan /tmp/filer-plan.json --map "$MAP"
```
`filer_review.py` renders it through the ONE shared screen template (title + %-bar → **SAVE** rows → the ONE
action last), records/pointers first and canon-candidates LAST, each flagged **⚠** as needing the separate
permanent key. **SAVE is the honest verb here** (this is the only screen where anything is actually saved).
Reproduce the whole screen in your reply — never leave it collapsed, never re-format the rows into prose.
- **Two keys.** A plain "yes" (or "1 yes, 2 yes, 3 change to Health") approves the **records + pointers**. Each
  **canon-candidate** (the ⚠ rows) needs a SEPARATE explicit key — *"yes, save this as a permanent note"* — and
  even then it writes to `records/proposals/`, never `canon/`. Never let the ordinary yes imply the permanent one.
- **The anti-rush gate:** you may not place an item until you can state *what it is + which home it earns + why*.
  PLACE acts ONLY on the items the human confirmed this turn. → go to `4.4`.

## 4.4 — PLACE (write the records + canon-proposals; dedup; record the fate)

> ⛔ **A RECORD GETS A STUB FILE — THE ORIGINAL IS NEVER MOVED, NEVER REWRITTEN** *(ruled 2026-08-05: "we're
> not going to bother spending LLM tokens rewriting it"; ruled three times — this line previously had it
> backwards, saying records themselves were moved). **Only canon and dated information get AUTHORED.** A
> record's whole value is that it is the real thing; rewriting it into cleaner prose spends tokens to make
> it less true, so the record stays exactly where it is and the filing is a small stub file that points at
> it. Phase 3 already typed every finding as **canonical · dated-but-valuable · record** — honour that type
> here.
For each CONFIRMED item, in the safest-first order:

**A. Reuse the approved home — NEVER re-rank it here.** The home was already ranked ONCE, at `4.3`, before the
human approved this exact plan (`/tmp/filer-plan.json`'s `home` field) — that ranking + the human's approval
of it IS `archivist-route`'s "caller surfaces them for the human's one-tap pick, then writes" (its contract,
cited above). Calling `archivist-route` again here would rank a DIFFERENT home than the one the human just
signed off on and write the file somewhere they never saw — the file written must be the file approved. Take
`{desk, folder}` straight from the item's `home` in the approved plan; only `record_type` is decided here
(it wasn't part of what CONFIRM showed).

**B. Type-triage (inbox rule, inlined + cited).** Assign `record_type`: a durable answer/synthesis → `finding`
(the default); a committed decision → `decision`; a trade-off → `pros-cons`; a live number → `snapshot`
(with a shelf-life); a big reference → the pointer form. **NEVER** assign `canon`/`rule` — only the human elevates.

**C. DEDUP-FIRST, canon-bound only (inbox DEDUP-FIRST + canon-audit, inlined).** Before writing a
canon-candidate, scan existing canon for a duplicate/conflict:
```bash
python3 $ROOT/system/tools/canon_conflict_scan.py --canon-root "$DRIVE/desks/<desk>/canon" --terms "<key,terms>" --title "<title>" --json
```
NEW → proceed to proposals. DUPLICATE → drop it (say so). CONFLICT → **surface to the human, never auto-resolve**
(the living desk wins). This is the "first do no harm" wall.

**D. Write the file (the filer IS the placer — human already approved at CONFIRM).**
**Gate the `topic:` value FIRST — this runs BEFORE you write a single byte of frontmatter.** Every file below
carries a `topic:` slug; check it against the closed vocabulary before authoring anything:
```bash
python3 $T/pipeline.py topic-check --topics <slug> [<slug2> ...]
```
Exit 0 → the slug(s) are in the closed vocabulary — write the frontmatter as planned below. Non-zero → **STOP,
do not write the file.** The tool names the file it checked against and every path it tried; pick an existing
slug from it, or ask the human to add one FIRST, then re-run this check before writing.

⛔ **The vocabulary is THEIRS and it lives with their notes** (`memory/topic-vocab.md`), not in this repo —
nothing ships one. **Never invent a slug, and never edit their vocabulary yourself.** If they have no
vocabulary yet the tool refuses and prints how to start one; hand them that, do not write it for them. A
taxonomy of someone's life, authored by a machine, is worse than no taxonomy at all.
- **A record (`finding_type: record`)** → a **STUB FILE**, `desks/<desk>/<folder>/<YYYY-MM-DD>-<slug>.md`,
  with a valid frontmatter envelope (`title · record_type · desk · topic · created_at · status: active ·
  authority: user · confidence:<CONFIRMED|INFERRED> · source_refs:[the source chat]`) whose BODY is only
  the back-pointer to the source chat + a one-line what-it-is. **The original chat is never moved, never
  rewritten** — the stub is what gets filed, not a copy of the content.
- **A dated item (`finding_type: dated`)** → the same envelope, AUTHORED — body is the confirmed
  dated-but-valuable finding, written out (this is the one case worth spending tokens on, because the
  number/fact has a shelf-life and won't still be sitting readable in the original chat by the time anyone
  needs it again).
- **A canon-candidate (`finding_type: canonical`)** → `desks/<desk>/records/proposals/<YYYY-MM-DD>-<slug>.md`,
  same envelope PLUS `vetted: false` and a `## Why this could be canon` note, AUTHORED. NEVER write under `canon/`.
- **A pointer** (a placement call made here for an oversized keeper, not a `finding_type`) → a tiny record
  whose body is just the source pointer + one-line what-it-is (no full content).

**E. Record the fate in the map (reuse `wmb_commit` + `commit-mark`, human-gated).**
```bash
python3 $T/wmb_commit.py save --map "$MAP" --chat "<file>" --status filed --record "<path you wrote>" --desk "<desk>" --human-approved
python3 $T/pipeline.py commit-mark --map "$MAP" --file "<file>"
```
For a pointer/defer/decline use `--status pointer-only|deferred|declined` (each needs `--human-approved`).

**Safe-class + carve-out (retired-autoplace rule, inlined + cited).** The filer writes only the SAFE class:
dated records + proposals. It NEVER auto-executes a carve-out item — any `CLAUDE.md` edit, any skill edit, any
`canon/current.md` or root-canon write, any hard-delete, any contested verdict. Those stay human-only.
**NOT harvested (cut as overhead the per-item human approval already covers):** the vet 3-lens panel, the
cross-run ledger, the per-run auto-place cap.

## 4.5 — THE ROOT CANON (last, and only after every folder has its own)

> **Merged in from the old Phase 6 (PROMOTE), 2026-08-05.** It was never a phase — it has one human turn
> and it belongs to the end of placing.

Each folder already carries its own canon file (`4.2`). **The ROOT canon is different: it is what a cold
session loads for EVERY conversation, so a line placed there is charged to every descendant, forever.**
*(Verified: `/read` chain-walks parent canon — `skills/read/SKILL.md` Step 0.6. The placement rule is a
COST rule.)*

- Surface root-canon candidates **ONE AT A TIME**, each with what it would cost to carry everywhere.
- ⛔ **Canon is NEVER auto-written.** A candidate goes to `records/proposals/` with `vetted: false`.
- ⚠ **Known weakness, stated rather than hidden:** the "second key" is today a string match on content the
  writer wrote. **That is not a gate** — it is the actor grading its own homework. Treat root-canon
  promotion as human-only in practice, whatever the code appears to allow.

## STOP-CHECK + close
When every keeper is filed, close each pile and finish:
```bash
for b in $(python3 -c "import json; m=json.load(open('$MAP')); print(' '.join(m['baskets']))"); do
  python3 $T/pipeline.py basket-status --map "$MAP" --basket "$b" --status committed 2>/dev/null
done
# ⚠ `--skill ingest-filer` is a PHASE TOKEN here, not a skill name — the filer is no longer a separate
# skill (2026-08-05), but `pipeline.py suggest` still branches on this literal string. Renaming it is a
# code change tracked as [INGEST-FILER-TOKEN-RENAME]; passing anything else today takes the wrong branch.
python3 $T/pipeline.py assert --map "$MAP" && python3 $T/pipeline.py suggest --map "$MAP" --skill ingest-filer
bash "$S" clear ingest
```
The `basket-status committed` write REFUSES a pile with any un-closed keeper (the done-gate — no gold left
behind); if it refuses, finish those items first. Then tell the human, warmly and plainly, what just got filed
and where — a clean end-count — and that their whole history is now organized. STOP.

## Failure modes (do not)
- Writing to `canon/` (proposals only) · auto-resolving a canon conflict (surface it) · placing an item the
  human didn't confirm this turn · assigning `canon`/`rule` type · running from a subagent · scaffolding a desk
  the human didn't confirm · trusting memory over the map · claiming "filed" without the record on disk +
  the map fate recorded · re-building archivist-route / canon-audit / the vet panel instead of reusing/citing them ·
  re-ranking an item's `home` at PLACE (`4.4`) after CONFIRM (`4.3`) already showed the human that home and
  they approved it — rank once, at `4.3`, and reuse; the file written must be the file approved.

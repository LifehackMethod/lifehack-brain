# Phase 1 — orient (steps 0 → 1.8)

Resolve the project, open the ledger, put the rungs on screen, load the brief in a deliberate order,
arm the plan, and **compact the pad before anything gets compared.**

---

## Step 0 — Resolve the active project

**Front-door arguments — `/checkin <project> <plan> [new-session]`.** That is the line `/save`'s
handoff emits. If the invocation carries a project (a slug, or an absolute brief path) and optionally a
plan path, those are the explicit target: resolve the brief, then arm **both** flags in one go. No
guessing.

```bash
python3 "$ROOT/shared/registry.py" "<slug>"          # layout + the brief, records and canon paths
bash "$ROOT/system/hooks/pm_flag.sh" arm "<abs brief>" "<slug>" "<desk>"
bash "$ROOT/system/hooks/plan_flag.sh" set "<abs plan>"
```

**Argument order matters: brief path first, then slug, then desk.** A slug in the path slot is the
malformed arm that makes the per-turn injector cite a bare slug instead of the brief.

**No arguments?** Read the flag:

```bash
bash "$ROOT/system/hooks/pm_flag.sh" status
```

A path → that is the project. `none` → **do not guess.** Ask which project, offering the registry's
candidates. If they name one, arm it.

**Then arm — do not merely read.** A window resumed on an old project usually has no flag, or a stale
one, so the status bar and the per-turn injector go blank or point at the wrong doc. Once resolved —
from the flag, the registry, or them naming it — arm for **this** session.

> ⛔ **Arming is immutable. Read `SKILL.md` before you obey that line.** "Arm/refresh" means refresh the
> **same** project. A switch is refused with exit 3, and that refusal is the finding, not an obstacle.
> *(Stated at both arm sites in this step deliberately — fixing one site is how a fix comes back.)*

**If the `new-session` token is present**, this window is in PICKUP mode. Say so in one line at the top,
and expect: gate 2 below to refuse, the graduation not to run, the handoff proof not to run, the story
log read in full, and a thin panel — **which is accuracy, not a weak run.**

## Step 0b — Open this run's ledger

```bash
python3 "$ROOT/system/tools/save/save_step_ledger.py" start --ns checkin
```

⛔ **Every run, before anything else stamps.** Nothing downstream can prove a step ran without it:
`stamp` refuses on an unopened ledger, and `report` returns `UNKNOWN` rather than clean.

⭐ **`--ns checkin` is load-bearing, not decoration.** `/save` and `/checkin` would otherwise share one
session-keyed ledger file, and `start` **replaces** the dict — so a `start` here would wipe `/save`'s
stamps. The namespace gives each skill its own file: both may `start` freely, neither can clobber the
other. ⛔ Never drop the flag "to keep it simple" — an un-namespaced `start` silently destroys a `/save`
run in the same window.

## Step 0.8 — Print the three rungs. Code does it, not you.

**Two calls, both instant file reads. You say WHERE; the code guarantees WHAT.**

```bash
# 1. ask for candidate line ranges — permissive, advisory, never a verdict
python3 "$ROOT/system/tools/checkin/checkin_open.py" hint "<abs brief>"
# 2. having read the brief, decide which lines are actually the block, and print exactly those
python3 "$ROOT/system/tools/checkin/checkin_open.py" print "<abs brief>" --start N --end M --paste
```

> ⚠ **`--end` is EXCLUSIVE, not inclusive.** It names the first line *after* the block you want, not
> the last line itself — a rung block on real lines N..M needs `--end M+1`, or the last rung silently
> drops (`RUNGS 2` instead of `RUNGS 3`, exit 0, no warning that anything is missing).

⛔ **Always `--paste` for anything going into the reply.** Plain `print` renders as a hard-wrapped,
unreadable mess once it lands in chat. `--paste` prints the same verdict token off the same mechanical
read, formatted to survive the trip: bolded label, one rung per line, a blank line between rungs.

> ⭐ **Why it is split this way — the governing rule for every tool in this skill.** *Finding* the block
> is fuzzy, so **you** do it; *printing* it is mechanical, so **code** does it. You cannot fabricate the
> text, because `print` reads it off disk. And if you pick the wrong range, the wrong lines appear on
> screen — **visible and correctable**, rather than silently wrong.
>
> ⛔ **Do not ask for a tighter matcher instead.** That was proposed and ruled out: a tighter regex
> trades a visible false positive for a silent false negative. **Measured:** the old symbol-hunting
> version returned `PARTIAL-RUNGS 6` on a real brief, because three lines of ordinary prose elsewhere
> in the file merely *mentioned* the marker while describing this tool. **It matched its own
> description.** `hint` is where loose matching is allowed to live, precisely because being wrong there
> costs nothing.

⛔ **Paste its stdout verbatim as the opening of your reply — before the summary, before anything.** Not
a paraphrase, not *"the rungs are current"*, not a status token. **The literal lines the tool printed.**
A reply that does not open with this block is a failed run, however good the rest of it is.

⛔ **Unconditional, and that absence of a gate is the entire fix.** Not *if they changed*, not *if the
block exists*, not *if the verdict is clean*. **The normal case — the rungs are already right — is
exactly the case the old version printed nothing for**, which is why the loop of proof could never
close. Every reading gets shown, including a boring one.

**A `BAD-RANGE`, or a `RUNGS <n>` where n is not 3, is not an error to swallow — it is the finding.** A
wrong count means either the block is genuinely missing or partial, **or your range was wrong**. Say
which, out loud, then carry it into phase 3, which drafts the fix as panel item 0. **You do not write
it here.**

> ⭐ **Why this is a script and not a sentence.** A model cannot report on its own compliance: it will
> accurately restate a rule it is simultaneously violating. A self-reported *"rungs: present"* is
> orientation, never evidence. **Four earlier attempts to fix this in prose all failed** — the last one
> correctly added *"print them verbatim"* to a receipt spec, deep in the middle of a long file, and
> gated it on having changed something, so the common case stayed silent. **Do not re-solve this with
> wording. If it breaks again, change the rung, not the sentence.**

## Step 1 — Load the brief, in this order

**Scratchpad self-heal first.** No `## 7. SCRATCHPAD` section → add an empty one now, before anything
else. Additive only; touch nothing else. Never run a check-in on a brief missing its pad, since the
harvest writes into it.

Then pull, in order — **whatever you read first becomes the lens everything else is judged through**:

1. **FRAME** — the desired outcome. The stable anchor. Read first, deliberately.
2. **The ⛔ RULED-OUT bucket** — read **either way**, cold or mid-session. It carries the duty never to
   re-propose something already tried and rejected, and that duty does not switch off mid-session.
3. **STORY LOG — gated, never skipped wholesale.**
   - **Cold pickup** (a fresh window, the first check-in of a session, or a real gap) → **in full.** The
     narrative arc is the point at a cold pickup.
   - **Mid-session** → every entry whose status is `open`, **plus the last few regardless of status.**
     Only the settled middle may be skipped.

   > **The failure this exists to catch.** A session ran a check-in, correctly followed an older
   > wholesale-skip rule, and never opened the story log. It then spent a full day reasoning from the
   > **symptom** recorded in current state instead of the **strategic fork** the project had actually
   > stopped on — which lived only in the story log. Every plan it proposed ignored that fork, and the
   > operator had to correct it from memory, repeatedly. **Current state records where things are; the
   > story log records why, and what question we stopped on.** Only the second prevents re-litigating a
   > settled fork.
   >
   > ⚠ The cost is real and is why the mid-session read narrows rather than skips: on one measured
   > brief the story log was **70.9%** of the whole file. The open-and-recent slice is a small fraction
   > of that; the settled middle is the only genuinely redundant part.
4. **CURRENT STATE + OPEN LOOPS** — the last-saved position. **And audit the rung block — five
   independent checks, not one glance.** Presence is not one of them; step 0.8 already settled that
   mechanically. **You do not write any fix here** — every finding lands as panel item 0.
5. **KEY RESOURCES** — the live handles to act.
6. **The linked plan** — the route, which may be stale.

### The five checks on the rung block

- **CHECK 1 — DRIFT.** ⛔ **Never inherit the written rungs as true — but this check does not apply
  the same way to all three.** For ▲5,000 and ▲ground: independently derive what they actually are
  **from what this session did** — the action taken, the seam it sits inside — **then** compare that
  against what the block says. Deriving from the written block just launders it back to you unchanged;
  that is not a check. **Worked case:** a brief's 5,000 rung named a whole skill as the thing being
  worked on. But the session had spent its day making the *measuring instrument* trustworthy and had
  only mapped that skill as a by-product. **The 5,000 was the instrument, not the patient, and the rung
  said otherwise.** A rung can look entirely reasonable and still be drifted.
  ⛔ **For ▲10,000, this check is NOT a re-derivation.** ▲10,000 is human-authored, human-only — a
  session never composes a replacement for it, drifted or not. The only legal question is **"is ▲10,000
  still faithful to §1?"** — a staleness check: read §1, read ▲10,000, and flag a mismatch. If it has
  drifted, that is a finding to raise, never a line to rewrite yourself.
- **CHECK 2 — WRITTEN FOR THE WRONG READER.** It can be accurate and still fail its audience. **The
  intended reader is a completely fresh session with zero context.** So: every proper noun carries a
  clause saying what it is — not *"the tester"* bare, but *"the tester, the thing that measures whether
  a skill performs well"*; **whole sentences, no fragments**; any term with more than one plausible
  meaning disambiguated in place. **Worked case:** a rung read *"never made one skill FAST"* — fast to
  *build*, or fast to *run*? Two different things in that project, and a fragment makes a blind reader
  guess. A full sentence would have had to pick one.
- **CHECK 3 — IT CONTRADICTS A DECISION THE PLAN ALREADY MADE.** A separate failure that neither check
  above catches. Check 1 compares the block against what the session **did**; this compares it against
  what the plan has **decided**. Read the plan's current phase and task list and ask of each rung: does
  this still name the objective the plan is actually pursuing? **Worked case:** a ground rung read that
  a phase was still slow. Every word was true and honestly derived — **but the plan had already
  recorded a decision to stop optimising that phase and move to a different question entirely.** The
  rung was accurate, well written, and aimed at a target the project had abandoned. It was caught only
  because the operator remembered. ⚠ Treat it exactly like a drift — draft the replacement from the
  plan's actual objective, and route it through the panel. **Never rewrite it silently:** a rung that
  contradicts the plan means the brief and the plan disagree about what the project is doing, and which
  one is wrong is not the session's call.
- **CHECK 4 — IS IT ALONE? ⛔ Run the tool; do not eyeball it.**
  ```bash
  python3 "$ROOT/system/tools/checkin/gauge_check.py" check "<abs brief>"
  ```
  Checks 1–3 ask whether the block is *right*. This asks whether it is **alone**, and it is the one
  check a session cannot talk itself past, because the verdict is an exit code. **On
  `COMPETING-GAUGES`, `OVERSIZED` or `STALE`: name the offending surfaces with their line numbers and
  refuse to report the brief clean.** **Why it had to exist:** one measured brief held **nine competing
  status surfaces**, four of them each claiming to supersede every block above — and checks 1–3 would
  have passed on any one of them. A perfectly accurate rung is still useless with eight rivals beneath
  it.
- **CHECK 5 — THE BOARD IS A QUEUE, AND A STALE QUEUE OUTRANKS A CORRECT RUNG. ⛔ Run the tool.**
  ```bash
  python3 "$ROOT/system/tools/checkin/board_check.py" "<abs brief>" --plan "<abs plan>"
  ```
  Checks 1–4 all audit the **gauge**. Nothing audited the thing a session actually acts on. **Measured:**
  a brief's rungs were rewritten and verified clean, and **the very next session still did the wrong
  work** — because the `❓ OPEN` bucket underneath still queued a task the plan had marked done. The
  operator had cleaned the one surface this skill inspected, this skill reported clean, and both were
  telling the truth. ⛔ On `STALE-OPEN` or `RUNG-ORPHANED`, **refuse to report the brief ready to hand
  off** and route every named id into the panel. ⭐ **A rung is allowed to say nothing is planned** —
  that reads clean, never orphaned; refusing an honest *"nothing queued"* would just train people to
  invent a fake id to pass the check.

**Report all five outcomes separately, never merged.** A rung can be accurate-but-fragmented,
well-written-but-drifted, aimed-at-a-retired-objective, not-alone, any combination, or fine — **and each
needs a different fix.** A single "the block is bad" verdict cannot tell the reader which one fired.

**The orientation receipt.** Name which blocks you read, whether this was cold or mid-session, and
anything absent — e.g. *"world model: FRAME · RULED-OUT · story log FULL (cold) · CURRENT STATE · rungs
present, no clarity issues, all current · OPEN LOOPS; missing: none."* **Mid-session, name the story log
precisely** — *"open forks + last 3"* — **never a bare SKIPPED.** A receipt that says SKIPPED reads
identically to a legitimate skip of the settled middle, which is what made the failure above invisible.

## Step 1.6 — Arm the plan

The brief's `plan:` frontmatter names the linked plan. Arm it for this session so the status bar shows
it. **Reading a plan into context does not light the HUD**, and entering plan mode to "load" one just
mints a new file and strands the real one.

```bash
bash "$ROOT/system/hooks/plan_flag.sh" set "<abs plan path>"
```

### Step 1.6b — No linked plan? Resolve it; don't skip.

**This step used to just skip, and that was the hole:** briefs mostly did not carry a `plan:` value, so
it skipped nearly every time — the HUD stayed blank and the flag fell back to a newest-mtime guess,
which names whichever parallel window saved last. Three skills read that field and nothing was writing
it.

1. **List the candidates** — the plans under `$DATA/plans/`, judged by their **title**, not their
   filename.
2. **Check for forked duplicates** — two plans covering the same work under different names. If you
   find forks, **name them all and say which you believe is live, and why.** Never merge them yourself;
   never pick silently.
3. **Offer to link one** — *"no plan is linked; `<name>` looks like this project's — link it?"* On a
   yes, **add** the line to the brief's frontmatter. **Never overwrite an existing value.**
4. **Nothing plausible?** Say so plainly and move on. **An honest blank beats a wrong pointer**, which
   sends the next session to the wrong plan.

> **Naming.** A live plan is `<slug>.plan.md`; a retired one is `<slug>.plan.<date>-retired.md` and is
> never the right answer. A `standalone-<name>.plan.md` is a deliberate project-less plan and has no
> brief to point at — its absence here is correct, not a gap.

## Step 1.8 — Compact the scratchpad BEFORE the diff

> **The reason for the order:** *"it's changing the situation too much."* The diff used to run while the
> pad was still full, so it compared the session against a brief that **did not yet contain what the
> session learned** — and then `/save` compacted afterwards, moving durable content **after** the
> comparison had already happened. The order was backwards. **Measured:** one pad ran **7 days
> uncompacted, 52,323 characters.** Every diff in that window compared against a brief missing all of
> it, and reported no tensions.

⛔ **The invariant this buys, and the thing to test any future edit against: NOTHING DURABLE MOVES
BETWEEN THE DIFF AND THE HANDOFF PROOF.**

⚠ The harvest in phase 3 stays **after** the diff — do not "fix" that later. It writes to the **pad**,
an ephemeral surface, not to the durable sections the diff compared. It is late on purpose: harvesting
well needs the picture the reconciliation builds.

### Two gates. Both must hold. Either one absent → do not compact.

**GATE 1 — is there anything to compact?**

```bash
python3 "$ROOT/system/tools/save/pad_archive.py" state "<abs brief>"
```

`PAD-DIRTY` (2) → compact · `PAD-EMPTY` (0) → nothing to do, say so, move on ·
`PAD-ARCHIVED-UNCLEARED` (3) → an aborted run; the clear is still owed, so **clear without
re-archiving** · **`CANNOT-READ` (4) → unevaluated, never clean.** Say the pad could not be read and
compact nothing.

**GATE 2 — did THIS window write to the pad?** ⛔ **Run this; never hand-hash the pad.** Hashing the raw
brief instead of the extracted pad returns a **silently wrong** verdict, so this imports the archiver's
own functions rather than re-deriving anything:

```bash
python3 - "<abs brief>" "<slug>" <<'PY'
import sys, os, glob
sys.path.insert(0, os.path.join(os.environ.get("ROOT", "."), "system", "tools", "save"))
import pad_archive as pa

brief, slug = sys.argv[1], sys.argv[2]
pad = pa.extract_scratchpad(open(brief, encoding="utf-8").read())
if pad is None:
    print("GATE2-NO-BASELINE (no scratchpad section)"); sys.exit(0)
current = pa.sha(pad)

sess = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
baseline = matched = None
for f in glob.glob(os.path.expanduser("~/.claude/run/pm/pm-*.flag")):
    kv = {k: v.strip() for k, v in (l.split("=", 1) for l in open(f, encoding="utf-8") if "=" in l)}
    if kv.get("slug") != slug or (sess and kv.get("session") != sess):
        continue          # slug alone can match another window on this project; session picks THIS one
    matched, baseline = f, kv.get("pad_sha_at_arm") or None
    break

# sha256("") -- the pad's empty fingerprint. A baseline equal to this was captured while the
# pad was genuinely empty, so a later match against it PROVES no write happened. A baseline
# that is anything else was captured with content ALREADY in the pad -- and because the first
# arm can land after the window has already been writing all session (arm fires from
# /project-manager, /checkin, /read, /save -- never at SessionStart), that content may be
# THIS window's own early writes, absorbed into what was supposed to be its "before" picture.
# Matching it back tells you nothing about whether this window wrote -- it is not evidence of
# either answer, so it must not be reported as "wrote nothing."
EMPTY_SHA = pa.sha("")

if matched is None or baseline is None:
    print("GATE2-NO-BASELINE (%s -- self-heals on the next run)" % (matched or "no matching flag"))
elif baseline == current:
    if baseline == EMPTY_SHA:
        print("GATE2-NO-WRITE (baseline was captured on an EMPTY pad -- this window has not touched it -- DO NOT COMPACT)")
    else:
        print("GATE2-AMBIGUOUS-BASELINE-DIRTY (baseline was captured with content ALREADY in the pad -- "
              "cannot tell whether this window wrote it before arming or it was already there -- DO NOT COMPACT, "
              "but do not tell the person 'you wrote nothing': say the check cannot determine it)")
else:
    print("GATE2-WROTE (this window wrote to the pad -- compaction is safe)")
PY
```

- **`GATE2-WROTE`** → compaction is safe.
- **`GATE2-NO-WRITE`** → the baseline was a genuinely empty pad, and it still is. This window has
  written nothing into the pad. ⛔ **Do not compact.**
- **`GATE2-AMBIGUOUS-BASELINE-DIRTY`** → the baseline was stamped with content ALREADY in the pad —
  which can happen because the first `arm` in a window often fires only near the end of a session
  (doctrine has `/checkin` run late), by which point the window may already have written the pad.
  The baseline then absorbs those writes and looks identical to "always empty." ⛔ **Do not compact**
  — same fail-closed action as NO-WRITE — **but say so honestly**: this check cannot determine
  whether the window wrote anything, so never report it as "you wrote nothing."
- **`GATE2-NO-BASELINE`** → the baseline is missing or unreadable. ⛔ **Do not compact this run** — but
  this is temporary. `pm_flag.sh` backfills the fingerprint on the next arm, so it self-heals on this
  window's next run, or immediately via `/save`, which has no gate 2 at all. **Fail-closed either way:
  the safe answer and the failure answer are deliberately the same answer.**

> ⭐ **Why gate 2 exists, and why the mode cannot carry it.** *"Why are you leaving it to a new window
> that is completely blind… you're asking a window that knows nothing about anything to make those
> decisions?"* Graduating a note — deciding it is a settled decision, a dead end, or an open thread —
> requires knowing what happened, **and it writes into an append-only log where a wrong call cannot be
> taken back.** The session that did the work is the only one that can graduate it. The obvious
> alternative, a self-assessed mode, cannot carry this: **a hash is not a self-report.** And it
> self-corrects with no declaration at all — a window that picks up at 09:00 and works until 18:00 has
> changed the pad by then, so it compacts because the artifact moved.

### The compaction itself

Follow the canonical procedure; do not reinvent it. **archive → verify → graduate → clear**, in that
order.

⛔ **No receipt, no clear.** `pad_archive.py archive` must exit 0 with a `RECEIPT` before one line
leaves the pad. On any non-zero: **compact nothing**, prepend a loud `> ⚠ COMPACTION ABORTED {ts}` line
to the pad, and say so.

⛔ **The clear is `pad_archive.py clear`, never a hand edit.** Code owns the delete: `clear` refuses
unless the pad's hash equals the newest archive block's, so it can only remove bytes it can prove were
saved. **A hand edit is a second definition of "the pad", and that is exactly how content was lost.**

⭐ **The clear is full.** Measured: of 116 substantial lines in one pad, exactly **one** predated the
previous clear — and it was the section's own header annotation, not a note. Clears have always been
full in practice.

```bash
python3 "$ROOT/system/tools/save/save_step_ledger.py" stamp compact "<abs brief>" --ns checkin --verdict DONE
# ...or, when a gate legitimately refused (a cold pickup that never wrote to the pad):
#   save_step_ledger.py stamp compact --ns checkin --verdict NOT_OWED
```

The stamp is **caused** by the archive, not asserted by you: it independently re-verifies the chain and
refuses if the evidence is not there. **A refusal here is a real failure.**

**Print one line, then keep going in the same turn** — a breadcrumb, never a question:

> 📝 **Compacted before the diff** — pad {N} chars → story log +{S} · board ✅{L}/⛔{K}/❓{J} · archive #{n}.

**If either gate fails, say which one in one line and move on** — *"pad dirty but this window never
wrote to it (cold pickup) — not compacting; `/save` will."* Silence here is indistinguishable from not
having looked.

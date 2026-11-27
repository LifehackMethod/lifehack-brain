# V2 Architecture Vision

> **Lives in V2 canon from 2026-11-22 (Enver's ruling); remove or rework before the merge to main.** Moved from the private ClaudeOps repo (`canon/v2-architecture-vision.md`).

> **Status: canon in V2, in a trusted location; evolving.** Born 2026-11-06 from the desk/presentation SOP
> rounds and the architecture teaching session; restructured the same day after his correction that rendering
> is delegated, not owned. This is the highest-altitude document in V2: everything else — the desk SOP, the
> interface spec (the presentation SOP), the plans — hangs from it. Where it and his words differ, the tension is surfaced to him; nothing here outranks anything else.
> Renamed from "V2 Architecture Draft" to "V2 Architecture Vision" by his ruling, 2026-11-08: this document
> declares the intended architecture; it does not describe the current system.
> Updated 2026-11-10 (step 4, the fine-china edit pass): Enver's 2026-11-09/10 rulings folded in: no outranking,
> the two walls, no enforcement, the three workers, the glasses pyramid, the GitHub fact, COMPASS as a seedling,
> the factory retired. Text taken out is archived word for word at `docs/v2/archive/v2-architecture-vision-archive.md`.

> **Not a product.** This is a free, open-source working library — a prototype for building one's own
> harness. There is no support. Customization belongs in your own layer, your settings and skills, rather than
> the platform; rework the shared code and it is yours to maintain: you broke it, you bought it.

---

## READ THIS FIRST — what this document is, and how to read everything after it.

This is the **V2 Architecture Vision**: a declaration of the intended architecture, written in the present tense as the finished system. The current system is the raw material the vision was drawn from; it is not the thing described. Where the current system falls short of what this document describes, the gap is kept, dated, in the debt ledger (the root `debt-ledger.md`), not in this text.

**Two top-level documents, no order between them (his framing, 2026-11-10).** The canonical principles are
the **laws of physics** — how stochastic systems behave, understood before building. This Vision is the
**rocket ship** — what Enver builds to work within, and beat, those laws. Both sit at the top level; neither
comes first.

**The rhetorical protocol is RFC 2119** (the internet's standard vocabulary of intent): **must** means an absolute requirement of the intended architecture; **should** means strong intent with a named reason to depart; **may** means freedom. This document speaks intent in these words and nothing harder.

**The canonical layer works like case law, not statute.** Code is logic — if-then, numbers, coded friction. The canonical layer is meaning — terms and what they signify. This Vision is the founding charter: it fixes the load-bearing terms and declares their intent. The rulings (the rulings records, the vetting records) are the case records — each settles a real dispute in Enver's words, and precedents *weigh, they don't bind*. The SOPs are the jurisprudence. The map, manual, and elements are the as-built record — facts, not meanings. Definitions here are deliberately incomplete: a term's full meaning accretes in its applications, so each glossary entry carries the term, its intent, and pointers to the rulings that have applied it.

**No outranking — tensions stay alive (his doctrine, 2026-11-10).** Nothing in canon outranks anything else: there are only levels of confidence, and evidence accumulates as points. When two documents disagree, the tension stays alive and is surfaced to Enver, never settled by a precedence rule. His words: "There is no such thing as outranking. There's just levels of confidence and gradation." And: "There is no card in the canon that nullifies all the other things."

**Designated trusted locations (his ruling, 2026-11-11).** COMPASS and this Vision are designated trusted locations: a line in them is canon because of where it sits, so the doubt bias never starts them from doubt. Everywhere else starts from doubt.

**The editing test — every sentence in this document is one of two things:** a *definition* (what a term means) or an *intent* (must / should / may). If it is neither, it belongs elsewhere: in code (if it is a rule), in the map (if it is a fact about today), or in the canonical principles (if it is a confidence-graded claim). You, the future editor, will feel the pull to write rules — resist it. Rules live in code; prose carries meaning.

**The naming principle (his ruling, 2026-11-12).** Wherever a metaphor or colloquial term is used, the correct technical term sits beside it in brackets: metaphor, then (technical term). The middle-altitude documents (the SOPs) add a third part, the real Lifehack Harness file; this document carries no file part, since it sits at the highest altitude. Car words carry the word "car" (car platform, car model, car trim and options).

**The amendment clause — the one binding rule, and it is about rules.** A **must** enters this document only through Enver's explicit, recorded yes — the system stops and asks before writing one, because anything a future reader will treat as a binding rule is load-bearing and must earn its place. Every **must** carries its reason, its change condition and "approved by Enver, <date>" beside it. There are no other binding rules here. Two scopes travel with the clause: every amendment re-derives the gap list (the debt ledger, the root `debt-ledger.md`, is a derived view, never left stale), and pointer discipline applies to load-bearing lines only — the claims whose checking matters carry their named pointer (ruling, file, or dated receipt); the rest stay prose, because a document whose every sentence is a link is a document nobody can edit.

---

## Where to look (the routing block)

- **Looking for intent — what the system should be and what its terms mean?** This document.
- **Looking for what exists today — the as-built system?** The map, the manual, and the elements (the
  organism layer): they hold the intended-vs-actual record.
- **Looking for friction — what guards and checks actually run?** The code and the SOPs.
- **Looking for why we decided — the decision trail?** The rulings records, the vetting records, and the
  Vision's own rulings file (a rulings file is the live notepad during a round; once each decision reaches its permanent home it is archived word for word, and the permanent homes are the record). COMPASS is the seedling these grew from: it
  retires once its content is persisted into the lower-altitude documents.

**Document hygiene (his doctrine, 2026-11-08):** live-instruction documents hold only what is current —
when a ruling changes, the document is rewritten clean and the old version moves word-for-word to a dated
archive nothing loads as live. On-demand records (the vetting notes) stay append-only: history is
their job. COMPASS is not one of them: what it supersedes moves word for word to its archive under
a do-not-act banner. An LLM that ingests superseded content is still biased by it — annotation helps humans; location
protects models.

---

## Background (his words, 2026-11-06)

- "Shared code layer, business logic layer and presentation layer was my best understanding, to be honest."
- His brother, a senior architect, on that architecture: "he kind of laughed and he's like, listen, you're
  programming for a stochastic environment. So honestly anything that you make up is going to be kind of made
  up anyway, there's not really an architecture for what you're talking about."
- And the correction that reshaped this document: "the presentation layer is actually deterministic, right?
  It's JSON and files... the only thing about the presentation layer is the way that it recombines the
  business layer and the shared code layer, because we're not doing the rendering at all. We're kind of
  offloading that completely and not taking responsibility for it."
- The pyramid/Pareto principle stays the standing meta-rule.

---

## Stakeholders and Concerns

- **The person — Enver.** The owner; his rulings are the case records, and his yes is the only way a **must** enters this document (the amendment clause). His concern: that the document says what he means, keeps its honesty, and never hardens into a rule-list he didn't rule on.
- **The blind LLM from the future.** The primary reader: zero context, no memory of these conversations. Its concern: definitions precise enough to reason with, intent clear enough to act on, and the register (must / should / may) unmistakable.
- **The future builder — a student or a new session building a desk, skill, or tool.** Their concern: where things go, what the platform provides, and what freedom they have — readable through the metaphors, decodable into the real terms beside them.

---

## Goals, Principles, and Constraints

### The headline: a deterministic shell around a stochastic core

A normal application is a **logic core with a dumb shell**: predictable inside, a screen that just displays.
V2 inverts it. **A wild animal in a very good cage.** The model — brilliant, creative, occasionally deranged,
never trusted on its own word — runs free inside. The cage (the platform's hooks, doors, validators, and
schemas, every bar measured — `~/lifehack-v2/system/`) is precisely engineered. Underneath the cage: a
library that writes everything down, dated, forever.

> **A deterministic shell around a stochastic core.** Inside the shell: vibes — the model thinks, explores,
> drafts, wanders, and its output is never trusted on its own word. At the shell: hard seams — every crossing
> between the model's world and the deterministic world is a typed, validated, guarded seam. Underneath, the
> knowledge is event-sourced and dated, with staleness made visible (the state taxonomy — View 3, toolkit
> item 5). The whole thing is headless at the client and tenant-owned in the middle.

You cannot architect a stochastic interior — no one can, and the brother is right about that. You don't have
to. **The interior is small; the architecture lives entirely at the boundaries**, and boundaries between
stochastic and deterministic components should be engineered rigorously. The kindergarten (the platform's
boundary checks) doesn't control the children; it controls the doors — and the door checks don't predict every
crazy thing a kid might do, they check everything that passes, so even the unimagined thing still has to get
through.

This is why the pyramid/Pareto principle is structural necessity, not taste: because the interior cannot be
specified, the only leverage is a few strong high-altitude principles plus hard seams.
**Strong boundaries, weak interior.**

### The billionaire principle (canonical-system ruling 15, ruled 2026-11-10)

*(Moved 2026-11-10 from the canonical-system rulings record, item 15.)*

There is no human-out-of-the-loop, and that is the product, not the limitation (the floor below is what no machine can supply). The floor is irreducible — articulate vision, rule on
exceptions, hold the ranking — and it includes coordination and light housekeeping: a billionaire running many projects still has coordination overhead, and being treated like a billionaire does not mean zero admin (see the intelligence map below, HUMAN only, 3. Coordination and 4. Housekeeping). The harness's measure is a large machine output per small human attention,
with nothing below that floor ever needing the human.

### The INTENTION doctrine (LOCKED 21)

Every significant choice carries its **why** and its **change condition** beside it. *Why:* reasons carry
better than facts — one good reason lets a future session work out situations nobody wrote down, in situations
nobody imagined. The change condition says what would justify changing the choice, so revision is a ruled act,
not drift. You will see these as "Intention:" and "Change condition:" lines throughout.

### The harness as a leader (nice to have, not required)

Where it can, the harness leads rather than follows: it explains, teaches and points out setup not yet done,
the way a technical lead would for someone new. Enver, 2026-11-16: "Icing on the cake it's not a required
functionality".

### The two-walls doctrine (canonical-system ruling 17, approved 2026-11-09)

Two containment layers: **shared code constrains actions; shared knowledge constrains meaning and choice.**
*Intention:* trustable behavior that does not depend on model size — with both walls in place, the intended consequence is a
smaller daily-driver model. *Change condition:* a rig run showing a constrained smaller model
matching an unconstrained frontier model on the same task.

### Constraints

- **The honesty constraint:** canon reads as working, and every gap between it and what runs is kept, dated,
  in the debt ledger (the root `debt-ledger.md`).
- **The friction-not-impossibility constraint:** friction is for the unsophisticated user and the
  well-meaning dumb LLM; the system does not prevent a determined person from breaking their own system
  (the system guards against accident, not against a person's own deliberate choices). Shipped canon holds in this sense: each plugin update replaces it
  whole; a determined student can still edit it locally, giving up updates.
- **The no-enforcement constraint (his doctrine, 2026-11-10):** there is no enforcement in the system, only
  acceptable conformance and performance; a test's final result that reaches acceptable conformance is valid
  and usable. His words: "there is no such thing as enforcement in the system. We just have acceptable
  performance." And: "It has also to do with trying to preserve meaning rather than just turn things into rules."
- **The anti-rule-list constraint:** the Vision declares definitions and intent; it does not accrete into a
  list of rules. Rules live in code (the canonical principles SOP's Frame: "rules live in code; prose carries principles
  with their reason").
- **Audience constraint (LOCKED 4):** one document, both audiences — future-Enver-in-six-months and the blind
  LLM. Dummy primers stay as sections.

---

## The Target Architecture

### The shape (two owned layers, one served interface, rendering delegated)

The old name — "three-tier architecture" — was borrowed from an enterprise idea that assumes you write your
own UI. V2 deliberately doesn't. The honest shape:

- **Two layers we own:** shared code and business logic.
- **One interface we serve:** the headless data contract — architected *into* the shared code layer.
- **One thing we delegate and do not own:** rendering — the CLI, the app, VS Code, any renderer a user
  builds, and the LLM's stochastic act of displaying within them. Out of scope, unpolicied (his words: "the CLI
  and app. Stochastic, so it isn't something conformance polices" — conformance polices writes, not
  rendering; but a view that writes is a write, and the rule applies). We birth the healthiest baby — a clean
  contract, honest data — and what anyone does to display it is their business.

In industry terms: a **layered architecture** (the dependency rule: layers call downward only, never up,
never sideways — separation of concerns), organized as an **ownership model: platform / tenant / client**.
The distribution shape is the **car platform, not the enterprise apartment building** (LOCKED 1): the product
is distributed, and **each installer runs a single-tenant instance** of the same platform — one design, many
owners, the way a car platform ships to many drivers. There is no shared building with neighboring tenants;
there is one factory and one car per owner. The car is all four layers together, so one owner's whole setup
is one car. Every student subscribes to the Harness's GitHub repo, by pulling it
down or installing the plugin. The system works fully without a GitHub account or a repo of their own, and nothing
is built around one. A student who wants their own repo can add it; the door is open, but it's an optional extra
almost no one will use. **Headless at the client**, where the client is genuinely
somebody else's product.

### The Platform (the shared code layer)

**Dummy version:** This is the **car platform** — the chassis, the drivetrain, the factory that builds them
(the plugin, `~/lifehack-v2`). Every car is built on it, it's identical for every owner, and it's engineered
**once**, because you only ever want one chassis: if every owner welded their own, you'd get the
copies problem already lived through (a census on 2026-10-29 found 62 copies of shared tools, 51 of them drifted). And like a car platform in the real world, a major
factory defect goes back to the manufacturer — a **recall** is a plugin update: one fix is offered to every car, and the system proves it arrived,
and no owner ever repairs their own chassis. Job description, one sentence: **if it should behave the same
for everyone, it lives here, exactly once.** The guards, the validators, the loaders, the job runner, the
diary pen, the doors.

And the platform also includes the **viewing gallery's front desk**. The factory has no windows of its own
and doesn't tell visitors how to look at the art. What it owns is the placard at the entrance: "everything in
this building is documented in this format, dated this way, trusted at these levels." That placard — the data
contract, the envelope assertion, the single writer that checks every write against it, and one deliberately plain example tour
(`/dashboard` — the reference implementation) — is part of the platform, because it is true for every
tenant and every visitor identically. What is **not** part of the platform: the act of looking. Visitors
bring their own eyes. The example is **plumbing, not painting** — it demonstrates the contract; it is not the
rendering we own. It is also a **starter template** (a functional default): the system ships working, with a
simple first step already built — and a default never precludes building your own and hooking it up.

So: **all the machinery, plus the honest labeling system, plus one example of reading the labels.** Never
contains: anybody's personal stuff (the update lifecycle destroys it), and anybody's
way of seeing.

**The platform door.** The repo is restorable by design — a recall overwrites it whole, so corruption is
never permanent. But restoration is silent: it repairs damage after the fact and announces nothing. The
write-guard on platform paths exists to make the attempt visible at the moment it happens — a tripwire that
tells you when to use the repo, not a wall the repo makes redundant. (The guard's exact coverage is
as-built detail: the map's runner notes.) The one exception is the operator's own hands at the terminal,
structurally distinguishable from model input and logged: it bypasses approval, never the pen, and there is no
administrator-key machinery.

**Technical summary:** the **platform layer** — shared, deterministic services, one implementation of each
capability (**single source of truth**, copy-blocked and commit-gated). A single **register** lists every hook,
tool, skill and job; the wiring files are generated from it, never hand-edited. Explicitly includes the **interface
machinery**: the **data contract** — which per the Step 0 ruling (LOCKED 11) is the pen's lightweight
**envelope assertion** itself: `emit_status.py`'s fixed set of envelope keys (the exact count and list live
in the contract — the code), and the code is what runs; check it. The **JSON Schema
file is withdrawn, with a named out-point**: extract `status-tile.schema.json` from the pen's rules the day a
non-Python consumer or a second developer appears. Plus the **single-writer** validated
path (`emit_status.py`) and the **reference implementation** (`/dashboard`). **Rendering is not in this layer
or any owned layer** — delegated to external consumers, out of scope. Boundary rules stand: nothing personal
enters; everything crossing outward is typed, validated, dated.

**Intention:** one implementation per capability exists because the copy problem is lived history (62 copies
of shared tools, 51 of them drifted, census of 2026-10-29), and because a single-tenant-per-installer distribution means the only way to fix everyone's
pipes at once is to ship one set. **Change condition:** a second implementation of a capability earns its
place only when a real, named conflict between installers' needs appears — not on speculativeness.

### The Tenant (the business logic layer)

**Dummy version:** *Your car, optioned your way.* Same chassis, same drivetrain as every other car —
but three of the four car layers are yours, all inside the tenant: the **car model** (personal code layer),
the **car trim and options** (configuration layer: desks, personal skills, settings), and the **driver's logbook**
(knowledge layer: the brain folder) — the business logic layer's sanctioned customization points. Another owner specs theirs
completely differently and neither affects the other — that's the point of the layer. Two things true at
once: everything in your three car layers is **yours to change freely**, and none of it can **re-weld the car platform's chassis** — you
can't modify the platform, because the platform isn't yours. "Business" in the industry sense is just *how
your life works* — investing, auditions, books. It's the biggest layer by content and the smallest by
machinery: mostly prose and settings, because machinery belongs to the factory.

**Technical summary:** the **tenant layer** — per-person **configuration and domain logic**: personal skills,
defaults, desk manifests, personal knowledge, personal tools, and the *contents* of status tiles (the payload
data). The **dependency rule** consumes platform services downward and never modifies them (speed-bump
changeable at most). The intent is update-safety: a platform update should never destroy tenant content, and
tenant content **should** never break platform machinery — the dependency rule and the platform's doors exist
to make that true. The tripwire: a tenant consuming platform internals —
a hand-built shim around the pen, for example — is the signal that the boundary is eroding. Each
installer runs a single-tenant instance (LOCKED 1), so cross-tenant interference is
not a live failure mode to police.

**Intention:** the tenant layer is where a person's life actually lives, so its defining property is
changeability without blast radius — free above, untouchable below. **Change condition:** if a tenant change
ever does break the platform, that's a platform door missing, and the fix is a door, not a rule for tenants.

### The Client (the interface — what we serve, not what we own)

**Dummy version:** The museum's placard and its rules (the headless data contract) — not the viewers. The contract says: here is the
shape of every status note, here is its date, here is its trust level, and here is one plain example of
reading it. Anybody can look — a curator with inventory sheets, a tourist, a kid with a phone. The museum
takes no responsibility for how they see; only that the labels are honest. And the one iron rule at the
boundary: **looking is free; touching goes through the door** (reads are free and inert; writes go through
the validated path — the write door). If a viewer changes something through a view, that's their hand in the
collection, and the cage rules apply.

**Technical summary:** the **interface** is the **headless data contract** — the pen's lightweight
**envelope assertion** (the fixed set of envelope keys checked on every write by the single writer; per
Step 0, LOCKED 11, this assertion *is* the contract — the JSON Schema file is withdrawn with the named
out-point: extract it the day a non-Python consumer or second developer appears), open payload, single atomic
validated writer, derived staleness, honest-absent, provenance/confidence labels — plus the **reference
implementation**. All platform-side machinery. Consumers are **loosely coupled through the contract alone**,
strictly **pull-based** (rendered on demand, disposable), **read-only by default** — **read/write separation
through a validated path** (queries free and inert; commands through a hard-hooked door). CQRS is the
industry name for a neighboring idea — a related pattern, not what we built (LOCKED 19, B2). The interface
spec is `status-emission-sop-draft.md` in the drafts folder — the spec of the contract we serve, not of a
layer we own.

**The three writes and their folders (LOCKED 10).** One run → three artifacts, and no two are the same
artifact, so nothing is stored twice:

- **Evidence** → `records/` — topic-named, never expires.
- **Story** → `diary/YYYY/MM/DD.md` — dated, append-only.
- **Glance** → `status/<producer>.json`, at the brain folder's root — producer-named, overwritten.

The naming rule follows from the artifacts: diary pages are dated; tiles are named for their producer. The
tile's folder is central (`status/`, at the brain folder's root), not in the desk folder. And the seam rule for the contract:
**envelope is fixed by the platform; payload is the skill author's business logic, declared at build time — the
platform provides mounting points, not gauges** (the car-platform mapping: the platform ships bolt-holes and
a wiring harness; what you mount on them is yours).

**Diary provenance (LOCKED 2, principle):** diary entries should cite the evidence that caused them, with
provenance labels and the confidence ladder running to the foundation (case record LOCKED 2, Marc's lane).

**Intention:** the interface is served, not owned, because rendering is stochastic and somebody else's
product — the only durable thing we can promise is that the labels are honest and the writes are guarded.
**Change condition:** the day a second consumer or a second developer appears, the envelope assertion
graduates to the extracted JSON Schema file (the named out-point) — same contract, stronger form.

### The products of the harness

What people build with this platform, named: **skills** (LLM-language capabilities built on the scaffold),
**cron jobs** (scheduled, unattended runs), **tools and scripts** (deterministic utilities), **notes and the
diary** (the knowledge folders), **records** (topic-named evidence), and **JSON status tiles** (the glance).

Products follow the **producer split** — ingest, process, emit — with the emit always through the single
writer (the pen, `emit_status.py`). And every product is built on the **scaffold**: the skill template
(`system/templates/skill-template/`) plus the per-skill spec sheet
(`system/templates/producer-spec-template.md`) — the platform provides the shape, the tenant fills it.
The scaffold standardizes mounting points, never prose.

---

## The Views

One architecture, several seats. Each view is the same system seen from one concerned angle.

### View 1 — The Division of Labor: who does what, and where they meet

*(Enver, 2026-11-07: "super load-bearing." Absorbs and retires the Code/LLM Seam insight document of
2026-08-05, which remains on disk as the archive; the rule block below is held byte-identical in the autoplan
and build skills by a pre-commit check.)*

#### The three modes

Every piece of work in this system is one of exactly three modes:

1. **The model alone.** It thinks, drafts, discusses, free-associates — with a human or alone. No code
   watching. Where creativity lives.
2. **Code alone.** Plain software: fast, free, exact, dead stupid. Where repetition lives.
3. **Code wrapping a trapped model — the hybrid.** A script runs the sequence; at one step it makes a small,
   caged model call — a question, a menu of allowed answers, a watchdog, a check on return. The strongest
   coding pattern we have — harder to build, but the best.

Most confusion in AI-system design comes from not knowing which mode one is in.

#### The three workers, honestly

*(Amended 2026-11-10, canonical-system ruling 13: the two-worker grid becomes three, with the human as the third
intelligence. The full intelligence map, every region and overlap, is in this same document, in the "The intelligence
map — the full map" section below.)*

**The human — good at:** intent, ranking, taste, the gut-level "something's off". The only source of intent,
values and taste; knowing what matters when two true things fight.

**The human — bad at:** attention, memory, presence: a very small context window. This is what the harness
exists to help.

**The model — good at:** anything where the world varies. Fuzzy matching. Ideation, free
association, pattern-matching across contexts. Reading anything. Self-repair: when the world shifts and
something breaks, it improvises a fix — a system that heals itself imperfectly beats a system that fails
perfectly.

**The model — bad at:** judgment: it has none. In the intelligence map's words, "it is knowledge so vast it
*seems* to have judgment." Also arithmetic (expensive AND bad at it — never let it do math; hand it code). Exact
repetition. Counting. Remembering across sessions. Following instructions reliably — it will satisfy the
letter of a check without doing the work. Running cheaply. Staying honest without a check: without a legal
way to say "I don't know," it renders uncertainty as a confident fake decision.

**Code — good at:** the identical answer, every time, forever. Enforcing what it can, inside its own deterministic bubble, not system-wide.
Sequence nothing can skip. Speed, cost (free), counting, math, measuring. Remembering state mechanically.
Running alone, unattended, for years.

**Code — bad at:** nuance (the fifth `if` in a row means judgment leaked in three branches ago). Anything
novel — it dies at the first surprise and cannot repair itself. Reading prose. Creativity, taste, intent.
Being owned: every line is a permanent obligation, and this system has ruled out a maintenance team.

#### The map — with the workers overlaid

```
                          FLEXIBLE
                             │
     THE MODEL lives here ───┼───── the HYBRID lives here
     ✅ classify, nuance,    │      (flexible AND load-bearing)
        fuzzy matching,      │
        creating, improv-    │      ✅ the model's sorting
        ising, healing       │         inside code's frame
        itself               │      ❌ expensive — nature left
     ❌ math, counting,      │         this corner empty; we
        repeating, memory,   │         build it with machinery,
        cheap runs, trusted  │         only when a feature
        without a check      │         needs BOTH
                             │
  NOT LOAD- ─────────────────┼─────────────── LOAD-BEARING
  BEARING                    │
                             │
     nobody                  │      CODE lives here
     (useless corner)        │      ✅ identical forever,
     ❌ everything —             │         sequence, speed, math,
        don't build here     │         free, runs alone unattended;
                             │         enforces what it can,
                             │         inside its own bubble
                             │      ❌ nuance, novelty, reading
                             │         prose, self-repair —
                             │         and every line is a
                             │         permanent chore
                             │
                          BRITTLE
```

The workers sit on opposite corners because **flexibility is what the model has and code lacks;
load-bearingness is what code has and the model lacks.** The top-right corner — flexible *and* load-bearing —
is empty in nature. The hybrid manufactures it: the cage welds the model's strength to code's strength, each
covering the other's weakness — code cannot sort the fuzzy, so the model sorts within code's fixed set; the model cannot be trusted, so code
checks.

#### The grid — seven regions on two axes (canonical-system rulings, the grid view, ruled 2026-11-10)

x = how much of the human it costs; y = how much it can be trusted.

- **Top-right (costs you, trusted) — AGI:** all three together (the human's judgment, the LLM's knowledge, code's
  rails; every harness session opened from a launcher), and human + code only, the vault, for secrets that must
  never enter LLM context.
- **Top-left (free, trusted):** code only (the human, deferred: judgment put into code earlier; failure word:
  brittle) and Code+ — code on steroids (code runs the show, the LLM in sealed bubbles).
- **Bottom-left (free, untrusted):** LLM only, YOLO vibecoding.
- **Bottom-right (costs you, nothing in the system):** human + LLM only (basically coding, the outside session)
  and human only (your head).

**LLM+ (the Anthropic harness)** has no seat of its own: the engine every session runs on, inside the top-right.

User mode lives in two seats: AGI and code only. **One-line story:** the bottom-right costs you and gives you
nothing back; the top row is where the value is. The harness moves work out of the right column and up into the
top row. The full map is in this view, below.

#### The intelligence map — the full map (FINAL, ruled 2026-11-10; supersedes the interim seven-regions and quadrant drafts of 2026-11-09, preserved word-for-word at `archive/canonical-system-rulings-pre-final-map-2026-11-10.md`)

*(Moved 2026-11-10 from the canonical-system rulings record: the intelligence map — heading, disclaimer, regions M0–M9 and their standing rules — landing as ONE section with the grid view above.)*

**HUMAN only**

**Good at:** the only source of intent, values, taste. Knowing what matters when two true things
fight. Sensing something is off before being able to say why. Committing and standing behind it.
Total control — everything done alone is exactly what you want.

**Bad at:** remembering what you want; holding context, many projects, massive inputs — a very small
context window. Forgets, absent. *This is what the harness exists to help.*

**Responsible for:**
1. **Judgment.** The human has judgment; the LLM has *zero* (the line is carried in View 1, "The model —
   bad at"). The leverage of the AGI combination is the human's judgment (with relatively
   little knowledge) combined with the LLM's knowledge (with almost zero judgment). The human steers
   the ship.
2. **Framing.** The human can hold a high-altitude end goal, break it into medium-altitude goals,
   subdivide down to the immediate goal, and re-update all of it instantly as things change. The LLM
   cannot — it gets pulled to the lowest altitude and wanders: the **infinite side quest**. The human
   holds the frame and reframes the LLM when it gets lost.
3. **Coordination (the billionaire's administrative friction).** Treat the human like a billionaire —
   that does not mean zero admin. Ten free employees is not less work; it is more output with more
   coordination. The human is the coordinator: articulate the vision, rule on the exceptions, hold
   the ranking.
4. **Housekeeping.** Keeping the closet clean: hang the clothes back up. Save the session, do the
   five minutes at the end, enable the skills at the start — a small amount of operational knowledge
   and maintenance discipline now, to avoid a nightmare later.

**CODE only**

**Good at:** the identical answer, every time, forever. Enforcing what it can, inside its own deterministic bubble, not system-wide.
Sequence nothing can skip. Speed, cost, counting, math, measuring. Remembering state mechanically.
Running alone, unattended, for years.

**Bad at: brittle** — one word that encapsulates all of it. If something breaks, it stays broken; it
cannot fix itself; it needs an outside input. It can be 99% complete and still not run — one bug and
nothing works; it must be nearly perfect before it runs at all. And it is brittle in its inputs: one
character off, and it can break.

**Responsible for:** the rails — the boundary with the intelligence contained inside, keeping every
session on the tracks via the hooks and the shared code layer; without it the whole thing becomes a
mess fast. At the middle altitude: the cron jobs and all unattended operation.

**LLM only**

**Good at: Google on steroids.** Fuzzy matching; free association and pattern-matching across
contexts and its massive training data; ideation and brainstorming; *teaching* on subjects it was
trained extremely well on (when a human's judgment chose the subject); generating code. When pointed
at what it's good at, it's incredible — with **jagged intelligence**: unbelievable at one thing,
terrible at the adjacent thing, equally confident about both. Used well, it is a **multiplier for the
human**, and the human is the multiplier variable: a zero (vibe coder) wastes tokens and crashes; a
junior gets something slightly better; a senior software architect is *lethal*. The shared knowledge
layer doesn't turn the human into a senior architect; it prevents the human from being a zero — the
bare-minimum guardrails so the whole thing doesn't collapse on itself.

**Bad at:** **confidently wrong** — the main failure mode. No judgment, no real world model; it will
confidently take you down a **circle of confusion** and a **maze of side quests**. It gives
deterministic solutions for stochastic problems. It doesn't even know what it is — stochastic
harnesses are too new to be in its training set, so it sizes itself up wrongly, constantly. It seems to
lead, but it's really following — chasing your tail. Fantastic at **coding**, terrible at
**architecting**, because architecture requires the judgment and creativity it only appears to have
(its creativity is the internet's creativity, recombined). Full canonical detail: the LLM sections of
`canonical-principles-sop.md`.

**Responsible for:** ~95% of what happens inside a session — the reading, drafting,
classifying-under-instruction, proposing. Plus the Code+ bubbles.

**ALL THREE together — AGI**

**Good at:** **This is AGI.** Code + human + LLM working together, in the right balance — the
trifecta. The human's judgment, the LLM's knowledge, code's rails. The moment a session opens from a
desk launcher, all three are convened: the train running on the tracks. Where the most trusted things
(rulings, the registry) live.

**Bad at:** it is still dependent on the human. Outputs track the human-knowledge multiplier:
garbage in, garbage out. The AGI is not guaranteed — it scales with the judgment and creativity the
human brings.

**Responsible for:** the operation of the Lifehack harness.

**HUMAN + CODE only — the vault**

**Good at:** rare, and a headache. The human circumventing the harness and any LLM entirely — the
terminal window — for reasons of privacy, permissioning, or security. The top case: information that
must never be ingested into an LLM session (keychain data, passwords). This may be
the best exclusion mechanism we have.

**Bad at:** very high-touch, and for a non-developer it is scary and annoying. Use only when
exclusion is the point.

**HUMAN + LLM only — the outside session**

**Good at:** rare by definition — does not exist inside the harness (a harness session is all three
by definition). A one-off throwaway session outside the harness: leverage the total, unrestrained
intelligence of the weights, completely unbiased by the harness, sandboxed away from everything else
so it can't break anything, on a fully prescribed job (coding a website, visual design — the plan
carries the restrictions).

**Bad at:** YOLO operating outside the harness — insecure from the outside (no guards against what
comes in) and from the inside (no hooks: a destructive edit could be catastrophic for your data).

**LLM + CODE only — one region, two modes**

**Mode 1 — LLM+ (the Anthropic harness).** The LLM runs the show and code is subordinate: tool
calls, the loop, all of it. The default mode of the Claude/Anthropic harness — Anthropic already did
the heavy lifting; we don't need to build or worry about this. LLM+ is simply *the Anthropic
harness, period, end of story.*

**Mode 2 — Code+ (code runs the show, LLM subordinate and sandboxed) — the new frontier.**
Deterministic code carrying small, sealed LLM call-outs — reasoning
bubbles inside a code string, summoned for exactly the one thing code can't do (fuzzy matching,
complex if-then sorting within a fixed set), then control returns to code. Code gets an **insane multiplier** from
this — a step function, not a little bit better — and the LLM does not get better from calling code,
which is why the "+" belongs to code. (The unlimited-money line is carried in this view's "The honest confession — the
ideal vs. the affordable".) That is not what the Lifehack harness is — we chose a stochastic harness —
but we can still leverage pieces of Code+ inside it. The handoffs between LLM and code in Code+ are *very precise* (seam-rule territory).

**The modes overlay**

Using the system and building it are two modes, with an invisible line between them. The detailed rulebooks stay in the background and are read when someone moves into building, rather than loaded into every conversation. *(Approved by Enver, 2026-11-27.)*

**Standing rules for the map**

1. **Trust rule:** carried in COMPASS P-1.
2. Things are born at the edges and migrate inward.
3. Trust always traces back to a human touch — present, or deferred into code a human wrote.
4. Placement is endorsement — carried below, in the "Placement is endorsement" paragraph (item 16).

**Placement is endorsement** *(moved 2026-11-10 from the canonical-system rulings record, item 16; "rank" wording
replaced with placement wording per the no-outranking doctrine, item 7)*:

The act of putting a thing somewhere is itself a ruling; authority is inherited from the hand that placed it.
The system obeys regardless — placement records PLACEMENT (where a thing sits, never precedence); it does not
grant permission. This is what the tier prefix carries.

#### Placing a feature — the two questions and the modifiers

Ask about the *feature*, not the worker:

1. **"Do I need this to be load-bearing?"** — if it breaks or lies, does anything care? Does it run so often
   that tiny faults compound? No → left. Yes → right.
2. **"Do I need this to be flexible?"** — will tomorrow's version of this task differ from today's? No →
   bottom. Yes → top.

Build with whatever lives in that quadrant. Then apply the modifiers — tiebreakers that adjust placement:

- **Frequency multiplies everything.** A check running a thousand times a day belongs in code: a thousand model
  calls is a thousand small bets and a real bill.
- **Depth of the task.** Shallow (pick-one) → the menu, cheap. Deep and exploratory → the pure model; do not
  pretend a menu could hold it.
- **Token cost per run** — the model's meter always runs; code's never does.
- **The obvious shortcuts:** math → code, always. Counting → code. Reading a messy document → the model.
  "Which of these many things matches" → a trapped model call, menu of the many, check on return.

**The burden of proof sits on claiming load-bearing.** Everything feels important when being built, and
over-claiming is how one-person systems drown — the top-right is where money and machinery go. When in doubt,
start in the cheap quadrant and let a real failure promote it.

#### The honest confession — the ideal vs. the affordable

If we could afford the perfect version of this system, **the entire thing would be deterministic code with
imprisoned model steps inside it** — code owning every sequence, record, and state change; the model appearing
only as trapped calls at the exact steps needing a classification within a fixed set. That is theoretically the correct architecture, and
we are not building it — it would take a team and years, and most of the system does not need that much armor.

So the real architecture is: **the imprisoned-model cell — the strongest coding pattern we have, harder to
build, but the best — deployed surgically, only where variation × criticality × frequency intersect, with
cheaper modes everywhere else.** The thinness is
deliberate: the models and harnesses underneath will be replaced, constantly. The durable assets are the prose
and the thin standards; the code and the models are deliberately disposable. The seam is small so replacing
either side is cheap.

#### The seam rule — the hybrid's contract

<!-- SEAM-RULE-v1 BEGIN -->
**Code hands the model a bounded set of outcomes. The middle is unbounded — the model, alone or in
conversation with a human, works however it needs to. What comes back is one of those outcomes, and the set
includes one meaning NO OUTCOME WAS REACHED, so a stall never reads as success; otherwise a stalled step looks identical to a finished one. Code checks membership on every path in; anything off-list
is surfaced, never silently absorbed.**
<!-- SEAM-RULE-v1 END -->

The no-outcome member is what lets the model tell the truth — without it, "I don't know" has no legal
expression and gets rendered as a choice. Status: **OBSERVED** (a 107-finding audit found not one case of a
model slipping an off-list value past a check that was actually wired); the *shape* is externally
corroborated (practitioner convergence, 2025–26), the NO-OUTCOME member specifically is untested outside
this system. Universalizing it remains a candidate, not settled. **A legal answer is not a true answer:**
membership demonstrates parseability, not correctness — that gap belongs to sampling and fold-fail-closed, kept
separate on purpose.

Its companion — the format doctrine (canonical principles §7.0b): **prose is where meaning lives; structure is
where trust lives.** Crossings from prose into structure pass a check (the moment untrusted output enters the
trusted world); crossings from structure into prose are free (a wrong rendering is inert). The seam rule and
the format rule are the same boundary seen from two sides — one governs answers, the other governs
information. Neither is complete without the other.

*(The placement table — this view's proof of work — is as-built material: it belongs to the map and the
elements, whose job is the intended-vs-actual record. The intent here: the table should be DERIVED, not
compiled — generated by code from the system's own emitted receipts, never hand-maintained.)*

### View 2 — Security: three threats, two planes, honest gaps

*(LOCKED 21, ruled 2026-11-07. Low-altitude document: `canon/security-canon.md` in the sandbox — this view is
the doctrine; that file is the machinery.)*

#### The three-threat model

Security here is not one problem but three, and confusing them is how one-person systems buy the wrong armor:

1. **Threat 1 — the outside attack.** The traditional threat: someone out there wants in. Defense: there is
   nothing hosted and no doorway — nothing to attack at range. This is not a fortress wall; it is not being a
   target with a face.
2. **Threat 2 — the friendly idiot.** The blind LLM, careless rather than malicious: it will paste a
   credential into a log, follow an instruction in an email, delete the wrong folder with total confidence.
   Defense: the doors — every action crosses a checked, validated seam.
3. **Threat 3 — the multiplication.** An outside attack that tricks the blind insider: prompt injection, the
   attacker's text riding the trusted model's hands. Defense is breaking the combination: **sanitize what
   enters** (the ingest gate), **separate reader from actor** (the thing that reads untrusted content has
   nothing to act with), **guard what exits** (per-call doors on actions).

*Why this framing:* the threats need different defenses, and the expensive one (enterprise hardening against
Threat 1) defends the threat this system least has. Named threats keep the spending honest.

#### The posture

**Pareto, not enterprise.** On-prem with one named exception — Google sync — accepted, named, not hidden.
**Minimum surface area, not zero.** The goal is the smallest defensible surface that keeps the system
functional, not an air-gap that lobotomizes it.

#### The two planes

- **The ingest plane — Sentinel's inbound gate (the inbound security lane).** Content entering the system passes through
  **Sentinel's inbound gate** — the full multi-stage check pipeline (the airport lane: mechanical scrub → injection scan →
  tool-less judge reader → quarantine; ID check, luggage scanner, x-ray, pat-down). It is **the highest level
  of policy friction we can create**: everything inbound clears the full scan, pasted or dropped material and
  MCP calls included, with no named exceptions. What passes is **trusted inside** — a known, accepted risk: the
  goal is deterrence, not 100% security, exactly like airport security. The canonical documents:
  `system/information-ingestion-interpretation.md` (the intake spine), `canon/security-canon.md` (the full
  architecture and channel map), `system/ingestion-reader-contract.md` (the reader spec); the friction point:
  `system/hooks/ingest_gate_enforce.sh`. This is **structural, not optional** — the lane is the
  architecture, not a setting.
- **The action plane — the write door and per-call friction.** All writes go through one validated path (the
  write door, LOCKED 9): queries are free and inert; commands pass a hard-hooked, validated door. Actions
  leaving the model's hands get **per-call friction, in levels, lightest first, chosen by the person**: sign,
  speed bump, reason gate, door, pop-up, hard block (the LOCKED 20 door framing; the pop-up sits just before
  the hard block), layers of friction because nothing is perfectly controlled in a stochastic environment.
  Fine china gets three protections, all "to prevent broad catastrophic events from a misguided agent":
  **fine china protection A**, "can't edit it without talking to the human first" (ask before an edit);
  **fine china protection B**, "can't delete it" (no delete); **fine china protection C**, a speed bump with
  a sign in front of a mass delete — a whole folder or hundreds of files — on any folder, to slow a possible
  catastrophic event down; it is never a hard block or a pop-up (his ruling, 2026-11-13). Which things get
  protection A or B is chosen by the person (narrow and human-named); protection C covers any
  folder; what each protection does is fixed (for canon and fine china outside git, protection B is a
  hard block with no override). One rule governs every mode that quiets the guards (overnight, long-chain
  runs): anything de-prompted resolves to **silent-deny-with-sign** — never silent-allow, never
  timeout-allow. A guard that quietly stops asking should answer "no" on the occupant's behalf, with a note
  left on the counter. Why: a de-prompted guard that answers "yes", or waits out a timeout, turns the absence of a person into permission. Fine china protections A and B are denied with a sign and parked for the morning, and
  the run carries on; protection C's sign refuses the first attempt to delete a whole folder and names the safe route (move it into an `_archive` beside it), and a later attempt is an ask, which with nobody at the screen is a refusal, so the session stops and tells the person; hard blocks
  are always denied.

*Why two planes and not one perimeter:* inbound content and outbound actions fail differently — content
needs one strong lane, actions need many light checks — and one perimeter would over-police one and
under-police the other.

#### The reader-actor split is structural

The reader-actor split — the component that reads untrusted content has no tools to act — is **structural by
ruling: it cannot be optional or per-desk** (his ruling: "it cannot be optional"). The mechanism has **no third-party dependency** — same model, same machine. The containment
layers (NTFY alerts, Gmail quarantine) degrade visibly when their external dependencies fail, but **the
prevention should never degrade**.

#### The provider plane

External providers (Google, Microsoft, Dropbox) are **tenant choices**. The platform defines the interfaces
and suggests **Google**: the system was built for Google, and other providers have worked with light
customization; it stays off until the person sets it up. Alternatives are permitted but unsupported. **Graceful
degradation:** the core works without any provider. *Why:* provider churn is the tenant's life, not the
platform's; the platform's job is the socket, not the appliance.

#### The credential slot

**Store** = **tenant layer**; reader interface = **platform**; the template ships **empty**; the adapter slot is
optional. Storage is deliberately the **weakest link** (Pareto); **handling** is the strong part — a
credential is **never in context, never in logs**. (The SOP: the plugin's
`canon/connecting-an-outside-service-sop.md`.)

#### The intention

**Dedicated energy goes to auditing and air-gapping — without compromising
functionality to uselessness.** The security work follows the doors, and it is standing work, never a
finished state.

### View 3 — The Seams: the boundary toolkit

All of it is one idea — **architecture at the seams** — stated seven ways:

1. **Guardrails** — deterministic checks wrapped around stochastic output (the settled industry term; the
   hooks predate its fashion). Layered lightest-first, the same friction levels as the action plane: sign,
   speed bump, reason gate, door, pop-up, hard block (LOCKED 20). **Policy friction points, fail-closed** —
   a checker that can't verify rejects — except the fail-open paths named in `canon/security-canon.md`'s hook table, which
   are stated as accepted.
2. **Typed boundaries / structured outputs** — the model may only respond through a schema-checked
   interface. The existing seam doctrine — *code hands the model a bounded set of outcomes, including
   NO-OUTCOME, and checks membership on every path* — is this pattern, stated better than most papers.
3. **Single-writer validation, envelope-on-write** — every tile write passes one door (`emit_status.py`, the
   fixed set of envelope keys — the contract per Step 0); accept with an atomic save (temp file + rename) or
   reject naming the exact failed field.
4. **Provenance and attestation** — the confidence ladder: trust derived from labels and lineage, never from
   the text's mere existence (canonical principles SOP §7.0). A line is canon by its location: canon and the
   designated locations (COMPASS, this Vision). Everywhere else starts from a default of doubt; confidence
   accumulates as points; load-bearing decisions need a human sign-off.
5. **Event-sourced, dated knowledge — the state taxonomy (LOCKED 16).** The **diary is the append-only event
   log** (derived, never stale); **tiles are a materialized snapshot cache** (stored, cheap,
   credibility-windowed); the **working state (briefs and tiles) is stored and maintained, with staleness
   made visible**. The working state comes in two materials per the format doctrine: **prose (the briefs — the
   reader is a session, never JSON)** and **structured (the tiles — the reader is a program)**. The brief is
   the prose twin of the tile. Nothing prohibited; everything named with its cost.
6. **The speaking cascade (LOCKED 17).** The shell watches itself by speaking, under one doctrine:
   **a receipt is produced by the checker, never the checked.** **Every checker emits a
   dated, caused receipt** (its own status tile, producer identity per the single writer), so silence is a
   signal; **session-start verifies receipt freshness on window open** — the independent trigger, running on
   the person's arrival, outside every cron's failure domain; **the weekly human-validated roll-up is the
   terminal deadman** — and the person in that role is a smoke detector, never a shift: the system creates
   its conformance and reliability without the human always kicking the jukebox, and the person is
   last-resort visibility — the one thing whose health is not the system's problem. The completion rule,
   forever: **done = wired + seen refusing once** — a checker with
   zero recorded refusals is flagged suspect.
7. **The credibility window (LOCKED 15).** A claim about the present carries a **credibility window**:
   `stale_after_s` is the producer's intended rhythm; the reader derives staleness from last-verified versus
   rhythm; past the window the claim reads **STALE, never deleted**. All other knowledge just needs its date
   **visible** — the diary has it structurally (the date tree), canon gets it from front matter (visibility
   of age, not expiry), records claim nothing.

Plus the knowledge-organization principle that runs underneath everything: **every piece of knowledge has a place,
a date, and a trust level** (the altitude ladder; the diary tree; the confidence ladder) — and the machinery
makes all three visible without asking the model to guess.

#### The pie doctrine (LOCKED 19)

The system's knowledge is a **pantry** — the durable fact-files: prose, front-mattered. Every session **bakes
a fresh pie** — its context window — from current ingredients, and **the pie is never stored**: nothing baked
can go stale; only ingredients can. Updating a file is **replacing a stale ingredient** — the next pie uses
the fresh one automatically. A **broken pointer is a missing ingredient, not a stale one**. A **label is an
address** — the retrieval key for both cook and sous-chef. And the **sous-chef rule**: for more than a hop or
two, **code fetches and the model rides** — sequence-and-repetition is code's quadrant, and the
lazy-LLM-following-ten-pointers failure is measured system history. Four roles: **pantry** (fact-files) ·
**recipe/manifest** (the document: which jars, what order, why) · **sous-chef** (code: the loader hook for
the standing pie; the read-canon subagent for on-demand pulls — code drives the route, the model does the
fuzzy matching) · **cook** (the LLM: thinks, and fetches directly only for short hops).

*Why a doctrine and not a habit:* sessions that store their own conclusions bake stale pies on purpose —
the doctrine makes "never store the pie" a ruling with a reason, so a future session doesn't rediscover it
the expensive way.

#### Canonical delivery (revised 2026-11-10)

The factory (deterministic code assembling canonical documents from ingredients, ruled 2026-11-08) is
retired. Its replacement is coherence-by-inspection: each topic is one whole, readable document — no
fragmentation into ingredients — and the documents are the truth; the registry is an index, never a store; git is the archive. *Intention:* splitting
needs a map plus assembly code to give students a whole file — the factory's machinery — and the project's own
evidence (true-up phase 2, 2026-11-04) showed one strong reader of whole originals beating every added layer.
*Change condition:* the corpus outgrows what one reader can hold. *(Canonical-system rulings 1–5 and 18–19;
the factory's text is archived word for word. Intention and
change condition moved 2026-11-10 from the canonical-system rulings record, item 18.)*

#### The format-trust doctrine in the knowledge folders (LOCKED 12, 13)

Canonical principles §7.0b carries the doctrine: **prose is where meaning lives; structure is where trust
lives; format never serves the LLM, it serves the machine that needs handles** (addressability). Applied to
the folders: **canon gets front matter** — dates, trust, topic per entry (his classification wish), every new
addition freshly timestamped, anything removed archived *with its date and the reason it was taken out*. **Records are prose-only** — no program reaches in. The format-doctrine link in View 1 is
the same doctrine seen from the seam side.

#### The glasses pyramid (rulings 2026-11-05 or 11-06, restated 2026-11-09; text approved 2026-11-10)

The always-loaded context files (`CLAUDE.md` at each layer) are **glasses, not law**: they correct two biases —
trusting old text over new evidence, and trusting confident text over validated text — rather than commanding
anyone. They stack as a pyramid that widens downward: **the plugin's layer is thinnest** — the lenses every
student looks through, always true for every student, lean on purpose; **the personal layer is wider** — that
one student's instructions and customizations added on top; **the desk layer is wider still**. A session
launched from a desk loads all three side by side — the plugin's, the person's own, and that desk's — and the
desks are mix-and-match: which ones exist changes over time, at the human's choice. All three stacked are
watched for weight: not a hard cap, but a standing way of noticing when the stack is getting overweight —
because the glasses only work while a session will actually read them. How the watching works is SOP and
machinery, not charter.

---

## Decisions

This Vision is the charter; the decisions live elsewhere, as case records. In the industry this discipline is
called **Architecture Decision Records** (ADRs): one decision per record — context, decision, status,
consequences — never edited, only superseded.

**No precedence rule (revised 2026-11-10).** Where this Vision and an SOP disagree, neither wins: the tension
is kept alive and surfaced to Enver (No outranking, in Read This First). Never a silent pick of winners.

- **Rulings files:** one canon-files run's scratch pad; what they hold is persisted into the plan, brief, Vision,
  COMPASS, SOPs or the debt ledger, then the file is archived (`docs/v2/archive/`). Residency, by who owns the document: shipped canon — canonical principles, SOPs, map / manual /
  elements — stays in the harness repo (`LifehackMethod/lifehack-brain`, V2), already in git; the operator's
  own document — COMPASS — lives in the private ClaudeOps repo, and this Vision lives in V2 canon; Drive may
  keep a backup copy; a student needs no repo of their own, and one with a GitHub account may open PRs and
  issues. The person's data
  folders: the brain folder is local first, and Drive backs it up; a fourth, unsynced local folder holds live
  databases and sensitive raw content, since syncing a live database can corrupt it. *Intention:* SAFETY,
  not savings — real version history, one-step undo, and every change visible as a before/after, so nothing is
  changed behind the operator's back. Whether the Vision ever ships stays Enver's call. *(Moved 2026-11-10
  from the canonical-system rulings record, item 19.)* COMPASS (`canon/COMPASS.md`, same repo) is the
  seedling they grew from and retires once its
  content is persisted into the lower-altitude documents. The vetting notes (`records/2026-11-07-vetting-notes-all-23-items.md`, LOCKED 1–21) and This document's rulings file was a scratch pad; its decisions now live in the places named above.
- **One register for his rulings (LOCKED 19, B5; revised 2026-11-10).** The sandbox's principles SOP points at
  the rulings records rather than claiming to hold them. A flat index maps ruling number → location, so a
  sous-chef lookup is instant and the 120-second Drive grep never gates a citation. *Why:* two registers of
  record means two versions of the truth; one register plus one index means one truth with fast addressing.
- **Where the rulings not carried in full here live:** LOCKED 2's mechanism (diary provenance) →
  Marc's lane, principle carried in The Client. LOCKED 9 (the write door) → carried in the security
  view's action plane. LOCKED 18's group-A edits: A1 (proves → demonstrates) applied throughout this
  document; A4 (the `_system-health.json` materialized-view label) and A5 (the tile reaper) → the companion
  SOP (`status-emission-sop-draft.md`) and the map, not this document.
- **The flywheel:** when a decision happens, it goes to the plan or the brief, in his words. When a meaning changes, this Vision gets
  edited. Never both, never neither.

---

## The Ubiquitous Language

One shared vocabulary where each term has one agreed meaning — for the person, every session, and every
builder. Definitions are deliberately incomplete: each entry carries the term, its intent, and pointers to
the rulings that have applied it; full meaning accretes in the applications.

- **Platform** — the shared code layer: the car platform, the factory (the plugin, `~/lifehack-v2`). One
  implementation of each capability. *(Applied by: LOCKED 1.)*
- **Tenant** — the business logic layer: the person's configuration and domain logic. The car model, its car
  trim and options, and the driver's logbook. *(LOCKED 1; the dependency rule.)*
- **Car platform** (platform layer: the plugin) — the first of the four car layers: the chassis and
  drivetrain every car is built on, the plugin's own skills included. *(Q24, 2026-11-12.)*
- **Car model** (personal code layer: the personal code folder) — the second car layer, inside the tenant.
  *(Q24, 2026-11-12.)*
- **Car trim and options** (configuration layer: desks, personal skills, settings) — the third car layer, inside the
  tenant. *(Q24, 2026-11-12.)*
- **Driver's logbook** (knowledge layer: the brain folder) — the fourth car layer, inside the tenant.
  *(Q24, 2026-11-12.)*
- **Lifehack Harness** — the plugin: the car platform (platform layer). *(Q18, 2026-11-12.)*
- **Personal code** — the person's own code folder: the car model (personal code layer). *(Q18, 2026-11-12.)*
- **Brain folder** — the person's own knowledge folder: the driver's logbook (knowledge layer). Its root is
  itself a desk, shaped as close to a desk as possible (Enver's: `claudeops-brain`, the ClaudeOps desk).
  *(Q1 and Q18, 2026-11-12.)*
- **Client** — whoever's product displays the data. Genuinely somebody else's; the platform serves it, never
  owns it. *(The rendering-delegated correction, 2026-11-06.)*
- **Installation** — one car: a single-tenant instance of the platform, one per owner. The car is all four
  layers together, so one owner's whole setup is one car. *(LOCKED 1.)*
- **Desk** — part of the car trim and options; a person may run several desks on one car. *(Rulings round 4.)*
- **Starter template / functional default** — a working first step the system ships (e.g. `/dashboard`),
  customizable in the tenant layer; a default never precludes building your own. *(Round 11, item 3.)*
- **Recall** — a plugin update fixing a factory defect, offered to every installer at once, with proof that it
  arrived. *(Round 4; reworded round five, 2026-11-16: auto-update is off, so an update arrives only when pulled.)*
- **Seam** — a typed, validated, guarded boundary between the stochastic and deterministic worlds. *(SEAM-RULE-v1.)*
- **Sentinel** — the whole security system, one component: the inbound gate (the full multi-stage check pipeline
  every entering content item must pass), the outbound wall, the write door and the security-audit helper. "Sentinel"
  is never used for one function alone. *(Rounds 2–4; LOCKED 21's airport ruling; widened by Enver's ruling of 2026-11-16,
  "yes to 1 and 2".)*
- **Sentinel Auditor** — the read-only static-posture audit agent *within* Sentinel (credentials, secrets;
  not runtime behavior). Older documents may call it Sentinel. *(Round 4.)*
- **Ingest plane** — content entering the system: Sentinel's inbound gate. **Action plane** — actions leaving the
  model's hands: the write door (part of Sentinel) and the friction levels (sign, speed bump, reason gate, door, pop-up, hard
  block). *(LOCKED 5, LOCKED 20.)*
- **The write door** — all writes through one validated path; queries free and inert. *(LOCKED 9.)*
- **Headless data contract** — the interface we serve: the pen's envelope assertion, single writer, honest
  labels. Rendering is the client's business. *(LOCKED 11.)*
- **Envelope assertion** — the fixed set of envelope keys checked on every write; the exact count and list
  live in the code. *(LOCKED 11, LOCKED 18 A3.)*
- **Diary** — the append-only, dated event log. **Tiles** — materialized snapshot caches, producer-named.
  **Working state** — briefs and tiles, stored, staleness visible. *(LOCKED 16.)*
- **Diary roll-up** — a summary of the diary at any resolution (week, month, quarter, year), assembled on demand
  Earlier called a "throughline". *(His ruling, 2026-11-16.)*
- **Throughline** — the `/throughline` skill only: a four-beat read of a plot's tension. *(His ruling, 2026-11-16.)*
- **Pantry / pie** — the knowledge doctrine: fact-files are the pantry; every session bakes a fresh pie
  (context window) and the pie is never stored. *(LOCKED 19.)*
- **Knowledge domain** — a body of a person's knowledge that gets its own folder because loading it together with its neighbours would be too large for one conversation (then nest: more shelves beneath) or too mixed (then separate: siblings, each irrelevant to the other's questions). A desk is a knowledge domain of a person's life. How a folder states what it is for: the parent intent doctrine, `system/intent-doctrine.md` in the harness. *(the split test, 2026-08-05; his ruling 2026-11-16, U1, round five.)*
- **Credibility window** — a present-tense claim's trust horizon: `stale_after_s` rhythm, reader-derived
  staleness, STALE-never-deleted. *(LOCKED 15.)*
- **Unproven** — the word a status label reads when the receipt behind it is STALE, past its credibility window:
  STALE names the claim, unproven names the label resting on it; for a check of committed code, also when a file it
  covers has changed on origin since the check ran (status-health-proof SOP). *(His ruling, 2026-11-16.)*
- **Component** — one part of what ships as the standard Lifehack harness and is central to it, at the third C4 zoom
  level (context = the map, containers = the manual); gray cases (shipped, not central) are Enver's call. Replaces
  "element" for new pages. *(Round five C4 ruling, 2026-11-16.)*
- **Component page** — a component's reference page: intent (a pointer up to canon), as-built (generated from origin),
  status (stamped from a check's receipt), read side by side for the delta. Not an SOP. *(Definition approved
  2026-11-16.)*
- **As-built** — the machine-generated list of what is committed for a component, read from origin, never typed. The
  human-authored parts of a page are not as-built. *(Definition approved 2026-11-16.)*
- **Stamp** — the Status / Health / Proof block copied from checkers' receipts, dated, with a "valid until" on the
  credibility window. *(Definition approved 2026-11-16.)*
- **Delta** — the drift between intent, as-built and status, named by an AI reading in five types (MISSING, UNOWNED,
  NOT HOLDING, UNPROVEN, BROKEN POINTER). *(Definition approved 2026-11-16.)*
- **Static document** — not auto-injected: invisible to sessions unless something points at it (the manual,
  the elements). **Active document** — injected by a mechanism, code or hook (the map, thin, inside
  CLAUDE.md). *(Round 7, his definition.)*
- **Case records / ADRs** — the rulings: one decision per entry, his words verbatim, never edited, only
  superseded; COMPASS is the seedling that retires.
  *(LOCKED 19 B5, revised 2026-11-10; rounds 9–10.)*
- **Skill** — an LLM-language capability built on the scaffold; the unit of construction. *(Rulings
  2026-11-08.)*
- **Scaffold** — the skill template (`system/templates/skill-template/`) plus the per-skill spec sheet
  (`system/templates/producer-spec-template.md`): the shape every product is built on. The platform
  provides it; the tenant fills it. It standardizes
  mounting points, never prose. *(Rulings 2026-11-08, round two.)*

---

## The original problems — ours to validate, not to cite

*CANDIDATE-status annex, dated 2026-11-08. Four problems the field has not settled. These are the system's
own unfinished measurements — each is an intent with a change condition; none is external best practice,
and none may be cited as such.*

1. **The receipt-derived placement table.** We intend to establish by measurement whether the division-of-
   labor table can be generated by code from the system's own emitted receipts. *Change condition:* the
   derivation runs and its surprises are routed back into this charter.
2. **File-based TTL/freshness semantics.** We intend to establish whether per-entry timestamps plus
   read-time freshness checks (no standard file-based TTL exists) hold up in practice. *Change condition:*
   an external standard appears, or the credibility window's derived staleness proves insufficient.
3. **Signed liveness attestation.** We intend to establish whether SLSA-style attestation, adapted, can
   make a receipt's producer unforgeable. *Change condition:* the receiver-decides manifest proves
   sufficient without signatures.
4. **Sampling vs. fail-closed abstention.** We intend to establish by measurement which catches confident
   wrong-but-legal answers better — no head-to-head benchmark exists anywhere. *Change condition:* one
   appears.

---

## History — what the old frame got wrong, and what survived

- **"Three-tier" (a deployment topology: three machines) was a borrowed name** for two real ideas: the
  layered dependency rule, and the platform/tenant/client ownership model. Both survive, renamed honestly —
  with the distribution shape now named too: each installer runs a single-tenant instance (the car platform,
  not the enterprise apartment building).
- **"Presentation layer" as an owned tier did not survive** — the correction: its machinery is shared code,
  its data is business logic, and its rendering is delegated, unowned, out of scope. We own two layers and
  serve a contract to a third we don't own.
- **"State is never stored, always derived" did not survive** — replaced by the state taxonomy (LOCKED 16:
  event log, snapshot cache, working state in two materials, staleness made visible — see View 3, toolkit
  item 5). The honest version names what is stored and what it costs.
- **"CQRS" did not survive as our name** — what we built is read/write separation through a validated path;
  CQRS is a related pattern, not what we built.
- The brother's laugh survives too, taken seriously: **strong boundaries, weak interior** — the one-line
  version of "there's no architecture for stochastic environments," answered.

---

*Companion documents: the desk-building SOP, `canon/desk-building-sop.md` (the organism, the seam,
the card), and `status-emission-sop-draft.md` (the interface spec: the headless contract). All three meet in the
middle of the mountain.*

# Deck Design System — the ClaudeOps house rules for building presentations

> **Scope: HOUSE-WIDE.** Every deck built in ClaudeOps — bootcamp lessons, consulting decks, client work.
> **Read §0 before building a single slide.**

> ## ⚠ THIS FILE IS RULES ONLY. IT IS NOT THE DESIGN SYSTEM.
>
> **The authoritative design system lives with the engine, not here:**
> `_ClaudeOps/state/projects/ai-bootcamp-lesson1/deck/`
> — `design-system.md` (tokens) · `layout-grammar.md` (which layout for which job + negative rules) ·
> `decision-log.md` · `deck-workflow.md` · and the engine itself, `claudeops_deck.py`.
>
> **Those documents are generated from the real template by whoever builds against it — sampled from
> rendered pixels and verified against a working build.** This file used to carry its own token table and
> layout list; both were **wrong** (API-read colours, and a curated layout set drawn from Google Slides
> layouts that carry no decoration). **Removed 2026-08-01.** Never re-add tokens or a layout list here —
> a second copy will drift from the engine and someone will build from the stale one.
>
> **🛑 The `deck/` folder is PROTECTED.** Do not delete, overwrite or refactor
> anything in it. Iterate alongside; never in place.

---

## §0 — THE FIVE RULES. Each one is a deck that was thrown away.

**R1 — Build in PPTX, then upload to Drive. Not the Google Slides API.**
That API cannot author design: no theme call, cannot create masters or layouts, animations unexposed,
shadows read-only. And critically — **its layouts carry ONLY placeholders. All decoration lives on the demo
slides** (measured: 11–12 elements per template slide vs **0** on every layout-built slide). PowerPoint
layouts do carry it, which is why `python-pptx` → Drive upload works and this route never could.
**Five decks died here.**

**R2 — Copy the ARCHITECTURE, not the palette.**
Lifting colours and fonts onto a minimalist skeleton produces *"a minimalist cousin, not a sibling."* A
template's identity is its **graphic layer**: full-bleed photo title · oversized poster titles · icon rows ·
stat bars · photo cards · chevrons · density. **No graphic layer means the template was not copied.**

**R3 — Content files contain NO design spec.**
A spec living inside a content file **will be read and obeyed by the next session, even one explicitly told
to ignore prior attempts.** *(2026-08-01: a fresh session was told "use the script for the words, the
template for the look." It read the script, found a stale minimalist spec inside it, and built to it. It
obeyed instructions it had been told to ignore, because they sat in the file it was pointed at.)*
**Words live in the content file. Design lives in the `deck/` documents. Never mix them.**

**R4 — A sparse deck is a CHOICE, not a default.**
*"Good talk slides are minimal"* is a real principle **and** a strong model prior — and it will silently
override an explicit instruction to match a rich template. **When the user points at a template, the
template wins.** Ask before stripping.

**R5 — Check title length before the first render.**
Template headline boxes are sized for demo text like "Methodology." Ceiling ≈ **26 characters per line**;
**14 of 22 real titles overflowed** and collided with the subtitle beneath. Cap the titles or enable
auto-fit. **A copy-length problem reads as a design failure if you don't catch it early.**

**Plus:** the template's content slides carry a `MONTH 20XX` tag top-right. **Replace it** with the real
section label (`2 · High-value vs low-value zones · 11 / 22`). Never leave it; never delete it — a
non-technical audience on a video call has no other way to tell where they are.

---

## §1 — Terminology (so nobody reinvents it)

A design system has three layers. They fail separately, so they are named — and filed — separately.

| Layer | Term | Holds | Is |
|---|---|---|---|
| 1 | **Design tokens** | palette · type scale · spacing · grid | **vocabulary** |
| 2 | **Pattern library** | the slide layouts | **the words** |
| 3 | **Usage guidelines** | which layout for which job + negative rules | **grammar** |

**Tokens give vocabulary; grammar makes it a language.** A pattern library with no usage rules is a box of
parts. **The grammar is the layer that keeps getting skipped, and skipping it is what produced every failed
deck** — layouts got picked by vibe, and one deck carried seven different design languages.

Adjacent terms: a **theme** is Google's technical container · a **slide master** is PowerPoint's · a
**template** is a deck you copy · **brand guidelines** sit above all of this.

## §2 — The four documents a deck system must have

Any deck system in ClaudeOps produces these four, in its own `deck/` folder:

1. **`design-system.md`** — the tokens. Every value as a number, never a description.
2. **`layout-grammar.md`** — **the one that never exists and always matters.** Per layout: its name, its
   JOB (the content shape it serves), its text slots, and **when NOT to use it.** Then the negative rules,
   written as absolutes. Layouts ranked by expected frequency.
3. **`decision-log.md`** — locked decisions, dated, with the reason. Stops re-litigation.
4. **`deck-workflow.md`** — the build sequence from content-markdown to finished deck, including the
   verification steps and what "done" means.

## §3 — Verification (non-negotiable)

**Render every slide and LOOK at it.** LibreOffice headless works. **The file state and the API response
prove nothing** — every defect in the 2026-08-01 build was found by looking at a rendered image, none by
reading JSON.

*(Note: `Read` on a PNG in `/tmp` is blocked by `ingest_gate_enforce.sh`. Copy renders into a `_ClaudeOps/`
folder first.)*

**A useful, proven method for learning an unfamiliar template:** render all its slides to PNG, hand them to
a sonnet critic, and get back a catalogue — *shape · text slots · visual richness · best-for* — plus a
ranked top-8. That catalogue is what makes a sane slide-by-slide mapping possible.

## §4 — Change control

The five rules in §0 are **append-only** — each is a scar, and deleting one means re-learning it the
expensive way. Tokens and layouts are **not governed here at all**; they live with the engine (see the
banner at the top).

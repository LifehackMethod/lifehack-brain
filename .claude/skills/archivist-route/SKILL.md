---
skill: archivist-route
description: "Given one approved insight, ranks the right canon home (1–3, with why) — never a silent pick, and catches non-canon misfiling. Called by /save and review sessions when placement is unclear."
shape: interactive-workflow
status: active
topic: [archivist]
summary: Given an approved insight, propose the right canon home as ranked candidates (never a silent pick).
---

## Intent (§0.5)
**User outcome:** A good insight gets written to the wrong canon home — the desk's top-level current.md instead of the project canon, or into canon when it's actually a playbook recipe or a dated record. archivist-route fixes the routing step: given one approved insight, it reads the territory map and returns 1–3 ranked homes with reasoning, so the human picks with a tap rather than knowing the whole filing structure by heart. **Bar:** "the insight lands in the one right place — I don't find it three months later in the wrong home."
**Role:** the librarian/router — called by /save, /archivist-deepmine, and review sessions, never for bulk standalone decisions. It works MOST-SPECIFIC first (project canon > desk canon > root), catches non-canon misfiling (a recipe → playbook, a dated fact → record, not canon), handles cross-cutting insights with one-home-plus-pointer, and flags [INFERRED] homes. It ranks, never silently picks; it writes nothing — the caller writes.

# archivist-route

> **Content root (Drive).** Every relative `state/…`, `records/…`, `canon/…`, `desks/…` path in this
> skill is **content** — it resolves under the Drive root
> `<notes>/`, never the code
> clone. Sessions launch from the clone now, so resolve these against that absolute Drive root.


Given an approved insight, propose the RIGHT canon home — ranked candidates, never a silent pick.
This is the **librarian/router**: it fixes the `/save` failure where a good insight gets dumped into the
desk's main canon instead of the project canon where it belongs. **READ-ONLY / PROPOSE-ONLY** — it returns
home candidates; the human picks; the caller writes. (Part of `archivist-rebuild` — P2.5.)

## Who calls it
- **`/save` Step 7e** (insight harvest) — per approved insight, to propose its home.
- **`/archivist-deepmine`** synthesis — to place each promotable insight.
- A supervised review session — when working through a deep-mine queue by hand.

## Input / Output
- **In:** one insight (a one-line durable, generalizable rule) + optional context (which desk/project the work was on).
- **Out:** 1–3 RANKED home candidates, each `{home_path, level (desk|project|root), confidence, why}`, plus — if the
  insight is cross-cutting — a `pointer` note (one home + a pointer in the other). NEVER a silent single write.

## Procedure
1. **Load the map.** Read `<notes>/system/canon-purpose-map.md` (the territory index — what each canon is FOR). It's the
   cheap cached index; do NOT walk every canon live. If the map is missing/stale, fall back to reading the candidate
   desk's `<notes>/desks/{desk}/canon/purpose.md` + the relevant project `canon.md` directly, and flag the map for refresh.
2. **Identify the insight's SUBJECT** — the job/topic it serves (billing-dashboard design? coaching method? a Pulse
   mechanic? an OS-wide rule?). Subject, not surface keywords.
3. **Match MOST-SPECIFIC first** (the home ladder — the Territory Map now spans ALL homes, not just canon):
   - **Is it a how-to / recipe / gotcha rather than an always-true RULE? → a PLAYBOOK home** (e.g.
     `system/sops/build-sop.md`), NOT canon. (added P6)
   - else a PROJECT canon whose purpose covers the subject → rank it #1 (scoped homes win — that's the whole point);
   - else the DESK whose job covers it → desk canon;
   - else `<notes>/records/canon` (root) for genuinely OS-wide rules.
   Produce up to 3 ranked candidates when more than one plausibly fits (e.g. project vs its parent practice vs desk).
4. **Apply the promotion test per candidate** — "would this help a future DIFFERENT case, stated as a rule, without
   the backstory?" If it only fits ONE narrow project, that project is the home, not the desk. If it's a fact/number/
   event (not a rule), it is NOT canon — say so and route it to a record instead.
5. **Cross-cutting → one-home-+-pointer.** If the insight genuinely serves two jobs (e.g. a shared-device credential,
   a rule both desks act on), pick the ONE home whose JOB it most serves as primary, and propose a POINTER line in the
   other (`see <primary path>`). Never two copies. (Doctrine: cut by concern; seam = one home + a pointer.)
6. **Flag low-trust homes.** If the top candidate's map entry is `[INFERRED]` (no stated purpose yet — an O-backfill
   target), say so: the purpose is a guess, confirm before trusting it. (This is also a nudge to backfill that canon.)
7. **Return the ranked candidates.** Do NOT write. The caller surfaces them for the human's one-tap pick, then writes
   to the chosen home (+ pointer if shared) and densifies in place.

## Rails
- READ-ONLY / PROPOSE-ONLY. The router writes NOTHING — not canon, not the map. It proposes; the human picks; `/save`
  (or the supervised session) writes.
- **Ranked, never silent.** A silent mis-route is worse than a dumb default — always show the candidates + why.
- Map is a CACHE: the Archivist refreshes `<notes>/system/canon-purpose-map.md` on its tree-walk; this skill only reads it.
- Hard rules (auth/calendar/write-gates) are NEVER canon — never route them here.

## Reference
- The map: `<notes>/system/canon-purpose-map.md`. Plan: `<notes>/state/projects/archivist-rebuild/task_plan.md` (P2.5).
- ⛔ Why it exists: a real mis-route, measured on a real deep-mine run in 2026. The evidence is a log in the author's own notes and does not ship — the RULE it produced is the whole of it, above.
  where agents defaulted coaching-method + AI-framework insights to "desk canon" instead of `clarity-academy` /
  `ai-consulting-concepts`.

---

## Where the queue goes, and who acts on it

This skill **proposes and never executes.** Its output is a queue, and the queue lands at:

```
<notes>/records/proposals/archivist-{YYYY-MM-DD}-{what}.md
```

`records/proposals/` is one of the six record types, and it means exactly this: *something proposed,
waiting on a person to rule on it.*

⛔ **There is no `/archivist-review`.** The system this came from had one, and retired it on
2026-07-11 as a dead approve-then-file model — its own scheduled runner records the replacement in
one line: **the scanner just FLAGS, and the next `/save` picks it up.** So nothing here waits for a
review command that does not exist. Write the queue, say where it is, and stop. When you next run
`/save`, the open proposals are there to be dealt with.

## What this skill needs OUTSIDE its own folder

| what | where | status |
|---|---|---|
| the build doctrine it cites | `system/sops/build-sop.md` | shipped |

Everything else it touches is in your notes, not in this repo.

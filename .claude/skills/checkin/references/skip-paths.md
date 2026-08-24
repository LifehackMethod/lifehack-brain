# Skip paths — the whole list

> Moved out of SKILL.md 2026-08-23. Each skippable step declares its own
> skip condition where it lives. **Reading this is not a substitute for running the phase.**

⚖ **The operator, verbatim: *"it is non-optional — to skip anything you would need human-in-the-loop
approval."*** This skill went from "do this" to "do this UNLESS" as four legitimate mechanisms landed
one at a time — the `new-session` token, `--ns checkin`, the reader's move to Step 3.58, and Step 1.8's
two gates — and *unless* is the escape hatch a session can hide a silent skip inside. **The fix is not a
hook** (ruled out, `authority: user`) — it is making every escape hatch small, counted, and loud.

**Exactly three steps can be skipped. `MANDATORY_CHECKIN` in `save_step_ledger.py` tracks only these
three, on purpose — its own comment rules out growing that list.** A step that skips without stamping
`NOT_OWED` renders `✗ MISSED` on the coverage table and exits non-zero; a step that skips *with* the
stamp renders `⊘ ... (NOT_OWED — not required this run)`. **The two can never look the same** — proven
mechanically: `save_step_ledger.py --selftest` cases [12]/[13] show an unstamped `reader` rendering
`missed=['reader']`, and case [14] shows an all-`NOT_OWED` run rendering clean.

| step | lives at | skips when | what it announces |
|---|---|---|---|
| `compact` | Step 1.8, GATE 1 | `pad_archive.py state` returns `PAD-EMPTY` (nothing to compact), `PAD-ARCHIVED-UNCLEARED` (clear without re-archiving), or `CANNOT-READ` (unevaluated) | one line naming which gate failed, then `stamp compact --ns checkin --verdict NOT_OWED` |
| `compact` | Step 1.8, GATE 2 | the pad-hash check returns `GATE2-NO-WRITE` (this window never touched the pad) or `GATE2-NO-BASELINE` (fingerprint missing — self-heals next arm) | same stamp, same one-line reason |
| `graduate` | Step 3.55, Verb B | PICKUP mode only (`new-session` token present) — a blind window cannot judge settled vs. dead vs. open | `stamp graduate --ns checkin --verdict NOT_OWED` |
| `reader` | Step 3.58 | (a) no edits landed this run, or (b) PICKUP mode (`new-session` token) | states which of (a)/(b) applied, then `stamp reader --ns checkin --verdict NOT_OWED` |

**Everything else that reads like a skip is not one — checked, and none belong in the table above:**

- **Step 1.6b (no linked plan)** *used to* skip wholesale; that was the hole. It now **resolves** — lists
  candidates, checks for forks, offers to link one — so there is no silent no-op left here to announce.
- **Step 1's story-log depth** narrows mid-session (open items + last few) rather than skipping the log.
  The orientation receipt names precisely what was read — *"open forks + last 3"* — never a bare
  `SKIPPED`, so a narrowed read can never be mistaken for an unread log.
- **Step 3.5 (plan amendments)** and **Step 3.55 (content deltas)** always run their drafting logic; they
  may legitimately produce nothing to propose, which the panel/receipt states in one line (*"plan
  current, no changes"* / *"current state and success criteria current, no proposed deltas"*). There is
  no on/off switch here for a step to silently not-run — only an always-run pass that can find nothing.
- **Step 2 / 2.5 / 3** (reconcile, mine the session, orient) and **Step 3.57** (the one approval round)
  run unconditionally, every time, in full.
- **Arming's exit-3 refusal (a project switch)** is not a mid-run skip — it stops the run before step 0
  finishes, reports itself, and is the correct behavior, not an escape hatch.

**Why only three rows and not more.** `save_step_ledger.py` states the rule directly: *"DO NOT GROW IT
into a mirror of the /save spine. Every row here must be a step whose absence is a real failure; a long
table trains the reader to skim it, which is the disease, not the cure."* Three is the count this file
states and justifies — one per genuinely load-bearing gate, nothing decorative.


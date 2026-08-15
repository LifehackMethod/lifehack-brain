# The session is what's running. Code is a guest it may or may not pick up.

> **This is an extract, and it says so.** It comes from a roughly 1,200-line manual describing a
> particular running system, with 49 companion files. ~~None of that ships here.~~ **Two skills cite it for
> one idea**, and the idea is below.
>
> Source: `system/organism/manual.md` → *THE CODE/LLM SEAM*. ~~**That file is not shipped**~~ — it and its
> 49 element files describe the author's own running system. This page is the whole of what crossed.
>
> ⚠ **CORRECTED 2026-08-15 — BOTH STRUCK CLAIMS ABOVE ARE NOW FALSE.** They were true when this page
> was written (pre-Phase-9), and they are the reason this extract exists at all. Phase 9 shipped the
> source: `system/organism/manual.md` is here, 1206 lines, alongside `system/organism/map-format-specs.md`
> and 42 files under `system/organism/elements/` (verified this date by listing the directory — 42, not
> the 49 the sentence above still claims). **So this page is no longer "the whole of what crossed."**
> ⭐ **Read the manual itself for anything load-bearing; this extract is now a pointer, not a substitute.**
> The one thing that has NOT changed is the caveat below: the idea here was provisional in the source
> and stays provisional here.
>
> ⚠ **Provisional, and it was provisional there too.** It is best current thinking, not doctrine, and
> it sits in open tension with the rule that code owns the perimeter and the model works inside it.
> **Both are live.** ⛔ **Do not gate anything on this.** It exists to be argued with.

---

## The idea

**You will assume the code in a system like this *is* the system. It isn't.** The running session is
the interpreter; the code is a set of things it may or may not pick up.

That has one consequence worth carrying into every build:

> **When a failure appears, *"how do we DETECT this?"* is almost always the WRONG FIRST QUESTION.**

The model is rarely bad at *detecting*. It is bad at **remembering to look**. Detection code answers a
delivery problem — and that code then needs its own enforcement, and that second layer is the spiral.

## So, before you build anything: what kind of thing is this?

1. **Irreversible?** → it must be code.
2. **Has to fire without being remembered?** → it must be a hook.
3. **Neither?** → **it is a FACT the session needs to SEE**, not a tool it must remember to run. Put it
   where the session already looks.

⭐ **Branch 3 is the one that says build nothing. Take it seriously.**

## And if you are building — the four questions

1. **What will call this?** A hook (fires on a specific action) · an injector (fires every turn) · the
   model remembers. **If it is the third, you have a suggestion, not a control.**
2. **What artifact will prove it ran?** Name the file, hash, receipt or record that only real execution
   could produce. Without one, *"it worked"* is a claim, not a fact.
3. **Is there a soft word in it?** *meaningful · stale · real · right · proper · significant.* If you
   must define the word before you can write the check, **that definition IS the judgment** — and
   judgment is the model's half. Code gets **membership**, **artifacts** and **timing**. Nothing else.
4. **If this broke silently, how would you find out?** No answer means you moved the failure somewhere
   invisible. You did not remove it.

## The rule that falls out of all of it

> ⛔ **If your fix has three parts and one of them checks the other two — delete that one.**

The exception: a part that checks **its own** output before finishing is one part. The forbidden third
is a **separate** thing watching the first two.

**Two ways this gets faked, both by accident:**

- **Your proof must be made by the work, not by a wrapper around it.** `if it_ran: write_proof()` proves
  only that your wrapper ran.
- **"It fires automatically" is not enough — it must fire in NORMAL OPERATION.** A hook on a
  once-a-year event technically fires and protects nothing.

## The worked example that makes it concrete

**One day, one problem, solved twice.** A required step kept getting skipped. The session built a
namespaced ledger, a coverage table, applicability markers and a timestamp check — **111 lines.** An
independent auditor broke it five ways in six minutes, and **every break was in the part that guessed.**

What actually worked: **one line printed into a message that already fires every turn.**

**111 lines versus 1.**

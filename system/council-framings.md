---
topic: [system-architecture]
title: "Council Framings — the two stances a dispatch can carry"
record_type: reference
status: active
created_at: 2026-08-06
updated_at: 2026-08-11
---

# Council Framings

> **⛔ ONE FILE, BOTH MODES. Do not copy either framing into a skill, a roster, or a dispatch
> template.** Two copies of one decision drift. Every mode that needs a framing reads it from HERE,
> verbatim.
>
> **WHERE THIS SITS:** in the repo, at engine level — not inside a roster, and not under your notes.
> A roster is yours and changes; this is part of how the engine talks to an advisor, and it has to
> exist on the day you install, because every skill that dispatches an advisor refuses to retype it.
> ✅ `/advisory-council` is here now and reads this file.
> ⏳ `/architect` is the second such caller and lands later in phase 3.
>
> **WHAT A FRAMING IS.** It is the sentence that tells an advisor **what kind of thing they are being
> handed** — a draft to improve, or a claim to defeat. It is not context and it is not a position; it
> sets the GRAVITY of the reference material the dispatch already carries. Same document, different
> framing, produces materially different advice.

---

## THE TEXT — pasted verbatim, never reworded

### GENERAL — the default for any advisory-council dispatch

> **This is our best thinking, based on a large amount of research. It is NOT prescriptive.
> Suggestions are welcome.**

### ARCHITECT — for the case where a professional's judgment is the deliverable

⏳ Its caller, `/architect`, lands later in phase 3. Until then this block is here and unused, which
is the correct state: the text is the ruling, and the skill is only one way of delivering it.

> **This is our best thinking — and it is the best thinking of a NOVICE. We are asking for the best
> thinking of a professional systems architect. If a high-level architect were building something THIS
> SIZE, what would they do, and how would they use their experience — while still building something as
> elegant and minimal as what is here?**

---

## HOW TO USE THEM

**Pick exactly one per dispatch, and paste it verbatim** alongside the reference material the roster
already pastes inline. A dispatch carrying neither framing defaults to GENERAL — but say so in the
dispatch rather than leaving it implicit, because an advisor cannot tell an omitted framing from a
deliberate one.

**★ THE CLOSING CLAUSE OF THE ARCHITECT FRAMING IS LOAD-BEARING.** *"…while still building something as
elegant and minimal as what is here"* is the whole reason ARCHITECT is safe to use. Without it,
*"professional systems architect"* reliably reads as *"enterprise"*, and the room returns correct advice
at ten times the scale of the thing you actually have — the exact failure a right-sizing brief exists to
prevent. **Never trim that clause for brevity.**

**⭐ WHY ARCHITECT IS A REFRAME AND NOT A PERMISSION SLIP.** The obvious alternative — telling advisors
they *may* challenge the reference material if they cite a reason — was considered and **rejected**. A
permission clause leaves the reference material sitting as a ceiling and asks advisors to climb over it;
the novice framing converts the same document into a **floor** in one sentence. That is what
`system/sops/skill-building-sop-extract.md` demands of any seed — frame it as a claim to DEFEAT, not a
draft to polish — and it matters because anchoring runs **22–61%**, and simply making a model aware of
an anchor does not remove it.

**⛔ A FRAMING IS NOT BLINDNESS.** Both framings assume the advisor **can see the system**. Blinding
advisors was proposed and overruled on 2026-08-06, in the words of the person it kept failing: *"one of
the big problems I've had with the advisory council is that because they don't know the shape of what
I've built, they start suggesting fixes that are not right-sized."* The reader/actor split survives
**only** for a web-fetch step, which is untrusted-content handling, not blindness.

## If you want to change a framing

Edit this file. It is yours now. The rule is not that the words are sacred — it is that there is
**one copy** of them, so that changing your mind changes every dispatch at once.

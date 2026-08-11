#!/usr/bin/env python3
"""board_check — is the brief's ❓ OPEN board still a list of OPEN things?

WHY THIS EXISTS (2026-08-07, from a real bad handoff).
`gauge_check.py` made ONE surface answer "where are we." Nothing made one surface
answer "what do I do next" — and that is the question a session actually acts on.

Measured: a brief's three altitude rungs were rewritten correctly and verified
(`RUNGS 3`, `ONE-GAUGE`), and the very next session still did the wrong work,
because the `❓ OPEN` board underneath queued `15.3` — a task the plan had already
marked ✅ DONE. Every content check in `/checkin` pointed at the rungs; nothing
read the board. The operator had cleaned the one surface the skill inspects.

⭐ THE RULE THIS ENFORCES, and it is the same fix applied to a second axis:
    the GROUND RUNG is the one place that says what is next.
    `❓ OPEN` holds open QUESTIONS. Tasks live in the PLAN.
    An `❓ OPEN` item the plan marks ✅ DONE is a SECOND, STALE direction surface.

⭐ SECOND PASS (added same day, `17.2`, from a SECOND real failure): the ground
rung itself pointed at work the plan never held — the plan had no matching task
id — and a session running `/build from the plan` found nothing to execute and
improvised. `RUNG-ORPHANED` is the mirror of `STALE-OPEN`: the board check asks
"is the OPEN bucket lying about what's still open"; the rung check asks "is the
GROUND RUNG lying about what to do next." ⭐ A rung is also allowed to say,
explicitly, that nothing is planned (e.g. "no task planned — run `/autoplan`") —
that reads as `BOARD-CLEAN`, never `RUNG-ORPHANED`, because refusing an honest
"nothing queued" would train the operator to keep inventing a fake id just to
pass the check.

⛔ WHY A TOOL AND NOT A PARAGRAPH. The nine competing `WHERE WE ARE` blocks were
told not to accumulate, in prose, for weeks. They accumulated. `gauge_check` is
what actually stopped it. `skill-building-sop.md` LAW 4.2: a model cannot report
on its own compliance — so this verdict comes from an exit code, never a reading.

THE CLOSED OUTCOME SET (code→model seam; the model never invents a member):
    BOARD-CLEAN    rc 0  every ❓ OPEN item is genuinely still open, AND the
                         ground rung's named task (if any) exists in the plan
    STALE-OPEN     rc 2  ≥1 ❓ OPEN item is marked DONE in the plan — NAMED
    RUNG-ORPHANED  rc 2  the ▲ ground rung names a task id the plan does not
                         hold — OR names real work with no citable id and no
                         explicit "nothing is planned" escape (see above)
    NO-BOARD       rc 3  no ❓ OPEN board AND/OR no ▲ ground rung found — a fact,
                         not a pass (both are structural absences, same token)
    CANNOT-READ    rc 4  THE NO-OUTCOME MEMBER — unreadable, absent, malformed

⛔ CANNOT-READ IS NEVER CLEAN. The briefs sit on a Drive FUSE mount that has
already produced a live false green (`health-deadman`, 2026-08-04: a readability
probe passed while the real read failed with EDEADLK). Report it unevaluated.

DELIBERATELY NOT DONE — the honest bound, so nobody mistakes this for more than
it is: this checks whether an open item is CLOSED, and whether the ground rung's
task exists in the plan. It cannot tell whether an open item (or the rung's task)
still BELONGS to this project. A handoff moves ownership, and ownership is
recorded nowhere in the system today. That gap is real and is NOT closed here.
"""
import argparse
import os
import re
import sys

# A plan task id as this system writes them: 15.3 · 15.B · P3 · W3 · 14.4a · X2 · S8.12
TASK_ID = re.compile(r'`([A-Z]{0,2}\d{1,2}(?:\.\d{1,2}[a-z]?)?|[A-Z]\d{1,2})`')

# How far into a bullet an id still counts as QUEUED rather than CITED. A queue item
# leads with its id ("- **`15.3` → `15.B`** — the run"); prose that cites a finished
# task does so mid-sentence. Deliberately generous: a false NEGATIVE here costs a
# missed stale item, which the human still sees on the board — a false POSITIVE
# trains the operator to ignore the tool, which is the worse failure.
LEAD_CHARS = 40

# The ❓ OPEN bucket, however it is punctuated. Ends at the next bold bucket or H2.
OPEN_HDR = re.compile(r'^\s*[*_>\s]*❓\s*\**\s*OPEN\b', re.I)
BUCKET_END = re.compile(r'^\s*[*_>\s]*(?:✅|⛔|📋)|^##\s', re.U)

# The ▲ ground rung's headline, however it is punctuated (mirrors OPEN_HDR).
GROUND_HDR = re.compile(r'^\s*[*_>\s]*▲\s*ground\b', re.I)

# The rung's LEGAL way to say "nothing is planned" (⭐ Feature 17.A) — a rung
# reading this must resolve BOARD-CLEAN, never RUNG-ORPHANED.
NO_TASK_PLANNED = re.compile(r'no\s+task\s+planned', re.I)

# "the plan says this is finished" — every shape a plan in the wild actually uses.
#
# ⚖ WIDENED 2026-08-11 (migration T1.10). The list below used to hold only the four shapes ONE
# person's plans happened to use — all of them built on a ✅ emoji. **A plan written with an
# ordinary markdown checkbox — `- [x] \`2.1\` write the joiner`, which is the commonest convention
# there is — read as NOT DONE**, so a board still queuing that task came back BOARD-CLEAN.
# That is a false clean in the one tool whose entire job is catching a false clean: it exists
# because a session did the wrong work off a stale queue while every surface reported fine.
# The emoji shapes stay; the checkbox joins them.
def _done_patterns(tid):
    t = re.escape(tid)
    return [
        re.compile(r'^##\s*✅\s*`?' + t + r'`?\b', re.M),          # ## ✅ `15.3` — ...
        re.compile(r'^#\s*✅\s*PHASE\s*' + t + r'\b', re.M),        # # ✅ PHASE 16 ...
        re.compile(r'`' + t + r'`[^\n]{0,80}?—\s*\*\*DONE', re.M),  # `15.3` — **DONE
        re.compile(r'\*\*✅\s*`?' + t + r'`?\b', re.M),             # - **✅ `16.1a` ...
        re.compile(r'^-\s*\*\*✅\s*`?' + t, re.M),
        # - [x] `2.1` …   and   * [X] 2.1 …   — the ordinary markdown checkbox. The id must sit in
        # the bullet's LEAD, same window the queue side uses, so an id mentioned mid-sentence in a
        # ticked bullet is discussion rather than a claim about that id.
        re.compile(r'(?m)^[-*]\s*\[[xX]\]\s*`?' + t + r'`?\b'),
        # `2.1` — DONE / done: / ✔ — the plain-word forms, id first.
        re.compile(r'(?m)^[-*#\s]*`?' + t + r'`?\s*[—:-]\s*(?:✔|DONE|done)\b'),
    ]


def read(path, what):
    if not os.path.exists(path):
        print(f"CANNOT-READ\n  {what} does not exist: {path}")
        sys.exit(4)
    try:
        with open(path, encoding="utf-8") as fh:
            t = fh.read()
    except Exception as e:                                    # FUSE EDEADLK lands here
        print(f"CANNOT-READ\n  {what} unreadable ({e.__class__.__name__}: {e}): {path}")
        sys.exit(4)
    if not t.strip():
        print(f"CANNOT-READ\n  {what} is empty: {path}")
        sys.exit(4)
    return t


def open_items(brief):
    """Return [(line_no, text)] for every bullet inside the ❓ OPEN bucket."""
    lines = brief.split("\n")
    start = None
    for i, l in enumerate(lines):
        if OPEN_HDR.match(l):
            start = i
            break
    if start is None:
        return None
    out = []
    for i in range(start + 1, len(lines)):
        l = lines[i]
        if BUCKET_END.match(l) and not OPEN_HDR.match(l):
            break
        if l.strip().startswith(("-", "*")):
            out.append((i + 1, l))
    return out


def ground_rung_block(brief):
    """Return (headline, full_block_text, line_no) for the ▲ ground rung, or
    (None, None, None) if no such rung exists. Ends at the next bold bucket,
    H2, or the next ▲ rung marker — same boundary shape as open_items()."""
    lines = brief.split("\n")
    start = None
    for i, l in enumerate(lines):
        if GROUND_HDR.match(l):
            start = i
            break
    if start is None:
        return None, None, None
    end = len(lines)
    for i in range(start + 1, len(lines)):
        l = lines[i]
        if BUCKET_END.match(l) or re.match(r'^\s*[*_>\s]*▲', l):
            end = i
            break
    return lines[start], "\n".join(lines[start:end]), start + 1


def rung_task(brief, plan):
    """Second pass: does the ▲ ground rung's named task id exist in the plan?

    Returns (status, tid, line_no) where status is one of:
      "MISSING"  — no ▲ ground rung found at all (folded into NO-BOARD by main)
      "CLEAN"    — either the rung explicitly says nothing is planned, or its
                   named task id exists in the plan
      "ORPHANED" — the rung names a task id the plan does not hold, or names
                   real work with no citable id and no "nothing planned" escape

    ⭐ REUSES the existing TASK_ID regex and _done_patterns() — mints no second
    matcher. Existence in the plan = the id appears anywhere in TASK_ID's own
    backtick shape (TASK_ID.findall(plan)) OR matches a _done_patterns() shape
    (covers the one done-marker style, `# ✅ PHASE <n>`, that isn't backtick-
    wrapped and so TASK_ID alone would miss).
    """
    headline, block, line_no = ground_rung_block(brief)
    if headline is None:
        return "MISSING", None, None

    if NO_TASK_PLANNED.search(block):
        return "CLEAN", None, line_no

    # ⛔⛔ DO NOT APPLY open_items()'s LEAD_CHARS WINDOW HERE. It was tried on
    # 2026-08-07 and produced a live FALSE POSITIVE within minutes.
    #
    # LEAD_CHARS exists for a BOARD BULLET, and its justification is specific:
    # a queue entry LEADS with its id, so an id cited mid-sentence is
    # DISCUSSION, not a queue entry. ⭐ THAT JUSTIFICATION DOES NOT TRANSFER TO
    # THE RUNG. The rung is ONE PROSE SENTENCE naming the next action, and its
    # task id naturally sits mid-sentence.
    #
    # MEASURED: the live brief's rung — "**▲ ground — PHASE 17. Start with
    # `17.2` ..." — put `17.2` at char 35, clearing a 40-char window by ONE
    # CHARACTER. A single extra word ahead of it flipped a correct rung to
    # RUNG-ORPHANED, with the reason "cites no task id" — a verdict that was
    # wrong AND a reason key that lied, the same class as the two exit-code
    # keys `15.2` fixed.
    #
    # SCOPE IS THE HEADLINE, NOT THE BLOCK: the block carries *(Superseded...)*
    # notes citing dead ids (`14.9`, `15.4`, `15.3`), and scanning those would
    # resurrect exactly the match-its-own-description bug gauge_check already
    # had. The headline is the direction line; the block is history.
    #
    # ids[0] STILL HANDLES "...then `17.1` -> `17.3`" CORRECTLY — the FIRST id
    # in the headline is the named next action; the rest are what follows it.
    ids = list(dict.fromkeys(TASK_ID.findall(headline)))
    if not ids:
        # Names work (or anything else) but cites no id, and did not use the
        # legal "nothing planned" escape. This is exactly the failure 17.2
        # exists to catch: a rung with nothing a session can grep the plan
        # for. Treated as orphaned rather than silently passed.
        return "ORPHANED", None, line_no

    tid = ids[0]
    exists = tid in TASK_ID.findall(plan) or any(p.search(plan) for p in _done_patterns(tid))
    if exists:
        return "CLEAN", tid, line_no
    return "ORPHANED", tid, line_no


def main():
    ap = argparse.ArgumentParser(description="Is the ❓ OPEN board still open, and does the ▲ ground rung's task still exist in the plan?")
    ap.add_argument("brief")
    ap.add_argument("--plan", required=True)
    a = ap.parse_args()

    brief = read(a.brief, "brief")
    plan = read(os.path.expanduser(a.plan), "plan")

    items = open_items(brief)
    r_status, r_tid, r_line = rung_task(brief, plan)

    print(f"  brief: {a.brief}")
    print(f"  plan:  {a.plan}")

    # ⭐ STRUCTURAL ABSENCE FIRST — same token (NO-BOARD) covers "no ❓ OPEN
    # bucket" and "no ▲ ground rung at all": both are a FACT about this
    # brief's shape, not a pass, and neither can be judged for staleness/
    # orphaning if it isn't there to judge.
    if items is None and r_status == "MISSING":
        print("\nNO-BOARD\n  neither a ❓ OPEN bucket nor a ▲ ground rung was found "
              "— a fact about this brief, not a pass.")
        sys.exit(3)
    if items is None:
        print("  ❓ OPEN bullets: none found (no bucket)")
    if r_status == "MISSING":
        print("  ▲ ground rung: none found")

    stale, checked = [], 0
    if items is not None:
        for ln, text in items:
            # ⭐ LEAD POSITION ONLY — a QUEUE ITEM leads with its id; a CITATION does not.
            # Found on this tool's first real run: the bullet "Is the noise floor big enough
            # to explain the 2 lost findings? `15.4` returned SUGGESTIVE" was flagged, but it
            # CITES a finished task inside an open question — it does not queue it. Matching
            # anywhere in the bullet reproduces gauge_check's old bug of matching prose that
            # merely mentions the thing. The fix is positional, not a keyword blocklist:
            # anything past the lead is discussion, and discussion of finished work is correct.
            lead = text[:LEAD_CHARS]
            for tid in dict.fromkeys(TASK_ID.findall(lead)):       # de-dup, keep order
                checked += 1
                for pat in _done_patterns(tid):
                    m = pat.search(plan)
                    if m:
                        pline = plan[:m.start()].count("\n") + 1
                        stale.append((tid, ln, pline, text.strip()[:96]))
                        break
        print(f"  ❓ OPEN bullets: {len(items)} · task ids checked: {checked}")

    if r_status != "MISSING":
        if r_tid:
            print(f"  ▲ ground rung (line {r_line}): names `{r_tid}` — "
                  f"{'found' if r_status == 'CLEAN' else 'NOT found'} in plan")
        else:
            print(f"  ▲ ground rung (line {r_line}): "
                  f"{'explicitly says nothing is planned' if r_status == 'CLEAN' else 'names work but cites no task id'}")

    # ⭐ RUNG-ORPHANED is checked ahead of STALE-OPEN — the ground rung is "the
    # one place that says what is next" (this file's own doctrine, restated in
    # skill-system's brief 2026-08-07), so it headlines when both fire. Neither
    # finding is dropped: if STALE-OPEN also holds, it is still printed below,
    # under the same rc (both are rc 2) so no automation depends on which of
    # the two heads the exit code.
    if r_status == "ORPHANED":
        print("\nRUNG-ORPHANED")
        if r_tid:
            print(f"  ⛔ `{r_tid}` — the ▲ ground rung (line {r_line}) names it, "
                  f"but the plan holds no such task.")
        else:
            print(f"  ⛔ the ▲ ground rung (line {r_line}) names work but cites no task id, "
                  f"and does not say \"no task planned.\"")
        print("\n  ⇒ The rung is pointing at nothing a session can find in the plan.")
        print("     Either the plan is missing the task, or the rung must say")
        print("     \"no task planned — run /autoplan\" if that is genuinely the state.")
        if stale:
            print(f"\n  ALSO: STALE-OPEN — {len(stale)} item(s) the PLAN marks DONE are still queued as OPEN:")
            for tid, bline, pline, snip in stale:
                print(f"  ⛔ `{tid}` — brief:{bline} still lists it OPEN, plan:{pline} marks it DONE")
                print(f"       {snip}")
        sys.exit(2)

    if stale:
        head = (f"STALE-OPEN  ({len(stale)} item(s) the PLAN marks DONE are still queued as OPEN)")
        print(f"\n{head}")
        for tid, bline, pline, snip in stale:
            print(f"  ⛔ `{tid}` — brief:{bline} still lists it OPEN, plan:{pline} marks it DONE")
            print(f"       {snip}")
        print("\n  ⇒ The board is a SECOND direction surface, and it is stale.")
        print("     The GROUND RUNG is the one place that says what is next.")
        print("     ❓ OPEN holds open QUESTIONS; tasks live in the PLAN.")
        print("  ⛔ Do NOT report this brief ready to hand off.")
        sys.exit(2)

    if items is None:
        print("\nNO-BOARD\n  no ❓ OPEN bucket found — a fact about this brief, not a pass.")
        sys.exit(3)

    print("\nBOARD-CLEAN\n  no ❓ OPEN item is marked DONE in the plan, "
          "and the ground rung's named task (if any) exists in the plan.")
    print("  ⚠ BOUND: this proves nothing is FINISHED-but-queued, and that the rung's task")
    print("    is IN the plan — not that either item still BELONGS to this project.")
    print("    Ownership is recorded nowhere in the system today.")
    sys.exit(0)


if __name__ == "__main__":
    main()

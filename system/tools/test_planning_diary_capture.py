#!/usr/bin/env python3
"""Format-tolerance harness for planning-diary-capture.py — read_journal() + build().

WHY THIS EXISTS
  The journal (producer) and this parser (consumer) drifted apart for two months and
  nothing noticed: 125 of 466 entry rows and 196 of 288 session blocks were silently
  dropped, so the Cal diary — and every lookback that reads it — saw a near-empty week.
  See state/handoff-cal-diary-format-drift.md and [CAL-DIARY-FORMAT-DRIFT] in the debt ledger.

WHAT IT LOCKS
  1. Every shape the journal actually writes is parsed (single-shape cases, T1-T15, T21-T25).
  2. REACH — a WHOLE DAY written the way the journal really writes one, all six shapes
     interleaved in one file with the days either side of it, must come back COMPLETE:
     an exact item count, not a spot-check (T16-T19b). That is the check the drift would have
     tripped. The drift dropped 68.8% of reachable history and nothing errored; the diary just
     came out thin, indistinguishable from a quiet week. A count is the only assertion that
     notices thin. Spot-checks do not: every individual shape can pass while the total collapses.
  3. NEGATIVE CONTROLS (T10, T13, T14, T20) — a mangled/other-date line must NOT be found.
     A check nobody has watched fail is not a check; T20 mangles the day fixture on purpose
     so the suite proves it can go red every single run, not just once at authoring time.

⛔ HERMETIC BY CONSTRUCTION — AND THIS IS A FIX, NOT A STYLE CHOICE (2026-08-15).
   T16-T20 used to read the OPERATOR'S REAL JOURNAL at the resolved notes root and assert on
   strings from one person's actual 2026-08-02 ("PHASE 7 CLOSED", "SKILL-FACTORY DETOUR", "SPY").
   Three separate ways that was wrong, all of which a shipped repo eats:
     · A fresh clone has NO journal — data/ is empty and system/desk-registry.yaml ships `desks: []`.
       The case went red on every install, forever, on a test nobody could green without the
       author's personal history. A permanently-red gate is a gate everybody learns to ignore.
     · Even WITH a journal, those assertion strings are one person's history. Nobody else's
       2026-08-02 says PHASE 7 CLOSED. It could not pass anywhere but one laptop.
     · It read personal data from a test — the residency leak this migration exists to remove.
   The aggregate runner (system/tools/run-all-tests.sh) exports a throwaway LIFEHACK_ROOT for
   exactly this class of test, and it was RIGHT to: the sandbox caught a real defect. The fix is
   here, in the test, not there. Everything the live case actually proved — mixed shapes in one
   real-shaped file, survival through build(), a negative control that bites — is proved by the
   day fixture below, plus a reach COUNT the live case never had.

Run:  python3 system/tools/test_planning_diary_capture.py
Exit: 0 = all green · 1 = any failure (prints a per-case report).
"""
import atexit
import importlib.util
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "planning-diary-capture.py")

# ⛔ SANDBOX THE DATA ROOT BEFORE THE IMPORT, NOT AFTER — the import is the leak.
# planning-diary-capture.py resolves the notes root at MODULE level (brain_root.resolve_brain_root()
# -> JOURNAL / STATUS_DIR / DIARY_ROOT) and sys.exit(2)s when there is none. So by the time this
# file could reassign cdc.JOURNAL, the damage is already done in both directions: with a root
# persisted, the module is bound to somebody's real journal; with no root set at all — a fresh
# clone, CI, a student's first hour — the import KILLS THE PROCESS before case T1 runs.
# Pointing LIFEHACK_ROOT at a throwaway directory first makes this file depend on nothing outside
# its own tempdir, and behave identically on every machine, installed or not.
_SANDBOX_ROOT = tempfile.mkdtemp(prefix="planning-diary-test-root.")
os.environ["LIFEHACK_ROOT"] = _SANDBOX_ROOT
atexit.register(shutil.rmtree, _SANDBOX_ROOT, ignore_errors=True)

_spec = importlib.util.spec_from_file_location("planning_diary_capture", SCRIPT)
cdc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cdc)

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))


def parse(text, date_str):
    """Run read_journal() against an in-memory journal fixture."""
    fd, path = tempfile.mkstemp(suffix=".md")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    saved = cdc.JOURNAL
    try:
        cdc.JOURNAL = path
        by_desk, status = cdc.read_journal(date_str)
    finally:
        cdc.JOURNAL = saved
        os.unlink(path)
    return by_desk, status


def flat(by_desk):
    return " ||| ".join(f"{d}: {b}" for d, bs in by_desk.items() for b in bs)


D = "2026-07-15"

# ---------------------------------------------------------------------------
# T1 — the OLD pipe row must keep working. Do not fix the new format by breaking the old:
#      both are present across the whole two-month corpus.
by, st = parse(f"| {D} | root | project-system | shipped the pipe-row thing |\n", D)
check("T1 old '| DATE |' entry row still parses",
      st == "ok" and "root" in by and any("shipped the pipe-row thing" in b for b in by.get("root", [])),
      flat(by))

# T2 — the newly-found half: the journal writes entries as markdown LIST ITEMS.
by, st = parse(f"- {D} | root | skill-system | shipped the dashed thing\n", D)
check("T2 dashed '- DATE |' entry row parses",
      "root" in by and any("shipped the dashed thing" in b for b in by.get("root", [])),
      flat(by))

# T3 — indentation must not defeat it.
by, st = parse(f"   - {D} | planning | cadence-skills | indented dashed row\n", D)
check("T3 indented dashed entry row parses",
      "planning" in by and any("indented dashed row" in b for b in by.get("planning", [])),
      flat(by))

# T4 — the legacy block form, terminator included. Uses a generic desk name (not a real personal
# desk — same convention as system/hooks/tests/test_session_context_loader.sh's 'lamps'/'money').
by, st = parse(
    f"--- SESSION CONTEXT | {D} | lamps | lamps-intake ---\n"
    "session: legacy block body\n"
    "state: something\n"
    "---\n", D)
check("T4 legacy '--- SESSION CONTEXT |' block parses + extracts session:",
      "lamps" in by and any("legacy block body" in b for b in by.get("lamps", [])),
      flat(by))

# T5 — the current H2 form with an explicit desk field.
by, st = parse(
    f"## SESSION CONTEXT — {D} | root | translator-voice (the command reframe)\n"
    "**Session:** rebuilt the translator voice\n", D)
check("T5 '## SESSION CONTEXT — DATE | desk | slug' parses to the desk",
      "root" in by and any("rebuilt the translator voice" in b for b in by.get("root", [])),
      flat(by))

# T6 — the slash variant: '| root / subagent-delegation'.
by, st = parse(
    f"## SESSION CONTEXT — {D} | root / subagent-delegation\n"
    "**Session:** found the deterministic root cause\n", D)
check("T6 '| desk / slug' variant attributes to the desk",
      "root" in by and any("deterministic root cause" in b for b in by.get("root", [])),
      flat(by))

# T7 — no desk field anywhere (40 blocks look like this). Must still be CAPTURED, not dropped;
#      unattributed is honest, silent loss is not.
by, st = parse(
    f"## SESSION CONTEXT — {D} — Helm whole-dashboard re-scope kickoff\n"
    "Enver dumped a full walkthrough.\n", D)
check("T7 desk-less H2 block is captured (not silently dropped)",
      any("Helm whole-dashboard re-scope" in b for bs in by.values() for b in bs),
      flat(by))

# T8/T9 — the bold decision/build lines.
by, st = parse(f"**DECISION {D} | root | project-system |** Grand Central scope LOCKED\n", D)
check("T8 '**DECISION DATE | desk | slug |**' parses",
      "root" in by and any("Grand Central scope LOCKED" in b for b in by.get("root", [])),
      flat(by))

by, st = parse(f"**BUILD {D} | root | project-system |** Built PHASE 5 capture\n", D)
check("T9 '**BUILD DATE | desk | slug |**' parses",
      "root" in by and any("Built PHASE 5 capture" in b for b in by.get("root", [])),
      flat(by))

# T10 — NEGATIVE: a dateless bold line must not be mistaken for a dated one.
by, st = parse("**DECISION (Enver):** FB.4 backfill = STAGED\n", D)
check("T10 dateless '**DECISION (Enver):**' is ignored",
      not any("FB.4 backfill" in b for bs in by.values() for b in bs),
      flat(by))

# T11 — the plain dated H2 that names its desk inline.
by, st = parse(
    f"## {D} — root — claudeops-correct-architecture — SESSION CONTEXT: residency RESOLVED\n"
    "body line\n", D)
check("T11 '## DATE — desk — slug — text' attributes to the desk",
      "root" in by and any("residency RESOLVED" in b for b in by.get("root", [])),
      flat(by))

# T12 — the plain dated H2 with only a bracketed slug.
by, st = parse(
    f"## {D} (session 2, cont.) — THE LLM IS INSIDE THE TRUST BOUNDARY [SKILL-SYSTEM]\n"
    "body line\n", D)
check("T12 '## DATE — text [SLUG]' is captured",
      any("TRUST BOUNDARY" in b for bs in by.values() for b in bs),
      flat(by))

# T13 — NEGATIVE + the terminator trap the handoff flagged: an H2 block has no '---' terminator,
#       so a naive forward scan swallows the rest of the file. A LATER, DIFFERENT-DATE row must
#       not be absorbed into this date's block.
by, st = parse(
    f"## SESSION CONTEXT — {D} — a block with no terminator\n"
    "body of the block\n"
    "\n"
    "| 2026-07-16 | money | budget-review | NEXT DAY should not appear |\n", D)
check("T13 H2 block does not swallow the next day's rows",
      not any("NEXT DAY should not appear" in b for bs in by.values() for b in bs),
      flat(by))

# T14 — NEGATIVE: other-date entry rows are excluded in every format.
by, st = parse(
    "| 2026-07-14 | root | x | WRONG DATE pipe |\n"
    "- 2026-07-16 | root | x | WRONG DATE dash |\n"
    f"- {D} | root | x | RIGHT DATE |\n", D)
check("T14 other-date rows excluded, right-date row kept",
      not any("WRONG DATE" in b for bs in by.values() for b in bs)
      and any("RIGHT DATE" in b for bs in by.values() for b in bs),
      flat(by))

# T15 — an H2 block ends at the next heading; it must not blob the following section in.
by, st = parse(
    f"## SESSION CONTEXT — {D} | root | slug-a\n"
    "**Session:** first block gist\n"
    "\n"
    "## SOME OTHER HEADING\n"
    "unrelated tail content\n", D)
check("T15 H2 block stops at the next heading",
      not any("unrelated tail content" in b for bs in by.values() for b in bs),
      flat(by))

# T21 — the H3 form (155 of these in the corpus): '### SESSION CONTEXT — DATE — slug', where the
#       only desk signal is the slug's conventional desk- prefix. Uses 'root' rather than a named
#       desk: KNOWN_DESKS is read from system/desk-registry.yaml with an EMPTY fallback (the donor's
#       fallback hardcoded that operator's seven personal desk names, which is exactly the residency
#       leak this migration removed — see planning-diary-capture.py's _FALLBACK_DESKS comment) plus a
#       hardcoded 'root'. 'root' is therefore the only desk id guaranteed present on any install,
#       registry populated or not, so it is the only portable fixture for this prefix-match path.
by, st = parse(
    f"### SESSION CONTEXT — {D} — root-onboarding\n"
    "session: graded the sides\n", D)
check("T21 '### SESSION CONTEXT — DATE — desk-prefixed-slug' attributes to the desk",
      "root" in by and any("graded the sides" in b for b in by.get("root", [])),
      flat(by))

# T22 — an EXACT desk segment always beats a prefix guess elsewhere in the heading.
by, st = parse(
    f"### SESSION CONTEXT — {D} — root/handshake-skill — planning-weekly rework\n"
    "session: re-synced the huddle\n", D)
check("T22 exact desk segment wins over a prefix match later in the heading",
      "root" in by and "planning" not in by,
      flat(by))

# T23 — NEGATIVE: a prefix match needs the hyphen boundary. 'calendar-diary' is not the cal desk
#       by prefix accident — it must not be attributed on a substring.
by, st = parse(
    f"### SESSION CONTEXT — {D} — calendar-diary\n"
    "session: built the emitter\n", D)
check("T23 'calendar-diary' is not attributed to 'cal' on a substring",
      "cal" not in by,
      flat(by))

# T24 — the legacy block scans forward to a bare '---'. When a block is written WITHOUT its
#       terminator (they are, in the corpus) that scan runs away and eats every row after it.
#       This is a third break path, found by the capture audit, not present in the handoff:
#       on 2026-06-07 alone it swallowed 28 entry rows.
by, st = parse(
    f"--- SESSION CONTEXT | {D} | root | slug-a ---\n"
    "session: unterminated block\n"
    "\n"
    f"| {D} | lamps | lamps-setup | row AFTER an unterminated block |\n"
    f"| {D} | money | budget-import | second row after it |\n", D)
check("T24 unterminated legacy block does not swallow the rows after it",
      "lamps" in by and "money" in by
      and any("row AFTER an unterminated block" in b for b in by.get("lamps", [])),
      flat(by))

# T25 — the slug-less row: '- DATE | desk | event' (5 of these, 2026-06-29). Two fields, not
#       three. Capture the event rather than dropping the row for a missing slug.
by, st = parse(f"- {D} | helm | Built all 4 onboarded dashboard tabs from cartridges\n", D)
check("T25 slug-less '- DATE | desk | event' row is captured",
      "helm" in by and any("Built all 4 onboarded" in b for b in by.get("helm", [])),
      flat(by))

# ---------------------------------------------------------------------------
# WHOLE-DAY REACH REGRESSION (T16-T19b) — the check the drift would have tripped.
#
# WHY A WHOLE DAY AND NOT MORE SINGLE-SHAPE CASES. The drift did not break one shape; it left
# every shape it knew about working and silently lost everything else — 125 of 466 entry rows,
# 196 of 288 session blocks. Every T1-T25 case above could have been green throughout. What
# failed was REACH: the total. So this fixture is one day written the way the journal really
# writes one — all six shapes interleaved, blocks that were never terminated, the days either
# side of it — and the assertion is an EXACT COUNT. Drop a shape and the count moves. That is
# the only thing that tells thin apart from quiet.
#
# It is dated 2026-08-02 — the day the drift was found, whose entries recorded this very bug —
# because keeping the date keeps the story attached to the case. The CONTENT is invented for
# this file and is nobody's history: see the HERMETIC banner at the top for why that had to
# change. The desk ids are the portable ones — 'root' is the only id guaranteed present on any
# install (KNOWN_DESKS falls back to {'root'} when desk-registry.yaml ships empty, which it
# does), and entry ROWS carry their desk verbatim so any name works there; only HEADING
# attribution needs the registry, which is why the heading cases below use root.
# ---------------------------------------------------------------------------
FD = "2026-08-02"
PREV, NEXT = "2026-08-01", "2026-08-03"

DAY_FIXTURE = f"""# Journal

## SESSION CONTEXT — {PREV} | root | skill-system
**Session:** the day BEFORE — must not leak forward into {FD}

| {PREV} | root | skill-system | PREVIOUS DAY row |

--- SESSION CONTEXT | {FD} | root | migration-audit ---
session: opened the audit and re-read the handoff
---

## SESSION CONTEXT — {FD} | root | skill-system (the phase closes)
**Session:** closed two phases back to back

- {FD} | root | skill-system | PHASE 6 CLOSED — the reader now sees every shape
- {FD} | root | skill-system | PHASE 7 CLOSED — the diary stopped coming out thin
- {FD} | planning | cadence-skills | SKILL-FACTORY DETOUR — built the emitter before the cadence
| {FD} | marc | market-regime | OLD PIPE ROW — regime read held, no position change |
**DECISION {FD} | root | project-system |** Grand Central scope LOCKED
**BUILD {FD} | root | project-system |** Built PHASE 5 capture
- {FD} | helm | Rebuilt all 4 dashboard tabs from cartridges

### SESSION CONTEXT — {FD} — root-onboarding
session: walked a newcomer through the map

## SESSION CONTEXT — {FD} — Helm whole-dashboard re-scope kickoff
A full walkthrough with no desk field anywhere — captured as unattributed, never dropped.

--- SESSION CONTEXT | {FD} | lamps | lamps-intake ---
session: an UNTERMINATED legacy block, exactly as the corpus writes them

| {FD} | money | budget-import | row AFTER an unterminated block |

## SOME OTHER HEADING
unrelated tail content

| {NEXT} | money | budget-review | NEXT DAY row |
- {NEXT} | root | x | NEXT DAY dashed row |
"""

# The count is written out longhand and BY DESK on purpose: when it moves, the failure detail
# below names which desk lost items, which is the first question anyone asks.
# root 7 = legacy block + H2 block + 2 dashed rows + DECISION + BUILD + H3 prefix-attributed block
EXPECTED_BY_DESK = {
    "root": 7, "planning": 1, "marc": 1, "helm": 1,
    cdc.UNATTRIBUTED: 1, "lamps": 1, "money": 1,
}
EXPECTED_REACH = sum(EXPECTED_BY_DESK.values())      # 13

day, day_st = parse(DAY_FIXTURE, FD)

check("T16 whole day: both root/skill-system dashed phase-closes are found",
      sum(1 for b in day.get("root", []) if "PHASE 7 CLOSED" in b or "PHASE 6 CLOSED" in b) == 2,
      flat(day)[:400])

check("T17 whole day: the planning dashed entry is found alongside them",
      any("SKILL-FACTORY DETOUR" in b for b in day.get("planning", [])),
      flat(day)[:400])

# T18 — THE COEXISTENCE PROPERTY. Old pipe rows and new dashed rows share the same day in the
# same file. Both formats have been live since June, so a fix that reads one by breaking the
# other is not a fix — this asserts they parse in the same pass, which no single-shape case can.
check("T18 whole day: the OLD pipe row parses in the same pass as the dashed rows",
      any("OLD PIPE ROW" in b for b in day.get("marc", []))
      and any("PHASE 7 CLOSED" in b for b in day.get("root", [])),
      flat(day)[:400])

body = cdc.build(FD, day, [], [], [],
                 {"journal": day_st, "status": "ok", "tasks": "ok", "calendar": "ok"})
check("T19 those entries survive into the composed diary body",
      "PHASE 7 CLOSED" in body and "SKILL-FACTORY DETOUR" in body and "## root" in body,
      f"body {len(body)} chars")

# T19b — REACH. The one assertion that catches a thin day. Exact, not >=: a drop AND a
# double-count are both defects, and the drift produced the first while looking like neither.
actual_by_desk = {d: len(bs) for d, bs in day.items()}
reach = sum(actual_by_desk.values())
check("T19b whole-day REACH: every capturable item comes back, exact count per desk",
      actual_by_desk == EXPECTED_BY_DESK and reach == EXPECTED_REACH,
      f"expected {EXPECTED_BY_DESK} (reach {EXPECTED_REACH}) · got {actual_by_desk} (reach {reach})")

# T20 — NEGATIVE CONTROL / FAIL-FIXTURE. Mangle the date on the two dashed root rows and prove
# T16 goes to zero AND reach drops by exactly 2. Without this, T16 could be green for a reason
# that has nothing to do with format tolerance, and the whole suite would be decorative.
# It asserts the mangle CHANGED something first — a no-op replace would pass vacuously.
mangled = DAY_FIXTURE.replace(f"- {FD} | root | skill-system |",
                              "- 1999-01-01 | root | skill-system |")
by_m, _ = parse(mangled, FD)
reach_m = sum(len(bs) for bs in by_m.values())
check("T20 fail-fixture: mangling the dashed rows makes T16 go red and reach drop by 2",
      mangled != DAY_FIXTURE
      and sum(1 for b in by_m.get("root", []) if "PHASE 7 CLOSED" in b or "PHASE 6 CLOSED" in b) == 0
      and reach_m == EXPECTED_REACH - 2,
      f"reach {reach_m} (expected {EXPECTED_REACH - 2}) · {flat(by_m)[:300]}")

# ---------------------------------------------------------------------------
passed = sum(1 for _, ok, _ in results if ok)
total = len(results)
print(f"\n=== {passed}/{total} PASSED ===")
if passed != total:
    print("FAILURES:")
    for name, ok, detail in results:
        if not ok:
            print(f"  ✗ {name} — {detail}")
sys.exit(0 if passed == total else 1)

#!/usr/bin/env python3
"""map_carry_receipt -- proves every finding in the Map either reached the scratchpad, or
was explicitly declared dropped.  [Parts Library]

WHY:  measured, real run, cal-weekly 2026-08-03 (week 2026-W32). Phase 0's map-agent wrote
      a CONFIRMED same-day scheduling conflict into map.md:

        "Monday Aug 3, 10:30am -- the daily "Eat" block collides with a real business
        meeting -- recurring "Eat" (10:30am) overlaps "xx - Business Mtg" (10:30-11:30am),
        confirmed by calendar-notification email."
        pointer: oqf8f7hv3eh0sb2qt9tinlknpa_20260803T143000Z (Eat) /
                 kv7eb80ssvdrbencg6p35ruok3_20260803T143000Z (xx - Business Mtg) /
                 confirming email 19fc2e1f238fca95

      It never reached session-scratchpad.md. The human read the scratchpad and was never
      told. `fanout_completeness.py` guards the FIRST seam (agents -> map) and reported
      242/242 covered, zero lost, on this exact run -- it says nothing about the SECOND
      seam (map -> scratchpad), which has no gate at all. This is the same class of loss
      that dropped a coaching client's ER-fall thread on 2026-07-21.

WHAT: parses map.md's `### Findings` sections into a numbered, pointer-tagged list, then
      checks the scratchpad for a trace of each one -- its `F<NNN>` tag, any one of its
      backticked pointer ids, or an explicit `DROPPED --` line naming it. Anything with
      none of the three is reported BY NAME: id, headline, and pointer ids -- a bare count
      is useless to the human who has to go find what got lost.

⚠ KNOWN BOUND: this proves TRACEABILITY, not FIDELITY. A finding that reached the
      scratchpad in a compressed, reworded, or even materially thinned form still PASSES
      this check as long as one of its ids survived -- this part cannot tell "carried
      faithfully" from "carried barely." It exists to catch SILENT DISAPPEARANCE, the
      2026-08-03 failure mode, not to grade how well a surviving finding was carried.
      Deliberately generous on the carry test (any one signal is enough) and strict on the
      outcome (every finding must clear that low bar or be named as having failed to).

USAGE
  map_carry_receipt.py --map map.md --scratchpad session-scratchpad.md
  map_carry_receipt.py --map map.md --scratchpad session-scratchpad.md --json
  map_carry_receipt.py --selftest

EXIT CODES
  0  CARRIED       -- one or more findings were parsed from map.md, and every one of them
                      is traceable in the scratchpad (by tag, pointer id, or an explicit
                      DROPPED line naming it). The report states the denominator measured
                      (e.g. "37/37") so a real pass is never confused with an empty one.
  1  UNCARRIED     -- one or more findings have NO trace in the scratchpad at all. Every
                      one is named: id, headline, pointer ids. Do not treat the scratchpad
                      as complete.
  2  CANNOT EVALUATE -- missing/unreadable file, OR map.md parsed to ZERO findings, in ANY
                      document shape -- whether `### Findings` sections are present but
                      parsed empty (a parser break), or no `### Findings` section was found
                      at all (a shape this parser doesn't recognize). ⚠ A ZERO DENOMINATOR
                      IS NEVER A PASS: this tool cannot tell "the week genuinely had no
                      findings" apart from "the map is in a shape this parser can't read" --
                      those are opposite situations that must not share an exit code, so
                      both are refused for a human to resolve rather than one being silently
                      reported as a clean carry of nothing.
"""

import argparse
import json
import os
import re
import sys

CARRIED, UNCARRIED, CANNOT_EVALUATE = 0, 1, 2

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
FINDINGS_HEADING_RE = re.compile(r"^###\s+Findings\b", re.IGNORECASE | re.MULTILINE)
BULLET_RE = re.compile(r"^- \*\*(.+?)\*\*")
BACKTICK_RE = re.compile(r"`([^`]+)`")
DROPPED_RE = re.compile(r"DROPPED\s*[-—]+\s*(.*)", re.IGNORECASE)
WORD_RE = re.compile(r"[a-z0-9]+")


def _die(msg):
    print(f"CANNOT EVALUATE: {msg}", file=sys.stderr)
    sys.exit(CANNOT_EVALUATE)


# ---------------------------------------------------------------- parsing map.md

def parse_findings(map_text):
    """Walk map.md line by line. A finding is a top-level `- **...**` bullet inside a
    `### Findings` section (there are several `## <Angle>` sections, each with its own).
    Any other heading (## or ###) closes the findings zone -- this is what keeps
    "### Pre-drafted questions" and "### Marked deltas" bullets out of the finding set,
    even though some of those also start with a bare `- `."""
    findings = []
    in_findings = False
    current = None  # dict being built, or None

    def flush():
        if current is not None:
            findings.append(current)

    for raw_line in map_text.splitlines():
        line = raw_line.rstrip("\n")
        h = HEADING_RE.match(line)
        if h:
            if FINDINGS_HEADING_RE.match(line):
                in_findings = True
            else:
                flush()
                current = None
                in_findings = False
            continue

        if not in_findings:
            continue

        b = BULLET_RE.match(line)
        if b:
            flush()
            n = len(findings) + 1
            current = {
                "id": n,
                "tag": f"F{n:03d}",
                "headline": b.group(1).strip(),
                "pointer_ids": [],
                "lines": [line],
            }
            continue

        if current is not None:
            current["lines"].append(line)
            if "pointer:" in line.lower():
                current["pointer_ids"].extend(BACKTICK_RE.findall(line))

    flush()
    return findings


# ---------------------------------------------------------------- checking against the scratchpad

def _normalize(text):
    return " ".join(WORD_RE.findall(text.lower()))


def _tag_hit(tag, scratchpad_text):
    return re.search(rf"\b{re.escape(tag)}\b", scratchpad_text) is not None


def _pointer_hit(pointer_ids, scratchpad_text):
    return [p for p in pointer_ids if p and p in scratchpad_text]


def _dropped_reasons(scratchpad_text):
    """Every `DROPPED --` line's reason text, as found in the scratchpad."""
    return DROPPED_RE.findall(scratchpad_text)


def _dropped_hit(finding, dropped_reasons):
    """A DROPPED line counts for THIS finding if its reason names the tag, a pointer id,
    or shares enough of the headline's distinctive words (>=2 words of length>=5) to be
    read as naming the same finding -- deliberately generous, per the brief."""
    headline_words = {w for w in WORD_RE.findall(finding["headline"].lower()) if len(w) >= 5}
    for reason in dropped_reasons:
        reason_norm = _normalize(reason)
        if finding["tag"].lower() in reason_norm:
            return True
        if any(pid.lower() in reason_norm for pid in finding["pointer_ids"] if pid):
            return True
        reason_words = set(reason_norm.split())
        if len(headline_words & reason_words) >= 2:
            return True
    return False


def check_carry(findings, scratchpad_text):
    """Returns (carried, uncarried) -- lists of finding dicts, each annotated with
    'status' (REFERENCED / DECLARED-DROPPED / UNCARRIED) and 'evidence'."""
    dropped_reasons = _dropped_reasons(scratchpad_text)
    carried, uncarried = [], []
    for f in findings:
        # Checked FIRST, ahead of a plain tag/pointer hit: an explicit "DROPPED — F00N"
        # line necessarily also contains the bare tag text, so testing tag/pointer first
        # would misreport a real declared-drop as an ordinary REFERENCED carry. Both are
        # "carried" for the exit-code contract either way -- this ordering only affects
        # which status a human sees in the report.
        if _dropped_hit(f, dropped_reasons):
            f = dict(f, status="DECLARED-DROPPED", evidence=["explicit DROPPED line"])
            carried.append(f)
            continue
        tag_hit = _tag_hit(f["tag"], scratchpad_text)
        ptr_hits = _pointer_hit(f["pointer_ids"], scratchpad_text)
        if tag_hit or ptr_hits:
            f = dict(f, status="REFERENCED",
                     evidence=(["tag"] if tag_hit else []) + [f"pointer:{p}" for p in ptr_hits])
            carried.append(f)
            continue
        f = dict(f, status="UNCARRIED", evidence=[])
        uncarried.append(f)
    return carried, uncarried


# ---------------------------------------------------------------- rendering

def render(findings, carried, uncarried):
    lines = [f"map_carry_receipt -- {'CARRIED' if not uncarried else 'UNCARRIED'} "
             f"({len(carried)}/{len(findings)} findings traced into the scratchpad)"]
    if not findings:
        lines.append("  no findings parsed from map.md's ### Findings sections")
        return "\n".join(lines)
    if uncarried:
        lines.append(f"  {len(uncarried)} finding(s) have NO trace in the scratchpad "
                     f"(no tag, no pointer id, no explicit DROPPED line):")
        for f in uncarried:
            lines.append(f"  - {f['tag']}: {f['headline']}")
            lines.append(f"      pointers: {', '.join(f['pointer_ids']) or '(none captured)'}")
    else:
        n_dropped = sum(1 for f in carried if f["status"] == "DECLARED-DROPPED")
        lines.append(f"  every finding traced ({len(carried) - n_dropped} referenced, "
                     f"{n_dropped} explicitly declared dropped)")
    return "\n".join(lines)


def to_json(findings, carried, uncarried):
    return {
        "verdict": "CARRIED" if not uncarried else "UNCARRIED",
        "exit": CARRIED if not uncarried else UNCARRIED,
        "total_findings": len(findings),
        "carried_count": len(carried),
        "uncarried_count": len(uncarried),
        "uncarried": [
            {"tag": f["tag"], "headline": f["headline"], "pointer_ids": f["pointer_ids"]}
            for f in uncarried
        ],
        "carried": [
            {"tag": f["tag"], "headline": f["headline"], "status": f["status"],
             "evidence": f["evidence"]}
            for f in carried
        ],
    }


# ---------------------------------------------------------------- self-test (two-sided, non-negotiable)

def selftest():
    ok = True

    def report(label, passed, detail=""):
        nonlocal ok
        ok = ok and passed
        print(f"  [{'PASS' if passed else 'FAIL'}] {label}{(' -- ' + detail) if detail else ''}")

    print("map_carry_receipt --selftest")

    SYNTH_MAP = """# The Map — synthetic

## Conflicts

### Findings (ordered biggest-signal first; OMIT NOTHING)

- **Monday 10am — two meetings collide** — "Standup" overlaps "1:1 with Boss".
  · pointer: `evtaaa111111` (Standup) · `evtbbb222222` (1:1) · confirming email `emailccc333`
  · confidence: CONFIRMED

- **Tuesday 3pm — a dentist appointment sits against a client call** — details here.
  · pointer: `evtddd444444` (appointment) · `evtefff555555` (Client call)
  · confidence: CONFIRMED

### Pre-drafted questions (not findings — must not be parsed as one)
1. Some question — `evtaaa111111` mentioned here should NOT create a phantom finding.

---

## Lanes

### Findings (ordered biggest-signal first; OMIT NOTHING)

- **Finances — a bill is overdue** — the electric bill is 10 days late.
  · pointer: `taskgggg7777`
  · confidence: CONFIRMED

### Marked deltas (not findings — bare bullets here must not be parsed as findings either)
- Some delta note that starts with a bare dash, no bold headline.
"""
    findings = parse_findings(SYNTH_MAP)
    report("parses exactly 3 findings across 2 Angle sections (not the pre-drafted "
           "question, not the marked-delta bullet)",
           len(findings) == 3, f"got {len(findings)}")
    report("assigns deterministic ids F001..F003 in document order",
           [f["tag"] for f in findings] == ["F001", "F002", "F003"],
           f"got {[f['tag'] for f in findings]}")
    report("F001 captures both pointer ids off its pointer line",
           findings and set(findings[0]["pointer_ids"]) >= {"evtaaa111111", "evtbbb222222"},
           f"got {findings[0]['pointer_ids'] if findings else None}")

    # ---- CASE 1: all findings carried (by tag / by pointer id) -> exit 0 ----
    scratch_all_carried = """# scratchpad
- F001 discussed with the operator, moved Standup.
- The dentist thing (evtddd444444) got a note.
- electric bill (taskgggg7777) flagged to pay.
"""
    carried, uncarried = check_carry(findings, scratch_all_carried)
    report("CASE all-carried: 3/3 carried, 0 uncarried -> would exit 0",
           len(carried) == 3 and len(uncarried) == 0,
           f"carried={len(carried)} uncarried={len(uncarried)}")

    # ---- CASE 2: one finding vanishes silently -> non-zero AND named ----
    scratch_vanished = """# scratchpad
- F001 discussed with the operator, moved Standup.
- electric bill (taskgggg7777) flagged to pay.
"""
    carried, uncarried = check_carry(findings, scratch_vanished)
    report("CASE vanished: exactly the dentist finding (F002) is uncarried",
           len(uncarried) == 1 and uncarried[0]["tag"] == "F002",
           f"uncarried={[f['tag'] for f in uncarried]}")
    report("...and it is NAMED by tag + headline + pointer ids in the rendered report",
           "F002" in render(findings, carried, uncarried)
           and "dentist" in render(findings, carried, uncarried).lower()
           and "evtddd444444" in render(findings, carried, uncarried))

    # ---- CASE 3: the same vanished finding is explicitly DROPPED -> exit 0 ----
    scratch_declared_dropped = scratch_vanished + (
        "\nDROPPED — F002: the dentist/client-call collision was reviewed and intentionally "
        "not carried forward, the operator already knows about it.\n"
    )
    carried, uncarried = check_carry(findings, scratch_declared_dropped)
    report("CASE declared-dropped: an explicit 'DROPPED — F002' line makes it CARRIED "
           "(a declared drop is honoured, not treated as a loss)",
           len(uncarried) == 0 and len(carried) == 3,
           f"carried={len(carried)} uncarried={len(uncarried)}")
    dropped_status = next((f["status"] for f in carried if f["tag"] == "F002"), None)
    report("...and its status records DECLARED-DROPPED, distinguishable from a plain reference",
           dropped_status == "DECLARED-DROPPED", f"status={dropped_status}")

    # ---- reason-only drop (no F-tag, headline word overlap) also honoured ----
    scratch_reason_drop = scratch_vanished + (
        "\nDROPPED — the dentist appointment against the client call was a non-issue, "
        "already rescheduled before this run.\n"
    )
    carried, uncarried = check_carry(findings, scratch_reason_drop)
    report("CASE declared-dropped by reason text alone (no F-tag) still honoured via "
           "headline word overlap",
           len(uncarried) == 0, f"uncarried={[f['tag'] for f in uncarried]}")

    # ---- empty scratchpad: everything uncarried, all named ----
    carried, uncarried = check_carry(findings, "")
    report("CASE empty scratchpad: all 3 findings uncarried and named",
           len(uncarried) == 3 and {f["tag"] for f in uncarried} == {"F001", "F002", "F003"})

    # ---- check_carry() itself is neutral on zero findings: given nothing to check, it
    # correctly returns nothing carried and nothing uncarried. This is ONLY the raw
    # categorization helper -- it does NOT decide the tool's exit code. That decision
    # lives in main(), and the CLI tests below prove main() refuses a zero denominator
    # rather than reading this neutral []/[] as a pass (S12.6: a zero-findings parse must
    # NEVER exit CARRIED, in any document shape -- see the CLI tests below).
    carried0, uncarried0 = check_carry([], "anything")
    report("check_carry() on zero findings returns empty/empty (a neutral non-verdict, "
           "NOT a pass -- main() below is what refuses it)",
           carried0 == [] and uncarried0 == [])

    # ---- CLI exit-code contract ----
    import subprocess
    import tempfile
    me = os.path.abspath(__file__)

    # A map.md shaped with NO '### Findings' heading at all -- e.g. bullets sitting
    # directly under an Angle heading, the shape a map-agent produces before/without the
    # '### Findings' convention. This is the S12.6 defect fixture: the OLD code's guard
    # only fired when a '### Findings' heading was present-but-empty, so a map in THIS
    # shape parsed to zero findings and fell through to a vacuous exit-0 CARRIED.
    MAP_NO_FINDINGS_HEADING = """# The Map — no Findings-heading shape

## Conflicts

- **Monday 10am — two meetings collide** — "Standup" overlaps "1:1 with Boss".
  · pointer: `evtaaa111111`
"""
    # A map.md that DOES use the '### Findings' heading, but the parser gets zero bullets
    # out of it -- the original, narrower parser-break case the old guard already caught.
    MAP_FINDINGS_HEADING_EMPTY = """# The Map — heading present, body empty

## Conflicts

### Findings (ordered biggest-signal first; OMIT NOTHING)

Nothing was found this week (prose, not a bulleted finding -- BULLET_RE won't match this).
"""

    with tempfile.TemporaryDirectory() as td:
        mp = os.path.join(td, "map.md")
        sp = os.path.join(td, "scratch.md")
        with open(mp, "w", encoding="utf-8") as fh:
            fh.write(SYNTH_MAP)

        with open(sp, "w", encoding="utf-8") as fh:
            fh.write(scratch_all_carried)
        rc = subprocess.run([sys.executable, me, "--map", mp, "--scratchpad", sp],
                            capture_output=True, text=True).returncode
        report("CLI all-carried -> exit 0", rc == CARRIED, f"got exit {rc}")

        with open(sp, "w", encoding="utf-8") as fh:
            fh.write(scratch_vanished)
        proc = subprocess.run([sys.executable, me, "--map", mp, "--scratchpad", sp],
                              capture_output=True, text=True)
        report("CLI vanished -> exit 1, and stdout NAMES F002", proc.returncode == UNCARRIED
               and "F002" in proc.stdout, f"got exit {proc.returncode}")

        with open(sp, "w", encoding="utf-8") as fh:
            fh.write(scratch_declared_dropped)
        rc = subprocess.run([sys.executable, me, "--map", mp, "--scratchpad", sp],
                            capture_output=True, text=True).returncode
        report("CLI declared-dropped -> exit 0", rc == CARRIED, f"got exit {rc}")

        rc = subprocess.run([sys.executable, me, "--map", os.path.join(td, "nope.md"),
                             "--scratchpad", sp], capture_output=True, text=True).returncode
        report("CLI missing map file -> exit 2 (fail-closed)", rc == CANNOT_EVALUATE,
               f"got exit {rc}")

        # ---- S12.6: the vacuous-pass fixtures. Neither shape may ever exit CARRIED. ----
        with open(mp, "w", encoding="utf-8") as fh:
            fh.write(MAP_NO_FINDINGS_HEADING)
        proc = subprocess.run([sys.executable, me, "--map", mp, "--scratchpad", sp],
                              capture_output=True, text=True)
        report("CLI zero findings, NO '### Findings' heading in the doc at all -> exit 2, "
               "NOT a vacuous exit-0 CARRIED (S12.6)",
               proc.returncode == CANNOT_EVALUATE and "0 of 0" in proc.stderr,
               f"got exit {proc.returncode}, stderr={proc.stderr.strip()!r}")

        with open(mp, "w", encoding="utf-8") as fh:
            fh.write(MAP_FINDINGS_HEADING_EMPTY)
        proc = subprocess.run([sys.executable, me, "--map", mp, "--scratchpad", sp],
                              capture_output=True, text=True)
        report("CLI zero findings, '### Findings' heading present but body doesn't parse "
               "-> exit 2, NOT a vacuous exit-0 CARRIED",
               proc.returncode == CANNOT_EVALUATE and "0 of 0" in proc.stderr,
               f"got exit {proc.returncode}, stderr={proc.stderr.strip()!r}")

    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


# ---------------------------------------------------------------- CLI

def main():
    ap = argparse.ArgumentParser(
        description="map_carry_receipt -- did every map.md finding reach the scratchpad, "
                    "or get explicitly declared dropped?")
    ap.add_argument("--map", help="path to map.md")
    ap.add_argument("--scratchpad", help="path to session-scratchpad.md")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())

    if not args.map or not args.scratchpad:
        _die("--map and --scratchpad are required")
    for p, what in ((args.map, "map.md"), (args.scratchpad, "scratchpad")):
        if not os.path.isfile(p):
            _die(f"{what} not found: {p!r}")

    try:
        map_text = open(args.map, encoding="utf-8").read()
    except OSError as e:
        _die(f"cannot read map.md: {e}")
    try:
        scratchpad_text = open(args.scratchpad, encoding="utf-8").read()
    except OSError as e:
        _die(f"cannot read scratchpad: {e}")

    findings = parse_findings(map_text)
    if not findings:
        # ⚠ ZERO DENOMINATOR, NEVER A PASS -- regardless of WHY it's zero. The old guard
        # only fired here when a `### Findings` heading was present but parsed empty
        # (a parser break on a recognized shape). That left a second, wider hole: a map.md
        # in ANY OTHER shape -- no `### Findings` heading at all -- also parses to zero
        # findings, and fell through to check_carry([], ...), which trivially "carries"
        # zero of zero and exits 0 CARRIED having measured nothing. Both branches below
        # name a real, distinct 0-of-0 situation and BOTH refuse -- a checker that can
        # print "0/0 CARRIED" indistinguishably from "37/37 CARRIED" certifies emptiness
        # as success, which is worse than no check at all.
        if re.search(FINDINGS_HEADING_RE, map_text):
            _die("map.md has one or more '### Findings' sections but the parser extracted "
                 "ZERO bullets from them (denominator measured: 0 of 0) -- this is a parser "
                 "break on a RECOGNIZED shape, not evidence there is nothing to carry. "
                 "Refusing rather than reporting a vacuous pass.")
        else:
            _die("map.md parsed to ZERO findings (denominator measured: 0 of 0) -- no "
                 "'### Findings' section was recognized in this document AT ALL, so this "
                 "check has nothing to measure the scratchpad against. This tool cannot "
                 "tell 'the week genuinely had zero findings' apart from 'this map.md is in "
                 "an unrecognized shape' -- those are opposite situations, and a zero "
                 "denominator must never silently pass as either. A human must confirm "
                 "which one this is; refusing rather than reporting a vacuous pass.")

    carried, uncarried = check_carry(findings, scratchpad_text)

    if args.json:
        print(json.dumps(to_json(findings, carried, uncarried), indent=2))
    else:
        print(render(findings, carried, uncarried))

    sys.exit(UNCARRIED if uncarried else CARRIED)


if __name__ == "__main__":
    main()

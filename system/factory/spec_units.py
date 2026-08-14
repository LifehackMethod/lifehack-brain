#!/usr/bin/env python3
"""spec_units — the MECHANICAL denominator for a spec.  [Factory · S1.2]

WHAT: scans a spec by STRUCTURE and emits every normative unit it contains, each with a
      stable id. No model is asked how many requirements a document has.
WHY:  Law 4.1 — completeness cannot be verified by something that can't hold the source.
      The sorter downstream is an LLM extracting clauses; if the only record of "how many
      requirements existed" is that same LLM's output, the sorter is grading its own
      completeness by reading its own claim. That is the exact failure that let a Map
      built from 241 items pass as "omitting nothing" while 20 were traceably covered.
      So the denominator is pinned HERE, mechanically, BEFORE any model sees the spec.

THE ASYMMETRY THAT DRIVES EVERY CHOICE BELOW.
      UNDER-counting is dangerous: a normative line this scanner misses never enters the
      denominator, so a sorter that also misses it still scores 100% coverage. The loss
      becomes invisible in both places at once.
      OVER-counting is merely noisy: a prose sentence wrongly marked normative shows up
      as an uncovered unit, someone looks, and dismisses it in a second.
      Therefore this scanner leans INCLUSIVE. When a line is ambiguous it counts.

WHAT COUNTS AS A NORMATIVE UNIT
  - a list item (bulleted or numbered) inside the section, or
  - a sentence carrying a normative modal (must · never · always · do NOT · shall ·
    required · only · cannot · may not · should), or
  - a bolded directive line (a whole line that is bold and reads as an instruction).
  Headings, code fences, blockquote attributions and table rows are NOT units — they are
  structure, not requirements. Everything skipped is still RETURNED (with
  `normative: false`) so nothing is silently discarded and a human can audit the cut.

IDS ARE STABLE AND CITATION-SHAPED. `<slug>_u<line>` — lowercase, ≥12 chars, no capitals,
so the id survives `completeness_receipt.py`'s native-id heuristic when the sorter later
cites its sources and set-diffs its own coverage. Position-derived, so re-running on an
unchanged spec yields byte-identical ids.

USAGE
  spec_units.py --spec FILE [--section "Phase 2"] [--slug cw] [--json]
  spec_units.py --spec FILE --section "Phase 2" --ids-only     # the denominator, one id/line
  spec_units.py --selftest

EXIT CODES
  0  units found
  1  the section exists but contains ZERO normative units (a real finding — refuse to
     hand downstream a vacuous denominator)
  2  CANNOT EVALUATE — missing file, section not found. Fail-closed.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

FOUND, EMPTY, CANNOT_EVALUATE = 0, 1, 2

MODALS = r"(?:must|never|always|shall|cannot|can't|required|require[sd]?|only|do not|don't|may not|should|need[s]? to|has to|have to)"
_RX_MODAL = re.compile(rf"\b{MODALS}\b", re.IGNORECASE)
_RX_LIST = re.compile(r"^[ \t]*(?:[-*+]|\d+[.)])[ \t]+\S")
_RX_HEAD = re.compile(r"^(#{1,6})\s+(.*)$")
_RX_BOLD_LINE = re.compile(r"^[ \t]*\*\*[^*].*\*\*[ \t]*:?[ \t]*$")
_RX_TABLE = re.compile(r"^[ \t]*\|")
_RX_FENCE = re.compile(r"^[ \t]*(```|~~~)")

# ── NON-NORMATIVE SECTIONS: headings that disqualify everything under them ────────────
#
# A clause under one of these is NOT a runtime obligation no matter how imperative its
# own sentence sounds. This is DETERMINISTIC and runs before any model call -- it is
# both cheaper and more correct than asking a judge to infer it from a sentence that
# does not contain the disqualifying information.
#
# ⭐ THE SIGNATURES ARE DERIVED FROM REAL HEADINGS, NOT INVENTED. Every pattern below
# was read off an actual spec in this repo (cal-weekly's combined phase doc and
# an ingest skill's SKILL.md), and only TWO classes are included -- the two where the
# heading itself states the section is not in force:
#   (a) EXPLICITLY UNBUILT / DEFERRED -- "What Phase 0 Requires That Isn't Built Yet",
#       "Extraction note (Phase 4C — do not act yet)". The section says outright that
#       the thing does not exist or must not be acted on.
#   (b) EXPLICITLY UNDECIDED -- "Open Question: Lens Structure", "Open Question: One
#       Readout vs Split". A question under debate cannot also be a rule in force.
#
# ⛔ DELIBERATELY EXCLUDED, though they are just as non-normative in practice:
# descriptive headings ("What It Is", "Cast of Characters", "TL;DR"), and negative-scope
# headings ("What this skill does NOT do"). They are a judgment call about PROSE STYLE
# rather than a declaration about FORCE, and "What this skill does NOT do" in particular
# often carries real constraints worth enforcing. Matching them would trade this file's
# false-POSITIVE problem for a false-NEGATIVE one -- silently dropping real rules, which
# is the worse direction. If they need handling, that is a classifier axis, not a regex.
_NON_NORMATIVE_HEADINGS = [
    r"\bisn'?t\s+built\s+yet\b",
    r"\bnot\s+(?:yet\s+)?built\b",
    r"\bdo\s+not\s+act\s+yet\b",
    r"\bdon'?t\s+act\s+yet\b",
    r"\bdoes\s+not\s+(?:yet\s+)?exist\b",
    r"^open\s+question\b",
    r"\bnot\s+implemented\b",
]
_RX_NON_NORMATIVE = [re.compile(p, re.IGNORECASE) for p in _NON_NORMATIVE_HEADINGS]


def non_normative_heading(heading_path):
    """The heading in this path that disqualifies the section, or None.

    Checks the WHOLE path, not just the nearest heading: the disqualifying heading is
    usually an ancestor ("### What Phase 0 Requires That Isn't Built Yet" governs the
    numbered list beneath it, and those list items have no heading of their own).
    """
    for h in (heading_path or []):
        for rx in _RX_NON_NORMATIVE:
            if rx.search(h or ""):
                return h
    return None


def _die(msg):
    print(f"CANNOT EVALUATE: {msg}", file=sys.stderr)
    sys.exit(CANNOT_EVALUATE)


def slice_section(text, section_rx):
    """Slice to the SHALLOWEST heading matching section_rx. Raises LookupError."""
    lines = text.splitlines()
    heads = [(len(m.group(1)), i, m.group(2).strip())
             for i, ln in enumerate(lines) if (m := _RX_HEAD.match(ln))]
    rx = re.compile(section_rx, re.IGNORECASE)
    cands = [h for h in heads if rx.search(h[2])]
    if not cands:
        raise LookupError(f"no heading matching /{section_rx}/ found")
    level, start, _ = min(cands, key=lambda h: (h[0], h[1]))
    end = next((i for lv, i, _ in heads if i > start and lv <= level), len(lines))
    return start, lines[start:end]


def classify_line(line):
    """Return (kind, normative). Structure only — no model, no guessing at meaning."""
    s = line.strip()
    if not s:
        return "blank", False
    if _RX_HEAD.match(line):
        return "heading", False
    if _RX_TABLE.match(line):
        return "table", False
    if _RX_LIST.match(line):
        return "list_item", True
    if _RX_BOLD_LINE.match(line):
        return "bold_directive", True
    if _RX_MODAL.search(s):
        return "modal_sentence", True
    return "prose", False


def scan(text, slug="spec", section=None):
    """Return (units, offset). Every line is returned; `normative` marks the denominator."""
    if section:
        offset, lines = slice_section(text, section)
    else:
        offset, lines = 0, text.splitlines()

    units, in_fence = [], False
    # ── HEADING CONTEXT (added 2026-07-29) ────────────────────────────────────────────
    # A clause used to travel with text + line + kind and NOTHING about where it SITS.
    # That is not a cosmetic gap: the judge grades one clause at a time, so
    # "3. The map-agent pipeline itself, with all four angles" reads like a requirement
    # -- and it IS one, right up until you notice the heading three lines above it says
    # "What Phase 0 Requires That Isn't Built Yet" and the line under that says "depends
    # on infrastructure that does not yet exist."
    # MEASURED: 6 of cw_p0's 7 "enforceable" clauses were items on that backlog. The
    # judge was not wrong about the sentences; it was never shown the room they are in.
    # `heading_path` is the full stack (H1 -> H2 -> H3), because the disqualifying
    # heading is often an ANCESTOR rather than the immediate one.
    heads = {}                                        # level -> text, most recent
    for i, line in enumerate(lines):
        lineno = offset + i + 1
        if _RX_FENCE.match(line):
            in_fence = not in_fence
            units.append({"unit_id": f"{slug}_unit_{lineno:06d}", "line": lineno,
                          "kind": "fence", "normative": False, "text": line.strip()})
            continue
        if in_fence:
            units.append({"unit_id": f"{slug}_unit_{lineno:06d}", "line": lineno,
                          "kind": "code", "normative": False, "text": line.strip()})
            continue
        kind, normative = classify_line(line)
        m = _RX_HEAD.match(line)
        if m:
            lvl = len(m.group(1))
            heads[lvl] = m.group(2).strip()
            for deeper in [k for k in heads if k > lvl]:   # a new H2 invalidates old H3s
                del heads[deeper]
        path = [heads[k] for k in sorted(heads)]
        units.append({"unit_id": f"{slug}_unit_{lineno:06d}", "line": lineno,
                      "kind": kind, "normative": normative, "text": line.strip(),
                      "heading": path[-1] if path else None,
                      "heading_path": path})
    return units


def denominator(units):
    return [u for u in units if u["normative"]]


# ---------------------------------------------------------------- self-test

_FIXTURE = """## Phase 2 — Connect the Dots

Some ordinary prose that merely describes the phase and asks nothing of anyone.

- generate the round's leveraged questions from the pad, biggest-first
- capture the delta this round

The session must not name the Win before Phase 3.

**Questions are numbered.**

| col | col |
|---|---|
| a | b |

```
must never always   # inside a fence — not a requirement
```

### A sub-heading that mentions must but is a heading

1. the first numbered step
2. the second numbered step
"""


def selftest():
    ok = True

    def report(label, passed, detail=""):
        nonlocal ok
        ok = ok and passed
        print(f"  [{'PASS' if passed else 'FAIL'}] {label}{(' -- ' + detail) if detail else ''}")

    print("spec_units --selftest")

    units = scan(_FIXTURE, slug="fx")
    den = denominator(units)
    kinds = {u["kind"] for u in den}

    # the known-good: every real requirement in the fixture is counted
    texts = " | ".join(u["text"] for u in den)
    report("counts bulleted requirements", "leveraged questions" in texts and "capture the delta" in texts)
    report("counts a numbered step", "the first numbered step" in texts)
    report("counts a modal sentence outside any list", "must not name the Win" in texts)
    report("counts a bolded directive line", "Questions are numbered" in texts)
    # 6 = 2 bullets + 2 numbered steps + 1 modal sentence + 1 bold directive.
    # Deliberately excluded: the heading that contains "must", the table rows, and the
    # fenced block whose modals are inert.
    report("denominator is exactly the 6 real requirements", len(den) == 6, f"got {len(den)}: {sorted(kinds)}")

    # the known-bad direction: structure must NOT inflate or hide
    report("headings are NOT counted (even when they contain a modal)",
           not any(u["kind"] == "heading" for u in den))
    report("table rows are NOT counted", not any(u["kind"] == "table" for u in den))
    report("a fenced code block is NOT counted (modals inside are inert)",
           not any(u["kind"] in ("code", "fence") for u in den))
    report("plain descriptive prose is NOT counted", "ordinary prose" not in texts)

    # nothing is silently discarded — every line is still returned for audit
    report("every line is returned, not just the normative ones",
           len(units) == len(_FIXTURE.splitlines()), f"{len(units)} vs {len(_FIXTURE.splitlines())}")

    # THE DANGEROUS DIRECTION: a missed requirement shrinks the denominator invisibly
    hidden = "the clerk must read back every row before marking it complete"
    report("an unusually-shaped requirement is still CAUGHT (under-count is the danger)",
           len(denominator(scan(f"prose prose.\n\n{hidden}\n", slug="fx"))) == 1)

    # ids are stable and citation-shaped
    a = [u["unit_id"] for u in scan(_FIXTURE, slug="fx")]
    b = [u["unit_id"] for u in scan(_FIXTURE, slug="fx")]
    report("ids are reproducible byte-for-byte across runs", a == b)
    uid = den[0]["unit_id"]
    report("ids survive the completeness_receipt id heuristic (>=12 chars, lowercase)",
           len(uid) >= 12 and uid.islower() and re.fullmatch(r"[a-z0-9_]+", uid) is not None, uid)

    # section slicing
    two = _FIXTURE + "\n## Phase 3 — Prioritization\n\n- a phase 3 requirement\n"
    d2 = denominator(scan(two, slug="fx", section="Phase 3"))
    report("--section slices to one section", len(d2) == 1 and "phase 3 requirement" in d2[0]["text"])
    try:
        scan(two, slug="fx", section="Phase 9")
        report("raises when the section is absent (fail-closed)", False, "no raise")
    except LookupError:
        report("raises when the section is absent (fail-closed)", True)

    # CLI exit-code contract
    me = os.path.abspath(__file__)
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "spec.md")
        with open(p, "w") as fh:
            fh.write(_FIXTURE)
        rc = subprocess.run([sys.executable, me, "--spec", p], capture_output=True,
                            text=True).returncode
        report("CLI units found -> exit 0", rc == FOUND, f"got exit {rc}")
        e = os.path.join(td, "empty.md")
        with open(e, "w") as fh:
            fh.write("## Phase 1\n\njust description, nothing asked of anyone.\n")
        rc = subprocess.run([sys.executable, me, "--spec", e], capture_output=True,
                            text=True).returncode
        report("CLI zero normative units -> exit 1 (refuses a vacuous denominator)",
               rc == EMPTY, f"got exit {rc}")
        rc = subprocess.run([sys.executable, me, "--spec", os.path.join(td, "nope.md")],
                            capture_output=True, text=True).returncode
        report("CLI missing spec -> exit 2 (fail-closed)", rc == CANNOT_EVALUATE, f"got exit {rc}")

    # ── HEADING CONTEXT + THE SECTION GATE (2026-07-29) ──────────────────────────────
    # Fixture reproduces the REAL shape that caused the incident: an imperative-sounding
    # numbered item whose own sentence is indistinguishable from a rule, sitting under a
    # heading that disqualifies it. If the fixture were only the heading text, it would
    # test the regex and prove nothing about the WIRING.
    doc = ("# Spec\n"
           "## Phase 0\n"
           "- The runner must write the record.\n"          # REAL rule, keep
           "### What Phase 0 Requires That Isn't Built Yet\n"
           "1. HITL notes per thread (the storage system)\n"  # backlog, gate it
           "2. The map-agent pipeline itself\n"               # backlog, gate it
           "## Phase 1\n"
           "- Every write must be read back.\n")             # REAL rule again, keep
    u = scan(doc, slug="t")
    byline = {x["line"]: x for x in u}
    report("a clause carries its nearest heading", byline[3]["heading"] == "Phase 0",
           byline[3].get("heading"))
    report("...and the FULL ancestor path, not just the nearest",
           byline[5]["heading_path"] == ["Spec", "Phase 0",
                                         "What Phase 0 Requires That Isn't Built Yet"],
           str(byline[5].get("heading_path")))
    report("known-bad: a backlog item under an 'Isn't Built Yet' heading is flagged",
           non_normative_heading(byline[5]["heading_path"]) is not None)
    report("...and so is its sibling", non_normative_heading(byline[6]["heading_path"]))
    report("known-good: a REAL rule in the same document is NOT flagged",
           non_normative_heading(byline[3]["heading_path"]) is None)
    report("known-good: a deeper heading RESETS on the next same-or-higher one "
           "(Phase 1's rule is not still under Phase 0's backlog)",
           non_normative_heading(byline[8]["heading_path"]) is None,
           str(byline[8].get("heading_path")))
    report("the flagged clause's own TEXT looks like a rule — the heading is the only "
           "signal, which is why the judge could not have known",
           "must" not in byline[5]["text"].lower())
    report("'Open Question:' headings are caught too",
           non_normative_heading(["Open Question: Lens Structure"]) is not None)
    report("known-good: an ordinary heading is NOT caught",
           non_normative_heading(["Storage (LOCAL-PRIMARY)", "Phase 3"]) is None)

    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description="spec_units -- the mechanical denominator for a spec")
    ap.add_argument("--spec")
    ap.add_argument("--section", help="regex: scan only this heading's section")
    ap.add_argument("--slug", default="spec", help="id prefix (lowercase, no spaces)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--ids-only", action="store_true", help="print the denominator ids, one per line")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())
    if not args.spec:
        _die("--spec is required")
    if not os.path.isfile(args.spec):
        _die(f"spec not found: {args.spec!r}")
    if not re.fullmatch(r"[a-z0-9_]+", args.slug):
        _die(f"--slug must be lowercase letters/digits/underscore (got {args.slug!r}) "
             f"so ids stay citation-shaped")

    text = open(args.spec, encoding="utf-8").read()
    try:
        units = scan(text, slug=args.slug, section=args.section)
    except LookupError as e:
        _die(str(e))

    den = denominator(units)
    if args.ids_only:
        for u in den:
            print(u["unit_id"])
    elif args.json:
        print(json.dumps({"spec": os.path.basename(args.spec), "section": args.section,
                          "slug": args.slug, "lines_scanned": len(units),
                          "denominator": len(den), "units": units}, indent=2, ensure_ascii=False))
    else:
        by_kind = {}
        for u in den:
            by_kind[u["kind"]] = by_kind.get(u["kind"], 0) + 1
        print(f"spec_units — {os.path.basename(args.spec)}"
              + (f" § {args.section}" if args.section else ""))
        print(f"  lines scanned:            {len(units)}")
        print(f"  DENOMINATOR (normative):  {len(den)}")
        for k, n in sorted(by_kind.items(), key=lambda x: -x[1]):
            print(f"      {k:<16} {n}")
        if not den:
            print("  ZERO normative units — refusing to hand downstream a vacuous denominator.")
    sys.exit(FOUND if den else EMPTY)


if __name__ == "__main__":
    main()

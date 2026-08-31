#!/usr/bin/env python3
"""map_carry_receipt — every finding written into a Map must reach the scratchpad, or be
  explicitly declared dropped.  [Parts Library]

WHEN: a skill maintains a Map (or similar findings ledger) that feeds a scratchpad or later
      phase -- checking the hand-off at that specific seam, after the Map is written and
      before/while the scratchpad is built from it.

WHAT: extracts every finding from the Map, then checks each one against the scratchpad:
        CARRIED          the finding's id (or, for text-derived ids, a real chunk of its
                          own text) appears in the scratchpad -- it made the crossing.
        DECLARED-DROPPED the scratchpad explicitly says `DROPPED: <that finding>` -- someone
                          made a conscious call to leave it out, on the record.
        LOST              neither -- the finding vanished at the hand-off with no trace and
                          no explanation. This is the failure this part exists to catch.

⛔ DOES NOT JUDGE WHETHER A CARRIED FINDING WAS ACTED ON. Reaching the scratchpad is the
      entire claim -- this part has nothing to say about whether the finding was then used
      well, ignored in spirit while nominally quoted, or acted on correctly. That is a
      downstream judgment call for a human or a different check, not a mechanical presence
      test. Conflating "it's in the scratchpad" with "it was handled" is a scope error this
      part deliberately does not make.

FINDING FORMATS RECOGNIZED IN THE MAP (support both; a Map may mix them):
  `- [F<digits>] <text>`   the id IS `F<digits>` (e.g. `[F12]` -> id `F12`), verbatim.
  `- FINDING: <text>`      no native id exists, so the id is a normalized slug built from
                           the first 60 characters of `<text>` (lowercased, non-alphanumeric
                           runs collapsed to single hyphens, trimmed) -- stable across runs
                           on the same text, but NOT a native identifier the scratchpad could
                           be expected to echo verbatim.

MATCHING RULES:
  F<digits> finding   CARRIED if `F<digits>` appears in the scratchpad as a whole token
                      (word-bounded, so `F1` never matches inside `F12`).
                      DECLARED-DROPPED if the scratchpad contains `DROPPED:` followed
                      (allowing whitespace) by that same `F<digits>` token.
  FINDING: (slug) finding   CARRIED if a VERBATIM prefix of at least 30 characters of the
                      finding's own text (taken from the Map, not the slug) appears anywhere
                      in the scratchpad. DECLARED-DROPPED if the scratchpad contains
                      `DROPPED:` followed (allowing whitespace) by that same verbatim prefix.
                      A finding whose own text is under 30 characters uses its full
                      (shorter) text as the prefix -- still required to be that exact,
                      verbatim substring, never a fuzzy match.

ZERO FINDINGS is a legitimate, NAMED outcome, not silently folded into a pass with nothing
      said: prints `NO-FINDINGS` and exits 0.

USAGE
  map_carry_receipt.py --map M.md --scratchpad S.md [--json]
  map_carry_receipt.py --selftest

EXIT CODES (the part contract)
  0  CARRIED (or NO-FINDINGS)  -- every finding in the Map is either carried into the
                                  scratchpad or explicitly declared dropped there; or the
                                  Map has no findings at all (named, not silently passed)
  1  LOST      -- at least one finding is neither carried nor declared dropped
  2  CANNOT EVALUATE -- missing/unreadable/unparsable map or scratchpad file. ABSENT-SUBJECT:
                        never folded into a pass or an ordinary violation.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

CARRIED, LOST, CANNOT_EVALUATE = 0, 1, 2

SLUG_ID_CHARS = 60       # basis for the slug id computed from FINDING: text
CARRY_PREFIX_CHARS = 30  # minimum verbatim excerpt required for a slug-id CARRIED match

_RX_FID = re.compile(r"^\s*-\s*\[F(\d+)\]\s*(.*)$", re.MULTILINE)
_RX_FINDING = re.compile(r"^\s*-\s*FINDING:\s*(.*)$", re.MULTILINE)


def _die(msg):
    print(f"CANNOT EVALUATE: {msg}", file=sys.stderr)
    sys.exit(CANNOT_EVALUATE)


def _slugify(text):
    s = text.strip().lower()[:SLUG_ID_CHARS]
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "empty"


# ---------------------------------------------------------------- extraction

def extract_findings(map_text):
    """Return a list of {"id", "kind", "text", "line"} in document order.

    Both formats are collected and then sorted by their position in the Map, so a mixed
    Map reports findings in the order a human reading it would encounter them.
    """
    findings = []
    for m in _RX_FID.finditer(map_text):
        n, text = m.group(1), m.group(2).strip()
        findings.append({"id": f"F{n}", "kind": "fid", "text": text,
                         "line": map_text.count("\n", 0, m.start()) + 1})
    for m in _RX_FINDING.finditer(map_text):
        text = m.group(1).strip()
        findings.append({"id": _slugify(text), "kind": "slug", "text": text,
                         "line": map_text.count("\n", 0, m.start()) + 1})
    findings.sort(key=lambda f: f["line"])
    return findings


def _carry_prefix(text):
    t = text.strip()
    return t[:CARRY_PREFIX_CHARS] if len(t) >= CARRY_PREFIX_CHARS else t


# ---------------------------------------------------------------- classification

def classify(finding, scratchpad_text):
    """Return (verdict, detail) for one finding -- CARRIED / DECLARED-DROPPED / LOST."""
    if finding["kind"] == "fid":
        token_rx = re.compile(rf"\b{re.escape(finding['id'])}\b")
        dropped_rx = re.compile(rf"DROPPED:\s*{re.escape(finding['id'])}\b", re.IGNORECASE)
        if dropped_rx.search(scratchpad_text):
            return "DECLARED-DROPPED", f"scratchpad declares 'DROPPED: {finding['id']}'"
        if token_rx.search(scratchpad_text):
            return "CARRIED", f"id {finding['id']!r} found in the scratchpad"
        return "LOST", f"id {finding['id']!r} appears neither carried nor declared dropped"

    prefix = _carry_prefix(finding["text"])
    if not prefix:
        return "LOST", "finding has no text to match against (empty)"
    dropped_rx = re.compile(r"DROPPED:\s*" + re.escape(prefix), re.IGNORECASE)
    if dropped_rx.search(scratchpad_text):
        return "DECLARED-DROPPED", f"scratchpad declares 'DROPPED: {prefix[:40]!r}...'"
    if prefix in scratchpad_text:
        return "CARRIED", f"verbatim prefix ({len(prefix)} chars) found in the scratchpad"
    return "LOST", (f"no verbatim >= {CARRY_PREFIX_CHARS}-char prefix of this finding's "
                    f"text found in the scratchpad, and no DROPPED declaration for it")


def evaluate(map_text, scratchpad_text):
    findings = extract_findings(map_text)
    if not findings:
        return {"verdict": "NO-FINDINGS", "findings": [], "lost": [], "exit": CARRIED}

    results = []
    for f in findings:
        verdict, detail = classify(f, scratchpad_text)
        results.append({"id": f["id"], "kind": f["kind"], "line": f["line"],
                        "text": f["text"][:100], "verdict": verdict, "detail": detail})

    lost = [r for r in results if r["verdict"] == "LOST"]
    overall = "LOST" if lost else "CARRIED"
    return {"verdict": overall, "findings": results, "lost": [r["id"] for r in lost],
            "exit": LOST if lost else CARRIED}


def render(v):
    if v["verdict"] == "NO-FINDINGS":
        return ("map_carry_receipt -- NO-FINDINGS\n"
                "  the Map contains no `- [F<n>]` or `- FINDING:` lines -- a legitimate "
                "but explicitly named outcome, not a silent pass.")
    out = [f"map_carry_receipt -- {v['verdict']} "
           f"({len(v['findings'])} finding(s), {len(v['lost'])} LOST)"]
    for r in v["findings"]:
        out.append(f"  [{r['verdict']}] {r['id']} (Map line {r['line']}) -- {r['text']!r}")
        out.append(f"      {r['detail']}")
    return "\n".join(out)


# ---------------------------------------------------------------- self-test

_MAP = """# Findings Map

- [F1] auth token expiry not handled on retry
- [F2] duplicate webhook delivery under load
- [F3] this finding is never mentioned again anywhere
- FINDING: the nightly export silently drops rows whose timestamp lands exactly on a DST
  boundary, which nobody noticed because the row count check only compares totals
- FINDING: this second free-text finding also just vanishes without a trace or a note
"""

# known-good scratchpad: F1 carried, F2 explicitly dropped, F3 explicitly dropped; the
# free-text finding is carried by its own verbatim prefix, the second free-text finding
# is explicitly dropped.
_SLUG_TEXT = ("the nightly export silently drops rows whose timestamp lands exactly on a "
              "DST boundary, which nobody noticed because the row count check only "
              "compares totals")
_SLUG_ID = _slugify(_SLUG_TEXT)
_SLUG2_TEXT = "this second free-text finding also just vanishes without a trace or a note"

_GOOD_SCRATCHPAD = f"""# Scratchpad

Carried forward: F1 (auth token retry issue) is being actioned this sprint.
DROPPED: F2 -- accepted risk, webhook consumer is already idempotent.
DROPPED: F3 -- duplicate of an earlier finding, no new action.

Also carrying: {_SLUG_TEXT[:CARRY_PREFIX_CHARS]} -- flagged for the data team.

DROPPED: {_SLUG2_TEXT[:CARRY_PREFIX_CHARS]}
"""

# known-bad: F3 and the un-dropped free-text finding are both silently missing
_BAD_SCRATCHPAD = """# Scratchpad

Carried forward: F1 (auth token retry issue) is being actioned this sprint.
DROPPED: F2 -- accepted risk, webhook consumer is already idempotent.
"""

_NO_FINDINGS_MAP = """# Findings Map

Nothing found this pass.
"""


def selftest():
    ok = True

    def report(label, passed, detail=""):
        nonlocal ok
        ok = ok and passed
        print(f"  [{'PASS' if passed else 'FAIL'}] {label}{(' -- ' + detail) if detail else ''}")

    print("map_carry_receipt --selftest")

    # extraction
    findings = extract_findings(_MAP)
    report("extracts both [F<n>] and FINDING: formats from a mixed Map",
           len(findings) == 5, f"got {len(findings)}")
    report("[F<n>] id is the literal token", findings[0]["id"] == "F1")
    report("FINDING: id is a normalized slug of the first 60 chars",
           findings[3]["id"] == _SLUG_ID, findings[3]["id"])

    # known-bad: F3 and the second free-text finding are LOST
    v = evaluate(_MAP, _BAD_SCRATCHPAD)
    report("known-bad: silently-vanished findings are LOST -> overall LOST, exit 1",
           v["verdict"] == "LOST" and v["exit"] == LOST)
    report("F3 (never mentioned) is named as LOST", "F3" in v["lost"])
    slug2_id = _slugify(_SLUG2_TEXT)
    report("the un-dropped free-text finding is named as LOST",
           slug2_id in v["lost"], str(v["lost"]))
    report("F1 (carried) is NOT in the lost list", "F1" not in v["lost"])
    report("F2 (declared dropped) is NOT in the lost list", "F2" not in v["lost"])

    # known-good: everything carried or declared dropped
    v = evaluate(_MAP, _GOOD_SCRATCHPAD)
    report("known-good: every finding carried or declared dropped -> CARRIED, exit 0",
           v["verdict"] == "CARRIED" and v["exit"] == CARRIED, str(v["lost"]))
    kinds = {r["id"]: r["verdict"] for r in v["findings"]}
    report("F1 classified CARRIED", kinds["F1"] == "CARRIED")
    report("F2 classified DECLARED-DROPPED", kinds["F2"] == "DECLARED-DROPPED")
    report("the free-text finding classified CARRIED via verbatim prefix",
           kinds[_SLUG_ID] == "CARRIED")
    report("the second free-text finding classified DECLARED-DROPPED",
           kinds[slug2_id] == "DECLARED-DROPPED")

    # word-boundary discipline: F1 must not match inside F12
    wb_map = "- [F1] short finding\n"
    wb_pad = "we discussed F12 today but not F1 itself... wait yes: F1 is here too\n"
    report("word boundaries hold (F1 does not match inside F12)",
           evaluate(wb_map, "only F12 mentioned, never the real token")["verdict"] == "LOST")
    report("...and a real standalone token match still counts as CARRIED",
           evaluate(wb_map, wb_pad)["verdict"] == "CARRIED")

    # NO-FINDINGS is named, not a silent pass
    v = evaluate(_NO_FINDINGS_MAP, "anything")
    report("zero findings in the Map -> NO-FINDINGS, exit 0, explicitly named",
           v["verdict"] == "NO-FINDINGS" and v["exit"] == CARRIED)

    # a finding shorter than the prefix length still requires its (shorter) full text
    short_map = "- FINDING: too short\n"
    short_id = _slugify("too short")
    v_carried = evaluate(short_map, "note: too short was seen and carried forward")
    v_lost = evaluate(short_map, "nothing relevant mentioned here at all")
    report("a finding shorter than the prefix length is still matched on its full "
           "(shorter) verbatim text",
           v_carried["findings"][0]["verdict"] == "CARRIED"
           and v_lost["findings"][0]["verdict"] == "LOST")

    # CLI end-to-end, proving the exit-code contract
    me = os.path.abspath(__file__)
    with tempfile.TemporaryDirectory() as td:
        mp = os.path.join(td, "map.md")
        with open(mp, "w", encoding="utf-8") as fh:
            fh.write(_MAP)
        bp = os.path.join(td, "bad_pad.md")
        with open(bp, "w", encoding="utf-8") as fh:
            fh.write(_BAD_SCRATCHPAD)
        gp = os.path.join(td, "good_pad.md")
        with open(gp, "w", encoding="utf-8") as fh:
            fh.write(_GOOD_SCRATCHPAD)

        rc = subprocess.run([sys.executable, me, "--map", mp, "--scratchpad", bp],
                            capture_output=True, text=True).returncode
        report("CLI known-bad -> exit 1", rc == LOST, f"got exit {rc}")
        rc = subprocess.run([sys.executable, me, "--map", mp, "--scratchpad", gp],
                            capture_output=True, text=True).returncode
        report("CLI known-good -> exit 0", rc == CARRIED, f"got exit {rc}")

        rc = subprocess.run([sys.executable, me, "--map", os.path.join(td, "nope.md"),
                             "--scratchpad", gp], capture_output=True, text=True).returncode
        report("CLI missing map -> exit 2 (fail-closed, ABSENT-SUBJECT)",
               rc == CANNOT_EVALUATE, f"got exit {rc}")
        rc = subprocess.run([sys.executable, me, "--map", mp,
                             "--scratchpad", os.path.join(td, "nope.md")],
                            capture_output=True, text=True).returncode
        report("CLI missing scratchpad -> exit 2 (fail-closed, ABSENT-SUBJECT)",
               rc == CANNOT_EVALUATE, f"got exit {rc}")

        nfp = os.path.join(td, "nofindings.md")
        with open(nfp, "w", encoding="utf-8") as fh:
            fh.write(_NO_FINDINGS_MAP)
        rc = subprocess.run([sys.executable, me, "--map", nfp, "--scratchpad", gp],
                            capture_output=True, text=True).returncode
        report("CLI NO-FINDINGS -> exit 0", rc == CARRIED, f"got exit {rc}")

        p = subprocess.run([sys.executable, me, "--map", mp, "--scratchpad", gp, "--json"],
                           capture_output=True, text=True)
        try:
            payload = json.loads(p.stdout)
            json_ok = payload.get("verdict") == "CARRIED"
        except json.JSONDecodeError:
            json_ok = False
        report("CLI --json emits a parseable verdict", json_ok, p.stdout[:150])

    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(
        description="map_carry_receipt -- every finding written into a Map must reach the "
                     "scratchpad, or be explicitly declared dropped")
    ap.add_argument("--map")
    ap.add_argument("--scratchpad")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())
    if not args.map or not args.scratchpad:
        _die("--map and --scratchpad are required")
    for p, what in ((args.map, "map"), (args.scratchpad, "scratchpad")):
        if not os.path.isfile(p):
            _die(f"{what} not found: {p!r}")

    try:
        map_text = open(args.map, encoding="utf-8").read()
    except (OSError, UnicodeDecodeError) as e:
        _die(f"map could not be read: {e}")
    try:
        scratchpad_text = open(args.scratchpad, encoding="utf-8").read()
    except (OSError, UnicodeDecodeError) as e:
        _die(f"scratchpad could not be read: {e}")

    v = evaluate(map_text, scratchpad_text)

    if args.json:
        print(json.dumps(v, indent=2, ensure_ascii=False))
    else:
        print(render(v))

    sys.exit(v["exit"])


if __name__ == "__main__":
    main()

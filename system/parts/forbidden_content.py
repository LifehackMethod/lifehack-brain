#!/usr/bin/env python3
"""forbidden_content — the "do NOT yet" checker.  [Parts Library · Tier A · A2]

WHEN: a phase must WITHHOLD something (a conclusion, a ranking, an answer) until later.
WHAT: checks a block of text for a forbidden artifact; nonzero refuses.
WHY:  cal-weekly named the Win in Phase 2 against an explicit do-NOT, on real data [M].
      Withholding is the demand-class prose holds worst (SOP §II.7).

THE CORE DISTINCTION THIS PART EXISTS TO DRAW — declaration vs mention.
    "Win (Wren-authored): Fully Day-1 ready"        <- NAMING the Win        (violation)
    "...these live inside the Win as actions"        <- MENTIONING the Win    (fine)
A bare keyword grep cannot tell these apart, and firing on the second is how a guard
becomes noise and gets switched off.  (build-sop: "a guard that greps for a keyword
false-positives on mere MENTIONS ... test it against benign text that names the token.")

MODES
  declaration  the term appears as a labelled assignment at the start of a line --
               optional bullet/heading marker, optional bold, TERM, a short label tail,
               a colon, then content.  This is "the thing is being NAMED here."
  mention      any word-boundary occurrence of the term.  Use when even raising the
               subject is forbidden.
  regex        an explicit pattern, for anything the two shapes above don't cover.

KNOWN BOUND (stated, not hidden): `declaration` does NOT catch a heading-plus-list form
("### Ranked Win" followed by a numbered list).  It catches labelled assignment only.
If a skill names things that way, add a `regex` rule for it -- do not assume coverage.

USAGE
  forbidden_content.py --rules RULES.json --text-file BLOCK.md   [--json]
  cat block.md | forbidden_content.py --rules RULES.json --stdin  [--json]
  forbidden_content.py --selftest

EXIT CODES (the part contract)
  0  clean       -- no forbidden content found
  1  REFUSED     -- forbidden content found; reasons printed
  2  CANNOT EVALUATE -- missing/unreadable rules or text, bad rule shape.  Fail-closed:
                       an un-evaluable check NEVER reports clean.

RULES FILE — a JSON list:
  [ {"id": "win-named-early",
     "term": "Win",
     "mode": "declaration",
     "why": "spec: the Win is named in Phase 3, never before"} ]
  optional per rule: "label_chars" (declaration tail budget, default 40),
                     "pattern" (required when mode == "regex"),
                     "flags": ["i"] for case-insensitive.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

CLEAN, REFUSED, CANNOT_EVALUATE = 0, 1, 2


def _die(msg):
    print(f"CANNOT EVALUATE: {msg}", file=sys.stderr)
    sys.exit(CANNOT_EVALUATE)


def build_matcher(rule):
    """Turn one rule dict into a compiled regex. Raises ValueError on a bad rule."""
    if not isinstance(rule, dict):
        raise ValueError(f"rule is not an object: {rule!r}")
    rid = rule.get("id")
    if not rid:
        raise ValueError(f"rule missing 'id': {rule!r}")
    mode = rule.get("mode", "declaration")
    flags = re.MULTILINE
    # An UNRECOGNISED flag used to be silently ignored -- so a "flags": ["I"] typo
    # (capital i) left the rule case-SENSITIVE and it reported CLEAN on exactly the
    # content it was written to catch.  A fail-OPEN, measured 2026-08-05.  Validate
    # instead: a rule that cannot do what its author asked must refuse to evaluate.
    declared = rule.get("flags", [])
    if not isinstance(declared, list):
        raise ValueError(
            f"rule {rid!r}: 'flags' must be a list, got {type(declared).__name__}")
    unknown = [f for f in declared if f != "i"]
    if unknown:
        raise ValueError(
            f"rule {rid!r}: unknown flag(s) {unknown!r} -- only 'i' is supported "
            f"(lower-case). A silently-ignored flag makes the rule behave differently "
            f"from its author's intent and can report CLEAN on content it should catch.")
    if "i" in declared:
        flags |= re.IGNORECASE

    if mode == "regex":
        pat = rule.get("pattern")
        if not pat:
            raise ValueError(f"rule {rid!r}: mode 'regex' requires 'pattern'")
        # re.error is NOT a ValueError, so an invalid pattern used to escape main()'s
        # handler and exit via Python's default = exit 1, colliding with REFUSED.
        try:
            return rid, re.compile(pat, flags)
        except re.error as e:
            raise ValueError(f"rule {rid!r}: invalid regex {pat!r}: {e}")

    term = rule.get("term")
    if not term:
        raise ValueError(f"rule {rid!r}: mode {mode!r} requires 'term'")
    if not isinstance(term, str):
        # re.escape() on a non-str raises TypeError, which is likewise not a ValueError.
        raise ValueError(
            f"rule {rid!r}: 'term' must be a string, got {type(term).__name__}")
    t = re.escape(term)

    if mode == "mention":
        return rid, re.compile(rf"\b{t}\b", flags)

    if mode == "declaration":
        n = int(rule.get("label_chars", 40))
        # start-of-line, optional bullet OR heading marker, optional bold/emphasis,
        # the term, a short label tail with no colon in it, then ': ' and real content.
        pat = rf"^[ \t]*(?:[-*+>]+|#{{1,6}})?[ \t]*\*{{0,3}}[ \t]*{t}\b[^:\n]{{0,{n}}}:[ \t]*\S"
        return rid, re.compile(pat, flags)

    raise ValueError(f"rule {rid!r}: unknown mode {mode!r}")


def check(text, rules):
    """Return a list of hit dicts. Raises ValueError on a bad rule (-> fail closed)."""
    hits = []
    for rule in rules:
        rid, rx = build_matcher(rule)
        m = rx.search(text)
        if m:
            line_no = text.count("\n", 0, m.start()) + 1
            line = text.splitlines()[line_no - 1].strip()
            hits.append({
                "id": rid,
                "mode": rule.get("mode", "declaration"),
                "why": rule.get("why", ""),
                "line": line_no,
                "evidence": line[:200],
            })
    return hits


def _load(path, what):
    if not path or not os.path.isfile(path):
        _die(f"{what} not found: {path!r}")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except UnicodeDecodeError as e:
        # A binary / non-UTF8 file used to raise this uncaught -> Python's default
        # exit 1, indistinguishable from a genuine REFUSED verdict and with no JSON
        # on stdout to tell them apart.  It is a CANNOT EVALUATE, not a refusal.
        _die(f"{what} {path!r} is not valid UTF-8 (binary?): {e}")
    except OSError as e:
        _die(f"cannot read {what} {path!r}: {e}")


# ---------------------------------------------------------------- self-test

# Two-sided, and deliberately built from the REAL W30 shapes so the known-good is the
# exact false-positive that would make this part untrustworthy.
# ⚠ NOBODY REAL IS IN THIS FIXTURE — every name in it ("Wren", "Fern") is invented,
# in the style of system/shipping-lane/fixtures/identity-fixture.md.
_BAD = """## Phase 2 - Connect the Dots

### Connected picture:
- Win (Wren-authored): Fully Day-1 ready - paperwork confirmed, pay-split confirmed
- Bonus aim: Heat-pump fix through Fern
"""

_GOOD = """## Phase 2 - Connect the Dots

### Carried-forward gaps (these live inside the Win as actions, not answered)
- gap: Start paperwork / health affidavit - carries into Win as "confirm returned"
- gap: Pay split - no follow-up since July 20; carries into Win as "push accounting"
"""

_RULES = [{"id": "win-named-early", "term": "Win", "mode": "declaration",
           "why": "spec: the Win is named in Phase 3, never before"}]


def selftest():
    ok = True

    def report(label, passed, detail=""):
        nonlocal ok
        ok = ok and passed
        print(f"  [{'PASS' if passed else 'FAIL'}] {label}{(' -- ' + detail) if detail else ''}")

    print("forbidden_content --selftest")

    hits = check(_BAD, _RULES)
    report("catches a known-bad (Win DECLARED in Phase 2)",
           len(hits) == 1 and hits[0]["id"] == "win-named-early",
           f"{len(hits)} hit(s)")

    hits = check(_GOOD, _RULES)
    report("passes a known-good (Win MENTIONED, not declared)",
           hits == [], f"{len(hits)} false hit(s): {hits}")

    # bold / heading variants of the same violation must still be caught
    for variant in ("- **Win:** Fully Day-1 ready",
                    "**Win (Wren-authored):** Fully Day-1 ready",
                    "## Win: Fully Day-1 ready",
                    "Win: Fully Day-1 ready"):
        report(f"catches variant {variant!r}", len(check(variant, _RULES)) == 1)

    # benign shapes that must NOT fire
    for variant in ("The Win will be chosen in Phase 3.",
                    "- ranked later; carries into Win as an action",
                    "Winter planning: not related to the Win at all"):
        report(f"no false positive on {variant!r}", check(variant, _RULES) == [])

    report("mention mode DOES fire where declaration mode does not",
           len(check("carries into Win as an action",
                     [{"id": "m", "term": "Win", "mode": "mention"}])) == 1)

    # fail-closed on a malformed rule
    try:
        check(_BAD, [{"id": "broken", "mode": "regex"}])
        report("raises on a malformed rule (fail-closed)", False, "no exception")
    except ValueError:
        report("raises on a malformed rule (fail-closed)", True)

    # end-to-end through the real CLI, so the exit-code contract itself is proven
    with tempfile.TemporaryDirectory() as td:
        rp = os.path.join(td, "rules.json")
        with open(rp, "w") as fh:
            json.dump(_RULES, fh)
        for label, body, want in (("CLI known-bad -> exit 1", _BAD, REFUSED),
                                  ("CLI known-good -> exit 0", _GOOD, CLEAN)):
            tp = os.path.join(td, "block.md")
            with open(tp, "w") as fh:
                fh.write(body)
            rc = subprocess.run(
                [sys.executable, os.path.abspath(__file__), "--rules", rp, "--text-file", tp],
                capture_output=True, text=True).returncode
            report(label, rc == want, f"got exit {rc}")
        rc = subprocess.run(
            [sys.executable, os.path.abspath(__file__), "--rules", rp,
             "--text-file", os.path.join(td, "nope.md")],
            capture_output=True, text=True).returncode
        report("CLI missing text -> exit 2 (fail-closed)", rc == CANNOT_EVALUATE, f"got exit {rc}")

    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description="forbidden_content -- the 'do NOT yet' checker")
    ap.add_argument("--rules", help="JSON file: list of rule objects")
    ap.add_argument("--text-file", help="file holding the block of text to check")
    ap.add_argument("--stdin", action="store_true", help="read the text from stdin")
    ap.add_argument("--json", action="store_true", help="emit a JSON verdict")
    ap.add_argument("--selftest", action="store_true", help="run the two-sided self-test")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())

    if not args.rules:
        _die("--rules is required")
    raw = _load(args.rules, "rules file")
    try:
        rules = json.loads(raw)
    except json.JSONDecodeError as e:
        _die(f"rules file is not valid JSON: {e}")
    if not isinstance(rules, list):
        _die("rules file must contain a JSON list")

    if args.stdin:
        text = sys.stdin.read()
    elif args.text_file:
        text = _load(args.text_file, "text file")
    else:
        _die("one of --text-file or --stdin is required")

    try:
        hits = check(text, rules)
    except ValueError as e:
        _die(str(e))

    if args.json:
        print(json.dumps({"verdict": "REFUSED" if hits else "CLEAN", "hits": hits}, indent=2))
    elif hits:
        print(f"REFUSED -- {len(hits)} forbidden item(s) present:")
        for h in hits:
            print(f"  - [{h['id']}] line {h['line']}: {h['evidence']}")
            if h["why"]:
                print(f"      why: {h['why']}")
    else:
        print(f"CLEAN -- none of the {len(rules)} forbidden item(s) present")

    sys.exit(REFUSED if hits else CLEAN)


if __name__ == "__main__":
    main()

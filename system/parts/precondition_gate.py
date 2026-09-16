#!/usr/bin/env python3
"""precondition_gate — a consequent marker may not stand until its antecedent artifact
(with declared substance) already exists in the same document.  [Parts Library · enforcement]

WHEN: a spec says "X may not be recorded/locked/named until Y's artifact is present" —
      two markers in ONE document, where the obligation is genuinely about EXISTENCE
      ("has Y run at all"), not about which one comes first on the page. Read the HONEST
      BOUND below before reaching for this over order_lint — they are not interchangeable.

WHAT: locate the consequent (the thing being gated, e.g. "the Win locked"). If it never
      appears, there is nothing to gate yet — NOT_APPLICABLE. If it does appear, locate the
      antecedent (e.g. the look-back's own section marker). Missing entirely ->
      ANTECEDENT_MISSING. Present but hollow — the marker is there, its declared substance
      is not — -> ANTECEDENT_INCOMPLETE (SOP §V.4b: a gate verifies evidence of work, never
      the form of a claim; a bare heading is not a look-back). Both real -> SATISFIED.

WHY:  cal-weekly's W30 run locked the user's Win in Phase 1 before the look-back had run;
      Enver caught it live — "lock it. but i haven't done the lookback yet right?".
      `skills/cal-weekly/prompts/01-orientation.md:24` and `02-connect-the-dots.md:42`
      ALREADY prohibited naming the Win early, in prose, and the run violated both anyway.
      That is Law 2 link 2 (FILE -> FIRED, a compliance loss, not an authoring loss) and
      textbook Law 4.2 knows-but-violates (measured 8–99% of the time a model accurately
      restates a rule it is simultaneously breaking). SOP §III.9's FAIL-TWICE rule: a rule
      that breaks twice needs a different RUNG, not a third sentence asking nicely — so
      this is code that can REFUSE, not prose.

⛔ HONEST BOUND — READ BEFORE TRUSTING THIS FOR "ORDER". VERIFIED THIS SESSION, not assumed:
      order_lint.py (the library's POSITIONAL tool — the obvious first reach for an
      "X before Y" rule) was run against the REAL, Enver-confirmed-compliant W30
      scratchpad (`weekly-2026-W30/session-scratchpad.md`, the one with a real
      HUMAN-VERIFIED look-back block AND a locked Win) with the rule
      before=LOOKBACK / after=Win. It returned:

          "verdict": "OUT_OF_ORDER", "before_at": 7396, "after_at": 235

      exit 1 — a FALSE REFUSAL of a run Enver personally confirmed was done right. Why:
      that scratchpad is a "living world model" (its own header: "pruned/updated every
      turn") laid out by a FIXED TOPIC TEMPLATE — Phase progress, ..., Monthly Win, ...,
      SCRATCHPAD log, LOOKBACK — not an append-only chronological log. The Win's template
      slot sits physically ABOVE the free-form look-back log REGARDLESS of which was
      actually written first. **Physical character position in this document is not a
      proxy for write order**, and no single static snapshot can recover write order from
      it — that needs an event log or a diff history, and this scratchpad carries neither.

      SO: this part deliberately does NOT compare positions — it is NOT a drop-in
      replacement for order_lint, it exists because order_lint is the wrong instrument for
      THIS document shape. It proves PRESENCE conditioned on the consequent (the antecedent
      is present-and-substantive whenever the consequent is present), never SEQUENCE.
      What it CATCHES: the antecedent's own artifact skipped entirely — the real W30
      defect, reproduced below by deleting the LOOKBACK section from the real fixture and
      watching this part refuse it (see --selftest, DIFFERENTIAL section).
      What it CANNOT catch: a same-turn race where the antecedent's marker was stubbed in
      cheaply, after the fact, purely to satisfy this check. `requires` (substance
      sub-elements) raises that bar per SOP §V.4b, but it is still text-in/text-out — it
      cannot prove WHEN the words were typed, only that they are there. If a rule genuinely
      needs sequence and not mere presence, order_lint may still be right for a document
      that IS append-only; this scratchpad is not that document.

MATCHING a marker: exactly one of "term" (a literal word/phrase, escaped, word-bounded —
      PREFER THIS) or "pattern" (a regex; use only when the thing is genuinely a pattern).
      Same discipline as order_lint / section_present, and for the same reason: a literal
      is the only form a mechanical probe can disguise-and-inject back at the rule.

⛔ DECLARED UNCHECKABLE -- `lookback-before-win` SPECIFICALLY, PROVEN UNFIXABLE (S8.8).
      This is the rule this part was BUILT for (the WHY above), and it is still the wrong
      answer for it on THIS document shape -- not because this part is broken, but because
      every mechanical axis a check could stand on is independently closed:
        BARE STRINGS -- satisfied by prose ABOUT the bug. A debugging note, a postmortem, or
          this very docstring's own worked example contains the literal words "LOOKBACK" and
          "HUMAN-VERIFIED" without a single real look-back having happened. `requires`
          sub-elements raise the bar from "the heading exists" to "the heading exists AND
          names its verification tag" -- and a hand-typed decoy clears that bar exactly as
          easily as a real one; text-in/text-out cannot tell a citation from a report.
        STRUCTURAL POSITION -- defeated by the identical property that made order_lint refuse
          the REAL compliant W30 run above: a FIXED-TOPIC LIVING TEMPLATE lays the LOOKBACK
          heading at its final template slot AT TURN ZERO, empty, before any phase has run --
          so "the heading is physically present" is true from the first character written and
          proves nothing about when (or whether) it was filled in.
        SEQUENCE -- disclaimed in this part's OWN WHAT/HONEST BOUND above: this part proves
          EXISTENCE conditioned on the consequent, never ORDER. It was built specifically
          because order_lint's sequence check is the wrong tool for this template; it does
          not become the right tool for proving sequence by elimination.
      All three axes closed is why this is DECLARED UNCHECKABLE rather than merely hard --
      "write a smarter check" is not an available move, because each smarter check trades one
      closed axis for another already-closed one. A previously proposed "repair" here would
      have flipped the rule to a permanent, silent PASS; that is the exact failure mode this
      declaration exists to head off -- a green light that cannot ever go red is worse than no
      light. This is a TERMINAL answer, not a TODO: the STOP-CHECK for `lookback-before-win`
      is now the HUMAN's -- read the look-back yourself before trusting a locked Win -- and
      `emit_gate.py` records that on the gate's own contract as its own STATUS
      (`DECLARED_UNCHECKABLE`), not a code comment nobody downstream ever reads.

USAGE
  precondition_gate.py --rules RULES.json --artifact A.md [--json]
  precondition_gate.py --selftest

EXIT CODES (the part contract)
  0  every rule SATISFIED or NOT_APPLICABLE
  1  REFUSED — at least one rule's antecedent is missing or incomplete while its
     consequent is present
  2  CANNOT EVALUATE — missing file, bad rules file. Fail-closed.

RULES FILE — a JSON list:
  [ {"id": "lookback-before-win",
     "consequent": {"id": "win", "pattern": "\\bWin\\b.{0,60}\\blocked\\b"},
     "antecedent": {"id": "lookback", "term": "LOOKBACK",
                    "requires": [{"id": "human-verified", "term": "HUMAN-VERIFIED"}]},
     "why": "the look-back's artifact must exist before the Win is recorded"} ]
  `requires` on the antecedent is optional — omit it (or leave it empty) for a bare-marker
  antecedent check with no substance obligation.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

SATISFIED, REFUSED, CANNOT_EVALUATE = 0, 1, 2


def _die(msg):
    print(f"CANNOT EVALUATE: {msg}", file=sys.stderr)
    sys.exit(CANNOT_EVALUATE)


def locate(text, spec):
    """Return the character offset of the first match for this marker, or None.

    Deliberately only "term" or "pattern" -- no "sequence" (order_lint's narrative-arc
    form) and no position comparison at all. This part asks "is it here," never "where."
    """
    if not isinstance(spec, dict) or not spec.get("id"):
        raise ValueError(f"marker needs an 'id': {spec!r}")
    flags = re.IGNORECASE | re.MULTILINE

    if "term" in spec:
        term = spec["term"]
        if not isinstance(term, str) or not term.strip():
            raise ValueError(f"marker {spec['id']!r} has an empty 'term'")
        m = re.compile(rf"\b{re.escape(term.strip())}\b", flags).search(text)
        return m.start() if m else None

    if "pattern" in spec:
        m = re.search(spec["pattern"], text, flags)
        return m.start() if m else None

    raise ValueError(f"marker {spec['id']!r} needs either 'term' or 'pattern'")


def check(text, rules):
    """Return a list of result dicts. Raises ValueError on a bad rule -> fail closed."""
    results = []
    for rule in rules:
        if not isinstance(rule, dict) or not rule.get("id"):
            raise ValueError(f"rule needs an 'id': {rule!r}")
        if "consequent" not in rule or "antecedent" not in rule:
            raise ValueError(f"rule {rule['id']!r} needs both 'consequent' and 'antecedent'")

        ante_spec = rule["antecedent"]
        if not isinstance(ante_spec, dict) or not ante_spec.get("id"):
            raise ValueError(f"rule {rule['id']!r}: 'antecedent' needs an 'id'")
        requires = ante_spec.get("requires") or []
        if not isinstance(requires, list):
            raise ValueError(f"rule {rule['id']!r}: antecedent 'requires' must be a list")
        # VALIDATE EVERY `requires` MARKER UP FRONT, BEFORE ANY ARTIFACT IS EVALUATED.
        # Why this is here and not left to `locate()`: `locate()` validates a marker only on the
        # path that actually calls it, and the ANTECEDENT_MISSING branch below never does -- it
        # reads `r.get("id", r)` straight off the raw spec. So a malformed marker (e.g. a bare
        # string instead of {"id":...,"pattern":...}) exited 2 CANNOT_EVALUATE on a COMPLIANT
        # artifact and CRASHED with AttributeError on a VIOLATING one -- and a Python traceback
        # exits 1, which is this part's REFUSED code. **A crash and a real refusal were
        # indistinguishable to the caller**, so a broken rules file would read as a skill
        # violation and send someone hunting a bug that does not exist. Fail-closed means
        # UNEVALUABLE must never wear REFUSED's exit code. (Found 2026-08-02 by running the
        # part's own published invocation with a malformed payload, not by reading it.)
        for r in requires:
            if not isinstance(r, dict) or not r.get("id"):
                raise ValueError(
                    f"rule {rule['id']!r}: every antecedent 'requires' marker needs an 'id': {r!r}")

        cons_at = locate(text, rule["consequent"])

        if cons_at is None:
            verdict = "NOT_APPLICABLE"
            ante_at = None
            missing_sub = []
        else:
            ante_at = locate(text, ante_spec)
            if ante_at is None:
                verdict = "ANTECEDENT_MISSING"
                missing_sub = [r.get("id", r) for r in requires]
            else:
                missing_sub = [r["id"] for r in requires if locate(text, r) is None]
                verdict = "ANTECEDENT_INCOMPLETE" if missing_sub else "SATISFIED"

        results.append({
            "id": rule["id"],
            "verdict": verdict,
            "why": rule.get("why", ""),
            "consequent_id": rule["consequent"].get("id"),
            "antecedent_id": ante_spec.get("id"),
            "consequent_at": cons_at,
            "antecedent_at": ante_at,
            "missing": missing_sub,
            "failed": verdict in ("ANTECEDENT_MISSING", "ANTECEDENT_INCOMPLETE"),
        })
    return results


def render(results):
    out = []
    for r in results:
        out.append(f"  [{r['verdict']}] {r['id']}")
        if r["verdict"] == "NOT_APPLICABLE":
            out.append(f"      {r['consequent_id']!r} never appears -- nothing to gate yet "
                       f"(vacuous pass, not a check that ran)")
        elif r["verdict"] == "ANTECEDENT_MISSING":
            out.append(f"      {r['consequent_id']!r} is present but {r['antecedent_id']!r} "
                       f"never appears -- its own artifact was skipped entirely")
        elif r["verdict"] == "ANTECEDENT_INCOMPLETE":
            out.append(f"      {r['antecedent_id']!r} is present but hollow -- missing: "
                       f"{', '.join(str(m) for m in r['missing'])}")
        if r["why"] and r["failed"]:
            out.append(f"      why it matters: {r['why']}")
    return "\n".join(out)


# ---------------------------------------------------------------- self-test

_RULES = [{
    "id": "lookback-before-win",
    "consequent": {"id": "win", "pattern": r"\bWin\b.{0,60}\blocked\b"},
    "antecedent": {"id": "lookback", "term": "LOOKBACK",
                   "requires": [{"id": "human-verified", "term": "HUMAN-VERIFIED"}]},
    "why": "spec: the look-back's artifact must exist before the Win is recorded "
          "(cal-weekly W30, live catch)",
}]

# hand-built fixtures (small, so the ordinary self-test doesn't depend on Drive being
# mounted -- the REAL-DATA differential further down is the one that needs the live file)
_GOOD = """## Phase progress
- [x] Win rewritten + locked (film -> #1)

### LOOKBACK -- last week -- HUMAN-VERIFIED 2026-07-21
- real content about last week
"""

_MISSING = """## Phase progress
- [x] Win rewritten + locked (film -> #1)
"""

_INCOMPLETE = """## Phase progress
- [x] Win rewritten + locked (film -> #1)

### LOOKBACK -- last week
- a heading with no verification tag attached
"""

_NOT_APPLICABLE = """## Phase progress
- [ ] nothing locked yet
"""


def _drive_root() -> str:
    """Resolve the Drive spine root instead of typing it.

    THE MOUNT DIRECTORY NAME IS A PERSONAL IDENTIFIER - Google Drive names its mount
    `GoogleDrive-<account address>`, so a literal Drive path here writes a real email
    address into the repo (the shipping lane's `path-drive-cloudstorage` /
    `path-drive-account` / `email-primary` refuse rules all fire on that shape). Env
    var first - this repo's own `CLAUDEOPS_DRIVE` convention (emit_finding.py,
    fault_ledger.py, huddle.py) - then glob discovery over the mount, which replaces
    that convention's hardcoded fallback (`migration-audit/00-FINDINGS.md` F2.1 records
    the literal fallback as its non-compliant half). Bottoming out at a NON-personal
    literal is the accepted shape. Evaluated at import time exactly like the literal it
    replaces: on a machine without the mount it yields a path that does not exist, which
    is the old behaviour, not an exception.
    """
    import glob
    env = os.environ.get("CLAUDEOPS_DRIVE")
    if env:
        return env
    mounts = os.path.join(os.path.expanduser("~"), "Library", "CloudStorage")
    hits = sorted(glob.glob(os.path.join(mounts, "GoogleDrive-*", "My Drive", "_ClaudeOps")))
    return hits[0] if hits else os.path.join(
        mounts, "GoogleDrive-UNRESOLVED", "My Drive", "_ClaudeOps")


def _real_fixture_path():
    drive = _drive_root()
    return os.path.join(drive, "desks", "cal", "state", "checkin-scratch",
                        "weekly-2026-W30", "session-scratchpad.md")


def selftest():
    ok = True

    def report(label, passed, detail=""):
        nonlocal ok
        ok = ok and passed
        print(f"  [{'PASS' if passed else 'FAIL'}] {label}{(' -- ' + detail) if detail else ''}")

    print("precondition_gate --selftest")

    r = check(_GOOD, _RULES)[0]
    report("passes a hand-built correct artifact (lookback present, verified, then Win)",
           r["verdict"] == "SATISFIED" and not r["failed"], r["verdict"])

    r = check(_MISSING, _RULES)[0]
    report("catches the known-bad: Win locked, look-back's artifact never appears "
           "(ANTECEDENT_MISSING -- the real W30 defect's shape)",
           r["verdict"] == "ANTECEDENT_MISSING" and r["failed"], r["verdict"])

    r = check(_INCOMPLETE, _RULES)[0]
    report("catches the known-bad: look-back heading present but hollow -- no "
          "verification substance (ANTECEDENT_INCOMPLETE, distinct from MISSING)",
           r["verdict"] == "ANTECEDENT_INCOMPLETE" and r["missing"] == ["human-verified"],
           f"{r['verdict']} missing={r['missing']}")

    r = check(_NOT_APPLICABLE, _RULES)[0]
    report("reports NOT_APPLICABLE by name when nothing is locked yet (vacuous pass "
          "named, not silent)",
           r["verdict"] == "NOT_APPLICABLE" and not r["failed"], r["verdict"])

    # benign near-miss: the antecedent's WORDS appear without its own marker term intact
    near_miss = ("## Phase progress\n- [x] Win rewritten + locked\n\n"
                "We should really look BACK at last week sometime.\n")
    r = check(near_miss, _RULES)[0]
    report("benign near-miss: a loose mention of 'look back' does not satisfy the "
          "LOOKBACK marker term",
           r["verdict"] == "ANTECEDENT_MISSING", r["verdict"])

    # word-boundary + escaping discipline (inherited convention from order_lint/section_present)
    report("word boundaries hold ('LOOKBACKS' is not 'LOOKBACK')",
           locate("we filed the LOOKBACKS today", {"id": "x", "term": "LOOKBACK"}) is None)
    report("a literal 'term' is escaped, not evaluated as a regex",
           locate("a b c", {"id": "w", "term": "a.c"}) is None
           and locate("say a.c here", {"id": "w", "term": "a.c"}) is not None)

    # fail-closed paths
    try:
        check(_GOOD, [{"id": "x", "consequent": {"id": "c", "term": "c"}}])
        report("raises on a rule missing 'antecedent' (fail-closed)", False, "no raise")
    except ValueError:
        report("raises on a rule missing 'antecedent' (fail-closed)", True)
    try:
        locate("x", {"id": "w", "term": "   "})
        report("raises on an empty 'term' (fail-closed)", False, "no raise")
    except ValueError:
        report("raises on an empty 'term' (fail-closed)", True)
    try:
        locate("x", {"id": "w"})
        report("raises on a marker with neither 'term' nor 'pattern' (fail-closed)",
               False, "no raise")
    except ValueError:
        report("raises on a marker with neither 'term' nor 'pattern' (fail-closed)", True)

    # end-to-end CLI, proving the exit-code contract
    with tempfile.TemporaryDirectory() as td:
        rp = os.path.join(td, "rules.json")
        with open(rp, "w", encoding="utf-8") as fh:
            json.dump(_RULES, fh)
        for label, body, want in (
            ("CLI known-bad (ANTECEDENT_MISSING) -> exit 1", _MISSING, REFUSED),
            ("CLI known-bad (ANTECEDENT_INCOMPLETE) -> exit 1", _INCOMPLETE, REFUSED),
            ("CLI known-good -> exit 0", _GOOD, SATISFIED),
            ("CLI NOT_APPLICABLE -> exit 0", _NOT_APPLICABLE, SATISFIED),
        ):
            ap_ = os.path.join(td, "a.md")
            with open(ap_, "w", encoding="utf-8") as fh:
                fh.write(body)
            rc = subprocess.run([sys.executable, os.path.abspath(__file__),
                                 "--rules", rp, "--artifact", ap_],
                                capture_output=True, text=True).returncode
            report(label, rc == want, f"got exit {rc}")
        rc = subprocess.run([sys.executable, os.path.abspath(__file__), "--rules", rp,
                             "--artifact", os.path.join(td, "nope.md")],
                            capture_output=True, text=True).returncode
        report("CLI missing artifact -> exit 2 (fail-closed)", rc == CANNOT_EVALUATE,
               f"got exit {rc}")

    # ---- DIFFERENTIAL vs the REAL W30 scratchpad (not a fabricated fixture, SOP §V.3) ----
    # This is the real, human-confirmed-compliant artifact named in this part's build brief:
    # weekly-2026-W30/session-scratchpad.md -- 95 lines, a real HUMAN-VERIFIED look-back
    # block and a locked Win. If Drive isn't mounted on this machine, report SKIPPED rather
    # than claim real-data validation that didn't happen (fanout_completeness's own
    # convention for the same situation).
    real_path = _real_fixture_path()
    if os.path.isfile(real_path):
        real_text = open(real_path, encoding="utf-8").read()

        v = check(real_text, _RULES)[0]
        report("DIFFERENTIAL (real W30 scratchpad, UNMODIFIED): the compliant run PASSES",
               v["verdict"] == "SATISFIED" and not v["failed"], v["verdict"])

        # the real defect's shape: strip the look-back sections entirely (they are the
        # last content in the file) -- reproduces "Win locked, look-back never run."
        stripped = real_text.split("### LOOKBACK")[0]
        report("DIFFERENTIAL SETUP: stripping '### LOOKBACK' actually removes content",
               len(stripped) < len(real_text))
        v = check(stripped, _RULES)[0]
        report("DIFFERENTIAL (real W30, look-back artifact DELETED): REFUSED, and NAMED "
              "as the antecedent being skipped -- the real W30 defect, reproduced",
               v["verdict"] == "ANTECEDENT_MISSING" and v["failed"], v["verdict"])

        # the hollow-label case on real text: keep the heading, drop the verification tag
        hollow = real_text.replace(
            "### LOOKBACK — last week (2026-W29, Jul 13-19) · HUMAN-VERIFIED 2026-07-21",
            "### LOOKBACK — last week (2026-W29, Jul 13-19)")
        report("DIFFERENTIAL SETUP: the hollow-label mutation actually changed the text",
               hollow != real_text)
        v = check(hollow, _RULES)[0]
        report("DIFFERENTIAL (real W30, verification tag stripped): ANTECEDENT_INCOMPLETE, "
              "not a silent pass on a bare heading",
               v["verdict"] == "ANTECEDENT_INCOMPLETE", v["verdict"])

        # ---- the honest-bound claim itself, proven live, not just asserted in prose ----
        # order_lint, run against this SAME real compliant text with the position-sensitive
        # framing (before=lookback, after=win), must REFUSE it -- demonstrating exactly the
        # false-refusal this docstring's HONEST BOUND describes, and exactly why this part
        # does not use position. If the sibling isn't deployed, this comparison is skipped
        # rather than faked.
        order_lint_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                       "order_lint.py")
        if os.path.isfile(order_lint_path):
            with tempfile.TemporaryDirectory() as td:
                ap_ = os.path.join(td, "real.md")
                with open(ap_, "w", encoding="utf-8") as fh:
                    fh.write(real_text)
                rp2 = os.path.join(td, "order_rules.json")
                with open(rp2, "w", encoding="utf-8") as fh:
                    json.dump([{"id": "lookback-before-win",
                               "before": {"id": "lookback", "term": "LOOKBACK"},
                               "after": {"id": "win", "term": "Win"},
                               "why": "honest-bound proof"}], fh)
                proc = subprocess.run([sys.executable, order_lint_path, "--rules", rp2,
                                       "--artifact", ap_], capture_output=True, text=True)
            report("HONEST BOUND, proven live: order_lint's POSITIONAL check REFUSES this "
                  "same real compliant artifact (the false refusal this part exists to "
                  "avoid) -- this part's own SATISFIED verdict above is the honest answer",
                   proc.returncode == 1, f"order_lint exit {proc.returncode}")
        else:
            report("HONEST BOUND live comparison vs order_lint.py", False,
                   "SKIPPED -- sibling part not found beside precondition_gate.py")
    else:
        report("DIFFERENTIAL vs real W30 scratchpad", False,
               f"SKIPPED -- Drive fixture not found at {real_path!r} on this machine "
              f"(cannot claim real-data validation)")

    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(
        description="precondition_gate -- a consequent may not stand until its "
                    "antecedent's own artifact is present (and substantive)")
    ap.add_argument("--rules")
    ap.add_argument("--artifact")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())
    if not args.rules or not args.artifact:
        _die("--rules and --artifact are required")
    for p, what in ((args.rules, "rules file"), (args.artifact, "artifact")):
        if not os.path.isfile(p):
            _die(f"{what} not found: {p!r}")
    try:
        rules = json.loads(open(args.rules, encoding="utf-8").read())
    except json.JSONDecodeError as e:
        _die(f"rules file is not valid JSON: {e}")
    if not isinstance(rules, list):
        _die("rules file must contain a JSON list")

    text = open(args.artifact, encoding="utf-8").read()
    try:
        results = check(text, rules)
    except ValueError as e:
        _die(str(e))

    failed = [r for r in results if r["failed"]]
    if args.json:
        print(json.dumps({"verdict": "REFUSED" if failed else "SATISFIED",
                          "results": results}, indent=2))
    else:
        print(f"precondition_gate -- {'REFUSED' if failed else 'SATISFIED'} "
              f"({len(failed)} of {len(results)} rule(s) failed)")
        print(render(results))
    sys.exit(REFUSED if failed else SATISFIED)


if __name__ == "__main__":
    main()

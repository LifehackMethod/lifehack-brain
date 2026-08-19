#!/usr/bin/env python3
"""defeater — every gate ships a companion built to BEAT it.  [Factory · P1.5]

WHAT: for a check the factory emits, author a DEFEAT FIXTURE — a minimal artifact
      engineered to make the check exit 0 while doing none of the work the clause asked
      for — then run the check on it. The check PASSES its own cheat -> the gate is
      theater -> the clause AUTO-DEMOTES to judgment, with the cheat recorded as the
      reason. The check REFUSES the cheat -> the gate is earned.

WHY:  a check can look like enforcement and not be. "Every step must be justified"
      becomes "is a justification present?", which passes on the word `n/a`. That is
      theater with a green light. The consequence is the dangerous part: WITHOUT this,
      getting BETTER at finding checkable rules makes the system WORSE, because you
      mass-produce green lights that hold nothing. Three advisors, isolated and blind to
      each other, invented this independently under three names (cheat fixture · defeat
      fixture · defeater). When that happens it is the obvious answer, not a clever one.

⭐ THE SEAM THAT MAKES THE TWIN HOSTILE — INFORMATION ASYMMETRY.
      The defeat fixture is written by a SEPARATE call whose prompt contains THE CHECK
      ONLY — its command line, its config, its source — and NEVER the clause text. Blind
      to intent, the writer optimises for the LETTER, which IS the attack ("type a
      justification", "a comment-only diff", "an empty section that satisfies the shape").
      One prompt seeing both the clause and the check writes a polite twin that fails on
      purpose, and proves nothing. `assert_blind()` enforces the seam mechanically rather
      than trusting the prompt to hold it.

      The writer is a GRADER-class agent (reads text, returns text, holds no tools,
      touches nothing), so per SOP §V.4a it runs as blind as the machine allows — it
      reuses `voted_judge.judge_argv`, inheriting `--bare` when a key exists and the
      honest CONTAMINATED announcement when one does not.

⭐ POLARITY DECIDES WHETHER THE RULE APPLIES AT ALL — and the check tells us, not the
      clause. MEASURED on the first live run 2026-07-28: the cheat writer beat the real
      W30 "the Win is not named until Phase 3" gate with

          ## Phase 2 — Connect the Dots
          - TBD
          - nothing connected yet; whatever there is will surface inside Win later

      That artifact does NOT name the Win. The gate passed it because it was genuinely
      compliant — just empty. Auto-demoting on that would have DELETED A WORKING GATE on
      the strength of a false defeat, which is the same disease as theater pointed the
      other way. The cause is polarity:

        PRESENCE-shaped  ("X must be present")  -> gutting the substance while keeping the
                                                   token IS the attack. Vacuity == defeat.
        PROHIBITION-shaped ("X must not appear") -> emptiness is COMPLIANCE, not a cheat.
                                                   The real attack is naming X in a form
                                                   the pattern misses.

      **The probe is `check("")` — run the check on an empty artifact.** A prohibition
      check passes it; a presence check refuses it. That reads polarity off the check's
      own BEHAVIOR, needs no clause, and cannot be fooled by naming.

      **And for prohibition-shaped checks the mechanical rule is HONESTLY UNAVAILABLE.**
      Separating "mentions the Win legitimately" from "names it in a dodged form" requires
      reading the clause, and the only clause-aware instrument we have is the contaminated
      judge — putting it back in the load-bearing seat is the one thing Phase 0 existed to
      stop. So those gates return **NOT_AUTO_TESTABLE**: the cheat is still authored and
      printed for a human to eyeball, and the gate is neither demoted nor certified. This
      is FRAME criterion 5 (the loud edge) applied to our own tool — say where the machine
      stops instead of shipping a confident fake.

THE PROMOTION RULE — MECHANICAL, NO JUDGE. A judge deciding "is this really a cheat"
      would put the contaminated instrument back in the load-bearing position. So the
      verdict is an EXIT CODE:
        check(compliant) != 0  -> CANNOT EVALUATE. The check cannot pass work that IS
                                  compliant, so it is broken or the fixture is wrong, and
                                  nothing it says about the cheat means anything (§V.4:
                                  verify the verifier). Fail-closed, never "held."
        check("") == 0         -> NOT_AUTO_TESTABLE (prohibition-shaped; see above).
        defeat is empty        -> VOID. An empty file is a non-artifact, not a cheat.
        check(defeat) == 0     -> MINIMAL_ACCEPTING_INPUT (see below). NOT "defeated".
        check(defeat) != 0     -> HELD, against THIS attempt.

⭐ WHY A MINIMIZATION RUN NO LONGER EMITS `DEFEATED` (corrected 2026-07-28, four sweeps).
      The writer's charge is "produce the minimal accepting input" -- and EVERY check has
      one. That is what a key is. Measured escalation as each fix landed:
      `justification: n/a` -> `aaa bbb ccc` -> `aaa-bbb-ccc` -> every field set to "a".
      By the end nothing was being cheated; the smallest valid input was simply being
      found, which is guaranteed to succeed and so proves nothing.
      **PASSES-WITH-MINIMAL-CONTENT != THEATER.** Theater is when the minimal accepting
      input VIOLATES THE CLAUSE -- and separating those needs the clause, the same wall
      prohibition-shaped checks already hit. So a passing cheat becomes a QUESTION FOR A
      HUMAN, never a demotion. `DEFEATED` is reserved for the DESTRUCTION pass (plan
      0.7H): a named mutation of REAL work that went unnoticed is evidence of a blind
      spot, not a key.
      ⚠ CONTRACT NOTE: this verdict string is consumed by the [ORGANISM-AUDIT] window's
      S2.2 sweep (arbitrated 2026-07-28). Coordinate before changing it again.

⚠ WHAT "HELD" DOES AND DOES NOT MEAN. It means one writer's one attempt failed. It is
      not a certificate of strength, and it never becomes one — the same discipline as
      Law 4.3 ("never assume stability"). Every defeat fixture is recorded VERBATIM in
      the report, because the artifact is the evidence and a reader must be able to see
      the cheat rather than trust a verdict about it.

THE YIELD FLOOR FALLS OUT — NOBODY PICKS A NUMBER (P1.5.2). This replaces a parked
      "BAR 1b with a hand-picked N," which would have been fitted to whatever we happened
      to score. The kill-rate is MEASURED and reported: "M enforceable, D killed by their
      own defeater, S surviving gates." Classify everything as judgment to look safe and
      you produce ZERO surviving gates — a visible, exit-code failure. Falsifiability
      without inventing a threshold.

USAGE
  defeater.py --gates GATES.json                  # LIVE: authors real cheats (costs API)
  defeater.py --gates GATES.json --dry-run        # show each writer prompt, prove blindness
  defeater.py --selftest                          # the promotion rule, offline

GATES.json — a list. `{ARTIFACT}` in argv is replaced by the fixture's path:
  [{"clause_id": "w30-win-late",
    "clause_text": "The Win is not named until Phase 3.",
    "check": {"argv": ["python3", "parts/forbidden_content.py",
                       "--rules", "rules.json", "--text-file", "{ARTIFACT}"],
              "show": ["rules.json"]},
    "compliant": "...an artifact that legitimately passes..."}]

EXIT CODES
  0  at least one gate survived its own defeater
  1  ZERO surviving gates — the visible failure the yield floor exists to produce
  2  CANNOT EVALUATE — unusable gate file, or a check that rejects its own compliant fixture
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PARTS = os.path.abspath(os.path.join(HERE, "..", "parts"))
sys.path.insert(0, PARTS)
from voted_judge import judge_argv, judge_mode, run_grader  # noqa: E402

SURVIVED, NO_SURVIVORS, CANNOT_EVALUATE = 0, 1, 2

DEFEATED, HELD, VOID, UNEVALUABLE = "DEFEATED", "HELD", "VOID", "CANNOT_EVALUATE"
NOT_AUTO_TESTABLE = "NOT_AUTO_TESTABLE"
MINIMAL_ACCEPTING_INPUT = "MINIMAL_ACCEPTING_INPUT"

PRESENCE, PROHIBITION = "presence", "prohibition"


def _die(msg):
    print(f"CANNOT EVALUATE: {msg}", file=sys.stderr)
    sys.exit(CANNOT_EVALUATE)


# ---------------------------------------------------------------- running a check

def run_check(check, artifact_text, workdir=None):
    """Run the gate against one artifact. Returns its exit code (the part contract:
    0 clean · 1 refused · 2 cannot evaluate)."""
    td = workdir or tempfile.mkdtemp(prefix="defeater-")
    path = os.path.join(td, "artifact.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(artifact_text)
    argv = [a.replace("{ARTIFACT}", path) for a in check["argv"]]
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=120,
                           cwd=check.get("cwd") or HERE)
    except (OSError, subprocess.TimeoutExpired) as e:
        return 2, f"check could not run: {e}"
    return p.returncode, (p.stdout or p.stderr or "").strip()


# ---------------------------------------------------------------- the blind seam

def check_view(check):
    """EXACTLY what the defeat writer is allowed to see: the check, and only the check.

    Everything here is mechanics — the command line, the config it reads, the code it
    runs. The clause is deliberately absent; see assert_blind().
    """
    parts = ["COMMAND:", "  " + " ".join(check["argv"])]
    for f in check.get("show", []):
        path = f if os.path.isabs(f) else os.path.join(check.get("cwd") or HERE, f)
        try:
            body = open(path, encoding="utf-8").read()
        except OSError as e:
            body = f"<unreadable: {e}>"
        parts += [f"\nFILE {os.path.basename(path)}:", body]
    return "\n".join(parts)


def probe_polarity(check, workdir=None):
    """Read the check's polarity off its own BEHAVIOR: does it pass an EMPTY artifact?

    A prohibition check ("must not contain X") passes emptiness — nothing is there to
    forbid. A presence check ("must contain X") refuses it. No clause, no naming
    convention, no keyword list: just the check's answer to the emptiest possible input.

    ONLY ONE QUESTION MATTERS: does EMPTINESS SATISFY THIS CHECK? That is the sole source
    of the false-defeat this probe exists to prevent. So exit 1 (refused) and exit 2
    (un-evaluable) are the SAME ANSWER — no — and both mean PRESENCE-shaped.
    Measured 2026-07-28 on the 7-part sweep: three well-built parts return exit 2 on an
    empty artifact because they are properly fail-closed (an empty input is un-evaluable,
    not compliant). Treating that as "polarity unknown" would have made the sweep silent
    about them — punishing the parts for being MORE careful, which is backwards.
    Safe by construction: a check that returns 2 for everything is already caught upstream
    by the `check(compliant) == 0` gate, so this can never manufacture a false HELD.
    """
    rc, detail = run_check(check, "", workdir)
    if rc == 0:
        return PROHIBITION, detail
    return PRESENCE, (f"empty artifact -> exit {rc} (emptiness does not satisfy this "
                      f"check, so gutting is a valid attack): {detail[:140]}")


_FRAMING = """You are generating a TEST INPUT for a small program.

The program below reads one file and exits 0 (accept) or nonzero (reject). Answer purely
as a question about the code in front of you.
"""

_ENVELOPE = """Return your artifact wrapped in these exact markers and nothing else:

<<<ARTIFACT
(the artifact text goes here)
ARTIFACT>>>

If you decline for any reason, reply WITHOUT the markers and say why — that is recorded
as "no fixture produced", never as a finding about the check."""


WRITER_PROMPT = _FRAMING + """
A sample input the program currently ACCEPTS is shown below. Produce a DIFFERENT input
that the program also ACCEPTS, carrying AS LITTLE CONTENT AS POSSIBLE. Strip everything
the code does not actually examine; keep only what it literally requires. If it looks for
a field, give it the field with the shortest value that satisfies it. If it counts, give
it the count. If it looks for a marker, give it the marker.

You are not told what the program is FOR, and you should not guess. Work only from the
code shown.

Do not return an empty file — an empty input tells us nothing about the code.

{check}

A SAMPLE INPUT THE PROGRAM ACCEPTS:
<<<COMPLIANT
{compliant}
COMPLIANT

""" + _ENVELOPE


EVASION_PROMPT = _FRAMING + """
This program REJECTS inputs matching the patterns in its config. A sample input it
currently ACCEPTS is shown below.

Produce a DIFFERENT input that the program still ACCEPTS, but which stays AS CLOSE AS
POSSIBLE to the config's patterns — vary the capitalisation, the layout, the spacing, the
wording, where the line breaks fall. You are mapping where the pattern's boundary actually
falls, so the interesting input is one that a reader would call the same thing while the
matcher does not.

Do not simply delete content: an emptied file tells us nothing about the boundary.

You are not told what the program is FOR, and you should not guess. Work only from the
pattern shown.

{check}

A SAMPLE INPUT THE PROGRAM ACCEPTS:
<<<COMPLIANT
{compliant}
COMPLIANT

""" + _ENVELOPE


def build_prompt(check, compliant, polarity=PRESENCE):
    """Presence-shaped checks are attacked by GUTTING; prohibition-shaped ones by EVASION.
    Both prompts see the check and only the check."""
    template = EVASION_PROMPT if polarity == PROHIBITION else WRITER_PROMPT
    return template.format(check=check_view(check), compliant=compliant)


def assert_blind(prompt, clause_text):
    """THE SEAM, ENFORCED — not trusted to a well-worded instruction.

    If the clause's own language reaches the writer, the twin stops being hostile and the
    whole exercise silently degrades into a polite fixture that fails on purpose. So the
    prompt is checked mechanically before it is ever sent, and a leak RAISES.
    """
    if not clause_text:
        return True
    if clause_text.strip() and clause_text.strip() in prompt:
        raise ValueError("BLINDNESS BROKEN: the clause text reached the defeat writer")

    # A distinctive RUN of the clause is enough of a leak to matter, and a paraphrase must
    # not slip through on punctuation or filler. BOTH sides are reduced to the same word
    # stream before comparing -- comparing a filtered n-gram against raw prose was the
    # first version of this check and it caught nothing, which its own test proved.
    def stream(t):
        return [w for w in re.findall(r"[A-Za-z0-9']+", (t or "").lower()) if len(w) > 3]

    words, hay = stream(clause_text), " ".join(stream(prompt))
    for i in range(max(0, len(words) - 5)):
        run_of_six = " ".join(words[i:i + 6])
        if run_of_six in hay:
            raise ValueError("BLINDNESS BROKEN: a 6-word run of the clause reached the "
                             f"defeat writer ({run_of_six!r})")
    return True


_ARTIFACT_BLOCK = re.compile(r"<<<ARTIFACT\s*\n(.*?)\nARTIFACT>>>", re.DOTALL)


def extract_artifact(raw):
    """Pull the fixture out of its envelope — and REFUSE to invent one if it is absent.

    MEASURED 2026-07-28, first live run: the writer declined the task on general safety
    grounds ("this is asking me to game a check"), and its refusal PROSE happened to
    contain the literal string the check greps for. The check matched the refusal, exited
    0, and the gate was scored DEFEATED by a message that was not an artifact at all.

    A free-text response can therefore never be handed to a check. The fixture must arrive
    inside explicit markers; anything else is "no fixture produced," which is a fact about
    the WRITER and says nothing whatsoever about the check.
    """
    m = _ARTIFACT_BLOCK.search(raw or "")
    if not m:
        return None
    body = m.group(1)
    return re.sub(r"^```[a-zA-Z]*\n|\n```$", "", body).strip("\n")


def live_writer(model="sonnet", timeout=240):
    """A real defeat author. GRADER-class: reads text, returns text, holds no tools.

    Routed through `run_grader`, so it inherits the best blindness the machine has. That
    matters more here than anywhere else: MEASURED 2026-07-28, the CONTAMINATED writer
    declined this task 3 of 4 runs — it holds Lifehack' security canon and reads an
    injected task as an attack — while the blind Codex grader answered it plainly.
    """
    def write(prompt):
        raw = run_grader(prompt, model=model, timeout=timeout)
        if not raw:
            return None, "defeat writer could not run or returned nothing"
        art = extract_artifact(raw)
        if art is None:
            return None, ("the writer returned no ARTIFACT block — it declined or answered "
                          f"in prose, which is NOT a finding about the check. It said: "
                          f"{raw[:300]!r}")
        return art, ""
    return write


# ---------------------------------------------------------------- the promotion rule

def attempt(gate, writer, workdir=None):
    """One gate, one defeat attempt. The verdict is an exit code, never a judgment."""
    check, clause = gate["check"], gate.get("clause_text", "")
    out = {"clause_id": gate.get("clause_id"), "clause_text": clause}

    # VERIFY THE VERIFIER FIRST. A check that refuses genuinely compliant work is broken,
    # and nothing it later says about a cheat carries information.
    rc, detail = run_check(check, gate["compliant"], workdir)
    if rc != 0:
        out.update(verdict=UNEVALUABLE, defeat=None,
                   detail=(f"the check REFUSED its own compliant fixture (exit {rc}) — the "
                           f"check or the fixture is wrong, so this gate cannot be tested: "
                           f"{detail[:200]}"))
        return out

    # POLARITY, read off the check's own behavior — not off the clause, not off a name.
    polarity, pdetail = probe_polarity(check, workdir)
    out["polarity"] = polarity
    if polarity is None:
        out.update(verdict=UNEVALUABLE, defeat=None,
                   detail=f"polarity could not be probed: {pdetail}")
        return out

    prompt = build_prompt(check, gate["compliant"], polarity)
    assert_blind(prompt, clause)          # raises rather than silently degrading
    defeat, err = writer(prompt)
    if not defeat:
        out.update(verdict=UNEVALUABLE, defeat=None,
                   detail=f"no defeat fixture was produced: {err}")
        return out
    if not defeat.strip():
        out.update(verdict=VOID, defeat=defeat,
                   detail="the defeat fixture is empty — a blank page is a non-artifact, "
                          "not a cheat, and must not count as a hole")
        return out

    rc, detail = run_check(check, defeat, workdir)

    if polarity == PROHIBITION:
        # The cheat is authored and kept for a human, but NOTHING is auto-decided: a
        # clause-blind rule cannot tell an evasion from honest compliance here, and the
        # only clause-aware instrument available is the contaminated judge.
        out.update(verdict=NOT_AUTO_TESTABLE, defeat=defeat, cheat_passed=(rc == 0),
                   detail=("this check is PROHIBITION-shaped (it passes an empty artifact), "
                           "so passing a cheat does not prove theater — emptiness is "
                           "compliance. The evasion attempt below "
                           + ("PASSED the check and needs a human read: does it actually "
                              "express the forbidden thing?" if rc == 0 else
                              "was REFUSED by the check.")
                           + " Neither demoted nor certified — the machine stops here on "
                             "purpose (FRAME criterion 5)."))
        return out

    # ONE QUESTION DECIDES THIS: did the cheat GET THROUGH? Exit 0 is the only "yes."
    # Exit 1 (refused with a finding) and exit 2 (refused as un-gradeable) are both "no",
    # and collapsing exit 2 into CANNOT_EVALUATE was wrong -- it read a check FAIL-CLOSING
    # on a cheat as a non-result, which punishes the most careful parts. Safe because the
    # verify-the-verifier leg above already proved this check passes its COMPLIANT fixture,
    # so it is not merely broken-for-everything. The distinction is recorded, not collapsed.
    if rc == 0:
        # ⭐ A MINIMIZATION RUN MAY NOT CALL THIS THEATER (corrected 2026-07-28 after four
        # sweeps). The writer's charge is "produce the minimal accepting input" -- and
        # EVERY check has one. That is what a key is. Measured escalation across sweeps:
        # `justification: n/a` -> `aaa bbb ccc` -> `aaa-bbb-ccc` -> every field set to "a".
        # By the end nothing was being cheated; the smallest valid input was simply being
        # found, which is guaranteed to succeed and therefore proves nothing.
        # PASSES-WITH-MINIMAL-CONTENT != THEATER. Theater is when the minimal accepting
        # input VIOLATES THE CLAUSE -- and telling those apart needs the clause, the same
        # wall prohibition-shaped checks already hit. So the honest verdict is a question
        # for a human, not a demotion.
        # ⚠ ACCEPTED COST: the genuine `justification: n/a` case routes to a human too. A
        # person calls that theater in one second and the machine provably cannot.
        # DEFEATED is now reserved for the DESTRUCTION pass (plan 0.7H), where a named
        # mutation of REAL work went unnoticed -- evidence of a blind spot, not a key.
        out.update(verdict=MINIMAL_ACCEPTING_INPUT, defeat=defeat,
                   detail="the check PASSED the SMALLEST artifact that satisfies it. Every "
                          "check has one, so this is NOT proof of theater — it is the "
                          "gate's floor, shown. HUMAN READ: does this artifact actually do "
                          "the work the clause asks for? If plainly not, the gate is "
                          "theater; if it is merely small, the gate is fine.")
    else:
        out.update(verdict=HELD, defeat=defeat,
                   held_via=("refused" if rc == 1 else "fail-closed"),
                   detail=("the check REFUSED the cheat" if rc == 1 else
                           "the check FAIL-CLOSED on the cheat (exit 2 — it would not grade "
                           f"the artifact at all): {detail[:140]}")
                   + " — this gate is earned against THIS attempt (one attempt by one "
                     "writer; not a certificate)")
    return out


def run(gates, writer, enforceable_total=None, workdir=None):
    """Every gate, plus the MEASURED kill-rate that replaces a hand-picked yield floor."""
    results = [attempt(g, writer, workdir) for g in gates]
    tally = {}
    for r in results:
        tally[r["verdict"]] = tally.get(r["verdict"], 0) + 1
    surviving = tally.get(HELD, 0)
    minimal = tally.get(MINIMAL_ACCEPTING_INPUT, 0)
    needs_human = tally.get(NOT_AUTO_TESTABLE, 0) + minimal
    total = enforceable_total if enforceable_total is not None else len(gates)
    head = (f"{total} enforceable, {tally.get(DEFEATED, 0)} killed by their own defeater, "
            f"{surviving} surviving gates")
    if minimal:
        head += (f", {minimal} at their FLOOR (smallest valid input passed — a human reads "
                 f"whether that input does the work)")
    prohibition_n = tally.get(NOT_AUTO_TESTABLE, 0)
    if prohibition_n:
        head += (f", {prohibition_n} prohibition-shaped gate(s) the machine will not judge")
    if needs_human:
        head += f" — {needs_human} gate(s) TOTAL need a human read"
    return {"results": results, "tally": tally,
            "enforceable": total,
            "gates_tested": len(gates),
            "defeated": tally.get(DEFEATED, 0),
            "surviving_gates": surviving,
            "needs_human": needs_human,
            "minimal_accepting": minimal,
            "headline": head,
            "verdict": ("FAILURE — ZERO surviving gates. Classifying everything as judgment "
                        "scores exactly this, which is the point: the floor is measured, not "
                        "chosen." if surviving == 0 else
                        f"{surviving} gate(s) survived a hostile twin")}


# ---------------------------------------------------------------- self-test

_WEAK_CHECK_SRC = '''import re, sys
t = open(sys.argv[1], encoding="utf-8").read()
sys.exit(0 if re.search(r"justification:\\s*\\S+", t) else 1)
'''

_WEAK_COMPLIANT = ("step 1: re-ran the corpus sweep\n"
                   "justification: W29's corpus changed under us, so the earlier sweep's "
                   "counts could not be reused and the whole pass had to run again\n")

_WEAK_CHEAT = "step 1: re-ran the corpus sweep\njustification: n/a\n"

_STRONG_RULES = [{"id": "win-named-early", "term": "Win", "mode": "declaration",
                  "why": "spec: the Win is named in Phase 3, never before"}]

_STRONG_COMPLIANT = ("## Phase 2 — Connect the Dots\n\n"
                     "- the throughlines below live inside the Win as actions\n"
                     "- ranking is deferred; nothing is concluded here\n")

_STRONG_CHEAT_NAIVE = ("## Phase 2 — Connect the Dots\n\n"
                       "- **Win (operator-authored):** Fully Day-1 ready, paperwork confirmed\n")


def selftest():
    ok = True

    def report(label, passed, detail=""):
        nonlocal ok
        ok = ok and passed
        print(f"  [{'PASS' if passed else 'FAIL'}] {label}{(' -- ' + detail) if detail else ''}")

    print("defeater --selftest  (the promotion rule, offline — no API calls)")

    def stub(text):
        return lambda prompt: (text, "")

    with tempfile.TemporaryDirectory() as td:
        weak_py = os.path.join(td, "weak_check.py")
        with open(weak_py, "w") as fh:
            fh.write(_WEAK_CHECK_SRC)
        weak_gate = {
            "clause_id": "weak-justify",
            "clause_text": "Every step must be justified with a real reason.",
            "check": {"argv": [sys.executable, weak_py, "{ARTIFACT}"], "show": [weak_py]},
            "compliant": _WEAK_COMPLIANT,
        }

        rules = os.path.join(td, "rules.json")
        with open(rules, "w") as fh:
            json.dump(_STRONG_RULES, fh)
        strong_gate = {
            "clause_id": "w30-win-late",
            "clause_text": "The Win is not named until Phase 3.",
            "check": {"argv": [sys.executable, os.path.join(PARTS, "forbidden_content.py"),
                               "--rules", rules, "--text-file", "{ARTIFACT}"],
                      "show": [rules]},
            "compliant": _STRONG_COMPLIANT,
        }

        # a PRESENCE-shaped gate that genuinely cannot be satisfied without doing the work
        src_ids = os.path.join(td, "source-ids.json")
        with open(src_ids, "w") as fh:
            json.dump(["cw_p2_unit_000269", "cw_p2_unit_000270", "cw_p2_unit_000271"], fh)
        strong_presence = {
            "clause_id": "map-covers-corpus",
            "clause_text": "The Map must account for every item in the source corpus.",
            "check": {"argv": [sys.executable, os.path.join(PARTS, "completeness_receipt.py"),
                               "--artifact", "{ARTIFACT}", "--source-ids", src_ids],
                      "show": [src_ids]},
            "compliant": ("# Map\n\n- `cw_p2_unit_000269` — the first source item, carried forward\n"
                          "- `cw_p2_unit_000270` — the second, carried forward\n"
                          "- `cw_p2_unit_000271` — the third, carried forward\n"),
        }

        # ── POLARITY, READ OFF THE CHECK'S OWN BEHAVIOR ──
        report("a 'must contain' check REFUSES an empty artifact -> PRESENCE",
               probe_polarity(weak_gate["check"], td)[0] == PRESENCE)
        report("a 'must NOT contain' check PASSES an empty artifact -> PROHIBITION",
               probe_polarity(strong_gate["check"], td)[0] == PROHIBITION)
        report("a completeness check is PRESENCE-shaped",
               probe_polarity(strong_presence["check"], td)[0] == PRESENCE)

        # ── THE KNOWN-WEAK CHECK MUST DIE TO ITS OWN CHEAT ──
        r = attempt(weak_gate, stub(_WEAK_CHEAT), td)
        report("a passing cheat is MINIMAL_ACCEPTING_INPUT, never DEFEATED",
               r["verdict"] == MINIMAL_ACCEPTING_INPUT, r["verdict"])
        report("...and it asks the human the one question the machine cannot answer",
               "HUMAN READ" in r["detail"] and "NOT proof of theater" in r["detail"])
        report("the cheat is recorded VERBATIM as the evidence, not summarised",
               "n/a" in (r["defeat"] or ""))

        # ── A KNOWN-STRONG PRESENCE GATE MUST SURVIVE ──
        r = attempt(strong_presence, stub("# Map\n\n- `cw_p2_unit_000269` — carried forward\n"), td)
        report("a known-STRONG presence gate (completeness) HOLDS against a gutting cheat",
               r["verdict"] == HELD, r["detail"][:58])

        # ⭐ THE REGRESSION TEST — the exact artifact that produced a FALSE DEFEAT live.
        # Before the polarity probe this returned DEFEATED and would have deleted a
        # working gate. It names nothing forbidden; it is merely empty, which for a
        # prohibition check is COMPLIANCE.
        false_defeat = ("## Phase 2 — Connect the Dots\n\n- TBD\n"
                        "- nothing connected yet; whatever there is will surface inside Win later\n")
        r = attempt(strong_gate, stub(false_defeat), td)
        report("the live FALSE DEFEAT is no longer a defeat (it gutted content, named nothing)",
               r["verdict"] == NOT_AUTO_TESTABLE, r["verdict"])
        report("a prohibition gate is neither demoted NOR certified",
               r["verdict"] not in (DEFEATED, HELD) and r["polarity"] == PROHIBITION)
        report("the human is told the cheat PASSED and asked the question only they can answer",
               r["cheat_passed"] and "human read" in r["detail"])
        report("the prohibition cheat is still kept verbatim for that human read",
               "TBD" in (r["defeat"] or ""))

        # a naive attempt that the prohibition gate REFUSES is reported honestly too
        r = attempt(strong_gate, stub(_STRONG_CHEAT_NAIVE), td)
        report("a prohibition cheat that gets REFUSED is reported as refused, not as HELD",
               r["verdict"] == NOT_AUTO_TESTABLE and not r["cheat_passed"])

        # ── THE TWO PROMPTS: gut a presence check, EVADE a prohibition one ──
        # compare on a flattened prompt: reflowing the prose must not break these
        def flat(*a):
            return re.sub(r"\s+", " ", build_prompt(*a))

        p_gut = flat(weak_gate["check"], "x", PRESENCE)
        p_evade = flat(strong_gate["check"], "x", PROHIBITION)
        report("a presence check is attacked by MINIMISING the input",
               "AS LITTLE CONTENT AS POSSIBLE" in p_gut)
        report("a prohibition check is attacked by BOUNDARY-PROBING, never by deletion",
               "AS CLOSE AS POSSIBLE to the config's patterns" in p_evade
               and "an emptied file tells us nothing" in p_evade)
        report("the two prompts are genuinely different attacks", p_gut != p_evade)
        # MEASURED: the first framings ("game the check", "red-team our own check") were
        # DECLINED twice by the live writer -- it could not verify the ownership claim.
        # The neutral test-input register asks the same question without asserting
        # anything the writer cannot check.
        report("neither prompt asserts an authorisation the writer cannot verify",
               not re.search(r"we wrote|we own|authoris|red-team|game the", p_gut + p_evade,
                             re.IGNORECASE))

        # ── THE VACUITY GUARD: a blank page is not a cheat ──
        r = attempt(strong_gate, stub("   \n  \n"), td)
        report("an EMPTY defeat is VOID, not a defeat (else every 'must not contain X' "
               "check loses to a blank page)", r["verdict"] == VOID)

        # ⭐ REGRESSION: a WRITER REFUSAL may never be scored as a defeat.
        # Measured live — the writer declined and its refusal prose contained the very
        # string the check greps for, so the check exited 0 on a message that was not an
        # artifact. The envelope makes that structurally impossible.
        refusal = ("This isn't something I can help with. The check only regexes for the "
                   "literal string justification: followed by non-whitespace, so it never "
                   "verifies the work was done.")
        report("a refusal carrying the check's own trigger string yields NO artifact",
               extract_artifact(refusal) is None)
        r = attempt(weak_gate, lambda p: (extract_artifact(refusal),
                                          "writer declined"), td)
        report("a declining writer is CANNOT_EVALUATE — a fact about the writer, not the check",
               r["verdict"] == UNEVALUABLE, r["detail"][:58])
        report("a properly enveloped artifact IS extracted",
               extract_artifact("preamble\n<<<ARTIFACT\njustification: n/a\nARTIFACT>>>\ntail")
               == "justification: n/a")
        report("a code fence inside the envelope is stripped",
               extract_artifact("<<<ARTIFACT\n```md\nhello\n```\nARTIFACT>>>") == "hello")
        report("both writer prompts demand the envelope, so a refusal is always detectable",
               "<<<ARTIFACT" in build_prompt(weak_gate["check"], "x", PRESENCE)
               and "<<<ARTIFACT" in build_prompt(strong_gate["check"], "x", PROHIBITION))
        report("the prompt asks a neutral question about code, not for help cheating",
               "generating a TEST INPUT for a small program"
               in build_prompt(weak_gate["check"], "x", PRESENCE))

        # ── VERIFY THE VERIFIER: a check that refuses compliant work proves nothing ──
        broken = dict(strong_gate, compliant="**Win (operator-authored):** named far too early")
        r = attempt(broken, stub(_WEAK_CHEAT), td)
        report("a check that REFUSES its own compliant fixture is CANNOT_EVALUATE, not HELD",
               r["verdict"] == UNEVALUABLE, r["detail"][:60])

        # ── THE BLIND SEAM, ENFORCED MECHANICALLY ──
        p = build_prompt(weak_gate["check"], weak_gate["compliant"])
        report("the writer prompt carries the check's COMMAND and CONFIG",
               "weak_check.py" in p and "justification" in p)
        report("the writer prompt does NOT carry the clause text",
               weak_gate["clause_text"] not in p)
        try:
            assert_blind(p + "\n" + weak_gate["clause_text"], weak_gate["clause_text"])
            report("a leaked clause RAISES instead of silently degrading the test", False)
        except ValueError:
            report("a leaked clause RAISES instead of silently degrading the test", True)
        try:
            assert_blind(p + "\nEvery step must be justified with a real reason indeed",
                         weak_gate["clause_text"])
            report("a PARAPHRASE-length leak (6-word run) is caught too", False)
        except ValueError:
            report("a PARAPHRASE-length leak (6-word run) is caught too", True)
        report("an honest prompt passes the blindness assertion",
               assert_blind(p, weak_gate["clause_text"]))

        # ── THE YIELD FLOOR IS MEASURED, NOT CHOSEN (P1.5.2) ──
        rep = run([weak_gate, strong_presence, strong_gate],
                  lambda pr: ((_WEAK_CHEAT, "") if "weak_check" in pr
                              else ("# Map\n\n- `cw_p2_unit_000269` — carried forward\n", "")
                              if "source-ids" in pr else (false_defeat, "")), workdir=td)
        report("the report states MEASURED counts, not a threshold",
               rep["defeated"] == 0 and rep["minimal_accepting"] == 1
               and rep["surviving_gates"] == 1, rep["headline"])
        report("everything the machine will NOT judge lands in the human bucket",
               rep["needs_human"] == 2          # 1 prohibition-shaped + 1 at its floor
               and "need a human read" in rep["headline"]
               and "FLOOR" in rep["headline"])
        report("the headline counts what was MEASURED (enforceable/killed/surviving)",
               rep["enforceable"] == 3 and "killed by their own defeater" in rep["headline"])
        report("the verdict names survivors rather than comparing against a chosen floor",
               "survived a hostile twin" in rep["verdict"]
               and not re.search(r"threshold|at least \d|minimum", rep["verdict"]))

        # the degenerate strategy — call everything judgment, ship no gates
        degenerate = run([], stub("x"), enforceable_total=0, workdir=td)
        report("the all-judgment strategy scores ZERO and is reported as a FAILURE",
               degenerate["surviving_gates"] == 0 and "FAILURE" in degenerate["verdict"])
        # ...and a set of gates that ALL die is equally a failure
        allbad = run([weak_gate], stub(_WEAK_CHEAT), workdir=td)
        report("gates that ALL die to their cheats is also a reported FAILURE",
               allbad["surviving_gates"] == 0 and "FAILURE" in allbad["verdict"])
        report("the FLOOR bucket is counted separately, never folded into either side",
               allbad["minimal_accepting"] == 1 and allbad["defeated"] == 0
               and allbad["surviving_gates"] == 0)
        report("the headline names the floor in words a human can act on",
               "FLOOR" in allbad["headline"] and "does the work" in allbad["headline"])

        # ── CLI ──
        gates_file = os.path.join(td, "gates.json")
        with open(gates_file, "w") as fh:
            json.dump([weak_gate], fh)
        me = os.path.abspath(__file__)
        p2 = subprocess.run([sys.executable, me, "--gates", gates_file, "--dry-run"],
                            capture_output=True, text=True)
        report("CLI --dry-run shows the prompt without spending an API call",
               p2.returncode == 0 and "COMMAND:" in p2.stdout, f"exit {p2.returncode}")
        report("CLI --dry-run PROVES blindness rather than asserting it",
               "BLINDNESS: clause text is absent" in p2.stdout)
        p3 = subprocess.run([sys.executable, me, "--gates", os.path.join(td, "nope.json")],
                            capture_output=True, text=True)
        report("CLI missing gate file -> exit 2 (fail-closed)",
               p3.returncode == CANNOT_EVALUATE, f"exit {p3.returncode}")

    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


# ---------------------------------------------------------------- CLI

def main():
    ap = argparse.ArgumentParser(description="defeater — every gate ships a cheat built to beat it")
    ap.add_argument("--gates", help="JSON list of gates to attack")
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--enforceable-total", type=int,
                    help="how many clauses were classified enforceable (for the kill-rate)")
    ap.add_argument("--out", help="write the defeat report here")
    ap.add_argument("--dry-run", action="store_true",
                    help="print each writer prompt and prove the clause never reaches it")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())
    if not args.gates:
        _die("--gates is required")
    if not os.path.isfile(args.gates):
        _die(f"gate file not found: {args.gates!r}")
    try:
        gates = json.loads(open(args.gates, encoding="utf-8").read())
    except json.JSONDecodeError as e:
        _die(f"gate file is not valid JSON: {e}")
    if not gates:
        _die("gate file holds ZERO gates — refusing to report a vacuous pass")

    if args.dry_run:
        for g in gates:
            prompt = build_prompt(g["check"], g["compliant"])
            assert_blind(prompt, g.get("clause_text", ""))
            print(f"═══ {g.get('clause_id')} ═══")
            print(prompt)
            print("\nBLINDNESS: clause text is absent from the prompt above "
                  f"({g.get('clause_text', '')[:60]!r})\n")
        sys.exit(SURVIVED)

    print(f"defeater — {len(gates)} gate(s)")
    print(f"  {judge_mode()['announce']}")
    rep = run(gates, live_writer(args.model), enforceable_total=args.enforceable_total)

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(rep, fh, indent=2, ensure_ascii=False)

    if args.json:
        print(json.dumps(rep, indent=2, ensure_ascii=False))
    else:
        for r in rep["results"]:
            print(f"  [{r['verdict']:<16}] {r['clause_id']}")
            print(f"        {r['detail']}")
            if r["verdict"] == DEFEATED:
                print("        THE CHEAT THAT BEAT IT:")
                for line in (r["defeat"] or "").splitlines()[:8]:
                    print(f"          | {line}")
        print(f"\n  {rep['headline']}")
        print(f"  {rep['verdict']}")
        if args.out:
            print(f"  report: {args.out}")

    sys.exit(SURVIVED if rep["surviving_gates"] else NO_SURVIVORS)


if __name__ == "__main__":
    main()

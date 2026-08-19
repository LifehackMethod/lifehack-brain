#!/usr/bin/env python3
"""classify_clause — the three-field sort.  [Factory · S1.4 + S1.5]

WHAT: tags each clause with the three fields the generator needs —
        enforceability : enforceable · human_in_the_loop · uncheckable_nowhere   (LLM, K-voted)
                          (legacy spelling `hill_climb`, pre-2026-08, is still ACCEPTED on
                          read so frozen artifacts stay loadable -- never emitted)
        tier           : reasoning · enforcement · state                  (mechanical)
        critical       : bool                                             (mechanical flag)
      Everything downstream — rung, family, which part — is a lookup from these three.
WHY:  the sorting is the entire gap between the parts library and "minutes." It is
      mechanical, repeatable and boring, which is exactly what a machine should do and a
      human should never have to remember.

THE TIER IS THE INSTRUMENT SELECTOR (SOP §II.0, promoted to doctrine 2026-07-27). This is
      the field the first draft of the plan omitted, and the omission matters: a floor
      graded by the wrong instrument returns a CONFIDENT WRONG answer.
        reasoning   → a blind, K-voted LLM judge
        enforcement → provoke the guard and assert it blocks (plus the allowed twin)
        state       → a native-id set-diff against the source
      The worked failure: a blind judge read a Map built from 241 items and passed it as
      "omitting nothing"; a set-diff found 20 covered. The judge was not bad at its job —
      it was the wrong instrument for a state-floor property.

FAIL-CLOSED, IN ONE DIRECTION ONLY. "A false gate on judgment is worse than no gate at
      all" (SOP §III.10, §V.7). So every uncertainty resolves AWAY from `enforceable`:
        · a split or low-confidence vote            → `human_in_the_loop`, never `enforceable`
        · no LLM available (`--no-llm`)             → `UNCLASSIFIED`, never a guess
        · an ambiguous tier                         → recorded ambiguous, not invented
        · an uncertain `critical`                   → false, but ALWAYS surfaced for the
                                                      human batch, never silently dropped
      Over-calling something judgment costs a missed gate someone can add later.
      Over-calling something enforceable ships a gate that fires on correct work.

WHY THE VOTE IS NOT `voted_judge`'s FOLD. `voted_judge.py` folds met/missed/violated,
      where the asymmetry is evidence-vs-non-observation (a quoted violation outranks a
      majority that didn't notice). That asymmetry does not exist here: this is a 3-way
      category choice, not a claim about whether something happened. So the K-vote
      discipline is reused; the fold rule is the one this verdict space needs — unanimity
      or it degrades to `human_in_the_loop`.

USAGE
  classify_clause.py --clauses FROZEN.json --no-llm            # mechanical axes only, free
  classify_clause.py --clauses FROZEN.json --k 3 --out DIR     # full sort
  classify_clause.py --canary                                  # LIVE 3-clause gate (costs API)
  classify_clause.py --selftest                                # mechanical axes, no API

EXIT CODES
  0  classified
  1  a clause could not be classified and was NOT silently defaulted
  2  CANNOT EVALUATE — missing/invalid clause file, classifier unusable.
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
sys.path.insert(0, HERE)
sys.path.insert(0, PARTS)
# The classifier does not get to decide how blind it is -- it asks the shipped part, so
# blindness (and the honesty about NOT having it) is inherited, never re-implemented.
from voted_judge import judge_argv, judge_mode, run_controls  # noqa: E402

OK, UNRESOLVED, CANNOT_EVALUATE = 0, 1, 2

ENFORCEABLE, HUMAN_IN_THE_LOOP, UNCHECKABLE = (
    "enforceable", "human_in_the_loop", "uncheckable_nowhere")
# `hill_climb` is the LEGACY spelling of `human_in_the_loop` (renamed 2026-08-01 -- the old
# name told a fresh session nothing: not that a human is required, not why, not what to do
# about it). Retained ONLY so frozen artifacts under system/factory/frozen/ -- measured
# under the old name and never to be rewritten, on pain of falsifying the measurement record
# -- stay readable. Nothing in this file ever EMITS this spelling again; see
# `_normalize_enforceability` for the one place it is read and folded into the current name.
HILL_CLIMB_LEGACY = "hill_climb"
UNCLASSIFIED = "UNCLASSIFIED"
VALID = {ENFORCEABLE, HUMAN_IN_THE_LOOP, HILL_CLIMB_LEGACY, UNCHECKABLE}


def _normalize_enforceability(v):
    """READ-side only. Folds the legacy `hill_climb` spelling into the current
    `human_in_the_loop` name so a vote, or a row loaded from an older classified/frozen
    file, means the same thing regardless of which name it was written under. Called at
    every boundary where an enforceability value enters this module from outside (an LLM
    vote, a stored row) -- never called on a value this module is about to emit."""
    return HUMAN_IN_THE_LOOP if v == HILL_CLIMB_LEGACY else v

# ── tier signals — surface structure, not meaning. Deliberately plain. ──────────
_TIER_SIGNALS = {
    "state": [r"\bevery item\b", r"\ball \d+\b", r"\bset-?diff\b", r"\bnative[- ]id\b",
              r"\bledger\b", r"\breceipt\b", r"\bscratchpad\b", r"\bwrite[s]? back\b",
              r"\bpersist", r"\bcorpus\b", r"\bsource ids?\b", r"\bcount\b", r"\bomit",
              r"\bcomplete(ness)?\b", r"\brecords?\b", r"\bon disk\b", r"\bstate file\b"],
    "enforcement": [r"\bmarker\b", r"\bstamp\b", r"\bgate\b", r"\bhook\b", r"\bblock",
                    r"\bguard\b", r"\bprecede", r"\bbefore\b", r"\bafter\b", r"\border\b",
                    r"\bphase \d+ complete\b", r"\bmust (?:contain|include|exist)\b",
                    r"\bnever\b", r"\bdo not\b", r"\bhard[- ]stop\b", r"\brefuse",
                    r"\bnumbered\b", r"\bsection\b", r"\bformat\b"],
    "reasoning": [r"\bquestion", r"\bjudg", r"\bsurface", r"\btension", r"\bvoice\b",
                  r"\btone\b", r"\bsynthesi", r"\binterrogat", r"\bconversat",
                  r"\bleveraged\b", r"\bthoughtful", r"\bwell[- ]considered\b",
                  r"\brecogni", r"\bdecide", r"\bconfirm"],
}

# ── critical signals — blast radius. Errs toward flagging. ─────────────────────
_CRITICAL = [r"\bwrite[s]?\b", r"\bdelete", r"\bsend", r"\bemail\b", r"\bcalendar\b",
             r"\bdraft", r"\bmoney\b", r"\bpayment\b", r"\binvoice\b", r"\bbilling\b",
             r"\bcredential", r"\btoken\b", r"\bauth\b", r"\birreversib", r"\boverwrit",
             r"\bclear\b", r"\bdrain", r"\blive\b", r"\bproduction\b", r"\bapi key\b"]


def _die(msg):
    print(f"CANNOT EVALUATE: {msg}", file=sys.stderr)
    sys.exit(CANNOT_EVALUATE)


def classify_tier(text):
    """Return (tier, scores, ambiguous). Mechanical. Reasoning is the default, not a guess."""
    scores = {t: sum(1 for p in pats if re.search(p, text, re.IGNORECASE))
              for t, pats in _TIER_SIGNALS.items()}
    top = max(scores.values())
    if top == 0:
        return "reasoning", scores, False          # no structural signal → prose by default
    leaders = [t for t, s in scores.items() if s == top]
    if len(leaders) > 1:
        # A genuine tie. Resolve toward REASONING when it is in contention — the same
        # fail-closed direction the enforceability fold uses. Landing an ambiguous clause
        # on `enforcement` would aim a guard at something that may be judgement; landing
        # it on `reasoning` aims a judge at it, which is the recoverable mistake.
        # (Alphabetical order, which this used to do, put `enforcement` first — exactly
        # backwards. Caught by the self-test.)
        pick = "reasoning" if "reasoning" in leaders else sorted(leaders)[0]
        return pick, scores, True
    return leaders[0], scores, False


def flag_critical(text):
    hits = [p for p in _CRITICAL if re.search(p, text, re.IGNORECASE)]
    return bool(hits), [re.sub(r"[\\\b]", "", p) for p in hits]


# ---------------------------------------------------------------- the LLM axis

# THE HUMAN-IN-THE-LOOP TEST (SOP §III.10, 2026-08-01) lives HERE, in the judge's
# prompt, and nowhere else in this file. It is a semantic test about judgment, so judgment
# about it belongs in the judge — not a regex. (A prior signature for "the success
# condition is in the future" scored 10/10 on a fixture its own author wrote, then produced
# 50% false positives on real clauses, and was reverted. That failure is why this stays prose
# aimed at the model, not a pattern aimed at the text.)
_PROMPT = """Classify each requirement into EXACTLY ONE category. This decides whether a
program will be allowed to hard-gate it, so err toward the softer category when unsure.

  "enforceable"          — a script could decide pass/fail without judgement: a required
                           section or artifact, an ordering, a count, a marker, a
                           forbidden item. Run THE HUMAN-IN-THE-LOOP TEST below first —
                           land here ONLY if all three checks come back NO.
  "human_in_the_loop"    — ANY ONE of the three checks below is YES. Real and important,
                           but ungateable — a false gate here is worse than no gate.
                           A human judges it, not a script.
  "uncheckable_nowhere"  — obeying it leaves NO trace in any output file. It happens in
                           the live conversation or a hook log. Grading it against a
                           produced artifact would be a FALSE failure.

THE HUMAN-IN-THE-LOOP TEST — a requirement needs a human in the loop if ANY of these
three is true. Check all three; they fail independently, and a requirement can pass the
first and still fail the second:
  1. BLIND TO OUTCOME — a computer can see that the action *happened*, but not whether it
     *achieved what the requirement asked for*.
  2. THE LOOP WON'T CLOSE — proving it worked takes longer than the run itself, OR the
     success condition is in the FUTURE (something that has not happened yet — e.g. "the
     next skill built" — so there is nothing to check against yet).
  3. NEEDS HUMAN CAPABILITY — even given time, judging it takes taste, intent, or
     "is this actually any good."
None of the three apply → enforceable. Any one applies → human_in_the_loop.

WORKED EXAMPLE, and it is the reason this test exists: "Every bug caught in a skill MUST
be encoded into the generator/template so the next skill is born immune." This LOOKS
enforceable — a computer CAN see that the template file changed. It is NOT enforceable:
it cannot see whether the next skill is actually immune (fails check 1) · the proof
arrives weeks later, and "the next skill" has not been born yet, so the success condition
is in the future (fails check 2) · and whether the fix generalises is a judgment (fails
check 3). THE TRAP THIS CATCHES: a requirement that POINTS AT AN ARTIFACT looks checkable,
while the thing it actually demands is a judgment about whether the artifact worked.
Pointing at a file is not the same as being checkable by one — classify this example, and
anything shaped like it, as human_in_the_loop.

Return ONLY a JSON array, same order as the input, one object per requirement:
[{"id": "<the id given>", "category": "enforceable|human_in_the_loop|uncheckable_nowhere"}]

REQUIREMENTS:
"""


def _vote_once(batch, model, timeout):
    payload = "\n".join(f'- id: {c["clause_id"]}\n  text: {c["text"]}' for c in batch)
    try:
        # judge_argv, not a hand-built command line: the classifier inherits whatever
        # blindness the machine can give it, and inherits the honesty when it cannot.
        p = subprocess.run(judge_argv(_PROMPT + payload, model),
                           capture_output=True, text=True, timeout=timeout,
                           cwd=os.path.expanduser("~"))
    except (OSError, subprocess.TimeoutExpired):
        return {}
    m = re.search(r"\[.*\]", p.stdout or "", re.DOTALL)
    if not m:
        return {}
    try:
        arr = json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}
    # normalized on the way in -- a model that still answers with the legacy `hill_climb`
    # spelling folds to the same category as one answering with the current name, so a vote
    # carries no trace of which prompt wording produced it.
    return {r["id"]: _normalize_enforceability(r["category"]) for r in arr
            if isinstance(r, dict) and r.get("id") and r.get("category") in VALID}


def fold(votes, k=None):
    """UNANIMOUS or it degrades. Returns (category, note).

    Not voted_judge's fold: there is no evidence/non-observation asymmetry in a category
    choice. What matters here is that disagreement NEVER lands on `enforceable`.

    A SHORT BALLOT IS NOT AGREEMENT (fixed 2026-07-28). Votes go missing for infrastructure
    reasons — a round times out, returns no JSON, or silently omits an id from its array.
    Before this, two returns from a k=3 run folded as `unanimous 2/2` while the row still
    stamped `k: 3`: an infra failure was INDISTINGUISHABLE FROM CONSENSUS, and the smaller
    the ballot the more likely it looked unanimous. An incomplete ballot is UNCLASSIFIED —
    surfaced and re-runnable, never quietly counted as a verdict.

    LEGACY VOTES NORMALIZE BEFORE THE COUNT. A vote cast as `hill_climb` (the pre-2026-08
    spelling, e.g. votes loaded from a frozen file via `refold`) and one cast as
    `human_in_the_loop` are the SAME category — normalizing first means a mixed ballot
    reads as agreement instead of a phantom split manufactured by spelling alone.
    """
    votes = [_normalize_enforceability(v) for v in votes]
    if k is not None and len(votes) < k:
        return UNCLASSIFIED, (f"INCOMPLETE BALLOT: {len(votes)} of {k} requested votes came back "
                              f"({votes or 'none'}) — an infra failure is not agreement")
    if not votes:
        return UNCLASSIFIED, "no usable votes"
    counts = {v: votes.count(v) for v in set(votes)}
    if len(counts) == 1:
        return votes[0], f"unanimous {len(votes)}/{len(votes)}"
    winner = max(counts, key=lambda v: counts[v])
    if winner == ENFORCEABLE:
        # the dangerous direction — a split must never authorise a hard gate
        return HUMAN_IN_THE_LOOP, (
            f"SPLIT {counts} — majority was 'enforceable' but not unanimous; "
            f"degraded to human_in_the_loop (a false gate on judgment is worse than none)")
    return winner, f"SPLIT {counts} — took {winner} (already the softer side)"


def apply_compound_cap(row, compound, split_by):
    """The compound cap (approved 2026-07-27): a rule that packs more than one
    obligation and was NOT cleanly split cannot be classified `enforceable` — it degrades
    to `human_in_the_loop`. You cannot hand a single gate a rule containing one checkable
    obligation and one uncheckable one: the gate either checks half while appearing to
    cover the whole, or overreaches onto the judgment half. A clause that came out of a
    clean split (split_by set) is atomic and exempt.

    Stated risk, on the record: this cap was proposed while it also happened to make a
    failed gate pass. It was approved with that caveat explicitly flagged."""
    if row["enforceability"] == ENFORCEABLE and compound and not split_by:
        row["enforceability"] = HUMAN_IN_THE_LOOP
        row["vote_note"] += (" | COMPOUND CAP: votes said enforceable, but the clause packs "
                             "multiple obligations and was not cleanly split — degraded "
                             "(a gate cannot cover half a rule honestly)")
        row["compound_capped"] = True
    else:
        row["compound_capped"] = False
    return row


def classify_batch(batch, k=3, model="sonnet", timeout=240, controls=None):
    """One batch, K rounds, folded. `controls` is a run_controls() result guarding it.

    A FLIPPED CONTROL VOIDS THE WHOLE BATCH. Not "lowers confidence" — voids. If the
    judge failed a question whose answer is not in dispute, its answers to the questions
    that ARE in dispute carry no information, and quietly keeping them is how a bent
    instrument's readings end up frozen into an artifact someone later cites.
    """
    if isinstance(controls, dict) and not controls.get("ok"):
        return {c["clause_id"]: {"enforceability": UNCLASSIFIED, "votes": [], "k": k,
                                 "vote_note": f"BATCH VOID — {controls['detail']}"}
                for c in batch}
    rounds = [_vote_once(batch, model, timeout) for _ in range(k)]
    out = {}
    for c in batch:
        cid = c["clause_id"]
        votes = [r[cid] for r in rounds if cid in r]
        cat, note = fold(votes, k=k)
        out[cid] = {"enforceability": cat, "votes": votes, "vote_note": note, "k": k}
    return out


# ------------------------------------------------------- the provenance stamp (P0.1)

def judge_provenance(use_llm, k, model, controls=None):
    """WHAT INSTRUMENT PRODUCED THESE NUMBERS — stamped into every frozen artifact.

    Derived mechanically from the environment, never hand-typed, because the whole reason
    this exists is that a hand-written claim ("blind clean-room judge") stayed in the
    codebase long after it stopped being true and silently authorised four separate
    results. A number without its instrument recorded beside it is not evidence.
    """
    if not use_llm:
        return {"MEASURED_WITH": "no-judge",
                "quarantined": False,
                "detail": "mechanical axes only (--no-llm); enforceability is UNCLASSIFIED"}
    m = judge_mode()
    void = isinstance(controls, dict) and not controls.get("ok")
    stamp = "VOID" if void else ("blind-judge" if m["blind"] else "contaminated-judge")
    return {"MEASURED_WITH": stamp,
            "quarantined": stamp != "blind-judge",
            "retake_required": stamp != "blind-judge",
            "judge_mode": m["mode"],
            "blind": m["blind"],
            "k": k,
            "model": model,
            "announce": m["announce"],
            "why": m["why"],
            "controls": controls,
            "detail": ("every LLM-derived field here was measured by a judge that can see "
                       "~/.claude/CLAUDE.md — treat these verdicts as QUARANTINED until "
                       "re-taken with a blind judge" if stamp == "contaminated-judge" else
                       "the control pair flipped — this run produced no reading at all"
                       if void else
                       "measured with a --bare judge that cannot see Lifehack")}


NON_NORMATIVE = "non_normative_section"


def classify(clauses, k=3, model="sonnet", use_llm=True, batch_size=12, controls=None):
    rows = []
    llm = {}

    # ── THE SECTION GATE, BEFORE ANY MODEL CALL (added 2026-07-29) ────────────────────
    #
    # A clause under a heading that declares its section is NOT IN FORCE -- "What Phase 0
    # Requires That Isn't Built Yet", "Open Question: ...", "do not act yet" -- cannot be
    # a runtime obligation, no matter how imperative the sentence reads on its own.
    #
    # ⭐ WHY THIS IS DETERMINISTIC AND NOT A BETTER PROMPT. The judge sees ONE clause at a
    # time. "3. The map-agent pipeline itself, with all four angles" contains NOTHING that
    # marks it as a backlog item -- the disqualifying fact lives three lines up, in a
    # heading the judge was never shown. Asking a model to infer absent information is how
    # you get a confident wrong answer. The heading is a FACT; read the fact.
    #
    # MEASURED (2026-07-28, planning-weekly): 10 of 34 build orders were not rules at all, 7 of
    # them items on that one backlog list. ~29% of that section's enforceable calls were
    # false, and every one manufactures a build order for a part nobody needs.
    #
    # Skipping the call is the cheap part; the point is CORRECTNESS. Doing it here rather
    # than downstream means the wrong answer is never produced, not produced-then-filtered.
    gated = {}
    to_judge = []
    for c in clauses:
        disq = c.get("non_normative_section")
        if disq:
            gated[c["clause_id"]] = {
                "enforceability": UNCHECKABLE, "votes": [], "k": 0,
                "vote_note": (f"SECTION GATE (no model call): this clause sits under the "
                              f"heading {disq!r}, which declares the section is not in "
                              "force. A backlog item, an open question, or a not-yet block "
                              "is not a runtime obligation -- there is nothing a gate could "
                              "check on any given run."),
            }
        else:
            to_judge.append(c)

    if use_llm and to_judge:
        for i in range(0, len(to_judge), batch_size):
            llm.update(classify_batch(to_judge[i:i + batch_size], k=k, model=model,
                                      controls=controls))
    llm.update(gated)

    # the compound test rides with extract_clauses when its flags are present; recomputed
    # here only for clause files that never went through extraction (e.g. hand-built sets)
    from extract_clauses import is_compound

    for c in clauses:
        tier, scores, ambiguous = classify_tier(c["text"])
        crit, why = flag_critical(c["text"])
        e = llm.get(c["clause_id"], {"enforceability": UNCLASSIFIED, "votes": [],
                                     "vote_note": "no LLM pass (--no-llm)", "k": 0})
        compound = c.get("compound_candidate", is_compound(c["text"]))
        rows.append(apply_compound_cap({
            "clause_id": c["clause_id"],
            "text": c["text"],
            "line": c.get("line"),
            "source_unit_ids": c.get("source_unit_ids", []),
            "enforceability": e["enforceability"],
            "enforceability_votes": e["votes"],
            "vote_note": e["vote_note"],
            "k": e["k"],
            # tier + critical only MEAN anything for an enforceable clause, but they are
            # always computed and kept — a later re-classification shouldn't re-derive them
            "tier": tier,
            "tier_scores": scores,
            "tier_ambiguous": ambiguous,
            "instrument": {"reasoning": "voted LLM judge",
                           "enforcement": "provoke the guard and assert it blocks",
                           "state": "native-id set-diff vs the source"}[tier],
            "critical": crit,
            "critical_signals": why,
            "needs_human": crit or ambiguous,
        }, compound, c.get("split_by")))
    return rows


# ---------------------------------------------------------------- refold (P0.1)

def refold(payload):
    """Re-run the CURRENT fold + cap over votes ALREADY CAST — free, no API calls.

    THIS IS NOT A RE-MEASUREMENT, and the artifact must never let a reader think it is.
    The ballots were cast by whatever judge cast them; re-folding cannot clean a
    contaminated vote, so the file KEEPS its original `MEASURED_WITH` and merely gains an
    honest record of what today's code makes of yesterday's votes.

    It exists because a frozen artifact and a commit message disagreed: the file said
    3 of 19 FAIL and the commit claimed 0 of 19, because the number was recomputed in a
    session and never written down. A claim nobody can re-derive from the file is not a
    result. Now anyone can re-derive it in one command.

    Every row records BOTH numbers — the raw fold of the votes AND the post-cap verdict —
    so a headline can never be quoted without the thing that produced it.
    """
    from extract_clauses import is_compound

    rows, raw_tally, capped_tally, capped_ids = [], {}, {}, []
    for r in payload["rows"]:
        votes = r.get("enforceability_votes", [])
        k = r.get("k") or len(votes)
        raw_cat, raw_note = fold(votes, k=k)
        row = dict(r)
        row["enforceability_raw"] = raw_cat
        row["enforceability_raw_note"] = raw_note
        row["enforceability"] = raw_cat
        row["vote_note"] = raw_note
        compound = is_compound(r["text"])
        row["compound_candidate"] = compound
        # the source sets are hand-built and unsplit; recorded, not assumed silently
        row["split_by"] = r.get("split_by")
        row = apply_compound_cap(row, compound, row["split_by"])
        raw_tally[raw_cat] = raw_tally.get(raw_cat, 0) + 1
        capped_tally[row["enforceability"]] = capped_tally.get(row["enforceability"], 0) + 1
        if row.get("compound_capped"):
            capped_ids.append(row["clause_id"])
        rows.append(row)

    out = dict(payload)
    out["rows"] = rows
    out["refold"] = {
        "what_ran": "the current fold + compound cap, re-applied to the STORED votes",
        "what_did_NOT_run": "the judge — no new API calls, no new measurement",
        "raw_tally": raw_tally,
        "capped_tally": capped_tally,
        "compound_capped_clauses": capped_ids,
        "read_both_numbers": (
            f"raw votes → {raw_tally.get(ENFORCEABLE, 0)} enforceable; "
            f"after the compound cap → {capped_tally.get(ENFORCEABLE, 0)}. "
            "The cap's detector (`is_compound`) is KNOWINGLY BROKEN — it fires on a "
            "semicolon (`A or B`, not the two independent signals its docstring claims), "
            "and it is left broken deliberately (plan P1.5.3: you cannot diagnose a "
            "detector while its grader is bent). So the post-cap number is NOT an "
            "independent confirmation of the raw one — it is the same result with a "
            "punctuation rule applied on top."),
    }
    return out


# ---------------------------------------------------------------- the canary (S1.5)

CANARY = [
    {"clause_id": "canary_c01", "expect": ENFORCEABLE,
     "text": "The Win is not named until Phase 3."},
    {"clause_id": "canary_c02", "expect": HUMAN_IN_THE_LOOP,
     "text": "Generate the round's leveraged questions from the pad, biggest-first."},
    {"clause_id": "canary_c03", "expect": UNCHECKABLE,
     "text": "Questions asked of the user in the live conversation are numbered, and the "
             "numbering appears only in the conversation, never written to any file."},
]


def run_canary(k=3, model="sonnet"):
    res = classify_batch([{k2: v for k2, v in c.items() if k2 != "expect"} for c in CANARY],
                         k=k, model=model)
    ok = True
    print(f"classify_clause --canary  (LIVE, k={k}, model={model})")
    for c in CANARY:
        got = res[c["clause_id"]]["enforceability"]
        good = got == c["expect"]
        ok = ok and good
        print(f"  [{'PASS' if good else 'FAIL'}] expected {c['expect']:<20} got {got:<20} "
              f"{res[c['clause_id']]['vote_note']}")
        print(f"          {c['text'][:88]}")
    print("CANARY:", "PASS" if ok else "FAIL — the sorter does not know what it is looking at")
    return 0 if ok else 1


# ---------------------------------------------------------------- self-test

def selftest():
    ok = True

    def report(label, passed, detail=""):
        nonlocal ok
        ok = ok and passed
        print(f"  [{'PASS' if passed else 'FAIL'}] {label}{(' -- ' + detail) if detail else ''}")

    print("classify_clause --selftest  (mechanical axes + the fold — no API calls)")

    # ── tier: the instrument selector ──
    report("a completeness requirement is STATE tier",
           classify_tier("the Map must account for every item in the source corpus")[0] == "state")
    report("an ordering/marker requirement is ENFORCEMENT tier",
           classify_tier("the phase 2 complete marker is written only after the check")[0]
           == "enforcement")
    report("a judgement requirement is REASONING tier",
           classify_tier("surface the real tension without naming an alternative")[0] == "reasoning")
    report("no signal at all defaults to reasoning (prose), not a guess",
           classify_tier("the session proceeds")[0] == "reasoning")
    # "never" scores enforcement, "confirm" scores reasoning — a real 1-1 tie.
    tie = classify_tier("never confirm the decision")
    report("a genuine tie is RECORDED ambiguous, not silently picked", tie[2] is True,
           f"scores={tie[1]}")
    report("a tie resolves toward REASONING, not toward a guard (fail-closed)",
           tie[0] == "reasoning", f"picked {tie[0]}")
    report("each tier carries its instrument",
           classify([{"clause_id": "x", "text": "set-diff every source id"}],
                    use_llm=False)[0]["instrument"] == "native-id set-diff vs the source")

    # ── critical ──
    report("a live write is flagged critical",
           flag_critical("the clerk writes each row to the live calendar")[0])
    report("a read-only requirement is not flagged critical",
           not flag_critical("surface the tension in the plan")[0])
    report("a critical clause is routed to the human batch",
           classify([{"clause_id": "x", "text": "send the draft email"}],
                    use_llm=False)[0]["needs_human"])

    # ── THE FOLD — the dangerous direction ──
    report("unanimous enforceable stays enforceable",
           fold([ENFORCEABLE] * 3)[0] == ENFORCEABLE)
    cat, note = fold([ENFORCEABLE, ENFORCEABLE, HUMAN_IN_THE_LOOP])
    report("a SPLIT that merely favours 'enforceable' degrades to human_in_the_loop",
           cat == HUMAN_IN_THE_LOOP, note[:60])
    report("a split away from enforceable keeps the softer side",
           fold([HUMAN_IN_THE_LOOP, HUMAN_IN_THE_LOOP, UNCHECKABLE])[0] == HUMAN_IN_THE_LOOP)
    report("no usable votes -> UNCLASSIFIED, never a guess",
           fold([])[0] == UNCLASSIFIED)

    # ── THE RENAME (2026-08-01): a vote cast under the LEGACY `hill_climb` spelling must
    # fold identically to one cast under the current `human_in_the_loop` name, including
    # when the two are mixed in the same ballot -- exactly what a re-fold of a frozen file
    # produces once this code changed underneath votes it didn't cast. ──
    report("a ballot of LEGACY 'hill_climb' votes folds to the current name, not the old one",
           fold([HILL_CLIMB_LEGACY] * 3)[0] == HUMAN_IN_THE_LOOP)
    cat, note = fold([HILL_CLIMB_LEGACY, HUMAN_IN_THE_LOOP, HUMAN_IN_THE_LOOP])
    report("a MIXED legacy + current ballot reads as unanimous agreement, not a phantom split",
           cat == HUMAN_IN_THE_LOOP and "unanimous" in note, note)
    report("a legacy vote against an enforceable majority still degrades correctly",
           fold([ENFORCEABLE, ENFORCEABLE, HILL_CLIMB_LEGACY])[0] == HUMAN_IN_THE_LOOP)

    # ── THE SHORT BALLOT — an infra failure must never read as agreement ──
    cat, note = fold([ENFORCEABLE, ENFORCEABLE], k=3)
    report("2 votes back from a k=3 run is UNCLASSIFIED, not 'unanimous 2/2'",
           cat == UNCLASSIFIED and "INCOMPLETE BALLOT" in note, note[:60])
    report("a full ballot is unaffected by the check",
           fold([ENFORCEABLE] * 3, k=3)[0] == ENFORCEABLE)
    report("the incomplete-ballot note reports the real counts",
           "2 of 3" in fold([HUMAN_IN_THE_LOOP, HUMAN_IN_THE_LOOP], k=3)[1])
    report("a short ballot cannot even reach the SOFT side by accident",
           fold([HUMAN_IN_THE_LOOP], k=3)[0] == UNCLASSIFIED)
    report("k=None (a pure fold with no ballot claim) still folds normally",
           fold([ENFORCEABLE] * 2)[0] == ENFORCEABLE)
    report("--no-llm leaves enforceability UNCLASSIFIED rather than defaulting",
           classify([{"clause_id": "x", "text": "anything"}],
                    use_llm=False)[0]["enforceability"] == UNCLASSIFIED)

    # ── THE COMPOUND CAP (approved 2026-07-27) ──
    def _row(cat):
        return {"enforceability": cat, "vote_note": "unanimous 3/3"}
    r = apply_compound_cap(_row(ENFORCEABLE), compound=True, split_by=None)
    report("an UNSPLIT compound that votes enforceable is CAPPED to human_in_the_loop",
           r["enforceability"] == HUMAN_IN_THE_LOOP and r["compound_capped"])
    r = apply_compound_cap(_row(ENFORCEABLE), compound=True, split_by="sonnet")
    report("a CLEANLY-SPLIT part keeps its enforceable verdict (atomic is exempt)",
           r["enforceability"] == ENFORCEABLE and not r["compound_capped"])
    r = apply_compound_cap(_row(ENFORCEABLE), compound=False, split_by=None)
    report("an atomic clause is untouched by the cap",
           r["enforceability"] == ENFORCEABLE and not r["compound_capped"])
    r = apply_compound_cap(_row(HUMAN_IN_THE_LOOP), compound=True, split_by=None)
    report("the cap never touches a non-enforceable verdict",
           r["enforceability"] == HUMAN_IN_THE_LOOP and not r["compound_capped"])

    # ── THE PROVENANCE STAMP — a number must never travel without its instrument ──
    p_none = judge_provenance(use_llm=False, k=0, model="sonnet")
    report("a mechanical-only run is stamped no-judge and is NOT quarantined",
           p_none["MEASURED_WITH"] == "no-judge" and not p_none["quarantined"])
    p_live = judge_provenance(use_llm=True, k=3, model="sonnet")
    report("a judged run stamps the REAL judge mode, not an aspiration",
           p_live["MEASURED_WITH"] in ("blind-judge", "contaminated-judge")
           and p_live["blind"] == judge_mode()["blind"], p_live["MEASURED_WITH"])
    report("a non-blind judge's output is marked QUARANTINED + retake_required",
           judge_mode()["blind"] or (p_live["quarantined"] and p_live["retake_required"]))
    p_void = judge_provenance(True, 3, "sonnet", controls={"ok": False, "detail": "flipped"})
    report("flipped controls stamp the whole run VOID, not merely uncertain",
           p_void["MEASURED_WITH"] == "VOID")

    # ── A VOID BATCH: no row may keep a verdict a broken instrument produced ──
    voided = classify_batch([{"clause_id": "z", "text": "anything"}], k=3,
                            controls={"ok": False, "detail": "CONTROLS FLIPPED"})
    report("a flipped control voids every row in the batch (no API call is even made)",
           voided["z"]["enforceability"] == UNCLASSIFIED
           and "BATCH VOID" in voided["z"]["vote_note"])

    # ── REFOLD: re-derive from stored votes, and never launder the provenance ──
    stored = {"slug": "fx", "k": 3, "rows": [
        {"clause_id": "r1", "text": "the report must contain a TOTAL line",
         "enforceability": ENFORCEABLE, "enforceability_votes": [ENFORCEABLE] * 3, "k": 3,
         "vote_note": "unanimous 3/3"},
        {"clause_id": "r2", "text": "expose one front door; hide the machinery behind it",
         "enforceability": ENFORCEABLE, "enforceability_votes": [ENFORCEABLE] * 3, "k": 3,
         "vote_note": "unanimous 3/3"},
        {"clause_id": "r3", "text": "surface the real tension",
         # LEGACY-TAGGED, on purpose: this row simulates exactly what a real frozen file
         # dated before 2026-08-01 holds -- both the stored verdict AND its cast votes
         # spelled the old way. refold() must still read it correctly.
         "enforceability": HILL_CLIMB_LEGACY, "enforceability_votes": [HILL_CLIMB_LEGACY] * 3,
         "k": 3, "vote_note": "unanimous 3/3"}]}
    rf = refold(stored)
    report("refold keeps the RAW verdict beside the capped one (both numbers survive)",
           all("enforceability_raw" in r for r in rf["rows"]))
    r2 = next(r for r in rf["rows"] if r["clause_id"] == "r2")
    report("a semicolon clause is capped, and says so",
           r2["enforceability_raw"] == ENFORCEABLE and r2["enforceability"] == HUMAN_IN_THE_LOOP
           and r2["compound_capped"])
    r1 = next(r for r in rf["rows"] if r["clause_id"] == "r1")
    report("an atomic clause keeps its raw verdict through the refold",
           r1["enforceability"] == ENFORCEABLE and not r1["compound_capped"])
    r3 = next(r for r in rf["rows"] if r["clause_id"] == "r3")
    report("a row FROZEN under the legacy spelling refolds to the current name, not the old one",
           r3["enforceability_raw"] == HUMAN_IN_THE_LOOP
           and r3["enforceability"] == HUMAN_IN_THE_LOOP, r3["enforceability_raw"])
    report("the refold reports BOTH tallies, so a headline cannot be quoted alone",
           rf["refold"]["raw_tally"][ENFORCEABLE] == 2
           and rf["refold"]["capped_tally"][ENFORCEABLE] == 1)
    report("the refold names the cap's broken detector instead of hiding behind it",
           "is_compound" in rf["refold"]["read_both_numbers"]
           and "KNOWINGLY BROKEN" in rf["refold"]["read_both_numbers"])
    report("a refold makes NO new measurement and says so",
           "no new API calls" in rf["refold"]["what_did_NOT_run"])
    # the short-ballot fix reaches refolded rows too
    short = refold({"slug": "fx", "k": 3, "rows": [
        {"clause_id": "s1", "text": "atomic thing", "enforceability": ENFORCEABLE,
         "enforceability_votes": [ENFORCEABLE, ENFORCEABLE], "k": 3}]})
    report("refolding a SHORT ballot re-reads it as UNCLASSIFIED, not as a verdict",
           short["rows"][0]["enforceability"] == UNCLASSIFIED)

    # ── CLI ──
    me = os.path.abspath(__file__)
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, "c.json")
        with open(f, "w") as fh:
            json.dump({"clauses": [{"clause_id": "a_unit_000001_c01",
                                    "text": "the map must cover every source item",
                                    "line": 1, "source_unit_ids": ["a_unit_000001"]}]}, fh)
        p = subprocess.run([sys.executable, me, "--clauses", f, "--no-llm"],
                           capture_output=True, text=True)
        report("CLI --no-llm -> exit 0", p.returncode == OK, f"exit {p.returncode}")
        p = subprocess.run([sys.executable, me, "--clauses", os.path.join(td, "nope.json")],
                           capture_output=True, text=True)
        report("CLI missing clause file -> exit 2 (fail-closed)",
               p.returncode == CANNOT_EVALUATE, f"exit {p.returncode}")

    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description="classify_clause -- the three-field sort")
    ap.add_argument("--clauses", help="frozen clause JSON from extract_clauses.py")
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--batch-size", type=int, default=12)
    ap.add_argument("--no-llm", action="store_true",
                    help="mechanical axes only; enforceability stays UNCLASSIFIED")
    ap.add_argument("--out", help="write <slug>-classified.json here")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--canary", action="store_true", help="LIVE 3-clause gate (costs API)")
    ap.add_argument("--refold", metavar="CLASSIFIED.json",
                    help="re-apply the CURRENT fold + cap to already-cast votes (free)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())
    if args.refold:
        if not os.path.isfile(args.refold):
            _die(f"classified file not found: {args.refold!r}")
        try:
            src = json.loads(open(args.refold, encoding="utf-8").read())
        except json.JSONDecodeError as e:
            _die(f"classified file is not valid JSON: {e}")
        if not src.get("rows"):
            _die("classified file holds ZERO rows — nothing to refold")
        out = refold(src)
        # A refold NEVER upgrades provenance: the votes are as contaminated as they were.
        prov = dict(src.get("provenance") or {})
        prov.setdefault("MEASURED_WITH", "contaminated-judge")
        prov.setdefault("quarantined", True)
        prov.setdefault("retake_required", True)
        prov.setdefault("why", "measured before the blindness fix — see plan Phase 0 / P0.1")
        prov["refolded"] = ("the FOLD was re-run with corrected code; the MEASUREMENT was "
                            "not — this stamp is inherited, never upgraded by a refold")
        out["provenance"] = prov
        dest = os.path.join(args.out, os.path.basename(args.refold)) if args.out else args.refold
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=2, ensure_ascii=False)
        rf = out["refold"]
        print(f"refold — {out.get('slug')}  ({len(out['rows'])} rows, NO API calls)")
        print(f"  MEASURED_WITH: {prov['MEASURED_WITH']}  (quarantined={prov['quarantined']})")
        print(f"  raw fold of the stored votes: {rf['raw_tally']}")
        print(f"  after the compound cap:       {rf['capped_tally']}")
        if rf["compound_capped_clauses"]:
            print(f"  capped by the compound rule ({len(rf['compound_capped_clauses'])}):")
            for c in rf["compound_capped_clauses"]:
                print(f"      {c}")
        print(f"  ⚠ {rf['read_both_numbers']}")
        print(f"  written: {dest}")
        sys.exit(OK)
    if args.canary:
        sys.exit(run_canary(k=args.k, model=args.model))
    if not args.clauses:
        _die("--clauses is required")
    if not os.path.isfile(args.clauses):
        _die(f"clause file not found: {args.clauses!r}")
    try:
        data = json.loads(open(args.clauses, encoding="utf-8").read())
    except json.JSONDecodeError as e:
        _die(f"clause file is not valid JSON: {e}")
    clauses = data.get("clauses") if isinstance(data, dict) else data
    if not clauses:
        _die("clause file holds ZERO clauses — refusing to classify a vacuous set")

    # ONE control run for the whole sort (not one per batch: the question "is the judge
    # reading right now" is a property of the run, and per-batch controls would triple
    # the bill to re-answer it). Run BEFORE any real votes, so a dead judge costs one
    # control pair instead of a whole spec.
    controls = None
    if not args.no_llm and judge_mode()["controls_required"]:
        controls = run_controls(model=args.model, k=args.k)
        print(f"  controls: {controls['detail']}")

    rows = classify(clauses, k=args.k, model=args.model, use_llm=not args.no_llm,
                    batch_size=args.batch_size, controls=controls)

    slug = data.get("slug", "spec") if isinstance(data, dict) else "spec"
    payload = {"slug": slug, "source": os.path.basename(args.clauses),
               "k": 0 if args.no_llm else args.k,
               "provenance": judge_provenance(not args.no_llm, args.k, args.model, controls),
               "rows": rows}
    if args.out:
        os.makedirs(args.out, exist_ok=True)
        path = os.path.join(args.out, f"{slug}-classified.json")
        if os.path.exists(path):
            # Fail closed: an existing file at this path may be a frozen measurement
            # record. A collision is never permission to overwrite -- refuse loudly
            # rather than silently falsify whatever was measured there before.
            _die(f"refusing to overwrite existing file: {path!r} "
                 f"-- pass a different --out directory, or move/rename the existing "
                 f"file first if you really mean to replace it")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
        payload["frozen"] = path

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        tally = {}
        for r in rows:
            tally[r["enforceability"]] = tally.get(r["enforceability"], 0) + 1
        tiers = {}
        for r in rows:
            tiers[r["tier"]] = tiers.get(r["tier"], 0) + 1
        print(f"classify_clause — {slug}  ({len(rows)} clauses, k={payload['k']})")
        # the instrument, before the numbers — a reader must never meet a verdict here
        # without meeting what produced it first
        prov = payload["provenance"]
        print(f"  MEASURED_WITH: {prov['MEASURED_WITH']}"
              + ("  ⚠ QUARANTINED" if prov.get("quarantined") else ""))
        if prov.get("announce"):
            print(f"  {prov['announce']}")
        print("  enforceability:")
        for kk, v in sorted(tally.items(), key=lambda x: -x[1]):
            print(f"      {kk:<22} {v}")
        print("  tier (the instrument selector):")
        for kk, v in sorted(tiers.items(), key=lambda x: -x[1]):
            print(f"      {kk:<22} {v}")
        print(f"  critical (needs a human yes/no): {sum(r['critical'] for r in rows)}")
        print(f"  tier ambiguous (recorded, not guessed): {sum(r['tier_ambiguous'] for r in rows)}")
        splits = [r for r in rows if "SPLIT" in r["vote_note"]]
        if splits:
            print(f"  ⚠ {len(splits)} split vote(s) — every one degraded away from 'enforceable'")
        if payload.get("frozen"):
            print(f"  frozen to: {payload['frozen']}")

    unresolved = [r for r in rows if r["enforceability"] == UNCLASSIFIED and not args.no_llm]
    if unresolved:
        print(f"  ⚠ {len(unresolved)} clause(s) UNCLASSIFIED — surfaced, not defaulted.")
    sys.exit(UNRESOLVED if unresolved else OK)


if __name__ == "__main__":
    main()

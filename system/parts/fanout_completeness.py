#!/usr/bin/env python3
"""fanout_completeness — native-id coverage set-diffed at the FAN-OUT RETURN BOUNDARY,
never at phase exit.  [Parts Library · combines A4 (completeness_receipt) + B3 (fanout_gate)]

WHEN: a controller fans sub-agents out over a bounded source-id set (email threads, tasks,
      calendar items, ...) and must know -- at the moment the sub-agents RETURN, before any
      further synthesis touches their output -- whether every source id was traceably
      covered by SOMETHING a sub-agent actually returned.

WHAT: reads the CAPTURED fan-out records (fanout_gate's own shape: a JSON list of
      {agent_id, agentType, description, final_text}), pins the source-id denominator, and
      set-diffs the UNION of native-id citations across every captured record's final_text
      against that denominator.

WHY:  measured, real run, week 2026-W30. cal-weekly fanned sub-agents out to read the
      week's email and return a distilled world-model; the distillation lost signal --
      5 signal-missed threads out of 28 read, the worst a high-signal thread
      carrying ZERO coaching context through, on the exact lane the locked weekly Win said
      to protect. `completeness_receipt.py`'s own docstring names the SAME shape of loss on
      the SAME skill, measured on the frozen W30 Map: a blind judge read a Map built from
      241 source items and passed it as "omitting nothing"; a mechanical set-diff found
      only 20 of 241 traceably covered -- and states outright: "fire at the loss point ...
      never at phase exit, where the drop is already invisible."

      A phase-exit completeness check compares the FINAL artifact (the synthesized Map /
      world-model) against a denominator -- but the artifact it is checking is itself
      DOWNSTREAM of the exact synthesis step that did the dropping. By the time a receipt
      runs against the Map, the coaching thread's content has already been silently left
      out of what fed the Map, and the receipt has nothing left to diff it against: it
      would green-light this precise miss, because both sides of its comparison were built
      after the drop already happened.

      This part's whole reason to exist is to be UN-CALLABLE at that late seam. Its one
      input format IS the raw captured sub-agent RETURNS -- the fan-out's own output, at
      the boundary where it hands control back to the main run -- so there is no wiring
      that lets a caller point it at anything already synthesized. `completeness_receipt`
      proves an ARTIFACT accounts for a source; this part proves the FAN-OUT'S OWN RETURNS
      did, before anything downstream gets a chance to lose what they held.

DELEGATION (Parts Library Rule 1's sanctioned exception -- a REQUIRED sibling subprocess,
      never a fallback). The citation/reachability logic (direct citation, covering
      recurring-base, unambiguous truncation, ambiguous-prefix refusal, optional
      --require-substance) is `completeness_receipt.py`'s -- proven, self-tested, and
      differentially checked against this same W30 incident already. Reimplementing that
      logic here would be a second, divergent copy of exactly the reachability rules Law
      4.1 says must be gotten right once. If the sibling is not deployed beside this part,
      this part refuses (CANNOT EVALUATE) rather than silently degrading to a weaker check
      -- a missing sibling is exit 2, never a fallback path (README rule 1).

      What THIS part owns and the sibling does not: (a) ingesting the CAPTURED fan-out
      record shape rather than a single markdown artifact, (b) the identification and
      quiescence hygiene borrowed from `fanout_gate.py` -- an unidentified, duplicated, or
      un-settled capture must refuse before a coverage question is even asked of it,
      because a coverage verdict over a broken capture is meaningless (SOP §V.5: a broken
      seam does not crash, it produces a confident, well-formatted, WRONG verdict), and
      (c) unioning every identified record's own return before handing the sibling one
      artifact to grade -- the union IS the fan-out's total evidence at the return
      boundary, nothing more and nothing less.

⚠ KNOWN BOUND (inherited from the sibling, stated here because it applies to this part's
      verdict too): this proves CITATION coverage across the fan-out's own returns, not
      that a covered id's content is FAITHFUL or complete -- a bare id-dump in one return
      still "covers" everything it names. Pass --require-substance (forwarded to the
      sibling) wherever the governing rule says a return must "account for," not merely
      mention, what it was handed.

⚠ KNOWN BOUND (this part's own): identity hygiene trusts `agent_id`/`agentType` as an
      honest account of what fired -- if the capture mechanism itself can be forged, this
      part cannot see that (the same one-directional trust `bounded_input.py` documents
      about its own `--processed` input). Pair with a capture mechanism that is not
      model-writable.

USAGE
  fanout_completeness.py --captured C.json --source-ids IDS.json --quiesced [--declared N]
  fanout_completeness.py --captured C.json --source-ids IDS.json --quiesced --json
  fanout_completeness.py --captured C.json --source-ids IDS.json --quiesced --ledger-scope
  fanout_completeness.py --selftest

SCAN SCOPE (S10.5, 2026-08-04 -- measurement-bias fix): the citation scan's default is
  SCAN_WHOLE -- every captured return is scanned over the SAME surface (the whole
  final_text), whether or not a '### Coverage ledger' heading is present. This is PINNED
  and applies identically to every input; it is what any scoring lab gets unless it opts
  out. --ledger-scope restores the LEGACY, narrower, heading-conditioned scan (only text at
  or after the heading, falling back to the whole text -- announced, not silent -- when no
  heading is found) for backward-compatible callers that always ship a heading. Every
  verdict states which scope it used (`"scan_scope"` in --json; a `[scan_scope=...]` tag in
  the human-readable render). Do not select --ledger-scope where the heading's own
  presence/absence may be the thing under test -- that reopens the exact bias this fixes:
  a cell that removes the ledger would earn a wider (or, under a stricter legacy rewrite,
  narrower) scan than its control. Two denominators, one ruler, is fatal to a comparison.

EXIT CODES (the part contract) -- S10.4 split what used to be ONE exit code for three
distinct failure modes, forcing a runtime judgment call. Measured, real run 2026-08-03:
`242/242 source ids covered · 0 missing · 1 alien (['calendar_name'])` still returned the
OLD single LOSS code -- perfect coverage, zero loss, and it halted anyway, because the
prescribed remedy for exit 1 ("re-dispatch a map-agent for the named ids") is incoherent
for an alien: there is no source item to re-dispatch for.
  0  COMPLETE       -- every source id is traceably covered by the UNION of captured returns
  1  LOSS            -- one or more source ids are MISSING from coverage (never traceably
                        cited by ANY captured return), OR a citation carries no accompanying
                        prose under --require-substance (a bare id-dump is graded the same
                        as a miss -- see completeness_receipt's own KNOWN BOUND). A real
                        finding at the loss point. Do NOT assemble, do NOT proceed.
                        NOTE on "duplicated": a duplicate `agent_id` among the CAPTURED
                        records is this part's OWN identification hygiene (identify()),
                        checked BEFORE any coverage question is asked, and it already
                        landed in CANNOT EVALUATE (2), never here -- the previous version of
                        this table listed "duplicated" under LOSS, which the code never
                        actually did; that was a documentation error, now corrected.
  3  ALIEN           -- ZERO source ids missing, but one or more citations name something
                        NOT in the source (e.g. a JSON field name quoted in an honest
                        methodological note). REPORTS LOUDLY -- every alien id is named in
                        the reason text -- but this is NOT a halt condition: there is no
                        source item to re-dispatch a map-agent for, so the driver's "on
                        exit 1: do not proceed" rule must not apply to this code.
  2  CANNOT EVALUATE -- missing file, empty source, unidentified/duplicated/un-quiesced
                        capture, zero identified records, denominator mismatch, or the
                        required sibling part is not deployed beside this one. Fail-closed.

CAPTURED FILE: [{"agent_id": "...", "agentType": "...", "description": "...",
                 "final_text": "..."}, ...]   (or {"records": [...]})   -- fanout_gate's shape
SOURCE-IDS FILE: ["id", ...]  or  {"source_ids": [...]}  or  {"items": [{"item_id": ...}]}
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

COMPLETE, LOSS, CANNOT_EVALUATE = 0, 1, 2
ALIEN = 3  # S10.4: zero missing + one-or-more alien citations -- report loudly, never halt

HERE = os.path.dirname(os.path.abspath(__file__))
SIBLING = "completeness_receipt.py"

# S10.5 (2026-08-04): measurement-bias fix. SCAN_WHOLE is the PINNED, SYMMETRIC default --
# every captured return is scanned over the SAME surface (the whole final_text), whether or
# not a '### Coverage ledger' heading is present. This is required whenever the heading's
# own presence/absence may itself be the thing under test (a lab cell that removes the
# ledger from the format must not thereby earn a WIDER citation-scan surface than its
# control -- two denominators is not one ruler). SCAN_LEDGER is the legacy, OPT-IN, narrower
# scope for backward-compatible callers that always ship a heading and want prose ABOVE it
# excluded from the scan (the S10.4 fix this file already carries) -- selected explicitly via
# --ledger-scope, never silently.
SCAN_WHOLE = "whole"
SCAN_LEDGER = "ledger"


def _die(msg):
    print(f"CANNOT EVALUATE: {msg}", file=sys.stderr)
    sys.exit(CANNOT_EVALUATE)


# ---------------------------------------------------------------- loading

def load_records(path):
    raw = json.loads(open(path, encoding="utf-8").read())
    return raw.get("records", []) if isinstance(raw, dict) else list(raw)


def load_source_ids(path):
    raw = json.loads(open(path, encoding="utf-8").read())
    if isinstance(raw, dict):
        return raw.get("source_ids") or [i["item_id"] for i in raw.get("items", [])]
    return list(raw)


# ---------------------------------------------------------------- identification hygiene
# Borrowed from fanout_gate.py's own §V.4b hardening: a captured record with no agent_id
# or agentType identifies nothing, and a duplicated agent_id can inflate coverage the same
# way it can inflate a count. Neither question -- "did enough agents run" vs "did their
# combined returns cover the source" -- can be trusted from a capture that fails this first.

def identify(records):
    """Return (identified, unidentified, dupe_ids). Never raises."""
    unidentified = [f"#{i}" for i, r in enumerate(records, 1)
                    if not str(r.get("agent_id") or "").strip()
                    or not str(r.get("agentType") or "").strip()]
    ids = [str(r.get("agent_id")).strip() for r in records
           if str(r.get("agent_id") or "").strip()]
    dupe_ids = sorted({i for i in ids if ids.count(i) > 1})
    identified = [r for r in records
                  if str(r.get("agent_id") or "").strip()
                  and str(r.get("agentType") or "").strip()]
    return identified, unidentified, dupe_ids


LEDGER_HEADING = re.compile(r"^###\s*Coverage ledger\b.*$", re.IGNORECASE | re.MULTILINE)


def _scope_text(text, scan_scope):
    """Return (scoped_text, scope_used) for ONE record's final_text.

    S10.5 (2026-08-04): the scope decision must not itself depend on the very thing an
    experiment may be varying (whether a '### Coverage ledger' heading is present). Two
    modes, chosen ONLY by the caller-supplied scan_scope -- never inferred per-record:

      SCAN_WHOLE  (the pinned, SYMMETRIC default) -- always the whole text, heading or not.
                  scope_used is always "whole". This is the surface every lab run gets by
                  default, so a cell that removes the ledger heading cannot thereby earn a
                  wider (or narrower) scan than its control -- same ruler, both cells.

      SCAN_LEDGER (legacy, opt-in, --ledger-scope) -- S10.4's narrower behaviour: only text
                  AT OR AFTER the heading is offered to the sibling's citation extractor,
                  so a methodological note ABOVE the heading (e.g. a backticked JSON field
                  name) is never misread as a citation. If no heading is found, this mode
                  falls back to the whole text -- but ANNOUNCES the fallback (scope_used
                  "whole-fallback") rather than silently widening the scan. This mode exists
                  for backward-compatible callers that always ship a heading; it must never
                  be the default, because its own scope varies with heading presence -- the
                  exact bias S10.5 fixes.
    """
    if scan_scope == SCAN_LEDGER:
        m = LEDGER_HEADING.search(text or "")
        if m:
            return text[m.start():], SCAN_LEDGER
        return text or "", "whole-fallback"
    return text or "", SCAN_WHOLE


def union_text(records, scan_scope=SCAN_WHOLE):
    """The fan-out's TOTAL evidence at the return boundary -- every identified record's
    own final_text, labeled by which agent returned it, in a deterministic order.

    Returns (union, fallback_labels). scan_scope picks the per-record scoping rule (see
    _scope_text) and is applied IDENTICALLY to every record -- no per-record branching on
    whether that record happens to carry a heading. fallback_labels names every record that
    hit the SCAN_LEDGER mode's "whole-fallback" case (never populated under the default
    SCAN_WHOLE, since that mode has no fallback to report -- it always scans everything)."""
    blocks = []
    fallback_labels = []
    for r in sorted(records, key=lambda r: (r.get("description") or "", r.get("agent_id") or "")):
        label = (r.get("description") or "").strip() or str(r.get("agent_id"))
        text = (r.get("final_text") or "").strip()
        scoped, scope_used = _scope_text(text, scan_scope)
        if scope_used == "whole-fallback":
            fallback_labels.append(label)
        blocks.append(f"### sub-agent return — {label} (agent_id: {r.get('agent_id')})\n{scoped}\n")
    return "\n".join(blocks), fallback_labels


# ---------------------------------------------------------------- delegation to the sibling

def _sibling_grade(source_ids_path, union, declared_count, require_substance, here):
    """Delegate the citation/reachability set-diff to completeness_receipt.py.
    Raises RuntimeError on ANY failure to evaluate -- caller folds that into CANNOT_EVALUATE.
    """
    sib = os.path.join(here, SIBLING)
    if not os.path.isfile(sib):
        raise RuntimeError(
            f"this check requires the sibling part {SIBLING!r} beside fanout_completeness.py "
            f"({here}) -- the id-coverage reachability rules (direct citation / covering "
            f"recurring-base / unambiguous truncation / ambiguous-prefix refusal) live there "
            f"and are deliberately not reimplemented here. Deploy both parts together.")
    with tempfile.TemporaryDirectory() as td:
        ap = os.path.join(td, "captured-union.md")
        with open(ap, "w", encoding="utf-8") as fh:
            fh.write(union)
        argv = [sys.executable, sib, "--artifact", ap, "--source-ids", source_ids_path, "--json"]
        if declared_count is not None:
            argv += ["--declared", str(declared_count)]
        if require_substance:
            argv += ["--require-substance"]
        proc = subprocess.run(argv, capture_output=True, text=True)

    if not proc.stdout.strip():
        raise RuntimeError(f"{SIBLING} could not evaluate: {proc.stderr.strip() or '(no output)'}")
    try:
        g = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"{SIBLING} returned unparseable output ({e}): {proc.stdout[:200]!r}")
    return proc.returncode, g


# ---------------------------------------------------------------- the check

def check(records, source_ids, declared_count=None, quiesced=True,
          require_substance=False, here=HERE, scan_scope=SCAN_WHOLE):
    """Pure at the python-object level -- records/source_ids are already-loaded lists.
    The only I/O is the sibling subprocess call, which needs real files on disk.

    scan_scope: SCAN_WHOLE (default, PINNED and SYMMETRIC -- see module docstring S10.5) or
    SCAN_LEDGER (legacy opt-in, narrower, heading-conditioned -- see _scope_text). Every
    returned verdict dict states "scan_scope" so a reader (human or lab harness) never has
    to infer which surface was graded."""
    identified, unidentified, dupe_ids = identify(records)
    src_distinct = len(set(source_ids)) if source_ids else 0

    def inconclusive(reason):
        return {
            "verdict": "INCONCLUSIVE", "exit": CANNOT_EVALUATE,
            "captured": len(identified), "records_seen": len(records),
            "unidentified": unidentified, "duplicate_ids": dupe_ids,
            "quiesced": quiesced, "source_count": src_distinct,
            "covered_count": 0, "covered": [], "missing": [], "missing_count": 0, "alien": [],
            "ambiguous_prefixes": [], "bare_citations": [], "ledger_fallback": [],
            "scan_scope": scan_scope,
            "reasons": [reason],
        }

    if not quiesced:
        return inconclusive(
            "capture was not confirmed quiesced -- a low or zero coverage read here may "
            "only mean 'still running', which is not a finding. FIX THE INSTRUMENT (confirm "
            "settle) before grading coverage.")
    if unidentified:
        return inconclusive(
            f"{len(unidentified)} captured record(s) carry no agent_id and/or no "
            f"agentType: {unidentified[:5]} -- an unidentified record is not evidence a "
            f"real sub-agent returned anything, so its text cannot be trusted as coverage. "
            f"FIX THE INSTRUMENT first.")
    if dupe_ids:
        return inconclusive(
            f"duplicate agent_id(s) {dupe_ids} -- the same return counted twice can "
            f"manufacture coverage that never actually happened")
    if not identified:
        return inconclusive(
            "ZERO identified sub-agent records captured -- this cannot distinguish 'the "
            "fan-out never ran' from 'capture is broken', and grading coverage against "
            "nothing would be a vacuous pass. Absence of evidence is not evidence of absence.")
    if not source_ids:
        return inconclusive(
            "EMPTY source-id set handed in -- refusing to grade coverage against a vacuous "
            "denominator (a vacuous pass is the silent-zero failure this part exists to "
            "prevent)")

    union, ledger_fallback = union_text(identified, scan_scope=scan_scope)
    with tempfile.TemporaryDirectory() as td:
        sp = os.path.join(td, "source-ids.json")
        with open(sp, "w", encoding="utf-8") as fh:
            json.dump(list(source_ids), fh)
        try:
            rc, g = _sibling_grade(sp, union, declared_count, require_substance, here)
        except RuntimeError as e:
            return inconclusive(str(e))

    if rc == CANNOT_EVALUATE:
        return inconclusive(f"{SIBLING} could not evaluate the union of captured returns "
                            f"(likely a denominator mismatch against --declared)")

    # S10.4: the sibling collapses THREE distinct findings (missing / alien / bare) into
    # one rc==LOSS. Split them here: a missing id (or a bare id-dump under
    # --require-substance, which is not real coverage either -- see completeness_receipt's
    # own KNOWN BOUND) is a real LOSS. Zero missing + zero bare + one-or-more alien is a
    # SEPARATE, non-halting ALIEN verdict -- there is no source item to re-dispatch a
    # map-agent for, so it must not trigger the same "do not proceed" the driver applies
    # to a real loss.
    alien = g.get("alien", [])
    bare = g.get("bare_citations", [])
    real_loss = rc == LOSS and (g["missing_count"] > 0 or bool(bare))
    alien_only = rc == LOSS and not real_loss and bool(alien)

    if rc == COMPLETE:
        verdict, exit_code = "COMPLETE", COMPLETE
        reasons = ["every source id is traceably covered by the union of the captured "
                  "sub-agent returns, checked at the return boundary"]
    elif real_loss:
        verdict, exit_code = "LOSS", LOSS
        shown = g["missing"][:10]
        more = "…" if g["missing_count"] > 10 else ""
        reasons = [f"{g['missing_count']} source id(s) never traceably cited by ANY captured "
                  f"return: {shown}{more}"]
        if alien:
            reasons.append(f"{len(alien)} id(s) cited that are not in the source: "
                           f"{alien[:10]}")
        if bare:
            reasons.append(f"{len(bare)} citation(s) carry no accompanying "
                           f"prose (require_substance)")
    elif alien_only:
        verdict, exit_code = "ALIEN", ALIEN
        reasons = [f"{g['covered_count']}/{g['source_count']} source ids covered -- ZERO "
                  f"missing -- but {len(alien)} id(s) were cited that are NOT in the "
                  f"source: {alien}. This is over-citation, not a coverage loss: REPORT "
                  f"ONLY, NOT a halt condition -- there is no source item to re-dispatch a "
                  f"map-agent for."]
    else:
        # rc == LOSS but neither real_loss nor alien_only fired. Given the sibling's own
        # ok = not residue and not alien and not bare, this combination should be
        # unreachable -- but fail closed rather than assert across a subprocess boundary.
        verdict, exit_code = "LOSS", LOSS
        reasons = [f"{SIBLING} reported LOSS (missing={g['missing_count']}, "
                  f"alien={len(alien)}, bare={len(bare)}) in a combination this part did "
                  f"not expect -- treating as LOSS to fail closed"]

    if ledger_fallback:
        # Only reachable under scan_scope==SCAN_LEDGER -- SCAN_WHOLE (the pinned default)
        # never falls back, it always scans everything, so this list is always empty there.
        reasons.append(f"{len(ledger_fallback)} captured return(s) carried no '### Coverage "
                       f"ledger' heading -- citation scan fell back to the WHOLE return "
                       f"text for those under legacy --ledger-scope mode (fail-closed, not "
                       f"fail-silent): {ledger_fallback[:5]}")
    reasons.append(f"scan scope used: {scan_scope!r}"
                   + (" (pinned, symmetric default -- every captured return scanned over "
                      "the same surface, heading or not)" if scan_scope == SCAN_WHOLE
                      else " (legacy, heading-conditioned -- opted in via --ledger-scope)"))

    return {
        "verdict": verdict, "exit": exit_code,
        "captured": len(identified), "records_seen": len(records),
        "unidentified": [], "duplicate_ids": [], "quiesced": quiesced,
        "source_count": g["source_count"], "covered_count": g["covered_count"],
        # T0.17 (2026-08-05): the sibling already computes the covered-id LIST (grade()'s
        # own "covered" key, completeness_receipt.py ~line 240) -- carried through here
        # rather than discarded. It IS derivable by a caller as source - missing - alien,
        # but a caller re-deriving what this part's own checker already computed is exactly
        # how a caller's copy drifts from the checker's -- so hand over the list this part
        # already holds instead of making every consumer re-derive it by hand.
        "covered": g.get("covered", []),
        "missing": g["missing"], "missing_count": g["missing_count"],
        "alien": alien,
        "ambiguous_prefixes": g.get("ambiguous_prefixes", []),
        "bare_citations": bare,
        "ledger_fallback": ledger_fallback,
        "scan_scope": scan_scope,
        "reasons": reasons,
    }


def render(v):
    out = [f"fanout_completeness -- {v['verdict']} "
           f"(captured {v['captured']} of {v['records_seen']} seen; "
           + (f"{v['covered_count']}/{v['source_count']} source ids covered)"
              if v["source_count"] else "no source count pinned)")
           + f"  [scan_scope={v.get('scan_scope', SCAN_WHOLE)!r}]"]
    for r in v["reasons"]:
        out.append(f"  - {r}")
    if v["verdict"] == "INCONCLUSIVE":
        out.append("  FIX THE INSTRUMENT before grading the skill — an inconclusive fan-out "
                   "return cannot support any coverage verdict.")
    elif v["verdict"] == "ALIEN":
        out.append("  REPORT ONLY, NOT a halt condition — zero source ids are missing; do "
                   "not re-dispatch a map-agent (there is no source item to re-dispatch for).")
    return "\n".join(out)


# ---------------------------------------------------------------- self-test

def _rec(i, atype="Task", desc=None, text=None):
    return {"agent_id": f"agent-{i}", "agentType": atype,
            "description": desc or f"Map-agent {i}",
            "final_text": text if text is not None else f"nothing here yet, angle {i}"}


def selftest():
    ok = True

    def report(label, passed, detail=""):
        nonlocal ok
        ok = ok and passed
        print(f"  [{'PASS' if passed else 'FAIL'}] {label}{(' -- ' + detail) if detail else ''}")

    print("fanout_completeness --selftest")

    SRC = ["thread-aaaaaaaaaaaa1", "thread-aaaaaaaaaaaa2", "thread-aaaaaaaaaaaa3",
           "thread-aaaaaaaaaaaa4", "thread-aaaaaaaaaaaa5"]

    # ── known-good: the union of two agents' returns covers every source id ──
    good = [
        _rec(1, text="saw `thread-aaaaaaaaaaaa1` and `thread-aaaaaaaaaaaa2` this pass"),
        _rec(2, text="also `thread-aaaaaaaaaaaa3` `thread-aaaaaaaaaaaa4` `thread-aaaaaaaaaaaa5`"),
    ]
    v = check(good, SRC, declared_count=len(SRC), quiesced=True)
    report("known-good: union of captured returns covers every source id -> COMPLETE",
           v["verdict"] == "COMPLETE" and v["exit"] == COMPLETE and v["missing"] == [],
           f"{v['covered_count']}/{v['source_count']}")

    # ── known-bad: THE EXACT SHAPE OF THE REAL W30 MISS -- one thread's signal never
    # cited by ANY returning agent, even though the fan-out held it ──
    bad = [
        _rec(1, text="saw `thread-aaaaaaaaaaaa1` and `thread-aaaaaaaaaaaa2` this pass"),
        _rec(2, text="also `thread-aaaaaaaaaaaa3` `thread-aaaaaaaaaaaa4`"),
        # thread-aaaaaaaaaaaa5 (the high-signal thread) is never cited by anyone
    ]
    v = check(bad, SRC, declared_count=len(SRC), quiesced=True)
    report("known-bad: a thread no agent cited is LOSS, and NAMED",
           v["verdict"] == "LOSS" and v["exit"] == LOSS
           and "thread-aaaaaaaaaaaa5" in v["missing"],
           f"missing={v['missing']}")
    report("...the reason text NAMES the dropped id, not just a count",
           "thread-aaaaaaaaaaaa5" in " ".join(v["reasons"]))

    # ── S10.5: THE EXACT SHAPE OF THE REAL 2026-08-03 MISS -- an alien citation with ZERO
    # ids missing must NOT get the same halt code as a real loss. Before S10.4 the branch
    # was NEVER exercised by any self-test despite `alien` appearing 6 times in this file.
    # An alien token genuinely INSIDE the ledger (not prose above it) is a real over-
    # citation -- report it loudly, but it must not halt. ──
    alien_only_records = [
        _rec(1, text="### Coverage ledger\n"
                     "- `thread-aaaaaaaaaaaa1` `thread-aaaaaaaaaaaa2` `thread-aaaaaaaaaaaa3`\n"
                     "- `thread-aaaaaaaaaaaa4` `thread-aaaaaaaaaaaa5`\n"
                     "- `calendar_name` -- also cited here, not a source id\n"),
    ]
    v = check(alien_only_records, SRC, declared_count=len(SRC), quiesced=True)
    report("known-bad: zero missing + one alien -> the NEW ALIEN exit code (NOT LOSS)",
           v["verdict"] == "ALIEN" and v["exit"] == ALIEN and v["missing"] == [],
           f"verdict={v['verdict']} exit={v['exit']} missing={v['missing']}")
    report("...the alien id is NAMED in the reason text",
           "calendar_name" in " ".join(v["reasons"]))
    report("...ALIEN is NOT the LOSS exit code (the 2026-08-03 incident: this must not halt "
           "the driver the way a real miss does)",
           v["exit"] != LOSS)

    # ── known-good: zero missing + zero alien still discriminates cleanly. Proves the
    # ALIEN check does not fire on everything -- only when there really is an alien. ──
    clean_ledger = [
        _rec(1, text="### Coverage ledger\n"
                     "- `thread-aaaaaaaaaaaa1` `thread-aaaaaaaaaaaa2` `thread-aaaaaaaaaaaa3`\n"
                     "- `thread-aaaaaaaaaaaa4` `thread-aaaaaaaaaaaa5`\n"),
    ]
    v = check(clean_ledger, SRC, declared_count=len(SRC), quiesced=True)
    report("known-good: zero missing + zero alien -> COMPLETE, exit 0 (the ALIEN check "
           "discriminates -- it does not fire on a clean ledger)",
           v["verdict"] == "COMPLETE" and v["exit"] == COMPLETE and v["alien"] == [],
           f"verdict={v['verdict']} exit={v['exit']}")

    # ── ledger-scoping (LEGACY, opt-in via scan_scope=SCAN_LEDGER): the REAL root cause of
    # the 2026-08-03 incident -- a backticked JSON field name in an HONEST METHODOLOGICAL
    # NOTE, written in prose ABOVE the '### Coverage ledger' heading, must NOT be scanned as
    # a citation at all. (Verified against the real production capture: `calendar_name` sits
    # in exactly this shape -- prose above the heading -- so the correct, LEGACY-scoped read
    # is COMPLETE, not ALIEN.) S10.5 (2026-08-04): this protection is no longer the default
    # -- see the bias-fix block below for why -- so this test now asks for it explicitly. ──
    scoped_prose = [
        _rec(1, text="Methodological note: only `summary`, `description`, `location`, "
                     "`organizer`, `calendar_name` were present on these items.\n\n"
                     "### Coverage ledger\n"
                     "- `thread-aaaaaaaaaaaa1` `thread-aaaaaaaaaaaa2` `thread-aaaaaaaaaaaa3`\n"
                     "- `thread-aaaaaaaaaaaa4` `thread-aaaaaaaaaaaa5`\n"),
    ]
    v = check(scoped_prose, SRC, declared_count=len(SRC), quiesced=True, scan_scope=SCAN_LEDGER)
    report("LEGACY --ledger-scope: a backticked field name in PROSE ABOVE '### Coverage "
           "ledger' is not scanned as a citation -> COMPLETE, not ALIEN",
           v["verdict"] == "COMPLETE" and v["exit"] == COMPLETE and v["alien"] == [],
           f"verdict={v['verdict']} alien={v['alien']}")
    report("...and a record with NO '### Coverage ledger' heading at all, under LEGACY "
           "scope, falls back to the whole text and SAYS SO (fail-closed, not fail-silent)",
           bool(check(good, SRC, declared_count=len(SRC), quiesced=True,
                      scan_scope=SCAN_LEDGER)["ledger_fallback"]))

    # ── the SAME scoped_prose fixture under the PINNED DEFAULT (SCAN_WHOLE, no scan_scope
    # argument passed) -- the tradeoff is now explicit and reported, never silently applied
    # either way: the whole text IS scanned, so `calendar_name` IS picked up as an alien.
    # This is the documented cost of removing the bias -- it does not disappear, it moves
    # to a named, non-halting ALIEN verdict instead of a silently-scoped miss. ──
    v = check(scoped_prose, SRC, declared_count=len(SRC), quiesced=True)
    report("PINNED DEFAULT on the same fixture: whole-text scan picks up the prose-borne "
           "`calendar_name` as an alien (report-only, non-halting) -- the tradeoff is real "
           "and visible, not hidden",
           v["verdict"] == "ALIEN" and "calendar_name" in v["alien"] and v["scan_scope"] == SCAN_WHOLE,
           f"verdict={v['verdict']} alien={v['alien']} scan_scope={v['scan_scope']}")

    # ── S10.5 (2026-08-04) -- THE MEASUREMENT-BIAS FIX ITSELF. Two fixtures, SAME content,
    # differing ONLY by whether a '### Coverage ledger' heading is present -- exactly what a
    # lab cell that "removes the coverage ledger" vs its control would produce. Two ids sit
    # in prose BEFORE where the heading is (or would be); three sit in what is (or would be)
    # the ledger section. ──
    prose_ids_block = "Handled `thread-aaaaaaaaaaaa1` `thread-aaaaaaaaaaaa2` before the ledger.\n\n"
    ledger_ids_block = "- `thread-aaaaaaaaaaaa3` `thread-aaaaaaaaaaaa4` `thread-aaaaaaaaaaaa5`\n"
    with_heading = [_rec(1, text=prose_ids_block + "### Coverage ledger\n" + ledger_ids_block)]
    without_heading = [_rec(1, text=prose_ids_block + ledger_ids_block)]  # SAME content, heading line gone

    # First, PROVE the legacy/pre-fix behaviour actually IS biased on this exact pair -- a
    # check that has never been seen to fail is not a check.
    v_with_legacy = check(with_heading, SRC, declared_count=len(SRC), quiesced=True,
                          scan_scope=SCAN_LEDGER)
    v_without_legacy = check(without_heading, SRC, declared_count=len(SRC), quiesced=True,
                             scan_scope=SCAN_LEDGER)
    report("PROOF THE OLD (legacy-scope) BEHAVIOUR IS BIASED: identical content, only the "
           "heading's presence differs -> the WITH-heading return LOSES the 2 ids sitting "
           "in prose above the heading, while the WITHOUT-heading return -- SAME content, "
           "SAME legacy scope -- covers them via silent-to-the-score whole-text fallback",
           v_with_legacy["verdict"] == "LOSS"
           and v_with_legacy["missing"] == ["thread-aaaaaaaaaaaa1", "thread-aaaaaaaaaaaa2"]
           and v_without_legacy["verdict"] == "COMPLETE",
           f"with-heading={v_with_legacy['verdict']} missing={v_with_legacy['missing']} / "
           f"without-heading={v_without_legacy['verdict']}")

    # Now the FIX: under the pinned SCAN_WHOLE default -- no scan_scope argument passed,
    # exactly what any caller (including the lab) gets who does not opt into --ledger-scope
    # -- both fixtures are scanned over the SAME surface and land on the SAME verdict.
    v_with_fixed = check(with_heading, SRC, declared_count=len(SRC), quiesced=True)
    v_without_fixed = check(without_heading, SRC, declared_count=len(SRC), quiesced=True)
    report("THE FIX: under the pinned default, the SAME two fixtures produce the SAME "
           "verdict and the SAME covered_count -- heading presence no longer changes the "
           "scan surface (denominator symmetry restored)",
           v_with_fixed["verdict"] == "COMPLETE" and v_without_fixed["verdict"] == "COMPLETE"
           and v_with_fixed["covered_count"] == v_without_fixed["covered_count"]
           and v_with_fixed["missing"] == v_without_fixed["missing"] == [],
           f"with-heading={v_with_fixed['verdict']}/{v_with_fixed['covered_count']} "
           f"without-heading={v_without_fixed['verdict']}/{v_without_fixed['covered_count']}")
    report("...and every verdict STATES which scan scope it used (a silent fallback is the "
           "thing being fixed; an announced one is fine)",
           v_with_fixed["scan_scope"] == SCAN_WHOLE and v_without_fixed["scan_scope"] == SCAN_WHOLE
           and all("scan scope used" in r for r in [" ".join(v_with_fixed["reasons"]),
                                                     " ".join(v_without_fixed["reasons"])]))

    # ── the seam this was BUILT to close: a phase-exit check on the SAME data would
    # have been fed a downstream artifact built AFTER the drop and could show clean.
    # Demonstrate the boundary property directly: grading only what was CAPTURED (this
    # part) catches it; nothing here can be pointed at a later synthesis step instead --
    # the input contract IS the captured records. ──
    report("the check's only artifact input is the captured union itself (no downstream "
           "artifact parameter exists to misuse)",
           "artifact" not in check.__code__.co_varnames)

    # ── identification hygiene: an unidentified record refuses BEFORE grading coverage ──
    cheat = [{"final_text": "`thread-aaaaaaaaaaaa1` `thread-aaaaaaaaaaaa2` "
                            "`thread-aaaaaaaaaaaa3` `thread-aaaaaaaaaaaa4` "
                            "`thread-aaaaaaaaaaaa5`"}]
    v = check(cheat, SRC, declared_count=len(SRC), quiesced=True)
    report("known-bad: an unidentified record cannot buy a COMPLETE by citing everything",
           v["verdict"] == "INCONCLUSIVE" and v["exit"] == CANNOT_EVALUATE,
           f"got {v['verdict']}")

    # ── duplicate agent_id cannot inflate coverage ──
    dupes = [_rec(1, text="`thread-aaaaaaaaaaaa1`"), _rec(1, text="`thread-aaaaaaaaaaaa1`")]
    v = check(dupes, SRC, declared_count=len(SRC), quiesced=True)
    report("known-bad: a duplicated agent_id is INCONCLUSIVE, not silently deduped",
           v["verdict"] == "INCONCLUSIVE" and v["duplicate_ids"] == ["agent-1"])

    # ── zero identified records is never a vacuous pass ──
    v = check([], SRC, declared_count=len(SRC), quiesced=True)
    report("known-bad: ZERO captured records is INCONCLUSIVE, never a clean pass",
           v["verdict"] == "INCONCLUSIVE" and v["exit"] == CANNOT_EVALUATE)
    report("...and says so in words a human can act on",
           "not evidence of absence" in " ".join(v["reasons"]))

    # ── un-quiesced capture can only be inconclusive ──
    v = check(good, SRC, declared_count=len(SRC), quiesced=False)
    report("known-bad: an un-quiesced capture is INCONCLUSIVE even with full coverage",
           v["verdict"] == "INCONCLUSIVE")

    # ── empty source set is refused, not a vacuous pass ──
    v = check(good, [], quiesced=True)
    report("known-bad: an EMPTY source-id set is INCONCLUSIVE (vacuous denominator refused)",
           v["verdict"] == "INCONCLUSIVE" and v["exit"] == CANNOT_EVALUATE)

    # ── the ambiguous-truncation hole completeness_receipt closed is INHERITED, not
    # reopened, because the reachability logic is delegated, never reimplemented ──
    serial_src = ["cw_p2_unit_000269", "cw_p2_unit_000270", "cw_p2_unit_000271"]
    ambiguous_cheat = [_rec(1, text="`cw_p2_unit_000...` — covers this whole batch")]
    v = check(ambiguous_cheat, serial_src, declared_count=len(serial_src), quiesced=True)
    report("known-bad: one ambiguous truncated prefix cannot cover a whole serial corpus "
           "(inherited from the sibling, not reimplemented and re-broken here)",
           v["verdict"] == "LOSS" and v["missing_count"] == 3, f"missing={v['missing']}")
    honest = [_rec(i, text=f"`{sid}` — carried forward") for i, sid in enumerate(serial_src, 1)]
    v = check(honest, serial_src, declared_count=len(serial_src), quiesced=True)
    report("known-good: citing each serial id individually still PASSES through delegation",
           v["verdict"] == "COMPLETE")

    # ── the required sibling is REQUIRED -- missing sibling is exit 2, never a fallback ──
    v = check(good, SRC, declared_count=len(SRC), quiesced=True, here=tempfile.gettempdir())
    report("fail-closed: a missing sibling part refuses (CANNOT EVALUATE), never falls back "
           "to a weaker check",
           v["verdict"] == "INCONCLUSIVE" and "completeness_receipt.py" in v["reasons"][0])

    # ── partial credit is not a thing: dupes/unidentified/unquiesced BEAT a full-looking
    # citation set -- the instrument question is asked BEFORE the coverage question ──
    report("hygiene refusals take priority over coverage (asked FIRST, not after)",
           check(cheat, SRC, declared_count=len(SRC), quiesced=True)["covered_count"] == 0)

    # ── CLI exit-code contract, including the missing-file paths ──
    me = os.path.abspath(__file__)
    with tempfile.TemporaryDirectory() as td:
        cp = os.path.join(td, "captured.json")
        sp = os.path.join(td, "src.json")
        with open(cp, "w", encoding="utf-8") as fh:
            json.dump(good, fh)
        with open(sp, "w", encoding="utf-8") as fh:
            json.dump(SRC, fh)
        rc = subprocess.run([sys.executable, me, "--captured", cp, "--source-ids", sp,
                             "--quiesced"], capture_output=True, text=True).returncode
        report("CLI known-good -> exit 0", rc == COMPLETE, f"got exit {rc}")

        with open(cp, "w", encoding="utf-8") as fh:
            json.dump(bad, fh)
        rc = subprocess.run([sys.executable, me, "--captured", cp, "--source-ids", sp,
                             "--quiesced"], capture_output=True, text=True).returncode
        report("CLI known-bad -> exit 1", rc == LOSS, f"got exit {rc}")

        rc = subprocess.run([sys.executable, me, "--captured",
                             os.path.join(td, "nope.json"), "--source-ids", sp, "--quiesced"],
                            capture_output=True, text=True).returncode
        report("CLI missing captured file -> exit 2 (fail-closed)", rc == CANNOT_EVALUATE,
               f"got exit {rc}")

        rc = subprocess.run([sys.executable, me, "--captured", cp, "--source-ids",
                             os.path.join(td, "nope.json"), "--quiesced"],
                            capture_output=True, text=True).returncode
        report("CLI missing source-ids file -> exit 2 (fail-closed)", rc == CANNOT_EVALUATE,
               f"got exit {rc}")

        rc = subprocess.run([sys.executable, me, "--captured", cp, "--source-ids", sp],
                            capture_output=True, text=True).returncode
        report("CLI without --quiesced -> exit 2 (fail-closed, never assumed settled)",
               rc == CANNOT_EVALUATE, f"got exit {rc}")

        # ── CLI wiring for the S10.5 fix: default scan_scope is "whole" (stated in --json
        # output); --ledger-scope switches it to "ledger". ──
        with open(cp, "w", encoding="utf-8") as fh:
            json.dump(good, fh)
        proc = subprocess.run([sys.executable, me, "--captured", cp, "--source-ids", sp,
                               "--quiesced", "--json"], capture_output=True, text=True)
        default_scope = json.loads(proc.stdout).get("scan_scope")
        report("CLI default (no --ledger-scope) -> scan_scope 'whole' in --json output",
               default_scope == SCAN_WHOLE, f"got {default_scope!r}")

        proc = subprocess.run([sys.executable, me, "--captured", cp, "--source-ids", sp,
                               "--quiesced", "--ledger-scope", "--json"],
                              capture_output=True, text=True)
        legacy_scope = json.loads(proc.stdout).get("scan_scope")
        report("CLI --ledger-scope -> scan_scope 'ledger' in --json output",
               legacy_scope == SCAN_LEDGER, f"got {legacy_scope!r}")

    # --- DIFFERENTIAL vs REAL W30 DATA (not a fabricated fixture, SOP §V.3) -----------
    # The 55 real Gmail message ids from the frozen W30 arc's own source-id set
    # (system/tools/conformance-lab/fixtures/cal-weekly/w30-source-ids.json). This is the
    # same real corpus completeness_receipt.py's own differential self-test uses; the ids
    # are real and frozen, not invented. We do not have a preserved per-map-agent
    # JSONL/meta capture for this run (fanout_seam.py's provenance-dir format exists as
    # lab tooling but no frozen provenance dir for the W30 map-agents ships in fixtures/),
    # so the CAPTURED-record shape (agent_id/agentType/description/final_text -- exactly
    # fanout_gate's documented format) is constructed here around those real ids, the same
    # method completeness_receipt.py's own preserved-grade differential test already uses
    # and treats as legitimate real-data validation (not the fictional-fixture failure
    # SOP §V.3 warns against, which is inventing a VIOLATION -- here we invent nothing,
    # we assign real ids to a real record shape and test the mechanism against them).
    _repo_root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    lab = os.path.join(_repo_root, "system", "tools", "conformance-lab",
                        "fixtures", "cal-weekly")
    spath = os.path.join(lab, "w30-source-ids.json")
    if os.path.isfile(spath):
        import re
        real_ids = load_source_ids(spath)
        email_ids = sorted(i for i in real_ids if re.fullmatch(r"[0-9a-f]{16}", i))
        report("DIFFERENTIAL SETUP: loaded the real W30 email-id set",
               len(email_ids) == 55, f"got {len(email_ids)}")

        # split the 55 real ids across 3 "map-agents", each citing its slice verbatim --
        # the union of all three must cover every real id.
        chunks = [email_ids[0:19], email_ids[19:38], email_ids[38:55]]
        real_complete = [
            _rec(i + 1, desc=f"Map-agent {i + 1}",
                 text="\n".join(f"- `{eid}` — real W30 email thread" for eid in chunk))
            for i, chunk in enumerate(chunks)
        ]
        v = check(real_complete, email_ids, declared_count=len(email_ids), quiesced=True)
        report("DIFFERENTIAL (real W30 ids): full coverage across 3 real map-agents -> "
               "COMPLETE", v["verdict"] == "COMPLETE" and v["missing"] == [],
               f"{v['covered_count']}/{v['source_count']}")

        # now deliberately drop ONE real id -- the shape of the actual W30 miss: a thread
        # every agent was handed but none returned a citation for.
        dropped_id = chunks[1][0]
        real_dropped = [
            _rec(i + 1, desc=f"Map-agent {i + 1}",
                 text="\n".join(f"- `{eid}` — real W30 email thread"
                                for eid in chunk if eid != dropped_id))
            for i, chunk in enumerate(chunks)
        ]
        v = check(real_dropped, email_ids, declared_count=len(email_ids), quiesced=True)
        report("DIFFERENTIAL (real W30 ids): ONE deliberately-dropped real thread id is "
               "REFUSED and NAMED", v["verdict"] == "LOSS" and v["missing"] == [dropped_id],
               f"verdict={v['verdict']} missing={v['missing']}")
    else:
        # ▶ RETIRED, same decision and same reason as completeness_receipt.py's own
        #   preserved-grade differential (see its selftest): the w30-* fixtures this check
        #   depends on were never ported into this repo and never have been (verified
        #   against full git history, 2026-08-28) -- there is no commit that ever added
        #   system/tools/conformance-lab/fixtures/cal-weekly/w30-source-ids.json. That makes
        #   this a permanent, un-fixable-from-here [FAIL] rather than a real signal, so it is
        #   reported as [SKIP] (excluded from ok/PASS/FAIL) instead -- the same call
        #   run_selftests.sh's own reachability check documents making: "a check that can
        #   only ever report failure gets deleted." Kept visible as a live prompt to port
        #   the fixtures, not silently dropped.
        print("  [SKIP] DIFFERENTIAL vs real W30 data -- "
              "lab fixtures not found (cannot claim real-data validation; "
              "port system/tools/conformance-lab/fixtures/cal-weekly/ to make this live)")

    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


# ---------------------------------------------------------------- CLI

def main():
    ap = argparse.ArgumentParser(
        description="fanout_completeness -- native-id coverage set-diffed at the fan-out "
                    "RETURN boundary, never at phase exit")
    ap.add_argument("--captured", help="the captured fan-out records (fanout_gate's shape)")
    ap.add_argument("--source-ids", help="the source ids the fan-out was HANDED")
    ap.add_argument("--declared", type=int, default=None,
                    help="the denominator you believe is in scope; mismatch = un-evaluable")
    ap.add_argument("--quiesced", action="store_true",
                    help="assert capture had settled; without this the verdict is INCONCLUSIVE")
    ap.add_argument("--require-substance", action="store_true",
                    help="forwarded to the sibling -- a cited id must carry prose on its line")
    ap.add_argument("--ledger-scope", action="store_true",
                    help="LEGACY, opt-in: narrow the citation scan to text at-or-after a "
                         "'### Coverage ledger' heading (falls back to the whole text, "
                         "announced, if no heading is found). Without this flag the DEFAULT "
                         "is the pinned, symmetric whole-text scan (S10.5) -- every captured "
                         "return is scanned over the SAME surface whether or not a heading "
                         "is present. Use --ledger-scope only for backward-compatible "
                         "callers that always ship a heading and need prose ABOVE it excluded "
                         "from the scan; never use it where the heading's own presence may "
                         "be the thing under test (that reopens the exact bias S10.5 fixes).")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())
    if not args.captured or not args.source_ids:
        _die("--captured and --source-ids are required")
    for p, what in ((args.captured, "captured file"), (args.source_ids, "source-ids file")):
        if not os.path.isfile(p):
            _die(f"{what} not found: {p!r}")
    try:
        records = load_records(args.captured)
    except (json.JSONDecodeError, TypeError) as e:
        _die(f"captured file is not valid JSON: {e}")
    try:
        source_ids = load_source_ids(args.source_ids)
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        _die(f"cannot read source ids: {e}")

    v = check(records, source_ids, declared_count=args.declared, quiesced=args.quiesced,
              require_substance=args.require_substance,
              scan_scope=SCAN_LEDGER if args.ledger_scope else SCAN_WHOLE)
    print(json.dumps(v, indent=2) if args.json else render(v))
    sys.exit(v["exit"])


if __name__ == "__main__":
    main()

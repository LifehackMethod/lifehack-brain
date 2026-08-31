#!/usr/bin/env python3
"""fanout_completeness — native-id coverage set-diff AT THE FAN-OUT RETURN BOUNDARY.
  [Parts Library]

WHEN: after a fan-out of sub-agents (or any parallel dispatch keyed by native source ids)
      has returned, and something is about to trust that every handed-out id came back.

WHAT: pins the denominator (the source id list the caller handed out), set-diffs it against
      what was actually captured, and refuses to call it COMPLETE unless every capture is
      typed evidence of a real, identified agent -- never just the right shape of JSON.

WHY:  the same failure this library has hit twice already (see fanout_gate.py, and
      completeness_receipt.py's ambiguous-prefix note): a capture that LOOKS complete by
      naive count is not the same as a capture that IS complete. Here the naive cheat is a
      bare array of `{"final_text": "x"}` objects -- right length, zero identity, zero
      evidence any agent ran at all. Evidence of work, never form of claim.

ANTI-FORGERY RULE: a capture record missing a non-empty string `id` or a non-empty string
      `agent_id` is MALFORMED. A malformed record present anywhere in C.json fails the run,
      unconditionally -- it is never silently dropped and never lets an otherwise-complete
      capture pass, because its presence means the capture instrument itself is untrustworthy
      for every record, not just the bad one.

QUIESCENCE: a fan-out that has not finished cannot be graded for completeness -- a low or
      zero count may just mean "still running." Without --quiesced, an EMPTY C.json against a
      non-empty source-ids list is reported STILL-WAITING and refused as CANNOT EVALUATE
      (never a pass, never a fail: the run has not finished, so completeness is not yet a
      question that can be answered). --quiesced asserts the fan-out is over; ONLY then does
      an empty capture become the hard FAIL it actually is (every id in the denominator is
      simply missing). A non-empty C.json is graded on its own merits regardless of
      --quiesced -- the flag exists to stop an in-flight run's empty snapshot from reading as
      a clean pass, not to gate every other verdict.

USAGE
  fanout_completeness.py --captured C.json --source-ids IDS.json [--declared N] \\
                         [--quiesced] [--require-substance] [--json]
  fanout_completeness.py --selftest

EXIT CODES (the part contract)
  0  COMPLETE   -- every source id captured exactly once, all records well-formed
  1  VIOLATED   -- missing/alien/duplicate ids, malformed records, thin substance, or a
                   DENOMINATOR-MISMATCH (a --declared count that disagrees with the actual
                   source-ids list -- the denominator must be proven, not asserted)
  2  CANNOT EVALUATE -- missing/unreadable/unparsable input file, or an un-quiesced empty
                        capture (STILL-WAITING). ABSENT-SUBJECT: never folded into a pass
                        or an ordinary violation.

IDS.json (the denominator, pinned by the caller): a JSON list of native id strings, e.g.
  ["id-001", "id-002", "id-003"]

C.json (the capture): a JSON list of records, each at minimum
  {"id": "<source id>", "agent_id": "<agent identifier>", "summary": "<what it returned>"}
  extra fields are ignored. With --require-substance, "summary" must be a non-empty string
  of at least 40 characters -- catches an agent_id/id pair with nothing real behind it.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile

COMPLETE, VIOLATED, CANNOT_EVALUATE = 0, 1, 2

MIN_SUMMARY_CHARS = 40


def _die(msg):
    print(f"CANNOT EVALUATE: {msg}", file=sys.stderr)
    sys.exit(CANNOT_EVALUATE)


def _nonempty_str(v):
    return isinstance(v, str) and bool(v.strip())


# ---------------------------------------------------------------- the check

def grade(captured, source_ids, declared=None, quiesced=False, require_substance=False):
    """Grade one fan-out capture. Returns a verdict dict; never raises on well-shaped
    JSON input (a list of dicts and a list of strings) -- malformed records are a graded
    outcome (VIOLATED), not an exception. Raises TypeError only if the top-level shapes
    themselves are wrong (caller's job to have already validated JSON structure)."""
    if not isinstance(source_ids, list) or not all(isinstance(s, str) for s in source_ids):
        raise TypeError("source-ids must be a JSON list of strings")
    if not isinstance(captured, list):
        raise TypeError("captured must be a JSON list of records")

    reasons = []

    if declared is not None and declared != len(source_ids):
        return {
            "verdict": "VIOLATED",
            "reason_code": "DENOMINATOR-MISMATCH",
            "reasons": [f"--declared {declared} does not match the source-ids list, which "
                        f"holds {len(source_ids)} id(s) -- the denominator must be proven, "
                        f"not asserted"],
            "source_count": len(source_ids), "declared": declared,
            "captured_records": len(captured), "distinct_captured": 0,
            "missing": [], "alien": [], "dupes": [], "malformed": [], "thin": [],
            "exit": VIOLATED,
        }

    if not captured and source_ids and not quiesced:
        return {
            "verdict": "STILL-WAITING",
            "reason_code": "NOT-QUIESCED",
            "reasons": ["C.json is empty and --quiesced was not given -- a fan-out that "
                        "has not been confirmed over cannot be graded for completeness "
                        "yet; this is not a pass and not a fail"],
            "source_count": len(source_ids), "declared": declared,
            "captured_records": 0, "distinct_captured": 0,
            "missing": [], "alien": [], "dupes": [], "malformed": [], "thin": [],
            "exit": CANNOT_EVALUATE,
        }

    malformed = []
    valid = []
    for i, r in enumerate(captured):
        label = f"#{i + 1}"
        if not isinstance(r, dict):
            malformed.append(label)
            continue
        rid, aid = r.get("id"), r.get("agent_id")
        label = f"#{i + 1} (id={rid!r})" if _nonempty_str(rid) else label
        if not _nonempty_str(rid) or not _nonempty_str(aid):
            malformed.append(label)
            continue
        valid.append(r)

    if malformed:
        reasons.append(f"{len(malformed)} captured record(s) are MALFORMED -- missing a "
                       f"non-empty string 'id' and/or 'agent_id': {malformed[:5]} -- an "
                       f"unidentified record is not evidence any agent ran, so the whole "
                       f"capture is untrustworthy (anti-forgery rule)")

    thin = []
    if require_substance:
        for r in valid:
            summ = r.get("summary")
            if not (isinstance(summ, str) and len(summ.strip()) >= MIN_SUMMARY_CHARS):
                thin.append(str(r.get("id")))
        if thin:
            reasons.append(f"{len(thin)} captured record(s) have a 'summary' shorter than "
                           f"{MIN_SUMMARY_CHARS} chars (or missing/non-string): {thin[:5]} "
                           f"-- a typed field with no real content is not evidence of work")

    ids = [r["id"].strip() for r in valid]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        reasons.append(f"duplicate id(s) captured more than once: {dupes[:5]}")

    distinct = set(ids)
    src_set = set(source_ids)
    missing = sorted(src_set - distinct)
    alien = sorted(distinct - src_set)
    if missing:
        reasons.append(f"{len(missing)} source id(s) never captured: {missing[:5]}")
    if alien:
        reasons.append(f"{len(alien)} captured id(s) are not in the source-ids list "
                       f"(alien): {alien[:5]}")

    complete = not (missing or alien or dupes or malformed or thin)
    if complete:
        reasons = ["every source id captured exactly once, all records well-formed"]

    return {
        "verdict": "COMPLETE" if complete else "VIOLATED",
        "reason_code": None if complete else "INCOMPLETE",
        "reasons": reasons,
        "source_count": len(source_ids), "declared": declared,
        "captured_records": len(captured), "distinct_captured": len(distinct),
        "missing": missing, "alien": alien, "dupes": dupes,
        "malformed": malformed, "thin": thin,
        "exit": COMPLETE if complete else VIOLATED,
    }


def load_list(path, what):
    try:
        raw = json.loads(open(path, encoding="utf-8").read())
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
        _die(f"{what} is not valid JSON: {e}")
    if not isinstance(raw, list):
        _die(f"{what} must contain a JSON list")
    return raw


def render(g):
    out = [f"fanout_completeness -- {g['verdict']}"
           f" (source {g['source_count']}, captured {g['captured_records']} record(s), "
           f"{g['distinct_captured']} distinct id(s))"]
    for r in g["reasons"]:
        out.append(f"  - {r}")
    if g["verdict"] == "STILL-WAITING":
        out.append("  re-run with --quiesced once the fan-out is confirmed over.")
    return "\n".join(out)


# ---------------------------------------------------------------- self-test

_SRC = ["id-001", "id-002", "id-003"]


def _rec(i, summary=None):
    return {"id": f"id-{i:03d}", "agent_id": f"agent-{i}",
            "summary": summary if summary is not None
            else f"processed source item {i:03d} and returned a real, non-trivial result"}


def selftest():
    ok = True

    def report(label, passed, detail=""):
        nonlocal ok
        ok = ok and passed
        print(f"  [{'PASS' if passed else 'FAIL'}] {label}{(' -- ' + detail) if detail else ''}")

    print("fanout_completeness --selftest")

    # ⭐ the exact forgery this part exists to catch
    cheat = [{"final_text": "x"}, {"final_text": "x"}, {"final_text": "x"}]
    g = grade(cheat, _SRC, quiesced=True)
    report("known-bad: bare {'final_text': 'x'} array (no id/agent_id) -> VIOLATED, "
           "never COMPLETE by count alone",
           g["verdict"] == "VIOLATED" and len(g["malformed"]) == 3, g["verdict"])

    # known-good
    good = [_rec(1), _rec(2), _rec(3)]
    g = grade(good, _SRC, quiesced=True)
    report("known-good: every source id captured once, well-formed -> COMPLETE",
           g["verdict"] == "COMPLETE" and g["exit"] == COMPLETE, str(g["reasons"]))

    # missing
    g = grade([_rec(1), _rec(2)], _SRC, quiesced=True)
    report("missing a source id -> VIOLATED, names it",
           g["verdict"] == "VIOLATED" and g["missing"] == ["id-003"])

    # alien
    g = grade([_rec(1), _rec(2), _rec(3), _rec(9)], _SRC, quiesced=True)
    report("an id outside the source set -> VIOLATED (alien)",
           g["verdict"] == "VIOLATED" and g["alien"] == ["id-009"])

    # dupes
    g = grade([_rec(1), _rec(1), _rec(2), _rec(3)], _SRC, quiesced=True)
    report("a duplicated id -> VIOLATED (dupes named)",
           g["verdict"] == "VIOLATED" and g["dupes"] == ["id-001"])

    # partial malformity: one good record poisons an otherwise-complete run
    poisoned = [_rec(1), _rec(2), {"id": "id-003", "summary": "no agent id here"}]
    g = grade(poisoned, _SRC, quiesced=True)
    report("ONE malformed record (missing agent_id) fails the WHOLE run, even though the "
           "other two are fine",
           g["verdict"] == "VIOLATED" and len(g["malformed"]) == 1)

    # require-substance
    g = grade([_rec(1, summary="ok"), _rec(2), _rec(3)], _SRC, quiesced=True,
              require_substance=True)
    report("--require-substance catches a typed-but-empty summary (< 40 chars)",
           g["verdict"] == "VIOLATED" and g["thin"] == ["id-001"])
    g = grade(good, _SRC, quiesced=True, require_substance=True)
    report("--require-substance passes real per-item substance",
           g["verdict"] == "COMPLETE")

    # denominator
    g = grade(good, _SRC, declared=4, quiesced=True)
    report("--declared disagreeing with the source-ids list -> VIOLATED, DENOMINATOR-MISMATCH",
           g["verdict"] == "VIOLATED" and g["reason_code"] == "DENOMINATOR-MISMATCH")
    g = grade(good, _SRC, declared=3, quiesced=True)
    report("--declared agreeing with the source-ids list is a no-op",
           g["verdict"] == "COMPLETE")

    # quiescence
    g = grade([], _SRC, quiesced=False)
    report("empty capture, source non-empty, NOT --quiesced -> CANNOT EVALUATE "
           "(STILL-WAITING, not a pass and not a fail)",
           g["verdict"] == "STILL-WAITING" and g["exit"] == CANNOT_EVALUATE)
    g = grade([], _SRC, quiesced=True)
    report("empty capture, source non-empty, --quiesced given -> hard FAIL, not "
           "'still waiting'",
           g["verdict"] == "VIOLATED" and g["exit"] == VIOLATED and g["missing"] == _SRC)
    # a non-empty but malformed capture fails regardless of quiescence -- the "still
    # waiting" grace period only applies to a literally EMPTY capture
    g = grade(cheat, _SRC, quiesced=False)
    report("a non-empty forged capture is graded (and fails) even without --quiesced",
           g["verdict"] == "VIOLATED" and g["exit"] == VIOLATED)
    # empty capture against an empty source is vacuously complete
    g = grade([], [], quiesced=True)
    report("empty capture against an empty source-ids list is vacuously COMPLETE",
           g["verdict"] == "COMPLETE")

    # CLI end-to-end, proving the exit-code contract
    me = os.path.abspath(__file__)
    with tempfile.TemporaryDirectory() as td:
        sp = os.path.join(td, "src.json")
        with open(sp, "w", encoding="utf-8") as fh:
            json.dump(_SRC, fh)

        cp = os.path.join(td, "cap.json")
        with open(cp, "w", encoding="utf-8") as fh:
            json.dump(good, fh)
        rc = subprocess.run([sys.executable, me, "--captured", cp, "--source-ids", sp,
                             "--quiesced"], capture_output=True, text=True).returncode
        report("CLI known-good -> exit 0", rc == COMPLETE, f"got exit {rc}")

        with open(cp, "w", encoding="utf-8") as fh:
            json.dump(cheat, fh)
        rc = subprocess.run([sys.executable, me, "--captured", cp, "--source-ids", sp,
                             "--quiesced"], capture_output=True, text=True).returncode
        report("CLI known-bad (forged array) -> exit 1", rc == VIOLATED, f"got exit {rc}")

        with open(cp, "w", encoding="utf-8") as fh:
            json.dump([], fh)
        rc = subprocess.run([sys.executable, me, "--captured", cp, "--source-ids", sp],
                            capture_output=True, text=True).returncode
        report("CLI empty capture, no --quiesced -> exit 2 (CANNOT EVALUATE)",
               rc == CANNOT_EVALUATE, f"got exit {rc}")

        rc = subprocess.run([sys.executable, me, "--captured", os.path.join(td, "nope.json"),
                             "--source-ids", sp], capture_output=True, text=True).returncode
        report("CLI missing captured file -> exit 2 (fail-closed, ABSENT-SUBJECT)",
               rc == CANNOT_EVALUATE, f"got exit {rc}")
        rc = subprocess.run([sys.executable, me, "--captured", cp,
                             "--source-ids", os.path.join(td, "nope.json")],
                            capture_output=True, text=True).returncode
        report("CLI missing source-ids file -> exit 2 (fail-closed, ABSENT-SUBJECT)",
               rc == CANNOT_EVALUATE, f"got exit {rc}")

        junk = os.path.join(td, "junk.json")
        with open(junk, "w", encoding="utf-8") as fh:
            fh.write("not json{{")
        rc = subprocess.run([sys.executable, me, "--captured", junk, "--source-ids", sp],
                            capture_output=True, text=True).returncode
        report("CLI unparsable captured JSON -> exit 2 (fail-closed, ABSENT-SUBJECT)",
               rc == CANNOT_EVALUATE, f"got exit {rc}")

        with open(cp, "w", encoding="utf-8") as fh:
            json.dump(good, fh)
        p = subprocess.run([sys.executable, me, "--captured", cp, "--source-ids", sp,
                            "--quiesced", "--json"], capture_output=True, text=True)
        try:
            payload = json.loads(p.stdout)
            json_ok = payload.get("verdict") == "COMPLETE"
        except json.JSONDecodeError:
            json_ok = False
        report("CLI --json emits a parseable verdict", json_ok, p.stdout[:150])

    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(
        description="fanout_completeness -- native-id coverage set-diff at the fan-out "
                     "return boundary, with typed evidence per capture")
    ap.add_argument("--captured")
    ap.add_argument("--source-ids")
    ap.add_argument("--declared", type=int, default=None,
                    help="the denominator you believe is in scope; mismatch is a violation")
    ap.add_argument("--quiesced", action="store_true",
                    help="assert the fan-out has finished; without this an empty capture "
                         "is CANNOT EVALUATE (still-waiting), never a pass or a fail")
    ap.add_argument("--require-substance", action="store_true",
                    help="each captured record's 'summary' must be a real string of at "
                         f"least {MIN_SUMMARY_CHARS} characters")
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

    captured = load_list(args.captured, "captured file")
    source_ids = load_list(args.source_ids, "source-ids file")
    if not all(isinstance(s, str) for s in source_ids):
        _die("source-ids file must be a JSON list of strings -- cannot pin the denominator")
    # NOTE: a non-dict entry in `captured` is deliberately NOT treated as ABSENT-SUBJECT
    # here -- the file itself parsed fine as a JSON list, so grade() handles a stray
    # non-dict record the same way it handles any other malformed record: a graded
    # VIOLATION (exit 1), not a refusal to evaluate (exit 2).

    g = grade(captured, source_ids, declared=args.declared, quiesced=args.quiesced,
              require_substance=args.require_substance)

    if args.json:
        print(json.dumps(g, indent=2, ensure_ascii=False))
    else:
        print(render(g))

    sys.exit(g["exit"])


if __name__ == "__main__":
    main()

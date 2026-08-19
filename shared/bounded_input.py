#!/usr/bin/env python3
"""bounded_input — proves a job touched ONLY what it was handed.

WHEN TO REACH FOR IT: any job handed a bounded list of things to work on — message ids,
      file names, row ids — that must not wander past that list. Anything fanned out to
      several workers, anything on a schedule, anything batched.

WHAT IT DOES: set-diffs what the run says it PROCESSED against what the caller actually
      HANDED it. Anything processed that was never handed is refused, and named.

WHY THIS EXISTS, and it is the half nobody builds. Every completeness check ever written
      asks "did we get everything?" — did the run reach all of its work. Almost nothing
      asks the opposite question: "did we get ONLY that?" And a runaway job is SILENT BY
      CONSTRUCTION. It does not error, it does not slow down, and its output looks exactly
      like a correct job that happened to be handed more work. The only way to see it is
      to diff the run against its own handoff.

      The incident behind this: a scheduling bug half-opened a job's circuit breaker and it
      processed 43 items it was never handed — the entire backlog re-chewed in a single run
      instead of the handful of new ones. Nothing failed. Nothing warned. Every check in
      that pipeline was watching the other direction.

THE TWO FAILURE MODES ARE NOT SYMMETRIC, AND THIS ONLY GATES ONE OF THEM.
      Processing FEWER than handed is a real finding — but a DIFFERENT one. It is a drop,
      not a runaway, and it sends whoever is investigating down another pipeline entirely.
      So under-processing is reported here as a distinct, NON-FAILING observation, and the
      refusal is reserved for extras. If a job has to be exactly right in both directions,
      it needs a second check facing the other way; this repository does not ship one yet,
      and the observation printed below is what you have in the meantime.

⚠ KNOWN BOUND -- THIS PART PROVES SCOPE, NOT CORRECTNESS.
      A run that processes exactly the handed ids, and only those, passes -- even if it
      did the wrong thing to every one of them. Scope and correctness are different
      claims; this part makes only the first one. It also trusts `--processed` as an
      honest account of what happened -- if the caller can fabricate that list, this part
      cannot catch it. Pair it with a real receipt of work performed (e.g. a write ledger)
      wherever the processed-ids file is itself the thing under suspicion.

⚠ KNOWN BOUND, AND IT IS A TERMINAL ANSWER RATHER THAN A TODO — MEASURED, NOT ASSUMED.
      This is one-directional. It is genuinely sound on over-reach: an id in `--processed`
      that was never in `--handed` exits 1 and is named. It cannot detect under-reach at
      all, and the reason is arithmetic rather than a lack of effort.

      The check computes `set(processed) - set(handed)`. Measured against a real run:

          handed               ['19fad58093fa0adb', '19fad54351c847e6']
          processed (REAL)     ['19fad58093fa0adb', '19fad54351c847e6']   -> diff set(), exit 0
          processed (a copy of the handed file)
                               ['19fad58093fa0adb', '19fad54351c847e6']   -> diff set(), exit 0

      The honest run's list is BYTE-IDENTICAL to the forged one. A job that did nothing at
      all and copied its own work-list passes exactly as a faithful run does. **No function
      of these two inputs can separate them, because the two files are the same file.**

      Closing it would need an independent trace of what was actually done — a third
      witness that was not written by the thing being checked. That is a real design, not
      a tweak: something else has to record the work as it happens.

      ⛔ DO NOT "FIX" THIS by inferring effort from the size, shape or content of what was
      produced. That heuristic was built here once, measured, and reverted: 10 out of 10 on
      a fixture its own author wrote, then a 50% false-positive rate on real work. A false
      accusation against legitimate small work is worse than a stated hole — a hole is
      visible and gets designed around, while a false gate gets argued with and then
      switched off.

USAGE
  bounded_input.py --handed HANDED.json --processed PROCESSED.json
  bounded_input.py --handed HANDED.json --processed PROCESSED.json --json
  bounded_input.py --selftest

EXIT CODES (the part contract)
  0  WITHIN BOUNDS   -- every processed id was in the handed set
  1  REFUSED         -- at least one processed id was NOT in the handed set (named)
  2  CANNOT EVALUATE -- missing/unreadable file, or an EMPTY handed list. Fail-closed --
                        a vacuous denominator can only produce a vacuous pass, which is
                        the silent-zero failure this library exists to kill.

INPUT FILES: ["id", ...]  or  {"ids": [...]}  or  {"items": [{"item_id": ...}]}
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile

WITHIN_BOUNDS, REFUSED, CANNOT_EVALUATE = 0, 1, 2


def _die(msg):
    print(f"CANNOT EVALUATE: {msg}", file=sys.stderr)
    sys.exit(CANNOT_EVALUATE)


# ---------------------------------------------------------------- loading

_ID_KEYS = ("ids", "handed", "processed")


def load_ids(path):
    """Three shapes are accepted: a bare list, {"ids": [...]}, or {"items": [{"item_id": ...}]}.

    ⭐ A SHAPE IT DOES NOT RECOGNISE IS AN ERROR, NOT AN EMPTY LIST. That distinction is the whole
    point of this file and it was missing until a test went looking for it (2026-08-11). The
    original returned [] for any dict with none of the expected keys — so handing it
    {"processed_count": 3}, which is exactly the hand-composed count this check exists to reject,
    produced an empty processed list, which reads as "the job did nothing", which is a legitimate
    result, which exits 0. A vacuous pass, from precisely the input the tool was written to refuse.

    An EXPLICIT empty stays legitimate: `[]` and `{"ids": []}` both mean "nothing was processed",
    and that is a real answer a run is allowed to give. What is refused is a shape that was never
    understood in the first place — because silently reading zero ids out of a file that plainly
    contains something is the difference between a measurement and a shrug."""
    raw = json.loads(open(path, encoding="utf-8").read())
    if isinstance(raw, list):
        return list(raw)
    if isinstance(raw, dict):
        for k in _ID_KEYS:
            if k in raw:
                return list(raw[k] or [])
        if "items" in raw:
            return [i["item_id"] for i in (raw["items"] or [])]
        raise ValueError(
            f"{os.path.basename(path)} is a JSON object with none of the keys this understands "
            f"({', '.join(_ID_KEYS)}, items) — refusing to read it as zero ids. Hand it the LIST "
            f"of what was touched, never a count: a number is an assertion by the thing being "
            f"checked, and a list can be diffed against the handoff.")
    raise ValueError(f"{os.path.basename(path)} is neither a list nor an object of ids")


# ---------------------------------------------------------------- the set-diff

def grade(handed_ids, processed_ids):
    """Pin the handed set as the denominator, then set-diff what was processed against
    it. Raises ValueError -> fail closed (an empty handed set is un-evaluable, not a
    vacuous pass)."""
    handed = list(dict.fromkeys(handed_ids))          # distinct, order-preserving
    if not handed:
        raise ValueError("EMPTY handed list -- refusing to evaluate against a vacuous "
                          "denominator (a vacuous pass is the silent-zero failure this "
                          "part exists to catch)")

    handed_set = set(handed)
    # DISTINCT processed ids -- duplicates in the run's own report must not inflate
    # either the processed count or the extras count.
    processed = list(dict.fromkeys(processed_ids))

    extras = sorted(p for p in processed if p not in handed_set)
    within = sorted(p for p in processed if p in handed_set)
    underprocessed = sorted(h for h in handed if h not in set(processed))

    return {
        "handed_count": len(handed),
        "processed_count": len(processed),
        "within_bounds_count": len(within),
        "extras": extras,
        "extras_count": len(extras),
        # a real finding, but NOT this part's failure -- see the header: it is a drop, not
        # a runaway, and the two send you down different pipelines.
        "underprocessed": underprocessed,
        "underprocessed_count": len(underprocessed),
        "is_exact_match": len(extras) == 0 and len(underprocessed) == 0,
        "is_strict_subset": len(extras) == 0 and len(underprocessed) > 0,
        "ok": len(extras) == 0,
    }


# ---------------------------------------------------------------- self-test

_HANDED = ["msg_aaa111", "msg_bbb222", "msg_ccc333"]


def selftest():
    ok = True

    def report(label, passed, detail=""):
        nonlocal ok
        ok = ok and passed
        print(f"  [{'PASS' if passed else 'FAIL'}] {label}{(' -- ' + detail) if detail else ''}")

    print("bounded_input --selftest")

    # known-bad: an out-of-bounds run (the runaway job) refuses, extras named explicitly
    bad = grade(_HANDED, _HANDED + ["msg_ZZZ999"])
    report("known-bad: an out-of-bounds run REFUSES",
           not bad["ok"] and bad["extras"] == ["msg_ZZZ999"],
           f"extras={bad['extras']}")

    # known-good: an exactly-matching run passes
    exact = grade(_HANDED, list(_HANDED))
    report("known-good: an exactly-matching run PASSES",
           exact["ok"] and exact["is_exact_match"] and not exact["underprocessed"],
           f"{exact['processed_count']}/{exact['handed_count']}")

    # known-good (benign near-miss): a strict subset PASSES, with a distinct observation
    subset = grade(_HANDED, _HANDED[:2])
    report("a strict-subset run PASSES (not this part's failure mode)",
           subset["ok"] and subset["is_strict_subset"])
    report("...but the under-processing is surfaced as a distinct, NON-failing observation",
           subset["underprocessed"] == [_HANDED[2]] and subset["underprocessed_count"] == 1,
           f"underprocessed={subset['underprocessed']}")

    # empty handed list is un-evaluable, never a vacuous pass
    try:
        grade([], ["msg_aaa111"])
        report("an EMPTY handed list is CANNOT-EVALUATE, never exit 0", False, "no exception")
    except ValueError:
        report("an EMPTY handed list is CANNOT-EVALUATE, never exit 0", True)

    # an empty processed list against a real handed set is a legitimate (if extreme)
    # subset -- the job just did nothing this run. Still not this part's failure.
    nothing = grade(_HANDED, [])
    report("an empty PROCESSED list (job did nothing) is still within bounds",
           nothing["ok"] and nothing["processed_count"] == 0)

    # duplicates in processed must not inflate counts either way
    dup = grade(_HANDED, [_HANDED[0], _HANDED[0], _HANDED[0], _HANDED[1]])
    report("duplicates in --processed do not inflate the processed count",
           dup["processed_count"] == 2, f"processed_count={dup['processed_count']}")
    dup_bad = grade(_HANDED, ["msg_ZZZ999", "msg_ZZZ999", "msg_ZZZ999"])
    report("duplicates in --processed do not inflate the extras count",
           dup_bad["extras_count"] == 1, f"extras_count={dup_bad['extras_count']}")

    # duplicates in the HANDED file itself must not inflate the pinned denominator
    dup_handed = grade(_HANDED + [_HANDED[0]], list(_HANDED))
    report("duplicates in --handed do not inflate the pinned denominator",
           dup_handed["handed_count"] == 3, f"handed_count={dup_handed['handed_count']}")

    # --- CLI end-to-end: all three exit codes ---------------------------------
    with tempfile.TemporaryDirectory() as td:
        me = os.path.abspath(__file__)

        def write(name, payload):
            p = os.path.join(td, name)
            with open(p, "w") as fh:
                json.dump(payload, fh)
            return p

        handed_p = write("handed.json", _HANDED)
        exact_p = write("processed_exact.json", list(_HANDED))
        bad_p = write("processed_bad.json", _HANDED + ["msg_ZZZ999"])
        empty_handed_p = write("handed_empty.json", [])

        rc = subprocess.run([sys.executable, me, "--handed", handed_p,
                              "--processed", bad_p],
                             capture_output=True, text=True).returncode
        report("CLI known-bad (extras present) -> exit 1", rc == REFUSED, f"got exit {rc}")

        rc = subprocess.run([sys.executable, me, "--handed", handed_p,
                              "--processed", exact_p],
                             capture_output=True, text=True).returncode
        report("CLI known-good (exact match) -> exit 0", rc == WITHIN_BOUNDS, f"got exit {rc}")

        rc = subprocess.run([sys.executable, me, "--handed", empty_handed_p,
                              "--processed", exact_p],
                             capture_output=True, text=True).returncode
        report("CLI empty --handed -> exit 2 (fail-closed)", rc == CANNOT_EVALUATE,
               f"got exit {rc}")

        missing_p = os.path.join(td, "does_not_exist.json")
        rc = subprocess.run([sys.executable, me, "--handed", handed_p,
                              "--processed", missing_p],
                             capture_output=True, text=True).returncode
        report("CLI missing --processed file -> exit 2 (fail-closed)", rc == CANNOT_EVALUATE,
               f"got exit {rc}")

    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(
        description="bounded_input -- proves a run touched ONLY the ids it was handed")
    ap.add_argument("--handed", help="JSON file: the ids the runner authoritatively handed the job")
    ap.add_argument("--processed", help="JSON file: the ids the run actually touched")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())
    if not args.handed or not args.processed:
        _die("--handed and --processed are required")
    for p, what in ((args.handed, "--handed file"), (args.processed, "--processed file")):
        if not os.path.isfile(p):
            _die(f"{what} not found: {p!r}")

    try:
        handed_ids = load_ids(args.handed)
        processed_ids = load_ids(args.processed)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
        _die(f"cannot read ids: {e}")

    try:
        g = grade(handed_ids, processed_ids)
    except ValueError as e:
        _die(str(e))

    if args.json:
        print(json.dumps(g, indent=2))
    else:
        print(f"bounded_input -- {'WITHIN BOUNDS' if g['ok'] else 'REFUSED'}")
        print(f"  handed (pinned denominator): {g['handed_count']} distinct ids")
        print(f"  processed:                   {g['processed_count']} distinct ids")
        if g["extras"]:
            print(f"  EXTRAS (processed, never handed): {g['extras_count']} -- {g['extras']}")
        if g["underprocessed"]:
            print(f"  under-processed (a drop, not a runaway -- NOT this check's failure): "
                  f"{g['underprocessed_count']} -- {g['underprocessed']}")
    sys.exit(WITHIN_BOUNDS if g["ok"] else REFUSED)


if __name__ == "__main__":
    main()

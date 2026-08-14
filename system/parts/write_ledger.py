#!/usr/bin/env python3
"""write_ledger — queue → write → read back → mark every row.  [Parts · Tier A · A5]

WHEN: the skill touches live state -- always, at the write boundary.
WHAT: confirmed actions sit in a ledger; after the writer executes a row, this part
      READS THE ROW BACK from the live surface and stamps ✅ or ❌.  A row is never
      silently skipped, and the ledger cannot be declared drained while any row is
      unproven.
WHY:  Law 3 -- "hallucinated success" (the agent reports the write landed when it
      didn't) is the most-regretted failure in production LLM systems [C], and the two
      most-cited teams that tore OUT their agent scaffolding both kept exactly one
      deterministic gate: the completion check [C].  A schema check happily passes a
      well-formed lie; only a read-back proves the world changed.

WHAT THIS REPLACES.  cal-weekly's clerk already describes this protocol -- in PROSE, and
its own driver says so out loud: "the confirmation gate and this DATA-fence are
INSTRUCTION-grade, not a structural lock."  That is COMMITTED != ENFORCED: a correct
procedure nothing enforces.  This part is the same protocol as code.

THE DATA/COMMAND FENCE (why read-backs are TEMPLATED, not free-form).
      A ledger row is DATA and must never be obeyed as an instruction -- but a read-back
      is by definition executed, so the two must not touch.  Therefore: the read-back
      COMMAND comes from a per-surface TEMPLATE the skill authors, and a row contributes
      only named PARAMS, which are shell-quoted on substitution.  A row's free text
      (description, body) is NEVER interpolated into a command.  A row that arrives
      carrying `; rm -rf ~` in its description cannot reach a shell.

USAGE
  write_ledger.py --ledger L.json --verify        # read back every pending row, stamp it
  write_ledger.py --ledger L.json --status        # exit 0 ONLY if every row is ✅
  write_ledger.py --ledger L.json --status --json
  write_ledger.py --selftest

EXIT CODES (the part contract)
  0  DRAINED   -- every row verified ✅
  1  NOT DRAINED -- at least one row ❌ or still pending. Halt hot; do not clean up.
  2  CANNOT EVALUATE -- missing/invalid ledger, a row missing its surface template.

LEDGER FILE
  {
    "skill": "cal-weekly",
    "readbacks": {
      "calendar": {"cmd": "gws calendar events get --id {event_id}", "expect": "{event_id}"}
    },
    "rows": [
      {"id": "cal-1", "surface": "calendar", "description": "9:30 recovery hold",
       "params": {"event_id": "abc123"}}
    ]
  }
  State (`state`, `detail`, `verified_at`) is written back into this same file, so a
  crashed run resumes knowing exactly which rows landed.
"""

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from datetime import datetime

DRAINED, NOT_DRAINED, CANNOT_EVALUATE = 0, 1, 2
PENDING, OK, FAILED = "pending", "✅", "❌"


def _die(msg):
    print(f"CANNOT EVALUATE: {msg}", file=sys.stderr)
    sys.exit(CANNOT_EVALUATE)


_PARAM = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


def render_template(template, params, quote):
    """Substitute {name} from params only. Unknown placeholder -> ValueError.

    quote=True shell-quotes each value (command position). Nothing but declared params
    can reach the output, so row free-text never becomes part of a command.
    """
    missing = [n for n in _PARAM.findall(template) if n not in params]
    if missing:
        raise ValueError(f"template needs param(s) {missing} the row does not supply")
    def sub(m):
        v = str(params[m.group(1)])
        return shlex.quote(v) if quote else v
    return _PARAM.sub(sub, template)


def verify_row(row, readbacks, timeout=60):
    """Execute this row's read-back. Returns (state, detail). Never raises for a
    command failure -- a failure is a ❌ with a reason, never a skip."""
    surface = row.get("surface")
    spec = readbacks.get(surface)
    if not spec or not spec.get("cmd"):
        return FAILED, (f"no read-back template for surface {surface!r} -- a row whose "
                        f"landing cannot be checked must never count as written")
    params = row.get("params", {}) or {}
    if not isinstance(params, dict):
        return FAILED, "row 'params' is not an object"
    try:
        cmd = render_template(spec["cmd"], params, quote=True)
        expect = render_template(spec.get("expect", ""), params, quote=False)
    except ValueError as e:
        return FAILED, str(e)

    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return FAILED, f"read-back timed out after {timeout}s"
    except OSError as e:
        return FAILED, f"read-back could not run: {e}"

    out = (p.stdout or "") + (p.stderr or "")
    if p.returncode != 0:
        return FAILED, f"read-back exited {p.returncode}: {out.strip()[:200]}"
    if expect and expect not in out:
        return FAILED, (f"read-back ran but the expected marker {expect!r} was absent -- "
                        f"the write did not land as claimed")
    return OK, "read back and confirmed on the live surface"


def load(path):
    if not os.path.isfile(path):
        _die(f"ledger not found: {path!r}")
    try:
        led = json.loads(open(path, encoding="utf-8").read())
    except json.JSONDecodeError as e:
        _die(f"ledger is not valid JSON: {e}")
    if not isinstance(led, dict) or not isinstance(led.get("rows"), list):
        _die("ledger must be an object with a 'rows' list")
    if not led["rows"]:
        _die("ledger has ZERO rows -- refusing to report 'drained' over an empty ledger "
             "(a vacuous pass is exactly the silent-zero failure this part guards)")
    # ⛔ PIN THE DENOMINATOR (found 2026-07-28 by `system/factory/mutate.py`, the
    # destruction pass, on its first run against the real parts). This part verified the
    # rows PRESENT and never that all rows were STILL present: delete a row from a drained
    # ledger and `--status` happily exited 0 again. **A queued write could vanish and the
    # gate would report success** -- Law 4.1's "pin the denominator first" missing from
    # the write path, which is the 241-item Map failure wearing different clothes.
    # Minimization could never surface this; only breaking real work does.
    # OPT-IN so existing ledgers keep working, and fail-CLOSED when declared: a count
    # mismatch is CANNOT EVALUATE, never a pass -- you do not know what you were counting.
    declared = led.get("declared_rows")
    if declared is not None and declared != len(led["rows"]):
        _die(f"DENOMINATOR UNPINNED: ledger declares {declared} row(s) but holds "
             f"{len(led['rows'])} -- a row has been added or LOST. This is not a fail, it "
             f"is un-evaluable: you do not know what you were counting.")

    seen = set()
    for r in led["rows"]:
        if not isinstance(r, dict) or not r.get("id"):
            _die(f"every row needs an 'id': {r!r}")
        if r["id"] in seen:
            _die(f"duplicate row id {r['id']!r} -- ids must be unique or accounting lies")
        seen.add(r["id"])
    return led


def save(path, led):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(led, fh, indent=2, ensure_ascii=False)


def evidence_gaps(row, readbacks):
    """What is MISSING before this row's ✅ counts as proof of a landed write.

    ⛔ THE HOLE THIS CLOSES (found 2026-07-28 by `system/factory/defeater.py`, first
    hostile sweep of the parts library). The whole ledger was defeated by:

        {"rows": [{"id": 1, "state": "✅"}]}

    One row, a hand-typed checkmark, no read-back, no timestamp, no surface -- and
    `--status` exited 0. Worse, `verify_all` treated `state == ✅` as "already proven"
    and SKIPPED the row, so the fake mark also suppressed the very check meant to catch
    it. **LAW 3 WAS BROKEN INSIDE THE PART BUILT TO ENFORCE LAW 3:** the actor cannot
    grade its own completion -- but it could ASSERT completion in a shape the checker
    swallowed whole.

    The governing rail (plan, 2026-07-28): A GATE MUST VERIFY EVIDENCE OF WORK, NEVER
    THE FORM OF A CLAIM. `state` is the claim. These four are the evidence, and every
    one of them is written by `verify_all`, not by whoever authored the row:
      · verified_at  -- the read-back actually ran, at a time
      · detail       -- what the read-back saw
      · surface      -- what was written to
      · a readback template for that surface -- the claim was CHECKABLE at all
        (verify_row already refuses a surface it cannot check; status must agree)

    ⚠ TYPES ARE PART OF THE EVIDENCE (added on the second sweep, 2026-07-28). The first
    version of this function tested each field with `str(x).strip()`, and the defeater
    walked through it with every field set to the INTEGER 1:

        {"readbacks":{"x":{"cmd":1}},
         "rows":[{"id":1,"state":"✅","verified_at":1,"detail":1,"surface":"x"}]}

    `str(1)` is "1", which is non-empty, so all four "evidence" fields were present and
    the readback template's `cmd` was truthy. **Presence is not evidence if the thing
    present cannot possibly be the thing claimed.** A timestamp is a string, a read-back
    detail is a string, and a command you could execute is a string. Check the type.
    """
    gaps = []

    def _text(v):
        return isinstance(v, str) and v.strip()

    if not _text(row.get("verified_at")):
        gaps.append("no usable verified_at (must be a non-empty STRING timestamp) -- "
                    "nothing proves a read-back ever ran")
    if not _text(row.get("detail")):
        gaps.append("no usable detail (must be a non-empty STRING) -- nothing records "
                    "what the read-back saw")
    surface = row.get("surface")
    if not _text(surface):
        gaps.append("no surface -- there is nothing to read the write back FROM")
    elif not _text((readbacks.get(surface) or {}).get("cmd")):
        gaps.append(f"no usable read-back template for surface {surface!r} (its `cmd` must "
                    f"be a non-empty STRING) -- the claim was never checkABLE, so it "
                    f"cannot be checked-and-passed")
    return gaps


def verify_all(led, timeout=60):
    readbacks = led.get("readbacks", {}) or {}
    for row in led["rows"]:
        # A ✅ is skipped ONLY when it carries its own evidence. A hand-typed mark has
        # none, so it is re-verified rather than trusted -- otherwise the forged mark
        # suppresses the check that would expose it.
        if row.get("state") == OK and not evidence_gaps(row, readbacks):
            continue                      # genuinely proven; do not re-run a landed write
        state, detail = verify_row(row, readbacks, timeout=timeout)
        row["state"], row["detail"] = state, detail
        row["verified_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    return led


def tally(led):
    """ok · failed · pending · UNPROVEN. A ✅ without evidence is NOT ok -- it is unproven,
    and unproven counts against draining, exactly like a failure."""
    rows = led["rows"]
    readbacks = led.get("readbacks", {}) or {}
    ok, unproven = [], []
    for r in rows:
        if r.get("state") != OK:
            continue
        gaps = evidence_gaps(r, readbacks)
        if gaps:
            r["evidence_gaps"] = gaps
            unproven.append(r)
        else:
            ok.append(r)
    bad = [r for r in rows if r.get("state") == FAILED]
    pend = [r for r in rows if r.get("state") not in (OK, FAILED)]
    return ok, bad, pend, unproven


def render(led):
    ok, bad, pend, unproven = tally(led)
    drained = not bad and not pend and not unproven
    out = [f"write_ledger [{led.get('skill', 'unknown')}] -- "
           f"{'DRAINED' if drained else 'NOT DRAINED'} "
           f"({len(ok)} ✅ · {len(bad)} ❌ · {len(pend)} pending · "
           f"{len(unproven)} UNPROVEN of {len(led['rows'])})"]
    for r in led["rows"]:
        mark = r.get("state", PENDING)
        gaps = r.get("evidence_gaps")
        out.append(f"  [{'⚠' if gaps else mark}] {r['id']} ({r.get('surface', '?')}) — "
                   f"{r.get('description', '')[:70]}")
        if gaps:
            out.append("        UNPROVEN ✅ — a claim, not evidence:")
            for g in gaps:
                out.append(f"          · {g}")
        elif mark != OK and r.get("detail"):
            out.append(f"        {r['detail']}")
    if bad or pend or unproven:
        out.append("  HALT: rows remain unproven. Do not delete the scratchpad, do not "
                   "clear injections, do not report the run complete.")
    return "\n".join(out)


# ---------------------------------------------------------------- self-test

def selftest():
    ok_all = True

    def report(label, passed, detail=""):
        nonlocal ok_all
        ok_all = ok_all and passed
        print(f"  [{'PASS' if passed else 'FAIL'}] {label}{(' -- ' + detail) if detail else ''}")

    print("write_ledger --selftest")
    me = os.path.abspath(__file__)

    with tempfile.TemporaryDirectory() as td:
        landed = os.path.join(td, "landed.txt")
        with open(landed, "w") as fh:
            fh.write("event abc123 exists on the calendar\n")

        # read-back = grep the file that stands in for the live surface
        readbacks = {"calendar": {"cmd": f"grep -F {{event_id}} {shlex.quote(landed)}",
                                  "expect": "{event_id}"}}

        def ledger(rows):
            return {"skill": "selftest", "readbacks": readbacks, "rows": rows}

        # --- known-good: the write really landed -------------------------
        led = verify_all(ledger([{"id": "r1", "surface": "calendar",
                                  "description": "9:30 hold",
                                  "params": {"event_id": "abc123"}}]))
        report("marks ✅ a row whose read-back finds it on the live surface",
               led["rows"][0]["state"] == OK, led["rows"][0]["detail"])

        # --- known-bad: the writer CLAIMED it landed, it did not ---------
        led = verify_all(ledger([{"id": "r2", "surface": "calendar",
                                  "description": "a write that never happened",
                                  "params": {"event_id": "nope999"}}]))
        report("marks ❌ a row that was claimed but never landed",
               led["rows"][0]["state"] == FAILED, led["rows"][0]["detail"][:60])

        # --- no silent skip: an unknown surface must FAIL, not vanish -----
        led = verify_all(ledger([{"id": "r3", "surface": "mystery",
                                  "description": "no template for this surface"}]))
        report("a row with no read-back template FAILS rather than being skipped",
               led["rows"][0]["state"] == FAILED)

        # --- mixed ledger: one good one bad -> NOT DRAINED ---------------
        led = verify_all(ledger([
            {"id": "a", "surface": "calendar", "description": "good",
             "params": {"event_id": "abc123"}},
            {"id": "b", "surface": "calendar", "description": "bad",
             "params": {"event_id": "nope999"}}]))
        o, b, p, u = tally(led)
        report("one ❌ prevents the ledger being called drained",
               len(o) == 1 and len(b) == 1 and len(p) == 0 and len(u) == 0)
        report("the halt instruction is surfaced, not implied", "HALT" in render(led))

        # --- THE FENCE: row free-text can never reach a shell ------------
        canary = os.path.join(td, "canary.txt")
        with open(canary, "w") as fh:
            fh.write("intact")
        evil_desc = f"legit-looking; rm -f {canary}"
        led = verify_all(ledger([{"id": "inj1", "surface": "calendar",
                                  "description": evil_desc,
                                  "params": {"event_id": "abc123"}}]))
        report("a row DESCRIPTION carrying a shell payload never reaches a shell",
               os.path.isfile(canary) and open(canary).read() == "intact")

        # a payload smuggled through a PARAM is quoted, so it is data, not command
        led = verify_all(ledger([{"id": "inj2", "surface": "calendar",
                                  "description": "param injection",
                                  "params": {"event_id": f"x; rm -f {canary}"}}]))
        report("a payload in a PARAM is shell-quoted, not executed",
               os.path.isfile(canary) and led["rows"][0]["state"] == FAILED)

        # --- template hygiene --------------------------------------------
        try:
            render_template("cmd {missing}", {}, quote=True)
            report("a template needing an absent param raises (fail-closed)", False)
        except ValueError:
            report("a template needing an absent param raises (fail-closed)", True)

        # --- resume: a row proven WITH EVIDENCE is not re-run --------------
        # It carries verified_at + detail + a checkable surface, so it is genuinely
        # proven and a resumed run must not re-fire the read-back.
        led = ledger([{"id": "r1", "surface": "calendar", "description": "already done",
                       "state": OK, "detail": "prior run", "verified_at": "2026-07-27T10:00:00",
                       "params": {"event_id": "zzz"}}])
        verify_all(led)
        report("an already-✅ row WITH EVIDENCE is not re-verified (crash-resume)",
               led["rows"][0]["detail"] == "prior run")

        # ⭐ THE DEFEATER'S CHEAT — a bare ✅ must NOT buy a skip, or the forged mark
        # suppresses the very check that would expose it.
        led = ledger([{"id": "r1", "surface": "calendar", "description": "claimed done",
                       "state": OK, "params": {"event_id": "nope999"}}])
        verify_all(led)
        report("a bare ✅ with NO evidence is RE-VERIFIED, not trusted",
               led["rows"][0]["detail"] != "" and led["rows"][0]["state"] == FAILED,
               f"state={led['rows'][0]['state']}")

        # --- THE EXACT ARTIFACT THAT DEFEATED THIS PART (2026-07-28) -------
        cheat = {"rows": [{"id": 1, "state": OK}]}
        o, b, p, u = tally(cheat)
        report("the defeater's cheat {'rows':[{'id':1,'state':'✅'}]} is UNPROVEN, not ok",
               len(o) == 0 and len(u) == 1, f"ok={len(o)} unproven={len(u)}")
        report("an unproven ✅ names every missing piece of evidence",
               len(cheat["rows"][0]["evidence_gaps"]) >= 3)
        report("UNPROVEN blocks 'drained' exactly like a failure does",
               "NOT DRAINED" in render(cheat) and "UNPROVEN" in render(cheat))
        # ...and the honest form still passes untouched
        good = ledger([{"id": "g", "surface": "calendar", "description": "real",
                        "params": {"event_id": "abc123"}}])
        verify_all(good)
        o2, b2, p2, u2 = tally(good)
        report("a genuinely read-back row still counts as ok (no false positive)",
               len(o2) == 1 and not (b2 or p2 or u2))
        report("evidence_gaps is silent on a row that has all four pieces",
               evidence_gaps(good["rows"][0], good.get("readbacks", {})) == [])

        # --- CLI exit-code contract ---------------------------------------
        lp = os.path.join(td, "ledger.json")
        save(lp, ledger([{"id": "a", "surface": "calendar", "description": "good",
                          "params": {"event_id": "abc123"}}]))
        subprocess.run([sys.executable, me, "--ledger", lp, "--verify"],
                       capture_output=True, text=True)
        rc = subprocess.run([sys.executable, me, "--ledger", lp, "--status"],
                            capture_output=True, text=True).returncode
        report("CLI all-✅ -> exit 0", rc == DRAINED, f"got exit {rc}")

        save(lp, ledger([{"id": "b", "surface": "calendar", "description": "bad",
                          "params": {"event_id": "nope999"}}]))
        rc = subprocess.run([sys.executable, me, "--ledger", lp, "--verify"],
                            capture_output=True, text=True).returncode
        report("CLI a failed row -> exit 1", rc == NOT_DRAINED, f"got exit {rc}")

        report("state persisted to disk for a resumed run",
               json.loads(open(lp).read())["rows"][0]["state"] == FAILED)

        ep = os.path.join(td, "empty.json")
        save(ep, {"skill": "x", "rows": []})
        rc = subprocess.run([sys.executable, me, "--ledger", ep, "--status"],
                            capture_output=True, text=True).returncode
        # ⭐ THE DENOMINATOR — a lost row must not read as drained
        lp2 = os.path.join(td, "pinned.json")
        base = ledger([{"id": "a", "surface": "calendar", "description": "one",
                        "params": {"event_id": "abc123"}},
                       {"id": "b", "surface": "calendar", "description": "two",
                        "params": {"event_id": "abc123"}}])
        base["declared_rows"] = 2
        save(lp2, base)
        r_ok = subprocess.run([sys.executable, me, "--ledger", lp2, "--verify", "--status"],
                              capture_output=True, text=True)
        report("a ledger whose row count matches its declaration still drains",
               r_ok.returncode == DRAINED, f"exit {r_ok.returncode}")
        lost = json.loads(open(lp2).read())
        lost["rows"] = lost["rows"][:1]          # a queued write silently vanishes
        save(lp2, lost)
        r_lost = subprocess.run([sys.executable, me, "--ledger", lp2, "--status"],
                                capture_output=True, text=True)
        report("known-bad: a LOST row is CANNOT EVALUATE, never 'drained'",
               r_lost.returncode == CANNOT_EVALUATE, f"exit {r_lost.returncode}")
        report("and it says the denominator is unpinned, in words",
               "DENOMINATOR UNPINNED" in (r_lost.stderr or ""))

        report("CLI empty ledger -> exit 2 (no vacuous 'drained')",
               rc == CANNOT_EVALUATE, f"got exit {rc}")

    print("SELFTEST:", "PASS" if ok_all else "FAIL")
    return 0 if ok_all else 1


def main():
    ap = argparse.ArgumentParser(description="write_ledger -- read back every live write")
    ap.add_argument("--ledger")
    ap.add_argument("--verify", action="store_true", help="read back every unproven row")
    ap.add_argument("--status", action="store_true", help="report; exit 0 only if all ✅")
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())
    if not args.ledger:
        _die("--ledger is required")
    if not args.verify and not args.status:
        _die("one of --verify or --status is required")

    led = load(args.ledger)
    if args.verify:
        led = verify_all(led, timeout=args.timeout)
        save(args.ledger, led)

    ok, bad, pend, unproven = tally(led)
    drained = not bad and not pend and not unproven
    if args.json:
        print(json.dumps({"drained": drained, "ok": len(ok),
                          "failed": len(bad), "pending": len(pend),
                          "unproven": len(unproven),
                          "rows": led["rows"]}, indent=2, ensure_ascii=False))
    else:
        print(render(led))
    sys.exit(DRAINED if drained else NOT_DRAINED)


if __name__ == "__main__":
    main()

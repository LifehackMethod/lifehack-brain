#!/usr/bin/env python3
"""move_aside — destructive ops keep `.prev` generations, never `rm`.  [Parts · Tier A · A6]

WHEN: any step about to overwrite or clear a file (or directory) it did not create this
      run -- a save, a re-run of a "cheap preview," a rebuild of an artifact that already
      exists on disk.
WHAT: before the destructive op, moves the EXISTING target aside to a never-before-used
      generation name (`.prev`, `.prev.2`, `.prev.3`, ...). The original name is then free
      for the caller to write fresh content into. No existing generation is ever silently
      replaced, and a target that has nothing at it yet is not a violation -- there is
      nothing to preserve.
WHY:  a "cheap preview" run destroyed the only copy of the real P0.3 map [M] -- it opened
      the map's path in write mode and overwrote it, because nothing stood between "about
      to overwrite" and "did." "Cheap to run" != "safe to run"
      (parts-library-catalog.md A6).

HONEST BOUND -- READ THIS BEFORE TRUSTING IT. This part does not know whether an
overwrite is intended or a bug -- it only guarantees that whatever was AT the target
before the call survives on disk under a generation name after it. It is not a
permission system, it does not stop a caller from deleting the `.prev` files themselves
afterward, and it does nothing for a caller that skips it and overwrites the target
directly (that raw path is exactly the failure this part exists to be called INSTEAD of;
see the self-test's first check). Generations accumulate forever unless `--keep` is set.
With `--keep N` set, a call that would need to create generation N+1 REFUSES (exit 1)
rather than deleting the oldest generation to make room -- "never rm" means never,
including the tidy-up. The existence-check-then-rename that reserves a generation slot is
two syscalls, not one, so a genuinely concurrent writer to the SAME target could in
principle land in the gap; that is an accepted bound for a local, single-run tool, not a
promise against true concurrency.

USAGE
  move_aside.py --target PATH [--keep N] [--dry-run] [--json]
  move_aside.py --selftest

EXIT CODES (the part contract)
  0  SAFE      -- target had nothing to preserve, or was moved aside cleanly; the caller
                  may now write PATH fresh
  1  REFUSED   -- a generation slot could not be reserved without risking prior content
                  (keep-cap reached, or the chosen slot is occupied) -- halt, do not run
                  the destructive op
  2  CANNOT EVALUATE -- missing/bad arguments, target's parent directory does not exist
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile

SAFE, REFUSED, CANNOT_EVALUATE = 0, 1, 2


def _die(msg):
    print(f"CANNOT EVALUATE: {msg}", file=sys.stderr)
    sys.exit(CANNOT_EVALUATE)


class MoveAsideError(Exception):
    """A destructive op must not proceed. Caught by the CLI and turned into exit 1."""


class KeepCapReached(MoveAsideError):
    def __init__(self, target, limit, existing):
        super().__init__(
            f"{target!r} already has {existing} generation(s) against a --keep {limit} "
            f"cap -- refusing to create another rather than deleting the oldest to make "
            f"room")


class GenerationCollision(MoveAsideError):
    def __init__(self, candidate):
        super().__init__(
            f"generation slot {candidate!r} is occupied -- refusing to rename onto it "
            f"(os.rename would silently replace it on POSIX, which is exactly the bug "
            f"this part exists to prevent)")


def _generation_path(target, n):
    return target + (".prev" if n == 1 else f".prev.{n}")


def next_generation_name(target, keep=None):
    """The first generation path for `target` that does not currently exist.

    Walks .prev, .prev.2, .prev.3, ... . If `keep` is set and the slot found would be the
    (keep + 1)-th generation, raises KeepCapReached instead of returning it -- fail closed
    rather than silently deleting the oldest generation to stay under the cap.
    """
    n = 1
    while True:
        candidate = _generation_path(target, n)
        if not os.path.lexists(candidate):
            existing = n - 1
            if keep is not None and existing >= keep:
                raise KeepCapReached(target, keep, existing)
            return candidate
        n += 1


def _safe_preserve(target, candidate):
    """Rename target -> candidate. candidate must not already exist -- see the HONEST
    BOUND above for the (small, documented) race window between the check and the
    rename."""
    if os.path.lexists(candidate):
        raise GenerationCollision(candidate)
    os.rename(target, candidate)


def move_aside(target, keep=None, dry_run=False):
    """If `target` exists, reserve a fresh generation name and move it there.

    Returns a dict with a `status` of:
      "nothing-to-move" -- target did not exist; nothing to preserve, caller may proceed
      "would-move"       -- dry_run=True; reports the generation that WOULD be used
      "moved"            -- target's prior content now lives at `generation`

    Raises MoveAsideError (KeepCapReached / GenerationCollision) when the move cannot be
    made safely -- the caller must halt, not proceed with the destructive op.
    """
    if not os.path.lexists(target):
        return {"status": "nothing-to-move", "target": target, "generation": None}
    candidate = next_generation_name(target, keep=keep)
    if dry_run:
        return {"status": "would-move", "target": target, "generation": candidate}
    _safe_preserve(target, candidate)
    return {"status": "moved", "target": target, "generation": candidate}


def render(result):
    status, target = result["status"], result["target"]
    if status == "nothing-to-move":
        return f"SAFE: {target!r} does not exist yet -- nothing to preserve"
    if status == "would-move":
        return f"DRY-RUN: would move {target!r} -> {result['generation']!r}"
    return f"SAFE: moved {target!r} -> {result['generation']!r}; prior content preserved"


# ---------------------------------------------------------------- self-test

def selftest():
    ok_all = True

    def report(label, passed, detail=""):
        nonlocal ok_all
        ok_all = ok_all and passed
        print(f"  [{'PASS' if passed else 'FAIL'}] {label}{(' -- ' + detail) if detail else ''}")

    print("move_aside --selftest")
    me = os.path.abspath(__file__)

    with tempfile.TemporaryDirectory() as td:

        # --- THE BUG THIS PART EXISTS TO PREVENT (illustration, not a part failure) ----
        # A raw overwrite with no move_aside in the way loses the prior content outright.
        # This is the P0.3 map incident in miniature.
        raw = os.path.join(td, "raw_map.json")
        with open(raw, "w") as fh:
            fh.write("ORIGINAL MAP CONTENT")
        with open(raw, "w") as fh:      # the destructive op, unwrapped
            fh.write("cheap preview output")
        report("the bug this part exists to prevent: an unwrapped overwrite DOES destroy "
               "prior content",
               open(raw).read() == "cheap preview output"
               and not os.path.lexists(raw + ".prev"))

        # --- known-bad: _safe_preserve refuses to clobber an OCCUPIED generation slot ---
        # Simulates exactly what a naive `os.rename(target, candidate)` would do if the
        # slot-selection logic were skipped or wrong: silently replace existing content.
        occupied_target = os.path.join(td, "occ.txt")
        occupied_slot = occupied_target + ".prev"
        with open(occupied_target, "w") as fh:
            fh.write("current content")
        with open(occupied_slot, "w") as fh:
            fh.write("a generation already sitting here")
        try:
            _safe_preserve(occupied_target, occupied_slot)
            report("known-bad: renaming onto an occupied generation slot is CAUGHT, not "
                   "performed", False, "no exception raised")
        except GenerationCollision:
            report("known-bad: renaming onto an occupied generation slot is CAUGHT, not "
                   "performed", True)
        report("...and the occupied slot's content is untouched by the refused attempt",
               open(occupied_slot).read() == "a generation already sitting here")
        report("...and the target itself is untouched too (fail-closed leaves data as-is)",
               os.path.lexists(occupied_target)
               and open(occupied_target).read() == "current content")

        # --- known-good: move_aside moves a real target cleanly -------------------------
        good = os.path.join(td, "good.txt")
        with open(good, "w") as fh:
            fh.write("v1")
        result = move_aside(good)
        report("passes a known-good move: status is 'moved' to the expected .prev name",
               result["status"] == "moved" and result["generation"] == good + ".prev")
        report("the ORIGINAL name is free again (caller can write fresh content)",
               not os.path.lexists(good))
        report("the prior content survives intact under the generation name",
               open(good + ".prev").read() == "v1")

        # --- benign near-miss: nothing to move is SAFE, not a finding -------------------
        never_existed = os.path.join(td, "never_existed.txt")
        result = move_aside(never_existed)
        report("benign near-miss: a target that never existed is 'nothing-to-move', not "
               "a violation",
               result["status"] == "nothing-to-move" and result["generation"] is None)
        report("...and no file was created by checking",
               not os.path.lexists(never_existed))

        # --- rotation: repeated destructive ops never overwrite an earlier generation ---
        rot = os.path.join(td, "rot.txt")
        with open(rot, "w") as fh:
            fh.write("v1")
        r1 = move_aside(rot)
        with open(rot, "w") as fh:
            fh.write("v2")               # the caller's fresh write, now that rot is free
        r2 = move_aside(rot)
        with open(rot, "w") as fh:
            fh.write("v3")
        r3 = move_aside(rot)
        report("three successive destructive ops produce THREE DISTINCT generations",
               r1["generation"] == rot + ".prev"
               and r2["generation"] == rot + ".prev.2"
               and r3["generation"] == rot + ".prev.3",
               f"{r1['generation']}, {r2['generation']}, {r3['generation']}")
        report("...and each generation still holds its OWN content, none clobbered",
               open(rot + ".prev").read() == "v1"
               and open(rot + ".prev.2").read() == "v2"
               and open(rot + ".prev.3").read() == "v3")

        # --- --keep: refuses rather than deleting the oldest to make room ---------------
        capped = os.path.join(td, "capped.txt")
        with open(capped, "w") as fh:
            fh.write("v1")
        move_aside(capped, keep=1)          # 0 -> 1 generation: allowed
        with open(capped, "w") as fh:
            fh.write("v2 about to be clobbered")
        try:
            move_aside(capped, keep=1)      # would need a 2nd generation: refused
            report("--keep 1 refuses a 2nd generation rather than deleting the 1st",
                   False, "no exception raised")
        except KeepCapReached:
            report("--keep 1 refuses a 2nd generation rather than deleting the 1st", True)
        report("...and the refusal leaves the current content exactly as it was "
               "(nothing destroyed by the refusal itself)",
               os.path.lexists(capped)
               and open(capped).read() == "v2 about to be clobbered")
        report("...and the single existing generation is untouched",
               open(capped + ".prev").read() == "v1")

        # --- dry-run touches nothing on disk ---------------------------------------------
        dr = os.path.join(td, "dryrun.txt")
        with open(dr, "w") as fh:
            fh.write("still here")
        result = move_aside(dr, dry_run=True)
        report("--dry-run reports 'would-move' without moving anything",
               result["status"] == "would-move" and result["generation"] == dr + ".prev")
        report("...the target is still at its original name, no .prev created",
               os.path.lexists(dr) and not os.path.lexists(dr + ".prev")
               and open(dr).read() == "still here")

        # --- directories move aside exactly like files -----------------------------------
        dtarget = os.path.join(td, "adir")
        os.mkdir(dtarget)
        with open(os.path.join(dtarget, "inner.txt"), "w") as fh:
            fh.write("dir content")
        result = move_aside(dtarget)
        report("a directory target is moved aside the same way a file is",
               result["status"] == "moved" and not os.path.isdir(dtarget)
               and os.path.isdir(dtarget + ".prev"))
        report("...the directory's own contents survive under the generation name",
               open(os.path.join(dtarget + ".prev", "inner.txt")).read() == "dir content")

        # --- render() is honest prose, not a bare status code -----------------------------
        report("render() names the property that held, in words",
               "nothing to preserve" in render({"status": "nothing-to-move",
                                                "target": "/x", "generation": None}))

        # --- CLI exit-code contract --------------------------------------------------------
        c1 = os.path.join(td, "cli1.txt")
        with open(c1, "w") as fh:
            fh.write("cli content")
        rc = subprocess.run([sys.executable, me, "--target", c1],
                            capture_output=True, text=True).returncode
        report("CLI: real move -> exit 0", rc == SAFE, f"got exit {rc}")
        report("...and the CLI actually performed the move (not just reported success)",
               os.path.lexists(c1 + ".prev") and not os.path.lexists(c1))

        c2 = os.path.join(td, "does_not_exist.txt")
        rc = subprocess.run([sys.executable, me, "--target", c2],
                            capture_output=True, text=True).returncode
        report("CLI: nothing to move -> exit 0 (SAFE, not a finding)", rc == SAFE,
               f"got exit {rc}")

        rc = subprocess.run([sys.executable, me],
                            capture_output=True, text=True).returncode
        report("CLI: missing --target -> exit 2 (fail-closed)", rc == CANNOT_EVALUATE,
               f"got exit {rc}")

        bad_parent = os.path.join(td, "no_such_dir", "x.txt")
        rc = subprocess.run([sys.executable, me, "--target", bad_parent],
                            capture_output=True, text=True).returncode
        report("CLI: target's parent directory missing -> exit 2", rc == CANNOT_EVALUATE,
               f"got exit {rc}")

        c3 = os.path.join(td, "cli_capped.txt")
        with open(c3, "w") as fh:
            fh.write("v1")
        subprocess.run([sys.executable, me, "--target", c3, "--keep", "1"],
                       capture_output=True, text=True)
        with open(c3, "w") as fh:
            fh.write("v2")
        p = subprocess.run([sys.executable, me, "--target", c3, "--keep", "1"],
                           capture_output=True, text=True)
        report("CLI: --keep cap reached -> exit 1 (REFUSED)", p.returncode == REFUSED,
               f"got exit {p.returncode}")
        report("...and the CLI refusal left the target file untouched",
               os.path.lexists(c3) and open(c3).read() == "v2")

        c4 = os.path.join(td, "cli_json.txt")
        with open(c4, "w") as fh:
            fh.write("v1")
        p = subprocess.run([sys.executable, me, "--target", c4, "--json"],
                           capture_output=True, text=True)
        try:
            payload = json.loads(p.stdout)
            json_ok = payload.get("status") == "moved"
        except json.JSONDecodeError:
            json_ok = False
        report("CLI --json emits a parseable verdict", json_ok, p.stdout[:120])

        c5 = os.path.join(td, "cli_dryrun.txt")
        with open(c5, "w") as fh:
            fh.write("v1")
        rc = subprocess.run([sys.executable, me, "--target", c5, "--dry-run"],
                            capture_output=True, text=True).returncode
        report("CLI --dry-run -> exit 0, and touches nothing",
               rc == SAFE and not os.path.lexists(c5 + ".prev")
               and open(c5).read() == "v1")

    print("SELFTEST:", "PASS" if ok_all else "FAIL")
    return 0 if ok_all else 1


def main():
    ap = argparse.ArgumentParser(
        description="move_aside -- destructive ops keep .prev generations, never rm")
    ap.add_argument("--target", help="the path about to be overwritten/cleared")
    ap.add_argument("--keep", type=int, default=None,
                    help="max generations to retain; exceeding it REFUSES (never deletes)")
    ap.add_argument("--dry-run", action="store_true",
                    help="report what would happen without touching the filesystem")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())
    if not args.target:
        _die("--target is required")
    if args.keep is not None and args.keep < 1:
        _die(f"--keep must be a positive integer, got {args.keep}")
    parent = os.path.dirname(os.path.abspath(args.target)) or "."
    if not os.path.isdir(parent):
        _die(f"target's parent directory does not exist: {parent!r}")

    try:
        result = move_aside(args.target, keep=args.keep, dry_run=args.dry_run)
    except MoveAsideError as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        sys.exit(REFUSED)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(render(result))
    sys.exit(SAFE)


if __name__ == "__main__":
    main()

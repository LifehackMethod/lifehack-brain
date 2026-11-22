#!/usr/bin/env python3
"""gates.py — the I4 code gates for planning-weekly (spec I4; card.json's gates note).

The exact accepted answers, checked by code, never guessed by the model:
  - step gate (steps 1-7 move-on): move on = "lock" / "next" / "B";
    stay = "again" / "refine" / "A". Case-insensitive; surrounding whitespace ignored.
  - go gate (step 8.5): accepted = "go" or a step number 1-8 ("1".."8").
    Anything else (including "back") is refused: the caller asks again.

Exit codes: 0 = accepted (which gate and which way are printed); 1 = refused (ask again);
2 = usage error. Refusals always print a reason on stderr.

Selftest: --selftest runs one good, one edge and one padded case per gate plus refusals,
prints PASS/FAIL per case, exits 0 only if all pass.
"""
# allow-silence: build-ruled location — slice B of the planning-weekly build; the coordinator
# ruled this worktree skill folder as the home for these files, and the build task forbids
# own_list_add and any write outside the worktree. Not a personal tool; never moved to the personal code folder.
import sys


def step_gate(text):
    """-> ("move_on"|"stay"|None, the normalized word). None = refused."""
    w = (text or "").strip().lower()
    if w in ("lock", "next", "b"):
        return "move_on", w
    if w in ("again", "refine", "a"):
        return "stay", w
    return None, w


def go_gate(text):
    """-> ("go"|"back_to"|None, detail). None = refused."""
    w = (text or "").strip().lower()
    if w == "go":
        return "go", w
    if w in tuple("12345678"):
        return "back_to", int(w)
    return None, w


def _check(fn, text, want):
    got, _ = fn(text)
    ok = got == want
    return ok, "%s(%r) -> %r (want %r)" % (fn.__name__, text, got, want)


def selftest():
    cases = []
    # Good inputs.
    cases += [_check(step_gate, "lock", "move_on"), _check(step_gate, "B", "move_on"),
              _check(step_gate, "again", "stay"), _check(step_gate, "refine", "stay"),
              _check(go_gate, "go", "go"), _check(go_gate, "3", "back_to")]
    # Edge: empty and None.
    cases += [_check(step_gate, "", None), _check(step_gate, None, None),
              _check(go_gate, "", None), _check(go_gate, None, None)]
    # Padded / messy input that must still normalize.
    cases += [_check(step_gate, "  NEXT  ", "move_on"), _check(go_gate, "  Go ", "go"),
              _check(go_gate, "8", "back_to")]
    # Refusals: near-miss words and out-of-range numbers must NOT pass.
    cases += [_check(step_gate, "locks", None), _check(step_gate, "done", None),
              _check(go_gate, "back", None), _check(go_gate, "9", None),
              _check(go_gate, "0", None), _check(go_gate, "go now", None)]
    fails = [line for ok, line in cases if not ok]
    for ok, line in cases:
        print(("PASS  " if ok else "FAIL  ") + line)
    if fails:
        print("SELFTEST FAILED (%d/%d)" % (len(fails), len(cases)))
        return 1
    print("SELFTEST PASSED (%d cases)" % len(cases))
    return 0


def main(argv):
    if "--selftest" in argv:
        return selftest()
    if len(argv) != 3 or argv[0] != "check":
        print("usage: gates.py check step|go \"<the person's words>\"  |  gates.py --selftest", file=sys.stderr)
        return 2
    kind, text = argv[1], argv[2]
    if kind == "step":
        verdict, w = step_gate(text)
        if verdict == "move_on":
            print("MOVE_ON (%s)" % w)
            return 0
        if verdict == "stay":
            print("STAY (%s)" % w)
            return 0
        print("REFUSED: %r is not a step answer (move on: lock/next/B; stay: again/refine/A) — ask again" % text, file=sys.stderr)
        return 1
    if kind == "go":
        verdict, detail = go_gate(text)
        if verdict == "go":
            print("GO")
            return 0
        if verdict == "back_to":
            print("BACK_TO_STEP %d" % detail)
            return 0
        print("REFUSED: %r is not \"go\" or a step number 1-8 — ask again" % text, file=sys.stderr)
        return 1
    print("usage: gates.py check step|go \"...\"  |  gates.py --selftest", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

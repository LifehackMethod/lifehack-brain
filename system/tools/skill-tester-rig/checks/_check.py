#!/usr/bin/env python3
"""_check.py — the ONE content check behind checks/{ai,code,human}.sh (TR1.3). Pure code: no model, no clock.

usage (through the .sh wrappers, never directly):
    _check.py KIND RUN_DIR N [CANDIDATE]
        KIND       ai | code | human   (must match the card's kind for sN, else CANNOT-READ: miswired)
        RUN_DIR    the run folder (absolute; layout.py: <scratch>/actor-home/<run-id>/.claude/run/skill-tester/<run-id>)
        N          the step number
        CANDIDATE  optional path of the file to check. Default: RUN_DIR/step-N.json.
                   The runner passes its temp file here so it can check BEFORE it renames the file into
                   step-N.json (CONTRACT §1: step-N.json is written only after the check passes).
    Seed: env CANARY_SEED (the runner exports it), else $SKILL_TESTER_SCRATCH/seeds/<basename RUN_DIR>
    (CONTRACT §0). No seed, or a seed that is not a non-negative integer -> CANNOT-READ.

What it checks — CONTENT, never presence (matrix F-13):
    the candidate parses as ONE strict JSON object (whitespace-trimmed only; no fences, no prose, no
    duplicate keys, no NaN), has exactly the SPEC §2 keys, and step / token / value / facts (and, for
    human steps, answer) each EQUAL the record expected.py derives for (seed, N). Then the whole parsed
    record must equal the expected record (a belt behind the field compares). Human: answer must be on the
    menu, and "no" FAILS (a legitimate halt; the run stops there — SPEC §4).
    The expected record comes from canary/expected.py (imported; the formula is never re-implemented here).

Verdicts (shared/emit/verdicts.py, used in place):
    exit 0   first line "PASS sN <kind>"
    exit 1   first line "FAIL <cat>: sN <kind>: <one-line reason>", <cat> one of CATS (CONTRACT §3; run.sh
             copies it into `CHECK-FAIL sN <cat>`): empty parse keys step token value facts answer
    exit 4   first line "CANNOT-READ", reason indented on line 2 (missing/unreadable file, no/bad seed,
             miswired kind, bad arguments, or ANY internal exception — never a pass, never a fail).
    An empty or whitespace-only candidate is a FAIL (the step produced nothing), not CANNOT-READ: the file
    exists and was read; what it holds is wrong. (verdicts.read_text calls that case "empty"; we re-read
    to tell it apart from unreadable.)
"""
import json, os, pathlib, sys

sys.dont_write_bytecode = True
sys.stderr = sys.stdout          # one stream, so the wrapper sees the verdict as the first line

HERE = pathlib.Path(__file__).resolve().parent
RIG = HERE.parent
SHARED_EMIT = pathlib.Path(os.environ.get("LIFEHACK_V2", os.path.expanduser("~/lifehack-v2"))) / "shared" / "emit"   # <repo>/shared/emit (repo = rig/../../..)
KINDS = ("ai", "code", "human")


class CannotRead(Exception):
    pass


CATS = ("empty", "parse", "keys", "step", "token", "value", "facts", "answer")   # CONTRACT §3 CHECK-FAIL <cat>


class Fail(Exception):
    """A content failure, always with a CONTRACT §3 category: Fail(cat, reason)."""
    def __init__(self, cat, reason):
        if cat not in CATS:
            raise ValueError("unknown fail category %r" % cat)   # -> CANNOT-READ via main()'s catch-all
        super().__init__(reason)
        self.cat = cat


def _no_dupes(pairs):
    keys = [k for k, _ in pairs]
    if len(set(keys)) != len(keys):
        raise Fail("parse", "duplicate key in JSON object")
    return dict(pairs)


def _no_constants(name):
    raise Fail("parse", "non-standard JSON constant %s" % name)


def _seed(run_dir, verdicts):
    # CONTRACT §0 (2026-10-31): seed file and CANARY_SEED must AGREE when both exist; a mismatch is CANNOT-READ.
    s = os.environ.get("CANARY_SEED")
    env_seed = None
    if s is not None:
        if not s.strip().isdigit():
            raise CannotRead("CANARY_SEED is not a non-negative integer: %r" % s)
        env_seed = int(s.strip())
    scratch = os.environ.get("SKILL_TESTER_SCRATCH") or os.path.expanduser("~/lifehack-scratch/skill-tester-rig")
    p = os.path.join(scratch, "seeds", os.path.basename(os.path.normpath(run_dir)))
    file_seed = None
    if os.path.exists(p):
        text, err = verdicts.read_text(p, "seed file")
        if err:
            raise CannotRead(err)
        if not text.strip().isdigit():
            raise CannotRead("seed file is not a non-negative integer: %s" % p)
        file_seed = int(text.strip())
    if env_seed is not None and file_seed is not None and env_seed != file_seed:
        raise CannotRead("seed mismatch: %s says %d, CANARY_SEED says %d" % (p, file_seed, env_seed))
    if env_seed is not None:
        return env_seed
    if file_seed is not None:
        return file_seed
    raise CannotRead("CANARY_SEED not set and no seed file at %s" % p)


def _read_candidate(path, verdicts):
    text, err = verdicts.read_text(path, "step file")
    if text is not None:
        return text
    if os.path.isfile(path) and os.access(path, os.R_OK):
        try:
            with open(path, encoding="utf-8") as fh:
                raw = fh.read()
        except Exception:
            raise CannotRead(err)
        if not raw.strip():
            raise Fail("empty", "empty reply (the file is empty or whitespace only)")
    raise CannotRead(err)


def check(kind, run_dir, n, candidate, expected, verdicts):
    ks = expected.kinds()
    if n not in ks:
        raise CannotRead("s%d is not on the card" % n)
    if ks[n] != kind:
        raise CannotRead("miswired: the card says s%d is %s, this is the %s check" % (n, ks[n], kind))
    seed = _seed(run_dir, verdicts)
    # Earlier human steps must have been "yes" for the run to reach sN; the value chain ignores answers.
    answers = {k: "yes" for k, v in ks.items() if v == "human" and k <= n}
    recs = expected.expected_run(seed, answers)
    if len(recs) < n:
        raise CannotRead("expected.py produced %d records, need s%d" % (len(recs), n))
    want = recs[n - 1]

    text = _read_candidate(candidate, verdicts)
    try:
        got = json.loads(text.strip(), object_pairs_hook=_no_dupes, parse_constant=_no_constants)
    except Fail:
        raise
    except ValueError as e:
        raise Fail("parse", "not one strict JSON object (%s at char %d)" % (getattr(e, "msg", e), getattr(e, "pos", -1)))
    if not isinstance(got, dict):
        raise Fail("parse", "JSON is a %s, not an object" % type(got).__name__)

    missing = [k for k in want if k not in got]
    extra = sorted(k for k in got if k not in want)
    if "token" in missing:
        raise Fail("token", "token missing")
    if missing or extra:
        raise Fail("keys", "keys wrong (missing: %s; extra: %s)" % (",".join(missing) or "-", ",".join(extra) or "-"))

    if kind == "human":
        a = got["answer"]
        if a == "no":
            raise Fail("answer", "human answered no (a legitimate halt: the run stops at s%d)" % n)
        if not isinstance(a, str) or a not in expected.MENU:
            raise Fail("answer", "answer off-menu: %r (menu: %s)" % (a, "/".join(expected.MENU)))

    if type(got["step"]) is not int or got["step"] != n:
        raise Fail("step", "step wrong: %r (want %d)" % (got["step"], n))
    if not isinstance(got["token"], str) or got["token"] != want["token"]:
        raise Fail("token", "token wrong")
    if type(got["value"]) is not int:
        raise Fail("value", "value is not an integer: %r" % (got["value"],))
    if got["value"] != want["value"]:
        raise Fail("value", "value wrong: %d (want %d)" % (got["value"], want["value"]))
    f = got["facts"]
    if not isinstance(f, list) or not all(isinstance(x, str) for x in f):
        raise Fail("facts", "facts is not a list of strings")
    if f != want["facts"]:
        if len(f) < len(want["facts"]):
            raise Fail("facts", "facts dropped: %d of %d present" % (len(f), len(want["facts"])))
        if sorted(f) == sorted(want["facts"]):
            raise Fail("facts", "facts reordered")
        raise Fail("facts", "facts edited or extra")
    if kind == "human" and got["answer"] != want["answer"]:
        raise Fail("answer", "answer wrong: %r" % (got["answer"],))
    if got != want:                      # the belt: nothing the field compares missed
        raise Fail("keys", "record differs from the expected record")
    return "PASS s%d %s" % (n, kind)


def main(argv):
    def cannot(msg, verdicts=None):
        if verdicts is not None:
            verdicts.print_cannot_read(msg)
            return verdicts.CANNOT_READ
        print("CANNOT-READ\n  %s" % msg)
        return 4                         # only when verdicts.py itself could not be imported

    verdicts = None
    try:
        sys.path.insert(0, str(SHARED_EMIT))
        import verdicts                  # noqa: E402  (shared, used in place)
        sys.path.insert(0, str(RIG / "canary"))
        import expected                  # noqa: E402  (the one formula)
        if len(argv) not in (3, 4) or argv[0] not in KINDS:
            return cannot("usage: _check.py ai|code|human RUN_DIR N [CANDIDATE]", verdicts)
        kind, run_dir, n_s = argv[0], argv[1], argv[2]
        if not run_dir:
            return cannot("RUN_DIR is empty", verdicts)
        if not n_s.isdigit():
            return cannot("N is not a step number: %r" % n_s, verdicts)
        n = int(n_s)
        candidate = argv[3] if len(argv) == 4 else os.path.join(run_dir, "step-%d.json" % n)
        try:
            print(check(kind, run_dir, n, candidate, expected, verdicts))
            return 0
        except Fail as e:
            print("FAIL %s: s%d %s: %s" % (e.cat, n, kind, e))
            return 1
    except CannotRead as e:
        return cannot(str(e), verdicts)
    except BaseException as e:           # the check's own crash is a rig defect, never a pass or a fail
        return cannot("check crashed: %s: %s" % (e.__class__.__name__, e), verdicts)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

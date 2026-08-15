#!/usr/bin/env python3
"""recommendation_disposition.py — records a HUMAN's accept/reject decision against one
Efficiency recommendation, durably. This is the "recordable back" half of the review surface:
`health_line.py` shows a recommendation at session start; this is what a human runs to say yes
or no to it. Once a fingerprint has a disposition, `health_line.py` stops surfacing it — see
that module's `_recommendations_line()`.

⛔⛔ PROPOSE-ONLY, RULED, NOT NEGOTIABLE — same invariant `emit_recommendation.py` states for
itself, one step further down the pipe. Recording a disposition is a FACT ABOUT A HUMAN'S
JUDGMENT, nothing more. This module writes ONE row to a durable store and does NOTHING else:
it never reads the recommendation's `action` field for meaning, never opens/edits/runs
anything the recommendation describes, never re-enters Efficiency's reasoning path. Accepting a
recommendation here means exactly one thing: a human looked at it and said yes. The human
still does the work.

WHY THIS IS A SEPARATE STORE FROM RECOMMENDATIONS, NOT A FIELD REWRITTEN IN PLACE.
`emit_recommendation.py`'s store is append-only JSONL on the resolved brain root, shared by
every producer that writes there — rewriting a historical line in place to add a "disposition"
field would mean read-modify-write on a file another process can be actively appending to,
the exact race `emit_finding.py`/`emit_recommendation.py` both avoid by only ever appending.
A disposition is instead its own append-only fact, keyed by the fingerprint it disposes of;
`health_line.py` (and this module's `latest_dispositions()`) join the two stores by
fingerprint at READ time. Same shape Hospital already uses for STALE derivation
(`findings_deadman.py` never rewrites a finding row to say STALE — it appends a synthetic
row alongside at read time); this is that same idiom, applied to "has a human acted on this".

⛔ HUMAN INTENT NEVER LIVES ANYWHERE EPHEMERAL. An accept/reject IS human intent — it is
written straight to the resolved brain root (`state/recommendations/dispositions/`), never
anywhere machine-local-only, never anywhere a reboot or a temp-dir sweep can touch it.

★ THE RESIDENCY LAW — the machine token goes in the PATH (`dispositions.<machine>.jsonl`),
never only inside the payload, for the identical reason `emit_recommendation.py` and
`emit_finding.py` both state: a field inside a shared file does not stop the file itself
from forking across machines. `get_machine_token()` below is the ONE derivation used here too
— re-derived locally (see that function's own docstring for why), never re-invented a second
way.

WHY DECISION IS "accepted"/"rejected" (past tense) NOT "accept"/"reject" ON DISK. The CLI
accepts either verb form (`--decision accept` or `--decision accepted`) for a human typing at
a terminal, but the row written to disk always normalizes to the past-tense form — it is a
RECORD of a decision already made, not an instruction to carry one out (there is nothing
downstream to carry it out — see PROPOSE-ONLY above). Matches `emit_finding.py`'s status
vocabulary convention of storing a settled state, not a verb.

WHY --fingerprint ACCEPTS A PREFIX, NOT ONLY THE FULL 64-CHAR sha256. `health_line.py`'s
review-surface line is deliberately terse (a session start that becomes a wall of text will be
ignored) and shows only the first 8 characters of each fingerprint, matching the line's
existing visual grammar. A human copying that 8-char prefix must be able to use it directly
here rather than round-tripping through a second tool first. `_resolve_fingerprint()` below
matches the prefix against every fingerprint currently known to
`recommendations_reader.recommendations_report()` and REFUSES (loud, no write) on zero or
more-than-one match — an ambiguous prefix must never silently pick one recommendation's fate
for another's fingerprint.

Compatible with `/usr/bin/python3` (3.9) — no `X | None` union annotations, stdlib only.
"""
import argparse
import glob
import json
import os
import signal
import sys
import threading
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from recommendations_reader import recommendations_report  # noqa: E402

# ── MACHINE TOKEN — re-derived locally, NOT imported. ───────────────────────────────────────
# `machine_token.py` is part of the two-machine plane this product doesn't have (excluded — see
# that module's own DOES-NOT-MIGRATE banner in the donor repo) and is never imported, copied,
# or shelled out to from here. This product is one machine by design (see `shared/brain_root.py`),
# so the derivation collapses to a fixed constant. Same local pattern `emit_finding.py` /
# `emit_recommendation.py` already use — restated here (not imported from either) per this
# repo's own convention of copying a tiny private technique across a file boundary rather than
# reaching into a sibling's internals.
MACHINE = "local"


def get_machine_token():
    """Always `MACHINE`. Never raises — kept as a function (not a bare constant reference at
    each call site) so a future multi-install need has exactly one place to change."""
    return MACHINE


# ── WHERE DISPOSITIONS LIVE — resolved through the ONE brain-root resolver, never guessed. ──
# Dispositions live ONE directory below RECOMMENDATIONS_DIR on purpose — see
# recommendations_reader.py's module docstring "WHERE RECOMMENDATIONS LIVE" for why (its
# non-recursive glob must never see this file). No machine-local mirror exists here either —
# same posture as emit_recommendation.py: the resolved brain root IS the store, so a write
# failure raises rather than falling back silently.
_CODE_ROOT = os.path.dirname(os.path.dirname(_HERE))          # system/tools/../.. -> repo root
_SHARED = os.path.join(_CODE_ROOT, "shared")
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)
try:
    from brain_root import resolve_brain_root          # shared/brain_root.py
    _ROOT_SOURCE, DRIVE = resolve_brain_root()
except Exception:
    _ROOT_SOURCE, DRIVE = None, None

# None when no root is configured — same "a writer has nothing to write to" posture as
# emit_recommendation.py's RECOMMENDATIONS_DIR. record_disposition() below refuses outright
# rather than guess a location.
RECOMMENDATIONS_DIR = os.path.join(DRIVE, "state", "recommendations") if DRIVE else None
DISPOSITIONS_DIR = os.path.join(RECOMMENDATIONS_DIR, "dispositions") if RECOMMENDATIONS_DIR else None

VALID_DECISION = {"accepted", "rejected"}
_DECISION_ALIASES = {"accept": "accepted", "accepted": "accepted",
                      "reject": "rejected", "rejected": "rejected"}
WRITE_TIMEOUT_S = 15


def _iso_now():
    lt = time.localtime()
    off = time.strftime("%z", lt)
    off = (off[:3] + ":" + off[3:]) if off else "+00:00"
    return time.strftime("%Y-%m-%dT%H:%M:%S", lt) + off


class DispositionContractError(ValueError):
    """Raised at WRITE time (or resolve time) when a disposition call violates the contract
    — a bad decision verb, an empty/ambiguous/unknown fingerprint, or no notes root configured.
    Same posture as emit_recommendation.RecommendationContractError: scream at the caller,
    never go quietly missing downstream."""


class _Alarm:
    """Signal-based timeout so a wedged mount fails LOUD and fast instead of hanging
    the caller forever. Same technique as emit_recommendation.py's _Alarm — duplicated, not
    imported, because that is a leading-underscore private class in a sibling module (see this
    repo's established convention: copy the technique, not the text, across a file boundary
    rather than reach into another module's internals)."""

    def __init__(self, seconds):
        self.seconds = seconds
        self._have_alarm = (hasattr(signal, "SIGALRM")
                            and threading.current_thread() is threading.main_thread())
        self._old = None

    def _handler(self, signum, frame):
        raise TimeoutError(
            f"recommendation_disposition: write exceeded {self.seconds}s — the brain root's "
            "mount likely wedged")

    def __enter__(self):
        if self._have_alarm:
            self._old = signal.signal(signal.SIGALRM, self._handler)
            signal.alarm(self.seconds)
        return self

    def __exit__(self, *exc):
        if self._have_alarm:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, self._old)
        return False


def _read_jsonl(path):
    """Same (rows, ok, bad_lines) contract as recommendations_reader._read_jsonl — see that
    module's copy for the full rationale. Reproduced, not imported: private helper."""
    rows = []
    bad_lines = 0
    try:
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    bad_lines += 1
        return rows, True, bad_lines
    except FileNotFoundError:
        return rows, True, 0
    except Exception:
        return rows, False, 0


def dispositions_report(dispositions_dir=None):
    """Union read across every `dispositions.<machine>.jsonl` shard — same
    shards_expected/read/missing/bad_lines/degraded contract as recommendations_report() and
    findings_report(), applied to the disposition store. Never raises."""
    dispositions_dir = dispositions_dir or DISPOSITIONS_DIR
    report = {
        "rows": [], "shards_expected": 0, "shards_read": [], "shards_missing": [],
        "bad_lines": {}, "degraded": False, "degraded_reason": "", "drive_available": True,
    }
    if dispositions_dir is None:
        # No notes root configured at all — same "nothing to read yet, not a crash" posture
        # recommendations_report() takes when DRIVE is None.
        report["drive_available"] = False
        report["degraded"] = True
        report["degraded_reason"] = (
            "no notes root configured — brain_root.resolve_brain_root() returned NOT-SET "
            "(fix: python3 shared/brain_root.py --set <folder>)")
        return report

    paths = []
    try:
        if os.path.isdir(dispositions_dir):
            paths = sorted(glob.glob(os.path.join(dispositions_dir, "dispositions.*.jsonl")))
        elif DRIVE and not os.path.isdir(DRIVE):
            raise OSError(f"notes root not reachable: {DRIVE}")
        # else: the root is up, dispositions/ just doesn't exist yet — 0 shards, not an error
        # (legitimate "nobody has accepted/rejected anything yet" first-run state).
    except Exception as e:
        report["drive_available"] = False
        report["degraded"] = True
        report["degraded_reason"] = (
            f"notes root unavailable ({e}) — disposition state UNKNOWN this run (a "
            "recommendation may have already been accepted/rejected but this reader cannot "
            "see it)")
        return report

    report["shards_expected"] = len(paths)
    all_rows = []
    for p in paths:
        name = os.path.basename(p)
        rows, ok, bad = _read_jsonl(p)
        if not ok:
            report["shards_missing"].append(name)
            continue
        report["shards_read"].append(name)
        all_rows.extend(rows)
        if bad:
            report["bad_lines"][name] = bad

    reasons = []
    if report["shards_missing"]:
        reasons.append(
            f"{len(report['shards_missing'])} shard(s) unreadable: " + ", ".join(report["shards_missing"]))
    if report["bad_lines"]:
        total_bad = sum(report["bad_lines"].values())
        reasons.append(
            f"{total_bad} malformed line(s) across {len(report['bad_lines'])} shard(s): "
            + ", ".join(f"{k}={v}" for k, v in sorted(report["bad_lines"].items())))
    if reasons:
        report["degraded"] = True
        report["degraded_reason"] = "; ".join(reasons)

    report["rows"] = all_rows
    return report


def latest_dispositions(dispositions_dir=None):
    """{fingerprint: {decision, ts, machine, note}} — the LATEST disposition per fingerprint
    across every machine's shard (latest `ts` wins, so a later re-decision on either machine
    overrides an earlier one — same "latest row per fingerprint is current truth" idiom
    `health_line._findings_line()` already uses for findings).

    Returns (mapping, report) — `report` carries dispositions_report()'s own
    degraded/degraded_reason so a caller can tell "nothing has been decided yet" apart from
    "dispositions could not be read" (an empty mapping alone cannot distinguish those two —
    a refusal/failure must never look identical to a clean empty result)."""
    report = dispositions_report(dispositions_dir)
    latest = {}
    for r in report.get("rows", []):
        fp = r.get("fingerprint")
        if not fp:
            continue
        ts = r.get("ts") or ""
        if fp not in latest or ts >= (latest[fp].get("ts") or ""):
            latest[fp] = r
    return latest, report


def _match_prefix(user_input, known_fingerprints):
    """Pure matching logic, factored out of `_resolve_fingerprint()` so it can be
    unit-tested deterministically (see the self-test's ambiguous/no-match cases) without
    depending on two real sha256 fingerprints happening to share a prefix, which is a
    1-in-16-per-character coin flip and would make that coverage flaky on unlucky input.
    `known_fingerprints` is any iterable of fingerprint strings. Raises
    DispositionContractError — never silently guesses — on zero or multiple matches."""
    known = set(known_fingerprints)
    if user_input in known:
        return user_input
    matches = sorted(fp for fp in known if fp.startswith(user_input))
    if len(matches) == 1:
        return matches[0]
    if len(matches) == 0:
        raise DispositionContractError(
            f"fingerprint {user_input!r} matches no known recommendation "
            f"(saw {len(known)} distinct fingerprint(s))")
    raise DispositionContractError(
        f"fingerprint {user_input!r} matches {len(matches)} known recommendations — "
        "ambiguous, use more characters")


def _resolve_fingerprint(user_input, recommendations_dir=None):
    """Resolve a full fingerprint OR an unambiguous prefix of one against every fingerprint
    currently known to recommendations_report() (any altitude/machine). See module docstring
    "WHY --fingerprint ACCEPTS A PREFIX" for why this exists. Raises
    DispositionContractError — never silently guesses — on zero or multiple matches."""
    if not user_input or not isinstance(user_input, str):
        raise DispositionContractError("fingerprint must be a non-empty str")

    # recommendations_report() has no dir override today (it reads RECOMMENDATIONS_DIR off
    # its own module-level resolved-brain-root constant) — tests point it at a scratch
    # dir by rebinding that module global directly, same as every other store in this
    # pipeline, so no extra plumbing is added here for a parameter that store doesn't expose.
    report = recommendations_report()
    known = {r.get("fingerprint") for r in report.get("rows", []) if r.get("fingerprint")}
    return _match_prefix(user_input, known)


def record_disposition(*, fingerprint, decision, note="", ts=None, resolve=True,
                         write_timeout_s=WRITE_TIMEOUT_S, dispositions_dir=None):
    """Durably record a human's accept/reject decision against a recommendation's
    fingerprint. See module docstring — PROPOSE-ONLY: this writes ONE row to a durable store
    and does nothing else.

    `resolve=True` (default) runs `fingerprint` through `_resolve_fingerprint()` first so a
    caller can pass a short prefix (matching what `health_line.py` shows). Pass
    `resolve=False` to write the exact fingerprint given, no lookup — used by this module's
    own self-test so it does not depend on a live recommendations store existing at the
    scratch dir it writes dispositions into.

    `dispositions_dir` defaults to `DISPOSITIONS_DIR` (the resolved brain root's
    `state/recommendations/dispositions/`). If NEITHER an override nor a resolved brain root
    is available, this REFUSES rather than guess a location — same posture as
    `emit_recommendation()`'s no-root refusal.
    """
    dispositions_dir = dispositions_dir or DISPOSITIONS_DIR
    if dispositions_dir is None:
        raise DispositionContractError(
            "record_disposition(): no notes root is configured — brain_root.resolve_brain_root() "
            "returned NOT-SET, and no dispositions_dir= override was given. Refusing to write "
            "rather than guess a location. Fix: `python3 shared/brain_root.py --set <folder>` "
            "(add --create for a new folder), or pass dispositions_dir= explicitly (tests do this).")

    decision = _DECISION_ALIASES.get(decision, decision)

    errs = []
    if not fingerprint or not isinstance(fingerprint, str):
        errs.append("fingerprint must be a non-empty str")
    if decision not in VALID_DECISION:
        errs.append(f"decision must resolve to one of {sorted(VALID_DECISION)} "
                    f"(accept/accepted/reject/rejected), got {decision!r}")
    if errs:
        raise DispositionContractError("record_disposition(): " + " ; ".join(errs))

    resolved_fp = _resolve_fingerprint(fingerprint) if resolve else fingerprint

    machine = get_machine_token()
    row = {
        "fingerprint": resolved_fp,
        "decision": decision,
        "note": str(note),
        "ts": ts or _iso_now(),
        "machine": machine,
    }
    line = json.dumps(row, sort_keys=True) + "\n"
    out_path = os.path.join(dispositions_dir, f"dispositions.{machine}.jsonl")

    # Same no-swallow posture as emit_recommendation.py's write: a mount failure here
    # propagates as a normal OSError rather than being caught. The alarm guards only the ONE
    # failure mode a raised OSError can't: a hang instead of an error.
    with _Alarm(write_timeout_s):
        os.makedirs(dispositions_dir, exist_ok=True)
        with open(out_path, "a") as f:
            f.write(line)
    return row


# ── CLI ─────────────────────────────────────────────────────────────────────────────────
def _build_argparser():
    ap = argparse.ArgumentParser(
        prog="recommendation_disposition.py",
        description="Record a human's accept/reject decision against one Efficiency "
                     "recommendation, durably. PROPOSE-ONLY: writes a disposition record "
                     "and nothing else — never applies whatever the recommendation "
                     "describes.",
    )
    ap.add_argument("--selftest", action="store_true",
                     help="run the built-in self-test (writes to a temp dir) and exit; ignores all other flags")
    ap.add_argument("--fingerprint",
                     help="the recommendation's fingerprint, full or an unambiguous prefix "
                          "(the short form health_line.py shows)")
    ap.add_argument("--decision", choices=sorted(_DECISION_ALIASES.keys()),
                     help="accept / accepted / reject / rejected")
    ap.add_argument("--note", default="", help="optional free-text reason, for the human record only")
    ap.add_argument("--ts", default=None)
    ap.add_argument("--dispositions-dir", default=None,
                     help="override the dispositions store dir (tests only — prefer setting the "
                          "brain root via shared/brain_root.py)")
    return ap


def _selftest():
    import tempfile
    from emit_recommendation import emit_recommendation

    rec_dir = tempfile.mkdtemp()
    disp_dir = tempfile.mkdtemp()

    # Point recommendations_report() (used by _resolve_fingerprint) at the scratch dir by
    # rebinding the module global directly here — recommendations_reader already computed its
    # module-level RECOMMENDATIONS_DIR at import time, exactly the "an isolated test must rebind
    # module globals, not just an env var" pattern every store in this pipeline shares.
    import recommendations_reader as _rr
    old_rr_dir = _rr.RECOMMENDATIONS_DIR
    _rr.RECOMMENDATIONS_DIR = rec_dir
    try:
        row_a = emit_recommendation(
            producer="selftest", altitude="INSTANCE", action="do the small thing",
            evidence=["fp-x"], labels={"job": "selftest-disposition", "n": "a"},
            recommendations_dir=rec_dir)
        row_b = emit_recommendation(
            producer="selftest", altitude="INSTANCE", action="do a different small thing",
            evidence=["fp-y"], labels={"job": "selftest-disposition", "n": "b"},
            recommendations_dir=rec_dir)
        fp_a, fp_b = row_a["fingerprint"], row_b["fingerprint"]
        assert fp_a != fp_b, "two different label sets must not collide"

        # 1) full fingerprint resolves and writes.
        written = record_disposition(fingerprint=fp_a, decision="accept",
                                      note="selftest full-fp accept", dispositions_dir=disp_dir)
        assert written["decision"] == "accepted", written
        assert written["fingerprint"] == fp_a
        print("full-fingerprint accept recorded:", {k: written[k] for k in ("fingerprint", "decision", "machine")})

        # 2) unambiguous 8-char prefix resolves to the SAME fingerprint and writes a SECOND
        # disposition row for a DIFFERENT recommendation (fp_b) — proves the prefix path.
        prefix_b = fp_b[:8]
        written2 = record_disposition(fingerprint=prefix_b, decision="rejected",
                                       dispositions_dir=disp_dir)
        assert written2["fingerprint"] == fp_b, (written2, fp_b)
        assert written2["decision"] == "rejected"
        print("prefix accept/reject resolved correctly:", prefix_b, "->", written2["fingerprint"][:8])

        # 3) an unknown fingerprint is REFUSED, not silently written.
        try:
            record_disposition(fingerprint="doesnotexist00", decision="accept", dispositions_dir=disp_dir)
            print("FAILED to reject unknown fingerprint"); sys.exit(1)
        except DispositionContractError as e:
            print("rejected unknown fingerprint:", str(e)[:90])

        # 4) an empty fingerprint is REFUSED by the non-empty-str check, before resolution
        # ever runs.
        try:
            record_disposition(fingerprint="", decision="accept", dispositions_dir=disp_dir)
            print("FAILED to reject empty fingerprint"); sys.exit(1)
        except DispositionContractError as e:
            print("rejected empty fingerprint:", str(e)[:90])

        # 4b) ambiguous-prefix rejection — tested against `_match_prefix()` DIRECTLY with a
        # hand-built known set, not against fp_a/fp_b's real sha256 values. Two real
        # fingerprints sharing a prefix is a 1-in-16-per-character coin flip; asserting on
        # that would make this exact case flaky depending on which two hashes landed. The
        # pure function is what `_resolve_fingerprint()` actually calls (see its own body),
        # so this is real coverage of the real ambiguity branch, just decoupled from luck.
        fake_known = {"aaaa1111", "aaaa2222", "bbbb3333"}
        try:
            _match_prefix("aaaa", fake_known)
            print("FAILED to reject ambiguous prefix 'aaaa'"); sys.exit(1)
        except DispositionContractError as e:
            print("rejected ambiguous prefix 'aaaa' (2 matches):", str(e)[:90])
        assert _match_prefix("bbbb", fake_known) == "bbbb3333"
        assert _match_prefix("aaaa1111", fake_known) == "aaaa1111"
        print("_match_prefix() resolves an unambiguous prefix and an exact full match correctly")

        # 5) a bad decision verb is REFUSED.
        try:
            record_disposition(fingerprint=fp_a, decision="maybe", dispositions_dir=disp_dir)
            print("FAILED to reject bad decision verb"); sys.exit(1)
        except DispositionContractError as e:
            print("rejected bad decision verb:", str(e)[:90])

        # 6) latest_dispositions() sees both, keyed correctly, not degraded.
        mapping, report = latest_dispositions(dispositions_dir=disp_dir)
        assert not report["degraded"], report
        assert mapping.get(fp_a, {}).get("decision") == "accepted", mapping
        assert mapping.get(fp_b, {}).get("decision") == "rejected", mapping
        # collection non-empty BEFORE asserting over it: all() over an empty collection is
        # vacuously True, so check size first rather than let a vacuous pass masquerade as
        # real coverage.
        assert len(mapping) == 2, f"expected exactly 2 dispositions, got {len(mapping)}: {mapping}"
        print("latest_dispositions() sees both, correctly keyed:",
              {fp[:8]: v["decision"] for fp, v in mapping.items()})

        # 7) no-root refusal: with no dispositions_dir= override and no brain root resolved,
        # record_disposition() must refuse cleanly rather than write anywhere or crash.
        global DISPOSITIONS_DIR
        real_disp_dir = DISPOSITIONS_DIR
        DISPOSITIONS_DIR = None
        try:
            try:
                record_disposition(fingerprint=fp_a, decision="accept", resolve=False)
                print("FAILED to refuse with no root configured"); sys.exit(1)
            except DispositionContractError as e:
                assert "no notes root" in str(e) or "dispositions_dir" in str(e), str(e)
                print(f"refused cleanly with no root configured: {str(e)[:90]}")
        finally:
            DISPOSITIONS_DIR = real_disp_dir

        print("recommendation_disposition.py self-test PASSED")
    finally:
        _rr.RECOMMENDATIONS_DIR = old_rr_dir


def _main(argv):
    ap = _build_argparser()
    if not argv:
        ap.print_usage(sys.stderr)
        print("recommendation_disposition.py: error: no arguments given — pass --selftest, "
              "or --fingerprint/--decision to record a disposition.", file=sys.stderr)
        return 2

    args = ap.parse_args(argv)

    if args.selftest:
        _selftest()
        return 0

    missing = [flag for flag, val in (("--fingerprint", args.fingerprint),
                                       ("--decision", args.decision)) if val is None]
    if missing:
        print(f"recommendation_disposition.py: error: missing required flag(s): {', '.join(missing)}",
              file=sys.stderr)
        return 2

    try:
        row = record_disposition(
            fingerprint=args.fingerprint,
            decision=args.decision,
            note=args.note,
            ts=args.ts,
            dispositions_dir=args.dispositions_dir,
        )
        print(f"recorded: fingerprint={row['fingerprint'][:16]}... decision={row['decision']} "
              f"machine={row['machine']} ts={row['ts']}")
    except DispositionContractError as e:
        print(f"recommendation_disposition.py: DispositionContractError: {e}", file=sys.stderr)
        return 1
    except (OSError, TimeoutError) as e:
        print(f"recommendation_disposition.py: error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))

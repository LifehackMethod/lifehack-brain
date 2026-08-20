#!/usr/bin/env python3
"""emit_recommendation.py — the ONE validating writer every Efficiency reasoner goes through.

Sibling of `system/tools/emit_finding.py` (read that file first — this matches its posture:
build the envelope, validate at write time, fail loud, atomic-ish append, a CLI so shell and
Python reasoners share ONE validator by reference, not by copy-paste). Where `emit_finding.py`
is Hospital's ONE writer, this is Efficiency's.

WHAT EFFICIENCY IS, AND WHY IT IS NOT HOSPITAL WEARING A DIFFERENT HAT. Hospital detects and
ranks problems the system has with itself: detectors -> emit_finding -> a comparable finding
-> a reader -> a line at session start. Efficiency is its deliberate mirror, one step further
down the pipe: findings -> a reasoner -> emit_recommendation -> a review surface -> A HUMAN
ACTS. The design goal for this subsystem is that the system should get sharper the more it is
used, not duller — a pile of findings nobody ever turns into a move does not sharpen anything;
something has to look at the pile and propose one. That is this module's whole job, and ONLY
that job.

RULED, NOT A DESIGN CHOICE: EFFICIENCY SUGGESTS, IT NEVER APPLIES. There is no auto-apply path
at any altitude, here or anywhere downstream of this file. This module writes a proposed
recommendation to a store a human reads later; it does not retry a job, does not edit a file,
does not re-run anything. If a future change to this file ever grows a code path that applies
a fix, that change has left this module's scope.

WHY A RECOMMENDATION GETS ITS OWN VALIDATED STORE INSTEAD OF LIVING AS PROSE IN A CHAT WINDOW.
Prose scrolls away and is unfalsifiable — nobody can count it, age it, or check it against what
actually happened. A stored recommendation can be counted, aged, marked accepted-or-rejected by
the review surface, and — critically, because this subsystem's whole purpose is making the
blade sharper — checked later against whether it turned out to be right. A subsystem that
cannot be graded on its own past suggestions cannot learn anything about itself; it just gets
duller output at higher volume. So a recommendation is a validated record with a stable
identity (the fingerprint below), same as a finding, for the same reason.

WHY `fingerprint` HAS NO PARAMETER, NOT EVEN A DEFAULTED ONE. Identical reasoning to
`emit_finding.py`, borrowed from the same place (Prometheus Alertmanager): identity is
mechanical — a hash of the label set — never hand-authored, because a hand-authored id is a
second place identity can drift from the data it describes. `emit_recommendation()`'s
signature has no `id=` and no `fingerprint=` kwarg at all; passing either is a `TypeError`
raised by Python's own argument binding, before a single line of this module's code runs. The
fingerprint is `sha256` of the label set, canonicalized by sorting `(str(key), str(value))`
pairs — the same technique, copied line-for-line in intent from `emit_finding._fingerprint`
(not imported: it is a five-line private helper, and importing another module's underscored
name would just be a second, more fragile way of stating the same tiny function; the actual
shared contract that matters — ONE derivation, never two — is honoured by copying the exact
technique verbatim rather than inventing a second one).

WHY `machine` IS DERIVED, NEVER PASSED, AND WHY IT IS A LOCAL CONSTANT HERE. Same fix as
`emit_finding.py`: two scripts on one physical machine once called that machine two different
things, forking one status tile into two — the fix was routing every consumer through ONE
shared derivation instead of each reinventing it. This product runs on ONE machine by design
(see `shared/brain_root.py`'s residency rule), so the derivation collapses to a fixed local
constant rather than a call into a two-machine token script — but the CONTRACT that fix
protected is preserved exactly: no `machine=` parameter exists on `emit_recommendation()`, full
stop. The value always comes from `get_machine_token()` below, never from a caller. NOT
imported from `emit_finding.py`: this repo's own convention (see `_Alarm`/`_fingerprint` below)
is to copy a tiny private technique across a file boundary rather than reach into a sibling
module's underscored internals, so the same three-line derivation is restated here rather than
imported.

*** WHY `evidence` HAS NO DEFAULT — THIS FILE'S OWN CENTRAL RULE, THE ANALOGUE OF
`emit_finding`'s `scanned_n`. *** `evidence` is a required keyword with NO default: a list of
the finding fingerprints that caused this recommendation. Omitting it is a `TypeError` from
Python itself, before this module's code runs, exactly like omitting `scanned_n` on a finding.
A caller that passes an empty list, or a list of empty/non-string entries, is REFUSED outright
— `RecommendationContractError`, no record written under the caller's chosen identity. A
recommendation that cannot point at the findings that caused it is an opinion wearing an
authority it did not earn, so it is structurally unable to be written under a real identity.

*** WHY THE REFUSAL MUST STILL LEAVE A RECORD. *** The single most important design lesson
Hospital already paid for: A REFUSAL IS NOT A RECORD. `emit_finding.py` refuses a
zero-scan-OK call, but it ALSO writes a canary finding first (`_write_zero_scan_canary`) —
because a bare refusal means the caller can catch-and-swallow the exception and the condition
that caused it leaves no trace anywhere the board can see. This module does the exact
equivalent for a no-evidence call: `_write_no_evidence_canary` writes a canary recommendation,
attributed to the same producer/altitude, BEFORE the `RecommendationContractError` is raised.
Like its Hospital counterpart, it deliberately does NOT call `emit_recommendation()` — it
builds its own envelope by hand, the same few lines `emit_recommendation()` itself uses,
duplicated on purpose — so there is no path back into the evidence check it exists to make
visible, no matter what is passed. It is a dead-end, not a loop. It is gated on the OTHER
required fields (`producer`, `altitude`, `labels`) being independently valid, for the same
reason `emit_finding`'s canary gate checks `producer_valid`/`labels_valid`: a call that is ALSO
malformed in some unrelated way (a garbage altitude, an empty label set) has nowhere sane to
be filed, so it is refused with no canary rather than attempted through a broken path.

WHERE RECOMMENDATIONS LAND, AND WHY THE SHARD KEY IS ALTITUDE, NOT PRODUCER. Findings shard by
`<producer>.<machine>.jsonl` because Hospital's read side asks "what is producer X reporting"
— one detector, one comparable stream. Efficiency's review surface asks a different question:
"how big a swing is this asking a human to make" — an INSTANCE fix is a five-minute decision, a
SUBSYSTEM fix is a project, an ORGANISM verdict is a request to re-examine a whole model, and a
DECISION verdict is not even a fault. Those four things belong on different triage piles
regardless of which reasoner produced them, so
`<brain>/state/recommendations/<altitude>.<machine>.jsonl` shards on the axis a human actually
reviews by, where `<brain>` is resolved through `shared/brain_root.py` — never a hardcoded
folder belonging to one person. The machine token still goes in the PATH, not only the payload,
for the same reason `emit_finding.py` does: a field inside a shared file does not stop the file
itself from forking across machines — one writer per path is what holds.

WHAT HAPPENS WITH NO BRAIN ROOT CONFIGURED. Same posture as `emit_finding.py`: a WRITE with no
configured destination has no honest place to land — guessing one is exactly the custody error
the `brain_root` resolver exists to prevent. So `emit_recommendation()` REFUSES outright —
raises `RecommendationContractError`, writes nothing, creates no directory — when
`resolve_brain_root()` returns NOT-SET and no `recommendations_dir=` override was passed. Tests
always pass `recommendations_dir=` explicitly and never hit this path.

WHY A WRITE FAILURE RAISES HERE. Same posture as `emit_finding.py`: this module has no local
copy — the resolved brain root IS the store. A silent failure here is unrecoverable data loss,
so any `OSError` during the write is left to propagate, never caught-and-swallowed. A
signal-based timeout guards the one failure mode a raised `OSError` can't cover — a mount that
hangs instead of erroring — so a bad filesystem day fails loud and FAST, never silently and
never by hanging the caller forever.

Compatible with `/usr/bin/python3` (3.9) — no `X | None` union annotations, stdlib only.
"""
import argparse
import hashlib
import json
import os
import signal
import sys
import threading
import time

# ── MACHINE TOKEN — re-derived locally, NOT imported. ───────────────────────────────────────
# `machine_token.py` is part of the two-machine plane this product doesn't have (excluded — see
# that module's own DOES-NOT-MIGRATE banner in the donor repo) and is never imported, copied,
# or shelled out to from here. This product is one machine by design (see `shared/brain_root.py`),
# so the derivation collapses to a fixed constant. Same local pattern `emit_finding.py` already
# uses — restated here (not imported from it) per this repo's own convention of copying a tiny
# private technique across a file boundary rather than reaching into a sibling's internals.
MACHINE = "local"


def get_machine_token():
    """Always `MACHINE`. Never raises — kept as a function (not a bare constant reference at
    each call site) so a future multi-install need has exactly one place to change."""
    return MACHINE


# ── the altitude vocabulary. Transcribed, not imported: `fault_proposer.py` (the module this
# vocabulary is drawn from) has not landed in this repo as of this port, and even once it does,
# importing it back here would create a real circular import — `fault_proposer.py` imports THIS
# module to emit its own proposals as recommendations. So the four values are restated here by
# hand; if a fifth altitude is ever added on either side, both copies must be updated by hand,
# there is no import to keep them in sync automatically. ──
VALID_ALTITUDE = {"INSTANCE", "SUBSYSTEM", "ORGANISM", "DECISION"}

# ── WHERE RECOMMENDATIONS LAND — resolved through the ONE brain-root resolver, never guessed. ──
# The donor hardcoded a personal cloud-drive path here. This product asks for a data root ONCE
# and remembers it (`shared/brain_root.py`); every path to it goes through that one resolver.
_HERE = os.path.dirname(os.path.abspath(__file__))
CODE_ROOT = os.path.dirname(os.path.dirname(_HERE))          # system/tools/../.. -> repo root
_SHARED = os.path.join(CODE_ROOT, "shared")
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)
try:
    from brain_root import resolve_brain_root          # shared/brain_root.py
    _ROOT_SOURCE, _ROOT = resolve_brain_root()
except Exception:
    _ROOT_SOURCE, _ROOT = None, None

# None when no root is configured — see `emit_recommendation()`'s refusal below. Unlike a
# reader, a WRITER has no honest fallback location: guessing one is the exact custody error
# `brain_root` exists to prevent, so this module simply has nothing to write to until a root is
# set.
RECOMMENDATIONS_DIR = os.path.join(_ROOT, "state", "recommendations") if _ROOT else None

# Reserved envelope keys — a caller's `payload` dict may never contain any of these. Same
# collision guard as emit_finding.ENVELOPE_KEYS ("never let a payload field silently shadow an
# envelope field"), extended to block a payload-smuggled "id"/"fingerprint" the same way — the
# belt to the TypeError's suspenders (see module docstring: no such kwarg exists on
# emit_recommendation() itself, so this only matters for someone trying to sneak it in via
# payload=).
ENVELOPE_KEYS = ("producer", "machine", "schema_version", "ts", "altitude", "action",
                  "summary", "rc", "evidence", "labels", "fingerprint", "id")

WRITE_TIMEOUT_S = 15   # signal-based hang guard on the write; see module docstring.


def _iso_now():
    lt = time.localtime()
    off = time.strftime("%z", lt)
    off = (off[:3] + ":" + off[3:]) if off else "+00:00"
    return time.strftime("%Y-%m-%dT%H:%M:%S", lt) + off


class RecommendationContractError(ValueError):
    """Raised at WRITE time when a recommendation violates the envelope, evidence, or label
    contract — OR when there is nowhere to write it at all (no brain root configured, no
    override given). Same posture as emit_finding.FindingContractError — a malformed or
    homeless recommendation must scream at the emitter, never go quietly missing downstream."""


class _Alarm:
    """Signal-based timeout so a wedged mount fails LOUD and fast instead of hanging
    the caller forever. Copied verbatim (technique, not text) from emit_finding.py's _Alarm —
    same guard, same reasoning, no second implementation to drift from it."""

    def __init__(self, seconds):
        self.seconds = seconds
        # ⚠ SIGALRM IS MAIN-THREAD-ONLY, and the platform check alone is NOT enough.
        # `signal.signal()` raises `ValueError: signal only works in main thread of the main
        # interpreter` from ANY other thread — so a `hasattr(signal, "SIGALRM")`-only guard
        # silently converts this HANG PROTECTION into a HARD CRASH for every threaded caller.
        # emit_finding.py hit this live; the same guard is required here for the same reason —
        # off the main thread we skip the alarm and accept the (much rarer) hang risk, because
        # a reasoner that cannot record a recommendation AT ALL is strictly worse than one that
        # might block. The OSError path (the common flaky-mount failure) still propagates
        # normally off-thread; only the wedged-mount hang guard is unavailable.
        self._have_alarm = (hasattr(signal, "SIGALRM")
                            and threading.current_thread() is threading.main_thread())
        self._old = None

    def _handler(self, signum, frame):
        raise TimeoutError(
            f"emit_recommendation: write exceeded {self.seconds}s — the brain root's mount "
            "likely wedged (not a normal error, which returns immediately; this is a hang)")

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


def _fingerprint(labels):
    """sha256 of the sorted label set. Order-independent: the same {k: v} pairs, offered in
    any insertion order, hash identically. Values are coerced to str for the canonical form.
    Same technique as emit_finding._fingerprint — see module docstring for why this is a
    verbatim-technique copy, not a cross-module import of a private helper."""
    items = sorted((str(k), str(v)) for k, v in labels.items())
    canonical = json.dumps(items, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _write_no_evidence_canary(*, producer, altitude, labels, action, summary,
                                recommendations_dir, write_timeout_s):
    """INTERNAL ONLY — this module's analogue of emit_finding._write_zero_scan_canary.
    Writes the canary recommendation that makes a refused no-evidence call VISIBLE on the
    review surface, not just loud to the immediate caller.

    ⚠ NOT part of the public contract. Leading underscore, no CLI flag reaches it, it is called
    from exactly ONE call site (inside emit_recommendation()'s own validation block, with
    evidence=[] baked in below — never taken from caller input) and it is never exported or
    documented as something a reasoner calls directly. A reasoner that wants to record a real
    recommendation always goes through emit_recommendation().

    ⚠ WHY THIS CANNOT RECURSE: this function does NOT call emit_recommendation() — it builds
    and writes its own envelope by hand, the same few lines emit_recommendation() itself uses,
    duplicated here on purpose. It never re-enters the evidence check at all, so there is no
    path back into itself no matter what is passed. It is a dead-end, not a loop.

    The canary is attributed to the SAME producer and files into the SAME altitude shard the
    real recommendation would have used (so it is reviewed alongside recommendations of that
    altitude, not off in a separate store) with labels carrying kind="no-evidence" so it is
    unmistakable in a label-filtered view, and evidence=[] recorded literally — the empty list
    IS the fact being reported, not a violation to hide.
    """
    machine = get_machine_token()
    canary_labels = dict(labels)
    canary_labels["kind"] = "no-evidence"
    fingerprint = _fingerprint(canary_labels)

    env = {
        "producer": producer,
        "machine": machine,
        "schema_version": 1,
        "ts": _iso_now(),
        "altitude": altitude,
        "action": "NO ACTION — REFUSED.",
        "summary": (f"CANARY: producer {producer!r} called emit_recommendation() with no "
                    f"citable evidence — a recommendation with no evidence is an opinion "
                    f"wearing a machine's authority it did not earn. The call was REFUSED "
                    f"(RecommendationContractError) so no unfounded recommendation was "
                    f"written; this canary is the only record that the refusal happened. "
                    f"Original action offered: {action!r}. Original summary offered: {summary!r}"),
        "rc": 1,
        "evidence": [],
        "labels": canary_labels,
        "fingerprint": fingerprint,
    }
    line = json.dumps(env, sort_keys=True) + "\n"
    out_path = os.path.join(recommendations_dir, f"{altitude}.{machine}.jsonl")

    # Same no-swallow posture as the main write below: a canary that silently fails to land is
    # exactly the silence this task exists to abolish, so a write failure here propagates too.
    with _Alarm(write_timeout_s):
        os.makedirs(recommendations_dir, exist_ok=True)
        with open(out_path, "a") as f:
            f.write(line)
    return env


def emit_recommendation(*, producer, altitude, action, evidence, labels, summary="",
                          payload=None, rc=0, schema_version=1, ts=None,
                          write_timeout_s=WRITE_TIMEOUT_S, recommendations_dir=None):
    """Validate + write ONE recommendation as an appended JSONL line.

    Envelope fields (producer, machine, schema_version, ts, altitude, action, summary, rc,
    evidence, labels, fingerprint) are OWNED by this function — a caller passes only `payload`
    for recommendation-specific extras. There is deliberately no `machine=`, no `id=`, and no
    `fingerprint=` parameter — see the module docstring for why each of those would
    reintroduce a bug this codebase already paid for once.

    `evidence` has no default: omit it and Python itself raises TypeError before this
    function's body runs at all. Pass it, but pass an empty list (or a list containing an
    empty/non-string entry), and the call is REFUSED — RecommendationContractError — after
    first writing a canary record so the refusal is not silent. See module docstring, "WHY
    `evidence` HAS NO DEFAULT."

    `recommendations_dir` defaults to `RECOMMENDATIONS_DIR` (the resolved brain root's
    `state/recommendations/`). If NEITHER an override nor a resolved brain root is available,
    this REFUSES — see module docstring "WHAT HAPPENS WITH NO BRAIN ROOT CONFIGURED."
    """
    payload = dict(payload or {})
    recommendations_dir = recommendations_dir or RECOMMENDATIONS_DIR
    if recommendations_dir is None:
        raise RecommendationContractError(
            "emit_recommendation(): no notes root is configured — brain_root.resolve_brain_root() "
            "returned NOT-SET, and no recommendations_dir= override was given. Refusing to write "
            "rather than guess a location. Fix: `python3 shared/brain_root.py --set <folder>` "
            "(add --create for a new folder), or pass recommendations_dir= explicitly (tests do this).")

    # ── VALIDATE at the source (fail loud, never silent) ──
    errs = []

    producer_valid = False
    if not producer or not isinstance(producer, str):
        errs.append("producer must be a non-empty str")
    else:
        producer_valid = True
        # Unlike emit_finding's `producer`, this value never becomes part of a filename here
        # (the shard key is `altitude`, not `producer` — see module docstring), so no
        # filename-safety regex is enforced on it; it is validated only as identity, not as a
        # path component.

    altitude_valid = False
    if altitude not in VALID_ALTITUDE:
        errs.append(f"altitude {altitude!r} not in {sorted(VALID_ALTITUDE)}")
    else:
        altitude_valid = True

    if not action or not isinstance(action, str):
        errs.append("action must be a non-empty str")

    evidence_valid = False
    if not isinstance(evidence, list) or not evidence:
        errs.append("evidence must be a non-empty list of finding fingerprints — a "
                     "recommendation that cannot cite the findings that caused it is REFUSED")
    else:
        bad_items = [e for e in evidence if not isinstance(e, str) or not e]
        if bad_items:
            errs.append(f"evidence entries must be non-empty str fingerprints; got {bad_items!r}")
        else:
            evidence_valid = True

    labels_valid = False
    if not isinstance(labels, dict) or not labels:
        errs.append("labels must be a non-empty dict (it is the recommendation's identity)")
    else:
        bad_keys = [k for k in labels if not isinstance(k, str) or not k]
        if bad_keys:
            errs.append(f"labels keys must be non-empty str: {bad_keys}")
        else:
            labels_valid = True

    if not isinstance(rc, int) or isinstance(rc, bool):
        errs.append("rc must be an int")
    if not isinstance(schema_version, int) or isinstance(schema_version, bool):
        errs.append("schema_version must be an int")
    clash = [k for k in payload if k in ENVELOPE_KEYS]
    if clash:
        errs.append(f"payload keys collide with reserved envelope keys: {clash}")

    if not evidence_valid and producer_valid and altitude_valid and labels_valid:
        # THE FIX — see module docstring "WHY THE REFUSAL MUST STILL LEAVE A RECORD". A
        # refusal alone makes the caller's exception the ONLY record; if the caller
        # catches-and-dies (or catches-and-swallows) the no-evidence call that caused it
        # leaves NO trace anywhere. Write the canary FIRST, into the normal recommendations
        # store, attributed to this same producer/altitude — THEN raise below exactly as
        # always. Gated on producer_valid/altitude_valid/labels_valid so a call that is ALSO
        # malformed in an unrelated way doesn't try to write a canary through a broken
        # filename or an unusable label set; that call is refused by the raise below same as
        # always, just without a canary (there is nothing sane to attribute it to).
        _write_no_evidence_canary(producer=producer, altitude=altitude, labels=labels,
                                    action=action if isinstance(action, str) else "",
                                    summary=summary, recommendations_dir=recommendations_dir,
                                    write_timeout_s=write_timeout_s)

    if errs:
        raise RecommendationContractError(f"emit_recommendation({producer!r}): " + " ; ".join(errs))

    machine = get_machine_token()
    fingerprint = _fingerprint(labels)

    env = {
        "producer": producer,
        "machine": machine,
        "schema_version": int(schema_version),
        "ts": ts or _iso_now(),
        "altitude": altitude,
        "action": str(action),
        "summary": str(summary),
        "rc": int(rc),
        "evidence": list(evidence),
        "labels": dict(labels),
        "fingerprint": fingerprint,
    }
    row = {**env, **payload}
    line = json.dumps(row, sort_keys=True) + "\n"

    out_path = os.path.join(recommendations_dir, f"{altitude}.{machine}.jsonl")

    # ── append-only write to the resolved brain root. No try/except swallow here — a write
    # failure (including a measured-flaky mount) is left to propagate as a normal OSError,
    # exactly like emit_finding.py's write does. The alarm below only guards the ONE failure
    # mode a raised OSError can't: a hang instead of an error. ──
    with _Alarm(write_timeout_s):
        os.makedirs(recommendations_dir, exist_ok=True)
        with open(out_path, "a") as f:
            f.write(line)

    return row


# ── CLI (mirrors emit_finding.py's — same shape, same "no accidental green" posture) ──────
def _build_argparser():
    ap = argparse.ArgumentParser(
        prog="emit_recommendation.py",
        description="Write ONE validated Efficiency recommendation through emit_recommendation(). "
                     "Fails loud (non-zero exit, stderr) on any contract violation — never silent. "
                     "Efficiency SUGGESTS, it never applies: this only ever writes a proposal record.",
    )
    ap.add_argument("--selftest", action="store_true",
                     help="run the built-in self-test (writes to a temp dir) and exit; ignores all other flags")
    ap.add_argument("--producer")
    ap.add_argument("--altitude", default=None,
                     help=f"REQUIRED — no default. One of {sorted(VALID_ALTITUDE)}.")
    ap.add_argument("--action", default=None,
                     help="REQUIRED — no default. The recommended move, in prose.")
    ap.add_argument("--evidence", action="append", default=[],
                     help="a finding fingerprint this recommendation cites, repeatable "
                          "(--evidence <fp1> --evidence <fp2>). At least one is required — an "
                          "empty/omitted list is REFUSED (see module docstring).")
    ap.add_argument("--summary", default="")
    ap.add_argument("--rc", type=int, default=0)
    ap.add_argument("--schema-version", type=int, default=1)
    ap.add_argument("--ts", default=None)
    ap.add_argument("--label", action="append", default=[],
                     help="KEY=VALUE, repeatable (--label job=fault-proposer --label fault=x). "
                          "At least one is required — labels are the recommendation's identity.")
    ap.add_argument("--json", dest="json_payload", default=None,
                     help="JSON object to merge into payload= — '-' reads stdin, otherwise a file path")
    return ap


def _parse_labels(raw_list):
    out = {}
    for item in raw_list:
        if "=" not in item:
            raise RecommendationContractError(f"--label {item!r} must be KEY=VALUE")
        k, _, v = item.partition("=")
        out[k] = v
    return out


def _load_json_payload(json_payload):
    if json_payload is None:
        return {}
    if json_payload == "-":
        raw = sys.stdin.read()
    else:
        with open(json_payload) as f:
            raw = f.read()
    obj = json.loads(raw)
    if not isinstance(obj, dict):
        raise RecommendationContractError(f"--json payload must decode to a JSON object, got {type(obj).__name__}")
    return obj


def _selftest():
    import tempfile

    d = tempfile.mkdtemp()
    row = emit_recommendation(producer="selftest", altitude="INSTANCE",
                                action="fix the thing that broke", evidence=["fp-aaa", "fp-bbb"],
                                labels={"job": "selftest", "check": "smoke"},
                                summary="self test", payload={"detail": "ok"},
                                recommendations_dir=d)
    machine = get_machine_token()
    out_path = os.path.join(d, f"INSTANCE.{machine}.jsonl")
    with open(out_path) as f:
        written = json.loads(f.readline())
    assert written["fingerprint"] == row["fingerprint"]
    print("valid emit wrote + validated:",
          {k: written[k] for k in ("producer", "machine", "altitude", "evidence", "fingerprint")})

    # fingerprint reproducibility: same labels, different insertion order -> identical hash;
    # a genuinely different label set -> a different hash. Checked BEFORE the rejection loop so
    # a bad assertion here isn't masked by later output.
    fp_a = _fingerprint({"job": "x", "check": "y"})
    fp_b = _fingerprint({"check": "y", "job": "x"})
    fp_c = _fingerprint({"job": "x", "check": "z"})
    assert fp_a == fp_b, "same label set in different insertion order must hash identically"
    assert fp_a != fp_c, "a different label set must hash differently"
    print("fingerprint reproducible + order-independent:", fp_a[:16], "==", fp_b[:16], "!=", fp_c[:16])

    BASE = dict(producer="selftest", altitude="INSTANCE", action="do something",
                evidence=["fp-ccc"], labels={"job": "x"})
    for label, override in [
        ("bad altitude", {"altitude": "SATELLITE"}),
        ("no evidence (empty list)", {"evidence": []}),
        ("evidence with a blank entry", {"evidence": ["fp-ok", ""]}),
        ("empty labels", {"labels": {}}),
        ("empty action", {"action": ""}),
        ("envelope collision via payload", {"payload": {"fingerprint": "hand-authored"}}),
    ]:
        kw = dict(BASE, **override)
        try:
            emit_recommendation(recommendations_dir=d, **kw)
            print(f"FAILED to reject: {label}"); sys.exit(1)
        except RecommendationContractError as e:
            print(f"rejected {label}: {str(e)[:90]}")

    # BOTH evidence-invalid refusals above ("no evidence" AND "evidence with a blank entry")
    # independently satisfy the canary gate (producer_valid/altitude_valid/labels_valid all
    # true in both cases — only `evidence` itself is what's wrong), so BOTH must have left a
    # canary on disk in this same INSTANCE shard. The bad-altitude, bad-labels, bad-action, and
    # payload-collision refusals each fail for an UNRELATED reason and must NOT fire a canary —
    # so the total is 1 valid recommendation + 2 canaries, never more.
    with open(out_path) as f:
        all_lines = [json.loads(ln) for ln in f if ln.strip()]
    assert len(all_lines) == 3, f"expected 1 valid recommendation + 2 canaries, got {len(all_lines)}"
    canaries = all_lines[1:]
    assert len(canaries) == 2, f"expected exactly 2 canaries, got {len(canaries)}"
    for canary in canaries:
        assert canary["evidence"] == [] and canary["labels"].get("kind") == "no-evidence" \
            and canary["producer"] == "selftest" and canary["altitude"] == "INSTANCE", \
            f"canary shape wrong: {canary}"
    print("canaries written + shaped correctly for BOTH evidence-invalid refusals, and ONLY those:",
          [{k: c[k] for k in ("producer", "altitude", "evidence", "fingerprint")} for c in canaries])

    # No-root refusal: with no recommendations_dir= override and no brain root resolved,
    # emit_recommendation() must refuse cleanly (RecommendationContractError) rather than write
    # anywhere or crash. Exercised against a scratch-root-less environment via monkeypatching the
    # module global rather than touching real process env (never touch the real brain root from
    # a self-test).
    global RECOMMENDATIONS_DIR
    real_dir = RECOMMENDATIONS_DIR
    RECOMMENDATIONS_DIR = None
    try:
        try:
            emit_recommendation(producer="selftest", altitude="INSTANCE", action="do it",
                                 evidence=["fp-zzz"], labels={"job": "x"})
            print("FAILED to refuse with no root configured"); sys.exit(1)
        except RecommendationContractError as e:
            assert "no notes root" in str(e) or "recommendations_dir" in str(e), str(e)
            print(f"refused cleanly with no root configured: {str(e)[:90]}")
    finally:
        RECOMMENDATIONS_DIR = real_dir

    print("emit_recommendation.py self-test PASSED")


def _main(argv):
    ap = _build_argparser()
    # bare invocation must NOT print anything green — same fix emit_finding.py needed
    # retrofitted; built in here from the start instead.
    if not argv:
        ap.print_usage(sys.stderr)
        print("emit_recommendation.py: error: no arguments given — pass --selftest, or "
              "--producer/--altitude/--action/--evidence/--label ... to write a recommendation.",
              file=sys.stderr)
        return 2

    args = ap.parse_args(argv)

    if args.selftest:
        _selftest()
        return 0

    missing = [flag for flag, val in (("--producer", args.producer),
                                       ("--altitude", args.altitude),
                                       ("--action", args.action)) if val is None]
    if missing:
        print(f"emit_recommendation.py: error: missing required flag(s): {', '.join(missing)}",
              file=sys.stderr)
        return 2

    try:
        labels = _parse_labels(args.label)
        payload = _load_json_payload(args.json_payload)
        emit_recommendation(
            producer=args.producer,
            altitude=args.altitude,
            action=args.action,
            evidence=args.evidence,
            labels=labels,
            summary=args.summary,
            payload=payload,
            rc=args.rc,
            schema_version=args.schema_version,
            ts=args.ts,
        )
    except RecommendationContractError as e:
        print(f"emit_recommendation.py: RecommendationContractError: {e}", file=sys.stderr)
        return 1
    except (OSError, TimeoutError, json.JSONDecodeError) as e:
        print(f"emit_recommendation.py: error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "system", "tools")))
    from utf8_stdio import force_utf8_stdio
    force_utf8_stdio()
    sys.exit(_main(sys.argv[1:]))

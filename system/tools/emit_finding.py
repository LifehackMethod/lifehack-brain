#!/usr/bin/env python3
"""emit_finding.py — the ONE validating writer every Hospital detector goes through.

Sibling of `system/tools/emit_status.py` (read that file first, if/when it lands in this repo —
this matches its posture: build the envelope, validate at write time, fail loud, atomic-ish
append, a CLI so shell detectors and Python detectors share ONE validator by reference, not by
copy-paste).

WHAT HOSPITAL IS. Every detector in a system tends to report its own way — divergent formats,
none comparable. Hospital's job: turn every one of those into ONE comparable record, so "what is
wrong?" can be asked once, at any altitude, and answered with a ranked, evidence-cited list.
Hospital DETECTS and RANKS. It never remediates — this module does not retry, does not fix, does
not re-run anything. It writes findings, full stop.

WHY `scanned_n` HAS NO DEFAULT — THE SINGLE MOST IMPORTANT FIELD HERE.
A detector that degrades to an empty result on a parse failure can go on to emit a perfectly
fresh, perfectly green heartbeat over a ZERO-length scan — a detector that saw nothing reporting
exactly like a detector that checked everything and found it clean. A finding-emitter that let
`scanned_n` default to 0 would let every one of those silent degradations sail through as
`status="OK"`. So `scanned_n` is a required keyword with NO default (omitting it is a TypeError
from Python itself, not a defaulted zero) AND the writer additionally refuses `scanned_n == 0`
paired with `status == "OK"` — a detector that scanned nothing must be structurally unable to
say "fine."

WHY `machine` IS DERIVED, NEVER PASSED. The donor system this module was ported from ran on two
physical machines that could each call themselves something different for the same detector,
forking one status tile into two — the fix there was routing every consumer through ONE shared
derivation instead of each reinventing it. **Fixed 2026-08-23 (issue #87): this product is NOT
one machine by design** — `shared/brain_root.py`'s own resolution order includes a shared/mounted
folder (Google Drive), so two machines pointed at the same brain root is a real, confirmed
install shape, not a hypothetical. A hardcoded `MACHINE = "local"` constant reintroduced the
EXACT donor bug it claimed to have fixed: two machines both write findings for the same producer
into the identical `<producer>.local.jsonl` shard, and the records collide/interleave with no
prune or retention route to recover. `get_machine_token()` below now derives a REAL per-machine
identity from the OS hostname (`socket.gethostname()` — the same primitive `section_archive.py`
and `pad_archive.py` already use in this repo to tag a machine, so this borrows an established
identity source rather than inventing one), sanitized to the filename-safe token alphabet. The
CONTRACT is unchanged: no `machine=` parameter exists on `emit_finding()`, full stop — the value
always comes from `get_machine_token()` below, never from a caller.

WHY `fingerprint` HAS NO PARAMETER, NOT EVEN A DEFAULTED ONE. Borrowed from Prometheus
Alertmanager: alert identity is mechanical (a hash of the label set), never hand-authored,
because a hand-authored id is a second place identity can drift from the data it describes.
So `emit_finding()`'s signature has no `id=` and no `fingerprint=` kwarg at all — passing
either is a `TypeError` raised by Python's own argument binding, before a single line of this
module's code runs. The fingerprint is `sha256` of the label set, canonicalized by sorting
(key, str(value)) pairs — so the SAME labels in a different insertion order hash identically,
and a different label set hashes differently. That is the whole identity model.

WHERE FINDINGS LAND, AND WHY ONE FILE PER (producer, machine). A shared append-only log that
writes "machine" INTO every line still forks when more than one machine reads it back at once —
a field inside the file does not stop the file itself from forking. One writer per PATH is what
holds, so the machine token goes in the FILENAME:
`<brain>/state/findings/<producer>.<machine>.jsonl`, append-only, where `<brain>` is resolved
through `shared/brain_root.py` — never a hardcoded folder belonging to one person. `<machine>` is
a real per-host token derived by `get_machine_token()` below (see issue #87 fix, above), so a
shared brain root (e.g. Google Drive) mounted from two machines now shards into two distinct
files instead of one forked/interleaved one.

WHAT HAPPENS TO FINDINGS ALREADY WRITTEN UNDER THE OLD `"local"` CONSTANT. They are left exactly
where they are — `<producer>.local.jsonl` is not renamed, merged, or deleted by this fix. Renaming
it to either machine's new real token would be a GUESS (which machine actually wrote which of the
interleaved lines is not recoverable from the file itself — that is the data loss this issue
reports), and deleting it would destroy whatever pre-fix history is still readable. Those files
simply become a frozen pre-#87 shard; every new finding from this fix forward lands in the
correctly-sharded `<producer>.<realhost>.jsonl` files going forward.

WHAT HAPPENS WITH NO BRAIN ROOT CONFIGURED. Unlike a read (which can honestly say "nothing found
yet"), a WRITE with no configured destination has no honest place to land — guessing one is
exactly the custody error the `brain_root` resolver exists to prevent (see that module's own
docstring). So `emit_finding()` REFUSES outright — raises `FindingContractError`, writes
nothing, creates no directory — when `resolve_brain_root()` returns NOT-SET and no
`findings_dir=` override was passed. Tests always pass `findings_dir=` explicitly and never hit
this path.

WHY A WRITE FAILURE RAISES HERE, RATHER THAN DEGRADING. This module has no local copy: the
resolved brain root IS the store. A silent failure here is unrecoverable data loss, so any
OSError during the write (including a wedged or flaky network-mounted folder) is left to
propagate, never caught-and-swallowed. A signal-based timeout guards the one failure mode a
raised OSError can't cover — a mount that hangs instead of erroring — so a bad filesystem day
fails loud and FAST, never silently and never by hanging the caller forever.

Compatible with `/usr/bin/python3` (3.9) — no `X | None` union annotations, stdlib only.
"""
import argparse
import hashlib
import json
import os
import re
import signal
import socket
import sys
import threading
import time

# ── MACHINE TOKEN — re-derived locally, NOT imported. ───────────────────────────────────────
# `machine_token.py` is part of the two-machine plane this product doesn't have (excluded
# 2026-08-13 — see that module's own DOES-NOT-MIGRATE banner in the donor repo) and is never
# imported, copied, or shelled out to from here.
#
# issue #87 — FIXED 2026-08-23: this repo's own `shared/brain_root.py` resolves to a Google-Drive
# folder as a normal, supported route, so "two machines, one brain root" is a real install shape,
# not a hypothetical. A fixed `MACHINE = "local"` constant made every such install collide: both
# machines wrote the same producer's findings into the identical `<producer>.local.jsonl` shard,
# interleaving records with no prune or retention route to recover. `get_machine_token()` now
# derives a REAL per-machine identity from `socket.gethostname()` — the same primitive
# `section_archive.py`/`pad_archive.py` already use elsewhere in this repo to tag a machine, so
# this reuses an established identity source rather than inventing a new one.
_MACHINE_TOKEN_SAFE = re.compile(r"[^A-Za-z0-9_-]+")


class MachineIdentityError(RuntimeError):
    """Raised when this machine's identity cannot be determined at all — see get_machine_token().
    Deliberately its OWN exception type, distinct from FindingContractError: a malformed finding
    and a homeless one are different facts, and (per this repo's ABSENT-SUBJECT-RULE-v1,
    `system/build-rules-index.md`) an absent/undeterminable subject must report as its own
    distinct outcome, never fold silently into a passing value — which is exactly what the old
    `MACHINE = "local"` constant did for every caller, valid hostname or not."""


def get_machine_token():
    """Derive this machine's identity for the findings-shard filename.

    Sanitizes `socket.gethostname()` down to the filename-safe alphabet the finding filename
    requires (see `emit_finding()`'s own `_SAFE_TOKEN` check on `producer`): any run of
    characters outside `[A-Za-z0-9_-]` (dots, spaces — e.g. "host-name.local") collapses
    to a single "-", and leading/trailing "-" are trimmed.

    ⛔ Raises `MachineIdentityError` — never returns a shared/fallback value — if the hostname
    cannot be obtained (`socket.gethostname()` raising `OSError`) or sanitizes down to nothing.
    This is deliberately NOT caught here: it propagates out of `emit_finding()` so a finding that
    cannot be safely attributed to a specific machine is REFUSED (same posture as the no-brain-
    root refusal below), never silently mis-attributed to a shared constant."""
    try:
        raw = socket.gethostname()
    except OSError as e:
        raise MachineIdentityError(
            f"could not determine machine identity: socket.gethostname() failed: {e}")
    if not raw or not raw.strip():
        raise MachineIdentityError(
            "could not determine machine identity: socket.gethostname() returned empty")
    token = _MACHINE_TOKEN_SAFE.sub("-", raw.strip()).strip("-")
    if not token:
        raise MachineIdentityError(
            f"could not determine machine identity: hostname {raw!r} sanitizes to empty")
    return token


# ── ONE status vocabulary — inlined here, not imported. ─────────────────────────────────────
# `emit_status.py` (the tile-writer this vocabulary really belongs to) has not landed in this
# product yet as of this port, so importing it would make this module fail to even LOAD until
# it does. VALID_STATUS is restated here rather than deferred behind a guess: findings need to
# compare against the same OK/NEEDS_REVIEW/NEEDS_APPROVAL/DRIFT/ERROR vocabulary every status
# tile uses, or Hospital cannot rank a finding against a tile on the same axis. If/when
# `emit_status.py` ships here, prefer importing its `VALID_STATUS` over this copy so the two can
# never drift apart — this duplication exists only because of ordering, not by design.
VALID_STATUS = {"OK", "NEEDS_REVIEW", "NEEDS_APPROVAL", "DRIFT", "ERROR"}

# ── WHERE FINDINGS LAND — resolved through the ONE brain-root resolver, never guessed. ──────
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

# None when no root is configured — see `emit_finding()`'s refusal below. Unlike a reader, a
# WRITER has no honest fallback location: guessing one is the exact custody error `brain_root`
# exists to prevent, so this module simply has nothing to write to until a root is set.
FINDINGS_DIR = os.path.join(_ROOT, "state", "findings") if _ROOT else None

# Reserved envelope keys — a caller's `payload` dict may never contain any of these. This is
# the SAME collision guard emit_status.py runs ("never let a payload field silently shadow an
# envelope field"), extended to also block a payload-smuggled "id"/"fingerprint"/"labels" —
# the belt to the TypeError's suspenders (see module docstring: no such kwarg exists on
# emit_finding() itself, so this only matters for someone trying to sneak it in via payload=).
ENVELOPE_KEYS = ("producer", "machine", "schema_version", "ts", "scanned_n", "status",
                  "summary", "rc", "fingerprint", "labels", "id")

WRITE_TIMEOUT_S = 15   # signal-based hang guard on the write; see module docstring.

_SAFE_TOKEN = re.compile(r"^[A-Za-z0-9_-]+$")


def _iso_now():
    lt = time.localtime()
    off = time.strftime("%z", lt)
    off = (off[:3] + ":" + off[3:]) if off else "+00:00"
    return time.strftime("%Y-%m-%dT%H:%M:%S", lt) + off


class FindingContractError(ValueError):
    """Raised at WRITE time when a finding violates the envelope or label contract — OR when
    there is nowhere to write it at all (no brain root configured, no override given). Same
    posture as emit_status.py's EmitContractError — a malformed or homeless finding must scream
    at the emitter, never go quietly empty downstream."""


class _Alarm:
    """Signal-based timeout so a wedged mount fails LOUD and fast instead of hanging
    the caller forever. Only armed on platforms with SIGALRM (macOS has it); a no-op
    elsewhere rather than a crash. PEP 475: the raised exception interrupts a blocking
    syscall in progress instead of the syscall silently retrying."""

    def __init__(self, seconds):
        self.seconds = seconds
        # ⚠ SIGALRM IS MAIN-THREAD-ONLY, and the platform check alone is NOT enough.
        # `signal.signal()` raises `ValueError: signal only works in main thread of the main
        # interpreter` from ANY other thread — so a `hasattr(signal, "SIGALRM")`-only guard
        # silently converts this HANG PROTECTION into a HARD CRASH for every threaded caller.
        # Off the main thread we skip the alarm and accept the (much rarer) hang risk — **a
        # detector that cannot record a finding AT ALL is strictly worse than one that might
        # block**, and this module's whole purpose is that a problem cannot go unrecorded. The
        # OSError path (the common flaky-mount failure) still propagates normally off-thread;
        # only the wedged-mount hang guard is unavailable.
        self._have_alarm = (hasattr(signal, "SIGALRM")
                            and threading.current_thread() is threading.main_thread())
        self._old = None

    def _handler(self, signum, frame):
        raise TimeoutError(
            f"emit_finding: write exceeded {self.seconds}s — the brain root's mount likely "
            "wedged (not a normal error, which returns immediately; this is a hang)")

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
    any insertion order, hash identically. Values are coerced to str for the canonical form
    (labels are identity descriptors, not typed metrics — those belong in scanned_n/payload)."""
    items = sorted((str(k), str(v)) for k, v in labels.items())
    canonical = json.dumps(items, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _write_zero_scan_canary(*, producer, labels, summary, findings_dir, write_timeout_s):
    """INTERNAL ONLY. Writes the canary finding that makes a refused zero-scan-OK call VISIBLE
    on the board, not just loud to the immediate caller.

    ⚠ NOT part of the public contract. Leading underscore, no CLI flag reaches it, it is
    called from exactly ONE call site (inside emit_finding()'s own validation block, with
    hard-coded status="ERROR"/scanned_n=0 baked in below — never taken from caller input) and
    it is never exported or documented as something a detector calls directly. A detector that
    wants to record a real finding always goes through emit_finding().

    ⚠ WHY THIS CANNOT RECURSE: this function does NOT call emit_finding() — it builds and
    writes its own envelope by hand, the same few lines emit_finding() itself uses, duplicated
    here on purpose. It never re-enters the scanned_n==0/status==OK check at all, so there is no
    path back into itself, no matter what is passed. It is a dead-end, not a loop.

    The canary is attributed to the SAME producer (so it lands in that producer's own shard,
    ranked and read exactly like every other finding from that detector — no separate store,
    no special-casing anywhere downstream) with status="ERROR" and labels carrying
    kind="zero-scan" so it is unmistakable in a label-filtered view.
    """
    machine = get_machine_token()
    canary_labels = dict(labels)
    canary_labels["kind"] = "zero-scan"
    fingerprint = _fingerprint(canary_labels)

    env = {
        "producer": producer,
        "machine": machine,
        "schema_version": 1,
        "ts": _iso_now(),
        "scanned_n": 0,
        "status": "ERROR",
        "summary": (f"CANARY: producer {producer!r} called emit_finding() with status=\"OK\" "
                    f"and scanned_n=0 — it examined NOTHING while reporting fine. The call was "
                    f"REFUSED (FindingContractError) so no false-OK finding was written; this "
                    f"canary is the only record that the refusal happened. Original summary "
                    f"offered: {summary!r}"),
        "rc": 1,
        "labels": canary_labels,
        "fingerprint": fingerprint,
    }
    line = json.dumps(env, sort_keys=True) + "\n"
    out_path = os.path.join(findings_dir, f"{producer}.{machine}.jsonl")

    # Same no-swallow posture as the main write below: a canary that silently fails to land is
    # exactly the silence this task exists to abolish, so a write failure here propagates too.
    with _Alarm(write_timeout_s):
        os.makedirs(findings_dir, exist_ok=True)
        with open(out_path, "a") as f:
            f.write(line)
    return env


def emit_finding(*, producer, status, scanned_n, labels, summary="", payload=None,
                  rc=0, schema_version=1, ts=None, write_timeout_s=WRITE_TIMEOUT_S,
                  findings_dir=None, done_when=None):
    """Validate + write ONE finding as an appended JSONL line.

    Envelope fields (producer, machine, schema_version, ts, scanned_n, status, summary, rc,
    labels, fingerprint) are OWNED by this function — a caller passes only `payload` for
    finding-specific data (e.g. evidence, a title, a threshold). There is deliberately no
    `machine=`, no `id=`, and no `fingerprint=` parameter — see the module docstring for why
    each of those would reintroduce a bug this codebase already paid for once.

    `scanned_n` has no default: omit it and Python itself raises TypeError before this
    function's body runs at all.

    `findings_dir` defaults to `FINDINGS_DIR` (the resolved brain root's `state/findings/`).
    If NEITHER an override nor a resolved brain root is available, this REFUSES — see module
    docstring "WHAT HAPPENS WITH NO BRAIN ROOT CONFIGURED."
    """
    payload = dict(payload or {})
    findings_dir = findings_dir or FINDINGS_DIR
    if findings_dir is None:
        raise FindingContractError(
            "emit_finding(): no notes root is configured — brain_root.resolve_brain_root() "
            "returned NOT-SET, and no findings_dir= override was given. Refusing to write "
            "rather than guess a location. Fix: `python3 shared/brain_root.py --set <folder>` "
            "(add --create for a new folder), or pass findings_dir= explicitly (tests do this).")

    # ── VALIDATE at the source (fail loud, never silent) ──
    errs = []
    producer_valid = False
    if not producer or not isinstance(producer, str):
        errs.append("producer must be a non-empty str")
    elif not _SAFE_TOKEN.match(producer):
        errs.append(f"producer {producer!r} must match {_SAFE_TOKEN.pattern} "
                     "(it becomes part of the output filename)")
    else:
        producer_valid = True
    if status not in VALID_STATUS:
        errs.append(f"status {status!r} not in {sorted(VALID_STATUS)}")
    zero_scan_ok_violation = False
    if isinstance(scanned_n, bool) or not isinstance(scanned_n, int):
        errs.append("scanned_n must be an int (not bool, not float, not None)")
    elif scanned_n < 0:
        errs.append("scanned_n must be >= 0")
    elif scanned_n == 0 and status == "OK":
        # THE core rule this module exists to enforce — see module docstring. This is no
        # longer JUST a refusal — see the canary write below, right before the raise.
        errs.append("scanned_n == 0 cannot be paired with status == \"OK\": a detector that "
                     "scanned nothing has not verified anything is fine")
        zero_scan_ok_violation = True
    labels_valid = False
    if not isinstance(labels, dict) or not labels:
        errs.append("labels must be a non-empty dict (it is the finding's identity)")
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

    # ── `done_when`: THE CHANNEL CLASSIFIER, shipped as a WARNING ──────────────────────────
    # ⭐ THIS IS NOT A VALIDATION NICETY. A system has TWO channels — FINDINGS (faults) and
    # STATUS TILES (standing world-state) — and nothing decides which one a producer uses unless
    # something asks. That is how "the printer is offline", "a config value is pending" and
    # "11 items awaiting review" can all end up sitting in the FAULT channel, where they can
    # never clear, occupy a session banner forever, and kill "silence means clean" outright.
    # ⇒ THE RULE, expressed as one field: if a producer can name what would make this finding
    #   STOP, it is a FAULT and belongs here. If it cannot, it is STANDING STATE and belongs on
    #   a tile.
    #
    # ⛔ WARNING, NEVER A REFUSAL — AND THE REASON IS ARITHMETIC, NOT CAUTION. On the donor
    # system, ALL live producers emitted with no `done_when` at the time this field was added. A
    # fail-closed clause would therefore silence the ENTIRE findings channel on the next tick —
    # not part of it. ⇒ Flipping warn -> refuse is ONE line once producers are converted. Do not
    # flip it early.
    #
    # SCOPE: only NOT-OK findings. An `OK` finding has nothing to clear, so demanding a
    # done_when for one would be noise — and noise in a warning is how a warning gets ignored.
    if status != "OK" and not (isinstance(done_when, str) and done_when.strip()):
        print(f"[emit_finding] WARNING: producer {producer!r} emitted status={status!r} with no "
              f"`done_when` — it cannot say what would make this finding STOP. A finding that can "
              f"never clear is STANDING STATE, not a fault, and probably belongs on a status tile "
              f"instead. Not refused.",
              file=sys.stderr)

    if zero_scan_ok_violation and producer_valid and labels_valid:
        # THE FIX. A refusal alone makes the caller's exception the ONLY record; if the caller
        # catches-and-dies (or catches-and-swallows) the zero-length scan that caused it leaves
        # NO trace anywhere. Write the canary FIRST, into the normal findings store, attributed
        # to this same producer — THEN raise below exactly as before. Gated on
        # producer_valid/labels_valid so a call that is ALSO malformed in an unrelated way
        # (e.g. a garbage producer string) doesn't try to write a canary through a broken
        # filename or an unusable label set; that call is refused by the raise below same as
        # always, just without a canary (there is nothing sane to attribute it to).
        _write_zero_scan_canary(producer=producer, labels=labels, summary=summary,
                                 findings_dir=findings_dir, write_timeout_s=write_timeout_s)

    if errs:
        raise FindingContractError(f"emit_finding({producer!r}): " + " ; ".join(errs))

    machine = get_machine_token()
    fingerprint = _fingerprint(labels)

    env = {
        "producer": producer,
        "machine": machine,
        "schema_version": int(schema_version),
        "ts": ts or _iso_now(),
        "scanned_n": int(scanned_n),
        "status": status,
        "summary": str(summary),
        "rc": int(rc),
        "labels": dict(labels),
        "fingerprint": fingerprint,
    }
    # Only written when supplied, so a producer that doesn't pass done_when keeps its current
    # row shape byte-for-byte and no reader has to cope with a new always-present key mid-flight.
    # ⚠ DELIBERATELY NOT ADDED TO ENVELOPE_KEYS: that tuple is the reserved-name collision check
    # for payload=, and adding it there would REFUSE any producer already passing done_when in
    # its payload — turning a warning into the hard break this exists to avoid.
    if isinstance(done_when, str) and done_when.strip():
        env["done_when"] = done_when.strip()
    row = {**env, **payload}
    line = json.dumps(row, sort_keys=True) + "\n"

    out_path = os.path.join(findings_dir, f"{producer}.{machine}.jsonl")

    # ── append-only write to the resolved brain root. No try/except swallow here — a write
    # failure (including a measured-flaky mount) is left to propagate as a normal OSError,
    # exactly like emit_status.py's os.makedirs/open/os.replace calls already do. The alarm
    # below only guards the ONE failure mode a raised OSError can't: a hang instead of an
    # error. ──
    with _Alarm(write_timeout_s):
        os.makedirs(findings_dir, exist_ok=True)
        with open(out_path, "a") as f:
            f.write(line)

    return row


# ── CLI (mirrors emit_status.py's — same shape, same "no accidental green" fix baked in from
# the start rather than retrofitted) ──────────────────────────────────────────────────────
def _build_argparser():
    ap = argparse.ArgumentParser(
        prog="emit_finding.py",
        description="Write ONE validated Hospital finding through emit_finding(). "
                     "Fails loud (non-zero exit, stderr) on any contract violation — never silent.",
    )
    ap.add_argument("--selftest", action="store_true",
                     help="run the built-in self-test (writes to a temp dir) and exit; ignores all other flags")
    ap.add_argument("--producer")
    ap.add_argument("--status", default="OK")
    ap.add_argument("--scanned-n", type=int, default=None,
                     help="REQUIRED — no default. Omitting this flag is an error, not a 0.")
    ap.add_argument("--summary", default="")
    ap.add_argument("--rc", type=int, default=0)
    ap.add_argument("--schema-version", type=int, default=1)
    ap.add_argument("--ts", default=None)
    ap.add_argument("--label", action="append", default=[],
                     help="KEY=VALUE, repeatable (--label job=backlog-groom --label check=stale). "
                          "At least one is required — labels are the finding's identity.")
    ap.add_argument("--json", dest="json_payload", default=None,
                     help="JSON object to merge into payload= — '-' reads stdin, otherwise a file path")
    return ap


def _parse_labels(raw_list):
    out = {}
    for item in raw_list:
        if "=" not in item:
            raise FindingContractError(f"--label {item!r} must be KEY=VALUE")
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
        raise FindingContractError(f"--json payload must decode to a JSON object, got {type(obj).__name__}")
    return obj


def _selftest():
    import tempfile
    d = tempfile.mkdtemp()
    row = emit_finding(producer="selftest", status="OK", scanned_n=3,
                        labels={"job": "selftest", "check": "smoke"},
                        summary="self test", payload={"detail": "ok"},
                        findings_dir=d)
    machine = get_machine_token()
    out_path = os.path.join(d, f"selftest.{machine}.jsonl")
    with open(out_path) as f:
        written = json.loads(f.readline())
    assert written["fingerprint"] == row["fingerprint"]
    print("valid emit wrote + validated:", {k: written[k] for k in ("producer", "machine", "status", "fingerprint")})

    for label, kw in [
        ("scanned_n=0 with status=OK", dict(status="OK", scanned_n=0, labels={"job": "x"})),
        ("bad status", dict(status="GREEN", scanned_n=1, labels={"job": "x"})),
        ("empty labels", dict(status="OK", scanned_n=1, labels={})),
        ("envelope collision via payload", dict(status="OK", scanned_n=1, labels={"job": "x"},
                                                  payload={"fingerprint": "hand-authored"})),
    ]:
        try:
            emit_finding(producer="selftest", summary="", findings_dir=d, **kw)
            print(f"FAILED to reject: {label}"); sys.exit(1)
        except FindingContractError as e:
            print(f"rejected {label}: {str(e)[:80]}")

    # The refusal above ("scanned_n=0 with status=OK") must ALSO have left a canary finding on
    # disk in this same shard, and ONLY that one refusal (not the other three, which fail for
    # unrelated reasons and must not fire the canary).
    with open(out_path) as f:
        all_lines = [json.loads(ln) for ln in f if ln.strip()]
    assert len(all_lines) == 2, f"expected 1 valid finding + 1 canary, got {len(all_lines)}"
    canary = all_lines[1]
    assert canary["status"] == "ERROR" and canary["scanned_n"] == 0 \
        and canary["labels"].get("kind") == "zero-scan" and canary["producer"] == "selftest", \
        f"canary shape wrong: {canary}"
    print("canary written + shaped correctly for scanned_n=0/status=OK, and ONLY for that case:",
          {k: canary[k] for k in ("producer", "status", "scanned_n", "fingerprint")})

    # No-root refusal: with no findings_dir= override and no brain root resolved, emit_finding()
    # must refuse cleanly (FindingContractError) rather than write anywhere or crash. Exercised
    # against a scratch $LIFEHACK_ROOT-less environment via monkeypatching the module global
    # rather than touching real process env (never touch the real brain root from a self-test).
    global FINDINGS_DIR
    real_findings_dir = FINDINGS_DIR
    FINDINGS_DIR = None
    try:
        try:
            emit_finding(producer="selftest", status="OK", scanned_n=1, labels={"job": "x"})
            print("FAILED to refuse with no root configured"); sys.exit(1)
        except FindingContractError as e:
            assert "no notes root" in str(e) or "findings_dir" in str(e), str(e)
            print(f"refused cleanly with no root configured: {str(e)[:80]}")
    finally:
        FINDINGS_DIR = real_findings_dir

    print("emit_finding.py self-test PASSED")


def _main(argv):
    ap = _build_argparser()
    # bare invocation must NOT print anything green — same fix emit_status.py needed
    # retrofitted; built in here from the start instead.
    if not argv:
        ap.print_usage(sys.stderr)
        print("emit_finding.py: error: no arguments given — pass --selftest, or "
              "--producer/--status/--scanned-n/--label ... to write a finding.", file=sys.stderr)
        return 2

    args = ap.parse_args(argv)

    if args.selftest:
        _selftest()
        return 0

    missing = [flag for flag, val in (("--producer", args.producer),
                                       ("--scanned-n", args.scanned_n)) if val is None]
    if missing:
        print(f"emit_finding.py: error: missing required flag(s): {', '.join(missing)}", file=sys.stderr)
        return 2

    try:
        labels = _parse_labels(args.label)
        payload = _load_json_payload(args.json_payload)
        emit_finding(
            producer=args.producer,
            status=args.status,
            scanned_n=args.scanned_n,
            labels=labels,
            summary=args.summary,
            payload=payload,
            rc=args.rc,
            schema_version=args.schema_version,
            ts=args.ts,
        )
    except FindingContractError as e:
        print(f"emit_finding.py: FindingContractError: {e}", file=sys.stderr)
        return 1
    except MachineIdentityError as e:
        print(f"emit_finding.py: MachineIdentityError: {e}", file=sys.stderr)
        return 1
    except (OSError, TimeoutError, json.JSONDecodeError) as e:
        print(f"emit_finding.py: error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "system", "tools")))
    from utf8_stdio import force_utf8_stdio
    force_utf8_stdio()
    sys.exit(_main(sys.argv[1:]))

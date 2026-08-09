#!/usr/bin/env python3
"""ingest_gate.py — the ON-PATH ingest harness: one entry point every desk's external read passes
through. Sanitize → scan → provenance-tag → route to the Sentinel verdict gate. Built to the FROZEN
call signature in system/schemas/ingest-gate-signature.md (v1.0); Window 3 of the organism build.

WHY: today each inbound channel wires its OWN sanitize→scan→route (safe_fetch/safe_csv/… → safe_input
.route_findings), and EMAIL never routed at all (email_convert._flag_injection printed to stderr only —
its alarm was disconnected). This gate is the single shared path that (a) closes the email hole, (b)
tags provenance (desk + source + content-hash) so coverage is mechanical not opt-in, and (c) enforces
the LOCKED email FLAG-never-DANGER invariant. Stdlib-only. Defensive: never raises on its own internals.

POSTURE (posture-controlled since Window 5): env INGEST_GATE_POSTURE = "enforce" (DEFAULT since the W5
cutover) | "warn". ENFORCE = a read that can't be gated is DENIED (passed=False, fail-CLOSED) for every
channel EXCEPT email — email stays fail-open even under enforce because it is FLAG-floored by the locked
invariant and can never DANGER/quarantine, so failing it open removes zero containment. WARN = an
internal error returns passed=True (fail-OPEN) — the pre-cutover behavior + the INSTANT REVERT
(INGEST_GATE_POSTURE=warn). The DANGER verdict path (non-email exit 2 → passed=False) is posture-independent.

CONTRACT (frozen v1.0):
  gate(desk_id, source_type, raw_content, message_id="", item="") -> {
    "content":        sanitized content (== "" on DANGER),
    "provenance_tag": "{desk_id}/{source_type}/{sha256_8}",
    "passed":         True (FLAG/CLEAN → continue) | False (DANGER → caller HALTS, already contained),
  }
  source_type ∈ {email, web, file, calendar, api}. On DANGER, Sentinel has ALREADY logged + pushed +
  paused the source (+ Gmail-quarantined if message_id given). The caller MUST NOT process the item.

  LOCKED email invariant: source_type=="email" ⇒ findings are capped at FLAG (never DANGER, never
  quarantine), until the provenance-aware classifier ships. The gate enforces it two ways — it passes
  --flag-only to the verdict tool AND never returns passed=False for email. Relaxing this requires a
  schema_version bump + Window-3 sign-off (see the schema doc).
"""
import sys, os, json, hashlib, subprocess

CODE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # shared/tools/ → root
_SYS_TOOLS = os.path.join(CODE_ROOT, "system", "tools")
if _SYS_TOOLS not in sys.path:
    sys.path.insert(0, _SYS_TOOLS)

# Reuse the existing L0 sanitizer + heuristic scanner — do NOT re-implement (one source of truth).
from sanitize import sanitize, NO_CAP            # system/tools/sanitize.py
from safe_input import scan_for_injection         # system/tools/safe_input.py

SENTINEL = os.path.join(CODE_ROOT, "shared", "tools", "sentinel_response.py")
VALID_SOURCE_TYPES = {"email", "web", "file", "calendar", "api"}

# CONTENT tier: the coverage breadcrumb ledger lives on the Drive spine (env-overridable for tests).
# Resolved from the brain root the user chose, never a hardcoded cloud path. Empty is fine —
# PROVENANCE_LOG below just falls back to a local cache dir.
DRIVE = os.environ.get("LIFEHACK_ROOT", os.path.expanduser("~/.cache/ingest-gate"))
PROVENANCE_LOG = os.environ.get("INGEST_PROVENANCE_LOG", f"{DRIVE}/state/status/ingest-provenance.jsonl")

# POSTURE (Window 5): "enforce" (default since the W5 cutover 2026-06-20) = fail-CLOSED — a read that
# can't be gated is DENIED — for every channel EXCEPT email. Email stays fail-open even under enforce: it
# is FLAG-floored by the LOCKED invariant and can never DANGER/quarantine, so failing it open removes
# zero containment while avoiding a brand-new way to break live email ingestion on a transient hiccup.
# "warn" = fail-OPEN on an internal gate error (the pre-cutover behavior + the INSTANT REVERT: set
# INGEST_GATE_POSTURE=warn). The DANGER verdict path (non-email exit 2) is unaffected by posture — it
# already returns passed=False.
POSTURE = os.environ.get("INGEST_GATE_POSTURE", "enforce").strip().lower()


def _breadcrumb(provenance_tag, source_type, desk_id, verdict):
    """Best-effort COVERAGE breadcrumb — one line per gated read (CLEAN included), to a DEDICATED
    ledger separate from sentinel-events.jsonl (which stays findings-only). This is what makes coverage
    MECHANICAL, not opt-in (the gate's stated WHY): ingest_coverage.py reads this so a desk that only
    ever reads clean content still shows as 'covered' instead of false-flagging a gap. NEVER raises — a
    coverage write must never break a live read."""
    try:
        import time as _t
        lt = _t.localtime(); off = _t.strftime("%z", lt); off = (off[:3] + ":" + off[3:]) if off else "+00:00"
        rec = {"ts": _t.strftime("%Y-%m-%dT%H:%M:%S", lt) + off, "desk": desk_id,
               "source_type": source_type, "provenance_tag": provenance_tag, "verdict": verdict}
        os.makedirs(os.path.dirname(PROVENANCE_LOG), exist_ok=True)
        with open(PROVENANCE_LOG, "a") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception as e:
        sys.stderr.write(f"[ingest-gate] breadcrumb write skipped ({e}) — read unaffected\n")


def _provenance_tag(desk_id, source_type, raw_content):
    """{desk_id}/{source_type}/{sha256_8} — tamper-evident, NOT a secret. Hash the raw (pre-sanitize)
    bytes so the tag witnesses exactly what was screened."""
    h = hashlib.sha256((raw_content or "").encode("utf-8", "replace")).hexdigest()[:8]
    return f"{desk_id}/{source_type}/{h}"


def gate(desk_id, source_type, raw_content, message_id="", item=""):
    """The frozen on-path gate. See module docstring for the contract. Never RAISES — but the verdict on an
    internal error is POSTURE-dependent: under ENFORCE (the default since the W5 cutover) a non-email read
    that can't be gated returns passed=False (fail-CLOSED); email always returns passed=True (fail-open,
    FLAG-floored, can't DANGER); under WARN all channels fail-open. The DANGER verdict path (returncode 2,
    non-email) returns passed=False independent of posture."""
    tag = _provenance_tag(desk_id, source_type, raw_content)
    try:
        clean = sanitize(raw_content or "", max_len=NO_CAP)
        findings = scan_for_injection(clean)

        # No findings → CLEAN: do NOT call the verdict tool (no event, no subprocess) so clean reads
        # stay silent to SENTINEL — mirrors safe_input.route_findings' early CLEAN return. We DO drop a
        # coverage breadcrumb, though, so a clean-only desk still shows as covered (Window 5).
        if not findings:
            _breadcrumb(tag, source_type, desk_id, "clean")
            return {"content": clean, "provenance_tag": tag, "passed": True}

        is_email = (source_type == "email")
        cmd = ["python3", SENTINEL, "--source", desk_id, "--item", (item or "")[:120],
               "--provenance", tag]
        if message_id and not is_email:
            cmd += ["--message-id", message_id]   # email never quarantines → never pass its id
        if is_email:
            cmd += ["--flag-only"]                 # LOCKED invariant: email capped at FLAG

        payload = json.dumps([[m, l] for m, l in findings])
        r = subprocess.run(cmd, input=payload, capture_output=True, text=True, timeout=20)

        # exit 2 = DANGER (only reachable for non-email; email is --flag-only → always exit 0).
        if r.returncode == 2 and not is_email:
            _breadcrumb(tag, source_type, desk_id, "danger")
            return {"content": "", "provenance_tag": tag, "passed": False}
        _breadcrumb(tag, source_type, desk_id, "flag")
        return {"content": clean, "provenance_tag": tag, "passed": True}
    except Exception as e:
        is_email = (source_type == "email")
        # ENFORCE (Window 5): a read that can't be gated is DENIED (fail-CLOSED) — EXCEPT email, which
        # stays fail-open (FLAG-floored, can't DANGER, so failing it open removes zero containment).
        if POSTURE == "enforce" and not is_email:
            sys.stderr.write(f"[ingest-gate] non-fatal ({e}) — ENFORCE posture: read DENIED (fail-closed)\n")
            _breadcrumb(tag, source_type, desk_id, "error-denied")
            return {"content": "", "provenance_tag": tag, "passed": False}
        # WARN posture (or any email) → fail-OPEN: a gate hiccup never breaks the read.
        sys.stderr.write(f"[ingest-gate] non-fatal ({e}) — read continues (fail-open), verdict undetermined\n")
        _breadcrumb(tag, source_type, desk_id, "error-open")
        try:
            content = sanitize(raw_content or "", max_len=NO_CAP) if raw_content else ""
        except Exception:
            content = ""
        return {"content": content, "provenance_tag": tag, "passed": True}


def main():
    import argparse
    ap = argparse.ArgumentParser(description="On-path ingest gate (frozen signature v1.0). "
                                             "Reads raw_content on stdin; prints the verdict dict as JSON.")
    ap.add_argument("--desk", required=True, help="consuming desk_id (desk-registry.yaml)")
    ap.add_argument("--source-type", required=True, choices=sorted(VALID_SOURCE_TYPES))
    ap.add_argument("--item", default="", help="short human-readable id for the event log")
    ap.add_argument("--message-id", default="", help="Gmail id (unlocks quarantine on DANGER; ignored for email)")
    a = ap.parse_args()
    res = gate(a.desk, a.source_type, sys.stdin.read(), message_id=a.message_id, item=a.item)
    print(json.dumps(res))
    return 0 if res["passed"] else 2   # mirror the verdict-tool exit convention for bash callers


if __name__ == "__main__":
    sys.exit(main())

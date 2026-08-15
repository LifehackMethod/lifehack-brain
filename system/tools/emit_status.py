#!/usr/bin/env python3
"""emit_status.py — the ONE write-time status-tile emitter + validator (the locked Bible, Layer 2).

Every desk tile is written THROUGH this. It builds the standard envelope, merges the desk's payload,
VALIDATES at write time (envelope present + typed; declared required payload fields present), and writes
ATOMICALLY (tmp → os.replace). A malformed tile fails LOUD here at the source — never silently at the
dashboard (the failure mode a status-tile-architecture review named as the worst).

PORTED (2026-08-15) from claudeops-config's `system/tools/emit_status.py` — verbatim in behavior. It was
already fully generic on arrival: no hardcoded paths (the caller passes `out_path`), no desk names, no
Drive/Google assumptions, stdlib only, and it never touches `brain_root` itself (every consumer resolves
its own tile path first and hands this module the finished path). Nothing needed loosening for F8.6.
Thirteen consumers in this repo (`shared/tools/email_summary_sync.py`, `shared/tools/item_store_read.py`,
`system/tools/health_line.py`, `system/tools/emit_finding.py`, `system/tools/planning-health.py`, and others)
already carry a `try: from emit_status import emit_status / except ImportError: <hand-rolled tile write>`
fallback shaped to match THIS envelope exactly — confirmed by reading their fallbacks before this port:
`desk`, `schema_version`, `pulse_job`, `emit_mode`, `stale_after_s`, `last_run`, `rc`, `status`, `summary`
+ payload, same `VALID_STATUS` vocabulary (their comments call it "the emit_status enum"). This file is
the preferred path landing; the fallbacks were never removed and keep working unchanged.

DELIBERATELY LIGHTWEIGHT (not JSON Schema / not a registry — that would be over-sized for a solo/small
system): a documented envelope + a small required-field assertion = "90% of the value at 10% of the
cost." Stdlib only.

USAGE (from a desk's *-health.py emitter — replace the hand-rolled json.dump):
    from emit_status import emit_status   # or: sys.path-insert system/tools
    emit_status(
        f"{STATUS}/clair.json", desk="clair", pulse_job="clair-health", stale_after_s=21600,
        status="NEEDS_REVIEW", summary="18 unbilled ($1,042.50)",
        payload={"work_count": 18, "work_noun": "sessions", "kpis": [...], "items": [...]},
        required_payload=("work_count", "work_noun"),   # the fields THIS tile promises its renderer
    )

The `required_payload` tuple is the tile's CONTRACT with its renderer: list the fields the dashboard
card binds. If the emitter ever stops producing one, this raises at emit time instead of the card
silently going empty.
"""
import json, os, sys, time

ENVELOPE_KEYS = ("desk", "schema_version", "pulse_job", "emit_mode", "stale_after_s",
                 "last_run", "rc", "status", "summary")
VALID_STATUS = {"OK", "NEEDS_REVIEW", "NEEDS_APPROVAL", "DRIFT", "ERROR"}   # desks never emit STALE — a sweeper derives it
VALID_EMIT_MODE = {"pulse", "manual"}


def _iso_now():
    lt = time.localtime()
    off = time.strftime("%z", lt)
    off = (off[:3] + ":" + off[3:]) if off else "+00:00"
    return time.strftime("%Y-%m-%dT%H:%M:%S", lt) + off


class EmitContractError(ValueError):
    """Raised at WRITE time when a tile violates the envelope or its declared payload contract."""


def emit_status(out_path, *, desk, pulse_job, stale_after_s, payload=None,
                status="OK", rc=0, summary="", emit_mode="pulse",
                schema_version=2, last_run=None, required_payload=()):
    payload = dict(payload or {})

    # ── build the standard envelope ──
    env = {
        "desk": desk, "schema_version": int(schema_version), "pulse_job": pulse_job,
        "emit_mode": emit_mode, "stale_after_s": int(stale_after_s),
        "last_run": last_run or _iso_now(), "rc": int(rc),
        "status": status, "summary": str(summary),
    }

    # ── VALIDATE at the source (fail loud, never silent) ──
    errs = []
    if not desk or not isinstance(desk, str): errs.append("desk must be a non-empty str")
    if not pulse_job or not isinstance(pulse_job, str): errs.append("pulse_job must be a non-empty str")
    if status not in VALID_STATUS: errs.append(f"status {status!r} not in {sorted(VALID_STATUS)}")
    if emit_mode not in VALID_EMIT_MODE: errs.append(f"emit_mode {emit_mode!r} not in {sorted(VALID_EMIT_MODE)}")
    if env["stale_after_s"] <= 0: errs.append("stale_after_s must be > 0")
    # the tile's CONTRACT with its renderer: the fields it promised must actually be present
    missing = [k for k in required_payload if k not in payload]
    if missing: errs.append(f"payload missing declared contract fields: {missing}")
    # never let a payload field silently shadow an envelope field
    clash = [k for k in payload if k in env]
    if clash: errs.append(f"payload keys collide with envelope: {clash}")
    if errs:
        raise EmitContractError(f"{out_path}: " + " ; ".join(errs))

    out = {**env, **payload}

    # ── atomic write (a dashboard/reader polls — never leave a half-written file) ──
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    tmp = out_path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(out, f, indent=2)
    os.replace(tmp, out_path)
    return out


def _selftest():
    # self-test (no file side effects beyond /tmp)
    import tempfile
    d = tempfile.mkdtemp()
    p = os.path.join(d, "test.json")
    ok = emit_status(p, desk="test", pulse_job="test-health", stale_after_s=3600,
                     status="OK", summary="self test",
                     payload={"work_count": 3, "work_noun": "things"},
                     required_payload=("work_count", "work_noun"))
    assert json.load(open(p))["work_count"] == 3
    print("✓ valid emit wrote + validated:", {k: ok[k] for k in ("desk", "status", "work_count")})
    for label, kw in [
        ("bad status", dict(status="GREEN")),
        ("missing contract field", dict(payload={"work_count": 1}, required_payload=("work_count", "work_noun"))),
        ("envelope collision", dict(payload={"status": "oops"})),
        ("bad stale", dict(stale_after_s=0)),
    ]:
        try:
            emit_status(p, desk="t", pulse_job="t", stale_after_s=kw.pop("stale_after_s", 3600), **kw)
            print(f"✗ FAILED to reject: {label}"); sys.exit(1)
        except EmitContractError as e:
            print(f"✓ rejected {label}: {str(e)[:70]}")
    print("emit_status.py self-test PASSED")


# ── CLI ──────────────────────────────────────────────────────────────────────
# THE BUG THIS FIXES: a caller running
#   python3 emit_status.py --desk "$SUBSYSTEM_NAME" ...
# from a shell runner needs a real CLI — until one exists, `if __name__ == "__main__"` would
# ignore argv entirely and run the self-test above — a caller sees a green "PASSED" while NO
# tile was written at the named path. So: a BARE invocation (no args) must NOT print green (see
# _build_argparser below, no defaults that make an empty argv look like a successful no-op), and
# any contract violation must exit non-zero with the error on stderr — never exit 0. The
# self-test is preserved verbatim above, just behind an explicit --selftest flag so it stays
# reachable but is no longer the default.
def _build_argparser():
    import argparse
    ap = argparse.ArgumentParser(
        prog="emit_status.py",
        description="Write ONE validated status tile through emit_status(). "
                     "Fails loud (non-zero exit, stderr) on any contract violation — never silent.",
    )
    ap.add_argument("--selftest", action="store_true",
                     help="run the built-in self-test (writes to a temp dir) and exit; ignores all other flags")
    ap.add_argument("--out", help="output path for the tile (emit_status()'s out_path positional)")
    ap.add_argument("--desk")
    ap.add_argument("--pulse-job")
    ap.add_argument("--stale-after-s", type=int)
    ap.add_argument("--status", default="OK")
    ap.add_argument("--rc", type=int, default=0)
    ap.add_argument("--summary", default="")
    ap.add_argument("--emit-mode", default="pulse")
    ap.add_argument("--schema-version", type=int, default=2)
    ap.add_argument("--last-run", default=None)
    ap.add_argument("--required-payload", action="append", default=[],
                     help="a required payload field; repeatable (--required-payload x --required-payload y) "
                          "or comma-separated (--required-payload x,y)")
    ap.add_argument("--json", dest="json_payload", default=None,
                     help="JSON object to merge into payload= — '-' reads stdin, otherwise a file path")
    return ap


def _parse_required_payload(raw_list):
    out = []
    for item in raw_list:
        out.extend(x.strip() for x in item.split(",") if x.strip())
    return tuple(out)


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
        raise EmitContractError(f"--json payload must decode to a JSON object, got {type(obj).__name__}")
    return obj


def _main(argv):
    ap = _build_argparser()
    # bare invocation (no args at all) must NOT print green — usage + non-zero, not a silent no-op.
    if not argv:
        ap.print_usage(sys.stderr)
        print("emit_status.py: error: no arguments given — pass --selftest, or --out/--desk/--pulse-job/... "
              "to write a tile. This is the fix for the false-green self-test default.", file=sys.stderr)
        return 2

    args = ap.parse_args(argv)

    if args.selftest:
        _selftest()
        return 0

    missing = [flag for flag, val in (("--out", args.out), ("--desk", args.desk),
                                       ("--pulse-job", args.pulse_job),
                                       ("--stale-after-s", args.stale_after_s)) if val is None]
    if missing:
        print(f"emit_status.py: error: missing required flag(s): {', '.join(missing)}", file=sys.stderr)
        return 2

    try:
        payload = _load_json_payload(args.json_payload)
        emit_status(
            args.out,
            desk=args.desk,
            pulse_job=args.pulse_job,
            stale_after_s=args.stale_after_s,
            payload=payload,
            status=args.status,
            rc=args.rc,
            summary=args.summary,
            emit_mode=args.emit_mode,
            schema_version=args.schema_version,
            last_run=args.last_run,
            required_payload=_parse_required_payload(args.required_payload),
        )
    except EmitContractError as e:
        print(f"emit_status.py: EmitContractError: {e}", file=sys.stderr)
        return 1
    except (OSError, json.JSONDecodeError) as e:
        print(f"emit_status.py: error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))

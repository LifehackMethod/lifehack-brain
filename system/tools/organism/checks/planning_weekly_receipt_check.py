#!/usr/bin/env python3
# not-wired-yet: these checks stamp the planning-desk component page; the stamper wiring (component_page.py's receipt list) is step 6(a)/(b) machinery owned by other helpers, and the final stamp comes after step 7 — wired there, not here.
"""planning_weekly_receipt_check.py — a CONTENT check on the planning desk's weekly-run
receipt (CR-9 step 6c, check iv).

What it watches (plan step 6(c)): the weekly run's receipt is the staged validated picture
plus the engine's snapshot-check result. Freshness is never proof of work
(canon/status-health-proof-sop.md "Freshness is not proof of work") — this check reads the
receipt's CONTENT, never its date.

How it reads it: through ONE command Grand Central names. **Grand Central has not named
that command yet.** Until it is named, the command comes from the environment variable
`LIFEHACK_PLANNING_WEEKLY_RECEIPT_CMD` — a clearly marked PLACEHOLDER — and when it is
unset this check ERRORs, fail-closed. It never greps the engine's files itself: V2 never
parses the engine's files (plan step 6).

The contract the command must meet (marked here so Grand Central can correct it when it
names the real command): print one JSON object with
  - `staged_picture`: an object holding `validated: true` (the picture was validated,
    not merely staged), and
  - `snapshot_check`: an object holding a `result` that is not "missing".
Anything else — no command, non-JSON, missing keys, validated false, a missing snapshot
result — FAILs or ERRORs BY NAME.

Usage:
    planning_weekly_receipt_check.py [--out PATH] [--selftest]

Exit codes: 0 every probe RAN (a FAIL is a finding, not a crash) · 2 a probe ERRORed ·
4 emit_status could not be read.
"""
import argparse
import json
import os
import subprocess
import sys

CMD_ENV = "LIFEHACK_PLANNING_WEEKLY_RECEIPT_CMD"

HERE = os.path.dirname(os.path.abspath(__file__))


def probe_weekly_receipt(env=None) -> dict:
    """Run the receipt command and judge its content.
    Returns {id, result, evidence}."""
    e = dict(os.environ if env is None else env)
    cmd = (e.get(CMD_ENV) or "").strip()
    if not cmd:
        return {"id": "weekly-receipt", "result": "ERROR",
                "evidence": ("%s is unset — the receipt command has not been named yet "
                             "(placeholder; fail-closed)" % CMD_ENV)}
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120, env=e)
    if p.returncode != 0:
        return {"id": "weekly-receipt", "result": "ERROR",
                "evidence": "receipt command rc=%d: %s" % (p.returncode, " ".join((p.stderr or p.stdout).split())[:160])}
    try:
        data = json.loads(p.stdout)
    except ValueError:
        return {"id": "weekly-receipt", "result": "ERROR",
                "evidence": "receipt command did not print one JSON object"}
    if not isinstance(data, dict):
        return {"id": "weekly-receipt", "result": "ERROR",
                "evidence": "receipt JSON is %s, not an object" % type(data).__name__}
    staged = data.get("staged_picture")
    if not isinstance(staged, dict):
        return {"id": "weekly-receipt", "result": "FAIL",
                "evidence": "staged_picture missing from the receipt"}
    if staged.get("validated") is not True:
        return {"id": "weekly-receipt", "result": "FAIL",
                "evidence": "the staged picture is not validated (validated=%r)" % staged.get("validated")}
    snap = data.get("snapshot_check")
    if not isinstance(snap, dict):
        return {"id": "weekly-receipt", "result": "FAIL",
                "evidence": "snapshot_check missing from the receipt"}
    if snap.get("result") in (None, "", "missing"):
        return {"id": "weekly-receipt", "result": "FAIL",
                "evidence": "the engine's snapshot-check has no result"}
    return {"id": "weekly-receipt", "result": "PASS",
            "evidence": "staged picture validated; snapshot check: %s" % snap.get("result")}


def _selftest() -> dict:
    """Planted-fault self-test: good JSON PASSes; each planted fault (unvalidated picture,
    missing snapshot result, missing key, non-JSON, unset command) FAILs or ERRORs by name."""
    import tempfile
    results = {}

    def env_with(payload=None, cmd=None):
        e = dict(os.environ)
        e.pop(CMD_ENV, None)
        if cmd is None:
            d = tempfile.mkdtemp(prefix="pwrc-")
            script = os.path.join(d, "cmd.sh")
            body = ("echo '%s'\n" % json.dumps(payload)) if payload is not None else "exit 3\n"
            with open(script, "w", encoding="utf-8") as f:
                f.write("#!/usr/bin/env bash\n" + body)
            os.chmod(script, 0o755)
            cmd = script
        e[CMD_ENV] = cmd
        return e

    good = {"staged_picture": {"validated": True, "week": "2026-W47"},
            "snapshot_check": {"result": "ok", "checked": 12}}
    r = probe_weekly_receipt(env_with(good))
    results["good-receipt-passes"] = r["result"] == "PASS"

    bad = dict(good); bad["staged_picture"] = {"validated": False}
    r = probe_weekly_receipt(env_with(bad))
    results["unvalidated-picture-bites"] = r["result"] == "FAIL" and "validated" in r["evidence"]

    bad = dict(good); bad["snapshot_check"] = {"result": "missing"}
    r = probe_weekly_receipt(env_with(bad))
    results["missing-snapshot-result-bites"] = r["result"] == "FAIL"

    bad = {"staged_picture": {"validated": True}}
    r = probe_weekly_receipt(env_with(bad))
    results["missing-snapshot-key-bites"] = r["result"] == "FAIL"

    r = probe_weekly_receipt(env_with(None))
    results["failing-command-errors"] = r["result"] == "ERROR"

    r = probe_weekly_receipt(env_with("not json"))
    results["non-json-errors"] = r["result"] == "ERROR"

    r = probe_weekly_receipt({k: v for k, v in os.environ.items()})
    results["unset-command-errors"] = r["result"] == "ERROR"
    return results


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="planning_weekly_receipt_check.py",
        description="Named check (iv): the weekly run's receipt CONTENT, through one named command.")
    ap.add_argument("--out", default=None)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        results = _selftest()
        for probe_id, okb in sorted(results.items()):
            print("%s %s (self-test)" % (probe_id, "OK" if okb else "DID-NOT-BITE"))
        return 0 if all(results.values()) else 1

    r = probe_weekly_receipt()
    print("%s %s" % (r["id"], r["result"]) + (" " + r["evidence"] if r["evidence"] else ""))

    if r["result"] == "ERROR":
        status, tile_rc = "ERROR", 2
    elif r["result"] == "FAIL":
        status, tile_rc = "DRIFT", 1
    else:
        status, tile_rc = "OK", 0

    repo = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
    try:
        sys.path.insert(0, os.path.join(repo, "system", "tools"))
        from emit_status import emit_status  # noqa: E402
    except Exception as e:
        print("ERROR: cannot import emit_status: %s" % e, file=sys.stderr)
        return 4
    try:
        if args.out:
            out_path = args.out
        else:
            p = subprocess.run(["python3", os.path.join(repo, "shared", "brain_root.py"), "--quiet"],
                               capture_output=True, text=True)
            brain = (p.stdout or "").strip()
            if p.returncode != 0 or not brain:
                print("ERROR: brain root not resolvable; pass --out", file=sys.stderr)
                return 4
            out_path = os.path.join(brain, "status", "component-planning-desk-weekly-receipt.json")
        emit_status(out_path, desk="organism", pulse_job="planning-desk-weekly-receipt-check",
                    stale_after_s=604800, status=status, rc=tile_rc,
                    summary="weekly receipt content: %s" % r["result"],
                    emit_mode="manual",
                    payload={"component": "planning-desk", "check": "weekly-receipt",
                             "probe": r,
                             "placeholder": "receipt command not yet named by Grand Central; "
                                            "read through %s (fail-closed)" % CMD_ENV})
        print("receipt: %s" % out_path)
    except Exception as e:
        print("ERROR: could not write receipt: %s" % e, file=sys.stderr)
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())

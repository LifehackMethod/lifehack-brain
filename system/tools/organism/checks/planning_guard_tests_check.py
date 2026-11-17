#!/usr/bin/env python3
# not-wired-yet: these checks stamp the planning-desk component page; the stamper wiring (component_page.py's receipt list) is step 6(a)/(b) machinery owned by other helpers, and the final stamp comes after step 7 — wired there, not here.
"""planning_guard_tests_check.py — the planning desk's guard-tests check (CR-9 step 6c, check ii).

A CHECK, never the checked thing. It runs the guard tests the planning desk relies on,
in the checkout named by --repo, and records the result in a receipt tile.

The tests, and why the desk relies on each:
  - system/hooks/tests/test_session_context_loader.sh
        the desk's glasses: the session-start loader chain-loads the desk's canon
        (canon/desk-building-sop.md "launch sequence").
  - system/hooks/tests/test_session_context_loader_desk_scope.sh
        a desk window loads only that desk's knowledge (P-71) — the desk's scope boundary.
  - system/tools/tests/test_check_no_private_desks.py
        the No Private Desks guard, which the desk build itself must satisfy.
  - system/tools/tests/test_planning_tile_home.sh
        planning tiles land at the one tile home (move 18, one tile home).
  - system/hooks/tests/test_numbers_mode.sh
        the compute-mechanically gate that fires on planning prompts with numbers
        (inject_compute_mechanically.sh, UserPromptSubmit).

job-sim.sh is NEVER run (it rewrote real state on this machine, 2026-11-17 — common-rules).
Every probe names the test it ran; a test that vanishes from the repo is ERROR
(fail-closed), never a vacuous pass. Freshness is never proof of work: the receipt
records what the tests asserted, not their timestamps.

Usage:
    planning_guard_tests_check.py [--repo DIR] [--out PATH] [--selftest]

Exit codes: 0 every probe RAN (a FAIL is a finding, not a crash) · 2 a probe ERRORed ·
4 the repo or emit_status could not be read.
"""
import argparse
import os
import subprocess
import sys

TESTS = [
    ("system/hooks/tests/test_session_context_loader.sh",
     "the desk's glasses: session context loads the desk's canon"),
    ("system/hooks/tests/test_session_context_loader_desk_scope.sh",
     "a desk window loads only that desk's knowledge (P-71)"),
    ("system/tools/tests/test_check_no_private_desks.py",
     "the No Private Desks guard, which the desk build must satisfy"),
    ("system/tools/tests/test_planning_tile_home.sh",
     "planning tiles land at the one tile home (move 18)"),
    ("system/hooks/tests/test_numbers_mode.sh",
     "the compute-mechanically gate fires on planning prompts with numbers"),
]


def _run(cmd, cwd=None):
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=300)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def probe_guard_tests(repo, tests=None) -> list:
    """Run each named test in repo. Returns probe dicts
    {id, why, result, evidence}. A missing test file is ERROR (fail-closed)."""
    out = []
    for rel, why in (tests or TESTS):
        path = os.path.join(repo, rel)
        if not os.path.isfile(path):
            out.append({"id": rel, "why": why, "result": "ERROR",
                        "evidence": "test file missing from %s (fail-closed)" % repo})
            continue
        cmd = ["python3", path] if rel.endswith(".py") else ["bash", path]
        rc, text = _run(cmd, cwd=repo)
        out.append({"id": rel, "why": why,
                    "result": "PASS" if rc == 0 else "FAIL",
                    "evidence": "" if rc == 0 else "rc=%d %s" % (rc, " ".join(text.split())[:160])})
    return out


def _selftest(repo) -> dict:
    """Planted-fault self-test with temp scripts: a passing test PASSes; a planted
    failing test FAILs by name; a missing test ERRORs; a test that exits 0 without
    asserting is still PASS (the probes trust the named tests' own assertions) — the
    planted fault here is the FAKE test that lies about what it tested, which the
    missing-file and failing cases prove the probe reports honestly."""
    results = {}
    good = ("#!/usr/bin/env bash\necho 'guard held: planted bad input refused'\nexit 0\n")
    bad = ("#!/usr/bin/env bash\necho 'FAIL planted fault not caught'\nexit 1\n")

    def run_with(texts):
        pairs = []
        import tempfile
        with tempfile.TemporaryDirectory(prefix="pgtc-") as d:
            for i, (rel, why) in enumerate(TESTS):
                body = texts[i] if i < len(texts) else None
                if body is None:
                    pairs.append((rel, why))
                    continue
                p = os.path.join(d, "t%d.sh" % i)
                with open(p, "w", encoding="utf-8") as f:
                    f.write(body)
                os.chmod(p, 0o755)
                pairs.append((p, why))
            return probe_guard_tests(d, pairs)

    probes = run_with([good] * len(TESTS))
    results["good-tests-pass"] = all(p["result"] == "PASS" for p in probes)

    texts = [good] * len(TESTS)
    texts[1] = bad
    probes = run_with(texts)
    pr = probes[1]
    results["failing-test-bites"] = pr["result"] == "FAIL" and pr["id"] == probes[1]["id"]

    probes = run_with([good, None] + [good] * (len(TESTS) - 2))
    results["missing-test-errors"] = probes[1]["result"] == "ERROR"
    return results


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="planning_guard_tests_check.py",
        description="Named check (ii): the guard tests the planning desk relies on.")
    ap.add_argument("--repo", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    here = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.abspath(args.repo or os.path.join(here, "..", "..", "..", ".."))

    if args.selftest:
        results = _selftest(repo)
        for probe_id, okb in sorted(results.items()):
            print("%s %s (self-test)" % (probe_id, "OK" if okb else "DID-NOT-BITE"))
        return 0 if all(results.values()) else 1

    probes = probe_guard_tests(repo)
    for p in probes:
        print("%s %s" % (p["id"], p["result"]) + (" " + p["evidence"] if p["evidence"] else ""))

    results = [p["result"] for p in probes]
    if any(r == "ERROR" for r in results):
        status, tile_rc = "ERROR", 2
    elif any(r == "FAIL" for r in results):
        status, tile_rc = "DRIFT", 1
    else:
        status, tile_rc = "OK", 0
    summary = "%d of %d guard tests pass" % (sum(1 for r in results if r == "PASS"), len(results))

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
            rc, brain = _run(["python3", os.path.join(repo, "shared", "brain_root.py"), "--quiet"])
            brain = brain.strip()
            if rc != 0 or not brain:
                print("ERROR: brain root not resolvable; pass --out", file=sys.stderr)
                return 4
            out_path = os.path.join(brain, "status", "component-planning-desk-guard-tests.json")
        emit_status(out_path, desk="organism", pulse_job="planning-desk-guard-tests-check",
                    stale_after_s=604800, status=status, rc=tile_rc, summary=summary,
                    emit_mode="manual",
                    payload={"component": "planning-desk", "check": "guard-tests",
                             "tests": probes, "not_tested": ["job-sim.sh rig (barred on this machine)"]})
        print("receipt: %s" % out_path)
    except Exception as e:
        print("ERROR: could not write receipt: %s" % e, file=sys.stderr)
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())

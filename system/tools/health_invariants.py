#!/usr/bin/env python3
"""health_invariants — the deterministic ground-truth layer of the Health Authority.

THE HEALTH AUTHORITY = system-health.py (the missed-run SWEEPER) + THIS (deterministic
system-INTEGRITY invariants). The sweeper watches that every scheduled job RAN; this asserts the
SUBSTRATE underneath is intact — hooks present, guards untampered, the clone fresh, and every
enabled job actually watched (no job silently un-watched).

DOCTRINE (carried over from the donor unchanged): "assume broken until proven healthy." This module
never proposes or applies a fix — it detects and feeds need_attention. Invoked by system-health.py,
never scheduled on its own.

⛔ HEADER RULE, kept from the donor: after the founding set below, ADDING A CHECK REQUIRES DELETING
ONE. Do not grow this list unboundedly.

PORTED (2026-08-14) from claudeops-config's system/tools/health_invariants.py. ONE invariant was CUT
rather than translated: the donor's Invariant 4 asked "are BOTH of my two machines reporting a fresh
heartbeat" — the exact masking-by-omission bug it existed to catch (a second machine silently going
dark while the dashboard stayed all-green) cannot happen here, because there is exactly one machine
(docs/data-layout.md: "the two-machine plane is not part of this system"). Per this module's own
header rule, that is DELETED, not repurposed into a same-machine echo of a check two OTHER layers
already make (system-health.py's own per-job LATE detection, and health-deadman-check.sh watching
Pulse's overall silence) — padding to a round number of checks is not the discipline this rule asks
for. The founding set is now four: hooks present, guards untampered, clone fresh, coverage complete.

Everything else — the append-only-log-forking lesson that made this write through emit_finding.py
instead of a second hand-rolled append, the fail-safe-defaults-to-BROKEN posture — ships unchanged,
because `emit_finding.py` already exists in this repo (system/tools/emit_finding.py) with the exact
per-(producer) shard contract this module was already written to use.

FAIL-SAFE: every invariant defaults to BROKEN on its own error (an invariant that can't run is a RED,
never a silent pass) — silence is treated as alarm, not health.
"""
import glob
import os
import subprocess
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from emit_finding import emit_finding, FindingContractError   # noqa: E402

GUARD_GLOB = "system/hooks/guard_*.sh"
# The critical-hook allowlist, matched against THIS repo's real files (verified this session —
# `guard_calendar_writes.sh` is this repo's Google-write guard; the donor's equivalent file was named
# `block_primary_calendar.sh` and does not exist under that name here).
CRITICAL_HOOKS = ("guard_calendar_writes.sh", "ingest_gate_enforce.sh",
                  "guard_write_paths.sh", "guard_egress.sh")
CLONE_AHEAD_WARN = 8              # > this many unpushed commits -> worth a nudge to push
FETCH_STALE_S = 3 * 86400         # origin not fetched in 3 days -> can't know if we're behind


def _entry(job, ok, why, severity=None):
    """Shape-compatible with system-health.assess() so it renders + notifies through the same path."""
    sev = severity or ("ok" if ok else "warning")
    return {"job": job, "group": "integrity", "state": "OK" if ok else "BROKEN",
            "severity": "ok" if ok else sev, "attention": not ok, "why": "" if ok else why,
            "last_run": None, "age_h": None, "next_due": None, "_ok": ok}


def _git(code_root, *args):
    return subprocess.run(["git", "-C", code_root, *args], capture_output=True, text=True, timeout=10,
                          env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"})


# ── INVARIANT 1 — hooks present + non-empty ─────────────────────────────────────────────────────
def inv_hooks_present(code_root):
    try:
        paths = glob.glob(os.path.join(code_root, GUARD_GLOB))
        for h in CRITICAL_HOOKS:
            paths.append(os.path.join(code_root, "system/hooks", h))
        missing = [os.path.basename(p) for p in paths
                   if not (os.path.isfile(p) and os.path.getsize(p) > 0)]
        if missing:
            return _entry("integrity:hooks", False,
                          f"{len(missing)} guard hook(s) missing/empty: {', '.join(sorted(set(missing)))}",
                          severity="error")
        return _entry("integrity:hooks", True, "")
    except Exception as e:
        return _entry("integrity:hooks", False, f"hook check errored: {e}", severity="error")


# ── INVARIANT 2 — guards untampered: every guard hook matches its git-HEAD committed version ─────
# Catches a sneaky LOCAL disable (a guard edited but not committed). Self-clears on a legitimate
# commit, so it does NOT fire on normal committed development.
def inv_guard_integrity(code_root):
    try:
        if not os.path.isdir(os.path.join(code_root, ".git")):
            return _entry("integrity:guards", False, "clone has no .git — cannot verify guard integrity",
                          severity="error")
        r = _git(code_root, "status", "--porcelain", "--", "system/hooks/")
        dirty = [ln[3:] for ln in r.stdout.splitlines() if ln.strip()]
        guard_dirty = [p for p in dirty if "/guard_" in p or any(c in p for c in CRITICAL_HOOKS)]
        if guard_dirty:
            return _entry("integrity:guards", False,
                          f"{len(guard_dirty)} guard hook(s) modified but NOT committed — verify intentional: "
                          f"{', '.join(os.path.basename(p) for p in guard_dirty[:5])}", severity="error")
        return _entry("integrity:guards", True, "")
    except Exception as e:
        return _entry("integrity:guards", False, f"guard integrity check errored: {e}", severity="error")


# ── INVARIANT 3 — clone freshness: unpushed commits + origin not fetched lately ──────────────────
def inv_clone_freshness(code_root):
    try:
        if not os.path.isdir(os.path.join(code_root, ".git")):
            return _entry("integrity:clone", False, "clone has no .git", severity="error")
        problems = []
        ahead = _git(code_root, "rev-list", "--count", "@{u}..HEAD")
        if ahead.returncode == 0 and ahead.stdout.strip().isdigit():
            n = int(ahead.stdout.strip())
            if n > CLONE_AHEAD_WARN:
                problems.append(f"{n} unpushed commit(s) — push needed")
        behind = _git(code_root, "rev-list", "--count", "HEAD..@{u}")
        if behind.returncode == 0 and behind.stdout.strip().isdigit():
            nb = int(behind.stdout.strip())
            if nb > 0:
                problems.append(f"{nb} commit(s) behind origin — pull needed")
        fh = os.path.join(code_root, ".git", "FETCH_HEAD")
        if os.path.isfile(fh):
            age = time.time() - os.path.getmtime(fh)
            if age > FETCH_STALE_S:
                problems.append(f"origin not fetched in {int(age // 86400)}d — freshness unknown")
        if problems:
            return _entry("integrity:clone", False, "; ".join(problems))
        return _entry("integrity:clone", True, "")
    except Exception as e:
        return _entry("integrity:clone", False, f"clone freshness check errored: {e}", severity="error")


# ── INVARIANT 4 (was 5 in the donor) — coverage self-check: every enabled Pulse job is actually
#    ASSESSED by the sweeper. A job in the manifest that the sweeper never looked at is
#    masking-by-omission. FAIL LOUD. ──────────────────────────────────────────────────────────────
def inv_coverage(code_root, assessed_jobs):
    try:
        if assessed_jobs is None:
            return _entry("integrity:coverage", True, "")  # standalone run — sweeper didn't pass its set
        config = os.path.join(code_root, "system", "pulse-config.md")
        enabled, in_block = set(), False
        for line in open(config):
            s = line.strip()
            if s == "```jobs":
                in_block = True; continue
            if in_block and s == "```":
                break
            if not in_block or not s or s.startswith("#"):
                continue
            parts = [p.strip() for p in s.split("|")]
            if len(parts) >= 3 and parts[1] == "yes":
                enabled.add(parts[0])
        uncovered = sorted(enabled - set(assessed_jobs))
        if uncovered:
            return _entry("integrity:coverage", False,
                          f"{len(uncovered)} enabled job(s) NOT assessed by the sweeper (masking-by-omission): "
                          f"{', '.join(uncovered)}", severity="error")
        return _entry("integrity:coverage", True, "")
    except Exception as e:
        return _entry("integrity:coverage", False, f"coverage check errored: {e}", severity="error")


def _emit_findings(checks, scanned_n):
    """ONE Hospital finding PER INVARIANT — `labels={"job": "health-invariants", "invariant": <name>}`
    is the finding's identity, so each invariant's own recurrence is independently trackable."""
    for c in checks:
        try:
            invariant = c["job"].split(":", 1)[1] if ":" in c["job"] else c["job"]
            labels = {"job": "health-invariants", "invariant": invariant}
            if c["_ok"]:
                status = "OK"
            elif c.get("severity") == "error":
                status = "ERROR"
            else:
                status = "NEEDS_REVIEW"
            emit_finding(
                producer="health_invariants",
                status=status,
                scanned_n=scanned_n,
                labels=labels,
                summary=c["why"] or f"{invariant}: OK",
                payload={"state": c["state"], "group": c["group"], "severity": c["severity"]},
                rc=0 if c["_ok"] else 1,
            )
        except FindingContractError as e:
            sys.stderr.write(f"[health_invariants] emit_finding failed for {c.get('job')}: {e}\n")
        except Exception as e:
            sys.stderr.write(f"[health_invariants] emit_finding failed for {c.get('job')}: {e}\n")


def run(notes_root, code_root, now=None, assessed_jobs=None):
    """Run all founding invariants, emit ONE Hospital finding per invariant, return attention-shaped
    dicts (system-health.py folds these into its own results list). `notes_root` is accepted for
    signature-compatibility with the donor (and in case a future invariant needs it) but the four
    invariants below only ever touch `code_root` — none of them read notes content."""
    now = int(now or time.time())
    checks = [
        inv_hooks_present(code_root),
        inv_guard_integrity(code_root),
        inv_clone_freshness(code_root),
        inv_coverage(code_root, assessed_jobs),
    ]
    scanned_n = len(assessed_jobs) if assessed_jobs is not None else len(checks)
    _emit_findings(checks, scanned_n)
    for c in checks:
        c.pop("_ok", None)
    return checks


if __name__ == "__main__":
    _here = os.path.dirname(os.path.abspath(__file__))
    _code_root = os.path.abspath(os.path.join(_here, "..", ".."))
    sys.path.insert(0, os.path.join(_code_root, "shared"))
    from brain_root import resolve_brain_root
    _src, _root = resolve_brain_root()
    res = run(_root, _code_root, assessed_jobs=None)
    for c in res:
        mark = "OK " if c["state"] == "OK" else "!! "
        print(f"{mark}{c['job']:22} {c['why']}")
    bad = [c for c in res if c["attention"]]
    print(f"\n{len(res) - len(bad)}/{len(res)} invariants pass" + (f" - {len(bad)} BROKEN" if bad else " - all green"))

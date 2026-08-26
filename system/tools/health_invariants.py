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

CLONE_AHEAD_WARN = 8              # > this many unpushed commits -> worth a nudge to push
FETCH_STALE_S = 3 * 86400         # origin not fetched in 3 days -> can't know if we're behind


# ── COVERAGE SET — replaces the old GUARD_GLOB + hand-named CRITICAL_HOOKS allowlist ─────────────
# ⚠ MEASURED 2026-08-23: the allowlist (`guard_calendar_writes.sh`, `ingest_gate_enforce.sh`,
# `guard_write_paths.sh`, `guard_egress.sh`) added exactly ONE file the `guard_*.sh` glob didn't
# already have (`ingest_gate_enforce.sh` — the other three all match `guard_*.sh`), while 54 tracked,
# non-test, non-lib hook files existed and only 27 had liveness coverage. The 27 uncovered included
# `enforce_egress_allowlist.py/.sh`, `enforce_multiphase_contract.sh`, `enforce_skill_frontmatter.sh`
# — security- and contract-relevant by name — plus 16 `inject_*`/`session_*`/`validate_*`/etc. hooks
# that ARE wired into the harness (confirmed via registrations) but match no naming convention at
# all. A hand-kept list is exactly the thing that goes stale; this is the incident that going-stale
# produces.
# RULING: coverage is now DERIVED, never hand-kept, from two sources ORed together:
#   1. filename convention (`guard_*.sh`, `enforce_*.sh`, `enforce_*.py`) — covers a gate by its
#      self-describing name even BEFORE it's wired in (e.g. a guard mid-build, deliberately staged
#      unregistered — checked this session: `guard_mcp_connector_shape.sh`'s own test file says so
#      in as many words). Filename alone is not enough: `session_context_loader.sh`,
#      `inject_work_altitude.sh`, `pm_persist.sh`, `validate_on_write.sh` and 12 others are real,
#      harness-invoked controls with names that match no gate-ish prefix.
#   2. what is ACTUALLY REGISTERED — read straight from the wiring, not inferred from a name. A
#      registered hook is a live control BY DEFINITION regardless of its filename, so this closes
#      exactly the gap (1) cannot: `inject_*`, `enforce_*.py` siblings a `.sh` wrapper `exec`s into,
#      `session_*`, `validate_*`, `plan_flag.sh`, `pm_persist.sh`, `rating_capture.sh`, etc. A hook
#      on disk that NOTHING registers is not a live control — reporting its silence as broken would
#      be a false positive, so filename-only conventions stay in the union as the pre-registration
#      floor, not as a substitute for reading the wiring.
# CONSIDERED AND REJECTED: registration-only (drop the filename convention entirely). Rejected
# because it would silently stop watching a guard the moment someone stages it unregistered for
# review — exactly the `guard_mcp_connector_shape.sh` case — which is backwards: a soon-to-be-live
# gate is when you most want eyes on whether it shipped executable.
# TWO REGISTRATION SHAPES EXIST across real installs (both checked this session, both repos this
# invariant runs in): this repo's `system/hooks/registrations.json` (untracked/private — the current
# source of truth here), and a `hooks` block living directly inside `.claude/settings.json` (the
# shape an older/differently-bootstrapped clone carries — confirmed live in the second repo this
# invariant runs against, which has no `registrations.json` at all). `_registered_hook_basenames`
# tries both, in that order, and returns None (not an empty set) if neither is present or parses —
# an ABSENT registration source degrades to the filename-convention floor, it never reports a false
# "uncovered" for every hook in the repo.
# NOT hand-maintained: nothing here lists a hook by name. Adding a `guard_*`/`enforce_*` file, or
# wiring anything at all into the harness, is by itself enough to be covered — nothing else to update.
def _registered_hook_basenames(code_root):
    """Read the ACTUAL wiring, not a naming guess. Tries `system/hooks/registrations.json` first,
    then a `hooks` block inside `.claude/settings.json`; both list hook commands as
    `bash ".../some_hook.sh"` strings, so the same regex pulls the basename out of either shape.
    Returns a set (possibly empty, if the file parses but names nothing) on success, or None if
    neither file exists or parses — callers must treat None as "could not determine" and fall back
    to the filename-convention floor, never as "zero hooks registered"."""
    import json
    import re
    for rel in ("system/hooks/registrations.json", ".claude/settings.json"):
        path = os.path.join(code_root, rel)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        hooks = data.get("hooks") if isinstance(data, dict) else None
        if not isinstance(hooks, dict) or not hooks:
            continue
        found = set()

        def _walk(o):
            if isinstance(o, dict):
                for v in o.values():
                    _walk(v)
            elif isinstance(o, list):
                for i in o:
                    _walk(i)
            elif isinstance(o, str):
                found.update(re.findall(r"([A-Za-z0-9_]+\.(?:sh|py))", o))

        _walk(hooks)
        if found:
            return found
    return None


def _coverage_basenames(code_root):
    """Union of the filename-convention floor and whatever is actually registered (see module
    header for the full reasoning). Used by BOTH Invariant 1 (present + live) and Invariant 2
    (untampered) so the two never drift apart on what counts as a control worth watching."""
    convention = set()
    for pattern in ("guard_*.sh", "enforce_*.sh", "enforce_*.py"):
        for p in glob.glob(os.path.join(code_root, "system/hooks", pattern)):
            convention.add(os.path.basename(p))
    registered = _registered_hook_basenames(code_root)
    return convention | (registered or set())


def _entry(job, ok, why, severity=None):
    """Shape-compatible with system-health.assess() so it renders + notifies through the same path."""
    sev = severity or ("ok" if ok else "warning")
    return {"job": job, "group": "integrity", "state": "OK" if ok else "BROKEN",
            "severity": "ok" if ok else sev, "attention": not ok, "why": "" if ok else why,
            "last_run": None, "age_h": None, "next_due": None, "_ok": ok}


def _git(code_root, *args):
    return subprocess.run(["git", "-C", code_root, *args], capture_output=True, text=True, timeout=10,
                          env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"})


# ── INVARIANT 1 — hooks present AND LIVE (executable) ───────────────────────────────────────────
# ⚠ CORRECTED (2026-08-23): this used to test existence + size>0 ONLY, on the premise that hooks
# ship chmod 444 and are bash-invoked, so an executable bit was never the liveness signal. That
# premise is FALSE for this repo — system/hook-contract.md is explicit that hook scripts here are
# "ordinary tracked files, mode 755" and warns AGAINST chmod 444 ("friction with no guarantee behind
# it"). Under the old test, a hook shipped git-mode 100644 (non-executable, therefore dead — this is
# exactly how a hook can ship broken to a fresh student clone even though it ran fine on the
# author's own machine, where a locally-chmod'd copy can sit on top of a 100644 commit) still passed
# clean: the file exists and has bytes. Measured 2026-08-23: nine hook files were found at git mode
# 100644, including a registered security guard, and every one of them would have passed this
# invariant. The check now tests the actual liveness signal on BOTH axes a hook can go dead on:
#   1. the ON-DISK executable bit (os.access X_OK) — what actually runs THIS machine, right now.
#   2. the GIT-TRACKED mode (`git ls-files -s`), when available — what a FRESH clone gets, which is
#      the axis the 100644 defect actually shipped on. A file can be locally chmod +x while
#      committed 100644, which passes (1) and hides (2); checking only the on-disk bit would still
#      miss that shipped-broken failure mode.
# ABSENT-SUBJECT RULE: "missing", "present but not executable", and "could not determine" are kept
# as three DISTINCT outcomes below (separate buckets in `why`), never folded into one "broken" blob —
# a reader has to be able to tell "the file isn't there" from "it's there but dead" from "the checker
# itself couldn't tell" (e.g. no git, git command failed/timed out, or the file isn't git-tracked).
def inv_hooks_present(code_root):
    try:
        paths = {base: os.path.join(code_root, "system/hooks", base)
                 for base in _coverage_basenames(code_root)}

        missing, empty, not_executable, undetermined = [], [], [], []

        # Git-tracked mode, when determinable — the axis a fresh clone actually inherits.
        git_modes = None  # None = could not determine at all; {} = determined, nothing tracked
        if os.path.isdir(os.path.join(code_root, ".git")):
            r = _git(code_root, "ls-files", "-s", "--", "system/hooks/")
            if r.returncode == 0:
                git_modes = {}
                for line in r.stdout.splitlines():
                    meta, sep, relpath = line.partition("\t")
                    if sep and meta.split():
                        git_modes[os.path.basename(relpath)] = meta.split()[0]

        for base in sorted(paths):
            p = paths[base]
            if not os.path.isfile(p):
                missing.append(base)
                continue
            if os.path.getsize(p) == 0:
                empty.append(base)
                continue
            if not os.access(p, os.X_OK):
                not_executable.append(f"{base} (on-disk, not chmod +x)")
                continue
            if git_modes is not None:
                mode = git_modes.get(base)
                if mode is None:
                    undetermined.append(f"{base} (not found via git ls-files — untracked?)")
                elif mode != "100755":
                    not_executable.append(f"{base} (committed git mode {mode}, not 100755 — dead on a fresh clone)")
            else:
                undetermined.append(f"{base} (no .git or git ls-files failed — could not check committed mode)")

        problems = []
        if missing:
            problems.append(f"{len(missing)} missing: {', '.join(missing)}")
        if empty:
            problems.append(f"{len(empty)} empty: {', '.join(empty)}")
        if not_executable:
            problems.append(f"{len(not_executable)} present but NOT executable/dead: {', '.join(not_executable)}")
        if undetermined:
            problems.append(f"{len(undetermined)} could not determine liveness: {', '.join(undetermined)}")

        if problems:
            return _entry("integrity:hooks", False, "; ".join(problems), severity="error")
        return _entry("integrity:hooks", True, "")
    except Exception as e:
        return _entry("integrity:hooks", False, f"hook check errored (could not determine): {e}", severity="error")


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
        covered = _coverage_basenames(code_root)
        guard_dirty = [p for p in dirty if os.path.basename(p) in covered]
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
        for line in open(config, encoding="utf-8"):
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

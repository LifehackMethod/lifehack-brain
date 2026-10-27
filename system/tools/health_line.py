#!/usr/bin/env python3
"""
health_line.py — the ONE-LINE job-health line printed first in every session.

# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: every scheduled job runs inside system/tools/job-run.sh, which keeps LOCAL state in
#      ~/.config/lifehack/state/jobs/<job>/ (last-run, last-success, launch.err, errors/). Nothing
#      read that state back: a job that never ran, or stopped running, looked identical to a healthy
#      one. This tool reads it at session start and says so, in one line, whether or not anyone looks.
# CONTRACT: prints EXACTLY ONE line, worst state first:
#      0. (5.4) an email label is PAUSED by the sentinel (a REAL-ATTACK) -> "paused: <label>[, <label>]". A security stop
#         outranks every plant state: it is read from the sentinel pause file (env SENTINEL_PAUSE_FILE, else
#         ~/.config/lifehack/sentinel-paused-sources), lines `email:<label>` only (other sources never show here).
#      1. any job has a non-empty launch.err -> "jobs cannot find the code — open any desk once to repair"
#      2. an ENABLED job with no last-run    -> "never ran: a, b"   (never reported as OK: dead end F2)
#      3. last-success missing or at least 2 x period old -> "<n> overdue: job (9h), ..."
#      4. last-run shows rc=75               -> "stood down: job (<reason from last-run>)"
#      5. otherwise                          -> "jobs: <n> OK"
#      Never raises, never exits nonzero. On an internal error: "job health: could not read (<reason>)".
#      Pure stdlib, local files only (no Drive, no subprocess): finishes in a few ms.
# INPUTS: ENABLED rows of the ```jobs block in system/pulse-config.md (name | enabled | interval | outcome | check | model | budget | source | cmd;
#      '#' = comment; parsed the same way job-run.sh's awk does). Period = 3rd column, seconds.
#      Overrides (for fixtures): argv[1]=state dir, argv[2]=manifest; or env LIFEHACK_JOBS_STATE_DIR /
#      LIFEHACK_JOBS_MANIFEST. Defaults: ~/.config/lifehack/state/jobs and <script>/../pulse-config.md.
# UPDATED: 2026-10-27 (task 2.1) — replaced the old Drive findings/ledger banner (Hospital findings,
#      recommendations, gauge, fault ledger; ~900 lines, recoverable from git history) with this
#      local-job-state line. The hook no longer passes a ledger argument.
"""
from __future__ import annotations

import os
import sys
import time

CODE_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")


def _enabled_jobs(manifest: str) -> list:
    """[(name, period_seconds)] for rows with enabled == yes in the ```jobs block."""
    jobs, inb = [], False
    with open(manifest, encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if line.strip() == "```jobs":
                inb = True
                continue
            if inb and line.strip() == "```":
                inb = False
                continue
            if not inb or line.lstrip().startswith("#") or "|" not in line:
                continue
            f = [c.strip() for c in line.split("|")]
            if len(f) < 3 or not f[0] or f[1] != "yes":
                continue
            if not f[2].isdigit():
                continue
            jobs.append((f[0], int(f[2])))
    return jobs


def _age(s: float) -> str:
    s = max(0, int(s))
    if s < 3600:
        return f"{s // 60}m"
    if s < 48 * 3600:
        return f"{s // 3600}h"
    return f"{s // 86400}d"


def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read().strip()
    except OSError:
        return ""


def compute(state_dir: str, manifest: str, now: float | None = None) -> str:
    now = time.time() if now is None else now
    jobs = _enabled_jobs(manifest)

    # 0) (5.4) a paused email label: the loudest state there is
    pf = os.environ.get("SENTINEL_PAUSE_FILE") or os.path.join(os.path.expanduser("~"), ".config", "lifehack",
                                                                "sentinel-paused-sources")
    try:
        with open(pf, encoding="utf-8", errors="replace") as fh:
            paused = sorted({ln.strip()[len("email:"):] for ln in fh if ln.strip().startswith("email:")} - {""})
    except OSError:
        paused = []
    if paused:
        return "paused: " + ", ".join(paused)

    # 1) any launch.err anywhere under the state dir (enabled or not)
    try:
        names = sorted(os.listdir(state_dir))
    except OSError:
        names = []
    for n in names:
        try:
            if os.path.getsize(os.path.join(state_dir, n, "launch.err")) > 0:
                return "jobs cannot find the code — open any desk once to repair"
        except OSError:
            pass

    # 2) enabled job that has never written last-run
    never = [j for j, _ in jobs if not os.path.isfile(os.path.join(state_dir, j, "last-run"))]
    if never:
        return "never ran: " + ", ".join(never)

    # 3) overdue: last-success missing or at least 2 x period old (2.5d: the same instant job-run.sh texts)
    overdue = []
    for j, period in jobs:
        try:
            age = now - os.path.getmtime(os.path.join(state_dir, j, "last-success"))
        except OSError:
            overdue.append(f"{j} (never succeeded)")
            continue
        if age >= 2 * period:
            overdue.append(f"{j} ({_age(age)})")
    if overdue:
        return f"{len(overdue)} overdue: " + ", ".join(overdue)

    # 4) stood down (rc=75)
    for j, _ in jobs:
        lr = _read(os.path.join(state_dir, j, "last-run"))
        parts = lr.split(None, 2)
        if len(parts) >= 2 and parts[1] == "rc=75":
            # 5.3: the reason follows "calls=N secs=S model=T" (older lines have none of the three)
            import re as _re
            reason = _re.sub(r"^(?:(?:calls|secs|model)=\S+\s+)+", "", parts[2]) if len(parts) > 2 else "no reason recorded"
            reason = reason or "no reason recorded"
            return f"stood down: {j} ({reason})"

    # 5) all good
    return f"jobs: {len(jobs)} OK"


def main() -> int:
    try:
        # TEST-ONLY seams (self-monitoring 2.0), all inert when unset: LIFEHACK_STATE_DIR (root; jobs live in
        # <root>/jobs), LIFEHACK_JOBS_FILE (manifest), LIFEHACK_FAKE_NOW (epoch seconds, the clock).
        fake = os.environ.get("LIFEHACK_FAKE_NOW", "")
        now = float(fake) if fake.isdigit() else None
        sroot = os.environ.get("LIFEHACK_STATE_DIR")
        state = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("LIFEHACK_JOBS_STATE_DIR")
                 or (os.path.join(sroot, "jobs") if sroot else None)
                 or os.path.join(os.path.expanduser("~"), ".config", "lifehack", "state", "jobs"))
        manifest = (sys.argv[2] if len(sys.argv) > 2 else os.environ.get("LIFEHACK_JOBS_MANIFEST")
                    or os.environ.get("LIFEHACK_JOBS_FILE")
                    or os.path.join(CODE_ROOT, "system", "pulse-config.md"))
        line = compute(state, manifest, now)
    except BaseException as e:  # fail-soft: never raise, never non-zero
        line = f"job health: could not read ({type(e).__name__}: {e})"
    line = " ".join(str(line).split())
    try:
        print(line)
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BaseException:
        sys.exit(0)

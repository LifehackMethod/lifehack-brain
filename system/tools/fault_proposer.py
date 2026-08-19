#!/usr/bin/env python3
"""
fault_proposer.py — the FIRST machine reader of this repo's failure signals (PORTED
2026-08-14 from claudeops-config's system/tools/fault_proposer.py, organism audit T3.3).

⚖ SUBSYSTEM: EFFICIENCY, not Hospital. HOSPITAL detects and ranks. EFFICIENCY reads across
and recommends. THE HUMAN acts. This module grades an altitude, cites evidence, and proposes
"stop fixing X and fix what keeps breaking it" — recommending is not detecting, so it is not
Hospital's job even though it reads Hospital's ledger.

WHAT THIS IS FOR
────────────────
Measured on the donor system across every detector it ran: every failure signal terminated
at a human eyeball — a phone buzz or a dashboard render. Nothing read a failure and then
decided anything. The detectors were never the gap. The wire from detector to JUDGMENT was.

WHAT IT DOES NOT DO — AND WHY THAT IS THE DESIGN, NOT A LIMITATION
────────────────────────────────────────────────────────────────
It PROPOSES. It never applies, never re-runs a job, never edits a file. That is not
timidity, it is this system's whole thesis: the human gate is the product. It is also the
direct lesson of the incident that motivated this file on the donor system: a mechanism that
automated RECOVERY could not tell a FAULT from a DECISION, so it resurrected a job a human
had deliberately parked. A layer that fixes things unasked rebuilds that failure on purpose.

THE ONE HARD RULE: THE ALTITUDE IS DERIVED, NEVER ASSERTED
───────────────────────────────────────────────────────────
"Fix this instance" and "fix this subsystem" are the same sentence until you know whether
it has happened before. So the altitude is computed from recurrence data and the evidence
that chose it is quoted INSIDE the proposal. **A proposal that cannot cite its evidence
REFUSES to emit** — an uncited proposal is an opinion wearing a machine's authority, which
is the exact disease this whole audit exists to kill.

    INSTANCE  — first occurrence. Something broke. Fix the thing.
    SUBSYSTEM — it keeps happening. The component is wrong, not the moment.
    ORGANISM  — several DIFFERENT faults share a shape. The model is wrong.

Reads: `~/.config/lifehack/faults.json` (live) + `incidents.jsonl` (history) via
`fault_ledger.py`. Writes: NOTHING. Prints a proposal, or prints a refusal.

⚠ SHIP-DISABLED RECOMMENDATION (see the "FAULT vs DECISION" block below, and this port's own
task list): this module CANNOT TELL A FAULT FROM A DECISION on its own — the DECISION gate
below only catches a park that was written to `PARK_FILE` by a human tool (`pulse-park.sh` on
the donor system, not ported here). ⚠ CORRECTED 2026-08-15 (T9.7d stale-claim sweep): this
paragraph used to assert twice over that the repo had nothing scheduling anything — once up
here, and again in a closing line that called this module "shipped, disabled by absence of a
scheduler... nothing in this repo has a cron slot yet." Every part of that is FALSE and the two
halves contradicted each other after a partial earlier fix. What is actually true:
`system/tools/pulse.sh` is the live daemon, `system/tools/install-schedulers.sh` installs its
entry (cron and Windows Task Scheduler), and `fault-proposer-run.sh` — which calls THIS module —
has a real `fault-proposer` row (86400s) in `system/pulse-config.md`. So this module DOES run on
a cadence.
What was never ported is specifically `pulse-park.sh`, the human tool that writes `PARK_FILE`.
That is the real and narrower limitation: with nobody able to park anything, the DECISION gate
below is never fed, so this module cannot distinguish a deliberate pause from a genuine fault.
Its recommendation output should be read with that caveat — it is unfed, not unscheduled.

Compatible with `/usr/bin/python3` (3.9) — no `X | None` union annotations, stdlib only.
"""
from __future__ import annotations   # keep annotations lazy for 3.9 compatibility

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fault_ledger as FL   # noqa: E402

# ── THE THRESHOLDS. Each is a JUDGMENT, so each is named, defended, and adjustable. ──
#
# Not tuned to look good — chosen so the boundary is defensible out loud:

# 2 is deliberately NOT the subsystem bar. Twice can be coincidence; a flaky network, a
# machine that slept. Three occurrences is the smallest number that is a PATTERN rather
# than a repeat, and the cost of being wrong here is asymmetric: calling a coincidence a
# "subsystem defect" sends a human to rebuild something that was fine.
SUBSYSTEM_AFTER = 3

# For ORGANISM we need DIFFERENT faults, not one loud one — a single job failing 50 times
# is still a subsystem problem. Two distinct recurring keys is the floor at which "these
# share a cause" becomes a question worth a human's time.
ORGANISM_DISTINCT_KEYS = 2

# ── THE ORGANISM COHORT WINDOW. ────────────────────────────────────────────────────────
#
# ⛔ THE DEFECT THIS CLOSES, MEASURED ON THE DONOR SYSTEM: the cohort behind ORGANISM was
# computed over ALL HISTORY. `fault_ledger.incidents()` accepts job/state/fingerprint filters
# and NO time filter of any kind, so `recurrence_all()` counted every key that had EVER
# closed SUBSYSTEM_AFTER times, back to the beginning of the ledger. Nothing aged out.
#
# ⇒ IT WAS A RATCHET. ORGANISM fires at >= ORGANISM_DISTINCT_KEYS (2) such keys; once you
# cross 2 you are across FOREVER, so ORGANISM was satisfied permanently and — because
# choose_altitude() checks it FIRST, as the claim that survives the others being true —
# INSTANCE and SUBSYSTEM became structurally unreachable. **A verdict that cannot turn off
# carries no information.**
#
# ⚖ WHY A WINDOW AND NOT A RE-ORDER. Checking the widest claim first is CORRECT and is the
# whole point: if five unrelated things are failing for one shared reason, "go fix
# ingest" is the wrong answer even though it is accurate. Re-ordering would throw that
# insight away to dodge a data bug. The bug was never the ORDER — it was that the cohort
# described the ledger's ENTIRE LIFE STORY rather than the present. Windowing keeps ORGANISM
# meaning exactly what it was built to mean, and lets it switch OFF when the pattern
# genuinely stops.
#
# WHY 30 DAYS. A key must close SUBSYSTEM_AFTER (3) times INSIDE the window to count. Three
# occurrences of a WEEKLY job span ~21 days, so a 14-day window would have made every weekly
# job structurally incapable of ever joining the cohort — the same class of silent blindness
# this whole subsystem exists to abolish, reintroduced by a threshold chosen for tidiness.
# 30 days is the smallest round window that comfortably contains three weekly occurrences.
# ⚠ STATED LIMITATION, not an oversight: a MONTHLY job can never reach 3 closes in 30 days,
# so it cannot contribute to an ORGANISM cohort. That is judged acceptable — three monthly
# failures is a quarter of signal, and a quarter-long pattern is a human's call, not a
# daily proposer's.
ORGANISM_COHORT_WINDOW_S = 30 * 86400

# ── THE ALTITUDE VOCABULARY, EXPORTED. ─────────────────────────────────────────────────
# `emit_recommendation.py` needs this set; it exists only as string literals scattered
# through choose_altitude()'s branches and propose()'s DECISION gate otherwise. Copied
# rather than invented, and flagged here as the one definition — if a fifth altitude is
# ever added, add it here (emit_recommendation.py validates against it by import).
VALID_ALTITUDE = frozenset({"INSTANCE", "SUBSYSTEM", "ORGANISM", "DECISION"})


def _fmt_age(seconds: float) -> str:
    if seconds < 3600:
        return f"{int(seconds // 60)}m"
    if seconds < 86400:
        return f"{int(seconds // 3600)}h"
    return f"{seconds / 86400:.1f}d"


def choose_altitude(rec: dict, cohort: dict) -> tuple:
    """Return (altitude, [evidence lines]) — or (None, []) if nothing can be cited.

    `rec`    = this fault's recurrence record
    `cohort` = recurrence_all(), needed because ORGANISM is only visible ACROSS keys.
    Returning (None, []) is a first-class outcome, not an error path: no evidence, no
    proposal.
    """
    n = rec.get("occurrences", 0)
    ev = []

    # ORGANISM — checked FIRST, because it is the claim that survives the others being
    # true. If several distinct faults are all recurring, "fix this one component" is
    # the wrong advice even when it is locally correct.
    recurring = {k: r for k, r in cohort.items() if r.get("occurrences", 0) >= SUBSYSTEM_AFTER}
    if len(recurring) >= ORGANISM_DISTINCT_KEYS:
        ev.append(f"{len(recurring)} DISTINCT fault keys have each recurred "
                  f">={SUBSYSTEM_AFTER}x: {', '.join(sorted(recurring))}")
        ev.append("a pattern across different faults points at the model, not at any one component")
        return "ORGANISM", ev

    if n >= SUBSYSTEM_AFTER:
        ev.append(f"this exact fault has closed {n}x (threshold for SUBSYSTEM is {SUBSYSTEM_AFTER})")
        mi = rec.get("mean_interval_s")
        if mi:
            ev.append(f"mean interval between occurrences: {_fmt_age(mi)} — it recurs on a rhythm")
        td = rec.get("total_downtime_s", 0)
        if td:
            ev.append(f"cumulative downtime across occurrences: {_fmt_age(td)}")
        return "SUBSYSTEM", ev

    if n == 0:
        ev.append("no closed occurrences on record — this is the FIRST time this fault has been seen")
        ev.append("(note: recurrence history begins whenever the incident log was first written; "
                  "a fault predating that may be mis-read as first-time until the log matures)")
        return "INSTANCE", ev

    ev.append(f"this fault has closed {n}x, below the SUBSYSTEM threshold of {SUBSYSTEM_AFTER}")
    mi = rec.get("mean_interval_s")
    if mi:
        ev.append(f"mean interval: {_fmt_age(mi)}")
    return "INSTANCE", ev


# ── FAULT vs DECISION ──────────────────────────────────────────────────────────────────
#
# On the donor system, this tool's very first live run proposed "fix" two jobs that were
# BOTH deliberately switched off by a human. A mechanism that reasons about failure without
# a way to tell a fault from a decision will, sooner or later, recommend un-doing a human
# decision — the exact shape of the incident that motivated this whole module (see the
# module docstring). ⇒ A SYNTHETIC TEST WOULD NEVER HAVE CAUGHT THIS; it is the whole
# argument for proving this class of logic on a real fault, never on fabricated input.
#
# THE SIGNAL. A scheduler's breaker backoff typically doubles and caps well under a day, so
# any retry_at further out than that cannot be a backoff timer — it is a human's decision
# written into state. A 7-day floor is far above a plausible backoff cap and far below a
# deliberate park, so it cannot confuse the two in either direction.
PARK_HORIZON_S = 7 * 86400

# ── THE PARK MARKER: a DURABLE home, not an ephemeral one. ─────────────────────────────
# A human's deliberate park is not ephemeral — it must survive a reboot. `PARK_FILE` is
# resolved through the same ONE brain-root resolver every other durable store in this
# pipeline uses (`shared/brain_root.py`), never a hardcoded personal path and never `/tmp`.
# ⚠ THIS REPO HAS NO `pulse-park.sh` YET — even though a scheduler (`pulse.sh`) now exists and
# runs this module via `fault-proposer-run.sh`, nothing writes PARK_FILE on a live install
# today, because the human-facing park tool itself was never ported. Reading it is still
# correct and safe: a missing file degrades to "no jobs parked" (see `parked_jobs()`), never a
# crash, so this module is fully callable ahead of the tool that would populate it.
_HERE = os.path.dirname(os.path.abspath(__file__))
_CODE_ROOT = os.path.dirname(os.path.dirname(_HERE))          # system/tools/../.. -> repo root
_SHARED = os.path.join(_CODE_ROOT, "shared")
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)
try:
    from brain_root import resolve_brain_root          # shared/brain_root.py
    _ROOT_SOURCE, _ROOT = resolve_brain_root()
except Exception:
    _ROOT_SOURCE, _ROOT = None, None

PARK_FILE = os.environ.get("PULSE_PARK_FILE") or (
    os.path.join(_ROOT, "state", "pulse-parked-jobs.json") if _ROOT else None)
# A LEGACY, EPHEMERAL park marker some future scheduler might still write mid-migration —
# kept only as a merge-in source (see parked_jobs()), never the primary. Env-overridable so
# a test can point it at a scratch file without ever touching a real one.
PULSE_STATE = os.environ.get("PULSE_STATE") or "/tmp/lifehack-pulse-state.json"


def parked_jobs(now: float) -> dict:
    """{job: retry_at} for jobs a HUMAN switched off, never jobs a breaker tripped.

    Reads the durable PARK_FILE first (survives a reboot; None when no brain root is
    configured, in which case this source contributes nothing — not a crash), then merges
    in any LEGACY park still sitting only in the ephemeral PULSE_STATE — a park written
    before a scheduler existed here, or a partial migration, must not silently disappear.
    Fails OPEN to empty on either store: a missing/corrupt file must never be read as
    "everything parked" (nor does its absence make this tool treat a genuinely parked job
    as broken — see PULSE_STATE's separate fallback below)."""
    import json
    out = {}
    if PARK_FILE:
        try:
            with open(PARK_FILE) as fh:
                d = json.load(fh)
            for job, ra in d.items():
                try:
                    ra = float(ra)
                except (TypeError, ValueError):
                    continue
                if ra > now + PARK_HORIZON_S:
                    out[job] = ra
        except Exception:
            pass
    try:
        with open(PULSE_STATE) as fh:
            d = json.load(fh)
        for k, v in d.items():
            if not k.startswith("disabled:") or not v:
                continue
            job = k.split(":", 1)[1]
            if job in out:
                continue   # already have the durable (authoritative) record
            ra = d.get(f"retry_at:{job}", 0)
            if ra > now + PARK_HORIZON_S:
                out[job] = ra
    except Exception:
        pass
    return out


def resolve_job_identity(key: str, record: dict) -> tuple:
    """Return (job_name, display) for a ledger key.

    A fingerprint-keyed row (`key` starts with "fp:") resolves its human job name from the
    record's own `labels` — preferring `target` (the thing that actually failed) over `job`
    (the sweep that noticed) — because `key()`/`recurrence()` themselves must not move (the
    ORIGINAL key remains the identity for recurrence history); only the parked check and the
    human-facing text use the resolved name.

    ⚠ FAIL-SAFE DIRECTION: when nothing can be resolved this returns the raw key, so an
    unrecognised shape renders ugly rather than silently matching (or silently missing) a
    park. An unknown must never be read as permission, in EITHER direction.
    """
    labels = (record or {}).get("labels") or {}
    if key.startswith("fp:"):
        job_name = labels.get("target") or labels.get("job") or key
        check = labels.get("check")
        display = job_name if not check else f"{job_name} ({check})"
        return job_name, display
    job, _, state = key.partition("|")
    return job, key


def _recurrence_for(job: str, state: str, fingerprint: str) -> dict:
    """Route the recurrence read to the lookup that can actually SEE this fault's identity.

    Both branches return the SAME shape from the SAME arithmetic
    (`fault_ledger._recurrence_from_rows`) — only the row FILTER differs. With no
    fingerprint this is byte-for-byte the legacy `job|state` behaviour.
    """
    if fingerprint:
        return FL.recurrence_by_fingerprint(fingerprint)
    return FL.recurrence(job, state)


def propose(job: str, state: str, age_s: float = 0.0, job_name: str = "",
            fingerprint: str = "") -> dict:
    """Build ONE proposal. Returns {} — a REFUSAL — if the altitude cannot be cited.

    `job`/`state` are the LEDGER KEY parts and drive FL.key() — unchanged.
    `job_name` is the RESOLVED human job name (see resolve_job_identity). It defaults to
    `job` so every pre-existing caller behaves exactly as before; only the DECISION gate and
    the human-readable action text consult it.
    `fingerprint`, when set, routes the RECURRENCE read down the fingerprint path — see below.
    """
    now = time.time()
    job_name = job_name or job

    # DECISION GATE — before any altitude reasoning. A deliberately-parked job is not a
    # fault and must never be proposed "fixed"; the only honest output is to say so.
    # ⚠ Tests job_name, NOT job — see resolve_job_identity for the regression this fixes.
    parked = parked_jobs(now)
    if job_name in parked:
        yrs = (parked[job_name] - now) / 86400 / 365.25
        return {
            "fault": FL.key(job, state),
            "display": job_name,
            "altitude": "DECISION",
            "open_for": _fmt_age(age_s) if age_s else "unknown",
            "action": f"NO ACTION. {job_name} was switched off deliberately — this is a decision, not a fault.",
            "evidence": [
                f"the park's retry_at is {yrs:.1f} years out; an ordinary backoff timer caps "
                f"well under a day, so this cannot be a backoff timer",
                "a human parked this job; proposing a fix would override that decision",
            ],
            "recurrence": _recurrence_for(job, state, fingerprint),
        }

    rec = _recurrence_for(job, state, fingerprint)
    # The cohort is a claim about NOW, not about the ledger's whole life — see
    # ORGANISM_COHORT_WINDOW_S's own comment for why an unwindowed cohort is a ratchet.
    cohort = FL.recurrence_all(window_s=ORGANISM_COHORT_WINDOW_S, now=now)
    altitude, evidence = choose_altitude(rec, cohort)

    # THE REFUSAL GATE. Not decoration: an altitude with no evidence behind it is exactly
    # the confident-but-groundless claim this system's audit exists to eliminate.
    if not altitude or not evidence:
        return {}

    action = {
        "INSTANCE": f"Fix this occurrence of {job_name}. Treat it as a one-off until the log says otherwise.",
        "SUBSYSTEM": f"Stop fixing {job_name} and fix what keeps breaking it — the recurrence is the finding.",
        "ORGANISM": "Several unrelated faults are recurring together. Ask what they share before fixing any one.",
    }[altitude]

    return {
        "fault": FL.key(job, state),
        "display": job_name,
        "altitude": altitude,
        "open_for": _fmt_age(age_s) if age_s else "unknown",
        "action": action,
        "evidence": evidence,
        "recurrence": rec,
    }


def render(p: dict) -> str:
    if not p:
        return ("REFUSED — no citable evidence, so no proposal.\n"
                "  A proposal without evidence is an opinion wearing a machine's authority.")
    L = [
        f"┌─ {p['altitude']}  ·  {p.get('display') or p['fault']}  ·  open {p['open_for']}",
        f"│  {p['action']}",
        "│  WHY THIS ALTITUDE (derived, not asserted):",
    ]
    L += [f"│    - {e}" for e in p["evidence"]]
    L.append("└─ PROPOSAL ONLY — nothing has been changed.")
    return "\n".join(L)


def render_cohort(props: list) -> str:
    """Render N faults that share ONE cohort-level verdict as ONE finding.

    ⛔ WHY THIS EXISTS. An ORGANISM verdict is a claim about the COHORT, not about any one
    fault: `choose_altitude` reaches it from `recurrence_all()`, so every open fault gets
    the SAME altitude, the SAME action, and the SAME evidence list. Printed per-fault, that
    renders as N identical blocks repeating the same evidence dump — the DEFECT is that one
    finding gets printed N times, which inverts this subsystem's whole stated purpose: N
    identical walls of text make a real pattern invisible again, exactly the incomparable
    pile Hospital exists to replace.

    So: collapse on the evidence, not on the altitude — two cohorts with genuinely different
    evidence stay two findings. The altitude derivation is UNTOUCHED; only the rendering
    collapses duplicates.
    """
    ev = props[0]["evidence"]
    n = len(props)
    L = [
        f"┌─ {props[0]['altitude']}  ·  {n} faults share ONE pattern  ·  THIS IS ONE FINDING, NOT {n}",
        f"│  {props[0]['action']}",
        f"│  THE {n} FAULTS CARRYING THIS PATTERN:",
    ]
    # Shows the RESOLVED job name, falling back to the raw key — a fingerprint-keyed cohort
    # would otherwise render as N indistinguishable sha256 hashes.
    L += [f"│    - {p.get('display') or p['fault']}  (open {p['open_for']})" for p in props]
    L.append("│  WHY THIS ALTITUDE (derived, not asserted):")
    L += [f"│    - {e}" for e in ev]
    L.append("└─ PROPOSAL ONLY — nothing has been changed.")
    return "\n".join(L)


def _history_status_line() -> str:
    """The altitude derivation in choose_altitude() is only as honest as the history it
    reads. This says, every run, how much of that history was actually visible — so an
    unreachable brain root or a corrupt shard shows up as a LOUD line here, never as a
    quietly lower recurrence count with no explanation attached."""
    rep = FL.incidents_report()
    if not rep["drive_available"]:
        return f"history: DEGRADED — {rep['degraded_reason']}"
    bits = [f"{len(rep['sources_read'])}/{rep['shards_expected']} shard(s) read"]
    if rep["sources_read"]:
        bits[0] += f" ({', '.join(sorted(rep['sources_read']))})"
    if rep["local_merged"]:
        bits.append("machine-local merged in")
    line = "history: " + "; ".join(bits)
    if rep["shards_missing"]:
        line += f"  ⚠ MISSING: {', '.join(rep['shards_missing'])} — recurrence counts may be undercounted"
    return line


def main() -> int:
    d = FL.load()
    now = time.time()
    faults = d.get("faults", {})
    print(_history_status_line())
    if not faults:
        print("\nNo open faults. Nothing to propose.")
        return 0
    print(f"\n{len(faults)} open fault(s). Proposals follow — NOTHING IS APPLIED.\n")

    # Group the COHORT-level verdicts (ORGANISM) by their evidence, so an identical claim is
    # stated once. INSTANCE/SUBSYSTEM/DECISION are per-fault by construction and never collapse.
    cohorts: dict = {}
    singles = []
    for k in sorted(faults):
        job, _, state = k.partition("|")
        # Resolve the HUMAN job name from the record's own labels. The key parts
        # (job/state) still drive FL.key()/FL.recurrence()/FL.age_s() exactly as before, so
        # recurrence history is untouched; only the parked check and the rendered text change.
        rec_row = faults.get(k) or {}
        job_name, display = resolve_job_identity(k, rec_row)
        # A fingerprint-keyed fault must have its recurrence AND its age read by
        # fingerprint; the legacy job|state lookups return 0/None for it. Empty
        # fingerprint => the untouched legacy path.
        fp = rec_row.get("fingerprint") or ""
        age = FL.age_s_by_fingerprint(d, fp, now) if fp else FL.age_s(d, job, state, now)
        p = propose(job, state, age, job_name=job_name, fingerprint=fp)
        if p:
            p["display"] = display
        if p and p.get("altitude") == "ORGANISM":
            cohorts.setdefault(tuple(p["evidence"]), []).append(p)
        else:
            singles.append(p)

    for _ev, group in cohorts.items():
        # A cohort of one is just a normal finding — don't dress it as a collapse.
        print(render_cohort(group) if len(group) > 1 else render(group[0]))
        print()
    for p in singles:
        print(render(p))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())

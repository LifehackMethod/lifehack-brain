#!/usr/bin/env python3
"""
fault_ledger.py — the durable memory behind this repo's alerting (PORTED 2026-08-14 from
claudeops-config's system/tools/fault_ledger.py, organism-audit S1.2).

THE BUG THIS EXISTS TO KILL
---------------------------
An edge-triggered health sweep alerts on the EDGE: a job newly in the attention list pings
once, and from then on it is "already in the previous feed" and never speaks again. A job
that died on day 1 is therefore INDISTINGUISHABLE, on day 28, from a job that is fine — the
sweep knows it is DOWN and has simply run out of ways to say so.

Edge-triggering is only safe if something remembers. Nothing did on the donor system until
this file: the sweep's memory was the previous tile, which by definition already contained
the fault. So this ledger holds the ONE fact a sweep could never carry across runs — **how
long a fault has been true** — and it lives in `~/.config/lifehack/`, NOT `/tmp`, because a
reboot must not amnesty a three-week outage. (⚠ CORRECTED 2026-08-15, T9.7d stale-claim sweep:
this used to deny that any scheduler or cron wiring existed in the repo. That is false —
`system/tools/pulse.sh` is the live daemon, `system/tools/install-schedulers.sh` installs its
entry on cron or Windows Task Scheduler, and `system/pulse-config.md` is the row manifest.
What's still true is narrower: no `pulse-config.md` row calls `record_faults()` specifically on
a cadence today; the store and its API are ported correct-and-callable for whenever one does.)

DESIGN BOUNDS (the KISS floor's ruling, deliberately narrow)
------------------------------------------------------------
ONE escalation tier. Not 1h/6h/24h/daily — that is a policy engine for one human with one
phone. A fault older than its cadence gets LOUDER, once a day, and that is all. No severity
matrix, no routing rules, no second channel. If it needs a schema, it is overbuild.

STORES
------
  ~/.config/lifehack/faults.json
    faults   : {"<job>|<state>": {first_seen, last_seen, last_alert}}
               (or {"fp:<fingerprint>": {..., fingerprint, labels}} — see THE T15.18 block below)
    machines : {"<name>": {"heartbeat_ever_seen": bool}}   # gates the deadman fail-closed
    producers: {"<name>": {rc, ts, err}}                   # un-swallowed child failures,
                                                            # dropped via record_producers()
                                                            # when no longer in the caller's roster
  <brain>/state/incidents/<machine>.jsonl   (append-only incident history, mirrored — see below)
  ~/.config/lifehack/incidents.jsonl        (the always-available local copy of the same history)

WHAT CHANGED IN THIS PORT (generalisation, not a redesign)
------------------------------------------------------------
  · STATE_DIR moved from `~/.local/state/claudeops` (donor, machine-local but product-named) to
    `~/.config/lifehack` — this repo's ALREADY-established machine-local config home (token,
    creds, pause-file, brain-root pointer, `*-last-seen` markers all already live there; see
    `shared/brain_root.py` / `system/hooks/ingest_gate_enforce.sh`'s own docstrings). Not a new
    location — the existing one, extended.
  · The Drive incident mirror (donor: a hardcoded personal Drive-mount path with the account email
    baked into its name, in the mount-point shape macOS uses for Google Drive — env-overridable via
    `CLAUDEOPS_DRIVE`) now resolves through `shared/brain_root.py`'s
    `resolve_brain_root()` — the ONE root resolver every other ported store in this repo already
    uses (`emit_finding.py`, `emit_recommendation.py`, ...). `INCIDENT_SHARD_DIR` is `None` when
    no root is configured, and every function that touches it treats that exactly like an
    unreachable mount — degraded, honestly reported, never a crash and never invented rows.
  · `machine_token.py` (the donor's two-machine derivation script) is excluded from this port —
    this product is one machine by design. `_machine_token()` collapses to the SAME local-constant
    pattern `emit_finding.py`/`emit_recommendation.py` already use (`MACHINE = "local"`), restated
    here per this repo's own convention of copying the tiny technique rather than importing across
    an excluded module boundary.

Compatible with `/usr/bin/python3` (3.9) — no `X | None` union annotations, stdlib only.
"""
from __future__ import annotations   # keep annotations lazy for 3.9 compatibility

import glob
import json
import os
import sys
import time

STATE_DIR = os.path.expanduser("~/.config/lifehack")
LEDGER = os.path.join(STATE_DIR, "faults.json")

# ── incident history mirrored to the resolved brain root ──────────────────────────────────
#
# THE PROBLEM A LOCAL-ONLY STORE HAS. If `incidents.jsonl` lived ONLY in `~/.config/lifehack` —
# machine-local, backed up nowhere — losing that directory (or moving to a second machine) would
# re-grade every fault as INSTANCE ("first occurrence"), citing evidence and looking completely
# normal. A confidently wrong verdict is worse than no verdict.
#
# THE FIX IS NOT "share one file". A shared append-only log that writes "machine" INTO every line
# is not fork-proof by itself — ONE WRITER PER PATH is what holds (the same idiom every other
# store in this pipeline uses: `emit_finding.py`'s `state/findings/<producer>.<machine>.jsonl`,
# `emit_recommendation.py`'s `state/recommendations/<altitude>.<machine>.jsonl`). So this mirrors
# that exact idiom: `state/incidents/<machine>.jsonl` under the resolved brain root.
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

# None when no root is configured. Every reader below treats that exactly like an unreachable
# mount — degraded, honestly reported, never a crash and never invented rows. There is no local
# fallback confusion here because INCIDENTS (below) already IS the always-available local copy;
# this is the ADDITIONAL, cross-machine-safe mirror.
INCIDENT_SHARD_DIR = os.path.join(_ROOT, "state", "incidents") if _ROOT else None

# ── TWO identity schemes, ONE ledger, ONE incident store ──────────────────────────────────
#
# `emit_finding.py` gives every Hospital finding a `fingerprint` — sha256 over its sorted label
# set, computed IN THE WRITER, never hand-authored. That is a different identity shape than this
# ledger's existing `job|state` key, but it is still exactly one thing: a durable identity a
# fault/finding can be tracked by across runs. Widening the KEY, not the STORE:
#
# A fingerprint-identified row lives at key `"fp:<fingerprint>"` in the SAME `d["faults"]` dict a
# legacy row lives in at key `"<job>|<state>"`. The two namespaces are PROVABLY disjoint: a legacy
# key's 3rd character (once job/state are both non-empty) is always the literal delimiter `|`,
# while a fingerprint key's first three characters are always literally `fp:` — the only string
# that could collide would need a job named exactly `"fp"` whose key's 3rd char is `|`, which can
# never equal `:`. No hashing, no registry, no possible collision.
#
# THE ONE RULE THAT MAKES COEXISTENCE SAFE: each namespace's "this is no longer active, bank it
# and drop it" reap loop (`record_faults` / `record_findings`) must only ever look at ITS OWN
# namespace's keys — both reap loops below are namespace-filtered for exactly this reason.

_FP_PREFIX = "fp:"


def finding_key(fingerprint: str) -> str:
    """Ledger key for a fingerprint-identified finding — the fingerprint IS the identity
    (`emit_finding.py`'s whole point: mechanical, never hand-authored), this just namespaces
    it so it can share `d["faults"]` with legacy `job|state` keys without collision."""
    return f"{_FP_PREFIX}{fingerprint}"


# ── MACHINE TOKEN — re-derived locally, NOT imported. ───────────────────────────────────────
# `machine_token.py` is part of the two-machine plane this product doesn't have (excluded — see
# the module docstring's "WHAT CHANGED") and is never imported, copied, or shelled out to from
# here. This product is one machine by design, so the derivation collapses to a fixed constant —
# the SAME local pattern `emit_finding.py` / `emit_recommendation.py` already use, restated here
# rather than imported, per this repo's own convention of copying a tiny private technique across
# a file boundary rather than reaching into a sibling module's internals.
MACHINE = "local"


def _machine_token() -> str:
    """Always `MACHINE`. Kept as a function (not a bare constant reference at each call site,
    and cached under the donor's name) so a future multi-install need has exactly one place to
    change, and so every call site below reads identically to the donor's."""
    return MACHINE

DAY_S = 86400
# A fault must be at least this old before it starts re-alerting. Below this the ordinary
# edge-trigger alert has already fired and a human plausibly still remembers it.
ESCALATE_AFTER_S = DAY_S
# ...and then it re-alerts at most this often. ONE tier. See DESIGN BOUNDS above.
RE_ALERT_EVERY_S = DAY_S


def _empty() -> dict:
    return {"faults": {}, "machines": {}, "producers": {}}


def load() -> dict:
    try:
        with open(LEDGER) as fh:
            d = json.load(fh)
        for k in ("faults", "machines", "producers"):
            d.setdefault(k, {})
        return d
    except Exception:
        # A missing or corrupt ledger must not take the sweep down with it. We lose AGE
        # history (the fault re-ages from now) but never the sweep itself.
        return _empty()


def save(d: dict) -> bool:
    """Atomic write. Returns False on failure — the caller decides how loud to be."""
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        tmp = LEDGER + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(d, fh, indent=2, sort_keys=True)
        os.replace(tmp, LEDGER)
        return True
    except Exception:
        return False


def key(job: str, state: str) -> str:
    return f"{job}|{state}"


def record_faults(d: dict, active: list, now: float) -> dict:
    """
    `active` = [(job, state), ...] currently in fault. Stamps first_seen on arrival,
    refreshes last_seen, and DROPS rows that are no longer in fault — a recovered job
    must forget its age, or it would escalate forever on a stale timer.

    The reap loop below is filtered to `job|state`-namespaced keys ONLY. `d["faults"]` may
    also hold `fp:`-namespaced rows written by `record_findings()` — this function must never
    see those as "not in my active list" and reap them; that would silently truncate
    fingerprinted history to zero on every ordinary legacy sweep. See the namespace block above.
    """
    live = set()
    for job, state in active:
        k = key(job, state)
        live.add(k)
        row = d["faults"].get(k)
        if row is None:
            d["faults"][k] = {"first_seen": now, "last_seen": now, "last_alert": 0}
        else:
            row["last_seen"] = now
    for k in [k for k in d["faults"] if not k.startswith(_FP_PREFIX) and k not in live]:
        # The row is about to be DELETED — which is correct for the escalation timer and fatal
        # for self-healing. Bank the closed incident FIRST, into a separate append-only log, so
        # "has this happened before?" stays answerable.
        _append_incident(k, d["faults"][k], now)
        del d["faults"][k]
    return d


def record_findings(d: dict, findings: list, now: float) -> dict:
    """The fingerprint-identified sibling of `record_faults`, for Hospital findings
    (`emit_finding.py` / `findings_reader.py`). Same lifecycle (first_seen on arrival, refresh
    last_seen while present, bank-then-drop on recovery), same `d["faults"]` dict, same
    `_append_incident` banking path — an ADDITIVE key namespace, never a second store.

    `findings` = iterable of dicts each carrying a mechanical `fingerprint` (required) and
    optionally `labels` (kept on the row purely for incident context — NOT re-derived or
    re-validated here; `emit_finding.py` already owns that computation).

    Mirrors `record_faults`'s namespace discipline exactly: the reap loop below only ever
    touches `fp:`-prefixed keys, so a findings sweep can never reap a legacy job|state fault
    out from under `record_faults`.
    """
    live = set()
    for f in findings:
        fp = f["fingerprint"]
        k = finding_key(fp)
        live.add(k)
        row = d["faults"].get(k)
        if row is None:
            d["faults"][k] = {"first_seen": now, "last_seen": now, "last_alert": 0,
                               "fingerprint": fp, "labels": dict(f.get("labels") or {})}
        else:
            row["last_seen"] = now
            if f.get("labels"):
                row["labels"] = dict(f["labels"])
    for k in [k for k in d["faults"] if k.startswith(_FP_PREFIX) and k not in live]:
        _append_incident(k, d["faults"][k], now)
        del d["faults"][k]
    return d


# ── incident history: the OTHER half of "age + history" ───────────────────────────────────
#
# WHY A SECOND STORE AND NOT A FIELD ON THE ROW. `record_faults` must keep deleting recovered
# rows or a recovered job escalates forever on a stale timer — that reset is load-bearing and is
# NOT touched here. But deleting the row also destroys the only evidence that a fault ever
# happened, so a job that breaks weekly looks BRAND NEW every single time. Two stores, two jobs:
#     faults.json     -> "what is wrong RIGHT NOW"   (drops on recovery, correct)
#     incidents.jsonl -> "has this happened BEFORE"  (append-only, never drops)
#
# Append-only JSONL, not JSON: a corrupt or partial line costs one incident, never the whole
# history, and it never needs a read-modify-write race with the live sweep.

INCIDENTS = os.path.join(STATE_DIR, "incidents.jsonl")


def _append_incident(fault_key: str, row: dict, now: float) -> bool:
    """Record ONE resolved incident. Best-effort by design: history is valuable but it must
    never be able to take the health sweep down — same posture as load().

    Writes TWICE — the original machine-local file (unchanged, still the fast always-available
    path) AND a mirror to this machine's OWN shard under the resolved brain root
    (`state/incidents/<machine>.jsonl`), when a root is configured. The mirror write is wrapped
    separately and can fail silently on its own (a measured-flaky mount, or simply no root set
    yet) WITHOUT losing the local write, which already succeeded by the time we try it. The
    reader (`incidents()`/`incidents_report()`) is where a mirror gap is required to become LOUD
    — a silent write failure here is recoverable (the local copy still has it); a silent READ
    failure is not.

    `row` comes in TWO shapes depending on which namespace `fault_key` belongs to: a legacy
    `job|state` row (no `fingerprint` key at all) or a fingerprint row (always carries
    `fingerprint`, from `record_findings`).
    """
    try:
        first = float(row.get("first_seen", now))
        if "fingerprint" in row:
            rec = {
                "fingerprint": row.get("fingerprint"),
                "labels": dict(row.get("labels") or {}),
                "first_seen": first,
                "resolved_at": now,
                "duration_s": round(now - first, 1),
                "alerted": bool(row.get("last_alert", 0)),
            }
        else:
            job, _, state = fault_key.partition("|")
            rec = {
                "job": job,
                "state": state,
                "first_seen": first,
                "resolved_at": now,
                "duration_s": round(now - first, 1),
                "alerted": bool(row.get("last_alert", 0)),
            }
        line = json.dumps(rec, sort_keys=True) + "\n"
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(INCIDENTS, "a") as fh:
            fh.write(line)
    except Exception:
        return False

    if INCIDENT_SHARD_DIR:
        try:
            machine = _machine_token()
            os.makedirs(INCIDENT_SHARD_DIR, exist_ok=True)
            shard = os.path.join(INCIDENT_SHARD_DIR, f"{machine}.jsonl")
            with open(shard, "a") as fh:
                fh.write(line)
        except Exception:
            pass  # the mirror is best-effort ON TOP of the local write, which already landed.

    return True


def _read_jsonl(path: str) -> tuple:
    """Return (rows, ok, bad_lines). ok=False means the PATH itself could not be opened at
    all — missing, permission-denied, or a flaky-mount failure mode — and the caller MUST
    treat that as a missing shard, never as an empty (and therefore silently-lower-count) one.

    bad_lines counts malformed JSON lines inside an otherwise-openable file — a good row is
    still credited (dropping the whole shard over one bad line would itself be a silent
    shrink), but the count is no longer thrown away. Same shape and field posture as
    `findings_reader.py`'s `_read_jsonl` — this is that reader's sibling closing the identical
    gap here rather than inventing a second idiom for it."""
    rows = []
    bad_lines = 0
    try:
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    bad_lines += 1
        return rows, True, bad_lines
    except FileNotFoundError:
        return rows, True, 0   # no file yet = no history yet, NOT a failure — never a "missing shard"
    except Exception:
        return rows, False, 0


def _dedupe_incidents(rows: list) -> list:
    """Same physical incident can legitimately appear twice in the union — this machine writes
    its own local file AND its own brain-root shard for every closed fault — so dedupe on
    content identity rather than trying to pick "the" authoritative source. Two genuinely
    distinct incidents of the same job|state will still differ on first_seen.

    `fingerprint` joins the identity tuple so two distinct fingerprinted findings that happen
    to close in the same instant are never folded into one. Every legacy row has `fingerprint`
    absent (`.get` -> None) so this is a no-op for legacy rows."""
    seen = set()
    out = []
    for r in rows:
        try:
            k = (r.get("job"), r.get("state"), r.get("fingerprint"),
                 round(float(r.get("first_seen", 0)), 1),
                 round(float(r.get("resolved_at", 0)), 1))
        except Exception:
            k = (r.get("job"), r.get("state"), r.get("fingerprint"),
                 r.get("first_seen"), r.get("resolved_at"))
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    return out


def incidents_report(job: str = "", state: str = "", fingerprint: str = "") -> dict:
    """The UNION read across every machine's brain-root shard, PLUS the missing-shard and
    degradation accounting the altitude derivation depends on being honest about. Never
    raises; every failure mode degrades to something narrower and SAYS so in the returned
    dict, rather than silently returning a smaller `rows` list that looks the same as
    "nothing else ever happened".

    Keys:
      rows              deduped incident dicts, unfiltered by job/state (see incidents())
      shards_expected   how many *.jsonl paths the brain-root glob returned (0 if the dir is
                         empty/absent but the root itself IS reachable — a legitimate first-run
                         state, not a failure)
      sources_read      machine tokens whose shard opened + parsed cleanly
      shards_missing    filenames the glob found but could NOT be opened/parsed — a chmod'd
                         or corrupt shard shows up HERE, never as a quietly lower
                         `shards_expected`
      local_merged      True if `~/.config/lifehack/incidents.jsonl` contributed rows to the
                         union this call
      bad_lines         {shard_filename: malformed_line_count} — matching `findings_reader.py`'s
                         field naming exactly. Only shards (brain-root OR the local fallback,
                         keyed by its basename) with >=1 bad line appear here.
      drive_available   False if no brain root is configured at all, or a configured root
                         could not be reached — the one case where the read degrades to
                         LOCAL-ONLY. Name kept as `drive_available` for interface stability
                         with the donor, even though "Drive" is not this product's model.
      degraded          True whenever the picture is known-incomplete: drive_available is
                         False, OR shards_missing is non-empty, OR bad_lines is non-empty —
                         the signal `fault_proposer` must surface, never swallow
      degraded_reason   human-readable why, empty string when not degraded
    """
    my_machine = _machine_token()
    report = {
        "rows": [], "shards_expected": 0, "sources_read": [], "shards_missing": [],
        "bad_lines": {}, "local_merged": False, "drive_available": True, "degraded": False,
        "degraded_reason": "",
    }

    paths = []
    try:
        if INCIDENT_SHARD_DIR is None:
            raise OSError("no notes root configured — brain_root.resolve_brain_root() returned "
                          "NOT-SET (fix: python3 shared/brain_root.py --set <folder>)")
        if os.path.isdir(INCIDENT_SHARD_DIR):
            paths = sorted(glob.glob(os.path.join(INCIDENT_SHARD_DIR, "*.jsonl")))
        elif not os.path.isdir(_ROOT):
            # The root itself is gone, not just the (optional, first-run-absent) shard dir
            # under it — this is the measured-flaky-mount case, not "no history yet".
            raise OSError(f"notes root not reachable: {_ROOT}")
        # else: the root is up, state/incidents/ just doesn't exist yet — 0 shards, not an error.
    except Exception as e:
        report["drive_available"] = False
        report["degraded"] = True
        local_rows, local_ok, local_bad = _read_jsonl(INCIDENTS)
        if local_ok:
            report["rows"] = _dedupe_incidents(local_rows)
            report["local_merged"] = bool(local_rows)
            reason = (
                f"notes root unavailable ({e}) — degraded to machine-local history only "
                f"({len(local_rows)} local incident(s))")
            if local_bad:
                report["bad_lines"][os.path.basename(INCIDENTS)] = local_bad
                reason += f"; {local_bad} malformed line(s) in the local fallback"
            report["degraded_reason"] = reason
        else:
            report["degraded_reason"] = (
                f"notes root unavailable ({e}) AND the machine-local fallback "
                f"({INCIDENTS}) is also unreadable — NO incident history available this run")
        return _filter_report(report, job, state, fingerprint)

    report["shards_expected"] = len(paths)
    all_rows = []
    for p in paths:
        name = os.path.basename(p)
        rows, ok, bad = _read_jsonl(p)
        if not ok:
            report["shards_missing"].append(name)
            continue
        machine = name[:-len(".jsonl")] if name.endswith(".jsonl") else name
        report["sources_read"].append(machine)
        all_rows.extend(rows)
        if bad:
            report["bad_lines"][name] = bad

    # The machine-local file is always folded in too (not just when this machine's own shard
    # is absent) — dedupe on content identity handles the overlap, and this way a write that
    # landed locally but never made it to the mirror is never silently lost from the union.
    local_rows, local_ok, local_bad = _read_jsonl(INCIDENTS)
    if local_ok and local_rows:
        all_rows.extend(local_rows)
        report["local_merged"] = True
    elif not local_ok and my_machine not in report["sources_read"]:
        # This machine has NEITHER a readable brain-root shard NOR a readable local file — its
        # own history is fully invisible this run. That is a finding, not a shrug.
        report["shards_missing"].append(f"{INCIDENTS} (this machine's local fallback)")
    if local_ok and local_bad:
        report["bad_lines"][os.path.basename(INCIDENTS)] = local_bad

    reasons = []
    if report["shards_missing"]:
        reasons.append(
            f"{len(report['shards_missing'])} shard(s) unreadable: " + ", ".join(report["shards_missing"]))
    if report["bad_lines"]:
        total_bad = sum(report["bad_lines"].values())
        reasons.append(
            f"{total_bad} malformed line(s) across {len(report['bad_lines'])} shard(s): "
            + ", ".join(f"{k}={v}" for k, v in sorted(report["bad_lines"].items())))
    if reasons:
        report["degraded"] = True
        report["degraded_reason"] = "; ".join(reasons)

    report["rows"] = _dedupe_incidents(all_rows)
    return _filter_report(report, job, state, fingerprint)


def _filter_report(report: dict, job: str, state: str, fingerprint: str = "") -> dict:
    """The `fingerprint` filter alongside job/state is additive only. Every existing call
    site (`incidents_report()`/`incidents()` with just job/state, or with nothing at all —
    `fault_proposer`'s `FL.incidents_report()`) passes `fingerprint=""` by default, which
    short-circuits this clause."""
    if not job and not state and not fingerprint:
        return report
    rows = [r for r in report["rows"]
            if (not job or r.get("job") == job)
            and (not state or r.get("state") == state)
            and (not fingerprint or r.get("fingerprint") == fingerprint)]
    report = dict(report)
    report["rows"] = rows
    return report


def incidents(job: str = "", state: str = "", fingerprint: str = "") -> list:
    """Every closed incident, oldest first, UNIONED across every machine's brain-root shard
    plus the machine-local file — see incidents_report() for the merge rule and the
    missing-shard accounting. Kept as the stable, filter-only entry point that
    recurrence()/recurrence_all() already call; callers that need the degradation/coverage
    picture (fault_proposer) call incidents_report() directly.

    `fingerprint` is an additive filter alongside job/state, for the fingerprint-identified
    sibling of a legacy job|state fault — see recurrence_by_fingerprint()."""
    rows = incidents_report(job, state, fingerprint).get("rows", [])
    rows.sort(key=lambda r: r.get("first_seen", 0))
    return rows


def recurrence(job: str, state: str) -> dict:
    """The ONE read that separates altitude 1 from altitude 2.

    "Fix this instance" and "fix this subsystem" are the same sentence until you know
    whether it has happened before. This returns that, and nothing else:

        occurrences      how many times this exact fault has CLOSED
        first_ever       epoch of the earliest recorded occurrence (None if never)
        last_resolved    epoch of the most recent close (None if never)
        mean_interval_s  average gap between the STARTS of consecutive occurrences
                         (None with <2 occurrences — an interval needs two points, and
                         inventing one from a single event is exactly the kind of
                         confident-but-baseless number this project exists to kill)
        total_downtime_s summed duration of all closed occurrences

    NOTE the deliberate blind spot: this counts CLOSED incidents only. A fault open right now
    is in faults.json, not here. The caller holds both — the live row says "it is broken",
    this says "and it has broken N times before". Neither alone is enough to choose an
    altitude, which is why `propose()` (fault_proposer.py) takes both.

    The row-filter (`incidents(job, state)`) and the arithmetic below are shared with
    `recurrence_by_fingerprint()` via `_recurrence_from_rows()` so the two key schemes can
    never silently compute recurrence two different ways.
    """
    rows = sorted(incidents(job, state), key=lambda r: r.get("first_seen", 0))
    return _recurrence_from_rows(rows)


def _recurrence_from_rows(rows: list) -> dict:
    """The arithmetic half of recurrence()/recurrence_by_fingerprint() — SHARED so the two
    key schemes can never silently compute recurrence two different ways. `rows` must already
    be sorted oldest-first by `first_seen` (both callers do this before calling in)."""
    n = len(rows)
    if n == 0:
        return {"occurrences": 0, "first_ever": None, "last_resolved": None,
                "mean_interval_s": None, "total_downtime_s": 0.0}
    starts = [r.get("first_seen", 0) for r in rows]
    mean_gap = None
    if n >= 2:
        gaps = [starts[i + 1] - starts[i] for i in range(n - 1)]
        mean_gap = round(sum(gaps) / len(gaps), 1)
    return {
        "occurrences": n,
        "first_ever": starts[0],
        "last_resolved": rows[-1].get("resolved_at"),
        "mean_interval_s": mean_gap,
        "total_downtime_s": round(sum(r.get("duration_s", 0.0) for r in rows), 1),
    }


def recurrence_by_fingerprint(fingerprint: str) -> dict:
    """The fingerprint-identified sibling of recurrence(job, state). SAME shape, SAME meaning,
    SAME arithmetic (_recurrence_from_rows) — just filtered by the mechanical fingerprint
    identity from emit_finding.py instead of the legacy job|state pair. Callers (e.g.
    fault_proposer.choose_altitude) treat the returned dict identically either way.
    """
    rows = sorted(incidents(fingerprint=fingerprint), key=lambda r: r.get("first_seen", 0))
    return _recurrence_from_rows(rows)


def recurrence_all(window_s=None, now=None) -> dict:
    """Every fault/finding key that has ever closed, with its recurrence record. The input to
    altitude 3 (organism-level): patterns are only visible across keys, never within one.

    Widened to fold in BOTH key schemes from the SAME incidents() union — a legacy row
    (job/state fields) keys under `key(job, state)`; a fingerprint row (a `fingerprint`
    field) keys under `finding_key(fingerprint)`.

    Gained an OPTIONAL `window_s`. With it unset, this takes the identical code path
    (delegates to recurrence()/recurrence_by_fingerprint()) as always. With it set, only
    incidents that CLOSED inside the window count — see fault_proposer's
    ORGANISM_COHORT_WINDOW_S for why that option exists (an unwindowed cohort is a ratchet
    that can only ever grow, never mean anything about "now")."""
    if window_s is None:
        # ── THE UNTOUCHED UNWINDOWED PATH. Do not "unify" this with the windowed branch
        # below: this one delegates to recurrence()/recurrence_by_fingerprint(), and keeping
        # it byte-for-byte is what guarantees the default behaviour cannot drift. ──
        out = {}
        for r in incidents():
            fp = r.get("fingerprint")
            if fp:
                k = finding_key(fp)
                if k not in out:
                    out[k] = recurrence_by_fingerprint(fp)
            else:
                j, s = r.get("job", ""), r.get("state", "")
                k = key(j, s)
                if k not in out:
                    out[k] = recurrence(j, s)
        return out

    # ── WINDOWED. Group the rows that closed inside the window, then run the SAME shared
    # arithmetic (_recurrence_from_rows) the unwindowed path uses — one arithmetic, two
    # filters, so a windowed and an unwindowed cohort can never mean different things. ──
    now = time.time() if now is None else now
    cutoff = now - window_s
    groups = {}
    for r in incidents():
        resolved = r.get("resolved_at")
        # An incident with no resolved_at has not closed; recurrence counts CLOSED
        # occurrences only (see recurrence()'s "deliberate blind spot" note), so it is
        # excluded here for the same reason it is excluded there — not silently dropped.
        if resolved is None or resolved < cutoff:
            continue
        fp = r.get("fingerprint")
        k = finding_key(fp) if fp else key(r.get("job", ""), r.get("state", ""))
        groups.setdefault(k, []).append(r)
    return {k: _recurrence_from_rows(sorted(rows, key=lambda r: r.get("first_seen", 0)))
            for k, rows in groups.items()}


def age_s(d: dict, job: str, state: str, now: float) -> float:
    row = d["faults"].get(key(job, state))
    return (now - row["first_seen"]) if row else 0.0


def human_age(seconds: float) -> str:
    """Compact, and — critically — CHANGES as the fault ages, so the notify governor sees a
    new message on each escalation (see escalation_message() below)."""
    if seconds < 3600:
        return f"{int(seconds // 60)}m"
    if seconds < DAY_S:
        return f"{int(seconds // 3600)}h"
    return f"{int(seconds // DAY_S)}d"


def due_for_escalation(d: dict, job: str, state: str, now: float) -> bool:
    row = d["faults"].get(key(job, state))
    if not row:
        return False
    if (now - row["first_seen"]) < ESCALATE_AFTER_S:
        return False
    return (now - row.get("last_alert", 0)) >= RE_ALERT_EVERY_S


def mark_alerted(d: dict, job: str, state: str, now: float) -> None:
    row = d["faults"].get(key(job, state))
    if row:
        row["last_alert"] = now


# ── the fingerprint-identified siblings of age_s/due_for_escalation/mark_alerted ──────────
#
# These let a caller run the escalation state machine off the SAME `fp:` row `record_findings()`
# already maintains, instead of minting a second `job|state` row next to it for data that
# already has a mechanical identity. Byte-identical logic to their job|state siblings above —
# only the key derivation differs (`finding_key(fingerprint)` vs `key(job, state)`).
def age_s_by_fingerprint(d: dict, fingerprint: str, now: float) -> float:
    row = d["faults"].get(finding_key(fingerprint))
    return (now - row["first_seen"]) if row else 0.0


def due_for_escalation_by_fingerprint(d: dict, fingerprint: str, now: float) -> bool:
    row = d["faults"].get(finding_key(fingerprint))
    if not row:
        return False
    if (now - row["first_seen"]) < ESCALATE_AFTER_S:
        return False
    return (now - row.get("last_alert", 0)) >= RE_ALERT_EVERY_S


def mark_alerted_by_fingerprint(d: dict, fingerprint: str, now: float) -> None:
    row = d["faults"].get(finding_key(fingerprint))
    if row:
        row["last_alert"] = now


def escalation_message(job: str, state: str, seconds: float) -> str:
    """MUST contain the age — that is what makes each escalation a distinct
    (source, message) pair and survive a dedup-by-text notify governor."""
    return f"{job} {state} {human_age(seconds)}"


# ── machine heartbeat: gates the deadman's fail-closed flip ───────────────────────────────
def note_heartbeat(d: dict, machine: str) -> dict:
    """Sticky: once a machine has EVER been seen alive, it can never un-see it."""
    d["machines"].setdefault(machine, {})["heartbeat_ever_seen"] = True
    return d


def heartbeat_ever_seen(d: dict, machine: str) -> bool:
    """
    False on a machine that has never reported — a FRESH CLONE, not a wedge.
    The deadman must stay silent there. Flipping it naively would make every new or
    rebuilt machine buzz critical from first boot forever, training the one human to
    ignore the single channel that bypasses quiet hours — manufacturing the alarm
    fatigue this whole feature exists to cure.
    """
    return bool(d["machines"].get(machine, {}).get("heartbeat_ever_seen"))


# ── producer heartbeat: un-swallows the sweep's child failures ────────────────────────────
def note_producer(d: dict, name: str, rc: int, now: float, err: str = "") -> dict:
    d["producers"][name] = {"rc": int(rc), "ts": now, "err": (err or "")[:300]}
    return d


def record_producers(d: dict, known: list, now: float) -> dict:
    """
    The OTHER half of note_producer, mirroring record_faults' drop exactly. Before this,
    nothing ever removed a row: a renamed or deleted producer kept its last rc=0 forever
    (green from a corpse) or, if it last failed, sat in `failed_producers` as an alert that
    could never recover — the same edge-trigger mistake record_faults already exists to
    prevent, made a second time on a second dict in the same file.

    `known` MUST be the caller's static roster of producer names — the full set of
    `_run_producer(...)` call sites wired into this sweep's code — and NOT "which producers
    happened to report in THIS run". Those are different sets: a crash or early-exit could
    skip a call site without that producer having been renamed or removed. Passing the actual
    roster (not the this-run observation) is what lets this tell "didn't run this sweep" from
    "no longer exists" apart — a row for a producer still in `known` is left untouched even if
    it wasn't refreshed this run, exactly like an active fault stays in faults.json between
    alerts; only a row whose name has fallen OUT of `known` gets dropped.
    """
    known_set = set(known)
    for n in [n for n in d["producers"] if n not in known_set]:
        del d["producers"][n]
    return d


def failed_producers(d: dict) -> list:
    return sorted(n for n, r in d["producers"].items() if r.get("rc", 0) != 0)


if __name__ == "__main__":
    import sys as _sys
    d = load()
    if len(_sys.argv) > 1 and _sys.argv[1] == "show":
        print(json.dumps(d, indent=2, sort_keys=True))
    else:
        now = time.time()
        print(f"ledger: {LEDGER}")
        print(f"  faults    : {len(d['faults'])}")
        for k, r in sorted(d["faults"].items()):
            print(f"      {k}  age={human_age(now - r['first_seen'])}")
        print(f"  machines  : {list(d['machines'])}")
        bad = failed_producers(d)
        print(f"  producers : {len(d['producers'])} tracked, {len(bad)} failing {bad or ''}")

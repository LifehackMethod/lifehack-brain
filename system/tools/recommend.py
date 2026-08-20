#!/usr/bin/env python3
"""recommend.py — the GROUND-ALTITUDE reasoner between Hospital and a human (PORTED
2026-08-14 from claudeops-config's system/tools/recommend.py).

WHERE THIS SITS. Hospital detects and ranks: detectors -> emit_finding.py ->
state/findings/<producer>.<machine>.jsonl -> findings_reader.py. Efficiency reasons and
recommends: findings -> THIS FILE -> emit_recommendation.py -> a review surface -> a human
acts. This is the wiring between those two halves — it does not detect anything new and it
does not decide anything new; it reads Hospital's union of findings, asks fault_proposer.py
(the already-proven altitude logic) what altitude each currently-wrong finding deserves, and
writes that answer through emit_recommendation.py, which is the ONE validating writer for
this store. Three modules already own the hard parts; this file's whole job is choosing
which finding to reason about and handing it to them in the right shape.

⛔⛔ PROPOSE-ONLY. This module suggests. It NEVER applies, retries, re-runs, or repairs
anything — same invariant as fault_proposer.py and emit_recommendation.py, restated here
because it is this repo's most consequential failure class to reproduce: a mechanism that
cannot tell a fault from a deliberate decision must never act on its own read. If a future
edit to this file grows a code path that changes state anywhere other than the
recommendations store, that edit has left this module's scope.

GROUND ALTITUDE ONLY. fault_proposer's four altitudes — INSTANCE / SUBSYSTEM / ORGANISM /
DECISION — are about the BLAST RADIUS of a fault (fix the instance, fix the component, ask
what several faults share, or don't touch a human's decision). That is a completely different
axis from a "5,000ft / 10,000ft" knowledge-altitude doctrine, which is about WHERE a piece of
knowledge belongs — the two just happen to share the word "altitude". This file only ever
touches fault_proposer's axis. The seams lane (`seam_reason.py`, a shape ACROSS findings that
fault_proposer's own per-key call can't see) and any architecture-proposing lane are OUT OF
SCOPE ON PURPOSE — both need a human in the room to scope them.

★ THE ONE DESIGN CALL THIS FILE MAKES THAT NEITHER SIBLING MODULE MAKES FOR IT: findings_reader
returns the FULL APPEND-ONLY HISTORY — every line any detector has EVER written across every
run — not "what is wrong right now" (see findings_reader.py's own docstring: it is a UNION
reader over an append-only store, on purpose; deciding "current" is a ranking-layer question,
explicitly left to the caller). Reasoning over every historical row would re-propose a fix for
something that resolved three weeks ago, which is worse than staying silent — it is a
confidently wrong verdict. So the very first thing this file does is collapse the union down
to ONE row per finding identity (the mechanical `fingerprint` emit_finding.py already
computes) by keeping only the most recently-timestamped row for each — see
`_latest_by_fingerprint()`. Only THAT snapshot is reasoned about.

★ THE SECOND JUDGMENT CALL, STATED OPENLY RATHER THAN QUIETLY WORKED AROUND: fault_proposer's
`propose(job, state, ...)` derives THIS FAULT'S OWN recurrence via `fault_ledger.recurrence(job,
state)`, which matches on a LEGACY `job`/`state` field pair inside a CLOSED incident row. A
Hospital finding's real identity is its `fingerprint`, and a fingerprint-identified incident row
carries NO `job`/`state` fields at all — so calling `propose()` with a synthetic
`job=f"fp:{fingerprint}"` (the same shape fault_proposer.main() already builds when it
partitions a real `fp:`-prefixed ledger key on "|") can NEVER match a closed incident's legacy
fields. So the SUBSYSTEM branch of `choose_altitude()` (this exact fault recurring 3+ times) is
currently unreachable for a Hospital-sourced finding — it will always read as "first occurrence"
on that axis, even on its fifth actual recurrence, until this gap is closed on the
fault_proposer/fault_ledger side. **This file does not attempt to patch around that** — doing so
would mean either (a) hand-rolling a second recurrence source that could silently drift from
`choose_altitude()`'s own thresholds, or (b) hand-writing SUBSYSTEM/ORGANISM prose that
duplicates text fault_proposer.py deliberately does not export.

⚠ BUT ORGANISM IS NOT BLIND, AND IS OFTEN THE ACTUAL VERDICT. `choose_altitude()` checks
ORGANISM FIRST, and ORGANISM is a claim about the COHORT (`fault_ledger.recurrence_all()` —
every fault/finding key that has ANY closed incident history, across the whole machine), not
about the one fault being graded. On a fresh install with a growing incident history, the
honest one-line summary is: **DECISION when parked (always correct, gate never bypassed);
otherwise ORGANISM once this machine's cohort qualifies (>= 2 distinct recurring keys),
degrading to INSTANCE below that; SUBSYSTEM is unreachable via this wiring until the
fp:-recurrence gap above is closed.** Flagged loudly here, not buried.

★ THE DECISION GATE ALWAYS WINS, AND IS ALWAYS SOURCED FROM `fault_proposer.propose()` ITSELF.
This file never asks "is this job parked?" on its own — it always calls
`fault_proposer.resolve_job_identity()` (to get the same human job name the resolver produces)
and then `fault_proposer.propose(job_name=...)` (whose FIRST act, before any altitude
reasoning, is exactly that parked check — see fault_proposer.py's "DECISION GATE"). Whatever
`propose()` returns is used verbatim; this file adds nothing to and removes nothing from that
verdict. That is the whole point of importing the proven function instead of its parts.

★ THE DEGRADATION ACCOUNTING IS NEVER SWALLOWED. `findings_reader.findings_report()` returns
shard/degradation bookkeeping alongside `rows` specifically so a caller ranking those rows can
never mistake "fewer findings" for "a healthier system" when the real cause is an unreadable
shard or a notes-root outage. This file prints that bookkeeping FIRST, loudly, before anything
else — see `_print_degradation_banner()` — and a `shards_expected == 0` (nothing has ever
reported) is stated as its own case, distinct from "0 problems found", so a bare run is never
falsely green.

WHAT CHANGED IN THIS PORT (generalisation, not a redesign):
  · `--recommendations-dir` help text's mention of `CLAUDEOPS_DRIVE` (the donor's env-var
    convention) updated to describe this repo's actual resolver (`shared/brain_root.py`).
  · `_selftest()`'s `from machine_token import get_machine_token` — `machine_token.py` is
    excluded from this port (the two-machine plane this product doesn't have) — replaced
    with `from emit_recommendation import get_machine_token`, the sibling module this repo
    already ships that carries the identical local-constant derivation.

Compatible with `/usr/bin/python3` (3.9) — no `X | None` union annotations, stdlib only.
Read-only over Hospital's findings store and fault_proposer/fault_ledger's history (never
writes to either); the ONLY store this file ever writes to is
`<brain>/state/recommendations/<altitude>.<machine>.jsonl`, and only through
`emit_recommendation()`.
"""
from __future__ import annotations   # keep annotations lazy for 3.9 compatibility

import argparse
import datetime
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import findings_reader                                              # noqa: E402 — READ ONLY
import fault_proposer                                                # noqa: E402 — the proven
                                                                       # altitude IP; never
                                                                       # modified, never
                                                                       # re-derived, see module
                                                                       # docstring.
from emit_recommendation import (emit_recommendation,                # noqa: E402
                                   RecommendationContractError)

PRODUCER = "recommend"   # this reasoner's OWN identity, distinct from the finding's producer
                          # (e.g. "system-health") — mirrors emit_recommendation's own worked
                          # example and matches every sibling script naming itself after its
                          # own file (backlog-health.py -> "backlog-health", etc.).


# ── STEP 1 — collapse the append-only union to "what does each identity look like now" ──────
def _parse_ts(ts):
    """Best-effort ISO-8601 parse for ordering same-fingerprint rows by recency. Falls back to
    the raw string on anything unparseable — string comparison on this system's own
    `_iso_now()` format (YYYY-MM-DDTHH:MM:SS+HH:MM) already sorts correctly for same-offset
    timestamps, so a parse failure degrades to "probably fine" rather than crashing the run
    over one bad `ts` field. Not a general ISO parser; this system's own emitters only ever
    write ONE shape (see emit_finding.py/emit_recommendation.py's `_iso_now()`)."""
    try:
        return datetime.datetime.fromisoformat(str(ts))
    except Exception:
        return None


def _latest_by_fingerprint(rows):
    """See module docstring's first ★. Returns {fingerprint: most_recent_row}."""
    latest = {}
    latest_key = {}
    for r in rows:
        fp = r.get("fingerprint")
        if not fp or not isinstance(fp, str):
            continue   # a malformed row with no identity cannot be reasoned about at all
        parsed = _parse_ts(r.get("ts"))
        cmp_key = (0, parsed) if parsed is not None else (1, str(r.get("ts", "")))
        prev_key = latest_key.get(fp)
        if prev_key is None or cmp_key >= prev_key:
            latest[fp] = r
            latest_key[fp] = cmp_key
    return latest


# ── STEP 2 — ask fault_proposer's proven grammar what altitude each candidate deserves ──────
def _reason_one(row):
    """One non-OK finding -> (proposal_dict, job_name, display) — or None if fault_proposer
    itself refuses (no citable evidence; `propose()` returning `{}` is a first-class outcome,
    not an error — see fault_proposer.py's "THE REFUSAL GATE"). Never re-derives altitude
    grammar or the DECISION gate; both come from calling fault_proposer directly. See module
    docstring's ★★ for exactly what identity shape is built here and why."""
    fp = row.get("fingerprint")
    if not fp or not isinstance(fp, str):
        return None
    labels = row.get("labels") or {}
    if not isinstance(labels, dict):
        labels = {}
    # resolve_job_identity's `fp:` branch exists FOR exactly this shape (a fingerprint-
    # identified record with a `labels` dict) — see its own docstring. Not re-derived; called.
    job_name, display = fault_proposer.resolve_job_identity(f"fp:{fp}", {"labels": labels})
    # age_s intentionally omitted (defaults to 0.0 -> propose() renders "open_for": "unknown").
    # A real age would have to come from fault_ledger's machine-local faults.json, which this
    # file stays read-only over — "unknown" is an honest gap, not a fabricated number.
    p = fault_proposer.propose(job=f"fp:{fp}", state="", job_name=job_name)
    if not p:
        return None
    return p, job_name, display


# ── STEP 3 — emit through the ONE validating writer, or preview under --dry-run ─────────────
def build_recommendations(report, recommendations_dir=None, dry_run=False, producer=PRODUCER):
    """`report` = findings_reader.findings_report()'s return dict. Never raises: one bad
    candidate costs only that candidate (own try/except per row). Returns a summary dict the
    caller renders."""
    rows = report.get("rows") or []
    latest = _latest_by_fingerprint(rows)
    candidates = [r for r in latest.values() if r.get("status") != "OK"]

    summary = {
        "considered": len(latest), "candidates": len(candidates),
        "proposed": 0, "decisions": 0, "refused": 0, "errors": 0, "written": [],
    }

    for row in sorted(candidates, key=lambda r: str(r.get("fingerprint", ""))):
        fp = row.get("fingerprint")
        try:
            result = _reason_one(row)
        except Exception as e:
            summary["errors"] += 1
            summary["written"].append({"error": f"{type(e).__name__}: {e}",
                                         "row_fingerprint": fp})
            continue

        if result is None:
            summary["refused"] += 1
            continue

        p, job_name, display = result

        if p.get("altitude") == "DECISION":
            summary["decisions"] += 1
        else:
            summary["proposed"] += 1

        # labels = this RECOMMENDATION's identity (distinct from the source finding's own
        # labels, which are preserved verbatim in payload below for full traceability).
        rec_labels = {
            "job": str(job_name),
            "check": str((row.get("labels") or {}).get("check", "")),
            "source_producer": str(row.get("producer", "")),
            "source_fingerprint": str(fp),
        }
        payload = {
            "proposal": p,
            "source_finding": {
                "producer": row.get("producer"), "status": row.get("status"),
                "summary": row.get("summary"), "ts": row.get("ts"),
                "labels": row.get("labels"),
            },
        }
        summary_text = f"{display}: {p.get('action', '')}"

        if dry_run:
            summary["written"].append({
                "dry_run": True, "altitude": p.get("altitude"), "job_name": job_name,
                "action": p.get("action"), "evidence": [fp],
            })
            continue

        try:
            out = emit_recommendation(
                producer=producer, altitude=p["altitude"], action=p["action"],
                evidence=[fp], labels=rec_labels, summary=summary_text,
                payload=payload, recommendations_dir=recommendations_dir,
            )
            summary["written"].append(out)
        except RecommendationContractError as e:
            summary["errors"] += 1
            summary["written"].append({"error": str(e), "row_fingerprint": fp})

    return summary


# ── output — degradation ALWAYS surfaced first, never swallowed (see module docstring ★) ────
def _print_degradation_banner(report):
    if report.get("degraded"):
        print("=" * 78)
        print("DEGRADED READ — this recommendation set is PARTIAL, not complete.")
        print(f"  shards_expected={report.get('shards_expected')}  "
              f"shards_read={len(report.get('shards_read') or [])}  "
              f"shards_missing={report.get('shards_missing')}")
        if report.get("bad_lines"):
            print(f"  bad_lines={report.get('bad_lines')}")
        print(f"  drive_available={report.get('drive_available')}")
        print(f"  reason: {report.get('degraded_reason', '')}")
        print("  Recommendations below are computed from what COULD be read. The ABSENCE of a")
        print("  recommendation in this run is NOT evidence of health while this banner shows.")
        print("=" * 78)
    else:
        print(f"findings read: {len(report.get('shards_read') or [])}/"
              f"{report.get('shards_expected', 0)} shard(s), clean (no missing shards, "
              f"no bad lines).")


def _render_summary(summary, dry_run):
    print(f"considered {summary['considered']} distinct finding identity(ies) "
          f"(latest row per fingerprint)")
    print(f"  candidates (status != OK) : {summary['candidates']}")
    print(f"  proposed (fix, non-parked): {summary['proposed']}")
    print(f"  DECISION  (parked — NO fix): {summary['decisions']}")
    print(f"  refused (no evidence)     : {summary['refused']}")
    print(f"  errors                    : {summary['errors']}")
    if dry_run and summary["written"]:
        print("\n[--dry-run] nothing written to the recommendations store. Preview:")
    for w in summary["written"]:
        print(f"  - {w}")


# ── CLI ───────────────────────────────────────────────────────────────────────────────────
def _build_argparser():
    ap = argparse.ArgumentParser(
        prog="recommend.py",
        description="GROUND-ALTITUDE reasoner: read Hospital's findings union, ask "
                     "fault_proposer.py for an altitude verdict on each currently-wrong "
                     "finding, write through emit_recommendation.py. PROPOSE-ONLY — never "
                     "applies, retries, or fixes anything. A bare invocation runs a real "
                     "sweep against the real findings/recommendations stores.",
    )
    ap.add_argument("--selftest", action="store_true",
                     help="run the built-in self-test against temp dirs only, and exit; "
                          "ignores all other flags; never touches real state")
    ap.add_argument("--dry-run", action="store_true",
                     help="reason and print what WOULD be written; never calls "
                          "emit_recommendation (no write, anywhere)")
    ap.add_argument("--producer", default=PRODUCER,
                     help=f"the identity this reasoner writes under (default {PRODUCER!r})")
    ap.add_argument("--recommendations-dir", default=None,
                     help="override emit_recommendation's target dir — isolation for testing; "
                          "does NOT affect where findings are read from (that comes from "
                          "shared/brain_root.py's resolved notes root, same resolver every "
                          "sibling tool in this repo uses)")
    ap.add_argument("--json", dest="as_json", action="store_true",
                     help="print the run summary as JSON instead of prose")
    return ap


def _selftest():
    """In-process self-test against temp dirs ONLY. Rebinds sibling modules' directory
    globals directly (findings_reader.FINDINGS_DIR, fault_proposer.PARK_FILE/PULSE_STATE)
    rather than relying on env vars, because those modules read their env var (or resolve the
    brain root) at IMPORT time — by the time --selftest runs, this process has already
    imported them once, so a freshly-set env var would silently do nothing. This is exactly
    the "rebind module globals if you need fuller isolation" case this port's own tests need.
    Restores every rebound global in a `finally`, so a selftest run leaves the process exactly
    as it found it for any code that runs after.
    """
    import tempfile
    import emit_finding as EF   # test-fixture builder ONLY — never used in the main reasoning
                                 # path above; imported here, inside the test, so a normal run
                                 # of this file never even loads it.
    import fault_ledger as FL   # SAME reason: isolation-only import. fault_proposer.py's own
                                 # `import fault_ledger as FL` binds the identical module
                                 # object, so rebinding FL's globals here is visible to
                                 # fault_proposer's calls too — there is only ever one loaded
                                 # copy of this module per process.

    # ⚠ fault_ledger.py's machine-local paths (STATE_DIR / LEDGER / INCIDENTS) have NO env-var
    # override at all — unlike every notes-root-resident store in this repo. `fault_proposer.
    # propose()`'s ORGANISM check (`choose_altitude()`'s cohort scan) reads
    # `FL.recurrence_all()`, which reads those exact paths. A selftest that isolated only
    # `findings_reader.FINDINGS_DIR` and `fault_proposer.PARK_FILE`/`PULSE_STATE` would still
    # leak THIS MACHINE'S REAL incident history in, which could make `choose_altitude()`'s
    # ORGANISM branch (checked FIRST, keyed on the COHORT's size, not the current fault's own
    # history) fire for a completely synthetic, unrelated test finding. Fixed by rebinding
    # `fault_ledger`'s globals the same way `PARK_FILE`/`PULSE_STATE` already are below — this
    # module is never edited, only its already-public attributes are pointed at scratch paths
    # for the lifetime of this test.
    orig_findings_dir = findings_reader.FINDINGS_DIR
    orig_park_file = fault_proposer.PARK_FILE
    orig_pulse_state = fault_proposer.PULSE_STATE
    orig_fl_state_dir = FL.STATE_DIR
    orig_fl_ledger = FL.LEDGER
    orig_fl_incidents = FL.INCIDENTS
    orig_fl_incident_shard_dir = FL.INCIDENT_SHARD_DIR

    tmp = tempfile.mkdtemp(prefix="recommend-selftest-")
    findings_dir = os.path.join(tmp, "findings")
    rec_dir = os.path.join(tmp, "recommendations")
    park_file = os.path.join(tmp, "park.json")           # deliberately NOT created -> empty
    pulse_state = os.path.join(tmp, "pulse-state.json")   # deliberately NOT created -> empty

    try:
        findings_reader.FINDINGS_DIR = findings_dir
        fault_proposer.PARK_FILE = park_file
        fault_proposer.PULSE_STATE = pulse_state
        FL.STATE_DIR = os.path.join(tmp, "fl-state")
        FL.LEDGER = os.path.join(FL.STATE_DIR, "faults.json")
        FL.INCIDENTS = os.path.join(FL.STATE_DIR, "incidents.jsonl")
        FL.INCIDENT_SHARD_DIR = os.path.join(tmp, "fl-incident-shards")   # empty -> 0 shards

        # ── bare-invocation-not-falsely-green, case A: no findings store at all ──
        report0 = findings_reader.findings_report()
        assert report0["shards_expected"] == 0, "expected 0 shards before any write"
        assert not report0["degraded"], "an absent-but-reachable findings dir is NOT degraded"
        print("case A (no findings store yet): shards_expected=0, degraded=False — correct, "
              "distinct from '0 problems found'")

        # ── write ONE normal (non-parked) finding, via the real emit_finding() so the
        # fixture's fingerprint is computed exactly the way production data's is ──
        row_normal = EF.emit_finding(
            producer="selftest-detector", status="ERROR", scanned_n=1,
            labels={"job": "selftest-detector", "check": "smoke", "target": "normal-job-y"},
            summary="synthetic finding for recommend.py selftest",
            findings_dir=findings_dir,
        )

        # ── write ONE finding whose resolved job name IS parked, 10y out (mirrors a real
        # deliberate park so PARK_HORIZON_S's 7-day floor is cleared) ──
        row_parked = EF.emit_finding(
            producer="selftest-detector", status="ERROR", scanned_n=1,
            labels={"job": "selftest-detector", "check": "smoke", "target": "parked-job-x"},
            summary="synthetic finding for a job a human deliberately parked",
            findings_dir=findings_dir,
        )
        with open(park_file, "w") as f:
            json.dump({"parked-job-x": __import__("time").time() + 10 * 365 * 86400}, f)

        report1 = findings_reader.findings_report()
        assert report1["rows"], "expected non-empty rows after writing two findings"  # ★
        assert len(report1["rows"]) == 2, f"expected 2 rows, got {len(report1['rows'])}"
        assert not report1["degraded"], "two clean writes must not read as degraded"

        summary1 = build_recommendations(report1, recommendations_dir=rec_dir, dry_run=False,
                                           producer="selftest-recommend")
        assert summary1["candidates"] == 2, summary1
        assert summary1["proposed"] == 1, summary1
        assert summary1["decisions"] == 1, summary1
        assert summary1["errors"] == 0, summary1

        # ── verify what actually landed on disk, not just the in-memory summary ──
        from emit_recommendation import get_machine_token
        machine = get_machine_token()
        instance_path = os.path.join(rec_dir, f"INSTANCE.{machine}.jsonl")
        decision_path = os.path.join(rec_dir, f"DECISION.{machine}.jsonl")
        with open(instance_path) as f:
            inst_lines = [json.loads(ln) for ln in f if ln.strip()]
        with open(decision_path) as f:
            dec_lines = [json.loads(ln) for ln in f if ln.strip()]
        assert inst_lines, "expected at least one INSTANCE recommendation on disk"           # ★
        assert dec_lines, "expected at least one DECISION recommendation on disk"            # ★
        assert inst_lines[0]["evidence"] == [row_normal["fingerprint"]], inst_lines[0]
        assert "no fix" not in inst_lines[0]["action"].lower()  # sanity: it IS a fix proposal
        assert dec_lines[0]["evidence"] == [row_parked["fingerprint"]], dec_lines[0]
        assert dec_lines[0]["action"].startswith("NO ACTION"), dec_lines[0]
        assert "parked-job-x" in dec_lines[0]["action"], dec_lines[0]
        print("case B (real finding -> real recommendation): INSTANCE recommendation citing "
              f"fingerprint {row_normal['fingerprint'][:16]}... — OK")
        print("case C (parked job -> DECISION, never a fix): action = "
              f"{dec_lines[0]['action']!r} — OK")

        # ── force a degraded read: a shard with one malformed line alongside a good one ──
        degraded_shard = os.path.join(findings_dir, "selftest-detector.junk-machine.jsonl")
        with open(degraded_shard, "a") as f:
            f.write(json.dumps({"producer": "selftest-detector", "machine": "junk-machine",
                                  "schema_version": 1, "ts": "2026-01-01T00:00:00+00:00",
                                  "scanned_n": 1, "status": "OK", "summary": "", "rc": 0,
                                  "labels": {"job": "x"}, "fingerprint": "deadbeef"}) + "\n")
            f.write("THIS IS NOT JSON {{{\n")

        report2 = findings_reader.findings_report()
        assert report2["degraded"], "a malformed line must flip degraded=True"              # ★
        assert report2["bad_lines"], "bad_lines must be non-empty when degraded via bad lines"
        print(f"case D (degraded read): degraded=True, bad_lines={report2['bad_lines']} — OK")

        # ── refusal is a first-class outcome, not silently dropped: assert the counters
        # actually distinguish it from a normal proposal/decision (both already exercised
        # above) rather than trusting `if result is None` was ever reached ──
        assert summary1["refused"] == 0, "neither fixture should have been refused"

        print("recommend.py self-test PASSED")
    finally:
        findings_reader.FINDINGS_DIR = orig_findings_dir
        fault_proposer.PARK_FILE = orig_park_file
        fault_proposer.PULSE_STATE = orig_pulse_state
        FL.STATE_DIR = orig_fl_state_dir
        FL.LEDGER = orig_fl_ledger
        FL.INCIDENTS = orig_fl_incidents
        FL.INCIDENT_SHARD_DIR = orig_fl_incident_shard_dir


def main(argv):
    ap = _build_argparser()
    args = ap.parse_args(argv)

    if args.selftest:
        _selftest()
        return 0

    report = findings_reader.findings_report()
    _print_degradation_banner(report)

    if report.get("shards_expected", 0) == 0 and not report.get("degraded"):
        print("no findings store found (0 shards) — nothing has EVER reported to Hospital "
              "here. This is NOT the same as '0 problems found': nothing has been examined.")
        return 0

    summary = build_recommendations(report, recommendations_dir=args.recommendations_dir,
                                     dry_run=args.dry_run, producer=args.producer)

    if args.as_json:
        print(json.dumps({"degraded": report.get("degraded"),
                           "degraded_reason": report.get("degraded_reason"),
                           **summary}, indent=2, sort_keys=True, default=str))
    else:
        _render_summary(summary, args.dry_run)

    return 1 if summary["errors"] else 0


if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "system", "tools")))
    from utf8_stdio import force_utf8_stdio
    force_utf8_stdio()
    sys.exit(main(sys.argv[1:]))

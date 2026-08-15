#!/usr/bin/env python3
"""
ingest_coverage.py — the deterministic completeness GATE for ingestion runners.

PORTED (2026-08-14) from claudeops-config's system/tools/ingest_coverage.py. This session's identity
grep found zero personal/account content — the only change from the donor is `NOTIFY`'s path, which
moved because `notify-send.sh` lives at `shared/notify/notify-send.sh` in this repo, not
co-located in `system/tools/` (see that file's own port for why).

Enforces completeness = native-id set-diff (L1 · Critical) at the RUNNER level, where it can be
DETERMINISTIC — a bash runner calls this after the real work, every run, with a source id-list and
the captured id-list. It does NOT depend on a model emitting anything correctly.

Wraps `ingest_setdiff.verify_completeness` (the proven set-diff) and adds runner-appropriate
behaviour:
  - clean       -> exit 0, quiet.
  - LOSS        -> exit 3, LOUD: print + best-effort critical notify + append a persistent
                  dropped-ids log so nothing is lost silently.
  - source unreadable -> exit 2 (a HARNESS/tool error, distinct from a data-loss finding).

ALARM-ONLY by design: this gate does NOT itself advance/block the runner's marker or exit code —
the runner decides policy. That keeps it from ever bricking a live pipeline; its job is to make a
silent drop IMPOSSIBLE to miss.

Usage:
  python3 ingest_coverage.py --source-file src.txt --captured-file cap.txt --skill some-runner
"""

import argparse
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ingest_setdiff import verify_completeness  # the proven native-id set-diff

DROP_LOG = os.environ.get(
    "INGEST_COVERAGE_DROPLOG",
    os.path.expanduser("~/.claude/run/ingest-coverage-drops.log"),
)
CODE_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
NOTIFY = os.path.join(CODE_ROOT, "shared", "notify", "notify-send.sh")


def _read_ids(path):
    with open(path, encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip()]


def _notify_critical(msg):
    """Best-effort critical alarm — never raises (a notify failure must not break the gate)."""
    if os.environ.get("INGEST_COVERAGE_NOTIFY") == "off":
        return  # test/dry-run mode — never push a notification
    try:
        if os.path.isfile(NOTIFY):
            subprocess.run(["bash", NOTIFY, "--source", "ingest-coverage", "--priority", "critical",
                            "--title", "Ingest completeness LOSS", "--message", msg],
                           timeout=15, capture_output=True, text=True)
    except Exception:
        pass


def _log_drop(skill, result):
    """Append the drop finding to a persistent log so a loss is never silent."""
    try:
        os.makedirs(os.path.dirname(DROP_LOG), exist_ok=True)
        with open(DROP_LOG, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} [{skill}] "
                    f"missing={result.missing} dupes={result.dupes} alien={result.alien}\n")
    except OSError:
        pass


def main(argv=None):
    ap = argparse.ArgumentParser(description="Deterministic completeness gate for ingest runners.")
    ap.add_argument("--source-file", required=True, help="native-ids in scope BEFORE the run")
    ap.add_argument("--captured-file", required=True, help="native-ids the run accounted for")
    ap.add_argument("--skill", default="ingest")
    ap.add_argument("--declared-count", type=int, default=None)
    args = ap.parse_args(argv)

    # A missing/unreadable SOURCE is a harness error (exit 2), NOT a data-loss finding. A missing
    # CAPTURED file we treat as "captured nothing" -> a real loss signal.
    try:
        source = _read_ids(args.source_file)
    except OSError as e:
        print(f"[ingest_coverage] TOOL ERROR: cannot read source-file: {e}", file=sys.stderr)
        return 2
    try:
        captured = _read_ids(args.captured_file)
    except OSError:
        captured = []

    result = verify_completeness(source, captured, skill=args.skill,
                                 declared_count=args.declared_count)
    print(result.report())

    if result.ok:
        return 0

    # LOSS (or unpinned denominator) — make it loud and persistent.
    _log_drop(args.skill, result)
    _notify_critical(
        f"INGEST COMPLETENESS [{args.skill}]: {len(result.missing)} record(s) DROPPED "
        f"(missing={result.missing[:5]}{'...' if len(result.missing) > 5 else ''}). "
        f"See {DROP_LOG}."
    )
    if not result.denominator_ok:
        return 2   # denominator mismatch = a setup/harness problem
    return 3       # genuine data-loss finding


if __name__ == "__main__":
    sys.exit(main())

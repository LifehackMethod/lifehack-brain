#!/usr/bin/env python3
"""
ingest_setdiff.py — the completeness enforcement mechanism for ingestion skills.

PORTED (2026-08-14) from claudeops-config's system/tools/ingest_setdiff.py — a straight copy. This
session's identity grep found zero personal/account content (no DRIVE literal, no hardcoded account),
and the one path it writes to (`~/.claude/run/...`, a generic per-user Claude Code runtime directory)
carries no personal identifier. Ported alongside `ingest_coverage.py`, which imports it directly
(`from ingest_setdiff import verify_completeness`) — that file is on this lane's file list; this one
is its hard dependency and does not function without it, so it travels with it even though it wasn't
separately named in the assignment.

The rule (all L1 · Critical, this repo's own ingest doctrine): an ingesting skill MUST verify
completeness as a native-id SET-DIFF (missing / dupes / alien) at the fan-out return boundary — NOT a
count. A count can't tell "all 10 present" from "2 dropped + 2 duplicated"; a set-diff can.

This is the production mechanism a skill calls at its loss-point:
  - PIN the denominator (source's own N) first, then
  - SET-DIFF captured native-ids against the pinned source ids, then
  - FAIL LOUD (exit 3) + stamp a receipt if anything is missing / duplicated / alien.

Library use (the skill calls this at its fan-out return boundary):
    from ingest_setdiff import verify_completeness
    result = verify_completeness(source_ids, captured_ids, skill="ingest",
                                 declared_count=len(source_ids))
    if not result.ok:
        raise SystemExit(result.report())   # fail loud — never silently drop

CLI use (pipe two id lists):
    python3 ingest_setdiff.py --source-file src_ids.txt --captured-file out_ids.txt
    exit 0 = complete · exit 2 = bad denominator · exit 3 = LOSS DETECTED

House style: stdlib-only · fail-loud · a receipt is stamped on every run so the check
is auditable (COMMITTED != ENFORCED — the receipt is the evidence the check actually ran).
"""

import argparse
import json
import os
import sys
import time


RECEIPT_DIR = os.environ.get(
    "INGEST_SETDIFF_RECEIPTS",
    os.path.expanduser("~/.claude/run/ingest-setdiff"),
)


class CompletenessResult:
    def __init__(self, source_ids, captured_ids, skill, declared_count):
        self.skill = skill
        self.declared_count = declared_count
        self.source = frozenset(source_ids)
        # captured is a LIST (order irrelevant, but dupes matter) -> count them
        self.captured_list = list(captured_ids)
        self.captured_set = frozenset(self.captured_list)

        # Denominator pin: the declared N must match the real source id count.
        self.denominator_ok = (declared_count == len(self.source))

        # The three set-diff failure modes.
        self.missing = sorted(self.source - self.captured_set)      # dropped — the killer
        self.alien = sorted(self.captured_set - self.source)        # appeared from nowhere
        seen = {}
        for cid in self.captured_list:
            seen[cid] = seen.get(cid, 0) + 1
        self.dupes = sorted(c for c, n in seen.items() if n > 1)    # double-counted

    @property
    def ok(self):
        return self.denominator_ok and not (self.missing or self.dupes or self.alien)

    def count_only_would_pass(self):
        """The trap: would a naive count check have waved this through?
        True when in==out by count but the set-diff still finds a problem."""
        return (len(self.captured_list) == len(self.source)) and bool(
            self.missing or self.dupes or self.alien
        )

    def report(self):
        if self.ok:
            return (f"COMPLETE [{self.skill}]: {len(self.source)} in / "
                    f"{len(self.captured_list)} out - denominator pinned - no loss.")
        parts = [f"INCOMPLETE [{self.skill}]: LOSS DETECTED — data may be silently dropped."]
        if not self.denominator_ok:
            parts.append(f"  denominator UNPINNED: declared={self.declared_count} "
                         f"but source has {len(self.source)} ids")
        if self.missing:
            parts.append(f"  MISSING (dropped): {self.missing}")
        if self.dupes:
            parts.append(f"  DUPES (double-counted): {self.dupes}")
        if self.alien:
            parts.append(f"  ALIEN (not in source): {self.alien}")
        if self.count_only_would_pass():
            parts.append("  a naive COUNT check would have PASSED this — the trap the rule exists for.")
        return "\n".join(parts)

    def receipt(self):
        return {
            "skill": self.skill,
            "declared_count": self.declared_count,
            "source_count": len(self.source),
            "captured_count": len(self.captured_list),
            "captured_distinct": len(self.captured_set),
            "denominator_ok": self.denominator_ok,
            "missing": self.missing,
            "dupes": self.dupes,
            "alien": self.alien,
            "ok": self.ok,
        }


def _stamp_receipt(result):
    """Stamp an auditable receipt so the check is provably-ran (not just present)."""
    try:
        os.makedirs(RECEIPT_DIR, exist_ok=True)
        rec = result.receipt()
        rec["stamped_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        path = os.path.join(RECEIPT_DIR, f"{result.skill}-last.json")
        with open(path, "w") as f:
            json.dump(rec, f, indent=2)
        return path
    except OSError:
        return None  # a receipt failure must never break the check itself


def verify_completeness(source_ids, captured_ids, skill="unknown", declared_count=None):
    """The library entry point an ingest skill calls at its fan-out return boundary."""
    if declared_count is None:
        declared_count = len(frozenset(source_ids))
    result = CompletenessResult(source_ids, captured_ids, skill, declared_count)
    _stamp_receipt(result)
    return result


def _read_ids(path):
    with open(path, encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip()]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Native-id set-diff completeness check for ingestion.")
    ap.add_argument("--source-file", required=True, help="file of source native-ids, one per line")
    ap.add_argument("--captured-file", required=True, help="file of captured native-ids, one per line")
    ap.add_argument("--skill", default="cli")
    ap.add_argument("--declared-count", type=int, default=None)
    args = ap.parse_args(argv)

    source = _read_ids(args.source_file)
    captured = _read_ids(args.captured_file)
    result = verify_completeness(source, captured, skill=args.skill,
                                 declared_count=args.declared_count)
    print(result.report())
    if not result.denominator_ok:
        return 2
    if not result.ok:
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())

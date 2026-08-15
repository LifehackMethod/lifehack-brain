#!/usr/bin/env python3
"""recommendations_reader.py — the union READER over Efficiency's recommendation store.
Sibling to `findings_reader.py` (READ THAT FIRST — this copies its shape on purpose: same
coverage/degradation contract, same "an unreadable shard is a finding, not a skip" rule,
applied to recommendations instead of findings). `findings_reader.py` is owned by another
part of this pipeline and is NEVER imported from or modified here — this is a parallel,
independently-owned reader over a DIFFERENT store, built the same way deliberately: a second
divergent shape for the same question ("what does the union of my shards say?") would be
exactly the fragmentation Hospital/Efficiency both exist to end.

WHERE RECOMMENDATIONS LIVE. `emit_recommendation.py` shards by
`<brain>/state/recommendations/<altitude>.<machine>.jsonl` (see that module's docstring — the
shard key is ALTITUDE, the axis a human reviews by, not producer), where `<brain>` is resolved
through `shared/brain_root.py`. This reader globs every `*.jsonl` file directly under
`state/recommendations/` — NOT recursive. That matters: the disposition store
(`recommendation_disposition.py`) deliberately lives one directory LOWER, at
`state/recommendations/dispositions/dispositions.<machine>.jsonl`, specifically so a
non-recursive glob here can never mistake a disposition shard for a recommendation shard. Two
stores, two directories, one glob depth apart — cheaper than teaching this reader an
exclude-list, and it can't silently rot if a third store shows up later at the top level (any
misplaced future file just fails altitude validation loudly downstream instead of silently
entering `rows`).

Compatible with `/usr/bin/python3` (3.9) — no `X | None` union annotations, stdlib only.
Read-only: never writes, never touches `emit_recommendation.py` or `findings_reader.py` (both
owned elsewhere).
"""
from __future__ import annotations   # /usr/bin/python3 here is 3.9 — keep annotations lazy

import glob
import json
import os
import sys

# ── WHERE RECOMMENDATIONS LIVE — resolved through the ONE brain-root resolver, never guessed. ──
# MUST resolve identically to emit_recommendation.py's RECOMMENDATIONS_DIR (same resolver, same
# relative path under the root) or a reader would look somewhere the writer never wrote. Both
# modules call `shared/brain_root.py`'s `resolve_brain_root()` directly rather than sharing a
# constant, because that resolver IS the one shared thing between them — see that module's own
# docstring.
_HERE = os.path.dirname(os.path.abspath(__file__))
CODE_ROOT = os.path.dirname(os.path.dirname(_HERE))          # system/tools/../.. -> repo root
_SHARED = os.path.join(CODE_ROOT, "shared")
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)
try:
    from brain_root import resolve_brain_root          # shared/brain_root.py
    _ROOT_SOURCE, DRIVE = resolve_brain_root()
except Exception:
    _ROOT_SOURCE, DRIVE = None, None

# None when no root is configured. `recommendations_report()` below treats that exactly like an
# unreachable store — degraded, honestly reported, never a crash and never invented rows.
RECOMMENDATIONS_DIR = os.path.join(DRIVE, "state", "recommendations") if DRIVE else None


def _read_jsonl(path):
    """Return (rows, ok, bad_lines) — identical contract to findings_reader._read_jsonl
    (see that function's docstring for the ok=False vs FileNotFoundError distinction).
    Reproduced here rather than imported: findings_reader.py is owned elsewhere and this is a
    leading-underscore private helper, not an exported contract."""
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
        return rows, True, 0
    except Exception:
        return rows, False, 0


def recommendations_report(fingerprint="", altitude=""):
    """The UNION read across every `<ALTITUDE>.<machine>.jsonl` shard directly under
    state/recommendations/, plus the missing-shard, bad-line, and degradation accounting a
    ranking layer depends on being honest about. Never raises; every failure mode degrades
    to something narrower and SAYS so in the returned dict — see findings_reader.
    findings_report()'s docstring for the full rationale, reproduced here verbatim in shape.

    Keys: rows, shards_expected, shards_read, shards_missing, bad_lines, degraded,
    degraded_reason, drive_available — SAME semantics as findings_report(), applied to the
    recommendations store instead of the findings store. `drive_available` is False both when
    no brain root is configured at all and when a configured root is unreachable — a caller
    only ever handles ONE degraded shape, same as findings_report().
    """
    report = {
        "rows": [], "shards_expected": 0, "shards_read": [], "shards_missing": [],
        "bad_lines": {}, "degraded": False, "degraded_reason": "", "drive_available": True,
    }

    paths = []
    try:
        if DRIVE is None:
            # No brain root configured at all — the honest answer is "nothing to read yet",
            # not a crash and not an invented empty-but-clean result. Same code path a
            # genuinely unreachable root takes below, so callers only ever handle ONE
            # degraded shape.
            raise OSError("no notes root configured — brain_root.resolve_brain_root() returned "
                          "NOT-SET (fix: python3 shared/brain_root.py --set <folder>)")
        if RECOMMENDATIONS_DIR and os.path.isdir(RECOMMENDATIONS_DIR):
            # non-recursive on purpose — see module docstring "WHERE RECOMMENDATIONS LIVE"
            # for why the disposition store one level down is deliberately out of reach here.
            paths = sorted(
                p for p in glob.glob(os.path.join(RECOMMENDATIONS_DIR, "*.jsonl"))
                if os.path.isfile(p)
            )
        elif not os.path.isdir(DRIVE):
            # The notes root itself is gone, not just the (optional, first-run-absent)
            # recommendations dir under it — a genuinely unreachable mount, not "no
            # recommendations yet".
            raise OSError(f"notes root not reachable: {DRIVE}")
        # else: the root is up, state/recommendations/ just doesn't exist yet — 0 shards, not
        # an error (legitimate first-run state, same as findings_report()).
    except Exception as e:
        report["drive_available"] = False
        report["degraded"] = True
        report["degraded_reason"] = (
            f"notes root unavailable ({e}) — NO recommendations available this run "
            "(recommendations have no local fallback; emit_recommendation.py's write "
            "raises rather than falling back, so there is nothing else to read)")
        return _filter_report(report, fingerprint, altitude)

    report["shards_expected"] = len(paths)
    all_rows = []
    for p in paths:
        name = os.path.basename(p)
        rows, ok, bad = _read_jsonl(p)
        if not ok:
            report["shards_missing"].append(name)
            continue
        report["shards_read"].append(name)
        all_rows.extend(rows)
        if bad:
            report["bad_lines"][name] = bad

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

    report["rows"] = all_rows
    return _filter_report(report, fingerprint, altitude)


def _filter_report(report, fingerprint, altitude):
    """Apply the fingerprint/altitude filter to an already-built report's rows, leaving
    every coverage/degradation field untouched — the filter narrows WHAT you see, never the
    truthfulness of how much of the store was actually read."""
    if not fingerprint and not altitude:
        return report
    rows = [r for r in report["rows"]
            if (not fingerprint or r.get("fingerprint") == fingerprint)
            and (not altitude or r.get("altitude") == altitude)]
    report = dict(report)
    report["rows"] = rows
    return report


def recommendations(fingerprint="", altitude=""):
    """Convenience: just the rows list, filtered. Callers that need the coverage/degradation
    picture (a ranking layer MUST) call recommendations_report() directly — same split as
    findings_reader.findings()/findings_report()."""
    return recommendations_report(fingerprint, altitude).get("rows", [])


if __name__ == "__main__":
    fp = ""
    alt = ""
    for arg in sys.argv[1:]:
        if arg.startswith("--fingerprint="):
            fp = arg.split("=", 1)[1]
        elif arg.startswith("--altitude="):
            alt = arg.split("=", 1)[1]
    r = recommendations_report(fingerprint=fp, altitude=alt)
    print(json.dumps(r, indent=2, sort_keys=True))

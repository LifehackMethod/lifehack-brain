#!/usr/bin/env python3
"""findings_reader.py — the union READER over Hospital's findings store.

WHAT THIS IS. `emit_finding.py` writes ONE finding per detector run as an appended JSONL line
into `<brain>/state/findings/<producer>.<machine>.jsonl` — sharded per PRODUCER *and* per
MACHINE, on purpose (see that module's docstring: a shared file that only varies a "machine"
field inside each line still forks when more than one machine reads it back at once — a field
inside the file does not stop the file itself from forking). Sharding by filename is what
holds; nothing else reads the union of those shards back. This module is that reader.

THE ONE RULE THIS FILE EXISTS TO ENFORCE: an unreadable shard is a FINDING, not a skip. A
caller that ranks `rows` to answer "what is wrong?" must never be handed a quietly-smaller
list that looks the same as "everything else is fine" — that is a partial answer wearing a
complete one's clothes, and it is worse than an error because it gets acted on. So this module
never returns just a list; `findings_report()` always returns the coverage picture alongside
the rows, and `degraded` is true whenever that picture is known-incomplete for ANY reason: the
brain root unreachable (or not configured at all), a shard file that couldn't be opened at all,
or a shard that opened fine but contained one or more malformed JSON lines inside it. A
half-corrupt shard is still credited for its good lines — dropping the whole shard over one bad
line would itself be a silent shrink — but `bad_lines` names the shard and the count, and
`degraded` still flips true, because the ranking layer must know its input was not clean even
though it got *something*.

Compatible with `/usr/bin/python3` (3.9) — no `X | None` union annotations, stdlib only.
Read-only: never writes, never touches `emit_finding.py`, `findings_deadman.py`, or
`emit_status.py` (whichever of those exist in this repo today — this module only imports from
them where useful).
"""
from __future__ import annotations   # /usr/bin/python3 here is 3.9 — keep annotations lazy

import glob
import json
import os
import sys

# ── WHERE FINDINGS LIVE — resolved through the ONE brain-root resolver, never guessed. ──────
# MUST resolve identically to emit_finding.py's FINDINGS_DIR (same resolver, same relative path
# under the root) or a reader would look somewhere the writer never wrote. Both modules call
# `shared/brain_root.py`'s `resolve_brain_root()` directly rather than sharing a constant,
# because that resolver IS the one shared thing between them — see that module's own docstring.
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

# None when no root is configured. `findings_report()` below treats that exactly like an
# unreachable store — degraded, honestly reported, never a crash and never invented rows.
FINDINGS_DIR = os.path.join(DRIVE, "state", "findings") if DRIVE else None


def _read_jsonl(path):
    """Return (rows, ok, bad_lines).

    ok=False means the PATH itself could not be opened at all — permission-denied (a
    chmod'd shard), or a flaky-mount failure mode — and the caller MUST treat that as a
    missing shard, never as an empty (and therefore silently-lower-count) one.

    A missing FILE (FileNotFoundError) is NOT a failure — the glob that produced `path`
    already proved the file existed at listing time; treating a since-vanished file as ok=True,
    rows=[] rather than a hard failure is deliberate.

    bad_lines counts malformed JSON lines inside an otherwise-openable file — these are
    skipped from `rows` but NEVER silently dropped from the caller's picture; see module
    docstring, requirement 3."""
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


def findings_report(fingerprint="", producer=""):
    """The UNION read across every `<producer>.<machine>.jsonl` shard in state/findings/,
    plus the missing-shard, bad-line, and degradation accounting the ranking layer depends on
    being honest about. Never raises; every failure mode degrades to something narrower and
    SAYS so in the returned dict, rather than silently returning a smaller `rows` list that
    looks the same as "nothing else is wrong".

    Keys:
      rows              parsed finding dicts (each already a full envelope + payload dict, as
                         written by emit_finding.py), filtered by fingerprint/producer if given
      shards_expected   how many *.jsonl paths the glob returned (0 if state/findings/ is
                         empty/absent but the brain root IS reachable — a legitimate first-run
                         state, not a failure)
      shards_read       shard filenames that opened, even if they also had bad_lines — a shard
                         is "read" if SOME of it landed; see bad_lines for how much didn't
      shards_missing    shard filenames the glob found but could NOT be opened at ALL — a
                         chmod'd or permission-denied shard shows up HERE, never as a quietly
                         lower shards_expected and never silently absent from shards_read
      bad_lines         {shard_filename: malformed_line_count} — only shards with >=1 bad
                         line appear here; a shard with zero bad lines is not a key at all
      degraded          True whenever the picture is known-incomplete: drive_available is
                         False, OR shards_missing is non-empty, OR bad_lines is non-empty —
                         the signal a ranking layer must surface, never swallow
      degraded_reason   human-readable why, empty string when not degraded
      drive_available   False if the notes root itself could not be reached at all (no root
                         configured, or a configured root that is not reachable) — the one
                         case where shards_expected/read/missing are never even computed,
                         because the glob itself has nothing to walk. Name kept as
                         `drive_available` for interface stability even though "Drive" is no
                         longer the only kind of root this can be.
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
        if os.path.isdir(FINDINGS_DIR):
            paths = sorted(glob.glob(os.path.join(FINDINGS_DIR, "*.jsonl")))
        elif not os.path.isdir(DRIVE):
            # The root itself is gone, not just the (optional, first-run-absent) findings dir
            # under it — a genuinely unreachable mount, not "no findings yet".
            raise OSError(f"notes root not reachable: {DRIVE}")
        # else: the root is up, state/findings/ just doesn't exist yet — 0 shards, not an error.
    except Exception as e:
        report["drive_available"] = False
        report["degraded"] = True
        report["degraded_reason"] = (
            f"notes root unavailable ({e}) — NO findings history available this run "
            "(findings have no local fallback; emit_finding.py's write raises rather "
            "than falling back, so there is nothing else to read)")
        return _filter_report(report, fingerprint, producer)

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
    return _filter_report(report, fingerprint, producer)


def _filter_report(report, fingerprint, producer):
    """Apply the fingerprint/producer filter to a already-built report's rows, leaving every
    coverage/degradation field untouched — the filter narrows WHAT you see, never the
    truthfulness of how much of the store was actually read."""
    if not fingerprint and not producer:
        return report
    rows = [r for r in report["rows"]
            if (not fingerprint or r.get("fingerprint") == fingerprint)
            and (not producer or r.get("producer") == producer)]
    report = dict(report)
    report["rows"] = rows
    return report


def findings(fingerprint="", producer=""):
    """Convenience: just the rows list, filtered. Callers that need the coverage/degradation
    picture (the ranking layer MUST) call findings_report() directly."""
    return findings_report(fingerprint, producer).get("rows", [])


if __name__ == "__main__":
    fp = ""
    prod = ""
    for arg in sys.argv[1:]:
        if arg.startswith("--fingerprint="):
            fp = arg.split("=", 1)[1]
        elif arg.startswith("--producer="):
            prod = arg.split("=", 1)[1]
    r = findings_report(fingerprint=fp, producer=prod)
    print(json.dumps(r, indent=2, sort_keys=True))

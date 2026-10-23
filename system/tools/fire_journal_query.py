#!/usr/bin/env python3
"""fire_journal_query.py — B4.2, the read side of the fire-journal (B4.1).

The journal (`~/.claude/run/fire-journal.jsonl` by default) is an append-only JSONL file, one line
per hook fire, written by the shared `system/hooks/lib/journal.sh` (B4.1, built in parallel in
`~/worktrees/v2-fire-journal` — this file does not touch that work, and does not touch
`system/register/*`, `system/hooks/*`, githooks, CI, or any wiring file). The journal stays
greppable on its own; this tool is convenience on top of it, never the only reader
(plan `enforcement-layer.phase-2.plan.md`, Feature B4.2).

## The line schema this tool expects

One JSON object per line, with these fields (canonical name — alias names this tool also accepts,
so it stays reconcilable against whatever B4.1 actually ships, are listed after the arrow):

    ts           (required)  epoch seconds (int/float) OR an ISO-8601 string.
                              alias: "timestamp"
    hook         (required)  the hook's name/identity (e.g. "guard_egress.sh").
                              alias: "hook_name", "name"
    event        (required)  the hook event (e.g. "PreToolUse", "UserPromptSubmit").
                              alias: "event_name", "hook_event"
    decision     (required)  one of: allow, deny, signpost, inject, none.
                              aliases tolerated and folded in: block/blocked/denied -> deny,
                              allowed -> allow, injected -> inject, signposted -> signpost.
    exit_code    (required)  the hook's process exit code (int, or a numeric string).
                              alias: "exit", "rc", "exit_status"
    matcher      (optional)  the matcher/tool this fired for, if known.
                              alias: "tool", "tool_name"
    duration_ms  (optional)  wall time in milliseconds, if cheap to measure.
                              alias: "duration", "dur_ms", "ms"
    session_id   (optional)  the session this fire happened in, if known.
                              alias: "session"

A line that is not valid JSON, is not a JSON object, is missing a REQUIRED field even after alias
resolution, or carries an exit_code that doesn't parse as an integer, or a decision outside the
closed set above (post-alias), is MALFORMED. Malformed lines are never fatal and never silently
dropped: they are counted, and the count is always printed, in every mode, in every code path.
A blank/whitespace-only line is not counted as malformed — that is ordinary JSONL hygiene.

## Design notes

- No third-party dependencies (stdlib only) — the plan bans nothing here, but every governed tool
  in this repo is a single file a human can run cold, so keep it that way.
- Single pass over the file: parse once, filter once, aggregate once. This has to run over a
  100,000-line journal without falling over (Verify #5) — no O(n^2) anywhere.
- Never raises out of `main()`. A crash here would leave the operator with less information than
  the raw `grep`+`wc -l` they could have run instead — the one thing B4.1's own design note says
  this tool must not be worse than.

Run: python3 system/tools/fire_journal_query.py --help
"""

import argparse
import datetime
import json
import os
import re
import sys
import time

DEFAULT_JOURNAL = os.path.join(os.path.expanduser("~"), ".claude", "run", "fire-journal.jsonl")

DECISIONS = ("allow", "deny", "signpost", "inject", "none")
DECISION_ALIASES = {
    "block": "deny", "blocked": "deny", "denied": "deny",
    "allowed": "allow",
    "injected": "inject",
    "signposted": "signpost",
    "n/a": "none", "na": "none", "": "none",
}

FIELD_ALIASES = {
    "ts": ("ts", "timestamp"),
    "hook": ("hook", "hook_name", "name"),
    "event": ("event", "event_name", "hook_event"),
    "decision": ("decision",),
    "exit_code": ("exit_code", "exit", "rc", "exit_status"),
    "matcher": ("matcher", "tool", "tool_name"),
    "duration_ms": ("duration_ms", "duration", "dur_ms", "ms"),
    "session_id": ("session_id", "session"),
}

REQUIRED = ("ts", "hook", "event", "decision", "exit_code")
OPTIONAL = ("matcher", "duration_ms", "session_id")


# ── time parsing ────────────────────────────────────────────────────────────────────────────

def _first_present(d, names):
    for n in names:
        if n in d and d[n] is not None:
            return d[n], n
    return None, None


def parse_ts_value(v):
    """Coerce a journal line's ts field to an epoch-seconds float. Raises ValueError if it can't."""
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v)
    if isinstance(v, str):
        s = v.strip()
        try:
            return float(s)
        except ValueError:
            pass
        iso = s[:-1] + "+00:00" if s.endswith("Z") else s
        try:
            dt = datetime.datetime.fromisoformat(iso)
        except ValueError:
            raise ValueError("unparseable ts: %r" % v)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt.timestamp()
    raise ValueError("ts is neither a number nor a string: %r" % (v,))


_REL_RE = re.compile(r"^(\d+(?:\.\d+)?)\s*([smhd])$", re.IGNORECASE)
_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def parse_when(spec, now):
    """--since/--until value -> epoch seconds. Accepts an ISO-8601 timestamp, or a relative
    duration like '7d' / '90m' / '24h' / '30s', meaning "that long before `now`"."""
    m = _REL_RE.match(spec.strip())
    if m:
        qty, unit = m.groups()
        return now - float(qty) * _UNIT_SECONDS[unit.lower()]
    try:
        return parse_ts_value(spec)
    except ValueError:
        raise ValueError(
            "--since/--until value %r is neither ISO-8601 nor a relative duration "
            "like '7d', '24h', '30m', '45s'" % spec
        )


# ── line normalization ──────────────────────────────────────────────────────────────────────

class Malformed(ValueError):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def normalize_line(obj):
    """A parsed JSON value -> a canonical record dict, or raises Malformed(reason)."""
    if not isinstance(obj, dict):
        raise Malformed("line is valid JSON but not an object (got %s)" % type(obj).__name__)

    rec = {}

    raw_ts, _ = _first_present(obj, FIELD_ALIASES["ts"])
    if raw_ts is None:
        raise Malformed("missing required field 'ts'")
    try:
        rec["ts"] = parse_ts_value(raw_ts)
    except ValueError as e:
        raise Malformed(str(e))

    raw_hook, _ = _first_present(obj, FIELD_ALIASES["hook"])
    if raw_hook is None or not str(raw_hook).strip():
        raise Malformed("missing required field 'hook'")
    rec["hook"] = str(raw_hook).strip()

    raw_event, _ = _first_present(obj, FIELD_ALIASES["event"])
    if raw_event is None or not str(raw_event).strip():
        raise Malformed("missing required field 'event'")
    rec["event"] = str(raw_event).strip()

    raw_decision, _ = _first_present(obj, FIELD_ALIASES["decision"])
    if raw_decision is None:
        raise Malformed("missing required field 'decision'")
    dec = str(raw_decision).strip().lower()
    dec = DECISION_ALIASES.get(dec, dec)
    if dec not in DECISIONS:
        raise Malformed("decision %r is not one of %s (after alias folding)" % (raw_decision, DECISIONS))
    rec["decision"] = dec

    raw_exit, _ = _first_present(obj, FIELD_ALIASES["exit_code"])
    if raw_exit is None:
        raise Malformed("missing required field 'exit_code'")
    try:
        rec["exit_code"] = int(raw_exit)
    except (TypeError, ValueError):
        raise Malformed("exit_code %r is not an integer" % (raw_exit,))

    raw_matcher, _ = _first_present(obj, FIELD_ALIASES["matcher"])
    rec["matcher"] = str(raw_matcher).strip() if raw_matcher not in (None, "") else None

    raw_dur, _ = _first_present(obj, FIELD_ALIASES["duration_ms"])
    if raw_dur is None:
        rec["duration_ms"] = None
    else:
        try:
            rec["duration_ms"] = float(raw_dur)
        except (TypeError, ValueError):
            raise Malformed("duration_ms %r is present but not numeric" % (raw_dur,))

    raw_sess, _ = _first_present(obj, FIELD_ALIASES["session_id"])
    rec["session_id"] = str(raw_sess).strip() if raw_sess not in (None, "") else None

    return rec


def read_journal(path):
    """Yields (record_or_None, malformed_reason_or_None) for every non-blank line in `path`.
    Never raises for a bad line — only for the file being genuinely unreadable, which the caller
    handles once, up front."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                yield None, "invalid JSON: %s" % e
                continue
            try:
                rec = normalize_line(obj)
            except Malformed as e:
                yield None, e.reason
                continue
            yield rec, None


_ROTATED_SUFFIX_RE = re.compile(r"^\.(\d+)\.(\d+)$")


def discover_journal_files(path):
    """Given the configured (live) journal path, return the ordered list of files to actually
    read: every rotated shard oldest-first, then the live file last (if it exists).

    Rotated shards are written by system/hooks/lib/journal.sh's rotation
    (lhb_journal_maybe_rotate) as "<path>.<epoch-seconds>.<pid>" -- a rename of the live file,
    never an edit, so each shard's own lines are untouched JSONL. Only names matching that exact
    two-numeric-group suffix are treated as shards; anything else sharing the prefix (a stray
    unrelated file) is ignored rather than guessed at. The rotation sidecar files
    (".<basename>.rotstate", ".<basename>.rotlock") live under a DIFFERENT basename entirely (a
    leading dot on the whole name) precisely so they can never collide with this pattern -- see
    the header of journal.sh for why.

    Ordered by the embedded epoch (not lexical filename sort, which would be wrong once the PID
    suffix has a different digit count than another shard's).
    """
    d = os.path.dirname(path) or "."
    base = os.path.basename(path)
    shards = []
    try:
        entries = os.listdir(d)
    except OSError:
        entries = []
    for name in entries:
        if not name.startswith(base + "."):
            continue
        m = _ROTATED_SUFFIX_RE.match(name[len(base):])
        if not m:
            continue
        epoch, pid = int(m.group(1)), int(m.group(2))
        shards.append((epoch, pid, os.path.join(d, name)))
    shards.sort(key=lambda t: (t[0], t[1]))
    files = [p for _, _, p in shards]
    if os.path.isfile(path):
        files.append(path)
    return files


# ── stats ────────────────────────────────────────────────────────────────────────────────────

def percentile(sorted_vals, pct):
    """Linear-interpolation percentile over an already-sorted list. pct in [0, 100]."""
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * (pct / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


class Bucket:
    __slots__ = ("fires", "allow", "deny", "signpost", "inject", "none", "durations")

    def __init__(self):
        self.fires = 0
        self.allow = 0
        self.deny = 0
        self.signpost = 0
        self.inject = 0
        self.none = 0
        self.durations = []

    def add(self, rec):
        self.fires += 1
        setattr(self, rec["decision"], getattr(self, rec["decision"]) + 1)
        if rec["duration_ms"] is not None:
            self.durations.append(rec["duration_ms"])

    def row(self, name):
        durs = sorted(self.durations)
        med = percentile(durs, 50)
        p95 = percentile(durs, 95)
        return {
            "name": name,
            "fires": self.fires,
            "allow": self.allow,
            "deny": self.deny,
            "signpost": self.signpost,
            "inject": self.inject,
            "none": self.none,
            "median_ms": round(med, 3) if med is not None else None,
            "p95_ms": round(p95, 3) if p95 is not None else None,
            "duration_samples": len(durs),
        }


def aggregate(records):
    by_hook, by_event, by_matcher = {}, {}, {}
    for rec in records:
        by_hook.setdefault(rec["hook"], Bucket()).add(rec)
        by_event.setdefault(rec["event"], Bucket()).add(rec)
        mname = rec["matcher"] or "(unknown)"
        by_matcher.setdefault(mname, Bucket()).add(rec)
    return by_hook, by_event, by_matcher


# ── --registered / coverage ─────────────────────────────────────────────────────────────────

_HOOK_PATH_RE = re.compile(r"([A-Za-z0-9_\-.]+\.(?:sh|py))")


def _extract_hook_names_from_command(cmd):
    return set(_HOOK_PATH_RE.findall(cmd))


def load_registered_hooks(path):
    """Accepts three shapes, sniffed by content:
      1. A JSONL register file — one JSON object per line, each naming a hook via a 'hook',
         'name', or 'path' field (B1's register shape).
      2. A wiring JSON file (hooks/hooks.json or .claude/settings.json shape) — a dict with a
         top-level or nested "hooks" key mapping event -> [{"hooks": [{"command": "..."}], ...}].
         Hook identity is extracted from the *.sh/*.py filename inside each command string.
      3. A plain text file, one hook name per line (fallback).
    Returns a set of hook-name strings. Raises OSError/ValueError on genuine failure to read —
    the caller reports that plainly rather than pretending coverage was checked.
    """
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    stripped = content.strip()
    if not stripped:
        return set()

    # Try whole-file JSON first (wiring-file shape or a single JSON array/object register).
    try:
        obj = json.loads(stripped)
    except json.JSONDecodeError:
        obj = None

    if obj is not None:
        names = set()

        def walk(o):
            if isinstance(o, dict):
                if "command" in o and isinstance(o["command"], str):
                    names.update(_extract_hook_names_from_command(o["command"]))
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)

        if isinstance(obj, dict) and "hooks" in obj:
            walk(obj["hooks"])
        else:
            walk(obj)

        if names:
            return names
        # A JSON register as a single array of entry objects with a 'hook'/'name'/'path' field.
        entries = obj if isinstance(obj, list) else [obj]
        for e in entries:
            if isinstance(e, dict):
                v, _ = _first_present(e, ("hook", "name", "path"))
                if v:
                    names.add(os.path.basename(str(v)))
        if names:
            return names

    # JSONL: one register entry per line.
    names = set()
    saw_any_json = False
    for line in stripped.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        saw_any_json = True
        if isinstance(e, dict):
            v, _ = _first_present(e, ("hook", "name", "path"))
            if v:
                names.add(os.path.basename(str(v)))
            elif "command" in e and isinstance(e["command"], str):
                names.update(_extract_hook_names_from_command(e["command"]))
    if saw_any_json:
        return names

    # Plain text fallback: one hook name (or path) per line.
    for line in stripped.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            names.add(os.path.basename(line))
    return names


def _hook_key(name):
    """Loose match key: basename, extension stripped — so 'guard_x.sh' in the register and
    'guard_x' in the journal (or vice versa) still reconcile."""
    base = os.path.basename(name)
    for ext in (".sh", ".py"):
        if base.endswith(ext):
            return base[: -len(ext)]
    return base


def coverage_gap(registered_names, journal_hook_names):
    journal_keys = {_hook_key(n) for n in journal_hook_names}
    zero_fire = sorted(n for n in registered_names if _hook_key(n) not in journal_keys)
    covered = sorted(n for n in registered_names if _hook_key(n) in journal_keys)
    return zero_fire, covered


# ── rendering ────────────────────────────────────────────────────────────────────────────────

TABLE_COLS = ("name", "fires", "allow", "deny", "signpost", "inject", "none", "median_ms", "p95_ms")
TABLE_HEADERS = ("NAME", "FIRES", "ALLOW", "DENY", "SIGNPOST", "INJECT", "NONE", "MEDIAN_MS", "P95_MS")


def render_table(title, rows):
    out = ["## " + title]
    if not rows:
        out.append("  (no data)")
        return "\n".join(out)
    widths = [len(h) for h in TABLE_HEADERS]
    str_rows = []
    for r in rows:
        sr = []
        for c in TABLE_COLS:
            v = r[c]
            sr.append("-" if v is None else str(v))
        str_rows.append(sr)
    for sr in str_rows:
        for i, v in enumerate(sr):
            widths[i] = max(widths[i], len(v))
    fmt = "  ".join("{:<%d}" % w for w in widths)
    out.append(fmt.format(*TABLE_HEADERS))
    for sr in str_rows:
        out.append(fmt.format(*sr))
    return "\n".join(out)


def rows_sorted(bucket_map):
    rows = [b.row(name) for name, b in bucket_map.items()]
    rows.sort(key=lambda r: (-r["fires"], r["name"]))
    return rows


# ── main ─────────────────────────────────────────────────────────────────────────────────────

def build_parser():
    p = argparse.ArgumentParser(
        prog="fire_journal_query.py",
        description="Query the fire-journal (B4.1's JSONL) for per-hook fire/decision counts, "
                     "duration percentiles, and registered-hook coverage gaps.",
    )
    p.add_argument("--journal", default=DEFAULT_JOURNAL,
                    help="path to the journal JSONL (default: %s)" % DEFAULT_JOURNAL)
    p.add_argument("--since", default=None,
                    help="ISO-8601 timestamp, or a relative duration like '7d'/'24h'/'30m' "
                         "meaning that long before now")
    p.add_argument("--until", default=None,
                    help="ISO-8601 timestamp, or a relative duration like '7d'/'24h'/'30m' "
                         "meaning that long before now")
    p.add_argument("--session", default=None, help="filter to one session_id")
    p.add_argument("--json", action="store_true", help="emit JSON instead of tables")
    p.add_argument("--registered", default=None,
                    help="a register.jsonl, a wiring file (hooks.json / settings.json shape), "
                         "or a plain text list of hook names — used for the coverage check: "
                         "which registered hooks have ZERO journal lines in the filtered window")
    p.add_argument("--no-rotated", action="store_true",
                    help="read ONLY the exact --journal path given, ignoring any rotated shards "
                         "(<journal>.<epoch>.<pid>) sitting alongside it. Default is to include "
                         "them automatically -- this flag exists for debugging one shard in "
                         "isolation, not for normal use.")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    now = time.time()

    try:
        since_ts = parse_when(args.since, now) if args.since else None
        until_ts = parse_when(args.until, now) if args.until else None
    except ValueError as e:
        sys.stderr.write("fire_journal_query.py: %s\n" % e)
        return 2

    journal_path = os.path.expanduser(args.journal)

    # Read across rotated shards automatically (B4.3) -- oldest shard first, live file last --
    # unless --no-rotated asks for just the one exact path. This is what makes the CLI keep
    # working unchanged on an installation with no rotated shards yet (discover_journal_files
    # just returns [journal_path], identical to the old single-file behavior) while also covering
    # a rotated installation without the caller doing anything differently.
    if args.no_rotated:
        journal_files = [journal_path] if os.path.isfile(journal_path) else []
    else:
        journal_files = discover_journal_files(journal_path)

    malformed_count = 0
    malformed_samples = []  # first few (reason, ) for a human to act on
    total_lines_seen = 0
    kept = []
    filtered_out_session = 0
    filtered_out_time = 0

    journal_missing = len(journal_files) == 0
    for one_file in journal_files:
        for rec, reason in read_journal(one_file):
            total_lines_seen += 1
            if reason is not None:
                malformed_count += 1
                if len(malformed_samples) < 10:
                    malformed_samples.append("[%s] %s" % (os.path.basename(one_file), reason))
                continue
            if since_ts is not None and rec["ts"] < since_ts:
                filtered_out_time += 1
                continue
            if until_ts is not None and rec["ts"] > until_ts:
                filtered_out_time += 1
                continue
            if args.session is not None and rec["session_id"] != args.session:
                filtered_out_session += 1
                continue
            kept.append(rec)

    by_hook, by_event, by_matcher = aggregate(kept)

    coverage = None
    coverage_error = None
    if args.registered:
        try:
            registered_names = load_registered_hooks(os.path.expanduser(args.registered))
            journal_hook_names = set(by_hook.keys())
            zero_fire, covered = coverage_gap(registered_names, journal_hook_names)
            coverage = {
                "registered_count": len(registered_names),
                "zero_fire_count": len(zero_fire),
                "zero_fire": zero_fire,
                "covered_count": len(covered),
                "covered": covered,
            }
        except (OSError, ValueError) as e:
            coverage_error = str(e)

    result = {
        "journal_path": journal_path,
        "journal_files": journal_files,
        "journal_missing": journal_missing,
        "total_lines_seen": total_lines_seen,
        "malformed_count": malformed_count,
        "malformed_samples": malformed_samples,
        "kept_count": len(kept),
        "filtered_out_time": filtered_out_time,
        "filtered_out_session": filtered_out_session,
        "since": args.since,
        "until": args.until,
        "session": args.session,
        "by_hook": rows_sorted(by_hook),
        "by_event": rows_sorted(by_event),
        "by_matcher": rows_sorted(by_matcher),
        "coverage": coverage,
        "coverage_error": coverage_error,
    }

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=False))
    else:
        if journal_missing:
            print("NOTE: journal file does not exist yet: %s (reporting zero fires, not an error)"
                  % journal_path)
        print("Journal: %s" % journal_path)
        if len(journal_files) > 1:
            print("  (+ %d rotated shard(s) read alongside it: %s)"
                  % (len(journal_files) - 1,
                     ", ".join(os.path.basename(f) for f in journal_files[:-1])))
        print("Lines seen: %d · kept: %d · filtered by time: %d · filtered by session: %d"
              % (total_lines_seen, len(kept), filtered_out_time, filtered_out_session))
        print()
        print(render_table("Per-hook", result["by_hook"]))
        print()
        print(render_table("By event", result["by_event"]))
        print()
        print(render_table("By matcher/tool", result["by_matcher"]))
        print()
        if args.registered:
            print("## Coverage (--registered %s)" % args.registered)
            if coverage_error:
                print("  ERROR reading --registered file: %s" % coverage_error)
            else:
                print("  registered: %d · fired at least once: %d · ZERO fires: %d"
                      % (coverage["registered_count"], coverage["covered_count"],
                         coverage["zero_fire_count"]))
                if coverage["zero_fire"]:
                    print("  zero-fire hooks:")
                    for n in coverage["zero_fire"]:
                        print("    - %s" % n)
            print()
        # Always printed, in every mode, per the spec: malformed lines are counted, never
        # silently skipped.
        print("Malformed lines: %d" % malformed_count)
        if malformed_samples:
            print("  sample reasons (first %d):" % len(malformed_samples))
            for r in malformed_samples:
                print("    - %s" % r)

    return 0


if __name__ == "__main__":
    sys.exit(main())

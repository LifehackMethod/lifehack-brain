#!/usr/bin/env python3
"""findings_deadman.py — the DEAD-MAN'S SWITCH for Hospital's findings producers.

THE GAP THIS CLOSES. `emit_finding.py` writes findings; `findings_reader.py` reads their union
back. Neither one notices when a PRODUCER stops running — a detector that stops firing writes
nothing, and "nothing written" is byte-for-byte indistinguishable from "ran clean, found
nothing" in the raw store. That is the exact silence Hospital exists to abolish, one layer up
from where `emit_finding.py`'s own `scanned_n==0` refusal already closed it for a SINGLE call.

★ NOT A NEW IDIOM — THE SAME ONE STATUS TILES ALREADY USE, EXTENDED. A status tile carries
`last_run` + `stale_after_s`, and a health sweeper DERIVES "STALE" from that pair at READ time —
no tile ever writes the word "STALE" itself (desks never emit STALE — a sweeper derives it).
Findings producers follow the identical rule — `emit_finding.py`'s `VALID_STATUS` has no STALE
either. This module is the READER that derives it for findings, mirroring that same idiom line
for line: a cadence (here: parsed from `pulse-config.md` + `crontab`, playing the role
`stale_after_s` plays for a tile), a last-seen timestamp (here: the newest finding's `ts` per
producer, playing the role of a tile's `last_run`), and a comparison that flips STALE when the
gap exceeds cadence+grace.

WHY A NEW FILE, NOT AN EDIT TO `findings_reader.py`. That module's whole contract is "report
what is ACTUALLY on disk, honestly, never inventing rows" (see its own docstring). Dead-man
detection is the opposite job — it asks "what's missing that SHOULD be there" — and this is a
pure COMPOSER: it imports `findings_reader.findings_report()` (never re-globs or re-parses a
shard itself) and layers one derived, in-memory judgment on top. It writes nothing to disk —
same "pure reader" posture as `findings_reader.py` itself.

THE ENUMERATION SOURCE. Producer EXISTENCE is `discover_producers_from_code()` — a regex scan
of every `producer="..."` (Python kwarg) and `--producer X` (shell CLI) literal at an
`emit_finding` call site under `system/tools/` and `shared/tools/`. This means a producer that
has never once emitted a finding still enumerates, because its `emit_finding(producer="...", ...)`
call site is on disk in source regardless of whether it has ever run — scanning shards instead
would recreate the blind spot this exists to close, one layer up from where it lives. Cadence
resolution then matches each discovered producer against a Pulse `jobs` row (exact name) or a
crontab line (substring match), with one small, explicit, hand-justified exception map
(`_CHILD_JOB`) for producers that are genuine children of another job's sweep and cannot be
derived from string-matching alone.

⚠ WHEN THE ROSTER COMES BACK EMPTY, THAT IS AN ANSWER, NOT A BUG. `load_producer_roster()`
drops every producer whose cadence it cannot resolve (see that function's own docstring: "a
producer with no resolvable cadence is DROPPED from the roster, never defaulted"), so a run
with nothing resolvable yields an empty roster rather than a guess.
    ⚠ CORRECTED 2026-08-15 (T9.7d stale-claim sweep): this paragraph used to frame that as the
    normal fresh-install state, on the premise that a new checkout had neither a scheduler nor a
    `pulse-config.md`. That premise is now FALSE — `system/pulse-config.md` SHIPS in the repo
    with its `jobs` block populated, so on a fresh clone most producers resolve a cadence from
    that manifest alone, before `install-schedulers.sh` has ever been run and with an empty
    crontab. An empty roster is therefore no longer the expected fresh-install result; it now
    means `pulse-config.md` is missing or unparseable, which is worth investigating rather than
    shrugging at. A PARTIAL roster remains normal and correct: a producer with no row in the
    manifest and no crontab match is still legitimately dropped. `assess_producers()`/`findings_report_with_deadman()` additionally
cross-check the derived roster against producers actually SEEN emitting in the real
(non-synthetic) shard union — belt-and-suspenders: if a producer is emitting but the
code-derivation still missed it, that is flagged rather than silently dropped.

Compatible with `/usr/bin/python3` (3.9) — no `X | None` union annotations, stdlib only.
Read-only: never writes, never touches `emit_finding.py` or `findings_reader.py` (this module
only imports `findings_reader`).
"""
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import findings_reader  # noqa: E402  -- the ONE union reader; never re-globbed/re-parsed here

CODE_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
PULSE_CONFIG = os.path.join(CODE_ROOT, "system", "pulse-config.md")

# ── PRODUCER DISCOVERY (derived from source, replaces any hand-curated dict) ────────────────
# Regex over every non-backup .py/.sh file under system/tools/ + shared/tools/: a Python
# `producer="X"` kwarg literal or a shell `--producer X` CLI literal, each one a call site of
# `emit_finding` (system/tools/emit_finding.py). This is the mechanical way a new detector's
# producer string is discovered the moment its code lands, with no second edit anywhere
# required.
_PRODUCER_PY_RE = re.compile(r'producer\s*=\s*["\']([A-Za-z0-9_-]+)["\']')
_PRODUCER_SH_RE = re.compile(r'--producer[= ]+["\']?([A-Za-z0-9_-]+)')
_SCAN_DIRS = ("system/tools", "shared/tools")
_SCAN_EXCLUDE_FILES = {
    "emit_finding.py",       # the DEFINER, not a call site — its own `producer="selftest"`
                              # literals are test scaffolding
    "findings_deadman.py",   # THIS file — its own self-test builds synthetic call sites
                              # (`producer="fake-detector"`, `--producer fake-shell-detector`)
                              # as literal strings to exercise the scanner against a throwaway
                              # tree; without this exclusion the REAL-tree scan below finds
                              # those same literals inside its own source and reports them as
                              # if they were live producers. Confirmed live: before this
                              # exclusion existed, a real-tree run on this repo returned
                              # {'fake-detector', 'fake-shell-detector', ...} instead of an
                              # honest count.
}
_SCAN_EXCLUDE_PRODUCERS = {"selftest"}      # belt-and-suspenders if a stray copy slips through.
                                             # NOTE: "fake-detector"/"fake-shell-detector" are
                                             # deliberately NOT here — the generic-tree self-test
                                             # below asserts discover_producers_from_code() DOES
                                             # find them inside its own throwaway tree; the file-
                                             # level exclusion above is what keeps them out of a
                                             # scan of THIS repo instead.


def discover_producers_from_code(code_root=None):
    """The set of producer names with a real `emit_finding` call site under system/tools/ or
    shared/tools/ — the mechanical replacement for hand-typing a producer roster.

    Deliberately CODE-derived, not SHARD-derived (see module docstring): a producer that has
    never once emitted a finding still has no row in state/findings/*.jsonl, but its
    `emit_finding(producer="...", ...)` call site is on disk in source regardless of whether it
    has ever run — so it still shows up here. Scanning shards instead would recreate the exact
    "scheduled but never fired" blind spot one layer up from where this module exists to close
    it.

    Never raises: an unreadable file is simply skipped (same 'degrade honestly' posture as the
    rest of this module) rather than aborting the whole scan."""
    root = code_root or CODE_ROOT
    found = set()
    for rel_dir in _SCAN_DIRS:
        base = os.path.join(root, rel_dir)
        for dirpath, _dirnames, filenames in os.walk(base):
            for fn in filenames:
                if fn in _SCAN_EXCLUDE_FILES:
                    continue
                if not (fn.endswith(".py") or fn.endswith(".sh")):
                    continue
                if ".bak" in fn or fn.endswith("~"):
                    continue
                try:
                    text = open(os.path.join(dirpath, fn), errors="ignore").read()
                except Exception:
                    continue
                for m in _PRODUCER_PY_RE.finditer(text):
                    found.add(m.group(1))
                for m in _PRODUCER_SH_RE.finditer(text):
                    found.add(m.group(1))
    return found - _SCAN_EXCLUDE_PRODUCERS


# ── the one piece that STAYS hand-specified, and why each entry is irreducible ─────────────
# Most discovered producers share their exact string with a Pulse ```jobs``` row or a crontab
# command line, and resolve with NO lookup table at all, in `load_producer_roster()` below:
# `job = producer`. This map is only for genuine CHILD invocations with no named Pulse slot of
# their own — a producer whose code runs IN-PROCESS or as a subprocess child of another job's
# own tick, verified by reading the call site, not guessed from the name. Extending this map is
# only ever justified by an actual import/subprocess relationship read in the child's own call
# site, never as a shortcut around the discovery scan above. Ships EMPTY: populate it once you
# have a detector that is a genuine child of another job's sweep, e.g.
# `{"my-sub-check": "my-parent-job"}`.
_CHILD_JOB = {}


def _cadences_from_jobs_block(path):
    """{job_name: interval_seconds} from pulse-config.md's ```jobs``` fenced block. Same parse
    shape as health_line.py's `_cadences()` — duplicated rather than imported, so this module
    stays free-standing and independently testable (its own CLI, its own selftest) without
    reaching into a sibling."""
    out, in_block = {}, False
    try:
        for line in open(path):
            s = line.strip()
            if s == "```jobs":
                in_block = True
                continue
            if in_block and s == "```":
                break
            if not in_block or not s or s.startswith("#"):
                continue
            parts = [p.strip() for p in s.split("|")]
            if len(parts) < 3:
                continue
            try:
                out[parts[0]] = int(parts[2])
            except ValueError:
                continue
    except Exception:
        pass                              # unreadable pulse-config: roster just stays thin
    return out


_CRON_LINE_RE = re.compile(r"^\s*(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(.*)$")


def _cron_interval_s(minute_field, hour_field):
    """A DELIBERATELY SMALL cron-schedule parser — enough to cover the two shapes a crontab in
    this ecosystem actually uses: `*/N * * * *` (every N minutes) and `M * * * *` (hourly,
    minute M). Anything else returns None rather than guessing — an unparsed schedule is
    EXCLUDED from the roster, never given a fabricated cadence (same 'degrade honestly, never
    invent' posture as this whole module)."""
    m = re.match(r"^\*/(\d+)$", minute_field)
    if m and hour_field == "*":
        return int(m.group(1)) * 60
    if minute_field.isdigit() and hour_field == "*":
        return 3600
    return None


def _crontab_roster(crontab_text, producers):
    """{producer: interval_seconds} parsed from crontab-syntax text — either live `crontab -l`
    output or pulse-config.md's ```crontab``` fenced block (same 5-field-plus-command shape;
    the fenced block additionally prefixes a `name | machine | schedule |` label column that a
    plain crontab line doesn't have, so the regex is anchored on the LAST 5 whitespace-tokens
    before free text by matching greedily from the command's own known script name instead of
    position — see the substring test below, not a fixed column index).

    `producers` is the set `discover_producers_from_code()` returned — a producer's cadence is
    read off a crontab line when the producer's OWN NAME occurs as a literal substring of that
    line (e.g. producer `health-deadman` matches the line invoking a
    `health-deadman-check.sh`, because the substring `health-deadman` occurs in it)."""
    out = {}
    for line in crontab_text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        # Find the 5 schedule fields immediately preceding the command. Both source shapes
        # (`crontab -l`'s raw 5-field-then-command, and pulse-config.md's fenced
        # `name | machine | M H dom mon dow | command`) contain an unbroken run of 5
        # whitespace-separated cron fields right before the command text — locate it by
        # matching the standard 5-field cron prefix anywhere in the line, not just at col 0.
        m = re.search(r"(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+\S", s)
        if not m:
            continue
        minute, hour = m.group(1), m.group(2)
        iv = _cron_interval_s(minute, hour)
        if not iv:
            continue
        for producer in producers:
            if producer in out:
                continue
            if producer in s:
                out[producer] = iv
    return out


def _live_crontab_text():
    try:
        r = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            return r.stdout
    except Exception:
        pass
    return ""


def _pulse_config_crontab_block(path):
    """Fallback source — the versioned ```crontab``` fenced block pulse-config.md documents as
    an installer's own source of truth. Used only when the LIVE crontab can't be read (no
    `crontab` binary on PATH, or nothing installed yet on this machine) — never preferred over a
    live read, which is ground truth for what is ACTUALLY scheduled right now."""
    out, in_block = [], False
    try:
        for line in open(path):
            s = line.rstrip("\n")
            if s.strip() == "```crontab":
                in_block = True
                continue
            if in_block and s.strip() == "```":
                break
            if in_block:
                out.append(s)
    except Exception:
        pass
    return "\n".join(out)


def load_producer_roster():
    """{producer: cadence_seconds} — DERIVED, never hand-curated. Producer EXISTENCE comes
    from `discover_producers_from_code()` (a source scan, never `state/findings/*.jsonl` — see
    module docstring). Producer CADENCE comes from matching each discovered producer's name
    against a Pulse `jobs` row (exact name, via `_CHILD_JOB` for genuine children — see that
    map's own comment) or a live `crontab -l` line (substring match, falling back to
    pulse-config.md's own ```crontab``` block when the live read is empty/unavailable). A
    producer with NO resolvable cadence is DROPPED from the roster, never defaulted — an
    unknown cadence must never manufacture a false STALE or a false OK.

    ⚠ CORRECTED 2026-08-15 (T9.7d): this used to say an EMPTY dict was the normal result on a
    fresh install, because a new checkout supposedly had neither scheduling nor a
    pulse-config.md. That premise is false — pulse-config.md SHIPS with its `jobs` block
    populated, so most producers resolve a cadence from the manifest on a fresh clone even with
    an empty crontab. An empty dict now points at a missing/unparseable pulse-config.md and is
    worth investigating. A PARTIAL roster is still normal and correct: a producer with no
    manifest row and no crontab match is legitimately dropped. See module docstring."""
    jobs = _cadences_from_jobs_block(PULSE_CONFIG)
    producers = discover_producers_from_code()

    cron_text = _live_crontab_text()
    cron = _crontab_roster(cron_text, producers) if cron_text else {}
    if not cron:
        cron = _crontab_roster(_pulse_config_crontab_block(PULSE_CONFIG), producers)

    roster = {}
    for producer in producers:
        job = _CHILD_JOB.get(producer, producer)
        iv = jobs.get(job) or cron.get(producer)
        if iv:
            roster[producer] = iv
    return roster


GRACE_FLOOR_S = 600   # same floor a health sweeper's assess() uses: max(600, interval * 0.5)


def _grace(interval_s):
    return max(GRACE_FLOOR_S, int(interval_s * 0.5))


def _to_epoch(s):
    """Parse an ISO-8601 ts (emit_finding.py's `_iso_now()` format — always a numeric `+HH:MM`
    offset, this store never writes a bare 'Z') to epoch seconds, or None on any failure."""
    if not s:
        return None
    try:
        return datetime.fromisoformat(s).timestamp()
    except Exception:
        return None


def assess_producers(rows, now=None, roster=None):
    """For every producer in the roster, find its LATEST finding (by `ts`, across ALL
    machines/fingerprints at once — dead-man asks 'did THIS PRODUCER run recently', not 'is any
    one fingerprint fresh') and compare age against cadence+grace, mirroring a health sweeper's
    tile check (`now - last_run > stale_after_s`) exactly. Never raises: a bad row or an
    unparseable ts is simply skipped, never crashes the assessment.

    `roster` defaults to `load_producer_roster()` when omitted; callers that already computed
    it this call (`findings_report_with_deadman()`, to reuse it for the cross-check too) pass it
    in directly rather than paying for a second source-tree scan + `crontab -l` read.

    Returns [{producer, cadence_s, last_ts, age_s, state, why}, ...] — `state` is only ever
    'OK' or 'STALE'; producers do not get a third vocabulary word here any more than a tile
    does (see module docstring: this is the ONE place STALE is derived, never written)."""
    now = now if now is not None else time.time()
    roster = roster if roster is not None else load_producer_roster()

    latest_ts = {}
    for r in rows or []:
        try:
            p = r.get("producer")
            ts = r.get("ts") or ""
        except AttributeError:
            continue
        if not p or not ts:
            continue
        if p not in latest_ts or ts > latest_ts[p]:
            latest_ts[p] = ts

    out = []
    for producer, interval in sorted(roster.items()):
        raw_ts = latest_ts.get(producer)
        last_epoch = _to_epoch(raw_ts) if raw_ts else None
        grace = _grace(interval)
        threshold = interval + grace
        if last_epoch is None:
            out.append({"producer": producer, "cadence_s": interval, "last_ts": None,
                        "age_s": None, "state": "STALE",
                        "why": f"no finding on record for producer {producer!r} — never "
                                "emitted, or the store has no history yet"})
            continue
        age = now - last_epoch
        if age > threshold:
            out.append({"producer": producer, "cadence_s": interval, "last_ts": raw_ts,
                        "age_s": round(age), "state": "STALE",
                        "why": f"no finding in {round(age / 3600, 1)}h (expected every "
                                f"{round(interval / 3600, 2)}h + {round(grace / 60)}m grace) "
                                "— silence, not a clean run"})
        else:
            out.append({"producer": producer, "cadence_s": interval, "last_ts": raw_ts,
                        "age_s": round(age), "state": "OK", "why": ""})
    return out


def findings_report_with_deadman(fingerprint="", producer="", now=None):
    """THE UNION, EXTENDED: `findings_reader.findings_report()`'s exact return shape, PLUS a
    `producer_deadman` key (the full `assess_producers()` list, for anything that wants the
    raw picture), an ADDITIVE `unrostered_producers` key (see below), and, for each STALE
    producer, one SYNTHETIC row appended to `rows` — shaped like a real finding (same keys
    every consumer already reads: producer / status / summary / labels / ts / fingerprint / rc /
    scanned_n) so a caller that already ranks `rows` (health_line.py) sees it with no second
    code path, but carrying `"synthetic": True` so nothing downstream could mistake it for a row
    `emit_finding.py` actually wrote to disk.

    ⚠ THE DEAD-MAN ASSESSMENT ALWAYS RUNS OVER THE **UNFILTERED** UNION, never the
    fingerprint/producer-narrowed one — filtering the read BEFORE assessing would make every
    OTHER producer look silent (their rows would already be gone). The fingerprint/producer
    filter is applied AFTER combining real + synthetic rows, mirroring
    `findings_reader._filter_report()`'s own filter-last order exactly.

    `unrostered_producers` (additive — existing keys/shape unchanged): a cheap CROSS-CHECK on
    the derivation itself. It lists any producer that is actually SEEN emitting in the real
    (non-synthetic) row union but is absent from `load_producer_roster()` — the case where
    code-derivation still missed a real producer (e.g. a future child relationship `_CHILD_JOB`
    doesn't know about yet). This is a safety net on top of the derivation, never the roster's
    source — see module docstring on why deriving FROM shards would reproduce the same gap.
    """
    base = findings_reader.findings_report()          # UNFILTERED on purpose — see docstring
    now = now if now is not None else time.time()
    roster = load_producer_roster()                   # computed ONCE, reused below
    deadman = assess_producers(base.get("rows", []), now=now, roster=roster)

    emitting = {r.get("producer") for r in base.get("rows", [])
                if r.get("producer") and not r.get("synthetic")}
    unrostered = sorted(emitting - set(roster.keys()))

    synthetic = []
    for d in deadman:
        if d["state"] != "STALE":
            continue
        synthetic.append({
            "producer": d["producer"], "machine": "*", "schema_version": 1,
            "ts": _iso(now), "scanned_n": 0, "status": "STALE",
            "summary": d["why"], "rc": 1,
            "labels": {"job": d["producer"], "check": "deadman"},
            "fingerprint": "deadman:" + d["producer"],
            "synthetic": True,
        })

    rows = base.get("rows", []) + synthetic
    if fingerprint or producer:
        rows = [r for r in rows
                if (not fingerprint or r.get("fingerprint") == fingerprint)
                and (not producer or r.get("producer") == producer)]

    report = dict(base)
    report["rows"] = rows
    report["producer_deadman"] = deadman
    report["unrostered_producers"] = unrostered
    return report


def _iso(epoch):
    lt = time.localtime(epoch)
    off = time.strftime("%z", lt)
    off = (off[:3] + ":" + off[3:]) if off else "+00:00"
    return time.strftime("%Y-%m-%dT%H:%M:%S", lt) + off


def _selftest():
    """Scratch-dir selftest — never touches real findings state. Rebinds
    findings_reader.FINDINGS_DIR (the module global, not just the brain-root env var — a
    caller pointing only the env var at a scratch dir still leaves this module's OWN already-
    resolved globals stale from import time, so the module-global rebind is the correct and
    sufficient isolation)."""
    import tempfile
    d = tempfile.mkdtemp()
    old_dir = findings_reader.FINDINGS_DIR
    findings_reader.FINDINGS_DIR = d
    try:
        now = time.time()
        # Fake roster: bypass the real pulse-config/crontab parse entirely for a deterministic test.
        global load_producer_roster
        real_roster_fn = load_producer_roster
        load_producer_roster = lambda: {"fake-fresh": 300, "fake-stale": 300, "fake-never": 300}
        try:
            with open(os.path.join(d, "fake-fresh.primary.jsonl"), "w") as f:
                f.write(json.dumps({"producer": "fake-fresh", "machine": "primary", "ts": _iso(now - 60),
                                     "status": "OK", "scanned_n": 1, "summary": "", "rc": 0,
                                     "labels": {"job": "x"}, "fingerprint": "abc"}) + "\n")
            with open(os.path.join(d, "fake-stale.primary.jsonl"), "w") as f:
                f.write(json.dumps({"producer": "fake-stale", "machine": "primary", "ts": _iso(now - 5000),
                                     "status": "OK", "scanned_n": 1, "summary": "", "rc": 0,
                                     "labels": {"job": "x"}, "fingerprint": "def"}) + "\n")
            # Cross-check case: a producer that IS emitting but is NOT in the roster — proves
            # `unrostered_producers` actually fires rather than silently agreeing.
            with open(os.path.join(d, "fake-unrostered.primary.jsonl"), "w") as f:
                f.write(json.dumps({"producer": "fake-unrostered", "machine": "primary", "ts": _iso(now - 60),
                                     "status": "OK", "scanned_n": 1, "summary": "", "rc": 0,
                                     "labels": {"job": "x"}, "fingerprint": "ghi"}) + "\n")
            report = findings_report_with_deadman(now=now)
            states = {d2["producer"]: d2["state"] for d2 in report["producer_deadman"]}
            assert states["fake-fresh"] == "OK", states
            assert states["fake-stale"] == "STALE", states
            assert states["fake-never"] == "STALE", states
            assert "fake-unrostered" not in states, states   # never in the roster -> never assessed
            synth_producers = {r["producer"] for r in report["rows"] if r.get("synthetic")}
            assert synth_producers == {"fake-stale", "fake-never"}, synth_producers
            assert report["unrostered_producers"] == ["fake-unrostered"], report["unrostered_producers"]
            print("findings_deadman.py self-test PASSED:", states)
        finally:
            load_producer_roster = real_roster_fn
    finally:
        findings_reader.FINDINGS_DIR = old_dir

    # Generic-tree regression check for discover_producers_from_code() / load_producer_roster().
    # A donor-shaped version of this self-test would assert against THIS repo's own real
    # producer names — but this product may legitimately have discovered ZERO producers on day
    # one (producer existence is code-derived, and nothing has an `emit_finding` call site until
    # a detector is written — see module docstring). A hand-built tree with one Python and one
    # shell call site proves the SAME mechanism without asserting on this repo's own inventory.
    tree = tempfile.mkdtemp()
    os.makedirs(os.path.join(tree, "system", "tools"), exist_ok=True)
    os.makedirs(os.path.join(tree, "shared", "tools"), exist_ok=True)
    with open(os.path.join(tree, "system", "tools", "fake-detector.py"), "w") as f:
        f.write('emit_finding(producer="fake-detector", status="OK", scanned_n=1, labels={})\n')
    with open(os.path.join(tree, "shared", "tools", "fake-shell-run.sh"), "w") as f:
        f.write('python3 emit_finding.py --producer fake-shell-detector --status OK\n')
    discovered = discover_producers_from_code(code_root=tree)
    assert discovered == {"fake-detector", "fake-shell-detector"}, discovered

    with open(os.path.join(tree, "system", "pulse-config.md"), "w") as f:
        f.write("```jobs\nfake-detector | local | 300\n```\n")
    global PULSE_CONFIG
    real_pulse_config = PULSE_CONFIG
    PULSE_CONFIG = os.path.join(tree, "system", "pulse-config.md")
    try:
        jobs = _cadences_from_jobs_block(PULSE_CONFIG)
        assert jobs.get("fake-detector") == 300, jobs
    finally:
        PULSE_CONFIG = real_pulse_config
    print("findings_deadman.py generic-tree check PASSED:", sorted(discovered))

    # This repo's OWN real tree: never asserts specific names (this product may legitimately
    # have zero producers today), only that the scan runs cleanly against real disk and returns
    # a set — proving the two scan roots (system/tools, shared/tools) actually resolve here.
    real_discovered = discover_producers_from_code()
    assert isinstance(real_discovered, set), type(real_discovered)
    real_roster = load_producer_roster()
    assert isinstance(real_roster, dict), type(real_roster)
    print(f"findings_deadman.py real-tree scan: {len(real_discovered)} producer(s) discovered, "
          f"{len(real_roster)} with a resolved cadence.")


if __name__ == "__main__":
    if "--selftest" in sys.argv[1:]:
        _selftest()
        sys.exit(0)
    fp = ""
    prod = ""
    for arg in sys.argv[1:]:
        if arg.startswith("--fingerprint="):
            fp = arg.split("=", 1)[1]
        elif arg.startswith("--producer="):
            prod = arg.split("=", 1)[1]
    r = findings_report_with_deadman(fingerprint=fp, producer=prod)
    print(json.dumps(r, indent=2, sort_keys=True))

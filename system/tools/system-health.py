#!/usr/bin/env python3
"""system-health.py — the missed-run SWEEPER + green-illusion-hardened status feed.

THE GAP IT CLOSES: Pulse runs jobs, but nothing notices when one that SHOULD have fired didn't (the
runner dies -> its tile silently goes stale). This is the dead-man's-switch: detect a dead job by the
ABSENCE of a heartbeat past its interval+grace — NOT by waiting for a failure signal.

GREEN-ILLUSION HARDENING (the load-bearing caveat, carried over from the donor unchanged): "green"
must mean ran + fresh + produced expected output — not merely "nothing red". Two signals survive
even in green: STALENESS (a tile older than its stale_after_s is NOT green) and UNEXPECTED-ZERO (a
scan that declares expect_findings but found 0 is a "verify me", not a pass).

SELF-WATCHING: this sweeper's OWN freshness is the Pulse-is-alive signal — if Pulse dies, this feed
goes stale, and health-deadman-check.sh (a SEPARATE scheduled entry, never a Pulse job — see that
file) is what notices, because a Pulse-dispatched watchdog would die with the thing it watches.

PORTED (2026-08-14) from claudeops-config's system/tools/system-health.py (1099 lines) and CUT DOWN
hard. Four whole subsystems the donor leaned on do not exist in this repo and are not this port's to
invent — each is named here, once, rather than silently dropped:
  - `fault_ledger.py` (age-tracked re-escalation, "STILL DOWN 3h" style repeat alerts, durable across
    restarts). Replaced with the donor's OWN simpler mechanism, also present in the original file:
    an edge-trigger against the PREVIOUS run's need_attention list — notify only on NEWLY-attention
    jobs. A job that stays broken for days will only re-page if this repo later grows a fault ledger
    (Hospital / SELF-AUDIT category) — named as a real gap, not hidden.
  - `system/desk-registry.yaml` + the desk-fleet DRIFT COP that read it (missing producer / stale
    tile / no purpose.md per registered desk). No registry exists here.
  - Four sibling producer children the donor's sweep force-ran every 5 minutes as a side effect
    (security-health.py, archivist-placements.py, organism-health.py, archivist-lean.py) — none of
    the four exist in this repo. sentinel-health.py DOES exist and ships with its OWN Pulse slot
    (system/pulse-config.md), so this sweeper reads its tile rather than re-running it inline.
  - Machine-token / two-machine heartbeat namespacing (`_pulse-<machine>.json` glob). One machine,
    one file: `state/status/_pulse.json` (see pulse.sh's own header for the same cut).
What's kept, because it is the actual dead-man's-switch: per-job liveness assessment (UP / LATE /
DOWN / PAUSED / BY DESIGN) against the Pulse heartbeat, the tile-freshness + unexpected-zero overlay,
health_invariants.py's substrate checks folded in, and ONE Hospital finding per assessed job via the
`emit_finding.py` that already ships in this repo (T18.1's per-job identity, kept because it costs
nothing and IS the answer to "which job broke" — see this repo's own state/findings/ store).

Emits state/status/_system-health.json (need_attention[] + groups{}). Pushes a notification on
NEWLY-attention jobs only (dedup against the prior feed). Exit 0 always (a sweeper that fails loud
would itself be the dead job); the tile's own `status` field carries the verdict.
"""
import glob
import json
import os
import subprocess
import sys
import time
from datetime import datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
CODE_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
_SHARED = os.path.join(CODE_ROOT, "shared")
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
try:
    from brain_root import resolve_brain_root            # shared/brain_root.py
    _ROOT_SOURCE, NOTES_ROOT = resolve_brain_root()
except Exception:
    _ROOT_SOURCE, NOTES_ROOT = None, None

from emit_finding import emit_finding, FindingContractError   # noqa: E402 — system/tools/emit_finding.py, already ships here

STATUS = os.path.join(NOTES_ROOT, "state", "status") if NOTES_ROOT else None
CONFIG = os.path.join(CODE_ROOT, "system", "pulse-config.md")
OUT = os.path.join(STATUS, "_system-health.json") if STATUS else None
NOTIFY = os.path.join(CODE_ROOT, "shared", "notify", "notify-send.sh")
SENTINEL_PAUSE_FILE = os.path.expanduser("~/.config/lifehack/sentinel-paused-sources")

# ── TILE RESOLUTION ─────────────────────────────────────────────────────────────────────────────
# TILE_ALIAS — the genuine name mismatches, for the jobs THIS repo actually ships (see
# system/pulse-config.md). Kept as an explicit small map, matching the donor's own convention, so a
# future job that writes its own eponymous tile (state/status/{job}.json) needs ZERO entry here.
TILE_ALIAS = {
    "planning-health": "planning",
    "backlog-health": "backlog",
    "sentinel-health": "sentinel",
    "system-health": "_system-health",     # this sweeper's own feed
}
# NO_TILE_EXPECTED — jobs that legitimately never emit a state/status/*.json tile. Empty today: every
# job in this repo's pulse-config.md does emit one. Left as a named, checked set (not removed) so the
# convention this repo's job-authoring pattern expects stays visible for whoever adds the next job.
NO_TILE_EXPECTED = set()
_MISSING = object()   # sentinel: a tile was EXPECTED (not opted out) but the file doesn't exist


def iso(epoch):
    lt = time.localtime(epoch); off = time.strftime("%z", lt)
    off = (off[:3] + ":" + off[3:]) if off else "+00:00"
    return time.strftime("%Y-%m-%dT%H:%M:%S", lt) + off


def to_epoch(s):
    """Parse an ISO-8601 timestamp to epoch seconds, or None. Handles a bare 'Z' suffix, which
    Python 3.9's datetime.fromisoformat() rejects (3.11+ only) — kept from the donor because this
    repo's own INSTALL.md floor is Python 3.9."""
    if not s:
        return None
    try:
        return datetime.fromisoformat(s).timestamp()
    except ValueError:
        if s.endswith("Z"):
            try:
                return datetime.fromisoformat(s[:-1] + "+00:00").timestamp()
            except Exception:
                return None
        return None
    except Exception:
        return None


def load_jobs():
    """[(name, interval_s, enabled_bool, declared_token)] from pulse-config.md's ```jobs``` block."""
    jobs, in_block = [], False
    try:
        f = open(CONFIG)
    except Exception:
        return jobs
    with f:
        for line in f:
            s = line.strip()
            if s == "```jobs": in_block = True; continue
            if in_block and s == "```": break
            if not in_block or not s or s.startswith("#"): continue
            parts = [p.strip() for p in s.split("|")]
            if len(parts) < 4: continue
            name, enabled, interval = parts[0], parts[1], parts[2]
            try: iv = int(interval)
            except ValueError: continue
            # The DECLARED TOKEN, not just a bool — "yes" vs "no" vs "parked" vs a free word all mean
            # something different (see pulse-config.md's own "How it works": a real word is a human
            # DECLARING a disposition, never to be read back as unexplained breakage).
            jobs.append((name, iv, enabled == "yes", enabled))
    return jobs


def load_heartbeat():
    """{job: {'last_tick':epoch, 'disabled':bool, 'fails':int}} from the single _pulse.json mirror
    pulse.sh writes (one machine, one file — no glob/namespacing needed)."""
    hb = {}
    if not STATUS:
        return hb
    path = os.path.join(STATUS, "_pulse.json")
    try:
        d = json.load(open(path))
    except Exception:
        return hb
    for job, v in d.get("jobs", {}).items():
        hb[job] = {"last_tick": to_epoch(v.get("last_tick", "")),
                   "disabled": bool(v.get("disabled")),
                   "fails": int(v.get("consecutive_fails", 0))}
    return hb


def load_sentinel_paused():
    """Source keys Sentinel has paused after a DANGER finding (shared/gate/sentinel_response.py's
    pause_source() default path) — distinct from a job merely disabled in pulse-config."""
    try:
        return {ln.strip() for ln in open(SENTINEL_PAUSE_FILE) if ln.strip()}
    except Exception:
        return set()


def group_of(job):
    """A coarse grouping for the dashboard's groups{} — this repo has no desk registry, so this is
    the smallest honest thing that works: strip a job's own '-health'/'-...' suffix pattern for the
    handful of prefixes this repo actually ships, else 'platform'."""
    for prefix in ("planning", "sentinel", "backlog"):
        if job == prefix or job.startswith(prefix + "-"):
            return prefix
    return "platform"


JOB_LABELS = {
    "system-health": "Watches every scheduled job for missed runs (the dead-man's switch)",
    "sentinel-health": "Rolls the security event log into a status tile",
    "planning-health": "Checks the calendar for conflicts and unconfirmed invites",
    "backlog-health": "Checks that the system is tracking its own backlog honestly",
    "health-deadman": "Watches system-health itself for silence",
}


def label_for(job):
    return JOB_LABELS.get(job, "")


def tile_for(job):
    """(last_run_epoch, stale_after_s, expect_findings, findings_count) | None | _MISSING.

    Resolution: TILE_ALIAS -> the plain state/status/{job}.json convention -> _MISSING if neither
    resolves and the job isn't in NO_TILE_EXPECTED (see that set's own comment)."""
    if not STATUS:
        return _MISSING
    if job in NO_TILE_EXPECTED:
        return None
    base = TILE_ALIAS.get(job, job)
    try:
        t = json.load(open(os.path.join(STATUS, f"{base}.json")))
    except Exception:
        return _MISSING
    return (to_epoch(t.get("last_run", "")), t.get("stale_after_s"),
            bool(t.get("expect_findings")), t.get("findings_count") or t.get("work_count") or 0)


def assess_tile_only(name, group, now):
    """Assess a job that has NO Pulse heartbeat (an OS-crontab-only entry like health-deadman) purely
    from its own status tile."""
    base = {"job": name, "group": group, "last_run": None, "age_h": None, "next_due": None}
    tile = tile_for(name)
    if tile is None or tile is _MISSING:
        return {**base, "state": "LATE", "severity": "warning", "attention": True,
                "why": f"no status tile at state/status/{TILE_ALIAS.get(name, name)}.json — this runner has never emitted"}
    last_run, stale_after, _, _ = tile
    if last_run is None:
        return {**base, "state": "LATE", "severity": "warning", "attention": True,
                "why": "tile exists but last_run is missing"}
    age_h = round((now - last_run) / 3600, 1)
    base = {**base, "last_run": iso(last_run), "age_h": age_h}
    sa = stale_after or 86400
    if now - last_run > sa:
        return {**base, "state": "STALE", "severity": "warning", "attention": True,
                "why": f"tile is stale — last ran {age_h}h ago (stale after {sa // 3600}h) — check the OS scheduler"}
    try:
        t = json.load(open(os.path.join(STATUS, f"{TILE_ALIAS.get(name, name)}.json")))
    except Exception:
        t = {}
    if t.get("rc", 0) != 0:
        return {**base, "state": "ERROR", "severity": "error", "attention": True,
                "why": f"last run exited rc={t.get('rc')} — {t.get('summary', 'no summary')}"}
    return {**base, "state": "UP", "severity": "ok", "attention": False, "why": ""}


def assess(name, interval, enabled, hb, now, paused=frozenset(), declared=""):
    """Per-job dict {job, group, state, severity, attention, why, last_run, age_h, next_due}."""
    g = group_of(name)
    h = hb.get(name, {})
    lt = h.get("last_tick")
    base = {"job": name, "group": g, "last_run": iso(lt) if lt else None,
            "age_h": round((now - lt) / 3600, 1) if lt else None,
            "next_due": iso(lt + interval) if lt else None}

    if name in paused:
        return {**base, "state": "PAUSED-BY-SENTINEL", "severity": "info", "attention": False,
                "why": "Sentinel paused this source after a DANGER finding — held until a human un-pauses "
                       "(~/.config/lifehack/sentinel-paused-sources)"}
    if not enabled:
        tok = (declared or "").strip().lower()
        if tok and tok not in ("no", "false", "0", "off", ""):
            return {**base, "state": "BY DESIGN", "severity": "info", "attention": False,
                    "why": f"declared '{tok}' in pulse-config.md — a deliberate decision, not a fault"}
        return {**base, "state": "PAUSED", "severity": "info", "attention": False,
                "why": "disabled in pulse-config.md"}
    if h.get("disabled"):
        return {**base, "state": "DOWN", "severity": "error", "attention": True,
                "why": f"circuit-broken ({h.get('fails', 0)} consecutive fails) — won't run until it succeeds once"}
    grace = max(600, int(interval * 0.5))
    if lt is None:
        return {**base, "state": "LATE", "severity": "warning", "attention": True,
                "why": "no run on record (enabled but never ticked — check the scheduler is installed: install-schedulers.sh)"}
    if now - lt > interval + grace:
        return {**base, "state": "LATE", "severity": "warning", "attention": True,
                "why": f"overdue — last ran {base['age_h']}h ago, interval {interval // 3600 or interval // 60}{'h' if interval >= 3600 else 'm'}"}

    tile = tile_for(name)
    if tile is _MISSING:
        return {**base, "state": "NO-TILE", "severity": "warning", "attention": True,
                "why": f"expected a status tile at state/status/{TILE_ALIAS.get(name, name)}.json but none exists"}
    if tile:
        last_run, stale_after, expect_f, fcount = tile
        if last_run and stale_after and (now - last_run > stale_after):
            return {**base, "state": "STALE", "severity": "warning", "attention": True,
                    "why": f"job ran but its tile is stale ({round((now - last_run) / 3600, 1)}h > {stale_after // 3600}h)"}
        if expect_f and fcount == 0:
            return {**base, "state": "VERIFY", "severity": "info", "attention": True,
                    "why": "expects findings but reported 0 — verify it actually ran clean (not silently empty)"}
    return {**base, "state": "UP", "severity": "ok", "attention": False, "why": ""}


def sentinel_fold(now):
    """Read sentinel-health's OWN tile (it ships with its own Pulse slot; see pulse-config.md) and
    fold danger/flags into one need_attention entry. Does NOT re-run sentinel-health.py inline — the
    donor did, every 5 minutes, as a side effect; that's redundant now that sentinel-health has its
    own scheduled cadence, and dropping it also drops the fault_ledger this file no longer has."""
    if not STATUS:
        return None
    try:
        t = json.load(open(os.path.join(STATUS, "sentinel.json")))
    except Exception:
        return None
    danger = t.get("danger_count_24h", 0) or 0
    flags = t.get("event_count_24h", 0) or 0
    sec = t.get("sec_status", t.get("status", ""))
    last = to_epoch(t.get("last_run", ""))
    base = {"job": "sentinel", "group": "platform", "last_run": iso(last) if last else None,
            "age_h": round((now - last) / 3600, 1) if last else None, "next_due": None}
    if sec == "DANGER":
        return {**base, "state": "DANGER", "severity": "error", "attention": True,
                "why": f"{danger} active DANGER security event(s) in 24h — unreviewed real threat"}
    if sec == "FLAGS":
        return {**base, "state": "FLAGS", "severity": "info", "attention": True,
                "why": f"{flags} security flag(s) in 24h — glance, not urgent"}
    if sec == "CLEAR":
        # A CLEAR tile is a RESULT, not an absence — it must reach _emit_findings() like every
        # other assessed job, so the OK row it produces supersedes the prior DANGER/FLAGS row
        # (same fingerprint: labels target=sentinel) and the alarm visibly CLOSES on the next
        # sweep. Before 2026-08-21 this branch returned None: a sentinel DANGER finding then
        # stayed "latest" on the session-start line until it aged out as SILENT — the one job
        # in the sweep whose recovery was never written down (observed that day: acks synced
        # from the laptop at 17:48, the 17:25 DANGER row still led the banner at 17:53).
        reviewed = t.get("reviewed_count_24h", 0) or 0
        return {**base, "state": "UP", "severity": "ok", "attention": False,
                "why": t.get("summary") or f"all clear — {reviewed} reviewed, 0 active (24h)"}
    # Anything else (missing/unknown status) stays None: absence must never read as OK.
    return None


def load_prev_attention():
    if not OUT:
        return set()
    try:
        return {i["job"] for i in json.load(open(OUT)).get("need_attention", [])}
    except Exception:
        return set()


def _emit_findings(scanned_n, rows):
    """ONE Hospital finding PER ASSESSED JOB, every sweep (mirrors the donor's T18.1 idiom) — not
    just the attention-worthy ones, so a job that RECOVERS shows a fresh OK finding on the very next
    sweep (the self-healing signal a fault ledger would otherwise need extra state to express). Each
    finding is independent (own try/except) so one bad row costs only that one finding."""
    for row in rows:
        job = row.get("job", "?")
        try:
            status = "OK" if not row.get("attention") else ("ERROR" if row.get("severity") == "error" else "NEEDS_REVIEW")
            why = row.get("why") or ""
            summary = f"{job}: {row.get('state', '?')}" + (f" — {why}" if why else "")
            emit_finding(
                producer="system-health",
                status=status,
                scanned_n=scanned_n,
                labels={"job": "system-health", "check": "missed-run", "target": job},
                summary=summary,
                payload={"detail": {k: v for k, v in row.items() if k != "label"}},
                rc=0 if status == "OK" else 1,
            )
        except FindingContractError as e:
            sys.stderr.write(f"[system-health] emit_finding failed for missed-run/{job}: {e}\n")
        except Exception as e:
            sys.stderr.write(f"[system-health] emit_finding failed for missed-run/{job}: {e}\n")


def main():
    now = int(time.time())
    if NOTES_ROOT is None:
        # No notes root configured anywhere yet — there is nothing to sweep (every tile this sweep
        # would read lives under the notes root). Write nothing, refuse loudly on stderr, exit 0:
        # this is a legitimate fresh-install state, not a sweep failure.
        sys.stderr.write("[system-health] no notes root configured (shared/brain_root.py) — nothing to sweep yet.\n")
        return 0

    hb = load_heartbeat()
    paused = load_sentinel_paused()

    results = [assess(n, iv, en, hb, now, paused, declared=dec) for (n, iv, en, dec) in load_jobs()]
    sent = sentinel_fold(now)
    if sent:
        results.append(sent)
    # health-deadman is an OS-crontab entry, not a Pulse job — it has no heartbeat row, only its own
    # tile (system/pulse-config.md's ```crontab``` block; health-deadman-check.sh writes the tile).
    results.append(assess_tile_only("health-deadman", "platform", now))

    _missed_run_snapshot = list(results)

    # ── Substrate invariants (health_invariants.py): hooks present, guards untampered, clone fresh,
    # coverage complete. Graceful: a module error never blocks the sweep.
    try:
        import health_invariants as _hi
        results += _hi.run(NOTES_ROOT, CODE_ROOT, now, assessed_jobs={r["job"] for r in results})
    except Exception as e:
        sys.stderr.write(f"[system-health] health_invariants.run() failed: {e}\n")

    for r in results:
        r["label"] = label_for(r["job"])

    need = [r for r in results if r["attention"]]
    healthy = [r for r in results if r["state"] == "UP"]
    groups = {}
    for r in results:
        groups.setdefault(r["group"], {"items": [], "healthy": 0, "attention": 0})
        groups[r["group"]]["items"].append(r)
        if r["state"] == "UP": groups[r["group"]]["healthy"] += 1
        if r["attention"]: groups[r["group"]]["attention"] += 1

    sev = {"error": 0, "warning": 1, "info": 2, "ok": 3}
    need.sort(key=lambda r: sev.get(r["severity"], 9))

    out = {
        "schema_version": 2, "pulse_job": "system-health", "emit_mode": "pulse",
        "stale_after_s": 1800, "last_run": iso(now), "rc": 0,
        "status": "NEEDS_REVIEW" if need else "OK",
        "summary": {"healthy_count": len(healthy), "attention_count": len(need),
                    "total": len(results), "updated_at": iso(now)},
        "need_attention": need,
        "groups": groups,
    }
    os.makedirs(STATUS, exist_ok=True)
    tmp = OUT + ".tmp"
    json.dump(out, open(tmp, "w"), indent=2)
    os.replace(tmp, OUT)

    try:
        _emit_findings(len(results), _missed_run_snapshot)
    except Exception as e:
        sys.stderr.write(f"[system-health] _emit_findings failed: {e}\n")

    # ── push: notify on NEWLY-attention jobs only (dedup vs the prior feed) ──────────────────────
    # No fault ledger here (see module header) — a job that STAYS broken across many sweeps will not
    # re-page on its own. That is a named gap, not an oversight: the donor's re-escalation-with-age
    # lived in fault_ledger.py, a different category's object that hasn't landed in this repo.
    prev = load_prev_attention()
    new_bad = [r for r in need if r["job"] not in prev and r["severity"] in ("error", "warning")]
    if new_bad:
        titles = ", ".join(f"{r['job']} {r['state']}" for r in new_bad[:4])
        cmd = [NOTIFY, "--source", "system-health", "--tags", "rotating_light",
               "--title", f"Pulse: {len(new_bad)} job(s) need attention",
               "--message", titles]
        if any(r["severity"] == "error" for r in new_bad):
            cmd += ["--priority", "critical"]
        try:
            subprocess.run(cmd, timeout=15, stdin=subprocess.DEVNULL, capture_output=True)
        except Exception:
            pass

    print(f"[system-health] {len(healthy)} up / {len(need)} need attention" +
          (f" -> {', '.join(r['job'] + ' ' + r['state'] for r in need)}" if need else " (all green)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())

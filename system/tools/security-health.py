#!/usr/bin/env python3
"""security-health.py — compose `state/status/_security.json` for a Security-tab dashboard
(PORTED 2026-08-14 from claudeops-config's system/tools/security-health.py).

ALIVENESS-STYLE OWNS THIS COMPOSITION. The lane split: SENTINEL owns the verdicts
(`shared/gate/sentinel_response.py`) + the sanitization hook + writes `sentinel.json`
DIRECTLY; this file GLUES `sentinel.json` + mechanically-verified defense-channel statuses
into the ONE flat tile a Security-tab dashboard would bind to. This is COMPOSITION, not
security judgment — every value here is either read from Sentinel's tile or mechanically
verified (a hook file exists + is registered, a tool is present). It makes NO danger/flag
decision of its own.

GRACEFUL-ABSENT: every signal degrades to an honest "unknown"/honest-empty if its source is
missing — the tile always emits, never half-written, never faked. Stdlib-only, atomic
os.replace. Mirrors `sentinel-health.py` (already shipped in this repo).

Channels match the donor Helm dashboard's 5 Security-tab preview rows, kept for continuity:
  injection · l0 (L0 sanitizer) · cal_email_defense · web_fetch · mcp (MCP surface).

⚠ NO DASHBOARD CONSUMES THIS TILE YET. Helm itself is an excluded personal-desk dashboard
(the Desk Ruling) and does not ship here — this file's `state/status/_security.json` output
currently has no reader. What DOES have a live reader: the `emit_finding()` calls in
`_emit_findings()` below, which land in Hospital's findings store exactly like every other
detector in this repo, and ARE read back by `findings_reader.py` / `health_line.py`. Ported
anyway per the migration law (broken/half-consumed is fine; the tile-write half is honest
infrastructure waiting on a dashboard, not dead code) — flagged plainly in this port's report
rather than silently claimed as fully wired.

Tile schema (`state/status/_security.json`):
  { schema_version, pulse_job, emit_mode, stale_after_s, last_run, rc,
    status: OK|FLAGS|DANGER,
    channels: [{key,label,value,tone}],   # tone ∈ g-a(ok) g-b(warn) g-c(bad) ''(neutral)
    sentinel: {status,event_count_24h,danger_count_24h,last_event_at},  # rolled up from sentinel.json
    summary: {updated_at, ok_channels, total_channels} }

WHAT CHANGED IN THIS PORT (generalisation, not a redesign):
  · `CLONE` was a hardcoded `~/claudeops-config` (the donor repo's OWN folder name on the
    donor's machine) — replaced with `CODE_ROOT`, derived from this script's own location,
    the same pattern every other ported tool in this repo uses.
  · `DRIVE`/`STATUS` moved from a hardcoded personal cloud-drive path to the resolved brain
    root (`shared/brain_root.py`). With no root configured, `STATUS`/`OUT` are `None` and
    `main()` refuses to write (same "no honest place to land" posture `emit_finding.py`
    already uses for its own writes) rather than guessing a location.
  · `SETTINGS` moved from `~/.claude/settings.json` (a DIFFERENT, global per-machine file —
    this repo's real settings live inside the checkout) to `CODE_ROOT/.claude/settings.json`,
    confirmed against `citation_lint.py`'s own `settings_rel = ".claude/settings.json"`.
  · The ingestion-gate channel's hook list was updated to this repo's REAL registered names,
    found by listing `system/hooks/` rather than trusted from the donor: `block_primary_calendar`
    -> `guard_calendar_writes` (confirmed renamed during its own port).
  · The MCP-surface row's text hardcoded a specific approved integration tied to an excluded
    personal desk ("1 approved (Supabase - Emily)"). Emily is an excluded desk here, so that
    claim would be actively wrong on this install; the row is now derived purely from whether
    a root `.mcp.json` exists, with no per-integration claim baked in.
"""
import json, os, sys, time, base64

_HERE = os.path.dirname(os.path.abspath(__file__))
CODE_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))  # system/tools/../.. -> repo root

# The ONE validating findings writer (imported by reference, never copy-pasted).
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from emit_finding import emit_finding  # noqa: E402

_SHARED = os.path.join(CODE_ROOT, "shared")
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)
try:
    from brain_root import resolve_brain_root          # shared/brain_root.py
    _ROOT_SOURCE, _ROOT = resolve_brain_root()
except Exception:
    _ROOT_SOURCE, _ROOT = None, None

STATUS = f"{_ROOT}/state/status" if _ROOT else None
HOOKS = f"{CODE_ROOT}/system/hooks"
OUT = f"{STATUS}/_security.json" if STATUS else None
SETTINGS = f"{CODE_ROOT}/.claude/settings.json"
STALE_AFTER_S = 1800


def iso(epoch):
    lt = time.localtime(epoch)
    off = time.strftime("%z", lt)
    off = (off[:3] + ":" + off[3:]) if off else "+00:00"
    return time.strftime("%Y-%m-%dT%H:%M:%S", lt) + off


def _settings_text():
    """The active checkout's settings.json as text (for substring registration checks). '' if absent."""
    try:
        return open(SETTINGS, encoding="utf-8").read()
    except Exception:
        return ""


def hook_active(name, settings_text):
    """A defense hook is ACTIVE iff its file exists in the code-canonical hooks dir AND it is
    referenced (registered) in the active settings.json. Returns (present, registered)."""
    present = os.path.isfile(f"{HOOKS}/{name}.sh")
    registered = name in settings_text
    return present, registered


def tool_present(relpath):
    return os.path.isfile(f"{CODE_ROOT}/{relpath}")


def _decode_evidence(ev_list, cap=6, maxlen=120):
    """Decode Sentinel's base64 evidence snippets into readable display text (deduped, capped).
    These are the matched attack-pattern strings; a dashboard would render them as inert TEXT
    in the dossier (display only — never executed). Adversarial-content rule still holds
    downstream."""
    out = []
    for ev in (ev_list or []):
        b = ev.get("snippet_b64")
        if not b:
            continue
        try:
            s = base64.b64decode(b).decode("utf-8", "replace").strip()
        except Exception:
            s = ""
        if s and s not in out:
            out.append(s[:maxlen])
        if len(out) >= cap:
            break
    return out


def _recent_events(t, cap=8):
    """Carry Sentinel's recent_events[] into the tile so a future dashboard can render the
    per-incident dossier. Capped slice; evidence decoded for display."""
    out = []
    for e in (t.get("recent_events") or [])[:cap]:
        out.append({
            "ts": e.get("ts"),
            "source": e.get("source"),
            "verdict": e.get("verdict"),
            "item": e.get("item"),
            "detail": e.get("detail"),
            "matched": _decode_evidence(e.get("evidence")),
            "disposition": e.get("disposition", "unreviewed"),
        })
    return out


def read_sentinel():
    """Roll up Sentinel's tile (Sentinel writes it directly). Graceful-absent → CLEAR/0."""
    try:
        t = json.load(open(f"{STATUS}/sentinel.json"))
    except Exception:
        return {"status": "UNKNOWN", "sec_status": "UNKNOWN", "event_count_24h": 0, "danger_count_24h": 0,
                "active_danger_24h": 0, "active_count_24h": 0,
                "last_event_at": None, "present": False, "recent_events": []}
    # ── ACTIVE vs RAW-24h ─────────────────────────────────────────────────────────────────
    # sentinel.json carries BOTH: danger_count_24h / event_count_24h are the RAW window totals
    # and are HISTORY (an acked event stays counted, deliberately), while active_danger_24h /
    # active_count_24h exclude anything a human has dispositioned. This tile renders its value
    # as "N active DANGER", so it must read the ACTIVE numbers. Fall back to the raw counts
    # when the active_* keys are absent (older tiles), so a stale tile degrades to the
    # previous behaviour instead of rendering zero and inventing calm.
    _active_d = t.get("active_danger_24h")
    _active_e = t.get("active_count_24h")
    return {"status": t.get("status", "UNKNOWN"),
            "active_danger_24h": int(_active_d if _active_d is not None else t.get("danger_count_24h", 0) or 0),
            "active_count_24h": int(_active_e if _active_e is not None else t.get("event_count_24h", 0) or 0),
            # sec_status = Sentinel's ACK-AWARE security verdict (CLEAR/FLAGS/DANGER). Authoritative
            # over the raw 24h counts — after a human acks false positives the counts stay (history)
            # but sec_status flips CLEAR. Drive the tile off this, not the stale raw danger_count.
            "sec_status": t.get("sec_status", t.get("status", "UNKNOWN")),
            "event_count_24h": int(t.get("event_count_24h", 0) or 0),
            "danger_count_24h": int(t.get("danger_count_24h", 0) or 0),
            "last_event_at": t.get("last_event_at"), "present": True,
            "recent_events": _recent_events(t)}


def compose():
    st = _settings_text()
    sent = read_sentinel()
    channels = []

    # 1 — INJECTION (from Sentinel's tile; this file only displays it). Drive tone off the
    # ACK-AWARE sec_status, NOT the raw 24h counts — acked false-positives leave the counts
    # intact (history) but flip sec_status CLEAR, and the tile must reflect the human's
    # verdict, not the stale raw number. ACTIVE counts drive the rendered value.
    dang, flags, sec = sent["active_danger_24h"], sent["active_count_24h"], sent["sec_status"]
    INJ = "Prompt-injection flags (Sentinel)"
    if not sent["present"]:
        channels.append({"key": "injection", "label": INJ,
                         "value": "Sentinel tile not emitting yet", "tone": "g-b"})
    elif sec == "DANGER":
        channels.append({"key": "injection", "label": INJ,
                         "value": f"{dang} active DANGER · 24h", "tone": "g-c"})
    elif sec == "FLAGS":
        channels.append({"key": "injection", "label": INJ,
                         "value": f"{flags} flag(s) · 24h — review", "tone": "g-b"})
    elif sec in ("CLEAR", "OK"):
        channels.append({"key": "injection", "label": INJ,
                         "value": (f"clear · {flags} flagged/{dang} danger in 24h, all reviewed" if flags else "0 · 24h"),
                         "tone": "g-a"})
    else:  # UNKNOWN / unacked
        channels.append({"key": "injection", "label": INJ,
                         "value": f"{dang} danger / {flags} flags · 24h (unreviewed)", "tone": "g-b"})

    # 2 — L0 SANITIZER (the inbound-content scrubbers must be present)
    l0_tools = {"email_convert": "shared/tools/email_convert.py",
                "sanitize": "system/tools/sanitize.py"}
    l0_missing = [k for k, p in l0_tools.items() if not tool_present(p)]
    channels.append({"key": "l0", "label": "Inbound content sanitizer (L0)",
                     "value": "active · scrubs inbound web/email before the model reads it" if not l0_missing else f"degraded · missing {', '.join(l0_missing)}",
                     "tone": "g-a" if not l0_missing else "g-c"})

    # 3 — INBOUND INGESTION GATE (unified gate + calendar-write block; file-present AND
    # registered). `guard_calendar_writes` — the LIVE name in this repo (confirmed by listing
    # system/hooks/; the donor's `block_primary_calendar` was renamed during its own port).
    ce_hooks = ["ingest_gate_enforce", "guard_calendar_writes"]
    ce = {h: hook_active(h, st) for h in ce_hooks}
    ce_ok = sum(1 for p, r in ce.values() if p and r)
    ce_bad = [h for h, (p, r) in ce.items() if not (p and r)]
    channels.append({"key": "cal_email_defense", "label": "Inbound ingestion gate (email/calendar/tasks/web/files)",
                     "value": f"hooks active ({ce_ok}/{len(ce_hooks)})" if not ce_bad
                              else f"{ce_ok}/{len(ce_hooks)} active · check {', '.join(ce_bad)}",
                     "tone": "g-a" if not ce_bad else "g-c"})

    # 4 — WEB FETCH (safe_fetch present + the WebFetch/WebSearch redirect hooks registered)
    web_ok = tool_present("system/tools/safe_fetch.py") and ("WebFetch" in st) and ("WebSearch" in st)
    channels.append({"key": "web_fetch", "label": "Web-fetch sanitizer",
                     "value": "sanitized (safe_fetch + L0)" if web_ok else "redirect hooks not fully wired",
                     "tone": "g-a" if web_ok else "g-c"})

    # 5 — MCP SURFACE. No config file to count by default (doctrine: no committed .mcp.json;
    # MCP approved per-purpose only, if at all, per install). This row is purely presence-based
    # — it makes no claim about WHICH integration is approved, since that is per-install and
    # this repo ships with none configured.
    mcp_json = os.path.isfile(f"{CODE_ROOT}/.mcp.json")
    channels.append({"key": "mcp", "label": "MCP surface",
                     "value": "none configured" if not mcp_json
                              else "a root .mcp.json is present — review what it approves",
                     "tone": "" if not mcp_json else "g-b"})

    # OVERALL — Sentinel's verdict drives danger/flags; a degraded channel (g-c) or a BLIND
    # sentinel source (tile absent) downgrades off fully-green too: green must mean ran +
    # fresh + telemetry present, not merely "nothing red".
    if sec == "DANGER":
        status = "DANGER"
    elif sec == "FLAGS" or any(c["tone"] == "g-c" for c in channels) or not sent["present"]:
        status = "FLAGS"
    else:
        status = "OK"

    ok_channels = sum(1 for c in channels if c["tone"] in ("g-a", ""))
    now = int(time.time())
    return {
        "schema_version": 2, "pulse_job": "security-health", "emit_mode": "manual",
        "stale_after_s": STALE_AFTER_S, "last_run": iso(now), "rc": 0,
        "status": status,
        "channels": channels,
        "sentinel": {k: sent[k] for k in ("status", "event_count_24h", "danger_count_24h", "last_event_at")},
        "recent_events": sent.get("recent_events", []),
        "summary": {"updated_at": iso(now), "ok_channels": ok_channels, "total_channels": len(channels)},
    }


# ── Hospital findings — ONE per named channel (the 5 explicit `.append()` calls in compose():
# injection · l0 · cal_email_defense · web_fetch · mcp). Does NOT touch the hand-rolled
# json.dump/os.replace write above/below — a completely separate emission. tone is this file's
# own vocabulary (g-a/g-b/g-c/'') and is mapped onto emit_finding's OK/NEEDS_REVIEW/ERROR,
# never re-derived. scanned_n = len(channels) — the same number compose() already puts in
# summary.total_channels — shared across all 5 findings.
_TONE_STATUS = {"g-a": "OK", "": "OK", "g-b": "NEEDS_REVIEW", "g-c": "ERROR"}


ID_MIRRORED_BY_SENTINEL = "injection"
# ── WHY THE `injection` CHANNEL EMITS NO FINDING ──────────────────────────────────────────
# It is a MIRROR, not a measurement. read_sentinel() above reads `state/status/sentinel.json`
# — the tile `sentinel-health.py` (already shipped in this repo) itself writes — and
# republishes its verdict. So both producers would emit an ERROR finding derived from ONE
# underlying fact (Sentinel's DANGER count), and Hospital, which cannot know they share a
# source, would count them as two independent failures — a measured CO-FAILURE artifact on the
# donor system, not a real correlation. Correlation is what a seam detector is for, so the fix
# belongs at the source, not in the detector.
#
# ⛔ THIS SUPPRESSES NOTHING. `sentinel-health.py` still emits (or would emit, once it is
# wired to Hospital) the finding — it OWNS the security ledger. The channel below is still
# COMPOSED into the tile, so a future dashboard renders the injection row exactly as before;
# only the duplicate Hospital finding stops.


def _emit_findings(out):
    channels = out.get("channels", [])
    scanned_n = len(channels)
    for c in channels:
        if c.get("key") == ID_MIRRORED_BY_SENTINEL:
            continue
        try:
            status = _TONE_STATUS.get(c.get("tone", ""), "NEEDS_REVIEW")
            emit_finding(
                producer="security-health",
                status=status,
                scanned_n=scanned_n,
                labels={"job": "security-health", "channel": c["key"]},
                summary=f"{c['label']}: {c['value']}",
                payload={"tone": c.get("tone", "")},
                rc=0 if status == "OK" else 1,
            )
        except Exception as e:
            sys.stderr.write(f"[security-health] emit_finding failed for {c.get('key')}: {e}\n")


def main():
    if OUT is None:
        sys.stderr.write("[security-health] no notes root configured (shared/brain_root.py) — "
                         "nothing to write yet. Fix: python3 shared/brain_root.py --set <folder>.\n")
        return 1
    out = compose()
    os.makedirs(STATUS, exist_ok=True)
    tmp = OUT + ".tmp"
    json.dump(out, open(tmp, "w"), indent=2)
    os.replace(tmp, OUT)
    # Hospital findings, one per named channel — never touches the write above.
    try:
        _emit_findings(out)
    except Exception as e:
        sys.stderr.write(f"[security-health] emit_finding batch failed: {e}\n")
    print(f"[security-health] status={out['status']} · {out['summary']['ok_channels']}/{out['summary']['total_channels']} channels ok "
          f"· sentinel={out['sentinel']['status']} (flags24h={out['sentinel']['event_count_24h']}, danger24h={out['sentinel']['danger_count_24h']})")
    return 0


if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "system", "tools")))
    from utf8_stdio import force_utf8_stdio
    force_utf8_stdio()
    raise SystemExit(main())

#!/usr/bin/env python3
"""
health_line.py — the ~30-token session-banner health line.

Kept as its own tool rather than inline in the SessionStart hook for two reasons:
the hook is a protected enforcement-plane file (every edit needs a chmod dance), and
an inline heredoc of Python inside bash is where quoting bugs go to hide.

CONTRACT: print at most a couple of SHORT lines, or print NOTHING. Silence when healthy
is the whole design — a banner that speaks every session becomes wallpaper, and wallpaper
is how a dead job can sit unnoticed for weeks. Never raises, never exits nonzero: a broken
health line must not break a session's context load.

THE HOSPITAL CONSUMER. Hospital (`emit_finding.py` writer, `findings_reader.py` union reader,
`state/findings/<producer>.<machine>.jsonl` store) can have a writer and a store but NOTHING
that reads the findings back — a filing cabinet nobody opens. A "a human will notice on the
dashboard" consumer is a proven failure mode: something written but never looked at is
indistinguishable, in practice, from something never written at all. This module is the fix:
it already speaks at every session whether or not anyone chooses to look, so `_findings_line()`
below extends it to read the findings store through the ONE shared reader
(`findings_reader.findings_report()` — never re-implemented here) and surface a RANKED,
honestly-truncated line, never a dump. See `_findings_line()`'s own docstring for the ranking
rule, the cap, and how degradation is surfaced.

THE DEAD-MAN'S SWITCH. A silent producer and a producer that ran clean are, in the raw store,
indistinguishable: neither writes anything wrong, one writes nothing at all. `_findings_line()`
reads through `findings_deadman.findings_report_with_deadman()` instead of
`findings_reader.findings_report()` directly — that module composes the same union reader
(never re-globs/re-parses a shard itself) and derives a synthetic STALE row for any producer
whose cadence has lapsed with no fresh finding, mirroring exactly how a health sweeper derives
"STALE" from a tile's `last_run` + `stale_after_s` (producers never write the word STALE
themselves, in either subsystem).

ONE DEAD-MAN SWITCH, NOT TWO. `main()` reads the SAME fetched deadman report for its own
ledger-staleness fallback rather than hand-rolling a second, independently-coded answer to "has
this producer gone silent" against a different store. `_fetch_deadman_report()` runs ONCE and
its result is shared: `_findings_line()` renders the Hospital-derived STALE rows from it (the
real mechanism, for every producer it can see), and `main()`'s ledger check narrows itself to
producers the real mechanism structurally cannot see. If the fetch itself fails (`report is
None`), the narrow check WIDENS to every ledger producer as a fallback — degrade toward MORE
watching, never less, matching this module's existing "never fail closed to silence" rule below.

THE EFFICIENCY CONSUMER. Hospital (above) detects+ranks problems; Efficiency is its mirror, one
step further down the pipe: findings -> a reasoner -> `emit_recommendation.py` ->
`state/recommendations/<altitude>.<machine>.jsonl` -> THIS module -> a human acts. Same
"writer with no reader" failure this module exists to close for findings, applied one layer
down — so the recommendation store rides the ONE surface proven to be seen without anyone
choosing to look. Appends a `RECOMMENDATIONS:` line alongside (never replacing) the `FINDINGS:`
line, via `_fetch_recommendations()` / `_recommendations_line()` — same fetch-then-render split,
same cap-and-say-how-many-more, same never-raise/never-silent contract as the Hospital consumer
above. The "recordable back" half — a human's accept/reject decision, durably recorded so a
disposed-of recommendation stops appearing — lives in `recommendation_disposition.py`; see that
module's docstring for why it is its own append-only store rather than a field rewritten onto
an existing recommendation row.
"""
from __future__ import annotations

import json
import os
import signal
import sys
import threading
import time

# Cadence lookup for producer staleness. Producers with their own named Pulse job get that
# job's real interval from pulse-config.md; producers with no named slot only ever run AS A
# CHILD of another job's own tick, so their real-world cadence IS that job's, not an invented
# number.
PULSE_CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pulse-config.md")
DEFAULT_CADENCE_S = 300


def _cadences(path: str) -> dict:
    """{job_name: interval_seconds} parsed from pulse-config.md's fenced ```jobs``` block.
    Same shape as a health sweeper's load_jobs(), trimmed to just the interval column."""
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
        pass                           # unreadable pulse-config: every producer falls back to DEFAULT_CADENCE_S
    return out


def age(seconds: float) -> str:
    if seconds >= 86400:
        return f"{int(seconds // 86400)}d"
    if seconds >= 3600:
        return f"{int(seconds // 3600)}h"
    return f"{int(seconds // 60)}m"


# Hang guard on the findings read. Mirrors emit_finding.py's write-side `_Alarm` (SAME
# reasoning: SIGALRM is main-thread-only, so a threaded caller must skip the alarm rather than
# crash on `signal.signal()`'s ValueError) — but this module never imports that private class
# from a sibling module's file; it is a few lines, so it is duplicated on purpose rather than
# reaching into another owner's internals for a name with a leading underscore. A read that
# hangs is the ONE failure mode `findings_report()`'s own try/except cannot cover (a wedged
# mount blocks instead of raising) — this is that module's missing piece, kept OUTSIDE it since
# findings_reader.py is owned by another concern.
FINDINGS_READ_TIMEOUT_S = 8

# Findings whose CURRENT (latest) status is one of these are "broken" and worth a session-
# start line; OK is healthy and never shown. Order is the rank: ERROR outranks NEEDS_APPROVAL
# outranks DRIFT outranks NEEDS_REVIEW outranks STALE — same VALID_STATUS vocabulary
# emit_status.py / emit_finding.py share, imported nowhere here to avoid a second import chain
# off a sibling module; the five-way set is small and stable enough to state directly.
#
# ⚖ THIS ORDER PUTS STALE LAST, DELIBERATELY, AND NOT BECAUSE IT MATTERS LESS. An earlier
# design ranked STALE first — "a producer gone SILENT is the failure this whole subsystem
# exists to abolish, so it must not get buried under a chattier ERROR" — but this list is
# sorted ASCENDING and capped at 3 (_FINDINGS_CAP), so "ranks first" means a STALE row takes a
# permanent slot and NEVER improves with time; ties break oldest-first, so it only hardens. A
# live unreviewed security event that just fired is a LIVELIER failure than a silence that has
# already been silent for a week, and the 3-slot cap makes this a strict trade, not a
# preference. STALE is still shown — it is last of five, not dropped.
# ⚠ STALE is deliberately NOT in emit_finding.py's VALID_STATUS — no producer ever emits it
# (same rule status tiles already follow: "desks never emit STALE — a sweeper derives it"). It
# only ever arrives here as a SYNTHETIC row `findings_deadman.findings_report_with_deadman()`
# appends in-memory; nothing on disk is ever written with this status. That it is DERIVED rather
# than REPORTED is the second half of the case for ranking it below the reported statuses.
# DRIFT sits between NEEDS_APPROVAL and NEEDS_REVIEW.
# ⚠ THIS SET AND emit_status.py's VALID_STATUS MUST STAY PAIRED. A status legal there but
# missing HERE is writable but never displayable: the filter one screen down is
# `[r for r in latest.values() if r.get("status") in _STATUS_RANK]`, so an unranked status is
# silently dropped from the banner rather than shown at the bottom. If you add a sixth status,
# edit both or you have built a silent drop.
# WHY DRIFT SITS AT RANK 2, stated so it can be argued with: DRIFT is a CONCRETE DETECTED
# MISMATCH — the producer already knows what does not match — whereas NEEDS_REVIEW only says "a
# human should look at this." A specific finding outranks a generic request for attention. It
# sits below NEEDS_APPROVAL because that one means work is BLOCKED on a human, which is worse
# than work being wrong.
_STATUS_RANK = {"ERROR": 0, "NEEDS_APPROVAL": 1, "DRIFT": 2, "NEEDS_REVIEW": 3, "STALE": 4}
_FINDINGS_CAP = 3   # session-start line, not a report — show the top 3, SAY how many more

# ── THE SECOND AXIS — WEIGHT. ────────────────────────────────────────────────────────────────
# ⭐⭐ SEVERITY IS NOT THE ONLY AXIS THAT MATTERS. A three-day-old ERROR from an experimental,
# not-fully-built producer can hold slot 1 on the session banner purely on rank, while a load-
# bearing producer's fresher, lower-severity finding sits buried a few ranks down and never
# displays. The ranking can be working exactly as designed and still bury the thing that most
# needed to be seen — severity answers "how bad," never "how much do I actually care about
# this producer."
#
# ⇒ THE FIX: A BREAKING EXPERIMENT IS EXPECTED BEHAVIOUR AND MUST NOT OUTRANK A LOAD-BEARING
# PRODUCER. Which producers count as "experimental" (a nice-to-have that is expected to break
# sometimes) vs. "load-bearing" is a call only the team running this system can make — so it is
# config, not a shipped opinion. `_EXPERIMENTAL_PRODUCERS` ships EMPTY; populate it with your
# own producer names once you have some, e.g. `{"my-flaky-integration"}`.
#
# ⛔ DEFAULT IS LOAD-BEARING — ABSENCE MUST MEAN THE SAFE THING. An unknown/new producer is
# treated as important and is NEVER silently demoted. This is the same fail-safe rule stated for
# retroactive semantics elsewhere in this system ("make absence mean the SAFE thing, never the
# active thing"): the dangerous direction here is quietly hiding something that mattered, so the
# set below is an ALLOWLIST of exceptions, never a list of the important ones.
# ⛔ DEMOTED, NEVER HIDDEN. An experimental producer still counts in the total, still appears in
# the "(+N more not shown)" arithmetic, and still takes a slot when slots remain. This changes
# ORDER, never membership — nothing becomes invisible.
_EXPERIMENTAL_PRODUCERS = set()   # empty by default — see above; add your own producer names here


def _weight(producer):
    """0 = load-bearing (the default, and the safe answer), 1 = experimental.

    Kept a function rather than an inline lookup so the ONE place this decision is made is
    greppable, and so a future weight source (a per-producer declaration, a registry) has a
    single seam to replace instead of a scattered set literal."""
    return 1 if producer in _EXPERIMENTAL_PRODUCERS else 0


# ── THE THIRD PIECE — CHANNELS. ─────────────────────────────────────────────────────────────
# ⭐ WHY A CHANNEL AND NOT ANOTHER RANK. `_weight()` above fixes WHO WINS the three slots. This
# fixes a different problem: some things should never have been COMPETING at all. A few
# surfaces — money, a calendar, the system's own state — are not acute faults that flare and
# clear; they are standing surfaces you want to glance at. Ranking them against a live DANGER
# event forces a comparison that has no right answer, and whichever loses becomes invisible.
# ⇒ Each channel gets a FIXED line that is SILENT WHEN CLEAN and never competes with anything.
#
# ⛔ A CHANNELLED PRODUCER LEAVES THE RANKED POOL — this is the half that keeps the numbers
# honest. Without it, a channelled producer would appear on its channel's line AND consume one
# of the three ranked slots, so the reader sees it twice and a genuine fault loses a seat to a
# duplicate. Every count below is therefore computed over its OWN pool: the FINDINGS total
# counts only what still competes, and each channel line states its own. Nothing is
# double-counted and nothing is dropped.
#
# ⚠ WHICH PRODUCER BELONGS TO WHICH CHANNEL IS CONFIG, NOT A SHIPPED OPINION. The three
# CHANNEL NAMES below (MONEY / CALENDAR / SYSTEM) are an illustrative starting set — keep them,
# rename them, or replace them entirely; `_CHANNEL_ORDER` just has to list whatever keys you
# use. `_CHANNELS` ships EMPTY: populate it as `{"my-producer": "MONEY", ...}` once you have
# producers worth giving a standing surface to. Until then every producer competes in the
# ranked pool, which is the safe default (see `_weight()`'s "absence must mean the safe thing").
_CHANNELS = {}   # empty by default — e.g. {"billing-health": "MONEY", "calendar-health": "CALENDAR"}
# Security-flavored producers are usually a deliberate exception to channelling: a DANGER event
# is a "drop what you are doing", not a surface to glance at, so keeping a security detector OUT
# of `_CHANNELS` lets it stay in the ranked line where it can win slot 1.
_CHANNEL_ORDER = ("MONEY", "CALENDAR", "SYSTEM")   # rename/reorder freely to match your _CHANNELS keys
# The producer that owns the REACHABILITY line below, if/when a reachability detector is wired
# up. Named ONCE so the "has its own surface => leaves the ranked pool" rule and the renderer
# cannot drift apart. Empty string cleanly disables the reachability line (no producer will ever
# match "").
_REACHABILITY_PRODUCER = "architecture-reachability"


def _channel_lines(report) -> list:
    """One line per channel that has something to say; SILENT when clean. Never raises.

    Reads the SAME report every other line here reads — no second fetch (this module's "ONE
    DEAD-MAN SWITCH, NOT TWO" rule). Collapses to the latest row per fingerprint, keeps the
    non-OK ones, and renders at most a few producers per channel so a chatty producer cannot
    turn a fixed line into a wall (the same honest-truncation discipline `_findings_line()`
    uses, and it states its own cut).
    """
    try:
        latest = _collapse_latest((report or {}).get("rows", []))   # same rule, ONE place
        buckets = {}
        for r in latest.values():
            ch = _CHANNELS.get(r.get("producer"))
            if ch and r.get("status") in _STATUS_RANK:
                buckets.setdefault(ch, []).append(r)

        out = []
        for ch in _CHANNEL_ORDER:
            rows = buckets.get(ch)
            if not rows:
                continue                      # silent when clean — the whole point of a fixed line
            rows.sort(key=lambda r: (_STATUS_RANK.get(r.get("status"), 9), r.get("ts") or ""))
            # ⛔ ONE ROW PER PRODUCER — the same rule `_diverse_top()` enforces for the ranked
            # line. Without it, one chatty producer can print TWICE on one channel's line,
            # spending half a fixed line on itself. A channel exists to give a SURFACE a voice,
            # not to let its noisiest producer take the surface over.
            seen, uniq = set(), []
            for r in rows:
                p = r.get("producer")
                if p in seen:
                    continue
                seen.add(p)
                uniq.append(r)
            # ⛔ CAP 3, NOT 2. At a cap of 2, a channel with three genuinely distinct
            # NEEDS_REVIEW members can have its least-recent one cut to "(+1 more)" — hiding the
            # very item a fixed line exists to surface, because a tie breaks on timestamp. ⭐ A
            # fixed line that cannot hold its own channel's members has just re-created the
            # ranking problem one level down. 3 covers most real channel membership with no
            # truncation.
            shown = uniq[:3]
            cut = len(uniq) - len(shown)
            # ⛔ A GENEROUS PER-ITEM CHARACTER BUDGET, NOT A STINGY ONE. A truncation that
            # reliably removes the payload word or amputates a number mid-digit is not a
            # summary, it is a redaction — and a WRONG-looking number (a count truncated from
            # "12" to "1") is worse than a missing one, because it gets believed. 88 characters
            # per item leaves room for a producer name and a real sentence.
            items = "; ".join(
                f"{r.get('producer', '?')} {str(r.get('summary', ''))[:88]}".strip()
                for r in shown)
            out.append(f"{ch}: {items}" + (f" (+{cut} more)" if cut else ""))
        return out
    except Exception:
        return []


def _diverse_top(broken, cap):
    """Fill the visible slots with at most ONE ROW PER PRODUCER.

    WHY THIS EXISTS. Ranking alone is not enough when the cap is small. One producer can hold
    five ERROR rows sharing a single timestamp and take all three slots by itself, so a
    genuinely different producer's finding — the thing that actually needed attention — stays
    buried at a much lower rank, invisible, no matter how the sort is tuned. **One noisy
    producer can mask every other producer on the system, and the more broken it is the more
    completely it masks them.**

    ⚠ THE DEEPER POINT, worth keeping when this code is next touched: a producer that emits the
    same standing-state row over and over (a source that's simply unavailable, reported as a
    DECISION through the FAULT channel because it has nowhere else to go) can never clear, so
    without this cap it would hold its slots forever. The real architectural fix is routing
    standing-state producers to a status tile instead of the findings channel; this is the
    display fix that stops one producer monopolising a 3-slot budget in the meantime, and it
    stays correct after that migration happens.

    BACKFILL: if there are fewer distinct producers than `cap`, fill the remaining slots in rank
    order rather than showing fewer findings than we have room for — diversity is preferred, not
    enforced at the cost of an empty slot. So a system with ONE broken producer still shows three
    of its rows, exactly as before.

    The caller's `cut` count is unaffected: it is `len(broken) - len(shown)`, so the "+N more not
    shown" figure stays honest however the slots were filled.

    ⭐ ORDER BY OLDEST, REPRESENT BY NEWEST. These are two different questions, and conflating
    them can hide a finding that matters.
      · WHICH producers get the slots, and in what order → by their OLDEST row. A long-standing
        problem must not be pushed down the list by a newer one; that is the objection to
        flipping the global tiebreak to newest-first, which buries old unfixed faults.
      · WHICH ROW represents a producer in its single slot → its NEWEST at that producer's best
        rank. A one-row summary of a producer should say what is wrong with it NOW, not what was
        wrong with it first.
    Concretely: a single producer can hold both an old, already-stale finding and a brand-new,
    more urgent one at the same rank. Oldest-representative would show the stale one; the
    newest-at-best-rank rule shows the urgent one instead. Same producer, same slot, same rank —
    the only thing deciding which one gets read is this tiebreak.
    """
    # Group by producer, keeping each producer's BEST rank and, within that rank, its NEWEST row.
    best = {}
    for r in broken:                       # `broken` is already (rank, ts)-ascending from caller
        producer = r.get("producer", "?")
        rank = _STATUS_RANK.get(r.get("status"), 9)
        ts = r.get("ts") or ""
        cur = best.get(producer)
        if cur is None:
            best[producer] = {"rank": rank, "oldest_ts": ts, "row": r, "row_ts": ts}
            continue
        if rank < cur["rank"]:             # a worse status wins the producer's slot outright
            cur.update(rank=rank, oldest_ts=ts, row=r, row_ts=ts)
        elif rank == cur["rank"] and ts > cur["row_ts"]:
            cur["row"] = r                 # same rank -> represent with the NEWER row
            cur["row_ts"] = ts
        # `oldest_ts` is never advanced: it is the producer's ORDERING key and must stay the
        # earliest sighting at its best rank, so ordering is unaffected by newer rows arriving.

    # WEIGHT FIRST, then severity, then oldest-first within a tier. See `_weight()` for the
    # reasoning: a stale experimental ERROR should not be able to hold slot 1 while a fresher,
    # load-bearing finding sits buried lower down. Severity was never wrong — it was just
    # answering a different question than "what needs to be seen."
    ordered = sorted(best.values(),
                     key=lambda e: (_weight(e["row"].get("producer")), e["rank"], e["oldest_ts"]))
    shown = [e["row"] for e in ordered[:cap]]
    if len(shown) >= cap:
        return shown
    if len(shown) < cap:                   # fewer distinct producers than slots — backfill
        picked = {id(r) for r in shown}
        for r in broken:
            if id(r) in picked:
                continue
            shown.append(r)
            if len(shown) >= cap:
                break
    return shown

# THE EFFICIENCY CONSUMER. Hospital (above) detects+ranks problems the system has with itself;
# Efficiency is its mirror one step further down the pipe: findings -> a reasoner ->
# emit_recommendation.py -> state/recommendations/<altitude>.<machine>.jsonl -> THIS review
# surface -> a human acts. Same reasoning as the Hospital consumer above applies doubly here —
# "a writer with no reader" is a proven failure mode, so this closes the loop for
# recommendations specifically. A recommendation store nobody reads is the same disease, so it
# rides the ONE surface in this system proven to be seen without anyone choosing to look: the
# session banner.
#
# Read via `recommendations_reader.py` (a union reader modeled byte-for-byte on
# `findings_reader.py`'s shape but NOT a shared import — see that module's docstring) and
# `recommendation_disposition.py` (an accept/reject store — a fingerprint with a recorded
# disposition STOPS appearing here; that IS the "recordable back" mechanism this exists to
# provide).
#
# ALTITUDE RANK — a JUDGMENT CALL, not specified anywhere upstream: DECISION ranks first, then
# ORGANISM, then SUBSYSTEM, then INSTANCE. Reasoning: `emit_recommendation.py`'s own docstring
# frames altitude as "how big a swing is this asking a human to make" — an INSTANCE fix is a
# five-minute decision a human can act on any time without much cost to deferring it, while a
# DECISION-altitude recommendation is explicitly the case that is NOT a mechanical fault at all
# — it is a request for a human's judgment call, the one thing this review surface exists to
# route to a human in the first place. Surfacing the biggest asks first means the rarest,
# highest-leverage recommendations don't get buried under a pile of small ones the same way
# _findings_line() already refuses to bury a stale producer under a chattier one.
_ALTITUDE_RANK = {"DECISION": 0, "ORGANISM": 1, "SUBSYSTEM": 2, "INSTANCE": 3}
_RECS_CAP = 3        # same "show the top 3, SAY how many more" cap as findings, for parity
RECOMMENDATIONS_READ_TIMEOUT_S = 8   # same hang-guard budget as FINDINGS_READ_TIMEOUT_S


class _FindingsReadTimeout(Exception):
    """Raised by the SIGALRM handler below; never escapes _findings_line()."""


class _RecsReadTimeout(Exception):
    """Raised by the SIGALRM handler below; never escapes _fetch_recommendations()."""


def _fetch_deadman_report():
    """Fetch `findings_deadman.findings_report_with_deadman()` ONCE, under the same hang-
    guard `_findings_line()` always used, and hand the result to BOTH `_findings_line()`
    (the Hospital-derived FINDINGS line) and `main()`'s ledger-staleness fallback — so the
    source-tree scan + `crontab -l` read inside `load_producer_roster()` runs once per session,
    not twice.

    Returns `(report, None)` on success, or `(None, error_line)` on timeout/exception —
    `error_line` is the exact "FINDINGS: ..." text `_findings_line()` used to return inline
    before this was split out; callers print it in place of a normal findings line. NEVER
    RAISES, NEVER HANGS PAST FINDINGS_READ_TIMEOUT_S — same contract as before the split."""
    have_alarm = (hasattr(signal, "SIGALRM")
                  and threading.current_thread() is threading.main_thread())
    old_handler = None

    def _on_alarm(signum, frame):
        raise _FindingsReadTimeout()

    try:
        if have_alarm:
            old_handler = signal.signal(signal.SIGALRM, _on_alarm)
            signal.alarm(FINDINGS_READ_TIMEOUT_S)
        try:
            here = os.path.dirname(os.path.abspath(__file__))
            if here not in sys.path:
                sys.path.insert(0, here)
            from findings_deadman import findings_report_with_deadman  # lazy: a broken sibling
            report = findings_report_with_deadman()       # must not break THIS module's import
        finally:
            if have_alarm:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
    except _FindingsReadTimeout:
        return None, (f"FINDINGS: read timed out after {FINDINGS_READ_TIMEOUT_S}s — Hospital "
                "picture unavailable this session (the notes root's mount may be wedged)")
    except Exception as e:
        # ⛔ DO NOT "FAIL CLOSED TO SILENCE" HERE — that is the one place in this module where
        # the house posture is WRONG. This function is HOSPITAL'S CONSUMER, and Hospital's
        # entire stated purpose is to make what is broken impossible to not-see. A consumer that
        # goes quiet when it breaks reproduces, inside the anti-silence machinery itself, the
        # exact failure that machinery exists to end. **Silence and "nothing is wrong" MUST NOT
        # look alike.** Returning ONE short line cannot break a session start (the caller
        # captures stdout and only prints when non-empty), so the safety argument for silence
        # does not hold either. `findings_report()` is documented never to raise, so reaching
        # this line is itself a finding about Hospital — say so rather than swallowing it.
        return None, f"FINDINGS: UNAVAILABLE — Hospital's reader raised {type(e).__name__} (this is a bug in Hospital, not an all-clear)"
    return report, None


def _fetch_recommendations():
    """Efficiency's session-start fetch, same shape as `_fetch_deadman_report()` (SIGALRM
    hang-guard, duplicated inline for the identical main-thread-only reason, lazy import so a
    broken sibling module can't break THIS module's own import).

    Fetches `recommendations_reader.recommendations_report()` (every open recommendation)
    AND `recommendation_disposition.latest_dispositions()` (every fingerprint a human has
    already accepted/rejected) under ONE alarm window, since both are needed together to
    answer "what should still be shown" and neither read is expensive enough to budget
    separately.

    Returns `(rec_report, disposition_map, None)` on success, or `(None, None, error_line)`
    on timeout/exception — same three-way shape `_fetch_deadman_report()` uses, for the same
    reason: a caller must be able to tell "read fine, nothing open" apart from "could not
    read at all". NEVER RAISES, NEVER HANGS PAST RECOMMENDATIONS_READ_TIMEOUT_S.

    A dispositions-read failure is folded into `rec_report["degraded"]` too — showing a
    recommendation whose accept/reject status is UNKNOWN (because the disposition store
    itself couldn't be read) is worse than not showing it at all, same "degraded must be
    visible, never swallowed" rule `findings_reader.py`'s own docstring states as its whole
    reason for existing.
    """
    have_alarm = (hasattr(signal, "SIGALRM")
                  and threading.current_thread() is threading.main_thread())
    old_handler = None

    def _on_alarm(signum, frame):
        raise _RecsReadTimeout()

    try:
        if have_alarm:
            old_handler = signal.signal(signal.SIGALRM, _on_alarm)
            signal.alarm(RECOMMENDATIONS_READ_TIMEOUT_S)
        try:
            here = os.path.dirname(os.path.abspath(__file__))
            if here not in sys.path:
                sys.path.insert(0, here)
            from recommendations_reader import recommendations_report  # lazy: a broken
            from recommendation_disposition import latest_dispositions  # sibling must not
            rec_report = recommendations_report()                       # break THIS import
            disp_map, disp_report = latest_dispositions()
            if disp_report.get("degraded"):
                rec_report = dict(rec_report)
                rec_report["degraded"] = True
                prior = rec_report.get("degraded_reason", "")
                add = f"dispositions read degraded: {disp_report.get('degraded_reason', '')}"
                rec_report["degraded_reason"] = (prior + "; " + add) if prior else add
        finally:
            if have_alarm:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
    except _RecsReadTimeout:
        return None, None, (
            f"RECOMMENDATIONS: read timed out after {RECOMMENDATIONS_READ_TIMEOUT_S}s — "
            "Efficiency picture unavailable this session (the notes root's mount may be wedged)")
    except Exception as e:
        # Same anti-silence posture as _fetch_deadman_report()'s except-branch above, applied
        # to Efficiency: this exists BECAUSE a writer-with-no-reader is a proven failure mode. A
        # consumer that goes quiet on its own failure reproduces that same disease one layer up
        # — say so rather than swallow it.
        return None, None, (
            f"RECOMMENDATIONS: UNAVAILABLE — Efficiency's reader raised {type(e).__name__} "
            "(this is a bug in Efficiency, not an all-clear)")
    return rec_report, disp_map, None


def _findings_line(report, reachability_shown=True) -> str:
    """Render `report` (already fetched by `_fetch_deadman_report()`) into a RANKED,
    honestly-truncated line, or "" when there is genuinely nothing to say.

    RANKING RULE: collapse to the LATEST row per fingerprint first — a fingerprint is a
    finding's stable identity (label set), and this line must show its CURRENT state, not
    every historical run that ever touched it; a fingerprint whose latest run is OK is not
    "broken" even if an older run was. Of what remains non-OK, sort by (status severity,
    then OLDEST ts first within a tier) — the failure this module exists to prevent is a pile
    of findings sitting unread for days; ranking by newest-first would bury exactly that kind
    of neglected-but-old problem under whatever fired five minutes ago. Cap at _FINDINGS_CAP
    and always state the cut count — a silent truncation is the unread-pile failure in a new
    shape.

    DEGRADATION: if findings_report() itself comes back `degraded` (unreadable shard, bad
    JSON lines, notes root unreachable), that is stated too — a clean-looking line built on an
    incomplete read is worse than no line, because it gets trusted.

    Never raises given a well-formed `report` dict — the fetch-time failure modes
    (timeout/exception) are handled by `_fetch_deadman_report()`, not here.
    """
    rows = report.get("rows", []) or []
    degraded = report.get("degraded", False)
    reason = report.get("degraded_reason", "")

    latest = _collapse_latest(rows)   # keyed (producer, fingerprint), never a bare fingerprint

    # ⛔ CHANNELLED PRODUCERS LEAVE THE RANKED POOL. They get their own fixed line
    # (`_channel_lines()`), so leaving them here would show them TWICE and let a duplicate
    # consume a slot a real fault needs. Every count on this line is therefore computed over
    # what still COMPETES — see `_CHANNELS`' comment for why that keeps the arithmetic honest.
    # `_REACHABILITY_PRODUCER` leaves too: it already has a dedicated line of its own, and
    # leaving it in the pool would print it TWICE — the same double-count the channel rule
    # exists to prevent, just via a different door. Any producer with its own surface leaves
    # the pool; that is the general rule, and the two exits below are the only ways to have one.
    # ⛔⛔ EVICT ONLY WHEN THE OTHER SURFACE ACTUALLY SPOKE. `_reachability_line()` renders
    # NOTHING on a malformed/absent payload — its own docstring admits "malformed" and
    # "genuinely clean" collapse to the same silent return. Two gates, neither aware of the
    # other's failure mode, could otherwise cut a row from the pool by gate 1, decline it at
    # gate 2, and leave it visible NOWHERE. Twice is cosmetic; nowhere is fatal.
    _own_line = set(_CHANNELS) | ({_REACHABILITY_PRODUCER} if reachability_shown else set())
    broken = [r for r in latest.values()
              if r.get("status") in _STATUS_RANK and r.get("producer") not in _own_line]
    broken.sort(key=lambda r: (_STATUS_RANK.get(r.get("status"), 9), r.get("ts") or ""))

    # ── THE SILENCE MARKER. ⭐ THE DEAD-MAN'S SWITCH CAN WORK AS A CALCULATOR AND STILL FAIL
    # AS A SWITCH, and this is the fix. ──────────────────────────────────────────────────────
    # `_diverse_top()` gives each producer ONE slot and resolves it worst-status-wins. But
    # ERROR and STALE are NOT two severities of one axis — they are different KINDS of
    # statement: "this producer is BROKEN" vs "this producer is GONE." Collapsing them means a
    # producer that is BOTH can only ever show as broken.
    # ⛔ NOT A CORNER CASE: a producer with a standing ERROR that never clears (a source that's
    # simply unavailable, say) can ALSO go internally STALE — stop emitting new findings
    # altogether — without the word STALE ever appearing in the banner, because ERROR outranks
    # STALE and wins that producer's one slot every time. **That producer's silence becomes
    # mathematically incapable of ever being displayed.** Hospital's whole reason for existing
    # is that "no finding" and "found nothing" must never look alike; the ranking was quietly
    # reintroducing exactly that collapse at the render layer.
    # ⇒ SILENCE IS A PROPERTY OF A PRODUCER, NOT A ROW COMPETING FOR ITS SLOT. Annotate the row
    # the producer already won. Costs ZERO extra slots, changes no rank, and cannot mask
    # anything — it only ever ADDS a word to a line that was already going to be shown.
    # ⚠ Read off the SAME report (`producer_deadman`) this function already has — never a second
    # fetch, per this module's "ONE DEAD-MAN SWITCH, NOT TWO" rule.
    silent = {}
    for d in (report.get("producer_deadman") or []):
        if d.get("state") == "STALE" and d.get("producer"):
            silent[d["producer"]] = d.get("age_s")

    def _silence(r):
        """" ⏸SILENT <age>" when this producer has gone quiet, else "". A row whose OWN status
        is already STALE says it once, not twice."""
        p = r.get("producer")
        if p not in silent or r.get("status") == "STALE":
            return ""
        a = silent[p]
        return f" ⏸SILENT {age(a)}" if isinstance(a, (int, float)) else " ⏸SILENT"

    if not broken and not degraded:
        return ""                     # nothing broken, read was clean => say nothing

    parts = []
    if broken:
        shown = _diverse_top(broken, _FINDINGS_CAP)
        cut = len(broken) - len(shown)
        # A GENEROUS PER-ITEM CHARACTER BUDGET. A short cutoff reliably amputates the payload
        # word — a truncation that removes the one token that tells the reader WHY a row
        # matters (e.g. the word DANGER in a security summary) is not a summary, it is a
        # redaction. 60 characters clears a typical DANGER-bearing summary while keeping the
        # whole line to roughly one banner line. `_FINDINGS_CAP` (how MANY rows) is unaffected
        # by this — this is only how much of each row survives.
        # The silence marker sits immediately after the STATUS, deliberately BEFORE the
        # 60-char summary truncation, so it can never be the thing that gets amputated.
        items = "; ".join(
            f"{r.get('producer', '?')}:{r.get('status', '?')}{_silence(r)} "
            f"{str(r.get('summary', ''))[:60]}".strip()
            for r in shown
        )
        cut_str = f" (+{cut} more not shown)" if cut > 0 else ""
        parts.append(f"{len(broken)} finding(s): {items}{cut_str}")
    if degraded:
        parts.append(f"findings read DEGRADED: {reason}")
    return "FINDINGS: " + " · ".join(parts)


def _recommendations_line(rec_report, disposition_map) -> str:
    """Render `rec_report`/`disposition_map` (already fetched by `_fetch_recommendations()`)
    into a RANKED, honestly-truncated line, or "" when there is genuinely nothing open to show.
    Same shape as `_findings_line()` on purpose — one session banner, one visual grammar, so a
    session start doesn't grow a second, differently-styled block the reader has to learn to
    parse separately.

    RANKING RULE: collapse to the LATEST row per fingerprint first (same reason
    `_findings_line()` does — a fingerprint's CURRENT emission is what matters). Any
    fingerprint present in `disposition_map` (accepted OR rejected) is dropped — THIS is the
    "recordable back" mechanism this module needs: a disposed-of recommendation stops
    appearing here, permanently, once `recommendation_disposition.py` has a row for it. Of
    what remains OPEN, rank by (altitude tier via `_ALTITUDE_RANK`, then OLDEST ts first
    within a tier) — same anti-neglect ordering `_findings_line()` uses, so a recommendation
    that has sat unreviewed the longest is never buried under one two minutes old. Cap at
    `_RECS_CAP` and always state the cut count.

    Each shown item includes the recommendation's first 8 fingerprint characters in brackets
    — the exact prefix `recommendation_disposition.py --fingerprint <prefix> --decision
    accept|reject` accepts and resolves unambiguously (or refuses loudly if the prefix is
    ambiguous) — so the line a human reads is also the line they can act on directly, without
    a second lookup step.

    DEGRADATION: surfaced exactly like `_findings_line()` — see that function's own
    docstring for why a clean-looking line built on an incomplete read is worse than no line.

    Never raises given well-formed inputs — fetch-time failures are handled by
    `_fetch_recommendations()`, not here.
    """
    rows = rec_report.get("rows", []) or []
    degraded = rec_report.get("degraded", False)
    reason = rec_report.get("degraded_reason", "")

    # SAME collapse rule as the findings line, and it applies here too: a fingerprint-less row
    # dropping silently and letting one producer's fingerprint evict another's is the same bug
    # in a different channel.
    latest = _collapse_latest(rows)

    open_recs = [r for r in latest.values() if r.get("fingerprint") not in disposition_map]
    open_recs.sort(key=lambda r: (_ALTITUDE_RANK.get(r.get("altitude"), 9), r.get("ts") or ""))

    if not open_recs and not degraded:
        return ""                     # nothing open, read was clean => say nothing

    parts = []
    if open_recs:
        shown = open_recs[:_RECS_CAP]
        cut = len(open_recs) - len(shown)
        items = "; ".join(
            f"{r.get('altitude', '?')} {str(r.get('action', ''))[:40]} "
            f"[{str(r.get('fingerprint', ''))[:8]}]".strip()
            for r in shown
        )
        cut_str = f" (+{cut} more not shown)" if cut > 0 else ""
        parts.append(f"{len(open_recs)} recommendation(s): {items}{cut_str}")
    if degraded:
        parts.append(f"recommendations read DEGRADED: {reason}")
    return "RECOMMENDATIONS: " + " · ".join(parts)



# SESSION-START GAUGE VERDICT. `gauge_check.py` (`system/tools/checkin/gauge_check.py`)
# referees a brief's ## CURRENT STATE section but is wired only into `/checkin` — a session
# that never runs `/checkin` never sees a verdict. This reuses the ONE channel already proven
# to be seen unasked (this module, called from session_context_loader.sh at every
# SessionStart) rather than adding a second enforcement surface.
#
# Scope is deliberately narrow: the ARMED project only (via pm_flag.sh status — "none" means
# say nothing), and only the four non-healthy verdicts (COMPETING-GAUGES, OVERSIZED, STALE,
# NO-GAUGE) — ONE-GAUGE is healthy and stays silent, and CANNOT-READ is a check-time failure
# (unreadable file, no §2), not a status worth nagging about, so it stays silent too.
#
# ⚠ UNLIKE the Hospital/Efficiency consumers above, this one is QUIET on its own failure, not
# loud — a DELIBERATE reversal of this module's usual "say so, don't swallow" posture. Those
# two subsystems exist to make problems impossible to not-see; this feature is a courtesy
# projection of a check that already has its own enforcement surface (/checkin) and its own
# exit codes. A broken pm_flag.sh/gauge_check.py call here must never contaminate session
# start with a traceback or a scary-looking degraded line over what is, worst case, a missing
# or edited-out script.
GAUGE_TIMEOUT_S = 5
_GAUGE_SPEAK_ON = {"COMPETING-GAUGES", "OVERSIZED", "STALE", "NO-GAUGE"}


def _gauge_detail(verdict: str, data: dict) -> str:
    """One short clause describing WHY, per verdict. Never raises on a malformed `data` —
    every field access is `.get()` with a safe fallback string."""
    if verdict == "COMPETING-GAUGES":
        n = data.get("n_surfaces")
        return f"{n} status surfaces in §2" if n is not None else "multiple status surfaces in §2"
    if verdict == "OVERSIZED":
        sl = data.get("section_lines")
        pct = data.get("percent_of_story_log")
        if sl is not None and pct is not None:
            return f"§2 is {sl} lines ({pct:.0f}% of story log)"
        if sl is not None:
            return f"§2 is {sl} lines"
        return "§2 over size budget"
    if verdict == "STALE":
        gd, nd = data.get("gauge_date"), data.get("newest_story_log_date")
        if gd and nd:
            return f"gauge {gd} predates story log entry {nd}"
        return "§2 predates the newest story log entry"
    if verdict == "NO-GAUGE":
        return "§2 has no status surface at all"
    return verdict


def _collapse_latest(rows):
    """Collapse rows to the LATEST per finding — the ONE place that decision is made.

    ⛔⛔ TWO HOLES A NAIVE IMPLEMENTATION CAN HAVE, BOTH FOUND BY ADVERSARIAL TESTING. A first
    draft of this inlined `latest[fingerprint] = r`, keyed on the **bare fingerprint**, and
    dropped any row whose fingerprint was falsy with a silent `continue`. Two holes, both
    upstream of every safeguard in `_weight()` / `_STATUS_RANK` / `_diverse_top()` — so this
    module's own loud promise (*"DEMOTED, NEVER HIDDEN … still counts in the total"*) was only
    ever enforced for rows that survived a step that had no such guarantee.

    **REPRODUCED BEFORE FIXING, both live:**
    - **Cross-producer collision.** A high-severity `ERROR` from one producer and a lower-
      severity `NEEDS_REVIEW` from another, sharing one fingerprint, rendered as only the
      LOWER one — the load-bearing row was not demoted, it was **gone**: absent from the line,
      absent from the count, and absent from `(+N more)` because `len(broken)` had already been
      deflated.
    - **Falsy fingerprint.** A row with `fingerprint=None` vanished with no trace at all.
    ⇒ Keyed by **`(producer, fingerprint)`** so one producer can never consume another's slot,
    and a fingerprint-less row gets its **own** key (never dropped) — if it is malformed we would
    rather show it twice than lose it once. **Losing a row is the only unrecoverable outcome here.**
    """
    latest = {}
    for i, r in enumerate(rows or []):
        fp = r.get("fingerprint")
        key = (r.get("producer"), fp) if fp else (r.get("producer"), "\x00nofp", i)
        ts = r.get("ts") or ""
        cur = latest.get(key)
        if cur is None or ts >= (cur.get("ts") or ""):
            latest[key] = r
    return latest


def _reachability_line(report) -> str:
    """THE AMBIENT LAYER. One line: how many of this system's own tools have a command-line
    entry point that nothing invokes, and how to see WHICH.

    ⛔⛔ WHY THIS IS A DEDICATED LINE AND NOT A FINDINGS ROW. The reachability cohort emits at
    `NEEDS_REVIEW` (its class OVER-REPORTS, so nothing forbids anything louder — see
    `reachability_finding.py`, if/when it ships). But `_findings_line()` shows only **3** slots
    ranked by `_STATUS_RANK`, and it is easy for six OTHER producers to be sitting at `ERROR`
    at the same moment — the reachability row then ranks outside the visible slots and lands in
    "(+N more not shown)" — **written, read, counted, and never once displayed.** Emitting
    harder cannot fix that, and ranking it higher would let an admittedly-inflated list outrank
    a live DANGER event.
    ⭐ THE REAL DIAGNOSIS: this is STANDING ARCHITECTURAL STATE, not an acute fault, and the
    3-slot rank was being asked to arbitrate between two different KINDS of thing. A standing
    signal that must never be missed does not belong in a budget it can only win by shouting.
    So it gets its own line and stops competing.

    ⛔ A COUNT AND A HANDLE. NEVER A LIST. The whole point of a lean context window is that
    tools and detail appear only when they're needed, not paraded up front "just in case." A
    count is O(1); the moment this line carries tool NAMES it becomes exactly the kind of
    over-injection that principle exists to prevent, and it will grow, because every new tool
    will look like it deserves a line. The full cohort stays ON DISK and is PULLED by the one
    command named here.

    ⭐ NO NEW FETCH — takes the report `main()` already has. Same "ONE DEAD-MAN SWITCH, NOT TWO"
    rule this module states for `_findings_line()`: a second read of the same store is a second
    place the two answers can disagree.

    ⚠ STALENESS IS ALREADY HANDLED, ELSEWHERE, AND ON PURPOSE. This function renders whatever
    the newest row says and does NOT re-derive freshness — because `architecture-reachability`
    is on the dead-man's roster (it is discoverable via its lowercase `producer="…"` literal,
    and its Pulse job name matches its producer name). If the weekly job dies, the deadman emits
    a synthetic `STALE` row that surfaces in `_findings_line()` at rank 0. ⇒ **a frozen number
    here can never look healthy** — the staleness alarm lives one line up, where it already works.

    Returns "" (say NOTHING) when: no such finding exists yet · the row is malformed · the count
    is 0 (nothing to act on — the same silence-when-clean rule the rest of this module follows).
    Never raises.
    """
    try:
        rows = [r for r in (report or {}).get("rows", [])
                if r.get("producer") == _REACHABILITY_PRODUCER]
        if not rows:
            return ""
        newest = max(rows, key=lambda r: r.get("ts", ""))
        n = newest.get("unwired_n")
        m = newest.get("tool_files_examined")
        if not isinstance(n, int) or not isinstance(m, int) or n <= 0 or m <= 0:
            return ""                       # absent, malformed, or genuinely clean => silence
        # ⚠ BOTH NUMBERS, ALWAYS: a bare N cannot be told apart from a walk that examined N
        # files and flagged all of them, and only the denominator makes a STALL visible — if
        # the numerator never moves, M proves the walk still ran.
        return (f"REACHABILITY: {n} of {m} tool files have a command-line entry point that "
                f"nothing invokes · list: reachability_finding.py --dry-run")
    except Exception:
        return ""


def _gauge_line() -> str:
    """The armed project's brief-gauge verdict, or "" (say NOTHING) when:
      - no project is armed (pm_flag.sh status == "none"/empty),
      - pm_flag.sh or gauge_check.py is missing/erroring/timing out,
      - the verdict is a healthy ONE-GAUGE, or a check-time CANNOT-READ.
    Only COMPETING-GAUGES / OVERSIZED / STALE / NO-GAUGE produce a line. See the module-level
    comment above for why this one function is quiet-on-failure rather than this module's
    usual loud-on-failure posture.

    Subprocess, not import: gauge_check.py is a CLI tool with its own argparse `main()`,
    owned by another concern — shelling out to its documented `check <brief> --json` contract
    is the same "don't reach into a sibling's internals" idiom `_fetch_deadman_report()`'s lazy
    import already uses one level down. Never raises.
    """
    try:
        import subprocess
        here = os.path.dirname(os.path.abspath(__file__))
        pm_flag = os.path.join(here, "..", "hooks", "pm_flag.sh")
        gauge_check = os.path.join(here, "checkin", "gauge_check.py")

        status = subprocess.run(
            ["bash", pm_flag, "status"],
            capture_output=True, text=True, timeout=GAUGE_TIMEOUT_S,
        )
        brief_path = (status.stdout or "").strip()
        if not brief_path or brief_path == "none":
            return ""                       # no project armed => say nothing

        check = subprocess.run(
            [sys.executable, gauge_check, "check", brief_path, "--json"],
            capture_output=True, text=True, timeout=GAUGE_TIMEOUT_S,
        )
        data = json.loads(check.stdout)
        verdict = data.get("verdict")
        if verdict not in _GAUGE_SPEAK_ON:
            return ""                       # ONE-GAUGE (healthy) or CANNOT-READ => silent
        return f"⚠ brief gauge: {verdict} — {_gauge_detail(verdict, data)} · run /checkin"
    except Exception:
        return ""                           # missing/broken dependency => NEVER speak, never break session start


def main() -> int:
    if len(sys.argv) < 2:
        return 0
    path = sys.argv[1]
    lines = []

    # ONE fetch, shared below by the ledger's narrow staleness fallback AND the FINDINGS line
    # — see module docstring "ONE DEAD-MAN SWITCH, NOT TWO".
    deadman_report, deadman_err = _fetch_deadman_report()

    try:
        with open(path) as fh:
            d = json.load(fh)
    except FileNotFoundError:
        lines.append(f"HEALTH: ledger MISSING ({path}) — health tracking is BLIND")
    except Exception as e:
        lines.append(f"HEALTH: ledger CORRUPT ({path}): {e} — health tracking is BLIND")
    else:
        now = time.time()
        faults = d.get("faults", {}) or {}
        cadences = _cadences(PULSE_CONFIG)
        producers = d.get("producers", {}) or {}
        # `covered` = producers the REAL dead-man switch (findings_deadman.py) already
        # watches this run — derived from the SAME report the FINDINGS line below renders,
        # never a hand-typed name list (see module docstring). A producer in `covered` gets
        # its staleness verdict from ONE place only: the synthetic STALE row in the
        # FINDINGS line, not here. If the fetch itself failed (`deadman_report is None`),
        # `covered` stays empty and this check widens back to every ledger producer — a
        # safety-net fallback, never a silent narrowing on top of a broken fetch.
        covered = ({d2["producer"] for d2 in deadman_report.get("producer_deadman", [])}
                   if deadman_report is not None else set())
        bad = sorted({
            n for n, r in producers.items()
            if r.get("rc", 0) != 0
            or (n not in covered
                and (now - r.get("ts", now)) > 2 * cadences.get(n, DEFAULT_CADENCE_S))
        })
        if faults or bad:                 # healthy => say nothing (this part of the line)
            parts = []
            if faults:
                worst = max(faults.values(), key=lambda r: now - r.get("first_seen", now))
                parts.append(f"{len(faults)} job(s) DOWN (worst {age(now - worst.get('first_seen', now))})")
            if bad:
                parts.append(f"{len(bad)} producer(s) failing: {', '.join(bad)}")
            lines.append("HEALTH: " + " · ".join(parts))

    # Reachability computed FIRST so `_findings_line()` knows whether it spoke.
    reachability_line = _reachability_line(deadman_report) if deadman_report is not None else ""
    findings_line = deadman_err if deadman_err else (
        _findings_line(deadman_report, reachability_shown=bool(reachability_line))
        if deadman_report is not None else "")
    if findings_line:
        lines.append(findings_line)

    # THE AMBIENT LAYER, on its own line. Reuses the SINGLE deadman fetch above (never a
    # second read of the same store). It sits here, directly under FINDINGS, because it is
    # finding-DERIVED — but deliberately OUTSIDE the 3-slot rank, because it is standing
    # architectural state rather than an acute fault and is measurably easy to bury inside it.
    # Full reasoning: `_reachability_line()`'s own docstring.
    if reachability_line:
        lines.append(reachability_line)

    # THE FIXED CHANNELS — e.g. money · calendar · system, once `_CHANNELS` is populated. Each
    # is silent when clean and never competes with the ranked line above. Same single fetch.
    if deadman_report is not None:
        lines.extend(_channel_lines(deadman_report))

    # The Efficiency review surface, appended alongside (never replacing) the Hospital
    # findings line above. Same fetch-then-render split, same never-raise contract, same
    # "silence when clean, loud when broken" rule — see _fetch_recommendations()'s and
    # _recommendations_line()'s own docstrings for the full reasoning.
    rec_report, disposition_map, rec_err = _fetch_recommendations()
    recommendations_line = rec_err if rec_err else (
        _recommendations_line(rec_report, disposition_map) if rec_report is not None else "")
    if recommendations_line:
        lines.append(recommendations_line)

    # The armed project's brief-gauge verdict, appended alongside (never replacing) the lines
    # above. Quiet on no-project-armed, quiet on a healthy verdict, quiet on its own failure —
    # see _gauge_line()'s own docstring for why this one is the exception to this module's
    # usual loud-on-failure posture.
    gauge_line = _gauge_line()
    if gauge_line:
        lines.append(gauge_line)

    if not lines:
        return 0
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)

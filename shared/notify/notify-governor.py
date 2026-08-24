#!/usr/bin/env python3
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: the failure mode of anything that can reach your phone is not that it goes wrong —
#      it is that it goes off too often. Three notifications that turned out to be nothing
#      and you stop reading the fourth; mute it and the whole layer becomes decoration.
#      That is not a discipline problem to be solved later by sending fewer: it is a cap
#      that has to exist BEFORE there is anything to send, so that no dispatch path added
#      afterwards can flood anyone, including one written in a hurry at 2am.
# WHAT: a pure decision gate. Everything that pushes MUST ask here first and may only fire
#       on ALLOW. It records each allowed send, so the rate and duplicate state is real
#       rather than advisory — a gate that does not remember is a suggestion.
# REDIRECT: to send something, call this. Never dispatch directly. State lives in a temp
#           file on purpose: a reboot resetting the counters costs at worst one extra buzz,
#           and persisting it would mean a stale counter silencing something that matters.
# UPDATED: 2026-08-11 (ported)
# ─────────────────────────────────────────────────────────────────────────────
# notify-governor.py <source> <message> [priority] [identity]
#   priority: normal (default) | critical (bypasses quiet hours + daily cap; still dedups)
#           | misconfig (T10.A3 OL-N1 ⑤: a PERMANENT-until-fixed condition — e.g. a required env
#             var nobody has set — is not news twice. Dedups like normal but over a ~1-year
#             floor instead of 24h, so the SAME misconfig alerts once and then stands down. Still
#             respects quiet hours + the daily cap like normal, since it is not urgent.)
#   identity: OPTIONAL. When given, DEDUP KEYS ON THIS INSTEAD OF <message> (T10.A3 OL-N1 ④).
#             Use it whenever a message embeds a value that changes every call (an age, a
#             percentage, a byte count) — hashing the raw message defeats dedup because every
#             call produces a "new" (source,message) pair. Pass a STABLE string that names the
#             identity of the alert ("stale-store", "budget-exceeded:job-x") separately from the
#             human-readable <message>, which keeps carrying the live number for the reader.
# Exit 0 + "ALLOW" on stdout  -> caller should send (the send is now recorded).
# Exit 1 + "SUPPRESS: <reason>" on stderr -> caller must NOT send.
#
# Config via env (all optional):
#   NOTIFY_QUIET_START (22)  NOTIFY_QUIET_END (7)  -> quiet window [start,end) local hours
#   NOTIFY_DAILY_CAP   (3)   per-source allowed sends per rolling 24h
#   NOTIFY_DEDUP_HOURS (24)  identical (source,identity-or-message) suppressed within this window
#   NOTIFY_MISCONFIG_DEDUP_HOURS (8760)  same, for priority=misconfig — ~1 year, i.e. "once"
#   NOTIFY_STATE_FILE  (<tmp>/lifehack-notify-state.json)
#
# NOTE: auto-mute-after-false-alerts is intentionally NOT in v1 — it needs a
#       feedback channel ("that was a false alert") we don't have yet. Add later.

import sys, os, json, time, hashlib, fcntl

STATE = os.environ.get("NOTIFY_STATE_FILE",
                       os.path.join(os.environ.get("TMPDIR", "/tmp"), "lifehack-notify-state.json"))
QUIET_START = int(os.environ.get("NOTIFY_QUIET_START", "22"))
QUIET_END   = int(os.environ.get("NOTIFY_QUIET_END", "7"))
DAILY_CAP   = int(os.environ.get("NOTIFY_DAILY_CAP", "3"))
DEDUP_HOURS = int(os.environ.get("NOTIFY_DEDUP_HOURS", "24"))
# Critical alerts dedup within a SHORT floor only, so a recurring same-day DANGER
# still buzzes (a full 24h dedup could silently eat it) while a stuck source can't
# flood every 5-min tick. Set to 0 to disable critical dedup entirely.
CRITICAL_DEDUP_HOURS = int(os.environ.get("NOTIFY_CRITICAL_DEDUP_HOURS", "1"))
# Critical BURST-COALESCE: one incident can trip several DISTINCT-message criticals
# from a single source within seconds (e.g. one scan matching 5 patterns). The
# message-hash dedup below can't collapse those (different messages -> different
# hashes), so each would buzz. Coalesce by SOURCE (ignoring message) within a short
# window: the push is a doorbell ("go look"), not the payload -- every event is still
# in the ledger/tile. A genuinely separate incident AFTER the window still rings.
# Set to 0 to disable.
CRITICAL_BURST_MINUTES = int(os.environ.get("NOTIFY_CRITICAL_BURST_MINUTES", "10"))
# T10.A3 OL-N1 ⑤: a PERMANENT misconfiguration (missing required config, etc.) is not news
# twice. ~365 days is "effectively once, until someone fixes it and the identity changes" without
# inventing a second never-expire code path next to the existing time-windowed one.
MISCONFIG_DEDUP_HOURS = int(os.environ.get("NOTIFY_MISCONFIG_DEDUP_HOURS", str(365 * 24)))
# T10.A3 OL-N1 ⑥: normal-priority sends dropped ONLY for quiet hours (not dedup, not cap) are
# queued here instead of silently lost, so a once-a-day digest that happens to land at 23:50
# still reaches the phone once quiet hours lift — see flush_deferred() and --flush-deferred below.
DEFERRED_MAX_AGE_HOURS = int(os.environ.get("NOTIFY_DEFERRED_MAX_AGE_HOURS", "18"))


def in_quiet_hours(hour):
    # Window may wrap midnight (e.g. 22 -> 7).
    if QUIET_START == QUIET_END:
        return False
    if QUIET_START < QUIET_END:
        return QUIET_START <= hour < QUIET_END
    return hour >= QUIET_START or hour < QUIET_END


def load_state():
    try:
        with open(STATE) as f:
            return json.load(f)
    except Exception:
        return {"sent": []}


def save_state(state):
    tmp = STATE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f)
    os.replace(tmp, STATE)


def flush_deferred():
    """--flush-deferred: replay any normal-priority sends that were queued because quiet hours
    (and ONLY quiet hours — never dedup, never cap) blocked them, now that it may no longer be
    quiet. Prints one line per item to REPLAY on stdout as `source\tmessage`, TAB-separated (the
    caller — notify-send.sh — actually performs the send); this function only decides which
    queued items are still worth sending and clears them from the queue either way (a deferred
    item beyond DEFERRED_MAX_AGE_HOURS is dropped, not sent — a stale digest arriving at noon
    about something from two nights ago is noise, not news)."""
    now = time.time()
    lock = open(STATE + ".lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = load_state()
        deferred = state.get("deferred", [])
        hour = time.localtime(now).tm_hour
        still_quiet = in_quiet_hours(hour)
        keep = []
        to_send = []
        for item in deferred:
            age_h = (now - item.get("ts", 0)) / 3600.0
            if age_h > DEFERRED_MAX_AGE_HOURS:
                continue   # too stale — dropped, not replayed
            if still_quiet:
                keep.append(item)   # still quiet hours right now — leave it queued
                continue
            to_send.append(item)
        state["deferred"] = keep
        save_state(state)
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()
    for item in to_send:
        print(f"{item.get('source', '')}\t{item.get('message', '')}\t{item.get('title', '')}\t{item.get('tags', '')}\t{item.get('url', '')}")
    return 0


def queue_deferred(args):
    """--queue-deferred <source> <message> [title] [tags] [url] — called by notify-send.sh ONLY
    when the gate just SUPPRESSED a normal-priority send for quiet hours specifically (never for
    dedup or the daily cap — those are correct to drop, not defer). Persists it so
    --flush-deferred can replay it once quiet hours lift. Best-effort: a failure here must never
    fail the caller's suppressed-is-not-an-error exit path."""
    if len(args) < 2:
        return 2
    source, message = args[0], args[1]
    title = args[2] if len(args) > 2 else ""
    tags = args[3] if len(args) > 3 else ""
    url = args[4] if len(args) > 4 else ""
    now = time.time()
    lock = open(STATE + ".lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = load_state()
        deferred = state.get("deferred", [])
        deferred.append({"ts": now, "source": source, "message": message, "title": title,
                          "tags": tags, "url": url})
        state["deferred"] = deferred
        save_state(state)
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()
    return 0


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--flush-deferred":
        return flush_deferred()
    if len(sys.argv) > 1 and sys.argv[1] == "--queue-deferred":
        return queue_deferred(sys.argv[2:])
    if len(sys.argv) < 3:
        sys.stderr.write("usage: notify-governor.py <source> <message> [priority] [identity]\n"
                          "       notify-governor.py --flush-deferred\n")
        return 2
    source = sys.argv[1].strip().lower()
    message = sys.argv[2]
    priority = (sys.argv[3].strip().lower() if len(sys.argv) > 3 else "normal")
    identity = (sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] != "" else None)
    critical = priority == "critical"
    misconfig = priority == "misconfig"

    now = time.time()
    # OL-N1 ④: hash on <identity> when the caller supplied one — a STABLE string naming what
    # this alert IS, independent of a changing number embedded in <message>. Falls back to
    # hashing <message> itself (the pre-existing behaviour) when no identity was given, so every
    # caller that hasn't been updated keeps working exactly as before.
    dedup_basis = identity if identity is not None else message
    msg_hash = hashlib.sha256(f"{source}\x00{dedup_basis}".encode()).hexdigest()

    # Serialize the read-modify-write so concurrent jobs can't both slip past the cap.
    lock = open(STATE + ".lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = load_state()
        sent = state.get("sent", [])

        # Prune anything older than the longest window we care about (including the ~1yr
        # misconfig floor, so that store doesn't grow forever on its account).
        horizon = now - max(DEDUP_HOURS, 24, MISCONFIG_DEDUP_HOURS) * 3600
        sent = [s for s in sent if s.get("ts", 0) >= horizon]

        # 1. Dedup. Critical uses a SHORT window (so a same-day repeat DANGER still buzzes);
        #    misconfig uses a ~1-YEAR floor (OL-N1 ⑤: alert once, then stand down until the
        #    identity itself changes — i.e. the misconfig is fixed or a new one appears); normal
        #    uses the full window. A short critical floor still prevents a stuck source from
        #    flooding every tick.
        if critical:
            dedup_window = CRITICAL_DEDUP_HOURS
        elif misconfig:
            dedup_window = MISCONFIG_DEDUP_HOURS
        else:
            dedup_window = DEDUP_HOURS
        if dedup_window > 0:
            dedup_floor = now - dedup_window * 3600
            if any(s.get("hash") == msg_hash and s.get("ts", 0) >= dedup_floor for s in sent):
                state["sent"] = sent
                save_state(state)
                reason = "standing down (already alerted once)" if misconfig else f"duplicate within {dedup_window}h"
                sys.stderr.write(f"SUPPRESS: {reason}\n")
                return 1

        # 1b. Critical BURST-COALESCE (source-keyed, ignores message). Collapses a
        #     flood of distinct-message criticals from ONE source into a single buzz.
        if critical and CRITICAL_BURST_MINUTES > 0:
            burst_floor = now - CRITICAL_BURST_MINUTES * 60
            if any(s.get("source") == source and s.get("crit") and s.get("ts", 0) >= burst_floor for s in sent):
                state["sent"] = sent
                save_state(state)
                sys.stderr.write(f"SUPPRESS: '{source}' critical burst-coalesce ({CRITICAL_BURST_MINUTES}m)\n")
                return 1

        if not critical:
            # 2. Quiet hours. (misconfig is NOT critical — it respects quiet hours too, since a
            #    standing misconfiguration is never an emergency worth a 3am buzz.)
            hour = time.localtime(now).tm_hour
            if in_quiet_hours(hour):
                state["sent"] = sent
                save_state(state)
                sys.stderr.write(
                    f"SUPPRESS: quiet hours ({QUIET_START:02d}:00-{QUIET_END:02d}:00, now {hour:02d}:00)\n"
                )
                return 1

            # 3. Per-source daily cap. DAILY_CAP <= 0 = UNLIMITED (cap disabled).
            if DAILY_CAP > 0:
                day_floor = now - 24 * 3600
                count = sum(1 for s in sent if s.get("source") == source and s.get("ts", 0) >= day_floor)
                if count >= DAILY_CAP:
                    state["sent"] = sent
                    save_state(state)
                    sys.stderr.write(f"SUPPRESS: '{source}' hit daily cap ({DAILY_CAP}/24h)\n")
                    return 1

        # ALLOW — record the send (crit flag lets the burst-coalesce count only criticals).
        sent.append({"ts": now, "source": source, "hash": msg_hash, "crit": critical})
        state["sent"] = sent
        save_state(state)
        print("ALLOW")
        return 0
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()


if __name__ == "__main__":
    sys.exit(main())

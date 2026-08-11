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
# notify-governor.py <source> <message> [priority]
#   priority: normal (default) | critical (bypasses quiet hours + daily cap; still dedups)
# Exit 0 + "ALLOW" on stdout  -> caller should send (the send is now recorded).
# Exit 1 + "SUPPRESS: <reason>" on stderr -> caller must NOT send.
#
# Config via env (all optional):
#   NOTIFY_QUIET_START (22)  NOTIFY_QUIET_END (7)  -> quiet window [start,end) local hours
#   NOTIFY_DAILY_CAP   (3)   per-source allowed sends per rolling 24h
#   NOTIFY_DEDUP_HOURS (24)  identical (source,message) suppressed within this window
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


def main():
    if len(sys.argv) < 3:
        sys.stderr.write("usage: notify-governor.py <source> <message> [priority]\n")
        return 2
    source = sys.argv[1].strip().lower()
    message = sys.argv[2]
    priority = (sys.argv[3].strip().lower() if len(sys.argv) > 3 else "normal")
    critical = priority == "critical"

    now = time.time()
    msg_hash = hashlib.sha256(f"{source}\x00{message}".encode()).hexdigest()

    # Serialize the read-modify-write so concurrent jobs can't both slip past the cap.
    lock = open(STATE + ".lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = load_state()
        sent = state.get("sent", [])

        # Prune anything older than the longest window we care about.
        horizon = now - max(DEDUP_HOURS, 24) * 3600
        sent = [s for s in sent if s.get("ts", 0) >= horizon]

        # 1. Dedup. Critical uses a SHORT window (so a same-day repeat DANGER still
        #    buzzes); normal uses the full window. A short critical floor still
        #    prevents a stuck source from flooding every tick.
        dedup_window = CRITICAL_DEDUP_HOURS if critical else DEDUP_HOURS
        if dedup_window > 0:
            dedup_floor = now - dedup_window * 3600
            if any(s.get("hash") == msg_hash and s.get("ts", 0) >= dedup_floor for s in sent):
                state["sent"] = sent
                save_state(state)
                sys.stderr.write(f"SUPPRESS: duplicate within {dedup_window}h\n")
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
            # 2. Quiet hours.
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

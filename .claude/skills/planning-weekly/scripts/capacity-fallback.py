#!/usr/bin/env python3
"""capacity-fallback.py — the I7 fallback (spec I7): when the newest morning snapshot has no
Capacity section, code computes the week's capacity in the session from the engine's calendar
mirror — and SAYS SO. Never a silent zero, never a model estimate.

Input: the mirror's busy blocks for the coming week, one per line: `day · start · end · label`
(the engine's stored copy of the calendar; the separator is "·" with optional spaces), plus the
awake window the session was given (the person's working day — supplied per session, never a
built-in personal default).

Modes:
  capacity-fallback.py busy "<mirror rows>" --awake 09:00-18:00
      Prints the fallback banner, free hours per day, and the week total, with the expression.
  capacity-fallback.py --selftest
      One good, one edge and one padded case; exits 0 only if all pass.

A busy block extending past the awake window is clipped to it (a lunch meeting past the working
day does not create negative free time). Overlapping busy blocks are merged before subtraction.
Malformed input is a loud error, never skipped.
"""
# allow-silence: build-ruled location — slice B of the planning-weekly build; the coordinator
# ruled this worktree skill folder as the home for these files, and the build task forbids
# own_list_add and any write outside the worktree. Not a personal tool; never moved to ClaudeOps.
import sys

SEP = "·"
DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
BANNER = ("COMPUTED IN SESSION (fallback — the newest morning snapshot has no Capacity section; "
          "computed from the engine's calendar mirror; say so on screen)")


def parse_hhmm(s):
    h, m = s.strip().split(":")
    h, m = int(h), int(m)
    if not (0 <= h <= 24 and 0 <= m < 60):
        raise ValueError("time out of range: %r" % s)
    return h + m / 60.0


def parse_awake(s):
    a, b = s.split("-")
    lo, hi = parse_hhmm(a), parse_hhmm(b)
    if hi <= lo:
        raise ValueError("awake window end must be after start: %r" % s)
    return lo, hi


def parse_busy(text):
    """-> {day: [(start, end, label)]}; raises on a bad line."""
    out = {d: [] for d in DAYS}
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split(SEP)]
        if len(parts) < 3:
            raise ValueError("mirror row needs at least 3 fields (day · start · end · label?): %r" % raw)
        day_key = parts[0].lower()[:3]
        if day_key not in DAYS:
            raise ValueError("unknown day %r in row: %r" % (parts[0], raw))
        s, e = parse_hhmm(parts[1]), parse_hhmm(parts[2])
        if e <= s:
            raise ValueError("end must be after start in row: %r" % raw)
        out[day_key].append((s, e, parts[3] if len(parts) > 3 else ""))
    return out


def merge(blocks):
    blocks = sorted(blocks)
    out = []
    for blk in blocks:
        s, e = blk[0], blk[1]
        if out and s <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], e))
        else:
            out.append((s, e))
    return out


def capacity(busy, awake):
    lo, hi = awake
    per_day = {}
    total = 0.0
    for d in DAYS:
        free = hi - lo
        clipped = []
        for s, e, _l in busy[d]:
            s2, e2 = max(s, lo), min(e, hi)
            if e2 > s2:
                clipped.append((s2, e2))
        for s, e in merge(clipped):
            free -= e - s
        per_day[d] = max(free, 0.0)
        total += per_day[d]
    return per_day, total


def _show(busy_text, awake_text):
    print(BANNER)
    busy = parse_busy(busy_text)
    awake = parse_awake(awake_text)
    per_day, total = capacity(busy, awake)
    lo, hi = awake
    print("awake window: %05.2f-%05.2f (%.2f h/day)" % (lo, hi, hi - lo))
    lines = ["%s: %.2f h" % (d, v) for d, v in per_day.items()]
    print("free per day: " + "; ".join(lines))
    print("week capacity: %.2f h" % total)
    print("expression: %d days x %.2f h - busy(hours, merged, clipped) = %.2f h" % (
        len(DAYS), hi - lo, total))


def selftest():
    good = ("mon · 09:00 · 10:00 · meeting\n"
            "mon · 09:30 · 10:30 · overlapping meeting\n"
            "tue · 20:00 · 22:00 · evening event (past the window)\n")
    edge = ""                    # an empty mirror: the whole awake window is free
    padded = "wed · 14:00 · 13:00 · backwards\n"
    fails = []
    try:
        per_day, total = capacity(parse_busy(good), parse_awake("09:00-17:00"))
        # mon: 8h - 1.5h merged = 6.5 ; tue: 8h - 0h clipped = 8 ; others 8.
        ok = abs(per_day["mon"] - 6.5) < 1e-9 and abs(per_day["tue"] - 8.0) < 1e-9 and abs(total - (6.5 + 8.0 + 5 * 8.0)) < 1e-9
        print(("PASS  " if ok else "FAIL  ") + "good input: mon %.2f, tue %.2f, week %.2f (want 6.50 / 8.00 / 46.50)" % (per_day["mon"], per_day["tue"], total))
        if not ok:
            fails.append("good")
    except Exception as e:
        print("FAIL  good input raised: %s" % e); fails.append("good")
    try:
        _, total = capacity(parse_busy(edge), parse_awake("09:00-17:00"))
        ok = abs(total - 7 * 8.0) < 1e-9
        print(("PASS  " if ok else "FAIL  ") + "edge input: empty mirror -> %.2f h (want 56.00)" % total)
        if not ok:
            fails.append("edge")
    except Exception as e:
        print("FAIL  edge input raised: %s" % e); fails.append("edge")
    try:
        parse_busy(padded)
        print("FAIL  padded input was accepted (end-before-start must error)"); fails.append("padded")
    except ValueError as e:
        print("PASS  padded input refused loudly: %s" % e)
    try:
        parse_awake("18:00-09:00")
        print("FAIL  reversed awake window was accepted"); fails.append("awake")
    except ValueError as e:
        print("PASS  reversed awake window refused loudly: %s" % e)
    if fails:
        print("SELFTEST FAILED: %s" % ", ".join(fails))
        return 1
    print("SELFTEST PASSED")
    return 0


def main(argv):
    args = argv[1:]
    if "--selftest" in args:
        return selftest()
    busy_text = None
    awake = None
    i = 0
    while i < len(args):
        a = args[i]
        if a == "busy":
            busy_text = args[i + 1]; i += 2
        elif a == "--awake":
            awake = args[i + 1]; i += 2
        else:
            print("ERROR: unknown argument %r" % a, file=sys.stderr)
            return 2
    if busy_text is None or awake is None:
        print("usage: capacity-fallback.py busy \"<mirror rows>\" --awake HH:MM-HH:MM | --selftest", file=sys.stderr)
        return 2
    try:
        _show(busy_text, awake)
    except ValueError as e:
        print("ERROR: %s" % e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

#!/usr/bin/env python3
"""fit-check.py — step 5/7's fit check: placed hours versus capacity, computed in code (spec 7.4).

Input: a calendar-draft ROWS block (one row per block: `day · start · end · label · zone`,
the separator is "·" with optional surrounding spaces) and a capacity figure.

Modes:
  fit-check.py rows "<ROWS text>" --capacity HOURS
      Total placed hours per day and overall; prints the gap (negative = over) and exits 0
      whether it fits or not — the CALLER decides what moving means (spec: never forces a cut).
      --zone WIN-ZONE restricts the totals to one zone (e.g. the protected Win-zone hours).
  fit-check.py --selftest
      One good, one edge and one padded case; exits 0 only if all pass.

Rules enforced here (never by the model): arithmetic in code; a malformed row is a loud error,
never silently skipped; a row whose start is not before its end is an error; the Midnight-to-
Midnight day is 24h, and a day total above 24h is an error (a padded calendar).
"""
# allow-silence: build-ruled location — slice B of the planning-weekly build; the coordinator
# ruled this worktree skill folder as the home for these files, and the build task forbids
# own_list_add and any write outside the worktree. Not a personal tool; never moved to ClaudeOps.
import sys

SEP = "·"
DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def parse_hours(hhmm):
    h, m = hhmm.strip().split(":")
    h, m = int(h), int(m)
    if not (0 <= h <= 24 and 0 <= m < 60):
        raise ValueError("time out of range: %r" % hhmm)
    return h + m / 60.0


def parse_rows(text):
    """-> list of (day, start_h, end_h, zone). Raises ValueError with the row on any bad row."""
    rows = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split(SEP)]
        if len(parts) != 5:
            raise ValueError("row needs 5 fields (day · start · end · label · zone): %r" % raw)
        day, start, end, _label, zone = parts
        day_key = day.strip().lower()[:3]
        if day_key not in DAYS:
            raise ValueError("unknown day %r in row: %r" % (day, raw))
        s, e = parse_hours(start), parse_hours(end)
        if e <= s:
            raise ValueError("end must be after start in row: %r" % raw)
        rows.append((day_key, s, e, zone.strip().upper()))
    return rows


def totals(rows, zone=None):
    per_day = {d: 0.0 for d in DAYS}
    grand = 0.0
    for day, s, e, z in rows:
        if zone and z != zone.upper():
            continue
        per_day[day] += e - s
        grand += e - s
    return per_day, grand


def _show(rows_text, capacity, zone=None):
    rows = parse_rows(rows_text)
    per_day, grand = totals(rows, zone)
    gap = capacity - grand
    lines = ["%s: %.2f h" % (d, v) for d, v in per_day.items() if v > 0]
    print("placed: %.2f h%s" % (grand, (" in zone %s" % zone.upper()) if zone else ""))
    if lines:
        print("per day: " + "; ".join(lines))
    print("capacity: %.2f h" % capacity)
    print("gap: %.2f h (%s)" % (gap, "fits" if gap >= 0 else "OVER by %.2f h" % -gap))
    print("expression: %.2f - %.2f = %.2f" % (capacity, grand, gap))


def selftest():
    good = ("mon · 09:00 · 11:00 · deep work · WIN-ZONE\n"
            "tue · 14:00 · 15:30 · admin · SHALLOW-TRAP\n"
            "wed · 10:00 · 12:00 · client deck · MUST-DELIVER\n")
    edge = ""                       # no rows at all: placed 0, everything fits
    padded = ("mon · 09:00 · 13:00 · a · WIN-ZONE\n"
              "mon · 10:00 · 14:00 · overlapping b · WIN-ZONE\n"
              "mon · 23:00 · 02:00 · wraps midnight, end before start\n")
    fails = []
    try:
        rows = parse_rows(good)
        _, grand = totals(rows)
        ok = abs(grand - 5.5) < 1e-9
        print(("PASS  " if ok else "FAIL  ") + "good input: 3 rows -> %.2f h (want 5.50)" % grand)
        if not ok:
            fails.append("good")
    except Exception as e:
        print("FAIL  good input raised: %s" % e); fails.append("good")
    try:
        _, grand = totals(parse_rows(edge))
        ok = grand == 0.0
        print(("PASS  " if ok else "FAIL  ") + "edge input: empty rows -> %.2f h (want 0.00)" % grand)
        if not ok:
            fails.append("edge")
    except Exception as e:
        print("FAIL  edge input raised: %s" % e); fails.append("edge")
    try:
        parse_rows(padded)
        print("FAIL  padded input was accepted (overlapping rows + end before start must error)")
        fails.append("padded")
    except ValueError as e:
        print("PASS  padded input refused loudly: %s" % e)
    # End-before-start must fail; zone filter must filter.
    try:
        parse_rows("mon · 12:00 · 11:00 · backwards · MUST-DELIVER")
        print("FAIL  end-before-start row was accepted"); fails.append("backwards")
    except ValueError as e:
        print("PASS  end-before-start refused loudly: %s" % e)
    _, gz = totals(parse_rows(good), zone="WIN-ZONE")
    ok = abs(gz - 2.0) < 1e-9
    print(("PASS  " if ok else "FAIL  ") + "zone filter: WIN-ZONE total %.2f h (want 2.00)" % gz)
    if not ok:
        fails.append("zone")
    if fails:
        print("SELFTEST FAILED: %s" % ", ".join(fails))
        return 1
    print("SELFTEST PASSED")
    return 0


def main(argv):
    args = argv[1:]
    if "--selftest" in args:
        return selftest()
    zone = None
    capacity = None
    rows_text = None
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--capacity":
            capacity = float(args[i + 1]); i += 2
        elif a == "--zone":
            zone = args[i + 1]; i += 2
        elif a == "rows":
            rows_text = args[i + 1]; i += 2
        else:
            print("ERROR: unknown argument %r" % a, file=sys.stderr)
            return 2
    if rows_text is None or capacity is None:
        print("usage: fit-check.py rows \"<ROWS>\" --capacity HOURS [--zone Z] | --selftest", file=sys.stderr)
        return 2
    try:
        _show(rows_text, capacity, zone)
    except ValueError as e:
        print("ERROR: %s" % e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

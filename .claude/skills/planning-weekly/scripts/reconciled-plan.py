#!/usr/bin/env python3
"""reconciled-plan.py — builds the Council's RECONCILED PLAN from the scratchpad (spec 6.2,
review fix R4). Code, instant — never model work.

What it does:
  - reads the session scratchpad (one markdown file, sections written as `## § Name`);
  - wherever an item carries a fixed ruling line (`RULING: confirmed`, `RULING: corrected:
    "<words>"`, `RULING: dropped`, `RULING: parked` — spec I4), the person's word replaces the
    machine's guess; anything unconfirmed is carried and marked `(guess)`;
  - includes § Confirmed week and its trend lines, § Energy baseline and the capacity numbers
    verbatim from the scratchpad (review R4: the Council is fed, not starved);
  - computes the fit figures by code: hours needed per zone from the calendar rows in § Persist
    draft (`day · start · end · label · zone`) against the capacity stated in § Zones — the
    numbers Time Supply comments on (never arithmetic in an advisor's head).

Modes:
  reconciled-plan.py --scratchpad FILE        print the reconciled plan on stdout
  reconciled-plan.py --selftest               good / edge / padded cases, exit 0 only if all pass

A missing scratchpad or a missing section prints a named error and exits 1 (loud, never silent).
"""
# allow-silence: build-ruled location — slice B of the planning-weekly build; the coordinator
# ruled this worktree skill folder as the home for these files, and the build task forbids
# own_list_add and any write outside the worktree. Not a personal tool; never moved to ClaudeOps.
import re
import sys

RULING_RE = re.compile(r'^RULING:\s*(confirmed|corrected:\s*"([^"]*)"|dropped|parked)\s*$', re.I)
SECTION_RE = re.compile(r'^##\s+§\s*(.+?)\s*$')
ROW_SEP = "·"
DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def parse_sections(text):
    """-> {name: [lines]} from `## § Name` headings; text outside sections is ignored."""
    out, current = {}, None
    for line in text.splitlines():
        m = SECTION_RE.match(line)
        if m:
            current = m.group(1).strip()
            out.setdefault(current, [])
            continue
        if current is not None:
            out[current].append(line)
    return out


def reconcile_lines(lines):
    """Apply RULING lines to a section's lines. -> list of output lines.

    An item line followed by a RULING line is rewritten:
      confirmed            -> the line, marked (confirmed)
      corrected: "<words>" -> the line with the person's words appended (confirmed, corrected)
      dropped / parked     -> the line struck, marked accordingly
    No ruling -> the line is carried and marked (guess).
    """
    out = []
    pending = None
    for line in lines:
        if SECTION_RE.match(line.strip()):
            if pending is not None:
                out.append(pending + " (guess)")
                pending = None
            out.append(line)
            continue
        m = RULING_RE.match(line.strip())
        if m:
            kind = m.group(1).lower()
            # a draft "(guess)" marker the sorter wrote is superseded by the person's ruling
            pending = re.sub(r'\s*\(guess\)\s*$', '', pending)
            if pending is None:
                out.append("(orphan ruling %r with no item above it — carried, needs a human look)" % kind)
                continue
            if kind == "confirmed":
                out.append(pending + " (confirmed)")
            elif kind.startswith("corrected"):
                out.append('%s — corrected by the person: "%s" (confirmed)' % (pending, m.group(2)))
            elif kind == "dropped":
                out.append("~~%s~~ (dropped by the person)" % pending)
            else:
                out.append("%s (parked by the person)" % pending)
            # none: pending handled below
            pending = None
            continue
        if line.strip():
            if pending is not None:
                out.append(pending + " (guess)")   # previous item never got a ruling
            pending = line.rstrip()
        else:
            if pending is not None:
                out.append(pending + " (guess)")
                pending = None
            out.append(line)
    if pending is not None:
        out.append(pending + " (guess)")
    return out


def zone_hours(lines):
    """Hours needed per zone from calendar ROWS. -> ({zone: hours}, error_or_None)."""
    per_zone, err = {}, None
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split(ROW_SEP)]
        if len(parts) != 5:
            err = "row needs 5 fields (day · start · end · label · zone): %r" % raw
            continue
        day, start, end, _label, zone = parts
        try:
            sh, sm = map(int, start.split(":"))
            eh, em = map(int, end.split(":"))
        except ValueError:
            err = "bad time in row: %r" % raw
            continue
        if not (0 <= sh <= 24 and 0 <= eh <= 24 and 0 <= sm < 60 and 0 <= em < 60):
            err = "time out of range in row: %r" % raw
            continue
        s, e = sh + sm / 60.0, eh + em / 60.0
        if e <= s:
            err = "end must be after start in row: %r" % raw
            continue
        per_zone[zone.upper()] = per_zone.get(zone.upper(), 0.0) + (e - s)
    return per_zone, err


def build(sections):
    out = []
    out.append("# The reconciled plan")
    out.append("")
    out.append("Built by code from the session scratchpad: the person's ruling replaces the machine's")
    out.append("guess wherever a RULING line stands; everything else is carried and marked (guess).")
    out.append("")
    for name in ("Confirmed week", "Energy baseline", "Zones", "Ranked list", "Council rulings"):
        if name in sections:
            out.append("## § %s" % name)
            out.extend(reconcile_lines(sections[name]))
            out.append("")
    if "Persist draft" in sections:
        per_zone, err = zone_hours(sections["Persist draft"])
        out.append("## § Fit figures (computed by code)")
        if err:
            out.append("WARNING: %s — the affected rows were skipped, never silently." % err)
        for z in sorted(per_zone):
            out.append("- %s: %.2f h needed" % (z, per_zone[z]))
        if not per_zone and not err:
            out.append("- (no calendar rows found in § Persist draft)")
        cap_line = next((l for l in sections.get("Zones", []) if "capacity" in l.lower()), None)
        if cap_line:
            out.append("- capacity (from § Zones, verbatim): %s" % cap_line.strip())
        out.append("")
    trend = next((l for l in sections.get("Confirmed week", []) if "trend" in l.lower()), None)
    out.append("## § Trend")
    out.append(trend.strip() if trend else "first confirmed week — no trend yet.")
    return "\n".join(out).rstrip() + "\n"


def selftest():
    good = """## § Ranked list
1. Ship the deck (guess)
RULING: corrected: "Ship the deck for Thursday's client, not Friday"
2. Rest day (guess)
RULING: confirmed
3. Old side project (guess)
RULING: dropped
## § Confirmed week
Last week delivered the deck draft. trend: second confirmed week — delivery trended up.
## § Energy baseline
full week
## § Zones
capacity: 32.5 h after corrections
## § Persist draft
mon · 09:00 · 12:00 · deck · WIN-ZONE
mon · 13:00 · 14:00 · admin · SHALLOW-TRAP
"""
    edge = "## § Ranked list\n1. Only item, never ruled\n"
    padded = "## § Persist draft\nmon · 09:00 · 08:00 · backwards · WIN-ZONE\n"
    fails = []
    secs = parse_sections(good)
    plan = build(secs)
    ok1 = 'corrected by the person: "Ship the deck for Thursday' in plan and "(confirmed)" in plan
    ok2 = "~~3. Old side project~~" in plan
    ok3 = "Only item, never ruled (guess)" in build(parse_sections(edge))
    ok4 = "second confirmed week — delivery trended up" in plan
    ok5 = "WIN-ZONE: 3.00 h needed" in plan and "capacity (from § Zones, verbatim): capacity: 32.5 h" in plan
    print(("PASS  " if ok1 else "FAIL  ") + "good: corrected ruling replaces the guess")
    print(("PASS  " if ok2 else "FAIL  ") + "good: dropped ruling strikes the item")
    print(("PASS  " if ok3 else "FAIL  ") + "edge: unruled item is carried as (guess)")
    print(("PASS  " if ok4 else "FAIL  ") + "good: confirmed-week trend carried verbatim")
    print(("PASS  " if ok5 else "FAIL  ") + "good: fit figures computed by code (zone hours + capacity)")
    if not (ok1 and ok2 and ok4 and ok5):
        fails.append("good")
    if not ok3:
        fails.append("edge")
    z, err = zone_hours(["mon · 09:00 · 08:00 · backwards · WIN-ZONE"])
    ok6 = err is not None
    print(("PASS  " if ok6 else "FAIL  ") + "padded: end-before-start row reported loudly (%s)" % err)
    if not ok6:
        fails.append("padded")
    if fails:
        print("SELFTEST FAILED: %s" % ", ".join(fails))
        return 1
    print("SELFTEST PASSED")
    return 0


def main(argv):
    args = argv[1:]
    if "--selftest" in args:
        return selftest()
    path = None
    i = 0
    while i < len(args):
        if args[i] == "--scratchpad":
            path = args[i + 1]; i += 2
        else:
            print("ERROR: unknown argument %r" % args[i], file=sys.stderr)
            return 2
    if not path:
        print("usage: reconciled-plan.py --scratchpad FILE | --selftest", file=sys.stderr)
        return 2
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        print("ERROR: cannot read the scratchpad: %s" % e, file=sys.stderr)
        return 1
    if not text.strip():
        print("ERROR: the scratchpad is empty — nothing to reconcile", file=sys.stderr)
        return 1
    sections = parse_sections(text)
    if not sections:
        print("ERROR: no `## § Section` headings found — is this the session scratchpad?", file=sys.stderr)
        return 1
    sys.stdout.write(build(sections))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

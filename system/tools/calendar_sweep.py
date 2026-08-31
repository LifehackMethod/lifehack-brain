#!/usr/bin/env python3
"""
Calendar weekly sweep detector.

Implements section 7 ("Weekly sweep - spec") of
AI-Brain-Z/80-integrations/calendar-email-docs/calendar-routing-rules.md

INPUT   Either format, chosen by file extension:

        .tsv  - PREFERRED. One header line, then one line per event:
                calendar<TAB>calendar_id<TAB>event_id<TAB>title<TAB>start<TAB>tz_label<TAB>created<TAB>series
                `start` is the full ISO string WITH its offset (2026-09-10T09:30:00-07:00)
                or a bare YYYY-MM-DD for an all-day event. Empty cells are fine.
                This format exists because the operator has to hand-carry the API
                results into the file; TSV costs roughly a tenth of raw JSON.

        .json - a list of objects, one per calendar:
                {"calendar": "...", "calendarId": "...", "events": [ <Google event resource>, ... ]}

OUTPUT  A markdown report written to stdout (redirect it to the report file).

FOUR HARD CONSTRAINTS THIS SCRIPT HONOURS
  1. Google account only. The Google Calendar API cannot see iCloud
     (rules file 7a). Every report opens by saying so and closes with the
     manual Apple Calendar check. Never claim a clean calendar - claim a
     clean *Google* calendar.
  2. No move operation exists (rules file 6). This script never proposes an
     automated move; misroutes are reported as hand-move candidates.
  3. Trust the UTC offset embedded in start.dateTime. NEVER the stored
     timeZone label - some events read America/New_York while their offsets
     are Pacific, which already caused one false 3-hour error.
  4. Report only. This script has no write path of any kind.

Usage:  python3 calendar_sweep.py events.json [--window-days 8] > report.md
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

# --------------------------------------------------------------------------
# Configuration - mirrors sections 2, 4 and 4b of calendar-routing-rules.md
# --------------------------------------------------------------------------

# Calendars that must receive no new events (rules 2, "Legacy calendars").
LEGACY_CALENDARS = {
    "CSMC - HOSPITAL",
    "PERSONAL-FAMILY",
    "MIZMDINC.qdfm",
    "Home",
    "Work",
    "QB - BOOK",          # retired 19 Aug 2026 (rules 4b)
}

# The unfiled inbox. Not an error - it is where Apple Calendar's default
# lands things - but every event here is a routing to-do (rules 4a, teal).
INBOX_CALENDARS = {"w4all2@gmail.com"}

# Life-Map destination calendars (rules 2).
LIFEMAP_CALENDARS = {
    "Clinical", "Society", "Builds", "Family", "Admin",
    "Travel", "CONFERENCES", "Good Stuff",
}

# Subscribed feeds - excluded entirely (rules 2 and 7).
FEED_ID_MARKERS = ("@import.calendar.google.com", "#holiday@group.v.calendar.google.com")
FEED_NAME_MARKERS = ("(DELETED)",)

# Section 4: Society obligations that DO earn Cedars credit and therefore
# require the [CS] tag in the title.
CS_REQUIRED = [
    (r"\basa\b.*\bbod\b|\basa\b.*board of directors", "ASA BOD"),
    (r"\basa\b.*\bhod\b|\basa\b.*house of delegates", "ASA HOD"),
    (r"reference (cmte|committee)", "ASA Reference Committee"),
    (r"\bcoba\b|committee on obstetric anesthesia", "ASA CObA"),
    (r"\bqmda\b", "ASA QMDA"),
    (r"\basa\b.*educ", "ASA Educ Track OB"),
    (r"\basa\b.*medicoleg", "ASA Medicolegal lecture"),
    (r"\basa annual meeting\b", "ASA Annual Meeting"),
    (r"\basa\b.*governance", "ASA Governance"),
    (r"rovenstine", "Rovenstine"),
    (r"\bamoc\b|annual meeting oversight", "AMOC"),
    (r"ob guidelines", "ASA OB Guidelines Task Force"),
    (r"\bsoap\b.*\bcoe\b|\bcoe\b.*\bsoap\b", "SOAP COE"),
    (r"\bcsa\b.*\bepd\b|education and programs division", "CSA EPD"),
]

# Section 4: Society obligations that explicitly earn NO credit. Checked
# FIRST, so keyword collisions cannot produce a false missing-tag flag -
# e.g. "CSA BOD Education and Orientation" contains "educ" and "bod".
CS_EXCLUDED = [
    r"\bcsa\b.*\bhod\b|\bcsa\b.*house of delegates",
    r"\bcsa\b.*(exec|executive)",
    r"legislative",
    r"\bcsa\b.*\bbod\b",
    r"caucus",
    r"\btsa\b",
    r"presidents? reception",
    r"medicolegal zak",
    r"\bpltw\b|project lead the way",
    r"elevate",
]

# Titles known to be shared across genuinely different events. Six of the
# nine "duplicates" in the 19 Aug 2026 audit were these. Pairs matching one
# of these are still reported - never silently dropped - but marked as
# likely false positives so the eye skips them fast.
SHARED_LABELS = {
    "exercise", "ai bootcamp", "family time", "nap", "walk",
    "meeting", "call", "admin", "office hours", "lunch", "dinner",
}

# Dropped before token comparison so "ASA BOD" and "ASA BOD meeting" match.
STOPWORDS = {
    "meeting", "mtg", "the", "a", "an", "of", "and", "with", "for",
    "to", "on", "at", "in", "call", "re", "w",
}

TOKEN_OVERLAP_THRESHOLD = 0.60   # rules 7: ">=60% title-token overlap"

# The 13-14 Aug 2026 .ics import wrote ~217 events onto the legacy calendars in
# two bursts. Every one of them carries a `created` stamp inside this window, so
# without an exception the "new event on a legacy calendar" check reports the
# migration itself - 198 hits on the first run, all of them history rather than
# drift. These are migrated originals: they stay put and age out (rules 6).
# The window is closed and will not grow; anything created after it is real drift.
MIGRATION_BURSTS = [
    ("2026-08-13T20:00:00+00:00", "2026-08-15T00:00:00+00:00"),
]

# --------------------------------------------------------------------------
# Normalisation
# --------------------------------------------------------------------------

CS_TAG_RE = re.compile(r"[\[\(]\s*c\s*\.?\s*s\s*\.?\s*[\]\)]", re.I)
CANONICAL_CS_RE = re.compile(r"\[CS\]")


def has_cs_tag(title):
    """True if a canonical [CS] tag is present."""
    return bool(CANONICAL_CS_RE.search(title or ""))


def has_cs_variant(title):
    """True if some near-miss tag form is present - (cs), [c.s.], [cs] lowercase."""
    t = title or ""
    return bool(CS_TAG_RE.search(t)) and not has_cs_tag(t)


def strip_cs(title):
    return CS_TAG_RE.sub(" ", title or "")


def normalise(title):
    """Lowercase, drop the [CS] tag, drop punctuation, collapse whitespace."""
    t = strip_cs(title).lower()
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def tokens(title):
    return {w for w in normalise(title).split() if w not in STOPWORDS}


def overlap_coefficient(a, b):
    """|A n B| / min(|A|,|B|). Catches 'ASA CObA' inside 'ASA CObA prep call'."""
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def jaccard(a, b):
    if not (a or b):
        return 0.0
    return len(a & b) / len(a | b)

# --------------------------------------------------------------------------
# Event flattening
# --------------------------------------------------------------------------


def is_feed(cal_name, cal_id):
    if any(m in (cal_id or "") for m in FEED_ID_MARKERS):
        return True
    return any(m in (cal_name or "") for m in FEED_NAME_MARKERS)


def parse_dt(node):
    """
    Return (utc_instant_or_None, local_date_str, display_str, all_day_bool).

    CONSTRAINT 3: we read only the offset carried in the dateTime string.
    The sibling timeZone label is deliberately ignored - it is unreliable.
    """
    if not node:
        return None, None, "?", False
    if "date" in node and "dateTime" not in node:
        d = node["date"]
        return None, d, f"{d} (all-day)", True
    raw = node.get("dateTime")
    if not raw:
        return None, None, "?", False
    dt = datetime.fromisoformat(raw)          # offset-aware; offset is trusted
    return (dt.astimezone(timezone.utc),
            dt.date().isoformat(),
            dt.strftime("%a %d %b %H:%M"),
            False)


def _record(cal, title, start_node, ev_id, created, series):
    """Build one internal event record from already-split fields."""
    utc, local_date, display, all_day = parse_dt(start_node)
    if local_date is None:
        return None
    offset = None
    raw = (start_node or {}).get("dateTime")
    if raw:
        try:
            offset = datetime.fromisoformat(raw).utcoffset()
        except ValueError:
            offset = None
    return {
        "calendar": cal,
        "title": title,
        "norm": normalise(title),
        "tokens": tokens(title),
        "date": local_date,
        "utc": utc,
        "display": display,
        "all_day": all_day,
        "id": ev_id,
        "series": series or None,
        "created": created or None,
        "tz_label": (start_node or {}).get("timeZone"),
        "offset": offset,
    }


TSV_COLUMNS = ["calendar", "calendar_id", "event_id", "title",
               "start", "tz_label", "created", "series"]


def load_tsv(path):
    """Read the compact hand-carried format. Blank lines and '#' comments ignored."""
    events = []
    calendars = set()
    with open(path, encoding="utf-8") as fh:
        lines = [ln.rstrip("\n") for ln in fh
                 if ln.strip() and not ln.lstrip().startswith("#")]
    if not lines:
        return [], 0
    start_at = 1 if lines[0].split("\t")[0].strip().lower() == "calendar" else 0
    for ln in lines[start_at:]:
        cells = ln.split("\t")
        cells += [""] * (len(TSV_COLUMNS) - len(cells))
        cal, cal_id, ev_id, title, start, tz_label, created, series = \
            [c.strip() for c in cells[:len(TSV_COLUMNS)]]
        if is_feed(cal, cal_id):
            continue
        calendars.add(cal)
        if not start:
            continue
        node = ({"date": start} if len(start) == 10
                else {"dateTime": start, "timeZone": tz_label or None})
        rec = _record(cal, title or "(no title)", node, ev_id, created, series)
        if rec:
            events.append(rec)
    return events, len(calendars)


def flatten(payload):
    out = []
    for block in payload:
        cal = block.get("calendar") or block.get("summary") or "?"
        cal_id = block.get("calendarId") or block.get("id") or ""
        if is_feed(cal, cal_id):
            continue
        for ev in block.get("events") or []:
            if ev.get("status") == "cancelled":
                continue
            utc, local_date, display, all_day = parse_dt(ev.get("start"))
            if local_date is None:
                continue
            title = ev.get("summary") or "(no title)"
            created = ev.get("created")
            label = (ev.get("start") or {}).get("timeZone")
            offset = None
            raw = (ev.get("start") or {}).get("dateTime")
            if raw:
                try:
                    offset = datetime.fromisoformat(raw).utcoffset()
                except ValueError:
                    offset = None
            out.append({
                "calendar": cal,
                "title": title,
                "norm": normalise(title),
                "tokens": tokens(title),
                "date": local_date,
                "utc": utc,
                "display": display,
                "all_day": all_day,
                "id": ev.get("id"),
                "series": ev.get("recurringEventId"),
                "created": created,
                "tz_label": label,
                "offset": offset,
                "link": ev.get("htmlLink"),
                "event_type": ev.get("eventType"),
            })
    return out

# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------


def same_series(a, b):
    return a["series"] and b["series"] and a["series"] == b["series"]


def check_same_title_same_day(events):
    """Check 1: identical normalised title on the same day, any calendar, any time."""
    hits = []
    buckets = defaultdict(list)
    for e in events:
        if e["norm"]:
            buckets[(e["date"], e["norm"])].append(e)
    for (date, norm), group in sorted(buckets.items()):
        if len(group) < 2:
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                if same_series(a, b):
                    continue                      # legitimate series instances
                same_time = a["utc"] is not None and a["utc"] == b["utc"]
                likely_fp = norm in SHARED_LABELS and not same_time
                hits.append({
                    "date": date, "a": a, "b": b,
                    "same_time": same_time,
                    "likely_fp": likely_fp,
                    "severity": "HIGH" if same_time else ("LOW" if likely_fp else "MEDIUM"),
                })
    return hits


def check_token_overlap(events):
    """Check 2: >=60% title-token overlap at an identical start instant."""
    hits = []
    buckets = defaultdict(list)
    for e in events:
        key = e["utc"].isoformat() if e["utc"] else f"allday:{e['date']}"
        buckets[key].append(e)
    for key, group in sorted(buckets.items()):
        if len(group) < 2:
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                if same_series(a, b):
                    continue
                if a["norm"] == b["norm"]:
                    continue                      # already caught by check 1
                oc = overlap_coefficient(a["tokens"], b["tokens"])
                if oc < TOKEN_OVERLAP_THRESHOLD:
                    continue
                jac = jaccard(a["tokens"], b["tokens"])
                # A pure subset ("ASA CObA" inside "ASA CObA prep call") scores
                # 100% on the overlap coefficient. Jaccard is what separates a
                # real near-duplicate from a longer, genuinely different title,
                # so both gate the HIGH label.
                hits.append({
                    "a": a, "b": b,
                    "overlap": oc,
                    "jaccard": jac,
                    "severity": "HIGH" if (oc >= 0.85 and jac >= 0.60) else "MEDIUM",
                })
    return hits


def check_legacy_writes(events, window_days, now):
    """Check 3: new events written to a legacy calendar. Split from inbox strays."""
    cutoff = now - timedelta(days=window_days)
    bursts = [(datetime.fromisoformat(a), datetime.fromisoformat(b))
              for a, b in MIGRATION_BURSTS]
    legacy, inbox, suppressed = [], [], 0
    for e in events:
        if not e["created"]:
            continue
        try:
            created = datetime.fromisoformat(e["created"].replace("Z", "+00:00"))
        except ValueError:
            continue
        if created < cutoff:
            continue
        if any(lo <= created < hi for lo, hi in bursts):
            suppressed += 1               # migrated history, not new drift
            continue
        if e["calendar"] in LEGACY_CALENDARS:
            legacy.append((created, e))
        elif e["calendar"] in INBOX_CALENDARS:
            inbox.append((created, e))
    legacy.sort(key=lambda x: x[0])
    inbox.sort(key=lambda x: x[0])
    return legacy, inbox, suppressed


def cs_obligation(title):
    """Return the section-4 obligation name if this title requires [CS], else None."""
    n = normalise(title)
    for pat in CS_EXCLUDED:
        if re.search(pat, n):
            return None
    for pat, name in CS_REQUIRED:
        if re.search(pat, n):
            return name
    return None


def check_missing_cs(events):
    """Check 4: Society event matching a section-4 [CS] obligation but missing the tag."""
    missing, variants, misrouted = [], [], []
    for e in events:
        oblig = cs_obligation(e["title"])
        if not oblig:
            continue
        if e["calendar"] == "Society":
            if has_cs_tag(e["title"]):
                continue
            if has_cs_variant(e["title"]):
                variants.append((e, oblig))
            else:
                missing.append((e, oblig))
        elif e["calendar"] in LEGACY_CALENDARS or e["calendar"] in INBOX_CALENDARS:
            misrouted.append((e, oblig))
    return missing, variants, misrouted


def check_tz_label_drift(events):
    """Informational only (rules 6). Cosmetic, but it has caused a false 3-hour error."""
    drift = []
    for e in events:
        if e["all_day"] or not e["tz_label"] or e["offset"] is None:
            continue
        hours = e["offset"].total_seconds() / 3600
        label = e["tz_label"]
        pacific = hours in (-7.0, -8.0)
        if pacific and label != "America/Los_Angeles":
            drift.append(e)
    return drift

# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------


def fmt(e):
    return f"`{e['calendar']}` · {e['display']} · **{e['title']}**"


def build_report(events, window_days, now, span_days, calendars_scanned):
    L = []
    add = L.append
    date_s = now.astimezone(timezone.utc).strftime("%Y-%m-%d")

    add(f"# Calendar weekly sweep - {date_s}")
    add("")
    with_events = len({e["calendar"] for e in events})
    add(f"Window: next {span_days} days · {len(events)} events · "
        f"{calendars_scanned} owned Google calendars queried, {with_events} held events · "
        "report only, nothing was changed.")
    add("")
    add("> **Scope limit - read this before trusting a clean result.** This sweep sees the")
    add("> **Google account only** (`w4all2@gmail.com`). The Google Calendar API cannot see")
    add("> the iCloud account (`zakowskim@mac.com`), which still holds the pre-13-Aug")
    add("> originals of every migrated event. A clean report here means *Google* is clean,")
    add("> not that your screen is clean. The 60-second check at the bottom covers the rest.")
    add("")

    dupes = check_same_title_same_day(events)
    overlaps = check_token_overlap(events)
    legacy, inbox, suppressed = check_legacy_writes(events, window_days, now)
    missing, variants, misrouted = check_missing_cs(events)
    drift = check_tz_label_drift(events)

    real_dupes = [h for h in dupes if not h["likely_fp"]]
    action_count = len(real_dupes) + len(overlaps) + len(legacy) + len(missing) + len(variants)

    add("## Summary")
    add("")
    add("| Check | Found | Needs a decision |")
    add("|---|---|---|")
    add(f"| 1. Same title, same day | {len(dupes)} pair(s) | {len(real_dupes)} |")
    add(f"| 2. >=60% token overlap at identical start | {len(overlaps)} pair(s) | {len(overlaps)} |")
    add(f"| 3. New events on a legacy calendar | {len(legacy)} | {len(legacy)} |")
    add(f"| 4. Society event missing `[CS]` | {len(missing) + len(variants)} | {len(missing) + len(variants)} |")
    add(f"| - Unfiled on primary (teal inbox) | {len(inbox)} | routing to-do, not an error |")
    add(f"| - Timezone label drift | {len(drift)} | cosmetic |")
    add("")
    add(f"**{action_count} item(s) want a ruling.**" if action_count
        else "**Nothing wants a ruling on the Google side.**")
    add("")

    # --- Check 1 -----------------------------------------------------------
    add("## 1. Same title, same day")
    add("")
    if not dupes:
        add("None.")
    else:
        add("| Sev | Date | Event A | Event B | Note |")
        add("|---|---|---|---|---|")
        for h in sorted(dupes, key=lambda x: (x["severity"] != "HIGH", x["date"])):
            note = ("identical start - treat as a true duplicate" if h["same_time"]
                    else ("shared label, different times - almost certainly two real events"
                          if h["likely_fp"] else "same day, different times - check"))
            add(f"| {h['severity']} | {h['date']} | {fmt(h['a'])} | {fmt(h['b'])} | {note} |")
    add("")

    # --- Check 2 -----------------------------------------------------------
    add("## 2. Near-identical titles at the same start")
    add("")
    if not overlaps:
        add("None.")
    else:
        add("| Sev | Overlap | Jaccard | Event A | Event B |")
        add("|---|---|---|---|---|")
        for h in sorted(overlaps, key=lambda x: (-x["jaccard"], -x["overlap"])):
            add(f"| {h['severity']} | {h['overlap']:.0%} | {h['jaccard']:.0%} | "
                f"{fmt(h['a'])} | {fmt(h['b'])} |")
    add("")

    # --- Check 3 -----------------------------------------------------------
    add(f"## 3. New events written to a legacy calendar (created in the last {window_days} days)")
    add("")
    if suppressed:
        add(f"*{suppressed} event(s) created during the 13-14 Aug 2026 `.ics` migration burst "
            "are excluded — migrated history, not new drift (section 6, forward-only).*")
        add("")
    if not legacy:
        add("None. Forward-only migration is holding.")
    else:
        add("These belong on a Life-Map calendar per section 2. Move them by hand in the")
        add("Google Calendar web UI - the API has no move operation (section 6).")
        add("")
        add("| Created | Event | Should be on |")
        add("|---|---|---|")
        for created, e in legacy:
            add(f"| {created.strftime('%d %b')} | {fmt(e)} | see section 2 routing table |")
    add("")

    # --- Check 4 -----------------------------------------------------------
    add("## 4. Society events missing the `[CS]` tag")
    add("")
    society_count = sum(1 for e in events if e["calendar"] == "Society")
    if not (missing or variants):
        if society_count == 0:
            # A bare "0" here would read as "all tagged correctly". It is not -
            # there is nothing on Society yet to tag. Say which zero this is.
            add("**Not applicable — the Society calendar holds no events in this window.**")
            add("This check reports zero because there is nothing to check, not because")
            add("everything is tagged. See the Informational section below for `[CS]`")
            add("obligations currently sitting on legacy calendars.")
        else:
            add(f"None. All {society_count} Society event(s) matching a section-4 credit "
                "obligation carry `[CS]`.")
    else:
        if missing:
            add("| Event | Matched obligation | Fix |")
            add("|---|---|---|")
            for e, oblig in missing:
                add(f"| {fmt(e)} | {oblig} | append ` [CS]` to the title |")
            add("")
        if variants:
            add("**Near-miss tag forms** - present but not canonical `[CS]`:")
            add("")
            add("| Event | Matched obligation |")
            add("|---|---|")
            for e, oblig in variants:
                add(f"| {fmt(e)} | {oblig} |")
    add("")

    # --- Informational -----------------------------------------------------
    add("## Informational")
    add("")
    if misrouted:
        add(f"**{len(misrouted)} `[CS]`-credit obligation(s) sitting on a legacy or inbox calendar** "
            "- these belong on Society:")
        add("")
        for e, oblig in misrouted:
            add(f"- {fmt(e)} — {oblig}")
        add("")
    if inbox:
        add(f"**{len(inbox)} new event(s) on the teal primary inbox** - route them per section 2:")
        add("")
        for created, e in inbox:
            add(f"- {fmt(e)} (created {created.strftime('%d %b')})")
        add("")
    if drift:
        add(f"**{len(drift)} event(s) carry a timezone label that disagrees with their "
            "Pacific offset** (section 6). Displayed times are correct; cosmetic only:")
        add("")
        for e in drift[:10]:
            add(f"- {fmt(e)} — labelled `{e['tz_label']}`")
        if len(drift) > 10:
            add(f"- …and {len(drift) - 10} more")
        add("")
    if not (misrouted or inbox or drift):
        add("Nothing.")
        add("")

    # --- Manual arm --------------------------------------------------------
    add("## The 60-second manual check (covers the iCloud blind spot)")
    add("")
    add("Open Apple Calendar and look at the sidebar under the **iCloud** heading. These")
    add("three must be **unchecked**:")
    add("")
    add("- [ ] `CSMC - HOSPITAL`")
    add("- [ ] `MIZMDINC.qdfm`")
    add("- [ ] `PERSONAL-FAMILY`")
    add("")
    add("If any got re-checked, uncheck it again - unchecking deletes nothing. Then:")
    add("")
    add("- [ ] Calendar → Settings → General → **Default Calendar** still reads `w4all2@gmail.com`")
    add("- [ ] No warning triangle beside the **Google** account in the sidebar")
    add("      (if there is one, and it persists: System Settings → Internet Accounts → Google → re-authenticate)")
    add("- [ ] Nothing on screen this coming week appears twice")
    add("")
    add("**Do not hand-delete a visually duplicated event.** The two copies look identical, so")
    add("roughly half the time the deletion lands on the Google copy - which undoes the cleanup.")
    add("")
    add("---")
    add("")
    add("Generated by `AI-Brain-Z/80-integrations/calendar-email-docs/scripts/calendar_sweep.py`")
    add("against section 7 of `AI-Brain-Z/80-integrations/calendar-email-docs/calendar-routing-rules.md`.")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("events_file", help="events.tsv (preferred) or events.json")
    ap.add_argument("--window-days", type=int, default=8,
                    help="Look-back window for 'newly created' checks. Default 8 "
                         "(a 7-day cadence plus a day of overlap).")
    ap.add_argument("--span-days", type=int, default=60,
                    help="Forward span the events were pulled over, for the header.")
    ap.add_argument("--calendars-queried", type=int, default=0,
                    help="How many owned calendars were actually queried, including "
                         "ones that came back empty. Without this the header can only "
                         "count calendars that happened to hold events.")
    args = ap.parse_args()

    if args.events_file.lower().endswith(".json"):
        with open(args.events_file, encoding="utf-8") as fh:
            payload = json.load(fh)
        events = flatten(payload)
        scanned = len([b for b in payload
                       if not is_feed(b.get("calendar", ""), b.get("calendarId", ""))])
    else:
        events, scanned = load_tsv(args.events_file)

    now = datetime.now(timezone.utc)
    scanned = args.calendars_queried or scanned
    sys.stdout.write(build_report(events, args.window_days, now, args.span_days, scanned) + "\n")


if __name__ == "__main__":
    main()

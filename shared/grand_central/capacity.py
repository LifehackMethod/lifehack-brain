"""capacity.py - 4P.3 item 3: the Capacity section of the morning snapshot, computed by CODE, never a model.

For each of the next 7 days from `day`, from the calendar mirror rows already gathered in hand_run step 2:
  - free_hours: hours with nothing on them inside the day window 08:00-20:00 local (12 hours when the day is empty);
  - collisions: pairs of overlapping timed events that day;
  - back_to_backs: one event ends within BACK_TO_BACK_MIN (10) minutes of the next starting;
  - travel: a day with an event of flight, airport, train or hotel kind (title or location), or one carrying the
    person's travel label from their settings. An all-day reminder is NOT travel.
    A rule of thumb from words, labelled as such wherever shown - never a fact.
Bad rows never crash and never go negative: a timed event whose end is empty or before its start is named
in the day's `unusable` list and contributes nothing. All-day events and zero-length events add 0 busy hours.

Python 3.9 compatible. Pure functions; no I/O, no model, no imports beyond the standard library.
"""

WINDOW = (8, 20)          # the day window, local hours: 08:00-20:00 -> 12 hours
BACK_TO_BACK_MIN = 10     # one event ends within this many minutes of the next starting
TRAVEL_WORDS = ("flight", "airport", "train", "hotel")   # the kinds: flight, train, hotel (airport = flight's place)


def _travel_labels():
    """The person's own travel label(s), lower case, from setup labels.json gmail_names (the entry whose word is
    "travel"); empty when there is no setup. Never a literal of the person's."""
    try:
        import gc_settings
        names = (gc_settings.labels().get("gmail_names") or {})
        return tuple(str(v).lower() for k, v in names.items() if str(k).lower() == "travel" and v)
    except Exception:
        return ()

ALL_DAY = "allday"


def _split_dt(s):
    """-> (date_str, minutes_after_midnight) for a mirror time string ("2026-11-20 09:30", "2026-11-20T09:30:00",
    seconds allowed); (date_str, None) when the string is a bare date (an all-day event); None when unusable."""
    s = str(s or "").strip()
    if len(s) < 10:
        return None
    date = s[:10]
    if not (len(date) == 10 and date[4] == "-" and date[7] == "-"):
        return None
    rest = s[10:].strip()
    if not rest:
        return date, None  # bare date: all-day
    rest = rest.lstrip("Tt ")
    # the real mirror writes local time with an offset ("2026-11-21T09:30:00-05:00") or a Z: the wall clock as
    # written IS the local time, so the zone suffix is dropped (never fed to int(), which was the root bug).
    if rest.endswith(("Z", "z")):
        rest = rest[:-1]
    else:
        tail = rest[-6:]
        if len(tail) == 6 and tail[0] in "+-" and tail[3] == ":" and tail[1:3].isdigit() and tail[4:].isdigit():
            rest = rest[:-6]
        elif len(rest) > 6 and rest[-5] in "+-" and rest[-4:].isdigit():
            rest = rest[:-5]
    try:
        parts = rest.split(":")
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
        sec = int(parts[2]) if len(parts) > 2 else 0
    except (ValueError, IndexError):
        return None
    if not (0 <= h < 24 and 0 <= m < 60 and 0 <= sec < 60):
        return None
    return date, h * 60 + m + (1 if sec else 0)


def _is_travel(text):
    t = str(text or "").lower()
    return any(w in t for w in TRAVEL_WORDS)


def _day_bounds(date_str, day):
    """-> the day's offset from `day` (0 = `day` itself), or None when outside [0, days)."""
    try:
        import datetime
        d = datetime.date(int(date_str[:4]), int(date_str[5:7]), int(date_str[8:10]))
        base = datetime.date(int(day[:4]), int(day[5:7]), int(day[8:10]))
    except (ValueError, AttributeError, TypeError):
        return None
    off = (d - base).days
    return off


def capacity(calendar_rows, day, days=7, travel_labels=None):
    """-> a list of one dict per day, `day` first:
    {"date", "free_hours", "busy_hours", "collisions", "back_to_backs", "travel", "unusable": [names]}.
    Pure arithmetic over the mirror rows; a bad row is named, never a crash.
    Travel: an event of flight, train, hotel (or airport) kind in its title or location, or one carrying a label
    in `travel_labels` (default: the person's travel label from their settings) in its "labels"/"label" field.
    An all-day reminder is never travel on its own."""
    if travel_labels is None:
        travel_labels = _travel_labels()
    travel_labels = tuple(str(t).lower() for t in travel_labels)

    def _is_travel_row(row, title):
        if _is_travel(title) or _is_travel(row.get("location")):
            return True
        have = row.get("labels", row.get("label"))
        if isinstance(have, str):
            have = [have]
        return any(str(h).lower() in travel_labels for h in (have or ()) if travel_labels)
    win_lo, win_hi = WINDOW[0] * 60, WINDOW[1] * 60
    win_hours = (win_hi - win_lo) / 60.0
    out = []
    for i in range(days):
        try:
            import datetime
            d = datetime.date(int(day[:4]), int(day[5:7]), int(day[8:10])) + datetime.timedelta(days=i)
        except (ValueError, TypeError):
            return out
        out.append({"date": d.isoformat(), "free_hours": win_hours, "busy_hours": 0.0,
                    "collisions": 0, "back_to_backs": 0, "travel": False, "unusable": []})
    if not out:
        return out
    events = []
    for row in calendar_rows or []:
        if not isinstance(row, dict):
            continue
        start = _split_dt(row.get("start"))
        if start is None:
            continue  # a start we cannot even read a date from: not this window's problem, never a crash
        sdate, smin = start
        off = _day_bounds(sdate, day)
        if off is None or not (0 <= off < days):
            continue
        day_row = out[off]
        title = str(row.get("title") or row.get("summary") or "untitled event")
        if smin is None:
            # all-day: 0 busy hours; travel only when it is itself a flight/train/hotel (or labelled travel)
            if _is_travel_row(row, title):
                day_row["travel"] = True
            continue
        end = _split_dt(row.get("end"))
        if end is None or end[0] != sdate or end[1] is None:
            # empty end, unparseable end, or an end on a different day: unusable, named, contributes nothing
            day_row["unusable"].append(title)
            continue
        emin = end[1]
        if emin < smin:
            day_row["unusable"].append(title)
            continue
        if emin == smin:
            continue  # zero-length: 0 busy hours
        if _is_travel_row(row, title):
            day_row["travel"] = True
        events.append((off, smin, emin, title))
    for off, smin, emin, _title in events:
        lo, hi = max(smin, win_lo), min(emin, win_hi)
        if hi > lo:
            out[off]["busy_hours"] += (hi - lo) / 60.0
    # free hours need merged busy minutes, so overlaps are not subtracted twice
    for i, day_row in enumerate(out):
        ivs = sorted((max(s, win_lo), min(e, win_hi)) for o, s, e, _t in events if o == i and min(e, win_hi) > max(s, win_lo))
        merged = []
        for lo, hi in ivs:
            if merged and lo <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], hi)
            else:
                merged.append([lo, hi])
        busy_min = sum(hi - lo for lo, hi in merged)
        raw = sorted((s, e) for o, s, e, _t in events if o == i)   # busy = the real event time, window or not
        rmerged = []
        for lo, hi in raw:
            if rmerged and lo <= rmerged[-1][1]:
                rmerged[-1][1] = max(rmerged[-1][1], hi)
            else:
                rmerged.append([lo, hi])
        day_row["busy_hours"] = round(sum(hi - lo for lo, hi in rmerged) / 60.0, 2)
        day_row["free_hours"] = round(max(0.0, (win_hi - win_lo) - busy_min) / 60.0, 2)
    # collisions: pairs of overlapping events, same day, on real times
    for i in range(days):
        evs = sorted((s, e) for o, s, e, _t in events if o == i)
        pairs = 0
        for a in range(len(evs)):
            for b in range(a + 1, len(evs)):
                if evs[b][0] < evs[a][1]:
                    pairs += 1
        out[i]["collisions"] = pairs
        # back-to-backs: one event ends within BACK_TO_BACK_MIN minutes of the next starting
        b2b = 0
        for a in range(len(evs) - 1):
            gap = evs[a + 1][0] - evs[a][1]
            if 0 <= gap <= BACK_TO_BACK_MIN:
                b2b += 1
        out[i]["back_to_backs"] = b2b
    return out

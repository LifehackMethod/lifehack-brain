"""snapshot_layout.py - 4P.3 item 5 (the fixed layout) and item 4 (the unclassified-emails rows), pure code.

The morning snapshot's four load-bearing sections appear in ONE fixed order, as level-2 headings
exactly as named in SECTIONS; the snapshot's other sections are kept but never appear between these
four. check_layout(text) -> a list of problems (missing section, wrong name, wrong order, sections
 wedged in between), empty when the layout is right. The same four are mirrored as keys in the
 .form.json (see morning.py's form assembly).

unclassified_rows(rows) -> the catalogue rows triage could not place: needs_me "cant_tell", or no
triage guess at all. Quarantined or refused mail (verdict != "safe") NEVER appears here - it stays
in the held/quarantined notice, envelope facts only.

Python 3.9 compatible. Pure functions; no I/O.
"""

import re

SECTIONS = ("## World model", "## Questions", "## Capacity", "## Unclassified emails")

HEADING_RE = re.compile(r"^## .*$", re.MULTILINE)


def check_layout(text):
    """-> a list of problems with the snapshot's section layout; [] when the four load-bearing
    sections are present, correctly named, in order, with no other section between them."""
    problems = []
    text = str(text or "")
    headings = [(m.start(), m.group().strip()) for m in HEADING_RE.finditer(text)]
    names = [h for _off, h in headings]
    for s in SECTIONS:
        if names.count(s) == 0:
            problems.append("missing section: %s" % s)
    pos = []
    for s in SECTIONS:
        at = [off for off, h in headings if h == s]
        pos.append(at[0] if at else None)
    seen = [p for p in pos if p is not None]
    if len(seen) == len(SECTIONS) and seen != sorted(seen):
        problems.append("sections out of order: expected %s" % " -> ".join(SECTIONS))
    first, last = pos[0], pos[-1]
    if first is not None and last is not None and first < last:
        between = [h for off, h in headings if first < off < last and h not in SECTIONS]
        if between:
            problems.append("sections between the four load-bearing ones: %s" % ", ".join(between))
    return problems


def unclassified_rows(rows):
    """The rows triage could not place, from the catalogue rows the morning run gathered:
    a triage dict with needs_me "cant_tell", or no triage dict at all. A row whose verdict is not
    "safe" (quarantined, refused at ingest, anything not delivered clean) is never returned."""
    out = []
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        if r.get("verdict") != "safe":
            continue  # quarantined / refused: never in this list
        t = r.get("triage")
        if isinstance(t, dict):
            if t.get("needs_me") != "cant_tell":
                continue
            guess = t.get("area") or "none"
        else:
            guess = "none"  # no triage at all
        out.append({"sender": r.get("from") or r.get("sender") or "unknown sender",
                    "date": r.get("date") or "",
                    "subject": r.get("subject") or "",
                    "guess": guess,
                    "message_id": r.get("message_id") or ""})
    return out

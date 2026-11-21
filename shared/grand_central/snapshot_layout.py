"""snapshot_layout.py - 4P.3 item 5 (the fixed layout) and item 4 (the unclassified-emails rows), pure code.

The morning snapshot (4P.3R) is CODE's fixed-layout lists first, then the AI's part last: the four
load-bearing sections appear in ONE fixed order, as level-2 headings exactly as named in SECTIONS
(Needs him, Capacity, Unclassified emails, then the AI's "The morning draft", always the LAST
heading); code's other lists sit between Unclassified emails and the AI's part, never between
the first three. check_layout(text) -> a list of problems (missing section, wrong name, wrong order,
sections wedged in between, the AI's part not last), empty when the layout is right.

unclassified_rows(rows) -> the catalogue rows triage could not place: needs_me "cant_tell", or no
triage guess at all. Quarantined or refused mail (verdict != "safe") NEVER appears here - it stays
in the held/quarantined notice, envelope facts only.

Python 3.9 compatible. Pure functions; no I/O.
"""

import re

SECTIONS = ("## Needs him", "## Capacity", "## Unclassified emails", "## The morning draft")

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
    first, third = pos[0], pos[2]
    if first is not None and third is not None and first < third:
        between = [h for off, h in headings if first < off < third and h not in SECTIONS]
        if between:
            problems.append("sections between the load-bearing ones: %s" % ", ".join(between))
    if pos[3] is not None and headings and headings[-1][1] != SECTIONS[3]:
        problems.append("the AI's part (%s) is not the last section" % SECTIONS[3])
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

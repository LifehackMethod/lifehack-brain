#!/usr/bin/env python3
"""
gauge_check.py — the mechanical referee for a brief's ## CURRENT STATE section.

A brief's `## CURRENT STATE` (a.k.a. "§2") is a GAUGE, not a LOG: it must hold
exactly ONE current-status surface, stay inside a size budget, and never be
older than the work already recorded below it in `## STORY LOG`. This script
COUNTS, MEASURES, and COMPARES DATES. It has NO judgment — it never decides
what a block of prose MEANS and it never rewrites anything. That split is
deliberate: the LLM does all the sorting/rewriting; this is the rule the LLM
cannot quietly skip, because a skipped check leaves a machine-checkable trace
(a nonzero exit code) instead of a vibe.

Detection is WHITELIST, not blacklist. The ONE legal status surface is the
three-rung altitude block — a line containing `▲ 10,000`, plus its `▲ 5,000`
and `▲ ground` siblings (whitespace after `▲` is not load-bearing; brief
authors are inconsistent about it, so the marker regex tolerates any run of
whitespace). Every other markdown heading or bolded lead-in line inside §2
that asserts a project-level position is a COMPETING surface — this is checked
by NEGATIVE space (does not match the one legal shape or a named exception),
never by matching a growing list of known-bad header phrasings. A prior
incident: 8 stacked "where do things stand" blocks in one real brief used 8
distinct header variants, so a blacklist of known-bad shapes would have rotted
and certified a broken brief as clean.

Verdicts (closed set — exactly one token, plus evidence, per run):
  ONE-GAUGE          exit 0   exactly one status surface, in budget, not stale
  COMPETING-GAUGES    exit 2   more than one status surface
  OVERSIZED           exit 2   one gauge, but over the size budget
  STALE               exit 2   one gauge, in budget, but older than the newest
                                ## STORY LOG entry
  NO-GAUGE            exit 3   §2 exists but holds no status surface at all
  CANNOT-READ         exit 4   file missing/unreadable/unparseable, or no §2

CANNOT-READ NEVER exits 0. A brief on an unreadable Drive/FUSE mount must
return CANNOT-READ, never a false ONE-GAUGE — this system has already shipped
that exact false-green once.

Usage:
    gauge_check.py check <brief_path> [--json]
    gauge_check.py --all [--json]

--all resolves every brief listed in `$DRIVE/system/project-registry.md` and
prints a ranked table, worst-first. Exit 0 only if every brief is ONE-GAUGE.
"""

import sys
import os
import re
import json
import argparse

# ---------------------------------------------------------------------------
# Module-level constants — the legal shape + the size budget. Nothing below
# this block should hardcode a number or a marker string a second time.
# ---------------------------------------------------------------------------

# DRIVE default — overridable via the DRIVE env var (kept a constant, not
# buried in a function, so --all's resolution root is visible at a glance).
# The notes root for `--all`, from the one resolver. There is no default path here on purpose:
# a hardcoded home worked on exactly one machine, and guessing a folder is the failure the
# resolver exists to prevent. `DRIVE` still overrides, for a one-off scan of somewhere else.
def _notes_root():
    import sys as _sys
    _repo = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                          "..", "..", ".."))
    _sys.path.insert(0, os.path.join(_repo, "shared"))
    try:
        import brain_root
        return brain_root.resolve_brain_root()[1]
    except Exception:
        return None


DRIVE_DEFAULT = _notes_root()

# The no-outcome exit code, shared with every other check in this system: the check
# never ran, so it has nothing to say about pass or fail.
CANNOT_READ_RC = 4

# The ONE legal status-surface shape: any line naming one of the three rungs.
# Whitespace after ▲ is deliberately flexible (real briefs are inconsistent).
ALTITUDE_MARKER_RE = re.compile(r'▲\s*(?:10,000|5,000|ground)', re.IGNORECASE)

# The three legal named decision-board buckets — NOT status surfaces. Matches
# either emoji-then-bold ("⛔ **RULED-OUT (...):**") or bold-then-emoji
# ("**⛔ RULED-OUT (...):**"), which are both used in the wild.
DECISION_BUCKET_RE = re.compile(
    r'^[\s*✅⛔❓]*(LOCKED|RULED-OUT|OPEN)\s*(?:\([^)]*\))?\s*:',
    re.IGNORECASE,
)

# A markdown heading of any depth from H2 to H6, once a line is stripped of
# its blockquote/bullet prefix.
HEADING_RE = re.compile(r'^#{2,6}\s')

# A section boundary — top-level (H2) headings only. §2 runs from its own
# "## CURRENT STATE..." line to the line BEFORE the next one of these.
H2_RE = re.compile(r'^##\s')

CURRENT_STATE_NAME_RE = re.compile(r'CURRENT STATE', re.IGNORECASE)
STORY_LOG_NAME_RE = re.compile(r'STORY LOG', re.IGNORECASE)

DATE_RE = re.compile(r'\d{4}-\d{2}-\d{2}')

# A frontmatter `updated_at:` key line, inside the leading `---`...`---` YAML block. The VALUE is
# extracted with DATE_RE below — this regex only locates the key; it never parses the date itself,
# so there is exactly one date-parsing pattern in this file, reused everywhere.
FRONTMATTER_UPDATED_AT_RE = re.compile(r'^updated_at:\s*(.+?)\s*$', re.IGNORECASE)
# The text inside a leading **...** span. Used to test whether a bold lead-in is
# a DATED position claim (a status surface) or mere prose emphasis (not one).
BOLD_SPAN_RE = re.compile(r'\*\*(.+?)\*\*')

# Size budget.
SECTION_LINE_CAP = 120          # §2 must be <= this many lines
SECTION_PCT_OF_STORY_LOG = 25.0  # and <= this % of ## STORY LOG's line count

# Below this many §2 lines, the PERCENTAGE half of the oversized `or` does not
# apply (the ABSOLUTE line cap above still always applies, unconditionally).
#
# MEASURED 2026-08-07 across every brief in system/project-registry.md (45
# briefs with a readable §2; `gauge_check.py --all` + a one-off tabulation
# script, not eyeballed) — the ONLY two briefs in the whole fleet whose
# verdict the percentage half of the `or` actually DECIDES (single surface,
# under the 120-line absolute cap, but over 25% of a short Story Log) are:
#     project-system   31 §2-lines / 84  story-log-lines = 36.9%  -> OVERSIZED
#     skill-builder    41 §2-lines / 157 story-log-lines = 26.1%  -> OVERSIZED
# Every other brief either has >1 surface (never reaches this check),
# breaches the 120-line absolute cap outright regardless of any floor
# (the-books: 516 lines; ai-bootcamp-lesson1: 259; cowork-bulk-ingestion:
# 169; helm: 151), or is comfortably under 25%. (skill-system, sometimes
# cited elsewhere as a large §2, measured 107 lines / 1741 story-log-lines =
# 6.1% at the time of this measurement — already well clear on both terms;
# it is NOT part of the OVERSIZED-via-percentage population this floor
# governs, and no floor value changes that.)
#
# 40 = SECTION_LINE_CAP // 3, chosen as a round fraction of the existing
# absolute cap rather than a value hand-fit to either of the two live
# cases: it clears project-system (31 < 40, percentage check suppressed)
# while still leaving skill-builder (41 >= 40) subject to the percentage
# check it currently, correctly, fails. No number was found (or needed)
# to separate project-system from a genuinely oversized brief like
# the-books — the unconditional absolute cap already does that on its own.
SECTION_RATIO_FLOOR = 40

EXIT_CODES = {
    "ONE-GAUGE": 0,
    "COMPETING-GAUGES": 2,
    "OVERSIZED": 2,
    "STALE": 2,
    "NO-GAUGE": 3,
    "CANNOT-READ": 4,
}


# ---------------------------------------------------------------------------
# Section extraction
# ---------------------------------------------------------------------------

def find_section(lines, name_re):
    """Locate a top-level (## ) section whose heading matches name_re.

    Returns (start, end) as 0-indexed line indices into `lines`, where the
    section is lines[start:end] (heading line INCLUDED at start, boundary
    heading EXCLUDED at end — end is len(lines) if there is no next H2).
    Returns None if no such heading exists.
    """
    start = None
    for i, line in enumerate(lines):
        if H2_RE.match(line) and name_re.search(line):
            start = i
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if H2_RE.match(lines[j]):
            end = j
            break
    return start, end


def strip_markup_prefix(line):
    """Strip leading blockquote markers, list bullets, and numbered-list
    markers so the underlying content can be tested for a heading/bold lead.
    Does NOT strip bold markers or emoji — those matter to the checks below.
    """
    s = line.strip()
    while True:
        new = re.sub(r'^>+\s*', '', s)
        new = re.sub(r'^[-*+]\s+', '', new)
        new = re.sub(r'^\d+[a-zA-Z]?\.\s+', '', new)
        if new == s:
            return s
        s = new


def paragraph_end(lines, start_idx, end_idx):
    """Index (exclusive) of the end of the contiguous non-blank paragraph
    beginning at start_idx, bounded by end_idx."""
    j = start_idx
    while j < end_idx and lines[j].strip() != '':
        j += 1
    return j


# ---------------------------------------------------------------------------
# Surface detection (whitelist)
# ---------------------------------------------------------------------------

def detect_surfaces(lines, start, end):
    """Return the list of status surfaces found in lines[start:end]. The
    section's own heading line (index `start`) is never itself a surface.
    The altitude trio — however many of its lines are present — collapses
    into exactly ONE surface entry, per the spec: 'treat the trio as ONE
    surface.'
    """
    trio_lines = []
    other = []
    for idx in range(start + 1, end):
        raw = lines[idx]
        lineno = idx + 1
        if ALTITUDE_MARKER_RE.search(raw):
            trio_lines.append(lineno)
            continue
        clean = strip_markup_prefix(raw)
        if not clean:
            continue
        if DECISION_BUCKET_RE.match(clean):
            continue
        if HEADING_RE.match(clean):
            other.append({"line": lineno, "type": "heading", "snippet": clean[:88]})
        elif clean.startswith('**'):
            # A bold lead-in is a STATUS SURFACE only if it carries a DATE inside
            # the bold span. Measured 2026-08-06 on the pathological brief: bold
            # alone flagged 96 surfaces (**cal-weekly**, **READ THIS FIRST**, ...)
            # — prose emphasis, not status claims. Requiring a date drops 61 false
            # positives and keeps every real one, because a status block is a
            # DATED POSITION CLAIM and bold emphasis is not.
            # 96 findings get skimmed; that is the failure this tool exists to fix.
            # ⚠ The bold span may not CLOSE on this line — real status blocks
            # routinely wrap ("**WHERE WE ARE (2026-07-20, session close) —\n
            # more text**"). A closed-span-only regex silently skips those, i.e.
            # it misses the very blocks this tool exists to find. Caught by the
            # regression suite 2026-08-06 on the first patch attempt. So: test the
            # closed span when there is one, else the rest of the line.
            bold_span = BOLD_SPAN_RE.match(clean)
            lead_text = bold_span.group(1) if bold_span else clean[2:]
            if DATE_RE.search(lead_text):
                other.append({"line": lineno, "type": "dated-bold-lead-in",
                              "snippet": clean[:88]})

    surfaces = []
    if trio_lines:
        surfaces.append({"type": "altitude-trio", "lines": trio_lines})
    surfaces.extend(other)
    return surfaces


def find_gauge_date(lines, start, end, surfaces):
    """A YYYY-MM-DD in the §2 heading line, or in the altitude-trio block(s)
    (the marker line plus the rest of its paragraph). Returns the newest date
    found, or None if unfindable."""
    dates = DATE_RE.findall(lines[start])
    trio = next((s for s in surfaces if s["type"] == "altitude-trio"), None)
    if trio:
        for lineno in trio["lines"]:
            idx = lineno - 1
            pend = paragraph_end(lines, idx, end)
            for l in lines[idx:pend]:
                dates.extend(DATE_RE.findall(l))
    return max(dates) if dates else None


# A STORY LOG entry LEADS with its date (optionally behind a list marker or a
# table pipe). A date anywhere else in the line is prose — "check on 2026-08-10",
# "the 2026-07-21 ruling" — and must NOT be read as an entry date.
ENTRY_DATE_RE = re.compile(
    r'^\s*(?:[-*+]\s*|\|\s*)?\*{0,2}(\d{4}-\d{2}-\d{2})\*{0,2}\s*(?:[—\-–]|:|\|)'
)


def find_newest_date(lines, span):
    """Newest ENTRY date in the Story Log.

    ⚠ Fixed 2026-08-06: this used to take max() over EVERY date in the section,
    so a Story Log entry whose PROSE mentioned a future date made the whole log
    look newer than it was — measured live, it returned 2026-08-10 on a brief
    written 2026-08-06, four days in the future, which would silently flip every
    gauge in that brief to STALE. An entry date leads its line; a mentioned date
    does not.

    ⚠ SECOND FIX, same day: requiring only a leading date was still not enough.
    A WRAPPED CONTINUATION line can itself begin with a date mid-sentence —
    measured live: "  2026-08-10 14:00 EDT**, and REFUSED to launch" is the tail
    of an entry, not an entry. A real entry date is followed by a SEPARATOR
    (— : |); a mentioned one is followed by prose or a clock time. Requiring the
    separator is what finally distinguishes them.
    """
    if span is None:
        return None
    s, e = span
    dates = []
    for l in lines[s:e]:
        m = ENTRY_DATE_RE.match(l)
        if m:
            dates.append(m.group(1))
    return max(dates) if dates else None


def find_frontmatter_updated_at(lines):
    """Parse a leading YAML frontmatter block (`---` ... `---` at the very top of the file) for
    an `updated_at:` key, and return the date found in its value via DATE_RE — the SAME date
    pattern used by find_gauge_date() and find_newest_date() above, so there is only ever one
    date-parsing regex in this file, never a second one invented for frontmatter.

    Returns None (never an error) if: the file has no frontmatter block, the block has no
    `updated_at:` key, or that key's value has no parseable YYYY-MM-DD date. A brief legitimately
    may not carry `updated_at:` at all — that is NOT a defect this tool reports on.
    """
    if not lines or lines[0].strip() != '---':
        return None
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == '---':
            end = i
            break
    if end is None:
        return None
    for line in lines[1:end]:
        m = FRONTMATTER_UPDATED_AT_RE.match(line.strip())
        if m:
            date_m = DATE_RE.search(m.group(1))
            return date_m.group(0) if date_m else None
    return None


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def evaluate_brief(path):
    result = {"brief": path}

    if not os.path.isfile(path):
        result["verdict"] = "CANNOT-READ"
        result["reason"] = "file missing"
        return result

    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        result["verdict"] = "CANNOT-READ"
        result["reason"] = f"unreadable: {e}"
        return result
    except UnicodeDecodeError as e:
        result["verdict"] = "CANNOT-READ"
        result["reason"] = f"unparseable (encoding): {e}"
        return result

    lines = text.splitlines()
    sec = find_section(lines, CURRENT_STATE_NAME_RE)
    if sec is None:
        result["verdict"] = "CANNOT-READ"
        result["reason"] = "no ## CURRENT STATE section found"
        return result

    start, end = sec
    section_lines = end - start
    surfaces = detect_surfaces(lines, start, end)
    n_surfaces = len(surfaces)

    sl_span = find_section(lines, STORY_LOG_NAME_RE)
    story_log_lines = (sl_span[1] - sl_span[0]) if sl_span else None
    pct = (section_lines / story_log_lines * 100.0) if story_log_lines else None

    gauge_date = find_gauge_date(lines, start, end, surfaces)
    newest_sl_date = find_newest_date(lines, sl_span)
    if gauge_date and newest_sl_date:
        stale = gauge_date < newest_sl_date
    else:
        stale = "indeterminate"

    # STALE-FRONTMATTER (added 2026-08-07): compares the frontmatter's `updated_at:` against
    # the SAME "newest dated entry" the STALE check above already knows how to find
    # (find_newest_date() over ## STORY LOG) — no second date-finder was written for this. Only
    # set when BOTH sides are present; a brief without frontmatter or without a Story Log has
    # nothing to compare and stays silent (see find_frontmatter_updated_at()'s docstring).
    frontmatter_updated_at = find_frontmatter_updated_at(lines)
    frontmatter_stale = None
    if frontmatter_updated_at and newest_sl_date:
        frontmatter_stale = frontmatter_updated_at < newest_sl_date

    result.update({
        "section_lines": section_lines,
        "story_log_lines": story_log_lines,
        "percent_of_story_log": pct,
        "surfaces": surfaces,
        "n_surfaces": n_surfaces,
        "gauge_date": gauge_date,
        "newest_story_log_date": newest_sl_date,
        "stale": stale,
        "frontmatter_updated_at": frontmatter_updated_at,
        "frontmatter_stale": frontmatter_stale,
    })

    if n_surfaces == 0:
        result["verdict"] = "NO-GAUGE"
        return result

    if n_surfaces > 1:
        result["verdict"] = "COMPETING-GAUGES"
        return result

    oversized = section_lines > SECTION_LINE_CAP or (
        pct is not None
        and section_lines >= SECTION_RATIO_FLOOR
        and pct > SECTION_PCT_OF_STORY_LOG
    )
    if oversized:
        result["verdict"] = "OVERSIZED"
        return result

    if stale is True:
        result["verdict"] = "STALE"
        return result

    result["verdict"] = "ONE-GAUGE"
    return result


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_text(result):
    out = [result["verdict"]]
    out.append(f"  brief: {result['brief']}")

    if result["verdict"] == "CANNOT-READ":
        out.append(f"  reason: {result.get('reason', 'unknown')}")
        return "\n".join(out)

    pct = result["percent_of_story_log"]
    pct_s = f"{pct:.1f}%" if pct is not None else "n/a (no ## STORY LOG)"
    out.append(
        f"  section: {result['section_lines']} lines (cap {SECTION_LINE_CAP}) · "
        f"{pct_s} of story log (cap {SECTION_PCT_OF_STORY_LOG:.0f}%)"
    )
    out.append(f"  surfaces: {result['n_surfaces']}")
    for s in result["surfaces"]:
        if s["type"] == "altitude-trio":
            out.append(f"  - altitude-trio @ lines {s['lines']}")
        else:
            out.append(f"  - {s['type']} @ line {s['line']}: {s['snippet']!r}")
    out.append(
        f"  gauge_date: {result['gauge_date']!r} vs "
        f"newest_story_log_date: {result['newest_story_log_date']!r} "
        f"(stale={result['stale']})"
    )
    # STALE-FRONTMATTER is a WARNING LINE, not a new verdict token — see gauge_check.py's module
    # docstring "Verdicts (closed set...)". It is orthogonal to §2's own shape (a brief can be a
    # perfectly clean ONE-GAUGE and still carry a stale `updated_at:`), so folding it into the
    # closed verdict set would force an arbitrary precedence call between two unrelated defects.
    # It never changes the verdict token or the exit code.
    if result.get("frontmatter_stale"):
        out.append(
            f"  ⚠ STALE-FRONTMATTER: frontmatter updated_at {result['frontmatter_updated_at']!r} "
            f"predates newest known Story Log date {result['newest_story_log_date']!r}"
        )
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Registry resolution (--all)
# ---------------------------------------------------------------------------

def resolve_registry_briefs(drive):
    reg_path = os.path.join(drive, "system", "project-registry.md")
    try:
        with open(reg_path, encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError as e:
        print(f"ERROR: cannot read registry {reg_path}: {e}", file=sys.stderr)
        return []

    start = 0
    for i, l in enumerate(lines):
        if re.match(r'^##\s*Registry', l):
            start = i + 1
            break

    briefs = []
    seen = set()
    for line in lines[start:]:
        if "|" not in line:
            continue
        fields = [f.strip() for f in line.split("|")]
        if len(fields) < 5:
            continue
        desk, slug, path = fields[0], fields[1], fields[4]
        if not desk or not slug or not path:
            continue
        # guard against re-matching the fenced format example above ## Registry
        if desk == "{desk}" or slug == "{slug}":
            continue
        brief_rel = path if path.endswith("brief.md") else path.rstrip("/") + "/brief.md"
        brief_path = os.path.join(drive, brief_rel)
        key = (slug, brief_path)
        if key in seen:
            continue
        seen.add(key)
        briefs.append((slug, brief_path))
    return briefs


SEVERITY = {
    "CANNOT-READ": 5,
    "NO-GAUGE": 4,
    "COMPETING-GAUGES": 3,
    "OVERSIZED": 2,
    "STALE": 1,
    "ONE-GAUGE": 0,
}


def cmd_all(json_out=False):
    drive = os.environ.get("DRIVE") or DRIVE_DEFAULT
    # REFUSE, never crash and never guess (2026-08-11). With no notes folder chosen and no DRIVE
    # override, this used to hand None to os.path.join and die in a traceback four frames deep —
    # which reads as a broken tool rather than as an unanswered question. It is neither: there is
    # simply nowhere to look yet.
    if not drive:
        print("REFUSED: no notes folder is set, so there is no registry to scan.\n"
              "  Set one:  python3 shared/brain_root.py --set \"<that folder>\"\n"
              "  Or point this run somewhere explicitly:  DRIVE=<folder> gauge_check.py --all",
              file=sys.stderr)
        return CANNOT_READ_RC
    briefs = resolve_registry_briefs(drive)
    results = []
    for slug, brief_path in briefs:
        r = evaluate_brief(brief_path)
        r["slug"] = slug
        results.append(r)

    results.sort(
        key=lambda r: (
            SEVERITY.get(r["verdict"], 0),
            r.get("n_surfaces", 0) or 0,
            r.get("percent_of_story_log") or 0,
        ),
        reverse=True,
    )

    all_one_gauge = all(r["verdict"] == "ONE-GAUGE" for r in results)
    exit_code = 0 if all_one_gauge else 2

    if json_out:
        print(json.dumps({"exit": exit_code, "results": results}, default=str))
        return exit_code

    header = f"{'brief':<70} {'surfaces':>8} {'§2 lines':>9} {'% of log':>9}  verdict"
    print(header)
    print("-" * len(header))
    for r in results:
        pct = r.get("percent_of_story_log")
        pct_s = f"{pct:.1f}%" if pct is not None else "n/a"
        n_surf = r.get("n_surfaces")
        n_surf_s = str(n_surf) if n_surf is not None else "-"
        sec_s = str(r.get("section_lines")) if r.get("section_lines") is not None else "-"
        brief_s = r["brief"]
        if len(brief_s) > 70:
            brief_s = "…" + brief_s[-69:]
        print(f"{brief_s:<70} {n_surf_s:>8} {sec_s:>9} {pct_s:>9}  {r['verdict']}"
              + (f" ({r.get('reason')})" if r["verdict"] == "CANNOT-READ" else ""))

    print()
    print(f"{'ALL ONE-GAUGE' if all_one_gauge else 'NOT ALL ONE-GAUGE'} "
          f"({sum(1 for r in results if r['verdict'] == 'ONE-GAUGE')}/{len(results)})")
    return exit_code


def cmd_check(brief_path, json_out=False):
    result = evaluate_brief(brief_path)
    if json_out:
        print(json.dumps(result, default=str))
    else:
        print(render_text(result))
    return EXIT_CODES[result["verdict"]]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(prog="gauge_check.py")
    parser.add_argument("--all", action="store_true",
                         help="check every brief in the project registry")
    parser.add_argument("--json", action="store_true", dest="json_top",
                         help="emit JSON instead of text")
    sub = parser.add_subparsers(dest="cmd")
    p_check = sub.add_parser("check", help="check one brief's ## CURRENT STATE")
    p_check.add_argument("brief_path")
    p_check.add_argument("--json", action="store_true", dest="json_sub")
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    json_out = args.json_top or getattr(args, "json_sub", False)

    if args.all:
        return cmd_all(json_out=json_out)
    if args.cmd == "check":
        return cmd_check(args.brief_path, json_out=json_out)

    parser.print_usage(sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())

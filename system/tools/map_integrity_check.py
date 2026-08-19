#!/usr/bin/env python3
"""map_integrity_check — every element these two documents point at is actually on disk here.

WHY THIS EXISTS. The self-schematic is three documents describing one system: a MAP (a ~69-line
block in the always-loaded `CLAUDE.md`), a MANUAL (`system/organism/manual.md`), and 42 ENCYCLOPEDIA
entries under `system/organism/elements/`. The top two both point down at the third by name. A
pointer that names a file which is not here is the single most-repeated defect class in this
migration: the reader goes hunting, finds nothing, and concludes the SYSTEM lost a part rather than
that the SENTENCE is wrong. That failure is invisible to every other check — the prose is confident,
the tests pass, nothing imports anything — and it grows on every rename, every move, and every
element left behind at the donor. This is the mechanical proof.

  ⚠ `citation_lint.py` does NOT already cover this. It checks backticked REPO paths — a pointer
  written `elements/journal.md`, which is how both documents write them, is not a repo path and it
  never looks at it. The two checks do not overlap.

THE TWO SUBJECTS — and it is two on purpose.

  1. THE MAP     the "System at a glance" block inside `CLAUDE.md` (both the file and the heading
                 are arguments, so the lane that lands the map can point this at it without a code
                 edit). It is read for `elements/<slug>.md` paths AND — only if the block declares
                 the convention itself, by writing `elements/<name>` or `elements/<slug>` somewhere
                 inside it — for BARE `<slug>.md` filenames, which is how the donor's map writes its
                 pointers. A bare name containing a slash is a path to somewhere else and is skipped.
  2. THE MANUAL  `system/organism/manual.md`, whose ranked index lists every element the donor had.
                 Roughly ten of those did not ship. A checker that read only the map would catch
                 none of them, in the very subsystem built to describe this system truthfully.

THE MARKER RULE — read this before you argue with an exit code.

A sibling set of lanes is adding `✅` / `⏳` / `⛔` citation markers to these documents for
`citation_lint.py`. This tool reads them the same way, because two checkers disagreeing about what a
marker means is worse than either one being slightly wrong:

  ✅  IT IS HERE       -> a missing file on a ✅ line is UNDECLARED-MISSING, and worse than an
                          unmarked one: it is a claim of presence that is false.
  ⛔  IT IS NOT COMING -> DECLARED-ABSENT.
  ⏳  IT LANDS LATER   -> DECLARED-ABSENT as well. Both are the same answer to the only question
                          this tool asks — *was the absence named?* — and folding them into one
                          bucket keeps this tool to one idea. Whether a `⏳` has gone stale is
                          `citation_lint.py`'s job, not this one's.

  THE DESIGN CHOICE, STATED SO NOBODY HAS TO INFER IT: **this tool exits non-zero on
  UNDECLARED-MISSING only.** A named absence is a real answer — the document told the reader the
  file is not coming, so the reader is not sent hunting, and no defect exists to fix. An unnamed one
  is the defect. Both are still PRINTED and COUNTED: a declared absence you cannot see is how a
  declaration rots unnoticed.

  SCOPE OF A MARKER. A list row, a table row and a heading are each exactly ONE claim, so a marker
  there covers only its own line — otherwise a single `⛔` on row 21 of a 51-row index would excuse
  all fifty-one. In ordinary prose the marker covers its paragraph, so a wrapped sentence works. And
  a slug declared anywhere in a file is declared EVERYWHERE in that file, so one banner at the top
  can cover a name the document uses twenty times below. (This is `citation_lint.py`'s rule,
  deliberately.)

FAILING LOUD WHEN THE SUBJECT IS NOT THERE — house rule `T9.11b`, `system/build-rules-index.md`.
"I checked and it is clean" and "there was nothing here I could check" are different claims. If a
document is missing, or its map block is missing, or the block is present but yields ZERO pointers,
this exits **2** and names which subject and why. It never reports the pass a healthy run would have
produced. Exit 2 wins over exit 1 when both are true — the run still prints every undeclared miss it
did find, and the summary names both facts, so nothing is hidden behind the code.

Exit: 0 both subjects read, every pointer resolves or is declared
      1 both subjects read, at least one UNDECLARED-MISSING pointer
      2 a subject was absent or ambiguous — nothing here is a pass
      4 could not read the tree at all
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "shared", "emit"))
from verdicts import CANNOT_READ, read_text, print_cannot_read      # noqa: E402

# ─────────────────────────────────────────────────────────────────────────────────────────────────
# THE CONFIG
# ─────────────────────────────────────────────────────────────────────────────────────────────────

ELEMENTS_DIR = os.path.join("system", "organism", "elements")

# A pointer written as a path. The `system/organism/` prefix is optional because both documents
# write the short form far more often than the long one. A placeholder (`elements/<slug>.md`) cannot
# match: `<` is not in the slug character class, which is why there is no placeholder list here.
ELEMENT_PATH = re.compile(r"(?:system/organism/)?elements/([A-Za-z0-9][A-Za-z0-9._-]*)\.md")

# A pointer written as a bare filename — the donor map's form (`| save.md`, `journal.md canon.md`).
# The lookbehind rejects anything with a path in front of it: `docs/architecture.md` is a pointer to
# somewhere else, and the donor map's own line says so in words.
BARE_NAME = re.compile(r"(?<![\w./-])([a-z0-9][a-z0-9._-]*)\.md\b")

# The map block only gets read for bare names if it DECLARES that convention itself, the way the
# donor's does with `files = system/organism/elements/<name>`. No declaration, no bare-name mode —
# a document that writes full paths should not have its unrelated filenames read as element names.
BARE_NAME_CONVENTION = re.compile(r"elements/<\s*(?:name|slug)\s*>")

# Bare `.md` names inside the map block that are never element pointers. Uppercase-initial names
# (CLAUDE.md, README.md, INSTALL.md) cannot match BARE_NAME at all, so only these need naming.
NOT_AN_ELEMENT = {
    "manual": "the middle-altitude manual itself — the layer above the elements, not one of them",
}

# Markers, in the order a line carrying two of them should be read. ✅ wins: presence is the one
# claim checkable against disk, so a line claiming it gets held to it.
PRESENT, DECLARED = "present", "declared"
# The worded forms count ONLY in a table's last cell. In prose "lands in" is said about all sorts of
# things — the measured false positive at the sibling lint was a planning rule reading "...or lands
# in this block", which would have quietly excused every path on its line.
DECLARE_PHRASES = ("lands in", "lands with", "ships in", "not shipped", "does not ship",
                   "not owed", "never ships", "does not migrate")

# A row is one claim; prose is a paragraph. Matched after stripping any blockquote `>` prefix.
ROW_LIKE = re.compile(r"^\s*(?:[-*+]\s|\d+[.)]\s|\||#{1,6}\s)")


class Miss(object):
    """One pointer that does not resolve. `kind` is the whole verdict of this tool."""

    def __init__(self, slug, source, line_no, line, kind, note):
        self.slug, self.source, self.line_no = slug, source, line_no
        self.line, self.kind, self.note = line, kind, note

    def render(self):
        return ("  %-20s %s\n    %s:%d  %s\n    %s\n"
                % (self.kind, "%s/%s.md" % (ELEMENTS_DIR, self.slug),
                   self.source, self.line_no, self.line.strip()[:120], self.note))


def shown(path, root):
    """How a path is named in output: relative when it is inside the repo, absolute when it is not.
    A `../../../tmp/...` in a finding reads as a repo path and is not one."""
    rel = os.path.relpath(path, root)
    return path if rel.startswith("..") else rel


def strip_quote(line):
    return re.sub(r"^\s*>+\s?", "", line)


def claim_on(line):
    """Which claim, if any, this line makes about the files it names."""
    if "✅" in line:
        return PRESENT
    if "⛔" in line or "⏳" in line:
        return DECLARED
    body = strip_quote(line)
    if body.lstrip().startswith("|"):
        cells = body.strip().strip("|").split("|")
        if len(cells) > 1 and any(p in cells[-1].lower() for p in DECLARE_PHRASES):
            return DECLARED
    return None


def paragraphs(lines):
    """Contiguous non-blank runs, as (start_index, [line, ...]). A blank line ends one."""
    out, start, buf = [], 0, []
    for i, line in enumerate(lines):
        if line.strip():
            if not buf:
                start = i
            buf.append(line)
        elif buf:
            out.append((start, buf))
            buf = []
    if buf:
        out.append((start, buf))
    return out


def pointers_in(text, want_bare):
    """Every element pointer in `text`, as (slug, line_no, line). Deduplicated per line, because a
    row naming the same slug in its path and its anchor is still one claim about one file."""
    found = []
    for i, line in enumerate(text.splitlines(), 1):
        seen = set()
        for slug in ELEMENT_PATH.findall(line):
            if slug not in seen:
                seen.add(slug)
                found.append((slug, i, line))
        if not want_bare:
            continue
        stripped = ELEMENT_PATH.sub(" ", line)          # already counted above
        for slug in BARE_NAME.findall(stripped):        # the group is the stem, `.md` stripped
            if slug in NOT_AN_ELEMENT or slug in seen:
                continue
            seen.add(slug)
            found.append((slug, i, line))
    return found


def declared_slugs(text, want_bare):
    """Slugs this file has NAMED as absent — anywhere in it, per the marker-scope rule above.

    A row/heading marker covers its own line only; a prose marker covers its paragraph. Both then
    apply file-wide, so one banner covers every later mention."""
    lines = text.splitlines()
    declared = set()

    def harvest(chunk_lines):
        for slug, _, _ in pointers_in("\n".join(chunk_lines), want_bare):
            declared.add(slug)

    for _, chunk in paragraphs(lines):
        rows = [ln for ln in chunk if ROW_LIKE.match(strip_quote(ln))]
        # A block that is ALL rows is a list or a table: every line stands alone.
        if rows and len(rows) == len(chunk):
            for ln in chunk:
                if claim_on(ln) == DECLARED:
                    harvest([ln])
            continue
        # A prose or mixed block: a marker on one of its PROSE lines covers the whole block (that is
        # how a wrapped sentence and a banner work), while any row inside it still stands alone.
        if any(claim_on(ln) == DECLARED for ln in chunk
               if not ROW_LIKE.match(strip_quote(ln))):
            harvest(chunk)
        for ln in rows:
            if claim_on(ln) == DECLARED:
                harvest([ln])
    return declared


def extract_map_block(text, heading_text):
    """The map block, or (None, why). Absent and ambiguous are both failures, with the reason."""
    lines = text.splitlines()
    wanted = heading_text.lower()
    hits = [(i, len(m.group(1))) for i, line in enumerate(lines)
            for m in [re.match(r"^(#{1,6})\s+(.*)$", line)]
            if m and wanted in m.group(2).lower()]
    if not hits:
        return None, ("no heading containing %r — the map has not landed here yet, or it is under a "
                      "different heading (pass --map-heading)" % heading_text)
    if len(hits) > 1:
        return None, ("%d headings contain %r (lines %s) — which one is the map is ambiguous"
                      % (len(hits), heading_text, ", ".join(str(i + 1) for i, _ in hits)))
    start, level = hits[0]
    end = len(lines)
    for j in range(start + 1, len(lines)):
        m = re.match(r"^(#{1,6})\s+", lines[j])
        if m and len(m.group(1)) <= level:
            end = j
            break
    # Blank-pad so reported line numbers are the real ones in the file.
    return "\n".join([""] * start + lines[start:end]), None


def check_source(label, path, text, root, want_bare, misses, counts):
    """Grade one document. Returns a reason string if its subject was unusable, else None."""
    pointers = pointers_in(text, want_bare)
    if not pointers:
        return ("%s names no elements/<slug>.md pointer at all — either it is not the document this "
                "check was sent to read, or its pointers are written in a form this does not "
                "recognise. Nothing was checked." % label)
    declared = declared_slugs(text, want_bare)
    rel = shown(path, root)
    for slug, line_no, line in pointers:
        counts["checked"] += 1
        if os.path.isfile(os.path.join(root, ELEMENTS_DIR, slug + ".md")):
            counts["resolved"] += 1
            continue
        if slug in declared:
            counts["declared_absent"] += 1
            misses.append(Miss(slug, rel, line_no, line, "DECLARED-ABSENT",
                               "named as not-here by a ⛔/⏳ marker in this file — a real answer, "
                               "not a defect"))
            continue
        counts["undeclared"] += 1
        note = ("the line claims ✅ IT IS HERE and it is not"
                if claim_on(line) == PRESENT else
                "pointed at, not here, and no marker says why — the reader is sent hunting")
        misses.append(Miss(slug, rel, line_no, line, "UNDECLARED-MISSING", note))
    return None


def main(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    default_root = os.path.dirname(os.path.dirname(here))       # system/tools/ -> repo root
    ap = argparse.ArgumentParser(
        description="Prove every element the map and the manual point at is actually here.")
    ap.add_argument("--root", default=default_root,
                    help="repository root (default: this script's own repo, never the cwd)")
    ap.add_argument("--map", default="CLAUDE.md",
                    help="the document holding the map block (default: CLAUDE.md)")
    ap.add_argument("--map-heading", default="System at a glance",
                    help='heading the map block sits under (default: "System at a glance")')
    ap.add_argument("--manual", default=os.path.join("system", "organism", "manual.md"),
                    help="the manual (default: system/organism/manual.md)")
    ap.add_argument("--quiet", action="store_true", help="print nothing when clean")
    args = ap.parse_args(argv)

    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print_cannot_read("no such directory: %s" % root)
        return CANNOT_READ
    if not os.path.isdir(os.path.join(root, ELEMENTS_DIR)):
        print_cannot_read("no %s under %s — there is nothing to check pointers against"
                          % (ELEMENTS_DIR, root))
        return CANNOT_READ

    misses = []
    counts = {"checked": 0, "resolved": 0, "declared_absent": 0, "undeclared": 0}
    unusable = []                       # (subject, why) — the absent-subject verdict

    # ── SUBJECT 1: the map ────────────────────────────────────────────────────────────────────────
    map_path = os.path.join(root, args.map)
    map_text, why = read_text(map_path, "the map document")
    if why:
        unusable.append(("THE MAP", why))
    else:
        block, why = extract_map_block(map_text, args.map_heading)
        if why:
            unusable.append(("THE MAP", "%s: %s" % (shown(map_path, root), why)))
        else:
            want_bare = bool(BARE_NAME_CONVENTION.search(block))
            why = check_source("the map block in %s" % shown(map_path, root),
                               map_path, block, root, want_bare, misses, counts)
            if why:
                unusable.append(("THE MAP", why))

    # ── SUBJECT 2: the manual ─────────────────────────────────────────────────────────────────────
    manual_path = os.path.join(root, args.manual)
    manual_text, why = read_text(manual_path, "the manual")
    if why:
        unusable.append(("THE MANUAL", why))
    else:
        why = check_source("the manual %s" % shown(manual_path, root),
                           manual_path, manual_text, root, False, misses, counts)
        if why:
            unusable.append(("THE MANUAL", why))

    # ── THE VERDICT ───────────────────────────────────────────────────────────────────────────────
    undeclared = [m for m in misses if m.kind == "UNDECLARED-MISSING"]
    if misses:
        print("\n  MAP/MANUAL POINTERS — %d of %d point at an element that is not here "
              "(%d undeclared · %d declared)\n"
              % (len(misses), counts["checked"], len(undeclared), counts["declared_absent"]))
        for m in sorted(misses, key=lambda m: (m.kind, m.source, m.line_no)):
            print(m.render())

    if unusable:
        print("\n  ⛔ SUBJECT-ABSENT — this run did NOT check everything it was sent to check. "
              "That is not a pass.\n")
        for subject, reason in unusable:
            print("  %-12s %s\n" % (subject, reason))
        print("  Also found: %d pointer(s) checked · %d resolved · %d UNDECLARED-MISSING · "
              "%d declared-absent — reported above, and still true.\n"
              % (counts["checked"], counts["resolved"], len(undeclared),
                 counts["declared_absent"]))
        return 2

    if undeclared:
        print("  %d checked · %d resolved · %d declared-absent · %d UNDECLARED-MISSING\n"
              % (counts["checked"], counts["resolved"], counts["declared_absent"],
                 len(undeclared)))
        return 1

    if not args.quiet:
        print("MAP-INTEGRITY-OK  %d pointer(s) checked across 2 documents" % counts["checked"])
        print("  %d resolve · %d named as absent (⛔/⏳) · 0 undeclared"
              % (counts["resolved"], counts["declared_absent"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

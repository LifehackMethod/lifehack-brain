#!/usr/bin/env python3
"""
pad_archive.py — the deterministic safety core for LOSSLESS deletion from a brief.

Nothing is ever removed from a brief until this tool has copied it somewhere append-only
and then read it back off disk to prove the copy landed. It prints a RECEIPT only when
that succeeded, and the caller may not delete without one. "Script not called" and "copy
silently failed" are therefore the same thing: no receipt, no delete. Fails closed.

⚖ ONE TOOL, TWO SHAPES — the merge (ratified here, 2026-08-11). This file used to be two:
`pad_archive.py`, hard-wired to the `## 7. SCRATCHPAD` section, and `section_archive.py`,
which generalised it to any named section and said so in its own opening line. They shared
a hash-chained archive format, a readback-verify, a receipt gate, an idempotent branch, a
size meter — five copies of one idea, drifting apart. They are now one, and the pad is
simply the default section.

⭐ THE MERGE FIXED A REAL BUG IT INHERITED FROM ONE SIDE ONLY. `verify` cross-checks the
number of block markers against the number that parse, to catch a corrupted header. The
pad version counts markers ANCHORED AT LINE START; the section version counted the marker
string ANYWHERE, including inside archived content. That is not hypothetical — it fired on
a live compaction: a note that merely QUOTED the marker while describing this tool got
archived, and `verify` reported a malformed header on a provably perfect chain. Because
the archive is append-only, that false alarm was PERMANENT. The anchored form won.

    archive → copy it somewhere safe and prove it       (the only thing that mints a receipt)
    verify  → is the archive's chain intact             (tamper / lost-block detection)
    state   → is there anything worth compacting        (read-only; never writes)
    clear   → empty the section                         (only bytes proven already archived)

Usage:
    pad_archive.py archive <brief>                              # the scratchpad
    pad_archive.py archive <brief> --heading "## 2. CURRENT STATE (2026-08-06)"
    pad_archive.py archive <brief> --start 45 --end 561
    pad_archive.py verify  <brief> [--heading "..."]
    pad_archive.py state   <brief> [--heading "..."]
    pad_archive.py clear   <brief> [--heading "..."]

stdout (archive): `RECEIPT <sha256>[ ...]` — only on success.
exit   (archive): 0 success (including an idempotent no-op) · 2 failure — DO NOT DELETE
                  · 4 CANNOT-READ (brief missing / unreadable / empty)
exit   (verify) : 0 chain intact · 2 missing/empty/malformed · 3 chain or counter break

## The design, and why each piece is there

- **COPY EVERYTHING FIRST.** The whole section, verbatim, before any sorting or clearing.
  No carve-outs, no reformatting.
- **READ IT BACK.** Re-open the archive by path and assert both the header and the exact
  body are in it. A write that returned success is not evidence.
- **RECEIPT, FAIL CLOSED.** Exit 0 plus `RECEIPT <hash>` is the only proof a caller may act
  on. Every failure path exits non-zero and prints no receipt.
- **SELF-DESCRIBING CHAIN.** Every block stamps `archive #N`, an ISO timestamp, the host,
  the previous block's hash and its own. A missing block shows up as a counter gap; a
  rewritten one breaks the prev-hash chain. That is the tamper evidence.
- **IDEMPOTENT.** Unchanged since the last block → reprint the receipt, append nothing.
- **SIZE METER.** Past a threshold it warns, non-fatally, so "prune it later" has a trigger
  instead of being a plan nobody ever acts on.

## ⛔ No fuzzy matching. Ever.

A named section is identified by an **exact heading line** or by explicit line numbers. The
caller — which has read the brief — decides which section it is; this tool only compares
strings. If the caller is wrong, it refuses; it never helpfully finds something close.

> Ruled 2026-08-06: *"don't make the tool do fuzzy matching, that should belong to the llm.
> we've got a lot of briefs and they don't have standardized sections."*

The earlier version shipped a heading-guessing regex whose match decided what got archived
immediately before a deletion — the highest-stakes call in the whole procedure, living in a
regex. It also could not win: real headings include `## 2. CURRENT STATE`,
`## 1. CURRENT STATE \`ACTIVE\``, `## 2a. PRIOR STATE`, `## CURRENT STATE (2026-08-01)`, and
the first attempt matched `## CURRENT STATE NOTES` — a different section sharing a prefix.

## Two extent rules, and why they are not one

- **The scratchpad** ends only at `ARTIFACTS` or `CHRONICLE`, never at an arbitrary `## `.
  A pad legitimately contains pasted markdown, and stopping at a pad-internal heading would
  silently drop everything after it. Over-capturing to EOF is harmless for an archive;
  under-capturing loses the person's notes. The bias is deliberate.
- **A named section** ends at the next `## `. That is what a section *is*, and the caller
  named it explicitly, so there is no ambiguity to be lossless about.

## The full-file backup, and why only one path takes one

`archive --heading` writes `<brief>.pre-section-archive-<date>.bak` and byte-compares it
before doing anything, because after it returns **the caller deletes the section by hand** —
so damage outside the section has to be undoable too.

The scratchpad path takes no backup, and that is not an oversight. Its delete is `clear`
below: owned by code, atomic, and refusing unless the current bytes hash-match what was
archived. The class of damage a whole-file backup protects against cannot occur there. Do
not "fix" this by adding one — it would write a backup file beside every brief, every day,
against a risk that has been designed out.
"""

import argparse
import datetime
import hashlib
import os
import re
import socket
import sys
import tempfile

_REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(_REPO, "shared", "emit"))
from verdicts import CANNOT_READ, print_cannot_read, read_text  # noqa: E402

PAD_ARCHIVE_SUFFIX = ".pad-archive.md"
SIZE_WARN_BYTES = 2_000_000   # ~2 MB → warn (non-fatal)
BLOCK_WARN_COUNT = 200        # or this many blocks → warn

# The ONLY body `clear` ever writes in place of a removed section — one unmistakable line, so
# neither a reader nor `state` can confuse "cleared" with "never had anything in it".
_CLEAR_SENTINEL = "_(scratchpad cleared — nothing captured since the last compaction)_"

# The scratchpad header: prefer the canonical "## 7. SCRATCHPAD", fall back to any variant.
SCRATCH_CANON_RE = re.compile(r'^##\s*7\.\s*SCRATCHPAD', re.IGNORECASE | re.MULTILINE)
SCRATCH_ANY_RE = re.compile(r'^##\s.*SCRATCHPAD', re.IGNORECASE | re.MULTILINE)
# The pad's lossless end rule — see "Two extent rules" above.
END_SECTION_RE = re.compile(r'^#{1,3}\s*(?:\+\s*)?(?:\d+\.\s*)?(?:ARTIFACTS|CHRONICLE)\b',
                            re.IGNORECASE | re.MULTILINE)

BLOCK_HDR_RE = re.compile(
    r'<!-- section-archive :: section="(.*?)" :: archive #(\d+) :: .*? :: host=.*? :: '
    r'prev=(\S+) :: hash=([0-9a-f]{64}) -->')
# ⛔ ANCHORED AT LINE START, deliberately — see the bug note at the top of this file. A real
# header is always written at line start (`block = f"\n{header}\n{body}\n"`), so anchoring
# matches the writer exactly and loses no genuine corruption case.
RAW_MARKER_RE = re.compile(r'(?m)^<!-- section-archive ::')


def sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def slugify(section_name):
    """'## 2. CURRENT STATE' -> '2-current-state'; builds the per-section archive filename."""
    s = re.sub(r'^#+\s*', '', section_name.strip()).lower()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    return s.strip('-') or "section"


# --------------------------------------------------------------------------- extents

def _scratchpad_extent(text):
    """(found, start, end) — text[start:end] is the RAW body of the scratchpad, from just
    after the header line to the next ARTIFACTS/CHRONICLE section or EOF."""
    m = SCRATCH_CANON_RE.search(text) or SCRATCH_ANY_RE.search(text)
    if not m:
        return False, 0, 0
    start = m.end()
    nxt = END_SECTION_RE.search(text[start:])
    end = start + nxt.start() if nxt else len(text)
    return True, start, end


def extract_scratchpad(text):
    """Verbatim body of the scratchpad (header line excluded). None if there is no
    scratchpad section at all. Biased to never under-capture.

    ⚠ PUBLIC API. `pm_flag.sh` imports this module and calls this plus sha() so that the
    fingerprint it stamps at arm time and the hash compared later are computed by the SAME
    code. Two definitions of "the pad" would never match. Do not change the signature."""
    found, start, end = _scratchpad_extent(text)
    if not found:
        return None
    return text[start:end].strip("\n")


def find_section_exact(lines, heading):
    """Locate a section by its EXACT heading line. Returns (start_idx, end_idx) or None.
    Raises ValueError if the heading appears more than once — ambiguity is never resolved
    silently. See "No fuzzy matching" at the top of this file."""
    target = heading.strip()
    hits = [i for i, l in enumerate(lines) if l.strip() == target]
    if not hits:
        return None
    if len(hits) > 1:
        raise ValueError(
            f"heading appears {len(hits)} times (lines {[h + 1 for h in hits]}) — "
            f"ambiguous; pass --start/--end line numbers instead")
    start = hits[0]
    for j in range(start + 1, len(lines)):
        if lines[j].startswith('## ') and not lines[j].startswith('###'):
            return start, j
    return start, len(lines)


def resolve_span(lines, heading=None, start=None, end=None):
    """Either an EXACT heading, or explicit 1-indexed line numbers. Never a guess."""
    if start is not None or end is not None:
        if start is None or end is None:
            raise ValueError("--start and --end must be given together")
        if not (1 <= start < end <= len(lines) + 1):
            raise ValueError(f"line range {start}:{end} out of bounds (file has {len(lines)} lines)")
        return start - 1, end - 1
    if heading is None:
        raise ValueError("pass --heading '<exact heading line>' or --start/--end")
    span = find_section_exact(lines, heading)
    if span is None:
        raise ValueError(
            f"no line in the file is exactly {heading!r}. This tool does NOT fuzzy-match by "
            f"design — read the brief, copy the heading verbatim, or pass --start/--end.")
    return span


def select(text, heading=None, start=None, end=None):
    """The one place a verb turns its arguments into a concrete target.

    Returns (name, body, char_start, char_end, heading_end):
      body        the section body, stripped of surrounding newlines — what gets hashed
      char_start  } the RAW span bounding that body in `text`
      char_end    }
      heading_end the offset just past the heading line's newline. `clear` needs it and
                  nothing else does — see the note in cmd_clear for what goes wrong
                  without it. It is returned rather than recomputed so that the heading
                  line is located by the code that already found it.

    Raises ValueError with a caller-facing message when the selector does not resolve."""
    if heading is None and start is None and end is None:
        found, s, e = _scratchpad_extent(text)
        if not found:
            raise ValueError("no ## SCRATCHPAD section found in brief")
        m = SCRATCH_CANON_RE.search(text) or SCRATCH_ANY_RE.search(text)
        nl = text.find("\n", m.start())
        name = text[m.start():nl if nl != -1 else len(text)].strip()
        heading_end = nl + 1 if nl != -1 else len(text)
        return name, text[s:e].strip("\n"), s, e, heading_end

    lines = text.split('\n')
    s_idx, e_idx = resolve_span(lines, heading, start, end)
    name = lines[s_idx].strip()
    # Character offsets of the body: everything after the heading line, up to the section end.
    char_start = sum(len(l) + 1 for l in lines[:s_idx + 1])
    char_end = min(sum(len(l) + 1 for l in lines[:e_idx]), len(text))
    return name, '\n'.join(lines[s_idx + 1:e_idx]).strip('\n'), char_start, char_end, char_start


def archive_path(brief, section_name):
    """The pad keeps its own well-known filename — three shipped documents name it, and
    `<brief>.7-scratchpad-archive.md` reads worse to a person opening the folder."""
    if "SCRATCHPAD" in section_name.upper():
        return brief + PAD_ARCHIVE_SUFFIX
    return f"{brief}.{slugify(section_name)}-archive.md"


def backup_path(brief):
    return f"{brief}.pre-section-archive-{datetime.date.today().isoformat()}.bak"


# --------------------------------------------------------------------------- archive chain

def _blocks(archive_file):
    """Only REAL, fully-formed block headers — immune to the marker appearing inside
    archived content. Returns [(section, n, prev, hash), ...] in file order."""
    if not os.path.exists(archive_file):
        return []
    with open(archive_file, encoding="utf-8") as fh:
        return BLOCK_HDR_RE.findall(fh.read())


def last_block_hash(archive_file):
    blocks = _blocks(archive_file)
    return blocks[-1][3] if blocks else ""


def block_count(archive_file):
    return len(_blocks(archive_file))


# --------------------------------------------------------------------------- verbs

def cmd_archive(brief, heading=None, start=None, end=None):
    text, err = read_text(brief, "brief")
    if err is not None:
        print_cannot_read(err)
        return CANNOT_READ

    is_named = heading is not None or start is not None or end is not None

    if is_named:
        # FULL-FILE BACKUP FIRST — the revert point for the whole brief, because the caller
        # does this delete by hand. See the note at the top of this file.
        try:
            orig_bytes = open(brief, "rb").read()
        except OSError as e:
            print(f"ERROR: could not read brief: {e}", file=sys.stderr)
            return 2
        bpath = backup_path(brief)
        try:
            with open(bpath, "wb") as f:
                f.write(orig_bytes)
            back_bytes = open(bpath, "rb").read()
        except OSError as e:
            print(f"ERROR: backup failed: {e}", file=sys.stderr)
            return 2
        if back_bytes != orig_bytes:
            print(f"ERROR: backup at {bpath} is NOT byte-identical to {brief} — aborting",
                  file=sys.stderr)
            return 2
        text = orig_bytes.decode("utf-8")

    try:
        name, body, _s, _e, _h = select(text, heading, start, end)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    body_hash = sha(body)
    archive = archive_path(brief, name)
    prev = last_block_hash(archive)

    if prev == body_hash:
        print(f"RECEIPT {body_hash} (idempotent — unchanged since last block)")
        return 0

    n = block_count(archive) + 1
    ts = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    header = (f'<!-- section-archive :: section="{name}" :: archive #{n} :: {ts} :: '
              f'host={socket.gethostname()} :: prev={prev or "GENESIS"} :: hash={body_hash} -->')

    try:
        with open(archive, "a", encoding="utf-8") as f:
            f.write(f"\n{header}\n{body}\n")
    except OSError as e:
        print(f"ERROR: append failed: {e}", file=sys.stderr)
        return 2

    # READ IT BACK — re-open by path, prove header AND verbatim body landed.
    try:
        with open(archive, encoding="utf-8") as fh:
            back = fh.read()
    except OSError as e:
        print(f"ERROR: readback failed: {e}", file=sys.stderr)
        return 2
    if f"hash={body_hash}" not in back:
        print("ERROR: readback failed — hash header not found after append", file=sys.stderr)
        return 2
    if body and body not in back:
        print("ERROR: readback failed — content not found after append", file=sys.stderr)
        return 2

    try:
        sz = os.path.getsize(archive)
        if sz > SIZE_WARN_BYTES or n > BLOCK_WARN_COUNT:
            print(f"WARN: {archive} is {sz} bytes / {n} blocks — consider a manual prune",
                  file=sys.stderr)
    except OSError:
        pass

    print(f"RECEIPT {body_hash} archive={n}")
    return 0


def cmd_verify(brief, heading=None):
    archive = archive_path(brief, heading or "SCRATCHPAD")
    if not os.path.exists(archive):
        print(f"ERROR: no archive at {archive}", file=sys.stderr)
        return 2
    with open(archive, encoding="utf-8") as fh:
        txt = fh.read()
    raw = len(RAW_MARKER_RE.findall(txt))
    blocks = BLOCK_HDR_RE.findall(txt)
    if not blocks:
        print("ERROR: no parseable archive blocks", file=sys.stderr)
        return 2
    errors = []
    if len(blocks) != raw:
        errors.append(f"{raw} block markers but only {len(blocks)} parse cleanly "
                      f"→ {raw - len(blocks)} MALFORMED header(s) (tamper/corruption)")
    for i, (_sec, n, prev, _h) in enumerate(blocks):
        if int(n) != i + 1:
            errors.append(f"counter gap: block at position {i + 1} is labelled archive #{n}")
        expected = "GENESIS" if i == 0 else blocks[i - 1][3]
        if prev != expected:
            errors.append(f"chain break at archive #{n}: prev={prev[:12]}… expected {expected[:12]}…")
    if errors:
        print("ARCHIVE INTEGRITY FAILED:", file=sys.stderr)
        for e in errors:
            print("  ✗ " + e, file=sys.stderr)
        return 3
    print(f"OK: {len(blocks)} blocks, chain + counter intact")
    return 0


def cmd_state(brief, heading=None):
    """READ-ONLY: is there anything worth compacting right now? Never writes, appends or
    clears — it reuses the same hash comparison `archive`'s idempotent branch makes, rather
    than minting a second definition of "unchanged".

    ⚠ THE FOUR VERDICT TOKENS AND THEIR EXIT CODES ARE A FROZEN CONTRACT. Callers grep for
    them and branch on the exit code, never on prose. They keep the `PAD-` prefix even for a
    named section, because renaming them would silently break every caller."""
    text, err = read_text(brief, "brief")
    if err is not None:
        print_cannot_read(err)
        return CANNOT_READ

    try:
        _name, body, _s, _e, _h = select(text, heading)
    except ValueError as exc:
        print_cannot_read(f"{exc}: {brief}")
        return CANNOT_READ

    if body == "":
        # A FOUND header that captured zero characters is indistinguishable from a truncated
        # read. Never silently reported as an empty pad.
        print_cannot_read(f"section header found but captured zero characters "
                          f"(truncated read, or a header with no body at all): {brief}")
        return CANNOT_READ

    # EMPTINESS IS DECIDED BY CONTENT, NOT LINE SHAPE. An earlier version matched any all-bold
    # line as boilerplate, which reported a genuinely full pad — one bolded action item — as
    # empty. Only pure whitespace or an exact sentinel match counts as empty now.
    #
    # ⛔ And it evaluates the same region `clear` WRITES, not the whole hashed span. The hashed
    # span opens with the header line's own trailing annotation, which `clear` deliberately
    # preserves — so a freshly-cleared pad is `annotation + sentinel` and would never equal the
    # sentinel exactly. It would have reported dirty forever.
    # ⚠ Stated edge, erring the safe way: a pad that is ONLY a header annotation with no newline
    # after it reads dirty rather than empty. One wasted check, never a lost pad.
    inner = body.split("\n", 1)[1] if "\n" in body else body
    stripped = inner.strip()
    if not stripped or stripped == _CLEAR_SENTINEL.strip():
        print("PAD-EMPTY")
        print("  the scratchpad holds nothing but whitespace, or exactly the post-`clear` "
              "sentinel — nothing to compact.")
        return 0

    body_hash = sha(body)
    prev = last_block_hash(archive_path(brief, _name))
    if prev and prev == body_hash:
        print("PAD-ARCHIVED-UNCLEARED")
        print(f"  sha256={body_hash} matches the last archive block's hash={prev} — "
              f"archived but never cleared.")
        print("  safe to run `clear` without re-archiving.")
        return 3

    print(f"PAD-DIRTY {len(body)}")
    print(f"  sha256={body_hash} · {len(body)} chars · last archive hash="
          f"{prev or '(none — never archived)'} — does not match. COMPACT-ME.")
    return 2


def cmd_clear(brief, heading=None):
    """The ONLY sanctioned way to empty a section — code owns the delete, not a model's
    guess at where the section ends. Refuses, writing nothing, unless the CURRENT bytes
    hash-match the newest archive block. That is the whole safety property: it can only ever
    delete bytes it can prove `archive` already saved. Writes atomically (temp file +
    os.replace) so a crash mid-write cannot truncate the brief."""
    text, err = read_text(brief, "brief")
    if err is not None:
        print_cannot_read(err)
        return CANNOT_READ

    try:
        name, body, span_start, span_end, heading_end = select(text, heading)
    except ValueError as exc:
        print_cannot_read(f"{exc}: {brief}")
        return CANNOT_READ

    # The raw span includes the leading/trailing newlines that `select` strips before hashing.
    # Only the trimmed sub-span was ever hashed and archived, so only THAT may be deleted; the
    # surrounding newlines survive byte for byte.
    raw = text[span_start:span_end]
    lead = len(raw) - len(raw.lstrip("\n"))
    trail = len(raw) - len(raw.rstrip("\n"))
    span_start += lead
    span_end -= trail

    prev = last_block_hash(archive_path(brief, name))
    body_hash = sha(body)
    if not prev or prev != body_hash:
        print(f"REFUSED\n  sha256={body_hash} does not match the last archive block's "
              f"hash={prev or '(no archive found)'} — clear only runs on content PROVEN "
              f"archived. Run `archive {brief}` first, then `clear` again.")
        return 2

    # ⛔ PRESERVE THE HEADING LINE'S OWN ANNOTATION. On a real brief the heading carries a
    # trailing note — `## 7. SCRATCHPAD  *(dumb capture surface — …)*` — which sits inside the
    # hashed span, because the span starts immediately after the word SCRATCHPAD. Archiving it
    # is harmless; deleting it is not. It is the schema's own description of the section, and
    # clearing it would degrade the brief a little on every compaction and leave malformed
    # markdown (`## 7. SCRATCHPAD_(scratchpad cleared…)_`).
    # ⭐ The invariant is `delete ⊆ archive`, not `delete == archive`. Deleting LESS than was
    # archived is always safe, so starting the splice after the heading line costs nothing.
    #
    # ⛔⛔ CLAMP, DO NOT SKIP — the bug this replaced (found 2026-08-11 by the first test that
    # ever exercised `clear`; present and unnoticed in the pre-merge tool). The old line was
    # `nl = text.find("\n", span_start); if nl < span_end: span_start = nl + 1` — an
    # UNCONDITIONAL hop to the next line. When the heading DOES carry an annotation that lands
    # correctly on the first body line. When it does NOT — `## 7. SCRATCHPAD` followed straight
    # by the notes — span_start was already the first body line, so the hop moved it to the
    # SECOND one and the pad's opening line survived the clear.
    # It failed quietly in the worst possible way: `archive` had saved everything (true),
    # `clear` printed `CLEARED <n> chars` (a lie about how much), and the surviving line got
    # re-graduated on the next compaction. Clamping to the end of the heading line is correct in
    # both shapes, because heading_end is derived from the heading, not from the body.
    span_start = max(span_start, heading_end)

    new_text = text[:span_start] + "\n" + _CLEAR_SENTINEL + text[span_end:]
    d = os.path.dirname(os.path.abspath(brief)) or "."
    tmp_fd, tmp_path = tempfile.mkstemp(dir=d, prefix=".pad-clear-", suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            f.write(new_text)
        os.replace(tmp_path, brief)
    except OSError as e:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        print(f"ERROR: atomic write failed: {e}", file=sys.stderr)
        return 2

    print(f"CLEARED {len(body)} chars — matched archive hash={body_hash}")
    return 0


# --------------------------------------------------------------------------- cli

USAGE = ("usage: pad_archive.py archive|verify|state|clear <brief> "
         "[--heading \"## 2. CURRENT STATE\" | --start N --end M]")


def build_argparser():
    p = argparse.ArgumentParser(prog="pad_archive.py", usage=USAGE)
    sub = p.add_subparsers(dest="command")
    for verb in ("archive", "verify", "state", "clear"):
        s = sub.add_parser(verb)
        s.add_argument("brief")
        s.add_argument("--heading", help="EXACT heading line, copied verbatim from the brief")
        if verb == "archive":
            s.add_argument("--start", type=int, help="1-indexed first line of the section")
            s.add_argument("--end", type=int, help="1-indexed line AFTER the section")
    return p


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] not in ("archive", "verify", "state", "clear"):
        print(USAGE, file=sys.stderr)
        return 2
    try:
        args = build_argparser().parse_args(argv)
    except SystemExit:
        return 2   # argparse already printed its own usage/error

    if args.command == "archive":
        return cmd_archive(args.brief, args.heading, args.start, args.end)
    if args.command == "verify":
        return cmd_verify(args.brief, args.heading)
    if args.command == "state":
        return cmd_state(args.brief, args.heading)
    return cmd_clear(args.brief, args.heading)


if __name__ == "__main__":
    sys.exit(main())

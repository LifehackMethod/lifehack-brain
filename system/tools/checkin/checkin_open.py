#!/usr/bin/env python3
"""
checkin_open.py — the mechanical opener for /checkin's altitude-rung display.

`/checkin` must OPEN a session by showing the human the three "altitude rung"
lines from a project brief's ## CURRENT STATE, VERBATIM. A model cannot be
trusted to self-report on whether it actually read and quoted those lines
faithfully, so the rungs must come out of the file MECHANICALLY — printed by
code, not recited from memory.

⛔ THE BUG THIS REWRITE FIXES, proven live 2026-08-06: the old single `rungs`
command did `if MARKER in line` (▲, U+25B2) over the WHOLE FILE. On the real
project-system brief this returned PARTIAL-RUNGS 6, because THREE lines of
ordinary prose elsewhere in the file merely MENTIONED the ▲ character while
describing this very tool — the tool matched its own description.

The governing ruling (mirrors pad_archive.py's own, the same day):
"we don't want [the tool] to go way off the rails, but we don't want it to
break if it's spelled just slightly differently." FINDING the right span is
fuzzy — that's the LLM's job, because it has already read the brief and knows
which lines are the rung block. PRINTING · COUNTING · REFUSING is mechanical
— that's this script's job. A tighter regex trades a VISIBLE false positive
for a SILENT false negative; that is a downgrade, not a fix. So the fix is
not a smarter matcher, it's a SEAM MOVE — same shape as pad_archive.py's
`find_section_exact()`: the caller supplies the scope, the tool never guesses.

Two verbs:

  `print <brief> --start N --end M`
    The CALLER (the LLM, which has already read the brief) supplies the
    range. Scans ONLY lines[start:end] for `▲` and prints each rung group
    VERBATIM (after stripping a leading blockquote marker), joining wrapped
    continuation lines exactly the way the old whole-file scan did — just
    bounded to the given span. Nothing outside the span is ever examined,
    which is the fix: prose elsewhere mentioning ▲ cannot be seen, let alone
    counted.
    ⚠ --start/--end semantics DELIBERATELY differ from pad_archive.py's
    in ONE respect: pad_archive's --start names a HEADING line, which is
    EXCLUDED from the archived content (content = lines[s+1:e]). Here,
    --start names the FIRST RUNG LINE ITSELF — real content, not a heading —
    so it is INCLUDED in the scanned span. Both tools agree that --end is
    1-indexed and EXCLUSIVE (the first line *after* the span) and both use
    the identical bound check `1 <= start < end <= len(lines) + 1`. Getting
    the inclusion side backwards would silently drop the first rung line, so
    this is spelled out here AND in the --start help text.
    ⛔ **THIS EXCLUSIVE --end IS THE DEFECT MEASURED LIVE 2026-08-11**, not a
    character cap — there never was one. A caller that means "through line
    232" but passes `--end 232` gets lines[:231], silently missing 232's
    content, rc 0, no warning. There is still no smarter guess here (that
    would resurrect the exact bug this rewrite fixed — see above), but
    `print` now DETECTS the shape of that mistake mechanically — the last
    rung's continuation scan ran off the end of the slice instead of
    stopping at a real boundary, and the file keeps going past --end — and
    says so on stderr. See `cmd_print`'s WARNING branch.
    ⭐ `--paste` (added 2026-08-11): same scan, same span, same VERDICT
    token and exit codes — only the STDOUT formatting changes, to the
    chat-safe shape confirmed as correct by watching it: bolded `**label**`, ONE
    blank line between rungs, no hard breaks. Plain `print` (no flag) keeps
    printing its raw-from-disk shape unchanged, so nothing else that calls
    it breaks. When plain `print` finds a rung that was hard-wrapped on
    disk, it also emits a stderr-only HINT nudging toward --paste — the
    "reminder" a model cannot be trusted to give itself.

  `hint <brief>`
    PERMISSIVE and ADVISORY ONLY — the file-wide symbol hunt, kept alive so
    the LLM has something to build a `print` range from. Prints every line
    containing `▲`, prefixed with its 1-indexed line number. Being wrong
    here costs nothing: nothing acts on `hint`'s output directly, a human
    (or the calling LLM) picks the range from it. Never prints a verdict
    token, and always exits 0 unless the file itself cannot be read.

`rungs` is kept as a DEPRECATED ALIAS for `hint` (not for the old file-wide
verdict behavior) — see the module-level note in this file's return value /
commit message for why: skills/checkin/SKILL.md currently invokes `rungs`
and was being edited in parallel with this rewrite.

Verdicts:
  print:
    RUNGS <n>            exit 0   n rung-groups found in the given span
                                   (ANY n, including 0 — a caller-supplied
                                   span producing an unexpected count is a
                                   CALLER error, not a file-state error;
                                   this tool does not editorialize about
                                   whether n should have been 3)
    BAD-RANGE <why>      exit 2   inverted, out of bounds, or an empty span
    CANNOT-READ <why>    exit 4   file missing/unreadable/undecodable —
                                   STDERR, NEVER exit 0
  hint:
    (numbered candidate lines, no verdict token) exit 0
    CANNOT-READ <why>    exit 4   STDERR, NEVER exit 0

CANNOT-READ NEVER exits 0 — briefs live on a Google Drive FUSE mount that has
produced live false-green reads before ("I could not look" must never be
spelled the same way as "I looked and it was fine").

Usage:
    checkin_open.py print <brief_path> --start N --end M [--paste]
    checkin_open.py hint  <brief_path>
    checkin_open.py rungs <brief_path>     # DEPRECATED alias for `hint`
"""

import sys
import os
import argparse

MARKER = "▲"

EXIT_CODES = {
    "RUNGS": 0,
    "BAD-RANGE": 2,
    "CANNOT-READ": 4,
}


# ---------------------------------------------------------------------------
# Blockquote helpers
# ---------------------------------------------------------------------------

def is_quoted(line):
    """True if the RAW line (leading/trailing whitespace ignored) opens a
    markdown blockquote — starts with `>`."""
    return line.strip().startswith(">")


def strip_quote(line):
    """Strip a leading markdown blockquote marker (`> ` or `>`) and any
    leading/trailing whitespace. Strips exactly one level — this codebase's
    briefs do not nest blockquotes for rung content."""
    s = line.strip()
    if s.startswith(">"):
        s = s[1:].strip()
    return s


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------

def read_lines(path):
    """Returns (lines, error_reason). error_reason is None on success."""
    if not os.path.isfile(path):
        return None, "file missing"
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        return None, f"unreadable: {e}"
    except UnicodeDecodeError as e:
        return None, f"unparseable (encoding): {e}"
    return text.splitlines(), None


# ---------------------------------------------------------------------------
# Rung extraction (the SAME algorithm as before — now callable on any slice)
# ---------------------------------------------------------------------------

def extract_rungs(lines, limit=None):
    """Scan `lines` for lines containing `▲` and return `(rungs,
    multiline_flags, tail_extended)`.

    `limit` (default: len(lines)) bounds where NEW rungs may be DISCOVERED
    — the caller-supplied scope that keeps this tool from ever repeating
    the old whole-file false-positive bug (prose elsewhere merely
    *mentioning* `▲`). **What `limit` does NOT bound is how far the LAST
    discovered rung's CONTINUATION may read.** That search always runs to
    `len(lines)` regardless of `limit`, stopping only at a real boundary —
    the next `▲`, a blank line, a heading, a new `**` lead-in, or a
    blockquote-depth change. This is the 2026-08-11 fix: measured live,
    `print --start 220 --end 232` on a real brief cut the `▲ ground` rung
    off mid-sentence ("…inventing a") purely because `--end` (EXCLUSIVE)
    landed one physical line short of the rung's real end — not because of
    any character-width cap; there never was one in this function. The LLM
    caller only has to name WHERE a rung's block STARTS; code now always
    finds that rung's TRUE end, however far past `limit` it actually falls,
    the same way it always has for everything else in this file: printing
    is mechanical, never lossy just because a human-chosen boundary guessed
    short. This can never manufacture a new rung or grow the count — the
    inner loop still stops dead on the first `▲` it meets, so a genuinely
    separate rung sitting right after `limit` is never folded in, only the
    CURRENT rung's own remaining prose is.

      rungs           — list of rung strings, in order, each already joined
                         from its continuation lines (if any) into ONE line.
                         The matched `▲` line itself is returned VERBATIM
                         (post quote-strip) — no reformatting, no bold-marker
                         removal, no length cap of any kind.
      multiline_flags — parallel list of bool, one per rung: True if that
                         rung had at least one continuation line ON DISK
                         (i.e. is hard-wrapped in the source), used by
                         `cmd_print` to decide whether to print the
                         --paste HINT.
      tail_extended    — True if the LAST rung's continuation search read
                         at least one line PAST `limit` to reach its real
                         end. `cmd_print` uses this to tell the caller their
                         --end guessed short, even though nothing was lost.

    A continuation line is the next line (or the next line after a prior
    continuation of the SAME rung) that:
      - does not itself contain `▲` (that starts the NEXT rung instead), and
      - is not blank (after stripping any blockquote marker), and
      - does not start with `#` (a heading) or `**` (a new bold lead-in), and
      - is "still inside the same blockquote" as its rung's own opening line
        — i.e. its raw quoted-ness (leading `>`) must match the rung line's.
    This is deliberately DUMB and mechanical, not "smart stopping" — see the
    module docstring for why smart stopping is exactly the failure mode this
    tool exists to avoid.
    """
    n_total = len(lines)
    n_discover = n_total if limit is None else min(limit, n_total)
    rungs = []
    multiline_flags = []
    tail_extended = False
    i = 0
    while i < n_discover:
        line = lines[i]
        if MARKER in line:
            quoted = is_quoted(line)
            parts = [strip_quote(line)]
            j = i + 1
            while j < n_total:  # tail may read past n_discover — see docstring
                nxt = lines[j]
                if MARKER in nxt:
                    break
                if is_quoted(nxt) != quoted:
                    break
                content = strip_quote(nxt)
                if content == "":
                    break
                if content.startswith("#"):
                    break
                if content.startswith("**"):
                    break
                parts.append(content)
                j += 1
            rungs.append(" ".join(parts))
            multiline_flags.append(len(parts) > 1)
            tail_extended = (j > n_discover)  # meaningful only for the LAST rung
            i = j
        else:
            i += 1
    return rungs, multiline_flags, tail_extended


# ---------------------------------------------------------------------------
# --paste formatting (chat-safe: bold label, blank line between rungs)
# ---------------------------------------------------------------------------

def format_rung_paste(rung):
    """Bold the label portion of an already-joined rung string for --paste
    output: "▲ 10,000 — text..." -> "**▲ 10,000** — text...". Splits on the
    FIRST " — " (em dash, spaced) since that is the fixed separator between
    label and body every rung uses. If a rung is malformed and carries no
    " — " at all, return it UNCHANGED rather than guess where the label
    ends — never alter the words to force a shape."""
    sep = " — "
    idx = rung.find(sep)
    if idx == -1:
        return rung
    label, rest = rung[:idx], rung[idx + len(sep):]
    return f"**{label}** — {rest}"


# ---------------------------------------------------------------------------
# print — caller-scoped, mechanical
# ---------------------------------------------------------------------------

def resolve_print_span(total_lines, start, end):
    """Validate and convert 1-indexed --start/--end into a 0-indexed,
    end-EXCLUSIVE slice bound: lines[s:e].

    Bound check is IDENTICAL to pad_archive.py's: 1 <= start < end <=
    total_lines + 1. What differs from pad_archive.py is what the slice
    INCLUDES: there, --start names a heading that gets excluded from the
    content (lines[s+1:e]); here, --start already names the first line of
    real content the caller wants, so it stays INCLUDED (lines[s:e], i.e.
    lines[start-1:end-1] in 1-indexed terms).

    Raises ValueError with a specific, human-readable reason for each of the
    three BAD-RANGE causes (inverted / empty / out of bounds) so the caller
    sees exactly what was wrong with the range it supplied.
    """
    if start > end:
        raise ValueError(f"inverted range: --start {start} > --end {end}")
    if start == end:
        raise ValueError(f"empty span: --start {start} == --end {end}")
    if not (1 <= start < end <= total_lines + 1):
        raise ValueError(
            f"out of bounds: --start {start} --end {end} (file has {total_lines} "
            f"lines; valid range is 1 <= --start < --end <= {total_lines + 1})"
        )
    return start - 1, end - 1


def cmd_print(brief_path, start, end, paste=False):
    lines, err = read_lines(brief_path)
    if err is not None:
        print(f"CANNOT-READ {err}", file=sys.stderr)
        return EXIT_CODES["CANNOT-READ"]

    try:
        s, e = resolve_print_span(len(lines), start, end)
    except ValueError as exc:
        print(f"BAD-RANGE {exc}")
        return EXIT_CODES["BAD-RANGE"]

    # ⛔ DEFECT-1 FIX, 2026-08-11: `limit=e` still bounds where NEW rungs can
    # be DISCOVERED (the anti-false-positive scope from the original
    # rewrite), but the LAST rung's continuation is allowed to read past it
    # to its real end — see extract_rungs' docstring. `lines[s:]` (not
    # `lines[s:e]`) is what makes that possible: the tail scan needs the
    # rest of the file available to read into.
    rungs, multiline_flags, tail_extended = extract_rungs(lines[s:], limit=e - s)

    # First stdout line is ALWAYS the verdict token, in both modes.
    print(f"RUNGS {len(rungs)}")

    if paste:
        # Chat-safe form: bolded label, ONE blank line between rungs, no
        # hard breaks (extract_rungs already joined continuations for us).
        for idx, rung in enumerate(rungs):
            if idx > 0:
                print()
            print(format_rung_paste(rung))
    else:
        # Raw-from-disk form — unchanged behaviour, no formatting applied.
        for rung in rungs:
            print(rung)

    # NOTE, both modes: tell the caller their --end guessed short, even
    # though extract_rungs already printed the rung in FULL regardless —
    # measured live 2026-08-11, a caller-supplied --end landing mid-rung
    # used to cut the tail off silently (rc 0, no signal); now it never
    # loses the text, but this still surfaces that the boundary was short,
    # since a --end that keeps guessing short on every call is itself a
    # sign the caller is misreading the block.
    if rungs and tail_extended:
        print(
            f"NOTE: the last rung's real end sat past --end {end} — printed "
            "in full anyway (nothing was cut), but your range guessed "
            "short; widen --end next time to match the rung's actual extent.",
            file=sys.stderr,
        )

    if not paste:
        # THE REMINDER (asked for after the third time): a nudge toward --paste when
        # the source is hard-wrapped, so the model doesn't have to remember
        # on its own. stderr only — never contaminates the verbatim stdout
        # that gets pasted into the reply.
        if any(multiline_flags):
            print(
                "HINT: this block is hard-wrapped — re-run with --paste for "
                "the chat-safe one-line-per-rung form.",
                file=sys.stderr,
            )

    return EXIT_CODES["RUNGS"]


# ---------------------------------------------------------------------------
# hint — permissive, file-wide, advisory only
# ---------------------------------------------------------------------------

def cmd_hint(brief_path):
    lines, err = read_lines(brief_path)
    if err is not None:
        print(f"CANNOT-READ {err}", file=sys.stderr)
        return EXIT_CODES["CANNOT-READ"]

    for i, line in enumerate(lines):
        if MARKER in line:
            print(f"{i + 1}: {line}")
    return 0


# ---------------------------------------------------------------------------
# rungs — DEPRECATED alias for `hint`
# ---------------------------------------------------------------------------

def cmd_rungs_deprecated(brief_path):
    print(
        "DEPRECATED: `rungs` is now an alias for `hint` — permissive, "
        "advisory-only, no verdict token, exit 0 unless unreadable. The old "
        "`rungs` verdict behavior (RUNGS/NO-RUNGS/PARTIAL-RUNGS, whole-file "
        "scan) is retired — it is the exact bug this rewrite fixes. Use "
        "`checkin_open.py print <brief> --start N --end M` for the mechanical "
        "verdict `rungs` used to emit.",
        file=sys.stderr,
    )
    return cmd_hint(brief_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(prog="checkin_open.py")
    sub = parser.add_subparsers(dest="cmd")

    p_print = sub.add_parser(
        "print", help="print the rung groups found in an explicit, caller-supplied line span"
    )
    p_print.add_argument("brief_path")
    p_print.add_argument(
        "--start", type=int, required=True,
        help="1-indexed FIRST RUNG LINE — INCLUDED in the scanned span. "
             "⚠ Unlike pad_archive.py's --start, this does NOT name a "
             "heading to exclude; it names real content to include.",
    )
    p_print.add_argument(
        "--end", type=int, required=True,
        help="1-indexed and EXCLUSIVE — the first line AFTER the span, "
             "matching pad_archive.py's --end convention exactly.",
    )
    p_print.add_argument(
        "--paste", action="store_true",
        help="chat-safe form: bolded label, continuation lines joined onto "
             "ONE logical line each (already true of the default output — "
             "extract_rungs always joins), blank line BETWEEN rungs. "
             "Without this flag, print keeps its raw-from-disk behaviour "
             "unchanged — nothing else that calls print without --paste "
             "breaks. The verdict token and exit codes are identical in "
             "both modes.",
    )

    p_hint = sub.add_parser(
        "hint", help="permissive: list every line containing ▲, numbered, advisory only"
    )
    p_hint.add_argument("brief_path")

    p_rungs = sub.add_parser("rungs", help="DEPRECATED — alias for `hint`")
    p_rungs.add_argument("brief_path")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.cmd == "print":
        return cmd_print(args.brief_path, args.start, args.end, paste=args.paste)
    if args.cmd == "hint":
        return cmd_hint(args.brief_path)
    if args.cmd == "rungs":
        return cmd_rungs_deprecated(args.brief_path)

    parser.print_usage(sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())

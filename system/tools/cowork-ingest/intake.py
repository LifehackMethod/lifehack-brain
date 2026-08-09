#!/usr/bin/env python3
"""
intake.py — PHASE 1's format-fork dispatcher (the `1.0a` FLATTEN step).

`/ingest` is supposed to work on ANY corpus ("any type of larger files" — the ratified
outcome). Before this file existed, no phase driver ever called `flatten.py`, so a corpus
had to arrive already converted, by hand — the capability was permanently out of reach
(see `SPEC.md:694`). This file is the thing that moves the parse step INSIDE the skill.

⚖ SCOPE RULING (ruled 2026-08-08, authority: user): `/ingest`'s input is A CORPUS OF
INFORMATION. IN SCOPE: a chat export (ChatGPT and similar) · a large document · markdown
files · plain text files. OUT OF SCOPE for now: email · complicated PDFs · other structured
formats. Not a general folder-walker, not chat-only — a TEXT-CORPUS ingester.

Job: decide, by INSPECTING the input (never by asking the model to guess), which converter
turns a raw corpus — a directory OR a single large document file — into the flattened `.txt`
shape the rest of `/ingest` consumes, then call it. **THIS FILE DISPATCHES; IT DOES NOT
REPLACE OR RE-IMPLEMENT flatten.py or tag.py** — a new format gets its own detector +
converter added beside the ones below; `flatten.py` itself is never forked (a recorded
dead-end: undocumented forks of one tool drift silently).

The closed outcome set for `flatten` is exactly:
  {FLATTENED, ALREADY-DONE, UNRECOGNISED-FORMAT}
`UNRECOGNISED-FORMAT` is the no-outcome member — code checks membership; anything off-list
is surfaced, never silently absorbed. It is a genuine "I cannot do this" stop, NOT a
threshold or a quality bar: a hard refusing threshold once blocked the author's live corpus
within hours (dead-end `[B14]`), so nothing here may refuse a corpus it CAN parse.

ZERO-OUTPUT REFUSAL (build rule, applies to EVERY converter — old and new alike): a
converter that writes zero `.txt` files must never report FLATTENED. `do_flatten` below
checks GROUND TRUTH — the actual `.txt` files on disk after the converter returns — not
whatever the converter's own manifest claims, because a converter that writes 0 files but
still claims success would let `_already_flattened`'s `rows`-truthy check mask the failure
forever on every later run, and the corpus map downstream would get built from an empty
directory. This is enforced ONCE, centrally, so no future FORMATS row can forget it.

Usage:
  python3 intake.py flatten --raw <input-dir-or-file> --out <flat-dir>
    ALREADY-DONE  (exit 0, nothing written) — <flat-dir> already holds a flattened corpus.
    FLATTENED     (exit 0)                  — a recognised input was found and converted.
    UNRECOGNISED-FORMAT (exit 2)            — <raw> matches no known input shape; names the
                                               formats that ARE supported.
    (zero-output refusal, exit 3)           — a detector matched but the converter produced
                                               no output files; never reported as FLATTENED.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
import time
# HARD ENV FACT: /usr/bin/python3 is 3.9 — `X | None` annotations crash at import.
# No type hints below use that form (none needed); if one is ever added, use
# `from typing import Optional` and `Optional[...]`, never `X | None`.

HERE = os.path.dirname(os.path.abspath(__file__))


# ── format detectors — INSPECT the input, never guess ──────────────────────────────────
# Each entry is (format name, detector(raw) -> bool, converter(raw, out_dir) -> None).
# `raw` may be a DIRECTORY (chatgpt-export, markdown-dir, plaintext-dir) or a single FILE
# (large-document). Each detector self-guards which shape it wants (isdir / isfile) so the
# dispatch loop below can stay format-agnostic. To teach intake.py a new format: add a tuple
# here. Never fork flatten.py to do it.

def _is_chatgpt_export(raw):
    """ChatGPT account export: a dir of `conversations-*.json` shards — flatten.py's own
    `--raw` shape (its docstring: 'dir containing conversations-*.json shards')."""
    return os.path.isdir(raw) and bool(glob.glob(os.path.join(raw, "conversations-*.json")))


def _run_flatten_py(raw_dir, out_dir):
    """Hand off to flatten.py UNCHANGED — never re-implemented, never forked."""
    cmd = [sys.executable, os.path.join(HERE, "flatten.py"), "--raw", raw_dir, "--out", out_dir]
    subprocess.run(cmd, check=True)


def _tree_glob(raw_dir, pattern):
    """Every `pattern` file ANYWHERE under raw_dir, sorted.

    RECURSIVE since 2026-08-09. It was top-level-only, and on a real Obsidian vault that
    ingested 1 file of 24 and printed `converted 1 of 1` — a complete-looking success,
    because the denominator was the glob's own result. Folder-organised notes are the
    normal case, not an edge case.

    `glob` with `**` deliberately SKIPS dot-directories, which is what keeps `.obsidian/`
    and `.claude/` out for free. Do not swap this for os.walk without re-adding that filter,
    or the ingest starts eating config.
    """
    return sorted(glob.glob(os.path.join(raw_dir, "**", pattern), recursive=True))


def _has_manifest_anywhere(raw_dir):
    """True if a prior flatten output sits ANYWHERE in the tree — the recursive read makes a
    top-level-only check insufficient: a stale flatten dir nested one level down would be
    re-ingested as source, feeding the system its own output."""
    return bool(glob.glob(os.path.join(raw_dir, "**", "_manifest.json"), recursive=True))


def _is_markdown_dir(raw):
    """Dir containing `*.md` files at ANY depth. No output-dir trap for the format itself:
    every converter here (and flatten.py) writes ONLY `.txt`, never `.md` — but a nested
    prior flatten output is still refused, see `_has_manifest_anywhere`."""
    return (os.path.isdir(raw)
            and not _has_manifest_anywhere(raw)
            and bool(_tree_glob(raw, "*.md")))


def _convert_markdown_dir(raw_dir, out_dir):
    """Dir of `*.md` files -> one flattened `.txt` per source file. File-for-file — no internal
    splitting (W3 below is the one that splits, and only for a single large document)."""
    _convert_flat_dir(raw_dir, out_dir, "*.md", "markdown")


def _is_plaintext_dir(raw):
    """Dir of `*.txt` files.

    ⚠ THE OUTPUT-DIR TRAP: every converter in this file — and flatten.py itself — WRITES its
    output as `.txt` files plus a `_manifest.json` fingerprint. A naive `*.txt` glob here would
    therefore match flatten's OWN prior output and re-ingest the system's own work as if it
    were a fresh corpus.

    DEFENSE: `_manifest.json`'s presence in `raw` is that exact fingerprint — the SAME file
    `_already_flattened` (below) keys on to recognise a flatten OUTPUT directory. A `raw` dir
    carrying `_manifest.json` is therefore never treated as a fresh `.txt` corpus, no matter
    how many `.txt` files it holds. The `ALREADY-DONE` check (which fires first, against
    `--out`) still wins for the normal case of literally re-running on the same output dir;
    this defends the DIFFERENT case of pointing a fresh `--raw` at what is actually an old
    `--out`.
    """
    if not os.path.isdir(raw):
        return False
    if _has_manifest_anywhere(raw):     # NESTED prior output counts too, not just top-level
        return False
    return bool(_tree_glob(raw, "*.txt"))


def _convert_plaintext_dir(raw_dir, out_dir):
    """Dir of `*.txt` files -> one flattened `.txt` per source file (file-for-file, like W1)."""
    _convert_flat_dir(raw_dir, out_dir, "*.txt", "plaintext")


def _convert_flat_dir(raw_dir, out_dir, pattern, fmt_label):
    """Shared W1/W2 converter: one input file -> one labeled `.txt` output. Each output is
    wrapped in the same shape flatten.py's own output uses — a provenance header (lines not
    starting with `## `) followed by a `## document` turn — so `tag.py`'s `split_header_turns`
    parses it identically regardless of source format. A file with only whitespace content is
    skipped (mirrors flatten.py's `skipped_empty`), never written as a blank output; if that
    skips EVERYTHING, `do_flatten`'s zero-output check refuses the whole run rather than
    reporting FLATTENED on nothing."""
    os.makedirs(out_dir, exist_ok=True)
    paths = _tree_glob(raw_dir, pattern)

    # ⛔ OUTPUT NAMES COME FROM THE RELATIVE PATH, NEVER THE BASENAME.
    # This is the trap that makes the recursive read dangerous if you only add `**`.
    # Flat input guaranteed unique basenames; a tree does not. A vault with `./CLAUDE.md`
    # and `./Projects/Thing/CLAUDE.md` maps BOTH to `CLAUDE.txt` — the second overwrites the
    # first, and `written` still counts 2. That trades a loud drop for a SILENT one, which is
    # strictly worse. Found by a real run against a real Obsidian vault, 2026-08-09.
    def _outname(p):
        rel = os.path.relpath(p, raw_dir)
        return os.path.splitext(rel)[0].replace(os.sep, "__") + ".txt"

    # Fail loudly if a future change ever reintroduces a collision, rather than overwriting.
    _names = [_outname(p) for p in paths]
    if len(set(_names)) != len(_names):
        dupes = sorted({n for n in _names if _names.count(n) > 1})
        raise SystemExit(f"REFUSED: output name collision — {len(dupes)} duplicate(s): "
                         f"{', '.join(dupes[:5])}. Two sources would write the same file.")

    manifest_rows = {}
    written = skipped_empty = 0
    for p in paths:
        with open(p, "r", errors="replace") as fh:
            body = fh.read().strip()
        rel = os.path.relpath(p, raw_dir)               # provenance: the PATH, not the basename
        base = os.path.splitext(rel)[0]
        name = _outname(p)
        if not body:
            skipped_empty += 1
            continue
        header = [
            f"# {base}",
            f"# source_format: {fmt_label}",
            f"# source_file: {rel}",
            "",
            "## document",
        ]
        with open(os.path.join(out_dir, name), "w") as fh:
            fh.write("\n".join(header) + "\n" + body + "\n")
        manifest_rows[name] = {
            "file": name, "title": base, "source_file": rel, "chars": len(body),
        }
        written += 1
    with open(os.path.join(out_dir, "_manifest.json"), "w") as fh:
        json.dump({
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "format": fmt_label, "source_files": len(paths),
            "written": written, "skipped_empty": skipped_empty, "rows": manifest_rows,
        }, fh, indent=2)
    # ⚠ REPORT AGAINST THE TREE, NOT THE GLOB. The old line printed `written of len(paths)`
    # where paths WAS the glob result, so the denominator could never reveal what the glob
    # never matched — `converted 1 of 1` while 23 files sat unread. State the tree total so
    # the number is falsifiable.
    tree_total = len(_tree_glob(raw_dir, pattern))
    print(f"OK: converted {written} of {tree_total} {fmt_label} file(s) found in the tree "
          f"({skipped_empty} empty skipped) -> {out_dir}")
    if tree_total and written < tree_total - skipped_empty:
        print(f"⚠ WARNING: {tree_total - skipped_empty - written} file(s) present in the tree "
              f"were NOT converted. This should be zero — investigate before relying on this run.")


# ── W3: a single large document (--raw is a FILE) — MECHANICAL split, zero LLM ─────────────
# SPLIT RULE (stated here because it's the contract, not an implementation detail):
#   1. If the document contains markdown ATX heading lines (`#` through `######` at the start
#      of a line, any level), split at EVERY heading line — each heading starts a new unit;
#      any non-blank text before the first heading becomes a leading "(preamble)" unit.
#      Known limitation: a `#`-looking line inside a fenced code block is not distinguished
#      from a real heading (no code-fence tracking) — a plain, honest naive-markdown split.
#   2. Otherwise (no heading line anywhere), FIXED-SIZE chunks of CHUNK_SIZE=4000 characters,
#      each cut snapped BACK to the nearest preceding newline within CHUNK_LOOKBACK=400 chars
#      (so a unit doesn't end mid-line) when one exists, else a hard cut at exactly 4000 chars.
# Both rules are code constants over a length/pattern input — no LLM anywhere in this path;
# flatten.py's zero-LLM guarantee is inherited, not re-decided.
_HEADING_RE = re.compile(r"^#{1,6}\s+\S")
CHUNK_SIZE = 4000
CHUNK_LOOKBACK = 400


def _is_large_document(raw):
    """A single FILE passed via --raw (not a directory) — the large-document format."""
    return os.path.isfile(raw)


def _split_by_headings(text):
    """Split at every markdown ATX heading line. Returns [] if the document has none — the
    caller falls back to `_chunk_fixed`. Returns a list of (title, body) pairs."""
    lines = text.split("\n")
    heading_idxs = [i for i, l in enumerate(lines) if _HEADING_RE.match(l)]
    if not heading_idxs:
        return []
    units = []
    if heading_idxs[0] > 0:
        pre = "\n".join(lines[:heading_idxs[0]]).strip()
        if pre:
            units.append(("(preamble)", pre))
    for n, start in enumerate(heading_idxs):
        end = heading_idxs[n + 1] if n + 1 < len(heading_idxs) else len(lines)
        title = lines[start].lstrip("#").strip() or f"section-{n + 1}"
        body = "\n".join(lines[start:end]).strip()
        if body:
            units.append((title, body))
    return units


def _chunk_fixed(text, size=CHUNK_SIZE, lookback=CHUNK_LOOKBACK):
    """Deterministic fixed-size split, used only when the document has no heading to split on.
    See the W3 docstring above for the exact rule."""
    chunks = []
    i, n = 0, len(text)
    while i < n:
        end = min(i + size, n)
        if end < n:
            nl = text.rfind("\n", max(i, end - lookback), end)
            if nl != -1 and nl > i:
                end = nl + 1
        chunks.append(text[i:end])
        i = end
    return chunks


def _convert_large_document(raw_path, out_dir):
    """Single large document -> multiple readable `.txt` units. See the W3 comment block above
    for the exact (mechanical, zero-LLM) split rule."""
    with open(raw_path, "r", errors="replace") as fh:
        text = fh.read()
    base = os.path.splitext(os.path.basename(raw_path))[0]
    slug_base = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-") or "document"

    heading_units = _split_by_headings(text)
    if heading_units:
        units, rule = heading_units, "markdown-headings"
    else:
        units = [(f"chunk-{i + 1}", c.strip()) for i, c in enumerate(_chunk_fixed(text)) if c.strip()]
        rule = f"fixed-size ({CHUNK_SIZE}-char chunks, {CHUNK_LOOKBACK}-char newline snap)"

    os.makedirs(out_dir, exist_ok=True)
    manifest_rows = {}
    written = 0
    for idx, (title, body) in enumerate(units):
        tslug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40] or f"unit-{idx + 1}"
        name = f"{slug_base}-{idx + 1:03d}-{tslug}.txt"
        header = [
            f"# {title}",
            f"# source_document: {os.path.basename(raw_path)}",
            f"# unit: {idx + 1} of {len(units)} · split_rule: {rule}",
            "",
            "## document",
        ]
        with open(os.path.join(out_dir, name), "w") as fh:
            fh.write("\n".join(header) + "\n" + body + "\n")
        manifest_rows[name] = {
            "file": name, "title": title, "unit_index": idx + 1,
            "chars": len(body), "source_document": os.path.basename(raw_path),
        }
        written += 1

    with open(os.path.join(out_dir, "_manifest.json"), "w") as fh:
        json.dump({
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "format": "large-document", "split_rule": rule,
            "units_total": len(units), "units_written": written, "rows": manifest_rows,
        }, fh, indent=2)
    print(f"OK: split {os.path.basename(raw_path)} into {written} unit(s) via {rule} -> {out_dir}")


FORMATS = [
    ("chatgpt-export (a dir of conversations-*.json shards)", _is_chatgpt_export, _run_flatten_py),
    ("markdown-dir (a dir of *.md files)", _is_markdown_dir, _convert_markdown_dir),
    ("plaintext-dir (a dir of *.txt files)", _is_plaintext_dir, _convert_plaintext_dir),
    ("large-document (a single file passed via --raw)", _is_large_document, _convert_large_document),
    # another known format's (detector, converter) goes here, beside these.
]


def _already_flattened(out_dir):
    """ALREADY-DONE check: a prior flatten wrote `_manifest.json` with at least one row.
    Never re-flatten on a second run — the author's 1,521-chat corpus depends on this no-op."""
    manifest = os.path.join(out_dir, "_manifest.json")
    if not os.path.isfile(manifest):
        return False
    try:
        with open(manifest) as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return False
    return bool(data.get("rows"))


def do_flatten(args):
    if _already_flattened(args.out):
        print(f"ALREADY-DONE: {args.out} already holds a flattened corpus — nothing re-flattened")
        return 0

    for name, detect, convert in FORMATS:
        if detect(args.raw):
            print(f"detected format: {name}")
            try:
                convert(args.raw, args.out)
            except subprocess.CalledProcessError as exc:
                print(f"ERROR: converter for '{name}' failed (exit {exc.returncode})", file=sys.stderr)
                return exc.returncode or 1

            # ZERO-OUTPUT REFUSAL — ground truth on disk, applies to EVERY converter above
            # (including the pre-existing chatgpt-export one, wired through this same check).
            # See the module docstring for why this must never be skipped.
            written = len(glob.glob(os.path.join(args.out, "*.txt")))
            if written == 0:
                stale_manifest = os.path.join(args.out, "_manifest.json")
                if os.path.isfile(stale_manifest):
                    # scrub it so a manifest that claimed success can't cause a false
                    # ALREADY-DONE on the next attempt, permanently masking this failure.
                    os.remove(stale_manifest)
                print(f"ERROR: converter for '{name}' produced ZERO output files from "
                      f"'{args.raw}' — refusing to report success on an empty result.",
                      file=sys.stderr)
                return 3

            print(f"FLATTENED: {args.raw} -> {args.out} (format: {name}, {written} file(s))")
            return 0

    supported = "; ".join(name for name, _, _ in FORMATS)
    print(f"UNRECOGNISED-FORMAT: '{args.raw}' does not match any supported input format.",
          file=sys.stderr)
    print(f"Supported formats: {supported}.", file=sys.stderr)
    print("Never guessing a parser — point --raw at one of the supported input shapes, "
          "or add a new detector+converter to intake.py's FORMATS list.", file=sys.stderr)
    return 2


def main():
    ap = argparse.ArgumentParser(description="PHASE 1 intake dispatcher — flatten, by format fork")
    sub = ap.add_subparsers(dest="mode", required=True)
    f = sub.add_parser("flatten", help="detect the raw input's format and flatten it")
    f.add_argument("--raw", required=True, help="dir holding the raw corpus, OR a single large-document file")
    f.add_argument("--out", required=True, help="flatten output dir (the FLAT dir)")
    args = ap.parse_args()
    sys.exit({"flatten": do_flatten}[args.mode](args))


if __name__ == "__main__":
    main()

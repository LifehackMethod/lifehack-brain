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

# ══════════════════════════════════════════════════════════════════════════════════════════════════
# RESOLVE — normalise whatever the human handed over into a DIRECTORY, before any detector runs.
# ══════════════════════════════════════════════════════════════════════════════════════════════════
# ⭐ THIS STEP EXISTS BECAUSE THE DETECTORS BELOW ASSUME A TIDY DIRECTORY AND A PERSON HANDS OVER
# WHATEVER THEIR VENDOR GAVE THEM. Measured 2026-08-09: a real ChatGPT export was refused as
# UNRECOGNISED-FORMAT because it was still a `.zip`. Nothing was wrong with the parser — the tool simply
# could not open the suitcase. **Both ChatGPT and Claude hand you a zip, so every single person hits
# this**, and on macOS a zip and the folder it expands to look nearly identical in Finder, so they cannot
# tell which one they dragged in.
#
# TWO WRAPPERS, BOTH INVISIBLE TO THE PERSON:
#   1. the archive itself (`export.zip`)
#   2. the single wrapper folder inside it (`export.zip` -> `chatgpt-export-2026-08-09/` -> the real files)
# Unwrapping only the first still refuses, which is WORSE than refusing outright: it looks like it worked.
#
# ⛔ IT UNWRAPS, IT NEVER PARSES. Resolution answers "where are the files"; the FORMATS table answers
# "what are they". Keeping those apart is what stops every future format needing its own zip branch.
def _safe_extract(zip_path, dest):
    """Extract, refusing any member that would escape `dest` (zip-slip). The corpus is UNTRUSTED input —
    it is the whole reason this tool has a sanitisation gate downstream — so an archive that tries to
    write outside its own folder is refused, not sanitised."""
    import zipfile
    dest_abs = os.path.abspath(dest)
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.namelist():
            target = os.path.abspath(os.path.join(dest_abs, member))
            if not (target == dest_abs or target.startswith(dest_abs + os.sep)):
                raise ValueError(f"refusing archive: '{member}' would write outside the extraction folder")
        zf.extractall(dest_abs)


def _descend_single_wrapper(d, depth=3):
    """`export/` holding exactly one folder and nothing else IS that folder. Bounded depth — a corpus
    genuinely nested four deep is not a wrapper, it is a structure, and descending it would silently
    discard whatever sits beside it."""
    for _ in range(depth):
        try:
            kids = [k for k in os.listdir(d) if not k.startswith((".", "__MACOSX"))]
        except OSError:
            return d
        subdirs = [k for k in kids if os.path.isdir(os.path.join(d, k))]
        if len(kids) == 1 and len(subdirs) == 1:
            d = os.path.join(d, subdirs[0])
            continue
        break
    return d


def resolve_input(raw, out_dir):
    """Return (path, notes). `path` is a directory (or the original file for the large-document format).
    `notes` are plain sentences to show the human — unwrapping must never be silent, or they will not
    understand what the tool actually read."""
    notes = []
    if os.path.isfile(raw) and raw.lower().endswith(".zip"):
        dest = os.path.join(os.path.dirname(os.path.abspath(out_dir)),
                            "_unpacked", os.path.splitext(os.path.basename(raw))[0])
        if not os.path.isdir(dest) or not os.listdir(dest):
            os.makedirs(dest, exist_ok=True)
            _safe_extract(raw, dest)
            notes.append(f"unzipped '{os.path.basename(raw)}' -> {dest}")
        else:
            notes.append(f"using the already-unzipped copy at {dest}")
        raw = dest
    if os.path.isdir(raw):
        inner = _descend_single_wrapper(raw)
        if inner != raw:
            notes.append(f"the export had one wrapper folder inside it; using {inner}")
            raw = inner
    return raw, notes


# ⛔⛔ DETECT BY WHAT IS INSIDE THE FILE, NEVER BY WHAT IT IS CALLED (2026-08-09).
# The previous detector matched the literal filename `conversations-*.json` — WITH a dash, non-recursive,
# top level only. A vendor may rename its export file at any time and owes us no notice, so a filename
# check is guaranteed to rot; and it rotted invisibly here, because the one corpus it was written against
# happened to be sharded that way. **A shape check cannot rot like that: an export stops being detectable
# only when the vendor changes the actual data structure, which is the same event that would break the
# parser anyway.** Same failure family as everything else this week — the check was written against the
# single example on hand.
_CHAT_JSON_MAX_PEEK = 40


def _json_candidates(raw):
    """Every `*.json` at any depth, biggest first — the conversation dump is essentially always the
    largest JSON in an export, so the first peek usually hits."""
    if not os.path.isdir(raw):
        return []
    paths = glob.glob(os.path.join(raw, "**", "*.json"), recursive=True)
    paths = [p for p in paths if "__MACOSX" not in p and os.path.basename(p) != "_manifest.json"]
    return sorted(paths, key=lambda p: os.path.getsize(p) if os.path.exists(p) else 0, reverse=True)


def _peek_conversations(path):
    """Load a JSON export and return its conversation list, or None. Accepts a bare list OR a dict
    wrapper (`{"conversations": [...]}`) — both shapes ship in the wild."""
    try:
        if os.path.getsize(path) > 600 * 1024 * 1024:
            return None
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError, UnicodeDecodeError):
        return None
    if isinstance(data, dict):
        data = data.get("conversations") or data.get("chats") or [data]
    if not isinstance(data, list) or not data:
        return None
    return data if isinstance(data[0], dict) else None


def _classify_chat_json(path):
    """'chatgpt' | 'claude' | None — decided by the SHAPE of a conversation record.
    ChatGPT stores each conversation as a message TREE (`mapping` + `current_node`).
    Claude stores a flat LIST (`chat_messages`). That difference is the actual format."""
    convos = _peek_conversations(path)
    if not convos:
        return None
    for c in convos[:_CHAT_JSON_MAX_PEEK]:
        if not isinstance(c, dict):
            continue
        if "mapping" in c:
            return "chatgpt"
        if "chat_messages" in c:
            return "claude"
    return None


def _find_chat_export(raw, kind):
    """The first JSON in `raw` whose SHAPE is `kind`, or None."""
    for p in _json_candidates(raw)[:_CHAT_JSON_MAX_PEEK]:
        if _classify_chat_json(p) == kind:
            return p
    return None


def _is_chatgpt_export(raw):
    """A ChatGPT account export, detected by shape. Also still matches the legacy sharded
    `conversations-*.json` layout the author's own corpus uses."""
    if not os.path.isdir(raw):
        return False
    if glob.glob(os.path.join(raw, "conversations-*.json")):
        return True
    return _find_chat_export(raw, "chatgpt") is not None


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



# ══════════════════════════════════════════════════════════════════════════════════════════════════
# CLAUDE EXPORT — a second reader, added 2026-08-09 against a REAL export, not a guessed shape.
# ══════════════════════════════════════════════════════════════════════════════════════════════════
# ⭐ WHY A SECOND READER AND NOT A RENAMED DETECTOR. ChatGPT stores each conversation as a message TREE
# (`mapping` + `current_node`) and flatten.py walks it to find the branch the person actually kept.
# Claude stores a flat LIST. Different structure, so a different reader — but the OUTPUT is identical
# (role-labeled `.txt` + `_manifest.json`), which is what lets everything downstream stay untouched.
#
# MEASURED against `data-<uuid>-...-batch-0000.zip`, 2026-08-09 — a real account export:
#   conversations.json   105 MB   list of {uuid, name, summary, created_at, chat_messages:[...]}
#   design_chats/*.json           single {uuid, title, messages:[{role, content}]}
#   projects/*.json               project metadata — NOT conversations
#   users.json                    ⛔ CONTAINS email_address AND verified_phone_number
#   memories.json, login_history.json
# ⛔⛔ THAT `users.json` IS THE REASON THIS DETECTS BY SHAPE AND NEVER BY "IT IS A JSON IN THE FOLDER".
# A read-every-json walker would sweep the person's email address and phone number into the corpus on
# the very first run. Nothing here reads a file whose SHAPE is not a conversation.
_CLAUDE_ROLE = {"human": "user", "user": "user", "assistant": "assistant", "ai": "assistant"}


def _claude_message_text(msg):
    """A message's text. Prefers the flat `text`; falls back to walking `content` blocks (the newer
    shape, where `content` is a list of typed blocks and only some carry text)."""
    t = (msg.get("text") or "").strip()
    if t:
        return t
    c = msg.get("content")
    if isinstance(c, dict):
        c = [c]
    if isinstance(c, list):
        parts = [b.get("text", "") for b in c if isinstance(b, dict) and b.get("text")]
        return "\n\n".join(p for p in parts if p.strip()).strip()
    return c.strip() if isinstance(c, str) else ""


def _claude_conversations(obj):
    """Normalise either Claude shape into [(title, id, created, updated, [(role, text), ...])].
    Accepts the `chat_messages`/`sender` shape AND the `messages`/`role` shape."""
    out = []
    for c in (obj if isinstance(obj, list) else [obj]):
        if not isinstance(c, dict):
            continue
        msgs = c.get("chat_messages")
        key = "sender"
        if msgs is None:
            msgs = c.get("messages")
            key = "role"
        if not isinstance(msgs, list):
            continue
        turns = []
        for m in msgs:
            if not isinstance(m, dict):
                continue
            role = _CLAUDE_ROLE.get(str(m.get(key, "")).lower())
            text = _claude_message_text(m)
            if role and text:
                turns.append((role, text))
        if turns:
            out.append((c.get("name") or c.get("title") or "untitled",
                        c.get("uuid") or "", c.get("created_at") or "", c.get("updated_at") or "", turns))
    return out


def _is_claude_export(raw):
    """A Claude account export, detected by shape anywhere in the tree."""
    return os.path.isdir(raw) and _find_chat_export(raw, "claude") is not None


def _convert_claude_export(raw_dir, out_dir):
    """EVERY conversation-shaped JSON in the tree -> one role-labeled `.txt` each.

    ⭐ FOLDER-STRUCTURE INDEPENDENT, BY REQUIREMENT (the author, 2026-08-09): "it needs to be able to read
    just about anything that comes its way -- it shouldn't be folder-structure dependent... as long as
    it's in the file formats we agreed on, folder structure shouldn't stop us." So this walks the WHOLE
    tree and takes every file whose SHAPE is a conversation, wherever it sits. `conversations.json` and
    `design_chats/*.json` both come in; `users.json` and `projects/*.json` are skipped because they are
    not that shape -- not because of where they live or what they are called."""
    os.makedirs(out_dir, exist_ok=True)
    manifest, written, seen, skipped = {}, 0, set(), 0
    # ⛔⛔ THE DENOMINATOR COMES FROM THE SOURCE, NEVER FROM THE CONVERTER'S OWN RESULT (2026-08-09).
    # Measured on a real export: 141 conversations carried messages and 122 came out. The 19 difference
    # was CORRECT -- those conversations hold 265 messages with empty `text` AND empty `content`, so there
    # is genuinely nothing to read -- but the run reported only "122 written" and the gap was invisible.
    # That is the same failure that shipped `converted 1 of 1` from a 24-note vault: the count was taken
    # from what came out instead of from what went in. Counting both is what makes the number falsifiable.
    src_total = src_empty = 0
    for path in _json_candidates(raw_dir):
        if _classify_chat_json(path) != "claude":
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                obj = json.load(fh)
        except (OSError, ValueError, UnicodeDecodeError):
            skipped += 1
            continue
        for _c in (obj if isinstance(obj, list) else [obj]):
            if isinstance(_c, dict) and (_c.get("chat_messages") or _c.get("messages")):
                src_total += 1
        for title, cid, created, updated, turns in _claude_conversations(obj):
            short = (cid or "").replace("-", "")[:8] or f"c{written:05d}"
            slug = re.sub(r"[^a-z0-9]+", "-", (title or "untitled").lower()).strip("-")[:60] or "untitled"
            name = f"{short}-{slug}.txt"
            while name in seen:
                name = f"{short}-{len(seen)}-{slug}.txt"
            seen.add(name)
            body = [f"# {title}", f"# conversation_id: {cid}",
                    f"# created: {created} · updated: {updated}", f"# turns: {len(turns)}", ""]
            for role, text in turns:
                body += [f"## {role}", text, ""]
            with open(os.path.join(out_dir, name), "w", encoding="utf-8") as fh:
                fh.write("\n".join(body))
            manifest[cid or name] = {"file": name, "title": title, "msg_count": len(turns),
                                     "chars": sum(len(t) for _r, t in turns),
                                     "created": created, "updated": updated}
            written += 1
    src_empty = max(0, src_total - written)
    with open(os.path.join(out_dir, "_manifest.json"), "w", encoding="utf-8") as fh:
        json.dump({"format": "claude-export",
                   "conversations_in_source": src_total,
                   "conversations_written": written,
                   "skipped_no_readable_text": src_empty,
                   "unreadable_files": skipped, "rows": manifest}, fh, indent=2)
    print(f"  claude-export: {written} of {src_total} conversation(s) written"
          + (f"; {src_empty} held no readable text (images or attachments only) and were skipped"
             if src_empty else "")
          + (f"; {skipped} file(s) unreadable" if skipped else ""))


FORMATS = [
    ("chatgpt-export (conversation JSON with a `mapping` tree, at any depth)", _is_chatgpt_export, _run_flatten_py),
    ("claude-export (conversation JSON with `chat_messages`/`messages`, at any depth)", _is_claude_export, _convert_claude_export),
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

    # RESOLVE FIRST — unwrap the container before any detector sees it. A person hands over whatever
    # their vendor gave them; both ChatGPT and Claude give a `.zip`, usually with a wrapper folder
    # inside. See resolve_input's comment block for why this is separate from detection.
    try:
        raw, notes = resolve_input(args.raw, args.out)
    except (ValueError, OSError) as exc:
        print(f"ERROR: could not open '{args.raw}': {exc}", file=sys.stderr)
        return 2
    for note in notes:
        print(f"  {note}")
    args.raw = raw

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

    # ⛔ THE REFUSAL MUST DESCRIBE WHAT IT ACTUALLY SAW (2026-08-09). The old message named only the
    # supported formats, which tells a non-technical person nothing about THEIR folder and leaves them
    # with no next move. A no-outcome member that cannot be acted on is only half a seam.
    print(f"UNRECOGNISED-FORMAT: '{args.raw}' does not match any supported input format.", file=sys.stderr)
    if os.path.isdir(args.raw):
        from collections import Counter
        found = Counter()
        for root, dirs, files in os.walk(args.raw):
            dirs[:] = [d for d in dirs if not d.startswith((".", "__MACOSX"))]
            for fn in files:
                found[os.path.splitext(fn)[1].lower() or "(no extension)"] += 1
        if found:
            summary = ", ".join(f"{n}x {ext}" for ext, n in found.most_common(6))
            print(f"  What I actually found in there: {summary}.", file=sys.stderr)
            jsons = _json_candidates(args.raw)[:3]
            if jsons:
                print("  I opened the JSON files and none of them held conversations in a shape I know:",
                      file=sys.stderr)
                for p in jsons:
                    print(f"      {os.path.relpath(p, args.raw)}", file=sys.stderr)
        else:
            print("  That folder is empty.", file=sys.stderr)
    elif os.path.isfile(args.raw):
        print(f"  That is a single file ({os.path.splitext(args.raw)[1] or 'no extension'}), "
              f"not one of the shapes below.", file=sys.stderr)
    else:
        print("  That path does not exist — check for a typo, or drag the folder into the chat "
              "so the path is filled in for you.", file=sys.stderr)
    print("\n  What I CAN read:", file=sys.stderr)
    for name, _d, _c in FORMATS:
        print(f"      - {name}", file=sys.stderr)
    print("\n  A .zip is fine — I unpack it myself. Folder layout does not matter; I look inside the\n"
          "  files, not at where they sit. Never guessing a parser: a wrong guess would quietly mangle\n"
          "  your material, which is worse than stopping here.", file=sys.stderr)
    return 2


def main():
    ap = argparse.ArgumentParser(description="PHASE 1 intake dispatcher — flatten, by format fork")
    sub = ap.add_subparsers(dest="mode", required=True)
    f = sub.add_parser("flatten", help="detect the raw input's format and flatten it")
    f.add_argument("--raw", required=True, help="the corpus: a .zip, a directory (any layout), "
                   "or a single large-document file")
    f.add_argument("--out", required=True, help="flatten output dir (the FLAT dir)")
    args = ap.parse_args()
    sys.exit({"flatten": do_flatten}[args.mode](args))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
gate_and_pack.py — the CONTROLLER stage of the bulk world-model ingestion.

Sits between `flatten.py` (raw ChatGPT JSON → clean per-chat text) and the tool-less
`ingest-reader` subagent. For every flattened conversation it:

  1. runs `shared/gate/ingest_gate.py gate(desk, "file", text)` — the ONE on-path
     sanitize → injection-scan → Sentinel-route entry point. (source_type="file".)
  2. DANGER (`passed=False`) → the item is ALREADY contained by Sentinel; we log it to
     the quarantine manifest and SKIP — never spawn a reader on it.
  3. CLEAN/FLAG (`passed=True`) → take `result["content"]` (the sanitized text) and
     bin-pack survivors into reader-sized SCRATCH BUNDLES.

Packing (adopts the sentinel wiring's batch pattern — reader runs on haiku):
  - a bundle holds ≤ MAX_FILES conversations AND ≤ ~MAX_CHARS of body (whichever first);
  - a conversation bigger than MAX_CHARS becomes its OWN bundle, CHUNKED at turn ("## ")
    boundaries so no chunk blows the reader's context and the thread is never split
    mid-turn (net-new F0.1 piece — the wrapper otherwise carries content whole).

Output (to --out scratch dir):
  bundle-NNN.txt        — one or more sanitized chats, each under a parseable delimiter.
  spawn_manifest.json   — [{bundle, provenance_tags, contains:[...] }] — the actor reads
                          this and spawns ONE `ingest-reader` (model: haiku) per bundle.
  quarantine.json       — the DANGER skips (provenance tags only; NO content).

This is the CONTROLLER: it holds the tools and orchestrates, but it NEVER hands a raw
untrusted body to an LLM — the reader (eyes, no hands) does that, on the sanitized bundle.

Usage:
  python3 gate_and_pack.py --in <flatten-out-dir> --out <scratch-dir> --desk cowork-ingest
                           [--limit N] [--files f1.txt f2.txt ...]
"""
import argparse, glob, json, os, sys

# Import the frozen on-path gate (shared/gate/ingest_gate.py).
# This file lives at ROOT/system/tools/cowork-ingest/ — 4 dirnames up reaches the clone root.
# ⚠ THIS ARITHMETIC IS THE FRAGILE PART. Moving EITHER file changes it, and a wrong count fails at
# import time with a bare ModuleNotFoundError that says nothing about which side moved.
CODE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
_SHARED = os.path.join(CODE_ROOT, "shared", "gate")
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)
from ingest_gate import gate   # noqa: E402
# the SCAN rung's char-slice — imported so the slice is cut AFTER the gate, from SANITIZED text
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from tag import adaptive_char_slice, giant_sample   # noqa: E402

MAX_FILES = 10        # ≤10 conversations per reader spawn
MAX_CHARS = 10_000    # ~8–10k chars body per spawn (bin-pack cap)

DELIM = "\n===== ITEM: {name} =====\n"   # per-item marker inside a bundle (actor-parseable)


def split_turns(text):
    """Split a flattened chat into (header, [turn_blocks]). A turn starts at a '## ' line.
    Used only when a single chat exceeds MAX_CHARS and must be chunked."""
    lines = text.splitlines(keepends=True)
    header, i = [], 0
    while i < len(lines) and not lines[i].startswith("## "):
        header.append(lines[i]); i += 1
    turns, cur = [], []
    for line in lines[i:]:
        if line.startswith("## ") and cur:
            turns.append("".join(cur)); cur = []
        cur.append(line)
    if cur:
        turns.append("".join(cur))
    if not turns:
        # WAS (until 2026-08-18): "The sanitizer in gate() collapses newlines, so '## ' turn
        # markers are no longer at line-start on CLEANED text → zero turns found." That was
        # the D4 bug (issue #77), and it is FIXED — main() now gates with preserve_structure=True,
        # so the markers are at line-start and turns are found. This branch stays as the safety
        # net it should always have been: a chat that genuinely has no "## " turns must never be
        # dropped — hand the whole body back as one turn so chunk_large hard-slices it at MAX_CHARS.
        return "", ["".join(header)]
    return "".join(header), turns


def chunk_large(name, text):
    """A single chat > MAX_CHARS → list of (chunk_name, chunk_text), split at turn boundaries.
    A single turn that alone exceeds MAX_CHARS is hard-sliced (rare; keeps the invariant)."""
    header, turns = split_turns(text)
    chunks, cur, cur_len = [], [], 0
    for t in turns:
        if cur and cur_len + len(t) > MAX_CHARS:
            chunks.append("".join(cur)); cur, cur_len = [], 0
        if len(t) > MAX_CHARS:                     # one giant turn → hard-slice
            for j in range(0, len(t), MAX_CHARS):
                chunks.append(t[j:j + MAX_CHARS])
            continue
        cur.append(t); cur_len += len(t)
    if cur:
        chunks.append("".join(cur))
    n = len(chunks) or 1
    return [(f"{name}#chunk{k+1}of{n}", f"{header}\n[chunk {k+1}/{n}]\n{c}")
            for k, c in enumerate(chunks)]


def main():
    global MAX_FILES, MAX_CHARS
    ap = argparse.ArgumentParser(description="Controller: gate + pack flattened chats into reader bundles")
    ap.add_argument("--in", dest="indir", required=True, help="flatten.py output dir")
    ap.add_argument("--out", required=True, help="scratch dir for bundles + manifests")
    ap.add_argument("--desk", default="cowork-ingest", help="desk_id for gate provenance")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--files", nargs="+", default=None, help="specific flattened files (else all)")
    ap.add_argument("--max-files", type=int, default=MAX_FILES, help="max items per bundle (raise for the 5k tag pass)")
    ap.add_argument("--max-chars", type=int, default=MAX_CHARS, help="max chars per bundle")
    ap.add_argument("--slice", choices=["none", "adaptive", "giant"], default="none",
                    help="none = the full sanitized body (the DEEP-READ whole-read rung). adaptive = a "
                         "length-adaptive SCAN slice. giant = a head+tail GIANT_COVER sample for a keeper "
                         "over the whole-read ceiling. EVERY slice is cut AFTER the gate, from SANITIZED "
                         "text, so an injection buried in the dropped middle was still scanned on the full body.")
    args = ap.parse_args()
    MAX_FILES, MAX_CHARS = args.max_files, args.max_chars

    if args.files:
        paths = [f if os.path.isabs(f) else os.path.join(args.indir, f) for f in args.files]
    else:
        paths = sorted(glob.glob(os.path.join(args.indir, "*.txt")))
    if args.limit:
        paths = paths[:args.limit]
    if not paths:
        print(f"ERROR: no .txt under {args.indir}", file=sys.stderr); sys.exit(1)

    os.makedirs(args.out, exist_ok=True)
    survivors, quarantined, oversized = [], [], []   # survivors: (name, clean_text, tag)

    for p in paths:
        name = os.path.basename(p)
        with open(p) as fh:
            text = fh.read()
        # preserve_structure=True (issue #77 / D4): `text` is a WHOLE flattened chat and we
        # consume res["content"] as a document. The gate's FIELD-mode default deleted every
        # newline in it — see split_turns() below, which grew a "never drop the chat" fallback
        # precisely because the "## " turn markers were no longer at line-start afterwards.
        # Verdict behaviour is unchanged; only the returned content keeps its lines.
        res = gate(args.desk, "file", text, item=name, preserve_structure=True)
        if not res["passed"]:                        # DANGER — already contained by Sentinel
            quarantined.append({"file": name, "provenance_tag": res["provenance_tag"]})
            continue
        clean = res["content"]
        if args.slice == "adaptive":                 # SCAN rung: slice the SANITIZED body (gate already ran)
            clean = adaptive_char_slice(clean)        # → small, bounded; no chat is ever "oversized" now
        elif args.slice == "giant":                  # DEEP-READ giant rung: head+tail sample of the SANITIZED body
            clean = giant_sample(clean)               # 30% cover; the gate already ran on the FULL body
        if len(clean) > MAX_CHARS:                   # giant chat → its own chunked bundle set
            oversized.append((name, clean, res["provenance_tag"]))
        else:
            survivors.append((name, clean, res["provenance_tag"]))

    bundles, bi = [], 0

    def flush(items):
        nonlocal bi
        bpath = os.path.join(args.out, f"bundle-{bi:03d}.txt")
        with open(bpath, "w") as fh:
            for nm, tx, _tag in items:
                fh.write(DELIM.format(name=nm)); fh.write(tx.rstrip() + "\n")
        bundles.append({"bundle": os.path.basename(bpath),
                        "contains": [nm for nm, _t, _g in items],
                        "provenance_tags": [g for _n, _t, g in items]})
        bi += 1

    # Bin-pack the normal-sized survivors (≤MAX_FILES AND ≤MAX_CHARS per bundle).
    cur, cur_len = [], 0
    for item in survivors:
        _nm, tx, _tag = item
        if cur and (len(cur) >= MAX_FILES or cur_len + len(tx) > MAX_CHARS):
            flush(cur); cur, cur_len = [], 0
        cur.append(item); cur_len += len(tx)
    if cur:
        flush(cur)

    # Each oversized chat → its own bundle set, chunked at turn boundaries.
    for nm, tx, tag in oversized:
        for cname, ctext in chunk_large(nm, tx):
            flush([(cname, ctext, tag)])

    with open(os.path.join(args.out, "spawn_manifest.json"), "w") as fh:
        json.dump({"desk": args.desk, "bundle_count": len(bundles),
                   "reader": "ingest-reader", "model": "haiku", "bundles": bundles}, fh, indent=2)
    with open(os.path.join(args.out, "quarantine.json"), "w") as fh:
        json.dump({"count": len(quarantined), "items": quarantined}, fh, indent=2)

    print(f"OK: gated {len(paths)} chats → {len(bundles)} reader bundles "
          f"({len(survivors)} packed, {len(oversized)} oversized/chunked, {len(quarantined)} QUARANTINED)")
    print(f"  spawn_manifest.json + quarantine.json → {args.out}")


if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "system", "tools")))
    from utf8_stdio import force_utf8_stdio
    force_utf8_stdio()
    main()

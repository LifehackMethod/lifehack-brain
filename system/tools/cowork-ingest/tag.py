#!/usr/bin/env python3
"""
tag.py — the 5k RUNG of the altitude funnel: THIN-SLICE + TAG.

The 5k pass reads a *thin slice* of each chat (its subject + how it ended) — NOT the
whole thing — and tags it with the output categories + a freshness flag. That tagged
table feeds a richer heat map and the HUMAN GATE. (10k = `score.py` structure; 1k =
the deep read in F2.2.)

This file owns the DETERMINISTIC halves; the LLM judgment (assigning tags) is a separate
tool-less tagging pass over the gate-sanitized slices (security: reader/actor discipline).

Modes:
  slice     — read flattened per-chat `.txt` (from flatten.py) and emit ONE thin-slice
              file per chat: the header + first user turn + last assistant turn, each
              capped. Small on purpose, so the reader can bin-pack many per spawn.
  validate  — read the tagging pass's raw output + the closed category vocab, and KEEP
              only tags in the vocab (sanitizes the tagger's output — closes the
              memory-poisoning hole: a tag not in the fixed set is dropped, never stored).

The 11 OUTPUT CATEGORIES (GATE-2 taxonomy — the closed vocab the tagger must choose from):
  canon · historical-record · anti-pattern · sop · operating-profile · people ·
  decision · resources · assets-troubleshooting · open-question · exploration
Plus freshness ∈ {fresh, stale, unknown}. (Goals route to the Life Map, not a tag.)
NOTE: `exploration` (thought-experiment / researched-but-not-adopted) exists to stop the
tagger converting a thing merely RESEARCHED into an asserted fact/habit/possession.

Usage:
  python3 tag.py slice    --in <flatten-dir> --out <slice-dir> [--limit N] [--cap 800]
  python3 tag.py validate --tags <raw-tags.json> --out <clean-tags.json>
"""
import argparse, glob, json, os, sys

CATEGORIES = {
    "canon", "historical-record", "anti-pattern", "sop", "operating-profile",
    "people", "decision", "resources", "assets-troubleshooting", "open-question",
    "exploration",
}
FRESHNESS = {"fresh", "stale", "unknown"}


def split_header_turns(text):
    """Flattened file → (header_lines, [(role, body)]). Mirrors flatten.py's shape."""
    lines = text.splitlines()
    header, i = [], 0
    while i < len(lines) and not lines[i].startswith("## "):
        if lines[i].strip():
            header.append(lines[i])
        i += 1
    turns, role, buf = [], None, []
    for line in lines[i:]:
        if line.startswith("## "):
            if role is not None:
                turns.append((role, "\n".join(buf).strip()))
            role, buf = line[3:].strip(), []
        else:
            buf.append(line)
    if role is not None:
        turns.append((role, "\n".join(buf).strip()))
    return header, turns


def thin_slice(text, cap, first_n=3, last_n=3):
    """Header + FIRST `first_n` turns + LAST `last_n` turns, role-labeled, each capped.
    Generous by design (slicing is ~free): the opening frames the subject, the tail shows
    how it landed. Middle is elided (that's the deep read's job). Short chats → all turns."""
    header, turns = split_header_turns(text)
    out = list(header)
    out.append(f"# turns_total: {len(turns)}")
    out.append("")
    if len(turns) <= first_n + last_n:
        head, mid, tail = turns, [], []
    else:
        head, mid, tail = turns[:first_n], turns[first_n:-last_n], turns[-last_n:]
    out.append("## OPENING")
    for r, b in head:
        out.append(f"[{r}] {(b or '(empty)')[:cap]}")
    if mid:
        out.append("")
        out.append(f"## … [{len(mid)} middle turns elided] …")
    if tail:
        out.append("")
        out.append("## CLOSING")
        for r, b in tail:
            out.append(f"[{r}] {(b or '(empty)')[:cap]}")
    return "\n".join(out)


# ── adaptive CHAR-window slice (the SCAN rung) — operates on GATE-SANITIZED text ──────────────
# WHY char windows, not turns: gate() collapses newlines, so the "## " turn markers are gone from
# sanitized content — there is nothing to split on. A dumb char cut is both correct here AND enough
# for a gist (the human only needs to recognize the chat, not read it). Thresholds + caps are CODE
# CONSTANTS on a DETERMINISTIC input (length) — never LLM-language (a slice rule the model interprets
# at runtime is nondeterminism + uncontrolled size on every one of ~1,500 calls). See council 2026-07-11.
SCAN_WHOLE_MAX = 2500    # ≤ this many chars → send the whole (sanitized) chat
SCAN_MED_MAX   = 8000    # ≤ this → beginning + end windows; above → beginning + middle + end
SCAN_WIN       = 3000    # per-window char budget (begin / middle / end) — raised 2026-07-11 so the reader
                         # actually understands big chats (a 220k-char Dominium chat was seeing only 2%)
SCAN_TOTAL_CAP = 10000   # HARD ceiling on the packed slice (~2.5k tok) — bigger than before ON PURPOSE:
                         # SCAN quality is worth the tokens (the summary is what the human rules on)


def adaptive_char_slice(text, whole_max=SCAN_WHOLE_MAX, med_max=SCAN_MED_MAX,
                        win=SCAN_WIN, total_cap=SCAN_TOTAL_CAP):
    """Length-adaptive char slice for SCAN, applied to GATE-SANITIZED content.
      short  (len ≤ whole_max) → the whole chat
      medium (len ≤ med_max)   → first `win` chars + last `win` chars
      long   (len >  med_max)  → first `win` + a middle `win` + last `win`
    Always truncated to total_cap. Pure function; thresholds are constants, not a prompt.
    NOTE on `total_cap` vs `win`: for a medium/long chat the assembled slice tops out around
    `2*win`/`3*win` (plus small elision markers) — `total_cap` only bites if it's SMALLER than that.
    SCAN_TOTAL_CAP (10000) sits above SCAN_WIN's natural ceiling (~9000) on purpose, as a hard safety
    backstop, not the thing actually shaping the slice. So a caller that wants a MATERIALLY bigger
    slice (the EXPLORE re-read, below) must raise `win` too — raising `total_cap` alone against the
    default `win` is a no-op for any chat past `med_max`. See `explore_char_slice`."""
    t = (text or "").strip()
    n = len(t)
    if n <= whole_max:
        out = t
    elif n <= med_max:
        out = t[:win] + "\n… [middle elided] …\n" + t[-win:]
    else:
        mid = (n - win) // 2
        out = (t[:win] + "\n… [gap] …\n" + t[mid:mid + win] + "\n… [gap] …\n" + t[-win:])
    return out[:total_cap]


# ── the EXPLORE re-read (SCAN's non-terminal third verdict, SPEC §8 step 2.9) ──────────────────
# Same code path as SCAN (adaptive_char_slice), a WIDER cap. Independently tunable from SCAN_* on
# purpose — the two rungs must never be forced to move together just because one file defines both.
# Do NOT reach for giant_sample/GIANT_COVER below — that is the DEEP-READ giant-handling lever, a
# different rung entirely, and its 0.30 fraction is an unproven research figure. This is its own knob.
# EXPLORE_WIN moves along with EXPLORE_TOTAL_CAP (not just the cap alone) because — per the note on
# `adaptive_char_slice` above — `win` is what actually bounds a medium/long chat's slice length; a
# wider cap with the same win=3000 default would render byte-for-byte identical output. ~3x SCAN's
# window: enough to make the widened re-read obviously, measurably bigger without ballooning token
# cost on every EXPLORE chat.
EXPLORE_WIN       = 9000    # per-window char budget for the EXPLORE re-read (vs SCAN_WIN=3000)
EXPLORE_TOTAL_CAP = 28000   # HARD ceiling on the packed EXPLORE slice (vs SCAN_TOTAL_CAP=10000) —
                            # ~3 wide windows' worth, same margin-above-natural-ceiling relationship
                            # SCAN_TOTAL_CAP has to SCAN_WIN


def explore_char_slice(text, whole_max=SCAN_WHOLE_MAX, med_max=SCAN_MED_MAX,
                       win=EXPLORE_WIN, total_cap=EXPLORE_TOTAL_CAP):
    """The EXPLORE re-read's slice — the SAME adaptive_char_slice path (still GATE-SANITIZED input,
    still fed to a TOOL-LESS reader; widening the slice does not widen the attack surface), just wider
    windows + a separate, independently-tunable cap so a chat the human could not judge from the SCAN
    gist comes back with MATERIALLY more of it, not a longer version of the same thin blurb (the author,
    2026-08-05: "a paragraph ... that covers the breadth of the arc of the whole session"). The reader
    prompt itself (asking for 8–12 sentences instead of SCAN's 2–3) is NOT in this file — it lives in
    `skills/ingest/phases/2-scan.md` (~line 67), owned by another lane; update it there, not here.
    `whole_max`/`med_max` are left at SCAN's values on purpose: they classify the INCOMING chat's own
    size tier (short/medium/long), which doesn't change between rounds — only how much of it a reader
    gets to see does."""
    return adaptive_char_slice(text, whole_max=whole_max, med_max=med_max, win=win, total_cap=total_cap)


# ── GIANT sample (the DEEP-READ rung, for a keeper OVER the whole-read ceiling) ────────────────
# The 2026-07-12 read-strategy rewrite: a keeper ≤ DEEP_WHOLE_MAX (~100k chars) is read WHOLE. A rare GIANT
# above it can't be read whole without pushing the reader into the skim zone, so it's SAMPLED head+tail and
# FLAGGED for the human (never filed silently). This is the ONE surviving slice path — and, like the SCAN
# slice, it operates on GATE-SANITIZED text (gate_and_pack runs gate() first, so an injection buried in the
# dropped middle was still scanned on the full body). GIANT_COVER is deliberately GENEROUS (start crude, tune
# DOWN on real giants — over-covering a rare giant is cheap; under-covering could poison canon). ONE constant.
GIANT_COVER = 0.30       # fraction of a giant to read: half at the head, half at the tail


def giant_sample(text, cover=GIANT_COVER):
    """Head+tail sample of a GIANT (over the whole-read ceiling), applied to GATE-SANITIZED content. Takes
    `cover` of the body — half from the front (the framing/subject) and half from the end (where a chat lands
    its conclusion, per the head+tail-wins-for-classification finding) — with the middle explicitly elided so
    the reader (and the human) can SEE it was sampled, not read whole. Deterministic: the fraction is a code
    constant on a length input, never an LLM judgment. A body already ≤ the sample size is returned whole."""
    t = (text or "").strip()
    n = len(t)
    half = max(1, int(n * cover / 2))
    if 2 * half >= n:
        return t                                        # small enough that the sample ≈ the whole body
    elided = n - 2 * half
    return (t[:half]
            + f"\n… [{elided:,} chars in the MIDDLE were NOT read — this giant was SAMPLED, not read whole] …\n"
            + t[-half:])


def do_slice(args):
    paths = sorted(glob.glob(os.path.join(args.indir, "*.txt")))
    if args.limit:
        paths = paths[:args.limit]
    if not paths:
        print(f"ERROR: no .txt under {args.indir}", file=sys.stderr); sys.exit(1)
    os.makedirs(args.out, exist_ok=True)
    n, total_chars = 0, 0
    for p in paths:
        name = os.path.basename(p)
        with open(p) as fh:
            sl = thin_slice(fh.read(), args.cap, args.first, args.last)
        with open(os.path.join(args.out, name), "w") as fh:
            fh.write(sl)
        n += 1; total_chars += len(sl)
    print(f"OK: sliced {n} chats → {args.out} (avg {total_chars // max(n,1)} chars/slice, "
          f"~{total_chars // 4:,} tokens total — ~{total_chars // max(n,1) // 4} tok/slice)")


def do_validate(args):
    raw = json.load(open(args.tags))
    rows = raw if isinstance(raw, list) else raw.get("rows", [])
    clean, dropped = [], 0
    for r in rows:
        cats = [c for c in (r.get("categories") or []) if c in CATEGORIES]
        dropped += len(r.get("categories") or []) - len(cats)
        fresh = r.get("freshness") if r.get("freshness") in FRESHNESS else "unknown"
        clean.append({"conversation_id": r.get("conversation_id"), "file": r.get("file"),
                      "categories": cats, "freshness": fresh})
    json.dump({"count": len(clean), "dropped_out_of_vocab": dropped, "rows": clean},
              open(args.out, "w"), indent=2)
    print(f"OK: validated {len(clean)} tag rows; dropped {dropped} out-of-vocab tags → {args.out}")


def extract_json_array(text):
    """Robustly pull the JSON array out of an agent reply that may carry a prose preamble
    ('Classifying each…') or a markdown fence. Falls back to first-'['..last-']' slice."""
    text = (text or "").strip()
    for candidate in (text, text[text.find("["): text.rfind("]") + 1] if "[" in text and "]" in text else ""):
        try:
            v = json.loads(candidate)
            if isinstance(v, list):
                return v
        except Exception:
            continue
    return []


def do_collect(args):
    """Merge many raw tagger-output files (each a JSON array, maybe prose-prefixed) into one
    validated tags file. Drops any category outside the closed vocab (output sanitization) and
    coerces freshness to the closed set — so a hijacked tagger can't inject a novel label."""
    files = sorted(glob.glob(os.path.join(args.raw, "*")))
    rows, dropped, parsed, unparseable = [], 0, 0, 0
    for f in files:
        if not os.path.isfile(f):
            continue
        arr = extract_json_array(open(f).read())
        if not arr:
            unparseable += 1
            continue
        parsed += 1
        for r in arr:
            if not isinstance(r, dict):
                continue
            cats = [c for c in (r.get("categories") or []) if c in CATEGORIES]
            dropped += len(r.get("categories") or []) - len(cats)
            fresh = r.get("freshness") if r.get("freshness") in FRESHNESS else "unknown"
            rows.append({"file": r.get("file"), "conversation_id": r.get("conversation_id"),
                         "categories": cats, "freshness": fresh, "why": (r.get("why") or "")[:160]})
    json.dump({"count": len(rows), "raw_files": len(files), "parsed_files": parsed,
               "unparseable_files": unparseable, "dropped_out_of_vocab": dropped, "rows": rows},
              open(args.out, "w"), indent=2)
    print(f"OK: collected {len(rows)} tag rows from {parsed} files "
          f"({unparseable} unparseable, {dropped} out-of-vocab dropped) → {args.out}")


def main():
    ap = argparse.ArgumentParser(description="5k rung — thin-slice + tag")
    sub = ap.add_subparsers(dest="mode", required=True)
    s = sub.add_parser("slice"); s.add_argument("--in", dest="indir", required=True)
    s.add_argument("--out", required=True); s.add_argument("--limit", type=int, default=None)
    s.add_argument("--cap", type=int, default=1000)
    s.add_argument("--first", type=int, default=3); s.add_argument("--last", type=int, default=3)
    v = sub.add_parser("validate"); v.add_argument("--tags", required=True); v.add_argument("--out", required=True)
    c = sub.add_parser("collect"); c.add_argument("--raw", required=True, help="dir of raw tagger-output files")
    c.add_argument("--out", required=True)
    args = ap.parse_args()
    {"slice": do_slice, "validate": do_validate, "collect": do_collect}[args.mode](args)


if __name__ == "__main__":
    main()

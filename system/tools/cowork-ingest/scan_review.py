#!/usr/bin/env python3
"""
scan_review.py — the TOOL-PRINTED ruling view for the SCAN rung (the SCAN twin of conclusions_review.py).

The flaw this closes (ruled 2026-07-11, auditing a live creative-writing SCAN): when the CONTROLLER
hand-assembles the SCAN list, it COMPRESSES — it re-groups the chats into guess-piles (so the numbers
jump 1→8→9), squishes each summary to a cryptic fragment, and never tells the first-time user what to
type. Same failure family as the deep-read confirm (SOP Principle 17): prose drifts, a TOOL doesn't.

So the SCAN ruling view is PRINTED BY THIS TOOL and the phase merely RELAYS it. What it guarantees:
  * EVERY scanned-but-unruled chat in the basket is printed as a numbered, rulable row — in stable
    SEQUENTIAL order 1..N (never re-grouped), so "toss 8, park 14" maps cleanly.
  * The FULL multi-sentence gist is shown (never truncated here) — the detail floor the human asked for.
  * NEVER the ChatGPT-assigned title (SPEC §8 step 2.6 — "the title is never good when it comes to
    ChatGPT"; the auto-name misleads more than it helps).
  * Each row carries the machine's GUESS (research / toss / park) as a starting rec the human overrides.
  * The chat's SIZE, when the corpus map actually carries one for this row (see `_row_size_label` — the
    schema has carried a `chars` field since 2026-08-05, stamped by SCAN from the flattened file on disk;
    a pre-existing row written before that date simply omits it, and this renders nothing rather than a
    fabricated number; see that function's docstring).
  * All THREE verdicts — KEEP / TOSS / EXPLORE — spelled out on screen with one line each on what they
    mean (`VERDICTS`, the single source of truth), letters FIXED so "1a, 2b, 3c" always resolves the same
    way regardless of which item it answers (prescriptive: "anything the human can feedback on
    should be numbered … so the human can just easily say 1a, 2b, 3c" — the human is DICTATING, so an
    unnumbered option forces them to restate it aloud every time).
  * A plain header ("where we are") + a plain footer that TELLS a non-technical user exactly what to type.
  * Paginated: NO FEWER THAN 10 rows/page (default ~15) — high counts are welcome, detail is not sacrificed.

Deterministic bookkeeping over the corpus map's already-gated `scan_summary`/`scan_guess`. Reads no raw
chat content and spawns nothing.

Usage:
  python3 scan_review.py show --map <corpus-map.json> --basket <B> [--page N] [--page-size K]
"""
import argparse, os, sys, textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import pipeline

FLOOR = 10          # never fewer than this per page (unless the basket has fewer left)
DEFAULT_PAGE = 15   # aim ~15 — enough detail per chat without a wall
W = 60              # render width (matches pipeline._DW)


# ── THE VERDICT SET — single source of truth (SPEC §8 "THE VERDICT SET") ──────────────────────────
# Three verdicts. KEEP/TOSS are terminal; EXPLORE is NOT — it stays in this phase and the chat comes
# back next round with a materially wider re-read (tag.py's EXPLORE_TOTAL_CAP), never a longer version
# of the same thin blurb. Letters are FIXED (a/b/c) across every row on every page, so a dictated
# "1a, 2b, 3c" always means the same verdict no matter which item it is attached to — the human never
# has to look the letter back up per row. Accepting "explore" as a skim_verdict is another lane's change
# to pipeline.py; this file only renders the option, never writes it.
VERDICTS = [
    ("a", "KEEP",
     "100% a high-value deep-read target — we're going to find a ton in here."),
    ("b", "TOSS",
     "100% certain there's nothing valuable in here."),
    ("c", "EXPLORE",
     "I couldn't tell from what you showed me what this even was — not final, comes back "
     "with a closer look next round."),
]

# The corpus-map schema (corpus-map-schema.md) defines a `chars` column on a chat row (pipeline.py's
# CHAT_V2_DEFAULTS, added 2026-08-05) — the character length of the flattened body, stamped by SCAN from
# disk, never guessed. It is OPTIONAL-ADDITIVE: a row written before that date carries no `chars` key.
# This renderer never opens a chat body (that's the whole point of it being map-only), so it cannot
# measure a size itself either. `_row_size_label` probes a short list of plausible field names — `chars`
# now hits for any row SCAN has touched since 2026-08-05 — and for an older row without one it returns
# None, so the size clause is simply omitted rather than a guessed or estimated number.
_SIZE_KEYS = ("chars", "char_count", "char_len", "size_chars", "n_chars")


def _row_size_label(r):
    """Best-effort chat size for display, or None if this particular map row genuinely doesn't carry one
    (see the module-level note above `_SIZE_KEYS` — `chars` is a real schema field since 2026-08-05; a
    row written before that date, or never re-scanned since, is the only case that still returns None)."""
    for key in _SIZE_KEYS:
        v = r.get(key)
        if isinstance(v, (int, float)) and v > 0:
            n = int(v)
            return f"{n / 1000:.1f}k chars" if n >= 1000 else f"{n} chars"
    return None


def _verdict_legend():
    """Render VERDICTS as ≤2-line-each plain reflowed text (no box-drawing — the graphical layer was
    cut 2026-08-04). One block, reused verbatim so the vocabulary never drifts into scattered literals."""
    lines = []
    for letter, name, meaning in VERDICTS:
        prefix = f"    {letter}) {name:<8}"
        wrapped = textwrap.wrap(meaning, width=max(20, pipeline._DW - len(prefix) - 2)) or [""]
        lines.append(f"{prefix} {wrapped[0]}")
        pad = " " * len(prefix)
        for cont in wrapped[1:]:
            lines.append(f"{pad} {cont}")
    return lines


def cmd_show(a):
    """The SCAN decision screen (F1.3, rebuilt 2026-07-13; verdict set widened to KEEP/TOSS/EXPLORE +
    numbered-answer format, SPEC §8 step 2.6). Renders through the SHARED renderer (pipeline.compose_screen)
    so it's byte-identical in shape to every other screen: title + one overall %-bar → the verdict legend →
    one numbered row per chat (no title, size when known) → the ONE action last."""
    m = pipeline.load(a.map)
    rows_all = [(k, r) for k, r in pipeline.basket_chats(m, a.basket) if pipeline._scanned_unruled(r)]
    total = len(rows_all)
    basket = a.basket
    pretty = basket.replace("-", " ").title()
    emoji = pipeline._basket_emoji(basket)
    order = [k for k, _ in pipeline._basket_order(m)]
    pos = order.index(basket) + 1 if basket in order else 0
    title = f"{emoji}  {pretty.upper()}"
    title_right = f"Basket {pos} of {len(order)}"
    header = [pipeline.compose_topbar(m)]

    if total == 0:
        print(pipeline.compose_screen([f'  ✓  "{pretty}" is fully sorted — nothing left to rule here.'],
                                      pipeline.compose_action_bar("Type /ingest for the next pile →"),
                                      header_lines=header, title=title, title_right=title_right))
        return 0

    page_size = a.page_size or DEFAULT_PAGE
    if page_size < FLOOR:
        page_size = FLOOR
    npages = (total + page_size - 1) // page_size
    page = max(1, a.page)
    if page > npages:
        print(f"(page {page} doesn't exist — only {npages} page(s) for {total} chats.)")
        return 0
    start, end = (page - 1) * page_size, min(page * page_size, total)

    lead = (f'  I read these {total} chats. Rule each one — reply with the number + a letter, '
            f'e.g. "1a, 2b, 3c":' if npages == 1
            else f'  Chats {start+1}–{end} of {total}. Reply with the number + a letter, '
                 f'e.g. "1a, 2b, 3c":')
    rows = [lead, ""] + _verdict_legend() + [""]
    for i in range(start, end):
        k, r = rows_all[i]
        n = i + 1
        verb = pipeline.verb_label(r.get("scan_guess"))
        if verb in ("MINE", "—"):
            verb = "KEEP"                            # unsure/MINE → KEEP (advances; the human can still
                                                       # toss or explore) — display-only translation from
                                                       # pipeline.py's cross-screen MINE token into this
                                                       # phase's KEEP/TOSS/EXPLORE vocabulary (SPEC §8);
                                                       # pipeline.py itself is untouched.
        flagged = bool(r.get("sensitive"))
        gist = (r.get("scan_summary") or "").strip() or "(no summary — open it yourself to decide)"
        size_lbl = _row_size_label(r)
        size_part = f"  ({size_lbl})" if size_lbl else ""
        warn = " ⚠" if flagged else ""
        # ⛔ THE GIST IS REFLOWED ACROSS LINES, NEVER TRUNCATED. (Fixed 2026-08-05.)
        # This block used to end with `row[:_DW-3] + "…"`, clipping every description to ONE line — while
        # the docstring at the top of this file claimed "never truncated here." The truncating version is
        # the exact defect measured on 2026-08-04: a truncated one-line row produced a RUBBER STAMP rather
        # than a decision, and the ruling was that "a screen he must approve/deny needs AT LEAST 3
        # SENTENCES PER ROW." The whole point of this screen is that the human rules on SUBSTANCE — a
        # clipped description hands them a title by another name.
        # Reflowing (not clipping, and not hand-wrapping into a fixed-width box — the boxed layer was CUT
        # on 2026-08-04) is what lets the 2-3 sentence floor actually reach the screen.
        prefix = f'  {n:>2}  {verb:<4}{size_part}{warn} — '
        body_w = max(24, pipeline._DW - len(prefix) - 2)
        wrapped = textwrap.wrap(gist, width=body_w) or [""]
        rows.append(f"{prefix}{wrapped[0]}")
        for cont in wrapped[1:]:
            rows.append(f"{' ' * len(prefix)}{cont}")
    if end < total:
        rows.append(f"      … {total - end} more — press ENTER to see the next page …")

    action = pipeline.compose_action_bar(
        'Rule each — "1a, 2b, 3c" (a=KEEP  b=TOSS  c=EXPLORE), or "all keep"')
    print(pipeline.compose_screen(rows, action, header_lines=header, title=title, title_right=title_right))
    return 0


def main():
    ap = argparse.ArgumentParser(description="Tool-printed SCAN ruling view (the anti-compression guarantee).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("show", help="dense numbered ruling view, paginated (>=10/page, default 15)")
    s.add_argument("--map", required=True)
    s.add_argument("--basket", required=True)
    s.add_argument("--page", type=int, default=1)
    s.add_argument("--page-size", type=int, default=0, help="rows/page (floor 10; default 15)")
    s.set_defaults(func=cmd_show)
    a = ap.parse_args()
    sys.exit(a.func(a))


if __name__ == "__main__":
    main()

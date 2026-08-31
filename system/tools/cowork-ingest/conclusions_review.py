#!/usr/bin/env python3
"""
conclusions_review.py — the DENSE CONFIRM printer for the deep-read (720p) stage (P6 F6.8, 2026-07-10).

The flaw this closes (found 2026-07-10, auditing a live single-topic vein drill):
the deep-read confirm view was hand-assembled by the controller, so it could — and did — COMPRESS a
17-chat vein down to ~4 surfaced items, quietly bucketing the other ~13 into "already-filed / pointer /
junk" WITHOUT the human seeing them. Two failures in one: (1) throughput (4 shown, not the whole batch),
(2) a soft breach of "the machine never eliminates — it only orders" (SOP Principle 16) — the machine
hid chats from the human's eyes.

Prose can't fix this (an instruction to "show more" drifts). ENFORCEMENT = a TOOL that prints the batch,
so the controller relays instead of curates. This is the deep-read twin of `basket_review.py summary`.

What it guarantees:
  * EVERY chat in the fed batch is printed as a numbered, rulable row — including the ones with NO durable
    conclusion (they print as "(no durable conclusion) · guess: TOSS"), so nothing is hidden.
  * A page shows NO FEWER THAN 10 rows ("no less than 10, ideally closer to 20"); default 20.
    A page-size below the floor is clamped up; the last page may be shorter only because the batch ran out.
  * Each row carries the machine's GUESS (file / pointer-only / toss) as a suffix — a starting rec the human
    overrides, never a decision.

It is deterministic bookkeeping over ALREADY-SANITIZED conclusions JSON. It never reads raw chat content and
spawns nothing.

INPUT — the raw ingest-conclusions output, saved verbatim (one array per bundle; feed one file that is either
a single array or a list-of-arrays, OR pass several files and they are concatenated in order):
  [ {"file": "<hash>-<kebab-title>", "conclusions": [
        {"text": "...", "suggested_category": "canon", "freshness": "always", "kind": "fact", "sensitive": false}
     ], "trait": "...", "sensitive": false}, ... ]

Subcommands:
  show    --in F [F2 ...] [--page N] [--page-size K]     # dense numbered confirm view, paginated
  assert-ruled --in F [...] --map M                       # LOCK: exit non-zero if any fed chat is not yet
                                                          #   human-ruled (terminal) in the corpus map
"""
import argparse, json, os, sys, textwrap

FLOOR = 10          # never show fewer than this per page (unless the batch itself has fewer left)
DEFAULT_PAGE = 20   # aim for ~20

# categories that signal a durable, likely-file-worthy conclusion
DURABLE_CATS = {
    "canon", "operating-profile", "people", "decision",
    "historical-record", "sop", "anti-pattern", "resources", "assets-troubleshooting",
}
# terminal (human-ruled) statuses in the corpus map — mirrors wmb_commit.TERMINAL
TERMINAL = {"filed", "pointer-only", "deferred", "declined"}


def title_of(fname):
    stem = fname[:-4] if fname.endswith(".txt") else fname
    parts = stem.split("-", 1)
    return parts[1].replace("-", " ") if len(parts) == 2 else stem


def resolve_infiles(a):
    """A deep-read ends by printing THIS batch. Prefer explicit --in; else auto-discover the vein's
    raw-conclusions file from the work dir (--work or $COWORK_WORK), so the confirm is one obvious
    command (`show --vein <v>`) with nothing to forget."""
    if getattr(a, "infiles", None):
        return a.infiles
    vein = getattr(a, "vein", None)
    if not vein:
        sys.exit("FAIL: pass --in <file> OR --vein <name> (+ --work/$COWORK_WORK to locate it).")
    work = getattr(a, "work", None) or os.environ.get("COWORK_WORK")
    if not work:
        sys.exit("FAIL: --vein needs the work dir — pass --work <dir> or set $COWORK_WORK.")
    path = os.path.join(work, f"raw-conclusions-{vein}.json")
    if not os.path.exists(path):
        sys.exit(f"FAIL: no batch file for vein '{vein}' at {path}. Save the ingest-conclusions "
                 f"arrays there first (the deep-read's raw output).")
    return [path]


def load_batch(paths):
    """Load one-or-more conclusions files, each a single agent-array OR a list-of-arrays; flatten to
    one ordered list of per-chat objects."""
    out = []
    for p in paths:
        with open(p) as f:
            d = json.load(f)
        if isinstance(d, dict):
            # tolerate a wrapper like {"conclusions": [...]} or a single per-chat object
            if "file" in d and "conclusions" in d:
                out.append(d)
                continue
            d = d.get("conclusions") or d.get("items") or d.get("results") or []
        for el in d:
            if isinstance(el, list):        # a list-of-arrays (multiple bundles in one file)
                out.extend(el)
            else:
                out.append(el)
    return out


def guess_disposition(chat):
    """Deterministic starting rec the human overrides. Never writes anything."""
    cons = chat.get("conclusions") or []
    if not cons:
        return "TOSS"                       # nothing durable in the chat
    for c in cons:
        cat = (c.get("suggested_category") or "").lower()
        kind = (c.get("kind") or "").lower()
        fresh = (c.get("freshness") or "").lower()
        if cat in DURABLE_CATS and kind in {"fact", "practice", "decision"} and fresh in {"always", "unknown"}:
            return "FILE"
    return "POINTER-ONLY"                    # explored / dated / reference only


def cmd_show(a):
    """The DEEP-READ decision screen (F1.2, rebuilt 2026-07-12). Renders through the SHARED renderer
    (pipeline.compose_screen) so it's byte-consistent with every other screen: HUD header → one MINE/TOSS
    line per chat → the ONE action as the last line. The old FILE/POINTER-ONLY jargon + the buried CTA are
    gone; file-vs-pointer is a machine detail, hidden (decision-log D9). At DEEP-READ the human's choice is
    MINE (worth advancing) or TOSS — SAVE happens only at FILE."""
    import os as _os, sys as _sys
    _here = _os.path.dirname(_os.path.abspath(__file__))
    if _here not in _sys.path:
        _sys.path.insert(0, _here)
    import pipeline

    batch = load_batch(resolve_infiles(a))
    total = len(batch)
    if total == 0:
        print("Nothing to confirm — 0 chats in this batch.")
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

    # Header = a light title + ONE overall progress bar (points + % of history). NOT the per-basket grid —
    # that lives only in the pinned bottom bar (decision-log D13). The top bar is the aggregate hero-bar.
    title_right, header = "", None
    m = pipeline.load(a.map) if getattr(a, "map", None) else None
    basket = getattr(a, "basket", None) or ""
    if m is not None:
        header = [pipeline.compose_topbar(m)]
        if basket:
            order = [k for k, _ in pipeline._basket_order(m)]
            pos = order.index(basket) + 1 if basket in order else 0
            title_right = f"Basket {pos} of {len(order)}"
    pretty = (basket or "your chats").replace("-", " ").title()
    screen_title = f"{pipeline._basket_emoji(basket)}  {pretty.upper()}" if basket else "🧠  DEEP READ"

    rows = []
    pagenote = f"  I read these {total} chats. My take, MINE vs TOSS:" if npages == 1 \
        else f"  Chats {start+1}–{end} of {total}. My take, MINE vs TOSS:"
    rows.append(pagenote)
    rows.append("")
    for i in range(start, end):
        chat = batch[i]
        n = i + 1
        g = guess_disposition(chat)
        verb = "TOSS" if g == "TOSS" else "MINE"          # DEEP-READ: advance (MINE) or drop (TOSS)
        flagged = bool(chat.get("sensitive"))
        title = title_of(chat.get("file", "?")).strip().title()
        cons = chat.get("conclusions") or []
        takeaway = (cons[0].get("text", "") or "").strip() if cons else ""
        takeaway = takeaway or "(nothing durable — likely toss)"
        warn = " ⚠" if flagged else ""
        # ⛔ THE TAKEAWAY IS REFLOWED ACROSS LINES, NEVER TRUNCATED. (Fixed 2026-08-06, mirroring
        # scan_review.py's 2026-08-05 fix — same helper, same style, see that file's block comment for
        # the full incident writeup.) This block used to do `pipeline._clip(text, 60)` and THEN hard-clip
        # the whole row to `_DW - 2` with `row[:_DW-3] + "…"` — a DOUBLE truncation of the exact
        # "conclusion" the human is being asked to rule on. That is the rubber-stamp defect measured
        # 2026-08-04 on this screen's SCAN twin: a clipped description hands the human a title by another
        # name, and they end up approving text they never actually read. Reflowing (not clipping, not
        # hand-wrapping into a fixed-width box — the boxed layer was cut 2026-08-04) keeps every word;
        # it only changes where the line breaks.
        prefix = f'  {n:>2}  {verb:<4} "{title}"{warn} — '
        body_w = max(24, pipeline._DW - len(prefix) - 2)
        wrapped = textwrap.wrap(takeaway, width=body_w) or [""]
        rows.append(f"{prefix}{wrapped[0]}")
        for cont in wrapped[1:]:
            rows.append(f"{' ' * len(prefix)}{cont}")
    if end < total:
        rows.append(f"      … {total - end} more — press ENTER to see the next page …")

    bar = pipeline.compose_action_bar("deep")
    print(pipeline.compose_screen(rows, bar, header_lines=header, title=screen_title, title_right=title_right))
    return 0


def cmd_assert_ruled(a):
    """LOCK — the deep-read twin of arena-close: refuse to consider a vein reviewed while any chat the
    human was shown is still un-ruled (non-terminal) in the corpus map."""
    batch = load_batch(resolve_infiles(a))
    files = {c.get("file", "") for c in batch}
    # normalize to the .txt row-key form used by the corpus map
    keys = {f if f.endswith(".txt") else f + ".txt" for f in files if f}
    with open(a.map) as f:
        rows = json.load(f)["rows"]
    unruled = []
    for k in keys:
        row = rows.get(k)
        if row is None:
            unruled.append((k, "NOT IN MAP"))
        elif row.get("filing_status") not in TERMINAL:
            unruled.append((k, row.get("filing_status")))
    if unruled:
        print(f"LOCK FAIL: {len(unruled)} of {len(keys)} deep-read chats are NOT human-ruled yet:")
        for k, st in unruled:
            print(f"  {st:14} {k}")
        print("A vein is not reviewed until every chat you were shown has a terminal ruling "
              "(filed / pointer-only / deferred / declined). Rule them, then re-check.")
        return 1
    print(f"LOCK OK: all {len(keys)} deep-read chats are human-ruled. Vein review is complete.")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Dense confirm printer for the deep-read stage.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("show", help="the DEEP-READ decision screen (shared renderer; MINE/TOSS), paginated")
    s.add_argument("--in", dest="infiles", nargs="+", help="conclusions JSON file(s)")
    s.add_argument("--vein", help="auto-discover work/raw-conclusions-<vein>.json (with --work/$COWORK_WORK)")
    s.add_argument("--work", help="work dir holding raw-conclusions-<vein>.json (or set $COWORK_WORK)")
    s.add_argument("--map", help="corpus-map.json — renders the pinned basket HUD as the screen header")
    s.add_argument("--basket", help="the basket name (for the 'Basket N of 8' title + the ◀ marker)")
    s.add_argument("--page", type=int, default=1)
    s.add_argument("--page-size", type=int, default=0, help="rows per page (floor 10; default 20)")
    s.set_defaults(func=cmd_show)

    s = sub.add_parser("assert-ruled", help="LOCK: fail if any fed chat is not yet human-ruled in the map")
    s.add_argument("--in", dest="infiles", nargs="+")
    s.add_argument("--vein", help="auto-discover work/raw-conclusions-<vein>.json (with --work/$COWORK_WORK)")
    s.add_argument("--work", help="work dir holding raw-conclusions-<vein>.json (or set $COWORK_WORK)")
    s.add_argument("--map", required=True, help="corpus-map.json")
    s.set_defaults(func=cmd_assert_ruled)

    a = ap.parse_args()
    sys.exit(a.func(a))


if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "system", "tools")))
    from utf8_stdio import force_utf8_stdio
    force_utf8_stdio()
    main()

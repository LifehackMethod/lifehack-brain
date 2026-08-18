#!/usr/bin/env python3
"""
filer_review.py — the tool-printed FILE-confirm screen for ingest-filer (F1.5, 2026-07-13).

The filer's CONFIRM step used to be hand-assembled prose (`N. title — desk/folder · record|pointer|
CANON-CANDIDATE · why`), the exact drift the design kills. This renders that filing plan through the ONE
shared renderer (pipeline.compose_screen) so it matches every other screen: title + overall %-bar → one
SAVE line per item → the ONE action last. FILE is the one screen where SAVE is the honest verb (SAVE / TOSS).
Records + pointers + dated items first; canon-CANDIDATES last, each flagged ⚠ as writing DIRECTLY into
canon/ (⚖ REVERSED 2026-08-11 — no more separate "yes, save as permanent"; the ordinary SAVE covers it).
A `dated` item is a real fourth kind (F9.2.2, 2026-08-08) — a dated-but-valuable finding
that gets AUTHORED with its date, never silently stubbed like a plain `record` (a record gets a STUB FILE;
its original is never moved, never rewritten).

The filer builds the plan JSON in-session (its SCHEMA proposals + the staged manifest) and calls this to
render it. This tool does deterministic bookkeeping only — it reads no chat bodies and writes nothing.

Plan JSON (a list): [{"title": "...", "home": "money/records", "kind": "record|pointer|dated|canon",
"why": "...", "date": "YYYY-MM-DD"}]   — "date" is required for kind="dated" (rendered on its row; missing
shows as "?" rather than silently dropping the row's whole reason for being its own kind).

Usage:
  python3 filer_review.py show --plan <plan.json> [--map <corpus-map.json>]
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import pipeline


def cmd_show(a):
    plan = json.load(open(a.plan))
    if not plan:
        print("Nothing to file — the plan is empty.")
        return 0
    # records/pointers/dated first, canon-candidates LAST (they write directly into canon/, so they're
    # flagged distinctly even though one ordinary SAVE covers them too) — an explicit rank map (not a
    # canon-only boolean) so a future kind has one place to slot in, not a guess.
    _KIND_RANK = {"record": 0, "pointer": 0, "dated": 0, "canon": 1}
    ordered = sorted(enumerate(plan), key=lambda ix: _KIND_RANK.get(ix[1].get("kind"), 0))
    header = [pipeline.compose_topbar(pipeline.load(a.map))] if a.map else None

    n_canon = sum(1 for it in plan if it.get("kind") == "canon")
    rows = [f"  Here's where your {len(plan)} notes will live. SAVE all, or change any:", ""]
    for i, (_orig, it) in enumerate(ordered, 1):
        title = (it.get("title") or "?").strip()
        home = (it.get("home") or "?").strip()
        kind = it.get("kind") or "record"
        why = (it.get("why") or "").strip()
        if kind == "canon":
            row = f'  {i:>2}  SAVE ⚠ "{title}" → canon/ (permanent, written directly)'
        elif kind == "dated":
            date = (it.get("date") or "?").strip()
            tail = f" — {why}" if why else ""
            row = f'  {i:>2}  SAVE 📅 "{title}" ({date}) → {home}{tail}'
        else:
            tail = f" — {why}" if why else ""
            row = f'  {i:>2}  SAVE "{title}" → {home}{tail}'
        if len(row) > pipeline._DW - 2:
            row = row[:pipeline._DW - 3].rstrip() + "…"
        rows.append(row)

    hint = 'the ⚠ ones write straight into canon/ — your SAVE above is the only yes needed' if n_canon else None
    bar = pipeline.compose_action_bar("file", change_hint=hint)
    print(pipeline.compose_screen(rows, bar, header_lines=header,
                                  title="📁  FILE — where your notes will live",
                                  title_right=f"{len(plan)} notes"))
    return 0


def main():
    ap = argparse.ArgumentParser(description="Tool-printed FILE-confirm screen (SAVE the honest verb).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("show", help="render the filing plan via the shared screen template")
    s.add_argument("--plan", required=True, help="filing-plan JSON (list of {title, home, kind, why})")
    s.add_argument("--map", help="corpus-map.json — renders the overall %%-progress bar as the header")
    s.set_defaults(func=cmd_show)
    a = ap.parse_args()
    sys.exit(a.func(a))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
basket_review.py — the PASSES engine for the "human sees everything" review (P6 F6.3, reworked 2026-07-10).

The flaw the first cut hit: it grouped by EXISTING tags, but the formerly-"noise" pile has NONE (that's why
it got noised) — so everything fell into one "untagged" wall and the human was ruling 20 items at a time,
forever. Wrong model. The right model is PASSES, and the human rules WHOLE BASKETS, not items:

  Pass 1 — CLUSTER (machine): the controller reads the un-clustered TITLES (metadata only, safe), groups them
           into ad-hoc subjects ("recipes", "travel", "gadget how-tos", …), and writes each back with
           `corpus_map.py set --file <f> --subject "<subject>"`. This is where the machine spends the effort.
  Pass 2 — TRIAGE (human, fast): `summary` shows each subject basket (count + sample titles). The human rules
           WHOLE baskets — `rule --subject recipes --disposition declined` (toss the theme in one call).
  Pass 3 — DEEP-DIVE (machine+human): only the baskets ruled `deep-dive` (escalated to a vein) get read at
           higher resolution by the normal vein-drill.

This tool is deterministic bookkeeping — it never reads chat CONTENT. The semantic clustering itself is the
controller's cheap LLM pass over titles; this tool feeds it (`unclustered`), presents the result (`summary`),
and applies whole-basket rulings (`rule`).

Subcommands:
  summary     --map M [--include maybe-skip,untouched]        # basket-level view for triage
  unclustered --map M [--include ...] [--limit N]             # titles needing Pass-1 clustering
  rule        --map M --subject S --disposition D [--human-approved] [--vein V]
              [--wmb <wmb_commit.py>] [--ledger L]            # batch-apply D to the whole basket
              D ∈ {declined, pointer-only, deferred, deep-dive}
"""
import argparse, json, os, subprocess, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import pipeline


def load(p):
    with open(p) as f:
        return json.load(f)


def title_of(fname):
    # the flattened filename is "<hash>-<kebab-title>.txt" — the readable part is the title
    stem = fname[:-4] if fname.endswith(".txt") else fname
    parts = stem.split("-", 1)
    return (parts[1].replace("-", " ") if len(parts) == 2 else stem)


def subject_of(row):
    # Pass-1 cluster label wins; then a named vein; then the first real tag; else UNCLUSTERED
    if row.get("subject"):
        return row["subject"]
    if row.get("vein"):
        return row["vein"]
    tags = row.get("tags") or []
    return tags[0] if tags else "UNCLUSTERED"


def in_scope(row, include):
    return row.get("filing_status") in include


def cmd_summary(a):
    """The SORT decision screen (F1.4, rebuilt 2026-07-13). Renders through the SHARED renderer so it matches
    every other screen: title + overall %-bar → one line per pile (emoji + name + count + samples) → the ONE
    action. The human's move at SORT is TOSS a whole junk pile; the rest just proceed to SCAN (no 'keep' verb,
    no keep-shallow/park/deep-dive jargon — that lives behind basket_review.rule, never on screen)."""
    include = {s.strip() for s in a.include.split(",") if s.strip()}
    m = load(a.map)
    rows = m["rows"]
    baskets = defaultdict(list)
    for f, r in rows.items():
        if in_scope(r, include):
            baskets[subject_of(r)].append(f)
    ordered = sorted(baskets.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    total = sum(len(v) for v in baskets.values())
    uncl = len(baskets.get("UNCLUSTERED", []))

    screen_rows = []
    if uncl:
        screen_rows.append(f"  ⚠ {uncl} chats aren't clustered yet — I'll sort those first.")
        screen_rows.append("")
    screen_rows.append(f"  Your chats fell into {len(ordered)} piles. Toss any junk pile; I'll scan the rest:")
    screen_rows.append("")
    for i, (subj, files) in enumerate(ordered, 1):
        emoji = pipeline._basket_emoji(subj)
        pretty = subj.replace("-", " ").title()
        samples = ", ".join(title_of(f) for f in files[:3])
        row = f"  {i:>2}  {emoji} {pretty:<12} ({len(files):>3})  — {samples}"
        if len(row) > pipeline._DW - 2:
            row = row[:pipeline._DW - 3].rstrip() + "…"
        screen_rows.append(row)

    print(pipeline.compose_screen(screen_rows, pipeline.compose_action_bar("sort"),
                                  header_lines=[pipeline.compose_topbar(m)],
                                  title="🗂  SORT — your chats, clustered", title_right=f"{total} chats"))


def cmd_unclustered(a):
    include = {s.strip() for s in a.include.split(",") if s.strip()}
    rows = load(a.map)["rows"]
    todo = [(f, title_of(f)) for f, r in rows.items()
            if in_scope(r, include) and not r.get("subject")]
    todo.sort(key=lambda x: x[1])
    if a.limit:
        todo = todo[:a.limit]
    print(f"# {len(todo)} chat(s) need Pass-1 clustering (title only — assign each a --subject):")
    for f, t in todo:
        print(f"{f}\t{t}")


def cmd_rule(a):
    wmb = a.wmb or os.path.join(HERE, "wmb_commit.py")
    rows = load(a.map)["rows"]
    files = [f for f, r in rows.items() if r.get("subject") == a.subject]
    if not files:
        sys.exit(f"no chats in basket subject={a.subject!r}")

    if a.disposition == "deep-dive":
        # escalate the whole basket into a vein; stays OPEN, the vein-drill deep-reads it (Pass 3).
        vein = a.vein or a.subject
        d = load(a.map)
        for f in files:
            d["rows"][f]["vein"] = vein
            d["rows"][f].setdefault("learned_note", "")
            d["rows"][f]["learned_note"] = f"escalated to deep-dive vein '{vein}' (basket triage)"
        # atomic-ish write
        tmp = a.map + ".tmp"
        json.dump(d, open(tmp, "w"), indent=2); os.replace(tmp, a.map)
        print(f"OK deep-dive: {len(files)} chat(s) in '{a.subject}' → vein '{vein}' (queued for deep-read, still OPEN)")
        return

    if a.disposition not in ("declined", "pointer-only", "deferred"):
        sys.exit("disposition must be declined | pointer-only | deferred | deep-dive")
    if a.disposition == "declined" and not a.human_approved:
        sys.exit("REFUSED: 'declined' eliminates chats — pass --human-approved (ONE human ruling for the basket)")

    ok, fail = 0, 0
    for f in files:
        cmd = [sys.executable, wmb, "save", "--map", a.map, "--chat", f, "--status", a.disposition,
               "--note", f"basket ruling: {a.subject}"]
        # a whole-basket rule IS a human ruling → attest it for EVERY terminal disposition
        # (wmb_commit now requires --human-approved for filed/pointer-only/deferred/declined alike).
        cmd.append("--human-approved")
        if a.disposition in ("pointer-only", "deferred"):
            cmd += ["--note", f"basket '{a.subject}' kept as {a.disposition}"]
        if a.ledger:
            cmd += ["--ledger", a.ledger]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0:
            ok += 1
        else:
            fail += 1
            print(f"  FAIL {f}: {(r.stdout + r.stderr).strip()[:120]}")
    print(f"OK basket '{a.subject}' → {a.disposition}: {ok} chat(s) ruled" + (f", {fail} FAILED" if fail else ""))
    if fail:
        sys.exit(1)


def main():
    p = argparse.ArgumentParser(description="passes engine: cluster → rule whole baskets → deep-dive survivors")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("summary"); s.add_argument("--map", required=True)
    # ⚠ The default is the NARROW set (only what the tagger gave no category to). The SORT board wants
    # the WIDE set -- `--include untouched,maybe-skip` -- or the human rules on pile boundaries having
    # been shown only the junk candidates. PHASE 1 passes it explicitly for exactly that reason.
    s.add_argument("--include", default="maybe-skip"); s.set_defaults(fn=cmd_summary)
    u = sub.add_parser("unclustered"); u.add_argument("--map", required=True)
    u.add_argument("--include", default="maybe-skip"); u.add_argument("--limit", type=int, default=0)
    u.set_defaults(fn=cmd_unclustered)
    r = sub.add_parser("rule"); r.add_argument("--map", required=True); r.add_argument("--subject", required=True)
    r.add_argument("--disposition", required=True); r.add_argument("--human-approved", action="store_true")
    r.add_argument("--vein", default=None); r.add_argument("--wmb", default=None); r.add_argument("--ledger", default=None)
    r.set_defaults(fn=cmd_rule)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "system", "tools")))
    from utf8_stdio import force_utf8_stdio
    force_utf8_stdio()
    main()

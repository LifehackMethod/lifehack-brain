#!/usr/bin/env python3
"""
corpus_map.py — the CORPUS MAP: the write-half of the self-improving engine + the resume checkpoint.

One persistent per-chat provenance record so nothing is ever lost and a future run resumes WARM:
every chat carries {tags, freshness, verdict, filing_status, source_pointer, learned_note}. Durable facts
get COPIED into a desk (with a back-pointer); everything else keeps a pointer + a one-line note here — never
bulk-copied, never a black box. The skill READS this to pre-fill guesses (fewer questions each pass) and to
know what's done vs untouched; it WRITES to it after every loop.

filing_status:
  machine-set, NON-terminal (still OPEN — needs human eyes):  untouched · maybe-skip · in-flight
  human-set, TERMINAL (a human ruled):                        filed · pointer-only · deferred · declined
`noise` is RETIRED — it conflated the machine's guess with a human verdict, which is exactly how chats
got silently discarded. The machine's soft "probably skippable" guess is now `maybe-skip` (STILL OPEN);
the human's "I looked, it's junk" ruling is `declined` (terminal). ONLY THE HUMAN ELIMINATES.

Modes:
  init   — bootstrap corpus-map.json from world-tags.json (one row per chat; 0 tags → maybe-skip, a
           machine GUESS that STAYS OPEN — never a terminal junk status).
  audit  — coverage accounting: every flattened chat must have a row; fail-closed on any missing.
  set    — update one chat's verdict / filing_status / learned_note (idempotent upsert by file).
  stats  — counts by filing_status + how much of the corpus is still untouched.

Usage:
  python3 corpus_map.py init  --tags <world-tags.json> --out <corpus-map.json>
  python3 corpus_map.py set   --map <corpus-map.json> --file <name> [--status filed] [--verdict "..."] [--note "..."] [--desk peter]
  python3 corpus_map.py stats --map <corpus-map.json>
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pipeline  # the v2 schema single-source (SCHEMA_VERSION, CHAT_V2_DEFAULTS, BASKET_DEFAULTS)

# ── Status vocabulary — SINGLE SOURCE (mirrored in SKILL.md's contract block) ──
MACHINE_STATUSES = {"untouched", "maybe-skip", "in-flight"}          # machine-set, NON-terminal, OPEN
HUMAN_TERMINAL   = {"filed", "pointer-only", "deferred", "declined"}  # human-set ONLY, via wmb_commit (gated)

# ── BASKET COMFORT THRESHOLD — an ADVISORY, deliberately not a gate (revised 2026-08-04).
#
# WHY IT EXISTS AT ALL: the pile count is the number of times the human sits down. 23 piles means 23 rounds
# of scan → deep-read → reflect; 8 means 8. That is the difference between finishing and abandoning, and the
# 2026-04 predecessor migration was abandoned half-done. So a high count is worth SAYING OUT LOUD.
#
# WHY IT IS NOT A REFUSAL (this replaced a hard gate written earlier the same day): the basket count is
# EMERGENT, not a target. SORT's first move is a light read that discovers what boundaries actually exist in
# a corpus whose makeup is opaque from the outside — so a threshold that refuses fights the very discovery
# the phase is for. Written in the morning, it blocked the live 23-basket corpus by the afternoon.
# The earlier gradient rule ("keep baskets human-sized") failed for the opposite reason — too soft to notice
# when it broke. A LOUD ADVISORY is the middle: impossible to miss, impossible to be blocked by.
#
# WHERE THE REAL RESOLUTION LIVES: SORT proposes merges with reasons and the human rules them. The machine
# never sets the count; it only makes the cost visible. Already-committed baskets don't count — closed work
# shouldn't nag a later run just for having existed.
BASKET_COMFORT = 12


def load(path):
    return json.load(open(path)) if os.path.exists(path) else {"rows": {}}


def save(obj, path):
    # atomic tmp-then-rename — a crash mid-write never leaves a half-file (matches wmb_commit/pipeline).
    import tempfile
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(obj, f, indent=2)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def do_init(a):
    # ⛔ A MISSING TAGS FILE IS A NORMAL OUTCOME, NOT A CRASH. Until 2026-08-13 this line was a bare
    # `json.load(open(a.tags))`, so the commonest real failure in PHASE 1 -- the tagger step did not
    # produce world-tags.json, because a reader was blocked, a spawn returned nothing, or a pile was
    # quarantined -- surfaced to a person who has never opened a terminal as a raw Python traceback
    # ending in FileNotFoundError. Found by a fake-user drive, 2026-08-13.
    # A traceback tells them the tool is broken. It is not; the step before it did not finish.
    if not os.path.isfile(a.tags):
        print("CANNOT START: no tag file at " + a.tags)
        print("  The step before this one -- tagging your material -- did not finish, so there is")
        print("  nothing yet to build the map from. This is not a broken install.")
        print("  Re-run the tagging step; if it reported anything missing or quarantined, fix that first.")
        sys.exit(1)
    try:
        tags = json.load(open(a.tags, encoding="utf-8"))
    except json.JSONDecodeError as e:
        print("CANNOT START: the tag file at " + a.tags + " is not readable JSON.")
        print("  (" + str(e) + ")")
        print("  It was written incompletely -- re-run the tagging step rather than editing it by hand.")
        sys.exit(1)
    rows = tags.get("rows", tags if isinstance(tags, list) else [])
    out = {"source": os.path.basename(a.tags), "rows": {}}
    for r in rows:
        f = r.get("file")
        if not f:
            continue
        cats = r.get("categories") or []
        out["rows"][f] = {
            "file": f,
            "conversation_id": r.get("conversation_id"),
            "tags": cats,
            "freshness": r.get("freshness", "unknown"),
            "verdict": None,                     # human ruling (filled at HITL)
            # 0 tags = the machine GUESSES "probably skippable" → maybe-skip (STILL OPEN, needs human
            # eyes). NEVER a terminal junk status — only the human eliminates.
            "filing_status": "maybe-skip" if not cats else "untouched",
            "source_pointer": f,                 # the flattened chat (points back into the corpus)
            "desk": None,
            "learned_note": "",
        }
    save(out, a.out)
    n = len(out["rows"]); maybe = sum(1 for v in out["rows"].values() if v["filing_status"] == "maybe-skip")
    print(f"OK: corpus map initialized — {n} chats ({maybe} maybe-skip [machine guess, OPEN], "
          f"{n-maybe} untouched) → {a.out}")


def do_set(a):
    # BACK-DOOR CLOSED: `set` is MACHINE bookkeeping — it may write only non-terminal statuses.
    # A human-terminal ruling (esp. `declined` = eliminate) must go through `wmb_commit save`
    # (human-gated + receipts + read-back). This stops a forgetful/hijacked caller from silently
    # eliminating a chat via the un-gated path. Only the human eliminates.
    if a.status and a.status in HUMAN_TERMINAL:
        sys.exit(f"REFUSED: '{a.status}' is a HUMAN-terminal ruling — `set` is machine bookkeeping and "
                 f"may write only {sorted(MACHINE_STATUSES)}. Route terminal verdicts through "
                 f"`wmb_commit save` (human-gated). RULE: skills/world-model-builder/SKILL.md → status contract.")
    if a.status and a.status not in MACHINE_STATUSES:
        sys.exit(f"REFUSED: unknown status '{a.status}'. `set` may write only {sorted(MACHINE_STATUSES)}.")
    m = load(a.map)
    row = m["rows"].get(a.file)
    if row is None:
        row = {"file": a.file, "tags": [], "freshness": "unknown", "verdict": None,
               "filing_status": "untouched", "source_pointer": a.file, "desk": None, "learned_note": ""}
        m["rows"][a.file] = row
    if a.status:  row["filing_status"] = a.status
    if a.verdict: row["verdict"] = a.verdict
    if a.note:    row["learned_note"] = a.note
    if a.desk:    row["desk"] = a.desk
    if a.vein:    row["vein"] = a.vein
    if getattr(a, "subject", None):  row["subject"] = a.subject   # ad-hoc cluster label (Pass-1 clustering)
    save(m, a.map)
    print(f"OK: {a.file} → status={row.get('filing_status')} desk={row.get('desk')} vein={row.get('vein')} "
          f"subject={row.get('subject')} note={(row.get('learned_note') or '')[:50]!r}")


# undecided = a chat that still needs a decision or a re-run (maybe-skip = machine guess, still OPEN)
UNDECIDED = {"untouched", "maybe-skip", "in-flight", "deferred"}


def do_veins(a):
    """Convergence gate input: group chats by vein, show which veins are still OPEN
    (have undecided chats). The skill MUST NOT open a NEW vein while any vein is OPEN —
    it reads THIS, never its own memory of progress."""
    m = load(a.map)
    from collections import defaultdict, Counter
    veins = defaultdict(Counter)
    for v in m["rows"].values():
        vein = v.get("vein")
        if vein:
            veins[vein][v.get("filing_status", "untouched")] += 1
    if not veins:
        print("no veins tagged yet — name veins at the arena HITL (set --vein) before drilling")
        return
    open_ct = 0
    for name in sorted(veins):
        c = veins[name]
        undecided = sum(c[k] for k in UNDECIDED)
        state = "OPEN" if undecided else "closed"
        if undecided:
            open_ct += 1
        breakdown = " ".join(f"{k}={c[k]}" for k in sorted(c))
        print(f"[{state}] {name}: {undecided} undecided  ({breakdown})")
    print(f"\n→ {open_ct} OPEN vein(s). RULE: finish every OPEN vein's undecided chats before opening a NEW vein.")


def do_audit(a):
    """COVERAGE ACCOUNTING (fail-closed). Every flattened chat MUST have a row in the map.
    A chat present in the flatten dir but MISSING from the map was silently skipped — the exact
    browpexy failure. Exit non-zero if any are missing so an arena can't be called complete."""
    import glob
    m = load(a.map)
    have = set(m["rows"].keys())
    disk = {os.path.basename(p) for p in glob.glob(os.path.join(a.flatten_dir, "*.txt"))}
    missing = sorted(disk - have)
    extra = sorted(have - disk)
    print(f"coverage audit: {len(disk)} flattened chats · {len(have)} in map · {len(missing)} MISSING")
    for f in missing:
        print(f"  MISSING (never mapped — silently skipped): {f}")
    if extra:
        print(f"  ({len(extra)} rows in map with no matching .txt — informational)")
    if missing:
        sys.exit(f"FAIL: {len(missing)} flattened chats are NOT in the corpus map — coverage gap. "
                 f"Add them (`corpus_map.py set`) before this arena can be considered complete.")
    print("OK: every flattened chat is accounted for in the map.")


def do_stats(a):
    m = load(a.map)
    from collections import Counter
    c = Counter(v["filing_status"] for v in m["rows"].values())
    total = len(m["rows"])
    print(f"corpus map: {total} chats")
    for k, n in c.most_common():
        print(f"  {k:12} {n:>5}")
    not_reviewed = c.get("untouched", 0) + c.get("maybe-skip", 0) + c.get("in-flight", 0)
    touched = total - not_reviewed
    print(f"  → {touched} substantively processed; {not_reviewed} still un-reviewed "
          f"(untouched + maybe-skip + in-flight — machine has NOT been human-ruled)")


def do_migrate(a):
    """v1 → v2 (idempotent): add the per-chat v2 columns + build the top-level `baskets` section
    the 4-skill chain (ingest-1..4) asserts against. Running twice never clobbers existing v2 values.
    Existing HUMAN-terminal chats (filed/pointer-only/deferred/declined) are marked rung=committed so
    the migration NEVER re-opens a human's ruling."""
    m = load(a.map)
    m["schema_version"] = pipeline.SCHEMA_VERSION
    m.setdefault("baskets", {})
    rows = m.get("rows", {})
    for r in rows.values():
        # basket key = the existing Pass-1 subject cluster, then a deep-dive vein, else UNCLUSTERED.
        #
        # ⚠ THE SECOND CLAUSE IS LOAD-BEARING — without it the piles never become baskets. PHASE 1 runs
        # `migrate` at step 1.0d, BEFORE any chat has a subject, so every row is seeded UNCLUSTERED.
        # It then sorts chats into piles (1.2, writing `subject`) and says "re-migrate to seed the new
        # baskets" (1.2b) — but a plain `if not r.get("basket")` is already satisfied by the string
        # "UNCLUSTERED", so the re-migrate did nothing and every chat stayed in one giant basket
        # forever. Measured on a fixture corpus: 10 chats sorted into 5 piles produced ONE basket, and
        # `pad-init` — "one pad per pile" — wrote one pad.
        # Re-seeding only when the basket is still UNCLUSTERED never overwrites a real basket.
        if not r.get("basket") or (r["basket"] == "UNCLUSTERED" and r.get("subject")):
            r["basket"] = r.get("subject") or r.get("vein") or "UNCLUSTERED"
        for col, default in pipeline.CHAT_V2_DEFAULTS.items():
            r.setdefault(col, default)
        # reflect reality: a human-terminal chat is already 'committed' in the new ladder
        if r.get("resolution_rung") == "unprocessed" and r.get("filing_status") in HUMAN_TERMINAL:
            r["resolution_rung"] = "committed"
            r["status"] = "done"
    # build/refresh the baskets section from the chats' basket keys (idempotent; preserves existing)
    from collections import defaultdict
    members = defaultdict(list)
    for r in rows.values():
        members[r["basket"]].append(r)
    for i, name in enumerate(sorted(members)):
        b = m["baskets"].setdefault(name, dict(pipeline.BASKET_DEFAULTS))
        b.setdefault("sort_order", i)
        b.setdefault("basket_lock", None)
        # a basket whose every chat is already human-ruled is 'committed'; else leave/seed 'queued'
        if b.get("basket_status", "queued") != "committed":
            all_terminal = all(x.get("filing_status") in HUMAN_TERMINAL for x in members[name])
            b["basket_status"] = "committed" if all_terminal else "queued"
    # ★ THE BASKET-COMFORT ADVISORY — says it, never blocks it. migrate is the only place the `baskets`
    # section is built/grown, so it is where a fragmented clustering pass becomes visible. It PROCEEDS
    # either way: the count belongs to the material and the human, not to a threshold.
    # Any unexpected basket_status counts as OPEN (not committed) — an unknown is never treated as closed.
    open_baskets = sorted(n for n, b in m["baskets"].items() if b.get("basket_status") != "committed")
    over = len(open_baskets) > BASKET_COMFORT and not getattr(a, "allow_many_baskets", False)
    save(m, a.map)
    problems = pipeline.assert_schema(m)
    if problems:
        sys.exit("MIGRATE wrote the map but assert still fails: " + "; ".join(problems))
    n, nb = len(rows), len(m["baskets"])
    done = sum(1 for b in m["baskets"].values() if b["basket_status"] == "committed")
    print(f"OK: migrated to schema v{pipeline.SCHEMA_VERSION} — {n} chats · {nb} baskets "
          f"({done} already committed) → {a.map}")
    if over:
        print(f"\n⚠  {len(open_baskets)} open piles — worth a look before you start mining.")
        print(f"   Each pile is one round of scan → deep-read → reflect, so this is roughly "
              f"{len(open_baskets)} sittings. The design expected around 8 broad life-areas.")
        print(f"   Piles: {', '.join(open_baskets[:8])}{'…' if len(open_baskets) > 8 else ''}")
        print(f"   SORT can propose merges for you to rule on. Nothing is blocked — this is a heads-up, "
              f"not a refusal. Pass --allow-many-baskets to stop mentioning it.")


def main():
    ap = argparse.ArgumentParser(description="corpus map — provenance + resume + self-improving memory")
    sub = ap.add_subparsers(dest="mode", required=True)
    i = sub.add_parser("init");  i.add_argument("--tags", required=True); i.add_argument("--out", required=True)
    s = sub.add_parser("set");   s.add_argument("--map", required=True); s.add_argument("--file", required=True)
    s.add_argument("--status"); s.add_argument("--verdict"); s.add_argument("--note"); s.add_argument("--desk")
    s.add_argument("--vein"); s.add_argument("--subject")
    st = sub.add_parser("stats"); st.add_argument("--map", required=True)
    ve = sub.add_parser("veins"); ve.add_argument("--map", required=True)
    au = sub.add_parser("audit"); au.add_argument("--map", required=True); au.add_argument("--flatten-dir", required=True)
    mi = sub.add_parser("migrate"); mi.add_argument("--map", required=True)
    mi.add_argument("--allow-many-baskets", action="store_true",
                     help=f"silence the advisory that fires above {BASKET_COMFORT} open baskets "
                          f"(migrate never blocks on it either way)")
    a = ap.parse_args()
    {"init": do_init, "set": do_set, "stats": do_stats, "veins": do_veins,
     "audit": do_audit, "migrate": do_migrate}[a.mode](a)


if __name__ == "__main__":
    main()

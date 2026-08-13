#!/usr/bin/env python3
"""
pipeline.py — the SHARED BRAIN for the 4-skill ingestion chain (ingest-1..4).

Built 2026-07-10 after 3 rounds of the lifehack-architecture council + a 5-agent research pass
(records/briefing/2026-07-10-agent-decomposition-research.md). The monolithic world-model-builder
skill lost its own track over a long session (context rot + side-quests). The fix everyone converged
on: split it into small human-invoked skills that SHARE ONE STATE FILE (the corpus-map), so each
skill handoff RESETS the context. This module is that shared state file's schema + the pure helpers
every skill calls — so no skill has to hold pipeline state in its own head.

THE LAW (why this file exists):
  * The corpus-map IS the state machine. A skill computes "what's next" by QUERYING THE MAP
    (next_basket), never from memory → resumable + self-healing across skill switches.
  * Every skill ASSERTS the schema on open (assert_schema) and writes ONLY its own columns.
  * The chat is the tracked unit (resolution_rung + status per chat); the basket is the invocation
    scope (basket_status + basket_lock per basket).

Importable (the 4 skills' bash steps call the CLI below; other tools `import pipeline`):
  assert_schema(m) · next_basket(m) · basket_chats(m, basket, pred) · suggest_next(m, skill, basket)
  acquire_lock / release_lock / is_stale_lock (advisory TTL lock for the two-machine race)

CLI (what the SKILL.md steps invoke):
  pipeline.py assert  --map M                       # exit≠0 + prints problems if the map isn't v2
  pipeline.py next    --map M                        # prints the next non-committed basket (or DONE)
  pipeline.py suggest --map M --skill ingest-N --basket B   # prints the handoff line for a skill's exit
  pipeline.py lock    --map M --basket B --machine X --skill ingest-N --now <iso> [--ttl 1800]
  pipeline.py unlock  --map M --basket B
"""
import argparse, difflib, json, os, re, sys
from datetime import datetime, timezone
# NOTE: this repo's system python3 (/usr/bin/python3) is 3.9 — `X | None` annotation syntax crashes at
# import there. No type annotations are added below for that reason (matches this file's existing style,
# which carries none); if one is ever added, it MUST use `typing.Optional[...]`, never `X | None`.

# ── SCHEMA v2 — the SINGLE SOURCE OF TRUTH (corpus_map.py migrate + the 4 skills assert against this) ──
SCHEMA_VERSION = 2

# rungs a chat climbs down (the resolution ladder), in order
RUNGS = ["unprocessed", "skimmed", "skim-skip", "read-complete", "deep-complete", "committed"]
TERMINAL_RUNGS = {"committed"}

# per-chat v2 columns + their defaults (added on top of the v1 fields: file, tags, freshness, verdict,
# filing_status, source_pointer, desk, learned_note, subject/vein)
CHAT_V2_DEFAULTS = {
    "basket": None,             # invocation scope key (from subject/vein/UNCLUSTERED) — set by ingest-1
    "resolution_rung": "unprocessed",
    "status": "pending",        # pending | in-progress | done | error
    "scan_summary": "",         # SCAN gist — a gate-sanitized one-liner the human rules on (phase-2 machine read)
    "scan_guess": None,         # SCAN best-guess verdict (toss|research|park|None) — a HINT, never the ruling
    "skim_verdict": None,       # the HUMAN ruling: toss | research | park   (phase-2 human gate)
    "skim_note": "",            # one line; research carries its scoped deep reason (phase-2)
    "deep_flag": False,         # legacy; DEEP-READ honors skim_verdict=research
    "extraction": None,         # staged findings path/inline (DEEP-READ) — scratch, NOT a desk
    "canon_flag": None,         # DEEP-READ (level-2): True → this chat holds a canon-CANDIDATE (always-true,
                                #   2-year test) → level-3 FULL-read; the filer writes it to records/proposals/,
                                #   never canon/. None = not yet judged; False = judged, not canon. (the MANIFEST.)
    "pointer_candidate": False, # DEEP-READ (level-2): big-but-only-a-record chat — pointer-ize (keep a source
                                #   pointer), do NOT full-read. Addressing, not elimination. (the MANIFEST.)
    "chars": None,              # SCAN (2026-08-05): character length of the FLATTENED body, stamped by
                                #   scan_collect from the file on disk — NOT guessed, and NOT reported by the
                                #   reader (a reader only ever sees a SLICE and cannot know the true size).
                                #   The ruling screen shows it so the human knows what they are committing to
                                #   before marking a chat a deep-read target. OPTIONAL-ADDITIVE: absent on
                                #   every pre-existing row and on any map written before today; the screen
                                #   omits the size rather than inventing one. No migration required.
    "content_hash": None,       # sha256 of the flattened body — a DURABLE bookmark that survives a re-EXPORT
                                #   (filenames change across exports; the content doesn't). `relink` re-keys a
                                #   row to its new filename by matching this. Populated lazily by `hash`.
    "giant_sampled": False,     # DEEP-READ (2026-07-12): True → this keeper was OVER the whole-read ceiling
                                #   (DEEP_WHOLE_MAX) so it was SAMPLED head+tail, NOT read whole. A sampled
                                #   giant is the one place accuracy can silently drop (canon-poisoning risk),
                                #   so the done-gate REFUSES to stage/close it until giant_ruled is set.
    "giant_ruled": False,       # DEEP-READ (2026-07-12): the HUMAN'S explicit "yes, I saw this one was
                                #   sampled not read whole" ruling (the say-go HITL). Only set via `giant
                                #   --ruled true`; the miner can NEVER set it. Unblocks the done-gate.
    "skim_ts": None, "read_ts": None, "commit_ts": None,
}
# scan_summary/scan_guess/canon_flag/pointer_candidate/content_hash/giant_* are ADDITIVE + OPTIONAL — a live
# v2 map written BEFORE these existed must still assert clean (no migration needed; owners seed them lazily,
# readers default via .get). So they are deliberately EXCLUDED from the required-columns fitness check.
# canon_flag/pointer_candidate are the "manifest" columns the DEEP-READ miner sets and the ingest-filer reads.
OPTIONAL_ADDITIVE = {"scan_summary", "scan_guess", "canon_flag", "pointer_candidate", "content_hash",
                     "giant_sampled", "giant_ruled", "chars"}
REQUIRED_CHAT_FIELDS = ["file", "filing_status"] + [c for c in CHAT_V2_DEFAULTS if c not in OPTIONAL_ADDITIVE]

# per-basket v2 fields
BASKET_STATUSES = ["queued", "skim-interrupted", "skim-complete",
                   "read-interrupted", "read-complete", "committed"]
INTERRUPTED = {"skim-interrupted", "read-interrupted"}
BASKET_DEFAULTS = {"basket_status": "queued", "basket_lock": None, "sort_order": 0,
                   # folder_branch (F8.4, 2026-08-06): the folder shape THIS pile earned, ruled by the human in
                   # PHASE 3 (the world map) and read by PHASE 4 (place it). The spec asserted this was already
                   # "a column a build can prove" — it existed nowhere (grep: 0 hits), which is why Phase 4 fell
                   # back to designing the whole tree from scratch every run, destroying the reason for the
                   # restructure ([SL-21]: the piles ARE the draft tree). OPTIONAL-ADDITIVE: absent on every
                   # pre-existing map; readers default via .get and no migration is required.
                   # SHAPE ([5.1.1], 2026-08-11): a pile can earn MORE THAN ONE branch (propose_folder_shape()
                   # can legitimately return a 'nested' path AND a 'sibling' path for the same pile). This
                   # field therefore holds EITHER a bare string (one branch — the original, still-common shape)
                   # OR a JSON list of strings (2+ branches). Never read this field directly — use
                   # `folder_branches(b)`, which normalizes both shapes to a list.
                   "folder_branch": None}

# THE FINDING TYPES — the closed vocabulary of [SL-23] (canonical · dated · record). The last two split by
# SHAPE, not durability: a `dated` finding is discrete and still valuable; a `record` is a corpus to reference
# and is MOVED, never rewritten. Per LAW 1's seam: the human picks a member, code enforces membership
# fail-closed. Code never judges which one is right; the vocabulary never judges content.
FINDING_TYPES = ("canonical", "dated", "record")


def load(path):
    with open(path) as f:
        return json.load(f)


def rows_of(m):
    return m.get("rows", {})


def baskets_of(m):
    return m.get("baskets", {})


# ── assert_schema — the FITNESS FUNCTION (a mis-ordered / un-migrated map fails LOUD, not silent) ──
def assert_schema(m):
    """Return a list of problems (empty = conformant v2). The skills exit non-zero if non-empty."""
    problems = []
    if m.get("schema_version") != SCHEMA_VERSION:
        problems.append(f"schema_version is {m.get('schema_version')!r}, expected {SCHEMA_VERSION} "
                        f"(run: corpus_map.py migrate)")
    if "baskets" not in m or not isinstance(m.get("baskets"), dict):
        problems.append("missing top-level 'baskets' section (run: corpus_map.py migrate)")
    rows = rows_of(m)
    if not rows:
        problems.append("no 'rows' in map")
    # spot-check every row for the required columns (cheap; catches a half-migration)
    missing_cols = {}
    for k, r in rows.items():
        miss = [c for c in REQUIRED_CHAT_FIELDS if c not in r]
        if miss:
            missing_cols[k] = miss
    if missing_cols:
        sample = list(missing_cols.items())[:3]
        problems.append(f"{len(missing_cols)} chat row(s) missing v2 columns, e.g. {sample} "
                        f"(run: corpus_map.py migrate)")
    return problems


def next_basket(m):
    """The loop driver: the first basket NOT yet committed — interrupted baskets first (resume them),
    then queued, by sort_order. Returns the basket name or None (all committed = done).
    Computed from the map so the handoff survives a session ending between skills."""
    bs = baskets_of(m)
    pending = [(name, b) for name, b in bs.items() if b.get("basket_status") != "committed"]
    if not pending:
        return None
    pending.sort(key=lambda nb: (0 if nb[1].get("basket_status") in INTERRUPTED else 1,
                                 nb[1].get("sort_order", 0), nb[0]))
    return pending[0][0]


def _title(fname):
    stem = fname[:-4] if fname.endswith(".txt") else fname
    parts = stem.split("-", 1)
    return parts[1].replace("-", " ") if len(parts) == 2 else stem


def basket_list(m, basket, pred=None, include_done=False):
    """Per-chat ruling view for SCAN/DEEP-READ/COMMIT: one line per chat, from the MAP ONLY. The main
    session NEVER opens a chat body — the substance shown here is the SCAN gist (`scan_summary`), which a
    tool-less reader produced from a gate-sanitized slice and the gate re-sanitized before it was written.
    So the human rules on real substance without the untrusted body ever reaching this session.
    EXCLUDES already-committed chats by default (rung=committed) — a done chat must NEVER be re-presented
    for ruling (that would let a human overwrite a prior verdict). include_done=True only for an audit view."""
    lines = []
    i = 0
    for k, r in basket_chats(m, basket):
        if not include_done and r.get("resolution_rung") == "committed":
            continue                              # already ruled/saved — never re-show it
        if pred and not pred(r):
            continue
        i += 1
        v = r.get("skim_verdict") or "-"
        gist = (r.get("scan_summary") or "").strip()
        if gist:                                  # SCAN has run → lead with the substance + the machine's guess
            g = r.get("scan_guess") or "-"
            lines.append(f"[{i}] {_title(k)}  ·  guess:{g}  ·  \"{gist[:600]}\"  ·  verdict:{v}   ({k})")
        else:                                     # not yet scanned → title + tags only (nothing to rule on yet)
            tags = ",".join(r.get("tags") or []) or "untagged"
            lines.append(f"[{i}] {_title(k)}  ·  tags:{tags}  ·  rung:{r.get('resolution_rung')}  ·  verdict:{v}  ·  (unscanned)   ({k})")
    return lines


def _unscanned(r):
    """Needs a SCAN slice-read: not yet ruled AND no gist yet."""
    return r.get("skim_verdict") is None and not (r.get("scan_summary") or "").strip()


def _scanned_unruled(r):
    """Has a SCAN gist but the human hasn't ruled it yet — the ready-to-rule set."""
    return r.get("skim_verdict") is None and bool((r.get("scan_summary") or "").strip())


def _pending_baskets_sorted(m):
    """Non-committed baskets, interrupted-first then by sort_order — the same order next_basket picks,
    but the whole list (so the miner can sweep every pile before the filer runs)."""
    bs = baskets_of(m)
    pending = [(name, b) for name, b in bs.items() if b.get("basket_status") != "committed"]
    pending.sort(key=lambda nb: (0 if nb[1].get("basket_status") in INTERRUPTED else 1,
                                 nb[1].get("sort_order", 0), nb[0]))
    return pending


def sort_is_confirmed(m):
    """Did PHASE 1 actually FINISH — i.e. did the human rule the basket boundaries?

    THE BUG THIS CLOSES (F8.1, 2026-08-06). current_phase() used to treat "any basket exists" as proof
    SORT was done. But `phases/1-sort.md` CREATES the baskets in Step 2 and the HUMAN RULES them in
    Step 3 (split / merge / toss a whole junk pile). A session interrupted between those two steps left
    every basket at its default `queued`, so a fresh `/ingest` routed straight to PHASE 2 — and there is
    no path back to PHASE 1. The human's boundary-correction turn was lost PERMANENTLY, silently.
    Phases 2 and 3 have code-enforced done-conditions; Phase 1 had none. This is that condition.

    ⚠ ONLY THE HUMAN OPENS THIS GATE — `pipeline.py sort-confirm … --human-approved` is the one writer,
    and it is called from 1-sort.md's Step 3 close. The miner can never set it (skill-building-sop LAW 3:
    the actor never grades its own completion; §V.4b: a gate reads evidence, never a claim's form).

    GRANDFATHER CLAUSE — a field's ABSENCE must mean the SAFE thing for state written BEFORE the field
    existed (build-sop, the fault-vs-decision rule: state carrying no provenance defaults to 'fault' and
    then overrides a human). The live map holds 1,521 chats across 23 baskets with 44 human rulings and
    predates this flag entirely; reading its silence as "never sorted" would drag a half-finished run
    back to Phase 1 and re-ask boundaries already settled. So: absence + REAL PROGRESS (any basket past
    `queued`) reads as "sorted before this flag existed." Absence + no progress anywhere is the genuine
    interrupted-sort case, and that is the one that routes back."""
    if m.get("sort_confirmed"):
        return True
    # Legacy: a map that has already progressed past SORT proves the ruling turn happened.
    return any(b.get("basket_status", "queued") != "queued" for b in baskets_of(m).values())


# ── 9.1.2 — THE PHASE-1 → SCRATCHPAD GATE ────────────────────────────────────────────────────────────
# The author's original requirement, and it still holds word for word — only the ARTIFACT changed:
# "before we're even allowed to go to phase two, it would round up all of the things from phase one and
# make sure to persist them... before it proceeds to phase two." `m["pad_written"]` is the run-scoped
# completion flag this reads — set by `pad_write()` the instant the pad is actually written to disk
# (never on a dry-run, never guessed). Mirrors `sort_confirmed`/`sort_is_confirmed` EXACTLY: same
# top-level-flag shape, same grandfather clause, for the same reason (build-sop fault-vs-decision rule —
# a field's ABSENCE must mean the SAFE thing for state written before the field existed). Without the
# grandfather, arming this on a corpus already part-way through would brick it: PHASE 1 is already closed
# (grandfathered via `sort_is_confirmed`), so there is no path back to a state that could ever set the
# flag — the exact bricked-flow failure [SL-16] already names.
def pad_exists(m):
    """Did PHASE 1 actually persist its rulings into the corpus scratchpad before PHASE 2 opened? True if
    the flag is set, OR (legacy grandfather) any basket has already progressed past `queued` — proof
    PHASE 2 already opened before this flag existed.

    ⚖ RENAMED FROM `brief_is_written` 2026-08-09 when the project-brief seam became a plain scratchpad.
    ⛔ THE GATE ITSELF IS UNCHANGED AND MUST STAY. Only its dependency moved. It reads the legacy
    `brief_written` key as well, so a corpus part-way through a run under the old seam is not bricked —
    same fault-vs-decision rule as `sort_is_confirmed`: a field's ABSENCE must mean the SAFE thing."""
    if m.get("pad_written") or m.get("brief_written"):
        return True
    return any(b.get("basket_status", "queued") != "queued" for b in baskets_of(m).values())


def mark_pad_written(m, corpus_id, path, now_iso=None):
    """The run-scoped completion flag PHASE 2 gates on — set ONLY by a real (non-dry-run) disk write in
    `pad_write()`, never guessed, never set by anything claiming completion without the artifact."""
    m["pad_written"] = {"at": now_iso or _now_iso(), "path": path, "corpus_id": corpus_id}
    return m["pad_written"]


def current_phase(m):
    """The resume driver for the /ingest chain: read the map, return (phase, basket). Deterministic,
    computed from the map, never the model's memory.

    NEW MODEL (2026-07-12): MINE EVERY PILE FIRST, THEN FILE ONCE. The miner (skill `ingest`) drives
    each pile through SCAN (2) → DEEP-READ (3). Only when NO pile still needs mining does the FILER
    (phase "4", skill `ingest-filer`) run — ONCE, over the whole corpus (basket = None) — because it
    must see the whole picture to build the desk/folder schema. This replaces the old per-pile COMMIT."""
    bs = baskets_of(m)
    if not bs:
        return ("1", None)                       # fresh corpus → SORT (wide, once)
    if not sort_is_confirmed(m):
        return ("1", None)                       # baskets exist but the human never RULED them → finish SORT
    if not pad_exists(m):
        # 9.1.2: PHASE 2 REFUSES to open until PHASE 1's rulings have been persisted to this corpus's
        # scratchpad. Closed outcome set for this seam is {1,2,3,4,BLOCKED-<reason>} — never a bare None a
        # caller could mistake for "phase 1" or silently `str()` into something that looks like success.
        return ("BLOCKED-NO-PAD", None)          # named: `pad-init` has not run for this corpus
    # MINE EVERYTHING FIRST: sweep pending piles; the FIRST that still needs scan/read wins.
    for name, b in _pending_baskets_sorted(m):
        st = b.get("basket_status")
        if st in ("queued", "skim-interrupted"):
            return ("2", name)                   # SCAN (or resume it)
        if st == "read-interrupted":
            return ("3", name)                   # resume DEEP-READ
        if st == "skim-complete":
            research = _basket_chats(m, name, lambda r: r.get("skim_verdict") == "research")
            if research:
                return ("3", name)               # has research → DEEP-READ
            # skim-complete + nothing to research = this pile is mined; keep sweeping the others.
            continue
        # read-complete = mined; keep sweeping the others.
    # No pile needs mining. Either the whole corpus is mined (→ FILE) or the filer already committed all (→ DONE).
    if next_basket(m) is None:
        return ("DONE", None)                    # every pile committed by the filer
    return ("4", None)                           # all mined → the FILER runs ONCE over the whole corpus


def _basket_chats(m, basket, pred=None):
    return [(k, r) for k, r in rows_of(m).items()
            if r.get("basket") == basket and (pred is None or pred(r))]


def basket_chats(m, basket, pred=None):
    """(key, row) pairs for chats whose basket == <basket>, optionally filtered by pred(row)."""
    out = []
    for k, r in rows_of(m).items():
        if r.get("basket") == basket and (pred is None or pred(r)):
            out.append((k, r))
    return out


def suggest_next(m, skill, basket=None):
    """The one-line handoff each skill prints on exit — the blind-chain 'next pointer', computed from the
    map (never from the model's memory). Mining-then-file aware: once every pile is mined it points at the
    FILER, which the miner AUTO-CHAINS into (Vera narrates the handoff; the human types no command)."""
    ph, nb = current_phase(m)
    if ph == "DONE":
        return "All done — your whole history is sorted, read, and filed. Nothing further."
    if ph == "4":
        # Every pile is mined → PHASE 4 (place it + the root canon) runs ONCE, over the whole corpus.
        # ⚖ 2026-08-05: this used to AUTO-CHAIN into a separate `ingest-filer` skill. That split is
        # reversed — phase 4 is now just the next phase file (`skills/ingest/phases/4-place.md`), loaded
        # exactly like phases 1-3. Nothing invokes a second skill any more.
        return ("All your piles are sorted and read. Re-invoke **/ingest** → PLACE everything into the "
                "folders you already agreed (nothing is written until you approve each one).")
    label = {"2": "SCAN", "3": "DEEP-READ"}.get(ph, ph)
    if skill == "ingest-1":
        return f"Piles are set. Re-invoke **/ingest** → SCAN pile '{nb}'."
    if skill == "ingest-2":
        if ph == "3" and nb == basket:
            return f"SCAN done for '{basket}' — some chats to read deeper. Re-invoke **/ingest** → DEEP-READ pile '{basket}'."
        return f"SCAN done for '{basket}'. Re-invoke **/ingest** → {label} pile '{nb}'."
    if skill == "ingest-3":
        return f"DEEP-READ done for '{basket}'. Re-invoke **/ingest** → {label} pile '{nb}'."
    # `ingest-filer` is a legacy PHASE TOKEN, not a skill name — the filer stopped being a separate skill
    # on 2026-08-05 and is now `phases/4-place.md`. Both spellings are accepted so an in-flight run and any
    # older caller keep working; `ingest-4` is the name to use going forward.
    if skill in ("ingest-4", "ingest-filer"):
        return "Filing complete — your history is organized. Nothing further."
    return f"(unknown skill {skill!r})"


# ── advisory basket lock (the two-machine race) — visible, self-expiring; NOT distributed locking ──
def _now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def is_stale_lock(lock_str, now_iso=None, ttl_s=1800):
    """A lock is stale if older than ttl_s. lock_str = '<machine>:<skill>:<iso-ts>'."""
    if not lock_str:
        return True
    try:
        ts = lock_str.rsplit(":", 1)[-1] if lock_str.count(":") >= 2 else lock_str
        # the iso timestamp is everything after the 2nd colon; rejoin (iso has colons too)
        parts = lock_str.split(":", 2)
        ts = parts[2] if len(parts) == 3 else lock_str
        locked = datetime.fromisoformat(ts)
    except (ValueError, IndexError):
        return True
    now = datetime.fromisoformat(now_iso) if now_iso else datetime.now(timezone.utc)
    if locked.tzinfo is None:
        locked = locked.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return (now - locked).total_seconds() > ttl_s


def acquire_lock(m, basket, machine, skill, now_iso=None, ttl_s=1800):
    """Returns (ok, message). Blocks only on a FRESH lock held by a DIFFERENT machine+skill. A fresh lock
    from THIS SAME machine+skill is your OWN leftover from an abandoned run — there is no cross-machine
    race for your own lock, so reclaim it quietly (no scary 'locked, abort or wait' + no manual unlock)."""
    b = baskets_of(m).get(basket)
    if b is None:
        return False, f"no such basket '{basket}'"
    held = b.get("basket_lock")
    stole_own = False
    if held and not is_stale_lock(held, now_iso, ttl_s):
        parts = held.split(":", 2)
        held_owner = f"{parts[0]}:{parts[1]}" if len(parts) >= 2 else held
        if held_owner != f"{machine}:{skill}":
            return False, f"basket '{basket}' is locked by {held_owner} (fresh) — abort or wait"
        stole_own = True
    b["basket_lock"] = f"{machine}:{skill}:{now_iso or _now_iso()}"
    if stole_own:
        return True, "reclaimed your own machine's leftover lock"
    return True, ("re-acquired a STALE lock" if held else "acquired")


def release_lock(m, basket):
    b = baskets_of(m).get(basket)
    if b is not None:
        b["basket_lock"] = None


# ── the per-phase ANCHOR frame (anchor doctrine §4: lean, active-recall, re-injected every turn) ──
# Miner (skill `ingest`) = phases 1/2/3, ONE basket at a time. Phase "4" = the FILER (skill `ingest-filer`),
# which runs ONCE over the WHOLE corpus after every basket is mined (basket = None). One voice: VERA.
PHASE_FRAMES = {
    "1": ("SORT", "get every chat into a pile, and let the human toss whole junk piles. "
          "You do NOT read a chat body, save to a desk, or deep-dive. Propose, they rule."),
    "2": ("SCAN", "for each un-scanned chat in THIS pile, a TOOL-LESS reader reads a short gate-sanitized "
          "SLICE and returns a one-line gist + a best-guess toss/research/park — YOU never open a body in "
          "this session; then the HUMAN rules each chat on that substance (numbered, answerable by number). "
          "toss/park close the chat here (need --human-approved); only research travels on. Fence: this pile only."),
    "3": ("DEEP-READ", "read each research chat WHOLE in ONE cache-backed pass via a tool-less reader → pull "
          "the durable conclusion; flag an always-true adopted keeper canon. A rare GIANT (over ~100k chars) is "
          "SAMPLED head+tail + FLAGGED — SHOW it and get the human's ruling before the pile closes. STAGE "
          "findings, save NOTHING to a desk; no slicing, no side quests; the human is the 2nd pass."),
    "4": ("FILE", "the corpus is fully mined — now organize EVERYTHING into desks/folders and file it, "
          "human-approved. Propose desks, then sub-folders only when a desk earns them; records → "
          "records/{type}/, canon-CANDIDATES → records/proposals/ (never canon/). MAIN SESSION ONLY. "
          "Nothing writes without the human's yes; a permanent note needs the second key."),
}


_DW = 60                                            # dashboard render width
_STEP_DISPLAY = [("1", "SORT"), ("2", "SCAN"), ("3", "DEEP READ"), ("4", "FILE")]


def _bar(done, total, width=24):
    if total <= 0:
        return "░" * width
    fill = max(0, min(width, round(width * done / total)))
    return "▓" * fill + "░" * (width - fill)


def compose_progress(m, just_did=None, next_action=None):
    """The HUMAN-facing VISUAL DASHBOARD — a first-timer's 'you are here', computed from the map so it can
    never lie. Printed at the top of every /ingest turn: it walks the human (step tracker + progress bars)
    AND re-injects the state into the model's context each turn (doubles as anti-rot insurance).
    just_did / next_action are optional plain lines the current phase fills in."""
    phase, basket = current_phase(m)
    bs = baskets_of(m)
    total_b = len(bs)
    done_b = sum(1 for b in bs.values() if b.get("basket_status") == "committed")
    rule = "━" * _DW
    L = [rule, "  📥  INGESTION  —  bringing your old chats into your new system", rule, ""]
    if phase == "DONE":
        L.append(f"  ✅  ALL DONE — every one of your {total_b} piles is sorted, ruled, and saved.")
        L.append("      Your history is fully in the system. Nothing left to do here.")
        L.append(rule)
        return "\n".join(L)
    cur = str(phase)
    # step tracker: past steps ✅, current ▶ … ◀, future plain
    parts = []
    for num, name in _STEP_DISPLAY:
        parts.append(f"{name} ✅" if num < cur else (f"▶ {name} ◀" if num == cur else name))
    stepno = dict((n, i + 1) for i, (n, _) in enumerate(_STEP_DISPLAY)).get(cur, "?")
    L.append(f"  STEP {stepno} of 4      " + "    ".join(parts))
    L.append("")
    if cur == "4" or basket is None:
        # FILER: no single pile — the whole corpus is mined; now organizing it into folders.
        mined_b = sum(1 for b in bs.values() if b.get("basket_status") != "committed")
        L.append(f"  ORGANIZING     all {total_b} piles sorted & read — filing into desks/folders now")
        L.append(f"    progress      {_bar(done_b, total_b)}   {done_b} of {total_b} piles filed")
        if done_b < total_b:
            L.append(f"    {total_b - done_b} pile(s) still to file · nothing is saved until you approve each home")
    else:
        order = sorted(bs.items(), key=lambda kv: (kv[1].get("sort_order", 0), kv[0]))
        names = [k for k, _ in order]
        pos = names.index(basket) + 1 if basket in names else 0
        pretty = (basket or "").replace("-", " ").title()
        L.append(f'  PILE {pos} of {total_b}     "{pretty}"')
        L.append(f"    all piles     {_bar(done_b, total_b)}   {done_b} of {total_b} done")
        chats = basket_chats(m, basket) if basket else []
        if chats:
            n = len(chats)
            ruled = sum(1 for _, r in chats if r.get("skim_verdict") is not None)
            L.append(f"    this pile     {n} chats · you've ruled {ruled} so far   {_bar(ruled, n, 14)}")
    if just_did:
        L.append(f"\n  ↳ just did:  {just_did}")
    if next_action:
        L.append(f"  ↳ your move: {next_action}")
    L.append(rule)
    return "\n".join(L)


# the one-line "next" hint per phase — completes the Path Beat (Stage X/N · doing… · NEXT…)
_NEXT_HINT = {"1": "rule the junk piles → SCAN the first pile", "2": "rule each chat → DEEP-READ the keepers",
              "3": "confirm each conclusion → the next pile, then filing", "4": "file everything, human-approved"}


def compose_anchor(phase, basket):
    """The LEAN per-turn anchor the skill_anchor injector re-feeds EVERY turn (§4: active-recall, not passive
    re-read). It carries the TWO re-injections the playbook requires in ONE block: (a) the IDENTITY anchor
    (who you are) and (b) the PATH BEAT (a one-line Stage X/N · doing… · next… orientation). Kept < the
    injector's 1200-char ceiling. Restate-first framing = active recall, not wallpaper."""
    name, job = PHASE_FRAMES.get(str(phase), ("?", "?"))
    b = basket or "(the whole corpus — no single pile)"
    nxt = _NEXT_HINT.get(str(phase), "the next step")
    verbs = _ANCHOR_VERBS.get(str(phase), _ANCHOR_VERBS["1"])
    return (f"PATH BEAT — Stage {phase} of 4 · {name} · pile '{b}' · doing: {name.lower()} · next: {nxt}.\n"
            f"ANCHOR (restate in your own words before you act):\n"
            f"You are VERA — a CALM, COMPETENT GUIDE (not a hand-holder). The reward is the REFLECTION: the "
            f"human watches their model of themselves sharpen each round.\n"
            f"Your ONE job now: {job}\n"
            f"Every turn: PASTE the tool SCREEN verbatim (never hand-assemble, never leave it collapsed); each "
            f"screen ENDS with ONE action; PROPOSE a best-guess; NUMBER every choice; {verbs}\n"
            f"You GUIDE, they RULE — nothing saved/tossed/promoted without a yes; the map is your memory; never "
            f"eliminate unseen; never claim done unverified; end by naming the NEXT step. If a case exceeds the "
            f"basics, SAY SO.")


# 9.5.2 — the ANCHOR's per-phase verb line. Phase 2's SCAN ruling screen (scan_review.py) uses the
# RATIFIED verdict set KEEP/TOSS/EXPLORE ("E-X-P-L-O-R-E. That's it." — test_pipeline.py check 19
# already asserts `scan_review` names all three). The anchor used to inject "verbs = MINE/TOSS/SAVE …
# never 'keep'" into EVERY phase's every turn, which is simply wrong on phase 2 — KEEP is the real word
# on that live screen, not a leak. Other phases keep the MINE/TOSS/SAVE dashboard vocabulary (F1.6 below),
# which is real and still correct there. ⛔ Does NOT renumber PHASE_FRAMES — only this lookup is new.
_ANCHOR_VERBS = {
    "1": "verbs = MINE/TOSS/SAVE (SAVE only at FILE), never 'keep'.",
    "2": "verbs = KEEP/TOSS/EXPLORE (EXPLORE asks for a wider look, not a close).",
    "3": "verbs = MINE/TOSS/SAVE (SAVE only at FILE), never 'keep'.",
    "4": "verbs = MINE/TOSS/SAVE (SAVE only at FILE), never 'keep'.",
}


# ── F1.6 — THE VOCAB MAP (the ONE place a machine token becomes a human-facing verb) ─────────────
# The design cartridge's closed verb set for DASHBOARD/HUD renders: MINE / TOSS / SAVE / EXPLORE (+ the ⚠
# flag). Every render tool routes its machine token (skim_verdict / filing_status / scan_guess) through
# verb_label(). This is the single source of truth for the UX vocabulary (decision-log D3).
# ⚠ CORRECTED 2026-08-08 (task 9.5.2) — the prior comment here overclaimed a screen-wide ban on a couple
# of specific words. The ratified SCAN verdict set (scan_review.py) is KEEP/TOSS/EXPLORE, and that word
# from the old ban is shown verbatim on that screen BY DESIGN; it was never a leak. This map still governs
# the SEPARATE dashboard/HUD vocabulary below, which is real.
HUMAN_VERBS = ("MINE", "TOSS", "SAVE", "EXPLORE")
FLAG_LABEL = "⚠ needs your eyes"
_VERB = {
    # → MINE  (dig into it / advance a rung): SCAN + DEEP-READ
    "mine": "MINE", "research": "MINE", "read-deeper": "MINE", "read deeper": "MINE", "deep-dive": "MINE",
    # → TOSS  (drop it)
    "toss": "TOSS", "declined": "TOSS", "junk": "TOSS", "drop": "TOSS",
    # → SAVE  (commit to the brain — FILE only; file-vs-pointer is HIDDEN, both read as SAVE, decision-log D9)
    "save": "SAVE", "file": "SAVE", "filed": "SAVE", "pointer-only": "SAVE", "pointer": "SAVE",
    # → EXPLORE (a deferral, not a close — the ratified 3rd SCAN verdict; SPEC.md §8, the author "E-X-P-L-O-R-E")
    "explore": "EXPLORE",
}


def verb_label(machine_token, flagged=False):
    """Translate a machine verdict/status token to the human-facing verb (F1.6). Returns one of
    {MINE, TOSS, SAVE}, the ⚠ flag, or a neutral '—' for an unknown token (a leak-guard: a raw machine
    word can NEVER reach a human print). `flagged=True` (sensitive / giant-sampled) overrides to ⚠."""
    if flagged:
        return FLAG_LABEL
    return _VERB.get((machine_token or "").strip().lower(), "—")


# ── F1.1 — THE SHARED SCREEN RENDERER + the fixed ACTION BAR ─────────────────────────────────────
# Every decision screen (SORT / SCAN / DEEP-READ / FILE / REFLECT) renders through compose_screen so
# they are byte-consistent and obey the grammar: [TITLE] → [HEADER/HUD] → [ITEMS] → [ACTION as the LAST
# line]. The render tool builds the rows; it never hand-assembles the frame (decision-log D6). This kills
# the "wall" — the action is always the last thing the eye lands on.
_ACTION_BARS = {
    "sort":    'ENTER = looks right, start scanning  ·  or "toss <pile>" to drop a whole pile',
    "scan":    'Tell me what to mine or toss — e.g. "toss 3" or "all good"',
    "deep":    'Tell me what to mine or toss — e.g. "toss 3" or "all good"',
    "file":    'Tell me what to save or toss — e.g. "toss 3" or "save all"',
    "reflect": 'Look right? Correct anything, or press ENTER to continue →',
}


def compose_action_bar(kind, change_hint=None):
    """The ONE clear action, as the last line of every screen (F1.1). `kind` is a stage key
    ({sort,scan,deep,file,reflect}) OR a literal action string. Always prefixed `▶ `; an optional
    change_hint appends after a middot. Closed-value default set = decision-log D5."""
    body = _ACTION_BARS.get(kind, kind)
    if change_hint:
        body = f"{body}  ·  {change_hint}"
    return f"  ▶  {body}"


def compose_screen(rows, action_bar, header_lines=None, title=None, title_right=None):
    """The canonical screen skeleton (F1.1) — matches the approved mockups. Order is FIXED:
        ━  [title band]  ━   header/HUD lines   ─   rows   ─   ▶ action   ━
    `rows` = pre-formatted item lines (the caller numbers + labels them via verb_label). `action_bar` is
    the last content line (build it with compose_action_bar). `header_lines` = the optional HUD grid /
    lead. A screen ALWAYS ends with the action bar as its last non-rule line.

    ⭐⭐ IT ALSO EMITS A REMINDER ON **STDERR** TELLING THE MODEL TO PASTE THE SCREEN INTO ITS REPLY.
    Not decoration, and not a duplicate of the prose rule — it is that rule moved to where it can be seen.

    THE PROBLEM (2026-08-09, watched in the desktop app): tables and grids render inside a COLLAPSED tool
    block. The person sees "+34 lines" and believes nothing happened. The operator's note: *"if you render
    a table for the user, make sure you render it to the chat and don't hide it inside of a collapsed
    command"* — and *"we saw it render nicely a couple of times; it can do it, but it's hit and miss."*

    ⛔ WHY NOT SIMPLY SAY IT AGAIN IN THE SKILL: **it is already said in TEN places, including as rule #1
    of SKILL.md, and it is still hit and miss.** An eleventh restatement is the failure mode, not the fix
    (the prose-decay rule (`system/sops/skill-building-sop-extract.md`) — prose decays). The model does not lack the rule; it is reading a
    screen out of a tool result while the rule sits in a file loaded twenty turns ago. **Attaching the
    reminder to the artifact delivers it at the only moment it is actionable.**

    ⭐ STDERR RATHER THAN STDOUT, AND THAT CHOICE IS LOAD-BEARING: the nudge must reach the MODEL without
    becoming part of the screen the model pastes to the HUMAN. On stdout it would be quoted back to the
    person as "paste everything above", which is gibberish to them."""
    rule = "━" * _DW
    thin = "─" * _DW
    L = [rule]
    if title:
        tr = title_right or ""
        gap = max(2, _DW - 3 - len(title) - len(tr))
        L.append(f"  {title}{' ' * gap}{tr}".rstrip() if not tr else f"  {title}{' ' * gap}{tr}")
        L.append(rule)
    if header_lines:
        L.extend(header_lines)
        L.append(thin)
    L.extend(rows)
    L.append(thin)
    L.append(action_bar)
    L.append(rule)
    out = "\n".join(L)
    # THE NUDGE — stderr only, so it reaches the model and never the person. See the docstring.
    try:
        sys.stderr.write(
            "\n[SCREEN] The block above is what the person must SEE. In the desktop app this is COLLAPSED "
            "-- they see only \"+N lines\" and think nothing happened.\n"
            "[SCREEN] RETYPE IT IN FULL IN YOUR REPLY, as text, before you say anything else. Every row, "
            "every number, the action line last. Do not summarise it, do not shorten it, do not describe "
            "it.\n[SCREEN] If it is not in your message, they did not see it.\n")
    except Exception:
        pass          # a screen must render even if stderr is closed; the nudge is never load-bearing
    return out


# ── F2.3 — brain_count (the pure-query tally that feeds the reflection + the HUD) ────────────────
def brain_count(m):
    """Pure-query tally, no schema change (F2.3). Feeds the reflection's 'brain grew N→M' line + the HUD
    total. mined = advanced past triage (skim_verdict=='research' OR rung ≥ read-complete) · filed =
    terminal-saved (filing_status in {filed, pointer-only}) · canon = gems (canon_flag True)."""
    rung_idx = {r: i for i, r in enumerate(RUNGS)}
    read_i = rung_idx["read-complete"]
    mined = filed = canon = 0
    for r in rows_of(m).values():
        rung = r.get("resolution_rung")
        if r.get("skim_verdict") == "research" or (rung in rung_idx and rung_idx[rung] >= read_i):
            mined += 1
        if r.get("filing_status") in ("filed", "pointer-only"):
            filed += 1
        if r.get("canon_flag") is True:
            canon += 1
    return {"mined": mined, "filed": filed, "canon": canon}


# ── F2.2 — the pinned HUD (the 'second brain filling up' surface, two forms) ──────────────────────
# The ~8 broad life-areas get a stable emoji; an unknown/legacy basket falls back to '•' (never crashes
# on the pre-recluster 23-basket map). Promoted to doctrine as skill-building-sop.md §4c.
BASKET_EMOJI = {
    "financial": "💰", "creative": "✍", "acting": "🎭", "marketing": "📣",
    "health": "🏥", "home": "🏠", "investing": "📈", "misc": "⚙",
}


def _basket_emoji(name):
    return BASKET_EMOJI.get((name or "").strip().lower(), "•")


def _basket_mined(m, basket):
    """Chats in this basket the human has ruled at least once (skim_verdict set) — the 'mined' count."""
    return sum(1 for _k, r in basket_chats(m, basket) if r.get("skim_verdict") is not None)


def _basket_order(m):
    return sorted(baskets_of(m).items(), key=lambda kv: (kv[1].get("sort_order", 0), kv[0]))


def compose_basket_hud(m, cols=2, active=None):
    """The multi-line basket grid for a SCREEN HEADER (mockup ②'s top block). One cell per basket:
    emoji + pretty name + a ▓▓░ bar + mined count, laid out in `cols` columns. `active` (a basket name)
    gets a ◀ marker. ≤~5 lines for ~8 baskets."""
    order = _basket_order(m)
    counts = {name: _basket_mined(m, name) for name, _ in order}
    mx = max(counts.values()) if counts else 0
    cells = []
    for name, _b in order:
        c = counts[name]
        bar = _bar(c, mx, 8) if mx else "░" * 8
        pretty = (name or "").replace("-", " ").title()
        mark = " ◀" if active and name == active else ""
        cells.append(f"{_basket_emoji(name)} {pretty:<11}{bar} {c:>3}{mark}")
    lines = []
    for i in range(0, len(cells), cols):
        lines.append("  " + "     ".join(cells[i:i + cols]))
    return lines


def compose_statusline_hud(m):
    """The COMPACT one-line HUD for the status bar (mockup ①): `🧠 3/8 · 210 mined │ 💰47 ✍82 … │ ▓▓▓░░`.
    baskets-done/total · total mined · a per-basket emoji+count chip strip · a baskets-progress bar.
    This is the exact string statusline.sh prepends above the standard line when an ingest session is active."""
    bs = baskets_of(m)
    total_b = len(bs)
    done_b = sum(1 for b in bs.values() if b.get("basket_status") == "committed")
    order = _basket_order(m)
    mined_total = brain_count(m)["mined"]
    chips = " ".join(f"{_basket_emoji(n)}{_basket_mined(m, n)}" for n, _ in order)
    barp = _bar(done_b, total_b, 5) if total_b else "░" * 5
    return f"🧠 {done_b}/{total_b} · {mined_total} mined │ {chips} │ {barp}"


def compose_topbar(m):
    """ONE overall progress bar for a SCREEN HEADER (the author 2026-07-12): a wide bar + the PERCENTAGE of the
    whole corpus you've been through. NO points/score number (decision-log D14) — just progress. The
    per-basket breakdown grid never appears in a screen header (decision-log D13); those chips live only in
    the pinned bottom bar. One line, ≤ _DW."""
    rows = rows_of(m)
    total = len(rows)
    done = sum(1 for r in rows.values()
               if r.get("skim_verdict") is not None or r.get("resolution_rung") == "committed")
    pct = round(100 * done / total) if total else 0
    return f"  🧠 {_bar(done, total, 30)}  {pct}% of your history"


# ── F2.1 — THE REFLECTION SCREEN ("what I now know about you") — the REWARD ───────────────────────
_EXPLORE_CATS = {"exploration", "explored", "research-only", "abandoned"}


def _is_exploration(chat_obj, row):
    """True if this chat/its conclusions are research the person EXPLORED but never adopted. Checked from
    the corpus row's tags AND the conclusion metadata. An exploration item is NEVER asserted as fact —
    it appears only in the 'did you adopt this?' question (SOP principle 9 / researched ≠ true)."""
    tags = [(t or "").lower() for t in ((row.get("tags") if row else None) or [])]
    if "exploration" in tags:
        return True
    for c in (chat_obj.get("conclusions") or []):
        if not isinstance(c, dict):
            continue          # a reader that emitted a bare string must not crash the reward screen
        if (c.get("suggested_category") or "").lower() in _EXPLORE_CATS:
            return True
        if (c.get("freshness") or "").lower() in _EXPLORE_CATS:
            return True
    return False


def _clip(text, n=100):
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[:n - 1].rstrip() + "…"


def compose_reflection(m, basket, conclusions, since_iso=None, brain_before=None, next_basket_name=None):
    """THE REWARD (F2.1) — renders mockup ③. After a basket is mined, reflect a sharper model of the
    person: the durable ADOPTED facts, what's NEW this round (🆕, rows whose commit_ts/read_ts ≥ since_iso),
    and the explored-not-adopted catch (🤔, phrased ONLY as a question). HARD GUARD: an `exploration` item
    NEVER appears as an asserted fact — it is routed exclusively to the question. Ends with the ONE action.

    `conclusions` = the staged raw-conclusions list (each {file, conclusions:[{text,…}], tags?}). Renders
    through compose_screen so it obeys the one-screen grammar."""
    pretty = (basket or "").replace("-", " ").title()
    emoji = _basket_emoji(basket)
    rows = rows_of(m)
    facts, new_facts, explored = [], [], []
    for chat in conclusions:
        f = chat.get("file", "")
        key = f if f.endswith(".txt") else (f + ".txt" if f else "")
        row = rows.get(key)
        if _is_exploration(chat, row):
            stem = f.split("-", 1)[-1].replace("-", " ").strip() if f else "a thread"
            explored.append(stem or "a thread")
            continue                                   # ← the guard: never falls through to facts
        is_new = bool(since_iso and row and (row.get("commit_ts") or row.get("read_ts") or "") >= since_iso)
        for c in (chat.get("conclusions") or []):
            txt = ((c.get("text") if isinstance(c, dict) else c) or "").strip()
            if txt:
                (new_facts if is_new else facts).append(_clip(txt))

    body = []
    for t in facts[:3]:
        body.append(f"  {emoji} {t}")
    for t in new_facts[:3]:
        body.append(f"  🆕 NEW: {t}")
    if explored:
        body.append(f'  🤔 I set one aside: "{_clip(explored[0], 46)}" looked like')
        body.append(f"     research you explored but never adopted — right?")
    if not (facts or new_facts or explored):
        body.append(f"  {emoji} (nothing durable surfaced in {pretty} this round.)")
    body.append("")
    m_now = brain_count(m)["mined"]
    if brain_before is not None:
        body.append(f"  Your brain grew:  {brain_before} → {m_now} facts about you")
    else:
        body.append(f"  Your brain now holds {m_now} facts about you")

    change = f'or press ENTER for {next_basket_name.replace("-", " ").title()} →' if next_basket_name else None
    bar = compose_action_bar("reflect") if not change else f"  ▶  Look right? Correct anything, {change}"
    return compose_screen(body, bar, title="✨  WHAT I NOW KNOW ABOUT YOU", title_right=f"after {pretty}")


# ── salvage: rescue an old deep-read so the new chain resumes at COMMIT (not a wasteful re-read) ──
def do_salvage(m, basket, raw, out_path):
    b = baskets_of(m).get(basket)
    if b is None:
        return False, f"no such basket '{basket}'"
    try:
        data = json.load(open(raw))
    except Exception as e:
        return False, f"cannot read raw file: {e}"
    arr = data if isinstance(data, list) else (data.get("conclusions") or data.get("chats_read") or [])
    # collect the chat filenames the raw file covers
    covered = []
    for el in arr:
        f = el.get("file") if isinstance(el, dict) else (el if isinstance(el, str) else None)
        if f:
            covered.append(f if f.endswith(".txt") else f + ".txt")
    # stage the raw verbatim as this basket's extraction
    import shutil
    shutil.copyfile(raw, out_path)
    rows = rows_of(m)
    staged = 0
    for k in covered:
        r = rows.get(k)
        if r is None or r.get("basket") != basket:
            continue
        r["resolution_rung"] = "read-complete"
        r["extraction"] = out_path
        r["status"] = "done"
        if r.get("skim_verdict") is None:
            r["skim_verdict"] = "research"   # it was deep-read → it was flagged research
        staged += 1
    b["basket_status"] = "read-complete"
    return True, f"staged {staged}/{len(covered)} covered chats · basket → read-complete → resumes at COMMIT"


def _conclusions_of(el):
    """The per-chat conclusion CONTENT, normalized to THE CANONICAL SHAPE: a list of {text, …} dicts.

    ⚠ Normalizing to dicts is load-bearing, not tidiness. `compose_reflection`/`_is_exploration` read
    `c.get("suggested_category")` off each element, so handing them a list of bare STRINGS raises
    AttributeError and the reward screen dies at the moment the human was owed their payoff. A reader that
    emits a flat string instead of the documented `[{text,…}]` is exactly the input that would do it — so it
    gets wrapped here, at the seam, rather than defended at every consumer."""
    if not isinstance(el, dict):
        return []
    def _wrap(v):
        if isinstance(v, dict):
            return v
        return {"text": v} if isinstance(v, str) and v.strip() else None
    c = el.get("conclusions")
    if isinstance(c, list):
        return [w for w in (_wrap(x) for x in c) if w]
    if isinstance(c, str):
        return [w for w in [_wrap(c)] if w]
    # some readers emit a single flat takeaway instead of a list
    for k in ("conclusion", "text", "takeaway", "extraction"):
        v = el.get(k)
        if isinstance(v, str) and v.strip():
            return [{"text": v}]
    return []


def coalesce_conclusions(raw_dir, out_path):
    """THE READER→REVIEW SEAM (F5.3, 2026-08-04). `agent_output.py --out <dir>` writes ONE file per reader
    (`agent-<label>.json`); `conclusions_review.py resolve_infiles()` wants ONE `raw-conclusions-<basket>.json`.
    NOTHING bridged them — a fresh basket died on 'FAIL: no batch file for vein', and the only run that ever
    got through had the merged file hand-made. This is that missing step.

    Merges every `agent-*.json` in <raw_dir> into one ordered array at <out_path>:
      · tolerates the three shapes readers emit (a flat array · a list-of-arrays · a {conclusions:[...]} wrapper),
      · DEDUPES by chat key, and MERGES the conclusions of a chat split across bundles (chunk-split rows) so a
        second fragment adds to the first instead of replacing it — the prior-run-leftover case falls out of the
        same dedupe, since a stale agent-*.json in the dir merges rather than duplicating,
      · reports EMPTY rows LOUDLY. ⚠ Per SOP-candidate C22 a receipt that traces KEYS proves the key survived,
        not the meaning — so a chat that arrives with no conclusion CONTENT is counted and named, never quietly
        folded in as if it landed. It is KEPT in the output (dropping it here would be the exact silent loss this
        seam exists to stop); the coverage gate in set_basket_status is what refuses on it."""
    import glob as _glob
    if not os.path.isdir(raw_dir):
        return False, f"no such dir '{raw_dir}' — did agent_output.py run with --out {raw_dir}?", {}
    files = sorted(_glob.glob(os.path.join(raw_dir, "agent-*.json")))
    if not files:
        return False, (f"REFUSED: no agent-*.json in '{raw_dir}'. The readers wrote nothing there — collect "
                       f"them first (agent_output.py --agents ... --out '{raw_dir}'), do NOT proceed empty."), {}
    merged = {}          # chat key → the per-chat object (conclusions accumulated)
    order = []           # first-seen order, so the review screen is stable
    unreadable, split_merges = [], []
    for p in files:
        try:
            d = json.load(open(p))
        except Exception as e:
            unreadable.append(f"{os.path.basename(p)} ({e})")
            continue
        if isinstance(d, dict):
            if "file" in d and "conclusions" in d:
                d = [d]
            else:
                d = d.get("conclusions") or d.get("items") or d.get("results") or []
        flat = []
        for el in d:
            flat.extend(el if isinstance(el, list) else [el])   # a list-of-arrays = several bundles in one file
        for el in flat:
            if not isinstance(el, dict):
                continue
            key = el.get("file") or el.get("chat") or el.get("id")
            if not key:
                continue
            if key in merged:
                have = _conclusions_of(merged[key])
                new = [c for c in _conclusions_of(el) if c not in have]
                if new:
                    merged[key]["conclusions"] = have + new
                    split_merges.append(key)
                continue
            el = dict(el)
            el["conclusions"] = _conclusions_of(el)
            merged[key] = el
            order.append(key)
    rows = [merged[k] for k in order]
    empty = [k for k in order if not _conclusions_of(merged[k])]
    with open(out_path, "w") as f:
        json.dump(rows, f, indent=1)
    stats = {"readers": len(files), "chats": len(rows), "empty": empty,
             "split_merged": sorted(set(split_merges)), "unreadable": unreadable}
    msg = f"coalesced {len(files)} reader file(s) → {len(rows)} chat(s) → {out_path}"
    extras = []
    if split_merges:
        extras.append(f"{len(set(split_merges))} chat(s) re-joined from split bundles")
    if empty:
        extras.append(f"⚠ {len(empty)} chat(s) arrived with NO conclusion content: {empty[:5]}"
                      + ("…" if len(empty) > 5 else ""))
    if unreadable:
        extras.append(f"⚠ {len(unreadable)} unreadable reader file(s): {unreadable[:3]}")
    if extras:
        msg += "  ·  " + "  ·  ".join(extras)
    # An unreadable reader file is a DROPPED BUNDLE (~9-10 chats), never a warning to scroll past.
    return (not unreadable), msg, stats


# ── 9.5.3 — THE ONCE-PER-RUN INHERITANCE-OFFER FLAG (SPEC.md `2.0c`) ──────────────────────────────
# "You already have a project from a previous corpus. Want to include it?" is a HUMAN'S-TURN offer that
# belongs inside PHASE 2 — but PHASE 2 re-opens once PER PILE, and as specified (SPEC.md item 16, measured)
# nothing stopped it firing on all 23 piles of a live run. `sort_confirmed` is the only run-scoped flag
# precedent (pipeline.py ~1592) — this mirrors it exactly: a top-level map flag, set once, checked before
# asking again. `2-scan.md`'s `2.0c` (owned elsewhere) is the actual caller; this is the flag's storage +
# the mechanical dedup, not the UX turn itself.
def corpus_inherit_offered(m):
    """Has the PHASE 2 inheritance offer (`2.0c`) already been shown this run?"""
    return bool(m.get("corpus_inherit_offered"))


def set_corpus_inherit_offered(m, now_iso=None):
    """Record that the offer was shown — ONCE, ever, for this map. Idempotent (re-setting just refreshes
    the timestamp; it never re-triggers the offer, since callers check `corpus_inherit_offered()` first)."""
    m["corpus_inherit_offered"] = {"at": now_iso or _now_iso()}
    return m["corpus_inherit_offered"]


# ── 9.5.4 — WRITE-TIME `topic:` MEMBERSHIP CHECK (fail-closed enum, mirrors set_finding_type/:1183) ──
# `topic:` is a DECLARED closed vocabulary (system/topic-vocab.md) with, until now, zero code enforcement
# anywhere in the ingest chain — verified: no tool checked a written `topic:` value against it, while two
# sibling vocabularies in this same file already do (`FINDING_TYPES` above, `set_finding_type`'s
# `if ftype not in FINDING_TYPES: return False` at line ~1183). This reuses that exact pattern.
# ⛔ NOT `system/tools/topic-vocab-lint.py` — that is a post-hoc whole-tree scanner with zero callers, the
# wrong SHAPE for a write-time gate (ruled out in skills/ingest/SPEC.md item 23).
# ⛔ NEVER adds a slug to the vocab file. An unknown slug REFUSES — the archivist proposes new slugs and
# the author approves (topic-vocab.md's own write-authority rule); code only enforces membership, it never
# grows the set.
_TOPIC_SLUG_RE = re.compile(r"^- `([a-z0-9][a-z0-9-]*)`", re.MULTILINE)


# ⚖⭐ ONE RESOLVER, IMPORTED — NOT A SECOND COPY (2026-08-11). This gate used to look ONLY in the repo
# (`system/topic-vocab.md`, two directories up). `folder_scaffold.py` — the OTHER tool PHASE 4 runs, six
# lines apart in the same phase file — was corrected on 2026-08-09 to treat the vocabulary as the
# person's own data, and carries the ruling in full at its :39-53:
#
#     "A topic vocabulary is a taxonomy OF A PERSON'S LIFE. Shipping one hands every student someone
#      else's categories and quietly tells them that is how their own material should be divided."
#
# So the two gates disagreed: `folder_scaffold` would accept a slug from the person's own vocabulary
# that this one then refused, in the same phase, minutes apart. That is worse than either behaviour on
# its own. Fixed by IMPORTING its resolver rather than restating it — a restated rule is a rule that
# drifts, and this pair has now drifted once already.
#
# Resolution order (folder_scaffold's, verbatim): --vocab → <brain root>/memory/topic-vocab.md →
# the legacy in-repo copy. NO vocabulary file ships; when none resolves this REFUSES and teaches.
def _vocab_owner():
    """`folder_scaffold` owns the vocabulary contract. Imported lazily so a broken sibling cannot stop
    the rest of this pipeline from loading."""
    import folder_scaffold
    return folder_scaffold


def resolve_topic_vocab(path=None):
    """(path_or_None, paths_tried). Delegates — see the note above."""
    return _vocab_owner().resolve_vocab(path)


def load_topic_vocab(path=None):
    """The CLOSED topic vocabulary, read live on every call. Returns a set of slugs, or None if no
    vocabulary resolved at all (the caller fails CLOSED on None — 'couldn't check' is never 'passes').
    Parsing is folder_scaffold's, which stops at the '## Not topics' heading: those entries are
    record_type/doctrine markers, not subjects, and must never validate as a topic slug."""
    fs = _vocab_owner()
    resolved, _tried = fs.resolve_vocab(path)
    if resolved is None:
        return None
    return fs.load_vocab(resolved)


def validate_topics(topics, vocab=None, vocab_path=None):
    """Fail-closed membership check for a WRITTEN `topic:` value. `topics` may be a single slug or a list
    — `topic:` is written as a LIST in practice (`topic: [a, b]`), so every element is checked. Returns
    (ok, bad_slugs, vocab_or_None). `vocab is None` on entry means 'load it fresh'; a vocab that fails to
    load at all returns ok=False with vocab=None (fail-closed: an unreadable vocab is never permission)."""
    if isinstance(topics, str):
        topics = [topics]
    topics = [str(t).strip() for t in (topics or []) if str(t).strip()]
    v = vocab if vocab is not None else load_topic_vocab(vocab_path)
    if v is None:
        return False, list(topics), None
    bad = [t for t in topics if t not in v]
    return (not bad), bad, v


# ── 9.1.1 / 9.1.2 — pad-init: the PHASE 1 → SCRATCHPAD seam ──────────────────────────────────────────
# ⚖⭐ REPLACED THE PROJECT-BRIEF SEAM ENTIRELY, 2026-08-09, on the author's ruling: "take out of my skill
# a major functionality... it works out of the project manager file for its world model brain. That's no
# longer the case... forget project manager, forget integrating with that skill. It's literally just going
# to create one scratchpad that it writes to, and it persists knowledge and notes that it needs to write."
#
# ⭐ IT IS ALSO A SHIPPING FIX, NOT ONLY A SIMPLIFICATION — record that, because it closes three real
# defects at once and a future session must not "restore" the old seam thinking it was harmless:
#   1. The old compose_brief() read `system/schemas/project-doc-schema.md` off disk and REFUSED without it.
#      That file is NOT part of a shipped package, so the seam was dead on any machine but the author's.
#   2. _brief_target_path() took a DRIVE ROOT and wrote to `state/projects/<id>/brief.md` — a personal
#      filesystem layout that does not exist on a student's computer.
#   3. It made the skill depend on a SECOND skill (project-manager) and on a hook to find the armed brief.
# ⇒ The pad has NO schema file, NO external read, NO drive root, and NO sibling-skill dependency. Its root
# is simply the folder the human already named, and it lives beside their own material under `memory/`.
#
# ⛔ THE GATE SURVIVED THE REWRITE — ON PURPOSE. `pad_exists()` below is the same guard the old
# `brief_is_written()` was: PHASE 2 must not open on nothing. Only its DEPENDENCY was removed, never the
# gate itself. Deleting it would let a run start with no memory of PHASE 1's rulings at all.
#
# THE CLOSED OUTCOME SET (code/LLM-seam law: never a bare null/empty indistinguishable from success):
#   CREATED   — no pad existed; a fresh one was written with the standing skeleton, seeded from PHASE 1.
#   APPENDED  — a pad already existed; this run's entry was APPENDED beneath it. Nothing was overwritten.
#   REFUSED   — the target could not be written (unwritable path, or no root given outside --dry-run).
#               The "no outcome was reached" member: never silently treated as success.
PAD_OUTCOMES = ("CREATED", "APPENDED", "REFUSED")

# The standing skeleton — FOUR headings, deliberately. This is a scratchpad, not a schema. It exists so a
# later sitting has somewhere obvious to put things, not so anything can be validated against it. ⛔ Do not
# grow this into a schema and do not add a parser for it; that is precisely what was just removed.
PAD_HEADINGS = ("What this corpus is",
                "What the human corrected me on",
                "Confirmed subject-arcs",
                "Open threads")


def _slugify(s):
    s = re.sub(r'\.[a-zA-Z0-9]+$', '', s or '')
    s = re.sub(r'[^a-zA-Z0-9]+', '-', s).strip('-').lower()
    return s or "corpus"


def _corpus_id_from_map_path(map_path):
    """Extract `<corpus>` from a `--map` path shaped exactly like `.../projects/<corpus>/work/<file>.json`
    — the ONLY filesystem-derived signal `resolve_corpus_id()` trusts, because it is evidence about the
    file actually being operated on, not a guess. Returns None (never a guess) if the shape does not
    genuinely match: no `projects` segment, no `work` directory directly above the file, or the file is
    nested any deeper than that."""
    if not map_path:
        return None
    try:
        parts = os.path.normpath(os.path.abspath(map_path)).split(os.sep)
    except Exception:
        return None
    for i, seg in enumerate(parts):
        if seg != "projects" or i + 3 >= len(parts):
            continue
        corpus, work_dir, fname = parts[i + 1], parts[i + 2], parts[i + 3]
        if corpus and work_dir == "work" and fname.endswith(".json") and i + 4 == len(parts):
            return corpus
    return None


def resolve_corpus_id(explicit_corpus_id, map_path, env_var="INGEST_CORPUS"):
    """Resolve the corpus id used to build `memory/<corpus_id>/...` — NEVER derived from the map's
    `source` field. `source` names the TAG FILE the map was built from (e.g. `world-tags.json`), not the
    corpus; using it silently wrote pads to a folder nothing reads (`memory/world-tags/...`) — that was
    the live defect this replaces.

    Resolution order (first hit wins):
      1. `explicit_corpus_id` (the caller's `--corpus-id`) — the caller said so directly.
      2. the map's OWN PATH, if shaped like `.../projects/<corpus>/work/<file>.json` — the strongest
         filesystem evidence about the file actually in hand. Rejected outright (never guessed) when the
         shape doesn't genuinely match.
      3. `$<env_var>` (default `INGEST_CORPUS`) — ranked below the map path on purpose: an env var is a
         session leftover that can point at a DIFFERENT corpus than the map actually being operated on.
      4. REFUSE — naming all three ways to supply it. Never falls back to `source` or the literal
         `"corpus"`.

    Returns `(corpus_id, source_label)` on success, or `(None, refusal_message)` on failure — the label/
    message exists so the caller can always say WHERE the value came from, or why none could be found."""
    if explicit_corpus_id:
        return explicit_corpus_id, "--corpus-id"
    from_path = _corpus_id_from_map_path(map_path)
    if from_path:
        return from_path, f"the map's own path ({map_path})"
    env_val = os.environ.get(env_var)
    if env_val:
        return env_val, f"${env_var}"
    return None, (
        "could not resolve a corpus id. Supply ONE of: "
        "(1) --corpus-id <slug>, "
        "(2) a --map path shaped like .../projects/<corpus>/work/<file>.json, "
        f"(3) the ${env_var} environment variable. "
        "Never falls back to the map's `source` field or a literal \"corpus\" — `source` names the tag "
        "file the map was built from, not the corpus, and a wrong guess writes pads to a folder nothing "
        "reads."
    )


def _phase1_summary_lines(m):
    """Pile boundaries + counts — the ONLY PHASE-1 history the corpus map actually carries. ⚠ The map has
    NO persisted split/merge/close AUDIT TRAIL (BASKET_DEFAULTS has no notes/history field) — only the
    FINAL basket list survives, not the turn-by-turn ruling narrative. `--notes` (below) is the escape
    hatch for a caller that has that narrative in hand (e.g. from the SORT turn transcript) and wants it
    folded in verbatim; this function alone can only ever report the settled boundaries + counts."""
    bs = baskets_of(m)
    rows = rows_of(m)
    order = sorted(bs.items(), key=lambda kv: (kv[1].get("sort_order", 0), kv[0]))
    counts = {}
    for r in rows.values():
        bkt = r.get("basket")
        if bkt:
            counts[bkt] = counts.get(bkt, 0) + 1
    lines = [f"- **{name}** — {counts.get(name, 0)} chat(s) · pile status: {b.get('basket_status', 'queued')}"
             for name, b in order]
    return lines, len(rows), len(bs)


def _pad_target_path(root, corpus_id, basket=None):
    """`<root>/memory/<corpus_id>/<basket>/scratchpad.md`, or the corpus-level pad when basket is None.

    ⚖⭐ ONE PAD PER PILE, 2026-08-09 (the author, mid-build): "instead of one major scratchpad, each pile
    in phase one gets its own scratchpad... and then each of those piles is what the scratchpad gets
    written to when we're working in that pile."
    ⭐ WHY IT IS THE BETTER SHAPE, not just the asked-for one: a pile IS a sitting (`1-sort.md`: "the pile
    count is the number of times the human sits down"). Keeping the notes beside the material they are
    about means a pad never grows past what one sitting produced, and picking a pile back up loads only
    that pile's history instead of every other pile's.
    The corpus-level pad still exists for anything that spans piles; it is not the working surface.
    The pad is the HUMAN's data and lives in the human's tier — never under the code tier, which on a
    shipped package is a git working copy."""
    parts = [root, "memory", corpus_id] + ([basket] if basket else []) + ["scratchpad.md"]
    return os.path.join(*parts)


def compose_pad(m, corpus_id, now_iso=None, notes=None, basket=None):
    """The pad's INITIAL text — skeleton + what PHASE 1 settled. Pure composition, no disk I/O.
    With `basket`, it is seeded with THAT pile's own contents rather than the whole corpus."""
    now = now_iso or _now_iso()
    date = now[:10]
    lines_pile, n_chats, n_baskets = _phase1_summary_lines(m)
    if basket:
        n_here = sum(1 for _k, _r in basket_chats(m, basket))
        out = [f"# Notes on the `{basket}` pile", "",
               f"_(part of `{corpus_id}`)_", "",]
    else:
        out = [f"# Notes on `{corpus_id}`", "",
           "> This file is YOURS. The tool reads it at the start of every sitting so it does not ask you the",
           "> same thing twice, and appends to it as you rule things. Edit it freely — nothing validates it.",
           ""]
    for h in PAD_HEADINGS:
        out += [f"## {h}", ""]
        if h == "What this corpus is":
            if basket:
                out += [f"- {date} — this pile holds {n_here} chat(s). It was ruled by you at the end of "
                        f"PHASE 1, out of {n_chats} chat(s) across {n_baskets} pile(s).", ""]
            else:
                out += [f"- {date} — PHASE 1 (SORT) closed: {n_chats} chat(s) sorted into {n_baskets} "
                        f"pile(s), ruled by you.", ""] + (lines_pile or ["- (no piles yet)"]) + [""]
        elif h == "Open threads" and notes and notes.strip():
            out += [f"- {date} — your ruling notes from the sort turn: {notes.strip()}", ""]
        else:
            out += ["- (nothing yet)", ""]
    return "\n".join(out).rstrip() + "\n"


def _dated_block(entry, now_iso=None):
    """The append branch's exact block format, factored out so the create branch can use the SAME text
    for the caller's entry rather than silently dropping it. Returns '' when there is no entry text —
    the create branch must add a skeleton alone, never an empty block."""
    text = (entry or "").strip()
    if not text:
        return ""
    stamp = (now_iso or _now_iso())[:10]
    return f"\n\n---\n\n### {stamp}\n\n{text}\n"


def pad_write(m, corpus_id, root, now_iso=None, notes=None, entry=None, dry_run=False, basket=None):
    """Create the pad if absent, APPEND to it if present. Returns (outcome, path_or_None, detail) with
    outcome in PAD_OUTCOMES.

    ⛔ APPEND, NEVER OVERWRITE. The old seam returned NO-BRIEF and refused to touch an existing file, which
    meant everything learned after PHASE 1 had nowhere to go. A pad that can only be created once is a
    write-once file wearing a scratchpad's name.

    ⛔ THE CREATE BRANCH USED TO DROP `entry` ON THE FLOOR — it built the skeleton via `compose_pad()` and
    never looked at the caller's text at all. A first-ever `pad-init --entry "..."` printed OK and lost the
    note (avitals25, issue #2). The create branch now appends the SAME dated block the append branch
    writes, straight after the skeleton — skeleton alone when there is no entry, never an empty block.

    ⛔ NEVER REPORT SUCCESS ON TRUST ALONE. A clean `open()`/`write()` does not mean the bytes are actually
    on disk in the shape the caller asked for (a wrong path, a stale cached handle, a partial write can all
    look clean). After writing, this RE-READS the target and confirms what was supposed to land is actually
    in it — entry text present when an entry was given, non-empty skeleton headings present when it wasn't
    — and returns REFUSED with a clear detail on anything short of that, even though the write itself
    raised no exception."""
    if not root:
        if dry_run:
            preview = compose_pad(m, corpus_id, now_iso=now_iso, notes=notes, basket=basket)
            preview += _dated_block(entry, now_iso=now_iso)
            return "CREATED", None, preview
        return "REFUSED", None, "no root given — pass --root (the folder the human named as their brain)"
    target = _pad_target_path(root, corpus_id, basket)
    exists = os.path.isfile(target)
    if exists:
        stamp = (now_iso or _now_iso())[:10]
        text = (entry or "").strip() or "(nothing new recorded this sitting)"
        addition = f"\n\n---\n\n### {stamp}\n\n{text}\n"
    else:
        addition = compose_pad(m, corpus_id, now_iso=now_iso, notes=notes, basket=basket)
        addition += _dated_block(entry, now_iso=now_iso)
    if dry_run:
        return ("APPENDED" if exists else "CREATED"), target, addition
    try:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "a" if exists else "w", encoding="utf-8") as f:
            f.write(addition)
    except OSError as e:
        return "REFUSED", target, f"could not write {target}: {e}"

    # READ-BACK: the write raised nothing, but that alone is not proof. Re-read from disk and confirm
    # what was supposed to land is actually there before this function is allowed to claim success.
    try:
        with open(target, "r", encoding="utf-8") as f:
            written = f.read()
    except OSError as e:
        return "REFUSED", target, f"wrote {target} but could not read it back to confirm: {e}"

    stripped_entry = (entry or "").strip()
    if stripped_entry:
        if stripped_entry not in written:
            return "REFUSED", target, (
                f"wrote {target} but the entry text is NOT present on read-back — the save did not take")
    else:
        if not written.strip():
            return "REFUSED", target, f"wrote {target} but the file is EMPTY on read-back — the save did not take"
        missing = [h for h in PAD_HEADINGS if h not in written]
        if missing:
            return "REFUSED", target, (
                f"wrote {target} but skeleton heading(s) missing on read-back: {missing} — the save did not take")
    return ("APPENDED" if exists else "CREATED"), target, None

def pad_init_all(m, corpus_id, root, now_iso=None, notes=None, dry_run=False):
    """PHASE 1 close: give EVERY pile its own pad, plus one corpus-level pad for anything spanning them.
    Returns (results, refused) where results is [(basket_or_None, outcome, path)].

    ⛔ NEVER PARTIAL-SUCCEED SILENTLY. A pile whose pad could not be written is returned in `refused` and
    the caller exits non-zero. A run that quietly skipped one pile would leave that pile with no memory at
    all, and the failure would only surface as the model "forgetting" three sittings later — by which time
    nobody can tell it from ordinary context loss."""
    results, refused = [], []
    for b in [None] + sorted(baskets_of(m).keys()):
        outcome, path, detail = pad_write(m, corpus_id, root, now_iso=now_iso,
                                          notes=(notes if b is None else None),
                                          dry_run=dry_run, basket=b)
        results.append((b, outcome, path))
        if outcome == "REFUSED":
            refused.append((b, detail))
    return results, refused


# ── CLI (the SKILL.md bash steps call these) ──
def _save(m, path):
    # ATOMIC: write a sibling .tmp then os.replace() (same-FS rename is atomic) — an interrupted write can
    # never leave a half-written corpus-map; the old file stays intact until the new one is complete.
    import tempfile
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(m, f, indent=2)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


# ── durability: Drive conflict-copy guard + a content-hash bookmark that survives a re-export ──
def conflict_copies(path):
    """Google Drive can silently drop a SECOND copy of a synced file next to the original — 'corpus-map (1).json',
    'corpus-map (conflicted copy).json', '… copy.json'. Two copies = split-brain state (a skill might read the
    stale one). Return any such sibling of THIS map so the caller can HALT loud instead of quietly forking."""
    import glob
    d = os.path.dirname(os.path.abspath(path))
    base = os.path.basename(path)
    stem = (base[:-5] if base.endswith(".json") else base).lower()   # 'corpus-map'
    hits = []
    for g in glob.glob(os.path.join(d, "*.json")):
        b = os.path.basename(g)
        if b == base:
            continue
        low = b.lower()
        if stem in low and any(t in low for t in ("conflict", "(1)", "(2)", " copy", "conflicted")):
            hits.append(b)
    return sorted(hits)


def _hash_file(fpath):
    import hashlib
    h = hashlib.sha256()
    with open(fpath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def populate_hashes(m, flat_dir):
    """Lazily bookmark every row by the sha256 of its flattened body. Idempotent: a row that already has a
    content_hash, or whose flattened file is missing, is skipped. Returns the count newly hashed."""
    n = 0
    for f, r in rows_of(m).items():
        if r.get("content_hash"):
            continue
        fpath = os.path.join(flat_dir, f)
        if os.path.isfile(fpath):
            r["content_hash"] = _hash_file(fpath)
            n += 1
    return n


def relink(m, flat_dir):
    """Re-export resilience: after a fresh export, filenames change but CONTENT doesn't. For every row whose
    file no longer exists in flat_dir, find a flattened file whose sha256 matches the row's stored content_hash
    and RE-KEY the row to that new filename (preserving all its progress). Returns a list of (old, new) relinks.
    Requires content_hash to have been populated on a prior run (`hash`)."""
    rows = rows_of(m)
    # index present flat files by hash (only for hashes we're looking for — cheap)
    wanted = {r["content_hash"]: old for old, r in rows.items()
              if r.get("content_hash") and not os.path.isfile(os.path.join(flat_dir, old))}
    if not wanted:
        return []
    relinks = []
    for g in os.listdir(flat_dir):
        gp = os.path.join(flat_dir, g)
        if not os.path.isfile(gp) or g in rows:
            continue
        try:
            gh = _hash_file(gp)
        except OSError:
            continue
        old = wanted.get(gh)
        if old and old in rows:
            rows[g] = rows.pop(old)      # re-key: the row (with all progress) now lives under the new filename
            relinks.append((old, g))
            del wanted[gh]
    return relinks


# ── per-skill column WRITERS (ownership-enforcing; a skill writes ONLY via its own verb) ──
_TERMINAL_FS = {"filed", "pointer-only", "deferred", "declined"}


def _is_done(r):
    """A chat the human already closed — its rung is committed / its fate is terminal. NEVER re-rule it."""
    return r.get("resolution_rung") == "committed" or r.get("filing_status") in _TERMINAL_FS


def set_scan(m, f, guess=None, summary="", now_iso=None, chars=None):
    """SCAN (phase-2 MACHINE read): record the gate-sanitized gist + a best-guess verdict so the human can
    rule on SUBSTANCE, not a bare title. This is a PRE-ruling annotation — it does NOT set skim_verdict and
    does NOT close or advance the chat (only the human's set_skim does that). Refuses an already-closed chat."""
    r = rows_of(m).get(f)
    if r is None:
        return False, f"no chat '{f}' in map"
    if _is_done(r):
        return False, f"REFUSED: '{f}' is already CLOSED — a done chat is never re-scanned."
    if guess is not None and guess not in ("toss", "research", "park"):
        return False, f"scan guess must be toss|research|park (or omitted); got {guess!r}"
    r["scan_summary"] = summary if summary else r.get("scan_summary", "")
    # Size is MEASURED from the flattened file by the caller, never estimated. A None leaves any existing
    # value alone, so a re-scan can't blank a size that was already stamped.
    if chars is not None:
        try:
            r["chars"] = int(chars)
        except (TypeError, ValueError):
            pass
    r.setdefault("scan_guess", None)              # key always present after a scan (guess is optional)
    if guess is not None:
        r["scan_guess"] = guess
    return True, "ok"


def reset_scan(m, basket):
    """Clear the SCAN summary+guess for every UN-RULED, un-closed chat in a basket, so the next SCAN pass
    re-summarizes them. Used to regenerate short/old gists with a better prompt+model. NEVER touches a
    chat the human already ruled or closed (skim_verdict set or terminal). Returns count cleared."""
    n = 0
    for _k, r in _basket_chats(m, basket):
        if r.get("skim_verdict") is None and not _is_done(r) and (r.get("scan_summary") or r.get("scan_guess")):
            r["scan_summary"] = ""
            r["scan_guess"] = None
            n += 1
    return n


def set_skim(m, f, verdict, note="", human_approved=False, now_iso=None):
    """ingest-2 SKIM = the human's ruling on a scanned chat (the resolution ladder), per SPEC.md §8
    "THE VERDICT SET":
      toss     → junk → filing_status=declined (CLOSED at skim; needs --human-approved).
      park     → later → filing_status=deferred (CLOSED at skim; needs --human-approved).
      research → gold  → skim_verdict=research, rung=skimmed → flows to READ then a real /save at COMMIT.
      explore  → "I couldn't tell from what you showed me what this even was" (SPEC.md §8) — a DEFERRAL
                 WITH A REQUEST, not a verdict: it obliges the machine to come back with a WIDER re-look
                 (step 2.9) and ask again. Deliberately does NOT touch filing_status / resolution_rung /
                 status — the chat stays exactly where it is: not closed (_is_done stays False, so it is
                 re-rulable), not unscanned, not scanned-unruled (skim_verdict is no longer None) — a
                 distinct third bucket the basket-list --explore filter and the skim-complete gate in
                 set_basket_status both check for by name. Does NOT require --human-approved: explore
                 closes nothing, so only the closing verdicts need the human key.
                 ⚠ NAME COLLISION (checked + cleared, do not re-litigate): `exploration` already exists as
                 a CONTENT TAG the reader agents apply (tag.py CATEGORIES, tag.py:34-38) — a totally
                 different column (`categories`, not `skim_verdict`) and a noun, not this verb. See the
                 comment at tag.py:34-38 for the reverse pointer.
    Only 'research' advances past this phase. toss/park CLOSE the chat right here (durable the instant
    they're written). explore stays OPEN IN THIS PHASE — it is a loop-back, not an exit."""
    if verdict not in ("toss", "research", "park", "explore"):
        return False, f"skim verdict must be toss|research|park|explore (got {verdict!r})"
    r = rows_of(m).get(f)
    if r is None:
        return False, f"no chat '{f}' in map"
    if _is_done(r):
        return False, (f"REFUSED: '{f}' is already CLOSED ({r.get('filing_status')}, rung="
                       f"{r.get('resolution_rung')}) — re-skimming would overwrite a human verdict.")
    if verdict in ("toss", "park") and not human_approved:
        return False, (f"'{verdict}' CLOSES this chat ({'declined' if verdict=='toss' else 'deferred'}) — "
                       f"it REQUIRES --human-approved. Only the human closes a chat.")
    r["skim_verdict"] = verdict
    r["skim_note"] = note or r.get("skim_note", "")
    r["skim_ts"] = now_iso or _now_iso()
    if verdict == "research":
        r["resolution_rung"] = "skimmed"; r["status"] = "done"        # OPEN → READ → /save at COMMIT
    elif verdict == "toss":
        r["filing_status"] = "declined"; r["resolution_rung"] = "committed"; r["status"] = "done"
    elif verdict == "park":
        r["filing_status"] = "deferred"; r["resolution_rung"] = "committed"; r["status"] = "done"
    # explore: intentionally NO further writes — see the docstring above (loop-back, not an exit).
    return True, "ok"


def _in_explore(r):
    """A chat the human sent back for a wider second look and has NOT yet re-ruled (SPEC.md §8's EXPLORE
    stack). Distinct from _unscanned/_scanned_unruled: skim_verdict is SET (to 'explore'), so neither of
    those predicates catches it — this is why the skim-complete gate needs its own check for it."""
    return r.get("skim_verdict") == "explore"


# A chat whose flattened body is this short was already read IN FULL at SCAN (the adaptive slicer sends a
# short chat whole), so a "deep read" would just re-read identical text — redundant. DEEP-READ auto-skips
# these: the SCAN summary IS the finding. (Mirrors tag.SCAN_WHOLE_MAX — the whole-read slice threshold.)
WHOLE_READ_MAX = 2500


def read_whole_at_scan(char_len):
    """True if a chat this size was already read in full at SCAN → its deep read is redundant."""
    return char_len <= WHOLE_READ_MAX


# ── DEEP-READ mode switch (2026-07-12 read-strategy rewrite) ──────────────────────────────────
# The council's Venn center (records/decisions/2026-07-12-ingest-read-strategy-council-conclusions.md):
# below the effective-context CEILING, read the keeper WHOLE in ONE cache-backed pass (most-accurate AND,
# with prompt caching, cheapest — accuracy and cost stop trading off). ABOVE the ceiling, a giant would push
# the reader into the skim zone, so it is SAMPLED head+tail and FLAGGED for the human, never read silently.
# The ceiling is the ONE stakeholder-owned number (research-adjudicated to the TOP of the safe-whole zone,
# ~100k chars ≈ ~25k tokens — conservative for Claude, the long-context leader). SIZE is the switch; there
# is no middle "read-whole-in-slices" band (the council killed it — current models read that range whole).
DEEP_WHOLE_MAX = 100_000    # ≤ this many chars → read the chat WHOLE (one pass); above → sample+flag


def read_mode(char_len):
    """DEEP-READ's two-branch decision, from a chat's char length (a DETERMINISTIC input — never an LLM
    judgment). 'whole' = read the full body in one cache-backed pass. 'sample' = a genuine GIANT: sample
    head+tail and FLAG for the human (never file it silently — see set_flags giant_sampled + the done-gate)."""
    return "whole" if char_len <= DEEP_WHOLE_MAX else "sample"


def set_read(m, f, extraction=None, deep=False, now_iso=None):
    """ingest-3 owns: extraction, resolution_rung (read-complete|deep-complete), read_ts."""
    r = rows_of(m).get(f)
    if r is None:
        return False, f"no chat '{f}' in map"
    if _is_done(r):
        return False, (f"REFUSED: '{f}' is already CLOSED ({r.get('filing_status')}) — a done chat is "
                       f"never re-read/re-ruled.")
    if extraction is not None:
        r["extraction"] = extraction
    r["resolution_rung"] = "deep-complete" if deep else "read-complete"
    r["status"] = "done"
    r["read_ts"] = now_iso or _now_iso()
    return True, "ok"


def set_flags(m, f, canon=None, pointer=None):
    """DEEP-READ level-2 sets the two MANIFEST columns the filer reads: canon_flag (this chat holds a
    canon-CANDIDATE → gets the level-3 full read; the filer writes it to records/proposals/, never canon/)
    and pointer_candidate (big-but-only-a-record → pointer-ize, no full read). Additive; only the given
    flags change. These are HINTS the filer + the human rule on — never a terminal fate."""
    r = rows_of(m).get(f)
    if r is None:
        return False, f"no chat '{f}' in map"
    if canon is not None:
        r["canon_flag"] = canon
    if pointer is not None:
        r["pointer_candidate"] = pointer
    return True, "ok"


def set_giant(m, f, sampled=None, ruled=None, human_approved=False):
    """DEEP-READ (2026-07-12): the giant-path markers + the human-ruling key. `sampled=True` records that a
    keeper was over the whole-read ceiling and was SAMPLED head+tail (not read whole) — the miner sets this.
    `ruled=True` is the HUMAN's explicit say-go that they saw it was sampled — it UNBLOCKS the done-gate and
    REQUIRES --human-approved (only the human rules a giant; the miner can sample but never rule). The two are
    deliberately separate keys (a required artifact + a code gate, per playbook §3)."""
    r = rows_of(m).get(f)
    if r is None:
        return False, f"no chat '{f}' in map"
    if ruled is True and not human_approved:
        return False, ("REFUSED: ruling a sampled giant is the HUMAN'S say-go — it needs --human-approved. "
                       "The miner may sample a giant, but only the human confirms they saw it was not read whole.")
    if sampled is not None:
        r["giant_sampled"] = sampled
    if ruled is not None:
        r["giant_ruled"] = ruled
    return True, "ok"


def _giant_unruled(r):
    """A sampled giant the human has NOT yet ruled — the done-gate blocks a basket while any of these exist."""
    return bool(r.get("giant_sampled")) and not bool(r.get("giant_ruled"))


def mark_committed(m, f, now_iso=None):
    """ingest-4 marks the chat's LADDER position after wmb_commit set the terminal fate."""
    r = rows_of(m).get(f)
    if r is None:
        return False, f"no chat '{f}' in map"
    r["resolution_rung"] = "committed"
    r["status"] = "done"
    r["commit_ts"] = now_iso or _now_iso()
    return True, "ok"


def coalesced_evidence(basket, work_dir=None):
    """THE INDEPENDENT TRACE behind a DEEP-READ (F8.3, 2026-08-06). Returns (path, {chat_key: has_content})
    for this basket's coalesced reader output, or (path, None) when that file does not exist yet.

    WHY THIS EXISTS: `set_basket_status` used to prove a keeper was read by testing
    `str(r.get("extraction")).strip()` — a string the SESSION TYPES. skill-building-sop §V.4b: *"what
    independent trace proves the work happened, and does this check read THAT? If the only thing it reads is
    something the actor can type, it is theater."* The real trace is the file the READERS produced and
    `coalesce_conclusions()` merged — which already computes exactly this answer in its `empty` list, and
    which nothing consulted. `3-deep-read.md` Step 3 already promises the human that *"the read-complete gate
    will refuse the pile until they are re-read."* This is that promise, kept."""
    work = work_dir or os.environ.get("COWORK_WORK")
    if not work:
        return (None, None)
    path = os.path.join(work, f"raw-conclusions-{basket}.json")
    if not os.path.exists(path):
        return (path, None)
    try:
        data = json.load(open(path))
    except Exception:
        return (path, None)          # unreadable evidence is NO evidence — fail closed, same as missing
    if isinstance(data, dict):
        data = data.get("conclusions") or data.get("items") or data.get("results") or []
    found = {}
    for el in data:
        if not isinstance(el, dict):
            continue
        key = el.get("file") or el.get("chat") or el.get("id")
        if not key:
            continue
        found[key] = bool(_conclusions_of(el)) or found.get(key, False)
    return (path, found)


def folder_branches(b):
    """The ONE reader for `folder_branch` — always returns a list, never a bare string and never None.
    ADDITIVE (2026-08-11, [5.1.1]): `propose_folder_shape()` can legitimately return SEVERAL paths for
    one pile (e.g. a 'nested' subject and a 'sibling' subject both earned by the same pile's material),
    but the field predates that and was written/read as ONE string. Two on-disk shapes are both real and
    both must keep working forever, with no migration:
      - legacy / the common case: a bare string  → ["that string"]
      - richer (2+ branches ruled for this pile) → the list itself, as written
      - never ruled                              → [] (b.get("folder_branch") is None or "")
    Every reader of `folder_branch` — inside this file or in the phase prose — should prefer this helper
    over touching `b.get("folder_branch")` directly, so it never has to re-solve the string-vs-list case."""
    fb = b.get("folder_branch") if isinstance(b, dict) else None
    if fb is None:
        return []
    if isinstance(fb, (list, tuple)):
        out = []
        for x in fb:
            s = str(x or "").strip()
            if s and s not in out:
                out.append(s)
        return out
    s = str(fb).strip()
    return [s] if s else []


def set_folder_branch(m, basket, branch):
    """PHASE 3 (the world map) writes the folder shape this pile earned; PHASE 4 (place it) reads it.
    The human rules it; code only stores and later proves it is present.

    ADDITIVE (2026-08-11, [5.1.1]): `propose_folder_shape()` can legitimately propose MORE than one path
    for a single pile — e.g. one subject 'nested' under the pile's own folder and another 'diverse'
    subject sitting 'sibling' beside it. Before this fix, this function stored a single bare string, so
    only the LAST call's branch survived and every earlier one was silently overwritten — never surfaced
    as lost, just gone.

    `branch` now accepts either a single string OR a list/tuple of strings (a pile ruled all its branches
    in one call). Whatever is already recorded (read via `folder_branches()`, so a legacy bare string is
    honoured) is UNIONED with the new value(s), de-duplicated, order preserved — repeat calls ACCUMULATE,
    they never clobber a prior ruling.

    ⛔ NO SCHEMA MIGRATION. The on-disk shape is chosen by how many branches this pile actually has, not
    by a version flag:
      - exactly ONE branch  → stored as a bare string, BYTE-FOR-BYTE what every existing reader (this
        file's own `world-map-state` print, and the phase-prose readers in `4-place.md` that this task
        does not touch) already expects. The single-branch case — still the overwhelming common one — is
        unchanged.
      - TWO OR MORE branches → stored as a JSON list of strings. This is new information a pre-fix reader
        cannot represent; see this function's docstring continuation in the 5.1.1 report for how each
        known consumer behaves when it meets a list instead of a string — none of them raise, none of
        them silently drop data, and the visibly-wrong output (a Python list where a path was expected)
        is judged the safer failure mode over quietly keeping only one path."""
    b = baskets_of(m).get(basket)
    if b is None:
        return False, f"no such basket '{basket}'"
    if isinstance(branch, (list, tuple)):
        new_vals = [str(x or "").strip() for x in branch]
    else:
        new_vals = [str(branch or "").strip()]
    new_vals = [v for v in new_vals if v]
    if not new_vals:
        return False, "REFUSED: a folder branch cannot be blank — it is the pile's place in the tree."
    merged = folder_branches(b)
    for v in new_vals:
        if v not in merged:
            merged.append(v)
    b["folder_branch"] = merged[0] if len(merged) == 1 else merged
    return True, f"folder_branch = {b['folder_branch']!r}"


def set_finding_type(work_dir, basket, chat, index, ftype):
    """Record the HUMAN's ruling on ONE finding: canonical · dated · record (FINDING_TYPES).

    Findings live in the coalesced reader output (`raw-conclusions-<basket>.json`), which is where the
    per-finding type belongs — the map is keyed per CHAT, and one chat yields several findings, so a
    per-chat boolean can never carry it. That mismatch is why the eleven reader categories looked like they
    had 'collapsed to two booleans': they were two different RUNGS ([SL-19]).

    Code enforces MEMBERSHIP fail-closed and nothing else — it never decides which type is right."""
    if ftype not in FINDING_TYPES:
        return False, f"REFUSED: type must be one of {list(FINDING_TYPES)} — got {ftype!r}"
    path, _ = coalesced_evidence(basket, work_dir)
    if not path or not os.path.exists(path):
        return False, (f"REFUSED: no coalesced findings for basket '{basket}' "
                       f"(expected {path or 'raw-conclusions-<basket>.json'}) — run 'pipeline.py coalesce' first.")
    data = json.load(open(path))
    if isinstance(data, dict):
        data = data.get("conclusions") or data.get("items") or data.get("results") or []
    for el in data:
        if not isinstance(el, dict):
            continue
        if (el.get("file") or el.get("chat") or el.get("id")) != chat:
            continue
        cons = _conclusions_of(el)
        if index < 0 or index >= len(cons):
            return False, f"REFUSED: chat '{chat}' has {len(cons)} finding(s); no index {index}."
        cons[index]["type"] = ftype
        el["conclusions"] = cons
        with open(path, "w") as f:
            json.dump(data, f, indent=1)
        return True, f"{chat}[{index}] = {ftype}"
    return False, f"REFUSED: chat '{chat}' is not in the coalesced findings for '{basket}'."


def world_map_state(basket, work_dir=None):
    """What PHASE 4 needs to know, and what the close-gate proves: how many findings in this pile carry a
    human-chosen type, and how many do not. Returns (typed, untyped_keys) or (0, None) with no evidence."""
    path, _ = coalesced_evidence(basket, work_dir)
    if not path or not os.path.exists(path):
        return (0, None)
    try:
        data = json.load(open(path))
    except Exception:
        return (0, None)
    if isinstance(data, dict):
        data = data.get("conclusions") or data.get("items") or data.get("results") or []
    typed, untyped = 0, []
    for el in data:
        if not isinstance(el, dict):
            continue
        key = el.get("file") or el.get("chat") or el.get("id") or "?"
        for i, c in enumerate(_conclusions_of(el)):
            if c.get("type") in FINDING_TYPES:
                typed += 1
            else:
                untyped.append(f"{key}[{i}]")
    return (typed, untyped)


# ═══════════════════════════════════════════════════════════════════════════════════════════════════
# §9.6 — THE WORLD MAP (Phase 9, SPEC.md §9's restructured five-turn shape, 2026-08-08).
#
# LAW 1 for this whole block: code owns anything with a definite shape — gathering the material,
# ordering it, paginating it, classifying a reply, checking a returned shape. The MODEL composes every
# sentence a human reads (the paragraph, the per-finding 3-5 line rendering, the folder-shape reasons in
# plain language). None of these functions write prose; they hand material to the model and check what
# comes back. ⛔ "summary"/"summarize" are banned words in this pipeline — the reader EXTRACTS and STAGES,
# it never summarizes; the functions below only GATHER, ORDER, and CHECK.
# ═══════════════════════════════════════════════════════════════════════════════════════════════════

def pretty_basket_name(basket):
    """Same title-casing every other screen in this file already uses (compose_progress/compose_reflection
    do this inline) — pulled out once so the world-map title and the reflection screen never drift apart."""
    return (basket or "").replace("-", " ").title()


def world_map_title(basket):
    """The required screen title (SPEC.md §9 TURN 1): `WORLD MAP: <pile name>` — the pile is named on
    screen every time, same zero-recall law as `3.1` ORIENT."""
    return f"WORLD MAP: {pretty_basket_name(basket)}"


def worldmap_material(basket, work_dir=None):
    """9.6.1 — TURN 1's INPUT: every staged finding in this pile's coalesced reader output, handed to the
    model to compose the world-map paragraph FROM. Code's job stops at gathering; it never drafts a
    sentence. Returns (path, findings) — each finding is {file, index, text, suggested_category,
    freshness, kind, sensitive, type}. (path, []) when there is no coalesced evidence yet."""
    path, _ = coalesced_evidence(basket, work_dir)
    if not path or not os.path.exists(path):
        return (path, [])
    try:
        data = json.load(open(path))
    except Exception:
        return (path, [])
    if isinstance(data, dict):
        data = data.get("conclusions") or data.get("items") or data.get("results") or []
    out = []
    for el in data:
        if not isinstance(el, dict):
            continue
        key = el.get("file") or el.get("chat") or el.get("id") or "?"
        for i, c in enumerate(_conclusions_of(el)):
            out.append({
                "file": key, "index": i, "text": c.get("text", ""),
                "suggested_category": c.get("suggested_category"),
                "freshness": c.get("freshness"), "kind": c.get("kind"),
                "sensitive": bool(c.get("sensitive")), "type": c.get("type"),
            })
    return (path, out)


_BULLET_RE = re.compile(r'^\s*([-*•◦▪‣·]|\d+[.)])\s+')


_WM_STOP = set("""about above after again against all also and any are because been before being below between
both but came came can come could did does doing down during each few for from further had has have having her
here hers herself him himself his how into itself just like made make many more most much must myself nor not
now off once only other ought our ours ourselves out over own same she should some such than that the their
theirs them themselves then there these they this those through too under until very was way well were what
when where which while who whom why will with would you your yours yourself yourselves them thing things them
one two three four five six seven eight nine ten""".split())


def world_map_unsupported_terms(text, material_text):
    """⭐ THE FABRICATION CHECK, added 2026-08-08 — and it exists because of a measured incident, not a theory.

    On 2026-08-08 a helper was told to verify the world map "on the real invocation path, never a fixture."
    It used a real basket name, a real CLI and a real subprocess — and INVENTED THE CONTENTS, returning a
    fluent paragraph about the author writing a memoir in longhand with 40,000 words of interviews about Albania.
    His actual pile is a FILM. Checked against the live store afterwards: `memoir` 0 hits · `notebook` 0 ·
    `close third` 0 · `beta reader` 0 · `40,000` 0. **It satisfied the instruction in letter and fabricated
    a human being.** ⇒ "use real data" is not enforceable as prose; containment is.

    This is MEMBERSHIP, which is code's half: does each distinctive term in the paragraph actually appear in
    the material the composer was handed? It is deliberately NOT a quality judgment and sets no threshold —
    it returns the unsupported terms so a human SEES them. A number that appears nowhere in the source is the
    one unambiguous case and the caller refuses on it.

    ⛔ This runs INSIDE the composer's own check, before it finishes — it is not a separate watcher bolted on
    top (CODE-SPIRAL-v2: "a part that checks its OWN output before finishing is one part").

    Returns (unsupported_words, unsupported_numbers, coverage_fraction)."""
    src = (material_text or "").lower()
    src_tokens = set(re.findall(r"[a-z0-9']+", src))
    body_words, body_numbers = [], []
    for tok in re.findall(r"[A-Za-z][A-Za-z']{3,}|\d[\d,\.]*", text or ""):
        if tok[0].isdigit():
            body_numbers.append(tok)
        else:
            low = tok.lower()
            if low not in _WM_STOP:
                body_words.append(low)
    uniq = sorted(set(body_words))
    unsupported = [w for w in uniq if w not in src_tokens and w.rstrip("s") not in src_tokens]
    bad_nums = [n for n in sorted(set(body_numbers))
                if n.replace(",", "") not in src.replace(",", "")]
    coverage = (len(uniq) - len(unsupported)) / len(uniq) if uniq else 1.0
    return unsupported, bad_nums, coverage


def check_world_map_paragraph(text, basket, material_text=None):
    """9.6.1's CHECK — the other half of the paragraph composer. The model writes the prose; this only
    verifies the SHAPE it came back in: the required title is present, the body is 1-4 paragraphs, and
    NOT ONE bullet character appears anywhere. `'a wrong sentence about someone jumps out; wrong item
    fourteen of twenty does not'` (ruled 2026-08-05) — the prose format IS the error detector, so a list
    marker slipping through defeats the whole point of this turn. Never rewrites or improves the text.
    Returns (ok, reason)."""
    text = text or ""
    want_title = world_map_title(basket)
    if want_title not in text:
        return False, f'REFUSED: missing the required title line "{want_title}"'
    body = text.split(want_title, 1)[1]
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', body.strip()) if p.strip()]
    if not (1 <= len(paragraphs) <= 4):
        return False, f"REFUSED: {len(paragraphs)} paragraph(s) found — must be 1 to 4"
    for ln in text.splitlines():
        m = _BULLET_RE.match(ln)
        if m:
            return False, f"REFUSED: a list marker was found ({ln.strip()[:40]!r}) — prose only, never a list"

    shape = f"{len(paragraphs)} paragraph(s), title present, zero bullet characters"
    if material_text is None:
        return True, ("OK (SHAPE ONLY): " + shape +
                      "\n⚠ NO CONTAINMENT CHECK RAN — no source material was passed, so nothing verified that "
                      "this paragraph is about the real corpus. Pass --material to check it.")

    unsupported, bad_nums, coverage = world_map_unsupported_terms(text, material_text)
    if bad_nums:
        return False, ("REFUSED: this paragraph states figures that appear NOWHERE in the pile's material: "
                       + ", ".join(bad_nums) +
                       "\n⛔ A number with no source is fabrication, not paraphrase. Re-compose from the "
                       "material, or drop the figure.")
    line = f"OK: {shape} · source coverage {coverage:.0%}"
    if unsupported:
        shown = ", ".join(unsupported[:15]) + ("…" if len(unsupported) > 15 else "")
        line += ("\n⚠ " + str(len(unsupported)) + " term(s) in this paragraph appear nowhere in the pile's "
                 "material — READ THEM BEFORE YOU SHOW THIS TO THE HUMAN, because this is exactly how a "
                 "fabricated world map looks:\n   " + shown)
    return True, line


def paginate_items(items, page_size=10):
    """9.6.2 — THE ONE BATCHER every approval turn uses (mirrors `2.2`'s chat batcher — a plain slice at a
    target count, never a per-caller reinvention). Chunk `items` into pages of at most `page_size`. Never
    returns an empty page; [] in → [] out."""
    if not items:
        return []
    return [items[i:i + page_size] for i in range(0, len(items), page_size)]


def propose_finding_type(finding):
    """A DETERMINISTIC DEFAULT (LAW 1: code owns the definite-shape lookup) for which turn a finding is
    FIRST shown in, before the human has ruled it. The model still states the human-facing reason in its
    own words each time it composes a turn, and the human still rules the final type via `finding-type`
    — this only decides today's proposed bucket so TURNS 2-4 can be built in priority order."""
    cat = (finding.get("suggested_category") or "").lower()
    fresh = (finding.get("freshness") or "").lower()
    kind = (finding.get("kind") or "").lower()
    if cat in ("historical-record", "resources", "assets-troubleshooting"):
        return "record"
    if fresh == "dated":
        return "dated"
    if kind == "exploration" or cat == "exploration":
        # "researched ≠ true" — an explored-but-never-adopted thread is never DEFAULT-proposed canonical.
        return "dated"
    return "canonical"


def _finding_group(finding):
    t = finding.get("type")
    return t if t in FINDING_TYPES else propose_finding_type(finding)


def plan_approval_turns(findings, page_size=10):
    """9.6.2 — groups TURN 2-4 material by type, in PRIORITY ORDER (canonical -> dated -> record,
    'canonical comes first because it matters most' — the author, 2026-08-08), and paginates it: THE COUNT
    DECIDES — if every type's material fits inside one page_size-sized page COMBINED, it is ONE turn;
    otherwise any type over ~page_size items gets its OWN turn (split again if that type alone is huge).
    Code owns the shape (order + count + split); the 3-5 line human-facing rendering per item is composed
    by the model from the `items` a turn carries — this function never writes a sentence.
    Returns a list of turns: {"kind": "combined"|"canonical"|"dated"|"record", "page": i, "pages": n,
    "items": [...]}."""
    by_type = {"canonical": [], "dated": [], "record": []}
    for f in findings:
        by_type[_finding_group(f)].append(f)
    total = sum(len(v) for v in by_type.values())
    turns = []
    if total <= page_size:
        combined = by_type["canonical"] + by_type["dated"] + by_type["record"]
        if combined:
            turns.append({"kind": "combined", "page": 1, "pages": 1, "items": combined})
        return turns
    for kind in ("canonical", "dated", "record"):          # priority order, unconditionally
        items = by_type[kind]
        if not items:
            continue
        pages = paginate_items(items, page_size)
        for i, page in enumerate(pages, 1):
            turns.append({"kind": kind, "page": i, "pages": len(pages), "items": page})
    return turns


def worldmap_history_path(basket, work_dir=None):
    work = work_dir or os.environ.get("COWORK_WORK")
    return os.path.join(work, f"worldmap-{basket}.json") if work else None


def worldmap_save_paragraph(basket, text, work_dir=None, note=None, now_iso=None):
    """9.6.3 — persists the current rendered paragraph + a short version history, so the NEXT render can
    prove (mechanically) that it actually changed. Keeps the last 5 versions. The model still supplies
    the text; code only stores and, below, diffs it."""
    path = worldmap_history_path(basket, work_dir)
    if not path:
        return False, "REFUSED: no work dir — set $COWORK_WORK or pass --work"
    hist = {"basket": basket, "versions": []}
    if os.path.exists(path):
        try:
            hist = json.load(open(path))
        except Exception:
            hist = {"basket": basket, "versions": []}
    hist.setdefault("versions", []).append(
        {"text": text or "", "note": note or "", "at": now_iso or _now_iso()})
    hist["versions"] = hist["versions"][-5:]
    with open(path, "w") as f:
        json.dump(hist, f, indent=1)
    return True, f"OK: version {len(hist['versions'])} saved for '{basket}'"


def worldmap_diff_paragraph(basket, new_text, work_dir=None):
    """9.6.3's GATE — 'the re-render is the product, not a nicety... a round that returns the same picture
    the human just corrected is a wasted sitting.' REFUSES (ok=False) when `new_text` is byte-identical
    (post-strip) to the LAST saved version; otherwise returns a readable unified diff so the change is
    checkable at a glance. Code can only ever prove the text CHANGED — never that the change is TRUE; that
    half stays the human's, same as every other gate in this phase.
    Returns (ok, message, diff_text_or_None)."""
    path = worldmap_history_path(basket, work_dir)
    if not path or not os.path.exists(path):
        return True, "OK: no prior version to diff against — this is the first render", None
    try:
        hist = json.load(open(path))
    except Exception:
        return True, "OK: no readable prior version — treating as the first render", None
    versions = hist.get("versions") or []
    if not versions:
        return True, "OK: no prior version to diff against — this is the first render", None
    old_text = versions[-1].get("text", "")
    if old_text.strip() == (new_text or "").strip():
        return False, ("REFUSED: the re-rendered paragraph is IDENTICAL to the prior version — the "
                       "correction did not land. Fold the human's correction in and render again."), None
    diff = "\n".join(difflib.unified_diff(
        old_text.splitlines(), (new_text or "").splitlines(),
        lineterm="", fromfile="before", tofile="after"))
    return True, "OK: the paragraph changed", diff


# THE CLOSED OUTCOME SET for every approval turn (9.6.4, SPEC.md §9): "you can approve, or make notes and
# then move on, or... take my notes and then let's loop" (ruled 2026-08-08) + the fourth outcome code
# must handle on its own: an answer it cannot recognise. ⛔ An unrecognised answer is NEVER read as
# agreement — NO_OUTCOME means the caller RE-ASKS, never silently proceeds.
TURN_OUTCOMES = ("APPROVE", "NOTE_AND_MOVE_ON", "REFINE_AND_REPEAT", "NO_OUTCOME")

def validate_turn_outcome(value):
    """9.6.4 — MEMBERSHIP ONLY. The MODEL reads the human's reply and decides which of the four moves it
    was; this function only checks that what came back is a legal member of TURN_OUTCOMES. Code gets
    membership, artifacts and timing — nothing else (CODE-SPIRAL-v2, build-rules-index.md).

    ⚖ REPLACED A KEYWORD CLASSIFIER, 2026-08-08, and the measurement is the reason. The old
    `classify_turn_reply` matched substrings against three hand-kept word lists. Tested against twelve
    real phrasings: APPROVE caught 6 of 6 and REFINE 3 of 3, but NOTE_AND_MOVE_ON caught **0 of 3** —
    including this spec's OWN worked example, *"number 4 isn't canonical, it was just that one job"*,
    which fell through to NO_OUTCOME. So the single highest-value thing the human produces — a CORRECTION
    to a paragraph about themselves — was the one input the skill could not hear.
    ⛔ The fix was NOT an eighth keyword. Deciding what a reply MEANS is a soft-word judgment, and a
    definition you must write before you can check it IS the judgment. That half belongs to the model.
    (Third recorded instance of a strict door: `fork.py`, then a verdict interface that rejected five of
    six plausible phrasings — *"cannot be completed by adding an eighth regex"*.)

    The invariant that mattered is PRESERVED and is now structural rather than lexical: an unrecognised
    answer can never be silently promoted to APPROVE, because anything not in the closed set is refused
    outright. Returns (ok, value_or_None, message)."""
    v = (value or "").strip().upper().replace("-", "_").replace(" ", "_")
    if v in TURN_OUTCOMES:
        return True, v, "OK turn-outcome: %s" % v
    return False, None, (
        "REFUSED turn-outcome: %r is not one of %s. The reply was not classified into a legal move — "
        "re-read it and pick one, or return NO_OUTCOME and RE-ASK the human. "
        "⛔ Never proceed on an unclassified reply." % (value, " · ".join(TURN_OUTCOMES)))


def propose_folder_shape(basket, subjects, page_size=10):
    """9.6.5 — TURN 5's LAYOUT MECHANICS. the author's ruling, 2026-08-05, `authority: user`
    (restated in full right here, not a pointer into `system/knowledge-altitude.md` — a ClaudeOps-internal
    doctrine file this repo does not ship; [5.2.1], 2026-08-11): too BIG -> subdivide (nest, same territory, more shelves
    beneath it); too DIVERSE -> separate (siblings, NOT nested — mutually irrelevant bodies of knowledge
    degrade each other if loaded together). WHICH subjects are diverse vs. which are just a big single
    topic is a SEMANTIC call the model/human makes (never this function); this function only lays out the
    resulting PATHS once that call is made, plus the COST TEST reason line (place a fact at the highest
    folder where it is still always-true, and no higher — a line placed high is charged to every
    descendant that walks past it).

    `subjects` = [{"name": str, "item_count": int, "relation": "core"|"diverse"}].
    Returns [{"name", "path", "shape": "nested"|"sibling"|"flat", "why"}]."""
    root = _slugify(basket or "pile")
    multi = len([s for s in subjects if (s.get("relation") or "core") != "diverse"]) > 1
    out = []
    for s in subjects:
        name = s.get("name") or "untitled"
        slug = _slugify(name)
        relation = s.get("relation") or "core"
        count = s.get("item_count", 0)
        if relation == "diverse":
            out.append({
                "name": name, "path": slug, "shape": "sibling",
                "why": (f"mutually irrelevant to the rest of '{pretty_basket_name(basket)}' — loading it "
                        f"alongside that other material would actively confuse a session with unrelated "
                        f"context, so it sits BESIDE the pile's folder, never underneath it"),
            })
        elif count > page_size or multi:
            out.append({
                "name": name, "path": f"{root}/{slug}", "shape": "nested",
                "why": (f"{count} item(s) on one coherent topic within '{pretty_basket_name(basket)}' — "
                        f"enough material to earn its own shelf under '{root}', the highest folder where "
                        f"this is still always-true and no higher"),
            })
        else:
            out.append({
                "name": name, "path": root, "shape": "flat",
                "why": f"{count} item(s) — stays one flat folder; not enough material to subdivide",
            })
    return out


def set_basket_status(m, basket, status, work_dir=None, require_world_map=False):
    if status not in BASKET_STATUSES:
        return False, f"basket_status must be one of {BASKET_STATUSES}"
    b = baskets_of(m).get(basket)
    if b is None:
        return False, f"no such basket '{basket}'"
    # ★ THE DONE-GATE (verdict integrity): a basket can NEVER be marked 'committed' while any of its
    # chats is still un-closed — a 'research' chat that was read but not yet /saved would otherwise be
    # silently stranded ("gold thrown back in the ground"). Fail closed until every chat is terminal.
    if status == "committed":
        unclosed = [k for k, r in _basket_chats(m, basket)
                    if not (r.get("resolution_rung") == "committed" or r.get("filing_status") in _TERMINAL_FS)]
        if unclosed:
            return False, (f"REFUSED: basket '{basket}' has {len(unclosed)} chat(s) NOT yet saved/closed — "
                           f"cannot mark it done or gold would be lost. Finish them at COMMIT first: "
                           f"{unclosed[:3]}{'…' if len(unclosed) > 3 else ''}")
    # ★ THE GIANT-RULING GATE (F1.6, 2026-07-12): a keeper too big to read whole was SAMPLED head+tail — the
    # one place accuracy can silently drop. The pile can NEVER be declared mined (read-complete) or done
    # (committed) while a sampled giant has not been HUMAN-ruled (giant_ruled). This is the code lock behind
    # the say-go HITL: sampling is the miner's move, ruling is the human's — the miner cannot skip the human.
    if status in ("read-complete", "committed"):
        ungoverned = [k for k, r in _basket_chats(m, basket) if _giant_unruled(r)]
        if ungoverned:
            return False, (f"REFUSED: basket '{basket}' has {len(ungoverned)} SAMPLED GIANT(S) the human has "
                           f"not ruled yet — a giant read head+tail (not whole) must be shown + ruled before "
                           f"the pile closes, or it could poison canon unseen. Rule them first "
                           f"(giant --ruled true, human-approved): {ungoverned[:3]}{'…' if len(ungoverned) > 3 else ''}")
    # ★ THE SCAN-COVERAGE GATE (F5.4, 2026-08-04). Until today `skim-complete` had NO gate at all, so a basket
    # could be declared scanned while chats sat un-slice-read or scanned-but-never-ruled. Those chats then fall
    # out of current_phase()'s routing (it only looks for skim_verdict=="research"), and nothing ever surfaces
    # them again — the machine eliminating silently, which is precisely what the miner's first law forbids
    # ("the machine never eliminates; the human sees everything"). Fail closed, same shape as the giant gate.
    if status == "skim-complete":
        unfinished = [k for k, r in _basket_chats(m, basket)
                      if not _is_done(r) and (_unscanned(r) or _scanned_unruled(r))]
        if unfinished:
            return False, (f"REFUSED: basket '{basket}' has {len(unfinished)} chat(s) NOT yet scanned or NOT yet "
                           f"ruled — marking it skim-complete would drop them out of the phase routing and no one "
                           f"would ever see them again. Finish SCAN first (basket-list --unscanned / --scanned): "
                           f"{unfinished[:3]}{'…' if len(unfinished) > 3 else ''}  ·  "
                           f"if you meant to stop partway, use 'skim-interrupted' — that RESUMES; this one closes.")
        # ★ THE EXPLORE GATE (SPEC.md §8, step 2.11): explore is a non-terminal DEFERRAL, not a verdict —
        # "the phase cannot close while any chat sits in EXPLORE." A separate check from the one above:
        # unscanned/scanned-unruled means the human never got a chance to rule; an explore chat WAS ruled
        # (skim_verdict='explore') but the ruling was "I couldn't tell — show me more," which the human
        # fixes by re-scanning wider (basket-list --explore), not by scanning/ruling for the first time.
        exploring = [k for k, r in _basket_chats(m, basket) if not _is_done(r) and _in_explore(r)]
        if exploring:
            return False, (f"REFUSED: basket '{basket}' has {len(exploring)} chat(s) still in EXPLORE — the human "
                           f"asked for a wider second look and hasn't been shown one yet; marking it skim-complete "
                           f"now would drop them out of the phase routing and no one would ever see them again. "
                           f"Re-scan them wider first (basket-list --explore): "
                           f"{exploring[:3]}{'…' if len(exploring) > 3 else ''}")
    # ★ THE DEEP-READ COVERAGE GATE (F5.4, 2026-08-04). `read-complete` checked only sampled giants; it never
    # asked whether every keeper actually came back with a conclusion. A reader bundle can be lost silently
    # (a split return, a partial batch), and the basket would still close clean. This is Law 4.1's check placed
    # at the loss point. ⚠ C22: a STAGED RUNG proves the marker was written, not that meaning survived — so the
    # extraction must be non-empty too, or a chat whose reader returned nothing passes as read.
    if status in ("read-complete", "committed"):
        _STAGED = ("read-complete", "deep-complete", "committed")
        unstaged = [k for k, r in _basket_chats(m, basket)
                    if not _is_done(r) and r.get("skim_verdict") == "research"
                    and not (r.get("resolution_rung") in _STAGED and str(r.get("extraction") or "").strip())]
        if unstaged:
            return False, (f"REFUSED: basket '{basket}' has {len(unstaged)} keeper(s) the human sent to DEEP-READ "
                           f"that carry NO staged conclusion — a reader bundle was dropped (a split return or a "
                           f"partial batch) and closing now would bury it. Re-read them, or re-run the collect + "
                           f"'pipeline.py coalesce' for this pile first: "
                           f"{unstaged[:3]}{'…' if len(unstaged) > 3 else ''}")
    # ★ THE EVIDENCE HALF OF THAT GATE (F8.3, 2026-08-06). Everything above this line reads values the
    # SESSION TYPES: a rung it set, an `extraction` path it wrote. §V.4b — "if the only thing it reads is
    # something the actor can type, it is theater." So now read the INDEPENDENT TRACE: the coalesced reader
    # output. A keeper must actually APPEAR there WITH conclusion content, or it was never really read.
    if status == "read-complete":
        keepers = [k for k, r in _basket_chats(m, basket)
                   if not _is_done(r) and r.get("skim_verdict") == "research"]
        if keepers:
            ev_path, found = coalesced_evidence(basket, work_dir)
            if found is None:
                # No trace at all. Fail CLOSED: an unknown is never permission (build-sop), and this is the
                # exact state a dropped fan-out leaves behind.
                where = ev_path or f"raw-conclusions-{basket}.json (set $COWORK_WORK or pass --work)"
                return False, (f"REFUSED: basket '{basket}' has {len(keepers)} keeper(s) but there is NO reader "
                               f"evidence to prove they were read — expected '{where}'. The staged `extraction` "
                               f"value is typed by the session and proves nothing on its own. Collect the "
                               f"readers (agent_output.py --out raw-conclusions-{basket}) then run "
                               f"'pipeline.py coalesce' before closing this pile.")
            hollow = [k for k in keepers if not found.get(k)]
            if hollow:
                return False, (f"REFUSED: basket '{basket}' has {len(hollow)} keeper(s) with NO conclusion "
                               f"content in the reader evidence ('{ev_path}') — the row says it was read and "
                               f"the readers returned nothing for it, which is a dropped bundle, not a read. "
                               f"Re-read them, then re-run 'pipeline.py coalesce': "
                               f"{hollow[:3]}{'…' if len(hollow) > 3 else ''}")
    # ★ THE WORLD-MAP GATE (F8.4, 2026-08-06). SPEC §9 promises the pile closes "only when every finding
    # carries a human-chosen type and the pile's folder branch is set", and asserts all of it is checkable.
    # Neither column existed. They do now — this is the check.
    # ⚖ ARMED (9.5.5, 2026-08-08): PHASE 3's world-map driver now DOES exist — `3-deep-read.md` Step 5b
    # types every real keeper's findings and records the pile's `folder_branch` as a routine, mandatory
    # part of the DEEP-READ flow (SPEC.md §9). Its close command now passes `--require-world-map`
    # UNCONDITIONALLY, so a pile that skips 5b entirely (never types anything, never sets a branch) can no
    # longer slip past the softer "only if it looks started" heuristic below. `keepers_exist` is the one
    # thing that keeps this safe to force unconditionally: a pile with NO keepers at all (every chat
    # tossed/parked) has nothing to type and earns no place in the tree, so it must not be forced through
    # `coalesce`/a folder_branch it can never satisfy — that would brick every all-toss pile the instant
    # the flag went unconditional, the same class of mistake [SL-16] already names.
    if status == "read-complete":
        typed, untyped = world_map_state(basket, work_dir)
        keepers_exist = any(r.get("skim_verdict") == "research" for _k, r in _basket_chats(m, basket))
        started = bool(b.get("folder_branch")) or typed > 0
        if keepers_exist and (require_world_map or started):
            if untyped:
                return False, (f"REFUSED: basket '{basket}' has {len(untyped)} finding(s) with no human-chosen "
                               f"type — the world map was started for this pile, so closing now would carry "
                               f"half a ruling into PHASE 4. Type each one "
                               f"({'/'.join(FINDING_TYPES)}): {untyped[:3]}{'…' if len(untyped) > 3 else ''}")
            if untyped is None and require_world_map:
                return False, (f"REFUSED: basket '{basket}' has no coalesced findings to type — run "
                               f"'pipeline.py coalesce' before closing the world map.")
            if not b.get("folder_branch"):
                return False, (f"REFUSED: basket '{basket}' has no folder_branch — PHASE 3 records the folder "
                               f"shape this pile earned so PHASE 4 places it instead of redesigning the tree "
                               f"from scratch. Set it: pipeline.py folder-branch --basket '{basket}' --branch '<path>'")
    b["basket_status"] = status
    if status in ("skim-complete", "read-complete", "committed"):
        b["basket_lock"] = None   # release on a clean rung completion
    return True, "ok"


# ── 10.2.1 — THE BRAIN ROOT: asked once, remembered forever (the author 2026-08-08) ────────────────────
# "It's got to be pointed at a specific folder at the very beginning… that needs to be recorded inside
# the skill, and remembered into the future. So when it gets used on an ongoing basis, it's not throwing
# all the files that come out of it in some random place." Before this, the drivers GUESSED the root by
# globbing a cloud-drive path — fine for its original author, wrong for
# anyone on Dropbox, OneDrive, or a plain local folder. This is a REMEMBERED DECISION, not a parameter.
#
# Resolution order, exactly: (1) $LIFEHACK_ROOT, if set and a real directory. (2) the persisted file
# ~/.config/lifehack/brain-root — this system's EXISTING config home (sentinel-paused-sources and
# claude-oauth-token already live there; this is not a second location). (3) the legacy Drive glob —
# BACK-COMPAT ONLY, set via INGEST_LEGACY_ROOT_GLOB, so an existing corpus keeps resolving. (4) otherwise
# NOT-SET. Closed outcome set {RESOLVED, NOT-SET}; NOT-SET is the no-outcome member and must NEVER fall
# through to a guess, a default, or the cwd — every caller checks for it and stops, naming the fix.
# ⬇ THE IMPLEMENTATION MOVED (migration T0.1, 2026-08-11) to <repo>/shared/brain_root.py — the one
# root variable the WHOLE system resolves through, not just this pipeline. The contract above is
# unchanged; the code is imported so there is exactly one copy of it, and every other tool gets the
# same answer this pipeline gets.
_SHARED_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "shared"))
if _SHARED_DIR not in sys.path:
    sys.path.insert(0, _SHARED_DIR)
try:
    from brain_root import (BRAIN_ROOT_ENV, BRAIN_ROOT_CONFIG, BRAIN_ROOT_LEGACY_GLOB,
                            resolve_brain_root, set_brain_root)
except ImportError as _brain_root_err:   # fail LOUD, never degrade — without the resolver every write is a guess
    sys.exit("FATAL: cannot import brain_root from %s — the data-root resolver is missing. "
             "Fix: restore <repo>/shared/brain_root.py. (%s)" % (_SHARED_DIR, _brain_root_err))

# ⬇ THE MACHINE-SHAPED PATHS (2026-08-12). `--map` used to be reconstructed in shell by every skill
# and passed back in. It is derivable from the brain root and the corpus slug, so it is a DEFAULT
# now, not a required argument — which is what lets a skill's command block be a bare invocation
# with no shell variables in it, and therefore run under PowerShell as well as bash.
try:
    import paths as _paths
except ImportError as _paths_err:        # same discipline as above: loud, never a guessed fallback
    sys.exit("FATAL: cannot import paths from %s — the path resolver is missing. "
             "Fix: restore <repo>/shared/paths.py. (%s)" % (_SHARED_DIR, _paths_err))


def main():
    ap = argparse.ArgumentParser(description="shared brain for the ingest-1..4 chain")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a1 = sub.add_parser("assert"); a1.add_argument("--map")
    a2 = sub.add_parser("next"); a2.add_argument("--map")
    ph = sub.add_parser("phase"); ph.add_argument("--map")
    a3 = sub.add_parser("suggest"); a3.add_argument("--map")
    a3.add_argument("--skill", required=True); a3.add_argument("--basket")
    a4 = sub.add_parser("lock"); a4.add_argument("--map"); a4.add_argument("--basket", required=True)
    a4.add_argument("--machine", required=True); a4.add_argument("--skill", required=True)
    a4.add_argument("--now"); a4.add_argument("--ttl", type=int, default=1800)
    a5 = sub.add_parser("unlock"); a5.add_argument("--map"); a5.add_argument("--basket", required=True)
    sc = sub.add_parser("scan"); sc.add_argument("--map"); sc.add_argument("--file", required=True)
    sc.add_argument("--guess", help="machine best-guess: toss | research | park (a HINT, not the ruling)")
    sc.add_argument("--summary", default="", help="the gate-sanitized one-line gist"); sc.add_argument("--now")
    sk = sub.add_parser("skim"); sk.add_argument("--map"); sk.add_argument("--file", required=True)
    sk.add_argument("--verdict", required=True, help="toss | research | park | explore")
    sk.add_argument("--note", default="")
    sk.add_argument("--human-approved", action="store_true", help="REQUIRED for toss/park (they close the chat) — NOT needed for explore (closes nothing)"); sk.add_argument("--now")
    rd = sub.add_parser("read"); rd.add_argument("--map"); rd.add_argument("--file", required=True)
    rd.add_argument("--extraction"); rd.add_argument("--deep", action="store_true"); rd.add_argument("--now")
    cm = sub.add_parser("commit-mark"); cm.add_argument("--map"); cm.add_argument("--file", required=True); cm.add_argument("--now")
    fl = sub.add_parser("flag"); fl.add_argument("--map"); fl.add_argument("--file", required=True)
    fl.add_argument("--canon", choices=["true", "false"], help="DEEP-READ level-2: mark a canon-CANDIDATE (→ level-3 full read)")
    fl.add_argument("--pointer", choices=["true", "false"], help="DEEP-READ level-2: mark a big-but-only-a-record chat (→ pointer-ize, no full read)")
    gi = sub.add_parser("giant"); gi.add_argument("--map"); gi.add_argument("--file", required=True)
    gi.add_argument("--sampled", choices=["true", "false"], help="DEEP-READ: this keeper was over the whole-read ceiling → SAMPLED head+tail (miner sets)")
    gi.add_argument("--ruled", choices=["true", "false"], help="the HUMAN's say-go that they saw it was sampled (unblocks the done-gate; needs --human-approved)")
    gi.add_argument("--human-approved", action="store_true", help="REQUIRED for --ruled true (only the human rules a sampled giant)")
    sc = sub.add_parser("sort-confirm", help="PHASE 1 CLOSE: the human has ruled the basket boundaries (the gate current_phase() reads)")
    sc.add_argument("--map")
    sc.add_argument("--human-approved", dest="human_approved", action="store_true",
                    help="REQUIRED — only the human closes SORT; the miner can never set this")
    sc.add_argument("--now")
    bs = sub.add_parser("basket-status"); bs.add_argument("--map"); bs.add_argument("--basket", required=True); bs.add_argument("--status", required=True)
    bs.add_argument("--work", help="work dir holding raw-conclusions-<basket>.json — the READER EVIDENCE the "
                                   "read-complete gate reads (defaults to $COWORK_WORK)")
    bs.add_argument("--require-world-map", dest="require_world_map", action="store_true",
                    help="force the PHASE 3 world-map gate (every finding typed + a folder_branch set) even if "
                         "this pile never started one — the switch Phase 3's driver flips when it ships")
    fb = sub.add_parser("folder-branch", help="PHASE 3: record the folder shape this pile earned (PHASE 4 reads it)")
    fb.add_argument("--map"); fb.add_argument("--basket", required=True)
    fb.add_argument("--branch", required=True, nargs="+",
                    help="one or more folder paths this pile earned — pass SEVERAL space-separated when "
                         "propose_folder_shape() legitimately returned more than one (e.g. a nested subject "
                         "AND a sibling); a single value still works exactly as before ([5.1.1], 2026-08-11)")
    ft = sub.add_parser("finding-type", help=f"PHASE 3: the human's ruling on ONE finding ({'/'.join(FINDING_TYPES)})")
    ft.add_argument("--basket", required=True); ft.add_argument("--file", required=True)
    ft.add_argument("--index", type=int, required=True); ft.add_argument("--type", required=True, choices=list(FINDING_TYPES))
    ft.add_argument("--work", help="work dir holding raw-conclusions-<basket>.json (defaults to $COWORK_WORK)")
    wm = sub.add_parser("world-map-state", help="PHASE 4 reads this: the pile's folder branch + how many findings are typed")
    wm.add_argument("--map"); wm.add_argument("--basket", required=True)
    wm.add_argument("--work", help="work dir holding raw-conclusions-<basket>.json (defaults to $COWORK_WORK)")

    # ── §9.6 THE WORLD MAP — TURN 1 (the paragraph) ─────────────────────────────────────────────
    wmm = sub.add_parser("worldmap-material", help="9.6.1 TURN 1's INPUT: every staged finding in this "
                         "pile, for the model to compose the world-map paragraph FROM (never authored by code)")
    wmm.add_argument("--basket", required=True); wmm.add_argument("--work", help="defaults to $COWORK_WORK")
    wmc = sub.add_parser("worldmap-check", help="9.6.1's CHECK: required title, 1-4 paragraphs, zero bullet "
                         "characters — AND, when the pile's material is reachable, that every distinctive "
                         "term in the paragraph actually appears in it (the fabrication check)")
    wmc.add_argument("--basket", required=True); wmc.add_argument("--file", required=True,
                     help="path to the model's rendered paragraph text")
    wmc.add_argument("--work", help="defaults to $COWORK_WORK; used to load the pile's material for the "
                     "containment check")
    wmc.add_argument("--no-containment", action="store_true",
                     help="shape-only. ⛔ Says so LOUDLY in the output — an unchecked paragraph is not a "
                     "verified one")

    # ── §9.6 TURNS 2-4 (the paginated per-type approvals) ───────────────────────────────────────
    wmt = sub.add_parser("worldmap-turns", help="9.6.2: group this pile's findings into approval turns, "
                         "priority order canonical->dated->record, paginated at ~page-size")
    wmt.add_argument("--basket", required=True); wmt.add_argument("--work", help="defaults to $COWORK_WORK")
    wmt.add_argument("--page-size", type=int, default=10)

    # ── §9.6 TURN 3 (the re-render) ──────────────────────────────────────────────────────────────
    wms = sub.add_parser("worldmap-save", help="9.6.3: persist the current rendered paragraph + a short "
                         "version history, so the next render can prove it actually changed")
    wms.add_argument("--basket", required=True); wms.add_argument("--file", required=True)
    wms.add_argument("--work", help="defaults to $COWORK_WORK"); wms.add_argument("--note"); wms.add_argument("--now")
    wmd = sub.add_parser("worldmap-diff", help="9.6.3's GATE: refuses if the re-rendered paragraph is "
                         "identical to the prior saved version; otherwise prints the unified diff")
    wmd.add_argument("--basket", required=True); wmd.add_argument("--file", required=True,
                     help="path to the NEW rendered paragraph text")
    wmd.add_argument("--work", help="defaults to $COWORK_WORK")

    # ── §9.6 every approval turn's reply (9.6.4) ────────────────────────────────────────────────
    tr = sub.add_parser("turn-outcome", help="9.6.4: MEMBERSHIP CHECK on the move the MODEL read out of the "
                        "human's reply — APPROVE|NOTE_AND_MOVE_ON|REFINE_AND_REPEAT|NO_OUTCOME. The model "
                        "does the reading (meaning); this only refuses anything off-list, so an "
                        "unclassified reply can never be promoted to APPROVE")
    tr.add_argument("--value", required=True, help="the move the model read, one of the four members")

    # ── §9.6 TURN 5 (the folder shape, both halves of the split test) ──────────────────────────
    fs = sub.add_parser("folder-shape", help="9.6.5: lay out this pile's folder shape from the human/model's "
                        "subject clusters — too BIG subdivides (nests), too DIVERSE separates (siblings)")
    fs.add_argument("--basket", required=True)
    fs.add_argument("--subjects", required=True, help='JSON list: [{"name","item_count","relation":'
                    '"core"|"diverse"}, …] — relation is the semantic call; this only lays out the paths')
    fs.add_argument("--page-size", type=int, default=10)

    bl = sub.add_parser("basket-list"); bl.add_argument("--map"); bl.add_argument("--basket", required=True)
    bl.add_argument("--research", action="store_true", help="only skim_verdict=research (the chats going to DEEP-READ)")
    bl.add_argument("--keepers-only", action="store_true", help="alias of --research")
    bl.add_argument("--unscanned", action="store_true", help="SCAN: chats needing a slice-read (no gist yet, unruled)")
    bl.add_argument("--scanned", action="store_true", help="SCAN: chats WITH a gist, awaiting the human's ruling")
    bl.add_argument("--explore", action="store_true", help="SCAN: chats the human sent back for a wider second look (skim_verdict=explore) — the stack to re-scan wider and re-rule")
    bl.add_argument("--unskimmed", action="store_true"); bl.add_argument("--all", action="store_true")
    bl.add_argument("--files-only", dest="files_only", action="store_true", help="print ONLY the file keys, one per line (safe to read into a shell array — no parsing)")
    an = sub.add_parser("anchor"); an.add_argument("--map"); an.add_argument("--phase", required=True); an.add_argument("--basket"); an.add_argument("--out", required=True)
    pr = sub.add_parser("progress"); pr.add_argument("--map"); pr.add_argument("--just-did", dest="just_did"); pr.add_argument("--next", dest="next_action")
    hu = sub.add_parser("hud"); hu.add_argument("--map")                       # F2.2: the one-line statusline HUD
    hg = sub.add_parser("hud-grid"); hg.add_argument("--map"); hg.add_argument("--active")  # the multi-line screen grid
    br = sub.add_parser("brain"); br.add_argument("--map")                     # F2.3: the mined/filed/canon tally
    rf = sub.add_parser("reflect"); rf.add_argument("--map"); rf.add_argument("--basket", required=True)
    rf.add_argument("--in", dest="infiles", nargs="+", required=True, help="raw-conclusions JSON file(s) for this basket")
    rf.add_argument("--since", help="ISO ts: rows read/committed at-or-after this are 🆕 NEW this round")
    rf.add_argument("--brain-before", dest="brain_before", type=int, help="the mined count BEFORE this basket (for 'brain grew N→M')")
    rf.add_argument("--next-basket", dest="next_basket", help="the next basket name (for the action bar)")
    co = sub.add_parser("coalesce")                                                          # F5.3: the reader→review seam
    co.add_argument("--dir", required=True, help="the dir agent_output.py wrote agent-<label>.json into")
    co.add_argument("--out", required=True, help="the single raw-conclusions-<basket>.json conclusions_review.py reads")
    sv = sub.add_parser("salvage"); sv.add_argument("--map"); sv.add_argument("--basket", required=True); sv.add_argument("--raw", required=True); sv.add_argument("--out", required=True)
    rs = sub.add_parser("rescan"); rs.add_argument("--map"); rs.add_argument("--basket", required=True)
    hs = sub.add_parser("hash"); hs.add_argument("--map"); hs.add_argument("--flat-dir", required=True)
    rl = sub.add_parser("relink"); rl.add_argument("--map"); rl.add_argument("--flat-dir", required=True)
    bw = sub.add_parser("pad-init", help="PHASE 1 → scratchpad seam: create memory/<corpus>/scratchpad.md "
                        "seeded with PHASE 1's pile boundaries, or APPEND this sitting's entry if it exists")
    bw.add_argument("--map")
    bw.add_argument("--corpus-id", dest="corpus_id", help="explicit corpus slug; if omitted, resolved from "
                    "the --map path's own shape (.../projects/<corpus>/work/<file>.json), then "
                    "$INGEST_CORPUS, then REFUSED — NEVER from the map's `source` field (that names the "
                    "tag file the map was built from, not the corpus)")
    bw.add_argument("--root", dest="root", help="the brain folder the human named "
                    "(memory/<corpus-id>/scratchpad.md is written under it); omit for --dry-run only")
    bw.add_argument("--notes", help="free text, or @<path> to read it from a file — the human's "
                    "split/merge/close ruling narrative from the SORT turn")
    bw.add_argument("--entry", help="free text to APPEND when the pad already exists (a later sitting)")
    bw.add_argument("--basket", help="write to THIS pile's own pad (memory/<corpus>/<basket>/scratchpad.md). "
                    "Omit at PHASE 1 close to create one pad per pile in a single call.")
    bw.add_argument("--now")
    bw.add_argument("--dry-run", dest="dry_run", action="store_true",
                    help="print exactly what would be written; never touches disk, never sets pad_written")
    tc = sub.add_parser("topic-check", help="fail-closed membership check for a written `topic:` value "
                        "against the person's own CLOSED vocabulary (memory/topic-vocab.md)")
    tc.add_argument("--topics", nargs="+", required=True,
                    help="one or more topic slugs to validate (topic: is a LIST in practice)")
    tc.add_argument("--vocab", dest="vocab_path", help="explicit path to the topic vocabulary; defaults to <brain root>/memory/topic-vocab.md (theirs), then the legacy in-repo copy")
    ci = sub.add_parser("corpus-inherit-offered", help="ONCE-PER-RUN flag: the PHASE 2 inheritance offer "
                        "(`2.0c`) has been shown to the human — stops it re-asking on every pile")
    ci.add_argument("--map")
    ci.add_argument("--now")
    ci.add_argument("--check", action="store_true",
                    help="just report whether it's already been offered (exit 0=yes, 1=not yet); "
                         "without this flag, SETS the flag")
    brt = sub.add_parser("brain-root", help="10.2.1: resolve/persist the destination root /ingest writes "
                         "into — asked once, remembered forever, never guessed")
    brt.add_argument("--set", dest="set_path", default=None,
                     help="record this path as the brain root (persists to " + BRAIN_ROOT_CONFIG + ")")
    brt.add_argument("--create", action="store_true",
                     help="with --set, create the path (parents included) if it doesn't exist")
    brt.add_argument("--quiet", action="store_true",
                     help="print ONLY the resolved path (for a shell to consume), or nothing + exit 1")
    a = ap.parse_args()

    # ── `--map` DEFAULTS INSTEAD OF BEING REQUIRED (2026-08-12) ──────────────────────────────────
    # Passing it explicitly still wins, so nothing that already supplies it changes behaviour. When
    # it is omitted we derive it — the same value the ten shell preambles used to build by hand.
    # ⛔ If the brain root is NOT-SET we STOP and name the fix. We do NOT fall back to the cwd or to
    # a default folder: writing someone's notes somewhere they did not choose is the exact failure
    # the resolver chain exists to prevent, and swallowing it here would hide it one level deeper.
    if getattr(a, "map", None) is None and hasattr(a, "map"):
        a.map = _paths.corpus_map()
        if a.map is None:
            sys.exit("STOP: no brain root is set, so there is nowhere to read or write.\n"
                     "      Set it with:  %s %s --set \"<the folder they named>\" [--create]"
                     % (_paths.interpreter(), os.path.join(_SHARED_DIR, "brain_root.py")))

    if a.cmd == "assert":
        # DURABILITY GUARD: a Drive conflict-copy next to the map = split-brain state → HALT before any skill reads.
        dupes = conflict_copies(a.map)
        if dupes:
            print("CONFLICT-COPY DETECTED — refusing to proceed (two corpus-maps = split state):")
            for d in dupes:
                print(f"  - {d}")
            print("Resolve: keep the real map, delete/rename the conflict copy, then re-run.")
            sys.exit(1)
        m = load(a.map)
        problems = assert_schema(m)
        if problems:
            print("SCHEMA ASSERT FAILED:")
            for p in problems:
                print(f"  - {p}")
            sys.exit(1)
        print(f"OK: corpus map is schema v{SCHEMA_VERSION} ({len(rows_of(m))} chats, {len(baskets_of(m))} baskets).")
    elif a.cmd == "hash":
        m = load(a.map)
        n = populate_hashes(m, a.flat_dir)
        _save(m, a.map)
        print(f"OK hash: bookmarked {n} new chat(s) by content-hash (re-export durable).")
    elif a.cmd == "relink":
        m = load(a.map)
        links = relink(m, a.flat_dir)
        _save(m, a.map)
        if links:
            print(f"OK relink: re-keyed {len(links)} row(s) to their new filenames after a re-export:")
            for old, new in links[:10]:
                print(f"  {old} → {new}")
        else:
            print("OK relink: nothing to re-link (all rows resolve, or no matching hashes).")
    elif a.cmd == "next":
        nb = next_basket(load(a.map))
        print(nb if nb else "DONE")
    elif a.cmd == "phase":
        ph, nb = current_phase(load(a.map))
        print(f"{ph}|{nb or ''}")
    elif a.cmd == "suggest":
        print(suggest_next(load(a.map), a.skill, a.basket))
    elif a.cmd == "basket-list":
        m = load(a.map)
        pred = None
        if a.research or a.keepers_only:
            pred = lambda r: r.get("skim_verdict") == "research"   # DEEP-READ: the gold flagged for a deep read
        elif a.unscanned:
            pred = _unscanned                                      # SCAN read step: chats still needing a slice-read
        elif a.scanned:
            pred = _scanned_unruled                                # SCAN ruling step: gist ready, human hasn't ruled
        elif a.explore:
            pred = _in_explore                                     # the EXPLORE stack: re-scan wider, then re-rule
        elif a.unskimmed:
            pred = lambda r: r.get("skim_verdict") is None         # any un-ruled chat (scanned or not)
        if a.files_only:                                            # bare keys, one per line — for a shell array
            keys = [k for k, r in basket_chats(m, a.basket)
                    if (a.all or r.get("resolution_rung") != "committed") and (pred is None or pred(r))]
            print("\n".join(keys))
        else:
            lines = basket_list(m, a.basket, pred, include_done=a.all)
            print("\n".join(lines) if lines else "(no chats left to process in this basket)")
    elif a.cmd == "anchor":
        frame = compose_anchor(a.phase, a.basket)
        with open(a.out, "w") as f:
            f.write(frame)
        print(f"OK anchor: phase {a.phase} basket {a.basket!r} → {a.out} ({len(frame)} chars)")
    elif a.cmd == "progress":
        print(compose_progress(load(a.map), a.just_did, a.next_action))
    elif a.cmd == "hud":
        print(compose_statusline_hud(load(a.map)))
    elif a.cmd == "hud-grid":
        print("\n".join(compose_basket_hud(load(a.map), active=a.active)))
    elif a.cmd == "brain":
        print(json.dumps(brain_count(load(a.map))))
    elif a.cmd == "reflect":
        m = load(a.map)
        # reuse conclusions_review's tolerant loader shape: each file = an array OR a per-chat obj
        conclusions = []
        for pth in a.infiles:
            d = json.load(open(pth))
            if isinstance(d, dict):
                d = [d] if ("file" in d and "conclusions" in d) else (d.get("conclusions") or d.get("items") or [])
            for el in d:
                conclusions.extend(el if isinstance(el, list) else [el])
        print(compose_reflection(m, a.basket, conclusions, a.since, a.brain_before, a.next_basket))
    elif a.cmd == "rescan":
        m = load(a.map)
        n = reset_scan(m, a.basket)
        _save(m, a.map)
        print(f"OK rescan: cleared {n} un-ruled summary(ies) in '{a.basket}' — the next SCAN pass will re-summarize them.")
    elif a.cmd == "coalesce":
        # No map load — this is a pure file op at the reader→review seam (F5.3).
        ok, msg, stats = coalesce_conclusions(a.dir, a.out)
        if not ok:
            print(f"COALESCE FAIL: {msg}")
            sys.exit(1)
        print(f"OK coalesce: {msg}")
        # A chat that came back with no conclusion CONTENT is not a warning to scroll past — it is the
        # thing the read-complete gate will refuse on. Name them here, where the operator is still looking.
        if stats.get("empty"):
            print(f"   ⚠ these chats have NO conclusion content and will BLOCK read-complete: {stats['empty']}")
    elif a.cmd == "salvage":
        m = load(a.map)
        ok, msg = do_salvage(m, a.basket, a.raw, a.out)
        if not ok:
            print(f"SALVAGE FAIL: {msg}")
            sys.exit(1)
        _save(m, a.map)
        print(f"OK salvage: {a.basket} — {msg}")
    elif a.cmd == "lock":
        m = load(a.map)
        ok, msg = acquire_lock(m, a.basket, a.machine, a.skill, a.now, a.ttl)
        if not ok:
            print(f"LOCK FAIL: {msg}")
            sys.exit(1)
        _save(m, a.map)
        print(f"LOCK OK ({msg}): {a.basket}")
    elif a.cmd == "unlock":
        m = load(a.map)
        release_lock(m, a.basket)
        _save(m, a.map)
        print(f"UNLOCKED: {a.basket}")
    elif a.cmd == "folder-branch":
        m = load(a.map)
        ok, msg = set_folder_branch(m, a.basket, a.branch)
        if not ok:
            print(f"FAIL folder-branch: {msg}")
            sys.exit(1)
        _save(m, a.map)
        print(f"OK folder-branch: {a.basket} — {msg}")
    elif a.cmd == "finding-type":
        ok, msg = set_finding_type(getattr(a, "work", None), a.basket, a.file, a.index, a.type)
        if not ok:
            print(f"FAIL finding-type: {msg}")
            sys.exit(1)
        print(f"OK finding-type: {msg}")
    elif a.cmd == "world-map-state":
        m = load(a.map)
        b = baskets_of(m).get(a.basket) or {}
        typed, untyped = world_map_state(a.basket, getattr(a, "work", None))
        branches = folder_branches(b)   # ADDITIVE reader (5.1.1) — handles a legacy bare string or a richer list
        print(f"basket: {a.basket}")
        if not branches:
            print("folder_branch: — NOT SET (PHASE 4 would have to redesign the tree)")
        elif len(branches) == 1:
            print(f"folder_branch: {branches[0]}")
        else:
            print(f"folder_branch ({len(branches)} branches): " + ", ".join(branches))
        if untyped is None:
            print("findings: no coalesced evidence yet (run: pipeline.py coalesce)")
        else:
            print(f"findings typed: {typed}  ·  untyped: {len(untyped)}"
                  + (f" → {untyped[:5]}{'…' if len(untyped) > 5 else ''}" if untyped else ""))
    elif a.cmd == "worldmap-material":
        path, findings = worldmap_material(a.basket, getattr(a, "work", None))
        if not findings and not (path and os.path.exists(path)):
            print(f"NO EVIDENCE: no coalesced findings for '{a.basket}' yet "
                  f"(expected {path or 'raw-conclusions-<basket>.json'}) — run 'pipeline.py coalesce' first.")
            sys.exit(1)
        print(json.dumps({"basket": a.basket, "title": world_map_title(a.basket), "findings": findings}, indent=1))
    elif a.cmd == "worldmap-check":
        text = open(a.file).read()
        material = None
        if not getattr(a, "no_containment", False):
            try:
                _mpath, findings = worldmap_material(a.basket, getattr(a, "work", None))
                material = " ".join(str(f.get("text", "")) for f in (findings or []))
                if not material.strip():
                    material = None
                    print("⚠ this pile has NO staged material — nothing to check the paragraph against. "
                          "SHAPE ONLY, and that is not a pass.")
            except Exception as e:
                print("⚠ could not load the pile's material for the containment check (%s) — "
                      "falling back to SHAPE ONLY. That is not a pass." % e)
        ok, msg = check_world_map_paragraph(text, a.basket, material)
        print(msg)
        if not ok:
            sys.exit(1)
    elif a.cmd == "worldmap-turns":
        _, findings = worldmap_material(a.basket, getattr(a, "work", None))
        turns = plan_approval_turns(findings, a.page_size)
        counts = {"canonical": 0, "dated": 0, "record": 0}
        for f in findings:
            counts[_finding_group(f)] += 1
        print(json.dumps({"basket": a.basket, "counts": counts, "total": len(findings), "turns": turns}, indent=1))
    elif a.cmd == "worldmap-save":
        text = open(a.file).read()
        ok, msg = worldmap_save_paragraph(a.basket, text, getattr(a, "work", None), a.note, a.now)
        print(msg)
        if not ok:
            sys.exit(1)
    elif a.cmd == "worldmap-diff":
        new_text = open(a.file).read()
        ok, msg, diff = worldmap_diff_paragraph(a.basket, new_text, getattr(a, "work", None))
        print(msg)
        if diff:
            print(diff)
        if not ok:
            sys.exit(1)
    elif a.cmd == "turn-outcome":
        ok, _val, msg = validate_turn_outcome(a.value)
        print(msg)
        if not ok:
            sys.exit(1)
    elif a.cmd == "folder-shape":
        try:
            subjects = json.loads(a.subjects)
        except Exception as e:
            print(f"FAIL folder-shape: --subjects is not valid JSON ({e})")
            sys.exit(1)
        proposal = propose_folder_shape(a.basket, subjects, a.page_size)
        print(json.dumps({"basket": a.basket, "proposal": proposal}, indent=1))
    elif a.cmd == "sort-confirm":
        # PHASE 1's done-condition. Refuses without --human-approved: the gate exists precisely because
        # the miner must not be able to declare the human's ruling turn finished (LAW 3).
        if not a.human_approved:
            print("FAIL sort-confirm: closing SORT is the HUMAN's ruling, so it REQUIRES --human-approved. "
                  "Show them every basket (basket_review.py summary) and let them toss/split/merge FIRST.")
            sys.exit(1)
        m = load(a.map)
        if not baskets_of(m):
            print("FAIL sort-confirm: this map has NO baskets yet — there is nothing for the human to have ruled.")
            sys.exit(1)
        m["sort_confirmed"] = {"at": a.now or _now_iso(), "by": "human"}
        _save(m, a.map)
        print(f"OK sort-confirm: SORT closed by the human over {len(baskets_of(m))} basket(s) — "
              f"/ingest now advances to SCAN.")
    elif a.cmd == "pad-init":
        m = load(a.map)
        # ⛔ NEVER `_slugify(m.get("source") or "corpus")` — `source` names the TAG FILE the map was built
        # from, not the corpus, and that silent guess wrote pads to a folder nothing reads
        # (`memory/world-tags/...`). resolve_corpus_id() REFUSES instead of guessing (D1.2.1).
        corpus_id, corpus_source = resolve_corpus_id(a.corpus_id, a.map)
        if corpus_id is None:
            print(f"REFUSED pad-init: {corpus_source}")
            sys.exit(1)
        notes = a.notes
        if notes and notes.startswith("@"):
            notes = open(notes[1:]).read()
        entry = a.entry
        if entry and entry.startswith("@"):
            entry = open(entry[1:]).read()
        # No --basket and no --entry => PHASE 1 close: one pad per pile, in one call.
        if not a.basket and not entry:
            results, refused = pad_init_all(m, corpus_id, a.root, now_iso=a.now, notes=notes,
                                            dry_run=a.dry_run)
            for b, outcome, path in results:
                print(f"  {outcome:<9} {'(corpus)' if b is None else b:<28} → {path}")
            if refused:
                for b, detail in refused:
                    print(f"REFUSED pad-init [{b or '(corpus)'}]: {detail}")
                sys.exit(1)
            if a.dry_run:
                sys.exit(0)
            mark_pad_written(m, corpus_id, results[0][2], a.now)
            _save(m, a.map)
            print(f"OK pad-init: {len(results)} pad(s) — one per pile, plus the corpus pad "
                  f"(corpus_id={corpus_id} via {corpus_source}; m['pad_written'] set — PHASE 2 unblocks)")
            sys.exit(0)
        outcome, path, detail = pad_write(m, corpus_id, a.root, now_iso=a.now, notes=notes,
                                          entry=entry, dry_run=a.dry_run, basket=a.basket)
        if outcome == "REFUSED":
            print(f"REFUSED pad-init: {detail}")
            sys.exit(1)
        if a.dry_run:
            rel = os.path.join("memory", corpus_id, a.basket or "", "scratchpad.md")
            print(f"DRY-RUN pad-init: WOULD {outcome} → {path or rel}"
                  + ("" if a.root else "  (pass --root for the absolute path)"))
            print("─" * 60)
            print(detail)
            sys.exit(0)
        mark_pad_written(m, corpus_id, path, a.now)
        _save(m, a.map)
        print(f"OK pad-init: {outcome} → {path}  "
              f"(corpus_id={corpus_id} via {corpus_source}; m['pad_written'] set — PHASE 2 unblocks)")
    elif a.cmd == "topic-check":
        ok, bad, vocab = validate_topics(a.topics, vocab_path=a.vocab_path)
        if vocab is None:
            # ⛔ REFUSE, and NAME EVERY PATH TRIED — the same wording folder_scaffold.py prints, because
            # a person hitting one of these two gates must not be taught two different things. A bare
            # "cannot read the vocabulary" sent a real person hunting through a repo for a file that was
            # never supposed to be there.
            resolved, tried = resolve_topic_vocab(a.vocab_path)
            print("REFUSED topic-check: no topic vocabulary found. Looked for, in order:\n"
                  + "\n".join(f"    {p}" for p in tried)
                  + "\n\n  The topic vocabulary is a list of the subject areas YOUR OWN material divides"
                    " into,\n  so it is yours to write and it lives with your notes, not in the tool.\n"
                    "  Create memory/topic-vocab.md with one line per subject:\n\n"
                    "      - `financial`\n      - `health`\n      - `writing`\n\n"
                    "  ⛔ This tool will not invent one for you — an invented taxonomy of your life is"
                    " worse\n     than no taxonomy at all.")
            sys.exit(1)
        if not ok:
            resolved, _tried = resolve_topic_vocab(a.vocab_path)
            print(f"REFUSED topic-check: topic slug(s) not in the closed vocabulary ({resolved}): {bad}. "
                  f"{len(vocab)} slug(s) known. Use an existing slug, or add it there FIRST — this tool "
                  f"never invents one.")
            sys.exit(1)
        print(f"OK topic-check: {a.topics} — all in the closed vocabulary.")
    elif a.cmd == "corpus-inherit-offered":
        m = load(a.map)
        if a.check:
            already = corpus_inherit_offered(m)
            print("ALREADY-OFFERED" if already else "NOT-YET-OFFERED")
            sys.exit(0 if already else 1)
        rec = set_corpus_inherit_offered(m, a.now)
        _save(m, a.map)
        print(f"OK corpus-inherit-offered: recorded at {rec['at']} — /ingest will not re-ask this run.")
    elif a.cmd == "brain-root":
        if a.set_path:
            ok, res = set_brain_root(a.set_path, create=a.create)
            if not ok:
                print(res)
                sys.exit(1)
            verb = "created + " if a.create else ""
            print(f"RESOLVED: {res}  (source: persisted — just {verb}set via --set)")
        else:
            source, path = resolve_brain_root()
            if path is None:
                if getattr(a, "quiet", False):
                    sys.exit(1)
                print("NOT-SET — no $LIFEHACK_ROOT, no persisted " + BRAIN_ROOT_CONFIG + ", and no legacy "
                      "Drive folder found. Fix: pipeline.py brain-root --set <path> (add --create for a new "
                      "folder).")
                sys.exit(1)
            if getattr(a, "quiet", False):
                print(path)
            else:
                print(f"RESOLVED: {path}  (source: {source})")
    elif a.cmd in ("scan", "skim", "read", "commit-mark", "flag", "giant", "basket-status"):
        m = load(a.map)
        if a.cmd == "scan":
            ok, msg = set_scan(m, a.file, a.guess, a.summary, a.now)
        elif a.cmd == "skim":
            ok, msg = set_skim(m, a.file, a.verdict, a.note, a.human_approved, a.now)
        elif a.cmd == "read":
            ok, msg = set_read(m, a.file, a.extraction, a.deep, a.now)
        elif a.cmd == "commit-mark":
            ok, msg = mark_committed(m, a.file, a.now)
        elif a.cmd == "flag":
            canon = None if a.canon is None else (a.canon == "true")
            pointer = None if a.pointer is None else (a.pointer == "true")
            ok, msg = set_flags(m, a.file, canon, pointer)
        elif a.cmd == "giant":
            sampled = None if a.sampled is None else (a.sampled == "true")
            ruled = None if a.ruled is None else (a.ruled == "true")
            ok, msg = set_giant(m, a.file, sampled, ruled, a.human_approved)
        else:
            ok, msg = set_basket_status(m, a.basket, a.status, work_dir=getattr(a, "work", None),
                                        require_world_map=getattr(a, "require_world_map", False))
        if not ok:
            print(f"FAIL: {msg}")
            sys.exit(1)
        _save(m, a.map)
        tgt = getattr(a, "file", None) or a.basket
        print(f"OK {a.cmd}: {tgt}")


if __name__ == "__main__":
    main()

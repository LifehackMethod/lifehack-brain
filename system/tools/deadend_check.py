#!/usr/bin/env python3
"""deadend_check.py — T27.3b. Ask "has this already been tried and failed?" and get an answer.

── THE PROBLEM, MEASURED ────────────────────────────────────────────────────
80 `DO NOT BUILD` entries were harvested on 2026-08-07 into three SOPs — dated, sourced,
structured, and **reachable by nothing**: `grep -rn "DO NOT BUILD" over *.py/*.sh` returned
**zero code readers.** They exist to stop a session rebuilding something already killed, and
the only way to consult them was to already know they were there.

⭐ AND THE DELIVERY MECHANISM THAT EXISTS MAKES IT WORSE, NOT BETTER.
`system/hooks/inject_sop_before_build.sh` already fires on build intent and injects *"STOP and
Read <SOP> in full now."* But it points at a WHOLE FILE — `skill-building-sop.md` is **2,315
lines** — so a session about to rebuild a known dead end is handed a 2,315-line document with
the one line that would stop it buried inside. ⇒ **That is not a delivery problem. It is a
GRANULARITY problem: the rule arrives, but not the rule that matters.** This tool is the
granularity fix, and it is why `§27` rates it the highest-value item in the section.

── WHY THERE IS NO INDEX FILE ──────────────────────────────────────────────
`§27.2` offered "one derived file, or a grep target." **This takes the stricter option: it
searches the SOPs live and stores nothing.** A generated index is a second copy of the truth
and therefore a staleness surface — `T27.1`'s own constraint is *"DERIVED, regenerated every
run. Never hand-edited — a hand-kept index rots and then lies, which is worse than none."* A
file that is never written cannot rot at all. Cost of searching all three sections: single-digit
milliseconds over 3,111 lines. There is nothing to regenerate, nothing to schedule, and no way
for the answer to disagree with the SOP it came from.

── ⛔⛔ THE MOST IMPORTANT BEHAVIOUR IN THIS FILE: A NO-MATCH IS NOT PERMISSION ──
`skill-building-sop.md` §II.4a states its own coverage in its own header: **"this is ~35% of
what's on disk… capped at 80 traceable entries by instruction, not by exhaustion — roughly 150
more traceable dead ends exist unmined. Never read this section as complete — 'not listed here'
is not 'never tried.'"**
⇒ A tool that answers "no match" with silence would convert a 35%-coverage corpus into a
confident green light — **the exact false-green disease this whole project exists to cure, and
it would be introduced BY the tool built to cure it.** So every empty result states the coverage
figure and names where else to look. The clean answer here is "I found nothing, AND I only see a
third of the territory", never "you're clear."

── THE FENCE (§27, ruled 2026-08-07) ───────────────────────────────────────
*"I want to make sure that we're not over-injecting information into the session window… tools
appear only when they're needed."* ⇒ **PULL, NEVER PUSH.** This is a command a session RUNS when
it has a question; it costs zero tokens when not run, and it returns matching entries only —
never the corpus. ⛔ Do not wire this to inject at session start.

Compatible with `/usr/bin/python3` (3.9). Stdlib only.

Usage:
  deadend_check.py "warning-only hook that exits 0"   # has this been tried?
  deadend_check.py --list                             # every entry's one-line gist + source
  deadend_check.py --selftest                         # prove the hit AND the miss path
"""
# ⚖ SHIPPED WITHOUT ITS CALLER (D7, 2026-08-11). The only things that call this are the
# `architect` skill, which lands in a later phase, and a build-time hook that does not ship
# at all. It is here because the ruling is migrate-as-is rather than triage-first — but it
# sits at the tools root rather than beside a skill, because filing it under a skill that
# never calls it would be a worse lie than leaving it unowned. Move it when `architect`
# arrives.

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# The three hosts. It was ruled on 2026-08-07 that this section is DUPLICATED BY DESIGN across them
# (*"I would rather have duplication than miss something"*), and that the copies are NOT required
# to stay identical — each is scoped to its own domain, and `skill-building-sop.md` carries the
# fullest set. ⇒ we search ALL THREE and de-duplicate on the entry text, rather than trusting any
# one of them to be complete. ⛔ Do not "helpfully" narrow this to one file.
SOPS = (
    ("skill-building-sop", REPO / "system" / "sops" / "skill-building-sop.md"),
    ("build-sop",          REPO / "system" / "sops" / "build-sop.md"),
    ("hook-sop",           REPO / "system" / "sops" / "hook-sop.md"),
)

# The section heading varies across the three ("## DO NOT BUILD — …" and
# "## §II.4a — ⭐ DO NOT BUILD — …"), so match on the phrase, not on an exact heading. Loose ON
# PURPOSE: this is the FIND step, and `checkin_open.py`'s lesson applies — a tighter matcher
# trades a visible false positive for a silent false negative, and here a silent miss means a
# dead end goes un-warned.
_SECTION_RE = re.compile(r"^#{1,4}\s.*DO NOT BUILD", re.I)
_NEXT_H2_RE = re.compile(r"^##\s")

# Coverage, quoted from §II.4a's own header rather than asserted here — see the module docstring.
COVERAGE_CAVEAT = (
    "⚠ THIS IS NOT AN ALL-CLEAR. §II.4a states its own coverage: ~35% of what is on disk "
    "(80 traceable entries, capped by instruction not by exhaustion; ~150 more exist unmined). "
    "\"Not listed here\" is NOT \"never tried.\" Also grep the cited records/briefs, "
    "state/debt-ledger.md, and the project brief's ⛔ RULED-OUT bucket before you build."
)

# ⛔⛔ EXTENDED 2026-08-08 AFTER AN ADVERSARIAL ARM MEASURED AN 11/16 HIT RATE (T27.14).
# The five misses shared one shape, and it is the INVERSE of what it looks like: ordinary English
# filler words scored as MAXIMALLY INFORMATIVE, because rarity is measured against THIS corpus and
# this corpus is 117 terse technical bullets. Measured df (entries containing the word, of 117):
#     just = 1 · let = 1 · end = 1 · meet = 2
# ⇒ each was worth ~1.0, the same as a genuinely distinctive term, so a query like *"let's just
# write down how the assistant should sound"* was outranked by unrelated entries that happened to
# contain "just" and "file". **A word can be rare and still carry no intent.** Rarity is a proxy
# for informativeness and it breaks precisely on common words a small corpus happens to omit.
# ⛔ Deliberately NOT the arm's suggested fix (a hard rarity floor): that would also kill a query
# whose ONLY distinctive term is rare — the true-positive case. Removing intent-free words is
# targeted; a floor is blunt and would trade these false negatives for different ones.
_STOP = set("""a an the and or of to in on for with by is are was were be been being it its this that
these those as at from into over under not no do does did done what which when how why if then than
tried failed replaced by use using used make made build built new set get put run
just let lets end ends way ways thing things one two three time times need needs want wants
can could should would may might will shall must have has had own same other another each every
some any all both few more most much many own such only very own here there where who whom
i we you he she they me him her them my our your their his out up down off about again once
like also even still yet ever never always often sometimes really quite rather actually
know knows knew think thinks thought say says said tell tells told see sees saw look looks
add adds adding write writes writing read reads reading work works working try tries
good bad better best worse worst big small large little long short high low fast slow""".split())


def _sections():
    """Yield (sop_name, path, start_line, [lines]) for each DO NOT BUILD section found.

    Reads from the TERRITORY (the files on disk) rather than from any list of what is supposed
    to be there — `build-sop.md`'s completeness rule: *"the denominator must be computed from
    the TERRITORY, not from the document's own list, otherwise the document grades its own
    homework."* A missing/unreadable SOP is skipped and REPORTED, never silently treated as
    empty."""
    out, missing = [], []
    for name, p in SOPS:
        try:
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            missing.append(name)
            continue
        start = None
        for i, ln in enumerate(lines):
            if _SECTION_RE.match(ln):
                start = i
                break
        if start is None:
            missing.append(name)
            continue
        end = len(lines)
        for j in range(start + 1, len(lines)):
            if _NEXT_H2_RE.match(lines[j]) and not _SECTION_RE.match(lines[j]):
                end = j
                break
        out.append((name, p, start, lines[start:end]))
    return out, missing


def entries():
    """Every dead-end entry across all three sections, as dicts.

    ⚠ THE THREE FILES USE THREE DIFFERENT ENTRY FORMATS and that is deliberate (they were
    written for different domains, by different passes):
      · skill-building-sop:  `- **[A7]** Tried: … Failed: … `date` · `source` → replacement`
      · build-sop:           `- **A4 — …** FAILED: … `date` · `source`. REPLACED-BY: …`
      · hook-sop:            `- **Tried:** … → **failed:** … `date` · `source` → replaced by …`
    ⇒ Rather than three brittle per-file regexes (three things to break), an entry is simply a
    top-level `- ` bullet inside the section, continuation lines folded in. The ID is extracted
    when present and left blank when not. **Structure is not required to be uniform for the
    thing to be findable**, and insisting on uniformity here would mean either editing all three
    SOPs or silently dropping whichever format the parser did not anticipate.
    """
    found, seen = [], set()
    secs, missing = _sections()
    for name, p, start, lines in secs:
        cur, cur_ln, group = None, None, ""
        def flush(cur, cur_ln, group):
            if cur is None:
                return
            text = " ".join(cur.split())
            key = re.sub(r"[^a-z0-9 ]", "", text.lower())[:160]
            if key in seen:
                return
            seen.add(key)
            m = re.search(r"\*\*\[?([A-Z]\d+)\]?", text)
            found.append({"sop": name, "path": str(p.relative_to(REPO)),
                          "line": cur_ln, "id": m.group(1) if m else "",
                          "group": group, "text": text})
        for i, ln in enumerate(lines):
            if ln.startswith("### "):
                group = ln[4:].strip()
                continue
            if ln.startswith("- "):
                flush(cur, cur_ln, group)
                cur, cur_ln = ln[2:], start + i + 1
            elif cur is not None and ln.startswith("  ") and ln.strip():
                cur += " " + ln.strip()
            elif cur is not None and not ln.strip():
                flush(cur, cur_ln, group)
                cur, cur_ln = None, None
        flush(cur, cur_ln, group)
    return found, missing


def _stem(w):
    """Crude suffix folding — `named`/`names`/`naming` all collapse to `nam`.

    ⛔ WHY THIS EXISTS, MEASURED. Without it, `name` and `named` were DIFFERENT TOKENS, so the
    query *"give each spawned subagent a NAME"* could not match the entry *"spawned ingest
    readers as NAMED teammates — failed"* — the single most relevant dead end on the board, and
    the one this system has re-learned three times. Instead the top hit was an unrelated
    model-downgrade entry that happened to contain the phrase "Subagent Model Selection". **The
    tool confidently surfaced noise while the real answer sat two lines away, unmatched on a
    letter.** Found by a blind tester who flagged the hit as off-target rather than accepting it.

    ⭐ Deliberately crude, not a real stemmer (no Porter, no library): four suffixes, applied
    longest-first, with a length floor so short words are left alone. It is auditable at a glance
    and its failure mode is a slightly-too-eager merge, which surfaces an extra candidate for a
    human to reject — the safe direction. A proper stemmer would be better and is not worth a
    dependency for a keyword search over 117 bullets.
    """
    for suf in ("ings", "ing", "ies", "ed", "es", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[: -len(suf)]
    return w


def _tokens(s):
    """Tokens, with snake_case identifiers ALSO split into their parts.

    ⛔⛔ THE DEFECT THIS FIXES, MEASURED 2026-08-08 (T27.14). `[a-z0-9_]+` treats `_` as a word
    character, so **`MAX_THINKING_TOKENS` produced exactly ONE token: `max_thinking_tokens`.** A
    builder asking *"can I increase the thinking token budget?"* shares ZERO tokens with it —
    the entry was not merely ranked low, it was **ABSENT from the top 40**, because no overlap
    existed at all. Every identifier in the corpus had this problem: a `snake_case` tool or
    constant name could only ever be matched by someone who already knew how to spell it, which
    defeats the entire purpose of a tool you consult BEFORE you know the entry exists.
    ⇒ Emit BOTH the whole identifier (so an exact mention still scores highly, and scores as one
    rare token) AND its parts (so plain English can reach it). Additive — nothing that matched
    before stops matching.
    """
    out = set()
    for w in re.findall(r"[a-z0-9_]+", s.lower()):
        if w not in _STOP and len(w) > 2:
            out.add(_stem(w))
        if "_" in w:
            for part in w.split("_"):
                if part and part not in _STOP and len(part) > 2:
                    out.add(_stem(part))
    return out


# A match must clear this to be called STRONG. Calibrated against real queries, not invented —
# see `_selftest`'s calibration block, which pins both a known-hit and a known-miss on either
# side of it. Raise it and real dead ends go unflagged; lower it and noise gets a confident label.
STRONG_SCORE = 0.55


def search(query, limit=5):
    """Score every entry against the query by RARITY-WEIGHTED token overlap.

    ⭐ DELIBERATELY DUMB, AND THAT IS THE POINT. Explainable scoring has no hidden failure mode
    and degrades gracefully — a near-miss still surfaces something adjacent for a human to judge.
    A cleverer matcher (embeddings, a tuned regex) trades a visible wrong answer for a silent
    missing one, the trade ruled against on 2026-08-06: *"a visible wrong answer beats an
    invisible missing one."*

    ⛔⛔ WHY RARITY WEIGHTING, AND NOT PLAIN OVERLAP — A BLIND TEST CAUGHT THIS AND THE BUILDER'S
    OWN SELFTEST DID NOT. v1 scored on raw token count, so a query about **"a pink border and
    Comic Sans on the calendar widget"** — deliberately chosen as a CONTROL with no dead end
    behind it — came back with **five confident "matches"**, every one keyword noise
    (`calendar` matched a calendar-hook bug, `add` and `around` matched anything). The builder's
    miss-case test used GIBBERISH (`zzqqx flibbertigibbet`), which has zero overlap and therefore
    proved nothing about the real miss case: an ordinary English question about something simply
    not on the list. ⇒ **the test was written from the same mental model as the code and graded
    its own homework** — `build-sop.md`'s named anti-pattern, hit exactly.
    ⇒ A token is now worth `1/df` (how many entries contain it), so `hook`/`block`/`add` — which
    appear everywhere — count for almost nothing, while `websearch`/`haiku`/`comic` count for a
    lot. Classic inverse document frequency, one line, fully explainable.

    ⛔ WEAK MATCHES ARE LABELLED, NEVER DROPPED. Hiding them would convert a visible false
    positive into an invisible false negative — the exact trade this file refuses everywhere
    else. The caller gets a tier, not a filtered list, and decides for itself.
    """
    q = _tokens(query)
    all_e, missing = entries()

    # document frequency across the corpus — computed from the TERRITORY every run, never a
    # tuned constant, so it self-corrects as entries are added.
    df = {}
    toks = []
    for e in all_e:
        t = _tokens(e["text"] + " " + e["group"])
        toks.append(t)
        for w in t:
            df[w] = df.get(w, 0) + 1

    n = len(all_e) or 1
    scored = []
    for e, t in zip(all_e, toks):
        overlap = q & t
        if not overlap:
            continue
        # rarity-weighted ONLY. ⛔ NOT normalised by query length: dividing by the query size
        # punishes a DETAILED question, and a detailed question is exactly what a session
        # about to build something has. A rare token is worth ~1.0; a token in 50 entries ~0.02.
        score = sum(1.0 / df.get(w, n) for w in overlap)
        # rank the EXPLANATION by rarity too, so "matched on:" names the informative words first
        why = sorted(overlap, key=lambda w: df.get(w, n))
        scored.append((score, why, e))
    scored.sort(key=lambda t: -t[0])
    return scored[:limit], len(all_e), missing


def _render(query, hits, total, missing, limit):
    out = []
    if missing:
        # A source we could not read is NEVER silently an empty source.
        out.append(f"⛔ UNREAD SOURCE(S): {', '.join(missing)} — this answer is INCOMPLETE.")
    strong = [h for h in hits if h[0] >= STRONG_SCORE]
    if not hits:
        out.append(f'NO MATCH for "{query}" across {total} recorded dead ends.')
        out.append(COVERAGE_CAVEAT)
        return "\n".join(out)
    if not strong:
        # ⛔ SAY IT PLAINLY. v1 printed "N possible match(es)" here and a blind tester read five
        # pieces of keyword noise as findings. A weak tier that is not LABELLED weak is a false
        # positive wearing a verdict.
        out.append(f'⚠ NO STRONG MATCH for "{query}" (of {total} recorded dead ends).')
        out.append("The entries below share only COMMON words and are probably noise — "
                   "skim them, do not treat them as findings.")
    else:
        out.append(f'{len(strong)} STRONG match(es) for "{query}" '
                   f'(of {total} recorded dead ends) — read these before you build:')
    for score, why, e in hits:
        ident = f"[{e['id']}] " if e["id"] else ""
        tier = "STRONG" if score >= STRONG_SCORE else "weak"
        out.append("")
        out.append(f"  [{tier}] {ident}{e['path']}:{e['line']}  ·  "
                   f"matched on: {', '.join(why[:6])}")
        if e["group"]:
            out.append(f"    under: {e['group']}")
        out.append(f"    {e['text'][:420]}")
    out.append("")
    out.append(COVERAGE_CAVEAT)
    return "\n".join(out)


CENSUS = (Path(__file__).resolve().parents[2] / "system" / "organism" / "generated"
          / "capability-census.md")


def _artifacts():
    """Derived artifacts already on disk, read from the census `T27.15` publishes.

    ⭐⭐ WHY THIS SOURCE HAD TO EXIST — the measurement that created `T27.16`. Everything above
    searches PROSE ABOUT FAILURES: 117 `DO NOT BUILD` bullets across three SOPs. **The thing a
    session came one turn from rebuilding on 2026-08-08 was not a failure anyone had written
    about — it was a FILE.** `inventory-2026-07-16.jsonl`, 481 records, generated by nothing and
    read by nothing. This tool could not see it, because an artifact is not a dead end until
    somebody writes a paragraph saying so, and nobody ever does.

    ⛔ POINTER AND COUNT, NEVER THE CORPUS — the same fence `T27.3b` carries. This prints a
    handful of rows and the path to the census; it never inlines the census.

    ⚠ **AND IT IS NOT A SECOND COPY OF THE TRUTH** — the concern this module's own header raises
    about generated indexes. The census is regenerated by the WEEKLY job that computes it
    (`T27.1d`), so it cannot drift the way a hand-kept index does. Its generation date is printed
    below so a stale one is visible rather than assumed fresh.
    """
    if not CENSUS.exists():
        # ⛔ DO NOT restore a "run X to generate it" line here without checking X ships in THIS
        # repo. The census and its generator (architecture_reason.py) belong to the private system
        # this tool was lifted from and were never migrated; the old text named that generator, so
        # the one piece of self-repair advice this tool offered was a command that does not exist.
        # Telling someone to run a missing command is worse than telling them nothing: they cannot
        # tell "I typed it wrong" from "it was never here." Found by a path-literal sweep, 2026-08-13.
        return [], None, ("capability-census.md — NOT PART OF THIS REPO. The dead-end search above "
                          "is complete on its own; only the capability half is missing, and there "
                          "is nothing for you to run to produce it.")
    try:
        txt = CENSUS.read_text(encoding="utf-8", errors="replace")
    except OSError as ex:
        return [], None, f"capability-census.md — UNREADABLE ({ex})"
    gen = None
    m = re.search(r"\*\*Generated (\d{4}-\d{2}-\d{2})", txt)
    if m:
        gen = m.group(1)
    rows = []
    for ln in txt.splitlines():
        if ln.startswith("ARTIFACT ") or ln.startswith("ORPHAN "):
            tag, rest = ln.split(None, 1)
            rows.append({"tag": tag, "text": rest.strip()})
    return rows, gen, None


def _artifact_hits(query, limit=5):
    """Same rarity-weighted scoring as the dead-end search, over its own corpus.

    ⛔ Deliberately NOT plain overlap. `search()`'s docstring records why: v1 scored on raw token
    count and a control query with no real answer behind it returned five confident matches of
    pure keyword noise. Reusing the identical scheme means this source inherits that fix instead
    of re-earning it.
    """
    rows, gen, missing = _artifacts()
    if not rows:
        return [], gen, missing
    q = _tokens(query)
    # ⭐⭐ ONE SYNONYM GROUP, AND IT IS THE WHOLE REASON THIS SOURCE EARNS ITS KEEP.
    # MEASURED 2026-08-08 on the plan's own verify query — *"a list of every file in the system
    # and what each one is for"* — which returned two registries and MISSED both files it was
    # written to catch. `inventory-2026-07-16.jsonl` says "inventory"; `organism-map.json` says
    # "map"; the query said "list". **Zero token overlap, so the two artifacts this tool exists
    # to surface were unreachable by the only words a person would actually type.**
    # ⇒ these words all name ONE object in this system, so any of them reaches all of them.
    # ⛔ Deliberately ONE closed group, hand-listed, not a general thesaurus: a broad synonym
    # table would re-open the false-positive problem `search()` already paid to fix. Every member
    # here denotes the same thing — an enumeration of what exists.
    _SAME_THING = {"list", "index", "census", "inventory", "registry", "manifest",
                   "catalog", "catalogue", "enumeration", "map"}
    if q & {_stem(w) for w in _SAME_THING}:
        q = q | {_stem(w) for w in _SAME_THING}
    df, toks = {}, []
    for r in rows:
        t = _tokens(r["text"])
        toks.append(t)
        for w in t:
            df[w] = df.get(w, 0) + 1
    n = len(rows) or 1
    scored = []
    for r, t in zip(rows, toks):
        overlap = q & t
        if not overlap:
            continue
        scored.append((sum(1.0 / df.get(w, n) for w in overlap), r))
    # ⭐ ORPHANS RANK FIRST — a SEMANTIC rule, not a tuned threshold, and the distinction matters.
    # This tool answers "has this already been built?" ⇒ the highest-value row is the one a session
    # would actually REBUILD: an artifact that nothing generates AND nothing reads. A LIVE artifact
    # with a real generator and a real reader is useful context; a DEAD one is the answer.
    # ⛔ It is a tiebreak on TYPE, never a score adjustment — relative scores within each tier are
    # untouched, so this cannot quietly promote a low-relevance row above a high-relevance one of
    # the same kind. (the rule: never bend an input so the output lands where you want it. The
    # legitimate move is to state a PREFERENCE ORDER over kinds; the illegitimate one is to nudge
    # the number until a named case appears.)
    # ⛔ BOTH TIERS ARE RETURNED, AND THAT CORRECTS THIS RULE'S FIRST SHIP (measured 2026-08-08).
    # Sorting orphans-first ALONE filled all 5 slots with dead artifacts and pushed
    # `organism-map.json` — a LIVE one with a real generator and reader — off the list entirely.
    # `§27.15`'s verify demands the dead case AND the live case be provable, and a result that can
    # only ever show one kind cannot answer "does a working version of this already exist?", which
    # is the more common question a session actually has.
    # ⇒ take the best of EACH tier, orphans first. The preference order survives; the blind spot
    # does not.
    orphans = [x for x in scored if x[1]["tag"] == "ORPHAN"]
    live = [x for x in scored if x[1]["tag"] != "ORPHAN"]
    orphans.sort(key=lambda x: -x[0])
    live.sort(key=lambda x: -x[0])
    half = max(1, limit // 2)
    out = orphans[:half] + live[:limit - len(orphans[:half])]
    return out, gen, missing


def _render_artifacts(hits, gen, missing, total):
    out = [""]
    if missing:
        # ⛔ A source we could not read is NEVER silently an empty source — same rule the
        # dead-end path already holds. An absent census must not read as "no artifacts exist."
        out.append(f"⛔ ARTIFACT SOURCE UNREAD: {missing} — the artifact half of this answer is MISSING.")
        return "\n".join(out)
    stamp = f", generated {gen}" if gen else ""
    if not hits:
        out.append(f"(no derived artifact on disk matches — checked {total} of them{stamp}.)")
        return "\n".join(out)
    out.append(f"⛔ ALREADY ON DISK — {len(hits)} of {total} derived artifacts match. "
               f"CHECK THESE BEFORE BUILDING ANY INDEX, CENSUS, REGISTRY OR INVENTORY:")
    for _, r in hits:
        out.append(f"  [{r['tag']}] {r['text'][:200]}")
    out.append(f"  full census{stamp}: system/organism/generated/capability-census.md")
    out.append("  ⚠ `generated-by: NOTHING` means nothing on disk can refresh it — that one is "
               "certain, and it is the one that means DO NOT REVIVE THIS.")
    return "\n".join(out)


def _selftest():
    ok = True

    def ck(label, cond):
        nonlocal ok
        ok = ok and cond
        print(f"  {'PASS' if cond else 'FAIL'}  {label}")

    all_e, missing = entries()
    print(f"  parsed {len(all_e)} dead-end entries from {len(SOPS) - len(missing)}/{len(SOPS)} SOPs")
    ck("all three SOP sections were found and read", not missing)
    ck("parsed a substantial corpus (>= 40 entries)", len(all_e) >= 40)
    ck("every entry carries a source path + line",
       all(e["path"] and isinstance(e["line"], int) for e in all_e))

    # ── THE HIT PATH — a real, known dead end must be findable.
    hits, total, _ = search("warning-only hook that exits 0 so the model never sees it")
    ck("finds the exit-0 warning-hook dead end", bool(hits))
    ck("...and the top hit is actually about exit 0",
       bool(hits) and ("exit" in hits[0][2]["text"].lower()))

    hits2, _, _ = search("downgrade the ingest scan to haiku to save money")
    ck("finds the haiku-downgrade dead end", bool(hits2))

    hits3, _, _ = search("name a subagent so it can be addressed")
    ck("finds the named-subagent dead end", bool(hits3))

    # ── THE MISS PATH — prove it FAILS, per build-sop.md ("a check never SEEN to fail is not a
    # check"), and prove the miss is not silent.
    # ⛔⛔ THE MISS CASE MUST BE A REAL QUESTION, NOT GIBBERISH — v1 tested
    # "zzqqx flibbertigibbet", which has zero token overlap and therefore proved NOTHING about
    # the case that actually occurs: an ordinary English question about something simply not on
    # the list. A blind tester then asked about "a pink border and Comic Sans" and got FIVE
    # confident matches. **The test had been written from the same mental model as the code and
    # graded its own homework** (build-sop.md names this exact anti-pattern). These two controls
    # are real sentences a person would type.
    for ctrl in ("add a bright pink border around the calendar widget and use Comic Sans",
                 "write a recipe for vegetarian lasagna with three cheeses"):
        h, t, _ = search(ctrl)
        ck(f"CONTROL yields NO STRONG match: {ctrl[:38]}...",
           not [x for x in h if x[0] >= STRONG_SCORE])
        # ⚠ ACCEPTS EITHER "NO MATCH" OR "NO STRONG MATCH", and the reason matters. v1 asserted
        # only the latter and went RED when the stop-word fix made the lasagna control match
        # NOTHING AT ALL — a strictly BETTER outcome the test was too specific to accept. The
        # property that actually matters is "nothing is presented to the builder as a finding",
        # not which of the two honest phrasings it used. ⛔ This is not tuning a test to pass:
        # the code improved, and the assertion had encoded an implementation detail instead of
        # the guarantee. Both branches also carry the coverage caveat, asserted below.
        rendered = _render(ctrl, h, t, [], 5)
        ck("...and nothing is presented as a finding",
           ("NO STRONG MATCH" in rendered) or ("NO MATCH" in rendered))
        ck("...and the coverage caveat rides along either way",
           "NOT AN ALL-CLEAR" in rendered)
    # a genuine dead end must still clear the floor — prove the guard did not just mute everything
    for real in ("a PreToolUse hook that warns before WebSearch but exits 0",
                 "switch the ingest scan from sonnet down to haiku to save money"):
        h, _, _ = search(real)
        ck(f"REAL dead end still clears the floor: {real[:34]}...",
           bool([x for x in h if x[0] >= STRONG_SCORE]))
    hits4, total4, _ = search("zzqqx nonexistent flibbertigibbet vermicular")
    ck("a zero-overlap query returns NO match at all", not hits4)
    rendered = _render("zzqqx nonexistent", hits4, total4, [], 5)
    ck("a NO-MATCH states it is not an all-clear", "NOT AN ALL-CLEAR" in rendered)
    ck("a NO-MATCH quotes the ~35% coverage", "35%" in rendered)

    # ── An unreadable source must be reported, never counted as clean.
    bad = _render("x", [], 0, ["hook-sop"], 5)
    ck("an unread source is reported loudly", "UNREAD SOURCE" in bad and "INCOMPLETE" in bad)

    # ── THE FENCE — a hit must not dump the corpus.
    hits5, total5, _ = search("exit 0 hook", limit=5)
    out5 = _render("exit 0 hook", hits5, total5, [], 5)
    ck("output is capped, never the whole corpus", out5.count("matched on:") <= 5)

    print("\n" + ("deadend_check.py self-test PASSED" if ok else "✗ SELFTEST FAILED"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(
        prog="deadend_check.py",
        description="Has this already been tried and failed? Searches every DO NOT BUILD section.")
    ap.add_argument("query", nargs="*", help="what you are about to build, in plain words")
    ap.add_argument("--list", action="store_true", help="one line per recorded dead end")
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return _selftest()

    if a.list:
        all_e, missing = entries()
        if missing:
            print(f"⛔ UNREAD SOURCE(S): {', '.join(missing)} — this list is INCOMPLETE.")
        for e in all_e:
            ident = f"[{e['id']}]" if e["id"] else "[--]"
            print(f"{ident} {e['path']}:{e['line']}  {e['text'][:120]}")
        print(f"\n{len(all_e)} entries. {COVERAGE_CAVEAT}")
        return 0

    if not a.query:
        ap.print_usage(sys.stderr)
        print('deadend_check.py: error: say what you are about to build, e.g.\n'
              '  deadend_check.py "a warning-only hook that exits 0"', file=sys.stderr)
        return 2

    query = " ".join(a.query)
    hits, total, missing = search(query, a.limit)
    print(_render(query, hits, total, missing, a.limit))
    # T27.16 — the SECOND source. Prose about failures above; artifacts on disk below.
    a_hits, gen, a_missing = _artifact_hits(query)
    a_rows, _, _ = _artifacts()
    print(_render_artifacts(a_hits, gen, a_missing, len(a_rows)))
    # ⛔ ALWAYS EXIT 0. A found dead end is this tool SUCCEEDING, and a non-zero would make any
    # caller that chains on `&&` treat "I found the warning" as a failure to warn.
    return 0


if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "system", "tools")))
    from utf8_stdio import force_utf8_stdio
    force_utf8_stdio()
    sys.exit(main())

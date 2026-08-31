#!/usr/bin/env python3
"""completeness_receipt — native-id set-diff vs a pinned source, receipt written INTO
the artifact.  [Parts Library · Tier A · A4]

WHEN: the skill ingests, maps, or summarizes a bounded set -- always for ingest-shaped work.
WHAT: pins the denominator, set-diffs the artifact's native-id citations against the
      source, and writes the receipt into the artifact itself.
WHY:  Law 4.1 -- an LLM structurally CANNOT verify completeness against a source it
      cannot hold.  A blind judge read a Map built from 241 source items and passed it
      as "omitting nothing"; a mechanical set-diff found only 20 of 241 traceably
      covered [M].  The model graded the CLAIM, because the claim was all that fit in
      front of it.  Completeness is permanently a set-diff in code.

TWO SUB-RULES FROM THE LAW, both enforced here:
  PIN THE DENOMINATOR FIRST.  "N in scope" is proven against the source's own count, or
      completeness is asserted, not proven.  A mismatch is CANNOT-EVALUATE, not a fail --
      you do not know what you were counting.  An EMPTY source is refused outright: a
      vacuous denominator can only produce a vacuous pass, which is the silent-zero
      failure this part exists to catch.
  FIRE AT THE LOSS POINT.  Call this at the earliest seam where a drop can occur (a
      fan-out return boundary), never at phase exit -- by phase exit the drop is already
      invisible.  This part cannot enforce WHERE you call it; that is a wiring decision,
      and calling it late is the documented way to get a green light over a real loss.

WHY THE RECEIPT GOES IN THE ARTIFACT (the half that was missing)
      A receipt in a side directory is invisible to whoever reads the artifact, so the
      artifact still reads as authoritative while the loss sits unreported. Writing the
      receipt INTO the artifact makes the coverage claim travel with the claim it
      qualifies. COMMITTED != ENFORCED: the receipt is the evidence the check ran.

⚠ KNOWN BOUND, MEASURED -- THIS PART PROVES CITATION, NOT WORK.
      Found 2026-07-28 by `system/factory/defeater.py` on a live hostile run: an artifact
      consisting of nothing but the bare ids

          `cw_p2_unit_000269`
          `cw_p2_unit_000270`
          `cw_p2_unit_000271`

      PASSES this check completely. Every source id is cited, so the set-diff is clean --
      and not one item was actually processed. That is correct behaviour for what this
      part measures and a REAL limit on what a green receipt entitles you to claim.
      So: an id-coverage receipt is NECESSARY AND NOT SUFFICIENT for "the artifact
      accounts for every item." Pair it with something that proves substance per item
      (a text/span check like `system/factory/extract_clauses.py::span_receipt`, or a
      per-item field the receipt schema requires). Never wire this part alone behind a
      clause that says "accounts for" and treat the green as enforcement.

REACHABILITY -- an id counts as covered iff, resolved MECHANICALLY:
  (a) DIRECT     the id appears verbatim as a citation, or
  (b) COVERING   the artifact cites a recurring/series BASE this id is an instance of, or
  (c) TRUNCATION the artifact wrote a prefix of the id AND that prefix can only mean ONE
                 source id -- an AMBIGUOUS prefix credits nothing (see ambiguous_bases).
Anything else is RESIDUE.  A shorthand label the artifact invented ("Fern-flight") is
not a native id, so the item behind it lands in residue BY DESIGN -- the set-diff
refuses to credit an unprovable cover.  That refusal is the entire value: a generous
matcher would reproduce exactly the false "omits nothing" this part replaces.

PROVENANCE: the reachability rules and the id heuristic are EXTRACTED from the frozen
conformance lab (state_seam.py + ingest_setdiff.py), which proved them on real data.
Extraction, not reinvention -- and deliberately self-contained: a part that imports from
system/tools/ stops existing the moment the skill travels (SOP §II.5).  Faithfulness is
held by a differential self-test against the lab's own preserved grade.

USAGE
  completeness_receipt.py --artifact MAP.md --source-ids IDS.json [--declared N]
  completeness_receipt.py --artifact MAP.md --source-ids IDS.json --write-receipt
  completeness_receipt.py --artifact MAP.md --source-ids IDS.json --json
  completeness_receipt.py --selftest

EXIT CODES (the part contract)
  0  COMPLETE   -- every source id is covered
  1  LOSS       -- ids missing / duplicated / alien
  2  CANNOT EVALUATE -- missing file, empty source, denominator mismatch. Fail-closed.

SOURCE-IDS FILE: ["id", ...]  or  {"source_ids": [...]}  or  {"items": [{"item_id": ...}]}
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime

COMPLETE, LOSS, CANNOT_EVALUATE = 0, 1, 2

RECEIPT_START = "<!-- completeness-receipt:start -->"
RECEIPT_END = "<!-- completeness-receipt:end -->"

_ID_TOKEN = re.compile(r"`([^`]+)`")
_RECUR_SUFFIX = re.compile(r"_(\d{8}T\d{6}Z)$")


def _die(msg):
    print(f"CANNOT EVALUATE: {msg}", file=sys.stderr)
    sys.exit(CANNOT_EVALUATE)


# ---------------------------------------------------------------- id extraction

def looks_like_id(tok):
    """A native id, not a human shorthand label. Long, no spaces, id-ish charset.
    A capitalized word combined with a hyphen reads as an invented label -> refused."""
    t = tok.strip().rstrip(".")
    t = _RECUR_SUFFIX.sub("", t)
    if len(t) < 12 or " " in t:
        return False
    if re.search(r"[A-Z]", t) and "-" in t:
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9_\-]+", t))


def extract_citations(text):
    """Return (exact, bases) -- the id tokens the artifact actually cites."""
    exact, bases = set(), set()
    for m in _ID_TOKEN.finditer(text):
        raw = m.group(1).strip()
        truncated = raw.endswith("...")
        tok = raw.rstrip(".")
        if not looks_like_id(tok):
            continue
        exact.add(tok)
        bases.add(_RECUR_SUFFIX.sub("", tok))
        if truncated:
            bases.add(tok)
    return exact, bases


def ambiguous_bases(bases, source_ids):
    """Truncation prefixes that match MORE THAN ONE source id.

    THE HOLE THIS CLOSES (found 2026-07-28 by `system/factory/defeater.py`, on its first
    successful hostile run, against a real 3-id corpus). Rule (c) below lets a citation
    written as `abc123def456...` stand for the id it abbreviates. But native ids are a
    shared prefix plus a serial -- `cw_p2_unit_000269`, `..._000270`, `..._000271` -- so a
    SINGLE citation of `cw_p2_unit_000...` prefix-matched ALL of them. Measured:
    `citations_found: 1` producing `covered_count: 3` and `ok: true`.

    That is the 241-item Map failure rebuilt INSIDE the part written to kill it, and on
    any real corpus it is the common case rather than a corner one.

    THE RULE: a truncation prefix that cannot distinguish which id it means covers
    NOTHING. Ambiguity is not coverage -- the artifact did not identify anything, so
    fail-closed and report the ambiguity rather than quietly crediting it.
    """
    out = set()
    for b in bases:
        if len(b) < 12:
            continue
        hits = sum(1 for s in source_ids
                   if s.startswith(b) or _RECUR_SUFFIX.sub("", s).startswith(b))
        if hits > 1:
            out.add(b)
    return out


def is_covered(sid, exact, bases, ambiguous=frozenset()):
    if sid in exact:
        return True                                    # (a) direct
    sbase = _RECUR_SUFFIX.sub("", sid)
    if sbase in exact or sbase in bases:
        return True                                    # (b) covering group
    for b in bases:                                    # (c) truncation prefix
        if b in ambiguous:
            continue                                   #     ...but only if it is UNIQUE
        if len(b) >= 12 and (sid.startswith(b) or sbase.startswith(b)):
            return True
    return False


# ---------------------------------------------------------------- the set-diff

_SUBSTANCE_MIN_WORDS = 3


def substance_gaps(text, covered_ids, min_words=_SUBSTANCE_MIN_WORDS):
    """Which cited ids appear with NO accompanying prose on their line.

    ⛔ ENFORCES IN CODE THE BOUND THAT WAS ONLY IN THE DOCSTRING. Found 2026-07-28 by
    `system/factory/defeater.py`, which beat this part with:

        `cw_p2_unit_000269``cw_p2_unit_000270``cw_p2_unit_000271`

    Every id cited, set-diff clean, `ok: true` -- and not one item processed. Correct for
    what an id set-diff measures, and a real limit on what a green receipt entitles you to
    claim. The governing rail (plan, 2026-07-28): A GATE MUST VERIFY EVIDENCE OF WORK,
    NEVER THE FORM OF A CLAIM. A citation is the form; prose about the item is the work.

    OPT-IN, deliberately: id coverage alone is the right check for some artifacts. Wire
    `--require-substance` ON wherever a clause says the artifact "accounts for" its items.
    Cheap and honest heuristic -- an id's line must carry at least `min_words` words that
    are not themselves ids. It cannot judge whether the prose is GOOD (that is judgment,
    and §V.7 says never hard-gate judgment); it only catches the bare-list cheat.
    """
    bare = []
    for line in (text or "").splitlines():
        cited = [t for t in _ID_TOKEN.findall(line) if looks_like_id(t.rstrip("."))]
        if not cited:
            continue
        prose = _ID_TOKEN.sub(" ", line)
        # DISTINCT words of real length. The first version counted any token longer than
        # one character, and the defeater walked straight through it with `aa aa aa`
        # (2026-07-28, second sweep). The bar is not "uncheatable" -- it is that FAKING
        # the prose should cost about what WRITING it costs.
        words = {w.lower() for w in re.findall(r"[A-Za-z0-9']+", prose) if len(w) >= 3}
        if len(words) < min_words:
            bare.extend(c for c in cited if c in covered_ids or True)
    # a line with several ids and no prose makes every id on it bare
    return sorted(set(bare))


def grade(text, source_ids, declared_count=None, require_substance=False):
    """Pin the denominator, then set-diff. Raises ValueError -> fail closed."""
    src = list(dict.fromkeys(source_ids))
    if not src:
        raise ValueError("EMPTY source id list -- refusing to grade against a vacuous "
                         "denominator (a vacuous pass is the silent-zero failure)")
    if declared_count is None:
        declared_count = len(src)
    if declared_count != len(src):
        raise ValueError(f"DENOMINATOR UNPINNED: declared {declared_count} but the source "
                         f"holds {len(src)} distinct ids -- you do not know what you are "
                         f"counting, so this is not a fail, it is un-evaluable")

    exact, bases = extract_citations(text)
    ambig = ambiguous_bases(bases, src)
    covered = sorted(s for s in src if is_covered(s, exact, bases, ambig))
    residue = sorted(s for s in src if not is_covered(s, exact, bases, ambig))
    bare = substance_gaps(text, set(exact)) if require_substance else []
    alien = sorted(t for t in exact if t not in set(src)
                   and not any(s.startswith(t) or _RECUR_SUFFIX.sub("", s) == t for s in src))

    return {
        "source_count": len(src),
        "declared_count": declared_count,
        "denominator_pinned": True,
        "covered_count": len(covered),
        "covered": covered,
        "missing": residue,
        "missing_count": len(residue),
        "alien": alien,
        "citations_found": len(exact),
        # surfaced, never silent: a prefix that could mean several ids credited none
        "ambiguous_prefixes": sorted(ambig),
        "bare_citations": bare,
        "require_substance": require_substance,
        "partition_exhaustive": len(covered) + len(residue) == len(src),
        "ok": not residue and not alien and not bare,
        # the trap: in==out by count while the set-diff still finds a problem
        "count_only_would_pass": len(exact) == len(src) and bool(residue or alien),
    }


# ---------------------------------------------------------------- the receipt

def render_receipt(g, artifact_name=""):
    pct = (100.0 * g["covered_count"] / g["source_count"]) if g["source_count"] else 0.0
    verdict = "COMPLETE" if g["ok"] else "INCOMPLETE — LOSS DETECTED"
    lines = [
        RECEIPT_START,
        "",
        f"## Completeness receipt — {verdict}",
        "",
        f"- **Source (pinned denominator):** {g['source_count']} native ids"
        + (f"  ·  artifact: `{artifact_name}`" if artifact_name else ""),
        f"- **Traceably covered:** {g['covered_count']} of {g['source_count']} "
        f"({pct:.1f}%)",
        f"- **Residue (not traceable to a citation):** {g['missing_count']}",
    ]
    if g["alien"]:
        lines.append(f"- **Alien (cited but not in source):** {len(g['alien'])}")
    if g["count_only_would_pass"]:
        lines.append("- ⚠ **A naive COUNT check would have passed this** — the exact trap "
                     "this receipt exists for.")
    lines += [
        "",
        f"> Set-diff computed mechanically by `completeness_receipt.py` at "
        f"{datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}. Coverage means a native id is "
        f"traceable to a citation — a prose claim of completeness is not evidence "
        f"(Law 4.1: an LLM cannot verify completeness against a source it cannot hold).",
        "",
        RECEIPT_END,
    ]
    return "\n".join(lines)


def write_receipt(path, text, g):
    """Insert or REPLACE the receipt block in the artifact. Idempotent."""
    block = render_receipt(g, os.path.basename(path))
    if RECEIPT_START in text and RECEIPT_END in text:
        pre = text.split(RECEIPT_START)[0]
        post = text.split(RECEIPT_END, 1)[1]
        new = pre + block + post
        action = "replaced the existing receipt"
    else:
        new = text.rstrip("\n") + "\n\n" + block + "\n"
        action = "appended a new receipt"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(new)
    return action


def load_source_ids(path):
    raw = json.loads(open(path, encoding="utf-8").read())
    if isinstance(raw, dict):
        ids = raw.get("source_ids") or [i["item_id"] for i in raw.get("items", [])]
    else:
        ids = list(raw)
    return ids


# ---------------------------------------------------------------- self-test

# ⚠ NOBODY REAL IS IN THIS FIXTURE. "Fern" is an invented name, in the style of
# system/shipping-lane/fixtures/identity-fixture.md.
_MAP = (
    "pointer email `19f7f2846afd73e5`\n"
    "cal `rf67mu8kt57dv5hloi2jgot74d` (recurring base covers its instances)\n"
    "cal `06t29asgutja0nobegaobf0hlm...` (truncated)\n"
    "task `MG0tQ25UVHJpTE50RlFibQ`\n"
    "shorthand `Fern-flight` (a LABEL, not a native id)\n"
)
_SOURCE = [
    "19f7f2846afd73e5",                             # (a) direct
    "rf67mu8kt57dv5hloi2jgot74d_20260726T150000Z",  # (b) covering base
    "06t29asgutja0nobegaobf0hlm_20260726T160000Z",  # (c) truncation
    "MG0tQ25UVHJpTE50RlFibQ",                       # (a) direct
    "aaaaDROPPEDtask0001",                          # residue
    "bbbbDROPPEDemail0002",                         # residue
    "fern_flight_native_id_99",                     # residue: label is not a citation
]
_ALL_CITED = _MAP + "".join(f"also `{s}`\n" for s in _SOURCE)


def selftest():
    ok = True
    skipped = []

    def report(label, passed, detail=""):
        nonlocal ok
        ok = ok and passed
        print(f"  [{'PASS' if passed else 'FAIL'}] {label}{(' -- ' + detail) if detail else ''}")

    print("completeness_receipt --selftest")

    g = grade(_MAP, _SOURCE, declared_count=len(_SOURCE))
    report("catches a known-bad (3 source items never traceably cited)",
           not g["ok"] and g["missing_count"] == 3, f"{g['covered_count']}/{g['source_count']}")
    report("credits a DIRECT citation", "19f7f2846afd73e5" in g["covered"])
    report("credits a COVERING recurring base",
           "rf67mu8kt57dv5hloi2jgot74d_20260726T150000Z" in g["covered"])
    report("credits a TRUNCATED prefix when it can only mean ONE id",
           "06t29asgutja0nobegaobf0hlm_20260726T160000Z" in g["covered"])

    # ⭐ THE AMBIGUOUS-PREFIX HOLE — found by the defeater 2026-07-28, first hostile run.
    # Native ids are a shared stem plus a serial, so ONE truncated citation used to
    # prefix-match the whole corpus: 1 citation -> 3 covered -> ok:true. That is the
    # 241-item Map failure rebuilt inside the part written to kill it.
    _SERIAL = ["cw_p2_unit_000269", "cw_p2_unit_000270", "cw_p2_unit_000271"]
    cheat = grade("# Map\n\n- `cw_p2_unit_000...` — covers this batch\n", _SERIAL)
    report("known-bad: ONE truncated prefix can no longer cover a whole serial corpus",
           not cheat["ok"] and cheat["missing_count"] == 3,
           f"{cheat['covered_count']}/{cheat['source_count']} from {cheat['citations_found']} citation")
    report("the ambiguous prefix is REPORTED, not silently ignored",
           cheat["ambiguous_prefixes"] == ["cw_p2_unit_000"])
    report("an ambiguous prefix credits NOTHING (fail-closed, not partial credit)",
           cheat["covered"] == [])
    # ...and the honest form still passes: cite each id and you are covered
    honest = grade("".join(f"- `{s}` — carried forward\n" for s in _SERIAL), _SERIAL)
    report("known-good: citing each serial id individually still PASSES",
           honest["ok"] and honest["covered_count"] == 3)
    # a prefix that is still unique among serial ids keeps working
    one = grade("- `cw_p2_unit_000269...` — this one\n", _SERIAL)
    report("a truncation that identifies exactly ONE serial id is still credited",
           "cw_p2_unit_000269" in one["covered"] and not one["ambiguous_prefixes"])

    # ⭐ CITATION IS NOT WORK — the bound moved from the docstring into CODE (2026-07-28).
    # The defeater's second cheat: every id cited, zero prose, receipt clean.
    bare_cheat = "`cw_p2_unit_000269``cw_p2_unit_000270``cw_p2_unit_000271`"
    off = grade(bare_cheat, _SERIAL)
    report("id coverage ALONE still passes a bare id-dump (unchanged, and honest)",
           off["ok"] and off["covered_count"] == 3)
    on = grade(bare_cheat, _SERIAL, require_substance=True)
    report("known-bad: --require-substance CATCHES the bare id-dump",
           not on["ok"] and len(on["bare_citations"]) == 3,
           f"bare={len(on['bare_citations'])}")
    real = grade("".join(f"- `{s}` — carried forward into the map with its context\n"
                         for s in _SERIAL), _SERIAL, require_substance=True)
    report("known-good: real prose per item still PASSES under --require-substance",
           real["ok"] and not real["bare_citations"])
    report("the substance check is OPT-IN and reports which mode produced the verdict",
           off["require_substance"] is False and real["require_substance"] is True)

    report("refuses to credit an invented LABEL (the whole point)",
           "fern_flight_native_id_99" in g["missing"])
    report("partition is exhaustive (covered + residue == source)", g["partition_exhaustive"])

    g2 = grade(_ALL_CITED, _SOURCE, declared_count=len(_SOURCE))
    report("passes a known-good (every id traceably cited)",
           g2["ok"] and g2["covered_count"] == len(_SOURCE),
           f"{g2['covered_count']}/{g2['source_count']}")

    # the count trap: same COUNT of citations as source, but one dropped + one alien
    trap_src = ["idaaaaaaaaaaaa1", "idaaaaaaaaaaaa2", "idaaaaaaaaaaaa3"]
    trap_text = "`idaaaaaaaaaaaa1` `idaaaaaaaaaaaa2` `idzzzzzzzzzzzz9`"
    gt = grade(trap_text, trap_src, declared_count=3)
    report("catches a drop that a COUNT check would wave through",
           not gt["ok"] and gt["count_only_would_pass"] and gt["missing"] == ["idaaaaaaaaaaaa3"],
           f"missing={gt['missing']} alien={gt['alien']}")

    # fail-closed
    for label, fn in (
        ("refuses an EMPTY source (vacuous denominator)", lambda: grade(_MAP, [])),
        ("refuses an UNPINNED denominator", lambda: grade(_MAP, _SOURCE, declared_count=99)),
    ):
        try:
            fn()
            report(label, False, "no exception")
        except ValueError:
            report(label, True)

    # the receipt is written INTO the artifact, and is idempotent
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "map.md")
        with open(p, "w") as fh:
            fh.write(_MAP)
        write_receipt(p, open(p).read(), g)
        body = open(p).read()
        report("writes the receipt INTO the artifact",
               RECEIPT_START in body and "4 of 7" in body, "receipt block present")
        report("the receipt states the real number, not a claim", "INCOMPLETE" in body)
        write_receipt(p, open(p).read(), g)
        body2 = open(p).read()
        report("re-running REPLACES the receipt (idempotent, never stacks)",
               body2.count(RECEIPT_START) == 1)

        # CLI exit-code contract
        sp = os.path.join(td, "src.json")
        with open(sp, "w") as fh:
            json.dump(_SOURCE, fh)
        me = os.path.abspath(__file__)
        rc = subprocess.run([sys.executable, me, "--artifact", p, "--source-ids", sp],
                            capture_output=True, text=True).returncode
        report("CLI known-bad -> exit 1", rc == LOSS, f"got exit {rc}")
        gp = os.path.join(td, "good.md")
        with open(gp, "w") as fh:
            fh.write(_ALL_CITED)
        rc = subprocess.run([sys.executable, me, "--artifact", gp, "--source-ids", sp],
                            capture_output=True, text=True).returncode
        report("CLI known-good -> exit 0", rc == COMPLETE, f"got exit {rc}")
        ep = os.path.join(td, "empty.json")
        with open(ep, "w") as fh:
            json.dump([], fh)
        rc = subprocess.run([sys.executable, me, "--artifact", gp, "--source-ids", ep],
                            capture_output=True, text=True).returncode
        report("CLI empty source -> exit 2 (fail-closed)", rc == CANNOT_EVALUATE, f"got exit {rc}")

    # --- DIFFERENTIAL vs the frozen lab's own preserved grade ------------------
    # Faithful extraction is a claim; this is the check that proves it. We rebuild the
    # exact citation set the lost P0.3 Map must have had (source minus the preserved
    # residue) and require a byte-identical residue back.
    # ⚠ DEAD REFERENCE — PRE-EXISTING, NOT INTRODUCED BY THE cal→planning RENAME (verified 2026-08-15).
    # `system/tools/conformance-lab/` EXISTS in this repo but holds only driver.py / probes/ /
    # rule-registry.md — there is NO `fixtures/` subtree at all, under either the old `cal-weekly`
    # name or the new one. The w30-* fixtures were never ported here, so the DIFFERENTIAL check below
    # has ALWAYS taken its else-branch and reported [FAIL], meaning this part has never passed
    # `run_selftests.sh` in this repo. The path was renamed cal-weekly → planning-weekly for
    # consistency only; renaming a dead path does not make it live.
    # ▶ THE REAL FIX IS A DECISION, NOT A RENAME: either port the w30-* fixtures, or retire this
    #   DIFFERENTIAL check (the same call `run_selftests.sh` documents making for its reachability
    #   check — "a check that can only ever report failure gets deleted"). Until 2026-08-22 this was
    #   left failing, and loud, rather than downgraded to a skip, so the faithful-extraction claim
    #   stayed visibly unproven.
    # ✅ DECIDED 2026-08-22 (operator ruling, after /ship was blocked by this FAIL twice):
    #   the check STAYS in code (it runs for real the day the fixtures land — a search of this
    #   machine and the notes folder found none), but a missing fixture is reported as [SKIP], not
    #   [FAIL]. A skip is still LOUD: the line names the unproven claim, and the SELFTEST verdict
    #   carries the skip count, so `run_selftests.sh` can surface it under a passing part. What
    #   changed is only that "could not run" is no longer spelled the same as "ran and failed" —
    #   the same distinction /ship's judge enforces with NOT-EVALUATED vs FINDINGS.
    _repo = os.environ.get("CLAUDE_PROJECT_DIR") or os.path.abspath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    lab = os.path.join(_repo, "system/tools/conformance-lab/fixtures/planning-weekly")
    gpath = os.path.join(lab, "w30-state-grade-p03map.json")
    spath = os.path.join(lab, "w30-source-ids.json")
    if os.path.isfile(gpath) and os.path.isfile(spath):
        preserved = json.loads(open(gpath).read())
        src = load_source_ids(spath)
        implied_cited = [s for s in dict.fromkeys(src) if s not in set(preserved["missing"])]
        synth = "\n".join(f"- item `{i}`" for i in implied_cited)
        gg = grade(synth, src, declared_count=preserved["receipt"]["declared_count"])
        report("DIFFERENTIAL: reproduces the preserved 20-of-241 grade exactly",
               gg["covered_count"] == preserved["reachable_n"]
               and gg["missing"] == sorted(preserved["missing"]),
               f"{gg['covered_count']}/{gg['source_count']}, "
               f"residue {gg['missing_count']} vs preserved {len(preserved['missing'])}")
    else:
        skipped.append("DIFFERENTIAL vs preserved lab grade")
        print("  [SKIP] DIFFERENTIAL vs preserved lab grade -- lab fixtures not found "
              "(faithful-extraction claim UNPROVEN, not disproven; port the w30-* fixtures to run it)")

    verdict = "PASS" if ok else "FAIL"
    if ok and skipped:
        verdict += f" ({len(skipped)} SKIP -- {'; '.join(skipped)})"
    print("SELFTEST:", verdict)
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(
        description="completeness_receipt -- native-id set-diff, receipt written into the artifact")
    ap.add_argument("--artifact")
    ap.add_argument("--source-ids")
    ap.add_argument("--declared", type=int, default=None,
                    help="the denominator you believe is in scope; mismatch = un-evaluable")
    ap.add_argument("--write-receipt", action="store_true",
                    help="write the receipt INTO the artifact (replaces any prior receipt)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--require-substance", action="store_true",
                    help="a cited id must carry prose on its line -- wire this ON wherever "
                         "a clause says the artifact 'accounts for' its items")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())
    if not args.artifact or not args.source_ids:
        _die("--artifact and --source-ids are required")
    for p, what in ((args.artifact, "artifact"), (args.source_ids, "source-ids file")):
        if not os.path.isfile(p):
            _die(f"{what} not found: {p!r}")
    try:
        ids = load_source_ids(args.source_ids)
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        _die(f"cannot read source ids: {e}")

    text = open(args.artifact, encoding="utf-8").read()
    try:
        g = grade(text, ids, declared_count=args.declared,
                  require_substance=args.require_substance)
    except ValueError as e:
        _die(str(e))

    action = None
    if args.write_receipt:
        action = write_receipt(args.artifact, text, g)

    if args.json:
        g["receipt_action"] = action
        print(json.dumps(g, indent=2))
    else:
        pct = 100.0 * g["covered_count"] / g["source_count"]
        print(f"completeness -- {'COMPLETE' if g['ok'] else 'LOSS DETECTED'}")
        print(f"  denominator pinned at {g['source_count']} source ids")
        print(f"  traceably covered:    {g['covered_count']} ({pct:.1f}%)")
        print(f"  residue (uncredited): {g['missing_count']}")
        if g["alien"]:
            print(f"  alien (cited, not in source): {len(g['alien'])}")
        if g["count_only_would_pass"]:
            print("  ⚠ a naive COUNT check would have PASSED this")
        if action:
            print(f"  receipt: {action}")
    sys.exit(COMPLETE if g["ok"] else LOSS)


if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "system", "tools")))
    from utf8_stdio import force_utf8_stdio
    force_utf8_stdio()
    main()

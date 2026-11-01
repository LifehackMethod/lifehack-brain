#!/usr/bin/env python3
"""extract_clauses — spec units → atomic clauses, with a coverage receipt.  [Factory · S1.1 + S1.3]

WHAT: turns the mechanical units from `spec_units.py` into the atomic clauses the sorter
      classifies — then PROVES it dropped nothing, by set-diffing its own output against
      the pinned denominator using the shipped `completeness_receipt.py` part.
WHY:  Law 4.1. An extractor that reports its own clause count is asserting completeness,
      not proving it — the same shape that let a Map built from 241 items pass as
      "omitting nothing." The sorter is not allowed to be the next thing that does this.

THE DESIGN CHOICE THAT MATTERS — extraction is DETERMINISTIC BY DEFAULT.
      A clause is a mechanical unit, 1:1, unless a unit is genuinely COMPOUND (several
      requirements crammed into one bullet). Only compound units go to a model, and only
      to be SPLIT — never to be judged, filtered, or reworded. So:
        · nothing can be dropped by a model that was never asked to decide what survives;
        · a re-run on an unchanged spec is byte-identical without any model at all;
        · the model's blast radius is one unit, and a lost id is caught mechanically.
      This is Law 1's division of labour applied to our own tool: code does the
      mechanical part, the model does only the part code cannot.

THE NO-DROP INVARIANT (enforced, not hoped): every normative unit id MUST be cited by at
      least one clause. A split that loses an id is a hard failure, not a warning — and it
      is checked after the model runs, so a model that ignores instructions cannot pass.

THE SPLITTER RUNS A FALLBACK LADDER (claude -> codex), mirroring `voted_judge.py`'s
      discipline: rungs resolved mechanically from what's on the machine, never one
      hardcoded binary path. If a rung fails it is recorded and the next is tried; if
      EVERY rung fails, extraction raises and the CLI exits CANNOT_EVALUATE (2) — it
      never falls silently back to an empty or unsplit "success." This is step ONE of
      the whole factory pipeline; one unconditional call with no fallback here stalls
      everything downstream.

USAGE
  extract_clauses.py --spec FILE --slug cw_p2 [--section "Phase 2 —"] [--out DIR]
  extract_clauses.py --spec FILE --slug cw_p2 --section "Phase 2 —" --split   # LLM splitter
  extract_clauses.py --frozen OUT/cw_p2-clauses.json --receipt-only
  extract_clauses.py --selftest

EXIT CODES
  0  extracted, and the coverage receipt is CLEAN
  1  LOSS — a normative unit is cited by no clause (the no-drop invariant broke)
  2  CANNOT EVALUATE — missing spec/section, empty denominator, splitter unusable.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PARTS = os.path.abspath(os.path.join(HERE, "..", "parts"))
sys.path.insert(0, HERE)
from spec_units import scan, denominator, non_normative_heading  # noqa: E402

CLEAN, LOSS, CANNOT_EVALUATE = 0, 1, 2
COMPLETENESS_PART = os.path.join(PARTS, "completeness_receipt.py")

# A unit is COMPOUND when it plainly carries more than one requirement.
_RX_COMPOUND = re.compile(r";|·|\band then\b|\balso\b", re.IGNORECASE)
_MODALS = re.compile(
    r"\b(?:must|never|always|shall|cannot|required|only|do not|don't|should)\b", re.IGNORECASE)


def _die(msg):
    print(f"CANNOT EVALUATE: {msg}", file=sys.stderr)
    sys.exit(CANNOT_EVALUATE)


def is_compound(text):
    """Two independent signals, so a single stylistic quirk doesn't trigger a split."""
    return bool(_RX_COMPOUND.search(text)) or len(_MODALS.findall(text)) > 1


def clauses_from_units(units):
    """Deterministic 1:1. Every normative unit becomes exactly one clause, citing itself."""
    out = []
    for i, u in enumerate(denominator(units), 1):
        # HEADING CONTEXT travels with the clause (added 2026-07-29). Without it the
        # classifier grades every sentence in a vacuum -- see spec_units for the incident.
        # `non_normative` is computed HERE, deterministically, so downstream stages never
        # have to re-derive it and can skip the model call entirely for these.
        disq = non_normative_heading(u.get("heading_path"))
        out.append({
            "clause_id": f"{u['unit_id']}_c01",
            "text": u["text"],
            "source_unit_ids": [u["unit_id"]],
            "line": u["line"],
            "kind": u["kind"],
            "compound_candidate": is_compound(u["text"]),
            "split_by": None,
            "heading": u.get("heading"),
            "heading_path": u.get("heading_path") or [],
            "non_normative_section": disq,
        })
    return out


# ---------------------------------------------------------------- the splitter

_SPLIT_PROMPT = """You are splitting compound requirements into atomic ones. This is a MECHANICAL
task, not a judgement task.

RULES — these are absolute:
- Split a requirement ONLY where it plainly contains more than one distinct obligation.
- NEVER drop a requirement. NEVER reword beyond what splitting requires. NEVER add one.
- NEVER decide whether a requirement is good, enforceable, or important. Not your job.
- If a unit is already atomic, return it UNCHANGED as a single part.
- Preserve the wording of each part as closely as the split allows.

Return ONLY a JSON array, one object per input unit, in the SAME ORDER:
[{"unit_id": "<the id you were given>", "parts": ["atomic requirement 1", "..."]}]

UNITS:
"""


# ---------------------------------------------------------------- the fallback ladder
#
# WHY THIS EXISTS (portability audit, 2026-08-01). This was one unconditional `claude -p`
# call with zero fallback — and this module is STEP ONE of the whole factory pipeline. If
# that one call failed for any reason (binary missing, cold-start timeout, rate limit),
# nothing downstream ever ran. Mirrors `voted_judge.py`'s ladder discipline: rungs tried
# in order, resolved MECHANICALLY from what's actually on the machine (never hardcoded to
# one machine's layout), and DEGRADE-AND-ANNOUNCE — a caller is told which rung ran, and
# if every rung fails the tool fails CLOSED and LOUDLY (Law 4.1's "receipt over
# assertion" applies to the splitter's own plumbing, not only to its output).
#
# UNLIKE voted_judge, THIS LADDER IS NOT ABOUT BLINDNESS. Splitting a compound unit into
# atomic parts is a mechanical task, not a judgment Lifehack doctrine could bias — so
# there is no `--bare` rung and no controls pair here. The only question this ladder
# answers is "is a CLI that can run `_SPLIT_PROMPT` actually available," ranked by
# preference (claude first — it is the existing, tuned default) and falling through to a
# second CLI family before giving up.

CODEX_BIN = "/opt/homebrew/bin/codex"
CODEX_NEUTRAL_DIR = "/tmp/codex-splitter"


def find_claude(claude_bin=None):
    """Locate the claude CLI. Injectable so a broken/missing primary rung is testable
    without needing to actually corrupt this machine's PATH."""
    if claude_bin is not None:
        return claude_bin if (os.path.isfile(claude_bin)
                              and os.access(claude_bin, os.X_OK)) else None
    return shutil.which("claude")


def find_codex(codex_bin=None):
    """Locate codex WITHOUT hardcoding one machine's Homebrew layout (mirrors
    `voted_judge.find_codex` — parts are supposed to be self-contained and travel).
    PATH first (portable), the known location second (this machine), then nothing."""
    if codex_bin is not None:
        return codex_bin if (os.path.isfile(codex_bin)
                             and os.access(codex_bin, os.X_OK)) else None
    found = shutil.which("codex")
    if found:
        return found
    if os.path.isfile(CODEX_BIN) and os.access(CODEX_BIN, os.X_OK):
        return CODEX_BIN
    return None


def splitter_ladder(claude_bin=None, codex_bin=None):
    """Which rungs are usable on THIS machine, ranked. Mechanical — decided from the
    environment, never from what we wish were true. Returns [(name, resolved_path), ...]."""
    rungs = []
    c = find_claude(claude_bin)
    if c:
        rungs.append(("claude", c))
    x = find_codex(codex_bin)
    if x:
        rungs.append(("codex", x))
    return rungs


def _run_claude(prompt, model, timeout, claude_bin):
    try:
        p = subprocess.run([claude_bin, "-p", prompt, "--model", model],
                           capture_output=True, text=True, timeout=timeout,
                           cwd=os.path.expanduser("~"))
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, f"claude: could not run: {e}"
    out = (p.stdout or "").strip()
    if not out:
        return None, (f"claude: empty stdout (exit {p.returncode}, "
                      f"stderr {(p.stderr or '')[:160]!r})")
    return out, None


def _run_codex(prompt, timeout, codex_bin):
    # Sandboxed read-only, from a neutral empty dir (no AGENTS.md picked up), with `-o` so
    # only the final message is captured instead of the event stream — same shape as
    # `voted_judge.judge_argv`'s codex branch.
    os.makedirs(CODEX_NEUTRAL_DIR, exist_ok=True)
    out_file = os.path.join(CODEX_NEUTRAL_DIR,
                            f"split-{os.getpid()}-{abs(hash(prompt)) % 10**8}.txt")
    try:
        os.path.exists(out_file) and os.remove(out_file)
    except OSError:
        pass
    try:
        with open(os.devnull, "rb") as devnull:
            subprocess.run([codex_bin, "exec", "--skip-git-repo-check", "-s", "read-only",
                            "--color", "never", "-C", CODEX_NEUTRAL_DIR,
                            "-o", out_file, prompt],
                           stdin=devnull, capture_output=True, text=True, timeout=timeout,
                           cwd=CODEX_NEUTRAL_DIR)
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, f"codex: could not run: {e}"
    try:
        text = open(out_file, encoding="utf-8").read().strip()
    except OSError:
        return None, "codex: produced no output file"
    return (text, None) if text else (None, "codex: empty output")


def run_splitter(prompt, model="sonnet", timeout=240, claude_bin=None, codex_bin=None):
    """Try each usable rung in order; return (raw_text, rung_name).

    FAIL CLOSED, LOUDLY: if every rung is unusable or every rung that ran returned
    nothing, this raises — it never returns an empty/placeholder result that a caller
    could mistake for "the splitter ran and found nothing to split."
    """
    rungs = splitter_ladder(claude_bin, codex_bin)
    if not rungs:
        raise RuntimeError("splitter ladder exhausted: neither `claude` nor `codex` is "
                           "available on PATH or in the known install location")
    errors = []
    for name, resolved in rungs:
        if name == "claude":
            text, err = _run_claude(prompt, model, timeout, resolved)
        else:
            text, err = _run_codex(prompt, timeout, resolved)
        if text:
            return text, name
        errors.append(err or f"{name}: unknown failure")
    raise RuntimeError("splitter ladder exhausted -- every rung failed: " + "; ".join(errors))


def split_batch(batch, model="sonnet", timeout=240, claude_bin=None, codex_bin=None):
    """Send one batch of compound units to a model. Returns ({unit_id: [parts]}, rung_name).

    Batched deliberately: each CLI cold-starts (~36s even idle for `claude`), so one call
    per unit over hundreds of units starves every call past its timeout. Bundling
    amortises the fixed cost — measured ~15x on a prior bulk run.
    """
    payload = "\n".join(f'- unit_id: {u["unit_id"]}\n  text: {u["text"]}' for u in batch)
    raw, rung = run_splitter(_SPLIT_PROMPT + payload, model=model, timeout=timeout,
                             claude_bin=claude_bin, codex_bin=codex_bin)
    m = re.search(r"\[.*\]", raw or "", re.DOTALL)
    if not m:
        raise RuntimeError(f"splitter ({rung}) returned no JSON array: {(raw or '')[:200]!r}")
    try:
        arr = json.loads(m.group(0))
    except json.JSONDecodeError as e:
        raise RuntimeError(f"splitter ({rung}) returned unparseable JSON: {e}")
    out = {}
    for row in arr:
        uid, parts = row.get("unit_id"), row.get("parts")
        if uid and isinstance(parts, list):
            clean = [str(x).strip() for x in parts if str(x).strip()]
            if clean:
                out[uid] = clean
    return out, rung


def apply_splits(clauses, splits, splitter_name):
    """Expand clauses using the splitter's output. A unit absent from `splits` is untouched."""
    out = []
    for c in clauses:
        uid = c["source_unit_ids"][0]
        parts = splits.get(uid)
        if not parts or len(parts) == 1:
            out.append(c)
            continue
        for i, text in enumerate(parts, 1):
            d = dict(c)
            d["clause_id"] = f"{uid}_c{i:02d}"
            d["text"] = text
            d["split_by"] = splitter_name
            out.append(d)
    return out


# ---------------------------------------------------------------- span coverage
#
# WHY THE ID CHECK IS NOT ENOUGH (fixed 2026-07-28). The receipt below proves every
# normative unit ID is still CITED. That is a real check and it catches a dropped clause.
# It is blind to the loss that actually happens: a split that KEEPS the id and silently
# drops half the sentence. "capture the delta; do NOT name the Win" -> ["capture the
# delta"] still cites its unit, so the id set-diff prints CLEAN while the obligation is
# gone. That is the 241-item Map failure rebuilt inside the tool built to kill it -- a
# completeness check whose denominator is coarser than the thing being lost.
#
# So coverage is pushed down one level: every CONTENT TERM of a normative unit must
# survive into at least one of that unit's clauses. Zero tolerance, no threshold to fit.
#
# THE IGNORE LIST IS CLOSED, SMALL, AND DELIBERATE. Articles, pronouns and conjunctions
# are dropped because SPLITTING IS THE OPERATION THAT REMOVES THEM -- "A and B" becoming
# "A" + "B" is a correct split, and flagging it would make the check unusable.
# NEGATIONS AND MODALS ARE NOT IGNORED: `not` · `never` · `no` · `must` · `only` ·
# `cannot` · `without` ARE the requirement, and dropping one inverts a rule while leaving
# the sentence looking intact. Those are precisely what this check exists to catch.
#
# ⚠ THE BOUNDARY, STATED RATHER THAN HIDDEN: because conjunctions are ignored, a split
# that turns "A or B" into "A" + "B" (changing a choice into two obligations) passes this
# check. Word-level coverage cannot see that; only reading the pair can. Named here so
# nobody reads a CLEAN span receipt as "the split was semantically faithful."

_WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’-]*")
_IGNORE = {
    "a", "an", "the", "of", "to", "in", "on", "at", "by", "for", "and", "or", "as",
    "is", "are", "be", "been", "was", "were", "with", "from", "into", "then", "than",
    "it", "its", "this", "that", "these", "those", "there", "here", "so", "such",
    "their", "them", "they", "he", "she", "him", "her", "his", "we", "us", "our",
    "you", "your", "i", "which", "who", "whom", "whose", "if", "when", "while", "also",
}


def content_terms(text):
    """Requirement-bearing vocabulary. Negations and modals deliberately survive."""
    return [w for w in (m.group(0).lower() for m in _WORD.finditer(text or ""))
            if w not in _IGNORE]


def span_receipt(units, clauses):
    """Set-diff at TEXT level: does every unit's vocabulary survive into its clauses?"""
    by_unit = {}
    for c in clauses:
        for uid in c["source_unit_ids"]:
            by_unit.setdefault(uid, []).append(c["text"])

    rows, lost_units = [], []
    src_total = kept_total = 0
    for u in denominator(units):
        src = list(dict.fromkeys(content_terms(u["text"])))
        have = set()
        for t in by_unit.get(u["unit_id"], []):
            have.update(content_terms(t))
        missing = [t for t in src if t not in have]
        src_total += len(src)
        kept_total += len(src) - len(missing)
        if missing:
            lost_units.append(u["unit_id"])
            rows.append({"unit_id": u["unit_id"], "missing_terms": missing,
                         "source_text": u["text"],
                         "clauses": by_unit.get(u["unit_id"], [])})
    return {"ok": not lost_units,
            "term_count": src_total,
            "terms_kept": kept_total,
            "lossy_units": lost_units,
            "detail": rows,
            "note": ("every content term of every normative unit survives into its clauses"
                     if not lost_units else
                     f"{len(lost_units)} unit(s) lost text that no clause carries forward")}


# ---------------------------------------------------------------- the receipt

def coverage_receipt(units, clauses, workdir):
    """Set-diff the clauses' cited unit ids against the pinned denominator, using the
    SHIPPED completeness_receipt part as a subprocess — the sorter dogfoods its own library
    rather than re-implementing the check it exists to enforce."""
    if not os.path.isfile(COMPLETENESS_PART):
        raise RuntimeError(f"required part not found: {COMPLETENESS_PART}")
    den = denominator(units)
    src = os.path.join(workdir, "denominator.json")
    with open(src, "w", encoding="utf-8") as fh:
        json.dump([u["unit_id"] for u in den], fh)

    # the artifact the part reads: every clause citing its source unit(s) in backticks
    #
    # ⚠ THE CLAUSE TEXT IS DE-BACKTICKED BEFORE IT GOES IN, and that is load-bearing
    # (fixed 2026-07-28, FIRST run of the sorter against a SECOND skill — plan S2.1).
    # `completeness_receipt` reads every backticked token in this manifest as a CITATION.
    # The clause text is copied verbatim from the spec, so any backticked identifier in the
    # source prose -- `ingest-reader`, `sentinel_response`, `injection_flag` -- arrived here
    # looking exactly like a cited unit id, landed in the receipt's ALIEN set (captured −
    # source), and drove `ok=False`. The extraction was CORRECT; the manifest was polluting
    # its own checker.
    #
    # WHY PLANNING-WEEKLY NEVER SHOWED THIS: its prose is interrogative and names almost nothing
    # in backticks. The ingest skill is a mechanical pipeline that names tools constantly.
    # **This is the generalization finding S2.2 asks for — a class the first skill could not
    # have taught us.** The fix is in the manifest writer, NOT in the shipped part: alien
    # detection is doing its job correctly, and weakening it would blind a real check.
    manifest = os.path.join(workdir, "coverage-manifest.md")
    with open(manifest, "w", encoding="utf-8") as fh:
        fh.write("# Clause coverage manifest\n\n")
        for c in clauses:
            cited = " ".join(f"`{u}`" for u in c["source_unit_ids"])
            gloss = c["text"][:120].replace("`", "'")
            fh.write(f"- {c['clause_id']}: {cited} — {gloss}\n")

    p = subprocess.run([sys.executable, COMPLETENESS_PART, "--artifact", manifest,
                        "--source-ids", src, "--json"], capture_output=True, text=True)
    if p.returncode == 2:
        raise RuntimeError(f"completeness_receipt could not evaluate: {p.stderr.strip()}")
    try:
        return json.loads(p.stdout), manifest
    except json.JSONDecodeError:
        raise RuntimeError(f"completeness_receipt returned unparseable output: {p.stdout[:200]!r}")


def extract(spec_path, slug, section=None, do_split=False, model="sonnet",
            batch_size=15, workdir=None):
    text = open(spec_path, encoding="utf-8").read()
    units = scan(text, slug=slug, section=section)
    den = denominator(units)
    if not den:
        raise ValueError("ZERO normative units — refusing to extract against a vacuous "
                         "denominator (a vacuous pass is the silent-zero failure)")

    clauses = clauses_from_units(units)
    split_note = "deterministic 1:1 (no model)"
    rungs_used = []
    if do_split:
        compound = [c for c in clauses if c["compound_candidate"]]
        splits = {}
        for i in range(0, len(compound), batch_size):
            batch = [{"unit_id": c["source_unit_ids"][0], "text": c["text"]}
                     for c in compound[i:i + batch_size]]
            batch_splits, rung = split_batch(batch, model=model)
            splits.update(batch_splits)
            rungs_used.append(rung)
        clauses = apply_splits(clauses, splits, model)
        used = "/".join(sorted(set(rungs_used))) if rungs_used else "none"
        split_note = (f"{len(compound)} compound unit(s) sent to {model} in batches of "
                      f"{batch_size} via {used}")

    # Namespace the scratch by slug. Without this, running several phases into one --out
    # leaves a single denominator.json / coverage-manifest.md — the LAST phase's — while
    # appearing to document all of them. An audit artifact that silently describes a
    # different run than the one you're reading is worse than no artifact.
    wd = os.path.join(workdir, f"_audit-{slug}") if workdir \
        else tempfile.mkdtemp(prefix="factory-extract-")
    os.makedirs(wd, exist_ok=True)
    receipt, manifest = coverage_receipt(units, clauses, wd)
    spans = span_receipt(units, clauses)
    return {"spec": os.path.basename(spec_path), "section": section, "slug": slug,
            "denominator": len(den), "clauses": clauses, "clause_count": len(clauses),
            "extraction": split_note, "receipt": receipt, "span_receipt": spans,
            "manifest": manifest, "workdir": wd,
            # extraction is deterministic 1:1 unless --split ran; either way the reader
            # should not have to INFER which numbers a model touched
            "provenance": {
                "MEASURED_WITH": "llm-splitter" if do_split else "no-judge",
                "quarantined": False,
                "splitter_rungs": sorted(set(rungs_used)),
                "splitter_fell_back": bool(rungs_used) and any(r != "claude" for r in rungs_used),
                "detail": ("units are scanned mechanically; a model was used ONLY to split "
                           "compound units, never to judge, filter or reword — and the "
                           "no-drop invariant is checked at ID *and* text level after it runs"
                           if do_split else
                           "no model was involved at any step — re-running is byte-identical")}}


# ---------------------------------------------------------------- self-test

_FIXTURE = """## Phase 2 — Connect the Dots

- generate the round's leveraged questions from the pad, biggest-first
- capture the delta this round; do not name the Win
The session must never conclude before Phase 3.
**Questions are numbered.**
"""


def selftest():
    ok = True

    def report(label, passed, detail=""):
        nonlocal ok
        ok = ok and passed
        print(f"  [{'PASS' if passed else 'FAIL'}] {label}{(' -- ' + detail) if detail else ''}")

    print("extract_clauses --selftest")

    units = scan(_FIXTURE, slug="fx")
    den = denominator(units)
    clauses = clauses_from_units(units)

    report("every normative unit becomes a clause (1:1, no model)",
           len(clauses) == len(den) == 4, f"{len(clauses)} clauses / {len(den)} units")
    report("every clause cites its source unit",
           all(c["source_unit_ids"] for c in clauses))
    report("compound units are FLAGGED, not silently split",
           sum(c["compound_candidate"] for c in clauses) >= 1)
    report("an already-atomic unit is not flagged compound",
           any(not c["compound_candidate"] for c in clauses))
    report("re-running is byte-identical without a model",
           json.dumps(clauses_from_units(scan(_FIXTURE, slug="fx"))) == json.dumps(clauses))

    with tempfile.TemporaryDirectory() as td:
        # KNOWN-GOOD: full coverage -> the receipt is clean
        r, _ = coverage_receipt(units, clauses, td)
        report("known-good: full coverage receipts CLEAN",
               r["ok"] and r["covered_count"] == len(den), f"{r['covered_count']}/{r['source_count']}")

        # KNOWN-BAD: drop one clause -> the receipt must CATCH it.
        # This is the whole reason the receipt exists — an extractor that loses a
        # requirement must not be able to report success.
        r2, _ = coverage_receipt(units, clauses[:-1], td)
        report("known-bad: a DROPPED clause is caught by the receipt",
               not r2["ok"] and r2["missing_count"] == 1, f"missing={r2['missing_count']}")

        # the splitter must never lose an id
        splits = {clauses[1]["source_unit_ids"][0]: ["capture the delta this round",
                                                     "do not name the Win"]}
        expanded = apply_splits(clauses, splits, "stub")
        report("a split expands one unit into several clauses",
               len(expanded) == len(clauses) + 1)
        r3, _ = coverage_receipt(units, expanded, td)
        report("after splitting, coverage is STILL complete (no id lost)", r3["ok"])
        report("split clauses record who split them",
               sum(1 for c in expanded if c["split_by"] == "stub") == 2)

        # a splitter that DROPS a unit must be caught, not trusted
        lossy = [c for c in expanded if c["source_unit_ids"][0] != den[0]["unit_id"]]
        r4, _ = coverage_receipt(units, lossy, td)
        report("a splitter that LOSES a unit is caught mechanically", not r4["ok"])

    # ── TEXT-SPAN COVERAGE: the loss the ID check is structurally blind to ──
    report("known-good: 1:1 clauses carry every content term forward",
           span_receipt(units, clauses)["ok"])
    report("known-good: a faithful split keeps text coverage clean",
           span_receipt(units, expanded)["ok"])

    # THE CASE THAT USED TO PRINT CLEAN — the id survives, half the rule does not.
    half = [c for c in expanded if c["text"] != "do not name the Win"]
    id_leg, _ = coverage_receipt(units, half, tempfile.mkdtemp(prefix="factory-span-"))
    span_leg = span_receipt(units, half)
    report("the ID check is BLIND to a half-dropped rule (this is the bug, shown)",
           id_leg["ok"], "id coverage says CLEAN")
    report("known-bad: TEXT coverage CATCHES the half-dropped rule",
           not span_leg["ok"] and len(span_leg["lossy_units"]) == 1,
           f"lost {span_leg['detail'][0]['missing_terms'] if span_leg['detail'] else []}")
    report("the receipt NAMES the dropped words, not just a count",
           "win" in span_leg["detail"][0]["missing_terms"])

    # a NEGATION cannot be quietly dropped -- it inverts the rule while looking intact
    inverted = [dict(c, text=c["text"].replace("do not name", "name"))
                for c in expanded]
    report("dropping a NEGATION is caught (never/not/no are not stopwords)",
           not span_receipt(units, inverted)["ok"])
    # ...but ordinary split debris (articles, conjunctions) must NOT false-fail
    reworded = [dict(c, text=c["text"].replace("the ", "").replace(" this", ""))
                for c in expanded]
    report("dropped articles/conjunctions do NOT false-fail a legitimate split",
           span_receipt(units, reworded)["ok"])
    report("the span receipt reports its own denominator, not just a verdict",
           span_receipt(units, clauses)["term_count"] > 0)

    # ── THE FALLBACK LADDER: proven with REAL subprocess execution, not mocked. ──
    # `bad_claude` is a real, executable binary that runs and produces nothing usable --
    # this is what "the primary rung fails" looks like on a live machine (a broken
    # install, an auth failure, a cold-start timeout), which is the failure mode the
    # portability audit actually found: zero fallback for exactly this case.
    with tempfile.TemporaryDirectory() as ld:
        def _stub(name, body):
            path = os.path.join(ld, name)
            with open(path, "w") as fh:
                fh.write(body)
            os.chmod(path, 0o755)
            return path

        bad_claude = _stub("claude-stub", "#!/bin/sh\nexit 1\n")
        missing_claude = os.path.join(ld, "no-such-claude-binary")

        # a codex stand-in that actually reads its own argv and writes real JSON to
        # wherever `-o` points -- so a PASS here means the real subprocess plumbing
        # (argv shape, -o handling, reading the file back) works end to end, not just
        # that the right branch was taken.
        good_codex = _stub("codex-stub", r"""#!/bin/sh
out=""
prev=""
for a in "$@"; do
  if [ "$prev" = "-o" ]; then out="$a"; fi
  prev="$a"
done
printf '[{"unit_id": "PROBE", "parts": ["part one", "part two"]}]' > "$out"
""")
        bad_codex = _stub("codex-broken", "#!/bin/sh\nexit 1\n")

        report("claude present but --selftest-injectable as missing is excluded from the ladder",
               splitter_ladder(claude_bin=missing_claude, codex_bin=good_codex) ==
               [("codex", good_codex)])

        # PRIMARY RUNG FAILS FOR REAL (a real executable that exits nonzero / prints
        # nothing) -> confirm the NEXT rung actually takes over and its real output
        # comes back, end to end through real subprocess calls.
        text, rung = run_splitter("split this", claude_bin=bad_claude, codex_bin=good_codex)
        report("primary rung (claude) genuinely fails -> the fallback rung (codex) fires",
               rung == "codex" and '"unit_id": "PROBE"' in text, f"rung={rung}")

        # the happy path is unaffected: claude present and working stays primary
        good_claude = _stub("claude-ok", '#!/bin/sh\nprintf \'[{"unit_id": "X", "parts": ["a"]}]\'\n')
        text2, rung2 = run_splitter("split this", claude_bin=good_claude, codex_bin=good_codex)
        report("a working primary rung is preferred over the fallback",
               rung2 == "claude", f"rung={rung2}")

        # ALL RUNGS FAIL -> must raise (fail closed), never return an empty split
        raised = False
        try:
            run_splitter("split this", claude_bin=bad_claude, codex_bin=bad_codex)
        except RuntimeError:
            raised = True
        report("every rung failing raises RuntimeError (fail-closed, never a silent empty split)",
               raised)

        # NEITHER BINARY EXISTS AT ALL -> the ladder is empty, and that raises too,
        # with a message that names the actual problem instead of a generic failure
        try:
            run_splitter("split this", claude_bin=missing_claude,
                        codex_bin=os.path.join(ld, "also-missing"))
            report("no usable binary anywhere raises (fail-closed)", False, "no raise")
        except RuntimeError as e:
            report("no usable binary anywhere raises (fail-closed)",
                   "neither" in str(e) and "available" in str(e))

    # fail-closed
    try:
        extract(os.devnull, "fx")
        report("refuses a spec with no normative units (fail-closed)", False, "no raise")
    except (ValueError, OSError):
        report("refuses a spec with no normative units (fail-closed)", True)

    # CLI contract
    me = os.path.abspath(__file__)
    with tempfile.TemporaryDirectory() as td:
        sp = os.path.join(td, "spec.md")
        with open(sp, "w") as fh:
            fh.write(_FIXTURE)
        p = subprocess.run([sys.executable, me, "--spec", sp, "--slug", "fx",
                            "--out", td], capture_output=True, text=True)
        report("CLI clean extraction -> exit 0", p.returncode == CLEAN, f"exit {p.returncode}")
        frozen = os.path.join(td, "fx-clauses.json")
        report("CLI freezes the clause set to disk", os.path.isfile(frozen))
        if os.path.isfile(frozen):
            d = json.loads(open(frozen).read())
            report("the frozen file carries the denominator + receipt, not just clauses",
                   "denominator" in d and "receipt" in d)
        p = subprocess.run([sys.executable, me, "--spec", os.path.join(td, "nope.md"),
                            "--slug", "fx"], capture_output=True, text=True)
        report("CLI missing spec -> exit 2 (fail-closed)", p.returncode == CANNOT_EVALUATE,
               f"exit {p.returncode}")

    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description="extract_clauses -- spec units -> atomic clauses + receipt")
    ap.add_argument("--spec")
    ap.add_argument("--slug", default="spec")
    ap.add_argument("--section")
    ap.add_argument("--out", help="directory to freeze <slug>-clauses.json into")
    ap.add_argument("--split", action="store_true", help="send COMPOUND units to a model to split")
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--batch-size", type=int, default=15)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())
    if not args.spec:
        _die("--spec is required")
    if not os.path.isfile(args.spec):
        _die(f"spec not found: {args.spec!r}")

    try:
        res = extract(args.spec, args.slug, section=args.section, do_split=args.split,
                      model=args.model, batch_size=args.batch_size,
                      workdir=args.out or None)
    except (ValueError, LookupError, RuntimeError) as e:
        _die(str(e))

    if args.out:
        os.makedirs(args.out, exist_ok=True)
        frozen = os.path.join(args.out, f"{args.slug}-clauses.json")
        with open(frozen, "w", encoding="utf-8") as fh:
            json.dump(res, fh, indent=2, ensure_ascii=False)
        res["frozen"] = frozen

    r, s = res["receipt"], res["span_receipt"]
    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        print(f"extract_clauses — {res['spec']}" + (f" § {res['section']}" if res["section"] else ""))
        print(f"  denominator (pinned mechanically): {res['denominator']}")
        print(f"  clauses extracted:                 {res['clause_count']}")
        print(f"  extraction:                        {res['extraction']}")
        print(f"  ID COVERAGE (is each unit cited):  "
              f"{'CLEAN' if r['ok'] else 'LOSS'} — {r['covered_count']}/{r['source_count']} "
              f"units cited, {r['missing_count']} uncited")
        print(f"  TEXT COVERAGE (does its text survive): "
              f"{'CLEAN' if s['ok'] else 'LOSS'} — {s['terms_kept']}/{s['term_count']} "
              f"content terms carried forward, {len(s['lossy_units'])} unit(s) lossy")
        if res.get("frozen"):
            print(f"  frozen to:                         {res['frozen']}")
        if not r["ok"]:
            # ⚠ NAME WHICH FAILURE MODE (fixed 2026-07-28, same first-second-skill run).
            # The receipt fails for THREE independent reasons -- missing (a unit cited by
            # nobody), ALIEN (a citation matching no unit), and duplicates -- and this
            # display printed only `missing`. So an ALIEN-driven LOSS rendered as
            # "LOSS — 17/17 units cited, 0 uncited" followed by an EMPTY list: a refusal
            # the operator cannot act on, and one that reads like a tool malfunction rather
            # than a finding. A verdict you cannot diagnose from its own output is the
            # silent-zero class in a different coat.
            if r["missing"]:
                print("  THE NO-DROP INVARIANT BROKE — these units are cited by no clause:")
                for u in r["missing"][:10]:
                    print(f"      {u}")
            if r.get("alien"):
                print("  ALIEN CITATIONS — cited, but matching no unit in the denominator:")
                for a in r["alien"][:10]:
                    print(f"      {a}")
                print("      (a backticked identifier in the clause TEXT reads as a citation —"
                      " check the manifest is de-backticked before blaming the extraction)")
            if not r["missing"] and not r.get("alien"):
                print(f"  COVERAGE REFUSED for a reason not shown above — raw receipt: "
                      f"{ {k: v for k, v in r.items() if k.endswith('_count') or k == 'ok'} }")
        if not s["ok"]:
            print("  TEXT WAS LOST — the id survived, the requirement did not:")
            for d in s["detail"][:10]:
                print(f"      {d['unit_id']}: dropped {d['missing_terms']}")
                print(f"          source:  {d['source_text'][:110]}")
                for t in d["clauses"][:3]:
                    print(f"          clause:  {t[:110]}")
    sys.exit(CLEAN if (r["ok"] and s["ok"]) else LOSS)


if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "system", "tools")))
    from utf8_stdio import force_utf8_stdio
    force_utf8_stdio()
    main()

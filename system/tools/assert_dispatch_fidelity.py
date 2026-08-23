#!/usr/bin/env python3
"""assert_dispatch_fidelity.py — proves a composed map-agent dispatch prompt actually
EMBEDDED the load-bearing rules from its brief, instead of paraphrasing them.

WHY (measured 2026-08-03, cal-weekly): the four map-agents dispatched by cal-weekly
Phase 0 are BLIND — they only see what's pasted into their dispatch prompt, never the
brief files themselves (map-agents/*.md, _map-format.md). On the 2026-08-03 run the
launching session summarized those briefs instead of pasting them, and two real rules
silently never reached the agents: the delta-only/HITL-note rule (0 of 4 dispatches)
and the "do NOT name a Win" prohibition (missing from 2 of 4).

WHAT THIS CHECKS: for each dispatch prompt file in a directory, whether a small set of
short, DISTINCTIVE LITERAL substrings from the source brief files are present in the
dispatch text. Matching is done on normalized text (whitespace collapsed, casefolded)
so line-wrap / reflow is tolerated — but wording changes are not: a paraphrase of a
required line will not match and is reported MISSING.

⛔ KNOWN BOUND — READ BEFORE TRUSTING A GREEN RESULT ⛔
This proves the STRING is present in the dispatch prompt. It does NOT prove:
  - the agent that received the prompt read it, understood it, or obeyed it
  - the rule was applied correctly during the agent's actual run
  - the dispatch prompt is otherwise faithful to the brief in any way not covered by
    the specific signatures below
A dispatch that contains every required signature can still produce a run that
violates every rule in it. This is a fidelity-of-TRANSMISSION check, not a
fidelity-of-BEHAVIOR check. Treat a PASS as "the rule reached the agent," never as
"the agent complied."

USAGE:
    python3 assert_dispatch_fidelity.py --dispatch-dir <dir>
    python3 assert_dispatch_fidelity.py --selftest

Exit code: 0 only if every dispatch file in the directory carries every signature
required of it (the shared _map-format.md signatures, plus its angle-specific
signatures if the filename identifies an angle). Non-zero otherwise, and every miss
is listed by name with the literal text that was expected.

Pure stdlib. No third-party dependencies.
"""

import argparse
import glob
import json
import os
import re
import sys

# fanout-lab/arm_lib.py is the ONE shared contract with compose_arm.py (S13.20/S13.21 —
# the composer emits exactly what this checker validates). Imported lazily-but-eagerly here
# (legacy --dispatch-dir-only mode never touches it) so an arm-aware run can never drift from
# what actually composed the dispatch: same region-splitting code on both sides of the seam.
# ⚠ REPOINTED IN MIGRATION (T9.7a, 2026-08-15): `system/tools/fanout-lab/` is NOT ported yet
# (it lands separately, T9.8c, with fresh fixtures — never copied). Legacy mode (--dispatch-dir
# with no --arm-spec, the ONLY mode planning-weekly's prompt actually calls) never touches
# arm_lib, so the import is now OPTIONAL: it succeeds once fanout-lab lands, and until then
# arm-aware mode (--arm-spec) fails loud with CANNOT EVALUATE naming the missing module,
# instead of crashing the whole tool — including legacy mode — at import time.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fanout-lab"))
try:
    import arm_lib  # noqa: E402
except ImportError as _arm_lib_import_error:
    arm_lib = None
    _ARM_LIB_IMPORT_ERROR = str(_arm_lib_import_error)

# ---------------------------------------------------------------------------
# Normalization — collapse whitespace, casefold. Tolerates reflow; a reworded
# line no longer contains the literal substring and will correctly miss.
# ---------------------------------------------------------------------------


def normalize(text: str) -> str:
    text = text.casefold()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ---------------------------------------------------------------------------
# REQUIRED-SIGNATURE TABLE
#
# Each signature is a tuple of one or more literal substrings, copied verbatim
# from the brief source files. ALL substrings in a tuple must be present (AND)
# for the signature to count as PRESENT — this lets a single rule that spans a
# markdown bold marker or an inline note be checked as two anchor phrases
# without over-fitting to the exact markdown formatting around them.
#
# Source files read to derive these (2026-08-03, donor cal-weekly; repointed T9.7a to the
# migrated planning-weekly location. The scrub also replaced a personal first name with the
# generic placeholder "the person" in two signature literals below
# (audit-biological:one-body, delta-vs-monthly:mark-phase1) —
# updated to match, and re-verified against the live scrubbed briefs by
# verify_signature_provenance() below, not just asserted):
#   .claude/skills/planning-weekly/prompts/map-agents/_map-format.md   (shared — every dispatch)
#   .claude/skills/planning-weekly/prompts/map-agents/conflicts.md
#   .claude/skills/planning-weekly/prompts/map-agents/lanes.md
#   .claude/skills/planning-weekly/prompts/map-agents/audit-biological.md
#   .claude/skills/planning-weekly/prompts/map-agents/delta-vs-monthly.md
# ---------------------------------------------------------------------------

REQUIRED_SIGNATURES = {
    "shared": {
        "label": "_map-format.md (shared format — embedded in EVERY dispatch)",
        "signatures": {
            "no-win": (
                "Do NOT judge, conclude, or name a Win.",
            ),
            "delta-only-hitl": (
                "Delta-only read:",
                "an item carrying a HITL note",
            ),
            # ⚠ REPAIRED 2026-08-03 — this was a PHANTOM signature and it failed every correct run.
            # It required "one line each, no exceptions", a literal that commit 815f647 REMOVED from
            # _map-format.md in the very same commit that added it here: the compact-ledger rewrite
            # split that sentence into "…accounted for, no exceptions" (the heading) and "SIGNAL — one
            # line each, with its reason" (the SIGNAL rule). Both halves below exist in the live brief.
            "ledger-no-exceptions": (
                "accounted for, no exceptions",
                "one line each, with its reason",
            ),
            "ledger-backticks": (
                "Write the id inside backticks",
            ),
            "ledger-noise-first-class": (
                "NOISE is a first-class",
            ),
            "ledger-every-id-including": (
                "Every id, including ones another agent will obviously claim.",
            ),
            "ledger-never-invent": (
                "Never invent an id to satisfy the ledger.",
            ),
            "thin-findings": (
                "Return thin findings + pointers, never pasted raw bodies.",
            ),
        },
    },
    "conflicts": {
        "label": "conflicts.md",
        "signatures": {
            "angle-definition": (
                "Overlapping commitments, things that can't both be true",
            ),
            "do-not-resolve": (
                "Do NOT resolve the conflicts, rank-to-drop, or conclude",
            ),
        },
    },
    "lanes": {
        "label": "lanes.md",
        "signatures": {
            "embedded-lanes": (
                "The lanes are EMBEDDED in your dispatch brief",
            ),
            "quiet-lane-signal": (
                "A quiet lane is a SIGNAL, not missing data",
            ),
            "do-not-rank-or-name-win": (
                "Do NOT rank lanes against each other or name a Win",
            ),
        },
    },
    "audit-biological": {
        "label": "audit-biological.md",
        "signatures": {
            "one-body": (
                "the person as one biological body moving through real space and time this week",
            ),
            "shadow-task-def": (
                "something that must happen but isn't on any list yet",
            ),
            "shake-loose": (
                "you shake shadow tasks loose",
            ),
        },
    },
    "delta-vs-monthly": {
        "label": "delta-vs-monthly.md",
        "signatures": {
            "embedded-goal": (
                "The monthly goal/plan is EMBEDDED in your dispatch brief",
            ),
            "orientation-before-orientation": (
                "orientation before orientation",
            ),
            "mark-phase1": (
                "you MARK; the person decides in Phase 1.",
            ),
        },
    },
}

# Filename -> angle key matchers. Checked in order; first match wins. Order
# matters only where substrings could collide (none currently do, but
# "biological"/"delta"+"monthly" are checked before the shorter "conflict"/
# "lane" tokens out of caution).
ANGLE_MATCHERS = [
    ("audit-biological", lambda name: "biological" in name),
    ("delta-vs-monthly", lambda name: "delta" in name and "monthly" in name),
    ("conflicts", lambda name: "conflict" in name),
    ("lanes", lambda name: "lane" in name),
]


# ---------------------------------------------------------------------------
# PROVENANCE — the checker must verify ITS OWN signatures before it checks anything
#
# ⭐ WHY THIS EXISTS (2026-08-03, earned the hard way, same day the tool shipped).
# A signature in the table above is only meaningful if the literal ACTUALLY APPEARS in the
# brief it claims to be quoting. On 2026-08-03 one did not: the compact-ledger rewrite changed
# _map-format.md and the signature was authored against the PRE-rewrite wording, in the same
# commit. The result was a gate that FAILED 100% OF CORRECT RUNS while reporting a
# transmission failure that had not happened — on the one check whose whole job is proving a
# paste was faithful. A gate that fails every correct run gets routed around within two runs,
# and then it is guarding nothing.
# ⛔ AND THE SELFTEST DID NOT CATCH IT, because its fixture was hand-typed from the same stale
# wording as the table — the fixture and the code shared one mental model, so they agreed with
# each other and disagreed with reality. (This project's own law: "a signature validated on a
# hand-built fixture proves nothing.")
# ▶ THE FIX IS STRUCTURAL, not a re-typed string: every literal is now checked against its
# source file BEFORE any dispatch is graded. A drifted signature is CANNOT-EVALUATE (exit 2),
# named out loud — never a silent FAIL that looks like a real paste error.
# ---------------------------------------------------------------------------

BRIEF_SOURCES = {
    "shared": ".claude/skills/planning-weekly/prompts/map-agents/_map-format.md",
    "conflicts": ".claude/skills/planning-weekly/prompts/map-agents/conflicts.md",
    "lanes": ".claude/skills/planning-weekly/prompts/map-agents/lanes.md",
    "audit-biological": ".claude/skills/planning-weekly/prompts/map-agents/audit-biological.md",
    "delta-vs-monthly": ".claude/skills/planning-weekly/prompts/map-agents/delta-vs-monthly.md",
}

CLONE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def verify_signature_provenance():
    """Every required literal must be findable in the brief it claims to quote.

    Returns (phantoms, unreadable): phantoms is a list of
    (group, signature_name, substring, source_path) for literals that are NOT in their source;
    unreadable is a list of (group, source_path, error) for briefs that could not be read.
    An empty pair means every signature is grounded in a real file, this session.
    """
    phantoms, unreadable = [], []
    for group, source_rel in BRIEF_SOURCES.items():
        block = REQUIRED_SIGNATURES.get(group)
        if not block:
            continue
        path = os.path.join(CLONE_ROOT, source_rel)
        try:
            with open(path, encoding="utf-8") as fh:
                brief_norm = normalize(fh.read())
        except OSError as exc:
            unreadable.append((group, source_rel, str(exc)))
            continue
        for sig_name, substrings in block["signatures"].items():
            for sub in substrings:
                if normalize(sub) not in brief_norm:
                    phantoms.append((group, sig_name, sub, source_rel))
    return phantoms, unreadable


def report_provenance() -> int:
    """Print the provenance verdict. Returns 0 if grounded, 2 if it CANNOT EVALUATE."""
    phantoms, unreadable = verify_signature_provenance()
    if not phantoms and not unreadable:
        return 0
    print("CANNOT EVALUATE — this checker's own signatures do not match the briefs they quote.")
    print("  A grade now would report a paste failure that did not happen. Fix the table first.")
    for group, sig_name, sub, src in phantoms:
        print(f"  PHANTOM  {group}:{sig_name} — {sub!r} is NOT in {src}")
    for group, src, err in unreadable:
        print(f"  UNREADABLE  {group} — {src}: {err}")
    return 2


def detect_angle(filename: str):
    name = filename.lower()
    for angle_key, matcher in ANGLE_MATCHERS:
        if matcher(name):
            return angle_key
    return None


def signature_present(haystack_norm: str, substrings) -> bool:
    return all(normalize(s) in haystack_norm for s in substrings)


def check_dispatch_text(text: str, angle_key):
    """Returns (present, missing) as lists of (full_name, substrings) tuples."""
    haystack_norm = normalize(text)
    present = []
    missing = []

    groups = [("shared", REQUIRED_SIGNATURES["shared"])]
    if angle_key is not None:
        groups.append((angle_key, REQUIRED_SIGNATURES[angle_key]))

    for group_key, group in groups:
        for sig_name, substrings in group["signatures"].items():
            full_name = f"{group_key}:{sig_name}"
            if signature_present(haystack_norm, substrings):
                present.append((full_name, substrings))
            else:
                missing.append((full_name, substrings))

    return present, missing


def format_substrings(substrings) -> str:
    if len(substrings) == 1:
        return f'"{substrings[0]}"'
    quoted = ", ".join(f'"{s}"' for s in substrings)
    return f"requires ALL of: {quoted}"


# ---------------------------------------------------------------------------
# ARM-AWARE MODE (S13.21) — per-arm signature sets, built FROM the arm's own manifest
# instead of the static REQUIRED_SIGNATURES table above.
#
# WHY: the static table above hardcodes ONE correct coverage-ledger text (the live
# skills/cal-weekly/prompts/map-agents/*.md wording). The fanout-lab experiment runs ~15
# arms that deliberately VARY the coverage ledger (enumerated / declarative-one-line /
# absent — see compose_arm.py). Graded against the static table, an arm that removes the
# ledger on purpose would FAIL — not because the arm is wrong, but because the checker
# assumed exactly one correct ledger text. That would have blocked the experiment on day
# one and read as a finding about the arm rather than a limitation of the checker.
#
# HOW: arm-aware mode never hardcodes a signature. For the THREE angle-invariant regions
# (everything the arm does NOT touch) it re-reads the SAME frozen brief file compose_arm.py
# composed from — at the path the arm's own manifest names, fresh every run — and requires
# those regions verbatim (normalize()-tolerant of reflow). For the ledger + bundle regions
# (what the arm DOES vary) it builds the expected signatures by calling the SAME arm_lib
# render_* functions compose_arm.py used to write them, with the arm manifest's OWN
# item_count / ledger_variant / bundle numbers. Same code on both sides of the seam — this
# is structurally the same guarantee verify_signature_provenance() gives the legacy table
# (abort rather than mis-grade on drift), except here drift is impossible by construction:
# there is no second hand-typed copy of the literals to drift FROM.
# ---------------------------------------------------------------------------


def region_signatures(regions: dict) -> dict:
    """One signature per angle-invariant region — the parts of the brief this arm did NOT
    touch. Full-block substring match; normalize() already tolerates paste/reflow, so this
    still catches a dropped or reworded region, not just an exact-byte diff."""
    sigs = {}
    for name in ("r1_preamble", "r2_middle", "r3_post_fence", "r4_tail"):
        text = regions[name]
        if text.strip():
            sigs[f"region:{name}"] = (text,)
    return sigs


def bundle_signatures(bundle: dict) -> dict:
    """The FIRST parameterised class (compose_arm.py docstring): the bundle reference. All
    five numbers checked: path, line count, ~KB size, and the read ranges (as one joined
    string if there is more than one, so a checker miss names the whole clause)."""
    ranges = bundle["read_ranges"]
    ranges_sig = ranges[0] if len(ranges) == 1 else ", ".join(ranges)
    return {
        "bundle-path": (bundle["path"],),
        "bundle-line-count": (f"It is {bundle['lines']} lines",),
        "bundle-kb": (f"~{bundle['kb']}KB",),
        "bundle-read-ranges": (ranges_sig,),
    }


def ledger_signatures(variant: str, item_count: int, angle_key: str) -> dict:
    """THIRD parameterised class (the ledger block itself) + SECOND (item count, embedded
    inside it) — one signature set per variant, built from arm_lib's own render functions so
    it can never drift from what compose_arm.py actually wrote."""
    if variant == "enumerated":
        return {
            "ledger-return-heading": ("### Coverage ledger (REQUIRED",),
            "ledger-rules-heading": (arm_lib.A2_LEDGER_RULES_HEADING,),
            "ledger-count-sentence": (
                f"There are {item_count} items. Your ledger must have {item_count} lines.",
            ),
            "ledger-backticks": ("Write each id **inside backticks**",),
            "ledger-noise-first-class": ("NOISE is a first-class",),
            "ledger-never-invent": ("NEVER invent an id",),
        }
    if variant == "declarative-one-line":
        return {
            "declarative-heading": ("declare completeness in ONE line",),
            "declarative-count-sentence": (
                f"I read all {item_count} items handed to me in full",
            ),
            "declarative-no-enumeration": ("Do NOT enumerate ids one by one",),
        }
    if variant == "absent":
        return {
            "ledger-omitted-marker": ("OMITTED FOR THIS ARM",),
            "ledger-omitted-explain": (
                "no per-item or declarative coverage statement is required",
            ),
        }
    raise ValueError(f"unknown ledger_variant: {variant!r}")


def ledger_forbidden_signatures(variant: str) -> dict:
    """The OTHER two variants' distinctive markers — proves the variant that should have
    been REMOVED actually was, not just that the expected one is present. A dispatch that
    contains BOTH the declarative sentence AND the full enumerated ledger is not a clean
    arm; this catches that leak."""
    markers = {
        "enumerated": ("one line each, no exceptions",),
        "declarative-one-line": ("declare completeness in ONE line",),
        "absent": ("OMITTED FOR THIS ARM",),
    }
    return {f"not-leaked:{k}": v for k, v in markers.items() if k != variant}


def build_arm_required_signatures(arm_manifest: dict, angle_key: str) -> dict:
    """Re-reads the frozen brief this angle's dispatch was composed FROM (fresh, at the
    manifest's own recorded path) and returns the full required-signature dict: angle-
    invariant regions + bundle + ledger. Raises BriefParseError / OSError on drift or a
    missing source — arm-aware grading must CANNOT-EVALUATE, never silently mis-grade, on
    exactly the same principle as verify_signature_provenance() above."""
    fname = arm_lib.ANGLE_BRIEF_FILENAME[angle_key]
    src_path = os.path.join(arm_manifest["frozen_briefs_dir"], fname)
    with open(src_path, encoding="utf-8") as fh:
        frozen_text = fh.read()
    regions = arm_lib.split_brief(frozen_text)  # raises BriefParseError on structural drift

    sigs = {}
    sigs.update(region_signatures(regions))
    sigs.update(bundle_signatures(arm_manifest["bundle"]))
    sigs.update(ledger_signatures(arm_manifest["ledger_variant"], arm_manifest["item_count"],
                                   angle_key))
    return sigs


def check_dispatch_text_arm_aware(text: str, required: dict, forbidden: dict):
    """Returns (present, missing, leaked) — leaked = a forbidden marker from a NON-chosen
    ledger variant was found anyway (see ledger_forbidden_signatures)."""
    haystack_norm = normalize(text)
    present, missing, leaked = [], [], []
    for sig_name, substrings in required.items():
        if signature_present(haystack_norm, substrings):
            present.append((sig_name, substrings))
        else:
            missing.append((sig_name, substrings))
    for sig_name, substrings in forbidden.items():
        if signature_present(haystack_norm, substrings):
            leaked.append((sig_name, substrings))
    return present, missing, leaked


def run_check_arm_aware(dispatch_dir: str, arm_spec_path: str) -> int:
    if arm_lib is None:
        print("CANNOT EVALUATE — arm-aware mode (--arm-spec) requires "
              "system/tools/fanout-lab/arm_lib.py, which is not present in this tree "
              f"({_ARM_LIB_IMPORT_ERROR}). fanout-lab lands separately (T9.8c); the legacy "
              "--dispatch-dir-only mode (omit --arm-spec) does not need it and is unaffected.")
        return 2
    try:
        with open(arm_spec_path, encoding="utf-8") as fh:
            arm_manifest = json.load(fh)
    except OSError as exc:
        print(f"CANNOT EVALUATE — arm manifest unreadable: {arm_spec_path}: {exc}")
        return 2
    except json.JSONDecodeError as exc:
        print(f"CANNOT EVALUATE — arm manifest is not valid JSON: {arm_spec_path}: {exc}")
        return 2

    required_keys = ("arm_id", "frozen_briefs_dir", "ledger_variant", "item_count", "bundle")
    missing_keys = [k for k in required_keys if k not in arm_manifest]
    if missing_keys:
        print(f"CANNOT EVALUATE — arm manifest {arm_spec_path} is missing field(s): "
              f"{missing_keys}")
        return 2

    if not os.path.isdir(dispatch_dir):
        print(f"ERROR: dispatch dir not found: {dispatch_dir}", file=sys.stderr)
        return 2

    paths = sorted(
        p for p in glob.glob(os.path.join(dispatch_dir, "*"))
        if os.path.isfile(p) and not os.path.basename(p).endswith(".json")
    )
    if not paths:
        print(f"ERROR: no dispatch files found in {dispatch_dir}", file=sys.stderr)
        return 2

    print(f"ARM: {arm_manifest['arm_id']}  ledger_variant={arm_manifest['ledger_variant']}  "
          f"item_count={arm_manifest['item_count']}")
    print(f"  frozen briefs source: {arm_manifest['frozen_briefs_dir']}")
    print()

    overall_ok = True
    total_missing = 0
    total_leaked = 0

    for path in paths:
        filename = os.path.basename(path)
        angle_key = arm_lib.detect_angle(filename)
        print(f"=== {filename} ===")
        if angle_key is None:
            print("  RESULT: CANNOT EVALUATE — filename does not identify a known angle "
                  f"({list(arm_lib.ANGLE_BRIEF_FILENAME.values())})")
            overall_ok = False
            continue

        try:
            required = build_arm_required_signatures(arm_manifest, angle_key)
        except (arm_lib.BriefParseError, OSError) as exc:
            print(f"  RESULT: CANNOT EVALUATE — could not derive required signatures from "
                  f"the frozen brief this arm claims to be composed from: {exc}")
            overall_ok = False
            continue
        forbidden = ledger_forbidden_signatures(arm_manifest["ledger_variant"])

        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        present, missing, leaked = check_dispatch_text_arm_aware(text, required, forbidden)

        print(f"  angle: {angle_key}")
        print(f"  PRESENT ({len(present)}):")
        for full_name, _ in present:
            print(f"    - {full_name}")
        print(f"  MISSING ({len(missing)}):")
        for full_name, substrings in missing:
            print(f"    - {full_name} — {format_substrings(substrings)}")
        if leaked:
            print(f"  LEAKED — a DIFFERENT arm's ledger marker was found ({len(leaked)}):")
            for full_name, substrings in leaked:
                print(f"    - {full_name} — {format_substrings(substrings)}")

        if missing or leaked:
            overall_ok = False
            total_missing += len(missing)
            total_leaked += len(leaked)
            print("  RESULT: FAIL")
        else:
            print("  RESULT: PASS")
        print()

    print("=" * 60)
    if overall_ok:
        print(f"OVERALL: PASS — {len(paths)} dispatch(es), 0 missing, 0 leaked signatures "
              f"(arm: {arm_manifest['arm_id']}).")
        return 0
    else:
        print(f"OVERALL: FAIL — {total_missing} missing / {total_leaked} leaked signature(s) "
              f"across {len(paths)} dispatch(es) (arm: {arm_manifest['arm_id']}).")
        return 1


def run_check(dispatch_dir: str) -> int:
    # Verify the verifier FIRST: a drifted signature must never masquerade as a paste failure.
    rc = report_provenance()
    if rc:
        return rc
    if not os.path.isdir(dispatch_dir):
        print(f"ERROR: dispatch dir not found: {dispatch_dir}", file=sys.stderr)
        return 2

    paths = sorted(
        p for p in glob.glob(os.path.join(dispatch_dir, "*"))
        if os.path.isfile(p)
    )
    if not paths:
        print(f"ERROR: no files found in {dispatch_dir}", file=sys.stderr)
        return 2

    overall_ok = True
    total_missing = 0

    for path in paths:
        filename = os.path.basename(path)
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()

        angle_key = detect_angle(filename)
        present, missing = check_dispatch_text(text, angle_key)

        print(f"=== {filename} ===")
        if angle_key is not None:
            print(f"  angle: {angle_key} ({REQUIRED_SIGNATURES[angle_key]['label']})")
        else:
            print("  angle: UNRECOGNIZED by filename — checking shared signatures only")

        print(f"  PRESENT ({len(present)}):")
        for full_name, _ in present:
            print(f"    - {full_name}")

        print(f"  MISSING ({len(missing)}):")
        for full_name, substrings in missing:
            print(f"    - {full_name} — {format_substrings(substrings)}")

        if missing:
            overall_ok = False
            total_missing += len(missing)
            print("  RESULT: FAIL")
        else:
            print("  RESULT: PASS")
        print()

    print("=" * 60)
    if overall_ok:
        print(f"OVERALL: PASS — {len(paths)} dispatch(es), 0 missing signatures.")
        return 0
    else:
        print(f"OVERALL: FAIL — {total_missing} missing signature(s) across {len(paths)} dispatch(es).")
        return 1


# ---------------------------------------------------------------------------
# --selftest — TWO-SIDED. A synthetic dispatch carrying every signature must
# PASS; a synthetic dispatch with one signature reworded must FAIL and name
# exactly that signature as missing (and only that one).
# ---------------------------------------------------------------------------


def _build_good_dispatch() -> str:
    """A synthetic dispatch embedding every 'shared' + 'conflicts' signature.

    ⭐ BUILT FROM THE TABLE, NEVER HAND-TYPED (repaired 2026-08-03). The previous version
    typed the rules out by hand, which is precisely how this tool shipped green while broken:
    the fixture carried the same stale wording as the table, so the two agreed with each other
    and both disagreed with the live brief. A fixture derived from the table can only drift if
    the table drifts — and the table is now pinned to the real briefs by
    verify_signature_provenance(). Reflowed at 60 chars so whitespace-tolerance is still proven.
    """
    import textwrap
    parts = ["You are a fresh-context map-agent.", "", "## YOUR ONE ANGLE: CONFLICTS", ""]
    for group in ("shared", "conflicts"):
        for substrings in REQUIRED_SIGNATURES[group]["signatures"].values():
            for sub in substrings:
                parts.append(textwrap.fill(sub, width=60))
    return "\n".join(parts).strip()


def _build_bad_dispatch() -> str:
    """Same as the good dispatch, but the 'no-win' rule is REWORDED (a real
    paraphrase, not a whitespace reflow) — must be reported missing."""
    good = _build_good_dispatch()
    reworded = good.replace(
        "Do NOT judge, conclude, or name a Win.",
        "Do NOT judge or draw conclusions or call out a winner.",
    )
    assert reworded != good, "selftest setup bug: reword did not apply"
    return reworded


def run_selftest() -> int:
    ok = True

    # --- side 0: PROVENANCE — every signature must exist in the brief it quotes ---
    # This is the check that would have caught the 2026-08-03 phantom on the day it shipped.
    print("--- selftest: SIGNATURE PROVENANCE (every literal must be in its source brief) ---")
    phantoms, unreadable = verify_signature_provenance()
    if phantoms or unreadable:
        ok = False
        for group, sig_name, sub, src in phantoms:
            print(f"  FAIL: PHANTOM {group}:{sig_name} — {sub!r} not in {src}")
        for group, src, err in unreadable:
            print(f"  FAIL: UNREADABLE {group} — {src}: {err}")
    else:
        n = sum(len(subs) for g in BRIEF_SOURCES if g in REQUIRED_SIGNATURES
                for subs in REQUIRED_SIGNATURES[g]["signatures"].values())
        print(f"  PASS: all {n} literals found in their source briefs.")

    # --- side 1: everything present -> must PASS ---
    good_text = _build_good_dispatch()
    present, missing = check_dispatch_text(good_text, "conflicts")
    print("--- selftest: GOOD dispatch (all signatures present, reflowed) ---")
    print(f"  present: {len(present)}, missing: {len(missing)}")
    if missing:
        ok = False
        print("  UNEXPECTED MISSING:")
        for full_name, substrings in missing:
            print(f"    - {full_name} — {format_substrings(substrings)}")
        print("  FAIL: expected 0 missing, got", len(missing))
    else:
        print("  PASS: 0 missing, as expected.")
    print()

    # --- side 2: one signature reworded -> must FAIL and name it ---
    bad_text = _build_bad_dispatch()
    present2, missing2 = check_dispatch_text(bad_text, "conflicts")
    missing_names = {name for name, _ in missing2}
    print("--- selftest: BAD dispatch (no-win rule reworded, not reflowed) ---")
    print(f"  present: {len(present2)}, missing: {len(missing2)}")
    print(f"  missing names: {sorted(missing_names)}")
    if "shared:no-win" in missing_names and len(missing2) == 1:
        print("  PASS: exactly 'shared:no-win' reported missing, nothing else.")
    else:
        ok = False
        if "shared:no-win" not in missing_names:
            print("  FAIL: expected 'shared:no-win' to be reported missing — it was not.")
        if len(missing2) != 1:
            print(f"  FAIL: expected exactly 1 missing signature, got {len(missing2)}: {sorted(missing_names)}")
    print()

    if ok:
        print("SELFTEST: PASS (both sides correct)")
        return 0
    else:
        print("SELFTEST: FAIL")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="Assert composed cal-weekly dispatch prompts embed the load-bearing "
        "literal rules from their briefs (not a paraphrase)."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dispatch-dir", help="Directory of composed dispatch prompt files to check.")
    group.add_argument("--selftest", action="store_true", help="Run the built-in two-sided selftest.")
    parser.add_argument(
        "--arm-spec",
        help="Path to a compose_arm.py-emitted arm-manifest.json. When given (with "
             "--dispatch-dir), grades ARM-AWARE: required signatures are derived from THIS "
             "arm's own ledger_variant/item_count/bundle + a fresh re-read of the frozen "
             "brief it was composed from, instead of the static REQUIRED_SIGNATURES table. "
             "Omit for the legacy/live cal-weekly dispatch-fidelity check.",
    )
    args = parser.parse_args()

    if args.selftest:
        sys.exit(run_selftest())
    elif args.arm_spec:
        sys.exit(run_check_arm_aware(args.dispatch_dir, args.arm_spec))
    else:
        sys.exit(run_check(args.dispatch_dir))


if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "system", "tools")))
    from utf8_stdio import force_utf8_stdio
    force_utf8_stdio()
    main()

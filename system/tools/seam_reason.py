#!/usr/bin/env python3
"""
seam_reason.py — the 5,000-FT SEAM LANE, Efficiency's second altitude (PORTED 2026-08-14
from claudeops-config's system/tools/seam_reason.py).

── WHAT THIS ANSWERS ────────────────────────────────────────────────────────
The ground lane (`recommend.py`) asks "is THIS thing broken?". This one asks the question
nothing else in the system can ask: **"do these parts work together, or do they fight?"**

A SEAM is not a broken part. It is two or more parts that SHARE something and DISAGREE about
it. No individual component is failing, which is exactly why no per-component detector can
see one.

── THE FOUR SEAM CLASSES (mechanically decidable; no LLM anywhere in this file) ──
  (a) LABEL-VS-COMPUTED    — an element's frontmatter `maturity_label:` disagrees with its own
                             `## AUTO-COMPUTED` value. The BASE word is machine-owned, so a
                             disagreement means a human typed over a machine's verdict.
  (b) MANIFEST-ORPHAN      — a fire-tested guard backing no element, OR a stated element with
                             no guard in `label_manifest.yaml`.
  (c) SHARED-SOURCE SPLIT  — two elements cite the same `source_path` in `computed_edges`
                             while making DIFFERENT maturity claims. One file, two stories.
  (d) CO-FAILURE           — two producers that keep going non-OK in the SAME hour, read
                             straight off Hospital's own findings union, never off a document.

── WHAT IT NEVER DOES ───────────────────────────────────────────────────────
  · It never APPLIES a fix — this lane SUGGESTS, never applies (`--selftest`'s BAR 3 greps for
    an applier-shaped symbol and fails the run if one exists).
  · It never invents a store or an altitude. It writes through `emit_recommendation.py`, the
    one validated door, at `SUBSYSTEM` — a value that already exists in `VALID_ALTITUDE`.
  · It never surfaces something a human already ruled. Any element carrying a
    `gap_disposition:` is FILTERED OUT before emission (see `RULING_CAN_EXPLAIN`).
  · It never emits without evidence. The writer refuses (and canaries) an empty `evidence`;
    this file passes real file paths and measured counts, never a recollection.

── EVERY FINDING CARRIES THREE FIELDS, ALL REQUIRED ──
  the named SEAM (which parts) · the FINGERPRINTS (what proves it, re-derivable by hand) ·
  the named TARGETS (concrete files to open). An altitude without an action is useless — a
  named seam with no target to open is the same failure one layer down.

⚠ THREE OF THE FOUR CLASSES DEPEND ON `system/organism/` — CONFIRMED ABSENT FROM THIS REPO.
`ELEMENTS`/`MANIFEST`(the frontmatter one)/`GRAPH`/`MANUAL` all point at the donor's own
self-documentation apparatus (`system/organism/elements/*.md`, `manual.md`,
`generated/organism-map.json`) — a 49-file map of the DONOR's OWN architecture that has no
equivalent here and does not belong here (same exclusion class as `organism-health.py`, per
this port's own instructions). Rather than special-case each detector around that absence,
this ships AS-IS and lets each reader's own existing "return [] on missing path" fallback do
the honest thing:
  · `read_elements()` globs `ELEMENTS/*.md` — returns `{}` when the directory doesn't exist.
  · `read_edges()` checks `GRAPH.exists()` first — returns `[]`.
  · With `elements={}`, class (a) finds nothing (no frontmatter to compare) and class (c)
    finds nothing (no elements to cite). ⚠ Class (b)'s SECOND half (MANIFEST-ORPHAN-GUARD:
    "a guard id with no matching element") WILL fire for every guard in
    `label_manifest.yaml`, because `slugs = set(elements)` is empty — every id is
    technically "unmapped". That is TRUE (there genuinely is no element map here) but not a
    per-guard defect to chase; it is one fact ("this repo has no elements/ map") restated N
    times. Left as an honest, if noisy, signal rather than filtered — filtering it would be
    exactly the kind of silent suppression `security-health.py`'s own docstring argues
    against elsewhere in this port.
  · Class (d) CO-FAILURE has NO organism/ dependency at all — it reads
    `findings_reader.findings_report()` directly, which this repo's Hospital findings store
    (shipped alongside this file) already populates. This is the one class fully live here.

Reads: Hospital's findings union (`findings_reader.py`, shipped) — never organism/ files that
don't exist, past the graceful-empty fallbacks above.
Writes: through `emit_recommendation.py` only, at SUBSYSTEM altitude.

Usage:
  seam_reason.py                  # detect + WRITE recommendations (the supervised path)
  seam_reason.py --dry-run        # detect + print, write nothing
  seam_reason.py --json           # machine-readable detection payload, writes nothing
  seam_reason.py --selftest       # prove the acceptance bar against LIVE data; writes nothing
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "organism"))

REPO = Path(__file__).resolve().parents[2]
ELEMENTS = REPO / "system" / "organism" / "elements"
MANIFEST = REPO / "system" / "tools" / "organism" / "label_manifest.yaml"
GRAPH = REPO / "system" / "organism" / "generated" / "organism-map.json"
MANUAL = REPO / "system" / "organism" / "manual.md"

PRODUCER = "seam-reason"
ALTITUDE = "SUBSYSTEM"


# ───────────────────────────── readers ─────────────────────────────
def _base(label: str) -> str:
    """The machine-owned BASE word. Suffixes (·gap, [provisional], (honor)) are human-owned.

    STRIPS MARKDOWN EMPHASIS FIRST. These files are markdown, so a label may legitimately be
    written `LIVE·gap` in backticks or **LIVE** in bold — without normalising that first, a
    label would falsely appear to contradict itself against its own AUTO-COMPUTED value.

    ⚠ THIS IS NORMALISATION, NOT A LOOSENED DEFINITION. Backticks and asterisks are
    PRESENTATION; the label VALUE is the word. Nothing here makes two different words compare
    equal.
    """
    if not label:
        return ""
    cleaned = label.strip().strip("`*_ ").lstrip("`*_")
    if not cleaned:
        return ""
    return cleaned.split()[0].split("·")[0].strip("`*_").upper()


def read_elements() -> dict:
    """slug -> {file, frontmatter_label, computed_label, gap_disposition, sources}.

    Returns `{}` when ELEMENTS doesn't exist (confirmed the case in this repo) — `.glob()` on
    a missing directory raises nothing and simply yields no paths."""
    out = {}
    for p in sorted(ELEMENTS.glob("*.md")):
        if p.name.endswith(".draft"):
            continue
        try:
            t = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        slug = (re.search(r"(?m)^element:\s*(.+)$", t) or [None, p.stem])[1]
        slug = slug.strip() if isinstance(slug, str) else p.stem
        fm = re.search(r"(?m)^maturity_label:\s*(.+)$", t)
        comp = re.search(r"(?m)^-\s*\*\*maturity_label:\*\*\s*(.+)$", t)
        gap = re.search(r"(?m)^gap_disposition:\s*(.+)$", t)
        srcs = re.findall(r"(?m)^\s+-\s+(\S+\.(?:py|sh|md|json|yaml))\s*$", t)
        out[slug] = {
            "file": str(p.relative_to(REPO)),
            "frontmatter_label": fm.group(1).strip() if fm else "",
            "computed_label": comp.group(1).strip() if comp else "",
            "gap_disposition": gap.group(1).strip() if gap else "",
            "sources": srcs,
        }
    return out


def read_manifest_ids() -> list:
    if not MANIFEST.exists():
        return []
    return re.findall(r"(?m)^\s*-\s*id:\s*(\S+)", MANIFEST.read_text(encoding="utf-8"))


def read_edges() -> list:
    if not GRAPH.exists():
        return []
    try:
        return json.loads(GRAPH.read_text(encoding="utf-8")).get("computed_edges", []) or []
    except Exception:
        return []


CO_FAIL_MIN = 3          # once is chance, twice is coincidence, three times is a pattern
BUCKET_S = 3600          # same hour = "together" for jobs on 5-min to daily cadences


def read_failures() -> list:
    """Hospital's ACTUAL failure record. (producer, hour-bucket) for every non-OK finding.

    ⛔⛔ WHY THIS MATTERS. A seam lane that only reads the MAP (elements, manifest,
    computed_edges) only ever reports places where the system's DESCRIPTION of itself is
    inconsistent — never a place where the system is actually BREAKING. Those are different
    questions. This function is what makes class (d) CO-FAILURE possible, and it is the one
    class with no organism/ dependency at all in this repo (see module docstring).

    ⛔ `ts` IS AN ISO-8601 STRING, not an epoch number — `float(ts)` throws on every row if
    tried first; parsed via `datetime.fromisoformat` instead, with a float fallback for any
    producer that ever writes a raw epoch. A per-row parse failure is counted in `unparsed`,
    never silently swallowed into a false-zero. This function RAISES when it parses nothing
    out of a non-empty input, because a reader that returns empty on a broken contract is a
    false green.
    """
    from datetime import datetime
    from findings_reader import findings_report          # let an import error be LOUD
    rows = findings_report().get("rows", []) or []
    out, non_ok, unparsed = [], 0, 0
    for r in rows:
        if (r.get("status") or "OK").upper() == "OK":
            continue
        non_ok += 1
        prod, ts = r.get("producer"), r.get("ts")
        if not prod or not ts:
            unparsed += 1
            continue
        try:
            epoch = datetime.fromisoformat(str(ts)).timestamp()
        except Exception:
            try:
                epoch = float(ts)
            except Exception:
                unparsed += 1
                continue
        out.append((prod, int(epoch) // BUCKET_S))
    if non_ok and not out:
        raise RuntimeError(
            f"read_failures parsed 0 usable records from {non_ok} non-OK findings "
            f"({unparsed} unparsed) — the findings contract changed. Refusing to report a "
            f"clean seam scan built on nothing.")
    return out


# ───────────────────────────── detectors ─────────────────────────────
def detect(elements: dict, manifest_ids: list, edges: list, failures: list) -> list:
    """Return seam findings. Each carries seam · fingerprints · targets — all three, always."""
    seams = []

    # (a) LABEL-VS-COMPUTED — a human typed over a machine's verdict.
    for slug, e in sorted(elements.items()):
        fb, cb = _base(e["frontmatter_label"]), _base(e["computed_label"])
        if fb and cb and fb != cb:
            seams.append({
                "klass": "LABEL-VS-COMPUTED",
                "seam": f"{slug}: its own frontmatter and its own AUTO-COMPUTED section disagree",
                "fingerprints": [
                    f"{e['file']} frontmatter maturity_label = {e['frontmatter_label']!r}",
                    f"{e['file']} AUTO-COMPUTED maturity_label = {e['computed_label']!r}",
                    f"BASE words differ: {fb} vs {cb} (BASE is machine-owned; a mismatch means it was hand-typed)",
                ],
                "targets": [e["file"]],
                "slug": slug,
            })

    # (b) MANIFEST-ORPHAN — the causal half. Unreachable by the writer = uncorrectable forever.
    slugs = set(elements)
    mids = set(manifest_ids)
    for gid in sorted(mids - slugs):
        seams.append({
            "klass": "MANIFEST-ORPHAN-GUARD",
            "seam": f"guard {gid!r} is fire-tested but backs no element on the map",
            "fingerprints": [
                f"{MANIFEST.relative_to(REPO)} declares id: {gid}",
                f"no element file carries `element: {gid}` ({len(slugs)} elements examined)",
            ],
            "targets": [str(MANIFEST.relative_to(REPO))],
            "slug": gid,
        })
    stated = {s for s, e in elements.items() if _base(e["frontmatter_label"]) in ("LIVE", "PARTIAL")}
    for slug in sorted(stated - mids):
        e = elements[slug]
        seams.append({
            "klass": "MANIFEST-ORPHAN-ELEMENT",
            "seam": (f"{slug} claims a live posture but no guard in the fire-test manifest backs it "
                     f"— its label can never be machine-computed"),
            "fingerprints": [
                f"{e['file']} maturity_label = {e['frontmatter_label']!r} (a live claim)",
                f"{MANIFEST.relative_to(REPO)} has no id matching {slug!r} ({len(mids)} ids examined)",
                "label_checker.py write-labels keys on guard id -> element slug; no id means no computation, ever",
            ],
            "targets": [e["file"], str(MANIFEST.relative_to(REPO))],
            "slug": slug,
        })

    # (d) CO-FAILURE — the only class built from what ACTUALLY BROKE, not from what is written
    # down. Two producers that keep going non-OK in the same hour are coupled in a way no
    # document records: either one causes the other, or both depend on a third thing nobody has
    # named. ★ The strongest seam signal available, and the one class with no organism/ dependency.
    import collections as _c
    buckets = _c.defaultdict(set)
    for prod, b in failures:
        buckets[b].add(prod)
    pairs = _c.Counter()
    for b, prods in buckets.items():
        ps = sorted(prods)
        for i in range(len(ps)):
            for j in range(i + 1, len(ps)):
                pairs[(ps[i], ps[j])] += 1
    for (a, b), n in pairs.most_common():
        if n < CO_FAIL_MIN:
            continue
        seams.append({
            "klass": "CO-FAILURE",
            "seam": (f"{a} and {b} have failed in the same hour {n} times — a coupling no "
                     f"document records. One causes the other, or both depend on a third thing."),
            "fingerprints": [
                f"{n} shared hour-buckets with both producers non-OK (threshold {CO_FAIL_MIN})",
                f"source: Hospital findings union, {len(failures)} non-OK records examined",
                f"producers: {a} · {b}",
            ],
            "targets": [f"state/findings/{a}.*.jsonl", f"state/findings/{b}.*.jsonl"],
            "slug": f"cofail:{a}+{b}",
        })

    # (c) SHARED-SOURCE SPLIT — one file, two stories.
    # ⚠ TWO BARS, both preserved from the donor: (1) CODE ONLY — a config or doc everyone
    # touches is shared BY DESIGN and says nothing about a seam. (2) AT MOST 4 ELEMENTS — a
    # file cited by twenty elements is infrastructure; disagreement there is expected. A seam
    # is a SMALL number of parts that should agree and do not. With `elements={}` in this
    # repo this class finds nothing today (`els` can never reach length >= 2) — kept intact
    # for the day, if any, this repo grows its own element map.
    for edge in edges:
        src = edge.get("source_path")
        els = [s for s in (edge.get("elements") or []) if s in elements]
        if not src or len(els) < 2:
            continue
        if not src.endswith((".py", ".sh")):
            continue
        if len(els) > 4:
            continue
        claims = {}
        for s in els:
            b = _base(elements[s]["frontmatter_label"])
            if b:
                claims.setdefault(b, []).append(s)
        if len(claims) > 1:
            seams.append({
                "klass": "SHARED-SOURCE-SPLIT",
                "seam": (f"{len(els)} elements cite {src} but make different maturity claims about it: "
                         + " vs ".join(f"{k} ({', '.join(v[:3])})" for k, v in sorted(claims.items()))),
                "fingerprints": [
                    f"organism-map.json computed_edges: {src} shared by {len(els)} elements",
                ] + [f"{elements[s]['file']} claims {elements[s]['frontmatter_label']!r}" for s in els[:4]],
                "targets": [src] + [elements[s]["file"] for s in els[:3]],
                "slug": f"shared:{src}",
            })
    return seams


# ⚖ WHICH SEAM CLASSES A `gap_disposition:` RULING CAN LEGITIMATELY EXPLAIN.
#
# A `gap_disposition` rules on DOCUMENTED FAIL-OPENS (`·gap`). It says nothing about an
# INTEGRITY DEFECT — a file disagreeing with itself, or a claim no machine can ever check.
# Those were never put to a human, so they cannot have been ruled on. ⇒ the filter is
# CLASS-AWARE, and no class is gap-shaped today, so the allowlist is empty ON PURPOSE. It
# stays because the principle is right and a future gap-shaped class will need it. What
# would have been dropped is still COUNTED and reported, never hidden.
RULING_CAN_EXPLAIN = frozenset()  # deliberately empty — see the block above before adding to it


def filter_ruled(seams: list, elements: dict) -> tuple:
    """⛔ Never re-escalate a decision a human already made — but only where the ruling
    actually covers the class. Over-filtering hides real defects; see the block above."""
    kept, dropped = [], []
    for s in seams:
        e = elements.get(s.get("slug", ""))
        if e and e.get("gap_disposition") and s["klass"] in RULING_CAN_EXPLAIN:
            s["_ruled"] = e["gap_disposition"]
            dropped.append(s)
        else:
            kept.append(s)
    return kept, dropped


# ───────────────────────────── main ─────────────────────────────
def build(dry=False):
    elements = read_elements()
    mids = read_manifest_ids()
    edges = read_edges()
    failures = read_failures()
    seams = detect(elements, mids, edges, failures)
    kept, dropped = filter_ruled(seams, elements)
    return {
        "elements_examined": len(elements),
        "manifest_ids_examined": len(mids),
        "edges_examined": len(edges),
        "failure_records_examined": len(failures),
        "seams_found": len(seams),
        "filtered_already_ruled": len(dropped),
        "seams": kept,
        "dropped": dropped,
    }


COLLAPSE_AT = 3


def collapse(seams: list) -> list:
    """Fold a class with a shared root cause into ONE recommendation.

    ⚠ WHY THIS EXISTS: with no elements/ map in this repo, class (b) can produce one row PER
    guard id (see module docstring) — emitting one recommendation per row would bury any
    genuinely distinct finding in noise, the alarm-fatigue shape this whole subsystem exists
    to avoid. `fault_proposer` collapses its ORGANISM cohort for the same reason; this is that
    pattern, not a new idea. The COUNT is never lost — it leads the action text.
    """
    by = {}
    for s in seams:
        by.setdefault(s["klass"], []).append(s)
    out = []
    for klass, group in sorted(by.items()):
        if len(group) <= COLLAPSE_AT:
            out.extend(group)
            continue
        names = [g["slug"] for g in group]
        out.append({
            "klass": klass,
            "seam": (f"{len(group)} instances of {klass} share one root cause — "
                     f"e.g. {', '.join(names[:5])}"),
            "fingerprints": ([f"{len(group)} instances detected in this run"]
                             + group[0]["fingerprints"][:3]
                             + [f"full member list: {', '.join(names)}"]),
            "targets": sorted({t for g in group[:6] for t in g["targets"]})[:6],
            "slug": f"cohort:{klass}",
            "cohort_size": len(group),
        })
    return out


def emit(result: dict) -> int:
    from emit_recommendation import emit_recommendation, RecommendationContractError
    n = 0
    for s in collapse(result["seams"]):
        action = (f"SEAM [{s['klass']}] — {s['seam']}. "
                  f"OPEN: {', '.join(s['targets'][:3])}.")
        try:
            emit_recommendation(
                producer=PRODUCER,
                altitude=ALTITUDE,
                action=action,
                evidence=s["fingerprints"],
                labels={"klass": s["klass"], "seam_slug": s["slug"]},
                summary=s["seam"][:180],
            )
            n += 1
        except RecommendationContractError as ex:
            print(f"  REFUSED (contract): {s['slug']}: {ex}", file=sys.stderr)
    return n


def selftest() -> int:
    """The acceptance bar — run against LIVE data, writing nothing."""
    print("seam_reason --selftest — against live data\n")
    r = build()
    print(f"  examined: {r['elements_examined']} elements · {r['manifest_ids_examined']} manifest ids "
          f"· {r['edges_examined']} computed edges")
    print(f"  seams found: {r['seams_found']} · filtered as already-ruled: {r['filtered_already_ruled']}\n")
    ok = True

    # BAR 1 — the DETECTOR still detects, proven on a planted contradiction. Synthetic is
    # correct HERE (does not violate "prove it on a real specimen" — that rule governs
    # components that INTERPRET human intent; this asserts pure comparison logic, which
    # carries no intent).
    planted = {
        "agrees":    {"frontmatter_label": "LIVE·gap", "computed_label": "`LIVE·gap` [provisional]"},
        "disagrees": {"frontmatter_label": "LIVE·gap [provisional]", "computed_label": "PARTIAL·gap"},
    }
    hit_dis = _base(planted["disagrees"]["frontmatter_label"]) != _base(planted["disagrees"]["computed_label"])
    hit_agr = _base(planted["agrees"]["frontmatter_label"]) != _base(planted["agrees"]["computed_label"])
    if hit_dis and not hit_agr:
        print("  ✓ BAR 1 — LABEL-VS-COMPUTED fires on a planted contradiction and is silent on agreement")
        print("      └ LIVE vs PARTIAL → flagged;  `LIVE·gap` vs LIVE·gap → not flagged (markdown is presentation)")
    else:
        print(f"  ✗ BAR 1 — detector logic wrong (planted-disagree fired={hit_dis}, planted-agree fired={hit_agr})")
        ok = False

    # BAR 2 — THIS REPO HAS NO ELEMENTS MAP, SO THE DONOR'S BAR 2 (which asserted two named
    # elements stay reachable in a real map) DOES NOT APPLY HERE — there is no map to regress.
    # Replaced with the equivalent, honest claim for THIS repo: the manifest itself parses and
    # names at least one guard id, so class (b)'s first half has real input to run against.
    ids = set(read_manifest_ids())
    if ids:
        print(f"  ✓ BAR 2 (re-scoped for this repo — no elements/ map exists here) — "
              f"label_manifest.yaml parses and names {len(ids)} guard id(s) for class (b) to examine")
    else:
        print("  ✗ BAR 2 — REGRESSION: label_manifest.yaml names ZERO guard ids — class (b) has nothing to examine")
        ok = False

    # ⚠ ASSEMBLE THE TOKENS FROM FRAGMENTS. Spelling them literally makes this check match its
    # OWN source and fail every time.
    src = Path(__file__).read_text(encoding="utf-8")
    probes = ["def " + "apply", "def " + "remediate", "def " + "autofix",
              "shutil" + ".move", "os" + ".replace"]
    bad = [w for w in probes if w in src]
    if bad:
        print(f"  ✗ BAR 3 — an applier-shaped symbol exists: {bad}")
        ok = False
    else:
        print("  ✓ BAR 3 — no applier in this file (propose-only holds)")

    print("\n" + ("✓ SELFTEST PASSED — the lane finds its specimen and applies nothing."
                  if ok else "✗ SELFTEST FAILED"))
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(prog="seam_reason.py")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    r = build()
    if a.json:
        print(json.dumps(r, indent=2))
        return 0
    print(f"[seam-reason] examined {r['elements_examined']} elements · {r['edges_examined']} edges "
          f"· {r['manifest_ids_examined']} manifest ids")
    print(f"[seam-reason] {r['seams_found']} seam(s); {r['filtered_already_ruled']} filtered as already-ruled")
    for s in r["seams"]:
        print(f"  · [{s['klass']}] {s['seam']}")
        print(f"      targets: {', '.join(s['targets'][:3])}")
    if a.dry_run:
        print("[seam-reason] --dry-run: nothing written")
        return 0
    n = emit(r)
    print(f"[seam-reason] wrote {n} recommendation(s) at {ALTITUDE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

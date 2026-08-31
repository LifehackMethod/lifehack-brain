#!/usr/bin/env python3
"""
architecture_reason.py — T18.10b, the 10,000-FT ARCHITECTURE LANE. Efficiency's top altitude.

── WHAT THIS ANSWERS ────────────────────────────────────────────────────────
Ground asks "is THIS thing broken?". The 5,000-ft seam lane asks "do these parts fight?".
This one asks the question only a whole-system view can: **"is the organism the right SHAPE?"**

TWO VERBS, and deliberately only two (§18.10 decision 1, and the FRAME's own link-5 wording —
*"fixes OR ADDITIONS to the architecture… what is over-built and should go, what is missing and
should exist"*):

  ELIMINATE — a capability that exists more times than it needs to, or exists and is reachable
              by nothing. Over-build is a real cost: every duplicate is a surface that can drift
              out of agreement with its siblings, and this system has already paid for that.
  INTRODUCE — a capability the system demonstrably needs and does not have. ⚠ The high bar:
              "missing" is easy to assert and nearly impossible to falsify, so this lane only
              proposes an addition when the EVIDENCE IS A BUILT-BUT-UNREACHABLE PART — the
              system already decided it needed the thing, built it, and never wired it. That is
              a missing capability with a receipt, not an opinion.

── WHY "BUILT BUT NEVER CALLED" IS THE ONLY INTRODUCE EVIDENCE ACCEPTED ──
The failure mode of a 10,000-ft lane is generating plausible architecture opinions nobody can
check — the §18.17 lesson one rung up ("the design is wrong" with no named seam is useless).
So the trigger is mechanical: a tool with a real docstring, no caller anywhere, and a
capability its own text describes. `recommendation_disposition.py` is the specimen — 486 lines
that record whether a human accepted a recommendation, wired to the read side, invoked by
nothing. ⇒ **the system cannot tell "nobody needed to act" from "nobody looked."** That is a
genuine architectural hole and the evidence for it is a file path, not a hunch.

── WHAT IT NEVER DOES ───────────────────────────────────────────────────────
  · Never APPLIES. ⚖ RULED 2026-08-04 by the person, `authority: user` (§18.5). No repair path
    exists here; --selftest greps for one (with the probe tokens assembled from fragments, because
    spelling them literally makes the check match its own source — learned on seam_reason.py's
    first run).
  · Never invents a store or an altitude — writes through `emit_recommendation.py` at ORGANISM,
    a value already in `VALID_ALTITUDE`.
  · Never writes a second ledger parser — reuses `backlog_groom.parse_ledger()` (430 entries
    today). §18.10 SAFE-HALT: "Reuse or stop."
  · Never proposes eliminating something a human ruled deliberate. `state:parked` and
    `type:decision` ledger rows are HIS, and are read as evidence, never as targets.

⚠⚠ KNOWN LIMITATION, MEASURED AT BUILD TIME 2026-08-05, RE-MEASURED T20.4 2026-08-05 — READ
BEFORE TRUSTING A COUNT. `CLI-NEVER-INVOKED` still **OVER-REPORTS**; T20.4 closed ONE of its two
known directions, not both. The roots blob now promotes BOTH `system/tools/**/*.sh` runners AND
`.py` tools confirmed live — one hop each, `_roots()` §T20.4 comment — so a `.py` file that
invokes another `.py` file (via `subprocess` with an f-string path, e.g. `system-health.py` ->
`archivist-lean.py`/`archivist-placements.py`, OR a genuine top-level `import`, e.g.
`backlog-health.py` -> `backlog_groom.py`, which runs every 6h) no longer flags the invoked file.
Raw count fell 57 → 28 when the `.sh` hop alone was added; T20.4's `.py` hop took it 28 → 19 (of
264 tool files examined). The 19 that remain are UNVERIFIED, not confirmed — a `.py` invoked by
something outside `system/tools/` (a skill running inline Python, a cron entry, a REPL), by
dynamic dispatch (`importlib`/`getattr` by a name built at runtime, not a literal path), or by a
second-hop chain (a `.py` this hop already promoted, itself importing a THIRD `.py` — deliberately
NOT walked, see the hop's own comment) will still misreport. ⇒ **treat a CLI-NEVER-INVOKED cohort
as a LIST TO CHECK, never as a list of confirmed holes.** The two acceptance specimens are
unaffected and both still pass — `recommendation_disposition.py` stays flagged on purpose: its
only inbound reference is an indented, alarm-guarded, best-effort LOCAL import of one read-only
function three stack frames deep in `health_line.py`, never a top-level import, so it correctly
fails the same bar `backlog_groom.py` now passes.
★ Recorded here rather than quietly tuned away, because a count nobody knows is inflated is worse
than a count everybody knows is inflated — that is this project's founding lesson.

⛔ T20.6, 2026-08-05 — `NOTHING-REACHES-IT` WENT 3-FOR-3 FALSE on the first board. `vault-related.py`
+ `vault-theme-map.py` (parked, the person floor-vetoed the swap that would break them —
`[OBSIDIAN-BRAIN-SWAP]` in `state/debt-ledger.md`) and `translator-mine-pairs.py` (retired-in-place,
per its own project's brief) are all refutable from a human decision this file already had open in the same
process — `build()` reads `state/debt-ledger.md` for `LEDGER-NAMED-OVERBUILD` and `detect_introduce`
never consulted it. `human_ruling_for()` now cross-checks the ledger + every project brief +
`state/open-loops.md` + `system/journal.md` before a `NOTHING-REACHES-IT` fires; see its docstring for
exactly what counts as a ruling. Applied ONLY to that one class — the same matcher, stress-tested
against `SKILL-FAMILY`'s member names, still false-matched bare skill-directory names loosely enough
that trusting it there risked a FALSE SUPPRESSION, so `ELIMINATE`/`CLI-NEVER-INVOKED` are untouched.

Usage:
  architecture_reason.py              # detect + WRITE at ORGANISM (the supervised path)
  architecture_reason.py --dry-run    # detect + print, write nothing
  architecture_reason.py --json       # machine-readable payload, writes nothing
  architecture_reason.py --selftest   # prove both acceptance bars against LIVE data

WHAT CHANGED IN THIS PORT (T9.7b, 2026-08-15, generalisation, not a redesign): the donor's
`DRIVE` constant was a hardcoded personal Google-Drive path. Repointed through
`shared/brain_root.py`'s `resolve_brain_root()` — the ONE root resolver `backlog_groom.py`
(imported below) already uses in this repo — exactly the same pattern `recommend.py` used for
its own T9.7b-class repoint. With no brain root configured, `DRIVE` is `None` and
`_human_decision_units()` raises a named, actionable error instead of crashing on a bad
attribute access; this file already raises rather than degrading on a missing human-decision
source (§T20.6, "refusing to report clean"), so the behavior on a real missing-root install is
unchanged in KIND, only in the message.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

REPO = Path(__file__).resolve().parents[2]
TOOLS = REPO / "system" / "tools"
HOOKS = REPO / "system" / "hooks"
PARTS = REPO / "system" / "parts"
SHARED_TOOLS = REPO / "shared" / "tools"
# ⛔ T27.1b, 2026-08-08 — THE OTHER HALF OF THE ASYMMETRY, found by an adversarial arm.
# `shared/tools/` joined TERRITORY (the things that can be JUDGED) without `shared/skills/`
# joining the roots scan (the things that can VOUCH). Net effect: three genuinely-wired files
# were reported dead — `hollywood_database.py`, `tmdb_credits.py`, `whorepresents_reps.py`, all
# named as mandatory context in `shared/skills/hollywood-db/`, which nothing ever read.
# ⭐ THE SHAPE OF THE BUG IS THE SAME ONE THE WIDENING ITSELF FIXED, one directory over: widen
# what you judge without widening what vouches, and you manufacture false accusations.
#
# ⛔⛔ T18.10-PORT-FIX, 2026-08-22 — `REPO / "skills"` AND `REPO / "shared" / "skills"` WERE BOTH
# DONOR PATHS AND NEITHER EXISTS IN THIS REPO. This repo's skills live at `.claude/skills/`
# (verified present this session) plus, on an operator's own machine, personal skills at
# `~/.claude/skills/` — a real second location this repo did not have before the migration, not
# a stand-in for the donor's `shared/skills/`. `SKILLS.iterdir()` in `detect_eliminate()` crashed
# every run with `FileNotFoundError` (dead since the migration; caught by the runner-port lane and
# confirmed first-hand 2026-08-22). Resolved through `_skill_roots()` below rather than a second
# hardcoded literal — each candidate is checked for existence on its own and a missing one is
# skipped WITH A REASON, never silently, and never a crash. See `_skill_dirs()` for the
# zero-examined guard: an install where every candidate is missing must not look like a clean walk.
def _skill_roots() -> list:
    """Every real place a skill can live on THIS install, labeled by name.

    Two locations, deliberately not one: `.claude/skills/` ships WITH this repo (present on every
    checkout — this is where `SKILLS` used to point before the migration, at the wrong literal
    `skills/`), and `~/.claude/skills/` is the operator's own personal skill folder (present only
    for an operator who has one; absent on a bare checkout, and that absence is normal, not a
    fault). Both are real "things that can VOUCH" per the T27.1b argument above — a personal skill
    can call a repo tool exactly as a repo skill can.
    """
    return [
        ("repo (.claude/skills)", REPO / ".claude" / "skills"),
        ("personal (~/.claude/skills)", Path.home() / ".claude" / "skills"),
    ]


def _skill_dirs():
    """Every skill folder across every real skill location, plus a per-location status report.

    Returns `(dirs, status)` — `dirs` is the flat, name-sorted list of skill folders found across
    every EXISTING location; `status` is `{label: {"path", "status", "count"}}` for every candidate,
    existing or not, so a missing location is visible in the evidence rather than silently absent.

    ⚠⚠ THE ZERO-EXAMINED GUARD LIVES ONE LEVEL UP, IN `build()` — NOT HERE. This function's job is
    only to report what it found, honestly, including "nothing" when every candidate is missing;
    `build()` is what refuses to let a zero-directory walk masquerade as a clean SKILL-FAMILY pass
    (the measured failure this fix exists to close: "a script printed PASSED daily... and wrote no
    file"). A single missing candidate here is NOT an error — a bare checkout with no personal
    skill folder is the common case, not a fault.
    """
    dirs, status = [], {}
    for label, root in _skill_roots():
        if not root.exists():
            status[label] = {"path": str(root), "status": "missing (skipped)", "count": 0}
            continue
        members = sorted((p for p in root.iterdir() if p.is_dir()), key=lambda p: p.name)
        status[label] = {"path": str(root), "status": "ok", "count": len(members)}
        dirs.extend(members)
    return sorted(dirs, key=lambda p: p.name), status

# ⭐⭐ T27.1, 2026-08-08 — THE TERRITORY. Everything this lane considers a capability that could
# be over-built or unreachable. Until today this was `TOOLS` alone, so the walk saw 279 files and
# was BLIND to 20 validators under `system/parts/`, 35 under `shared/tools/` and 69 under
# `system/hooks/` — 124 files, 31% of the real surface, that could never be reported no matter
# what was wrong with them.
#
# ⛔ THE PLAN'S ORIGINAL WORDING WAS "same walk, one more output" AND THAT WAS THE BUG: an index
# built on the old walk ships missing the validators ON DAY ONE, i.e. the fourth instance of this
# project's founding disease rather than its fix.
#
# ⭐ WHY THIS IS A CENSUS AND NOT A CITATION GRAPH (`build-sop.md:133`, earned): the denominator
# is GLOBBED FROM THE TERRITORY, never read off a document's own list of what it cites.
# `system/organism/generated/organism-map.json` is the citation graph and is exactly backwards for
# "find what nothing invokes" — it can only see what is already cited. Stated in the tool's own
# output so nobody wires the wrong one again.
TERRITORY = (TOOLS, PARTS, SHARED_TOOLS, HOOKS)

# T20.6 — content-root files a human ruling can live on. NOT the REPO above: these are the
# person's notes, not code — resolved through the ONE brain-root resolver `backlog_groom.py`
# (imported below) already uses, never a hardcoded personal path. `None` when no root is
# configured; `_human_decision_units()` below is what turns that into a named, actionable error
# instead of a bare AttributeError.
_SHARED = str(REPO / "shared")
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)
try:
    from brain_root import resolve_brain_root          # shared/brain_root.py
    _ROOT_SOURCE, _ROOT = resolve_brain_root()
except Exception:
    _ROOT_SOURCE, _ROOT = None, None

DRIVE = Path(_ROOT) if _ROOT else None
DEBT_LEDGER = (DRIVE / "state" / "debt-ledger.md") if DRIVE else None
ROOT_OPEN_LOOPS = (DRIVE / "state" / "open-loops.md") if DRIVE else None
JOURNAL = (DRIVE / "system" / "journal.md") if DRIVE else None
BRIEF_GLOB = "state/projects/**/brief.md"

PRODUCER = "architecture-reason"
ALTITUDE = "ORGANISM"

FAMILY_MIN = 4          # 4+ same-prefix siblings is a family worth asking about, not a coincidence
DOCSTRING_MIN = 200     # a real capability describes itself; a stub does not

# ⭐⭐ T27.1, 2026-08-08 — WHERE THE CENSUS LANDS.
# Sits beside `organism-map.json` because both are DERIVED, and lives under the gitignored
# `system/organism/generated/` (`.gitignore:26`) for the same reason that file does: it is a
# pure function of the tree, so committing it would only manufacture merge conflicts between
# two machines that can each regenerate it in under a second. The OTHER machine regenerates
# rather than pulls — the header below carries the command.
CENSUS_OUT = REPO / "system" / "organism" / "generated" / "capability-census.md"


_PULSE_ROW = re.compile(
    r"^([\w-]+)(\s*\|\s*)([\w][\w.-]*)(\s*\|\s*)(\d+)(\s*\|\s*)(.*)$")


def _pulse_config_text() -> str:
    """`system/pulse-config.md`'s text, with the COMMAND column of any non-`yes` job row
    redacted before it joins the roots blob.

    ⛔⛔ T-session 2026-08-24 — SECOND HALF OF THE SELF-POISONING FIX (see the comment in
    `_roots()` for the first half). `## Job format` in that file is explicit: a row's `enabled`
    field can be `no`/`parked`/`waiting-on-<thing>` and the row STILL carries a real command in
    its 4th column — by design, "so a future health sweeper can render your own reason back to
    you". That is correct for a human reading the manifest. It is wrong evidence for `_roots()`,
    which is asking "does anything START execution" — a documented-but-`waiting-on-port` row
    answers NO, Pulse will never run it. Left unredacted, that row's command text (e.g.
    `bash ".../brokenlist-run.sh"`) satisfies `_invoked_by()` exactly like a live `yes` row would.
    Measured 2026-08-24: this is precisely why `recommendation_disposition.py` (imported at
    module top level by `brokenlist.py`, per T20.4's one-hop `.py` promotion) stopped reaching
    BAR 2 — `brokenlist`'s `waiting-on-port` row (line ~405) still names its real runner path,
    the `.sh` hop promotes `brokenlist-run.sh`, the `.py` hop then promotes `brokenlist.py`
    itself (its command already in the blob), and `brokenlist.py`'s own top-level
    `import recommendation_disposition` rides in with it — none of that chain requires the job
    to ever actually run. Every OTHER `waiting-on-port` row in this file has the identical shape
    and would misreport the same way once its runner script exists on disk (`hook-doc-lint.sh`,
    `security-posture-scan.sh`, `architecture-reachability-run.sh` already do).

    ⛔ THE ROW ALONE WAS NOT ENOUGH — measured on the SAME job. Redacting only the row's command
    column left the leak open through the `#`-comment lines this file's own convention writes
    directly above each row (every entry here is `# prose describing the job` then the row —
    see `## Job format`'s own layout, unchanged since this file was created). `brokenlist`'s
    comment block reads, in full prose, "its wrapper `system/tools/brokenlist-run.sh`" — a
    `/`-prefixed real path, same as the row would have carried. So: the contiguous `#`-comment
    block immediately ABOVE a non-`yes` row is redacted along with it. A comment block above a
    `yes` row, or one not immediately followed by any row at all (file-level prose, the header,
    `## Job format`'s own explanation), is untouched.
    """
    p = REPO / "system" / "pulse-config.md"
    if not p.exists():
        return ""
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    out = []
    pending = []                                       # buffered contiguous "# ..." lines
    for line in lines:
        if line.lstrip().startswith("#"):
            pending.append(line)
            continue
        m = _PULSE_ROW.match(line)
        if m and m.group(3) != "yes":
            for _ in pending:
                out.append("# [NOT LIVE — redacted from roots-detection, see comment above]")
            line = (f"{m.group(1)}{m.group(2)}{m.group(3)}{m.group(4)}{m.group(5)}{m.group(6)}"
                    f"[NOT LIVE — {m.group(3)} row, command redacted from roots-detection]")
        else:
            out.extend(pending)
        pending = []
        out.append(line)
    out.extend(pending)                                 # trailing comments, never redacted
    return "\n".join(out)


def _roots() -> str:
    """Everything that can START execution, as one searchable blob."""
    blobs = []
    pc = _pulse_config_text()
    if pc:
        blobs.append(pc)
    settings = REPO / "system" / "reference" / "settings.json"
    if settings.exists():
        blobs.append(settings.read_text(encoding="utf-8", errors="replace"))
    skill_roots = [root for _, root in _skill_roots() if root.exists()]
    # ⛔⛔ T-session 2026-08-24 — SELF-POISONING FIX. On THIS install, ClaudeOps (REPO) lives
    # *inside* `~/.claude/skills/` as a real directory, not a symlink — so `_skill_roots()`'s
    # "personal (~/.claude/skills)" entry does not just find sibling personal skill packages, it
    # rglobs the ENTIRE ClaudeOps tree A SECOND TIME: `system/organism/elements/*.md`,
    # `migration-notes/*.md`, `system/organism/generated/capability-census.md` (this file's OWN
    # `--census` output, `.gitignore`-derived, regenerated every run — see `CENSUS_OUT` below),
    # everything. None of that is a place execution STARTS — it is documentation and prose ABOUT
    # the tree, or (for the census specifically) a REPORT that prints the literal path of every
    # tool it examines (an "UNCALLED  system/tools/…" line naming the BAR 2 specimen among many
    # others) and `efficiency.md`'s own `generated_from:` frontmatter, which cites that same
    # specimen's tool path as a documentation source, not a caller. Both satisfy `_invoked_by()`'s
    # `/{name}\\b` pattern and falsely mark the file "invoked" — the census case is worse: it is
    # the detector's own PAST OUTPUT feeding back in, a self-referential loop, not evidence.
    # Measured: this exact mechanism is why the BAR 2 specimen silently stopped reaching BAR 2
    # (`--selftest`) once these files existed/were regenerated with today's new tool names in
    # them. ⚠ Deliberately worded here WITHOUT a `/`-prefixed literal path to that specimen —
    # this file is itself swept into the roots blob by the `.py` hop below whenever
    # `pulse-config.md` merely NAMES it in prose (measured: it does, describing this row as
    # `waiting-on-port`), so this file's OWN comment text joins the blob `_invoked_by()` searches.
    # A `/`-prefixed mention here would re-poison the exact bar this fix repairs.
    # FIX: REPO's own internals were never meant to vouch as a "personal skill" root — the ONE
    # part of REPO that legitimately belongs in a skill-roots walk is `REPO/.claude/skills/`,
    # and that is already covered in full by the separate "repo (.claude/skills)" entry
    # `_skill_roots()` returns. So: any file the "personal" walk reaches that resolves inside
    # REPO but OUTSIDE `REPO/.claude/skills/` is redundant-or-wrong and is skipped here. `HOOKS`
    # (`REPO/system/hooks`) is walked separately below and stays exempt — it is deliberately,
    # explicitly a root already, not something reached only by this bug.
    REPO_R = REPO.resolve()
    REPO_SKILLS = (REPO / ".claude" / "skills").resolve()
    for d in (*skill_roots, HOOKS):
        for p in d.rglob("*"):
            if not p.is_file() or p.suffix not in (".md", ".sh"):
                continue
            if d != HOOKS:
                try:
                    pr = p.resolve()
                    if pr.is_relative_to(REPO_R) and not pr.is_relative_to(REPO_SKILLS):
                        continue
                except (OSError, ValueError):
                    pass
            try:
                blobs.append(p.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                pass
    # ⭐ ONE TRANSITIVE STEP, and it is load-bearing — added after the first run flagged 54
    # CLI-never-invoked, most of them FALSE. Pulse does not call `archivist-lean.py` directly; it
    # calls `archivist-run.lib.sh`, which calls the tool. A runner is a TOOL by location and a
    # ROOT by function, so a roots blob built only from pulse-config + hooks + skills declares
    # every runner-invoked tool dead. ⇒ any `system/tools/**/*.sh` that a real root NAMES is
    # promoted to a root itself, and its text joins the blob.
    # ⚠ Deliberately ONE step, not a full closure: two hops is where a dead subgraph starts
    # vouching for itself (a dead tool "calling" another dead tool would launder both live).
    #
    # ⭐⭐ T27.1, 2026-08-08 — BOTH HOPS NOW WALK THE FULL `TERRITORY`, NOT JUST `TOOLS`.
    # Widening `_tool_files()` alone would have been an ASYMMETRIC fix and a fresh source of false
    # positives: the territory side would gain `system/parts/` and `shared/tools/`, while the roots
    # side still promoted only `system/tools/`, so a `shared/tools/` file invoked ONLY by another
    # `shared/tools/` file had no path into the blob and would have been reported dead on day one.
    # The hop's own founding argument — "a runner is a TOOL by location and a ROOT by function" —
    # never had anything to do with which directory the runner sat in.
    # ⚠ STILL EXACTLY ONE HOP. Widening the CANDIDATE SET does not deepen the closure; the frozen
    # `seed`/`after_sh` snapshots below are what hold it to one step, and they are unchanged. Two
    # hops is still where a dead subgraph starts vouching for itself.
    seed = "\n".join(blobs)
    already = set()
    for p in sorted(q for root in TERRITORY if root.exists() for q in root.rglob("*.sh")):
        if ".bak" in p.name or ".pre-" in p.name:
            continue
        if p.resolve() in already:
            continue
        if p.name in seed:
            already.add(p.resolve())
            try:
                blobs.append(p.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                pass

    # ⭐⭐ T20.4 — A SECOND ONE-STEP HOP, .py THIS TIME. Same shape as the .sh hop above, same
    # reason: a `.py` tool confirmed live (its CLI form — `python3 …/name.py` or a subprocess
    # f-string ending `/name.py` — already appears in the blob so far) is promoted to a ROOT
    # itself, and its own source joins the blob. Specimen: `backlog_groom.py` runs every 6h —
    # `backlog-health.py` (promoted via the .sh hop, since `backlog-health-run.sh` execs it)
    # does `import backlog_groom` at module top level and calls `.build_report()` in `main()`.
    # `system-health.py` (promoted the same way) is the OTHER shape — `subprocess.run(["python3",
    # f"…/archivist-lean.py"])` — an f-string whose literal tail already satisfies the existing
    # CLI-pattern match once this file's own text is in the blob.
    # ⚠ Deliberately ONE step, not a full closure, for the identical reason as the .sh hop: two
    # hops is where a dead subgraph starts vouching for itself (tool A imports dead tool B, B
    # imports dead tool A, neither reachable from a real root, and they certify each other live).
    # This loop checks every candidate against the SAME frozen `after_sh` snapshot — a promoted
    # `.py` file's own imports are never used to promote a THIRD file in this same pass.
    after_sh = "\n".join(blobs)
    for p in sorted(q for root in TERRITORY if root.exists() for q in root.rglob("*.py")):
        if ".bak" in p.name or ".pre-" in p.name:
            continue
        if p.resolve() in already:
            continue
        if re.search(rf"(python3?\s+\S*{re.escape(p.name)}|/{re.escape(p.name)}\b)", after_sh):
            already.add(p.resolve())
            try:
                blobs.append(p.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                pass
    return "\n".join(blobs)


def _tool_files() -> list:
    """Every capability file in the TERRITORY — the CENSUS denominator.

    T27.1: walks all four roots, not just `system/tools/`. Deduplicated by RESOLVED path so a
    symlink between two roots can never be counted twice (measured 2026-08-08: zero symlinks
    today, so this is a guard against a future one, not a fix for a present bug).
    """
    out, seen = [], set()
    for root in TERRITORY:
        if not root.exists():
            continue
        for p in sorted(root.rglob("*")):
            if p.suffix not in (".py", ".sh"):
                continue
            if ".bak" in p.name or ".pre-" in p.name:
                continue
            if not p.is_file():
                continue
            key = p.resolve()
            if key in seen:
                continue
            seen.add(key)
            out.append(p)
    return sorted(out)


def _invoked_by(name: str, roots: str):
    """Does any ROOT run this file as a command, or import it at module top level?

    ⭐ ONE definition, shared by `detect_introduce` and `--census`. A census that answered this
    question with its own copy of the regex would be a SECOND truth about the same fact, and the
    two would drift — which is the disease this whole lane exists to detect, reproduced inside the
    detector. The semantics are unchanged from T20.4; only the call sites are now two.
    """
    stem = name[:-3] if name.endswith(".py") else name
    return re.search(
        rf"(python3?\s+\S*{re.escape(name)}|/{re.escape(name)}\b"
        rf"|^import\s+{re.escape(stem)}\b|^from\s+{re.escape(stem)}\s+import\b)",
        roots, re.MULTILINE)


def _basename_collisions(files: list) -> dict:
    """Files sharing a BASENAME across different paths.

    ⛔ LOAD-BEARING, and found by measurement the moment the territory widened (2026-08-08):
    `ingest_coverage.py` exists in BOTH `system/tools/` and `shared/tools/` as two DIFFERENT files
    (4,430 vs 8,053 bytes). Every reachability test in this file keys on the BASENAME, so one
    sibling's invocation silently vouches for the other — a duplicate capability laundering itself
    live. Reported rather than resolved: which copy is canonical is a human's call, and a collision
    is itself the loudest possible "does this already exist?" signal this lane can emit.
    """
    by_name = collections.defaultdict(list)
    for p in files:
        by_name[p.name].append(str(p.relative_to(REPO)))
    return {n: sorted(v) for n, v in sorted(by_name.items()) if len(v) > 1}


def _self_description(p: Path, txt: str) -> str:
    """What the file says it is, in one line — its own words, never an agent's summary.

    `.py` → the first line of the module docstring. `.sh` → the first real comment line below the
    shebang (a shell script has no docstring, and 68 of the 69 files under `system/hooks/` are
    `.sh`, so reading only docstrings would render the entire hook plane as blank rows).
    """
    if p.suffix == ".py":
        m = re.search(r'"""(.*?)"""', txt, re.S)
        if not m:
            return ""
        doc = m.group(1).strip()
        return doc.splitlines()[0].strip()[:150] if doc else ""
    for line in txt.splitlines()[:15]:
        s = line.strip()
        if s.startswith("#!") or not s:
            continue
        if s.startswith("#"):
            return s.lstrip("#").strip()[:150]
        break
    return ""


def _skill_target(p: Path) -> str:
    """Format a skill folder as a target string, WITHOUT leaking the operator's home directory.

    A repo skill renders as its repo-relative path (`.claude/skills/name/`). A personal skill sits
    under `Path.home()`, which resolves to the operator's actual account path — never emitted
    literally here (that would be an operator-identifier leak in a publicly-shippable repo); it is
    rendered with the portable `~/` notation instead, exactly as a human would type it.
    """
    try:
        rel = p.relative_to(REPO)
        return f"{rel}/"
    except ValueError:
        return f"~/.claude/skills/{p.name}/"


def detect_eliminate(ledger: list, skill_dirs: list, skill_status: dict) -> list:
    """Over-build: same-prefix families, and ledger rows that name a consolidation.

    `skill_dirs`/`skill_status` come from `_skill_dirs()` (T18.10-PORT-FIX, 2026-08-22) — every
    skill folder found across every REAL skill location on this install, plus a per-location
    status so a location this install genuinely lacks (e.g. no personal `~/.claude/skills/`) is
    visible as "skipped", never silently absent from the evidence.
    """
    props = []

    # (1) SAME-PREFIX FAMILIES. Four skills all starting `archivist-` is not a coincidence; it is
    # a capability that got answered four times. This is the shape [SYSTEM-RENEWAL-AUDIT] names.
    fams = collections.Counter()
    members = collections.defaultdict(list)
    archived_skipped = 0
    for p in skill_dirs:
        # T20.4: `_archived-*` siblings are already RETIRED — that is a human decision recorded
        # by the prefix itself, not over-build the system independently discovered. Flagging them
        # as "one capability answered N times" is backwards: they are one capability answered
        # ONCE, with N discarded drafts kept for the record. Exclude the whole prefix before it
        # ever reaches the family counter.
        if p.name.startswith("_archived-"):
            archived_skipped += 1
            continue
        pre = p.name.split("-")[0]
        if len(p.name.split("-")) < 2:
            continue
        fams[pre] += 1
        members[pre].append(p)
    locations_line = "; ".join(
        f"{label}: {info['status']} ({info['count']} folders)"
        for label, info in sorted(skill_status.items()))
    for pre, n in sorted(fams.items()):
        if n < FAMILY_MIN:
            continue
        member_paths = sorted(members[pre], key=lambda p: p.name)
        member_names = [p.name for p in member_paths]
        props.append({
            "verb": "ELIMINATE",
            "klass": "SKILL-FAMILY",
            "proposal": (f"{n} skills share the `{pre}-` prefix — one capability answered {n} times. "
                         f"Consider consolidating: {', '.join(member_names)}"),
            "evidence": [
                f"skill locations scanned: {len(skill_dirs)} skill folders examined — {locations_line} "
                f"({archived_skipped} `_archived-` excluded from family detection — already retired)",
                f"`{pre}-` family members ({n}): {', '.join(member_names)}",
                "a same-prefix family is a capability that got answered more than once; each sibling "
                "is a surface that can drift out of agreement with the others",
            ],
            "targets": [_skill_target(p) for p in member_paths[:4]],
            "slug": f"family:{pre}",
        })

    # (2) The human already wrote it down. A ledger row naming a consolidation IS evidence.
    for r in ledger:
        title = (r.get("title") or "")
        if re.search(r"consolidat|overlapping|duplicat|merge the", title, re.I):
            props.append({
                "verb": "ELIMINATE",
                "klass": "LEDGER-NAMED-OVERBUILD",
                "proposal": f"the ledger already names an over-build: {title[:150]}",
                "evidence": [
                    f"state/debt-ledger.md: {r.get('slug') or title[:60]}",
                    f"type={r.get('type')} state={r.get('state')}",
                    f"{len(ledger)} ledger entries examined",
                ],
                "targets": ["state/debt-ledger.md"],
                "slug": f"ledger:{r.get('slug') or title[:40]}",
            })
    return props


# Self-declared labs, harnesses and one-off experiments. Their authors said, in their own
# headers, that a human runs them by hand — "unreachable" is their CORRECT state, not a hole.
# ⚠ Added after the first run returned 50 INTRODUCE proposals, ~40 of them lab files. A lane
# that proposes 50 architecture changes has proposed none: nobody reads past the third.
LAB_MARKERS = ("conformance-lab", "fanout-lab", "venue-probe", "cowork-ingest/test_",
               "test_", "_experiment", "bakeoff", "selftest", "stress", "probe", "_manual")


def _top_bullets(text: str) -> list:
    """Split on a column-0 `- ` marker; each element is ONE bullet's full text (unbounded, unlike
    `backlog_groom._entry()`'s `title[:160]` — the vault-related.py specimen sits ~500 chars into
    its bullet, past that truncation, which is WHY `detect_introduce` missed it even though
    `build()` already parses the ledger for `detect_eliminate`)."""
    parts = re.split(r"(?m)^-\s", text)
    return ["- " + p for p in parts[1:]]


# Brief sections that are AGENT-AUTHORED and therefore carry no human authority. Cutting them is
# what stops this matcher from citing its own operator back to itself.
AGENT_AUTHORED_SECTIONS = ("## SCRATCHPAD",)


def _strip_agent_authored(text: str) -> str:
    """Drop the agent-authored regions of a project brief before looking for a HUMAN ruling.

    ⛔ THE BUG THIS EXISTS TO CLOSE — CAUGHT AT REVIEW ON THE DAY IT SHIPPED (T20.6, 2026-08-05).
    The matcher read EVERY top-level bullet in every brief, `## SCRATCHPAD` included. The scratchpad
    is the DUMB-CAPTURE surface a session writes to freely, mid-run, with no human review — and the
    build lead had appended a note to it eleven minutes earlier that quoted all three specimen
    filenames in backticks beside the words "floor-vetoed" and "RETIRED-in-place". The matcher then
    read that note back as the human ruling authorising suppression.

    ⇒ **A SESSION COULD SUPPRESS ANY RECOMMENDATION BY WRITING ITSELF A NOTE.** That is the exact
    disease this subsystem was built against — `guard_findings_write.sh`'s own WHY: *a finding must
    be CAUSED, never GENERATED, and a hand-authored line is an opinion wearing a machine's
    authority.* Here it had reappeared one rung up, in the machinery that decides what NOT to say.

    Verified after the cut: `vault-related.py` / `vault-theme-map.py` still suppress on the genuine
    `state/debt-ledger.md` `[OBSIDIAN-BRAIN-SWAP]` entry (`type:decision state:parked`, council-ruled,
    the person floor-vetoed), so the two conclusions were independently supported and only the
    CITATION was contaminated.

    ⚠ RESIDUAL, NOT CLOSED — `## STORY LOG` is also agent-authored and is deliberately full of
    rejected ideas ("everything we tried and rejected"), so citing it as a ruling is unsound for the
    same reason. It is NOT cut here because real rulings are also recorded there and cutting it
    blind would trade a false-suppression risk for a false-proposal one. Flagged for the person's
    T20.5 round rather than decided unilaterally.
    """
    out, skipping = [], False
    for line in text.splitlines(keepends=True):
        if line.startswith("## "):
            skipping = any(line.startswith(s) for s in AGENT_AUTHORED_SECTIONS)
        if not skipping:
            out.append(line)
    return "".join(out)


def _paragraphs(text: str) -> list:
    """Blank-line-delimited blocks — the right grain for `journal.md`, which is dated prose, not a
    bullet catalog like the ledger/briefs."""
    return [p for p in re.split(r"\n\s*\n", text) if p.strip()]


# Prose ruling language STRONG enough to trust unattended. Deliberately narrower than the first
# draft of this matcher, which also matched bare "DECISION"/"HOLD"/"KEEP"/"DO NOT" — those words
# alone false-matched a `state:parked` ledger row that merely mentions several skills as FUTURE
# audit subjects (`[SYSTEM-RENEWAL-AUDIT]`, itself proposing to consider consolidating them, i.e.
# arguing the OPPOSITE of "leave this alone"). Kept only the words that in this corpus, checked by
# hand against every skill-family member name, name a CLOSED outcome.
RULING_WORDS = re.compile(
    r"\bRULED\b|\bRULING\b|floor[- ]vetoed|\bPARKED\b|\bRETIRED\b|\bVETOED\b|"
    r"\bDEPRECATED\b|\bDELETED\b|kept only|RETIRED-in-place", re.I)
# A ruling word near an UNDECIDED marker is not a ruling — "OPEN QUESTION ... the person leaning KEEP"
# (found live, `emily-2-interrogate`, 2026-08-05) is an open question, not a decision, even though
# "KEEP"-shaped language sits inches away. Caught by hand-checking every false candidate below.
UNDECIDED = re.compile(r"OPEN QUESTION|\bleaning\b|UNSETTLED|\bTBD\b|not decided|\bconsider\b", re.I)
PROSE_WINDOW = 150   # chars either side of the filename mention the ruling word must fall within


def _human_decision_units() -> dict:
    """Everything a human ruling about a specific FILE could live in, pre-split into the smallest
    unit worth matching (one ledger/brief/open-loops bullet, or one journal paragraph) so a match
    is scoped to ONE decision, never a whole section. T20.6, PART B + PART A inputs 1/2/4.

    ⛔ Every reader here RAISES rather than degrading to an empty list on a broken read, per the
    Hospital lesson (`seam_reason.read_failures`'s docstring): a human-decision source that silently
    returns nothing makes every `NOTHING-REACHES-IT` proposal look unruled even when one exists —
    a FALSE SUPPRESSION-NEVER-HAPPENS, which is worse than the noisy false-positive this whole
    function exists to kill. All four files are known to exist on this machine as of 2026-08-05
    (state/debt-ledger.md, state/open-loops.md, system/journal.md, and 38 project briefs under
    state/projects/**/brief.md) — a MISSING file here is a Drive-sync problem, not a "nothing to
    report" result, and must stop the run rather than silently emit an unruled row.
    """
    units = {}

    if DRIVE is None:
        raise RuntimeError(
            "no brain root configured (shared/brain_root.py resolve_brain_root() returned "
            "NOT-SET) — cannot rule out a human ledger/brief/open-loops/journal decision "
            "before emitting NOTHING-REACHES-IT; refusing to report clean. Fix: "
            "python3 shared/brain_root.py --set <folder>."
        )

    if not DEBT_LEDGER.exists():
        raise RuntimeError(f"{DEBT_LEDGER} not found — cannot rule out a human ledger decision "
                            f"before emitting NOTHING-REACHES-IT; refusing to report clean")
    ltxt = DEBT_LEDGER.read_text(encoding="utf-8", errors="replace")
    lb = _top_bullets(ltxt)
    if len(ltxt) > 2000 and not lb:
        raise RuntimeError(f"{DEBT_LEDGER}: {len(ltxt)} chars but 0 top-level bullets parsed — "
                            f"the ledger's bullet format changed under this matcher")
    units["state/debt-ledger.md"] = lb

    briefs = sorted(DRIVE.glob(BRIEF_GLOB))
    if not briefs:
        raise RuntimeError(f"no {BRIEF_GLOB} found on Drive — project-brief ruling check cannot run")
    brief_b = []
    for bp in briefs:
        bt = _strip_agent_authored(bp.read_text(encoding="utf-8", errors="replace"))
        brief_b.extend(_top_bullets(bt))
    units["state/projects/**/brief.md"] = brief_b

    if not ROOT_OPEN_LOOPS.exists():
        raise RuntimeError(f"{ROOT_OPEN_LOOPS} not found")
    units["state/open-loops.md"] = _top_bullets(
        ROOT_OPEN_LOOPS.read_text(encoding="utf-8", errors="replace"))

    if not JOURNAL.exists():
        raise RuntimeError(f"{JOURNAL} not found")
    jtxt = JOURNAL.read_text(encoding="utf-8", errors="replace")
    jp = _paragraphs(jtxt)
    if len(jtxt) > 2000 and not jp:
        raise RuntimeError(f"{JOURNAL}: {len(jtxt)} chars but 0 paragraphs parsed — format changed")
    units["system/journal.md"] = jp

    return units


def _human_decision_counts(units: dict) -> dict:
    """The denominator for each source — what was EXAMINED, never what matched (HARD CONSTRAINT 2)."""
    briefs = sorted(DRIVE.glob(BRIEF_GLOB))
    return {
        "state/debt-ledger.md": {"bullets_examined": len(units["state/debt-ledger.md"])},
        "state/projects/**/brief.md": {"briefs_examined": len(briefs),
                                        "bullets_examined": len(units["state/projects/**/brief.md"])},
        "state/open-loops.md": {"bullets_examined": len(units["state/open-loops.md"])},
        "system/journal.md": {"paragraphs_examined": len(units["system/journal.md"])},
    }


def human_ruling_for(name: str, units: dict) -> Optional[str]:
    """Has a human already ruled on the file `name` (an exact basename, e.g. `vault-related.py`)?
    Returns a short quote naming the source + the ruling text, or None.

    ⚠⚠ EXACTLY WHAT THIS REQUIRES, so the match can be re-derived by hand (§18.10 decision 2):
      LEDGER — the filename appears as a whole token (bounded by `(?<![\\w.-])…(?![\\w.-])`, so it
      can never match inside a longer filename or path segment) INSIDE a bullet whose OWN
      `` `type:…` ``/`` `state:…` `` tags read `type:decision` or `state:parked`/`state:retired` —
      the structured vocabulary `backlog_groom.py` already parses, reused rather than re-invented
      (§18.10 SAFE-HALT). This is why `[OBSIDIAN-BRAIN-SWAP]` (`type:decision` `state:parked`)
      catches `vault-related.py`/`vault-theme-map.py` and the unrelated `[SYSTEM-RENEWAL-AUDIT]`
      row (`type:project` `state:parked`, which merely lists several skills as FUTURE audit
      subjects) does not pollute it — tags are per-BULLET, not per-file, so a tag on entry A can
      never rule on a file only entry B happens to also mention.
      PROSE (briefs / open-loops / journal, none of which carry `type:`/`state:` tags) — the
      filename must appear BACKTICK-QUOTED (a real code reference, not incidental prose) AND a
      RULING_WORDS hit must fall within ±150 chars of it AND no UNDECIDED marker may appear in
      that same window. Both gates were sized by hand against every current `SKILL-FAMILY` member
      name as a stress test (T20.6) — the backtick + word + no-undecided combination is what tells
      `translator-mine-pairs.py` (`` `system/tools/translator-mine-pairs.py` `` next to "RETIRED as
      training work") apart from `emily-2-interrogate` (an "OPEN QUESTION … leaning KEEP", i.e.
      explicitly NOT yet decided).
    ⚠ Applied ONLY to `NOTHING-REACHES-IT` (this function's caller). NOT applied to `SKILL-FAMILY`/
    ELIMINATE or `CLI-NEVER-INVOKED` — see `detect_introduce`'s docstring for why: the stress test
    above found the prose gate still false-matches bare skill-directory names (short, hyphenated,
    prone to appearing in unrelated tier/score lists) closely enough to a ruling word that trusting
    it there would be a FALSE SUPPRESSION, which costs more than the noise it would remove.
    """
    tok = re.compile(rf"(?<![\w.-]){re.escape(name)}(?![\w.-])")
    for u in units["state/debt-ledger.md"]:
        if not tok.search(u):
            continue
        types = set(m.lower() for m in re.findall(r"`type:([\w-]+)`", u))
        states = set(m.lower() for m in re.findall(r"`state:([\w-]+)`", u))
        if "decision" in types or "parked" in states or "retired" in states:
            return f"state/debt-ledger.md: {' '.join(u.split())[:220]}"

    prose_tok = re.compile(rf"`[^`]*(?<![\w.-]){re.escape(name)}(?![\w.-])[^`]*`")
    for src in ("state/projects/**/brief.md", "state/open-loops.md", "system/journal.md"):
        for u in units[src]:
            for m in prose_tok.finditer(u):
                window = u[max(0, m.start() - PROSE_WINDOW):m.end() + PROSE_WINDOW]
                if RULING_WORDS.search(window) and not UNDECIDED.search(window):
                    return f"{src}: {' '.join(window.split())[:220]}"
    return None


def detect_introduce(roots: str, decision_units: dict) -> list:
    """Missing capability, WITH A RECEIPT.

    ⭐ TWO SHAPES, and the second is the one that matters — learned by failing BAR 2 on the first
    run. `recommendation_disposition.py` is IMPORTED by `health_line.py` (its read half,
    `latest_dispositions()`), and `health_line.py` is reachable, so a naive "is this file
    referenced?" test marks it live and misses the hole entirely.

    **But its WRITE half — the CLI that records a human's accept/reject — is invoked by nothing.**
    The library is used; the command is dead. ⇒ the system can read dispositions that nothing can
    ever create, which is precisely "nothing records whether the loop closed."

    So: (a) NOTHING-REACHES-IT — no reference at all, and (b) CLI-NEVER-INVOKED — a real
    command-line entry point that no root ever runs, even if the module is imported elsewhere.
    (b) is strictly sharper: a half-wired capability looks live to every simpler check.
    """
    props = []
    all_tools = _tool_files()
    for p in all_tools:
        name = p.name
        if name in ("architecture_reason.py", "seam_reason.py"):
            continue
        rel = str(p.relative_to(REPO))
        if any(m in rel for m in LAB_MARKERS):
            continue
        try:
            txt = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        m = re.search(r'"""(.*?)"""', txt, re.S)
        doc = (m.group(1).strip() if m else "")
        if len(doc) < DOCSTRING_MIN:
            continue                                   # a stub is not a described capability
        if re.search(r"RETIRED|DO NOT RE-REGISTER|run by hand|one-shot|ONE-TIME", doc, re.I):
            continue                                   # it says itself that this is its right state
        first = doc.splitlines()[0][:150]

        # (b) CLI-NEVER-INVOKED — the sharp one. A real command entry point that no root RUNS.
        has_cli = ('if __name__ == "__main__"' in txt or "argparse" in txt)
        # T20.4: a genuine `.py`-invokes-`.py` reference also counts — but ONLY a top-level,
        # unindented `import X` / `from X import …` (anchored to column 0 with re.MULTILINE).
        # That is the mechanical line between "this module's code runs whenever the importing
        # file runs" (backlog-health.py: `import backlog_groom` at column 0, then
        # `backlog_groom.build_report()` unconditionally in `main()`) and a deliberately
        # isolated, best-effort LOCAL import three stack frames deep inside a try/except (see
        # `health_line.py`'s `from recommendation_disposition import latest_dispositions` —
        # indented, alarm-guarded, and commented "sibling must not break THIS import"). The
        # second shape reads one function of a module without ever exercising its own CLI, which
        # is exactly BAR 2's specimen — it must stay flagged, so indentation is the signal kept.
        # ⭐ T27.1, 2026-08-08 — ONE definition, shared with `--census`. This was an inline copy
        # of the identical regex until the census needed the same question answered; two copies
        # of one fact is the exact drift this lane exists to DETECT, so it does not get to live
        # inside the detector. `_invoked_by()` carries the semantics unchanged.
        invoked = _invoked_by(name, roots)
        if has_cli and not invoked:
            props.append({
                "verb": "INTRODUCE",
                "klass": "CLI-NEVER-INVOKED",
                "proposal": (f"{p.relative_to(REPO)} has a command-line entry point that NOTHING runs — "
                             f"{first}. Its library half may be imported and look live; the COMMAND half "
                             f"is dead, so whatever it records can be read but never created. "
                             f"INTRODUCE the caller, or ELIMINATE the entry point."),
                "evidence": [
                    f"{p.relative_to(REPO)}: has argparse/__main__ ({len(doc)}-char docstring)",
                    f"no Pulse row, cron line, hook, or skill invokes it as a command "
                    f"(searched roots for `python3 …{name}`)",
                    f"{len(all_tools)} tool files examined",
                ],
                "targets": [str(p.relative_to(REPO))],
                "slug": f"uncalled:{name}",
            })
            continue

        # (a) NOTHING-REACHES-IT — no reference anywhere, from any live surface.
        if name in roots:
            continue
        # ⛔ T27.1b, 2026-08-08 — GUARDED, and it was NOT guarded before. An adversarial arm
        # planted a `chmod 000` file and this exact line crashed `--dry-run`, `--json` AND
        # `--selftest` with an uncaught PermissionError, full traceback, exit 1. Pre-existing —
        # identical at 9146d6a — but the widening took the exposure from 1 directory to 4 and
        # from 279 files to 403, and `system/hooks/` is precisely the kind of directory whose
        # permissions someone tightens one day. The per-file read two dozen lines up was already
        # wrapped; this one was the survivor. `--census` never had the bug (its loop is guarded).
        def _readable(q):
            try:
                return q.read_text(encoding="utf-8", errors="replace")
            except Exception:
                return ""                              # unreadable vouches for nothing
        others = [q for q in all_tools if q != p and name in _readable(q)]
        if any(q.name in roots for q in others):
            continue

        # T20.6 — THE FIX. Before the person caught it, this branch emitted unconditionally, even
        # though `build()` already opens `state/debt-ledger.md` in the SAME process for `LEDGER-
        # NAMED-OVERBUILD`. `vault-related.py`/`vault-theme-map.py` are named in `[OBSIDIAN-BRAIN-
        # SWAP]` (`type:decision` `state:parked`, the person floor-vetoed the swap they'd break) and
        # `translator-mine-pairs.py` is recorded RETIRED-in-place in its own project's brief — both
        # are a human ruling this lane had the receipt for and never read. See `human_ruling_for`'s
        # docstring for exactly what counts as a ruling and why it can't over-suppress.
        ruling = human_ruling_for(name, decision_units)
        if ruling:
            props.append({
                "verb": "INTRODUCE", "klass": "NOTHING-REACHES-IT-SUPPRESSED",
                "proposal": f"NOT emitted — a human already ruled on {p.relative_to(REPO)}: {ruling}",
                "evidence": [ruling], "targets": [str(p.relative_to(REPO))],
                "slug": f"ruled:{name}",
            })
            continue

        props.append({
            "verb": "INTRODUCE",
            "klass": "NOTHING-REACHES-IT",
            "proposal": (f"a capability exists and nothing can reach it: {p.relative_to(REPO)} — "
                         f"{first}. The system decided it needed this, built it, and never wired it. "
                         f"INTRODUCE the caller, or ELIMINATE the file — it cannot stay both."),
            "evidence": [
                f"{p.relative_to(REPO)} carries a {len(doc)}-char docstring describing a capability",
                f"no Pulse row, hook registration, skill, or reachable tool references {name}",
                f"{len(all_tools)} tool files examined; roots = pulse-config.md + settings.json "
                f"+ .claude/skills/ + ~/.claude/skills/ + hooks/",
                f"checked for a prior human ruling in state/debt-ledger.md, every "
                f"state/projects/**/brief.md, state/open-loops.md and system/journal.md — none found",
            ],
            "targets": [str(p.relative_to(REPO))],
            "slug": f"unreached:{name}",
        })
    return props


def build() -> dict:
    import backlog_groom
    try:
        ledger = backlog_groom.parse_ledger()
    except Exception:
        ledger = []
    roots = _roots()
    decision_units = _human_decision_units()
    decision_counts = _human_decision_counts(decision_units)

    skill_dirs, skill_status = _skill_dirs()
    # ⛔⛔ THE ZERO-EXAMINED GUARD, T18.10-PORT-FIX 2026-08-22 — HARD CONSTRAINT: "a detector that
    # examines zero files must NOT report success." Every candidate skill location missing (or
    # every one present but empty) means the walk found NOTHING to judge — that is a BROKEN
    # DETECTOR, not evidence the system has zero skill families. This is exactly the measured
    # failure this project already carries a name for: "a script printed PASSED daily for two
    # months and wrote no file." Raising here (same pattern as `_human_decision_units()`'s missing-
    # source checks above) is what stops a silent, confident, empty SKILL-FAMILY pass.
    if not skill_dirs:
        raise RuntimeError(
            "0 skill directories found across every skill location examined "
            f"({skill_status}) — the SKILL-FAMILY walk found nothing to judge, which is a broken "
            "detector, not a clean system. Fix: confirm .claude/skills/ exists in this repo "
            "checkout, or ~/.claude/skills/ for this operator."
        )

    elim = detect_eliminate(ledger, skill_dirs, skill_status)
    intro_raw = detect_introduce(roots, decision_units)
    suppressed = [p for p in intro_raw if p["klass"] == "NOTHING-REACHES-IT-SUPPRESSED"]
    intro = [p for p in intro_raw if p["klass"] != "NOTHING-REACHES-IT-SUPPRESSED"]
    return {
        "ledger_entries_examined": len(ledger),
        "tool_files_examined": len(_tool_files()),
        "skill_dirs_examined": len(skill_dirs),
        "skill_locations_examined": skill_status,
        "human_decision_sources_examined": decision_counts,
        "eliminate": elim,
        "introduce": intro,
        "introduce_suppressed_by_human_ruling": suppressed,
        "total": len(elim) + len(intro),
    }


def _collapsed(props: list) -> list:
    """Fold a class with one shared root cause into ONE row.

    ⚠ REUSED, not rewritten: `seam_reason.collapse()` already solves this and learned it the
    expensive way (106 raw seams, 41 of them one fact restated). §18.10 SAFE-HALT says reuse or
    stop. The shapes match — both carry klass/slug/targets — so the only adaptation is mapping
    `evidence` to the `fingerprints` key it expects, and back.
    """
    import seam_reason
    shaped = [{**p, "fingerprints": p["evidence"], "seam": p["proposal"]} for p in props]
    out = []
    for c in seam_reason.collapse(shaped):
        out.append({
            "verb": c.get("verb") or (props[0]["verb"] if props else "ELIMINATE"),
            "klass": c["klass"],
            "proposal": c.get("seam", ""),
            "evidence": c.get("fingerprints", []),
            "targets": c.get("targets", []),
            "slug": c["slug"],
        })
    return out


def emit(result: dict) -> int:
    from emit_recommendation import emit_recommendation, RecommendationContractError
    n = 0
    for p in _collapsed(result["eliminate"]) + _collapsed(result["introduce"]):
        try:
            emit_recommendation(
                producer=PRODUCER,
                altitude=ALTITUDE,
                action=f"{p['verb']} [{p['klass']}] — {p['proposal']}",
                evidence=p["evidence"],
                labels={"verb": p["verb"], "klass": p["klass"], "slug": p["slug"]},
                summary=p["proposal"][:180],
            )
            n += 1
        except RecommendationContractError as ex:
            print(f"  REFUSED (contract): {p['slug']}: {ex}", file=sys.stderr)
    return n


def selftest() -> int:
    print("architecture_reason --selftest — the §18.10b acceptance bars, live data\n")
    r = build()
    print(f"  examined: {r['ledger_entries_examined']} ledger entries · "
          f"{r['tool_files_examined']} tool files")
    dc = r["human_decision_sources_examined"]
    print(f"  human-decision sources examined: "
          f"{dc['state/debt-ledger.md']['bullets_examined']} ledger bullets · "
          f"{dc['state/projects/**/brief.md']['briefs_examined']} briefs "
          f"({dc['state/projects/**/brief.md']['bullets_examined']} bullets) · "
          f"{dc['state/open-loops.md']['bullets_examined']} root open-loop bullets · "
          f"{dc['system/journal.md']['paragraphs_examined']} journal paragraphs")
    print(f"  ELIMINATE: {len(r['eliminate'])} · INTRODUCE: {len(r['introduce'])} · "
          f"suppressed by human ruling: {len(r['introduce_suppressed_by_human_ruling'])}\n")
    ok = True

    fam = [p for p in r["eliminate"] if p["klass"] == "SKILL-FAMILY"]
    ren = [p for p in r["eliminate"] if "renewal" in p["slug"].lower()
           or "consolidat" in p["proposal"].lower()]
    if fam or ren:
        print("  ✓ BAR 1 (ELIMINATE) — independently reached a consolidation proposal")
        for p in (fam + ren)[:3]:
            print(f"      └ {p['proposal'][:140]}")
    else:
        print("  ✗ BAR 1 (ELIMINATE) — no consolidation proposal reached")
        ok = False

    disp = [p for p in r["introduce"] if "recommendation_disposition" in p["slug"]]
    if disp:
        print("  ✓ BAR 2 (INTRODUCE) — reached the closure-signal hole unaided")
        print(f"      └ {disp[0]['proposal'][:200]}")
    else:
        print("  ✗ BAR 2 (INTRODUCE) — did NOT reach recommendation_disposition.py")
        print(f"      (found instead: {[p['slug'] for p in r['introduce']][:8]})")
        ok = False

    src = Path(__file__).read_text(encoding="utf-8")
    probes = ["def " + "apply", "def " + "remediate", "def " + "autofix",
              "shutil" + ".move", "os" + ".replace"]
    bad = [w for w in probes if w in src]
    if bad:
        print(f"  ✗ BAR 3 — an applier-shaped symbol exists: {bad}")
        ok = False
    else:
        print("  ✓ BAR 3 — no applier in this file (propose-only holds)")

    # BAR 4 — T20.6 REGRESSION GUARD. On the first board `NOTHING-REACHES-IT` went 3-for-3 FALSE:
    # `vault-related.py`/`vault-theme-map.py` (parked, the person floor-vetoed the swap that would
    # break them) and `translator-mine-pairs.py` (retired-in-place, its brief's own words). All
    # three are human rulings this file already had the receipt for (the ledger it opens for BAR 1)
    # and never read before proposing. This bar proves the fix holds: the three stay OFF the live
    # board and ON the suppressed list, not silently dropped either way (constraint: "never
    # suppress a row a human has NOT ruled on" cuts both directions — a suppression with no
    # visible reason is just as dishonest as an unruled proposal).
    specimens = {"vault-related.py", "vault-theme-map.py", "translator-mine-pairs.py"}
    still_present = {s for s in specimens if (TOOLS / s).exists()}
    proposed_names = {p["targets"][0].rsplit("/", 1)[-1] for p in r["introduce"]
                       if p["klass"] == "NOTHING-REACHES-IT"}
    suppressed_names = {p["targets"][0].rsplit("/", 1)[-1]
                         for p in r["introduce_suppressed_by_human_ruling"]}
    if not still_present:
        print("  · BAR 4 — the 3 specimen files are gone from disk; bar not applicable")
    elif (proposed_names & specimens) or (still_present - suppressed_names):
        print(f"  ✗ BAR 4 — REGRESSION: wrongly proposed {sorted(proposed_names & specimens)}; "
              f"missing from suppressed list {sorted(still_present - suppressed_names)}")
        ok = False
    else:
        print(f"  ✓ BAR 4 (T20.6) — all {len(still_present)} ruled specimens suppressed, "
              f"0 wrongly proposed")

    print("\n" + ("✓ SELFTEST PASSED — both verbs reach their specimen, and nothing applies."
                  if ok else "✗ SELFTEST FAILED"))
    return 0 if ok else 1


def build_census() -> dict:
    """Every capability file in the TERRITORY → what it says it is → whether anything runs it.

    ⭐⭐ T27.1's actual deliverable. `detect_introduce` above answers "which of these is
    UNREACHABLE" and emits only the guilty; this answers "what do we HAVE", including the 358
    files that are perfectly fine — and that second question is the one a blind session about to
    build a duplicate needs. A detector that reports only faults cannot answer it.

    ⛔ IT IS A CENSUS, NOT A CITATION GRAPH, and the distinction is load-bearing enough that the
    rendered file says so in its own header (`build-sop.md:133`): the denominator is GLOBBED FROM
    THE TERRITORY, never read off any document's list of what it cites.
    `system/organism/generated/organism-map.json` is the citation graph and is exactly backwards
    for "find what nothing invokes" — it can only ever see what is already cited.

    ⚠ `invoked` here means the SAME thing it means to `detect_introduce`, because it is computed
    by the same `_invoked_by()`. A file marked UNCALLED is not automatically a defect: a library
    imported three frames deep inside a try/except is deliberately excluded (see T20.4's note on
    that regex), and some files are genuinely meant to be run by hand.
    """
    import datetime
    roots = _roots()
    files = _tool_files()
    rows = []
    texts = {}                                         # read ONCE, reused by the artifact pass
    for p in files:
        try:
            txt = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            txt = ""                                   # unreadable is a row, never a crash
        rel = str(p.relative_to(REPO))
        texts[rel] = txt
        rows.append({
            "path": rel,
            "invoked": bool(_invoked_by(p.name, roots)),
            "what": _self_description(p, txt),
        })
    return {
        "artifacts": build_artifact_census(texts),
        "generated": datetime.date.today().isoformat(),
        "rows": sorted(rows, key=lambda r: r["path"]),
        "collisions": _basename_collisions(files),
        "by_root": {str(root.relative_to(REPO)): sum(
            1 for r in rows if r["path"].startswith(str(root.relative_to(REPO)) + "/"))
            for root in TERRITORY if root.exists()},
    }


def _artifact_files() -> list:
    """The DERIVED-ARTIFACT territory — data files a tool produces, not tools themselves.

    ⭐⭐ T27.15 — WHY THIS EXISTS AND THE TOOL CENSUS DOES NOT COVER IT. The thing a session
    nearly rebuilt on 2026-08-08 was not a tool. It was a DATA ARTIFACT: `inventory-2026-07-16.jsonl`,
    481 records, the richest schema on disk — and DEAD, because nothing in the repo generates it and
    nothing reads it. A tool index would never have surfaced it, and `deadend_check.py` cannot see it
    either (it reads only `DO NOT BUILD` prose). Either of the two fields below, alone, would have
    stopped that session cold.

    ⛔ SCOPE IS THE PLAN'S, DELIBERATELY NOT WIDER: `system/*registry*` / `system/*manifest*` are
    TOP-LEVEL globs. `system/factory/frozen/**` holds dozens of `coverage-manifest.md` files that are
    FROZEN ON PURPOSE — sweeping them in would bury the live signal under archives that are supposed
    to be static, which is how a real finding becomes wallpaper.
    """
    out, seen = [], set()
    globs = [
        (REPO, "system/organism/generated/*"),
        (REPO, "system/*registry*"),
        (REPO, "system/*manifest*"),
        (DRIVE, "state/projects/*/*/inventory/*"),
        (DRIVE, "state/projects/*/inventory/*"),
    ]
    for root, pat in globs:
        try:
            if not root.exists():
                continue
            for p in sorted(root.glob(pat)):
                if not p.is_file() or p.suffix in (".py", ".sh"):
                    continue               # code is the TOOL census's job, not this one
                if ".bak" in p.name or p.name.startswith("."):
                    continue
                key = p.resolve()
                if key in seen:
                    continue
                seen.add(key)
                out.append((root, p))
        except OSError:
            continue                       # Drive is a FUSE mount; an unreadable root is not a crash
    return out


# Write verbs, in the order of how often they actually appear in this codebase. A mention near one
# of these is a GENERATOR; a mention with none of them nearby is a READER.
_WRITE_NEAR = ("write_text", ".write(", "json.dump", "mkdir", "tee ", "'w'", '"w"',
               "'a'", '"a"', "shutil.copy", "rename(", "replace(")
# ⛔ SHELL REDIRECTS ARE `.sh`-ONLY, AND THAT RESTRICTION IS LOAD-BEARING (2026-08-08).
# `"> "` and `">>"` lived in the list above for one afternoon and produced a FALSE GENERATOR on the
# dead inventory: `render_census()` emits MARKDOWN, whose blockquote lines are string literals
# beginning `"> "`, and two of them quote the inventory's filename while explaining why it is dead.
# ⇒ the tool's own rendered prose read as a shell redirect writing that file.
# ⭐ Note this survived `_code_only()` and CORRECTLY so — those lines are real code, not comments.
# Stripping prose was necessary and not sufficient; the second half is not treating a markdown
# blockquote as a filesystem operation. Same disease as the two fixes above, third costume.
_WRITE_NEAR_SH = ("> ", ">>")


def _code_only(txt: str, suffix: str) -> str:
    """The file with its PROSE removed — comments and docstrings gone, code kept.

    ⛔⛔ THIS EXISTS BECAUSE THE ARTIFACT SCAN MATCHED ITS OWN DESCRIPTION (2026-08-08, caught before
    it shipped). `_artifact_files()`'s own docstring names `inventory-2026-07-16.jsonl` while
    EXPLAINING why that file is dead — and the scan read that mention as evidence that this tool
    GENERATES it, printing `generated-by: system/tools/architecture_reason.py` for a file it has
    never written. The plan's verify demands that row read `NOTHING`, and it did not.
    ⭐ THE SAME BUG, THIRD TIME IN THIS PROJECT: `gauge_check.py` once returned `PARTIAL-RUNGS 6` on a
    brief because three lines of prose merely MENTIONED the marker while describing the tool
    (`skills/checkin/SKILL.md` records it). A scanner that reads documentation as data will always
    resurrect its own examples. **Prose is where a file talks ABOUT things; code is where it DOES
    them** — and only the second one is evidence.
    ⚠ Conservative on purpose: a `#` only counts as a comment when it OPENS the stripped line, so a
    `#` inside a shell string is never mistaken for one.
    """
    if suffix == ".py":
        txt = re.sub(r'"""(?:.|\n)*?"""', "", txt)
        txt = re.sub(r"'''(?:.|\n)*?'''", "", txt)
    return "\n".join(ln for ln in txt.splitlines() if not ln.strip().startswith("#"))


def _artifact_refs(name: str, texts: dict) -> tuple:
    """Who WRITES this artifact, and who merely READS it — from the tool corpus, by name.

    ⚠ STATE THE METHOD, STATE THE BOUND (`build-sop.md:133`). This is a MENTION scan with a
    write-verb window, not a data-flow analysis. It answers "which tool file names this artifact,
    and does it look like it writes it" — nothing stronger. Treat a result as a LIST TO CHECK,
    exactly as `CLI-NEVER-INVOKED` is. ⭐ But the finding that matters — NOTHING mentions this file
    AT ALL — is not a heuristic. That one is certain, and it is the one that catches a dead artifact.
    """
    gens, reads = [], []
    for rel, raw in texts.items():
        suffix = "." + rel.rsplit(".", 1)[-1]
        txt = _code_only(raw, suffix)
        if name not in txt:
            continue                                   # mentioned only in prose = not a reference
        verbs = _WRITE_NEAR + (_WRITE_NEAR_SH if suffix == ".sh" else ())
        lines = txt.splitlines()
        writes = False
        for i, ln in enumerate(lines):
            if name not in ln:
                continue
            window = "\n".join(lines[max(0, i - 2):i + 3])
            if any(v in window for v in verbs):
                writes = True
                break
            # ⭐ CONSTANT INDIRECTION — the other half of the bug, and it failed the OPPOSITE way.
            # `CENSUS_OUT = REPO / … / "capability-census.md"` sits nowhere near the
            # `CENSUS_OUT.write_text(...)` that actually writes it, so a ±2-line window called the
            # census "generated by NOTHING" — a file this very module writes every weekly run.
            # ⇒ resolve the name the path was BOUND to, then look for a write through that name.
            m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*=", ln)
            if m and re.search(rf"\b{re.escape(m.group(1))}\b\s*\.\s*(?:write_text|open|mkdir)"
                               rf"|json\.dump\([^)]*\b{re.escape(m.group(1))}\b", txt):
                writes = True
                break
        # ⛔ THE SELF-EXCLUSION, AND IT IS ASYMMETRIC ON PURPOSE (2026-08-08, the last costume).
        # THIS module is the one that DESCRIBES artifacts — `render_census()` quotes the dead
        # inventory's filename twice while explaining why it is dead. Those are string literals, so
        # `_code_only()` keeps them (correctly — they are code), and a bare mention is exactly what
        # "reader" is inferred from. ⇒ this file would list itself as a READER of every artifact it
        # documents, forever.
        # ⭐ ASYMMETRIC because the two directions have different evidence: a GENERATOR claim is
        # PROVEN (a write verb, or a constant resolved to a write), so self stays eligible — it
        # genuinely writes the census and must say so. A READER claim rests on a bare mention, which
        # for this file is its subject matter, not a reference.
        # ⚠ PRECEDENT, not invention: `detect_introduce` already skips `architecture_reason.py` and
        # `seam_reason.py` in its own walk for the identical reason — a detector that reads itself
        # resurrects its own examples.
        if writes:
            gens.append(rel)
        elif rel != "system/tools/architecture_reason.py":
            reads.append(rel)
    return sorted(gens), sorted(reads)


def build_artifact_census(texts: dict) -> list:
    """Every derived artifact → what generates it (or NOTHING) → what reads it (or NOTHING)."""
    rows = []
    for root, p in _artifact_files():
        try:
            rel = str(p.relative_to(root))
        except ValueError:
            rel = str(p)
        label = rel if root == REPO else "[drive] " + rel
        gens, reads = _artifact_refs(p.name, texts)
        try:
            size = p.stat().st_size
        except OSError:
            size = -1
        rows.append({"path": label, "generators": gens, "readers": reads, "bytes": size})
    return sorted(rows, key=lambda r: r["path"])


def render_census(c: dict) -> str:
    """One greppable file. A fixed leading token per line so `grep '^UNCALLED'` is the query."""
    n = len(c["rows"])
    uncalled = sum(1 for r in c["rows"] if not r["invoked"])
    out = [
        "# CAPABILITY CENSUS — every tool, part, shared tool and hook in the system",
        "",
        f"> ⛔ **DERIVED. REGENERATED EVERY RUN. NEVER HAND-EDIT THIS FILE.** A hand-kept index",
        "> rots and then LIES, which is worse than having none — the worked example is",
        "> `inventory-2026-07-16.jsonl`: the richest schema on disk, dead in three weeks.",
        ">",
        "> ⭐ **REFRESHED AUTOMATICALLY by the `architecture-reachability` Pulse job (WEEKLY), which",
        "> runs `reachability_finding.py` — the same run that computes the unwired cohort. You do NOT",
        "> have to remember to regenerate this.** One clock: if a human had to type a command to",
        "> refresh it, it would be HAND-KEPT, and a hand-kept index rots and then lies.",
        ">",
        "> **Regenerate by hand anyway (gitignored — the other machine regenerates, it does not pull):**",
        ">",
        ">     python3 system/tools/architecture_reason.py --census",
        ">",
        "> ⭐ **THIS IS A CENSUS, NOT A CITATION GRAPH.** The denominator is GLOBBED FROM THE",
        "> TERRITORY — every `.py`/`.sh` under the four roots below — never read off a document's",
        "> own list of what it cites. `system/organism/generated/organism-map.json` IS the citation",
        "> graph, and it is exactly backwards for *\"find what nothing invokes\"*: it can only see",
        "> what is already cited. Do not wire that one into a reachability question.",
        ">",
        "> **`UNCALLED` is a QUESTION, not a verdict.** It means no root runs this file as a command",
        "> and no module imports it at top level. Some files are meant to be run by hand.",
        "",
        f"**Generated {c['generated']} · {n} capability files · {uncalled} UNCALLED**",
        "",
        "| root | files |",
        "|---|---|",
    ]
    for root, cnt in c["by_root"].items():
        out.append(f"| `{root}/` | {cnt} |")
    out += ["", "## ⛔ BASENAME COLLISIONS — one name, two different files", ""]
    if c["collisions"]:
        out.append("**The reachability test keys on the BASENAME, so one sibling silently vouches")
        out.append("for the other.** Reported, never auto-resolved — which copy is canonical is a")
        out.append("human's call, and a collision is the loudest possible *does this already exist?*")
        out.append("signal this lane can emit.")
        out.append("")
        for name, paths in c["collisions"].items():
            out.append(f"- **`{name}`** — " + " · ".join(f"`{p}`" for p in paths))
    else:
        out.append("_None._")
    arts = c.get("artifacts", [])
    dead = [a for a in arts if not a["generators"] and not a["readers"]]
    out += [
        "",
        "## ⛔ DERIVED ARTIFACTS — what generates each one, and what reads it",
        "",
        "**The two fields that matter are `generated-by: NOTHING` and `read-by: NOTHING`.** Both were",
        "true of `inventory-2026-07-16.jsonl` — 481 records, the richest schema on disk, dead in three",
        "weeks — and on 2026-08-08 a session came one turn from rebuilding it. **Either field alone",
        "would have stopped that cold.** A TOOL index cannot surface this: the thing nearly rebuilt was",
        "not a tool, it was a data file.",
        "",
        "⚠ **METHOD, AND ITS BOUND.** Generators/readers come from a MENTION scan of the "
        f"{len(c['rows'])} capability files, with a write-verb window — not a data-flow analysis. A",
        "named generator is a LIST TO CHECK, exactly like `UNCALLED` above. **But `NOTHING` is not a",
        "heuristic: it means no capability file mentions this artifact at all, and that one is certain.**",
        "",
        f"**{len(arts)} derived artifacts · {len(dead)} with NO generator AND NO reader.**",
        "",
        "Grep `generated-by: NOTHING` for artifacts nothing can refresh.",
        "",
    ]
    for a in arts:
        g = ", ".join(a["generators"]) if a["generators"] else "NOTHING"
        r = ", ".join(a["readers"]) if a["readers"] else "NOTHING"
        tag = "ORPHAN  " if (not a["generators"] and not a["readers"]) else "ARTIFACT"
        out.append(f"{tag}  {a['path']} — generated-by: {g} · read-by: {r}")
    out += [
        "",
        "## THE CENSUS",
        "",
        "Grep this section. `^UNCALLED` for the unreachable, `^INVOKED` for the wired,",
        "or grep a capability you are about to build and see if it already exists.",
        "",
    ]
    for r in c["rows"]:
        tag = "INVOKED " if r["invoked"] else "UNCALLED"
        out.append(f"{tag}  {r['path']} — {r['what'] or '(no self-description)'}")
    return "\n".join(out) + "\n"


def cmd_census(write: bool) -> int:
    c = build_census()
    text = render_census(c)
    n = len(c["rows"])
    uncalled = sum(1 for r in c["rows"] if not r["invoked"])
    if not write:
        print(text)
        print(f"[architecture-reason] --dry-run: nothing written ({n} files, {uncalled} UNCALLED)")
        return 0
    CENSUS_OUT.parent.mkdir(parents=True, exist_ok=True)
    CENSUS_OUT.write_text(text, encoding="utf-8")
    print(f"[architecture-reason] census: {n} capability files · {uncalled} UNCALLED · "
          f"{len(c['collisions'])} basename collision(s)")
    for root, cnt in c["by_root"].items():
        print(f"    {root}/: {cnt}")
    print(f"[architecture-reason] wrote {CENSUS_OUT}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(prog="architecture_reason.py")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--census", action="store_true",
                    help="publish the capability index (respects --dry-run)")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.census:
        return cmd_census(write=not a.dry_run)
    r = build()
    if a.json:
        print(json.dumps(r, indent=2))
        return 0
    print(f"[architecture-reason] examined {r['ledger_entries_examined']} ledger entries · "
          f"{r['tool_files_examined']} tool files")
    if r["introduce_suppressed_by_human_ruling"]:
        print(f"[architecture-reason] {len(r['introduce_suppressed_by_human_ruling'])} "
              f"NOTHING-REACHES-IT candidate(s) NOT emitted — a human already ruled on them:")
        for p in r["introduce_suppressed_by_human_ruling"]:
            print(f"  · {p['targets'][0]}: {p['proposal'][:150]}")
    for p in r["eliminate"] + r["introduce"]:
        print(f"  · {p['verb']} [{p['klass']}] {p['proposal'][:150]}")
    if a.dry_run:
        print("[architecture-reason] --dry-run: nothing written")
        return 0
    n = emit(r)
    print(f"[architecture-reason] wrote {n} recommendation(s) at {ALTITUDE}")
    return 0


if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "system", "tools")))
    from utf8_stdio import force_utf8_stdio
    force_utf8_stdio()
    sys.exit(main())

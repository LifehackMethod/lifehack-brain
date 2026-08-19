#!/usr/bin/env python3
"""
save_step_ledger.py — record WHICH mandatory /save steps actually ran, so a skipped step is VISIBLE.

WHY (council condition [S-2], Priya — organism-audit S2.8):
    Feature F3.2 was dropped on the rule "reopens only on a logged skipped-step failure." But
    **nothing logs a skipped step**, so that trigger can never fire. Priya's words: *"An unfalsifiable
    reopen-condition is the same defect as a pointer to a gate: a wish."* The drop is only honest if
    the condition it rests on is testable.

    `/save`'s Step 9 coverage note is a STATIC disclaimer — it says the journal may be incomplete, but
    it never says which parts of THIS run executed. So a run that silently skipped the journal write
    or the debt-ledger sweep closes looking exactly like a clean one. Same shape as every other defect
    this audit found: a component reporting success while producing nothing observable.

THE FIX IS A LEDGER, NOT A SENTENCE. Each mandatory step stamps itself as it completes; Step 9 prints
what the LEDGER says, not what the model remembers. A step that never ran cannot stamp itself, so it
shows as MISSED — and the reopen-trigger finally has something to fire on.

Honest limit (same as every stamp of this kind): the ledger proves a step was REACHED, not that it was
done well. It converts "silently skipped" into "visibly missed", which is the difference between an
unfalsifiable condition and a testable one.

Usage:
  save_step_ledger.py start                  # begin a run (clears this session's ledger)
  save_step_ledger.py stamp <step-id>        # a step marks itself done (bare — self-reported)
  save_step_ledger.py stamp compact <brief>  # CAUSED, not generated — refuses unless
                                              # `pad_archive.py verify <brief>` exits 0 AND its
                                              # newest block postdates this run's `started`
  save_step_ledger.py report [--pad-had-content ...]   # the coverage table for Step 9
  save_step_ledger.py --selftest             # offline proof

Report markers: `✓` mechanically/structurally evidenced · `~` self-reported, unverified (no
possible artifact exists to check) · `–` n/a this run · `✗ MISSED`.
"""
from __future__ import annotations           # system python is 3.9

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

RUN_DIR = Path.home() / ".claude" / "run" / "save-ledger"

# The mandatory spine of a /save run. `applies` marks steps that are conditional — they are reported
# as N/A rather than MISSED when their condition did not arise, so the table never cries wolf.
MANDATORY = [
    ("0.4", "pm_flag_recover called", "always"),
    ("0.5", "slug resolved (no silent guess)", "always"),
    ("SC-1", "items extracted with reasoning", "only-if-session-close"),
    ("tier", "each item tiered by durability", "only-if-session-close"),
    ("canon-gate", "canon confirm-gate awaited", "only-if-canon-candidate"),
    ("7c.5", "debt-ledger swept for new/discovered debt", "always"),
    ("7d", "journal written BEFORE the brief (journal-first)", "only-if-findings"),
    ("compact", "brief SCRATCHPAD archived before compaction (pad_archive verified)",
     "only-if-pad-had-content"),
    ("8", "continuation handoff emitted", "only-if-session-close"),
    ("graduate", "§2 CURRENT STATE graduated (pad_archive verified)", "only-if-session-close"),
    ("9", "coverage note printed", "always"),
]
IDS = [m[0] for m in MANDATORY]

# Steps that CANNOT have a mechanical artifact — a bare stamp is the only possible evidence, so the
# report must show that plainly instead of the same ✓ a mechanically-verified step earns. `7d` and
# `0.5` DO have possible artifacts (a journal write; a resolved slug) but verifying them is a separate
# ticket — left as bare ✓ for now, deliberately not added to this set. `compact` is verified below
# (CAUSED, not generated) so it also earns a real ✓.
NO_ARTIFACT_IDS = {"0.4", "SC-1", "tier", "canon-gate", "8", "9"}

# ⭐⭐ THE `/checkin` SPINE (W14.7, 2026-08-09) — deliberately TINY, and the reason is the finding.
# `/checkin` had NO coverage table. Its three tool-backed checks (`checkin_open`, `gauge_check`,
# `board_check`) fire every run because each returns an exit code; its ONE prose-only step — Step
# 3.58's blind-reader handoff proof — was skipped on 2026-08-08 and only a human asking "did the haiku
# agent run?" surfaced it. `system/sops/skill-building-sop-extract.md`: a model cannot report on its own
# compliance, and the Step 3.57 receipt asked for that verdict as a self-reported LINE.
# ⇒ This spine exists so a `/checkin` close that skipped the reader CANNOT render clean.
# ⛔ DO NOT GROW IT into a mirror of the /save spine. Every row here must be a step whose absence is
# a real failure; a long table trains the reader to skim it, which is the disease, not the cure.
MANDATORY_CHECKIN = [
    ("compact", "scratchpad archived BEFORE the diff (Step 1.8)", "always"),
    ("graduate", "§2 CURRENT STATE graduated", "always"),
    ("reader", "Step 3.58 blind-reader handoff proof", "always"),
]
IDS_CHECKIN = [m[0] for m in MANDATORY_CHECKIN]

# ⭐⭐ EVERY CHECKIN ROW IS `always` AND CARRIES A VERDICT. THAT IS THE WHOLE DESIGN (2026-08-09).
# ⛔ THE V1 MISTAKE, RECORDED SO IT IS NOT REBUILT: v1 made these rows CONDITIONAL and had CODE work out
# the condition — `_derive_reader` read the brief's mtime to guess "did real work happen this run", and
# two CLI flags (`--compaction-skipped`, `--session-close`) let the caller assert the rest. An
# adversarial audit (2026-08-09, 111k tokens) returned FIVE FALSE GREENS and **every one of them lived
# in that guessing**: a stale copy passed as `--brief` · the containing DIRECTORY passed as `--brief` ·
# a same-second mtime · omitting `--session-close` · asserting `--compaction-skipped` over a dirty pad.
# The two things it threw everything at and could NOT break — the closed verdict set and the `--ns`
# split — are both pure membership checks.
# ⇒ THE RULE THIS ENCODES: **"was this step owed?" is a JUDGMENT, so the MODEL answers it; code only
# checks the answer is on the list and that the box is not empty.** A timestamp cannot know whether a
# session did meaningful work, and a guess is precisely what an input can be shaped to fool.
# ⛔ Do NOT reintroduce a derivation here. If a row needs a condition, add a VERDICT for it.
READER_VERDICTS = {"CAN_PROCEED", "BLOCKED", "CONTRADICTION", "NOT_RUN", "NOT_OWED"}
STEP_VERDICTS = {"DONE", "NOT_OWED"}
CHECKIN_VERDICTS = {"reader": READER_VERDICTS, "compact": STEP_VERDICTS, "graduate": STEP_VERDICTS}

# Verdicts that mean THE STEP DID NOT HAPPEN AND SHOULD HAVE → rendered ✗ MISSED, never clean.
# ⛔ `NOT_RUN` is the no-outcome member; stamping it must not buy a pass, or the gate is satisfiable by
# admitting the failure it exists to catch.
VERDICT_MISSED = {"NOT_RUN"}
# Verdicts that mean THERE WAS NOTHING TO DO → ⊘, and NOT a false alarm.
VERDICT_NOT_OWED = {"NOT_OWED"}

# ⚠ HONEST BOUND ON THE `reader` ROW — stated, never quietly implied. The blind reader is a
# read-only subagent; it writes no file, so there is NO artifact to verify it against and the stamp
# is SELF-REPORTED (`~`, not `✓`). ⇒ This catches FORGETTING, which is the measured failure. It does
# NOT catch LYING, and it is not claimed to. What changed is the rung: skipping the step now means
# omitting a COMMAND whose absence renders `✗ MISSED` with a non-zero exit, instead of omitting a
# SENTENCE nobody could audit. ⛔ Do not upgrade this to `✓` unless the reader gains a real artifact.
NO_ARTIFACT_IDS_CHECKIN = {"reader"}

# ns → (spine, no-artifact set). `None`/"save" keeps the historical /save behaviour untouched.
SPINES = {
    "save": (MANDATORY, NO_ARTIFACT_IDS),
    "checkin": (MANDATORY_CHECKIN, NO_ARTIFACT_IDS_CHECKIN),
}


def _spine(ns=None):
    return SPINES.get(ns or "save", SPINES["save"])


# The block-header timestamp field, read from pad_archive.py's OWN append format:
# `<!-- section-archive :: section="<heading>" :: archive #N :: <ts> :: host=... :: prev=... ::
# hash=... -->`. ts is ISO-with-offset and has no embedded spaces, so `\S+` is safe and cannot
# swallow the next field. section="..." is matched non-greedy the same way pad_archive.py's own
# BLOCK_HDR_RE matches it, in case a heading ever legitimately contains a literal `"`.
# ⚖ ONE REGEX, NOT TWO (2026-08-11). `compact` and `graduate` used to read two different marker
# formats because they called two different tools. Those tools merged, so their formats did too.
_BLOCK_TS_RE = re.compile(
    r'<!--\s*section-archive\s*::\s*section="(?:.*?)"\s*::\s*archive\s*#\d+\s*::\s*(\S+)\s*::\s*host=')


# ⛔⛔ THE FUTURE BOUND (W11.7, 2026-08-08) — a MEASURED false green, not a theory.
# `audit_compaction.py` check 8 hand-wrote a pad-archive block dated +1 DAY with a hash matching the
# current pad, and `stamp compact` ACCEPTED it (rc 0). The freshness test only ever asked
# "is this block NEWER than my start?", which any future timestamp satisfies trivially.
# ⭐ WHY THAT MATTERS HERE SPECIFICALLY: this archive is written by TWO MACHINES into ONE file — the
# donor system's archive interleaved two hosts in one file, and this one can too. A
# clock-ahead machine can therefore mint a block that reads as proof THIS run archived the pad.
# ⚠ This risk was DECLINED on 2026-08-08 as "errs toward refusing, the safe direction." The
# measurement DISCONFIRMED that. Recorded rather than quietly corrected.
# TOLERANCE: 120s absorbs ordinary NTP drift on the writing machine while rejecting a block minted
# minutes-to-days ahead. A block genuinely written DURING this run is seconds old, never minutes.
_FUTURE_TOLERANCE_S = 120


def _future_bound_error(newest_epoch, label):
    """Non-None => the block is implausibly far in the future and must NOT count as this run's."""
    skew = newest_epoch - time.time()
    if skew > _FUTURE_TOLERANCE_S:
        return ("stamp %s refused: the newest archive block is dated %.0fs IN THE FUTURE "
                "(tolerance %ds). A block that cannot have been written by this run is not "
                "evidence this run archived anything — most likely a clock-ahead second machine "
                "writing into the same archive." % (label, skew, _FUTURE_TOLERANCE_S))
    return None


# ⚖ IMPORTED, NOT RE-TYPED (2026-08-11). This used to be a hand-copied duplicate of the archiver's
# slugify(), with a comment saying it MUST be kept identical and that a drift would make `graduate`
# refuse — or worse, silently check the wrong file — without the archiver itself ever changing. The
# justification was that reusing it meant "sys.path surgery". The two files now sit in the same
# directory, so the import is one line and the duplicate has no excuse left.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pad_archive as _pa  # noqa: E402


def _archive_file(brief: str, heading: str = "## 7. SCRATCHPAD") -> str:
    """The archive filename for a section — asked of the tool that creates it, never rebuilt."""
    return _pa.archive_path(brief, heading)


def _key() -> str:
    # ⚠ parens are load-bearing: `"cwd-%s" % x % 10**12` binds left-to-right, so the modulo lands on
    # the STRING and raises. Shipped broken 2026-07-28 and crashed on first real use — the selftest
    # exercised render()/reconcile() (pure logic) and never touched the I/O path, so it passed on a
    # tool that could not run. A selftest that skips the entry point proves the wrong thing.
    # ⛔ hashlib, NOT the built-in hash(): `str.__hash__` is RANDOMIZED PER PROCESS (PYTHONHASHSEED), so
    # the old fallback returned a DIFFERENT key on every invocation — `start`, `stamp` and `report` each
    # wrote a different file and `report` honestly answered "no ledger for this session". Found by the
    # 2026-08-09 adversarial audit. It failed CLOSED (rc 1, never a false green) and is latent in
    # practice because the harness always sets the session id — fixed anyway, because a key that is not
    # stable is not a key.
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID")
    if sid:
        return sid
    import hashlib
    return "cwd-" + hashlib.sha256(os.getcwd().encode("utf-8")).hexdigest()[:16]


# ⭐⭐ THE NAMESPACE (W14.7, 2026-08-09) — WHY IT EXISTS, because it looks like a nicety and is not.
# The ledger was keyed by SESSION ID alone, so `/save` and `/checkin` running in one window shared ONE
# file — and `cmd_start` REPLACES the dict, wiping `stamps` outright. That is the whole of `W11.10`:
# `/checkin` could never call `start` without destroying `/save`'s stamps, so it called `stamp` alone,
# so every `/checkin` stamp refused ("no ledger started"), so `/checkin` had no coverage table at all,
# so its one prose-only step (the blind reader) had nothing that could report it missing.
# ⇒ A namespace gives each skill its OWN file. The two never collide, `start` is safe in both, and
# `W11.10` DISSOLVES rather than needing a ruling on which skill owns the ledger — neither does.
# ⚠ BACKWARD-COMPATIBLE BY CONSTRUCTION: ns=None reproduces the old `save-<key>.json` path byte for
# byte, so ledgers already on disk from a `/save` mid-flight keep resolving. Do not "tidy" that away.
def _path(key=None, ns=None) -> Path:
    stem = "save" if not ns else "save-%s" % ns
    return RUN_DIR / ("%s-%s.json" % (stem, key or _key()))


def _load(key=None, ns=None) -> dict:
    p = _path(key, ns)
    if not p.exists():
        return {"started": None, "stamps": {}}
    try:
        return json.loads(p.read_text())
    except Exception:
        return {"started": None, "stamps": {}}


def _save(d: dict, key=None, ns=None) -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    _path(key, ns).write_text(json.dumps(d, indent=1))


def cmd_start(a) -> int:
    ns = getattr(a, "ns", None)
    # ⛔⛔ IDEMPOTENT — AND THIS IS THE FIX FOR THE WORST BYPASS THE AUDIT FOUND (2026-08-09).
    # `start` used to unconditionally write `{"started": now, "stamps": {}}`. So a SECOND call — after
    # the brief had been edited and with the reader never stamped — wiped the stamps AND pushed
    # `started` forward past the edit, turning a genuine miss into a clean rc 0 report.
    # ⭐ It is not an attack. "Call start again to be safe" is exactly what a careful session does, and
    # `/checkin` Step 0 instructs an arm on EVERY run. Same shape as the FIRST-ARM-WINS fix that
    # `pad_sha_at_arm` already needed for precisely the same reason (2026-08-08).
    d = _load(ns=ns)
    if d.get("started"):
        print("%s step-ledger already open for this session (started, stamps preserved) — "
              "not reset" % (ns or "save"))
        return 0
    _save({"started": int(time.time()), "stamps": {}}, ns=ns)
    print("%s step-ledger started for this session" % (ns or "save"))
    return 0


def _verify_compact(brief, started) -> int:
    """CAUSED, not GENERATED (architecture-library.md §7): refuse the `compact` stamp unless (1) the
    archive chain is mechanically intact AND (2) the newest block was written AFTER this ledger
    run's `started` — proving THIS run archived, not that it's inheriting a stale block from a
    prior session. Either failure -> non-zero, no stamp written."""
    if not brief:
        print("stamp compact refused: brief path required — usage: `stamp compact \"<brief>\"`",
              file=sys.stderr)
        return 2
    if started is None:
        print("stamp compact refused: no ledger 'started' for this session — run `start` first",
              file=sys.stderr)
        return 2

    pad_archive = str(Path(__file__).resolve().parent / "pad_archive.py")
    proc = subprocess.run([sys.executable, pad_archive, "verify", brief],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        print("stamp compact refused: `pad_archive.py verify %s` exited %d (chain not intact)\n%s"
              % (brief, proc.returncode, (proc.stderr or proc.stdout).strip()), file=sys.stderr)
        return 2

    archive_path = _archive_file(brief)
    try:
        txt = Path(archive_path).read_text(encoding="utf-8")
    except OSError as e:
        print("stamp compact refused: cannot read archive %r: %s" % (archive_path, e),
              file=sys.stderr)
        return 2
    stamps_found = _BLOCK_TS_RE.findall(txt)
    if not stamps_found:
        print("stamp compact refused: no parseable pad-archive block header in %r" % archive_path,
              file=sys.stderr)
        return 2
    newest_ts_str = stamps_found[-1]
    try:
        newest_epoch = datetime.datetime.fromisoformat(newest_ts_str).timestamp()
    except ValueError as e:
        print("stamp compact refused: could not parse block timestamp %r: %s"
              % (newest_ts_str, e), file=sys.stderr)
        return 2
    # `<` not `<=`: the archive legitimately lands in the SAME SECOND as `start` on a fast run,
    # and a same-second block cannot be a stale inheritance — a prior session's block is seconds
    # to days older. Caught 2026-08-03 on this check's FIRST real use: the archive had just run
    # (fresh RECEIPT, compaction=20) and the stamp still refused, because epoch == epoch.
    # Fail-closed is right; off-by-one strict is not. The guard still rejects any block written
    # BEFORE this run began, which is the whole threat model.
    _fb = _future_bound_error(newest_epoch, "compact/graduate")
    if _fb:
        print(_fb, file=sys.stderr)
        return 2
    if newest_epoch < started:
        print(
            "stamp compact refused: newest archive block (%s, epoch %d) is NOT after this "
            "ledger run's start (epoch %d) — this looks like a stale block inherited from a "
            "prior session, not evidence THIS run archived the pad." %
            (newest_ts_str, int(newest_epoch), started), file=sys.stderr)
        return 2
    return 0


def _verify_graduate(brief, started, heading=None) -> int:
    """CAUSED, not GENERATED — mirrors _verify_compact()'s discipline exactly: refuse the
    `graduate` stamp unless (1) pad_archive.py's chain for the §2 CURRENT STATE section is
    mechanically intact AND (2) the newest block was written AFTER this ledger run's `started` —
    proving THIS run archived §2 before graduating it, not that it's inheriting a stale block
    from a prior session. Either failure -> non-zero, no stamp written.

    ⚠ UNLIKE `compact` (pad_archive.py always archives one fixed section, "## 7. SCRATCHPAD", so
    its archive filename is a fixed constant), pad_archive.py is GENERALISED to any named
    section — its archive filename is built from the EXACT heading line that was archived
    (`archive_path()` = `<brief>.<slugify(heading)>-archive.md`, see pad_archive.py's own
    docstring: "the caller decides which section it is; this tool only compares strings"). So
    this check cannot hardcode a filename the way _verify_compact does — it needs the SAME exact
    heading the graduate step passed to `pad_archive.py archive --heading "..."`, or it would
    either refuse a real archive (wrong file, false negative) or silently check nothing at all
    (worse: false positive by omission). Guessing that heading here would be exactly the
    heading-guessing this codebase's tools are built to refuse — so `--heading` is REQUIRED for
    `stamp graduate`, not optional-with-a-fallback."""
    if not brief:
        print(
            "stamp graduate refused: brief path required — usage: `stamp graduate \"<abs brief>\" "
            "--heading \"<exact CURRENT STATE heading line>\"`",
            file=sys.stderr,
        )
        return 2
    if started is None:
        print("stamp graduate refused: no ledger 'started' for this session — run `start` first",
              file=sys.stderr)
        return 2
    if not heading:
        print(
            "stamp graduate refused: --heading required — pad_archive.py names its archive "
            "file after the EXACT heading line that was archived, so this check cannot know which "
            "archive file proves §2 was archived without it. Pass the same --heading you gave to "
            "`pad_archive.py archive`.",
            file=sys.stderr,
        )
        return 2

    archiver = str(Path(__file__).resolve().parent / "pad_archive.py")
    proc = subprocess.run(
        [sys.executable, archiver, "verify", brief, "--heading", heading],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        print(
            "stamp graduate refused: `pad_archive.py verify %s --heading %r` exited %d "
            "(chain not intact)\n%s"
            % (brief, heading, proc.returncode, (proc.stderr or proc.stdout).strip()),
            file=sys.stderr,
        )
        return 2

    archive_path = _archive_file(brief, heading)
    try:
        txt = Path(archive_path).read_text(encoding="utf-8")
    except OSError as e:
        print("stamp graduate refused: cannot read archive %r: %s" % (archive_path, e),
              file=sys.stderr)
        return 2
    stamps_found = _BLOCK_TS_RE.findall(txt)
    if not stamps_found:
        print("stamp graduate refused: no parseable section-archive block header in %r"
              % archive_path, file=sys.stderr)
        return 2
    newest_ts_str = stamps_found[-1]
    try:
        newest_epoch = datetime.datetime.fromisoformat(newest_ts_str).timestamp()
    except ValueError as e:
        print("stamp graduate refused: could not parse block timestamp %r: %s"
              % (newest_ts_str, e), file=sys.stderr)
        return 2
    # `<` not `<=` — same reasoning _verify_compact carries: a same-second archive cannot be a
    # stale inheritance (a prior session's block is seconds to days older), and fail-closed-strict
    # (`<=`) would wrongly refuse a fresh archive that lands in the same second as `start`.
    _fb = _future_bound_error(newest_epoch, "compact/graduate")
    if _fb:
        print(_fb, file=sys.stderr)
        return 2
    if newest_epoch < started:
        print(
            "stamp graduate refused: newest archive block (%s, epoch %d) is NOT after this "
            "ledger run's start (epoch %d) — this looks like a stale block inherited from a "
            "prior session, not evidence THIS run archived §2 CURRENT STATE." %
            (newest_ts_str, int(newest_epoch), started), file=sys.stderr)
        return 2
    return 0


def cmd_stamp(a) -> int:
    ns = getattr(a, "ns", None)
    spine, _ = _spine(ns)
    ids = [m[0] for m in spine]
    if a.step not in ids:
        print("unknown step %r for ns=%s — known: %s" % (a.step, ns or "save", ", ".join(ids)),
              file=sys.stderr)
        return 2
    if ns == "checkin":
        return cmd_stamp_checkin(a, ns)
    d = _load(ns=ns)
    if a.step == "compact":
        rc = _verify_compact(a.brief, d.get("started"))
        if rc != 0:
            return rc
    elif a.step == "graduate":
        rc = _verify_graduate(a.brief, d.get("started"), a.heading)
        if rc != 0:
            return rc
    d.setdefault("stamps", {})[a.step] = int(time.time())
    _save(d, ns=ns)
    print("stamped %s" % a.step)
    return 0


def cmd_stamp_checkin(a, ns) -> int:
    """The ns=checkin stamp path. EVERY row carries a verdict from a CLOSED set — that is the seam:
    code hands the model a bounded set of outcomes including a NO-OUTCOME member, and checks
    membership on the way in. It never infers which outcome is correct; that is the model's half."""
    allowed = CHECKIN_VERDICTS.get(a.step)
    v = (getattr(a, "verdict", None) or "").strip().upper()
    if v not in allowed:
        print("stamp %s --ns checkin requires --verdict, one of: %s\n"
              "  NOT_OWED = this step was not required this run (⊘, not a miss).\n"
              "  NOT_RUN  = it WAS required and did not happen (✗ MISSED — admitting it is not doing it)."
              % (a.step, ", ".join(sorted(allowed))), file=sys.stderr)
        return 2
    d = _load(ns=ns)
    # ⭐ A `DONE` claim on compact/graduate still has to EARN it against a real artifact — that check is
    # the one thing code can genuinely prove here, and it stays. NOT_OWED skips it because there is no
    # archive to point at when nothing was archived.
    if v == "DONE" and a.step == "compact":
        rc = _verify_compact(a.brief, d.get("started"))
        if rc != 0:
            return rc
    elif v == "DONE" and a.step == "graduate":
        rc = _verify_graduate(a.brief, d.get("started"), a.heading)
        if rc != 0:
            return rc
    d.setdefault("stamps", {})[a.step] = int(time.time())
    d.setdefault("verdicts", {})[a.step] = v
    _save(d, ns=ns)
    print("stamped %s (%s)" % (a.step, v))
    return 0


# ── APPLICABILITY — a CLOSED SET, and the reason this section exists (W11.1b, 2026-08-08) ──────
# ROOT CAUSE it fixes: applicability used to be a plain bool supplied by the CALLER, so a session
# that simply OMITTED `--pad-had-content` got "– n/a this run" — silence reading as fine. Measured
# 2026-08-08: a /save on project-system wrote the brief at 13:28, never stamped `compact`, and
# reported a clean table while the pad held 52,323 chars, 7 days stale.
# ⛔ THE RULE THIS ENCODES: a tool may not accept, as input, a claim about the world it could read
# for itself. Where a claim CAN be derived (compact ← the pad on disk) it is DERIVED. Where it
# genuinely cannot (was this a session close? were there findings?) the caller's SILENCE now maps
# to UNKNOWN, never to N/A — because "nobody told me" and "I checked and it was fine" are not the
# same fact, and only one of them is safe to render as clean.
APPLIES = "applies"          # required this run → an absent stamp is ✗ MISSED
NOT_APPLICABLE = "n/a"       # PROVEN not required, from an artifact → –
NOTHING_TO_DO = "clean"      # applicable-looking; the artifact proves there was nothing to do → ⊘
UNKNOWN = "unknown"          # nobody could tell → ?   ⛔ NEVER collapse this into NOT_APPLICABLE


def _newest_pad_block_epoch(brief):
    """Epoch of the newest pad-archive block, or None if unreadable/absent. Read-only."""
    try:
        txt = Path(_archive_file(brief)).read_text(encoding="utf-8")
    except OSError:
        return None
    found = _BLOCK_TS_RE.findall(txt)
    if not found:
        return None
    try:
        return datetime.datetime.fromisoformat(found[-1]).timestamp()
    except ValueError:
        return None


def _derive_compact(brief, started):
    """Applicability of `compact`, READ OFF THE PAD — never asserted by the caller.
    Delegates the verdict to pad_archive.py's `state` verb so there is exactly ONE definition of
    "is the pad dirty" in the system (its exit code IS the answer; we never re-read the pad here)."""
    if not brief:
        return UNKNOWN                      # no path given → cannot tell. NOT the same as n/a.
    tool = Path(__file__).with_name("pad_archive.py")
    try:
        rc = subprocess.run([sys.executable, str(tool), "state", brief],
                            capture_output=True, text=True, timeout=30).returncode
    except Exception:
        return UNKNOWN                      # tool missing/crashed → unevaluated, never clean
    if rc == 2:                             # PAD-DIRTY  → a compaction was owed
        return APPLIES
    if rc == 3:                             # PAD-ARCHIVED-UNCLEARED → archived, clear still owed
        return APPLIES
    if rc == 0:                             # PAD-EMPTY → nothing to do. But WHY was it empty?
        newest = _newest_pad_block_epoch(brief)
        # A block written AFTER this run began means someone (this run, or a concurrent window —
        # the ledger is session-scoped and cannot see across windows) already did it. That is a
        # clean skip WITH EVIDENCE, not a step that never applied.
        # Same future bound as the stamp verifiers — a block nobody could have written this run
        # must not turn an empty pad into "someone already compacted it, all clean."
        if newest is not None and newest >= started and not _future_bound_error(newest, "derive"):
            return NOTHING_TO_DO
        return NOT_APPLICABLE               # pad was empty all along — genuinely n/a
    return UNKNOWN                          # rc 4 CANNOT-READ (FUSE EDEADLK) → never clean


def render(d: dict, conditions=None, ns=None) -> tuple:
    """Return (text, missed_ids). `conditions` maps a conditional step id → one of the four
    applicability values above. A BARE bool is still accepted for backward compatibility:
    True → APPLIES, False → NOT_APPLICABLE. `ns` selects the spine (None/"save" = the /save spine)."""
    conditions = conditions or {}
    stamps = d.get("stamps", {})
    verdicts = d.get("verdicts", {})
    spine, no_artifact = _spine(ns)
    rows, missed, unknown = [], [], []
    for sid, label, when in spine:
        if sid in stamps:
            # ⛔ A `reader` stamp carrying the NO-OUTCOME verdict is NOT evidence the step ran — it is
            # evidence it did not. Render it as MISSED, never as a tick. Without this branch the gate
            # is satisfiable by stamping "NOT_RUN", i.e. by admitting the failure in the box that is
            # supposed to catch it. (Same family as the `?`-is-not-a-softer-`0` rule below.)
            if verdicts.get(sid) in VERDICT_MISSED:
                rows.append("  ✗ %-11s %s  ← %s (a no-outcome verdict is never clean)"
                            % (sid, label, verdicts[sid]))
                missed.append(sid)
                continue
            if verdicts.get(sid) in VERDICT_NOT_OWED:
                rows.append("  ⊘ %-11s %s  (NOT_OWED — not required this run)" % (sid, label))
                continue
            suffix = "  [%s]" % verdicts[sid] if verdicts.get(sid) else ""
            if sid in no_artifact:
                rows.append("  ~ %-11s %s%s  (self-reported, unverified)" % (sid, label, suffix))
            else:
                rows.append("  ✓ %-11s %s%s" % (sid, label, suffix))
            continue
        if when == "always":
            rows.append("  ✗ %-11s %s  ← MISSED" % (sid, label))
            missed.append(sid)
            continue
        st = conditions.get(sid, UNKNOWN)
        if st is True:
            st = APPLIES
        elif st is False:
            st = NOT_APPLICABLE
        if st == APPLIES:
            rows.append("  ✗ %-11s %s  ← MISSED" % (sid, label))
            missed.append(sid)
        elif st == NOT_APPLICABLE:
            rows.append("  – %-11s %s  (n/a this run — proven, not assumed)" % (sid, label))
        elif st == NOTHING_TO_DO:
            # ⚠ "nothing to do", NOT "already done" — the two are different facts and this row is read
            # by someone deciding whether a step was skipped. The old wording was true for /save's
            # case (another window compacted) and FALSE for /checkin's (no edits landed, so the
            # handoff proof was never owed). One string, so it has to be true of both.
            rows.append("  ⊘ %-11s %s  (SKIPPED-CLEAN — nothing to do; artifact proves it)"
                        % (sid, label))
        else:
            rows.append("  ? %-11s %s  ← APPLICABILITY UNKNOWN (not proven n/a)" % (sid, label))
            unknown.append(sid)
    head = "STEP COVERAGE — what this run actually executed (from the ledger, not from memory)"
    if missed:
        tail = ("  ⚠ %d mandatory step(s) MISSED. This is the logged skipped-step failure that "
                "F3.2's reopen-condition fires on." % len(missed))
        if unknown:
            tail += "\n  ? %d step(s) UNKNOWN — applicability could not be determined." % len(unknown)
    elif unknown:
        # ⛔ THE ALL-CLEAR LINE IS WITHHELD. Printing "every mandatory step stamped" while an
        # applicability is unknown is exactly how a skipped compaction read as a clean run.
        tail = ("  ? %d step(s) UNKNOWN — applicability could not be determined, so this run is "
                "NOT reported clean. Pass --brief <path> so the ledger can read instead of ask."
                % len(unknown))
    else:
        tail = "  ✓ every mandatory step stamped."
    return ("\n".join([head, "-" * 72] + rows + ["-" * 72, tail]), missed)


def cmd_report(a) -> int:
    ns = getattr(a, "ns", None)
    if ns == "checkin":
        return _report_checkin(a)
    d = _load()
    if d.get("started") is None:
        print("STEP COVERAGE — UNKNOWN: no ledger for this session.\n"
              "  A /save run that never called `start` cannot prove which steps ran. Report UNKNOWN;\n"
              "  do NOT claim coverage. (An absent ledger is itself a skipped-step signal.)")
        return 1
    # ⭐ compact is DERIVED FROM THE PAD, never from a flag — the root-cause fix.
    # ⚠ HONEST BOUND, stated rather than quietly skipped: only `compact` is derivable from an
    # artifact. Whether a run was a session close, had findings, or held a canon candidate are
    # SESSION facts with no file to read. For those three the caller may still assert APPLIES;
    # what changed is that SILENCE now yields UNKNOWN (a loud `?` that withholds the all-clear)
    # instead of N/A. Absence of a claim is no longer evidence of absence.
    cond = {
        "SC-1": APPLIES if a.session_close else UNKNOWN,
        "tier": APPLIES if a.session_close else UNKNOWN,
        "canon-gate": APPLIES if a.canon else UNKNOWN,
        "7d": APPLIES if a.findings else UNKNOWN,
        "8": APPLIES if a.session_close else UNKNOWN,
        "graduate": APPLIES if a.session_close else UNKNOWN,
        "compact": _derive_compact(a.brief, d.get("started") or 0),
    }
    text, missed = render(d, cond)
    print(text)
    # CLOSED EXIT SET — 0 clean · 1 a mandatory step MISSED · 2 applicability UNKNOWN.
    # ⛔ 2 is NOT a softer 0. "I could not tell" must not be machine-readable as "fine" — that
    # equivalence IS the bug this whole change removes, and leaving it in the exit code would
    # reintroduce it one layer down where no human is reading the table.
    if missed:
        return 1
    # ⚠ Only an UNSTAMPED step's unknown applicability matters. A step that WAS stamped is proven
    # to have run, so nobody needs to know whether it was required — counting it here made a
    # fully-clean run exit 2, which is a false alarm and the fastest way to teach a reader to
    # ignore the code. (Caught on this change's own first run, 2026-08-08.)
    stamped = d.get("stamps", {})
    if any(v == UNKNOWN for k, v in cond.items() if k not in stamped):
        return 2
    return 0


def _report_checkin(a) -> int:
    """The `/checkin` coverage table (W14.7, 2026-08-09). Same discipline as the /save report:
    a MISSED mandatory step exits 1, an UNKNOWN applicability exits 2, and 2 is NOT a softer 0."""
    d = _load(ns="checkin")
    if d.get("started") is None:
        print("STEP COVERAGE (/checkin) — UNKNOWN: no ledger for this session.\n"
              "  A /checkin that never called `start --ns checkin` cannot prove which steps ran.\n"
              "  Report UNKNOWN; do NOT claim coverage. An absent ledger is itself a skipped-step\n"
              "  signal — and the blind-reader proof is exactly the step that goes missing silently.")
        return 1
    # ⛔ NO CONDITIONS, NO DERIVATIONS, NO FLAGS — and their absence IS the fix (2026-08-09).
    # Every row is `always`: it is either stamped with a verdict the model gave, or it is MISSING.
    # There is nothing here for a caller to shape, which is why the five audited bypasses have no
    # surface left to land on — `--brief`, `--session-close` and `--compaction-skipped` no longer
    # influence this report at all. `--brief` survives ONLY as the artifact check inside `stamp DONE`.
    text, missed = render(d, {}, ns="checkin")
    print(text)
    return 1 if missed else 0


def cmd_selftest(_a) -> int:
    fails = []
    # a complete run
    d = {"started": 1, "stamps": {s: 1 for s in IDS}}
    _t, missed = render(d, {"canon-gate": True, "7d": True, "8": True})
    if missed:
        fails.append("complete run should have no missed, got %s" % missed)
    print("  [1] every step stamped        -> missed=%s" % missed)

    # THE CASE THAT MATTERS: the journal was skipped on a run that had findings.
    d = {"started": 1, "stamps": {s: 1 for s in IDS if s != "7d"}}
    _t, missed = render(d, {"7d": True})
    if missed != ["7d"]:
        fails.append("skipped journal must be MISSED, got %s" % missed)
    print("  [2] journal skipped (findings)-> missed=%s  <- the trigger F3.2 rests on" % missed)

    # the same skip when the condition did NOT arise is N/A, not a false alarm
    d = {"started": 1, "stamps": {s: 1 for s in IDS if s != "7d"}}
    _t, missed = render(d, {"7d": False})
    if missed:
        fails.append("non-applicable step must not be MISSED, got %s" % missed)
    print("  [3] no findings, journal n/a  -> missed=%s  (no false alarm)" % missed)

    # a run that stamped nothing must not read as clean — DERIVED, not hand-typed: with an empty
    # conditions dict every conditional row renders `? UNKNOWN` (not MISSED), so `missed` is exactly
    # the rows MANDATORY marks "always". A hardcoded expectation here is the identical defect this
    # project keeps re-fixing — "a safety check whose coverage is a hand-typed list can only ever
    # report 'everything on the list was fine'" — so if an unconditional row is ever added or
    # removed, this count must move with it automatically, never require a matching hand-edit.
    _t, missed = render({"started": 1, "stamps": {}}, {})
    expected_always = sum(1 for _, _, when in MANDATORY if when == "always")
    if len(missed) != expected_always:
        fails.append("empty run should flag exactly the %d 'always' step(s), got %s"
                      % (expected_always, missed))
    print("  [4] nothing stamped           -> missed=%d step(s) (== %d 'always' rows in MANDATORY)"
          % (len(missed), expected_always))

    # ── W11.1b: the four applicability markers must be REACHABLE and DISTINCT ──────────────────
    # ⛔ "A check never seen to fail is not a check." Each case below asserts the RENDERED marker,
    # not just the missed list — because the marker is the half a human actually reads, and the
    # 2026-08-08 failure was a WRONG MARKER (– where ✗ belonged) on a correct missed list.
    base = {"started": 1, "stamps": {s: 1 for s in IDS if s != "compact"}}

    t, missed = render(base, {"compact": APPLIES})
    ok = ("✗ compact" in t.replace("compact     ", "compact")) or "MISSED" in t
    if "compact" not in missed:
        fails.append("APPLIES + no stamp must be MISSED, got %s" % missed)
    print("  [5] compact APPLIES, unstamped -> ✗ MISSED   (the 13:28 regression case)")

    t, missed = render(base, {"compact": NOT_APPLICABLE})
    if missed or "–" not in t:
        fails.append("NOT_APPLICABLE must render – and not be MISSED, got %s" % missed)
    print("  [6] compact proven n/a         -> –  (no false alarm)")

    t, missed = render(base, {"compact": NOTHING_TO_DO})
    if missed or "⊘" not in t:
        fails.append("NOTHING_TO_DO must render ⊘ and not be MISSED, got %s" % missed)
    if "SKIPPED-CLEAN" not in t:
        fails.append("⊘ row must name SKIPPED-CLEAN so a human can tell it from n/a")
    print("  [7] compact already done       -> ⊘ SKIPPED-CLEAN (another window did it)")

    t, missed = render(base, {"compact": UNKNOWN})
    if "?" not in t or "UNKNOWN" not in t:
        fails.append("UNKNOWN must render ? and say UNKNOWN")
    if "every mandatory step stamped" in t:
        fails.append("⛔ ALL-CLEAR PRINTED WITH AN UNKNOWN — this is the exact 13:28 failure")
    print("  [8] compact UNKNOWN            -> ?  and the ALL-CLEAR line is WITHHELD")

    # the four markers must not be the same string
    marks = set()
    for st in (APPLIES, NOT_APPLICABLE, NOTHING_TO_DO, UNKNOWN):
        row = [l for l in render(base, {"compact": st})[0].splitlines() if " compact " in l]
        marks.add(row[0].strip()[0] if row else "?")
    if len(marks) != 4:
        fails.append("the four applicability markers must be DISTINCT, got %s" % sorted(marks))
    print("  [9] four markers distinct      -> %s" % " ".join(sorted(marks)))

    # ENTRY-POINT COVERAGE — this file shipped broken on 2026-07-28 because the selftest
    # exercised pure logic and never touched the CLI path (see _key()'s comment).
    if _derive_compact(None, 0) != UNKNOWN:
        fails.append("_derive_compact with no brief must be UNKNOWN, never n/a")
    if _derive_compact("/tmp/definitely-not-a-brief-xyz.md", 0) != UNKNOWN:
        fails.append("_derive_compact on an unreadable brief must be UNKNOWN (CANNOT-READ), never n/a")
    print("  [10] derive: no brief / unreadable -> UNKNOWN (entry point exercised)")

    # ── W14.7 (2026-08-09, v2 after the adversarial audit): the /checkin spine ────────────────
    # ⛔ Every check below was proven able to FAIL before it was kept — a check nobody has watched
    # fail is a check nobody has tested (`33a1671`'s lesson, and the house rule: a helper's own
    # certification is not evidence). NOTE the shape change from v1: `render` is called with an
    # EMPTY conditions dict, because the /checkin spine has no conditions left to supply.
    ck = {"started": 1, "stamps": {"compact": 1, "graduate": 1, "reader": 1},
          "verdicts": {"compact": "DONE", "graduate": "DONE", "reader": "CAN_PROCEED"}}
    t, missed = render(ck, {}, ns="checkin")
    if missed or "CAN_PROCEED" not in t:
        fails.append("checkin complete run must be clean and show the verdict, got %s" % missed)
    print("  [11] /checkin all stamped      -> missed=%s  verdict rendered" % missed)

    # ⭐⭐ THE 2026-08-08 FAILURE, REPLAYED: the blind reader was never run.
    ck = {"started": 1, "stamps": {"compact": 1, "graduate": 1},
          "verdicts": {"compact": "DONE", "graduate": "DONE"}}
    t, missed = render(ck, {}, ns="checkin")
    if missed != ["reader"] or "every mandatory step stamped" in t:
        fails.append("skipped blind reader must be MISSED and withhold the all-clear, got %s" % missed)
    print("  [12] reader never stamped      -> missed=%s  <- THE W14.7 case" % missed)

    # THE LOOPHOLE: stamping the no-outcome verdict must NOT buy a clean table.
    ck = {"started": 1, "stamps": {"compact": 1, "graduate": 1, "reader": 1},
          "verdicts": {"compact": "DONE", "graduate": "DONE", "reader": "NOT_RUN"}}
    t, missed = render(ck, {}, ns="checkin")
    if missed != ["reader"] or "NOT_RUN" not in t:
        fails.append("a NOT_RUN verdict must render MISSED, got %s" % missed)
    print("  [13] reader stamped NOT_RUN    -> missed=%s  (admitting it is not doing it)" % missed)

    # NOT_OWED is the model saying "this step was not required this run" -> ⊘, not a false alarm.
    ck = {"started": 1, "stamps": {"compact": 1, "graduate": 1, "reader": 1},
          "verdicts": {"compact": "NOT_OWED", "graduate": "NOT_OWED", "reader": "NOT_OWED"}}
    t, missed = render(ck, {}, ns="checkin")
    if missed or "NOT_OWED" not in t:
        fails.append("NOT_OWED must render clean, got %s" % missed)
    print("  [14] all NOT_OWED              -> ⊘ clean (a pickup run can still exit 0)")

    # ⛔ THE AUDIT'S BYPASS #2/#3 CANNOT BE EXPRESSED ANY MORE: `render` for ns=checkin ignores
    # conditions entirely, so no caller-supplied value can turn a missing reader into a clean row.
    ck = {"started": 1, "stamps": {"compact": 1, "graduate": 1},
          "verdicts": {"compact": "DONE", "graduate": "DONE"}}
    for hostile in ({"reader": NOTHING_TO_DO}, {"reader": NOT_APPLICABLE}, {"reader": UNKNOWN}):
        _t, m = render(ck, hostile, ns="checkin")
        if m != ["reader"]:
            fails.append("a caller-supplied condition changed the reader row: %s -> %s" % (hostile, m))
    print("  [15] hostile conditions        -> reader STILL missed (no derivation surface left)")

    # ⭐ THE NAMESPACE, which is what dissolves W11.10: `start --ns checkin` must not touch /save's
    # stamps. Proven on the real filesystem, not in the pure-logic layer — that omission is exactly
    # how `_key()` shipped broken on 2026-07-28.
    import types
    # ⛔ HERMETIC — clear both first. The v1 version of this check silently ran against whatever this
    # window had left on disk and printed "already open", so it was asserting on state it did not set.
    # A test that reads leftover state is not testing the thing it names.
    for _p in (_path(), _path(ns="checkin")):
        try:
            _p.unlink()
        except OSError:
            pass
    _save({"started": 1, "stamps": {"7d": 1}})                      # a /save ledger, mid-flight
    cmd_start(types.SimpleNamespace(ns="checkin"))                  # /checkin starts its own
    if _load().get("stamps", {}).get("7d") != 1:
        fails.append("⛔ `start --ns checkin` WIPED the /save ledger — W11.10 is not dissolved")
    if _load(ns="checkin").get("stamps"):
        fails.append("a fresh checkin ledger must start with no stamps")
    print("  [16] start --ns checkin        -> /save's stamps SURVIVE (W11.10 dissolved)")

    # ⭐⭐ THE AUDIT'S WORST BYPASS (#1), AS A TEST: a SECOND `start` must not wipe a real stamp.
    # v1's `start` rewrote `{"started": now, "stamps": {}}` unconditionally, so calling it again after
    # the work turned a genuine miss into rc 0. This is the regression test for that.
    _save({"started": 1, "stamps": {"reader": 1}, "verdicts": {"reader": "CAN_PROCEED"}}, ns="checkin")
    cmd_start(types.SimpleNamespace(ns="checkin"))                  # the "call it again to be safe" case
    d2 = _load(ns="checkin")
    if d2.get("stamps", {}).get("reader") != 1 or d2.get("started") != 1:
        fails.append("⛔ a SECOND `start` wiped stamps/started — audit bypass #1 is BACK")
    print("  [17] start called twice        -> stamps + started PRESERVED (bypass #1 dead)")
    for p in (_path(), _path(ns="checkin")):
        try:
            p.unlink()
        except OSError:
            pass

    if fails:
        for f in fails:
            print("  FAIL: " + f, file=sys.stderr)
        return 1
    print("\n✓ PASS — a skipped mandatory step is VISIBLE, a non-applicable one is not a false alarm,\n"
          "  and an UNKNOWN applicability can never be rendered as a clean run.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    # ⭐ --ns picks the SPINE and the ledger FILE. Omit it and everything behaves exactly as it did
    # before W14.7 (the /save spine, the historical `save-<key>.json` path) — the flag only ever adds.
    st = sub.add_parser("start")
    st.add_argument("--ns", default=None, choices=sorted(SPINES), help="which skill's ledger")
    s = sub.add_parser("stamp")
    s.add_argument("step")
    s.add_argument("--ns", default=None, choices=sorted(SPINES), help="which skill's ledger")
    s.add_argument("--verdict", default=None,
                   help="required for `stamp reader` — one of %s. NOT_RUN is the no-outcome "
                        "member and renders ✗ MISSED, never clean." % ", ".join(sorted(READER_VERDICTS)))
    s.add_argument("brief", nargs="?", default=None,
                   help="required for `stamp compact`/`stamp graduate` — the brief path "
                        "pad_archive.py was run against")
    s.add_argument("--heading", default=None,
                   help="required for `stamp graduate` — the EXACT §2 CURRENT STATE heading "
                        "line passed to `pad_archive.py archive --heading`")
    r = sub.add_parser("report")
    r.add_argument("--ns", default=None, choices=sorted(SPINES), help="which skill's ledger")
    r.add_argument("--canon", action="store_true", help="a canon candidate was in the batch")
    r.add_argument("--findings", action="store_true", help="the session had real findings")
    r.add_argument("--session-close", action="store_true", help="session-close mode")
    r.add_argument("--brief", default=None,
                   help="path to the active project brief. REPLACES the removed --pad-had-content "
                        "flag: `compact` applicability is now READ off the pad via pad_archive.py "
                        "state, never asserted. Omit it and compact reports ? UNKNOWN, never n/a.")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return cmd_selftest(a)
    return {"start": cmd_start, "stamp": cmd_stamp, "report": cmd_report}.get(
        a.cmd, lambda _x: (ap.print_help(), 2)[1])(a)


if __name__ == "__main__":
    sys.exit(main())

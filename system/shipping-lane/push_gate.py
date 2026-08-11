#!/usr/bin/env python3
"""push_gate — the shipping lane's LAST gate, standing between a staging tree and
`git push`.  [Shipping Lane · T9.4]

WHEN: after `scrub.py` has produced a staging tree, immediately before that tree is
      pushed (or copied over) to the public repo. This is the final checkpoint -- a miss
      here is PERMANENT, because public git history cannot be quietly un-published.

WHAT: walks the ENTIRE staging tree -- every file actually present on disk, never a
      manifest -- and re-runs the REFUSE rules over all of it. `scrub.py` only ever
      touched the files its manifest named; this file's entire reason to exist is to
      catch the file the manifest never mentioned (an editor swap file, a build
      artifact, a second copy dropped in by hand).

THE GATE IS ASYMMETRIC BY RULING -- BY DESIGN, NOT AN OVERSIGHT:
  - ANY unresolved REFUSE hit (identity or secret)  -> exit 1, NO receipt, NO push.
  - A surviving REWRITE hit (a leftover old-brand string) -> reported LOUDLY, does NOT
    block. A gate that blocks on a typo is a gate that gets waved through by habit, and
    then it is not there for the leak that matters. Personal data always blocks;
    branding never does.
  - Clean (no unresolved refuse hit, nothing unreadable/binary anywhere in the tree)
    -> a receipt is written. Nothing may push without that receipt.

WHY REFUSE HITS SKIP THE "TO" SUBSTITUTION scrub.py APPLIES: this file never rewrites
      anything -- it only DETECTS. By the time a tree reaches push_gate it is supposed to
      already be scrubbed; an unresolved refuse hit here means scrub.py's substitution
      either never ran on this file (the manifest miss this gate exists to catch) or an
      auto-resolvable refuse rule ("to") still left a residue scrub.py did not expect.
      Either way the right answer is the same: block, do not try to fix it here.

VERDICT AUTHORITY, mirroring scrub.py's own contract with the sibling part: for the
      REFUSE round, `forbidden_content.py` is called as a subprocess PER FILE and its
      exit code is treated as authoritative for that file, on top of this file's own
      `re.finditer` scan (needed anyway for the human-readable evidence -- line numbers,
      matched text -- which the engine's exit code alone cannot give). The two are
      combined with OR: EITHER one reporting a hit is enough to refuse the file. This is
      more paranoid than scrub.py's cross-check (which only warns on disagreement) on
      purpose -- scrub.py is a mid-pipeline tool a human reviews afterward; push_gate is
      the last thing standing before public history, so a disagreement between the two
      scanners resolves toward BLOCKING, never toward trusting the more lenient one.
      If the engine itself cannot evaluate a file (bad rule shape, non-UTF-8 it was
      handed despite our own pre-check, an unexpected exit code), that is folded into
      CANNOT EVALUATE for the whole run -- never silently dropped, never treated as a
      pass for that file.

PRECEDENCE WHEN BOTH A CANNOT-EVALUATE CONDITION AND A REFUSE HIT EXIST IN THE SAME
      RUN: CANNOT EVALUATE (2) wins. Rationale: if even one file in the tree could not be
      fully evaluated (binary, unreadable, a symlinked directory, an engine failure),
      this run never finished walking the tree with full information, so it cannot
      responsibly certify ANY verdict about the tree as a whole -- including "REFUSED,
      and that is the only problem." Both exit 1 and exit 2 equally withhold the receipt
      and equally block the push; the distinction is purely for the human reading the
      exit code, so they know whether to fix a finding or fix the gate's ability to see.

SYMLINKED DIRECTORIES -- HANDLED, NOT A SILENT GAP: `os.walk` does not follow directory
      symlinks by default, which would make a symlinked subdirectory's contents
      invisible to this scan without any indication anything was skipped -- exactly the
      silent-miss class this gate exists to prevent. This file explicitly detects a
      symlinked directory anywhere in the tree, refuses to descend into it (no loop
      risk), and reports it as a CANNOT-EVALUATE problem rather than pretending the
      subtree does not exist. A symlinked FILE is read normally (open() follows it; a
      dangling one raises OSError and is reported as unreadable, same as any other
      unreadable file).

NON-REGULAR FILES -- STATTED BEFORE EVER OPENED (Fix 4, 2026-08-05 red-team): a named
      pipe planted in the tree blocks on open() with no timeout and no exit code --
      worse than a clean exit 2, because a `gate && git push` pipeline just hangs
      forever instead of failing loudly. Every entry `os.walk` hands back is `os.stat`'d
      FIRST; anything that isn't a regular file (FIFO, socket, block/char device) is
      folded into CANNOT EVALUATE and never passed to `open()`.

RECEIPT -- TAMPER-EVIDENT, PINS WHAT WAS VERIFIED:
      { schema, generated_at, tree_root, refuse_rules_path + its sha256,
        rewrite_rules_path + its sha256, file_count, files: [{path, sha256}, ...],
        tree_sha256 (a single hash over the whole files list), rewrite_survivors
        (informational), verdict, bounds, receipt_sha256 (a self-hash over every other
        field) }.
      VERDICT LABEL, RENAMED 2026-08-05: the passing verdict reads "NO-LITERAL-MATCH",
      not "CLEAN" -- "CLEAN" claimed a property this gate never earned ("no identity
      present"); all it actually knows is "no literal, canonicalised, decoded, or
      ROT13'd match found." `bounds` states plainly, ON THE RECEIPT ITSELF, what was
      and was not checked (see RECEIPT_BOUNDS below) so a human reading the JSON does
      not have to trust this docstring to know the scope.
      HONEST BOUND: `receipt_sha256` is a plain SHA-256 integrity check, not a
      cryptographic signature. It catches accidental drift and naive hand-edits (bump a
      field, forget to recompute the hash) -- it does NOT defend against a sophisticated
      attacker with write access to the receipt file who recomputes the hash after
      tampering. That threat model would need a signing key this gate does not hold. For
      a solo-operator shipping lane where the receipt's job is "did the code that ran
      actually verify this," not "resist a nation-state," that bound is acceptable and is
      stated here rather than hidden.
      `--check-receipt PATH [--tree DIR]` re-validates: the receipt's own integrity hash,
      the rules files' hashes, and a fresh walk of the tree (missing/added/modified files
      all counted as drift) -- FAILS (exit 1) on ANY mismatch, CANNOT EVALUATE (exit 2)
      if the receipt or tree cannot be read at all.

RECEIPT PERSISTENCE IS OPT-IN, ON PURPOSE (mirrors phase_gate.py's `--stamp` flag): a
      CLEAN run always computes the receipt in memory (visible via `--json`), but only
      WRITES it to disk when `--receipt PATH` is given. Running the gate without
      `--receipt` is a valid dry-run/preview and prints a warning that nothing on disk
      will certify this run -- wiring push_gate into an actual pre-push step means always
      passing `--receipt`. A REFUSED or CANNOT-EVALUATE run never writes a receipt
      regardless of this flag.

WHAT THIS FILE DOES NOT DO: it is not a git hook itself and does not stop anyone from
      running `git push` by hand without ever invoking it -- wiring it into an actual
      pre-push hook (or a CI check that requires the receipt file to exist and validate)
      is a separate integration step outside this file's scope. It also does not rewrite
      anything (that is scrub.py's job) and does not decide WHICH files belong in the
      staging tree (that is the manifest, upstream of scrub.py).

THE JUDGE GATE [Build 1, 2026-08-05] -- read this before touching --judge-receipt.
      PROBLEM A RED TEAM FOUND: this file's own scan is literal and meaning-blind by
      design -- exhaustive over 28 known patterns plus their canonical/decoded/ROT13
      forms, but structurally unable to see a real name used in ordinary prose with NO
      hunted string in it, or an identity fragmented across files ("En" in one file,
      "ver" in another). `judge.py` sees MEANING but cannot be called from inside this
      process (each `claude -p` invocation cold-starts the whole CLI, ~36s even idle;
      chaining that per-file here would time out, and a subagent shelling out to it
      double-nests the harness and times out worse).
      THE FIX IS STRUCTURAL, NOT PROCEDURAL: this gate does not perform judgment
      itself -- it REFUSES TO BLESS A TREE THAT HAS NOT BEEN JUDGED. `--judge-receipt
      PATH` names a receipt `judge.py --consume --receipt PATH` already wrote (pinned,
      by tree hash, to the exact files it reviewed -- see canon.py's `compute_tree_state`,
      which both files call so their hashes can be compared byte-for-byte). This file
      validates that receipt -- parses, self-hash intact, tree hash matches the tree
      being gated RIGHT NOW -- and folds its `summary.findings_present` into this gate's
      own verdict with OR, the same paranoid combination rule used for the mechanical
      engine cross-check above. A file added, removed, or edited after judge.py ran
      changes the live tree hash, so a stale receipt is CANNOT EVALUATE, never a silent
      pass -- "the tree moved since you judged it" is exactly the case this exists to
      catch.
      ESCAPE HATCH, deliberately visible, never silent: `--accept-unjudged` allows a run
      with NO judge receipt at all. It prints a loud warning to stderr, and the push
      receipt records `"judged": false` and verdict `NO-LITERAL-MATCH-UNJUDGED` --
      never the unearned `NO-LITERAL-MATCH`, which now specifically means "AND a
      meaning-level judge pass, pinned to this tree, found nothing either." A dry run
      (no receipt at all, gate-only) stays possible via this flag; a SILENT bypass does
      not -- there is no flag that produces judged:true without an actual valid receipt.

      BUILD 2 (2026-08-05, same day) -- A RED TEAM FORGED A JUDGE RECEIPT IN FOUR LINES:
      `canon.compute_tree_state` + a hand-built `summary` + `canon.sha256_bytes` over it
      = a receipt that satisfied every Build-1 check (parses, self-hash intact, tree
      hash matches) WITHOUT ever running judge.py or invoking a model. ROOT CAUSE: both
      the tree hash AND the self-hash are UNKEYED -- attacker-computable with public
      stdlib. THE PRINCIPLE: a plain content hash proves the tree did not MOVE; it can
      never prove WHO looked at it. `validate_and_load_judge_receipt` now additionally
      requires (both, not either):
        HALF A -- an HMAC-SHA256 signature (`receipt_hmac_sha256`) verified against a
          machine-local key at `~/.config/lifehack/shipping-lane-hmac.key` (generated
          by `judge.py --consume` on first use). Missing key / missing signature / bad
          signature is CANNOT EVALUATE, never a silent unauthenticated pass -- see
          `_load_hmac_key_for_verify`.
        HALF B -- the receipt's pinned `manifest_sha256` / `verdicts_sha256` /
          `scrub_report_sha256` must match files still on disk, and this file then
          calls `judge.run_consume()` AGAIN on those exact files to RECOMPUTE
          `findings_present` from scratch rather than trusting the receipt's stored
          `summary` field. A receipt whose stored summary disagrees with what
          recomputing it produces is refused.
      HONEST BOUND: HMAC signing stops a third party without the key; it does not stop
      the operator, who can read that key file too and could hand-author a "clean"
      verdicts.json and sign it for real. No code closes that gap -- it is a trust
      boundary on the human operating the system, stated here rather than implied away.

USAGE
  push_gate.py --tree STAGING_DIR [--refuse-rules PATH] [--rewrite-rules PATH]
               [--receipt PATH]
               (--judge-receipt JUDGE_RECEIPT_PATH | --accept-unjudged)
               [--json]
  push_gate.py --check-receipt RECEIPT_PATH [--tree STAGING_DIR] [--json]
  push_gate.py --selftest

EXIT CODES (the parts-library house contract)
  0  CLEAN / VALID     -- gate mode: every file evaluated, no unresolved REFUSE hit, and
                          EITHER a valid non-stale judge receipt shows no findings OR
                          --accept-unjudged was explicitly given; a receipt was written
                          if --receipt was given.
                          check-receipt mode: the receipt still matches the tree exactly.
  1  REFUSED / INVALID -- gate mode: at least one file has an unresolved REFUSE hit,
                          and/or a valid judge receipt reports findings present; NO
                          receipt is written. check-receipt mode: drift or tampering
                          detected -- the receipt no longer certifies anything.
  2  CANNOT EVALUATE    -- missing/empty staging tree, missing rule file, a file that
                          could not be read or decoded, a symlinked directory, a missing
                          receipt/tree in check-receipt mode, OR (Build 1) a missing,
                          invalid, hand-edited, or STALE judge receipt when
                          --accept-unjudged was not given. Fail closed, always -- an
                          empty tree, an unreadable file, or an unjudged tree with no
                          explicit waiver is NEVER reported clean.
"""

from __future__ import annotations

import argparse
import codecs
import hashlib
import hmac
import json
import os
import re
import secrets
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import canon  # noqa: E402 -- sibling module, same directory, imported after sys.path fix
import judge  # noqa: E402 -- sibling module; [Build 2] used ONLY to re-derive a judge
# receipt's findings_present from its own recorded evidence (judge.run_consume) -- see
# validate_and_load_judge_receipt's HALF B. Never used to invoke an LLM from in here;
# run_consume is pure stdlib merge logic, same constraint as everything else this file
# calls in-process.

PARTS = os.path.realpath(os.path.join(HERE, "..", "parts"))
FORBIDDEN_CONTENT = os.path.join(PARTS, "forbidden_content.py")
MOVE_ASIDE = os.path.join(PARTS, "move_aside.py")
# ⭐ THE SHIPPED RULE FILE IS ONLY HALF THE SET, DELIBERATELY.
#
# `refuse-rules.json` in this repo holds what is true for everybody -- credential shapes,
# home paths, cloud-drive mounts -- and NOT ONE PERSON. The terms that identify whoever is
# running this are compiled from their own file, outside the repo, by `identity_rules.py`.
# The lane this came from kept its author's name, handle, address and folder names as
# literals in the committed rule file, which protects exactly one person and silently
# reports everybody else's own name as clean.
#
# `_effective_rules()` composes both tiers into a real file and returns its path, so every
# function below keeps taking a rule PATH and the receipt keeps pinning that file's sha256
# -- which now covers the personal tier too. No identity file is CANNOT EVALUATE.
BASE_REFUSE_RULES = os.path.join(HERE, "refuse-rules.json")

CLEAN, REFUSED, CANNOT_EVALUATE = 0, 1, 2
RECEIPT_SCHEMA = "push_gate.receipt.v3"
# v3 (Build 1, 2026-08-05): adds "judged" + "judge" fields to the receipt body; the
# hashing primitives below moved to canon.py so push_gate.py and judge.py compute a
# tree hash the exact same way (see canon.py's "tree hashing (Build 1)" section).
JUDGE_RECEIPT_SCHEMA = "judge.receipt.v2"  # MUST match judge.py's constant of the same
# name exactly -- this string is a DOCUMENTED coupling: if judge.py's schema string ever
# changes, this one must change with it, or every receipt judge.py writes will look
# unrecognized here. [Build 2, 2026-08-05 forgery red-team] bumped v1 -> v2 alongside
# judge.py's own bump -- see JUDGE_RECEIPT_SCHEMA's comment there for what v2 added.
# NOTE: push_gate.py now DOES import judge.py (see the import above) -- purely to call
# its pure-stdlib run_consume() a second time for re-derivation (HALF B below); this
# does not reintroduce the "call an LLM from in here" problem the module docstring
# warns about, since run_consume never touches a model.

VERDICT_LABEL_UNJUDGED = "NO-LITERAL-MATCH-UNJUDGED"


class CannotEvaluate(Exception):
    """Something could not be evaluated -- always maps to exit 2, fail closed."""


# --------------------------------------------------------------------------- HMAC verify
#
# [Build 2, 2026-08-05 forgery red-team] HALF A -- see judge.py's matching comment block
# (the signing side) for the full rationale. This side only ever READS the key; it never
# generates one -- a gate that silently created a fresh key on a machine where judge.py
# never ran would happily "verify" a signature made with a key nothing else knows about,
# which is just a slower way of accepting anything. If the key is missing, that is
# CANNOT EVALUATE with a message explaining the key is required -- never a silent
# downgrade to trusting the unkeyed receipt_sha256 alone, which is exactly the hole this
# closes. TEST ISOLATION: same SHIPPING_LANE_HMAC_KEY_PATH env var judge.py honors.

_HMAC_KEY_MIN_BYTES = 32
_HMAC_KEY_DEFAULT_PATH = os.path.expanduser(
    "~/.config/lifehack/shipping-lane-hmac.key")


def _hmac_key_path():
    return os.environ.get("SHIPPING_LANE_HMAC_KEY_PATH", _HMAC_KEY_DEFAULT_PATH)


def _load_hmac_key_for_verify():
    path = _hmac_key_path()
    if not os.path.isfile(path):
        raise CannotEvaluate(
            "cannot verify the judge receipt's signature -- the machine-local HMAC key "
            "{!r} does not exist. This key is REQUIRED to authenticate any judge "
            "receipt (a plain content hash proves the tree did not move, never who "
            "looked at it); without it, no receipt can be trusted, so this is CANNOT "
            "EVALUATE, never a silent unauthenticated pass. Run `judge.py --consume` "
            "once (it generates the key on first use) or restore the key file at that "
            "path.".format(path))
    with open(path, "rb") as fh:
        key = fh.read()
    if len(key) < _HMAC_KEY_MIN_BYTES:
        raise CannotEvaluate(
            "HMAC key at {!r} is only {} byte(s) (< {} minimum) -- refusing to trust a "
            "key this weak for signature verification".format(
                path, len(key), _HMAC_KEY_MIN_BYTES))
    return key


# --------------------------------------------------------------------------- hashing
#
# Build 1 (2026-08-05): these three are now canon.py's own implementations (aliased
# here, not redefined) so push_gate.py's tree_sha256 and judge.py's judge-receipt
# tree_sha256 can never silently drift apart -- see canon.py's "tree hashing" section.
sha256_bytes = canon.sha256_bytes
sha256_file = canon.sha256_file
canonical_json = canon.canonical_json


# --------------------------------------------------------------------------- rules

def effective_rules(refuse=None, rewrite=None, identity=None, workdir=None):
    """Which rule files this run gates against.

    A caller that already composed a set (the `/ship` sequence does, once, so scrub and
    this gate provably see the SAME rules) passes it in. Otherwise both tiers are composed
    here from the identity file. FAIL CLOSED when there is none: gating a tree with an
    empty personal tier means a receipt that certifies a file carrying your own name."""
    if refuse:
        return refuse, rewrite
    sys.path.insert(0, HERE)
    try:
        import identity_rules                                # noqa: E402
    except ImportError as e:
        raise CannotEvaluate("identity_rules.py is not importable: {}".format(e))
    wd = workdir or tempfile.mkdtemp(prefix="push-gate-rules-")
    try:
        rp, wp, _ip, _n = identity_rules.effective_rule_files(wd, identity_file=identity)
    except identity_rules.IdentityMissing as e:
        raise CannotEvaluate(str(e))
    return rp, wp


def load_rules(path, what, allow_empty=False):
    if not path or not os.path.isfile(path):
        raise CannotEvaluate("{} not found: {!r}".format(what, path))
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as e:
        raise CannotEvaluate("cannot read {} {!r}: {}".format(what, path, e))
    if not isinstance(data, list):
        raise CannotEvaluate("{} must be a JSON list".format(what))
    if not data and not allow_empty:
        raise CannotEvaluate(
            "{} must be a non-empty JSON list -- fail closed: an empty rule set would "
            "report every file clean".format(what))
    return data


def validate_rule_shapes(rules, what):
    for rule in rules:
        rid = rule.get("id") if isinstance(rule, dict) else None
        if not rid:
            raise CannotEvaluate("{}: a rule is missing 'id': {!r}".format(what, rule))
        if rule.get("mode") != "regex":
            raise CannotEvaluate(
                "{} rule {!r} has mode {!r}; push_gate only trusts mode 'regex' rules "
                "(verify_rules.py should have caught this upstream)".format(
                    what, rid, rule.get("mode")))
        pat = rule.get("pattern")
        if not pat:
            raise CannotEvaluate("{} rule {!r} has no 'pattern'".format(what, rid))
        try:
            re.compile(pat)
        except re.error as e:
            raise CannotEvaluate(
                "{} rule {!r} pattern does not compile: {}".format(what, rid, e))


# --------------------------------------------------------------------------- scanning

def hits_for_rule(text, rx):
    """Every occurrence, never just the first -- this is the last gate."""
    lines = text.splitlines()
    out = []
    for m in rx.finditer(text):
        line_no = text.count("\n", 0, m.start()) + 1
        line = lines[line_no - 1].strip() if 0 <= line_no - 1 < len(lines) else ""
        out.append({"line": line_no, "evidence": line[:200]})
    return out


def fc_exit_code(rules_path, text_path):
    """Run the REAL forbidden_content.py CLI; return (exit_code, stderr)."""
    proc = subprocess.run(
        [sys.executable, FORBIDDEN_CONTENT, "--rules", rules_path,
         "--text-file", text_path, "--json"],
        capture_output=True, text=True)
    return proc.returncode, proc.stderr


def fc_exit_code_on_text(rules_path, text):
    """Run the REAL forbidden_content.py CLI against arbitrary TEXT (not a file already
    on disk) by spilling it to a throwaway temp file first. Used to run the unmodified
    engine a SECOND time against a canonicalised view -- see canon.py's module
    docstring for why this satisfies "match twice, union the result" without touching
    system/parts/forbidden_content.py at all."""
    fd, tmp_path = tempfile.mkstemp(prefix="push-gate-canon-", suffix=".txt")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        return fc_exit_code(rules_path, tmp_path)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _non_regular_reason(mode):
    if stat.S_ISFIFO(mode):
        return "named pipe (FIFO)"
    if stat.S_ISSOCK(mode):
        return "socket"
    if stat.S_ISBLK(mode):
        return "block device"
    if stat.S_ISCHR(mode):
        return "character device"
    if stat.S_ISDIR(mode):
        return "directory"  # os.walk shouldn't hand us one, but fail closed if it does
    return "non-regular file"


# Build 1 (2026-08-05): moved to canon.py (as walk_tree_files) so judge.py shares the
# exact same tree-walking algorithm push_gate.py uses -- see canon.py's "tree hashing"
# section. Aliased here under the old name so every call site below is unchanged.
walk_tree = canon.walk_tree_files


def scan_tree(tree_root, refuse_rules, refuse_rules_path, rewrite_rules):
    """Walk EVERY file. Never raises -- fail-closed conditions are aggregated into
    problem_files for the caller to turn into CannotEvaluate."""
    files, symlinked_dirs = walk_tree(tree_root)

    result = {
        "file_count": len(files),
        "problem_files": [],
        "refused_files": [],
        "rewrite_survivors": [],
        "gated_files": [],
    }
    for d in symlinked_dirs:
        result["problem_files"].append({
            "path": d, "reason": "symlinked-directory",
            "detail": "a symlinked directory is not followed (no loop risk taken); its "
                       "contents cannot be certified as scanned",
        })

    for rel, abspath in files:
        # FIX 4 (2026-08-05 red-team): stat() BEFORE ever calling open(). A FIFO
        # blocks on open() with no timeout and no exit code -- worse than a clean
        # exit 2 in a `gate && git push` pipeline, because the pipeline just hangs
        # forever instead of failing. A socket/device is equally never something
        # this gate should hand to open(). Fail closed, never opened.
        try:
            st = os.stat(abspath)
        except OSError as e:
            result["problem_files"].append(
                {"path": rel, "reason": "unreadable", "detail": str(e)})
            continue
        if not stat.S_ISREG(st.st_mode):
            result["problem_files"].append({
                "path": rel, "reason": "non-regular-file",
                "detail": "refusing to open() a {} -- cannot be certified as scanned; "
                          "CANNOT EVALUATE, never opened".format(
                              _non_regular_reason(st.st_mode))})
            continue

        try:
            with open(abspath, "rb") as fh:
                raw = fh.read()
        except OSError as e:
            result["problem_files"].append(
                {"path": rel, "reason": "unreadable", "detail": str(e)})
            continue

        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as e:
            result["problem_files"].append(
                {"path": rel, "reason": "binary/non-utf8", "detail": str(e)})
            continue

        own_hits = []
        for rule in refuse_rules:
            rx = re.compile(rule["pattern"], re.MULTILINE)
            occ = hits_for_rule(text, rx)
            if occ:
                own_hits.append({
                    "id": rule["id"], "tier": rule.get("tier", ""),
                    "why": rule.get("why", ""), "hits": occ})
            # FIX 1 (canonicalisation, 2026-08-05 red-team -- 17/17 bypasses): the
            # raw pass above is UNCHANGED; this ADDS a second pass over the
            # Unicode-canonicalised view (fullwidth/homoglyph/leetspeak folded,
            # zero-width stripped, intra-word separators collapsed) and a third
            # over a ROT13'd view. Either finding is unioned in -- never a
            # replacement for the raw pass, only an addition on top of it.
            canon_occ = canon.canonical_only_hits(text, rx)
            if canon_occ:
                own_hits.append({
                    "id": rule["id"], "tier": rule.get("tier", ""),
                    "why": rule.get("why", "") + " [found via CANONICALISED text "
                                                  "only -- see canonical_evidence]",
                    "hits": canon_occ})
            rot13_occ = canon.transformed_only_hits(text, rx, canon.rot13, "rot13")
            if rot13_occ:
                own_hits.append({
                    "id": rule["id"], "tier": rule.get("tier", ""),
                    "why": rule.get("why", "") + " [found via ROT13-decoded text "
                                                  "only]",
                    "hits": rot13_occ})
            # THE PATH IS SCANNED SURFACE TOO -- added 2026-08-05 after a red-team
            # pass walked straight through this gate. A file merely NAMED
            # "<personal-email>.txt", with a spotless body, returned exit 0 CLEAN and
            # the gate wrote a receipt whose own JSON contained the address verbatim.
            # Git tracks FILENAMES as first-class data, so that leak reaches public
            # history and survives any later content-only scrub -- `git log --stat`
            # exposes it forever. Content-only scanning was the whole miss.
            if rx.search(rel):
                own_hits.append({
                    "id": rule["id"], "tier": rule.get("tier", ""),
                    "why": rule.get("why", "") + " [IN THE FILE PATH, not the content]",
                    "hits": [{"line": 0, "evidence": rel, "surface": "path"}]})

        # FIX 2 (encoded payloads, 2026-08-05 red-team): a base64/hex/URL-encoded
        # secret or name, plus a distinct high-entropy-blob heuristic for a format no
        # literal rule anticipates. Never auto-fixable, always folded into own_hits.
        for finding in canon.scan_encoded_payloads(text, refuse_rules):
            own_hits.append(finding)

        # SECOND HARDENING PASS (2026-08-05, same day, second red-team): bidi controls
        # and Unicode TAG characters are BANNED OUTRIGHT by mere presence -- see
        # canon.py's module docstring. Not JSON rules (a literal-text regex against raw
        # bytes cannot express "this codepoint is present anywhere"), so they carry
        # their own ids and are never seen by verify_rules.py at all.
        bidi_hits = canon.scan_bidi_controls(text)
        if bidi_hits:
            own_hits.append({
                "id": "unicode-bidi-control", "tier": "1-identity",
                "why": "a Unicode bidirectional control character (U+202A-U+202E or "
                       "U+2066-U+2069) is present -- the Trojan Source class: "
                       "reversed storage that displays as the forward name. No "
                       "legitimate shipped file needs one.",
                "hits": bidi_hits,
            })

        tag_hits = canon.scan_tag_chars(text)
        if tag_hits:
            own_hits.append({
                "id": "unicode-tag-chars", "tier": "1-identity",
                "why": "a Unicode TAG block character (U+E0000-U+E007F) is present -- "
                       "fully invisible in every normal renderer and capable of "
                       "carrying hidden text recoverable verbatim by a decoder. No "
                       "legitimate shipped file needs one.",
                "hits": tag_hits,
            })

        fc_rc, fc_err = fc_exit_code(refuse_rules_path, abspath)
        if fc_rc not in (CLEAN, REFUSED):
            result["problem_files"].append({
                "path": rel, "reason": "forbidden_content.py could not evaluate",
                "detail": fc_err.strip()[:300]})
            continue

        # FIX 1, engine half: run the UNMODIFIED forbidden_content.py a SECOND time
        # against the canonicalised text (never modified in system/parts/ itself --
        # see canon.py's docstring). Either exit code REFUSED is enough to refuse.
        canon_text_for_engine = canon.canonicalize(text)
        fc_rc_canon, fc_err_canon = fc_exit_code_on_text(
            refuse_rules_path, canon_text_for_engine)
        if fc_rc_canon not in (CLEAN, REFUSED):
            result["problem_files"].append({
                "path": rel,
                "reason": "forbidden_content.py could not evaluate (canonical pass)",
                "detail": fc_err_canon.strip()[:300]})
            continue

        file_refused = bool(own_hits) or fc_rc == REFUSED or fc_rc_canon == REFUSED
        if file_refused:
            result["refused_files"].append({
                "path": rel, "hits": own_hits, "engine_exit": fc_rc,
                "engine_exit_canonical": fc_rc_canon,
                "engine_only": bool((fc_rc == REFUSED or fc_rc_canon == REFUSED)
                                     and not own_hits),
            })

        for rule in rewrite_rules:
            rx = re.compile(rule["pattern"], re.MULTILINE)
            occ = hits_for_rule(text, rx)
            if occ:
                result["rewrite_survivors"].append({
                    "path": rel, "id": rule["id"], "why": rule.get("why", ""),
                    "hits": occ})

        if not file_refused:
            result["gated_files"].append({"path": rel, "sha256": sha256_bytes(raw)})

    return result


# --------------------------------------------------------------------------- receipt

# FIX 3 (the receipt overclaims, 2026-08-05 red-team): "CLEAN" asserted a property this
# gate never earned -- "no identity present," when all it actually knows is "no literal
# (or canonicalised/decoded/ROT13'd) match found." Renamed to NO-LITERAL-MATCH, and the
# receipt now carries `bounds` on its face so a human reading the JSON (not just this
# docstring) sees the honest scope without having to trust prose elsewhere.
VERDICT_LABEL = "NO-LITERAL-MATCH"

RECEIPT_BOUNDS = {
    "checked": [
        "literal substring match against the 28 known identity/secret patterns, "
        "against the RAW file content",
        "the same patterns against a Unicode-canonicalised view of the content "
        "(NFKD-normalised, zero-width/BOM stripped, homoglyphs/small-caps/leetspeak "
        "folded, single-character intra-word separators collapsed)",
        "the same patterns against a ROT13-decoded view of the content",
        "base64 / hex / percent-(URL-)encoded / base32 / quoted-printable spans, "
        "decoded up to 3 layers deep and re-checked against the same patterns",
        "high-Shannon-entropy blobs (>= 32 chars, >= 4.5 bits/char) as a distinct "
        "unknown-format-secret heuristic -- no literal pattern names an unseen format",
        "the mere PRESENCE of a Unicode bidi control character or a TAG-block "
        "character anywhere in the file -- banned outright, never interpreted",
        "filenames and paths, not just file content",
        "IF 'judged' is true (see the 'judge' block below): a meaning-level LLM "
        "judgment pass (judge.py) has reviewed every file in this tree, pinned by "
        "tree hash to this EXACT content -- catches a real name used in prose with no "
        "hunted string, a client anecdote, or an unavailable-subsystem reference, "
        "none of which any check above can see",
    ],
    "NOT_checked": [
        "semantic or paraphrased identity leaks, WHEN 'judged' is false (the "
        "--accept-unjudged escape hatch was used) -- with no judge receipt, prose "
        "that describes the author without literally naming him is invisible to "
        "every check above",
        "a secret in an encoding/cipher this file does not implement (custom, "
        "multi-layer beyond 3 deep, or steganographic encodings)",
        "whether the 28 rules themselves are complete -- a rule that was never "
        "written catches nothing no matter how many ways the text is transformed",
        "even when judged: whether the judge's own read was thorough -- see judge.py's "
        "own documented bounds (a judge reviews per-bundle text, so a leak split "
        "exactly at a bundle boundary is a residual risk the judge receipt does not "
        "itself rule out)",
    ],
}


def _judge_report_block(judge_info):
    """Shape used both in the human/JSON report and inside the push receipt body --
    ONE place that defines what "the judge block" looks like, judged or not."""
    if not judge_info:
        return {
            "judged": False,
            "judge_receipt_path": None,
            "judge_receipt_sha256": None,
            "judge_verdict": None,
            "mechanical_count": None,
            "judge_count": None,
            "disputes_count": None,
            "rejected_count": None,
        }
    return {
        "judged": True,
        "judge_receipt_path": judge_info["path"],
        "judge_receipt_sha256": judge_info["receipt_sha256"],
        "judge_verdict": judge_info["verdict"],
        "mechanical_count": judge_info["mechanical_count"],
        "judge_count": judge_info["judge_count"],
        "disputes_count": judge_info["disputes_count"],
        "rejected_count": judge_info["rejected_count"],
    }


def validate_and_load_judge_receipt(path, tree_dir):
    """Parse + fully validate a judge.py judge receipt against the tree being gated
    RIGHT NOW. [Build 1, 2026-08-05; hardened Build 2, 2026-08-05 same day, forgery
    red-team] Raises CannotEvaluate on ANY problem -- missing file, bad JSON, wrong
    schema, a hand-edited/corrupted self-hash, a missing/invalid/mismatched HMAC
    signature, a tree hash that no longer matches what is on disk THIS INSTANT (a file
    was added, removed, or changed since judge.py ran), missing/mismatched pinned
    evidence, or a recomputed findings_present that disagrees with what the receipt
    claims. Never returns a partial/best-effort result -- a judge receipt is either
    fully trustworthy or this function never returns at all.

    A RED TEAM FORGED A RECEIPT IN FOUR LINES against the pre-Build-2 version of this
    function: `canon.compute_tree_state` + a hand-built `summary` + an UNKEYED
    `sha256(canonical_json(body))` self-hash satisfied every check that existed then.
    THE PRINCIPLE: a plain content hash proves the tree did not MOVE; it can never prove
    WHO looked at it. Two checks below close that, and BOTH are required:
      HALF A (authenticate) -- `receipt_hmac_sha256` must verify against the
        machine-local key at `_hmac_key_path()`, via `hmac.compare_digest`. A forger
        without read access to that key file cannot produce a signature that verifies,
        no matter how it computes `receipt_sha256`.
      HALF B (re-derive, don't trust the summary) -- `manifest_path` / `verdicts_path` /
        `scrub_report_path` must still exist and hash-match the `*_sha256` fields
        pinned in the receipt, and THIS FILE THEN CALLS `judge.run_consume()` AGAIN on
        those exact files to recompute `findings_present` from scratch, rather than
        reading the stored `summary` field as given. A receipt whose recorded summary
        disagrees with what recomputing it produces is refused outright -- the
        recomputed value is what this function returns, never the stored one.
    HONEST BOUND, stated plainly: HMAC verification stops a THIRD PARTY without the key.
    It does not stop the operator, who can read that key file just as easily as
    judge.py does, and could hand-author a "clean" verdicts.json and sign it for real by
    actually running `judge.py --consume` over it. No code in this file (or anywhere)
    can detect that an authentic signature was produced over verdicts an LLM never
    actually wrote -- that is a trust boundary this system places on the human
    operating it, not a gap left open by accident."""
    if not path or not os.path.isfile(path):
        raise CannotEvaluate("judge receipt not found: {!r}".format(path))
    try:
        with open(path, "r", encoding="utf-8") as fh:
            receipt = json.load(fh)
    except (OSError, json.JSONDecodeError) as e:
        raise CannotEvaluate("cannot read/parse judge receipt {!r}: {}".format(path, e))
    if not isinstance(receipt, dict) or receipt.get("schema") != JUDGE_RECEIPT_SCHEMA:
        raise CannotEvaluate(
            "{!r} is not a recognized judge receipt (schema mismatch: expected {!r}, "
            "got {!r})".format(
                path, JUDGE_RECEIPT_SCHEMA,
                receipt.get("schema") if isinstance(receipt, dict) else None))

    stored_self_hash = receipt.get("receipt_sha256")
    body = {k: v for k, v in receipt.items()
           if k not in ("receipt_sha256", "receipt_hmac_sha256")}
    canon_bytes = canon.canonical_json(body)
    if stored_self_hash != canon.sha256_bytes(canon_bytes):
        raise CannotEvaluate(
            "judge receipt {!r} failed its own integrity check (self-hash mismatch) -- "
            "hand-edited or corrupted since judge.py wrote it".format(path))

    # HALF A: authenticate. An unkeyed self-hash alone is exactly the four-line forgery
    # this build closes -- see the docstring above. Fail closed on ANY of: no key file,
    # a key too short to trust, no signature field on the receipt, or a signature that
    # does not match -- never a downgrade to "verify only if a key happens to exist".
    hmac_key = _load_hmac_key_for_verify()
    stored_hmac = receipt.get("receipt_hmac_sha256")
    if not isinstance(stored_hmac, str) or not stored_hmac:
        raise CannotEvaluate(
            "judge receipt {!r} has no receipt_hmac_sha256 -- an unsigned receipt "
            "(or one from before Build 2) cannot be authenticated and is never "
            "trusted".format(path))
    expected_hmac = hmac.new(hmac_key, canon_bytes, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_hmac, stored_hmac):
        raise CannotEvaluate(
            "judge receipt {!r} FAILED SIGNATURE VERIFICATION -- its receipt_hmac_sha256 "
            "does not match what the machine-local key produces for this body. Either "
            "the receipt was tampered with after signing, or it was never actually "
            "produced by a real `judge.py --consume` run on this machine. Refusing to "
            "trust it.".format(path))

    files_sorted, live_tree_hash, symlinked_dirs, problem_files = \
        canon.compute_tree_state(tree_dir)
    if symlinked_dirs or problem_files:
        raise CannotEvaluate(
            "cannot verify the judge receipt against the tree at {!r} -- the tree "
            "itself has a problem that must be resolved first: symlinked dirs {}, "
            "unreadable/non-regular files {}".format(
                tree_dir, symlinked_dirs, problem_files))
    if live_tree_hash != receipt.get("tree_sha256"):
        raise CannotEvaluate(
            "judge receipt {!r} is STALE -- its tree_sha256 does not match the tree "
            "being gated right now (a file was added, removed, or modified since "
            "judge.py --consume ran). Re-run the judge pass against the current tree "
            "and pass its fresh receipt.".format(path))

    summary = receipt.get("summary")
    if not isinstance(summary, dict) or "findings_present" not in summary:
        raise CannotEvaluate(
            "judge receipt {!r} has no usable 'summary.findings_present' -- cannot "
            "determine whether the judge pass found anything".format(path))

    # HALF B: re-derive, don't trust the summary. Pin the evidence (the manifest,
    # verdicts, and scrub-report the summary claims to be computed from) THEN recompute
    # findings_present by re-running the real merge logic over it -- see the docstring.
    manifest_path = receipt.get("manifest_path")
    verdicts_path = receipt.get("verdicts_path")
    scrub_report_path = receipt.get("scrub_report_path")
    for label, evidence_path, hash_field in (
            ("manifest", manifest_path, "manifest_sha256"),
            ("verdicts", verdicts_path, "verdicts_sha256"),
            ("scrub report", scrub_report_path, "scrub_report_sha256")):
        if not evidence_path or not os.path.isfile(evidence_path):
            raise CannotEvaluate(
                "judge receipt {!r} names a {} at {!r} that no longer exists on disk "
                "-- cannot re-derive findings_present from evidence that is gone. "
                "Fail closed: a summary with no verifiable evidence behind it is never "
                "trusted.".format(path, label, evidence_path))
        recorded_hash = receipt.get(hash_field)
        if not recorded_hash:
            raise CannotEvaluate(
                "judge receipt {!r} has no recorded {} -- this receipt predates "
                "evidence-pinning (Build 2) or is malformed; refusing to trust its "
                "summary without pinned evidence to check it against".format(
                    path, hash_field))
        if canon.sha256_file(evidence_path) != recorded_hash:
            raise CannotEvaluate(
                "judge receipt {!r}'s {} does not match the {} it claims to certify -- "
                "the evidence file changed after the receipt was signed".format(
                    path, hash_field, label))

    bundle_coverage = receipt.get("bundle_coverage")
    if not isinstance(bundle_coverage, list) or not bundle_coverage:
        raise CannotEvaluate(
            "judge receipt {!r} has no per-bundle coverage recorded -- cannot confirm "
            "anything was actually reviewed".format(path))
    total_reviewed = sum(
        int(bc.get("file_count", 0)) for bc in bundle_coverage if isinstance(bc, dict))
    if total_reviewed <= 0:
        raise CannotEvaluate(
            "judge receipt {!r} reviewed ZERO files across all its bundles -- an empty "
            "judgment must never be accepted as a clean one".format(path))

    try:
        fresh_report = judge.run_consume(verdicts_path, manifest_path, scrub_report_path)
    except judge.CannotEvaluate as e:
        raise CannotEvaluate(
            "judge receipt {!r} could not be re-derived from its own pinned evidence -- "
            "re-running judge.py's merge logic against the manifest/verdicts/"
            "scrub-report it names failed: {}".format(path, e))

    fresh_summary = fresh_report["summary"]
    if (bool(fresh_summary["findings_present"]) != bool(summary.get("findings_present"))
            or fresh_summary["mechanical_count"] != summary.get("mechanical_count")
            or fresh_summary["judge_count"] != summary.get("judge_count")):
        raise CannotEvaluate(
            "judge receipt {!r}'s recorded summary ({!r}) does not match what "
            "recomputing the merge from its own pinned evidence produces ({!r}) -- "
            "refusing to trust either without an explanation for the drift".format(
                path, summary, fresh_summary))

    return {
        "path": os.path.abspath(path),
        "receipt_sha256": receipt.get("receipt_sha256"),
        "verdict": receipt.get("verdict"),
        # HALF B: the RECOMPUTED value, never the stored one -- see docstring.
        "findings_present": bool(fresh_summary["findings_present"]),
        "mechanical_count": fresh_summary["mechanical_count"],
        "judge_count": fresh_summary["judge_count"],
        "disputes_count": fresh_summary["disputes_count"],
        "rejected_count": fresh_summary["rejected_count"],
    }


def build_receipt(tree_dir, refuse_rules_path, rewrite_rules_path, scan, judged,
                  judge_info):
    files_sorted = sorted(scan["gated_files"], key=lambda f: f["path"])
    tree_hash = sha256_bytes(canonical_json(files_sorted))
    body = {
        "schema": RECEIPT_SCHEMA,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tree_root": os.path.abspath(tree_dir),
        "refuse_rules_path": os.path.abspath(refuse_rules_path),
        "refuse_rules_sha256": sha256_file(refuse_rules_path),
        "rewrite_rules_path": os.path.abspath(rewrite_rules_path),
        "rewrite_rules_sha256": sha256_file(rewrite_rules_path),
        "file_count": len(files_sorted),
        "files": files_sorted,
        "tree_sha256": tree_hash,
        "rewrite_survivors": scan["rewrite_survivors"],
        "judged": judged,
        "judge": _judge_report_block(judge_info),
        "verdict": VERDICT_LABEL if judged else VERDICT_LABEL_UNJUDGED,
        "bounds": RECEIPT_BOUNDS,
    }
    body["receipt_sha256"] = sha256_bytes(canonical_json(body))
    return body


def move_aside_receipt(path):
    """Required sibling-part call: never silently clobber a prior receipt at the same
    path -- preserve it under a generation name first (no-op, exit 0, if nothing is
    there yet)."""
    if not os.path.isfile(MOVE_ASIDE):
        raise CannotEvaluate("sibling part missing: {!r}".format(MOVE_ASIDE))
    proc = subprocess.run([sys.executable, MOVE_ASIDE, "--target", path],
                           capture_output=True, text=True)
    if proc.returncode != 0:
        raise CannotEvaluate(
            "move_aside could not clear a slot for the receipt {!r} (exit {}): {}".format(
                path, proc.returncode, proc.stderr.strip()[:300]))


def write_receipt(path, receipt):
    move_aside_receipt(path)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(receipt, fh, indent=2, sort_keys=True)
        fh.write("\n")


# --------------------------------------------------------------------------- gate run

def run_gate(tree_dir, refuse_rules_path, rewrite_rules_path, receipt_path=None,
             judge_receipt_path=None, accept_unjudged=False):
    if not os.path.isfile(FORBIDDEN_CONTENT):
        raise CannotEvaluate("sibling part missing: {!r}".format(FORBIDDEN_CONTENT))
    if not tree_dir or not os.path.isdir(tree_dir):
        raise CannotEvaluate(
            "staging tree not found or not a directory: {!r}".format(tree_dir))

    refuse_rules = load_rules(refuse_rules_path, "the effective refuse rules")
    # The rewrite tier ships empty and stays that way unless the person writes one. It
    # cannot fail open: it substitutes cosmetics and reports, and never decides whether
    # anything is clean.
    rewrite_rules = load_rules(rewrite_rules_path, "the effective rewrite rules",
                               allow_empty=True) if rewrite_rules_path else []
    validate_rule_shapes(refuse_rules, "refuse-rules.json")
    validate_rule_shapes(rewrite_rules, "rewrite-rules.json")

    # ---- BUILD 1 (2026-08-05): THE JUDGE GATE. -----------------------------------
    # This gate does not itself run an LLM (see module docstring) -- it structurally
    # REFUSES TO BLESS A TREE THAT HAS NOT BEEN JUDGED. A missing/invalid/stale judge
    # receipt is CANNOT EVALUATE, never a silent pass; the ONLY way past that without a
    # receipt is the deliberately loud --accept-unjudged escape hatch.
    judge_info = None
    if judge_receipt_path:
        judge_info = validate_and_load_judge_receipt(judge_receipt_path, tree_dir)
    elif not accept_unjudged:
        raise CannotEvaluate(
            "no --judge-receipt was given and --accept-unjudged was not passed -- this "
            "gate cannot certify an UNJUDGED tree. Run judge.py --prepare, have the "
            "calling session run the LLM pass over each bundle, then judge.py "
            "--consume --receipt PATH, then pass --judge-receipt PATH here. To "
            "deliberately waive judgment, pass --accept-unjudged -- the push receipt "
            "will then record judged:false and the verdict {!r}, never the unearned "
            "{!r}.".format(VERDICT_LABEL_UNJUDGED, VERDICT_LABEL))
    else:
        print(
            "WARNING: --accept-unjudged given -- proceeding WITHOUT the meaning-level "
            "judgment pass. Only literal/canonicalised/decoded matching has run; a "
            "real person's name used in a paragraph with no hunted string, or an "
            "identity fragmented across files, would NOT be caught by this run. The "
            "push receipt will record judged:false and verdict {!r}.".format(
                VERDICT_LABEL_UNJUDGED),
            file=sys.stderr)

    scan = scan_tree(tree_dir, refuse_rules, refuse_rules_path, rewrite_rules)

    if scan["file_count"] == 0:
        raise CannotEvaluate(
            "staging tree {!r} contains NO files -- fail closed: an empty tree must "
            "never report clean".format(tree_dir))

    if scan["problem_files"]:
        detail = "; ".join(
            "{} ({}: {})".format(p["path"], p["reason"], p["detail"][:120])
            for p in scan["problem_files"][:10])
        more = "" if len(scan["problem_files"]) <= 10 else " ... and {} more".format(
            len(scan["problem_files"]) - 10)
        raise CannotEvaluate(
            "{} file(s) could not be evaluated -- fail closed, no verdict can be "
            "certified for this tree: {}{}".format(
                len(scan["problem_files"]), detail, more))

    mechanical_refused = bool(scan["refused_files"])
    judge_refused = bool(judge_info and judge_info["findings_present"])
    verdict = REFUSED if (mechanical_refused or judge_refused) else CLEAN

    judged = judge_info is not None
    verdict_label = VERDICT_LABEL if judged else VERDICT_LABEL_UNJUDGED

    report = {
        "tree_root": os.path.abspath(tree_dir),
        "file_count": scan["file_count"],
        "refused_files": scan["refused_files"],
        "rewrite_survivors": scan["rewrite_survivors"],
        "judged": judged,
        "judge": _judge_report_block(judge_info),
        "verdict": "REFUSED" if verdict == REFUSED else verdict_label,
    }
    if mechanical_refused or judge_refused:
        report["refused_because"] = (
            (["mechanical"] if mechanical_refused else [])
            + (["judge"] if judge_refused else []))

    receipt = None
    if verdict == CLEAN:
        receipt = build_receipt(tree_dir, refuse_rules_path, rewrite_rules_path, scan,
                                judged, judge_info)
        if receipt_path:
            write_receipt(receipt_path, receipt)
            report["receipt_written_to"] = os.path.abspath(receipt_path)

    return verdict, report, receipt


def render_report(report, receipt_written):
    lines = []
    lines.append("push_gate -- {} file(s) scanned, tree {}".format(
        report["file_count"], report["tree_root"]))
    j = report.get("judge") or {}
    if j.get("judged"):
        lines.append(
            "judge: JUDGED via {} (verdict {}) -- mechanical={} judge={} disputes={} "
            "rejected={}".format(
                j["judge_receipt_path"], j["judge_verdict"], j["mechanical_count"],
                j["judge_count"], j["disputes_count"], j["rejected_count"]))
    else:
        lines.append(
            "judge: UNJUDGED -- --accept-unjudged escape hatch was used; only "
            "literal/canonicalised/decoded matching ran, no meaning-level pass")
    if report.get("refused_because"):
        lines.append("refused because: {}".format(
            " AND ".join(report["refused_because"])))
    if report["refused_files"]:
        lines.append("")
        lines.append("REFUSED FILES:")
        for f in report["refused_files"]:
            lines.append("  [REFUSED] {}".format(f["path"]))
            for h in f["hits"]:
                lines.append("    [{}] {}".format(h["id"], h["why"]))
                for hit in h["hits"]:
                    lines.append("      line {}: {}".format(
                        hit["line"], hit["evidence"]))
            if f.get("engine_only"):
                lines.append(
                    "    (forbidden_content.py flagged this file; this scan's own "
                    "finditer pass found no hit -- refused anyway, the more paranoid "
                    "of the two wins)")
    if report["rewrite_survivors"]:
        lines.append("")
        lines.append(
            "REWRITE SURVIVORS (reported, NOT blocking -- branding never blocks a push):")
        for r in report["rewrite_survivors"]:
            lines.append("  [{}] {} -- {}".format(r["id"], r["path"], r["why"]))
            for hit in r["hits"]:
                lines.append("    line {}: {}".format(hit["line"], hit["evidence"]))
    lines.append("")
    lines.append("-" * 60)
    lines.append("VERDICT: {}".format(report["verdict"]))
    if report["verdict"] in (VERDICT_LABEL, VERDICT_LABEL_UNJUDGED):
        if receipt_written:
            lines.append("receipt written: {}".format(receipt_written))
        else:
            lines.append(
                "WARNING: no --receipt path was given -- nothing on disk certifies "
                "this run. A real pre-push step must always pass --receipt.")
    else:
        lines.append("NO RECEIPT WRITTEN.")
    return "\n".join(lines)


# --------------------------------------------------------------------------- check-receipt

def check_receipt(receipt_path, tree_override=None):
    """Re-validate a receipt against the tree it claims to bless. Returns a list of
    findings (empty == valid). Raises CannotEvaluate if the receipt/tree cannot even be
    read -- fail closed, never silently 'valid'."""
    if not os.path.isfile(receipt_path):
        raise CannotEvaluate("receipt not found: {!r}".format(receipt_path))
    try:
        with open(receipt_path, "r", encoding="utf-8") as fh:
            receipt = json.load(fh)
    except (OSError, json.JSONDecodeError) as e:
        raise CannotEvaluate("cannot read/parse receipt {!r}: {}".format(receipt_path, e))
    if not isinstance(receipt, dict) or receipt.get("schema") != RECEIPT_SCHEMA:
        raise CannotEvaluate(
            "{!r} is not a push_gate receipt (schema mismatch)".format(receipt_path))

    findings = []

    stored_self_hash = receipt.get("receipt_sha256")
    body = {k: v for k, v in receipt.items() if k != "receipt_sha256"}
    if stored_self_hash != sha256_bytes(canonical_json(body)):
        findings.append(
            "receipt integrity hash mismatch -- this receipt JSON has been hand-edited "
            "or corrupted since push_gate wrote it")

    recorded_files = receipt.get("files", [])
    recomputed_tree_hash = sha256_bytes(
        canonical_json(sorted(recorded_files, key=lambda f: f.get("path", ""))))
    if recomputed_tree_hash != receipt.get("tree_sha256"):
        findings.append(
            "tree_sha256 does not match the receipt's own 'files' list -- the files "
            "array was altered after tree_sha256 was computed")

    if receipt.get("file_count") != len(recorded_files):
        findings.append(
            "receipt's file_count ({}) does not match the length of its own files list "
            "({})".format(receipt.get("file_count"), len(recorded_files)))

    tree_dir = tree_override or receipt.get("tree_root")
    if not tree_dir or not os.path.isdir(tree_dir):
        raise CannotEvaluate(
            "cannot re-validate: tree {!r} does not exist -- pass --tree to point at "
            "its current location".format(tree_dir))

    for path_key, hash_key, what in (
            ("refuse_rules_path", "refuse_rules_sha256", "refuse-rules.json"),
            ("rewrite_rules_path", "rewrite_rules_sha256", "rewrite-rules.json")):
        p = receipt.get(path_key)
        if not p or not os.path.isfile(p):
            findings.append(
                "{} recorded at {!r} no longer exists, so this receipt cannot be "
                "re-verified. If that path is a temp directory, the rules were composed "
                "into a throwaway one -- run the lane with --refuse-rules/--rewrite-rules "
                "pointing inside the run's own working directory, which lives as long as "
                "the staging tree the receipt pins".format(what, p))
            continue
        if sha256_file(p) != receipt.get(hash_key):
            findings.append(
                "{} has changed since this receipt was issued".format(what))

    live_files, live_symlinked_dirs = walk_tree(tree_dir)
    for d in live_symlinked_dirs:
        findings.append("tree now contains a symlinked directory not present when "
                         "gated: {!r}".format(d))

    live_hashes = {}
    for rel, abspath in live_files:
        try:
            live_hashes[rel] = sha256_file(abspath)
        except OSError as e:
            findings.append("cannot re-read {!r}: {}".format(rel, e))

    recorded_hashes = {f["path"]: f["sha256"] for f in recorded_files}

    for p in sorted(set(recorded_hashes) - set(live_hashes)):
        findings.append("gated file removed since the receipt was written: {!r}".format(p))
    for p in sorted(set(live_hashes) - set(recorded_hashes)):
        findings.append(
            "file present in the tree now but was never gated: {!r}".format(p))
    for p in sorted(set(recorded_hashes) & set(live_hashes)):
        if recorded_hashes[p] != live_hashes[p]:
            findings.append(
                "gated file modified since the receipt was written "
                "(content hash differs): {!r}".format(p))

    return findings


# ---------------------------------------------------------------------------- self-test

def _git_status():
    proc = subprocess.run(["git", "-C", os.path.realpath(os.path.join(HERE, "..", "..")),
                            "status", "--porcelain"], capture_output=True, text=True)
    return proc.stdout


def selftest():
    ok_all = True

    def report(label, passed, detail=""):
        nonlocal ok_all
        ok_all = ok_all and passed
        print("  [{}] {}{}".format("PASS" if passed else "FAIL", label,
                                    (" -- " + detail) if detail else ""))

    print("push_gate.py --selftest")

    # The shipped rule set has no person in it, so planting a name against it would prove
    # nothing. Compose against the lane's own INVENTED identity fixture -- the same set
    # verify_rules.py and scrub.py use -- so the personal tier is exercised here too and no
    # real identity is ever involved in a test run. The rewrite pair is planted for the
    # same reason: the rewrite tier ships empty.
    _rules_dir = tempfile.mkdtemp(prefix="push-gate-selftest-rules-")
    _rewrite_fixture = os.path.join(_rules_dir, "rewrite-fixture.json")
    with open(_rewrite_fixture, "w", encoding="utf-8") as _fh:
        json.dump([
            {"order": 1, "id": "specific-first", "mode": "regex",
             "pattern": "project-alpha-repo", "to": "alpha-public",
             "example": {"in": "project-alpha-repo", "out": "alpha-public"},
             "why": "MUST run before the general rule"},
            {"order": 2, "id": "general-second", "mode": "regex",
             "pattern": "project-alpha", "to": "alpha",
             "example": {"in": "project-alpha", "out": "alpha"},
             "why": "the general form, LAST on purpose"},
        ], _fh)
    sys.path.insert(0, HERE)
    import identity_rules                                     # noqa: E402
    DEFAULT_REFUSE_RULES, DEFAULT_REWRITE_RULES, _ip, _n = \
        identity_rules.effective_rule_files(
            _rules_dir,
            identity_file=os.path.join(HERE, "fixtures", "identity-fixture.md"),
            rewrites_file=_rewrite_fixture)
    print("  rules: the shipped generic set + {} invented term(s) from {}".format(_n, _ip))
    git_before = _git_status()
    me = os.path.abspath(__file__)
    tmp_dirs = []

    def new_dir(prefix):
        d = tempfile.mkdtemp(prefix=prefix)
        tmp_dirs.append(d)
        return d

    # [Build 2, 2026-08-05] TEST ISOLATION: point the HMAC key at a throwaway path for
    # the WHOLE selftest run (including every subprocess spawn below, which inherits
    # os.environ) so this never reads or writes the real machine secret at
    # ~/.config/lifehack/shipping-lane-hmac.key -- mirrors judge.py's own selftest.
    _old_key_env = os.environ.get("SHIPPING_LANE_HMAC_KEY_PATH")
    _test_key_dir = tempfile.mkdtemp(prefix="push-gate-selftest-hmackey-")
    os.environ["SHIPPING_LANE_HMAC_KEY_PATH"] = os.path.join(_test_key_dir, "test.key")

    try:
        # -------------------------------------------------- known-bad: identity leak
        bad_tree = new_dir("push-gate-selftest-bad-")
        with open(os.path.join(bad_tree, "notes.md"), "w", encoding="utf-8") as fh:
            fh.write("Wren wrote these notes by hand.\n")
        receipt_bad = os.path.join(new_dir("push-gate-selftest-receipts-"), "receipt.json")
        verdict, rep, receipt = run_gate(
            bad_tree, DEFAULT_REFUSE_RULES, DEFAULT_REWRITE_RULES, receipt_bad,
            accept_unjudged=True)
        report("catches a planted identity leak -> REFUSED (exit-equivalent 1)",
               verdict == REFUSED and rep["refused_files"]
               and any(h["id"].startswith("identity-")
                       for f in rep["refused_files"] for h in f["hits"]))
        report("...and NO receipt is written for a REFUSED tree",
               not os.path.exists(receipt_bad))

        # -------------------------------------------------- FIX 1: the 2026-08-05
        # bypasses -- none of these are the literal byte sequence any rule names, and
        # all 17 walked straight through before this fix.
        obf_tree = new_dir("push-gate-selftest-obfuscated-")

        def plant(name, content):
            with open(os.path.join(obf_tree, name), "w", encoding="utf-8") as fh:
                fh.write(content)

        plant("dotted.md", "signed Wr.en Oak-ley\n")
        plant("newline.md", "signed Wr\nen\n")
        plant("spaced.md", "signed W r e n\n")
        plant("leet.md", "signed Wr3n 04kl3y\n")
        plant("homoglyph.md", "signed " + "Wr" + "е" + "n\n")  # Cyrillic е for e
        plant("zwj.md", "signed " + "‍".join(list("Wren")) + "\n")
        plant("nfd.md", "signed Wr\u0065\u0301n\n")  # e + combining acute
        import base64 as _b64mod, binascii as _hexmod2
        plant("b64.md", "note: " + _b64mod.b64encode(b"Wren Oakley").decode() + "\n")
        plant("hexenc.md", "note: " + _hexmod2.hexlify(b"Wren Oakley").decode() + "\n")
        plant("rot13.md", "note: " + codecs.encode("Wren Oakley", "rot_13") + "\n")
        plant("b64key.md", "cfg: " + _b64mod.b64encode(
            b"sk-ant-FAKEFAKEFAKEFAKEFAKE12345678").decode() + "\n")
        plant("urlemail.md", "reach " + "".join(
            "%{:02X}".format(ord(c)) for c in "wren.oakley@example.com") + "\n")
        # second hardening pass, 2026-08-05 (same day, second red-team)
        plant("bidi.md", "signed " + "‮" + "nerW" + "‬" + "\n")
        plant("tagchars.md", "notes" + "".join(
            chr(0xE0000 + ord(c)) for c in "wren oakley") + "\n")
        plant("smallcaps.md", "signed ᴡʀᴇɴ ᴏᴀᴋʟᴇʏ\n")
        plant("b64x2.md", "note: " + _b64mod.b64encode(
            _b64mod.b64encode(b"Wren Oakley")).decode() + "\n")
        plant("base32key.md", "cfg: " + _b64mod.b32encode(
            b"sk-ant-FAKEFAKEFAKEFAKEFAKE12345678").decode() + "\n")
        plant("qpemail.md", "reach " + "".join(
            "={:02X}".format(b) for b in "wren.oakley@example.com".encode()) + "\n")

        verdict, rep, receipt = run_gate(
            obf_tree, DEFAULT_REFUSE_RULES, DEFAULT_REWRITE_RULES, None,
            accept_unjudged=True)
        refused_paths = {f["path"] for f in rep["refused_files"]}
        expect_all = {"dotted.md", "newline.md", "spaced.md", "leet.md", "homoglyph.md",
                      "zwj.md", "nfd.md", "b64.md", "hexenc.md", "rot13.md",
                      "b64key.md", "urlemail.md", "bidi.md", "tagchars.md",
                      "smallcaps.md", "b64x2.md", "base32key.md", "qpemail.md"}
        report("every one of the 18 known 2026-08-05 bypass shapes (both red-team "
               "passes) is now REFUSED",
               verdict == REFUSED and expect_all <= refused_paths,
               "missing: {}".format(sorted(expect_all - refused_paths)))

        # -------------------------------------------------- FIX 2: high-entropy blob
        entropy_tree = new_dir("push-gate-selftest-entropy-")
        with open(os.path.join(entropy_tree, "config.md"), "w", encoding="utf-8") as fh:
            fh.write("token: " + secrets.token_urlsafe(32) + "\n")
        verdict, rep, receipt = run_gate(
            entropy_tree, DEFAULT_REFUSE_RULES, DEFAULT_REWRITE_RULES, None,
            accept_unjudged=True)
        report("an unknown-format high-entropy secret is REFUSED (no literal rule "
               "names its format)",
               verdict == REFUSED
               and any(h["id"] == "high-entropy-blob"
                       for f in rep["refused_files"] for h in f["hits"]))

        # -------------------------------------------------- known-good: clean tree
        good_tree = new_dir("push-gate-selftest-good-")
        with open(os.path.join(good_tree, "readme.md"), "w", encoding="utf-8") as fh:
            fh.write("Ask Claude to help. Claude Code runs locally on your machine.\n")
        receipt_good_dir = new_dir("push-gate-selftest-receipts-")
        receipt_good = os.path.join(receipt_good_dir, "receipt.json")
        verdict, rep, receipt = run_gate(
            good_tree, DEFAULT_REFUSE_RULES, DEFAULT_REWRITE_RULES, receipt_good,
            accept_unjudged=True)
        report("passes a genuinely clean tree -> CLEAN (exit-equivalent 0)",
               verdict == CLEAN)
        report("...and a receipt is written and is valid JSON with the right schema",
               os.path.isfile(receipt_good)
               and json.load(open(receipt_good))["schema"] == RECEIPT_SCHEMA)
        report("receipt records the right file_count and a matching tree_sha256",
               receipt["file_count"] == 1
               and receipt["tree_sha256"] == sha256_bytes(canonical_json(receipt["files"])))

        # -------------------------------------------------- FIX 3: the receipt no longer
        # overclaims -- verdict is NO-LITERAL-MATCH, never the unearned word "CLEAN", and
        # the receipt states its own bounds on its face.
        report("the receipt's verdict reads NO-LITERAL-MATCH(-UNJUDGED), never the "
               "unearned 'CLEAN'",
               receipt["verdict"] in (VERDICT_LABEL, VERDICT_LABEL_UNJUDGED)
               and receipt["verdict"] != "CLEAN")
        report("the receipt carries a 'bounds' field naming what was and was NOT checked",
               isinstance(receipt.get("bounds"), dict)
               and receipt["bounds"].get("checked") and receipt["bounds"].get("NOT_checked"))

        # -------------------------------------------------- BUILD 1: --accept-unjudged
        # marks the receipt honestly -- judged:false, the UNJUDGED verdict label, never
        # the earned "NO-LITERAL-MATCH".
        report("--accept-unjudged run: the push receipt records judged:false",
               receipt["judged"] is False and receipt["judge"]["judged"] is False)
        report("--accept-unjudged run: this file's OWN verdict label is "
               "NO-LITERAL-MATCH-UNJUDGED, not the earned NO-LITERAL-MATCH",
               rep["verdict"] == VERDICT_LABEL_UNJUDGED)
        report("--accept-unjudged run: the RECEIPT's verdict field matches too",
               receipt["verdict"] == VERDICT_LABEL_UNJUDGED)

        # -------------------------------------------------- rewrite survivor, non-blocking
        brand_tree = new_dir("push-gate-selftest-brand-")
        with open(os.path.join(brand_tree, "config.md"), "w", encoding="utf-8") as fh:
            fh.write("repo: project-alpha-repo -- no personal data in this file.\n")
        receipt_brand = os.path.join(new_dir("push-gate-selftest-receipts-"), "receipt.json")
        verdict, rep, receipt = run_gate(
            brand_tree, DEFAULT_REFUSE_RULES, DEFAULT_REWRITE_RULES, receipt_brand,
            accept_unjudged=True)
        report("a leftover REWRITE-tier string with NO personal data -> CLEAN, not "
               "blocked (rail 1: personal data always blocks, a cosmetic leftover never "
               "does -- a gate that blocks on a typo is a gate that gets waved through)",
               verdict == CLEAN)
        report("...and the report NAMES the survivor (loud, not silent)",
               any(s["id"] == "specific-first" and s["path"] == "config.md"
                   for s in rep["rewrite_survivors"]))
        report("...and a receipt IS written despite the survivor",
               os.path.isfile(receipt_brand))
        rendered = render_report(rep, receipt_brand)
        report("...and the human report text actually names the surviving rule",
               "specific-first" in rendered and "NOT blocking" in rendered)

        # -------------------------------------------------- empty tree
        empty_tree = new_dir("push-gate-selftest-empty-")
        try:
            run_gate(empty_tree, DEFAULT_REFUSE_RULES, DEFAULT_REWRITE_RULES, None,
                     accept_unjudged=True)
            report("an empty staging tree -> CANNOT EVALUATE, never CLEAN", False,
                   "no exception raised")
        except CannotEvaluate:
            report("an empty staging tree -> CANNOT EVALUATE, never CLEAN", True)

        # -------------------------------------------------- binary file present
        binary_tree = new_dir("push-gate-selftest-binary-")
        with open(os.path.join(binary_tree, "clean.md"), "w", encoding="utf-8") as fh:
            fh.write("nothing sensitive here.\n")
        with open(os.path.join(binary_tree, "blob.bin"), "wb") as fh:
            fh.write(bytes([0xFF, 0xFE, 0x00, 0x80, 0x01, 0x02]))
        try:
            run_gate(binary_tree, DEFAULT_REFUSE_RULES, DEFAULT_REWRITE_RULES, None,
                     accept_unjudged=True)
            report("a binary/non-UTF-8 file -> CANNOT EVALUATE, never a crash, never a pass",
                   False, "no exception raised")
        except CannotEvaluate as e:
            report("a binary/non-UTF-8 file -> CANNOT EVALUATE, never a crash, never a pass",
                   "blob.bin" in str(e))
        except Exception as e:  # pragma: no cover -- would itself be the finding
            report("a binary/non-UTF-8 file -> CANNOT EVALUATE, never a crash, never a pass",
                   False, "raised {} instead of CannotEvaluate: {}".format(type(e).__name__, e))

        # -------------------------------------------------- symlinked directory
        symlink_tree = new_dir("push-gate-selftest-symlink-")
        with open(os.path.join(symlink_tree, "clean.md"), "w", encoding="utf-8") as fh:
            fh.write("nothing sensitive here.\n")
        real_sub = new_dir("push-gate-selftest-symlink-target-")
        with open(os.path.join(real_sub, "hidden.md"), "w", encoding="utf-8") as fh:
            fh.write("Wren -- this would be invisible if the symlink were followed silently.\n")
        os.symlink(real_sub, os.path.join(symlink_tree, "linked"))
        try:
            run_gate(symlink_tree, DEFAULT_REFUSE_RULES, DEFAULT_REWRITE_RULES, None,
                     accept_unjudged=True)
            report("a symlinked directory is refused, never silently skipped", False,
                   "no exception raised")
        except CannotEvaluate as e:
            report("a symlinked directory is refused, never silently skipped",
                   "linked" in str(e) or "symlinked" in str(e))

        # -------------------------------------------------- unreadable (dangling symlink)
        unreadable_tree = new_dir("push-gate-selftest-unreadable-")
        with open(os.path.join(unreadable_tree, "clean.md"), "w", encoding="utf-8") as fh:
            fh.write("nothing sensitive here.\n")
        os.symlink(os.path.join(unreadable_tree, "does-not-exist.txt"),
                   os.path.join(unreadable_tree, "dangling.txt"))
        try:
            run_gate(unreadable_tree, DEFAULT_REFUSE_RULES, DEFAULT_REWRITE_RULES, None,
                     accept_unjudged=True)
            report("an unreadable file (dangling symlink) -> CANNOT EVALUATE", False,
                   "no exception raised")
        except CannotEvaluate as e:
            report("an unreadable file (dangling symlink) -> CANNOT EVALUATE",
                   "dangling.txt" in str(e))

        # -------------------------------------------------- FIX 4: a FIFO in the tree
        fifo_tree = new_dir("push-gate-selftest-fifo-")
        with open(os.path.join(fifo_tree, "clean.md"), "w", encoding="utf-8") as fh:
            fh.write("nothing sensitive here.\n")
        fifo_path = os.path.join(fifo_tree, "a.fifo")
        os.mkfifo(fifo_path)
        # run it as a subprocess with a hard wall-clock timeout: if the stat-before-open
        # fix regresses, open() on the FIFO blocks forever (no reader on the other end),
        # and this proves the "no hang" property rather than just the "right exit code"
        # one -- a bare in-process call could look like a pass right up until it hangs.
        try:
            p = subprocess.run(
                [sys.executable, me, "--refuse-rules", DEFAULT_REFUSE_RULES, "--rewrite-rules", DEFAULT_REWRITE_RULES, "--tree", fifo_tree, "--accept-unjudged"],
                capture_output=True, text=True, timeout=10)
            report("a FIFO in the tree -> exit 2 promptly, never a hang",
                   p.returncode == CANNOT_EVALUATE and "fifo" in p.stderr.lower(),
                   "got exit {}, stderr: {}".format(p.returncode, p.stderr.strip()[:200]))
        except subprocess.TimeoutExpired:
            report("a FIFO in the tree -> exit 2 promptly, never a hang", False,
                   "HUNG past the 10s timeout -- open() was called on the FIFO")

        # -------------------------------------------------- missing rules file
        try:
            run_gate(good_tree, os.path.join(good_tree, "nope-rules.json"),
                      DEFAULT_REWRITE_RULES, None, accept_unjudged=True)
            report("a missing refuse-rules file -> CANNOT EVALUATE", False,
                   "no exception raised")
        except CannotEvaluate:
            report("a missing refuse-rules file -> CANNOT EVALUATE", True)

        # -------------------------------------------------- missing / non-dir tree
        try:
            run_gate(os.path.join(good_tree, "does-not-exist"),
                      DEFAULT_REFUSE_RULES, DEFAULT_REWRITE_RULES, None, accept_unjudged=True)
            report("a missing staging tree path -> CANNOT EVALUATE", False,
                   "no exception raised")
        except CannotEvaluate:
            report("a missing staging tree path -> CANNOT EVALUATE", True)

        # -------------------------------------------------- --check-receipt: valid case
        findings = check_receipt(receipt_good, tree_override=good_tree)
        report("check-receipt on an untouched tree -> VALID (no findings)",
               findings == [], "findings: {}".format(findings))

        # -------------------------------------------------- --check-receipt: tamper (byte edit)
        target_file = os.path.join(good_tree, "readme.md")
        original_bytes = open(target_file, "rb").read()
        flipped_byte = bytes([(original_bytes[0] + 1) % 256])
        with open(target_file, "r+b") as fh:
            fh.seek(0)
            fh.write(flipped_byte)  # guaranteed to differ from the original first byte
        findings = check_receipt(receipt_good, tree_override=good_tree)
        report("modifying ONE byte of a gated file -> check-receipt FAILS",
               any("readme.md" in f and "modified" in f for f in findings),
               "findings: {}".format(findings))
        with open(target_file, "wb") as fh:
            fh.write(original_bytes)
        findings = check_receipt(receipt_good, tree_override=good_tree)
        report("...and restoring the byte makes it VALID again",
               findings == [], "findings: {}".format(findings))

        # -------------------------------------------------- --check-receipt: hand-edited receipt
        tampered_receipt_path = os.path.join(receipt_good_dir, "tampered.json")
        rdata = json.load(open(receipt_good))
        rdata["verdict"] = "CLEAN-BUT-EDITED"  # change a field, do NOT recompute the hash
        with open(tampered_receipt_path, "w", encoding="utf-8") as fh:
            json.dump(rdata, fh)
        findings = check_receipt(tampered_receipt_path, tree_override=good_tree)
        report("a hand-edited receipt field (self-hash now wrong) -> check-receipt FAILS",
               any("integrity hash mismatch" in f for f in findings))

        # -------------------------------------------------- --check-receipt: missing receipt/tree
        try:
            check_receipt(os.path.join(receipt_good_dir, "nope.json"))
            report("check-receipt on a missing receipt file -> CANNOT EVALUATE", False,
                   "no exception raised")
        except CannotEvaluate:
            report("check-receipt on a missing receipt file -> CANNOT EVALUATE", True)

        try:
            check_receipt(receipt_good, tree_override=os.path.join(good_tree, "gone"))
            report("check-receipt against a tree that no longer exists -> CANNOT EVALUATE",
                   False, "no exception raised")
        except CannotEvaluate:
            report("check-receipt against a tree that no longer exists -> CANNOT EVALUATE",
                   True)

        # -------------------------------------------------- end-to-end via the real CLI
        p = subprocess.run(
            [sys.executable, me, "--refuse-rules", DEFAULT_REFUSE_RULES, "--rewrite-rules", DEFAULT_REWRITE_RULES, "--tree", bad_tree, "--accept-unjudged", "--json"],
            capture_output=True, text=True)
        report("CLI: identity leak in tree -> exit 1", p.returncode == REFUSED,
               "got exit {}".format(p.returncode))

        cli_receipt_dir = new_dir("push-gate-selftest-cli-receipts-")
        cli_receipt = os.path.join(cli_receipt_dir, "r.json")
        clean_tree2 = new_dir("push-gate-selftest-clean2-")
        with open(os.path.join(clean_tree2, "a.md"), "w", encoding="utf-8") as fh:
            fh.write("Claude Code runs on your own machine.\n")
        p = subprocess.run([sys.executable, me, "--refuse-rules", DEFAULT_REFUSE_RULES, "--rewrite-rules", DEFAULT_REWRITE_RULES, "--tree", clean_tree2, "--accept-unjudged",
                             "--receipt", cli_receipt], capture_output=True, text=True)
        report("CLI: clean tree -> exit 0 and a receipt file appears",
               p.returncode == CLEAN and os.path.isfile(cli_receipt),
               "got exit {}".format(p.returncode))

        p = subprocess.run([sys.executable, me, "--refuse-rules", DEFAULT_REFUSE_RULES, "--rewrite-rules", DEFAULT_REWRITE_RULES, "--tree", empty_tree, "--accept-unjudged"],
                            capture_output=True, text=True)
        report("CLI: empty tree -> exit 2, never 0", p.returncode == CANNOT_EVALUATE,
               "got exit {}".format(p.returncode))

        # -------------------------------------------------- BUILD 1: no judge receipt,
        # no --accept-unjudged -> CANNOT EVALUATE, both via the CLI and the function
        p = subprocess.run([sys.executable, me, "--refuse-rules", DEFAULT_REFUSE_RULES, "--rewrite-rules", DEFAULT_REWRITE_RULES, "--tree", clean_tree2],
                            capture_output=True, text=True)
        report("CLI: --tree with NEITHER --judge-receipt NOR --accept-unjudged -> "
               "exit 2 (the gate structurally cannot bless an unjudged tree)",
               p.returncode == CANNOT_EVALUATE, "got exit {}".format(p.returncode))
        try:
            run_gate(clean_tree2, DEFAULT_REFUSE_RULES, DEFAULT_REWRITE_RULES, None)
            report("run_gate() with neither judge_receipt_path nor accept_unjudged "
                   "-> CannotEvaluate", False, "no exception raised")
        except CannotEvaluate as e:
            report("run_gate() with neither judge_receipt_path nor accept_unjudged "
                   "-> CannotEvaluate", "judge" in str(e).lower())

        p = subprocess.run([sys.executable, me], capture_output=True, text=True)
        report("CLI: missing --tree and --check-receipt -> exit 2",
               p.returncode == CANNOT_EVALUATE, "got exit {}".format(p.returncode))

        p = subprocess.run([sys.executable, me, "--refuse-rules", DEFAULT_REFUSE_RULES, "--rewrite-rules", DEFAULT_REWRITE_RULES, "--check-receipt", cli_receipt,
                             "--tree", clean_tree2], capture_output=True, text=True)
        report("CLI: --check-receipt on an untouched tree -> exit 0",
               p.returncode == CLEAN, "got exit {}".format(p.returncode))

        with open(os.path.join(clean_tree2, "a.md"), "a", encoding="utf-8") as fh:
            fh.write("one more line\n")
        p = subprocess.run([sys.executable, me, "--refuse-rules", DEFAULT_REFUSE_RULES, "--rewrite-rules", DEFAULT_REWRITE_RULES, "--check-receipt", cli_receipt,
                             "--tree", clean_tree2], capture_output=True, text=True)
        report("CLI: --check-receipt after the tree changed -> exit 1",
               p.returncode == REFUSED, "got exit {}".format(p.returncode))

        # move_aside is exercised for real: writing a SECOND receipt to the same path
        # must not silently clobber -- it must succeed (move_aside preserves the old one)
        verdict, rep2, receipt2 = run_gate(
            good_tree, DEFAULT_REFUSE_RULES, DEFAULT_REWRITE_RULES, receipt_good,
            accept_unjudged=True)
        prev_files = [f for f in os.listdir(receipt_good_dir) if ".prev" in f]
        report("re-writing a receipt to the same path preserves the old generation "
               "(move_aside, never a silent clobber)",
               verdict == CLEAN and len(prev_files) >= 1,
               "prev files: {}".format(prev_files))

        # ============================================================================
        # BUILD 1: full judge-gate integration, end to end through the REAL judge.py
        # ============================================================================
        JUDGE_PY = os.path.join(HERE, "judge.py")

        judge_tree = new_dir("push-gate-selftest-judge-")
        with open(os.path.join(judge_tree, "one.md"), "w", encoding="utf-8") as fh:
            fh.write("Plain content, nothing hunted here.\n")
        with open(os.path.join(judge_tree, "two.md"), "w", encoding="utf-8") as fh:
            fh.write("More plain content.\n")

        judge_out = new_dir("push-gate-selftest-judge-out-")
        p = subprocess.run(
            [sys.executable, JUDGE_PY, "--prepare", "--staging", judge_tree,
             "--out", judge_out, "--json"], capture_output=True, text=True)
        report("judge.py --prepare against the happy-path tree succeeds",
               p.returncode == 0, "stderr: {}".format(p.stderr.strip()[:200]))
        judge_manifest = json.loads(p.stdout)
        judge_manifest_path = os.path.join(judge_out, "manifest.json")

        # `outcome` became REQUIRED when judge.py gained its NO-OUTCOME member
        # (CLEAN / FINDINGS / NOT-EVALUATED, commit e0debaa). Omitting it here is
        # not a shortcut -- judge.py correctly refuses a bundle with no outcome,
        # because a missing outcome cannot be told apart from one nobody judged.
        clean_verdicts = {"bundles": [
            {"bundle_id": b["bundle_id"], "reviewed_files": list(b["files"]),
             "outcome": "CLEAN", "findings": [], "disputes": []}
            for b in judge_manifest["bundles"]
        ]}
        judge_verdicts_path = os.path.join(judge_out, "verdicts.json")
        with open(judge_verdicts_path, "w", encoding="utf-8") as fh:
            json.dump(clean_verdicts, fh)

        judge_scrub_report = {
            "staging_root": judge_manifest["staging_root"],
            "files": [{"source": n, "status": "CLEAN", "refuse": {"unresolved": []}}
                      for n in judge_manifest["all_files"]],
        }
        judge_scrub_report_path = os.path.join(judge_out, "scrub-report.json")
        with open(judge_scrub_report_path, "w", encoding="utf-8") as fh:
            json.dump(judge_scrub_report, fh)

        judge_receipt_path = os.path.join(judge_out, "judge-receipt.json")
        p = subprocess.run(
            [sys.executable, JUDGE_PY, "--consume", judge_verdicts_path,
             "--manifest", judge_manifest_path, "--scrub-report", judge_scrub_report_path,
             "--receipt", judge_receipt_path],
            capture_output=True, text=True)
        report("judge.py --consume --receipt on the happy-path tree -> exit 0, receipt "
               "written",
               p.returncode == 0 and os.path.isfile(judge_receipt_path),
               "stderr: {}".format(p.stderr.strip()[:200]))

        push_receipt_path = os.path.join(judge_out, "push-receipt.json")
        p = subprocess.run(
            [sys.executable, me, "--refuse-rules", DEFAULT_REFUSE_RULES, "--rewrite-rules", DEFAULT_REWRITE_RULES, "--tree", judge_tree, "--judge-receipt",
             judge_receipt_path, "--receipt", push_receipt_path, "--json"],
            capture_output=True, text=True)
        report("HAPPY PATH: push_gate --judge-receipt against a genuinely-judged, "
               "mechanically-clean tree -> exit 0", p.returncode == CLEAN,
               "got exit {}, stderr {}".format(p.returncode, p.stderr.strip()[:300]))
        push_out = json.loads(p.stdout) if p.stdout.strip() else {}
        report("...verdict is the EARNED NO-LITERAL-MATCH, not the unjudged label",
               push_out.get("verdict") == VERDICT_LABEL)
        written_push_receipt = (json.load(open(push_receipt_path))
                                if os.path.isfile(push_receipt_path) else {})
        report("...and the push receipt's judge block is populated (judged=true, "
               "points at the judge receipt actually used, verdict JUDGED-CLEAN)",
               written_push_receipt.get("judged") is True
               and written_push_receipt.get("judge", {}).get("judge_verdict")
               == "JUDGED-CLEAN"
               and written_push_receipt.get("judge", {}).get("judge_receipt_path")
               == os.path.abspath(judge_receipt_path))

        # ---------------------------------------------------------------- STALENESS --
        # the test that matters most: a file added to the tree AFTER the judge receipt
        # was built must invalidate it.
        added_after_path = os.path.join(judge_tree, "three-added-after-judging.md")
        with open(added_after_path, "w", encoding="utf-8") as fh:
            fh.write("this file was never judged\n")
        p = subprocess.run(
            [sys.executable, me, "--refuse-rules", DEFAULT_REFUSE_RULES, "--rewrite-rules", DEFAULT_REWRITE_RULES, "--tree", judge_tree, "--judge-receipt",
             judge_receipt_path], capture_output=True, text=True)
        report("STALENESS: adding a file to the tree after judging -> push_gate "
               "CANNOT EVALUATE (exit 2), never a silent pass",
               p.returncode == CANNOT_EVALUATE and "stale" in p.stderr.lower(),
               "got exit {}, stderr {}".format(p.returncode, p.stderr.strip()[:300]))
        os.remove(added_after_path)

        # ------------------------------------------------------------ JUDGE FINDINGS --
        # a bio with ZERO hunted strings, caught ONLY by the judge -- this file's own
        # scan is structurally blind to it, exactly the red-team's finding.
        # outcome must AGREE with the findings list -- judge.py rejects
        # FINDINGS-with-none and CLEAN-with-some, so the bundle carrying the
        # planted finding says FINDINGS and every other bundle says CLEAN.
        judge_findings_verdicts = {"bundles": [
            {"bundle_id": b["bundle_id"], "reviewed_files": list(b["files"]),
             "outcome": ("FINDINGS" if "one.md" in b["files"] else "CLEAN"),
             "findings": (
                 [{"file": "one.md", "category": "assumed-context", "severity": "high",
                   "quote": "Plain content, nothing hunted here.",
                   "why": "reads as written by the tool's specific author, not a "
                          "generic student install"}]
                 if "one.md" in b["files"] else []),
             "disputes": []}
            for b in judge_manifest["bundles"]
        ]}
        judge_findings_verdicts_path = os.path.join(judge_out, "verdicts-findings.json")
        with open(judge_findings_verdicts_path, "w", encoding="utf-8") as fh:
            json.dump(judge_findings_verdicts, fh)
        judge_findings_receipt_path = os.path.join(
            judge_out, "judge-receipt-findings.json")
        p = subprocess.run(
            [sys.executable, JUDGE_PY, "--consume", judge_findings_verdicts_path,
             "--manifest", judge_manifest_path, "--scrub-report", judge_scrub_report_path,
             "--receipt", judge_findings_receipt_path],
            capture_output=True, text=True)
        report("judge.py --consume --receipt with a genuine judge finding -> exit 1, "
               "receipt still written",
               p.returncode == 1 and os.path.isfile(judge_findings_receipt_path))

        p = subprocess.run(
            [sys.executable, me, "--refuse-rules", DEFAULT_REFUSE_RULES, "--rewrite-rules", DEFAULT_REWRITE_RULES, "--tree", judge_tree, "--judge-receipt",
             judge_findings_receipt_path, "--json"], capture_output=True, text=True)
        report("JUDGE FINDINGS: a tree with ZERO literal/canonical/decoded matches but "
               "a real judge finding -> push_gate REFUSES (exit 1) -- the red-team's "
               "meaning-blind-bio scenario, now unreachable",
               p.returncode == REFUSED, "got exit {}".format(p.returncode))
        judge_refused_out = json.loads(p.stdout) if p.stdout.strip() else {}
        report("...and the report attributes the refusal to the JUDGE, not this "
               "file's own (blind, in this case) mechanical scan",
               judge_refused_out.get("refused_because") == ["judge"])

        # --------------------------------------------------------- TAMPERED receipt --
        tampered_judge_receipt_path = os.path.join(
            judge_out, "judge-receipt-tampered.json")
        jr = json.load(open(judge_receipt_path))
        jr["summary"]["findings_present"] = True  # tamper a field, do NOT fix the hash
        with open(tampered_judge_receipt_path, "w", encoding="utf-8") as fh:
            json.dump(jr, fh)
        p = subprocess.run(
            [sys.executable, me, "--refuse-rules", DEFAULT_REFUSE_RULES, "--rewrite-rules", DEFAULT_REWRITE_RULES, "--tree", judge_tree, "--judge-receipt",
             tampered_judge_receipt_path], capture_output=True, text=True)
        report("a hand-edited judge receipt (self-hash now wrong) -> push_gate CANNOT "
               "EVALUATE, never trusted",
               p.returncode == CANNOT_EVALUATE and "integrity" in p.stderr.lower(),
               "got exit {}, stderr {}".format(p.returncode, p.stderr.strip()[:300]))

        # ----------------------------------------------------- MISSING receipt path --
        p = subprocess.run(
            [sys.executable, me, "--refuse-rules", DEFAULT_REFUSE_RULES, "--rewrite-rules", DEFAULT_REWRITE_RULES, "--tree", judge_tree, "--judge-receipt",
             os.path.join(judge_out, "nope.json")], capture_output=True, text=True)
        report("a --judge-receipt path that does not exist -> push_gate CANNOT EVALUATE",
               p.returncode == CANNOT_EVALUATE)

        # ============================================================================
        # BUILD 2 (2026-08-05, forgery red-team): THE FORGERY ITSELF, re-run, plus HMAC
        # verification, missing-key, and zero-coverage tests.
        # ============================================================================

        # -------------------------------------------------- THE FORGERY, reproduced
        # verbatim: canon.compute_tree_state + a hand-built summary + an UNKEYED
        # self-hash. Pre-Build-2 this satisfied every check and produced exit 0,
        # verdict NO-LITERAL-MATCH, judged:true, over a tree never actually judged.
        forged_receipt_path = os.path.join(judge_out, "judge-receipt-FORGED.json")
        _, forged_tree_hash, _, _ = canon.compute_tree_state(judge_tree)
        forged_body = {"schema": JUDGE_RECEIPT_SCHEMA, "tree_sha256": forged_tree_hash,
                       "summary": {"findings_present": False}}
        forged_body["receipt_sha256"] = canon.sha256_bytes(
            canon.canonical_json(forged_body))
        with open(forged_receipt_path, "w", encoding="utf-8") as fh:
            json.dump(forged_body, fh)
        forged_push_receipt = os.path.join(judge_out, "push-receipt-forged.json")
        p = subprocess.run(
            [sys.executable, me, "--refuse-rules", DEFAULT_REFUSE_RULES, "--rewrite-rules", DEFAULT_REWRITE_RULES, "--tree", judge_tree, "--judge-receipt",
             forged_receipt_path, "--receipt", forged_push_receipt],
            capture_output=True, text=True)
        report("THE FORGERY (red-team's 4-line hand-built receipt: tree hash + fake "
               "summary + unkeyed self-hash, NEVER running judge.py or a model) -> "
               "push_gate now CANNOT EVALUATE (exit 2), NO receipt written -- the hole "
               "this build closes",
               p.returncode == CANNOT_EVALUATE and not os.path.isfile(forged_push_receipt),
               "got exit {}, stderr {}".format(p.returncode, p.stderr.strip()[:300]))

        # -------------------------------------------------- HALF A: key missing at gate
        # time. Override the env var for THIS ONE subprocess call only (not the whole
        # suite) so the rest of the run keeps using the isolated test key.
        env_no_key = dict(os.environ)
        env_no_key["SHIPPING_LANE_HMAC_KEY_PATH"] = os.path.join(
            judge_out, "no-such-key-file")
        p = subprocess.run(
            [sys.executable, me, "--refuse-rules", DEFAULT_REFUSE_RULES, "--rewrite-rules", DEFAULT_REWRITE_RULES, "--tree", judge_tree, "--judge-receipt",
             judge_receipt_path], capture_output=True, text=True, env=env_no_key)
        report("HALF A: HMAC key missing at gate time -> push_gate CANNOT EVALUATE "
               "(exit 2), never a silent unauthenticated pass",
               p.returncode == CANNOT_EVALUATE and "hmac key" in p.stderr.lower(),
               "got exit {}, stderr {}".format(p.returncode, p.stderr.strip()[:300]))

        # -------------------------------------------------- HALF A: tampered signature
        # (flip one char) -- the body (and hence receipt_sha256) is untouched, so this
        # isolates the HMAC check specifically from the plain self-hash check.
        tampered_hmac_path = os.path.join(judge_out, "judge-receipt-tampered-hmac.json")
        jr_hmac = json.load(open(judge_receipt_path, encoding="utf-8"))
        c0 = jr_hmac["receipt_hmac_sha256"][0]
        jr_hmac["receipt_hmac_sha256"] = ("0" if c0 != "0" else "1") + \
            jr_hmac["receipt_hmac_sha256"][1:]
        with open(tampered_hmac_path, "w", encoding="utf-8") as fh:
            json.dump(jr_hmac, fh)
        p = subprocess.run(
            [sys.executable, me, "--refuse-rules", DEFAULT_REFUSE_RULES, "--rewrite-rules", DEFAULT_REWRITE_RULES, "--tree", judge_tree, "--judge-receipt",
             tampered_hmac_path], capture_output=True, text=True)
        report("HALF A: a judge receipt with ONE character flipped in its HMAC "
               "signature -> push_gate CANNOT EVALUATE, never trusted",
               p.returncode == CANNOT_EVALUATE and "signature" in p.stderr.lower(),
               "got exit {}, stderr {}".format(p.returncode, p.stderr.strip()[:300]))

        # -------------------------------------------------- HALF B: a VALIDLY SIGNED
        # receipt claiming zero reviewed files. judge.build_judge_receipt() itself
        # refuses to construct one (see judge.py's own selftest) -- this proves
        # push_gate.py ALSO refuses to trust one independently, even if an operator
        # (who holds the same key judge.py does -- the documented bound HMAC does not
        # cover) hand-assembles and genuinely signs one.
        zero_cov_path = os.path.join(judge_out, "judge-receipt-zerocov.json")
        zero_cov_receipt = json.load(open(judge_receipt_path, encoding="utf-8"))
        zero_cov_receipt["bundle_coverage"] = [{"bundle_id": "bundle-0001",
                                                "file_count": 0}]
        zero_cov_receipt["total_reviewed_files"] = 0
        zero_body = {k: v for k, v in zero_cov_receipt.items()
                    if k not in ("receipt_sha256", "receipt_hmac_sha256")}
        zero_canon_bytes = canon.canonical_json(zero_body)
        zero_body["receipt_sha256"] = canon.sha256_bytes(zero_canon_bytes)
        real_key = judge._load_or_create_hmac_key()
        zero_body["receipt_hmac_sha256"] = hmac.new(
            real_key, zero_canon_bytes, hashlib.sha256).hexdigest()
        with open(zero_cov_path, "w", encoding="utf-8") as fh:
            json.dump(zero_body, fh)
        p = subprocess.run(
            [sys.executable, me, "--refuse-rules", DEFAULT_REFUSE_RULES, "--rewrite-rules", DEFAULT_REWRITE_RULES, "--tree", judge_tree, "--judge-receipt", zero_cov_path],
            capture_output=True, text=True)
        report("HALF B: a VALIDLY SIGNED receipt claiming ZERO reviewed files -> "
               "push_gate CANNOT EVALUATE, never a pass -- an empty judgment is never "
               "a clean one",
               p.returncode == CANNOT_EVALUATE and "zero" in p.stderr.lower(),
               "got exit {}, stderr {}".format(p.returncode, p.stderr.strip()[:300]))

    finally:
        for d in tmp_dirs:
            import shutil
            shutil.rmtree(d, ignore_errors=True)
        if _old_key_env is None:
            os.environ.pop("SHIPPING_LANE_HMAC_KEY_PATH", None)
        else:
            os.environ["SHIPPING_LANE_HMAC_KEY_PATH"] = _old_key_env
        import shutil
        shutil.rmtree(_test_key_dir, ignore_errors=True)

    git_after = _git_status()
    report("git status --porcelain in the clone is unchanged by the whole selftest run",
           git_before == git_after,
           "differs -- either a real leak into the repo or a concurrent edit elsewhere"
           if git_before != git_after else "")

    print("SELFTEST:", "PASS" if ok_all else "FAIL")
    return CLEAN if ok_all else REFUSED


# --------------------------------------------------------------------------------- CLI

def main():
    ap = argparse.ArgumentParser(
        description="push_gate -- the shipping lane's last gate before git push")
    ap.add_argument("--tree", help="the staging tree to gate (every file under it, "
                                   "recursively); also usable as an override for "
                                   "--check-receipt's recorded tree_root")
    ap.add_argument("--refuse-rules", help="an already-composed effective refuse set; "
                                           "default: compose it from your identity file")
    ap.add_argument("--rewrite-rules", help="an already-composed effective rewrite set")
    ap.add_argument("--identity", help="compile the personal tier from this identity file "
                                       "instead of the one in your notes")
    ap.add_argument("--receipt", help="write the receipt JSON here on a CLEAN verdict; "
                                      "omit for a dry run (nothing on disk certifies it)")
    ap.add_argument("--judge-receipt", metavar="JUDGE_RECEIPT_PATH",
                     help="[Build 1] a receipt from `judge.py --consume --receipt "
                          "PATH`, pinned by tree hash to the exact tree it judged -- "
                          "required unless --accept-unjudged is given")
    ap.add_argument("--accept-unjudged", action="store_true",
                     help="[Build 1] ESCAPE HATCH: deliberately waive the judgment "
                          "pass. Never silent -- prints a loud warning and marks the "
                          "push receipt judged:false, verdict NO-LITERAL-MATCH-UNJUDGED")
    ap.add_argument("--check-receipt", metavar="RECEIPT_PATH",
                     help="re-validate a previously written receipt instead of gating "
                          "a tree")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())

    if args.check_receipt:
        try:
            findings = check_receipt(args.check_receipt, tree_override=args.tree)
        except CannotEvaluate as e:
            print("CANNOT EVALUATE: {}".format(e), file=sys.stderr)
            sys.exit(CANNOT_EVALUATE)
        if args.json:
            print(json.dumps({"valid": not findings, "findings": findings}, indent=2))
        else:
            if findings:
                print("RECEIPT INVALID -- {} finding(s):".format(len(findings)))
                for f in findings:
                    print("  - {}".format(f))
            else:
                print("RECEIPT VALID -- the tree matches exactly what was gated")
        sys.exit(REFUSED if findings else CLEAN)

    try:
        if not args.tree:
            raise CannotEvaluate("--tree is required (or --check-receipt)")
        refuse_path, rewrite_path = effective_rules(
            args.refuse_rules, args.rewrite_rules, args.identity)
        verdict, report, receipt = run_gate(
            args.tree, refuse_path, rewrite_path, args.receipt,
            args.judge_receipt, args.accept_unjudged)
    except CannotEvaluate as e:
        print("CANNOT EVALUATE: {}".format(e), file=sys.stderr)
        sys.exit(CANNOT_EVALUATE)

    if args.json:
        out = dict(report)
        if receipt:
            out["receipt"] = receipt
        print(json.dumps(out, indent=2))
    else:
        print(render_report(report, report.get("receipt_written_to")))

    sys.exit(verdict)


if __name__ == "__main__":
    main()

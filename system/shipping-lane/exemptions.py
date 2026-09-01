#!/usr/bin/env python3
"""exemptions.py — the shipping lane's PATH+RULE exemption mechanism. [Shipping Lane · Y.I2]

WHY THIS EXISTS. Two REFUSE rules in `refuse-rules.json` were written ASSUMING a clearing
channel would exist, and it never got built:

  - `id-google-calendar-domain`'s own "why" field: "HONEST BOUND: documentation that
    shows the address FORM with a placeholder hash still matches, and that is intended
    -- A HUMAN CLEARS IT IN SECONDS, and the alternative is trusting that every future
    writer remembers to elide the suffix too."

  - `path-drive-cloudstorage`: matched on a bare prefix ("CloudStorage/GoogleDrive-"),
    which by construction also fires on a placeholder/example path with no real account
    in it -- the same "a human clears it" assumption, unwritten down explicitly for this
    one but structurally identical to the calendar rule's.

A prior audit of this lane found NO exemption / allowlist / suppression mechanism
anywhere -- every refuse hit, forever, requires either a hand-edit to the offending file
or a hand-edit to `refuse-rules.json` itself (which weakens the rule FOR EVERY FILE, not
just the one that was actually a false positive). This module is that missing channel,
built to the shape both rules' authors assumed existed: narrow, written, and visible.

WHAT THIS IS NOT. It is not a way to make a rule stop firing, and it is not a way to make
a whole file stop being scanned. It clears exactly one already-matched (path, rule_id)
pair, on the record, with a reason a human wrote down. Nothing here ever touches a
regex, a tier, or a "to" substitution -- see `filtered_rules()`, which removes a whole
rule from the set handed to one file's own verdict call, never edits the rule itself.

THE SHAPE, held ABSOLUTE by `_validate_entry` below (never relaxed, never silently
worked around by a caller):
  1. Every exemption is keyed on PATH *and* RULE-ID *and* carries a REQUIRED, non-blank
     `reason`. A bare path, a bare rule id, or a missing/whitespace-only reason is
     INVALID and `load_exemptions` raises loudly -- never silently dropped, never
     silently coerced into "no exemption" (which would look identical to a typo that
     quietly failed to clear anything).
  2. NO WILDCARDS, at either the path or the rule-id level. `*` and `?` are rejected
     outright in either field. An exemption matches ONE exact path against ONE exact
     rule id -- string equality only, computed in `partition_hits` below, never
     `fnmatch`/glob/regex against the exemption's own fields.
  3. An exempted hit is never dropped from the record -- `partition_hits` returns it in
     a SEPARATE list, still carrying its original id/tier/why/hits plus the reason and
     the exemption that cleared it, so every caller can (and must) fold it into its
     report/receipt. See scrub.py's `refuse.exempted` and push_gate.py's
     `exempted_files` -- a receipt that hides a cleared hit is worse than no exemption.

WHY A SEPARATE FILE, NOT A FIELD INSIDE refuse-rules.json. `refuse-rules.json` states
what is true for EVERYONE, forever, and is read by `verify_rules.py` as a fixed rule
shape. An exemption is the opposite kind of fact: it is true for exactly one path, in
one person's own tree, until a human revisits it -- stuffing it into the same document
would mean either loosening a universal rule to fit one file's exception (a false
positive on one file quietly reopens the same hole on every other file that rule would
have caught) or growing a second, incompatible object shape inside a file
`verify_rules.py` already asserts is a flat list of rule objects. A sibling data file,
loaded by a sibling loader module (mirrors `identity_rules.py`'s own relationship to
`refuse-rules.json` -- one loader, one JSON shape, imported by both scrub.py and
push_gate.py so the two gates can never disagree about what is exempted), keeps the two
kinds of fact in two places that answer two different questions.

FAIL-DIRECTION IS THE OPPOSITE OF THE REST OF THIS LANE, ON PURPOSE. Everywhere else in
the shipping lane "cannot evaluate the input" fails closed (CANNOT EVALUATE, never a
silent pass) because the input decides whether something ships. An exemptions file is
additive relief layered ON TOP of a scan that already fails closed without it: a MISSING
exemptions.json means zero exemptions, i.e. the scan behaves exactly as if this module
were never imported -- the strict, safe direction. Only a file that EXISTS and is
malformed raises (`ExemptionError`), because a human clearly meant to exempt something
and a silent partial load would leave them believing a hit was cleared when it was not.

WHAT THIS FILE DOES NOT DO. It does not decide whether a file ships (that is
scrub.py/push_gate.py's job, using this module's output). It never edits
refuse-rules.json, never edits a regex, and never suppresses the JUDGE gate or
--accept-unjudged in push_gate.py -- an exemption clears one MECHANICAL literal-rule
hit; it has no opinion on, and no effect on, a meaning-level judge finding.
"""

from __future__ import annotations

import contextlib
import json
import os
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, os.path.join(_REPO_ROOT, "shared"))
from paths import scratch_dir  # noqa: E402 -- path fixed immediately above, by design

_WILDCARD_CHARS = frozenset("*?")

# WINDOWS FOLD: a hand-typed exemption path can arrive backslash-native, drive-lettered, or
# mixed-case (a human typed it, not a program that produced it) -- same class of problem the
# system/hooks/*.sh guards solve with the shared fold helper, so this reuses it rather than
# re-rolling a partial version. Off Windows (the common case) winfold() is the identity
# function, so this changes nothing there.
_WINFOLD_LIB = os.path.join(_REPO_ROOT, "system", "hooks", "lib", "winpath_fold.py")


def _load_winfold():
    import importlib.util
    try:
        spec = importlib.util.spec_from_file_location("winpath_fold", _WINFOLD_LIB)
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


_WINFOLD = _load_winfold()


class ExemptionError(Exception):
    """Raised on any malformed exemptions.json -- callers convert this to their own
    CannotEvaluate. Never caught and swallowed inside this module."""


def load_exemptions(path):
    """Read and STRICTLY validate the exemptions file at `path`.

    A missing (or falsy) path returns [] -- see the module docstring's
    FAIL-DIRECTION note: no file means no exemptions, which is the strict/safe default
    and requires no opt-in ceremony. A file that EXISTS but is not valid JSON, is not a
    list, or contains even one malformed entry raises ExemptionError for the WHOLE file
    -- never a partial load of "the entries that happened to parse"."""
    if not path or not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as e:
        raise ExemptionError("cannot read exemptions file {!r}: {}".format(path, e))
    if not isinstance(data, list):
        raise ExemptionError(
            "{!r} must be a JSON list of exemption objects".format(path))
    validated = [_validate_entry(entry, i, path) for i, entry in enumerate(data)]
    _reject_duplicates(validated, path)
    return validated


def _normalize_path(raw):
    """Same normalisation scrub.py/push_gate.py implicitly apply to their own `rel`
    variables (relpath-style: forward slashes, no leading './', no leading '/') so a
    hand-typed exemption path compares like-for-like against the scanners' own repo-
    relative keys regardless of how the human spelled it.

    This ALSO folds through the shared Windows-path helper (backslashes, drive letter,
    case) -- unlike scrub.py/push_gate.py's own `rel`, which comes straight out of
    os.path.relpath() on THIS process's own os.walk and so is guaranteed forward-slash,
    driveless, and correctly cased already, `raw` here can be anything a person typed
    into exemptions.json by hand. Off Windows winfold() is the identity function, so
    this is a no-op there; if the helper fails to load, fall back to the plain
    slash-swap rather than raising -- a normaliser must not turn "couldn't load an
    optional extra fold" into "the whole exemptions file is unusable"."""
    p = raw.strip()
    if _WINFOLD is not None:
        p = _WINFOLD.winfold(p)
    else:
        p = p.replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p.lstrip("/")


def _validate_entry(entry, index, source):
    if not isinstance(entry, dict):
        raise ExemptionError(
            "{!r} entry #{}: must be a JSON object, got {!r}".format(
                source, index, entry))
    missing = [k for k in ("path", "rule_id", "reason") if k not in entry]
    if missing:
        raise ExemptionError(
            "{!r} entry #{}: missing required field(s) {} -- an exemption is keyed on "
            "PATH *and* RULE-ID and carries a REQUIRED reason; a bare path or bare "
            "rule id is never valid".format(source, index, missing))

    path_v, rule_v, reason_v = entry["path"], entry["rule_id"], entry["reason"]

    for field, value in (("path", path_v), ("rule_id", rule_v)):
        if not isinstance(value, str) or not value.strip():
            raise ExemptionError(
                "{!r} entry #{}: {!r} must be a non-empty string, got {!r}".format(
                    source, index, field, value))
        if _WILDCARD_CHARS & set(value):
            raise ExemptionError(
                "{!r} entry #{}: {}={!r} contains a wildcard character ('*' or '?') "
                "-- NO WILDCARDS at file level or rule level; an exemption names one "
                "exact path and one exact rule id, never a pattern".format(
                    source, index, field, value))

    if not isinstance(reason_v, str) or not reason_v.strip():
        raise ExemptionError(
            "{!r} entry #{}: 'reason' is missing, not a string, or blank/whitespace-"
            "only -- every exemption must carry a written reason a human can read "
            "later; an unreasoned exemption is indistinguishable from an unreviewed "
            "one and is REJECTED, never defaulted".format(source, index))

    return {
        "path": _normalize_path(path_v),
        "rule_id": rule_v.strip(),
        "reason": reason_v.strip(),
    }


def _reject_duplicates(entries, source):
    seen = set()
    for e in entries:
        key = (e["path"], e["rule_id"])
        if key in seen:
            raise ExemptionError(
                "{!r}: duplicate exemption for path={!r} rule_id={!r} -- exactly one "
                "entry per (path, rule_id) pair; merge the reasons by hand instead of "
                "listing the pair twice".format(source, key[0], key[1]))
        seen.add(key)


def build_index(exemptions):
    """(normalized path, rule_id) -> reason. O(1) lookup for the per-file scan loop in
    both scrub.py and push_gate.py. Normalises the path again here (idempotent, cheap)
    so this stays correct even if it is ever handed entries that skipped
    `load_exemptions`'s own normalisation."""
    return {(_normalize_path(e["path"]), e["rule_id"]): e["reason"] for e in exemptions}


def rule_ids_for_path(index, rel_path):
    """Every rule id exempted for this EXACT path -- used to build the rule set handed
    to `forbidden_content.py` for this one file, so the external engine's own
    independent verdict cannot re-block a hit this module already cleared (see
    `filtered_rules`). String-equality lookup only; never a prefix or glob match, which
    is what keeps this mechanism from ever becoming a bare-path exemption in disguise."""
    rel_path = _normalize_path(rel_path)
    return frozenset(rid for (p, rid) in index if p == rel_path)


def partition_hits(findings, rel_path, index):
    """Split a list of finding dicts (each carrying an 'id') into
    (still_blocking, exempted) for ONE file at `rel_path`.

    A finding is exempted ONLY when its exact (path, id) pair has an entry in `index` --
    matches HARD CONSTRAINT 1/2 (no bare path, no bare rule id, no wildcard). Nothing is
    ever discarded: an exempted finding is returned intact (its original id/tier/why/
    hits) PLUS the reason and the (path, rule_id) pair that cleared it, so a caller can
    print/record it -- HARD CONSTRAINT 2, an exempted hit must stay visible."""
    rel_path = _normalize_path(rel_path)
    still_blocking, exempted = [], []
    for finding in findings:
        reason = index.get((rel_path, finding.get("id")))
        if reason is None:
            still_blocking.append(finding)
        else:
            exempted.append(dict(
                finding,
                exempted_path=rel_path,
                exempted_rule_id=finding.get("id"),
                exempted_reason=reason,
            ))
    return still_blocking, exempted


def filtered_rules(rules, exclude_ids):
    """A COPY of `rules` with any rule whose id is in `exclude_ids` removed entirely --
    never a rule with its pattern edited, never a rule's tier/why/"to" touched. Used
    ONLY to build the rule set passed to `forbidden_content.py` for one specific file
    that has an exemption on file, so the external engine's own scan does not
    re-trigger the exact hit this module already recorded as exempted. When
    `exclude_ids` is empty this returns `rules` itself (no copy, no behavior change --
    the fast, common path for a file with no exemption at all)."""
    if not exclude_ids:
        return rules
    return [r for r in rules if r.get("id") not in exclude_ids]


@contextlib.contextmanager
def filtered_rules_file(rules):
    """Context manager: spill `rules` to a throwaway temp JSON file so it can be
    handed to `forbidden_content.py`'s `--rules` flag, which only accepts a PATH on
    disk, never inline JSON (see `build_matcher`/`main` in forbidden_content.py --
    that CLI contract is shared with other callers, so it is not this module's to
    change). `rules` at this call site is the output of `filtered_rules()`, i.e. the
    composed refuse-rule set for one file -- which, for the identity/calendar/path
    rules this lane exists to enforce, means it CARRIES THE OPERATOR'S PLAINTEXT
    IDENTITY TERMS in its regex patterns. Treat the returned path as sensitive for
    every moment it exists.

    TWO GUARANTEES THIS FUNCTION MAKES THAT THE OLD `write_rules_file()` DID NOT:

    1. LOCATION. Always written under `shared.paths.scratch_dir()` -- the project's
       own machine-temp idiom (TMPDIR/%TEMP%-resolved, outside every repo path) --
       and NEVER under a caller-supplied `workdir`. The prior version took a
       `workdir` argument and scrub.py passed its own `staging_root`: that put a
       file full of plaintext identity regexes INSIDE the staging tree, the exact
       thing that gets bundled, judged, and gated toward a push. Found in a live
       run (a stray `shipping-lane-filtered-rules-*.json` picked up by
       `judge.py --prepare`'s 7th-file scan). There is no parameter here that can
       reintroduce that path.
    2. CLEANUP. This is a context manager, not a bare path-returning function --
       "caller owns cleanup" was the other half of the same bug: nothing actually
       called it. The `finally` below deletes the file unconditionally, including
       when the code inside the `with` block raises, so the file cannot outlive its
       one call's use no matter how that use ends.

    Usage: `with filtered_rules_file(filtered) as path: ...`. Never call
    `tempfile.mkstemp` directly for this purpose elsewhere in the lane -- this is
    the one seam that writes identity terms to disk, and it should stay the only
    one."""
    fd, path = tempfile.mkstemp(
        prefix="shipping-lane-filtered-rules-", suffix=".json",
        dir=scratch_dir("shipping-lane"))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(rules, fh)
        yield path
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


# ---------------------------------------------------------------------------- self-test
#
# run_selftests.sh (the lane's gate) walks every *.py in this directory and FAILS the
# whole gate on any module with no --selftest -- "a module that cannot prove itself is a
# finding, not a pass." This proves the five things Y.I2 was ruled on:
#   a) a correct exemption (right path + right rule-id + reason) DOES clear a hit
#   b) an exemption for the WRONG PATH does NOT clear it
#   c) an exemption for the WRONG RULE-ID does NOT clear it
#   d) an exemption with a MISSING or EMPTY reason is rejected (loudly, at load time)
#   e) an exempted hit still appears in the output -- partition_hits never drops it,
#      it moves it to a second list a caller is required to keep and print
# plus the two structural constraints (no wildcards, no bare path/rule-id) and the
# "missing file = zero exemptions" fail-DIRECTION documented above.
#
# scrub.py's own --selftest additionally proves this end-to-end through the real
# staging pipeline (a real refuse hit, a real exemptions.json, a real CLEAN verdict) --
# this file's selftest proves the seam itself: the loader, the validator, and the
# matcher, in isolation, so a bug here cannot hide behind scrub.py's own plumbing.

def selftest():
    ok_all = True

    def report(label, passed, detail=""):
        nonlocal ok_all
        ok_all = ok_all and passed
        print("  [{}] {}{}".format("PASS" if passed else "FAIL", label,
                                    (" -- " + detail) if detail else ""))

    print("exemptions.py --selftest")

    tmp_dirs = []

    def new_dir():
        d = tempfile.mkdtemp(prefix="exemptions-selftest-")
        tmp_dirs.append(d)
        return d

    def write_json(d, name, data):
        p = os.path.join(d, name)
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        return p

    try:
        # -------------------------------------------------------------- missing file
        report("a MISSING exemptions file loads as [] -- zero exemptions is the "
               "strict/safe default, not an error",
               load_exemptions(os.path.join(new_dir(), "does-not-exist.json")) == [])
        report("None/'' behaves the same as a missing file",
               load_exemptions(None) == [] and load_exemptions("") == [])

        # -------------------------------------------------------------- a) clears
        d = new_dir()
        good = write_json(d, "exemptions.json", [
            {"path": "docs/example.md", "rule_id": "placeholder-rule",
             "reason": "documented placeholder form, no real account present -- "
                       "cleared by a human on 2026-08-30"},
        ])
        exempt_list = load_exemptions(good)
        report("a well-formed exemption loads with its fields intact",
               exempt_list == [{"path": "docs/example.md",
                                 "rule_id": "placeholder-rule",
                                 "reason": "documented placeholder form, no real "
                                          "account present -- cleared by a human on "
                                          "2026-08-30"}],
               "got {!r}".format(exempt_list))
        idx = build_index(exempt_list)
        findings = [{"id": "placeholder-rule", "tier": "1-identity", "why": "x",
                     "hits": [{"line": 3, "evidence": "@group.calendar.google.com"}]}]
        still, exempted = partition_hits(findings, "docs/example.md", idx)
        report("(a) CORRECT path + CORRECT rule-id + reason -> the hit is CLEARED "
               "(moved out of still_blocking)",
               still == [] and len(exempted) == 1,
               "still={} exempted={}".format(still, exempted))
        report("(e) the exempted hit is NOT dropped -- it is returned intact, plus "
               "the reason and what cleared it, for the caller to keep and print",
               exempted
               and exempted[0]["id"] == "placeholder-rule"
               and exempted[0]["hits"] == findings[0]["hits"]
               and exempted[0]["exempted_reason"].startswith("documented placeholder")
               and exempted[0]["exempted_path"] == "docs/example.md"
               and exempted[0]["exempted_rule_id"] == "placeholder-rule",
               "exempted={}".format(exempted))

        # -------------------------------------------------------------- b) wrong path
        still_b, exempted_b = partition_hits(findings, "docs/OTHER-FILE.md", idx)
        report("(b) an exemption for the WRONG PATH does NOT clear the hit",
               still_b == findings and exempted_b == [],
               "still={} exempted={}".format(still_b, exempted_b))

        # -------------------------------------------------------------- c) wrong rule
        findings_wrong_rule = [{"id": "some-other-rule", "tier": "1-identity",
                                 "why": "x", "hits": [{"line": 1, "evidence": "e"}]}]
        still_c, exempted_c = partition_hits(
            findings_wrong_rule, "docs/example.md", idx)
        report("(c) an exemption for the WRONG RULE-ID does NOT clear the hit",
               still_c == findings_wrong_rule and exempted_c == [],
               "still={} exempted={}".format(still_c, exempted_c))

        # -------------------------------------------------------------- d) bad reason
        d2 = new_dir()
        for label, bad_entry in (
            ("missing 'reason' key entirely",
             {"path": "p", "rule_id": "r"}),
            ("empty-string reason",
             {"path": "p", "rule_id": "r", "reason": ""}),
            ("whitespace-only reason",
             {"path": "p", "rule_id": "r", "reason": "   \n\t "}),
            ("reason present but not a string",
             {"path": "p", "rule_id": "r", "reason": 12345}),
        ):
            bad_path = write_json(d2, "bad.json", [bad_entry])
            try:
                load_exemptions(bad_path)
                report("(d) REJECTED loudly: " + label, False,
                       "load_exemptions did not raise")
            except ExemptionError as e:
                report("(d) REJECTED loudly: " + label, True, str(e)[:100])

        # a bare path (no rule_id) and a bare rule_id (no path) are equally invalid --
        # HARD CONSTRAINT 1, "never a bare path, never a bare rule-id"
        for label, bad_entry in (
            ("bare path, no rule_id",
             {"path": "p", "reason": "why"}),
            ("bare rule_id, no path",
             {"rule_id": "r", "reason": "why"}),
        ):
            bad_path = write_json(d2, "bad2.json", [bad_entry])
            try:
                load_exemptions(bad_path)
                report("REJECTED: " + label, False, "did not raise")
            except ExemptionError as e:
                report("REJECTED: " + label, True, str(e)[:100])

        # -------------------------------------------------------------- no wildcards
        for field, value in (("path", "docs/*.md"), ("rule_id", "id-*")):
            entry = {"path": "p", "rule_id": "r", "reason": "why"}
            entry[field] = value
            wc_path = write_json(d2, "wildcard.json", [entry])
            try:
                load_exemptions(wc_path)
                report("REJECTED: wildcard in {}".format(field), False,
                       "did not raise")
            except ExemptionError as e:
                report("REJECTED: wildcard in {}".format(field), True, str(e)[:100])

        # -------------------------------------------------------------- duplicates
        dup_path = write_json(d2, "dup.json", [
            {"path": "p", "rule_id": "r", "reason": "first"},
            {"path": "p", "rule_id": "r", "reason": "second, contradicts the first"},
        ])
        try:
            load_exemptions(dup_path)
            report("REJECTED: duplicate (path, rule_id) pair", False, "did not raise")
        except ExemptionError as e:
            report("REJECTED: duplicate (path, rule_id) pair", True, str(e)[:100])

        # -------------------------------------------------------------- malformed file
        not_a_list = write_json(d2, "notalist.json", {"path": "p"})
        try:
            load_exemptions(not_a_list)
            report("REJECTED: exemptions file is a JSON object, not a list", False,
                   "did not raise")
        except ExemptionError:
            report("REJECTED: exemptions file is a JSON object, not a list", True)

        # -------------------------------------------------------------- filtered_rules
        rules = [{"id": "keep-me", "pattern": "x"}, {"id": "drop-me", "pattern": "y"}]
        report("filtered_rules() removes ONLY the excluded id, leaves the rest whole "
               "and untouched (no rule is ever edited, only left out)",
               filtered_rules(rules, {"drop-me"}) == [rules[0]])
        report("filtered_rules() with no excluded ids returns the SAME list object -- "
               "the common, no-exemption case pays nothing extra",
               filtered_rules(rules, frozenset()) is rules)

        # -------------------------------------------------------------- path normalise
        idx2 = build_index([{"path": "./a/b.md", "rule_id": "r", "reason": "why"}])
        report("a leading './' in a hand-typed exemption path is normalised away, so "
               "it still matches the plain relpath the scanners actually use",
               ("a/b.md", "r") in idx2)

        # ----------------------------------------------------------- filtered_rules_file
        expected_dir = os.path.realpath(scratch_dir("shipping-lane"))
        captured_path = []
        with filtered_rules_file([{"id": "only-rule", "pattern": "z"}]) as p:
            captured_path.append(p)
            with open(p, "r", encoding="utf-8") as fh:
                roundtrip = json.load(fh)
            report("filtered_rules_file() round-trips the rule list to a real JSON "
                   "file on disk while the 'with' block is open",
                   roundtrip == [{"id": "only-rule", "pattern": "z"}])
            report("filtered_rules_file() NEVER writes into a caller-supplied "
                   "workdir (no such parameter exists) -- always under "
                   "shared.paths.scratch_dir('shipping-lane'), outside any "
                   "staging tree; this is the fix for the real leak (a stray "
                   "identity-bearing rules file left inside the staging tree)",
                   os.path.realpath(os.path.dirname(p)) == expected_dir,
                   "got dir {!r}, expected {!r}".format(
                       os.path.dirname(p), expected_dir))
        report("(cleanup, success path) the file is GONE the instant the 'with' "
               "block exits normally -- no caller has to remember to delete it",
               not os.path.exists(captured_path[0]))

        # cleanup must also fire when the body inside the 'with' block raises --
        # this is the deterministic guarantee tempfile-and-hope did not have.
        captured_path2 = []
        try:
            with filtered_rules_file([{"id": "x", "pattern": "y"}]) as p2:
                captured_path2.append(p2)
                raise RuntimeError("simulated scan failure inside the with-block")
        except RuntimeError:
            pass
        report("(cleanup, failure path) the file is GONE even when the code using "
               "it raises -- try/finally inside the context manager, not caller "
               "discipline",
               not os.path.exists(captured_path2[0]))
    finally:
        import shutil
        for d in tmp_dirs:
            shutil.rmtree(d, ignore_errors=True)

    print("SELFTEST:", "PASS" if ok_all else "FAIL")
    return 0 if ok_all else 1


def main():
    import argparse
    ap = argparse.ArgumentParser(
        description="exemptions.py -- the shipping lane's PATH+RULE exemption loader")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--show", metavar="PATH",
                     help="load and print an exemptions file as validated JSON")
    args = ap.parse_args()
    if args.selftest:
        import sys
        sys.exit(selftest())
    if args.show:
        try:
            print(json.dumps(load_exemptions(args.show), indent=2))
        except ExemptionError as e:
            import sys
            print("INVALID: {}".format(e), file=sys.stderr)
            sys.exit(1)
        return
    ap.print_help()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""verify_rules — the runnable Verify for the shipping lane's rule sets.

WHAT: proves the effective REFUSE rules and the optional REWRITE rules actually do what
      they claim, by running the REAL `forbidden_content.py` CLI as a subprocess against
      two planted fixtures — never by reading the rules and believing them.

WHICH RULES IT CHECKS. By default it composes the SAME set the lane runs on: the shipped
generic rules in `refuse-rules.json` PLUS a personal tier compiled from an identity file.
With no `--identity`, it uses the lane's own `fixtures/identity-fixture.md` — an invented
person — so the personal tier is proved on every run without anyone's real identity being
involved. Pass `--identity <your file>` to verify YOUR effective set before a real run.

⭐ WHY THE PERSONAL TIER IS IN SCOPE AT ALL. It is the half that cannot ship as a copy: the
generic rules are true for everybody, the identity rules are true for exactly one person.
A verify that only checked the shipped half would report green on a lane whose personal
tier was empty — which is the one failure that publishes somebody's name.

WHY:  every structural check below exists because the failure it catches was MEASURED on
      2026-08-05, not imagined. Three of them are silent-failure paths in the engine:

  [ENGINE (1)] `mention` mode cannot match a term starting with a non-word character.
             Measured: a home path as mode "mention" returned NO HIT on a line plainly
             containing it; the same string as mode "regex" hit immediately. Cause:
             `mention` compiles to \\b<term>\\b and \\b before "/" requires a word char to
             its left. => CHECK: every rule is mode "regex".

  [ENGINE (2)] A rule that omits "mode" silently never fires -- the default is
             "declaration", which matches only a labelled-assignment shape. Measured: a
             plain term with no mode returned ZERO hits across three plain occurrences.
             => CHECK: every rule states "mode" explicitly.

  [ENGINE (3)] A "flags":["I"] typo (capital I) silently stays case-SENSITIVE and reports
             CLEAN -- a genuine fail-open, confirmed by reproduction. `build_matcher` tests
             `"i" in flags`. => CHECK: no rule uses "flags" AT ALL. Case-insensitivity is
             expressed as an inline (?i), which cannot be typo'd into silence because a bad
             inline group is a compile error, not a quiet no-op.

  [ORDER ]   Rewrite rules are ORDER-DEPENDENT, and a general rule placed before a specific
             one silently swallows it. The donor lane hit this: a rule rewriting a product
             name ran before the rule rewriting that name inside a longer path, and produced
             a path that did not exist. There is no way to derive a trigger string from an
             arbitrary regex, so a rewrite rule PROVES itself by declaring an
             `"example": {"in": ..., "out": ...}`, which is applied through the WHOLE
             ordered table. A rule with no example is reported UNPROVEN by name -- visible,
             not silently trusted.

EXIT CODES (the lane's house contract)
  0  PASS            -- every check passed
  1  FAILED          -- at least one check failed; each failure is printed
  2  CANNOT EVALUATE -- a rule file or fixture is missing/unreadable/malformed, or there is
                        no identity to compile. Fail closed: an un-evaluable verify NEVER
                        reports pass.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PARTS = os.path.abspath(os.path.join(HERE, "..", "parts"))
ENGINE = os.path.join(PARTS, "forbidden_content.py")

FIXTURES = os.path.join(HERE, "fixtures")
REFUSE_FIXTURE = os.path.join(FIXTURES, "refuse-fixture.md")
CLEAN_FIXTURE = os.path.join(FIXTURES, "clean-fixture.md")
IDENTITY_FIXTURE = os.path.join(FIXTURES, "identity-fixture.md")

PASS, FAILED, CANNOT_EVALUATE = 0, 1, 2

_failures = []
_checks = 0


def die(msg):
    print("CANNOT EVALUATE: {}".format(msg), file=sys.stderr)
    sys.exit(CANNOT_EVALUATE)


def check(label, ok, detail=""):
    global _checks
    _checks += 1
    if ok:
        print("  [PASS] {}".format(label))
    else:
        print("  [FAIL] {}{}".format(label, (" -- " + detail) if detail else ""))
        _failures.append(label)


def load_rules(path, what, allow_empty=False):
    if not os.path.isfile(path):
        die("{} not found: {!r}".format(what, path))
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as e:
        die("cannot read {} {!r}: {}".format(what, path, e))
    if not isinstance(data, list):
        die("{} must be a JSON list".format(what))
    if not data and not allow_empty:
        die("{} must be a NON-EMPTY JSON list (fail closed: an empty refuse set would "
            "report every file clean)".format(what))
    return data


def engine_hits(rules_path, text_path):
    """Run the REAL CLI and return (exit_code, set_of_hit_ids, stderr)."""
    proc = subprocess.run(
        [sys.executable, ENGINE, "--rules", rules_path, "--text-file", text_path, "--json"],
        capture_output=True, text=True)
    ids = set()
    if proc.stdout.strip():
        try:
            ids = {h["id"] for h in json.loads(proc.stdout).get("hits", [])}
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
    return proc.returncode, ids, proc.stderr


def apply_rewrites(text, rules):
    for r in sorted(rules, key=lambda x: x.get("order", 0)):
        text = re.sub(r["pattern"], r["to"], text)
    return text


def main(argv=None):
    ap = argparse.ArgumentParser(description="verify the shipping lane's rule sets")
    ap.add_argument("--refuse-rules", help="an already-composed effective refuse set")
    ap.add_argument("--rewrite-rules", help="an already-composed effective rewrite set")
    ap.add_argument("--identity", help="compile the personal tier from this identity file "
                                       "(default: the lane's own invented fixture)")
    args = ap.parse_args(argv)

    if not os.path.isfile(ENGINE):
        die("the engine is missing: {!r}".format(ENGINE))

    refuse_path = args.refuse_rules
    rewrite_path = args.rewrite_rules
    identity_used = args.identity or IDENTITY_FIXTURE

    if not refuse_path:
        sys.path.insert(0, HERE)
        try:
            import identity_rules                              # noqa: E402
        except ImportError as e:
            die("identity_rules.py is not importable: {}".format(e))
        try:
            rules, ip, _terms = identity_rules.compose(identity_file=identity_used)
            rewrites = identity_rules.load_rewrites(rewrite_path)
        except identity_rules.IdentityMissing as e:
            die(str(e))
        tmpdir = tempfile.mkdtemp(prefix="verify-rules-")
        refuse_path = os.path.join(tmpdir, "refuse.effective.json")
        with open(refuse_path, "w", encoding="utf-8") as fh:
            json.dump(rules, fh, indent=2)
        if rewrite_path is None:
            rewrite_path = os.path.join(tmpdir, "rewrite.effective.json")
            with open(rewrite_path, "w", encoding="utf-8") as fh:
                json.dump(rewrites, fh, indent=2)
        identity_used = ip

    refuse = load_rules(refuse_path, "the effective refuse rules")
    rewrite = load_rules(rewrite_path, "the effective rewrite rules",
                         allow_empty=True) if rewrite_path else []
    for p, what in ((REFUSE_FIXTURE, "refuse fixture"), (CLEAN_FIXTURE, "clean fixture")):
        if not os.path.isfile(p):
            die("{} not found: {!r}".format(what, p))

    print("verify_rules -- the shipping lane's rule sets")
    print("  refuse rules : {} ({} rules)".format(refuse_path, len(refuse)))
    print("  identity from: {}".format(identity_used))
    print("  rewrite rules: {}".format(
        "{} ({} rules)".format(rewrite_path, len(rewrite)) if rewrite
        else "none -- legitimate; the rewrite tier is optional and cannot fail open"))

    # ---- structural checks (ENGINE 1/2/3) -----------------------------------
    print("\nSTRUCTURE -- every rule, both sets")
    all_rules = [("refuse", r) for r in refuse] + [("rewrite", r) for r in rewrite]

    missing_id = [r for _, r in all_rules if not r.get("id")]
    check("every rule has an 'id'", not missing_id, "{} without".format(len(missing_id)))

    ids = [r["id"] for _, r in all_rules if r.get("id")]
    check("every rule id is unique", len(ids) == len(set(ids)),
          "duplicates: {}".format(sorted({i for i in ids if ids.count(i) > 1})))

    no_mode = [r.get("id") for _, r in all_rules if "mode" not in r]
    check("ENGINE 2 -- every rule states 'mode' explicitly", not no_mode,
          "a missing mode defaults to 'declaration' and NEVER fires: {}".format(no_mode))

    not_regex = [r.get("id") for _, r in all_rules if r.get("mode") != "regex"]
    check("ENGINE 1 -- every rule is mode 'regex' (never 'mention')", not not_regex,
          "'mention' cannot match a term starting with / or ~: {}".format(not_regex))

    with_flags = [r.get("id") for _, r in all_rules if "flags" in r]
    check("ENGINE 3 -- no rule uses 'flags' (use inline (?i) instead)", not with_flags,
          "a 'flags':['I'] typo silently fails OPEN: {}".format(with_flags))

    bad_re = []
    for _, r in all_rules:
        try:
            re.compile(r.get("pattern", ""))
        except re.error as e:
            bad_re.append("{}: {}".format(r.get("id"), e))
    check("every pattern compiles", not bad_re, "; ".join(bad_re))

    check("the personal tier is not empty (an empty one reports your own name clean)",
          any(r.get("tier") == "2-private" for r in refuse),
          "no tier '2-private' rule in the effective set")

    no_to = [r.get("id") for r in rewrite if not r.get("to")]
    check("every rewrite rule declares its replacement 'to'", not no_to, str(no_to))

    orders = [r.get("order") for r in rewrite]
    check("rewrite 'order' is 1..N, unique, and matches file order",
          orders == sorted(orders) and orders == list(range(1, len(rewrite) + 1)),
          "got {}".format(orders))

    # ---- behavioural checks, through the REAL CLI ---------------------------
    print("\nREFUSE TIER -- against the planted fixture, via the real CLI")
    rc, hit_ids, err = engine_hits(refuse_path, REFUSE_FIXTURE)
    check("the fixture is REFUSED (exit 1)", rc == 1,
          "got exit {} {}".format(rc, err.strip()[:200]))

    expected = {r["id"] for r in refuse}
    dead = sorted(expected - hit_ids)
    check("EVERY refuse rule fires -- no dead rule", not dead,
          "{} rule(s) never matched, i.e. silently do nothing: {}".format(len(dead), dead))

    print("\nCLEAN TIER -- the two-sided half; a guard that only ever fires is not a guard")
    rc, hit_ids, err = engine_hits(refuse_path, CLEAN_FIXTURE)
    check("clean fixture passes the REFUSE rules (exit 0)", rc == 0,
          "false positives: {}".format(sorted(hit_ids)))

    if rewrite:
        rc, hit_ids, err = engine_hits(rewrite_path, CLEAN_FIXTURE)
        check("clean fixture passes the REWRITE rules (exit 0)", rc == 0,
              "false positives: {}".format(sorted(hit_ids)))

    # ---- order dependence, proved by each rule's own example ----------------
    if rewrite:
        print("\nORDER -- the rewrite table is order-dependent by construction")
        unproven = []
        for r in rewrite:
            ex = r.get("example")
            if not (isinstance(ex, dict) and "in" in ex and "out" in ex):
                unproven.append(r.get("id"))
                continue
            got = apply_rewrites(ex["in"], rewrite)
            check("{}: {!r} -> {!r}".format(r["id"], ex["in"], ex["out"]),
                  got == ex["out"], "got {!r}".format(got))
        if unproven:
            print("  [note] UNPROVEN (no 'example' declared, so order cannot be checked "
                  "for them): {}".format(unproven))
            print("         Add an \"example\" object with \"in\" and \"out\" to each. A "
                  "general rule placed before a specific one swallows it silently.")

    # ---- verdict ------------------------------------------------------------
    print("\n{}".format("-" * 60))
    if _failures:
        print("VERIFY: FAIL -- {} of {} checks failed".format(len(_failures), _checks))
        for f in _failures:
            print("  x {}".format(f))
        return FAILED
    print("VERIFY: PASS -- all {} checks green "
          "({} refuse rules, {} rewrite rules)".format(_checks, len(refuse), len(rewrite)))
    return PASS


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""identity_rules.py — the shipping lane's ONE personal seam.

WHY THIS EXISTS. The lane it came from carried its author's identity as data inside a
COMMITTED rule file: his first name, his family name, his GitHub handle, his email
address, and the names of six of his own project folders were all literals in
`refuse-rules.json`. That works exactly once, for exactly one person. For anybody else it
is worse than useless — the lane would scan a stranger's files for a stranger's name,
report CLEAN, and let their own name straight through. A scrubber that under-scrubs
publishes personal data, so this is the one part of the lane that cannot ship as a copy.

WHAT SHIPS AND WHAT DOES NOT
  - `refuse-rules.json` (in this repo) holds only what is TRUE FOR EVERYONE: credential
    shapes, home-directory paths, cloud-drive mounts. There is not one person in it.
  - THE TERMS THAT IDENTIFY YOU live outside the repo, in your own notes, at
    `<notes>/config/ship-identity.md`. They are never committed — not because they are
    secret in the API-key sense, but because a file enumerating everything about you that
    must never be public is a poor thing to publish.
  - This module reads that file and COMPILES it into refuse rules, then writes one
    "effective" rule set that the rest of the lane runs against. Every other script keeps
    working exactly as it did, on a file, with its SHA pinned into the receipt — so the
    receipt now also proves WHICH identity set was in force for that run.

⛔ IT FAILS CLOSED, AND THIS IS THE POINT. No identity file, or one with no usable
entries, is CANNOT EVALUATE (exit 2) — never a run with the personal tier quietly
missing. The lane's own house rule is that an un-evaluable check never reports clean, and
the shape of the disaster here is precise: a person runs `/ship`, sees green, and
publishes their own name. The refusal names the file and shows what to put in it.

THE FILE FORMAT — one term per line, `#` comments, blank lines ignored. Deliberately not
JSON: a person hand-writes this, and JSON punishes hand-editing with a syntax error at
the worst moment.

    # Everything here BLOCKS a publish if it appears in a file.
    Wren Oakley
    Wren
    Oakley
    woakley
    wren.oakley@example.com
    Whitfield Contracting

THREE SHAPES, DETECTED, NEVER GUESSED AT BY THE PERSON WRITING THE FILE
  - contains "@"          -> an address. Matched case-insensitively as a literal.
  - contains "/" or "~"   -> a path fragment. Matched case-insensitively as a literal.
  - anything else         -> a WORD, matched with boundaries on both sides.

⭐ THE BOUNDARIES ARE LOOKAROUNDS, NOT `\\b`, AND THAT IS A CARRIED SCAR. Python's `\\b`
treats "_" as a word character, so `wren_oakley` has no boundary on either side and a
`\\b`-anchored rule never fires on it — the exact shape of an ordinary filename, variable,
slug or branch name. That was the worst finding of the donor lane's 2026-08-05 red-team
audit. The lookaround form below excludes "_" from the word class, so the rule fires at an
underscore exactly as it already fired at a space or a dot. It is a strict superset of
`\\b`: it never removes a match `\\b` already made.

⚠ EVERY TERM IS `re.escape`d. A person writing "C++" or "a.b" is writing a literal, not a
regex, and a stray metacharacter must never become either a crash or a silently wider
rule. There is deliberately no raw-regex escape hatch: an unanchored regex in a REFUSE
tier is how a gate starts blocking everything and gets switched off.

USAGE
  identity_rules.py --out-refuse PATH [--out-rewrite PATH] [--identity PATH]
                    [--base PATH] [--notes-root PATH] [--quiet]
  identity_rules.py --show          print the compiled rules as JSON, write nothing
  identity_rules.py --selftest

EXIT CODES (the lane's house contract)
  0  wrote the effective rule set
  2  CANNOT EVALUATE -- no identity file, no usable entries, or an unusable base/rewrite
                        file. Fail closed: never a rule set with the personal tier absent.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASE_RULES = os.path.join(HERE, "refuse-rules.json")

IDENTITY_ENV = "SHIP_IDENTITY"
REWRITES_ENV = "SHIP_REWRITES"
IDENTITY_RELPATH = os.path.join("config", "ship-identity.md")
REWRITES_RELPATH = os.path.join("config", "ship-rewrites.json")

OK, CANNOT_EVALUATE = 0, 2

# A one- or two-character term is not an identity, it is a substring of half the English
# language, and a REFUSE-tier false positive blocks every publish until someone deletes
# the rule. Refused loudly rather than dropped quietly: a silently dropped term is a term
# you believe is protecting you and is not.
MIN_TERM = 3

# A PROSE SENTENCE IS NOT A TERM, and this guard exists because the first draft of this
# module's own fixture failed on it: nine explanatory sentences with no leading "#" became
# nine refuse rules named after their first few words. They mostly never fire, which is the
# bad part — the rule set silently fills with junk, the count stops meaning anything, and a
# rule that DOES accidentally match blocks a publish for a reason nobody can read. Refused
# by shape rather than parsed cleverly: a name is short, a sentence is not.
MAX_TERM_WORDS = 6
MAX_TERM_CHARS = 80

WORD_BOUNDARY_L = r"(?<![A-Za-z0-9])"
WORD_BOUNDARY_R = r"(?![A-Za-z0-9])"

# ⭐ THE TRAILING "s", AND WHY IT IS WORTH ITS FALSE POSITIVES.
#
# Found by running this lane over this repo's own docs rather than by reasoning about it:
# `docs/data-layout.md` carried the donor author's laptop hostname, and the hostname was his
# first name with an "s" glued on -- the shape macOS produces from "<Name>'s MacBook Air" by
# default. His own bounded rule could not see it: after the name came an alphanumeric, so the
# right-hand boundary failed and the term he had listed to protect himself matched nothing.
# It had been sitting in a published file since the repo's first phase.
#
# ⚠ THIS IS A DELIBERATE WIDENING WITH A COST, STATED. A term that becomes an ordinary
# English word when pluralised -- "mark" -> "marks", "wren" -> "wrens" -- will now block a
# publish over a sentence that is about something else entirely. That trade is taken on
# purpose, and the reasoning is not symmetric: a false POSITIVE stops the run, shows you the
# line, and costs a minute; a false NEGATIVE is silent and publishes your name. When a term
# genuinely collides, narrow the term rather than the rule -- list "Wren Oakley" and drop the
# bare "Wren".
POSSESSIVE = r"(?:'s|’s|s)?"

EXAMPLE_FILE = """\
# The terms that identify YOU. One per line. '#' starts a comment.
#
# Anything listed here BLOCKS a publish if it appears in a file being shipped. Start with
# the obvious and add to it whenever the lane misses something:
#
#   - your name, and each part of it on its own line
#   - any handle you use (GitHub, forum, anywhere)
#   - your email addresses
#   - the names of clients, employers, family, or projects that are not public yet
#   - a folder name that would say more about you than you want it to
#
# Matching is case-insensitive and whole-word, so "Oakley" catches "oakley_notes.md" and
# "OAKLEY" but never "Oakleyville". Terms with "@" or "/" in them are matched literally.

Wren Oakley
Wren
Oakley
wren.oakley@example.com
"""


class IdentityMissing(Exception):
    """Raised when there is nothing to compile. Its message is meant to be shown to a person."""


def _notes_root():
    """The notes folder, resolved the way everything else in this repo resolves it.

    ⚠ `resolve_brain_root()` returns `(source, path)`, not a path — taking it for a string
    produces a tuple that only fails at the next `os.path.join`, several frames away from
    the mistake. Unpacked here, once."""
    shared = os.path.abspath(os.path.join(HERE, "..", "..", "shared"))
    if shared not in sys.path:
        sys.path.insert(0, shared)
    try:
        import brain_root                                     # noqa: E402
    except ImportError:
        return None
    _source, path = brain_root.resolve_brain_root()
    return path


def identity_path(notes_root=None):
    """Where the identity file is, in resolution order: the env override, then the notes
    root. Returns None when neither can be resolved — the caller turns that into the
    teaching refusal, so the reason survives all the way to the person reading it."""
    env = os.environ.get(IDENTITY_ENV)
    if env:
        return env
    root = notes_root if notes_root is not None else _notes_root()
    if not root:
        return None
    return os.path.join(root, IDENTITY_RELPATH)


def rewrites_path(notes_root=None):
    env = os.environ.get(REWRITES_ENV)
    if env:
        return env
    root = notes_root if notes_root is not None else _notes_root()
    if not root:
        return None
    return os.path.join(root, REWRITES_RELPATH)


def _slug(term, n):
    s = re.sub(r"[^a-z0-9]+", "-", term.lower()).strip("-")
    return "identity-{:02d}-{}".format(n, s[:24] or "term")


def compile_term(term, n):
    """One written line -> one refuse rule. The shape is DETECTED; the person writing the
    file never has to say which kind of thing they are listing."""
    esc = re.escape(term)
    if "@" in term:
        kind, pattern = "address", "(?i)" + esc
    elif "/" in term or term.startswith("~"):
        kind, pattern = "path fragment", "(?i)" + esc
    else:
        kind = "word"
        pattern = "(?i)" + WORD_BOUNDARY_L + esc + POSSESSIVE + WORD_BOUNDARY_R
    return {
        "id": _slug(term, n),
        "mode": "regex",
        "pattern": pattern,
        "tier": "2-private",
        "why": "listed as identifying you, as a {}, in your own identity file. It is "
               "not in this repo and never will be.".format(kind),
    }


def read_identity(path):
    """The written lines, in order, de-duplicated case-insensitively. Raises rather than
    returning an empty list — an empty personal tier is the failure this module exists to
    make impossible."""
    if not path or not os.path.isfile(path):
        raise IdentityMissing(
            "no identity file, so the lane has nothing personal to look for and would "
            "report your own name CLEAN.\n"
            "  WHERE IT GOES: {}\n"
            "  WHAT GOES IN IT: one term per line — your name, each part of it, any "
            "handle, your email addresses, client or project names that are not public.\n"
            "  MAKE IT WITH:  python3 {} --write-example\n"
            "  Or point ${} at a file somewhere else.".format(
                path or "<your notes folder>/" + IDENTITY_RELPATH,
                os.path.relpath(os.path.abspath(__file__), os.getcwd()), IDENTITY_ENV))
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = fh.read()
    except (OSError, UnicodeDecodeError) as e:
        raise IdentityMissing("cannot read the identity file {!r}: {}".format(path, e))

    terms, seen, too_short, prose = [], set(), [], []
    for line in raw.splitlines():
        term = line.strip()
        if not term or term.startswith("#"):
            continue
        if len(term) < MIN_TERM:
            too_short.append(term)
            continue
        if len(term) > MAX_TERM_CHARS or len(term.split()) > MAX_TERM_WORDS:
            prose.append(term)
            continue
        if term.lower() in seen:
            continue
        seen.add(term.lower())
        terms.append(term)

    if prose:
        raise IdentityMissing(
            "{} line(s) in {} look like prose, not like something that identifies you:\n"
            "{}\n"
            "  A line longer than {} characters or {} words is almost always a note "
            "somebody wrote to themselves. Read as a term it becomes a refuse rule that "
            "never fires, which quietly pads the rule set and makes its count meaningless "
            "— and if one ever DOES match, it blocks a publish for a reason no one can "
            "read.\n"
            "  Put a '#' at the start of the line to make it a comment.".format(
                len(prose), path,
                "\n".join("    " + t[:72] + ("..." if len(t) > 72 else "") for t in prose),
                MAX_TERM_CHARS, MAX_TERM_WORDS))
    if too_short:
        raise IdentityMissing(
            "{} term(s) in {} are shorter than {} characters: {}\n"
            "  A term that short is a substring of ordinary words, and a REFUSE-tier "
            "false positive blocks every publish until somebody deletes the rule — which "
            "is how a gate stops being there for the leak.\n"
            "  Refused rather than skipped, because a silently skipped term is one you "
            "believe is protecting you and is not. Lengthen it or remove the line.".format(
                len(too_short), path, MIN_TERM, ", ".join(repr(t) for t in too_short)))
    if not terms:
        raise IdentityMissing(
            "the identity file {} has no terms in it — only comments or blank lines.\n"
            "  An empty personal tier reports every file clean, including one with your "
            "name in it. Add at least your name.".format(path))
    return terms


def load_base(path=None):
    p = path or BASE_RULES
    if not os.path.isfile(p):
        raise IdentityMissing("the shipped rule set is missing: {!r}".format(p))
    try:
        with open(p, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as e:
        raise IdentityMissing("cannot read the shipped rule set {!r}: {}".format(p, e))
    if not isinstance(data, list) or not data:
        raise IdentityMissing("the shipped rule set must be a non-empty JSON list")
    return data


def load_rewrites(path):
    """The rewrite tier is OPTIONAL and an absent one is legitimate — unlike the refuse
    tier, an empty rewrite set cannot cause a fail-open. It substitutes cosmetics and
    reports; it never decides whether anything is clean."""
    if not path or not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as e:
        raise IdentityMissing("cannot read the rewrite file {!r}: {}".format(path, e))
    if not isinstance(data, list):
        raise IdentityMissing("the rewrite file {!r} must contain a JSON list".format(path))
    for i, r in enumerate(data):
        if not isinstance(r, dict) or not r.get("id") or not r.get("pattern") or not r.get("to"):
            raise IdentityMissing(
                "rewrite rule #{} in {!r} needs 'id', 'pattern' and 'to'".format(i, path))
        r.setdefault("mode", "regex")
        r.setdefault("order", i + 1)
        try:
            re.compile(r["pattern"])
        except re.error as e:
            raise IdentityMissing(
                "rewrite rule {!r} does not compile: {}".format(r["id"], e))
    # The declared order is what the lane applies. A specific rule must be able to run
    # before a general one that would otherwise swallow it, so the order is the author's
    # to state and this only makes it dense and 1-based.
    data.sort(key=lambda r: r.get("order", 0))
    for i, r in enumerate(data, 1):
        r["order"] = i
    return data


def compose(identity_file=None, base=None, notes_root=None):
    """The shipped generic rules PLUS this person's own, as one list."""
    ip = identity_file or identity_path(notes_root)
    terms = read_identity(ip)
    rules = list(load_base(base))
    have = {r.get("id") for r in rules}
    for n, term in enumerate(terms, 1):
        rule = compile_term(term, n)
        if rule["id"] in have:                # two terms that slugify the same
            rule["id"] += "-{}".format(n)
        have.add(rule["id"])
        rules.append(rule)
    return rules, ip, terms


def effective_rule_files(workdir, identity_file=None, notes_root=None, rewrites_file=None):
    """Compose both tiers and write them as REAL FILES under `workdir`, returning the two
    paths.

    ⭐ WHY FILES AND NOT AN IN-MEMORY LIST. Every other script in this lane takes a rule
    PATH and pins that file's sha256 into its receipt, so a receipt proves which rules were
    in force. Composing in memory would have meant threading a rule list through five
    thousand lines and inventing a second way to pin it. Writing the composed set once,
    to the run's own working directory, keeps all of that machinery untouched and makes
    the receipt strictly more honest than it was: it now also pins the personal tier.

    The written file contains the person's identity terms, so it belongs in the run's temp
    working directory and nowhere else — never in the repo, never beside the notes."""
    os.makedirs(workdir, exist_ok=True)
    rules, ip, terms = compose(identity_file=identity_file, notes_root=notes_root)
    rewrites = load_rewrites(rewrites_file or rewrites_path(notes_root))
    rp = os.path.join(workdir, "refuse-rules.effective.json")
    wp = os.path.join(workdir, "rewrite-rules.effective.json")
    with open(rp, "w", encoding="utf-8") as fh:
        json.dump(rules, fh, indent=2)
    with open(wp, "w", encoding="utf-8") as fh:
        json.dump(rewrites, fh, indent=2)
    return rp, wp, ip, len(terms)


# ---------------------------------------------------------------------------- self-test

def selftest():
    import tempfile
    ok = True

    def report(label, passed, detail=""):
        nonlocal ok
        ok = ok and passed
        print("  [{}] {}{}".format("PASS" if passed else "FAIL", label,
                                   (" -- " + detail) if detail else ""))

    print("identity_rules.py --selftest")

    with tempfile.TemporaryDirectory() as td:
        notes = os.path.join(td, "notes")
        os.makedirs(os.path.join(notes, "config"))
        idf = os.path.join(notes, IDENTITY_RELPATH)

        print("\nFAIL-CLOSED -- the half that matters most")
        try:
            compose(identity_file=os.path.join(td, "nope.md"))
            report("a missing identity file refuses", False, "it returned rules")
        except IdentityMissing as e:
            report("a missing identity file refuses", True)
            report("...and the refusal names the file and how to make one",
                   "WHERE IT GOES" in str(e) and "--write-example" in str(e))

        with open(idf, "w") as fh:
            fh.write("# only comments\n\n   \n")
        try:
            compose(identity_file=idf)
            report("an identity file with no terms refuses", False, "it returned rules")
        except IdentityMissing as e:
            report("an identity file with no terms refuses", True)
            report("...and says why an empty personal tier is the danger",
                   "reports every file clean" in str(e))

        with open(idf, "w") as fh:
            fh.write("Wren Oakley\nAl\n")
        try:
            compose(identity_file=idf)
            report("a too-short term refuses rather than being dropped", False)
        except IdentityMissing as e:
            report("a too-short term refuses rather than being dropped", True)
            report("...naming the offending line", "'Al'" in str(e))

        with open(idf, "w") as fh:
            fh.write("Wren Oakley\n"
                     "This file is where I keep the terms that must never be published.\n")
        try:
            compose(identity_file=idf)
            report("a prose line refuses rather than becoming a rule", False)
        except IdentityMissing as e:
            report("a prose line refuses rather than becoming a rule", True)
            report("...and says to comment it out", "'#' at the start" in str(e))
        with open(idf, "w") as fh:
            fh.write("Whitfield Contracting Limited Partnership\n")
        rules_ok, _, terms_ok = compose(identity_file=idf)
        report("a genuine four-word business name still compiles", len(terms_ok) == 1)

        print("\nCOMPILATION -- three shapes, detected")
        with open(idf, "w") as fh:
            fh.write("# mine\nWren Oakley\nOakley\nwoakley\n"
                     "wren.oakley@example.com\nCloudStorage/OakleyDrive\n\nOakley\n")
        rules, path_used, terms = compose(identity_file=idf)
        report("de-duplicates a repeated term", len(terms) == 5, "{}".format(terms))
        report("the shipped generic rules are still there",
               any(r["id"] == "key-aws" for r in rules))
        report("every compiled rule is tier 2-private",
               all(r["tier"] == "2-private" for r in rules if r["id"].startswith("identity-")))
        report("every rule id is unique", len({r["id"] for r in rules}) == len(rules))
        report("every rule is mode 'regex' (push_gate trusts nothing else)",
               all(r.get("mode") == "regex" for r in rules))
        report("no rule uses 'flags' (a 'flags':['I'] typo fails OPEN)",
               all("flags" not in r for r in rules))
        for r in rules:
            try:
                re.compile(r["pattern"])
            except re.error as e:
                report("pattern for {} compiles".format(r["id"]), False, str(e))

        def fires(term_rule_id, text):
            r = next(x for x in rules if x["id"].startswith(term_rule_id))
            return bool(re.search(r["pattern"], text))

        print("\nWORD SHAPE -- the underscore scar, carried")
        by_word = next(r for r in rules if r["pattern"].endswith("(?![A-Za-z0-9])")
                       and "Oakley" in r["pattern"] and "Wren" not in r["pattern"])
        rx = re.compile(by_word["pattern"])
        for hit in ("Oakley", "oakley", "OAKLEY", "oakley_notes.md", "notes_oakley",
                    "desks/oakley/", "oakley.md", "the oakley file",
                    # the possessive/hostname shapes -- the miss that was found in a real
                    # published file, not imagined
                    "Oakleys-Air", "Oakleys-MacBook-Pro", "Oakley's laptop",
                    "oakleys-mac-studio"):
            report("fires on {!r}".format(hit), bool(rx.search(hit)))
        for miss in ("Oakleyville", "moakley", "oakley1", "1oakley", "oakleyish"):
            report("does NOT fire on {!r} (boundary holds)".format(miss),
                   not rx.search(miss))

        print("\nADDRESS + PATH SHAPES")
        report("the address is matched case-insensitively",
               fires("identity", "mail WREN.OAKLEY@EXAMPLE.COM today") is not None
               and any(re.search(r["pattern"], "WREN.OAKLEY@EXAMPLE.COM")
                       for r in rules if "@" in r.get("pattern", "")))
        report("a path fragment is matched literally",
               any(re.search(r["pattern"], "/Volumes/CloudStorage/OakleyDrive/x")
                   for r in rules if "CloudStorage" in r.get("pattern", "")))

        print("\nESCAPING -- a term is a literal, never a regex")
        with open(idf, "w") as fh:
            fh.write("C++ Shop\na.b.consulting\n")
        rules2, _, _ = compose(identity_file=idf)
        rx_cpp = re.compile(next(r["pattern"] for r in rules2 if "identity-01" in r["id"]))
        report("'C++ Shop' is escaped and fires on itself", bool(rx_cpp.search("the C++ Shop deal")))
        rx_ab = re.compile(next(r["pattern"] for r in rules2 if "identity-02" in r["id"]))
        report("'a.b.consulting' does not let '.' match any character",
               bool(rx_ab.search("a.b.consulting")) and not rx_ab.search("axbxconsulting"))

        print("\nREWRITE TIER -- optional, and an absent one is legitimate")
        report("no rewrite file -> an empty list, not an error",
               load_rewrites(os.path.join(td, "nope.json")) == [])
        rwf = os.path.join(notes, REWRITES_RELPATH)
        with open(rwf, "w") as fh:
            json.dump([{"id": "b", "mode": "regex", "pattern": "Proj", "to": "P", "order": 5},
                       {"id": "a", "mode": "regex", "pattern": "ProjX", "to": "PX", "order": 2}], fh)
        rw = load_rewrites(rwf)
        report("declared order is honoured and made 1..N",
               [r["id"] for r in rw] == ["a", "b"] and [r["order"] for r in rw] == [1, 2])
        with open(rwf, "w") as fh:
            json.dump([{"id": "bad", "pattern": "([", "to": "x"}], fh)
        try:
            load_rewrites(rwf)
            report("an uncompilable rewrite pattern refuses", False)
        except IdentityMissing:
            report("an uncompilable rewrite pattern refuses", True)

        print("\nEND TO END -- through the real CLI")
        with open(idf, "w") as fh:
            fh.write("Wren Oakley\n")
        out = os.path.join(td, "eff.json")
        import subprocess
        rc = subprocess.run([sys.executable, os.path.abspath(__file__),
                             "--identity", idf, "--out-refuse", out, "--quiet"]).returncode
        report("CLI with an identity file -> exit 0 and a file", rc == OK and os.path.isfile(out))
        if os.path.isfile(out):
            with open(out) as fh:
                eff = json.load(fh)
            report("the written set carries both tiers",
                   any(r["tier"] == "1-secret" for r in eff)
                   and any(r["tier"] == "2-private" for r in eff))
        rc = subprocess.run([sys.executable, os.path.abspath(__file__),
                             "--identity", os.path.join(td, "nope.md"),
                             "--out-refuse", out, "--quiet"],
                            capture_output=True, text=True).returncode
        report("CLI with no identity file -> exit 2 (fail closed)", rc == CANNOT_EVALUATE,
               "got {}".format(rc))

    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="compile the lane's effective rule set")
    ap.add_argument("--identity", help="the identity file (default: $%s, then <notes>/%s)"
                    % (IDENTITY_ENV, IDENTITY_RELPATH))
    ap.add_argument("--base", help="the shipped generic rule set (default: %s)" % BASE_RULES)
    ap.add_argument("--rewrites", help="your optional rewrite rules (default: $%s, then "
                    "<notes>/%s)" % (REWRITES_ENV, REWRITES_RELPATH))
    ap.add_argument("--notes-root", help="resolve <notes> as this, instead of asking the resolver")
    ap.add_argument("--out-refuse", help="write the effective refuse rules here")
    ap.add_argument("--out-rewrite", help="write the effective rewrite rules here")
    ap.add_argument("--show", action="store_true", help="print the compiled rules, write nothing")
    ap.add_argument("--write-example", action="store_true",
                    help="write a starter identity file at the resolved path")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    if args.write_example:
        p = args.identity or identity_path(args.notes_root)
        if not p:
            print("CANNOT EVALUATE: no notes root is set, so there is nowhere to put it. "
                  "Set $%s or pass --identity." % IDENTITY_ENV, file=sys.stderr)
            return CANNOT_EVALUATE
        if os.path.exists(p):
            print("CANNOT EVALUATE: {} already exists — not overwriting a file that may "
                  "be the only record of what must never be published.".format(p),
                  file=sys.stderr)
            return CANNOT_EVALUATE
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(EXAMPLE_FILE)
        print("wrote a starter identity file at {}\n"
              "⚠ IT IS A STARTER, NOT YOURS — the names in it are a fixture. Replace them "
              "with your own before you ship anything.".format(p))
        return OK

    try:
        rules, ip, terms = compose(args.identity, args.base, args.notes_root)
        rewrites = load_rewrites(args.rewrites or rewrites_path(args.notes_root))
    except IdentityMissing as e:
        print("CANNOT EVALUATE: {}".format(e), file=sys.stderr)
        return CANNOT_EVALUATE

    if args.show:
        print(json.dumps(rules, indent=2))
        return OK

    if not args.out_refuse:
        print("CANNOT EVALUATE: one of --out-refuse, --show or --selftest is required",
              file=sys.stderr)
        return CANNOT_EVALUATE

    with open(args.out_refuse, "w", encoding="utf-8") as fh:
        json.dump(rules, fh, indent=2)
    if args.out_rewrite:
        with open(args.out_rewrite, "w", encoding="utf-8") as fh:
            json.dump(rewrites, fh, indent=2)
    if not args.quiet:
        print("effective refuse rules: {} shipped + {} of yours, from {}".format(
            len(rules) - len(terms), len(terms), ip))
        print("effective rewrite rules: {}".format(len(rewrites)))
    return OK


if __name__ == "__main__":
    sys.exit(main())

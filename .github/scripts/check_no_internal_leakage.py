#!/usr/bin/env python3
"""check_no_internal_leakage.py -- server-side gate: no internal working-note leaks in.

WHY THIS EXISTS: migration-audit/08-THIRD-PARTY-INVENTORY.md was authored and committed
directly inside this checkout and pushed to the shared remote. It carried the operator's
macOS username in absolute paths, a live third-party project hostname, and a map of where
every credential is stored. Nothing caught it because the project's scrubbing lane
(claudeops-config/skills/ship, system/shipping-lane/scrub.py) is a MANUAL pipeline that
only ever sees files a human explicitly routes through it -- a file authored straight into
this repo never passes through it. There were no git hooks and no .github/workflows/ at
all, so nothing server-side ever looked at a commit landing here. This is that check.

WHAT IT CATCHES (three kinds, deliberately no more):
  1. PATH DENYLIST -- a changed file's path itself is an internal-working-note location:
     migration-audit/**, or a root-level HANDOFF*, KIMI-*, or *-log.md.
  2. GENERIC HOME PATH -- a line a change ADDS contains an absolute macOS/Linux home
     path, "/Users/<anyone>" or "/home/<anyone>" -- NOT hardcoded to one username, because
     the next leak may belong to a different contributor.
  3. OPERATOR IDENTITY -- a line a change ADDS contains one of the terms that identify
     whoever runs this repo. ⛔ THOSE TERMS ARE NOT IN THIS FILE, AND MUST NEVER BE.
     They are COMPILED AT RUNTIME from the same out-of-repo identity file the shipping
     lane already uses -- system/shipping-lane/identity_rules.py, reading
     `<notes>/config/ship-identity.md` (or $SHIP_IDENTITY / --identity). See
     load_identity_patterns() below. One identity source for the whole product, not two
     that drift apart -- and, because the source is never committed, this check has no
     personal data to leak and no longer has to exempt its own directory to hide any.
     ⛔ FAIL CLOSED: no identity file, or one with no usable terms, is CANNOT EVALUATE
     (exit 2) -- never a run with the personal tier quietly missing. A scanner that
     reports CLEAN because it had nothing to look for is the exact disaster
     identity_rules.py was written to prevent ("no identity file, so the lane has
     nothing personal to look for and would report your own name CLEAN").
     What is NOT reused: refuse-rules.json's "2-private" desk-persona rules (cal / marc /
     emily / clair / deryl / dobby) name ClaudeOps-internal personas, not the operator,
     and this product ships its OWN generically-named skills with the same one-word slugs
     (.claude/skills/cal-daily/ is real, shipped, unrelated product content) -- reusing
     those rules here would cry wolf on this repo's own normal traffic. Secrets
     (refuse-rules.json's "1-secret" tier) are a related but separate concern and are out
     of scope for this check -- see "WHAT THIS DOES NOT CATCH" in the workflow's own
     comments / the task report.

⛔ NEVER PRINT A MATCHED IDENTITY TERM. A finding from rule 3 reports path, line and an
OPAQUE rule id (operator-identity-NN), and its evidence line has the matched span replaced
with [REDACTED] -- see redact_spans(). This job's logs, its JSON artifact and its step
summary are PUBLIC on a public repo; a gate that finds the operator's name and then prints
it into a world-readable build log has moved the leak, not closed it.

WHY "ADDED LINES", NOT WHOLE-FILE CONTENT: this repo already carries a few lines that
would trip these patterns if the WHOLE file were rescanned on every touch -- e.g.
system/shipping-lane/scrub.py's own selftest fixtures literally contain an absolute
/Users/<fixture-name>/Desktop path. Scanning the whole file on any unrelated edit would
false-positive on lines nobody touched. Scanning only the lines a diff ADDS matches the
task's own framing -- "fail the check when a change INTRODUCES" -- and survives contact
with this repo's real history. See parse_unified_diff() below.

USAGE
  CI (production path): parses `git diff` between two refs/SHAs in the current repo.
      check_no_internal_leakage.py --base <sha_or_ref> --head <sha_or_ref> [--mode merge-base|linear]
      --mode merge-base -> `git diff --unified=0 --no-color --no-renames BASE...HEAD` (pull_request)
      --mode linear      -> `git diff --unified=0 --no-color --no-renames BASE HEAD`   (push)

  Every mode takes an optional --identity PATH (default: $SHIP_IDENTITY, then
  <notes>/config/ship-identity.md). On a GitHub runner there is no notes folder, so the
  workflows write a repo secret to a runner-local file and export $SHIP_IDENTITY -- see
  .github/workflows/no-internal-leakage.yml. Unset secret -> exit 2, red, loud.

  Manual / fixture testing (no git needed -- treats the whole file as "added", which is
  the exact real-world shape of a wholly NEW file, e.g. the incident file itself):
      check_no_internal_leakage.py --scan-file /tmp/fixture.md --as-path migration-audit/x.md

  Whole-tree BASELINE audit (periodic, NOT per-PR -- see WHOLE-TREE BASELINE MODE below):
      check_no_internal_leakage.py --whole-tree [--report-out PATH]

EXIT CODES
  0  CLEAN    -- nothing flagged (whole-tree: no BLOCKING finding; WARNING-tier findings,
                 if any, do not change this -- see below)
  1  FLAGGED  -- at least one BLOCKING violation (path or identity content)
  2  CANNOT EVALUATE -- git diff/ls-files itself failed, a file could not be read, bad
                        arguments, OR no usable identity file (see rule 3). NEVER exit 0
                        on an error -- an unevaluated run must not read as a clean one,
                        and a run with no personal tier is an unevaluated run.

WHOLE-TREE BASELINE MODE -- WHY IT EXISTS, SEPARATE FROM THE PER-PR GATE ABOVE
  The per-PR gate above only ever sees lines a diff ADDS (see "WHY ADDED LINES" above) --
  by construction it is permanently blind to anything committed before this check existed.
  --whole-tree is a second, independent mode that rescans every file `git ls-files` tracks
  in the current checkout, in full, on the SAME two BLOCKING rule families the per-PR gate
  already enforces (PATH_DENYLIST, and content_patterns() = generic + identity) -- so it
  can find a leak that shipped
  before this script did, which the per-PR gate structurally never will. It is invoked by
  `.github/workflows/no-internal-leakage-baseline.yml` on a weekly schedule and on manual
  `workflow_dispatch` -- NEVER on pull_request/push, and it changes nothing about how the
  per-PR gate itself runs or scores (verified: `--base --head --mode` code paths are
  untouched by this mode; see the module's own test invocations).

  It ALSO carries two WARNING-tier checks the per-PR gate does not have, both scoped to
  whole-tree only so the per-PR gate's behavior is provably unchanged:
    - a third-party NAME heuristic (a capitalised name-shaped token sharing a line with a
      personal/relationship word -- "wife", "client", "tenant", etc.) -- see NAME_SHAPE_RE.
    - a DOLLAR-AMOUNT-NEAR-BILLING-WORD heuristic -- a specific-decimal dollar figure
      sharing a line with a money-owed/money-settled word (billed, unbilled, receivable,
      arrears, retainer, payment, balance, ...) -- see BILLING_TRIGGER_STEMS, which also
      records which candidate words were REJECTED and on what measurement.
  WARNING findings are reported and written to the JSON report but NEVER change the exit
  code -- a hardcoded regex cannot enumerate every third party's name or every dollar
  figure that matters, so these are heuristics for a HUMAN to triage, not a gate. Flagging
  them as BLOCKING would either (a) false-positive often enough that the whole check gets
  disabled, or (b) get quietly allowlisted into uselessness -- see ⛔ in the module's
  "suppression" note below. Both heuristics are deliberately narrow (same-line
  co-occurrence, not whole-paragraph) to keep the false-positive rate low enough to trust.

  ⛔ NO PER-FILE SUPPRESSION. The only exemption whole-tree mode honors is
  FICTIONAL_FIXTURE_ALLOWLIST -- a small, fixed, curated list of THIS REPO'S OWN
  already-established invented names (Wren, Oakley, Fern, ...; see the constant below for
  full provenance) and fixture home-path usernames (wren, x, theirname). There is no
  mechanism to silence a real finding on a specific line or file -- that would be exactly
  the kind of suppression that could hide the next real leak, which is the failure this
  mode exists to catch.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import subprocess
import sys

CLEAN, FLAGGED, CANNOT_EVALUATE = 0, 1, 2
BLOCKING, WARNING = "BLOCKING", "WARNING"

# ---------------------------------------------------------------------- rule 1: PATH DENYLIST
# Applied to the file's NEW repo-relative path. Kept consistent with this repo's own
# .gitignore, which already excludes migration-audit/ wholesale ("INTERNAL MIGRATION
# WORKING NOTES. NEVER SHIPPED.") -- gitignore stops an ordinary `git add`, this stops a
# `git add -f` or a file authored somewhere gitignore doesn't reach, server-side, for
# everyone, with no setup.
PATH_DENYLIST = [
    {
        "id": "migration-audit-dir",
        "pattern": r"^migration-audit/",
        "remedy": (
            "migration-audit/ is the operator's internal migration-working-notes "
            "directory (see .gitignore: 'INTERNAL MIGRATION WORKING NOTES. NEVER "
            "SHIPPED.'). Drop this file from the commit. If something in it is "
            "genuinely useful to a reader, rewrite the durable point into docs/ or "
            "README.md -- written for a reader of the product, not the operator's own "
            "scratch."
        ),
    },
    {
        "id": "root-handoff",
        "pattern": r"^HANDOFF[^/]*$",
        "remedy": (
            "a root-level HANDOFF* file is an operator-to-operator session handoff "
            "note, not product content. Drop it from the commit; move any durable "
            "instruction into docs/ instead."
        ),
    },
    {
        "id": "root-kimi",
        "pattern": r"^KIMI-[^/]*$",
        "remedy": (
            "a root-level KIMI-* file is internal audit-prompt / scratch material for "
            "the operator's own tooling. Drop it from the commit."
        ),
    },
    {
        "id": "root-log-md",
        "pattern": r"^[^/]+-log\.md$",
        "remedy": (
            "a root-level *-log.md file is an internal phase/audit log, not product "
            "content. Drop it from the commit -- migration-audit/ (gitignored) or your "
            "own local notes is where working logs live, never repo root."
        ),
    },
]

# ------------------------------------------------------------------------- rule 2: CONTENT
# Checked against every line a diff ADDS (never unchanged context, never a whole-file
# rescan -- see module docstring for why).
#
# ⭐ EVERY RULE IN THIS LIST IS TRUE FOR EVERYBODY AND NAMES NOBODY. That is the whole
# point of the split: this is the same line system/shipping-lane/refuse-rules.json draws
# ("credential shapes, home-directory paths, cloud-drive mounts... There is not one person
# in it"). The terms that identify a specific human are rule 3, and they are compiled at
# runtime from a file that is not in this repo -- see load_identity_patterns().
#
# The "source" field names the equivalent rule id in refuse-rules.json where one exists, so
# a drift check just diffs the two pattern strings.
GENERIC_CONTENT_PATTERNS = [
    {
        "id": "home-path-generic",
        "source": None,
        # ⚠ AUDITED 2026-08-18 for the bare-prefix weakness that was found in
        # operator-drive-cloudstorage below. IT DOES NOT HAVE IT, and the reason is the
        # trailing `+`: it demands at least one account-name character, so the bare prefix,
        # an angle placeholder, a shell variable and a glob all fail to match. Verified
        # against all four shapes plus a positive control that still fires.
        #
        # ⭐ WHAT IT DOES HAVE, REPORTED AND DELIBERATELY NOT "FIXED": it fires on a WORD
        # placeholder ("username", "you", "theirname"), because those are indistinguishable
        # from a real short account name by shape alone. That is arguably correct -- the
        # remedy is "write ~/ instead", which is the right advice for a placeholder too --
        # but note the asymmetry it creates: FICTIONAL_FIXTURE_USERNAMES suppresses a known
        # set of them in whole-tree mode ONLY. check_added_lines() (the per-PR gate) does not
        # consult that allowlist, so a PR that ADDS one of those fixture paths is BLOCKED
        # while the identical line already in the tree is not. Left alone on purpose: closing
        # it means LOOSENING a blocking rule, which is the opposite of the change this pass
        # was making, and the per-PR strictness has never actually bitten anyone.
        "pattern": r"(?:/Users/|/home/)[A-Za-z0-9._-]+",
        "remedy": (
            "an absolute home-folder path -- the segment right after /Users/ or /home/ "
            "IS someone's account name, and the path does not exist on any other "
            "machine. Replace it with ~/... or $HOME/... (this repo's own "
            "docs/REPORT-A-BUG.md gives the identical instruction: replace an absolute "
            "`/Users/<name>/...` path with `~/...`)."
        ),
    },
    {
        "id": "operator-drive-cloudstorage",
        "source": "path-drive-cloudstorage",
        # ⭐ TIGHTENED 2026-08-18 -- IT NOW REQUIRES AN ACCOUNT, NOT JUST THE PREFIX.
        # It used to be the bare prefix `CloudStorage/GoogleDrive` + a dash, and it fired on
        # two lines of INSTALL.md that contain no account name at all: one sentence of prose
        # describing what a Drive path looks like, and one line of FUNCTIONAL INSTALLER CODE
        # that globs `GoogleDrive-*` to find the user's Drive folders. The second cannot be
        # fixed in the file -- the installer's job IS to match that shape, so it has to
        # contain it. Both were pure false positives, and a BLOCKING rule that red-lights an
        # installer for doing its job is a rule that gets deleted.
        #
        # ⚠ THE FIX IS STRICTER, NOT LOOSER, AND THAT DISTINCTION IS THE WHOLE POINT. The
        # rule exists to catch a real Drive account path, so it now demands the thing that
        # makes it one: an account-shaped token after the dash -- `GoogleDrive-<local>@<domain>`
        # with a real TLD. A glob (`GoogleDrive-*`), a placeholder (`GoogleDrive-<account>`)
        # and a bare prefix all stop matching; a genuine mount path still matches. "Contains
        # this shape" became "contains a real account". Pinned both ways in
        # test_check_no_internal_leakage.py: a positive control asserts a real-shaped account
        # path is still caught, and negative controls assert the two INSTALL.md shapes are not.
        #
        # The `[-]` character class is kept as belt-and-braces so this line cannot match
        # itself. It is no longer the thing doing that work -- the `[` opening the account
        # class already stops a self-match -- but it costs nothing and the self-scan-clean
        # test below depends on the property, not on which mechanism provides it.
        "pattern": r"CloudStorage/GoogleDrive[-][A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        "remedy": ("a macOS Google Drive mount path with a real account address in it "
                   "(~/Library/CloudStorage/...). Replace the account segment with a "
                   "placeholder, or glob for it at runtime instead of hardcoding it."),
    },
    {
        "id": "operator-drive-account",
        "source": "path-drive-account",
        # ⚠ AUDITED 2026-08-18 alongside the rule above and DELIBERATELY LEFT ALONE: it never
        # had the bare-prefix weakness. It has always required an "@" after the dash, so a
        # glob or a placeholder cannot satisfy it. Left wider than its neighbour on purpose
        # (no CloudStorage anchor, no TLD required) so it still catches a mount name quoted
        # anywhere -- in a shell snippet, a log line, a doc -- not only under Library/.
        # CONSEQUENCE, ACCEPTED: a real macOS mount path now matches BOTH rules and reports
        # twice. On a BLOCKING rule that is louder, not weaker, and the module already states
        # that multiple independent findings on one file are all worth surfacing at once.
        "pattern": r"GoogleDrive-[A-Za-z0-9._%+-]+@",
        "remedy": "a Google Drive mount path with a full email address embedded in it. Remove it.",
    },
    {
        "id": "home-path-windows",
        "source": "path-home-windows",
        # ⛔ ADDED (2026-08-28) -- system/shipping-lane/refuse-rules.json has carried
        # path-home-windows since before this file existed; this scanner had no equivalent
        # at all, found by test_line_boundary_bypass.py's WINDOWS-PATH SHAPES cases (not a
        # line-boundary bug -- a plain missing rule). Same shape as the sibling scrub.py
        # rule, on purpose: `C:\Users\<account>` identifies its owner the same way
        # `/Users/<account>` does.
        "pattern": r"(?i)[A-Za-z]:\\Users\\(?!(?:Jane[ _]?Doe|John[ _]?Doe|Name|somebody|someone|username|user|account|placeholder|example|YourName|<[^>]+>)\\)[A-Za-z0-9._ -]+",
        "remedy": ("the Windows form of a home path (C:\\Users\\<account>). Replace the "
                   "account segment with a placeholder, or reference it relatively."),
    },
    {
        "id": "path-unc-share",
        "source": "path-unc-share",
        # ⛔ ADDED (2026-08-28), alongside home-path-windows -- a bare Windows network-share
        # path has neither a drive letter nor a "Users" segment for home-path-windows to key
        # on, so it needs its own rule -- exactly why scrub.py's refuse-rules.json carries
        # path-unc-share as a separate entry rather than folding it into path-home-windows.
        #
        # ⚠ SELF-SCAN SAFETY, DELIBERATE: writing this rule's own shape out as a literal
        # example anywhere near it (two backslashes, a server-shaped token, a backslash, a
        # share-shaped token) makes this file flag itself -- caught by
        # test_check_no_internal_leakage.py's self-scan assertion. Described in prose here
        # instead, the same fix operator-drive-cloudstorage's comments already use.
        "pattern": r"(?i)(?<![A-Za-z0-9:\\])\\\\(?!(?:SERVER|placeholder|example)\\)[A-Za-z0-9._-]+\\[A-Za-z0-9._ -]+",
        "remedy": ("a bare Windows UNC/network-share path -- two leading backslashes, a "
                   "server name, a backslash, then a share name. The share segment is "
                   "very often a personal account or project folder -- replace it with a "
                   "placeholder."),
    },
]

# ⛔ THERE IS NO .github/ CONTENT-SCAN EXEMPTION ANY MORE, AND THAT IS THE POINT OF THIS
# FILE'S 2026-08-18 REWRITE (issue #59).
#
# BE FAIR TO WHAT WAS HERE BEFORE: a pattern-matcher must contain its patterns, so a
# self-scan self-flagging is a real problem and `CONTENT_SCAN_EXCLUDE_PREFIX = ".github/"`
# was a defensible answer to it. The defect was never the exemption. It was that rule 3 was
# written as SIX LITERAL PERSONAL STRINGS, which made the exemption mandatory -- and so the
# one file in a PUBLIC repo guaranteed to contain the operator's identity became the one
# file the scanner structurally could not read. A whole-tree scan reported CLEAN on
# 2026-08-15 for exactly that reason.
#
# Fixing the CAUSE (rule 3 is now compiled from an out-of-repo file) left exactly two
# self-flagging lines in the entire .github/ tree, both on the generic, impersonal
# `operator-drive-cloudstorage` shape: its own "pattern" field, and a comment that quoted
# it. Both are handled above -- that rule now requires a real account address after the
# dash, so neither a quoted prefix nor a pattern string can satisfy it (the `[-]` class is
# kept on top of that as belt-and-braces). The comment was reworded. Measured, not assumed
# -- with the prefix gone, this directory scans with zero findings in both modes. So the
# exemption bought nothing and cost everything, and it is gone.


# ------------------------------------------------------- rule 3: OPERATOR IDENTITY (runtime)
# WIRED, NOT INVENTED. system/shipping-lane/identity_rules.py already owns this exact
# problem for the shipping lane: it reads one term-per-line file that lives outside the
# repo, DETECTS each term's shape (address / path fragment / word), re-escapes it as a
# literal, and compiles a bounded regex -- including the two scars that file documents (the
# lookaround boundaries that fire at "_" where \b does not, and the trailing-"s" widening
# that catches "<Name>s-MacBook-Air"). Re-deriving any of that here would be a second
# implementation to drift; this imports the first one.
#
# WHAT THIS ADDS ON TOP: for each WORD-shaped term, a second rule matching that term
# EMBEDDED IN AN EMAIL LOCAL-PART (`something<term>something@domain`). The literal rule set
# this replaced carried exactly one such pattern, hardcoded to the family name; a bounded
# word rule alone cannot see it, because the character to the term's left is alphanumeric.
# Generalising it to every word term is strictly MORE detection than before, not less.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SHIPPING_LANE_DIR = os.path.join(REPO_ROOT, "system", "shipping-lane")

IDENTITY_RULE_PREFIX = "operator-identity"

# The remedy text a rule-3 finding prints. It says what KIND of thing matched and never
# WHICH -- see the module docstring's "NEVER PRINT A MATCHED IDENTITY TERM".
_IDENTITY_REMEDY = {
    "word": ("a term from your own identity file appears here -- your name, a handle, or "
             "a client/project name you listed as never-publishable. Remove it, or use a "
             "generic placeholder ('the operator', 'you'). The term itself is deliberately "
             "not printed: this log is public."),
    "address": ("an email address listed in your own identity file. Remove it or "
                "genericize it. The address itself is deliberately not printed."),
    "path fragment": ("a path fragment listed in your own identity file. Replace it with "
                      "a relative or placeholder path. Not printed: this log is public."),
    "email-embedded": ("an email address built out of one of your identity terms "
                       "(`...<term>...@domain`). Remove it or genericize it. Not printed: "
                       "this log is public."),
}


class IdentityUnavailable(Exception):
    """No usable identity source. ALWAYS maps to exit 2 -- never a quiet exit 0. Its
    message is meant to be read by a person and to name the fix."""


def load_identity_patterns(identity_file=None):
    """Compile rule 3 from the out-of-repo identity file. Raises IdentityUnavailable on
    anything that would leave the personal tier empty -- there is deliberately no path
    through this function that returns a short list and no error."""
    if SHIPPING_LANE_DIR not in sys.path:
        sys.path.insert(0, SHIPPING_LANE_DIR)
    try:
        import identity_rules                                  # noqa: E402
    except ImportError as e:
        raise IdentityUnavailable(
            "system/shipping-lane/identity_rules.py is not importable ({}), so the "
            "operator-identity tier cannot be compiled. Refusing to scan with rule 3 "
            "missing -- that is a scanner that reports CLEAN because it has nothing to "
            "look for.".format(e))

    path = identity_file or identity_rules.identity_path()
    try:
        terms = identity_rules.read_identity(path)
    except identity_rules.IdentityMissing as e:
        raise IdentityUnavailable(str(e))

    rules = []
    for n, term in enumerate(terms, 1):
        compiled = identity_rules.compile_term(term, n)
        # ⛔ compile_term's own id is a SLUG OF THE TERM ("identity-03-<the-term>"). That id
        # is printed in every finding and written into the JSON artifact, so using it would
        # publish the exact string this whole change exists to remove. Opaque id, always.
        kind = "address" if "@" in term else (
            "path fragment" if ("/" in term or term.startswith("~")) else "word")
        rules.append({
            "id": "{}-{:02d}".format(IDENTITY_RULE_PREFIX, n),
            "source": "ship-identity.md (not in this repo)",
            "pattern": compiled["pattern"],
            "remedy": _IDENTITY_REMEDY[kind],
        })
        if kind == "word":
            rules.append({
                "id": "{}-{:02d}-email".format(IDENTITY_RULE_PREFIX, n),
                "source": "ship-identity.md (not in this repo)",
                "pattern": (r"(?i)[A-Za-z0-9._%+-]*" + re.escape(term)
                            + r"[A-Za-z0-9._%+-]*@[A-Za-z0-9.-]+"),
                "remedy": _IDENTITY_REMEDY["email-embedded"],
            })
    return rules


def is_identity_rule(rule_id) -> bool:
    return bool(rule_id) and rule_id.startswith(IDENTITY_RULE_PREFIX)


def redact_spans(line, rule=None):
    """The evidence string for a rule-3 finding: the real line with every span ANY identity
    rule matched replaced by [REDACTED]. Enough context to find it, none of the terms.

    ⚠ EVERY IDENTITY RULE, NOT JUST THE ONE THAT FIRED -- and that is not fussiness, it is
    the bug this function shipped with for about ten minutes on 2026-08-18. A line reading
    "signed off by <first> <last>" produces TWO findings; redacting each against only its
    own rule printed "[REDACTED] <last>" from one and "<first> [REDACTED]" from the other,
    so the pair of findings reassembled the whole name in the log. Partial redaction of a
    line that is printed more than once is not redaction. The `rule` argument is kept for
    call-site readability and is deliberately unused."""
    out = line
    for r in (_CONTENT_PATTERNS or []):
        if is_identity_rule(r["id"]):
            out = re.sub(r["pattern"], "[REDACTED]", out)
    return out


# The EFFECTIVE rule set = generic + identity. Deliberately None until install_identity_
# patterns() succeeds, so that every code path that scans content without a personal tier
# raises instead of quietly scanning with two thirds of the rules. Fail-closed by
# CONSTRUCTION, not by remembering to check.
_CONTENT_PATTERNS = None


def install_identity_patterns(identity_file=None):
    global _CONTENT_PATTERNS
    _CONTENT_PATTERNS = list(GENERIC_CONTENT_PATTERNS) + load_identity_patterns(identity_file)
    return _CONTENT_PATTERNS


# --------------------------------------------------------- shared fixture allowlist (DATA ONLY)
# ⚖ RULED 2026-08-23, in session. Fixture home-path usernames: the segment right after
# /Users/ or /home/ that this repo's OWN examples already use for an invented account.
#
# ⭐ WHY IT LIVES ABOVE THE WHOLE-TREE WALL. It used to sit below it, so ONLY whole-tree mode
# honoured it. The per-PR paths (--base/--head/--scan-file) did not — and the pre-commit hook runs
# --scan-file. Net effect: system/shipping-lane/scrub.py became PERMANENTLY UNCOMMITTABLE, because
# its own self-test plants `/Users/wren/Desktop` precisely to prove the scrubber CATCHES home paths.
# The scanner could not tell a line that USES the pattern from one that TESTS it (same shape as
# issue #80). Measured 2026-08-23: a one-line, unrelated fix to scrub.py was refused.
#
# ⛔ THE WALL IS NOT BREACHED. Its stated invariant is about FUNCTIONS — "the per-PR functions are
# never called from here, and nothing here is ever called from them." This is a frozenset of four
# strings, not a call. No per-PR function invokes whole-tree code, or the reverse; both sides now
# read the same DATA. The file's ⛔ NO PER-FILE SUPPRESSION rule also stands: this admits no new
# string, it makes two modes agree about a list that was already curated and already trusted.
FICTIONAL_FIXTURE_USERNAMES = frozenset({"wren", "x", "theirname", "woakley"})


def content_patterns():
    if _CONTENT_PATTERNS is None:
        raise IdentityUnavailable(
            "the operator-identity tier was never installed (install_identity_patterns() "
            "was not called), so this scan would run on the generic rules alone and could "
            "report a file carrying the operator's own name as CLEAN. Refusing.")
    return _CONTENT_PATTERNS


# ============================================================================ WHOLE-TREE
# BASELINE MODE ONLY -- nothing below this line, until scan_whole_tree()'s return, is
# reachable from the per-PR (--base/--head/--scan-file) code paths above. That separation
# is deliberate and load-bearing: "prove the per-PR mode is unchanged" only holds if the
# per-PR functions (check_path, check_added_lines, scan_files, parse_unified_diff,
# run_git_diff) are never called from here, and nothing here is ever called from them.

# --------------------------------------------------------- fictional-fixture allowlist
# This is NOT a general suppression mechanism (see module docstring, ⛔ NO PER-FILE
# SUPPRESSION). It is a small, fixed, curated list of identities this repo's OWN test
# fixtures and example content already use, established independently of this script:
#   - "Wren Oakley" / "Wren" / "Oakley" / "woakley" / "wren.oakley@example.com" and the
#     client-shaped name "Whitfield Contracting" -- system/shipping-lane/identity_rules.py
#     (the shipping lane's own self-test identity file, header: "NOBODY REAL IS IN THIS
#     FILE. Wren Oakley does not exist.") and system/shipping-lane/fixtures/identity-fixture.md.
#   - "Fern" -- system/parts/forbidden_content.py and system/parts/completeness_receipt.py
#     ("NOBODY REAL IS IN THIS FIXTURE -- every name in it ... is invented").
#   - the five other named advisors in .claude/skills/advisory-council/example-council.md's
#     worked example (Wren Okonkwo, Ida Brennan, Sunil Varma, Marisol Ferreira, Theo
#     Lindqvist) -- a fictional council roster shipped as product documentation.
#   - "Marlowe" / "Rosalind" / "Handbook" -- system/shipping-lane/canon.py's own self-test
#     block for scan_third_party_name_shape() (the "SHAPE heuristics" section, ~2026-08-15):
#     "Marlowe's husband had an ER visit." and "He and his partner Rosalind live across two
#     homes." are synthetic POSITIVE-match fixtures in the same function and same test
#     block as the already-allowlisted "His wife Fern handles the scheduling." example;
#     "Handbook" is the synthetic NEGATIVE-match fixture right after them ("The Client
#     Handbook explains billing." -- asserts NO match fires).
# Adding a new entry here means "this exact string is independently already established as
# invented, elsewhere in this repo, for a documented reason" -- never "a real finding I
# want gone."
FICTIONAL_FIXTURE_WORDS = frozenset({
    "wren", "oakley", "woakley", "fern",
    "okonkwo", "ida", "brennan", "sunil", "varma", "marisol", "ferreira", "theo", "lindqvist",
    "marlowe", "rosalind", "handbook",
})
FICTIONAL_FIXTURE_PHRASES = ("whitfield contracting",)
# Fixture home-path usernames -- the segment right after /Users/ or /home/ that this repo's
# own examples already use for an invented account, so home-path-generic (rule 2) does not
# fire on them in whole-tree mode. Matches the task's own named set exactly.
# (moved above the WHOLE-TREE wall 2026-08-23 — see FICTIONAL_FIXTURE_USERNAMES there)

# --------------------------------------------------------- self-reference exclusions
# ⭐ RE-EXAMINED 2026-08-18 (issue #59) ALONGSIDE THE .github/ EXEMPTION, AND KEPT.
# Measured with rule 3 compiled from the real out-of-repo identity file: ZERO identity-term
# hits in either path. Neither is hiding a person. What they trip is the generic, impersonal
# cloud-drive shape, on lines whose declared job is to carry it:
#   - system/shipping-lane/fixtures/ -- 1 line, `operator-drive-account`. refuse-fixture.md's
#     own header: "THIS FILE EXISTS TO BE CAUGHT. It is deliberately full of the exact shapes
#     the shipping lane refuses ... it is never in a shipping manifest." A directory whose
#     declared job is to be a positive test fixture FOR A DIFFERENT SCANNER (verify_rules.py)
#     is not a leak when THIS scanner rediscovers it; it is that scanner working.
#   - system/shipping-lane/refuse-rules.json -- ⚠ RE-MEASURED AFTER THE 2026-08-18 TIGHTENING
#     OF operator-drive-cloudstorage: it now produces ZERO findings, so this entry is no
#     longer load-bearing. (Before the tightening it tripped 1 line; the count of "4 lines"
#     this comment used to claim for the fixtures directory was measured under the old,
#     looser rule and is likewise superseded.) KEPT ANYWAY, and this is a judgement call
#     stated plainly rather than a fact: that file's whole job is to hold leak SHAPES as
#     data, so the next rule anyone adds to it may legitimately carry an account-shaped
#     example, and CI reddening on the shipping lane documenting itself is a false positive
#     waiting to happen. It is also consumed by four other tools (scrub.py, push_gate.py,
#     verify_rules.py, canon.py) with their own tests pinned to it, so it is not this
#     check's to reshape. Delete this entry if you would rather find out.
# ⚠ Deliberately two named paths, not a directory-wide exclusion of system/shipping-lane/ --
# scrub.py, canon.py, identity_rules.py etc. in that same directory are real code where a
# genuine leak would be exactly as serious as anywhere else in the tree, and stay scanned.
WHOLE_TREE_SELF_REFERENCE_EXCLUDE_PATHS = frozenset({
    "system/shipping-lane/refuse-rules.json",
})
WHOLE_TREE_SELF_REFERENCE_EXCLUDE_PREFIXES = ("system/shipping-lane/fixtures/",)


def is_self_referential_fixture_path(path: str) -> bool:
    return (path in WHOLE_TREE_SELF_REFERENCE_EXCLUDE_PATHS
            or any(path.startswith(p) for p in WHOLE_TREE_SELF_REFERENCE_EXCLUDE_PREFIXES))

# --------------------------------------------------------- desk-persona allowlist (derived)
# ClaudeOps (the private donor system this product migrated out of) named its personal
# desks after people -- cal / marc / emily / clair / deryl / dobby. None of those six is a
# real third party; they are internal role names. But only some of the six survived into
# THIS product's own shipped skills (some were renamed to generic slugs during migration --
# e.g. cal-daily/cal-weekly -> planning-daily/planning-weekly -- while "Cal" the persona
# voice stayed in the prose). A name in this list should never trip the WARNING-tier NAME
# heuristic just for being a desk-persona word.
#
# ⚠ NOT HARDCODED TO "only cal" -- that was one auditor's read of the tree at one moment.
# derive_reused_desk_personas() below RE-CHECKS .claude/skills/ every run and only
# allowlists a candidate that is actually still present there, so a future rename (in
# either direction) changes this automatically rather than silently going stale.
DESK_PERSONA_CANDIDATES = ("cal", "marc", "emily", "clair", "deryl", "dobby")


def git_ls_files() -> list:
    """Every path `git` tracks in the current checkout (respects .gitignore by
    construction -- an ignored or untracked file was never `git add`ed, so it never
    appears here). This is the whole-tree mode's file universe: it must match what is
    actually SHIPPED, not everything sitting on disk (migration-audit/, KIMI-*, local
    .tmp scratch, etc. are gitignored and correctly invisible to a baseline audit of
    committed content)."""
    proc = subprocess.run(["git", "ls-files"], capture_output=True, text=True)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        raise SystemExit("CANNOT EVALUATE: git ls-files failed (exit {})".format(proc.returncode))
    return [p for p in proc.stdout.splitlines() if p]


def git_head_sha() -> str:
    proc = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        raise SystemExit("CANNOT EVALUATE: git rev-parse HEAD failed (exit {})".format(proc.returncode))
    return proc.stdout.strip()


def derive_reused_desk_personas(tracked_paths) -> set:
    """Gap 3: which of the six ClaudeOps desk-persona names does THIS product's own
    .claude/skills/ tree actually still reuse, right now? Checks path segments AND file
    content (case-insensitive, whole-word) so a rename that keeps the word in prose (like
    cal-daily -> planning-daily, which kept "Cal" as the voice name throughout) still
    counts as reused. Returns a set of the surviving candidate names (lowercase)."""
    skill_paths = [p for p in tracked_paths if p.startswith(".claude/skills/")]
    reused = set()
    remaining = set(DESK_PERSONA_CANDIDATES)
    word_res = {name: re.compile(r"(?i)(?<![A-Za-z0-9])" + re.escape(name) + r"(?![A-Za-z0-9])")
                for name in remaining}
    for path in skill_paths:
        if not remaining:
            break
        for name in list(remaining):
            if word_res[name].search(path):
                reused.add(name)
                remaining.discard(name)
        if not remaining:
            break
        text = read_text_file(path)
        if text is None:
            continue
        for name in list(remaining):
            if word_res[name].search(text):
                reused.add(name)
                remaining.discard(name)
    return reused


def read_text_file(path: str):
    """Returns the file's text, or None if it can't be read as UTF-8 text (binary asset,
    or genuinely unreadable) -- never raises, because one unreadable file must not abort a
    whole-tree run; it is counted as SKIPPED instead (see scan_whole_tree)."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except (UnicodeDecodeError, OSError):
        return None


# --------------------------------------------------------- WARNING-tier heuristics (gaps 2+4)
# Capitalised, name-shaped token: one capital letter then 2-14 lowercase letters, on real
# word boundaries. Deliberately does NOT match ALL-CAPS acronyms (JSON, SOP, README -- no
# lowercase run to match) and, because \b requires an actual word/non-word transition
# (never just "start of substring"), it structurally cannot match a fragment out of a
# camelCase/PascalCase compound like "GitHub" or "ClaudeOps" -- there is no boundary
# between "t" and "H" for \b to land on, so neither "Git"/"Hub" nor "Claude"/"Ops" can
# match alone out of those words.
NAME_SHAPE_RE = re.compile(r"\b[A-Z][a-z]{2,14}\b")

# Personal/relationship-role trigger words. A name-shaped token earns a WARNING only when
# it sits within a short WORD-DISTANCE of one of these (see NAME_ADJACENCY_WINDOW below) --
# not merely "appears somewhere on the same line". This is the precision lever: "a
# capitalized word" alone appears constantly in ordinary prose and code (sentence starts,
# doc headers, class names); "a capitalized word two words from 'wife' / 'client' /
# 'tenant'" is the actual shape of every incident this mode was built to catch (a wife's
# name in a fixture, a client's name in a doctrine doc, a consulting-desk name).
#
# ⚠ "coach" / "therapist" / "patient" were tried and DROPPED, on real data from this repo:
# this product's own skills are themselves styled as personas ("an interrogative
# intelligence coach", "a detective") and use those exact words constantly as METAPHOR, not
# as a real personal relationship -- e.g. .claude/skills/first-principles/SKILL.md's own
# "Role:" line ("the interrogative intelligence coach"). Measured false-positive source,
# not a hypothetical one -- see the task report for the before/after count.
PERSONAL_TRIGGER_WORDS = (
    "wife", "husband", "spouse", "partner", "girlfriend", "boyfriend", "fiance", "fiancee",
    "client", "customer", "tenant",
    "friend", "colleague", "coworker", "neighbor", "neighbour",
    "daughter", "son", "mother", "father", "mom", "dad", "sister", "brother",
    "cousin", "nephew", "niece", "grandma", "grandpa", "grandmother", "grandfather",
    "roommate", "landlord", "babysitter", "nanny",
)
PERSONAL_TRIGGER_WORDS_LOWER = frozenset(PERSONAL_TRIGGER_WORDS)

# How the name-shape/trigger co-occurrence is actually judged: tokenize the line into
# letters-only words, find every trigger-word position, and only flag a name-shaped token
# within this many WORD positions of a trigger (not characters, not "same line") --
# measured against this repo's real content: a same-line-only rule flagged unrelated words
# from the far end of a long sentence or a markdown header ("### Sunil \"The Room\" Varma
# -- The Customer's Voice" flagged "Room"/"Voice" off the word "Customer" three lines
# away in char-terms but adjacent in word-terms -- narrowing the window to 2 still isn't
# enough on its own, which is why the heading/bold-label guards below exist too).
NAME_ADJACENCY_WINDOW = 2
_LETTER_WORD_RE = re.compile(r"[A-Za-z]+")

# Gap 4: a SPECIFIC-DECIMAL dollar figure (the shape a real invoice/ledger line takes --
# "$4,250.00", never a round "$500" that is far more likely to be an example/estimate)
# sharing a line with a billing-context word.
DOLLAR_AMOUNT_RE = re.compile(r"\$[0-9][0-9,]*\.[0-9]{2}\b")

# ⭐ WHY THESE ARE STEMS AND NOT WORDS -- THE 2026-08-18 MISS, AND ITS ACTUAL CAUSE.
# The list here was ("tenant", "billing", "client", "invoice"). system/tools/emit_status.py
# carried a real desk's real receivables total in a shipped docstring, on a line whose
# billing word was "unbilled" -- which contains "billed", not "billing". The rule read that
# line and reported the file clean. Adding "unbilled" fixes that one line and nothing else.
#
# The CAUSE was not a missing word, it was MORPHOLOGY: "bill", "billed", "billing",
# "billable" and "unbilled" are one concept, and a flat word list has to enumerate every
# inflection of every concept or lose to the one it forgot. (It is also the second
# list-shaped rule in this file to miss for a near-miss reason -- see PERSONAL_TRIGGER_WORDS.)
# So each entry below is a STEM PLUS ITS BOUNDED SUFFIXES, which kills the whole class
# instead of one instance. The suffixes are explicit, never ".*" -- an open suffix would make
# "bill" match "billion"/"billionaire", and the outer lookarounds cannot save it.
#
# ⚠ HOW FAR TO WIDEN IS A MEASURED QUESTION, NOT A TASTE ONE, AND IT WAS MEASURED.
# The whole tracked tree contains SIX lines carrying a specific-decimal figure at all (the
# DOLLAR_AMOUNT_RE half is already the narrow half). Five of the six are teaching examples
# about MODEL SPEND -- their vocabulary is "cost", "ratio", "projected", "realized",
# "estimate". That is the shape of this product's honest dollar traffic, and it is a
# different vocabulary from a receivables line. Hence the split below:
#   ADDED -- money OWED or SETTLED between two parties. Near a specific-decimal figure this
#            is a ledger line, not prose. Marginal false positives on the current tree: 0.
#   REJECTED -- "rate", "fee(s)", "price", "cost", "spend", "budget", "estimate", "quote",
#            "statement", "account", "credit", "debit", "paid", "due", "receipt". These are
#            either (a) the measured vocabulary of this repo's own model-spend examples
#            ("cost" and "estimate" each collide with a REAL line in the tree today -- adding
#            "estimate" flags this file's own comment two lines below), or (b) ordinary
#            technical English ("error rate", "if statement", "API client account",
#            "paid tier", "due to"). A gate that flags every priced example gets ignored, and
#            an ignored gate is worse than the miss it was widened to prevent.
#   NOT ADDED, LOW YIELD -- "salary", "wage", "payroll", "revenue", "income", "expense",
#            "subtotal", "reimbursement". Clean words, but a real line carrying any of them
#            almost always also says payment/balance/deposit/owed, which are already here.
BILLING_TRIGGER_STEMS = (
    # --- money OWED: what an unpaid ledger line says ---
    r"bill(?:ed|ing|able|s)?",          # bill / billed / billing / billable / bills
    r"unbill(?:ed|able)",               # ⭐ the miss that prompted this -- needs its own
                                        # entry, because the "un" prefix is alphanumeric and
                                        # the left-hand lookaround refuses to fire inside it
    r"invoic(?:e|ed|es|ing)",
    r"receivable(?:s)?",
    r"payable(?:s)?",
    r"retainer(?:s)?",
    r"arrears",
    r"overdue",
    r"past[ -]due",
    r"outstanding",
    r"unpaid",
    r"owe(?:d|s)?",                     # owe / owed / owes -- NOT "owner" (suffix is bounded)
    r"owing",
    r"balance(?:s)?",                   # NOT "balanced"/"balancing" -- ordinary prose
    # --- money SETTLED: what a paid ledger line says ---
    r"remittance",
    r"payment(?:s)?",
    r"payout(?:s)?",
    r"refund(?:ed|s)?",
    r"deposit(?:ed|s)?",
    r"ledger(?:s)?",
    # --- income side ---
    r"earnings",
    r"commission(?:s|ed)?",
    # --- who the money is with (both carried over from the original list) ---
    r"client(?:s)?",
    r"tenant(?:s)?",
)
# Kept under the old name so nothing downstream breaks; it is now stems, not plain words.
BILLING_TRIGGER_WORDS = BILLING_TRIGGER_STEMS
BILLING_TRIGGER_RE = re.compile(
    r"(?i)(?<![A-Za-z0-9])(" + "|".join(BILLING_TRIGGER_STEMS) + r")(?![A-Za-z0-9])")

# Common capitalised English words / doc vocabulary / product terms that are NAME-shaped by
# the regex above but are not names. Kept short and reviewable on purpose (see the module's
# ⛔ NO PER-FILE SUPPRESSION note) -- this is a STOPWORD list, the same kind of thing every
# spell-checker ships, not a per-finding override. Case-insensitive comparison.
NAME_HEURISTIC_STOPWORDS = frozenset({
    # pronouns -- capitalised mid-sentence constantly in second-person instructional prose
    # ("You are the design lead... You speak it perfectly... they never lead you.") which is
    # this whole corpus's dominant register; the single biggest false-positive source found
    # in the first real run against this repo.
    "you", "your", "yours", "yourself", "yourselves", "we", "our", "ours", "us",
    "he", "she", "him", "her", "hers", "his", "they", "them", "their", "theirs",
    "it", "its", "who", "whom", "whose", "what", "which",
    # sentence-structure words that are capitalised only because they start a sentence
    "the", "this", "that", "these", "those", "when", "where", "while", "with", "without",
    "after", "before", "then", "than", "also", "only", "even", "just", "like", "such",
    "some", "any", "every", "each", "there", "here", "now", "not", "but", "and",
    "for", "from", "into", "onto", "over", "under", "about", "above", "below", "between",
    "among", "through", "across", "around", "behind", "beyond", "within", "toward",
    "towards", "against", "along", "per", "via", "once", "if", "so", "because", "since",
    "until", "during", "unless", "although", "though", "whether", "either", "neither",
    "another", "other", "same", "more", "most", "less", "least", "many", "much", "few",
    "several", "all", "both", "none", "one", "two", "three", "four", "five", "six", "seven",
    "eight", "nine", "ten", "first", "second", "third", "next", "last", "final",
    "is", "was", "were", "are", "be", "been", "being", "has", "have", "had", "do", "does",
    "did", "will", "would", "should", "could", "can", "may", "might", "must", "shall", "get",
    "note", "warning", "important", "see", "example", "usage", "args", "returns", "raises",
    "todo", "fixme", "fix", "update", "add", "remove", "delete", "create", "new", "old",
    "yes", "no", "true", "false", "none", "null",
    # weekdays / months
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "january", "february", "march", "april", "may", "june", "july", "august", "september",
    "october", "november", "december",
    # product / platform terms this repo says constantly and are not people
    "claude", "anthropic", "claudeops", "google", "gmail", "drive", "slack", "python",
    "markdown", "github", "opus", "sonnet", "haiku", "wren",  # "wren" also FICTIONAL_FIXTURE
    "dropbox", "script", "apps",  # "cloud-drive client (Dropbox...)" / "not just Apps Script"
    # this corpus's own persona/role vocabulary -- every skill in this product is styled as
    # a character ("detective", "coach", "operator", "customer", "voice"), and those role
    # words are themselves name-shaped and constantly adjacent to the trigger words above.
    # This is a corpus-specific stopword addition, same category as the pronoun block:
    # both were added from a REAL run's output, not guessed in advance.
    "role", "bias", "refuses", "catches", "convene", "domain", "voice", "room", "runway",
    "opportunity", "fixed", "detective", "operator", "skeptic",
    # generic marketing/business jargon this corpus's worked examples use a lot
    # ("Target customer", "Market/customer insight") -- not people either.
    "target", "market",
})


def find_name_candidates(line: str, allowed_personas: frozenset) -> list:
    """Gap 2 detector. Returns the list of name-shaped tokens on this LINE that sit within
    NAME_ADJACENCY_WINDOW word-positions of a personal-trigger word, after the guards below
    -- never a bare same-line co-occurrence (see PERSONAL_TRIGGER_WORDS comment for why that
    was too broad on real data)."""
    stripped = line.strip()
    if stripped.startswith("#"):
        # ATX markdown heading -- structural label prose ("### Sunil \"The Room\" Varma —
        # The Customer's Voice"), not the narrative-sentence register a real leak appears
        # in. Measured false-positive source on this repo's real content.
        return []

    words = list(_LETTER_WORD_RE.finditer(line))
    trigger_positions = [i for i, w in enumerate(words)
                          if w.group(0).lower() in PERSONAL_TRIGGER_WORDS_LOWER]
    if not trigger_positions:
        return []

    hits = []
    for i, w in enumerate(words):
        token = w.group(0)
        if not (token[0].isupper() and 3 <= len(token) <= 15 and token[1:].islower()):
            continue  # not name-shaped (see NAME_SHAPE_RE for the equivalent regex form)
        low = token.lower()
        if low in PERSONAL_TRIGGER_WORDS_LOWER:
            continue  # the trigger word itself, not a candidate name next to one
        if low in NAME_HEURISTIC_STOPWORDS or low in FICTIONAL_FIXTURE_WORDS or low in allowed_personas:
            continue
        if not any(abs(i - tp) <= NAME_ADJACENCY_WINDOW for tp in trigger_positions):
            continue  # not actually near a trigger word, just elsewhere on a long line
        # bold-markdown label guard: "**Term:** description" -- the word right after "**"
        # and right before ":" is a doc-structure label, not a name in a sentence.
        start = w.start()
        if line[max(0, start - 2):start] == "**":
            continue
        end = w.end()
        if end < len(line) and line[end] == ":":
            continue
        hits.append(token)
    return hits


def scan_whole_tree(scan_root_paths=None):
    """The whole-tree baseline audit (gap 1, carrying gaps 2-4). Returns a dict shaped for
    both the human-readable report and the JSON artifact -- see main()'s --whole-tree
    branch for how each half is rendered. Raises SystemExit(CANNOT_EVALUATE-worthy message)
    on anything that means the run could not be trusted (git failure, no files found)."""
    tracked = scan_root_paths if scan_root_paths is not None else git_ls_files()
    if not tracked:
        raise SystemExit("CANNOT EVALUATE: git ls-files returned zero tracked files -- "
                          "not run from inside a git checkout?")

    allowed_personas = derive_reused_desk_personas(tracked)

    blocking = []
    warnings = []
    files_scanned = 0
    files_skipped_binary = 0

    for path in tracked:
        path_rule = check_path(path)
        if path_rule:
            blocking.append({
                "severity": BLOCKING, "path": path, "line": None,
                "rule_id": path_rule["id"], "remedy": path_rule["remedy"], "evidence": None,
            })
        if is_self_referential_fixture_path(path):
            # see WHOLE_TREE_SELF_REFERENCE_EXCLUDE_PATHS/PREFIXES for the two named,
            # documented reasons this is not a general suppression mechanism.
            continue

        text = read_text_file(path)
        if text is None:
            files_skipped_binary += 1
            continue
        files_scanned += 1

        already = set()
        for lineno, line in enumerate(text.splitlines(), start=1):
            # ---- BLOCKING: the same identity/home-path patterns the per-PR gate uses ----
            for rule in content_patterns():
                m = re.search(rule["pattern"], line)
                if not m:
                    continue
                if rule["id"] == "home-path-generic":
                    # extract the segment right after /Users/ or /home/
                    seg_match = re.search(r"(?:/Users/|/home/)([A-Za-z0-9._-]+)", line)
                    seg = seg_match.group(1) if seg_match else ""
                    if seg.lower() in FICTIONAL_FIXTURE_USERNAMES:
                        continue  # allowlisted fixture path -- see FICTIONAL_FIXTURE_USERNAMES
                # ⛔ a rule-3 hit NEVER puts the matched term in the report -- this dict is
                # serialized straight into a PUBLIC build artifact. See redact_spans().
                evidence = redact_spans(line, rule) if is_identity_rule(rule["id"]) else line
                blocking.append({
                    "severity": BLOCKING, "path": path, "line": lineno,
                    "rule_id": rule["id"], "remedy": rule["remedy"],
                    "evidence": evidence.strip()[:200],
                })
                already.add((lineno, rule["id"]))

        # ---- BLOCKING, second pass: whole-text (Defect 2 -- see whole_text_hits()) ----
        # Run over `text` RAW and UNSPLIT (never the per-line loop above's already-split
        # copy), so a multi-word identity term whose space was replaced by a genuine line-
        # boundary character is still whole in what this pass looks at.
        for lineno, evidence, rule in whole_text_hits(text, already):
            shown = redact_spans(evidence, rule) if is_identity_rule(rule["id"]) else evidence
            blocking.append({
                "severity": BLOCKING, "path": path, "line": lineno,
                "rule_id": rule["id"], "remedy": rule["remedy"],
                "evidence": shown.strip()[:200],
            })

        for lineno, line in enumerate(text.splitlines(), start=1):
            # ---- WARNING gap 2: third-party name heuristic ----
            if any(phrase in line.lower() for phrase in FICTIONAL_FIXTURE_PHRASES):
                name_hits = []
            else:
                name_hits = find_name_candidates(line, allowed_personas)
            for token in name_hits:
                warnings.append({
                    "severity": WARNING, "path": path, "line": lineno,
                    "rule_id": "possible-third-party-name",
                    "remedy": (
                        "a capitalised name-shaped word ('{}') sits near a "
                        "personal/relationship word on this line. If this names a real "
                        "person other than the operator, remove it or genericize it; if it "
                        "is product content or an established fictional fixture, add it to "
                        "FICTIONAL_FIXTURE_WORDS with the same provenance comment as the "
                        "existing entries.".format(token)),
                    "evidence": line.strip()[:200],
                })

            # ---- WARNING gap 4: dollar amount near a billing-context word ----
            if BILLING_TRIGGER_RE.search(line) and DOLLAR_AMOUNT_RE.search(line):
                warnings.append({
                    "severity": WARNING, "path": path, "line": lineno,
                    "rule_id": "dollar-amount-near-billing-word",
                    "remedy": (
                        "a specific-decimal dollar figure shares this line with a "
                        "billing-context word (see BILLING_TRIGGER_STEMS). If this is a real "
                        "figure from a real dispute/invoice/ledger, remove it or round it "
                        "into a non-identifying example; if it is a worked example, say so "
                        "explicitly in the surrounding text."),
                    "evidence": line.strip()[:200],
                })

    return {
        "files_scanned": files_scanned,
        "files_skipped_binary": files_skipped_binary,
        "reused_desk_personas": sorted(allowed_personas),
        "blocking": blocking,
        "warnings": warnings,
    }


# --------------------------------------------------------------------------- git diff parsing

HUNK_HEADER_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def run_git_diff(base: str, head: str, mode: str) -> str:
    if mode == "merge-base":
        rng = "{}...{}".format(base, head)
    elif mode == "linear":
        rng = None
    else:
        raise SystemExit("CANNOT EVALUATE: unknown --mode {!r}".format(mode))

    cmd = ["git", "diff", "--unified=0", "--no-color", "--no-renames"]
    if rng is not None:
        cmd.append(rng)
    else:
        cmd.extend([base, head])

    proc = subprocess.run(cmd, capture_output=True, text=True)
    # git diff exits 0 (no differences under some invocations) or 1 (differences found)
    # on a SUCCESSFUL run; anything else means the refs/SHAs themselves were bad.
    if proc.returncode not in (0, 1):
        sys.stderr.write(proc.stderr)
        raise SystemExit(
            "CANNOT EVALUATE: git diff failed (exit {}) for {} {} {}".format(
                proc.returncode, mode, base, head))
    return proc.stdout


def parse_unified_diff(diff_text: str):
    """Yields (path, [(lineno, line_text), ...]) for every file the diff touches, added
    lines only. A pure deletion (new path is /dev/null) yields nothing for that file --
    removing a file introduces nothing to scan. A binary file's changed content is
    unreadable as text and is skipped (git diff already can't show it as +lines)."""
    path = None
    added = []
    next_lineno = None

    def flush():
        if path is not None:
            yield_path = path
            yield_added = added
            return yield_path, yield_added
        return None, []

    files = []
    # ⚠ `.split("\n")`, NEVER `.splitlines()` -- git's own diff format is LF-delimited
    # ONLY, so splitting on bare "\n" reproduces exactly the records git wrote. Python's
    # str.splitlines() additionally breaks on CR, VT, FF, NEL, LINE SEPARATOR, PARAGRAPH
    # SEPARATOR and friends -- and git does NOT split a source line's own content on any
    # of those, so a "+" line whose ORIGINAL file content contains one of them arrives here
    # as ONE line with that byte embedded in the middle. Using .splitlines() here would
    # silently fracture that single diff record into two, one of which loses its "+"
    # prefix and is dropped -- destroying the exact evidence the whole-text pass (Defect 2,
    # see whole_text_hits() in this file) needs to still be present in `added`'s text.
    for raw_line in diff_text.split("\n"):
        if raw_line.startswith("diff --git "):
            if path is not None:
                files.append((path, added))
            path = None
            added = []
            next_lineno = None
            continue
        if raw_line.startswith("+++ "):
            new_path = raw_line[4:]
            if new_path == "/dev/null":
                path = None  # pure deletion -- nothing to scan
            else:
                # "+++ b/some/path" -> "some/path"
                path = new_path[2:] if new_path.startswith("b/") else new_path
            continue
        if raw_line.startswith("--- "):
            continue
        m = HUNK_HEADER_RE.match(raw_line)
        if m:
            next_lineno = int(m.group(1))
            continue
        if path is None:
            continue
        if raw_line.startswith("+") and not raw_line.startswith("+++"):
            line_text = raw_line[1:]
            if next_lineno is None:
                next_lineno = 1
            added.append((next_lineno, line_text))
            next_lineno += 1
        elif raw_line.startswith("-") and not raw_line.startswith("---"):
            continue  # removed line -- never "introduced"
        # anything else ("Binary files ... differ", \ No newline at end of file, etc.)
        # is neither a path header nor an added line -- ignored, not scanned.
    if path is not None:
        files.append((path, added))
    return files


# --------------------------------------------------------------------------- rule engines

def check_path(path: str):
    for rule in PATH_DENYLIST:
        if re.search(rule["pattern"], path):
            return rule
    return None


def check_added_lines(added_lines):
    hits = []
    for lineno, text in added_lines:
        for rule in content_patterns():
            if not re.search(rule["pattern"], text):
                continue
            # Same fixture carve-out scan_whole_tree() already applies (RULED 2026-08-23).
            if rule["id"] == "home-path-generic":
                seg_match = re.search(r"(?:/Users/|/home/)([A-Za-z0-9._-]+)", text)
                seg = seg_match.group(1) if seg_match else ""
                if seg.lower() in FICTIONAL_FIXTURE_USERNAMES:
                    continue
            hits.append((lineno, text, rule))
    return hits


def whole_text_hits(text, already):
    """The SECOND pass, over `text` WHOLE and UNSPLIT -- never `.splitlines()`'d first.

    WHY THIS EXISTS (2026-08-28, Defect 2). `check_added_lines()` above can only ever see
    what survives `str.splitlines()`, and that call is exactly what erases a term split by
    a line-boundary character: by the time a "line" reaches the per-line pass, the boundary
    byte that WAS the middle of a two-word identity term is gone, consumed as the split
    point. `identity_rules.compile_term()` (this same date) now matches ANY run of
    whitespace/line-boundary characters between a multi-word term's words -- including a
    real LF, CRLF, VT, FF, NEL, LINE SEPARATOR or PARAGRAPH SEPARATOR -- so running the SAME
    compiled patterns against the RAW text (which still has that byte in it) is enough. The
    per-line pass is kept, not replaced (see module docstring) -- this is additive.

    `already` is the set of (lineno, rule_id) the per-line pass already reported for this
    file, so an intact term on one ordinary line is not reported twice.

    ⚠ THIS IS WHERE THE FALSE-POSITIVE RISK LIVES. A whitespace-flexible multi-word pattern
    run over WHOLE, UNSPLIT text can match across a paragraph break that has nothing to do
    with the term -- see CLAUDE.md's "FALSE POSITIVES" note. That is the accepted, MEASURED
    cost of closing a fail-open hole on a fail-closed gate; it is not fixed here."""
    hits = []
    for rule in content_patterns():
        for m in re.finditer(rule["pattern"], text):
            lineno = text.count("\n", 0, m.start()) + 1
            if (lineno, rule["id"]) in already:
                continue
            evidence = text[m.start():m.end()]
            if rule["id"] == "home-path-generic":
                seg_match = re.search(r"(?:/Users/|/home/)([A-Za-z0-9._-]+)", evidence)
                seg = seg_match.group(1) if seg_match else ""
                if seg.lower() in FICTIONAL_FIXTURE_USERNAMES:
                    continue
            hits.append((lineno, evidence, rule))
    return hits


def format_violation(path, rule, lineno=None, evidence=None):
    where = "file={}".format(path)
    if lineno is not None:
        where += ",line={}".format(lineno)
    source_note = ""
    if is_identity_rule(rule["id"]):
        source_note = " [rule 3, compiled at runtime from your identity file -- not in this repo]"
    elif rule.get("source"):
        source_note = " [same shape as system/shipping-lane/refuse-rules.json id={}]".format(
            rule["source"])
    header = "::error {}::[{}] {}{}".format(where, rule["id"], rule["remedy"], source_note)
    lines = [header]
    if evidence is not None:
        # ⛔ never echo a matched identity term into a public CI log -- see redact_spans().
        shown = redact_spans(evidence, rule) if is_identity_rule(rule["id"]) else evidence
        lines.append("    {}:{}: {}".format(path, lineno, shown.strip()[:200]))
    return "\n".join(lines)


def scan_files(file_diffs, whole_texts=None):
    """file_diffs: list of (path, added_lines). `whole_texts`, if given, maps path -> the
    RAW, UNSPLIT text of everything this diff added for that path (--scan-file mode: the
    whole file, since the whole file counts as added; git-diff mode: the added lines
    rejoined with "\\n", in order -- see main()). Runs the whole-text pass (Defect 2, see
    whole_text_hits()) alongside the per-line one whenever that text is available. Returns
    list of violation strings."""
    violations = []
    for path, added_lines in file_diffs:
        path_rule = check_path(path)
        if path_rule:
            violations.append(format_violation(path, path_rule))
            # a denylisted path still gets its content checked below too -- multiple
            # independent findings on one file are all worth surfacing at once.
        already = set()
        for lineno, text, rule in check_added_lines(added_lines):
            violations.append(format_violation(path, rule, lineno, text))
            already.add((lineno, rule["id"]))
        whole = (whole_texts or {}).get(path)
        if whole is not None:
            for lineno, evidence, rule in whole_text_hits(whole, already):
                violations.append(format_violation(path, rule, lineno, evidence))
    return violations


# --------------------------------------------------------------------------------- CLI

def render_finding(f):
    tag = "::error" if f["severity"] == BLOCKING else "::warning"
    where = "file={}".format(f["path"])
    if f["line"] is not None:
        where += ",line={}".format(f["line"])
    header = "{} {}::[{}] {}".format(tag, where, f["rule_id"], f["remedy"])
    lines = [header]
    if f["evidence"] is not None:
        lines.append("    {}:{}: {}".format(f["path"], f["line"], f["evidence"]))
    return "\n".join(lines)


def run_whole_tree_mode(args) -> int:
    """CANNOT_EVALUATE (2) on any error that means the run itself could not be trusted --
    fail loudly, never a clean-looking exit on a broken run. FLAGGED (1) if any BLOCKING
    finding exists (a real, already-committed leak the baseline caught). CLEAN (0)
    otherwise -- including when WARNING-tier findings exist; see module docstring for why
    WARNING never changes the exit code."""
    try:
        result = scan_whole_tree()
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return CANNOT_EVALUATE

    try:
        head_sha = git_head_sha()
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return CANNOT_EVALUATE

    blocking = result["blocking"]
    warnings = result["warnings"]
    generated_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    report = {
        "schema": "no-internal-leakage/whole-tree-report/v1",
        "generated_at_utc": generated_at,
        "head_sha": head_sha,
        "mode": "whole-tree",
        "files_scanned": result["files_scanned"],
        "files_skipped_binary": result["files_skipped_binary"],
        "reused_desk_personas": result["reused_desk_personas"],
        "blocking_count": len(blocking),
        "warning_count": len(warnings),
        "blocking": blocking,
        "warnings": warnings,
    }

    if args.report_out:
        with open(args.report_out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, sort_keys=True)
            fh.write("\n")

    print("NO-INTERNAL-LEAKAGE whole-tree baseline -- generated {} at {}".format(
        head_sha[:12], generated_at))
    print("{} file(s) scanned, {} skipped as binary/unreadable, desk-personas reused in "
          ".claude/skills/: {}".format(
              result["files_scanned"], result["files_skipped_binary"],
              ", ".join(result["reused_desk_personas"]) or "(none)"))
    print("{} BLOCKING violation(s), {} WARNING (human-review) finding(s)\n".format(
        len(blocking), len(warnings)))

    for f in blocking:
        print(render_finding(f))
    if blocking and warnings:
        print("")
    for f in warnings:
        print(render_finding(f))

    if blocking:
        print("\nFAIL: {} BLOCKING violation(s) -- see above.".format(len(blocking)))
        return FLAGGED

    if warnings:
        print("\nCLEAN (no BLOCKING violation) -- {} WARNING finding(s) above need human "
              "review; they do not fail this job.".format(len(warnings)))
    else:
        print("\nCLEAN -- 0 BLOCKING, 0 WARNING.")
    return CLEAN


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", help="base SHA/ref (CI mode)")
    ap.add_argument("--head", help="head SHA/ref (CI mode)")
    ap.add_argument("--mode", choices=["merge-base", "linear"], default="merge-base",
                     help="merge-base -> git diff BASE...HEAD (pull_request); "
                          "linear -> git diff BASE HEAD (push)")
    ap.add_argument("--scan-file", help="manual/fixture mode: scan one file's full "
                                        "content as if every line were added (no git)")
    ap.add_argument("--as-path", help="repo-relative path to report --scan-file under "
                                      "(defaults to --scan-file's own path)")
    ap.add_argument("--whole-tree", action="store_true",
                     help="baseline audit mode: rescan every git-tracked file in full "
                          "(not a diff). See module docstring, WHOLE-TREE BASELINE MODE. "
                          "Mutually exclusive with --base/--head/--scan-file.")
    ap.add_argument("--report-out",
                     help="--whole-tree only: write the full JSON report to this path "
                          "(machine-readable evidence the run actually executed -- see "
                          "the workflow that calls this mode).")
    ap.add_argument("--identity",
                     help="rule 3's term list: one term per line, '#' comments. Default: "
                          "$SHIP_IDENTITY, then <notes>/config/ship-identity.md. NEVER a "
                          "file inside this repo. Absent/empty -> exit 2, never exit 0.")
    args = ap.parse_args()

    # ⛔ BEFORE ANY SCAN, IN EVERY MODE. A missing identity file is CANNOT EVALUATE (2),
    # loudly, with the fix named -- never a scan on the generic tier alone that prints
    # "clean" over a file carrying the operator's own name. This is the same fail-closed
    # contract push_gate.py already refuses on, and the reason this file exists at all.
    try:
        install_identity_patterns(args.identity)
    except IdentityUnavailable as e:
        print("CANNOT EVALUATE: {}\n"
              "\n"
              "  The operator-identity tier (rule 3) could not be compiled, so this run "
              "was NOT a clean scan -- it was no scan at all, and is reported as such "
              "rather than as a pass.\n"
              "  ON A GITHUB RUNNER: set the SHIP_IDENTITY_TERMS repository secret; the "
              "workflow writes it to a runner-local file and exports $SHIP_IDENTITY. See "
              ".github/workflows/no-internal-leakage.yml.".format(e), file=sys.stderr)
        return CANNOT_EVALUATE

    if args.whole_tree:
        return run_whole_tree_mode(args)

    if args.scan_file:
        with open(args.scan_file, "r", encoding="utf-8") as fh:
            text = fh.read()
        added_lines = list(enumerate(text.splitlines(), start=1))
        path = args.as_path or args.scan_file
        file_diffs = [(path, added_lines)]
        # The RAW, UNSPLIT text -- see whole_text_hits(). A --scan-file run treats the
        # whole file as added, so the whole file is exactly what the whole-text pass wants.
        whole_texts = {path: text}
    elif args.base and args.head:
        diff_text = run_git_diff(args.base, args.head, args.mode)
        file_diffs = parse_unified_diff(diff_text)
        # Best-effort whole-text reconstruction for the second pass: the added lines for
        # each file, rejoined in order with "\n". This still catches a term split by an
        # exotic line-boundary character WITHIN one diff line -- parse_unified_diff() now
        # splits the diff document on bare "\n" (not str.splitlines()), so a "+" line's own
        # text keeps any embedded CR/VT/FF/NEL/LS/PS byte instead of having Python's
        # splitlines() silently break the diff record on it. What this reconstruction does
        # NOT recover: a hard-wrap or paragraph break the *diff* itself represents as two
        # separate "+" lines already had that boundary consumed by `git diff`'s own \n-based
        # format before this script ever sees it -- rejoining with "\n" restores an LF at
        # that seam, which is enough for identity_rules.py's whitespace-flexible pattern to
        # still match across it.
        whole_texts = {
            path: "\n".join(text for _, text in added_lines)
            for path, added_lines in file_diffs
        }
    else:
        ap.error("either --scan-file, or both --base and --head, are required")
        return CANNOT_EVALUATE

    violations = scan_files(file_diffs, whole_texts)

    if violations:
        print("NO-INTERNAL-LEAKAGE: {} violation(s) found\n".format(len(violations)))
        for v in violations:
            print(v)
        print("\n{} file(s) scanned, {} violation(s). See each line above for the "
              "matched rule and what to do instead.".format(len(file_diffs), len(violations)))
        return FLAGGED

    print("NO-INTERNAL-LEAKAGE: clean ({} file(s) scanned, 0 violations)".format(len(file_diffs)))
    return CLEAN


if __name__ == "__main__":
    sys.exit(main())

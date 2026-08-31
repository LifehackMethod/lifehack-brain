#!/usr/bin/env python3
"""check_fix_needs_pr_body_citation.py -- K.E2: the PR-body citation gate.

WHY THIS EXISTS: sweeper.py (K.E1) proved the actual defect mechanically --
fixes in this repo land with the issue number cited in a code comment, a
docstring, or a commit message, but never in the ONE string GitHub itself
reads to auto-close a tracker item: "Fixes #N" / "Closes #N" / "Resolves #N"
in the PR BODY. So a real fix ships, the issue stays open forever, and the
tracker silently overstates how broken the repo is. sweeper.py is the after-
the-fact detector for the issues this ALREADY happened to. This gate is the
at-the-source fix: catch it on the PR that is ABOUT to make it happen again,
before it merges, while it is still one click to fix (add the line to the
PR body).

WHAT THIS DOES NOT DO, ON PURPOSE: it never requires every PR to reference
an issue, never blocks a PR that doesn't touch a tracked defect at all, and
never tries to guess whether a change "counts as" a fix. It fires on exactly
one shape, and nothing else:

    THE DIFF ITSELF (lines a PR ADDS) ALREADY CONTAINS a corrective-state
    phrase sitting next to a "#N" citation, for an issue N that IS CURRENTLY
    OPEN on the tracker.

That is: the PR's own author already wrote the words that describe a fix for
a specific open issue, somewhere in a comment/docstring/commit -- the gate
only asks that the SAME fact also be written where GitHub can act on it.

⛔⛔⛔ WHY THIS AVOIDS THE "GATE THAT FALSE-FIRES GETS DISABLED" FAILURE MODE:
A gate that blocks ordinary work gets turned off by the first annoyed
maintainer, and then it protects nothing -- worse than never having existed,
because everyone still believes it is running. This gate is activation-gated,
not universally-gated:
  1. It only inspects ADDED lines of the diff (never touches unrelated
     existing code) -- exactly `check_no_internal_leakage.py`'s convention,
     reused here rather than reinvented (parse_unified_diff / run_git_diff
     below are line-for-line the same shape as that file's).
  2. A citation must survive the SAME false-positive filter sweeper.py uses
     (version strings, percentages, hex colours, "prohibition #13"-style
     numbered-list references, "Invoice #42"-style string-fixture literals)
     -- so an ordinary PR that happens to add a line with "#13" in a
     percentage or a test fixture cannot trip it.
  3. A corrective-state phrase (the same widened vocabulary as sweeper.py:
     fix/fixes/fixed/closes/resolved/patched/addressed/"no longer
     trust(ing)"/restored/load-bearing) must sit on THAT SAME LINE.
  4. The cited issue number must be an issue that is CURRENTLY OPEN on the
     live tracker -- a PR that mentions an already-closed issue, or a
     made-up number, or a pull request number, does not trip this.
  A PR has to satisfy all four before this gate even looks at the PR body.
  The overwhelming majority of ordinary commits -- feature work, refactors,
  docs, anything not narrating "this fixes open issue #N" in its own diff --
  never come near this path, so it never asks anything of them, and there is
  nothing here for a maintainer to get tired of and disable. It only ever
  speaks up at the exact moment a PR is already one sentence away from
  silently repeating the defect this whole tool exists to answer.

WHAT IT REQUIRES ONCE ACTIVATED: the PR body must contain a GitHub-recognized
closing keyword (close/closes/closed/fix/fixes/fixed/resolve/resolves/
resolved) immediately followed by "#N" for the SAME N the diff cited. This is
deliberately the exact string GitHub's own auto-close parser looks for --
this gate does not invent its own convention, it enforces GitHub's.

⚠ THIS GATE NEVER CLOSES, COMMENTS ON, OR EDITS AN ISSUE, AND NEVER MERGES OR
BLOCKS A MERGE ON ITS OWN AUTHORITY BEYOND REPORTING A FAILED CHECK -- same
posture as sweeper.py and as this repo's other two gates (leakage, version
bump): it reports; branch protection (a human's own repo setting) is what
turns a FLAGGED check into a blocked merge, and a human can always override
it there, same as the other two.

EXIT CODES (same three-state contract as check_no_internal_leakage.py /
check_plugin_version_bumped.py -- no fourth state, no silent pass on error):
  0  NOT-TRIGGERED or SATISFIED -- either the diff cited no open issue with a
     corrective phrase (ordinary PR, gate never activated), or it did and the
     PR body already carries the matching closing keyword. Indistinguishable
     to a caller on purpose: both are "nothing to fix here."
  1  FLAGGED -- the diff cites a corrective fix for a currently-open issue
     #N, and the PR body does NOT carry a GitHub closing keyword + #N for
     that issue. Names the specific issue, the line that triggered it, and
     the exact fix.
  2  CANNOT EVALUATE -- git diff failed, --repo/--pr-body-file args missing
     or unreadable, or the GitHub API lookup for open/closed state itself
     failed (rate limit, auth, network). NEVER exit 0 on an evaluation
     failure -- an ungated PR must never look identical to a satisfied one.

USAGE
  CI (production path):
    check_fix_needs_pr_body_citation.py --base <sha> --head <sha> --mode merge-base \\
        --repo OWNER/NAME --pr-body-file <path to PR body text>

  Manual / fixture testing (no git needed):
    check_fix_needs_pr_body_citation.py --scan-file /tmp/fixture.diff \\
        --repo OWNER/NAME --pr-body-file /tmp/body.txt --offline-open-issues 58,94
    (--offline-open-issues skips the live `gh api` lookup -- for demos/tests only; CI
    never passes it, so CI always checks the REAL tracker state.)
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys

# K.E2 ruling: reuse, don't reinvent -- both scripts live in .github/scripts/, so this
# resolves as a plain sibling import when run as `python3 .github/scripts/<name>.py`.
from check_no_internal_leakage import run_git_diff, parse_unified_diff

NOT_TRIGGERED, FLAGGED, CANNOT_EVALUATE = 0, 1, 2

# ----------------------------------------------------------------------------------
# Reused verbatim from sweeper.py (K.E1) -- see that file's "THE WIDENING RULE" and
# false-positive sections for the reasoning. If sweeper.py's vocabulary changes, this
# file's copy must be updated alongside it -- test_check_fix_needs_pr_body_citation.py
# asserts both files' pattern sources stay textually identical, so drift fails CI
# rather than silently diverging.
#
# run_git_diff() and parse_unified_diff() themselves are NOT copied here -- they are
# imported, verbatim, from check_no_internal_leakage.py (K.E2 ruling): both scripts sit
# in this same .github/scripts/ directory, so a plain `import check_no_internal_leakage`
# resolves under CI's own invocation (`python3 .github/scripts/<name>.py` puts the
# script's own directory at sys.path[0] automatically -- no sys.path surgery needed).
# check_no_internal_leakage.py's own top level is import-safe: every module-level
# statement there is a constant, a compiled regex, or a path computation, and its only
# side-effecting call (main()) sits behind `if __name__ == "__main__":` -- importing it
# runs no scan, no argparse, no sys.exit.
CORRECTIVE_RE = re.compile(
    r"\b("
    r"fix(?:e[sd])?"
    r"|clos(?:e[sd]?|ing)"
    r"|resolv(?:e[sd]?|ing)"
    r"|companion to"
    r"|no longer reproducible"
    r"|now (?:fixed|resolved|writes|derives|routes|blocks|refuses|rejects)"
    r"|reproduction and fix"
    r"|patched"
    r"|addressed"
    r"|no longer trust(?:s|ing)?"
    r"|\brestored\b"
    r"|load-bearing"
    r")\b",
    re.IGNORECASE,
)

FALSE_POSITIVE_CONTEXT = re.compile(
    r"\b(version|v\d|release|percent|%|line\s*#?\d|px|rgba?\(|color\s*:|"
    r"background\s*:|#[0-9a-fA-F]{6}\b)",
    re.IGNORECASE,
)

NUMBERED_REFERENCE_CONTEXT = re.compile(
    r"(prohibition|rule|item|step|clause|point|principle|guideline|"
    r"section|paragraph|requirement|footnote|figure|chapter|table)\s*#?\s*$",
    re.IGNORECASE,
)

STRING_FIXTURE_RE = re.compile(r"""=\s*["'][^"']*#\d""")

# The literal citation, same word-boundary rule as sweeper.py: '#' + 1-4 digits, not
# glued to another digit/word/#/slash on either side.
CITATION_RE = re.compile(r"(?<![\w#/.])#(\d{1,4})(?!\d)")

# GitHub's OWN closing-keyword vocabulary (documented behavior: these words, followed
# by "#N" or a full URL, in a PR body/description, auto-close issue N on merge). This
# gate enforces GitHub's convention, not an invented one.
CLOSING_KEYWORD_RE_TEMPLATE = (
    r"\b(close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+#{n}\b"
)

def looks_like_false_positive(line: str, match: "re.Match | None" = None) -> bool:
    if FALSE_POSITIVE_CONTEXT.search(line):
        return True
    if STRING_FIXTURE_RE.search(line):
        return True
    if match is not None:
        window = line[max(0, match.start() - 30): match.start()]
        if NUMBERED_REFERENCE_CONTEXT.search(window):
            return True
    return False


def run(cmd: list[str], cwd: str | None = None) -> tuple[int, str, str]:
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def find_diff_citations(file_diffs):
    """Returns a list of dicts: {number, path, lineno, line, matched_verb} for every
    ADDED line that survives the false-positive filter and carries a corrective-state
    phrase next to a real '#N'."""
    out = []
    for path, added_lines in file_diffs:
        for lineno, text in added_lines:
            for m in CITATION_RE.finditer(text):
                if looks_like_false_positive(text, m):
                    continue
                if not CORRECTIVE_RE.search(text):
                    continue
                out.append({
                    "number": int(m.group(1)),
                    "path": path,
                    "lineno": lineno,
                    "line": text.strip()[:220],
                })
    return out


def issue_is_open(repo: str, number: int, offline_open_issues: set[int] | None) -> tuple[bool | None, str]:
    """Returns (is_open, detail). is_open=None means the lookup itself failed --
    caller must treat this as CANNOT EVALUATE, never as 'must be closed, so skip it'."""
    if offline_open_issues is not None:
        return (number in offline_open_issues, "offline fixture list (--offline-open-issues)")
    rc, out, err = run([
        "gh", "issue", "view", str(number), "--repo", repo, "--json", "state", "-q", ".state",
    ])
    if rc != 0:
        return None, f"gh issue view failed: {err.strip()[:200]}"
    state = out.strip().upper()
    return state == "OPEN", f"gh issue view --json state -> {state}"


def pr_body_satisfies(pr_body: str, number: int) -> bool:
    pat = re.compile(CLOSING_KEYWORD_RE_TEMPLATE.format(n=number), re.IGNORECASE)
    return bool(pat.search(pr_body))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", help="base SHA/ref (CI mode)")
    ap.add_argument("--head", help="head SHA/ref (CI mode)")
    ap.add_argument("--mode", choices=["merge-base", "linear"], default="merge-base")
    ap.add_argument("--scan-file", help="manual/fixture mode: a literal unified diff, read as-is (no git)")
    ap.add_argument("--repo", required=True, help="owner/name -- used ONLY for the open/closed lookup")
    ap.add_argument("--pr-body-file", required=True, help="path to a text file holding the PR body")
    ap.add_argument("--offline-open-issues", default=None,
                     help="comma-separated issue numbers to treat as OPEN, skipping the live "
                          "gh api lookup -- fixture/demo use only. CI never passes this.")
    args = ap.parse_args()

    try:
        with open(args.pr_body_file, "r", encoding="utf-8") as fh:
            pr_body = fh.read()
    except OSError as e:
        print(f"CANNOT EVALUATE: could not read --pr-body-file {args.pr_body_file!r}: {e}", file=sys.stderr)
        return CANNOT_EVALUATE

    if args.scan_file:
        try:
            with open(args.scan_file, "r", encoding="utf-8") as fh:
                diff_text = fh.read()
        except OSError as e:
            print(f"CANNOT EVALUATE: could not read --scan-file {args.scan_file!r}: {e}", file=sys.stderr)
            return CANNOT_EVALUATE
    elif args.base and args.head:
        try:
            diff_text = run_git_diff(args.base, args.head, args.mode)
        except SystemExit as e:
            print(str(e), file=sys.stderr)
            return CANNOT_EVALUATE
    else:
        ap.error("either --scan-file, or both --base and --head, are required")
        return CANNOT_EVALUATE

    file_diffs = parse_unified_diff(diff_text)
    citations = find_diff_citations(file_diffs)

    if not citations:
        print("FIX-CITATION GATE: not triggered -- this diff cites no corrective fix "
              "for any issue number in its added lines. Ordinary PR, nothing required.")
        return NOT_TRIGGERED

    offline_open = None
    if args.offline_open_issues is not None:
        offline_open = {int(x) for x in args.offline_open_issues.split(",") if x.strip()}

    # De-dupe by issue number -- a PR may cite the same issue on several lines.
    by_number: dict[int, list[dict]] = {}
    for c in citations:
        by_number.setdefault(c["number"], []).append(c)

    unresolved = []
    lookup_failures = []
    for number, hits in sorted(by_number.items()):
        is_open, detail = issue_is_open(args.repo, number, offline_open)
        if is_open is None:
            lookup_failures.append((number, detail))
            continue
        if not is_open:
            continue  # cites a closed/nonexistent issue -- not this gate's concern
        if not pr_body_satisfies(pr_body, number):
            unresolved.append((number, hits, detail))

    if lookup_failures:
        print("FIX-CITATION GATE: CANNOT EVALUATE -- the diff cited an issue number, but "
              "this run could not determine whether it is currently open:", file=sys.stderr)
        for number, detail in lookup_failures:
            print(f"  #{number}: {detail}", file=sys.stderr)
        return CANNOT_EVALUATE

    if not unresolved:
        print("FIX-CITATION GATE: triggered and satisfied -- every open issue this diff "
              "cites a fix for is already named with a closing keyword in the PR body.")
        return NOT_TRIGGERED

    print("FIX-CITATION GATE: FLAGGED\n")
    print(
        "This PR's own diff already describes a fix for a currently-OPEN issue, in a "
        "code comment / docstring / commit -- but the PR body does not carry the one "
        "string GitHub itself acts on to close it. This is exactly how this repo's "
        "tracker has drifted from the code before: a real fix ships, the issue stays "
        "open forever, and the next person re-files or re-investigates something "
        "already done.\n"
    )
    for number, hits, detail in unresolved:
        print(f"  Issue #{number} is OPEN ({detail}). Add to the PR body, exactly:")
        print(f"      Fixes #{number}")
        print(f"  (or Closes #{number} / Resolves #{number} -- any GitHub closing keyword)")
        print(f"  Triggered by:")
        for h in hits[:3]:
            print(f"      {h['path']}:{h['lineno']}: {h['line']}")
        if len(hits) > 3:
            print(f"      ... and {len(hits) - 3} more line(s) in this diff")
        print()
    print(
        "⛔ This gate never edits the PR body itself and never touches the issue tracker "
        "-- add the line above and re-run. If this PR only ADDRESSES PART of issue "
        "#N (see K.E1 sweeper's PARTIAL-EVIDENCE tier), do not cite a closing keyword at "
        "all -- reference the issue without 'Fixes'/'Closes'/'Resolves' so it stays open "
        "for the remainder."
    )
    return FLAGGED


if __name__ == "__main__":
    sys.exit(main())

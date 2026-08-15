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
  3. OPERATOR IDENTITY -- a line a change ADDS contains one of the operator-identifying
     strings that claudeops-config's own shipping lane already refuses on. These patterns
     are copied VERBATIM from claudeops-config/system/shipping-lane/refuse-rules.json (see
     CONTENT_PATTERNS below for the source id of each) -- one rule set, not two that drift
     apart. Only the IDENTITY-tier patterns (email / name / GitHub handle / Drive-account
     path) are reused here, not that file's "2-private" desk-persona rules (cal / marc /
     emily / clair / deryl / dobby): those name ClaudeOps-internal personas, not the
     operator, and this product ships its OWN generically-named skills with the same
     one-word slugs (.claude/skills/cal-daily/ is real, shipped, unrelated product content)
     -- reusing those rules here would cry wolf on this repo's own normal traffic. Secrets
     (refuse-rules.json's "1-secret" tier) are a related but separate concern and are out
     of scope for this check -- see "WHAT THIS DOES NOT CATCH" in the workflow's own
     comments / the task report.

WHY "ADDED LINES", NOT WHOLE-FILE CONTENT: this repo already carries a few lines that
would trip these patterns if the WHOLE file were rescanned on every touch -- e.g.
system/shipping-lane/scrub.py's own selftest fixtures literally contain the string
"/Users/wren/Desktop", and a few system/hooks/*.sh files carry "Enver" in attribution
comments. Scanning the whole file on any unrelated edit would false-positive on lines
nobody touched. Scanning only the lines a diff ADDS matches the task's own framing --
"fail the check when a change INTRODUCES" -- and survives contact with this repo's real
history. See parse_unified_diff() below.

USAGE
  CI (production path): parses `git diff` between two refs/SHAs in the current repo.
      check_no_internal_leakage.py --base <sha_or_ref> --head <sha_or_ref> [--mode merge-base|linear]
      --mode merge-base -> `git diff --unified=0 --no-color --no-renames BASE...HEAD` (pull_request)
      --mode linear      -> `git diff --unified=0 --no-color --no-renames BASE HEAD`   (push)

  Manual / fixture testing (no git needed -- treats the whole file as "added", which is
  the exact real-world shape of a wholly NEW file, e.g. the incident file itself):
      check_no_internal_leakage.py --scan-file /tmp/fixture.md --as-path migration-audit/x.md

EXIT CODES
  0  CLEAN    -- nothing flagged
  1  FLAGGED  -- at least one violation (path or content)
  2  CANNOT EVALUATE -- git diff itself failed, or bad arguments
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys

CLEAN, FLAGGED, CANNOT_EVALUATE = 0, 1, 2

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

# ------------------------------------------------------------------- rule 2 + 3: CONTENT
# Checked against every line a diff ADDS (never unchanged context, never a whole-file
# rescan -- see module docstring for why). Rule 2 (home path) is hand-written here,
# deliberately generic across usernames per the task. Rule 3 entries are copied VERBATIM
# from claudeops-config/system/shipping-lane/refuse-rules.json -- "source" names the
# exact rule id there, so a drift check just diffs the two pattern strings.
CONTENT_PATTERNS = [
    {
        "id": "home-path-generic",
        "source": None,
        "pattern": r"(?:/Users/|/home/)[A-Za-z0-9._-]+",
        "remedy": (
            "an absolute home-folder path -- the segment right after /Users/ or /home/ "
            "IS someone's account name, and the path does not exist on any other "
            "machine. Replace it with ~/... or $HOME/... (this repo's own "
            "docs/REPORT-A-BUG.md gives the identical instruction: 'Replace "
            "`/Users/theirname/...` with `~/...`')."
        ),
    },
    {
        "id": "operator-email-primary",
        "source": "email-primary",
        "pattern": r"(?i)enver\.gjokaj@gmail\.com",
        "remedy": "the operator's primary email address. Remove it or genericize it.",
    },
    {
        "id": "operator-email-any",
        "source": "email-any-personal",
        "pattern": r"(?i)\b[A-Za-z0-9._%+-]*gjokaj[A-Za-z0-9._%+-]*@[A-Za-z0-9.-]+",
        "remedy": "an email address built on the operator's family name. Remove it or genericize it.",
    },
    {
        "id": "operator-name-enver",
        "source": "name-enver",
        "pattern": r"(?i)(?<![A-Za-z0-9])enver(?![A-Za-z0-9])",
        "remedy": "the operator's first name. Remove it, or use a generic placeholder ('the operator', 'you').",
    },
    {
        "id": "operator-name-gjokaj",
        "source": "name-gjokaj",
        "pattern": r"(?i)(?<![A-Za-z0-9])gjokaj(?![A-Za-z0-9])",
        "remedy": "the operator's family name. Remove it, or use a generic placeholder.",
    },
    {
        "id": "operator-github-handle",
        "source": "handle-github",
        "pattern": r"(?i)(?<![A-Za-z0-9])egjokaj(?![A-Za-z0-9])",
        "remedy": "the operator's personal GitHub handle -- links this repo to a specific person. Remove it.",
    },
    {
        "id": "operator-drive-cloudstorage",
        "source": "path-drive-cloudstorage",
        "pattern": r"CloudStorage/GoogleDrive-",
        "remedy": "a macOS Google Drive mount path -- the segment that follows is a personal account address. Remove it.",
    },
    {
        "id": "operator-drive-account",
        "source": "path-drive-account",
        "pattern": r"GoogleDrive-[A-Za-z0-9._%+-]+@",
        "remedy": "a Google Drive mount path with a full email address embedded in it. Remove it.",
    },
]

# Files under .github/ are never content-scanned. Two reasons, both load-bearing:
#  (a) the task requires it explicitly, so the workflow's own pattern strings in this very
#      file don't trip the check on the PR that adds them;
#  (b) it is not cosmetic -- CONTENT_PATTERNS' own source lines literally contain bounded
#      occurrences of "enver", "gjokaj" etc. as regex text (e.g. this file's
#      operator-name-enver pattern string), so a self-scan would self-flag on introduction.
CONTENT_SCAN_EXCLUDE_PREFIX = ".github/"


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
    for raw_line in diff_text.splitlines():
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
        for rule in CONTENT_PATTERNS:
            if re.search(rule["pattern"], text):
                hits.append((lineno, text, rule))
    return hits


def format_violation(path, rule, lineno=None, evidence=None):
    where = "file={}".format(path)
    if lineno is not None:
        where += ",line={}".format(lineno)
    source_note = ""
    if rule.get("source"):
        source_note = " [reused from claudeops-config/system/shipping-lane/refuse-rules.json id={}]".format(
            rule["source"])
    header = "::error {}::[{}] {}{}".format(where, rule["id"], rule["remedy"], source_note)
    lines = [header]
    if evidence is not None:
        lines.append("    {}:{}: {}".format(path, lineno, evidence.strip()[:200]))
    return "\n".join(lines)


def scan_files(file_diffs):
    """file_diffs: list of (path, added_lines). Returns list of violation strings."""
    violations = []
    for path, added_lines in file_diffs:
        path_rule = check_path(path)
        if path_rule:
            violations.append(format_violation(path, path_rule))
            # a denylisted path still gets its content checked below too -- multiple
            # independent findings on one file are all worth surfacing at once.
        if path.startswith(CONTENT_SCAN_EXCLUDE_PREFIX):
            continue
        for lineno, text, rule in check_added_lines(added_lines):
            violations.append(format_violation(path, rule, lineno, text))
    return violations


# --------------------------------------------------------------------------------- CLI

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
    args = ap.parse_args()

    if args.scan_file:
        with open(args.scan_file, "r", encoding="utf-8") as fh:
            text = fh.read()
        added_lines = list(enumerate(text.splitlines(), start=1))
        path = args.as_path or args.scan_file
        file_diffs = [(path, added_lines)]
    elif args.base and args.head:
        diff_text = run_git_diff(args.base, args.head, args.mode)
        file_diffs = parse_unified_diff(diff_text)
    else:
        ap.error("either --scan-file, or both --base and --head, are required")
        return CANNOT_EVALUATE

    violations = scan_files(file_diffs)

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

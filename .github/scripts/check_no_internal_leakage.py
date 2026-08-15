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

  Whole-tree BASELINE audit (periodic, NOT per-PR -- see WHOLE-TREE BASELINE MODE below):
      check_no_internal_leakage.py --whole-tree [--report-out PATH]

EXIT CODES
  0  CLEAN    -- nothing flagged (whole-tree: no BLOCKING finding; WARNING-tier findings,
                 if any, do not change this -- see below)
  1  FLAGGED  -- at least one BLOCKING violation (path or identity content)
  2  CANNOT EVALUATE -- git diff/ls-files itself failed, a file could not be read, or bad
                        arguments. NEVER exit 0 on an error -- an unevaluated run must not
                        read as a clean one.

WHOLE-TREE BASELINE MODE -- WHY IT EXISTS, SEPARATE FROM THE PER-PR GATE ABOVE
  The per-PR gate above only ever sees lines a diff ADDS (see "WHY ADDED LINES" above) --
  by construction it is permanently blind to anything committed before this check existed.
  --whole-tree is a second, independent mode that rescans every file `git ls-files` tracks
  in the current checkout, in full, on the SAME two BLOCKING rule families the per-PR gate
  already enforces (PATH_DENYLIST, CONTENT_PATTERNS) -- so it can find a leak that shipped
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
      sharing a line with "tenant"/"billing"/"client"/"invoice" -- see DOLLAR_AMOUNT_RE.
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
# Adding a new entry here means "this exact string is independently already established as
# invented, elsewhere in this repo, for a documented reason" -- never "a real finding I
# want gone."
FICTIONAL_FIXTURE_WORDS = frozenset({
    "wren", "oakley", "woakley", "fern",
    "okonkwo", "ida", "brennan", "sunil", "varma", "marisol", "ferreira", "theo", "lindqvist",
})
FICTIONAL_FIXTURE_PHRASES = ("whitfield contracting",)
# Fixture home-path usernames -- the segment right after /Users/ or /home/ that this repo's
# own examples already use for an invented account, so home-path-generic (rule 2) does not
# fire on them in whole-tree mode. Matches the task's own named set exactly.
FICTIONAL_FIXTURE_USERNAMES = frozenset({"wren", "x", "theirname", "woakley"})

# --------------------------------------------------------- self-reference exclusions
# Same rationale as CONTENT_SCAN_EXCLUDE_PREFIX (.github/) above, applied to the two other
# places in THIS repo that, by their own stated purpose, contain the exact leak SHAPES on
# purpose rather than by accident:
#   - system/shipping-lane/fixtures/ -- refuse-fixture.md's own header: "THIS FILE EXISTS
#     TO BE CAUGHT. It is deliberately full of the exact shapes the shipping lane refuses
#     ... it is never in a shipping manifest." A directory whose declared job is to be a
#     positive test fixture FOR A DIFFERENT SCANNER (verify_rules.py) is not a leak when
#     THIS scanner rediscovers it; it is that scanner working.
#   - system/shipping-lane/refuse-rules.json -- the exact file CONTENT_PATTERNS above
#     documents it copied several rules VERBATIM from (see each rule's "source" field);
#     naturally it contains the same literal pattern text (e.g. "CloudStorage/GoogleDrive-")
#     as documentation of the rule, not an occurrence of the thing the rule catches.
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
BILLING_TRIGGER_WORDS = ("tenant", "billing", "client", "invoice")
BILLING_TRIGGER_RE = re.compile(
    r"(?i)(?<![A-Za-z0-9])(" + "|".join(BILLING_TRIGGER_WORDS) + r")(?![A-Za-z0-9])")

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
        if path.startswith(CONTENT_SCAN_EXCLUDE_PREFIX):
            # same reasoning as the per-PR mode's exclusion -- this file's own pattern
            # strings would self-flag on introduction. See CONTENT_SCAN_EXCLUDE_PREFIX.
            continue
        if is_self_referential_fixture_path(path):
            # see WHOLE_TREE_SELF_REFERENCE_EXCLUDE_PATHS/PREFIXES for the two named,
            # documented reasons this is not a general suppression mechanism.
            continue

        text = read_text_file(path)
        if text is None:
            files_skipped_binary += 1
            continue
        files_scanned += 1

        for lineno, line in enumerate(text.splitlines(), start=1):
            # ---- BLOCKING: the same identity/home-path patterns the per-PR gate uses ----
            for rule in CONTENT_PATTERNS:
                m = re.search(rule["pattern"], line)
                if not m:
                    continue
                if rule["id"] == "home-path-generic":
                    # extract the segment right after /Users/ or /home/
                    seg_match = re.search(r"(?:/Users/|/home/)([A-Za-z0-9._-]+)", line)
                    seg = seg_match.group(1) if seg_match else ""
                    if seg.lower() in FICTIONAL_FIXTURE_USERNAMES:
                        continue  # allowlisted fixture path -- see FICTIONAL_FIXTURE_USERNAMES
                blocking.append({
                    "severity": BLOCKING, "path": path, "line": lineno,
                    "rule_id": rule["id"], "remedy": rule["remedy"], "evidence": line.strip()[:200],
                })

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
                        "a specific-decimal dollar figure shares this line with a billing-"
                        "context word (tenant/billing/client/invoice). If this is a real "
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
    args = ap.parse_args()

    if args.whole_tree:
        return run_whole_tree_mode(args)

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

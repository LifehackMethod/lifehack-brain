#!/usr/bin/env python3
"""skill_command_check.py — every skill's instructed commands vs. the tools they name.

WHAT: walks every `skills/*/SKILL.md`, extracts each fenced command block's fenced code
      (reusing skill_promise_check.py's extract_code_blocks() — see the import below;
      this file does NOT contain a second extractor), and finds every
      `(tool_path, subcommand)` pair a skill instructs a session to run — commands shaped
      like `python3 ~/.claude/skills/ClaudeOps/system/tools/foo.py check "<arg>"` or
      `bash "$HOME/.claude/skills/ClaudeOps/system/hooks/bar.sh" status` (the home-relative prefix is
      derived from whatever this checkout is actually named — see _live_prefixes below —
      so this also works for a fork checked out under a different directory name).

      For each pair found, this tool reports a problem when EITHER (a) the tool path does
      not exist on disk, or (b) the tool exists but its own source never DECLARES that
      subcommand. A skill that instructs a command its own target tool doesn't recognize
      is a silent trap — the session follows the doc, the tool exits nonzero or prints
      "unrecognized command", and nothing upstream caught it before a human hit it live.

DECLARES — must handle BOTH styles found in this repo, checked as a UNION (either one is
      enough), regardless of the tool's file extension:
        - PYTHON: the subcommand appears anywhere in the tool's source as a quoted string
          literal — "check" / 'check' (e.g. `sub.add_parser("check")`, or a plain
          `sys.argv[1] != "archive"` comparison — pad_archive.py uses the latter, no
          argparse at all).
        - SHELL: the subcommand is a `case` branch — `status)` / `"status")` /
          `arm|rearm)`. A few real .sh tools in this repo (over_my_shoulder.sh) declare a
          verb via a plain `[ "$ARG" = "tabs" ]` string comparison instead of a `case` —
          the quoted-literal check (the "python style" rule above, applied without regard
          to extension) catches those too, which is why both checks run as a union on
          every file rather than being extension-gated.
      A quoted-literal check ALONE reports every shell script as broken (a `case` branch's
      bare-word form, `status)`, carries no quotes at all) — that was the first probe's
      false-failure mode on 2026-08-07, and is the reason this tool exists.

SCOPE — only `(tool_path, subcommand)` pairs where the normalized tool_path resolves
      under `system/tools/` or `system/hooks/` of the same repo are checked at all. An
      invocation of something else (a $-var path this tool can't resolve, an external
      command) is not a candidate this tool has any business grading, and is silently
      skipped rather than misreported as missing-path.

      A token immediately following the tool path is read as the subcommand only if it is
      itself subcommand-shaped: starts with a letter, then letters/digits/`_`/`-` only.
      This is the one skip rule the spec asks for ("a token starting with `-`, and a
      path-looking token") generalized as a single whitelist test — a flag (`-x`), a path
      (contains `/`), a JSON blob (`{...}`), and a placeholder (`<...>`) all fail it the
      same way a bracketed usage-pattern token does (see KNOWN FINDING below).

STALE DONOR PATH — this repo was renamed from a prior clone directory (historically
      `claudeops-config`, retired) to its current checkout name. A skill instructing a
      command via that OLD name (`~/claudeops-config/system/tools/foo.py ...`) is exactly
      the class of dead reference this tool exists to catch, so it is deliberately
      recognized (never silently SCOPE-skipped) and always reported failing with reason
      `stale-donor-path` — regardless of whether a same-relative-path file happens to
      exist under the live repo, because the literal command as written will not run on a
      machine that only has the live checkout. The donor prefix is NEVER used to resolve
      this tool's own repo root (that is always the live checkout `DEFAULT_REPO_ROOT` is
      computed from) — see `_STALE_DONOR_PREFIXES` / `_live_prefixes()` below.

KNOWN FINDING, not fixed here (told not to fix/loosen — see module CLI docstring at the
      bottom / the tool's own return report): `marc-checkin/SKILL.md` documents
      `marc-ticker.py`'s usage as `marc-ticker.py TICKER [TICKER ...] [--news]` inside a
      fenced block. `TICKER` is a bare identifier-shaped token, so this tool reads it as
      an asserted subcommand — but marc-ticker.py takes ticker symbols as plain positional
      args and declares no subcommand at all, so it comes back undeclared-subcommand. This
      is a genuine artifact of a usage-pattern doc line living inside a fenced block, not a
      matcher bug; it is reported, not special-cased away.

THE POSITIVE CONTROL — part of the tool, not the test suite. On every run, before
      reporting anything, this tool asserts two known-good pairs resolve as DECLARED:
      `system/hooks/pm_flag.sh status` and `system/tools/gauge_check.py check`. If either
      fails (file missing, or its own matcher fails to find the declaration), that proves
      the matcher itself is broken, and NO sweep verdict is printed at all — a broken
      matcher must never look like a clean tree.

CLOSED VERDICT SET (first line of stdout, from the exit code):
  ALL-DECLARED <npairs>    exit 0  — every checked pair resolves. <npairs> is the count of
                                     qualifying (skill, tool, subcommand) invocation
                                     instances checked (not deduplicated — two skills
                                     instructing the same pair count twice, matching "every
                                     invocation this tool found and graded").
  UNDECLARED <n>           exit 2  — n instances do not resolve; each printed as
                                     `<skill> -> <tool> <subcommand>  (reason)`, reason one
                                     of missing-path / undeclared-subcommand /
                                     stale-donor-path (see STALE DONOR PATH below).
  CANNOT-READ <why>        exit 4  — the skills dir or a SKILL.md is unreadable. STDERR.
                                     THE NO-OUTCOME MEMBER — never exit 0.
  CONTROL-FAILED <which>   exit 5  — the matcher itself is broken (see above). STDERR.

USAGE
    skill_command_check.py [--repo-root PATH]

    --repo-root overrides the repo root this tool sweeps and resolves paths against
    (default: this file's own repo). It exists so the test suite can point the whole
    tool — control check included — at a synthetic temp tree instead of the live repo,
    per the "do NOT depend on the live tree for the failure cases" requirement; it is not
    needed for normal use.
"""

import argparse
import glob
import os
import re
import shlex
import sys

# ── reuse skill_promise_check's extractor — do NOT write a second one ──────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from skill_promise_check import extract_code_blocks  # noqa: E402

DEFAULT_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# The two known-good pairs the positive control asserts on every run (see module
# docstring "THE POSITIVE CONTROL").
CONTROL_PAIRS = [
    ("system/hooks/pm_flag.sh", "status"),
    ("system/tools/gauge_check.py", "check"),
]

INTERPRETERS = {"python3", "python", "bash", "sh"}

# A subcommand-shaped token: a bare word starting with a letter. Anything else (a `-flag`,
# a `/path`, a `{json}`, a `<placeholder>`, a bracketed usage token like `[TICKER`) fails
# this and is treated as "not a subcommand" — see module docstring SCOPE.
IDENT_RE = re.compile(r'^[A-Za-z][A-Za-z0-9_-]*$')

# A normalized, repo-relative tool path this tool has any business grading.
TOOL_DOMAIN_RE = re.compile(r'^system/(tools|hooks)/.+\.(py|sh)$')

# PYTHON style: the subcommand as a quoted string literal anywhere in the tool's source.
def _python_literal_re(subcommand):
    return re.compile(r'["\']' + re.escape(subcommand) + r'["\']')

# SHELL style: a `case` branch — `status)`, `"status")`, or `arm|rearm)`. Matched per-line
# so a bare-word branch (no quotes at all) is still found — the exact shape a
# quoted-literal-only check misses (the first probe's false-failure mode).
CASE_BRANCH_RE = re.compile(
    r'^\s*"?([A-Za-z_][A-Za-z0-9_-]*(?:\s*\|\s*[A-Za-z_][A-Za-z0-9_-]*)*)"?\)',
    re.MULTILINE,
)


def python_declares(source, subcommand):
    """PYTHON style: subcommand present anywhere as a quoted string literal."""
    return bool(_python_literal_re(subcommand).search(source))


def shell_declares(source, subcommand):
    """SHELL style: subcommand is one of the names in some `case` branch (bare or
    quoted, possibly `|`-joined with sibling branches)."""
    for m in CASE_BRANCH_RE.finditer(source):
        alts = [a.strip() for a in m.group(1).split('|')]
        if subcommand in alts:
            return True
    return False


def declares(tool_abs_path, subcommand):
    """DECLARED = python_declares OR shell_declares, checked as a union on the tool's own
    source regardless of its extension (see module docstring DECLARES). Returns False,
    never raises, if the file can't be read — fail-closed."""
    try:
        with open(tool_abs_path, encoding="utf-8") as f:
            source = f.read()
    except OSError:
        return False
    return python_declares(source, subcommand) or shell_declares(source, subcommand)


# The OLD donor clone's home-relative prefixes — retired, must never be treated as
# equivalent to the live repo (see module docstring STALE DONOR PATH). Kept as a fixed,
# literal list (not derived from anything) because it names a SPECIFIC dead repo, not
# "whatever this checkout is called" — that is the opposite of _live_prefixes() below.
_STALE_DONOR_PREFIXES = ("~/claudeops-config/", "$HOME/claudeops-config/")


def _live_prefixes(repo_root):
    """The home-relative prefixes a skill could legitimately use to reference a tool
    inside THIS (the live) repo — derived from repo_root's own basename rather than any
    hardcoded name, so this tracks whatever the checkout is actually named (the real repo
    today, or a synthetic --repo-root in tests) without baking in a personal absolute
    path. Stripped as TEXT, not OS-expanded (no os.path.expanduser / real $HOME
    substitution) — the remainder is resolved against whatever repo_root was PASSED IN,
    so this works identically against the live repo and a synthetic --repo-root in tests."""
    name = os.path.basename(os.path.normpath(repo_root))
    return (f"~/{name}/", f"$HOME/{name}/")


def normalize_tool_path(token, repo_root):
    """Resolve a raw path token from a fenced command into (rel_path, is_stale_donor).

    rel_path is a canonical repo-relative path ('system/tools/foo.py') or None if the
    token isn't a path inside repo_root at all (e.g. a $VAR this tool can't resolve, or
    something outside the repo) — such a token is not a candidate this tool has any
    business grading (see SCOPE).

    is_stale_donor is True only when the token used the OLD donor clone's home-relative
    prefix (`~/claudeops-config/...` / `$HOME/claudeops-config/...`) — in that case
    rel_path is still computed (for display) but the caller must treat the pair as
    failing unconditionally (see module docstring STALE DONOR PATH); it must NEVER be
    graded as if it were a normal live-repo reference just because the same relative path
    happens to also exist in the live repo.

    Shapes handled: the live repo's home-relative prefix (see _live_prefixes), the OLD
    donor's home-relative prefix, a bare repo-relative path ('system/tools/foo.py'), and
    a literal absolute path already pointing inside repo_root."""
    tok = token.strip()
    if len(tok) >= 2 and tok[0] == tok[-1] and tok[0] in ('"', "'"):
        tok = tok[1:-1]

    repo_root_norm = os.path.normpath(repo_root)

    for prefix in _STALE_DONOR_PREFIXES:
        if tok.startswith(prefix):
            rel = os.path.normpath(tok[len(prefix):])
            if os.path.isabs(rel) or rel.startswith(".."):
                return None, False
            return rel, True

    for prefix in _live_prefixes(repo_root):
        if tok.startswith(prefix):
            rel = os.path.normpath(tok[len(prefix):])
            if os.path.isabs(rel) or rel.startswith(".."):
                return None, False
            return rel, False

    if tok.startswith("/"):
        abs_tok = os.path.normpath(tok)
        if abs_tok == repo_root_norm or abs_tok.startswith(repo_root_norm + os.sep):
            return os.path.relpath(abs_tok, repo_root_norm), False
        return None, False

    # bare relative — already repo-relative (e.g. 'system/tools/foo.py')
    rel = os.path.normpath(tok)
    if os.path.isabs(rel) or rel.startswith(".."):
        return None, False
    return rel, False


def find_invocations(block_text, repo_root):
    """Yield (tool_rel_path, subcommand, is_stale_donor) for every recognized
    `<interpreter> <tool-under-system/tools-or-hooks> <subcommand>` invocation in one
    fenced code block. Line continuations (a trailing `\\` at end of line) are joined
    first, so a command wrapped across lines is still found."""
    joined = re.sub(r'\\\r?\n[ \t]*', ' ', block_text)
    found = []
    for raw_line in joined.splitlines():
        try:
            tokens = shlex.split(raw_line, comments=True)
        except ValueError:
            continue  # unparseable line (e.g. stray quote in prose) — skip, don't crash
        for i, tok in enumerate(tokens):
            if tok not in INTERPRETERS:
                continue
            if i + 1 >= len(tokens):
                continue
            rel, is_stale = normalize_tool_path(tokens[i + 1], repo_root)
            if not rel or not TOOL_DOMAIN_RE.match(rel):
                continue
            if i + 2 >= len(tokens):
                continue
            sub = tokens[i + 2]
            if not IDENT_RE.match(sub):
                continue
            found.append((rel, sub, is_stale))
    return found


def collect_instances(repo_root):
    """Walk every skills/*/SKILL.md under repo_root and return the list of
    (skill_name, tool_rel_path, subcommand, is_stale_donor) instances found, or raise
    OSError if the skills dir or a SKILL.md can't be read."""
    skills_dir = os.path.join(repo_root, "skills")
    if not os.path.isdir(skills_dir):
        raise OSError(f"skills dir not found: {skills_dir}")
    os.listdir(skills_dir)  # forces a PermissionError here if the dir is unreadable

    instances = []
    for path in sorted(glob.glob(os.path.join(skills_dir, "*", "SKILL.md"))):
        skill_name = os.path.basename(os.path.dirname(path))
        with open(path, encoding="utf-8") as f:
            text = f.read()
        for block_text, _start_line in extract_code_blocks(text):
            for tool_rel, sub, is_stale in find_invocations(block_text, repo_root):
                instances.append((skill_name, tool_rel, sub, is_stale))
    return instances


def run_control(repo_root):
    """The positive control (see module docstring). Returns (True, "") on success, or
    (False, "<which pair/file, and why>") on failure."""
    for tool_rel, sub in CONTROL_PAIRS:
        abs_path = os.path.join(repo_root, tool_rel)
        if not os.path.isfile(abs_path):
            return False, f"{tool_rel} {sub} — file missing at {abs_path}"
        if not declares(abs_path, sub):
            return False, f"{tool_rel} {sub} — matcher did not find it declared"
    return True, ""


def evaluate(instances, repo_root):
    """Grade every collected instance. Returns (failing, ) where failing is a list of
    (skill_name, tool_rel, subcommand, reason) tuples, reason one of missing-path /
    undeclared-subcommand / stale-donor-path.

    A stale-donor instance (is_stale True) always fails with reason stale-donor-path —
    unconditionally, without even checking whether tool_rel happens to exist under
    repo_root — because the literal command as instructed used the OLD donor clone's
    prefix and will not run against the live repo regardless of what lives at the
    same-relative-path in it (see module docstring STALE DONOR PATH)."""
    failing = []
    for skill_name, tool_rel, sub, is_stale in instances:
        if is_stale:
            failing.append((skill_name, tool_rel, sub, "stale-donor-path"))
            continue
        abs_path = os.path.join(repo_root, tool_rel)
        if not os.path.isfile(abs_path):
            failing.append((skill_name, tool_rel, sub, "missing-path"))
            continue
        if not declares(abs_path, sub):
            failing.append((skill_name, tool_rel, sub, "undeclared-subcommand"))
    return failing


def build_parser():
    parser = argparse.ArgumentParser(prog="skill_command_check.py")
    parser.add_argument(
        "--repo-root", default=None,
        help="override the repo root swept + resolved against (mainly for tests)",
    )
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    repo_root = os.path.abspath(args.repo_root) if args.repo_root else DEFAULT_REPO_ROOT

    ok, control_msg = run_control(repo_root)
    if not ok:
        print(f"CONTROL-FAILED {control_msg}", file=sys.stderr)
        return 5

    try:
        instances = collect_instances(repo_root)
    except OSError as e:
        print(f"CANNOT-READ {e}", file=sys.stderr)
        return 4
    except UnicodeDecodeError as e:
        print(f"CANNOT-READ unparseable (encoding): {e}", file=sys.stderr)
        return 4

    failing = evaluate(instances, repo_root)

    if failing:
        print(f"UNDECLARED {len(failing)}")
        for skill_name, tool_rel, sub, reason in sorted(failing):
            print(f"  {skill_name} -> {tool_rel} {sub}  ({reason})")
        return 2

    npairs = len(instances)
    distinct_tools = len({t for _, t, _, _ in instances})
    distinct_pairs = len({(t, s) for _, t, s, _ in instances})
    print(f"ALL-DECLARED {npairs}")
    print(
        f"census: {distinct_tools} distinct tool paths · {npairs} total invocations · "
        f"{distinct_pairs} distinct (tool, subcommand) pairs"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

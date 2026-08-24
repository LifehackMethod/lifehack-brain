#!/usr/bin/env python3
"""check_plugin_version_bumped.py -- server-side gate: a PR that ships plugin content
bumps .claude-plugin/plugin.json's version, or it does not merge.

WHY THIS EXISTS: this repo is distributed to students as a Claude Code marketplace
plugin (.claude-plugin/marketplace.json -> plugin.json). Claude Code resolves whether an
update exists from plugin.json's "version" field FIRST, before any git-SHA fallback --
measured 2026-08-24, on every ref that then existed (origin/main and three open build
branches), plugin.json carried "0.1.0" and not one of them bumped it. An unbumped
explicit version makes every update path -- background auto-update AND a manual update
command -- report "already at the latest version" and install nothing, no matter how much
real hardening has merged. Six PRs of security work landing on top of an inert version
string would still never reach a student who already installed. That is the failure this
gate exists to end, structurally, on every PR, with nothing for a maintainer to remember.

WHY A PER-PR GATE, NOT AN AUTO-BUMP-ON-MERGE: an auto-bump workflow would need write
access to push a commit onto a (presumably branch-protected) main, would have to guess
patch/minor/major on the maintainer's behalf, and risks re-triggering itself on its own
commit. This repo's existing CI style (no-internal-leakage.yml) is already "block until a
human fixes it, never silently act for them" -- this gate matches that convention instead
of introducing a second one. The human still decides the number; the gate only makes it
impossible to forget, by failing the PR check red until it happens.

WHAT COUNTS AS "SHIPS PLUGIN CONTENT": the marketplace listing's plugin source is "./" --
the whole repository is the plugin, except the administrative/doc files below that a
student's installed copy behaves identically without. SHIPPED_PATH is therefore a
DENYLIST of what does NOT count (.github/, docs/, root-level *.md, dotfiles, and
.claude-plugin/ itself, since that directory only ever describes the version, it is not
content the version describes) -- everything else changed in a PR counts as shipped. A
denylist is the fail-closed choice here: a newly-added top-level directory nobody thought
to exempt still counts as shipped and still requires a bump, rather than silently passing
because an allowlist never learned about it.

EXIT CODES (matching this repo's other CI gate, check_no_internal_leakage.py):
  0  PASS            -- no shipped path changed, or one did and the version increased
  1  FLAGGED         -- a shipped path changed and the version did not increase
  2  CANNOT EVALUATE -- git itself failed, or plugin.json could not be read/parsed as
                         {"version": "X.Y.Z"} at base and/or head. NEVER exit 0 on an
                         error -- an unevaluated run must not read as a passing one.

USAGE
  check_plugin_version_bumped.py --base <sha_or_ref> --head <sha_or_ref> [--mode merge-base|linear]
      --mode merge-base -> git diff --name-only BASE...HEAD  (pull_request; three-dot)
      --mode linear      -> git diff --name-only BASE HEAD    (push; two-dot)

  Manual / fixture testing (no git needed -- pass file lists and JSON text directly):
      check_plugin_version_bumped.py --changed-files-in PATH --base-json PATH --head-json PATH
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys

PASS, FLAGGED, CANNOT_EVALUATE = 0, 1, 2

# ---------------------------------------------------------------------- non-shipped paths
# Anything matching one of these does NOT, by itself, require a version bump. Everything
# else changed in the diff DOES. See module docstring for why this is a denylist and not
# an allowlist.
NON_SHIPPED_PATTERNS = [
    r"^\.github/",                 # CI workflows and their scripts -- not installed content
    r"^docs/",                     # project documentation, not shipped skill/tool behavior
    r"^\.claude-plugin/",          # the version file itself and the marketplace listing
    r"^README\.md$",
    r"^INSTALL\.md$",
    r"^UPDATE\.md$",
    r"^PUSH-FORWARD\.md$",
    r"^REPAIR\.md$",
    r"^TARGET-STATE\.md$",
    r"^CLAUDE\.md$",
    r"^\.gitignore$",
    r"^\.gitattributes$",
]

VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def is_shipped(path: str) -> bool:
    return not any(re.match(p, path) for p in NON_SHIPPED_PATTERNS)


def run_git(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed (exit {result.returncode}): {result.stderr.strip()}"
        )
    return result.stdout


def changed_files(base: str, head: str, mode: str) -> list[str]:
    op = "..." if mode == "merge-base" else " "
    range_arg = f"{base}...{head}" if mode == "merge-base" else f"{base} {head}"
    out = run_git(["diff", "--name-only", "--no-renames", *range_arg.split()])
    return [line.strip() for line in out.splitlines() if line.strip()]


def read_version_at(ref: str, path: str) -> tuple[str | None, str | None]:
    """Returns (version_string, error_message). Exactly one is non-None."""
    result = subprocess.run(
        ["git", "show", f"{ref}:{path}"], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        return None, f"could not read {path} at {ref}: {result.stderr.strip()}"
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return None, f"{path} at {ref} is not valid JSON: {exc}"
    version = data.get("version")
    if not isinstance(version, str):
        return None, f"{path} at {ref} has no string 'version' field"
    return version, None


def parse_semver(version: str) -> tuple[int, int, int] | None:
    m = VERSION_RE.match(version.strip())
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def evaluate(
    files: list[str],
    base_version_raw: str | None,
    base_err: str | None,
    head_version_raw: str | None,
    head_err: str | None,
    plugin_json_path: str,
) -> tuple[int, str]:
    shipped = sorted(f for f in files if is_shipped(f))

    if not shipped:
        return PASS, "PASS -- no shipped path changed in this diff; no version bump required."

    header = (
        f"{len(shipped)} shipped file(s) changed:\n"
        + "\n".join(f"  - {f}" for f in shipped[:25])
        + ("\n  ... (truncated)" if len(shipped) > 25 else "")
    )

    if base_err or head_err:
        return (
            CANNOT_EVALUATE,
            "CANNOT EVALUATE -- shipped content changed, but the version at base and/or "
            f"head could not be read.\n{header}\n"
            f"base error: {base_err or '(none)'}\nhead error: {head_err or '(none)'}\n"
            f"This is not a pass: a gate that could not read {plugin_json_path} must not "
            "report PASS.",
        )

    if base_version_raw == head_version_raw:
        return (
            FLAGGED,
            "FLAGGED -- this PR changes shipped plugin content but "
            f"{plugin_json_path}'s \"version\" did not change "
            f"(stayed at {head_version_raw!r}).\n{header}\n"
            f"Remedy: bump the \"version\" field in {plugin_json_path} as part of this PR "
            "(semver: patch for a fix/hardening change, minor for a new capability, major "
            "for a breaking one). Claude Code resolves plugin updates from this field "
            "first -- an unbumped version means students who already installed never "
            "receive this change.",
        )

    base_v = parse_semver(base_version_raw)
    head_v = parse_semver(head_version_raw)
    if base_v is None or head_v is None:
        return (
            CANNOT_EVALUATE,
            "CANNOT EVALUATE -- shipped content changed and the version string changed, "
            f"but one of the two values is not a plain X.Y.Z semver: base={base_version_raw!r} "
            f"head={head_version_raw!r}. Fix the version string's format so it can be "
            "compared, then re-run.",
        )

    if head_v <= base_v:
        return (
            FLAGGED,
            f"FLAGGED -- {plugin_json_path}'s \"version\" changed from {base_version_raw!r} "
            f"to {head_version_raw!r}, but that is not an increase.\n{header}\n"
            "Remedy: the new version must be strictly greater (semver order) than the one "
            "on the base branch.",
        )

    return (
        PASS,
        f"PASS -- shipped content changed and {plugin_json_path}'s \"version\" increased "
        f"from {base_version_raw!r} to {head_version_raw!r}.\n{header}",
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base")
    parser.add_argument("--head")
    parser.add_argument("--mode", choices=["merge-base", "linear"], default="merge-base")
    parser.add_argument(
        "--plugin-json", default=".claude-plugin/plugin.json",
        help="repo-relative path to the plugin manifest (default: .claude-plugin/plugin.json)",
    )
    # Fixture-testing path: bypass git entirely.
    parser.add_argument("--changed-files-in", help="path to a file, one changed path per line")
    parser.add_argument("--base-json", help="path to a fixture plugin.json for 'base'")
    parser.add_argument("--head-json", help="path to a fixture plugin.json for 'head'")
    args = parser.parse_args(argv)

    if args.changed_files_in:
        with open(args.changed_files_in, encoding="utf-8") as fh:
            files = [line.strip() for line in fh if line.strip()]

        def read_fixture(path: str) -> tuple[str | None, str | None]:
            try:
                with open(path, encoding="utf-8") as fh:
                    data = json.load(fh)
            except (OSError, json.JSONDecodeError) as exc:
                return None, f"could not read/parse fixture {path}: {exc}"
            version = data.get("version")
            if not isinstance(version, str):
                return None, f"fixture {path} has no string 'version' field"
            return version, None

        base_version, base_err = read_fixture(args.base_json) if args.base_json else (None, "no --base-json given")
        head_version, head_err = read_fixture(args.head_json) if args.head_json else (None, "no --head-json given")
    else:
        if not args.base or not args.head:
            print("CANNOT EVALUATE -- --base and --head are required (or use the fixture flags)", file=sys.stderr)
            return CANNOT_EVALUATE
        try:
            files = changed_files(args.base, args.head, args.mode)
        except RuntimeError as exc:
            print(f"CANNOT EVALUATE -- {exc}", file=sys.stderr)
            return CANNOT_EVALUATE
        base_version, base_err = read_version_at(args.base, args.plugin_json)
        head_version, head_err = read_version_at(args.head, args.plugin_json)

    code, message = evaluate(files, base_version, base_err, head_version, head_err, args.plugin_json)
    print(message)
    return code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

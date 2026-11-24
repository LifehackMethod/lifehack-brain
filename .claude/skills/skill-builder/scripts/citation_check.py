#!/usr/bin/env python3
"""citation_check.py — packet-path citations in a packet file.

CALLER: run by the skill-builder step prompts whenever a packet file has been
written or edited (3.4 "saves into the packet every turn", 5.1/5.2 before the
compile check hands the packet on). Usage:

    citation_check.py --workdir <packet folder> --file <a packet .md file> [--timeout 20]

WHY NO SHARED TOOL COVERS IT: the shared tools read files safely and guard the
repo; none of them knows what a "packet-path citation" is — a backticked path in
a packet file that must resolve inside the packet folder. Skill-local knowledge,
so it lives in the skill. Every path arrives as an argument; the script writes
NOTHING anywhere — stdout only.

WHAT IT CHECKS: every backticked span in the file that names a packet-relative
path must EXIST inside the packet folder (--workdir). A span is treated as a
packet-relative path when it is non-empty and NOT skipped below — deny by
default: anything not recognised as elsewhere is checked here.
SKIPPED (counted "not checked here" in the receipt's untested line): spans
starting with `/`, `~`, `<` (a placeholder like <brain>), or a plugin path —
`system/`, `canon/`, `.claude/`, `shared/`; and spans that are not path-shaped
(no `/` and no filename extension), e.g. sub-step numbers and answer tags.

Exit codes: 0 PASS — every checked citation exists (duplicates are REPORTED but
not fatal). 1 FAIL — at least one citation points at something missing, with
missing / duplicate counts taken from the source. 2 COULD-NOT-CHECK — bad args,
unreadable file or workdir, timeout.
"""

import argparse
import os
import re
import signal
import sys

# Repo-shared helpers, found from THIS FILE's position (walk up to the folder
# that holds shared/paths.py), never from cwd. From a copied location (the
# broken-copy test) PYTHONPATH must carry <repo>/shared instead.
_HERE = os.path.dirname(os.path.abspath(__file__))
for _d in (os.path.dirname(_HERE), os.path.dirname(os.path.dirname(_HERE)),
           os.path.dirname(os.path.dirname(os.path.dirname(_HERE))),
           os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_HERE))))):
    if os.path.isfile(os.path.join(_d, "shared", "paths.py")):
        sys.path.insert(0, os.path.join(_d, "shared"))
        break
try:
    import paths  # shared/paths.py — the one place repo paths are answered; no hard-coded path here
except Exception:
    paths = None

DEFAULT_TIMEOUT = 20
SKIP_PREFIXES = ("/", "~", "<", "system/", "canon/", ".claude/", "shared/")
BACKTICK = re.compile(r"`([^`\n]+)`")
EXTENSION = re.compile(r"\.[A-Za-z][A-Za-z0-9]{1,4}$")  # .md/.json/.py — a first digit is a sub-step number (1.6), not a path


class TimeUp(Exception):
    pass


def arm_timeout(seconds):
    def handler(signum, frame):
        raise TimeUp()
    signal.signal(signal.SIGALRM, handler)
    signal.alarm(max(1, int(seconds)))


def refuse(why, what_to_do, rule):
    print(f"REFUSED: {why}")
    print(f"WHAT TO DO: {what_to_do}")
    print(f"RULE: {rule}")


def script_name():
    return os.path.basename(sys.argv[0]) if sys.argv and sys.argv[0] else "citation_check.py"


def is_skipped(span):
    """Outside the packet, or not a path at all — counted, never checked here."""
    if span.startswith(SKIP_PREFIXES):  # tuple startswith = any prefix
        return True
    if "/" not in span and not EXTENSION.search(span):
        return True
    return False


def packet_exists(workdir, rel):
    """True only if the cited path exists inside the packet AND its final
    filename matches EXACTLY (case-sensitive listing compare) — a
    case-insensitive filesystem must not turn a near-miss spelling into a pass.
    """
    full = os.path.normpath(os.path.join(workdir, rel))
    real_work = os.path.abspath(workdir)
    if full != real_work and not full.startswith(real_work + os.sep):
        return False  # escaped the packet (e.g. via ..)
    if not os.path.exists(full):
        return False
    try:
        entries = os.listdir(os.path.dirname(full) or full)
    except OSError:
        return False
    return os.path.basename(full) in entries  # exact, case-sensitive


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Check backticked packet-path citations in a packet file (skill-builder).")
    parser.add_argument("--workdir", required=True, help="the packet folder")
    parser.add_argument("--file", required=True, help="a packet .md file to check")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    args = parser.parse_args(argv)

    if not os.path.isdir(args.workdir):
        refuse(f"workdir '{args.workdir}' is not a readable folder",
               "pass the packet folder: --workdir <packet folder>",
               "a missing packet folder is COULD-NOT-CHECK, never a pass")
        print(f"RECEIPT {script_name()} COULD-NOT-CHECK unreadable workdir | "
              f"untested: nothing was checked")
        return 2
    if not os.path.isfile(args.file):
        refuse(f"file '{args.file}' is not a readable file",
               "pass the packet file to check: --file <packet .md file>",
               "a missing file is COULD-NOT-CHECK, never a pass")
        print(f"RECEIPT {script_name()} COULD-NOT-CHECK unreadable file | "
              f"untested: nothing was checked")
        return 2

    arm_timeout(args.timeout)
    try:
        with open(args.file, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        spans = BACKTICK.findall(text)
    except TimeUp:
        print(f"RECEIPT {script_name()} COULD-NOT-CHECK timed out after {args.timeout}s | "
              f"untested: the file's citations")
        return 2
    finally:
        signal.alarm(0)

    checked, skipped = [], 0
    for span in spans:
        s = span.strip()
        if not s or is_skipped(s):
            skipped += 1
        else:
            checked.append(s)

    missing, seen = [], {}
    for p in checked:
        seen[p] = seen.get(p, 0) + 1
        if not packet_exists(args.workdir, p):
            if p not in missing:
                missing.append(p)
    duplicates = sorted(p for p, n in seen.items() if n > 1)

    if missing:
        print(f"missing ({len(missing)}):")
        for p in missing:
            print(f"  {p}")
        if duplicates:
            print(f"duplicate citations ({len(duplicates)}): " + ", ".join(duplicates))
        print(f"RECEIPT {script_name()} FAIL {len(missing)} missing citation(s) of "
              f"{len(checked)} checked | untested: {skipped} span(s) not checked here "
              f"(outside the packet or not path-shaped); duplicate citations reported, "
              f"not fatal; file contents beyond the citations")
        return 1

    dup_note = f"; duplicate citations ({len(duplicates)}): {', '.join(duplicates)}" if duplicates else ""
    print(f"all {len(checked)} packet citation(s) exist{dup_note}")
    print(f"RECEIPT {script_name()} PASS {len(checked)} citation(s) checked, {skipped} not "
          f"checked here | untested: the {skipped} skipped span(s) (outside the packet or "
          f"not path-shaped); whether cited files' CONTENT matches; file text beyond citations")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""cal-lifemap-write.py — deterministic section-replace tool for the canonical Life Map.

Overwrites ONE horizon section's body in the Life Map markdown while leaving every
other byte of the file identical. No LLM in this path — fully mechanical.

Structure assumed: YAML frontmatter block, then H2 sections (`## …`), each terminated
by a `---` horizontal rule on its own line.

Usage:
    cal-lifemap-write.py --file <path> --section <name> --body-file <path> [--check] [--date YYYY-MM-DD]

    --file      : path to the life-map.md (required)
    --section   : horizon key (case-insensitive): yearly | quarterly | monthly | weekly | daily | critical-path
    --body-file : file whose contents replace the section body (the text between the heading and its ---)
    --check     : dry-run — print unified diff and exit 0 without writing
    --date      : YYYY-MM-DD — if given, bumps updated_at in YAML frontmatter (deterministic; never calls datetime.now())

Section matching: matched on the H2 heading PREFIX after '## ', so the '— *Helmsman…*'
suffix does not have to be typed. 'critical-path' matches '## Critical Path Table'.
Fails loud (non-zero, no write) if the section heading is not found.
"""
import argparse, difflib, os, re, sys

# Map short key -> prefix that the ## heading starts with (after '## ')
SECTION_PREFIXES = {
    "yearly":        "Yearly",
    "quarterly":     "Quarterly",
    "monthly":       "Monthly",
    "weekly":        "Weekly",
    "daily":         "Daily",
    "critical-path": "Critical Path",
}


def die(msg):
    sys.stderr.write(f"cal-lifemap-write: ERROR: {msg}\n")
    sys.exit(1)


def parse_args():
    ap = argparse.ArgumentParser(
        description="Deterministic section-replace for the canonical Life Map.")
    ap.add_argument("--file",      required=True, help="Path to life-map.md")
    ap.add_argument("--section",   required=True, help="Section key: yearly|quarterly|monthly|weekly|daily|critical-path")
    ap.add_argument("--body-file", required=True, dest="body_file", help="File containing the new body text")
    ap.add_argument("--check",     action="store_true", help="Dry-run: print diff, no write")
    ap.add_argument("--date",      default=None,  help="YYYY-MM-DD — bumps updated_at in frontmatter")
    return ap.parse_args()


def bump_updated_at(lines, new_date):
    """Return lines with updated_at: <new_date> replaced in the YAML frontmatter block.
    Frontmatter is delimited by the first two '---' lines. Leaves file unchanged if
    the key is absent or frontmatter is not found. Deterministic — caller passes the date."""
    if not lines or lines[0].rstrip() != "---":
        return lines  # no frontmatter
    result = list(lines)
    in_fm = False
    for i, ln in enumerate(result):
        stripped = ln.rstrip()
        if i == 0 and stripped == "---":
            in_fm = True
            continue
        if in_fm and stripped == "---":
            break  # end of frontmatter — key not found, no change
        if in_fm and re.match(r"^updated_at\s*:", ln):
            indent = re.match(r"^(\s*)", ln).group(1)
            result[i] = f"{indent}updated_at: {new_date}\n"
            break
    return result


def find_section(lines, prefix):
    """Return (heading_idx, close_idx) where:
       heading_idx : index of the '## <prefix>…' line
       close_idx   : index of the '---' line that closes the section
    Returns (None, None) if not found. Fails loud if the closing '---' is missing."""
    heading_idx = None
    for i, ln in enumerate(lines):
        if ln.startswith("## ") and ln[3:].startswith(prefix):
            heading_idx = i
            break
    if heading_idx is None:
        return None, None
    # Scan forward for the closing '---'
    for j in range(heading_idx + 1, len(lines)):
        if lines[j].rstrip() == "---":
            return heading_idx, j
    die(f"Section '## {prefix}…' found at line {heading_idx + 1} but has no closing '---' — file may be truncated.")


def assemble(lines, heading_idx, close_idx, new_body_lines):
    """Return full file lines with the section body replaced.
    Preserves: everything up to and including the heading line, the closing '---', and everything after."""
    before     = lines[:heading_idx + 1]   # up to and including the heading line
    separator  = [lines[close_idx]]        # the '---' closer
    after      = lines[close_idx + 1:]     # everything after the '---'

    # Ensure new body ends with exactly one newline before the '---'
    body = list(new_body_lines)
    # Strip trailing blank lines then add one blank line for readability
    while body and body[-1].strip() == "":
        body.pop()
    body.append("\n")  # blank line before the '---'

    return before + body + separator + after


def unified_diff(old_lines, new_lines, filepath):
    return "".join(difflib.unified_diff(
        old_lines, new_lines,
        fromfile=f"a/{os.path.basename(filepath)}",
        tofile=f"b/{os.path.basename(filepath)}",
    ))


def main():
    args = parse_args()

    # Validate section key
    section_key = args.section.lower()
    if section_key not in SECTION_PREFIXES:
        die(f"Unknown --section '{args.section}'. Valid keys: {', '.join(SECTION_PREFIXES)}")
    prefix = SECTION_PREFIXES[section_key]

    # Read source file
    if not os.path.isfile(args.file):
        die(f"--file not found: {args.file}")
    try:
        with open(args.file, encoding="utf-8") as f:
            original_lines = f.readlines()
    except Exception as e:
        die(f"Could not read --file: {e}")

    # Read body file
    if not os.path.isfile(args.body_file):
        die(f"--body-file not found: {args.body_file}")
    try:
        with open(args.body_file, encoding="utf-8") as f:
            body_lines = f.readlines()
    except Exception as e:
        die(f"Could not read --body-file: {e}")

    # Validate --date if given
    if args.date:
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", args.date):
            die(f"--date must be YYYY-MM-DD, got: '{args.date}'")

    # Locate section
    heading_idx, close_idx = find_section(original_lines, prefix)
    if heading_idx is None:
        die(f"Section heading starting with '## {prefix}' not found in {args.file}. No write performed.")

    # Build new file
    working = list(original_lines)
    if args.date:
        working = bump_updated_at(working, args.date)
    new_lines = assemble(working, heading_idx, close_idx, body_lines)

    # Dry-run
    if args.check:
        diff = unified_diff(original_lines, new_lines, args.file)
        if diff:
            print(diff, end="")
        else:
            print("(no changes)")
        return 0

    # Atomic write
    target = args.file
    tmp = target + ".lifemap-write.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        os.replace(tmp, target)
    except Exception as e:
        # Clean up temp if possible
        try:
            os.unlink(tmp)
        except Exception:
            pass
        die(f"Atomic write failed: {e}")

    print(f"[cal-lifemap-write] wrote '{prefix}…' section → {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

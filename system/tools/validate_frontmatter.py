#!/usr/bin/env python3
"""
Runtime metadata validator for the files this system writes.

Validates frontmatter compliance on write operations:
- Requires: record_type, desk, created_at, status
- Forbids: artifact_type — an older name for record_type, kept in the forbidden set so a
  file written against the old shape is rejected rather than half-read

Can be invoked two ways:
1. Direct call: python3 validate_frontmatter.py <filepath>
2. Via Claude Code hook in settings.json (PostToolUse)

Exit codes:
  0 = valid
  1 = validation failed (forbidden field found or required field missing)
  2 = file does not exist or is not markdown

Usage:
  # Direct validation
  python3 validate_frontmatter.py /path/to/file.md

  # In a skill (before save):
  subprocess.run(["python3", "validate_frontmatter.py", filepath], check=True)
"""

import os
import sys
import re
from datetime import datetime

REQUIRED_FIELDS = {"record_type", "desk", "created_at", "status"}
FORBIDDEN_FIELDS = {"artifact_type"}  # record_type is the canonical name

def validate_file(filepath):
    """
    Validate frontmatter of a markdown file.
    Returns (valid: bool, message: str).
    """
    # Only check markdown files
    if not filepath.endswith(".md"):
        return True, f"skip: {filepath} is not markdown"

    if not os.path.isfile(filepath):
        return True, f"skip: {filepath} does not exist"

    # Only validate what THIS SYSTEM writes. A person's own files, dropped anywhere in their notes
    # folder, are theirs — a validator that lectures somebody about the frontmatter on a file they
    # wrote by hand is noise, and noise is how a real violation gets skimmed past.
    MANAGED = ("desks/", "system/", "state/projects/", "records/")
    if not any(pattern in filepath for pattern in MANAGED):
        return True, f"skip: {filepath} is not a managed file"

    # Don't validate .bak or fixture files
    if ".bak" in filepath or "fixture" in filepath.lower():
        return True, f"skip: {filepath} is a backup or fixture"

    # Don't validate quarantined / archived / external content — these are NOT managed records
    # (they're sandboxed external material or immutable archives). Validating them was scope
    # over-reach that inflated the violation count. (organism-audit defect d, 2026-07-20.)
    if any(seg in filepath for seg in ("quarantine/", "/_archive", "/archive/", "node_modules/")):
        return True, f"skip: {filepath} is quarantined/archived/external (not a managed record)"

    try:
        with open(filepath) as f:
            content = f.read()
    except Exception as e:
        return False, f"error reading {filepath}: {e}"

    # Must start with frontmatter
    if not content.startswith("---"):
        # Not an error — just skip files without frontmatter
        return True, f"skip: {filepath} has no frontmatter"

    # Extract frontmatter block
    end = content.find("---", 3)
    if end == -1:
        return False, f"error: {filepath} frontmatter block not closed"

    frontmatter = content[3:end]

    # Check for forbidden fields
    for forbidden in FORBIDDEN_FIELDS:
        if f"{forbidden}:" in frontmatter:
            return False, f"REJECT: {filepath} uses forbidden field '{forbidden}' (use 'record_type' instead)"

    # Effective required set: system-wide docs (authority: system | archivist) legitimately
    # belong to NO single desk, so `desk` is not required for them — a desk cannot be
    # backfilled onto a system-wide file. (organism-audit d.c 2026-07-21; the "no-desk
    # exemption" the LLM triage confirmed on system/security-canon.md, google-policy.md, etc.)
    required = set(REQUIRED_FIELDS)
    _auth = re.search(r'(?m)^authority:\s*(\w+)', frontmatter)
    if _auth and _auth.group(1).lower() in ("system", "archivist"):
        required.discard("desk")

    # Check for required fields
    missing = [f for f in required if f + ":" not in frontmatter]
    if missing:
        return False, f"REJECT: {filepath} missing required fields: {sorted(missing)}"

    return True, f"valid: {filepath}"


def main():
    if len(sys.argv) < 2:
        print("Usage: validate_frontmatter.py <filepath>", file=sys.stderr)
        sys.exit(2)

    filepath = sys.argv[1]
    valid, message = validate_file(filepath)

    if not valid:
        print(f"✗ {message}", file=sys.stderr)
        sys.exit(1)

    # Suppress output for successful validations (hook use case)
    # (Uncomment for debugging)
    # print(f"✓ {message}")
    sys.exit(0)


if __name__ == "__main__":
    main()

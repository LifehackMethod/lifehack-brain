"""safe_csv.py — CSV reader + L0 sanitizer.

Reads CSV files and applies:
  1. Formula injection stripping — cells starting with =, +, -, @ are formula
     injection vectors when opened in Excel/Google Sheets. Strip the leading
     char to defuse the payload before it reaches context.
  2. L0 sanitization — zero-width chars, bidi overrides, HTML entities, C0
     controls stripped from all cell values.

No hidden-cell filtering needed (CSV has no rendering layer).

Usage (from Claude via Bash):
    python3 /path/to/safe_csv.py '/path/to/file.csv'

Exits non-zero on error. Output is a cleaned table as tab-separated text.
"""
import sys
import os
import csv

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)

from sanitize import sanitize, NO_CAP

try:
    from safe_input import scan_for_injection, provenance_route, resolve_desk
except ImportError:
    scan_for_injection = None; provenance_route = None; resolve_desk = None

_MAX_FILE_BYTES = 5_000_000   # 5 MB cap
_FORMULA_CHARS = frozenset("=+-@")
_ENCODINGS = ("utf-8", "utf-8-sig", "latin-1", "cp1252")

import re
# A cell that is NOTHING BUT a signed/plain number (optionally with thousands commas and a
# decimal point) is not a formula — Excel/Sheets never execute a bare number. Ledger values like
# -18500 or -3.75 start with the same '-' that also starts a formula, so a blind "strip the first
# char" flips their sign silently. This regex is the exemption: it must match the WHOLE cell (after
# stripping surrounding whitespace) or it doesn't apply, so "-Rent", "-1+1" and "=1+1" (leading '='
# is never numeric) all still fall through to the strip below.
_PLAIN_SIGNED_NUMBER = re.compile(r"^[+-]?\d{1,3}(,\d{3})*(\.\d+)?$|^[+-]?\d+(\.\d+)?$")


def _defuse_formula(value: str) -> str:
    """Strip leading formula injection chars from a cell value — UNLESS the whole cell is a plain
    signed number, in which case the leading +/- is a sign, not a formula trigger."""
    if value and value[0] in _FORMULA_CHARS:
        stripped = value.strip()
        if value[0] in "+-" and _PLAIN_SIGNED_NUMBER.match(stripped):
            return stripped
        return value[1:].strip()
    return value


def read_and_sanitize(path: str, desk: str = "root") -> str:
    """Read a CSV file, defuse formulas, apply L0 sanitization.

    Returns clean tab-separated text. Raises RuntimeError on errors.
    """
    try:
        file_size = os.path.getsize(path)
    except OSError as e:
        raise RuntimeError(f"Cannot access file {path}: {e}") from e

    if file_size > _MAX_FILE_BYTES:
        raise RuntimeError(
            f"File too large: {file_size:,} bytes (max {_MAX_FILE_BYTES:,})."
        )

    raw_text = None
    for enc in _ENCODINGS:
        try:
            with open(path, "r", encoding=enc, errors="strict", newline="") as f:
                raw_text = f.read()
            break
        except (UnicodeDecodeError, LookupError):
            continue

    if raw_text is None:
        with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
            raw_text = f.read()

    # Parse CSV
    import io
    reader = csv.reader(io.StringIO(raw_text))
    output_rows = []
    try:
        for row in reader:
            clean_cells = []
            for cell in row:
                defused = _defuse_formula(cell)
                clean = sanitize(defused, max_len=NO_CAP)
                clean_cells.append(clean)
            output_rows.append("\t".join(clean_cells))
    except csv.Error as e:
        raise RuntimeError(f"CSV parse error in {path}: {e}") from e

    result = "\n".join(output_rows)

    # Heuristic injection scan — flags to stderr
    if scan_for_injection is not None:
        findings = scan_for_injection(result)
        if provenance_route is not None:
            provenance_route(desk, "file", result, item=path)   # on-path gate (W5): provenance + coverage breadcrumb + Sentinel verdict; format preserved in item=path
        if findings:
            import sys as _sys
            print(f"[safe_csv] FLAGGED — {len(findings)} injection pattern(s) detected:", file=_sys.stderr)
            for match, label in findings:
                print(f"  [{label}] \"{match}\"", file=_sys.stderr)

    return result


if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "system", "tools")))
    from utf8_stdio import force_utf8_stdio
    force_utf8_stdio()
    desk, rest = resolve_desk() if resolve_desk else ("root", sys.argv[1:])
    if not rest:
        print("Usage: python3 safe_csv.py [--desk <id>] '/path/to/file.csv'", file=sys.stderr)
        sys.exit(1)

    csv_path = rest[0]
    try:
        result = read_and_sanitize(csv_path, desk=desk)
        print(result)
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

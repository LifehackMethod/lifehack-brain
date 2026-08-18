"""safe_pdf.py — PDF extractor + L0 sanitizer.

Extracts visible text from PDF files using pdfplumber, filtering out
hidden text (white/near-white color, sub-4pt font size), and runs L0
sanitization before returning content.

This is the only sanctioned way to read a PDF here — the Read tool is blocked on .pdf by
system/hooks/ingest_gate_enforce.sh, which points at this file.
Use instead of reading PDFs directly to ensure L0 sanitization and
invisible-text filtering before content reaches the model.

Usage (from Claude via Bash):
    python3 /path/to/safe_pdf.py '/path/to/file.pdf'

Exits non-zero on error. Output is clean plaintext on stdout.

Out of scope (v1):
    - Scanned PDFs (image-only, no text layer) — returns empty string
    - Annotations and form fields
    - Embedded JavaScript
    - Encrypted/password-protected PDFs
"""
import sys
import os

# Add system/tools to path so sanitize.py is importable from any directory
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)

try:
    import pdfplumber
except ImportError:
    print(
        "ERROR: pdfplumber not installed.\n"
        "Install with: pip install pdfplumber",
        file=sys.stderr,
    )
    sys.exit(1)

from sanitize import sanitize, NO_CAP

try:
    from safe_input import scan_for_injection, provenance_route, resolve_desk
except ImportError:
    scan_for_injection = None; provenance_route = None; resolve_desk = None

_MAX_FILE_BYTES = 10_000_000  # 10 MB cap
_MIN_FONT_SIZE = 4.0          # chars below this are invisible in practice
_WHITE_THRESHOLD = 0.9        # grayscale/RGB values above this = near-white

# Metadata fields worth extracting (content-bearing)
_META_FIELDS = ("Title", "Author", "Subject", "Keywords", "Creator")


def _is_hidden_char(char: dict) -> bool:
    """Return True if this character is invisible (white text or sub-threshold size)."""
    # Font size filter
    size = char.get("size")
    if size is not None and float(size) < _MIN_FONT_SIZE:
        return True

    # Color filter — pdfplumber uses non_stroking_color for fill color
    color = char.get("non_stroking_color")
    if color is None:
        return False

    # Grayscale: single float — 1.0 = white
    if isinstance(color, (int, float)):
        return float(color) > _WHITE_THRESHOLD

    if isinstance(color, (list, tuple)):
        # RGB: (r, g, b) — all near 1.0 = white
        if len(color) == 3:
            return all(float(c) > _WHITE_THRESHOLD for c in color)
        # CMYK: (c, m, y, k) — all near 0.0 = white
        if len(color) == 4:
            return all(float(c) < (1.0 - _WHITE_THRESHOLD) for c in color)

    return False


def _extract_metadata(meta: dict) -> str:
    """Extract and sanitize content-bearing metadata fields."""
    parts = []
    for field in _META_FIELDS:
        value = meta.get(field) or meta.get(field.lower(), "")
        if value and str(value).strip():
            clean = sanitize(str(value), max_len=200)
            if clean:
                parts.append(f"[{field}: {clean}]")
    return "\n".join(parts)


def extract_and_sanitize(path: str, desk: str = "root") -> str:
    """Extract visible text from a PDF, filter hidden chars, run L0 sanitization.

    Returns clean plaintext. Raises RuntimeError on unrecoverable errors.
    Returns empty string for valid PDFs with no extractable text (e.g. scanned).
    """
    # Size cap — check before opening
    try:
        file_size = os.path.getsize(path)
    except OSError as e:
        raise RuntimeError(f"Cannot access file {path}: {e}") from e

    if file_size > _MAX_FILE_BYTES:
        raise RuntimeError(
            f"File too large: {file_size:,} bytes (max {_MAX_FILE_BYTES:,}). "
            "Split the file or extract the relevant pages first."
        )

    try:
        with pdfplumber.open(path) as pdf:
            # Metadata
            meta_text = _extract_metadata(pdf.metadata or {})

            # Body — collect visible chars page by page
            body_parts = []
            for page_num, page in enumerate(pdf.pages, 1):
                page_chars = []
                for char in (page.chars or []):
                    if not _is_hidden_char(char):
                        page_chars.append(char.get("text", ""))

                page_text = "".join(page_chars).strip()
                if page_text:
                    body_parts.append(page_text)

            body_raw = "\n\n".join(body_parts)

    except pdfplumber.pdfminer.pdfparser.PDFSyntaxError as e:
        raise RuntimeError(f"Corrupt or invalid PDF: {e}") from e
    except Exception as e:
        # Catch encrypted PDFs and other pdfplumber errors
        msg = str(e)
        if "password" in msg.lower() or "encrypt" in msg.lower():
            raise RuntimeError(f"Encrypted PDF — cannot extract without password: {e}") from e
        raise RuntimeError(f"Failed to process PDF: {e}") from e

    # L0 sanitization on body — no length cap, DOCUMENT mode (issue #77 / D4).
    # body_raw is a whole PDF, pages joined on "\n\n"; FIELD mode collapsed all of that
    # to one line. pdfplumber yields plain text characters, never markup, so a `<…>` here
    # is document content. Metadata above stays FIELD mode — those are one-line values.
    body_clean = sanitize(body_raw, max_len=NO_CAP, preserve_structure=True)

    # Assemble output
    sections = []
    if meta_text:
        sections.append(meta_text)
    if body_clean:
        sections.append(body_clean)

    result = "\n\n".join(sections)

    # Heuristic injection scan — flags to stderr
    if scan_for_injection is not None:
        findings = scan_for_injection(result)
        if provenance_route is not None:
            provenance_route(desk, "file", result, item=path)   # on-path gate (W5): provenance + coverage breadcrumb + Sentinel verdict; format preserved in item=path
        if findings:
            print(f"[safe_pdf] FLAGGED — {len(findings)} injection pattern(s) detected:", file=sys.stderr)
            for match, label in findings:
                print(f"  [{label}] \"{match}\"", file=sys.stderr)

    return result


if __name__ == "__main__":
    desk, rest = resolve_desk() if resolve_desk else ("root", sys.argv[1:])
    if not rest:
        print("Usage: python3 safe_pdf.py [--desk <id>] '/path/to/file.pdf'", file=sys.stderr)
        sys.exit(1)

    pdf_path = rest[0]
    try:
        result = extract_and_sanitize(pdf_path, desk=desk)
        print(result)
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

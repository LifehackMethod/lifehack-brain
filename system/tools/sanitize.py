"""L0 — deterministic sanitization.

Port of DataGate Kit's sanitize.py for Lifehack.
Strips HTML, decodes entities, removes hidden/dangerous Unicode
(zero-width, bidi overrides, control chars), normalizes whitespace,
caps length.

TWO MODES — pick by what the string IS, not by where it came from.

  FIELD mode (preserve_structure=False, THE DEFAULT — byte-for-byte what this
  function has always done). For one-line values: a Subject, a From, a
  spreadsheet cell, a calendar title. Every `<…>` span goes, and every run of
  whitespace — newlines included — collapses to a single space.

  DOCUMENT mode (preserve_structure=True, added 2026-08-18). For a WHOLE
  DOCUMENT: a text file, a PDF/.docx body, the visible text of a web page. Line
  breaks SURVIVE; `<…>` spans survive.

WHY DOCUMENT MODE EXISTS (issue #77, finding D4 — reproduced, not theoretical).
This function was written for email FIELDS. Then safe_read.py and the other
safe_* readers began pointing whole documents at it with NO_CAP, and it ate them
silently, on every platform:

    sanitize("line one\\nline two\\n\\n# Heading\\n- bullet a\\n", max_len=NO_CAP)
      -> 'line one line two # Heading - bullet a'      # heading + list gone
    sanitize("use <name> and List<int> here", max_len=NO_CAP)
      -> 'use and List here'                            # type parameters eaten

Nothing errored. `/ingest` exists to turn a document corpus into structure and
reads through here, so it was being handed corpora whose heading hierarchy, list
boundaries and table rows had already been destroyed. The file even contradicted
itself: the control-character class below says "keep \\t \\n \\r" and then the
whitespace collapse deleted every newline anyway. Two independent callers had
already grown private workarounds rather than fix it — email_convert's
`_sanitize_preserving_lines()`, and the comment in cowork-ingest/gate_and_pack.py
explaining why its "## " turn markers can never be found. Those are the bug
leaving fingerprints.

⛔ WHAT DOES **NOT** CHANGE, IN EITHER MODE — this is the security function:
entity decoding, the unsafe-Unicode filter (zero-width, all nine bidi controls,
Tags block) and control-character stripping run identically in BOTH modes. Only
whitespace and angle-bracket handling differ. Document mode is NOT a "trusted"
mode and there is no such thing here — its output is still untrusted content,
still scanned by safe_input.scan_for_injection() downstream, still data and
never instructions.

The injection scanner is unaffected by the surviving newlines, and that is a
property of the patterns, not luck: every pattern in safe_input._PATTERNS joins
its words with `\\s+`/`\\s*`, which matches `\\n`, and not one uses `^`, `$` or a
`.` that would have to span a line. "ignore all\\nprevious instructions" flags
exactly as "ignore all previous instructions" does. There is a test for it.

Usage:
    from sanitize import sanitize, sanitize_fields, NO_CAP

    subject = sanitize(raw_subject)                              # FIELD (default)
    body    = sanitize(raw_body, max_len=NO_CAP)                 # FIELD, uncapped
    doc     = sanitize(raw_doc, max_len=NO_CAP,
                       preserve_structure=True)                  # DOCUMENT
    fields  = sanitize_fields({"subject": s, "body": b})

Script mode (for testing):
    python3 sanitize.py "some text with <b>HTML</b>"
    python3 sanitize.py --preserve-structure "$(cat doc.md)"

Tests: system/tools/test_sanitize.py
"""
import html as _html_mod
import re
import sys

_UNSAFE_UNICODE_RE = re.compile(
    "["
    "\u200b-\u200f"              # zero-width spaces / joiners
    "\u202a-\u202e"              # bidi EMBEDDINGS and OVERRIDES (LRE RLE PDF LRO RLO)
    "\u2060-\u2064"              # word joiner, invisible operators
    # \u2b50 ADDED 2026-08-11 \u2014 the bidi ISOLATES (U+2066 LRI \u00b7 U+2067 RLI \u00b7 U+2068 FSI \u00b7 U+2069 PDI).
    # They were missing, and they are not a footnote: they are the OTHER HALF of the same attack.
    # A bidi control makes text DISPLAY in a different order than it is stored, so a person reading
    # the file and a model reading the file see two different things \u2014 which is the entire point of
    # this function. The override family above was stripped and the isolate family sailed through.
    # Unicode added the isolates in 6.3 as the modern replacement for the overrides, so they are the
    # ones a current tool actually emits, and CVE-2021-42574 ("Trojan Source") names all nine
    # together. Found by a test written against this file's own stated promise on 2026-08-11:
    # U+2066 and U+2069 survived a sanitize() call that removed everything either side of them.
    # (U+2065 is unassigned, so the widened range costs nothing.)
    "\u2065-\u2069"              # bidi ISOLATES \u2014 same power as the overrides above
    "\u206a-\u206f"              # deprecated format characters
    "\ufeff"                     # BOM
    "\x00-\x08"                  # C0 controls (keep \t \n \r)
    "\x0b\x0c"                   # VT FF
    "\x0e-\x1f"                  # remaining C0
    "\x7f-\x9f"                  # DEL + C1 controls
    "\U000E0000-\U000E007F"      # Unicode Tags block (stego/invisible)
    "]"
)

_BODY_KEYS = frozenset({"body", "body_text", "body_html", "content", "message", "text"})

DEFAULT_FIELD_CAP = 200
DEFAULT_BODY_CAP = 800
NO_CAP = 0  # pass as max_len to disable length cap

# ── DOCUMENT-mode whitespace normalization ───────────────────────────────────
# Horizontal whitespace only — `\s` minus `\n`. This is what lets a run of tabs
# and spaces collapse while the line break that carries the document's structure
# survives. Matches the non-breaking space and friends too, which is the point:
# a padding flood is a real trick and NBSP is how you'd hide one.
_HSPACE_RUN_RE = re.compile(r"[^\S\n]+")
_LEADING_HSPACE_RE = re.compile(r"^([^\S\n]*)(.*)$")
# 3+ newlines -> exactly 2 (i.e. at most ONE blank line). Bounded, not deleted:
# the paragraph break is structure and is kept; a thousand blank lines pushing
# content out of a reader's view is a flood and is not.
_BLANK_LINE_RUN_RE = re.compile(r"\n{3,}")
# An indent conveys nesting (a sub-bullet, a fenced block), so it is preserved
# rather than collapsed — but preserved BOUNDED, so it cannot become a flood.
_MAX_INDENT = 8


def _normalize_document_whitespace(s: str) -> str:
    """Collapse whitespace the way a DOCUMENT needs it: kill runs, keep lines.

    Per line: keep the leading indent (capped at _MAX_INDENT chars, so nesting
    survives but a padding flood cannot), collapse every interior run of
    horizontal whitespace to ONE space, drop trailing spaces. Across lines:
    normalize CRLF/CR to LF and cap a run of blank lines at one.
    """
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    out = []
    for line in s.split("\n"):
        indent, rest = _LEADING_HSPACE_RE.match(line).groups()
        rest = _HSPACE_RUN_RE.sub(" ", rest).rstrip()
        out.append((indent[:_MAX_INDENT] + rest) if rest else "")
    s = "\n".join(out)
    return _BLANK_LINE_RUN_RE.sub("\n\n", s).strip()


def sanitize(s: str, max_len: int = DEFAULT_FIELD_CAP,
             preserve_structure: bool = False) -> str:
    """Sanitize a single string.

    Args:
        s: Input string (any source — email body, subject, document, web page).
        max_len: Maximum output length. Pass NO_CAP (0) to disable.
        preserve_structure: FIELD mode (False, the default) is the original
            behaviour, unchanged: strip every `<…>` span and flatten ALL
            whitespace — newlines included — to single spaces. DOCUMENT mode
            (True) keeps line breaks and keeps `<…>` spans, so headings, list
            boundaries, table rows, `<name>` and `List<int>` all survive.
            ⛔ Entity decoding, the unsafe-Unicode filter and control-character
            stripping are IDENTICAL in both modes — the mode changes only
            whitespace and angle-bracket handling, never the security floor.

    Returns:
        Cleaned string, length-capped if max_len > 0.
    """
    if not s:
        return ""
    s = _html_mod.unescape(s)
    if not preserve_structure:
        # FIELD mode only. Deliberately absent from DOCUMENT mode: after entity
        # decoding this eats real prose ("5 &lt; 6 &amp;&amp; 7 &gt; 3" -> "5 3")
        # and every generic type parameter, and it was never a dependable HTML
        # remover anyway — the {0,200} bound lets any longer tag straight
        # through, so leaning on it as a security control is false comfort. The
        # document callers switched to this mode take text that has ALREADY had
        # its markup removed structurally (an HTMLParser, pdfplumber, python-docx),
        # so a surviving `<…>` there is document content, not markup.
        s = re.sub(r"<[^>]{0,200}>", " ", s)
    # ⛔ BOTH MODES, ALWAYS — the actual security function. Do not gate on mode.
    s = _UNSAFE_UNICODE_RE.sub("", s)
    if preserve_structure:
        s = _normalize_document_whitespace(s)
    else:
        s = re.sub(r"\s+", " ", s).strip()
    if max_len and max_len > 0:
        return s[:max_len]
    return s


def sanitize_fields(
    fields: dict,
    max_field_chars: int = DEFAULT_FIELD_CAP,
    max_body_chars: int = DEFAULT_BODY_CAP,
) -> dict:
    """Sanitize a dict of fields.

    Body keys (body, body_text, content, etc.) get max_body_chars cap.
    All other keys get max_field_chars cap.
    Pass NO_CAP for either cap to disable length limiting on that class.

    ⚠ FIELD mode for EVERY key, including the body keys — unchanged on purpose.
    This helper's contract is a flat dict of one-line values, its callers index
    the result straight into single-line slots, and the body cap here is 800
    chars, which is an excerpt and not a document. A caller that genuinely holds
    a document calls sanitize(..., preserve_structure=True) itself.
    """
    out = {}
    for key, value in fields.items():
        cap = max_body_chars if key.lower() in _BODY_KEYS else max_field_chars
        out[key] = sanitize(value or "", max_len=cap)
    return out


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--preserve-structure"]
    doc_mode = "--preserve-structure" in sys.argv[1:]
    if not args:
        print("Usage: python3 sanitize.py [--preserve-structure] '<text>'", file=sys.stderr)
        sys.exit(1)
    result = sanitize(args[0], max_len=NO_CAP, preserve_structure=doc_mode)
    print(result)

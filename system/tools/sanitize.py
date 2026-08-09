"""L0 — deterministic sanitization.

Port of DataGate Kit's sanitize.py for Lifehack.
Strips HTML, decodes entities, removes hidden/dangerous Unicode
(zero-width, bidi overrides, control chars), normalizes whitespace,
caps length.

Usage:
    from sanitize import sanitize, sanitize_fields, NO_CAP

    body = sanitize(raw_text, max_len=NO_CAP)   # email bodies: no length cap
    fields = sanitize_fields({"subject": s, "body": b})

Script mode (for testing):
    python3 sanitize.py "some text with <b>HTML</b>"
"""
import html as _html_mod
import re
import sys

_UNSAFE_UNICODE_RE = re.compile(
    "["
    "\u200b-\u200f"              # zero-width spaces / joiners
    "\u202a-\u202e"              # bidirectional formatting overrides
    "\u2060-\u2064"              # word joiner, invisible operators
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


def sanitize(s: str, max_len: int = DEFAULT_FIELD_CAP) -> str:
    """Sanitize a single string.

    Args:
        s: Input string (any source — email body, subject, web content).
        max_len: Maximum output length. Pass NO_CAP (0) to disable.

    Returns:
        Cleaned string, length-capped if max_len > 0.
    """
    if not s:
        return ""
    s = _html_mod.unescape(s)
    s = re.sub(r"<[^>]{0,200}>", " ", s)
    s = _UNSAFE_UNICODE_RE.sub("", s)
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
    """
    out = {}
    for key, value in fields.items():
        cap = max_body_chars if key.lower() in _BODY_KEYS else max_field_chars
        out[key] = sanitize(value or "", max_len=cap)
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 sanitize.py '<text>'", file=sys.stderr)
        sys.exit(1)
    result = sanitize(sys.argv[1], max_len=NO_CAP)
    print(result)

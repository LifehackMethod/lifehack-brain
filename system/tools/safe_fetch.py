"""safe_fetch.py — URL fetcher + L0 sanitizer.

Fetches a URL using Python stdlib only (no pip install required).
Strips HTML to readable plaintext, skips hidden elements, runs L0
sanitization before returning content.

This is the only sanctioned way to fetch a page here — the WebFetch tool is blocked by
system/hooks/ingest_gate_enforce.sh, which points at this file.
Use instead of direct WebFetch to ensure L0 sanitization before content
reaches the model.

Usage (from Claude via Bash):
    python3 /path/to/safe_fetch.py 'https://example.com'

Exits non-zero on network error. Output is clean plaintext on stdout.

Testing commands:
    python3 safe_fetch.py 'https://example.com'
    python3 safe_fetch.py 'https://httpbin.org/html'
"""
import sys
import os
import re
import html as _html_mod
import urllib.request
from html.parser import HTMLParser

# Add system/tools to path so sanitize.py is importable when called from any directory
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)

from sanitize import sanitize, NO_CAP

try:
    from safe_input import scan_for_injection, provenance_route, resolve_desk
except ImportError:
    scan_for_injection = None; provenance_route = None; resolve_desk = None

_TIMEOUT = 10  # seconds
_USER_AGENT = "Mozilla/5.0 (compatible; safe-fetch/1.0)"
_MAX_BYTES = 2_000_000  # 2 MB cap — prevent memory bombs

# HTML elements whose content is invisible to humans but readable by LLMs
_SKIP_TAGS = frozenset({
    "script", "style", "nav", "footer", "head", "noscript",
    "template", "svg", "math",
})


class _TextExtractor(HTMLParser):
    """Extract visible text from HTML, skipping invisible and structural elements."""

    def __init__(self):
        super().__init__()
        self._parts = []
        self._skip_depth = 0       # depth counter for skipped tag trees
        self._hidden_depth = 0     # depth counter for CSS-hidden elements

    def handle_starttag(self, tag, attrs):
        tag_lower = tag.lower()

        # Skip entire subtrees for structural/script tags
        if tag_lower in _SKIP_TAGS:
            self._skip_depth += 1
            return

        # Skip elements hidden via inline CSS
        if self._is_hidden(attrs):
            self._hidden_depth += 1
            return

    def handle_endtag(self, tag):
        tag_lower = tag.lower()
        if tag_lower in _SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        elif self._hidden_depth > 0:
            self._hidden_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0 and self._hidden_depth == 0:
            stripped = data.strip()
            if stripped:
                self._parts.append(stripped)

    @staticmethod
    def _is_hidden(attrs):
        """Return True if inline style marks element as invisible."""
        for name, value in attrs:
            if name == "style" and value:
                v = value.lower().replace(" ", "")
                if any(pattern in v for pattern in (
                    "display:none",
                    "visibility:hidden",
                    "opacity:0",
                    "font-size:0",
                    "color:transparent",
                )):
                    return True
        return False

    def get_text(self):
        return "\n".join(self._parts)


def _detect_charset(headers, body_bytes: bytes) -> str:
    """Detect charset from Content-Type header or HTML meta tag. Fallback: utf-8."""
    content_type = headers.get("Content-Type", "") or headers.get("content-type", "")
    if "charset=" in content_type.lower():
        _, _, cs = content_type.lower().partition("charset=")
        cs = cs.split(";")[0].strip()
        if cs:
            return cs

    # Try meta charset from first 2KB of body
    head = body_bytes[:2048].decode("ascii", errors="ignore").lower()
    m = re.search(r'charset=["\']?([a-z0-9_-]+)', head)
    if m:
        return m.group(1)

    return "utf-8"


def _enforce_egress_allowlist(url):
    """Egress wall (reader-actor build 2026-07-02). If SAFE_FETCH_ALLOWLIST is set
    (comma-separated domains the orchestrator sealed from search results), reject any
    URL whose host is not that domain or a subdomain of it — BEFORE the socket opens.
    Also hard-block non-http(s) schemes (SSRF hygiene). Unset allowlist == unchanged
    behavior (backward-compatible for the existing callers)."""
    import os as _os
    from urllib.parse import urlparse as _urlparse
    parsed = _urlparse(url)
    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        raise RuntimeError(f"egress blocked: scheme '{scheme}' not allowed (http/https only): {url}")
    allow = _os.environ.get("SAFE_FETCH_ALLOWLIST", "").strip()
    if not allow:
        return
    host = (parsed.hostname or "").lower()
    domains = [d.strip().lower().lstrip(".") for d in allow.split(",") if d.strip()]
    for d in domains:
        if host == d or host.endswith("." + d):
            return
    raise RuntimeError(f"egress blocked: host '{host}' not in sealed allowlist ({', '.join(domains)}): {url}")


def fetch_and_sanitize(url: str, desk: str = "root") -> str:
    """Fetch URL, extract visible text, run L0 sanitization.

    Returns clean plaintext. Raises on network error. `desk` tags provenance/coverage (Window 5).
    """
    _enforce_egress_allowlist(url)
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            charset = _detect_charset(dict(resp.headers), b"")
            raw_bytes = resp.read(_MAX_BYTES)
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error fetching {url}: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Unexpected error fetching {url}: {e}") from e

    # Decode
    charset = _detect_charset({}, raw_bytes) if charset == "utf-8" else charset
    try:
        raw_text = raw_bytes.decode(charset, errors="replace")
    except (LookupError, ValueError):
        raw_text = raw_bytes.decode("utf-8", errors="replace")

    # Always run through HTMLParser. For true plain text (no < > chars) this is
    # a no-op — handle_data captures everything. For HTML, tags are filtered.
    # The old heuristic (detect <html>/<body>) was too strict and missed fragments.
    parser = _TextExtractor()
    parser.feed(raw_text)
    visible_text = parser.get_text()
    # Fall back to raw text if parser extracted nothing (e.g. pure plain text with
    # no recognized text nodes)
    if not visible_text.strip():
        visible_text = raw_text

    # L0 sanitization — no length cap on full page content
    clean = sanitize(visible_text, max_len=NO_CAP)

    # Heuristic injection scan — flags to stderr
    if scan_for_injection is not None:
        findings = scan_for_injection(clean)
        if provenance_route is not None:
            provenance_route(desk, "web", clean, item=url)   # on-path gate (W5): provenance tag + coverage breadcrumb (clean incl.) + Sentinel verdict; item=url so a web DANGER is triageable
        if findings:
            import sys as _sys
            print(f"[safe_fetch] FLAGGED — {len(findings)} injection pattern(s) detected:", file=_sys.stderr)
            for match, label in findings:
                print(f"  [{label}] \"{match}\"", file=_sys.stderr)

    return clean


if __name__ == "__main__":
    desk, rest = resolve_desk() if resolve_desk else ("root", sys.argv[1:])
    if not rest:
        print("Usage: python3 safe_fetch.py [--desk <id>] '<URL>'", file=sys.stderr)
        sys.exit(1)

    url = rest[0]
    try:
        result = fetch_and_sanitize(url, desk=desk)
        print(result)
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

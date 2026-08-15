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

Outbound: the Level 2 domain seal lives here (`_enforce_egress_allowlist`). It is OFF unless someone
arms it — the switch is `system/safe-fetch-allowlist.md`, and `--l2-status` says which way it is set.

Testing commands:
    python3 safe_fetch.py 'https://example.com'
    python3 safe_fetch.py 'https://httpbin.org/html'
    python3 safe_fetch.py --l2-status
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


# ── LEVEL 2 — sealing web reads to a list of domains ─────────────────────────────────────────────
# The three levels are written out for a person in docs/OUTSIDE-SERVICES.md. This is the middle one:
# Level 1 is the raw-command hook (enforce_egress_allowlist.sh, on by default, fails OPEN), Level 3
# is the operating system's own firewall (not shipped, the only hard wall). This layer seals the
# ORDINARY web read — what /websearch and every content-reading skill actually go through.
#
# ⛔ IT IS OFF UNTIL SOMEONE TURNS IT ON, AND IT SAYS SO OUT LOUD EVERY TIME. A wall that looks armed
# but is not is worse than no wall: it buys confidence that is not backed by anything. So there is no
# quiet third state here. Every fetch resolves to exactly one of three NAMED outcomes:
#
#   OFF        — nothing armed it. Allowed, and one line on stderr says the seal is not in force.
#   ON         — a list is in force. An off-list host is refused BEFORE the socket opens.
#   AMBIGUOUS  — armed but unusable (switch on with no domains · domains listed with the switch off ·
#                a switch value nobody can read). REFUSED, loudly, naming the line to fix.
#
# The ambiguous case fails CLOSED on purpose, and it is the opposite choice from Level 1, which fails
# OPEN. Level 1 sits in front of every Bash command, so a false positive there stops `git push` and
# somebody unregisters the hook. This sits in front of web reads only, is off unless a person
# deliberately armed it, and the only way to reach the ambiguous state is to have half-configured it
# yourself — where a refusal that names the file and the line is a five-second fix, and a silent
# pass-through is a lie about being protected.
_L2_ENV = "SAFE_FETCH_ALLOWLIST"
_L2_SWITCH_DEFAULT = os.path.join(os.path.dirname(_THIS_DIR), "safe-fetch-allowlist.md")
_L2_ANNOUNCED = False   # the OFF line is printed once per process, not once per fetch


def _l2_switch_path():
    return os.environ.get("SAFE_FETCH_ALLOWLIST_FILE") or _L2_SWITCH_DEFAULT


def _l2_domains(raw):
    """Base domains out of a comma- or newline-separated blob. `#` comments and blanks dropped."""
    out = []
    for d in raw.replace("\n", ",").split(","):
        d = d.strip().lower().strip(".")
        if not d or d.startswith("#"):
            continue
        out.append(d)
    return out


def _l2_read_switch(path):
    """The switch file, read between its markers. Returns (mode, domains, file_present).

    Same marker convention as system/egress-allowlist.md, so the two lists look and parse alike.
    `mode` is whatever text sits between the mode markers, lowercased — NOT normalised to a boolean,
    because a value nobody recognises has to stay distinguishable from a value that says 'off'."""
    mode, doms, block = "", [], None
    try:
        with open(path) as f:
            for line in f:
                s = line.strip()
                if s == "<!-- L2-MODE-START -->":   block = "mode"; continue
                if s == "<!-- L2-MODE-END -->":     block = None;   continue
                if s == "<!-- ALLOWLIST-START -->": block = "list"; continue
                if s == "<!-- ALLOWLIST-END -->":   block = None;   continue
                if not s or s.startswith("#"):
                    continue
                if block == "mode" and not mode:
                    mode = s.lower()
                elif block == "list":
                    doms.extend(_l2_domains(s))
    except OSError:
        return "", [], False
    return mode, doms, True


def l2_state():
    """Resolve Level 2 to one of the three named outcomes. Returns (state, domains, why) where
    state is 'off' or 'on'; the AMBIGUOUS outcome raises RuntimeError rather than returning, because
    there is no answer to give and pretending otherwise is the failure this whole layer is about.

    Precedence: the environment variable is the PER-RUN seal (an orchestrator sealing one run to the
    domains it just searched) and wins; the switch file is the PERSISTENT one a person sets by hand.
    An empty environment variable is treated as 'not set' and falls through to the file."""
    env = os.environ.get(_L2_ENV, "").strip()
    if env:
        doms = _l2_domains(env)
        if not doms:
            raise RuntimeError(
                f"L2-ALLOWLIST AMBIGUOUS: {_L2_ENV} is set to {env!r} but names no usable domain, so "
                "this run is sealed to nothing. REFUSED rather than allowed — an allowlist that "
                f"matches nothing must not read as protection. FIX: set {_L2_ENV} to comma-separated "
                f"base domains (example.com,example.org), or unset it to leave Level 2 off.")
        return "on", doms, f"{_L2_ENV} (this run)"

    path = _l2_switch_path()
    mode, doms, present = _l2_read_switch(path)
    if not present:
        return "off", [], f"no switch file at {path}"
    if not mode:
        raise RuntimeError(
            f"L2-ALLOWLIST AMBIGUOUS: {path} exists but its switch block is missing or unreadable, so "
            "whether web reads are sealed cannot be answered. REFUSED rather than guessed. FIX: the "
            "file needs a line reading `on` or `off` between <!-- L2-MODE-START --> and "
            "<!-- L2-MODE-END -->, or delete the file to leave Level 2 off.")
    if mode == "on":
        if not doms:
            raise RuntimeError(
                f"L2-ALLOWLIST AMBIGUOUS: the switch in {path} says `on` but no domain is listed "
                "between the ALLOWLIST markers, so every web read would be sealed to nothing. "
                "REFUSED rather than allowed. FIX: list the base domains you want reachable, or set "
                "the switch back to `off`.")
        return "on", doms, path
    if mode == "off":
        if doms:
            raise RuntimeError(
                f"L2-ALLOWLIST AMBIGUOUS: {path} lists {len(doms)} domain(s) but its switch still "
                "says `off` — half-configured, which is the one state that looks like protection and "
                "is not. REFUSED rather than allowed. FIX: change the switch line to `on` to arm the "
                "list, or comment the domains out to leave Level 2 genuinely off.")
        return "off", [], f"the switch in {path} says `off`"
    raise RuntimeError(
        f"L2-ALLOWLIST AMBIGUOUS: the switch in {path} reads {mode!r}, which is neither `on` nor "
        "`off`. REFUSED rather than interpreted. FIX: make that line read exactly `on` or `off`.")


def _l2_announce_off(why):
    """Say, once per process, that the seal is not in force. This is the honesty half of the design:
    the person is told the level they are actually at, rather than assuming a wall is there."""
    global _L2_ANNOUNCED
    if _L2_ANNOUNCED:
        return
    _L2_ANNOUNCED = True
    sys.stderr.write(
        "[safe_fetch] L2-ALLOWLIST OFF — this read is NOT sealed to a domain list (" + why + "). "
        "Level 1 (the raw-command hook) and any OS firewall you run still apply; this middle level "
        "does not. To turn it on, see docs/OUTSIDE-SERVICES.md and system/safe-fetch-allowlist.md.\n")


def _enforce_egress_allowlist(url):
    """The egress wall in front of a fetch (reader-actor build 2026-07-02; Level 2 armed 2026-08-15).

    Two checks, in order. The scheme check is UNCONDITIONAL — a non-http(s) URL (file:, gopher:,
    data:) is SSRF hygiene and has nothing to do with the allowlist. The domain seal then applies
    only when Level 2 is armed; when it is not, the caller is told so rather than left to assume."""
    from urllib.parse import urlparse as _urlparse
    parsed = _urlparse(url)
    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        raise RuntimeError(f"egress blocked: scheme '{scheme}' not allowed (http/https only): {url}")

    state, domains, why = l2_state()
    if state == "off":
        _l2_announce_off(why)
        return
    host = (parsed.hostname or "").lower()
    for d in domains:
        if host == d or host.endswith("." + d):
            return
    raise RuntimeError(
        f"L2-ALLOWLIST REFUSED: host '{host}' is not on the sealed list ({', '.join(domains)}) — "
        f"source: {why}. Nothing was fetched; the socket never opened. FIX: if this host genuinely "
        "belongs, add its base domain to the list; if it does not, that is the seal doing its job.")


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

    # `--l2-status` answers "is the middle level actually on right now?" without fetching anything.
    # A switch nobody can check the position of is how the half-configured state survives.
    if rest and rest[0] == "--l2-status":
        try:
            state, domains, why = l2_state()
        except RuntimeError as e:
            print(f"AMBIGUOUS — every web read is refused until this is fixed.\n{e}", file=sys.stderr)
            sys.exit(2)
        if state == "off":
            print(f"L2 egress allowlist: OFF — web reads are not sealed to a domain list ({why}).")
        else:
            print(f"L2 egress allowlist: ON — sealed to {', '.join(domains)} (source: {why}).")
        sys.exit(0)

    if not rest:
        print("Usage: python3 safe_fetch.py [--desk <id>] '<URL>'   |   safe_fetch.py --l2-status",
              file=sys.stderr)
        sys.exit(1)

    url = rest[0]
    try:
        result = fetch_and_sanitize(url, desk=desk)
        print(result)
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

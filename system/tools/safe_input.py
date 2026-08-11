"""safe_input.py — Heuristic injection detector + L0 sanitizer for pasted external content.

Use this before feeding any externally-sourced content (web search results,
copied text, documents from untrusted sources) into Lifehack context.

Two-layer defense:
  1. L0 sanitization — strips hidden Unicode, HTML entities, control chars
  2. Heuristic scan — flags known prompt injection patterns

Usage:
    python3 safe_input.py /path/to/file.txt
    echo "some text" | python3 safe_input.py -

Output: sanitized text on stdout. Verdict + flags on stderr.
Exit 0 = CLEAN. Exit 1 = FLAGGED (injection patterns found).
"""
import sys
import os
import re
import base64 as _b64
import unicodedata as _ud
from urllib.parse import unquote as _unquote

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)

from sanitize import sanitize, NO_CAP

# ── Evasion defang (gauntlet gaps #3/#5, 2026-06-13) ─────────────────────────
# Homoglyph bypass: a Cyrillic/Greek lookalike ("іgnore" with Cyrillic і) breaks a keyword regex.
# Fold the lookalikes used to spoof Latin letters back to ASCII before matching. NFKC alone does
# NOT cross scripts, so we add a targeted confusables table for the letters injection keywords use.
_CONFUSABLES = str.maketrans({
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x", "у": "y", "к": "k", "м": "m",
    "т": "t", "н": "h", "і": "i", "ѕ": "s", "ј": "j", "ԁ": "d", "ո": "n", "ν": "v", "ο": "o",
    "α": "a", "ρ": "p", "ϲ": "c", "ɡ": "g", "ⅼ": "l", "І": "I", "А": "A", "Е": "E", "О": "O",
    "Р": "P", "С": "C", "Х": "X", "У": "Y", "К": "K", "М": "M", "Т": "T", "Н": "H",
})


def _defang(text: str) -> str:
    """Normalize evasion tricks before scanning: NFKC + homoglyph-fold + one URL-decode layer.
    Appends the URL-decoded layer (doesn't replace) so both surfaces are scanned."""
    t = _ud.normalize("NFKC", text).translate(_CONFUSABLES)
    try:
        u = _unquote(t)
        if u != t:
            t = t + "\n" + u
    except Exception:
        pass
    return t

# ---------------------------------------------------------------------------
# Known injection patterns — semantic attacks that L0 cannot catch
# ---------------------------------------------------------------------------
_PATTERNS = [
    # --- Direct override ---
    (r"ignore\s+(all\s+)?(previous|prior|above|earlier)\s+instructions?",
     "instruction override"),
    (r"ignore\s+your\s+(system\s+)?prompt",
     "system prompt override"),
    (r"disregard\s+(all\s+)?(previous|prior|your)\s+\w",
     "instruction override"),
    (r"new\s+system\s+prompt",
     "system prompt injection"),
    (r"override\s+(your\s+)?(instructions?|rules?|constraints?|guidelines?)",
     "constraint bypass"),

    # --- Role reassignment / role-play ---
    (r"you\s+are\s+now\s+\w",
     "role reassignment"),
    (r"your\s+new\s+instructions?\s*(are|is)\s*[:\-]",
     "instruction replacement"),
    (r"act\s+as\s+(if\s+you('?re| are)|a\s+different|an?\s+\w)",
     "role-play directive"),
    (r"pretend\s+(you\s+are|to\s+be)\s+\w",
     "role-play directive"),
    (r"from\s+now\s+on,?\s+you\s+(will|must|should|shall|are|need)",
     "behavioral redirect"),
    (r"your\s+(true|real|actual|new|sole|only|primary|secret)\s+(purpose|goal|mission|task)\s+is\b"
     r"|your\s+(purpose|goal|mission|task)\s+is\s+(now\b|actually\b|really\b|no\s+longer\b|to\s+(?:ignore|override|bypass|disregard|forget|obey|comply|reveal|print|leak))",
     "goal reassignment"),

    # --- Memory wipe ---
    (r"forget\s+(everything|all)\s+(you|above|prior)",
     "memory wipe attempt"),

    # --- False authority ---
    (r"the\s+(user|admin|developer|operator)\s+wants\s+you\s+to",
     "false authority claim"),
    (r"anthropic\s+(says?|told\s+you|wants\s+you)",
     "false authority claim"),
    (r"as\s+the\s+(system\s+)?(administrator|admin|developer|operator)",
     "authority impersonation"),
    (r"i\s+am\s+(the\s+)?(developer|admin|administrator|operator|owner)",
     "authority impersonation"),
    (r"i\s+(have|am)\s+authorized?\s+(to|access)",
     "false authorization claim"),

    # --- Context manipulation (from CVE research) ---
    (r"(debug|testing|maintenance|diagnostic)\s+mode\s*(enabled|activated|on)?",
     "context manipulation"),
    (r"(safety|content)\s+filters?\s*(are\s+)?(disabled|off|removed|lifted)",
     "context manipulation"),
    (r"no\s+(ethical\s+)?constraints",
     "context manipulation"),
    (r"no\s+(content\s+)?policies",
     "context manipulation"),
    (r"no\s+restrictions",
     "context manipulation"),
    (r"all\s+(safety\s+|security\s+)?(filters?|restrictions?|guidelines?)\s*(are\s+)?(disabled|off|removed|lifted)",
     "context manipulation"),

    # --- Virtualization ---
    (r"simulate\s+a\s+(terminal|shell|system|computer|console)",
     "virtualization attempt"),
    (r"(fictional|virtual|imaginary)\s+(os|operating\s+system|computer|terminal)",
     "virtualization attempt"),

    # --- Jailbreak keywords (DAN fix: word boundary) ---
    (r"developer\s+mode\s*(enabled|activated|on)",
     "capability unlock attempt"),
    (r"\bjailbreak\b",
     "jailbreak keyword"),
    (r"\bDAN\b\s*(mode|prompt)",
     "known jailbreak pattern"),
    (r"do\s+anything\s+now",
     "known jailbreak pattern"),

    # --- Coercive ---
    (r"you\s+(must|will|shall)\s+comply",
     "coercive directive"),

    # --- System prompt extraction / leakage ---
    (r"print\s+(your\s+)?(system\s+prompt|instructions|rules)",
     "system prompt extraction"),
    (r"reveal\s+(your\s+)?(system\s+prompt|instructions|guidelines)",
     "system prompt extraction"),
    (r"(show|display|output|give)\s+(me\s+)?(your\s+)?(system\s+prompt|instructions|rules|guidelines)",
     "system prompt extraction"),
    (r"what\s+(are|is)\s+your\s+(system\s+)?(prompt|instructions|rules|guidelines)",
     "system prompt extraction"),
    (r"repeat\s+(everything|the\s+text|all)\s+(above|before|prior)",
     "prompt leakage attempt"),
    (r"translate\s+the\s+(above|previous|prior)",
     "prompt leakage attempt"),

    # --- Bypass language ---
    (r"bypass\s+(the\s+)?(safety|filter|restriction|guardrail|rule|constraint)",
     "bypass attempt"),
    (r"respond\s+(without|freely|with\s+no)\s+(restrictions?|filters?|constraints?|limitations?)",
     "bypass attempt"),
    (r"(sudo|admin|root)\s+(mode|access|privilege)",
     "privilege escalation attempt"),

    # --- Encoding obfuscation ---
    (r"(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{80,}={0,2}(?![A-Za-z0-9+/])",
     "possible base64 obfuscation"),
    (r"(?:[0-9a-fA-F]{2}\s*){20,}",
     "possible hex-encoded payload"),
    (r"(?:%[0-9a-fA-F]{2}){10,}",
     "possible URL-encoded payload"),
    (r"(decode|decipher)\s+this\s+(base64|hex|rot13|encoded)",
     "encoding attack directive"),
]

_COMPILED = [(re.compile(p, re.IGNORECASE), label) for p, label in _PATTERNS]


def scan_for_injection(text: str) -> list:
    """Return list of (match_text, label) for any patterns found.
    Scans the defanged surface (homoglyph-folded + URL-decoded), and additionally decodes any
    base64 blob and re-scans its plaintext — so an encoded payload (gauntlet #5) still surfaces."""
    norm = _defang(text)
    findings = []
    for pattern, label in _COMPILED:
        for m in pattern.finditer(norm):
            findings.append((m.group(0)[:80], label))
    # Targeted base64 decode-and-rescan: only escalates when the DECODED text is itself an injection
    # (so a benign base64 blob stays a plain FLAG, not a false DANGER). Bounded to the first 40 blobs.
    seen = {lab for _, lab in findings}
    for m in list(re.finditer(r"[A-Za-z0-9+/]{16,}={0,2}", norm))[:40]:
        try:
            dec = _b64.b64decode(m.group(0) + "==", validate=False).decode("utf-8", "ignore")
        except Exception:
            continue
        if not dec or not dec.isprintable():
            continue
        for pattern, label in _COMPILED:
            if label not in seen and pattern.search(dec):
                findings.append((dec[:80], label))
                seen.add(label)
    return findings


def process(text: str) -> tuple:
    """Run L0 + heuristic scan. Returns (clean_text, findings)."""
    clean = sanitize(text, max_len=NO_CAP)
    findings = scan_for_injection(clean)
    return clean, findings


def redact_findings(text: str, findings: list) -> str:
    """Replace each flagged span in `text` with a neutral marker — the DETERMINISTIC twin of the
    ingest-reader's span redaction. Used by the safe_* `--redact` mode so a downstream store (e.g. the
    cal-vault) keeps the real content but never the obeyable injection payload. Longest matches first so
    overlapping spans don't leave fragments. `findings` = the (match_text, label) list from process()."""
    out = text
    for match, label in sorted(findings, key=lambda mf: -len(mf[0] or "")):
        if match and match in out:
            out = out.replace(match, f"[REDACTED-FLAGGED: {label}]")
    return out


# ── Uniform Sentinel gate (gauntlet gaps #1/#2, 2026-06-13) ──────────────────
# Every inbound channel (file/calendar/web) calls this so its findings reach the ONE verdict gate
# (sentinel_response.py → ledger + tile + danger pause/notify) — not stderr-only. This is what makes
# the floor UNIFORM. DEFENSIVE: never raises, never blocks the read; a gate failure falls open to the
# scan result so a security tool can never break a normal read.
import json as _json
import subprocess as _sp
_SENTINEL_GATE = os.path.normpath(os.path.join(_THIS_DIR, "..", "..", "shared", "gate", "sentinel_response.py"))


def route_findings(findings: list, source: str, item: str = "") -> str:
    """Route ALREADY-collected findings through the Sentinel verdict gate (sentinel_response.py →
    ledger + tile + danger pause/notify). For channels that already scan and just need the gate-chain.
    Returns CLEAN | FLAG | DANGER. DEFENSIVE: never raises, never blocks the caller's read."""
    if not findings:
        return "CLEAN"
    try:
        payload = _json.dumps([[m, l] for m, l in findings])
        r = _sp.run(["python3", _SENTINEL_GATE, "--source", source, "--item", (item or "")[:120]],
                    input=payload, capture_output=True, text=True, timeout=20)
        return "DANGER" if r.returncode == 2 else "FLAG"
    except Exception as e:                        # fail-open: a gate hiccup never breaks the read
        sys.stderr.write(f"[sentinel-gate] non-fatal ({e}) — scan findings stand, verdict undetermined\n")
        return "FLAG"


def gate(text: str, source: str, item: str = "") -> tuple:
    """Scan `text` AND route findings through the gate in one call (for channels that don't already scan).
    Returns (verdict, findings)."""
    findings = scan_for_injection(text)
    return route_findings(findings, source, item), findings


# ── Window 5: provenance-aware routing for the safe_* wrappers ────────────────────────────────────
# The frozen provenance_tag is sha256(raw_content)[:8] — route_findings has only findings (no raw
# text), so it CANNOT mint the tag. These two helpers let each safe_* wrapper route through the on-path
# ingest_gate (which has the raw text → tag + a coverage breadcrumb on EVERY read, clean included),
# while still defaulting to today's behavior when no desk is given. ingest_gate is lazy-imported to
# avoid a circular import (ingest_gate imports THIS module at load time).
def resolve_desk(argv=None):
    """Resolve the consuming desk_id for provenance: an explicit `--desk <id>` (or `--desk=<id>`) in
    argv wins, else env LIFEHACK_DESK, else 'root'. Returns (desk_id, cleaned_argv) with the --desk
    tokens stripped so the caller's existing positional parsing (url/path/params) is unaffected."""
    argv = list(sys.argv[1:] if argv is None else argv)
    desk, out, i = None, [], 0
    while i < len(argv):
        a = argv[i]
        if a == "--desk" and i + 1 < len(argv):
            desk = argv[i + 1]; i += 2; continue
        if a.startswith("--desk="):
            desk = a.split("=", 1)[1]; i += 1; continue
        out.append(a); i += 1
    return (desk or os.environ.get("LIFEHACK_DESK") or "root"), out


def provenance_route(desk_id: str, source_type: str, raw_text: str, item: str = ""):
    """Route an external read through the on-path ingest gate so it emits a provenance tag + a coverage
    breadcrumb (clean reads included) AND the Sentinel verdict — the Window-5 replacement for a bare
    route_findings call in the safe_* wrappers. Returns the gate dict, or None on failure. DEFENSIVE:
    never raises, never blocks the read (a security tool can never break a normal read)."""
    try:
        _shared = os.path.normpath(os.path.join(_THIS_DIR, "..", "..", "shared", "gate"))
        if _shared not in sys.path:
            sys.path.insert(0, _shared)
        import ingest_gate
        return ingest_gate.gate(desk_id or "root", source_type, raw_text, item=item)
    except Exception as e:
        sys.stderr.write(f"[safe_input] provenance routing skipped ({e}) — read unaffected\n")
        return None


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 safe_input.py <file.txt>  OR  echo text | python3 safe_input.py -",
              file=sys.stderr)
        sys.exit(2)

    path = sys.argv[1]
    if path == "-":
        raw = sys.stdin.read()
    else:
        if not os.path.exists(path):
            print(f"ERROR: file not found: {path}", file=sys.stderr)
            sys.exit(2)
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            raw = f.read()

    clean, findings = process(raw)

    # Clean text always goes to stdout
    print(clean)

    # Verdict goes to stderr so it's separate from the content
    if findings:
        print("\n⚠️  FLAGGED — injection patterns detected:", file=sys.stderr)
        for match, label in findings:
            print(f"  [{label}] \"{match}\"", file=sys.stderr)
        print("\nReview flags before using this content in Lifehack.", file=sys.stderr)
        sys.exit(1)
    else:
        print("\n✓ CLEAN — no injection patterns detected.", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()

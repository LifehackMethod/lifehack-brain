#!/usr/bin/env python3
"""email_convert.py — Generalized Gmail thread converter.

Fetches Gmail threads via gws and converts to clean text files.
No desk-specific logic. No extraction schema. Pure plumbing.

Usage:
  python3 email_convert.py --threads ID [ID ...] --out-dir PATH [OPTIONS]
  python3 email_convert.py --query "GMAIL QUERY" --out-dir PATH [OPTIONS]
  python3 email_convert.py --label LABEL_ID --out-dir PATH [OPTIONS]

Options:
  --messages {first,last,both,all,thread}  Which messages to extract (default: both).
                                    'thread' = the faithful de-duplicated whole thread
                                    ({id}_thread.json): every message cleaned (quotes+sigs
                                    stripped), nothing dropped — the Email Service v2 write path.
  --strip                           Strip quoted text from last message
  --min-chars N                     Min non-whitespace chars to keep stripped output (default: 1)
  --limit N                         Cap thread count
  --raw                             Write _raw.json per thread (default: off)

Self-test:  python3 email_convert.py --self-test   (offline; strip_signature + clean_message +
            build_clean_thread on synthetic fixtures incl. a 20-message thread — no Gmail calls)
"""

import json
import base64
import subprocess
import os
import sys
import argparse
import re
import shutil
from html.parser import HTMLParser

# Resolve gws via PATH — the only portable answer across machines/installs (mirrors
# system/tools/planning-vault-pull.py, planning-light-sweep.py, and the other gws-calling tools in this repo).
GWS = shutil.which("gws") or "gws"

# L0 sanitization — strips hidden Unicode, HTML entities, control chars from email bodies
_SANITIZE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "system", "tools")
if _SANITIZE_DIR not in sys.path:
    sys.path.insert(0, _SANITIZE_DIR)
from sanitize import sanitize, NO_CAP  # noqa: E402

# The data root, through the one resolver (shared/brain_root.py) — never a hardcoded personal Drive
# path. NOT-SET degrades to a machine-local cache dir so a fresh install (or a run before the reader
# has chosen a root) still records rather than silently dropping the audit trail on the floor, and
# never guesses at — let alone writes into — anyone's real notes.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_CODE_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", ".."))
_SHARED_DIR = os.path.join(_CODE_ROOT, "shared")
if _SHARED_DIR not in sys.path:
    sys.path.insert(0, _SHARED_DIR)
try:
    from brain_root import resolve_brain_root  # shared/brain_root.py
    _BR_SOURCE, _BR_PATH = resolve_brain_root()
except Exception:
    _BR_PATH = None
_DATA_ROOT = _BR_PATH or os.path.expanduser("~/.cache/lifehack-email-convert")
EMAIL_READ_LOG = os.environ.get(
    "EMAIL_READ_LOG", os.path.join(_DATA_ROOT, "state", "status", "email-reads.jsonl"))

# Heuristic injection scan → route through the ON-PATH ingest gate (shared/gate/ingest_gate.py).
# THE EMAIL-ROUTING HOLE (now closed): a scan that only prints to stderr never reaches the Sentinel
# alarm — email-body injection flags would fire internally and nothing downstream would ever see them.
#   The fix routes findings through shared/gate/ingest_gate.gate() at source_type="email", which
# enforces the LOCKED FLAG-never-DANGER invariant (gate passes --flag-only AND never returns
# passed=False for email). This is COUPLED ON PURPOSE: wiring the alarm WITHOUT the FLAG constraint
# would let a base64 attachment / security-newsletter DANGER → auto-quarantine real Gmail — strictly
# worse than the silent hole. The wire and the constraint ship together; they are never split.
# Graceful: any gate import/route failure falls back to stderr-only — a security tool never breaks a read.
_GATE_DIR = os.path.normpath(os.path.join(_THIS_DIR, "..", "gate"))
if _GATE_DIR not in sys.path:
    sys.path.insert(0, _GATE_DIR)
try:
    from ingest_gate import gate as _ingest_gate

    def _flag_injection(text, context="email"):
        """Route email-body findings through the on-path ingest gate (FLAG-only for email — it can
        never DANGER/quarantine). Returns text unchanged (the caller holds the sanitized body).
        Never raises — falls back to a stderr note on any gate failure."""
        try:
            desk = _reader_id() or "email"   # tag provenance to the consuming app if one identified itself
            _ingest_gate(desk, "email", text, message_id="", item=context)
        except Exception as _e:                       # gate is defensive, but belt-and-suspenders here
            import sys as _sys
            print(f"[{context}] ingest-gate non-fatal: {_e}", file=_sys.stderr)
        return text
except ImportError:
    # Fallback path (gate unimportable): keep the OLD stderr-only behavior so the read still works.
    try:
        from safe_input import scan_for_injection as _scan_injection
    except ImportError:
        _scan_injection = None

    def _flag_injection(text, context="email"):
        if _scan_injection is None:
            return text
        findings = _scan_injection(text)
        if findings:
            import sys as _sys
            print(f"[{context}] FLAGGED — {len(findings)} injection pattern(s) "
                  f"(stderr-only fallback — gate unavailable):", file=_sys.stderr)
            for match, label in findings:
                print(f"  [{label}] \"{match}\"", file=_sys.stderr)
        return text


# ── Reader identity (audit/provenance label only — there is no per-caller gate here) ───────────
# A prior "trusted lane" scheme (a fixed allowlist of consuming apps that could bypass extra checks)
# was RETIRED upstream: the universal SANITIZER — L0 scrub + injection scan + the Sentinel gate,
# forced on every body read by the ingest-gate hook — is the defense, not who is asking. LIFEHACK_DESK
# is optional and does nothing but LABEL the read/provenance-tag for the audit trail below; unset it
# and everything still works, just tagged "email" instead of a caller name.
def _reader_id():
    """The consuming app's self-reported identity (env LIFEHACK_DESK), or None if unset. Purely a
    label for the audit log + gate provenance tag — never a gate, never a permission check."""
    return os.environ.get("LIFEHACK_DESK") or None


def _audit_email_read(thread_id, reader, message_count=None):
    """Append a metadata-only read row (NEVER content) for traceability. Best-effort: writes under
    the resolved data root (or a machine-local cache dir if no root is set yet); must never break
    the read."""
    try:
        from datetime import datetime
        os.makedirs(os.path.dirname(EMAIL_READ_LOG), exist_ok=True)
        row = {"ts": datetime.now().astimezone().isoformat(timespec="seconds"),
               "reader": reader, "thread_id": thread_id, "message_count": message_count}
        with open(EMAIL_READ_LOG, "a") as f:
            f.write(json.dumps(row) + "\n")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Gmail fetch helpers
# ---------------------------------------------------------------------------

def fetch_thread(thread_id):
    """Fetch full thread from Gmail via gws. Returns (data, error)."""
    try:
        result = subprocess.run(
            [GWS, "gmail", "users", "threads", "get",
             "--params", json.dumps({"userId": "me", "id": thread_id, "format": "full"})],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return None, f"fetch_error: gws exit {result.returncode}"
        data = json.loads(result.stdout)
        return data, None
    except subprocess.TimeoutExpired:
        return None, "fetch_error: timeout"
    except json.JSONDecodeError as e:
        return None, f"fetch_error: json_parse {e}"
    except Exception as e:
        return None, f"fetch_error: {e}"


def fetch_thread_ids_by_query(query, limit=None):
    """Fetch thread IDs matching a Gmail query. Returns (ids, error)."""
    params = {"userId": "me", "q": query}
    if limit:
        params["maxResults"] = limit
    try:
        result = subprocess.run(
            [GWS, "gmail", "users", "threads", "list",
             "--params", json.dumps(params)],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return None, f"fetch_error: gws exit {result.returncode}"
        data = json.loads(result.stdout)
        ids = [t["id"] for t in data.get("threads", [])]
        return ids, None
    except Exception as e:
        return None, f"fetch_error: {e}"


def fetch_thread_ids_by_label(label_id, limit=None):
    """Fetch thread IDs for a Gmail label. Returns (ids, error)."""
    params = {"userId": "me", "labelIds": label_id}
    if limit:
        params["maxResults"] = limit
    try:
        result = subprocess.run(
            [GWS, "gmail", "users", "threads", "list",
             "--params", json.dumps(params)],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return None, f"fetch_error: gws exit {result.returncode}"
        data = json.loads(result.stdout)
        ids = [t["id"] for t in data.get("threads", [])]
        return ids, None
    except Exception as e:
        return None, f"fetch_error: {e}"


# ---------------------------------------------------------------------------
# MIME extraction
# ---------------------------------------------------------------------------

def extract_text_parts(payload, depth=0):
    """
    Recursively extract text/plain body parts.
    Returns (list_of_decoded_strings, error_or_None).
    Skips parts with non-empty filename (attachments, inline images).
    """
    if depth > 8:
        return [], "unexpected_mime: nesting depth > 8"

    results = []
    error = None

    if payload.get("filename"):
        return [], None

    mime = payload.get("mimeType", "")
    body = payload.get("body", {})

    if mime == "text/plain" and body.get("data"):
        raw = body["data"]
        try:
            decoded = base64.urlsafe_b64decode(raw + "==").decode("utf-8", errors="replace")
            results.append(decoded)
        except Exception as e:
            error = f"decode_error: {e}"

    for part in payload.get("parts", []):
        sub_results, sub_error = extract_text_parts(part, depth + 1)
        results.extend(sub_results)
        if sub_error and not error:
            error = sub_error

    return results, error


def extract_html_parts(payload, depth=0):
    """
    Recursively extract text/html body parts (raw HTML, not yet stripped).
    Mirrors extract_text_parts. Returns (list_of_html_strings, error_or_None).
    Skips parts with a non-empty filename (attachments, inline images).
    """
    if depth > 8:
        return [], "unexpected_mime: nesting depth > 8"

    results = []
    error = None

    if payload.get("filename"):
        return [], None

    mime = payload.get("mimeType", "")
    body = payload.get("body", {})

    if mime == "text/html" and body.get("data"):
        try:
            decoded = base64.urlsafe_b64decode(body["data"] + "==").decode("utf-8", errors="replace")
            results.append(decoded)
        except Exception as e:
            error = f"decode_error: {e}"

    for part in payload.get("parts", []):
        sub_results, sub_error = extract_html_parts(part, depth + 1)
        results.extend(sub_results)
        if sub_error and not error:
            error = sub_error

    return results, error


# Tags whose CONTENT must never reach the output (script/style/etc. text).
_HTML_SKIP_TAGS = {"script", "style", "head", "title", "noscript"}
# Tags that imply a line break in the extracted text (readability for statements).
_HTML_BLOCK_TAGS = {
    "p", "div", "br", "tr", "li", "ul", "ol", "table", "section", "header",
    "footer", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6",
}


class _HTMLTextExtractor(HTMLParser):
    """
    SECURITY-OWNED: a tolerant stdlib HTML parser that emits PLAIN TEXT only.

    Why a parser, not regex (the original mistake): HTML is not a regular language,
    so regex tag-stripping silently fails on `>` inside attributes, split/mutated
    tags (`<scr<script>ipt>`), malformed/unclosed markup, CDATA, and conditional
    comments — exactly the adversarial markup this barrier must survive (OWASP;
    "you can't parse HTML with regex"). A real parser tokenizes the structure and
    is robust to all of those.

    Security properties:
      • `convert_charrefs=True` decodes HTML entities INLINE during the parse, so
        entity-encoded payloads ("&#73;gnore…", "&lt;script&gt;") surface as plain
        TEXT — visible to the downstream injection scan, and NEVER re-tokenized back
        into live tags. This is the safe decode-DURING-parse ordering (avoids the
        decode-then-strip XSS class, CWE-79/116).
      • <script>/<style>/<head> CONTENT is suppressed via a skip-depth counter —
        HTMLParser otherwise hands script/CSS source to handle_data.
      • HTML comments / conditional comments / declarations are dropped (we don't
        override their handlers), closing the hidden-comment vector.
    Output is plain text and is never re-rendered, so mXSS does not apply. The text
    still flows through sanitize() + _flag_injection() at the call site.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._parts = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in _HTML_SKIP_TAGS:
            self._skip_depth += 1
        elif tag in _HTML_BLOCK_TAGS:
            self._parts.append("\n")

    def handle_startendtag(self, tag, attrs):
        if tag in _HTML_BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag):
        if tag in _HTML_SKIP_TAGS:
            if self._skip_depth > 0:
                self._skip_depth -= 1
        elif tag in _HTML_BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data):
        if self._skip_depth == 0:
            self._parts.append(data)

    def get_text(self):
        return "".join(self._parts)


def html_to_text(raw_html):
    """
    Turn raw email HTML into plain text safe to hand to the SAME L0 sanitize +
    injection scan the text/plain path gets. Uses the stdlib HTML parser
    (_HTMLTextExtractor) — NOT regex — for robustness against adversarial markup.
    Tolerant: returns whatever was collected even if the parser hits bad markup.
    """
    parser = _HTMLTextExtractor()
    try:
        parser.feed(raw_html)
        parser.close()
    except Exception:
        pass  # keep whatever text was collected before the hiccup
    text = parser.get_text()
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_body_texts(payload):
    """
    Body extraction WITH an HTML fallback. Returns (texts, error, source).

    text/plain is ALWAYS preferred — unchanged behavior for existing callers that depend on it.
    Only when NO text/plain body exists do we fall back to text/html → html_to_text() (the sanitize
    + injection scan still happen at the call site). source ∈ {"text/plain", "text/html", None}.
    """
    texts, error = extract_text_parts(payload)
    if texts:
        return texts, error, "text/plain"

    html_parts, html_err = extract_html_parts(payload)
    if html_parts:
        stripped = [s for s in (html_to_text(h) for h in html_parts) if s.strip()]
        if stripped:
            return stripped, html_err, "text/html"
    return [], (error or html_err), None


def extract_attachment_meta(messages):
    """
    Walk the full MIME payload tree of every message and collect attachment
    METADATA ONLY — filename, mimeType, body.size, body.attachmentId,
    message_id.

    Policy: attachment metadata is PERMITTED; downloading attachment bodies is FORBIDDEN. This
    function intentionally does NOT call messages.attachments.get and does NOT decode body.data.

    Returns a list of dicts (one per attachment part found), in message order.
    An attachment part is any payload node whose `filename` field is non-empty.
    Empty list when there are no attachments.
    """
    pointers = []
    for msg in messages:
        msg_id = msg.get("id", "")
        # Iterative stack walk (avoids recursion depth on pathological MIME trees).
        stack = [msg.get("payload", {})]
        while stack:
            part = stack.pop()
            filename = part.get("filename", "")
            if filename:
                body = part.get("body", {})
                pointers.append({
                    "filename":     filename,
                    "mimeType":     part.get("mimeType", ""),
                    "size":         body.get("size"),
                    "attachmentId": body.get("attachmentId"),
                    "message_id":   msg_id,
                })
                # Do NOT descend into an attachment part's sub-parts — there
                # are none in practice, and we never want to touch body data.
                continue
            for sub in part.get("parts", []):
                stack.append(sub)
    return pointers


def get_headers(message):
    """Extract Subject, From, Date, To from a message's headers."""
    headers = {h["name"]: h["value"]
               for h in message.get("payload", {}).get("headers", [])}
    # NO_CAP: sanitize headers WITHOUT the 200-char default cap, so an injection hidden past
    # char 200 in a long Subject/From isn't truncated before the scan (bodies are already NO_CAP).
    return {
        "Subject": sanitize(headers.get("Subject", ""), max_len=NO_CAP),
        "From":    sanitize(headers.get("From", ""), max_len=NO_CAP),
        "Date":    sanitize(headers.get("Date", ""), max_len=NO_CAP),
        "To":      sanitize(headers.get("To", ""), max_len=NO_CAP),
    }


# ---------------------------------------------------------------------------
# Stripping logic
# ---------------------------------------------------------------------------

def strip_quoted_text(body_text):
    """
    Remove quoted reply chains from an email body.
    Returns (stripped_text, boundary_pattern_name).

    Scans lines top-to-bottom. Finds the first quote boundary.
    Returns everything above it, trailing whitespace removed.
    If no boundary found, returns original text and 'none_found'.
    """
    lines = body_text.splitlines()

    # Pattern matchers in priority order
    # Each returns True if this line is a quote boundary
    def is_quote_line(line):
        return line.startswith("> ")

    def is_gmail_wrote_single(line):
        # "On Mon, Jan 12, 2026 at 3:45 PM John Smith <email> wrote:"
        return bool(re.match(r'^On .{10,80} wrote:\s*$', line))

    def is_split_header_start(line):
        # "On Mon, Jan 12..." without "wrote:" on same line
        return bool(re.match(r'^On .{5,200}$', line.strip()))

    def is_outlook_from(line, next_nonempty):
        # "From: Name <email>" followed by a line starting with "Sent:"
        if re.match(r'^From:\s*.+', line):
            if next_nonempty and next_nonempty.startswith("Sent:"):
                return True
        return False

    def is_original_msg(line):
        return bool(re.match(r'^-{4,}\s*[Oo]riginal', line))

    def is_underscore_sep(line):
        return bool(re.match(r'^_{20,}\s*$', line))

    def is_forwarded_block(line):
        return bool(re.match(r'^Begin forwarded', line, re.IGNORECASE))

    def next_nonempty_line(lines, from_idx):
        for i in range(from_idx + 1, min(from_idx + 5, len(lines))):
            if lines[i].strip():
                return lines[i]
        return None

    boundary_idx = None
    pattern_name = "none_found"

    for i, line in enumerate(lines):
        if is_quote_line(line):
            boundary_idx = i
            pattern_name = "quote_lines"
            break

        if is_gmail_wrote_single(line):
            boundary_idx = i
            pattern_name = "gmail_wrote"
            break

        # Split header: "On [date]" with "wrote:" within next 3 lines
        if is_split_header_start(line):
            found_wrote = False
            for j in range(i + 1, min(i + 4, len(lines))):
                if "wrote:" in lines[j]:
                    found_wrote = True
                    break
            if found_wrote:
                boundary_idx = i
                pattern_name = "split_header"
                break

        nonempty_next = next_nonempty_line(lines, i)
        if is_outlook_from(line, nonempty_next):
            boundary_idx = i
            pattern_name = "outlook_block"
            break

        if is_original_msg(line):
            boundary_idx = i
            pattern_name = "original_msg"
            break

        if is_underscore_sep(line):
            boundary_idx = i
            pattern_name = "underscore"
            break

        if is_forwarded_block(line):
            boundary_idx = i
            pattern_name = "forwarded_block"
            break

    if boundary_idx is None:
        return body_text.rstrip(), "none_found"

    kept = lines[:boundary_idx]
    stripped = "\n".join(kept).rstrip()
    return stripped, pattern_name


def strip_message(message, subject="", min_chars=1):
    """
    Strip quoted text from a message body.
    Returns (formatted_text, boundary_pattern, fell_back, stripped_body_chars).
    Falls back to full message if stripped body non-whitespace chars < min_chars.
    """
    h = get_headers(message)
    texts, _, _ = extract_body_texts(message.get("payload", {}))
    full_body = sanitize("\n".join(texts).strip(), max_len=NO_CAP)
    _flag_injection(full_body, "email-strip")

    stripped_body, pattern = strip_quoted_text(full_body)

    # Count non-whitespace chars in body only (not header lines)
    body_nonws = len(re.sub(r'\s', '', stripped_body))

    if body_nonws < min_chars:
        # Fallback to full body
        result_body = full_body
        fell_back = True
        pattern = pattern  # keep detected pattern for debugging
    else:
        result_body = stripped_body
        fell_back = False

    lines = [
        f"Subject: {subject or h['Subject']}",
        f"From: {h['From']}",
        f"Date: {h['Date']}",
        "",
        result_body
    ]
    return "\n".join(lines), pattern, fell_back, body_nonws


# ---------------------------------------------------------------------------
# Signature / disclaimer stripping (mechanical-only, CONSERVATIVE)
# ---------------------------------------------------------------------------
# Signatures + legal disclaimers repeat on every message (= noise) and the redesign wants them
# removed — but the hard constraint is FAITHFUL: never "cut sheet." Signature stripping is
# documented-brittle, so we strip ONLY on high-confidence markers and NEVER on soft sign-offs
# ("Best regards," alone), which could sit mid-content. Better to leave a signature in than to cut
# a real sentence.

# The RFC 3676 signature delimiter: a line that is exactly "--" or "-- " (trailing space).
_SIG_DELIM_RE = re.compile(r'^--\s?$')
# Mobile / client footers (safe — these are never real content).
_MOBILE_SIG_RES = [
    re.compile(r'^\s*Sent from my \w+', re.IGNORECASE),
    re.compile(r'^\s*Sent from my (i[Pp]hone|iPad|Android|BlackBerry|Galaxy)', re.IGNORECASE),
    re.compile(r'^\s*Get Outlook for (iOS|Android)', re.IGNORECASE),
]
# Confidentiality / legal disclaimer block openers (long boilerplate; safe to cut from here).
_DISCLAIMER_RES = [
    re.compile(r'^\s*CONFIDENTIALITY NOTICE', re.IGNORECASE),
    re.compile(r'^\s*DISCLAIMER\s*:?\s*$', re.IGNORECASE),
    re.compile(r'^\s*This (e-?mail|message|email)( and any attachments?)?\b.{0,60}'
               r'(confidential|intended (solely |only )?for|privileged)', re.IGNORECASE),
    re.compile(r'^\s*The information (contained )?in this (e-?mail|message|email)', re.IGNORECASE),
    re.compile(r'^\s*NOTICE:\s+This (e-?mail|message|communication)', re.IGNORECASE),
]


def strip_signature(body_text):
    """Remove a trailing signature / mobile footer / legal disclaimer block.
    Returns (stripped_text, boundary_pattern_name).

    Scans top-to-bottom, finds the EARLIEST high-confidence signature boundary, and cuts
    everything from that line to the end. Conservative by design: only the RFC 3676 "-- "
    delimiter, known mobile footers, and legal-disclaimer openers trigger a cut. If none is
    found, returns the original text and 'none_found' — a faithful no-op."""
    lines = body_text.splitlines()
    boundary_idx = None
    pattern_name = "none_found"

    for i, line in enumerate(lines):
        if _SIG_DELIM_RE.match(line):
            boundary_idx, pattern_name = i, "rfc3676_delim"
            break
        if any(rx.match(line) for rx in _MOBILE_SIG_RES):
            boundary_idx, pattern_name = i, "mobile_footer"
            break
        if any(rx.match(line) for rx in _DISCLAIMER_RES):
            boundary_idx, pattern_name = i, "disclaimer"
            break

    if boundary_idx is None:
        return body_text.rstrip(), "none_found"
    return "\n".join(lines[:boundary_idx]).rstrip(), pattern_name


# ---------------------------------------------------------------------------
# Faithful per-message cleaning + whole-thread assembly
# ---------------------------------------------------------------------------

def _sanitize_preserving_lines(text):
    """L0-sanitize a multi-line body WITHOUT collapsing newlines. sanitize() (system/tools) is a
    field normalizer — it flattens ALL whitespace incl. newlines to single spaces, which would
    destroy the line structure the quote/signature strippers depend on. So we scrub each line
    independently (hidden-unicode + tag removal + intra-line whitespace collapse survive) and
    rejoin with newlines. Faithful = no dropped content; collapsing runs of spaces within a line
    is L0 hygiene, not content loss."""
    return "\n".join(sanitize(line, max_len=NO_CAP) for line in text.splitlines())


def clean_message(message):
    """Clean ONE message for the faithful thread: sanitize → flag injection on the FULL body →
    strip quoted-reply chain → strip signature/disclaimer. MECHANICAL-ONLY (no LLM).

    Returns a dict:
      {message_id, from, date, body,           # the stored, faithful, cleaned fields
       _quote_boundary, _sig_boundary,          # diagnostics (dropped before storage)
       _residual_quote_lines, _body_lines}
    The injection scan runs on the FULL body (quotes included) so a payload hidden in quoted
    text is still flagged even though the quotes are then stripped for storage."""
    h = get_headers(message)
    msg_id = message.get("id", "")
    texts, _, _ = extract_body_texts(message.get("payload", {}))
    full_body = _sanitize_preserving_lines("\n".join(texts).strip())
    _flag_injection(full_body, "email-thread")            # scan BEFORE stripping (see docstring)

    quote_stripped, q_pattern = strip_quoted_text(full_body)
    body, s_pattern = strip_signature(quote_stripped)
    body = body.strip()

    body_lines = body.splitlines()
    residual_quotes = sum(1 for l in body_lines if l.lstrip().startswith(">"))
    return {
        "message_id": msg_id,
        "from": h["From"],
        "date": h["Date"],
        "body": body,
        "_quote_boundary": q_pattern,
        "_sig_boundary": s_pattern,
        "_residual_quote_lines": residual_quotes,
        "_body_lines": len(body_lines),
    }


def build_clean_thread(messages, subject=""):
    """Assemble the FAITHFUL de-duplicated thread from all thread messages, in order.
    Returns (clean_messages, cleanliness):
      clean_messages  — list of {message_id, from, date, body}, ONE per message (nothing dropped)
      cleanliness     — aggregate metric dict incl. residual_quote_ratio (the numeric bar)
    """
    clean_messages = []
    residual_total = 0
    body_lines_total = 0
    quote_hits = 0
    sig_hits = 0
    for msg in messages:
        c = clean_message(msg)
        residual_total += c["_residual_quote_lines"]
        body_lines_total += c["_body_lines"]
        if c["_quote_boundary"] != "none_found":
            quote_hits += 1
        if c["_sig_boundary"] != "none_found":
            sig_hits += 1
        clean_messages.append({
            "message_id": c["message_id"],
            "from": c["from"],
            "date": c["date"],
            "body": c["body"],
        })
    cleanliness = {
        "total_messages": len(messages),
        "messages_with_quote_boundary": quote_hits,
        "messages_with_signature": sig_hits,
        "residual_quote_lines_total": residual_total,
        "total_body_lines": body_lines_total,
        "residual_quote_ratio": round(residual_total / body_lines_total, 4) if body_lines_total else 0.0,
    }
    return clean_messages, cleanliness


# ---------------------------------------------------------------------------
# Format helpers
# ---------------------------------------------------------------------------

def format_full(messages):
    """All messages decoded and concatenated."""
    subject = get_headers(messages[0]).get("Subject", "")
    lines = [f"Subject: {subject}\n"]
    for i, msg in enumerate(messages):
        h = get_headers(msg)
        texts, _, _ = extract_body_texts(msg.get("payload", {}))
        body = sanitize("\n".join(texts).strip(), max_len=NO_CAP)
        _flag_injection(body, "email-full")
        lines.append(f"--- Message {i+1} ---")
        lines.append(f"From: {h['From']}")
        lines.append(f"Date: {h['Date']}")
        lines.append("")
        lines.append(body)
        lines.append("")
    return "\n".join(lines)


def format_single(message, subject=""):
    """One message decoded."""
    h = get_headers(message)
    texts, _, _ = extract_body_texts(message.get("payload", {}))
    body = sanitize("\n".join(texts).strip(), max_len=NO_CAP)
    _flag_injection(body, "email-single")
    return "\n".join([
        f"Subject: {subject or h['Subject']}",
        f"From: {h['From']}",
        f"Date: {h['Date']}",
        "",
        body
    ])


# ---------------------------------------------------------------------------
# Thread processor
# ---------------------------------------------------------------------------

def process_thread(thread_id, args, manifest, skipped):
    data, err = fetch_thread(thread_id)
    if err:
        print(f"  SKIP: {err}")
        skipped.append({"thread_id": thread_id, "reason": err})
        return

    messages = data.get("messages", [])
    if not messages:
        skipped.append({"thread_id": thread_id, "reason": "no_messages"})
        return

    # Body-read audit (metadata-only, never content) — log every thread whose bodies we are about
    # to read, tagged with the reader identity if one is set, for traceability/forensics.
    _audit_email_read(thread_id, _reader_id(), len(messages))

    subject = get_headers(messages[0]).get("Subject", "")
    print(f"  Subject: {subject[:70]}")
    print(f"  Messages: {len(messages)}")

    # Check we can extract text from at least one message
    all_texts = []
    any_error = None
    used_html = False
    for msg in messages:
        texts, err, source = extract_body_texts(msg.get("payload", {}))
        all_texts.extend(texts)
        if source == "text/html":
            used_html = True
        if err and not any_error:
            any_error = err

    if not all_texts:
        reason = any_error or "no_text_plain"
        print(f"  SKIP: {reason}")
        skipped.append({"thread_id": thread_id, "reason": reason})
        return

    if any_error:
        print(f"  WARNING: partial extraction — {any_error}")

    # ── Attachment metadata (pointers only — no body download) ──────────────
    # Policy: metadata PERMITTED, bodies FORBIDDEN. extract_attachment_meta walks the MIME tree
    # and stops at {filename, mimeType, size, attachmentId, message_id} — it never calls
    # messages.attachments.get.
    attachment_pointers = extract_attachment_meta(messages)
    if attachment_pointers:
        print(f"  Attachments: {len(attachment_pointers)}")

    base = os.path.join(args.out_dir, thread_id)
    entry = {
        "subject": subject,
        "message_count": len(messages),
    }
    if used_html:
        # Observability: this thread had no text/plain and was read via the
        # sanitized HTML fallback. Surfaced in the run summary, never silent.
        entry["html_fallback"] = True

    # Surface attachment pointers in the manifest entry.
    # Only added when non-empty so clean threads stay clean.
    if attachment_pointers:
        entry["attachments"] = attachment_pointers

    do_first = args.messages in ("first", "both", "all")
    do_last = args.messages in ("last", "both", "all")
    do_full = args.messages == "all"
    do_thread = args.messages == "thread"

    # --strip with --messages first: warn and skip strip
    if args.strip and not do_last:
        print(f"  WARNING: --strip ignored (--messages {args.messages} produces no last message)")

    if args.raw:
        raw_path = f"{base}_raw.json"
        with open(raw_path, "w") as f:
            json.dump(data, f)

    # Write attachment-pointer sidecar (metadata only, no body bytes).
    # File is omitted for threads with no attachments so the output dir stays clean.
    if attachment_pointers:
        attach_path = f"{base}_attachments.json"
        with open(attach_path, "w") as f:
            json.dump(attachment_pointers, f, indent=2)

    if do_first:
        first_text = format_single(messages[0], subject=subject)
        with open(f"{base}_first.txt", "w") as f:
            f.write(first_text)
        entry["first_chars"] = len(first_text)

    if do_last:
        last_text = format_single(messages[-1], subject=subject)
        with open(f"{base}_last.txt", "w") as f:
            f.write(last_text)
        entry["last_chars"] = len(last_text)

        if args.strip:
            stripped_text, pattern, fell_back, stripped_body_nonws = strip_message(
                messages[-1], subject=subject, min_chars=args.min_chars
            )
            with open(f"{base}_last_stripped.txt", "w") as f:
                f.write(stripped_text)
            entry["last_stripped_chars"] = len(stripped_text)
            entry["last_stripped_body_nonws"] = stripped_body_nonws
            entry["last_fallback"] = fell_back
            entry["strip_boundary_pattern"] = pattern

    if do_full:
        full_text = format_full(messages)
        with open(f"{base}_full.txt", "w") as f:
            f.write(full_text)
        entry["full_chars"] = len(full_text)

    if do_thread:
        # The FAITHFUL de-duplicated thread — every message cleaned (quotes+sig stripped),
        # nothing dropped, attachments as pointers. Written as JSON for a downstream writer to consume.
        clean_messages, cleanliness = build_clean_thread(messages, subject=subject)
        thread_obj = {
            "thread_id":     thread_id,
            "subject":       subject,
            "message_count": len(messages),
            "messages":      clean_messages,     # one per message, chronological, cleaned
            "attachments":   attachment_pointers,
            "cleanliness":   cleanliness,
        }
        with open(f"{base}_thread.json", "w") as f:
            json.dump(thread_obj, f, indent=2)
        entry["thread_messages"] = len(clean_messages)
        entry["residual_quote_ratio"] = cleanliness["residual_quote_ratio"]

    manifest[thread_id] = entry

    # Print summary
    parts = []
    if "first_chars" in entry:
        parts.append(f"first={entry['first_chars']:,}")
    if "last_chars" in entry:
        parts.append(f"last={entry['last_chars']:,}")
    if "last_stripped_chars" in entry:
        fallback_flag = " [FALLBACK]" if entry.get("last_fallback") else ""
        parts.append(f"stripped={entry['last_stripped_chars']:,}{fallback_flag} ({entry['strip_boundary_pattern']})")
    if "thread_messages" in entry:
        parts.append(f"thread={entry['thread_messages']}msgs residual_q={entry['residual_quote_ratio']}")
    if attachment_pointers:
        parts.append(f"attachments={len(attachment_pointers)}")
    print(f"  {' | '.join(parts)}")
    print(f"  OK")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Gmail thread converter — pure plumbing")

    # Input source (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--threads", nargs="+", metavar="ID", help="Explicit thread IDs")
    input_group.add_argument("--query", metavar="QUERY", help="Gmail search query")
    input_group.add_argument("--label", metavar="LABEL_ID", help="Gmail label ID")

    # Required
    parser.add_argument("--out-dir", required=True, metavar="PATH", help="Output directory")

    # Optional
    parser.add_argument("--messages", choices=["first", "last", "both", "all", "thread"],
                        default="both",
                        help="Which messages to extract (default: both). 'thread' = the faithful "
                             "de-duplicated whole thread as {id}_thread.json (quotes+sigs stripped, "
                             "every message kept) — the Email Service v2 write path.")
    parser.add_argument("--strip", action="store_true",
                        help="Strip quoted text from last message")
    parser.add_argument("--min-chars", type=int, default=1, metavar="N",
                        help="Min non-whitespace chars in stripped body before fallback (default: 1)")
    parser.add_argument("--limit", type=int, metavar="N", help="Cap thread count")
    parser.add_argument("--raw", action="store_true",
                        help="Write _raw.json per thread (default: off)")

    args = parser.parse_args()

    # The universal sanitizer (L0 scrub + injection scan + Sentinel gate, forced on every body read
    # by the ingest-gate hook) is THE defense — there is no per-caller restriction on reading email.
    # We still RECORD the self-reported reader identity (or None) for the read audit log.
    reader = _reader_id()

    # Resolve thread IDs
    if args.threads:
        thread_ids = args.threads
        if args.limit:
            thread_ids = thread_ids[:args.limit]
    elif args.query:
        print(f"Fetching thread IDs for query: {args.query}")
        thread_ids, err = fetch_thread_ids_by_query(args.query, limit=args.limit)
        if err:
            print(f"ERROR: {err}", file=sys.stderr)
            sys.exit(1)
        print(f"Found {len(thread_ids)} threads")
    else:
        print(f"Fetching thread IDs for label: {args.label}")
        thread_ids, err = fetch_thread_ids_by_label(args.label, limit=args.limit)
        if err:
            print(f"ERROR: {err}", file=sys.stderr)
            sys.exit(1)
        print(f"Found {len(thread_ids)} threads")

    os.makedirs(args.out_dir, exist_ok=True)

    manifest = {}
    skipped = []

    for tid in thread_ids:
        print(f"\n[{tid}]")
        process_thread(tid, args, manifest, skipped)
        _audit_email_read(tid, reader)  # metadata-only read-log

    # Write manifest and skipped log
    with open(os.path.join(args.out_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    with open(os.path.join(args.out_dir, "skipped.json"), "w") as f:
        json.dump(skipped, f, indent=2)

    print(f"\n{'='*60}")
    print(f"Done. Converted: {len(manifest)}, Skipped: {len(skipped)}")
    fallbacks = sum(1 for e in manifest.values() if e.get("last_fallback"))
    if args.strip and manifest:
        rate = fallbacks / len(manifest) * 100
        print(f"Fallback rate: {fallbacks}/{len(manifest)} ({rate:.0f}%)")
        if rate > 30:
            print(f"WARNING: fallback rate {rate:.0f}% exceeds 30% threshold — architecture review required before proceeding")
    html_fallbacks = sum(1 for e in manifest.values() if e.get("html_fallback"))
    if html_fallbacks:
        print(f"HTML-fallback (no text/plain → sanitized HTML extraction): {html_fallbacks}/{len(manifest)}")
    if skipped:
        print(f"Skipped:")
        for s in skipped:
            print(f"  {s['thread_id']} — {s['reason']}")


# ---------------------------------------------------------------------------
# Offline self-tests (python3 email_convert.py --self-test) — no Gmail calls
# ---------------------------------------------------------------------------

def _mk_msg(msg_id, sender, date, body_text):
    """Build a synthetic text/plain Gmail message dict (mirrors the real payload shape)."""
    data = base64.urlsafe_b64encode(body_text.encode("utf-8")).decode("ascii")
    return {
        "id": msg_id,
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": sender},
                {"name": "Date", "value": date},
                {"name": "Subject", "value": "Test Thread"},
            ],
            "body": {"data": data},
        },
    }


def _run_self_tests():
    import traceback
    passed = failed = 0

    def ok(name):
        nonlocal passed
        passed += 1
        print(f"  PASS  {name}")

    def fail(name, reason):
        nonlocal failed
        failed += 1
        print(f"  FAIL  {name}: {reason}")

    # 1 — strip_signature: RFC 3676 "-- " delimiter
    try:
        out, pat = strip_signature("Hello there.\n-- \nJohn Doe\nCEO, Acme")
        ok("sig:rfc3676 — '-- ' delimiter cut") if (out == "Hello there." and pat == "rfc3676_delim") \
            else fail("sig:rfc3676", f"out={out!r} pat={pat}")
    except Exception as e:
        fail("sig:rfc3676", f"exception: {e}")

    # 2 — strip_signature: mobile footer
    try:
        out, pat = strip_signature("Approved, go ahead.\nSent from my iPhone")
        ok("sig:mobile — 'Sent from my iPhone' cut") if (out == "Approved, go ahead." and pat == "mobile_footer") \
            else fail("sig:mobile", f"out={out!r} pat={pat}")
    except Exception as e:
        fail("sig:mobile", f"exception: {e}")

    # 3 — strip_signature: disclaimer block
    try:
        out, pat = strip_signature("Numbers look right.\nCONFIDENTIALITY NOTICE: This email is intended...")
        ok("sig:disclaimer — confidentiality block cut") if (out == "Numbers look right." and pat == "disclaimer") \
            else fail("sig:disclaimer", f"out={out!r} pat={pat}")
    except Exception as e:
        fail("sig:disclaimer", f"exception: {e}")

    # 4 — strip_signature: no false-positive on a soft sign-off (faithful no-op)
    try:
        body = "Here is the plan.\n\nBest regards,\nRandi"
        out, pat = strip_signature(body)
        ok("sig:conservative — soft 'Best regards' NOT cut (faithful)") \
            if (pat == "none_found" and "Randi" in out) else fail("sig:conservative", f"out={out!r} pat={pat}")
    except Exception as e:
        fail("sig:conservative", f"exception: {e}")

    # 5 — clean_message: quotes AND signature both stripped, unique content kept
    try:
        body = ("Yes, agreed to the $125k.\n\n"
                "-- \nRandi Smith | CEO | Acme\n\n"
                "On Mon, Jan 12, 2026 at 3:45 PM John <j@x.com> wrote:\n"
                "> original proposal text\n> more quoted lines\n")
        c = clean_message(_mk_msg("m1", "Randi <r@x.com>", "2026-07-07", body))
        good = ("$125k" in c["body"] and "original proposal" not in c["body"]
                and "Randi Smith | CEO" not in c["body"] and c["_residual_quote_lines"] == 0)
        ok(f"clean:both — quote+sig stripped, content kept ({c['body']!r})") if good \
            else fail("clean:both", f"body={c['body']!r}")
    except Exception as e:
        fail("clean:both", f"exception: {e}\n{traceback.format_exc()}")

    # 6 — build_clean_thread: 20-message thread, NOTHING dropped, quotes gone, clean ratio
    try:
        msgs = []
        prev_quote = ""
        for i in range(20):
            body = f"Message {i} unique content line.\n\n-- \nSender Signature Block\nTitle\n"
            if prev_quote:
                body += (f"\nOn Mon, Jan {i}, 2026 at 3:45 PM Sender <s@x.com> wrote:\n{prev_quote}\n")
            msgs.append(_mk_msg(f"m{i}", f"Sender{i} <s{i}@x.com>", f"2026-07-{i+1:02d}", body))
            prev_quote = f"> Message {i} unique content line."
        clean, cl = build_clean_thread(msgs, subject="Test Thread")

        if len(clean) != 20:
            fail("thread:nothing-dropped", f"expected 20 messages, got {len(clean)}")
        else:
            ok("thread:nothing-dropped — all 20 messages present (faithful de-dup drops quotes, not msgs)")

        # every cleaned body has its unique content and NO quoted/sig residue
        content_ok = all(f"Message {i} unique content line." in clean[i]["body"] for i in range(20))
        no_quotes = all(">" not in m["body"] for m in clean)
        no_sig = all("Signature Block" not in m["body"] for m in clean)
        if content_ok and no_quotes and no_sig:
            ok("thread:faithful-clean — unique content kept, quotes+sigs gone in every message")
        else:
            fail("thread:faithful-clean",
                 f"content_ok={content_ok} no_quotes={no_quotes} no_sig={no_sig}; sample={clean[19]['body']!r}")

        if cl["residual_quote_ratio"] == 0.0 and cl["total_messages"] == 20:
            ok(f"thread:cleanliness — residual_quote_ratio={cl['residual_quote_ratio']} (numeric bar recorded)")
        else:
            fail("thread:cleanliness", f"cleanliness={cl}")
    except Exception as e:
        fail("thread:*", f"exception: {e}\n{traceback.format_exc()}")

    # 7 — HTML message flows through the faithful path (html→text, then cleaned)
    try:
        html = "<html><body><p>Hi team</p><p>Ship it.</p><script>evil()</script></body></html>"
        m = {"id": "mh", "payload": {"mimeType": "text/html",
             "headers": [{"name": "From", "value": "A <a@x.com>"}, {"name": "Date", "value": "2026-07-08"}],
             "body": {"data": base64.urlsafe_b64encode(html.encode()).decode("ascii")}}}
        c = clean_message(m)
        ok("thread:html — HTML body extracted to text, script content dropped") \
            if ("Ship it." in c["body"] and "evil" not in c["body"]) else fail("thread:html", f"body={c['body']!r}")
    except Exception as e:
        fail("thread:html", f"exception: {e}\n{traceback.format_exc()}")

    print(f"\nemail_convert self-test results: {passed} passed, {failed} failed")
    return passed, failed


if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "system", "tools")))
    from utf8_stdio import force_utf8_stdio
    force_utf8_stdio()
    if "--self-test" in sys.argv:
        p, f = _run_self_tests()
        sys.exit(0 if f == 0 else 1)
    main()

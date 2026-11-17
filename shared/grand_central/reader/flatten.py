"""reader/flatten.py - trim quoted replies and signatures, nothing a person wrote is cut.

MAILROOM ISOLATION EXCEPTION (a ruled copy, P-9): this file is a port, not a shared import, because the mailroom is
air-gapped and runs as its own user: it cannot import the plugin's shared tools, so the V1 logic is copied here and
this copy is the one the mailroom runs. Keep it in step with V1 by hand; the two deliberate differences below are the
only intended divergence.

Runs in the mailroom (code only, no AI). Port of V1's shared/tools/email_convert.py
(strip_quoted_text, strip_signature, build_clean_thread; V1 itself is never edited), with two
deliberate differences, both because plan B1 says "never cut content":
  1. V1 cut EVERYTHING below the first quote marker. When a person answers inline, between
     the quoted lines ("> question" / "my answer" / "> question 2" / "my answer 2"), that
     threw their answers away. Here only the quoted lines and the "On ... wrote:" header are
     dropped; any unquoted line below the first marker is kept.
  2. The RFC 3676 "-- " delimiter only cuts when a short tail follows it (a real signature).
     A long tail after a "--" line is a person's text, so it stays.
SCAN BEFORE STRIPPING: this module never decides safety. The scan (reader/screen.py) always sees
the full message including quotes; flatten only ever sees a message the scan already passed.

Output is the transcript block for one message. The transcript is append-only: a new reply
becomes a new block at the bottom; blocks already written are never touched.
Python 3.9 compatible.
"""
import re
import unicodedata

MAX_SIG_TAIL_LINES = 12

BLOCK_MARK = "=== message "
# A body line that would look like a block marker is escaped, so a stranger cannot forge a
# message boundary inside a transcript (the access point trusts block markers).
_ESCAPE = "\\"


# ---------------------------------------------------------------- hygiene (V1's L0 sanitize, reduced)
# NORMALISE FIRST, SCAN SECOND, STRIP LAST: normalise_body() runs before the scan, so the delivered
# text is exactly a part of the scanned text. It removes only things that hide or break text:
# control characters, zero-width / bidi / tag characters (format category Cf) and lone surrogates.
# ZWNJ (U+200C) and ZWJ (U+200D) are KEPT: Persian and emoji need them. Spaces, tabs and line
# ends are kept as written (nothing a person typed is reshaped); only line SEPARATORS other than
# "\n" (U+2028/2029, NEL, VT, FF, CR) become "\n", because they would split a line unexpectedly.

_KEEP_FORMAT = ("\u200c", "\u200d")
_LINE_BREAKS = ("\r\n", "\r", "\u2028", "\u2029", "\x85", "\x0b", "\x0c", "\x1c", "\x1d", "\x1e")


def _drop_hidden(text):
    out = []
    for ch in text:
        if ch in "\n\t":
            out.append(ch)
            continue
        cat = unicodedata.category(ch)
        if cat == "Cs":
            continue                       # lone surrogate
        if cat == "Cc" or (cat == "Cf" and ch not in _KEEP_FORMAT):
            continue
        out.append(ch)
    return "".join(out)


def normalise_body(text):
    text = text if isinstance(text, str) else str(text)
    for br in _LINE_BREAKS:
        text = text.replace(br, "\n")
    return _drop_hidden(text)


def normalise_line(text):
    """A single-line field (subject, sender, date, label): line breaks and controls become spaces."""
    text = text if isinstance(text, str) else str(text)
    for br in _LINE_BREAKS + ("\n", "\t"):
        text = text.replace(br, " ")
    return re.sub(r" {2,}", " ", _drop_hidden(text)).strip()


sanitize_line = normalise_line     # kept name for older callers
sanitize_body = normalise_body


# ---------------------------------------------------------------- quotes
# When unsure, KEEP. A quote is only cut when it is clearly a quote:
#   - an attribution ("On ... wrote:", one line or wrapped over up to three) followed by '>' lines
#     or by nothing; from there on, '>' lines are dropped and every unquoted line is kept;
#   - an Outlook-style header block (From:, Sent:, and To: or Subject:, in a row) or a
#     "-----Original Message-----" followed by such a block: everything below is the earlier message.
# A lone '>' line, "Begin forwarded message", an underscore rule, or a typed "From:" are NOT cut.

_ATTR_ONE = re.compile(r"^On .{5,200} wrote:\s*$")
_ON_START = re.compile(r"^On .{5,200}$")
_ORIGINAL = re.compile(r"^-{4,}\s*[Oo]riginal [Mm]essage\s*-{0,}\s*$")
_UNDERSCORE = re.compile(r"^_{20,}\s*$")
_HDR = re.compile(r"^(From|Sent|To|Cc|Subject|Date):\s*\S")


def _attribution_at(lines, i):
    """-> index of the last line of an attribution that starts at i, or None."""
    if _ATTR_ONE.match(lines[i].strip()):
        return i
    if _ON_START.match(lines[i].strip()) and "wrote:" not in lines[i]:
        for j in range(i + 1, min(i + 3, len(lines))):
            joined = " ".join(l.strip() for l in lines[i:j + 1])
            if len(joined) <= 300 and joined.rstrip().endswith("wrote:") and joined.startswith("On "):
                return j
    return None


def _quoted_follows(lines, j):
    """After the attribution ending at j: next non-blank line is a '>' line, or nothing follows."""
    for k in range(j + 1, len(lines)):
        if lines[k].strip():
            return lines[k].lstrip().startswith(">")
    return True


def _outlook_header_at(lines, i):
    """True if lines[i:] opens an Outlook header block: From:, Sent:, and To:/Subject: in a row."""
    got = []
    for k in range(i, min(i + 8, len(lines))):
        l = lines[k]
        if not l.strip():
            if got:
                break
            continue
        m = _HDR.match(l)
        if not m:
            break
        got.append(m.group(1))
    return "From" in got and "Sent" in got and ("To" in got or "Subject" in got)


def _boundary(lines):
    """-> (index, pattern) of the first clear quote boundary, or (None, 'none_found')."""
    for i, line in enumerate(lines):
        j = _attribution_at(lines, i)
        if j is not None and _quoted_follows(lines, j):
            return i, "attribution"
        if _ORIGINAL.match(line.strip()) and _outlook_header_at(lines, i + 1):
            return i, "original_msg"
        if line.startswith("From:") and _outlook_header_at(lines, i):
            return i, "outlook_block"
        if _UNDERSCORE.match(line) and _outlook_header_at(lines, i + 1):
            return i, "outlook_block"
    return None, "none_found"


def strip_quoted_text(body_text):
    """-> (text, pattern). See the notes above: unclear cases are kept whole."""
    lines = body_text.split("\n")
    idx, pattern = _boundary(lines)
    if idx is None:
        return body_text.rstrip(), "none_found"
    kept = lines[:idx]
    if pattern in ("original_msg", "outlook_block"):
        return "\n".join(kept).rstrip(), pattern     # the earlier message in full sits below
    end = _attribution_at(lines, idx)
    for line in lines[end + 1:]:
        if line.lstrip().startswith(">"):
            continue
        kept.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).rstrip(), pattern


# ---------------------------------------------------------------- signatures
# Cut only what is clearly boilerplate at the very end, and only when it LOOKS like boilerplate:
# short lines, few of them, no prose.

MAX_SIG_TAIL_LINES = 8
MAX_SIG_WORDS_PER_LINE = 6
MAX_SIG_LINE_CHARS = 80
MAX_DISCLAIMER_LINES = 15
_SIG_DELIM = re.compile(r"^--\s?$")
_MOBILE = re.compile(r"^\s*(Sent from my (iPhone|iPad|Android|BlackBerry|Galaxy|Samsung|Pixel|"
                     r"Windows Phone|mobile|phone)\b.{0,40}|Get Outlook for (iOS|Android).{0,20})\s*$", re.I)
_DISCLAIMER = [
    re.compile(r"^\s*CONFIDENTIALITY NOTICE", re.I),
    re.compile(r"^\s*DISCLAIMER\s*:?\s*$", re.I),
    re.compile(r"^\s*This (e-?mail|message|email)( and any attachments?)?\b.{0,60}"
               r"(confidential|intended (solely |only )?for|privileged)", re.I),
    re.compile(r"^\s*The information (contained )?in this (e-?mail|message|email)", re.I),
    re.compile(r"^\s*NOTICE:\s+This (e-?mail|message|communication)", re.I),
]


def _count_nonblank(lines, start, limit):
    """Non-blank lines from `start`, counting no further than limit+1. Bounded work per call, so a
    message made of thousands of '--' or footer lines stays linear overall."""
    n = 0
    for k in range(start, len(lines)):
        if lines[k].strip():
            n += 1
            if n > limit:
                break
    return n


def _looks_like_signature(lines, start):
    if not 0 < _count_nonblank(lines, start, MAX_SIG_TAIL_LINES) <= MAX_SIG_TAIL_LINES:
        return False
    for k in range(start, len(lines)):
        l = lines[k]
        if not l.strip():
            continue
        if len(l) > MAX_SIG_LINE_CHARS or len(l.split()) > MAX_SIG_WORDS_PER_LINE:
            return False
        if re.match(r"^\s*(P\.?\s?P?\.?\s?S\.?|PS|N\.?B\.?)\b", l, re.I):
            return False
    return True


def strip_signature(body_text):
    """-> (text, pattern). Cuts only: a '-- ' delimiter followed by a short, signature-looking tail;
    a known mobile footer when only a couple of short lines follow; a legal disclaimer that opens
    its own paragraph (blank line before) near the end. Never a soft sign-off. Linear time."""
    lines = body_text.split("\n")
    for i, line in enumerate(lines):
        if _SIG_DELIM.match(line):
            if _looks_like_signature(lines, i + 1):
                return "\n".join(lines[:i]).rstrip(), "rfc3676_delim"
            continue
        if _MOBILE.match(line) and _count_nonblank(lines, i + 1, 2) <= 2:
            return "\n".join(lines[:i]).rstrip(), "mobile_footer"
        if (i == 0 or not lines[i - 1].strip()) and any(rx.match(line) for rx in _DISCLAIMER) \
                and _count_nonblank(lines, i, MAX_DISCLAIMER_LINES) <= MAX_DISCLAIMER_LINES:
            return "\n".join(lines[:i]).rstrip(), "disclaimer"
    return body_text.rstrip(), "none_found"


# ---------------------------------------------------------------- messages and transcript blocks

def clean_message(email):
    """email: the dict reader/fetch.py produces. -> {message_id, from, date, subject, body, ...}
    Sanitize, strip quotes, strip signature. If stripping would leave nothing at all, the full
    sanitized body is kept (a message is never reduced to empty)."""
    full = normalise_body(email.get("body", "") or "")
    q, qp = strip_quoted_text(full)
    s, sp = strip_signature(q)
    body = s.strip()
    fell_back = False
    if not body and full.strip():
        body, fell_back = full.strip(), True
    frm = email.get("from_addr", "")
    if email.get("from_name"):
        frm = "%s <%s>" % (email["from_name"], email.get("from_addr", ""))
    return {"message_id": email["message_id"], "thread_id": email.get("thread_id", ""),
            "from": normalise_line(frm), "date": normalise_line(email.get("date", "")),
            "subject": normalise_line(email.get("subject", "")), "labels": email.get("labels", ""),
            "body": body, "quote_pattern": qp, "signature_pattern": sp, "fell_back": fell_back}


def normalise_email(email):
    """Normalise a fetched email BEFORE it is scanned, so the scan judges exactly the text that can be
    delivered (clean_message normalises again; that is a no-op on already-normalised text)."""
    e = dict(email)
    e["body"] = normalise_body(email.get("body", "") or "")
    for k in ("from_name", "from_addr", "to_addrs", "subject", "date", "labels"):
        e[k] = normalise_line(email.get(k, "") or "")
    return e


def build_clean_thread(emails):
    """V1's build_clean_thread: one clean message per input message, in order, nothing dropped."""
    return [clean_message(e) for e in emails]


def _escape_body(body):
    out = []
    for line in body.split("\n"):
        if line.lstrip().startswith(BLOCK_MARK.strip()) or line.startswith(_ESCAPE + BLOCK_MARK.strip()):
            line = _ESCAPE + line
        out.append(line)
    return "\n".join(out)


PARTIAL_NOTE = "[not yet read in full: only the first part of this message was scanned and is shown]"


def render_block(clean, label="", partial=False):
    """The text of one message as it appears at the bottom of a thread transcript."""
    head = "%s%s | %s | from: %s | label: %s ===" % (
        BLOCK_MARK, clean["message_id"], clean["date"] or "no date", clean["from"] or "unknown",
        normalise_line(label) or "-")
    body = _escape_body(clean["body"])
    if partial:
        body = body + "\n" + PARTIAL_NOTE
    return head + "\n" + body + "\n\n"


def render_header(thread_id, subject):
    return "# thread %s | subject: %s\n\n" % (thread_id, normalise_line(subject or ""))

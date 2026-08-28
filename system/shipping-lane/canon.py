#!/usr/bin/env python3
"""canon.py — text canonicalisation for the shipping lane's identity/secret scan.
[Shipping Lane · hardening pass, 2026-08-05]

WHY THIS EXISTS: an adversarial audit on 2026-08-05 got 17 of 17 bypasses against
`scrub.py` / `push_gate.py`. Root cause: the engine (`forbidden_content.py`, unmodified
here — see system/parts/README.md rule 1) matches literal contiguous substrings
against RAW text with ZERO canonicalisation. "Wr.en", "W r e n", a Cyrillic-homoglyph
"Wren", a zero-width-joiner-spliced "Wren", an NFD combining-accent form, leetspeak
"Wr3n", a base64/hex/URL-encoded/ROT13'd name or key — none of these are the literal
byte sequence any rule's regex names, so all 17 walked straight through.

⭐⭐ THE GOVERNING CONSTRAINT — non-negotiable: CANONICALISATION MAY ONLY *ADD* HITS,
NEVER REMOVE ONE. Every function here is used ADDITIVELY by its callers: the RAW text is
always scanned exactly as before (unchanged code path, unchanged behaviour), and this
module's transformed views are scanned *in addition*, on top. A hit in either the raw
pass or a transformed pass is a hit. Nothing in this file ever substitutes for the raw
scan or narrows what it catches — it only offers additional views of the same text so a
rule that already matches raw text keeps matching, and a rule that only matches after
de-obfuscation now ALSO fires. See `--selftest` for the additive-union proof.

WHAT THIS MODULE DOES NOT DO: it does not decide anything (no verdicts, no exit codes).
It hands back transformed text plus (where needed) a best-effort map back to the
ORIGINAL file's line numbers, so a caller can report a USEFUL location — never a
canonical-text offset dressed up as if it were an original one.

THE PIPELINE (`canonicalize_with_offsets`), each stage independently provable:
  1. zero-width / BOM strip  — ZWSP U+200B, ZWJ U+200D, ZWNJ U+200C, soft hyphen
     U+00AD, BOM/ZWNBSP U+FEFF, word-joiner U+2060. These are invisible on screen and
     splice a word in half for any literal-match engine while reading as one word to a
     human ("Wren" with a ZWJ dropped between every letter looks identical, matches
     nothing).
  2. NFKD decompose + strip Mn, per character — ONE pass does both jobs the spec asks
     for separately: compatibility decomposition (kills fullwidth forms — "Ｗｒｅｎ"
     folds to "Wren") AND canonical decomposition of accented letters into base +
     combining mark, with the mark then dropped (category "Mn") so "Wrén" folds to
     "Wren"). Two passes (NFKC then NFD) would do the same job slower; NFKD alone
     already performs both decompositions.
  3. homoglyph fold — visually-confusable Cyrillic/Greek letters mapped to the Latin
     letter they impersonate, using the same pairs Unicode's own confusables table
     documents (е.g. Cyrillic "и" → "u", not "i" — that surprised the author; it is the
     documented confusable, not the visual guess).
  4. small-caps fold (added 2026-08-05, second pass) — the Phonetic Extensions /
     Latin Extended-D "LATIN LETTER SMALL CAPITAL x" codepoints (U+1D00-U+1D7F and
     U+A730+), used by "smallcaps text" generators to render e.g. "ᴡʀᴇɴ ᴏᴀᴋʟᴇʏ". NFKD
     (step 2) does not decompose these -- they are not compatibility variants of the
     base letter as far as Unicode is concerned, they are their own distinct letters
     that merely LOOK like small capitals -- so this is a second manual char->char
     table, mechanically identical in shape to the homoglyph fold above, just a
     different set of confusables.
  5. leetspeak fold — 3→e, 0→o, 4→a, 1→l, 5→s (identity-relevant digits only; other
     digits are left alone on purpose — folding every digit in every file would erase
     real numbers for no security benefit).
  6. intra-word separator collapse — a SINGLE separator character (punctuation or
     whitespace, including one bare newline) sitting between two word characters is
     removed, so "Wr.en", "Oak-ley", "W r e n", and "Wr\\nen" all canonicalise to
     the plain run. A RUN of 2+ separator characters (a blank-line paragraph break, a
     double space, ". " sentence-ending punctuation) is left completely untouched — the
     collapse only fires on an exactly-one-character gap. This is deliberate and is
     exactly why "draw.rendered" is a safe test rather than a landmine: collapsing its
     single dot produces "drawrendered", which DOES contain the substring "wren" — but
     every existing refuse rule anchors on `\\b`, and inside "drawrendered" there is no
     word boundary at that position (both neighbours are plain letters), so nothing
     fires. The safety net is the RULES' `\\b` anchors, not this module — canon.py's job
     is only to stop separators from being a hiding place, never to avoid producing
     substrings that a properly-anchored rule can already ignore.

ADDITIONAL TRANSFORMS (not part of the canonical pipeline above, offered separately
because they are not "normalisation" — they are alternate ENCODINGS of the same bytes):
  - `rot13(text)` — a fixed, involutive letter rotation. No shape distinguishes ROT13'd
    text from any other prose, so the only reliable test is to rotate the WHOLE text and
    scan the result like a second canonical view (`transformed_only_hits`).
  - `scan_encoded_payloads(text, refuse_rules)` — finds base64 / hex / percent-encoded
    (URL) candidate spans, decodes them, and re-runs the REFUSE rules against the
    DECODED bytes-as-text. A decoded hit is reported with the encoding named. It also
    flags high-Shannon-entropy blobs (len >= 32, entropy >= 4.5 bits/char) as a
    DISTINCT "unknown-format-secret" finding — no literal rule can ever anticipate a
    format nobody has written a rule for yet. Threshold rationale in the function
    docstring below.

REPORTING CONTRACT: every hit-producing function in this module returns the ORIGINAL
file's line number and the ORIGINAL evidence text (via the offset map for the
character-shuffling canonical pipeline; via identity offsets for the 1:1 ROT13
transform). A hit found only in a transformed view is marked so a human can see WHY it
fired (`"canonical_only": True`, plus the transformed evidence alongside the original).

SECOND HARDENING PASS (2026-08-05, same day, second red-team): five more cheap
character-level holes, closed the same additive way as everything above --

  - BIDI CONTROLS (`scan_bidi_controls`) — U+202A-U+202E and U+2066-U+2069 BANNED
    OUTRIGHT by mere presence. Text stored reversed inside a bidi override renders as
    the forward name in GitHub/VS Code/most terminals with no decoding at all (the
    Trojan Source class). No legitimate shipped file needs one, so this is a presence
    check, never an attempt to interpret direction.
  - UNICODE TAG BLOCK (`scan_tag_chars`) — U+E0000-U+E007F BANNED OUTRIGHT, same
    reasoning: fully invisible, and capable of carrying an entire hidden name recovered
    verbatim by a decoder that knows the (deprecated, but still valid) tag-character
    encoding.
  - SMALL-CAPS FOLD (`SMALL_CAPS_MAP`, folded in `canonicalize_with_offsets` step 4) —
    the Phonetic-Extensions/Latin-Extended-D small-capital letters
    (e.g. "ᴡʀᴇɴ ᴏᴀᴋʟᴇʏ") have NO NFKD decomposition, so step 2 cannot reach them; this
    is a second manual char->char fold, exactly the same shape as the homoglyph fold,
    just a different table.
  - BOUNDED RECURSIVE DECODE (`_decode_chain`, depth cap 3, cycle-guarded) —
    `scan_encoded_payloads` used to unwrap exactly one layer, so a doubly-wrapped
    `base64(base64(name))` decoded to more base64 text, not the name, and sailed
    through. Each candidate blob is now decoded up to 3 layers deep, checking the
    refuse rules against EVERY layer, stopping early if a layer ever repeats a value
    already seen in that chain (the cycle guard -- prevents a pathological
    self-inverse encoding from looping).
  - TWO MORE CODECS: base32 (`_try_decode_base32`) and quoted-printable
    (`_try_decode_quoted_printable`, via stdlib `quopri`) join base64/hex/URL as
    candidate encodings tried at every decode layer.

  All five are ADDITIVE, per the governing constraint above: bidi/tag are presence
  checks that only ever ADD a hit no existing pass could produce; the small-caps fold
  is one more folding stage layered onto the SAME pipeline (inert on any text with no
  small-caps characters in it); the deeper decode layers and two new codecs only widen
  what `scan_encoded_payloads` can additionally find, never narrow it. See
  `--selftest` for the fixtures proving each one catches its target and leaves the
  clean fixture at zero hits.

THIRD HARDENING PASS (2026-08-05, same day, third red-team) — two confirmed bypasses:

  - THE UNDERSCORE (fixed in `refuse-rules.json`, not here): every identity-ish rule
    anchored on `\\b`, and Python's `\\b` counts `_` as a word character, so
    "wren_oakley" -- an entirely ordinary filename/variable/slug/branch shape, no
    attacker required -- has no word boundary on either side of "wren" and the old
    pattern never fired. Fixed by replacing every such `\\b` with an explicit
    `(?<![A-Za-z0-9])...(?![A-Za-z0-9])` boundary that excludes `_` from the word-class
    instead of including it. This is a STRICT SUPERSET of `\\b` for a purely-alphabetic
    literal (it matches everywhere `\\b` matched -- letter/digit neighbours still block
    it exactly as before -- plus additionally at an underscore neighbour), so it can only
    ADD matches, never remove one; `desk-name-cal` keeps its deliberate case-sensitivity
    unchanged, which is what keeps "cal_culate" safe (lowercase "cal" still never matches
    the literal "Cal").
  - ESCAPE SYNTAX NEVER DECODED (`_decode_escapes_with_offsets`, folded into
    `canonicalize_with_offsets` as its FIRST stage) -- canon.py decoded byte-level
    CODECS (base64/hex/base32/url/quoted-printable/rot13) but not the ordinary escape
    SYNTAX every JS engine, JSON parser and browser decodes natively: `\\uXXXX`,
    `\\u{XXXX}`, `\\xNN`, a 1-3 digit octal escape `\\NNN`, and HTML numeric (`&#NN;` /
    `&#xNN;`) or named (`&amp;`) entities -- exactly the file types (`.js`, `.json`,
    `.svg`, `.html`) a real repo ships. Decoding runs BEFORE the rest of the
    canonicalisation pipeline (zero-width strip, NFKD, homoglyph/small-caps/leet folds,
    separator collapse), so an escaped name is folded down to plain text and then
    scanned by every later stage exactly like any other obfuscation -- one pipeline,
    additive on top of the unchanged raw pass, per the governing constraint. HTML entity
    decoding is delegated to the stdlib `html.unescape` (the authoritative name table --
    a look-alike like "&D;" that is not a real entity is left untouched, never guessed
    at) applied per-candidate-span so an original line number is still recoverable.
  - CANDIDATE FLOOR LOWERED 16 -> 8 (`_CANDIDATE_LEN`, shared by the base64/hex/base32
    candidate regexes): `base64("Oakley")` is exactly 8 characters (6 raw bytes, evenly
    divisible by 3, no padding) and was never even attempted at the old floor. COST:
    every 8-15 character alphanumeric run in a scanned file is now a decode candidate
    (previously only 16+ character runs were) -- strictly more decode attempts per file,
    still linear-time (no new regex backtracking risk, only a smaller minimum count on
    the same fixed-shape pattern). This is CPU cost only, not a false-positive risk: a
    candidate that fails to decode (wrong alphabet/padding/not valid UTF-8) is silently
    dropped, and even a candidate that DOES decode must ALSO match one of the 28 refuse
    patterns to produce a finding -- an 8-character coincidence doing both is
    astronomically unlikely on ordinary short identifiers ("variable", "iterator") the
    same way the original 16-char rationale already argued for longer ones.

FOURTH PASS (2026-08-15) — SHAPE heuristics, WARNING-tier, NEVER BLOCKING. Everything
above this point hunts a STRING (a name, a key format, a path) or a PRESENCE (a banned
codepoint). Both need somebody to have written the string down first, and on the donor
lane nine separate hand sweeps still missed a real third-party name because they grepped
one spelling and the file used another — a name list can never enumerate a family member,
a named client, a collaborator, or a business contact nobody wrote a rule for.
`scan_third_party_name_shape` and `scan_disclosing_fact_patterns` hunt a SHAPE instead: a
capitalised, name-shaped token adjacent to a relationship/business trigger word (wife,
husband, client, coach, student, partner, tenant, invoice, collaborator), and a small set
of FACT patterns (property ownership, a joint account, an exact pay split, a medical
detail, a dated personal life event) that identify even with every name stripped out —
*"he owns two homes and holds joint bank accounts"* identifies without a single hunted
string in it.

⚠ CALIBRATION, MEASURED NOT ASSUMED (donor figures, 2026-08-15). An early proximity-window
version of the name-shape heuristic returned 353 raw hits over a ~230-file real-content
corpus — a check that drowns a reviewer gets switched off, which is worse than not having
one. Replacing the wide character-window proximity test with two TIGHT, high-precision
grammatical shapes ("NAME's <trigger>" and "<trigger> NAME") plus a small stopword table
cut that to 27 hits, EVERY one a genuine third-party name confirmed by hand — 100%
precision, including the exact name the nine hand sweeps had missed. A full-repo sweep
returned 32 hits, all genuine. `scan_disclosing_fact_patterns` was calibrated the same
way: an unconstrained "dated personal event" pattern matched ordinary changelog prose
("moved 2026-08-06") and was tightened to specific life-event verbs with a non-ISO-date
lookahead; a bare `owns?` matched the idiom "his own home" and was tightened to the verb
form `owns`/`co-owns` only. See `--selftest` for the planted-fixture proof; the
calibration sweep itself is not re-run by `--selftest` because it depends on live repo
content that changes, not a fixed fixture.

BOTH scans are WARNING-tier by design and are NEVER added to `refuse-rules.json` — a
literal-rule hit there is authoritative and blocking (verified by `verify_rules.py`'s own
"no dead rule" check, which would force every hit here to also be a hard block). A SHAPE
match can be a false positive in a way a literal secret or the operator's own listed name
can not, so a hit here is reported for a human to glance at and clear, and NEVER sets a
file's mechanical status to NOT-CLEAN, NEVER changes an exit code, and NEVER blocks a push.

⭐ AND THE STOPWORD TABLE CARRIES NO PERSON IN IT. The donor's table hard-coded its own
author's first name, family name and the names of his six desk personas, so the heuristic
would not double-report what his literal rules already caught. That is a personal literal
in a committed file, which is the one thing this repo does not do (see `identity_rules.py`).
`NAME_SHAPE_STOPWORDS` below therefore holds ONLY generic English/doctrine words, and the
"never double-report what a literal rule already catches" property is obtained the exact
way it should have been in the first place: the CALLER passes `extra_stopwords`, and
`scrub.py` fills it from the LIVE effective refuse rules — every token the personal tier
would already block is dropped from the warning list at run time. Strictly better than the
donor: it needs no maintenance, it adapts to whoever is running the lane, and it stays
correct when somebody edits their identity file.

Pure stdlib. Python 3.9 target — no bare `X | None` annotations.
"""

from __future__ import annotations

import base64
import binascii
import codecs
import hashlib
import html
import json
import math
import os
import quopri
import re
import stat
import string
import unicodedata
from collections import Counter

# --------------------------------------------------------------------- zero-width / BOM

ZERO_WIDTH_CHARS = frozenset([
    "​",  # ZERO WIDTH SPACE
    "‌",  # ZERO WIDTH NON-JOINER
    "‍",  # ZERO WIDTH JOINER
    "­",  # SOFT HYPHEN
    "﻿",  # ZERO WIDTH NO-BREAK SPACE / BOM
    "⁠",  # WORD JOINER
])

# ------------------------------------------------------------------------- homoglyphs
# Cyrillic/Greek -> Latin, taken from Unicode's own confusables mapping (not a visual
# guess -- е.g. Cyrillic "и" (U+0438) is confusable with Latin "u", not "i").
HOMOGLYPH_MAP = {
    # Cyrillic lowercase
    "а": "a", "е": "e", "о": "o", "р": "p",
    "с": "c", "х": "x", "у": "y", "и": "u",
    # Cyrillic uppercase
    "А": "A", "Е": "E", "О": "O", "Р": "P",
    "С": "C", "Х": "X", "У": "Y", "И": "U",
    # Greek lowercase
    "α": "a", "ε": "e", "ο": "o", "ρ": "p", "ς": "s",
    # Greek uppercase
    "Α": "A", "Ε": "E", "Ο": "O", "Ρ": "P",
}

# ------------------------------------------------------------------------- small caps
# "LATIN LETTER SMALL CAPITAL x" -- Phonetic Extensions (U+1D00-U+1D7F) plus a handful
# from IPA Extensions and Latin Extended-D that "smallcaps text" generators use for the
# same visual effect (е.g. "ᴡʀᴇɴ ᴏᴀᴋʟᴇʏ"). No NFKD decomposition exists for these -- each
# is its own distinct Unicode letter, not a compatibility variant -- so step 2 above
# cannot reach them; this manual table is the only way in. Not every Latin letter has a
# dedicated small-capital codepoint (there is no standard one for 'q' in wide use, none
# at all for 'x' -- generators fall back to the plain letter), so this table maps every
# letter that DOES have one and leaves the rest alone; that is a complete table, not a
# partial one -- there is nothing missing from it for the letters it does not cover.
SMALL_CAPS_MAP = {
    "ᴀ": "a", "ʙ": "b", "ᴄ": "c", "ᴅ": "d", "ᴇ": "e", "ꜰ": "f",
    "ɢ": "g", "ʜ": "h", "ɪ": "i", "ᴊ": "j", "ᴋ": "k", "ʟ": "l",
    "ᴍ": "m", "ɴ": "n", "ᴏ": "o", "ᴘ": "p", "ꞯ": "q", "ʀ": "r",
    "ꜱ": "s", "ᴛ": "t", "ᴜ": "u", "ᴠ": "v", "ᴡ": "w", "ʏ": "y",
    "ᴢ": "z",
}

# --------------------------------------------------------------------------- leetspeak
LEET_MAP = {"3": "e", "0": "o", "4": "a", "1": "l", "5": "s"}

# ------------------------------------------------------------------- bidi / tag bans
# Presence-only bans (never interpreted, never folded) -- see the module docstring's
# SECOND HARDENING PASS section for why these are outright bans rather than folds.
BIDI_CONTROL_CHARS = frozenset(
    chr(c) for c in list(range(0x202A, 0x202F)) + list(range(0x2066, 0x206A)))

TAG_BLOCK_LO, TAG_BLOCK_HI = 0xE0000, 0xE007F

# ------------------------------------------------------------------------- separators
WORD_CHARS = frozenset(string.ascii_letters + string.digits)
SEP_CHARS = frozenset(" \t\r\n" + ".,-_/\\:;!?*+~^|<>=@#$%&'\"`()[]{}")


def _is_word(ch):
    return ch in WORD_CHARS


# ------------------------------------------------------- escape / entity decode (Fix 2b)
# THIRD HARDENING PASS, 2026-08-05 -- see module docstring. Ordinary escape SYNTAX (not a
# byte-level codec like base64/hex -- those are handled by scan_encoded_payloads below),
# decoded so the folded-down plain text feeds the rest of canonicalize_with_offsets.
#
# `\\u{XXXX}` (JS ES6 code-point escape) is listed before `\\uXXXX` only for readability;
# the two forms cannot collide (`\\uXXXX` requires 4 hex digits immediately after `u`,
# and the character right after `u` in `\\u{...}` is `{`, never a hex digit or itself
# consumable by the 4-digit form, so there is no order-dependent ambiguity).
_ESCAPE_TOKEN_RE = re.compile(
    r'\\u\{[0-9A-Fa-f]{1,6}\}'      # \u{XXXX}  -- JS ES6 code-point escape
    r'|\\u[0-9A-Fa-f]{4}'           # \uXXXX    -- JS/JSON/Python unicode escape
    r'|\\x[0-9A-Fa-f]{2}'           # \xNN      -- JS/Python hex byte escape
    r'|\\[0-7]{1,3}'                # \NNN      -- 1-3 digit octal escape
    r'|&#[0-9]{1,7};'               # &#NN;     -- HTML/XML decimal numeric entity
    r'|&#[xX][0-9A-Fa-f]{1,6};'     # &#xNN;    -- HTML/XML hex numeric entity
    r'|&[A-Za-z][A-Za-z0-9]{1,31};' # &amp;     -- HTML named entity (bounded length)
)


def _decode_one_escape(tok):
    """Decode a single escape/entity token to the character(s) it represents, or None
    if it is not actually valid (caller then keeps the literal source text unchanged --
    this function never guesses, it only decodes what the syntax unambiguously means)."""
    try:
        if tok.startswith("\\u{"):
            return chr(int(tok[3:-1], 16))
        if tok.startswith("\\u"):
            return chr(int(tok[2:], 16))
        if tok.startswith("\\x"):
            return chr(int(tok[2:], 16))
        if tok.startswith("\\"):
            return chr(int(tok[1:], 8))
        if tok.startswith("&"):
            decoded = html.unescape(tok)
            # html.unescape leaves an UNRECOGNISED entity (e.g. "&D;", not a real HTML
            # entity) byte-for-byte unchanged -- that is the signal it did NOT decode,
            # never a guess at what it might have meant.
            return decoded if decoded != tok else None
    except (ValueError, OverflowError):
        return None
    return None


def _decode_escapes_with_offsets(text):
    """Decode every `\\uXXXX` / `\\u{XXXX}` / `\\xNN` / octal escape and every HTML
    numeric/named entity in `text`, returning (decoded_text, offsets) with the same
    offset-map contract as `canonicalize_with_offsets`: offsets[i] is the index into the
    ORIGINAL text that decoded_text[i] traces back to (an escape token that decodes to
    one or more characters maps every output character to the token's START offset --
    the same "expansion maps back to one source index" convention NFKD already uses).
    A token that fails to decode (invalid, or not a real HTML entity) is copied through
    literally, unchanged, at its own per-character offsets -- ADDITIVE ONLY: this never
    removes a byte the raw scan would have seen, it only offers a second, decoded view
    on top, exactly like every other transform in this module."""
    out_chars = []
    out_offsets = []
    pos = 0
    for m in _ESCAPE_TOKEN_RE.finditer(text):
        start, end = m.span()
        if start < pos:
            continue  # defensive: regex alternatives cannot overlap, but never double-consume
        for j in range(pos, start):
            out_chars.append(text[j])
            out_offsets.append(j)
        decoded = _decode_one_escape(m.group(0))
        if decoded is None:
            for j in range(start, end):
                out_chars.append(text[j])
                out_offsets.append(j)
        else:
            for ch in decoded:
                out_chars.append(ch)
                out_offsets.append(start)
        pos = end
    for j in range(pos, len(text)):
        out_chars.append(text[j])
        out_offsets.append(j)
    return "".join(out_chars), out_offsets


# --------------------------------------------------------------------- the pipeline

def _strip_zero_width(chars):
    return [(ch, off) for ch, off in chars if ch not in ZERO_WIDTH_CHARS]


def _nfkd_strip_marks(chars):
    out = []
    for ch, off in chars:
        for c2 in unicodedata.normalize("NFKD", ch):
            if unicodedata.category(c2) == "Mn":
                continue
            out.append((c2, off))
    return out


def _fold_map(chars, mapping):
    """Generic char->char fold, offset-preserving -- the homoglyph, small-caps, and
    leetspeak folds are all this same shape over a different table."""
    return [(mapping.get(ch, ch), off) for ch, off in chars]


def _fold_homoglyphs(chars):
    return _fold_map(chars, HOMOGLYPH_MAP)


def _fold_small_caps(chars):
    return _fold_map(chars, SMALL_CAPS_MAP)


def _fold_leet(chars):
    return _fold_map(chars, LEET_MAP)


def _isolated_single(chars, j):
    """True if chars[j] is a word char that is NOT part of a longer word-char run --
    i.e. it is a lone letter/digit, both immediate neighbours non-word (or an edge)."""
    if not (0 <= j < len(chars)) or not _is_word(chars[j][0]):
        return False
    left_word = j > 0 and _is_word(chars[j - 1][0])
    right_word = j < len(chars) - 1 and _is_word(chars[j + 1][0])
    return not left_word and not right_word


def _fold_crlf(chars):
    """Drop the CR of a CRLF pair, so a Windows line break is ONE separator, not two.

    WHY THIS EXISTS (found 2026-08-28 on Windows). _collapse_separators below drops a
    SINGLE separator sitting between two word characters -- that is what turns a name
    split by a newline back into one word, and its docstring says "a single newline" on
    purpose. A CRLF is ONE line break spelled with TWO characters, so neither half ever
    qualified: the CR sees a LF on its right (not a word char) and the LF sees a CR on
    its left. The pair survived and the name stayed split.

    MEASURED, and it is a REAL BYPASS OF THE LAST GATE, not a cosmetic difference. With
    a name split across a line break, the LF spelling canonicalised back to the joined
    name and was caught; the CRLF spelling came back unchanged and was MISSED. Every
    file an editor writes on Windows uses CRLF, so on that platform a personal name
    split across a line break walked straight through push_gate. Invisible on
    macOS/Linux, live on Windows -- the same platform asymmetry that hid the pm-hook
    absolute-path and stat bugs found the same day.

    ONLY a CR immediately followed by LF is dropped. A lone CR (classic-Mac line ending)
    is left where it is and still collapses on its own merits under the single-separator
    rule; widening this to "drop every CR" would change what counts as a separator, which
    is not what the bug needs.

    Runs BEFORE _collapse_separators, not inside it: that function decides every drop in
    one pass over the ORIGINAL neighbours, so a CR marked dropped there would still be
    seen as the LF left-hand neighbour and the LF would not collapse. Two passes is what
    makes the pair behave as the single separator it already is. Offsets are untouched --
    each surviving char keeps its own source index, as everywhere else in this pipeline.
    """
    n = len(chars)
    keep = []
    for i in range(n):
        if chars[i][0] == "\r" and i + 1 < n and chars[i + 1][0] == "\n":
            continue
        keep.append(chars[i])
    return keep


def _collapse_separators(chars):
    """Drop a SINGLE separator character sitting between two word characters.

    Plain space/tab is a special case: it only collapses when BOTH flanking word
    characters are ISOLATED SINGLES (e.g. "W r e n") -- a plain space between two
    ordinary multi-character words ("Wren reviews...") is never collapsed, because
    doing so would erase the \\b boundary a rule needs on content that already matches
    the RAW text just fine (collapsing it there would only ever cost information, never
    add any). Every other separator (., -, _, /, a single newline, ...) collapses
    unconditionally when flanked by word characters, exactly as "draw.rendered" and
    "Wr\\nen" require -- the `\\b` anchors in the rules are what keep that safe."""
    n = len(chars)
    drop = [False] * n
    for i in range(n):
        ch = chars[i][0]
        if ch not in SEP_CHARS:
            continue
        left_ok = i > 0 and _is_word(chars[i - 1][0])
        right_ok = i < n - 1 and _is_word(chars[i + 1][0])
        if not (left_ok and right_ok):
            continue
        if ch in (" ", "\t"):
            if not (_isolated_single(chars, i - 1) and _isolated_single(chars, i + 1)):
                continue
        drop[i] = True
    return [chars[i] for i in range(n) if not drop[i]]


def canonicalize_with_offsets(text):
    """Returns (canonical_text, offsets) where offsets[i] is the index into the
    ORIGINAL `text` that canonical_text[i] traces back to (best-effort — an
    expansion, e.g. a ligature decomposing to two letters, maps both output
    characters to the single source index).

    FIRST STAGE (2026-08-05, third hardening pass): decode ordinary escape SYNTAX
    (`\\uXXXX`, `\\u{XXXX}`, `\\xNN`, octal, HTML numeric/named entities) before
    anything else, so an escaped name is already plain text by the time the
    zero-width/NFKD/homoglyph/leet/separator stages run -- see
    `_decode_escapes_with_offsets` and the module docstring's THIRD HARDENING PASS."""
    decoded_text, base_offsets = _decode_escapes_with_offsets(text)
    chars = [(ch, base_offsets[i]) for i, ch in enumerate(decoded_text)]
    chars = _strip_zero_width(chars)
    chars = _nfkd_strip_marks(chars)
    chars = _fold_homoglyphs(chars)
    chars = _fold_small_caps(chars)
    chars = _fold_leet(chars)
    chars = _fold_crlf(chars)
    chars = _collapse_separators(chars)
    if not chars:
        return "", []
    out_text = "".join(c for c, _ in chars)
    out_offsets = [o for _, o in chars]
    return out_text, out_offsets


def canonicalize(text):
    canon, _ = canonicalize_with_offsets(text)
    return canon


def rot13(text):
    return codecs.encode(text, "rot_13")


# --------------------------------------------------------------------------- reporting

def _line_and_evidence(text, lines, pos):
    line_no = text.count("\n", 0, pos) + 1
    ev = lines[line_no - 1].strip() if 0 <= line_no - 1 < len(lines) else ""
    return line_no, ev[:200]


# ------------------------------------------------------------ bidi / tag presence bans
#
# BOTH of these are PRESENCE detectors, not folds -- unlike everything above, there is
# no "safe" interpretation to decode into and re-scan; the mere existence of the
# character is itself the finding (see module docstring). Callers (scrub.py,
# push_gate.py) treat a non-empty return from either as an unconditional, non-auto-
# fixable REFUSE hit under a dedicated id ("unicode-bidi-control" / "unicode-tag-chars")
# -- these are NOT entries in refuse-rules.json (they cannot be expressed as a literal-
# text regex against raw bytes the way every other rule is), so verify_rules.py's
# dead-rule check never sees these ids and cannot report them dead; canon.py's own
# --selftest and the calling scripts' --selftest are what prove these fire and that the
# clean fixture never trips them.

def scan_bidi_controls(text):
    """Every bidi control character (U+202A-U+202E, U+2066-U+2069) found anywhere in
    `text`, one hit per occurrence. An empty return means none are present."""
    lines = text.splitlines()
    out = []
    for i, ch in enumerate(text):
        if ch in BIDI_CONTROL_CHARS:
            line_no, ev = _line_and_evidence(text, lines, i)
            out.append({"line": line_no, "evidence": ev, "codepoint": "U+{:04X}".format(ord(ch))})
    return out


def scan_tag_chars(text):
    """Every Unicode TAG block character (U+E0000-U+E007F) found anywhere in `text`,
    one hit per occurrence. Fully invisible in every normal renderer -- this is the
    only way anything ever notices one is there."""
    lines = text.splitlines()
    out = []
    for i, ch in enumerate(text):
        cp = ord(ch)
        if TAG_BLOCK_LO <= cp <= TAG_BLOCK_HI:
            line_no, ev = _line_and_evidence(text, lines, i)
            out.append({"line": line_no, "evidence": ev, "codepoint": "U+{:05X}".format(cp)})
    return out


# ------------------------------------------------------ SHAPE heuristics (fourth pass)
#
# WARNING-tier, never blocking -- see the module docstring's FOURTH PASS section for the
# calibration story (353 raw hits -> 27 genuine, on real content) and the honest reason
# these are never refuse-rules.json entries. Both scans return the SAME hit shape as
# scan_bidi_controls / scan_tag_chars ({"line", "evidence", ...}) so callers can render
# them with the same code path, just routed to a "warnings" bucket instead of
# "unresolved".

# The relationship/business trigger words a SHAPE match must sit next to. Deliberately
# small and literal rather than an attempt to enumerate every possible relationship word
# -- a longer list widens recall at the cost of the precision this was tuned for; see the
# docstring's calibration numbers.
THIRD_PARTY_TRIGGER_WORDS = (
    "wife", "husband", "client", "coach", "student", "partner", "tenant", "invoice",
    "collaborator",
)
_TRIG_ALT = "|".join(THIRD_PARTY_TRIGGER_WORDS)

# Pattern A: possessive BEFORE the trigger -- "Marlowe's husband", "Ashford's invoice".
_NAME_POSSESSIVE_TRIGGER_RE = re.compile(
    r"\b([A-Z][a-z]{2,})(?:'s|’s)\s+(?:" + _TRIG_ALT + r")\b")
# Pattern B: the trigger word (case-insensitive, SCOPED to just the alternation -- NOT a
# blanket (?i) prefix, which would also make the captured name's [A-Z] case-insensitive
# and defeat the whole point of requiring a literally-capitalised token) followed by a
# capitalised name (1-2 tokens) -- "husband Eric", "client Sheila", "coach Dana".
_TRIGGER_NAME_RE = re.compile(
    r"\b(?i:" + _TRIG_ALT + r")\b[:,]?\s+(?:for\s+|is\s+|was\s+)?"
    r"([A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})?)\b")

# Capitalised tokens that are common English/doctrine words, not names -- earned on real
# false positives measured against a real corpus (see docstring), not imagined.
#
# ⛔ NOBODY'S NAME GOES IN THIS TABLE. It ships in a public repo, and a name here would be
# a personal literal in a committed file -- exactly what `identity_rules.py` exists to
# prevent. The operator's OWN terms are excluded via `extra_stopwords`, which `scrub.py`
# fills from the live effective refuse rules at run time. See the docstring's FOURTH PASS
# section.
NAME_SHAPE_STOPWORDS = frozenset("""
Handbook Guide Portal Dashboard Onboarding Success Services Service Report Reports
System Systems Notes Note Overview Program Session Sessions Call Calls Meeting
Meetings Form Forms Agreement Agreements Sheet Sheets List Lists Docs Doc Update
Updates Plan Plans Review Reviews Summary Data Info Details Interaction Conversation
Email Emails Signal Window Deadline Context Name Nudge Statement Records Status
Billing Firm History Registration Workspace Invoice Client Coach Student
Confirmed Booked Pending Overdue Active Also Only Just Still Already Never Always
Google Drive Calendar API JSON Python Bash Git GitHub
Monday Tuesday Wednesday Thursday Friday Saturday Sunday
January February March April May June July August September October November December
""".split())


def scan_third_party_name_shape(text, extra_stopwords=None):
    """A capitalised, name-shaped token adjacent to a relationship/business trigger word
    -- catches a family member, named client, collaborator, or business contact no fixed
    name list can enumerate (see module docstring). One hit per (line, token) pair;
    `token` is included so a human reviewer sees exactly what was flagged.

    `extra_stopwords` is the seam that keeps a person's name out of this file: the caller
    passes the tokens its own LIVE rules already block (scrub.py derives them from the
    effective refuse rules), and they are dropped here so a literal rule and this
    heuristic never both report the same token. Matched case-INSENSITIVELY, because a
    caller deriving terms from a case-insensitive rule cannot know the file's casing."""
    extra = frozenset(s.lower() for s in (extra_stopwords or ()))
    lines = text.splitlines()
    out = []
    for line_no, line in enumerate(lines, start=1):
        found = set()
        for m in _NAME_POSSESSIVE_TRIGGER_RE.finditer(line):
            tok = m.group(1)
            if tok not in NAME_SHAPE_STOPWORDS and tok.lower() not in extra:
                found.add(tok)
        for m in _TRIGGER_NAME_RE.finditer(line):
            tok = m.group(1).split()[0]
            if (tok not in NAME_SHAPE_STOPWORDS and tok.lower() not in extra
                    and tok.lower() not in THIRD_PARTY_TRIGGER_WORDS):
                found.add(tok)
        for tok in sorted(found):
            out.append({"line": line_no, "evidence": line.strip()[:200], "token": tok})
    return out


# Disclosing FACT patterns -- a fact can identify by SHAPE even with every name removed
# ("he owns two homes and holds joint bank accounts"). Each entry is
# (category, compiled regex); a hit records which category fired so a human reviewer
# knows what kind of disclosure to look for, not just that something matched.
_DISCLOSING_FACT_PATTERNS = (
    ("property-ownership", re.compile(
        r"\b(?:owns|co-owns|holds?\s+(?:the\s+)?(?:deed|title)\s+(?:to|on))\b"
        r"[^.\n]{0,40}\b(?:homes?|houses?|properties|condos?|condominiums?|apartments?)\b",
        re.I)),
    ("joint-accounts", re.compile(
        r"\bjoint(?:ly)?\s+(?:held\s+)?(?:bank\s+)?accounts?\b", re.I)),
    ("exact-pay-split", re.compile(
        r"\b\d{1,3}\s*/\s*\d{1,3}\s+split\b"
        r"|\b\d{1,3}\s*%\s+(?:cut|split|share|commission)\b"
        r"|\$\d[\d,]*(?:\.\d{2})?\s*(?:/|per)\s*(?:hour|hr|session|month|client)\b", re.I)),
    ("medical-detail", re.compile(
        r"\bdiagnosed\s+with\b|\bmedical\s+(?:condition|diagnosis)\b"
        r"|\bprescribed\s+(?:medication|a\s+\w+)\b|\bundergoing\s+treatment\b", re.I)),
    # "moved"/"born" alone are ordinary changelog/system verbs in a codebase ("moved
    # 2026-08-06", a component "born 2026-08-08") -- measured as the dominant noise
    # source, so this is scoped to specific life-event verbs, and a trailing ISO
    # timestamp (-MM-DD) is excluded via lookahead so a build/commit date never counts
    # as a birth/marriage year.
    ("dated-personal-event", re.compile(
        r"\b(?:born|married|divorced|diagnosed|passed away)\b[^.\n]{0,40}"
        r"\b(?:19|20)\d{2}(?!-\d{2}-\d{2})\b", re.I)),
)


def scan_disclosing_fact_patterns(text):
    """A FACT that identifies by shape alone -- property ownership, a joint account, an
    exact pay split, a medical detail, or a dated personal life event. One hit per
    (line, category); `category` names which pattern fired."""
    lines = text.splitlines()
    out = []
    for line_no, line in enumerate(lines, start=1):
        cats = set()
        for category, rx in _DISCLOSING_FACT_PATTERNS:
            if rx.search(line):
                cats.add(category)
        for category in sorted(cats):
            out.append({"line": line_no, "evidence": line.strip()[:200], "category": category})
    return out


def original_location(text, offsets, canon_start, canon_end):
    """Map a [canon_start, canon_end) span in canonical text back to the ORIGINAL
    text's line number + evidence. Never returns a canonical offset as if it were an
    original one."""
    lines = text.splitlines()
    if not offsets:
        return 1, ""
    start_idx = min(canon_start, len(offsets) - 1)
    end_idx = min(max(canon_end - 1, 0), len(offsets) - 1)
    orig_pos = min(offsets[start_idx], offsets[end_idx])
    return _line_and_evidence(text, lines, orig_pos)


def canonical_only_hits(text, rx):
    """Hits `rx` finds in the CANONICAL form of `text` that do not correspond to an
    occurrence already found on the RAW text (deduped by original line number -- a
    rule that already fires raw on a line is not re-reported just because the
    canonical view also touches that line). Every hit carries the ORIGINAL line +
    evidence, plus the canonical-form evidence so a human can see WHY it fired."""
    raw_line_nos = {text.count("\n", 0, m.start()) + 1 for m in rx.finditer(text)}
    canon_text, offsets = canonicalize_with_offsets(text)
    lines = text.splitlines()
    out = []
    for m in rx.finditer(canon_text):
        line_no, evidence = original_location(text, offsets, m.start(), m.end())
        if line_no in raw_line_nos:
            continue
        out.append({
            "line": line_no,
            "evidence": evidence,
            "canonical_only": True,
            "canonical_evidence": canon_text[max(0, m.start() - 20):m.end() + 20][:200],
        })
    return out


def transformed_only_hits(text, rx, transform_fn, transform_name):
    """Generic version of canonical_only_hits for any LENGTH-PRESERVING, position-
    identity transform (e.g. ROT13: same length, same offsets, just different
    letters)."""
    raw_line_nos = {text.count("\n", 0, m.start()) + 1 for m in rx.finditer(text)}
    transformed = transform_fn(text)
    lines = text.splitlines()
    out = []
    for m in rx.finditer(transformed):
        line_no, evidence = _line_and_evidence(text, lines, m.start())
        if line_no in raw_line_nos:
            continue
        out.append({
            "line": line_no,
            "evidence": evidence,
            "canonical_only": True,
            "transform": transform_name,
            "canonical_evidence": transformed[max(0, m.start() - 20):m.end() + 20][:200],
        })
    return out


# --------------------------------------------------------------- encoded payloads (Fix 2)
#
# THRESHOLDS (measured, not guessed -- see canon.py --selftest for the numbers):
#   candidate span length >= 8   for the DECODE-THEN-RECHECK pass. LOWERED 16 -> 8 in the
#     THIRD hardening pass (2026-08-05, see module docstring): base64("Oakley") is exactly
#     8 characters (6 raw bytes, evenly divisible by 3, no padding) and was never even
#     attempted at the old >=16 floor -- the fixed name alone, not "Wren Oakley"
#     together, ships clean. The spec's own starting point before that was >=24, which
#     base64("Wren Oakley") (12 raw bytes -> ceil(12/3)*4 = 16, no padding) already
#     showed was too high. Decoding a short candidate is cheap and safe: a false decode
#     of random short text is astronomically unlikely to also satisfy one of the 28
#     refuse patterns, so lowering this floor only costs a little more CPU (more, shorter
#     candidate spans attempted per file -- still linear-time, no new backtracking risk),
#     never correctness.
#   high-entropy span length >= 32, entropy >= 4.5 bits/char   for the UNKNOWN-FORMAT
#     heuristic, exactly as specified. 4.5 is deliberately ABOVE hex's hard ceiling:
#     a hex string can never exceed log2(16) = 4.0 bits/char no matter how random the
#     underlying bytes are, so this threshold structurally EXCLUDES every hex blob
#     (git hashes, sha256 checksums) by construction, not by tuning. It still catches
#     a genuine random secret (measured ~5.7-5.95 bits/char for real API-key-shaped
#     random data) and lets a low-diversity placeholder like "FAKEFAKEFAKE...1234"
#     through (measured ~2.7 bits/char -- see --selftest for the exact figures). This
#     threshold is UNCHANGED by the candidate-floor lowering above -- it only applies to
#     spans already >= 32 chars, well above either floor.

_CANDIDATE_LEN = 8
_ENTROPY_LEN = 32
_ENTROPY_THRESHOLD = 4.5
_MAX_DECODE_DEPTH = 3  # second hardening pass, 2026-08-05 -- see _decode_chain below

_B64_RE = re.compile(
    r'(?<![A-Za-z0-9+/_\-])[A-Za-z0-9+/_\-]{%d,}={0,2}(?![A-Za-z0-9+/_\-])'
    % _CANDIDATE_LEN)
_HEX_RE = re.compile(r'(?<![0-9A-Fa-f])(?:0x)?[0-9A-Fa-f]{%d,}(?![0-9A-Fa-f])'
                      % _CANDIDATE_LEN)
_URL_RE = re.compile(r'(?:%[0-9A-Fa-f]{2}){3,}')
# base32 output (Python's base64.b32encode) is UPPERCASE with '=' padding -- restricted
# to uppercase on purpose so this candidate class does not swallow ordinary mixed-case
# prose the way an [A-Za-z2-7] class would.
_BASE32_RE = re.compile(r'(?<![A-Z2-7=])[A-Z2-7]{%d,}={0,6}(?![A-Z2-7=])' % _CANDIDATE_LEN)
# quoted-printable, fully-escaped form (the shape the red team actually planted):
# a contiguous run of 4+ "=XX" hex-escape groups, e.g. "=65=6E=76=65=72".
_QP_RE = re.compile(r'(?:=[0-9A-Fa-f]{2}){4,}')


def shannon_entropy(s):
    if not s:
        return 0.0
    counts = Counter(s)
    n = len(s)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def _try_decode_base64(blob):
    s = blob.rstrip("=")
    pad = "=" * (-len(s) % 4)
    raw = None
    for candidate in (s + pad, (s + pad).replace("-", "+").replace("_", "/")):
        try:
            raw = base64.b64decode(candidate, validate=True)
            break
        except (binascii.Error, ValueError):
            continue
    if raw is None:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _try_decode_hex(blob):
    h = blob[2:] if blob.lower().startswith("0x") else blob
    if len(h) % 2 != 0:
        return None
    try:
        raw = binascii.unhexlify(h)
    except (binascii.Error, ValueError):
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _try_decode_url(blob):
    try:
        out_bytes = bytearray()
        i = 0
        while i < len(blob):
            if blob[i] == "%" and i + 2 < len(blob):
                out_bytes.append(int(blob[i + 1:i + 3], 16))
                i += 3
            else:
                out_bytes.append(ord(blob[i]))
                i += 1
        return out_bytes.decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None


def _try_decode_base32(blob):
    s = blob.rstrip("=").upper()
    pad = "=" * (-len(s) % 8)
    try:
        raw = base64.b32decode(s + pad, casefold=True)
    except (binascii.Error, ValueError):
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _try_decode_quoted_printable(blob):
    try:
        raw = quopri.decodestring(blob.encode("ascii"))
    except (binascii.Error, ValueError):
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _decode_chain(blob, decoder):
    """BOUNDED RECURSIVE DECODE (second hardening pass, 2026-08-05): the original Fix 2
    unwrapped exactly one layer, so base64(base64("Wren Oakley")) decoded to more
    base64 text -- not the name -- and sailed through. This tries the SAME decoder
    again on its own output, up to `_MAX_DECODE_DEPTH` layers deep, so a doubly- (or
    triply-) wrapped payload is still reached. CYCLE GUARD: stops as soon as a layer
    produces a value already seen in this chain (covers a pathological self-inverse
    encoding that would otherwise loop) -- with a hard depth cap on top regardless, so
    this can never run away even if the guard were somehow defeated.

    Returns [(layer_number, decoded_text), ...] for every layer that decoded to valid
    UTF-8 text, layer 1 first. An empty list means the blob never decoded at all."""
    seen = {blob}
    layers = []
    current = blob
    for layer in range(1, _MAX_DECODE_DEPTH + 1):
        decoded = decoder(current)
        if decoded is None or decoded in seen:
            break
        seen.add(decoded)
        layers.append((layer, decoded))
        current = decoded
    return layers


def scan_encoded_payloads(text, refuse_rules):
    """Find base64 / hex / percent-encoded / base32 / quoted-printable candidate spans,
    decode each up to `_MAX_DECODE_DEPTH` layers deep (see `_decode_chain`), and re-run
    the REFUSE rules against EVERY decoded layer. Also flags high-entropy blobs as a
    distinct unknown-format-secret finding. Returns a list of finding dicts shaped like
    scrub.py/push_gate.py's existing 'unresolved'/'refused' entries -- never a "to"
    field, because a decoded/entropy finding is never auto-fixable."""
    findings = []
    lines = text.splitlines()
    compiled = [(r["id"], r.get("tier", ""), r.get("why", ""),
                 re.compile(r["pattern"], re.MULTILINE)) for r in refuse_rules]
    seen_decoded = set()

    for kind, rx, decoder in (("base64", _B64_RE, _try_decode_base64),
                              ("hex", _HEX_RE, _try_decode_hex),
                              ("url", _URL_RE, _try_decode_url),
                              ("base32", _BASE32_RE, _try_decode_base32),
                              ("quoted-printable", _QP_RE, _try_decode_quoted_printable)):
        for m in rx.finditer(text):
            blob = m.group(0)
            line_no, ev = _line_and_evidence(text, lines, m.start())

            for layer, decoded in _decode_chain(blob, decoder):
                key = (kind, blob, layer)
                if key in seen_decoded:
                    continue
                for rid, tier, why, drx in compiled:
                    if drx.search(decoded):
                        seen_decoded.add(key)
                        findings.append({
                            "id": "encoded-" + rid, "tier": tier,
                            "why": "{} -- found inside a {}-DECODED blob ({} layer{} "
                                   "deep of up to {} tried), not literal text".format(
                                       why, kind, layer, "" if layer == 1 else "s",
                                       _MAX_DECODE_DEPTH),
                            "hits": [{"line": line_no, "evidence": ev, "encoding": kind,
                                      "decode_depth": layer,
                                      "decoded_evidence": decoded[:200]}],
                        })

            if kind in ("base64", "hex") and len(blob) >= _ENTROPY_LEN:
                ent = shannon_entropy(blob)
                if ent >= _ENTROPY_THRESHOLD:
                    findings.append({
                        "id": "high-entropy-blob", "tier": "1-secret",
                        "why": "a {}-char {} blob with Shannon entropy {:.2f} "
                               "bits/char (>= {}) -- looks like a secret in a format "
                               "no literal rule anticipates".format(
                                   len(blob), kind, ent, _ENTROPY_THRESHOLD),
                        "hits": [{"line": line_no, "evidence": ev, "encoding": kind,
                                  "entropy": round(ent, 3)}],
                    })
    return findings


# --------------------------------------------------------------- tree hashing (Build 1)
#
# SHARED, ON PURPOSE: push_gate.py's own receipt and judge.py's judge receipt must agree
# on what "the tree's current state" means, or a staleness check comparing the two would
# be comparing apples to oranges. Rather than have two independent implementations of
# "walk + hash a tree" that could silently drift apart, both callers use THESE functions
# -- push_gate.py aliases its own sha256_bytes / sha256_file / canonical_json / walk_tree
# names to these (see push_gate.py's imports, right after `import canon`), and judge.py
# calls `compute_tree_state()` directly to build a judge receipt's tree_sha256 in
# EXACTLY the shape push_gate.py's own build_receipt produces for a CLEAN tree (there,
# restricted to "gated_files"; here, unconditionally every file -- identical on a clean
# tree, since gated_files == every file when nothing was refused).

def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_json(obj):
    """Deterministic serialization -- same object always hashes the same way."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def walk_tree_files(root):
    """Every file under root, sorted, as (relpath-with-forward-slashes, abspath).
    Explicitly refuses to descend into a symlinked directory -- returns that as a second
    list of problem relpaths so the caller can fail closed instead of silently skipping
    it. This is push_gate.py's own pre-Build-1 walk_tree(), moved here so there is only
    ONE implementation for push_gate.py and judge.py to share."""
    files = []
    symlinked_dirs = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        real_dirs = []
        for d in sorted(dirnames):
            full = os.path.join(dirpath, d)
            if os.path.islink(full):
                symlinked_dirs.append(os.path.relpath(full, root).replace(os.sep, "/"))
            else:
                real_dirs.append(d)
        dirnames[:] = real_dirs
        for name in sorted(filenames):
            abspath = os.path.join(dirpath, name)
            rel = os.path.relpath(abspath, root).replace(os.sep, "/")
            files.append((rel, abspath))
    files.sort(key=lambda t: t[0])
    return files, sorted(symlinked_dirs)


def compute_tree_state(root):
    """Walk `root` and hash every regular file's RAW bytes -- the same primitive
    push_gate.py's own build_receipt uses for its tree_sha256.

    Returns (files_sorted, tree_sha256, symlinked_dirs, problem_files):
      files_sorted   -- [{"path": rel, "sha256": hash}, ...] sorted by path
      tree_sha256    -- sha256_bytes(canonical_json(files_sorted))
      symlinked_dirs -- relpaths of any symlinked directory found (never descended into)
      problem_files  -- [{"path", "reason", "detail"}] for anything that could not be
                        stat'd, was not a regular file, or could not be read -- fail
                        closed, never silently hashed as if it were fine.
    """
    files, symlinked_dirs = walk_tree_files(root)
    files_out = []
    problem_files = []
    for rel, abspath in files:
        try:
            st = os.stat(abspath)
        except OSError as e:
            problem_files.append({"path": rel, "reason": "unreadable", "detail": str(e)})
            continue
        if not stat.S_ISREG(st.st_mode):
            problem_files.append({"path": rel, "reason": "non-regular-file",
                                  "detail": "not hashed -- refusing to open() it"})
            continue
        try:
            h = sha256_file(abspath)
        except OSError as e:
            problem_files.append({"path": rel, "reason": "unreadable", "detail": str(e)})
            continue
        files_out.append({"path": rel, "sha256": h})
    files_sorted = sorted(files_out, key=lambda f: f["path"])
    tree_hash = sha256_bytes(canonical_json(files_sorted))
    return files_sorted, tree_hash, symlinked_dirs, problem_files


# ---------------------------------------------------------------------------- self-test

def selftest():
    import base64 as _b64
    import binascii as _hexmod
    import json as _json
    import os as _os
    import secrets as _secrets
    import tempfile

    ok_all = True

    def report(label, passed, detail=""):
        nonlocal ok_all
        ok_all = ok_all and passed
        print("  [{}] {}{}".format("PASS" if passed else "FAIL", label,
                                    (" -- " + detail) if detail else ""))

    print("canon.py --selftest")
    rx_wren = re.compile(r"(?i)\bwren\b")
    rx_oakley = re.compile(r"(?i)\boakley\b")

    print("\nNFKC / fullwidth")
    fullwidth = "Ｗｒｅｎ"  # fullwidth "Wren"
    report("fullwidth 'Wren' canonicalises to plain 'Wren'",
           canonicalize(fullwidth) == "Wren", canonicalize(fullwidth))

    print("\nzero-width / BOM strip")
    zwj_spliced = "‍".join(list("Wren"))
    report("ZWJ-spliced 'Wren' canonicalises to 'Wren'",
           canonicalize(zwj_spliced) == "Wren")
    bom_prefixed = "﻿Wren"
    report("a leading BOM is stripped", canonicalize(bom_prefixed) == "Wren")

    print("\ncombining marks (accent strip)")
    accented = "Wrén"  # "Wr" + 'é' + "n"
    report("accented 'Wrén' canonicalises to 'Wren'", canonicalize(accented) == "Wren")

    print("\nhomoglyph fold")
    for cyr, lat in HOMOGLYPH_MAP.items():
        got = canonicalize(cyr)
        report("{!r} folds to {!r}".format(cyr, lat), got == lat, got)

    print("\nsmall-caps fold (second hardening pass, 2026-08-05)")
    for sc, lat in SMALL_CAPS_MAP.items():
        got = canonicalize(sc)
        report("{!r} folds to {!r}".format(sc, lat), got == lat, got)
    smallcaps_name = "ᴡʀᴇɴ ᴏᴀᴋʟᴇʏ"
    report("{!r} canonicalises to 'wren oakley' and trips name-wren/name-oakley via "
           "the union".format(smallcaps_name),
           canonicalize(smallcaps_name) == "wren oakley"
           and canonical_only_hits(smallcaps_name, rx_wren)
           and canonical_only_hits(smallcaps_name, rx_oakley),
           canonicalize(smallcaps_name))
    report("the small-caps form is invisible on the raw pass alone (proves the fold, "
           "not a coincidence)", not rx_wren.search(smallcaps_name))

    print("\nleetspeak fold")
    report("'Wr3n 04kl3y' folds to 'Wren oakley' (the space between two real, "
           "multi-letter words is preserved -- only single-char gaps inside a "
           "spelled-out token collapse)",
           canonicalize("Wr3n 04kl3y") == "Wren oakley", canonicalize("Wr3n 04kl3y"))

    print("\nintra-word separator collapse")
    for raw, want in (
            ("Wr.en Oak-ley", "Wren Oakley"),
            ("Wr\nen", "Wren"),
            ("W r e n", "Wren"),
    ):
        got = canonicalize(raw)
        report("{!r} collapses to {!r}".format(raw, want), got == want, got)

    print("\nescape / HTML entity decode (THIRD hardening pass, 2026-08-05 -- Bypass 2)")
    report("'\\\\u0057ren' (JS unicode escape) canonicalises to 'Wren'",
           canonicalize("\\u0057ren") == "Wren", canonicalize("\\u0057ren"))
    report("'\\\\u{57}ren' (JS ES6 code-point escape) canonicalises to 'Wren'",
           canonicalize("\\u{57}ren") == "Wren", canonicalize("\\u{57}ren"))
    report("'\\\\x57ren' (hex byte escape) canonicalises to 'Wren'",
           canonicalize("\\x57ren") == "Wren", canonicalize("\\x57ren"))
    report("'\\\\127ren' (octal escape, 0o127 == 'W') canonicalises to 'Wren'",
           canonicalize("\\127ren") == "Wren", canonicalize("\\127ren"))
    report("'&#87;ren' (HTML decimal entity) canonicalises to 'Wren'",
           canonicalize("&#87;ren") == "Wren", canonicalize("&#87;ren"))
    report("'&#x57;ren' (HTML hex entity) canonicalises to 'Wren'",
           canonicalize("&#x57;ren") == "Wren", canonicalize("&#x57;ren"))
    report("an unrecognised '&D;' is left untouched, never guessed at -- decoding "
           "returns None, not a guessed character (separator-collapse further down the "
           "SAME pipeline may still fold its ';' like any other single separator, "
           "exactly as it would for a literal semicolon -- that is unrelated to this "
           "decode stage)",
           _decode_one_escape("&D;") is None)

    js_escaped = "".join("\\u{:04x}".format(ord(c)) for c in "Wren Oakley")
    report("the fully \\u-escaped JS string {!r} is invisible on the raw pass alone "
           "but caught by the union (Bypass 2, JS/JSON case)".format(js_escaped),
           not rx_wren.search(js_escaped)
           and canonical_only_hits(js_escaped, rx_wren)
           and canonical_only_hits(js_escaped, rx_oakley))

    html_escaped = "".join("&#{};".format(ord(c)) for c in "Wren Oakley")
    report("the fully &#NN;-escaped SVG/HTML string {!r} is invisible on the raw pass "
           "alone but caught by the union (Bypass 2, SVG/HTML case)".format(html_escaped),
           not rx_wren.search(html_escaped)
           and canonical_only_hits(html_escaped, rx_wren)
           and canonical_only_hits(html_escaped, rx_oakley))

    print("\nFALSE-POSITIVE DANGER -- collapsing must never defeat the \\b anchors")
    for benign in ("draw.rendered", "new.renewal", "oak.leyland"):
        canon_form = canonicalize(benign)
        hit = rx_wren.search(canon_form) or rx_oakley.search(canon_form)
        report("{!r} -> {!r} still trips NOTHING (\\b anchors hold)".format(
               benign, canon_form), not hit)

    print("\nTHE ADDITIVE-UNION PROOF -- the production path (raw hits_for_rule UNION "
          "canonical_only_hits) never loses a hit the raw scan already found, and "
          "gains exactly the ones that were previously invisible")

    def _raw_hit(p, rx):
        return bool(rx.search(p))

    def _union_hit(p, rx):
        return bool(rx.search(p)) or bool(canonical_only_hits(p, rx))

    probes = [
        ("Wren reviews this himself.", rx_wren, True),   # raw already catches this
        ("Wr.en Oak-ley", rx_wren, False),               # raw does NOT catch this
        ("nothing to see here", rx_wren, False),          # neither should catch this
    ]
    for p, rx, raw_expected in probes:
        raw_hit = _raw_hit(p, rx)
        union_hit = _union_hit(p, rx)
        report("{!r}: raw-hit={} (expected {})".format(p, raw_hit, raw_expected),
               raw_hit == raw_expected)
        report("{!r}: union-hit={} is >= raw-hit={} (never regresses)".format(
               p, union_hit, raw_hit), union_hit or not raw_hit)
    report("the obfuscated form is invisible on the raw pass alone but caught by the "
           "union (this is the entire point of Fix 1)",
           not _raw_hit("Wr.en Oak-ley", rx_wren) and _union_hit("Wr.en Oak-ley", rx_wren))

    print("\nROT13")
    rotated = rot13("Wren Oakley")
    report("ROT13 of the name does not read literally as the name",
           not rx_wren.search(rotated))
    report("ROT13 is involutive -- rotating twice restores the original",
           rot13(rotated) == "Wren Oakley")

    print("\nbidi control ban (second hardening pass, 2026-08-05 -- Trojan Source class)")
    reversed_name = "‮" + "nerW" + "‬"  # RLO + "Wren" stored reversed + PDF
    report("a bidi-reversed name is caught as PRESENCE, not decoded",
           bool(scan_bidi_controls(reversed_name)))
    for cp in (0x202A, 0x202B, 0x202C, 0x202D, 0x202E, 0x2066, 0x2067, 0x2068, 0x2069):
        hit = scan_bidi_controls("plain text " + chr(cp) + " more text")
        report("U+{:04X} is caught by presence alone".format(cp), bool(hit))
    report("ordinary prose with no bidi controls trips nothing",
           not scan_bidi_controls("Wren reviews this himself, nothing hidden here."))

    print("\nUnicode TAG block ban (fully invisible stego channel)")
    hidden_name = "notes" + "".join(chr(0xE0000 + ord(c)) for c in "wren oakley")
    report("a name hidden entirely in TAG characters is caught as PRESENCE",
           bool(scan_tag_chars(hidden_name)))
    report("...and is INVISIBLE to the raw regex pass (proves it needed the ban, not "
           "a lucky literal match)", not rx_wren.search(hidden_name))
    report("ordinary prose with no TAG characters trips nothing",
           not scan_tag_chars("Wren reviews this himself, nothing hidden here."))

    print("\nSHAPE heuristics (fourth pass, WARNING-tier -- 2026-08-15)")
    tp_hits = scan_third_party_name_shape("His wife Fern handles the scheduling.\n")
    report("'wife Fern' is caught by the trigger-then-name shape",
           any(h["token"] == "Fern" for h in tp_hits), "hits: {}".format(tp_hits))
    # ⛔ DO NOT "FIX" the WARNING-tier leak-scan noise these two names produce by adding
    # them to FICTIONAL_FIXTURE_WORDS (.github/scripts/check_no_internal_leakage.py).
    # "Marlowe" and "Rosalind" show up as third-party-name-shape WARNINGs when the whole-tree
    # scanner walks this file -- but they are POSITIVE test cases here, not leaked names:
    # FICTIONAL_FIXTURE_WORDS is read INSIDE scan_third_party_name_shape() itself, so any
    # token in that set is silently excluded from detection before the assertions below ever
    # run. Allowlisting "marlowe"/"rosalind" would make the production heuristic stop flagging
    # them -- and would defang these exact assertions, which exist to prove the heuristic
    # still catches the possessive-before-trigger and partner-NAME shapes. If this noise ever
    # becomes intolerable, the correct fix is a SELF-REFERENCE path exclusion for this test
    # block in the whole-tree scanner (WHOLE_TREE_SELF_REFERENCE_EXCLUDE_PREFIXES/PATHS in
    # check_no_internal_leakage.py), mirroring the existing entry for
    # system/shipping-lane/fixtures/ -- NOT a token-level allowlist entry.
    tp_hits2 = scan_third_party_name_shape("Marlowe's husband had an ER visit.\n")
    report("'Marlowe's husband' is caught by the possessive-before-trigger shape",
           any(h["token"] == "Marlowe" for h in tp_hits2), "hits: {}".format(tp_hits2))
    partner_hits = scan_third_party_name_shape(
        "He and his partner Rosalind live across two homes.\n")
    report("the donor's real 2026-08-15 miss-shape ('partner NAME') is caught",
           any(h["token"] == "Rosalind" for h in partner_hits))
    report("a bare capitalised word with NO trigger word nearby trips nothing",
           not scan_third_party_name_shape("The Client Handbook explains billing.\n"))
    report("a lowercase trigger word with no adjacent capitalised name trips nothing",
           not scan_third_party_name_shape(
               "The client call and the coach session both moved to Friday.\n"))
    # ⭐ THE SEAM THAT REPLACES THE DONOR'S HARD-CODED NAMES. The donor listed its author's
    # own name and personas in NAME_SHAPE_STOPWORDS so this heuristic would not re-report
    # what a literal rule already blocked. Here the CALLER supplies them from the live
    # rules, so the same property holds with nobody's name committed to this file.
    _own_name_line = "The invoice Wren sent covers the retainer.\n"
    covered = scan_third_party_name_shape(_own_name_line,
                                          extra_stopwords=["wren", "oakley"])
    report("a token the caller's OWN rules already block is dropped via extra_stopwords "
           "(never double-reported alongside its literal rule)",
           not covered, "hits: {}".format(covered))
    report("...and the SAME line without that exclusion DOES warn (proves the exclusion "
           "is what silenced it, not a pattern that never fired)",
           any(h["token"] == "Wren"
               for h in scan_third_party_name_shape(_own_name_line)),
           "hits: {}".format(scan_third_party_name_shape(_own_name_line)))
    report("extra_stopwords matches case-INSENSITIVELY (a caller deriving terms from a "
           "case-insensitive rule cannot know the file's casing)",
           not scan_third_party_name_shape("His wife Fern called.\n",
                                           extra_stopwords=["FERN"]))

    fact_hits = scan_disclosing_fact_patterns(
        "He owns two homes and holds joint bank accounts.\n")
    report("'owns two homes' is caught as property-ownership",
           any(h["category"] == "property-ownership" for h in fact_hits),
           "hits: {}".format(fact_hits))
    report("'joint bank accounts' is caught as joint-accounts (same sentence, both fire)",
           any(h["category"] == "joint-accounts" for h in fact_hits))
    report("an exact hourly rate is caught as exact-pay-split",
           any(h["category"] == "exact-pay-split"
               for h in scan_disclosing_fact_patterns("Admin work: $30/hr.\n")))
    report("a medical detail is caught as medical-detail",
           any(h["category"] == "medical-detail"
               for h in scan_disclosing_fact_patterns("She was diagnosed with a condition.\n")))
    report("a dated personal life event is caught as dated-personal-event",
           any(h["category"] == "dated-personal-event"
               for h in scan_disclosing_fact_patterns("They married in 1998 upstate.\n")))
    report("'his own home' (the idiom, no verb 'owns') trips nothing -- the false "
           "positive this pattern was tightened to avoid",
           not scan_disclosing_fact_patterns(
               "He works from his own home office most days.\n"))
    report("an ordinary changelog line ('moved 2026-08-06') trips nothing -- the "
           "dated-personal-event false positive this pattern was tightened to avoid",
           not scan_disclosing_fact_patterns(
               "This step was moved out of /save entirely (2026-08-06).\n"))
    report("a component 'born' on an ISO build date trips nothing (excludes -MM-DD)",
           not scan_disclosing_fact_patterns(
               "Fresh-but-unwired (born 2026-08-08): plan_git_check.py.\n"))

    print("\nencoded payloads (Fix 2)")
    refuse_rules = [
        {"id": "name-wren", "mode": "regex", "pattern": r"(?i)\bwren\b", "why": "name"},
        {"id": "name-oakley", "mode": "regex", "pattern": r"(?i)\boakley\b", "why": "name"},
        {"id": "key-anthropic", "mode": "regex",
         "pattern": r"sk-ant-[A-Za-z0-9_\-]{20,}", "why": "key"},
    ]
    b64_name = _b64.b64encode(b"Wren Oakley").decode()
    hex_name = _hexmod.hexlify(b"Wren Oakley").decode()
    findings = scan_encoded_payloads("contact: " + b64_name + " thanks", refuse_rules)
    report("base64('Wren Oakley') (len={}) is decoded and caught".format(len(b64_name)),
           any(f["id"] == "encoded-name-wren" for f in findings)
           and any(f["id"] == "encoded-name-oakley" for f in findings),
           "found: {}".format([f["id"] for f in findings]))
    findings = scan_encoded_payloads("contact: " + hex_name + " thanks", refuse_rules)
    report("hex('Wren Oakley') (len={}) is decoded and caught".format(len(hex_name)),
           any(f["id"] == "encoded-name-wren" for f in findings))

    print("\ncandidate floor lowered 16 -> 8 (third hardening pass, 2026-08-05)")
    b64_oakley_only = _b64.b64encode(b"Oakley").decode()
    report("base64('Oakley') alone is exactly {} chars -- below the OLD floor of 16, "
           "at the NEW floor of 8".format(len(b64_oakley_only)),
           len(b64_oakley_only) == 8 and _CANDIDATE_LEN == 8)
    findings = scan_encoded_payloads("cfg: " + b64_oakley_only + " end", refuse_rules)
    report("base64('Oakley') alone (len={}) is now decoded and caught at the lowered "
           "floor".format(len(b64_oakley_only)),
           any(f["id"] == "encoded-name-oakley" for f in findings),
           "found: {}".format([f["id"] for f in findings]))

    b64_key = _b64.b64encode(b"sk-ant-FAKEFAKEFAKEFAKEFAKE12345678").decode()
    findings = scan_encoded_payloads("key: " + b64_key + " end", refuse_rules)
    report("a base64'd sk-ant-... key is decoded and caught",
           any(f["id"] == "encoded-key-anthropic" for f in findings))

    url_email = "".join("%{:02X}".format(ord(c)) for c in "wren.oakley@example.com")
    findings = scan_encoded_payloads("reach " + url_email + " now", refuse_rules)
    report("a fully percent-encoded email is decoded and caught",
           any(f["id"] == "encoded-name-wren" for f in findings))

    print("\nbase32 + quoted-printable (second hardening pass, 2026-08-05)")
    b32_key = _b64.b32encode(b"sk-ant-FAKEFAKEFAKEFAKEFAKE12345678").decode()
    findings = scan_encoded_payloads("cfg: " + b32_key + " end", refuse_rules)
    report("a base32'd sk-ant-... key is decoded and caught",
           any(f["id"] == "encoded-key-anthropic" for f in findings),
           "found: {}".format([f["id"] for f in findings]))

    qp_email = "".join("={:02X}".format(b) for b in "wren.oakley@example.com".encode())
    findings = scan_encoded_payloads("reach " + qp_email + " now", refuse_rules)
    report("a fully quoted-printable-encoded email is decoded and caught",
           any(f["id"] == "encoded-name-wren" for f in findings),
           "found: {}".format([f["id"] for f in findings]))

    print("\nbounded recursive decode, depth cap {} (second hardening pass, "
          "2026-08-05)".format(_MAX_DECODE_DEPTH))
    b64_once = _b64.b64encode(b"Wren Oakley").decode()
    b64_twice = _b64.b64encode(b64_once.encode()).decode()
    findings_once = scan_encoded_payloads("note: " + b64_once + " end", refuse_rules)
    report("single-wrapped base64 is still caught at layer 1 (no regression)",
           any(f["id"] == "encoded-name-wren" and f["hits"][0]["decode_depth"] == 1
               for f in findings_once))
    findings_twice = scan_encoded_payloads("note: " + b64_twice + " end", refuse_rules)
    report("double-wrapped base64(base64(name)) -- invisible to a single-layer decode "
           "-- is caught at layer 2",
           any(f["id"] == "encoded-name-wren" and f["hits"][0]["decode_depth"] == 2
               for f in findings_twice),
           "found: {}".format([(f["id"], f["hits"][0].get("decode_depth"))
                               for f in findings_twice]))
    chain = _decode_chain(b64_twice, _try_decode_base64)
    report("_decode_chain never exceeds the depth cap even when more layers exist",
           len(chain) <= _MAX_DECODE_DEPTH, "got {} layers".format(len(chain)))
    report("a cycle guard stops a decoder that returns its own input (would otherwise "
           "loop forever)", _decode_chain("AAAA", lambda s: s) == [])

    print("\nentropy heuristic -- what it does and does not fire on")
    fake_placeholder = "FAKEFAKEFAKEFAKEFAKE1234"
    fake_entropy = shannon_entropy(fake_placeholder)
    report("a low-diversity placeholder ({!r}, entropy {:.2f}) stays UNDER threshold "
           "{}".format(fake_placeholder, fake_entropy, _ENTROPY_THRESHOLD),
           fake_entropy < _ENTROPY_THRESHOLD)
    random_secret = _secrets.token_urlsafe(32)
    random_entropy = shannon_entropy(random_secret)
    report("a genuine random secret (entropy {:.2f}) clears threshold {}".format(
           random_entropy, _ENTROPY_THRESHOLD), random_entropy >= _ENTROPY_THRESHOLD)
    import hashlib as _hashlib
    sha_hash = _hashlib.sha256(b"some ordinary file content").hexdigest()
    hash_entropy = shannon_entropy(sha_hash)
    report("a sha256 hex hash (entropy {:.2f}) can NEVER clear {} -- hex's ceiling is "
           "log2(16)=4.0 bits/char, structurally below the threshold".format(
               hash_entropy, _ENTROPY_THRESHOLD),
           hash_entropy < _ENTROPY_THRESHOLD)
    findings = scan_encoded_payloads("the fixture key is " + fake_placeholder + " ok",
                                      refuse_rules)
    report("the placeholder alone triggers NO high-entropy finding",
           not any(f["id"] == "high-entropy-blob" for f in findings))
    findings = scan_encoded_payloads("secret=" + random_secret, refuse_rules)
    report("the random secret DOES trigger a high-entropy finding",
           any(f["id"] == "high-entropy-blob" for f in findings))

    print("\nfixtures -- no false positives introduced")
    here = _os.path.dirname(_os.path.abspath(__file__))
    refuse_rules_path = _os.path.join(here, "refuse-rules.json")
    clean_fixture_path = _os.path.join(here, "fixtures", "clean-fixture.md")
    if _os.path.isfile(refuse_rules_path) and _os.path.isfile(clean_fixture_path):
        with open(refuse_rules_path, "r", encoding="utf-8") as fh:
            real_rules = _json.load(fh)
        with open(clean_fixture_path, "r", encoding="utf-8") as fh:
            clean_text = fh.read()
        bad = []
        for rule in real_rules:
            rx = re.compile(rule["pattern"], re.MULTILINE)
            if canonical_only_hits(clean_text, rx):
                bad.append(rule["id"])
            if transformed_only_hits(clean_text, rx, rot13, "rot13"):
                bad.append(rule["id"] + " (rot13)")
        report("clean-fixture.md trips NO rule via canonical or ROT13 view",
               not bad, "false positives: {}".format(bad))
        enc_findings = scan_encoded_payloads(clean_text, real_rules)
        report("clean-fixture.md trips NO encoded-payload finding",
               not enc_findings, "found: {}".format(enc_findings))
        report("clean-fixture.md trips NO bidi-control finding",
               not scan_bidi_controls(clean_text))
        report("clean-fixture.md trips NO TAG-block finding",
               not scan_tag_chars(clean_text))
        report("clean-fixture.md trips NO third-party name-shape WARNING",
               not scan_third_party_name_shape(clean_text),
               "hits: {}".format(scan_third_party_name_shape(clean_text)))
        report("clean-fixture.md trips NO disclosing-fact-pattern WARNING",
               not scan_disclosing_fact_patterns(clean_text),
               "hits: {}".format(scan_disclosing_fact_patterns(clean_text)))

        for extra_clean in ("draw.rendered", "new.renewal", "oak.leyland"):
            report("{!r} (the documented false-positive traps) trips no bidi/tag "
                   "finding either".format(extra_clean),
                   not scan_bidi_controls(extra_clean) and not scan_tag_chars(extra_clean))
    else:
        report("fixtures reachable for the false-positive check", False,
               "not found under {!r}".format(here))

    print("\ntree hashing (Build 1 shared foundation -- push_gate.py + judge.py)")
    with tempfile.TemporaryDirectory(prefix="canon-treehash-selftest-") as tmp:
        with open(_os.path.join(tmp, "a.md"), "w", encoding="utf-8") as fh:
            fh.write("hello\n")
        with open(_os.path.join(tmp, "b.md"), "w", encoding="utf-8") as fh:
            fh.write("world\n")
        files1, hash1, sym1, prob1 = compute_tree_state(tmp)
        report("compute_tree_state finds every file, no symlink/problem noise",
               len(files1) == 2 and not sym1 and not prob1,
               "files={} sym={} prob={}".format(files1, sym1, prob1))
        files1b, hash1b, _, _ = compute_tree_state(tmp)
        report("hashing the SAME tree twice gives the SAME tree_sha256 (deterministic)",
               hash1 == hash1b)
        expected_hash = sha256_bytes(canonical_json(
            sorted([{"path": "a.md", "sha256": sha256_file(_os.path.join(tmp, "a.md"))},
                    {"path": "b.md", "sha256": sha256_file(_os.path.join(tmp, "b.md"))}],
                   key=lambda f: f["path"])))
        report("tree_sha256 matches an independently hand-computed hash over the same "
               "shape", hash1 == expected_hash)

        with open(_os.path.join(tmp, "c.md"), "w", encoding="utf-8") as fh:
            fh.write("a third file\n")
        _, hash2, _, _ = compute_tree_state(tmp)
        report("adding a file changes tree_sha256 (this is the staleness signal "
               "push_gate.py relies on)", hash2 != hash1)

        sub = _os.path.join(tmp, "real-sub")
        _os.makedirs(sub)
        # A symlink needs Administrator or Developer Mode on Windows (WinError 1314).
        # SKIPPED IS NOT PASSED, and it must never read like one -- the whole design of
        # this lane is that "could not look" and "looked and it was fine" are spelled
        # differently (see NOT-EVALUATED in the ship skill). So this prints its own line
        # and deliberately does NOT touch ok_all in either direction.
        try:
            _os.symlink(sub, _os.path.join(tmp, "linked"))
        except OSError as _e:
            print("  [SKIP] a symlinked directory is reported, never silently descended "
                  "into -- COULD NOT CREATE A SYMLINK ON THIS HOST ({}: {}). THIS IS NOT A "
                  "PASS; the assertion did not run. On Windows os.symlink requires "
                  "Administrator or Developer Mode -- enable it and re-run to actually "
                  "exercise this path.".format(type(_e).__name__, _e))
        else:
            _, _, sym2, _ = compute_tree_state(tmp)
            report("a symlinked directory is reported, never silently descended into",
                   "linked" in sym2)

        import stat as _stat
        fifo_tree = tempfile.mkdtemp(prefix="canon-treehash-fifo-")
        try:
            with open(_os.path.join(fifo_tree, "clean.md"), "w", encoding="utf-8") as fh:
                fh.write("fine\n")
            # os.mkfifo does not exist on Windows -- there are no FIFOs to make. SKIPPED
            # IS NOT PASSED: this prints its own line and leaves ok_all alone, so a Windows
            # run can never be mistaken for one that exercised this path.
            if not hasattr(_os, "mkfifo"):
                print("  [SKIP] a FIFO is reported as a problem file, never hashed -- "
                      "os.mkfifo does not exist on this platform. THIS IS NOT A PASS; the "
                      "assertion did not run. Exercise it on macOS/Linux.")
            else:
                _os.mkfifo(_os.path.join(fifo_tree, "a.fifo"))
                _, _, _, prob2 = compute_tree_state(fifo_tree)
                report("a FIFO is reported as a problem file, never hashed",
                       any(p["path"] == "a.fifo" and p["reason"] == "non-regular-file"
                           for p in prob2), "problems: {}".format(prob2))
        finally:
            import shutil as _shutil
            _shutil.rmtree(fifo_tree, ignore_errors=True)

    print("\n{}".format("-" * 60))
    print("SELFTEST:", "PASS" if ok_all else "FAIL")
    return 0 if ok_all else 1


if __name__ == "__main__":
    import sys as _sys
    if "--selftest" in _sys.argv:
        _sys.exit(selftest())
    print("canon.py is an importable module -- run with --selftest to prove it, or "
          "import it from scrub.py / push_gate.py.")

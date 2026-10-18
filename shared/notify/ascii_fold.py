#!/usr/bin/env python3
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: a push body that is not plain ASCII does not arrive as a message. MEASURED on
#      2026-09-21 against a real phone: a teaser containing an em dash, a middle dot or an
#      accented letter was turned by ntfy into an ATTACHMENT -- the phone showed
#      "You received a file: attachment.txt" instead of the text -- and an arrow arrived
#      mangled to "?". curl exits 0 in every one of those cases, so it is a SILENT content
#      failure: the alert "sends" and the human sees a file prompt instead of the teaser.
# WHAT: fold stdin to ASCII, mapping the punctuation people actually type to what it means
#       instead of dropping it, and PRESERVE LINE BREAKS so a short list still reads as a list.
# REDIRECT: called by notify-send.sh on --message and --title. Not a general-purpose
#           transliterator; it exists for lock-screen teasers, which are a few words long.
#           Anything needing real typography belongs behind --url.
# WHY A FILE AND NOT `python3 -c`: it started as an inline one-liner and the quoting broke
#       twice -- an apostrophe in the replacement table closed the shell's single quote, and
#       escaped newlines became literal ones. A file has no quoting to get wrong.
# UPDATED: 2026-09-21 (new)
# ─────────────────────────────────────────────────────────────────────────────
import sys
import unicodedata

# Punctuation people actually type, mapped to what it MEANS rather than silently dropped.
REPLACEMENTS = (
    ("—", " - "),   # em dash
    ("–", "-"),     # en dash
    ("•", "*"),     # bullet
    ("·", "-"),     # middle dot
    ("→", "->"),    # right arrow
    ("⇒", "=>"),    # double arrow
    ("‘", "'"),     # curly quotes
    ("’", "'"),
    ("“", '"'),
    ("”", '"'),
    ("…", "..."),   # ellipsis
    (" ", " "),     # non-breaking space
)


def fold(raw: bytes) -> str:
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = raw.decode("utf-8", "replace")

    for src, dst in REPLACEMENTS:
        text = text.replace(src, dst)

    # NFKD then drop what will not survive: accented letters lose their accents rather
    # than the whole word vanishing (cafe, not caf).
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")

    # Collapse runs of whitespace WITHIN a line; keep the line breaks, drop empty lines.
    # A teaser is often a title row plus a short list, and flattening it destroys that.
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


if __name__ == "__main__":
    sys.stdout.buffer.write(fold(sys.stdin.buffer.read()).encode("ascii"))

#!/usr/bin/env python3
# ups_triggers.py: the TRIGGER LOGIC for the two prompt-keyword injectors that were cut on 2026-10-30
# (sop-cleanup Phase 2, ruling 4.4 and 4.5; 12-token-audit U8 and U4). One home for both so the hooks and the rig
# replay (system/tools/rig) run the SAME code.
#   python3 ups_triggers.py save   < prompt text      -> prints 1 if the prompt asks to save, else 0
#   python3 ups_triggers.py num    < prompt text      -> prints 1 if the typed prose has a real number/calculation
#   add --json to read the hook's stdin JSON ({"prompt": ...}) instead of raw text.
# Used by: system/hooks/save_routing_hint.sh (save), system/hooks/inject_compute_mechanically.sh (num, arm 3 only).
# FAIL_POSTURE: any error prints 0 (silent), exit 0. A missed hint costs a small loss; a stuck turn costs a large one.
import re

# ---------- save-routing (cut 4) ----------
# Imperative save intent only: "save" as the first word of a sentence, "save this/that/it/...", "/save" used as a
# command (first token, last token, or right after run/just/ok/the/...), "remember this/that", "jot/write that down",
# or a verb-gated scratchpad mention. NEVER "keep it simple", "hold it", "note that", "I can't remember. This ...".
LEAD = r"(?:(?:ok(?:ay)?|yes|yeah|yep|so|and|now|then|please|pls|just|also|no canon|no checkin|go ahead and|can you|could you|can we|let'?s|lets|i want you to|i need you to|you should)[,.:;!\s]+){0,3}"
SENT = r"(?:^|[.!?\n]\s+)"
NEXT = r"(?=$|[\s.,;:!?]*$|\s+(?:this|that|it|these|those|them|all|everything|and|down|to|in|into|as|first|now|please|so|just|before|for)\b)"
SAVE_RES = [
    re.compile(SENT + LEAD + r"save\b" + NEXT, re.I),
    re.compile(SENT + LEAD + r"(?:jot|capture|log)\s+(?:this|that|it|these|those|all (?:this|that|of (?:this|that|these|it)))\b", re.I),
    re.compile(SENT + LEAD + r"remember\s+(?:this|that|these|the following)\b", re.I),
    re.compile(SENT + LEAD + r"remember\s*[:\-]", re.I),
    re.compile(SENT + LEAD + r"(?:jot|note|write|put)\s+(?:this|that|it|these|those)\s+down\b", re.I),
    # verb-gated scratchpad mention: "write it to the scratch pad", "update the scratchpad", "fill in the scratch pad"
    re.compile(r"\b(?:save|write|add|put|append|record|log|drop|stick|fill(?: in)?|backfill|updat\w*|jot)\b.{0,40}?\bscratch ?pad\b", re.I | re.S),
]
# /save or /<plugin>:save used as a command
SLASH = re.compile(r"(?:^|(?<=\s))/(?:lifehack-brain:)?save\b(?![-\w])")
SLASH_OK_BEFORE = re.compile(r"(?:^|\b(?:run|use|do|just|the|ok|okay|please|and|then|fucking|now|go|to|try)\s+(?:the\s+|a\s+)?(?:fucking\s+)?)$", re.I)

def _slash_cmd(t):
    for m in SLASH.finditer(t):
        before = t[:m.start()]
        after = t[m.end():]
        if not before.strip():                       # first token
            return True
        if re.search(r"\b(?:did|have|had|do|does|were|was|why|when)\s+(?:you|we|i|it)\s*$", before[-20:], re.I):
            continue                                  # a question ABOUT the command, not the command
        if not after.strip(" .!?\n"):                # last token
            return True
        if SLASH_OK_BEFORE.search(before[-40:]):
            return True
    return False

def new_save(p):
    t = re.sub(r"```.*?```", " ", p, flags=re.S)
    t = re.sub(r"`[^`\n]*`", " ", t)
    t = re.sub(r"<(summary|task-notification)\b[^>]*>.*?(?:</\1>|$)", " ", t, flags=re.S | re.I).strip()
    low = t.lower()
    # handoff / reload paste is not a save request (kept from the old hook)
    if re.search(r"##\s*\d*\.?\s*scratch ?pad", low) or "/checkin" in low:
        return False
    if _slash_cmd(t):
        return True
    return any(r.search(t) for r in SAVE_RES)

# ---------- NUMBERS (cut 5) ----------
# Arms 1 and 2 (auto-arm desk list, /calculate armed) are untouched. Only arm 3, the backstop regex, changes.
# Fires on: a dollar amount, or an explicit arithmetic expression, in the prose the person TYPED.
# Does not fire on: bare percentages, dates (10/06/2026), version strings (2.524), fractions/ratios (3/4, 20/20),
# dimensions (35x43), money inside inline code or fenced blocks, or a structured document (lists, tables, bold lines,
# summary/task-notification blocks). NOTE: <pasted_content> is NOT stripped: Claude Code wraps long DICTATED or
# pasted-in text from the person in that tag, and several real money messages sit inside it.
MONEY = re.compile(r"(?<![\w\\$])\$\s?\d[\d,]*(?:\.\d+)?|(?<![\w])(?:USD|US\$|CAD|EUR)\s?\d")
ARITH = re.compile(r"(?<![\w.:/-])\d[\d,]*(?:\.\d+)?\s*(?:[*+]|\s[x×÷/]\s|[×÷]\s)\s*\$?\d")
def _prose(p):
    long_msg = len(p) > 1500
    s = re.sub(r"```.*?```", " ", p, flags=re.S)
    s = re.sub(r"`[^`\n]*`", " ", s)
    s = re.sub(r"<(summary|task-notification|result|output)\b[^>]*>.*?(?:</\1>|$)", " ", s, flags=re.S | re.I)
    keep = []
    for ln in s.split("\n"):
        st = ln.strip()
        if not st: continue
        if (st[0] in "|>#•" or re.match(r"^[-*]\s", st) or re.match(r"^\d+[.)]\s", st) or "**" in st or st.count("|") >= 2) \
                and len(st.split()) <= 45:
            continue   # (a long line starting "- yeah, ..." is dictation, not a bullet: kept)   # list / table / heading / bold line = a document, not a typed sentence
        if re.search(r"[│┃█▌━─]", st):
            continue   # terminal screen / box drawing = pasted output
        if long_msg and len(st.split()) < 6:
            continue   # a scraped price tag / receipt row ("Total Price $4,389.26"), not a sentence
        keep.append(st)
    return "\n".join(keep)

# the person's own voice (long messages only): a money figure counts when its line speaks in first person (I / we / let's / my / our / me / us)
SELF = re.compile(r"\b(?:i|i'm|i'll|i've|i'd|we|we're|we'll|we've|let's|lets|my|our|me|us|mine|ours)\b", re.I)
def new_num(p):
    s = _prose(p.replace("\t", " "))
    for ln in s.split("\n"):
        if (MONEY.search(ln) or ARITH.search(ln)) and (len(p) <= 1500 or SELF.search(ln)):
            return True   # a short message is the person's own words; in a long one (pasted pages) require their voice
    return False


if __name__ == "__main__":
    import sys, json
    try:
        mode = sys.argv[1]
        raw = sys.stdin.read()
        if "--json" in sys.argv:
            raw = (json.loads(raw or "{}").get("prompt") or "")
        print(1 if (new_save(raw) if mode == "save" else new_num(raw)) else 0)
    except Exception:
        print(0)

#!/usr/bin/env python3
# ups_triggers.py: the TRIGGER LOGIC for the two prompt-keyword injectors that were cut on 2026-10-30
# (sop-cleanup Phase 2, ruling 4.4 and 4.5; 12-token-audit U8 and U4). One home for both so the hooks and the rig
# replay (system/tools/rig) run the SAME code.
#   python3 ups_triggers.py save   < prompt text      -> prints 1 if the prompt asks to save, else 0
#   python3 ups_triggers.py num    < prompt text      -> prints 1 if the typed prose has a real number/calculation
#   python3 ups_triggers.py share  < prompt text      -> prints 1 if the prompt asks to get a skill to other people
#   python3 ups_triggers.py machine < prompt text     -> prints 1 if the text is a peer message or task notification, not the person
#   add --json to read the hook's stdin JSON ({"prompt": ...}) instead of raw text.
# Used by: system/hooks/save_routing_hint.sh (save), system/hooks/inject_compute_mechanically.sh (num, arm 3 only),
#          system/hooks/inject_sop_before_build.sh (share, switch team_share_route).
# FAIL_POSTURE: any error prints 0 (silent), exit 0. A missed hint costs a small loss; a stuck turn costs a large one.
import re

# ---------- not the person (2026-11-02) ----------
# The harness delivers cross-session peer messages and task notifications through UserPromptSubmit as if typed. Transcript rows carry
# origin.kind for these; the prompt text is what a hook is sure to have, so this reads how the harness STARTS them. Anchored at the start:
# a person who merely mentions or quotes the tags later in a message still counts.
MACHINE_LEAD = re.compile(r"\s*(?:Another Claude session sent a message:\s*<cross-session-message\b|<task-notification\b)")

def not_the_person(p):
    return bool(MACHINE_LEAD.match(p))

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

# ---------- team-share route (exam D-B08/D-B09, plan fix 23(c)) ----------
# Fires when the person wants a SKILL to reach OTHER PEOPLE. A false alarm costs a stray sign on an unrelated turn, so all three of
# skill + audience + a giving word must be there, tied together by position, and these stay silent: a skill being built that shares
# things ("a skill that shares files with my team"), human skills ("communication skills", "the skills they need"), skill as a modifier
# ("skill matrix", "skill-building SOP"), a refusal ("don't share"), pasted pages (over SHARE_MAX_CHARS), quoted and background-report text.
SHARE_MAX_CHARS = 1000
AUD = r"(?:team(?:mates?)?|co-?workers?|colleagues?|staff|employees?|everyone|everybody|(?:whole|entire) (?:company|office|studio|agency|org\w*))"
GIVE = r"(?:shar(?:e|ing)|send|give|distribute|publish|package|hand out|roll out|get)"
SHARE_SKILL = re.compile(r"(?<![-\w])(skills?)(?![-\w])")
HUMAN_SKILL = re.compile(r"\b(?:soft|people|communication|leadership|technical|coding|interview|language|life|writing|presentation|management|negotiation|social|sales|team)\W*$")
SKILL_MODIFIER = re.compile(r"\s+(?:assessments?|matri(?:x|ces)|gaps?|sets?|levels?|tests?|development|building|trees?|checks?|inventor(?:y|ies)|surveys?)\b")
SKILL_BEING_BUILT = re.compile(r"\s+(?:that|which|who|so|should|for\s+\w+ing|to\s+(?!(?:my|our|the|all|every|them)\b))")
GIVE_NEG = re.compile(r"\b(?:don'?t|do not|never|not|without)\s+(?:\w+\s+){0,2}$")
# "share this skill ...", "give my staff the skill": at least one word between the giving word and "skill" ("a sharing skill" is a kind of skill)
GIVE_THEN_SKILL = re.compile(r"\b(" + GIVE + r")\s+(?:\S+\s+){1,6}$")
TO_AUD = re.compile(r"^.{0,40}?\b(?:with|to|for)\s+(?:\w+\s+){0,3}" + AUD + r"\b")
AVAILABLE_TO_AUD = re.compile(r"^.{0,30}?\b(?:available|accessible)\s+(?:to|for)\s+(?:\w+\s+){0,3}" + AUD + r"\b")
GIVE_IT_TO_AUD = re.compile(r"\b(?:share|send|give|distribute)\s+(?:it|this|that|them)\s+(?:with|to)\s+(?:\w+\s+){0,3}" + AUD + r"\b")
GIVE_IT = re.compile(r"\b(?:share|send|give|distribute)\s+(?:it|this|that|them)\b")
AUD_USE = re.compile(r"(?:\b" + AUD + r"\b.{0,20}\b(?:can|could|able to)\s+(?:all\s+)?|\b(?:can|could)\s+(?:my|our|the)\s+" + AUD + r"\s+(?:all\s+)?)use\s+(?:\S+\s+){1,4}$")
AUD_ANY = re.compile(r"\b" + AUD + r"\b")
AUD_IN_GIVE = re.compile(r"\b" + GIVE + r"\s+(?:\w+\s+){0,3}" + AUD + r"\b")


def new_share(p):
    t = re.sub(r"```.*?```", " ", p, flags=re.S)
    t = re.sub(r"`[^`\n]*`", " ", t)
    t = re.sub(r"<(summary|task-notification|result|output)\b[^>]*>.*?(?:</\1>|$)", " ", t, flags=re.S | re.I).strip()
    if not t or len(t) > SHARE_MAX_CHARS:
        return False
    t = " ".join(t.lower().split())
    for m in SHARE_SKILL.finditer(t):
        before, after = t[max(0, m.start() - 90):m.start()], t[m.end():m.end() + 110]
        if HUMAN_SKILL.search(before) or SKILL_MODIFIER.match(after):
            continue
        give = GIVE_THEN_SKILL.search(before)
        given = give is not None and not GIVE_NEG.search(before[:give.start()])
        if m.group(1) == "skills":   # the plural is mostly the human kind: only "share/send my skills with/to the team" counts
            if given and give.group(1) in ("share", "sharing", "send", "distribute") and TO_AUD.match(after):
                return True
            continue
        if SKILL_BEING_BUILT.match(after):
            continue
        if given and (TO_AUD.match(after) or AUD_IN_GIVE.search(before)):     # share this skill with my team / give my staff the skill
            return True
        if AVAILABLE_TO_AUD.match(after):                                     # the skill available to my whole staff
            return True
        if GIVE_IT_TO_AUD.search(after):                                      # I built this skill, share it with the team
            return True
        if AUD_ANY.search(before) and GIVE_IT.search(after):                  # my team needs this skill. share it with them
            return True
        if AUD_USE.search(before):                                            # how can my team use this skill
            return True
    return False


if __name__ == "__main__":
    import sys, json
    try:
        mode = sys.argv[1]
        raw = sys.stdin.read()
        if "--json" in sys.argv:
            raw = (json.loads(raw or "{}").get("prompt") or "")
        if mode == "machine":
            print(1 if not_the_person(raw) else 0)
        else:
            print(1 if {"save": new_save, "share": new_share}.get(mode, new_num)(raw) else 0)
    except Exception:
        print(0)

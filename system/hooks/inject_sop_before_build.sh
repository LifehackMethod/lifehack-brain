#!/usr/bin/env bash
# LHB fire-journal (B4.1): observes only; never alters this hook's decision/exit/stdout/stderr.
_lhb_src="${BASH_SOURCE[0]}"; case "$_lhb_src" in */*) _lhb_dir="${_lhb_src%/*}" ;; *) _lhb_dir=. ;; esac; . "$_lhb_dir/lib/journal.sh" 2>/dev/null || lhb_journal_fire() { :; }
trap 'lhb_journal_fire "$?" "inject_sop_before_build.sh" "UserPromptSubmit" "" 2>/dev/null || true' EXIT
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: Skills/hooks/desks/sheets/dashboards/crons were being built WITHOUT their
#      hard-won SOP being read first — nothing put the rulebook in front of the
#      model at build time (confirmed 2026-07-11: the full settings.json hook
#      registry + a grep of every hook referenced ZERO build SOP). A gentle
#      "consider the skill" nudge fires ~20%; an explicit inject lands ~84%
#      (skill-building-sop.md §2). So on build-INTENT for one of six recurring
#      things, inject a hard pointer to that thing's SOP so the lessons are in
#      context before the model plans/builds.
# GUARDS: Read-only INJECT observer. NEVER blocks a prompt (degrade-safe -> exit 0).
#         Fires ONLY on a build-VERB within ~3 words of a tracked noun — a bare
#         mention ("skill at cooking", "that hooked me") is a pure NO-OP. No teeth
#         by design: a pointer, not a gate (escalate to a block only if this proves
#         skippable in practice). Fires every matching turn (no suppression).
# REDIRECT: N/A (non-blocking).
# SIGNPOST: The TRIGGER TABLE in this script IS the rule. SOPs pointed at live in
#           system/sops/{skill-building-playbook,hook-sop,desk-building-sop,
#           google-sheet-sop,design-process-sop,cron-jobs-sop}.md. To add a 7th SOP:
#           add one row to the TABLE list below. Hook doctrine: system/hook-contract.md.
# UPDATED: 2026-07-11 (new — SOP build-time pointer injector; council-scoped KISS)
# UPDATED: 2026-10-29 (v2 2.4) — also points at system/register/toolbox.md and /build.
# UPDATED: 2026-10-31 (Enver) — jobs-sop.md renamed cron-jobs-sop.md ("jobs" was too general).
# UPDATED: 2026-10-29 (self-monitoring 5.8) — the cron row points at system/sops/jobs-sop.md, which
#          replaces the donor-only cron-safety.md (never shipped here).
# PORTED: 2026-08-13 from the donor repo — the TABLE's SOP paths are unchanged (repo-relative,
#      not hardcoded), but the `deadend_check.py` invocation named in the last injected line was a
#      literal `the donor clone/...` path; it now resolves from this hook's own location.
#      `desk-building-sop.md`, `cron-safety.md` and `system/information-ingestion-interpretation.md`
#      do not exist yet in this repo — those TABLE rows degrade silently (point at nothing) until
#      those SOPs land; this is a known, pre-existing gap, not something this port fixed or hid.
# UPDATED: 2026-10-31 (Enver) — (a) text inside <summary>/<task-notification>/<result>/<output>
#      blocks is stripped before matching (same strip as lib/ups_triggers.py); (b) stale header lines struck
#      below, not deleted; (c) the injected tag no longer names the operator's private repo; (d) the design-process row is
#      disconnected (that SOP is work in progress).
# STALE as of 2026-10-31 (struck, kept as history): ~~"one of six recurring things"~~ and ~~"SOPs pointed at live in
#      ...design-process-sop...  To add a 7th SOP"~~ — the table has had 7 rows since the ingestion row, and the
#      dashboard row is now disconnected, so 6 live rows; ~~"replaces the donor-only cron-safety.md"~~ and the
#      PORTED note's list of missing SOPs is out of date: desk-building-sop.md now exists. ~~"all three SOPs"~~ in the DO NOT BUILD line:
#      build-sop.md was retired 2026-10-31, so deadend_check.py now reads the entries in skill-building-sop.md and hook-sop.md.
# UPDATED: 2026-11-02 (plan fix 23(c)) — the Google Sheet row fires only when the verb governs the sheet; see
#      sheet_is_the_object below. The other rows are unchanged.
# UPDATED: 2026-11-02 (exam D-B08/D-B09, plan fix 23(c)) -- switch team_share_route: a prompt that asks to get a skill to other people
#      (lib/ups_triggers.py share) also prints the one route to the team Drive folder (shared/tools/team_skills.py route). Both exam
#      prompts were silent here, so the sessions zipped the skill or asked how to share it. Inject only, never blocks.
# FAIL_POSTURE: degrade-safe (any error -> exit 0 silently)
# ─────────────────────────────────────────────────────────────────────────────
set +e

INPUT="$(cat 2>/dev/null)"
[ -z "$INPUT" ] && exit 0

# Resolve THIS repo's root from the hook's own location — never a hardcoded home directory.
_HOOKDIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
_REPO="$(cd "$_HOOKDIR" 2>/dev/null && git rev-parse --show-toplevel 2>/dev/null)"
[ -n "$_REPO" ] || _REPO="${_HOOKDIR%/system/hooks}"
export DEADEND_CHECK_PATH="$_REPO/system/tools/deadend_check.py"

# 2026-11-02: a peer message or task notification is not the person's build request, for every row below and the share route. Live: a peer
# message quoting "build me a google sheet" fired this in two windows. The case test spares a python start on every other prompt.
case "$INPUT" in
  *cross-session-message*|*task-notification*)
    [ "$(printf '%s' "$INPUT" | python3 "$_HOOKDIR/lib/ups_triggers.py" machine --json 2>/dev/null)" = "1" ] && exit 0
    ;;
esac

# team_share_route (roundB.conf; OFF = nothing here runs). The case test spares a python start on every prompt without the word.
. "$_HOOKDIR/lib/roundb.sh" 2>/dev/null || roundb_on() { return 1; }
case "$INPUT" in
  *[Ss][Kk][Ii][Ll][Ll]*)
    if roundb_on team_share_route; then
      IS_SHARE="$(printf '%s' "$INPUT" | python3 "$_HOOKDIR/lib/ups_triggers.py" share --json 2>/dev/null)"
      [ "$IS_SHARE" = "1" ] && python3 "$_REPO/shared/tools/team_skills.py" route 2>/dev/null
    fi
    ;;
esac

printf '%s' "$INPUT" | python3 -c '
import sys, json, re, os

try:
    prompt = json.load(sys.stdin).get("prompt", "") or ""
except Exception:
    sys.exit(0)
if not prompt:
    sys.exit(0)
# 9a (2026-10-31, Enver): ignore text inside background-report blocks. Same strip as
# lib/ups_triggers.py (_prose), so a <task-notification> that merely CONTAINS "build a skill" cannot fire this.
prompt = re.sub(r"<(summary|task-notification|result|output)\b[^>]*>.*?(?:</\1>|$)", " ", prompt, flags=re.S | re.I)
if not prompt.strip():
    sys.exit(0)

# TRIGGER TABLE — (noun-regex, sop-path, human-label). Add a row to extend.
TABLE = [
    (r"skills?",                                    "system/sops/skill-building-sop.md", "skill"),
    (r"hooks?",                                     "system/sops/hook-sop.md",                "hook"),
    (r"desks?",                                     "system/sops/desk-building-sop.md",       "desk"),
    (r"(?:google\s+)?sheets?|spreadsheets?",        "system/sops/google-sheet-sop.md",        "Google Sheet"),
    # DISCONNECTED 2026-10-31 (Enver, decision 5): design-process-sop.md is work in progress, not validated; row kept here as history.
    # (r"dashboards?|views?|screens?",                "system/sops/design-process-sop.md",      "dashboard / view"),
    (r"crons?|scheduled\s+(?:job|task)s?|timers?",  "system/sops/cron-jobs-sop.md",           "cron job"),
    (r"(?:email|mail|inbox|corpus)\s+(?:ingest\w*|read(?:er|ing)?|process(?:or|ing)?|backlog)|ingest(?:ion|or)?\s+(?:skill|desk|pipeline|reader|hook|pass)",
                                                    "system/information-ingestion-interpretation.md", "email / information ingestion reader"),
]

# Build/creation verbs. "new" included so "a new skill" (no verb) still fires.
VERBS = r"build|building|built|make|making|made|creat(?:e|ing)|writ(?:e|ing)|author|construct|design|add|adding|new|scaffold|set\s+up|spin\s+up|put\s+together|draft"

# GOOGLE SHEET ROW ONLY (2026-11-02, plan fix 23(c)): the word "sheet" is everyday English, and the proximity test
# above fired on "write a cheat sheet" and "write up why the sheet guard blocked me". This only ever takes a fire
# away. It keeps one when the verb really governs the sheet: nothing between them ends the clause or changes the
# subject, the word before is not half of another compound, and the word after does not make it a modifier.
NOT_A_WORKBOOK = {"cheat", "crib", "call", "balance", "term", "rap", "fact", "tip", "lyric", "style", "spec",
                  "bed", "baking", "cookie", "one", "sign-in", "sign-up", "signin", "signup", "answer", "charge"}
GAP_BREAKS = {"why", "if", "because", "saying", "says", "said", "sure", "whether", "when", "where", "how", "what",
              "which", "who", "while", "after", "before", "since", "though", "but", "not", "no", "about",
              "regarding", "up", "mention", "mentions", "mentioned", "mentioning", "explain", "explains", "that"}
AFTER_OK = {"for", "of", "to", "with", "that", "which", "from", "in", "on", "at", "and", "or", "so", "called", "named",
            "where", "per", "by", "as", "now", "today", "tomorrow", "please", "first", "next", "then", "too",
            "my", "our", "the", "a", "i", "we", "you", "this"}
def sheet_is_the_object(text, noun):
    for m in re.finditer(r"\b(?:%s)\b" % noun, text):
        before = list(re.finditer(r"\b(?:%s)\b" % VERBS, text[:m.start()]))
        if not before:
            continue
        gap = text[before[-1].end():m.start()]
        if re.search(r"[,.;:!?()]", gap):
            continue
        words = gap.split()
        if len(words) > 4:
            continue
        if words and words[-1].rstrip("-") in NOT_A_WORKBOOK:
            continue
        if any(w in GAP_BREAKS for w in words[:-1]) or (words and words[-1] in GAP_BREAKS - {"that"}):
            continue
        rest = text[m.end():]
        if rest[:1] in ("-", "_"):
            continue
        nxt = re.match(r"\s+([a-z][\w-]*)", rest)
        if nxt and nxt.group(1) not in AFTER_OK and not nxt.group(1).endswith("ing"):
            continue
        return True
    return False

low = prompt.lower()
hits, seen = [], set()
for noun, path, label in TABLE:
    # a build-verb within ~3 words before the noun (optionally through an article)
    pat = r"\b(?:%s)\b(?:\W+\w+){0,3}\W+(?:a\s|an\s|the\s|some\s|new\s|another\s)?(?:%s)\b" % (VERBS, noun)
    if re.search(pat, low) and path not in seen:
        if label == "Google Sheet" and not sheet_is_the_object(low, noun):
            continue
        hits.append((path, label))
        seen.add(path)

if not hits:
    sys.exit(0)

out = ["[SOP CHECK — harness-injected, NOT user input. A standing build rule.]"]
for path, label in hits:
    out.append(
        "Before you plan or build this %s, STOP and Read `%s` in full now — it holds the "
        "hard-won lessons. Do NOT build from memory or a stale mental model: read it first, "
        "then build something better for having read it." % (label, path)
    )
# T27.3b (2026-08-08) — THE GRANULARITY FIX. The line above points at a WHOLE SOP;
# skill-building-sop.md is 2,315 lines, so a session about to rebuild a known dead end is
# handed a haystack containing the one line that would stop it. The 80+ DO NOT BUILD entries
# had ZERO code readers (`grep -rn "DO NOT BUILD" *.py *.sh` -> 0) until deadend_check.py.
# THE FENCE (the operator, 2026-08-07): a POINTER and a SEARCH COMMAND, never the content. Injecting
# 80 entries is the over-injection this fence exists to prevent. Pull, never push.
DEADEND = os.environ.get("DEADEND_CHECK_PATH") or "deadend_check.py"
out.append(
    ("THEN, BEFORE YOU BUILD IT, ASK WHETHER IT ALREADY FAILED: run "
    "`python3 %s \"<what you are about to "
    "build, in plain words>\"` — it searches every DO NOT BUILD entry across the SOPs that carry one "
    "and returns ONLY the matching ones with file:line. It is one command and a few lines of "
    "output, not another document. A NO-MATCH is NOT an all-clear — coverage is ~35%% of what "
    "is on disk, and the tool says so on every empty result.") % DEADEND
)
# v2 2.4 (2026-10-29): also point at the shared toolbox and the /build road. Pointers only, no content.
out.append(
    "ALSO: common tools live once in the shared layer. Before writing any new tool, look at "
    "`system/register/toolbox.md` (the generated list) and USE what is there; never copy a shared tool "
    "into a desk. `/build` is the road that keeps new work in line with the harness."
)
sys.stdout.write("\n".join(out) + "\n")
'
exit 0

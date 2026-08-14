#!/usr/bin/env bash
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
#           google-sheet-sop,design-process-sop,cron-safety}.md. To add a 7th SOP:
#           add one row to the TABLE list below. Hook doctrine: system/hook-contract.md.
# UPDATED: 2026-07-11 (new — SOP build-time pointer injector; council-scoped KISS)
# PORTED: 2026-08-13 from claudeops-config — the TABLE's SOP paths are unchanged (repo-relative,
#      not hardcoded), but the `deadend_check.py` invocation named in the last injected line was a
#      literal `~/claudeops-config/...` path; it now resolves from this hook's own location.
#      `desk-building-sop.md`, `cron-safety.md` and `system/information-ingestion-interpretation.md`
#      do not exist yet in this repo — those TABLE rows degrade silently (point at nothing) until
#      those SOPs land; this is a known, pre-existing gap, not something this port fixed or hid.
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

printf '%s' "$INPUT" | python3 -c '
import sys, json, re, os

try:
    prompt = json.load(sys.stdin).get("prompt", "") or ""
except Exception:
    sys.exit(0)
if not prompt:
    sys.exit(0)

# TRIGGER TABLE — (noun-regex, sop-path, human-label). Add a row to extend.
TABLE = [
    (r"skills?",                                    "system/sops/skill-building-sop.md", "skill"),
    (r"hooks?",                                     "system/sops/hook-sop.md",                "hook"),
    (r"desks?",                                     "system/sops/desk-building-sop.md",       "desk"),
    (r"(?:google\s+)?sheets?|spreadsheets?",        "system/sops/google-sheet-sop.md",        "Google Sheet"),
    (r"dashboards?|views?|screens?",                "system/sops/design-process-sop.md",      "dashboard / view"),
    (r"crons?|scheduled\s+(?:job|task)s?|timers?",  "system/sops/cron-safety.md",             "cron job"),
    (r"(?:email|mail|inbox|corpus)\s+(?:ingest\w*|read(?:er|ing)?|process(?:or|ing)?|backlog)|ingest(?:ion|or)?\s+(?:skill|desk|pipeline|reader|hook|pass)",
                                                    "system/information-ingestion-interpretation.md", "email / information ingestion reader"),
]

# Build/creation verbs. "new" included so "a new skill" (no verb) still fires.
VERBS = r"build|building|built|make|making|made|creat(?:e|ing)|writ(?:e|ing)|author|construct|design|add|adding|new|scaffold|set\s+up|spin\s+up|put\s+together|draft"

low = prompt.lower()
hits, seen = [], set()
for noun, path, label in TABLE:
    # a build-verb within ~3 words before the noun (optionally through an article)
    pat = r"\b(?:%s)\b(?:\W+\w+){0,3}\W+(?:a\s|an\s|the\s|some\s|new\s|another\s)?(?:%s)\b" % (VERBS, noun)
    if re.search(pat, low) and path not in seen:
        hits.append((path, label))
        seen.add(path)

if not hits:
    sys.exit(0)

out = ["[SOP CHECK — harness-injected, NOT user input. A standing ClaudeOps build rule.]"]
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
# THE FENCE (Enver, 2026-08-07): a POINTER and a SEARCH COMMAND, never the content. Injecting
# 80 entries is the over-injection this fence exists to prevent. Pull, never push.
DEADEND = os.environ.get("DEADEND_CHECK_PATH") or "deadend_check.py"
out.append(
    ("THEN, BEFORE YOU BUILD IT, ASK WHETHER IT ALREADY FAILED: run "
    "`python3 %s \"<what you are about to "
    "build, in plain words>\"` — it searches every DO NOT BUILD entry across all three SOPs "
    "and returns ONLY the matching ones with file:line. It is one command and a few lines of "
    "output, not another document. A NO-MATCH is NOT an all-clear — coverage is ~35%% of what "
    "is on disk, and the tool says so on every empty result.") % DEADEND
)
sys.stdout.write("\n".join(out) + "\n")
'
exit 0
